"""Integrity/translation oracles; actual proofs run in the CAD/VCS verifier."""

import json
from pathlib import Path
import re
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.formal_state_map import export_state_map, gate_deposits, sha
from tools.checkpoint_formats.relational_state import INPUTS, SCRIPT, miter
from tools.checkpoint_formats.replay import builds
from tools.checkpoint_formats.semantic import encode_semantic
from tools.checkpoint_formats.tests.verify_formal_state_map import fixture_manifest
from tools.checkpoint_formats.tests.verify_relational_state_map import candidate_spec


def fixture(optimized=False):
    base = Path(__file__).with_name("fixtures") / "formal"
    rtl_path = base / ("merged/optimized/dut.v" if optimized else "merged/dut.v")
    manifest, boundary = fixture_manifest(rtl_path, merge_registers=True, optimize_registers=optimized)
    adapter = json.loads((base / "cell-adapter.json").read_text())
    spec = candidate_spec("direct", True, optimized)
    gates = sorted({r["gate"].split(".")[0] for r in spec["relations"]})
    netlist = ("module StateMapDUT(input clock, input reset, input enable, input write, "
               "input [1:0] address, input [3:0] data, output [3:0] held_out, "
               "output [3:0] count_out, output [3:0] read_out); wire q;\n" +
               "\n".join(f"CKDFF \\{g} (.CP(clock),.D(1'b0),.Q(q));" for g in gates) + "\nendmodule\n").encode()
    artifacts = dict(rtl=rtl_path.read_bytes(), netlist=netlist, models=(base / "cells.v").read_bytes(),
                     library=(base / "cells.lib").read_bytes(), synthesis_script=b"retime false",
                     relation_spec=(json.dumps(spec, indent=2) + "\n").encode(), relation_script=SCRIPT.encode())
    artifacts["relation_miter"] = miter(spec, artifacts["rtl"].decode(), netlist.decode())
    artifacts["synthesis_log"] = ("CHECKPOINT_RETIMING=false\n" +
        "\n".join(f"CHECKPOINT_SYNTH_INPUT\t{role}\t{sha(artifacts[role])}" for role in ("rtl", "library", "synthesis_script")) +
        f"\nCHECKPOINT_SYNTH_OUTPUT\t{sha(netlist)}\n").encode()
    properties = []
    for name, kind in re.findall(r"^(\w+): (assert|cover) property", artifacts["relation_miter"].decode(), re.M):
        prop = "<embedded>::checkpoint_relation_miter." + name
        properties.append((prop, kind, "proven" if kind == "assert" else "covered"))
        if kind == "assert": properties.append((prop + ":precondition1", "cover", "covered"))
    artifacts["relation_results"] = ("FORMAT\tjasper-relation-v1\n" +
        "\n".join(f"INPUT\t{r}\t{sha(artifacts[r])}" for r in INPUTS) + "\n" +
        "\n".join("PROPERTY\t" + "\t".join(p) for p in properties) + "\nEND\n").encode()
    log = ["CHECKPOINT_RELATION_RESET=none", "Exiting the analysis session with status 0."]
    log += [f"CHECKPOINT_RELATION_INPUT\t{r}\t{sha(artifacts[r])}" for r in INPUTS]
    for prop, kind, status in properties:
        log += [f"CHECKPOINT_RELATION_PROPERTY\t{prop}\t{kind}\t{status}",
                f'The {"cover " if kind == "cover" else ""}property "{prop.split("::")[1]}" was {status} in 0 s.']
    artifacts["relation_log"] = ("\n".join(log) + "\n").encode()
    build = builds(manifest, boundary, "test")[0]
    checkpoint = dict(format_version=1, checkpoint_type="rtlckpt", target_cycle=17,
                      target_clock_phase="before_rising_edge", build=build,
                      records=[dict(state_id=e["state_id"], width=4, depth=e["depth"], values=["a"] * e["depth"])
                               for e in manifest["state"]])
    return manifest, adapter, artifacts, build, checkpoint


class RelationalStateTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.adapter, self.artifacts, self.build, self.checkpoint = fixture()

    def export(self, artifacts=None):
        return export_state_map(self.manifest, "StateMapDUT", self.adapter, artifacts or self.artifacts)

    def test_many_to_many_translation_is_complete_and_conflicts_reject(self):
        mapping = self.export()
        cycle, deposits = gate_deposits(mapping, self.manifest, self.adapter, self.artifacts,
                                       encode_semantic(self.checkpoint, self.manifest), self.build, "tb.dut")
        self.assertEqual((cycle, len(deposits)), (17, 28))
        self.assertEqual(sum(len(e["gates"]) for e in mapping["entries"]), 32)
        alias = next(s for s in self.manifest["state"] if s["hierarchy"].endswith(".held_copy"))
        next(r for r in self.checkpoint["records"] if r["state_id"] == alias["state_id"])["values"] = ["b"]
        with self.assertRaisesRegex(FormatError, "inconsistent merged"):
            gate_deposits(mapping, self.manifest, self.adapter, self.artifacts,
                          encode_semantic(self.checkpoint, self.manifest), self.build, "tb.dut")

    def test_omitted_alias_or_copy_rejects_before_global_proof_claim(self):
        for kind in ("alias", "copy"):
            spec = json.loads(self.artifacts["relation_spec"])
            spec["relations"] = [r for r in spec["relations"] if not
                                 (r["original_rtl"] == "held[0]" if kind == "alias" else "SYNTHESIS_SEQ_DUP" in r["gate"])]
            artifacts = dict(self.artifacts, relation_spec=json.dumps(spec).encode(),
                             relation_miter=miter(spec, self.artifacts["rtl"].decode(), self.artifacts["netlist"].decode()))
            with self.subTest(kind=kind), self.assertRaisesRegex(FormatError, "unproven or unmappable"):
                self.export(artifacts)

    def test_bounded_failed_missing_or_vacuous_properties_reject(self):
        results = self.artifacts["relation_results"]
        for changed in (results.replace(b"\tproven", b"\tbounded", 1), results.replace(b"\tproven", b"\tcex", 1),
                        results.replace(b"\tcovered", b"\tunreachable", 1),
                        b"\n".join(r for r in results.split(b"\n") if b"step_0:precondition1" not in r)):
            with self.assertRaisesRegex(FormatError, "unproven or vacuous"):
                self.export(dict(self.artifacts, relation_results=changed))

    def test_weakened_miter_and_changed_inputs_reject(self):
        weakened = self.artifacts["relation_miter"].replace(b"relation |=>", b"1'b0 |=>", 1)
        with self.assertRaisesRegex(FormatError, "unaudited relational"):
            self.export(dict(self.artifacts, relation_miter=weakened))
        for role in INPUTS:
            with self.subTest(role=role), self.assertRaises(FormatError):
                self.export(dict(self.artifacts, **{role: self.artifacts[role] + b"\n"}))

    def test_extra_or_truncated_outputs_and_wrong_inputs_are_unsupported(self):
        spec = json.loads(self.artifacts["relation_spec"])
        rtl, netlist = self.artifacts["rtl"].decode(), self.artifacts["netlist"].decode()
        for text in (rtl.replace("output [3:0] held_out", "output [7:0] held_out"),
                     rtl.replace("input [3:0] data", "input [7:0] data"),
                     rtl.replace("input clock", "output extra, input clock")):
            with self.assertRaisesRegex(FormatError, "interface"):
                miter(spec, text, netlist)
        with self.assertRaisesRegex(FormatError, "interface"):
            miter(spec, rtl, netlist.replace("output [3:0] count_out", "output [7:0] count_out"))

    def test_machine_pass_without_engine_result_or_raw_identity_rejects(self):
        raw = self.artifacts["relation_log"]
        for changed in (b"\n".join(r for r in raw.split(b"\n") if b'The property "checkpoint_relation_miter.step_0"' not in r),
                        raw.replace(b"CHECKPOINT_RELATION_INPUT\trtl\t", b"CHECKPOINT_RELATION_INPUT\tother\t")):
            with self.assertRaises(FormatError): self.export(dict(self.artifacts, relation_log=changed))

    def test_unread_induction_keeps_inventory_and_accepts_arbitrary_unread_values(self):
        manifest, adapter, artifacts, build, checkpoint = fixture(True)
        mapping = export_state_map(manifest, "StateMapDUT", adapter, artifacts)
        self.assertEqual((mapping["map_version"], mapping["semantic_bits"], mapping["gate_storage_bits"]), (6, 32, 28))
        unread = [e for e in mapping["entries"] if not e["gates"]]
        self.assertEqual({e["original_rtl"] for e in unread}, {f"unused[{bit}]" for bit in range(4)})
        self.assertTrue(all(e["optimization"] == dict(kind="unread", proof_status="proven", report="relation_results") for e in unread))
        baseline = gate_deposits(mapping, manifest, adapter, artifacts, encode_semantic(checkpoint, manifest), build, "tb.dut")
        record = next(r for r in checkpoint["records"] if r["state_id"] == unread[0]["state_id"])
        for value in ("0", "f"):
            record["values"] = [value]
            self.assertEqual(gate_deposits(mapping, manifest, adapter, artifacts, encode_semantic(checkpoint, manifest), build, "tb.dut"), baseline)

    def test_unread_candidates_missing_outside_inventory_or_overlap_reject(self):
        manifest, adapter, artifacts, _, _ = fixture(True)
        for case in ("missing", "outside", "overlap", "duplicate", "unsupported"):
            spec = json.loads(artifacts["relation_spec"])
            if case == "missing": spec["unread"].pop()
            elif case == "outside": spec["unread"][-1] = "unknown[0]"
            elif case == "overlap": spec["unread"][-1] = "held[0]"
            elif case == "duplicate": spec["unread"][-1] = spec["unread"][0]
            else: spec["unread"][-1] = "ram[0][0]"
            with self.subTest(case=case), self.assertRaises(FormatError):
                changed = dict(artifacts, relation_spec=json.dumps(spec).encode(),
                               relation_miter=miter(spec, artifacts["rtl"].decode(), artifacts["netlist"].decode()))
                export_state_map(manifest, "StateMapDUT", adapter, changed)

    def test_unread_coverage_or_output_engine_evidence_missing_rejects(self):
        manifest, adapter, artifacts, _, _ = fixture(True)
        for role, needle in (("relation_results", b".unread_0_0\t"),
                             ("relation_log", b'The cover property "checkpoint_relation_miter.unread_0_1"'),
                             ("relation_results", b".output_held\t")):
            changed = dict(artifacts, **{role: b"\n".join(row for row in artifacts[role].split(b"\n") if needle not in row)})
            with self.subTest(role=role, needle=needle), self.assertRaises(FormatError):
                export_state_map(manifest, "StateMapDUT", adapter, changed)

    def test_malformed_relational_schema_fails_explicitly(self):
        spec = json.loads(self.artifacts["relation_spec"])
        for changed in (None, [], 1, dict(spec, relation_version=True),
                        dict(spec, relation_version=2.0), dict(spec, relation_version=9),
                        dict(spec, unread=["unused[0]"])):
            with self.subTest(spec=changed), self.assertRaises(FormatError):
                miter(changed, self.artifacts["rtl"].decode(), self.artifacts["netlist"].decode())


if __name__ == "__main__":
    unittest.main()
