# Prepared base simulation lifecycle publication

Iteration 173 adds prepared publication for `runtime/simulation/base`, implemented
by `simulation_t::base_checkpoint_t`. This owner is separate from the concrete
FireSim driver's `runtime/simulation` adapter. Complete Rocket Level 1 remains
in progress, with CPU admission disabled.

The existing `firesim.simulation.base.v1` source payload is unchanged. It binds
zero/load-memory and fingerprint configuration, incremental dispatch capability,
target name, effective load-memory path and the ordered widget IDs/schemas. Its
state is the running lifecycle marker, completed-step flag, wall-clock baseline
and initial host-cycle count. Source capture requires an idle returned operation
of an unfinished running flow, without finalization counters or fingerprint-only
execution. A terminal returned step remains capturable before finalization.
Wall-clock baselines are retained for reporting; elapsed wall time across a
restart does not establish target-time determinism.

`prepare_checkpoint_publication` validates the complete source and decodes its
three scalar fields into candidate-owned storage. It independently stamps the
fresh destination, since a constructed flow cannot call running-source save.
The stamp covers the full effective configuration/registry plus `flow_phase`,
`flow_on_stack`, `flow_poisoned`, `base_checkpoint_loaded`, `run_done`, both time
baselines, both host-cycle optional flags and values, and `end_tcycle`.
The call guard rejects an active or poisoned synchronous operation.

Sealing checks lifetime, native thread, generation and consumption before owner
access, then compares the complete destination stamp. A failed or cancelled
preparation/seal leaves the destination fresh. Publication first consumes the
sealed guard and then assigns the start baselines, completed-step flag, running
phase and loaded flag. It is allocation-free `noexcept`; no initialization,
reset, time sample, MMIO, output or concrete-driver operation occurs. Legacy load
invalidates outstanding candidates before assignment. Destination lifetime and
thread checks do not acquire exclusion: the coordinator must retain exclusion
from sealing through aggregate readback and launch.

`verify_base_publication_vcs` compiles the production base-flow implementation,
master/clock/loadmem/registry code and a separate MMIO/driver/bridge fixture.
The native backend uses ASan/UBSan; the VCS backend loads at time zero, reads back
the entire source payload before its first fixture edge, and continues in a new
process. Its independent Python byte/MMIO oracle covers success, error and
timeout at each of four returned steps, including the terminal step. The
`--legacy` variant preserves the original load path. Fixture steps are not
Rocket target-cycle labels.

The prepared matrix passes 24 fresh continuations, 24 complete pre-edge
readbacks, 264 continued MMIO calls, eight fresh malformed-image rejections and
four actual first-boundary `run_done` corruptions across the two backends.
Premature completion first calls finalization instead of the next step; a false
terminal flag first attempts another step instead of finalization. Neither
fault acknowledges a divergent operation or issues MMIO at that boundary.
These are component images and faults, not CPU `.fsckpt` parser acceptance.

The rejection matrix passes 608 checks per backend, including every truncated
prefix, configuration/reserved-bit corruption, incompatible registry/flags,
active/poisoned/completed destinations, cancellation, expiration, foreign-thread
sealing and stale/consumed candidates. Each backend exhaustively injects 32
preparation and 16 sealing allocation failures; failed sealing permits retry.
Valid publication runs with the next allocation armed to fail. Twelve fatal
contract cases exit 86 after verifying unchanged destination state. Two explicit
unexpected-return controls exit 88, keeping a returning implementation from
passing the fatal-test harness. Eight rehashed offline forged-receipt controls
also reject; these exercise evidence auditing, not additional CPU executions.

Selected prepared evidence:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/base-prepared/invocation-8xtddnom/summary.json`.
Independent original-command and full-byte audit:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/base-independent-audit.json`.
Source snapshots, executables, original commands, complete owner bytes and logs
remain in that invocation. Reproduction and the remaining owner inventory are
recorded in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Heartbeat, UART, blockdev, FASED and all four TracerV owners still require
prepared publication. Full generated RTL/FAME/channel/harness state, memory,
runtime I/O, scheduler/loop and creator-side TSI must join one production
coordinator with thread/signal/descriptor/parser exclusion. The existing generic
aggregate still loads legacy owners sequentially. This base adapter supplies
one prerequisite and enables neither CPU admission nor whole-runtime restore.
Independent Rocket Level 2 remains separate. BOOM/Saturn are pending;
standalone Shuttle, physical FPGA validation and ASIC power remain outside scope.
