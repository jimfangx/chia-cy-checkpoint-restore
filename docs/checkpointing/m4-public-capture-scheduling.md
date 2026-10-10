# M4 public settled-cut capture scheduling — iteration 41

M4 remains in progress. The audited FCFS/FASED VCS capability now accepts
`+fs-checkpoint=/absolute/output.fsckpt +fs-checkpoint-operation=N`. `N` counts
completed driver operations, not target cycles or host clock edges. The actual
target cycle remains bound to the manifested 64-bit FASED `model.tCycle`.
The request is parsed before capability/platform construction; missing, empty,
zero, signed, overflowing, duplicate, orphaned or conflicting schedules reject.
The public capability requires a schedule. Ordinary builds retain rejection.

Before worker startup, the capability arms the existing completed-operation
dispatcher with a settled low-clock cut. Neither a diagnostic path nor private
capture plusargs is needed. The `FS_CHECKPOINT_DURABLE` VCS harness callback runs
after the falling edge and settled observer event, while the worker remains
parked. It collects the complete compiled generated/harness/native inventory,
validates it, and atomically publishes through the existing native writer.
Successful publication must be acknowledged before `checkpoint_settled` can
release the worker. A missing callback therefore fails explicitly at the cut.
Publication errors exit immediately without VCS exit handlers or crash dumps.
An unreachable schedule fails at driver completion without publishing.

The diagnostic cut may accompany a public request only when its operation and
low-clock/settled modifiers match, supporting the independent full-state oracle.
The public schedule can also run without these diagnostic controls. The new
harness host-edge counter is capture observer metadata: it never drives target
logic, MMIO, AXI, clocks or the dispatcher and is irrelevant after a fresh
restore. Captured target-cycle metadata and restored execution state remain
independent of that counter. The existing 29 harness records retain their
geometry; the audited harness source hash now binds the optional callback.

The full verifier's `--public-capture` mode uses public plusargs and the ordinary
opt-in harness callback, omitting the verification-only collector observer.
It compares all five native images byte-for-byte with the independent Python
oracle, then restores each actual published image into a fresh VCS process.
`verify_public_capture` additionally exercises every cut without diagnostic
controls, compares the complete image and uninterrupted trace, then checks a
second fresh restart with exact pre-edge native readback. Separate processes
have distinct historical `gettimeofday` reporting baselines in the final
16 bytes of `runtime/simulation/base`; the eight timestamp bytes are bounded
independently by the capture process launch/completion wall times before
binding that field for the cross-process canonical image comparison. Every
other image byte must match, and every original native byte, including that
timestamp, must read back exactly before the restored process takes an edge.
The first verifier incorrectly required the timestamps of two separate
processes to match. Its five complete captures and matching full target traces
are retained under `public-capture-requests-final`; the corrected full rerun
uses `public-capture-requests-verified`. No production state or capture code
changed for this oracle correction. It also checks scheduling rejection, special destinations,
unreachable cuts and an executable compiled without the callback.

Final verification results are retained under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m4-iteration41/`.
The native live collector's 225 ASan/UBSan rejections, native writer fault suite,
real-worker guard (including missing publication acknowledgment), 142 native/VCS
entry dispatch cases, ordinary clean RTL VCS and full M2 checks have passed.
All five final public continuations and their independent 68-process audit
pass, with 3,765,516 complete transaction samples, 67,537,280 generated-word
comparisons, 85 native-owner comparisons, all five publications and 56 public
restore rejections. All 44 retained baseline and 15 final-source focused scopes
pass. All five corrected diagnostic-free public capture/restarts pass another
3,765,516 complete transaction samples, with exact native pre-edge readback,
independently bounded reporting timestamps and unchanged durable inputs.
All 19 public scheduling rejections, four publication failures, an unreachable
schedule and an actual missing-callback executable fail closed. The legacy
verification observer retains its five full continuations, independent audit,
11 request rejections and four publication failure checks.
Development directories `public-capture`, `public-capture-current` and
`public-capture-final` predate the final source revision and cannot authorize
source-bound acceptance. `public-capture-verified` is the final-code run;
`public-restore-verified` is the final executable without the public callback.
The earlier `public-restore-final` correctly fails the current source audit and
must not authorize acceptance. Final focused scopes rerun its consumers against
the current executable.

`results.json`, `final-focused-results.json`, `native-results.json` and
`extra-results.json` retain the actual command results. The final direct public
result is `public-direct-result.json`; its detailed evidence is under
`public-capture-requests-verified`. `native-repeat-audit.json` proves all 503
prior immutable fixture/log inodes and hashes unchanged. The first repeat
catalog included two mutable summary files; its diagnostic is retained, and
the corrected fixture catalog and repeated complete publication suite pass.
`initial-public-oracle-diagnostic.json` binds the initial timestamp mismatch
to all five retained complete captures and identical uninterrupted traces.
`executed-verification-commands.json` contains exact successful command argv
arrays, and `artifact-manifest.json` lists full artifact paths and source/input
hashes. `final-integrity.py` checks these source-bound results, owner/word/timing
comparison counts and plan preservation.

Next: opt-in normal Make integration, including generation of the complete
compiled inventory and restore coordinator. `FS_CHECKPOINT_DURABLE` currently
requires explicit harness build integration; ordinary Make builds do not enable
the public capability. This increment does not implement rolling capture or
capture during a restored continuation. Level-1 and Level-2 remain independent.
No missing external dependency has been observed. Both plans remain read-only
with their initial hashes preserved. No plan corrections, conda/PDF edits,
staging, commits, reset/clean, physical FPGA, formal or ASIC validation.

Run from the Chipyard root, with both environments and `vcs-env.sh` sourced last:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_production_aggregate_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration41/public-capture-verified \
  --public-capture
python -m tools.checkpoint_formats.tests.audit_production_aggregate \
  --out automations/checkpoint_loop/runs/m4-iteration41/public-capture-verified
python -m tools.checkpoint_formats.tests.verify_public_capture \
  --production automations/checkpoint_loop/runs/m4-iteration41/public-capture-verified \
  --without-hook automations/checkpoint_loop/runs/m4-iteration41/public-restore-verified \
  --out automations/checkpoint_loop/runs/m4-iteration41/public-capture-requests-verified
```
