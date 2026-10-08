import copy
import unittest

from tools.checkpoint_formats.banked import encode_banked, validate_binding
from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.semantic import encode_semantic, manifest_hash
from tools.checkpoint_formats.tests.test_semantic import example


def beats_for(manifest):
    words = [dict(entry=i, address=a, width=e["width"], data=0x101, error=0, last=0)
             for i, e in enumerate(manifest["state"]) for a in range(e["depth"])]
    words[-1]["last"] = 1
    return words


class BankedTests(unittest.TestCase):
    def test_binding_is_complete_unambiguous_and_manifest_compatible(self):
        manifest, _ = example()
        binding = dict(access_version=1, protocol="banked64-v1", dut_root=manifest["dut_root"],
                       state_manifest_sha256=manifest_hash(manifest),
                       state=[dict(state_id=e["state_id"], bank=0, slot=i, width=e["width"], depth=e["depth"])
                              for i, e in enumerate(manifest["state"])])
        validate_binding(manifest, binding)
        mutations = [lambda b: b.update(state_manifest_sha256="b" * 64), lambda b: b["state"].pop(),
                     lambda b: b["state"].reverse(), lambda b: b["state"][0].update(width=8),
                     lambda b: b["state"][1].update(slot=0), lambda b: b["state"][0].update(bank=256)]
        for mutate in mutations:
            bad = copy.deepcopy(binding)
            mutate(bad)
            with self.assertRaises(FormatError):
                validate_binding(manifest, bad)

    def test_public_stream_encodes_identically_to_complete_semantic_oracle(self):
        manifest, doc = example()
        self.assertEqual(encode_banked(manifest, "test-dut", 42, beats_for(manifest)),
                         encode_semantic(doc, manifest))

    def test_incomplete_reordered_errored_or_wrong_metadata_never_serializes(self):
        manifest, _ = example()
        mutations = [lambda b: b.pop(), lambda b: b.append(copy.deepcopy(b[-1])),
                     lambda b: b.reverse(), lambda b: b[0].update(entry=1),
                     lambda b: next(x for x in b if x["address"] == 1).update(address=0),
                     lambda b: b[0].update(width=8), lambda b: b[0].update(error=1),
                     lambda b: b[0].update(last=1), lambda b: b[-1].update(last=0),
                     lambda b: b[0].update(data=512), lambda b: b[0].update(data=-1),
                     lambda b: b[0].update(data="xxx"), lambda b: b[0].update(entry=True),
                     lambda b: b[0].update(unknown=0)]
        for mutate in mutations:
            beats = beats_for(manifest)
            mutate(beats)
            with self.subTest(mutation=mutate), self.assertRaises(FormatError):
                encode_banked(manifest, "test-dut", 42, beats)

    def test_wide_state_is_rejected_and_64_bit_words_keep_high_bits(self):
        manifest, _ = example()
        for entry in manifest["state"]:
            entry["width"] = 64
        beats = beats_for(manifest)
        for beat in beats:
            beat["data"] = (1 << 63) | 0x101
        from tools.checkpoint_formats.semantic import decode_semantic, manifest_hash
        build = dict(target_configuration="test-dut", rtl_build_hash=manifest["reference_sha256"],
                     state_manifest_hash=manifest_hash(manifest))
        decoded = decode_semantic(encode_banked(manifest, "test-dut", 42, beats), build, manifest)
        self.assertTrue(all(v == "8000000000000101" for r in decoded["records"] for v in r["values"]))
        manifest["state"][0]["width"] = 65
        with self.assertRaisesRegex(FormatError, "wide state"):
            encode_banked(manifest, "test-dut", 42, beats)


if __name__ == "__main__":
    unittest.main()
