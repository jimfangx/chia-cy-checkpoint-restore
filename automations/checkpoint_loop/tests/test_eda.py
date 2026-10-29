"""Real rsync round trips through a local SSH stand-in; no licensed EDA execution."""

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eda


class EdaTests(unittest.TestCase):
    @contextmanager
    def workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            local = base / "local workspace"
            remote = base / "remote workspace"
            helper = local / "automations/checkpoint_loop"
            helper.mkdir(parents=True)
            (local / eda.RUNS).mkdir()
            (local / "sims/firesim").mkdir(parents=True)
            (local / "env.sh").write_text("echo WRONG_LOCAL_ENV; return 99\n")
            (local / "sims/firesim/env.sh").write_text("return 99\n")
            (local / "source.txt").write_text("first version\n")
            (local / ".aws").mkdir()
            (local / ".aws/credentials").write_text("do not copy")
            (local / ".conda-env").mkdir()
            (local / ".conda-env/private").write_text("do not copy")
            (local / ".git").mkdir()
            (local / ".git/HEAD").write_text("git metadata\n")
            (local / ".git/index").write_text("real index\n")
            (local / ".git/index.lock").write_text("transient root index lock\n")
            gitdir = local / "sims/firesim/.git/modules/platforms/f1/aws-fpga"
            gitdir.mkdir(parents=True)
            (gitdir / "HEAD").write_text("submodule metadata\n")
            (gitdir / "index").write_text("submodule index\n")
            (gitdir / "index.lock").write_text("transient submodule index lock\n")
            (local / "input.lock").write_text("real source input\n")
            (local / eda.RUNS / "state.json").write_text("local state")
            (local / eda.RUNS / "seed.txt").write_text("input seed")
            (local / eda.RUNS / "migration-source").mkdir()
            (local / eda.RUNS / "migration-source/resume-notes.txt").write_text("original migration input")
            (local / eda.RUNS / "one-build/build-host").mkdir(parents=True)
            (local / eda.RUNS / "one-build/build-host/private-build").write_text("local Vivado worktree")
            (local / eda.RUNS / "native/.Xil/realtime/tmp").mkdir(parents=True)
            (local / eda.RUNS / "native/.Xil/realtime/tmp/volatile.rtd").write_text("live Vivado scratch")
            (local / eda.RUNS / "native/state.dcp").write_text("retained synthesis evidence")
            shutil.copy2(eda.ROOT / "automations/checkpoint_loop/vcs-env.sh", helper)
            shutil.copytree(eda.ROOT / "automations/checkpoint_loop/compiler-bin", helper / "compiler-bin")
            bin_dir = base / "bin"
            bin_dir.mkdir()
            ssh = bin_dir / "ssh"
            ssh.write_text(
                "#!/bin/bash\n"
                'while [[ "$1" == -o ]]; do shift 2; done\n'
                '[[ "$1" == fake-eda ]] || exit 88\nshift\n'
                'exec /bin/sh -c "$*"\n')
            ssh.chmod(0o755)
            vcs = base / "mock-vcs/bin/vcs"
            vcs.parent.mkdir(parents=True)
            vcs.write_text("#!/bin/sh\necho 'mock compiler for transport tests only'\n")
            vcs.chmod(0o755)
            setup = base / "native-setup.sh"
            setup.write_text("export SNPSLMD_LICENSE_FILE=already-sourced-test-license\n")
            output = []
            config = eda.EdaConfig(host="fake-eda", root=str(remote), vcs=str(vcs), setup=str(setup))
            workspace = eda.RemoteWorkspace(config, local, output.append)
            with patch.dict(os.environ, {"PATH": str(bin_dir) + ":" + os.environ["PATH"]}):
                yield workspace, local, remote, output

    @unittest.skipUnless(shutil.which("rsync"), "rsync required")
    def test_round_trip_mapping_native_env_failure_and_control_protection(self):
        with self.workspace() as (workspace, local, remote, output):
            workspace.preflight()
            self.assertFalse(remote.exists())  # Dry preflight does not mirror.
            with workspace.locked():
                workspace.push()
                self.assertFalse((remote / ".aws").exists())
                self.assertFalse((remote / ".conda-env").exists())
                self.assertEqual((remote / ".git/HEAD").read_text(), "git metadata\n")
                self.assertEqual((remote / ".git/index").read_text(), "real index\n")
                self.assertFalse((remote / ".git/index.lock").exists())
                gitdir = remote / "sims/firesim/.git/modules/platforms/f1/aws-fpga"
                self.assertEqual((gitdir / "HEAD").read_text(), "submodule metadata\n")
                self.assertEqual((gitdir / "index").read_text(), "submodule index\n")
                self.assertFalse((gitdir / "index.lock").exists())
                self.assertEqual((remote / "input.lock").read_text(), "real source input\n")
                self.assertFalse((remote / eda.RUNS / "state.json").exists())
                self.assertFalse((remote / eda.RUNS / "one-build/build-host").exists())
                self.assertFalse((remote / eda.RUNS / "native/.Xil").exists())
                self.assertEqual((remote / eda.RUNS / "native/state.dcp").read_text(), "retained synthesis evidence")
                migration = remote / eda.RUNS / "migration-source/resume-notes.txt"
                self.assertEqual(migration.read_text(), "original migration input")
                migration.write_text("remote cannot replace the migration archive")
                self.assertNotIn("WRONG_LOCAL_ENV", (remote / "env.sh").read_text())
                code = workspace.run(["bash", "-lc",
                    'source env.sh && source sims/firesim/env.sh && '
                    'source automations/checkpoint_loop/vcs-env.sh && '
                    'source automations/checkpoint_loop/vcs-env.sh && '
                    'printf "%s\\n" "$PWD" "$SNPSLMD_LICENSE_FILE" "$VCS_HOME" '
                    '> automations/checkpoint_loop/runs/returned.txt; exit 23'])
                self.assertEqual(code, 23)
                (remote / eda.RUNS / "state.json").write_text("remote must not win")
                (remote / eda.RUNS / "verification.log").write_text("remote must not win")
                (remote / eda.RUNS / "remote-native/.Xil").mkdir(parents=True)
                (remote / eda.RUNS / "remote-native/.Xil/volatile.rtd").write_text("scratch")
                (remote / eda.RUNS / "remote-native/timing.rpt").write_text("retained timing evidence")
                workspace.fetch()
                self.assertFalse((local / eda.RUNS / "remote-native/.Xil").exists())
                self.assertEqual((local / eda.RUNS / "remote-native/timing.rpt").read_text(), "retained timing evidence")
                result = (local / eda.RUNS / "returned.txt").read_text()
                self.assertIn(str(remote), result)
                self.assertIn("already-sourced-test-license", result)
                self.assertEqual((local / eda.RUNS / "state.json").read_text(), "local state")
                self.assertFalse((local / eda.RUNS / "verification.log").exists())
                self.assertEqual((local / eda.RUNS / "migration-source/resume-notes.txt").read_text(),
                                 "original migration input")
                # Remote inputs survive source deletion sync and native env is kept.
                (local / "source.txt").unlink()
                (remote / eda.RUNS / "remote-only.txt").write_text("evidence")
                workspace.push()
                self.assertFalse((remote / "source.txt").exists())
                self.assertEqual((remote / eda.RUNS / "remote-only.txt").read_text(), "evidence")
                # Exact argv survives shell metacharacters and whitespace.
                argument = 'literal $HOME `id` "quotes" ; exit 91'
                destination = str(local / eda.RUNS / "argv.txt")
                self.assertEqual(workspace.run([
                    "/bin/sh", "-c", 'printf %s "$1" > "$2"', "argv-test", argument, destination]), 0)
                workspace.fetch()
                self.assertEqual((local / eda.RUNS / "argv.txt").read_text(), argument)

    @unittest.skipUnless(shutil.which("rsync"), "rsync required")
    def test_fetch_preserves_concurrent_manager_evidence_and_returns_new_remote_results(self):
        with self.workspace() as (workspace, local, remote, _):
            with workspace.locked():
                local_log = local / eda.RUNS / "vivado.log"
                local_log.write_text("synthesis started\n")
                os.utime(local_log, (1700000000, 1700000000))
                workspace.push()
                # The manager continues writing after EDA receives its inputs.
                local_log.write_text("synthesis started\nsynthesis completed\n")
                os.utime(local_log, (1700000010, 1700000010))
                result = remote / eda.RUNS / "fresh-eda.log"
                result.write_text("new EDA result\n")
                # Also check updates to an already returned EDA output.
                local_result = local / eda.RUNS / "updated-eda.log"
                local_result.write_text("old EDA result\n")
                os.utime(local_result, (1700000000, 1700000000))
                remote_result = remote / eda.RUNS / "updated-eda.log"
                remote_result.write_text("newer EDA result\n")
                os.utime(remote_result, (1700000010, 1700000010))
                workspace.fetch()
                self.assertEqual(local_log.read_text(), "synthesis started\nsynthesis completed\n")
                self.assertEqual((local / eda.RUNS / "fresh-eda.log").read_text(), "new EDA result\n")
                self.assertEqual(local_result.read_text(), "newer EDA result\n")

    @unittest.skipUnless(shutil.which("rsync"), "rsync required")
    def test_unrelated_remote_directory_is_not_overwritten(self):
        with self.workspace() as (workspace, _, remote, _):
            remote.mkdir()
            owned_by_user = remote / "user-work"
            owned_by_user.write_text("keep")
            with self.assertRaises(RuntimeError):
                workspace.push()
            self.assertEqual(owned_by_user.read_text(), "keep")

    @unittest.skipUnless(shutil.which("rsync"), "rsync required")
    def test_noninteractive_nested_shell_loads_explicit_site_license(self):
        with self.workspace() as (workspace, local, _, output):
            setup = Path(workspace.config.setup)
            license_setup = setup.with_name("site-license.sh")
            license_setup.write_text("export SNPSLMD_LICENSE_FILE=1701@site-test\nexport LM_PROJECT=site-users\n")
            setup.write_text("unset SNPSLMD_LICENSE_FILE LM_LICENSE_FILE\n"
                             "export CHECKPOINT_EDA_LICENSE_SETUP=" + str(license_setup) + "\n")
            with workspace.locked():
                workspace.push()
                code = workspace.run(["bash", "-lc",
                    'unset SNPSLMD_LICENSE_FILE LM_LICENSE_FILE; '
                    'source automations/checkpoint_loop/vcs-env.sh && '
                    'printf "%s\\n" "$SNPSLMD_LICENSE_FILE" "$LM_PROJECT" '
                    '> automations/checkpoint_loop/runs/license.txt'])
                workspace.fetch()
            self.assertEqual(code, 0)
            self.assertEqual((local / eda.RUNS / "license.txt").read_text(), "1701@site-test\nsite-users\n")

    @unittest.skipUnless(shutil.which("rsync"), "rsync required")
    def test_missing_explicit_license_setup_fails_before_running_command(self):
        with self.workspace() as (workspace, local, _, output):
            Path(workspace.config.setup).write_text(
                "export CHECKPOINT_EDA_LICENSE_SETUP=/nonexistent/checkpoint-license.sh\n")
            with workspace.locked():
                workspace.push()
                code = workspace.run(["bash", "-c", "echo MUST_NOT_RUN"])
            self.assertNotEqual(code, 0)
            self.assertNotIn("\nMUST_NOT_RUN\n", "".join(output))

    def test_invalid_remote_config_and_workdir_rejected(self):
        for key, value in (("CHECKPOINT_EDA_HOST", "-oProxyCommand=bad"),
                           ("CHECKPOINT_EDA_ROOT", "/scratch/jfx/../"),
                           ("CHECKPOINT_EDA_ROOT", "/scratch/jfx")):
            with self.subTest(key=key, value=value), patch.dict(os.environ, {key: value}):
                with self.assertRaises(ValueError):
                    eda.EdaConfig.from_env()
        workspace = eda.RemoteWorkspace(eda.EdaConfig())
        for cwd in ("..", "/tmp", "sims/../../outside"):
            with self.assertRaises(ValueError):
                workspace.command(["vcs"], cwd)


if __name__ == "__main__":
    unittest.main()
