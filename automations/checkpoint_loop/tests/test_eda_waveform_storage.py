"""Storage recovery must audit complete waveforms without dropping evidence."""
import errno
import hashlib
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eda_waveform_storage as storage


class WaveformStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name)/'source.vcd'
        self.destination = Path(self.tmp.name)/'destination.vcd'
        # Different header, two equal pages, one differing page, EOF tail.
        self.x = b'x'*4096 + b'a'*8192 + b'b'*4096 + b'tail'
        self.y = b'y'*4096 + b'a'*8192 + b'c'*4096 + b'tail'
        self.source.write_bytes(self.x)
        self.destination.write_bytes(self.y)

    @staticmethod
    def digest(data):
        return hashlib.sha256(data).hexdigest()

    def kernel(self, fd, op, request, mutate):
        self.assertEqual(op, storage.FIDEDUPERANGE)
        self.assertTrue(mutate)
        row = list(struct.unpack('=QQHHIqQQiI', request))
        self.assertEqual(row[0], row[6])
        # Model a kernel that completes only one aligned page per ioctl.
        count = min(4096, row[1])
        equal = os.pread(fd, count, row[0]) == os.pread(row[5], count, row[6])
        row[7], row[8] = (count, 0) if equal else (0, 1)
        request[:] = struct.pack('=QQHHIqQQiI', *row)

    def share(self, **kwargs):
        return storage.share(self.source, self.destination, self.digest(self.x), self.digest(self.y), **kwargs)

    def test_partial_ranges_differing_header_and_tail_keep_every_byte_and_inode(self):
        paths = self.source, self.destination
        before = [storage.identity(p.stat()) for p in paths]
        with patch.object(storage.fcntl, 'ioctl', side_effect=self.kernel) as ioctl:
            row = self.share()
        self.assertEqual(ioctl.call_count, 3)
        self.assertEqual(row['bytes_shared'], 8192)
        self.assertEqual(row['bytes_different'], 4096)
        self.assertEqual(row['complete_before_after_digests'], [self.digest(self.x), self.digest(self.y)]*2)
        self.assertEqual(before, [storage.identity(p.stat()) for p in paths])
        self.assertNotEqual(before[0][1], before[1][1])
        self.assertEqual(self.source.read_bytes(), self.x)
        self.assertEqual(self.destination.read_bytes(), self.y)

    def test_wrong_expected_digest_and_middle_corruption_cannot_publish_success(self):
        for data in (self.y, self.y[:9000]+b'!'+self.y[9001:]):
            with self.subTest(data=data[9000:9001]):
                self.destination.write_bytes(data)
                with patch.object(storage.fcntl, 'ioctl', side_effect=self.kernel):
                    with self.assertRaisesRegex(ValueError, 'complete waveform digest mismatch'):
                        storage.share(self.source, self.destination, self.digest(self.x), '0'*64)
                self.assertEqual(self.destination.read_bytes(), data)

    def test_malformed_digest_rejects_before_kernel_or_open(self):
        with patch.object(storage.os, 'open') as opened:
            with self.assertRaises(ValueError):
                storage.share(self.source, self.destination, '', self.digest(self.y))
            opened.assert_not_called()

    def test_symlink_hardlink_size_and_owner_mismatch_reject(self):
        link = self.destination.with_name('symlink')
        link.symlink_to(self.destination)
        with self.assertRaises(OSError):
            storage.share(self.source, link, self.digest(self.x), self.digest(self.y))
        with self.assertRaisesRegex(ValueError, 'independent inodes'):
            storage.share(self.source, self.source, self.digest(self.x), self.digest(self.x))
        self.destination.write_bytes(b'short')
        with self.assertRaisesRegex(ValueError, 'equal sizes'):
            self.share()
        self.destination.write_bytes(self.y)
        with patch.object(storage.os, 'getuid', return_value=-1):
            with self.assertRaisesRegex(ValueError, 'owned'):
                self.share()

    def test_concurrent_byte_and_metadata_changes_reject(self):
        def changed_bytes(fd, op, request, mutate):
            self.kernel(fd, op, request, mutate)
            with self.destination.open('r+b') as stream:
                stream.seek(4096)
                stream.write(b'!')
        with patch.object(storage.fcntl, 'ioctl', side_effect=changed_bytes):
            with self.assertRaisesRegex(RuntimeError, 'bytes changed'):
                self.share()
        self.destination.write_bytes(self.y)

        def changed_metadata(*args):
            self.kernel(*args)
            os.utime(self.destination, ns=(1700000000000000000, 1700000000000000000))
        with patch.object(storage.fcntl, 'ioctl', side_effect=changed_metadata):
            with self.assertRaisesRegex(RuntimeError, 'metadata changed'):
                self.share()

    def test_path_replacement_rejects_even_when_open_inode_is_unchanged(self):
        def replace(row):
            if row['audited_bytes'] == row['total_bytes']:
                renamed = self.destination.with_name('replaced')
                self.destination.rename(renamed)
                self.destination.write_bytes(self.y)
        with patch.object(storage.fcntl, 'ioctl', side_effect=self.kernel):
            with self.assertRaisesRegex(RuntimeError, 'path changed'):
                self.share(progress=replace)

    def test_short_files_and_empty_files_are_completely_hashed_without_ioctl(self):
        for size in (0, 1, 4095, 4096, 4097):
            with self.subTest(size=size):
                self.x, self.y = b'x'*size, b'y'*size
                self.source.write_bytes(self.x)
                self.destination.write_bytes(self.y)
                with patch.object(storage.fcntl, 'ioctl') as ioctl:
                    row = self.share()
                    ioctl.assert_not_called()
                self.assertEqual(row['complete_before_after_digests'], [self.digest(self.x),self.digest(self.y)]*2)

    def test_kernel_errors_and_impossible_progress_never_fall_back_to_writes(self):
        for count, status in ((0, -errno.ENOSPC), (0, -errno.EOPNOTSUPP), (0, 0),
                              (1, 0), (4096, 1), (999999, 0), (0, 2)):
            with self.subTest(count=count, status=status):
                def kernel(fd, op, request, mutate):
                    row = list(struct.unpack('=QQHHIqQQiI', request))
                    row[7:9] = count, status
                    request[:] = struct.pack('=QQHHIqQQiI', *row)
                with patch.object(storage.fcntl, 'ioctl', side_effect=kernel):
                    with self.assertRaises((OSError, RuntimeError)):
                        self.share()
                self.assertEqual(self.destination.read_bytes(), self.y)

    def test_capacity_checks_bytes_and_inodes_independently(self):
        observed = dict(available_bytes=100, available_inodes=10)
        with patch.object(storage, 'capacity', return_value=observed):
            self.assertEqual(storage.require_capacity(self.source, 100, 10), observed)
            for count, inodes in ((101, 10), (100, 11)):
                with self.assertRaisesRegex(RuntimeError, 'recover capacity before launching VCS'):
                    storage.require_capacity(self.source, count, inodes)


if __name__ == '__main__':
    unittest.main()
