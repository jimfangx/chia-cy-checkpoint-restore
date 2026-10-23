# FireSim checkpoint/restore Chia loop

The active loop implements the current root `plan_agent.md`: Level-1 and
Level-2 capture from actual AWS F2 FPGA execution, FPGA-to-VCS migration, finite
RTL replay and sustained live clean-RTL shadowing for Rocket, BOOM, then
Shuttle + Saturn. Physical FPGA acceptance is required. ASIC synthesis, formal state mapping, gate replay and power analysis
are outside scope. `automations/checkpoint_loop_legacy_asic/` and
`tools/checkpoint_loop/` contain historical flows; do not launch them.

Codex, the Chia controller and the AWS FireSim manager run locally. Report
`backend: f2` for manager/AWS hardware deployment, workload execution and
capture; report `backend: eda` for all VCS and EDA checks (the compatibility
default). The controller keeps command order and exchanges captured files and
results between backends before the next check. Read
[the AWS F2 workflow](../../docs/checkpointing/aws-f2-workflow.md) for setup,
image builds, evidence collection and hardware acceptance. Metasim-origin
images cannot satisfy the new F2 milestones.

From the Chipyard root:

```bash
bash automations/checkpoint_loop/run.sh --dry-run
# Optional read-only connectivity/account checks:
bash automations/checkpoint_loop/run.sh --check-backends
bash automations/checkpoint_loop/run.sh
```

The launcher sources local Chipyard/FireSim `env.sh` and imports Chia. The
sibling Chia checkout is the default; `CHIA_SOURCE` overrides it. No local VCS
installation is required. Dry-run prints routing and milestones offline and
does not sync, launch resources, start Ray/Codex or change saved state.
`--check-backends` checks the manager's AWS access and EDA SSH/VCS access
without launching instances. Otherwise backend dependencies are checked when
needed; EDA availability does not prevent initial F2 bring-up work.

The four `sims/firesim/deploy/config_*.yaml` files and AWS configuration are
already initialized. Reuse them; do not rerun managerinit or aws configure.
Vivado bitstream builds run on this server through `ExternallyProvisioned`
with `build_farm_hosts: [localhost]`; generated configs enforce this. No EC2
build host is launched. EDA remains exclusively the VCS backend. Local build
worktrees are excluded from EDA sync.

Generate isolated single-node F2 configs and manager argv with
`python automations/checkpoint_loop/f2.py prepare`; run exploratory manager
commands with `f2.py run`. `f2.py check` checks manager/AWS access alone.
`CHECKPOINT_F2_SETUP` can source additional local manager setup. The manager
sources `sourceme-manager.sh` noninteractively and uses `~/firesim.pem`.
The generator uses the existing four configs as input, preserves custom runtime
settings and selected recipes/HWDB entries, and writes isolated overrides. It
never overwrites the default manager configs. Public images are
baseline-only; new checkpoint-enabled AFIs must be built after implementing
the complete synthesized capture path. Config generation is not FPGA evidence.

Default EDA configuration:

| Variable | Default / meaning |
| --- | --- |
| `CHECKPOINT_EDA_HOST` | `eda`, using `~/.ssh/config` (`rocky@32.185.44.117`) |
| `CHECKPOINT_EDA_ROOT` | `/scratch/jfx/chia-cy-checkpoint-restore`, a dedicated mirror |
| `CHECKPOINT_EDA_VCS` | `/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs` |
| `CHECKPOINT_EDA_SETUP` | Optional absolute path to a **remote** native build setup script |

Licenses are inherited from EDA's login shell. No old `/ecad` license setup is
sourced. Local `env.sh` files, conda environments, credentials and compiler
caches are excluded from uploads. Minimal remote `env.sh` adapters are created
only if absent; they source `CHECKPOINT_EDA_SETUP` when set. Configure that
script for any native Python/conda, Java, RISC-V, libraries and other build
prerequisites. Local conda binaries cannot be assumed to run on Rocky.
An existing native remote `env.sh` is preserved.

The first sync refuses an existing nonempty directory without the helper's
`.checkpoint-eda-owner` marker. Choose another dedicated `CHECKPOINT_EDA_ROOT`
if necessary; do not point the mirror at unrelated work. Source sync includes
Git metadata and dirty/untracked files, propagates source deletions, and may be
large on the first invocation. Run inputs sync incrementally without deleting
remote evidence. Local edits to input harnesses are uploaded; newer remote
results are preserved. Local `state*.json`, loop logs, lock files and the
migration archive are never overwritten by remote artifacts.

