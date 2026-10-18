# Prepared publication for mutable scalar host owners

Iteration 171 adds explicit prepared-publication adapters to the final concrete
`CPUManagedStreamWidget` and `peek_poke_t` classes. Stream host state is the
inherited initialization bit; peek/poke host state is the returned-call unstable
and timeout bits. Existing v1 payloads and flag masks are unchanged. Generated
stream queues, FAME/token/channel state, MMIO/DMA transport, caller buffers and
DUT ports remain separate owners.

Each candidate validates the entire source configuration/payload and retains the
complete destination bytes before publication. Stream bindings include direction,
generated order, name, DMA/count addresses, depth and beat width; peek/poke binds
all MMIO addresses, port names, chunk widths and direction. Source flags may
differ from destination flags. These owners cannot use the configuration-only
adapter's equality rule.

Sealing checks the candidate's lifetime, native thread, generation and consumption
before dereferencing its owner, then compares every destination byte. Publication
is allocation-free `noexcept`: it consumes the guard and assigns only the decoded
scalars. It does not call `init()`, MMIO, DMA, reset or stepping. Identical-byte
legacy loads invalidate candidates. Both owners are noncopyable/nonmovable.
Suspended and interrupted services retain their existing explicit rejection.
The coordinator must retain exclusion from sealing through aggregate readback;
these adapters do not implement process/thread/signal/descriptor/parser exclusion.

The maintained native ASan/UBSan and time-zero VCS DPI matrix compiles the actual
production methods with deterministic MMIO/DMA and wall-clock fixtures. Twenty
service cuts span stream initialization, transfers with data and full/empty
queues, flushes, scalar/GMP peeks and pokes, step/done checks and both timeout
paths. An independent Python oracle serializes every payload byte and compares
every service request, response, DMA byte, GMP result and result flag. Fresh
process readback precedes any service call. Cuts are service cursors, not Rocket
target-cycle labels.

Negative checks cover every truncation/configuration-byte mutation, all reserved
flag bits, trailing bytes, wrong owners, changed destinations, suspended and
interrupted services, cancellation before/after sealing, repeated sealing,
consumed/stale/legacy-load/expired/wrong-thread candidates, all eight legal flag
combinations from differing destinations, and every C++ allocation in paired
preparation/sealing. Valid publication runs with allocation failure armed. Fatal
misuse checks cannot acknowledge publication. Exact receipts and commands are in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Complete Rocket Level 1 remains disabled. The concrete driver's fresh lifecycle,
blockdev, UART, FASED, four TracerV owners and heartbeat still need prepared
publication. Join all owners with generated RTL/harness, functional memory,
runtime I/O, scheduler/bridge-loop and creator-side TSI under production exclusion.
The generic aggregate still loads legacy owners sequentially. Independent Rocket
Level 2 stays separate; BOOM/Saturn remain pending. Standalone Shuttle, physical
FPGA validation and ASIC power remain outside scope.
