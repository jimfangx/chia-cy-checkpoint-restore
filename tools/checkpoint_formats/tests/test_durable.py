"""Real filesystem interruption and publication failure checks for Level 1."""
import errno
import os
from pathlib import Path
import select
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from tools.checkpoint_formats import aggregate, aggregate_packed as packed
from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.durable import PublicationError, atomic_output
from tools.checkpoint_formats.tests import test_aggregate, test_aggregate_packed


class DurableTest(unittest.TestCase):
    def test_full_container_validation_precedes_any_filesystem_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            for api, fixture in ((aggregate, test_aggregate.AggregateTest()),
                                 (packed, test_aggregate_packed.PackedAggregateTest())):
                parts = fixture.fixture(out)
                build, manifest, generated, layout = parts[:4]
                good = parts[-1]
                target = out/'capture.fsckpt'
                for existing in (False, True):
                    target.unlink(missing_ok=True)
                    if existing:
                        target.write_bytes(b'previous checkpoint')
                    with patch('tools.checkpoint_formats.durable.os.open', side_effect=AssertionError('opened before validation')):
                        with self.assertRaises(FormatError):
                            api.publish_aggregate(good[:-1], build, manifest, generated, layout, target)
                        with self.assertRaises(FormatError):
                            api.prepare_aggregate_restore(good[:-1], build, manifest, generated, layout, target)
                    self.assertEqual(target.read_bytes() if target.exists() else None,
                                     b'previous checkpoint' if existing else None)
                doc = api.publish_aggregate(good, build, manifest, generated, layout, target)
                self.assertEqual(api.decode_aggregate(target.read_bytes(), build, manifest, generated, layout), doc)
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
                api.prepare_aggregate_restore(target.read_bytes(), build, manifest, generated, layout, out/'load')
                self.assertTrue((out/'load').read_bytes().startswith(b'FSAGG1 '))
                self.assertFalse(list(out.glob('.*.pending-*')))

    def test_io_failures_preserve_destination_and_report_postrename_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            target = out/'capture.fsckpt'
            real_sync, real_replace = os.fsync, os.replace
            for existing in (False, True):
                for failure in ('directory-preflight', 'write', 'file-sync', 'rename', 'directory-commit'):
                    with self.subTest(existing=existing, failure=failure):
                        target.unlink(missing_ok=True)
                        if existing:
                            target.write_bytes(b'old')
                        directory_syncs = 0
                        def sync(fd):
                            nonlocal directory_syncs
                            directory_fd = stat.S_ISDIR(os.fstat(fd).st_mode)
                            if directory_fd:
                                directory_syncs += 1
                            if (failure == 'directory-preflight' and directory_syncs == 1
                                    or failure == 'file-sync' and not directory_fd
                                    or failure == 'directory-commit' and directory_fd and directory_syncs == 2):
                                raise OSError(errno.EIO, 'injected fsync failure')
                            return real_sync(fd)
                        def replace(*args, **kwargs):
                            if failure == 'rename':
                                raise OSError(errno.EXDEV, 'injected rename failure')
                            return real_replace(*args, **kwargs)
                        with patch('tools.checkpoint_formats.durable.os.fsync', side_effect=sync), \
                                patch('tools.checkpoint_formats.durable.os.replace', side_effect=replace):
                            with self.assertRaises(PublicationError) as caught:
                                with atomic_output(target, binary=True) as stream:
                                    stream.write(b'new complete checkpoint')
                                    if failure == 'write':
                                        raise OSError(errno.ENOSPC, 'injected short/incomplete write')
                        published = failure == 'directory-commit'
                        self.assertEqual(caught.exception.published, published)
                        self.assertEqual(target.read_bytes() if target.exists() else None,
                                         b'new complete checkpoint' if published else b'old' if existing else None)
                        self.assertFalse(list(out.glob('.*.pending-*')))

    def test_buffered_flush_failure_retains_original_status_and_cleans_temporary(self):
        class FailedFlush:
            def __init__(self, fd): self.fd, self.closed = fd, False
            def write(self, data): os.write(self.fd, data[:3])
            def flush(self): raise OSError(errno.ENOSPC, 'buffer flush full')
            def close(self):
                os.close(self.fd); self.closed = True
                raise OSError(errno.EIO, 'second close flush failure')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'capture.fsckpt'; target.write_bytes(b'old')
            with patch('tools.checkpoint_formats.durable.os.fdopen', side_effect=lambda fd, *a, **k: FailedFlush(fd)):
                with self.assertRaises(PublicationError) as caught:
                    with atomic_output(target, binary=True) as stream:
                        stream.write(b'incomplete')
            self.assertEqual(caught.exception.errno, errno.ENOSPC)
            self.assertFalse(caught.exception.published)
            self.assertEqual(target.read_bytes(), b'old')
            self.assertFalse(list(Path(directory).glob('.*.pending-*')))

    def test_symlinks_and_special_destinations_reject_without_following(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            original = out/'original'; original.write_bytes(b'keep')
            link = out/'link'; link.symlink_to(original)
            folder = out/'folder'; folder.mkdir()
            fifo = out/'fifo'; os.mkfifo(fifo)
            for target in (link, folder, fifo):
                with self.assertRaises(PublicationError):
                    with atomic_output(target, binary=True) as stream:
                        stream.write(b'new')
            self.assertTrue(link.is_symlink())
            self.assertEqual(original.read_bytes(), b'keep')
            self.assertFalse(list(out.glob('.*.pending-*')))
            with self.assertRaises(PublicationError) as caught:
                with atomic_output(out/'absent'/'capture.fsckpt', binary=True):
                    self.fail('entered writer without destination directory')
            self.assertFalse(caught.exception.published)
            self.assertEqual(caught.exception.errno, errno.ENOENT)

    def test_concurrent_writers_and_readers_only_observe_complete_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'capture.fsckpt'
            versions = {b'old', b'a'*100003, b'b'*99991}
            target.write_bytes(b'old')
            parked = threading.Barrier(3); release = threading.Event()
            failures = []
            def writer(data):
                try:
                    with atomic_output(target, binary=True) as stream:
                        stream.write(data[:7]); stream.flush()
                        parked.wait(timeout=10); release.wait(timeout=10)
                        stream.write(data[7:])
                except BaseException as error: failures.append(error)
            threads = [threading.Thread(target=writer, args=(data,)) for data in list(versions - {b'old'})]
            for thread in threads: thread.start()
            try:
                parked.wait(timeout=10)
                old_reader = target.open('rb')
                self.assertEqual(target.read_bytes(), b'old')
                release.set()
                while any(t.is_alive() for t in threads):
                    self.assertIn(target.read_bytes(), versions)
                with old_reader:
                    self.assertEqual(old_reader.read(), b'old')
                self.assertIn(target.read_bytes(), versions - {b'old'})
                self.assertEqual(failures, [])
                self.assertFalse(list(Path(directory).glob('.*.pending-*')))
            finally:
                release.set()
                for thread in threads: thread.join(timeout=10)

    def test_sigkill_at_partial_write_sync_and_rename_boundaries(self):
        # An actual killed writer cannot run exception cleanup. It may leave
        # private pending files, but never publishes a partial checkpoint.
        script = '''
import os, stat, sys, signal
from tools.checkpoint_formats.durable import atomic_output
target, phase, ready = sys.argv[1], sys.argv[2], int(sys.argv[3])
def stop():
    os.write(ready, b'R')
    signal.pause()
real_sync, real_replace = os.fsync, os.replace
syncs = 0
def sync(fd):
    global syncs
    isdir = stat.S_ISDIR(os.fstat(fd).st_mode)
    if isdir: syncs += 1
    if phase == 'file-sync' and not isdir: stop()
    if phase == 'after-rename' and isdir and syncs == 2: stop()
    real_sync(fd)
def replace(*args, **kwargs):
    if phase == 'before-rename': stop()
    real_replace(*args, **kwargs)
os.fsync, os.replace = sync, replace
with atomic_output(target, binary=True) as stream:
    stream.write(b'new')
    if phase == 'partial-write':
        stream.flush(); stop()
    stream.write(b' complete checkpoint')
'''
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            for existing in (False, True):
                for phase in ('partial-write', 'file-sync', 'before-rename', 'after-rename'):
                    with self.subTest(existing=existing, phase=phase):
                        case = out/f'{existing}-{phase}'; case.mkdir()
                        target = case/'capture.fsckpt'
                        if existing: target.write_bytes(b'old')
                        read_fd, write_fd = os.pipe()
                        process = subprocess.Popen([sys.executable, '-c', script, str(target), phase, str(write_fd)],
                                                   pass_fds=(write_fd,), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        os.close(write_fd)
                        try:
                            self.assertTrue(select.select([read_fd], [], [], 10)[0], 'writer did not reach boundary')
                            self.assertEqual(os.read(read_fd, 1), b'R')
                            process.kill(); _, errors = process.communicate(timeout=10)
                            self.assertEqual(process.returncode, -signal.SIGKILL, errors.decode())
                            self.assertEqual(target.read_bytes() if target.exists() else None,
                                             b'new complete checkpoint' if phase == 'after-rename' else b'old' if existing else None)
                            self.assertEqual(len(list(case.glob('.*.pending-*'))), 0 if phase == 'after-rename' else 1)
                        finally:
                            os.close(read_fd)
                            if process.poll() is None:
                                process.kill(); process.communicate(timeout=10)


if __name__ == '__main__': unittest.main()
