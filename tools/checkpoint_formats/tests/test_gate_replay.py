"""Failure-path unit tests; real CAD/VCS acceptance uses verify_gate_replay."""

import copy
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError, encode
from tools.checkpoint_formats.formal_state_map import export_state_map, sha
from tools.checkpoint_formats.gate_activity import audit_activity, read_saif
from tools.checkpoint_formats.gate_replay import prepare_gate_replay, validate_design_boundary
from tools.checkpoint_formats.replay import builds
from tools.checkpoint_formats.semantic import encode_semantic
from tools.checkpoint_formats.tests.test_formal_state_map import fixture


class GateReplayTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.adapter, self.artifacts, _, self.checkpoint = fixture()
        for role in ("rtl", "netlist"):
            previous = self.artifacts[role]
            self.artifacts[role] = previous.replace(b"module DUT(input clock)",
                b"module DUT(input clock, input [1:0] data, output [1:0] out)")
            for log in ("synthesis_log", "evidence"):
                self.artifacts[log] = self.artifacts[log].replace(sha(previous).encode(), sha(self.artifacts[role]).encode())
        self.manifest["reference_sha256"] = sha(self.artifacts["rtl"])
        self.mapping = export_state_map(self.manifest, "DUT", self.adapter, self.artifacts)
        self.boundary = dict(boundary_version=1, dut_module="DUT", dut_root="Harness.dut",
                             clock="clock", sample_phase="before_rising_edge", ports=[
                                 dict(name="clock", direction="input", width=1),
                                 dict(name="data", direction="input", width=2),
                                 dict(name="out", direction="output", width=2)])
        build, trace_build = builds(self.manifest, self.boundary, "unit-test")
        self.checkpoint["build"] = build
        self.trace = dict(format_version=1, checkpoint_type="trace", target_cycle=17,
                          target_clock_phase="before_rising_edge", build=trace_build, records=[
                              dict(cycle=17, inputs=dict(data=dict(width=2, value="2")),
                                   outputs=dict(out=dict(width=2, value="1")))])

    def reject(self, pattern, **changes):
        values = dict(mapping=self.mapping, manifest=self.manifest, boundary=self.boundary,
                      adapter=self.adapter, artifacts=self.artifacts,
                      checkpoint_data=encode_semantic(self.checkpoint, self.manifest),
                      trace_data=encode("trace", self.trace), configuration="unit-test")
        values.update(changes)
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "unpublished"
            with self.assertRaisesRegex(FormatError, pattern):
                prepare_gate_replay(**values, out=out)
            self.assertFalse(out.exists(), "validation failed after publishing loader files")

    def test_trace_cut_and_checkpoint_are_independently_bound(self):
        trace = copy.deepcopy(self.trace)
        trace.update(target_cycle=18)
        trace["records"][0]["cycle"] = 18
        self.reject("cycle mismatch", trace_data=encode("trace", trace))
        self.reject("incompatible build", configuration="wrong-build")
        raw = bytearray(encode("trace", self.trace)); raw[-1] ^= 1
        self.reject("checksum", trace_data=bytes(raw))

    def test_incomplete_or_wrong_width_boundary_rejects_before_files(self):
        for mutate in (lambda t: t["records"][0]["inputs"].clear(),
                       lambda t: t["records"][0]["outputs"].clear(),
                       lambda t: t["records"][0]["outputs"]["out"].update(width=3),
                       lambda t: t["records"][0]["inputs"].update(extra=dict(width=1, value="0"))):
            trace = copy.deepcopy(self.trace); mutate(trace)
            self.reject("boundary signals", trace_data=encode("trace", trace))

    def test_changed_map_or_current_netlist_cannot_load(self):
        changed = copy.deepcopy(self.mapping); changed["entries"][0]["gates"][0]["xor"] ^= 1
        self.reject("map or build/proof", mapping=changed)
        self.reject("identity|bound", artifacts=dict(self.artifacts, netlist=self.artifacts["netlist"]+b"\n"))

    def test_level_one_container_is_not_semantic_state(self):
        self.reject("magic|type", checkpoint_data=b"FSCKPT\0\1"+b"\0"*60)

    def test_boundary_cannot_omit_actual_inputs_or_outputs(self):
        incomplete = copy.deepcopy(self.boundary)
        incomplete["ports"] = [p for p in incomplete["ports"] if p["name"] != "data"]
        self.reject("DUT boundary", boundary=incomplete)
        for text in ("module DUT(clock, out); input clock; output [1:0] out; endmodule",
                     "module DUT(input clock, output [1:0] out); endmodule"):
            with self.assertRaisesRegex(FormatError, "DUT boundary"):
                validate_design_boundary(text, "DUT", self.boundary["ports"])


