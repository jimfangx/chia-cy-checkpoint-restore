#!/usr/bin/env python3
"""Chia/Codex implementation loop for FireSim checkpoint and restore.

Run via run.sh so Chipyard, FireSim and Chia share the right environment.
Agent and verification are separate Chia nodes. Large process output is
streamed, never returned through Ray's object store.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import ray

from chia.base.ChiaFunction import ChiaFunction, get
from milestones import MILESTONES, Milestone


ROOT = Path(__file__).resolve().parents[2]
FIRE = ROOT / "sims" / "firesim"
HERE = Path(__file__).resolve().parent
SCHEMA = HERE / "report.schema.json"
DEFAULT_RUNS = HERE / "runs"
VCS = Path("/ecad/tools/synopsys/vcs/W-2024.09-1/bin/vcs")
JASPER = Path("/ecad/tools/cadence/JASPER/jasper_2025.03/bin/jg")
LOG_BYTES = 16 * 1024 * 1024
LOG_BACKUPS = 6


class BoundedLog:
    """Rotate only diagnostic logs; rotation never changes task outcomes."""

    def __init__(self, path: Path, max_bytes: int = LOG_BYTES, backups: int = LOG_BACKUPS):
        self.path = path
        self.max_bytes = max_bytes
        self.backups = backups
        self.enabled = True
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = path.open("ab")

    def _rotate(self) -> None:
        self.file.close()
        oldest = self.path.with_name(f"{self.path.name}.{self.backups}")
        oldest.unlink(missing_ok=True)
        for index in range(self.backups - 1, 0, -1):
            source = self.path.with_name(f"{self.path.name}.{index}")
            if source.exists():
                source.replace(self.path.with_name(f"{self.path.name}.{index + 1}"))
        if self.path.exists():
            self.path.replace(self.path.with_name(f"{self.path.name}.1"))
        self.file = self.path.open("ab")

    def write(self, message: str) -> None:
        if not self.enabled:
            return
        data = message.encode("utf-8", errors="replace")
        try:
            while data:
                room = self.max_bytes - self.file.tell()
                if room <= 0:
                    self._rotate()
                    room = self.max_bytes
                self.file.write(data[:room])
                self.file.flush()
                data = data[room:]
        except OSError as exc:
            self.enabled = False
            sys.stderr.write(f"[log warning] diagnostic log unavailable: {exc}\n")

    def show(self, message: str) -> None:
        self.write(message)
        try:
            sys.stdout.write(message)
            sys.stdout.flush()
        except BrokenPipeError:
            pass

    def close(self) -> None:
        self.file.close()


def render_codex_event(line: str) -> str:
    """Show messages, tool calls/results and errors from Codex JSONL."""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return f"[codex stderr] {line.rstrip()}\n"
    kind = event.get("type", "unknown")
    item = event.get("item") or {}
    if kind == "item.started" and item.get("type") == "command_execution":
        return f"[tool call] {item.get('command', '')}\n"
    if kind == "item.completed":
        item_kind = item.get("type")
        if item_kind == "command_execution":
            return (f"[tool result] exit={item.get('exit_code')} "
                    f"command={item.get('command', '')}\n"
                    f"{item.get('aggregated_output', item.get('output', ''))}\n")
        if item_kind == "agent_message":
            return f"[agent response] {item.get('text', '')}\n"
        if item_kind == "reasoning":
            return f"[agent message] {item.get('text', '')}\n"
        if item_kind in {"file_change", "mcp_tool_call", "web_search"}:
            return f"[tool result] {json.dumps(item, ensure_ascii=False)}\n"
    if kind == "thread.started":
        return f"[codex session] {event.get('thread_id', '')}\n"
    if kind == "turn.completed":
        return f"[codex usage] {json.dumps(event.get('usage', {}), sort_keys=True)}\n"
    if kind in {"turn.failed", "error"}:
        return f"[codex error] {json.dumps(event, ensure_ascii=False)}\n"
    return ""


@ChiaFunction(resources={"codex_creds": 0.01})
def codex_iteration(prompt: str, schema: str, report_path: str, log_path: str,
                    model: str | None, sandbox: str) -> dict[str, Any]:
    """Run one Codex turn, streaming events without collecting its stdout."""
    log = BoundedLog(Path(log_path))
    command = [
        "codex", "-a", "never", "exec", "--json", "--ephemeral",
        "--ignore-user-config",
        "--sandbox", sandbox, "--color", "never", "-C", str(ROOT),
        "--output-schema", schema, "--output-last-message", report_path,
    ]
    if model:
        command.extend(["--model", model])
    command.append("-")
    log.show(f"[agent prompt]\n{prompt}\n")
    log.show(f"[agent command] {' '.join(command[:-1])} -\n")
    try:
        with subprocess.Popen(
            command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", bufsize=1,
        ) as process:
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(prompt)
            process.stdin.close()
            for line in process.stdout:
                # The raw stream is retained only in rotating diagnostics.
                log.write(f"[codex jsonl] {line}")
                rendered = render_codex_event(line)
                if rendered:
                    log.show(rendered)
            returncode = process.wait()
        log.show(f"[agent exit] {returncode}\n")
        report_file = Path(report_path)
        if returncode != 0 or not report_file.is_file():
            return {"error": f"Codex exited {returncode}; see {log_path}"}
        report = json.loads(report_file.read_text(encoding="utf-8"))
        report_file.unlink(missing_ok=True)
        return {"report": report}
    except (OSError, json.JSONDecodeError) as exc:
        log.show(f"[agent error] {type(exc).__name__}: {exc}\n")
        return {"error": f"{type(exc).__name__}: {exc}"}
    finally:
        log.close()


def checked_workdir(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_dir():
        raise ValueError(f"verification cwd is outside workspace or absent: {relative}")
    return path


@ChiaFunction(resources={"verification": 1.0})
def verify(commands: list[dict[str, Any]], log_path: str) -> list[dict[str, Any]]:
    """Execute checks in a separate Chia node and stream full tool logs."""
    log = BoundedLog(Path(log_path))
    results = []
    try:
        for check in commands:
            argv = check["argv"]
            if not argv or not all(isinstance(arg, str) for arg in argv):
                raise ValueError("verification argv must be a nonempty string list")
            cwd = checked_workdir(check["cwd"])
            log.show(f"[verification] {check['purpose']}\n")
            log.show(f"[verification command] cwd={cwd} argv={json.dumps(argv)}\n")
            try:
                with subprocess.Popen(
                    argv, cwd=cwd, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                    errors="replace", bufsize=1,
                ) as process:
                    assert process.stdout is not None
                    for line in process.stdout:
                        log.show(f"[verification log] {line}")
                    returncode = process.wait()
            except OSError as exc:
                returncode = 127
                log.show(f"[verification error] {exc}\n")
            log.show(f"[verification result] exit={returncode}\n")
            results.append({"purpose": check["purpose"], "argv": argv,
                            "cwd": check["cwd"], "returncode": returncode})
            if returncode:
                break
        return results
    finally:
        log.close()


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=check)


def dirty_paths(repo: Path) -> set[str]:
    """Parse NUL porcelain, including rename/copy's second path."""
    fields = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.split(b"\0")
    paths: set[str] = set()
    index = 0
    while index < len(fields) and fields[index]:
        entry = fields[index].decode("utf-8", errors="surrogateescape")
        status, path = entry[:2], entry[3:]
        paths.add(path)
        if "R" in status or "C" in status:
            index += 1
            if index < len(fields) and fields[index]:
                paths.add(fields[index].decode("utf-8", errors="surrogateescape"))
        index += 1
    return paths


