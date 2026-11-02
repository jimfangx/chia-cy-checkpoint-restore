# Generated common cut for native regions

Iteration 9795 adds `NativeCheckpointRegionClockCut.generate` to connect the
existing selective native-region bank network to the synthesized
`CheckpointPhysicalClockCut`. This is a bounded compiler integration and
component fixture. It does not replace the ordinary Rocket output, remove its
physical-owner refusal, or admit a checkpoint-enabled image.

The compiler reconstructs the region banks, global descriptor identities,
physical CE order and shared readout graft before attaching one controller.
The controller uses the proven common raw clock with
`EXTERNAL_CLOCK_NETWORK=1` and `RESTORE_ENABLE=0`. Its falling-edge mask drives
all selected subtrees; its post-stop logical CE sample drives their bank-255
endpoints. The enclosing host, unselected executions and bank/router clocks
retain their original raw clock. No second functional execution or second set
of native gates is introduced by the attachment.

The mask, read permission and captured-CE signals become controller-driven
outputs. The caller supplies a shared controller/readout reset, freeze request,
ordered external-owner presence vector and target-cycle value. These explicit
inputs are prerequisites, not authenticated production acknowledgements or
proof of target-time authority. In particular, stopping FASED's selected
subtree does not freeze its external AXI ingress/egress, outstanding memory
traffic, reset writers or host owners.

Both directions of the outer bank request/response interface are gated by
physical read permission, including invalid-selector responses. Data and error
outputs are suppressed when permission is absent. New requests also require
the caller's freeze request. An explicit raw-clock register records accepted
requests and holds the effective cut until the accepted response drains,
including healthy request withdrawal during backpressure. This register is
independent of endpoint readiness. A new owner, CE or target-cycle fault
revokes handshakes combinationally; the existing sticky controller keeps the
cut stopped until shared reset. A lost cut never fabricates a response
acknowledgement or discards an accepted beat.

The exposed control vector contains the existing `GATES + 70` physical
controller bits followed by the accepted-request pending bit. It remains live
control state requiring an atomic capture/restore owner. Native shell banks
and borrowed synchronous-reader state are rejected by this attachment until
such staging is integrated. Coverage deficits are copied from the reconstructed
regional descriptor manifest. Complete FPGA capture, deployable image,
production writer/reset ownership, target-time authority, atomic controller
ownership and metasim restore support all remain false.

The focused Scala suite passes six tests covering generated connectivity,
independent raw host clocks, all handshake gates, explicit pending state,
ordered owners, retained coverage deficits, coherently rehashed circuit
changes, altered resources, reserved identifiers and unsupported shell owners.
Its full fixture is under
`automations/checkpoint_loop/runs/aws-f2/iteration9795/scala-common-cut/generated/bank/native-regions-common-cut/`.
The original regional audit artifacts are retained alongside `attached.fir`,
`attached.sv`, `cut-binding.json`, `graft-binding.json` and the exact controller
source. The fixture has two existing native executions, four sampled logical
CEs, six BUFGCE instances including their two generated root masks, fourteen
descriptors and two explicitly uncovered raw ancestor counters. The first
launch's runtime-directory error and the initial post-lowering reset emission
failure remain in their original logs; `scala-common-cut-attempt3.log` records
the passing focused run. Native synthesis and EDA VCS evidence are separate
receipts maintained by the central iteration.

The fresh exact-Rocket regional diagnostic with FAME observation exposes a
separate strict boundary: region banking wraps observer updates in a freeze
hold, while the original FAME role contract requires the original next-state
equation. It rejects this changed equation rather than treating the wrapper as
an authenticated owner. The failed exploratory compile is retained under
`iteration9795/rocket-regional-inspect/`; FAME validation is unchanged.

Production integration still requires an authenticated FAME freeze mapping,
complete FASED/channel/functional-memory/bridge/host/reset writer fences,
atomic ownership of collector and readout state, an ungated production
MMIO/DMA path, original pre-FAME semantic state and physical-CE restore mapping.
Full localhost image timing/P&R/AFI, active all-hart FPGA captures, paired
FPGA-origin zero-edge restores, finite replay, sustained live clean-RTL
comparison and rolling hardware recovery remain pending.

The independent Python checker reconstructs the original root/region hierarchy,
complete controller pin types, CE order, raw clock, handshake gates and pending
next-state/reset. Eight coherently rehashed wiring mutations reject. A separate
raw VCD checker derives pending state from accepted request/response edges,
checks original state and actual BUFGCE output nets through each held cut, and
audits failed tails through EOF. Four altered-wave probes reject fault repair,
a gate edge after failure, a response after failure and a mismatched pending
owner. Original waves remain intact. The exploratory EDA healthy case passes
9,537 bench checks, four complete cuts / 280 descriptor reads, 285 requests /
284 responses (one deliberately reset pending beat), 64 withdrawal-stall edges
and 868 observed physical gate edges during active execution. All nine physical
fault modes pass in separate fresh processes. These exploratory receipts precede
completed native qualification; final source/native-bound receipts are separate.

The expanded verifier's final-source retained rerun initially stopped before
VCS at its unchanged 8 GiB reserve (8,021,585,920 bytes available). Byte-preserving
recovery resumes the existing explicit generated-source sharing plan at row
2,195. It authenticates complete before/after hashes and preserves independent
original files/inodes, including every waveform. Recovery shares 1,134 pairs and
raises free bytes from 7,788,113,920 to 17,181,511,680, with no removed files.
The failed attempt and recovery receipt remain under iteration9795; all checks
and sanitizer/debug scope are retained for the subsequent fresh rerun.

A production attachment must coordinate with the one existing widget transport
controller, rather than layering independent cut authorities. This sibling API
by itself supplies neither that production connection nor complete state capture.

The final full Scala sweep passes 407 tests / 64 suites plus sixteen preparation
checks. Both final exact-Rocket negative compiler checks preserve all 321 FAME
observer bits and the physical-owner/missing-widget refusals. All eight
current-source native Vivado component syntheses pass on this manager, with at
most two jobs after the JVMs exit. The new cut component uses 2,148 LUTs,
996 registers and six BUFGCEs; 347 control/readout registers are independently
checked against the raw source clock, including the new pending owner and the
physical controller. Placement and full-image timing remain unproven.
The new native receipt is selected by `common-cut-native-selected.json`;
EDA VCS verifies those exact compiler/source/native-bound inputs separately.

Final source/native-bound EDA SP2 verification passes eleven fresh cases and
retains eleven full debug VCDs. The independent EOF auditor passes the healthy
case and nine faults and detects the compiled CE response defect at target
cycle 37, bank 255 slot 2, with 67 requests / 66 acknowledgements; neither that
bad word nor a later response is acknowledged. The final receipt also proves
all eight rehashed wiring and four raw-wave checker mutations reject. Both
retained and component EDA command groups pass on final source, retaining all
422 Python tests, FASED and configuration/scalar/base publication, host ASan/
UBSan, generated-bank, FCFS and cut checks. Native/EDA receipts, original remote
paths, commands, hashes and source snapshots are selected under iteration9795.
No physical FPGA checkpoint, complete CPU restore or live CPU acceptance is
established by these component tests.
