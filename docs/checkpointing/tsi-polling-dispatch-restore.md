# Atomic preparation of identity dispatch

Iteration 126 extends the sealed polling component transaction to twelve ordered
owners: `poll`, `program`, `init`, `host`, `read`, `serial`, `loadmem-read`,
`loadmem-queues`, `bcd`, `terminal`, `identity`, `write`. Even idle identity/write
images are mandatory. The historical unsealed inspection still returns eight
owners and rejects an active identity. This component interface does not restore
HTIF contexts, syscalls, descriptors, signals, stop/exit or the whole simulator.
Complete Rocket Level-1 and Level-2 acceptance remain in progress.

A suspended dispatch must retain the parent's exact raw identity command. The
identity caller must be writing that command's independently reconstructed
64-byte payload to its encoded address. Its write child must be waiting for a
partial head or tail merge read. The independent mailbox reader must be idle;
the host must be ready with program and initialization complete, both loaded
flags set, no pending loadmem caller and empty loadmem queues. Parseable
responding/complete identities or writes that have not reached a merge yield
are insufficient. At mailbox-read or idle boundaries both new owners must be
idle, retaining the prior phase predicates.

Preparation loads destination-configured temporary owners and checks every
relationship before publishing terminal state. It then uses only nonthrowing
moves/swaps. The identity's publication swaps its scalar state without copying
references: the real caller remains bound to the real destination writer and
serial FIFO. An exception before publication leaves all pristine peers and
metadata intact and creates neither the parent nor BCD device.

Prepared continuation now routes every identity through the ordinary explicit
dispatch service. The child returns blocked through both owner guards before
the component service returns. It resumes the existing command without replaying
startup, initialization, reset or tohost's clear. The pre-clear rejection hook
continues to reject unowned commands. `tick()` and complete CPU continuation
remain disabled.

The maintained polling byte oracle includes ordinary BCD input, output, EOF,
idle and aligned identities, then all four identity selectors at every address
residue. It retains partial requests, both merge phases, one-word responses
and partially consumed serial packets. Producers exit before fresh destinations
prepare; every one of the twelve images is checked before service and after
every host operation. The active-dispatch checker additionally injects every
preparation allocation failure, malformed/missing owners and inconsistent
parent/caller/child phases. Its two semantic faults alter an actual retained
merge byte or consistently alter the parent/caller command and copied payload;
execution must stop before consuming the first divergent request word. These
are host-operation labels, not Rocket target-cycle checkpoints.

Verification artifacts and exact executable VCS commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration126/`.
