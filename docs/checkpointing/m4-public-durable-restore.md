# M4 native public durable restore — iteration 37

M4 remains in progress. The audited FCFS/FASED VCS build now has a concrete
public `+fs-restore=PATH` capability. Public capture publication and normal Make
integration still need implementation. The default build and the retained test
capability continue to reject public durable requests. Level-2 remains independent.

The native consumer reads a regular `.fsckpt` once and verifies its complete
image before platform construction. Its generated C++ table binds the v3
profile, generated/harness inventories, native schemas, implementation hash
and target-cycle owner. It verifies the exact running executable, container
magic/length/SHA-256, canonical JSON with sorted unique keys/owners, exact
membership/shapes, every generated word's padding, low generated clock and
harness reset/finish state, and agreement with the manifested FASED counter.
The accepted image becomes in-memory staging; public restore does not depend
on Python, sidecar manifests or a staging pathname. Symlinks, special files
and files over the audited profile's explicit 256 MiB limit fail closed.

Production entry constructs one generated registry, platform and driver. The
capability reserves fresh clocks before ordinary run, then the settled VCS
coordinator prepares every native owner and both compiled VPI tables before
loading anything. Complete native readback, generated/harness settlement and
readback precede the existing zero-edge bootstrap. The restored dispatcher
cannot fall through to initialization. Public capture, private staging
bypasses, conflicting diagnostic capture controls, unsupported arguments,
widgets and drivers reject explicitly.

The standalone native consumer passes 96 ASan/UBSan rejection cases and its
staging bytes match the Python format oracle. The 90 actual-entry native/VCS
dispatch cases, 49 Python tests and runtime identity checks (41 rejections,
12 independent ELF hash comparisons) pass. All five final public VCS
continuations match 3,765,516 complete 40-port
samples, preserving 13,507,456 generated words, 29 harness records and 17
native owners per cut, with full pre-edge readback and zero-edge bootstrap.
The independent audit passes 68 distinct processes, 67,537,280 generated-word
and 85 native-owner comparisons, including outstanding native/FASED writes.
All 56 public rejection cases, 16 full-size publication failures and four
actual-trace mismatch diagnostics pass. The retained restricted capability
also passes all five continuations and its independent 42-process audit, 23
malformed loads, six compatibility changes and 15 public request rejections.
All 44 retained baseline scopes pass, including ordinary clean RTL VCS, full
M2/M3 replay, counters/profiling, rejection liveness, complete low-clock
comparisons and independent dispatcher/aggregate audits. The development public build predates
the final aggregate file-error poisoning correction. Final evidence uses
`public-restore-final`.

Reproduce from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_durable_restore \
  --out automations/checkpoint_loop/runs/m4-iteration37/durable-native-final
python -m tools.checkpoint_formats.tests.verify_production_aggregate_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration37/public-restore-final \
  --public-restore
python -m tools.checkpoint_formats.tests.audit_production_aggregate \
  --out automations/checkpoint_loop/runs/m4-iteration37/public-restore-final
python automations/checkpoint_loop/runs/m4-iteration37/run-all-regressions.py
```

Exact focused argv arrays are in `focused-verification-commands.json`; the
final full-path artifact catalog is `artifact-manifest.json`.

All diagnostic logs belong under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m4-iteration37/`.
Both plans remain read-only; no plan corrections are proposed. No required
external dependency is missing. No physical FPGA, formal, ASIC gate-level or
power validation is claimed. No staging, commit, reset or history cleanup.
