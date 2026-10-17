# Creator-owned resources across restored driver launch

Iteration 159 adds one optional creator-owned resource bundle to the existing
pre-edge driver mailbox. `emul_driver_thread_t::retain` accepts a nonempty
`unique_ptr<resource_t>` only from its worker during a synchronous preparation
callback. A second bundle, an empty bundle, and controller, foreign-thread or
post-launch submissions reject. The caller constructs the bundle on its creator;
the controller receives only immutable observations. A coordinator can put all
of its creator-affine owners in this single bundle.

`simif_emul_t::retain_on_restored_creator` additionally requires the existing
restore loading hold for the same simulation. It does not change owner/schema
admission. Preparation exceptions leave an installed bundle alive on the same
reserved worker for retry. A failed, unpublished preparation can instead cancel
the destination. Cancellation joins the worker after destroying its bundle.
After launch, the bundle remains alive through the complete driver continuation.
The worker destroys continuation captures first, then the bundle, before join
returns. Cleanup runs without the mailbox mutex held and destructors must not
throw. As before, a launched simulation must finish and join before destruction;
this API does not unwind an actively running simulation.

The native sanitizer/VCS mailbox matrix checks retained resources across
retryable exceptions, launch and cancellation, thread identity, occupied-slot
rejection and capture-before-resource destruction. Both reserved actual harness
modes retain a bundle through every driver step and finalization, including a
terminal zero-edge continuation, then prove creator-side destruction before
simulator teardown. Both legacy harness modes still run.

The production TSI bridge component matrix now owns its actual MMIO peer,
load-memory driver, bridge and restricted provider in a retained bundle.
Preparation publishes and reads back the same seventeen component owners as
before. Launch reads them all back again before the first MMIO operation, then
services the live provider on its original worker. Fresh cancellation cases at
every selected early, active and terminal component cut destroy the live provider
without servicing it. The independent auditor checks both readback epochs,
complete serial-operation boundaries, cancellation membership, cleanup ordering,
invalid images and first-divergence faults. The MMIO device is still a serial
fixture; these labels are host operations, not Rocket target cycles.

This closes the component lifetime gap between creator preparation and launch.
It does not join the TSI provider to the full Rocket simulator cut or grant
complete Level-1 support. CPU-managed streams and empty-schema owners still
reject; the TSI bridge aggregate schema remains empty. Complete simulator/FAME/
channel/other-bridge/functional-memory/runtime validation and production
process-wide thread, signal, descriptor and parser exclusion remain pending.
The coordinator must prepare every fallible launch resource before joint
publication. Post-publication bootstrap failure must stay process-fatal under
the clock hold. Level 2 remains independent.

Exact receipts, source archives and executable commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics remain under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/`.
