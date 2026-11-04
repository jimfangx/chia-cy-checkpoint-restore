# Shared regional-router state and held restore

Iteration 9810 adds a synthesizable opt-in interface to
`CheckpointRegionStateRouter.sv`. It exposes every sequential bit of this
router, including inactive values: `{owner, invalid, pending}`. For `R`
regions the owner occupies `max(1, ceil(log2(R)))` bits, above invalid bit 1
and pending bit 0. No snapshot storage or new sequential owner is introduced.

`RESTORE_SUPPORTED` defaults to zero. Existing generated regional callers
continue operating with restore disabled. The existing wildcard-port regression
explicitly ties off the new inputs. Production graft/manifest attachment,
state-bank allocation and atomic staging of this vector remain pending.

With restore enabled, assert `restore_hold` before loading. Hold blocks upstream
request readiness and response validity, downstream request validity and response
readiness. The router retains all state while endpoints and selectors change.
`restore_load` atomically loads the entire vector on the raw rising clock edge.
Keep hold asserted, deassert load, and independently compare `capture_state`
with the original source image before releasing hold. Releasing hold exposes
the restored outstanding response to its original endpoint; only a subsequent
accepted transaction changes the pending bit. Shared reset dominates loading.

A load without hold or an owner index outside the generated region count
asserts `restore_error`, suppresses all handshakes and preserves all state.
The error is combinational; callers must retain the control through its detecting
edge and maintain hold during validation. The interface does not supply a global
sticky fault controller or complete reset/clock ownership.

The directed qualification uses public ports and separate fresh source and
destination VCS processes. Actual source files contain idle, pending functional,
inactive functional-owner, pending invalid and inactive invalid states. A separate
ABI sweep restores all four flag combinations for every legal owner, including
inactive payload bits. Width cases are 1, 2, 3 and 255 regions. The disabled case
runs real transactions with unknown restore inputs. Negative cases cover every
representable invalid owner, unheld loading, reset cancellation and semantic
corruption before any acknowledged transaction. Debug VCDs retain all signals. A separate waveform auditor reconstructs all
three raw owner fields and rising-edge transitions from public accepted
transactions. It checks the first donor loads against the independent source
file, rather than trusting the restore input. All twenty per-bit mutations of
the readback checker reject across the four widths.

Replayable commands (all evidence goes beneath loop `runs/`):

```bash
# f2 backend; current manager and native HDK/Vivado only
bash -c 'bash automations/checkpoint_loop/runs/aws-f2/iteration9810/run-native.sh'
# eda backend only; the dedicated mirror and native SP2 toolchain
bash -lc 'export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"; source automations/checkpoint_loop/vcs-env.sh && python3 -m tools.checkpoint_formats.tests.verify_region_router_restore --mode vcs --out automations/checkpoint_loop/runs/aws-f2/iteration9810/router-restore'
```

Qualification passes 443 Scala tests, 81 manager tests, thirteen fresh EDA
debug-wave cases, 1,044 exhaustive ABI encodings, twenty donor restores and all
twenty per-bit checker mutations. The existing router regression passes 6,155
checks plus its boundary/configuration/corruption cases. Full retained FASED,
publication, Python/bank, host sanitizer, FCFS and cut scopes also pass.
Native restore-enabled three-region synthesis retains 124 LUTs and all four
original state registers on the raw clock. Default-router synthesis also passes.
Consult `progress.md` and the iteration's individual receipts for failed attempts
and closing integrity audits. Native synthesis covers this component;
its resource count cannot establish complete-image timing or achieved F2 Fmax.
This does not capture the physical routers, functional reader/CE response
pipelines, controller/staging owners, functional memory, host/bridge owners or
pre-FAME semantic state. Those owners must be held/restored independently and
bound to the same atomic cut. Full-image localhost implementation/AFI, physical
F2 capture, paired CPU zero-edge/finite/live migration and rolling hardware
recovery remain pending/in_progress. No hardware acceptance column advances.
