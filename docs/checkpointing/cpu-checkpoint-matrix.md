# CPU checkpoint matrix

Current milestone: M11 Rocket, iteration 98. Level-1 and Level-2 acceptance
remain **in_progress**. No CPU checkpoint continuation or clean CPU RTL replay
has passed. Physical FPGA validation, standalone Shuttle and ASIC power are
outside this matrix. The verified FCFS evidence remains in its existing docs.

| Family / existing recipe | Level 1 | Level 2 | Workload evidence |
| --- | --- | --- | --- |
| Rocket / `firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3` | in_progress: generated RTL inventory audited; TracerV and FireSim driver/termination-loop continuations pass; production TSI read and all four load-memory queues pass fresh component restores; complete HTIF/context/serial/bridge ownership and fresh CPU continuation pending | in_progress: complete ChipTop inventory/readback retained; explicit event-phase image/replay contract passes ordinary RTL component checks; coherent metasim CPU capture/replay pending | Both complete current four-hart default/buffered controls pass at C=3,329,794; all full traces and workload/store labels match; CPU checkpoint cuts remain pending |
| BOOM / `firesim_boom_singlecore_no_nic_l2_llc4mb_ddr3` | pending | pending | No execution claimed |
| Shuttle + Saturn / `firesim_saturn_GENV256D128_shuttle_singlecore_no_nic_l2_llc4mb_ddr3` | pending | pending | No vector execution claimed |

## Rocket settings and artifacts

Read the current recipe YAML on every build; `tools.checkpoint_formats.cpu_recipe`
prepares source-hashed commands without enabling an unaudited checkpoint profile.
The exact settings are:

| Setting | Value |
| --- | --- |
| PLATFORM | `f2` |
| TARGET_PROJECT | `firesim` |
| TARGET_PROJECT_MAKEFRAG | `../../generators/firechip/chip/src/main/makefrag/firesim` |
| DESIGN | `FireSim` |
| TARGET_CONFIG | `WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig` |
| PLATFORM_CONFIG | `WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config` |

The manager resolves the recipe's relative Makefrag from `sims/firesim`.
Direct `make -C sims/firesim/sim` uses the same directory's absolute path.
The recipe also specifies frequency 140 MHz and TIMING build strategy; these
are retained in the recipe record, with no FPGA implementation invoked.
VCS uses Y-2026.03-SP1, `-full64`, `VCS_FLAGS=-Mupdate`, system GCC/G++ 13,
and the sourced Conda library/include directories. No Conda files are edited.

## Iteration 98: complete production TSI load-memory queues

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration98/`.
No CPU checkpoint acceptance is claimed. See
[tsi-loadmem-queues.md](tsi-loadmem-queues.md) for the payload contract and
remaining parent-state owners. The read-operation schema, FCFS profile and
independent Level-2 schemas are preserved.

`firesim.tsi.loadmem-queues.v1` owns all four production queues and the active
write request/consumed-byte cursor. Restore validates complete write-data
ownership, request arithmetic, configuration, queue lengths and response widths
before allocating/committing all candidate queues. No host I/O, HTIF work or
dequeue occurs during load/readback. The actual TSI delegates all queue accesses
to this owner; const component inspection does not enable aggregate restore.

Selected evidence: `loadmem-queues/invocation-isd5rmud/summary.json`.
All 340 fresh sanitizer/VCS component restores pass for 4/8/64/1,024/4,096-byte
writes/reads at every completed-call cut. The independent oracle compares 5,950
complete state readbacks and 5,610 subsequent records, including overlapping
read/write queues, zero/full/high-bit responses, FIFO order, address crossings
and byte-granular partial write drains. Each backend passes 134 atomic checks;
42 fresh malformed/missing/truncated/incompatible/incomplete image processes
reject before mutation/continuation/publication. Actual valid write-data
corruption first differs at fixture C=114 / operation 14: `DATA 1 00` versus
`DATA 1 01`, with zero resumed operations acknowledged in either backend.
These labels are host fixture labels, not Rocket target cycles.

Actual installed-FESVR evidence:
`real-fesvr-current/invocation-b_yth_n4/summary.json`. Both native/VCS ELF-load
runs preserve all fourteen suspended read-operation images and match 22 complete
queue images, including one-byte write drain and pending response cuts. All 22
actual queue images additionally restore in fresh native/VCS processes and match
their entire component continuations in `real-queue-restores/summary.json`.
HTIF itself is not restored. The ELF/library hashes remain
`45a7f219e68180b49d557cad0c10277277af843c16e4a5e58dc8fb7fb6cb77be` /
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
Historical iteration-96 read-only evidence still audits under its original scope.

The exact-recipe rebuild binds the new queue header and save/validate/load
symbols, with all 59 native translation units unchanged
(`rocket-queue-linkage-audit.json`). Both full four-hart default/buffered controls
pass at C=3,329,794 in `rocket-controls/invocation-evqkntda/summary.json`.
All four complete traces per mode (37,582,346 / 49,976,156 / 50,391,641 /
50,189,006 bytes) and all workload/store labels match the uninterrupted reference.
The self-checking four-hart workload hash remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Exact settings, source/workload hashes, original native argv/environment and
process/exit records are bound by the invocation's `rocket-build-identity.json`
and retained commands. These runs are CPU controls, not checkpoint continuations.
A fresh ordinary Rocket RTL diagnostic probe reads all 318,637 words / seven
clocks before edges in `native-rocket-probe-mW61Q6/run.log`. This remains a
storage probe, not a workload image.
Current complete CPU preflight/capture/restore requests reject unsupported TSI
or absent durable capability before run/publication in
`cpu-request-rejections-final/summary.json`. Two earlier rejection-checker
wording mistakes are retained as failures; the final three checks actually pass.

All 245 Python tests and all eight preserved native checks pass in
`native-regressions/invocation-1xwnfhz9/summary.json`; its independent audit seals
5,113 artifacts and 695 original source bindings. The 260 prior read-owner fresh
continuations pass again in `loadmem-read/invocation-zm4hqn4f/summary.json`.
Production transport retains all 1,012 requests / 566,096 records, 32 invalid
requests before I/O, four callback-unwind checks and four actual bridge runs in
`loadmem-transport/invocation-hff1svl3/summary.json`. Both private repeated-beat /
response-bit fault backends still detect their first unacknowledged wrong word in
`loadmem-transport-faults/invocation-alr14lc9/summary.json`. Four independent
retained complete inventory/clock/memory/policy/TracerV audits pass.

Complete HTIF/context/serial/device/idle/reset/bridge ownership and cross-owner
validation remain required. Both independent checkpoint levels at early,
warmed-cache, outstanding-memory and late four-hart cuts remain pending.
No dependency is missing. BOOM/Saturn remain pending; physical FPGA and ASIC
work remain deferred. Existing iteration-97 controller commits were published
FireSim first (`1bdd959cc68d4f31964d06841c6002c7fc62032c`), then Chipyard
(`db5af10d786b231fa512d45429e2cb781b55819b`); independently queried remote tips
match. Local read-only tracking-ref diagnostics are retained. No local commit,
staging or protected-input edit was performed.

All created run paths are enumerated in `artifact-manifest.json`; original
native artifacts/build inputs are sealed in `native-input-archives.json`.
Exact executed native commands and fresh-output rechecks are recorded in
`verification-commands-native.json`; both native/VCS command forms are themselves
tested in `executable-native-command-checks.json`. Parent HTIF/context remains
explicitly unsupported. Plans remain read-only.

Executable native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_loadmem_queues_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration98/queue-recheck
python -m tools.checkpoint_formats.tests.verify_loadmem_queues_checkpoint_vcs --audit automations/checkpoint_loop/runs/m11-iteration98/loadmem-queues/invocation-isd5rmud/summary.json
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs --out automations/checkpoint_loop/runs/m11-iteration98/fesvr-recheck
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs --audit automations/checkpoint_loop/runs/m11-iteration98/real-fesvr-current/invocation-b_yth_n4/summary.json
python -m tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration98/read-recheck
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration98/native-regressions/invocation-1xwnfhz9/summary.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration98/rocket-controls/invocation-evqkntda/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration98/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration98/rocket-controls/invocation-evqkntda/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

## Iteration 97: production multi-beat TSI read transport

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration97/`.
No CPU checkpoint acceptance is claimed. See
[tsi-loadmem-transport.md](tsi-loadmem-transport.md) for the transport contract
and the independently pending state owners.

The production TSI bridge now advances translated read addresses across beats
and owns its GMP export destination and temporary value through exception
cleanup. Narrow requests select their actual lanes within aligned host-memory
beats. Whole-request validation rejects invalid sizes/alignment/beat widths,
address wrap and signed-offset underflow/overflow before MMIO or response
publication. This fixes the previously recorded repeated-first-beat bug and
export allocation leak; it introduces no aggregate TSI checkpoint schema.

Selected immutable component evidence:
`loadmem-transport-final/invocation-dd0p5ayx/summary.json`. All 1,012 native/
VCS requests and 566,096 independently expanded MMIO/response records match.
Requests cover 4/8/12/64/128/1,024/4,096 bytes, 1/2/4/16-word beats, first/last
lane starts, zero/sparse/full-bit words, signed offsets, crossings of the low
32-bit address boundary and valid unsigned/`INT64_MIN` boundaries. Thirty-two
malformed requests reject before I/O; four injected response/platform failures
exercise scoped cleanup in sanitizer/native and VCS runs. Four actual public
TSI bridge runs use the installed FESVR archive and original partial-write ELF;
all complete MMIO and serial transcripts match, including a two-beat read,
eight merged bytes, original aligned writes and six reset words. The integration
ELF hash remains `45a7f219e68180b49d557cad0c10277277af843c16e4a5e58dc8fb7fb6cb77be`;
the FESVR library hash remains
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
These are host transport runs, not CPU execution/checkpoint cuts.

Selected native/VCS fault evidence:
`loadmem-transport-faults-current/invocation-ea5fqt9a/summary.json`. Private
header mutations reproduce the original repeated beat and flip a real response
bit. All four processes reject at the first wrong response, with no wrong-word
acknowledgement or subsequent FESVR work. The repeated-beat fault first differs
at response word 1 / host address 4,294,967,284, expected 1,092,632,414 versus
actual zero, with one word acknowledged. The bit flip differs at response word
0 / host address 4,294,967,280, expected zero versus one, with zero words
acknowledged. These response labels are not target-cycle or post-restore
corruption evidence. Native failure status is propagated explicitly through DPI;
VCS's zero process exit for `$fatal` is retained as an initial rejected check.

The exact-recipe rebuild binds the new helper and retains all 59 translation
units (`rocket-tsi-transport-integration-audit.json`). Both complete default/
buffered four-hart controls pass at C=3,329,794 in
`rocket-controls/invocation-mvyq_wmu/summary.json`. All four full instruction
traces per mode (37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes) and
all workload/store labels match the uninterrupted reference. These are CPU
controls, not CPU checkpoint cuts. The self-checking four-hart workload hash
is `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Source/workload hashes and unchanged exact recipe settings are bound by
`rocket-build-identity.json` and the invocation record. The native build and
all command/environment/exit records are retained with their original paths.
Fresh ordinary Rocket RTL VCS reads all 318,637 words / seven clocks before
edges in `native-rocket-probe-*/run.log`; this is a diagnostic storage probe,
not a CPU image or captured CPU trace. Current CPU preflight/capture/restore
still reject unsupported TSI or missing durable capability before execution
and file publication (`cpu-request-rejections/summary.json`).

All 245 Python tests and eight final native regressions pass in
`native-regressions-current/invocation-u3d8wjhm/summary.json`; its independent
audit preserves 5,110 artifacts and 692 source bindings. The initial full
suite rejected a concurrent fixture source change; the entire final suite ran
again against the final sources. Retained complete inventory, clocks,
memory/policy, TracerV, driver, read-owner and real-FESVR audits pass. Earlier
link, argument, unsigned fixture-offset and VCS-exit diagnostics are preserved
in `failure-ledger.json`.
Both required checkpoint levels at early, warmed-cache, outstanding-memory and
late four-hart cuts remain pending, including complete HTIF/context/queue/device
ownership and coherent generated/semantic capture. BOOM/Saturn remain pending;
physical FPGA/ASIC work remains deferred. No dependency is missing.

Complete paths and immutable source/artifact bindings are recorded in
`artifact-manifest.json` and `native-input-archives.json`; both final retention
audits pass all 12,876 original bindings. The inherited saved probe command had
an escaping error; the original catalog is preserved, and the corrected command
is tested in a fresh native process. Its command/readback and original evidence
are additionally sealed in `native-input-archives-v2.json`. Exact executed native
argv, fresh process results and independently runnable checks are recorded in
`verification-commands-native.json` and each selected invocation's command records.

Executable native commands from the Chipyard root (every nested VCS build/run
also sources the pinned helper last):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_vcs --out automations/checkpoint_loop/runs/m11-iteration97/transport-recheck
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_faults_vcs --out automations/checkpoint_loop/runs/m11-iteration97/transport-faults-recheck
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_vcs --audit automations/checkpoint_loop/runs/m11-iteration97/loadmem-transport-final/invocation-dd0p5ayx/summary.json
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_faults_vcs --audit automations/checkpoint_loop/runs/m11-iteration97/loadmem-transport-faults-current/invocation-ea5fqt9a/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration97/native-regressions-current/invocation-u3d8wjhm/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration97/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration97/rocket-controls/invocation-mvyq_wmu/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

## Iteration 96: explicit production TSI load-memory read operation

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration96/`.
No CPU checkpoint acceptance is claimed.

