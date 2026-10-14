# FireSim FESVR serial read progress

Iteration 102 introduces `firesim.tsi.serial-read.v1` in the production
source-integrated FESVR TSI. The owner holds a read's original 64-bit address,
byte length, issue/response/complete phase, response cursor and all collected
32-bit words. It has no host pointers. The serial request/response FIFOs retain
their independent owner; the HTIF destination and suspended caller, TestChip
progress and context reconstruction remain pending. Complete CPU and TSI
checkpoint support stay disabled.

The raw component prefix is `WDGCKPT1`, version 1, kind 20, configuration
`(1024, 4, 2, 2)`. Four mutable words encode phase, address, byte length and
collected count, followed by every collected word in FIFO order. Phases are
idle=0, issue=1, response=2 and complete=3. Idle is empty; issue has no collected
words; response has fewer than length/4; complete has exactly length/4. Requests
must have a nonzero length divisible by four and at most 1,024 bytes. Full
64-bit serial addresses retain the original protocol's semantics.

Every configuration byte, length, count, phase and data width validates before
allocating a candidate. Capacity for the entire result is reserved before issue
or restore so consuming a response cannot lose it through a subsequent
allocation failure. Loading replaces the owner only after complete validation
and allocation, with no services, context switch or target edge. Callback
reentrancy and escaping service/context exceptions invalidate checkpoint access.

The production adapter preserves the original read packet and FIFO operations:
issue once, consume available response words, and yield only when the response
FIFO is empty. Completion consumes no extra response. Collected data is copied
to the current caller's destination on completion; that destination and caller
are not restored by this component. Complete ownership requires a pointer-free
HTIF/TestChip caller engine and cross-owner validation before CPU support can
be enabled.

`verify_tsi_serial_read_vcs` independently expands the packet/pop/yield algorithm
in Python and exercises fresh sanitizer and VCS DPI component processes. Both
read and FIFO state are read back before any operation, then every resumed
operation and every complete owner image are compared. Coverage includes
pre-issue, packet tails, waiting responses, partial words, completion, extra
queued responses, successive reads and maximum 1,024-byte chunks. Malformed,
incompatible and missing owners reject before deposits. Deliberate valid address
and collected-response corruption must report the first differing operation
without acknowledging it. Fixture operation labels are not Rocket target cycles.

The actual installed-HTIF checker captures read state alongside serial FIFOs at
TestChip init and HTIF polling cuts, including the collected first response half.
Fresh component readbacks do not restore HTIF or continue a CPU workload.
Exact native results, artifact paths and runnable VCS checks are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostic artifacts belong
under `automations/checkpoint_loop/runs/m11-iteration102/`.

Next work is HTIF poll/fromhost/device/stop/signature state, TestChip
loader/cache-flush/init progress, pointer-free read callers and cross-owner
coherence, followed by coherent active-workload CPU cuts and both complete
checkpoint levels. No external dependency is missing. BOOM and Saturn remain
pending; standalone Shuttle, physical FPGA validation and ASIC power remain
deferred.

## Remaining caller ownership audit

The following source owners remain unsupported. Empty queues in a control run
cannot substitute for explicit ownership or a checked configuration restriction.

| Source owner | State needed for a fresh continuation |
| --- | --- |
| FESVR `htif_t::run()` (`fesvr/htif.cc`) | Poll/clear/dispatch/idle/device-tick/fromhost-read/fromhost-write/stop phase; local `tohost`; every `fromhost_queue` word; callback destination reconstructed by identity rather than a saved closure pointer |
| FESVR `htif_t` (`fesvr/htif.h`) | Entry, expected XLEN, write-zero policy, resolved tohost/fromhost/signature addresses and lengths, optional exit-code presence/value, stopped flag; bind host/target arguments, payloads, symbol inputs, signature policy and address-to-symbol map |
| FESVR `memif_t::read/write` (`fesvr/memif.cc`) | Alignment/leading/trailing/bulk phase, current address, remaining length, chunk position and partial merge bytes; replace destination/source pointers and the suspended typed `read_uint64` result with explicit caller-owned data |
| FESVR devices (`fesvr/device.h`, `fesvr/syscall.h`) | Ordered device/command configuration, BCD pending commands and response identity, syscall file-descriptor mapping/chroot and in-progress dispatch; explicitly reject unsupported external descriptors/devices before any aggregate restore |
| FESVR stop/signal handling (`fesvr/htif.cc`) | Static `signal_exit`, stop/signature-read progress and complete signature bytes/output state; do not serialize a process-global signal-handler pointer |
| TestChip TSI (`testchip_tsi.h/.cc`) | `has_loadmem`, `is_loadmem`, `cflush_addr`, loader entry/return phase and pending cache-flush/read/write caller; bind exact parsed arguments |
| TestChip init (`testchip_htif.h/.cc`) | `write_hart0_msip`, full ordered `init_accesses`, current access index, read result and before/after access/MSIP phase; the current range-for element and `rdata` still live on its stack |
| Owned FESVR host/context (`owned_fesvr_tsi.cc`, `tsi.h`) | Before/after `run()` and terminal-yield phase, explicit caller reconstruction and current context binding; raw `context_t` stacks and `target` pointers are not image state |

The new read owner removes the original per-word loop cursor and partially
collected response from the serial coroutine's stack. It does not remove any
of the callers above. The actual TestChip init-read fixture demonstrates this:
the owner can restore all collected data while the original caller's local
`rdata` and access-loop position remain unavailable in a fresh HTIF instance.
The original `htif_t::run()` is nonvirtual; a same-named derived method alone
cannot replace the call currently made by `host_thread`. Source integration or
an explicit pointer-free engine must replace that call before coherent complete
CPU checkpoints can be enabled.
