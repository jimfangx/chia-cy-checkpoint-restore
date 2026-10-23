# FPGA capture transport component

Iteration 177 adds `CheckpointCaptureTransport.sv`, connected to the existing
`CheckpointCaptureCut.sv`. This is a synthesized component with an EDA VCS
fixture, **not a CheckpointBridge integrated into the Rocket FPGA image**.
The exact CPU recipe and its initialized manager configs remain unchanged.

Iteration 178 adds `GeneratedStateBankAccess`, `CheckpointCaptureWidget` and
native `checkpoint_capture_t`/`checkpoint_capture_session_t`. Generated storage
and the real FireSim control/stream interfaces now have independent component
verification. FPGATop registration, complete Rocket ownership/mapping and
physical checkpoint-image deployment are still required; these classes do not
enable CPU admission by themselves.

Iteration 179 adds `CheckpointCaptureDescriptors.fromGenerated`: complete
ordered bindings and both reference/instrumented circuit hashes are checked
against the independent inventory before one immutable descriptor set is
constructed. `CheckpointCaptureDescriptorROM` returns invalid all-zero outputs
for every out-of-range 32-bit ordinal. When Widget parameters include this
descriptor set, its hash/count must match the transport and its internal ROM
drives descriptor inputs; external descriptor pins have no authority in this
mode. The existing external-descriptor mode remains a component interface.

The same immutable descriptors generate host `checkpoint_capture_manifest_t`
metadata (including exact little-endian digest bytes) and the actual
`checkpoint_capture_t` registry constructor. Headers retain binding SHA256,
StateIDs, MMIO base, stream allocation and transport source hashes. This joins
transport/driver compatibility; it does not supply functional-memory or host
snapshots, complete CPU ownership, or automatic checkpoint publication.

`verify_generated_capture_network_vcs` checks actual generated banks connected
to that ROM and Widget. No handwritten bank-data or descriptor source supplies
the captured state. An independent functional-input oracle checks every word
through reset/write freeze, DMA stalls, missing fixture owners and abort/reuse.
Three cuts pass **1,014** checks, **48** bank reads, **49** decoder negatives
and **2,940** ASan/UBSan host checks per cut. The exact generated C++ initializer
validates the real VCS streams independently. Deliberate semantic bit corruption
stops at the first state word at **C=30**, frozen before publication. This is
finite component checking, not live CPU comparison. Full component VCD,
canonical VCS-origin fixture images and original source/command receipts are in
`runs/aws-f2/iteration179/network-vcs-final/generated-network-0fzl_g1v/`
(relative to the loop). The native localhost bank/Widget-with-ROM synthesis
reports **138 / 1,725 LUTs**, **67 / 692 registers**, and estimated setup slack
**+6.298 / +4.425 ns** at 140 MHz for the F2 part. Full Rocket synthesis/P&R,
AFI creation, deployment and hardware capture remain pending.

After elaborating `CheckpointCaptureDescriptorsSpec` with
`-Dcheckpoint.widget.out=DIR`, run on EDA:

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_generated_capture_network_vcs \
  --generated DIR/generated-network \
  --out automations/checkpoint_loop/runs/aws-f2/iteration179/network-reverify
