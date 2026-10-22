"""Exercise the real kernel cap, descendant cleanup, and bwrap compatibility."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jasper_limits


class JasperLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = Path(f"/sys/fs/cgroup/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service")
        if not base.is_dir():
            raise unittest.SkipTest("requires a delegated systemd user cgroup")
        cls.temporary = tempfile.TemporaryDirectory()
        cls.socket = Path(cls.temporary.name) / "limits.sock"
        cls.slice = f"checkpoint-jasper-test{os.getpid()}.slice"
        cls.env = dict(os.environ, XDG_RUNTIME_DIR=f"/run/user/{os.getuid()}",
                       DBUS_SESSION_BUS_ADDRESS=f"unix:path=/run/user/{os.getuid()}/bus",
                       CHECKPOINT_JASPER_LIMIT_SOCKET=str(cls.socket),
                       CHECKPOINT_JASPER_BIN="/usr/bin/python3")
        cls.errors = (Path(cls.temporary.name) / "server.log").open("w")
        cls.server = subprocess.Popen(
            [sys.executable, str(Path(jasper_limits.__file__)), "--socket", str(cls.socket),
             "serve", "--memory-bytes", str(128 * 1024 * 1024), "--cgroup-name", cls.slice],
            env=cls.env, stdout=cls.errors, stderr=cls.errors)
        for _ in range(100):
            try:
                cls.status = jasper_limits.request(cls.socket, {"operation": "status"})
                break
            except (FileNotFoundError, ConnectionRefusedError):
                if cls.server.poll() is not None:
                    cls.errors.close()
                    raise RuntimeError((Path(cls.temporary.name) / "server.log").read_text())
                time.sleep(0.05)
        else:
            cls.server.terminate()
            raise RuntimeError("test limit broker did not start")
        cls.budget = Path(cls.status["cgroup"])
        cls.launcher = str(Path(jasper_limits.__file__).with_name("jasper-limited.sh"))

    @classmethod
    def tearDownClass(cls):
        for group in cls.budget.glob("checkpoint-jasper-job-*.scope"):
            if group.exists():
                (group / "cgroup.kill").write_text("1")
                subprocess.run(["systemctl", "--user", "stop", group.name], env=cls.env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        cls.server.terminate()
        cls.server.wait(timeout=10)
        subprocess.run(["systemctl", "--user", "stop", cls.slice], env=cls.env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        cls.errors.close()
        cls.temporary.cleanup()

    def run_job(self, code, timeout=30):
        return subprocess.run([self.launcher, "-c", code], env=self.env,
                              text=True, capture_output=True, timeout=timeout)

    def test_shared_cap_kills_two_jobs_and_their_children(self):
        before = dict(line.split() for line in (self.budget / "memory.events").read_text().splitlines())
        touch = "data=bytearray(70*1024*1024); data[::4096]=b'x'*len(data[::4096]); "
        code = ("import subprocess,time; " + touch +
                "child=subprocess.Popen(['/usr/bin/python3','-c','import time; time.sleep(30)']); "
                "print('allocated',child.pid,flush=True); time.sleep(30)")
        first = subprocess.Popen([self.launcher, "-c", code], env=self.env,
                                 text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(first.stdout.close)
        self.addCleanup(first.stderr.close)
        self.addCleanup(lambda: first.poll() is None and first.kill())
        ready = first.stdout.readline().split()
        self.assertEqual(ready[0], "allocated")
        child_pid = int(ready[1])
        second = self.run_job("import time; " + touch + "time.sleep(1)")
        killed = first.poll()
        if killed is None:
            # The kernel can choose either proof scope as its OOM victim.
            self.assertNotEqual(second.returncode, 0)
            first.terminate()
        first.communicate(timeout=10)
        self.assertTrue(killed not in (None, 0) or second.returncode != 0)
        self.assertIsNone(jasper_limits.process_identity(child_pid))
        after = dict(line.split() for line in (self.budget / "memory.events").read_text().splitlines())
        self.assertGreater(int(after["oom_group_kill"]), int(before["oom_group_kill"]))
        self.assertEqual((self.budget / "memory.max").read_text().strip(), str(128 * 1024 * 1024))
        self.assertEqual((self.budget / "memory.swap.max").read_text().strip(), "0")

    def test_timeout_kills_engine_descendants(self):
        pidfile = Path(self.temporary.name) / "child.pid"
        code = ("import subprocess,time; "
                "child=subprocess.Popen(['/usr/bin/python3','-c','import time; time.sleep(30)']); "
                f"open({str(pidfile)!r},'w').write(str(child.pid)); time.sleep(30)")
        result = subprocess.run([self.launcher, "-c", code],
            env=dict(self.env, CHECKPOINT_JASPER_TIMEOUT_SECONDS="1"),
            text=True, capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(jasper_limits.process_identity(int(pidfile.read_text())))

    def test_normal_exit_cleans_orphan_engines(self):
        pidfile = Path(self.temporary.name) / "orphan.pid"
        code = ("import subprocess; "
                "child=subprocess.Popen(['/usr/bin/python3','-c','import time; time.sleep(30)']); "
                f"open({str(pidfile)!r},'w').write(str(child.pid))")
        result = self.run_job(code, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(jasper_limits.process_identity(int(pidfile.read_text())))

    def test_jasper_stays_in_workspace_sandbox(self):
        result = subprocess.run(
            ["codex", "sandbox", "-P", "checkpoint",
             "-c", 'permissions.checkpoint.extends=":workspace"',
             "-c", "permissions.checkpoint.network.enabled=true", "--",
             "/usr/bin/env", f"CHECKPOINT_JASPER_LIMIT_SOCKET={self.socket}",
             "CHECKPOINT_JASPER_BIN=/usr/bin/python3", self.launcher, "-c",
             "import os; assert os.statvfs('/home/eecs/yf328').f_flag & os.ST_RDONLY; "
             "print('sandbox retained')"],
            env=self.env, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sandbox retained", result.stdout)


if __name__ == "__main__":
    unittest.main()
