# Native network attachment through FPGATop

Iteration 230 adds `NativeCheckpointCaptureBinding`, an opt-in elaboration
attachment for a bounded generated native network. It reconstructs functional
banks, physical clock masking, the CE endpoint and router from the same original
circuit as the immutable descriptor ROM. Its emitted blackbox contains those
validated implementations. FPGATop registers the actual checkpoint widget after
existing bridges, retaining their stream indices, and connects it through the
ordinary AXI control interconnect and CPU-managed AXI DMA engine.

The helper wires the network's common source directly to FPGATop's raw clock.
The router and both bank endpoints share the widget's controller reset, mask,
captured CE vector, permission and backpressured request/response ports. The
callback receives every original port except that raw clock, and must connect
functional reset, CE inputs and memory writers, the authoritative target-cycle
signal and every explicit freeze owner. Missing reset or owner connections fail
FIRRTL initialization checking. There are no default owner acknowledgements.

This attachment cannot embed an enclosing F1Shim/FPGATop simulator: it rejects
that request before generating banks, because doing so would duplicate the
simulator rather than instrument its existing execution. The complete Rocket
F1Shim network still needs an in-place production transformation that preserves
raw transport clocks and includes all remaining owners. This helper does not
activate capture in the stock recipe or grant complete capture/restore admission.

The native FPGATop fixture has two original gated counters, a wide old-read RAM
and its synchronous pipeline, and an existing diagnostic stream. Its checkpoint
stream uses index 1. The independent attachment auditor reconstructs native
storage and constraints, checks exact inline emission bytes, follows FPGATop wire
aliases for functional ports/raw clock/reset/all transaction connections, and
checks generated host metadata against actual CPU stream-engine allocation.
Five changed top connections must reject. Local Vivado checks original native
gates, the falling-edge mask, every endpoint clock, and all transport, control
interconnect and DMA-engine register clocks. It applies all six original cell/pin
constraint queries under `nativeCapture/network` and rejects empty queries.

The fresh EDA VCS test uses public FPGATop MMIO and AXI DMA ports for every
capture. Independent arithmetic and old-read RAM models check functional
execution and all 34 functional/physical transfer words per cut. The test fills
the real shared DMA queue, stalls AXI responses, reads the older bridge's stream
while frozen, publishes/releases cuts and continues execution. A common reset
discards a queued unpublished capture before a later capture resumes. Separate
missing-owner and changed-cycle cases must remain stopped after abort; semantic
and independently compiled CE-payload corruptions must fail at their first
observed data mismatch. Healthy and negative processes retain hierarchical VCDs.

Current-source native synthesis uses **4,582 LUTs / 1,726 registers**, including
**1,028** independently checked raw-clock control/transport/DMA registers. OOC
140 MHz setup/hold estimates are **+0.591/−0.095 ns**; full-image timing closure
remains pending. All **238 Scala tests** pass. Fresh EDA SP2 execution passes
**15,655 checks / five cuts / 170 words / 1,110 DMA stalls**, at cuts
**16/84/184/324**, then reset recovery at **21** and continuation through cycle
**200**. Semantic/compiled CE corruptions stop at cut **16**, on transfer frames
**1/33**, while frozen. Independent native/EDA matching covers **86 inputs /
41 sources**. Five changed top connections reject; all five execution VCDs remain.
All **20 localhost synthesis / 39 EDA scopes**, **309 checkpoint Python / 40 loop
tests**, and retained ASan/UBSan/host/FCFS regressions pass.

Execution evidence and exact commands belong under
`automations/checkpoint_loop/runs/aws-f2/iteration230/`; consult `summary.json`
and `verification-commands.json` for the final observed results and raw logs.

Full Rocket reset/external CE/DRAM writer, FASED/bridge/software ownership and
independent pre-FAME state mapping remain incomplete. Physical CE restore,
production XDC attachment, localhost full-image P&R/timing closure/AFI creation,
driver binding, active four-hart FPGA cuts and all FPGA-to-VCS migration/live
comparison/rolling recovery remain pending. Component synthesis or this fixture's
VCS streams establish none of those hardware acceptance requirements.
