"""EDA-only native VCS checks of Scala-generated checkpoint Widget and NASTI adapter.

Elaborate CheckpointCaptureWidgetSpec first with -Dcheckpoint.widget.out=DIR.
Run this module through automations/checkpoint_loop/eda.py after sourcing
vcs-env.sh last. These are finite component checks, never FPGA/CPU acceptance.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_widget_shadow import audit as audit_shadow

ROOT = Path(__file__).resolve().parents[3]
EXIT = "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc"
GENERATED = (
    "CheckpointNastiAdapter.v", "checkpoint_nasti_adapter_tb.sv", "checkpoint_widget_constants.h",
    "widget/CheckpointCaptureWidget.v", "widget/CheckpointCaptureTransport.sv",
    "widget/CheckpointCaptureCut.sv", "widget/checkpoint_capture_widget_tb.sv",
)
STANDALONE = tuple(f"live-snapshot/{bits}/CheckpointLiveWidgetSnapshot.v" for bits in (1169, 1242))
ADAPTERS = tuple(f"adapter-state/{a}-{i}/CheckpointNastiAdapter.v" for a,i in ((8,1),(32,4),(64,64)))
SOURCE = (
    "sims/firesim/sim/build.sbt",
    "sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureWidget.scala",
    "sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureWidgetSpec.scala",
    "sims/firesim/sim/midas/src/test/resources/checkpoint/checkpoint_nasti_adapter_tb.sv",
    "sims/firesim/sim/midas/src/test/resources/checkpoint/checkpoint_capture_widget_tb.sv",
    "sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureTransport.sv",
    "sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureCut.sv",
    "tools/checkpoint_formats/tests/verify_checkpoint_widget_vcs.py",
    "sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointLiveWidgetSnapshot.scala",
    "sims/firesim/sim/midas/src/main/scala/midas/checkpoint/CheckpointTransportControlState.scala",
    "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc",
    "tools/checkpoint_formats/tests/audit_widget_shadow.py",
    "tools/checkpoint_formats/tests/verify_transport_control_state.py",
    "sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalCaptureTransport.sv",
    "sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalClockCut.sv",
    "sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureSnapshotSpec.scala",
    "sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointNastiState.scala",
    'sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureNastiStateSpec.scala',
    "tools/checkpoint_formats/tests/checkpoint_nasti_state_tb.sv",
    "tools/checkpoint_formats/tests/live_widget_snapshot_tb.sv",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    require(Path(toolchain.VCS).is_file() and os.environ.get("VCS_HOME") == toolchain.VCS_HOME,
            "source vcs-env.sh LAST on EDA; use eda.py for routing")
    generated = args.generated.resolve()
    root = args.out.resolve()
    require(root.is_relative_to(ROOT / "automations/checkpoint_loop/runs"), "evidence must be beneath runs/")
    for name in (*GENERATED, *STANDALONE, *ADAPTERS):
        require((generated / name).is_file() and (generated / name).stat().st_size > 0,
                f"missing Scala-generated artifact: {name}")
    # Refuse stale resource/fixture copies rather than testing a different adapter.
    for name, source in (
        ("widget/CheckpointCaptureTransport.sv", SOURCE[5]),
        ("widget/CheckpointCaptureCut.sv", SOURCE[6]),
        ("checkpoint_nasti_adapter_tb.sv", SOURCE[3]),
        ("widget/checkpoint_capture_widget_tb.sv", SOURCE[4]),
    ):
        require(sha(generated / name) == sha(ROOT / source), f"stale generated resource: {name}")
    root.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="widget-", dir=root))
    hashes = {name: sha(ROOT / name) for name in SOURCE}
    generated_hashes = {name: sha(generated / name) for name in (*GENERATED, *STANDALONE, *ADAPTERS)}
    for group, base, names in (("source-snapshots", ROOT, SOURCE), ("generated-snapshots", generated, (*GENERATED, *STANDALONE, *ADAPTERS))):
        for name in names:
            dest = out / group / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((base / name).read_bytes())
    commands = []

    def run(argv, log, cwd, expected=0):
        commands.append(dict(argv=[str(a) for a in argv], cwd=str(cwd), log=str(log)))
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        with log.open("w") as stream:
            result = subprocess.run(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, text=True)
        commands[-1]["returncode"] = result.returncode
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(result.returncode == expected, f"command failed; inspect {log}")
        return log.read_text()

    cases = (
        ("adapter", "checkpoint_nasti_adapter_tb", (GENERATED[0], GENERATED[1]),
         r"CHECKPOINT_NASTI_PASS checks=(\d+)"),
        ("widget", "checkpoint_capture_widget_tb", tuple(GENERATED[3:]),
         r"CHECKPOINT_WIDGET_PASS checks=(\d+) frames=(\d+)"),
    )
    results = {}
    for name, top, sources, marker in cases:
        case = out / name
        case.mkdir()
        run([toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate",
             "-debug_access+all",
             "-top", top, f"-Mdir={case / 'csrc'}", "-o", str(case / "simv"),
             *[str(out / "generated-snapshots" / source) for source in sources],
             str(ROOT / EXIT)], case / "compile.log", case)
        text = run([str(case / "simv"), "-no_save"], case / "run.log", case)
        matches = re.findall(marker, text)
        require(len(matches) == 1, f"missing or repeated successful marker for {top}")
        counts = matches[0] if isinstance(matches[0], tuple) else (matches[0],)
        require(int(counts[0]) > 0, f"no checks executed for {top}")
        if name == "widget":
            require(int(counts[1]) == 5, "widget did not transfer exactly header/3words/trailer")
            require("CHECKPOINT_WIDGET_SHADOW_PASS captures=1 words=57" in text,
                    "missing complete immutable transport/local readback")
        results[name] = dict(checks=int(counts[0]), marker=matches[0])
    for (addr, ident), source in zip(((8,1),(32,4),(64,64)), ADAPTERS):
        work = out / f"adapter-{addr}-{ident}"
        work.mkdir()
        run([toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate",
             "-debug_access+all", f"+define+NASTI_ADDR_BITS={addr}", f"+define+NASTI_ID_BITS={ident}",
             "-top", "checkpoint_nasti_state_tb", f"-Mdir={work / 'csrc'}", "-o", str(work / "simv"),
             str(out / "generated-snapshots" / source), str(ROOT / SOURCE[-2]), str(ROOT / EXIT)],
             work / "compile.log", work)
        text = run([str(work / "simv"), "-no_save"], work / "run.log", work)
        match = re.search(rf"CHECKPOINT_NASTI_STATE_PASS addr={addr} id={ident} state_checks=(\d+) random_steps=3000",text)
        require(match is not None and int(match[1]) > 3000, "incomplete canonical adapter state comparison")
        results[f"adapter_{addr}_{ident}"] = dict(state_checks=int(match[1]), random_steps=3000)
    # Corrupt the synthesized observation logic, independently of the source
    # register oracle. The first initialized observation must reject it.
    work = out / "adapter-corruption"
    work.mkdir()
    source = (out / "generated-snapshots" / ADAPTERS[-1]).read_text()
    site = re.compile(r"(assign io_controlState = )([^;]+);",re.S)
    require(len(site.findall(source)) == 1,"ambiguous adapter observation corruption site")
    (work / "adapter.v").write_text(site.sub(lambda m:m[1]+"("+m[2]+") ^ 530'h8000000000000000;",source))
    run([toolchain.VCS,"-full64","-sverilog","-timescale=1ns/1ps","-Mupdate","-debug_access+all",
         "+define+NASTI_ADDR_BITS=64","+define+NASTI_ID_BITS=64","-top","checkpoint_nasti_state_tb",
         f"-Mdir={work / 'csrc'}","-o",str(work / "simv"),str(work / "adapter.v"),
         str(ROOT / SOURCE[-2]),str(ROOT / EXIT)],work / "compile.log",work)
    text = run([str(work / "simv"),"-no_save"],work / "run.log",work,expected=1)
    require("NASTI_STATE_DIVERGENCE complete canonical original register vector" in text and
            "CHECKPOINT_NASTI_STATE_PASS" not in text,"compiled adapter corruption escaped original register oracle")
    results["adapter_corruption"] = dict(returncode=1,corrupt_signal="aw_addr[63]")
    # Compile an actual bad staging bank. The independent MMIO oracle must
    # stop on the first differing word while the AXI read remains unacknowledged.
    bad = out / "shadow-corruption"
    bad.mkdir()
    original = (out / "generated-snapshots/widget/CheckpointCaptureWidget.v").read_text()
    require(original.count("saved <= io_live;") == 1, "ambiguous snapshot corruption site")
    (bad / "widget.v").write_text(original.replace("saved <= io_live;", "saved <= io_live ^ 1169'h1;"))
    run([toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate",
         "-debug_access+all", "-top", "checkpoint_capture_widget_tb",
         f"-Mdir={bad / 'csrc'}", "-o", str(bad / "simv"), str(bad / "widget.v"),
         *[str(out / "generated-snapshots" / n) for n in GENERATED[4:]], str(ROOT / EXIT)],
        bad / "compile.log", bad)
    text = run([str(bad / "simv"), "-no_save"], bad / "run.log", bad, expected=1)
    require("WIDGET_DIVERGENCE cut=42 word=0 reason=read data" in text and
            "CHECKPOINT_WIDGET_PASS" not in text, "wrong first shadow divergence")
    results["shadow_corruption"] = dict(word=0, component_cut=42, returncode=1)
    results["shadow_waves"] = {
        "healthy": audit_shadow(out / "widget/checkpoint-widget.vcd"),
        "corrupt": audit_shadow(bad / "checkpoint-widget.vcd", corrupt=True),
    }
    for bits, source in zip((1169, 1242), STANDALONE):
        work = out / str(bits)
        work.mkdir()
        run([toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate",
             "-debug_access+all", f"+define+SHADOW_BITS={bits}", "-top", "live_widget_snapshot_tb",
             f"-Mdir={work / 'csrc'}", "-o", str(work / "simv"),
             str(out / "generated-snapshots" / source), str(ROOT / SOURCE[-1]), str(ROOT / EXIT)],
            work / "compile.log", work)
        text = run([str(work / "simv"), "-no_save"], work / "run.log", work)
        match = re.search(rf"LIVE_WIDGET_SNAPSHOT_PASS bits={bits} captures=65 words=(\d+) checks=(\d+)", text)
        require(match is not None and int(match[1]) == 128 * ((bits + 63) // 64),
                "incomplete complete-width shadow protocol regression")
        results[str(bits)] = dict(captures=65, words=int(match[1]), checks=int(match[2]))
    require(all(sha(ROOT / name) == digest for name, digest in hashes.items()), "source changed during execution")
    require(all(sha(generated / name) == digest for name, digest in generated_hashes.items()),
            "generated RTL changed during execution")
    summary = dict(observed_utc=datetime.now(timezone.utc).isoformat(), backend="eda",
                   hostname=socket.gethostname(), remote_root=str(ROOT), tool=toolchain.VCS,
                   scope="Scala-generated global Widget/NASTI/stream components; fixture bank only",
                   physical_fpga_validated=False, rocket_image_integrated=False,
                   complete_state_ownership=False, results=results,
                   source_sha256=hashes, generated_sha256=generated_hashes,
                   artifacts={str(path.relative_to(out)): dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)
                              for path in out.rglob("*") if path.is_file() and
                              (path.suffix in (".log", ".json", ".sv", ".v", ".scala", ".h", ".py", ".sbt", ".vcd"))})
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(dict(summary=str(out / "summary.json"), results=results,
                          physical_fpga_validated=False, complete_state_ownership=False)))


if __name__ == "__main__":
    main()
