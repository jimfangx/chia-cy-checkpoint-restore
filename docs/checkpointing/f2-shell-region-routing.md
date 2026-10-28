# Local ancestor banks on regional readout

Iteration 261 extends `NativeCheckpointRegions.generate` with explicit
`shellTargets`: local-only owners may sit above
selected disjoint child regions. Each local bank is reconstructed against the
same original host and global clock/dependency inventory. Native subtree
selectors remain local; the shared router allocates separate functional banks
and gives the local endpoints zero physical CE slots. The graft preserves
original child executions and carries their sidebands alongside each ancestor's
own banks. Local storage must resolve through transparent Clock aliases to the
same original raw input; independent clocks and casts reject. Every descriptor,
annotation contract, mapping and equation is rebuilt during validation.

The compiler diagnostic accepts `--simulator-native-shell-compiler-probe`
alongside its explicit regional request. Root paths are allowed for local-only
selection. Shell references, bank mappings, instrumented circuits and bindings
are retained before any connection attempt. No coverage or restore flag becomes
true because a local owner has a descriptor.

The exact Rocket request selects `F1Shim.top.sim` and
`F1Shim.top.FASEDMemoryTimingModel_0`, plus local-only `F1Shim.top` and `F1Shim`.
Its original local inventory is 181 FPGATop registers plus two F1Shim counters.
Those include eight inlined CheckpointCaptureWidget registers needed by the
live checkpoint stream. Holding those registers while asking the same widget
to produce/drain frames is invalid. `liveTransportConflicts` follows the exact
registered widget's pre-inline identity through the actual native storage map;
it does not guess flattened names. Connection rejects any such overlap until
an explicit atomic transport-owner protocol exists. The probe records
`transport-freeze-conflicts.json` and preserves the actual exception. Image
emission remains guarded even when no overlap exists.

The mixed component has two original native regions and local owners on both
ancestors. It exercises every functional and physical word, shared backpressure,
reset cancellation, missing-owner and CE-drift rejection. A separately compiled
local payload defect must stop on its first word before acknowledging it.
Independent audit reconstructs local register hold equations, original ownership,
selector allocation, raw access clock, common mask and response wiring. Eight
rehashed corruption cases cover omitted owners, selector changes, local hold
removal, mask/clock/payload wiring, false admission and changed ordering.

Verification receipts, commands and original failed/cancelled exploratory logs
are retained under `automations/checkpoint_loop/runs/aws-f2/iteration261/`.
Final-source verification passes 316 Scala tests / 47 suites plus twelve
preparation tests, 336 checkpoint Python / 45 manager tests, sixteen native OOC
and sixteen fresh EDA SP2 scopes, retaining ASan/UBSan, FCFS and atomic-cut checks.
All six waveform audits pass. The mixed component passes 8,452 checks over four
component cuts, 288 reads and 864 stalled cycles. Native OOC uses 2,165 LUTs /
1,128 registers; the clock audit retains four original gates plus two generated
root-mask gates and checks 405 raw-clock state registers. Independent waves
check 1,672 healthy samples / 1,447 frozen samples. The compiled local defect
stops at fixture cycle 36 / word 64 with freeze held and acknowledgment low.
These component labels do not describe CPU or FPGA checkpoint cuts. Complete
source/receipt/protected-input/resource auditing passes; the final inventory has
no active tagged runtime, pending AFI or native Java/Vivado job.

This remains a readout integration prerequisite. Functional DRAM, remaining raw
and shared subtrees, bridge/host state, transport-local snapshot ownership,
common cut/reset/external writers, additional access/control state and pre-FAME
mapping remain incomplete. Full localhost image/P&R/AFI, physical all-hart cuts,
FPGA-origin paired zero-edge restores, finite/live RTL continuation beyond the
trace and rolling failure recovery remain required. No complete image or FPGA
checkpoint acceptance follows from these component artifacts.
