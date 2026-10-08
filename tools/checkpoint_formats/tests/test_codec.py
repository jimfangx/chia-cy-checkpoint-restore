import copy
import hashlib
import json
import random
import struct
import unittest

from tools.checkpoint_formats.codec import BUILD_KEYS, MAGIC, FormatError, decode, encode


def example(kind):
    build = {key: "test-dut" if key == "target_configuration" else "a" * 64 for key in BUILD_KEYS[kind]}
    records = {
        "fsckpt": [{"owner": "driver:memory", "width": 9, "value": "1ff"}],
        "rtlckpt": [{"state_id": "b" * 64, "width": 9, "depth": 2, "values": ["000", "1ff"]}],
        "trace": [{"cycle": 42, "inputs": {"in": {"width": 9, "value": "101"}},
                   "outputs": {"out": {"width": 1, "value": "0"}}}],
    }
    return dict(format_version=1, checkpoint_type=kind, target_cycle=42,
                target_clock_phase="before_rising_edge", build=build, records=records[kind])


class CodecTests(unittest.TestCase):
    def test_all_formats_roundtrip_and_every_single_bit_corruption(self):
        for kind in MAGIC:
            doc = example(kind)
            data = encode(kind, doc)
            self.assertEqual(decode(data, kind, doc["build"]), doc)
            self.assertEqual(encode(kind, decode(data, kind, doc["build"])), data)
            for byte in range(len(data)):
                for bit in range(8):
                    damaged = bytearray(data)
                    damaged[byte] ^= 1 << bit
                    with self.assertRaises(FormatError):
                        decode(bytes(damaged), kind, doc["build"])
            for end in range(len(data)):
                with self.assertRaises(FormatError):
                    decode(data[:end], kind, doc["build"])
            with self.assertRaises(FormatError):
                decode(data + b"extra", kind, doc["build"])

    def test_wide_random_bit_vectors_and_memories(self):
        rng = random.Random(923)
        for width in (1, 7, 8, 9, 31, 64, 65, 129, 1025):
            doc = example("rtlckpt")
            values = [format(rng.getrandbits(width), f"0{(width + 3) // 4}x") for _ in range(17)]
            doc["records"][0].update(width=width, depth=len(values), values=values)
            self.assertEqual(decode(encode("rtlckpt", doc), "rtlckpt", doc["build"]), doc)

    def test_independent_builds_and_type_confusion(self):
        for kind in MAGIC:
            doc = example(kind)
            data = encode(kind, doc)
            for key in BUILD_KEYS[kind]:
                build = dict(doc["build"], **{key: "c" * 64})
                with self.assertRaisesRegex(FormatError, "incompatible"):
                    decode(data, kind, build)
            for other in MAGIC.keys() - {kind}:
                with self.assertRaises(FormatError):
                    decode(data, other, example(other)["build"])
        self.assertNotIn("golden_gate_build_hash", example("rtlckpt")["build"])
        self.assertNotIn("golden_gate_build_hash", example("trace")["build"])

    def test_unsupported_and_malformed(self):
        mutations = [
            lambda d: d.update(format_version=2),
            lambda d: d.update(format_version=True),
            lambda d: d.update(target_cycle=-1),
            lambda d: d.update(target_clock_phase="falling_edge"),
            lambda d: d.update(unknown=0),
            lambda d: d["records"].append(copy.deepcopy(d["records"][0])),
            lambda d: d["records"][0].update(width=0),
            lambda d: d["records"][0].update(values=["xxx", "000"]),
            lambda d: d["records"][0].update(values=["200", "000"]),
            lambda d: d["records"][0].update(values=["00", "000"]),
            lambda d: d["records"][0].update(depth=3),
            lambda d: d["records"][0].update(state_id="foo"),
        ]
        for mutate in mutations:
            doc = example("rtlckpt")
            mutate(doc)
            with self.assertRaises(FormatError):
                encode("rtlckpt", doc)
            # A valid checksum must not bypass schema validation on read.
            payload = json.dumps(doc).encode()
            header = MAGIC["rtlckpt"] + struct.pack(">Q", len(payload))
            with self.assertRaises(FormatError):
                decode(header + payload + hashlib.sha256(header + payload).digest(), "rtlckpt", example("rtlckpt")["build"])

    def test_trace_cycles_and_boundary_values(self):
        doc = example("trace")
        doc["records"].append(copy.deepcopy(doc["records"][0]))
        with self.assertRaises(FormatError):
            encode("trace", doc)
        doc["records"][1]["cycle"] = 43
        self.assertEqual(decode(encode("trace", doc), "trace", doc["build"]), doc)
        doc["records"][1]["inputs"]["in"]["value"] = "x00"
        with self.assertRaises(FormatError):
            encode("trace", doc)

    def test_duplicate_keys_and_noncanonical_json(self):
        for payload in (b'{"format_version":1,"format_version":1}', json.dumps(example("rtlckpt")).encode()):
            header = MAGIC["rtlckpt"] + struct.pack(">Q", len(payload))
            with self.assertRaises(FormatError):
                decode(header + payload + hashlib.sha256(header + payload).digest(), "rtlckpt", example("rtlckpt")["build"])


if __name__ == "__main__":
    unittest.main()
