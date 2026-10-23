"""Fresh EDA VCS regression of FIRRTL-generated real-state bank endpoints."""
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
ORACLE = {
    "Harness.harnessOnly": (0, 1, 1),
    "Harness.dut.counter": (1, 9, 1),
    "Harness.dut.fsm": (2, 2, 1),
    "Harness.dut.bank_0": (3, 9, 1),
    "Harness.dut.bank_1": (4, 9, 1),
    "Harness.dut.bank_2": (5, 9, 1),
    "Harness.dut.a.saved": (6, 9, 1),
    "Harness.dut.b.saved": (7, 9, 1),
    "Harness.dut.sram": (8, 9, 8),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(Path(toolchain.VCS).is_file() and os.environ.get("VCS_HOME") == toolchain.VCS_HOME,
            "source vcs-env.sh LAST on EDA")
    generated = args.generated.resolve()
    out_root = args.out.resolve()
    require(out_root.is_relative_to(ROOT / "automations/checkpoint_loop/runs"), "evidence must be beneath runs/")
    out_root.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="generated-bank-", dir=out_root))
    snapshots = out / "source-snapshots"
    snapshots.mkdir()
    source_names = ["generated-bank.sv", "generated-bank.fir", "generated-bank-input.fir",
                    "generated-bank-binding.json", "generated-bank-semantic.json"]
    hashes = {}
    for name in source_names:
        source = generated / name
        hashes[str(source)] = sha(source)
        (snapshots / name).write_bytes(source.read_bytes())
    for name in ["tools/checkpoint_formats/tests/generated_bank_tb.sv",
                 "tools/checkpoint_formats/tests/verify_generated_bank_vcs.py",
                 "sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala",
                 "sims/firesim/sim/midas/src/test/scala/midas/checkpoint/GeneratedStateBankAccessSpec.scala"]:
        source = ROOT / name
        hashes[name] = sha(source)
        (snapshots / source.name).write_bytes(source.read_bytes())
    binding = json.loads((snapshots / "generated-bank-binding.json").read_text())
    require(binding["reference_sha256"] == sha(snapshots / "generated-bank-input.fir"),
            "reference FIRRTL does not match generated binding")
    require(binding["instrumented_sha256"] == sha(snapshots / "generated-bank.fir"),
            "instrumented FIRRTL does not match generated binding")
    require(binding["manifest_sha256"] == sha(snapshots / "generated-bank-semantic.json"),
            "semantic manifest does not match generated binding")
    entries = binding["state"]
    require({e["hierarchy"] for e in entries} == set(ORACLE), "complete fixture oracle coverage required")
    require(len(entries) == len(ORACLE), "duplicate generated state")
    header = [f"localparam integer ENTRY_COUNT={len(entries)};",
              "integer banks[0:ENTRY_COUNT-1],slots[0:ENTRY_COUNT-1],depths[0:ENTRY_COUNT-1],kinds[0:ENTRY_COUNT-1];",
              "initial begin"]
    for i, entry in enumerate(entries):
        kind, width, depth = ORACLE[entry["hierarchy"]]
        require((entry["width"], entry["depth"]) == (width, depth), "fixture state reshaped")
        header.append(f"banks[{i}]={entry['bank']}; slots[{i}]={entry['slot']}; depths[{i}]={depth}; kinds[{i}]={kind};")
    header.append("end")
    (snapshots / "generated_bank_bindings.svh").write_text("\n".join(header) + "\n")
    commands = []

    def run(argv, log):
        commands.append(dict(argv=[str(a) for a in argv], cwd=str(ROOT), log=str(out / log)))
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        with (out / log).open("w") as stream:
            result = subprocess.run(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, text=True)
        commands[-1]["returncode"] = result.returncode
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(result.returncode == 0, f"command failed; inspect {out / log}")
        return (out / log).read_text()

    run([toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate",
         "-top", "generated_bank_tb", f"+incdir+{snapshots}",
         f"-Mdir={out / 'csrc'}", "-o", str(out / "simv"),
         str(snapshots / "generated-bank.sv"), str(snapshots / "generated_bank_tb.sv")], "compile.log")
    text = run([str(out / "simv"), "-no_save"], "run.log")
    match = re.search(r"GENERATED_BANK_PASS checks=(\d+) reads=(\d+) stalls=(\d+) functional_edges=(\d+)", text)
    require(match is not None, "generated endpoint simulation did not pass")
    require(int(match[2]) == 53 and int(match[1]) > 300, "incomplete generated endpoint verification")
    summary = dict(status="verified", scope="generated_lowered_state_component_only",
                   hardware_capture=False, timestamp=datetime.now(timezone.utc).isoformat(),
                   hostname=socket.gethostname(), checks=int(match[1]), reads=int(match[2]),
                   stalls=int(match[3]), functional_edges=int(match[4]),
                   source_sha256=hashes, artifact_sha256={p.name: sha(p) for p in out.iterdir() if p.is_file()})
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
