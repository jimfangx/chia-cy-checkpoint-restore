# CPU checkpoint matrix

Current milestone: M11 Rocket, iteration 85. Level-1 and Level-2 acceptance
remain **in_progress**. No CPU checkpoint continuation or clean CPU RTL replay
has passed. Physical FPGA validation, standalone Shuttle and ASIC power are
outside this matrix. The verified FCFS evidence remains in its existing docs.

| Family / existing recipe | Level 1 | Level 2 | Workload evidence |
| --- | --- | --- | --- |
| Rocket / `firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3` | in_progress: generated RTL inventory audited; private-memory blockdev and explicit buffered-file UART host adapters pass native component continuation; complete runtime ownership and fresh CPU continuation pending | in_progress: fresh complete ChipTop inventory rejects its block-device clock alias | Full 16 GiB native VCS controls and all four instruction traces retained; four actual memory faults pass in Spike; see iteration 85 below |
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

## Iteration 85: UART ownership and reusable evidence

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration85/`.

`firesim.widget.uart.v1` supports completed, unpoisoned host calls before
`finish()` with explicit `+uart-checkpoint-file0`, `+uart-in0=<regular-file>`
and `+uart-out0=<destination>`. The constructor owns every input byte; the
image binds those bytes, the UART index and all six actual Rocket MMIO
addresses (1056 through 1076). It captures the entire input cursor, binary
output prefix, both data bytes and all four handshake flags. Active/poisoned
call state and finished lifecycle are rejected rather than omitted. Output
stays in owned memory until successful `finish()`, so construction, validation
and restore do not overwrite an existing destination. A fresh process may
select a new output destination but must supply the identical input bytes.
Default stdin/signals, PTYs and ordinary file descriptors explicitly reject
checkpointing. No CPU whitelist or semantic schema is extended.

`uart-native/latest.json` selects the retained component summary. Native
ASan/UBSan and VCS DPI each pass all nine cuts in independent processes,
including startup, binary input/output and EOF. An independent Python oracle
compares every state byte before the first edge, full final readback, every
MMIO transaction with its original **fixture** label, and the complete output
including its restored prefix. Each backend passes 723 rejection assertions
without owner/MMIO/destination mutation. Structurally valid actual cursor
corruption first fails `uart_in_bits` at fixture C=128, operation 4; no input
valid acknowledgement or operation 5 is issued. Positive raw traces are
rechecked after all negative cases. These checks establish the host component,
not Rocket CPU `.fsckpt` or Level-2 semantic replay acceptance.

Run from the Chipyard root; each invocation preserves previous component runs:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_uart_checkpoint_vcs \
  --rocket-header automations/checkpoint_loop/runs/m11-iteration85/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h \
  --out automations/checkpoint_loop/runs/m11-iteration85/uart-native
```

The exact-recipe native VCS rebuild links the adapter and retains the settings
above, full 16-GiB functional backing, GCC/G++ 13.3 and 58 actual host translation
units. `rocket-build-identity.json` binds 207 current native inputs, including
actual compiler dependencies. Two complete four-hart workload controls, with
default and explicit buffered UART modes, independently pass at target count
3,329,794. Every complete hart trace matches the prior uninterrupted control
(37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes), as do independently
decoded phase/completion/failure/HTIF store and CPU-print labels. The generated
RTL, compared constant headers and complete simulator inventory match too.
These are uninterrupted controls; all four required CPU checkpoint cuts and
fresh CPU restore comparisons remain pending. Workload ELF SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Full M2/M3 metasim/ordinary RTL VCS, 52 existing widget continuations, all 219
Python tests and eight FCFS Make/four generator guards pass. Fresh exact-source
ChipTop discovery still rejects `FireSim.chiptop0.system.bdev_clock`, emitting
no partial semantic manifest/clean RTL. Fresh native CPU preflight/save/restore
requests still reject unsupported runtime ownership without publishing an
incomplete image. Full CPU cuts, fresh Level-1 continuation, independent
multi-clock semantic capture, fresh ordinary RTL zero-edge readback/replay and
CPU-level image/corruption tests remain pending.

