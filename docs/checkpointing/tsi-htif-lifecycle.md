# Actual HTIF exit and stopped fields

Iteration 131 adds an **opt-in host component**, independent of the direct-exit
recorder. It reads and restores the actual provider's private
`std::optional<int> exitcode` and `bool stopped`. An absent optional, a present
zero, even/odd raw values and all 32 signed status bits remain distinct. Loading
assigns those fields directly after validation. It never reissues a command,
calls `stop()`, switches a context or performs a target memory operation.

`build_checkpoint_fesvr.py --htif-source PATH` requires the source's `htif.h`
to match the installed header byte for byte. In a temporary include tree it
adds only a friend declaration for the accessor, and compiles the unchanged
`htif.cc` method bodies followed by `htif_lifecycle_provider.inc`. The build
report binds both generated hashes, all source hashes and archive members.
The independent audit reconstructs the generated source/header from snapshots.
Only `htif.o` is additionally replaced; the existing ELF-loader/context
replacements remain, and every other installed archive member is byte identical.
The installed archive and headers are untouched. A mismatched source/header
rejects without replacing an existing output archive or report.

The default overlay and recipe Make integration still retain installed
`htif.o`. The new provider is selected only by the explicit option. The kind-32,
revision-1 component image binds the 32-bit integer and no-signature/no-signal
policy; it is not a build-bound `.fsckpt`. `tsi_htif_lifecycle.h` adapts the
actual provider fields to the component interface. No complete CPU profile or
twelve-owner polling admission is enabled.

The caller must suspend HTIF and serialize accesses. SIGINT, SIGTERM and SIGABRT
must be blocked in the calling thread; pending signals, the delivered global
latch, changed handler identity and signature mode reject. These are
prerequisites and rejection checks, not ownership/restoration of process-wide
signals or other threads. In particular, both pending and delivered signals
reject even after an optional zero exit is already set. The destination must
have absent exit and `stopped=false`. Complete parsing and provider guards
precede nonthrowing field assignments. All malformed images and occupied
destinations reject without a partial lifecycle restore.

The new suite reuses the production FireSim/TestChip TSI serial peer with an
optional capture observer. Both original cache policies and all eight direct
payloads retain their complete five historical component images, packet order
and host-tick labels. At all **1,216 source cuts**, the observer additionally
reads both actual provider fields. Every producer terminates before any fresh
destination starts. Native and VCS destinations restore these fields into the
actual final FireSim TSI class and read back the complete component before
calling any service. All **2,432 fresh readbacks** match an independent Python
oracle. Subsequent no-signature stop behavior matches too, with serial queues
unchanged. The native harness uses ASan/UBSan; the provider archive uses its
ordinary optimized build flags.

Additional reference-provider sources distinguish absent/present zero,
even/odd raw statuses, sign bits and independent stopped flags: **88 fresh
cross-backend readbacks**. **282 malformed/incompatible image processes**,
**18 signal/signature/occupied-destination rejections** and **20 valid-image
raw-status corruptions** pass. Flipping the low status bit leaves `exit_code()`
unchanged, but the complete private-field comparison detects the fault at
host boundary zero, before acknowledging or servicing that boundary. These
are component faults, not Rocket semantic DUT corruption tests.

Accepted diagnostics:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration131/lifecycle-final/invocation-y0rvbsmo/summary.json`.
Separate audit: `m11-iteration131/lifecycle-independent-audit.log`.
The interrupted preliminary lifecycle invocation and changed-source native-regression pilot are excluded.
Executable commands are in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Next: bind the opt-in provider into the exact-recipe metasim build and its
aggregate preparation, then complete session/descriptors, syscall parents,
process signals, outer caller/context and coherent simulator-wide CPU cuts.
Level 1 fresh CPU continuation and independent Level 2 captured CPU
readback/replay remain pending. BOOM/Saturn remain pending. Physical FPGA,
standalone Shuttle and ASIC power remain excluded.
