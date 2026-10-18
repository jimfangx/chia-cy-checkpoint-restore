# Sealed functional-memory publication

Iteration 168 adds a prepared/sealed component transaction to the production
`mm_magic_t` functional-memory owner. Complete Rocket Level 1 remains in
progress, with CPU aggregate admission disabled.

`prepare_checkpoint` parses and validates the complete existing
`firesim.mm_magic.full.v1` payload, owns the incoming bytes and preallocates the
dummy/read/write response storage. It retains every destination byte and field
for a later complete comparison. Neither preparation nor candidate destruction
publishes any memory state. The caller can release its image after preparation.

`seal_checkpoint` checks destination lifetime, native thread, consumption and
publication generation, then compares the complete destination image. All
throwing checks and C++ allocations finish before a successful seal. A failed
multi-owner sealing pass can discard all candidates, including members already
sealed, without publishing any owner.

`publish_sealed_checkpoint` is `noexcept` and performs no C++ allocations. It
copies the prepared backing bytes into the existing mapping, preserving aliases
returned by `get_data`, then swaps dummy/read/write storage and assigns the
pending write cursor and cycle counter. Compile-time assertions require all
container swaps to be nonthrowing. Lifetime, thread, seal, consumption and
generation violations terminate before that owner's first copy; they cannot
unwind into a runnable simulator. Every successful publication advances a
destination-local generation. The existing `load_checkpoint` also advances it,
including identical-byte loads, so it invalidates earlier prepared/sealed
candidates. The payload format and semantic state are unchanged.

Memory owners cannot be copied or moved. Reinitializing a live mapping rejects
before replacing it; this prevents alias invalidation and the previous mapping
leak. Normal construction and the legacy validated load path remain available.

The coordinator must exclude both simulator contexts and all backing-memory
users from preparation through publication and complete readback. These APIs
do not acquire that exclusion or detect arbitrary unsynchronized writes after
sealing. They cover one concrete native state owner; they do not supply a
durable CPU image parser, build binding, generated RTL or harness publication.

The maintained native ASan/UBSan and time-zero VCS DPI matrix exercises pristine,
outstanding AW/read, partial strobed-write and buffered-response cuts. It tests
one bank with the exact Rocket AXI geometry and an additional four-bank group.
Each component bank has a 4,096-byte backing mapping; these fixtures do not
establish full 16-GiB CPU checkpoint support. Fresh processes read back every
owner byte before any edge and continue all sampled AXI boundaries against a
separate Python byte/queue/strobe oracle. Preparation and multi-bank sealing
exhaust every injected allocation failure; sealed publication runs with the
next allocation armed to fail. Fatal processes test unsealed, foreign-thread,
foreign-destination, recycled-lifetime, consumed, stale and legacy-load-stale
candidates. Negative cases also cover incompatible geometry, changed backing
bytes and pending queues/cursors, repeated seals, uninitialized/reinitialized
owners and unpublished cancellation. Exact receipts and executable commands
are recorded in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Next: join prepared/sealed functional memory with runtime I/O, creator-side TSI,
all remaining widgets/driver state, generated RTL and harness state under actual
controller/creator/thread/signal/descriptor/parser exclusion. The generic
`aggregate_restore_t::commit_native` still calls allocating owner loads
sequentially; `checkpoint_owner_t` still has no general prepared publication
contract. Keep complete CPU requests denied until the whole transaction and
independent whole-state readback are implemented, then test fresh-process
Rocket continuation at all four real workload cuts. Level 2 stays independent.
BOOM/Saturn remain pending; standalone Shuttle, FPGA validation and ASIC power
remain outside this task.

The remaining publication work is concrete. A source review of the actual
Rocket owner census finds these legacy load paths; per-owner validation before
mutation does not make them an atomic multi-owner transaction:

| Owner(s) | Current load path and remaining preparation boundary |
| --- | --- |
| `master_t`, `loadmem_t`, `reset_pulse_t`, `clockmodule_t` | Recheck returned-call/configuration state during load; require a seal and a publication contract even when no semantic assignment is needed. |
| `CPUManagedStreamWidget` | Validate configuration/returned-call state, then assign `initialized`; separate that throwing check from publication. Hardware queues and runtime stream callers remain separate. |
| `peek_poke_t` | Reconstruct configuration and validate flags before assigning `req_unstable`/`req_timeout`; stage both flags and destination checks. |
| `blockdev_t` | Decode/allocate queues and disk bytes, then `fmemopen`/seek a new owned stream before replacing the old stream. Stage the libc stream too, and retain retired resources outside the aggregate publication path. |
| `uart_t` plus its buffered-file handler | Decode parent and child payloads, allocate the child output buffer, then swap output/cursor and assign handshake data. Prepare both together. |
| `FASEDMemoryTimingModel` | Allocate decoded histogram/range/history storage, then copy/swap it and assign lifecycle/replay flags. Preserve these flags as well as generated FASED RTL. |
| Four `tracerv_t` owners | Allocate each output prefix, then swap it and assign initialization/cycle state. Include all four stream identities and sinks. |
| `heartbeat_t` | Allocate decoded samples, then swap samples and assign start time, timeout, trip count and last cycle. |
| FireSim concrete driver | Rebuild and validate its configuration, require a fresh driver, then set `started`. Keep this separate from scheduler and run-loop state. |
| `systematic_scheduler_t` | Parse and allocate a deadline vector, then assign current cycle and every task deadline. Bind callback identities and owner schemas before publication. |
| `bridge_run_loop_t` | Parse phase/index/termination/status into a POD replacement; expose a prepared publication contract instead of re-running throwing validation at aggregate commit. |
| `tsibridge_t` | Already has private creator-side preparation, sealing and `noexcept` publication for its restricted context group; its generic owner schema remains unsupported. Join that real creator/lifetime guard, rather than calling generic legacy hooks. |

These observations come from the corresponding concrete `load_checkpoint`
implementations in MIDAS `core/`, `bridges/`, FireChip `bridgestubs/` and
`firesim_top.cc`; they are a recovery checklist, not new runtime acceptance.
A general prepared-owner contract must reject unaudited owners by default.
Do not fall back to sequential legacy loading when enabling a CPU profile.
