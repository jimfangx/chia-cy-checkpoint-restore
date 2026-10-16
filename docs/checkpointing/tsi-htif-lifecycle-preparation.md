# HTIF lifecycle preparation and peer publication

Iteration 133 adds destination-aware preparation to the opt-in lifecycle
provider. This is a host-component primitive for future aggregate restore.
The twelve-owner polling aggregate and complete CPU admission remain unchanged.

`firesim_tsi_htif_lifecycle_t::prepare_checkpoint(image)` parses the complete
component and checks the actual destination's private exit/stopped fields,
signature policy and signal guards without publishing state. The returned
candidate owns its parsed values, binds one destination, cannot be copied or
moved, and can be committed once. Destroying an unpublished candidate performs
no service or assignment. The HTIF destination must outlive its candidate.
`validate_checkpoint()` remains a format-only check.

`candidate.commit(publish_peers)` repeats all provider checks immediately
before calling the supplied `noexcept` publisher. That callback may only
publish already prepared peers and must not access HTIF or signal state.
The remaining actual provider assignments cannot allocate or throw. Failed
guards run before either peers or lifecycle fields change; a consumed
candidate rejects before invoking the publisher again. The ordinary component
`load_checkpoint()` uses this same preparation/publication path.

The caller must retain exclusive access to a suspended provider throughout
preparation and publication and maintain the supported thread/signal policy.
Blocked INT/TERM/ABRT, no pending/delivered signals, unchanged handlers and no
signature state remain requirements. These checks do not checkpoint signals,
reserve process-wide state or establish complete HTIF/context ownership.
Other owners must finish their parsing, allocation and cross-owner validation
before the final publication callback. Appending lifecycle restore after
another owner's publication is still insufficient.

The existing `prepare_polling_components()` cannot be placed inside this
callback: it still allocates and validates, including the terminal/BCD/poll
replacement in `load_sealed_polling_checkpoint()`. A future aggregate needs
to separate that preparation from its nonthrowing swaps. It also needs the
direct-exit recorder as a distinct owner and must compare its full phase and
raw status with the lifecycle fields. In the restricted direct-command path,
running means absent exit/not stopped, requested means present matching odd
raw status/not stopped, and stopped means present matching raw status/stopped.
Comparing only `exit_code()` loses the low raw bit and absent/present zero.
The provider component deliberately represents more states than that restricted
caller can produce; successful component parsing does not validate the caller.

The native ASan/UBSan and VCS suites independently check **440 transactions**
over all absent/present-zero/raw-bit/stopped images: successful paired lifecycle
and real serial-FIFO publication, abandoned candidates, invalid peer candidates,
late pending/delivered signals, mask/handler changes, occupied destinations and
signature rejection. Every successful commit rejects a second attempt, including
an entirely empty lifecycle. Clearing the input bytes after preparation does
not change the candidate. Peers retain every FIFO word on all rejected cuts.
Three native compile-negative cases reject copying, moving and throwing peer
callbacks. All 282 existing malformed-image processes additionally reject
preparation without assignment. These are component cuts, not CPU target cuts.

The complete pre-existing lifecycle suite remains required: 1,216 production
captures, 2,432 fresh final-class TSI readbacks, 88 optional/raw/stopped restores,
eighteen destination/signal/signature rejections and twenty boundary-zero
raw-status first divergences. No target service is performed by restore.

Diagnostics reside under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration133/`.
The standalone provider suite and its independent audit pass in
`lifecycle/invocation-arsi0u2h/summary.json` and
`lifecycle-independent-audit.log`. The same complete suite and independent audit
also pass using the archive actually linked into the new exact-recipe metasim
build: `recipe-lifecycle/invocation-nu6bqm1v/summary.json` and
`recipe-lifecycle-independent-audit.log`. Five separately resealed evidence mutations
reject in `transaction-auditor-rejections.json`: omitted peer publication,
lost optional zero, late-guard peer publication, accepted malformed preparation
and missing throwing-callback diagnostic. Those are auditor tests, not executed
DUT corruption cases. Exact-recipe and preserved regression results are
recorded in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Next: integrate lifecycle preparation into a complete aggregate after owning
the remaining session, descriptor, syscall-parent, signal and outer-context
state. Complete configuration-specific simulator/bridge/memory ownership,
coherent active CPU cuts, fresh Level-1 continuation and independently captured
Level-2 readback/replay remain pending. BOOM/Saturn remain pending. Physical
FPGA validation, standalone Shuttle and ASIC power remain outside this task.
