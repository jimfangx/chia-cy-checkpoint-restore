#!/usr/bin/env python3
"""Sync a dedicated EDA workspace, execute checks over SSH, return run artifacts.

This module deliberately has no Chia/Ray dependencies, so the implementation
agent can use it for exploratory checks as well as independent verification.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
RUNS = "automations/checkpoint_loop/runs"
DEFAULT_VCS = "/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs"
SSH_OPTIONS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]
# Never overwrite destination environments or copy local credentials. Preserve
# remote compiler caches/builds; source deletions still propagate via --delete.
SOURCE_EXCLUDES = (
    ".aws/", ".codex/", ".agents/", ".ssh/", ".conda-env/", ".conda-lock-env/",
    ".bloop/", ".sbt/", ".ivy2/", "__pycache__/", "target/", ".Xil/",
    "/env.sh", "/sims/firesim/env.sh",
    "/sims/firesim/deploy/results-build/", "/sims/firesim/deploy/results-workload/",
    "/sims/firesim/deploy/logs/", "/sims/firesim/deploy/built-hwdb-entries/",
    "/sims/firesim/deploy/config_runtime.yaml", "/sims/firesim/deploy/config_build.yaml",
    "/sims/firesim/deploy/config_hwdb.yaml",
    "/automations/checkpoint_loop/runs/", ".checkpoint-eda-owner",
)
CONTROL_EXCLUDES = (
    "/state*.json", "/loop.log*", "/verification.log*", "/last-message.json",
    "/eda.lock", "/migration-source/",
    "build-host/", "/aws-f2/local-build/",
    # Vivado's live realtime scratch files disappear during native synthesis.
    # They are not build inputs or retained evidence (DCP/reports/logs remain).
    ".Xil/",
)
INPUT_EXCLUDES = tuple(pattern for pattern in CONTROL_EXCLUDES if pattern != "/migration-source/")


@dataclass(frozen=True)
class EdaConfig:
    host: str = "eda"
    root: str = "/scratch/jfx/chia-cy-checkpoint-restore"
    vcs: str = DEFAULT_VCS
    setup: str = ""

    @classmethod
    def from_env(cls) -> EdaConfig:
        config = cls(
            os.environ.get("CHECKPOINT_EDA_HOST", cls.host),
            os.environ.get("CHECKPOINT_EDA_ROOT", cls.root),
            os.environ.get("CHECKPOINT_EDA_VCS", cls.vcs),
            os.environ.get("CHECKPOINT_EDA_SETUP", ""),
        )
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@-]*", config.host):
            raise ValueError("invalid CHECKPOINT_EDA_HOST")
        for name, value in (("ROOT", config.root), ("VCS", config.vcs)):
            path = PurePosixPath(value)
            if not path.is_absolute() or ".." in path.parts or "\n" in value:
                raise ValueError(f"CHECKPOINT_EDA_{name} must be an absolute normalized path")
        if len(PurePosixPath(config.root).parts) < 4:
            raise ValueError("CHECKPOINT_EDA_ROOT must be a dedicated workspace directory")
        if config.setup and not PurePosixPath(config.setup).is_absolute():
            raise ValueError("CHECKPOINT_EDA_SETUP must name a remote absolute path")
        return config


def stream(command: list[str], emit: Callable[[str], None], **kwargs) -> int:
    emit(f"[eda command] {shlex.join(command)}\n")
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace", **kwargs) as process:
        assert process.stdout is not None
        for chunk in iter(lambda: process.stdout.readline(64 * 1024), ""):
            emit(chunk)
        return process.wait()


class RemoteWorkspace:
    def __init__(self, config: EdaConfig | None = None, root: Path = ROOT,
                 emit: Callable[[str], None] = lambda s: print(s, end="", flush=True)):
        self.config = config or EdaConfig.from_env()
        self.root = root.resolve()
        self.emit = emit

    def ssh(self, script: str) -> list[str]:
        return ["ssh", *SSH_OPTIONS, self.config.host, "bash -lc " + shlex.quote(script)]

    def checked(self, command: list[str]) -> None:
        code = stream(command, self.emit)
        if code:
            raise RuntimeError(f"EDA transport/setup failed (exit {code}): {shlex.join(command)}")

    def preflight(self) -> None:
        for binary in ("ssh", "rsync"):
            if not shutil.which(binary):
                raise RuntimeError(f"missing local executable: {binary}")
        config = self.config
        # This checks tool availability, not actual license checkout. vcs-env.sh
        # loads the site license script when noninteractive startup omits it.
        self.checked(self.ssh(
            "set -e; command -v rsync; command -v bash; "
            f"test -x {shlex.quote(config.vcs)} || "
            "{ echo 'Remote VCS executable is missing or not executable' >&2; exit 1; }; "
            f"test -d {shlex.quote(str(PurePosixPath(config.root).parent))}; "
            f"test -w {shlex.quote(str(PurePosixPath(config.root).parent))}; "
            + (f"test -r {shlex.quote(config.setup)}; " if config.setup else "")
            + f"printf '%s\\n' {shlex.quote('EDA VCS: ' + config.vcs)}"
        ))

    @contextmanager
    def locked(self):
        directory = self.root / RUNS
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "eda.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def rsync(self, excludes: tuple[str, ...], *paths: str, delete: bool = False,
              update: bool = False) -> None:
        command = ["rsync", "-a", "--protect-args", "--stats",
                   "-e", shlex.join(["ssh", *SSH_OPTIONS])]
        if delete:
            command.append("--delete")
        if update:
            command.append("--update")
        for pattern in excludes:
            command.extend(["--exclude", pattern])
        self.checked([*command, *paths])

    def push(self) -> None:
        config = self.config
        root = shlex.quote(config.root)
        # Refuse to mirror over an unrelated checkout. --delete is limited to
        # a directory claimed by this transport, never the /scratch/jfx parent.
        self.checked(self.ssh(
            f"set -e; test ! -L {root}; mkdir -p {root}; cd {root}; "
            "if test ! -f .checkpoint-eda-owner; then "
            "test -z \"$(ls -A)\" || { echo 'EDA workspace is not empty and is not owned by checkpoint_loop' >&2; exit 1; }; "
            "printf '%s\\n' checkpoint_loop > .checkpoint-eda-owner; fi"
        ))
        self.rsync(SOURCE_EXCLUDES, str(self.root) + "/",
                   f"{config.host}:{config.root}/", delete=True)
        # Native EDA adapters allow existing harnesses to source env.sh. They
        # never activate or relocate the Ubuntu conda environment. A site setup
        # can activate its native environment via CHECKPOINT_EDA_SETUP instead.
        environment = (
            "#!/usr/bin/env bash\n"
            'if [[ -n "${CHECKPOINT_EDA_SETUP:-}" ]]; then\n'
            '    source "$CHECKPOINT_EDA_SETUP" || return $?\nfi\n'
            f"export CY_DIR={shlex.quote(config.root)}\n"
        )
        fire_environment = (
            "#!/usr/bin/env bash\n"
            f"source {shlex.quote(config.root + '/env.sh')} || return $?\n"
            f"export FS_DIR={shlex.quote(config.root + '/sims/firesim')}\n"
            "export FIRESIM_ENV_SOURCED=1\n"
        )
        self.checked(self.ssh(
            f"set -e; cd {root}; "
            f"if test ! -f env.sh; then printf %s {shlex.quote(environment)} > env.sh; fi; "
            "mkdir -p sims/firesim; "
            "if test ! -f sims/firesim/env.sh; then "
            f"printf %s {shlex.quote(fire_environment)} > sims/firesim/env.sh; fi"
        ))
        self.checked(self.ssh(f"mkdir -p {shlex.quote(config.root + '/' + RUNS)}"))
        # Preserve newer remote artifacts, while sending edited local harnesses
        # and additional inputs. Returned files retain their remote timestamps.
        command = ["rsync", "-a", "--protect-args", "--update", "--stats",
                   "-e", shlex.join(["ssh", *SSH_OPTIONS])]
        for pattern in INPUT_EXCLUDES:
            command.extend(["--exclude", pattern])
        self.checked([*command, str(self.root / RUNS) + "/",
                      f"{config.host}:{config.root}/{RUNS}/"])

    def mapped_argv(self, argv: list[str]) -> list[str]:
        if not argv or not all(isinstance(arg, str) for arg in argv):
            raise ValueError("verification argv must be a nonempty string list")
        return [arg.replace(str(self.root), self.config.root) for arg in argv]

    def command(self, argv: list[str], cwd: str) -> list[str]:
        relative = PurePosixPath(cwd)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("EDA cwd must be relative to the workspace")
        config = self.config
        qroot = shlex.quote(config.root)
        script = f"set -eo pipefail; cd {qroot}; "
        script += f"export CHECKPOINT_EDA_VCS={shlex.quote(config.vcs)}; "
        script += f"export CHECKPOINT_EDA_SETUP={shlex.quote(config.setup)}; "
        # These are native EDA environments, never the copied Ubuntu env.sh.
        script += "if test -f env.sh; then source ./env.sh; fi; "
        script += "if test -f sims/firesim/env.sh; then source sims/firesim/env.sh; fi; "
        script += "source automations/checkpoint_loop/vcs-env.sh; "
        script += f"cd {shlex.quote(config.root + '/' + str(relative))}; "
        script += "exec " + shlex.join(self.mapped_argv(argv))
        return self.ssh(script)

    def run(self, argv: list[str], cwd: str = ".") -> int:
        return stream(self.command(argv, cwd), self.emit)

    def fetch(self) -> None:
        # F2/Vivado logs may keep growing here while an EDA check is running.
        # Its input snapshot must not overwrite newer manager-side evidence.
        # Remote-created and newer remote results still return, including on
        # simulation failure. Runs use unique paths; never relabel old output.
        self.rsync(CONTROL_EXCLUDES, f"{self.config.host}:{self.config.root}/{RUNS}/",
                   str(self.root / RUNS) + "/", update=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check SSH, rsync and remote VCS; do not sync")
    parser.add_argument("--cwd", default=".", help="working directory relative to Chipyard")
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    workspace = RemoteWorkspace()
    try:
        workspace.preflight()
        if args.check:
            return 0
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        if not argv:
            parser.error("a command after -- is required")
        workspace.command(argv, args.cwd)  # Validate before syncing.
        with workspace.locked():
            workspace.push()
            try:
                code = workspace.run(argv, args.cwd)
            finally:
                workspace.fetch()  # Failed simulations still return diagnostics.
            return code
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[eda error] {exc}", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
