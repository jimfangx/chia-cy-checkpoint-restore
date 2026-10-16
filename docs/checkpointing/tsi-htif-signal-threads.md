# HTIF signal checks across host threads

Iteration 143 extends the opt-in exact-source delivered-signal provider's
capture, preparation and final publication guard. Before accessing actual
`signal_exit`, optional raw exit and stopped state, it audits every Linux
`/proc/self/task/<tid>/status`: SIGINT, SIGTERM and SIGABRT must be blocked,
and neither thread-directed nor process-shared instances may be pending.
Missing, unreadable, incomplete or malformed status and changing task membership
reject before provider or peer publication. The helper is an explicit hashed
input to the build-local FESVR overlay and its Make dependency list.

This is an audit under an existing exclusive-suspension contract. Reading
procfs cannot suspend a running thread or stop it changing masks afterward.
The caller must suspend all affected providers/threads and exclude changes to
thread membership, signal actions/masks and signal delivery throughout access.
A simulator coordinator that establishes and holds this exclusion remains
pending. The tests block signal inheritance before VCS starts its workers;
this test bootstrap does not implement a production coordinator. Procfs is a
required dependency of this opt-in GNU/Linux x86-64 provider, with explicit
rejection if it is unavailable. Other signal classes remain outside its scope.

No kernel thread IDs, masks, pending queues, pointers or raw signal actions are
serialized. The `firesim.tsi.htif-signal.v1` image remains unchanged: delivered
latch and private lifecycle projection. Build identity must independently bind
the provider and its helper. The strict lifecycle/polling admission rules remain
separate; delivered signals are still excluded from their aggregate.

The archive-linked native ASan/UBSan and VCS suite passes 686 fresh processes,
including six captures with two parked pthreads, twelve fresh cross-backend
threaded restores, and 24 thread-policy transactions. For each transaction,
actual worker masks, `pthread_kill` pending signals or `kill` shared signals
cause capture, preparation and an already-prepared candidate's commit to
reject. All three checks leave provider and actual serial FIFO peer unchanged;
repairing the exclusion while workers stay parked permits one atomic retry.
Workers drain their test signals before runtime teardown. The independent
archive/state/trace auditor rejects fourteen missing/duplicate evidence variants.
The same new harness fails against the previous exact-recipe provider in six
native/VCS cases, demonstrating sensitivity to its missing worker checks.

Accepted evidence is under:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration143/`:

- `recipe-signals/invocation-g9yeawcm/summary.json`
- `signals-independent-audit.json` and `signals-builtin-audit.json`
- `prior-provider-witness/invocation-9k80fwnt/summary.json`

See [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) for recipe settings,
complete workload/regression outcomes and executable VCS commands. These are
host-provider component checks; complete Rocket Level 1 remains disabled.

The session audit also confirms why default-device construction cannot be
replayed as a substitute for session state. Installed `syscall_t` duplicates
stdin once and stdout twice; target descriptors 1 and 2 therefore refer to the
same stdout open-file description. Its descriptor table, free slots, ownership
indices, syscall table and device handlers, HTIF/memif bindings and chroot
string need explicit ownership. Kernel offsets/flags, underlying files/pipes,
process working directory and external effects need a defined policy too.
The suspended `dispatch` parent additionally owns eight target-endian argument
words, selection/result/writeback progress and its enclosing response callback.
Existing memif child ownership does not capture this parent. Session/descriptors,
syscall parent, executable outer caller, signal-caused stop callers and coherent
simulator/bridge/memory publication remain required before CPU admission.
