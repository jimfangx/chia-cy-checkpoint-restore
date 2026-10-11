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


def audit(run):
    mapping = json.loads((run / "asic_state_map.json").read_text())
    manifest = json.loads((run / "manifest.json").read_text())
    paths = json.loads((run / "inputs.json").read_text())
    for role, path in paths.items():
        assert digest(Path(path).read_bytes()) == mapping["build"][role], role
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    assert digest(encoded) == mapping["state_manifest_hash"]
    assert mapping["retiming"] is False
    assert "\nCHECKPOINT_RETIMING=false\n" in Path(paths["synthesis_log"]).read_text()
    expected = {(state["state_id"], address, bit) for state in manifest["state"]
                for address in range(state["depth"]) for bit in range(state["width"])}
    assert len(expected) == 24
    assert {(e["state_id"], e["address"], e["bit"]) for e in mapping["entries"]} == expected
    assert len(mapping["entries"]) == 24
    # Cross-check the machine export against Formality's human passing report.
    passing = (run / "formal/passing.rpt").read_text()
    pairs = re.findall(r"Ref\s+DFF\s+(r:\S+)\s+Impl\s+DFF\s+(i:\S+)", passing)
    assert len(pairs) == len(set(pairs)) == 24
    map_pairs = [(e["formal_reference"], gate["formal_implementation"])
                 for e in mapping["entries"] for gate in e["gates"]]
    assert set(pairs) == set(map_pairs)
    cell_instances = re.findall(r"\bCKDFF\s+\\([^\s]+)\s+\(", Path(paths["netlist"]).read_text())
    assert len(cell_instances) == len(set(cell_instances)) == 24
    mapped_instances = [gate["instance"] for e in mapping["entries"] for gate in e["gates"]]
    assert set(mapped_instances) == set(cell_instances) and len(mapped_instances) == 24
    for entry in mapping["entries"]:
        state = next(s for s in manifest["state"] if s["state_id"] == entry["state_id"])
        name = state["hierarchy"].split(".")[-1]
        name += f"[{entry['address']}]" if state["kind"] == "memory" else ""
        assert entry["original_rtl"] == name + f"[{entry['bit']}]"
        for gate in entry["gates"]:
            assert gate["xor"] == 0 and gate["storage"] == "state" and gate["proof_status"] == "passing"
    checkpoint = container(run / "reference/capture.rtlckpt", b"RTLCKP\x00\x01")
    trace = container(run / "reference/capture.trace", b"TRACE\x00\x00\x01")
    assert checkpoint["target_cycle"] == trace["target_cycle"] == 17
    assert checkpoint["target_clock_phase"] == trace["target_clock_phase"] == "before_rising_edge"
    layout = json.loads((run / "reference/capture-layout.json").read_text())
    captured = [json.loads(line) for line in (run / "reference/capture.jsonl").read_text().splitlines()]
    records = {r["state_id"]: r for r in checkpoint["records"]}
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
    for case in ("missing", "width", "duplicate", "unknown-value", "incomplete"):
        text = (run / "gate-restored" / (case + ".log")).read_text()
        assert text.count("RESTORE_VERIFY: matched 24 semantic words before first DUT edge") == 2
        assert "INVALID_GATE_LOAD_REJECTED edges=0 unchanged=24" in text
        assert gate_lines(run / "gate-restored" / (case + ".log")) == restored
    assert "GATE_ZERO_EDGE_READBACK cycle=17 bits=24 edges=0" in (run / "gate-restored/simulation.log").read_text()
    fault = (run / "gate-restored/fault.log").read_text()
    assert len(gate_lines(run / "gate-restored/fault.log")) == 12
    assert "GATE_MISMATCH cycle=29 signal=count_out" in fault
    assert "Verification FAILED" in (run / "formal-fault/formal.log").read_text()
    assert "\nVERIFY\t0\n" in (run / "formal-fault/evidence.tsv").read_text()
    result = dict(status="passed", independently_checked_state_bits=24, ram_words=4,
                  restored_pre_edge_boundaries=79, compared_outputs=237, loader_atomic_rejections=5,
                  first_actual_gate_fault_cycle=29, actual_faulty_netlist_formal_failed=True,
                  scope="direct correspondence; transformations/macros remain unvalidated")
    (run / "independent-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--run", type=Path, required=True)
    audit(parser.parse_args().run)


if __name__ == "__main__":
    main()
