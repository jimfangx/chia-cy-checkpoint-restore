# Held restore of regional cut staging

`NativeCheckpointRegionCutSnapshot.generate(..., restoreStaging = true)` adds an
explicit whole-owner restore interface to the generated regional cut snapshot.
The default compiler path ties restore off and exposes no new external controls.
The opt-in is a generator API; production CLI/recipe and widget/MMIO integration
remain unsupported.
This option restores the separate staging owner; it does not restore the live
physical controller, accepted-request bit, routers, endpoints or original DUT.

The packed owner retains `{error, cut_cycle, occupied, payload}`, including
released payload and donor errors. A qualified raw positive edge replaces every
field together. Hold or load keeps the physical freeze request asserted and
revokes snapshot visibility and all bank handshakes. Unsafe current owners,
physical permission, reader activity, requests, release or borrow prevent loading;
reset dominates. Retain hold after loading and independently compare every bit
before making the snapshot visible. Loading a donor with sticky errors remains
possible when the current cut is safe. This adds no sequential storage.

The version-three attachment binding records complete owner widths, source and
resource hashes, exact generated routes and the staging-only restore contract.
Independent structural auditing checks both enabled and disabled connections.
The ordinary compiler's MMIO and complete-image guard remain unchanged.

Qualification inputs, original failed attempts, native synthesis receipts and
EDA commands are retained under
`automations/checkpoint_loop/runs/aws-f2/iteration9814/`. The entry point is
`python3 -m tools.checkpoint_formats.tests.verify_regional_staging_restore`,
using `--mode vivado --compiler <receipt>` here and
`--mode vcs --native <receipt>` on EDA SP2. Original endpoints and the controller
are independently prepared through public inputs in each fresh process; only
the staging owner migrates in this regression. Sustained held readback is not
live CPU continuation.

Current-source localhost synthesis retains all 146 / 153 staging registers on
the raw clock. Whole-fixture resources are 2,381 / 2,384 LUTs and 1,142 / 1,149
registers, respectively; this is OOC synthesis without a full-image Fmax claim.
The updated fixture withdraws the host freeze request during held loads and
checks both original target counters remain at cut 38. The first two native
cases and their exact pre-refinement testbench are retained separately. Fresh
EDA SP2 VCS qualification passes 38 processes, eight actual component donors
and 630 successful complete owner loads. All 299 waveform-checker bit mutations
reject; two compiled payload faults stop at the first readback at target cut 38
with zero acknowledged bank edges. Full debug waves and nine unsafe-load or
label-drift cases per width are retained. All 447 Scala / 430 Python / 81 manager
tests, fourteen current-scope native
synthesis cases and the complete retained EDA SP2 sanitizer/FASED/publication/
bank/FCFS/cut/router/caller/staging regression scope pass. Closing auditing
checks 22,364 bindings across 30 receipts; consult progress.md and the command
index for exact paths. No hardware acceptance advances.

Fresh exact-Rocket auditing retains 2,701 definitions, 37 adapter routes and
81 observation / 152 staging bits. Its actual compiler stops at the existing
image guard with 1,245 uncovered functional entries and unbound cut MMIO.
This produces no image, AFI or hardware checkpoint.

Full cut/MMIO and original-controller/router/reader/endpoint integration,
functional-memory and host/bridge/pre-FAME ownership, a complete localhost
image build and AFI, active all-hart F2 captures, paired zero-edge CPU restores,
finite replay, live RTL comparison and rolling FPGA recovery remain pending.
No hardware acceptance advances from this component work.
