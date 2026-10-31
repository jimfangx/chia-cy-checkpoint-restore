# FAME progress role identities

Iteration 296 adds typed construction-site metadata for the observations from
iteration 295. Each model retains its original identity and complete domain
list separately from live FIRRTL ReferenceTargets. A two-clock model has 21
roles: host clock/reset/completion, completed-step and overflow registers, and
each domain's consume/launch/pending observations, counters, original pending
register, native CE and native output clock.

References are rooted at their concrete execution immediately after FAME.
Gate pins use nonlocal leaf-port targets. Module-local `instance.field` targets
can survive native inlining with stale module identities; they cannot establish
the required mapping. The native abstract-to-BUFGCE replacement now translates
only exact concrete CE/O progress roles through a FIRRTL RenameMap at the
actual replacement. Other references to retired definitions remain rejected.
SimulationMapping may retain the original inner root inside the outer platform.
Its typed references are accepted only when that parent has exactly one reachable
execution; repeated or unreachable relative parents remain unsupported.

The final checker reads the emitter's actual prepared IR, opens its instance
connectors using the existing direction-checked analysis, and follows compiler
renames rather than inferred emitted names. It checks complete role cardinality,
unique execution, kind/width, gate input/CE/output associations, pending-register
connectivity and register clock/reset ownership. Synchronous reset lowering is
checked in its actual data mux after RemoveReset. Construction-site model/domain
identities and role keys must survive the production host/emitter pipeline.

Inventory-enabled emission produces `.fame-clock-progress.json`, binding roles
to exact targets, emitted paths, complete generated storage StateIDs, RTL,
prepared IR and inventory hashes. The map explicitly declares
`capture_supported: false` and `global_target_cut_proven: false`. It records
321 observer bits and two original pending bits for the two-clock fixture.
It does not prove counter arithmetic against arbitrary malicious compiler
rewrites; source-pinned functional execution and independent raw-wave auditing
remain separate checks.

This is a role map, not production collector wiring, target-cycle authority,
physical CE-latch ownership or an FPGA capture transport. Whole-root bank
specialization of these new annotations still requires an explicit translation
contract. The observed exact-Rocket bank trial explicitly rejects both new annotation
classes before specialization. A separate ordinary exact-recipe trial checks
the existing missing-FASED-physical-owner guard. Neither is image admission.
No checkpoint-enabled AFI, hardware checkpoint, FPGA-origin CPU restore/replay,
live RTL acceptance or rolling hardware recovery follows from this metadata.

Reproducible commands, fresh attempts and original diagnostic logs are under
`automations/checkpoint_loop/runs/aws-f2/iteration296/`. Reuse iteration 194's
retained localhost build invocation. The next implementation step is selective
all-owner freeze/cut and bank/collector binding using these concrete references,
including independent FASED, channel, memory, transport and host-owner progress.
All physical CPU acceptance remains pending until a complete local image build
and actual F2 execution produce both checkpoint levels and their boundary trace.

Exact-Rocket read-only production emission now passes with 21 bound roles and
11,465 inventoried generated storage entries. Sixteen focused compiler tests
cover the linked inner-root case, native inlining, emitter renames and negative
metadata cases. This generated inventory includes simulator adapters and is not
a physical FPGA state inventory or capture image.

Current verification passes 369 Scala tests / 59 suites plus sixteen preparation
checks, sixteen focused tests and the complete retained 409 Python / 61 manager /
EDA sanitizer, host, bank, FCFS and cut scope. Source-final observer/collector
components close unchanged 140 MHz at +2.768/+0.051 and +1.720/+0.035 ns; shell
and parent timing remain unmodeled. SP2 execution and raw-wave audits pass all
321 observer / 81 collector bit mutations, 21 role-path mutations, overflow and
first-divergence observation cases. Closure:
`runs/aws-f2/iteration296/final-audit-d53wmq0n/summary.json`. No hardware acceptance
column advances.
