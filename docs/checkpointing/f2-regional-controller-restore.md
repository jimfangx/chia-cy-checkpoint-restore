# Parked restore of the generated regional cut controller

`NativeCheckpointRegionClockCut.generate(..., restoreController = true)`
connects the existing physical cut primitive's restore interface and restores
the adapter's original accepted-request bit. Default compiler callers retain
their existing ports, tied-off restore and incomplete-image guard.

The complete vector contains the physical controller in the low bits, followed
by accepted-request pending. Within the physical controller the low-to-high
fields are falling-edge mask, sampled, release-pending, captured logical CE,
64-bit cut cycle and three sticky errors. Restore adds no sequential storage.

This interface is for a permanently parked destination. Assert hold before
its first raw edge; load the mask at a raw falling edge and all other fields at
a raw rising edge, retaining the same whole vector across both edges. Retain
hold and independently compare every original bit after both loads. Reset
dominates either load. An unheld load is rejected and still asserts the physical
mask; ordinary requests and responses receive no permission during hold or load.
Inactive pending, cycle, CE and error values participate in restore.

There is no resume contract. This restores neither routers/endpoints nor DUT,
functional memory, host owners, vendor gate internals or target-time authority.
It does not admit a complete checkpoint image or establish CPU migration.
Production snapshot/MMIO integration and complete ownership remain pending.

Iteration 12214 commands and original attempts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration12214/`. The qualification entry
point is `python3 -m tools.checkpoint_formats.tests.verify_regional_controller_restore`:
use `--mode vivado --compiler <receipt>` on this manager, then
`--mode vcs --native <receipt>` on EDA SP2 after native writers finish. It uses
the actual generated attachment with two original executions. A source process
records controller phases, including an accepted/stalled request and sticky
missing-owner error; a separate destination loads only this controller owner.
The destination's functional clocks remain parked from before its first edge.
Full VCDs retain each original controller field and the adapter's pending bit.
Consult progress.md and the iteration command index for observed test results;
the procedure itself is not execution evidence.

Qualification passes all 449 Scala / 430 Python / 81 manager tests, fifteen
serialized localhost native syntheses and the complete retained EDA SP2
sanitizer/FASED/publication/bank/host/FCFS/cut/router/caller/staging scope. The new
native case retains 74 physical-controller registers and the original pending
register on the raw clock, using 2,158 LUTs / 996 total fixture registers. These
are OOC component resources, with no full-image timing claim.

Four fresh VCS processes pass: source and healthy destination, then two expected
corruption rejections. Eleven actual source records cover inactive and active cut,
accepted/stalled request, release, error and controller-reset phases at logical
labels 17–20. Complete destination readback retains 119 held raw edges, rejects
eleven unheld loads and observes zero functional/transport acknowledgements.
Both corrupt mask/pending donors stop at first readback at label 17. All 75
waveform checker mutations and six coherently rehashed attachment defects reject.
Exact testbench/exit-helper bytes, full VCDs, native DCP/reports and source snapshots
are retained beneath the iteration directory.

The closing independent audit passes 23,022 bindings / 32 receipts. Exact
Rocket compiler attachment auditing retains 2,701 definitions / 37 routes and
81 observation / 152 staging bits; image emission still rejects 1,245 uncovered
functional entries and unbound cut MMIO. No image, AFI, FPGA checkpoint, CPU
migration, live CPU comparison or hardware rolling recovery is established.
