# Publish creator-affine owners under retained guards

Iteration 162 extends the optional pre-edge driver mailbox with a synchronous
owner publication step. `prepare_publication(callback)` stages the callback on
the controller after continuation preparation and before sealing. Callable
allocation failures leave the same reservation retryable. Final validation and
guard acquisition still run through `seal_launch`.

`publish_prepared()` runs the staged callback on the reserved creator while
retaining its publication guards. The callback commits its already prepared
owners and performs creator-side readback. Its captures are destroyed on that
creator before acknowledgment. The creator then parks under the same guards
while the controller publishes and reads back its remaining owners, RTL and
harness banks. A successful request needs no callable allocation, copying or
new thread. Empty, duplicate, foreign, recursive, unsealed and late requests
reject. Publication exceptions terminate before acknowledgment; skipping a
staged publication also terminates before continuation. Validation must happen
before entering this step, and publication callbacks must not throw.

Cancellation destroys continuation and publication captures before guards and
the resident resource, on the creator. Successful launch releases guards before
entering the continuation. Existing callers may omit staged publication.
`simif_emul_t::prepare_restored_publication` and `publish_restored_owners` expose
the step only for the same fresh driver under the loading hold with its launch
already prepared. Simulation entry, MMIO and ticks remain forbidden there.

This is a coordinator mechanism, not a complete Rocket state-owner transaction.
The new callback tests publish resident fixture state. The production TSI
component regression still commits its seventeen-owner candidate during initial
creator preparation; it has not yet moved that candidate into this sealed
publication phase. That wiring needs a retained prepared candidate and final
creator validation, followed by guarded commit/readback before other owners
are released. The existing component regression remains separate evidence.
The complete simulator/FAME/channel/CPU-managed-stream/bridge/memory/runtime
coordinator and production thread, signal, descriptor and parser exclusion
remain pending. The API does not suspend arbitrary process threads. Complete
Rocket Level 1 remains disabled. Independent Level 2 retains its complete
four-cut finite replay. BOOM and Saturn remain pending; standalone Shuttle,
physical FPGA validation and ASIC power are outside this increment.

Results and executable checks are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics remain under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/`.
