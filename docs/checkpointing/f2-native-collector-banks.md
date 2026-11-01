# Native banks connected to the F2 collector

Iteration 299 adds `F2ClockResetCutWiring.generateNative`. It independently
reconstructs the supplied native banks/clock mask through the existing descriptor
contract, audits the original reset fanout, and connects the existing synthesized
F2 collector inside the same generated execution. The endpoint's access clock
is tied to the raw common source. Its freeze and reset are internal connections
to the collector mask and independent controller initialization. Original
functional reset consumers use the held reset. External callers cannot drive
these connections independently.

The collector's read permission gates both transaction handshakes. Dropping the
external freeze request prevents another request immediately, while an already
accepted response keeps the collector cut held through arbitrary backpressure.
After response acknowledgement the existing registered low-phase release runs.
An owner/reset/writer fault removes both handshakes immediately, retains the
unacknowledged beat and keeps functional clocks stopped; source/presence return
does not repair the failed cut. Separate controller reset is required. Direct
combinational data/match taps are internal, so they cannot bypass the endpoint.

Cycle selection must name a driven UInt<64> output of the original reference.
A newly generated bank output cannot feed the cut label. This proves original
connectivity only; it supplies no global target-time authority.

The binding records original/reference/reset/clock-plan/bank hashes, functional
entry count and exact clock/reset/freeze/read/release/cancellation contracts.
Stale bindings, changed bank entries/circuits, missing reset ownership and added
readout outputs selected as cycle sources reject before composition.

The compiler fixture has three original registers (80 functional bits) and two
original BUFGCEs. The bank interface reads every register plus invalid selector
and address cases at four cuts; it changes selectors under backpressure and
withdraws freeze with a response outstanding. All original functional outputs
and cycle labels compare with a separately emitted original reference. Owner,
writer, reset and DDR fault runs cancel during an outstanding read, including
release-boundary faults. Raw full-visibility wave auditing reconstructs collector
registers and every accepted/acknowledged bank beat independently from the
original functional state. Retain all immutable attempts beneath
`automations/checkpoint_loop/runs/aws-f2/iteration299/`.

Fresh native Vivado 2025.2 component P&R passes the unchanged 140 MHz request:
165 LUTs, 231 CLB registers, three BUFGCEs and +0.665/+0.046 ns setup/hold slack.
The 234 sequential-cell count includes those three clock gates. Parent/shell/I/O
timing remains unmodeled. Fresh EDA SP2 VCS passes 6,304 comparisons at cuts
0/17/128/256, twenty ordinary reads, eighty response-stall cycles and sixteen
withdrawal-stall cycles, plus ten cancellation cases and first-divergent reset
corruption. Independent raw-wave auditing confirms 24 healthy accepted and
acknowledged beats, and seven accepted/six acknowledged beats for each
cancellation case. Exact drain/cancel edge counts pass; all 64 response-data and
81 packed collector-state bit mutations reject. Keep the initial invalid
sample-count threshold audit and the corrected exact-edge audit separately.
All 376 Scala tests across 59 suites pass (37m02s), alongside sixteen
preparation checks, six focused collector checks, 21 FAME/emitter checks,
409 Python and 61 manager tests. Full-suite native/collector/FAME generated
bytes match the synthesized and simulated fixtures. All retained native/EDA
bank, observer, collector and 124 final-emitter corruption checks pass. Fresh
observed and ordinary exact Rocket compiler runs both retain the real FASED
physical CE owner/common-low-phase cut refusal. Closure is
`runs/aws-f2/iteration299/final-audit-xizzcue_/summary.json`. Final scoped AWS,
native HDK/Vivado and manager-localhost checks pass; no loop F2 instance, pending
AFI or local Java/Vivado job remains. Both plans and initialized manager inputs
retain entry hashes. Existing controller checkpoints were published FireSim
then Chipyard with matching remote tips; retain the local tracking-ref warning.
No staging or local commits were performed.

This is a combined compiler/hardware component. Production selective attachment,
ungated CheckpointBridge MMIO/DMA hookup, complete physical CE/memory/FASED/host/
pre-FAME ownership, authoritative cycle/boundary binding and atomic collector
state capture remain mandatory. Complete FPGA capture, deployable image and
metasim restore flags remain false. In particular, the existing
`NativeCheckpointRegionWidgetGraft.liveTransportConflicts` guard still refuses
freezing eight widget-local MMIO/DMA owners. The new component does not bypass
that guard or install its own collector beside the widget's existing controller.
Production must compose one controller with selective functional ownership,
atomic staging of borrowed-reader/control state and the real ungated transport.
Do not promote a FAME completed-step counter to global cycle authority without
complete model/domain, channel and environment convergence.

No full checkpoint image, AFI/AGFI, actual FPGA checkpoint, CPU restore/replay/live comparison or rolling recovery is
established by this component. No hardware matrix column advances.

Reuse iteration194's retained ExternallyProvisioned localhost invocation and the
four initialized manager inputs. Plans remain read-only. Managed worker startup
failed before execution; all work is central and no worker started. Follow
[github-publication.md](github-publication.md); only the loop controller stages
and creates local commits.
