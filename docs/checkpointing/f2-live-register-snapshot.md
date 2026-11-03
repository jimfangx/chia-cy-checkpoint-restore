# Live register subtree staging

`NativeCheckpointRegisterSnapshot` adds combinational observation routes for
every register in one concrete hierarchy and connects them to the existing
`CheckpointNativeStateSnapshot` staging module. Shared module definitions expose
the same vector independently at each execution; only the selected execution
routes to the staging input. Original register declarations, next-state
equations, resets, clocks, instances, ports and effects remain unchanged.
Signed fields retain their exact bit representation. The layout binds original
StateIDs, concrete paths, widths, offsets and declaration/equation hashes.

All selected registers must use one transparently routed root clock. Memories,
opaque descendants, unresolved storage, stale paths, clock casts/gates,
ambiguous drivers and namespace collisions reject. The root's staging controls
are explicit: reset, request/release, owner and frozen-target certificates,
target-cycle label and a bounded word address. All original state is sampled
immediately before one accepting positive raw-clock edge. The original live
registers continue running while serial words come from the retained copy.
The existing staging implementation revokes visibility on faults before the
edge and retains sticky errors. Its entire payload/occupancy/cycle/error vector
is exposed as a separate owner, with production restore disabled.

The opt-in `--simulator-native-register-snapshot-probe` requires one regional
compiler diagnostic and a single concrete path. It writes a separate staged
circuit at the actual compiler boundary. It does not replace the regional
image circuit or waive its incomplete-image guard. The actual Rocket AW reorder
queue is selected at
`F1Shim.top.ctrlInterconnect.xbar.router.aw_queue`: 192 registers / 704 bits,
eleven serial words and 775 staging-owner bits. The equivalent AR selection is
also exercised by the Scala checks. Separate selections do not establish a
common AW/AR cut.

The full control fabric has **395 registers and thirteen memories**, totaling
408 entries / 1,749 stored bits. The complete-fabric request deliberately
rejects its memories; no RAM state is silently omitted. The native/VCS component
uses the exact selected Rocket definitions, extracted from the retained
compiler input with provenance. A fresh exact-recipe compiler diagnostic also
exercises the new attachment. Neither component input nor diagnostic output
is evidence of an FPGA-origin checkpoint.

The independent Python auditor reconstructs the original complete register
inventory, ordered vector, every ancestor/child clock and observation route,
source-preservation equations, staging ABI/parameters, certificates, original
StateIDs and the actual staging source. The executable verifier exercises a
shared-instance/signed/multiword fixture and the real reorder-queue definitions
on localhost Vivado and fresh EDA SP2 VCS. Functional initialization/enqueue
traffic supplies original state; no simulator state writes are used. An
independent original execution supplies every expected bit and output while
the live source changes under a held snapshot. Compiled payload corruption
must stop at its first unequal word before that word is acknowledged. Exact
commands, raw failed attempts and final receipts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration9798/`; progress.md records
which checks actually completed.

The original debug oracle is emitted separately from the exact original
FIRRTL, with a complete set of register `DontTouch` annotations. These retain
otherwise unused state through emitter dead-code elimination; they add no
capture logic and change no original equation. The independent checker verifies
the original circuit bytes, exact annotation prefix and complete added target
set, emitted register declarations and reference-source hashes. Native and VCS
receipts bind the same oracle. The initial VCS attempt exposed an optimized-away
signed register in the unprotected oracle; its compiler log is retained.

Global target-cut/reset/writer/host ownership, simultaneous AW/AR staging,
control-fabric memories, MMIO/DMA attachment, original and staging restore,
complete descriptor coverage, FASED/functional memory/bridge/pre-FAME ownership,
full image P&R/AFI, actual F2 capture and paired finite/live CPU migration remain
required. The descriptor manifest still reports these owners as uncovered;
none of the new metadata grants production admission.
