# Joint metasim runtime I/O restoration

Iteration 167 adds a split sealing/nonthrowing publication API to this
transaction; see [runtime-io-sealed-publication.md](runtime-io-sealed-publication.md).
The account below retains the iteration-166 API and evidence. The complete
simulator coordinator and production process exclusion remain pending.

Iteration 166 adds a prepared component transaction to production
`simif_emul_t`. Its ordered membership is:

| Owner | State |
| --- | --- |
| `runtime/mmio-io` | Returned, unpoisoned control read/write caller and complete control geometry |
| `runtime/mmio` | Complete control AXI queues, response buffers, dummy beat and in-flight flags |
| `runtime/cpu-managed-stream-io` | Returned, unpoisoned stream caller and complete DMA geometry, when configured |
| `runtime/cpu-managed-axi4` | Complete DMA AXI queues, response buffers, dummy beat and in-flight flags, when configured |
| `runtime/host-timing` | Full MT19937-64 engine and explicit total/remaining delay, seed and maximum delay |

`save_checkpoint_io` returns named, schema-bound component payloads.
`prepare_checkpoint_io` checks the exact ordered owner membership and validates
every payload before privately constructing replacement AXI/timing owners. It
records the complete destination image. Preparing or abandoning a candidate
publishes nothing. `publish_checkpoint_io` checks native thread, destination
lifetime and single-use ownership, then reads back the complete destination
again. A changed destination, suspended/interrupted call, malformed image or
allocation failure rejects before any member changes. After that recheck, the
only operations are nonthrowing queue/vector/PRNG/scalar swaps and marking the
candidate consumed. Queue and PRNG swap guarantees have compile-time checks.
Returned-call validation never clears a poisoned native lifetime.

A retained identity token prevents a candidate from accepting a different
simulator constructed at the same recycled address. Candidates retain their
own parsed replacement state, independently of the input buffers. Their
component data does not require creator-affine destruction.

The caller must hold both simulator contexts and exclude other users for the
whole operation. This API does not supply production process exclusion or the
full CPU transaction. Functional memory, generated RTL/FAME/channel state,
harness latches and all bridge/driver owners remain separate. The outer image
must bind executable and library identity. FPGA-managed streams and partition
QSFP explicitly reject. Both CPU-managed and no-stream component configurations
are tested; this does not extend the existing FCFS aggregate membership.
Complete Rocket Level-1 admission remains disabled.

The new native ASan/UBSan and time-zero VCS DPI matrix restores fresh processes
with queued, in-flight and response-buffered traffic on both AXI transports.
Each destination reads back every component before any edge, then consumes all
responses and compares the complete final image. A separate Python byte oracle
constructs every owner payload, including write bytes/strobes/last flags,
responses and the complete MT19937-64 state with a pending delay.

Invalid cases cover every missing/duplicate/unknown/schema-mismatched/trailing/
empty/bad-magic member, reordered membership, incompatible control/DMA/timing
configuration, foreign destination/thread, recycled destination address,
changed destinations in each stateful member and repeated publication. Native
and VCS tests inject C++ allocation failures at every successive preparation and
publication allocation through the first uninjected success, checking the
entire destination after each failure. libstdc++ may convert an injected
allocation exception into a stream parse error; both must leave the entire
destination unchanged. The original production blocking-MMIO fixture now uses
the same five-owner transaction for fresh restores and checks all three group
hooks at every suspended read/write handoff, alongside the existing per-owner
and nested-stream guards. Its independent AXI/timing oracle is preserved.
Joined suspended-call checks currently cover control MMIO and nested stream
count reads. Production DMA calls retain their separate component guard tests;
extend the joined-hook coverage through their suspended stacks during complete
CPU coordination.

Exact receipts, executable native commands and results are maintained in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/`.
The initial test attempts remain diagnostic: one needed to account for
libstdc++ allocation-to-parse error translation, and another incorrectly
required more than 100 publication allocations for the smaller no-DMA group.
The corrected matrix still sweeps every allocation point. Earlier broader
runs overlapping that test correction are superseded by the complete final
suite under `final/`; no check was cancelled.

Next: integrate this component transaction with sealed creator-side TSI
publication and all other simulator owners, under production thread/signal/
descriptor/parser exclusion, before admitting complete CPU restore. Level 2
stays independent. BOOM/Saturn remain pending; standalone Shuttle, physical
FPGA validation and ASIC power are outside this increment.


## Remaining Rocket coordinator integration

A source-bound structural audit uses the final exact-recipe header and manifest:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/cpu-integration-audit.json`.
It is a recovery inventory, not CPU continuation evidence. The regular native
build has 11,464 generated state entries / 445,838 emitted storage words. Its
header specifies one functional-memory channel, control `{12,32,32}`, DMA
`{16,64,512}`, no FPGA-managed stream and zero QSFP channels. Its generated
manifest must be bound separately from the retained Level-2 semantic map.

