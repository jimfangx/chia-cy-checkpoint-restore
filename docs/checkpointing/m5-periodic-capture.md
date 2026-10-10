# M5 repeated live capture — iteration 44

This increment connects repeated completed-operation dispatch to live Level-1
collection in the audited FCFS/FASED VCS profile. It uses verification controls
`+test-live-periodic=PREFIX +test-live-interval=N`; `N` is an interval in actual
manifested FASED target cycles. These controls use the ordinary production
harness callback and complete native/VPI collector. Each due cut atomically
publishes `PREFIX.<actual-target-cycle>.fsckpt`. The adapter does not prune or
commit a retained-history index, and does not enable public periodic options.

The driver remains parked during sampling, collection and publication. Every
callback requires a new acknowledgment, including polls without a due deadline.
A previous callback's acknowledgment cannot release a later cut. Consecutive
software-only operations can park again without an intervening MMIO yield;
the dispatcher and harness loop service those callbacks without extra native
or target edges. Existing single-operation public capture remains supported.

The C++ target schedule has an explicit origin, advances deadlines only after
successful publication, skips crossed deadlines without inventing snapshots,
and cannot wrap at the unsigned 64-bit limit. Restored runs initialize a new
policy with the restored target cycle. Policy and polling state are host
configuration, independent of the Level-1 serialized target/runtime state.

The FASED cycle counter resets during the initial target reset pulse. Ordinary
startup waits for the compiled reset-pulse `doneInit`/`pulseLength` state and
FASED reset input to certify completion before sampling deadlines from origin
zero. Later resets/regressions reject. Periodic capture from a restore during
the initial target reset is explicitly unsupported. Unknown values, changed
inventory/geometry or an unsupported topology also reject.

Polling checks the host clock and the compiled generated clock-gate outputs.
Every actual snapshot still checks the complete generated/harness clock
inventory, all 13,507,456 generated words, 29 harness banks and 17 native owners,
including complete readback and stability checks. The optional runtime identity
observers hash loaded ELFs at due full captures and finalization rather than
every poll. Bootstrap refresh assertions now apply until bootstrap completes;
subsequent restored-run capture refreshes remain permitted.

Verification artifacts and command catalog are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m5-iteration44/`.
The initial wrong build-path diagnostic, startup counter-regression rejection
and superseded build/runtime trials are preserved. Only the final source-bound
`normal-make-polling` and `periodic-vcs-polling` evidence can authorize the
periodic implementation. Logs and large artifacts are not stored in this doc.

The periodic verifier runs the complete 10,000-transaction workload, compares
all 40 transaction ports against an independently completed reference with
identical generated RTL, validates each due complete image, admits live cuts to
the existing retained-history API, and selects a strictly earlier checkpoint.
It injects/detects external late SIGSTOP stalls in fresh retained replays, checks
native pre-edge readback and zero-edge bootstrap, captures again during a
restored continuation and restores each recaptured image in another process.
History admission in this verifier happens after the live run, and watchdog
sampling is external; neither is a production runtime integration claim.

The final verifier completed successfully in `periodic-vcs-polling/invocation-k7cie810/`.
It revalidated the already completed, identical initial VCS run in
`invocation-r49_phbh/periodic/` after correcting a verifier metadata lookup:
host sample is the `cut/host_sample` record, not a top-level container field.
The executable, reference and complete initial images were preserved; every
remaining test ran afresh. Initial cuts are 250000, 500000 and 750001, with
the last two retained. Both fresh 500000-cycle replays detect an external stall
after 600000; the resumed replay matches all 366,116 complete 40-port samples.
The killed replay matches every available byte, including its partial final
row. Restored execution recaptures at 600001 and 700000, and both images replay
in fresh processes with exact native pre-edge readback and zero-edge bootstrap.
All 18 periodic argument rejections and the early-reset restore rejection pass.

The two root papers were read for their checkpoint-interval overhead, complete
memory state and cycle-by-cycle replay requirements. Local text extraction and
reader-setup diagnostics are under this iteration's run directory. Their finite
semantic replay and ASIC energy workflows remain separate from this Level-1
whole-runtime continuation. No RTL switching activity is used as ASIC activity.

Remaining M5 work: public periodic configuration; live retained-history
commit/validation/retention before worker release; independent production host
watchdog sampling with intentional-capture accounting; and an audited target
progress owner/sampler. Keep Level-1 and Level-2 independent. No physical FPGA,
formal or ASIC gate-level activity validation is claimed. The existing proposed
M5/M6 milestone naming correction remains in `m5-rolling-history.md`; both plans
remain read-only and unchanged from this iteration's initial hashes.