The production `firesim_tsi_t::load_mem_read` now uses the pointer-free
`firesim.tsi.loadmem-read.v1` operation owner. It owns drain/issue/response/
complete progress, address/length and every consumed response word. Save/load
does not issue requests or dequeue responses. Entire-candidate validation and
response-capacity allocation precede mutation. Configuration, phase, lengths,
alignment, address overflow and response cursors are checked. Active/interrupted
callbacks reject. Its four queue owners and HTIF's suspended caller/destination,
program loader, contexts and devices remain separate and incomplete. The TSI
bridge still rejects complete checkpointing. See
[tsi-loadmem-read.md](tsi-loadmem-read.md).

Selected component evidence:
`loadmem-read-current/invocation-gauvuay_/summary.json`. All 260 fresh sanitizer/
VCS continuations pass for 4/8/64/128/1,024/4,096-byte reads, including pending
writes, empty response queues, partial results, completion and acknowledgement.
All 520 complete owner/queue pre-edge readbacks and 193,094 continued call/data/
fixture-cycle records match the independent original-loop oracle. Each backend
passes 306 atomic/configuration/lifecycle checks. Twenty-eight fresh invalid
processes reject missing/truncated/trailing/version/kind/incompatible/phase/
cursor/alignment/length/response-width images before mutation/requests/readback.
Actual valid response corruption first differs at fixture C=127,
`RESULT[0] expected=0 actual=1`; operation 27 is never acknowledged (26 were).
All 306 component build/check/restore processes and original input snapshots
are retained. The final DPI failure exits with native status 2: earlier VCS
`$fatal` returned zero and correctly failed the runner's required exit check.
Earlier oracle-label and fixture-exit diagnostics remain separately retained.
These are host-component cuts; they do not satisfy required Rocket CPU cuts.

Actual installed-FESVR integration passes in native C++ and VCS DPI:
`real-fesvr-native/invocation-4ed87qfs/summary.json`. The generated RISC-V ELF
forces the production program-loader read/modify/write path with an incomplete
one-word response. All fourteen complete suspended-owner images match an
independent byte oracle; eight merged bytes and six reset serial words match.
This checks real FESVR integration, not CPU execution or context migration.
Integration ELF SHA256 is
`45a7f219e68180b49d557cad0c10277277af843c16e4a5e58dc8fb7fb6cb77be`;
the actual linked FESVR archive is
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
The first VCS link diagnostic is retained; the final link explicitly retains
the static FESVR archive when VCS places link flags before its C++ objects.

Exact Rocket build settings remain those above. The current rebuild retains
all 59 native units and binds the new owner header, implementation and actual
save/validate/load symbols (`rocket-tsi-read-integration-audit.json`). Both full
four-hart default/buffered controls pass at C=3,329,794 in
`rocket-controls/invocation-hh3w9zq2/`. All four complete traces
(37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes) and workload/store
labels match the original uninterrupted reference. These are CPU controls;
complete CPU checkpoint cuts remain pending. The workload hash remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
A fresh ordinary Rocket VCS diagnostic storage probe reads all 318,637 words
with seven clocks held before edges; it is not a CPU checkpoint image/trace.
Current CPU preflight/capture/restore requests still reject unsupported TSI or
missing durable capability before run/image/bridge output.

The final complete eight-check regression suite passes, including all 245 Python
tests, full M2/M3 metasim/ordinary RTL, widget/UART/blockdev/heartbeat ownership
and FCFS guards. Selected evidence:
`native-regressions-current/invocation-kf453gp_/summary.json` (5,106 retained
artifacts / 688 source bindings). The earlier complete eight-check invocation
is also preserved. Retained complete Rocket inventory, clock-event replay,
memory/policy, TracerV, FireSim driver and original four-hart control audits pass.

Executable native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration96/read-recheck
python -m tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs --audit automations/checkpoint_loop/runs/m11-iteration96/loadmem-read-current/invocation-gauvuay_/summary.json
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs --out automations/checkpoint_loop/runs/m11-iteration96/fesvr-recheck
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs --audit automations/checkpoint_loop/runs/m11-iteration96/real-fesvr-native/invocation-4ed87qfs/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration96/native-regressions-current/invocation-kf453gp_/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration96/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration96/rocket-controls/invocation-hh3w9zq2/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

Complete Level-1 fresh CPU continuation, Level-2 coherent CPU capture/readback/
captured-trace replay and all required early/warmed-cache/outstanding-memory/
late CPU cuts remain pending. Component labels cannot satisfy CPU cuts. No
dependency is missing. BOOM/Saturn remain pending; physical FPGA, standalone
Shuttle and ASIC power remain deferred. Existing iteration-95 controller
commits FireSim `b4e1daad6df62fda628ee56e69e5e71a43cac9d0`, then Chipyard
`a20c3f2a2ddac0f63e3627575d25302a9c96890b` are published and independently
confirmed (`publication.json`). Plans remain read-only; no staging/local commits.

`verification-commands.json` records executable argv, including a fresh complete
ordinary Rocket zero-edge VCS probe. `native-input-archives.json` seals 37,119
original native artifacts/input bindings, including failed invocations and
per-invocation source snapshots; every original runtime path remains mandatory.
The internal and executable CLI evidence audits pass
(`final-native-evidence-audit.json`, `final-archive-cli-audit.json`). Complete
artifact paths are in `artifact-manifest.json`; progress and remaining work are
in `summary.json`. Rechecks allocate new directories and preserve originals.

## Iteration 95: production FireSim driver and per-bridge termination ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration95/`.

The actual `firesim_top_t` now returns after completed synchronous host operations.
Its independent `firesim.bridge-run-loop.v1` owner preserves ready/tasks/issue/
poll/tick/terminate/status/finished phases, next bridge, termination and signed
32-bit exit code. It checks termination immediately after each bridge tick and
stops before touching later bridges. A successful termination query retains its
bridge until the exit-status call commits. Credit, PeekPoke and bridge calls
never replay after restore. Active/interrupted calls poison and reject.
`firesim.simulation.bridge-driver.v1` binds effective profiling configuration,
PeekPoke identity/schema and the complete post-heartbeat registry traversal.
It owns running/finalized lifecycle and requires fresh loading without MMIO,
callback execution, initialization or finalization. Anonymous profiling tasks
remain explicitly unsupported. Base flow, scheduler, each bridge, transport,
functional memory and generated RTL are separate owners. The FCFS driver,
loop and schemas are unchanged. See `firesim-driver-owner-audit.json`.

Selected original component evidence:
`firesim-driver-native/invocation-_u5imb8v/summary.json`. Native ASan/UBSan and
VCS DPI each exercise four distinct early terminating bridges with statuses
0/7/-9/INT_MIN, horizon exhaustion, and immediate zero-horizon completion.
Every completed host call is a cut: 18/20/22/24/27/1 per scenario. All 224 fresh
continuations pass; the independent original nested-loop oracle checks 2,464
complete owner payloads before edges and 4,846 continued boundary records.
Each backend passes 871 atomic/configuration/lifecycle assertions. Sixteen
separate invalid-owner processes reject missing/truncated/trailing/unknown/
incompatible/impossible-state images before loads, readback publication or
edges. Actual structurally valid next-bridge corruption first reports
`fixture_cycle=106 operation=6 acknowledged=5 expected=R 200 0 actual=R 208 0`;
the changed read is never acknowledged. These labels describe host fixtures,
not active Rocket target-cycle checkpoints or DUT semantic corruption.
All 258 executed component processes, input snapshots and complete artifact
catalogs are retained. No ASan/UBSan/leak diagnostics occur. A fixture's initial
global wall-clock stub incorrectly affected VCS licensing; the final fixture
pins only heartbeat's diagnostic clock and leaves libc/VCS time intact. Initial
compile/oracle/license diagnostics remain in separate failed invocations.

Exact Rocket VCS builds retain all 58 original native translation units and add
only `core/bridge_run_loop.cc`. Actual linked driver/loop hooks and all build
inputs are bound in `rocket-native-source-inventory-delta.json` and
`rocket-controls/invocation-4sp34o9f/rocket-build-identity.json`. Both full default
and buffered four-hart controls pass at C=3,329,794. All four complete traces
(37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes) and decoded workload/
store labels match the original uninterrupted reference. These are real active
CPU controls, not checkpoints. The independent current audit is
`rocket-controls-independent-audit.json`; original executable native build and
runtime argv are in the selected invocation's `summary.json`.
The existing self-checking workload hash remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Actual current CPU preflight still rejects TSI at `widget/12`; capture and
restore reject before run because no durable CPU capability exists. The three
native requests publish no image or bridge output. These are unsupported-owner
guards, not malformed CPU-image acceptance (`cpu-request-rejections/summary.json`).
`rocket-tsi-fesvr-pending-owner-audit.json` lists the full next-owner chain,
including HTIF's suspended fromhost queue/callback and read destinations,
program-load/reset/idle progress, contexts, serial/loadmem queues and device
handles. Capturing deques alone cannot reconstruct a fresh FESVR process.
Installed headers, checked source and actually linked FESVR library are hashed;
no TSI support is inferred.

All 245 Python tests and eight preserved native checks pass in
`native-regressions/invocation-rovyvlmy/summary.json` (5,100 retained artifacts /
682 source bindings). An earlier eight-check execution overlapped edits and
correctly failed its source-retention guard; it remains preserved. Independent
retained inventory, clock-event, memory, TracerV and original four-hart control
audits pass. A fresh ordinary Rocket VCS process reads all 318,637 diagnostic
semantic words with seven clocks held and zero edges. This remains a storage
probe, not a CPU image/trace. Current native commands source both repository
environments then `vcs-env.sh` last; VCS Y-2026.03-SP1, `-full64`, GCC/G++ 13.

Executable checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_firesim_driver_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration95/firesim-driver-recheck
python -m tools.checkpoint_formats.tests.verify_firesim_driver_checkpoint_vcs --audit automations/checkpoint_loop/runs/m11-iteration95/firesim-driver-native/invocation-_u5imb8v/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration95/native-regressions/invocation-rovyvlmy/summary.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration95/rocket-controls/invocation-4sp34o9f/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration95/native-input-archives.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration94/rocket-controls/invocation-s3q7sujf/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration94/native-input-archives.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration95/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration95/rocket-controls/invocation-4sp34o9f/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

`verification-commands.json` also records an executable fresh ordinary Rocket
zero-edge VCS probe with complete pattern/baseline paths, plus the retained-
evidence audit. `native-input-archives.json` seals original native bytes and
source snapshots; `artifact-manifest.json` lists full artifact paths. Rechecks
allocate new directories and never overwrite a selected native invocation.
The final archive binds 62,123 original native inputs/artifacts; both the
internal and executable CLI retention audits pass. A first sealing catalog
included its active stdout and correctly failed the later retention check.
`first-seal-diagnostic/` preserves that rejection. The final catalog excludes
only sealer stdout while all native build/runtime logs remain mandatory.

Acceptance remains **in_progress**. Complete TSI/FESVR, stream/transport and
remaining runtime owners; bind all semantic owners through actual FAME metasim
with coherent clock events; then verify fresh complete Level-1 CPU continuation
and independent Level-2 CPU image/readback/captured-trace replay at early,
warmed-cache, outstanding-memory and late cuts. No required CPU checkpoint cut
has passed. No external dependency is missing. BOOM/Saturn remain pending;
physical FPGA/standalone Shuttle/ASIC work is deferred. Existing iteration-94
controller commits FireSim `28f6aa38fb1033921c399509069eb1cbd6f0b04e`, then
Chipyard `715088bb1364419f914264cc8c218723604d4c18`, are published and their remote
tips independently confirmed (`publication.json`). No staging or local commits;
both plans remain read-only.

