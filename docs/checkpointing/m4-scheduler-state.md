# M4 scheduler and callback owners — iteration 13

M4 remains in progress. The production `systematic_scheduler_t` now provides
component save/validate/load and explicit callback-owner enumeration. Native
ASan/UBSan and fresh VCS DPI processes reproduce its credits, callback order,
deadlines and separate callback state. A coherent metasim cut and fresh-process
FireSim restore remain outstanding; no external dependency is missing.

The adapter is in `sims/firesim/sim/midas/src/main/cc/core/systematic_scheduler.*`.
`firesim.scheduler.deadlines.v1` stores little-endian magic/version, optional
maximum-cycle horizon, default credit limit, current issued cycle, task count,
and each task's identity, callback-owner schema, initial deadline and next
deadline in registration order. Callback code, closures, pointers and C++
layouts are never serialized. The outer checkpoint must bind these component
payloads to its executable/build, integrity and complete owner manifest.

`register_checkpoint_task(id, first_cycle, callback, owner)` requires a stable
path-safe identity and a separately audited `checkpoint_owner_t` covering all
callback/closure state. `checkpoint_owners()` returns `runtime/scheduler` and
`runtime/scheduler/callback/ID` for every registered callback. The adapter must
outlive the scheduler. Duplicate IDs/owners, unsupported/self owners, empty
callbacks and invalid registration boundaries reject. Existing anonymous
`register_task` calls remain supported for ordinary simulation but make
checkpoint schema/save/validate/load/enumeration unsupported. No production
profiling callback or concrete driver has been newly declared audited.

Load parses and allocates every deadline before changing the scheduler. Wrong
schema/version, configuration/horizon, task count/order/identity/schema or
initial deadline, deadlines preceding issued/initial cycles, out-of-horizon
current cycles, truncation and trailing bytes reject without mutation. Hooks
never execute a callback or advance simulation. All separate callback owners
must also validate before the future coordinator loads any owner.

A callback may yield to RTL while executing MMIO. Checkpoint hooks, recursive
scheduler operations and registration reject during callback execution. A
throwing callback, zero interval or overflowing deadline poisons the scheduler;
subsequent checkpoint/advance attempts reject. This prevents claiming a
restorable boundary after a partially executed callback. Access still requires
the future coordinator to park both contexts; the adapter is not a concurrent
freeze mechanism and cannot restore a suspended C++ stack.

`current_cycle` records **issued scheduling credit**, which may precede
completion by the RTL simulator. A cut after credit issuance also needs the
corresponding driver and generated RTL step state. Scheduler payloads do not
certify a completed target cycle. Existing callback registration order and
non-overflowing credit behavior are preserved. Maximum-cycle parsing now
accepts the full unsigned 64-bit range and rejects malformed values; bounded
credit addition and callback deadline checks fail explicitly instead of wrapping.

`verify_scheduler_checkpoint_vcs` exercises the actual production scheduler
with two stateful callback owners, variable periods and coincident deadlines.
An independent Python oracle compares every credit, callback invocation/order,
issued cycle, counter and byte of all three owners. Eighteen cuts include
initial state, before/after callbacks and credit issuance, coincident callbacks
at scheduling cycle 43, the final horizon at 101, and completed scheduling.
Both native ASan/UBSan and VCS DPI run fresh processes for every cut: **36
continuations and 2,090 compared component operations**. Every owner
reserializes identically before the first edge and at the end. Native checks
reject **237** malformed scheduler payloads through both validation and load,
without mutation, and additionally check incompatible callback order/schema,
anonymous owners, callback reentrancy/failure, duplicate/invalid registrations,
zero/invalid horizons and a credit ending at `UINT64_MAX`.

Reproduce from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_scheduler_checkpoint_vcs \
  --out automations/checkpoint_loop/runs/m4-iteration13/scheduler-owner
```

All existing regressions pass: 24 Python and 20 Scala tests; compiler
codec/corruption and emitted-memory checks; MMIO/memory-owner 104 fresh
continuations/7,168 edges and memory-only 64 continuations/1,704 edges; generated
InventoryFixture coverage of all 539 words; full M2 (five fresh cases, 108
samples, 1,404 comparisons and negatives); full M3 (six matching captures,
547 stalls, five semantic and 242 transfer replay samples, eight invalid reads);
ordinary clean RTL VCS; and GCD VCS metasim at 12 target cycles. The full
10,000-transaction FCFS FASED fuzzer passes at 774,628 target cycles. Its three
complete outstanding-traffic captures retain the previous hash
`b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`.
All full preflight/save/restore requests still reject `widget/0` before driver
initialization and publish no incomplete checkpoint. Symbol checks confirm the
new scheduler hooks are linked in all four actual reused metasim executables.

The remaining runtime inventory in [m4-mmio-runtime.md](m4-mmio-runtime.md)
still applies. The scheduler timing fields now have an adapter; production
callback closures, simulation/main-loop phases and resumable driver boundaries
still need audits. The coordinator must capture generated FAME/LI-BDN/FASED and
bridge state together with AXI owners, full functional memory, harness latches,
clock/reset/DPI phase, PRNG/pending host delays, thread handoff, stream engines,
all driver owners and any external partition state. Fresh restore must bypass
initialization actions that overwrite loaded state, prevalidate all owners and
RTL handles, and load before target advancement. Full requests still fail
closed; this increment does not publish `.fsckpt` or claim whole-runtime
continuation or target-visible outstanding-memory equivalence.

Diagnostic commands, logs and artifacts are under
`automations/checkpoint_loop/runs/m4-iteration13/`. `verification-commands.json`
contains argv arrays, `regression-results.json` records checks that actually
ran, and `artifacts.json` lists evidence with absolute paths and hashes.
All VCS shells source both environments followed by `vcs-env.sh` last, retaining
Y-2026.03-SP1, `-full64`, GCC/G++ 13 and `VCS_FLAGS=-Mupdate` on reused Make
builds. The existing DESSERT token/DMA/snapshot and Strober snapshot/trace
sections were reread from root-paper text extractions under
`runs/m2-iteration7/`. No plan correction is proposed. Plans, conda files and
PDFs were preserved without staging, committing, resetting or cleaning.
Level-1 owners remain independent of Level-2 semantic checkpoints. No physical
FPGA, formal or ASIC gate-level activity/power validation is claimed.
