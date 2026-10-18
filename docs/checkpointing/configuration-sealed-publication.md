# Prepared publication for configuration-only widgets

Iteration 170 adds explicit prepared-publication adapters for production
`master_t`, `clockmodule_t`, `loadmem_t` and `reset_pulse_t`. Their host payloads
contain immutable MMIO/configuration bindings and zero result flags. Hardware
counters, clock latches, loadmem traffic, functional memory and reset progress
remain owned by generated RTL, MMIO queues and memory adapters. Completed-call
boundaries do not retain host buffers, file handles or partial GMP operations.
Suspended and interrupted calls continue to reject checkpoint access.

`configuration_checkpoint_t` validates the complete source payload and requires
byte equality with the destination's independently captured configuration.
Sealing checks lifetime, native thread, generation and complete destination
bytes before consuming the seal. Publication is `noexcept`, allocates nothing,
performs no MMIO and makes no host-state assignments: both configurations are
already identical. It consumes the generation guard. An identical-byte legacy
load invalidates outstanding candidates. All four owners become noncopyable and
nonmovable through their destination-local publication guard.

This adapter is explicitly restricted to these audited configuration-only
owners. Mutable completed-call flags in `peek_poke_t` do not gain support.
Unregistered owners still reject the generic prepared-publication interface.
As with the existing scheduler/bridge-loop adapters, the coordinator must retain
exclusion from final sealing through full aggregate readback. This component
does not implement process-wide thread/signal/descriptor/parser exclusion or
recognize a completed target-cycle boundary.

The maintained native ASan/UBSan and time-zero VCS DPI matrix uses actual widget
methods with deterministic MMIO services. Twelve cuts span all eleven returned
service operations: master status/fingerprint reads and writes, both clock
latches, reset initialization, loadmem reads/writes/chunk writes, zeroing and file
loading. Every fresh component process reads back all four complete host payloads
before any MMIO and compares the complete service suffix to an independent Python
oracle. These cuts are service cursors, not Rocket target cycles.

Additional checks sweep every payload truncation and byte mutation, trailing
bytes, wrong owner bindings, suspension, interrupted-call poisoning, cancellation,
repeated sealing, consumed/stale/legacy-load/expired/wrong-thread candidates and
every allocation in paired preparation/sealing. Valid publication runs with the
next C++ allocation armed to fail. Separate processes test fatal misuse without
acknowledging publication. Exact receipts and executable commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Complete Rocket Level 1 remains disabled. Iteration 171 adds separate prepared
publication for `CPUManagedStreamWidget` and `peek_poke_t`. `blockdev_t`, `uart_t`, FASED, all four TracerV owners, `heartbeat_t` and the
concrete FireSim driver still need audited prepared publication. Join those
owners with scheduler/bridge-loop, memory, runtime I/O, creator-side TSI, generated
RTL and harness under production exclusion before admitting a complete CPU
transaction. The generic aggregate still loads legacy owners sequentially.
Independent Rocket Level 2 remains separate; BOOM/Saturn remain pending.
Standalone Shuttle, physical FPGA validation and ASIC power remain outside scope.

## Remaining publication audit and next increment

This read-only audit identifies preparation work; none of these rows grants
prepared support or complete CPU acceptance. The source paths and hashes are
recorded in `runs/m11-iteration170/remaining-publication-owner-audit.json`.
The current four adapters cannot replace any of the following loads.

| Owner | Restorable host state beyond configuration | Preparation/publication work still needed |
| --- | --- | --- |
| `CPUManagedStreamWidget` | Inherited `StreamEngine::initialized` | Decode the one allowed flag, retain complete destination state, then publish that scalar without `init()`, MMIO or DMA. Direction, generated stream order, names, addresses, depths and beat widths remain bound. Hardware queues and runtime AXI ownership stay separate. |
| `peek_poke_t` | `req_unstable`, `req_timeout` | Decode both result bits before publication; publish scalar flags under lifetime/generation guards. Keep port maps/chunk widths and all MMIO bindings checked. Interrupted/suspended polling remains unsupported. |
| `FASEDMemoryTimingModel` | Lifecycle, complete statistics history, histogram baselines and range-counter vectors | Prepare the decoded history/vectors and seal the actual FRFCFS recipe configuration; publish fixed histogram copies, vector/string swaps and scalar lifecycle/replay flags. File replay remains a later ordinary service, with external output/descriptor policy audited separately. FCFS coverage does not establish this configuration's support. |
| Four `tracerv_t` instances | Initialization, `cur_cycle`, full buffered output prefix | Prepare each complete byte vector and clock/trigger/stream binding, then publish via swap/scalars. All four instances remain separate owners. Live `FILE`, tracker, DWARF/fireperf and finished modes currently reject; an empty log is not a statelessness proof. |
| `heartbeat_t` | Epoch, timeout flag, trip count, last cycle, complete signed-elapsed sample vector | Prepare every sample and the clock configuration binding, then publish vector/scalars. Existing capture requires buffered unfinished output. Host elapsed time is diagnostic; it cannot replace target-cycle labels or generated clock-counter state. |
| `uart_t` and its concrete buffered-file handler | Six serial-data/handshake fields, immutable input bytes, input cursor, complete output bytes | Prepare the nested handler and parent together; sealing must validate both before publication. The legacy parent calls an allocating handler load. Live stdin, PTY, signals and ordinary descriptors retain explicit rejection. Finished output cannot be silently reopened. |
| `blockdev_t` | Initialized/response-pending flags, complete private disk bytes, stream cursor, all request/data/response/ack queues and every write tracker | Prepare disk/queues/trackers and a correctly positioned owned `fmemopen` stream before sealing. Preserve its backing-vector alias through publication. The legacy load creates a libc stream and closes the old stream; neither operation can simply be moved into a supposedly nonthrowing aggregate commit. Retire/cancel resources under the eventual process/descriptor policy. External disk/log modes reject. |
| FireSim `concrete_checkpoint_t` | Running/fresh/finalized driver lifecycle; separate scheduler and bridge-loop owners retain credits/deadlines/cursor/termination | Prepare a running-source flag for a strictly fresh unfinished destination. Capture of a fresh driver's source image already rejects, so destination sealing needs its own explicit fresh-state stamp rather than calling the source-only `save_checkpoint()`. Bind registry order/identities/schemas and profile settings; set `started` without initialization, reset, stepping or finalization. |

The scalar candidates for CPU-managed stream control and peek/poke are now
implemented in iteration 171; the concrete driver's fresh-state candidate is next. The
existing configuration-only helper requires exact source/destination payload
equality and cannot restore these differing scalar values. Keep source-bound
lifetime/thread/generation checks, identical-byte legacy-load invalidation and
allocation-failure cancellation. Later vector/string candidates must prepare all
replacement storage; no adapter may defer its allocating legacy load to
`publish()`. Ensure derived classes cannot inherit an incomplete prepared adapter.

These are returned-call boundaries. `blockdev_t::save_checkpoint()` also calls
`fflush()` before reading its private backing bytes and stream cursor: treating
that function as a side-effect-free arbitrary destination observer would need an
additional audit. Resource acquisition, old-resource retirement, signal/thread
exclusion and creator-side TSI coordination remain aggregate responsibilities.
Normal uninterrupted controls with live logging do not establish checkpoint
admission for those modes; the existing buffered/finite-input runtime modes
must be bound and tested explicitly at complete CPU cuts.
