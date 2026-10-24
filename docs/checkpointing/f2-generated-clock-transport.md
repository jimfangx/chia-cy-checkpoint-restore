# Generated physical clocks connected to capture transport

Iteration 220 connects the hierarchy-preserving clock network from
`PhysicalClockCutWiring` to `CheckpointPhysicalCaptureTransport`. Set
`EXTERNAL_CLOCK_NETWORK=1` and connect its `clock_mask` output to the generated
network's mask input. The generated network receives the raw source clock;
its unmasked logical CE output feeds the physical sampler. The descriptor,
bank response endpoint, controller and MMIO/DMA transport keep the raw clock.
No duplicate internal clock gates are instantiated. The default transport mode
retains its original internal gates.

The new `PhysicalClockCaptureNetworkSpec` emits an independent three-native-gate
fixture through the real compiler. Its sole external CE input is reset. In
this composition the **same raw synchronous reset** drives the generated
network, physical sampler, capture coordinator, transport and bank endpoint.
Reset invalidates an unfinished capture; it is not held back from the DUT.
This is a fixture contract, not ownership for the production `F1Shim.reset`
writer or other platform inputs.

`CheckpointCaptureTransport.dma_abort` now includes reset directly. Previously
reset immediately removed the coordinator's `freeze`, potentially leaving a
complete stream waiting for publication without an abort indication. The DMA
adapter must discard its unpublished stream when abort is asserted, including
before the next source edge. The adapter and any accepted bank request endpoint
must participate in the common reset. This does not supply a production DMA
adapter, reset epoch protocol or host-owner snapshot implementation.

The EDA harness runs the exact locally synthesized RTL and original native
BUFGCE/glbl models. It exercises the original full cut/backpressure/abort/fault
scope in both internal and compiler-generated clock modes, and interrupts
freeze, outstanding bank response, stalled DMA data, complete unpublished
stream and physical release with reset. Every interruption must immediately
withdraw transfers, invalidate the stream, clear the common-reset endpoints,
then complete a new cut and resume independently checked functional execution.
The host arithmetic/CRC oracle checks every word of all complete normal cuts.
The independent structural oracle checks the generated wiring and original CE
cones. Native/EDA source and generated-input hashes must match.

Evidence and exact commands belong under
`automations/checkpoint_loop/runs/aws-f2/iteration220/`; its summary and
verification command list record the actual completed checks. Native synthesis
is OOC on the F2 part, not a placed/routed checkpoint-enabled Rocket image.

Production banking still rejects physical BUFGCE state. Bind the complete
Rocket reset/external writers, physical CE bank IDs and zero-edge metasim
adapters; translate production annotations/XDC and connect complete generated
state banks, functional memory, timing/bridge/host owners and pre-FAME semantic
capture at the same cut. Full localhost image/P&R/AFI, active four-hart FPGA
cuts and the independent paired restores/finite replay/live RTL/rolling
hardware recovery remain required. All CPU hardware acceptance entries stay
pending. Reuse iteration194's localhost build invocation and preserve native
build jobs/AFI IDs. Do not deploy this fixture as a capture image.
