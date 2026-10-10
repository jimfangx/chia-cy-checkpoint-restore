# M4 opt-in normal Make integration — iteration 42

`FS_CHECKPOINT_PROFILE=fcfs-fased-v1` enables the audited non-debug RTL VCS
metasim capability through the ordinary FireSim Make flow. It requires
`TARGET_PROJECT=fasedtests`, `DESIGN=AXI4Fuzzer`, `TARGET_CONFIG=FCFSConfig`
and `PLATFORM_CONFIG=FCFS16GBQuadRank_DefaultF1Config`. Other profiles,
drivers, partial generated inventories and debug/gate-level/other-backend
requests fail explicitly. Ordinary builds retain their public-request
rejection and existing flags.

The profile automatically requests the complete `FPGATop` generated-state
manifest and reference FIRRTL. The native inventory is derived from the
generated header's constructor passes in the same order as production entry:
core, managed streams, then bridges. This profile requires exactly the six
audited widgets, four functional-memory channels, no managed streams and no
QSFP channels. Runtime validation rechecks all 17 actual native owners and
their schemas before capture and before any restore loads. No historical
checkpoint, diagnostic or test fixture is a production build input.

`tools/checkpoint_formats/metasim_build.py` independently checks emitted RTL
coverage, generates the four compiled loader tables and runtime manifests,
and binds source/header contents, compile/link flags, compiler and VCS release.
The generated coordinator guards all host and generated clock edges, waits
for production entry's restore reservation, loads through the existing
all-owner prevalidation/commit contract, verifies generated/harness readback,
and bootstraps the parked dispatcher before releasing clocks. Emitter startup
initialization settles while clocks remain reserved, before any state loads.
Native readback
remains part of the aggregate commit. Capture uses the existing ordinary
harness callback; neither capture nor restore requires a verification monitor.

Checkpoint executables and VCS companion data live in
`GENERATED_DIR/checkpoint-vcs/AXI4Fuzzer-checkpoint[.daidir]`; checkpoint C caches
and compiled tables also have separate names. Make revalidates the inventory
on every opt-in invocation and invalidates only checkpoint objects whose
recorded source/header dependencies are newer. This includes regenerated
loader tables that VCS's cached external-C Makefile can otherwise miss.
VCS's compiled `+no_notifier` argument is omitted for this restricted profile;
the public runtime continues to reject unaudited arguments.

Run from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
cd sims/firesim/sim
make TARGET_PROJECT=fasedtests DESIGN=AXI4Fuzzer TARGET_CONFIG=FCFSConfig \
  PLATFORM_CONFIG=FCFS16GBQuadRank_DefaultF1Config \
  FS_CHECKPOINT_PROFILE=fcfs-fased-v1 VCS_FLAGS=-Mupdate vcs
```

Invoke the resulting executable with explicit positive `+memsize` and
`+max-cycles`, `+vcs+initreg+0 +vcs+initmem+0`, and either
`+fs-checkpoint=/absolute/output.fsckpt +fs-checkpoint-operation=N` or
`+fs-restore=/absolute/input.fsckpt`. The operation schedule counts completed
driver operations. The container's target cycle comes from manifested FASED
state. Restore requires the same executable, loaded libraries and compatible
runtime configuration.

Verification passes under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m4-iteration42/`.
The full verifier's `--normal-make` mode uses Make's generated tables and
coordinator; its optional monitor only observes transactions and cut metadata.
It preserves VCS's compiled executable basename and companion directory when
archiving a test executable, with `simv` aliases for existing verifiers.
Repeating `--normal-make` in an existing output directory creates a separate
`invocation-*` directory and reruns the entire scope, preserving earlier
executables, libraries, checkpoints and logs.
Initial packaging trials failed on missing companion data/library lookup;
their logs remain separate diagnostics. A subsequent trial correctly rejected
Make's injected `+no_notifier`, which prompted the profile-only flag correction.
An early fresh-load readback also caught emitter initialization overwriting a
restored token bit at time zero; clocks remain reserved through the audited
initialization-settlement delay before loading in the corrected coordinator.
The uninterrupted runs complete at 774,628 default / 774,632 randomized target
cycles. The original complete run and a repeated complete run each match all
3,765,516 continuation samples across the five cuts, including an in-flight
native write and outstanding FASED traffic at cut 699275. Each cut preserves
all 13,507,456 generated words, 29 harness records and 17 native owners, with
exact pre-edge readback and zero-edge bootstrap. Both independent audits pass
68 fresh processes, 67,537,280 generated-word comparisons and 85 native-owner
comparisons. Each run passes all 56 public restore rejections. The repeated
run preserves 123 earlier immutable files' contents and inodes.

All five additional diagnostic-free public capture/restarts pass another
3,765,516 continuation samples, exact original native readback and independently
bounded reporting timestamps. All 19 scheduling rejections, four publication
failures, unreachable-cut and missing-callback checks pass. All eight Make and
four generator rejections preserve the compiled inventory. All 44 retained
baseline and 15 focused scopes pass, including 53 Python / 20 Scala tests,
ordinary clean RTL VCS, complete M2/M3, component owners, counters/profiling,
lifecycle/bootstrap guards, publication faults and independent audits.

The first independent Make audit assumed `simv` was the canonical executable
filename. It now resolves the archive's alias, retaining exact ELF content
hash and inventory checks. Its initial diagnostic is retained separately.
The baseline runner initially lacked copied local helper scripts and its audit
expected the historical 49-test Python count. The scripts were supplied,
the count increased to 53 and every unfinished scope rerun in full.

`normal-make-settled/summary.json` and `independent-evidence.json` hold the
original full Make results; the repeat is under
`normal-make-settled/invocation-m5u2i5du/`. `normal-make-public/summary.json`
holds diagnostic-free restart/request results. `results.json`,
`focused-results.json` and `normal-followup-results.json` retain actual command
results. `normal-repeat-audit.json` proves prior file preservation.
`executed-verification-commands.json` records successful argv arrays;
`artifact-manifest.json` lists full paths and source/input hashes.
`final-integrity.py` verifies the complete source-bound evidence and catalog.

M4 is ready for this audited profile. M5 DMA transport is next; rolling capture
and capture during a restored continuation remain later work. The supported
production flow uses the canonical Golden Gate emission for the named
configuration; additional verification modules are observers.

Both plans remain read-only, with their initial content hashes retained.
Level-1 and Level-2 remain independent. No physical FPGA, formal or ASIC
validation is claimed.
