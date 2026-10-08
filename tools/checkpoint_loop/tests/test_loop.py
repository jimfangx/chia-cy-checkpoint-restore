"""Checks for the loop's safety-critical logging and milestone gates."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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


if __name__ == "__main__":
    unittest.main()
