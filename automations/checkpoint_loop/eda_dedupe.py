#!/usr/bin/env python3
"""Reclaim duplicate EDA artifact extents without deleting or hard-linking files.

Linux FIDEDUPERANGE compares bytes in the kernel before sharing disk extents.
The files keep independent inodes, metadata and copy-on-write semantics. This is
an explicit maintenance command, never an automatic part of verification.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
RUNS = Path("automations/checkpoint_loop/runs")
FIDEDUPERANGE = 0xC0189436
# Keep requests bounded; filesystems can deduplicate less than requested.
CHUNK = 16 * 1024 * 1024
ALIGNMENT = 4096


def identity(info):
    # atime can change on reads. Everything else here must remain unchanged.
    return (info.st_dev, info.st_ino, info.st_size, info.st_mode,
            info.st_uid, info.st_gid, info.st_mtime_ns)


def dedupe(source: Path, destination: Path) -> dict:
    """Share only kernel-verified equal ranges, without changing file metadata."""
    flags = os.O_NOFOLLOW | os.O_CLOEXEC
    with os.fdopen(os.open(source, os.O_RDONLY | flags), "rb") as src, \
            os.fdopen(os.open(destination, os.O_RDWR | flags), "r+b") as dst:
        before = [os.fstat(src.fileno()), os.fstat(dst.fileno())]
        if not all(stat.S_ISREG(s.st_mode) for s in before):
            raise ValueError("dedupe requires regular files")
        if before[0].st_dev != before[1].st_dev or before[0].st_size != before[1].st_size:
            raise ValueError("dedupe requires same-device, equal-size files")
        if before[0].st_ino == before[1].st_ino:
            return dict(status="same_inode", bytes_deduped=0)
        size = before[0].st_size
        # A partial final block is deliberately left alone (no rounding beyond EOF).
        limit = size - size % ALIGNMENT
        offset = 0
        shared = 0
        different = 0
        while offset < limit:
            length = min(CHUNK, limit - offset)
            request = bytearray(struct.pack("=QQHHIqQQiI", offset, length, 1, 0, 0,
                                            dst.fileno(), offset, 0, 0, 0))
            fcntl.ioctl(src.fileno(), FIDEDUPERANGE, request, True)
            _, _, _, _, _, _, _, count, status, _ = struct.unpack("=QQHHIqQQiI", request)
            if status < 0:
                raise OSError(-status, os.strerror(-status), str(destination))
            if status == 1:  # FILE_DEDUPE_RANGE_DIFFERS: no sharing for this range.
                different += length
                offset += length
            elif status == 0 and 0 < count <= length and count % ALIGNMENT == 0:
                shared += count
                offset += count
            else:
                raise RuntimeError(f"unexpected FIDEDUPERANGE result: {status}, {count}")
        after = [os.fstat(src.fileno()), os.fstat(dst.fileno())]
        if [identity(s) for s in before] != [identity(s) for s in after]:
            raise RuntimeError("artifact changed during extent deduplication")
    return dict(status="equal" if different == 0 else "different", bytes_deduped=shared,
                bytes_different=different, unshared_tail_bytes=size-limit,
                source_identity=identity(before[0]), destination_identity=identity(before[1]))


def sample(path: Path) -> tuple:
    """Cheap candidate filter only; the kernel still compares every shared byte."""
    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        digest = hashlib.sha256(stream.read(65536))
        stream.seek(max(0, info.st_size - 65536))
        digest.update(stream.read(65536))
    return info.st_dev, info.st_size, digest.hexdigest()


def selftest(out: Path) -> dict:
    """Independently check contents, metadata and COW isolation on this filesystem."""
    with tempfile.TemporaryDirectory(prefix="dedupe-selftest-", dir=out) as directory:
        source, target, different = [Path(directory) / s for s in ("source", "target", "different")]
        data = bytes(range(256)) * 4096
        for path in (source, target):
            path.write_bytes(data)
        different.write_bytes(bytes(reversed(range(256))) * 4096)
        os.utime(source, ns=(1700000000000000000, 1700000000000000001))
        os.utime(target, ns=(1700000000000000000, 1700000000000000002))
        before = [identity(p.stat()) for p in (source, target, different)]
        result = dedupe(source, target)
        unequal = dedupe(source, different)
        assert result["bytes_deduped"] == len(data) and result["status"] == "equal"
        assert unequal["bytes_deduped"] == 0 and unequal["status"] == "different"
        assert before == [identity(p.stat()) for p in (source, target, different)]
        assert source.read_bytes() == target.read_bytes() == data
        assert different.read_bytes() == bytes(reversed(range(256))) * 4096
        with target.open("r+b") as stream:
            stream.write(b"changed")
        assert source.read_bytes() == data and target.read_bytes() != data
        return dict(status="pass", equal=result, unequal=unequal,
                    sha256=hashlib.sha256(data).hexdigest(), independent_inodes=True,
                    preserved_contents_and_metadata=True, copy_on_write_isolated=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="share duplicate extents; default inventories only")
    parser.add_argument("--minimum-bytes", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--target-free-bytes", type=int, default=16 * 1024**3,
                        help="stop after this much free space is available; 0 processes all candidates")
    parser.add_argument("--out", type=Path, required=True, help="new evidence directory beneath runs/")
    args = parser.parse_args()
    if args.minimum_bytes < ALIGNMENT:
        parser.error("minimum must be at least one filesystem block")
    if args.target_free_bytes < 0:
        parser.error("target free space cannot be negative")
    if not (ROOT / ".checkpoint-eda-owner").is_file():
        parser.error("only run in the claimed EDA mirror")
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / RUNS):
        parser.error("evidence must be beneath runs/")
    out.mkdir(parents=True, exist_ok=False)
    receipt = out / "receipt.jsonl"
    started = datetime.now(timezone.utc).isoformat()
    source_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    initial = os.statvfs(ROOT)
    # Generated source/build files only, never checkpoints, traces or live logs.
    groups = defaultdict(list)
    scope = ROOT / RUNS / "aws-f2"
    for directory, dirs, files in os.walk(scope, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in {"build-host", "local-build", ".Xil"}
                         and not (Path(directory)/d).is_symlink() and not (Path(directory)/d).is_relative_to(out))
        for name in sorted(files):
            p = Path(directory) / name
            if p.suffix in {".fir", ".v", ".sv", ".json", ".dcp"} and not p.is_symlink():
                info = p.stat()
                if stat.S_ISREG(info.st_mode) and info.st_size >= args.minimum_bytes:
                    groups[(info.st_dev, info.st_size)].append(p)
    with receipt.open("x") as stream:
        if args.apply:
            result = selftest(out)
            stream.write(json.dumps(dict(selftest=result)) + "\n")
            stream.flush()
        candidates = defaultdict(list)
        for paths in groups.values():
            if len(paths) > 1:
                for p in paths:
                    candidates[sample(p)].append(p)
        pairs = shared = 0
        stopped = False
        # Recover capacity promptly from large generated sources before small
        # duplicates. Reclamation is bounded independently of regression scope.
        for key, paths in sorted(candidates.items(), key=lambda item: item[0][1], reverse=True):
            for destination in paths[1:]:
                available = os.statvfs(ROOT)
                if args.apply and args.target_free_bytes and available.f_bavail*available.f_frsize >= args.target_free_bytes:
                    stopped = True
                    break
                row = dict(source=str(paths[0]), destination=str(destination), sample=list(key))
                if args.apply:
                    row.update(dedupe(paths[0], destination))
                    shared += row["bytes_deduped"]
                else:
                    row["status"] = "candidate_only"
                pairs += 1
                stream.write(json.dumps(row) + "\n")
                stream.flush()
            if stopped:
                break
    final = os.statvfs(ROOT)
    summary = dict(status="pass", applied=args.apply, started_utc=started,
                   finished_utc=datetime.now(timezone.utc).isoformat(), root=str(ROOT),
                   kernel_operation="FIDEDUPERANGE", pairs=pairs, bytes_deduped=shared,
                   stopped_at_free_space_target=stopped, target_free_bytes=args.target_free_bytes,
                   available_bytes_before=initial.f_bavail*initial.f_frsize,
                   available_bytes_after=final.f_bavail*final.f_frsize,
                   receipt=str(receipt), receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
                   source_sha256=source_digest,
                   hardware_acceptance=False)
    (out/"summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(out/"summary.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
