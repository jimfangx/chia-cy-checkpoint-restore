# Live widget shadow readout

Iteration 262 connects an immutable staging bank to the actual
`CheckpointCaptureWidget` MMIO path. The bank samples the transport's versioned
control vector and all eight original widget-local registers on one ungated
positive clock edge. The transport and stream remain live while the host reads
that copy. The low 411 bits (or `481 + GATES` physical bits) retain the existing
transport layout. The 228 local bits follow in this order: `invalid`,
`producedFrames`, `producedSnapshot`, `hostDrainedFrames`, `counterOverflow`,
`localValid`, `localData`, `localError`. Fields are packed least significant
first. The generated driver header records widths, offsets and layout version.

The capture command requires an acknowledged coordinator cut with the exact
target label, no coordinator error, every declared owner present and frozen,
and a valid stream. Physical mode additionally requires the post-stop sampler
to acknowledge the same cut without a physical fault. Elaboration validates the
exact RTL resource hashes of the source-register schema. A freeze request alone
cannot authorize capture. Reset immediately hides the old epoch.

The MMIO window uses `SHADOW_COMMAND` at `0x78` (1 capture, 2 release, 4 discard),
`SHADOW_INDEX` at `0x7c`, low/high word reads at `0x80/0x84`, valid status at
`0x88`, low/high target label at `0x8c/0x90`, and word count at `0x94`. Reads and
invalid operations return normal AXI responses through the existing adapter.
The last word is zero padded. Indices outside the exact word count reject
without changing the previous selection. Repeated capture, uncertified cuts,
release of an empty bank, malformed commands and writes to read-only registers
reject without changing an occupied image. Release/discard never resample the
source. Consumer reads introduce no source sampling edges.

`checkpoint_capture_session_t::capture_live_widget_shadow(bits)` exposes this
window through the existing concrete MMIO driver. The caller supplies the exact
generated header width. The session requires validated frame capture with freeze
still held, checks the word count, every selector, canonical padding and both
cut labels, and returns a separate observation vector. It releases staging only
after a complete successful read. An uncertain write or read fault fails the
session closed; explicit abort/discard recovers its own staging epoch. Existing
foreign staging history is never overwritten or discarded. ASan/UBSan coverage
includes repeated observations, malformed widths, stale history, incorrect
counts/selectors/cuts/padding, missing valid status and uncertain write/release
failures. The software protocol oracle is a fixture, not physical FPGA evidence.

This is observation staging, not a complete checkpoint or a restore owner.
The eight original locals still conflict with a shell bank that tries to hold
them: connection must continue to reject that freeze. The new staging bank's
own state, NASTI adapter, stream engine, primitive encodings, functional DRAM,
host state and the remaining simulator/pre-FAME owners still need an atomic
capture/restore protocol. No image guard or inventory exemption is removed.
No full image, AFI, FPGA-produced checkpoint or CPU migration is established.

Verification and recovery artifacts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration262/`. The real-widget tests
read every word through AXI during DMA backpressure and after transport state
changes. Their oracles reconstruct the original source registers before the
accepting edge, independently of the exported control vector and staging data.
The physical fixture additionally uses the external clock network, target-label
checks, CE faults, missing owners and reset recovery. Both concrete widths have
randomized standalone protocol tests. A separately compiled staging defect must
stop at the first differing MMIO word before acknowledging its AXI read. Full
debug waveforms support a separate source-register/epoch/readback audit.

Final component verification passes 317 Scala tests / 48 suites plus twelve
preparation checks, 336 Python / 45 manager tests, seventeen native OOC and
seventeen matching EDA SP2 scopes, with full ASan/UBSan host, FCFS and cut checks
retained. All six earlier waveform audits and the new independent shadow audits
pass. The real physical-widget fixture passes six cuts / 144 word reads / 43,233
checks with 2,459 stalled cycles and reset recovery to cycle 96. Native resources
are 2,641 LUTs / 1,661 registers; 811 shadow flops include all 809 logical bits and
two native index replicas, all on the ungated positive edge. These replicas and
the staging owner still need explicit restore mapping. Source-policy OOC timing
remains negative (−0.172/−0.074 ns at 140 MHz, unconstrained I/O); there is no
full-image timing closure. Current-turn native receipt reuse is explicit, with
all changed-source or failed scopes regenerated; original failed receipts and
EDA path/snapshot diagnostics remain in `development-attempts.json`.