The initial buffered post-run audit lacked `command.json`; the full native
run had passed. The executed launcher is retained as
`run-buffered-rocket-control.initial.py`. Command metadata was reconstructed
from that exact launcher, and the independent decoder/full trace comparison
was rerun against the complete finished run. Initial diagnostics and the
passing `rocket-buffered-control-audit-retry.log` are retained; no workload
was shortened or reported passing without actual execution. The interim
combined audit also correctly rejected while the buffered summary was pending.
The completed reusable audit checks all artifacts after both controls finish.

The previous verification failure was an old Git index/HEAD snapshot compared
after the controller's next checkpoint. Historical logs remain intact. The
retained-evidence audit now binds old UART sources to exact archived bytes and
pinned Git objects; current native evidence separately binds current sources.
The reusable check validates immutable protected inputs and controller
ancestry. `verify-protected-turn.py` additionally checks raw index/HEAD bytes
at turn end. See [evidence-lifecycle.md](evidence-lifecycle.md).

Executable native controls (no FPGA build):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration85/run-rocket-control.py
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration85/record-rocket-build.py
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration85/run-buffered-rocket-control.py
```

Independent saved-evidence verification:

```sh
python -m automations.checkpoint_loop.runs.m11-iteration85.verify-evidence
```

## Iteration 84: block-device host ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration84/`.

Added `firesim.widget.blockdev.v1` for completed host calls with a private
in-memory disk, including the actual workload's `+blkdev-in-mem0=128`, and for a
disconnected device. The disk now has an explicit owned, initially zeroed byte
buffer behind `fmemopen`; both memory and external FILE streams close at
destruction. The adapter binds all 26 generated MMIO addresses, the actual one
tracker/24-bit latency configuration, sector geometry and runtime latencies.
It captures initialization, response-pending status, ordered request/data/read
response/ack queues, every tracker offset/count/size and all 1,024 tracker data
words, all 65,536 disk bytes and the logical FILE position. FILE buffering is
flushed at the completed-call boundary; restore reconstructs an independent
stream at the captured position without MMIO or target advancement.

Decode and allocation precede all restore mutation. Invalid booleans, lengths,
tags, ranges, tracker shapes, pending flags, lifecycle contradictions,
configuration mismatches and incomplete disk bytes reject. Every public host
operation guards suspended/reentrant cuts and poisons interrupted calls.
External disk paths, debug logs and failed/EOF FILE state explicitly reject;
they need external ownership adapters. No CPU runtime whitelist is extended.

`blockdev-native/latest.json` selects the final component run under
`blockdev-native/native-xb8o3fpu/`. ASan/UBSan native execution and native VCS
DPI each terminate the source and independently restore all 15 cuts in fresh
processes. An independent Python oracle checks every owner byte, including
inactive tracker words and the full disk; native VCS reports readback at zero
edges. All MMIO operations, 128 actual read response words and two write
acknowledgements retain their fixture release labels. Cuts include data queued
before a request, queued requests, partial writes with 5/21 beats retained,
stalled acks and partially drained read responses. Each backend passes 1,639
negative assertions, including malformed/incompatible payloads, unsupported
external modes and interrupted calls, without partial owner mutation or MMIO.
A separate zero-edge roundtrip varies every disk byte, including its first and
last bytes, at a legal end-of-file position, checking libc reconstruction.
The final evidence audit also rechecks every positive raw continuation after
the negatives. It caught the initial negative fixture overwriting cut 5's
trace; the corrected suite isolates that fixture and retains all 15 traces.
Earlier diagnostics remain under their original run directories.

