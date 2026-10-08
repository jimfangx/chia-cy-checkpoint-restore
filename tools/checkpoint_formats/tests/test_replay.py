import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError, encode
from tools.checkpoint_formats.replay import package_capture, prepare_capture, prepare_replay
from tools.checkpoint_formats.semantic import state_id


def fixture():
    entries = []
    for name, kind, depth in (("saved", "register", 1), ("ram", "memory", 2)):
        path = "Harness.dut." + name
        entries.append(dict(state_id=state_id(path, kind), hierarchy=path, kind=kind,
                            width=9, depth=depth, signed=False, clock_domain="Harness.dut.clock",
                            reset="none", bit_order="lsb0", address_order="ascending_zero_based"))
    manifest = dict(manifest_version=1, manifest_type="rtlckpt", identity_scheme="pre-fame-state-v1",
                    circuit="Harness", dut_root="Harness.dut", clock_domain="Harness.dut.clock",
                    reference_sha256="a" * 64, state=sorted(entries, key=lambda e: e["state_id"]))
    boundary = dict(boundary_version=1, dut_module="DUT", dut_root="Harness.dut", clock="clock",
                    sample_phase="before_rising_edge", ports=[dict(name=n, direction=d, width=w)
                    for n, d, w in (("clock", "input", 1), ("data", "input", 9), ("result", "output", 9))])
    rtl = "module DUT(input clock, input [8:0] data, output [8:0] result);\n" + \
          "reg [8:0] saved;\nreg [8:0] ram [0:1];\nendmodule\n"
    return manifest, boundary, rtl


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.manifest, self.boundary, self.rtl = fixture()

    def capture(self):
        raw = self.out / "raw.jsonl"
        raw.write_text("\n".join(json.dumps(dict(cycle=c, values=["101", "102", "103", "104", "105"]))
                                 for c in range(4)))
        return raw

    def test_complete_memory_register_and_boundary_replay_generation(self):
        prepare_capture(self.manifest, self.boundary, self.rtl, self.rtl + "DUT dut();", self.out)
        package_capture(self.manifest, self.boundary, "test", self.capture(), 1, 3, self.out)
        self.replay()
        self.assertIn("cycle=3 signal=result", (self.out / "replay.sv").read_text())
        self.assertEqual(len((self.out / "restore.txt").read_text().splitlines()), 3)
        self.assertIn("ram[1]", (self.out / "restore.txt").read_text())
        self.assertIn("@(posedge clock)", (self.out / "capture.sv").read_text())

    def replay(self, trace=None, checkpoint=None):
        prepare_replay(self.manifest, self.boundary, "test",
                       checkpoint or (self.out / "capture.rtlckpt").read_bytes(),
                       trace or (self.out / "capture.trace").read_bytes(), self.out)

    def test_lost_extra_threaded_and_duplicate_instance_state_rejected(self):
        for transformed in (self.rtl.replace("saved", "renamed") + "DUT dut();",
                            self.rtl.replace("reg [8:0] saved;", "reg [8:0] saved [0:0];") + "DUT dut();",
                            self.rtl.replace("endmodule", "reg extra; endmodule") + "DUT dut();",
                            self.rtl + "DUT dut(); DUT other();"):
            with self.assertRaises(FormatError):
                prepare_capture(self.manifest, self.boundary, self.rtl, transformed, self.out)

    def test_unknown_values_missing_edges_and_short_capture_rejected(self):
        for mutate in (lambda r: r[1]["values"].__setitem__(2, "10x"),
                       lambda r: r[1].update(cycle=3),
                       lambda r: r.pop(),
                       lambda r: r[1]["values"].pop()):
            raw = self.capture()
            rows = [json.loads(line) for line in raw.read_text().splitlines()]
            mutate(rows)
            raw.write_text("\n".join(json.dumps(row) for row in rows))
            with self.assertRaises(FormatError):
                package_capture(self.manifest, self.boundary, "test", raw, 1, 3, self.out)

    def test_valid_checksum_cannot_hide_incomplete_boundary_or_cycle_mismatch(self):
        _, trace = package_capture(self.manifest, self.boundary, "test", self.capture(), 1, 3, self.out)
        for mutate in (lambda t: t["records"][0]["inputs"].pop("data"),
                       lambda t: t["records"][0]["outputs"]["result"].update(width=10),
                       lambda t: t.update(target_cycle=2, records=t["records"][1:])):
            changed = copy.deepcopy(trace)
            mutate(changed)
            with self.assertRaises(FormatError):
                self.replay(trace=encode("trace", changed))

    def test_corruption_and_incompatible_boundary_rejected_before_restore_generation(self):
        package_capture(self.manifest, self.boundary, "test", self.capture(), 1, 3, self.out)
        bad = bytearray((self.out / "capture.rtlckpt").read_bytes())
        bad[-1] ^= 1
        with self.assertRaisesRegex(FormatError, "checksum"):
            self.replay(checkpoint=bytes(bad))
        self.boundary["ports"][1]["width"] = 10
        with self.assertRaisesRegex(FormatError, "incompatible build"):
            self.replay()
        self.assertFalse((self.out / "restore.txt").exists())


if __name__ == "__main__":
    unittest.main()
