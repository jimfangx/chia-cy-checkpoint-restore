# Prepared scheduler and bridge-loop publication

Iteration 169 adds the default-unsupported
`checkpoint_owner_t::prepare_checkpoint_publication` contract. Audited owners
return a candidate that owns its replacement storage. `seal()` completes all
throwing validation and destination checks without publishing. `publish()` is
`noexcept`; the caller must retain exclusion through complete aggregate readback.
Destroying an unsealed or sealed candidate cancels without changing the owner.
An audited legacy schema does not automatically enable this interface, and the
interface never falls back to an allocating legacy load during publication.

The production `systematic_scheduler_t` and `bridge_run_loop_t` implement this
contract. Scheduler preparation retains every issued-credit/deadline word and
binds maximum-cycle settings, callback order, first deadlines, identities and
schemas. Callback closure state remains separately owned. Bridge-loop
preparation retains phase, next bridge index, termination and signed exit status,
with the existing bridge-count and phase validation. Neither adapter invokes a
callback, bridge service, MMIO transaction or target edge during restoration.
Payload formats and target-time behavior are unchanged.

`checkpoint_publication_t` provides a shared lifetime token, destination-local
generation, candidate-native-thread identity and sealed/consumed guards. Weak
candidate handles reject expired destinations before accessing their references;
a recycled object address cannot revive a candidate. Both owners are noncopyable
and nonmovable. Legacy loads invalidate candidates even when loading identical
bytes. Sealing compares every current destination byte and rejects suspended or
poisoned calls. Publication performs only prepared scalar assignments, without
parsing, allocation or callbacks. A violated lifetime/thread/generation/consumption
contract terminates before that owner's first assignment.

These are component APIs, not production process exclusion. They do not acquire
a controller/creator lock, validate all process threads/signals/descriptors, or
detect arbitrary unsynchronized changes after sealing. They do not certify a
completed target cycle: scheduler `current_cycle` still means issued credits.
The whole-simulator coordinator must prepare all owners, seal all owners, then
publish them under exclusion and independently read back the full cut.

The maintained native ASan/UBSan and time-zero VCS DPI test uses the actual
production owners with explicitly synthetic returned-call services and two
stateless callback adapters. An independent Python oracle serializes every
scheduler/loop word, every fixture service cursor and every service event for
horizon and negative-status termination paths. Fresh component processes restore
cuts spanning loop phases, pending steps, bridge traversal, termination status
and completion. Exact readback precedes the first service call. Invalid-image
sweeps, suspended/poisoned calls, cancellation, lifetime/thread/generation guards
and exhaustive paired allocation failures test the publication contract.
These services do not simulate Rocket instructions, generated FAME RTL or
functional DRAM. See [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) for
selected receipts and executable commands.

Complete Rocket Level 1 remains disabled. The generic aggregate still loads
legacy owners sequentially. Memory, runtime I/O and creator-side TSI have separate
prepared APIs; they must be joined with these controls, remaining widgets, the
concrete driver, generated RTL and harness state. In particular, `master_t`,
`loadmem_t`, `reset_pulse_t`, `clockmodule_t`, `CPUManagedStreamWidget`,
`peek_poke_t`, `blockdev_t`, `uart_t`, FASED, all four TracerV owners,
`heartbeat_t` and the FireSim driver still need audited prepared publication
adapters before a complete CPU transaction can be admitted. Keep default
rejections rather than forwarding any of them to legacy allocating loads.
Independent Rocket Level 2 and its retained replay are unchanged. BOOM/Saturn
remain pending; standalone Shuttle, physical FPGA validation and ASIC power
remain outside the current task.
