"""Native localhost synthesis and fresh EDA VCS of local enclosing state banks.

The arithmetic/memory oracle runs through original public I/O. The component
does not establish a global simulator cut or FPGA checkpoint acceptance.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
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
SOURCES = (
    "sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointShellStateAccess.scala",
    "sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala",
    "sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala",
    "sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SimulatorStateInventory.scala",
    "sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointShellStateAccessSpec.scala",
    "tools/checkpoint_formats/tests/verify_shell_state_access.py",
    "tools/checkpoint_formats/tests/shell_state_access_tb.sv",
    "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc",
    "tools/checkpoint_formats/tests/audit_checkpoint_regions.py",
    "tools/checkpoint_formats/tests/audit_physical_clock_plan.py",
    "tools/checkpoint_formats/codec.py", "tools/checkpoint_formats/toolchain.py",
)
SOURCES = tuple(sorted(set(SOURCES) | {
    str(p.relative_to(ROOT))
    for p in (ROOT / "sims/firesim/sim/midas/src/main/scala/midas/checkpoint").glob("*.scala")
}))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(directory):
    """Reconstruct every original local owner independently of Scala metadata."""
    directory = Path(directory)
    source = (directory / "source.fir").read_text()
    modules = parse_modules(source)
    require(modules["ShellTop"]["instances"] == {"enclosing": "Shell", "sibling": "Child"},
            "different directed shell fixture")
    local = [r for r in inventory_from_firrtl(source, "ShellTop")
             if r["hierarchy"].startswith("ShellTop.enclosing.")
             and r["hierarchy"].count(".") == 2]
    expected = {r["hierarchy"]: r for r in local}
    require(set(expected) == {"ShellTop.enclosing.cycles", "ShellTop.enclosing.saved",
                             "ShellTop.enclosing.mem", "ShellTop.enclosing.mem_r_data"},
            "incomplete original local-state reconstruction")
    # The producer's exact mapping schema is audited below, before constructing
    # any selectors or compiling RTL. Its StateIDs are never an oracle for data.
    mapping = json.loads((directory / "mapping.json").read_text())
    require(mapping["mapping_version"] == 1 and mapping["selected_execution"] == "ShellTop.enclosing",
            "different local execution mapping")
    rows = mapping["state"]
    require(len(rows) == len(expected), "omitted or duplicate local state")
    require({row["hierarchy"] for row in rows} == set(expected)
            and len({row["state_id"] for row in rows}) == len(rows), "incomplete or duplicate original owners")
    for row in rows:
        original = expected.get(row["hierarchy"])
        require(original is not None and row["state_id"] == original["state_id"],
                "different original local owner identity")
        suffix = row["hierarchy"].split(".")[-1]
        storage = "CheckpointPipeline_mem_r_data" if suffix == "mem_r_data" else suffix
        local_path = "Shell." + suffix
        local_id = hashlib.sha256(canonical(dict(namespace="generated-simulator-state-v1",
                                                 hierarchy=local_path, kind=original["kind"]))).hexdigest()
        require(row["kind"] == original["kind"] and row["local_state_id"] == local_id
                and row["storage_hierarchy"] == "ShellTop.enclosing." + storage,
                "different local pipeline/storage identity")
        chunks = (original["width"] + 63) // 64
        require(row["width"] == original["width"] and row["depth"] == original["depth"]
                and row["transfer_width"] == min(64, original["width"])
                and row["transfer_depth"] == chunks * original["depth"], "reshaped local transfer")
    require(len({(r["bank"], r["slot"]) for r in rows}) == len(rows), "aliased local selectors")
    emitted = parse_modules((directory / "generated.fir").read_text())
    require(emitted["ShellTop"]["instances"] == modules["ShellTop"]["instances"]
            and emitted["Shell"]["instances"] == modules["Shell"]["instances"],
            "changed original concrete child execution")
    require(emitted["Child"]["body"] == modules["Child"]["body"], "changed child definition")
    binding = json.loads((directory / "binding.json").read_text())
    source_annotations = json.loads((directory / "source.anno.json").read_text())
    final_annotations = json.loads((directory / "generated.anno.json").read_text())
    require(final_annotations == [a for a in source_annotations
                                  if a["class"] != "firrtl.transforms.CombinationalPath"],
            "changed original annotation ownership/order")
    for key, filename in (("host_sha256", "source.fir"), ("reference_sha256", "reference.fir"),
                          ("instrumented_sha256", "generated.fir"), ("mapping_sha256", "mapping.json"),
                          ("manifest_sha256", "manifest.json"), ("banks_binding_sha256", "banks-binding.json")):
        require(binding[key] == sha(directory / filename), "changed local source/output binding " + key)
    require(binding["scope"] == "existing_unique_execution_local_state_readout_only"
            and binding["local_entries"] == 4 and binding["child_executions_frozen"] is False
            and binding["transport_state_supported"] is False, "changed local bank scope")
    for flag in ("complete_fpga_capture", "deployable_capture_image",
                 "production_freeze_owners_bound", "metasim_restore_supported"):
        require(binding[flag] is False, "local banks cannot grant hardware admission")
    return rows


def selectors(rows):
    lines = ["task allwords;", "begin"]
    for row in rows:
        suffix = row["hierarchy"].split(".")[-1]
        values = {"cycles": ["64'(expected_cycle)"],
                  "saved": ["64'(expected_value)", "64'(expected_value >> 64)"],
                  "mem_r_data": ["64'(expected_read)"],
                  "mem": [f"64'(expected_memory[{i}])" for i in range(4)]}[suffix]
        require(len(values) == row["transfer_depth"], "fixture oracle transfer coverage")
        lines.extend(f"readword({row['bank']},{row['slot']},{i},{value},0);"
                     for i, value in enumerate(values))
    return "\n".join(lines + ["end", "endtask", ""])


def audit_negatives(generated, output):
    """Rehash altered documents so source reconstruction must reject them."""
    results = []
    for case in ("omitted_owner", "duplicate_owner", "changed_id", "pipeline_remap",
                 "wide_truncation", "aliased_selector", "changed_child", "false_admission"):
        directory = output / case
        shutil.copytree(generated, directory)
        mapping = json.loads((directory / "mapping.json").read_text())
        binding = json.loads((directory / "binding.json").read_text())
        rows = mapping["state"]
        if case == "omitted_owner":
            rows.pop()
        elif case == "duplicate_owner":
            rows[-1] = dict(rows[0], bank=rows[-1]["bank"], slot=rows[-1]["slot"])
        elif case == "changed_id":
            rows[0]["state_id"] = "0" * 64
        elif case == "pipeline_remap":
            next(r for r in rows if r["hierarchy"].endswith(".mem_r_data"))["storage_hierarchy"] = "ShellTop.enclosing.saved"
        elif case == "wide_truncation":
            next(r for r in rows if r["hierarchy"].endswith(".saved"))["transfer_depth"] = 1
        elif case == "aliased_selector":
            rows[-1]["slot"] = rows[0]["slot"]
        elif case == "changed_child":
            path = directory / "generated.fir"
            text = path.read_text()
            require(text.count("count <=") == 1, "ambiguous child mutation")
            path.write_text(text.replace("count <=", "count <= UInt<8>(0) ; original:", 1))
            binding["instrumented_sha256"] = sha(path)
        else:
            binding["complete_fpga_capture"] = True
        (directory / "mapping.json").write_bytes(canonical(mapping))
        binding["mapping_sha256"] = sha(directory / "mapping.json")
        (directory / "binding.json").write_bytes(canonical(binding))
        try:
            audit(directory)
        except FormatError as error:
            results.append(dict(case=case, status="rejected", error=str(error)))
        else:
            raise FormatError("coherently rehashed shell corruption accepted: " + case)
    (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("vivado", "vcs"), required=True)
    parser.add_argument("--generated", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), "evidence under runs required")
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + "-", dir=args.out.resolve()))
    source_hashes = {n: sha(ROOT / n) for n in SOURCES}
    commands = []
    receipt = dict(status="running", backend="f2" if args.mode == "vivado" else "eda",
                   scope="enclosing local state-bank component only; no global cut or hardware capture",
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   source_root=str(ROOT), sources=source_hashes, physical_fpga_capture=False,
                   full_image=False, cut_labels="component scenario identifiers; local cycle output independently checked")
    (out / "summary.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(out, flush=True)

    def run(argv, name, expected=0):
        log = out / (name + ".log")
        row = dict(argv=list(map(str, argv)), cwd=str(out), log=str(log))
        commands.append(row)
        with log.open("w") as stream:
            result = subprocess.run(row["argv"], cwd=out, stdout=stream, stderr=subprocess.STDOUT)
        row["returncode"] = result.returncode
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(result.returncode == expected, "inspect underlying compiler/runtime log " + str(log))
        return log.read_text()

    if args.mode == "vivado":
        require(ROOT == Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"),
                "native localhost Vivado required")
        require(args.generated is not None and args.native is None, "explicit generated input required")
        shutil.copytree(args.generated, out / "generated")
        rows = audit(out / "generated")
        receipt["independent_rehashed_negatives"] = audit_negatives(out / "generated", out / "audit-negatives")
        (out / "shell_selectors.svh").write_text(selectors(rows))
        (out / "sources").mkdir()
        for name in SOURCES:
            shutil.copyfile(ROOT / name, out / "sources" / Path(name).name)
        (out / "synth.tcl").write_text("""set_param general.maxThreads 4