Actual partial-write tracker corruption passes structural loading, then fails
at the first changed `bdev_rresp_data_lower` write at **fixture** cycle 142,
operation 6, exit 1; no operation 7 is issued. These are host component fixtures,
not Rocket target-cycle cuts, CPU `.fsckpt` acceptance, or Level-2 semantic
replay. The complete Rocket run loop, TSI/FESVR, UART, four TracerV sinks and
heartbeat owners, coherent cuts, fresh full CPU restores and CPU image/fault
checks still remain. Independent current-source ChipTop discovery continues to
reject `FireSim.chiptop0.system.bdev_clock`, emitting no partial semantic
manifest or ordinary CPU RTL. The six clocks, async reset and original CPU
storage require a separate versioned semantic adapter.

Executable component check from the Chipyard root (creates a new run directory):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_blockdev_checkpoint_vcs \
  --rocket-header automations/checkpoint_loop/runs/m11-iteration84/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h \
  --out automations/checkpoint_loop/runs/m11-iteration84/blockdev-native
```

The exact-recipe build and complete four-hart control are reproducible through
`run-rocket-control.py`; its `rocket-native-commands.json` records each native
build/runtime/audit argv and result. Every VCS shell sources both environments,
then `vcs-env.sh` last. The source-bound recipe helper retains
all settings above and builds no bitstream. Native build artifacts use a new
iteration-84 directory, preserving prior controls.

The current exact-recipe build and full 16-GiB workload pass at C=3,329,794.
All four complete TracerV files match iteration 83 byte-for-byte (37,582,346 /
49,976,156 / 50,391,641 / 50,189,006 bytes). Independent retired-store decoding
confirms phases 1/2/3/4, completion 1, failure 0 on every hart and the actual
HTIF PASS store; every audited CPU-print cycle field also matches the prior
control. Workload ELF SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Generated RTL, both compared constant headers and the complete generated-state
manifest retain their original bytes. `rocket-build-identity.json` binds 130
current input files and 58 native host translation units, GCC/G++ 13.3, the
normal executable and the newly linked blockdev methods. These are workload
and build controls, not restored CPU execution or complete boundary replay.

Full-path selection and executable checks are `selected-evidence.json`,
`verification-commands.json`, `verify-evidence.py`, `summary.json` and
`artifact-manifest.json`. The independent evidence checker re-audits complete
generated ownership, current source hashes, every component cut's full disk
and tracker words, all retained raw MMIO traces, native process statuses, CPU
controls, explicit runtime/semantic rejection, regressions and protected inputs.

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration84/run-rocket-control.py
```

Run the independent saved-evidence audit without rerunning the workload:

```sh
python -m automations.checkpoint_loop.runs.m11-iteration84.verify-evidence
```

## Iteration 83: exact generated RTL ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration83/`.

The exact recipe now emits its complete generated RTL manifest and reference.
The metasim-only `plusarg_reader` adapter owns `myplus`, including its runtime
value rather than assuming `DEFAULT`. Each instance binds the exact inline
Verilog SHA256, WIDTH, DEFAULT and FORMAT; unknown models, ports and parameter
shapes still reject. This adapter describes the non-SYNTHESIS simulation model.
It does not add FPGA storage or change the target RTL. Level-2 IDs and the
FCFS runtime profile remain independent.

| Generated storage adapter | Entries | Words | Bits |
| --- | ---: | ---: | ---: |
| FIRRTL registers | 10,278 | 10,278 | 94,592 |
| FIRRTL memories | 742 | 435,116 | 20,899,468 |
| Emitter memory pipelines | 434 | 434 | 6,581 |
| Metasim plusarg registers | 7 | 7 | 193 |
| Metasim BUFGCE outputs | 3 | 3 | 3 |
| Total | 11,464 | 445,838 | 21,000,837 |

