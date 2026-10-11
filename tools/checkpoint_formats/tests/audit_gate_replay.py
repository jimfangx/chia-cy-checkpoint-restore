"""Recheck gate replay provenance, recorded outputs and native activity artifacts."""

import argparse
import json
from pathlib import Path

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.formal_state_map import gate_deposits, sha
from tools.checkpoint_formats.gate_activity import audit_activity, read_saif
from tools.checkpoint_formats.gate_replay import bench, memory_words, memory_witnesses, validate_design_boundary
from tools.checkpoint_formats.replay import boundary_ports, builds
from .audit_formal_state_map import container
from .verify_formal_state_map import ROOT, VCS
from .verify_gate_replay import window


def audit(run):
    load = lambda path: json.loads(path.read_text())
    inputs = load(run / "inputs.json")
    proof = Path(inputs["proof_run"])
    mapping, manifest, boundary, adapter = (load(proof / name) for name in
        ("asic_state_map.json", "manifest.json", "boundary.json", "cell-adapter.json"))
    paths = load(proof / "inputs.json")
    require(paths == inputs["proof_paths"], "changed proof paths")
    artifacts = {role: Path(path).read_bytes() for role, path in paths.items()}
    for role in ("rtl", "netlist"):
        validate_design_boundary(artifacts[role].decode(), mapping["top"], boundary["ports"])
    ckpt_data = Path(inputs["checkpoint_path"]).read_bytes()
    trace_data = Path(inputs["trace_path"]).read_bytes()
    trace = container(Path(inputs["trace_path"]), b"TRACE\0\0\1")
    request = load(run / "gate-restored/request.json")
    cycle, deposits = gate_deposits(mapping, manifest, adapter, artifacts, ckpt_data,
                                    builds(manifest, boundary, request["configuration"])[0], "tb.dut")
    require(request["artifact_hashes"] == {k: sha(v) for k, v in artifacts.items()} and
            request["checkpoint_sha256"] == sha(ckpt_data) and request["trace_sha256"] == sha(trace_data) and
            request["mapping_sha256"] == sha(json.dumps(mapping, sort_keys=True).encode()), "stale replay inputs")
    require(request["harness_sha256"] == sha((run / "gate-restored/tb.sv").read_bytes()) and
            request["restore_sha256"] == sha((run / "gate-restored/restore.txt").read_bytes()),
            "changed compiled harness or translated deposits")
    require((run / "gate-restored/restore.txt").read_text() ==
            "".join(f"{p} {w} {v}\n" for p, w, v in deposits), "incorrect gate initialization file")
    require((run / "netlist.v").read_bytes() == artifacts["netlist"] and
            (run / "models.v").read_bytes() == artifacts["models"], "compiled design is not proven gate netlist")
    require(sha((proof / "reference/capture.jsonl").read_bytes()) == inputs["raw_capture_sha256"],
            "changed continuous input prefix")
    ports = boundary_ports(boundary)
    prefix = []
    raw = [json.loads(line) for line in (proof / "reference/capture.jsonl").read_text().splitlines()]
    for row in raw[:cycle]:
        record = dict(cycle=row["cycle"], inputs={}, outputs={})
        for port, value in zip(ports, row["values"]):
            if port["direction"] == "input":
                record["inputs"][port["name"]] = dict(width=port["width"], value=value)
        prefix.append(record)
    require([record["cycle"] for record in prefix] == list(range(cycle)), "invalid continuous input prefix")
    require((run / "gate-restored/tb.sv").read_text() ==
            bench(mapping["top"], ports, trace, len(deposits), memories=memory_words(mapping)) and
            (run / "gate-continuous/tb.sv").read_text() ==
            bench(mapping["top"], ports, trace, len(deposits), prefix, memory_words(mapping)),
            "compiled harness differs from recorded-input gate replay")
    witnesses = memory_witnesses(mapping)
    require(request["vcd_memory_witnesses"] == witnesses, "changed memory witness binding")
    samples = len(trace["records"])
    require(request["target_cycle"] == trace["target_cycle"] == cycle and
            request["samples"] == samples and request["activity_duration_ps"] == 3000*samples and
            request["deposited_words"] == len(deposits) and
            request["gate_storage_bits"] == mapping["gate_storage_bits"], "incorrect request geometry")
    commands = load(run / "commands.json")
    builds_seen = []
    for command in commands:
        require(Path(command["log"]).is_file(), "missing command log")
        argv = command["argv"]
        if argv[0] == VCS:
            require(command["exit_code"] == 0 and "-full64" in argv and
                    argv[argv.index("-cc")+1] == "/usr/bin/gcc-13" and
                    "Y-2026.03-SP1" in Path(command["log"]).read_text(), "incorrect VCS build")
            directory = ROOT / command["cwd"]
            if directory.name.startswith("gate-"):
                sources = [str(run / "netlist.v"), str(run / "models.v"), str(directory / "tb.sv")]
            else:
                require(directory.name == "clean-rtl", "unknown simulation design")
                sources = [paths["rtl"], str(directory / "replay.sv")]
            first = argv.index("-cc")+2
            require(argv[first:-2] == [*sources, str(ROOT / "tools/checkpoint_formats/semantic_restore.cc")],
                    "unexpected simulation sources; gate build may contain RTL")
            require(argv[-2:] == ["-o", str(directory / "simv")], "incorrect simulator artifact")
            builds_seen.append(directory.name)
    require(sorted(builds_seen) == ["clean-rtl", "gate-continuous", "gate-restored"], "incomplete fresh build scope")
    require(len(commands) == 7 and [command["exit_code"] for command in commands] == [0]*6+[1] and
            len({command["pid"] for command in commands}) == 7, "incomplete fresh tool invocation evidence")
    activity = {}
    for label, prefix_edges in (("restored", 0), ("continuous", cycle)):
        directory = run / ("gate-" + label)
        log = (directory / "simulation.log").read_text()
        begin, first_edges, end, last_edges = window(log)
        require(first_edges == prefix_edges and last_edges == prefix_edges+samples, "wrong target edge count")
        if label == "restored":
            require(f"GATE_ZERO_EDGE_READBACK cycle={cycle} words={len(deposits)} edges=0" in log,
                    "missing complete zero-edge gate readback")
        lines = [line for line in log.splitlines() if line.startswith("GATE_SAMPLE ")]
        require(len(lines) == samples, "missing sampled boundary")
        for record, line in zip(trace["records"], lines):
            fields = dict(field.split("=", 1) for field in line.split()[1:])
            require(int(fields.pop("cycle")) == record["cycle"] and
                    {name: int(value, 16) for name, value in fields.items()} ==
                    {name: int(value["value"], 16) for name, value in record["outputs"].items()},
                    "recorded reference output mismatch")
        activity[label] = audit_activity((directory / "gate_level.saif").read_text(),
            (directory / "gate_level.vcd").read_text(), mapping, begin, end, samples, witnesses)
    require(read_saif((run / "gate-restored/gate_level.saif").read_text()) ==
            read_saif((run / "gate-continuous/gate_level.saif").read_text()), "gate activity trajectory differs")
    fault = (run / "storage-fault/simulation.log").read_text()
    require(f"GATE_MISMATCH cycle={cycle} signal=count_out" in fault and "GATE_SAMPLE " not in fault,
            "gate fault control did not fail at first sampled boundary")
    require("PASS: fresh clean RTL replay" in (run / "clean-rtl/simulation.log").read_text(), "missing RTL control")
    mutations = sorted((run / "activity-mutations").glob("*.saif"))
    require(len(mutations) == 9, "incomplete activity rejection scope")
    begin, _, end, _ = window((run / "gate-restored/simulation.log").read_text())
    for saif in mutations:
        try:
            audit_activity(saif.read_text(), saif.with_suffix(".vcd").read_text(), mapping,
                           begin, end, samples, witnesses)
        except FormatError:
            pass
        else:
            raise AssertionError(f"corrupt actual activity accepted: {saif}")
    return dict(status="passed", run=str(run), sampled_boundaries=samples,
                output_values=sum(len(r["outputs"]) for r in trace["records"]),
                activity_mutations_rejected=len(mutations), activity=activity)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    runs = [args.run.resolve()] if args.run else [Path(row["run"]) for row in
                                                 json.loads(args.catalog.read_text()).values()]
    results = [audit(run) for run in runs]
    args.out.write_text(json.dumps(results, indent=2) + "\n")
    print(f"PASS: rechecked {len(results)} gate replay and activity artifact sets")


if __name__ == "__main__":
    main()