def file_fingerprint(path: Path) -> str:
    if path.is_symlink():
        return "link:" + os.readlink(path)
    if not path.is_file():
        return "absent"
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def initial_baseline() -> dict[str, dict[str, str]]:
    baseline = {}
    for name, repo in (("chipyard", ROOT), ("firesim", FIRE)):
        if git(repo, "diff", "--cached", "--quiet", check=False).returncode:
            raise RuntimeError(f"{name} has staged changes; cannot safely checkpoint")
        baseline[name] = {path: file_fingerprint(repo / path)
                          for path in sorted(dirty_paths(repo))}
    return baseline


def check_baseline(baseline: dict[str, dict[str, str]]) -> None:
    for name, repo in (("chipyard", ROOT), ("firesim", FIRE)):
        changed = [path for path, original in baseline[name].items()
                   if file_fingerprint(repo / path) != original]
        if changed:
            raise RuntimeError(f"pre-existing {name} changes were modified: {changed}")


def stage_owned(repo: Path, baseline: dict[str, str]) -> list[str]:
    paths = sorted(dirty_paths(repo) - set(baseline))
    for start in range(0, len(paths), 128):
        git(repo, "add", "-A", "--", *paths[start:start + 128])
    staged = set(git(repo, "diff", "--cached", "--name-only", "-z").stdout
                 .decode("utf-8", errors="surrogateescape").strip("\0").split("\0"))
    staged.discard("")
    forbidden = staged & set(baseline)
    if forbidden:
        raise RuntimeError(f"refusing to commit pre-existing changes: {sorted(forbidden)}")
    return paths


