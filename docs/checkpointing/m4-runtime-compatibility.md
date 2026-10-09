# M4 runtime compatibility — iteration 33

M4 remains in progress. Production `entry.cc` still rejects `+fs-checkpoint`
and `+fs-restore`. This increment binds the existing full production test-entry
restart to its runtime configuration, loaded implementation and cycle indexing;
it does not enable the durable production entry.

The test entry adds an immutable `runtime/compatibility` owner. Its explicit
profile requires positive memory size and cycle horizon, zero VCS register and
memory initialization, and binds effective host-delay and full-width seed
values. Unknown options, duplicates, preload/audit library hooks and unaudited
callbacks fail closed. Test
capture/output paths do not participate in configuration identity. This is a
restricted FCFS/FASED profile, not an argument audit for arbitrary drivers.

`runtime_identity.cc` enumerates the executable and loaded ELF objects with
`dl_iterate_phdr`, canonicalizes their paths and hashes every file with SHA-256.
Addresses and ASLR do not participate. The kernel vDSO has no file-backed
simulator state and is excluded. Membership and hashes are rechecked at capture,
native validation/readback and exit. The executable, generated shared archive,
VCS libraries, conda libraries and OpenSSL implementation are all bound. The
owner uses OpenSSL headers and libcrypto, available on this machine; its actual
loaded conda libcrypto implementation is included in the identity.
It captures immutable compatibility, not arbitrary library globals. Missing
files, changed bytes or newly loaded objects reject explicitly.

The production packed aggregate uses `firesim.aggregate.lowclock.v3`, binding
the manifested 64-bit `FPGATop.FASEDMemoryTimingModel_0.model.tCycle` counter and
its loader path. The target-cycle field means this model counter at the settled
low-clock cut; host samples count preceding host rising edges. Completed driver
operations remain a third index. Python rejects a checksummed container whose
cycle disagrees with its generated counter before publishing staging. The
compiled coordinator separately checks the retained prepared VPI scalar before
any native load or RTL deposit. Existing v1/v2 and Level-2 formats are unchanged.

Plan clarification for later milestones: a Level-1 consistent cut can occur
inside model/driver progress and during reset. Its bound model counter,
completed host edges and completed driver operations must not be interpreted as
the Level-2 pre-FAME edge index. This clarification is recorded here; neither
input plan is edited.

Native ASan/UBSan passes 41 rejections and 12 independent ELF SHA-256 comparisons,
including altered configuration, malformed/unsupported arguments, changed
digests and changed library contents at the same pathname. All 43 Python tests
pass. Five final-implementation fresh VCS continuations match all 3,765,516
complete 40-port transaction samples at 774,628/774,632 target cycles, including
outstanding native/FASED writes. Each preserves 13,507,456 generated words,
29 harness records and 17 native owners, with complete readback and zero-edge
bootstrap. The independent audit passes all 42 simulator processes, 67,537,280
generated-word comparisons and 85 native-owner comparisons. All 23 malformed
loads and six runtime compatibility changes reject before loading/edges;
preload hooks reject before construction/reservation. Four mutations of actual
traces identify the expected first cycle/port mismatch. All 44 retained baseline
scopes pass: 43 Python/20 Scala tests, ordinary clean RTL VCS, full M2/M3,
native/VCS owners, GCD/FASED, profiling/counter expectations, rejection liveness,
complete low-clock captures/comparisons and independent component/state audits.

Commands, per-process logs and artifacts are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m4-iteration33/`.
The initial production trial predates the explicit library-hook guard and is
retained separately from `production-bound-final`; it is not final evidence.
The final matrix's first rejection assertion incorrectly expected the new
compatibility owner to reject before existing geometry/timing owners. That
diagnostic expectation is corrected, and the resumed verifier rechecks all
five completed continuations and their current build before rerunning every
rejection and sanitizer scope. The initial failure logs are retained.
Reproduce from the Chipyard root, sourcing `env.sh`, `sims/firesim/env.sh`, then
`automations/checkpoint_loop/vcs-env.sh` last:

```sh
python -m tools.checkpoint_formats.tests.verify_runtime_identity \
  --out automations/checkpoint_loop/runs/m4-iteration33/runtime-identity-verified
python -m tools.checkpoint_formats.tests.verify_production_aggregate_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration33/production-bound-final
python -m tools.checkpoint_formats.tests.audit_production_aggregate \
  --out automations/checkpoint_loop/runs/m4-iteration33/production-bound-final
python automations/checkpoint_loop/runs/m4-iteration33/run-all-regressions.py
```

Next: integrate the validated container and compatibility owner with production
`entry.cc`, publish durable captures atomically, and exercise the public API in
fresh VCS processes. Keep unsupported drivers fail closed. No physical FPGA,
formal, ASIC gate-level or power validation is claimed. Plans, conda files and
PDFs are preserved without staging, commit, reset or cleaning.
