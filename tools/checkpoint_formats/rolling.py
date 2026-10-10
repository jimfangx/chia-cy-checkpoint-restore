"""Level-1 retained history and progress policies, independent of Level-2.

This is a host-side API, not a live simulator capture adapter. Callers supply
complete settled-cut v3 images. Native payload semantics are still checked by
the all-owner restore coordinator before any target edge. A history directory
is private to one build/configuration; all API readers/writers take its lock.
Only the atomic index commits snapshots. Private files and unindexed images
left by killed writers are never candidates for restore.
"""
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat

from .aggregate import digest
from .aggregate_packed import decode_aggregate, runtime_manifest
from .codec import HASH, canonical, keys, require, unique_object

MAX_CYCLE = 2**64 - 1
INDEX = 'history.json'
LOCK = '.history.lock'
SCHEMA = 'firesim.rolling.level1.v1'


def counter(value):
    require(type(value) is int and 0 <= value <= MAX_CYCLE, 'invalid unsigned progress counter')
    return value


class CycleSchedule:
    """First eligible settled cut at/after each target deadline; no host units.

    A leap over deadlines produces one actual cut, never fabricated intermediate
    cuts. A failed publication leaves the deadline due. Restore must construct
    a new schedule with the restored target-cycle origin.
    """
    def __init__(self, interval, origin=0):
        require(counter(interval) > 0, 'target interval must be positive')
        self.interval = interval
        self.origin = self.last = counter(origin)
        self.deadline = origin + interval if origin + interval <= MAX_CYCLE else None

    def due(self, target_cycle):
        target_cycle = counter(target_cycle)
        require(target_cycle >= self.last, 'target cycle regressed; reinitialize after restore')
        self.last = target_cycle
        return self.deadline is not None and target_cycle >= self.deadline

    def committed(self, target_cycle):
        require(self.due(target_cycle), 'checkpoint committed before target deadline')
        next_cycle = self.origin + ((target_cycle - self.origin)//self.interval + 1)*self.interval
        self.deadline = next_cycle if next_cycle <= MAX_CYCLE else None


class ProgressWatchdogs:
    """Host stall by monotonic time; target stall by advancing target cycles.

    The host sampler must run independently of the simulation worker. Target
    progress is an audited cumulative retirement/transaction counter supplied
    by the caller, not RTL switching activity. None explicitly disables that
    watchdog. Capture overhead and worker suspension need runtime accounting;
    this policy deliberately does not infer it or start a timer thread.
    """
    def __init__(self, *, host_timeout_ns=None, target_timeout_cycles=None):
        for value in (host_timeout_ns, target_timeout_cycles):
            require(value is None or counter(value) > 0, 'watchdog timeout must be positive')
        require(host_timeout_ns is not None or target_timeout_cycles is not None, 'no watchdog enabled')
        self.host_timeout = host_timeout_ns
        self.target_timeout = target_timeout_cycles
        self.previous = None
        self.host_changed_ns = self.cycle_changed_ns = self.target_changed_cycle = None
        self.failure = None

    def sample(self, *, monotonic_ns, host_progress, target_cycle, target_progress=None):
        values = tuple(counter(v) for v in (monotonic_ns, host_progress, target_cycle))
        require(self.target_timeout is None or target_progress is not None,
                'target watchdog requires an audited progress counter')
        if target_progress is not None:
            counter(target_progress)
        now, host, cycle = values
        if self.previous is None:
            self.host_changed_ns, self.target_changed_cycle = now, cycle
            self.cycle_changed_ns = now
        else:
            old_now, old_host, old_cycle, old_progress = self.previous
            require(now >= old_now and host >= old_host and cycle >= old_cycle,
                    'watchdog counters regressed; reinitialize after restore')
            require((target_progress is None) == (old_progress is None), 'changed target progress availability')
            require(target_progress is None or target_progress >= old_progress, 'target progress regressed')
            if host != old_host:
                self.host_changed_ns = now
            if cycle != old_cycle:
                self.cycle_changed_ns = now
            if target_progress != old_progress:
                self.target_changed_cycle = cycle
        self.previous = (*values, target_progress)
        if self.failure is None:
            if self.host_timeout is not None and now - self.host_changed_ns >= self.host_timeout:
                self.failure = 'host_progress_stall'
            elif self.host_timeout is not None and now - self.cycle_changed_ns >= self.host_timeout:
                self.failure = 'target_cycle_stall'
            elif self.target_timeout is not None and cycle - self.target_changed_cycle >= self.target_timeout:
                self.failure = 'target_progress_stall'
        return self.failure


class HistoryError(RuntimeError):
    """A visible index may be committed even if durability/pruning failed."""
    def __init__(self, committed, cause):
        self.committed = committed
        super().__init__(f'rolling history failed (index_committed={committed}): {cause}')


class RollingHistory:
    def __init__(self, directory, *, retention, build, manifest, generated, layout):
        require(type(retention) is int and 0 < retention <= MAX_CYCLE, 'invalid checkpoint retention')
        require(manifest.get('schema') == 'firesim.aggregate.lowclock.v3' and
                manifest == runtime_manifest(manifest['profile'], generated, layout,
                    manifest['native_owners'], manifest['native_build_hash'],
                    manifest['cut_contract']['target_cycle_owner']), 'rolling history requires bound v3 Level-1 state')
        self.directory = Path(directory)
        self.retention = retention
        # Freeze caller-owned identity tables so later mutation cannot rebind a store.
        self.build, self.manifest, self.generated, self.layout = copy.deepcopy((build, manifest, generated, layout))
        self.binding = digest(dict(build=build, manifest=manifest, generated=generated, layout=layout))
        self.prefix = 'snapshot-' + self.binding + '-'
        self.pattern = re.compile(re.escape(self.prefix) + r'([0-9]{20})-([0-9a-f]{64})\.fsckpt\Z')

    @contextmanager
    def _locked(self):
        directory = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        lock = None
        try:
            lock = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                           0o600, dir_fd=directory)
            require(stat.S_ISREG(os.fstat(lock).st_mode), 'history lock must be a regular file')
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield directory
        finally:
            if lock is not None:
                os.close(lock)
            os.close(directory)

    def _read(self, directory, name):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, 'rb') as stream:
            require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'history input must be a regular file')
            return stream.read()

    def _decode(self, data):
        return decode_aggregate(data, self.build, self.manifest, self.generated, self.layout)

    def _image(self, directory, record):
        keys(record, {'name', 'target_cycle', 'sha256', 'bytes'})
        cycle = counter(record['target_cycle'])
        require(type(record['name']) is str and self.pattern.fullmatch(record['name']) and
                type(record['sha256']) is str and HASH.fullmatch(record['sha256']) and
                type(record['bytes']) is int and record['bytes'] > 0, 'invalid history record')
        require(record['name'] == f'{self.prefix}{cycle:020d}-{record["sha256"]}.fsckpt',
                'history filename disagrees with identity')
        data = self._read(directory, record['name'])
        require(len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256'],
                'retained checkpoint integrity failure')
        require(self._decode(data)['target_cycle'] == cycle, 'retained target cycle mismatch')
        return data

    def _index(self, directory):
        try:
            data = self._read(directory, INDEX)
        except FileNotFoundError:
            return dict(schema=SCHEMA, binding=self.binding, retention=self.retention, records=[])
        doc = json.loads(data, object_pairs_hook=unique_object)
        keys(doc, {'schema', 'binding', 'retention', 'records'})
        require(data == canonical(doc) and doc['schema'] == SCHEMA and doc['binding'] == self.binding and
                type(doc['retention']) is int and doc['retention'] == self.retention and
                type(doc['records']) is list and 0 < len(doc['records']) <= self.retention,
                'incompatible/noncanonical history index')
        last = -1
        for record in doc['records']:
            self._image(directory, record)
            require(record['target_cycle'] > last, 'history cycles must strictly increase')
            last = record['target_cycle']
        return doc

    def _write(self, directory, data):
        name = '.history.pending-' + secrets.token_hex(16)
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            os.unlink(name, dir_fd=directory)
            raise
        return name

    def publish(self, data):
        # Invalid state cannot even open/create the history lock.
        doc = self._decode(data)
        cycle = doc['target_cycle']
        sha = hashlib.sha256(data).hexdigest()
        record = dict(name=f'{self.prefix}{cycle:020d}-{sha}.fsckpt', target_cycle=cycle,
                      sha256=sha, bytes=len(data))
        with self._locked() as directory:
            old = self._index(directory)
            require(not old['records'] or cycle > old['records'][-1]['target_cycle'],
                    'new snapshot must advance target cycles')
            new = dict(old, records=(old['records'] + [record])[-self.retention:])
            pending = None
            committed = False
            try:
                os.fsync(directory)
                pending = self._write(directory, data)
                # No replacement of an existing snapshot; immutable names.
                try:
                    os.link(pending, record['name'], src_dir_fd=directory, dst_dir_fd=directory,
                            follow_symlinks=False)
                except FileExistsError:
                    # An earlier interrupted attempt may have left this exact
                    # immutable image. Reuse only after complete readback.
                    require(self._image(directory, record) == data, 'conflicting immutable snapshot')
                os.unlink(pending, dir_fd=directory)
                pending = None
                os.fsync(directory)
                self._image(directory, record)  # Reopen and validate actual on-disk bytes.
                pending = self._write(directory, canonical(new))
                os.replace(pending, INDEX, src_dir_fd=directory, dst_dir_fd=directory)
                pending = None
                committed = True
                os.fsync(directory)
                require(self._index(directory) == new, 'committed history readback failed')
                self._prune(directory, new)
            except Exception as error:
                raise HistoryError(committed, error) from error
            finally:
                if pending is not None:
                    os.unlink(pending, dir_fd=directory)
        return dict(record)

    def _prune(self, directory, index):
        retained = {r['name'] for r in index['records']}
        obsolete = []
        for name in os.listdir(directory):
            match = self.pattern.fullmatch(name)
            if match and name not in retained:
                # Validate every candidate before deleting any. No foreign or
                # partial/pending file is removed, including killed writers'.
                data = self._read(directory, name)
                record = dict(name=name, target_cycle=int(match[1]), sha256=match[2], bytes=len(data))
                self._image(directory, record)
                obsolete.append(name)
        for name in obsolete:
            os.unlink(name, dir_fd=directory)
        os.fsync(directory)

    def recover(self):
        """Validate committed history and finish interrupted retention cleanup."""
        with self._locked() as directory:
            index = self._index(directory)
            if index['records']:
                # Confirm a possibly interrupted index rename is durable before
                # reclaiming either its predecessors or orphaned complete images.
                os.fsync(directory)
                self._prune(directory, index)
            return copy.deepcopy(index['records'])

    def select(self, *, before_target_cycle):
        """Newest committed snapshot strictly before the suspected causal cut.

        Return bytes opened/validated under lock, so concurrent retention cannot
        remove the file between selection and consumption. The caller must use
        the bytes or publish a separately pinned restore input, not reopen name.
        """
        bound = counter(before_target_cycle)
        with self._locked() as directory:
            index = self._index(directory)
            candidates = [r for r in index['records'] if r['target_cycle'] < bound]
            require(bool(candidates), 'no retained checkpoint before requested target cycle')
            record = candidates[-1]
            return dict(record), self._image(directory, record)
