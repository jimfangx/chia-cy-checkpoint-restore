import copy
import hashlib
import unittest

from tools.checkpoint_formats.codec import FormatError, canonical
from tools.checkpoint_formats.simulator import (check_generated_rtl, generated_capture,
                                                generated_words, validate_generated_manifest)


def fixture():
    state = []
    for path, width, depth, kind in (("Top.counter", 257, 1, "register"), ("Top.fifo", 9, 2, "memory")):
        identity = hashlib.sha256(canonical(dict(hierarchy=path, kind=kind,
                                                namespace="generated-simulator-state-v1"))).hexdigest()
        state.append(dict(state_id=identity, hierarchy=path, module="Top", kind=kind, width=width,
                          depth=depth, signed=False, clock_expression="clock", reset_expression="none",
                          adapter="firrtl-" + kind + "-v1", bit_order="lsb0", address_order="ascending_zero_based"))
    return dict(manifest_version=1, manifest_type="fsckpt-generated", identity_scheme="generated-simulator-state-v1",
                circuit="Top", root_module="Top", scope="generated_rtl_only", external_runtime_required=True,
                reference_sha256=hashlib.sha256(b"reference").hexdigest(),
                instances=[dict(hierarchy="Top", module="Top", implementation_sha256="a"*64)],
                state=sorted(state, key=lambda e: e["state_id"]))


class SimulatorInventoryTest(unittest.TestCase):
    def test_wide_and_memory_values_are_complete_and_independent(self):
        m = fixture()
        words = list(generated_words(m))
        values = [f"{(1 << w['width']) - 1:0{(w['width']+3)//4}x}" for w in words]
        capture = generated_capture(m, values, 17)
        self.assertEqual(len(capture["records"]), 3)
        self.assertEqual(capture["capture_type"], "generated_rtl_diagnostic")
        self.assertTrue(capture["external_runtime_required"])
        self.assertEqual(capture["manifest_sha256"], hashlib.sha256(canonical(m)).hexdigest())
        self.assertEqual([r["value"] for r in capture["records"]], values)
        for bad in (values[:-1], values + ["0"], ["x"*len(v) for v in values], ["f"*len(v) for v in values]):
            with self.assertRaises(FormatError):
                generated_capture(m, bad, 17)

    def test_manifest_rejects_semantic_inventory_bad_ids_shapes_and_owners(self):
        for mutation in (
            lambda m: m.update(manifest_type="rtlckpt"),
            lambda m: m.update(external_runtime_required=False),
            lambda m: m["state"][0].update(state_id="0"*64),
            lambda m: m["state"][0].update(width=True),
            lambda m: m["state"][0].update(width=0),
            lambda m: m["state"][0].update(adapter="opaque"),
            lambda m: m["state"][0].update(module="Absent"),
            lambda m: m["state"].append(copy.deepcopy(m["state"][0])),
            lambda m: m.update(state=list(reversed(m["state"]))),
        ):
            m = fixture()
            mutation(m)
            with self.assertRaises(FormatError):
                validate_generated_manifest(m)

    def test_emitted_coverage_rejects_missing_extra_reshaped_and_wrong_reference(self):
        m = fixture()
        rtl = "module Top(input clock); reg [256:0] counter; reg [8:0] fifo [0:1]; endmodule"
        check_generated_rtl(m, "reference", rtl, "")
        for bad in (rtl.replace("reg [256:0] counter;", ""),
                    rtl.replace("endmodule", "reg hidden; endmodule"),
                    rtl.replace("endmodule", "reg [5:1] unsupported; endmodule"),
                    rtl.replace("[0:1]", "[0:2]")):
            with self.assertRaises(FormatError):
                check_generated_rtl(m, "reference", bad, "")
        with self.assertRaises(FormatError):
            check_generated_rtl(m, "modified", rtl, "")


if __name__ == "__main__":
    unittest.main()
