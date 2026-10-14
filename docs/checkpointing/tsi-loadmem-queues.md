# TSI load-memory queue ownership

Iteration 98 implements `firesim.tsi.loadmem-queues.v1` in the production
`firesim_tsi_t`. It owns write requests, read requests, unconsumed write bytes
and response words. A dequeued write retains its address, total byte count and
consumed cursor until its last byte drains. The payload has no process pointers.
The TSI wrapper exposes const inspection of this component; it still rejects
complete checkpointing through the bridge's unsupported aggregate contract.

Requests bind four-byte alignment, a nonzero multiple-of-four length up to
4,096 bytes and a nonwrapping 64-bit address range. Partial write-data drains
can consume individual bytes. A new write cannot be dequeued until the active
write drains. The image requires exactly the remaining active bytes plus all
queued write bytes, preserves FIFO order and rejects response words wider than
32 bits. Queue lengths are bounded by the actual payload before allocation;
there is no fixed queue-count limit that silently drops program-load state.

Load parses and allocates all candidate queues before a no-throw pointer swap.
Save, validate and load perform no bridge I/O, request delivery, response
consumption or HTIF execution. Invalid operations reject before mutation;
allocation failures during queue insertion poison checkpoint access. The read
operation, queue owner and external bridge remain separate owners. A future
aggregate must validate their cross-owner relationships before loading any one.

The native sanitizer/VCS suite independently expands requests, bytes and FIFO
responses, captures all completed-call cuts and restores in separate processes.
Every complete pre-edge payload and subsequent payload/transcript is compared
with the independent oracle. Its cycle labels are fixture operations. A valid
write-byte corruption is compared before the first resumed operation is
acknowledged. These checks do not establish Rocket target-cycle continuation.
The actual installed FESVR ELF loader also exposes seven suspended cuts and
four additional queue cuts per backend, including a one-byte write drain and
an unconsumed response. The original ELF read/merge/reset behavior is preserved.

Complete TSI ownership remains pending: FESVR's private serial input/output
queues; `host`/`target` context and suspended read destination; HTIF poll phase,
tohost/fromhost transaction and callback queue; stop/exit/signature/device state;
TestChip program-load/cache-flush/init-access phase; FireSim idle/reset cursors
and flags; and the TSI bridge's wait/step/fast-mode/transport state. HTIF's
`run()` retains its fromhost queue and callback on the coroutine stack. Copying
`ucontext` or re-running `start()` in a restored process cannot reconstruct
these owners. The installed FESVR library remains an explicit build input.

Recovery and exact native results are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostic files belong
under `automations/checkpoint_loop/runs/m11-iteration98/`. The two checkpoint
levels remain independent; physical FPGA and ASIC work remain deferred.
