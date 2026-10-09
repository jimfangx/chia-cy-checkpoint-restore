# M4 aggregate prevalidation — iteration 28

M4 remains in progress. One manifest/executable-bound `.fsckpt` now restores
all generated, harness, and native/driver owners in the audited harness
dispatcher fixture profile. Production `+fs-checkpoint`/`+fs-restore` still
fail closed. Fresh production FCFS/FASED restart with outstanding traffic
remains the milestone acceptance work.

`aggregate.py` uses the existing checksummed canonical FSCKPT v1 container.
The runtime manifest binds its exact low-clock returned-operation phase,
profile/configuration, generated inventory, harness geometry/source, native
implementation hash, and ordered owner IDs/schemas. The build also binds the
actual simulator executable. Generated words, harness words, and opaque native
bytes occupy separate namespaces. Target cycle, host sample, and driver
operation are distinct; the fixture's target cycle is checked against its
actual active target edge count, rather than its operation number.

Checksum, executable/build, manifest, complete membership, shape, low generated
clock outputs, and reset/finish validation all precede staging creation or
overwrite. The single aggregate staging file is a trusted local intermediary,
like the existing component staging files; it is not independently checksummed
and must be generated locally from the validated durable container.

`aggregate_restore_t` reads that staging into memory and validates the complete
enumerated native inventory against its compiled profile table, every native
payload, and both generated/harness VPI tables before loading any owner.
Commit uses retained payloads/handles, without rereading component files.
Every native owner is read back immediately after load. The coordinator is
consumed on any preparation/commit failure, including an exception; the caller
must terminate the failed process. RTL banks settle and both complete readbacks
finish before the existing actual DPI publication/input refresh/bootstrap.

`simif_emul_t::begin_restored_load` reserves the fresh harness clock hold before
loading any state. Entry can return and let generated clock nets settle, while
no worker, MMIO, native tick, or rising edge starts. The same driver is armed
only after all native/RTL prevalidation and native loading/readback. Unsupported
owners, nonincremental drivers, managed streams, QSFP, excessive channels,
diagnostics, loaded/live/repeated destinations and ordinary/direct fallback
reject. This is a component coordinator API; no production restore plusarg is
enabled.

The actual VCS integration passes five fresh aggregate continuations at fixture
operations 13/14/16/31/32. All 55 complete generated/bank/output samples match
uninterrupted execution, all 35 native comparisons match before the first edge,
and final native state plus remaining host/active target edges match. Each
checkpoint preserves all 539 generated words, 29 harness words, seven native
owners, full 4 KiB functional memory, a partial write and two held read responses.
The terminal checkpoint finishes with zero host/target/native edges. The driver
MMIO remains a fixture; there is no production FASED model in this fixture.

Thirty-five malformed native payloads and thirty-five late-section/framing/schema/order
faults reject with zero deposits, no native loads, unchanged native owners and
zero driver calls. Unsupported drivers also reject before mutation. Twenty
unsupported/bootstrap lifecycle processes, 25 arming guards and 15 reservation
guards run. The independent artifact audit checks 100 distinct simulator
processes, container integrity/executable binding, target-cycle indexing, every
generated/harness/native record and the independent operation/edge oracle.
The separate ASan/UBSan reservation test passes 58 rejections and 18 unchanged
native owner comparisons, with zero workers/edges across ten destinations.
All 40 Python format/inventory/replay tests pass.

All 44 executed verification scopes pass, including all 41 prior scopes and
the three new aggregate/reservation scopes. The retained checks cover 20 Scala
tests, all native/VCS component owners, ordinary clean RTL VCS, full M2/M3,
GCD/FASED, profiling, both rejection-liveness suites and real nonempty counter
expectations. Existing fresh harness continuations match 483,409 samples.
Five production low-clock cuts retain every one of 13,507,456 generated words
and four complete 4 MiB channels; complete 40-port traces match uninterrupted
execution at 774,628/774,632 target cycles with outstanding native/FASED traffic.
All seven negative requests and terminal capture pass. The paired audit checks
80 software owners and 67,537,280 generated words, allowing only historical
reporting timestamps and two falling clock-gate outputs. The separate active
terminal harness fixture retains exactly 12 host/12 target edges. Production
runs remain capture/continuation diagnostics, rather than fresh aggregate
FCFS/FASED restart acceptance.

Initial diagnostics are preserved separately. The first attempted generated
VPI prevalidation during entry, before generated clock nets settled; it rejected
without any owner load or deposit. A second successful continuation exposed a
test variable shadowing a capture with a memory header; the final tests use
distinct names. The first reservation sanitizer test constructed a driver with
an empty widget registry, which asserted before testing reservation; its fixed
test uses the fixture's complete registry. None is counted as a passing scope.

Reproduce from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_harness_dispatcher_vcs \
  --aggregate --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration28/aggregate-final
python automations/checkpoint_loop/runs/m4-iteration28/audit-aggregate.py
PYTHONPATH=. python automations/checkpoint_loop/runs/m4-iteration28/verify-loading-reservation.py
```

Exact regression commands/logs and full-path artifact catalogs are under
`automations/checkpoint_loop/runs/m4-iteration28/`. VCS uses Y-2026.03-SP1,
`-full64`, system GCC/G++ 13 and the prescribed helper sourced last. Plans,
conda files and PDFs remain untouched and unstaged; no commit/reset/clean.
Level-2 checkpoints remain independent. No physical FPGA, formal or ASIC
gate-level validation is claimed.

Next: enable a complete audited production FCFS profile and connect durable
aggregate capture/loading to its normal runtime. Bind libraries/configuration
and every native/generated/harness/widget/scheduler owner at the existing
coherent low-clock cut, preserve reporting/finalization semantics, then compare
a fresh full production VCS metasim process against uninterrupted execution
with outstanding native/FASED traffic and complete target transaction timing.
Production entry currently rejects restore before constructing the concrete
simulation in `sim/midas/src/main/cc/entry.cc`; its supported branch will need
to construct that driver, enumerate AXI/timing/driver/scheduler/widget owners,
reserve the clock hold and run this preparation/readback/bootstrap sequence.
Use the completed-operation low-clock capture hooks in
`emul/simif_emul.cc` and `core/driver_boundary_diagnostic.cc`. Preserve every
RAM word while scaling container validation and retained VPI preparation to
the production entry-based 13,507,456-word inventory; the flat per-word fixture
container has not yet been checked at that size. Bind production target-cycle
indexing independently of scheduler credit and native/host reset offsets.
