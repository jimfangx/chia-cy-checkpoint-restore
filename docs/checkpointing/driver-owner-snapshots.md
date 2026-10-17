# Driver-thread owner snapshots

Iteration 155 adds an immutable observation handoff to the production settled
driver diagnostic. `simif_emul_t::capture_driver_boundary()` freezes each
supported software owner on the driver thread while VCS is parked in DPI.
It validates complete payloads and checks schemas and bytes again after all
owner callbacks. Empty or duplicate identities, aliased owners, invalid images,
changing schemas and unstable payloads reject before publication. Unsupported
owners retain their explicit empty-schema inventory records.

Only names, schemas and owned bytes cross the existing settled mutex/condition
variable boundary. Frozen records retain no original owner, validator, optional
slot or creator reference. The VCS callback adds its settled harness observation
and serializes the combined diagnostic without calling the original software
owners. Snapshot loading always rejects, including an identical image. The
diagnostic format and existing owner schemas are unchanged. Ordinary diagnostics
use the same collection/validation implementation.

The handoff requires external quiescence of the captured owners. In production
the driver remains parked until VCS releases the boundary; the snapshot itself
does not stop threads, block signals or prevent concurrent mutation. Capture
occurs before the natural clock settlement. Native AXI software state is not
advanced during that settlement; generated RTL and harness banks are still
observed at the settled boundary. Target-cycle labels remain distinct from
completed host-operation numbers.

The actual TSI test constructs and prepares a restricted TSI on a worker,
freezes all sixteen public owner views on that creator, and reads the bytes
on the main VCS/DPI thread. Direct access to the same live views must reject.
It compares both parked and post-destruction readbacks with the independent
retained context oracle, checks creator retries, denies invalid images and
mutable loads, and injects every successive snapshot allocation failure before
successful publication. This component test adds no target edges or coroutine
entries. The separate production FCFS settled checks compare complete generated
state and target transaction timing with uninterrupted execution at both clock
phases, including outstanding traffic and terminal cuts.

The final receipt seals a separate complete source-input catalog. Its independent
auditor rejects all six missing/duplicate receipt variants and every one of the
96 individual source-binding omissions. The first auditor missed an omitted
auxiliary header; that failure stays diagnostic. The corrected checker and
fresh handoff execution form a second source epoch after the full native CPU
controls finished their live-source checks. Native C++ and build settings are
identical across both epochs; original execution snapshots remain intact.

Complete Rocket Level 1 remains disabled. The TSI bridge still has no complete
aggregate checkpoint schema; this change does not add its context images to
the simulator inventory or prepare/publish a fresh TSI on the new driver thread.
Next: integrate creator-side TSI preparation/publication with simulator restore,
coordinate actual process-wide thread/mask/action/signal access, and capture
all simulator/FAME/bridge/functional-memory owners in a coherent CPU cut.
Level 2 stays independent. BOOM and Saturn remain pending; standalone Shuttle,
physical FPGA validation and ASIC power are outside this increment.

Exact receipts and executable native commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostic artifacts stay
under `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration155/`.
