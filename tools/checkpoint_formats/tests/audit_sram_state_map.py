"""Independent SRAM raw-proof, complete storage, checkpoint and replay audit.

Does not import the state-map exporter, translator, relational miter or codec.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

from .audit_formal_state_map import container


FIXTURE = Path(__file__).with_name("fixtures") / "formal"
canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
digest = lambda data: hashlib.sha256(data).hexdigest()


def audited_miter(rows, rtl, netlist):
    lines = [re.sub(r"\bmodule StateMapDUT\b", "module checkpoint_reference", rtl),
             re.sub(r"\bmodule StateMapDUT\b", "module checkpoint_implementation", netlist),
             "module checkpoint_relation_miter(input clock, reset, enable, write,",
             "  input [1:0] address, input [3:0] data);",
             "wire [3:0] r_held, r_count, r_read, i_held, i_count, i_read;"]
    for prefix, module, instance in (("r", "checkpoint_reference", "reference"),
                                     ("i", "checkpoint_implementation", "implementation")):
        lines.append(f"{module} {instance}(.clock(clock),.reset(reset),.enable(enable),.write(write),"
                     f".address(address),.data(data),.held_out({prefix}_held),.count_out({prefix}_count),.read_out({prefix}_read));")
    def gate(path):
        instance, storage = path.split(".")
        return f"implementation.\\{instance} .{storage}"
    expressions = [f"(reference.{r['original_rtl']} == ({gate(r['gate'])} ^ 1'b{r['xor']}))" for r in rows]
    lines.append("wire relation = " + " &&\n  ".join(expressions) + ";")
    lines.extend(f"step_{n}: assert property (@(posedge clock) relation |=> {expr});" for n, expr in enumerate(expressions))
    lines.extend(f"output_{p}: assert property (@(posedge clock) relation |-> r_{p} == i_{p});" for p in ("held", "count", "read"))
    lines.append("checkpoint_edge: cover property (@(posedge clock) relation ##1 relation);")
    for n, path in enumerate(sorted({r["gate"] for r in rows})):
        for value in (0, 1):
            lines.append(f"bit_{n}_{value}: cover property (@(posedge clock) relation && {gate(path)} == 1'b{value});")
    return "\n".join(lines + ["endmodule", ""]).encode()


def audit_proof(data, rows, success):
    assert json.loads(data["relation_spec"]) == dict(relation_version=1, top="StateMapDUT", relations=rows)
    assert data["relation_miter"] == audited_miter(rows, data["rtl"].decode(), data["netlist"].decode())
    source = Path(__file__).parents[1] / "relational_state.py"
    script = next(ast.literal_eval(node.value) for node in ast.parse(source.read_text()).body if
        isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SCRIPT" for t in node.targets))
    assert data["relation_script"] == script.encode()
    expected = {}
    for name in [f"step_{n}" for n in range(len(rows))] + [f"output_{p}" for p in ("held", "count", "read")]:
        prop = "<embedded>::checkpoint_relation_miter." + name
        expected[prop] = "assert"
        expected[prop + ":precondition1"] = "cover"
    expected["<embedded>::checkpoint_relation_miter.checkpoint_edge"] = "cover"
    for n in range(len({row["gate"] for row in rows})):
        for value in (0, 1): expected[f"<embedded>::checkpoint_relation_miter.bit_{n}_{value}"] = "cover"
    text = data["relation_results"].decode()
    lines = text.splitlines()
    assert lines[0] == "FORMAT\tjasper-relation-v1" and lines[-1] == "END"
    inputs, results = {}, {}
    for line in lines[1:-1]:
        row = line.split("\t")
        if row[0] == "INPUT":
            assert len(row) == 3 and row[1] not in inputs
            inputs[row[1]] = row[2]
        else:
            assert len(row) == 4 and row[0] == "PROPERTY" and row[1] not in results
            results[row[1]] = tuple(row[2:])
    assert inputs == {role: digest(data[role]) for role in
                      ("rtl", "netlist", "models", "relation_spec", "relation_miter", "relation_script")}
    assert {p: kind for p, (kind, _) in results.items()} == expected
    log = data["relation_log"].decode()
    assert "ERROR" not in log and "CHECKPOINT_RELATION_RESET=none" in log and "Exiting the analysis session with status 0." in log
    raw = re.findall(r"^CHECKPOINT_RELATION_PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$", log, re.M)
    assert len(raw) == len(results) and {p: (kind, status) for p, kind, status in raw} == results
    raw_inputs = re.findall(r"^CHECKPOINT_RELATION_INPUT\t([^\t\n]+)\t([^\t\n]+)$", log, re.M)
    assert len(raw_inputs) == 6 and dict(raw_inputs) == inputs
    for prop, (kind, status) in results.items():
        name = re.escape(prop.split("::")[1])
        if status == "cex":
            assert not success and kind == "assert"
            assert re.search(r'A counterexample \(cex\) with \d+ cycles was found for the property "' + name + r'"', log)
        else:
            assert status == ("proven" if kind == "assert" else "covered")
            assert re.search(r'The (?:cover )?property "' + name + r'" was ' + status + r' (?:in|at) ', log)
    assert success or any(status == "cex" for _, status in results.values())


def audit(run):
    summary = json.loads((run / "summary.json").read_text())
    assert summary["status"] == "passed" and summary["profile"] in ("direct", "inverted")
    for name, value in dict(semantic_bits=35, gate_storage_bits=35, macro_storage_bits=27,
        macro_words=4, initialized_words=16, restore_cycle=17, restored_edges=79,
        compared_output_values=237, end_cycle=96, retiming=False,
        automatic_SRAM_inference=False, process_ASIC_or_power_validated=False, physical_fpga_validated=False).items():
        assert summary[name] == value and type(summary[name]) is type(value)
    parity = int(summary["profile"] == "inverted")
    scalar = FIXTURE / "inverted" if parity else FIXTURE
    macro = FIXTURE / "sram" / ("macro-inverted.v" if parity else "macro.v")
    paths = json.loads((run / "inputs.json").read_text())
    artifacts = {role: Path(path).read_bytes() for role, path in paths.items()}
    assert set(artifacts) == {"rtl", "implementation_rtl", "macro_stub", "netlist", "models", "library",
        "synthesis_script", "synthesis_log", "relation_spec", "relation_miter", "relation_script", "relation_log", "relation_results"}
    for role, expected in (("rtl", FIXTURE / "sram/dut.v"), ("implementation_rtl", FIXTURE / "sram/implementation.v"),
                           ("macro_stub", FIXTURE / "sram/macro-stub.v"), ("library", scalar / "cells.lib"),
                           ("synthesis_script", FIXTURE / "sram/synth.tcl")):
        assert artifacts[role] == expected.read_bytes()
    assert artifacts["models"] == (scalar / "cells.v").read_bytes() + macro.read_bytes()
    shapes = [("contents", "ram", 4, 4, "memory"), ("port_address", "addr_q", 2, 1, "register"),
              ("port_write", "write_q", 1, 1, "register"), ("port_data", "data_q", 4, 1, "register"),
              ("pipeline", "read_q", 4, 1, "register")]
    adapter = json.loads((run / "cell-adapter.json").read_text())
    expected_adapter = json.loads((scalar / "cell-adapter.json").read_text())
    expected_adapter.update(adapter_version=2, models_sha256=digest(artifacts["models"]))
    for cell in expected_adapter["cells"].values():
        for storage in cell["storage"]: storage.update(width=1, depth=1, kind="register")
    expected_adapter["cells"]["CKSRAM"] = dict(storage=[dict(rtl_path=name, formal_path=name + "_reg",
        width=width, depth=depth, kind=kind, xor=0) for name, _, width, depth, kind in shapes])
    assert adapter == expected_adapter
    synth = artifacts["synthesis_log"].decode()
    assert "Error" not in synth and "CHECKPOINT_RETIMING=false\n" in synth
    for role in ("rtl", "library", "implementation_rtl", "macro_stub", "synthesis_script"):
        assert f"CHECKPOINT_SYNTH_INPUT\t{role}\t{digest(artifacts[role])}" in synth.splitlines()
    assert f"CHECKPOINT_SYNTH_OUTPUT\t{digest(artifacts['netlist'])}" in synth.splitlines()
    netlist = artifacts["netlist"].decode()
    assert re.findall(r"\bmodule\s+(\w+)", netlist) == ["StateMapDUT"]
    assert len(re.findall(r"\bCKSRAM\s+memory\s*\(", netlist)) == 1
    cell = "CKDFFN" if parity else "CKDFF"
    flops = re.findall(rf"\b{cell}\s+\\([^\s]+)\s+\(", netlist)
    assert len(flops) == len(set(flops)) == 8 and set(flops) == {f"{name}_reg[{bit}]" for name in ("held", "count") for bit in range(4)}
    cell_instances = re.findall(r"^\s*(CK\w+)\s+(?:\\[^\s]+\s+|\w+\s*)\(", netlist, re.M)
    assert set(cell_instances) <= set(adapter["cells"])
    rows = [dict(original_rtl=f"{name}[{bit}]", gate=f"{name}_reg[{bit}].state", xor=parity)
            for name in ("held", "count") for bit in range(4)]
    storage_info = {row["gate"]: (cell, 1, 0, "state") for row in rows}
    for name, original, width, depth, kind in shapes:
        for address in range(depth):
            word = f"[{address}]" if kind == "memory" else ""
            for bit in range(width):
                suffix = f"[{bit}]" if width > 1 else ""
                path = "memory." + name + word + suffix
                rows.append(dict(original_rtl=original + word + suffix, gate=path, xor=parity))
                storage_info[path] = ("CKSRAM", width, bit, name + word)
    audit_proof(artifacts, rows, True)
    manifest = json.loads((run / "manifest.json").read_text())
    mapping = json.loads((run / "asic_state_map.json").read_text())
    assert mapping["map_version"] == 8 and mapping["retiming"] is False
    assert mapping["map_type"] == "asic_state_map" and mapping["top"] == "StateMapDUT"
    assert mapping["proof"] == dict(tool="Jasper", export="complete state relation induction and output equivalence",
        assumptions=[], reset="unconstrained synchronous input",
        initial_state="complete map relation; loader enforces merged source consistency")
    assert mapping["semantic_bits"] == mapping["gate_storage_bits"] == 35
    assert mapping["build"] == {role: digest(data) for role, data in artifacts.items()}
    assert mapping["cell_adapter_hash"] == digest(canonical(adapter)) and mapping["state_manifest_hash"] == digest(canonical(manifest))
    assert manifest["reference_sha256"] == digest(artifacts["rtl"])
    semantic_shapes = [("held", 4, 1, "register"), ("count", 4, 1, "register")] + [(original, width, depth, kind) for _, original, width, depth, kind in shapes]
    assert {(s["hierarchy"], s["width"], s["depth"], s["kind"]) for s in manifest["state"]} == \
           {("Harness.dut." + name, width, depth, kind) for name, width, depth, kind in semantic_shapes}
    bits = {}
    for state in manifest["state"]:
        assert state["state_id"] == digest(canonical(dict(hierarchy=state["hierarchy"], kind=state["kind"], namespace="pre-fame-state-v1")))
        name = state["hierarchy"].removeprefix("Harness.dut.")
        for address in range(state["depth"]):
            word = f"[{address}]" if state["kind"] == "memory" else ""
            for bit in range(state["width"]):
                suffix = f"[{bit}]" if state["width"] > 1 else ""
                bits[name + word + suffix] = (state["state_id"], address, bit, name + "_reg" + word + suffix)
    entries = {entry["original_rtl"]: entry for entry in mapping["entries"]}
    assert len(entries) == len(mapping["entries"]) == 35 and set(entries) == set(bits)
    for row in rows:
        sid, address, bit, ref = bits[row["original_rtl"]]
        cell, width, gate_bit, word = storage_info[row["gate"]]
        instance = row["gate"].split(".")[0]
        formal = "state_reg" if cell != "CKSRAM" else word.split("[")[0] + "_reg" + word[len(word.split("[")[0]):] + (f"[{gate_bit}]" if width > 1 else "")
        assert entries[row["original_rtl"]] == dict(state_id=sid, address=address, bit=bit, original_rtl=row["original_rtl"],
            formal_reference="r:/WORK/StateMapDUT/" + ref, gates=[dict(formal_implementation=f"i:/WORK/StateMapDUT/{instance}/{formal}",
            cell=cell, instance=instance, storage=word, bit=gate_bit, width=width, xor=parity, proof_status="passing")])
    checkpoint = container(run / "reference/capture.rtlckpt", b"RTLCKP\x00\x01")
    trace = container(run / "reference/capture.trace", b"TRACE\x00\x00\x01")
    assert checkpoint["target_cycle"] == trace["target_cycle"] == 17 and len(trace["records"]) == 79
    raw = [json.loads(line) for line in (run / "reference/capture.jsonl").read_text().splitlines()]
    assert len(raw) == 96 and [r["cycle"] for r in raw] == list(range(96))
    records = {r["state_id"]: r for r in checkpoint["records"]}
    layout = json.loads((run / "reference/capture-layout.json").read_text())
    values = dict(zip((f["path"] for f in layout), raw[17]["values"]))
    deposits = {}
    for name, (sid, address, bit, _) in bits.items():
        state = next(s for s in manifest["state"] if s["state_id"] == sid)
        source_word = state["hierarchy"].removeprefix("Harness.dut.") + (f"[{address}]" if state["kind"] == "memory" else "")
        assert int(records[sid]["values"][address], 16) == int(values[source_word], 16)
        gate = entries[name]["gates"][0]
        path = "tb.dut." + gate["instance"] + "." + gate["storage"]
        width, value = deposits.setdefault(path, (gate["width"], 0))
        value |= (((int(records[sid]["values"][address], 16) >> bit) & 1) ^ parity) << gate["bit"]
        deposits[path] = (width, value)
    assert len(deposits) == 16 and sum(width for width, _ in deposits.values()) == 35
    assert (run / "restore.txt").read_text() == "".join(f"{p} {w} {v:0{(w+3)//4}x}\n" for p, (w, v) in sorted(deposits.items()))
    expected_matches = []
    for n, record in enumerate(trace["records"], 17):
        assert record["cycle"] == n
        oracle = dict(zip((f["path"] for f in layout), raw[n]["values"]))
        for direction in ("inputs", "outputs"):
            for name, value in record[direction].items(): assert int(value["value"], 16) == int(oracle[name], 16)
        outputs = record["outputs"]
        expected_matches.append(f"GATE_MATCH cycle={n} held={outputs['held_out']['value']} count={outputs['count_out']['value']} ram={outputs['read_out']['value']}")
    for directory, edges in (("gate-restored", 79), ("gate-uninterrupted", 96)):
        log = (run / directory / "simulation.log").read_text()
        assert [line for line in log.splitlines() if line.startswith("GATE_MATCH")] == expected_matches
        assert f"GATE_END cycle=96 edges={edges}" in log
    assert "GATE_ZERO_EDGE_READBACK cycle=17 bits=16 edges=0" in (run / "gate-restored/simulation.log").read_text()
    assert "PASS: fresh clean RTL replay cycles=17..95 samples=79 outputs_per_cycle=3 restored_words=10" in (run / "rtl-restored/simulation.log").read_text()
    assert set(summary["loader_rejections"]) == {"missing-word", "missing-pipeline", "width", "duplicate", "unknown-value", "incomplete"}
    for name in summary["loader_rejections"]:
        log = (run / "gate-restored" / (name + ".log")).read_text()
        assert "INVALID_GATE_LOAD_REJECTED edges=0 unchanged=16" in log and "RESTORE_ERROR:" in log
        assert [line for line in log.splitlines() if line.startswith("GATE_MATCH")] == expected_matches
    assert set(summary["actual_state_fault_cycles"]) == {"contents", "address", "enable", "data", "pipeline"}
    for name, cycle in summary["actual_state_fault_cycles"].items():
        log = (run / ("fault-" + name) / "simulation.log").read_text()
        assert f"GATE_MISMATCH cycle={cycle} signal=read_out" in log and log.count("GATE_MATCH cycle=") == cycle - 17
    for name in ("wrong-polarity", "missing-memory-bit", "changed-write", "changed-pipeline"):
        negative = dict(artifacts)
        for role, filename in (("relation_spec", "spec.json"), ("relation_miter", "miter.sv"),
            ("relation_script", "prove.tcl"), ("relation_results", "relation-results.tsv"), ("relation_log", "jasper.log")):
            negative[role] = (run / name / filename).read_bytes()
        candidate = json.loads(json.dumps(rows))
        if name == "wrong-polarity": candidate[8]["xor"] ^= 1
        elif name == "missing-memory-bit": candidate.pop(8)
        else:
            negative["models"] = (run / (name + ".v")).read_bytes()
            token = ("if (~port_write)" if parity else "if (port_write)") if name == "changed-write" else \
                    ("pipeline <= contents[~port_address];" if parity else "pipeline <= contents[port_address];")
            replacement = "if (1'b0)" if name == "changed-write" else "pipeline <= port_data;"
            assert negative["models"] == artifacts["models"].replace(token.encode(), replacement.encode())
        audit_proof(negative, candidate, False)
    assert set(summary["real_counterexample_rejections"]) == {"wrong-polarity", "missing-memory-bit", "changed-write", "changed-pipeline"}
    for directory in ("reference", "gate-restored", "gate-uninterrupted", "rtl-restored") + tuple("fault-" + n for n in summary["actual_state_fault_cycles"]):
        assert "Y-2026.03-SP1" in (run / directory / "compile.log").read_text()
    assert all(c["exit_code"] == (1 if Path(c["log"]).parent.name.startswith("fault-") and Path(c["log"]).name == "simulation.log" else 0)
               for c in json.loads((run / "commands.json").read_text()))
    assert summary["pending_write"] == int(values["write_q"], 16) == 1
    result = dict(status="passed", semantic_bits=35, physical_bits=35, macro_bits=27,
                  initialized_words=16, assertions=38, covers=109, boundaries=79, outputs=237,
                  actual_storage_faults=5, real_counterexample_proofs=4, atomic_loader_rejections=6)
    (run / "independent-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.run.resolve()), indent=2))


if __name__ == "__main__":
    main()
