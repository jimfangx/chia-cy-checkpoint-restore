# In-place state access through the registered widget

Iteration 237 adds `NativeCheckpointInPlaceCaptureBinding`. It reconstructs the
in-place network and global descriptor identities before attaching functional
banks and physical CE readout to the registered FPGATop checkpoint widget.
The existing standalone binding uses the same endpoint attachment code.

The widget remains on the raw FPGATop clock, with its actual MMIO interconnect
and CPU-managed DMA stream. Existing stream allocation is preserved; capture
appends its stream. The controller reset stays separate from functional reset.
Original ancestor controls, the bank endpoint, router and CE endpoint keep the
raw clock while the selected functional execution is stopped. The callback
must connect original functional inputs, target-cycle authority and every
freeze owner; there are no default owner acknowledgements. Missing reset or
owner wiring fails elaboration.

The in-place endpoint is regenerated from the original source/context, rather
than accepting an RTL string and rehashed descriptor manifest. Changed source,
dependency or identity contracts reject. Original correlated XDC is emitted
for the actual attachment instance; independent verification checks the emitted
bytes and placement binding against the original source constraints. The fixture
explicitly emits and applies these constraints; production compiler attachment
remains pending. The host
header binds the global descriptor digest, preserving local bank selectors and
CE bit order.

This attachment supports an instrumented component host within FPGATop. It
explicitly rejects embedding an enclosing `F1Shim`, `FPGATop`, `SimWrapper`,
`TargetBox` or stream engine, which would create a second simulator. Applying
the connection to the existing production Rocket FPGATop still requires a
post-lowering graft into that top and a checked immutable descriptor ROM; this
component attachment does not establish that production mapping.

The bounded execution check uses active wide RAM writes and original read
pipelines, reads functional and physical words through actual AXI MMIO/CPU DMA,
and checks both ancestor counters independently while capture is backpressured.
It covers repeated cuts, shared-stream allocation, aborted unpublished frames,
reset recovery, missing owners, target-cycle drift, payload corruption and a
separately compiled CE connection fault. Native synthesis runs on this server;
VCS compilation and execution run only on EDA SP2, with debug waveforms.
Fresh receipts and exact commands belong under
`automations/checkpoint_loop/runs/aws-f2/iteration237/`.

The refreshed component passes **19,235 SP2 checks / five cuts / 170 words /
1,110 DMA stalls**, recovery through cycle **200**, four execution negatives
and ten independently rejected attachment mutations. Five debug waveforms
remain. Independent settled-wave reconstruction verifies both ancestor counters
advance across **3,034** frozen raw-clock edges, with no selected target advance.
Native synthesis retains **4,572 LUTs / 1,850 registers / three BUFGCEs**, with
**199** raw ancestor/router/endpoint and **1,024** raw control/stream register
clocks proven structurally. Native/EDA matching binds **156 inputs / 68 sources**.
OOC setup/hold estimates are **+0.590/−0.074 ns**; full-image closure is pending.
All **252 Scala / 23 native synthesis / 42 EDA scopes**, **313 checkpoint Python /
40 loop tests** and retained **ASan/UBSan/host/FCFS** regressions pass.

Production coverage remains 10,149 selected functional owners plus two CE
owners, leaving 1,947 functional owners and the FASED CE owner uncovered.
Reset/external writers, functional DRAM, FASED, bridges, host state, physical CE
restore and independent pre-FAME semantics still need complete bindings.
Full localhost image implementation/timing/AFI, active all-hart hardware cuts,
complete independent zero-edge restores, finite replay, sustained live RTL and
rolling recovery remain pending. No FPGA-produced checkpoint or CPU migration
acceptance is claimed.
