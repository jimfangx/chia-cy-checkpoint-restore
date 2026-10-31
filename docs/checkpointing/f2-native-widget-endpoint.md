# Native transport and real widget endpoint

The native transport now has an exact Chisel BlackBox interface and a reusable
`CheckpointNativeWidgetEndpoint`. It connects the existing native RTL to the
actual `CheckpointWidgetEndpoint.build` NASTI, stream-accounting and shadow
logic. Production `CheckpointCaptureWidget` selection, generated driver headers,
reservation/graft guards and image admission are unchanged.

The BlackBox binds the existing seven SV resources and has no nonexistent
restore or legacy physical-sideband ports. Its external-clock mode requires the
caller to provide the real clock network and connect the clock mask and CE
owners. Native root/gate compatibility outputs are constant zero in that mode;
they are not simulator clocks. The generated observation metadata records this
contract, geometry, selectors, resource hashes and unsupported ownership.

The raw native composite has `BITS + GATES + 627` bits. Its coordinator starts
at `BITS + GATES + 150`, so interpreting its low 411 bits as the coordinator
would inspect the wrong state. A reversible endpoint view puts the coordinator
first, then the original native owner, 66 payload-response bits and the separate
67-bit native-control-bank owner. Every bit is preserved once. Existing ordinary
and physical shadow layouts remain unchanged. Observability supplies neither
atomic self-capture nor restore ownership.

The focused geometry is BITS=130 / GATES=3 / OWNERS=2 / ENTRIES=1, with native
control capture enabled and selectors 251/252. Its raw/view/shadow widths are
760/827/1585. Scala checks exact ports, parameters, resources, invalid geometry,
all 827 mapping planes through the emitted expression graph, opposite cut
certificates and unchanged default headers. The EDA bench uses actual generated
RTL and native resources, a vendor external clock model, real NASTI transactions,
DMA stalls and full debug waves. It checks all 25 shadow words,
four progressing cuts, frame CRC/owners/payload, owner-loss/abort/reset recovery
and a compiled coordinator-selection fault before acknowledgement.

Native Vivado 2025.2 OOC synthesis on this server passes 3,567 LUTs / 2,666
registers and independently identifies all 67 bank register drivers. Unchanged
140 MHz estimates are -1.190/+0.073 ns setup/hold. The worst reported path
runs from the falling-edge physical `freeze_low` register to the shadow label
clock enable: 17 logic levels / 4.457 ns against a 3.572 ns half-cycle budget.
Timing closure and complete shell/I/O implementation remain pending. Receipts and all failed/interrupted
attempts are retained under `runs/aws-f2/iteration286/`. Fresh EDA SP2 execution passes all four cuts (35/68/112/167), all 25 shadow
words, 827 independent layout planes, complete original-register/frame/CRC
audits and owner-loss/abort/reset recovery. The exact compiled coordinator
selection fault stops at component cut 35 with every acknowledgement counter
zero. Its retained `raw_phase` field denotes the native sequencer phase; the
independent auditor establishes the low clock and absence of later timestamps
from the actual VCD. The complete retained regression sweep and independent
current-source aggregate pass: 335 Scala tests / 53 suites plus twelve preparation
tests, 377 Python tests, 61 manager tests, retained ASan/UBSan/FCFS, sixteen fresh
SP2 component scopes, six bank geometries and two compiled bank faults, full queue
execution/wave audit with eight corrupt streams and six compiled faults, fresh
staging/graft execution and the remaining component/waveform audits. Unchanged
outer native receipts retain their original dates and exact authenticated bytes.
The final aggregate is
`runs/aws-f2/iteration286/final-current-evidence-oodwzs0_/summary.json`;
`verification-commands.json` in that iteration records raw backend commands.

Next production work must bind this interface to the real widget's descriptor
manifest/header and complete native reader-idle and hold wiring. Shell functional
write sites need `functional_hold`, while physical gates need the low-phase
mask. Mixed physical regions, the complete common cut/reset, physical CE owners,
transport/stream/host self-state, functional memory/FASED/FAME and independent
pre-FAME mapping still need ownership and restore support. Full image/P&R/AFI,
physical four-hart cuts, hardware-produced checkpoint pairs, finite/live CPU
migration and rolling hardware recovery remain pending. Component results cannot
establish those hardware columns.
