# M4 production entry — iteration 35

M4 remains in progress. The complete FCFS/FASED restart verifier now compiles
the real production `entry.cc`, rather than reconstructing its platform,
generated registry and simulation in a separate test entry. Public
`+fs-checkpoint`/`+fs-restore` remain fail closed; the durable runtime API still
requires integration before milestone acceptance.

The optional `FS_CHECKPOINT_ENTRY` capability supplies a factory before platform
construction and a prepare hook after simulation creation, before `run`.
Normal construction order and ownership stay in `entry.cc`. An enabled build
without a factory fails to link; a null capability or exception exits the
process explicitly because VCS ignores the entry return code. Restore prepare
reserves the fresh harness clock hold before workers, MMIO or native ticks.
All-owner prevalidation, load/readback and zero-edge bootstrap still happen
through the existing aggregate coordinator while that hold remains armed.
Default builds do not invoke this optional hook.

The integration exposed an existing cross-translation-unit type mismatch:
`entry.cc` owned `unique_ptr<simif_t> simulator`, while DPI declared that object
as `simif_emul_t *` and deleted/overwrote it as a raw pointer. Both now use the
shared declaration in `entry.h`; DPI obtains a checked derived view and releases
the actual owner with `reset()` after joining the worker. The small harness
dispatcher fixture uses the same ownership contract. No checkpoint owner,
target counter, operation ordering or host timing policy is removed.

Native build identity now binds the actual entry translation unit and capability
compile flag. The independent artifact audit checks those build inputs and the
logged compile command, then verifies configuration/construction/reservation
order before any owner loads. Unsupported configuration/library hooks reject
before platform construction. This is still an explicitly restricted test
capability, not a general audited production checkpoint API.

Verification artifacts are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m4-iteration35/`.
The Python suite passed all 49 tests. All five fresh production-entry VCS
continuations match 3,765,516 complete 40-port samples, retaining 13,507,456
generated words, 29 harness records and 17 native owners per cut, including
outstanding native/FASED write traffic, with complete pre-edge readback and
zero-edge bootstrap. Completion remains 774,628/774,632 target cycles. All 23
malformed loads and six compatibility changes reject before loading/edges;
unsupported profiling rejects before platform construction. Sixteen full-size
publication failures, four actual-trace mismatch mutations and runtime identity
ASan/UBSan (41 rejections/12 independent ELF hash comparisons) pass.
The independent production audit passes 42 distinct simulator processes,
67,537,280 generated-word and 85 native-owner comparisons, including actual
entry compilation and reservation order. All 44 retained baseline scopes pass,
including Python/Scala suites, ordinary clean RTL VCS, full M2/M3, native/VCS
owners, profiling/counter expectations, rejection liveness, full low-clock
comparisons, terminal completion, dispatcher/bootstrap and the independent
100-process fixture aggregate audit. No comparison or test scope was removed.
The initial verifier invocation stopped on a Python indentation error before
building; its diagnostic is retained separately and is not passing evidence.

Reproduce from the Chipyard root, sourcing `env.sh`, `sims/firesim/env.sh`,
then `automations/checkpoint_loop/vcs-env.sh` last for VCS checks:

```sh
python -m unittest discover -s tools/checkpoint_formats/tests -v
python -m tools.checkpoint_formats.tests.verify_production_aggregate_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration35/production-entry
python -m tools.checkpoint_formats.tests.audit_production_aggregate \
  --out automations/checkpoint_loop/runs/m4-iteration35/production-entry
python -m tools.checkpoint_formats.tests.verify_durable_artifacts \
  --production automations/checkpoint_loop/runs/m4-iteration35/production-entry \
  --out automations/checkpoint_loop/runs/m4-iteration35/durable-production-faults
python -m tools.checkpoint_formats.tests.verify_runtime_identity \
  --out automations/checkpoint_loop/runs/m4-iteration35/runtime-identity-verified
python automations/checkpoint_loop/runs/m4-iteration35/verify-production-first-mismatch.py
python automations/checkpoint_loop/runs/m4-iteration35/run-all-regressions.py
python automations/checkpoint_loop/runs/m4-iteration35/final-integrity.py
```

The full-path artifact catalog is `artifact-manifest.json` in this iteration's
run directory; `focused-verification-commands.json` contains the exact command
arrays. Both starting plan hashes and all bound native sources are checked
after the baseline builds.

Next: connect durable aggregate capture/loading to the public production runtime
API through this capability, retaining exact configuration/library binding,
all-owner prevalidation/readback and the settled low-clock cut. No required
external dependency is missing. Level-2 formats remain independent; no physical
FPGA, formal, ASIC gate-level or power validation is claimed. Plans, conda files
and PDFs remain untouched and unstaged; no commit/reset/clean.
