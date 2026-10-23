#!/usr/bin/env python3
"""Chia/Codex implementation loop for FireSim checkpoint and restore.

Run via run.sh so Chipyard, FireSim and Chia share the right environment.
Agent and verification are separate Chia nodes. Large process output is
streamed, never returned through Ray's object store.
"""

from __future__ import annotations

import argparse
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
from eda import EdaConfig, RemoteWorkspace
from f2 import F2Manager
from milestones import LEGACY_MILESTONE_ORDER, MILESTONES, Milestone


ROOT = Path(__file__).resolve().parents[2]
FIRE = ROOT / "sims" / "firesim"
HERE = Path(__file__).resolve().parent
SCHEMA = HERE / "report.schema.json"
DEFAULT_RUNS = HERE / "runs"
LOG_BYTES = 16 * 1024 * 1024
LOG_BACKUPS = 6
STREAM_CHUNK_CHARS = 64 * 1024
MAX_PARSED_EVENT_CHARS = 4 * 1024 * 1024
READ_ONLY_PLANS = ("plan_agent.md", "plan_human.md")


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


def bounded_json_lines(stream):
    """Read JSONL without keeping an arbitrarily large tool result in RAM.

    Oversize events are still streamed verbatim to the diagnostic log and
    console. The structured final answer comes from --output-last-message.
    """
    pending = ""
    oversized = False
    while True:
        piece = stream.readline(STREAM_CHUNK_CHARS)
        if not piece:
            break
        if oversized:
            yield piece, False
            if piece.endswith("\n"):
                oversized = False
            continue
        pending += piece
        if len(pending) >= MAX_PARSED_EVENT_CHARS:
            yield pending, False
            pending = ""
            oversized = not piece.endswith("\n")
        elif pending.endswith("\n"):
            yield pending, True
            pending = ""
    if pending:
        yield pending, not oversized


@ChiaFunction(resources={"codex_creds": 0.01})
def codex_iteration(prompt: str, schema: str, report_path: str, log_path: str,
                    model: str | None, sandbox: str, effort: str = "high") -> dict[str, Any]:
    """Run one Codex turn, streaming events without collecting its stdout."""
    log = BoundedLog(Path(log_path))
    command = [
        "codex", "-a", "never", "exec", "--json", "--ephemeral",
        "--ignore-user-config",
        "-c", f'model_reasoning_effort="{effort}"',
        "--color", "never", "-C", str(ROOT),
        "--output-schema", schema, "--output-last-message", report_path,
    ]
    if sandbox == "workspace-write":
        # The agent needs SSH to EDA for exploratory VCS checks.
        command.extend([
            "-c", 'default_permissions="checkpoint"',
            "-c", 'permissions.checkpoint.extends=":workspace"',
            "-c", "permissions.checkpoint.network.enabled=true",
        ])
    else:
        command.extend(["--sandbox", sandbox])
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
            for line, parseable in bounded_json_lines(process.stdout):
                # The raw stream is retained only in rotating diagnostics.
                log.write(f"[codex jsonl] {line}")
                rendered = render_codex_event(line) if parseable else f"[codex raw chunk] {line}"
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
    """Coordinate EDA verification from a separate Chia node."""
    log = BoundedLog(Path(log_path))
    try:
        return run_verification(commands, log)
    finally:
        log.close()


