# M5 progress watchdogs — iteration 46

The audited FCFS/FASED VCS capability accepts these optional host policies with
public periodic history or public restore:

```text
+fs-checkpoint-host-timeout-ms=1000
+fs-checkpoint-cycle-timeout-ms=1000
+fs-checkpoint-capture-timeout-ms=600000
```

At least one progress deadline and a positive bounded capture deadline are
required. Values are strict unsigned millisecond integers bounded by the
signed nanosecond steady-clock range. Duplicate, incomplete, malformed,
overflowing, unsupported-mode and unknown checkpoint controls reject before
platform construction. Builds without a durable capability still reject.
These options do not enter native target-state identity or either checkpoint
level; a fresh restore initializes a fresh host monitoring epoch.

The existing settled completed-operation callback samples the same compiled,
manifested 64-bit FASED target-cycle counter used by collection. Initial target
reset must drain before monitoring arms. Later resets/regressions reject.
Restore-only monitoring schedules settled polling without a periodic capture
deadline. Its first actual settled sample occurs after bootstrap (two target
cycles after the audited 500000-cycle retained cut); it never synthesizes a
sample at the loaded cut or advances a clock to sample. It issues no MMIO, deposits, loads or added simulator/target edges.

An independent thread reads `steady_clock` and coherent host copies. It never
calls VPI or reads software owners. Its sampling-lock attempt is nonblocking:
if the sampler holds that lock indefinitely, the monitor continues aging its
last coherent copy. Host progress means a completed settled callback; target
cycle progress means that the manifested counter increased. The failure
reasons are `host_progress_stall`, `target_cycle_stall`, or `capture_stall`.
The monitor writes its diagnostic without stdio locks and exits the process
without VCS exit handlers, checkpoint publication, history pruning or worker
acknowledgment. Diagnostic trace buffers can end with a partial row.

Intentional full capture, complete image validation and atomic history
commit/readback/retention pause the ordinary progress deadlines. Resumption
adds only elapsed capture time to their time origins, preserving stall age
that preceded capture. This suspension has its own independent bounded
deadline; stalled collection/publication cannot disable monitoring forever.
The capture deadline must accommodate full-size state and local host load.
The first concurrent VCS trial exceeded its 60-second bound and correctly
reported `capture_stall`. Final verification uses an explicit ten-minute bound
while keeping the one-second ordinary progress deadlines. Failed/superseded
trials stay in the run directory. An initial restore-only check also exposed
full loaded-ELF hashing at every new polling callback. The coordinator and
verification observer now suppress these repeated audits for watchdog polling,
as they already do for periodic polling. Complete restore/capture and final
identity audits remain. All source-bound production scopes were rerun successfully
against the corrected generated coordinator.

Native ASan/UBSan evidence covers exact deadlines, stalled hosts, stalled target
cycles while host callbacks continue, bounded capture exclusion, pre-capture
stall age, invalid transitions, time/counter regression, strict public parsing,
clean monitor shutdown and a deliberately held sampling lock. Both production main-thread-only late-stall replays now pass, with all 17
native owners read back before any edge. The host and cycle failure diagnostics
report target cycles 600025 and 600002 respectively; first settled samples are
500002 after the loaded 500000-cycle origin. Each detector exits about 1.2
seconds after the confirmed thread stop. A healthy monitored replay matches
all 366116 continuation rows. Current live history also passes three original
and two restored-run commits, newest-two retention, fresh recapture restores
and all existing rejection scopes. All five full production captures/fresh continuations and 56 restore rejections
pass. Independent audit verifies 68 fresh processes, 67537280 generated-word
and 85 native-owner comparisons. All 63 Python tests, native history
fault/crash/concurrency, 142 entry cases, full M2/M3/dispatcher/harness, Make
rejections and ordinary clean RTL VCS also pass. Consult the concrete summaries
and exact argv catalog under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m5-iteration46/`
before treating a scope as completed.

The dedicated production verifier uses `PTRACE_SEIZE`/`PTRACE_INTERRUPT` to park
only the VCS main thread after target cycle 600000. The production monitor
remains runnable; the verifier supplies no external watchdog. It selects the
live-retained 500000-cycle image through complete locked integrity validation,
checks native readback/zero-edge bootstrap and compares every available replay
trace byte with the uninterrupted reference. A separate healthy continuation
must match the entire reference suffix. The live-history verifier additionally
checks all existing capture, retention, restore, corruption and rejection scopes
with monitoring enabled and captures longer than the ordinary deadline.

This implements host and target-cycle liveness. A running target that stops
retiring instructions or completing workload transactions while its cycles
advance still needs a separately audited semantic progress counter. Requests
for unknown semantic watchdog controls reject explicitly. M5 remains in
progress until that support and its injected failure replay are verified.
Monitoring before the first audited settled post-reset sample is also outside
this increment's coverage. Level-1 and Level-2 remain independent; there is no
physical FPGA, ASIC activity/power or formal validation claim. Both root papers'
checkpoint interval and complete-state/trace replay sections were reread from
the retained extracted texts. Plan-number corrections remain solely in earlier
checkpointing documentation; neither plan was edited or staged.
