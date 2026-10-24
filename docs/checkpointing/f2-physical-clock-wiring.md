# Generated physical clock mask wiring

Iteration 218 adds `--simulator-physical-clock-wiring-probe`, requiring the
complete root inventory and physical clock plan. The actual Rocket compiler
emits separate `.physical-clock-wiring.fir`, `.sv`, `.json` and emission-binding
files. The normal simulator output is unchanged. These files are explicitly
**nondeployable probes**, with capture and CE dependency closure marked false.

The generator preserves each original native SYNC BUFGCE and its hierarchy.
One additional root BUFGCE masks ordinary root-clock consumers. Dedicated
source-clock ports carry the ungated source to every original native I pin;
their original CE drivers feed both the logical CE output vector and a masked
native CE pin. Repeated and nested module instances retain separate CE bits,
ordered by complete gate hierarchy.
An external transport/controller can use the raw source; existing production
MMIO/DMA separation remains pending. The mask must change only at the common
source's falling edge.

The exact QuadRocket probe has four native gates: the new root plus the three
original FASED/target gates. Independent reconstruction checks 488 reachable
module definitions, 5,037 sequential-consumer definitions and every original
driver, storage/reset declaration, hierarchy connection and clocked effect.
The original topology plan still covers all 13,234 instantiated consumers and
11,459 simulator inventory entries. Eight coherently rehashed wiring/binding
corruptions reject; the retained topology audit also rejects its 15 mutations.

Final emitter IR contains internal operations such as `addw` and `subw` that
cannot be parsed back from textual FIRRTL. The generator therefore resolves
fresh types/kinds/flows directly in memory and checks them without rerunning
functional arithmetic or memory lowering. Existing emitted connectors are
expanded in the separate generated netlist with exact port directions.

`CheckpointPhysicalClockCut.EXTERNAL_CLOCK_NETWORK=1` exposes `clock_mask`
and instantiates no duplicate gates. Its existing post-stop CE/cycle sampler,
fault checks and registered release drive the generated network. The default
mode retains the component's internal gates under `internal_clock_network`;
the independent native-latch test observes that explicit hierarchy.

The generated fixture connects this real sampler to repeated native-gated
state and a 64-bit cycle owner. Native localhost synthesis and fresh EDA VCS
exercise the composition, while retained default-cut and bank/MMIO/DMA
regressions remain separate. Native OOC synthesis retains three SYNC gates and
one falling-edge mask register, using **47 LUTs / 151 registers**. At 140 MHz,
estimated setup slack is **+2.750 ns** and unplaced hold slack is **-0.072 ns**;
this does not establish implementation timing closure. EDA SP2 VCS passes
**1,813 checks**, cuts **0/17/128/256**, 64 stalled cycles and continuation to
320 functional cycles. A test-only CE expectation mutation stops at cycle 17
before an edge acknowledgement; two full debug VCDs are retained. The original
vendor global-reset startup interval is preserved. Commands and original failed trials are under
`automations/checkpoint_loop/runs/aws-f2/iteration218/`. This is component and
compiler evidence, never a hardware checkpoint receipt.

Next, bind this wiring into the production bank/capture pipeline with complete
annotation/XDC translation, external CE/reset/memory writer ownership, physical
latch bank IDs and metasim restore adapters. Bind FAME target time, memory,
timing, bridges, host and pre-FAME semantic state to the same cut, and connect
ungated MMIO/DMA control. The strict physical bank guard remains enabled.

Full localhost image synthesis/P&R/AFI, physical deployment and all active
four-hart FPGA cuts remain pending, as do hardware-produced paired zero-edge
restores, finite replay, sustained live RTL and rolling recovery. Reuse the
initialized iteration194 ExternallyProvisioned localhost invocation; no new
runtime instance or AFI was requested by this increment.
