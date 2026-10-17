# Metasim control MMIO call ownership

Iteration 165 adds `runtime/mmio-io`, schema
`firesim.emul.mmio-io.returned.v1`, to production `simif_emul_t`. Its diagnostic
owner list now includes this adapter alongside `runtime/mmio`. The image binds
all three control AXI geometry fields and certifies a returned, unpoisoned call.
The exact Rocket header specifies `{12,32,32}`.

`runtime/mmio` owns queued requests, response buffers and read/write in-flight
flags. That image cannot restore a suspended `simif_emul_t::read` stack's result
buffer or either blocking method's return continuation. The new owner rejects
save, validation and loading during either method. Nested reads and writes
reject before submitting another AXI request. Exceptions poison the lifetime;
loading a previously returned-call image cannot erase an interrupted call.
Checkpoint hooks perform no MMIO, delay draws or target advancement.

TracerV count reads nest the CPU-managed stream wrapper around this MMIO caller.
Both returned-call owners must be idle at an accepted cut. The AXI queues, host
PRNG/pending delay, CPU stream hardware, generated state and bridge state remain
separate owners. Production CPU admission remains disabled. Existing FCFS
aggregate membership is unchanged; its completed-operation protocol already
requires the synchronous calls to have returned. The new API and diagnostic do
not establish full simulator coordination or production thread/signal/descriptor/
parser exclusion. Joining this owner into the future CPU transaction is still
required, alongside the returned stream I/O owner.

The native sanitizer and VCS DPI fixture exercises the actual production
read/write methods against an independent synthetic AXI peer. Fixture startup
MMIO and clock queries are stubbed, and the source process completes before
component restores start. Each fresh component restore reads back four complete
owners before any edge: MMIO caller, MMIO AXI queues, host timing and CPU stream
wrapper. Fixture startup's initial handoff is compensated explicitly in the
synthetic peer labels and consumes no AXI or PRNG state. This is not a CPU
checkpoint, driver continuation or DUT target-cycle test.

The peer separately backpressures read address, write address and write data,
and delays both response channels. Work covers twelve alternating writes and
reads, the highest aligned 32-bit control address, two nested stream count reads,
and host delays of one or up to seven ticks. A separate Python MT19937-64 and
AXI scheduling oracle predicts every channel handshake, returned-call label and
complete host timing payload. Every suspended queued/in-flight boundary checks
all three caller hooks and nested read/write rejection without AXI mutation.
Nested count reads also check all three stream wrapper hooks. Negative cases
cover every truncation, every byte flip through validation/loading, trailing
bytes, incompatible control geometry and both interrupted read/write lifetimes.

Exact current receipts and executable commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics remain under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration165/`.
Complete Rocket Level 1 remains in progress; Level 2 stays independent. BOOM and
Saturn remain pending. Standalone Shuttle, FPGA validation and ASIC power remain
outside this increment.
