# M5 public live retained history — iteration 45

The audited `FS_CHECKPOINT_PROFILE=fcfs-fased-v1` VCS capability now accepts:

```text
+fs-checkpoint-directory=/absolute/private/existing/directory
+fs-checkpoint-interval=250000
+fs-checkpoint-retention=2
+fs-checkpoint-level=1
```

The interval counts actual manifested FASED target cycles. All four options
are required; values must be positive unsigned 64-bit integers. Duplicate,
malformed, Level-2, single-capture/preflight and private-capture combinations
reject before platform construction. Builds without an explicitly authorized
durable capability also reject. A public restore may supply these options
with a new history directory and explicit restored-cycle schedule origin.
Restoring during the initial target reset remains unsupported.

`durable_history.{h,cc}` implements production publication without Python or
a runtime helper. It pins the existing directory, locks a no-follow regular
`.history.lock`, validates the complete canonical v3 image against compiled
state tables and executable identity, syncs an exclusive private temporary,
and links an immutable cycle/hash filename without replacement. Complete
on-disk image readback/validation precedes a separately synced, atomically
replaced `history.json`. Index directory sync and complete readback precede
bounded retention. The worker remains parked across this sequence; only
successful completion advances its target deadline and acknowledges release.
Failures exit while the worker remains parked.

The native index schema is `firesim.rolling.native.level1.v1`; its binding is
SHA-256 of the canonical complete checkpoint build identity (including runtime
manifest and executable hashes). `NativeRollingHistory` in `rolling.py` uses
the same schema, lock, immutable names and commit protocol for Python selection
and recovery. Selection returns validated pinned bytes strictly before the
causal target cycle. Existing policy-only `firesim.rolling.level1.v1` indexes
are not reinterpreted. Both APIs preserve the existing complete `.fsckpt`
representation; Level-2 `.rtlckpt` remains independent.

Old snapshots survive every failure before index commit. A visible post-rename
index failure reports `index_committed=1`, without releasing the worker.
Startup recovery validates every retained image and confirms directory sync
before reclaiming complete orphaned images. All deletion candidates validate
before any deletion. Pending partials and foreign files survive. Failed or
killed writers may temporarily leave extra files; only indexed images can be
restored. A precommit retry may reuse an exact immutable orphan. A new capture
must advance the retained target cycle; restore into a fresh history directory
when rewinding before an existing history's newest cut.

Evidence and full-path command/artifact catalogs are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m5-iteration45/`.
The loop accepts nonempty regular-file report artifacts; iteration 44's existing
run directory failed that check because a directory was listed as an artifact.
Use concrete summary/manifest files in the report, while those catalogs retain
the complete absolute paths of generated files.
The native ASan/UBSan verifier passes independent Python byte comparisons,
18 actual I/O fault boundaries, seven actual SIGKILL boundaries, 12
corrupt/special-history cases, 24 parser rejections, eight competing native
writers, and native/Python publication and selection interoperability.
It also passes replaced-directory pinning, exact immutable-orphan reuse,
conflicting-image preservation and default capability rejection.

The source-bound normal Make production executable passes five complete
capture/restore continuations, including outstanding traffic and randomized
host timing, and all 56 full-size public restore rejections. All 63 Python
tests, complete 225-case native collector, repeated parked-worker guards,
native/VCS dispatcher and harness, ordinary clean RTL VCS, full M2/M3,
native durable publication faults, eight Make/four generator rejections and
the unchanged complete iteration-44 periodic verifier pass afresh.
The independent production audit verifies 68 fresh processes, 67537280
generated-word comparisons and 85 original native-owner readbacks. Final
integrity checks confirm actual trace bytes, source bindings, plan hashes and
the complete absolute artifact catalog.

The public live-history verifier completes in
`live-history-vcs/invocation-7gypov_u/`. An independent locked observer records
live retained sets `[250000]`, `[250000,500000]`, `[500000,750001]`; it never
commits or prunes the runtime history. Each cut contains all 13507456 generated
words, 29 harness banks and 17 native owners. The complete uninterrupted run
matches every byte of the reference across 40 transaction ports through target
cycle 774628. Diagnostic copies preserve the first image after runtime pruning;
they are outside the actual two-image retained directory.

Both fresh 500000-cycle retained replays inject and detect a late external
SIGSTOP at target cycle 600041. The killed replay matches all 133389 complete
rows and every partial final-row byte. The resumed replay matches all 366116
complete continuation rows through completion. Both restore/read back every
original native byte with zero host/target edges before bootstrap. Restored
execution captures/commits new images at 600001 and 700000; both restore in
additional fresh processes with matching continuations and native readback.
All 29 public configuration/directory, six incompatible/corrupt/special-history
and early-reset restore rejections pass before any unsupported continuation.

Reproduction from the Chipyard root (source helpers in this order):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_live_history_vcs \
  --production automations/checkpoint_loop/runs/m5-iteration45/normal-make \
  --reference-production automations/checkpoint_loop/runs/m4-iteration42/normal-make-settled \
  --out automations/checkpoint_loop/runs/m5-iteration45/live-history-vcs
```

The complete command catalog is `verification-commands.json`; the regular-file
`artifact-manifest.json` records absolute paths, sizes and SHA-256s for evidence
and changed sources. Plan preservation is checked against the iteration-start
`plan-inputs.sha256`. No directory is listed as a report artifact.

The root DESSERT and Strober papers' extracted checkpoint-interval and complete
state/trace replay sections were reread using iteration 44's retained text.
Periodic overhead does not change target time. No ASIC gate-level activity,
power, formal or physical FPGA validation is claimed. The proposed M5/M6
naming correction remains only in `m5-rolling-history.md`; both plans retain
their iteration-start hashes and were not staged or edited.

Remaining M5 work: independent production host watchdog sampling with explicit
intentional-capture accounting, and an audited target progress sampler/watchdog.
The existing Python watchdog policies and external late-SIGSTOP replay detection
remain supported; they do not establish integrated runtime watchdog coverage.
