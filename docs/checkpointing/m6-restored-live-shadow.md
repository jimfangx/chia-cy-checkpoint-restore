# M6 restored FCFS live shadow — iteration 52

`bridge_live_shadow.py` adds a host-only adapter for the schema-2,
bridge-extracted FCFS target. `FS_CHECKPOINT_SHADOW=1` links the known socket
transport into the production checkpoint binary while preserving the strict
production driver selection and all 17 native owners. Compile the observer
before capture: adding it after capture would change the native build identity
and invalidate the Level-1 image.

The opt-in public entry validates exactly four observer controls (socket,
session identity, semantic origin and saved FASED label), requires public
restore, and excludes only this validated set from future-environment
compatibility. Partial/duplicate/unknown controls, malformed labels and use
in ordinary builds or capture reject. Startup connection waits are bounded
at 600 seconds to accommodate complete production readback; each target-cycle
ACK still has the independently tested 30-second deadline.

All 14 data inputs come directly from their audited transformed-DUT bindings.
All 34 data outputs are compared, including the seven independently audited
erased constants/input aliases. The proven forwarded `ep_clock` is a clock
alias, not a data field. Missing inputs, changed shapes/definitions, incompatible
images and inconsistent cut labels reject before generating restore data.

The clean process loads the independent `.rtlckpt`, settles, and uses
`semantic_verify` to read back every semantic word before its first edge.
The verifier streams VPI bit-vector checks, including unknown-bit rejection,
instead of generating 13 million SV assertions. The restored authority waits
for the public zero-edge bootstrap, verifies the saved FASED label, and starts
its semantic counter at the independently observed Level-2 origin. It counts
actual gated DUT rising edges; no universal FASED offset is assumed.

At each actual DUT edge the authority sends the full settled pre-edge boundary
and blocks for its ACK. The clean process applies every input, settles, compares
every output, takes one edge, and ACKs. Only the authority drives FASED and the
environment. Packets are generated live; no saved input trace drives either
process. A mismatch uses the transport's flushed `_Exit(1)` path so a parked
FireSim worker cannot hang VCS teardown.

Run `verify_bridge_semantic_vcs --live` with both repository environments and
`vcs-env.sh` sourced last. It retains the complete paired-state/readback and
pre-edge corruption scope, then builds ordinary clean VCS and starts two fresh
public Level-1 restores: a full workload and a real clean queue-RAM bit flip
at semantic origin + 100. The live verifier requires more than 100,000 matched
cycles, substantial actual AXI traffic, complete edge counts and termination
at the first output divergence. Its separate `live/summary.json` is the live
acceptance artifact; the paired invocation's `summary.json` describes only the
pre-edge checks.

Diagnostic artifacts and exact argv are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m6-iteration52/`.
Verification results and remaining work are recorded in `progress.md`.

The rebuilt paired invocation is `paired-semantic/invocation-7in7vzpj/`.
Its healthy live pair matches **250,185** cycles, C=524453..774637, and all
**8,506,290** output comparisons. Metasim completes its workload at reported
cycle 774628. Its native finalizer then rejects two late-loaded VCS libraries:
`/ecad/tools/synopsys/vcs/Y-2026.03-SP1/linux64/lib/liberrindex.so` and
`/ecad/tools/synopsys/vcs/Y-2026.03-SP1/linux64/lib/libsystemcerror.so`.
Both files exist; their hashes are in `late-vcs-libraries.json`. The guard
remains intact, both actors exit 1, and clean RTL receives EOF before END.
This is a lifecycle failure after matching boundaries, not a healthy run pass.

`corruption-check.py` runs the mandatory fault case after that failed healthy
case, using the same already built executables, independent images and session.
It flips bit 0 of the actual clean AR queue memory word selected by its dequeue
pointer. The checker reports `ep_axi4_ar_bits_qos expected=0 actual=1` at
C=524553 with 100 clean edges; only C=524453..524552 are acknowledged.
Both actors stop at pending cycle 524553. Complete pre-edge readback and the
public zero-edge bootstrap ran again in these two fresh processes.

The run-directory audit's `--partial-live` mode verifies this specific failure,
the sustained record/held-payload checks and actual first-divergence evidence.
It reports `live_shadow_acceptance=false` / `healthy_end_verified=false`.
The full verifier still fails; no check or runtime identity guard was removed.

Next: warm or explicitly load the two pinned release-specific diagnostic
libraries **before** native identity construction for capture and restore,
bind their bytes through the existing full ELF inventory, recreate the native
image and rerun the complete healthy/fault scope. Do not whitelist late loads
or refresh the compatibility owner after entry. Whether warmup must invoke
the string-returning DPI machinery as well as load the files needs verification.
The sidecar's cycle-origin contract remains local to the observed cut; the
bridge's final reported cycle is not a substitute for actual gated DUT edges.

Both plans remain read-only; the loop's M6 still corresponds to Phase 8 / M7
in the agent input plan. No physical FPGA or ASIC validation is claimed.


## Iteration 53 — healthy END acceptance

`checkpoint_vcs_runtime_warmup()` now loads the two exact release-specific
VCS diagnostic table paths before the public capability constructs its immutable
compatibility owner. It requires `VCS_HOME=/ecad/tools/synopsys/vcs/Y-2026.03-SP1`,
retains both handles for process lifetime and fails explicitly on loader errors.
The ordinary complete ELF inventory binds both table bytes and dependencies;
no late-load exemption or post-entry identity refresh is used.

The new source-bound invocation is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m6-iteration53/paired-semantic/invocation-t4usmy06/`.
Fresh capture and ordinary public restore both pass at reported cycle 774628.
Full semantic readback still verifies all 1,543 entries / 13,503,308 words before
any clean edge; Level-1 restore retains all 17 owners and zero-edge bootstrap.

The healthy live pair matches C=524453..774637: **250,185 target cycles** and
**8,506,290 output comparisons**. Both actors exchange END at C=774638,
report exactly 250,185 actual DUT edges and exit 0. A second fresh pair flips
bit 0 of the real clean AR queue word at C=524553; `ep_axi4_ar_bits_qos` first
changes there, after exactly 100 acknowledged cycles. Both actors exit 1 with
cycle 524553 pending. No later boundary is acknowledged.

The complete scope and independent audit pass: 81 Python / 24 Scala tests,
complete M2/M3, 46 runtime-identity rejections, 24 transport sanitizer cases
including the real 30-second timeout, 21 shadow-control cases, eight VCS
readback cases and five actual public-entry rejections. The schema-1 fixture
matches 107,531 cycles and detects its real fault at cycle 29. The native oracle
checks all 14 warmed ELF hashes and fresh load; the production container audit
checks all 43 captured ELF hashes, including both diagnostic tables. All held
ready/valid payloads are checked across the five AXI channels.

`verification-commands.json`, `independent-evidence.json`, `summary.json` and
`artifact-manifest.json` under the iteration-53 directory contain exact argv,
complete acceptance evidence and the full-path artifact catalog. The invocation's
`live/summary.json` has `live_shadow_acceptance=true`. Both plan hashes and
staging are preserved. M6 is ready for this supported FCFS profile; unknown
state/topologies remain explicit rejections. No FPGA or ASIC validation is claimed.
