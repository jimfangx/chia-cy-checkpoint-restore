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
                     evidence=("\n".join(rows) + "\n").encode(),
                     blackboxes=b"No 'black boxes' matched current 'reference and implementation designs'")
    artifacts["synthesis_log"] += ("\n".join(
        f"CHECKPOINT_SYNTH_INPUT\t{role}\t{sha(artifacts[role])}" for role in ("rtl", "library", "synthesis_script"))
        + f"\nCHECKPOINT_SYNTH_OUTPUT\t{sha(artifacts['netlist'])}\n").encode()
    identities = "\n".join(f"INPUT\t{role}\t{sha(artifacts[role])}" for role in ("rtl", "models", "netlist", "formal_script"))
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
        for role in ("rtl", "models", "netlist", "library", "formal_script", "synthesis_script"):
            with self.subTest(role=role), self.assertRaises(FormatError):
                self.export(dict(self.artifacts, **{role: self.artifacts[role] + b"\n"}))


if __name__ == "__main__":
    unittest.main()
