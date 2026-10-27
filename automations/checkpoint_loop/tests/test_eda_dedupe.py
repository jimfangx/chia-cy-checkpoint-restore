"""Extent recovery must preserve independent artifacts and reject unsafe results."""

import os
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eda_dedupe


class DedupeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name)/"source"
        self.target = Path(self.temp.name)/"target"
        self.data = b"a" * (3*4096 + 7)
        self.source.write_bytes(self.data)
        self.target.write_bytes(self.data)

    def kernel(self, fd, op, request, mutate):
        self.assertEqual(op, eda_dedupe.FIDEDUPERANGE)
        self.assertTrue(mutate)
        row = list(struct.unpack("=QQHHIqQQiI", request))
        self.assertEqual(row[2:5], [1, 0, 0])
        self.assertEqual(row[0], row[6])
        self.assertEqual(os.pread(fd, row[1], row[0]), os.pread(row[5], row[1], row[6]))
        row[7] = min(row[1], 4096)  # A kernel may complete less than requested.
        request[:] = struct.pack("=QQHHIqQQiI", *row)

    def test_partial_progress_keeps_tail_contents_metadata_and_inodes(self):
        before = [eda_dedupe.identity(p.stat()) for p in (self.source, self.target)]
        with patch.object(eda_dedupe.fcntl, "ioctl", side_effect=self.kernel) as ioctl:
            result = eda_dedupe.dedupe(self.source, self.target)
        self.assertEqual(ioctl.call_count, 3)
        self.assertEqual(result["bytes_deduped"], 3*4096)
        self.assertEqual(result["unshared_tail_bytes"], 7)
        self.assertEqual(before, [eda_dedupe.identity(p.stat()) for p in (self.source, self.target)])
        self.assertNotEqual(self.source.stat().st_ino, self.target.stat().st_ino)
        self.assertEqual(self.target.read_bytes(), self.data)

    def test_kernel_rejects_differences_and_errors_without_fallback_writes(self):
        def response(status):
            def ioctl(fd, op, request, mutate):
                row = list(struct.unpack("=QQHHIqQQiI", request))
                row[8] = status
                request[:] = struct.pack("=QQHHIqQQiI", *row)
            return ioctl
        with patch.object(eda_dedupe.fcntl, "ioctl", side_effect=response(1)):
            result = eda_dedupe.dedupe(self.source, self.target)
        self.assertEqual(result["bytes_deduped"], 0)
        self.assertEqual(result["bytes_different"], 3*4096)
        for status, error in ((-95, OSError), (0, RuntimeError), (2, RuntimeError)):
            with self.subTest(status=status), patch.object(eda_dedupe.fcntl, "ioctl", side_effect=response(status)):
                with self.assertRaises(error):
                    eda_dedupe.dedupe(self.source, self.target)
        self.assertEqual(self.target.read_bytes(), self.data)

    def test_alias_symlink_size_and_concurrent_modification_rejected(self):
        self.assertEqual(eda_dedupe.dedupe(self.source, self.source)["status"], "same_inode")
        link = self.target.with_name("link")
        link.symlink_to(self.target)
        with self.assertRaises(OSError):
            eda_dedupe.dedupe(self.source, link)
        self.target.write_bytes(b"short")
        with self.assertRaises(ValueError):
            eda_dedupe.dedupe(self.source, self.target)
        self.target.write_bytes(self.data)
        def modifying_kernel(*args):
            self.kernel(*args)
            os.utime(self.target, ns=(1700000000000000000, 1700000000000000000))
        with patch.object(eda_dedupe.fcntl, "ioctl", side_effect=modifying_kernel):
            with self.assertRaisesRegex(RuntimeError, "artifact changed"):
                eda_dedupe.dedupe(self.source, self.target)

    def test_sample_collision_is_only_a_candidate(self):
        self.source.write_bytes(b"a" * 200000)
        self.target.write_bytes(b"a" * 100000 + b"b" + b"a" * 99999)
        self.assertEqual(eda_dedupe.sample(self.source), eda_dedupe.sample(self.target))
        # Actual sharing always uses the kernel's full-range comparison.
        self.assertNotEqual(self.source.read_bytes(), self.target.read_bytes())

    def test_inventory_is_read_only_and_apply_stops_at_capacity_target(self):
        root = Path(self.temp.name)
        (root/".checkpoint-eda-owner").write_text("checkpoint_loop\n")
        scope = root/eda_dedupe.RUNS/"aws-f2/old-generated"
        scope.mkdir(parents=True)
        for name in ("first.fir", "second.fir"):
            (scope/name).write_bytes(self.data)
        for apply, name in ((False, "inventory"), (True, "bounded")):
            out = root/eda_dedupe.RUNS/name
            argv = ["eda_dedupe.py", "--out", str(out), "--minimum-bytes", "4096",
                    "--target-free-bytes", "1"] + (["--apply"] if apply else [])
            with patch.object(eda_dedupe, "ROOT", root), patch.object(sys, "argv", argv), \
                    patch.object(eda_dedupe, "selftest", return_value={"status":"pass"}) as selftest, \
                    patch.object(eda_dedupe, "dedupe") as dedupe:
                self.assertEqual(eda_dedupe.main(), 0)
                dedupe.assert_not_called()
                self.assertEqual(selftest.call_count, int(apply))
            summary = json.loads((out/"summary.json").read_text())
            self.assertEqual(summary["applied"], apply)
            self.assertEqual(summary["pairs"], 0 if apply else 1)
            self.assertEqual(summary["stopped_at_free_space_target"], apply)
            self.assertEqual((scope/"first.fir").read_bytes(), self.data)
            self.assertEqual((scope/"second.fir").read_bytes(), self.data)


if __name__ == "__main__":
    unittest.main()
