# FireSim TestChip initialization caller

Iteration 103 adds `firesim.tsi.init-accesses.v1` to the production FireSim TSI
reset path. It owns the ordered TestChip access cursor, before/after child
phase, read destination/result and write/MSIP source buffer. The complete
resolved access list and hart-0 MSIP policy bind its image. Host addresses,
closures and coroutine stacks are absent from the payload.

The original TestChip initialization loop keeps its current element and
`rdata` on a suspended stack. FireSim now selects each access once, uses an
owner-resident buffer through the original virtual TestChip `read_chunk` or
`write_chunk`, records child return and retires that access. The optional final
MSIP uses the same address, word and virtual write routing as FESVR reset.
Ordered accesses, cache flushing, serial traffic, empty-response yields and
original TestChip stderr messages are preserved.

The component prefix is `WDGCKPT1`, version 1, kind 21, configuration
`(write_hart0_msip, access_count)`, followed by each immutable
`(address, uint32_data, store)` triple. Three mutable 64-bit words encode
phase, access index and the 32-bit buffer. Phases are idle=0, ready=1,
read-child=2, read-return=3, write-child=4, write-return=5, MSIP-child=6,
MSIP-return=7 and complete=8. Ready holds the next access index and zero data;
complete holds the full count and zero data. Child/return types must agree
with the configured access. Write data must match the configured word; MSIP
requires its enabled policy, final index and word 1. Read data is caller-owned.

Complete configuration, length, phase, index and buffer validation precede the
fixed-size commit. Restore allocates no state, calls no services and advances
no context or target edge. Duplicate selection, out-of-phase return/retire and
escaping reset exceptions reject access. The source and destination buffers
stay at stable member addresses, including through component image deposits.

`verify_tsi_init_vcs` expands the original ordered-access/MSIP algorithm in an
independent Python oracle. It checks every word before any operation in fresh
sanitizer and native VCS DPI processes, then every resumed operation and full
state image. Coverage includes empty lists, MSIP on/off, mixed reads/writes,
repeated addresses, zero/max words, full 64-bit addresses and repeated reset.
Invalid images and incompatible access configurations reject atomically;
valid cursor and read-result corruption must report the first unacknowledged
divergent operation. Fixture labels are not Rocket target cycles.

Real installed-FESVR/TestChip tests capture this caller beside complete serial
read/FIFO and host-control owners. Additional production runs execute mixed
reads/writes with cache flushing and MSIP independently on/off. Their complete
captured owner bytes and every serial packet word are independently audited.
Fresh readbacks of these caller images do not resume HTIF or a CPU. Exact
results and executable checks belong in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md);
diagnostics belong under `automations/checkpoint_loop/runs/m11-iteration103/`.

This component does not reconstruct the suspended read/cache-flush child,
HTIF reset caller, terminal/host context or TestChip loader. The production
coroutine still has a local return path: loading a child-phase image is not
permission to issue that access again. Cross-owner validation and a fresh
pointer-free caller dispatcher remain required before complete CPU support
can be enabled. HTIF poll/fromhost/device/stop/signature and memif progress,
coherent active CPU cuts, complete Level-1 continuation and independently
captured Level-2 replay remain pending. No external dependency is missing.
