"""Local F2-part synthesis and fresh EDA SP2 tests of coordinated native cuts.

Requires source-bound emitted queue synthesis. This establishes component
sequencing, not a complete image, physical capture, host transport or CPU restore.
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
import zipfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests import verify_shared_queue_access as queue
from tools.checkpoint_formats.tests import native_capture_queue
from tools.checkpoint_formats.tests.audit_native_state_capture_wave import audit

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "automations/checkpoint_loop/runs"
VERILOG = "sims/firesim/sim/midas/src/main/verilog/"
RTL = VERILOG + "CheckpointNativeStateCapture.sv"
TB = "tools/checkpoint_formats/tests/native_state_capture_tb.sv"
POLICY_TB = "tools/checkpoint_formats/tests/native_read_policy_tb.sv"
EXIT = "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc"
SOURCES = tuple(sorted(set(queue.SOURCES) | {RTL, TB, POLICY_TB, EXIT,
    VERILOG + "CheckpointNativeStateSnapshot.sv", VERILOG + "CheckpointPhysicalClockCut.sv",
    "tools/checkpoint_formats/tests/verify_native_state_capture.py",
    "tools/checkpoint_formats/tests/native_capture_queue.py",
    "tools/checkpoint_formats/tests/audit_native_state_capture_wave.py"}))
GEOMETRIES = (1, 64, 65, 130, 1036, 1664, 6656)
NEGATIVES = ("owner", "owner-error", "freeze", "ce", "cycle", "overlap", "borrow",
             "early-release", "early-borrow", "early-owner", "sample-busy", "sample-owner", "sample-borrow",
             "sample-capture", "sample-release")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def script(queue_mode):
    text = "set_param general.maxThreads 4\n"
    text += "read_verilog -sv " + " ".join(Path(n).name for n in SOURCES if n.startswith(VERILOG)) + "\n"
    if queue_mode:
        text += "read_verilog -sv generated/generated.sv native-capture-queue.sv\nread_xdc generated/generated.synthesis.xdc\n"
    top = "NativeCaptureQueueTop" if queue_mode else "CheckpointNativeStateCapture"
    parameters = "" if queue_mode else " -generic {BITS=1036 GATES=3 OWNERS=2}"
    text += f"synth_design -top {top} -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none{parameters}\n"
    text += "create_clock -name raw_clock -period 7.142857 [get_ports clock]\n"
    text += "set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]\n"
    # The generated shared host retains its original, unused always-on gate.
    # It is not silently incorporated into the new controller's latch vector.
    text += f'if {{[llength $gates] != {3 if queue_mode else 4}}} {{error "wrong native gate topology"}}\n'
    text += '''foreach gate $gates {
  if {[get_property CE_TYPE $gate] ne "SYNC"} {error "nondefault native CE latch contract"}
  puts "NATIVE_CAPTURE_GATE [get_property NAME $gate] [get_property CE_TYPE $gate]"
}
'''
    text += "set fall [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]\n"
    text += 'if {[llength $fall] != 1} {error "missing common low-phase mask"}\n'
    if queue_mode:
        text += """set block [get_cells -hier -filter {REF_NAME =~ RAMB*}]
foreach path {host/q0 host/q1 host/q2} {
  set count 0
  foreach cell $block {if {[string match "$path/*" [get_property NAME $cell]]} {incr count}}
  if {$count != 2} {error "changed native queue RAM inference at $path"}
}
"""
    else:
        text += """set registers [get_cells -hier -filter {REF_NAME =~ FD*}]