```

The opt-in LowForm generator checks the entire current input inventory before
specializing modules per instance. It reads actual registers and added logical
asynchronous RAM ports, gates functional reset/update/write with `ckpt_freeze`,
and returns registered responses held until consumption, even after release or
abort. Dedicated `ckpt_reset` is independent of functional reset. State wider
than 64 bits/deeper than 65,535 words, synchronous/readwrite RAM pipelines,
opaque/derived-clock/analog state, side-effecting statements and annotations
without explicit clone/rename support reject. Derived CombinationalPath caches
are invalidated and recomputed. The generated simulator and semantic StateIDs
remain separate. The fixture verifies 16 storage words; no whole-CPU coverage
is inferred.

The controller accepts a capture only while idle, freezes on the accepting
edge, waits for every declared owner, and reads logical bank words through
request/response handshakes. Descriptors come from an immutable generated ROM:
manifest ordinal, bank, slot, logical width and depth. Each descriptor is
latched before any bank request. Exactly one read can be outstanding. Bank
request and DMA payloads remain stable under backpressure; response latency
need not be fixed. Data with nonzero width padding rejects. Unsupported or
missing descriptors reject explicitly; this component supports widths 1–64,
1–65,535 entries, 8-bit bank and 16-bit slot selectors. Automatic wide-state
chunking and complete Rocket ownership remain required work.

The transport clock continues throughout freeze. All functional writes, resets,
token/channel movement, memory updates and host owners must honor the same
cut. Functional target reset must not reset the cut/transport controller.
Resetting the controller requires coordinated reset of the bank and DMA
endpoints; resetting it alone is not a cancellation protocol. An accepted bank
request must produce exactly one response, including on failure or abort.

An owner error, lost freeze, cycle drift, invalid descriptor, bank error or
noncanonical data invalidates the entire unpublished DMA stream and retains
freeze. An explicit abort releases owners and invalidates/flushes the stream.
If a bank read was already accepted, its response is discarded and a new
capture remains inadmissible until draining completes. An unresponsive endpoint
therefore prevents reuse rather than contaminating a later snapshot. The
bank must latch everything needed to return that response before accepting
its request. Premature publication reports an MMIO error and fails frozen.

The transport's MMIO interface is a single-request protocol with a backpressured
response; the global Widget adapts it to real FireSim NASTI. Register addresses
are byte offsets, all transfers are 32 bits, and writes to read-only/unaligned
addresses reject. Command values are exact, not composable bit masks.

| Address | Operation | Meaning |
| --- | --- | --- |
| `0x00` | write | `1` start, `2` publish/release, `4` abort |
| `0x04` | read | bit 0 ready, 1 freeze, 2 read enabled, 3 complete, 4 failed, 5 draining |
| `0x08` | read | bits 0–4 cut errors; 16 invalid descriptor, 17 bank error, 18 padding error, 19 sequence overflow |
| `0x10`, `0x14` | read | low/high halves of authoritative target cut |
| `0x18`, `0x1c` | read | low/high halves of transferred state-word count |
| `0x20` | read | generated entry count |
| `0x24` | read | complemented running CRC32C |
| `0x40` … `0x5c` | read | manifest SHA-256, least-significant 32-bit word first |

The global Widget wraps this request/response adapter in actual 32-bit FireSim
NASTI, independently buffers AW/W and holds all responses. It allocates a
256-byte control region and a real 512-bit StreamToHostCPU. Its clock continues
during the common freeze. Invalid/alignment/width/strobe/burst operations return
SLVERR without forwarding side effects. It adds these Widget-only registers:

| Address | Operation | Meaning |
| --- | --- | --- |
| `0x60` | read | bit 0 invalid shared stream; bit 1 lifetime frame-count overflow |
| `0x64` | write | exact `1`: acknowledge drain, only if producer quiescent and host count equals produced count |
| `0x68`, `0x6c` | read | cumulative accepted DMA frame count; low read latches a coherent high half |
| `0x70`, `0x74` | read/write | host cumulative consumed/discarded frame count for drain acknowledgement |

The produced counter survives capture, publication and abort, saturating with
sticky failure on overflow. Only a coordinated endpoint/stream reset clears
its epoch. An empty nonblocking pull does not establish drain completion;
the host must consume/discard every accepted frame and provide the exact
count. A new start stays blocked until acknowledgement succeeds. Shared
stream queues are not reset by a transport abort.

DMA frames are 64 bytes, little-endian at each integer field. `dma_last` marks
only the trailer. A generated manifest hash must be nonzero. The stream is a
transport envelope, independent of canonical checkpoint container formats.

| Bits | Common / header / data / trailer |
| --- | --- |
| 0–63 | magic bytes `FSMCKPT1` |
| 64–79 | version 1 |
| 80–95 | type: 1 header, 2 state word, 3 trailer |
| 96–159 | authoritative target cut |
| 160–223 | header zero; data zero-based word ordinal; trailer total words |
| 224–255 | header entry count; data entry ordinal; trailer CRC32C |
| 256–287 | header manifest hash starts at bit 256; data logical address |
| 288–303 | data logical bit width |
| 304–311 | data bank |
| 312–327 | data slot |
| 328–335 | data status, currently zero |
| 336–399 | data word |
| 400–511 | data reserved zero; header manifest hash ends at bit 511 |

Trailer bits above 255 are zero. CRC32C uses the reflected Castagnoli
polynomial `0x82f63b78`, initial state `0xffffffff`, and final complement.
It covers every byte of the header and every data frame, excluding the
trailer. The host decoder also independently checks the trailer's common
fields, count and reserved bits. CRC detects transfer corruption; it does not
authenticate provenance or establish complete state ownership.

`tools/checkpoint_formats/fpga_transport.py` validates complete length, manifest
compatibility, cut labels, word order, selectors, widths, padding, reserved
bits and CRC before returning any state. Its Level-2 adapter produces the
existing canonical `.rtlckpt` representation. This does not implement Level-1
ownership. The new C++ driver uses actual MMIO and StreamEngine calls, with
page-aligned bounded nonblocking transfers, independently supplied immutable
descriptor metadata, complete frame/CRC/cut/count validation and an explicit
post-publication release. Raw state bytes are exposed only after validation.
Transfer faults poison the session; abort drains against the cumulative
hardware frame count. Unknown consumed byte counts require coordinated reset.
The global coordinator must still snapshot all software/memory owners,
validate both independent images and trace, atomically publish without
overwriting valid history, and then authorize release. The new driver retains
the default unsupported aggregate checkpoint schema.

Fresh EDA verification (source the remote build environment first, then
`vcs-env.sh` last):

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_fpga_transport_vcs \
  --out automations/checkpoint_loop/runs/aws-f2/iteration177/transport-verified
```

