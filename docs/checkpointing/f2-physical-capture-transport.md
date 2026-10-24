# Physical cut and capture transport integration

Iteration 216 adds `CheckpointPhysicalCaptureTransport.sv`, connecting the
common-source physical cut to the existing descriptor/bank/MMIO/DMA protocol.
This remains a synthesizable component contract. The Rocket compiler still
rejects its unmapped physical owners; no checkpoint-enabled image or hardware
checkpoint is established by this integration.

`CheckpointCaptureCut.DEFERRED_CUT=1` waits for the entire `owner_frozen` vector
before sampling `target_cycle`. The default remains zero and retains the
accepting-edge behavior used by the existing generated widget and regressions.
In deferred mode, target progress during FREEZING is permitted, but label drift
once READING or COMPLETE begins fails closed. Missing owners, owner errors,
lost freeze and early publication keep their existing rejection behavior.

The wrapper adds the physical sampler as an explicit owner. Its acknowledgement
requires stopped native SYNC gates, a settled logical CE vector and a post-stop
cycle sample. That acknowledgement is combined with every external owner;
physical faults and independently sampled label disagreement become owner
errors. MMIO acceptance can coincide with the final functional edge: the
transport must publish the later settled cycle, never the accepting-edge label.
The complete data stream stays disabled until both physical and external owners
acknowledge. The three example logical CE bits are banked state in the fixture;
a production generated network must include every such physical-state mapping.

The transport's request and the external freeze hold are separate. External
owners remain held through the registered physical release and falling-edge
unmask; only then may they resume with gated owners on the next source edge.
The extended hold must not feed back into the physical request, which would
prevent release. A physical CE/cycle/missing-owner failure remains stopped after
host abort until controller reset. A healthy abort drains an already accepted
bank response before another transfer can start.

All functional clock owners and CE drivers must use the generated root/derived
clocks. External acknowledgements are protocol obligations, not proof that
functional memory, asynchronous writers, host drivers or semantic boundaries
have been covered. The actual Rocket integration must generate and audit that
complete binding, preserve outstanding work and provide host-visible physical
failure status. The existing production compiler guard remains mandatory.

The test uses actual unchanged installed BUFGCE/glbl models, an independent
source-edge/arithmetic scoreboard, delayed non-clock acknowledgements, delayed
bank responses and DMA stalls. Fresh EDA VCS compares banked root/gated/CE state,
labels and every resumed edge, and retains full debug VCDs. Host-side frame
checks independently reconstruct expected state from the target label and check
selectors, reserved bits and CRC32C. Mutations include semantic state with a
recomputed valid transport CRC. Component corruption checks do not establish
CPU semantic-corruption acceptance.

Evidence, exact commands, failed trials and native source/model snapshots are
under `automations/checkpoint_loop/runs/aws-f2/iteration216/`. Native synthesis
runs on this server; all VCS runs use EDA SP2. Full image implementation timing,
AFI creation, physical deployment, active four-hart cuts, both hardware-origin
restore levels, finite/live RTL CPU comparison and rolling recovery remain
pending in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Fresh verification passes 4,739 EDA checks through 320 functional cycles. Five
complete component snapshots at actual labels **2/19/130/258/302** each include
five state words and the independent host arithmetic/CRC check. There are 88
DMA stalls, 128 delayed-bank cycles and one accepted-read abort/drain followed
by a successful new capture. Six runtime negative cases and four host integrity
mutations reject. Seven full debug VCDs retain the healthy run, five owner/clock
fault cases and the deliberately corrupted CE readback.

The native 2025.2 OOC fixture uses **1,810 LUTs / 660 registers**, including four
SYNC BUFGCEs and exactly one falling-edge mask register. Estimated setup slack
at 140 MHz is **+0.545 ns**; unplaced hold slack remains **-0.062 ns**. These
reports do not establish implementation timing closure or an FPGA image.

The matching native/EDA audit rejects ten scope/source/model/contract/DCP/log/
waveform/cut substitutions, including coherent source rehashing. All 162
original execution files remain byte-identical. The inherited physical-cut
component and production bank/top audits also pass with fresh current inputs.
