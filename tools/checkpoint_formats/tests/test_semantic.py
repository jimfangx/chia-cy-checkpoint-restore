import copy
import hashlib
import unittest

from tools.checkpoint_formats.codec import FormatError, canonical, encode
from tools.checkpoint_formats.semantic import (
    decode_semantic, encode_semantic, manifest_hash, state_id, validate_manifest,
)


def example():
    state = []
    for name, kind, depth in (("a.saved", "register", 1), ("b.saved", "register", 1), ("sram", "memory", 8)):
        hierarchy = "Harness.dut." + name
        state.append(dict(state_id=state_id(hierarchy, kind), hierarchy=hierarchy, kind=kind,
                          width=9, depth=depth, signed=False, clock_domain="Harness.dut.clock",
                          reset="none", bit_order="lsb0", address_order="ascending_zero_based"))
    state.sort(key=lambda e: e["state_id"])
    manifest = dict(manifest_version=1, manifest_type="rtlckpt", identity_scheme="pre-fame-state-v1",
                    circuit="Harness", dut_root="Harness.dut", clock_domain="Harness.dut.clock",
                    reference_sha256="a" * 64, state=state)
    doc = dict(format_version=1, checkpoint_type="rtlckpt", target_cycle=42,
               target_clock_phase="before_rising_edge",
               build=dict(target_configuration="test-dut", rtl_build_hash="a" * 64,
                          state_manifest_hash=manifest_hash(manifest)),
               records=[dict(state_id=e["state_id"], width=e["width"], depth=e["depth"],
                             values=["101"] * e["depth"]) for e in state])
    return manifest, doc


class SemanticTests(unittest.TestCase):
    def test_complete_manifest_bound_roundtrip(self):
        manifest, doc = example()
        self.assertEqual(manifest_hash(manifest), hashlib.sha256(canonical(manifest)).hexdigest())
        data = encode_semantic(doc, manifest)
        self.assertEqual(decode_semantic(data, doc["build"], manifest), doc)
        self.assertNotEqual(state_id("Harness.dut.a.saved", "register"),
                            state_id("Harness.dut.b.saved", "register"))

    def test_valid_checksums_and_hashes_cannot_hide_wrong_membership_or_shape(self):
        mutations = [lambda d: d["records"].pop(),
                     lambda d: d["records"][0].update(state_id="0" * 64),
                     lambda d: d["records"][0].update(width=10),
                     lambda d: d["records"][0].update(depth=2, values=["101", "101"])]
        for mutate in mutations:
            manifest, doc = example()
            mutate(doc)
            doc["records"].sort(key=lambda e: e["state_id"])
            # Low-level format is valid; semantic completeness must still reject it.
            data = encode("rtlckpt", doc)
            with self.assertRaisesRegex(FormatError, "semantic state"):
                encode_semantic(doc, manifest)
            with self.assertRaisesRegex(FormatError, "semantic state"):
                decode_semantic(data, doc["build"], manifest)

    def test_manifest_version_identity_scope_shape_and_order_rejections(self):
        mutations = [lambda m: m.update(manifest_version=True),
                     lambda m: m.update(manifest_type="fsckpt"),
                     lambda m: m.update(identity_scheme="verilog-names"),
                     lambda m: m.update(state=[]),
                     lambda m: m["state"].reverse(),
                     lambda m: m["state"].append(copy.deepcopy(m["state"][0])),
                     lambda m: m["state"][0].update(hierarchy="Harness.bridge.state"),
                     lambda m: m["state"][0].update(state_id="b" * 64),
                     lambda m: m["state"][0].update(width=0),
                     lambda m: m["state"][0].update(signed=1),
                     lambda m: m["state"][0].update(clock_domain="Harness.dut.otherClock"),
                     lambda m: m["state"][0].update(reset="asynchronous"),
                     lambda m: m["state"][0].update(bit_order="msb0")]
        for mutate in mutations:
            manifest, _ = example()
            mutate(manifest)
            with self.assertRaises(FormatError):
                validate_manifest(manifest)

    def test_substituted_manifest_is_incompatible(self):
        manifest, doc = example()
        data = encode_semantic(doc, manifest)
        manifest["reference_sha256"] = "c" * 64
        with self.assertRaisesRegex(FormatError, "manifest hash mismatch"):
            decode_semantic(data, doc["build"], manifest)


if __name__ == "__main__":
    unittest.main()
