# Compiler-connected F2 clock/reset collector

Iteration 294 adds `F2ClockResetCutWiring`. The compiler now composes
`CheckpointF2ClockResetCut` inside the generated root, after the physical clock
and synchronous-reset rewrites. The adapter receives the original ungated
source clock. Clock mask and held functional reset become internal wires with
one adapter driver each, instead of independently driven root inputs. Native
BUFGCE instances retain their locations and original logical CE vector.

The explicit option is `--simulator-f2-clock-reset-cut CYCLE_OUTPUT:OWNER_COUNT`,
with the existing complete inventory, clock plan, clock wiring and synchronous
reset requests. It emits separate `.f2-clock-reset-cut` FIRRTL, Verilog, binding
and emission files; ordinary deployable output is unchanged. The cycle selection
must be an existing driven 64-bit root output. That checks connectivity, not
FAME target-time authority. The current Rocket shell still needs a real
bound cycle observation; neither a host counter nor an invented tieoff qualifies.
`ClockBridgeModule.tCycleFastest` counts outgoing clock tokens, and its source
explicitly permits the bridge to run ahead of the simulator. Binding that
counter alone would not establish the pre-FAME target boundary: consumed token
positions, FAME completion and each target clock still need a common-cut audit.

The six new collector interfaces are initialization, freeze request, raw
reset, raw DDR-ready, the four original shell writer bits, and the complete
owner vector. None has a default acknowledgement. An additional internal owner
compares the original root reset against the actual writer expression; a
mismatch cancels the cut rather than silently discarding the old reset port.
Writer ordering, counts, source clock, selected cycle output and all generated
file hashes are explicit in the binding. Duplicate or malformed requests,
stale plans, unsuitable cycle sources and collector definition/namespace
collisions reject. Complete-image ownership guards remain enabled.

Validation uses the actual compiler-emitted hierarchy with the adapter inside
it. The shell writer fixture retains the literal original synchronizers and
reset expression. An independent emitted original hierarchy supplies functional
state and cycle comparison. A separate waveform auditor reconstructs all 81
visible collector bits directly from the eleven actual register vectors and
checks the raw clock and every external/reset-consistency owner bit. These are
component tests, not CPU execution or FPGA-origin checkpoint readback.

Native Vivado 2025.2 exact-DCP component P&R closes unchanged requested 140 MHz
at +1.720/+0.035 ns. All 168 sequential identities survive; all 218 routable
nets route without errors, and DRC reports no violations. Component resources
are 69 LUTs, 165 registers and three SYNC BUFGCEs. Full-shell, parent-clock,
external I/O and asynchronous timing remain unmodeled.

Fresh EDA SP2 passes 4,547 checks, four component cuts, 320 active cycles,
64 collection stalls, ten cancellations and first-divergence reset-route
corruption at `left.reset`, cycle 17, without acknowledging another edge.
Cancellations test all four external owner bits and the raw reset-consistency
owner independently. Separate XOR fault injection changes only the root's reset
input, preserving the actual shell reset wire. All twelve debug waves pass
independent original-state/control/routing audits; corrupting any of the 81
packed control bits is detected against the actual eleven register vectors.
The complete compiler scope passes 360 tests / 58 suites plus sixteen preparation
checks. All 409 Python / 61 manager tests, ASan/UBSan, host capture,
generated-bank, FCFS and cut regressions pass fresh. The ordinary exact-Rocket
compiler still refuses the missing FASED physical CE owner before image emission.

Production shell installation, selective functional hold and independently
owned ungated MMIO/DMA, atomic collector/stream/transport state, complete
physical CE/reset/FASED/functional-memory/host ownership and pre-FAME semantic
mapping remain required. Full localhost image P&R, AFI/AGFI, physical active
four-hart cuts, hardware-origin paired zero-edge restore, finite replay,
sustained live RTL and rolling recovery remain pending. No hardware acceptance
column advances. Reuse the retained iteration-194 localhost build invocation.

Commands, compiler provenance, diagnostic attempts, native DCPs and raw debug
waves belong under `automations/checkpoint_loop/runs/aws-f2/iteration294/`.
