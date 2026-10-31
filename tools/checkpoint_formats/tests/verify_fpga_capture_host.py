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
    ROOT / "tools/checkpoint_formats/tests/native_capture_install_host.cc",
    CC / "core/bridge_driver.cc", CC / "core/widget.cc", CC / "core/stream_engine.cc",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--generated-native-header", type=Path,
                        help="also compile the actual native widget's generated constructor")
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
    install_options = []
    generated_native_header = None
    if args.generated_native_header:
        header = args.generated_native_header.resolve()
        text = header.read_text()
        require("#error Incomplete_checkpoint_hardware_coverage" in text,
                "native generated header lost incomplete-owner admission guard")
        constructors = re.findall(r"#ifdef GET_BRIDGE_CONSTRUCTOR\n(.*?)#endif", text, re.S)
        constructors = [body for body in constructors if "checkpoint_native_capture_binding_t" in body]
        require(len(constructors) == 1 and "registry.add_widget(new checkpoint_capture_t" in constructors[0],
                "one actual generated native installation required")
        (snapshots / "generated-native-header.h").write_bytes(header.read_bytes())
        (out / "native_constructor.h").write_text(constructors[0])
        generated_native_header = dict(path=str(header), sha256=hashlib.sha256(header.read_bytes()).hexdigest())
        install_options = ["-DCHECKPOINT_NATIVE_GENERATED_CONSTRUCTOR", "-I" + str(out)]
    run([*common, *install_options, CC / "core/checkpoint_capture.cc",
         CC / "bridges/checkpoint_capture.cc", CC / "core/bridge_driver.cc",
         CC / "core/widget.cc", CC / "core/stream_engine.cc",
         ROOT / "tools/checkpoint_formats/tests/native_capture_install_host.cc",
         "-o", out / "native-install-host"], "install-build.log")
    installation = run([out / "native-install-host"], "install-run.log")
    install_match = re.search(r"NATIVE_CAPTURE_INSTALL_HOST_PASS checks=(\d+) negatives=31 no_io=1", installation)
    require(install_match is not None, "native driver installation/no-I/O rejection matrix did not finish")
    run(["ldd", out / "capture-host"], "native-libraries.log")
    result = run([out / "capture-host", transport / "frames.bin", out / "manifest.txt", str(cycle)],
                 "native-run.log")
    match = re.search(r"CHECKPOINT_CAPTURE_HOST_PASS checks=(\d+)", result)
    require(match is not None, "host capture session did not finish")
    require("CHECKPOINT_WIDGET_SHADOW_HOST_PASS widths=2 captures=4 failures=13" in result,
            "host shadow capture/failure/recovery cases did not finish")
    require("CHECKPOINT_NATIVE_BOUND_SHADOW_HOST_PASS captures=8 bound_width_rejections=16 max_bits=71455" in result,
            "native identity-bound shadow captures/width rejections did not finish")
    retry = re.search(r"CHECKPOINT_WIDGET_SHADOW_RETRY_PASS widths=3 retried=(\d+) "
                      r"rejected=(\d+) operations=(\d+) repeated=1 invalid=26", result)
    require(retry is not None and int(retry[1]) > 600 and int(retry[2]) > 40 and
            int(retry[1]) + int(retry[2]) == 2 * int(retry[3]),
            "incomplete interrupted MMIO operation matrix or immutable-epoch recovery")
    receipt = dict(observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   source_root=str(ROOT), backend="eda", status="pass",
                   scope="ASan/UBSan host transport session and fresh VCS component frames; no hardware CPU acceptance",
                   checks=int(match[1]), target_cut=cycle, transport_summary=str(summaries[0]),
                   native_install=dict(checks=int(install_match[1]), no_io=True, negatives=31,
                                       generated_header=generated_native_header),
                   source_sha256=hashes, commands=commands,
                   frame_sha256=hashlib.sha256(frames).hexdigest(),
                   shadow_retry=dict(widths=[1169, 1242, 1245], retried=int(retry[1]),
                                     rejected=int(retry[2]), operations=int(retry[3]),
                                     repeated_interruptions=1, invalid_epoch_rejections=26),
                   remaining="complete generated network, memory/host-owner capture, runtime registration, F2 image/deployment/capture/migration")
    (out / "summary.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(out / "summary.json")


if __name__ == "__main__":
    main()
