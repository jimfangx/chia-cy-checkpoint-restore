"""EDA sanitizer host capture session against fresh VCS public-port frames.

The VCS stream is a component fixture, never an FPGA/CPU capture receipt.
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
import sys
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require

ROOT = Path(__file__).resolve().parents[3]
CC = ROOT / "sims/firesim/sim/midas/src/main/cc"
SOURCES = [
    CC / "core/checkpoint_capture.h", CC / "core/checkpoint_capture.cc",
    CC / "bridges/checkpoint_capture.h", CC / "bridges/checkpoint_capture.cc",
    ROOT / "tools/checkpoint_formats/tests/checkpoint_capture_host.cc",
    Path(__file__).resolve(),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(Path(toolchain.VCS).is_file() and os.environ.get("VCS_HOME") == toolchain.VCS_HOME,
            "run on EDA with vcs-env.sh sourced LAST")
    root = args.out.resolve()
    require(root.is_relative_to(ROOT / "automations/checkpoint_loop/runs"), "evidence outside runs")
    root.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="capture-host-", dir=root))
    snapshots = out / "source-snapshots"
    snapshots.mkdir()
    hashes = {}
    for source in SOURCES:
        hashes[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
        (snapshots / (source.parent.name + "-" + source.name)).write_bytes(source.read_bytes())
    commands = []

    def run(argv, log):
        command = dict(argv=[str(arg) for arg in argv], cwd=str(ROOT), log=str(out / log))
        commands.append(command)
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        with (out / log).open("w") as stream:
            result = subprocess.run(command["argv"], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        command["returncode"] = result.returncode
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(result.returncode == 0, f"command failed; inspect {out / log}")
        return (out / log).read_text()

    run([sys.executable, "-m", "tools.checkpoint_formats.tests.verify_fpga_transport_vcs",
         "--out", out / "transport"], "transport-command.log")
    summaries = list((out / "transport").glob("transport-*/summary.json"))
    require(len(summaries) == 1, "ambiguous fresh transport receipt")
    transport = summaries[0].parent
    manifest = json.loads((transport / "manifest.json").read_text())
    binding = json.loads((transport / "binding.json").read_text())
    frames = (transport / "frames.bin").read_bytes()
    cycle = int.from_bytes(frames[12:20], "little")
    from tools.checkpoint_formats.semantic import manifest_hash
    wire_hash = int(manifest_hash(manifest), 16).to_bytes(32, "little")
    metadata = " ".join(str(byte) for byte in wire_hash) + "\n" + str(len(binding["state"])) + "\n"
    metadata += "".join(f"{entry['bank']} {entry['slot']} {entry['width']} {entry['depth']}\n"
                        for entry in binding["state"])
    (out / "manifest.txt").write_text(metadata)
    common = [os.environ["CXX"], "-std=c++17", "-Wall", "-Wextra", "-Werror",
              "-Wno-unused-parameter", "-g", "-O1", "-fno-omit-frame-pointer",
              "-fsanitize=address,undefined", "-I" + str(CC)]
    run([*common, CC / "core/checkpoint_capture.cc", SOURCES[4],
         "-o", out / "capture-host"], "native-build.log")
    # The production StreamEngine/MMIO binding compiles against actual headers;
    # runtime integration is deliberately unavailable until complete owners exist.
    run([*common, "-c", CC / "bridges/checkpoint_capture.cc", "-o", out / "capture-driver.o"],
        "driver-build.log")
    run(["ldd", out / "capture-host"], "native-libraries.log")
    result = run([out / "capture-host", transport / "frames.bin", out / "manifest.txt", str(cycle)],
                 "native-run.log")
    match = re.search(r"CHECKPOINT_CAPTURE_HOST_PASS checks=(\d+)", result)
    require(match is not None, "host capture session did not finish")
    require("CHECKPOINT_WIDGET_SHADOW_HOST_PASS widths=2 captures=4 failures=13" in result,
            "host shadow capture/failure/recovery cases did not finish")
    receipt = dict(observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   source_root=str(ROOT), backend="eda", status="pass",
                   scope="ASan/UBSan host transport session and fresh VCS component frames; no hardware CPU acceptance",
                   checks=int(match[1]), target_cut=cycle, transport_summary=str(summaries[0]),
                   source_sha256=hashes, commands=commands,
                   frame_sha256=hashlib.sha256(frames).hexdigest(),
                   remaining="complete generated network, memory/host-owner capture, runtime registration, F2 image/deployment/capture/migration")
    (out / "summary.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(out / "summary.json")


if __name__ == "__main__":
    main()