if {[llength $registers] != 1189} {error "incomplete original composite register ownership: [llength $registers]"}
puts "NATIVE_CAPTURE_STORAGE bits=1189 payload=1036 snapshot_control=71 physical_control=73 sequencer=9"
"""
    prefix = "queue" if queue_mode else "owner"
    text += f"report_utilization -file {prefix}-utilization.rpt\nreport_timing_summary -file {prefix}-timing.rpt\n"
    text += f"write_checkpoint -force {prefix}.dcp\nputs \"NATIVE_CAPTURE_SYNTH_PASS top={top}\"\n"
    return text


def validate_native(receipt, sources):
    doc = json.loads(receipt.read_text())
    require(doc["status"] == "pass" and doc["backend"] == "f2" and doc["sources"] == sources,
            "stale or failed native capture receipt")
    require(doc["physical_fpga_capture"] is False and doc["full_image"] is False, "wrong native scope")
    for group in ("inputs", "artifacts"):
        for name, digest in doc[group].items():
            require(sha(receipt.parent / name) == digest, "changed native capture " + name)
    for name in SOURCES:
        require(sha(receipt.parent / "sources" / name) == sources[name], "changed source snapshot " + name)
        if name.startswith(VERILOG) or name in (TB, POLICY_TB, EXIT):
            require(sha(receipt.parent / Path(name).name) == sources[name],
                    "synthesis/execution copy differs from original source " + name)
    original_path = local(ROOT, doc["queue_receipt"]["path"])
    require(sha(original_path) == doc["queue_receipt"]["sha256"], "changed original native queue receipt")
    original_queue = json.loads(original_path.read_text())
    require(original_queue["status"] == "pass" and original_queue["backend"] == "f2" and
            original_queue["sources"] == {n: sources[n] for n in queue.SOURCES}, "unbound original native queue sources")
    for group in ("inputs", "artifacts"):
        for name, digest in original_queue[group].items():
            require(sha(original_path.parent / name) == digest, "changed original native queue " + name)
    names = lambda directory: {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
    require(names(receipt.parent / "generated") == names(original_path.parent / "generated"),
            "different original generated queue input set")
    for name in names(receipt.parent / "generated"):
        require(sha(receipt.parent / "generated" / name) == sha(original_path.parent / "generated" / name),
                "different original generated queue input")
    for name in ("synthesis-wrapper.sv", "shared-queue-selectors.svh", "BUFGCE.v", "glbl.v"):
        require(sha(receipt.parent / name) == sha(original_path.parent / name), "different original queue/model copy " + name)
    require((receipt.parent / "synthesis-wrapper.sv").read_text() == queue.synthesis_wrapper(receipt.parent / "generated") and
            (receipt.parent / "shared-queue-selectors.svh").read_text() == queue.selectors(receipt.parent / "generated"),
            "different independently regenerated queue wrapper/selectors")
    for name in ("BUFGCE.v", "glbl.v"):
        require(doc["vendor_models"][name]["sha256"] == sha(receipt.parent / name), "changed native vendor model " + name)
    for prefix in ("owner", "queue"):
        require((receipt.parent / (prefix + ".tcl")).read_text() == script(prefix == "queue"), "changed synthesis contract")
        with zipfile.ZipFile(receipt.parent / (prefix + ".dcp")) as dcp:
            require(dcp.testzip() is None and "xcvu47p-fsvh2892-2-e" in dcp.read("dcp.xml").decode(), "invalid F2 native DCP")
    queue.audit(receipt.parent / "generated")
    original = (receipt.parent / "synthesis-wrapper.sv").read_text()
    require((receipt.parent / "native-capture-queue.sv").read_text() == native_capture_queue.wrapper(original),
            "changed real queue/hold/request integration")
    require((receipt.parent / "native-capture-queue-tb.sv").read_text() == native_capture_queue.bench(receipt.parent / "generated"),
            "changed complete emitted-register oracle")
    return doc


def receipt_negatives(receipt, sources, out):
    """Reject coherently rehashed source/hold substitutions before any VCS run."""
    rows = []
    for case in ("source-copy", "unsafe-hold", "coherent-wrapper", "selectors", "vendor-model",
                 "incompatible-sources", "truncated"):
        directory = out / case
        directory.mkdir(parents=True)
        original = json.loads(receipt.read_text())
        for name in set(original["inputs"]) | set(original["artifacts"]):
            dest = directory / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(receipt.parent / name, dest)
        doc = json.loads(receipt.read_text())
        if case == "source-copy":
            name = Path(RTL).name
            path = directory / name
            path.write_text(path.read_text() + "\n// coherently rehashed foreign execution copy\n")
            doc["inputs"][name] = sha(path)
        elif case == "unsafe-hold":
            name = "native-capture-queue.sv"
            path = directory / name
            text = path.read_text()
            require(text.count(".functional_hold(capture_hold)") == 1, "ambiguous unsafe-hold mutation")
            path.write_text(text.replace(".functional_hold(capture_hold)", ".functional_hold()"))
            doc["inputs"][name] = sha(path)
        elif case == "incompatible-sources":
            doc["sources"][RTL] = "0" * 64
        elif case == "coherent-wrapper":
            path = directory / "synthesis-wrapper.sv"
            path.write_text(path.read_text() + "\n// foreign original wrapper\n")
            doc["inputs"][path.name] = sha(path)
            path = directory / "native-capture-queue.sv"
            path.write_text(native_capture_queue.wrapper((directory / "synthesis-wrapper.sv").read_text()))
            doc["inputs"][path.name] = sha(path)
        elif case in ("selectors", "vendor-model"):
            path = directory / ("shared-queue-selectors.svh" if case == "selectors" else "BUFGCE.v")
            path.write_text(path.read_text() + "\n// foreign input bytes\n")
            doc["inputs"][path.name] = sha(path)
        path = directory / "summary.json"
        path.write_text(json.dumps(doc, indent=2) + "\n")
        if case == "truncated":
            path.write_bytes(path.read_bytes()[:100])
        try:
            validate_native(path, sources)
        except ValueError as error:
            rows.append(dict(case=case, rejected_before_vcs=True, error=str(error),
                             receipt=str(path), receipt_sha256=sha(path)))
        else:
            require(False, "coherently rehashed incompatible native evidence admitted: " + case)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("vivado", "vcs"), required=True)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--queue-receipt", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), "all evidence belongs beneath runs")
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + "-", dir=args.out.resolve()))
    sources = {n: sha(ROOT / n) for n in SOURCES}
    doc = dict(status="running", backend="f2" if args.mode == "vivado" else "eda", sources=sources,
               scope="common physical/native staging and reader-drain component only",
               source_root=str(ROOT), host=socket.gethostname(), observed_utc=datetime.now(timezone.utc).isoformat(),
               physical_fpga_capture=False, full_image=False, production_owner_integration=False,
               cpu_restore_verified=False, cpu_live_acceptance=False)
    commands = []

    def save():
        (out / "summary.json").write_text(json.dumps(doc, indent=2) + "\n")

    def run(argv, name, *, cwd=out, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(out / (name + ".log")))
        commands.append(row)
        with Path(row["log"]).open("w") as stream:
            result = subprocess.run(row["argv"], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row.update(returncode=result.returncode, log_sha256=sha(row["log"]))
        doc.update(commands=commands, status="running" if result.returncode == expected else "fail")
        save()
        require(result.returncode == expected, "inspect underlying compiler/runtime log " + row["log"])
        return Path(row["log"]).read_text()

    save(); print(out, flush=True)
    if args.mode == "vivado":
        require(ROOT == Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"), "local native Vivado required")
        require(args.queue_receipt is not None and args.native is None, "source-bound queue synthesis required")
        receipt = local(ROOT, str(args.queue_receipt))
        original = json.loads(receipt.read_text())
        require(original["status"] == "pass" and original["backend"] == "f2" and
                original["sources"] == {n: sources[n] for n in queue.SOURCES}, "stale emitted queue receipt")
        for group in ("inputs", "artifacts"):
            for name, digest in original[group].items():
                require(sha(receipt.parent / name) == digest, "changed original queue evidence " + name)
        shutil.copytree(receipt.parent / "generated", out / "generated")
        queue.audit(out / "generated")
        for name in ("synthesis-wrapper.sv", "shared-queue-selectors.svh"):
            shutil.copyfile(receipt.parent / name, out / name)
        vendor = Path(os.environ["XILINX_VIVADO"]) / "data/verilog/src"
        doc["vendor_models"] = {}
        for name, source in (("BUFGCE.v", vendor / "unisims/BUFGCE.v"), ("glbl.v", vendor / "glbl.v")):
            shutil.copyfile(source, out / name)
            doc["vendor_models"][name] = dict(original_path=str(source), sha256=sha(source))
        for n in SOURCES:
            dest = out / "sources" / n; dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / n, dest)
            if n.startswith(VERILOG) or n in (TB, POLICY_TB, EXIT):
                shutil.copyfile(ROOT / n, out / Path(n).name)
        (out / "native-capture-queue.sv").write_text(native_capture_queue.wrapper((out / "synthesis-wrapper.sv").read_text()))
        (out / "native-capture-queue-tb.sv").write_text(native_capture_queue.bench(out / "generated"))
        for prefix in ("owner", "queue"):
            (out / (prefix + ".tcl")).write_text(script(prefix == "queue"))
        doc["queue_receipt"] = dict(path=str(receipt), sha256=sha(receipt), reused_immutable=True)
        doc["inputs"] = {str(p.relative_to(out)): sha(p) for p in out.rglob("*") if p.is_file() and p.name != "summary.json"}
        for prefix in ("owner", "queue"):
            text = run(["vivado", "-mode", "batch", "-source", prefix + ".tcl"], prefix + "-synth")
            require("NATIVE_CAPTURE_SYNTH_PASS" in text and not re.search(r"ERROR:|CRITICAL WARNING:", text), "native synthesis failed")
            timing = (out / (prefix + "-timing.rpt")).read_text()
            require("There are 0 combinational loops in the design." in timing and
                    "There are 0 combinational latch loops" in timing, "native combinational permission/clock loop")
        doc["owner_register_bits"] = 1189
        doc["native_parameters"] = dict(owner=dict(BITS=1036, GATES=3, OWNERS=2),
                                         queue=dict(BITS=1036, GATES=1, OWNERS=2))
    else:
        require(str(ROOT).startswith("/scratch/") and shutil.which("vcs") == toolchain.VCS and
                toolchain.VCS.endswith("Y-2026.03-SP2/bin/vcs"), "EDA native SP2 required")
        require(args.native is not None and args.queue_receipt is None, "exact native receipt required")
        receipt = local(ROOT, str(args.native)); native = validate_native(receipt, sources)
        doc["receipt_negatives"] = receipt_negatives(receipt, sources, out / "receipt-negatives")
        for name in native["inputs"]:
            dest = out / name; dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(receipt.parent / name, dest)
        doc["inputs"] = native["inputs"]
        common = [toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate", "-debug_access+all",
                  "-top", "native_state_capture_tb", "-top", "glbl"]
        rtl = [out / Path(n).name for n in SOURCES if n.startswith(VERILOG)]
        other = [out / "BUFGCE.v", out / "glbl.v", out / Path(EXIT).name]
        doc["wave_audits"] = []
        # Arbitrary raw-state injection is exclusively a component-policy test.
        # Compare the optimized outputs against the unchanged full hierarchical
        # fault network for all binary control combinations, including illegal
        # phases. It must also detect a compiled missing-sticky-error fault.
        policy_common = [toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate",
                         "-debug_access+all", "-top", "native_read_policy_tb", "-top", "glbl"]
        doc["policy_equivalence"] = []
        for mutation in (False, True):
            folder = out / ("policy-missing-error" if mutation else "policy-equivalence"); folder.mkdir()
            policy_rtl = rtl
            if mutation:
                original = (out / Path(RTL).name).read_text()
                needle = "wire read_integrity_fault = |error || |snapshot_sticky_error ||"
                require(original.count(needle) == 1, "ambiguous policy sticky-error mutation")
                broken = folder / "capture.sv"
                broken.write_text(original.replace(needle, "wire read_integrity_fault = |error || 1'b0 ||"))
                policy_rtl = [p for p in rtl if p.name != Path(RTL).name] + [broken]
            label = "policy-missing-error" if mutation else "policy-equivalence"
            run(policy_common + ["-Mdir=" + str(folder / "csrc"), "-o", folder / "simv",
                *policy_rtl, *other, out / Path(POLICY_TB).name], label + "-compile")
            text = run([folder / "simv", "-no_save"], label + "-run", cwd=folder, expected=int(mutation))
            if mutation:
                require("NATIVE_READ_POLICY_DIVERGENCE phase=3" in text and "signal=failed" in text,
                        "missing snapshot sticky-error policy was not rejected in READ")
            else:
                require("NATIVE_READ_POLICY_PASS combinations=131072 comparisons=393216" in text,
                        "incomplete exhaustive native policy equivalence")
            wave = folder / "native-read-policy.vcd"
            require(wave.is_file() and wave.stat().st_size > 0, "missing policy debug waveform")
            doc["policy_equivalence"].append(dict(mutation=mutation, path=str(wave), sha256=sha(wave)))
        for bits in GEOMETRIES:
            folder = out / f"unit-{bits}"; folder.mkdir()
            run(common + [f"+define+CAPTURE_BITS={bits}", "-Mdir=" + str(folder / "csrc"), "-o", folder / "simv",
                *rtl, *other, out / Path(TB).name], f"unit-{bits}-compile")
            for case in ("healthy",) + NEGATIVES:
                text = run([folder / "simv", "-no_save", "+CASE=" + case], f"unit-{bits}-{case}", cwd=folder)
                token = f"NATIVE_CAPTURE_PASS bits={bits} cuts=4 reads={4*((bits+63)//64)} borrows=4" if case == "healthy" else f"NATIVE_CAPTURE_NEGATIVE_PASS case={case} bits={bits} borrows=0 reads=0"
                require(token in text and "DIVERGENCE" not in text, "incomplete native cut coverage")
                wave = folder / (case + ".vcd")
                (folder / "native-state-capture.vcd").rename(wave)
                result = audit(wave, bits)
                require(result["captures"] == (4 if case == "healthy" else
                        0 if case.startswith(("early-", "sample-")) else 1), "wrong independent sample count")
                doc["wave_audits"].append(dict(path=str(wave), sha256=sha(wave), **result))
        folder = out / "queue"; folder.mkdir()
        queue_common = [toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate", "-debug_access+all",
                        "-top", "shared_queue_access_tb", "-top", "glbl", "+incdir+" + str(out)]
        run(queue_common + ["-Mdir=" + str(folder / "csrc"), "-o", folder / "simv", *rtl, *other,
            out / "generated/generated.sv", out / "native-capture-queue.sv", out / "native-capture-queue-tb.sv"], "queue-compile")
        text = run([folder / "simv", "-no_save"], "queue-run", cwd=folder)
        match = re.search(r"NATIVE_CAPTURE_QUEUE_PASS cuts=4 reads=180 words=(\d+) changes=(\d+) target_cycle=(\d+)", text)
        require(match is not None and int(match[1]) > 100 and int(match[2]) > 100, "incomplete actual queue/drain scope")
        doc["queue_serial_words"], doc["queue_live_changes"], doc["queue_final_target_cycle"] = map(int, match.groups())
        labels = re.findall(r"NATIVE_CAPTURE_QUEUE_CUT ordinal=(\d+) target_cycle=(\d+) fields=28 bits=1036 reader_ack_before=(\d+)", text)
        require(len(labels) == 4 and [int(r[0]) for r in labels] == list(range(4)) and
                [int(r[2]) for r in labels] == [0, 45, 90, 135], "missing per-cut original-reader provenance")
        doc["queue_target_cuts"] = [int(r[1]) for r in labels]
        wave = folder / "shared-queue-access.vcd"
        result = audit(wave, 1036, top="shared_queue_access_tb.dut.capture_owner", gates=1)
        require(result["captures"] == 4, "wrong emitted-register preedge sample count")
        doc["wave_audits"].append(dict(path=str(wave), sha256=sha(wave), **result))
        # Compiled semantic mutation must fail at the first complete snapshot,
        # before a borrowed native request or indexed word is acknowledged.
        folder = out / "compiled-corrupt"; folder.mkdir()
        original = (out / "CheckpointNativeStateSnapshot.sv").read_text()
        require(original.count("assign snapshot_state = payload;") == 1, "ambiguous compiled fault")
        (folder / "snapshot.sv").write_text(original.replace("assign snapshot_state = payload;", "assign snapshot_state = payload ^ 1'b1;"))
        broken = [p for p in rtl if p.name != "CheckpointNativeStateSnapshot.sv"] + [folder / "snapshot.sv"]
        run(common + ["+define+CAPTURE_BITS=1036", "-Mdir=" + str(folder / "csrc"), "-o", folder / "simv",
            *broken, *other, out / Path(TB).name], "corrupt-compile")
        text = run([folder / "simv", "-no_save"], "corrupt-run", cwd=folder, expected=1)
        require("signal=every native bit at first preedge snapshot cut=0" in text and "borrows=0 reads=0" in text,
                "semantic corruption did not stop before first acknowledgement")
        rejected = False
        try:
            audit(folder / "native-state-capture.vcd", 1036)
        except ValueError:
            rejected = True
        require(rejected, "independent original-register audit accepted compiled payload fault")
        doc.update(native_receipt=dict(path=str(receipt), sha256=sha(receipt)), geometries=list(GEOMETRIES),
                   negative_processes=len(GEOMETRIES)*len(NEGATIVES), compiled_semantic_fault_rejected_before_ack=True,
                   independent_semantic_fault_rejected=True, queue_reads=180, queue_cuts=4)
    require(sources == {n: sha(ROOT / n) for n in SOURCES}, "source changed during verification")
    doc.update(status="pass", commands=commands, artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob("*")
        if p.is_file() and p.suffix in {".log", ".rpt", ".dcp", ".vcd", ".hex"}})
    save(); print(out / "summary.json", flush=True)


if __name__ == "__main__":
    main()
