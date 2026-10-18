# Prepared heartbeat publication

Iteration 174 adds prepared publication for the buffered, unfinished
`firesim.widget.heartbeat.v1` host owner. Complete Rocket Level 1 remains
in progress, with CPU admission disabled. Clock hardware counters/latches,
MMIO transport and the calling bridge loop remain separate owners.

The v1 payload is unchanged. It binds the polling interval, partitioned/ignore
policy and complete clock MMIO configuration. State includes the signed host
epoch, sticky timeout, poll cursor, last target cycle and every buffered
cycle/signed-elapsed-time pair. The destination retains its diagnostic output
path. Live log streams, finished calls, suspended calls and poisoned calls
continue to reject explicitly. Host wall time remains diagnostic; it does not
establish target-time equivalence across a restart.

Preparation decodes and allocates all replacement sample storage and stamps the
complete destination payload. Sealing checks lifetime, native thread, generation
and consumption before accessing the owner, then compares the entire stamp.
Publication consumes the guard, swaps the sample vector and assigns four scalar
fields through allocation-free `noexcept` code. It performs no tick, time sample,
`localtime`, MMIO, output or clock advancement. Legacy load invalidates existing
candidates before its first assignment, including identical-byte loads.
The concrete owner is noncopyable and nonmovable.

These guards do not acquire process exclusion or protect arbitrary writes after
sealing. The production coordinator must retain exclusion through aggregate
publication, readback and launch. Generic aggregate loading still calls legacy
owners sequentially. Blockdev, UART, FASED and four TracerV owners still need
prepared publication; complete generated RTL/FAME/channel/harness, memory,
runtime I/O, scheduler/loop and creator-side TSI need one production coordinator
with thread/signal/descriptor/parser exclusion.

The extended `verify_heartbeat_checkpoint_vcs --prepared` checks production
heartbeat/clock code under native ASan/UBSan and fresh VCS DPI processes. The
independent Python oracle covers all sixteen cuts in three polling scenarios,
including zero interval, ignored heartbeat, repeated target cycles, sticky
timeout, 64-bit counters and negative elapsed samples. Each restore clears its
input buffer before sealing, reads back every owner byte before the first
fixture edge and compares the entire remaining MMIO/termination transcript and
complete buffered CSV. Every publication arms the next allocation to fail.
Fixture labels and substituted host time are component tests, not Rocket cuts.

Both backends pass 96 fresh continuations and complete pre-edge readbacks,
1,260 continued MMIO calls, eight malformed fresh loads and two actual polling
counter corruptions. Corruption first diverges at fixture cycle 107, before a
cycle read or termination result is acknowledged. The prepared matrix passes
904 candidate rejections, 102 preparation and 66 sealing allocation failures,
twelve fatal contract cases and two explicit unexpected-return controls.
Failed seals can retry; cancellation preserves the destination. Expired,
foreign-thread, stale and consumed candidates reject before owner access.
Eight rehashed offline forged-receipt controls exercise the evidence auditor;
they are not additional native or CPU executions.

Selected native/VCS receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/heartbeat-prepared/native-yun3bzvd/summary.json`.
Full-byte/MMIO/original-command audit:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/heartbeat-independent-audit.json`.
Native executables, source snapshots, captured images, readbacks, traces and
original commands remain in that invocation. Exact-recipe integration,
preserved regressions and executable commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Complete Rocket Level-1 continuation remains pending; independent Level 2
stays separate. BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA
validation and ASIC power remain outside scope.
