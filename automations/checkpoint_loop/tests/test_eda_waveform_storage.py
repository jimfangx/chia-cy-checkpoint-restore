"""Storage recovery must audit complete waveforms without dropping evidence."""
import errno
import hashlib
import json
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

    def test_special_files_reject_without_waiting_for_a_fifo_peer(self):
        fifo = self.destination.with_name('fifo')
        os.mkfifo(fifo)
        for source,destination in ((fifo,self.destination),(self.source,fifo)):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError,'regular files'):
                storage.share(source,destination,self.digest(self.x),self.digest(self.y))

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

    def bootstrap(self, rows, *, required_bytes=100, required_inodes=10):
        root = Path(self.tmp.name)
        (root/'.checkpoint-eda-owner').write_text('checkpoint_loop\n')
        self.events = []
        return storage.recover_existing(rows, root, required_bytes, required_inodes, self.events.append)

    def bootstrap_row(self):
        folder = Path(self.tmp.name)/storage.RUNS
        folder.mkdir(parents=True, exist_ok=True)
        s, d = folder/'source.fir', folder/'destination.fir'
        s.write_bytes(self.x);d.write_bytes(self.y)
        return dict(source=str(s), destination=str(d), size=len(self.x),
                    source_sha256=self.digest(self.x), destination_sha256=self.digest(self.y))

    def test_bootstrap_needs_no_remote_receipt_allocation_and_preserves_all_bytes(self):
        row = self.bootstrap_row()
        low = dict(available_bytes=0, available_inodes=0)
        enough = dict(available_bytes=100, available_inodes=10)
        with patch.object(storage, 'capacity', side_effect=[low,low,enough]), \
                patch.object(storage.fcntl, 'ioctl', side_effect=self.kernel):
            report = self.bootstrap([row])
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(report['audited_pairs'], 1)
        self.assertFalse(report['simulation_acceptance'])
        self.assertEqual(report['removed_files'], [])
        self.assertEqual([e['event'] for e in self.events], ['begin','audited','summary'])
        self.assertEqual(Path(row['destination']).read_bytes(), self.y)
        json.dumps(self.events)  # stdout evidence is independently serializable.

    def test_bootstrap_missing_and_partial_files_never_count_as_audited(self):
        row = self.bootstrap_row()
        for mode in ('absent','truncated'):
            with self.subTest(mode=mode):
                d = Path(row['destination'])
                if mode == 'absent':d.unlink()
                else:d.write_bytes(b'partial rsync')
                with patch.object(storage, 'capacity', return_value=dict(available_bytes=0,available_inodes=0)), \
                        patch.object(storage, 'share') as shared:
                    with self.assertRaisesRegex(RuntimeError, 'capacity insufficient'):
                        self.bootstrap([row])
                shared.assert_not_called()
                summary = self.events[-1]
                self.assertEqual(summary['status'], 'fail')
                self.assertEqual(summary['audited_pairs'], 0)
                self.assertEqual(summary['unavailable_pairs'], 1)

    def test_bootstrap_checks_whole_plan_even_when_capacity_is_already_sufficient(self):
        row = self.bootstrap_row()
        for key, value in (('destination','/tmp/outside'),('size',-1),('size',True),
                           ('source_sha256','BAD')):
            with self.subTest(key=key,value=value), patch.object(storage, 'share') as shared:
                with self.assertRaises(ValueError):self.bootstrap([row,{**row,key:value}],required_bytes=0,required_inodes=0)
                shared.assert_not_called()

    def test_bootstrap_corruption_fails_with_explicit_nonacceptance_receipt(self):
        row = self.bootstrap_row();row['destination_sha256']='0'*64
        with patch.object(storage, 'capacity', return_value=dict(available_bytes=0,available_inodes=0)), \
                patch.object(storage.fcntl, 'ioctl', side_effect=self.kernel):
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):self.bootstrap([row])
        self.assertEqual(self.events[-1]['status'], 'fail')
        self.assertEqual(self.events[-1]['audited_pairs'], 0)


if __name__ == '__main__':
    unittest.main()
