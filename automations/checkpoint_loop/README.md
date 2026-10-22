# FireSim checkpoint/restore Chia loop

Current priority (October 22, 2026): Level-1 and Level-2 checkpoint/restore
for existing F2 Rocket quad-core, BOOM single-core and Shuttle + Saturn recipes
in `sims/firesim-staging/sample_config_build_recipes.yaml`. The detailed workload,
cut, state-coverage and negative-test requirements are at the top of
`plan_agent.md`. Each recipe must also pass live untransformed RTL VCS guided
by a concurrently running, checkpoint-restored metasim. There is no standalone
Shuttle milestone. Physical FPGA validation is deferred.

The active milestones are M0-M7 and M11-M13, retaining historical names.
The three synthesis/formal/gate milestones have been removed. Legacy saved
states migrate by completed milestone name on resume: old index 11 becomes
active index 8, still Rocket, with the same iteration, feedback and commits.
The saved state then records `milestone_order` so migration is idempotent.
Do not delete or reset `runs/state.json`. FCFS/fixture results do not establish
CPU support; each recipe needs its own complete restore, finite replay and
live-shadow acceptance. Track that acceptance in
`docs/checkpointing/cpu-checkpoint-matrix.md` as implementation proceeds.

The old loop, including its Jasper launcher, memory limiter, tests and ASIC
milestones, is preserved in `automations/checkpoint_loop_legacy_asic/`.
That source archive also includes the old plans, a state snapshot and file
hashes; see its `ARCHIVE.md`. Large historical run artifacts remain under
the existing `runs/` directory. The active loop does not initialize a Jasper
broker, require systemd/cgroup services, or require formal tools, synthesis,
standard-cell libraries, gate-level activity or power analysis. Historical
formal/gate proofs are retained as evidence, not rerun as prerequisites.

This local Chia loop drives Codex through the metasimulation and ordinary RTL
parts of `plan_agent.md`. It does not report FPGA validation on this machine.
The loop is an implementation workflow; its presence alone is not a completed
FireSim checkpoint feature. Each milestone advances only after its declared
artifacts exist and its verification commands pass.

Start from the Chipyard root:

```bash
bash automations/checkpoint_loop/run.sh --dry-run
bash automations/checkpoint_loop/run.sh
```

`run.sh` sources Chipyard's `env.sh` and FireSim's `env.sh`, then imports the
local Chia checkout. Set `CHIA_SOURCE` if your Chia installation is elsewhere.
It then sources `vcs-env.sh`, which sources `/ecad/tools/vlsi.bashrc` for licenses and pins
`VCS_HOME` and `PATH` to VCS Y-2026.03-SP1. Set `CHECKPOINT_LICENSE_SETUP` to
use another license setup script. The helper also adds the conda library
directory to `LD_LIBRARY_PATH` so the 64-bit VCS executable can load `libelf.so.1`.
Source this helper last after the build environments in each `bash -lc` check:
login-shell startup can otherwise select an older `VCS_HOME` even when an
absolute path to the new `bin/vcs` is used.

The system setup includes the reachable Synopsys server
`1709@flex-lic.millennium.berkeley.edu`. The user's `~/flexlm.sh` currently
lists only the two BWRC servers, which failed connection checks from this host.

The helper selects `/usr/bin/gcc-13` and `/usr/bin/g++-13` for VCS builds.
Conda currently supplies GCC 15, which rejects an undeclared function in
VCS-generated C. Small `compiler-bin/gcc` and `compiler-bin/g++` wrappers
handle VCS's internal compiler/linker invocations in addition to the exported
`CC`/`CXX` and `VCS_CC`.
Conda's Python remains available for the loop.
On the first Make rebuild of an existing VCS directory after switching releases,
pass `VCS_FLAGS=-Mupdate` to regenerate VCS's cached C build Makefile.

To inspect the configured license servers and VCS feature availability:

