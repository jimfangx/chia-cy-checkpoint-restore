# Prepare the driver continuation before restore publication

Iteration 160 adds optional continuation staging to the existing pre-edge
creator mailbox. `emul_driver_thread_t::prepare_launch` installs a nonempty
continuation on an idle reservation without waking its worker. Construction
and copying of its `std::function` happen before installation. A failed
allocation leaves the same creator available for retry. Duplicate staging,
empty tasks, foreign/worker calls and legacy launch over a staged task reject.
Synchronous preparation callbacks remain available after staging, including
retryable exceptions and final owner validation.

`launch_prepared` moves the installed continuation into the mailbox and wakes
the existing worker. It is `noexcept`, creates no thread and allocates no
callable. A broken controller/state contract terminates the process. This is
the post-publication operation; it must never return a retryable failure from
a partially published restore. Cancellation destroys the staged captures on
the creator before destroying its retained resource bundle. Launch uses the
same destruction order after the continuation finishes.

`simif_emul_t::prepare_restored_launch` exposes this under the existing loading
hold for the same fresh driver and its reserved creator. It constructs both
the dispatcher task and its optional boundary callback before owner loading.
Arming and harness bootstrap still independently validate the loaded owners,
clock phase, reset and finish flags. Only then does startup consume the staged
continuation. The legacy paths remain available and are tested separately.
Checkpoint scheduling must be configured before staging: changing polling or
operation scheduling afterward rejects so the prepared boundary callback cannot
silently disagree with the live policy.

The staged callable, destination pointer and native thread are bootstrap
resources reconstructed by the fresh destination. They are consumed before
normal driver execution and are not new serialized CPU state owners. Capture
while loading remains prohibited by the existing hold.

Native ASan/UBSan and VCS test thirty-two staged lifetimes per backend, with
sixteen launches, sixteen cancellations, thirty-two allocation failures before
installation, preparation exceptions after installation and 208 lifecycle
rejections. All sixteen commits run with controller-side allocation failure
enabled. Staged captures are destroyed on the worker before its retained
resource in both launch and cancellation cases. The actual VCS harness tests
ten staged fresh continuations at five cuts, including terminal zero-edge
continuation, allocation-failure retry, foreign/recursive/duplicate and late
schedule rejection,
complete native/generated pre-edge readback and original-cycle continuation.
Both legacy harness modes are retained. The independent auditor checks the
new receipts as well as the existing owner and cycle comparisons.

This supplies a prepared dispatcher launch resource for a future complete
coordinator. It does not implement joint publication of the Rocket simulator,
FAME/channels, CPU streams, bridges, memory and runtime. Production process-wide
thread/signal/descriptor/parser exclusion remains pending. CPU-managed streams
and empty-schema owners still reject. Complete Rocket Level 1 stays disabled;
Level 2 remains independent. No FPGA or ASIC-power validation is claimed.

Exact native commands, source snapshots and results are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/`.
