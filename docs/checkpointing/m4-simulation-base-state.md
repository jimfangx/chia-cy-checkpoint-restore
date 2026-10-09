# M4 simulation base lifecycle — iteration 22

M4 remains in progress. `runtime/simulation/base` now uses the explicitly
limited `firesim.simulation.base.v1` adapter. `runtime/simulation` still
identifies the unaudited concrete driver and remains unsupported. Aggregate
`.fsckpt` publication/loading, harness banks and dispatcher/DPI continuation
remain outstanding. Production full-checkpoint requests still fail closed.

The adapter binds all effective base configuration: zero-memory and fingerprint
flags, fingerprint value, incremental-dispatch capability, target-name field,
effective load-memory path (including `+fastloadmem` clearing it), and ordered
widget identities/schemas. It owns initialized/running status, the last step's
completion flag, and historical wall-clock/host-cycle performance baselines.
Before finalization, end time/cycles are canonical zero/absent. There is no
buffered base output history: initialization messages have already been emitted
and are not emitted again; final status and performance reporting have not
started. Bridge/concrete-driver file histories remain their separate owners.

Only complete incremental-operation boundaries in the running phase can be
saved. Initialization, suspended/reentrant host calls, finalization, completed
flows and any interrupted flow reject. Validation compares the entire effective
configuration, exact length and canonical lifecycle flags before mutation.
Loading requires a fresh constructed flow, performs no timestamp sampling,
MMIO, file output or clock advancement, and cannot overwrite a live flow.
An interrupted operation or coordinator callback poisons the flow; it cannot
be checkpointed, reloaded or retried. Copying a simulation is disabled because
its adapter holds a reference to its owner.

`execute_simulation_flow` now skips initialization after a base restore and
dispatches the next operation. A cut after the terminal step skips further
dispatch and enters finalization directly. The ordinary initialization,
operation, finalization, bridge-finish and report order is preserved. The
coordinator must separately restore every driver/widget/hardware owner before
entering this flow; the component adapter certifies none of those owners.
`simif_emul_t::start_driver` still has its separate pre-flow fast-load-memory
path; a full restore coordinator must bypass that path and ordinary runtime
initialization. This base adapter does not reconstruct that outer lifecycle.
Historical wall-clock baseline serialization preserves reporting data, not
deterministic elapsed-time output; a restart includes downtime in the existing
performance calculation. Target-cycle counts never derive from wall time.

Component verification compiles the actual `simulation_t`, registry, stream
engine, bridge methods and clock/master/loadmem implementations. Platform MMIO,
clock service and concrete driver are independent fixtures; driver position is
restored separately. Native ASan/UBSan and fresh VCS DPI processes compare the
complete MMIO operation order against a Python oracle, exact base payloads
before the first fixture edge, and success/error/timeout finalization. All four
operation cuts include the terminal cut. Results: 24 fresh continuations,
264 matched MMIO calls, 24 pre-edge base comparisons, eight malformed fresh
loads rejected without trace/state publication, and 1,911 rejections per
backend. Rejections cover every byte truncation, every configuration/lifecycle
byte mutation, wrong arguments/registry/capability, repeated/live loads,
recursive flow entry and interruptions in initialization, operation,
finalization, end-counter reads, bridge finish and coordinator callbacks.
The first VCS link trial omitted `--no-as-needed` for GMP; it failed and is
retained separately. The corrected link trial passed; the verified run includes
the expanded interruption suite. No failed trial is passing evidence.

Production diagnostic checks independently bind this base payload to the full
ordered widget registry and cross-check its completed-step flag against the
FASED run-loop owner, including terminal timeout capture. All 26 regression
scopes pass: the previous 25 and complete generated RTL loading. These include
35 Python/20 Scala tests, compiler codecs, every native/VCS owner continuation,
full M2/M3, ordinary clean RTL VCS and default/randomized GCD. All five production
settled cuts retain 13,507,456 generated words and four full 4 MiB memory
channels. Complete 40-port AXI/FAME traces and generated observations match
uninterrupted references. Default/randomized completion remains
774,628/774,632 target cycles; the late cut retains an in-flight native write
and outstanding FASED traffic. Profiled FCFS preserves four samples at 774,629
cycles; both rejection-liveness suites pass. All three generated-hardware fresh
continuations match 521,695 samples, with all 539 words checked before the
first edge, 557 VCS atomic rejections and 333 native sanitizer rejections.
These preserve component/capture/timing behavior and do not establish whole
FireSim restart acceptance. Exact results, argv arrays and the full-path
artifact catalog are under `automations/checkpoint_loop/runs/m4-iteration22/`.

Reproduction from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_simulation_checkpoint_vcs \
  --out automations/checkpoint_loop/runs/m4-iteration22/simulation-base-verified
python automations/checkpoint_loop/runs/m4-iteration22/run-regressions.py
```

Every VCS shell sources both repository environments and `vcs-env.sh` last,
using Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make
`VCS_FLAGS=-Mupdate`. There is no missing external dependency. The relevant
DESSERT/Strober complete-state/memory and cycle-by-cycle output-replay passages
were read from the root-paper extractions under `runs/m2-iteration7/`.
Level-1 and Level-2 remain independent. No physical FPGA, whole-runtime restart,
formal or ASIC activity/power acceptance is claimed. Plans/conda/PDF files
remain untouched; no plan correction is proposed.

Next: audit the concrete FCFS driver's expectation configuration and finalization
state, restore harness banks and reconstruct the parked dispatcher/DPI
continuation at a supported clock phase, then bind/prevalidate/load every
generated/software owner in an aggregate manifest/executable-bound `.fsckpt`.
Compare fresh full VCS metasim target outputs and transaction timing with
outstanding native and FASED traffic. FPGA-managed streams remain unsupported.