## Iteration 94: complete TracerV host ownership and exact-recipe controls

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration94/`.

`+tracerv-checkpoint-buffered` adds `firesim.bridge.tracerv.v1` for completed
host calls. Save/restore does not pull/flush streams, change MMIO or publish an
output file. Own initialization, `cur_cycle` and the entire serialized history,
including the clock header. Bind all fifteen MMIO addresses, stream index/depth,
core IPC, clock name/ratio, trace enable, output/test mode, and every cycle/PC/
instruction trigger field. An output path is a fresh-process sink; its history
comes from captured bytes. Base simulator/stream references are rebound to
separate owners. Active/poisoned calls, finished/live-file/fireperf/tracker modes
and nonzero legacy DMA state reject. Temporary serializer FILE/buffer state
exists only inside guarded calls. `tracerv-owner-audit.json` lists every member,
including explicitly absent/rebound fields and separately owned hardware.
Generated TracerV FIFO/trigger/cycle state and CPU AXI queues remain separate;
this host adapter does not authorize an aggregate CPU profile.

The selected original host-component invocation is
`tracerv-native/invocation-ou6pxbr8/summary.json`: 256 fresh continuations,
296 executed processes including two builds, all four exact Rocket constructors
(streams 0–3, depth 6,144, IPC 1, 1/1 clock ratio), human/binary/test/disabled
modes and trigger selectors 0–3. Eight host-call cuts per case have fixture
labels C=100/107/114/121/128/135/142/149. They include complete batches, queued
traffic below the drain threshold, flushes and the final pre-publication state.
An independent byte/MMIO oracle verifies every owner and separately captured
fixture queue before edges and all 1,152 continued calls. Each backend passes
1,482 unchanged-state/configuration/lifecycle assertions. Reentrant calls and
interrupted pulls poison/reject rather than expose a suspended buffer.
Valid lifecycle corruption rejects before init MMIO; valid captured-history
corruption first reports `tracerv_output` at fixture C=149 without completing
that boundary. These are host fixtures, not active CPU checkpoint cuts.

Separate original `tracerv-invalid-native/invocation-375e7cg0/summary.json`
records sixteen actual fresh native/VCS processes rejecting missing/truncated/
trailing/unknown/incompatible/invalid-length/lifecycle/empty images before
fixture edges or readback publication, preserving the fresh sink sentinel.
All 312 selected process logs have no ASan/UBSan/leak diagnostics. Original
source snapshots and complete artifact catalogs seal both invocations. The
first VCS link failed because as-needed linking discarded libraries placed
before its objects; corrected link flags retain libelf/libdwarf. The failed
invocation remains preserved separately.

The exact Rocket VCS build is retained under
`rocket-controls/invocation-s3q7sujf/`. `rocket-tracerv-integration-audit.json`
binds its actual binary/header/source hashes, all three linked hooks and exact
constructor equality with the component evidence. The default and buffered
UART/heartbeat/TracerV complete four-hart controls both pass at C=3,329,794.
All four full hart files match the uninterrupted reference byte-for-byte
(37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes); all decoded phase,
completion, failure and tohost labels match independently. This covers actual
active execution on all four cores through the late memory phase. These are
uninterrupted controls; complete CPU checkpoint continuation and CPU RTL
replay remain pending. Workload SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The new CPU binary still rejects preflight at TSI (`widget/12`) and rejects
capture/restore without a durable capability, before run or output publication.
Those requests do not establish malformed CPU-image loader acceptance.

All 245 Python tests and eight preserved native checks pass in
`native-regressions/invocation-axtrckf_/summary.json`, guarding the iteration-93
archive before/after. Five independent retained audits pass: complete Rocket
inventory/readback, both full original controls, complete memory/policy replay,
clock-event replay and original archived bytes. The old control launcher was
not in its iteration-90 archive; `rocket-original-input-archives.json` selects
only exact original recorded hashes/snapshots from later archives. No native
path or audit rule is relaxed. A fresh ordinary Rocket VCS process again reads
all 318,637 diagnostic words before seven clocks advance. This is a storage
probe, not a workload image/replay. Failed initial audit/link diagnostics are
retained alongside passing checks. `native-input-archives.json` seals 8,814
original bindings; both internal and executable CLI audits pass.
`verification-commands.json` records the exact executable argv/relative cwd.

Executable native checks from the Chipyard root (all native build/runtime
shells independently source `vcs-env.sh` last):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
checkpoint_rocket_header=automations/checkpoint_loop/runs/m11-iteration87/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h
python -m tools.checkpoint_formats.tests.verify_tracerv_checkpoint_vcs --rocket-header "$checkpoint_rocket_header" --out automations/checkpoint_loop/runs/m11-iteration94/tracerv-recheck
python -m tools.checkpoint_formats.tests.verify_tracerv_checkpoint_vcs --audit automations/checkpoint_loop/runs/m11-iteration94/tracerv-native/invocation-ou6pxbr8/summary.json
python -m tools.checkpoint_formats.tests.verify_tracerv_invalid_vcs --summary automations/checkpoint_loop/runs/m11-iteration94/tracerv-native/invocation-ou6pxbr8/summary.json --out automations/checkpoint_loop/runs/m11-iteration94/tracerv-invalid-recheck
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration94/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration94/rocket-controls/invocation-s3q7sujf/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration94/rocket-controls/invocation-s3q7sujf/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration94/native-regressions/invocation-axtrckf_/summary.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration94/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration94/protected-inputs.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration90/rocket-controls/invocation-6f3ulwfs/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration94/rocket-original-input-archives.json
```

Acceptance remains **in_progress**: complete run-loop/TSI/FESVR and remaining
runtime owners, bind all semantic owners through actual FAME metasim with
coherent clock events, then fresh complete Level-1 continuation and independent
Level-2 readback/captured CPU trace replay at early, warmed-cache,
outstanding-memory and late cuts. No required CPU checkpoint cut has passed.
BOOM/Saturn remain pending; standalone Shuttle/physical FPGA/ASIC work is
excluded. Existing iteration-93 commits FireSim
`e3b78c81021ac14a5db17e33725a1ebe477377af`, then Chipyard
`30b335fba5a8f3f8c59981ba8851635dc17e12bf`, were published and remote tips
confirmed in `publication.json`. No staging or local commits; plans are intact.

## Iteration 93: retain native evidence across verification reruns

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration93/`.

The iteration-92 controller verification failed because its fixed-path regression
launcher overwrote archived `regression-{0,5,6,7}.log` files when rerun. The audit
correctly rejected the changed bytes. Exact original logs have been recovered
from their original content-addressed snapshots. Displaced verifier output and
both hashes remain in `retained-log-recovery.json`; no audit rule was relaxed.
Use the maintained `tools.checkpoint_formats.native_regressions` module for new
checks. Historical launchers and their selected invocations remain preserved.

Every maintained invocation receives fresh build, simulation, log and result
directories. All generated RTL, images, traces, readback, binaries and native
logs are sealed in a complete file catalog. Prior native evidence is audited
before and after execution. Original local checker/compiler sources are copied
to content-addressed snapshots and must remain unchanged during the run; later
source evolution uses the exact original snapshot. Failed commands and failed
evidence guards retain diagnostics and cannot publish a passing result. Five
new tests pass, including actual processes that overwrite retained logs or
change source files, and changed/missing/extra artifact rejection.

Both full native eight-check suites actually pass:

| Selected original invocation | Python tests | Sealed files excluding summary | Original source bindings |
| --- | ---: | ---: | ---: |
| `native-regressions/invocation-7e9aw5m8/summary.json` | 243 | 4,415 | Original iteration-92 archive guard |
| `native-regressions/invocation-gk0gj8s_/summary.json` | 245 | 5,086 | 672 |

The second full suite additionally guards all 4,416 original first-invocation
bindings. Both runs preserve full M2/M3 metasim/ordinary RTL replay, 52 widget,
18 UART, 30 blockdev and 96 heartbeat continuations, their native rejection and
corruption cases, and eight FCFS Make/four generator guards. Separate source,
captured state, complete readback and native continuation artifacts remain
inside each selected invocation. Both catalogs and original controller archives
re-audit after the rerun. `first-native-archives.json` binds the original first
suite; `native-input-archives.json` binds the final selected evidence and source
snapshots. `verification-commands.json` records exact argv and relative cwd.

Six retained audits also pass: complete Rocket storage/clock/readback, original
controller archives, both full four-hart controls, complete memory/policy replay
and the 172-sample clock-event capture/replay (2,064 stored words / 1,720 outputs).
A new fresh ordinary RTL VCS process reads and deposits all 318,637 Rocket
diagnostic words before any of seven clocks advances; its log is under
`native-rocket-probe-*/run.log`. This uses the exact retained recipe's pre-FAME
RTL and pinned Y-2026.03-SP1 runtime. It is a storage probe. No CPU workload cut,
checkpoint continuation or captured CPU boundary replay is claimed. Original
four-hart workload SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Executable checks from the Chipyard root (the module also sources both repository
environments and `vcs-env.sh` last in every native build/run shell):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
checkpoint_rocket_header=automations/checkpoint_loop/runs/m11-iteration87/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h
checkpoint_fcfs_inventory=automations/checkpoint_loop/runs/m3-metasim/f2/f2-fasedtests-AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config/checkpoint-native
python -m tools.checkpoint_formats.native_regressions --out automations/checkpoint_loop/runs/m11-iteration93/native-regressions --rocket-header "$checkpoint_rocket_header" --production "$checkpoint_fcfs_inventory" --guard automations/checkpoint_loop/runs/m11-iteration92/native-input-archives.json automations/checkpoint_loop/runs/m11-iteration92/protected-inputs.json --guard automations/checkpoint_loop/runs/m11-iteration93/first-native-archives.json automations/checkpoint_loop/runs/m11-iteration93/protected-inputs.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration93/native-regressions/invocation-gk0gj8s_/summary.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration93/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration93/protected-inputs.json
python -m tools.checkpoint_formats.tests.audit_multiclock_replay --summary automations/checkpoint_loop/runs/m11-iteration92/multiclock-replay-current/invocation-pub5jaqh/summary.json
```

The exact new Rocket diagnostic VCS command is recorded in
`verification-commands.json`; the full native build/probe commands remain in the
iteration-91 inventory summary. Recipe settings are freshly re-read in
`recipe.json`. Acceptance remains in progress: bind semantic owners through
actual FAME metasim/coherent clock events, complete CPU host/runtime owners,
then fresh Level-1 CPU continuation and independent Level-2 CPU readback/trace
replay at early, warmed-cache, outstanding-memory and late cuts. BOOM/Saturn
remain pending. No external dependency is missing; FPGA/ASIC work is deferred.
Existing iteration-92 commits FireSim
`0cba18f411f8fc98f74145f67b5854a546586553` and Chipyard
`1c55ffeb7c34b2f7bae6fd44b33a38a873e5a07d` were published in that order and
independently confirmed in `publication.json`. Plans, environments, index and
local HEADs remain preserved; no staging or local commits were performed.

## Iteration 92: clock-event images and fresh ordinary RTL replay

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration92/`.

Added an independent Level-2 version-2 payload for schema-3 inventories. Images
bind every boundary clock's settled level and completed rising-edge count, an
absolute event index and an explicitly selected cycle clock. Only all-low cuts
are supported. Traces capture every upcoming full clock vector, including
falling and simultaneous rising/falling transitions. Cycle labels count actual
completed rises of the selected clock; they can repeat across events. Inputs
settle and all outputs (including forwarded clocks) compare before the full
clock vector advances together. Both artifacts validate before loader files
are published; native restore/readback completes before any edge. Legacy
single-clock formats, StateIDs and Level-1 ownership remain independent.

Native evidence is **an ordinary RTL component capture**, not a Rocket workload
or metasim capture. The original compiler-emitted seven-clock component owns
seven counters, four RAM words and its synchronous read-data register: nine
entries / twelve words. Its 192 actual source events exercise every domain,
120 simultaneous-rise events, 24 mixed-rise/fall events and 137 events without
a cycle-clock rise. Independent source recurrence checks every stored word.
Source workload bench SHA256:
`e55ae29ea3e73b3ebd892c8315301ed7c12d8ca11b0c159023a43d173a799006`.
The source exits before fresh restore processes start. Component cuts are:

| Event index | Completed cycle-clock rises | Compared event samples |
| ---: | ---: | ---: |
| 0 | 0 | 48 |
| 12 | 3 | 48 |
| 80 | 23 | 48 |
| 164 | 47 | 28 |

The independent native waveform audit verifies every word before edges and at
all 172 continuation samples: 2,064 state comparisons and 1,720 output
comparisons. Direct continuous probes expose RAM words omitted by VCS's default
waveform dump. Two actual post-readback corruptions (`s0`, `ram_r_data`) fail at
event 80 / C=23, first reporting `crossing` and `readData`, respectively, with
zero acknowledged events. Seven invalid images (truncation, checksum, build,
missing/unknown owner, missing clock, missing output) reject without publishing
loader files. Four native loader requests (missing, duplicate, unknown,
wrong-width word) reject without depositing state and read back the complete
initial baseline with zero edges. Evidence includes thirteen fresh simulator
processes plus five builds, exact argv, snapshots, images, traces, logs and VCS
waveforms. Original final evidence is
`multiclock-replay-current/invocation-pub5jaqh/summary.json` and
`multiclock-replay-current-independent-audit.json`. Initial invocations and an
audit output-count correction remain retained.

All 240 final Python tests and eight preserved regression checks pass, including
M2/M3 metasim/ordinary RTL, 52 widget, 18 UART, 30 blockdev and 96 heartbeat
continuations and FCFS Make/generator guards. Results are in
`python-final.log` and `regression-results.json`. Four retained evidence audits
pass in `retained-audit-results.json`: complete Rocket inventory/readback,
controller-aware archives, both original full four-hart controls and complete
memory/policy evidence. Exact Rocket settings are re-read in `recipe.json`;
no new CPU workload run is claimed. Original four-hart workload SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Executable native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_multiclock_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration91/scala-retained-artifacts/semantic-multiclock --out automations/checkpoint_loop/runs/m11-iteration92/multiclock-replay-recheck
python -m tools.checkpoint_formats.tests.audit_multiclock_replay --summary automations/checkpoint_loop/runs/m11-iteration92/multiclock-replay-current/invocation-pub5jaqh/summary.json
python -m unittest discover -s tools/checkpoint_formats/tests -v
# Use the maintained invocation-preserving suite in iteration 93 above.
```

