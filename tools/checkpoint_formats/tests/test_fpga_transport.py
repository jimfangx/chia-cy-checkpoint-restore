import copy
import unittest

from tools.checkpoint_formats.banked import encode_banked
from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.fpga_transport import (
    MAGIC, crc32c, decode_frames, encode_transport_semantic,
)
from tools.checkpoint_formats.semantic import manifest_hash
from tools.checkpoint_formats.tests.test_semantic import example


def binding_for(manifest):
    return dict(access_version=1, protocol="banked64-v1", dut_root=manifest["dut_root"],
                state_manifest_sha256=manifest_hash(manifest),
                state=[dict(state_id=e["state_id"], bank=i+1, slot=2*i,
                            width=e["width"], depth=e["depth"])
                       for i, e in enumerate(manifest["state"])])


def frames_for(manifest, binding, cycle=42):
    base = MAGIC | (1 << 64) | (cycle << 96)
    frames = [base | (1 << 80) | (len(binding["state"]) << 224) |
              (int(manifest_hash(manifest), 16) << 256)]
    ordinal = 0
    for index, entry in enumerate(binding["state"]):
        for address in range(entry["depth"]):
            frames.append(base | (2 << 80) | (ordinal << 160) | (index << 224) |
                          (address << 256) | (entry["width"] << 288) | (entry["bank"] << 304) |
                          (entry["slot"] << 312) | (0x101 << 336))
            ordinal += 1
    raw = b"".join(f.to_bytes(64, "little") for f in frames)
    trailer = base | (3 << 80) | (ordinal << 160) | ((crc32c(raw) ^ 0xffffffff) << 224)
    return raw + trailer.to_bytes(64, "little")


def rechecksum(raw):
    data = bytearray(raw)
    data[-36:-32] = (crc32c(data[:-64]) ^ 0xffffffff).to_bytes(4, "little")
    return bytes(data)


def negative_checks(raw, manifest, binding, cycle):
    """Also used on actual component-VCS output, not only constructed frames."""
    count = 0

    def reject(data, m=manifest, b=binding, c=cycle):
        nonlocal count
        try:
            decode_frames(data, m, b, c)
        except FormatError:
            count += 1
        else:
            raise AssertionError("corrupt transport accepted")

    for end in (0, 1, 63, 64, 65, len(raw)-64, len(raw)-1):
        reject(raw[:end])
    reject(raw + raw[-64:])
    # Every individual frame is checksum protected, including the trailer.
    for offset in range(0, len(raw), 64):
        bad = bytearray(raw); bad[offset] ^= 1; reject(bytes(bad))
    # Correcting the checksum must not hide semantic framing violations.
    for offset in (0, 8, 10, 12, 20, 28, 32, 64+10, 64+12, 64+20,
                   64+28, 64+32, 64+36, 64+38, 64+39, 64+41, 64+50):
        bad = bytearray(raw); bad[offset] ^= 1; reject(rechecksum(bytes(bad)))
    # All fixture words have a narrow first entry; padding corruption rejects.
    bad = bytearray(raw)
    bad[64+49] |= 0x80
    reject(rechecksum(bytes(bad)))
    bad = bytearray(raw); bad[-1] |= 1; reject(bytes(bad))
    reject(raw, c=cycle+1)
    other = copy.deepcopy(manifest); other["reference_sha256"] = "f"*64
    reject(raw, m=other, b=binding_for(other))
    other_binding = copy.deepcopy(binding); other_binding["state"].pop()
    reject(raw, b=other_binding)
    other_binding = copy.deepcopy(binding); other_binding["state"][0]["slot"] += 1
    reject(raw, b=other_binding)
    return count


class FPGATransportTests(unittest.TestCase):
    def test_crc32c_known_check_value(self):
        self.assertEqual(crc32c(b"123456789") ^ 0xffffffff, 0xe3069283)

    def test_complete_transport_has_same_canonical_semantics(self):
        manifest, _ = example()
        binding = binding_for(manifest)
        raw = frames_for(manifest, binding)
        beats = decode_frames(raw, manifest, binding, 42)
        self.assertEqual(encode_transport_semantic(raw, manifest, binding, "test-dut", 42),
                         encode_banked(manifest, "test-dut", 42, beats))
        self.assertEqual(len(beats), 10)
        self.assertEqual(sum(b["last"] for b in beats), 1)

    def test_corruption_and_rechecksummed_semantic_failures(self):
        manifest, _ = example()
        binding = binding_for(manifest)
        self.assertGreaterEqual(negative_checks(frames_for(manifest, binding), manifest, binding, 42), 40)


if __name__ == "__main__":
    unittest.main()
