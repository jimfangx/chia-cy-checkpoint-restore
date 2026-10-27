# Existing widget connection for sibling native regions

`NativeCheckpointRegionWidgetGraft.connect` connects the shared region readout
at the original enclosing root to the actual reserved checkpoint widget. It
routes twenty typed signals through concrete ancestor ports with reversed
transport directions, internalizes the root capture ports, and replaces the
widget's annotated return placeholders. Original functional instance paths,
public root ports and raw-clock control execution remain in place. This allows
DUT and FASED sibling regions to share the existing MMIO/DMA transport.

The connector reconstructs the region banks and validates actual pre/post-inline
reservation history, descriptor counts, CE ordering and source circuits. Typed
storage annotations are projected over the complete host and merged with the
generated native constraints. An exact unchanged peer-host `HostClockSource`
contract is supported; other unknown metadata targeting changed definitions
rejects. The current source policy is deliberately limited to `NoCircuitDedupAnnotation`;
production compiler context and source contracts need explicit projection.
Descriptor identity, complete cut ownership and image admission remain
separate requirements. New adapter/router state and generated mask-gate/control
state also need capture or explicit exclusion/restore ownership before admission.

The reserved physical transport is opaque to FIRRTL inventory. The immutable
`ReservedCheckpointInventory` permission checks the actual widget ABI, parameters,
inline sources and compiler history. Only global inventory/clock/dependency
analysis uses a temporary view with invalid transport outputs and no invented
storage. Every instrumented and emitted circuit retains the original transport
external module. The permission and all region descriptors explicitly retain
that unsupported external owner. The default complete inventory continues to
reject it. This analysis permission supplies no capture or restore adapter.

The directed fixture places `sim.network` and a distinct `peer` under the same
existing `FPGATop`, itself beneath `ReservationShell`. The peer writes different
RAM data, making crossed regions observable. Its fourteen descriptors cover ten
functional entries and four physical CE identities. The real registered widget,
NASTI control path, CPU-managed DMA queue, baseline stream, backpressure and common
reset remain present. This is component evidence; the fixture is not a CPU or an
FPGA checkpoint donor.

Final iteration-256 verification passes 283 Scala tests / 43 suites plus twelve
preparation tests, 330 Python / 45 manager tests and all twelve native/EDA scopes.
The widget fixture passes 8,157 checks / four cuts / 272 words / 1,716 stalls.
Independent waveform checks retain 4,064 frozen samples and the compiled payload
defect at cut 81 / word 32 / entry 5, with the target still held. Twenty coherently
rehashed structural mutations reject. The original host census retains 550
uncovered functional entries / 638 words and the explicit opaque transport owner.

Native synthesis uses complete final-host XDC emitted by the compiled native
FIRRTL pass and independently reconstructs both retained RAM hints. Four exact
literal board-pad placements are preserved and deferred outside this OOC root.
Resources are 5,276 LUTs / 1,979 registers / six BUFGCEs. Setup/hold estimates
−0.031/−0.074 ns at 140 MHz have unconstrained I/O and establish no timing closure.

Verification evidence belongs under
`automations/checkpoint_loop/runs/aws-f2/iteration256/`. Exact-Rocket enclosing
state, functional memory, reset/external writers, bridge/host owners, pre-FAME
mapping and production common-cut admission remain incomplete. No checkpoint
image/P&R/AFI, hardware-origin image/trace, paired CPU restore, live RTL or rolling
hardware recovery follows from this connector.
