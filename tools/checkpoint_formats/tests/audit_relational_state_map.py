"""Independent raw-evidence audit for the flat merged/duplicated Jasper fixture."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

from .audit_formal_state_map import container


def digest(data):
    return hashlib.sha256(data).hexdigest()


def audit(run):
    mapping = json.loads((run / "asic_state_map.json").read_text())
    manifest = json.loads((run / "manifest.json").read_text())
    paths = json.loads((run / "inputs.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    artifacts = {k: Path(v).read_bytes() for k, v in paths.items()}
    assert set(artifacts) == {"rtl", "netlist", "models", "library", "synthesis_script", "synthesis_log",
                              "relation_spec", "relation_miter", "relation_script", "relation_log", "relation_results"}
    assert mapping["build"] == {k: digest(v) for k, v in artifacts.items()}
    assert mapping["map_version"] == 5 and mapping["retiming"] is False
    assert summary["status"] == "passed" and summary["merge_registers"] and summary["duplicate_registers"]
    assert mapping["semantic_bits"] == mapping["gate_storage_bits"] == 28
    assert mapping["proof"] == dict(tool="Jasper", export="complete state relation induction and output equivalence",
                                  assumptions=[], reset="unconstrained synchronous input",
                                  initial_state="complete map relation; loader enforces merged source consistency")
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    assert digest(canonical(manifest)) == mapping["state_manifest_hash"]
    assert manifest["reference_sha256"] == digest(artifacts["rtl"])
    expected_ports = {name: ("input", width) for name, width in
                      (("clock", 1), ("reset", 1), ("enable", 1), ("write", 1), ("address", 2), ("data", 4))}
    expected_ports.update({name: ("output", 4) for name in ("held_out", "count_out", "read_out")})
    rtl_header = re.search(r"\bmodule StateMapDUT\s*\((.*?)\);", artifacts["rtl"].decode(), re.S)[1]
    declared = re.findall(r"\b(input|output)\s+(?:\[(\d+):0\]\s*)?(\w+)", rtl_header)
    assert len(declared) == 9 and {n: (d, int(h)+1 if h else 1) for d,h,n in declared} == expected_ports
    net_ports = {}
    for direction, high, names in re.findall(r"\b(input|output)\s+(?:\[(\d+):0\]\s*)?([\w\s,]+);", artifacts["netlist"].decode()):
        for name in names.replace(" ", "").replace("\n", "").split(","):
            assert name not in net_ports
            net_ports[name] = (direction, int(high)+1 if high else 1)
    assert net_ports == expected_ports
    adapter = json.loads((run / "cell-adapter.json").read_text())
    assert mapping["cell_adapter_hash"] == digest(canonical(adapter))
    assert adapter["models_sha256"] == digest(artifacts["models"])
    synth = artifacts["synthesis_log"].decode()
    assert "CHECKPOINT_RETIMING=false\n" in synth and "Error" not in synth
    for role in ("rtl", "library", "synthesis_script"):
        assert f"CHECKPOINT_SYNTH_INPUT\t{role}\t{digest(artifacts[role])}" in synth.splitlines()
    assert f"CHECKPOINT_SYNTH_OUTPUT\t{digest(artifacts['netlist'])}" in synth.splitlines()
    polarity = int(summary["profile"] == "inverted")
    assert summary["profile"] in ("direct", "inverted")
    cell = "CKDFFN" if polarity else "CKDFF"
    slots = (2, 0, 3, 1) if summary["reorder_registers"] else (0, 1, 2, 3)
    counter = lambda bit: f"{'gate_count' if summary['reorder_registers'] else 'count'}_reg[{slots[bit]}]"
    expected_rows = []
    for name in ("held", "held_copy", "count"):
        for bit in range(4):
            gate = f"held_copy_reg[{bit}]" if name.startswith("held") else counter(bit)
            for suffix in (("", "_SYNTHESIS_SEQ_DUP_0") if name == "count" else ("",)):
                expected_rows.append(dict(original_rtl=f"{name}[{bit}]", gate=gate + suffix + ".state", xor=polarity))
    for address in range(4):
        for bit in range(4):
            expected_rows.append(dict(original_rtl=f"ram[{address}][{bit}]", gate=f"ram_reg[{address}][{bit}].state", xor=polarity))
    spec = json.loads(artifacts["relation_spec"])
    assert spec == dict(relation_version=1, top="StateMapDUT", relations=expected_rows)
    physical = {r["gate"] for r in expected_rows}
    instances = re.findall(rf"\b{cell}\s+\\([^\s]+)\s+\(", artifacts["netlist"].decode())
    assert len(instances) == len(set(instances)) == 28
    assert {i + ".state" for i in instances} == physical
    expected_state = {(s["state_id"], a, b) for s in manifest["state"] for a in range(s["depth"]) for b in range(s["width"])}
    assert {(e["state_id"], e["address"], e["bit"]) for e in mapping["entries"]} == expected_state
    assert len(mapping["entries"]) == 28
    pairs = []
    for entry in mapping["entries"]:
        state = next(s for s in manifest["state"] if s["state_id"] == entry["state_id"])
        name = state["hierarchy"].split(".")[-1]
        path = name + (f"[{entry['address']}]" if name == "ram" else "") + f"[{entry['bit']}]"
        assert path == entry["original_rtl"]
        assert entry["formal_reference"] == "r:/WORK/StateMapDUT/" + path.replace(name, name + "_reg", 1)
        for gate in entry["gates"]:
            assert gate["cell"] == cell and gate["storage"] == "state" and gate["bit"] == 0
            assert gate["xor"] == polarity and gate["proof_status"] == "passing"
            assert gate["formal_implementation"] == "i:/WORK/StateMapDUT/" + gate["instance"] + "/state_reg"
            pairs.append(dict(original_rtl=path, gate=gate["instance"] + ".state", xor=gate["xor"]))
    assert len(pairs) == 32 and {tuple(sorted(r.items())) for r in pairs} == {tuple(sorted(r.items())) for r in expected_rows}
    # Independently reconstruct the audited miter, including every antecedent.
    texts = [re.sub(r"\bmodule\s+StateMapDUT\b", "module " + name, artifacts[role].decode())
             for role, name in (("rtl", "checkpoint_reference"), ("netlist", "checkpoint_implementation"))]
    lines = texts + ["module checkpoint_relation_miter(input clock, reset, enable, write,",
                    "  input [1:0] address, input [3:0] data);",
                    "wire [3:0] r_held, r_count, r_read, i_held, i_count, i_read;"]
    for prefix, module, instance in (("r", "checkpoint_reference", "reference"), ("i", "checkpoint_implementation", "implementation")):
        lines.append(f"{module} {instance}(.clock(clock),.reset(reset),.enable(enable),.write(write),.address(address),.data(data),"
                     f".held_out({prefix}_held),.count_out({prefix}_count),.read_out({prefix}_read));")
    gate_expr = lambda path: "implementation.\\" + path.split(".")[0] + " ." + path.split(".")[1]
    expressions = [f"(reference.{r['original_rtl']} == ({gate_expr(r['gate'])} ^ 1'b{r['xor']}))" for r in expected_rows]
    lines.append("wire relation = " + " &&\n  ".join(expressions) + ";")
    lines.extend(f"step_{n}: assert property (@(posedge clock) relation |=> {expr});" for n, expr in enumerate(expressions))
    lines.extend(f"output_{port}: assert property (@(posedge clock) relation |-> r_{port} == i_{port});" for port in ("held", "count", "read"))
    lines.append("checkpoint_edge: cover property (@(posedge clock) relation ##1 relation);")
    for n, gate in enumerate(sorted(physical)):
        for value in (0, 1):
            lines.append(f"bit_{n}_{value}: cover property (@(posedge clock) relation && {gate_expr(gate)} == 1'b{value});")
    assert artifacts["relation_miter"] == "\n".join(lines + ["endmodule", ""]).encode()
    source = Path(__file__).parents[1] / "relational_state.py"
    script = next(ast.literal_eval(n.value) for n in ast.parse(source.read_text()).body if
                  isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SCRIPT" for t in n.targets))
    assert artifacts["relation_script"] == script.encode()
    expected = {}
    for name in [f"step_{n}" for n in range(32)] + [f"output_{port}" for port in ("held", "count", "read")]:
        prop = "<embedded>::checkpoint_relation_miter." + name
        expected[prop] = ("assert", "proven")
        expected[prop + ":precondition1"] = ("cover", "covered")
    expected["<embedded>::checkpoint_relation_miter.checkpoint_edge"] = ("cover", "covered")
    for n in range(28):
        for value in (0, 1): expected[f"<embedded>::checkpoint_relation_miter.bit_{n}_{value}"] = ("cover", "covered")
    result_lines = artifacts["relation_results"].decode().splitlines()
    assert result_lines[0] == "FORMAT\tjasper-relation-v1" and result_lines[-1] == "END"
    inputs, properties = {}, {}
    for row in [line.split("\t") for line in result_lines[1:-1]]:
        if row[0] == "INPUT":
            assert len(row) == 3 and row[1] not in inputs
            inputs[row[1]] = row[2]
        else:
            assert len(row) == 4 and row[0] == "PROPERTY" and row[1] not in properties
            properties[row[1]] = tuple(row[2:])
    assert inputs == {r: digest(artifacts[r]) for r in ("rtl", "netlist", "models", "relation_spec", "relation_miter", "relation_script")}
    assert properties == expected
    log = artifacts["relation_log"].decode()
    assert "ERROR" not in log and "CHECKPOINT_RELATION_RESET=none" in log and "Exiting the analysis session with status 0." in log
    raw = re.findall(r"^CHECKPOINT_RELATION_PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$", log, re.M)
    assert len(raw) == len(expected) and {p: (k, s) for p, k, s in raw} == expected
    raw_inputs = re.findall(r"^CHECKPOINT_RELATION_INPUT\t([^\t\n]+)\t([^\t\n]+)$", log, re.M)
    assert len(raw_inputs) == 6 and dict(raw_inputs) == inputs
    for prop, (_, status) in expected.items():
        assert re.search(r'The (?:cover )?property "' + re.escape(prop.split("::")[1]) + r'" was ' + status + r' (?:in|at) ', log)
    checkpoint = container(run / "reference/capture.rtlckpt", b"RTLCKP\x00\x01")
    trace = container(run / "reference/capture.trace", b"TRACE\x00\x00\x01")
    assert checkpoint["target_cycle"] == trace["target_cycle"] == 17 and len(trace["records"]) == 79
    records = {r["state_id"]: r for r in checkpoint["records"]}
    deposits = {}
    for entry in mapping["entries"]:
        bit = (int(records[entry["state_id"]]["values"][entry["address"]], 16) >> entry["bit"]) & 1
        for gate in entry["gates"]:
            path = "tb.dut." + gate["instance"] + ".state"
            value = str(bit ^ gate["xor"])
            assert path not in deposits or deposits[path] == value
            deposits[path] = value
    assert (run / "restore.txt").read_text() == "".join(f"{p} 1 {v}\n" for p, v in sorted(deposits.items()))
    conflicting = container(run / "inconsistent-merged.rtlckpt", b"RTLCKP\x00\x01")
    original = json.loads(json.dumps(checkpoint))
    state = next(s for s in manifest["state"] if s["hierarchy"].endswith(".held_copy"))
    record = next(r for r in original["records"] if r["state_id"] == state["state_id"])
    record["values"][0] = f"{int(record['values'][0],16)^1:x}"
    assert original == conflicting and summary["conflicting_merged_checkpoint_rejected"] is True
    restored = (run / "gate-restored/simulation.log").read_text()
    assert "GATE_ZERO_EDGE_READBACK cycle=17 bits=28 edges=0" in restored and "GATE_END cycle=96 edges=79" in restored
    matches = [l for l in restored.splitlines() if l.startswith("GATE_MATCH")]
    assert len(matches) == 79
    uninterrupted = (run / "gate-uninterrupted/simulation.log").read_text()
    assert "GATE_END cycle=96 edges=96" in uninterrupted
    assert matches == [l for l in uninterrupted.splitlines() if l.startswith("GATE_MATCH")]
    for directory in ("reference", "gate-restored", "gate-uninterrupted", "gate-shared-fault"):
        assert "Y-2026.03-SP1" in (run / directory / "compile.log").read_text()
    for record, line in zip(trace["records"], matches):
        match = re.fullmatch(r"GATE_MATCH cycle=(\d+) held=([a-f0-9]+) count=([a-f0-9]+) ram=([a-f0-9]+)", line)
        assert int(match[1]) == record["cycle"]
        assert [int(match[i],16) for i in (2,3,4)] == [int(record["outputs"][p]["value"],16) for p in ("held_out","count_out","read_out")]
    assert len(summary["loader_rejections"]) == 6
    for name in summary["loader_rejections"]:
        text = (run / "gate-restored" / (name + ".log")).read_text()
        assert "INVALID_GATE_LOAD_REJECTED edges=0 unchanged=28" in text and "GATE_END cycle=96 edges=79" in text
    for name, signal in (("gate-restored", "count_out"), ("gate-shared-fault", "held_out")):
        text = (run / name / "fault.log").read_text()
        assert f"GATE_MISMATCH cycle=29 signal={signal}" in text and text.count("GATE_MATCH cycle=") == 12
    for name in ("wrong-polarity", "wrong-alias", "wrong-permutation", "changed-clone-D", "changed-shared-D"):
        negative = (run / name / "relation-results.tsv").read_text()
        assert "\tcex\n" in negative
        raw = (run / name / "jasper.log").read_text()
        assert "ERROR" not in raw and "Exiting the analysis session with status 0." in raw
        for prop in re.findall(r"^PROPERTY\t([^\t\n]+)\tassert\tcex$", negative, re.M):
            assert re.search(r'A counterexample \(cex\) with \d+ cycles was found for the property "' +
                             re.escape(prop.split("::")[1]) + r'"', raw)
        assert name in summary["formal_negatives"]
    assert "\tunreachable\n" in (run / "vacuous-relation/relation-results.tsv").read_text()
    assert 'was proven unreachable' in (run / "vacuous-relation/jasper.log").read_text()
    assert summary["formal_negatives"]["vacuous-relation"] == "unproven or vacuous state correspondence"
    for name in ("wrong-polarity", "wrong-alias", "wrong-permutation", "changed-clone-D", "changed-shared-D", "vacuous-relation"):
        implementation = run / (name + ".v") if name.startswith("changed-") else Path(paths["netlist"])
        expected_inputs = {"rtl": Path(paths["rtl"]), "netlist": implementation, "models": Path(paths["models"]),
                           "relation_spec": run / name / "spec.json", "relation_miter": run / name / "miter.sv",
                           "relation_script": run / name / "prove.tcl"}
        assert expected_inputs["relation_script"].read_bytes() == script.encode()
        inputs_expected = {r: digest(p.read_bytes()) for r,p in expected_inputs.items()}
        negative = (run / name / "relation-results.tsv").read_text()
        machine_inputs = re.findall(r"^INPUT\t([^\t\n]+)\t([^\t\n]+)$", negative, re.M)
        raw = (run / name / "jasper.log").read_text()
        raw_inputs = re.findall(r"^CHECKPOINT_RELATION_INPUT\t([^\t\n]+)\t([^\t\n]+)$", raw, re.M)
        assert len(machine_inputs) == len(raw_inputs) == 6 and dict(machine_inputs) == dict(raw_inputs) == inputs_expected
    for name in ("missing-alias", "missing-copy"):
        assert name in summary["formal_negatives"] and len(json.loads((run / (name + "-spec.json")).read_text())["relations"]) == 31
    result = dict(status="passed", semantic_bits=28, physical_bits=28, proven_relations=32,
                  asserted_properties=35, covered_properties=92, compared_outputs=237,
                  restore_cycle=17, end_cycle=96, loader_rejections=6, actual_faults=2,
                  fresh_counterexample_proofs=5, actual_vacuous_proof_rejected=True)
    (run / "independent-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--run", type=Path, required=True)
    audit(parser.parse_args().run)
