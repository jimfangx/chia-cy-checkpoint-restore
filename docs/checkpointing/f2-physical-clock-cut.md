# Physical common-clock cut component

Iteration 217 resolves the actual Rocket final-emission clock topology and
inventory-clock coverage as a prerequisite to wiring this component. See
[f2-physical-clock-plan.md](f2-physical-clock-plan.md). It leaves the netlist
unchanged and does not remove physical capture-owner rejection.

Iteration 216 connects this component to the descriptor/bank/MMIO/DMA
transport with a deferred post-stop label and coordinated release. See
[f2-physical-capture-transport.md](f2-physical-capture-transport.md). Production
Rocket clock/owner integration and its compiler guard remain pending.

Iteration 215 adds `CheckpointPhysicalClockCut.sv`. This component is not yet
connected to the Rocket compiler, bank network or CheckpointBridge. The strict
physical BUFGCE rejection remains necessary. Component synthesis/simulation
cannot establish an FPGA checkpoint or CPU migration.

The interface requires one continuously running source clock and default SYNC
BUFGCEs. It instantiates one native root gate for simulator owners and one native
gate per supplied logical CE. Every CE driver, counter and other changing owner
must use those gated outputs. The transport/control domain remains ungated.
`owner_present` must come from a complete generated manifest. Negative-edge,
latch, unrelated-clock and external write owners require additional contracts.

The host holds `freeze_request` through capture. A falling-edge register masks
all gate enables during the common low phase. The next ungated positive edge
samples the complete unmasked CE vector and target-cycle label after all
functional drivers have stopped and settled. No read is permitted before that
sample. The captured logical enables map the original unmasked transparent-low
latches at the cut; the stopped physical primitive latches and outputs are zero.
There is no access to a vendor internal net in synthesized capture logic.

While stopped, missing owners, logical CE drift and target-cycle drift withdraw
read permission immediately and latch errors on the next control edge. Failure
holds the gates stopped even if the request is withdrawn; reset recovers the
component. Healthy release withdraws read permission immediately, validates faults on
one ungated positive edge, then unmasks at the following falling edge. The
next functional edge resumes ordinary clock behavior. Control and owner
inputs obey a source-clock synchronous contract. The full-width drift check
feeds the registered validation step rather than a half-cycle stop path.
Consumers must use `read_enable` as the completed capture acknowledgement;
`stopped` reports the earlier physical mask alone.

The earlier `CheckpointCaptureCut` captures a cycle label on its accepting edge.
It must not be directly composed with this delayed physical gate handshake by
assuming those two labels are identical. Integration must bind the last accepted
FAME target edge, physical stop and post-stop label explicitly, and keep every
memory, bridge, host and pre-FAME owner in that same cut. Retain fail-closed
compilation until the actual ownership and clock mapping are generated and tested.

Native Vivado 2025.2 OOC synthesis targets `xcvu47p-fsvh2892-2-e`. Its fixture
retains four SYNC BUFGCEs and exactly one falling-edge mask register, using
216 LUTs and 232 registers. Estimated setup slack at 140 MHz is +2.657 ns.
The unplaced report retains -0.072 ns hold slack; implementation timing is
pending. The first combinational release trial had -0.523 ns setup slack and
remains in its original receipt. The fixture
contains a root counter and three active gated state machines. EDA VCS SP2 uses
the exact native RTL and unchanged installed vendor BUFGCE/glbl models, an
independent uninstrumented reference and an independent target-edge counter.
The experiment captures logical cuts 0/17/128/256, holds 16 transport cycles at
each cut, reads every CE, compares against vendor low-latch observations and
compares all functional state after resuming through cycle 320. Missing-owner,
CE-drift and cycle-drift runs must stay frozen with no edge acknowledgement.
A deliberately corrupted readback expectation stops at CE bit 0 at cut 17.
These fixture failures do not establish CPU semantic-corruption acceptance.

Full debug VCDs, native DCP/reports, source/model snapshots and exact commands
are retained under `automations/checkpoint_loop/runs/aws-f2/iteration215/`.
The final audit checks native/EDA input identity and current source hashes;
coherently rehashed source substitutions must also reject.
