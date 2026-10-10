"""Filesystem crashes/concurrency, complete v3 validation and policy checks."""
import copy
import errno
import json
import multiprocessing
import os
from pathlib import Path
import signal
import stat
import tempfile
import threading
import unittest
from unittest.mock import patch

from tools.checkpoint_formats import aggregate, aggregate_packed as packed
from tools.checkpoint_formats.codec import FormatError, canonical, decode, encode
from tools.checkpoint_formats.rolling import (CycleSchedule, HistoryError, INDEX, LOCK,
                                            MAX_CYCLE, ProgressWatchdogs, RollingHistory)
from tools.checkpoint_formats.tests import test_aggregate_packed


def fixture(out):
    build, manifest, generated, layout, data = test_aggregate_packed.PackedAggregateTest().fixture(out)
    doc = decode(data, 'fsckpt', build)
    generated = copy.deepcopy(generated)
    entry = next(e for e in generated['state'] if e['kind'] == 'register')
    entry['width'] = 64
    manifest = packed.runtime_manifest(manifest['profile'], generated, layout,
        manifest['native_owners'], manifest['native_build_hash'], entry['hierarchy'])
    build = aggregate.build_identity(manifest, generated, layout, out/'simv')
    doc['build'] = build
    row = next(r for r in doc['records'] if r['owner'] == 'generated-entry/'+entry['hierarchy'])
    row.update(width=64, value=f'{doc["target_cycle"]:016x}')
    def image(cycle):
        result = copy.deepcopy(doc)
        result['target_cycle'] = cycle
        next(r for r in result['records'] if r['owner'] == row['owner'])['value'] = f'{cycle:016x}'
        return encode('fsckpt', result)
    arguments = dict(build=build, manifest=manifest, generated=generated, layout=layout, retention=2)
    return arguments, image


