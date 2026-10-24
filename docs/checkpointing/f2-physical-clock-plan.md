# Rocket physical clock cut prerequisites

Iteration 217 adds `--simulator-physical-clock-plan` to the actual Golden Gate
compiler. It requires one complete root inventory and rejects bank-probe or
semantic-map requests in the same invocation. It runs against the emitter's
actual final netlist, leaves that netlist unchanged, and emits
`.physical-clock-plan.json` and `.physical-clock-plan-emission.json` bound to
the exact reference, inventory and Verilog hashes. It **does not enable capture**.

The exact QuadRocket recipe resolves three source-checked default-SYNC BUFGCEs:

| Index | Instance below `F1Shim.top` | CE driver in its parent |
| --- | --- | --- |
| 0 | `FASEDMemoryTimingModel_0.gate` | `gate_CE` |
| 1 | `sim.target.FireSim_.clockBridge_clocks_0_buffer` | `clockBridge_clocks_0_buffer_CE` |
| 2 | `sim.target.FireSim_.clockBridge_clocks_1_buffer` | `clockBridge_clocks_1_buffer_CE` |

All three sources and all **13,234 sequential consumers** resolve to the common
root input `clock`. The plan includes **2,107 clock pins** and clock coverage
for all **11,459 simulator inventory entries**. Consumers comprise 10,280
registers, 779 sequential memory ports and 2,175 clocked print/stop/verification
effects. Asynchronous memory readers have no sequential clock obligation;
synchronous reader/readwriter pipelines remain linked to their original ports.
FAME clock tokens carried as data retain data/constant/invalid provenance and
cannot become a functional clock source by appearing on a Clock-typed port.

Final VerilogPrep instance connectors are expanded solely in the analysis view.
Every public pin, direction, width and connection is checked. Exact native
gates get temporary analysis bodies for source resolution; those bodies never
reach a bank generator or an emitter. Unknown external owners, native source or
parameter overrides, unrelated roots, computed functional clocks and cascaded
physical gate sources reject. The existing unconditional physical bank guard
remains. A physical transparent-low CE latch gets a distinct proposed StateID;
its mapping to metasim's `O` register remains explicitly pending.

The independent Python audit reconstructs instance connectivity, native
definitions, clock origins, sequential consumers and inventory-clock coverage
from FIRRTL. It rejects 15 coherent plan/binding mutations, including dropped
state/consumers/pins, CE/source/index changes, physical-to-metasim StateID aliasing
and false capture/CE-closure claims. Scala covers repeated hierarchy, emitted
connectors, separate roots, cascades, changed native sources, memory pipelines,
stale inventories, output collisions and invalid request combinations.

Next, implement the actual generated clock rewrite and CE bank/restore adapter:
every functional owner and CE driver must use the generated root/derived gates,
while transport stays ungated. Bind every external CE/reset/memory writer and
the authoritative FAME target counter to the same post-stop cut. Keep the
physical guard until all ownership and annotation/XDC translation survive
generation and independent readback. Topology alone proves neither atomic
capture nor CE dependency closure.

Reuse the initialized iteration194 ExternallyProvisioned localhost invocation.
Full image/P&R/AFI, FPGA deployment, active four-hart captures, hardware-origin
zero-edge restores, finite replay, sustained live clean-RTL comparison and
rolling recovery remain pending. Current commands, successful outputs and failed
trials are retained under `automations/checkpoint_loop/runs/aws-f2/iteration217/`;
no component or compiler result is an FPGA checkpoint receipt.
