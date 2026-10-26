# Transport control-state readout

Iteration 242 adds a separate [atomic shadow staging component](f2-transport-control-snapshot.md).
It copies this live vector in one edge for immutable bank reads. The production
widget and complete capture/restore ownership remain unbound.

`CheckpointPhysicalCaptureTransport.control_state` now exposes every sequential
source register in the transport, deferred cut coordinator and physical cut controller.
The transport exports 411 bits; the physical controller adds `70 + GATES` bits.
There are 24 registers and `481 + GATES` bits in total. The falling-edge
`physical.freeze_low` register is included. Vendor BUFGCE latch state remains a
separate physical owner.

The implementation uses direct synthesizable ports and concatenations. It adds
no sampling registers and preserves the existing MMIO, framing, abort, drain and
clock-mask behavior. `CheckpointTransportControlState` describes each field's
offset, width, clock edge and reset value. It pins all four implementation source
hashes and checks the concrete external module, specialization, readout ABI and
inline sources. Its generated combinational bank returns 64-bit words in ascending
LSB-first order, zero-pads the last word and rejects out-of-range words.

This is **live observation**, not an atomic multiword snapshot or a restore
adapter. These controllers continue to advance while the target is stopped.
Reading successive live words through an active transport cannot establish a
common cut. The registered widget currently leaves this output unused; a future
explicit owner must connect it and implement a coherent capture/restore protocol.
The ordinary simulator inventory still rejects the opaque transport, and the
unbound widget still cannot emit a production image. Descriptor/driver identity,
the checked production graft and complete stream/MMIO, FASED, functional DRAM,
reset, external writer, host and pre-FAME ownership remain required.

Vivado also creates internal FSM encoding registers. The native audit records
these separately, including source locations and `FSM_ENCODED_STATES`, and keeps
their capture/restore mapping unsupported. Source-register observation must not
be mistaken for a dump of every synthesized storage bit. The audit checks the
clock pin polarity and accounts for every native register cell, including these
additional encodings; it never waives their ownership.

The independent Python auditor reconstructs storage from sequential writes and
declarations, checks clock edges and reset assignments, then follows the actual
packing order through both nested controllers. Combinational `dma_data` and CRC
function locals are excluded because they are not sequential storage. Tests
reject missing or repeated fields, new unexported registers, multiple writers,
omitted nested state and changed clock/reset semantics.

The new verification harness synthesizes the actual transport with native
Vivado on this server. All protocol/descriptor inputs remain exposed so a fixed
fixture ROM cannot hide registers. It checks every field's retained registers,
their raw clock and the single falling-edge mask. EDA VCS independently compares
the exported vector against all actual registers and tests every bank word,
including padding and invalid addresses, during capture, backpressure, faults,
abort and reset recovery. A separately compiled equal-width field swap must
diverge against that independent oracle. Hierarchical reads are confined to the
component test oracle; they are not FPGA checkpoint extraction.

Iteration 241 passes 262 Scala, 318 checkpoint Python and 40 loop tests, 26
native synthesis scopes, 45 EDA scopes and retained host/sanitizer/FCFS checks.
The new readout compares 5,051 samples and 50,510 words across eleven scenarios,
retains 13 debug waves and rejects a separately compiled field swap at cycle 2,
sample 75. Native synthesis accounts for 500 register cells and separately records
five FSM encoding registers whose capture/restore mapping remains unsupported.
Original audit failures and their repairs remain available.

The production fixture was transformed from its actual retained iteration-239
compiler input. Fresh iteration-241 generation has identical RTL and complete
storage annotations, with a distinct target-directory/history epoch. Both complete
contexts are preserved and audited against their respective producers; no history
hashes are normalized. Fresh exact-recipe compilation still rejects the missing
FASED physical CE owner and common cut.

Commands, native results, EDA logs, component waves and final receipts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration241/`. No checkpoint-enabled
image, new AFI, physical capture or CPU migration acceptance is established.
