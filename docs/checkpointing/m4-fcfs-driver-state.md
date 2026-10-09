# M4 concrete FCFS driver — iteration 23

M4 remains in progress. FCFS now returns a separate
`firesim.simulation.fcfs.v1` adapter for `runtime/simulation`. Other concrete
drivers retain default unsupported hooks. Harness banks, dispatcher/DPI
continuation, a supported whole-runtime restore phase, and aggregate `.fsckpt`
publication/loading remain outstanding. Full checkpoint requests fail closed.

The adapter binds the effective optional profiling interval, ordered counter
expectations including last-value duplicate argument handling and signed-to-u32
conversion, PeekPoke identity, ordered bridge/model identities and schemas,
and both complete model address maps. The constructor retains the original
unordered-map traversal in an explicit vector; ordinary counter-check MMIO and
error-output order are preserved and bound across fresh processes. Missing
readable counters or changes to bridge/model traversal reject explicitly.

Driver state is running/not-finalized at a completed synchronous operation.
The step and finalization guards reject suspended/reentrant calls and poison
interrupted operations. No capture is allowed during counter checking or after
finalization; there is no buffered driver output history at a valid cut. A fresh
load validates before mutation and performs no MMIO, profiling, file output,
callback execution or clock advancement. Live/repeated loads reject. The
adapter is a separate object because FCFS inherits checkpoint owners through
both simulation and scheduler; overriding their methods on the concrete driver
would incorrectly replace scheduler serialization too.

The base lifecycle, scheduler deadlines/callbacks, run-loop position, widgets,
generated RTL, functional memory and transport are independent owners. Restoring
this adapter alone cannot certify their consistency or initialize the runtime.
Profiling callbacks remain unaudited: driver-owner enumeration rejects them,
even though the effective interval is now bound by the concrete configuration.
FASED profiling itself retains its previously verified component adapter.
The outer `simif_emul_t::start_driver` initialization/fast-loadmem path still
needs a restore entry; the base adapter skips only its own initialization.

The component test compiles the actual production FCFS driver, simulation base,
scheduler, run-loop, FASED models, registry, PeekPoke and clock/master/loadmem.
The platform/target MMIO service is an independent fixture. Native ASan/UBSan
and fresh VCS DPI processes pass 46 continuations across every operation and
terminal success/error/timeout cuts, with 138 pre-edge owner comparisons and
296 MMIO calls matching an independent Python oracle. Finalized counters,
comparison failure output and final scheduler/loop/driver payloads agree.
Eight malformed fresh restores reject before any fixture edge or trace/state
publication. Each backend passes 2,972 rejections covering every truncated
prefix and every mutated payload byte, incompatible configuration/maps/model
counts, missing counters, changed registries, unaudited profiling callbacks,
live/repeated loads, recursive entry and interrupted MMIO/finalization.
Constructed FASED output files remain unchanged during load.

Initial trials exposed the multiple-inheritance dispatch problem and fixture
compile/unsupported-callback errors; they are retained as diagnostics and are
not passing evidence. `fcfs-driver-trial4/summary.json` is the first complete
passing component trial. Final results are in `fcfs-driver-verified/summary.json`
under `automations/checkpoint_loop/runs/m4-iteration23/`. The linkage audit's
initial literal symbol match omitted GCC's `[abi:cxx11]` tag; the corrected
schema-symbol check passes without changing implementation or test coverage.
The first additional production trial also used an incorrect full-trace oracle
between different exit statuses. Nonzero exit terminates directly in `dpi.cc`,
while success returns to RTL and emits one final sample. The corrected check
compares all shared error/success samples plus that explicit termination
difference, then requires complete byte-identical traces between successful
uninterrupted and captured runs with the same effective counter configuration.

Production diagnostic verification independently reconstructs the concrete
configuration from emitted constructors and checks that scheduler ownership
retains its own schema. It preserves complete generated/functional-memory
capture and the existing target transaction/timing comparison scope.

All 29 final verification scopes pass: 35 Python/20 Scala tests, compiler
codecs, every native/VCS component, full M2/M3, ordinary clean RTL VCS and
default/randomized GCD. All five settled cuts retain 13,507,456 generated words
and four full 4 MiB functional-memory channels; complete 40-port target traces
and generated observations are byte-identical to uninterrupted references.
Default/randomized completion remains 774,628/774,632 cycles, with native/FASED
traffic retained at the late cut. Profiled FCFS and both rejection-liveness
suites pass. Generated-hardware fresh component loads match all 515,923 samples.
Actual nonempty counter checks bind `totalWrites=2418` and `totalReads=7582`;
successful uninterrupted, early-cut and terminal-cut runs have identical full
traces at their own 774,631-cycle configuration. An absent counter rejects
before diagnostic publication. These are capture/component comparisons, not
fresh whole-runtime restoration. The independent final evidence audit passes.
Exact argv arrays, logs, evidence and all full artifact paths are recorded in
`verification-commands.json`, `final-evidence.json`, `source-integrity.json`
and `artifact-manifest.json` beneath the iteration's run directory.

Reproduction from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_fcfs_checkpoint_vcs \
  --out automations/checkpoint_loop/runs/m4-iteration23/fcfs-driver-verified
python automations/checkpoint_loop/runs/m4-iteration23/run-regressions.py
```

Every VCS shell sources both repository environments and `vcs-env.sh` last,
using Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make
`VCS_FLAGS=-Mupdate`. The relevant complete-state/memory and cycle-replay
passages of the two root papers were read from their existing extractions under
`runs/m2-iteration7/`. Level-1 and Level-2 remain independent. No physical FPGA,
whole-runtime restart, formal or ASIC activity/power acceptance is claimed.
Plans/conda/PDFs are preserved; no plan correction is proposed.

Next: restore harness banks and reconstruct the parked dispatcher/DPI
continuation at a supported clock phase; bind/prevalidate/load every generated
and software owner in one manifest/executable-bound `.fsckpt`; compare fresh
full VCS metasim outputs and transaction timing with outstanding native/FASED
traffic. FPGA-managed streams and unaudited concrete drivers remain unsupported.