There are 2,292 generated instances. The seven plusarg registers belong to the
four cores' PlusArgTimeout instances, two UART transmit controls and the custom
boot pin. `rocket-generated-state-owners.json` also groups all storage by its
actual top-level owner, including the CPU-managed stream buffers, all four
TracerV bridges, TSI, blockdev, UART, FRFCFS/LLC, FAME and interconnect state.
This is generated RTL coverage; 16 GiB functional backing memory, native host
queues, MMIO/transport, scheduler and driver state still need complete owners.

`rocket-generated-independent-audit.json` independently checks emitted register
and memory declarations, including parameterized external instances, and passes
eight mutations of the actual Rocket artifacts: missing storage/owner, unbound
default, altered source, changed bound format, changed emitted width, an actual
extra register and missing model. Original files retain their hashes. These are
inventory rejection checks, not CPU checkpoint-image loader acceptance.

`plusarg-native/` contains separate capture and fresh ordinary VCS processes
using the compiler-produced two-owner inventory. Nondefault native values are
captured, conflicting startup plusargs are replaced, and both complete words
(33 bits) read back before any edge and match four diagnostic boundaries.
An actual storage-bit fault first diverges at boundary 0, edges=0, exit 1.
The initial diagnostic found VCS returning zero for `$fatal`; the final check
uses the existing DPI failure function and verifies nonzero native status.
This microtest establishes the external adapter only, not clean CPU RTL replay.

Executable native adapter verification, from the Chipyard root (each invocation
keeps prior evidence and creates a fresh output directory):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_plusarg_inventory_vcs \
  --inventory automations/checkpoint_loop/runs/m11-iteration83/scala-artifacts/plusarg-inventory.json \
  --reference automations/checkpoint_loop/runs/m11-iteration83/scala-artifacts/plusarg-reference.fir \
  --out automations/checkpoint_loop/runs/m11-iteration83/plusarg-native
```

All 16 compiler inventory tests and 219 Python tests pass. Fresh complete M2
and M3 native VCS metasim/ordinary RTL regressions pass, retaining their five
cuts/22-word readback/C=29 divergence and 717 transport edges/23 advances/six
captures/242 boundary samples/eight invalid reads respectively. Eight FCFS Make
and four generator guards pass without changing its compiled inventory.

### Native Rocket execution and generated-state samples

The exact recipe's native VCS build with read-only probes passes. The full
16-GiB, four-hart workload passes at 3,329,794 fastest-clock target cycles.
`rocket-workload-audit.json` independently decodes all harts' phase 1/2/3/4,
completion=1, failure=0 and the real HTIF PASS store from native execution.
The workload ELF remains SHA256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Every sample in `rocket-generated-probe/generated-state.jsonl` contains all
445,838 generated words at one settled host falling edge. The sample's actual
`ClockBridgeModule_0.tCycleFastest` value supplies its target-count label:

| Diagnostic sample | Target count | Host sample | Valid D-cache lines, harts 0/1/2/3 | Harts waiting for a cached grant | Host reads in flight |
| --- | ---: | ---: | --- | --- | ---: |
| Startup/early execution | 50,000 | 467,603 | 313 / 1 / 1 / 1 | 0 | 0 |
| Warmed-cache execution | 850,000 | 3,421,115 | 498 / 507 / 501 / 501 | 0, 1, 2 | 0 |
| Outstanding workload memory | 1,013,847 | 3,737,220 | 511 / 511 / 510 / 510 | 1, 2, 3 | 1 |
| Late execution | 3,200,000 | 8,002,559 | 511 / 512 / 510 / 512 | none | 0 |

`rocket-active-sample-audit.json` binds the actual DCache/ClientMetadata sources
and lowered bit extraction: coherence state is bits 24:23 of each of eight
64-word tag banks, and Nothing=0. `cached_grant_wait` is set when an actual
cached TileLink request fires and cleared by the final grant beat. All four
saved PC payloads at the outstanding sample are in the workload's memory loop.
These observations establish active generated state. They do not certify an
atomic simulator/host cut or original multi-clock semantic state at those
labels; all four required checkpoint/restore cut tests remain pending.

`rocket-trace-comparison.json` compares all four complete TracerV files against
the iteration-82 uninterrupted control: 37,582,346 / 49,976,156 / 50,391,641 /
50,189,006 bytes match respectively. Independently decoded phase, completion,
failure and HTIF store cycle fields also match. This establishes that the
read-only probes preserve the recorded instruction behavior and timing. It is
not restored execution or complete original-DUT boundary replay.

Current native artifacts are `rocket-generated-summary.json`,
`rocket-generated-independent-audit.json`, `rocket-build-identity.json` (145
bound inputs, 58 actual host translation units and GCC/G++ 13.3),
`rocket-native-commands.json` (exact build, full workload and audit argv/results),
`rocket-generated-runtime/{command.json,exit.json,native-vcs.log,TRACEFILE-C0..C3}`
and the two sample/trace audits above. The emitted RTL and all three headers
are byte-identical to iteration 82 (`rocket-baseline-build-byte-comparison.json`).

The following reproduces the native build/control/probe check using this run's
diagnostic build/output directory. Exact individual VCS commands and all recipe
settings are also recorded in `rocket-native-commands.json`:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration83/run-rocket-generated.py
```