Rocket acceptance remains in progress: bind original owners through the actual
metasim, capture coherent events at real four-hart workload cuts, finish
run-loop/TSI/FESVR/TracerV and other runtime owners, then demonstrate fresh
Level-1 continuation and independent complete Level-2 CPU replay at early,
warmed-cache, outstanding-memory and late cuts. This component contract cannot
authorize a CPU checkpoint profile. No external dependency is missing. The
iteration-91 controller commits FireSim
`fde729a95721c4e5d0dd3dd00368600ea4cd9a7c` and Chipyard
`d13fca04982c1d9f311daa9ab6a096c4f927882d` were published in that order;
`publication.json` confirms both remote tips. Local tracking refs are read-only.
No staging or local commits were performed.

## Iteration 91: complete Rocket clean storage and explicit clock ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/`.

The exact recipe now elaborates with discovery-only
`--semantic-multiclock-inventory`, independently of Level-1. Schema 3 lists all
seven boundary clock inputs, every state clock and six output clocks' proven
sources. It does not infer clock periods or authorize a multi-clock checkpoint.
High-level image encoding/decoding rejects until event phases and a coherent cut
are bound; multi-clock banked access also rejects. Legacy schemas 1/2 and
semantic StateIDs remain unchanged. Native VCS commands source both environments
and `vcs-env.sh` last; no FPGA bitstream build runs.

The clean emitter now preserves all original storage, including constant-driven
registers. A separate `.semantic-clean-access.json` binds original StateIDs to
the actual emitter's storage paths, its clean-source SHA256 and manifest SHA256.
It records register, memory and memory-pipeline keyword renames and each required
instance path segment. Stateless unused instances can disappear without deleting
storage owners. Compiler-internal emission state supplies these names; paths are
not guessed from keyword spellings. Independent RTL parsing audits all register
and array declarations, parameterized initialized owners, boundary widths,
sequential blocks and clock connections. Complete ChipTop ownership is:

| Owner clock / initialization | Entries | Words |
| --- | ---: | ---: |
| `clock_mbus_0` | 255 | 65,787 |
| `clock_sbus_rockettile_0` | 1,435 | 43,895 |
| `clock_sbus_rockettile_1` | 1,435 | 43,895 |
| `clock_sbus_rockettile_2` | 1,435 | 43,895 |
| `clock_sbus_rockettile_3` | 1,435 | 43,895 |
| `clock_uncore` | 2,321 | 76,942 |
| `serial_tl_0_clock_in` | 322 | 322 |
| Exact initialized external values | 6 | 6 |
| Total | 8,644 | 318,637 |

`rocket-semantic-retained-inventory/` retains the exact-recipe command, original
FIRRTL/reference, emitted manifest, clean access map, clean RTL and boundary.
The full ordinary RTL VCS build and six fresh native probes are retained at
`rocket-native-complete-inventory/invocation-yfr_nr9p/summary.json`.
Every probe reads all 318,637 original words before any edge. The valid probe
deposits deterministic diagnostic patterns and reads back every word, with all
seven clocks low. Four invalid loader requests (missing word, duplicate word,
unknown word, wrong width) reject without any deposit and preserve complete
baseline readback. Actual post-deposit corruption is detected by native readback.
`rocket-native-independent-audit.json` independently rechecks source/archive
hashes, complete storage/clock ownership, every pattern row, exact build/run argv,
native logs and all six fresh processes. **These are storage probes, with no CPU
workload cut, captured checkpoint, boundary trace, or continuation claim.**

The two final seven-clock component probes also pass, including a constant-driven
register, renamed nested instance and renamed memory pipeline: 12 and 13 words,
six fresh processes each. `selected-multiclock-fixtures.json` selects their exact
summaries and independent audits. All 22 Scala inventory tests and 235 final
Python tests pass. All eight preserved regression checks pass. Original memory,
initialized-owner waveform and full four-hart workload/control evidence is
retained and independently re-audited, using immutable source snapshots when
implementation sources have since changed.
The full current forwarded-clock native regression also passes (22 words / 108
samples). Both complete current memory suites and their independent audit pass:
37 metasim-captured words / 149 continuation samples, all five ordinary memory
policies / 245 samples, and 37 fresh native processes. Their current summaries
are `forwarded-native/summary.json`, `memory-native/summary.json` and
`memory-policy-native/summary.json`; `independent-memory-audit.json` binds the
original current images, logs and comparisons.

The previous verification incorrectly required `.git/index` and local HEADs to
remain identical after the loop controller created its checkpoint. The durable
audit now checks permitted controller ancestry, unchanged plan/environment bytes,
all 1,321 original archive bindings and original runtime evidence. Evolving
source bytes must match their recorded snapshot and controller commit; binaries,
generated artifacts, traces and logs cannot use that fallback. Index/HEAD
preservation is checked during this implementation turn and recorded separately.
The original failed verifier and all intermediate emission diagnostics remain
retained. Existing iteration 90 commits were published FireSim first
(`cc5681b967ead61edb31a13757586a117188c195`), then Chipyard
(`ab558a7d34eefd4262e0d4d0e11d94effe563c40`); remote tips were independently
confirmed. Local tracking-reference updates are read-only. No local staging or
commits were performed.

Executable native discovery probes (each writes a new invocation directory):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_multiclock_inventory_vcs --base automations/checkpoint_loop/runs/m11-iteration91/rocket-semantic-retained-inventory/FireSim-generated --out automations/checkpoint_loop/runs/m11-iteration91/rocket-native-recheck
python -m tools.checkpoint_formats.tests.audit_multiclock_inventory --summary automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/summary.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration90/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration90/protected-inputs.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration90/rocket-controls/invocation-6f3ulwfs/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration90/native-input-archives.json
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration91/run-regressions.py
```

CPU acceptance is still in progress. Next: preserve/bind original semantic
owners through the actual generated simulator, capture coherent clock events
and CPU state during real four-hart execution, and complete runtime run-loop,
TSI/FESVR/TracerV ownership. Required early, warmed-cache, outstanding-memory and
late CPU checkpoint cuts, fresh Level-1 continuation, and independent Level-2
image readback/captured-trace replay remain untested. No external dependency is
missing. BOOM and Shuttle + Saturn remain pending; physical FPGA/ASIC work is
deferred.

## Iteration 90: initialized external state and parent clock pins

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration90/`.

Pre-FAME inventory now owns each exact non-SYNTHESIS `plusarg_reader.myplus`
register. These values initialize from runtime arguments; the compiler never
substitutes `DEFAULT` for checkpoint state. Version-2 semantic manifests bind
every reachable external instance, specialized width/default/format and the
exact inline source SHA256. Their initialized registers have `clock_domain`
`initial`, separate from the selected target clock. Ordinary version-1
manifests and Level-1 state identities remain unchanged. Missing, altered,
duplicated or wrong-circuit source annotations, unsupported parameters/ports
and all other opaque models reject before semantic publication. Clean RTL
retains the original parameterized implementation exactly once. The capture
oracle audits actual model bytes, parameters and complete storage declarations;
SYNTHESIS variants and lost/changed owners reject. This is VCS semantic
ownership, with no physical FPGA support claim for this simulation model.

Clock provenance also follows a concrete child's driven input pin back to its
parent net. Rocket's serial domain uses `serdesser.clock` this way. Types,
directions, drivers and dependency cycles are checked; an input pin cannot
turn data, a gate or an undriven net into a target clock. All 19 final Scala
inventory tests pass, including exact external-source negatives and actual
emitted input-clock fanout. All 225 final Python tests pass.

The native ordinary RTL component checks consume the actual compiler-emitted
circuits. Both default and nondefault initialized values are captured, including
nested repeated instances and widths 1, 32 and 65. Source processes exit before
fresh restore processes start with conflicting plusargs. Each fixture restores
and reads back all five words before any edge at component C=0/3/9/16, then
compares 80 samples and all five outputs at their original labels. The second
fixture clocks its counter through the child's driven input pin. These are
component cuts, not Rocket workload cuts or vector workloads. Original results:

| Component | Original native summary | Independent original-artifact audit |
| --- | --- | --- |
| Initialized values | `semantic-plusarg-waveform-native/invocation-x0nujzuh/summary.json` | `semantic-plusarg-waveform-native-independent-audit.json` |
| Parent input-clock fanout plus initialized values | `semantic-clock-pin-waveform-native/invocation-a8tf_532/summary.json` | `semantic-clock-pin-waveform-native-independent-audit.json` |

Each audit verifies actual source state and recurrence, exact image membership,
all zero-edge guards, actual complete native waveform readback and per-cycle
input/output comparisons, finite captured traces, conflicting fresh initialization,
native build/run logs and 26 distinct native processes. Each fixture has eight
actual post-readback stored-value corruptions: their corresponding output first
diverges at C=9 and no edge is acknowledged. Ten malformed/incompatible/missing/
unknown-owner images and eight actual native loader requests reject before
partial restore. Across both fixtures this is 160 samples / 800 output
comparisons, sixteen corruption cases, twenty image rejections and sixteen
native loader rejections. Archived original inputs and their hashes are bound
in each summary; native argv/PIDs/exits are in the actual build/run logs.

Exact-recipe Rocket discovery now visits its six initialized external owners
and rejects seven distinct state clock domains: `clock_mbus_0`,
`clock_sbus_rockettile_0` through `_3`, `clock_uncore` and
`serial_tl_0_clock_in`, all under `FireSim.chiptop0`. No partial semantic
artifacts are emitted. The original IR, recipe record, compiler argv and input
hashes are in `rocket-semantic-verified-inventory/summary.json`.
`rocket-initialized-owner-audit.json` independently binds all six original
opaque instances to exact source bytes and parameters. Its 1,488 instances,
7,734 explicit registers, 500 memories / 310,493 logical words, 404 implicit
memory-pipeline owners and six initialized values suggest 318,637 semantic
words. This total remains a raw diagnostic, not a complete semantic manifest.
Independent multi-clock event capture, complete readback and replay are pending.

Initial diagnostics are retained: an oversized 65-bit test argument was corrected
without reducing widths or cases; a fanout test moved its instance declaration
before its first reference; a concurrent VCS build collided in its timestamp/PID
temporary directory. The corrected verifier gives each invocation its own
temporary root. The native replay test explicitly flushes the settled waveform
before comparisons so a failing DPI exit retains the first divergent values.
Expected-rejection discovery retries retain each original
compiler diagnostic. Memory audits also retain a cross-tool PID-namespace
collision diagnostic; the full corrected memory checks run in one shell.

Executable native checks from the Chipyard root (same pinned VCS release,
`-full64`, GCC/G++ 13, no FPGA build):

