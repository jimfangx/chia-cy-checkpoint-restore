# M4 public entry dispatch contract — iteration 36

M4 remains in progress. Production entry now has a typed, fail-closed dispatch
contract for public Level-1 requests. A concrete durable runtime capability is
still required; neither default builds nor the restricted aggregate test
capability enables public save/restore. Level-2 formats remain independent.

`checkpoint_request_t` parses `+fs-checkpoint=PATH`, `+fs-restore=PATH` and the
existing inventory preflight before capability/platform construction. It rejects
empty paths, malformed options and duplicate/conflicting requests. Paths remain
opaque, including spaces; parsing does not open files or publish anything.

An enabled capability must explicitly authorize a public durable request before
platform construction. The base authorization rejects durable requests, so
defining `FS_CHECKPOINT_ENTRY` alone cannot enable them. Default builds reject
them before constructing the platform. The missing-factory link requirement,
null/throwing-capability process failure and normal generated construction
order remain intact. Inventory preflight retains its diagnostic rejection.

For an authorized durable request, entry runs generated widget preflight before
constructing the simulation and checks every concrete driver owner for a
nonempty supported schema before preparation. Empty inventories and null owners
fail explicitly. It passes the parsed request to `prepare`. Public restore must
return `restore_reserved`; capture must return `run`. Incorrect actions fail
the process before ordinary startup. The capability remains responsible for
actually reserving fresh clocks, complete container/build/configuration
validation, all-owner loading/readback and zero-edge bootstrap; a returned enum
alone does not establish those properties.

`verify_checkpoint_entry` compiles the actual production entry translation unit
with observer platform/registry/driver declarations. All 90 native ASan/UBSan
and VCS DPI dispatch cases pass, including malformed/conflicting requests,
default/inherited rejection, missing/null/throwing capabilities, unsupported
widgets/drivers and incorrect prepare actions. Enabled builds without a factory
fail to link. Every failure exits explicitly; restore never invokes ordinary
run. Checkpoint inputs remain unchanged and no checkpoint output is published.
Native address/undefined-behavior checks remain enabled; leak detection excludes
entry's documented process-lifetime registry allocation. Observer fixtures
verify dispatch only and are not full generated-state restore evidence.

The full generated production-entry build rejects all 15 additional public
request cases before platform construction, preserving checkpoint inputs and
publishing nothing. All five fresh FCFS/FASED continuations match 3,765,516
complete 40-port samples through 774,628/774,632 target cycles, preserving
13,507,456 generated words, 29 harness records and 17 native owners per cut.
The late cut retains outstanding native and FASED writes. All 23 malformed
loads, six runtime compatibility changes and unsupported profiling reject
without loading/advancing. The independent audit passes 42 processes,
67,537,280 generated-word and 85 native-owner comparisons. All 16 full-size
publication failures, four actual-trace mismatch mutations, 49 Python tests
and runtime identity ASan/UBSan (41 rejections/12 ELF hash comparisons) pass.
All 44 retained baseline scopes pass, including ordinary clean RTL VCS, full
M2/M3, native/VCS owners, profiling/counter expectations, rejection liveness,
full low-clock comparisons, terminal behavior, dispatcher/bootstrap and the
independent 100-process fixture aggregate audit. The baseline audit initially
stopped on a missing hash-catalog filename; its diagnostic is retained, and
the expected catalog was generated from the saved initial plan hashes. The
resumed runner completed every unfinished scope without reducing comparisons.
Dispatch cases were rerun after setting their VCS simulation working directory
to the diagnostic run directory.

Additional verification and its exact commands are recorded under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m4-iteration36/`.
The focused command catalog is `focused-verification-commands.json`; the final
full-path artifact catalog is `artifact-manifest.json`. Diagnostic logs remain
under the run directory.

Reproduce from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_checkpoint_entry \
  --out automations/checkpoint_loop/runs/m4-iteration36/entry-dispatch
python -m tools.checkpoint_formats.tests.verify_production_aggregate_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration36/production-entry
python -m tools.checkpoint_formats.tests.verify_public_entry_requests \
  --production automations/checkpoint_loop/runs/m4-iteration36/production-entry \
  --out automations/checkpoint_loop/runs/m4-iteration36/public-entry-requests
python -m tools.checkpoint_formats.tests.audit_production_aggregate \
  --out automations/checkpoint_loop/runs/m4-iteration36/production-entry
python automations/checkpoint_loop/runs/m4-iteration36/run-all-regressions.py
python automations/checkpoint_loop/runs/m4-iteration36/final-integrity.py
```

Next: implement a concrete durable capability using this request contract,
binding supported capture scheduling and runtime configuration to the existing
validated publication/staging APIs. It must preserve the complete settled
low-clock inventory, validate/load/read back every owner before target time
advances, and keep unsupported drivers/configurations fail closed. Public API
integration remains a prerequisite for milestone acceptance. No required
external dependency is missing; no physical FPGA, formal, ASIC gate-level or
power validation is claimed. Plans/conda/PDFs remain untouched and unstaged;
no commit/reset/clean.
