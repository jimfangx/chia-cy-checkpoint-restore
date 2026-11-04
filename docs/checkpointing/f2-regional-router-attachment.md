# Held restore in generated regional routing

`NativeCheckpointRegionGraft.generate(..., observeRouterState = true,
restoreRouterState = true)` connects the existing shared-router and physical-router
restore interfaces in one generated adapter. The ordinary compiler path keeps
restore disabled. This opt-in currently requires native-only endpoints without
native-reader staging. It grants no additional descriptor or image admission.

The packed input has exactly the observation ABI: shared
`{owner, invalid, pending}` at the low bits, then each physical router's
`{selected_ce, pending}` in region order. Every original register participates,
including inactive values. No new sequential state is introduced.

Assert hold while the original physical mask and read permission are valid.
The adapter validates the complete shared-owner index before asserting one
common raw-positive-edge load for all routers. An invalid owner, missing physical
cut/read permission or load without hold cannot partially update a physical
router. Hold and even a rejected unheld load suppress all router handshakes.
Reset dominates loading. Deassert load, retain hold and compare the complete
observation against the independent donor before releasing hold. Error is
combinational; the caller must retain rejected controls through the detecting
edge and provide global fault handling.

The binding records exact original instances, field order, widths, generated
resources and source/descriptor identities, plus separate router-only load and
readback contracts. It explicitly disclaims endpoint and global-cut restore.
Production common-cut/controller/staging/reader/endpoint and MMIO integration,
functional-memory and host/bridge ownership, pre-FAME semantic ownership,
complete localhost image implementation/AFI, active F2 capture and paired CPU
migration/live RTL/rolling recovery remain pending.

Qualification commands and all attempts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration9813/`. The dedicated entry point
is `python3 -m tools.checkpoint_formats.tests.verify_regional_router_restore`
with `--mode vivado --compiler <receipt>` on this manager, or
`--mode vcs --native <receipt>` on EDA SP2. Native synthesis must finish before
EDA exchange. The new fixture runs source and destination in separate processes;
it exercises the real generated original host and readout. Destination endpoints
are deliberately prepared through matching public requests: only router state
is migrated by this test, so it cannot establish endpoint or CPU acceptance.
Independent waveform auditing checks individual raw registers, accepted
transactions and every held router/endpoint handshake. Fresh qualification
passes eleven EDA processes with eighteen actual donor records at cut 38, all 144 legal encodings and 164 successful loads. Seven
corrupted router bits stop before any acknowledged transport edge; twelve
waveform-checker mutations and 22 coherent structural defects reject. All
446 Scala / 430 Python / 81 manager tests and the full retained native/EDA
scope pass. Consult progress.md and the iteration command index for receipts.

The one-region native design has only one legal shared owner index. Its first
synthesis audit correctly stopped when Vivado removed that register. Independent
inspection of the retained DCP proved observation bit 2 has exactly one GND
driver. Qualification now requires that exact constant proof and all four
remaining raw-clock registers; the two-region case requires all seven original
registers. This accounts for the complete logical vector without inventing
physical storage. The original failed receipt and netlist remain intact.

The fresh destination first exposed a same-delta response check after hold
release. A second attempt passed runtime checks but the waveform audit rejected
unsettled cleanup at final reset/control release. The fixture now waits one
nanosecond at both points, before comparison or completion and before any next
edge. Both source-bound native fixtures were requalified after each change;
all final independent waveform checks pass, including the final row. Failed
receipts, full waves and exact original fixture sources remain under `runs/`.
