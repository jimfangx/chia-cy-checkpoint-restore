#!/usr/bin/env python3
"""Explicit, byte-preserving recovery of retained EDA waveform capacity.

An input plan names exact files and independently recorded complete SHA256s.
Every byte is hashed before AND after the kernel compares/shares equal ranges.
Original files, independent inodes, differing ranges and unaligned tails stay
intact. This maintenance operation never establishes simulation acceptance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import tempfile

from eda_dedupe import ALIGNMENT, CHUNK, FIDEDUPERANGE, ROOT, RUNS, identity


def capacity(path: Path) -> dict:
    info = os.statvfs(path)
    return dict(available_bytes=info.f_bavail * info.f_frsize,
                available_inodes=info.f_favail)


def require_capacity(path: Path, required_bytes: int, required_inodes: int) -> dict:
    observed = capacity(path)
    if (observed['available_bytes'] < required_bytes or
            observed['available_inodes'] < required_inodes):
        raise RuntimeError(f'EDA storage capacity insufficient: {observed}; '
                           f'require bytes={required_bytes}, inodes={required_inodes}; '
                           'preserve evidence and recover capacity before launching VCS')
    return observed


def share(source: Path, destination: Path, source_sha256: str,
          destination_sha256: str, *, progress=None) -> dict:
    """Bound memory and I/O while auditing full files, including different data.

    No file creation is needed, allowing bootstrap on a completely full disk.
    Expected hashes authenticate the result; the ioctl itself compares bytes
    even when a supplied hash is wrong. A failure never falls back to copying,
    truncation, unlinking, hard links, or substituting compressed waveforms.
    """
    expected = [source_sha256, destination_sha256] * 2
    if any(len(h) != 64 or any(c not in '0123456789abcdef' for c in h) for h in expected):
        raise ValueError('expected complete lowercase SHA256 digests')
    flags = os.O_CLOEXEC | os.O_NOFOLLOW
    sfd = os.open(source, os.O_RDONLY | flags)
    try:
        dfd = os.open(destination, os.O_RDWR | flags)
        try:
            before = [os.fstat(sfd), os.fstat(dfd)]
            if not all(stat.S_ISREG(i.st_mode) for i in before):
                raise ValueError('waveform sharing requires regular files')
            if before[0].st_dev != before[1].st_dev or before[0].st_size != before[1].st_size:
                raise ValueError('waveform sharing requires equal sizes and one filesystem')
            if before[0].st_ino == before[1].st_ino:
                raise ValueError('waveforms must retain independent inodes')
            if before[1].st_uid != os.getuid():
                raise ValueError('destination must be owned by the EDA user')
            digests = [hashlib.sha256() for _ in range(4)]
            size = before[0].st_size
            aligned_end = size - size % ALIGNMENT
            offset = shared = different = ranges = 0
            while offset < size:
                # A differing VCD date usually occupies the first block. Hash
                # it completely but leave it private, as well as the EOF tail.
                length = (min(ALIGNMENT, size) if offset == 0 else
                          min(CHUNK, aligned_end-offset) if offset < aligned_end else size-offset)
                x, y = os.pread(sfd, length, offset), os.pread(dfd, length, offset)
                if len(x) != length or len(y) != length:
                    raise RuntimeError('waveform truncated during storage audit')
                digests[0].update(x)
                digests[1].update(y)
                if offset >= ALIGNMENT and offset < aligned_end:
                    # Handle partial successful ioctls instead of skipping the
                    # remainder or hashing a prefix twice.
                    done = 0
                    while done < length:
                        request = bytearray(struct.pack('=QQHHIqQQiI', offset+done,
                            length-done, 1, 0, 0, dfd, offset+done, 0, 0, 0))
                        fcntl.ioctl(sfd, FIDEDUPERANGE, request, True)
                        row = struct.unpack('=QQHHIqQQiI', request)
                        count, status = row[7:9]
                        ranges += 1
                        if status == 1 and count == 0:
                            different += length-done
                            break
                        if status < 0:
                            raise OSError(-status, os.strerror(-status), str(destination))
                        if status != 0 or not 0 < count <= length-done or count % ALIGNMENT:
                            raise RuntimeError(f'invalid kernel sharing result: {count}, {status}')
                        shared += count
                        done += count
                after_x, after_y = os.pread(sfd, length, offset), os.pread(dfd, length, offset)
                if after_x != x or after_y != y:
                    raise RuntimeError('waveform bytes changed during storage audit')
                digests[2].update(after_x)
                digests[3].update(after_y)
                offset += length
                if progress:
                    progress(dict(audited_bytes=offset, total_bytes=size, bytes_shared=shared))
            actual = [h.hexdigest() for h in digests]
            if actual != expected:
                raise ValueError(f'complete waveform digest mismatch: expected={expected}, actual={actual}')
            if [identity(i) for i in before] != [identity(os.fstat(fd)) for fd in (sfd, dfd)]:
                raise RuntimeError('waveform metadata changed during storage audit')
            # Also detect path replacement: keeping an open fd is insufficient.
            if [identity(i) for i in before] != [identity(p.lstat()) for p in (source, destination)]:
                raise RuntimeError('waveform path changed during storage audit')
            return dict(source=str(source), destination=str(destination), size=size,
                        source_identity=identity(before[0]), destination_identity=identity(before[1]),
                        complete_before_after_digests=actual, bytes_shared=shared,
                        bytes_different=different, ranges=ranges,
                        original_regular_files_preserved=True)
        finally:
            os.close(dfd)
    finally:
        os.close(sfd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--required-free-bytes', type=int, default=256 * 1024**3)
    parser.add_argument('--required-free-inodes', type=int, default=100000)
    args = parser.parse_args()
    if min(args.required_free_bytes, args.required_free_inodes) < 0:
        parser.error('capacity requirements must be nonnegative')
    if not (ROOT / '.checkpoint-eda-owner').is_file():
        parser.error('run only in the claimed EDA mirror')
    scope = (ROOT / RUNS).resolve()
    if not args.out.resolve().is_relative_to(scope) or not args.plan.resolve().is_relative_to(scope):
        parser.error('plan and evidence must be beneath runs/')
    plan_bytes = args.plan.read_bytes()
    plan = json.loads(plan_bytes)
    for row in plan:
        for key in ('source', 'destination'):
            p = Path(row[key])
            if not p.is_absolute() or not p.resolve().is_relative_to(scope) or p.is_symlink():
                parser.error('plan files must be regular retained files beneath EDA runs/')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='wave-storage-', dir=args.out))
    doc = dict(status='running', backend='eda', observed_utc=datetime.now(timezone.utc).isoformat(),
               physical_fpga_capture=False, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               plan_sha256=hashlib.sha256(plan_bytes).hexdigest(), plan=str(args.plan.resolve()),
               required_free_bytes=args.required_free_bytes, required_free_inodes=args.required_free_inodes,
               before=capacity(ROOT), rows=[], removed_files=[])

    def save():
        pending = out / 'summary.pending'
        pending.write_text(json.dumps(doc, indent=2)+'\n')
        pending.replace(out / 'summary.json')

    save()
    print(out, flush=True)
    try:
        for row in plan:
            doc['rows'].append(share(Path(row['source']), Path(row['destination']),
                                    row['source_sha256'], row['destination_sha256']))
            save()
        doc['after'] = require_capacity(ROOT, args.required_free_bytes, args.required_free_inodes)
        doc['status'] = 'pass'
    except BaseException as error:
        doc.update(status='fail', error_type=type(error).__name__, error=str(error), after=capacity(ROOT))
        raise
    finally:
        save()
    print(out / 'summary.json', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