def run_verification(commands: list[dict[str, Any]], log: BoundedLog) -> list[dict[str, Any]]:
    results = []
    workspace = RemoteWorkspace(root=ROOT, emit=log.show)
    manager = F2Manager(root=ROOT, emit=log.show)
    for check in commands:
        checked_workdir(check["cwd"])
        execution = check.get("execution", "eda")
        if execution == "eda":
            workspace.command(check["argv"], check["cwd"])
        elif execution == "f2":
            manager.command(check["argv"], check["cwd"])
        elif execution != "local" or check["argv"] != ["git", "diff", "--check"]:
            raise ValueError("invalid verification backend; only controller whitespace checks run locally")
    with workspace.locked():
        eda_current = False
        for check in commands:
            argv = check["argv"]
            cwd = checked_workdir(check["cwd"])
            execution = check.get("execution", "eda")
            log.show(f"[verification] {check['purpose']}\n")
            log.show(f"[verification command] backend={execution} cwd={cwd} argv={json.dumps(argv)}\n")
            fetch_error = None
            try:
                if execution == "eda":
                    if not eda_current:
                        workspace.preflight()
                        workspace.push()
                        eda_current = True
                    try:
                        returncode = workspace.run(argv, check["cwd"])
                    finally:
                        # Each EDA result must arrive before a subsequent F2
                        # check; a later FPGA capture must be synced back to EDA.
                        try:
                            workspace.fetch()
                        except (OSError, RuntimeError) as exc:
                            fetch_error = str(exc)
                elif execution == "f2":
                    returncode = manager.run(argv, check["cwd"])
                    eda_current = False
                else:
                    returncode = run_local_check(argv, cwd, log)
            except (OSError, RuntimeError) as exc:
                returncode = 127
                log.show(f"[verification error] {exc}\n")
            log.show(f"[verification result] backend={execution} exit={returncode}\n")
            results.append({"purpose": check["purpose"], "argv": argv,
                            "cwd": check["cwd"], "returncode": returncode,
                            "backend": execution,
                            "host": workspace.config.host if execution == "eda" else "local-manager"})
            if execution == "eda":
                results[-1]["remote_argv"] = workspace.mapped_argv(argv)
                results[-1]["remote_cwd"] = workspace.config.root + "/" + check["cwd"]
            if fetch_error:
                log.show(f"[verification artifact error] {fetch_error}\n")
                results.append({"purpose": "Return EDA verification artifacts", "argv": [],
                                "cwd": ".", "returncode": 127, "backend": "eda",
                                "host": workspace.config.host})
            if returncode or fetch_error:
                break
    return results


def run_local_check(argv: list[str], cwd: Path, log: BoundedLog) -> int:
    with subprocess.Popen(
        argv, cwd=cwd, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        errors="replace", bufsize=1,
    ) as process:
        assert process.stdout is not None
        for line in iter(lambda: process.stdout.readline(STREAM_CHUNK_CHARS), ""):
            log.show(f"[verification log] {line}")
        return process.wait()


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


def initial_baseline() -> dict[str, list[str]]:
    baseline = {}
    for name, repo in (("chipyard", ROOT), ("firesim", FIRE)):
        if git(repo, "diff", "--cached", "--quiet", check=False).returncode:
            raise RuntimeError(f"{name} has staged changes; cannot safely checkpoint")
        baseline[name] = sorted(dirty_paths(repo))
    return baseline


def stage_owned(repo: Path, baseline: list[str]) -> list[str]:
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
                    baseline: dict[str, list[str]]) -> dict[str, str]:
    """Create paired FireSim then Chipyard git checkpoints on every turn."""
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


def load_state(path: Path) -> dict[str, Any]:
    """Load progress and commit exclusions, migrating old fingerprint maps."""
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    else:
        state = {"milestone_index": 0, "iteration": 0, "feedback": "",
                 "baseline": initial_baseline(), "commits": {}}
    # Map completed milestone names instead of reusing positional indices after
    # removing historical work. Preserve the iteration, feedback and commits.
    order = [milestone.name for milestone in MILESTONES]
    previous_order = state.get("milestone_order", LEGACY_MILESTONE_ORDER)
    index = state["milestone_index"]
    if (not isinstance(previous_order, (list, tuple)) or
            any(not isinstance(name, str) for name in previous_order) or
            len(set(previous_order)) != len(previous_order) or
            type(index) is not int or not 0 <= index <= len(previous_order)):
        raise ValueError("invalid saved milestone order or index")
    historical_completed = state.get("completed_milestones", [])
    if not isinstance(historical_completed, list) or any(not isinstance(n, str) for n in historical_completed):
        raise ValueError("invalid saved completed milestones")
    completed = set(previous_order[:index]) | set(historical_completed)
    state["milestone_index"] = next(
        (i for i, name in enumerate(order) if name not in completed), len(order))
    state["milestone_order"] = order
    state["completed_milestones"] = sorted(completed)
    # Old runs stored path -> fingerprint maps. Keep only the excluded paths;
    # their contents can change freely without blocking resume or checkpoints.
    for name, paths in state["baseline"].items():
        excluded = set(paths)
        if name == "chipyard":
            excluded.update(READ_ONLY_PLANS)
        state["baseline"][name] = sorted(excluded)
    save_state(path, state)
    return state


