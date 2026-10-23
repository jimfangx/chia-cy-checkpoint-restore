"""Versioned chunk mapping, canonical wide values, and strict rejection."""
import copy
import unittest

from tools.checkpoint_formats.banked import encode_chunked_banked, validate_binding
from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.fpga_transport import MAGIC, crc32c, decode_frames, encode_transport_semantic
from tools.checkpoint_formats.semantic import encode_semantic, manifest_hash
from tools.checkpoint_formats.tests.test_semantic import example
from tools.checkpoint_formats.tests.test_fpga_transport import rechecksum


def fixture():
    manifest, doc = example()
    for i, (entry, record) in enumerate(zip(manifest['state'], doc['records'])):
        entry['width'] = record['width'] = (65, 128, 129)[i]
        record['values'] = [f"{((1 << (entry['width'] - 1)) | (a << 64) | (0x101 + a)):0{(entry['width'] + 3) // 4}x}"
                            for a in range(entry['depth'])]
    doc['build']['state_manifest_hash'] = manifest_hash(manifest)
    binding = dict(access_version=2, protocol='banked64-chunked-v2', dut_root=manifest['dut_root'],
                   state_manifest_sha256=manifest_hash(manifest), state=[])
    beats = []
    for i, (entry, record) in enumerate(zip(manifest['state'], doc['records'])):
        chunks = (entry['width'] + 63) // 64
        binding['state'].append(dict(state_id=entry['state_id'], bank=i, slot=2*i, width=entry['width'],
                                     depth=entry['depth'], chunks=chunks, transfer_width=64,
                                     transfer_depth=entry['depth'] * chunks))
        for a, value in enumerate(record['values']):
            for chunk in range(chunks):
                beats.append(dict(entry=i, address=a*chunks+chunk, width=64,
                                  data=(int(value, 16) >> (chunk*64)) & (2**64 - 1), error=0, last=0))
    beats[-1]['last'] = 1
    base = MAGIC | 1 << 64 | 42 << 96
    frames = [base | 1 << 80 | len(binding['state']) << 224 | int(manifest_hash(manifest), 16) << 256]
    for ordinal, beat in enumerate(beats):
        entry = binding['state'][beat['entry']]
        frames.append(base | 2 << 80 | ordinal << 160 | beat['entry'] << 224 | beat['address'] << 256 |
                      64 << 288 | entry['bank'] << 304 | entry['slot'] << 312 | beat['data'] << 336)
    raw = b''.join(f.to_bytes(64, 'little') for f in frames)
    trailer = base | 3 << 80 | len(beats) << 160 | (crc32c(raw) ^ 0xffffffff) << 224
    return manifest, doc, binding, beats, raw + trailer.to_bytes(64, 'little')


class ChunkedTransportTests(unittest.TestCase):
    def test_matches_independent_full_logical_semantic_values(self):
        manifest, doc, binding, beats, raw = fixture()
        validate_binding(manifest, binding)
        self.assertEqual(decode_frames(raw, manifest, binding, 42), beats)
        expected = encode_semantic(doc, manifest)
        self.assertEqual(encode_chunked_banked(manifest, 'test-dut', 42, beats), expected)
        self.assertEqual(encode_transport_semantic(raw, manifest, binding, 'test-dut', 42), expected)

    def test_mapping_shape_version_and_overflow_reject(self):
        manifest, _, binding, _, raw = fixture()
        mutations = [lambda b: b.update(access_version=1), lambda b: b.update(access_version=True),
                     lambda b: b.update(protocol='banked64-v1'), lambda b: b['state'][0].update(chunks=1),
                     lambda b: b['state'][0].update(transfer_width=65),
                     lambda b: b['state'][0].update(transfer_depth=2**31),
                     lambda b: b['state'][0].update(transfer_depth=True),
                     lambda b: b['state'][0].update(width=64), lambda b: b['state'][0].pop('chunks'),
                     lambda b: b['state'][1].update(bank=0, slot=0), lambda b: b['state'].reverse()]
        for mutate in mutations:
            bad = copy.deepcopy(binding); mutate(bad)
            with self.subTest(mutation=mutate), self.assertRaises(FormatError):
                decode_frames(raw, manifest, bad, 42)

    def test_reordered_missing_or_padded_chunks_reject(self):
        manifest, _, binding, beats, raw = fixture()
        mutations = [lambda b: b.pop(), lambda b: b.reverse(), lambda b: b[0].update(address=1),
                     lambda b: b[0].update(width=65), lambda b: b[1].update(data=2),
                     lambda b: b[0].update(last=1), lambda b: b[-1].update(last=0),
                     lambda b: b[0].update(error=1), lambda b: b[0].update(data=-1)]
        for mutate in mutations:
            bad = copy.deepcopy(beats); mutate(bad)
            with self.subTest(mutation=mutate), self.assertRaises(FormatError):
                encode_chunked_banked(manifest, 'test-dut', 42, bad)
        # Fixing the CRC cannot hide invalid high padding in the second 65-bit chunk.
        bad = bytearray(raw); bad[2*64+42] |= 2
        with self.assertRaisesRegex(FormatError, 'noncanonical'):
            decode_frames(rechecksum(bad), manifest, binding, 42)
        for end in (0, 1, 63, 64, len(raw)-1, len(raw)-64):
            with self.assertRaises(FormatError):
                encode_transport_semantic(raw[:end], manifest, binding, 'test-dut', 42)
