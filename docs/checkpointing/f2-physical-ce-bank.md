# Physical CE StateIDs and bank endpoint

Iteration 221 adds a read-only companion to the opt-in physical clock wiring
probe. The exact Rocket compiler emits `physical-clock-state-bank.json` and
`physical-clock-state-bank.sv`. Every original native gate has its own one-bit
physical CE StateID, slot and captured-CE bit index. These IDs use the physical
latch namespace from the topology plan; they never reuse a metasim `O` ID.
The companion is separate from both the simulator inventory and the Level-2
semantic manifest. It does not replace either complete inventory.

The current three Rocket entries, in bit/slot order, are:

| Slot | Original native gate |
| --- | --- |
| 0 | `F1Shim.top.FASEDMemoryTimingModel_0.gate` |
| 1 | `F1Shim.top.sim.target.FireSim_.clockBridge_clocks_0_buffer` |
| 2 | `F1Shim.top.sim.target.FireSim_.clockBridge_clocks_1_buffer` |

Bank 255 is reserved for this endpoint. Each descriptor is width 1, depth 1;
only address zero is legal. A future complete arbiter must enforce that bank
reservation. The endpoint takes the physical sampler's **unmasked**
`captured_ce` and `read_enable`, on the ungated common source clock. It does
not read the masked-zero primitive latch or infer state from its output clock.
The sampler, transport and accepted-request endpoints require the same reset.

An accepted request latches the entire data/error response. It remains stable
under backpressure, including after physical release, until the receiver drains
it. A ready receiver can accept a replacement request on that same edge.
Requests outside an acknowledged cut, foreign banks, nonexistent slots and
nonzero addresses return zero data and an explicit error. Invalid descriptor
indices return an invalid, zero-shaped descriptor. Reset withdraws request
readiness immediately and cancels the held response at the common reset edge.
Transport abort and publication rules still govern whether a latched response
may become part of an image.

The manifest binds the exact reference, inventory, topology, original CE
dependency document and generated endpoint bytes. An independent Python oracle
reconstructs concrete native instances and both StateID namespaces, then checks
every entry and all scope/reset contracts. It rejects missing owners, selector
aliasing, changed shapes, stale RTL and unsupported capture/restore claims.

Verification uses the exact Rocket-generated endpoint with the compiler's
separate three-gate active-workload fixture, common-low-phase sampler and
native vendor BUFGCE models. Native synthesis runs on localhost; VCS runs only
on EDA. Independent arithmetic checks functional state, resumed cycles and CE
words. Backpressure, invalid selections, pipelined replacement, cut release,
reset cancellation/recovery and zero functional edges during readout are
checked. Debug waves and independently compiled inverted-bit fault evidence
belong under `runs/aws-f2/iteration221/`, alongside exact commands and receipts.

This remains **in_progress component/compiler work**. A separate synthesizable
[router composition](f2-physical-state-router.md) now connects this endpoint to
functional-bank/MMIO/DMA components. Complete production arbitration and bridge
binding remain pending. Production
`F1Shim.reset`/external writers, physical CE-to-metasim zero-edge restore,
complete simulator/functional-memory/timing/bridge/host/pre-FAME same-cut
ownership, production annotations/XDC, full image implementation/AFI and real
active four-hart captures remain pending. The production BUFGCE bank guard is
retained. No actual FPGA capture, paired CPU restore, finite/live CPU replay or
rolling hardware recovery is established by this companion or its fixture.
Reuse iteration194's initialized ExternallyProvisioned localhost invocation.
