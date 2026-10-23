# FPGA capture transport component

Iteration 177 adds `CheckpointCaptureTransport.sv`, connected to the existing
`CheckpointCaptureCut.sv`. This is a synthesized component with an EDA VCS
fixture, **not a CheckpointBridge integrated into the Rocket FPGA image**.
The exact CPU recipe and its initialized manager configs remain unchanged.

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

The MMIO interface is a single-request adapter protocol with a backpressured
response. It still needs a real FireSim control-bus adapter. Register addresses
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
ownership or an actual PCIe driver. The eventual host driver must snapshot all
software/memory owners, validate both independent images and trace, atomically
publish without overwriting valid history, and check publication acknowledgement.

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

Next: generate and audit complete independent simulator/semantic bank bindings,
implement synthesized register/RAM endpoints and global write/reset/token
freeze, integrate real FireSim MMIO and DMA stream widgets, and join complete
functional-memory/FASED/host ownership. Then build the exact checkpoint-enabled
Rocket recipe on localhost, create/bind AFI/AGFI and driver manifests, deploy
and capture actual F2 execution at every required cut. FPGA-reference
continuation, independent fresh EDA Level-1/Level-2 restores, sustained live
comparison beyond trace, waveforms and rolling FPGA recovery remain pending.

Use the existing [F2 workflow](aws-f2-workflow.md) and official
[custom-image guide](https://docs.fires.im/en/latest/getting-started-guides/aws-ec2-f2-getting-started/building-a-firesim-afi/).
