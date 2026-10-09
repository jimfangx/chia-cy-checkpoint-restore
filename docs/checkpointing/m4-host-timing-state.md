# M4 host timing owner — iteration 14

M4 remains in progress. The production metasim host-delay generator now owns
its full PRNG and pending delay progress explicitly. Native ASan/UBSan and
fresh VCS DPI processes pass component continuation against an independent
Python MT19937-64 oracle. This does not establish a coherent FireSim runtime
cut or fresh-process target-cycle continuation. No external dependency is missing.

`emul/host_timing.{h,cc}` (under `sims/firesim/sim/midas/src/main/cc/`) implements
`firesim.host-timing.mt19937-64.libstdcxx.v1`. Its fixed 2,560-byte little-endian
payload contains magic/version, maximum host delay, full unsigned seed, most
recently selected delay, remaining ticks, engine geometry, all 312 engine words
and the next-word index. The libstdc++ stream adapter supplies engine words;
C++ object layouts, pointers and locale-dependent textual payloads are not
serialized. The outer coordinator must bind this component to its complete
owner manifest, integrity and executable/library build.

`simif_emul_t::checkpoint_host_timing_owner()` supplies stable identity
`runtime/host-timing`. `advance_target()` now calls this owner's synchronous
delay loop. Each call draws once using the existing
`std::mt19937_64(seed)() % maximum_delay + 1` sequence, and commits each pending
tick only after `do_tick()` returns. The former stack-local tick count/index
are explicit fields. The separate component `begin_delay()`/`complete_tick()`
interface exposes resumable boundaries, and a loaded pending delay resumes
without another random draw. These methods do not implement a driver state
machine or issue RTL edges themselves.

Checkpoint save/validate/load, recursive timing operations and tick commits
reject during the synchronous callback, including when `do_tick()` is suspended
at a thread handoff. A callback exception poisons the owner: subsequent capture,
load or advancement rejects because the interrupted tick has no certified
commit boundary. The active/failure flags are boundary guards, not serialized
thread or C++ stack state. Access requires external synchronization that parks
both contexts; the owner is not a concurrent freeze mechanism.

Load constructs and validates a complete replacement before changing any
field. Wrong size/magic/version, configuration/seed mismatch, invalid delay
progress, engine geometry/index, zero engine state, inconsistent initial
state, truncation and trailing bytes fail without mutation. Host delay arguments
now require unsigned decimal values and a positive maximum at most `INT_MAX`;
seed parsing supports the full 64-bit unsigned range. Invalid arguments fail
before partition setup, rather than reaching modulo-zero/negative-delay behavior.

`verify_host_timing_checkpoint_vcs` compares every begin/commit and every
checkpoint/final engine word with an independent Python recurrence/tempering
oracle. Four maximum-delay/seed configurations include the default, unsigned
high-bit seeds and `UINT64_MAX`. Seventeen cuts cover initial, selected,
partially consumed and completed delays, including immediately before/after
engine wraparound. Native ASan/UBSan and fresh VCS DPI processes pass **136
continuations / 861,432 component operations**. Every load reserializes
identically before the first component edge and at completion. Each backend
and configuration rejects **2,574** malformed payloads through validate/load
without mutation and separately checks incompatible owners, strict arguments,
maximum configuration, synchronous/reentrant/failing callbacks and 1,500
draws against the former production loop. Thirty-two fresh malformed restore
processes exit nonzero before opening a trace/advancing a component edge.

Reproduce from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_host_timing_checkpoint_vcs \
  --out automations/checkpoint_loop/runs/m4-iteration14/host-timing-owner
```

All existing regressions pass: 24 Python/20 Scala tests, compiler codec,
corruption and emitted-memory coverage; scheduler 36 continuations/2,090
operations; AXI/memory 104 continuations/7,168 edges and memory-only 64/1,704;
all 539 generated InventoryFixture words; full M2 (five fresh cases/108 samples/
1,404 comparisons and negatives); full M3 (six captures/547 stalls/five
semantic and 242 transfer replay samples/eight invalid reads); ordinary clean
RTL VCS; and GCD metasim at 12 target cycles. Four explicit timing/seed GCD
runs also pass at 12 target cycles, and six malformed arguments fail before
initialization. The complete 10,000-transaction FCFS fuzzer passes at 774,628
target cycles; the three complete outstanding-traffic captures retain hash
`b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`.
All full checkpoint requests reject unsupported `widget/0` and publish no
incomplete checkpoint. Symbol checks confirm the new timing and existing
scheduler hooks in all four actual reused metasim executables.

The remaining runtime inventory in [m4-mmio-runtime.md](m4-mmio-runtime.md)
and scheduler qualifications in [m4-scheduler-state.md](m4-scheduler-state.md)
still apply. PRNG/delay fields now have an adapter; synchronous driver stacks,
MMIO/stream destination buffers, driver/main-loop phases, harness delayed AXI
records and clock/reset/DPI phase, thread handoff, stream engines, concrete
driver state and external QSFP/partition state still require audits and a
coherent freeze. No concrete driver has been declared checkpointable. Full
requests must continue to fail closed and publish no incomplete `.fsckpt`.

The actual FCFS regression uses `src/main/cc/fasedtests/fasedtests_top.cc`.
Its scheduler credit issuance, pending nonblocking PeekPoke step, bridge tick
iteration and `done` detection need explicit resumable phases; scheduler
issued cycles cannot substitute for completed RTL progress. Its configuration
map, final event checks and optional profiling callback/FASED owners also need
audits. The separate `midasexamples/TestHarness.h` still has its own test PRNG,
`t`, `pass`, `log` and `fail_t` plus concrete `run_test()` continuation state;
this new metasim timing owner does not cover those fields.

Next: make one production driver/main-loop path resumable with explicit
initialization/run/finish boundaries, then freeze both contexts at a settled
harness phase without draining target traffic. Capture generated RTL, all
functional memory/AXI queues, timing, scheduler/callback and driver owners as
one manifest/build-bound `.fsckpt`. Prevalidate every owner and RTL handle in a
fresh VCS metasim before loading or advancing target time; compare outputs
and transaction timing with outstanding target memory traffic. Pending delay
component restoration alone cannot restore a suspended MMIO caller.

Commands, results and diagnostic artifacts are under
`automations/checkpoint_loop/runs/m4-iteration14/`. Every VCS shell sources both
repository environments followed by `vcs-env.sh` last; Y-2026.03-SP1, `-full64`,
GCC/G++ 13 and `VCS_FLAGS=-Mupdate` on reused Make builds are retained.
The relevant DESSERT deterministic target-cycle replay and Strober exact
snapshot/I/O replay sections were reread from the root-paper text extractions
under `runs/m2-iteration7/`. No plan correction is proposed. Plans, conda files
and PDFs are preserved without staging, commit, reset or clean. Level-1 owner
state remains independent of Level-2 semantic checkpoints. No full Level-1,
physical FPGA, formal or ASIC gate-level activity/power acceptance is claimed.