def make_prompt(milestone: Milestone, iteration: int, state: dict[str, Any],
                verification_log: Path) -> str:
    eda = EdaConfig.from_env()
    return f"""Implement the current milestone of the FireSim checkpoint/restore plan.

Read the sections of {ROOT / 'plan_agent.md'} and {ROOT / 'plan_human.md'}
relevant to this milestone before editing. Re-read the top of plan_agent.md
on every iteration and apply its current user priorities. plan_agent.md takes
precedence over older instructions in plan_human.md and historical progress.
Capture checkpoints from an actual running AWS F2 FPGA. Migrate that hardware
state into fresh EDA VCS metasim and clean pre-FAME RTL, including sustained
restored-metasim-guided RTL execution. FPGA implementation, image builds and
physical hardware acceptance are required now. ASIC synthesis, formal RTL-to-cell
mapping, gate replay and power analysis remain outside scope.

You are the central implementation agent for this Chia-managed Codex turn.
The user explicitly authorizes as many subagents as needed, within the runtime's
available capacity; there is no additional task-specific subagent limit.
All LLM requests, delegation/follow-up requests and results must go through you.
Use native managed subagent tools under this central turn. Only you initiate
and coordinate delegation; workers request additional help through you and
return their results to you. Do not start independent codex exec sessions,
direct LLM API calls, separate Chia LLM jobs or detached model processes.
Keep the central turn alive until every delegated LLM request has finished.
Collect and integrate worker results, resolve conflicts, and wait for or cancel
and join any remaining workers before returning. Only you return the final
required JSON report; workers must not write controller state or final-report
files. No subagent or background LLM request may outlive your final response.
Chia relies on completion of this central invocation to know that the LLM call
is finished. Pass this coordination rule and the task constraints to each worker.

The old loop is archived at {ROOT / 'automations/checkpoint_loop_legacy_asic'};
treat that archive and its plans as read-only historical inputs.
Read {ROOT / 'docs/checkpointing/progress.md'}.
Read and follow {ROOT / 'docs/checkpointing/github-publication.md'}.
You may push existing loop checkpoint commits to the configured GitHub forks;
the loop controller remains responsible for staging and creating local commits.
Use targeted rg/sed reads so large plans do not flood the tool log.
Treat plan_agent.md and plan_human.md as read-only inputs. Never edit, rewrite,
rename, delete, or stage either plan, whether tracked, untracked, clean, or dirty.
Record progress and proposed plan corrections only under docs/checkpointing/.
Chipyard repo: {ROOT}
FireSim repo: {FIRE}
Chia loop: {HERE}
Current milestone: {milestone.name}
Task: {milestone.task}
Acceptance: {milestone.acceptance}
Iteration: {iteration}
Previous feedback: {state.get('feedback', '(none)')}
Full previous verification log: {verification_log}

All VCS compilation, simulation, metasimulation and VCS verification MUST run
on SSH host {eda.host}, in the dedicated mirror {eda.root}. Codex, source edits
and git checkpoints stay here. For exploratory checks use this local helper:
python {HERE / 'eda.py'} --cwd . -- bash -lc 'source automations/checkpoint_loop/vcs-env.sh && <check>'
The helper syncs source (including git metadata and dirty files) and run inputs,
uses the EDA login-shell licenses, and returns run artifacts even on failure.
It never copies local env.sh or conda environments over EDA's native setup.
Report backend="eda" for ALL VCS checks (also the default for older reports).
Report backend="f2" for AWS/FireSim manager, FPGA deployment, workload execution,
capture and manager-side audits. Both backends take raw command argv, not helper
or SSH wrappers. cwd is relative to Chipyard. Local absolute workspace paths in
EDA argv are mapped to the remote root. The controller executes commands in
reported order and exchanges artifacts between the F2 manager and EDA.
Use workspace-relative paths in scripts and put ALL generated evidence beneath
automations/checkpoint_loop/runs/ so it is returned here before artifact checks.
Report artifacts as local paths under {ROOT}; preserve original remote paths
inside receipts. Do not rewrite historical evidence to appear freshly verified.
Remote VCS is {eda.vcs}; use -full64. Source vcs-env.sh LAST after any native
EDA build setup, including inside nested bash -lc commands. If license variables
are empty it sources /tools/flexlm/flexlm.sh, the same setup used by EDA .zshrc;
noninteractive bash does not load .zshrc. CHECKPOINT_EDA_LICENSE_SETUP in the
remote setup can select another license script. Preserve inherited license
settings; do not source the former /ecad license setup. If necessary,
CHECKPOINT_EDA_SETUP names an additional REMOTE build environment script.
Old verification harnesses may pin SP1, /ecad, or Ubuntu compiler paths. Port
active build/runtime checks to the real SP2 toolchain, preserving exact
provenance and validation; never falsify old receipts or weaken acceptance.
Regenerate host-specific cached builds and binaries; use VCS_FLAGS=-Mupdate
when regenerating VCS cached Makefiles. Missing remote build dependencies must
be reported with their actual failing commands, not inferred from local tools.

Use this checkout as the local AWS FireSim manager; read
{ROOT / 'docs/checkpointing/aws-f2-workflow.md'} and the linked official guide.
For exploratory manager/hardware work:
python {HERE / 'f2.py'} check
python {HERE / 'f2.py'} run --cwd sims/firesim/deploy -- firesim <task> <isolated config flags>
f2.py sources sourceme-manager.sh with noninteractive key setup skipped; Fabric
uses ~/firesim.pem. CHECKPOINT_F2_SETUP can source additional local manager setup.
The user has already generated the four manager YAMLs in {FIRE / 'deploy'}
and run aws configure. Reuse that setup; do not rerun managerinit, aws configure
or account bootstrap. Generate invocation overrides with f2.py prepare from
those existing files: one AWS f2.6xlarge run host, a dedicated checkpoint-f2-*
tag, metasimulation_enabled=false and the exact CPU recipe (add its existing
staging recipe if absent from the user's build recipes). Preserve custom inputs.
Vivado synthesis/place-and-route and bitstream builds MUST run on THIS server,
not EDA or an EC2 build farm. Use build-farm-recipes/externally_provisioned.yaml
with build_farm_hosts=[localhost] and a local build directory. The helper enforces
this in generated configs. Reuse native Vivado and check the required F2 HDK
version and FireSim's localhost SSH access when building. Do not launch z1d
build instances. AWS is used for F2 runtime and AFI services. Existing AWS
configuration is established setup; report concrete API errors if encountered.
Do not clone/reset this implementation.
Public AGFIs are baseline-only. Implement actual synthesizable freeze/banked
state access and MMIO/DMA/host capture, build a checkpoint-enabled F2 image,
deploy it, then checkpoint active FPGA execution. Metasim capture, VCS backdoors,
or public-image boot cannot satisfy new hardware checkpoints. FPGA synthesis
with Vivado is allowed and required when hardware changes. Persist driver/image
source hashes, instance ID/type/region, loaded slot/AGFI, target cycles, DMA and
host receipts, workload and checkpoint hashes, complete state and comparison logs.
The FireSim manager returns run-farm results locally; configure workload outputs
to collect checkpoint/trace files and copy acceptance evidence into runs/ before
EDA verification. Retain native manager logs and AFI build outputs with provenance.
Use only this loop's tagged AWS run farm; record instance/AFI IDs and local build
jobs/work directories. Collect artifacts before scoped run-farm teardown. The
localhost build host and this manager must never be terminated. Preserve native
build results and in-progress AFI IDs across turns. Local build worktrees are
excluded from EDA sync; copy only required capture/restore inputs outside them.
If AWS access, quota, AMI, networking, SSH keys or account setup blocks hardware,
report the actual dependency; never substitute metasim for F2 acceptance.

Preserve target-cycle semantics and fail explicitly on unsupported state.
Keep Level-1 simulator and Level-2 semantic checkpoints independent. Validate
both independent finite replay and live clean-RTL shadowing driven by restored
metasim; a CPU recipe needs both modes before it is verified. Read the debugging
papers at the repository root when relevant. Work on a focused, testable
increment. Do not skip tests, edit the existing dirty conda files or the
untracked plan/PDF files, commit, reset, or clean git history. The Chia loop
handles git checkpoints. Update a concise progress document under
docs/checkpointing/ so the next Codex turn can recover context.
Put diagnostic logs in {HERE / 'runs'}, not in tracked documentation. Do not
reduce the test scope or skip a check to save memory or disk.

Return the required JSON report. Set status to ready only when the milestone's
acceptance is supported by real artifacts and verification commands. Include
commands as raw argv arrays with backend f2 or eda (use bash -c for manager scripts,
and bash -lc with vcs-env.sh sourced last for EDA scripts),
with cwd relative to the Chipyard root. Never report a test as passing unless
it actually ran. Diagnose failed checks from the underlying compiler/runtime log,
not just the wrapper exception. Attempt routine dependency recovery on the
appropriate host using available permissions before reporting blocked: inspect
compiler paths and linker scripts, repair missing matching runtime/development
packages when permitted, or use a compatible private installation. Missing GMP
headers or sanitizer libraries are repairable setup issues when access exists.
Keep ASan/UBSan and the full regression scope enabled; do not hide failures by
changing ABI, copying incompatible runtime libraries, or omitting checks.
Report blocked only when a concrete external dependency cannot be resolved
with available access (such as missing privileges, credentials, quota, network
or license access), recording attempted repairs and the actual error. If useful
implementation or recovery work remains possible, report in_progress and
continue next turn. Include full paths to individual nonempty artifact files,
not directories; the controller validates each reported path as a file.
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
         "argv": ["git", "diff", "--check"], "execution": "local"},
        {"purpose": "Chipyard whitespace check", "cwd": ".",
         "argv": ["git", "diff", "--check"], "execution": "local"},
    ]
    for check in report.get("verification_commands", []):
        backend = check.get("backend", "eda")
        if backend not in ("eda", "f2"):
            raise ValueError("verification backend must be eda or f2")
        commands.append({**check, "execution": backend})
    if report.get("status") == "ready" and not report.get("verification_commands"):
        raise ValueError("ready report requires independent verification commands")
    if report.get("status") == "ready" and milestone.needs_vcs:
        command_text = json.dumps([check["argv"] for check in commands
                                   if check.get("execution") == "eda"]).lower()
        if "vcs" not in command_text and "simv" not in command_text:
            raise ValueError("ready report for this milestone requires an EDA VCS command")
    if report.get("status") == "ready" and milestone.needs_f2:
        if not any(check.get("execution") == "f2" for check in commands):
            raise ValueError("ready report for this milestone requires AWS F2 verification")
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--model", default="gpt-6.1-sol",
                        help="Codex model (default: gpt-6.1-sol)")
    parser.add_argument("--effort", default="high",
                        choices=["low", "medium", "high", "xhigh"],
                        help="Codex reasoning effort (default: high)")
    parser.add_argument("--sandbox", choices=["workspace-write", "read-only"],
                        default="workspace-write",
                        help="Codex sandbox (default: workspace-write); approvals are never prompted")
    parser.add_argument("--max-iterations", type=int, default=0,
                        help="Optional operational stop for a trial run; 0 runs until done")
    parser.add_argument("--dry-run", action="store_true", help="print routing/milestones without network or state changes")
    parser.add_argument("--check-backends", action="store_true",
                        help="check AWS F2 manager and EDA access without launching resources")
    args = parser.parse_args()
    runs = args.runs.resolve()
    if not shutil.which("codex"):
        raise RuntimeError("local Codex executable is missing")
    try:
        workspace = RemoteWorkspace()
        if args.check_backends:
            if F2Manager().preflight():
                return 2
            workspace.preflight()
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[loop startup error] {exc}", file=sys.stderr)
        return 2
    if args.dry_run or args.check_backends:
        print(f"Chipyard: {ROOT}\nFireSim: {FIRE}\nChia: {ray.__version__}")
        print(f"EDA: {workspace.config.host}:{workspace.config.root}")
        print(f"Remote VCS: {workspace.config.vcs}\nCodex: {shutil.which('codex')}")
        for item in MILESTONES:
            print(f"{item.name}: {item.acceptance}")
        print("Capture: actual AWS F2 FPGA; restore/replay: EDA VCS; FPGA acceptance is required")
        return 0

    state_path = runs / "state.json"
    runs.mkdir(parents=True, exist_ok=True)
    state = load_state(state_path)

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
                args.model, args.sandbox, args.effort))
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
                completed = set(state.get("completed_milestones", [])) | {milestone.name}
                state["completed_milestones"] = sorted(completed)
                state["milestone_index"] = next(
                    (i for i, item in enumerate(MILESTONES) if item.name not in completed), len(MILESTONES))
                state["feedback"] = ""
            elif report.get("status") == "blocked":
                print(f"[milestone blocked] {milestone.name}: {report.get('evidence')}", flush=True)
                save_state(state_path, state)
                return 2
            else:
                print(f"[loop feedback] {state['feedback']}", flush=True)
            save_state(state_path, state)
        print("[loop complete] all configured milestones verified")
        print("[scope complete] AWS F2 capture and FPGA-to-EDA checkpoint migration verified")
        return 0
    finally:
        ray.shutdown()
        shutil.rmtree(ray_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
