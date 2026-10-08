"""Checks for the loop's safety-critical logging and milestone gates."""

import json
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import loop
from loop import BoundedLog, render_codex_event, verification_plan
from milestones import MILESTONES


class LoopTests(unittest.TestCase):
    def test_codex_tool_and_agent_events_are_visible(self):
        command = {"type": "item.completed", "item": {
            "type": "command_execution", "command": "make run-vcs",
            "exit_code": 1, "aggregated_output": "failed at cycle 17"}}
        answer = {"type": "item.completed", "item": {
            "type": "agent_message", "text": "fixed the counter"}}
        self.assertIn("failed at cycle 17", render_codex_event(json.dumps(command)))
        self.assertIn("fixed the counter", render_codex_event(json.dumps(answer)))

    def test_log_rotation_preserves_result_and_bounds_old_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "loop.log"
            sink = BoundedLog(path, max_bytes=32, backups=2)
            sink.write("x" * 257)
            sink.close()
            total = sum(p.stat().st_size for p in path.parent.iterdir())
            self.assertLessEqual(total, 32 * 3)
            self.assertTrue(path.is_file())

    def test_vcs_milestone_cannot_advance_without_vcs_check(self):
        report = {"status": "ready", "verification_commands": [
            {"purpose": "placeholder", "cwd": ".", "argv": ["true"]}]}
        with self.assertRaisesRegex(ValueError, "VCS command"):
            verification_plan(report, MILESTONES[2])

    def test_oversize_codex_event_streams_without_parsing(self):
        original = loop.MAX_PARSED_EVENT_CHARS
        try:
            loop.MAX_PARSED_EVENT_CHARS = 32
            payload = '{"type":"item.completed","item":{"text":"' + "z" * 100 + '"}}\n'
            chunks = list(loop.bounded_json_lines(io.StringIO(payload)))
            self.assertEqual("".join(piece for piece, _ in chunks), payload)
            self.assertTrue(all(not parseable for _, parseable in chunks))
        finally:
            loop.MAX_PARSED_EVENT_CHARS = original

    def test_git_checkpoint_excludes_preexisting_dirty_file(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "test"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.org"], check=True)
            existing = repo / "existing.txt"
            existing.write_text("original\n")
            subprocess.run(["git", "-C", str(repo), "add", "existing.txt"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "initial"], check=True)
            existing.write_text("user change\n")
            (repo / "agent.txt").write_text("agent change\n")
            owned = loop.stage_owned(repo, {"existing.txt": loop.file_fingerprint(existing)})
            self.assertEqual(owned, ["agent.txt"])
            staged = loop.git(repo, "diff", "--cached", "--name-only").stdout.decode().strip()
            self.assertEqual(staged, "agent.txt")


if __name__ == "__main__":
    unittest.main()