def checkpoint_both(iteration: int, milestone: str, outcome: str,
                    baseline: dict[str, dict[str, str]]) -> dict[str, str]:
    """Create paired FireSim then Chipyard git checkpoints on every turn."""
    check_baseline(baseline)
    commits = {}
    for name, repo in (("firesim", FIRE), ("chipyard", ROOT)):
        owned = stage_owned(repo, baseline[name])
        message = f"checkpoint({milestone}): iteration {iteration} {outcome}"
        git(repo, "commit", "--allow-empty", "-m", message,
            "-m", f"Chia Codex loop checkpoint. Owned paths: {', '.join(owned) or '(none)'}")
        commits[name] = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        print(f"[git checkpoint] {name} {commits[name]} ({len(owned)} owned paths)", flush=True)
    return commits


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def make_prompt(milestone: Milestone, iteration: int, state: dict[str, Any],
                verification_log: Path) -> str:
    return f"""Implement the current milestone of the FireSim checkpoint/restore plan.

Read {ROOT / 'plan_agent.md'} and {ROOT / 'plan_human.md'} before editing.
Chipyard repo: {ROOT}
FireSim repo: {FIRE}
Chia loop: {HERE}
Current milestone: {milestone.name}
Task: {milestone.task}
Acceptance: {milestone.acceptance}
Iteration: {iteration}
Previous feedback: {state.get('feedback', '(none)')}
Full previous verification log: {verification_log}

Use VCS metasim and ordinary clean RTL VCS on this machine. Source
{ROOT / 'env.sh'} and {FIRE / 'env.sh'} when a build needs them. VCS is {VCS};
Jasper is {JASPER}. There is no FPGA. Keep FPGA capture/transport code
synthesizable and test it through metasim, but do not claim FPGA validation.

Preserve target-cycle semantics and fail explicitly on unsupported state.
Keep Level-1 simulator and Level-2 semantic checkpoints independent. Do not
substitute RTL switching activity for ASIC gate-level activity. Read the two
papers at the repository root when relevant. Work on a focused, testable
increment. Do not skip tests, edit the existing dirty conda files or the
untracked plan/PDF files, commit, reset, or clean git history. The Chia loop
handles git checkpoints. Update a concise progress document under
docs/checkpointing/ so the next Codex turn can recover context.

Return the required JSON report. Set status to ready only when the milestone's
acceptance is supported by real artifacts and verification commands. Include
commands as argv arrays (use bash -lc when environment sourcing is needed),
with cwd relative to the Chipyard root. Never report a test as passing unless
it actually ran. If an external tool, netlist, license, or library is missing,
report blocked with the exact missing dependency. Otherwise report in_progress
and continue next turn. Include full paths to all created artifacts.
"""


def validated_artifacts(report: dict[str, Any], milestone: Milestone) -> list[str]:
    errors = []
    for name in (*milestone.required_files, *report.get("artifacts", [])):
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty artifact: {name}")
    return errors


