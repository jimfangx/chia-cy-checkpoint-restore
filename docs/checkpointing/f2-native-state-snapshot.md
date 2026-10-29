# Atomic staging of native synchronous queue state

`CheckpointNativeStateSnapshot.sv` stages a complete native-reader observation
vector and its logical cut label at one positive edge of the common running raw
clock. The sampled values are those immediately before that edge. Original
storage must already be frozen, previous bank traffic must have completed, and
no borrow may coincide with capture. The caller supplies ownership/freeze
acknowledgements; this component cannot establish them for the whole simulator.

The saved payload remains immutable while borrowed RAM readers, forwarding,
shadows, selectors and response endpoints advance. A 64-bit indexed interface
reads the saved payload, zero-pads the final word and rejects invalid addresses
without wraparound. Capture and release are mutually exclusive transactions.
Every reader request must be gated by `borrow_enable`. Release removes that
permission before its edge and requires the original reader to be idle.

Missing owners, missing/lost freeze, a busy reader at capture/release, borrowing
before capture, cycle-label drift and overlapping control operations revoke read
and borrow permission combinationally. Errors latch on the raw clock and require
explicit reset. Failed attempts retain the previous payload and cannot publish
it as a valid new capture. Reset also removes permission before its edge.

The new storage is an independent owner: payload, occupied flag, 64-bit cut label
and six error bits. `control_state` exposes all of it, with payload at offset
zero, then occupied, cut label and errors. This interface does not restore those
registers, provide MMIO/DMA framing, or admit an FPGA checkpoint. Its reset must
eventually participate in the complete production ownership protocol.

The verifier consumes the exact immutable, current-source queue synthesis
receipt. It reconstructs each native observation layout from generated FIRRTL
and maps every field to its actual emitted register. A synthesized component
wrapper gates the two original request/ready interfaces until all 28 added fields
are staged together. Native RAM port counts, original StateIDs/selectors and the
untouched sibling remain independent. EDA checks use the actual emitted queue
registers as the sampling oracle, retain the complete underlying queue regression,
and separately execute the same gated wrapper synthesized on localhost.

Iteration-272 commands, native utilization/timing/DCP, fresh EDA SP2 processes,
full debug waveforms and original failure logs belong beneath
`automations/checkpoint_loop/runs/aws-f2/iteration272/`. Consult `progress.md`
for the final checked results. These are component tests: there is still no
checkpoint-enabled full image/AFI or actual FPGA-produced CPU checkpoint pair.
Production integration must connect all four Rocket queue vectors to a common
cut and bind staging/restore/transport ownership, alongside the remaining global
physical-clock, memory, timing, bridge, host and pre-FAME semantic owners.

The existing `NativeCheckpointShellStateAccess` forwards the observation ports
through the concrete shell namespace; it does not instantiate this staging
component. `NativeCheckpointRegionWidgetGraft` still rejects the eight live
MMIO/DMA self-freeze conflicts and requires its peer-host raw-clock annotation.
Keep both checks. `PhysicalClockCutWiring` separately masks ordinary root-clock
consumers while retaining raw clock access for transport. Production must prove
that the native RAM reader and snapshot actually retain the same running raw
clock while original storage is held; an ungated transport endpoint alone does
not establish that contract. The reduced wrapper demonstrates the protocol with
that clock relationship explicitly supplied, rather than admitting the current
whole-Rocket clock network.
