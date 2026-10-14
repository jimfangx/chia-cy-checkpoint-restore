# CPU checkpoint matrix

Current milestone: M11 Rocket, iteration 82. Level-1 and Level-2 acceptance
remain **in_progress**. No CPU checkpoint continuation or clean CPU RTL replay
has passed. Physical FPGA validation, standalone Shuttle and ASIC power are
outside this matrix. The verified FCFS evidence remains in its existing docs.

| Family / existing recipe | Level 1 | Level 2 | Workload evidence |
| --- | --- | --- | --- |
| Rocket / `firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3` | in_progress: complete generated inventory rejects an unadapted plusarg reader | in_progress: complete ChipTop inventory rejects its block-device clock alias | Full 16 GiB native VCS baseline passes at 3,329,794 target cycles; all four harts independently audited; four actual memory faults pass in Spike |
| BOOM / `firesim_boom_singlecore_no_nic_l2_llc4mb_ddr3` | pending | pending | No execution claimed |
| Shuttle + Saturn / `firesim_saturn_GENV256D128_shuttle_singlecore_no_nic_l2_llc4mb_ddr3` | pending | pending | No vector execution claimed |

## Rocket settings and artifacts

Read the current recipe YAML on every build; `tools.checkpoint_formats.cpu_recipe`
prepares source-hashed commands without enabling an unaudited checkpoint profile.
The exact settings are:

| Setting | Value |
| --- | --- |
| PLATFORM | `f2` |
| TARGET_PROJECT | `firesim` |
| TARGET_PROJECT_MAKEFRAG | `../../generators/firechip/chip/src/main/makefrag/firesim` |
| DESIGN | `FireSim` |
| TARGET_CONFIG | `WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig` |
| PLATFORM_CONFIG | `WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config` |

