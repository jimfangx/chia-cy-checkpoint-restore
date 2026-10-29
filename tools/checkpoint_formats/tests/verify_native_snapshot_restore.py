"""Synthesize snapshot-owner restore locally; verify fresh processes on EDA.

Images here are directed component fixtures, never hardware .fsckpt/.rtlckpt.
Complete Rocket/global ownership, MMIO/DMA and physical FPGA capture are pending.
"""
import argparse
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
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests.audit_native_snapshot_restore_wave import audit

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "automations/checkpoint_loop/runs"
RTL = "sims/firesim/sim/midas/src/main/verilog/CheckpointNativeStateSnapshot.sv"
TB = "tools/checkpoint_formats/tests/native_snapshot_restore_tb.sv"
EXIT = "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc"
SOURCES = (RTL, TB, EXIT, "tools/checkpoint_formats/tests/verify_native_snapshot_restore.py",
           "tools/checkpoint_formats/tests/audit_native_snapshot_restore_wave.py",
           "tools/checkpoint_formats/toolchain.py", "tools/checkpoint_formats/codec.py")
GEOMETRIES = (1, 64, 65, 130, 1036, 1664)
CUTS = ("empty", "occupied", "released", "error", "preborrow")
NEGATIVES = ("held-request", "held-release", "held-borrow", "held-busy", "held-owner", "held-freeze",
             "unheld-load", "unpark-drift", "unpark-owner", "unpark-freeze", "held-overlap", "held-borrow-busy")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wrapper():
    text = (ROOT / RTL).read_text()
    ports = text.split(") (\n", 1)[1].split("\n);", 1)[0]
    ports = re.sub(r"\bBITS\b", "1036", ports).replace("output reg", "output wire")
    return ("module NativeSnapshotRestoreTop (\n" + ports + "\n);\n"
            "CheckpointNativeStateSnapshot #(.BITS(1036),.RESTORE_ENABLE(1)) owner(.*);\nendmodule\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("vivado", "vcs"), required=True)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--queue-captures", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), "evidence beneath runs required")
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + "-", dir=args.out.resolve()))
    sources = {name: sha(ROOT / name) for name in SOURCES}
    commands = []
    doc = dict(status="running", backend="f2" if args.mode == "vivado" else "eda", sources=sources,
               scope="native snapshot staging/control owner only; directed fixture donor",
               physical_fpga_capture=False, full_image=False, complete_capture_owner=False,
               metasim_restore_supported=False, host=socket.gethostname(), source_root=str(ROOT),
               observed_utc=datetime.now(timezone.utc).isoformat())

    def save():
        (out / "summary.json").write_text(json.dumps(doc, indent=2) + "\n")

    def run(argv, name, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(out), log=str(out / (name + ".log")))
        commands.append(row)
        with Path(row["log"]).open("w") as log:
            result = subprocess.run(row["argv"], cwd=out, stdout=log, stderr=subprocess.STDOUT)
        row.update(returncode=result.returncode, log_sha256=sha(row["log"]))
        doc.update(commands=commands, status="running" if result.returncode == expected else "fail")
        save()
        require(result.returncode == expected, "inspect underlying compiler/runtime log " + row["log"])
        return Path(row["log"]).read_text()

    save()
    print(out, flush=True)
    if args.mode == "vivado":
        require(ROOT == Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"),
                "native localhost synthesis required")
        require(args.native is None, "native input only on EDA")
        for name in SOURCES:
            dest = out / "sources" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        (out / "wrapper.sv").write_text(wrapper())
        (out / "synth.tcl").write_text("""set_param general.maxThreads 4
read_verilog -sv sources/sims/firesim/sim/midas/src/main/verilog/CheckpointNativeStateSnapshot.sv wrapper.sv
synth_design -top NativeSnapshotRestoreTop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set registers [get_cells -hier -filter {NAME =~ owner/* && REF_NAME =~ FD*}]
if {[llength $registers] != 1107} {error "incomplete restore-owner storage: [llength $registers]"}
puts "SNAPSHOT_RESTORE_STORAGE bits=1107 payload=1036 occupied=1 cycle=64 error=6"
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force snapshot-restore.dcp
puts "SNAPSHOT_RESTORE_SYNTH_PASS"
""")
        doc["inputs"] = {str(p.relative_to(out)): sha(p) for p in out.rglob("*")
                         if p.is_file() and p.name != "summary.json"}
        log = run(["vivado", "-mode", "batch", "-source", "synth.tcl"], "synth")
        require("SNAPSHOT_RESTORE_SYNTH_PASS" in log and not re.search(r"ERROR:|CRITICAL WARNING:", log),
                "native restore-owner synthesis failed")
        doc["staging_register_bits"] = 1107
    else:
        require(str(ROOT).startswith("/scratch/") and shutil.which("vcs") == toolchain.VCS and
                toolchain.VCS.endswith("Y-2026.03-SP2/bin/vcs"), "EDA native SP2 required")
        require(args.native is not None, "explicit source-bound native receipt required")
        receipt = local(ROOT, str(args.native))
        native = json.loads(receipt.read_text())
        require(native["status"] == "pass" and native["backend"] == "f2" and native["sources"] == sources,
                "stale native restore-owner receipt")
        for group in ("inputs", "artifacts"):
            for name, digest in native[group].items():
                require(sha(receipt.parent / name) == digest, "changed native restore evidence " + name)
        for name in native["inputs"]:
            dest = out / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(receipt.parent / name, dest)
        require((out / "wrapper.sv").read_text() == wrapper(), "changed native restore wrapper")
        doc["inputs"] = native["inputs"]
        common = [toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate", "-debug_access+all",
                  "-top", "native_snapshot_restore_tb"]
        doc["images"] = []
        doc["wave_audits"] = []
        for bits in GEOMETRIES:
            folder = out / f"unit-{bits}"
            folder.mkdir()
            simv = folder / "simv"
            run(common + [f"+define+SNAPSHOT_BITS={bits}", "-Mdir=" + str(folder / "csrc"), "-o", simv,
                out / "sources" / RTL, out / "sources" / TB, out / "sources" / EXIT], f"unit-{bits}-compile")
            for cut in CUTS:
                image = folder / (cut + ".hex")
                argv = [simv, "-no_save", "+CUT=" + cut, "+IMAGE=" + str(image)]
                text = run(argv + ["+MODE=donor"], f"unit-{bits}-{cut}-donor")
                require(f"RESTORE_DONOR_PASS bits={bits} cut={cut} " in text, "missing independent donor")
                require(re.fullmatch(r"[0-9a-f]+\n", image.read_text()) is not None and
                        len(image.read_text().strip()) == (bits + 74)//4, "incomplete/unknown donor image")
                shutil.move(out / "native-snapshot-restore.vcd", folder / (cut + "-donor.vcd"))
                text = run(argv + ["+MODE=restore"], f"unit-{bits}-{cut}-restore")
                require(f"RESTORE_PASS bits={bits} cut={cut} " in text and
                        "raw_continuation=128 target_edges=0" in text and "DIVERGENCE" not in text,
                        "incomplete fresh-process state/continuation")
                shutil.move(out / "native-snapshot-restore.vcd", folder / (cut + "-restore.vcd"))
                doc["wave_audits"].append(dict(path=str(folder / (cut + "-restore.vcd")),
                                             **audit(folder / (cut + "-restore.vcd"), bits)))
                doc["images"].append(dict(bits=bits, cut=cut, path=str(image), sha256=sha(image)))
            text = run([simv, "-no_save", "+MODE=restore", "+CUT=occupied", "+CASE=bit-coverage",
                        "+IMAGE=" + str(folder / "occupied.hex")], f"unit-{bits}-bit-coverage")
            require(f"RESTORE_BIT_COVERAGE_PASS bits={bits} owner_bits={bits+71} loads={2*(bits+71)} " in text,
                    "incomplete every-bit owner restore")
            wave = folder / "bit-coverage.vcd"
            shutil.move(out / "native-snapshot-restore.vcd", wave)
            doc["wave_audits"].append(dict(path=str(wave), **audit(wave, bits, loads=2*(bits+71)+1)))
            for case in NEGATIVES:
                text = run([simv, "-no_save", "+MODE=restore", "+CUT=occupied", "+CASE=" + case,
                            "+IMAGE=" + str(folder / "occupied.hex")], f"unit-{bits}-{case}")
                require(f"RESTORE_NEGATIVE_PASS bits={bits} case={case} " in text and "DIVERGENCE" not in text,
                        "unsafe restore did not reject before acknowledgement")
                shutil.move(out / "native-snapshot-restore.vcd", folder / (case + ".vcd"))
                doc["wave_audits"].append(dict(path=str(folder / (case + ".vcd")),
                                             **audit(folder / (case + ".vcd"), bits, loads=2)))
        # Restore the staged controls from all four actual emitted-queue cuts,
        # independently executed with both the underlying and gated wrappers.
        require(args.queue_captures is not None, "current emitted-queue capture receipt required")
        from tools.checkpoint_formats.tests.verify_native_state_snapshot import SOURCES as QUEUE_SOURCES
        queue_receipt = local(ROOT, str(args.queue_captures))
        queue_doc = json.loads(queue_receipt.read_text())
        require(queue_doc["status"] == "pass" and queue_doc["backend"] == "eda" and
                queue_doc["sources"] == {n: sha(ROOT / n) for n in QUEUE_SOURCES}, "stale emitted-queue captures")
        for name, digest in queue_doc["artifacts"].items():
            require(sha(queue_receipt.parent / name) == digest, "changed emitted-queue capture evidence")
        queue_images = sorted(n for n in queue_doc["artifacts"] if re.fullmatch(
            r"queue-(healthy|gated)/native-queue-cut[0-3]\.hex", n))
        require(len(queue_images) == 8, "all eight emitted-queue staging cuts required")
        doc["queue_restores"] = []
        for i, name in enumerate(queue_images):
            image = out / (f"emitted-queue-{i}.hex")
            shutil.copyfile(queue_receipt.parent / name, image)
            require(re.fullmatch(r"[0-9a-f]{277}\n", image.read_text()) is not None,
                    "incomplete/unknown emitted-queue owner; never mask state bits")
            text = run([out / "unit-1036/simv", "-no_save", "+MODE=restore", "+CUT=queue",
                        "+IMAGE=" + str(image)], f"emitted-queue-{i}-restore")
            require("RESTORE_PASS bits=1036 cut=queue " in text and "DIVERGENCE" not in text,
                    "fresh emitted-queue staging restore failed")
            shutil.move(out / "native-snapshot-restore.vcd", out / f"emitted-queue-{i}.vcd")
            doc["wave_audits"].append(dict(path=str(out / f"emitted-queue-{i}.vcd"),
                                         **audit(out / f"emitted-queue-{i}.vcd", 1036)))
            doc["queue_restores"].append(dict(donor_artifact=name, path=str(image), sha256=sha(image)))
        doc["queue_capture_receipt"] = dict(path=str(queue_receipt), sha256=sha(queue_receipt))
        # Mutate the compiled restore datapath, keeping donor bytes and oracle
        # unchanged. Stop at the complete readback before a single word ack.
        text = (ROOT / RTL).read_text()
        needle = "payload <= restore_state[BITS-1:0];"
        require(text.count(needle) == 1, "ambiguous compiled restore mutation")
        bad = out / "corrupt.sv"
        bad.write_text(text.replace(needle, "payload <= restore_state[BITS-1:0] ^ 1'b1;"))
        run(common + ["+define+SNAPSHOT_BITS=1036", "-Mdir=" + str(out / "corrupt-csrc"),
            "-o", out / "corrupt-simv", bad, out / "sources" / TB, out / "sources" / EXIT], "corrupt-compile")
        text = run([out / "corrupt-simv", "-no_save", "+MODE=restore", "+CUT=occupied",
                    "+IMAGE=" + str(out / "unit-1036/occupied.hex")], "corrupt-run", expected=1)
        require("signal=complete-control-before-target bits=1036 cut=occupied case=healthy target_edges=0 ack=0 reads=0" in text,
                "compiled semantic corruption escaped first independent readback")
        shutil.move(out / "native-snapshot-restore.vcd", out / "corrupt.vcd")
        doc["wave_audits"].append(dict(path=str(out / "corrupt.vcd"), **audit(out / "corrupt.vcd", 1036, broken=True)))
        doc.update(native_receipt=dict(path=str(receipt), sha256=sha(receipt)),
                   geometries=list(GEOMETRIES), donor_processes=30, fresh_restore_processes=30,
                   negative_processes=len(GEOMETRIES)*len(NEGATIVES),
                   per_bit_loads=sum(2*(bits+71) for bits in GEOMETRIES),
                   compiled_semantic_fault_rejected_before_ack=True, cpu_live_acceptance=False)
    require(sources == {n: sha(ROOT / n) for n in SOURCES}, "sources changed during verification")
    doc.update(status="pass", commands=commands, artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob("*")
        if p.is_file() and p.suffix in {".log", ".rpt", ".dcp", ".vcd", ".hex"}})
    save()
    print(out / "summary.json", flush=True)


if __name__ == "__main__":
    main()
