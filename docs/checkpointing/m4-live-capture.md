# M4 complete live VCS capture — iteration 40

M4 remains in progress. `capture_durable_snapshot` now collects complete live
generated RTL, harness and native state for the compiled audited profile. The
verification-only `+test-live-capture` hook invokes it at the existing completed
operation / settled host-negedge event, then publishes through the native
encoder and atomic writer. Public `+fs-checkpoint` remains disabled. Public cut
scheduling and opt-in normal Make integration are the next increment.

The collector reuses the generated, harness and aggregate restore tables. It
requires every manifested clock to be known low and rejects debug/global-reset
harness state. Every native owner must match the complete ordered inventory,
have a unique non-null pointer and a supported schema, and validate its saved
payload. VPI capture checks exact handle kinds/widths, every address, unknown
bits, word padding, low BUFGCE outputs, reset and finish. The checkpoint target
cycle comes from the compiled 64-bit FASED `model.tCycle`, with a separate host
sample. All native payloads and all generated/harness words are reread to detect
state changes across adapters. No loads, deposits, MMIO or simulation edges are
issued by collection or publication. The native publisher validates the whole
snapshot before accessing the output destination.

`simif_emul_t::require_settled_checkpoint_capture` checks the parked worker
boundary and low-clock request, rejecting managed stream IO, QSFP and more than
four functional-memory channels. Unsupported native/driver inventories fail
closed. The worker remains parked throughout native collection and publication;
the existing harness resumes the same driver operation after the observer
returns. Outstanding traffic is retained, without draining it.

The sanitizer collector verifier uses a complete independently encoded fixture
with a 257-bit scalar, 64-bit target counter, every 9-bit FIFO address, a BUFGCE
output, nonzero harness banks and opaque native payloads. Its staging bytes
match Python exactly. All 225 native/VPI rejections pass with the output sentinel
unchanged, including adapter side effects, unknown bits, reshaped/missing handles,
padding, clocks, controls and unsupported/aliased native owners. The real pthread
guard verifier passes at the parked cut, rejects other phases and unsupported
topology, and preserves all three checked native owners with no added edges.

All five final-code live VCS captures match the complete independent Python
container byte-for-byte. Fresh public restores match all 3,765,516 complete
40-port samples through completion at 774,628/774,632 target cycles, including
outstanding native/FASED writes. All owners are read back before any edge and
bootstrap issues zero edges. The independent audit passes 68 processes,
67,537,280 generated-word and 85 native-owner comparisons, and all five live
publications. All 56 public restore corruption/configuration/dispatch/special-file
rejections pass. The native publication suite also passes all 149 malformed
snapshots, 11 syscall faults, four special destinations, three killed-writer
boundaries and 16 concurrent writers; a repeat preserves all 503 earlier
fixture/log inodes and hashes.

The first 11 live dispatch and four publication failures preserved their outputs
and exited with status 1, but calling the generic restore failure helper at a
parked capture also produced a VCS segmentation-fault context dump. The capture
DPI entry now flushes diagnostics and calls `_Exit(1)` on error, without running
VCS/exit handlers or fallback startup. The failure verifier now rejects crash
dumps explicitly. All 11 actual-entry live dispatch rejections and four complete
live publication failures now pass without crash dumps and with outputs
preserved. Full final-code public/live continuations and independent audits pass
under `public-restore-current` / `live-capture-current` with this correction.

All 44 retained baseline and 15 focused scopes pass, including ordinary clean
RTL VCS, full M2/M3, public/restricted complete continuations and independent
audits, repeated consumer rejections, 90 entry dispatch cases, runtime identity,
counters/profiling, dispatcher lifecycle/bootstrap, full-size publication faults
and actual-trace mismatch diagnostics. The baseline audit initially lacked its
local plan-hash catalog; generating it from the saved initial hashes allowed
the full audit and every unfinished scope to pass. The older public executable
correctly failed its source audit after implementation changes; final focused
results use the new current executable. Both initial diagnostics are retained.
Results are retained under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m4-iteration40/`.
`live-verification-commands.json` contains exact argv arrays. Diagnostic logs and
development runs are retained there; `live-capture` predates the final topology
guard. The earlier `*-final` runs predate the immediate-exit correction; only
`*-current` can establish final source-bound evidence.
`results.json` records the 44 baseline scopes; `focused-final-results.json` records
all 15 focused scopes; `live-current-followup-results.json` records the independent
live audit and actual failure checks. `artifact-manifest.json` lists full artifact
paths and source/input hashes; `executed-verification-commands.json` contains
actual command argv arrays. `final-integrity.py` verifies these catalogs and the
source-bound evidence. Initial fixture errors and all development artifacts are
retained separately.

Run from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_durable_capture \
  --out automations/checkpoint_loop/runs/m4-iteration40/native-live-capture
python -m tools.checkpoint_formats.tests.verify_capture_guard \
  --out automations/checkpoint_loop/runs/m4-iteration40/capture-guard
python -m tools.checkpoint_formats.tests.verify_production_aggregate_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration40/live-capture-current \
  --public-restore --live-capture
python -m tools.checkpoint_formats.tests.audit_production_aggregate \
  --out automations/checkpoint_loop/runs/m4-iteration40/live-capture-current
python -m tools.checkpoint_formats.tests.verify_live_capture_requests \
  --production automations/checkpoint_loop/runs/m4-iteration40/live-capture-current \
  --out automations/checkpoint_loop/runs/m4-iteration40/live-request-rejections-current
```

Both plans remain read-only; no proposed plan correction is needed. Level-1 and
Level-2 formats remain independent. No missing external dependency has been
observed. No physical FPGA, formal, ASIC gate-level or power validation is claimed.
