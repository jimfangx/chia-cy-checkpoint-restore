# Delivered HTIF signal and lifecycle provider component

Iteration 142 adds `firesim.tsi.htif-signal.v1`, an opt-in projection of the
actual FESVR translation-unit `signal_exit` latch and private `exitcode` and
`stopped` fields. The exact-source build-local HTIF provider retains every
original method body and adds no object fields or virtual methods. The default
installed HTIF and the existing strict lifecycle/polling interfaces retain
their previous admission policies. Complete Rocket Level 1 remains disabled.

The image contains the optional-exit presence, all 32 raw exit bits, stopped
bit and delivered-signal bit. It distinguishes absent exit from present zero.
No pointers, file descriptors, raw signal actions or coroutine storage are
serialized. The component configuration binds revision 1, integer width 32
and the supported signal policy; the complete future image must also bind its
build and complete owner inventory independently.

Access requires exclusive suspension of every affected HTIF instance and
prevention of INT/TERM/ABRT delivery in every thread. The current thread must
block those signals. Corresponding pending kernel signals, changed handlers,
changed handler masks or action flags, signature mode and other provider ABIs
reject explicitly. The supported actions are the exact GNU/Linux x86-64 BSD
`signal()` actions installed by this provider. This is a component contract;
it does not implement the simulator's cross-thread signal coordinator or own
other process/thread signals. A fresh destination must have no delivered
latch, no optional exit and `stopped=false`.

Preparation owns parsed fields without publication. A destination-bound,
noncopyable, nonmovable candidate repeats every provider guard immediately
before a nonthrowing peer callback. Subsequent provider assignments cannot
allocate or throw. A failed guard publishes neither provider nor peers;
successful candidates are single-use. Restore does not re-deliver the signal,
invoke stop, enter a context, perform MMIO or advance a target edge.

The native ASan/UBSan and VCS suite tests the archive actually linked into the
exact Rocket recipe. Its 644 fresh processes include 72 actual captures,
144 fresh restores, 300 malformed/incompatible images, forty late-guard
transactions and 72 atomic publications with a real serial FIFO peer. Source
captures use real SIGINT/SIGTERM delivery. Complete image/field readback and
the next two HTIF boundaries match the uninterrupted source. Restoring a
delivered latch preserves the original handler's `exit(-1)` on a subsequent
signal in both native and VCS consumers. Pending SIGABRT rejects without
delivery. Six actual signal/stopped/raw-exit mutations report the first
provider divergence at boundary zero before acknowledgement; these are host
component faults, separate from the retained Rocket DUT CSR faults.

The independent auditor binds the actual Rocket executable, its defined
provider symbols, linked `owned-htif.o`, archive bytes, source snapshots,
executed commands, all state/trace readbacks and serial peer publication.
It additionally rejects eight missing/duplicate evidence variants. Both
auditors pass for `recipe-signals/invocation-68fia3n2/summary.json` under:

`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration142/`.

See [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) for exact recipe,
workload, full regression results and executable VCS commands. The new
projection is independent of the fourteen-owner polling/direct-exit group:
that group still rejects delivered signals and cannot resume a signal-caused
stop caller. Session/descriptors, syscall parent, executable outer caller,
cross-thread signal coordination and coherent simulator/bridge/memory cuts
remain necessary before complete CPU Level-1 admission.