For exploratory checks, after sourcing the local environment:

```bash
python automations/checkpoint_loop/eda.py --check
python automations/checkpoint_loop/eda.py --cwd . -- bash -lc \
  'source automations/checkpoint_loop/vcs-env.sh && vcs -full64 -ID'
```

The helper syncs the workspace, executes the command, streams output, and
fetches `automations/checkpoint_loop/runs/` even after a nonzero simulation
exit. Transfer failures fail verification. Workspace sync and execution are
serialized with a local lock. Always put generated evidence under that runs
directory; report artifacts as local paths. Receipts retain their true EDA
paths and hashes. Source edits and git commits belong on the local machine.
Do not wrap `verification_commands` in SSH, `eda.py` or `f2.py`: the controller
handles the selected backend. Commands use raw argv arrays and workspace-relative `cwd`;
local absolute workspace paths in argv are translated to EDA paths.

On EDA, source `vcs-env.sh` last after native environment setup, including in
nested `bash -lc` commands. It pins `VCS_HOME`, 64-bit mode and the compiler
wrappers without changing licenses. It prefers GCC/G++ 13, including Rocky's
`/opt/rh/gcc-toolset-13` layout, and otherwise selects the native GCC/G++.
`CHECKPOINT_EDA_CC` and `CHECKPOINT_EDA_CXX` can be set in the remote setup to
choose explicit compiler executables. GCC 14+ may reject VCS-generated C;
use a compatible native compiler. Active checkpoint harnesses and audits use
`tools/checkpoint_formats/toolchain.py` to bind the selected exact VCS/compiler
paths. Historical SP1 receipts stay unchanged; auditing them requires explicitly
selecting their original toolchain and having their original artifacts.

Regenerate host-specific build caches, binaries and missing migration artifacts.
For an existing VCS build directory, `VCS_FLAGS=-Mupdate` regenerates cached
Makefiles. Never treat copied receipts as a fresh SP2 validation. A VCS version
check alone does not establish compile/runtime license availability.

Existing M0-M7 component milestones precede the new hardware milestones:
`F2-bringup-and-baseline`, `F2-rocket-checkpoint-migration`,
`F2-boom-checkpoint-migration`, `F2-shuttle-saturn-checkpoint-migration`.
Saved index 11/iteration 174 migrates to index 8, F2 bring-up, with the next
turn still iteration 175. Old metasim CPU completion never completes new F2
milestones. History, feedback and commits are preserved, including names of
completed milestones no longer in the active order. Do not delete/reset
`runs/state.json`. `--max-iterations` is an absolute ceiling: from iteration
174, pass 175 for one more turn. Default 0 continues until verified completion
or an external block. Track hardware acceptance separately in
`docs/checkpointing/cpu-checkpoint-matrix.md`.

Codex defaults to `gpt-6.1-sol`, high effort; `--model` and `--effort` override
these. The implementation agent uses workspace filesystem restrictions and a
network-enabled permission profile for AWS and SSH, with approvals disabled. Full
access is unavailable through `--sandbox`. `--ignore-user-config` keeps unrelated
MCP apps out of implementation turns while retaining local authentication.

The central implementation agent is authorized to use as many subagents as
needed within runtime capacity. All LLM requests, delegation, follow-ups and
results go through that central agent using native managed subagent tools.
Independent Codex sessions, direct LLM API calls and detached Chia LLM jobs
are not part of this workflow. The central agent integrates results and waits
for, or cancels and joins, every worker before producing the final JSON report.
No delegated LLM work may outlive the central turn; Chia uses the central
invocation's completion to detect when the LLM call has finished.

Each turn produces independently executed verification and paired FireSim then
Chipyard git checkpoints, including WIP. Both plans are read-only and always
excluded from checkpoint commits. Console output and rotating `runs/loop.log*`
show prompts, tool calls and results; `runs/verification.log*` records remote
checks. Rotation retains six 16 MiB backups without truncating acceptance
inputs. Ephemeral Codex turns recover from repository history and saved state.