`entry.cc` includes the three generated constructor passes in core, managed
stream, then bridge order. `firesim_top_t` adds heartbeat afterward. The actual
registry order is:

| Owner | Concrete class |
| --- | --- |
| `widget/0` | `master_t` |
| `widget/1` | `loadmem_t` |
| `widget/2` | `CPUManagedStreamWidget` |
| `widget/3` | `peek_poke_t` |
| `widget/4` | `reset_pulse_t` |
| `widget/5` | `blockdev_t` |
| `widget/6` | `uart_t` |
| `widget/7` | `FASEDMemoryTimingModel` |
| `widget/8` through `widget/11` | Four `tracerv_t` instances |
| `widget/12` | `tsibridge_t` |
| `widget/13` | `clockmodule_t` |
| `widget/14` | `heartbeat_t` |

The concrete FireSim driver already has incremental dispatch and an adapter
with schema `firesim.simulation.bridge-driver.v1`. Its inventory includes the
base lifecycle, scheduler and `runtime/simulation/firesim-run-loop`. Avoid
reimplementing these existing adapters based on the older iteration-82 audit
retained in the matrix history. Anonymous profiling and diagnostic callbacks
remain unsupported. A concrete adapter/schema does not establish joint
ownership or a complete CPU restore.

Three current `simif_emul_t` admission sites still reject CPU-managed streams:
`require_restored_destination`, `begin_restored_load` and
`require_settled_checkpoint_capture`. The new I/O component transaction changes
none of those guards. `metasim_build.py` and `Makefrag-checkpoint` still admit
only the FCFS profile; that profile requires four memory channels and excludes
managed streams. Its native list in `durable_restore_entry.cc` omits both
returned-call owners, and `aggregate_restore_t::commit_native` still invokes
individual allocating `load_checkpoint` hooks sequentially. These are concrete
integration points, not permission to relax the FCFS whitelist or bypass guards.

The restricted TSI path prepares a private provider/control pair, seals it on
its creator, then publishes through `publish_sealed() noexcept`. It retains
empty generic `checkpoint_schema` admission. Its constructor rollback assumes
exclusive descriptor and getopt access; its component guards do not supply a
VCS-wide thread/process policy. The creator mailbox already supports retained
resources, a prepared continuation, retained publication guards, creator-side
publication/readback and same-thread cancellation/destruction. Reuse those
mechanisms under an actual production policy; keep foreign access and ordinary
unowned sessions rejected.

The complete transaction must prepare all generated/harness, functional memory,
I/O, widget, driver and compatibility state before any mutation. The I/O
publication recheck can allocate: it cannot be inserted after TSI or another
owner has already published. Establish a complete commit order or extend the
sealing protocol so every remaining throwing check/allocation precedes the
first publication. Hold creator and controller exclusions through every owner
readback and pre-edge RTL settlement. A post-publication invariant failure must
keep the destination from advancing. This remains unimplemented; independent
component mutexes and a sequence of ordinary owner loads cannot supply it.

Retain configuration-specific external-state checks: buffered UART input/output,
buffered TracerV/heartbeat, private-memory/disconnected blockdev, independently audited FASED
FRFCFS/LLC configuration and supported restricted TSI metadata/device/syscall
modes. Native ordinary/default controls remain execution regressions; their
success does not certify checkpoint ownership of ordinary files, live stdin,
signals or unsupported HTIF sessions. Fresh complete CPU continuation still
requires all four active-workload cuts, independent whole-state readback,
atomic invalid-image/build/owner rejection and first-boundary corruption checks.
Level 2 remains independent.


The same final exact-recipe binary also retains three fresh native denials:
preflight rejects `widget/12` (TSI) before driver creation; public capture and
restore reject the missing durable capability before platform construction.
No checkpoint image is created. Preflight does open the ordinary TracerV and
FASED constructor files: all four trace files contain only their exact clock
header, with no retired instructions. The initial denial test incorrectly
expected no constructor trace files; its log is retained and all three cases
were rerun with the correct phase-specific checks. These are unsupported CPU
capability/owner denials, **not malformed CPU-image parser validation**.
Receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/cpu-denial-verified/invocation-el8sj3ig/summary.json`.

Run both recovery checks from the Chipyard root:

```sh
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration166/audit-cpu-integration.py'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration166/verify-cpu-denial.py'
```
