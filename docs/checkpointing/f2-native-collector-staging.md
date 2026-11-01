# Atomic observation of the native collector and bank endpoint

Iteration 300 adds `F2NativeCollectorSnapshot.generate`, which reconstructs the
native bank/collector composition before connecting one ungated
`CheckpointNativeStateSnapshot`. Functional bank handshakes remain closed until
the collector has acknowledged its cut and the entire collector/idle endpoint
vector has been staged at one raw positive edge. Values are sampled before
that edge. Original functional storage and its bank selectors remain unchanged.

The low 66 bits contain the original response endpoint: pending at bit zero,
saved data at bits 1–64 and saved error at bit 65. The complete collector vector
follows. For the two-gate compiler fixture this is 147 bits / three words. The
staging module's own 218 bits are a separate owner: retained payload, occupied,
cut label and errors. Released payload is retained. Source hashes, ordered field
offsets, original/banked references and the connected circuit bind the schema.
The staged composition gives the response data/error registers explicit
synchronous zero initialization on the independent controller reset. Ordinary
bank access previously left these inactive bytes undefined until its first
read. Later inactive bytes are retained and captured exactly; they are not
masked or reset at each cut.

The same collector holds the cut through staging, reads, response backpressure
and host withdrawal. After accepted responses drain, an explicit idle staging
release closes both bank handshakes before the release edge. The ordinary
registered low-phase collector release then runs. Premature reads, duplicate
staging, busy release or target-label drift revoke access immediately and keep
functional clocks stopped. Owner/reset/writer faults also revoke publication
of staged words, even though the immutable bytes remain stored for diagnostics.
Controller initialization is required to recover a failed staging epoch.
Occupied state and retained errors hold the cut without feeding the live
failure/cycle-comparison cone back into its half-cycle freeze path. All faults
still revoke publication and handshakes immediately.

The compiler fixture, native Vivado implementation, EDA VCS execution and
independent pre-edge raw-wave audit are recorded under
`automations/checkpoint_loop/runs/aws-f2/iteration300/`. Verification results
and final closure are recorded in [progress.md](progress.md). The complete
retained sweep passes. Native P&R retains all 452 sequential cells / 218 staging
bits at 140 MHz (+0.878/+0.019 ns); fresh EDA VCS passes 6,505 comparisons,
36 staged-word reads and sixteen healthy/fault/corrupt runs. Independent raw-wave
auditing rejects all 147 payload and 218 owner-packing bit mutations.

This is an atomic observation component, not a complete capture/restore owner.
It does not install a second controller in the reserved widget, bypass
`liveTransportConflicts`, freeze MMIO/DMA storage, stage arbitrary synchronous
native readers, prove global target-time authority or provide staging restore.
Production selective composition with the ONE existing controller and ungated
transport remains pending, as do physical CE/FASED/functional-memory/host and
complete pre-FAME semantic ownership. Image admission and metasim restore flags
remain false. No full image/AFI, physical FPGA checkpoint, CPU migration/live
comparison or rolling hardware recovery is established here.
