# M4 concrete host widget state — iteration 18

M4 remains in progress. Five concrete widget drivers now provide audited,
configuration-bound save/validate/load hooks. They participate in the existing
parked-driver and settled-harness diagnostics. Full simulator checkpoint
publication and fresh-process FireSim restoration remain outstanding.

| Host owner | Retained host state | Configuration bound in payload |
| --- | --- | --- |
| `master_t` | No mutable state between calls | Init/fingerprint MMIO addresses |
| `clockmodule_t` | No mutable state between calls | All host/target counter and latch MMIO addresses |
| `loadmem_t` | No mutable state between calls | All memory-control MMIO addresses, AXI ID/address/data widths and chunk count |
| `reset_pulse_t` | Constructor-selected pulse length, immutable after construction | MMIO addresses, maximum/default/selected pulse lengths |
| `peek_poke_t` | Last request's unstable and timeout flags | Step/done/stability MMIO addresses and complete sorted input/output name/address/chunk maps |

Hardware counters, counter read latches, reset progress, load-memory address
and data registers, and outstanding transactions remain generated RTL/MMIO
owners. No hook reads or writes MMIO, advances a clock, replays initialization,
or drains outstanding traffic. Loading peek/poke assigns its two flags only
after complete validation. Its flags now start deterministically false rather
than containing uninitialized values before the first request.

`core/widget_checkpoint.h` provides explicit little-endian configuration
encoding and call guards, used only by the audited concrete classes. Payloads
start with `WDGCKPT1`, version 1, a concrete type tag and fixed-field count,
followed by configuration words, variable port maps where applicable, and a
64-bit result flag word. Schema names are `firesim.widget.<name>.v1`.
Validation requires exact length, concrete type, configuration, map contents
and legal flag bits before mutation. Passive owners require a zero flag word.
These component payloads are not `.fsckpt` containers and do not bind a whole
simulator build or certify a restorable runtime cut.

Every synchronous widget operation has a scope guard. Capture, validation,
load and reentrant calls reject while an operation is suspended in MMIO.
Interrupted operations poison the owner. Partially assembled counter reads,
GMP buffers, file cursors and polling deadlines are therefore never represented
as resumable host state. The internal file-loader/write and step/poll paths
remain inside one outer guard, preserving their original bus order. GMP export
buffers and file-loader values now release on ordinary and exception paths.

The generated registry constructs core widgets, then streams, then bridges.
This differs from header text order. In the actual FCFS fixture the audited
identities are `widget/0` (master), `widget/1` (loadmem), `widget/3` (clock),
`widget/4` (reset pulse) and `widget/5` (peek/poke). `widget/2` is the FASED
host driver and remains explicitly unsupported. Independent verification
parses the generated constructors in those three passes and checks every
captured configuration byte against the actual MMIO/geometry/maps. Unknown,
missing, extra or falsely supported owners reject. The InventoryFixture's
three concrete widgets are supported, but full requests still reject the
unsupported metasim runtime cut before initialization.

The next ownership work is concrete FASED profiling/configuration and output
file lifecycle (including histogram/range buffers and finish operations),
stream engines and their transfer buffers/cursors, and simulation
initialization/finalization/configuration. `runtime/simulation`,
`runtime/harness`, `runtime/execution-context` and `generated/rtl` load remain
unsupported. Reconstructing the parked dispatcher/DPI continuation and
published harness banks before the next edge remains necessary. After these
adapters, implement complete manifest/build-bound aggregate `.fsckpt`
publication and prevalidation, load a fresh VCS metasim before target
advancement, and compare target-visible outputs and transaction timing with
outstanding memory traffic.

The new component check compiles the actual five widget implementations with
a deterministic MMIO/time fixture. Native ASan/UBSan and fresh VCS DPI processes
match an independent Python oracle for every bus operation, response, GMP
value, configuration byte and result flag. All 26 cuts include before/after
timeout and unstable-value results, counter readout, reset init, file loading,
wide peek/poke, memory bursts and blocking/nonblocking steps. Both backends
pass 52 fresh continuations/650 operations, 260 owner comparisons before the
first fixture edge, and 2,470 malformed, changed-configuration, cross-type,
suspended, reentrant and interrupted-operation rejections per backend. The
fixture replaces platform MMIO and wall-clock services; these are concrete
host component tests, not whole FireSim restart acceptance.

Reproduction from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_widget_checkpoint_vcs \
  --out automations/checkpoint_loop/runs/m4-iteration18/widget-owners-final
python -m tools.checkpoint_formats.tests.verify_settled_boundary_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration18/settled-boundary-verified
```

The production settled verifier passes all five cuts: default operations
3/11/699275/699276 finish at 774,628 target cycles, and randomized operation
101 at 774,632. Each retains all 13,507,456 generated words, all four complete
4 MiB functional-memory channels and the five concrete widget payloads.
Complete 40-port AXI/FAME traces and outstanding generated observations are
byte-identical to their matching uninterrupted references. The late cut keeps
a native write at cycle 699360 and outstanding FASED target writes.

All prior checks pass: 27 Python/20 Scala tests, compiler codecs and emitted
memory coverage, existing native/VCS owner continuations, generated fixture
inventory, full M2/M3, ordinary clean RTL VCS, default/randomized GCD, standalone
FASED, the late native-traffic cut, four legacy cuts and two three-case worker
rejection-liveness suites. Profiled FCFS retains four samples at 774,629 target
cycles. All four production executables contain the new adapters. A symbol
check initially counted GCC's lowercase cold clones alongside the five public
functions; the corrected check passes and the failed log remains under runs.
Every VCS shell sources both environments then `vcs-env.sh` last, retaining
Y-2026.03-SP1, `-full64`, GCC/G++ 13 and `VCS_FLAGS=-Mupdate` for reused Make
builds. Final evidence rechecks complete traces, actual widget payloads,
component cuts and both input plan hashes.

Logs, exact command arrays and full artifact paths are recorded under
`automations/checkpoint_loop/runs/m4-iteration18/`. The first native trial
caught a misplaced helper declaration; the second trial caught VCS placing
`-lgmp` before objects under `--as-needed`. Corrected complete runs retain
both backends and every cut. Failed trial logs remain in `widget-owners/`
and `widget-owners-verified/`; neither is counted as a passing verification. The preliminary complete component
run was superseded by `widget-owners-final/`, which also preserves its
reference trace while writing negative fixtures to separate directories.

The relevant root DESSERT and Strober passages were read from their existing
text extractions under `runs/m2-iteration7/`: token/I/O timing and complete
state matter to exact continuation. Level-1 and Level-2 remain independent.
No required external dependency is missing. No whole-runtime restart, FPGA,
formal or ASIC activity/power acceptance is claimed. Both plans, conda files
and root PDFs remain untouched; no plan correction is proposed.