```bash
source automations/checkpoint_loop/vcs-env.sh
printenv VCS_HOME SNPSLMD_LICENSE_FILE
vcs -full64 -ID
/ecad/tools/mentor/calibre/current/bin/lmutil lmstat -a -c "$SNPSLMD_LICENSE_FILE"
```

Look for license server and `snpslmd` status `UP`, and the issued/in-use counts
for VCS features. `vcs -ID` only identifies the version; a successful VCS
compilation and `simv` run confirm actual compile/runtime license checkout.
Codex defaults to `gpt-6.1-sol` with `high` reasoning effort; `--model MODEL`
and `--effort LEVEL` override these settings. For a
short trial from a fresh state, `--max-iterations 1` stops after one Codex turn
and leaves a resumable state. This flag is an absolute iteration ceiling:
to run one more turn from saved iteration N, pass N+1. With the default `0`,
the loop continues until milestones are
verified or a real external dependency blocks progress. A repeat invocation
resumes from `runs/state.json`.

M0-M7 establish checkpoint formats, semantic replay, banked state access,
full metasim restore, rolling recovery, live clean-RTL shadowing and standalone
finite replay. M11-M13 apply complete Level-1, Level-2 and live-shadow acceptance
to Rocket, BOOM and Shuttle + Saturn, one family at a time. The live pair must
read back both restored states before any target edge, preserve transaction
timing beyond a recorded trace window, generate clean RTL debug waveforms,
complete healthy execution, and detect the first divergent signal and cycle.

The local Codex invocation defaults to `workspace-write`, using the Linux
bubblewrap sandbox. A per-invocation `checkpoint` permission profile inherits
`:workspace` filesystem restrictions and enables outbound networking for
Synopsys/FlexNet license checkout. This permits outbound connections generally;
it is not a license-server-only allowlist. It passes `-a never` so it never
prompts for approval; commands denied by the sandbox return an error to the agent.
Full access is unavailable through the loop's `--sandbox` option.
`--ignore-user-config` keeps unrelated MCP apps out of the implementation
agent; Codex still uses its local authentication. The loop explicitly passes
its model and reasoning effort settings to each Codex turn.

There are two remote Chia nodes: one runs Codex, one runs verification. Codex
receives one focused milestone at a time and reports a structured result with
artifacts and executable checks. Verification runs independently from the
agent's response. The loop always runs `git diff --check` in both repositories
and requires a VCS command for milestones involving simulation. The stated
acceptance criteria in `milestones.py` remain the source of truth; a successful
shell command alone does not prove a complex hardware invariant. Do not mark
the whole plan complete until the output comparisons and restoration tests
described there have passed.

The console and rotating `runs/loop.log*` show full Codex prompts, agent
messages and responses, tool calls and output, and verification logs. Older
diagnostic log segments are removed after six 16 MiB backups. This rotation
does not cap simulation resources, truncate verification input, or change pass
or fail decisions. Codex turns are ephemeral; progress lives in the repos,
their git history, and the small resumable state file. The Ray temporary
directory is removed after a normal shutdown.

After every turn, the loop commits a checkpoint to the FireSim git repository,
then to Chipyard (including the FireSim submodule pointer). It records even
work-in-progress turns with clearly labeled commits. Files already dirty when
the loop starts are excluded from commits. Their contents can change without
blocking resume or checkpointing. Existing staged changes prevent startup. This is
important in this checkout, where several conda files and the plan/PDF files
were already user-owned changes.
The agent treats `plan_agent.md` and `plan_human.md` as read-only inputs,
regardless of their git status; progress and proposed corrections go under
`docs/checkpointing/`.
Both plans are always excluded from checkpoints, even if initially clean.
There are no file-fingerprint checks, including during a running invocation.
Older saved runs automatically migrate to path-only commit exclusions on
resume, preserving milestone and iteration progress.

The current machine has VCS at
`/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs`. VCS compile/runtime licenses
remain required. FPGA bring-up is deferred. See `plan_agent.md` for the current
checkpoint/debug scope; it takes precedence over older plan and progress notes.
