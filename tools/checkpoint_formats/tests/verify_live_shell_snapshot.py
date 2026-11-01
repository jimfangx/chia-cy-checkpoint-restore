"""Local native synthesis / EDA-only VCS of actual live-shell register staging.

This is component evidence, never a physical FPGA checkpoint or CPU migration.
The independent audit enumerates original registers and checks pre-edge VCD
values, rather than using the packed observation vector as the payload oracle.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.tests.audit_checkpoint_regions import inventory_from_firrtl
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "automations/checkpoint_loop/runs"
RTL = "sims/firesim/sim/midas/src/main/verilog/CheckpointNativeStateSnapshot.sv"
TB = "tools/checkpoint_formats/tests/live_shell_snapshot_tb.sv"
SELF = "tools/checkpoint_formats/tests/verify_live_shell_snapshot.py"
SOURCES = sorted({str(p.relative_to(ROOT)) for tree in (
    "sims/firesim/sim/midas/src/main/scala/midas/checkpoint",
    "sims/firesim/sim/midas/src/test/scala/midas/checkpoint")
    for p in (ROOT / tree).glob("*.scala")} | {RTL, TB, SELF,
    "tools/checkpoint_formats/tests/audit_checkpoint_regions.py",
    "tools/checkpoint_formats/tests/audit_physical_clock_plan.py",
    "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc",
    "tools/checkpoint_formats/toolchain.py", "tools/checkpoint_formats/codec.py"})
NEGATIVES = ("missing-before", "freeze-before", "early-read", "sameedge-read", "overlap", "duplicate",
             "drift", "missing-after", "lost-freeze", "lost-owner-freeze", "endpoint-reset", "busy-release")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def audit_generated(directory, binding=None):
    read = lambda n: (directory / n).read_text()
    doc = json.loads(read("binding.json")) if binding is None else binding
    original = inventory_from_firrtl(read("source.fir"), "LiveTop")
    expected = sorted((r for r in original if r["hierarchy"] != "LiveTop.shell.count"), key=lambda r: r["hierarchy"])
    require(len(expected) == 8 and len(doc["state"]) == 8, "incomplete original live register inventory")
    before, after = parse_modules(read("source.fir"))["Shell"], parse_modules(read("wired.fir"))["Shell"]
    offset = 0
    for row, source in zip(doc["state"], expected):
        require(all(row[k] == source[k] for k in ("state_id", "hierarchy", "width", "signed")),
                "changed original live owner")
        name = source["hierarchy"].split(".")[-1]
        require(row["expression"] == name and row["offset"] == offset, "changed live packing")
        def declaration(body):
            m = re.search(r"^  reg " + name + r" : [^\n]+\n    reset => [^\n]+", body, re.M)
            require(m is not None, "missing original declaration")
            return "\n".join(line[2:] for line in m[0].splitlines())
        require(declaration(before["body"]) == declaration(after["body"])
                and before["drivers"][name] == after["drivers"][name], "original live execution changed")
        require(row["declaration_sha256"] == hashlib.sha256(declaration(before["body"]).encode()).hexdigest()
                and row["driver_sha256"] == hashlib.sha256((name + " <= " + before["drivers"][name]).encode()).hexdigest(),
                "original equations not bound")
        offset += row["width"]
    require(offset == doc["bits"] == 237 and doc["words"] == 4 and doc["staging_owner_bits"] == 308,
            "incorrect complete payload geometry")
    require(doc["raw_clock"] == "LiveTop.shell.clock" and doc["enclosing_raw_clock"] == "LiveTop.clock"
            and doc["snapshot_version"] == 1
            and doc["scope"] == "selected_original_live_shell_register_atomic_observation_only",
            "changed clock or ownership scope")
    require("checkpoint_shell_ckpt_clock" not in read("wired.fir"), "independent access clock still exists")
    require(doc["source_sha256"] == sha(ROOT / RTL) and doc["wired_sha256"] == sha(directory / "wired.fir")
            and doc["shell_binding_sha256"] == sha(directory / "banked-binding.json")
            and doc["wired_annotations_sha256"] == sha(directory / "wired.anno.json"), "stale source binding")
    for flag in ("complete_fpga_capture", "deployable_capture_image", "production_freeze_owners_bound",
                 "metasim_restore_supported", "staging_restore_supported", "target_time_authority_proven"):
        require(doc[flag] is False, "component falsely admits hardware/restore acceptance")
    mapping = json.loads(read("banked-mapping.json"))
    require(doc["original_unsupported_live_owners"] == mapping["unsupported_live_owners"], "lost ownership deficits")
    require(len(mapping["state"]) == 1 and mapping["state"][0]["hierarchy"] == "LiveTop.shell.count",
            "different original functional bank")
    return doc, mapping["state"][0]


def wave_rows(path, names):
    scopes, codes, values = [], {}, {}
    def sample():
        require(set(codes) == names, "missing full-visibility VCD signals: " + str(names - set(codes)))
        return {n: int(values[c], 2) if re.fullmatch("[01]+", values.get(c, "x")) else None for n,c in codes.items()}
    with path.open() as stream:
        for line in stream:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "$scope":
                scopes.append(parts[2])
            elif parts[0] == "$upscope":
                scopes.pop()
            elif parts[0] == "$var":
                full = ".".join(scopes + [parts[4].lstrip("\\")])
                prefix = "live_shell_snapshot_tb."
                if full.startswith(prefix) and full[len(prefix):] in names:
                    codes[full[len(prefix):]] = parts[3]
            elif line.startswith("#"):
                yield sample()
            elif line[0] in "bB" and len(parts) == 2:
                values[parts[1]] = parts[0][1:].lower()
            elif line[0] in "01xXzZ":
                values[line[1:].strip()] = line[0].lower()
    yield sample()


def audit_wave(path, doc, *, payload_bit=None, owner_bit=None):
    stage = "dut.shell.checkpoint_shell_live_snapshot_adapter."
    pending = "dut.shell.checkpoint_shell_ckpt_pending"
    names = set(("clock", "snapshot_reset", "bank_reset", "freeze", "request", "release_snapshot", "owners_present",
        "owners_frozen", "target_cycle", "ready", "valid", "borrow_enable", "failed", "word_address", "word_error",
        "word_data", "cut_cycle", "error", "control_state", "req_valid", "req_ready", "resp_valid", "resp_ready"))
    names |= {stage + n for n in ("clock", "payload", "occupied", "cut_cycle", "error", "live_state")}
    names |= {"dut.shell." + r["expression"] for r in doc["state"]} | {pending}
    previous = None
    saved = label = occupied = sticky = 0
    captures, releases, accepted, acknowledged, reads, held = [], 0, 0, 0, 0, 0
    def packed(v):
        return sum((v["dut.shell." + r["expression"]] & ((1 << r["width"]) - 1)) << r["offset"] for r in doc["state"])
    for v in wave_rows(path, names):
        if any(x is None for x in v.values()):
            require(v["snapshot_reset"] != 0, "unknown state after independent initialization")
            previous = v
            continue
        if previous and previous["clock"] == 0 and v["clock"] == 1:
            p = previous
            if p["snapshot_reset"]:
                saved = label = occupied = sticky = 0
            elif all(x is not None for x in p.values()):
                capture = p["request"] and not occupied
                active = occupied or p["request"] or p["req_valid"] or p["release_snapshot"]
                faults = (int(bool(active and (not p["owners_present"] or p["bank_reset"]))) |
                    (int(bool(active and not (p["freeze"] and p["owners_frozen"]))) << 1) |
                    (int(bool(((capture or p["release_snapshot"]) and p[pending]) or (capture and p["req_valid"]))) << 2) |
                    (int(bool(p["req_valid"] and not occupied)) << 3) |
                    (int(bool(occupied and p["target_cycle"] != label)) << 4) |
                    (int(bool((p["request"] and occupied) or (p["request"] and p["release_snapshot"]) or
                              (p["release_snapshot"] and not occupied))) << 5))
                if not sticky and not faults:
                    if p["request"] and p["ready"]:
                        saved, label, occupied = packed(p), p["target_cycle"], 1
                        captures.append(label)
                    elif p["release_snapshot"]:
                        occupied = 0
                        releases += 1
                sticky |= faults
                if p["req_valid"] and p["req_ready"]:
                    require(occupied and p["borrow_enable"] and not p["failed"], "bank borrowed before staging/fault")
                    accepted += 1
                if p["resp_valid"] and p["resp_ready"]:
                    require(p["borrow_enable"] and not p["failed"], "response acknowledged outside staged cut")
                    acknowledged += 1
                held += int(bool(sticky))
        if v["snapshot_reset"]:
            previous = v
            continue
        require(v[stage + "clock"] == v["clock"], "staging clock differs from original raw clock")
        require(v[stage + "live_state"] == packed(v), "live vector lost an original register bit")
        observed_payload = v[stage + "payload"] ^ (0 if payload_bit is None or not occupied else 1 << payload_bit)
        require(observed_payload == saved and v[stage + "cut_cycle"] == label
                and v[stage + "occupied"] == occupied and v[stage + "error"] == sticky,
                "snapshot differs from independently reconstructed preedge original state")
        observed_owner = v["control_state"] ^ (0 if owner_bit is None else 1 << owner_bit)
        require(observed_owner == saved | (occupied << 237) | (label << 238) | (sticky << 302),
                "staging control readback omitted original owner storage")
        if v["valid"]:
            require(occupied and not v["failed"] and v["borrow_enable"] and not v["release_snapshot"],
                    "unqualified snapshot publication")
            address = v["word_address"]
            require(v["word_error"] == int(address >= 4) and v["word_data"] ==
                    ((saved >> (address * 64)) & ((1 << 64) - 1) if address < 4 else 0), "serial staged read differs")
            reads += int(address < 4)
        else:
            require(not v["borrow_enable"] and not v["req_ready"] and not v["resp_valid"]
                    and v["word_error"] and v["word_data"] == 0, "revoked handshake or payload escaped")
        previous = v
    require(captures or held, "wave exercised no staging/faults")
    return dict(cut_labels=captures, releases=releases, bank_requests=accepted,
                bank_responses=acknowledged, serial_samples=reads, sticky_fault_edges=held)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("vivado", "vcs"), required=True)
    parser.add_argument("--generated", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), "evidence beneath runs required")
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + "-", dir=args.out.resolve()))
    sources = {n: sha(ROOT / n) for n in SOURCES}
    receipt = dict(status="running", backend="f2" if args.mode == "vivado" else "eda", sources=sources,
        observed_utc=datetime.now(timezone.utc).isoformat(), source_root=str(ROOT), host=socket.gethostname(),
        physical_fpga_capture=False, full_image=False, scope="original live shell register atomic staging component")
    commands = []
    def save():
        (out / "summary.json").write_text(json.dumps(receipt, indent=2) + "\n")
    save()
    print(out, flush=True)
    def run(argv, name, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(out), log=str(out / (name + ".log")))
        commands.append(row)
        with Path(row["log"]).open("x") as stream:
            result = subprocess.run(row["argv"], cwd=out, stdout=stream, stderr=subprocess.STDOUT)
        row["returncode"] = result.returncode
        receipt["commands"] = commands
        save()
        require(result.returncode == expected, "inspect actual compiler/runtime log " + row["log"])
        return Path(row["log"]).read_text()
    if args.mode == "vivado":
        require(ROOT == Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"), "native manager Vivado required")
        require(args.generated is not None and args.native is None, "explicit generated input required")
        shutil.copytree(args.generated, out / "generated")
        doc, bank = audit_generated(out / "generated")
        negatives = []
        for case in ("omission", "shape", "offset", "id", "signed", "restore", "clock"):
            mutant = copy.deepcopy(doc)
            if case == "omission": mutant["state"].pop()
            elif case == "shape": mutant["state"][2]["width"] -= 1
            elif case == "offset": mutant["state"][2]["offset"] += 1
            elif case == "id": mutant["state"][0]["state_id"] = "0" * 64
            elif case == "signed": mutant["state"][3]["signed"] = False
            elif case == "restore": mutant["staging_restore_supported"] = True
            elif case == "clock": mutant["raw_clock"] = "LiveTop.shell.reset"
            try: audit_generated(out / "generated", mutant)
            except FormatError as error: negatives.append(dict(case=case, rejected=True, error=str(error)))
            else: raise FormatError("accepted rehashed schema mutation " + case)
        receipt["schema_negatives"] = negatives
        shutil.copyfile(ROOT / RTL, out / "snapshot.sv")
        (out / "bank-selector.svh").write_text(f"localparam COUNT_BANK=8'd{bank['bank']}, COUNT_SLOT=16'd{bank['slot']};\n")
        (out / "synth.tcl").write_text("""set_param general.maxThreads 4