```sh
source env.sh && source sims/firesim/env.sh
export JAVA_TOOL_OPTIONS="-Xmx8G -Xss8M"
export CHECKPOINT_TEST_ARTIFACT_DIR="$PWD/automations/checkpoint_loop/runs/m11-iteration90/scala-reproduction-artifacts"
source automations/checkpoint_loop/vcs-env.sh
make -C sims/firesim/sim testOnly FIRESIM_SBT_PROJECT=midas SCALA_TEST=midas.checkpoint.SemanticStateInventorySpec
python -m tools.checkpoint_formats.tests.verify_semantic_plusarg_vcs \
  --scala-artifacts "$CHECKPOINT_TEST_ARTIFACT_DIR" \
  --out automations/checkpoint_loop/runs/m11-iteration90/initialized-reproduction
python -m tools.checkpoint_formats.tests.verify_semantic_plusarg_vcs --clock-pin \
  --scala-artifacts "$CHECKPOINT_TEST_ARTIFACT_DIR" \
  --out automations/checkpoint_loop/runs/m11-iteration90/clock-pin-reproduction
python -m tools.checkpoint_formats.tests.audit_semantic_plusarg \
  --summary automations/checkpoint_loop/runs/m11-iteration90/semantic-plusarg-waveform-native/invocation-x0nujzuh/summary.json
python -m tools.checkpoint_formats.tests.audit_semantic_plusarg \
  --summary automations/checkpoint_loop/runs/m11-iteration90/semantic-clock-pin-waveform-native/invocation-a8tf_532/summary.json
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration90/discover-rocket-verified.py
python automations/checkpoint_loop/runs/m11-iteration90/audit-rocket-initialized-state.py
```

Both full exact-recipe default/buffered four-hart controls pass at C=3,329,794.
All four complete hart traces and independently decoded workload/store labels
match the uninterrupted reference. The original invocation is
`rocket-controls/invocation-6f3ulwfs/summary.json`; its independent audit is
`rocket-controls-independent-audit.json`. Native source binding retains 297
inputs / 58 translation units and 445,838 generated state words. Workload
SHA256 is `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Fresh current native CPU preflight/save/restore requests reject incomplete
runtime support before execution and publish no partial checkpoint. These
controls and unsupported requests do not establish CPU continuation. All eight
preserved native regression checks, the full forwarded-clock native checks,
the full metasim memory checks and all five ordinary memory-policy checks pass.
`independent-memory-final-audit.json` verifies the original complete memory
images and 37 distinct native processes. Final original scope, native argv,
source snapshots and all created files are bound by `summary.json`,
`verification-commands.json`, `executed-initialized-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`.

Additional exact-recipe controls and retained regression reproduction commands:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration90/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration87/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls \
  --summary automations/checkpoint_loop/runs/m11-iteration90/rocket-controls/invocation-6f3ulwfs/summary.json
python -m tools.checkpoint_formats.tests.audit_semantic_memory \
  --metasim-summary automations/checkpoint_loop/runs/m11-iteration90/memory-verified-regression/summary.json \
  --policies-summary automations/checkpoint_loop/runs/m11-iteration90/ordinary-memory-policies-complete/summary.json
```

Complete CPU runtime ownership and fresh Level-1 continuation remain pending.
The Level-2 CPU boundary still needs seven-clock event scheduling and independent
active-workload capture/readback/replay, plus CPU image and corruption checks.
Required early, warmed-cache, outstanding-memory and late CPU checkpoint cuts
have not passed. BOOM and Shuttle + Saturn remain pending; physical FPGA and
ASIC work stay deferred. No required external dependency is missing.

## Iteration 89: synchronous and readwrite memory ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration89/`.

The pre-FAME inventory now owns one-cycle FIRRTL passthrough memory storage,
including the exact stored address for write-first/undefined readers, stored
data for read-first readers, and stored read data for read-first/undefined
readwriters. Each is a distinct semantic register, with its port field's actual
width, lowered name, reset semantics and resolved target clock, alongside every
logical array word. Clean RTL emission preserves the same passthrough layout.
Longer/readwrite-asynchronous/write-first-readwrite pipelines, unrelated port
clocks and colliding owner paths reject before semantic publication. All 15
Scala inventory tests pass, including emitted-layout and collision checks.
No CPU runtime profile or new checkpoint schema is enabled.

`memory-complete-native/summary.json` records actual VCS metasim capture from
the self-checking `MemoryPipelineFixture`, then eight fresh ordinary RTL VCS
restores at fixture C=0/5/13/21/24/26/28/30. All 37 words / nine semantic entries
are read back before any edge; all 149 continuation samples compare all five
outputs at their original labels. An independent recurrence checks every word
and output across all 37 captured edges, including enabled/disabled reads,
same-address collisions, and held data differing from address-selected contents.
These are component cuts, not Rocket CPU cuts. Five actual malformed/build/
missing-pipeline/unknown-owner images and four native loader cases reject without
partial publication/deposit. Four actual stored-pipeline corruptions first fail
at fixture C=21 on their corresponding output, acknowledging zero edges.

`ordinary-memory-policies-complete/summary.json` separately consumes actual
Scala-emitted circuits for all five supported reader/readwriter policies,
including a non-power-of-two RAM. Twenty fresh ordinary RTL continuations
restore all six words per circuit at C=0/5/10/16 and compare 245 samples. Five
actual pipeline corruptions fail `result` at C=10 before acknowledging an edge.
`independent-memory-audit.json` checks original images, complete native readback
benches, captured traces, pinned-release logs and 37 distinct fresh process IDs.

An initial undefined-reader metasim fixture correctly rejected changed ownership:
Golden Gate resolves its undefined policy to read-first and stores data, whereas
the earlier semantic reference stores an address. Both layouts have independent
ordinary RTL tests; no conversion between them is claimed. The passing metasim
fixture uses defined reader policies and both supported readwriter policies.
The initial ownership diagnostic, incorrect readwriter hold expectation and
missing ordinary-VCS initreg compile switch, plus their full corrected native
runs, are retained. The test expectation now follows the actual emitter, which
captures old readwriter data on enabled write edges too.

Exact Rocket ChipTop discovery now passes the synchronous/readwrite memories
and rejects `opaque external module plusarg_reader`, with no partial semantic
outputs. Its exact-recipe compiler argv, input hashes, original pre-FAME IR and
rejection are under `rocket-semantic-final-inventory/`. A separate complete raw
hierarchy diagnostic still finds 1,488 instances, 7,734 explicit registers,
500 memories / 310,493 logical words and six opaque instances. All 404
synchronous memories are undefined-policy readwriters with 404 additional
candidate stored-read-data owners; the other 96 memories are asynchronous
readers. These declaration counts are diagnostics, not a complete semantic
manifest. Multi-clock event capture/readback/replay remains pending.

Executable checks from the Chipyard root, using VCS Y-2026.03-SP1, `-full64`,
system GCC/G++ 13 and no FPGA build:

```sh
source env.sh && source sims/firesim/env.sh
export JAVA_TOOL_OPTIONS="-Xmx8G -Xss8M"
export CHECKPOINT_TEST_ARTIFACT_DIR="$PWD/automations/checkpoint_loop/runs/m11-iteration89/scala-final-artifacts"
source automations/checkpoint_loop/vcs-env.sh
make -C sims/firesim/sim testOnly FIRESIM_SBT_PROJECT=midas SCALA_TEST=midas.checkpoint.SemanticStateInventorySpec
python -m tools.checkpoint_formats.tests.verify_semantic_memory_vcs \
  --build automations/checkpoint_loop/runs/m11-iteration89/memory-defined-build \
  --out automations/checkpoint_loop/runs/m11-iteration89/memory-reproduction-native
python -m tools.checkpoint_formats.tests.verify_semantic_memory_policies_vcs \
  --scala-artifacts automations/checkpoint_loop/runs/m11-iteration89/scala-final-artifacts \
  --out automations/checkpoint_loop/runs/m11-iteration89/ordinary-memory-reproduction
python -m tools.checkpoint_formats.tests.audit_semantic_memory \
  --metasim-summary automations/checkpoint_loop/runs/m11-iteration89/memory-complete-native/summary.json \
  --policies-summary automations/checkpoint_loop/runs/m11-iteration89/ordinary-memory-policies-complete/summary.json
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration89/discover-rocket-semantic.py
```

Both full exact-recipe native default/buffered four-hart controls pass at
C=3,329,794. Every complete hart trace and decoded workload/store label matches
the uninterrupted reference. The retained run is
`rocket-controls/invocation-t0bmlj86/summary.json`, with 297 bound native inputs /
58 translation units. Workload SHA256 is
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
All 221 final Python tests, eight preserved native regression checks and the
full five-cut forwarded-clock native regression pass. Fresh current CPU
preflight/save/restore requests reject incomplete ownership before execution.
These controls/rejections do not establish CPU continuation. Reproduce into a
new retained invocation, then audit the selected original evidence:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration89/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration87/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls \
  --summary automations/checkpoint_loop/runs/m11-iteration89/rocket-controls/invocation-t0bmlj86/summary.json
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration89/verify-evidence.py
```

The existing controller commits were published FireSim first
(`a8d3ed98c000f2fa46ce31b5c12b3c2bc9ce878b`), then Chipyard
(`b0fb1ef48f5f8949c4c40f9187e28e8f453c77c3`), with independently confirmed
remote tips. Local remote-tracking updates hit read-only metadata. No local
staging or commits. Protected plans, environments, indexes and heads remain
unchanged during this turn. `summary.json`, `selected-evidence.json`,
`native-input-archives.json`, `executed-native-commands.json` and
`verification-commands.json` retain the final scope, source bindings and exact
native argv; the report references concrete files listed in
`artifact-manifest.json`.

The loop's iteration-88 artifact complaint came from listing a directory where
its report validator requires a nonempty file. The iteration-89 report names
concrete summary/manifest files; `artifact-manifest.json` enumerates all retained
files. The diagnostic directory itself is not a report artifact.

Complete CPU Level-1 runtime ownership/fresh continuation and independent
Level-2 opaque owners, multi-clock events, active-workload capture/readback/replay
and CPU image/corruption cases remain pending. Physical FPGA and ASIC work
remain deferred. No required external dependency is missing.

## Iteration 88: semantic clock provenance

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration88/`.

Pre-FAME discovery now follows clock outputs through concrete nested and sibling
instances. Dependency keys distinguish a parent instance pin from its child's
port, and input dependencies resolve lazily. Clock provenance also follows
exact one-bit `asUInt`/`asClock` casts and one-bit `bits(..., 0, 0)` identities
through transparent IO cells. It never follows a register's next-state driver,
invents a clock from a data input, or assumes all Rocket clocks share a domain.
Generated/gated/undriven/cyclic clocks, opaque cells, distinct state clock
domains and forwarded clocks outside the state domain still reject. Existing
manifest and boundary schemas and the CPU runtime whitelist are unchanged.

All 13 Scala inventory tests pass. The new
`ForwardedClockInventoryFixture` passes native VCS metasim capture and five
fresh ordinary RTL VCS restores/replays at actual fixture cuts C=0, 5, 22, 24
and 26. Each restores and reads back all 22 words / 15 semantic entries before
any edge. All 108 captured continuation samples compare all 13 outputs at
their original labels. Native capture observes 37 actual DUT edges; the clock
bridge reports 38, and the independent counter/input checks preserve that
distinction. These are fixture checks, not Rocket checkpoint cuts.

Five actual fixture images with truncation, checksum corruption, an incompatible
build and missing/unknown state owners reject before publishing `restore.txt`
or `replay.sv`. Four native loader cases reject missing handles, wrong widths,
malformed rows and incomplete word sets before any deposit. After complete
zero-edge readback, actual stored `a.saved` corruption first diverges on
`io_left` at fixture C=26; the native process exits nonzero and acknowledges
zero edges. The existing valid trace corruption case still first diverges on
`io_respData` at C=29. Exact artifacts are in `forwarded-verified-native/`,
including each `.rtlckpt`, `.trace`, readback/replay bench, native executable,
build/run log and waveform.

Reproduce from the Chipyard root with the pinned native VCS environment:

```sh
source env.sh && source sims/firesim/env.sh
export JAVA_TOOL_OPTIONS="-Xmx8G -Xss8M"
source automations/checkpoint_loop/vcs-env.sh
make -C sims/firesim/sim testOnly FIRESIM_SBT_PROJECT=midas SCALA_TEST=midas.checkpoint.SemanticStateInventorySpec
python -m tools.checkpoint_formats.tests.verify_semantic_vcs \
  --forwarded-clocks \
  --build automations/checkpoint_loop/runs/m11-iteration88/forwarded-bitcast-build \
  --out automations/checkpoint_loop/runs/m11-iteration88/forwarded-verified-native
```

