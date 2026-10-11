"""Prepare finite Level-2 replay of a proven synthesized netlist in fresh VCS.

Only the netlist and its hash-bound cell models are simulation design sources.
Native SAIF monitoring includes registers and arrays inside those gate models;
the VCS policy name ``rtl_on`` selects data types, not an RTL simulation flow.
"""

import argparse
import json
from pathlib import Path
import re

from .codec import decode, require
from .formal_state_map import gate_deposits, sha
from .replay import boundary_ports, builds


def validate_design_boundary(text, top, expected):
    """Require the entire flat DUT interface; omitted unused ports still reject."""
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    match = re.fullmatch(r"\s*module\s+" + re.escape(top) + r"\s*\((.*?)\);(.*?)endmodule\s*", clean, re.S)
    require(match is not None, "unsupported gate DUT interface")
    header, body = match.groups()
    ansi = bool(re.search(r"\b(input|output|inout)\b", header))
    declarations = [header] if ansi else re.findall(r"\b(?:input|output|inout)\b[^;]*", body)
    actual = {}
    for declaration in declarations:
        direction, width = None, None
        for item in declaration.split(","):
            parsed = re.fullmatch(r"\s*(?:(input|output)\s*(?:(?:wire|reg|logic)\s+)?"
                                  r"(?:\[(\d+):(\d+)\]\s*)?)?([A-Za-z_][A-Za-z0-9_$]*)\s*", item)
            require(parsed is not None, "unsupported gate port declaration")
            kind, high, low, name = parsed.groups()
            if kind:
                direction, width = kind, abs(int(high)-int(low))+1 if high is not None else 1
            require(direction is not None and name not in actual, "duplicate or unsupported gate port")
            actual[name] = (direction, width)
    if ansi:
        require(not re.search(r"\b(input|output|inout)\b", body), "mixed gate port declarations")
    else:
        names = [name.strip() for name in header.split(",")]
        require(len(names) == len(set(names)) and set(names) == set(actual), "incomplete gate port declaration")
    require(actual == {port["name"]: (port["direction"], port["width"]) for port in expected},
            "incomplete or reshaped gate DUT boundary")


def memory_words(mapping):
    paths = {}
    for entry in mapping["entries"]:
        for gate in entry["gates"]:
            if "[" in gate["storage"]:
                instance = gate["instance"]
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", instance):
                    instance = "\\" + instance + " "
                paths[f"tb.dut.{instance}.{gate['storage']}"] = gate.get("width", 1)
    return sorted(paths.items())


def memory_witnesses(mapping):
    witnesses = {}
    for index, (path, width) in enumerate(memory_words(mapping)):
        for bit in range(width):
            suffix = f"[{bit}]" if width > 1 else ""
            witnesses[path.replace("\\", "").replace(" ", "") + suffix] = \
                f"tb.dut.checkpoint_activity_probe.word_{index}" + suffix
    return witnesses


def bench(top, ports, trace, words, prefix=(), memories=()):
    """One target edge per record; optional recorded prefix is for the oracle."""
    source = ["`timescale 1ns/1ps", "module tb;", "reg clock = 0;", "integer edges = 0;",
              'import "DPI-C" context function int semantic_restore(input string path, input int unsigned words);',
              'import "DPI-C" context function int semantic_verify(input string path, input int unsigned words);',
              'import "DPI-C" context function void semantic_fail(input string message);']
    for port in ports:
        source.append(f"{'reg' if port['direction'] == 'input' else 'wire'} [{port['width']-1}:0] {port['name']};")
    source += [top + " dut(.clock(clock), " + ", ".join(f".{p['name']}({p['name']})" for p in ports) + ");",
               "string restore_path;", "always @(posedge clock) edges = edges + 1;", "initial begin",
               '$set_gate_level_monitoring("rtl_on", "mda");', "$set_toggle_region(tb.dut);", "#1;"]

    def inputs(record):
        return [f"{name} = {value['width']}'h{value['value']};"
                for name, value in sorted(record["inputs"].items())]

    if prefix:
        for record in prefix:
            source += inputs(record) + ["#1; clock = 1; #1; clock = 0; #1;"]
    else:
        source += ['if (!$value$plusargs("restore=%s", restore_path)) semantic_fail("MISSING_GATE_RESTORE");',
                   f'if (semantic_restore(restore_path, {words})) semantic_fail("GATE_RESTORE_FAILED");',
                   "#1;", 'if (edges != 0) semantic_fail("GATE_RESTORE_ADVANCED_EDGE");',
                   f'if (semantic_verify(restore_path, {words})) semantic_fail("GATE_READBACK_FAILED");',
                   f'$display("GATE_ZERO_EDGE_READBACK cycle={trace["target_cycle"]} words={words} edges=0");']
    source += inputs(trace["records"][0]) + ["#1;",
               '$dumpfile("gate_level.vcd"); $dumpvars(0, tb.dut);']
    # The bound probe below exposes memory words as read-only wires because
    # VCS's VCD hierarchy traversal does not dump unpacked memory variables.
    source += ["$toggle_start();",
               '$display("GATE_ACTIVITY_BEGIN ticks=%0t edges=%0d", $time, edges);', "#1;"]
    for index, record in enumerate(trace["records"]):
        if index:
            source += inputs(record) + ["#1;"]
        for name, value in sorted(record["outputs"].items()):
            source.append(f"if ({name} !== {value['width']}'h{value['value']}) "
                          f'semantic_fail("GATE_MISMATCH cycle={record["cycle"]} signal={name}");')
        names = sorted(record["outputs"])
        source += [f'$display("GATE_SAMPLE cycle={record["cycle"]} ' +
                   " ".join(name + "=%h" for name in names) + '", ' + ", ".join(names) + ");",
                   "clock = 1; #1; clock = 0; #1;"]
    # Dump the settled initial state a full timestep before the first edge, so
    # VCD's initial dump cannot absorb the first NBA register updates.
    source += ["$toggle_stop();", '$toggle_report("gate_level.saif", 1.0e-9, tb.dut);',
               '$display("GATE_ACTIVITY_END ticks=%0t edges=%0d", $time, edges);',
               f'if (edges != {len(prefix) + len(trace["records"])}) semantic_fail("GATE_EDGE_COUNT");',
               f'$display("GATE_END cycle={trace["target_cycle"]+len(trace["records"])} edges=%0d", edges);',
               "$finish;", "end", "endmodule"]
    if memories:
        source += ["module checkpoint_gate_memory_probe;"]
        for index, (path, width) in enumerate(memories):
            packed = f"[{width-1}:0] " if width > 1 else ""
            source.append(f"wire {packed}word_{index} = {path};")
        source += ["endmodule", f"bind {top} checkpoint_gate_memory_probe checkpoint_activity_probe();"]
    return "\n".join(source) + "\n"


