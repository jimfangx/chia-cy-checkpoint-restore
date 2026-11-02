# Prepared publication of the FASED host owner

Iteration 9794 adds prepared checkpoint publication to the production
`FASEDMemoryTimingModel` host driver. Its existing completed-call payload format
is unchanged: configuration, lifecycle, profiling history, histogram baselines
and range-counter buffers remain independently validated and restored.

Preparation allocates and validates every replacement buffer without changing
the destination, performing MMIO, or replaying output files. Sealing checks
the destination lifetime, creating thread, generation, complete saved bytes and
deferred-output flag. Destruction before publication, including after sealing,
cancels the candidate. Publication checks the guard before accessing the owner,
then uses only integer copies, buffer swaps and scalar assignments. The ordinary
profile/finish path materializes restored output history later.

Every ordinary init/profile/finish call invalidates older candidates before
its lifecycle checks or external effects. Legacy loads invalidate them only
after complete parsing/allocation, before the same no-throw application helper.
Identical-byte loads and state changes followed by restoration cannot revive an
old candidate. Expired, unsealed, reused, stale or wrong-thread publication
fails the process before touching the destination. The aggregate coordinator
still owns exclusion through every owner's complete readback.

The regression retains every existing native ASan/UBSan and VCS DPI case and
adds a separate fresh prepared restore for every cut and instrumentation
geometry. An independent Python oracle checks complete bytes before the first
edge, every subsequent MMIO operation and all profiling/histogram/range output.
Negative cases include malformed/configuration-incompatible payloads, active
or poisoned calls, terminal lifecycle, candidate cancellation, destination
address reuse, threads, generation changes, aggregate cancellation, preparation
and sealing allocation failures, and allocation-free publication. Fresh native
processes exercise fail-stop misuse. Every verifier invocation keeps its own
attempt, source snapshots, commands, logs and artifact digests beneath `runs/`.

This is host-owner integration, not an FPGA state donor or complete CPU
restore. The actual FASED timing-model registers, ingress/egress, outstanding
host-memory transactions and functional DRAM remain separate hardware owners.
The stock exact Rocket recipe still lacks complete production capture binding.
Physical CE/common-cut/reset/writer ownership, the transport's capture epoch,
complete restore, localhost image implementation/AFI, four active hardware cuts,
FPGA-to-EDA finite/live migration and rolling hardware recovery remain pending.
The independent image guard remains mandatory. No new RTL was changed or
checkpoint-enabled image built by this host-only increment.

Replayable commands and fresh verification receipts are under
`automations/checkpoint_loop/runs/aws-f2/iteration9794/`:
`run-eda.py` runs FASED and retained publication/bank/host/FCFS/cut regressions on
EDA; `run-rocket-guard.py` and `run-rocket-selection-guard.py` retain the exact
Rocket compiler's unsupported physical-owner and missing-widget refusals on
the manager. Final EDA verification passes 80 fresh continuations / 240
operations, sixteen malformed fresh processes, 49 preparation and nineteen
sealing allocation failures on each backend, allocation-free publication and
five native fail-stop processes. The retained configuration/scalar/base
publication suites, all 422 Python tests and bank/host sanitizer/FCFS/cut scope
also pass. The initial retained-harness linker failure remains separate:
removing its trailing `--as-needed` preserves the SP2 runtime libraries, and
all active publication compiles request `-Mupdate`. No check or sanitizer was
removed. Original receipts retain their remote EDA paths and source snapshots.
