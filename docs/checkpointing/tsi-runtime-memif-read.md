# Production runtime memif reader

Iteration 128 binds `firesim_tsi_memif_read_t` to the actual default-device
HTIF syscall session. `firesim_tsi_t::memif()` returns a per-instance derived
`memif_t`; the installed `syscall_t` retains this reference when the session
is constructed. Its virtual byte reads, including inherited typed reads,
use the explicit head/tail/body caller and copied result. Its inherited writes
still use the installed memif caller. The inherited HTIF syscall/device table
and custom-device path remain separate owners.

Normal runtime reads issue serial packets through
`firesim_tsi_memif_read_services_t`. For each actual head, tail or body chunk,
the service queues every intersecting 64-byte cache-line flush before queuing
that chunk's read. Neither action yields. A pending child therefore resumes
its response collection without repeating the flush or request. The adapter
holds only references and the immutable cache-flush address; program/startup
metadata owns that configuration, while the reader and FIFO own issued state.
Its final-address-space walk avoids endpoint overflow and rejects invalid
chunk requests before touching a queue.

Startup loadmem remains a separate transport: the derived interface delegates
to the installed `memif_t::read` while the program loader is in loadmem mode.
The startup loader's preload-aware interface and loadmem read/queue owners
are preserved. Metadata preparation and prepared-context reads reject before
reader entry. Unsupported lengths above 1 MiB, wrapping byte ranges and a
missing nonempty destination reject explicitly.

`read_runtime_memif` advances until blocked, leaves the component guards,
and only then switches to the target context. It copies the complete result
into the installed caller's destination on return. The destination pointer,
syscall buffers/arguments, descriptors, syscall return/response, signals and
outer context are **not** reconstructed by this change. Active generic reads
therefore reject polling-aggregate inspection; no thirteenth reader is silently
omitted from an admitted twelve-owner cut. Complete HTIF/CPU admission remains
disabled. This is production child integration, not a complete Level-1 restore.

The new `verify_tsi_memif_read_fesvr_vcs` uses actual installed
`syscall_t::sys_write` calls, with stdout bound to a retained regular file before
the session duplicates its descriptors. Its independent oracle expands the
installed memif order, all serial words and the peer's host-operation schedule.
It compares every source reader/FIFO byte at every sampled boundary, including
partial request drains and queued/partially consumed responses. It checks the
actual output bytes, normal installed exit, startup loadmem isolation and
rejection of an unowned active syscall parent. Producers finish before fresh
native/VCS processes prepare and read back all active reader/FIFO components.
Those fresh processes never enter a context or service the target.

The existing generic reader continuation suite additionally accepts `--flush`
and checks all four native/VCS producer/destination combinations at every
component cut, including partially drained flush packets, malformed images,
allocation failures and first-divergence corruption. These are host-operation
labels and component faults; they are not Rocket target cycles or semantic
DUT corruption. Diagnostic mutation controls bypass the production owned
reader or omit runtime cache flushing, and require the independent oracle to
detect both omissions in native and VCS execution.

Exact results, artifacts and executable commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md), under iteration 128.
Diagnostics stay under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration128/`.
Next: prioritize the exit/stop and outer-context continuation exercised by
the required four-hart workload, alongside complete session/descriptor/signal
ownership. The new reader does not require enabling arbitrary syscalls in a
restored polling service: unsupported commands must continue to reject before
partial target mutation. An explicit syscall request/buffer/return parent is
still required before admitting active generic reads. Any restricted profile
must independently audit every instantiated owner and reconstruct its permitted
state; unused or inaccessible session fields cannot simply be omitted. No
profile may be enabled until its complete CPU continuation checks pass. Required coherent CPU
cuts, full fresh Level-1 continuation and independent captured Level-2
readback/replay remain pending. No FPGA or ASIC validation is claimed.
