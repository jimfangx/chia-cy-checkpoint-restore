import copy
import json
from pathlib import Path
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.formal_state_map import export_state_map, gate_deposits, sha, validate_state_map
from tools.checkpoint_formats.semantic import encode_semantic, manifest_hash, state_id


def fixture():
    base = Path(__file__).with_name("fixtures") / "formal"
    models = (base / "cells.v").read_bytes()
    adapter = json.loads((base / "cell-adapter.json").read_text())
    state = []
    for name, kind, depth in (("saved", "register", 1), ("ram", "memory", 2)):
        path = "Harness.dut." + name
        state.append(dict(state_id=state_id(path, kind), hierarchy=path, kind=kind, width=2, depth=depth,
                          signed=False, clock_domain="Harness.dut.clock", reset="none", bit_order="lsb0",
                          address_order="ascending_zero_based"))
    manifest = dict(manifest_version=1, manifest_type="rtlckpt", identity_scheme="pre-fame-state-v1",
                    circuit="Harness", dut_root="Harness.dut", clock_domain="Harness.dut.clock",
                    reference_sha256="a" * 64, state=sorted(state, key=lambda e: e["state_id"]))
    rtl = b"module DUT(input clock); reg [1:0] saved; reg [1:0] ram [0:1]; endmodule\n"
    manifest["reference_sha256"] = sha(rtl)
    # Unit evidence exercises schema/translation invariants; real tool evidence
    # and simulation are required separately by verify_formal_state_map.py.
    refs = [f"r:/WORK/DUT/{p}" for p in ("saved_reg[0]", "saved_reg[1]", "ram_reg[0][0]",
                                         "ram_reg[0][1]", "ram_reg[1][0]", "ram_reg[1][1]")]
    impls = [f"i:/WORK/DUT/g{i}/state_reg" for i in range(7)]
    rows = ["FORMAT\tformality-state-v1", "VERIFY\t1"]
    rows += [f"REGISTER\tr\t{r}" for r in refs]
    rows += [f"REGISTER\ti\t{i}" for i in impls]
    # Permuted storage names, inverted polarity, and duplicated saved[0].
    destinations = [4, 0, 5, 1, 3, 2]
    for index, dest in enumerate(destinations):
        rows.append(f"PROVEN\t{'inverted' if index == 1 else 'noninverted'}\t{refs[index]}\t{impls[dest]}")
    rows += [f"PROVEN\tnoninverted\t{refs[0]}\t{impls[6]}", "END"]
    netlist = "module DUT(input clock); wire q;\n" + "\n".join(
        f"CKDFF g{i}(.CP(clock),.D(1'b0),.Q(q));" for i in range(7)) + "\nendmodule\n"
    artifacts = dict(rtl=rtl, netlist=netlist.encode(), models=models, library=(base / "cells.lib").read_bytes(),
                     synthesis_script=b"set_db design .retime false", synthesis_log=b"CHECKPOINT_RETIMING=false\n",
                     formal_script=b"verify; report_passing_points -list", formal_log=b"Verification SUCCEEDED\n",
                     formal_configuration=b"set checkpoint_candidate_polarity -noninverted",
                     evidence=("\n".join(rows) + "\n").encode(),
                     blackboxes=b"No 'black boxes' matched current 'reference and implementation designs'")
    artifacts["synthesis_log"] += ("\n".join(
        f"CHECKPOINT_SYNTH_INPUT\t{role}\t{sha(artifacts[role])}" for role in ("rtl", "library", "synthesis_script"))
        + f"\nCHECKPOINT_SYNTH_OUTPUT\t{sha(artifacts['netlist'])}\n").encode()
    identities = "\n".join(f"INPUT\t{role}\t{sha(artifacts[role])}" for role in
                           ("rtl", "models", "netlist", "formal_script", "formal_configuration"))
    artifacts["evidence"] = artifacts["evidence"].replace(b"VERIFY\t1\n", ("VERIFY\t1\n" + identities + "\n").encode())
    build = dict(target_configuration="unit-test", rtl_build_hash="a" * 64,
                 state_manifest_hash=manifest_hash(manifest))
    checkpoint = dict(format_version=1, checkpoint_type="rtlckpt", target_cycle=17,
                      target_clock_phase="before_rising_edge", build=build,
                      records=[dict(state_id=e["state_id"], width=2, depth=e["depth"],
                                    values=["2", "1"] if e["kind"] == "memory" else ["3"])
                               for e in manifest["state"]])
    return manifest, adapter, artifacts, build, checkpoint


class FormalStateMapTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.adapter, self.artifacts, self.build, self.checkpoint = fixture()

    def export(self, artifacts=None):
        return export_state_map(self.manifest, "DUT", self.adapter, artifacts or self.artifacts)

    def rebound(self, role, data):
        # Unit failure cases explicitly represent a new synthesis/proof build;
        # separate tests require changed sources with old tool identities to fail.
        result = dict(self.artifacts, **{role: data})
        old, new = sha(self.artifacts[role]).encode(), sha(data).encode()
        for log in ("synthesis_log", "evidence"):
            result[log] = result[log].replace(old, new)
        return result

    def test_polarity_permutation_duplication_and_memory_translation(self):
        mapping = self.export()
        cycle, deposits = gate_deposits(mapping, self.manifest, self.adapter, self.artifacts,
                                        encode_semantic(self.checkpoint, self.manifest), self.build, "tb.gate")
        self.assertEqual((cycle, mapping["semantic_bits"], mapping["gate_storage_bits"]), (17, 6, 7))
        self.assertEqual({p: v for p, w, v in deposits}, {
            "tb.gate.g0.state": "0", "tb.gate.g1.state": "1", "tb.gate.g2.state": "0",
            "tb.gate.g3.state": "1", "tb.gate.g4.state": "1", "tb.gate.g5.state": "0", "tb.gate.g6.state": "1"})
        self.assertTrue(all(w == 1 for _, w, _ in deposits))

    def test_every_build_input_and_mapping_transform_bound_before_load(self):
        mapping = self.export()
        for role in self.artifacts:
            changed = dict(self.artifacts, **{role: self.artifacts[role] + b"\n"})
            with self.subTest(role=role), self.assertRaises(FormatError):
                validate_state_map(mapping, self.manifest, self.adapter, changed)
        for mutate in (lambda m: m["entries"][0]["gates"][0].update(xor=1),
                       lambda m: m["entries"].pop(),
                       lambda m: m.update(retiming=True),
                       lambda m: m["entries"][0]["gates"][0].update(proof_status="matched")):
            changed = copy.deepcopy(mapping)
            mutate(changed)
            with self.assertRaises(FormatError):
                validate_state_map(changed, self.manifest, self.adapter, self.artifacts)

    def test_global_pass_cannot_hide_missing_proof_or_storage(self):
        evidence = self.artifacts["evidence"]
        changes = [evidence.replace(b"VERIFY\t1", b"VERIFY\t0"),
                   evidence.replace(b"END\n", b""),
                   b"\n".join(line for line in evidence.split(b"\n") if not line.startswith(b"PROVEN\tinverted")),
                   evidence.replace(b"PROVEN\tnoninverted", b"MATCHED\tnoninverted", 1),
                   evidence.replace(b"noninverted", b"unknown", 1)]
        for data in changes:
            with self.subTest(data=data[:90]), self.assertRaises(FormatError):
                self.export(dict(self.artifacts, evidence=data))
        netlist = self.artifacts["netlist"].replace(b"endmodule", b"CKDFF extra(.CP(clock),.D(1'b0),.Q(q)); endmodule")
        with self.assertRaisesRegex(FormatError, "inventory mismatch"):
            self.export(self.rebound("netlist", netlist))

    def test_optimized_state_unknown_macro_hidden_state_and_retiming_rejected(self):
        # No guessed constants or initial values for optimized-away bits.
        data = b"\n".join(line for line in self.artifacts["evidence"].split(b"\n")
                          if b"saved_reg[1]" not in line)
        with self.assertRaisesRegex(FormatError, "optimized reference state"):
            self.export(dict(self.artifacts, evidence=data))
        data = self.artifacts["netlist"].replace(b"CKDFF g0", b"SRAM g0")
        with self.assertRaisesRegex(FormatError, "SRAM macro"):
            self.export(self.rebound("netlist", data))
        for data in (b"CHECKPOINT_RETIMING=true\n", b"", b"Error: synthesis failed\nCHECKPOINT_RETIMING=false\n"):
            with self.assertRaises(FormatError):
                self.export(dict(self.artifacts, synthesis_log=data))
        data = self.artifacts["models"].replace(b"reg state;", b"reg state; reg hidden;")
        with self.assertRaisesRegex(FormatError, "unaudited"):
            self.export(dict(self.artifacts, models=data))
        self.adapter["models_sha256"] = sha(data)
        with self.assertRaisesRegex(FormatError, "hidden"):
            self.export(dict(self.artifacts, models=data))

    def test_checkpoint_corruption_and_semantic_build_rejected(self):
        mapping = self.export()
        data = encode_semantic(self.checkpoint, self.manifest)
        corrupt = bytearray(data)
        corrupt[-1] ^= 1
        for payload, build in ((bytes(corrupt), self.build),
                               (data, dict(self.build, target_configuration="other"))):
            with self.assertRaises(FormatError):
                gate_deposits(mapping, self.manifest, self.adapter, self.artifacts, payload, build, "tb.gate")

    def test_stale_tool_evidence_cannot_certify_new_sources(self):
        for role in ("rtl", "models", "netlist", "library", "formal_script", "synthesis_script", "formal_configuration"):
            with self.subTest(role=role), self.assertRaises(FormatError):
                self.export(dict(self.artifacts, **{role: self.artifacts[role] + b"\n"}))

    def test_manifest_must_bind_the_formally_proven_reference(self):
        self.manifest["reference_sha256"] = "b" * 64
        with self.assertRaisesRegex(FormatError, "manifest/reference RTL identity"):
            self.export()

    def unread_artifacts(self):
        # Schema/translation oracle only. The actual unread optimization proof
        # and independent original-RTL/gate replay run in --optimize-registers.
        netlist = self.artifacts["netlist"].replace(b"CKDFF g0(.CP(clock),.D(1'b0),.Q(q));\n", b"")
        artifacts = self.rebound("netlist", netlist)
        point = b"r:/WORK/DUT/saved_reg[1]"
        evidence = artifacts["evidence"].replace(b"FORMAT\tformality-state-v1\nVERIFY\t1\n",
                    b"FORMAT\tformality-state-v3\nVERIFY\t1\nORIENTATION\trtl-reference\n")
        evidence = b"\n".join(line for line in evidence.split(b"\n") if not
                             (line.startswith(b"PROVEN\t") and point in line or
                              line == b"REGISTER\ti\ti:/WORK/DUT/g0/state_reg"))
        artifacts["evidence"] = evidence.replace(b"END\n", b"OPTIMIZED\tunread\t" + point + b"\nEND\n")
        artifacts["optimization_report"] = (b"Report : unmatched_points\n -point_type reg\n -status unread\n"
                b"1 Unmatched points (1 reference, 0 implementation):\n Ref DFF " + point + b"\n1\n")
        return artifacts

    def test_explicit_unread_state_preserved_and_omitted_from_gate_deposits(self):
        artifacts = self.unread_artifacts()
        mapping = self.export(artifacts)
        self.assertEqual((mapping["map_version"], mapping["semantic_bits"], mapping["gate_storage_bits"]), (3, 6, 6))
        omitted = [e for e in mapping["entries"] if not e["gates"]]
        self.assertEqual(len(omitted), 1)
        self.assertEqual(omitted[0]["optimization"]["kind"], "unread")
        data = encode_semantic(self.checkpoint, self.manifest)
        baseline = gate_deposits(mapping, self.manifest, self.adapter, artifacts, data, self.build, "tb.gate")
        for value in ("1", "3"):
            changed = copy.deepcopy(self.checkpoint)
            next(r for r in changed["records"] if r["state_id"] == omitted[0]["state_id"])["values"] = [value]
            self.assertEqual(gate_deposits(mapping, self.manifest, self.adapter, artifacts,
                                          encode_semantic(changed, self.manifest), self.build, "tb.gate"), baseline)

    def test_unread_classification_requires_complete_independent_report(self):
        artifacts = self.unread_artifacts()
        report = artifacts["optimization_report"]
        for changed in (b"", report.replace(b"unread", b"const0"), report.replace(b"saved_reg[1]", b"saved_reg[0]"),
                        report.replace(b"Ref DFF", b"Impl DFF"), report.replace(b"1 reference", b"0 reference"),
                        report + b" Ref DFF r:/WORK/DUT/saved_reg[1]\n"):
            with self.subTest(report=changed), self.assertRaises(FormatError):
                self.export(dict(artifacts, optimization_report=changed))
        missing_report = dict(artifacts)
        del missing_report["optimization_report"]
        with self.assertRaisesRegex(FormatError, "incomplete formal build artifacts"):
            self.export(missing_report)
        with self.assertRaisesRegex(FormatError, "incomplete formal build artifacts"):
            self.export(dict(artifacts, evidence="not binary tool evidence"))
        evidence = artifacts["evidence"]
        for changed in (evidence.replace(b"OPTIMIZED\tunread", b"OPTIMIZED\tconst0"),
                        evidence.replace(b"OPTIMIZED\tunread\tr:/WORK/DUT/saved_reg[1]\n", b""),
                        evidence.replace(b"END\n", b"OPTIMIZED\tunread\tr:/WORK/DUT/saved_reg[1]\nEND\n"),
                        evidence.replace(b"OPTIMIZED\tunread\tr:/WORK/DUT/saved_reg[1]",
                                         b"OPTIMIZED\tunread\ti:/WORK/DUT/g1/state_reg")):
            with self.subTest(evidence=changed), self.assertRaises(FormatError):
                self.export(dict(artifacts, evidence=changed))

    def test_unread_cannot_excuse_missing_live_state_or_physical_storage(self):
        artifacts = self.unread_artifacts()
        # An unread label cannot replace a passing relationship for live state.
        evidence = artifacts["evidence"].replace(b"END\n", b"OPTIMIZED\tunread\tr:/WORK/DUT/saved_reg[0]\nEND\n")
        report = artifacts["optimization_report"].replace(b"1 Unmatched points (1 reference", b"2 Unmatched points (2 reference")
        report += b" Ref DFF r:/WORK/DUT/saved_reg[0]\n"
        with self.assertRaisesRegex(FormatError, "both passing and unread"):
            self.export(dict(artifacts, evidence=evidence, optimization_report=report))
        row = next(line for line in artifacts["evidence"].splitlines() if line.startswith(b"PROVEN\t"))
        with self.assertRaisesRegex(FormatError, "unproven or unmappable gate state"):
            self.export(dict(artifacts, evidence=artifacts["evidence"].replace(row + b"\n", b"")))
        mapping = self.export(artifacts)
        with self.assertRaisesRegex(FormatError, "identity mismatch"):
            validate_state_map(mapping, self.manifest, self.adapter,
                               dict(artifacts, optimization_report=artifacts["optimization_report"] + b"\n"))

    def test_native_duplicate_suffix_requires_each_copy_proven(self):
        name = b"saved_reg[0]_SYNTHESIS_SEQ_DUP_0"
        netlist = self.artifacts["netlist"].replace(b"CKDFF g6(", b"CKDFF \\" + name + b" (")
        artifacts = self.rebound("netlist", netlist)
        artifacts["evidence"] = artifacts["evidence"].replace(b"g6/state_reg", name + b"/state_reg")
        mapping = self.export(artifacts)
        self.assertEqual(mapping["gate_storage_bits"], 7)
        self.assertEqual(sum(len(e["gates"]) > 1 for e in mapping["entries"]), 1)
        row = next(line for line in artifacts["evidence"].splitlines()
                   if line.startswith(b"PROVEN\t") and name in line)
        missing = dict(artifacts, evidence=artifacts["evidence"].replace(row + b"\n", b""))
        with self.assertRaisesRegex(FormatError, "unproven or unmappable gate state"):
            self.export(missing)
        conflict = row.replace(b"saved_reg[0]\t", b"saved_reg[1]\t")
        conflicting = dict(artifacts, evidence=artifacts["evidence"].replace(b"END\n", conflict + b"\nEND\n"))
        with self.assertRaisesRegex(FormatError, "conflicting state relationships"):
            self.export(conflicting)

    def merged_artifacts(self):
        # Schema oracle only; real Genus/Formality/VCS merging is checked by
        # --merge-registers. saved[1] shares saved[0]'s gate with opposite XOR.
        netlist = self.artifacts["netlist"]
        for index in (0, 6):
            netlist = netlist.replace(f"CKDFF g{index}(.CP(clock),.D(1'b0),.Q(q));\n".encode(), b"")
        artifacts = self.rebound("netlist", netlist)
        rows = ["FORMAT\tformality-state-v2", "VERIFY\t1", "ORIENTATION\tgate-reference"]
        for line in artifacts["evidence"].decode().splitlines()[2:-1]:
            fields = line.split("\t")
            if fields[0] == "REGISTER":
                if fields[2] in ("i:/WORK/DUT/g0/state_reg", "i:/WORK/DUT/g6/state_reg"):
                    continue
                fields[1] = "i" if fields[1] == "r" else "r"
                fields[2] = fields[1] + fields[2][1:]
            elif fields[0] == "PROVEN":
                if fields[3].endswith("g6/state_reg"):
                    continue
                fields[3] = fields[3].replace("g0/state_reg", "g4/state_reg")
                fields[2], fields[3] = "r" + fields[3][1:], "i" + fields[2][1:]
            rows.append("\t".join(fields))
        artifacts["evidence"] = ("\n".join(rows + ["END"]) + "\n").encode()
        return artifacts

    def test_reverse_proven_merge_polarity_and_atomic_checkpoint_consistency(self):
        artifacts = self.merged_artifacts()
        mapping = self.export(artifacts)
        self.assertEqual((mapping["map_version"], mapping["semantic_bits"], mapping["gate_storage_bits"]), (2, 6, 5))
        saved = next(r for r in self.checkpoint["records"] if r["depth"] == 1)
        # Both bits are initially 1, so opposite proven polarities disagree.
        with self.assertRaisesRegex(FormatError, "inconsistent merged semantic state"):
            gate_deposits(mapping, self.manifest, self.adapter, artifacts,
                          encode_semantic(self.checkpoint, self.manifest), self.build, "tb.gate")
        saved["values"] = ["1"]
        cycle, deposits = gate_deposits(mapping, self.manifest, self.adapter, artifacts,
                                        encode_semantic(self.checkpoint, self.manifest), self.build, "tb.gate")
        self.assertEqual(cycle, 17)
        self.assertEqual(len(deposits), 5)
        self.assertEqual({p: v for p, _, v in deposits}, {
            "tb.gate.g1.state": "1", "tb.gate.g2.state": "0", "tb.gate.g3.state": "1",
            "tb.gate.g4.state": "1", "tb.gate.g5.state": "0"})

    def test_reverse_merge_requires_every_alias_and_valid_orientation(self):
        artifacts = self.merged_artifacts()
        evidence = artifacts["evidence"]
        missing = b"\n".join(row for row in evidence.split(b"\n") if not
                              (row.startswith(b"PROVEN\t") and row.endswith(b"saved_reg[1]")))
        with self.assertRaisesRegex(FormatError, "unproven or unmappable semantic state"):
            self.export(dict(artifacts, evidence=missing))
        for data in (evidence.replace(b"gate-reference", b"rtl-reference"),
                     evidence.replace(b"REGISTER\ti\ti:", b"REGISTER\ti\tr:", 1),
                     evidence.replace(b"\ti:/WORK/DUT/saved_reg[1]\n", b"\ti:/WORK/DUT/unknown\n", 1)):
            with self.subTest(data=data[:90]), self.assertRaises(FormatError):
                self.export(dict(artifacts, evidence=data))
        row = next(row for row in evidence.splitlines() if row.startswith(b"PROVEN\tinverted"))
        conflict = evidence.replace(b"END\n", row.replace(b"inverted", b"noninverted") + b"\nEND\n")
        with self.assertRaisesRegex(FormatError, "conflicting passing polarity"):
            self.export(dict(artifacts, evidence=conflict))


if __name__ == "__main__":
    unittest.main()
