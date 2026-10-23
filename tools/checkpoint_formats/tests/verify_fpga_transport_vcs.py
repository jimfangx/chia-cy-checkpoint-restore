"""Fresh EDA-only VCS transport component and strict host integrity checks."""
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
from tools.checkpoint_formats.fpga_transport import decode_frames, encode_transport_semantic
from tools.checkpoint_formats.semantic import decode_semantic, manifest_hash, state_id
from tools.checkpoint_formats.tests.test_fpga_transport import negative_checks

ROOT = Path(__file__).resolve().parents[3]
SOURCES = [
    "sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureCut.sv",
    "sims/firesim/sim/midas/src/main/verilog/CheckpointCaptureTransport.sv",
    "tools/checkpoint_formats/tests/checkpoint_transport_tb.sv",
    "tools/checkpoint_formats/fpga_transport.py",
    "tools/checkpoint_formats/tests/test_fpga_transport.py",
    "tools/checkpoint_formats/tests/verify_fpga_transport_vcs.py",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture():
    # This manifest describes a component oracle, never a Rocket inventory.
    entries = [dict(state_id=state_id(f"TransportFixture.dut.bank{i}", "memory"),
                    hierarchy=f"TransportFixture.dut.bank{i}", kind="memory", width=1,
                    depth=1, signed=False, clock_domain="TransportFixture.dut.clock",
                    reset="none", bit_order="lsb0", address_order="ascending_zero_based")
               for i in range(3)]
    entries.sort(key=lambda entry: entry["state_id"])
    for entry, width, depth in zip(entries, (9, 64, 1), (3, 1, 2)):
        entry.update(width=width, depth=depth)
    manifest = dict(manifest_version=1, manifest_type="rtlckpt", identity_scheme="pre-fame-state-v1",
                    circuit="TransportFixture", dut_root="TransportFixture.dut",
                    clock_domain="TransportFixture.dut.clock",
                    reference_sha256=sha(ROOT / SOURCES[2]), state=entries)
    binding = dict(access_version=1, protocol="banked64-v1", dut_root=manifest["dut_root"],
                   state_manifest_sha256=manifest_hash(manifest),
                   state=[dict(state_id=e["state_id"], bank=i+1, slot=(2,17,7)[i],
                               width=e["width"], depth=e["depth"])
                          for i, e in enumerate(entries)])
    return manifest, binding


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    require(Path(toolchain.VCS).is_file() and os.environ.get("VCS_HOME") == toolchain.VCS_HOME,
            "source vcs-env.sh LAST on EDA")
    root = args.out.resolve()
    require(root.is_relative_to(ROOT / "automations/checkpoint_loop/runs"), "evidence must be beneath runs/")
    root.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="transport-", dir=root))
    (out / "source-snapshots").mkdir()
    hashes = {}
    for name in SOURCES:
        path = ROOT / name
        hashes[name] = sha(path)
        (out / "source-snapshots" / path.name).write_bytes(path.read_bytes())
    manifest, binding = fixture()
    for name, doc in (("manifest.json",manifest),("binding.json",binding)):
        (out / name).write_text(json.dumps(doc,indent=2)+"\n")
    commands = []

    def run(argv, log):
        commands.append(dict(argv=[str(a) for a in argv], cwd=str(ROOT), log=str(out / log)))
        (out / "commands.json").write_text(json.dumps(commands,indent=2)+"\n")
        with (out / log).open("w") as stream:
            result = subprocess.run(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, text=True)
        commands[-1]["returncode"] = result.returncode
        (out / "commands.json").write_text(json.dumps(commands,indent=2)+"\n")
        require(result.returncode == 0, f"command failed; inspect {out / log}")
        return (out / log).read_text()

    run([toolchain.VCS,"-full64","-sverilog","-timescale=1ns/1ps","-Mupdate",
         "-top","checkpoint_transport_tb", f"+define+CHECKPOINT_TRANSPORT_MANIFEST_HASH=256'h{manifest_hash(manifest)}",
         f"-Mdir={out / 'csrc'}","-o",str(out / "simv"),
         *[str(ROOT / name) for name in SOURCES[:3]]], "compile.log")
    text = run([str(out / "simv"),"-no_save",f"+frames={out / 'frames.hex'}"],"run.log")
    match = re.search(r"CHECKPOINT_TRANSPORT_PASS checks=(\d+) captures=(\d+) requests=(\d+) dma_stalls=(\d+) mmio_stalls=(\d+)",text)
    require(match is not None,"component simulation did not pass")
    raw = b"".join(int(row,16).to_bytes(64,"little") for row in (out / "frames.hex").read_text().splitlines())
    (out / "frames.bin").write_bytes(raw)
    cycle = int.from_bytes(raw[12:20],"little")
    beats = decode_frames(raw,manifest,binding,cycle)
    (out / "beats.json").write_text(json.dumps(beats,indent=2)+"\n")
    data = encode_transport_semantic(raw,manifest,binding,"TransportFixture",cycle)
    (out / "component.rtlckpt").write_bytes(data)
    build = dict(target_configuration="TransportFixture",rtl_build_hash=manifest["reference_sha256"],
                 state_manifest_hash=manifest_hash(manifest))
    doc = decode_semantic(data,build,manifest)
    require(sum(len(r["values"]) for r in doc["records"]) == 6,"incomplete semantic conversion")
    negatives = negative_checks(raw,manifest,binding,cycle)
    require(all(sha(ROOT / name) == digest for name,digest in hashes.items()),"source changed during execution")
    summary = dict(observed_utc=datetime.now(timezone.utc).isoformat(),backend="eda",
                   hostname=socket.gethostname(),remote_root=str(ROOT),tool=toolchain.VCS,
                   scope="Synthesizable bank/MMIO/DMA component fixture; not integrated CPU/hardware acceptance",
                   physical_fpga_validated=False,rocket_image_integrated=False,
                   checks=int(match[1]),captures=int(match[2]),bank_requests=int(match[3]),
                   dma_stalls=int(match[4]),mmio_stalls=int(match[5]),integrity_rejections=negatives,
                   target_cycle=cycle,words=len(beats),source_sha256=hashes,
                   artifacts={p.name:dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
                              for p in out.iterdir() if p.is_file() and p.name!="summary.json"})
    (out / "summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(dict(summary=str(out / "summary.json"),checks=summary["checks"],
                          integrity_rejections=negatives,physical_fpga_validated=False)))


if __name__ == "__main__":
    main()
