# Restricted polling session lifetime

Follow-up: iteration 147 retires the unused inherited proxy resources in
restricted mode; see [tsi-dormant-proxy.md](tsi-dormant-proxy.md). The evidence
below records the earlier two-object lifetime audit.

Iteration 146 makes production `+checkpoint-syscall-exit` polling construct its
services directly, without allocating `default_devices_t`. Its explicit syscall
parent already supplies dispatch, exit, writeback and response ownership;
restricted device ticks perform no work. The fourteen-owner group now rejects
an instance containing a default session during inspection, preparation and
the final publication guard. Ordinary dispatch still constructs its session.

There are two distinct installed syscall objects to account for:

| Object | Construction and descriptors | Current disposition |
| --- | --- | --- |
| Embedded `htif_t::syscall_proxy` | Base constructor; duplicates stdin once and stdout twice | Still present in both modes; complete session ownership remains pending |
| FireSim `default_devices_t::syscall` | Ordinary polling startup; duplicates stdin once and stdout twice | Absent in restricted mode; ordinary lifetime preserved |

The installed `syscall.o` remains unchanged. Its constructor allocates a
dispatch table, handlers, descriptor lookup table and three descriptor indices.
Its destructor closes those indexed descriptors. Neither removing the second
object nor recognizing that the first object is unused implements restoration
of the inherited session. General syscalls remain unsupported in restricted
mode. No descriptor number or process pointer is stored in checkpoint images.

The executable descriptor audit enumerates actual `/proc/self/fd` entries and
records each number, device, inode, mode, rdev, status flags, descriptor flags
and symlink target. It checks construction, polling startup, four suspended
idle/read boundaries and destruction of a suspended TSI. Preexisting
descriptors must retain their complete recorded identities. Constructor
additions must be the three installed standard-stream duplicates. Polling
startup adds zero descriptors in restricted mode and three in ordinary mode.
Destruction must reproduce the complete initial table in both modes. Native
ASan/UBSan and VCS execute both paths. A separately compiled prior production
implementation must fail the new restricted descriptor-count check.

The independent byte oracle also now runs two complete zero-mailbox idle
rounds before every syscall scenario. It checks both partial mailbox words,
all three idle yields (including remaining=0), the busy flag when polling
resumes, and every subsequent fourteen-owner image and serial transaction.
Each native/VCS producer cut is restored in fresh native/VCS consumers, with
complete readback before any service. These remain host-operation cuts.

The source process completes syscall writeback, responds, calls stop and
returns. Fresh component continuation completes the response and polling
without calling stop or entering a context. Explicit outer startup, stop,
return and context ownership, inherited session state and production signal
coordination remain pending. The next increment must account for these owners
before coherent simulator/bridge/memory publication and complete Rocket
Level-1 continuation can be enabled.

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/`.
Exact accepted artifacts, native commands and results belong in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). This increment cannot
certify either CPU checkpoint level by itself; the existing independent
Rocket Level-2 four-cut replay evidence remains separately recorded.
