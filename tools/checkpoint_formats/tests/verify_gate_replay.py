"""Fresh ordinary VCS gate/RTL replay and native SAIF over proven M8 profiles.

Source env.sh, sims/firesim/env.sh, then vcs-env.sh LAST. Catalogs select existing
proof artifacts; every map is revalidated against their current bytes. No old
proof or simulation artifact is rewritten. Each invocation has new build paths.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from tools.checkpoint_formats.codec import FormatError, encode, require
from tools.checkpoint_formats.formal_state_map import sha
from tools.checkpoint_formats.gate_activity import audit_activity, read_saif
from tools.checkpoint_formats.gate_replay import bench, memory_words, memory_witnesses, prepare_gate_replay
from tools.checkpoint_formats.replay import boundary_ports, prepare_replay
from .verify_formal_state_map import ROOT, VCS


def window(log):
    begin = re.findall(r"GATE_ACTIVITY_BEGIN ticks=(\d+) edges=(\d+)", log)
    end = re.findall(r"GATE_ACTIVITY_END ticks=(\d+) edges=(\d+)", log)
    require(len(begin) == len(end) == 1, "missing or duplicate activity window")
    return tuple(map(int, (*begin[0], *end[0])))


def verify(proof, out):
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="invocation-", dir=out)).resolve()
    load = lambda name: json.loads((proof / name).read_text())
    mapping, manifest, boundary, adapter = map(load, ("asic_state_map.json", "manifest.json",
                                                    "boundary.json", "cell-adapter.json"))
    paths = load("inputs.json")
    artifacts = {role: Path(path).read_bytes() for role, path in paths.items()}
    capture = proof / "reference"
    checkpoint_data, trace_data = ((capture / name).read_bytes() for name in ("capture.rtlckpt", "capture.trace"))
    config = "formal-sram-dut-v1" if mapping["map_version"] == 8 else "formal-small-dut-v1"
    restored = run / "gate-restored"
    trace, deposits = prepare_gate_replay(mapping, manifest, boundary, adapter, artifacts,
                                         checkpoint_data, trace_data, config, restored)
    samples = len(trace["records"])
    ports = boundary_ports(boundary)
    rows = [json.loads(line) for line in (capture / "capture.jsonl").read_text().splitlines()]
    prefix = []
    for cycle, row in enumerate(rows[:trace["target_cycle"]]):
        require(row["cycle"] == cycle and len(row["values"]) >= len(ports), "invalid continuous prefix")
        record = dict(cycle=cycle, inputs={}, outputs={})
        for port, value in zip(ports, row["values"]):
            if port["direction"] == "input":
                record["inputs"][port["name"]] = dict(width=port["width"], value=value)
        prefix.append(record)
    require(len(prefix) == trace["target_cycle"] > 0, "continuous control needs complete nonzero prefix")
    # Startup output state may be unknown before reset and memory initialization.
    # Only prefix inputs are replayed; sampled outputs at/after the cut are strict.
    prefix_doc = dict(trace, target_cycle=0, records=prefix)
    encode("trace", prefix_doc)
    continuous = run / "gate-continuous"
    continuous.mkdir()
    (continuous / "tb.sv").write_text(bench(mapping["top"], ports, trace, len(deposits), prefix, memory_words(mapping)))
    (run / "netlist.v").write_bytes(artifacts["netlist"])
    (run / "models.v").write_bytes(artifacts["models"])
    commands = []

    def invoke(argv, directory, name, expected=0):
        argv = list(map(str, argv))
        log = directory / name
        with log.open("w") as output:
            process = subprocess.Popen(argv, cwd=directory, stdout=output, stderr=subprocess.STDOUT)
            pid = process.pid
            try:
                code = process.wait(timeout=300)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
                raise
        commands.append(dict(cwd=str(directory.relative_to(ROOT)), argv=argv,
                             log=str(log), exit_code=code, pid=pid))
        (run / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(code == expected, f"unexpected exit {code}: {log}")
        return log.read_text()

    def build(directory, sources):
        text = invoke([VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-debug_access+all",
                       "-CFLAGS", "-std=c++11", "-cc", os.environ["VCS_CC"], *sources,
                       ROOT / "tools/checkpoint_formats/semantic_restore.cc", "-o", directory / "simv"],
                      directory, "compile.log")
        require("Y-2026.03-SP1" in text, "VCS compiler release mismatch")
        return directory / "simv"

    simv = build(restored, [run / "netlist.v", run / "models.v", restored / "tb.sv"])
    restored_log = invoke([simv, f"+restore={restored / 'restore.txt'}"], restored, "simulation.log")
    continuous_simv = build(continuous, [run / "netlist.v", run / "models.v", continuous / "tb.sv"])
    continuous_log = invoke([continuous_simv], continuous, "simulation.log")
    matched = lambda log: [line for line in log.splitlines() if line.startswith("GATE_SAMPLE ")]
    require(len(matched(restored_log)) == samples and matched(restored_log) == matched(continuous_log),
            "continuous/restored sampled outputs differ")
    metrics = {}
    for label, directory, log, first_edges in (("restored", restored, restored_log, 0),
                                             ("continuous", continuous, continuous_log, len(prefix))):
        begin, begin_edges, end, end_edges = window(log)
        require(begin_edges == first_edges and end_edges == first_edges+samples, "target edge window mismatch")
        metrics[label] = audit_activity((directory / "gate_level.saif").read_text(),
            (directory / "gate_level.vcd").read_text(), mapping, begin, end, samples, memory_witnesses(mapping))
    # Activity must agree for every signal actually reported by native SAIF,
    # not merely the top-level outputs or a fabricated switching summary.
    require(read_saif((restored / "gate_level.saif").read_text()) ==
            read_saif((continuous / "gate_level.saif").read_text()), "continuous/restored gate SAIF differs")
    rtl = run / "clean-rtl"
    prepare_replay(manifest, boundary, config, checkpoint_data, trace_data, rtl)
    rtl_simv = build(rtl, [Path(paths["rtl"]), rtl / "replay.sv"])
    rtl_log = invoke([rtl_simv, f"+restore={rtl / 'restore.txt'}", f"+waveform={rtl / 'replay.vcd'}"],
                     rtl, "simulation.log")
    require("PASS: fresh clean RTL replay" in rtl_log, "ordinary RTL replay failed")

    # Same binary, actual storage corruption, fresh simulator process.
    fault = copy.deepcopy(deposits)
    fault_gates = next(entry["gates"] for entry in mapping["entries"] if entry["original_rtl"] == "count[0]")
    for gate in fault_gates:
        path = f"tb.dut.{gate['instance']}.{gate['storage']}"
        for index, (name, width, value) in enumerate(fault):
            if name == path:
                fault[index] = (name, width, f"{int(value,16) ^ (1 << gate['bit']):0{(width+3)//4}x}")
                break
    bad_restore = run / "fault-restore.txt"
    bad_restore.write_text("".join(f"{p} {w} {v}\n" for p, w, v in fault))
    negative = run / "storage-fault"
    negative.mkdir()
    fault_log = invoke([simv, f"+restore={bad_restore}"], negative, "simulation.log", expected=1)
    require(f'GATE_MISMATCH cycle={trace["target_cycle"]} signal=count_out' in fault_log,
            "real gate storage fault did not fail at first sampled cycle")

    # Actual generated-activity mutations: the unchanged control was audited above.
    saif_text = (restored / "gate_level.saif").read_text()
    vcd_text = (restored / "gate_level.vcd").read_text()
    begin, _, end, _ = window(restored_log)
    storage_path = path.split(".")[-1]
    mutations = {
        "rtl-producer": (saif_text.replace("VCS Y-2026.03-SP1_Full64", "RTL activity"), vcd_text),
        "wrong-duration": (saif_text.replace("(DURATION 237.00)", "(DURATION 238.00)"), vcd_text),
        "wrong-clock-count": (saif_text.replace("(TC 158)", "(TC 157)", 1), vcd_text),
        "missing-storage": (saif_text.replace("(" + storage_path + "\n", "(hidden_state\n", 1), vcd_text),
        "unknown-clock": (saif_text.replace("(T0 158) (T1 79) (TX 0)", "(T0 157) (T1 79) (TX 1)", 1), vcd_text),
        "wrong-vcd-release": (saif_text, vcd_text.replace("Y-2026.03-SP1_Full64", "old-release")),
        "wrong-vcd-timescale": (saif_text, vcd_text.replace("1ps", "10ps", 1)),
        "missing-vcd-storage": (saif_text, vcd_text.replace(" state $end", " hidden_state $end", 1)),
        "initialization-in-vcd": (saif_text, vcd_text.replace(f"#{begin}\n", f"#{begin-1000}\n", 1)),
    }
    rejections = {}
    mutation_directory = run / "activity-mutations"
    mutation_directory.mkdir()
    for name, (saif_mutation, vcd_mutation) in mutations.items():
        require((saif_mutation, vcd_mutation) != (saif_text, vcd_text), f"mutation did not apply: {name}")
        (mutation_directory / (name + ".saif")).write_text(saif_mutation)
        (mutation_directory / (name + ".vcd")).write_text(vcd_mutation)
        try:
            audit_activity(saif_mutation, vcd_mutation, mapping, begin, end, samples, memory_witnesses(mapping))
        except (FormatError, ValueError) as error:
            rejections[name] = str(error)
        else:
            raise AssertionError(f"corrupted gate activity accepted: {name}")
    identities = dict(proof_run=str(proof), proof_paths=paths,
                      checkpoint_path=str(capture / "capture.rtlckpt"), trace_path=str(capture / "capture.trace"),
                      raw_capture_sha256=sha((capture / "capture.jsonl").read_bytes()))
    (run / "inputs.json").write_text(json.dumps(identities, indent=2) + "\n")
    summary = dict(status="passed", target_cycle=trace["target_cycle"], samples=samples,
                   end_cycle=trace["target_cycle"]+samples, outputs=samples*sum(p["direction"] == "output" for p in ports),
                   zero_edge_readback=True, fresh_gate_processes=True, actual_netlist_activity=True,
                   continuous_and_restored_saif_equal=True, ordinary_rtl_replay=True,
                   storage_fault_rejected=True, activity_mutation_rejections=rejections, activity=metrics,
                   power_analysis="not run: artificial functional libraries lack cell power data",
                   process_ASIC_validated=False, physical_FPGA_validated=False)
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return run, summary


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--proof-run", type=Path)
    parser.add_argument("--catalog", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get("VCS_HOME") == str(Path(VCS).parents[1]) and
            os.environ.get("VCS_CC") == "/usr/bin/gcc-13", "source vcs-env.sh LAST")
    profiles = {}
    if args.proof_run:
        profiles["selected"] = str(args.proof_run.resolve())
    for index, catalog in enumerate(args.catalog):
        profiles.update({f"catalog-{index}-{name}": path for name, path in json.loads(catalog.read_text()).items()})
    require(profiles, "no proven profiles selected")
    args.out.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, proof in profiles.items():
        run, summary = verify(Path(proof).resolve(), args.out / name)
        results[name] = dict(run=str(run), **summary)
        (args.out / "matrix-results.json").write_text(json.dumps(results, indent=2) + "\n")
        print(f"PASS {name}: {run}", flush=True)


if __name__ == "__main__":
    main()