The manager resolves the recipe's relative Makefrag from `sims/firesim`.
Direct `make -C sims/firesim/sim` uses the same directory's absolute path.
The recipe also specifies frequency 140 MHz and TIMING build strategy; these
are retained in the recipe record, with no FPGA implementation invoked.
VCS uses Y-2026.03-SP1, `-full64`, `VCS_FLAGS=-Mupdate`, system GCC/G++ 13,
and the sourced Conda library/include directories. No Conda files are edited.

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/`.

Workload ELF SHA256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

* `rocket-recipe.json`: exact YAML bytes/hash, raw and resolved settings,
  executable complete-inventory Make commands.
* `rocket-elaboration-audit.json`: source-bound high-form elaboration with all
  four RocketTile instance paths, six ChipTop clock inputs, async reset and
  original external modules. This is not a complete lowered state manifest.
* `rocket-native-owners.json`: actual header's three constructor passes and
  the separately audited heartbeat construction. State adapters remain pending.
* `rocket-build-identity.json`: emitted baseline RTL, headers, concrete
  blackboxes, executable and tool/setup hashes. No checkpoint profile enabled.
* `rocket-verilog-cache.log`: complete generated inventory rejects the actual
  unadapted `plusarg_reader` inside core 0's `PlusArgTimeout`. Earlier writable
  cache setup failure is preserved in `rocket-verilog.log`.
* `rocket-semantic-inventory-retry.log`: independent pre-FAME ChipTop inventory
  rejects `FireSim.chiptop0.system.bdev_clock`; no semantic manifest, checkpoint
  image or clean CPU RTL acceptance is claimed. The initial missing output
  directory diagnostic remains in `rocket-semantic-inventory.log`.
* `rocket-baseline-vcs-build-retry.log`: exact regular recipe VCS build passes.
  The earlier include-path error is preserved in `rocket-baseline-vcs-build.log`;
  installed `libdwarf.h` and its library were found in the existing Conda env.
* `workload/{summary.json,commands.json,rocket-quad.riscv}`: RV64IMA/Zicsr
  bare-metal program, source/ELF hashes, native compiler and Spike commands.
  Each of four harts checks 64 KiB through early stores, sequential reads,
  three rounds of cache-line-strided read/write work and late verification.
  All four must complete before HTIF PASS. Fault ELFs corrupt real memory on
  harts 0/1/2/3 and return failure codes 1/2/4/8 respectively in Spike.
* `rocket-baseline-runtime-full-retry/command.json`: executable native VCS
  workload command, full 16 GiB functional backing memory, native output and
  four TracerV streams. PASS after 3,329,794 fastest-clock target cycles;
  native exit 0. Initial wrong-unit memory and argument-position diagnostics remain
  in the separate `rocket-baseline-runtime*` directories.
* `rocket-baseline-audit.json`: independent decoding of actual retired SD
  instructions and their source-register values. Every hart wrote phases
  1/2/3/4, completion 1 and failure 0; hart 0 actually stored HTIF PASS 1.
  Per-hart print labels are recorded separately from checkpoint target-cycle
  labels. This audit establishes workload execution, not checkpoint replay.
* `rocket-fcfs-profile-rejection.json`: the actual exact Rocket Make request
  rejects `FS_CHECKPOINT_PROFILE=fcfs-fased-v1` before generation, preserving
  the baseline RTL/header/executable bytes. This is a build preflight check;
  invalid CPU-image loader rejection remains unverified.

## State ownership and remaining acceptance

The constructor order is master, loadmem, CPUManagedStreamWidget, peek-poke,
reset-pulse, blockdev, UART, FASED, four TracerV instances, TSI and clock.
`firesim_top_t` adds heartbeat after construction. The actual F2 configuration
has one functional-memory channel, rather than the FCFS profile's four. Audit
complete generated storage, FAME/channel/clock state, MMIO, full functional
memory and host timing independently for this configuration.

`firesim_top_t` currently inherits the unsupported checkpoint schema and lacks
incremental dispatch. Its termination/run-loop state, scheduler and base
lifecycle need explicit owners. TSI/FESVR needs loading flags, wait/step state,
loadmem and serial queues, HTIF state and suspended execution accounted for.
UART, blockdev, four trace sinks, CPU stream, heartbeat and FRFCFS/LLC model
state also require configuration-specific audit. The FCFS whitelist remains
restricted; constructor membership alone never certifies a driver adapter.

Proposed Level-2 boundary is the complete `FireSim.chiptop0`, containing all
four CPUs, caches and uncore. Its external memory/device/serial inputs must be
recorded at the actual boundary. Six named clock inputs include 500 MHz uncore
and 1000 MHz tile/memory clocks. Alias resolution, async reset, clock phase and
multiple-clock trace/replay require an explicit versioned adapter; do not force
them into the current single-clock semantic schema or omit crossing state.

No early/warmed/outstanding-memory/late checkpoint cut is verified yet. Phase
markers in the workload help select cuts but cannot establish actual cache or
in-flight state. Complete fresh-process Level-1 continuation, independent
Level-2 zero-edge readback/replay, all sampled timing comparisons, atomic
invalid-image/build/owner rejections and first-divergence semantic corruption
remain required. No `.fsckpt`, `.rtlckpt` or boundary `.trace` is claimed here.

## Executable native regressions

Run from the Chipyard root. Source `vcs-env.sh` last in every VCS shell.

```sh
source env.sh && source sims/firesim/env.sh
export COURSIER_CACHE="$PWD/automations/checkpoint_loop/runs/m11-iteration82/coursier-cache"
export TMPDIR="$PWD/automations/checkpoint_loop/runs/m11-iteration82/tmp-semantic"
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
source automations/checkpoint_loop/vcs-env.sh
VCS_FLAGS=-Mupdate python -m tools.checkpoint_formats.tests.verify_semantic_vcs \
  --build automations/checkpoint_loop/runs/m11-iteration82/semantic-build \
  --out automations/checkpoint_loop/runs/m11-iteration82/semantic-regression-retry
```

M2 passes all five cuts, all 22 words, actual first divergence C=29 and four
loader rejections. M3's analogous `verify_banked_vcs` command uses `banked-build`,
`banked-regression` and `tmp-banked`; it passes 717 transport edges, 23 semantic
advances, six captures, 242 clean replay samples and eight invalid reads.
`assembly-destination-audit.json` checks all three newly requested JARs contain
the native generator/Golden Gate main classes. The Make helper now disables
sbt-assembly's stale destination cache and checks nonempty output before touch.
The observed zero-byte reused M2 build cache was repaired from the isolated,
native-validated JAR; `empty-cache-repair.json` records before/after bytes.

All 218 Python tests and the eight FCFS Make/four generator rejection checks
pass. Exact logs are `python-tests-final.log`, `fcfs-make-regression/summary.json`
and the two native regression directories. These regressions preserve earlier
support; they cannot substitute for CPU checkpoint acceptance.

The native Rocket baseline command can be rerun verbatim from
`rocket-baseline-runtime-full-retry/command.json`. Audit its actual output with:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.audit_rocket_baseline \
  --runtime automations/checkpoint_loop/runs/m11-iteration82/rocket-baseline-runtime-full-retry \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --out automations/checkpoint_loop/runs/m11-iteration82/rocket-baseline-audit.json
```

`verify-evidence.py` rechecks selected current-source native evidence and
protected inputs. `summary.json`, `verification-commands.json` and
`artifact-manifest.json` record the final in-progress result and full-path
recovery. No CPU checkpoint acceptance is inferred from the native baseline.
