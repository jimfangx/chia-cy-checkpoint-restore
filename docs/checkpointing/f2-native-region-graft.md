# Native checkpoint region graft

`NativeCheckpointRegions.generate` instruments disjoint concrete executions of
one original lowered host. Every region is reconstructed against that original
host. Shared ancestors retain their original functional bodies, clocks and
instance paths, carrying separate `checkpoint_inplace_regionN_` sidebands.
Generated storage definitions, their instances and generated annotation targets
receive region-specific names. Original host annotations are translated once
against the complete combined hierarchy. Compiler context remains separate.
Overlapping/stale selections, reused execution definitions, identifier collisions
and different raw clock sources reject. Validation reconstructs the source,
circuit, annotations, context, identities and descriptors rather than accepting
caller-rehashed metadata.

`NativeCheckpointRegionGraft.generate` internalizes those sidebands at the
original root through one raw-clock readout adapter. Each native region retains
its own functional bank/physical CE endpoint; `CheckpointRegionStateRouter`
allocates disjoint functional banks and physical slots and pins response
ownership until acknowledgement. The global descriptor ROM uses the same
selectors. One mask, reset and read permission reaches all region endpoints;
logical/captured CE vectors are sliced in region order. That order deliberately
need not match the enclosing inventory's physical-gate indices.

This is a bounded readout graft with a shared cut interface. It supplies no
production owner acknowledgement and is not installed in the production widget
pipeline. Reset, external writers, functional DRAM, enclosing timing/control,
bridge/host and pre-FAME owners still need a complete common cut. Newly added
readout/control state also needs explicit capture or exclusion/restore ownership.
Image admission
and ordinary physical-owner guards remain active. Complete FPGA capture,
metasim restore and deployable-image flags remain false.

The directed hardware fixture installs two existing banked executions beneath
the same two raw-clock ancestors. Complementary enables and different write data
make crossed regions observable. One common low-phase controller drives both
networks; an independent arithmetic/memory oracle checks both executions and
raw ancestor counters. Native synthesis and EDA VCS verification consume identical
source/generated/vendor-model pins. VCS is restricted to EDA. Debug waves and
negative tests are component evidence, not FPGA capture.

Final iteration-254 checks pass 280 Scala tests across 42 suites plus twelve
preparation tests, 330 Python tests, 40 loop tests and all eleven native/EDA
scopes. The new fixture passes 8,242 checks / four cuts / 280 words / 840 stalls,
reset cancellation, owner failures and the compiled wrong-CE defect before its
response acknowledgement. Independent waves retain 1,407 frozen samples. Native
OOC resources are 2,047 LUTs / 995 registers / six BUFGCEs, including 272 raw-clock
control/readout registers. Setup/hold estimates +2.027/−0.074 ns have unconstrained
I/O and establish no full-image timing closure. The installed exact-Rocket audit
retains all 2,292 original executions and checks 10,907 functional entries / three
CE identities; 1,189 functional entries / 198,818 words remain uncovered.

Verification and failed/superseded attempts are retained under
`automations/checkpoint_loop/runs/aws-f2/iteration254/`. Consult that invocation's
final receipts and the current progress entry for completed checks. Actual
checkpoint-enabled localhost image/P&R/AFI, all four active Rocket harts, hardware
cuts, independent complete zero-edge CPU restore, finite replay, sustained live
RTL beyond the trace and rolling hardware recovery remain pending.

## Optional common native-vector staging

`NativeCheckpointRegionGraft.generate(source, stageNativeState = true)` now
installs `CheckpointNativeStateSnapshot` on the shared raw clock. This mode
requires shell-only endpoints with an actual native observation vector; mixed
physical-clock regions still reject. The default live-readout interface and
original descriptor identities are unchanged.

One edge stages the entire vector and its target-cut label before any bank
request. Idle requires the router to be ready, every endpoint to be ready, and
no endpoint response. Both request and response handshakes, including their
internal endpoint acknowledgements, require the staging owner's borrow permission.
Premature requests, owner/freeze loss, cycle drift and busy release/capture revoke
permission before acknowledgement and latch failure. Failed pending transactions
require the common reset; release cannot fabricate completion. The saved vector
has indexed 64-bit readback and an explicit complete payload/occupied/cut/error
control vector. This is capture-only ownership, without a restore interface.

The binding records the snapshot geometry, layout, raw-edge sampling and idle
contract, source/resource hashes and remaining unsupported owners. This opt-in
adapter does not bind the production widget, global reset/cut, functional DRAM,
FASED, host transport or pre-FAME semantic state. The ordinary widget's existing
rejection stays enabled. It does not admit a full FPGA image or a CPU checkpoint.
New diagnostic and verification evidence belongs under
`automations/checkpoint_loop/runs/aws-f2/iteration282/`.