Exact-recipe complete ChipTop discovery now reaches and explicitly rejects
`FireSim.chiptop0.system.coh_wrapper.l2.inclusive_cache_bank_sched.directory.cc_dir_0`
with `read=1, write=1` and a readwrite port. No partial semantic artifacts are
published. Retain its actual pre-FAME FIRRTL, annotations, recipe settings,
compiler command, source hashes and rejection under
`rocket-semantic-final-inventory/`. Clock alias support does not establish
complete memory-pipeline ownership or multi-clock replay. Reproduce discovery:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration88/verify-rocket-semantic-final-rejection.py
```

`rocket-semantic-memory-obligations.json` separately traverses the selected
original IR hierarchy and checks every concrete raw register/memory
declaration. It records 1,488 instances, 7,734 raw registers and 500 logical
memories / 310,493 words; 404 memories require read/readwrite pipeline ownership.
It also identifies six opaque `plusarg_reader` instances whose ownership remains
pending. These totals exclude implicit pipeline/opaque state and are diagnostic,
not a semantic manifest or complete state audit. The executable diagnostic is
`PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration88/audit-semantic-memory-obligations.py`.

Both full exact-recipe default/buffered native VCS controls pass at
C=3,329,794, with all four complete hart traces and independently decoded
workload/store labels matching the uninterrupted reference. Workload SHA256
remains `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The retained invocation is `rocket-controls/invocation-8mdtqxuy/`; its native
build binds 297 inputs / 58 translation units. All six complete generated
source/header/inventory files match the previous exact recipe build. All
221 Python tests and eight preserved native regression checks pass, including
M2/M3 metasim/ordinary RTL, 52 widget, 18 UART, 30 blockdev and 96 heartbeat
continuations and the existing FCFS Make/generator guards. Native CPU
preflight/save/restore still reject incomplete runtime ownership before any
partial image is published. Reproduce the full controls into a new retained
invocation and independently audit the selected original run:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration88/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration87/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls \
  --summary automations/checkpoint_loop/runs/m11-iteration88/rocket-controls/invocation-8mdtqxuy/summary.json
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration88/verify-evidence.py
```

`summary.json`, `selected-evidence.json`, `native-input-archives.json`,
`artifact-manifest.json`, `executed-native-commands.json` and
`verification-commands.json` retain exact scope and commands. The latter also
runs the selected ordinary RTL VCS executable in a fresh process, preserving
its original images, traces, binaries and waveforms. Regression commands/results
are under `regression-complete/`. Controller checkpoints FireSim
`aa143ccc404eb97faff3a23249e2d38027a6d969` and Chipyard
`c9b10d3634173bdd010df5092efcdff81ad83381` were published in that order with
confirmed remote tips. Local remote-tracking ref updates hit read-only Git
metadata; the remote pushes succeeded. No local staging or commits.

Complete CPU Level-1 runtime ownership/fresh continuation and independent
Level-2 synchronous-memory/readwrite pipelines, complete multi-clock inventory,
capture/readback/replay, all required active-workload cuts and CPU image/fault
cases remain pending. No external dependency is missing. Physical FPGA and
ASIC work remain deferred.

## Iteration 87: reproducible exact-recipe native controls

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration87/`.

The previous loop verification failed before running either control. Its Make
call reused the existing executable and replaced `rocket-vcs-build.log` with
an up-to-date-build log containing no VCS command. The subsequent native build
recorder correctly rejected that log. The failed log is retained as
`previous-verification.log`; `actual-noop-build-rejection.json` records its
rejection by the maintained native invocation validator.

`VCS_FORCE_REBUILD=1` now adds a phony prerequisite at both the outer FireSim
Make target and the recursive native VCS target. `cpu_recipe.native_build_command`
requests this explicitly for VCS checks. It retains `-full64`, `-Mupdate` and
all exact recipe settings above. It changes no source timestamps and forces
the native invocation without forcing target elaboration. Ordinary builds
retain their existing caching behavior. A real two-layer Make regression with
a mock compiler proves repeated forced rebuilds and unchanged-source caching;
this mock test is explicitly separate from licensed native VCS evidence.

The maintained launcher is
`tools/checkpoint_formats/tests/verify_rocket_controls_vcs.py`. Each invocation
gets its own build directory, executable, logs, actual process IDs, commands,
full 16-GiB controls and complete four-hart traces. `cpu_native.py` binds 297
native inputs and 58 host translation units, including actual compiler `.d`
dependencies, generated RTL/inventory, the static FESVR archive, compiler
executables, VCS executable and linked shared libraries. Successful Make logs
must contain exactly one executed VCS command for the selected executable.
No-op, failed, ambiguous, wrong-release, wrong-mode and wrong-output logs
reject. No CPU checkpoint profile is enabled.

Both exact-recipe native builds and all five full four-hart controls pass at
target count 3,329,794: two independently rebuilt default/buffered pairs and
the frequent-heartbeat control. Every full hart trace and independently decoded
phase/completion/failure/HTIF store label matches the uninterrupted reference.
The frequent control retains 202 actual clock samples from C=16,459 through
3,322,351. Workload ELF SHA256 is
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The independent maintained control audit passes. All 221 Python tests, full M2/M3 native VCS
metasim and ordinary RTL checks, 52 existing widget continuations, UART's 18,
blockdev's 30, heartbeat's 96 native/VCS continuations and eight FCFS Make/four
generator guards have passed. Earlier iteration-84/85 evidence passes with
its original `cpu_recipe.py` bound to an archived snapshot and pinned Git
object. It remains historical evidence.

Reproduce both complete controls from the Chipyard root. Repeated invocations
retain earlier build and runtime artifacts:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration87/reusable-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration87/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

The selected initial immutable invocation is
`reusable-controls/invocation-yq4cdng6/`. Its passing independent audit command is:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.audit_rocket_controls \
  --summary automations/checkpoint_loop/runs/m11-iteration87/reusable-controls/invocation-yq4cdng6/summary.json
```

This checks complete generated inventory, every native input, actual argv and
process completion, full instruction traces and independently decoded workload
phase/completion/failure/HTIF stores at their original CPU-print labels. These
labels are workload controls, not checkpoint-cut target-cycle evidence.
No early/warmed/outstanding/late CPU checkpoint cut has passed. Complete
runtime ownership, fresh-process Level-1 continuation and independent
multi-clock Level-2 capture, zero-edge readback and finite replay remain pending.

Fresh current-source ChipTop discovery still rejects
`FireSim.chiptop0.system.bdev_clock`, with no partial semantic outputs. Native
CPU preflight/save/restore still reject incomplete runtime ownership before
partial checkpoint publication. Required CPU malformed/incompatible/incomplete
image validation and actual semantic first-divergence corruption cases remain
pending. The new build-log rejection cases are infrastructure checks.

`summary.json`, `selected-evidence.json`, `native-input-archives.json` and
`artifact-manifest.json` retain the exact selected artifacts and all 594 native
input bindings with archived original bytes. The combined saved evidence check
uses the selected immutable invocation independently of later `latest.json`
updates. Reproduce the remaining complete native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration87/run-rocket-polling-control.py
python automations/checkpoint_loop/runs/m11-iteration87/run-regressions.py
python -m automations.checkpoint_loop.runs.m11-iteration87.verify-evidence
```

Each nested VCS shell independently sources `vcs-env.sh` last. Existing
controller commits FireSim `06d8dd43b2162fdf943c255167404889d8afd95c` and then
Chipyard `bc3878be2bf298af6217dc7db1c2383c871cc70a` were published with confirmed
remote tips. Plans/environment inputs/indexes/heads are preserved; no local
staging/commits or required external dependency failure.

## Iteration 86: heartbeat host ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration86/`.

`firesim.widget.heartbeat.v1` supports completed, unpoisoned calls before
`finish()` with explicit `+heartbeat-checkpoint-buffered`. The payload owns
`trip_count`, `last_cycle`, sticky `has_timed_out`, the signed 64-bit start epoch
and every `(target count, signed elapsed seconds)` log sample. Configuration
binds `polling_interval`, `ignore_heartbeat` and the complete clock host
configuration: actual Rocket MMIO addresses 1088 through 1108. Generated
clock counters/latches and transport queues remain separate owners. A fresh
process may choose a new `+heartbeat-output` destination; construction and
restore leave its existing bytes untouched, and successful `finish()` publishes
the full log including the restored prefix. Default live-file mode rejects
checkpointing. Finished, suspended/reentrant and interrupted calls reject.
Parse, consistency checks and allocations precede all restore mutations.
The CPU profile/whitelist and independent Level-2 schemas remain unchanged.

`heartbeat-native/latest.json` selects `native-wshv6rpb/summary.json`.
Native ASan/UBSan and VCS DPI each pass 48 fresh continuations across all 16
cuts in three scenarios: interval two with termination enabled/ignored, and
interval zero polling every call. The independent oracle checks every state
byte before the first edge, full final state, every MMIO operation/termination
result at its original **fixture** boundary, and all published CSV bytes.
Cuts cover startup, pre-poll counts, 64-bit cycle progress, no-progress timeout,
sticky timeout and late samples. Test-only wall time also steps backwards;
the saved signed diagnostic timestamps survive independently of termination.
Production wall-clock timestamps remain diagnostic and may reflect restore
downtime; target behavior depends only on polling/observed cycle state.

Each backend passes 772 malformed/incompatible/incomplete/lifecycle assertions
without partial owner mutation or MMIO. Checks bind all clock addresses,
interval/partition settings and reject missing rows, bad counters/epochs/flags,
inconsistent timeout/history, live logs, reentrancy and interrupted operations.
Structurally valid actual polling-counter corruption first fails
`heartbeat_poll` at fixture C=107, operation 1; no cycle read, termination
result or next operation occurs. All positive readbacks/traces are re-audited
after negative cases. These are host component checks, not Rocket target-cycle
cuts, complete `.fsckpt` continuation or semantic CPU replay acceptance.

Run from the Chipyard root (new retained component directory per invocation):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_heartbeat_checkpoint_vcs \
  --rocket-header automations/checkpoint_loop/runs/m11-iteration85/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h \
  --out automations/checkpoint_loop/runs/m11-iteration86/heartbeat-native
```

The exact-recipe current native rebuild links the heartbeat adapter, binds 207
actual inputs and 58 host translation units, and uses the pinned native
VCS/GCC/G++ settings above. Full default/buffered four-hart controls pass at
target count 3,329,794, with all four complete traces and decoded phase,
completion, failure, retired-store and HTIF labels matching the previous
uninterrupted control. A third full run through `run-rocket-polling-control.py`
uses `+heartbeat-polling-interval=1024 +partitioned=1`, exercising real clock
MMIO with timeout checks disabled during boot stalls. It also passes at target
count 3,329,794 and captures 202 actual clock samples from C=16,459 through
3,322,351. Every full hart trace and decoded workload/store label matches the
same uninterrupted reference. Physical host timing differs; sampled target
labels remain identical. Workload ELF SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The earlier controls retain the default interval 1,000,000 and correctly emit
header-only heartbeat logs for this workload. All 219 Python tests, full M2/M3 VCS metasim/ordinary RTL,
52 existing widget continuations, current UART/blockdev native/VCS component
checks and eight FCFS Make/four generator guards pass. All seven executable
checks/results are `regression-commands.json` / `regression-results.json`.
Historical iteration-84/85 evidence remains independently audited using
archived original heartbeat sources bound to exact pinned FireSim Git objects;
it does not substitute for current native source binding.
Fresh current-source ChipTop discovery still rejects `bdev_clock`, publishing
no partial semantic manifest/ordinary RTL. Rebuilt CPU preflight/save/restore
still reject incomplete runtime ownership without partial images.

The initial control wrapper incorrectly asserted a heartbeat sample at the
legacy interval. Both full native runs passed; the corrected complete audit
passes using the exact executed command metadata and archived launcher
`run-rocket-controls.initial.py`. Initial diagnostics remain in
`rocket-controls.log` and the passing re-audit is
`rocket-controls-audit-retry.log`. No native run was shortened or skipped.

Reproduce complete exact-recipe native VCS controls and the regression scope
from the Chipyard root (no FPGA build):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration86/run-rocket-controls.py
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration86/run-rocket-polling-control.py
python automations/checkpoint_loop/runs/m11-iteration86/run-regressions.py
```

Every nested VCS shell independently sources both environments and
`vcs-env.sh` last. `rocket-native-commands.json`, `rocket-polling-commands.json`
and the component `commands.json` retain executed argv, logs and results.
`selected-evidence.json` selects complete current artifacts;
`artifact-manifest.json` lists generated artifacts by full path and hash.
`summary.json` preserves both CPU levels as incomplete. Independently audit:

```sh
python -m automations.checkpoint_loop.runs.m11-iteration86.verify-evidence
```

The reusable check binds current native sources, generated declarations,
every component readback/transaction, complete CPU controls, preserved
regressions, explicit runtime/semantic rejection, historical source objects
and publication/protected-input/controller ancestry. Raw index/HEAD bytes
are separately checked only at implementation-turn end, preserving the loop
controller's next staging/commit. Existing controller commits were published
FireSim first (`4e564603726d151e0a0ad020b13259148297ad01`), then Chipyard
(`5577b7b9288d77512d093e45bf3ddcac50478d75`), with confirmed remote tips.
No new commits/staging, protected plan/environment edits or external dependency
failure. Complete CPU restore/replay and all required active cuts remain pending.
Complete run-loop, TSI/FESVR, TracerV and remaining owners, coherent CPU cuts,
fresh full Level-1 restores and independent multi-clock semantic CPU
capture/restore/finite replay remain pending.