def verification_plan(report: dict[str, Any], milestone: Milestone) -> list[dict[str, Any]]:
    commands = [
        {"purpose": "FireSim whitespace check", "cwd": "sims/firesim",
         "argv": ["git", "diff", "--check"]},
        {"purpose": "Chipyard whitespace check", "cwd": ".",
         "argv": ["git", "diff", "--check"]},
    ]
    commands.extend(report.get("verification_commands", []))
    if report.get("status") == "ready" and not report.get("verification_commands"):
        raise ValueError("ready report requires independent verification commands")
    if report.get("status") == "ready" and milestone.needs_vcs:
        command_text = json.dumps(report.get("verification_commands", [])).lower()
        if "vcs" not in command_text and "simv" not in command_text:
            raise ValueError("ready report for this milestone requires a VCS command")
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--model", default=None, help="Codex model; default uses CLI config")
    parser.add_argument("--sandbox", choices=["workspace-write", "danger-full-access"],
                        default="danger-full-access")
    parser.add_argument("--max-iterations", type=int, default=0,
                        help="Optional operational stop for a trial run; 0 runs until done")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    runs = args.runs.resolve()
    if not VCS.is_file() or not JASPER.is_file() or not shutil.which("codex"):
        raise RuntimeError("VCS, Jasper, or Codex executable is missing")
    if args.dry_run:
        print(f"Chipyard: {ROOT}\nFireSim: {FIRE}\nChia: {ray.__version__}")
        print(f"VCS: {VCS}\nJasper: {JASPER}\nCodex: {shutil.which('codex')}")
        for item in MILESTONES:
            print(f"{item.name}: {item.acceptance}")
        print("M10 FPGA validation: deferred because this machine has no FPGA")
        return 0

    state_path = runs / "state.json"
    runs.mkdir(parents=True, exist_ok=True)
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        check_baseline(state["baseline"])
    else:
        state = {"milestone_index": 0, "iteration": 0, "feedback": "",
                 "baseline": initial_baseline(), "commits": {}}
        save_state(state_path, state)

    # Ray's own logs also rotate. Its temporary files are removed after shutdown.
    os.environ.setdefault("RAY_ROTATION_MAX_BYTES", str(LOG_BYTES))
    os.environ.setdefault("RAY_ROTATION_BACKUP_COUNT", str(LOG_BACKUPS))
    ray_dir = Path(tempfile.mkdtemp(prefix="chia-checkpoint-ray-", dir="/tmp"))
    ray.init(num_cpus=2, resources={"codex_creds": 1.0, "verification": 1.0},
             _temp_dir=str(ray_dir), log_to_driver=True, include_dashboard=False)
    try:
        while state["milestone_index"] < len(MILESTONES):
            if args.max_iterations and state["iteration"] >= args.max_iterations:
                print(f"[loop] stopped after {args.max_iterations} iterations; resumable at {state_path}")
                return 3
            milestone = MILESTONES[state["milestone_index"]]
            state["iteration"] += 1
            iteration = state["iteration"]
            log_path = runs / "loop.log"
            prior_verification = runs / "verification.log"
            report_path = runs / "last-message.json"
            prompt = make_prompt(milestone, iteration, state, prior_verification)
            print(f"[loop] iteration={iteration} milestone={milestone.name}", flush=True)
            agent_result = get(codex_iteration.chia_remote(
                prompt, str(SCHEMA), str(report_path), str(log_path),
                args.model, args.sandbox))
            report = agent_result.get("report", {})
            feedback = agent_result.get("error", "")
            if report and report.get("milestone") != milestone.name:
                feedback = f"wrong milestone in report: {report.get('milestone')}"
            results: list[dict[str, Any]] = []
            if not feedback:
                try:
                    commands = verification_plan(report, milestone)
                    results = get(verify.chia_remote(commands, str(prior_verification)))
                    failed = [result for result in results if result["returncode"]]
                    errors = validated_artifacts(report, milestone)
                    if failed:
                        errors.append(f"verification failed: {failed[-1]['purpose']}")
                    feedback = "; ".join(errors)
                except (KeyError, TypeError, ValueError) as exc:
                    feedback = f"invalid report or verification: {exc}"
            try:
                state["commits"] = checkpoint_both(
                    iteration, milestone.name,
                    "verified" if not feedback and report.get("status") == "ready" else "wip",
                    state["baseline"])
            except (RuntimeError, subprocess.CalledProcessError) as exc:
                state["feedback"] = f"git checkpoint failed: {exc}"
                save_state(state_path, state)
                raise
            state["last_report"] = report
            state["last_verification"] = results
            state["feedback"] = feedback or report.get("summary", "")
            if not feedback and report.get("status") == "ready":
                print(f"[milestone verified] {milestone.name}", flush=True)
                state["milestone_index"] += 1
                state["feedback"] = ""
            elif report.get("status") == "blocked":
                print(f"[milestone blocked] {milestone.name}: {report.get('evidence')}", flush=True)
                save_state(state_path, state)
                return 2
            else:
                print(f"[loop feedback] {state['feedback']}", flush=True)
            save_state(state_path, state)
        print("[loop complete] all metasim, clean RTL, and gate-level milestones verified")
        print("[deferred] FPGA bring-up requires hardware")
        return 0
    finally:
        ray.shutdown()
        shutil.rmtree(ray_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
