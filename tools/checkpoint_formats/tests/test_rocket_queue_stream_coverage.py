"""Coverage failures that remain checksummed and payload-consistent."""
import tempfile
import unittest
from pathlib import Path

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.fpga_transport import crc32c
from tools.checkpoint_formats.tests.audit_rocket_native_queues import frames


class RocketQueueStreamCoverageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'capture.bin'
        self.digest = '1234' * 16
        self.capture = dict(target_cycle=123, native=0, memory=[[0] for _ in range(4)],
                            wp=[0]*4, rp=[0]*4, ra=[0]*4, fullflag=[0]*4)
        names = ('ram', 'enq_ptr_value', 'deq_ptr_value', 'maybe_full', 'ram_io_deq_bits_MPORT_addr')
        self.rows = [dict(region=q, hierarchy=f'q{q}.{name}', bank=q, slot=s,
                          width=64 if s == 0 else 1, depth=8 if s == 0 else 1)
                     for q in range(4) for s, name in enumerate(names)]
        base = 0x3154504b434d5346 | 1 << 64 | 123 << 96
        data = [base | 1 << 80 | 21 << 224 | int(self.digest, 16) << 256]
        sequence = 0
        for ordinal, row in enumerate(self.rows + [dict(bank=252, slot=0, width=64, depth=104)]):
            for address in range(row['depth']):
                data.append(base | 2 << 80 | sequence << 160 | ordinal << 224 |
                            address << 256 | row['width'] << 288 | row['bank'] << 304 | row['slot'] << 312)
                sequence += 1
        data.append(base | 3 << 80 | sequence << 160)
        self.raw = bytearray(b''.join(f.to_bytes(64, 'little') for f in data))

    def audit(self, raw):
        raw[-36:-32] = (crc32c(raw[:-64]) ^ 0xffffffff).to_bytes(4, 'little')
        self.path.write_bytes(raw)
        return frames(self.path, self.rows, self.capture, self.digest)

    def test_complete_zero_payload_still_requires_every_owner_address(self):
        self.assertEqual(self.audit(self.raw)['words'], 152)

    def duplicate(self, source, destination):
        # Keep sequence labels valid. Identical zero payloads also satisfy the
        # reported selector's value oracle. Only the ownership coverage fails.
        self.raw[destination*64+28:(destination+1)*64] = self.raw[source*64+28:(source+1)*64]
        with self.assertRaisesRegex(FormatError, 'missing/duplicate/out-of-order owner word'):
            self.audit(self.raw)

    def test_duplicate_ram_address_with_valid_payload_and_crc(self):
        self.duplicate(1, 2)

    def test_duplicate_lane_omits_another_original_owner(self):
        self.duplicate(1, 13)

    def test_duplicate_native_word_omits_staged_bits(self):
        self.duplicate(49, 50)

    def test_reordered_equal_payloads_with_valid_sequence_and_crc(self):
        a, b = 64+28, 128+28
        self.raw[a:a+36], self.raw[b:b+36] = self.raw[b:b+36], self.raw[a:a+36]
        with self.assertRaisesRegex(FormatError, 'missing/duplicate/out-of-order owner word'):
            self.audit(self.raw)

    def test_nonzero_header_sequence_with_valid_crc(self):
        self.raw[20] = 1
        with self.assertRaisesRegex(FormatError, 'manifest header mismatch'):
            self.audit(self.raw)

    def test_truncation_cannot_replace_missing_words_with_a_valid_trailer(self):
        with self.assertRaisesRegex(FormatError, 'truncated four-queue stream'):
            self.audit(self.raw[:128] + self.raw[192:])


if __name__ == '__main__':
    unittest.main()