read_verilog -sv generated/generated.sv
synth_design -top ShellTop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
create_clock -name access_clock -period 7.142857 [get_ports checkpoint_shell_ckpt_clock]
foreach path {enclosing/child sibling} {
  if {[llength [get_cells $path]] != 1} {error "original child execution disappeared"}
}
if {[llength [get_cells -hier -filter {REF_NAME == BUFGCE}]] != 0} {error "local banks introduced physical clock owners"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force shell-state-access.dcp
puts "SHELL_STATE_ACCESS_SYNTH_PASS original_children=2"
""")
        receipt["inputs"] = {str(p.relative_to(out)): sha(p) for p in out.rglob("*")
                             if p.is_file() and p.name != "summary.json"}
        text = run(["vivado", "-mode", "batch", "-source", "synth.tcl"], "synth")
        require("SHELL_STATE_ACCESS_SYNTH_PASS original_children=2" in text
                and not re.search(r"ERROR:|CRITICAL WARNING:", text), "native shell synthesis failed")
        receipt["entries"] = len(rows)
    else:
        require(str(ROOT).startswith("/scratch/") and
                toolchain.VCS == "/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs", "EDA SP2 VCS required")
        require(args.native is not None and args.generated is None, "explicit native receipt required")
        native = json.loads((args.native / "summary.json").read_text())
        require(native["status"] == "pass" and native["backend"] == "f2"
                and native["sources"] == source_hashes, "stale native shell source pins")
        for group in ("inputs", "artifacts"):
            for name, digest in native[group].items():
                require(sha(args.native / name) == digest, "changed native shell " + group + " " + name)
        for name in native["inputs"]:
            destination = out / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.native / name, destination)
        receipt["inputs"] = native["inputs"]
        rows = audit(out / "generated")
        require((out / "shell_selectors.svh").read_text() == selectors(rows), "different oracle selectors")
        shutil.copyfile(ROOT / "tools/checkpoint_formats/tests/shell_state_access_tb.sv", out / "testbench.sv")
        for mode in ("healthy", "corrupt"):
            folder = out / mode
            folder.mkdir()
            text = (out / "generated/generated.sv").read_text()
            if mode == "corrupt":
                needle = "assign checkpoint_shell_ckpt_resp_data = checkpoint_shell_ckpt_saved_data;"
                require(text.count(needle) == 1, "ambiguous compiled payload corruption site")
                text = text.replace(needle, "assign checkpoint_shell_ckpt_resp_data = checkpoint_shell_ckpt_saved_data ^ 64'h1;")
            (folder / "compiled.sv").write_text(text)
            run([toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate", "-debug_access+all",
                 "+incdir+" + str(out), "-top", "shell_state_access_tb",
                 "-Mdir=" + str(folder / "csrc"), "-o", str(folder / "simv"),
                 str(folder / "compiled.sv"), str(out / "testbench.sv"),
                 str(ROOT / "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc")], mode + "-compile")
            text = run([folder / "simv", "-no_save"], mode + "-run", 0 if mode == "healthy" else 1)
            wave = out / "shell-state-access.vcd"
            require(wave.is_file() and wave.stat().st_size > 0, "missing full-visibility debug wave")
            shutil.move(wave, folder / wave.name)
            if mode == "healthy":
                match = re.search(r"SHELL_STATE_ACCESS_PASS checks=(\d+) reads=(\d+) stalls=(\d+) edges=(\d+) cuts=4", text)
                require(match and int(match[1]) > 1000 and int(match[2]) == 69,
                        "incomplete shell functional/readout regression")
                receipt["checks"], receipt["reads"], receipt["stalls"], receipt["edges"] = map(int, match.groups())
            else:
                require("SHELL_DIVERGENCE cut=11" in text and "frozen=1" in text
                        and "signal=captured word" in text and "SHELL_STATE_ACCESS_PASS" not in text,
                        "compiled payload corruption failed to stop at first capture")
                receipt["compiled_payload_corruption_rejected"] = True
        receipt["native_receipt"] = dict(path=str(args.native / "summary.json"),
                                        sha256=sha(args.native / "summary.json"))
    require(source_hashes == {n: sha(ROOT / n) for n in SOURCES}, "source changed during shell verification")
    receipt.update(status="pass", commands=commands,
                   artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob("*")
                              if p.is_file() and (p.suffix in {".log", ".rpt", ".dcp", ".vcd"}
                                                  or p.name in {"commands.json", "compiled.sv", "simv"})})
    (out / "summary.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(out / "summary.json", flush=True)


if __name__ == "__main__":
    main()
