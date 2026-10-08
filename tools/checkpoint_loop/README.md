# FireSim checkpoint/restore Chia loop

This local Chia loop drives Codex through the metasimulation and ordinary RTL
parts of `plan_agent.md`. It does not report FPGA validation on this machine.
The loop is an implementation workflow; its presence alone is not a completed
FireSim checkpoint feature. Each milestone advances only after its declared
artifacts exist and its verification commands pass.

Start from the Chipyard root:

```bash
bash tools/checkpoint_loop/run.sh --dry-run
bash tools/checkpoint_loop/run.sh
```

`run.sh` sources Chipyard's `env.sh` and FireSim's `env.sh`, then imports the
local Chia checkout. Set `CHIA_SOURCE` if your Chia installation is elsewhere.
It also adds the conda library directory to `LD_LIBRARY_PATH` so the 64-bit
VCS executable can load `libelf.so.1`.
Codex uses its CLI default model; `--model MODEL` overrides it. For a
short trial, `--max-iterations 1` stops after one Codex turn and leaves a
resumable state. With the default `0`, the loop continues until milestones are
verified or a real external dependency blocks progress. A repeat invocation
resumes from `runs/state.json`.

The local Codex invocation uses `danger-full-access` because this host's
`workspace-write` sandbox fails to initialize its `bwrap` loopback network.
`--ignore-user-config` keeps unrelated MCP apps out of the implementation
agent; Codex still uses its local authentication. The CLI's model default is
used unless `--model` is supplied.

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
the loop starts are excluded and fingerprinted; if they change, the loop stops
before committing. Existing staged changes also prevent startup. This is
important in this checkout, where several conda files and the plan/PDF files
were already user-owned changes.

The current machine has VCS at
`/ecad/tools/synopsys/vcs/W-2024.09-1/bin/vcs` and Jasper at
`/ecad/tools/cadence/JASPER/jasper_2025.03/bin/jg`. FPGA bring-up is deferred.
Gate-level replay and power analysis still require a real ASIC netlist,
matching libraries, and a suitable power analysis tool; the loop must report
those dependencies rather than inventing a result.
