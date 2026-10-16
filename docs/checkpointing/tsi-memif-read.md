# Explicit generic memif read caller

Iteration 127 adds `firesim_tsi_memif_read_t` in
`generators/firechip/bridgestubs/src/main/cc/fesvr/tsi_memif_read.h`.
This is a component prerequisite for the remaining HTIF/syscall callers.
Iteration 128 subsequently connects production runtime reads through the
default syscall session's virtual interface; see
[tsi-runtime-memif-read.md](tsi-runtime-memif-read.md). The sealed
polling transaction retains twelve owners and continues to reject general
syscalls, exits and context entry. Neither Rocket checkpoint level is accepted.

The owner implements the installed FESVR `memif_t::read` transaction order for
FireSim's eight-byte alignment and 1,024-byte maximum transport chunk: read the
unaligned head, then the tail, then the aligned body. Each partial read retains
its complete serial child, including an issued request and partially collected
response. The caller retains the original address, requested byte count,
zero-initialized output buffer, phase and body cursor. Completed head/tail/body
bytes live in this buffer, with no saved destination pointer or host stack.
Only a complete read exposes its result. Serial request/response queues remain
a separate owner, as does the enclosing syscall/HTIF service.

The `firesim.tsi.memif-read.v1` component image binds layout kind 30, revision 1,
alignment 8, chunk size 1,024 and maximum result size 1 MiB. Parsing validates
exact lengths, phase/cursor relationships, address wrap, canonical zero bytes
for unread output, and the child's exact pending chunk address and size.
Unsupported lengths reject before mutation. Reentrant callbacks, escaping
service exceptions and an interrupted caller reject subsequent access.
`load_serial_checkpoint` constructs and loads both candidate owners before
nonthrowing publication. It does not certify a simulator-wide cut or establish
the still-missing enclosing caller's ownership.

`verify_tsi_memif_read_vcs` independently expands the installed algorithm into
byte images and host operations. Its C++ installed-provider control calls the
actual installed `libfesvr.a`, checking transaction ordering, every output byte
and neighboring output-buffer sentinels. Its independent Python oracle checks
every byte of both owners at every source cut, before fresh destination service
and after every continued operation. Producers exit before destinations start;
native ASan/UBSan and VCS DPI destinations test all four backend pairings.
The VCS component bench finishes at simulation time zero. These labels are
host operations, not Rocket target cycles or semantic CPU checkpoints.

The suite covers all eight address residues, zero/one-byte reads, head-only and
tail-only reads, exact and partial 1,024-byte chunks, multiple body chunks,
partially drained requests, repeated blocked service and partial responses.
Separate native/VCS checks complete the full 1 MiB supported result, the final
seven bytes of the address space and a zero-byte read at the maximum address.
Malformed/incompatible/missing images preserve both destination images.
Allocation fault injection covers every allocation of the two-owner load.
Semantic faults change a retained response byte, copied output byte or pending
request word; comparison stops at the first changed result/request boundary,
before acknowledging it. Isolated diagnostic mutants omit a tail read or skip
remaining body chunks to check that the native/VCS oracle detects both errors.

Exact evidence and runnable native VCS commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration127/`.
Next, bind this child into an explicit production HTIF/syscall parent whose
parent returns blocked before any target yield, inventory its complete session
and external state, and retain rejection until that aggregate is complete.
The production adapter must preserve `firesim_tsi_t::read_chunk` policy:
startup loadmem dispatch is a different transport, and normal serial reads
flush each chunk's program-cache lines before issuing that chunk. The current
iteration-127 component services do not supply either policy. Reusing them directly as the
production adapter would omit required behavior when those modes are enabled.
