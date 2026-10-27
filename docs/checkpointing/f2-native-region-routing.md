# Native checkpoint region routing

`CheckpointRegionStateRouter.sv` routes one outstanding read among independently
banked native regions on a shared raw clock. Functional endpoints receive their
original bank, slot and address. Bank 255 retains physical CE semantics, with
disjoint global slot ranges translated to endpoint-local CE slots. The router
pins the response owner at request acceptance, holds that owner through delayed
responses and backpressure, ignores unsolicited responses and returns an explicit
error for an unallocated selector. Endpoint bounds/errors propagate unchanged.
Reset must reach the router and all endpoints together.

`CheckpointRegionRouting.allocate` allocates the static ranges and emits the
router source, parameter list and source-bound routing contract. It rejects
overlapping StateIDs, duplicate selectors, sparse bank ranges, malformed physical
words and ABI overflow. `CheckpointCaptureDescriptors.fromNativeRegions` composes
only independently reconstructed in-place identities from the same original
host, global inventory, clock plan and dependency graph. Selected executions
cannot overlap. Global descriptor ordinals and physical sample bits are distinct
from retained local ordinals, bank/slot selectors and CE bits. Uncovered owners
remain explicit. The resulting descriptor ROM and host initializer use exactly
the selectors consumed by the router.

The directed structural Rocket check selects `F1Shim.top.sim` and
`F1Shim.top.FASEDMemoryTimingModel_0` from the retained exact-recipe source.
Together they describe 10,910 entries and all three physical CE identities;
1,189 functional entries / 198,818 words remain outside those regions. This is
selector composition over actual generated definitions, not installation of
their networks into a common production cut. The independent auditor reconciles
both region manifests against the original global inventories and clock plan,
including every local/global ordinal, selector and CE sample bit.

Production integration still must connect both existing executions, route their
bank endpoints and concatenate their logical/captured CE vectors into one atomic
controller, preserve reset and all external writers, and provide the remaining
functional-memory, timing, bridge, host and pre-FAME owners. In particular,
describing the FASED CE owner does not freeze it. Ordinary bank capture and image
admission retain their unconditional missing-physical-owner rejection.
The next compiler change needs a checked multi-region in-place graft: the current
single-region graft exposes a fixed sideband namespace and cannot be applied
twice to shared ancestors. Extend that integration without duplicating the
simulator, freezing the raw transport, or treating region-local CE order as the
enclosing clock plan's order.

Component test commands and immutable receipts live under
`automations/checkpoint_loop/runs/aws-f2/iteration253/`. Complete localhost
image/P&R/AFI, active four-hart hardware capture, paired complete zero-edge CPU
migration, finite replay, sustained live RTL and rolling hardware recovery remain
pending. No FPGA-origin CPU acceptance follows from this component.

Final iteration-253 checks pass 276 Scala tests across 41 suites plus twelve
preparation tests, 330 Python tests, 40 loop tests and all ten native/EDA scopes.
The router's 6,155 public-port checks cover 201 requests, 199 responses, four
invalid selectors, 2,380 stalls and two reset cancellations. One- and three-region
boundary configurations and all five static range rejections pass. The compiled
wrong-owner defect stops before either response acknowledgement, independently
confirmed in the debug wave. Eight rehashed descriptor/coverage mutations reject.
The native two-region fixture uses 99 LUTs and three registers; I/O timing is
unconstrained. These remain component results, with all CPU hardware acceptance
pending. Failed/superseded epochs and their repairs are pinned in the recovery
notes; no historical receipt was rewritten as a successful run.