The runner creates a unique directory with frozen sources, compiler argv,
native logs, fixture manifest/binding, actual public-port frames, canonical
component image and hashes. The fixture's independently sampled register/RAM
values are compared against every handshake. It exercises delayed bank reads,
DMA/MMIO stalls, five complete publications, malformed descriptors, owner
failures, lost freeze, cycle drift, stale-response draining, early publication
and fresh capture after failure. The strict host decoder rejects 39 damaged
variants of the actual VCS-produced stream, including rechecksummed semantic
framing corruption. This finite component test establishes no CPU live-shadow
or physical FPGA acceptance.

Local native Vivado synthesis uses `capture_transport_synth.tcl`,
`xcvu47p-fsvh2892-2-e`, 16 owners and 1,024 entries, with 140 MHz constraint.
The component uses 2,055 LUTs and 423 registers. Estimated post-synthesis
register-to-register setup slack is +4.816 ns; this is not routed F2 timing.
The HDK setup must be sourced from its own repository directory. Run through
the local F2 helper with backend `f2`; never synthesize on EDA.

Fresh iteration-178 runners (all VCS on EDA) are
`verify_generated_bank_vcs`, `verify_checkpoint_widget_vcs` and
`verify_fpga_capture_host` in `tools.checkpoint_formats.tests`. Generated inputs
come from `GeneratedStateBankAccessSpec` and `CheckpointCaptureWidgetSpec`;
native localhost synthesis uses `capture_components_synth.tcl`. Each runner
retains exact sources/generated artifacts, raw commands and native logs under
loop `runs/`. No fixture image is relabeled as FPGA origin.

Next: insert generated access into the real compiler flow with complete
independent simulator/semantic mappings and descriptor ROMs, support the real
Rocket memory/width/annotation cases, connect global write/reset/token freeze,
register the global Widget and its stream in FPGATop, and join complete
functional-memory/FASED/host ownership. Then build the exact checkpoint-enabled
Rocket recipe on localhost, create/bind AFI/AGFI and driver manifests, deploy
and capture actual F2 execution at every required cut. FPGA-reference
continuation, independent fresh EDA Level-1/Level-2 restores, sustained live
comparison beyond trace, waveforms and rolling FPGA recovery remain pending.

Use the existing [F2 workflow](aws-f2-workflow.md) and official
[custom-image guide](https://docs.fires.im/en/latest/getting-started-guides/aws-ec2-f2-getting-started/building-a-firesim-afi/).
