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


def passing_pairs(report):
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
    cases = ("missing", "width", "duplicate", "unknown-value", "incomplete") + (("missing-copy",) if duplicated else ())
    assert mapping["semantic_bits"] == 24 and mapping["gate_storage_bits"] == gate_bits
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
    assert len(expected) == 24
    assert {(e["state_id"], e["address"], e["bit"]) for e in mapping["entries"]} == expected
    assert len(mapping["entries"]) == 24
    # Cross-check the machine export against Formality's human passing report.
    passing = (run / "formal/passing.rpt").read_text()
    pairs = passing_pairs(passing)
    assert len(pairs) == gate_bits
    map_pairs = [(e["formal_reference"], gate["formal_implementation"])
                 for e in mapping["entries"] for gate in e["gates"]]
    assert set(pairs) == set(map_pairs)
    for status, xor in (("noninverted", 0), ("inverted", 1)):
        report = (run / "formal" / f"passing-{status}.rpt").read_text()
        status_pairs = passing_pairs(report)
        assert set(status_pairs) == {(e["formal_reference"], g["formal_implementation"])
                                    for e in mapping["entries"] for g in e["gates"] if g["xor"] == xor}
    cell_instances = re.findall(rf"\b{cell}\s+\\([^\s]+)\s+\(", Path(paths["netlist"]).read_text())
    assert len(cell_instances) == len(set(cell_instances)) == gate_bits
    mapped_instances = [gate["instance"] for e in mapping["entries"] for gate in e["gates"]]
    assert set(mapped_instances) == set(cell_instances) and len(mapped_instances) == gate_bits
    evidence = Path(paths["evidence"]).read_text().splitlines()
    proven = [line.split("\t")[2:] for line in evidence if line.startswith("PROVEN\t")]
    assert len(proven) == gate_bits and {tuple(row) for row in proven} == set(pairs)
    assert {line.split("\t")[2] for line in evidence if line.startswith("REGISTER\ti\t")} == {impl for _, impl in pairs}
    assert {line.split("\t")[2] for line in evidence if line.startswith("REGISTER\tr\t")} == {ref for ref, _ in pairs}
    assert summary.get("duplicated_semantic_bits", 0) == (4 if duplicated else 0)
    for entry in mapping["entries"]:
        state = next(s for s in manifest["state"] if s["state_id"] == entry["state_id"])
        name = state["hierarchy"].split(".")[-1]
        name += f"[{entry['address']}]" if state["kind"] == "memory" else ""
        assert entry["original_rtl"] == name + f"[{entry['bit']}]"
        expected_instances = {entry["formal_reference"].rsplit("/", 1)[1]}
        if reordered and name == "count":
            expected_instances = {counter_name(entry["bit"])}
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
    expected_deposits = []
    for entry in mapping["entries"]:
        value = int(records[entry["state_id"]]["values"][entry["address"]], 16)
        for gate in entry["gates"]:
            expected_deposits.append(f"tb.dut.{gate['instance']}.{gate['storage']} 1 {((value >> entry['bit']) & 1) ^ polarity:x}")
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
    result = dict(status="passed", independently_checked_state_bits=24, ram_words=4,
                  independently_checked_gate_bits=gate_bits, duplicated_semantic_bits=4 if duplicated else 0,
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
