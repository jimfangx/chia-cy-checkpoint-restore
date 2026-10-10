# M4 repeat verification — iteration 38

M4 remains in progress. This increment repairs the iteration-37 verification
failure while preserving the complete durable-consumer and public VCS test
scope. Public capture publication and opt-in Make integration remain pending.

The loop reran `verify_durable_restore --out .../durable-native-final` against
an existing output directory. Recreating its fixed `symlink` path raised
`FileExistsError` after the ordinary corruption cases, before the special-file
checks completed. The public VCS verifier had the same fixed-path problem.
Both now allocate retained invocation directories for special inputs rather
than deleting or following earlier fixtures. Summaries record their absolute
paths. Native special-file rejections also check that the output sentinel is
unchanged; public special-file logs stay with their input directory.

The independent public artifact audit checks each recorded input's actual
symlink/FIFO/directory type, the path in the simulator argv, the failed process
exit, and rejection before platform construction. It retains support for the
historical log layout. The old full public artifact audit passes this branch.

Two new executable regressions repeat actual consumers against the same
directory, with the original fixed-path fixtures present. Native verification
passes both independent Python staging comparisons and all 192 ASan/UBSan
rejections, preserving old fixture inodes/types and sentinel contents. The
exact previously failing command also passes all 96 rejections. Public repeated
verification additionally checks unchanged hashes of every production
checkpoint and the executable, retains both special-file logs, and runs the
complete independent state/transaction/process audit after each invocation.

Both new public/restricted VCS runs pass all five continuations and all their
rejections. Each matches 3,765,516 complete 40-port samples, preserving
13,507,456 generated words, 29 harness records and 17 native owners per cut,
including an outstanding native/FASED write, with pre-edge readback and
zero-edge bootstrap. Independent audits pass 68 public / 42 restricted
processes, 67,537,280 generated-word and 85 native-owner comparisons per run.
Both repeated public invocations pass all 56 rejections and their complete
audits, with unchanged production hashes and retained old fixtures/logs.
All 49 Python tests, 90 dispatch cases, runtime identity sanitizers, 16 full-size
publication failures, 15 restricted public request rejections and both sets of
four real-trace mismatch mutations pass. All 44 baseline scopes pass, including
ordinary clean RTL VCS, full M2/M3 replay, native/VCS owners, hardware counters,
profiling, rejection liveness, complete low-clock owner comparisons, dispatcher
integration, the 100-process aggregate audit and bootstrap/reservation guards.

Run from the Chipyard root, sourcing both environments and the VCS helper last:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_durable_restore_repeat \
  --out automations/checkpoint_loop/runs/m4-iteration38/durable-repeat
python -m tools.checkpoint_formats.tests.verify_production_aggregate_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration38/public-restore \
  --public-restore
python -m tools.checkpoint_formats.tests.verify_public_durable_restore_repeat \
  --production automations/checkpoint_loop/runs/m4-iteration38/public-restore \
  --out automations/checkpoint_loop/runs/m4-iteration38/public-repeat
python automations/checkpoint_loop/runs/m4-iteration38/run-all-regressions.py
```

Diagnostic logs and exact argv arrays are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m4-iteration38/`.
`results.json` records all 44 baseline exits; `followup-results.json` records
the six dependent audits/rejection/mismatch checks. `artifact-manifest.json`
lists full artifact paths and source hashes; `executed-verification-commands.json`
contains only executed commands. The original loop failure remains in
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/verification.log`.
Both plans remain read-only, with initial hashes retained; no plan corrections
are proposed. Level-1 and Level-2 remain independent. No external dependency is
missing, and no physical FPGA, formal, ASIC gate-level or power validation is
claimed. No staging, commit, reset or history cleanup was performed.