class GateActivityTests(unittest.TestCase):
    # A small hand-calculated activity oracle, not simulation acceptance evidence.
    saif = '''(SAIFILE (SAIFVERSION "2.0") (DIRECTION "backward")
      (PROGRAM_NAME "VCS Y-2026.03-SP1_Full64") (TIMESCALE 1 ns) (DURATION 6)
      (INSTANCE tb (INSTANCE dut
       (NET (clock (T0 4)(T1 2)(TX 0)(TC 4)(IG 0)))
       (INSTANCE g (NET
        (contents\\[0\\]\\[0\\] (T0 3)(T1 3)(TX 0)(TC 1)(IG 0))
        (contents\\[0\\]\\[1\\] (T0 3)(T1 3)(TX 0)(TC 1)(IG 0)))))))'''
    vcd = '''$version Synopsys VCS version Y-2026.03-SP1_Full64 $end
$timescale 1ps $end
$scope module tb $end
$scope module dut $end
$var wire 1 ! clock $end
$scope module g $end
$var reg 2 " contents[0] [1:0] $end
$upscope $end
$upscope $end
$upscope $end
$enddefinitions $end
#1000
$dumpvars
0!
b10 "
$end
#2000
1!
#3000
0!
#4000
b01 "
#5000
1!
#6000
0!
'''
    mapping = dict(gate_storage_bits=2, entries=[dict(gates=[
        dict(instance="g", storage="contents[0]", width=2, bit=bit)]) for bit in range(2)])

    def test_memory_bit_order_and_dwell_match_hand_calculated_oracle(self):
        metrics = audit_activity(self.saif, self.vcd, self.mapping, 1000, 7000, 2)
        self.assertEqual(metrics["storage_transitions"], 2)
        self.assertEqual(metrics["mapped_storage_bits"], 2)

    def test_missing_unknown_or_fabricated_activity_rejects(self):
        for saif, vcd in (
            (self.saif.replace("(TC 1)", "(TC 2)", 1), self.vcd),
            (self.saif.replace("(TX 0)", "(TX 1)", 1), self.vcd),
            (self.saif.replace("contents", "missing", 1), self.vcd),
            (self.saif, self.vcd.replace("b10", "bx0")),
            (self.saif, self.vcd.replace("#1000", "#0")),
            (self.saif.replace("VCS Y-2026.03-SP1_Full64", "RTL-SAIF"), self.vcd)):
            with self.subTest(saif=saif, vcd=vcd), self.assertRaises(FormatError):
                audit_activity(saif, vcd, self.mapping, 1000, 7000, 2)

    def test_read_only_memory_witness_does_not_hide_wrong_bit_activity(self):
        witnessed = self.vcd.replace('contents[0]', 'word_0')
        witnesses = {f"tb.dut.g.contents[0][{bit}]": f"tb.dut.g.word_0[{bit}]" for bit in range(2)}
        audit_activity(self.saif, witnessed, self.mapping, 1000, 7000, 2, witnesses)
        swapped = {name: path.replace("[0]", "[1]") if path.endswith("[0]") else path.replace("[1]", "[0]")
                   for name, path in witnesses.items()}
        # Equal dwell times still differ in value ordering with a noncentral transition.
        biased_saif = self.saif.replace("(T0 3)(T1 3)", "(T0 2)(T1 4)", 1).replace(
            "(T0 3)(T1 3)", "(T0 4)(T1 2)", 1)
        biased_vcd = witnessed.replace("#4000", "#3000")
        audit_activity(biased_saif, biased_vcd, self.mapping, 1000, 7000, 2, witnesses)
        with self.assertRaisesRegex(FormatError, "activity mismatch"):
            audit_activity(biased_saif, biased_vcd, self.mapping, 1000, 7000, 2, swapped)

    def test_duplicate_and_unbalanced_saif_reject(self):
        for text in (self.saif[:-1], self.saif.replace("(TC 1)", "(TC 1)(TC 1)", 1)):
            with self.assertRaises(FormatError):
                read_saif(text)


if __name__ == "__main__":
    unittest.main()
