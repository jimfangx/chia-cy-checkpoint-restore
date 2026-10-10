# M5 rolling history foundation — iteration 43

The requested milestone is `M5-rolling-checkpoints`. The read-only agent plan
labels rolling checkpoints M6/Phase 7 and M5 as DMA; the human plan places
rolling Level-1 history after full simulator restart. Proposed correction:
align milestone names with the loop's current identifier. Neither plan was
edited. Implement this task's rolling scope, preserving Level-1/Level-2
independence and the existing audited FCFS/FASED v3 capture/restore contract.

`tools/checkpoint_formats/rolling.py` provides a host-side API for complete
settled-cut images. It requires the v3 manifest-bound FASED target-cycle
counter, complete generated/harness/native membership, canonical encoding,
SHA-256 and matching build identity. Native opaque payload semantics remain
the fresh all-owner coordinator's responsibility before any target edge.
This API neither captures live simulator state nor accepts semantic `.rtlckpt`.

Use a private existing directory for one build and retention setting. Writers
and readers lock a no-follow regular lock file in a pinned directory. Each
snapshot has an immutable cycle/content-hash name and mode 0600. The writer
syncs the complete image, publishes its immutable name, syncs the directory,
and reopens/validates every byte. A separately synced canonical `history.json`
is atomically replaced and directory-synced: this index is the commit point.
Its complete readback precedes retention. Old snapshots survive every failure
before that point. An index visible after rename but before confirmed sync is
reported with `HistoryError.committed=True`; old snapshots are still preserved.

Only committed snapshots are selectable, strictly before the requested causal
target cycle. Selection returns validated bytes while holding the lock; callers
must consume those bytes or publish a separate restore input, rather than
reopen a pathname that retention could remove. `recover()` validates all
retained state, syncs the index directory, then completes interrupted pruning.
Only fully validated unreferenced images in this build's owned namespace can
be removed. Partial pending files and foreign files are preserved. Retention
bounds committed images after successful publication/recovery; failed or killed
writers can temporarily leave additional complete images or pending files.
An exact orphan left before index commit can be reused by a publication retry.

`CycleSchedule` uses target cycles, never driver operations or host edges.
The first settled cut at/after a deadline is eligible. A leap across deadlines
creates one actual cut; it does not fabricate intervening snapshots. Publication
failure leaves a deadline due; deadlines advance only after commit. Unsigned
64-bit boundaries cannot wrap. Restore requires an explicit restored-cycle
origin and fresh policy objects; regressing counters fail explicitly.

`ProgressWatchdogs` supplies policies for a frozen host-progress counter or
frozen target-cycle counter using independent monotonic host time, and lack
of audited retirement/transaction progress using advancing target cycles.
An enabled target watchdog rejects a missing progress counter. Failures latch;
counter regressions and changed availability reject before policy updates.
No timer thread or live worker sampler is enabled by this increment. Runtime
integration must sample independently of the worker, define supported target
progress, and account explicitly for intentional capture suspension/overhead.

All 63 Python tests pass (53 retained plus 10 new), and ordinary clean RTL
compiles and runs on VCS Y-2026.03-SP1 full64. Verification artifacts are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m5-iteration43/`.
The full Python suite exercises nine I/O faults, five actual SIGKILL boundaries,
concurrent writers/readers, immutable-input and special-file rejection,
recovery/retry, pinned-directory replacement, deadline/overflow and both
watchdog policies. Initial fixture diagnostics are retained separately.

The full-size verifier admits the four existing live default-timing M4 cuts
(0, 1, 524402, 524404 target cycles), retains the newest two, and selects the
strictly earlier cut at 524402. It runs the unchanged source-bound production
VCS executable in fresh processes from that retained image, injecting an
external SIGSTOP after observing target cycle 600000 and detecting the frozen
worker by independent host time. The first process is killed after detection;
the second independently repeats injection/detection and resumes to completion.
Every available byte of the first trace and the complete second trace must
match the uninterrupted reference, with complete native pre-edge readback and
zero-edge bootstrap. This is an external host-stall test, not a target deadlock
or an integrated periodic-capture runtime. The verifier records actual outcomes
in its invocation-specific `summary.json`. The completed invocation is
`rolling-vcs/invocation-f3e_8ifd/`: both late stalls were detected; the first
process's 7,667,712 available trace bytes (including a partial final row)
match the reference prefix. The resumed second replay matches all 333,580
complete samples across 40 transaction ports through target cycle 774628.
Both fresh processes read back all 17 original native owners before any edge.
Each retained image includes all 13,507,456 generated words and 29 harness
banks. `final-integrity.py` independently verifies trace bytes, source/input
preservation, results and a full-path artifact catalog.

Reproduction commands (from the Chipyard root):

```sh
python -m unittest discover -s tools/checkpoint_formats/tests -p 'test_*.py' -v
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rolling_history_vcs \
  --production automations/checkpoint_loop/runs/m4-iteration42/normal-make-settled \
  --out automations/checkpoint_loop/runs/m5-iteration43/rolling-vcs
```

Next: connect repeated settled-cut dispatch and complete live collection to
`CycleSchedule`, add supported public configuration and capture-on-restored-run
support, acknowledge commit before releasing the worker, integrate independent
host sampling and an audited target-progress owner, and prove periodic history
rewind/reproduction of an injected late failure in the actual runtime. The
milestone remains in progress until those checks run. No missing dependency,
physical FPGA, formal, ASIC gate-level activity, or power validation is claimed.