Fresh native unsupported-runtime checks create their own output directory:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration83/verify-rocket-runtime-rejection.py
```

Preflight/save/restore each exits 1 before driver initialization and publishes
no partial checkpoint. Actual CPU image decoding remains unsupported. A fresh
exact-source semantic compiler request also rejects
`FireSim.chiptop0.system.bdev_clock` and emits no partial semantic manifest or
clean CPU RTL (`rocket-semantic-inventory/{command.json,summary.json,native-compiler.log}`).
Complete Level-1 fresh-process continuation, independent Level-2 zero-edge CPU
readback/finite boundary replay, CPU image rejection and first semantic
divergence remain required. No CPU recipe/level is verified.

## Retained iteration 82 evidence

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

Iteration 83's source-bound `rocket-runtime-owner-audit.json` distinguishes
existing hooks from missing ones. CPUManagedStreamWidget already implements
`firesim.widget.cpu-managed-stream.v1`: its host drivers have no persistent
queue offsets, but initialization, stream parameters, suspended stream calls
and the actual CPU AXI transport still need native cut/restore validation.
FASED already has a host adapter for configuration, lifecycle, statistics,
histograms and range counters; its presence does not certify this FRFCFS/LLC
recipe or its one 16-GiB memory channel. Generic master/loadmem/peek-poke/reset/
clock hooks likewise require exact CPU configuration binding.

| Missing concrete runtime adapter | State that cannot be omitted |
| --- | --- |
| FireSim run loop | `terminated`, local exit/run-loop phase, scheduler credits/deadlines/callbacks, base lifecycle and completed-operation dispatch |
| TSI/FESVR | Wait/step/loading flags; loadmem and serial queues; inherited testchip/HTIF state; suspended `context_t` execution, which contains process-specific pointers and a ucontext or pthread |
| Blockdev integration / external modes | Private-memory/disconnected host hooks now pass native component checks; complete CPU atomic cut integration and external disk/log ownership remain pending |
| UART | Serial handshake data, handler/input positions, pending external bytes, global `specialchar` and endpoint/signal behavior |
| Four TracerV sinks | Cycle/trigger/clock state, file history and positions, tracker/mode state, stream identities and any suspended token buffer; draining streams affects target timing |
| Heartbeat | Poll/trip/last-cycle/timeout state, time origin, configuration and log history; it can terminate execution |

The audit hashes the actual generated header, reviewed driver implementations,
testchip inheritance and installed FESVR headers. It explicitly remains an
in-progress source audit. Native preflight/save/restore requests on the exact
Rocket binary still reject unsupported CPU runtime ownership and publish no
partial checkpoint; this is not malformed-image loader acceptance.

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
