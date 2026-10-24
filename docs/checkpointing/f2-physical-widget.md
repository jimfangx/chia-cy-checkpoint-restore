# Physical cut in the FireSim MMIO/DMA widget

Iteration 223 adds an explicit `physicalClockGates` mode to
`CheckpointCaptureWidgetParams`. The default remains zero. A positive count
instantiates `CheckpointPhysicalCaptureTransport` inside the real NASTI/stream
widget, with `EXTERNAL_CLOCK_NETWORK=1`. The native BUFGCEs belong to the
compiler-generated simulator network. The widget creates no duplicate gates.

The optional `capture.physical` sideband carries original logical CE inputs,
the common falling-edge mask, captured CE words, stopped/read/failure status,
physical cut cycle and sticky error bits. A containing binding must connect
the logical enables and route the mask to that generated network. Transport,
NASTI, stream bookkeeping, descriptor/bank endpoints and the common sampler
use the ungated source clock and common controller reset. External memory and
host owners still require explicit present/frozen/error connections.

The existing cumulative stream accounting applies in both modes. Physical
release extends the external-owner freeze; abort invalidates unpublished bytes
and the host must drain accepted frames before acknowledging the invalid
stream. Reset immediately withdraws physical read/transfer permission.

For the registered NASTI backend, START is presented before the preceding
falling edge, so the native mask stops functional owners before the accepting
source posedge. The sampled target cut therefore equals the independent
pre-edge target count at actual adapter acceptance. The direct-MMIO fixture
asserts START after a falling edge and has a different accepting-edge offset.
Neither is a host-clock label; readout always uses the actual stopped target
counter. Debug failure paths flush waveforms before returning a nonzero exit.

The generated driver header records the physical gate count, external-network
mode and SHA256 of both physical RTL resources as well as the original logical
transport/cut resources. Physical configurations with an immutable descriptor
ROM require an ordered bank-255 tail, one width-one/depth-one descriptor per CE
bit, and reject functional descriptors that alias that reserved bank. The
current functional-only descriptor constructor cannot satisfy that condition;
the functional constructor rejects bank 255 entirely, so functional state cannot
impersonate physical CE owners. Complete physical descriptor composition and
production bank generation remain required. No unverified ROM or default owner tieoff bypass was added.

Current native/EDA auditing matches 52 inputs and 29 sources. Fresh SP2 VCS
passes 6,810 checks, six complete captures, 130 DMA stalls and reset recovery.
The independent auditor reconstructs all six seven-word frame streams and
rejects eight evidence substitutions, including valid-CRC semantic corruption.
All six debug VCDs contain execution; failure runs finish the simulator before
returning a nonzero process status, preserving first-divergence waveforms.

Verification uses the actual Scala-emitted widget, its NASTI adapter and 512-bit
stream. It connects the independent three-gate active workload network, router
and exact Rocket-generated physical endpoint. This is a component fixture,
not a complete Rocket image. Native Vivado synthesis runs on localhost; all
VCS compilation/execution runs on EDA. The entry point is
`tools.checkpoint_formats.tests.verify_physical_checkpoint_widget`, with
`vivado`, `vcs` and independent matching-receipt `audit` modes. Execution logs,
full debug waves, frames and negative evidence belong under
`automations/checkpoint_loop/runs/aws-f2/iteration223/`.

The exact Rocket production bank compile retains its physical-owner guard.
Production same-cut reset/external writers, complete simulator/functional-memory/
FASED/bridge/host/pre-FAME ownership, physical CE zero-edge metasim restore,
full image/P&R/AFI, physical four-hart active-workload checkpoints and paired
independent finite/live CPU migration and rolling recovery remain pending.
Reuse iteration194's initialized localhost build invocation. This widget mode
alone does not authorize any complete FPGA checkpoint acceptance claim.
