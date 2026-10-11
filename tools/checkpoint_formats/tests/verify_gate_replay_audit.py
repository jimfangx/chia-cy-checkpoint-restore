"""Actual artifact mutations test the gate auditor; restore all bytes afterward.

Only the selected new replay output is modified temporarily. Formal proof runs,
semantic inputs, netlists in proof runs and all protected user inputs are read-only.
"""

import argparse
import copy
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.formal_state_map import sha
from .audit_gate_replay import audit


def verify(run):
    control = audit(run)
    restored = run / "gate-restored"
    request_path = restored / "request.json"
    request = json.loads(request_path.read_text())
    harness = (restored / "tb.sv").read_text()
    changed_harness = harness.replace("clock = 1;", "clock = 0;", 1)
    require(changed_harness != harness, "harness mutation did not apply")
    rebound_harness = dict(request, harness_sha256=sha(changed_harness.encode()))
    restore = (restored / "restore.txt").read_text()
    rows = restore.splitlines()
    path, width, value = rows[0].split()
    rows[0] = f"{path} {width} {int(value,16)^1:0{(int(width)+3)//4}x}"
    changed_restore = "\n".join(rows)+"\n"
    rebound_restore = dict(request, restore_sha256=sha(changed_restore.encode()))
    commands_path = run / "commands.json"
    commands = json.loads(commands_path.read_text())
    changed_commands = copy.deepcopy(commands)
    argv = changed_commands[0]["argv"]
    argv[argv.index(str(run / "netlist.v"))] = str(run / "original-rtl.v")
    original_log = (restored / "simulation.log").read_text()
    match = re.search(r"GATE_SAMPLE cycle=\d+ count_out=([0-9a-f]+)", original_log)
    require(match is not None, "no sampled count output for mutation")
    changed_log = original_log[:match.start(1)]+format(int(match[1],16)^1, "x")+original_log[match.end(1):]
    encoded = lambda obj: (json.dumps(obj, indent=2)+"\n").encode()
    mutations = {
        "changed-compiled-netlist": {run / "netlist.v": (run / "netlist.v").read_bytes()+b"\n"},
        "changed-compiled-models": {run / "models.v": (run / "models.v").read_bytes()+b"\n"},
        "changed-harness-rehashed": {restored / "tb.sv": changed_harness.encode(), request_path: encoded(rebound_harness)},
        "changed-deposits-rehashed": {restored / "restore.txt": changed_restore.encode(), request_path: encoded(rebound_restore)},
        "RTL-compilation-source": {commands_path: encoded(changed_commands)},
        "forged-sampled-output": {restored / "simulation.log": changed_log.encode()},
        "wrong-activity-input-identity": {request_path: encoded(dict(request, trace_sha256="0"*64))},
        "missing-zero-edge-readback": {restored / "simulation.log": original_log.replace(
            "GATE_ZERO_EDGE_READBACK", "REMOVED_READBACK", 1).encode()},
    }
    rejections = {}
    evidence = run / "provenance-mutations"
    evidence.mkdir(exist_ok=True)
    for name, replacements in mutations.items():
        original = {path: path.read_bytes() for path in replacements}
        require(all(original[path] != data for path, data in replacements.items()), "mutation did not apply")
        directory = evidence / name
        directory.mkdir(exist_ok=True)
        for path, data in replacements.items():
            target = directory / path.relative_to(run)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        try:
            for path, data in replacements.items():
                path.write_bytes(data)
            try:
                audit(run)
            except (FormatError, AssertionError) as error:
                rejections[name] = str(error)
            else:
                raise AssertionError(f"actual corrupted replay artifact accepted: {name}")
        finally:
            for path, data in original.items():
                path.write_bytes(data)
            require(all(path.read_bytes() == data for path, data in original.items()), "artifact bytes not restored")
    result = dict(status="passed", run=str(run), unchanged_control=control["status"],
                  distinct_artifact_mutations_rejected=len(rejections), rejections=rejections,
                  original_bytes_preserved=True)
    (run / "provenance-rejections.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    results = [verify(Path(row["run"])) for row in json.loads(args.catalog.read_text()).values()]
    args.out.write_text(json.dumps(results, indent=2)+"\n")
    print(f"PASS: {len(results)} unchanged controls; {sum(r['distinct_artifact_mutations_rejected'] for r in results)} actual provenance mutations rejected")


if __name__ == "__main__":
    main()