class RollingTest(unittest.TestCase):
    def test_retention_selects_only_committed_strictly_earlier_cuts(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            args, image = fixture(out)
            store = RollingHistory(out, **args)
            foreign = out/'other.fsckpt'; foreign.write_bytes(b'foreign')
            pending = out/'.history.pending-interrupted'; pending.write_bytes(b'incomplete')
            schedule = CycleSchedule(10)
            for cycle in (10, 21, 43, 50):
                self.assertTrue(schedule.due(cycle))
                record = store.publish(image(cycle))
                schedule.committed(cycle)
                self.assertEqual(store.select(before_target_cycle=cycle+1), (record, image(cycle)))
                retained = store.recover()
                self.assertLessEqual(len(retained), 2)
                self.assertEqual(len(list(out.glob(store.prefix+'*.fsckpt'))), len(retained))
                self.assertEqual(stat.S_IMODE((out/record['name']).stat().st_mode), 0o600)
            self.assertEqual([r['target_cycle'] for r in store.recover()], [43, 50])
            self.assertEqual(store.select(before_target_cycle=50)[0]['target_cycle'], 43)
            with self.assertRaises(FormatError): store.select(before_target_cycle=43)
            self.assertEqual(foreign.read_bytes(), b'foreign')
            self.assertEqual(pending.read_bytes(), b'incomplete')

    def test_invalid_incomplete_and_level2_state_reject_before_filesystem_access(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); args, image = fixture(out)
            store = RollingHistory(out/'absent', **args)
            doc = decode(image(10), 'fsckpt', args['build'])
            invalid = [image(10)[:-1], image(10)+b'0', encode('fsckpt', dict(doc, target_cycle=11))]
            missing = copy.deepcopy(doc); missing['records'].pop(); invalid.append(encode('fsckpt', missing))
            high = copy.deepcopy(doc)
            next(r for r in high['records'] if r['owner'] == 'harness/emul.fin')['value'] = '1'
            invalid.append(encode('fsckpt', high))
            with patch('tools.checkpoint_formats.rolling.os.open', side_effect=AssertionError('filesystem accessed')):
                for data in invalid:
                    with self.assertRaises(FormatError): store.publish(data)
            bad = copy.deepcopy(args); bad['manifest']['schema'] = 'firesim.aggregate.lowclock.v2'
            with self.assertRaises(FormatError): RollingHistory(out, **bad)
            for retention in (0, -1, True, 1.5):
                with self.assertRaises(FormatError): RollingHistory(out, **dict(args, retention=retention))

    def test_retained_corruption_incompatible_index_and_special_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); args, image = fixture(out)
            store = RollingHistory(out, **args)
            first = store.publish(image(10))
            before = (out/INDEX).read_bytes()
            path = out/first['name']; saved = path.read_bytes(); path.write_bytes(saved[:-1])
            for operation in (store.recover, lambda: store.select(before_target_cycle=30), lambda: store.publish(image(20))):
                with self.assertRaises(FormatError): operation()
                self.assertEqual((out/INDEX).read_bytes(), before)
            path.write_bytes(saved)
            doc = json.loads(before)
            changed = [dict(doc, retention=True), dict(doc, binding='0'*64),
                       dict(doc, records=doc['records']*2), dict(doc, extra=1)]
            traversal = copy.deepcopy(doc); traversal['records'][0]['name'] = '../simv'; changed.append(traversal)
            for bad in changed:
                (out/INDEX).write_bytes(canonical(bad))
                with self.assertRaises(FormatError): store.publish(image(20))
                self.assertEqual(path.read_bytes(), saved)
            (out/INDEX).write_bytes(before)
            for name in (INDEX, LOCK, first['name']):
                original = (out/name).read_bytes()
                for special in ('symlink', 'fifo', 'directory'):
                    (out/name).unlink()
                    if special == 'symlink': (out/name).symlink_to(out/'simv')
                    elif special == 'fifo': os.mkfifo(out/name)
                    else: (out/name).mkdir()
                    with self.assertRaises((FormatError, OSError)): store.recover()
                    if special == 'directory': (out/name).rmdir()
                    else: (out/name).unlink()
                    (out/name).write_bytes(original)
            with self.assertRaises(FormatError): store.publish(image(10))
            with self.assertRaises(FormatError): store.publish(image(9))
            self.assertEqual((out/INDEX).read_bytes(), before)

    def test_io_faults_preserve_old_files_until_durable_index_commit(self):
        for phase in ('preflight', 'snapshot-write', 'snapshot-link', 'snapshot-directory',
                      'readback', 'index-write', 'index-rename', 'index-directory', 'prune'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                out = Path(directory); args, image = fixture(out)
                store = RollingHistory(out, **dict(args, retention=1))
                first = store.publish(image(10)); old = (out/INDEX).read_bytes()
                real_sync, real_write, real_link, real_image = os.fsync, store._write, os.link, store._image
                syncs = writes = 0
                def sync(fd):
                    nonlocal syncs
                    if stat.S_ISDIR(os.fstat(fd).st_mode):
                        syncs += 1
                        if (phase, syncs) in (('preflight', 1), ('snapshot-directory', 2), ('index-directory', 3)):
                            raise OSError(errno.EIO, phase)
                    return real_sync(fd)
                def write(fd, data):
                    nonlocal writes
                    writes += 1
                    if (phase, writes) in (('snapshot-write', 1), ('index-write', 2)):
                        raise OSError(errno.ENOSPC, phase)
                    return real_write(fd, data)
                def link(*a, **k):
                    if phase == 'snapshot-link': raise OSError(errno.EIO, phase)
                    return real_link(*a, **k)
                def readback(fd, record):
                    if phase == 'readback' and record['target_cycle'] == 20:
                        raise FormatError('injected disk readback corruption')
                    return real_image(fd, record)
                with patch.object(store, '_write', side_effect=write), \
                     patch.object(store, '_image', side_effect=readback), \
                     patch('tools.checkpoint_formats.rolling.os.fsync', side_effect=sync), \
                     patch('tools.checkpoint_formats.rolling.os.link', side_effect=link), \
                     patch('tools.checkpoint_formats.rolling.os.replace',
                           side_effect=OSError(errno.EIO, phase) if phase == 'index-rename' else os.replace), \
                     patch.object(store, '_prune', side_effect=OSError(errno.EIO, phase) if phase == 'prune' else store._prune):
                    with self.assertRaises(HistoryError) as caught: store.publish(image(20))
                committed = phase in ('index-directory', 'prune')
                self.assertEqual(caught.exception.committed, committed)
                self.assertEqual((out/first['name']).read_bytes(), image(10))
                if not committed: self.assertEqual((out/INDEX).read_bytes(), old)
                self.assertEqual(store.select(before_target_cycle=30)[0]['target_cycle'], 20 if committed else 10)
                records = store.recover()
                self.assertEqual(len(list(out.glob(store.prefix+'*.fsckpt'))), len(records))

    def test_real_sigkill_before_and_after_index_commit(self):
        for phase in ('snapshot-file-sync', 'snapshot-directory', 'index-rename', 'index-directory', 'prune'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                out = Path(directory); args, image = fixture(out)
                store = RollingHistory(out, **dict(args, retention=1))
                first = store.publish(image(10)); old = (out/INDEX).read_bytes()
                parent, child = multiprocessing.Pipe()
                def writer():
                    parent.close()
                    def stop():
                        child.send('parked'); signal.pause()
                    real_sync, real_replace = os.fsync, os.replace
                    syncs = 0
                    def sync(fd):
                        nonlocal syncs
                        isdir = stat.S_ISDIR(os.fstat(fd).st_mode)
                        if isdir: syncs += 1
                        if (phase == 'snapshot-file-sync' and not isdir or
                            (phase, syncs) in (('snapshot-directory', 2), ('index-directory', 3)) and isdir): stop()
                        return real_sync(fd)
                    def replace(*a, **k):
                        if phase == 'index-rename': stop()
                        return real_replace(*a, **k)
                    with patch('tools.checkpoint_formats.rolling.os.fsync', side_effect=sync), \
                         patch('tools.checkpoint_formats.rolling.os.replace', side_effect=replace), \
                         patch.object(store, '_prune', side_effect=lambda *a: stop()):
                        store.publish(image(20))
                process = multiprocessing.get_context('fork').Process(target=writer)
                process.start(); child.close()
                try:
                    self.assertTrue(parent.poll(10), 'writer never reached crash boundary')
                    self.assertEqual(parent.recv(), 'parked')
                    process.kill(); process.join(10)
                    self.assertEqual(process.exitcode, -signal.SIGKILL)
                    committed = phase in ('index-directory', 'prune')
                    self.assertEqual((out/first['name']).read_bytes(), image(10))
                    if not committed: self.assertEqual((out/INDEX).read_bytes(), old)
                    self.assertEqual(store.select(before_target_cycle=30)[0]['target_cycle'], 20 if committed else 10)
                    records = store.recover()
                    self.assertEqual(len(list(out.glob(store.prefix+'*.fsckpt'))), len(records))
                    # A reader never treats abandoned partial files as a commit.
                    if phase == 'snapshot-file-sync': self.assertTrue(list(out.glob('.history.pending-*')))
                finally:
                    if process.is_alive(): process.kill(); process.join(10)
                    parent.close()

    def test_serialized_writers_and_pinned_reader_survive_retention(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); args, image = fixture(out)
            store = RollingHistory(out, **dict(args, retention=1))
            store.publish(image(10)); record, pinned = store.select(before_target_cycle=11)
            barrier = threading.Barrier(3); results = []; failures = []
            def writer():
                barrier.wait(timeout=10)
                try: store.publish(image(20)); results.append('committed')
                except FormatError: results.append('duplicate')
                except Exception as error: failures.append(error)
            threads = [threading.Thread(target=writer) for _ in range(2)]
            for thread in threads: thread.start()
            barrier.wait(timeout=10)
            while any(thread.is_alive() for thread in threads):
                selected, data = store.select(before_target_cycle=30)
                self.assertEqual(data, image(selected['target_cycle']))
            for thread in threads: thread.join(10)
            self.assertEqual(failures, [])
            self.assertCountEqual(results, ['committed', 'duplicate'])
            self.assertFalse((out/record['name']).exists())
            self.assertEqual(pinned, image(10))

    def test_failed_commit_retries_exact_orphan_and_directory_remains_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); args, image = fixture(root)
            out = root/'history'; out.mkdir()
            store = RollingHistory(out, **args)
            store.publish(image(10))
            with patch('tools.checkpoint_formats.rolling.os.replace', side_effect=OSError(errno.EIO, 'rename')):
                with self.assertRaises(HistoryError): store.publish(image(20))
            self.assertEqual(store.publish(image(20))['target_cycle'], 20)
            moved = root/'moved'
            real_write = store._write
            def write(fd, data):
                if not moved.exists():
                    out.rename(moved)
                    out.mkdir()
                    (out/'sentinel').write_bytes(b'replacement directory')
                return real_write(fd, data)
            with patch.object(store, '_write', side_effect=write): store.publish(image(30))
            self.assertEqual(sorted(p.name for p in out.iterdir()), ['sentinel'])
            rebound = RollingHistory(moved, **args)
            self.assertEqual([r['target_cycle'] for r in rebound.recover()], [20, 30])


class ProgressPolicyTest(unittest.TestCase):
    def test_target_deadlines_skipped_cycles_retry_restore_and_overflow(self):
        schedule = CycleSchedule(10, origin=5)
        for cycle in (5, 5, 14): self.assertFalse(schedule.due(cycle))
        self.assertTrue(schedule.due(15))
        self.assertTrue(schedule.due(15))  # A publication failure leaves the same cut due.
        schedule.committed(15)
        self.assertFalse(schedule.due(24))
        self.assertTrue(schedule.due(99)); schedule.committed(99)
        self.assertEqual(schedule.deadline, 105)
        with self.assertRaises(FormatError): schedule.due(98)
        restored = CycleSchedule(10, origin=99)
        self.assertFalse(restored.due(108)); self.assertTrue(restored.due(109))
        limit = CycleSchedule(3, origin=MAX_CYCLE-4)
        limit.committed(MAX_CYCLE-1)
        self.assertIsNone(limit.deadline); self.assertFalse(limit.due(MAX_CYCLE))
        for value in (True, -1, 0, MAX_CYCLE+1):
            with self.assertRaises(FormatError): CycleSchedule(value)

    def test_host_watchdog_detects_frozen_worker_and_frozen_target_with_live_host(self):
        for host, reason in ((7, 'host_progress_stall'), (8, 'target_cycle_stall')):
            watchdog = ProgressWatchdogs(host_timeout_ns=100)
            self.assertIsNone(watchdog.sample(monotonic_ns=1000, host_progress=7, target_cycle=30))
            self.assertIsNone(watchdog.sample(monotonic_ns=1099, host_progress=host, target_cycle=30))
            self.assertEqual(watchdog.sample(monotonic_ns=1100, host_progress=host, target_cycle=30), reason)
            self.assertEqual(watchdog.sample(monotonic_ns=1101, host_progress=9, target_cycle=31), reason)

    def test_target_watchdog_requires_audited_progress_and_target_time(self):
        watchdog = ProgressWatchdogs(host_timeout_ns=1000, target_timeout_cycles=10)
        def sample(now, cycle, progress):
            return watchdog.sample(monotonic_ns=now, host_progress=now, target_cycle=cycle, target_progress=progress)
        self.assertIsNone(sample(0, 20, 2))
        self.assertIsNone(sample(500, 20, 2))  # Wall time alone cannot consume target timeout.
        self.assertIsNone(sample(501, 29, 2))
        self.assertIsNone(sample(502, 30, 3))  # Retirement restarts the target-cycle window.
        self.assertIsNone(sample(503, 39, 3))
        self.assertEqual(sample(504, 40, 3), 'target_progress_stall')
        fresh = ProgressWatchdogs(target_timeout_cycles=10)
        with self.assertRaises(FormatError): fresh.sample(monotonic_ns=0, host_progress=0, target_cycle=0)
        fresh.sample(monotonic_ns=50, host_progress=20, target_cycle=30, target_progress=10)
        for values in ((49, 20, 30, 10), (50, 19, 30, 10), (50, 20, 29, 10), (50, 20, 30, 9)):
            with self.assertRaises(FormatError):
                fresh.sample(monotonic_ns=values[0], host_progress=values[1],
                             target_cycle=values[2], target_progress=values[3])


if __name__ == '__main__': unittest.main()
