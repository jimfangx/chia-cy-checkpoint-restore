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
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import loop
from loop import BoundedLog, render_codex_event, verification_plan
from milestones import LEGACY_MILESTONE_ORDER, MILESTONES


class LoopTests(unittest.TestCase):
    def test_legacy_resume_requires_new_hardware_acceptance_and_keeps_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            for old_index in range(len(LEGACY_MILESTONE_ORDER) + 1):
                with self.subTest(old_index=old_index):
                    original = dict(milestone_index=old_index, iteration=174,
                                    feedback="saved feedback", commits={"chipyard": "saved"},
                                    baseline={"chipyard": list(loop.READ_ONLY_PLANS), "firesim": []})
                    loop.save_state(path, original)
                    state = loop.load_state(path)
                    expected = min(old_index, 8)
                    self.assertEqual(state["milestone_index"], expected)
                    self.assertEqual(state["milestone_order"], [m.name for m in MILESTONES])
                    self.assertEqual(set(state["completed_milestones"]),
                                     set(LEGACY_MILESTONE_ORDER[:old_index]))
                    for key in ("iteration", "feedback", "commits", "baseline"):
                        self.assertEqual(state[key], original[key])
                    self.assertEqual(loop.load_state(path), state)
            self.assertEqual(MILESTONES[8].name, "F2-bringup-and-baseline")

    def test_completed_metasim_cpu_run_cannot_skip_hardware_milestones(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            old_order = list(LEGACY_MILESTONE_ORDER[:8] + LEGACY_MILESTONE_ORDER[11:])
            original = dict(milestone_index=len(old_order), milestone_order=old_order,
                            iteration=211, feedback="old metasim complete", commits={"chipyard": "old"},
                            baseline={"chipyard": [], "firesim": []})
            loop.save_state(path, original)
            migrated = loop.load_state(path)
            self.assertEqual(migrated["milestone_index"], 8)
            self.assertEqual(migrated["iteration"], 211)
            self.assertTrue(set(old_order).issubset(migrated["completed_milestones"]))
            self.assertEqual(loop.load_state(path), migrated)

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

    def test_dry_run_prints_f2_and_eda_without_network_or_state_changes(self):
        with patch.object(sys, "argv", ["loop.py", "--dry-run"]), \
                patch.object(loop.RemoteWorkspace, "preflight") as preflight, \
                patch.object(loop.shutil, "which", return_value="/tools/codex"), \
                redirect_stdout(io.StringIO()) as output:
            self.assertEqual(loop.main(), 0)
        preflight.assert_not_called()
        self.assertIn("Remote VCS:", output.getvalue())
        self.assertIn("F2-rocket-checkpoint-migration", output.getvalue())
        self.assertIn("Capture: actual AWS F2 FPGA", output.getvalue())
        self.assertNotIn("Jasper:", output.getvalue())
        self.assertNotIn("M8-formal-state-map:", output.getvalue())

    def test_f2_cpu_acceptance_requires_hardware_and_eda_vcs_checks(self):
        report = {"status": "ready", "verification_commands": [
            {"purpose": "VCS restore", "cwd": ".", "argv": ["vcs", "-full64"], "backend": "eda"}]}
        hardware = MILESTONES[9]
        self.assertTrue(hardware.needs_f2 and hardware.needs_vcs)
        with self.assertRaisesRegex(ValueError, "AWS F2"):
            verification_plan(report, hardware)
        report["verification_commands"].append(
            {"purpose": "FPGA execution", "cwd": "sims/firesim/deploy",
             "argv": ["firesim", "runworkload"], "backend": "f2"})
        self.assertEqual(verification_plan(report, hardware)[-1]["execution"], "f2")
        report["verification_commands"] = report["verification_commands"][-1:]
        with self.assertRaisesRegex(ValueError, "EDA VCS"):
            verification_plan(report, hardware)

    def test_unknown_backend_cannot_bypass_remote_routing(self):
        with self.assertRaisesRegex(ValueError, "backend"):
            verification_plan({"verification_commands": [
                {"purpose": "bypass", "cwd": ".", "argv": ["vcs"], "backend": "local"}]}, MILESTONES[2])

    def test_eda_results_arrive_before_f2_and_new_fpga_capture_is_resynced(self):
        events = []
        workspace, manager = MagicMock(), MagicMock()
        workspace.config.host = "eda"
        workspace.config.root = "/scratch/mirror"
        workspace.preflight.side_effect = lambda: events.append("eda check")
        workspace.push.side_effect = lambda: events.append("upload")
        workspace.run.side_effect = lambda *a: events.append("eda run") or 0
        workspace.fetch.side_effect = lambda: events.append("download")
        manager.run.side_effect = lambda *a: events.append("fpga capture") or 0
        checks = [{"purpose": "restore", "argv": ["simv"], "cwd": ".", "execution": "eda"},
                  {"purpose": "capture", "argv": ["capture"], "cwd": ".", "execution": "f2"},
                  {"purpose": "new restore", "argv": ["simv"], "cwd": ".", "execution": "eda"}]
        with patch.object(loop, "RemoteWorkspace", return_value=workspace), \
                patch.object(loop, "F2Manager", return_value=manager):
            results = loop.run_verification(checks, MagicMock())
        self.assertEqual(events, ["eda check", "upload", "eda run", "download", "fpga capture",
                                  "eda check", "upload", "eda run", "download"])
        self.assertEqual([r["backend"] for r in results], ["eda", "f2", "eda"])

    def test_f2_work_does_not_require_eda_connectivity(self):
        workspace, manager = MagicMock(), MagicMock()
        manager.run.return_value = 0
        with patch.object(loop, "RemoteWorkspace", return_value=workspace), \
                patch.object(loop, "F2Manager", return_value=manager):
            results = loop.run_verification(
                [{"purpose": "FPGA", "argv": ["firesim", "runworkload"],
                  "cwd": ".", "execution": "f2"}], MagicMock())
        workspace.preflight.assert_not_called()
        workspace.push.assert_not_called()
        self.assertEqual(results[0]["returncode"], 0)

    def test_report_commands_cannot_opt_into_local_execution(self):
        report = {"status": "ready", "verification_commands": [
            {"purpose": "VCS", "cwd": ".", "argv": ["vcs", "-full64"],
             "execution": "local"}]}
        commands = verification_plan(report, MILESTONES[2])
        self.assertEqual([c["execution"] for c in commands], ["local", "local", "eda"])

    def test_failed_remote_check_returns_artifacts_and_stops_following_checks(self):
        workspace = MagicMock()
        workspace.config.host = "eda"
        workspace.run.return_value = 42
        log = MagicMock()
        commands = [{"purpose": "simulation", "cwd": ".", "argv": ["simv"]},
                    {"purpose": "later", "cwd": ".", "argv": ["true"]}]
        with patch.object(loop, "RemoteWorkspace", return_value=workspace):
            results = loop.run_verification(commands, log)
        workspace.push.assert_called_once()
        workspace.run.assert_called_once_with(["simv"], ".")
        workspace.fetch.assert_called_once()
        self.assertEqual(results[0]["returncode"], 42)
        self.assertEqual(results[0]["host"], "eda")
        self.assertEqual(len(results), 1)

    def test_fetch_failure_prevents_acceptance_even_after_passing_simulation(self):
        workspace = MagicMock()
        workspace.config.host = "eda"
        workspace.run.return_value = 0
        workspace.fetch.side_effect = RuntimeError("SSH disconnected")
        with patch.object(loop, "RemoteWorkspace", return_value=workspace):
            results = loop.run_verification(
                [{"purpose": "simulation", "cwd": ".", "argv": ["simv"]}], MagicMock())
        self.assertEqual([r["returncode"] for r in results], [0, 127])

    def test_ssh_failure_is_returned_as_failed_verification(self):
        workspace = MagicMock()
        workspace.config.host = "eda"
        workspace.preflight.side_effect = RuntimeError("SSH unavailable")
        with patch.object(loop, "RemoteWorkspace", return_value=workspace):
            results = loop.run_verification(
                [{"purpose": "simulation", "cwd": ".", "argv": ["simv"]}], MagicMock())
        workspace.run.assert_not_called()
        self.assertEqual(results[0]["returncode"], 127)

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
