"""Checks for the loop's safety-critical logging and milestone gates."""

import json
import io
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import loop
from loop import BoundedLog, render_codex_event, verification_plan
from milestones import LEGACY_MILESTONE_ORDER, MILESTONES


class LoopTests(unittest.TestCase):
    def test_legacy_resume_skips_retired_work_without_skipping_cpu_work(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            for old_index in range(len(LEGACY_MILESTONE_ORDER) + 1):
                with self.subTest(old_index=old_index):
                    original = dict(milestone_index=old_index, iteration=174,
                                    feedback="saved feedback", commits={"chipyard": "saved"},
                                    baseline={"chipyard": list(loop.READ_ONLY_PLANS), "firesim": []})
                    loop.save_state(path, original)
                    state = loop.load_state(path)
                    expected = old_index if old_index < 8 else max(8, old_index - 3)
                    self.assertEqual(state["milestone_index"], expected)
                    self.assertEqual(state["milestone_order"], [m.name for m in MILESTONES])
                    for key in ("iteration", "feedback", "commits", "baseline"):
                        self.assertEqual(state[key], original[key])
                    self.assertEqual(loop.load_state(path), state)
            # The actual saved position resumes the same CPU family.
            self.assertEqual(MILESTONES[8].name, LEGACY_MILESTONE_ORDER[11])

    def test_invalid_resume_position_does_not_rewrite_saved_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            for index in (-1, len(LEGACY_MILESTONE_ORDER) + 1):
                loop.save_state(path, dict(milestone_index=index, baseline={}))
                original = path.read_bytes()
                with self.assertRaisesRegex(ValueError, "saved milestone"):
                    loop.load_state(path)
                self.assertEqual(path.read_bytes(), original)

    def test_new_state_uses_active_order(self):
        with self.repositories() as (_, _, state_path):
            state = loop.load_state(state_path)
            self.assertEqual(state["milestone_index"], 0)
            self.assertEqual(state["milestone_order"], [m.name for m in MILESTONES])

    def test_dry_run_requires_only_vcs_and_codex(self):
        with patch.object(sys, "argv", ["loop.py", "--dry-run"]), \
                patch.object(loop, "VCS") as vcs, \
                patch.object(loop.shutil, "which", return_value="/tools/codex"), \
                redirect_stdout(io.StringIO()) as output:
            vcs.is_file.return_value = True
            self.assertEqual(loop.main(), 0)
        self.assertIn("M11-rocket-level1-level2", output.getvalue())
        self.assertNotIn("Jasper:", output.getvalue())
        self.assertNotIn("M8-formal-state-map:", output.getvalue())

    @contextmanager
    def repositories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "chipyard"
            fire = Path(directory) / "firesim"
            for repo in (root, fire):
                repo.mkdir()
                loop.git(repo, "init", "-q")
                loop.git(repo, "config", "user.name", "test")
                loop.git(repo, "config", "user.email", "test@example.org")
                (repo / "existing.txt").write_text("original\n")
                if repo == root:
                    for name in loop.READ_ONLY_PLANS:
                        (repo / name).write_text("original plan\n")
                loop.git(repo, "add", ".")
                loop.git(repo, "commit", "-qm", "initial")
            with patch.object(loop, "ROOT", root), patch.object(loop, "FIRE", fire):
                yield root, fire, Path(directory) / "state.json"

    def test_resume_accepts_plan_edits_and_preserves_progress(self):
        with self.repositories() as (root, fire, state_path):
            # Emulate an older saved run, including its dirty-plan fingerprint.
            baseline = {"chipyard": {"plan_agent.md": "outdated-fingerprint"}, "firesim": {}}
            old_state = {"milestone_index": 2, "iteration": 7, "feedback": "continue",
                         "baseline": baseline, "commits": {"chipyard": "saved-commit"}}
            loop.save_state(state_path, old_state)
            for name in loop.READ_ONLY_PLANS:
                (root / name).write_text("updated user plan\n")
            state = loop.load_state(state_path)
            for key in ("milestone_index", "iteration", "feedback", "commits"):
                self.assertEqual(state[key], old_state[key])
            self.assertEqual(json.loads(state_path.read_text()), state)
            for name in loop.READ_ONLY_PLANS:
                self.assertEqual((root / name).read_text(), "updated user plan\n")
                self.assertIn(name, state["baseline"]["chipyard"])
            self.assertIsInstance(state["baseline"]["chipyard"], list)
            self.assertEqual(state["baseline"]["firesim"], [])
            (root / "agent.txt").write_text("agent work\n")
            self.assertEqual(loop.stage_owned(root, state["baseline"]["chipyard"]), ["agent.txt"])
            self.assertEqual(loop.git(root, "diff", "--cached", "--name-only").stdout.decode().strip(),
                             "agent.txt")

    def test_plan_edits_during_run_are_excluded_without_blocking_checkpoint(self):
        with self.repositories() as (root, fire, state_path):
            state = loop.load_state(state_path)
            for name in loop.READ_ONLY_PLANS:
                plan = root / name
                plan.write_text("updated user plan\n")
            (root / "agent.txt").write_text("agent work\n")
            commits = loop.checkpoint_both(1, "test", "wip", state["baseline"])
            self.assertEqual(set(commits), {"chipyard", "firesim"})
            self.assertEqual(loop.git(root, "show", "HEAD:agent.txt").stdout, b"agent work\n")
            for name in loop.READ_ONLY_PLANS:
                self.assertEqual(loop.git(root, "show", f"HEAD:{name}").stdout, b"original plan\n")
                self.assertEqual((root / name).read_text(), "updated user plan\n")

    def test_resume_accepts_other_preexisting_edits_and_keeps_them_excluded(self):
        with self.repositories() as (root, fire, state_path):
            for repo in (root, fire):
                (repo / "existing.txt").write_text("user change\n")
            state = loop.load_state(state_path)
            for repo in (root, fire):
                existing = repo / "existing.txt"
                existing.write_text("updated user change\n")
            resumed = loop.load_state(state_path)
            self.assertEqual(resumed, state)
            loop.checkpoint_both(1, "test", "wip", resumed["baseline"])
            for repo in (root, fire):
                self.assertEqual(loop.git(repo, "show", "HEAD:existing.txt").stdout, b"original\n")
                self.assertEqual((repo / "existing.txt").read_text(), "updated user change\n")

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
            owned = loop.stage_owned(repo, ["existing.txt"])
            self.assertEqual(owned, ["agent.txt"])
            staged = loop.git(repo, "diff", "--cached", "--name-only").stdout.decode().strip()
            self.assertEqual(staged, "agent.txt")


if __name__ == "__main__":
    unittest.main()
