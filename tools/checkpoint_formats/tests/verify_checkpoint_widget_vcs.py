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

ROOT = Path(__file__).resolve().parents[3]
GENERATED = (
    "CheckpointNastiAdapter.v", "checkpoint_nasti_adapter_tb.sv", "checkpoint_widget_constants.h",
    "widget/CheckpointCaptureWidget.v", "widget/CheckpointCaptureTransport.sv",
    "widget/CheckpointCaptureCut.sv", "widget/checkpoint_capture_widget_tb.sv",
)
SOURCE = (
    "sims/firesim/sim/build.sbt",
    "sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureWidget.scala",
    "sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureWidgetSpec.scala",
    "sims/firesim/sim/midas/src/test/resources/checkpoint/checkpoint_nasti_adapter_tb.sv",
    "sims/firesim/sim/midas/src/test/resources/checkpoint/checkpoint_capture_widget_tb.sv",
    "sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureTransport.sv",
    "sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureCut.sv",
    "tools/checkpoint_formats/tests/verify_checkpoint_widget_vcs.py",
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
    for name in GENERATED:
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
    generated_hashes = {name: sha(generated / name) for name in GENERATED}
    for group, base, names in (("source-snapshots", ROOT, SOURCE), ("generated-snapshots", generated, GENERATED)):
        for name in names:
            dest = out / group / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((base / name).read_bytes())
    commands = []

    def run(argv, log, cwd):
        commands.append(dict(argv=[str(a) for a in argv], cwd=str(cwd), log=str(log)))
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        with log.open("w") as stream:
            result = subprocess.run(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, text=True)
        commands[-1]["returncode"] = result.returncode
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(result.returncode == 0, f"command failed; inspect {log}")
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
             "-top", top, f"-Mdir={case / 'csrc'}", "-o", str(case / "simv"),
             *[str(out / "generated-snapshots" / source) for source in sources]], case / "compile.log", case)
        text = run([str(case / "simv"), "-no_save"], case / "run.log", case)
        matches = re.findall(marker, text)
        require(len(matches) == 1, f"missing or repeated successful marker for {top}")
        counts = matches[0] if isinstance(matches[0], tuple) else (matches[0],)
        require(int(counts[0]) > 0, f"no checks executed for {top}")
        if name == "widget":
            require(int(counts[1]) == 5, "widget did not transfer exactly header/3words/trailer")
        results[name] = dict(checks=int(counts[0]), marker=matches[0])
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
                              (path.suffix in (".log", ".json", ".sv", ".v", ".scala", ".h", ".py", ".sbt"))})
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(dict(summary=str(out / "summary.json"), results=results,
                          physical_fpga_validated=False, complete_state_ownership=False)))


if __name__ == "__main__":
    main()
