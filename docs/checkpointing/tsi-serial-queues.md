# FireSim FESVR serial queues

Iteration 101 adds the production `firesim.tsi.serial-queues.v1` component.
It owns every word and FIFO position in the target-bound request queue and
host-bound response queue, including partially transmitted command packets and
responses waiting for a suspended read. It does not own the suspended read's
destination, its caller stack, HTIF, or TestChip progress. Complete TSI and CPU
checkpoint support remain disabled.

FireSim now compiles `owned_fesvr_tsi.cc` and its project-local `fesvr/tsi.h`.
The original serial algorithms are integrated into `firesim_fesvr_tsi_t`, with
the existing TestChip `tsi_t` spelling aliased to that distinct class. The
installed FESVR archive, HTIF, context implementation and toolchain headers are
unchanged. The normal native link omits the original archive's TSI object;
whole-archive DPI fixtures can link both distinct implementations. The exact
Rocket build must bind TestChip and FireSim to the owned class. This is source
integration, not binary introspection or an installed-library ABI patch.

The original read/write packet order, two 32-bit address halves, two length
halves, FIFO order, serial handshakes, coroutine read-yield loop, MSIP reset
write and terminal yield loop are preserved. Serial chunks must be nonempty,
divisible by four and at most FESVR's 1,024-byte maximum; unsupported calls fail
explicitly. FireSim's separate load-memory path and its existing 4,096-byte
owner remain unchanged. Full four-hart controls check target-visible timing
after the source integration.

The immutable raw component prefix is `WDGCKPT1`, version 1, kind 19 and
configuration words `(4, 2, 2, 1024)`. Mutable words are request count, every
request word in order, response count, and every response word in order.
Each serial word uses a 64-bit slot and must fit 32 bits. Counts must consume
the exact payload. Both queues are fully validated and allocated before two
no-throw swaps commit the candidate. Missing counts, malformed lengths,
truncation, extra words, wrong configuration and wide data reject before any
queue mutation. Component restore executes no service, serial handshake,
context switch or target edge. The aggregate image remains responsible for
integrity, build identity and complete cross-owner validation.

Queue API calls finish before capture; escaping transaction failures invalidate
component access. Unsupported argument checks precede mutation. A failed empty
pop poisons the component. The project header is included directly before the
TestChip system header so GCC's dependency files retain the base-class ABI
dependency for VCS's cached external-C objects.

The independent Python oracle expands both FIFO operations and original serial
packets. The native sanitizer and VCS component checks restore every fixture
cut in fresh processes, read back every word before any operation, compare all
continued payloads and operation labels, reject malformed images atomically,
and detect changed request/response data at the first unacknowledged operation.
Maximum 1,024-byte chunks are additionally read back and drained word by word.

The installed-HTIF checker runs real TestChip init reads and three actual tohost
poll loops for idle counts 1, 3 and 10. It independently reconstructs complete
queue images before/after each serial packet word and while responses are
queued, including loader/reset/idle cuts. Every captured queue image restores
in fresh sanitizer and VCS component processes. Those restores do not recreate
the HTIF caller or continue a CPU workload.

Exact selected results, source/workload hashes, build identity and executable
native checks are recorded in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).
Diagnostics are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration101/`.

Next ownership is the serial read cursor/destination and suspended caller,
HTIF poll/fromhost/device/stop/signature state, TestChip loader/cache-flush/init
progress, and cross-owner coherence. The exact Rocket recipe still needs
early, warmed-cache, outstanding-memory and late CPU cuts, complete fresh
Level-1 continuation, and independent Level-2 zero-edge readback/captured replay.
BOOM and Saturn remain pending; standalone Shuttle, physical FPGA validation
and ASIC power remain deferred. No dependency is missing.
