# Retain creator guards across restore publication

Iteration 161 adds an optional sealed phase to the pre-edge driver mailbox.
After staging the continuation, `emul_driver_thread_t::seal_launch(factory)`
runs final validation on the reserved creator. The factory returns an owned
guard bundle. The worker retains it while the controller publishes and reads
back native owners, generated RTL and harness banks under the loading hold.
Successful sealing rejects further preparation, continuation replacement and
duplicate seals. Empty factories/guards, foreign and recursive calls reject.
A throwing factory unwinds its guards and leaves the same reservation retryable.
Factories must acquire exclusion before validation and return only after all
creator-side checks succeed.

`launch_prepared()` consumes either the existing unsealed reservation or this
sealed reservation without allocating a callable or creating a thread. The
creator destroys its publication guards before entering the continuation, so
creator-affine mutexes and signal masks do not escape into normal execution.
Cancellation destroys staged captures first, then publication guards, then the
resident owner bundle, all on the creator. Guard destructors must not throw or
allocate; a broken post-publication contract is fatal. An abandoned sealed
reservation cancels and joins during mailbox/simulator destruction.

`simif_emul_t::seal_restored_launch(sim, factory)` exposes the operation only
for the same fresh driver under the loading hold with its launch already
staged. Existing independent arming, clock-phase, reset/finish and loaded-owner
checks remain active. Loading and poisoned destinations still reject MMIO,
ticks and simulation entry. The guard bundle is fresh destination bootstrap
policy, not serialized CPU state or a native thread/stack in an image.

Native ASan/UBSan and VCS each exercise 32 sealed lifetimes: 16 launches and
16 cancellations; 64 guards including failed final validation; 64 controller/
creator allocation failures; and 416 lifecycle rejections. A real mutex stays
owned by the creator during controller publication and rejects a competing
thread's access. A real creator SIGUSR2 mask is restored before continuation;
failed validation also restores the mask and unlocks the mutex before retry.
Launch runs with controller allocation failure enabled. Cleanup checks the
creator and ordering relative to the retained resource. VCS asserts time zero
and zero edges.

All four actual VCS harness modes remain tested. Ten reserved fresh
continuations additionally seal a creator-owned mutex, reject nine late/invalid
operations each, and test a throwing final validator. Both the separate-owner
and aggregate paths keep that mutex held during native publication, generated
RTL/harness deposit and complete pre-edge readback. DPI checks observe it before
deposit and after readback; every driver step and finalization verifies release
before execution. The five existing cuts, including the terminal zero-edge cut,
retain complete readback and original-label continuation comparisons. The
independent creator auditor requires these additional scope/order receipts.

The mutex and signal-mask scenarios test guard lifetime, not production
process-wide exclusion. The complete coordinator must still supply and enforce
the actual all-thread, signal-action/pending, descriptor and parser policy and
join all simulator/FAME/channel/stream/bridge/memory/runtime owners at one cut.
This API cannot make arbitrary external threads cooperative or replace the
required state-owner audits. CPU-managed streams and empty-schema owners still
reject; the TSI aggregate schema stays unsupported. Complete Rocket Level 1
remains disabled. Level 2 remains independent. BOOM/Saturn remain pending;
standalone Shuttle, physical FPGA validation and ASIC power remain outside scope.

Exact receipts, source archives, commands and regression results are in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/`.