## Iteration 85: UART ownership and reusable evidence

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration85/`.

`firesim.widget.uart.v1` supports completed, unpoisoned host calls before
`finish()` with explicit `+uart-checkpoint-file0`, `+uart-in0=<regular-file>`
and `+uart-out0=<destination>`. The constructor owns every input byte; the
image binds those bytes, the UART index and all six actual Rocket MMIO
addresses (1056 through 1076). It captures the entire input cursor, binary
output prefix, both data bytes and all four handshake flags. Active/poisoned
call state and finished lifecycle are rejected rather than omitted. Output
stays in owned memory until successful `finish()`, so construction, validation
and restore do not overwrite an existing destination. A fresh process may
select a new output destination but must supply the identical input bytes.
Default stdin/signals, PTYs and ordinary file descriptors explicitly reject
checkpointing. No CPU whitelist or semantic schema is extended.

`uart-native/latest.json` selects the retained component summary. Native
ASan/UBSan and VCS DPI each pass all nine cuts in independent processes,
including startup, binary input/output and EOF. An independent Python oracle
compares every state byte before the first edge, full final readback, every
MMIO transaction with its original **fixture** label, and the complete output
including its restored prefix. Each backend passes 723 rejection assertions
without owner/MMIO/destination mutation. Structurally valid actual cursor
corruption first fails `uart_in_bits` at fixture C=128, operation 4; no input
valid acknowledgement or operation 5 is issued. Positive raw traces are
rechecked after all negative cases. These checks establish the host component,
not Rocket CPU `.fsckpt` or Level-2 semantic replay acceptance.

Run from the Chipyard root; each invocation preserves previous component runs:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_uart_checkpoint_vcs \
  --rocket-header automations/checkpoint_loop/runs/m11-iteration85/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h \
  --out automations/checkpoint_loop/runs/m11-iteration85/uart-native
```

The exact-recipe native VCS rebuild links the adapter and retains the settings
above, full 16-GiB functional backing, GCC/G++ 13.3 and 58 actual host translation
units. `rocket-build-identity.json` binds 207 current native inputs, including
actual compiler dependencies. Two complete four-hart workload controls, with
default and explicit buffered UART modes, independently pass at target count
3,329,794. Every complete hart trace matches the prior uninterrupted control
(37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes), as do independently
decoded phase/completion/failure/HTIF store and CPU-print labels. The generated
RTL, compared constant headers and complete simulator inventory match too.
These are uninterrupted controls; all four required CPU checkpoint cuts and
fresh CPU restore comparisons remain pending. Workload ELF SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Full M2/M3 metasim/ordinary RTL VCS, 52 existing widget continuations, all 219
Python tests and eight FCFS Make/four generator guards pass. Fresh exact-source
ChipTop discovery still rejects `FireSim.chiptop0.system.bdev_clock`, emitting
no partial semantic manifest/clean RTL. Fresh native CPU preflight/save/restore
requests still reject unsupported runtime ownership without publishing an
incomplete image. Full CPU cuts, fresh Level-1 continuation, independent
multi-clock semantic capture, fresh ordinary RTL zero-edge readback/replay and
CPU-level image/corruption tests remain pending.

The initial buffered post-run audit lacked `command.json`; the full native
run had passed. The executed launcher is retained as
`run-buffered-rocket-control.initial.py`. Command metadata was reconstructed
from that exact launcher, and the independent decoder/full trace comparison
was rerun against the complete finished run. Initial diagnostics and the
passing `rocket-buffered-control-audit-retry.log` are retained; no workload
was shortened or reported passing without actual execution. The interim
combined audit also correctly rejected while the buffered summary was pending.
The completed reusable audit checks all artifacts after both controls finish.

The previous verification failure was an old Git index/HEAD snapshot compared
after the controller's next checkpoint. Historical logs remain intact. The
retained-evidence audit now binds old UART sources to exact archived bytes and
pinned Git objects; current native evidence separately binds current sources.
The reusable check validates immutable protected inputs and controller
ancestry. `verify-protected-turn.py` additionally checks raw index/HEAD bytes
at turn end. See [evidence-lifecycle.md](evidence-lifecycle.md).

Executable native controls (no FPGA build):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration85/run-rocket-control.py
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration85/record-rocket-build.py
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration85/run-buffered-rocket-control.py
```

Independent saved-evidence verification:

```sh
python -m automations.checkpoint_loop.runs.m11-iteration85.verify-evidence
```

## Iteration 84: block-device host ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration84/`.

Added `firesim.widget.blockdev.v1` for completed host calls with a private
in-memory disk, including the actual workload's `+blkdev-in-mem0=128`, and for a
disconnected device. The disk now has an explicit owned, initially zeroed byte
buffer behind `fmemopen`; both memory and external FILE streams close at
destruction. The adapter binds all 26 generated MMIO addresses, the actual one
tracker/24-bit latency configuration, sector geometry and runtime latencies.
It captures initialization, response-pending status, ordered request/data/read
response/ack queues, every tracker offset/count/size and all 1,024 tracker data
words, all 65,536 disk bytes and the logical FILE position. FILE buffering is
flushed at the completed-call boundary; restore reconstructs an independent
stream at the captured position without MMIO or target advancement.

Decode and allocation precede all restore mutation. Invalid booleans, lengths,
tags, ranges, tracker shapes, pending flags, lifecycle contradictions,
configuration mismatches and incomplete disk bytes reject. Every public host
operation guards suspended/reentrant cuts and poisons interrupted calls.
External disk paths, debug logs and failed/EOF FILE state explicitly reject;
they need external ownership adapters. No CPU runtime whitelist is extended.

`blockdev-native/latest.json` selects the final component run under
`blockdev-native/native-xb8o3fpu/`. ASan/UBSan native execution and native VCS
DPI each terminate the source and independently restore all 15 cuts in fresh
processes. An independent Python oracle checks every owner byte, including
inactive tracker words and the full disk; native VCS reports readback at zero
edges. All MMIO operations, 128 actual read response words and two write
acknowledgements retain their fixture release labels. Cuts include data queued
before a request, queued requests, partial writes with 5/21 beats retained,
stalled acks and partially drained read responses. Each backend passes 1,639
negative assertions, including malformed/incompatible payloads, unsupported
external modes and interrupted calls, without partial owner mutation or MMIO.
A separate zero-edge roundtrip varies every disk byte, including its first and
last bytes, at a legal end-of-file position, checking libc reconstruction.
The final evidence audit also rechecks every positive raw continuation after
the negatives. It caught the initial negative fixture overwriting cut 5's
trace; the corrected suite isolates that fixture and retains all 15 traces.
Earlier diagnostics remain under their original run directories.

Actual partial-write tracker corruption passes structural loading, then fails
at the first changed `bdev_rresp_data_lower` write at **fixture** cycle 142,
operation 6, exit 1; no operation 7 is issued. These are host component fixtures,
not Rocket target-cycle cuts, CPU `.fsckpt` acceptance, or Level-2 semantic
replay. The complete Rocket run loop, TSI/FESVR, UART, four TracerV sinks and
heartbeat owners, coherent cuts, fresh full CPU restores and CPU image/fault
checks still remain. Independent current-source ChipTop discovery continues to
reject `FireSim.chiptop0.system.bdev_clock`, emitting no partial semantic
manifest or ordinary CPU RTL. The six clocks, async reset and original CPU
storage require a separate versioned semantic adapter.

Executable component check from the Chipyard root (creates a new run directory):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_blockdev_checkpoint_vcs \
  --rocket-header automations/checkpoint_loop/runs/m11-iteration84/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h \
  --out automations/checkpoint_loop/runs/m11-iteration84/blockdev-native
```

The exact-recipe build and complete four-hart control are reproducible through
`run-rocket-control.py`; its `rocket-native-commands.json` records each native
build/runtime/audit argv and result. Every VCS shell sources both environments,
then `vcs-env.sh` last. The source-bound recipe helper retains
all settings above and builds no bitstream. Native build artifacts use a new
iteration-84 directory, preserving prior controls.

The current exact-recipe build and full 16-GiB workload pass at C=3,329,794.
All four complete TracerV files match iteration 83 byte-for-byte (37,582,346 /
49,976,156 / 50,391,641 / 50,189,006 bytes). Independent retired-store decoding
confirms phases 1/2/3/4, completion 1, failure 0 on every hart and the actual
HTIF PASS store; every audited CPU-print cycle field also matches the prior
control. Workload ELF SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Generated RTL, both compared constant headers and the complete generated-state
manifest retain their original bytes. `rocket-build-identity.json` binds 130
current input files and 58 native host translation units, GCC/G++ 13.3, the
normal executable and the newly linked blockdev methods. These are workload
and build controls, not restored CPU execution or complete boundary replay.

Full-path selection and executable checks are `selected-evidence.json`,
`verification-commands.json`, `verify-evidence.py`, `summary.json` and
`artifact-manifest.json`. The independent evidence checker re-audits complete
generated ownership, current source hashes, every component cut's full disk
and tracker words, all retained raw MMIO traces, native process statuses, CPU
controls, explicit runtime/semantic rejection, regressions and protected inputs.

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration84/run-rocket-control.py
```

Run the independent saved-evidence audit without rerunning the workload:

```sh
python -m automations.checkpoint_loop.runs.m11-iteration84.verify-evidence
```

## Iteration 83: exact generated RTL ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration83/`.

The exact recipe now emits its complete generated RTL manifest and reference.
The metasim-only `plusarg_reader` adapter owns `myplus`, including its runtime
value rather than assuming `DEFAULT`. Each instance binds the exact inline
Verilog SHA256, WIDTH, DEFAULT and FORMAT; unknown models, ports and parameter
shapes still reject. This adapter describes the non-SYNTHESIS simulation model.
It does not add FPGA storage or change the target RTL. Level-2 IDs and the
FCFS runtime profile remain independent.

| Generated storage adapter | Entries | Words | Bits |
| --- | ---: | ---: | ---: |
| FIRRTL registers | 10,278 | 10,278 | 94,592 |
| FIRRTL memories | 742 | 435,116 | 20,899,468 |
| Emitter memory pipelines | 434 | 434 | 6,581 |
| Metasim plusarg registers | 7 | 7 | 193 |
| Metasim BUFGCE outputs | 3 | 3 | 3 |
| Total | 11,464 | 445,838 | 21,000,837 |

There are 2,292 generated instances. The seven plusarg registers belong to the
four cores' PlusArgTimeout instances, two UART transmit controls and the custom
boot pin. `rocket-generated-state-owners.json` also groups all storage by its
actual top-level owner, including the CPU-managed stream buffers, all four
TracerV bridges, TSI, blockdev, UART, FRFCFS/LLC, FAME and interconnect state.
This is generated RTL coverage; 16 GiB functional backing memory, native host
queues, MMIO/transport, scheduler and driver state still need complete owners.

`rocket-generated-independent-audit.json` independently checks emitted register
and memory declarations, including parameterized external instances, and passes
eight mutations of the actual Rocket artifacts: missing storage/owner, unbound
default, altered source, changed bound format, changed emitted width, an actual
extra register and missing model. Original files retain their hashes. These are
inventory rejection checks, not CPU checkpoint-image loader acceptance.

`plusarg-native/` contains separate capture and fresh ordinary VCS processes
using the compiler-produced two-owner inventory. Nondefault native values are
captured, conflicting startup plusargs are replaced, and both complete words
(33 bits) read back before any edge and match four diagnostic boundaries.
An actual storage-bit fault first diverges at boundary 0, edges=0, exit 1.
The initial diagnostic found VCS returning zero for `$fatal`; the final check
uses the existing DPI failure function and verifies nonzero native status.
This microtest establishes the external adapter only, not clean CPU RTL replay.

Executable native adapter verification, from the Chipyard root (each invocation
keeps prior evidence and creates a fresh output directory):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_plusarg_inventory_vcs \
  --inventory automations/checkpoint_loop/runs/m11-iteration83/scala-artifacts/plusarg-inventory.json \
  --reference automations/checkpoint_loop/runs/m11-iteration83/scala-artifacts/plusarg-reference.fir \
  --out automations/checkpoint_loop/runs/m11-iteration83/plusarg-native