def prepare_gate_replay(mapping, manifest, boundary, adapter, artifacts, checkpoint_data,
                        trace_data, configuration, out):
    ports = boundary_ports(boundary)
    require(boundary["dut_root"] == manifest["dut_root"] and
            manifest["clock_domain"] == manifest["dut_root"] + ".clock" and
            boundary["dut_module"] == mapping["top"], "unsupported gate replay boundary")
    require(any(p["direction"] == "output" for p in ports), "gate replay requires observable outputs")
    require(not ({p["name"] for p in ports} & {"edges", "restore_path", "dut"}),
            "gate boundary collides with replay harness")
    for role in ("rtl", "netlist"):
        validate_design_boundary(artifacts[role].decode(), mapping["top"], boundary["ports"])
    checkpoint_build, trace_build = builds(manifest, boundary, configuration)
    cycle, deposits = gate_deposits(mapping, manifest, adapter, artifacts, checkpoint_data,
                                    checkpoint_build, "tb.dut")
    trace = decode(trace_data, "trace", trace_build)
    require(trace["target_cycle"] == cycle and trace["records"], "gate checkpoint/trace cycle mismatch")
    for record in trace["records"]:
        for direction in ("input", "output"):
            require({name: value["width"] for name, value in record[direction + "s"].items()} ==
                    {p["name"]: p["width"] for p in ports if p["direction"] == direction},
                    "incomplete, unknown or wrong-width gate boundary signals")
    # Validate every input and formal artifact before creating any loader files.
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "restore.txt").write_text("".join(f"{p} {w} {v}\n" for p, w, v in deposits))
    (out / "tb.sv").write_text(bench(mapping["top"], ports, trace, len(deposits), memories=memory_words(mapping)))
    request = dict(request_version=1, target_cycle=cycle, target_clock_phase="before_rising_edge",
                   samples=len(trace["records"]), gate_storage_bits=mapping["gate_storage_bits"],
                   deposited_words=len(deposits), activity_duration_ps=3000*len(trace["records"]),
                   configuration=configuration, simulation_sources=["netlist", "models"],
                   artifact_hashes={k: sha(v) for k, v in artifacts.items()},
                   checkpoint_sha256=sha(checkpoint_data), trace_sha256=sha(trace_data),
                   mapping_sha256=sha(json.dumps(mapping, sort_keys=True).encode()),
                   harness_sha256=sha((out / "tb.sv").read_bytes()),
                   restore_sha256=sha((out / "restore.txt").read_bytes()))
    request["vcd_memory_witnesses"] = memory_witnesses(mapping)
    (out / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    return trace, deposits


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--proof-run", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--configuration", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    load = lambda name: json.loads((args.proof_run / name).read_text())
    artifacts = {role: Path(path).read_bytes() for role, path in load("inputs.json").items()}
    prepare_gate_replay(load("asic_state_map.json"), load("manifest.json"), load("boundary.json"),
                        load("cell-adapter.json"), artifacts, args.checkpoint.read_bytes(),
                        args.trace.read_bytes(), args.configuration, args.out)


if __name__ == "__main__":
    main()
