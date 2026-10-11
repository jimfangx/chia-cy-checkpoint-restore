import copy
from pathlib import Path
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.formal_state_map import flat_inventory, sha


class SRAMInventoryTests(unittest.TestCase):
    def setUp(self):
        self.models = (Path(__file__).with_name("fixtures") / "formal/sram/macro.v").read_text()
        self.adapter = dict(adapter_version=2, models_sha256=sha(self.models.encode()), cells={"CKSRAM": dict(storage=[
            dict(rtl_path=name, formal_path=name + "_reg", xor=0, width=width, depth=depth, kind=kind)
            for name, width, depth, kind in (("contents", 4, 4, "memory"), ("port_address", 2, 1, "register"),
                ("port_write", 1, 1, "register"), ("port_data", 4, 1, "register"), ("pipeline", 4, 1, "register"))])})
        self.netlist = "module DUT(input clock); CKSRAM memory(.CP(clock),.WE(1'b0),.A(2'b0),.D(4'b0),.Q()); endmodule"

    def inventory(self, adapter=None, models=None):
        return flat_inventory(self.netlist, models or self.models, adapter or self.adapter, "DUT")

    def test_all_words_pipeline_and_pending_port_state_have_distinct_bits(self):
        gates = self.inventory()
        self.assertEqual(len(gates), 27)
        self.assertEqual(len({(v["storage_path"], v["bit"]) for v in gates.values()}), 27)
        words = {v["storage_path"]: v["width"] for v in gates.values()}
        self.assertEqual(words, {**{f"contents[{address}]": 4 for address in range(4)},
                                "port_address": 2, "port_write": 1, "port_data": 4, "pipeline": 4})

    def test_omitted_reshaped_duplicate_and_invalid_storage_fail(self):
        for change in (lambda s: s.pop(), lambda s: s[0].update(depth=3),
                       lambda s: s[0].update(width=3), lambda s: s.append(copy.deepcopy(s[0])),
                       lambda s: s[0].update(kind="register"), lambda s: s[0].update(width=True),
                       lambda s: s[0].update(formal_path="contents[0]")):
            adapter = copy.deepcopy(self.adapter)
            change(adapter["cells"]["CKSRAM"]["storage"])
            with self.subTest(adapter=adapter), self.assertRaises(FormatError):
                self.inventory(adapter=adapter)

    def test_hidden_or_initialized_storage_rejected_even_with_updated_model_hash(self):
        for declaration in ("reg hidden;", "logic hidden;", "int hidden;", "bit hidden;",
                            "integer hidden;", "initial pipeline = 0;", "parameter WIDTH = 4;"):
            models = self.models.replace("endmodule", declaration + "\nendmodule")
            adapter = dict(self.adapter, models_sha256=sha(models.encode()))
            with self.subTest(declaration=declaration), self.assertRaises(FormatError):
                self.inventory(adapter, models)

    def test_unknown_macro_or_stale_model_hash_rejected(self):
        self.netlist = self.netlist.replace("CKSRAM memory", "OTHER memory")
        with self.assertRaisesRegex(FormatError, "SRAM macro"):
            self.inventory()
        self.netlist = self.netlist.replace("OTHER memory", "CKSRAM memory")
        with self.assertRaisesRegex(FormatError, "unaudited"):
            self.inventory(models=self.models + "\n")

    def test_state_declared_in_model_ports_is_not_silently_omitted(self):
        models = self.models.replace("output [3:0] Q", "output reg [3:0] Q")
        with self.assertRaisesRegex(FormatError, "model ports"):
            self.inventory(dict(self.adapter, models_sha256=sha(models.encode())), models)


if __name__ == "__main__":
    unittest.main()
