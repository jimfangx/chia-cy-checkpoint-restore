# Driver creator reservation under the pre-edge hold

Iteration 158 adds an optional creator mailbox to `simif_emul_t`. After the
existing `begin_restored_load(sim)` admission succeeds, the coordinator may call
`reserve_restored_creator(sim)` and `prepare_on_restored_creator(sim, callback)`.
Preparation runs synchronously on the eventual driver thread. Arming and the
existing harness bootstrap launch the simulation continuation on that same
thread; they do not replace it with another worker. Ordinary startup and callers
that do not reserve a creator retain their existing paths.

The mailbox admits only the reserving controller. Empty, repeated, recursive,
foreign-thread and post-launch submissions reject. Callback exceptions return
to the controller while the same worker remains reserved for a retry. Callback
captures are destroyed on the creator before completion is acknowledged. An
unused reservation is cancelled and joined during simulator destruction; a
running simulation still requires the existing finish/join lifecycle.

The loading hold rejects production MMIO reads/writes and `do_tick`, including
calls from a preparation callback. The worker cannot run the simulation flow
until bootstrap. Failed bootstrap consumes the destination and retains MMIO/
tick exclusion even after its pending-driver pointer has been cleared. The
native poison test covers both reserved and unreserved destinations for every
invalid clock/reset/finish/bank shape, preserving all five loaded native owners.

The actual harness test optionally reserves the creator before loading native
owners, parks clocks beyond multiple normal periods, restores and reads back
generated RTL, harness banks and all seven native owners, then bootstraps.
Preparation checks real MMIO entry points, recursive/foreign requests and a
retryable exception; driver steps and finalization check the creator identity.
Both separate-owner and aggregate restore paths retain the original five cuts,
terminal zero-edge continuation and all malformed/lifecycle cases. Both legacy
paths run too. The production TSI bridge component matrix also uses this same
mailbox to prepare, publish, service and destroy its real restricted provider.
Its serial MMIO peer remains a component fixture, and its operation labels are
not Rocket target-cycle labels.
In iteration 158 that provider's lifetime finished inside the mailbox callback;
the harness separately proved driver launch on the reserved worker. Iteration
159 adds [creator-owned lifetimes](driver-creator-lifetimes.md) and tests the
live provider through component launch and cancellation. Joining it to the
complete CPU cut remains pending.

This supplies a worker rendezvous, not complete CPU restore admission. Existing
CPU-managed-stream and empty-schema-owner rejections remain unchanged; the TSI
bridge aggregate schema remains empty. No `.fsckpt` contains a native thread or
stack address. Only owned byte observations may cross between the creator and
VCS; provider/candidate lifetimes and process-wide thread, signal, descriptor and
parser exclusion still require the complete coordinator. The new API does not
supply that exclusion or jointly publish simulator peers with the TSI candidate.
Preparing/launching a `std::function` can allocate. A complete coordinator must
prepare its launch resources before joint publication; a later bootstrap failure
must remain process-fatal under the clock hold, never release a partial restore.
Iteration 160 adds an optional [prepared dispatcher continuation](driver-prepared-launch.md)
to move its callable allocation before publication. Joint simulator publication
and production process exclusion remain pending.

Next: connect creator-side bridge preparation and immutable observations to the
complete simulator/FAME/channel/other-bridge/functional-memory/runtime cut,
validate every owner before any publication, and add production process-wide
exclusion before enabling Rocket Level 1. Level 2 remains independent. Exact
receipts and executable commands are in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).
Diagnostics remain under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/`.
