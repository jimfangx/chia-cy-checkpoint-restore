# Native banks and physical CE routing through the FireSim widget

Iteration 228 adds `NativeCheckpointStateAccess.emit`. The explicit native probe
emits a separate state-access wrapper, the exact router resource and a binding.
The factory reconstructs both the functional banks and physical clock-mask
network from the same original circuit before accepting them. It retains all
original top ports, connects the generated network's request/response interface
to the synthesized router, instantiates the exact generated CE endpoint and
emits its complete functional descriptor table. The native response registers,
router and CE endpoint use the common ungated source and the widget's controller
reset. The physical mask and captured unmasked CE samples come from the actual
widget controller. Every binding keeps capture/production/restore admission
false and retains external CE dependencies and reset requirements.

`NativeCheckpointWidgetFixture` connects this generated wrapper to the actual
`CheckpointCaptureWidget`, including its manifest-bound internal descriptor ROM,
AXI control adapter and 512-bit DMA stream. Functional state is the original
native gated counters, wide RAM and old-read pipeline. Its VCS bench computes
counters and RAM independently through public ports, requests captures through
AXI, and compares every framed transfer word, selector and cut label. It also
exercises stalled DMA, unpublished abort/recovery, common reset and resumed
execution. Separate owner/CE/cycle faults must deny read/publication and remain
stopped after abort; semantic corruption and a separately compiled incorrect CE
connection must stop at their first payload mismatch. Hierarchical execution waveforms
are retained. VCS runs exclusively on EDA SP2.

Local Vivado 2025.2 synthesis checks three native/root gates, one falling-edge
mask and the electrical raw-clock connectivity of all bank/router/CE response
registers. The connected component uses 2,577 LUTs / 1,155 registers. OOC 140 MHz
setup/hold estimates are +0.597/−0.074 ns; hold and full-image timing closure remain
pending. The first diagnostic incorrectly selected combinational LUTs whose
names shared the response-register prefix. Its actual native log is retained;
the corrected audit selects flip-flops explicitly.

The independent structural audit checks original port directions/widths, every
network/router/CE connection, all ROM entries, original clock/bank reconstruction
and immutable bindings. Coherently rehashed reset, clock, freeze, CE, response,
ROM and port-shape changes reject. Independent execution auditing requires
native DCP/tool/part identity, matching sources/inputs, every word in exact
ordinal/address order, independent arithmetic and CRC, successful healthy and
expected negative process exits, cut labels and all debug waveforms. It tests
missing evidence and coherently altered frames/bindings separately.

Fresh EDA SP2 execution passes **6,482 checks / five cuts / 170 words / 210 DMA
stalls**, with initial-history cuts **63/84/184/324**, followed by reset recovery
at cut **21** and continuation through cycle **96**. Semantic corruption stops
at cut 63/check **273**; the separately compiled wrong CE sample stops at cut
63/check **1,036**. Owner/CE/cycle faults remain stopped with zero target edges
acknowledged. All six execution waveforms remain. Independent native/EDA
matching covers **89 inputs / 32 sources** and rejects **nine** evidence
corruptions, including corrected-CRC semantic and duplicate-word streams.
Eight coherently rehashed structural connection/port/table corruptions reject.

This connects readout components. The ordinary production bank path still
requires complete physical CE/common-cut owners. `F1Shim.reset`, all external
CE inputs and functional DRAM writers, FASED/bridge/host ownership, physical CE
restore and complete independent pre-FAME semantic mappings remain unbound.
Production FPGATop stream/MMIO registration and generated-network connection
must use one raw-clock/reset contract and rebase/validate original XDC paths
against the concrete wrapper instance. The companion does not claim those
production constraints are attached. Full localhost image implementation,
P&R/timing closure, AFI/AGFI/driver binding, deployment and actual all-hart active
FPGA capture remain pending, along with paired zero-edge restoration, finite
replay, sustained live RTL beyond trace and rolling hardware failure recovery.
No synthesized component or companion establishes those acceptance criteria.

Exact commands, original diagnostics and execution receipts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration228/`. Consult its final
`summary.json` and `verification-commands.json` for completed validation counts.

Final verification passes 236 Scala, 309 checkpoint Python and 40 loop tests,
all 19 localhost synthesis scopes and all 38 EDA scopes, including retained
ASan/UBSan/host/FCFS checks. Complete exact-Rocket structural reconstruction
matches independently on both hosts over 2,290 modules / 14,313 sequential/effect
definitions and 12,096 functional + three CE descriptors / 619,016 words. The
ordinary production trial's actual compiler log retains its physical CE-owner
rejection. Final source/artifact/resource audits pass after repairing a stale
log filename; `recovery-notes.json` preserves that initial failure and both
native-test diagnostics. Plans and initialized configs retain their entry hashes.
No new AFI/runtime was requested; the final inventory records a separately
observed pending account Saturn AFI without attributing capture support to it.
