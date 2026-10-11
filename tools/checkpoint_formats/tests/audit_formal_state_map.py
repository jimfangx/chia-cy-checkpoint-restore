"""Independent small-DUT evidence audit; does not import the exporter/codec."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


def digest(data):
    return hashlib.sha256(data).hexdigest()


def container(path, magic):
    data = path.read_bytes()
    assert data[:8] == magic
    length = struct.unpack(">Q", data[8:16])[0]
    assert len(data) == length + 48
    assert hashlib.sha256(data[:-32]).digest() == data[-32:]
    return json.loads(data[16:-32])


def passing_pairs(report, gate_reference=False):
    """Read every implementation in each human one-to-many DFF group."""
    pairs = []
    for block in re.split(r"\n\s*\n", report):
        refs = re.findall(r"^\s*Ref\s+DFF\s+(r:\S+)\s*$", block, re.M)
        impls = re.findall(r"^\s*Impl\s+DFF\s+(?:\(-\)\s+)?(i:\S+)\s*$", block, re.M)
        if refs or impls:
            assert len(refs) == 1 and impls, "incomplete human passing group"
            pairs.extend((refs[0], impl) for impl in impls)
    assert len(pairs) == len(set(pairs)), "duplicate human passing relationship"
    assert len(pairs) == len(re.findall(r"^\s*Impl\s+DFF\s", report, re.M))
    if gate_reference:
        return [("r" + impl[1:], "i" + ref[1:]) for ref, impl in pairs]
    return pairs


def audit(run):
    mapping = json.loads((run / "asic_state_map.json").read_text())
    manifest = json.loads((run / "manifest.json").read_text())
    paths = json.loads((run / "inputs.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    adapter = json.loads((run / "cell-adapter.json").read_text())
    profile = summary["profile"]
    assert profile in ("direct", "inverted")
    polarity = int(profile == "inverted")
    cell = "CKDFFN" if polarity else "CKDFF"
    duplicated = summary.get("duplicate_registers", False)
    assert type(duplicated) is bool
    reordered = summary.get("reorder_registers", False)
    assert type(reordered) is bool
    slots = (2, 0, 3, 1) if reordered else (0, 1, 2, 3)
    counter_name = lambda bit: f"{'gate_count' if reordered else 'count'}_reg[{slots[bit]}]"
    assert summary.get("counter_bit_to_gate_slot", list(slots)) == list(slots)
    assert summary.get("reordered_semantic_bits", 0) == (4 if reordered else 0)
    gate_bits = 28 if duplicated else 24
    merged = summary.get("merge_registers", False)
    assert type(merged) is bool and not (merged and duplicated)
    optimized = summary.get("optimize_registers", False)
    assert type(optimized) is bool and not (merged and optimized)
    constants = summary.get("constant_registers", False)
    assert type(constants) is bool and (not constants or optimized)
    semantic_bits = (28 if merged or optimized else 24) + (4 if constants else 0)
    cases = ("missing", "width", "duplicate", "unknown-value", "incomplete") + (("missing-copy",) if duplicated else ())
    assert mapping["semantic_bits"] == semantic_bits and mapping["gate_storage_bits"] == gate_bits
    assert mapping["map_version"] == (4 if constants else 3 if optimized else 2 if merged else 1)
    for role, path in paths.items():
        assert digest(Path(path).read_bytes()) == mapping["build"][role], role
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    assert digest(encoded) == mapping["state_manifest_hash"]
    assert manifest["reference_sha256"] == digest(Path(paths["rtl"]).read_bytes())
    assert digest(json.dumps(adapter, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()) == mapping["cell_adapter_hash"]
    assert adapter["models_sha256"] == digest(Path(paths["models"]).read_bytes())
    assert mapping["retiming"] is False
    assert "\nCHECKPOINT_RETIMING=false\n" in Path(paths["synthesis_log"]).read_text()
    expected = {(state["state_id"], address, bit) for state in manifest["state"]
                for address in range(state["depth"]) for bit in range(state["width"])}
    assert len(expected) == semantic_bits
    assert {(e["state_id"], e["address"], e["bit"]) for e in mapping["entries"]} == expected
    assert len(mapping["entries"]) == semantic_bits
    # Cross-check the machine export against Formality's human passing report.
    passing = (run / "formal/passing.rpt").read_text()
    pairs = passing_pairs(passing, merged)
    assert len(pairs) == gate_bits + (4 if merged else 0)
    assert len(re.findall(r"^\s*Impl\s+Port\s", passing, re.M)) == 12
    map_pairs = [(e["formal_reference"], gate["formal_implementation"])
                 for e in mapping["entries"] for gate in e["gates"]]
    assert set(pairs) == set(map_pairs)
    for status, xor in (("noninverted", 0), ("inverted", 1)):
        report = (run / "formal" / f"passing-{status}.rpt").read_text()
        status_pairs = passing_pairs(report, merged)
        assert set(status_pairs) == {(e["formal_reference"], g["formal_implementation"])
                                    for e in mapping["entries"] for g in e["gates"] if g["xor"] == xor}
    cell_instances = re.findall(rf"\b{cell}\s+\\([^\s]+)\s+\(", Path(paths["netlist"]).read_text())
    assert len(cell_instances) == len(set(cell_instances)) == gate_bits
    mapped_instances = [gate["instance"] for e in mapping["entries"] for gate in e["gates"]]
    assert set(mapped_instances) == set(cell_instances) and len(mapped_instances) == len(pairs)
    evidence = Path(paths["evidence"]).read_text().splitlines()
    proven = [line.split("\t")[2:] for line in evidence if line.startswith("PROVEN\t")]
    if merged:
        assert evidence[:3] == ["FORMAT\tformality-state-v2", "VERIFY\t1", "ORIENTATION\tgate-reference"]
        proven = [["r" + impl[1:], "i" + ref[1:]] for ref, impl in proven]
    elif optimized:
        assert evidence[:3] == ["FORMAT\tformality-state-v3", "VERIFY\t1", "ORIENTATION\trtl-reference"]
    else:
        assert evidence[:2] == ["FORMAT\tformality-state-v1", "VERIFY\t1"]
    assert len(proven) == len(pairs) and {tuple(row) for row in proven} == set(pairs)
    gate_side, rtl_side = ("r", "i") if merged else ("i", "r")
    assert {"i" + line.split("\t")[2][1:] for line in evidence if line.startswith(f"REGISTER\t{gate_side}\t")} == {impl for _, impl in pairs}
    omitted = [e for e in mapping["entries"] if not e["gates"]]
    unread_omitted = [e for e in omitted if e["optimization"]["kind"] == "unread"]
    assert {"r" + line.split("\t")[2][1:] for line in evidence if line.startswith(f"REGISTER\t{rtl_side}\t")} == \
           {ref for ref, _ in pairs} | {e["formal_reference"] for e in omitted}
    assert len(unread_omitted) == summary.get("unread_semantic_bits", 0) == (4 if optimized else 0)
    assert len(omitted) == (4 if optimized else 0) + (4 if constants else 0)
    if optimized:
        report = (run / "formal/optimized-unread.rpt").read_text()
        assert digest(report.encode()) == mapping["build"]["optimization_report"]
        assert re.search(r"^\s*-status unread\s*$", report, re.M)
        assert "4 Unmatched points (4 reference, 0 implementation):" in report
        unread = set(re.findall(r"^\s*Ref\s+DFF\s+(r:\S+)\s*$", report, re.M))
        assert unread == {f"r:/WORK/StateMapDUT/unused_reg[{bit}]" for bit in range(4)}
        assert unread == {e["formal_reference"] for e in unread_omitted}
        assert set(line for line in evidence if line.startswith("OPTIMIZED\t")) == \
               {f"OPTIMIZED\tunread\t{point}" for point in unread}
        assert summary["altered_unread_rtl_replayed"] is True
        assert summary["observed_unread_formal_failed"] is True
        assert "Verification FAILED" in (run / "formal-observed-unread/formal.log").read_text()
        observed_evidence = (run / "formal-observed-unread/evidence.tsv").read_text()
        assert "\nVERIFY\t0\n" in observed_evidence and "OPTIMIZED\tunread\t" not in observed_evidence
        expected_observed = Path(paths["rtl"]).read_text().replace("assign held_out = held", "assign held_out = held ^ unused")
        assert expected_observed != Path(paths["rtl"]).read_text()
        assert (run / "observed-unread.v").read_text() == expected_observed
        for case in ("missing-classification", "unsupported-constant", "live-state-classified-unread"):
            assert summary["optimization_evidence_rejections"][case]
            assert (run / (case + "-evidence.tsv")).read_text() != "\n".join(evidence) + "\n"
    assert summary.get("duplicated_semantic_bits", 0) == (4 if duplicated else 0)
    for entry in mapping["entries"]:
        state = next(s for s in manifest["state"] if s["state_id"] == entry["state_id"])
        name = state["hierarchy"].split(".")[-1]
        name += f"[{entry['address']}]" if state["kind"] == "memory" else ""
        assert entry["original_rtl"] == name + f"[{entry['bit']}]"
        if name == "unused":
            assert optimized and not entry["gates"]
            assert entry["optimization"] == dict(kind="unread", proof_status="tool_classified", report="optimization_report")
            continue
        if name == "constant":
            assert constants and not entry["gates"]
            assert entry["optimization"] == dict(kind="constant", value=(10 >> entry["bit"]) & 1,
                min_target_cycle=1, proof_status="proven", report="constant_results",
                property=f"<embedded>::StateMapDUT.checkpoint_constant_proof.constant_{entry['bit']}")
            continue
        expected_instances = {entry["formal_reference"].rsplit("/", 1)[1]}
        if reordered and name == "count":
            expected_instances = {counter_name(entry["bit"])}
        if merged and name == "held":
            expected_instances = {f"held_copy_reg[{entry['bit']}]"}
        if duplicated and name == "count":
            expected_instances.add(counter_name(entry["bit"]) + "_SYNTHESIS_SEQ_DUP_0")
        assert {gate["instance"] for gate in entry["gates"]} == expected_instances
        for gate in entry["gates"]:
            assert gate["xor"] == polarity and gate["storage"] == "state" and gate["proof_status"] == "passing"
            assert gate["cell"] == cell
    checkpoint = container(run / "reference/capture.rtlckpt", b"RTLCKP\x00\x01")
    trace = container(run / "reference/capture.trace", b"TRACE\x00\x00\x01")
    assert checkpoint["target_cycle"] == trace["target_cycle"] == 17
    assert checkpoint["target_clock_phase"] == trace["target_clock_phase"] == "before_rising_edge"
    layout = json.loads((run / "reference/capture-layout.json").read_text())
    captured = [json.loads(line) for line in (run / "reference/capture.jsonl").read_text().splitlines()]
    records = {r["state_id"]: r for r in checkpoint["records"]}
    if optimized:
        altered = container(run / "altered-unread.rtlckpt", b"RTLCKP\x00\x01")
        expected_altered = json.loads(json.dumps(checkpoint))
        unused_id = next(s["state_id"] for s in manifest["state"] if s["hierarchy"].endswith(".unused"))
        row = next(r for r in expected_altered["records"] if r["state_id"] == unused_id)
        row["values"][0] = f"{int(row['values'][0], 16) ^ 15:x}"
        assert altered == expected_altered and altered != checkpoint
        assert f"PASS: fresh clean RTL replay cycles=17..95 samples=79 outputs_per_cycle=3 restored_words={8 if constants else 7}" in \
               (run / "rtl-altered-unread/simulation.log").read_text()
        altered_records = {r["state_id"]: r for r in altered["records"]}
        semantic_rows = set()
        for state in manifest["state"]:
            name = state["hierarchy"].split(".")[-1]
            for address, value in enumerate(altered_records[state["state_id"]]["values"]):
                suffix = f"[{address}]" if state["kind"] == "memory" else ""
                semantic_rows.add(f"semantic_replay_tb.dut.{name}{suffix} 4 {value}")
        assert set((run / "rtl-altered-unread/restore.txt").read_text().splitlines()) == semantic_rows
    if constants:
        assert summary["constant_semantic_bits"] == 4
        spec = json.loads(Path(paths["constant_spec"]).read_text())
        assert spec == dict(constant_version=1, top="StateMapDUT", bits=[
            dict(signal="constant", bit=bit, width=4, value=(10 >> bit) & 1) for bit in range(4)])
        bind = Path(paths["constant_bind"]).read_text()
        expected_bind = "module checkpoint_constants(input clock, input c0, input c1, input c2, input c3);\n"
        expected_bind += "".join(f"constant_{bit}: assert property (@(posedge clock) 1'b1 |=> c{bit} == 1'b{(10 >> bit) & 1});\n" for bit in range(4))
        expected_bind += "checkpoint_edge: cover property (@(posedge clock) 1'b1 ##1 1'b1);\nendmodule\n"
        expected_bind += "bind StateMapDUT checkpoint_constants checkpoint_constant_proof(.clock(clock), .c0(constant[0]), .c1(constant[1]), .c2(constant[2]), .c3(constant[3]));\n"
        assert bind == expected_bind
        script = Path(paths["constant_script"]).read_text()
        assert "reset -none\n" in script and "clock clock\n" in script
        assert not re.search(r"^\s*(assume|set_constant|reset -expression|stopat|abstract)\b", script, re.M)
        log = Path(paths["constant_log"]).read_text()
        assert "ERROR" not in log and "Exiting the analysis session with status 0." in log
        results = Path(paths["constant_results"]).read_text().splitlines()
        assert results[0] == "FORMAT\tjasper-constant-v1" and results[-1] == "END"
        inputs = [row.split("\t")[1:] for row in results if row.startswith("INPUT\t")]
        assert len(inputs) == 4 and dict(inputs) == {role: digest(Path(paths[role]).read_bytes()) for role in
            ("rtl", "constant_spec", "constant_bind", "constant_script")}
        expected_properties = {f"<embedded>::StateMapDUT.checkpoint_constant_proof.constant_{bit}": ("assert", "proven") for bit in range(4)}
        expected_properties.update({p + ":precondition1": ("cover", "covered") for p in list(expected_properties)})
        expected_properties["<embedded>::StateMapDUT.checkpoint_constant_proof.checkpoint_edge"] = ("cover", "covered")
        rows = [row.split("\t")[1:] for row in results if row.startswith("PROPERTY\t")]
        assert len(rows) == 9 and {p: (kind, status) for p, kind, status in rows} == expected_properties
        raw = re.findall(r"^CHECKPOINT_CONSTANT_PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$", log, re.M)
        assert len(raw) == 9 and {p: (kind, status) for p, kind, status in raw} == expected_properties
        for prop, (kind, status) in expected_properties.items():
            name = prop.split("::", 1)[1]
            assert re.search(r'The (?:cover )?property "' + re.escape(name) + r'" was ' + status + r' (?:in|at) ', log)
        for case in ("wrong-value", "conditional-update"):
            negative = (run / ("constant-" + case) / "constant-results.tsv").read_text()
            assert "\tassert\tcex\n" in negative
            assert (run / ("constant-" + case) / "jasper.log").read_text().count("counterexample") > 0
        conditional = (run / "conditional-constant.v").read_text()
        assert conditional == Path(paths["rtl"]).read_text().replace("constant <= 4'b1010;", "if (enable) constant <= 4'b1010;")
        for bit in range(4):
            conflicting = container(run / f"conflicting-constant-{bit}.rtlckpt", b"RTLCKP\x00\x01")
            expected_conflict = json.loads(json.dumps(checkpoint))
            cid = next(s["state_id"] for s in manifest["state"] if s["hierarchy"].endswith(".constant"))
            row = next(r for r in expected_conflict["records"] if r["state_id"] == cid)
            assert row["values"] == ["a"]
            row["values"][0] = f"{10 ^ (1 << bit):x}"
            assert conflicting == expected_conflict
            assert summary["constant_rejections"][f"checkpoint-bit-{bit}"] == f"checkpoint conflicts with proven constant state: constant[{bit}]"
        early = container(run / "pre-horizon.rtlckpt", b"RTLCKP\x00\x01")
        expected_early = json.loads(json.dumps(checkpoint))
        expected_early["target_cycle"] = 0
        assert early == expected_early
        assert summary["constant_rejections"]["pre-horizon"] == "checkpoint precedes proven constant horizon"
        conflict_log = (run / "rtl-conflicting-constant/simulation.log").read_text()
        assert "cycle=17" in conflict_log and "PASS: fresh clean RTL replay" not in conflict_log
        assert not re.search(r"GATE_MATCH|REPLAY_MATCH", conflict_log)
        assert set(summary["constant_rejections"]) == {"pre-horizon", "wrong-value", "conditional-update", "missing-proof",
            "missing-property", "bounded-proof", "vacuous-proof", "wrong-raw-status"} | {f"checkpoint-bit-{bit}" for bit in range(4)}
        assert all(summary["constant_rejections"].values())
    expected_deposits = set()
    for entry in mapping["entries"]:
        value = int(records[entry["state_id"]]["values"][entry["address"]], 16)
        for gate in entry["gates"]:
            expected_deposits.add(f"tb.dut.{gate['instance']}.{gate['storage']} 1 {((value >> entry['bit']) & 1) ^ polarity:x}")
    assert len(expected_deposits) == gate_bits
    assert (run / "restore.txt").read_text().splitlines() == sorted(expected_deposits)
    for field, value in zip(layout, captured[17]["values"]):
        if "state_id" in field:
            assert records[field["state_id"]]["values"][field["address"]] == value
    gate_lines = lambda path: [line for line in path.read_text().splitlines() if line.startswith("GATE_MATCH ")]
    restored = gate_lines(run / "gate-restored/simulation.log")
    assert restored == gate_lines(run / "gate-uninterrupted/simulation.log")
    assert len(restored) == len(trace["records"]) == 79
    for record, line in zip(trace["records"], restored):
        assert record["cycle"] == 17 + trace["records"].index(record)
        fields = dict(zip((f["path"] for f in layout), captured[record["cycle"]]["values"]))
        for direction in ("inputs", "outputs"):
            for port, value in record[direction].items():
                assert value["value"] == fields[port]
        expected_line = "GATE_MATCH cycle=%d held=%s count=%s ram=%s" % (
            record["cycle"], fields["held_out"], fields["count_out"], fields["read_out"])
        assert line == expected_line
    for case in cases:
        text = (run / "gate-restored" / (case + ".log")).read_text()
        assert text.count(f"RESTORE_VERIFY: matched {gate_bits} semantic words before first DUT edge") == 2
        assert f"INVALID_GATE_LOAD_REJECTED edges=0 unchanged={gate_bits}" in text
        assert gate_lines(run / "gate-restored" / (case + ".log")) == restored
    assert f"GATE_ZERO_EDGE_READBACK cycle=17 bits={gate_bits} edges=0" in (run / "gate-restored/simulation.log").read_text()
    fault = (run / "gate-restored/fault.log").read_text()
    assert len(gate_lines(run / "gate-restored/fault.log")) == 12
    assert "GATE_MISMATCH cycle=29 signal=count_out" in fault
    assert "Verification FAILED" in (run / "formal-fault/formal.log").read_text()
    assert "\nVERIFY\t0\n" in (run / "formal-fault/evidence.tsv").read_text()
    assert "Verification FAILED" in (run / "formal-wrong-polarity/formal.log").read_text()
    assert "\nVERIFY\t0\n" in (run / "formal-wrong-polarity/evidence.tsv").read_text()
    assert summary["wrong_polarity_formal_failed"] is True
    if reordered:
        synth_log = Path(paths["synthesis_log"]).read_text()
        renames = [line.split("\t")[1:] for line in synth_log.splitlines() if line.startswith("CHECKPOINT_REORDER\t")]
        expected_renames = {(f"count_reg[{bit}]" + suffix, counter_name(bit) + suffix)
                            for bit in range(4) for suffix in
                            (("", "_SYNTHESIS_SEQ_DUP_0") if duplicated else ("",))}
        assert len(renames) == len(expected_renames) and set(map(tuple, renames)) == expected_renames
        assert "Verification FAILED" in (run / "formal-wrong-permutation/formal.log").read_text()
        assert "\nVERIFY\t0\n" in (run / "formal-wrong-permutation/evidence.tsv").read_text()
        assert summary["wrong_permutation_rejected"] == "formal tool did not prove equivalence"
        assert summary["swapped_destination_map_rejected"] == "ASIC map or build/proof identity mismatch"
        swapped = json.loads((run / "swapped-destinations-map.json").read_text())
        expected_swap = json.loads(json.dumps(mapping))
        count_entries = sorted((e for e in expected_swap["entries"] if e["original_rtl"].startswith("count[")),
                               key=lambda e: e["bit"])
        count_entries[0]["gates"], count_entries[1]["gates"] = count_entries[1]["gates"], count_entries[0]["gates"]
        assert swapped == expected_swap and swapped != mapping
    if duplicated:
        assert "Duplicated 4 register(s), creating 4 new registers" in Path(paths["synthesis_log"]).read_text()
        assert f"i:/WORK/StateMapDUT/{counter_name(3)}_SYNTHESIS_SEQ_DUP_0/state_reg" in (run / "formal-fault/failing.rpt").read_text()
        assert f"dut.\\{counter_name(0)}_SYNTHESIS_SEQ_DUP_0 .state" in (run / "gate-restored/tb.sv").read_text()
        assert summary["missing_copy_proof_rejected"] == "unproven or unmappable gate state"
        missing = (run / "missing-copy-evidence.tsv").read_text().splitlines()
        assert missing == [line for line in evidence if not
                           (line.startswith("PROVEN\t") and counter_name(0) + "_SYNTHESIS_SEQ_DUP_0/state_reg" in line)]
    if merged:
        actual_shared = {}
        for entry in mapping["entries"]:
            for gate in entry["gates"]:
                actual_shared.setdefault(gate["formal_implementation"], []).append(entry["original_rtl"])
        shared = {gate: sources for gate, sources in actual_shared.items() if len(sources) > 1}
        assert len(shared) == summary["merged_gate_bits"] == 4
        assert shared == summary["merged_semantic_sources"]
        for bit in range(4):
            assert set(shared[f"i:/WORK/StateMapDUT/held_copy_reg[{bit}]/state_reg"]) == {f"held[{bit}]", f"held_copy[{bit}]"}
        held = next(s for s in manifest["state"] if s["hierarchy"].endswith(".held"))
        alias = next(s for s in manifest["state"] if s["hierarchy"].endswith(".held_copy"))
        assert records[held["state_id"]]["values"] == records[alias["state_id"]]["values"]
        inconsistent = container(run / "inconsistent-merged.rtlckpt", b"RTLCKP\x00\x01")
        expected_inconsistent = json.loads(json.dumps(checkpoint))
        row = next(r for r in expected_inconsistent["records"] if r["state_id"] == alias["state_id"])
        row["values"][0] = f"{int(row['values'][0], 16) ^ 1:x}"
        assert inconsistent == expected_inconsistent
        assert summary["inconsistent_merge_rejected"] == "inconsistent merged semantic state for gate storage: tb.dut.held_copy_reg[0].state"
        missing = (run / "missing-alias-evidence.tsv").read_text().splitlines()
        assert missing == [line for line in evidence if not
                           (line.startswith("PROVEN\t") and line.endswith("\ti:/WORK/StateMapDUT/held_reg[0]"))]
        assert summary["missing_alias_proof_rejected"] == "unproven or unmappable semantic state"
        assert "Verification FAILED" in (run / "formal-wrong-alias/formal.log").read_text()
        assert "\nVERIFY\t0\n" in (run / "formal-wrong-alias/evidence.tsv").read_text()
        assert summary["wrong_alias_formal_rejected"] == "formal tool did not prove equivalence"
    result = dict(status="passed", independently_checked_state_bits=semantic_bits, ram_words=4,
                  independently_checked_gate_bits=gate_bits, duplicated_semantic_bits=4 if duplicated else 0,
                  merged_gate_bits=4 if merged else 0, inconsistent_merged_checkpoint_rejected=merged,
                  unread_semantic_bits=4 if optimized else 0, observed_unread_formal_failed=optimized,
                  constant_semantic_bits=4 if constants else 0, independent_constant_predicates_proven=constants,
                  profile=profile, independently_checked_inverted_bits=gate_bits * polarity,
                  reordered_semantic_bits=4 if reordered else 0,
                  wrong_permutation_hypothesis_formal_failed=reordered,
                  restored_pre_edge_boundaries=79, compared_outputs=237, loader_atomic_rejections=len(cases),
                  first_actual_gate_fault_cycle=29, actual_faulty_netlist_formal_failed=True,
                  wrong_polarity_hypothesis_formal_failed=True,
                  scope="synthesized " + profile + " correspondence; other transformations/macros remain unvalidated")
    (run / "independent-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--run", type=Path, required=True)
    audit(parser.parse_args().run)


if __name__ == "__main__":
    main()
