# M4 FCFS run-loop owner — iteration 15

M4 remains in progress. The production FCFS FASED driver now keeps its run-loop
continuation in an explicit component owner. Fresh native ASan/UBSan and VCS
DPI processes pass continuation at every completed host-operation boundary
against the former nested-loop operation order. This does not establish a
coherent FireSim runtime cut or fresh-process target-cycle restoration. No
external dependency is missing.

`sims/firesim/sim/midas/src/main/cc/core/stepped_run_loop.{h,cc}` implements
`firesim.stepped-run-loop.v1`. Its 48-byte little-endian payload contains
magic/version, bridge count, next phase, next bridge index and target `done`.
The phases are horizon check, scheduled callbacks, credit/step issuance,
nonblocking completion polling, individual bridge ticks, target-done sampling
and completion. Credit issuance and its nonblocking PeekPoke write form one
guarded operation. Neither credit nor the driver's phase proves that the RTL
has completed the issued cycles; the scheduler, PeekPoke RTL and harness remain
separate owners.

`sims/firesim/sim/src/main/cc/fasedtests/fasedtests_top.cc` now executes this
dispatcher. Each call completes at most one original host operation, preserving
the order of callbacks, step write, polls, each registered bridge and target
sampling. It stores bridge traversal order after registry construction. The
current `simulation_run()` still drives the dispatcher synchronously to
completion; a coordinator must add a boundary hook or incremental driver
entry before it can request/park at these boundaries. The component API alone
does not implement an accessible whole-runtime checkpoint request. It
does not insert RTL edges, drain target memory traffic or reconstruct suspended
MMIO stacks. The original constructor-local profiling interval was captured
by reference after its lifetime ended; it is now captured by value. Production
profiling callbacks and FASED profiling/file state remain unaudited.

The new virtual `simulation_t::checkpoint_driver_owners()` inventory retains
an unsupported `runtime/simulation` owner. The FCFS override appends scheduler
and audited callback components plus `runtime/simulation/fased-run-loop`.
This inventory is a subset of the runtime. Bridge count alone does not bind
bridge identity/order or configuration: the future coordinator must validate
the full generated/driver/build manifest, every owner and their relationships.
Initialization, memory loading, final event checks, performance baselines and
other concrete driver fields remain unsupported. No whole driver is newly
declared checkpointable, and full requests still fail closed.

All save/validate/load and recursive advancement/status access reject while a
service operation is active, including when it suspends on MMIO. A throwing
operation poisons the loop because its external effect may already have
committed. No subsequent capture/load/retry is permitted. These flags certify
a local operation boundary only; both execution contexts must still be parked
by external synchronization. The dispatcher is not itself a freeze coordinator.

Load validates the entire fixed payload before replacing any state. Wrong
geometry/magic/version, truncation/trailing bytes, incompatible bridge count,
invalid phase/Boolean/index and `done` outside completion reject atomically.
The payload contains no callbacks, object pointers, thread objects or stacks.
The services interface is rebound by constructing the production driver; its
own scheduler, devices and state are not serialized by this component.

`verify_stepped_loop_checkpoint_vcs` uses the actual production dispatcher and
scheduler with separately owned test services. An independent Python oracle
executes the original nested while-loop ordering; completed cycles advance
independently of issued credit. Cases cover three bridges and no bridges,
completion with unconsumed credit, horizon completion and a zero-cycle horizon.
Every operation boundary (including each bridge index) is restored in a fresh
process. All three owners validate before any load, reserialize identically
before the first component edge and match all final owner words.

Both backends pass **372 fresh continuations / 10,810 compared operations**,
including **270 cuts with pending credit**. Each backend rejects **467**
malformed payloads without mutation and tests **17** interrupted phases plus
suspended/reentrant save/validate/load/advance/status guards. **20** malformed
fresh restore processes reject before opening a trace or advancing an edge.
The DPI test exits explicitly with failure because VCS can return success after
`$fatal`. These are component edges, not target-cycle metasim restart evidence.

All existing regressions pass: 24 Python/20 Scala tests, compiler codec and
corruption/emitted-memory checks, host timing 136 fresh continuations/861,432
operations, scheduler 36/2,090, MMIO/memory 104/7,168 edges and memory-only
64/1,704 edges; all 539 InventoryFixture words; full M2 and M3 (including
547 stalled boundaries and invalid reads); ordinary clean RTL VCS; and GCD
metasim at 12 target cycles with default and four timing/seed configurations.
Six invalid timing configurations reject before initialization. The complete
10,000-transaction FCFS fuzzer passes at 774,628 target cycles; its three
complete outstanding-traffic captures retain SHA-256
`b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`.
All full preflight/save/restore requests reject `widget/0` before initialization
and publish no incomplete checkpoint. New run-loop plus existing scheduler
and timing symbols are linked in all four actual metasim executables; the
FCFS driver has the new inventory and service methods. The symbol check
accounts for the C++ ABI tag in the inventory method's demangled name.

A separate production profiling run also completes all 10,000 transactions
at 774,629 target cycles with `+profile-interval=250000` and four CSV samples.
The configured scheduler pauses differ from the default run, so these two
completion counts are recorded separately. Sampled read/write/beat counters
are monotonic and show traffic. This exercises the interval-lifetime fix;
it does not compare checkpointed execution or certify profiling state for
restore. Results: `integrated-loop-summary.json` and `fased-profile/run.log`.

Reproduce from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_stepped_loop_checkpoint_vcs \
  --out automations/checkpoint_loop/runs/m4-iteration15/stepped-loop-owner
python automations/checkpoint_loop/runs/m4-iteration15/run-regressions.py
python automations/checkpoint_loop/runs/m4-iteration15/check-integrated-loop.py
python automations/checkpoint_loop/runs/m4-iteration15/final-integrity.py
```

The full regression commands and diagnostics are under
`automations/checkpoint_loop/runs/m4-iteration15/`. Every nested VCS shell
sources both repository environments then `vcs-env.sh` last, retaining
Y-2026.03-SP1, `-full64`, GCC/G++ 13 and `VCS_FLAGS=-Mupdate` on reused Make
builds. The DESSERT deterministic token and Strober exact snapshot/I/O replay
sections were reread from the root-paper text extractions under
`runs/m2-iteration7/`. No plan correction is proposed. The production FCFS
source is under `sim/src/main/cc/fasedtests/`, correcting the path shorthand
in the previous iteration note; the plans remain read-only.

Next: expose incremental driver dispatch to the coordinator, audit the
harness's delayed AXI records and clock/reset/DPI phase and
define a coherent settled boundary with both contexts parked. Complete the
simulation initialization/run/finalization and PeekPoke/master/clock/loadmem/
FASED/stream-driver owners. Capture generated RTL, full functional memory,
AXI queues, timing, scheduler and driver components in one build/manifest-bound
`.fsckpt` without draining target traffic. Prevalidate every owner and RTL
handle before any fresh-process load or target advance, then compare outputs
and transaction timing with outstanding memory traffic. Remaining inventory:
[m4-mmio-runtime.md](m4-mmio-runtime.md), with scheduler and timing updates in
[m4-scheduler-state.md](m4-scheduler-state.md) and
[m4-host-timing-state.md](m4-host-timing-state.md).

Level-1 owners remain independent of Level-2 semantic checkpoints. No full
Level-1 acceptance, physical FPGA, formal or ASIC gate-level activity/power
validation is claimed. Plans, conda files and PDFs are preserved without
staging, commit, reset or clean.