read_verilog -sv {generated/wired.sv snapshot.sv}
synth_design -top LiveTop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none -keep_equivalent_registers
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set stage [get_cells shell/checkpoint_shell_live_snapshot_adapter]
if {[llength $stage] != 1} {error "missing original staging instance"}
set staged [get_cells -hier -filter {NAME =~ */checkpoint_shell_live_snapshot_adapter/* && IS_SEQUENTIAL == 1}]
set allseq [get_cells -hier -filter {IS_SEQUENTIAL == 1}]
if {[llength $staged] != 308} {error "incomplete original staging owner"}
if {[llength [get_cells -hier -filter {REF_NAME == BUFGCE}]] != 0} {error "unexpected gated clock owner"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force live-shell-snapshot.dcp
puts "LIVE_SHELL_SNAPSHOT_SYNTH_PASS staging_bits=[llength $staged] sequential=[llength $allseq]"
""")
        receipt["inputs"] = {str(p.relative_to(out)): sha(p) for p in out.rglob("*") if p.is_file() and p.name != "summary.json"}
        text = run(["vivado", "-mode", "batch", "-source", "synth.tcl"], "synth")
        require("LIVE_SHELL_SNAPSHOT_SYNTH_PASS staging_bits=308" in text and
                not re.search(r"ERROR:|CRITICAL WARNING:", text), "native staging synthesis failed")
    else:
        require(str(ROOT).startswith("/scratch/") and toolchain.VCS == "/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs", "EDA SP2 VCS required")
        require(args.native is not None and args.generated is None, "explicit native synthesis receipt required")
        native = json.loads((args.native / "summary.json").read_text())
        require(native["status"] == "pass" and native["sources"] == sources, "stale native sources")
        for group in ("inputs", "artifacts"):
            for name,digest in native[group].items(): require(sha(args.native / name) == digest, "changed native artifact " + name)
        for name in native["inputs"]:
            dest = out / name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(args.native / name, dest)
        receipt["inputs"] = native["inputs"]
        doc, bank = audit_generated(out / "generated")
        require((out / "bank-selector.svh").read_text() == f"localparam COUNT_BANK=8'd{bank['bank']}, COUNT_SLOT=16'd{bank['slot']};\n", "changed bank selector")
        shutil.copyfile(ROOT / TB, out / "testbench.sv")
        audits = {}
        for mode in ("healthy", "payload"):
            folder = out / mode; folder.mkdir()
            text = (out / "snapshot.sv").read_text()
            if mode == "payload":
                needle = "word_error ? 64'b0 : padded[word_address * 64 +: 64]"
                require(text.count(needle) == 1, "ambiguous payload mutation site")
                text = text.replace(needle, "word_error ? 64'b0 : (padded[word_address * 64 +: 64] ^ 64'h1)")
            (folder / "compiled-snapshot.sv").write_text(text)
            run([toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate", "-debug_access+all",
                "+incdir+" + str(out), "-top", "live_shell_snapshot_tb", "-Mdir=" + str(folder / "csrc"),
                "-o", str(folder / "simv"), str(out / "generated/wired.sv"), str(folder / "compiled-snapshot.sv"),
                str(out / "testbench.sv"), str(ROOT / "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc")], mode + "-compile")
            for case in (("healthy", *NEGATIVES) if mode == "healthy" else ("payload",)):
                text = run([folder / "simv", "-no_save", "+CASE=" + case], case + "-run", 1 if case == "payload" else 0)
                wave = out / "live-shell-snapshot.vcd"
                require(wave.is_file() and wave.stat().st_size > 0, "missing full debug VCD")
                destination = out / (case + ".vcd"); wave.rename(destination)
                if case == "payload":
                    require("LIVE_SHELL_DIVERGENCE scenario=payload cycle=0 signal=staged word and high padding reads=0" in text
                            and "LIVE_SHELL_SNAPSHOT_PASS" not in text, "payload corruption did not stop at first divergent word")
                    continue
                audits[case] = audit_wave(destination, doc)
                if case == "healthy":
                    match = re.search(r"LIVE_SHELL_SNAPSHOT_PASS checks=(\d+) cuts=4 reads=4 stalls=32 live_changes=(\d+)", text)
                    require(match and audits[case]["cut_labels"] == [0,17,128,256] and audits[case]["bank_responses"] == 4,
                            "incomplete four-cut live execution")
                    receipt["checks"] = int(match[1])
                else:
                    require("LIVE_SHELL_SNAPSHOT_NEGATIVE_PASS scenario=" + case in text
                            and audits[case]["bank_responses"] == 0, "fault acknowledged a bank response")
        receipt["wave_audits"] = audits
        mutations = []
        for kind,bits in (("payload",237),("owner",308)):
            for bit in range(bits):
                try: audit_wave(out / "healthy.vcd", doc, **({"payload_bit":bit} if kind=="payload" else {"owner_bit":bit}))
                except FormatError: mutations.append(dict(kind=kind, bit=bit, rejected=True))
                else: raise FormatError("independent wave auditor accepted " + kind + " mutation " + str(bit))
        (out / "wave-mutations.json").write_text(json.dumps(mutations, indent=2) + "\n")
        receipt["wave_mutations_rejected"] = len(mutations)
        receipt["native_receipt"] = dict(path=str(args.native / "summary.json"), sha256=sha(args.native / "summary.json"))
    require(sources == {n:sha(ROOT / n) for n in SOURCES}, "sources changed during verification")
    receipt.update(status="pass", commands=commands, artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob("*")
        if p.is_file() and (p.suffix in {".vcd", ".log", ".rpt", ".dcp"} or p.name in {"simv", "wave-mutations.json"})})
    save(); print(out / "summary.json", flush=True)


if __name__ == "__main__":
    main()