```

All 16 compiler inventory tests and 219 Python tests pass. Fresh complete M2
and M3 native VCS metasim/ordinary RTL regressions pass, retaining their five
cuts/22-word readback/C=29 divergence and 717 transport edges/23 advances/six
captures/242 boundary samples/eight invalid reads respectively. Eight FCFS Make
and four generator guards pass without changing its compiled inventory.

### Native Rocket execution and generated-state samples

The exact recipe's native VCS build with read-only probes passes. The full
16-GiB, four-hart workload passes at 3,329,794 fastest-clock target cycles.
`rocket-workload-audit.json` independently decodes all harts' phase 1/2/3/4,
completion=1, failure=0 and the real HTIF PASS store from native execution.
The workload ELF remains SHA256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Every sample in `rocket-generated-probe/generated-state.jsonl` contains all
445,838 generated words at one settled host falling edge. The sample's actual
`ClockBridgeModule_0.tCycleFastest` value supplies its target-count label:

| Diagnostic sample | Target count | Host sample | Valid D-cache lines, harts 0/1/2/3 | Harts waiting for a cached grant | Host reads in flight |
| --- | ---: | ---: | --- | --- | ---: |
| Startup/early execution | 50,000 | 467,603 | 313 / 1 / 1 / 1 | 0 | 0 |
| Warmed-cache execution | 850,000 | 3,421,115 | 498 / 507 / 501 / 501 | 0, 1, 2 | 0 |
| Outstanding workload memory | 1,013,847 | 3,737,220 | 511 / 511 / 510 / 510 | 1, 2, 3 | 1 |
| Late execution | 3,200,000 | 8,002,559 | 511 / 512 / 510 / 512 | none | 0 |

`rocket-active-sample-audit.json` binds the actual DCache/ClientMetadata sources
and lowered bit extraction: coherence state is bits 24:23 of each of eight
64-word tag banks, and Nothing=0. `cached_grant_wait` is set when an actual
cached TileLink request fires and cleared by the final grant beat. All four
saved PC payloads at the outstanding sample are in the workload's memory loop.
These observations establish active generated state. They do not certify an
atomic simulator/host cut or original multi-clock semantic state at those
labels; all four required checkpoint/restore cut tests remain pending.

`rocket-trace-comparison.json` compares all four complete TracerV files against
the iteration-82 uninterrupted control: 37,582,346 / 49,976,156 / 50,391,641 /
50,189,006 bytes match respectively. Independently decoded phase, completion,
failure and HTIF store cycle fields also match. This establishes that the
read-only probes preserve the recorded instruction behavior and timing. It is
not restored execution or complete original-DUT boundary replay.

Current native artifacts are `rocket-generated-summary.json`,
`rocket-generated-independent-audit.json`, `rocket-build-identity.json` (145
bound inputs, 58 actual host translation units and GCC/G++ 13.3),
`rocket-native-commands.json` (exact build, full workload and audit argv/results),
`rocket-generated-runtime/{command.json,exit.json,native-vcs.log,TRACEFILE-C0..C3}`
and the two sample/trace audits above. The emitted RTL and all three headers
are byte-identical to iteration 82 (`rocket-baseline-build-byte-comparison.json`).

The following reproduces the native build/control/probe check using this run's
diagnostic build/output directory. Exact individual VCS commands and all recipe
settings are also recorded in `rocket-native-commands.json`:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration83/run-rocket-generated.py
```

Fresh native unsupported-runtime checks create their own output directory:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration83/verify-rocket-runtime-rejection.py
```

Preflight/save/restore each exits 1 before driver initialization and publishes
no partial checkpoint. Actual CPU image decoding remains unsupported. A fresh
exact-source semantic compiler request also rejects
`FireSim.chiptop0.system.bdev_clock` and emits no partial semantic manifest or
clean CPU RTL (`rocket-semantic-inventory/{command.json,summary.json,native-compiler.log}`).
Complete Level-1 fresh-process continuation, independent Level-2 zero-edge CPU
readback/finite boundary replay, CPU image rejection and first semantic
divergence remain required. No CPU recipe/level is verified.

## Retained iteration 82 evidence

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/`.

Workload ELF SHA256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

* `rocket-recipe.json`: exact YAML bytes/hash, raw and resolved settings,
  executable complete-inventory Make commands.
* `rocket-elaboration-audit.json`: source-bound high-form elaboration with all
  four RocketTile instance paths, six ChipTop clock inputs, async reset and
  original external modules. This is not a complete lowered state manifest.
* `rocket-native-owners.json`: actual header's three constructor passes and
  the separately audited heartbeat construction. State adapters remain pending.
* `rocket-build-identity.json`: emitted baseline RTL, headers, concrete
  blackboxes, executable and tool/setup hashes. No checkpoint profile enabled.
* `rocket-verilog-cache.log`: complete generated inventory rejects the actual
  unadapted `plusarg_reader` inside core 0's `PlusArgTimeout`. Earlier writable
  cache setup failure is preserved in `rocket-verilog.log`.
* `rocket-semantic-inventory-retry.log`: independent pre-FAME ChipTop inventory
  rejects `FireSim.chiptop0.system.bdev_clock`; no semantic manifest, checkpoint
  image or clean CPU RTL acceptance is claimed. The initial missing output
  directory diagnostic remains in `rocket-semantic-inventory.log`.
* `rocket-baseline-vcs-build-retry.log`: exact regular recipe VCS build passes.
  The earlier include-path error is preserved in `rocket-baseline-vcs-build.log`;
  installed `libdwarf.h` and its library were found in the existing Conda env.
* `workload/{summary.json,commands.json,rocket-quad.riscv}`: RV64IMA/Zicsr
  bare-metal program, source/ELF hashes, native compiler and Spike commands.
  Each of four harts checks 64 KiB through early stores, sequential reads,
  three rounds of cache-line-strided read/write work and late verification.
  All four must complete before HTIF PASS. Fault ELFs corrupt real memory on
  harts 0/1/2/3 and return failure codes 1/2/4/8 respectively in Spike.
* `rocket-baseline-runtime-full-retry/command.json`: executable native VCS
  workload command, full 16 GiB functional backing memory, native output and
  four TracerV streams. PASS after 3,329,794 fastest-clock target cycles;
  native exit 0. Initial wrong-unit memory and argument-position diagnostics remain
  in the separate `rocket-baseline-runtime*` directories.
* `rocket-baseline-audit.json`: independent decoding of actual retired SD
  instructions and their source-register values. Every hart wrote phases
  1/2/3/4, completion 1 and failure 0; hart 0 actually stored HTIF PASS 1.
  Per-hart print labels are recorded separately from checkpoint target-cycle
  labels. This audit establishes workload execution, not checkpoint replay.
* `rocket-fcfs-profile-rejection.json`: the actual exact Rocket Make request
  rejects `FS_CHECKPOINT_PROFILE=fcfs-fased-v1` before generation, preserving
  the baseline RTL/header/executable bytes. This is a build preflight check;
  invalid CPU-image loader rejection remains unverified.

## State ownership and remaining acceptance

The constructor order is master, loadmem, CPUManagedStreamWidget, peek-poke,
reset-pulse, blockdev, UART, FASED, four TracerV instances, TSI and clock.
`firesim_top_t` adds heartbeat after construction. The actual F2 configuration
has one functional-memory channel, rather than the FCFS profile's four. Audit
complete generated storage, FAME/channel/clock state, MMIO, full functional
memory and host timing independently for this configuration.

`firesim_top_t` currently inherits the unsupported checkpoint schema and lacks
incremental dispatch. Its termination/run-loop state, scheduler and base
lifecycle need explicit owners. TSI/FESVR needs loading flags, wait/step state,
loadmem and serial queues, HTIF state and suspended execution accounted for.
UART, blockdev, four trace sinks, CPU stream, heartbeat and FRFCFS/LLC model
state also require configuration-specific audit. The FCFS whitelist remains
restricted; constructor membership alone never certifies a driver adapter.

Iteration 83's source-bound `rocket-runtime-owner-audit.json` distinguishes
existing hooks from missing ones. CPUManagedStreamWidget already implements
`firesim.widget.cpu-managed-stream.v1`: its host drivers have no persistent
queue offsets, but initialization, stream parameters, suspended stream calls
and the actual CPU AXI transport still need native cut/restore validation.
FASED already has a host adapter for configuration, lifecycle, statistics,
histograms and range counters; its presence does not certify this FRFCFS/LLC
recipe or its one 16-GiB memory channel. Generic master/loadmem/peek-poke/reset/
clock hooks likewise require exact CPU configuration binding.

| Missing concrete runtime adapter | State that cannot be omitted |
| --- | --- |
| FireSim run loop | `terminated`, local exit/run-loop phase, scheduler credits/deadlines/callbacks, base lifecycle and completed-operation dispatch |
| TSI/FESVR | Wait/step/loading flags; loadmem and serial queues; inherited testchip/HTIF state; suspended `context_t` execution, which contains process-specific pointers and a ucontext or pthread |
| Blockdev integration / external modes | Private-memory/disconnected host hooks now pass native component checks; complete CPU atomic cut integration and external disk/log ownership remain pending |
| UART | Serial handshake data, handler/input positions, pending external bytes, global `specialchar` and endpoint/signal behavior |
| Four TracerV sinks | Cycle/trigger/clock state, file history and positions, tracker/mode state, stream identities and any suspended token buffer; draining streams affects target timing |
| Heartbeat | Poll/trip/last-cycle/timeout state, time origin, configuration and log history; it can terminate execution |

The audit hashes the actual generated header, reviewed driver implementations,
testchip inheritance and installed FESVR headers. It explicitly remains an
in-progress source audit. Native preflight/save/restore requests on the exact
Rocket binary still reject unsupported CPU runtime ownership and publish no
partial checkpoint; this is not malformed-image loader acceptance.

Proposed Level-2 boundary is the complete `FireSim.chiptop0`, containing all
four CPUs, caches and uncore. Its external memory/device/serial inputs must be
recorded at the actual boundary. Six named clock inputs include 500 MHz uncore
and 1000 MHz tile/memory clocks. Alias resolution, async reset, clock phase and
multiple-clock trace/replay require an explicit versioned adapter; do not force
them into the current single-clock semantic schema or omit crossing state.

No early/warmed/outstanding-memory/late checkpoint cut is verified yet. Phase
markers in the workload help select cuts but cannot establish actual cache or
in-flight state. Complete fresh-process Level-1 continuation, independent
Level-2 zero-edge readback/replay, all sampled timing comparisons, atomic
invalid-image/build/owner rejections and first-divergence semantic corruption
remain required. No `.fsckpt`, `.rtlckpt` or boundary `.trace` is claimed here.

## Executable native regressions

Run from the Chipyard root. Source `vcs-env.sh` last in every VCS shell.

```sh
source env.sh && source sims/firesim/env.sh
export COURSIER_CACHE="$PWD/automations/checkpoint_loop/runs/m11-iteration82/coursier-cache"
export TMPDIR="$PWD/automations/checkpoint_loop/runs/m11-iteration82/tmp-semantic"
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
source automations/checkpoint_loop/vcs-env.sh
VCS_FLAGS=-Mupdate python -m tools.checkpoint_formats.tests.verify_semantic_vcs \
  --build automations/checkpoint_loop/runs/m11-iteration82/semantic-build \
  --out automations/checkpoint_loop/runs/m11-iteration82/semantic-regression-retry
```

M2 passes all five cuts, all 22 words, actual first divergence C=29 and four
loader rejections. M3's analogous `verify_banked_vcs` command uses `banked-build`,
`banked-regression` and `tmp-banked`; it passes 717 transport edges, 23 semantic
advances, six captures, 242 clean replay samples and eight invalid reads.
`assembly-destination-audit.json` checks all three newly requested JARs contain
the native generator/Golden Gate main classes. The Make helper now disables
sbt-assembly's stale destination cache and checks nonempty output before touch.
The observed zero-byte reused M2 build cache was repaired from the isolated,
native-validated JAR; `empty-cache-repair.json` records before/after bytes.

All 218 Python tests and the eight FCFS Make/four generator rejection checks
pass. Exact logs are `python-tests-final.log`, `fcfs-make-regression/summary.json`
and the two native regression directories. These regressions preserve earlier
support; they cannot substitute for CPU checkpoint acceptance.

The native Rocket baseline command can be rerun verbatim from
`rocket-baseline-runtime-full-retry/command.json`. Audit its actual output with:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.audit_rocket_baseline \
  --runtime automations/checkpoint_loop/runs/m11-iteration82/rocket-baseline-runtime-full-retry \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --out automations/checkpoint_loop/runs/m11-iteration82/rocket-baseline-audit.json
```

`verify-evidence.py` rechecks selected current-source native evidence and
protected inputs. `summary.json`, `verification-commands.json` and
`artifact-manifest.json` record the final in-progress result and full-path
recovery. No CPU checkpoint acceptance is inferred from the native baseline.
