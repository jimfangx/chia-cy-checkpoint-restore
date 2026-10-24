# Checkpointing progress

Delegation instruction from the user: the central implementation agent may use
as many subagents as needed within runtime capacity. All LLM/delegation and
follow-up requests and results must go through that central agent, using native
managed subagent tools. Workers request further help through the central agent;
do not launch independent Codex sessions, direct LLM API calls or detached Chia
LLM jobs. The central agent must collect results and wait for, or cancel and join,
all workers before its final JSON report. No delegated LLM work may outlive the
central turn: Chia uses that turn's completion to detect the end of the LLM call.
Preserve this instruction in subsequent progress updates.

Current user priority (October 23, 2026): actual AWS F2 FPGA capture and
FPGA-to-EDA checkpoint migration. Follow the current top of `plan_agent.md`
and [aws-f2-workflow.md](aws-f2-workflow.md). Reuse the four initialized manager YAMLs and the already configured AWS setup.
Build bitstreams on this server with ExternallyProvisioned localhost; do not
launch EC2 build hosts or build on EDA. Run a real single-node Rocket F2 workload, then implement/build/deploy complete
capture hardware and validate FPGA-produced Level-1/Level-2 images in fresh
EDA VCS, including finite replay, rolling recovery and sustained live RTL.
FPGA synthesis/image builds and physical acceptance are required. ASIC
mapping/formal/gate/power remain excluded. Standalone Shuttle is excluded.

Active milestone: `F2-rocket-checkpoint-migration`, iteration 195,
**in_progress**. Added an explicit diagnostic bank-generation hook after
production FPGA lowering. Its immutable pre-bank inventory, instrumented IR,
bank binding and descriptors are bound to the actual emitted RTL body.
Unknown annotation contracts, partial inventory roots, duplicate requests and
freezing a live capture transport reject. All **97 Scala / 290 checkpoint
Python / 40 loop tests** and the retained EDA bank/transport/host/FCFS
ASan/UBSan scope pass. The new compiler-path bank fixture passes **4,669**
EDA VCS checks at four complete cuts, continues through **1,025** functional
edges and stops first-word corruption frozen before acknowledgement. Native
localhost OOC synthesis of identical bytes uses **44 LUTs / 26 registers**.
Fresh exact-recipe bank compilation reaches this hook but **fails** the exact
adapter check for `AbstractClockGate_0`; no Rocket bank/image output is claimed.
The probe is non-deployable and is not added to manager recipes or stock Make
outputs. Complete physical/memory/host ownership, live transport/common-cut
integration, image P&R/AFI, actual FPGA capture and paired CPU live/rolling
acceptance remain pending. Reuse the iteration-194 checkpoint-build invocation.
See
[fpga-capture-transport.md](fpga-capture-transport.md).

On October 23 the
existing manager successfully launched one tagged `f2.6xlarge`, instance
`i-04b9cc3f81f16b61f`, in `us-west-2`, private IP `192.168.1.203`, using AMI
`ami-07a164f1a402ab274`. Its AWS tag is
`fsimcluster=checkpoint-f2-rocket-baseline-175`. The actual FPGA self-test
passed at **44,104,832 target cycles**, with slot 0 independently reporting
loaded/error-free `agfi-0c5eedfce0e568971`. Deployed driver/ELF hashes match
the saved bytes. Artifacts were collected, then scoped manager teardown
completed; AWS independently confirms **terminated**. No owned runtime
instance or native Vivado/Java build job remains. Full FPGA checkpoint
capture remains pending. See [aws-f2-bringup.md](aws-f2-bringup.md).
License recovery after the stopped iteration 175 is **verified**. EDA's
interactive `.zshrc` sources `/tools/flexlm/flexlm.sh`; the noninteractive
`bash -lc` path did not. `vcs-env.sh` now preserves inherited licenses and
sources that site helper when both license variables are empty (or an explicit
`CHECKPOINT_EDA_LICENSE_SETUP` override). Actual EDA VCS SP2 compilation and
simulation pass with `CHECKPOINT_CUT_PASS checks=82`. The fresh command includes
`-timescale=1ns/1ps`, needed because the testbench has an explicit timescale
while the component does not. New receipt, exact argv, source/log hashes and
native compile/runtime logs are under
`runs/aws-f2/iteration175/eda-license-confirmed-7rd4saf_/` (relative to the loop).
The old missing-license logs and initial timescale failure are retained.
No controller milestone/iteration was advanced manually. The original report
also listed directories as artifacts: future reports must list individual
nonempty files, not directories, as required by the controller artifact checks.
Full checkpoint-enabled image/capture support remains pending.
Retain the verified FCFS/component history and the original receipts below as
historical metasim/component evidence, not proof of FPGA capture.

Loop instruction: publish implementation checkpoint commits to GitHub, FireSim
first and then Chipyard. Follow [github-publication.md](github-publication.md)
and preserve this instruction when updating progress.

Iteration 176 independently re-audits the retained iteration-175 hardware run;
it does not claim another FPGA execution. New evidence is under
`automations/checkpoint_loop/runs/aws-f2/iteration176/`. The strengthened
`baseline-complete-audit.json` verifies all four nonempty native manager logs,
their actual disabled-metasim settings, task/farm and workload/result identity,
plus preservation of the exact CPU recipe and localhost build workspace.
All **14** offline evidence corruptions reject; **39** loop/config/inventory
tests pass. Fresh AWS access and scoped inventory succeed and still confirm
`i-04b9cc3f81f16b61f` terminated. Fresh EDA VCS SP2 compilation/simulation in
`cut-vcs/` passes all **82** coordinator checks with the recovered licenses.
Fresh HDK setup confirms native Vivado 2025.2, HDK `80b34d3`, shell `0x10212415`.
New `checkpoint-build/` configs retain ExternallyProvisioned `[localhost]`,
an invocation-local build directory, and no invented checkpoint AGFI.
Fresh local 16-owner coordinator synthesis passes for `xcvu47p-fsvh2892-2-e`
with **56 LUTs / 74 registers**; DCP, reports and exact Tcl are in `cut-vivado/`.
`summary.json` binds source snapshots and evidence hashes while preserving the
original remote paths. Final inventory confirms no owned live F2 instance or
native Vivado/Java job and no new AFI request. Existing controller checkpoints
were published FireSim first (`79f8dd18`), then Chipyard (`e535132d`); independent
remote tips agree. Chipyard's local tracking-ref update failed read-only after
the successful remote push; the controller owns subsequent commits/publication.
Full checkpoint-image synthesis/P&R, AFI creation and hardware capture remain
pending the complete state network, bridge and host-owner implementation.
Report individual nonempty files, including actual native manager logs and
`results-workload/.../uartlog`, instead of directories. Keep original
iteration-175 artifacts and failed-license receipts unchanged.

## Iteration 195: invoke generated banks from the production compiler

`--simulator-bank-probe` invokes `GeneratedStateBankAccess` after production
host/FPGA lowering, using a separate access clock and the complete root's
generated-state inventory. Only explicitly recognized compiler bookkeeping
bypasses storage-annotation translation; unknown annotations still reject.
Logical bank inputs and final emitted-state inventory remain distinct: the
latter additionally owns the bank response latch and emitter-renamed state.
All probe bindings say `deployable_capture_image=false` and require external
runtime ownership. Use an isolated Golden Gate `-td` under runs; there is no
stock recipe/Make switch that can contaminate an ordinary cached image.

The real compiler-path fixture retains injected host state and host-clock
wiring. Fresh EDA VCS SP2 checks every bank word at component cycles
**2 / 39 / 132 / 900**, invalid selectors/unfrozen requests, four stalled
response boundaries per read, frozen reset/clock pressure and continued
functional outputs through 1,025 edges. **4,669** checks / **21** requests
pass; deliberate word corruption stops at cycle 2, zero completed reads,
freeze asserted and no acknowledgement. Both runs retain full debug VCDs.
Native Vivado 2025.2 synthesizes identical bytes for the F2 part to 44 LUTs /
26 registers, estimated OOC WNS **+6.435 ns** / WHS **+0.049 ns** at 140 MHz;
external I/O is unconstrained. This is component evidence only.

The exact Rocket recipe freshly runs from retained high-level target inputs
and reaches the hook, then exits **1**: `no exact registered-enable clock-gate
adapter for AbstractClockGate_0`. Preserve that native compiler log and target
input hashes. The retained ordinary final reference has no instance of that
module; audit reachable definitions, physical BUFGCE/plusarg semantics and all
remaining annotation contracts before changing adapter admission. Do not
relax source checks or substitute the old abstract-gate probe for physical
state. No new checkpoint image, AFI request, runtime launch or FPGA checkpoint
was produced. Fresh AWS/localhost inventory finds no owned runtime instance or
remaining native Vivado/Java build job.

All 97 Scala / 290 Python / 40 loop tests and the complete retained EDA
bank/Widget/host/FCFS ASan/UBSan scope pass. The ordinary host-pipeline fixture
still passes 4,100 comparisons and rejects discarded circuitry at cycle 1.
Top MMIO/DMA passes 7,858 checks on the exact native synthesis inputs; the
independent EDA audit verifies source/generated/DCP identity, all four bank
cuts, the unsupported full-recipe trial, top evidence and 780 dense words.
Initial Scala syntax/fixture-construction/duplicate-request failures remain
in raw logs, followed by the full successful rerun. Managed worker startup
failed before any worker started; work remained central and no worker exists.
Existing controller checkpoints were pushed FireSim first (`31fd9c7b`), then
Chipyard (`c92da583`); independent remote tips agree. The successful Chipyard
remote push retains its local read-only tracking-ref error. No staging or local
commits; plans/conda/archive/history remain untouched. Commands, receipts and
remaining acceptance work: `runs/aws-f2/iteration195/summary.json` relative to
the loop. Complete image/driver, memory/host/common-cut ownership, four-hart
hardware captures, independent CPU zero-edge restores, finite/live comparison
and rolling hardware recovery remain pending.

## Iteration 194: preserve the production host compiler result

`GoldenGateCompilerPhase` now carries the post-mapping host-transform return
value into FPGA backend lowering and emission. Previously it executed that
compiler but reused the earlier simulator, losing injected circuitry and
clock wiring. The same production entry is exercised with a real added state
owner and host-clock sink, emitted keyword renaming, inventory opt-out
identity and a deliberately failing host transform. Inventory observes the
emitter's own prepared state instead of replaying its lowering passes.

`SIMULATOR_CHECKPOINT_INVENTORY` also emits `.simulator-emission.json`; Make
tracks that output. Its hashes bind the host-transformed/backend circuits,
actual emission-state serialization, generated manifest and **emitted RTL
body before blackbox resources are appended**. It retains
`scope=generated_rtl_only` / `external_runtime_required=true`. VerilogPrep's
instance-connector diagnostic serialization is not FIRRTL parser input; do not
silently parse/reconstruct it as another circuit or call it complete runtime
state. Full image/driver and external-resource binding remains future work.

New EDA VCS compares functional outputs against a public-input model across
1,025 host edges, repeated reset, width wraparound and 3,075 unrelated-clock
edges, retaining debug VCDs. The deliberately discarded-transform circuit
stops at cycle 1. Native Vivado 2025.2 synthesizes the same immutable generated
bytes for the F2 part: 12 LUTs / 16 registers, OOC estimated WNS +6.441 ns /
WHS +0.073 ns; external I/O is unconstrained. Initial test-fixture wiring,
width-text and diagnostic-parser failures remain in raw logs.

Fresh full Golden Gate compilation uses the exact Rocket target/platform
configuration with retained high-level target FIRRTL/annotation bytes, whose
hashes are preserved. All 11,466 generated entries / 618,254 transfer words /
2,293 instances are inventoried from actual final emission. This is ordinary
source compilation without semantic preservation or a capture binding, not a
fresh instrumented image, FPGA checkpoint or physical primitive mapping.
Native managed delegation failed at startup; all work was performed centrally.
Top MMIO/DMA passes 7,858 checks on exact native-synthesis inputs. Independent
EDA audits pass for complete immutable compiler inputs, emission hashes, native
DCP identity, top evidence and 780 dense public-input words. Scoped inventory
records no invocation runtime instance or native Vivado/Java job. The initial
EDA audit could not access excluded generated-src inputs; exact input snapshots
were copied beneath runs and independently hashed on EDA before the audit passed.
Existing controller checkpoints were pushed FireSim first (170a4e33), then
Chipyard (be1b6449); remote tips agree. The successful Chipyard push again
could not update its local read-only tracking ref; the raw error is retained.
Exact commands and evidence catalog: `runs/aws-f2/iteration194/summary.json`
relative to the loop. Plans remain read-only; no staging or local commits.

## Iteration 193: balanced generated-state readout

Module-local state selection now masks each unique selector and uses balanced
two-input match/data reductions instead of serial priority muxes. The 260-owner
dense fixture covers all widths 1..64 and three repeated children, retaining
nine OR stages at its root. Fresh EDA VCS SP2 passes **13,558 checks / 780
complete reads / 3,120 stalled response boundaries** at **2 / 39 / 132**, then
continues through 173 functional edges. Original RTL and a separate public-input
model check every word; invalid selectors return held zero/error, and deliberate
first-word corruption stops frozen. Full debug VCDs are retained. The independent
public-input auditor verifies all 780 words; four semantic-negative unit tests
cover input, membership, shape and payload corruption.

All **90 Scala / 290 checkpoint Python / 40 loop tests**, the full retained
EDA bank/transport/host/FCFS ASan/UBSan scope and the top's **7,858** MMIO/DMA
checks pass. An initial dense-reference compile failed because emission removed
unobserved original registers; original-only preservation fixes that oracle.
EDA sync also encountered a disappearing live Vivado scratch file. The helper
now excludes `.Xil` scratch while real rsync tests require DCPs/reports to
transfer. Both initial diagnostics remain immutable under this iteration's
`runs/`. All **15** native localhost OOC synthesis commands complete, including the
retained whole root (**711,231 LUTs / 107,319 registers / 64 DSPs / no block
RAM**). Its estimated setup WNS is **-0.287 ns** (72 failing
endpoints) and hold WHS is **-0.324 ns** (18,351 failing endpoints),
of **3,586,899** total. The whole root still fails estimated timing. External I/O
remains unconstrained and OOC clock-buffer locations unbound; full image timing
closure is not verified. The parent exits **0** and publishes a CRC-checked,
independently audited DCP after a parallel synthesis worker reports a Boost
interprocess `Bad file descriptor` shutdown exception. Its cause remains
unproven; the raw log and a separate diagnostic receipt preserve it.
The dense native component uses **14,176 LUTs / 8,579 registers**, estimated
WNS **+5.849 ns** / WHS **+0.073 ns** at 140 MHz (OOC, external I/O unconstrained).
Final independent EDA audits pass for complete source/inventory/DCP identity,
all 780 dense public-input words, retained receipt/semantic negatives and
computed-clock token corruptions. Fresh AWS/localhost inventory records no
invocation runtime instance and no remaining native Vivado/Java build job.
Exact commands and immutable receipts are cataloged in
`runs/aws-f2/iteration193/summary.json` relative to the loop.

Compared with the retained iteration-192 measurement, setup WNS improves from
**-0.916 ns** to **-0.287 ns**, with failing setup endpoints reduced from
**6,878** to **72**. The remaining worst setup path runs from L2
`mshrs_1/w_grantlast` to `sourceD/s3_bypass_data_REG_1` through 29 logic levels.
Address mapped-clock/placement timing during complete image integration.

The production exact recipe remains unmodified and does not yet select a
complete capture binding. Its bank probe is generated-RTL scope only, not an
atomic physical memory/host cut. Complete physical/pre-FAME mapping, live
MMIO/DMA/common-cut ownership, full image P&R/AFI and actual FPGA captures,
paired zero-edge CPU migration, finite/live RTL and rolling recovery remain
pending. Reuse the prepared `checkpoint-f2-rocket-capture-193` invocation and
localhost build configuration; do not launch a duplicate build or AWS farm.
Existing controller commits were published FireSim first (`a2a38229`), then
Chipyard (`c7cb1cbd`); independent remote tips agree. The successful Chipyard
remote push retained its read-only local tracking-ref update error. Managed
worker startup failed before a worker began; work stayed central and no
worker requests remain. Plans/conda/archive and local git history are untouched.

## Iteration 192: computed FAME clock tokens and whole-root bank emission

`GeneratedStateBankAccess` binds one-bit combinational token origins with
`data_clock: {hierarchy, expression}` and follows them through concrete aliases,
casts and repeated child pins. Every sequential consumer, including gate
sources, independently rejects computed data as a physical clock. The descriptor
validator reconstructs origins/consumers from emitted wiring and rejects binding
changes or sequential rewiring with a refreshed circuit hash.

The new fixture uses both token values for functional next-state data and keeps
**9 owners / 15 words / 22 clock-port routes**. Fresh EDA VCS SP2 passes **5,483**
checks / 60 words at **6 / 43 / 126 / 223**, original RTL and public-input oracles,
frozen write/reset/clock pressure, backpressure, continuation, first-word
corruption stop and full debug VCD. All **89 Scala / 286 checkpoint Python / 40
loop tests** and the complete retained EDA bank/transport/host/FCFS ASan/UBSan
scope pass. A healthy copied control and all **14** coherently rehashed token
metadata corruptions pass/reject as intended.

The retained whole Rocket probe now emits and validates banks for **12,099
entries / 619,016 words / 21,005,343 logical bits / 2,300 instances**. Its 2,120
clock-port routes include four computed data origins, eight static and one
invalid origin, plus three registered gate adapters. This is the retained
iteration-184 intermediate with explicit `generated_rtl_only` scope and
`external_runtime_required=true`, not a fresh complete F2 image. The original
input/annotation files and recipe provenance are preserved. All **13** native
component syntheses pass; the token fixture uses **169 LUTs / 96 registers**,
estimated WNS **+6.260 ns** / WHS **+0.038 ns** at 140 MHz (OOC, external I/O
unconstrained). Whole-root native OOC synthesis completes with **715,823 LUTs /
107,016 registers / 64 DSPs / no block RAM**, zero synthesis errors/critical
warnings and zero OOC DRC errors. Estimated setup WNS **-0.916 ns** has **6,878**
failing endpoints; hold WHS **-0.324 ns** has **18,710**, of **3,580,132** total.
The worst setup path crosses 34 logic levels from target cbus synchronizer state
to `ckpt_saved_data[0]`. These are pre-placement estimates with external I/O
unconstrained and OOC clock-buffer locations unbound. Timing closure is **not**
verified. Native DCP, netlist, exact Tcl and reports are retained. Final independent
EDA audits pass, including complete inventory/source/DCP identity, all retained
negative suites, **14** coherently rehashed token-origin corruptions and **23**
new fixture receipt corruptions. Top VCS passes **7,858** checks on exact native
inputs. Fresh inventory confirms no invocation runtime instance and no native
Vivado/Java job remains. Commands and immutable receipts are cataloged in
`runs/aws-f2/iteration192/summary.json` relative to the loop.

Next: integrate these banks with the real bridge/common cut and source-bound
physical primitive implementations; complete atomic functional-memory/host
capture and pre-FAME mapping, address readout/functional timing with mapped
clocks, then fresh whole-image build/P&R/AFI, active F2
captures and FPGA-produced paired CPU restore/finite/live/rolling acceptance.
The invocation reuses the initialized configs, exact recipe and localhost build
farm. No new AFI or runtime instance has been requested. Native worker startup
failed before a worker began; all implementation stayed central, with no worker
requests remaining. Existing controller commits were pushed FireSim first
(`118daa04`), then Chipyard (`ec2b9f95`); remote tips agree. The successful
Chipyard remote push retained its read-only local tracking-ref update error.
Both plan hashes remain unchanged. No staging, local commits, conda edits or
history changes were performed. Initial Scala diagnostic text and the stopped
first whole-synthesis attempt (corrected Tcl gate checks) remain under
`runs/aws-f2/iteration192/` relative to the loop. The controller owns the next
checkpoint commit/publication.

## Iteration 191: explicitly invalid metadata clock origins

`GeneratedStateBankAccess` retains explicit FIRRTL `is invalid` origins in
`invalid_clock` rows instead of treating the pin as a functional root or
silently removing it. Routing may pass through concrete aliases, transparent
casts and repeated child IO. An absent driver still rejects; overlapping
invalid/connected drivers reject. Registers, memory ports/pipelines, registered
gate state and clocked effects cannot consume invalid clocks. Descriptors
reconstruct origins and sequential consumers from the actual specialized
circuit; changed bindings and rewired consumers with an updated circuit hash
reject independently.

The repeated-child fixture retains **9 owners / 15 words / 22 clock-port
routes**, including **8** explicitly invalid metadata routes. All **86 Scala /
286 checkpoint Python / 40 loop tests** pass. Fresh EDA VCS SP2 passes **5,483**
checks, **60** word reads at steps **6 / 43 / 126 / 223**, frozen reset/write
pressure, independent clocks, response backpressure, continuation and first-word
corruption rejection with full debug VCD. The complete retained EDA bank/top/
transport/host/FCFS sanitizer regression scope passes. The top separately passes
**7,858** VCS checks using the native synthesis's exact immutable inputs.
All **12** native component syntheses pass, including retained FASED (**759
entries / 99,611 words**). The invalid metadata fixture uses **181 LUTs / 79
registers**, estimated setup WNS **+6.298 ns** and hold WHS **+0.049 ns** at
140 MHz. These are OOC component estimates with unconstrained external I/O;
FASED retains **-0.299 ns** hold slack / **4,102** failing endpoints, and
whole-image timing closure remains pending.

Independent audits verify all 60 words, 22 routes, complete source/generated
input identity and native DCPs. A healthy copied control passes before all
**12** coherently rehashed invalid-origin semantic corruptions reject; all
**23** invalid-fixture receipt corruptions and retained negative suites reject.
The original EDA paths remain in receipts. Fresh AWS/localhost inventory records
no invocation runtime instance or native Vivado/Java build job. No new AFI was
requested. Commands and immutable receipts are cataloged in
`runs/aws-f2/iteration191/summary.json` relative to the loop.

Whole retained Rocket generation now clears
`F1Shim.top.PeekPokeBridgeModule_0.hPort_dummyModule.tIO_clock`. Its exact dummy
module has no state or internal references to that pin. The next probe exits
**1** at `F1Shim.top.ClockBridgeModule_0.clockTokenGen.eq(timeToNextEdge_0,
minStepsToEdge)`. This is a Clock-typed token-data route: FAME consumes its
`asUInt` value for enable/fired-owner updates, while physical abstract gates
retain `hostClock`. Computed token provenance remains unsupported; no arbitrary
data expression has been admitted as a physical clock. Inventory remains
**12,099 entries / 619,016 words / 21,005,343 logical bits / 2,300 instances**.
Inputs remain the retained iteration-184 intermediate, not a freshly generated
whole F2 image. Source excerpts, route analysis, hashes and raw failure are in
`runs/aws-f2/iteration191/whole-rocket-probe.json` and
`clock-probe-analysis.json`, relative to the loop.

Next: represent computed Clock-typed token data explicitly while independently
prohibiting it on sequential clocks; then complete actual simulator/pre-FAME,
physical primitive and atomic memory/host integration before whole-image
P&R/AFI and all active hardware cuts. FPGA paired zero-edge CPU restores,
finite/live comparison and rolling recovery remain pending. Managed worker
startup failed before a worker began; all work stayed central and no delegated
requests remain. Both plan input hashes are unchanged. No staging, local
commits, conda edits or history actions were performed. Existing controller
checkpoints were pushed FireSim first (`e0737054`), then Chipyard (`29176ba4`);
remote tips agree. The successful Chipyard remote push retained its read-only
local tracking-ref update error. The final controller-created checkpoint still
belongs to the controller's publication flow.

## Iteration 190: static metadata clock provenance

`GeneratedStateBankAccess` resolves exact one-bit constants through transparent
hierarchical clock routing into explicit `constant_clock` binding rows, with
neither a fabricated root clock nor an omitted pin. Static clocks cannot drive
registers, synchronous RAM pipelines, memory ports, registered gates or clocked
effects. Descriptor validation checks actual sequential consumers as well as
all port routes, including an attacker who rewrites a storage clock and updates
the circuit hash. Existing conditional RAM clocks retain their independent
same-enable generation checks; materialized RAM pipeline clocks are followed
through aliases during descriptor-origin validation.

The new repeated-child static metadata fixture retains all **9 owners / 15
words** and **22 clock-port routes**, including **8** explicit zero/one static
pins. The three new Scala tests cover transparent casts/IO, complete ownership,
register/RAM/effect rejection, changed/dropped/static-to-root bindings and
post-generation clock rewiring. All **83 Scala / 286 checkpoint Python / 40 loop tests** pass. The
initial Scala diagnostic (a misplaced FIRRTL fixture connection and conditional
pipeline-origin validation) is preserved under this iteration's `runs/`.

Fresh EDA VCS SP2 checks every word against the unchanged original RTL and
functional-input model at component steps **6 / 43 / 126 / 223**: **5,483 checks**,
**60** readouts, independent clocks, frozen reset/write pressure, backpressure,
post-release continuation and first-word corruption rejection with full VCD.
The full retained bank/top/MMIO/DMA/host/FCFS ASan/UBSan scope passes. Top VCS
uses the exact native synthesis's immutable generated inputs; **7,858** top
checks pass without an elaboration mismatch. Independent complete-word/source/
DCP/clock audits pass, with a healthy copied control followed by all **10** new
static metadata corruptions rejected (including Boolean/float origins despite
Python's numeric equality), all **23** static-clock receipt negatives and the
retained rejection suites. Original remote receipt paths remain intact.

All **11** native localhost component syntheses pass, including retained FASED
(**759 entries / 99,611 words**) and the static-clock fixture (**181 LUTs / 79
registers**, estimated setup WNS **+6.298 ns**, hold WHS **+0.049 ns** at 140 MHz).
These are OOC component estimates with unconstrained external I/O, not complete
image timing closure. FASED retains its **-0.299 ns** estimated hold slack / **4,102**
failing endpoints. Fresh AWS/localhost inventory records no invocation runtime
instance or native Vivado/Java build job. No new AFI request was made.

The whole exact-recipe retained-input probe clears the prior constant-zero
clock rejection and now fails, exit **1**, at
`F1Shim.top.PeekPokeBridgeModule_0.hPort_dummyModule.tIO_clock` with
`missing child clock`. Its parent explicitly marks the pin invalid. No invalid
or undriven origin is treated as a root clock, no state/port was dropped and no
complete bank output was published. Inventory remains **12,099 entries /
619,016 transfer words / 21,005,343 logical bits / 2,300 instances**. Probe inputs,
raw command/failure and hashes are in
`runs/aws-f2/iteration190/whole-rocket-probe.json` relative to the loop. This is
the retained iteration-184 intermediate, not freshly generated complete F2
hardware. Next: prove the dummy pin's lack of functional consumers and represent
any supported invalid metadata explicitly, then finish actual simulator,
semantic boundary, physical primitive and atomic memory/host integration.

Managed worker startup failed before any worker began; all work stayed central.
Existing controller-created checkpoints were pushed FireSim first (`45e976a3`),
then Chipyard (`0ea54f0a`); the latter remote push succeeded while its local
tracking-ref update failed read-only. No local commit/staging, plan/conda edits
or history reset/clean. Full image P&R/AFI, physical capture, paired CPU restores,
finite/live comparison and rolling F2 recovery remain pending. Detailed fresh
verification commands, results and immutable receipts are cataloged in
`runs/aws-f2/iteration190/summary.json`.

## Iteration 189: exact FPGA synthesis constants and whole-Rocket probe

`GeneratedSynthesisConstantAdapter.prepare` explicitly selects the exact
source-hashed Rocket plusarg model's `SYNTHESIS` branch before inventory.
It validates WIDTH/DEFAULT/FORMAT/signature/source/circuit identity, materializes
the real constant and binds every instance to the original circuit and model.
Specialized annotations remain checked through descriptor construction, which
rejects dropped/changed metadata and altered storage/output implementations.
The default metasim inventory retains its independent `myplus` register and
opaque-bank rejection. No metasim donor is silently converted to FPGA state.

Fresh EDA VCS SP2 checks the independently emitted original Verilog with
`+define+SYNTHESIS` and conflicting `+checkpoint_constant=99`: **608 checks**,
**173 functional edges**, full reads at **2 / 39 / 132**, response backpressure,
frozen resets/inputs, healthy completion and full VCD. Semantic corruption stops
at the first frozen word at C=2. All **80 Scala / 286 checkpoint Python / 40 loop
tests** and the complete retained EDA bank/top/transport/host/FCFS ASan/UBSan
scope pass. The emitter's own resource side effect was fixed to keep the retained
Verilog under `runs/`; its diagnostic and the initial missing probe-helper
compiler error remain preserved.

The first independent top audit rejected two different elaborations: a Scala
regeneration changed the global widget namespace (`_2` versus `_1`) in both
the RTL and generated host header. No comparison was relaxed. Fresh EDA top
VCS now consumes the latest native synthesis's immutable `generated-snapshots`
after checking every input hash; `eda-suite.sh` uses this same selection for
reverification. The original failed audit and both original receipts remain
unchanged (`top-input-mismatch.json` records the exact differing file hashes).

All ten native localhost component synthesis checks pass, including retained
FASED and the new synthesis-constant component (**84 LUTs / 66 registers**,
estimated setup WNS **+6.232 ns**, hold WHS **+0.067 ns** at 140 MHz).
These are OOC component estimates with unconstrained external I/O, not a
whole-image timing result. Final AWS/localhost inventory confirms no invocation
runtime instance or native Vivado/Java job; no new runtime or AFI was requested.
The final full independent EDA audit passes, including all **16** new constant
receipt/semantic corruptions and the retained bank/top/host/clock/gate audits.
Its functional-input oracle independently reconstructs counter values
**0 / 2,750,501 / 9,494,105** at the three component cuts. Commands, immutable
execution receipts, native DCPs, complete debug VCDs and failed diagnostics are
cataloged by `runs/aws-f2/iteration189/summary.json` relative to the loop.

The explicit whole-root diagnostic inventories **12,099 entries / 619,016
transfer words / 21,005,343 logical bits / 2,300 instances**, including seven
source-bound synthesis-constant instances. It then **fails**, exit 1:
`Generated checkpoint bank unsupported: derived, gated, or undriven clock/child
clock at F1Shim.top.UInt<1>("h0")`. FPGATop ties bridge target-clock metadata
pins to zero; no port/state was dropped to bypass the resolver. Raw command,
failure, source hashes and prepared inputs are in
`runs/aws-f2/iteration189/whole-rocket-probe.json` and its linked log. This input
is the immutable retained iteration-184 exact-recipe intermediate, not freshly
generated complete checkpoint hardware. Next: distinguish and validate unused
static clock pins without accepting hidden constant-clock storage, then finish
the real simulator/boundary integration and complete memory/host/primitive owners.

Managed worker startup failed before a worker began; all work stayed central.
Only controller-created checkpoints were pushed: FireSim `ae00311c`, then
Chipyard `5c561701`; remote tips agree. The Chipyard tracking-ref update failed
read-only after its remote push succeeded. Plans remain read-only, no staging,
local commits, reset/clean or conda edits. Full image P&R/AFI, actual FPGA paired
capture, CPU zero-edge restores, finite/live comparison and rolling F2 recovery
remain pending; the milestone remains **in_progress**.

## Iteration 188: exact registered clock-gate owners and real FASED banks

`GeneratedClockGateAdapter` accepts only the exact inline
`DefineAbstractClockGate.impl`, its signature and circuit-qualified source
annotation. It materializes the original posedge enable register and
`I & enable` output; bank freeze holds the enable and every downstream owner.
Unknown, altered, missing, duplicated and foreign-circuit implementations
reject. Descriptors independently validate actual specialized enable clock,
reset, next-state and output expressions plus ordered gate-chain provenance.
Repeated/cascaded gate identities remain separate. Conditional RAM
`validif(enable, clock)` expressions retain their original wiring and are
accepted only when that same memory port's enable proves the guard. Guarded
register clocks and mismatched memory enables reject.

The exact retained Rocket FASED timing-model subtree now emits a complete
bank network: **759 entries / 99,611 physical transfer words**. This uses the
immutable iteration-184 FIRRTL and a separately hashed retained gate source;
it is not newly generated whole-Rocket hardware. Its generation and native
synthesis evidence live under `runs/aws-f2/iteration188/` relative to the loop.
Fresh EDA component readout checks original RTL plus an independent public-input
model, both gate-enable values, four cuts, backpressure, frozen resets/writes,
high-phase CE changes, adversarial clocks and first-word semantic corruption.
All **77 Scala / 286 checkpoint Python / 40 loop tests** and the full retained
EDA bank/top/network/Widget/transport/host/FCFS ASan/UBSan scope pass. The new
gate check passes **3,023** checks over **352** functional steps / **286** gated
edges, **28** complete reads at **C=6 / 43 / 126 / 223**, **84** stalled responses,
**74** frozen adversarial input edges and **352** high-phase CE changes. The
independent gate audit recomputes every word and rejects all **23** metadata
corruptions. Full debug VCD and first-word corruption stop are retained.

All eight bank/top native components synthesize. Gate OOC synthesis uses
**103 LUTs / 50 registers**, estimated setup WNS **+5.957 ns**, hold WHS
**+0.086 ns**. The actual retained FASED bank synthesizes **75,132 LUTs /
6,522 registers** across **201** specialized hierarchy instances and **1,131,341**
logical state bits. Its explicitly constrained gated clock has no unclocked or
unconstrained internal endpoints, estimated setup WNS **+0.978 ns** and hold WHS
**-0.299 ns** (**4,102** failing hold endpoints). These are OOC estimates with
unconstrained external I/O, not timing closure or a whole-image implementation.
FASED runtime/traffic validation remains pending. Final full independent audits
are cataloged by the iteration's summary; raw failures remain preserved.

The adapter covers the exact abstract RTL gate. Platform-mapped BUFGCE state,
complete simulator/semantic mapping, common target cut across memory/host
owners, image P&R/AFI and actual F2 paired checkpoint capture remain pending.
No complete CPU restore, finite/live comparison or rolling F2 recovery is
claimed. No new runtime instance or AFI was requested. Fresh final inventory confirms
no invocation-owned runtime instance or native Vivado/Java build job. Existing controller
checkpoints were pushed FireSim first (`216c579a`), then Chipyard (`b86a66cb`);
remote tips agree. Chipyard's tracking-ref update failed read-only after the
remote push succeeded. No staging/commits, plan/conda edits, reset or clean.
Managed subagent startup failed before a worker started; work stayed central.

## Iteration 187: transparent hierarchical clocks in generated banks

`GeneratedStateBankAccess` traces output clock ports, sibling forwarding,
connected child inputs, local aliases and exact one-bit clock casts through
concrete hierarchy to named root clock inputs. Lazy per-pin resolution avoids
false dependency cycles; hierarchy-qualified cycle checks reject real loops.
Registers, RAMs and clocked effects use the same checked resolver. Descriptor
construction independently reconstructs the actual specialized clock routes.
Opaque/gated clocks, data logic, sequential clock aliases and asynchronous
resets still reject. The all-owner freeze contract remains external; no CDC
acknowledgement or common CPU cut is inferred.

The new forwarded-clock fixture retains **9 entries / 15 words** with **14**
clock-port routes, including swapped repeated children and split-clock RAMs.
Fresh EDA VCS SP2 passes **5,483** checks across **352** functional steps,
**60** complete reads at component cuts **6 / 43 / 126 / 223**, **180** stalled
responses and **154** adversarial frozen edges in each functional domain.
Every word/output matches unchanged original RTL and an independent input
model; first-word corruption stops frozen before any completed read. Full VCD
is retained. Native localhost Vivado 2025.2 OOC synthesis uses **181 LUTs /
79 registers**, estimated WNS **+6.298 ns** with all three clocks at 140 MHz.
This is component synthesis, not a Rocket image build or physical capture.

All **71 Scala / 286 checkpoint Python / 40 loop tests** pass. Full retained
EDA initialized/synchronous/wide-deep banks, top/network, Widget/transport/host/
cut and native/VCS ASan/UBSan FCFS regressions pass. FCFS retains **46** fresh
continuations, **138** pre-edge owner comparisons, **296** matching MMIO calls,
eight malformed fresh processes and **2,972** rejections per backend.
Two initial Scala failures exposed parsed RAM clock types and declaration
ordering for local aliases. Both were corrected without changing logical
pipeline ownership; their diagnostic logs remain under this iteration's runs.

Fresh AWS identity/type access succeeds; the exact Rocket recipe and existing
manager configuration are preserved in invocation-local overrides selecting
one tagged f2.6xlarge, disabled metasim and ExternallyProvisioned `[localhost]`.
No runtime or AFI request was launched. Account AFI observations are read-only;
existing unrelated images were not used as checkpoint acceptance. The retained
exact-recipe donor remains iteration-184 FIRRTL with its original path/hash.
All seven native component/top synthesis checks pass. Independent EDA audits
verify all **60** forwarded-clock words/domain labels, **14** clock-port routes
and **48** immutable VCS/native files; all **23** forwarded-clock and **23**
direct-clock metadata corruptions reject. Retained data-array, wide/deep and top
audits pass with their full **16 / 14 / 14** rejection scopes. Final inventory
confirms no invocation-owned runtime instance or local Vivado/Java build job.
Individual receipts, executed commands and source provenance are cataloged in
`automations/checkpoint_loop/runs/aws-f2/iteration187/summary.json` and
`verification-commands.json` in the same directory. This is component evidence;
no FPGA-produced Level-1/Level-2 images or hardware trace was captured.

Published existing controller checkpoints FireSim first (`ecd698e2`), then
Chipyard (`3b56a234`); independently queried remote tips agree. Chipyard's local
tracking-ref update failed read-only after the remote push succeeded. Plans,
conda files and historical evidence were preserved; no staging/commits/reset/
clean. Managed subagent startup failed before a worker started; all work stayed
central, with no outstanding delegated LLM work.

Next: explicit gated/opaque-owner adapters and complete generated simulator
network, semantic mappings and common-cut memory/host owners; localhost whole
Rocket image P&R/AFI/deployment; all four active quad-hart hardware cuts and
paired images/trace; independent zero-edge CPU restores, finite/live comparison
and rolling FPGA recovery. These acceptance steps remain **pending**.

## Iteration 186: explicit multiple direct functional clock domains

`GeneratedStateBankAccess` supports multiple direct functional input clocks only
with `separateAccessClock = true`. Registers, RAM ports and materialized
synchronous pipelines keep their original clocks; child clocks must connect
directly to a parent input. The binding records every functional clock port's
root input, including swapped repeated children. Generation checks that
specialization preserved this topology, and descriptor construction independently
reconstructs it from the emitted circuit. Missing/reordered/changed provenance
rejects. Derived/gated clocks, asynchronous resets and opaque owners still
reject; no clock-domain handshake or common CPU cut is inferred. Callers must
establish and hold freeze for all domains before access until responses drain.

The new two-domain fixture has repeated swapped children, split-clock RAM
read/write ports, independent reset/register owners and synchronous read-data
owners: **9 entries / 15 words per cut**. Fresh EDA VCS passes **5,483**
checks across **352** functional steps (**237 / 235** domain edges), complete
15-word cuts at **6 / 43 / 126 / 223**, **180** response-stall cycles and
**154** frozen adversarial edges per domain. All words and outputs match
unchanged original RTL and an independent functional-input model. First-word
corruption stops frozen before any completed read. Full debug VCD is retained.
Native localhost Vivado 2025.2 OOC synthesis for the F2 part uses **181 LUTs /
79 registers**, estimated setup slack **+6.298 ns** with all three clocks
constrained at 140 MHz. This is component synthesis, not whole-image P&R/AFI.

All **69 Scala / 286 checkpoint Python / 40 loop tests** pass, as does the full
retained initialized/synchronous/wide-deep bank, top/network, Widget/transport/
host/cut and native/VCS ASan/UBSan FCFS scope. FCFS retains **46** fresh
continuations, **138** pre-edge owner comparisons, **296** matching MMIO calls,
eight malformed fresh processes and **2,972** rejections per backend.
Independent EDA audits verify every recorded new-fixture word/domain label
and **48** immutable VCS/native evidence files; all **23** new receipt-metadata
corruptions reject. Retained complete data-array/wide-deep/top audits pass,
including **16** data-array metadata and **14** top evidence-tamper rejections.
Results and independent evidence audits are recorded under
`automations/checkpoint_loop/runs/aws-f2/iteration186/`; the final
`summary.json` and `verification-commands.json` catalog executed checks and
individual immutable receipts. Initial Scala fixture assertions used the
pre-lowering reserved instance names `left` / `right`; the diagnostic logs are
preserved, and the corrected test binds actual `left_` / `right_` names.

Fresh AWS identity/type access succeeds. The initialized manager/AWS setup and
exact Rocket recipe remain in use. Generated invocation overrides select disabled metasim, one tagged f2.6xlarge
and ExternallyProvisioned `[localhost]`. No custom image, AFI, F2 capture,
`.fsckpt`, `.rtlckpt` or hardware boundary trace is claimed this iteration.
The retained exact-recipe donor remains the immutable iteration-184 FIRRTL,
with its original hash/path preserved in `generation-provenance.json`. Final
inventory confirms no owned runtime instance or native Vivado/Java build job.
A read-only account AFI inventory now observes the unrelated MegaBoom request
`afi-0cf1067195094a7f9` / `agfi-0545f60fbeffe7b02` available; it was not operated
on as a loop resource. No AFI request was made by this iteration.

Existing controller checkpoints were published FireSim first (`2f9b42dd`), then
Chipyard (`58c88f47`); independently queried remote tips agree. Chipyard's local
tracking-ref update reports a read-only filesystem after the successful push.
The controller retains responsibility for local commits and subsequent pushes.

Next: integrate actual gated/opaque clock owners and complete the simulator
bank network without freezing MMIO/DMA/control; bind semantic pre-FAME state
and common-cut functional-memory/host owners. Full Rocket localhost image
synthesis/P&R, AFI/deployment, four active quad-hart hardware cuts, independent
zero-edge CPU restores, finite/live CPU comparison and rolling F2 recovery
remain pending. Native subagent startup failed before a worker started; all
work remained in this central turn, with no outstanding delegated LLM work.

## Iteration 185: transport-clock bank endpoint and retained Rocket D-cache RAM

`GeneratedStateBankAccess.generate(..., separateAccessClock = true)` adds an
always-running root `ckpt_clock`; only the three response endpoint registers
use it. Functional registers, synchronous read-pipeline owners and RAM port
clocks retain their original clock. Descriptor construction checks the actual
endpoint clocks against `access_clock` and the explicit freeze contract.
Missing/altered contracts and wrong roots reject. This does not supply a CDC
handshake or an atomic multi-owner cut: the caller must establish and hold
global freeze before access until every response drains. Default generation
keeps its functional-clock endpoint and all existing state/clock restrictions.

The actual retained exact-recipe `DCacheDataArray` has **64 512-byte RAMs** and
**64 synchronous read-data owners**, **32,832** transfer words per cut.
Fresh EDA VCS SP2 captures every word at component cuts **C=513 / 611 / 869**,
with **7,132,541 checks**, **98,496** complete reads, **196,992** stalled-response cycles and full
debug VCD. **65,664** reads complete with the functional clock stopped; the
middle cut also applies **131,328** frozen functional-clock edges with writes
enabled to every way/byte. All outputs and words match unchanged original RTL
and a separate model initialized and updated solely through functional
requests. Masked writes, all eight ways, read pipelines, freeze and post-release
execution pass. First-word semantic corruption stops frozen at C=513 before
any completed state read. These are component cycle labels, not Rocket workload
or FPGA cuts. No `.fsckpt`, `.rtlckpt` or hardware `.trace` is claimed.

All **66 Scala / 286 checkpoint Python / 40 loop tests** pass. The complete
retained initialized/synchronous/wide-deep bank, FPGATop/network,
Widget/transport/host/cut and native/VCS ASan/UBSan FCFS scope passes. FCFS
retains 46 fresh continuations, 138 pre-edge owner comparisons, 296 matching
MMIO calls, eight malformed fresh processes and 2,972 rejections per backend.
Native localhost Vivado 2025.2 OOC
synthesis for the F2 part uses **9,568 LUTs / 522 registers**, estimated setup
slack **+5.228 ns** with both clocks constrained at 140 MHz. This is neither
whole-image P&R nor an AFI. The immutable exact-recipe donor FIRRTL remains
the iteration-184 retained input (SHA-256 `cb35c05f22eae3cfdc15a10e2f5aacd7daf32095c0832e601af86cc0caf243e3`),
not newly generated hardware. Raw commands, generated/source snapshots, compiler
and runtime logs and native DCP/reports are under
`automations/checkpoint_loop/runs/aws-f2/iteration185/`.
Independent EDA audits verify all **98,496** recorded words and **46** immutable
VCS/native data-array evidence files, reject **16** receipt-metadata corruption
cases, and retain complete wide/deep and top audits with all **14** tamper
rejections per retained suite. Initial audit-script import failure is preserved;
the complete corrected audit invocation passes. `summary.json` and
`verification-commands.json` catalog individual files and runnable commands.

Fresh AWS identity/type access succeeds. Initialized-manager overrides retain
the exact Rocket recipe, disabled metasim, one f2.6xlarge, dedicated tag
`checkpoint-f2-rocket-capture-185` and ExternallyProvisioned `[localhost]`.
No runtime instance or AFI request was launched. Final inventory confirms no
owned runtime instance or native Vivado/Java build job remains. A read-only
account image inventory also observes the unrelated MegaBoom request
`afi-0cf1067195094a7f9` / `agfi-0545f60fbeffe7b02` pending (created
2026-10-23T17:17:17Z); preserve it and do not operate on it as a loop resource.
Existing controller checkpoints
were published FireSim first (`65b117cb`), then Chipyard (`4da271c7`); remote
tips are independently recorded. The Chipyard tracking-ref update reports a
read-only filesystem after the successful remote push. The controller still
owns local commits and subsequent publication. Native subagent startup failed
before a worker started; all implementation and verification was coordinated
by this central turn.

Next: integrate the complete real simulator bank network while leaving MMIO,
DMA and capture control running; implement explicit gated/multiple-clock and
opaque-owner contracts, bind pre-FAME semantic mappings, and finish common-cut
memory/host ownership. Full Rocket synthesis/P&R/AFI/deployment, FPGA-produced
paired images/trace, independent zero-edge CPU restores, finite/live CPU
comparison and rolling hardware recovery remain pending. Initial Scala
format/exception-type failures are retained separately from the passing rerun.

## Iteration 184: synchronous effects and actual Rocket DTLB bank integration

The bank generator gates synchronous printf/stop/verification enables with the
storage freeze and rejects derived effect/child clocks and analog state.
Clockless stateless helpers route the network without inventing clock owners.
Explicit `NoCircuitDedupAnnotation`, bound into annotation-policy hashes,
prevents resolver deduplication from invalidating specialized clone contracts.

All **64 Scala / 286 checkpoint Python / 40 loop tests** pass. Fresh EDA VCS SP2
captures every one of the actual retained Rocket DTLB's **101** register words
at **C=2 / 39 / 132** through public bank ports: **28,918** checks, **303** reads,
**1,212** stalled response cycles and **173** functional edges. Every output and
state word matches independently emitted original RTL. Full healthy VCD and
bank-word logs remain separate from the first-word corruption run, which exits
1 frozen at C=2 before any completed read. The effects fixture passes **226**
checks, verifies **116** actual live printf messages with none frozen, preserves
released stop and immediate-assertion reporting, and rejects semantic corruption.
Native localhost Vivado OOC DTLB synthesis uses **3,084 LUTs / 1,859 registers**,
estimated setup slack **+4.450 ns** at 140 MHz; effects storage uses **42 LUTs /
20 registers**. The input is the hash-bound retained exact-recipe
`post-sim-mapping.fir`, not newly generated full Rocket or FPGA state.

The complete retained initialized/synchronous/wide-deep bank, FPGATop/network,
Widget/transport/host/cut and FCFS native/VCS ASan/UBSan scopes pass. FCFS retains
46 fresh continuations, 138 pre-edge owner comparisons, 296 matching MMIO calls,
eight malformed processes and 2,972 rejections per backend. Independent new-component audits verify 52 effects and 44 DTLB files, including
identical VCS/native generated inputs. Retained wide/deep and top audits verify
107 / 92 files and each rejects all 14 evidence-tamper cases. Final inventory
confirms no owned active run instance or native Vivado/Java build job.
Raw compiler/runtime logs, full waveforms, source snapshots and exact commands are under
`automations/checkpoint_loop/runs/aws-f2/iteration184/`.
Initial Scala/parser/dedup trials, VCS obsolete-initializer/reserved-name errors
and the immediate-assertion policy test failure are retained as diagnostics.

Fresh AWS identity/type access passes. Isolated initialized-manager overrides
use the exact Rocket recipe, disabled metasim, one f2.6xlarge, dedicated tag
`checkpoint-f2-rocket-capture-184` and ExternallyProvisioned `[localhost]`.
No F2 instance or AFI job was launched. Existing controller checkpoints were
published FireSim first (`4b74c3ac`), then Chipyard (`f6cc3017`); the successful
Chipyard push retains its read-only tracking-ref diagnostic. Managed delegation
failed before creating a worker; all implementation stayed central.
Plans, conda and legacy archive were preserved without staging or local commits.

Next: integrate the actual Rocket/FAME multi-clock/opaque-clock/annotation
contracts and complete simulator/channel/FASED/functional-memory/host ownership
with the top binding; build/P&R the full checkpoint-enabled image on localhost,
create AFI, deploy and capture all four active quad-hart cuts. Full zero-edge
CPU restores, finite replay, sustained live RTL and rolling FPGA recovery remain
pending. Component bank readout and synthesis do not establish those criteria.

## Iteration 183: wide/deep storage and versioned transport reconstruction

`GeneratedStateBankAccess` slices arbitrary-width lowered registers/RAM words
into little-endian 64-bit transfers, address-major within each unchanged StateID.
The generated `latched-banked64-chunked-v2` binding retains logical width/depth
and explicitly binds chunk count and physical width/depth. Descriptor ROM and
C++ metadata share the checked flattened shape. Signed high chunks zero-pad
rather than sign-extend. Transfers beyond the supported **2^31-1** per-entry
depth reject before hardware generation. Narrow-only bindings retain v1;
legacy explicit unchunked capture still rejects wide state.

EDA VCS SP2 passes **13,769,412** checks, **196,692** physical reads and
**1,573,571** stalled DMA cycles for three complete **65,564-transfer-word** /
**65,545-logical-word** captures at **C=1 / 42 / 138**. The fixture covers signed
65-bit, 128-bit and 512-bit registers, 129-bit x 5 RAM (three chunks per word)
and 9-bit x 65,537 RAM. Every public output agrees with original RTL and a
functional-input oracle; the decoder independently reconstructs every logical
word. Active writes to address 65,536 cross the former limit. Reset and writes
remain frozen during readout; the first corrupted data word stops frozen at
C=1 before any image publication. Full healthy debug VCD is retained. Fresh
ASan/UBSan production C++ frame validation passes all three complete cuts,
including corrupt/truncated, wrong-cycle, incompatible and incomplete metadata.

Native localhost Vivado 2025.2 synthesizes the complete wide/deep storage fixture
for `xcvu47p-fsvh2892-2-e`: **20,687 LUTs / 259 registers**, estimated setup
slack **+5.328 ns** at 140 MHz. This is component OOC synthesis; it is not a
checkpoint-enabled Rocket image, P&R, AFI or FPGA execution. A read-only shape
audit of the retained exact Rocket generated inventory finds **11,464** entries,
**132** wider than 64 bits, maximum width **512**, maximum depth **16,384**,
**445,838** logical / **618,252** transfer words, and no flattened-depth overflow.
That retained inventory is historical input, not fresh full-Rocket generation.

All **60** Scala / **286** checkpoint Python / **40** loop tests pass. The full
retained FCFS ASan/UBSan/VCS and generated-bank, Widget, host, cut, synchronous,
initialized, generated-network and FPGATop fixture scopes pass without reduced
checks. Independent EDA audits verify **107** wide/deep files and **92** top
files; both suites reject all **14** receipt/evidence mutations. The retained
fixture-top native synthesis remains **3,528 LUTs / 1,383 registers**. Final
inventory reports no owned live runtime or native Vivado/Java build job.
Initial Scala syntax, reference-clock and backpressure-coverage trials
remain diagnostic evidence. The testbench reference now receives exactly one
pulse per functional edge; backpressure was increased to satisfy the original
stress requirement. Healthy captures and waveforms remain separate from the
semantic-negative run.

Fresh AWS identity/type access passes. Isolated exact-Rocket checkpoint configs
reuse initialized manager inputs, disabled metasim, one `f2.6xlarge`, tag
`checkpoint-f2-rocket-capture-183` and ExternallyProvisioned `[localhost]`.
The original invocation with a mistyped workload name remains a preparation
trial. `checkpoint-build-final/` selects the byte-identical retained quad-hart
self-check ELF, installed under the invocation's new workload name; the native
manager resolves its real file successfully. `workload-installation.json` binds
the original, private and manager-installed bytes. No F2 instance or AFI job
was launched. Existing controller commits were
published FireSim first (`1fb2d55a`), then Chipyard (`07392193`); independent
remote tips agree. The successful Chipyard push reports its usual read-only
local tracking-ref failure. Managed delegation failed before creating a worker;
all work remained central. Plans, conda and the legacy archive were preserved;
no staging or local commits were made.

Exact commands, immutable inputs, per-cut receipts and raw logs are cataloged
in `automations/checkpoint_loop/runs/aws-f2/iteration183/summary.json`. Next: actual
Rocket compiler/FAME binding and remaining annotation/side-effect/clock contracts;
global channel/FASED/functional-memory/host ownership and atomic freeze; complete
localhost Rocket image P&R/AFI/deployment; four real active-workload FPGA cuts;
independent zero-edge CPU restores, finite/live RTL comparison and rolling F2
recovery. All hardware capture/migration acceptance remains pending.

## Iteration 182: initialized storage and explicit annotation translation

`GeneratedStateBankAnnotations` translates `DontTouchAnnotation` and hex/binary
`MemoryFileInlineAnnotation` to every applicable specialized instance. Exact
local/nonlocal targets and declaration kinds are checked; overlapping initializers,
missing/reshaped targets and unknown annotation contracts reject. Synthesis
initialization policy is preserved explicitly. Source and translated annotation
hashes join the bank/driver binding; dropped/changed initialization and extra
unsupported metadata reject before descriptor construction.

Fresh EDA VCS SP2 passes **1,870** checks, **69** bank reads and **276** response
stall cycles. Both initialized RAMs pass complete readout at **C=0**, before any
functional edge, then **C=7 / 44 / 155** after writes. All **587** public output
observations match an independent input oracle and original RTL emitted through
standard FIRRTL path resolution. No private state read/deposit supplies the
capture. Full debug VCD and exact hex/binary images are retained. Native localhost
Vivado 2025.2 synthesizes this component at **77 LUTs / 11 registers**, estimated
setup slack **+6.491 ns** at 140 MHz. All **18** logical RAM bit planes and **36**
physical read-port copies retain the independent expected INIT values; **seven**
semantic/mapping corruptions reject in the independent EDA audit. Native DCP CRC,
part/top/OOC metadata and identical private VCS/synthesis inputs are checked.

All **58** Scala / **283** checkpoint Python / **40** loop tests pass. The full
retained FCFS ASan/UBSan/VCS scope retains 46 fresh continuations, 138 pre-edge
owner comparisons, 296 matching MMIO calls, eight malformed fresh processes and
2,972 rejections per backend. Synchronous banks retain 21,970 checks / ten cuts;
the generated network retains 1,014 checks / three cuts; FPGATop retains 7,858
checks at **C=109 / 167 / 305**, 66 decoder negatives and 5,532 sanitizer checks
per cut. Current fixture-top native synthesis remains **3,528 LUTs / 1,383
registers**, **+4.282 ns**. Independent top audit verifies **92** files and all
**14** evidence-tamper cases reject. Initial compile/reference/hash trials,
native-report mapping/marker trials and the first audit import failure remain
separate diagnostic logs; corrected executions passed without reducing scope.

Fresh AWS access/type queries pass. New isolated exact-Rocket configs reuse the
initialized manager inputs, retain disabled metasim and one `f2.6xlarge`, tag
`checkpoint-f2-rocket-capture-182`, and ExternallyProvisioned `[localhost]`.
No runtime instance or AFI job was launched. Final AWS/process inventory confirms
no tagged runtime instance or native Vivado/Java job. Existing account AFIs were
observed read-only. Existing controller checkpoints were published FireSim first
(`34bbeaa3`), then Chipyard (`4816aa6b`); remote tips agree. Chipyard's successful
push could not update its read-only local tracking ref. Managed delegation failed
before creating a worker; all work was central and no worker remains. Plans,
conda files and the legacy archive were preserved without staging or commits.

Exact commands, immutable inputs, complete per-cut fixture receipts, native logs,
failed trials and hashes are cataloged in
`automations/checkpoint_loop/runs/aws-f2/iteration182/summary.json`. Next: actual
Rocket/FAME integration with wide/deep state, remaining annotation contracts,
global channel/FASED/functional-memory/host freeze and complete capture. Full
localhost Rocket image P&R/AFI/deployment, four active-workload FPGA captures,
independent zero-edge CPU restores, finite/live RTL continuation and rolling F2
recovery remain pending. This increment establishes component behavior only.

## Iteration 181: synchronous RAM owners and immutable execution audits

`GeneratedStateBankAccess` materializes the exact FIRRTL passthrough memory
pipeline owners already present in both independent inventories. New/undefined
readers retain address state; old readers and old/undefined readwriters retain
data state. RW data updates on enabled write edges, matching the passthrough
emitter. Distinct physical register names bind back to unchanged logical
StateIDs. Pipeline updates and RAM writes honor accepting-edge freeze; held
responses survive abort/release. RW-new policies, collisions, unretargeted
annotations, wide/deep state and derived clocks still reject explicitly.

Fresh EDA VCS SP2 passes **21,970** checks, **454** reads, **1,816** response
stall cycles and ten complete 45-word fixture cuts. Five RAM modes match
unchanged reference RTL and an independent oracle over **2,905** observed
edges / **202** functional edges. Full debug VCD is retained. Initial Scala
trials and a reference trial using generic memory-delay lowering failed;
the corrected reference uses the inventoried passthrough configuration.
Original failed logs remain separate diagnostics under this iteration.

All **54** Scala, **283** checkpoint Python and **40** loop tests pass. Fresh
bank/Widget/transport-host/cut and full FCFS ASan/UBSan/VCS pass: 46 fresh
continuations, 138 pre-edge comparisons, 296 matching MMIO calls, eight
malformed fresh processes and 2,972 rejections per native/VCS backend.
The ROM/Widget network retains 1,014 checks and three cuts. FPGATop retains
7,858 checks at **C=109 / 167 / 305**, 66 decoder negatives and 5,532 sanitized
host checks per cut, and first-word semantic rejection.

Native localhost Vivado 2025.2 synthesizes the synchronous endpoint at
**133 LUTs / 32 registers**, estimated setup slack **+6.087 ns** at 140 MHz;
the integrated fixture top remains **3,528 LUTs / 1,383 registers**, **+4.282 ns**.
Both are out-of-context component results, not Rocket image P&R or an AFI.
The iteration-180 controller audit compared saved VCS execution with a later
regenerated `FPGATop.v`; historical evidence remains unchanged. New durable
`synth_checkpoint_top` / `audit_checkpoint_top` helpers require identical private
VCS/native inputs and independently check current sources, actual execution,
all cuts, native DCP CRC/top/part/OOC metadata and final resources. Fresh EDA
audit passes; **14** evidence tamper cases reject, including DCP damage and
wrong native identity with updated outer hashes. The synchronous/native and
full retained evidence audit also passes. Exact commands and hashes are in
`automations/checkpoint_loop/runs/aws-f2/iteration181/summary.json`.

Fresh AWS identity/type access passes. Isolated exact-Rocket configs reuse
initialized inputs and the installed workload with disabled metasim, one
`f2.6xlarge`, tag `checkpoint-f2-rocket-capture-181`, and ExternallyProvisioned
`[localhost]`. No runtime or AFI was launched. Final inventory reports no
instances or native Vivado/Java jobs; existing account AFIs were observed
read-only and left untouched. Existing controller checkpoints were pushed
FireSim first (`1ed84c04`), then Chipyard (`b1751aa3`); remote tips agree.
Chipyard's successful remote push could not update its read-only tracking ref.
Delegation failed before creating any worker; all work was central. Plans,
conda files and the legacy archive were preserved without staging or commits.

Next: real Rocket compiler/FAME mappings, wide/deep state and annotation
translation, complete channel/FASED/functional-memory/host freeze and capture,
then full localhost image P&R/AFI and F2 deployment. Four hardware cuts,
FPGA-reference continuation, complete independent zero-edge CPU restores,
finite replay, sustained live RTL/debug waves and rolling F2 recovery remain
pending. Component acceptance does not complete those requirements.

## Iteration 180: FPGATop registration and actual CPU DMA queues

`CheckpointCaptureTopKey` is disabled in stock recipes. An explicit binding
must provide immutable generated descriptors and wire all bank, cut-counter
and owner ports in FPGATopImp's module context. There are no default owner
acknowledgements. Missing ROM metadata rejects at construction; missing
hardware connections reject during FIRRTL initialization checking. The Widget
uses an InModuleBody sideband port, preserving its standalone RTL interface.
FPGATop appends this global stream after target bridges, creates the normal
stream-engine metadata/driver constructor, and checks endpoint membership.
This extension does not grant CPU checkpoint admission.

Fresh EDA VCS SP2 tests actual generated 64-bit register and 32-word RAM state
through FPGATop's NASTI interconnect, the global Widget and CPUManagedStreamEngine
AXI4 buffers/FIFOs. Public functional inputs independently predict all **33
words** at fixture cuts **C=109 / 167 / 305**. All **7,858** checks pass,
including **660** stalled DMA cycles, **1,926** frozen edges, a full two-frame
FIFO, functional reset/writes during freeze, the existing stream retaining
index zero and usable data, missing-owner rejection, abort/drain and capture
reuse. Each stream passes **66** decoder negatives and **5,532** ASan/UBSan
host checks; the actual top-generated registry constructor compiles against
production headers. Corrupting an actual bank-response bit stops at the first
data word at **C=109**, frozen before publication. Full fixture visibility is
retained in `top.vcd`. Fixture `.rtlckpt` files are explicitly VCS-origin.

All **52** Scala tests, **283** checkpoint Python tests and **40** local loop
tests pass. The previous generated-bank/ROM network still passes **1,014**
checks; retained bank, Widget, transport/host, **82** cut-controller and full
FCFS ASan/UBSan plus VCS checks pass. FCFS retains **46** fresh continuations,
**296** MMIO calls, **138** pre-edge owner comparisons, eight malformed fresh
processes and **2,972** rejection checks per backend. Initial compile errors,+a negative-test Diplomacy scope leak and a W-before-AW testbench deadlock are
preserved under this iteration; the corrected complete checks pass. The
testbench offers both channels independently because the real interconnect
needs AW routing before it can accept W.

Native localhost Vivado 2025.2 synthesizes the integrated **fixture** FPGATop
for `xcvu47p-fsvh2892-2-e`: **3,528 LUTs / 1,383 registers**, estimated setup
slack **+4.282 ns** at 140 MHz. DCP and native reports are in
`runs/aws-f2/iteration180/top-vivado-uMoTxd/` (relative to the loop).
This is out-of-context synthesis, not Rocket synthesis/P&R or an AFI.

Fresh AWS identity/type access passes. Isolated exact-Rocket configs reuse
the initialized manager files and installed self-checking workload, with
tag `checkpoint-f2-rocket-capture-180`, disabled metasim, one `f2.6xlarge`
and ExternallyProvisioned `[localhost]`. No runtime or AFI was launched.
Existing controller checkpoints were pushed FireSim first (`2b625e40`), then
Chipyard (`e0fefc47`); independent remote tips agree. Chipyard's successful
remote push again could not update its local read-only tracking ref.
Managed delegation failed before creating any worker; all work was done by
the central agent. Plans, conda files and the legacy archive were preserved;
no staging or local commits were performed.

Evidence and exact commands: `automations/checkpoint_loop/runs/aws-f2/iteration180/summary.json`.
The passing top receipt is `top-vcs-corrected/checkpoint-top-yxwt2f1i/summary.json`;
retained regressions are in `retained-pkwfe6xs/`. Original EDA paths remain in
the native receipts. Fresh EDA `audit-abim2m10/audit.json` independently
verifies **38** evidence files, current sources/generated inputs, all cut
receipts, native DCP CRC/top/part/OOC metadata and final resource inventory.
The final scoped inventory contains no runtime instance or remaining native
Vivado/Java job. Next: connect the binding to real compiler-generated
Rocket simulator/semantic mappings; support synchronous/readwrite RAM
pipelines, wide/deep objects and annotation translation; freeze and capture
all FAME/channel/FASED, functional-memory and host state. Full localhost
image synthesis/P&R/AFI, F2 deployment and four active hardware cuts,
FPGA-reference continuation, complete independent zero-edge restores, finite
CPU replay, sustained live RTL/debug waveforms and rolling F2 recovery remain
pending. Finite fixture capture does not complete these requirements.

## Iteration 179: manifest-bound ROM and generated-storage-to-DMA network

`CheckpointCaptureDescriptors.fromGenerated` validates the complete independent
inventory, generated bank bindings and exact instrumented circuit before
constructing immutable descriptors. ROM lookup rejects invalid 32-bit ordinals
without truncating them into valid entries. The same descriptors generate the
host manifest initializer, little-endian digest bytes and the actual
`checkpoint_capture_t` registry constructor. Generated-ROM mode checks the
transport's hash/count and ignores external descriptor inputs. External-ROM
component mode remains compatible; neither mode grants CPU admission.

Fresh EDA VCS SP2 joins **actual generated storage**, the immutable ROM,
NASTI Widget and DMA stream. Public functional inputs independently predict
all **16 words / 9 entries** at component cuts **C=30 / 60 / 134**. The network
passes **1,014** checks, **48** bank reads and **82** stalled DMA cycles, holds
freeze against functional reset/writes, rejects a missing fixture owner and
recovers after counted abort/drain. Every stream passes **49** decoder negatives
and **2,940** native ASan/UBSan host checks. The generated constructor compiles
against production registry/driver headers; the exact generated C++ initializer
also independently validates all three streams. Component `.rtlckpt` images
are explicitly **VCS-origin fixtures**, not F2 or CPU capture evidence.
Deliberately flipping an actual bank-response bit stops the independent oracle
at its first divergent word, **C=30**, with freeze held and no publication.
This checks component state comparison, not CPU boundary-output comparison.
The final network receipt is `network-vcs-final/generated-network-0fzl_g1v/summary.json`;
full component visibility is retained in `network.vcd` beside it.

Full Scala scope passes **48** tests in six suites. Retained EDA checks pass
all **283** Python tests, generated-bank and existing Widget/transport/host
regressions, the **82** cut-controller checks, and full FCFS native ASan/UBSan
plus VCS (**46** continuations, **296** MMIO calls, **138** pre-edge owner
comparisons, eight malformed fresh processes and **2,972** rejection checks
per backend). All **40** local loop tests pass. The initial ROM probe used
pruned internal ports; its corrected independently emitted probe checks every
row and invalid alias. An initial backpressure testbench active-region race
was fixed by moving readiness changes after sampling. Original failed logs
remain intact. SP2 returned zero after the initial intentional `$fatal`;
the final checker uses a process-exit-only DPI function to return **1** on
failure, and the runner requires both the first-word diagnostic and that
nonzero exit. This function never reads/writes DUT state or advances time.

Native localhost Vivado 2025.2 synthesizes the actual generated bank and the
Widget **with its internal ROM** for `xcvu47p-fsvh2892-2-e`: **138 LUTs / 67
registers**, and **1,725 LUTs / 692 registers**, respectively. Estimated setup
slack is **+6.298 / +4.425 ns** at 140 MHz; these are separate out-of-context
components, not routed Rocket timing or an AFI. DCPs and native reports are in
`runs/aws-f2/iteration179/components-vivado-6BI0vY/` (relative to the loop).

Fresh AWS identity/type access passes. The new isolated exact-Rocket invocation
reuses the installed self-checking workload and initialized manager YAMLs,
with tag `checkpoint-f2-rocket-capture-179`, disabled metasim, one `f2.6xlarge`
and ExternallyProvisioned `[localhost]`. No runtime or AFI was launched.
Final scoped inventory confirms no runtime instance or native Vivado/Java job.
Existing controller checkpoints were published FireSim first (`6c1b277c`),
then Chipyard (`3b5cb16e`); independent remote tips agree. The successful
Chipyard push again could not update its local read-only tracking ref.
No plan, conda, archive, staging or local commit changes were made by this turn.
Managed delegation failed before creating any worker; all implementation and
verification were coordinated directly by the central agent.

Evidence, exact raw commands, immutable source/generated inputs and original
remote paths are under `automations/checkpoint_loop/runs/aws-f2/iteration179/`.
`summary.json` catalogs individual nonempty artifacts and runnable commands;
fresh EDA `audit-c9r6vh90/audit.json` independently verifies **43** files,
current source hashes, all cut receipts, native DCP archive contents and
the final inventory. The earlier arbitrary DCP-size audit assertion was
replaced by archive CRC, actual top/part/OOC metadata and netlist/state checks.
Next: register the global Widget/stream in FPGATop; support real Rocket
synchronous/readwrite RAM pipelines, wide/deep state and annotation translation;
generate complete independent simulator/semantic mappings; freeze/capture every
FAME/channel/FASED, functional-memory and host owner. Full localhost image
synthesis/P&R/AFI, F2 deployment and four active hardware cuts, FPGA-reference
comparison, independent complete zero-edge restores, finite CPU replay,
sustained live RTL/debug waveforms and rolling hardware recovery remain pending.

## Iteration 178: generated storage, real control/stream adapter and host capture

The previous sanitizer feedback is resolved and independently rerun on EDA:
full ASan/UBSan plus fresh VCS FCFS passes **46** continuations, **296** MMIO
calls, **138** pre-edge owner comparisons, eight malformed fresh processes and
**2,972** rejection checks per backend. System GCC/GMP/sanitizer provenance is
retained in `runs/aws-f2/iteration178/fcfs-system-regressions-m2o3tz1m/`.
All **283** checkpoint Python tests pass on EDA; all **40** loop tests pass
on the local manager's existing Chia/Ray environment. A remote loop-discovery
diagnostic is retained: EDA Python 3.9 lacks Ray (and current Chia needs a
newer Python). This is not a VCS or sanitizer block; no checks were removed.

`GeneratedStateBankAccess` now specializes a complete lowered hierarchy per
instance, binds independently named simulator/semantic inventories to real
registers/RAMs, gates functional resets/updates/writes with the accepting-edge
freeze and latches bank responses independently of subsequent abort/release.
Stale/incomplete bindings and unsupported state fail before hardware is
returned. Synchronous/readwrite RAM pipelines, wide/deep unchunked objects,
opaque/derived-clock/analog state, target side effects and unretargeted
annotations remain explicit unsupported cases; only derived CombinationalPath
cache annotations are invalidated/recomputed. Full checkpoint Scala scope:
**40 tests**, four suites. EDA public-port endpoint checks cover all 16 fixture
words three times, functional reset/write freeze, delayed/held responses,
invalid selectors and capture reuse. These are finite component checks.

`CheckpointCaptureWidget` connects the transport to real 32-bit NASTI and
512-bit StreamToHostCPU, with separate AW/W arrival, held responses and
malformed-access/burst errors. It is a global Widget because its host clock
must continue during simulator freeze. Its C++ `checkpoint_capture_t` binds
actual FireSim MMIO/StreamEngine calls to a strict host session that verifies
manifest, complete framing/CRC, selectors, cut and hardware readback before
exposing bytes; freeze remains held through external publication. Host-owner
capture and canonical CPU image publication are not implied by this class.

An initial sanitizer test exposed premature drain acknowledgement after an
empty nonblocking DMA pull. The fix counts every hardware-accepted frame
across captures/aborts, counts every host-consumed frame, and requires exact
equality plus producer quiescence before clearing invalid stream history.
Unknown transfer counts require coordinated reset. Earlier failed test logs
remain unchanged. Final host ASan/UBSan checks: **1,384**, against a fresh
VCS transport stream (**1,294** transport checks and **39** strict decoder
negatives). EDA adapter/Widget checks: **73 / 133**, with five actual fixture
frames. Widget Scala checks: **4**. Evidence, commands, frozen generated/source
inputs and native logs are under `runs/aws-f2/iteration178/`; the final
`summary.json` catalogs individual files and keeps original remote paths.

The new exact-Rocket configs reuse the installed
`checkpoint-f2-rocket-selfcheck-175.json`, initialized YAMLs, disabled metasim,
one `f2.6xlarge`, tag `checkpoint-f2-rocket-capture-178`, and
ExternallyProvisioned `[localhost]` with invocation-local `build-host/`.
The earlier unused `checkpoint-build/` preparation named a nonexistent workload;
retain it as diagnostic and use **`checkpoint-build-installed-workload/`**.
Fresh AWS identity/type access and tagged inventory succeed; no runtime
instance or AFI was launched. Existing controller commits were pushed FireSim
first (`9d729e59`), then Chipyard (`37604207`); remote tips independently agree.
The successful Chipyard push again could not update its local read-only
tracking ref; no history or plan files were staged/committed by this agent.

Next: register the global Widget and its stream in FPGATop; generate complete
independent simulator/semantic mappings and descriptor ROMs; support the real
Rocket RAM/width/annotation cases; connect all generated/FAME/channel/FASED,
functional-memory and host-owner freeze/capture. Then perform localhost full
image synthesis/P&R/AFI creation, deploy to F2, capture the four active cuts,
and prove independent fresh complete readback, FPGA-reference continuation,
finite replay, sustained live RTL/debug waveforms and rolling recovery.
The bank/Widget native Vivado runs are component synthesis, not a Rocket AFI.
Both complete successfully on localhost Vivado 2025.2 for the actual F2 part:
bank endpoint **138 LUTs / 67 registers**, Widget **1,878 LUTs / 756 registers**;
estimated post-synthesis setup slack **+6.298 / +4.432 ns** at 140 MHz.
`components-vivado-CUPhQl/source-binding.json` independently matches synthesis
inputs to the EDA-generated-file hashes. DCPs, native reports and the complete
command log are retained. Final scoped inventory has no runtime instances or
native Vivado/Java jobs. Fresh final endpoint/cut VCS checks pass **571 / 82**;
the final endpoint receipt matches current generator/spec/testbench/runner
sources. No worker or background LLM work remains after central integration.
The final combined local Scala invocation also passes **44/44** tests across
five suites, with all generated evidence in its fresh `scala-reverify-*/`
workspace. The final independent EDA evidence audit passes **98**
source/artifact hash checks in `evidence-audit-kgmvzvrq/audit.json`.
Keep the retained earlier failed trials separate.

## EDA dependency recovery after stopped iteration 177

The FCFS dependency block is **resolved**. EDA's GCC 11.5 linker scripts named
missing ASan/UBSan runtime files. Passwordless sudo was available, so recovery
installed Rocky's matching `libasan-11.5.0-14.el9` and
`libubsan-11.5.0-14.el9`. The next VCS link exposed the private GMP workaround's
static archive before the referencing objects. Installed matching system
`gmp-devel-6.2.0-13.el9` (and its `gmp-c++` dependency); system GMP runtime was
already present. No compiler, Conda, HDL or acceptance scope was changed.
Use native EDA system headers/shared GMP and source `vcs-env.sh` last. Do not
source the old `eda-gmp-WxqXPP/setup.sh` by default: its static-library search
path causes the VCS archive-order failure. That earlier private build remains
retained evidence, not the current environment requirement.

The **full** native ASan/UBSan plus fresh VCS FCFS regression passes:
46 fresh continuations, 296 matched MMIO calls, 138 pre-edge owner comparisons,
eight malformed fresh processes, and 2,972 rejection checks on **each** backend.
`ldd` confirms the native executable loads `libasan.so.6` and `libubsan.so.1`.
The native/VCS build logs, exact command, package versions/install log, runtime
library paths, checksums and summary are under
`runs/aws-f2/iteration177/fcfs-system-deps-recovery-o2_ehox6/` relative to the loop.
The ASan-fixed/private-GMP VCS failure remains separately preserved in
`fcfs-sanitizer-recovery-7whvv8z9/`; original stopped-iteration logs are unchanged.
All 40 current loop tests pass locally. The agent prompt now requires diagnosis
and routine dependency repair using available access before declaring an
external block; keep all sanitizers and required regressions enabled.

Saved state remains iteration 177 / hardware milestone in_progress; normal
restart starts iteration 178. No controller acceptance was advanced manually.
This verifies the retained component regression, not complete Rocket hardware
checkpoint capture, which still requires the implementation work below.

## Iteration 177: synthesized bank/MMIO/DMA transport component

Hardware milestone remains **in_progress**. At the original iteration-177
stop, the required FCFS regression failed on EDA's missing native sanitizer runtime:
`/usr/bin/ld: cannot find /usr/lib64/libasan.so.6.0.0`. Do not omit that regression
or claim CPU acceptance. Exact failing `/usr/bin/g++ ... -fsanitize=address,undefined
... -lgmp` argv and native output are in
`runs/aws-f2/iteration177/fcfs-regression-LLdYDi/native-build.log`.

`CheckpointCaptureTransport.sv` now joins the existing atomic cut component
to delayed logical bank requests, generated descriptor-ROM inputs, held MMIO
responses and 512-bit DMA framing. It includes manifest/cut/selector/word
labels, CRC32C, explicit descriptor/bank/padding failures, held freeze through
publication and stale accepted-read draining after abort. It still needs real
Rocket bank endpoints, global generated-state freeze, BridgeModule/control-bus
and FireSim DMA integration, and complete memory/host owners. Both checkpoint
levels remain independent. No checkpoint-enabled AFI/image build, F2 capture,
CPU restore, finite/live CPU comparison, waveforms or rolling hardware
recovery was performed. See [fpga-capture-transport.md](fpga-capture-transport.md).

Evidence root: `automations/checkpoint_loop/runs/aws-f2/iteration177/`.
Fresh EDA VCS SP2 transport verification under `transport-verified/` passes
**1,294** checks, five healthy publications, 36 bank requests, 48 DMA stalls and
228 MMIO stalls. The strict host codec rejects **39** damaged variants of its
actual public-port stream before returning state. Its six-word fixture
`.rtlckpt` is VCS/component-origin, not a hardware CPU checkpoint. Sources,
manifests, exact argv, checksums and native logs are frozen in that invocation.
Fresh localhost Vivado 2025.2/HDK setup and component synthesis pass with
**2,055 LUTs / 423 registers**, estimated +4.816 ns setup slack at 140 MHz.
This is out-of-context synthesis, not full-image P&R. The first HDK setup
attempt used the wrong working directory; its log is retained, and the actual
successful command sources `hdk_setup.sh` from the HDK repository directory.
The complete native synthesis output is `transport-vivado-command.log`.
An EDA return sync overwrote `transport-vivado.log` with its older input copy;
that partial file is retained as diagnostic, not used as completion evidence.
`eda.py fetch` now uses `rsync --update` to preserve newer local manager logs
while still receiving new/newer EDA output; a real-rsync regression covers both.
All six helper tests pass locally and in a fresh EDA invocation, including
failure-result collection, control-file protection and concurrent log retention.

All **283** Python tests pass on EDA Python 3.9 after replacing the unavailable
`Path.hardlink_to` test helper with equivalent `os.link`; all **82** cut checks
pass. The retained FCFS script first failed on missing `gmp.h` (`gmp-devel`
is absent). A private matching GMP 6.2.0 source build and its full `make check`
pass under `eda-gmp-WxqXPP/`, with archive hash/configuration/native logs. No
system or Conda files were changed during that original turn. Its `setup.sh`
supplied the private headers/archive, after which FCFS reached the linker and
failed on the missing ASan runtime above. This was the original stopped-turn
state, not the current recovery procedure; the subsequent
system-package recovery above resolves it and the private archive-order issue.
Initial Python-3.9/header failures and the stopped broad dependency probe are
retained separately. No regression scope was reduced.

Fresh manager/AWS access succeeds. New isolated exact-Rocket checkpoint
configs in `checkpoint-build/` use ExternallyProvisioned `[localhost]`, local
`build-host/`, one `f2.6xlarge`, tag `checkpoint-f2-rocket-capture-177`, disabled
metasim and no invented AGFI. Final scoped AWS inventory has no instance for
that tag, reconfirms the previous baseline instance terminated, and records no
native Vivado/Java job. No AFI request was started. Existing controller-created
commits were published FireSim first (`355cb7fe`), then Chipyard (`25acc5b5`);
independent remote tips match. Chipyard's local tracking-ref update again failed
read-only after its successful remote push. The controller owns subsequent
staging/commits/publication. No worker was successfully started; the native
subagent startup failed and the central agent performed this increment.

## Active F2 bring-up recovery

Evidence root: `automations/checkpoint_loop/runs/aws-f2/iteration175/`.
The `baseline/manager-commands.json` contains exact raw manager commands and
source-config hashes. Runtime uses one Rocket node, public
`agfi-0c5eedfce0e568971`, and `metasimulation_enabled: false`.
`instance.json`, `aws-identity.json`, `aws-region.txt`, and
`resources-running.json` independently record AWS identity and resources.
The first broad inventory used the wrong tag key (`firesim`); use the corrected
`f2_inventory.py`, which queries FireSim's actual `fsimcluster` key. Its result
is an inventory, never a target-pass receipt.

`launchrunfarm.log` and `infrasetup.log` retain actual manager output; copy the
corresponding native deploy logs into this evidence root before cleanup.
The installed workload is `checkpoint-f2-rocket-selfcheck-175.json`; its JSON
and input directory are symlinked from deploy/workloads into this evidence
root. Retained ELF hash/bytes are in `workload-provenance.json`. Independent
fresh compiler/Spike checks pass the healthy four-hart workload and all four
corruption variants in `workload-fresh/`; this is workload validation only.
All 37 loop/config/inventory unit tests pass in `test-loop-all.log`.
`baseline-audit.json` cross-checks actual runtime, independent identities,
loaded image, deployed hashes, target PASS and final cleanup. Nine offline
evidence forgeries reject in `baseline-audit-negatives.json`.

Local build prerequisites: native Vivado 2025.2; F2 HDK `80b34d3`, shell
`0x10212415`; actual `hdk_setup.sh -s` version/environment check passes.
This check omits shell downloads and is not a bitstream build.
Fabric and default-key localhost SSH pass. A separate OpenSSH check with only
`~/firesim.pem` failed public-key authentication; it does not prevent Fabric
from using the existing default localhost key. Preserve both diagnostics.
Generated `checkpoint-build/` configs select ExternallyProvisioned localhost,
an invocation-local build directory, and an empty HWDB (no invented image).
The existing banked module is a component prototype, not a connected Rocket
capture network. New `CheckpointCaptureCut.sv` starts the owner-acknowledged
atomic cut implementation. Native Vivado OOC synthesis on this server for
the real F2 device passes with 16 owners (56 LUTs, 74 registers), with source
hash and DCP/reports in `local-build-receipt.json` and `cut-vivado/`.
EDA source/input migration sync completed. At the stopped iteration 175,
VCS SP2 failed before parsing with `Cannot find license file` (exit 255).
The original failure logs remain in `cut-vcs/`, including `compile-retry.log`,
`command.stdout`, `compile-returncode.txt`, `license-environment.log` and
`license-candidates.log`. This is historical failure evidence, not the current
license status. The corrected helper and fresh EDA run in
`eda-license-confirmed-7rd4saf_/` establish compile/runtime checkout and all
82 cut-component checks. Its `verification-commands.json` records the actual
argv; when running again, choose a fresh output directory and retain
`-timescale=1ns/1ps`, `-full64`, and `vcs-env.sh` sourced last. Do not substitute
local simulation or relabel the old failing logs as passing. The helper initially fetched an older
copy of its redirected transcript; subsequent transport transcripts use
`runs/loop.log-eda-*` (excluded from fetch) and compiler stdout is recorded
directly on EDA. The actual compiler failure is preserved, not inferred.
This component is not integrated; no full checkpoint-image synthesis/P&R,
AFI creation or capture is claimed. See [f2-rocket-image.md](f2-rocket-image.md)
for remaining build admission work.

Existing controller-created commits were pushed FireSim first, then Chipyard;
both reported `Everything up-to-date`. Chipyard's local tracking-ref update
failed read-only, so preserve the push log and do not rewrite history.
The supplied `runs/verification.log` was absent on this migrated checkout;
historical summaries are not newly audited acceptance evidence.

## Historical metasim/component work (retained)

Historical milestone: M11-rocket-level1-level2, iteration 175, in progress.
Prepared/sealed publication now covers the private-memory/disconnected blockdev
owner. Preparation owns all queues, trackers, disk bytes and a positioned libc
stream. Guarded allocation-free `noexcept` publication swaps resources and
assigns two flags, with no libc I/O/MMIO/edge. The candidate retires old streams
and backing afterward. Legacy loads use the same guarded path. External
files/logs and suspended/poisoned calls reject. See
[blockdev-sealed-publication.md](blockdev-sealed-publication.md).

Native ASan/UBSan and fresh VCS pass 30 prepared continuations, complete pre-edge
readback and 25,870 continued MMIO calls across all fifteen component cuts.
Each backend passes 756 candidate rejections, 65 preparation and 44 sealing
allocation failures and both libc preparation failures. Twelve fatal contract
cases, two unexpected-return controls, eight malformed fresh loads and two
actual first-boundary tracker corruptions at fixture C=142 pass. Eight rehashed
offline forged receipts reject. These are host components, not Rocket Level-1
restores. Prepared receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/blockdev-prepared/native-33p9_drw/summary.json`.

All eight preserved native scopes pass, including 280 Python tests plus
semantic/banked, widget, FCFS, UART, blockdev and heartbeat. Legacy blockdev
independently passes all 30 continuations; prepared concrete-driver checks pass
224 fresh continuations. Both exact-recipe 16-GiB four-hart VCS controls pass
at C=3,329,794, with every complete hart trace and decoded workload/store label
matching the uninterrupted reference. These are CPU controls, not Level-1
restores. All nine final independent audits pass, twice. Explicit receipt
selection replaces ambiguous singleton/glob selection; two repeated audits
succeed with sibling builds present. Native source snapshots remain immutable;
checker-only completion/path corrections followed the frozen execution runs.

The retained Rocket Level-2 audit passes all four original cuts (C=100 /
700,000 / 900,000 / 3,250,000), 318,637 pre-edge words per cut, 256 events,
sixteen actual first divergences and 44 invalid cases. This re-audits retained
ordinary RTL VCS artifacts. Six unchanged publication/I/O/base audits and the
prepared/legacy heartbeat audits pass. The current exact-recipe census/link
checks retain 15 widgets, 11,464 generated entries / 445,838 words, the new
blockdev adapter and all three CPU admission guards. Three fresh capability/
owner denials create no image; they are not CPU-image parser tests.

Exact receipts, source/workload hashes and executable VCS commands are in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/verification-commands.json`.
Full artifact catalog:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/artifact-manifest.json`.
The storage manifest preserves 132 inactive compiler-IR files (3,198,216,645
bytes) with verified identical bytes and links at their original paths:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/cold-artifact-storage.json`.
Retain its `/tmp` storage. Logs/images/traces remain under runs; no test scope
was reduced. Existing controller-created FireSim and Chipyard heads were pushed
in that order; remote tips match despite local tracking-ref write warnings.
No staging, local commit or plan/environment edit occurred.

Next: prepared UART, FASED and four TracerV owners, then a production coordinator
joining complete generated/harness, memory, I/O, scheduler/loop and creator-side
TSI state under process/thread/signal/descriptor/parser exclusion. Generic
aggregate loading remains sequential legacy publication. Source-bound recovery:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/remaining-owner-audit.json`.
Complete Rocket Level 1 remains disabled/in progress; independent Level 2 stays
separate. BOOM/Saturn remain pending. No dependency is missing and no plan
correction is proposed. Standalone Shuttle, FPGA validation and ASIC power
remain outside scope.

Previous iteration 174 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 174, in progress.
Prepared/sealed publication now covers the buffered, unfinished heartbeat owner.
Preparation owns every decoded sample and stamps the full destination payload;
sealing checks lifetime/thread/generation/consumption before owner access.
Allocation-free `noexcept` publication swaps samples and assigns four scalars,
with no tick/time/localtime/MMIO/output/edge. Legacy load invalidates candidates.
The v1 payload is unchanged; live-log/finished/suspended/poisoned modes reject.
Details: [heartbeat-sealed-publication.md](heartbeat-sealed-publication.md).

Native ASan/UBSan and fresh VCS pass 96 prepared continuations, 96 complete
pre-edge owner readbacks and 1,260 matched MMIO calls across all sixteen cuts
in three polling scenarios. Both backends pass 904 candidate rejections,
102 preparation and 66 sealing allocation failures, twelve fatal contract
cases, two unexpected-return controls, eight malformed fresh loads and two
actual first-boundary polling corruptions at fixture cycle 107. Eight offline
rehashed forged-receipt controls reject. These are host components with fixture
MMIO and substituted diagnostic wall time, not Rocket Level-1 restores.
Selected receipt: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/heartbeat-prepared/native-yun3bzvd/summary.json`.

The independent retained Rocket Level-2 audit passes all four original cuts
(C=100 / 700,000 / 900,000 / 3,250,000), 318,637 pre-edge words per cut,
256 events, sixteen actual first divergences and 44 invalid cases. This is a
re-audit of retained ordinary RTL VCS artifacts, not a new Rocket replay run.
The current exact-recipe build/link census retains 15 host widgets,
11,464 generated entries / 445,838 words, the heartbeat prepared adapter and
all three CPU admission guards. Three new native capability/owner denials
create no image; they are not CPU-image parser tests.

All eight preserved regression scopes pass, including 280 Python tests,
semantic/banked, widget, FCFS, UART, blockdev and heartbeat checks. The legacy
heartbeat matrix independently passes all 96 continuations. The prepared
concrete-driver regression passes all 224 fresh native/VCS continuations.
Six unchanged publication/I/O/base evidence audits also pass.
Native suite: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/native-regressions/invocation-j8xhqpnf/summary.json`.
Driver: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/driver-regression/invocation-i2hecxq3/summary.json`.

Both new exact-recipe 16-GiB four-hart controls pass at C=3,329,794. Every
complete hart trace and decoded workload/store label matches the uninterrupted
reference. These are full CPU controls, not Level-1 restores. Selected receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/rocket/invocation-qg7mpk66/summary.json`.
Both environments and vcs-env.sh last are sourced for native VCS builds/runs,
using Y-2026.03-SP1, -full64, GCC/G++ 13 and reused Make VCS_FLAGS=-Mupdate.
Exact source/workload hashes, recipe settings and executable commands are in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/verification-commands.json`.
All seven final independent source/evidence audits pass. The complete full-path
artifact catalog is `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/artifact-manifest.json`.
No external dependency is missing.

Workspace capacity required relocating 68 inactive compiler-IR files (2,971,569,360
bytes) from retained diagnostic builds to `/tmp`, with identical verified bytes
and links at their original paths. Preserve the storage listed in
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/cold-artifact-storage.json`.
Logs/images/traces remain under `runs/`; no check is reduced or cancelled.
Existing controller-created FireSim and Chipyard commits were published in that
order; remote tips match despite local tracking-ref write warnings. No staging,
local commit, reset or cleanup occurred. Plans/environment inputs remain read-only.

Next: prepared publication for blockdev, UART, FASED and four TracerV owners;
then one production coordinator joining all generated/harness, memory, I/O,
scheduler/loop and creator TSI state under thread/signal/descriptor/parser
exclusion. Generic aggregate loading still uses sequential legacy publication.
Complete Rocket Level 1 stays disabled/pending; independent Level 2 stays
separate. Source-bound recovery: `runs/m11-iteration174/remaining-owner-audit.json`.
BOOM/Saturn are pending; standalone Shuttle, physical FPGA and ASIC power are
outside scope. No plan correction is proposed.

Previous iteration 173 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 173, in progress.
Added prepared/sealed publication for the separate
`simulation_t::base_checkpoint_t` lifecycle owner. The fresh destination stamp
covers every base lifecycle/performance field and complete configuration/widget
binding, independently of running-source save. Preparation owns decoded scalars;
publication is allocation-free `noexcept`, assigning only start baselines,
`run_done`, running phase and loaded flag. Lifetime/thread/generation/consumption
guards precede owner access. Legacy load invalidates candidates. No initialization,
reset, timestamp, MMIO or output occurs. Details:
[base-lifecycle-publication.md](base-lifecycle-publication.md).

Native ASan/UBSan and fresh VCS pass 24 prepared and 24 legacy continuations,
with complete pre-edge payload readback and 264 continued MMIO calls per matrix.
The prepared matrix passes 1,216 rejections, 64 preparation and 32 sealing
allocation failures, twelve fatal contract cases, eight malformed fresh loads
and four actual first-boundary `run_done` corruptions. Two unexpected-return
controls exit 88. Eight rehashed offline forged-receipt controls reject.
These are actual base-flow components with fixture drivers/MMIO/bridges, not
Rocket Level-1 images or target-cycle continuation. Selected prepared receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/base-prepared/invocation-8xtddnom/summary.json`.

The prepared concrete-driver regression passes all 224 fresh continuations.
All eight preserved native scopes pass, including 280 Python tests plus
semantic/banked, widget, FCFS, UART, blockdev and heartbeat checks. Five unchanged
publication/I/O evidence audits pass. The independent retained Level-2 audit
passes all four original Rocket windows (C=100 / 700,000 / 900,000 / 3,250,000),
318,637 pre-edge semantic words per cut, 256 events, sixteen actual first
divergences and 44 invalid cases. This iteration re-audits those ordinary RTL
VCS artifacts; it does not claim a new Rocket replay simulation.

Both new exact-recipe 16-GiB four-hart direct-exit controls pass at C=3,329,794;
every complete hart trace and decoded workload/store label matches the
uninterrupted reference. These are full CPU controls, not Level-1 restores.
Selected receipt: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/rocket/invocation-vetn068e/summary.json`.
The final independent current-source audits pass. Exact settings, workload/source
hashes and executable native commands are in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/verification-commands.json`.

The current exact-recipe build census and symbol audit retain 15 host widgets,
11,464 generated entries / 445,838 words, both lifecycle adapters and all three
CPU admission guards. Three fresh native capability/owner denials create no
CPU image; these are not CPU-image parser tests. Workspace capacity required
moving 44 inactive compiler-IR files from this new invocation to separate
`/tmp` storage, with verified bytes and links at their original paths; see
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/cold-artifact-storage.json`.
Workspace capacity recovered during the controls; all 44 intermediates were
reinstated as regular files at their original paths, with identical bytes.
Logs/checkpoints/traces remain under `runs/`; no test was reduced or cancelled.
Existing controller-created FireSim and Chipyard heads were published in that
order with matching remote tips. No staging/local commit occurred. Plan and
environment inputs retain their initial bytes. No external dependency is missing.

Heartbeat is the next smallest owner requiring prepared publication, followed by
blockdev, UART, FASED and all four TracerV owners. Complete generated RTL/FAME/
channels/harness, memory, runtime I/O, scheduler/loop and creator-side TSI still
need one production coordinator and process thread/signal/descriptor/parser
exclusion. Generic aggregate loading remains sequential legacy publication.
Source-bound recovery: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/remaining-owner-audit.json`.
Complete Rocket Level-1 fresh continuation remains pending; independent Level 2
stays separate. BOOM/Saturn are pending. Standalone Shuttle, physical FPGA and
ASIC power remain outside scope.

Previous iteration 172 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 172, in progress.
The concrete FireSim driver now explicitly prepares a fresh lifecycle destination,
seals the complete configuration/registry stamp and publishes only `started`
through allocation-free `noexcept` code. Running source capture retains its v1
payload; destination stamping never calls running-source save. Lifetime, native
thread, generation and consumption guards precede owner access. Legacy load
invalidates candidates. Publication performs no init/reset/MMIO/step/finalization.
The driver remains noncopyable/nonmovable.

Final native ASan/UBSan and fresh VCS component checks pass 224
continuations, 2,464 complete fixture-owner readbacks,
4,846 service boundaries, 1,490 invalid-publication
rejections, 82 preparation and 40 sealing allocation failures,
12 fatal contract cases, 16 malformed/incomplete fixture loads and
2 actual first-boundary cursor corruptions. Two deliberate unexpected-return
controls fail with exit 88; seven rehashed offline forged-receipt controls reject.
Review found and corrected a fatal-fixture fallthrough weakness. Both complete
driver matrices and all eight preserved native scopes ran again with corrected
fixture bytes; preliminary driver receipts are not selected final evidence.
These are actual driver components with fixture MMIO/bridges, not Rocket Level-1
restores or Rocket target-cycle continuation. Final receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/driver-final/invocation-rd6me6o5/summary.json`.

The final eight-scope envelope passes 280 Python tests and semantic, banked,
widget, FCFS, UART, block-device and heartbeat native checks. Stream, MMIO,
CPU-managed I/O and configuration/scalar/control publication regressions pass.
Independent ordinary RTL VCS replay retains all four Rocket cuts at C=100 /
700,000 / 900,000 / 3,250,000: 318,637 semantic words read back before any edge
per cut, 256 captured events, sixteen actual first divergences and 44 invalid
cases. Both exact-recipe 16-GiB four-hart direct-exit controls pass at C=3,329,794;
every complete hart trace and workload label matches the uninterrupted reference.
These are uninterrupted CPU controls; production binary inputs did not change
when the driver-only fixture was corrected. Exact sources/workload hashes,
commands and selected receipts are in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Fourteen final independent audits pass. The actual build census/link audit
retains 15 host widgets, 11,464 generated entries / 445,838 words, the concrete
driver's prepared adapter and all three CPU admission guards. Three fresh native
capability/owner denials create no CPU image; they are not CPU-image parser tests.
Existing controller heads reached both GitHub forks, FireSim first, with remote
tips verified despite local tracking-reference write warnings. No staging or
local commit occurred. Plans and environment helpers remain read-only inputs.
No external dependency is missing; no test was cancelled or reduced.

Complete CPU admission remains disabled. The separate
`simulation_t::base_checkpoint_t` lifecycle owner still lacks prepared publication;
it must not be conflated with the concrete driver. Prepare that base owner,
heartbeat, blockdev, UART, FASED and all four TracerV owners, then join generated
RTL/FAME/channels/harness, memory, runtime I/O, scheduler/loop and creator-side
TSI under production controller/creator/thread/signal/descriptor/parser exclusion.
The generic aggregate still loads legacy owners sequentially. The source-bound
recovery ledger is `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/remaining-owner-audit.json`.
Complete Rocket Level-1 fresh continuation remains pending. Independent Level 2
stays separate; BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA
validation and ASIC power remain outside scope.

Previous iteration 171 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 171, in progress.
Added explicitly opted-in prepared publication for production CPU-managed stream
initialization and peek/poke returned-call unstable/timeout flags. Complete source
configuration/payload and destination bytes validate before scalar-only,
allocation-free `noexcept` publication. Lifetime/native-thread/generation/
consumption guards precede owner access; identical-byte legacy loads invalidate
candidates. Both final concrete owners are noncopyable/nonmovable. Suspended and
interrupted services remain unsupported. Recovery:
[scalar-sealed-publication.md](scalar-sealed-publication.md).

Final-source native ASan/UBSan and time-zero VCS DPI pass 40 fresh component
restores, 244 complete owner comparisons, 418 service boundaries, 34,440 invalid
rejections, 1,360 exhaustive allocation failures and 24 fatal contract checks.
The independent full-byte/MMIO/DMA oracle and five offline forged-receipt controls
pass. The selected receipt is
`runs/m11-iteration171/scalar-verified/invocation-ziqgcxqh/summary.json`.
These are two actual host owners with fixture MMIO/DMA/clock services, not
complete Rocket Level-1 checkpoints or target-cycle continuation. The initial
fixture compile diagnostic and an earlier source-drift rejection remain separate.

The final-source eight-scope repeat passes 280 Python tests and preserved
semantic, banked, widget, FCFS, UART, block-device and heartbeat native checks.
Stream/MMIO/CPU-managed I/O and configuration publication regressions pass.
An earlier native envelope completed all eight checks then rejected source drift;
the selected repeat is `runs/m11-iteration171/verified/native-confirmed/invocation-q8mph5lg/summary.json`.
Fresh ordinary RTL VCS and its independent full-source audit pass all four
retained Rocket windows: 318,637 words before any edge per cut, 256 captured
events, sixteen actual first divergences and 44 invalid cases. The replay receipt
is `runs/m11-iteration171/regressions/native-replay/invocation-s35wxbbl/summary.json`.
These results retain the independent Level-2 evidence; they do not enable Level 1.

Both exact-recipe 16-GiB four-hart direct-exit controls pass at C=3,329,794;
every complete hart trace and decoded workload label matches the uninterrupted
reference. The selected receipt is
`runs/m11-iteration171/verified/rocket/invocation-4cpr4qqv/summary.json`.
These are uninterrupted CPU controls, not complete Level-1 continuations.
The preserved scheduler/bridge-loop publication matrix also passes. Exact
workload/source hashes and commands are in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md)
and the receipts under `runs/m11-iteration171/`.

All twelve final independent audits pass. The source census and linked-symbol
audit retain 15 host widgets, 11,464 generated entries / 445,838 words, both new
scalar APIs and all three CPU admission guards. Three fresh native capability/
owner denials and their audit create no CPU image; these are not malformed
CPU-image parser tests. Selected receipts, exact workload/source bindings,
executable commands and full-path artifacts are `selected-results.json`,
`workloads.json`, `native-input-archives.json`, `verification-commands.json`,
`raw-native-commands.json` and `artifact-manifest.json` under `runs/m11-iteration171/`.
Existing controller heads reached both GitHub forks, FireSim first, with remote
tip verification despite local tracking-reference write warnings. Plans,
environment helpers, heads and the root index retain their starting bytes;
both cached diffs remain empty. No staging/local commit occurred. No external
dependency is missing. No test was cancelled or reduced.

Complete CPU admission remains disabled. The next smallest owner is the concrete
FireSim driver's fresh lifecycle; the source-only save cannot stamp a fresh
destination. The read-only recovery audit is
`runs/m11-iteration171/next-driver-publication-audit.json`. Prepare/seal that owner,
blockdev, UART, FASED, four TracerV owners and heartbeat, then join all owners with
generated RTL/FAME/channels/harness, memory, runtime I/O, scheduler/bridge-loop and
creator-side TSI under production controller/creator/thread/signal/descriptor/
parser exclusion. The generic aggregate still loads legacy owners sequentially.
Complete fresh Rocket Level-1 continuation at all four active-workload cuts
remains pending. Independent Level 2 stays separate; BOOM/Saturn remain pending.
Standalone Shuttle, physical FPGA validation and ASIC power remain outside scope.

Previous iteration 170 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 170, in progress.
Added explicitly opted-in prepared publication for production master, clock,
loadmem and reset-pulse configuration-only host owners. Complete source and
current destination bytes must match. Sealing checks lifetime/native-thread/
generation/consumption; publication is allocation-free `noexcept` with no MMIO,
target edge or host-state assignment. Identical-byte legacy loads invalidate
candidates. All four owners are noncopyable/nonmovable. Suspended/interrupted
calls remain unsupported. Recovery:
[configuration-sealed-publication.md](configuration-sealed-publication.md).

Final-source native ASan/UBSan and time-zero VCS DPI pass 24 fresh component
restores, 296 complete owner comparisons, 154 service boundaries, 22,248 invalid
rejections, 2,472 exhaustive allocation failures and 48 fatal contract checks.
The independent full-byte/MMIO oracle and five offline forged-receipt controls
pass. The final receipt is
`runs/m11-iteration170/configuration-final/invocation-4k90qdxr/summary.json`.
These are four actual host owners with deterministic fixture services, not
complete Rocket Level-1 checkpoints or target-cycle continuation.

All fifteen broader checks and twelve independent audits pass. The eight
preserved native scopes retain 280 Python tests plus semantic/banked, FCFS,
widget, UART, block-device and heartbeat native VCS checks. Creator/harness,
dispatcher, stream/DMA, MMIO, runtime I/O, memory, scheduler/bridge-loop and the
production TSI matrix pass. Thirty retained auditors and thirteen retained
I/O/memory receipts pass. A retained-receipt wrapper initially selected the DMA
auditor for a memory receipt; corrected routing passes all thirteen receipts and
preserves the failed diagnostic. Additional audits retain all 32 dispatcher
diagnostics, 336 unpublished TSI invalid cases and 128 unpublished cancellations.

Fresh ordinary RTL VCS and its independent full-source audit pass all four
retained Rocket windows at C=100 / 700,000 / 900,000 / 3,250,000: 318,637 words
read back per cut before any edge, 256 captured events, sixteen first semantic
divergences and 44 invalid cases. Both exact-recipe 16-GiB four-hart direct-exit
controls pass at C=3,329,794; all four ordinary/restricted and buffered/unbuffered
syscall controls pass at C=3,330,050. Complete hart traces and decoded workload
labels match within each protocol. These CPU controls are uninterrupted runs,
not complete Level-1 continuations. Final selected receipts, exact workload/source
hashes and executable native commands are `summary.json`, `selected-results.json`,
`workloads.json`, `native-input-archives.json`, `verification-commands.json`,
`raw-native-commands.json` and `artifact-manifest.json` under
`runs/m11-iteration170/`; see [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

The source census and linked-symbol audit retain 15 host widgets, 11,464
generated entries / 445,838 words, all four prepared widget APIs and all three
CPU admission guards. Three fresh capability/owner denials and their independent
audit create no CPU image; these are not malformed CPU-image parser tests.
Existing controller heads reached both GitHub forks, FireSim first; independently
read remote tips match despite local tracking-reference write warnings.
Plans, environment helpers, heads and indices retain their starting bytes.
No staging or local commit occurred. No external dependency is missing.
No test was cancelled or reduced.

The remaining-owner read-only audit binds seventeen source files in
`runs/m11-iteration170/remaining-publication-owner-audit.json` and records
mutable flags, nested UART state, FASED/TracerV/heartbeat output ownership,
blockdev libc-resource preparation/retirement and the driver's fresh-state
boundary. The smallest next increment is CPU-managed stream initialization,
peek/poke result flags and the concrete driver's fresh lifecycle candidate;
none can use the configuration-only equality adapter for differing values.

Complete CPU admission remains disabled. Prepare/seal CPU-managed stream control,
peek/poke, block device, UART, FASED, four TracerV owners, heartbeat and the concrete
driver, then join them with generated RTL/FAME/channels/harness, memory, runtime
I/O, scheduler/bridge-loop and creator-side TSI under production
controller/creator/thread/signal/descriptor/parser exclusion. The generic
aggregate still loads legacy owners sequentially. Complete fresh Rocket Level-1
continuation at all four active-workload cuts remains pending. Independent
Level 2 remains separate; BOOM/Saturn remain pending. Standalone Shuttle,
physical FPGA validation and ASIC power remain outside scope.

Previous iteration 169 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 169, in progress.
Added a default-unsupported prepared-owner interface and production scheduler /
bridge-loop adapters with complete sealing before allocation-free `noexcept`
publication. Lifetime, native thread, generation, seal and consumption guards
reject invalid candidates; identical-byte legacy loads invalidate them. Both
owners are noncopyable/nonmovable. Recovery:
[control-sealed-publication.md](control-sealed-publication.md).

Final-source native ASan/UBSan and time-zero VCS DPI pass 48 fresh component
restores, 776 complete owner comparisons, 3,120 service boundaries, 12,336 invalid
rejections, 3,072 exhaustive allocation failures and 288 fatal contract checks.
The independent full-state/event oracle and five explicitly offline adversarial
auditor controls pass. These are two actual host owners with synthetic services,
not a whole-simulator restore. The final receipt is
`runs/m11-iteration169/control-final/invocation-92_ldc4m/summary.json`.

All fourteen broader checks and eleven independent audits pass. The eight
preserved native scopes (280 Python tests), creator/harness matrix, dispatcher
guards, stream, MMIO, DMA, runtime I/O, memory and production TSI pass. Thirty
retained auditors and nine retained I/O/memory receipts pass. The four fresh
ordinary RTL windows and independent full-source audit pass 318,637 pre-edge
words per cut, 256 events, sixteen first semantic divergences and 44 invalid
cases at C=100 / 700,000 / 900,000 / 3,250,000. Both exact-recipe 16-GiB four-hart
direct-exit controls pass at C=3,329,794. All four ordinary/restricted and
buffered/unbuffered syscall controls pass at C=3,330,050. Complete hart traces
and decoded workload labels match within each protocol. These uninterrupted
CPU controls do not establish Level-1 restore. Final selected receipts, exact
workload/source hashes, executable native commands and the full-path artifact
index are `summary.json`, `selected-results.json`, `workloads.json`,
`native-input-archives.json`, `raw-native-commands.json`,
`verification-commands.json` and `artifact-manifest.json` under
`runs/m11-iteration169/`. Both control and memory offline forged-receipt tests
reject all five altered receipts after artifact hashes are recomputed.

The source-bound census and linked-symbol audit retain 15 host widgets,
11,464 generated entries / 445,838 words, both new control publication APIs,
and all three CPU admission guards. Three current-binary requests and their
independent audit retain unsupported owner/capability denial with no CPU image
created; these are not malformed CPU-image parser tests. Additional audits
retain all 32 dispatcher diagnostics, 336 TSI invalids and 128 unpublished
prepared/sealed cancellations. Both existing controller heads reached GitHub,
FireSim first then Chipyard, with independently verified remote tips despite
local tracking-reference write warnings. No staging or local commit occurred.
Plans, environment helpers, heads and indices retain their starting bytes.
No external dependency is missing. No test was cancelled or reduced.

Complete CPU admission remains disabled: prepare/seal the remaining widgets and
concrete driver, join memory/I/O/creator-side TSI/generated RTL/harness under
production controller/creator/thread/signal/descriptor/parser exclusion, and
validate fresh whole-CPU continuation at all four workload cuts. The generic
aggregate still loads legacy owners sequentially. Independent Level 2 remains
separate; BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA validation
and ASIC power remain outside scope.

Previous iteration 168 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 168, in progress.
Production `mm_magic_t` now prepares and seals its complete functional-memory
payload before allocation-free, nonthrowing publication, preserving the mmap
address and backing-memory aliases. Lifetime/thread/seal/consumption/generation
guards reject stale candidates, including after identical-byte legacy loads.
CPU aggregate admission remains disabled. Recovery:
[functional-memory-sealed-publication.md](functional-memory-sealed-publication.md).

Final-source native ASan/UBSan and time-zero VCS DPI pass 16 fresh component
restores, 200 complete owner comparisons, 420 AXI boundary samples, 728 invalid
rejections, 2,152 exhaustive allocation failures and 112 fatal contract checks.
The independent byte/queue/strobe oracle and five explicitly offline adversarial
auditor controls pass. These use 4-KiB component mappings, not a complete 16-GiB
Rocket checkpoint. The final memory receipt is
`runs/m11-iteration168/memory-final/invocation-h3ent2gp/summary.json`.

The eight preserved native scopes (280 Python tests), creator/harness matrix,
dispatcher guards, stream widgets, MMIO and DMA suites, production TSI matrix,
thirty retained auditors and five retained I/O receipts pass. Four fresh ordinary
RTL replay windows and the independent full-source audit pass 318,637 pre-edge
words per cut, 256 events, sixteen first semantic divergences and 44 invalid
cases at C=100 / 700,000 / 900,000 / 3,250,000. Both exact-recipe 16-GiB four-hart
direct-exit controls pass at C=3,329,794. All four ordinary/restricted and
buffered/unbuffered syscall controls pass at C=3,330,050. Complete hart traces
and decoded workload labels match within each protocol. All fourteen final
checks and ten independent audits pass. These CPU controls are uninterrupted
regressions, not complete Level-1 restores. Final selected receipts, executable
native commands, exact workload/source hashes and full-path artifact index are
`summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `workloads.json`, `native-input-archives.json` and
`artifact-manifest.json` under `runs/m11-iteration168/`.
The exploratory memory pilot overlapped final edits and correctly failed its
source-binding guard after all cases ran; only the fixed-source final receipt
is selected. No test was cancelled or reduced.

The source-bound census and linked-symbol audit retain 15 host widgets,
11,464 generated entries / 445,838 words, the new memory and existing I/O APIs,
and all three CPU admission guards. Three current-binary requests and their
independent audit retain unsupported owner/capability denial, with no CPU image
created; these are not malformed CPU-image parser tests. Both existing
controller heads reached GitHub, FireSim first then Chipyard, with independently
confirmed remote tips despite local tracking-reference write warnings. No
staging or local commit occurred. Plans, environment helpers, heads and indices
retain their starting bytes. No external dependency is missing.
Complete prepared/sealed simulator coordination and production
controller/creator/thread/signal/descriptor/parser exclusion remain pending.
The generic aggregate still loads allocating owners sequentially. Level 2 stays
independent; BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA
validation and ASIC power remain outside scope.

Previous iteration 167 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 167, in progress.
Production runtime I/O now separates complete destination sealing from
allocation-free `noexcept` publication. A destination generation invalidates
other prepared candidates after any commit, including identical-byte commits.
CPU aggregate admission remains disabled. Recovery:
[runtime-io-sealed-publication.md](runtime-io-sealed-publication.md).

Final-source native ASan/UBSan and time-zero VCS DPI pass 24 fresh component
restores, 336 complete owner comparisons, 510 invalid/stale rejections, 5,092
exhaustive allocation failures and 72 fatal contract checks without partial
publication. The independent complete byte/queue/MT19937-64 oracle passes.
The final receipt is `runs/m11-iteration167/runtime-io-final/invocation-taxn7a8r/summary.json`.
The initial matrix also passed; its retained receipt is under `runtime-io/`.
The MMIO fixture and independent audit pass 48 fresh restores, 480 owner
comparisons, 2,556 suspended boundaries / 24,318 guard rejections and 824 invalid
cases. DMA passes 84 fresh restores, 336 owner comparisons, 187,296 suspended
boundaries / 1,872,960 guard rejections and 1,230 invalid cases. These are
component results, not complete Rocket Level-1 continuation.

All thirteen final checks and nine independent audits pass. All eight preserved
native scopes (280 Python tests), creator/harness matrix, dispatcher guards,
stream-widget suite, thirty retained auditors and production TSI matrix pass.
The four fresh ordinary RTL windows and independent full-source audit pass
318,637 pre-edge words per cut, 256 captured events, sixteen first semantic
divergences and 44 invalid cases at C=100 / 700,000 / 900,000 / 3,250,000.
Both exact-recipe 16-GiB direct-exit four-hart controls pass at C=3,329,794.
All four syscall variants pass at C=3,330,050. Complete hart traces and decoded
workload labels match within each protocol. Final selected receipts, exact
workload/source hashes, executable native commands and the full-path artifact
index are `summary.json`, `selected-results.json`, `workloads.json`,
`native-input-archives.json`, `raw-native-commands.json`,
`verification-commands.json` and `artifact-manifest.json` under
`runs/m11-iteration167/`.

The source-bound structural audit records 15 host widgets and 11,464 generated
entries / 445,838 words. A symbol audit confirms all three I/O transaction APIs
are linked in the current exact-recipe binary. Three fresh native CPU requests
and their independent audit retain unsupported owner/capability denial; no
CPU checkpoint is created. These denials are not malformed CPU-image parser
validation. Additional audits pass all 32 dispatcher diagnostics, 336 TSI
invalids and 128 unpublished prepared/sealed cancellations. Four retained I/O
receipts also pass the backwards-compatible auditors.

Both existing iteration-166 controller heads reached GitHub, FireSim first and
then Chipyard, with independently checked remote heads; local tracking-reference
writes warned. Both plans, environment helpers, heads and indices retain their
starting bytes. No staging, local commits, test cancellation or check reduction
occurred. No external dependency is missing. Complete simulator coordination
and production controller/creator/thread/signal/descriptor/parser exclusion
remain pending. In particular, the generic aggregate still loads allocating
owners sequentially; the new I/O sealing API does not make it a CPU transaction.
Level 2 stays independent; BOOM/Saturn remain pending. Standalone Shuttle,
physical FPGA validation and ASIC power remain outside scope.

Previous iteration 166 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 166, in progress.
Production `simif_emul_t` now prepares and publishes the returned MMIO/stream
callers, control/DMA AXI and host timing jointly. Exact owner membership,
complete destination recheck and lifetime/thread/single-use binding precede
nonthrowing swaps. CPU aggregate admission stays disabled. Recovery:
[runtime-io-transaction.md](runtime-io-transaction.md).

Final-source native ASan/UBSan and time-zero VCS DPI pass 12 fresh component
restores, 240 complete owner comparisons, 474 invalid/configuration/stale/
lifetime rejections and 3,714 exhaustive allocation failures without partial
publication. The independent complete byte/queue/MT19937-64 oracle passes.
All eight preserved native scopes (280 Python tests), creator/harness matrix,
stream-widget and CPU-managed I/O suites, dispatcher guards, retained auditors
and production TSI component matrix pass. Four fresh ordinary RTL windows and
the full-source audit pass 318,637 pre-edge words per cut, 256 events, sixteen
first semantic divergences and 44 invalid cases. Both exact-recipe 16-GiB
four-hart direct-exit controls and their audits pass at C=3,329,794 with complete
traces and workload labels matching. All four final-source syscall variants and their independent audits pass at
C=3,330,050. Complete hart traces and decoded labels match within each protocol.
All twelve final checks and nine independent audits pass. The final selected
receipts, workload/source hashes, executable native commands and full-path
artifact index are `summary.json`, `selected-results.json`, `workloads.json`,
`native-input-archives.json`, `raw-native-commands.json`,
`verification-commands.json` and `artifact-manifest.json` under
`runs/m11-iteration166/`.
The structural integration audit binds 15 host widgets and 11,464 generated
entries / 445,838 words. Three fresh native denials and an independent audit
confirm CPU admission remains unsupported; this is not CPU-image validation.
The recovery document identifies concrete remaining coordinator entry points
and corrects the historical iteration-82 assumption that the concrete FireSim
driver/run-loop adapters are still missing.
Earlier fixture corrections and broader checks that overlapped the final test
correction remain diagnostic; the complete final suite supersedes them. No
check was cancelled. Both existing controller heads reached GitHub, FireSim
first then Chipyard, with independently checked remote heads; local tracking-ref
writes warned. Both plans, environment helpers, heads and indices retain their
starting bytes. No staging or local commits occurred. No external dependency
is missing. Complete simulator coordination and production thread/signal/
descriptor/parser exclusion remain pending. Level 2 stays independent;
BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA validation and
ASIC power remain outside scope.

Previous iteration 165 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 165, in progress.
Production `simif_emul_t::read/write` now have a distinct returned-call owner,
`runtime/mmio-io`, in the driver diagnostic inventory. All three checkpoint
hooks and nested calls reject during suspended reads/writes; interrupted calls
stay poisoned. `runtime/mmio` continues to own the AXI queues separately.
TracerV count reads nest the CPU stream and MMIO call owners. CPU aggregate
admission remains disabled. Recovery: [mmio-runtime-io.md](mmio-runtime-io.md).

Final-source native ASan/UBSan and VCS DPI pass 48 fresh component restores,
192 complete pre-edge and 192 final owner comparisons, 2,556 suspended
boundaries / 14,094 guard rejections and 824 invalid/configuration/poisoned
rejections. The independent MT19937-64/AXI oracle passes every handshake,
returned-call label and complete host timing payload at both delay settings.
An additional audit passes both MMIO owners in all 32 dispatcher diagnostics.
These are component and diagnostic results, not Rocket CPU continuation.

All eight preserved native scopes (280 Python tests), the stream-widget and
CPU-managed I/O suites, creator/harness matrix, dispatcher guards and thirty
retained auditors pass. The production TSI component matrix and independent
audit pass; the additional audit rejects all 336 invalid images before
publication and checks 128 staged cancellations remain unpublished. Four fresh
ordinary RTL VCS windows and the independent full-source audit pass 318,637
pre-edge words per cut, 256 captured events, sixteen first semantic divergences
and 44 invalid cases. Both exact-recipe 16-GiB direct-exit four-hart controls
pass at C=3,329,794, with complete hart traces and workload labels matching.
All four syscall controls and their independent audits pass at C=3,330,050;
complete hart traces and decoded workload labels match within each protocol.
The independent native suite audit also passes. Final selected receipts,
workload hashes, source archives and executable native commands are in
summary.json, selected-results.json, workloads.json, native-input-archives.json,
raw-native-commands.json, verification-commands.json and artifact-manifest.json
under `runs/m11-iteration165/`. All implementation sources stayed fixed through
validation; no check was cancelled or superseded.
Complete simulator coordination and production thread/signal/descriptor/parser
exclusion remain pending. Join the new returned MMIO owner and returned stream
I/O owner into the complete CPU transaction with sealed creator-side TSI
publication; neither component API supplies that policy. Level 2 stays
independent. BOOM/Saturn remain pending; standalone Shuttle, physical FPGA
validation and ASIC power remain outside scope. No external dependency is
missing. Existing controller commits reached GitHub, FireSim first then
Chipyard; remote heads match despite local tracking-reference write warnings.
Both plans, environment helpers, heads and indices retain their starting bytes.
No staging or local commits occurred.

Previous iteration 164 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 164, in progress.
The production metasim CPU-managed stream wrapper now has an explicit
returned-call owner, separate from AXI queues and stream hardware. Capture,
validation, loading and nested I/O reject suspended or interrupted calls. Zero
transfers submit no requests; partial beats reject explicitly. CPU aggregate
admission stays disabled. Recovery:
[cpu-managed-runtime-io.md](cpu-managed-runtime-io.md).

Final-source native ASan/UBSan and VCS DPI pass 84 fresh component restores,
168 complete pre-edge and 168 final owner comparisons, 187,296 suspended
boundaries /
1,123,776 guard rejections and 1,230 invalid/poisoned-state rejections. The
independent auditor passes. The exact Rocket stream census records four
TracerV streams and 32 generated entries / 24,604 words, all separate from the
new host owner. These component/structural results are not CPU continuation.

All eight preserved native scopes (280 Python tests), the creator/harness matrix,
dispatcher guards, thirty retained auditors, production TSI component matrix and
independent audits pass. Existing stream-widget checks pass 144 continuations
and 42 malformed processes. Four fresh ordinary RTL VCS windows and independent
full-source audit pass 318,637 pre-edge words per cut, 256 events, sixteen first
semantic divergences and 44 invalid cases. All six final-source exact-recipe
16-GiB four-hart controls and independent
audits pass: both direct-exit controls terminate at C=3,329,794 and all four
syscall protocols at C=3,330,050. Complete hart traces and decoded workload
labels match within each protocol. Initial fixture/native/control attempts
were superseded after correcting a reference lifetime in the new test fixture.
Affected checks were rerun under verified/; unaffected replay/TSI/retained checks
remain under regressions/. Exact selected receipts, source archives, workload
hashes and native commands are in summary.json, selected-results.json,
workloads.json, native-input-archives.json, raw-native-commands.json,
verification-commands.json and artifact-manifest.json under runs/m11-iteration164/.

Complete simulator coordination and production thread/signal/descriptor/parser
exclusion remain pending; Level 2 stays independent. No external dependency is
missing. BOOM/Saturn remain pending; standalone Shuttle, FPGA validation and ASIC
power remain outside scope. Existing controller commits reached GitHub,
FireSim first then Chipyard; remote heads match despite local tracking-ref write
warnings. Both plans, environment helpers, heads and indices retain their
starting bytes. No staging or local commits occurred. Next: join the returned
stream I/O, stream widget/TracerV, AXI/generated/harness, other bridge, memory
and runtime owners with sealed TSI publication at one complete CPU cut, and
establish production process exclusion before admitting CPU restore.

Previous iteration 163 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 163, in progress.
The actual restricted production TSI candidate now stays on its reserved creator
until sealing, then publishes without allocation under the retained guard.
Complete seventeen-owner readback precedes publication acknowledgment and
continuation. Cancellation passes before sealing, after sealing before commit,
and after commit, with creator-side provider/candidate destruction. Recovery:
[tsi-sealed-publication.md](tsi-sealed-publication.md).

The final-source native ASan/UBSan and VCS component matrix passes 64 fresh
restores, 192 cancellations, 336 invalid images, eight fatal publication misuse
processes and eight semantic first divergences. All eight preserved native scopes
(280 Python tests) and the independent native audit pass. Four fresh ordinary
RTL VCS windows and the independent full-source audit pass 318,637 pre-edge
words per cut, 256 events, sixteen semantic faults and 44 invalid cases.
All six final-source exact-recipe 16-GiB four-hart controls and their independent
audits pass: direct-exit controls terminate at C=3,329,794 and all four syscall
protocols at C=3,330,050. Complete hart traces and decoded workload labels match
within each protocol. The independent creator audit passes all four harness
modes (20 fresh continuations); dispatcher guards and all 30 retained auditors
also pass. The independent TSI audit verifies 52,088 owner comparisons, 3,000
serial boundaries and 136 sealed publications. An additional audit verifies
all 336 invalid images reject before sealing and 128 cancellations remain
unpublished. The same candidate retries 1,373 seal allocation failures across
native and VCS without publication.

Selected receipts, exact workload hashes, build settings, source archives and
executable native commands are in `summary.json`, `selected-results.json`,
`workloads.json`, `native-input-archives.json`, `raw-native-commands.json`,
`verification-commands.json` and `artifact-manifest.json` under
`runs/m11-iteration163/`. Accepted evidence is under `verified/`; the earlier
`bridge/` invocation overlapped edits and correctly rejected source drift.
Both plans, environment helpers, heads and indices retain their starting bytes.

Complete Rocket Level 1 remains disabled. Next: join the complete
simulator/FAME/channel/CPU-managed-stream/other-bridge/functional-memory/runtime
transaction with this sealed TSI publication, and establish production
thread/signal/descriptor/parser exclusion. The component mutex does not provide
that policy; the fresh simulator still rejects CPU-managed streams and
unsupported widgets. Level 2 stays independent. BOOM/Saturn remain pending;
standalone Shuttle, physical FPGA validation and ASIC power remain outside scope.
No external dependency is missing. Existing controller commits reached GitHub,
FireSim first then Chipyard, with independently checked remote heads; tracking
ref writes warned. No staging or local commits occurred.

Previous iteration 162 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 162, in progress.
The optional pre-edge mailbox now stages creator-affine owner publication before
sealing, runs commit/readback on that same creator under retained guards, and
parks it under those guards for controller publication/readback. Cancellation
and capture destruction stay on the creator. Skipped publication or a throwing
commit terminates before acknowledgment/continuation. Native ASan/UBSan, VCS
time-zero checks, all four harness modes and the independent creator audit pass.
An additional audit passes ten successful creator publications and 110 invalid
processes rejected before creator publication. Recovery:
[driver-owner-publication.md](driver-owner-publication.md).

Diagnostics: `runs/m11-iteration162/`. Accepted creator evidence is
`creator-verified/invocation-s3rdevgj/summary.json`; final broader checks run
under `verified/`. Earlier fixture failures and superseded source snapshots
remain diagnostic only. Complete Rocket Level 1 remains disabled. Next: join
creator-side publication with the complete simulator/FAME/channel/CPU-managed-
stream/other-bridge/functional-memory/runtime transaction, and establish the
production thread/signal/descriptor/parser exclusion policy. The actual TSI
component still commits during initial preparation; move its retained candidate
into the new sealed phase before claiming that integration. BOOM/Saturn remain
pending; standalone Shuttle, physical FPGA validation and ASIC power remain
outside scope. No external dependency is missing.

Final-source results: all eight preserved native scopes (280 Python tests),
thirty retained auditors, dispatcher/poison/loading/capture guards and independent
archive audits pass. Four fresh ordinary RTL VCS cuts pass 318,637 pre-edge words
per cut, 256 captured events, sixteen semantic first divergences and 44 invalid
cases, including the independent full-source audit. The production TSI bridge
component matrix and audit pass 64 fresh restores/cancellations, 52,088 owner
comparisons, 3,000 serial boundaries, 336 invalid processes and eight first
divergences. All six exact-recipe final-source 16-GiB four-hart controls and
independent audits pass: direct controls at C=3,329,794 and all four syscall
protocols at C=3,330,050. Complete hart traces and decoded labels match within
each protocol. Level 2 retains the direct ELF.

Exact selected receipts, workload hashes, source archives and native commands
are in `summary.json`, `selected-results.json`, `workloads.json`,
`native-input-archives.json`, `raw-native-commands.json`, `verification-commands.json`
and `artifact-manifest.json` under this iteration. Both plans, environment
helpers, heads and indices retain their starting bytes. Existing controller
heads reached GitHub, FireSim first then Chipyard; local tracking-ref writes
warned and remote heads were independently checked. No staging or local commits
occurred. The milestone remains in progress; no external dependency is missing.

Previous iteration 161 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 161, in progress.
The optional pre-edge mailbox now retains a creator-owned publication guard
between final validation and controller publication/readback, rejects later
preparation after sealing, and releases the guard on its creator before
continuation or during cancellation. Native ASan/UBSan, VCS time-zero checks,
all four actual harness modes and independent creator audit pass. Complete
Rocket Level 1 remains disabled; production process exclusion and the complete
simulator owner coordinator are still pending. Recovery:
[driver-publication-scope.md](driver-publication-scope.md).

Diagnostics: `runs/m11-iteration161/`. All eight preserved native scopes
(280 Python tests), thirty retained auditors, dispatcher/poison/loading/capture
guards and independent archive audits pass. Four fresh ordinary RTL VCS cuts
and the full-source audit pass 318,637 words before any edge per cut, 256 events,
sixteen first divergences and 44 invalid cases. The production bridge matrix
and audit pass 64 fresh restores/cancellations, 52,088 owner comparisons,
3,000 serial boundaries, 336 invalid processes and eight first divergences.
All six complete final-source 16-GiB four-hart controls and independent audits
pass: both direct controls at C=3,329,794 and all four syscall protocols at
C=3,330,050. Full hart traces and decoded labels match within each protocol.
Level 2 retains the direct ELF. Selected receipts, exact source archives,
workload bytes/hashes and native commands are in `summary.json`,
`selected-results.json`, `native-input-archives.json`, `workloads.json`,
`raw-native-commands.json`, `verification-commands.json` and
`artifact-manifest.json` under this iteration.
Both plans, environment helpers, heads and indices retain their starting bytes.
Existing controller heads
have reached GitHub, FireSim first then Chipyard; local tracking-ref writes
warned. No staging or local commits occurred. No external dependency is missing.

Next: use the retained publication scope with a production process exclusion
policy and join the complete simulator/FAME/channel/CPU-managed-stream/other-
bridge/functional-memory/runtime cut with creator-side provider publication.
The test mutex/mask does not establish that policy. Complete Rocket Level 1
remains disabled; BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA
validation and ASIC power remain outside scope.

Previous iteration 160 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 160, in progress.
The pre-edge creator can now stage its dispatcher continuation before owner
publication, commit it without callable allocation or thread creation, and
destroy staged captures before its retained resource on cancellation. Checkpoint
scheduling rejects after staging so the prepared boundary callback cannot go
stale. CPU aggregate admission remains disabled. Recovery:
[driver-prepared-launch.md](driver-prepared-launch.md).

Diagnostics: `runs/m11-iteration160/`. Final creator native sanitizer/VCS and
all four actual harness modes pass; the independent audit passes. Four-cut
ordinary RTL VCS replay and full-source audit pass 318,637 pre-edge words per
cut, 256 events, sixteen first divergences and 44 invalid cases. Final
poison/loading/capture guards pass. The production bridge component matrix and
independent audit pass 64 fresh restores, 64 cancellations, 52,088 owner
comparisons, 3,000 serial boundaries, 336 invalid processes, 1,326 control
truncations, 7,555 allocation failures and eight first divergences. All eight
preserved native scopes (280 Python tests) and independent archive audit pass;
all thirty retained auditors and the legacy dispatcher matrix pass. All six
complete final-source 16-GiB Rocket controls and independent audits pass: both
direct controls at C=3,329,794 and all four syscall controls at C=3,330,050.
Complete hart traces and decoded labels match within each protocol. Level 2
retains the direct ELF. Early import/unsupported-auditor-option failures and
source epochs superseded by the scheduling guard remain diagnostic only.
Selected receipts bind the completed final sources.

Exact receipts, source archives, native argv and every artifact path/hash are
in `summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json` and `artifact-manifest.json`
under this iteration. Both plans, environment helpers, heads and indices retain
their starting bytes. Existing controller heads reached GitHub, FireSim first
then Chipyard; only local tracking-ref writes warned. No staging or local
commits occurred. No external dependency is missing.

Complete Rocket Level 1 still needs simulator/FAME/channel/CPU-managed-stream/
other-bridge/functional-memory/runtime coordination, jointly guarded owner
publication and production process-wide thread/signal/descriptor/parser
exclusion. BOOM/Saturn remain pending; standalone Shuttle, physical FPGA
validation and ASIC power remain outside scope.

Previous iteration 159 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 159, in progress.
The optional pre-edge creator now retains one creator-owned resource bundle
through retryable preparation, driver continuation and creator-side destruction,
or destroys it on that worker during cancellation. The production TSI bridge
component keeps its live restored provider through launch, rereads all seventeen
owners before MMIO, and services it on that same worker. CPU aggregate admission
stays disabled. Recovery: [driver-creator-lifetimes.md](driver-creator-lifetimes.md).

Diagnostics: `runs/m11-iteration159/`. Final-source native sanitizer/VCS mailbox
and four-mode actual harness checks pass, including resource lifetime and
capture-before-resource destruction. The actual bridge matrix and independent
audit pass 64 fresh restores, 64 fresh cancellations, 52,088 complete-owner
comparisons, 3,000 serial boundaries, 336 invalid processes, 1,326 control
truncations, 7,555 allocation failures and eight first divergences. Four fresh
ordinary RTL VCS cuts and full-source audit pass all 318,637 words before any
edge per cut, 256 events, sixteen first divergences and 44 invalid cases.
All thirty retained auditors and dispatcher/poison/loading/capture checks pass.
All eight preserved native scopes (280 Python tests) and their independent
archive audit pass. All six complete 16-GiB four-hart controls and independent
audits pass: both direct controls at C=3,329,794 and all four syscall controls
at C=3,330,050. Complete hart traces and decoded labels match within each
protocol. Level 2 retains the direct ELF. Early source-epoch failures and an
audit attempted before replay completion remain diagnostic only; selected
receipts bind completed final source epochs.

Exact receipts, source archives, native argv and all created artifact paths and
hashes are in `summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json` and `artifact-manifest.json`
under this iteration. Both plans, environment helpers, local heads and indices
retain their starting bytes. All selected maintained C++ matches current sources.

Existing controller heads reached GitHub, FireSim first and Chipyard second;
only local tracking-ref writes warned. No staging or local commits occurred.
Both plans remain read-only. Complete Rocket Level 1 still requires coherent
simulator/FAME/channel/CPU-managed-stream/other-bridge/functional-memory/runtime
coordination, jointly prepared publication/launch, and production process-wide
thread/signal/descriptor/parser exclusion. BOOM/Saturn remain pending; standalone
Shuttle, physical FPGA validation and ASIC power remain outside scope.
No external dependency is missing.

Previous iteration 158 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 158, in progress.
The simulator can now reserve its eventual driver creator under the existing
pre-edge loading hold, run synchronous retryable preparation callbacks, and
continue on that same thread. MMIO/ticks reject throughout loading and after a
poisoned bootstrap; unused reservations cancel/join. CPU stream/empty-schema
admission stays unchanged. Recovery:
[driver-creator-reservation.md](driver-creator-reservation.md).

Diagnostics: `runs/m11-iteration158/`. Native ASan/UBSan and VCS pass 512 tasks,
512 exceptions, 17 launches, 16 cancellations and 1,296 rejections per backend.
Both legacy and both reserved actual-harness modes pass: 20 fresh continuations,
140 malformed native processes, 80 lifecycle cases and 140 aggregate prevalidation
cases (overlapping the malformed counts). Ten reserved continuations prove
creator identity; 130 preparation guards and ten retryable failures pass before
any edge. The independent audit rejects four incomplete receipt variants.
All dispatcher/capture/reservation regressions pass, including 108 poison
rejections over twelve destinations with all sixty native readbacks unchanged.

The production bridge matrix uses the same mailbox on its creator and passes
64 fresh restores / 52,088 complete-owner comparisons / 3,000 serial boundaries /
4,652 words. All 336 invalid processes, 1,326 control truncations, 7,555 allocation
failures, ten foreign calls, four late guards and eight first divergences pass.
Its independent audit rejects twelve missing/duplicate receipt variants and
all 125 source omissions. These remain component host-operation boundaries,
not complete Rocket target-cycle restores.

All eight native scopes (280 Python tests), their independent archive audit and
thirty retained auditors pass. All six full 16-GiB four-hart controls and audits
pass: both direct controls at C=3,329,794; all four syscall controls at C=3,330,050.
Complete hart traces and decoded labels match within each protocol. Fresh
ordinary RTL VCS plus the full-source audit pass all four independent Level-2
cuts: 318,637 words before any edge per cut, 256 events, sixteen first divergences
and 44 invalid cases. Level 2 retains the direct ELF.

Exact receipts, source archives, native argv and all created artifact paths and
hashes are in `summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json` and `artifact-manifest.json`
under this iteration. Early source-epoch rejections and the first bridge auditor's
incorrect runtime-marker requirement on build logs remain diagnostic; selected
receipts use completed source epochs. All selected maintained C++ matches current
sources. Both plans, environment helpers, heads and indices retain starting bytes.
Existing controller heads reached GitHub, FireSim first and Chipyard second;
only local tracking-ref writes warned. No staging or local commits occurred.

Complete Rocket Level 1 remains disabled. Next: keep a live TSI provider on the
reserved worker through launch, join creator preparation to the complete
simulator/FAME/channel/CPU-managed-stream/other-bridge/functional-memory/runtime
cut and establish production process-wide thread/signal/descriptor/parser
exclusion with jointly guarded publication. BOOM/Saturn remain pending;
standalone Shuttle, physical FPGA validation and ASIC power remain outside scope.
No external dependency is missing.

Previous iteration 157 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 157, in progress.
The actual TSI bridge now prepares a private fresh creator-side provider and
matching bridge control, then publishes both without MMIO, native context entry
or startup/reset replay. Restored service uses the owned context continuation.
The aggregate schema stays unsupported. Recovery:
[tsi-bridge-context.md](tsi-bridge-context.md).

Diagnostics: `runs/m11-iteration157/`. The final native ASan/UBSan + VCS bridge
matrix and independent audit pass **64 fresh restores / 52,088 complete-owner
comparisons / 3,000 serial boundaries / 4,652 words**. All **336** invalid
processes, **1,326** control byte truncations and **7,555** successive allocation
failures reject without publication. Complete descriptor tables and getopt
globals remain unchanged after failed attempts. Ten foreign calls, four late
guards, competing/consumed candidates and eight actual semantic first divergences
pass. VCS asserts time zero and zero edges. These are component host-operation
boundaries, not complete CPU target-cycle restores. Accepted receipt:
`bridge-verified/invocation-kzt3ygo7/summary.json`. The independent auditor rejects
twelve missing/duplicate receipt variants and all 124 source omissions.

All eight native scopes (280 Python tests), their independent archive audit and
thirty retained auditors pass. All six complete 16-GiB four-hart controls and
independent audits pass: both direct controls at C=3,329,794; all four syscall
modes at C=3,330,050. Full hart traces and decoded labels match within each
protocol. Fresh four-cut ordinary RTL VCS and the full-source audit pass all
318,637 words before any edge per cut, 256 events, sixteen first divergences and
44 invalid cases. Level 2 uses the retained direct ELF.

The first complete bridge runtime receipt remains failed for the auditor's
32-bit signed-exit interpretation. The corrected fresh bridge invocation has a
separate source catalog; CPU/native controls retain their completed first catalog.
Production C++ is identical across both catalogs. Initial path/link/fixture,
parser and source-epoch failures remain diagnostic. Exact receipts, native argv,
source snapshots and all artifact paths/hashes are in `summary.json`,
`selected-results.json`, `verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json` under this iteration.

Both plans, environment helpers, local heads and indices retain starting bytes.
Existing controller heads reached GitHub, FireSim first then Chipyard; local
tracking-ref writes warned after remote success. No staging or local commits
occurred. The controller still owns the new checkpoint.

Complete Rocket Level 1 remains disabled. Next: reserve the fresh creator worker
under the pre-edge hold, coordinate this bridge with the complete simulator/
FAME/channel/other-bridge/functional-memory/runtime cut, and establish production
process-wide thread/signal/descriptor/parser exclusion. BOOM/Saturn remain pending.
Standalone Shuttle, physical FPGA validation and ASIC power stay outside scope.
No external dependency is missing.

Previous iteration 156 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 156, in progress.
The restricted context group now exports a build- and metadata-bound byte image
and prepares a fresh creator-side publication candidate. All sixteen ordered
owners include the private lifecycle projection. A complete-context metadata
observation admits live returned sources while ordinary polling metadata
admission stays unchanged. Recovery: [tsi-context-images.md](tsi-context-images.md).
Complete Rocket Level 1 remains disabled; simulator integration and production
process-wide exclusion remain pending.

Diagnostics: `runs/m11-iteration156/`. The native ASan/UBSan and VCS image matrix
and its primary independent audit pass: 64 actual live captures, 128 fresh
cross-backend restores, 136,320 complete-owner comparisons / 8,388 host
operations, 336 invalid processes, 8,912 byte truncations and 2,284 successive
allocation failures with no publication. Eight actual semantic first divergences,
eight foreign-thread rejections and two late mask guards with creator retry pass.
Accepted: `context-image/invocation-uifjvkhy/summary.json`. The separate independent
auditor rejects all fourteen missing/duplicate receipt variants and all 99
individual source omissions. These are component host-operation cuts, not complete CPU target-cycle restores. Fresh four-cut
ordinary RTL VCS replay and its complete-source audit pass all 318,637 semantic
words before any edge per cut, 256 events, sixteen first divergences and 44
invalid cases.

All eight stable native scopes (280 Python tests), their independent archive
audit and thirty retained auditors pass. The complete prior context matrix and
independent audit pass 887 cuts / 3,548 fresh restores / 3,277,056 owner
comparisons / 201,268 host operations; 102 invalid processes, twelve late guards,
eight resource cases, eight first divergences and fourteen evidence rejections.
Both backends reject 1,960 malformed images, 64 membership variants, two cross-
owner inconsistencies and 927 allocations without publication. Accepted:
`context-regression/invocation-8xj33jgy/summary.json`.
All six full 16-GiB four-hart controls and independent audits pass: both direct
controls at C=3,329,794; all four syscall modes at C=3,330,050. Complete hart
traces and decoded workload labels match within each protocol. Level 2 uses
the retained direct ELF. Exact receipts, native argv, source catalogs and all
created artifact paths/hashes are in `summary.json`, `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json` under this iteration.
Initial cut-selection/log-directory and live-return metadata failures, plus
initial native/CPU source-epoch rejections, remain diagnostic. Selected checks
use stable sources and fresh outputs; no incomplete invocation is selected.

Existing controller commits are confirmed on GitHub, FireSim first and then
Chipyard; read-only local tracking-ref updates warned after remote success.
Both plans, environment helpers, local heads and indices retain starting bytes.
No staging or local commits occurred. Next: connect creator-side image/metadata
preparation and publication to coherent simulator/FAME/bridge/functional-memory
restoration, establish production process-wide exclusion, and validate full
Rocket Level-1 target-cycle continuation. BOOM/Saturn remain pending. Standalone
Shuttle, physical FPGA validation and ASIC power stay outside scope. No external
dependency is missing.

Previous iteration 155 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 155, in progress.
The settled driver diagnostic now freezes supported software owners on the
driver creator while VCS is parked in DPI, then transfers only names, schemas
and immutable bytes through the existing settled mutex. Frozen observations
retain no live owner references and always reject loading. Unsupported inventory
records and diagnostic/owner schemas stay unchanged. Recovery:
[driver-owner-snapshots.md](driver-owner-snapshots.md).

Diagnostics: `runs/m11-iteration155/`. The native ASan/UBSan + VCS actual-TSI
handoff passes four processes / 128 complete public-owner readbacks, 1,544
successive allocation failures with creator retries, 64 raw-reference rejections
and 128 each of invalid-image and mutable-load rejections. Parked and
post-creator-destruction bytes match the independent retained context oracle;
VCS asserts zero edges. Accepted receipt:
`snapshot-final/invocation-7zj4kqy2/summary.json`. The independent audit passes
all six missing/duplicate evidence variants and all 96 individual source-binding
omissions. The initial auditor omission failure remains diagnostic. The final
verifier/auditor have a separate recorded source epoch; production C++ stays
identical throughout every native execution.

The 500-case retained-view access matrix and independent audit pass. Both
production settled FCFS phases pass five cuts, complete generated-state and
target token/AXI comparisons, outstanding memory traffic, terminal cuts and
eleven invalid requests. All eight native scopes (280 Python tests), their
independent archive audit and thirty retained auditors pass.
All six complete 16-GiB four-hart controls and independent audits pass: both
direct controls at C=3,329,794, all four syscall modes at C=3,330,050; complete
hart traces and decoded workload labels match within each protocol. Fresh
four-cut ordinary RTL VCS plus the complete-source audit pass all 318,637 words
before any edge per cut, 256 events, sixteen semantic first divergences and
44 invalid cases. Level 2 uses the retained direct ELF.

Exact receipts, executable argv, both source epochs and full created artifact
paths/hashes are in `summary.json`, `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json` under this iteration.
Existing controller commits reached GitHub FireSim first and then Chipyard;
only local tracking-ref updates warned about read-only metadata. Both plans,
environment helpers, local heads and indices retain starting bytes. No staging
or local commits occurred.

Complete Rocket Level 1 stays disabled. Next: connect creator-side TSI images
and fresh creator-side preparation/publication to complete simulator restoration,
establish production process-wide exclusion, and validate coherent full CPU
continuation. This diagnostic handoff does not add TSI aggregate admission.
Level 2 stays independent; BOOM/Saturn remain pending. Standalone Shuttle,
physical FPGA validation and ASIC power stay outside scope. No dependency is
missing.

Previous iteration 154 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 154, in progress.
All sixteen public TSI owner getters now return stable views that recheck the
live creator on schema/save/validate/load, including malformed loads and
references retained before aggregate publication. Views follow actual optional
owner slots without serializing process-local bindings. Recovery:
[tsi-owner-views.md](tsi-owner-views.md). Owner image schemas stay unchanged;
complete Rocket Level 1 stays disabled.

Diagnostics: `runs/m11-iteration154/`. The 500-process / 125-operation native
ASan/UBSan + VCS matrix and independent audit pass, including all six missing/
duplicate evidence rejections. Receipt:
`thread-access/invocation-1ojny_2f/summary.json`. The lifetime diagnostic passes
128 real recycled-ID cases / 640 expired-view rejections, optional-slot replacement
and absence, unchanged owner calls and creator retries. Sixteen prior-source
sensitivity processes fail as expected, reproducing the raw-reference gap.

The complete 720-case admission matrix, 686-case signal/thread suite, fourteen-
owner lifecycle suite, eight native scopes (280 Python tests), thirty retained
auditors and fresh four-cut ordinary RTL VCS replay pass. The complete context
suite and independent audit pass 887 cuts / 3,548 restores / 3,277,056 owner
comparisons / 201,268 operations, 102 invalid processes, twelve late guards,
eight resource cases, eight first divergences and fourteen evidence rejections.
Both backends reject 1,960 malformed images, 64 membership variants, two cross-
owner inconsistencies and 927 allocations without publication. Receipt:
`context-regression/invocation-saf8lf7z/summary.json`.
All six complete 16-GiB four-hart controls and independent audits pass: both
direct controls at C=3,329,794, all four ordinary/restricted syscall controls at
C=3,330,050. Complete hart traces and decoded workload labels match within each
protocol. Fresh ordinary RTL VCS and complete-source audit pass four retained
cuts: all 318,637 words before any edge, 256 events, sixteen actual semantic
first divergences and 44 invalid cases. Level 2 uses the retained direct ELF.

Catalogs: `summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `artifact-manifest.json`.
The initial CPU/native source-snapshot drift failures stay diagnostic; selected
stable-source runs use fresh roots. Both plans, environment helpers, heads and
indices retain starting bytes. Existing controller heads reached GitHub FireSim
first and Chipyard second; local tracking-ref updates warned about read-only
metadata after remote success. No staging or local commits occurred.

Next: supply production process-wide exclusion and coordinate one complete
simulator/FAME/bridge/functional-memory cut. TSI is created on the driver thread;
serialize its owners there and hand immutable images to the parked low-clock
VCS callback. Do not transfer mutable TSI owner references across that boundary.
Fresh restoration likewise needs creator-thread preparation/publication before
any target edge. Complete Rocket Level-1 continuation remains pending; Level 2
stays independent. BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA
validation and ASIC power are outside scope. No dependency is missing.

Previous iteration 153 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 153, in progress.
Supported TSI aggregate and production serial/load-memory entries now reject
foreign threads before mutable owner access. A weak thread-local lifetime token
also rejects recycled creator IDs. Recovery: [tsi-thread-access.md](tsi-thread-access.md).
Owner image schemas stay unchanged; complete Rocket Level 1 stays disabled.

Diagnostics: `runs/m11-iteration153/`. The final native ASan/UBSan + VCS access
matrix and independent audit pass 180 processes / 45 entries at execution and
returned-tail outer boundaries, exact candidate retries and all six missing/
duplicate evidence rejections. Receipt:
`thread-access-final/invocation-otnosc2h/summary.json`.
The separate native/VCS lifetime check rejects all 128 actual recycled-ID cases.

The full context matrix and independent audit pass 887 cuts / 3,548 restores /
3,277,056 owner comparisons / 201,268 operations; 102 invalid processes, twelve
late guards, eight resource cases, eight first divergences and fourteen evidence
rejections. Both backends reject 1,960 malformed images, 64 membership variants,
two cross-owner inconsistencies and 927 allocation failures without publication.
Receipt: `context-stable/invocation-mrl1ypcu/summary.json`.
The 720-process aggregate admission matrix, 686-process signal/thread suite,
eight native core scopes (280 Python tests) and thirty retained auditors pass.

All six full 16-GiB four-hart CPU controls and independent audits pass: both
direct controls at C=3,329,794, all four ordinary/restricted syscall controls at
C=3,330,050. Complete hart traces and workload labels match within each protocol.
Fresh ordinary RTL VCS plus complete-source audit pass four retained cuts:
318,637 words before any edge per cut, 256 events, sixteen actual semantic first
divergences and 44 invalid cases. Level 2 uses the retained direct-exit ELF.

Catalogs: `summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json` and
`artifact-manifest.json`. Initial fixture compilation/mode/boundary mistakes,
evidence-checker KeyError and changed-source receipts remain diagnostic. The
final test-only declaration reorder ensures auxiliary destinations outlive their
candidates; its own complete native/VCS matrix passes. Source catalogs retain
separate execution epochs; production/native/context bytes stay frozen. The
post-fixture native artifact audit also passes.

Both plans, environment helpers, heads and indices retain starting bytes.
Existing controller heads reached GitHub FireSim first and Chipyard second;
local tracking-ref updates warned about read-only metadata. No staging/commits.
Next: coordinate production signal/thread/mask/action access and publish one
coherent simulator/FAME/bridge/functional-memory cut, then validate fresh complete
Rocket target-cycle Level-1 continuation. Entry confinement and procfs admission
do not supply process-wide exclusion. BOOM/Saturn remain pending. Standalone
Shuttle, physical FPGA and ASIC power are outside scope. No dependency is missing.

Previous iteration 152 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 152, in progress.
The actual lifecycle provider now enforces the existing all-thread and exact-action
guard for restricted polling/host/context capture, preparation, publication and
resume. Owner image schemas stay unchanged. Recovery:
[tsi-context-signal-admission.md](tsi-context-signal-admission.md).

Diagnostics: `runs/m11-iteration152/`. The fresh 720-process aggregate admission
matrix and independent audit pass: 360 current-provider cases, 300 prior-provider
worker/action sensitivity witnesses, 60 prior shared-pending controls, and six
missing/duplicate evidence rejections. Accepted:
`admission-accepted/invocation-b6_40pk6/summary.json`.

The complete current-provider context matrix and independent audit pass at
`context-accepted/invocation-88_6m1gp/summary.json`: 887 host-operation cuts,
3,548 fresh restores, 3,277,056 owner comparisons, 201,268 operations, 102 invalid
processes, twelve late guards, eight resource cases, eight first divergences and
fourteen evidence rejections. Both backends pass 1,960 malformed images,
64 membership cases, two cross-owner cases and 927 allocation failures each.
The foreign-creator fixture now keeps its worker parked through complete
readback; twenty separate native/VCS pilots pass. An earlier post-join audit
correctly rejected a disappearing task. Other observer/expectation/launcher,
source-drift and output-path pilots remain diagnostic; none is selected.

All six full 16-GiB four-hart CPU controls and their independent audits pass:
both direct controls finish at C=3,329,794; all four ordinary/restricted syscall
modes finish at C=3,330,050. Complete hart traces and decoded labels match within
each protocol. Eight native core scopes (280 Python tests), the post-fixture
archived-source audit, thirty retained auditors and the 686-process signal/thread
suite pass. Fresh ordinary RTL VCS and complete-source audit pass four retained
cuts: 318,637 words before any edge per cut, 256 events, sixteen real semantic
faults and 44 invalid cases. This Level-2 evidence uses the retained direct ELF.

Catalogs: `summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `artifact-manifest.json`.
The source catalog retains separate execution epochs for the test-only fixture
change; accepted native files and earlier-iteration artifacts stay intact.
Both plans, environment helpers, index and heads retain starting bytes. Existing
controller heads reached both GitHub main branches, FireSim first, with local
tracking-ref warnings after remote success. No staging or local commits.

Next: establish production exclusion throughout thread/mask/action/signal access;
publish one coherent simulator/FAME/bridge/functional-memory cut; validate fresh
complete Rocket CPU Level-1 continuation at original target-cycle labels.
Procfs inspection does not provide that coordination. CPU Level 1 stays disabled.
BOOM/Saturn remain pending; standalone Shuttle, physical FPGA and ASIC power stay
outside scope. No external dependency is missing.

Previous iteration 151 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 151, in progress.
The separately hashed syscall-93 variant of the self-checking four-hart workload
now passes complete native VCS execution on ordinary/restricted HTIF, each with
ordinary/buffered observers and a full 16-GiB backing memory. All four finish at
C=3,330,050. All sixteen complete hart traces and decoded phase/completion/failure,
BSS-zero, request and pointer-store labels match. Spike success and four real
hart-memory faults pass for both workload protocols; the retained direct images
and source stay untouched. Fresh direct builds reproduce every loadable byte;
random compiler FILE symbols account for their ELF hash differences.
Recovery: [rocket-syscall-workload.md](rocket-syscall-workload.md).

Diagnostics: `runs/m11-iteration151/`. Selected controls:
`accepted-controls/invocation-36jsobc5/summary.json`; actual native processes/logs:
`syscall-controls/invocation-a6oe1ba6/`. The selected receipt freezes the original
native files/source snapshots and runs fresh corrected decoders. The first
checker omitted eight actual BSS-zero stores, and its input-drift guard rejects
because it changed during execution. A reuse-audit pilot rejected overlapping
PID numbers across native and later audit launch namespaces; uniqueness now
applies within each launch phase, with every argv/log/runtime still bound.
The initial launch also had a harness NameError before any VCS execution. All
initial failures remain diagnostic; no original failed summary is rewritten.
The exact-recipe iteration-150 native executable and all native build inputs
remain byte-exact. No target execution was skipped or replayed for checker repair.

The independent control audit and all nine incomplete/duplicate evidence
rejections pass. Catalogs: `summary.json`, `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`. The fresh sixteen-owner context matrix and independent audit
pass 887 host-operation cuts / 3,548 fresh restores / 3,277,056 comparisons /
201,268 operations, all 102 invalid processes, twelve late guards, eight resource
cases, eight first divergences and fourteen evidence rejections. All eight
native core scopes (280 Python tests), their artifact audit and thirty retained
auditors pass. Fresh ordinary RTL VCS plus its complete-source independent audit
passes the four retained cuts: 318,637 words before any edge, 256 events,
sixteen real semantic faults and 44 invalid cases. This retained Level-2 evidence
uses the original direct-exit workload; new syscall-workload Level 2 is pending.

Test-only inherited signal masks do not establish production coordination.
Audit correction: the aggregate's lifecycle guard checks the calling thread;
the separate signal-owner all-thread audit is not connected to that aggregate.
Next: connect all-thread admission and production exclusion, publish a coherent
simulator/FAME/bridge/functional-memory cut and validate fresh complete Rocket
Level-1 continuation at original target-cycle labels. Complete CPU Level 1 is
still disabled. BOOM/Saturn remain pending; standalone Shuttle, physical FPGA and
ASIC power stay outside scope. Both plans/environment helpers retain starting
bytes. Existing controller heads reached both remote main branches, FireSim
first, with local tracking-ref warnings after remote success. No staging/commits.
The corrected decoder also reproduces every original retained direct-exit CPU
phase/completion/failure/tohost/retirement label in a final independent re-audit.

Previous iteration 150 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 150, in progress.
The restricted sixteen-owner transaction now includes semantic wrapper phases
and fresh process-local coroutine continuation. It reconstructs polling or
returned-tail frames without startup replay; ordinary restored `tick()` remains
disabled. Recovery: [tsi-context-continuation.md](tsi-context-continuation.md).
Complete Rocket CPU Level 1 remains pending.

Diagnostics: `runs/m11-iteration150/`. The current-recipe-bound context matrix
passes eight scenarios / 887 host-operation cuts / 3,548 fresh
native/VCS restores / 3,277,056 complete owner comparisons /
201,268 operations. All sixteen owners read back before context creation;
all continued owner bytes and three tail ticks per continuation match. The
independent auditor rejects fourteen missing/duplicate evidence variants.
Accepted: `context-final/invocation-kuad914v/summary.json`.

All 102 fresh invalid processes, twelve late guards, exhaustive malformed/
membership/cross-owner/allocation cases, eight creator/actual 1 MiB stack/
continuation-signal resource cases and eight first divergent outgoing words
pass. Sixteen real source coroutines match the independently executed parent.
The full current-recipe polling, fifteen-owner and outer regressions pass,
with 3,452 / 3,580 / 160 fresh restores and independent audits. The 1,200-restore
syscall parent, 686-process signal/thread suite, legacy direct-exit matrix,
context lifetime and actual bridge transport regressions also pass. All eight
core native scopes (280 Python tests) and thirty retained auditors pass.
Fresh ordinary RTL VCS and its independent audit pass all four retained cuts:
318,637 words before any edge per cut, 256 events / 21,760 comparisons,
sixteen semantic faults and 44 invalid cases. Both full 16-GiB four-hart controls
complete at C=3,329,794; all eight traces and workload/store labels match.
These host cuts are not CPU target-cycle checkpoints.

Catalogs: `summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `artifact-manifest.json`.
Only the final fixed-input suites are selected; the initial context pilot has
superseded resource-guard inputs and remains diagnostic. The corrected source
preflight passes all eight scenarios and eleven negative/resource modes.
The initial catalog writer expected a hash absent from the legacy descriptor
receipt; corrected catalogs bind its actual command and verified polling summary.
Both plans and environment helpers retain starting bytes. Existing controller
heads reached both remote main branches, FireSim first, with local tracking-ref
write warnings after remote success. No staging or local commits.

Next: integrate the retained CPU workload's direct-exit wrapper/outer path or
use a separately hashed self-checking syscall-93 CPU workload; coordinate
production signals and publish one coherent simulator/FAME/bridge/functional-
memory cut, then validate complete fresh Rocket CPU Level-1 target-cycle
continuation. No external dependency is missing. BOOM/Saturn remain pending;
standalone Shuttle, physical FPGA validation and ASIC power remain outside scope.

Previous iteration 149 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 149, in progress.
The restricted TSI transaction now atomically restores all fifteen outer,
polling, syscall and provider owners. It binds stop/return phases to completed
polling and the actual provider's signed exit result. Fresh continuation uses
production poll/stop/return services; `tick()` still rejects. Recovery:
[tsi-host-aggregate.md](tsi-host-aggregate.md). Complete Rocket CPU Level 1
remains disabled.

Diagnostics: `runs/m11-iteration149/`. The accepted current-recipe aggregate
passes eight scenarios / 895 host-operation cuts / 3,580
fresh native/VCS restores / 3,125,940 complete owner
comparisons / 204,816 operations. All 102 fresh invalid images,
twelve late guards, exhaustive malformed/membership/allocation checks and eight
first divergent outgoing words pass. Sixteen real source coroutines match the
independent polling parent and final returned aggregate. The independent auditor
rejects twelve incomplete/duplicate evidence variants. Accepted:
`frozen/host-final/invocation-2uwuywgo/summary.json`.

The full fourteen-owner polling parent, 1,200-restore syscall parent,
686-process signal/thread suite, 160-restore outer component regression,
full legacy polling/direct-exit suite, all eight native core suites and thirty
retained auditors pass, together with their independent evidence audits.
Fresh ordinary RTL VCS passes four retained cuts: 318,637 words before any edge
per cut, 256 events / 21,760 output comparisons, sixteen semantic faults and
44 invalid cases. Both exact-recipe default/buffered 16-GiB four-hart controls
pass at C=3,329,794; all eight complete hart traces and workload/store labels
match. Stop/return-code cuts are explicit component boundaries; production does
not yield there. These host cuts are not CPU target-cycle checkpoints.

Catalogs: `summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `artifact-manifest.json`.
The initial aggregate/polling source guards reject the changed inputs. The
initial controls and waiting coordinators were stopped after supersession;
only the full replacement scopes under `frozen/` are selected. Both
plans and environment helpers retain starting bytes. Existing controller heads
reached both GitHub main branches, FireSim first; local tracking-ref warnings
followed remote success. No staging or local commits.

Next: reconstruct and validate the wrapper/context handshake without replaying
startup; coordinate production signals and complete inherited-session policy;
publish one coherent simulator/bridge/functional-memory cut and validate fresh
complete Rocket CPU Level-1 continuation. No external dependency is missing.
BOOM/Saturn remain pending; standalone Shuttle, physical FPGA validation and
ASIC power remain outside scope.

Previous iteration 148 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 148, in progress.
Production `run_host()` now uses an explicit five-phase outer caller with
pointer-free signed return state. Active startup/nested-service captures reject;
escaping services poison the owner. Component restoration still rejects context
entry. Recovery: [tsi-host-execution.md](tsi-host-execution.md).
Complete Rocket CPU Level 1 remains disabled.

Diagnostics: `runs/m11-iteration148/`. The final current-recipe-bound outer suite
passes 160 fresh cross-backend component restores / 880 complete owner comparisons /
sixteen actual production-coroutine runs / eight invalid processes / eight first
service-boundary corruptions. Its independent auditor rejects twelve incomplete
or duplicate evidence variants. Accepted: `outer-final/invocation-321c0poi/summary.json`.

The full frozen-input polling matrix passes eight scenarios / 863 host-operation
cuts / 3,452 fresh native/VCS restores / 2,768,080 owner comparisons / 190,816
operations, with all malformed, membership, allocator, idle, late/admission and
eight first-divergence checks. The 1,200-restore syscall parent, 686-process
signal/thread suite, full legacy polling/direct-exit scope, all eight native
core suites (5,291 artifacts / 824 source bindings), all thirty retained auditors
and their selected independent audits pass.

Fresh ordinary RTL VCS plus its independent audit pass all four retained cuts:
318,637 semantic words before any edge per cut, 256 events / 21,760 comparisons,
sixteen actual semantic faults and 44 invalid cases. Both exact-recipe default
and buffered 16-GiB four-hart controls pass at C=3,329,794; all eight complete
hart traces and workload/store labels match. Controls:
`rocket-controls/invocation-7w9n3gl4/summary.json`.

Final catalogs: `summary.json`, `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`. Initial polling source
drift is an explicit rejection, retained separately; only the frozen replacement
is accepted. The outer pilot uses retained parent evidence and is separate from
the selected current-parent suite. A diagnostic auditor indentation error was
corrected before its accepted independent runs. Plans and environment helpers
retain starting bytes. Existing controller heads reached both remote main
branches, FireSim first; local tracking-ref updates warned after remote success.
No staging/local commits.

Next: aggregate outer and wrapper/context reconstruction, production signal
coordination, complete inherited-session policy and coherent simulator/bridge/
memory publication, then fresh complete Rocket CPU Level-1 continuation. No
external dependency is missing. BOOM/Saturn remain pending; standalone Shuttle,
physical FPGA validation and ASIC power remain outside scope.

Previous iteration 147 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 147, in progress.
Restricted mode now retires the unused inherited HTIF proxy descriptors and
dispatch table. Every restricted group boundary requires its resources to remain
absent with correct owner links. Ordinary sessions keep their original lifetime.
The exact-header provider adds friends only; installed syscall/device members
remain byte-exact. Recovery: [tsi-dormant-proxy.md](tsi-dormant-proxy.md).

Diagnostics: `runs/m11-iteration147/`. Native ASan/UBSan and VCS descriptor
checks preserve all existing identities/flags and reproduce baseline tables at
suspended destruction. All 36 actual private-proxy fault cases reject before
preparation/publication/service. Missing/incomplete APIs and an unsupported
syscall header reject; the prior constructor fails the new descriptor check.
The independently audited recipe provider contains no test mutator.

The exact-recipe group passes eight scenarios / 863 host-operation cuts /
3,452 fresh native/VCS restores / 2,768,080 complete owner comparisons /
190,816 operations. All malformed, membership, allocator, late-guard,
admission, idle-cross-owner and eight first-divergence cases pass. The independent
auditor rejects fourteen incomplete evidence sets and five altered descriptor
tables. Accepted: `recipe-polling-syscall/invocation-jcm6k_dr/summary.json`.

The recipe-bound syscall parent and 686-process signal/thread suites, full
legacy polling/direct-exit scope, all eight native core suites, thirty retained
auditors and the prior iteration-146 polling audit pass. Core evidence:
5,286 artifacts / 819 source bindings. Fresh ordinary RTL VCS plus its
independent audit pass four retained cuts: 318,637 words before edges per cut,
256 events / 21,760 comparisons, sixteen actual semantic faults and 44 invalid
cases. Both exact-recipe default/buffered 16-GiB four-hart controls pass at
C=3,329,794; all eight complete hart traces and workload/store labels match.
Controls: `rocket-controls/invocation-d8873709/summary.json`.

Final catalogs: `summary.json`, `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json`, `artifact-manifest.json`. All selected scopes
pass independent auditing; the full standalone polling suite passes too.
Initial private-fault test-wrapper compile errors remain separate diagnostics;
only its corrected full native/VCS run is accepted. Plans, papers and environment
helpers preserve starting bytes. Existing controller checkpoints reached both
remote main branches, FireSim first; local read-only tracking-ref errors followed
remote success. No staging or local commits.

Next: explicit outer startup/stop/return/context, production signal coordination,
complete inherited-session policy and coherent simulator/bridge/memory publication,
then complete fresh Rocket CPU Level-1 continuation. Complete CPU Level 1 stays
disabled. No external dependency is missing. BOOM/Saturn remain pending;
standalone Shuttle, physical FPGA validation and ASIC power remain outside scope.

Previous iteration 146 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 146, in progress.
Restricted polling now skips its unused default syscall session; group admission
requires that session to be absent. Actual native ASan/UBSan and VCS descriptor
audits distinguish the three inherited proxy descriptors from the three extra
ordinary-session descriptors, preserve all existing identities/flags through
idle cuts, and reproduce the complete baseline table at suspended destruction.
The new check rejects separately compiled prior production code. Recovery:
[tsi-restricted-session.md](tsi-restricted-session.md).

Diagnostics: `runs/m11-iteration146/`. The exact-recipe archive-bound group
passes eight scenarios / 863 host-operation cuts / 3,452 fresh native/VCS
restores, 2,768,080 complete owner-image comparisons and 190,816 operations.
Every scenario now runs two zero-mailbox idle rounds. All malformed, membership,
allocator, late-guard and admission checks pass; seven incompatible idle cuts
reject in fourteen fresh processes. Eight actual semantic faults stop at the
first unconsumed outgoing word. The independent auditor rejects fourteen
incomplete evidence sets and five altered descriptor tables. Accepted:
`recipe-polling-syscall/invocation-s5uurlzp/summary.json`.

The retained archive-bound syscall parent and 686-process signal/thread suites,
full legacy polling/direct-exit scope, all eight native core suites and thirty
retained auditors pass. Core evidence: 5,286 artifacts / 819 source bindings;
the copied runner's new invocation is under
`runs/m11-iteration145/native-regressions/invocation-kvn1pu5w/` and is selected
in the iteration-146 catalog. No prior accepted artifact was overwritten.
Ordinary RTL VCS and its independent audit pass four retained cuts: 318,637
words before edges per cut, 256 events / 21,760 comparisons, sixteen actual
semantic faults and 44 invalid cases. Both exact-recipe default/buffered
16-GiB four-hart controls pass at C=3,329,794; all eight complete hart traces
and workload/store labels match. Controls:
`rocket-controls/invocation-dn6w_xbn/summary.json`.

Final catalogs: `summary.json`, `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`. Every selected scope
passes independent auditing. The separate complete standalone polling scope
passes too. Initial diagnostic import/oracle preflight errors remain separate
logs. Both plans, papers and environment helpers retain their starting bytes.
Existing controller checkpoint commits reached both remote main branches,
FireSim first; read-only local tracking-ref warnings followed remote success.
No staging or local commits.

Next: own the inherited HTIF proxy/session and explicit outer startup/stop/
return/context, coordinate production signals, and publish a coherent complete
simulator/bridge/memory cut before fresh Rocket CPU Level-1 continuation.
Complete CPU Level 1 remains disabled. No external dependency is missing.
BOOM/Saturn remain pending; standalone Shuttle, physical FPGA validation and
ASIC power remain outside scope.

Previous iteration 145 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 145, in progress.
Production polling now routes explicit `+checkpoint-syscall-exit` through the
owned syscall-93 caller. A fourteen-owner group restores polling, nested memif
progress, serial queues and actual lifecycle fields atomically, preserving
cache flush, writeback and response order. Recovery:
[tsi-polling-syscall.md](tsi-polling-syscall.md). Complete CPU Level 1 stays disabled.

Diagnostics: `runs/m11-iteration145/`. The exact-recipe linked archive passes
eight scenarios / 703 host-operation cuts / 2,812 fresh cross-backend restores,
1,867,040 owner-image comparisons and 127,736 operations. Both backends reject
1,844 malformed cases, 56 membership faults and seven cross-owner faults;
all 846 allocation-failure positions preserve the destination. Eight actual
semantic faults stop at their first unconsumed outgoing word. Eighty-four fresh
invalid-image processes, ten late guards and fifteen admission/terminal checks
pass. The independent auditor rejects fourteen missing/duplicate/changed
source, build, process and divergence evidence variants. Accepted:
`recipe-polling-syscall-final-inputs/invocation-ckf8ipgj/summary.json`.

The separate 1,200-restore syscall suite and 686 signal/thread processes pass
against that same linked archive. The full legacy polling/direct-exit suite,
all eight native core suites (280 Python tests / 5,286 artifacts / 819 source
bindings) and all thirty retained auditors pass. Ordinary RTL VCS and its
independent audit pass four retained cuts: 318,637 words before edges per cut,
256 events / 21,760 comparisons, sixteen semantic faults and 44 invalid cases.
Both exact-recipe default/buffered **16-GiB four-hart controls pass at
C=3,329,794**; all eight complete hart traces and workload/store labels match.
Controls: `rocket-controls-final-inputs/invocation-uv_o5b21/summary.json`.

Final catalogs: `summary.json`, `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`. Initial pilots retain
fixture offset/oracle/link errors, a missing provider-include snapshot and
source-drift rejections. Superseded runs are never accepted as passing; final
full scopes use sealed inputs. Both plans, papers and environment helpers are
unchanged. Existing controller checkpoints reached both remote main branches,
FireSim first; read-only local tracking-ref warnings followed remote success.
No staging or local commits.

Next: audit/remove unused default-session descriptors in restricted mode;
cover its idle/outer-completion cuts, own outer startup/stop/return/context and
signal coordination, then publish a coherent simulator/bridge/memory cut and
validate complete fresh CPU Level 1. Generic syscalls remain unsupported in
restricted mode. No external dependency is missing. BOOM/Saturn remain pending;
standalone Shuttle, physical FPGA validation and ASIC power remain outside scope.

Previous iteration 144 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 144, in progress.
Added the executable syscall-93 parent component: eight request words, nested
read/write progress, actual-provider exit and response ordering, with atomic
caller/serial/lifecycle restore. It is not yet wired into live polling dispatch;
complete Rocket Level 1 remains disabled. Recovery:
[tsi-syscall-exit.md](tsi-syscall-exit.md).

Diagnostics: `runs/m11-iteration144/`. The recipe archive-bound syscall suite
passes four scenarios / 300 host-operation cuts / 1,200 fresh cross-backend
restores, 141,408 complete owner comparisons and 45,936 operations. Its
independent audit passes and rejects twelve incomplete/duplicate evidence
variants. Eight installed-syscall differentials, eighteen fresh invalid images,
814 malformed cases per backend, atomic ownership/allocation guards and four
actual first-boundary semantic faults pass. Accepted:
`recipe-syscall/invocation-9b6f2981/summary.json`.

All eight native suites pass: 280 Python tests / 5,283 artifacts / 816 source
bindings. All thirty retained auditors pass. Fresh ordinary RTL VCS four-cut
replay and its independent audit pass: 318,637 words before edges per cut,
256 captured events / 21,760 comparisons, sixteen semantic faults and 44 invalid
cases. Both exact-recipe default/buffered **16-GiB four-hart controls pass at
C=3,329,794**. All eight full hart traces and workload/store labels match the
uninterrupted reference. The accepted controls/build are under
`rocket-controls/invocation-iyg5oler/summary.json` and its adjacent build identity.

Initial pilots retain an unaligned oracle error and source-drift rejections.
Final catalogs: `summary.json`, `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`. All selected scopes
pass their independent audits. Native artifacts and immutable inputs remain at
their original invocation paths. No CPU Level-1 continuation is claimed.

Next: wire the restricted parent into owned live polling and own sessions,
descriptors, general syscall parents, signals and outer execution; publish a
coherent simulator/bridge/memory cut and validate fresh complete CPU Level 1.
No external dependency is missing. Plans and environment inputs are unchanged.
Existing controller commits reached both remote main branches, FireSim first;
local tracking-ref updates reported read-only filesystem errors after remote
success, independently confirmed by `ls-remote`.

Previous iteration 143 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 143, in progress.
The exact-source delivered-signal provider now audits every kernel thread's
SIGINT/TERM/ABRT mask and local/shared pending state, with stable task inventory
and explicit procfs rejection. Production cross-thread coordination and complete
CPU Level 1 remain pending. Recovery:
[tsi-htif-signal-threads.md](tsi-htif-signal-threads.md).

Diagnostics: `runs/m11-iteration143/`. The archive actually linked into the
rebuilt exact Rocket recipe passes all 686 native ASan/UBSan and VCS signal
processes, including 24 actual cross-thread transactions and twelve fresh
threaded restores. Capture, preparation and final commit reject worker/shared
signal faults without publication; repaired parked workers permit one atomic
retry. Both auditors pass; fourteen incomplete/duplicate evidence sets reject.
Six new tests detect the retained prior provider's missing checks. Accepted:
`recipe-signals/invocation-g9yeawcm/summary.json`.

Strict lifecycle and the full running/pending/stopped polling suite pass,
including 2,432 lifecycle restores, 3,872 protocol readbacks, 1,105,584 host
operations, 256 pending-exit continuations and 96 stopped restores. All eight
native suites pass: 280 Python tests / 5,280 artifacts / 813 source bindings.
All thirty retained independent auditors pass. The initial general suite
rejected mid-run test-source drift; its fresh complete rerun is
`native-regressions/invocation-1s7q9cgo/summary.json`.

Fresh ordinary RTL VCS passes all four retained Rocket windows: every one of
318,637 words before edges, 256 events / 21,760 comparisons, sixteen actual
stored-CSR first divergences and 44 invalid cases. Captured target-cycle labels
are unchanged. Evidence: `native-replay/invocation-ugf9msom/summary.json`.
Both exact-recipe default/buffered **16-GiB four-hart controls pass at
C=3,329,794**. All eight full hart traces and workload/store labels match the
uninterrupted reference: `rocket-controls/invocation-8dy5111m/summary.json`.
Generated inventory stays 11,464 entries / 445,838 words / sixty native units.

Final catalogs: `summary.json`, `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`.
`final-independent-audit.json` passes all selected scopes. Initial signal
pilots exposed pending-SIGABRT draining and thread-teardown test assumptions;
failed pilots remain separate diagnostics.

Controller commits were published FireSim first, then Chipyard; both remote
main tips match local HEADs. No staging or local commits. Both plans, papers
and environment helpers retain their starting bytes.

Next: default session/descriptors, syscall parent, executable outer caller,
production signal coordination and signal-caused stop callers; coherent
simulator/bridge/memory cuts and fresh complete CPU Level-1 continuation.
Session construction duplicates stdin/stdout and cannot substitute for restoring
external state or the suspended parent. The thread audit requires caller-held
exclusive suspension. Complete CPU Level 1 stays disabled. No external
dependency is missing. BOOM/Saturn remain pending; standalone Shuttle, physical
FPGA validation and ASIC power remain outside this task.

Previous iteration 142 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 142, in progress.
The opt-in exact-source HTIF provider now has a separate delivered-signal plus
private lifecycle component. It restores actual `signal_exit`, optional raw
exit and stopped fields atomically with prepared peers, without redelivering a
signal or replaying a service. Existing strict lifecycle/fourteen-owner polling
interfaces still reject delivered signals. Complete CPU Level 1 stays disabled.
Recovery: [tsi-htif-signal.md](tsi-htif-signal.md).

Diagnostics: `runs/m11-iteration142/`. The archive-bound native ASan/UBSan and
VCS suite passes 644 fresh processes: 72 actual captures, 144 fresh restores,
300 invalid images, forty late-guard transactions, 72 serial-peer publications,
two actual second-signal exits and six actual provider first-boundary faults.
The independent archive/state/continuation auditor passes and rejects eight
missing/duplicate evidence variants. Accepted signal invocation:
`recipe-signals/invocation-68fia3n2/summary.json`.

The strict lifecycle regression passes 2,432 fresh restores, 282 malformed
cases and 440 atomic transactions. The full fourteen-owner running/pending/
stopped polling suite passes, including 3,872 fresh protocol readbacks,
1,105,584 host operations, 256 pending-exit continuations and 96 stopped
restores. All eight preserved native suites pass: 280 Python tests / 5,279
artifacts / 812 source bindings. All thirty retained independent auditors pass.

Fresh ordinary RTL VCS passes all four retained complete Rocket windows:
318,637 words per zero-edge readback, 256 captured events / 21,760 output
comparisons, sixteen actual stored-CSR first divergences and 44 invalid cases.
The independent audit also checks the retained complete source capture.
These remain the original captured inputs and target-cycle labels.

Both exact-recipe complete default and buffered **16-GiB four-hart controls
pass at C=3,329,794**. All eight complete hart traces and every workload/store
label match the uninterrupted reference. Accepted control evidence:
`rocket-controls/invocation-xew5lebr/summary.json`.
The rebuilt binary's actual linked archive supplies the new signal suite.

Final recovery catalogs: `summary.json`, `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`. The initial standalone
644-case signal suite remains a separate diagnostic; the accepted suite tests
the archive actually linked into the exact Rocket recipe.
The final independent audit passes all selected scopes and seals 147,975
artifacts, 972 native source bindings and 8,573 executed native commands.
Its result is `final-independent-audit.json`; milestone status is in_progress.

Existing controller commits were published FireSim first and then Chipyard;
both remote main tips match local HEADs. No staging or local commits.
The plans, root papers and environment helpers retain their starting bytes.

Next: default session/descriptors, syscall parent, executable outer caller,
cross-thread signal coordination and signal-caused stop callers; coherent
simulator/bridge/memory cuts and complete fresh Level-1 CPU continuation.
The new projection requires exclusive suspended-provider access, blocked
INT/TERM/ABRT, original handler policy and no pending kernel signals. It does
not establish complete process signal ownership or extend polling admission.
No external dependency is missing. BOOM/Saturn remain pending; standalone
Shuttle, physical FPGA validation and ASIC power remain outside this task.

Previous iteration 141 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 141, in progress.
Semantic capture observers now explicitly exclude Level-1 admission. Public
FAME/legacy semantic-capture options reject in parsing; the linked FAME backend
rejects public requests before the capability factory, including when disabled.
The capability base constructor also excludes private diagnostic paths before
derived initialization. This does not enable Rocket Level 1 or serialize observer
state. Recovery: [level1-observer-exclusion.md](level1-observer-exclusion.md).

Diagnostics: `runs/m11-iteration141/`. Final native ASan/UBSan and VCS entry
checks pass all 572 fresh cases: 384 runtime exclusions, 24 compiled public
exclusions and eight base-constructor exclusions. Independent audit also rejects
four missing/duplicate evidence sets. Another eighteen fresh exact-recipe Rocket
VCS admission cases pass. Accepted invocations: `entry-observer-final/invocation-fjy_0l1n/`
and `rocket-observer-exclusion-final/invocation-whola2r4/`.

Both complete four-hart controls and the new complete source capture pass at
reported fastest-clock C=3,329,794. All twelve full hart traces and every
workload/store label match the uninterrupted reference. The observer separately
logs 3,329,793 completed mbus rises; checkpoint labels retain actual original
clock events. All eight current state/trace files at C=100/700000/900000/3250000
are byte-identical to the retained source files consumed by fresh ordinary RTL
VCS. The independent audit binds this equivalence rather than relabeling replay
inputs. The four ordinary runs read back every one of 318,637 words before any
edge, match 256 captured events / 21,760 output comparisons, and pass sixteen
actual stored-CSR first divergences and 44 invalid cases. Source capture:
`rocket-capture-final/invocation-z48jyzzk/`; controls:
`rocket-controls/invocation-bb9qmkkw/`; replay:
`native-replay/invocation-gnt43h6w/`.

All eight preserved native regressions pass: 280 Python tests / 5,276 artifacts
/ 809 source bindings. All thirty retained independent auditors pass. Exact
build audits distinguish the ordinary recipe's 60 native units / 11,464 generated
entries / 445,838 words from the semantic-preservation capture's 62 units /
11,746 entries / 446,120 words. The post-inventory observer remains excluded.
Original ChipTop ownership stays 8,644 entries / 318,637 words / seven clocks /
116 ports. Complete CPU Level-1 continuation remains pending.

Final catalogs: `summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json` and `artifact-manifest.json`.
The initial entry pilot rejected source changes during its test; an incorrect
source seed path and an incorrect test-only error-marker assertion were corrected.
These pilots remain separate diagnostics, not accepted results.

The controller's iteration-140 commits were published FireSim first and then
Chipyard. Remote main tips match local HEADs despite read-only local tracking-ref
update errors. Both plans, papers and environment helpers retain their starting
bytes. No staging or local commits.

Next: session/descriptors/signals/syscall-parent/outer-caller ownership, coherent
simulator/bridge/memory cuts and complete Level-1 fresh metasim continuation.
Keep the observer exclusion until its complete state is owned. Independent
Rocket Level 2 remains verified for the four finite captured windows. No external
dependency is missing. BOOM/Saturn remain pending; standalone Shuttle, physical
FPGA validation and ASIC power remain outside this task.

Previous iteration 140 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 140, in progress.
The guarded fourteen-owner polling/direct-exit/provider group now restores
completed direct-exit images with complete terminal readback, before any edge
or service. Public twelve-owner preparation still rejects completed callers.
The stopped recorder/provider must agree on raw optional status and stopped
state, and the polling caller must be complete with idle children. No context,
session, startup or stop is replayed. Complete CPU Level 1 remains disabled.
Recovery: [tsi-polling-lifecycle.md](tsi-polling-lifecycle.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Diagnostics: `runs/m11-iteration140/`. Final native ASan/UBSan and VCS suite:
`polling-lifecycle-final/invocation-rsfaix44/summary.json`. All 96 stopped
fourteen-owner fresh restores, 112 incompatible owner groups, 5,284 malformed
cases, 3,000 allocation failures, 24 final guards and 32 actual provider-status
first divergences pass. Existing running/pending scope passes 3,872 fresh
readbacks / 1,105,584 host operations / 256 pending-exit continuations. The
independent oracle audit and ten missing/duplicate evidence rejections pass.
Another twelve fresh stopped restores preserve two pending BCD commands,
transcript `5a` and 7/5/0-word serial packet tails without re-emitting output
(`nonempty-stopped/invocation-_1d_cbzb/summary.json`). The public twelve-owner
regression passes all 2,976 fresh preparations, including allocation and
destination-guard sweeps (`twelve-owner-regression/invocation-sucm3irm/summary.json`).
The initial lifecycle pilot failed a test-only three-byte terminal offset
assumption; the final test uses an actual terminal read and passes both input
lengths. The failed pilot remains retained and is not accepted evidence.

Fresh ordinary RTL VCS passes all four retained complete Level-2 windows:
318,637 words per cut, 256 captured events / 21,760 output comparisons,
sixteen actual stored CSR first divergences and 44 invalid-image/native-loader
cases. The source capture remains iteration 139's complete four-hart run.
All eight preserved native suites pass, including FCFS and 280 Python tests /
5,276 artifacts / 809 source bindings. All thirty retained independent audits
pass. Both final exact-recipe 16-GiB four-hart controls pass at the reported
fastest-clock C=3,329,794; all eight complete hart traces and every workload/store
label match the uninterrupted reference. Native build audit passes all sixty
translation units and the selected lifecycle provider. The initial broad
regression and earlier controls correctly rejected their test-only source
change; they remain diagnostic pilots. Accepted controls:
`rocket-controls-final/invocation-ezdigj8q/summary.json`.

Final recovery catalogs: `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `summary.json` and
`artifact-manifest.json`. Independent audits bind all accepted commands, source
snapshots, original state/trace words, readbacks, comparisons and negative cases.

The controller's iteration-139 commits were published FireSim first and then
Chipyard; both remote main tips match the unchanged local HEADs despite
read-only local tracking-ref update errors. Both plans, root papers and
environment helpers retain their starting bytes. No staging or local commits.

Next: session/descriptors/signals/syscall-parent/outer-context aggregate
ownership, coherent simulator/bridge/memory cuts and complete Level-1 fresh
metasim continuation. Active semantic observation also needs explicit rejection
or ownership for any future Level-1 profile. Rocket Level 2 remains independent.
No external dependency is missing. BOOM/Saturn remain pending; standalone
Shuttle, physical FPGA validation and ASIC power remain outside this task.

Previous iteration 139 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 139, in progress.
Rocket Level 2 now passes complete captured ChipTop finite replay at four cuts;
complete Level-1 CPU continuation remains pending. Recovery:
[rocket-semantic-event-capture.md](rocket-semantic-event-capture.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Diagnostics: `runs/m11-iteration139/`. The exact preservation-enabled recipe
build passes the explicit 62-unit native audit. The full 16-GiB self-checking
four-hart capture run passes at the reported fastest-clock C=3,329,794. All four
complete hart traces and workload/store labels match the uninterrupted reference.
All nine semantic/generated sidecars match the actual running metasim build.
`source-end-clock-audit.json` separately records the reported bridge count
(3,329,794) and the observer's logged completed mbus rises (3,329,793).
Checkpoint/replay labels use observed original-clock completed rises.

Actual original-clock cuts C=100/700000/900000/3250000 each restore and read back
all 8,644 owners / 318,637 words before any ordinary RTL edge. Fresh pre-FAME VCS
passes 256 captured clock events / 21,760 output comparisons at original event
and completed-rise labels. Sixteen actual per-hart stored CSR faults stop at
their first divergent boundary before acknowledgement. All 44 invalid-image /
atomic native-loader cases pass. Independent audits bind every original word,
clock count, boundary value, native command, image, readback and comparison.
C=900000 contains two pending cached TileLink grants and two voluntary writebacks;
its external AXI window is idle. Observer state remains outside Level 2 and has
no Level-1 restore adapter. The CPU Level-1 profile stays disabled.

All eight preserved native suites pass, including FCFS and 280 Python tests /
5,276 artifacts / 809 source bindings. All 30 retained audits pass. Initial
catalog/source-stability pilots are retained separately from accepted evidence.
Catalogs: `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `summary.json` and
`artifact-manifest.json`. Both plans, papers, helpers and local HEADs retain
their starting bytes/values. No staging or local commits. The controller's
iteration-138 checkpoints were published FireSim first and then Chipyard; both
remote main tips match despite read-only local tracking-ref errors.

Next: complete configuration-specific Level-1 session/descriptors/signals/syscall
parent/context and simulator/bridge/memory ownership, coherent CPU cuts and fresh
metasim continuation. Active event-observer state also needs explicit rejection
or ownership in a future Level-1 profile. Keep Level 2 independent. No external
dependency is missing. BOOM/Saturn remain pending; standalone Shuttle, physical
FPGA validation and ASIC power remain outside this task.

Previous iteration 138 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 138, in progress. Recovery:
[semantic-fame-state-map.md](semantic-fame-state-map.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Added opt-in compiler-carried
original StateIDs through path resolution, inlining, FAME and actual emitter
renames, preserving constant-driven registers, logical memories, memory pipelines
and exact initialized external owners. The raw emitted RTL has a separate
hash-bound sidecar before Make appends blackbox sources. Capture/profile
admission remains disabled; complete Level 1 and captured Level 2 remain pending.

Diagnostics: `runs/m11-iteration138/`. Exact-recipe discovery maps all 8,644
original entries / 318,637 words against 11,746 generated entries. Twelve fresh
VCS processes pass complete zero-edge transformed/ordinary diagnostic readback,
eight atomic invalid-loader cases and two actual stored-bit corruptions. The
separate native audit passes. Both layouts use the same original-word oracle;
these values are diagnostic patterns, not captured CPU checkpoints. All five
map/raw-RTL/semantic/generated-manifest/reference artifacts match the actual
preservation-enabled recipe metasim build byte-for-byte.

All 33 Scala tests and all eight preserved native suites pass (277 Python tests,
5,270 artifacts / 803 source bindings; FCFS included). All 30 retained audits
pass. The retained ordinary Rocket probe again passes all 318,637 words / seven
clocks / zero edges. Independent static checks cover every owner's clock and
all 116 original ChipTop boundary ports. Six original clock domains reach
target clock buffer 1; uncore reaches buffer 0. Dynamic event-phase/cut binding
and captured boundary replay remain pending.

All four complete 16-GiB default/buffered four-hart controls pass at
C=3,329,794 in `rocket-controls-final/invocation-vd1ngrsc/` and
`rocket-mapped-controls/invocation-h497o2iy/`. The latter enables all three
semantic-discovery/preservation flags in the exact recipe Make command. All
sixteen full hart traces and workload/store-cycle labels match the uninterrupted
reference. Both independent control audits pass; the mapped audit retains every
original check and additionally binds the complete native mapping artifacts.
The freshly rebuilt ordinary profile has 11,464 entries / 445,838 generated
words; preservation retains exactly 282 additional register words, with no
removed or reshaped existing owner. The mapped profile has 11,746 / 446,120.
Accepted native mapping: `native-map-sealed/invocation-ovekdx0g/summary.json`.
Accepted regressions: `native-regressions-final/invocation-a_9td1k6/summary.json`.
Earlier compiler/root-binding diagnostics and source-change guard rejections
are retained separately. Sources are now stable; plans and environment helpers
retain their starting bytes. No staging or local commits were performed.
The controller's iteration-137 commits were published FireSim first, then
Chipyard; both remote tips match despite read-only local tracking-ref errors.

Recovery catalogs: `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `summary.json` and
`artifact-manifest.json`. The new archive passes the independent retained-input
audit; protected plans, papers, helpers and local HEADs retain their bytes/values.

Next: bind actual FAME event phases and
all original boundary values, then capture real four-hart cuts and demonstrate
complete zero-edge ordinary RTL restore plus finite captured-trace replay.
Complete configuration-specific simulator/bridge/host/runtime ownership and
fresh Level-1 CPU continuation also remain pending. Neither CPU checkpoint
level is accepted. No missing external dependency is known. BOOM/Saturn remain
pending; standalone Shuttle, physical FPGA and ASIC power remain outside this task.

Previous iteration 137 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 137, in progress. Recovery:
[tsi-polling-lifecycle.md](tsi-polling-lifecycle.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Added guarded explicit
pending-exit caller continuation through the actual no-signature provider stop.
It finishes only the outstanding fromhost transaction and exit condition. An
occupied mailbox preserves the response queue. All fourteen owners read back
before service and after completion; repeated exit service, ordinary polling
and tick reject without mutation. Stopped-image restore, session/destruction/
return/context ownership and complete CPU admission remain pending.

Diagnostics: `runs/m11-iteration137/`. Full aggregate native ASan/UBSan and VCS
matrix passes all previous 1,936 captures / 3,872 fresh readbacks, 1,105,584 host
operations / 15,532,384 owner readbacks, 5,132 invalid-image/membership/cross-owner
rejections, 3,012 allocation failures and 24 final provider guards. Added 256
pending-exit continuations pass 1,664 host operations / 30,464 owner readbacks.
All 32 real response faults stop at original host operation 30 / request word 3
before acknowledgement; all 24 late provider/signal service guards pass.
Accepted aggregate: `aggregate-corrected/invocation-tm06fhlk/summary.json`.
A separate native/VCS build using the actual exact-recipe provider archive
passes the same 256 continuations / 32 faults / 24 guards in
`recipe-pending-exit-d2zrsbaf/summary.json`. Its occupied-mailbox extension passes
768 fresh continuations / 3,456 host operations / 69,888 owner readbacks across
three nonzero mailbox values and all eight raw exit payloads in
`occupied-exit-2uflihjh/summary.json`. All three independent audits pass.
These remain host component checks with zero DUT edges.

All eight preserved native suites pass (275 Python tests / FCFS included;
5,258 artifacts / 798 source bindings), as do all 30 retained audits. Ordinary
Rocket RTL diagnostic readback passes 318,637 words / seven clocks / zero edges.
Both complete exact-recipe 16-GiB four-hart controls pass at C=3,329,794 in
`rocket-controls-final/invocation-8vn9ksop/summary.json`. All full traces and
workload/store cycle labels match the uninterrupted reference. Initial checker errors
and source-guard rejections are retained separately; complete checks restarted
with stable sources. Both plans and environment helpers preserve their bytes.
Separate control/host audits pass eight active samples / 64 known component
images, including the late cut. Preserved twelve-owner preparation and
continuation pass all 2,976 fresh cases / 744 cuts; all eight continuation faults
stop before acknowledgement. Dispatch, bound device and actual recipe-linked
lifecycle suites pass, including 440 atomic transactions and twenty lifecycle
first divergences. The preserved raw-bit suite passes all 32 first divergences /
96 atomic cross-owner rejections; candidate type checks pass. All twelve commands
and independent audits in `host-regressions-summary.json` pass. The occupied
checker now uses original recipe source snapshots with retained-source guards;
its complete 768-case matrix reran successfully. Recovery catalogs:
`selected-results.json`, `verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json`, `summary.json` and `artifact-manifest.json`.

The controller's iteration-136 commits were published FireSim first, then
Chipyard; both remote main tips match. No staging or local commits.

Next: stopped-image/caller and complete session/descriptor/signal/syscall-parent/
context ownership; complete configuration-specific simulator/bridge/memory
ownership; coherent CPU cuts; complete fresh Level-1 continuation and independent
captured Level-2 replay. No missing external dependency is known. Neither CPU
checkpoint level is accepted. BOOM/Saturn remain pending. Standalone Shuttle,
physical FPGA and ASIC power remain outside this task.

Level-2 work can proceed independently of the remaining host session work.
A useful next increment is preserving original StateIDs through FAME flattening
and optimization, binding actual clock events and capturing complete ChipTop
state/boundary traffic at a real workload cut. The current clean readback remains
a diagnostic pattern. Matching hierarchy spellings is not a certified semantic
mapping, and missing optimized storage must not receive guessed values.

Previous iteration 136 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 136, in progress. Recovery:
[tsi-polling-lifecycle.md](tsi-polling-lifecycle.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Added an opt-in fourteen-owner
polling/direct-exit/actual-provider lifecycle group. It prepares every owner
before publication, compares full optional presence/raw status/stopped fields,
rechecks the actual destination and publishes all peers only after the final
provider guard. Requested exits at the real queued-response read yield permit
complete fresh readback; exit/stop continuation and stopped-parent restoration
remain explicitly unsupported. Complete CPU admission is unchanged.

Diagnostics: `runs/m11-iteration136/`. The complete new native ASan/UBSan and VCS
matrix passes 1,936 captured host cuts, 3,872 fresh fourteen-owner readbacks
(including 256 requested-exit readbacks), 1,105,584 continued host operations and
15,532,384 complete owner readbacks. All 5,132 invalid-image/membership/cross-owner
rejections, 3,012 allocation failures and 24 final provider guards pass without
partial publication. Candidate abandonment, late peers, consumed/competing
candidates and released input storage pass. Native copy/move/private-publication
compile negatives reject; C++17 construction passes. The separate aggregate
audit passes. An additional native/VCS build linked to the actual exact-recipe
provider archive passes 32 fresh fourteen-owner restores and 96 atomic cross-owner
rejections. All 32 real post-restore raw-bit faults preserve the projected exit
code and stop at their first host boundary before serial acknowledgement;
`raw-fault-rj61ff0w/summary.json` and its separate audit pass. Accepted full invocation:
`aggregate-pilot/invocation-9a5cvr7q/summary.json`.

All eight preserved native suites pass (275 Python tests / FCFS included;
5,258 artifacts / 798 original source bindings). Actual recipe-linked lifecycle
checks pass, including 440 atomic transactions and twenty first divergences.
Ordinary Rocket RTL diagnostic readback passes 318,637 words / seven clocks /
zero edges; captured CPU replay remains pending. Complete twelve-owner
preparation and continuation pass all 2,976 fresh cases across 744 cuts, with
all eight continuation first divergences detected before acknowledgement.
Active dispatch and bound three-owner tests pass too. Both full 16-GiB
four-hart controls pass at C=3,329,794 in
`rocket-controls/invocation-5xd7i_is/summary.json`. All full traces and workload
labels match the uninterrupted reference. Separate control/host audits and all
30 retained audits pass. Eight active host samples / 64 known component images
match, including the late cut; these remain partial inspections, not complete
CPU checkpoints. Recovery catalogs: `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json`, `summary.json` and `artifact-manifest.json`.

The controller's iteration-135 commits were published FireSim first, then
Chipyard. Remote main tips match; `.git` tracking-ref update errors are recorded
separately from successful remote publication. No staging or local commits.
Both plans and environment helpers preserve their starting bytes. No missing
external dependency is known. Next: exit/stop outer caller and complete
session/descriptor/signal/syscall-parent/context ownership; complete
configuration-specific simulator/bridge/memory ownership; coherent CPU cuts;
fresh complete Level-1 continuation and independently captured Level-2 replay.
Neither CPU checkpoint level is accepted. BOOM/Saturn remain pending.
Standalone Shuttle, physical FPGA and ASIC power remain outside this task.

Previous iteration 135 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 135, in progress. Recovery:
[native-input-provenance.md](native-input-provenance.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Fixed the controller's
continuation failure: the retained preparation build predates a Python auditor
change, while all native inputs still match. New invocations audit the original
build snapshots, separately pin live source bytes and reject edits during
execution. Fresh dispatch compilation additionally rejects changed native
inputs before building. Independent audits require complete invocation guards
when the executed checker has this contract. CPU admission is unchanged;
neither complete checkpoint level is accepted.

Diagnostics: `runs/m11-iteration135/`. Eleven focused guard tests and all 275
Python tests pass. All eight preserved native suites pass (5,256 artifacts /
796 source bindings), as do all 30 retained audits. Actual recipe-linked
lifecycle, bound three-owner restoration and active-dispatch suites pass with
their independent audits. Five resealed invocation-guard evidence mutations
reject. Ordinary Rocket RTL diagnostic readback passes 318,637 words / seven
clocks / zero edges; this remains a pattern test, not captured CPU replay.
Full native/VCS sweeps and independent audits pass 2,976 preparations and
2,976 fresh continuations across 744 cuts, with 1,105,584 host operations /
13,302,720 complete owner readbacks. All eight continuation semantic faults
stop at their first divergent word without consuming it. Both full four-hart
controls pass at C=3,329,794 with 16 GiB memory. Every full hart trace and
workload/store cycle label matches; eight active host samples / 64 known
component images match, including the late cut. Separate control and host
audits pass. These remain uninterrupted controls and partial host inspections,
not complete CPU checkpoint restores.

Recovery catalogs: `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `summary.json` and
`artifact-manifest.json`. `failure-analysis.json` preserves the original
controller failure and exact evolving source hashes. Complete continuation:
`polling-continuation/invocation-92r4gved/summary.json`; exact-recipe controls:
`rocket-controls/invocation-38rhy04q/summary.json`. Native preparation and
continuation guards now survive the previously failing retained-auditor path.

Existing controller iteration-134 commits were published FireSim first, then
Chipyard. Both GitHub main tips match; local tracking-ref updates encounter
read-only `.git`, recorded separately from the successful remote publication.
No staging or local commits. Plans and environment helpers remain unchanged.
No missing external dependency is known. Next: lifecycle/direct-exit aggregate,
session/descriptor/signal/syscall-parent/outer-context and simulator/bridge/
memory ownership; coherent CPU cuts; complete fresh Level-1 continuation and
independently captured Level-2 replay. BOOM/Saturn remain pending. Standalone
Shuttle, physical FPGA and ASIC power remain outside this task.

Previous iteration 134 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 134, in progress. Recovery:
[tsi-polling-preparation.md](tsi-polling-preparation.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). All twelve known sealed
polling owners now prepare without publication, own their replacements, bind
one destination and publish once after final pristine-destination checks.
The poll/BCD/terminal coordinator supplies a private nonthrowing publication
primitive. Lifecycle/session/context aggregate integration remains pending.
Neither complete CPU checkpoint level is accepted.

Diagnostics: `runs/m11-iteration134/`. Native ASan/UBSan and VCS pass 2,976 fresh
preparations and 2,976 fresh continuations across 744 cuts, with 1,105,584 host
operations and 13,302,720 complete owner readbacks. Candidate guards pass
abandonment, twelve late-peer changes, 172 commit-allocation failures and eight
consumed/competing rejections. Two native copy/move compile negatives reject;
C++17 return-by-value construction passes. All malformed/membership/cross-owner
and allocation failures reject atomically. Continuation and active-dispatch
suites each pass eight actual first divergences without consuming the faulty
word. The full bound three-owner suite and actual recipe-linked lifecycle suite
pass, including the prior 440 lifecycle transactions. All separate audits pass;
five resealed evidence mutations reject. All eight preserved native suites pass
(268 Python tests / FCFS included; 5,254 artifacts / 794 source bindings).
All 30 retained audits pass before and after auditor hardening, and the final
268-test Python suite passes. Ordinary Rocket RTL diagnostic readback passes
318,637 words / seven clocks / zero edges; captured CPU replay is pending.

Both full 16 GiB exact-recipe four-hart controls pass at C=3,329,794 under
`rocket-controls/invocation-92nr2hl7/`. Every full hart trace and workload/store
cycle label matches the uninterrupted reference. Eight active host samples /
64 known component images match, including the late cut; these are partial
host inspections, not complete CPU checkpoints. Separate control/host audits
pass. The native binary contains all three new preparation/commit APIs.
Recovery catalogs: `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`,
`final-auditor-inputs.json`, `summary.json` and `artifact-manifest.json`.

Both plans and environment helpers retain their initial hashes. Existing
controller iteration-133 commits were published FireSim first, then Chipyard;
both GitHub main tips match. No staging or local commits. One initial guard
pilot used incompatible relative startup paths and is excluded; the corrected
pilot and final matrix pass. No missing external dependency is known. Next:
integrate lifecycle/direct-exit publication with the prepared polling group;
complete session/descriptor/signal/syscall-parent/outer-context and simulator/
bridge/memory ownership, coherent CPU cuts, fresh complete Level-1 continuation
and independently captured Level-2 readback/replay. BOOM/Saturn remain pending;
standalone Shuttle, physical FPGA and ASIC power remain outside this task.

Previous iteration 133 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 133, in progress. Recovery:
[tsi-htif-lifecycle-preparation.md](tsi-htif-lifecycle-preparation.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Added destination-aware,
single-use lifecycle preparation and final provider guards before nonthrowing
peer publication. The component loader uses this path. The existing twelve-owner
polling aggregate and complete CPU admission remain unchanged.

Diagnostics: `runs/m11-iteration133/`. Both standalone and actual recipe-linked
lifecycle suites pass, each with 440 paired lifecycle/serial transactions,
three compile rejections and the full prior lifecycle suite (1,216 captures,
2,432 fresh final-class TSI restores, 88 raw/optional/stopped restores,
282 malformed-image processes, eighteen guards and twenty first divergences).
Both independent audits pass. Five resealed auditor-evidence mutations reject.
Production Make provider selection/header rejection and eight read-only
incompatible-build rejections pass. All eight preserved native suites pass
(268 Python tests, FCFS included; 5,254 artifacts / 794 source bindings), with
a passing completed-suite independent audit. All 30 retained audits pass.
Fresh ordinary Rocket RTL VCS passes 318,637 diagnostic words / seven clocks /
zero edges; captured CPU replay remains pending.

Both complete exact-recipe four-hart controls pass at C=3,329,794 in
`rocket-controls/invocation-tbfiwdyq/`, with full 16 GiB memory. All eight full
hart traces and every workload/store cycle label match the uninterrupted
reference. All eight active host samples / 64 known component images match,
including the late cut. Separate control/host audits pass; these are not
complete CPU checkpoints. Five incompatible provider metadata flags reject;
all four lifecycle APIs are independently bound to the actual linked object.
Recovery catalogs: `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `summary.json` and
`artifact-manifest.json`.
Accepted lifecycle: `recipe-lifecycle/invocation-nu6bqm1v/summary.json`;
standalone: `lifecycle/invocation-arsi0u2h/summary.json`.
Both plans and environment helpers retain their initial hashes. Existing
controller iteration-132 commits were published FireSim first, then Chipyard;
both GitHub main tips match. No staging or local commits. No missing external
dependency is known. Next: complete aggregate/session/descriptor/signal/
syscall-parent/outer-context and simulator/bridge/memory ownership, coherent
CPU cuts, fresh Level-1 continuation and independent captured Level-2 replay.
Neither CPU level is accepted. BOOM/Saturn remain pending; physical FPGA and
ASIC power remain deferred. An initial native audit observed the final native
check still running and is excluded; the completed suite and final audit pass.

Previous iteration 132 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 132, in progress. Recovery:
[tsi-htif-recipe-integration.md](tsi-htif-recipe-integration.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Added explicit production
Make/recipe selection of the actual lifecycle provider, a separately linked
HTIF object with an executed-build audit, and source snapshots before native
compilation. The complete lifecycle suite passes using the actual linked
recipe archive. Aggregate lifecycle/session/context ownership and both complete
CPU checkpoint levels remain pending.

Diagnostics: `runs/m11-iteration132/`. Accepted lifecycle:
`recipe-lifecycle/invocation-qzzg2vo_/summary.json`; independent audit passes.
All eight preserved native suites pass (268 Python tests / FCFS included;
5,254 artifacts / 794 source bindings), as do all 30 retained audits, the
complete 318,637-word / seven-clock / zero-edge ordinary Rocket diagnostic
readback, production Make provider selection/header rejection and eight
read-only incompatible build-record rejections. Both complete exact-recipe
four-hart controls pass at C=3,329,794 in
`rocket-controls/invocation-lnj9j73_/`, each with full 16 GiB memory. Every
full hart trace and workload/store cycle label matches the uninterrupted
reference. All eight active host samples / 64 known component images match,
including the late cut; these are not complete CPU checkpoints. Both
independent control audits pass. Five contradictory/untyped provider metadata
flags reject in the independent auditor, and the final 268-test Python run
passes. Recovery catalogs: `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `summary.json` and
`artifact-manifest.json`. The optional initial live-prefix pilot expected
buffered trace files before finish and is excluded; both complete final
controls pass. Both plans and environment helpers retain their initial hashes.
Existing controller iteration-131 commits were published FireSim first, then Chipyard;
both GitHub main tips match. No staging or local commits. No missing external
dependency is known. Complete fresh Level-1 continuation and independent
captured Level-2 replay remain pending; BOOM/Saturn remain pending. Physical
FPGA and ASIC power remain deferred.

Previous iteration 131 recovery follows.

Previous milestone checkpoint: M11-rocket-level1-level2, iteration 131, in progress. Recovery:
[tsi-htif-lifecycle.md](tsi-htif-lifecycle.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Added an opt-in
exact-header FESVR provider overlay for the actual private optional exit and
stopped fields. It preserves absent/present zero and every raw status bit,
restores without services, and rejects invalid images, occupied destinations,
signature mode and unsupported signal state before assignment. The default
recipe still retains installed `htif.o`; provider/aggregate integration and
complete signal/session/descriptor/context ownership remain pending. Neither
CPU checkpoint level is accepted.

Diagnostics: `runs/m11-iteration131/`. Accepted lifecycle summary:
`lifecycle-final/invocation-y0rvbsmo/summary.json`; independent audit:
`lifecycle-independent-audit.log`. Native/VCS pass 1,216 complete production
lifecycle captures, 2,432 fresh final-class TSI readbacks, 88 additional
optional/raw/stopped restores, 282 malformed-image processes, eighteen
lifecycle guards, a source/header build rejection and twenty boundary-zero
raw-status divergences. Every historical packet/host-tick/component byte
matches the independent oracle. These are host components, not CPU cuts.
All eight preserved native suites pass (267 Python tests and FCFS included),
with 5,260 artifacts / 794 source bindings independently audited in
`native-regressions/invocation-fixn0qrr/summary.json`. All 30 retained audits
pass again in `retained-rechecks/invocation-lftt9_9r/summary.json`; the original last control audit needed
its immutable iteration-129 builder source archive. Fresh ordinary Rocket RTL
VCS passes 318,637 diagnostic words / seven clocks / zero edges
(`ordinary-result.json`), not captured replay. The current default-provider
exit suite also passes all 1,216 cuts / 6,080 complete source images, 2,432
fresh projections, 268 invalid images, eighteen lifecycle rejections, twelve
signal-delivery proofs and sixteen first divergences; independent audit passes
(`exit/invocation-0zsktmm6/summary.json`). Recovery catalogs:
`selected-results.json`, `verification-commands.json`, `raw-native-commands.json`,
`summary.json` and `artifact-manifest.json`. Initial interrupted/changed-source
pilots and the original missing-source-archive audit are excluded.

Both plans and environment helpers retain their initial hashes. Existing
controller iteration-130 commits were published FireSim first, then Chipyard;
both GitHub main tips match. Read-only `.git` prevents local tracking-ref
updates, but remote publication succeeded. No staging or local commits.
No missing external dependency is known. Next: integrate actual lifecycle
ownership with the exact-recipe build/aggregate, complete the remaining HTIF
owners, coherent CPU cuts, complete fresh Level-1 continuation and independent
captured Level-2 readback/replay. BOOM/Saturn remain pending; physical FPGA and
ASIC power remain deferred.

Previous iteration 130 recovery follows.

Current milestone: M11-rocket-level1-level2, iteration 130, in progress. Recovery:
[tsi-htif-direct-exit.md](tsi-htif-direct-exit.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Fixed the controller's
exit-component test failure: inherited blocked SIGINT/SIGTERM masks leave
`raise()` pending, so the original test never exercises the installed handler.
Native and VCS reproduce all four original failures under a blocked parent;
all four fixed processes observe delivery, reject the unowned lifecycle and
preserve serial state. The suite now covers inherited, blocked and unblocked
starting masks and independently audits pending/delivered signal evidence.
Production checkpoint admission and state ownership are unchanged; neither
CPU checkpoint level is accepted.

Diagnostics: `runs/m11-iteration130/`. All 30 retained audits, the native/VCS
polling rejection regression and fresh ordinary Rocket RTL diagnostic readback
pass (318,637 words / seven clocks / zero edges). All eight preserved native
suites pass, including 267 Python tests, fixture metasim/replay, banked capture,
FCFS and bridge checks; their independent audit passes. The complete exit suite
passes 1,216 production cuts / 6,080 complete owner images, 2,432 fresh
projections, 268 invalid-image processes, eighteen lifecycle rejections,
twelve signal-delivery proofs and sixteen component first-divergence cases.
Accepted summaries: `exit/invocation-g8_32sg1/summary.json`,
`native-regressions/invocation-nlr8j59v/summary.json` and
`masked-signals/invocation-o8s4roe1/summary.json`. Recovery catalogs:
`selected-results.json`, `verification-commands.json`, `raw-native-commands.json`,
`summary.json` and `artifact-manifest.json`. The compile-only final-class pilot
is excluded. Both plans and environment helpers retain their initial hashes.
Existing controller iteration-129 commits were published FireSim first, then
Chipyard, and both GitHub main tips match. Read-only `.git` prevents updating
local tracking refs, but remote publication succeeded. No staging or local
commits. No missing external dependency is known. Next: complete installed
session/descriptor/signal/exit/stop and outer-context ownership, coherent CPU
cuts, complete fresh Level-1 continuation and independent captured Level-2
readback/replay. BOOM/Saturn remain pending; physical FPGA and ASIC power
remain deferred.

Previous iteration 129 recovery follows.

Previous milestone checkpoint: M11-rocket-level1-level2, iteration 129, in progress. Recovery:
[tsi-htif-direct-exit.md](tsi-htif-direct-exit.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Added an explicit direct
HTIF pass/fail status and no-signature stop component around the unchanged
installed handler. Active exit/signal/stop state now rejects historical polling
aggregate inspection. This component does not own the installed session,
descriptors, signal latch, optional exit field, stopped field or outer context;
complete CPU admission remains disabled. Neither CPU level is accepted.

Diagnostics: `runs/m11-iteration129/`. All eight preserved native suites pass,
including 267 Python tests and FCFS. All 26 retained independent audits pass.
Fresh ordinary Rocket RTL VCS again reads back all 318,637 diagnostic words /
seven clocks before an edge. Native/VCS production omission controls detect
missing exit recording at cut 20 / host tick 6 and missing stop recording at
cut 28 / host tick 8; all 480 preceding complete component images match the
independent oracle. The final direct-exit suite passes 1,216 production cuts /
6,080 complete owner images, 2,432 fresh component projections, 268 malformed
images, ten unowned lifecycle cases and sixteen first-divergence corruptions.
Its independent audit passes. The polling-cut regression now rejects the
unowned exit after proxied `sys_exit`, while preserving all eight independent
component readbacks; native/VCS execution and all 267 Python tests pass.
The production reader regression passes all 4,048 fresh reader/FIFO pairs,
68 installed syscall outputs and 3,424 complete source cuts. Atomic twelve-owner
polling preparation passes all 2,976 fresh preparations, 35,760 complete
readbacks, 4,368 malformed rejections and 2,708 allocation failures. All three
exact-recipe default/buffered/sealed four-hart controls pass at C=3,329,794,
each with the full 16 GiB memory. Every full trace and workload/store cycle
label matches the uninterrupted reference. All twelve active host samples /
112 complete known component images match reference; sealed input is `4100ff`.
No complete CPU checkpoint continuation or captured CPU replay is claimed.

Accepted summaries: `exit-final/invocation-iqc63m8o/summary.json`,
`reader-production/invocation-lpys96ka/summary.json`,
`polling-cut-final/invocation-omo0zrnb/summary.json`,
`polling-prepare/invocation-0bd3_lzo/summary.json`,
`native-regressions-final/invocation-mflxh2ih/summary.json`,
`rocket-controls-final/invocation-m4dnr1vl/summary.json` and
`rocket-sealed-terminal/summary.json`. Aggregate recovery: `summary.json`,
`selected-results.json`, `verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`. Independent audits
verify every accepted family. Source-changing pilots, the initial polling-test
expectation and diagnostic setup/path failures remain excluded. The early CPU
pilot's wrapper reported pass despite a stale object; `build-stability-audit.json`
rejects it and verifies the new guard in the selected final executable.
Follow-up: snapshot build inputs before compilation, rather than only afterward.

Existing controller iteration-128 commits were published FireSim first and
then Chipyard, with both remote main tips confirmed. Remote publication
succeeded; read-only `.git` prevented local tracking-ref updates. No staging
or local commits. The controller owns the upcoming iteration-129 checkpoint.
Both plans and environment helpers retain their iteration-128 hashes.
No missing external dependency is known. Next: complete explicit installed
session/descriptor/signal/exit/stop and outer-context ownership, coherent CPU
cuts, complete fresh Level-1 continuation and independent captured Level-2
readback/replay. BOOM/Saturn remain pending; standalone Shuttle, physical FPGA
validation and ASIC power remain excluded.

Previous iteration 128 recovery follows.

Previous milestone checkpoint: M11-rocket-level1-level2, iteration 128, in progress. Recovery:
[tsi-runtime-memif-read.md](tsi-runtime-memif-read.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Production default-session
syscall reads now use the explicit generic reader through the virtual memif
interface, with per-chunk serial cache flushing and separate startup loadmem.
Active generic readers reject twelve-owner polling admission because the
syscall parent, destination, descriptors and context remain unowned. Neither
complete CPU checkpoint level is accepted.

Diagnostics: `runs/m11-iteration128/`. Both stable native/VCS reader suites
pass all 4,336 fresh continuations at 1,084 component cuts, 2,467,736 complete
owner readbacks, 60 invalid-image processes, 156 allocation failures and
24 first-divergence cases. Actual installed syscall output, packet ordering,
host-operation labels and all 3,424 sampled source cuts match the independent
oracle; all 4,048 fresh native/VCS production reader/FIFO readbacks pass.
Native/VCS omission controls detect bypassed ownership at cut 7 / host tick 2
and missing cache flush at packet 4 / host tick 2. Installed syscall/memif
archive members remain byte-identical. All eight preserved native suites,
267 Python tests, 24 retained audits and the iteration-127 reader audit pass.
Fresh ordinary Rocket RTL VCS reads back all 318,637 diagnostic words / seven
clocks before an edge; captured CPU replay is still pending.

Exact-recipe default/buffered/sealed four-hart controls pass at C=3,329,794
with full 16 GiB backing memory; every hart trace and workload/store label
matches the uninterrupted reference. All twelve active host samples / 112
known component images pass independent audit. This iteration's sealed CPU
control used empty input rather than the historical `4100ff`: its four terminal
images match that exact empty configuration; all other images match reference.
The nonempty terminal native/VCS integration regression also passes all 52
fresh pair readbacks, 16,148 malformed metadata rejections and 44 transaction
allocation failures. No nonempty-input CPU rerun is claimed.

Accepted summaries: `read-default-final/invocation-6j7i6oni/summary.json`,
`read-policy/invocation-m9tpw5by/summary.json`,
`read-production/invocation-_0kcp4ci/summary.json`,
`native-regressions/invocation-jozfoaj3/summary.json`,
`rocket-controls/invocation-hzekq4xd/summary.json`,
`rocket-sealed-terminal/summary.json` and
`terminal-nonempty/invocation-kto0n13o/summary.json`. Aggregate recovery:
`summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json` and
`artifact-manifest.json`. Independent audits check every accepted family.
Changed-source, wrapper-formatting and sealed-metadata/configuration setup
failures remain diagnostic-only; final audits determine accepted results.
Existing controller iteration-127 commits were published FireSim first, then
Chipyard, with both GitHub tips confirmed. Pushes could not update local
tracking refs because `.git` is read-only; remote publication succeeded.
The controller owns the upcoming iteration-128 commit/publication. No local
staging or commits. No missing external dependency is known. Next: explicit
syscall/session, descriptor, signal, stop/exit and outer-context ownership,
coherent CPU cuts, full fresh Level-1 continuation and independent captured
Level-2 readback/replay. BOOM/Saturn remain pending; standalone Shuttle,
physical FPGA validation and ASIC power remain excluded.

Previous iteration 127 recovery follows.

Previous milestone checkpoint: M11-rocket-level1-level2, iteration 127, in progress. Recovery:
[tsi-memif-read.md](tsi-memif-read.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Added an explicit generic
memif read owner with head/tail/body state, copied output and pending serial
child, plus atomic reader/FIFO loading. Production syscall/HTIF dispatch remains
pending; sealed polling retains twelve owners and complete CPU admission stays
disabled. Both CPU levels remain in_progress.

Diagnostics: `runs/m11-iteration127/`. Native ASan/UBSan and VCS pass all
1,692 fresh continuations at 423 component cuts: 357,012 continued operations
and 717,408 complete reader/FIFO images. All 30 invalid-image processes, 78
allocation failures and twelve first-divergence corruptions pass. Independent
audit also checks all 24 complete corrupted pre-service images. Both native/VCS
tail/body omission mutation controls pass. All eight native suites (267 Python
tests and FCFS), all 24 retained component audits and 306,422 iteration-126
artifacts are independently verified. Fresh ordinary RTL VCS passes 318,637
diagnostic pattern words/seven clocks before an edge; captured CPU replay
remains pending. Exact-recipe default/buffered/sealed four-hart controls all
pass at C=3,329,794 after a native VCS rebuild, each with full 16 GiB memory.
Every full trace and workload/store target label matches; twelve active host
samples match all 112 known component images. These are uninterrupted controls,
not complete CPU checkpoint continuations. Final independent audits pass.

Accepted reader summary: `read-final/invocation-pkkpcbgv/summary.json`.
Accepted regression summary: `native-regressions/invocation-tf3yrt83/summary.json`.
Recovery catalogs are `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`. Independent reader
evidence is in `read-independent-audit.json`; exact CPU controls are in
`rocket-controls/invocation-yom27fih/summary.json` and
`rocket-sealed-terminal-final/summary.json`. The production adapter still needs
per-chunk cache flushing and startup loadmem policy. Development
pilots, the rejected changed-source invocation and the wrapper's post-check
formatting failure are diagnostic-only (`diagnostic-pilots.json`).

Existing controller iteration-126 checkpoints were published FireSim first,
then Chipyard; both remote tips are confirmed. No staging or local commits.
The controller owns the upcoming iteration-127 checkpoint and publication.
No missing external dependency is known. Next: production caller/parent
integration and remaining syscall/session, descriptor, signal, stop/exit and
simulator ownership, then coherent CPU cuts and complete independent Level-1
continuation and Level-2 captured readback/replay. BOOM/Saturn remain pending;
standalone Shuttle, physical FPGA validation and ASIC power remain excluded.

Previous iteration 126: atomic twelve-owner sealed polling preparation and
active identity continuation passed. Full evidence and exact workload controls
remain in `runs/m11-iteration126/`; see
[tsi-polling-dispatch-restore.md](tsi-polling-dispatch-restore.md).

Previous milestone checkpoint: M11-rocket-level1-level2, iteration 125, in progress. Recovery:
[tsi-polling-dispatch.md](tsi-polling-dispatch.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Ordinary identity dispatch
now returns blocked through both owner guards before switching to the target.
Its parent command/phase/response queue is readable during active merge cuts;
retries validate and resume the existing child. Twelve-owner atomic polling
preparation/admission remains pending. Prepared admission stays aligned-only;
complete HTIF/CPU continuation remains disabled.

Diagnostic root: `runs/m11-iteration125/`. The parent suite passes 78 fresh
native/VCS continuations, 1,560 complete readbacks, 42,010 internal invalid-image
checks, eight separate invalid-image processes and four first-divergence cases.
Actual ordinary HTIF passes 128 identity commands and 2,892 sampled cuts,
including 1,344 complete active parent images; 2,688 fresh preparations read
back all 10,752 parent/caller/write/FIFO images. Parent readback is separate
from the atomic child group, not an aggregate restore. Both native/VCS
mutation controls detect discarded child yields and the old suspended callback.
Caller/write/FIFO continuation retains 4,020 fresh processes, 30 invalid-image
processes and twelve first-divergence cases; aligned preparation retains 400
continuations and all negative cases. All labels here are host operations.

All eight native suites (267 Python tests and FCFS), all seventeen host suites
and all 23 independent component/native audits pass. All three exact-recipe
four-hart controls pass at C=3,329,794; complete traces, workload/store labels
and 104 known component images at twelve active samples match. Each retains
full 16 GiB backing memory. Rebuilt TSI/bridge/loader/context objects equal
independent recompilation. Ordinary RTL VCS reads all 318,637 pattern words and
seven clocks before any edge; captured CPU replay remains pending. No external
dependency is missing.

Recovery artifacts: `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json` and `artifact-manifest.json`. Accepted summaries:
`poll/invocation-y_vih7sy/summary.json`,
`actual-identity/invocation-vuq1hjdo/summary.json`,
`identity/invocation-rqf51t_j/summary.json` and
`aligned-identity/invocation-jawcnuph/summary.json`. The post-test prior audit
preserves all 184,830 iteration-124 artifacts and 1,044 input bindings. Earlier
diagnostic import/include pilots remain separate. Existing controller
iteration-124 commits were published FireSim first, then Chipyard, with remote
tips independently confirmed; local remote-tracking updates were denied by
the sandbox after successful pushes. Plans/environments retain their original
bytes; no staging or local commits. The controller owns the upcoming
iteration-125 checkpoint and its publication.

Next: extend parent/identity/write phase predicates and atomic preparation to
all twelve owners, then complete other memif/syscall, descriptor, signal,
stop/exit and simulator ownership. Coherent CPU capture, complete fresh Level-1
continuation and independent captured Level-2 readback/replay remain pending.
BOOM/Saturn remain pending; physical FPGA validation and ASIC power are deferred.

Previous iteration 124, in progress. Recovery:
[tsi-bcd-identity.md](tsi-bcd-identity.md) and
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Ordinary identity dispatch
now owns its command and write/response/return cursors, with atomic preparation
of the caller/write/FIFO component group. Prepared ten-owner polling retains
aligned-only identity admission; parent dispatch integration remains pending.
Complete HTIF/CPU admission stays disabled. Diagnostic root:
`runs/m11-iteration124/`. The new native ASan/UBSan and VCS suite passes 4,020
fresh continuations at 1,005 component cuts, 2,018,040 host operations and
6,066,180 complete owner readbacks. All 30 invalid-image processes preserve
their three destinations; all twelve semantic corruptions stop at the first
divergent request word without consuming it. Atomic, hostile-service and both
diagnostic mutation checks pass. Actual ordinary HTIF execution passes 128
identity commands and 2,892 sampled cuts; 2,688 fresh preparations read back
all 8,064 complete caller/write/FIFO images. These are host-operation labels,
not CPU semantic cuts. Accepted summaries are `identity/invocation-x4mo5328/summary.json`
and `actual-identity/invocation-h2xz5m4s/summary.json`.

All eight native suites (including 267 Python tests and FCFS), all 17 host
suites and 23 independent component audits pass. The preserved write/FIFO and
aligned-caller suites retain 1,616 and 400 fresh continuations. All three exact
Rocket default/buffered/sealed four-hart controls pass at C=3,329,794; complete
traces, workload/store cycle labels and 104 known component images at twelve
active samples match. Each retains full 16 GiB backing memory. Rebuilt
TSI/bridge/loader/context objects equal independent recompilation. Ordinary RTL
VCS reads all 318,637 pattern words/seven clocks before an edge; captured CPU
replay remains pending. No external dependency is missing.

Recovery artifacts are `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json` and `artifact-manifest.json`. Earlier include and
tail-corruption pilots and the rejected source-stability invocation remain
separate in `diagnostic-pilots.json`; none supplies passing evidence. The final
prior audit preserves all 113,211 iteration-123 artifacts and 1,041 bindings.
Existing controller iteration-123 commits were published FireSim first, then
Chipyard, with independent remote-tip confirmation. Plans/environments retain
their original bytes; no staging or local commits. The controller owns the
upcoming iteration-124 checkpoint and its publication.

The sealed audit passes all 184,830 iteration artifacts, 1,044 native input
bindings and 13,646 command records, with controller provenance verified.
Its result is the sibling `runs/m11-iteration124-manifest-audit.json`.

Next: make parent dispatch return blocked before capture, then extend its
phase predicates and atomic preparation to all twelve owners. Other memif,
syscall/descriptor, signal, stop/exit and simulator owners, coherent CPU cuts,
complete fresh Level-1 continuation and independently captured Level-2 replay
remain pending. BOOM/Saturn remain pending; FPGA validation and ASIC power are
deferred.

Previous iteration 123, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-memif-write.md](tsi-memif-write.md). Ordinary BCD identity now uses an
explicit copied-payload memif write child, including unaligned head/tail merge
reads and the aligned-body cursor. Prepared polling still rejects unaligned
identity; its resumable dispatch caller and atomic preparation of the new child
remain pending. Complete HTIF/CPU admission stays disabled; neither CPU level
meets acceptance.

Diagnostic root: `runs/m11-iteration123/`. The new write/FIFO suite passes
1,616 fresh continuations at 404 component cuts, 325,624 operations and 654,480
complete readbacks. All 28 invalid-image processes and twelve semantic
corruptions pass; divergent request words remain unconsumed. Both native/VCS
negative controls detect skipped tail merge and missing child-address ownership.
Actual ordinary HTIF/BCD execution passes 128 identity commands, 2,892 sampled
cuts and 2,688 fresh child/FIFO readbacks; all 1,344 active samples reject
ordinary polling admission. These are host-operation labels, not CPU cycles.
Recovery summaries are `memif-write/invocation-nvr50hp8/summary.json` and
`actual-identity/invocation-wvw9dhbn/summary.json` under the diagnostic root.

All eight preserved native suites pass, including 267 Python tests and FCFS.
Existing aligned identity continuation and atomic ten-owner preparation pass
unchanged. All three exact-recipe default/buffered/sealed four-hart controls pass
at C=3,329,794; full traces and workload/store labels match the uninterrupted
reference. Independent audits pass all 104 known component images at 12 active
samples. Each control retains full 16 GiB backing memory. The actual rebuilt
TSI/bridge/loader/context objects match independent recompilation, and the
executable binds the new write owner. These controls do not restore a CPU.
All 17 retained host suites and 22 independent component/native audits pass
(`host/host-regression-results.json`, `independent-component-audits.json`).
Ordinary RTL VCS repeats all 318,637 pattern-word/seven-clock readbacks before
an edge; captured CPU replay remains pending. No external dependency is missing.
The prior audit preserves all 88,831 iteration-122 artifacts and 1,030 native
input bindings.

Recovery artifacts are `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json` and `artifact-manifest.json` under the diagnostic
root. All checks use fresh invocations. Earlier diagnostic build, link and
bookkeeping pilots remain separate in `diagnostic-pilots.json`. No previous invocation was
overwritten. The installed, host-test and exact Rocket overlay `memif.o` members
are byte-identical (`memif-path-ownership.json`); other general memif callers
remain unowned.

The sealed audit passes 113,211 iteration artifacts and 1,041 native input
bindings, with controller provenance verified; 9,560 native command records
retain relative working directories. Its final result is the sibling
`runs/m11-iteration123-manifest-audit.json`. The post-test prior preservation
audit again passes all 88,831 iteration-122 artifacts and 1,030 input bindings
(`runs/m11-iteration123-prior-preservation-final.json`).

Both plans remain read-only; the controller owns local commits. Existing
iteration-122 controller commits were published FireSim first, then Chipyard,
with independent remote-tip confirmation.

Next: reconstruct resumable unaligned device dispatch and include its write
child in the atomic preparation contract, then complete other syscall/memif,
descriptor, signal, stop/exit and simulator ownership before CPU admission.
Required semantic CPU cuts, fresh complete Level-1 continuation and independently
captured Level-2 zero-edge readback/replay remain pending. BOOM/Saturn remain
pending; physical FPGA validation and ASIC power remain deferred.

Previous iteration 122, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-polling-preparation.md](tsi-polling-preparation.md). Prepared polling now
supports aligned 64-byte BCD identity writes through a destination-bound,
non-suspending serial writer. Unaligned identity still requires unowned memif
read/merge state and rejects before clearing tohost. Complete HTIF/CPU admission
remains disabled; both CPU levels remain unverified.

Diagnostic root: `runs/m11-iteration122/`. Native ASan/UBSan and VCS DPI pass
`aligned-identity/invocation-iwxxvjyk/summary.json`: 400 fresh continuations at
100 host-operation cuts, 19,800 operations and 202,000 complete owner readbacks.
All 132 unsupported-command rejections, four exit guards and eight semantic
corruptions pass. Identity packet corruption first diverges at operation 61,
request word 2, expected 1,684,104,562 versus actual 1,684,104,563; the word stays
unconsumed. Native/VCS negative controls detect removal of pre-clear validation.
Atomic ten-owner preparation retains 400 preparations, 4,040 readbacks, 3,200
malformed rejections, 204 membership and 44 cross-owner/configuration rejections,
2,588 allocation failures and 2,000 execution guards. These are component
operation labels, not semantic CPU cycles.

All eight native suites pass, including 267 Python tests and FCFS. Ordinary RTL
VCS again reads all 318,637 pattern words/seven clocks before an edge; captured
CPU replay remains pending. The exact-recipe Rocket build is
`rocket-controls/invocation-r3xamu9p/`; its loader/context/TSI/bridge objects
match independent recompilation. All three complete default/buffered/sealed
four-hart controls pass at C=3,329,794. Full traces and every workload/store
print-cycle label match the reference; all 104 known owner images at 12 active
samples pass independent audit. Each run retains full 16 GiB backing memory.
All 17 retained host suites and all 20 independent component/native audits
pass (`host/host-regression-results.json`, `independent-component-audits.json`).
Recovery artifacts are `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json` and `artifact-manifest.json` under the diagnostic
root. All check invocations are fresh; previous logs/images remain in place.
The sealed manifest audit passes 88,831 artifacts and 1,030 native input
bindings with controller provenance verified. Native command records total 5,192.
Prior preservation passes 85,949 iteration-121 artifacts, 22,465 external
artifacts and 1,037 input bindings. Existing controller commits were published
FireSim first then Chipyard; independent remote queries confirm both tips.
Local remote-tracking ref updates report a read-only filesystem after the
successful pushes. The controller must publish the upcoming iteration-122
checkpoint after creating it. No staging or local commits. Protected plans and
environments remain unchanged.

Next: own general memif read/merge, syscall/file-descriptor, process signals
and stop/exit state, and complete the aggregate caller/driver/simulator contract
before full CPU admission. Required
CPU cuts, complete fresh Level-1 continuation and independent captured Level-2
readback/replay remain pending. BOOM/Saturn remain pending. No external tool,
netlist, license or library dependency is missing.

Previous iteration 121, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-polling-preparation.md](tsi-polling-preparation.md). Prepared polling
components now have an executable sealed BCD caller that never replays startup,
reset or a coroutine. Complete HTIF/CPU admission remains disabled; both CPU
levels remain unverified.

Diagnostic root: `runs/m11-iteration121/`. Native ASan/UBSan and VCS DPI pass
`polling-continue-final/invocation-er_7mscr/summary.json`: 224 fresh component
continuations at 56 cuts, 6,160 host operations and 63,840 complete owner
readbacks. All 24 unowned-command rejections and four external-exit guards pass.
Four terminal-cursor corruptions stop at operation 21, request word 5, expected
321 versus actual 256, without consuming the divergent word. Native/VCS mutation
checks detect removal of validation before mailbox clear. Prerequisite atomic
ten-owner preparation retains 224 preparations, 2,280 readbacks, 3,200 malformed
rejections, 204 membership and 44 cross-owner/configuration rejections, 2,588
allocation failures and 1,120 execution/preparation guards. These are component
operation labels, not semantic CPU target cycles.

All eight preserved native suites pass, including 267 Python tests and FCFS
(`native-regressions/invocation-27qvwxe6/summary.json`). Fresh ordinary RTL VCS
again reads all 318,637 pattern words/seven clocks before an edge; captured CPU
replay is pending. Final-source exact-recipe control build is
`rocket-controls-final/invocation-_zmvyqmc/`. Its executable includes the new
caller API and every audited owner header; actual loader/context/TSI/bridge
objects equal independent recompilation. All three complete default/buffered/
sealed four-hart controls pass at C=3,329,794. Full hart traces and workload/store
print-cycle labels match the reference; all 104 known component images at 12
active samples pass independent audit. Each control uses full 16 GiB backing
memory. All 17 retained host suites and all 19 independent component/native
audits pass (`host-final/host-regression-results.json`,
`independent-component-audits-final.json`). The separate new caller audit also
passes. Recovery is `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json` and `artifact-manifest.json`. Four inherited host
commands allocated fresh invocations in earlier runs roots; their exact original
paths and bytes are indexed in `external-evidence.json` and were retained in
place. Initial warning/source-race/import pilots remain separate in
`diagnostic-pilots.json`. No external dependency is missing.

The preservation audit passes 57,348 iteration-120 cataloged artifacts and 1,015
native input bindings. The final sealed-manifest audit passes 85,949 iteration
artifacts, 22,465 external artifacts and 1,037 native input bindings, with
controller provenance verified. Exact native command records total 4,727. Existing controller commits were published FireSim first,
then Chipyard; queried remote tips match. No staging or local commits; protected
plans and environment bytes are unchanged. Both plans remain read-only.

Next: own HTIF syscall/file-descriptor, process signal, stop/exit and memif state
and complete the aggregate caller/driver/simulator ownership contract before
admitting `tick()` after restore. Required semantic CPU cuts, fresh complete
Level-1 continuation and independent captured Level-2 readback/replay remain
pending. BOOM/Saturn stay pending; physical FPGA and ASIC power remain deferred.
The controller owns local commits.

Previous milestone: M11-rocket-level1-level2, iteration 120, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-polling-preparation.md](tsi-polling-preparation.md). All ten known polling
owners now prepare atomically in a fresh metadata-bound TSI, with complete
pre-service readback. No HTIF context/CPU execution is enabled; both CPU levels
remain unverified.

Diagnostic root: `runs/m11-iteration120/`. Native ASan/UBSan and VCS DPI pass
`polling-prepare/invocation-p95inli2/summary.json`: 224 fresh ten-owner preparations
at 56 component cuts, 2,280 complete readbacks, 3,200 malformed rejections,
204 membership rejections, 44 cross-owner/configuration rejections and 2,588
injected allocation failures. All failures preserve eight pristine peers and
metadata and leave poll/BCD absent. All 1,120 execution/preparation guards pass.
The premature-terminal-publication mutation is detected. A separate valid
initialization-image guard passes native/VCS and detects guard removal.

Eight fresh native/VCS preparations of actual iteration-119 Rocket host samples
read back all 80 owner images; reconstructed trusted-workload metadata is not
captured CPU state. Credits remain distinct from semantic CPU cuts. Evidence:
`actual-rocket-preparations-v2/summary.json`. Actual Rocket loader/context/TSI/
bridge objects equal independent recompilation; its executable includes the
new preparation API and all audited headers. Ordinary RTL VCS again reads all
318,637 pattern words/seven clocks before an edge; captured replay is pending.

All eight preserved native suites pass, including 267 Python tests and FCFS.
All 13 retained host suites and all 19 independent component/native audits pass.
Complete default/buffered/sealed four-hart controls pass at C=3,329,794; every
full hart trace and workload/store print-cycle label matches the uninterrupted
reference. All 104 known host images pass at 12 active samples. Full 16 GiB
backing memory is retained. The final preservation audit passes 100,378 prior
artifacts and 1,011 native input bindings.
Existing controller commits were published FireSim first, then Chipyard, with
queried remote tips matching. No staging or local commits; protected plan and
environment hashes match. No external dependency is missing.

Recovery: `summary.json`, `selected-results.json`, `raw-native-commands.json`,
`verification-commands-native.json`, `native-input-archives.json`,
`artifact-manifest.json`, `independent-component-audits.json` and
`polling-prepare-independent-audit.json` under the diagnostic root. One passing
polling-device regression used the prior controller-recheck root; its original
bytes stay in place and `external-evidence.json` indexes all files. Diagnostic
argument-count and ABI-symbol pilots remain separate from passing evidence.

Next: reconstruct the executable polling caller without startup writes/reset
and complete syscall/file-descriptor, signal, stop/exit and simulator ownership.
Required CPU cuts, fresh complete Level-1 continuation and independent captured
Level-2 readback/replay remain pending. BOOM/Saturn remain pending; physical FPGA
and ASIC power remain deferred. Both plans stay read-only and the controller
owns local commits.

Previous iteration 119, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-sealed-terminal.md](tsi-sealed-terminal.md). Production BCD binds directly
to its polling destination. The ordered poll/terminal/BCD transaction parses
and allocates all three replacements before nonthrowing publication. Complete
CPU admission remains disabled; neither CPU level meets acceptance yet.

Diagnostic root: `runs/m11-iteration119/`. Native ASan/UBSan and VCS DPI pass
`polling-devices/invocation-20wykfub/summary.json` and
`polling-devices-rocket-parameters/invocation-8_b2bzms/summary.json`: together
448 fresh three-owner restores, 12,320 host operations and 39,648 complete owner
readbacks across all nine poll phases. Both bounded and actual Rocket mailbox/
queue configurations pass. Together they reject 1,864 malformed images, 64
owner-membership cases, eight unbound callbacks and 88 allocation failures
atomically. Sixteen cursor/response corruptions stop at the first divergent
mailbox write, host operation 20, without acknowledging it. The sequential
validate/load mutation is detected. An additional 24 native/VCS active/poisoned/
unsupported owner guards pass with 34 independently checked readable peer images.
These are component boundaries, not CPU target-cycle cuts.

All eight preserved native suites pass, including 267 Python tests and FCFS
(`native-regressions-accepted/invocation-4yitb3d4/summary.json`). All 13 retained
host suites and all 18 independent component/native audits pass. Failed link,
diagnostic-build, import-path and changing-source-binding pilots remain separate
in `pilots.json`. Actual Rocket loader/context/TSI/bridge objects match independent
recompilation. Fresh ordinary RTL VCS again reads all 318,637 pattern words and
seven clocks before any edge; this is not captured CPU replay.

All three exact-recipe complete default/buffered/sealed four-hart controls pass
at C=3,329,794. Every full hart trace and workload/store print-cycle label matches
the reference. All 104 known host images pass at 12 active samples. The production-
parameter transaction audit independently binds its configuration to the workload
ELF and actual sealed host samples. Credits/enqueue labels remain distinct from
uncertified semantic CPU cuts. All 53,043 prior cataloged artifacts and 1,006
prior native input bindings pass the final preservation guard. No external
dependency is missing. Existing controller commits were published FireSim first,
then Chipyard, with queried remote tips matching. No staging/local commits or
plan/environment/Conda edits were performed.

Recovery under the run root: `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `artifact-manifest.json`,
`independent-component-audits.json`, `polling-devices-independent-audit.json`,
`polling-devices-rocket-parameters-independent-audit.json`,
`polling-group-guards-independent-audit.json` and `preservation-audit.json`.

Next: extend atomic restoration to the complete HTIF/transport aggregate and
reconstruct its caller without startup writes/reset. Syscall/file-descriptor,
signal, stop/exit and complete simulator ownership, required active CPU cuts,
fresh Level-1 continuation and independent captured Level-2 readback/replay
remain pending. BOOM/Saturn stay pending; physical FPGA and ASIC power stay
deferred. The controller owns local commits and both plans remain read-only.

Previous iteration 118, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-sealed-terminal.md](tsi-sealed-terminal.md). The BCD component now restores
its bound sealed terminal and command queue transactionally: both images are
parsed and allocated before nonthrowing publication. Complete CPU admission
remains disabled; neither CPU level meets acceptance yet.

Diagnostic root: `runs/m11-iteration118/`. Native ASan/UBSan and VCS DPI pass
`terminal/invocation-knyl8x5i/summary.json`: 52 fresh continuations/312 host
events, four additional paired readbacks, 576 malformed pair rejections,
28 owner-membership rejections and 44 injected allocation failures. All failures
preserve both complete destination images before any service. A mutation
control using the old validate/load sequence fails precisely for partial
publication (`transaction-mutation/summary.json`). Existing metadata, terminal
and first response-divergence checks also pass. These are component events,
not CPU target-cycle cuts.

All eight preserved native suites pass, including 267 Python tests and FCFS.
All three exact-recipe default/buffered/sealed controls pass at C=3,329,794.
Every full hart trace and workload/store print-cycle label matches the reference.
Independent audits pass all 104 known host images at 12 active samples; credit
and enqueue labels remain distinct from uncertified CPU semantic cuts. All
13 retained host suites and all 17 independent component/native evidence
audits pass. Dispatcher checks retain 240 fresh continuations, 7,012 complete
peer readbacks, 5,112 atomic invalid-image rejections and four first component
divergences. Fresh ordinary RTL VCS again reads all 318,637 pattern words/seven
clocks before its first
edge. Actual Rocket loader/context/TSI/bridge objects match independent
recompilation. Existing controller checkpoints were published FireSim first,
then Chipyard, with matching queried remote tips. No staging/local commits or
plan/environment edits were performed. No external dependency is missing.
The final preservation guard passes all 53,019 prior cataloged artifacts and
1,005 prior native input bindings.

Recovery: `summary.json`, `selected-results.json`, `raw-native-commands.json`,
`verification-commands-native.json`, `native-input-archives.json`,
`artifact-manifest.json`, `independent-component-audits.json`,
`native-terminal-build-audit.json`, `sealed-workload-independent-audit.json`
and `preservation-audit.json` under the run root. Complete CPU restore and
captured replay remain pending; no FPGA or ASIC acceptance is claimed.

Next: extend transactional preparation/publication to the complete HTIF
aggregate and reconstruct a coherent caller without startup writes/reset.
Syscall/file-descriptor, signal, stop/exit and complete simulator ownership,
required CPU cuts, fresh Level-1 continuation and independent captured Level-2
readback/replay remain pending. BOOM/Saturn remain pending; physical FPGA and
ASIC power stay deferred.

Previous iteration 117, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-sealed-terminal.md](tsi-sealed-terminal.md). Sealed startup metadata now
uses revision 4 and binds the terminal's complete pristine image/input as its
eighth peer; default live metadata retains revision-3 bytes. The production
sealed polling audit includes all ten known protocol/BCD/terminal owners,
validates each image and checks repeated complete readback. Complete CPU
admission remains disabled. Neither Rocket Level-1 continuation nor captured
Level-2 replay has passed.

Diagnostic root: `runs/m11-iteration117/`. New native sanitizer/VCS evidence is
`terminal/invocation-vszs_4d9/summary.json`: eight fresh sealed metadata readbacks,
64 unchanged peer images, 16,004 atomic malformed rejections, 16 incompatible
input/mode/missing-owner/order cases and 24 caller/duplicate-preparation guards.
Two actual TSI runs audit 60 component images through input/output progress.
Existing terminal/BCD checks retain 52 fresh paired restores, 312 host events,
568 malformed rejections and four first response divergences after cursor
corruption. These remain component events, not CPU target-cycle cuts.

All eight preserved native suites pass, including 267 Python tests and FCFS.
Startup metadata and device-lifetime suites also pass. The fresh ordinary RTL
pattern diagnostic again reads all 318,637 words/seven clocks before any edge;
this is not captured CPU replay. All three exact-recipe default/buffered/sealed
controls pass at C=3,329,794. Every full hart trace and workload/store print-cycle
label matches the reference. All 104 known host images pass at 12 active samples
(64 default/buffered, 40 sealed); master credits and one-ahead enqueue labels
remain distinct from uncertified semantic CPU cuts. The build's loader/context/
TSI/bridge objects equal independent recompilation. All 13 retained host suites
and all 17 independent component/native evidence audits pass. Dispatcher checks
retain 240 fresh continuations, 7,012 peer readbacks, 5,112 atomic invalid images
and four first component divergences. All 53,355 prior cataloged artifacts and
1,005 native input bindings pass the final preservation guard. Existing
controller commits were published FireSim first, then Chipyard; remote tips
match despite local read-only tracking-ref warnings. Both plans remain unchanged.

Recovery files under the run root: `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `artifact-manifest.json`,
`independent-component-audits.json`, `native-terminal-build-audit.json`,
`sealed-workload-independent-audit.json` and `preservation-audit.json`.

Next: finish atomic aggregate restoration including terminal and BCD, coherent
caller reconstruction without startup writes/reset, syscall/file-descriptor,
signal and stop/exit ownership. Complete simulator/FAME/channel/memory/bridge
ownership, required CPU cuts, fresh Level-1 continuation and independently
captured Level-2 zero-edge readback/finite replay remain pending. No external
dependency is missing. BOOM/Saturn remain pending; physical FPGA and ASIC power
stay deferred. The controller owns local commits; no staging or local commits.

Previous iteration 116, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-sealed-terminal.md](tsi-sealed-terminal.md). An opt-in production BCD
terminal owner captures a bounded input file, cursor and binary output
transcript. Live terminals reject checkpoint operations; fresh restore emits
only subsequent output. Startup metadata explicitly rejects this additional
unbound peer. Complete CPU admission stays disabled. Neither Rocket Level-1
continuation nor captured Level-2 replay has passed.

Diagnostic root: `runs/m11-iteration116/`. The terminal invocation
`terminal/invocation-imxpr74q/summary.json` passes native sanitizer/VCS: 52 fresh
paired component restores, 312 host events, 568 atomic malformed rejections,
four incompatible images, eight incomplete pairs, 28 service guards and four
first response divergences after cursor corruption. Two production TSI checks
pass exact BCD input/output/serial routing after replacing the source input file.
These component events are not CPU target-cycle cuts. Actual recipe objects
match independent recompilation; ordinary RTL pattern readback again passes
318,637 words/seven clocks before any edge. All three complete four-hart controls
(default, buffered, sealed terminal) pass at C=3,329,794; every full hart trace
and workload/store print-cycle label matches the reference. The default/buffered
controls retain 64 independently audited active host images. Credits/tokens are
not certified semantic CPU cuts. All eight preserved native suites (267 Python
tests and FCFS included), 13 retained host suites and 17 independent audits pass.
Dispatcher results retain 240 fresh continuations, 7,012 peer readbacks, 5,112
atomic invalid images and four first component divergences. Six production input
option cases, three complete CPU requests and 16 invalid audit options reject.

All 54,064 sealed iteration-115 artifacts and 1,005 native bindings pass
preservation checks. Existing controller commits are published FireSim first,
then Chipyard, with matching remote tips despite local tracking-ref warnings.
No staging, local commits or plan/environment/Conda edits were performed.

Recovery: `summary.json`, `selected-results.json`, `raw-native-commands.json`,
`verification-commands-native.json`, `native-input-archives.json`,
`artifact-manifest.json`, `independent-component-audits.json`,
`native-terminal-build-audit.json`, `sealed-workload-independent-audit.json`
and `preservation-audit.json` under the run root. Both independently allocated
BCD regression invocations pass and are preserved. No failed pilot is claimed
as passing. Complete CPU admission stays disabled; no dependency is missing.

Next: bind the terminal peer into coherent aggregate restoration; complete
syscall/file-descriptor, signal and stop/exit ownership and reconstruct callers
without startup writes/reset. Complete simulator/FAME/channel/memory/bridge
ownership, required workload cuts, fresh Level-1 continuation and independent
Level-2 captured readback/replay remain pending. No dependency is missing.
BOOM/Saturn stay pending; physical FPGA and ASIC power remain deferred.

Previous iteration 115, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-xlen-policy.md](tsi-xlen-policy.md). Startup metadata revision 3 now binds
actual installed HTIF expected-XLEN policy, including base-reference setter
calls. Policies 0 and 64 produce distinct images and reject each other before
publication. Legacy revisions reject. Complete CPU admission stays disabled;
no Level-1 CPU continuation or captured Level-2 replay has passed.

Diagnostic root: `runs/m11-iteration115/`. Native sanitizer/VCS provider checks
pass 352 cases and two missing-provider negative controls. Native/VCS metadata
passes 24 fresh readbacks, 168 peer images, 13,964 malformed images, 20 incompatible
cases, eight policy mismatches, 192 installed-XLEN rejection/recovery checks and
704 loader-resource cases. Installed shared HTIF independently passes another
24 fresh readbacks/168 peer images/eight policy rejections. Exact-recipe loader,
context, TSI and bridge objects equal independent recompilation; dynamic symbols
bind shared HTIF to the owned loader. Both plans and guarded environment/Conda
inputs remain unchanged. All 58,484 cataloged iteration-114 artifacts and 999
native bindings pass preservation checks. All eight preserved native suites
pass, including 267 Python tests and FCFS. Default-device lifetime and context/
transport checks pass. Both complete four-hart controls independently pass at
C=3,329,794; every full trace and workload/store label matches the reference.
All 64 active host component images pass independent inspection. Credits/tokens
remain distinct from uncertified semantic CPU cuts. All 13 retained host suites,
transport/context suites and all 19 independent audits pass. Dispatcher checks
retain 240 fresh continuations, 7,012 peer readbacks, 5,112 atomic invalid images
and four first semantic divergences. Complete CPU checkpoints remain pending.

Recovery: `summary.json`, `selected-results.json`, `raw-native-commands.json`,
`verification-commands-native.json`, `native-input-archives.json`,
`independent-component-audits.json`, `native-policy-build-audit.json`,
`shared-policy-independent-audit.json`, `preservation-audit.json`, `pilots.json`
and `artifact-manifest.json` under the run root. Initial oracle, symbol-audit,
existing-directory fixture and context-audit invocation failures are retained
separately. Existing controller commits are published FireSim first, then Chipyard; queried tips
match despite read-only local tracking-ref warnings. No staging or local commits.

Next: finish complete HTIF configuration/build and terminal/syscall/stop/exit/
signal ownership, coherent caller reconstruction and atomic aggregate restoration
without startup writes/reset. Complete simulator/FAME/channel/memory/bridge
ownership, required semantic CPU cuts, fresh Level-1 continuation and independent
Level-2 captured readback/finite replay remain pending. BOOM/Saturn stay pending.
No external dependency is missing. Physical FPGA validation and ASIC power stay
deferred; the controller owns local commits and both plans remain read-only.

Previous iteration 114, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-default-device-lifetime.md](tsi-default-device-lifetime.md). The default
HTIF syscall device and device table now belong to the production TSI object's
lifetime. Native ASan/UBSan and VCS pass all 352 instances across 11 cuts,
including 256 suspended callers and 64 completed callers, with no retained
descriptors. The original source/header reproduce three leaked descriptors at
the first polling cut. Semantic device ownership and complete CPU admission
remain pending. No CPU continuation or captured clean-RTL replay has passed.

Diagnostic root: `runs/m11-iteration114/`. Both complete exact-recipe four-hart
controls pass at C=3,329,794; every full hart trace and workload/store print-cycle
label matches the uninterrupted reference. All 64 active host component images
pass independent inspection. Credits/tokens remain distinct from uncertified
semantic CPU edge/outstanding-memory cuts. All eight final native suites pass,
including 267 Python tests and FCFS. All 11 retained host suites, serial and
transport-fault suites pass. Dispatcher continuation retains 240 fresh restores,
7,012 peer readbacks, 5,112 atomic invalid images and four first divergences.
All 17 independent component/native audits pass. The fresh ordinary
Rocket pattern diagnostic passes all 318,637 words before any edge; this is
not captured replay. All 137,659 sealed iteration-113 artifacts and 1,018
original native bindings pass preservation checks. Existing controller commits
are published FireSim first, then Chipyard; remote tips match.

Recovery artifacts: `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json`, `pilots.json`,
`native-device-build-audit.json` and `artifact-manifest.json` under the run root.
Initial runner/packet-expectation and regression source-stability failures are
retained separately. Protected plans, environment/Conda inputs and both indices
match their guards. No staging or local commits were performed.

Next: bind complete HTIF configuration/XLEN and terminal/syscall/stop/exit/signal
semantics; reconstruct coherent callers and atomically restore all owners without
startup writes/reset. Complete simulator/FAME/channel/memory/bridge ownership,
required workload cuts, fresh Level-1 continuation and independent Level-2 capture/
readback/replay remain pending. No external dependency is missing. Both plans
remain read-only and the controller owns local commits.

Previous iteration 113, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-context-lifetime.md](tsi-context-lifetime.md). A build-local, installed-ABI
context replacement owns inactive and thread-exit coroutine stack storage.
Use `runs/m11-iteration113/verified/` for the final source; earlier attempts are
retained in `pilots.json`. Complete CPU admission stays disabled. No CPU
checkpoint continuation or captured clean-RTL replay has passed.

- Native sanitizer/VCS lifetime checks release all 278 stacks per backend. Six
  death cases reject active/creator destruction and active-child process exit
  before freeing a running stack. Fully instrumented context-source checks also
  pass. Suspended frames are discarded, not unwound or serialized.
- The formerly failing production transport sanitizer check passes, without
  suppression. Native/VCS independent oracles check 1,012 requests, four bridge
  runs and 24 bridge-control readbacks; all 12 original/current functional records
  match. The original iteration-112 failed sanitizer evidence remains intact.
- Both complete exact-recipe default/buffered four-hart controls pass at
  C=3,329,794. Every full hart trace and workload/store label matches the reference.
  All 64 active host component images pass independent inspection. Credits/tokens
  remain distinct from uncertified semantic edge/outstanding-memory cuts.
- Both explicit resource objects match independent recompilation and actual
  production providers. The 12 other installed members and Conda bytes remain
  unchanged. Shared HTIF resolves the executable loader; the executable host
  caller invokes its own context methods. The shared library has no context exports.
- Startup and shared-HTIF metadata checks each pass 704 resource cases, 192 XLEN
  rejection/recovery checks, 12 fresh readbacks, 84 peer images and 18 incompatible
  cases; malformed totals are 13,924 and 13,916 respectively. All precede target
  services, context entry and edges in the destination.
- All eight preserved native suites pass, including 267 Python tests and FCFS.
  All 11 retained host suites, serial and transport fault suites pass. Full
  initialization records 1,471 commands; dispatch retains 240 fresh restores,
  7,012 peer readbacks and four first divergences. The ordinary pattern diagnostic
  retains all 318,637 words/seven clocks before edges; it is not captured replay.
  Three complete CPU requests, 16 invalid audit options and five archive cases reject.
- All 66,509 sealed iteration-112 artifacts / 1,080 original native bindings pass
  preservation checks. Protected plans, environment, Conda inputs and both indices
  match. Existing controller commits are published FireSim first, then Chipyard;
  queried tips match despite local read-only tracking-ref warnings. No staging,
  local commits, plan/environment/Conda edits or history cleanup.

Recovery artifacts under `runs/m11-iteration113/`: `summary.json`,
`selected-results.json`, `raw-native-commands.json`,
`verification-commands-native.json`, `native-input-archives.json`,
`independent-audit-results.json`, and `artifact-manifest.json`. Strict-exit,
source-stability, linkage-assumption and runner pilots remain separately indexed.

Next: complete exact HTIF configuration/build/XLEN policy, terminal/syscall and
stop/signature/exit/signal ownership; reconstruct coherent semantic callers and
atomically assemble host owners without repeating startup target writes/reset.
Complete simulator/FAME/channel/memory/bridge ownership, coherent required CPU
cuts, fresh Level-1 CPU continuation and independent Level-2 captured readback/
finite replay remain pending. BOOM/Saturn remain pending. No external dependency
is missing. Physical FPGA validation and ASIC power stay deferred. The controller
owns local commits; both plans remain read-only.

Previous iteration 112: ELF-loader exception cleanup and actual production
symbol binding remain in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md)
and `runs/m11-iteration112/`. Its historical transport sanitizer check failed
with two retained 1 MiB stacks; preserve that failure. The new source is tested
independently, without suppressions.

Previous iteration 111: metadata revision-2 compatibility and pre-publication
XLEN rejection are retained under `runs/m11-iteration111/`, including its
historical installed-loader mapping-leak diagnostic. Historical metadata audits
still run and explicitly make no resource-atomicity claim.

Previous iteration-110 BCD recovery is retained in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and [tsi-bcd.md](tsi-bcd.md).

Previous recovery (iteration 109):
Current milestone: M11-rocket-level1-level2, iteration 109, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-startup-metadata.md](tsi-startup-metadata.md). Production explicit-path ELF
loads now use sealed byte snapshots. The installed HTIF entry/mailboxes/symbol
map can be reconstructed in a pristine object without target writes, reset or
host coroutine entry. This is a metadata component only; complete CPU ownership,
fresh Level-1 continuation and independently captured Level-2 replay remain
pending. Diagnostic root: `runs/m11-iteration109/`.

- Native/VCS metadata checks pass eight fresh sanitizer/VCS readbacks and all
  56 unchanged peer-component images. Every image byte/truncation plus extension
  is tested: 7,364 atomic invalid cases, followed by valid preparation. All 14
  changed-ELF/argument and unsupported-option cases reject without partial
  restore. Expected XLEN/build, devices/stop/signature/signal/context and aggregate
  ownership remain pending; prepared objects explicitly reject execution.
- Both complete exact-recipe default/buffered four-hart controls pass at
  C=3,329,794. Every complete instruction trace and workload/store CPU print-cycle
  label matches the uninterrupted reference. All eight active host samples pass
  complete eight-owner inspection; clock-token/master-credit labels remain
  distinct from semantic DUT edges. Outstanding memory cuts are uncertified.
- All ten additional host suites and all eight full native regression suites
  pass, including 267 Python tests and FCFS. Polling retains 72 fresh
  continuations, 1,332 readbacks, 38,744 atomic invalid cases and four first
  divergences; actual polling retains 324 fresh component restores / 252 caller
  readbacks. Full initialization and 240 fresh dispatcher restores pass. All
  60 exact-recipe native units/dependencies bind current sources.
- The fresh ordinary Rocket pattern diagnostic reads back all 318,637 words /
  seven clocks before edges. This is not a captured CPU image/replay. Three
  complete CPU admission requests and all 16 invalid audit options still reject.
  The previous iteration's 60,240 sealed artifacts pass preservation checks.
- Recovery: summary.json, selected-results.json, raw-native-commands.json,
  verification-commands-native.json, native-input-archives.json,
  independent-audit-results.json and artifact-manifest.json under the run root.
  Existing iteration-108 controller commits are published FireSim first, then
  Chipyard; queried remote tips match. Local tracking-ref refreshes failed on
  read-only .git after successful pushes. Protected inputs and indices match;
  no staging, local commits, plan/environment/Conda edits or history cleanup.

Next: bind configuration/build/XLEN and complete default-device, stop/signature,
signal and context ownership; atomically restore coherent host owners without
repeating startup writes/reset. Complete simulator/FAME/channel/memory/bridge
ownership, coherent early/warm/outstanding-memory/late CPU cuts, fresh Level-1
continuation, independently captured Level-2 readback/replay and whole-CPU
rejection/corruption cases remain pending. BOOM/Saturn remain pending. No external
dependency is missing. Both plans remain read-only; the controller owns commits.

Previous recovery (iteration 108):
Current milestone: M11-rocket-level1-level2, iteration 108, in progress. Recovery:
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-polling-cut-audit.md](tsi-polling-cut-audit.md). Production TSI inspection now
validates all eight owned components at a suspended polling cut, including
partial reads and idle countdowns. Startup, active syscall/memif/device services,
termination and incoherent child states reject explicitly. This is read-only
inspection; complete HTIF/TSI restore and both CPU checkpoint levels remain
unsupported. Diagnostic root: `runs/m11-iteration108/`.

- Both complete exact-recipe default/buffered four-hart controls pass at
  C=3,329,794. Every complete instruction trace and workload/store CPU print-cycle
  label matches the uninterrupted reference. All eight active host samples at
  master credits 520,064, 700,032, 900,096 and 3,250,048 pass complete inspection:
  64 component images, 79 serialized words per sample including configuration.
  Startup rejects at zero. Clock-token counts are recorded separately (one
  ahead at active samples); semantic DUT edge labels/outstanding memory remain
  uncertified. Workload hash and exact settings are bound by the build identity.
- Native/VCS installed-syscall checks reject both pending and partial 64-byte
  memif reads, inspect all eight components after installed sys_exit returns,
  then finish response publication/termination. Actual polling integration passes
  54 cross-owner rejections and 1,008 independently expected component images at
  126 cuts, all 324 fresh component restores and 252 fresh polling readbacks.
  BCD/fromhost checks retain all 20 fresh caller readbacks. These are host tests.
- All 72 fresh polling continuations, 1,332 complete readbacks, 38,744 atomic
  invalid checks, eight fresh invalid images and four first divergences pass.
  The retained initialization checks pass all 768 actual and 320 mixed-policy
  readbacks; fresh initialization dispatch passes all 240 restores, 7,012 peer
  readbacks, 5,112 atomic invalid images and four first divergences. All eight
  final native suites, including 267 Python tests and FCFS, pass.
- All 16 audit-option rejections and three unsupported complete-CPU admission
  cases pass. The ordinary Rocket pattern diagnostic reads back all 318,637
  words / seven clocks before edges; it is not a captured CPU image/replay.
- Recovery: summary.json, selected-results.json, rocket-host-audit.json,
  raw-native-commands.json, verification-commands-native.json,
  native-input-archives.json, independent-audit-results.json and the complete
  artifact-manifest.json under the run root. Failed VCS temporary-directory,
  ordinary-launcher cwd, polling-parent-path and ABI-symbol audit pilots remain
  separate from corrected runs. Use separate TMPDIRs for concurrent VCS builds.
- Existing iteration-107 controller commits are published FireSim first, then
  Chipyard; queried remote tips match. Local tracking-ref updates failed on
  read-only .git after successful remote pushes. Protected plan, environment,
  PDF and dirty Conda bytes match; no staging, local commits or history cleanup.

Next: reconstruct hash-bound HTIF metadata and complete default-device,
stop/signature/context ownership without replaying startup writes/reset. Complete
configuration-specific simulator/FAME/channel/memory/bridge ownership, atomic CPU
images, coherent early/warm/outstanding-memory/late cuts, fresh Level-1 CPU
continuation, independently captured Level-2 readback/replay and whole-CPU
rejection/corruption cases remain pending. BOOM/Saturn remain pending; no external
dependency is missing. Both plans remain read-only; the controller owns commits.

Previous recovery (iteration 107):
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-htif-poll.md](tsi-htif-poll.md). Production default-device HTIF polling now
owns all nine phases, the pending command and ordered fromhost responses, with
nonblocking serial-read/idle children. Long options (including abbreviations)
and custom-device/chroot plusargs retain the installed HTIF path. The alias bug's
failed pilot and initial source-bound runs remain separate retained diagnostics.
Final corrected native evidence is under `runs/m11-iteration107/current/`.

- All 72 fresh sanitizer/VCS caller continuations pass: 1,332 complete readbacks,
  38,744 atomic invalid-image checks, eight fresh invalid images and four first
  divergences. All 252 real polling-caller readbacks and 20 actual BCD/fromhost
  response readbacks pass before services/contexts/edges. All 18 installed-FESVR
  option cases pass. These are host components, not CPU checkpoints.
- All eight corrected native suites (267 Python tests and FCFS), all 240 fresh
  initialization dispatches, 294 retained fixture continuations, 768 actual
  initialization caller and 320 mixed cache-flush/MSIP readbacks pass. Four-worker
  execution retains every case and failed sibling; four runner tests pass.
- Both complete corrected exact-recipe four-hart controls pass at C=3,329,794.
  Every complete instruction trace and workload/store cycle label matches the
  uninterrupted reference. All 60 native units, TSI/bridge header consumers and
  unchanged generated RTL/inventory/reference/constants are bound. The ordinary
  Rocket pattern diagnostic reads back all 318,637 words / seven clocks before
  edges; it is not a captured CPU image. Complete CPU requests still reject.
- Recovery: root `summary.json`, `selected-results.json`, `raw-native-commands.json`,
  `verification-commands-native.json`, `native-input-archives.json` and full
  `artifact-manifest.json`. See `remaining-host-owners.json` for the pending audit.
  Existing iteration-106 controller commits are published FireSim first, then
  Chipyard; remote tips match. Local tracking-ref refreshes failed on read-only
  `.git` after successful pushes. No staging, local commits, protected plan/
  environment/Conda edits, reset or history cleanup occurred.

Complete HTIF startup/metadata/memif/device/stop/signature/context and cross-owner
ownership, coherent required active CPU cuts, fresh Level-1 CPU continuation,
independently captured Level-2 zero-edge CPU readback/replay and whole-CPU image/
corruption cases remain pending. Next: prove startup/child inactivity at those
cuts and reconstruct hash-bound metadata without repeating target writes/reset;
see the proposed boundary in the owner doc. Neither CPU level is accepted.
BOOM/Saturn remain pending; no external dependency is missing. Both plans remain
read-only; the controller owns staging/local commits.

Previous recovery (iteration 106):
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-program-loader.md](tsi-program-loader.md). Production program-load phase,
transport selection and cache-flush configuration now have a pointer-free owner.
Fresh component readbacks and all retained native/initialization regressions pass;
both complete exact-recipe four-hart controls match the uninterrupted reference.
HTIF ELF/memif/device/poll/stop/signature/context and cross-owner CPU ownership,
coherent active cuts, complete Level-1 continuation and independently captured
Level-2 CPU replay remain pending. Diagnostics: `runs/m11-iteration106/`.
Both plans remain read-only; the controller owns staging/local commits.

Iteration 106 (October 14):

- Production read/write/cache-flush routing consumes the new program-load phase
  owner, preserving TestChip's original initial yield and ELF loading interval.
  This owns transport selection and loader entry/return; it cannot resume an
  ELF/memif/HTIF caller. Complete CPU checkpoints remain disabled.
- Actual installed-FESVR ELF loads pass native/VCS request/partial-read/merge/
  reset/idle checks and capture 14 suspended loader images. All 28 fresh native
  sanitizer/VCS component readbacks pass before services, context entry or edges.
  All four policies/four phases pass 7,072 atomic invalid-image cases per process,
  illegal-transition/poison guards and two first-divergence phase corruptions.
- Preserved initialization checks pass 294 fresh fixture continuations, all
  768 actual caller and 320 mixed cache-flush/MSIP readbacks, atomic invalid
  cases and first divergences. Fresh initialization dispatch passes 240 restores,
  7,012 complete readbacks and 5,112 atomic invalid images. These remain host
  component cuts, not Rocket target-cycle checkpoints.
- All eight native regression suites, including 263 Python tests and full FCFS
  checks, pass. Both complete exact-recipe default/buffered four-hart controls
  pass at C=3,329,794; every full trace and workload/store label matches the
  uninterrupted reference. All 60 translation units and both TSI/bridge header
  consumers bind the new owner; generated RTL/inventory/reference are unchanged.
- Eight final and 28 retained independent audits pass. A fresh ordinary Rocket
  diagnostic reads back all 318,637 words / seven clocks before edges. Complete
  CPU requests still reject before target execution/publication. No CPU Level-1
  continuation or captured Level-2 replay is claimed; no dependency is missing.
- Recovery: `summary.json`, `selected-results.json`, `native-input-archives.json`,
  `verification-commands-native.json` and `artifact-manifest.json` under the run
  root. The running-prefix pilot incorrectly expected buffered files before
  their final flush; its failure is retained separately from the successful
  default-prefix check and complete final default/buffered comparisons.
- Existing iteration-105 controller commits are published FireSim first, then
  Chipyard. Remote tips match; local tracking-ref refreshes failed on read-only
  `.git` after the successful remote pushes. No staging, local commits, plan/
  environment/Conda edits, reset or history cleanup. Next: complete HTIF/memif/
  ELF/device/context and cross-owner ownership, then actual active CPU cuts and
  both independently restored levels. BOOM/Saturn remain pending.

Previous recovery (iteration 105):
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) and
[tsi-init-resume.md](tsi-init-resume.md). Production initialization now resumes
from owned caller/serial-read phases without a saved coroutine return path.
A four-owner component bundle validates configurations and supported phase
relationships before allocation-free atomic commit. Fresh component objects
initialize no host coroutine; HTIF continuation remains explicitly unsupported.
Diagnostics are under `runs/m11-iteration105/`. Complete CPU continuation,
coherent active cuts and independent captured Level-2 CPU replay remain pending.
Both plans remain read-only; the controller owns staging/local commits.

Iteration 105 (October 14):

- Production reset and fresh objects share a pointer-free initialization
  dispatcher. It resumes an outstanding serial read without repeating its
  flush/request and retains ordered writes, read diagnostics and MSIP policy.
  The four-owner bundle validates all candidate configurations and supported
  caller/reader phases before allocation-free atomic commit. See
  [tsi-init-resume.md](tsi-init-resume.md).
- All 240 fresh actual initialization dispatches pass in native
  sanitizer/VCS processes: 7,012 complete peer readbacks,
  6,772 operations, 5,112 atomic invalid-image checks and
  four repeated first-divergence packet-corruption checks at fixture C=101.
  These are host component cuts, not Rocket target-cycle checkpoints. Native
  sanitizer and VCS unstarted/HTIF-entry/atomic replacement guards pass too.
- The preserved initialization suite passes 294 fresh fixture continuations,
  7,264 complete readbacks, all 768 actual caller and
  320 mixed cache-flush/MSIP fresh component readbacks, all
  60 fresh invalid cases and four first divergences. All eight native
  regressions, including 263 Python tests and full FCFS checks, pass.
- Both exact-recipe default/buffered four-hart controls pass at C=3,329,794.
  Every full instruction trace and workload/store label matches the uninterrupted
  reference. All 60 native translation units, driver/bridge header consumers and
  unchanged generated RTL/inventory are bound in the native build/linkage audits.
- All 32 final/retained audit checks pass, including a fresh ordinary Rocket
  318,637-word/seven-clock diagnostic zero-edge readback and the full old catalog
  recheck after the native runs. Complete CPU preflight/capture/restore still
  reject before target execution/publication. The milestone stays in_progress.
- The failed sanitizer pilot retains the installed FESVR context destructor's
  1 MiB stack allocation diagnostic. Host initialization is now lazy; fresh
  component dispatch allocates no coroutine stack. Leak detection and installed
  library bytes are unchanged. HTIF continuation remains explicitly unsupported.
- Recovery: `runs/m11-iteration105/summary.json`, `selected-results.json`,
  `native-input-archives.json`, `verification-commands-native.json` and the full
  `artifact-manifest.json`. Existing iteration-104 controller commits are
  published FireSim first, then Chipyard; remote tips match. No local staging,
  commits, protected plan/environment/Conda edits or history cleanup.
- Next: complete HTIF/memif/device/TestChip loader/context reconstruction and
  cross-owner coherence, required early/warm/outstanding/late actual CPU cuts,
  full fresh Level-1 continuation and independently captured Level-2 replay.
  BOOM/Saturn remain pending; no external dependency is missing.

Iteration 104 (October 14):

- Added `tools.checkpoint_formats.run_artifacts`, with explicit manifest hash
  selection and no mutation of old seals. Diagnostic bytes cannot fall back to
  archived sources. Changed source bytes must exist in permitted controller
  ancestry. Index/HEAD equality remains a turn-local check; durable checks
  require linear controller checkpoints and reject protected plans in commits
  or the current index. Protected plan/environment/PDF/Conda bytes remain checked.
- The old file catalog omitted 14 dangling VCS cache symlinks. Their exact paths
  and targets now have a separately hash-pinned supplemental catalog, bound to
  the unchanged original manifest. New seals can include dangling links directly.
  Unlisted links, changed targets, altered/missing/extra files and changed seals
  reject; no diagnostic file is removed or omitted to pass verification.
- All 18 new tests pass, including real disposable controller histories, source
  evolution, rewritten/unexpected commits, staged/committed/changed protected
  plans, corrupt diagnostic bytes, incomplete audits and false CPU claims.
- The full 142,367-file / 9,085,529,263-byte catalog and all 14 supplemental
  link targets pass. All 19 retained native audits and a fresh ordinary Rocket
  RTL 318,637-word / seven-clock zero-edge diagnostic readback pass. All 263
  Python tests and eight frozen-source native regressions pass. Preliminary
  link-membership and source-stability failures remain separate diagnostics.
- Full native validation and publication records: see the iteration-104 section
  of the CPU matrix. Remaining CPU acceptance work is unchanged.
- Both exact-recipe four-hart controls pass at C=3,329,794 with complete traces
  and workload/store labels matching the uninterrupted reference. Initialization
  components pass 294 fresh fixture continuations, 7,264 complete readbacks,
  60 atomic invalid cases and four first-divergence checks; all 768 actual caller
  and 320 mixed caller restores pass before edges/services. These are component
  restores and uninterrupted CPU controls, not complete CPU checkpoints.
- Recovery: `runs/m11-iteration104/summary.json`, `selected-results.json`,
  `native-input-archives.json`, `verification-commands-native.json` and
  `artifact-manifest.json`. All selected audits use frozen sources. Existing
  iteration-103 commits are published in both forks; no local checkpoint commit
  or staging was performed. Next: complete HTIF/memif/device/TestChip child-caller/
  context reconstruction and cross-owner coherence, then required active CPU
  cuts and both independently restored levels. BOOM/Saturn remain pending.

Previous recovery (iteration 103):
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Production TestChip init
cursor, child/return phases and result/source buffers now have a pointer-free
owner bound to the complete ordered access list and MSIP policy. See
[tsi-init-accesses.md](tsi-init-accesses.md). Both complete source-stable four-hart
controls, full fresh component continuations/readbacks and all preserved native
checks pass. Evidence is under `runs/m11-iteration103/`. Installed HTIF/context/
library bytes remain unchanged. Fresh child/caller reconstruction, HTIF/memif/
device/TestChip loader and cross-owner ownership, coherent CPU cuts, complete
Level-1 continuation and independent Level-2 CPU replay remain pending.
No CPU acceptance or missing dependency. Neither plan was edited or staged.

Iteration 103 (October 14):

- Added production `firesim.tsi.init-accesses.v1`: ordered access index,
  before/after read/write/MSIP child phases and persistent result/source buffer,
  bound to every resolved access and MSIP policy. Original virtual routing,
  cache flushing, packets, empty-response yields and stderr results are retained.
  Complete validation precedes fixed-size restore with no services or edges.
  See [tsi-init-accesses.md](tsi-init-accesses.md) for unsupported fresh children.
- Both sanitizer/VCS backends pass 294 fresh fixture continuations, 7,264 complete
  readbacks, 6,970 records and 7,766 atomic/phase/interruption checks per backend.
  All 60 fresh invalid cases reject atomically; valid cursor/result corruption
  first differs at fixture C=102/C=105 with no failed operation acknowledged.
- All 384 actual installed-HTIF caller images restore in 768 fresh processes.
  Eight actual mixed TestChip runs cover cache flush and MSIP independently
  on/off; all packet words and four complete peer owner images match independent
  bytes at 160 selected cuts. All 160 caller images additionally restore in 320
  fresh processes before edges/services. These are host component cuts.
- Exact recipe rebuild retains all 60 units, binds the new header in driver and
  bridge dependencies, and retains generated RTL/reference/manifests/constants
  and installed FESVR bytes. Both complete four-hart default/buffered controls
  pass at C=3,329,794; all full traces and workload/store labels match the
  uninterrupted reference. These remain controls, not CPU restores.
- Preserved serial/read, load-memory read/queue/loader, bridge/host-control,
  actual child/poll, transport and four transport-fault suites pass. All 245
  Python tests and eight native regressions pass. Four retained state/clock/
  replay/memory-policy/TracerV audits and a fresh ordinary Rocket RTL complete
  318,637-word/seven-clock diagnostic zero-edge probe pass. Complete CPU preflight
  rejects TSI widget/12; public capture/restore reject before run/publication.
- Published existing iteration-102 controller commits FireSim first, then
  Chipyard; independent remote tips and submodule pointer match. No staging,
  local commits, protected plan/environment/library edits or history cleanup.
- Recovery: `automations/checkpoint_loop/runs/m11-iteration103/`; selected results,
  original source bindings and executable native checks are in the root JSON
  reports (19 independent audits, 950 input bindings and 5,706 native command
  records). Initial standalone include failure and two source-stability failures
  remain separate; final suites use frozen sources. Complete HTIF/memif/device/
  stop/signature and TestChip loader/cache-flush child progress, fresh context/
  caller dispatch and cross-owner coherence remain next, then required active
  CPU cuts and both complete levels. BOOM/Saturn remain pending; standalone
  Shuttle, physical FPGA validation and ASIC power remain deferred.

Iteration 102 (October 14):

- Added production `firesim.tsi.serial-read.v1`: original address/length,
  issue/response/complete phase, response cursor and every collected word, with
  complete validation before mutation and capacity reserved before dequeue.
  Packet order and original empty-response yields are preserved. No service,
  context switch or target edge occurs during component restore. See
  [tsi-serial-read.md](tsi-serial-read.md), including the remaining caller audit.
- Sanitizer/VCS checks pass 522 fresh fixture continuations, 71,828 complete
  read/FIFO readbacks, 35,392 records and 581 atomic/interruption checks per
  backend. Fifty malformed/incompatible/missing-owner cases reject atomically.
  Actual valid address/data corruption first differs at fixture C=103/C=115,
  without acknowledging the failing operation. These are component labels.
- All 384 complete actual installed-HTIF read/FIFO pairs match independent bytes
  and restore in 768 fresh processes before edges, with no restore services.
  Preserved serial FIFO tests pass 78 fixture continuations and 768 actual
  restores. Actual loader, read/queue/bridge/host-control/child-poll and transport
  regressions pass, including all four transport-fault checks.
- Exact Rocket recipe rebuild retains all 60 units and binds the new header in
  the owned implementation and all three TestChip/FireSim/bridge consumers.
  Installed FESVR, generated RTL/reference/manifests/constants and recipe
  settings remain unchanged. Both complete four-hart controls pass at
  C=3,329,794; every full instruction trace and workload/store label matches
  the uninterrupted reference. These remain controls, not CPU restores.
- All 245 Python tests and eight preserved native regressions pass; four retained
  inventory/clock/replay/memory-policy/TracerV audits and a fresh ordinary Rocket
  RTL 318,637-word/seven-clock zero-edge diagnostic probe pass. Complete CPU
  preflight rejects TSI widget/12; capture/restore reject the unavailable public
  durable runtime capability before execution/checkpoint publication. Initial
  guard/selector/import diagnostic failures remain separate from passing checks.
- Published existing iteration-101 controller commits FireSim first, then
  Chipyard; independent remote tips and the submodule pointer match. Local
  read-only tracking-ref diagnostics are retained. No staging/local commits,
  plan/environment/library edits or history cleanup were performed.
- Recovery: `automations/checkpoint_loop/runs/m11-iteration102/`; selected native
  results, original inputs, actual commands and executable checks are recorded
  in the root JSON reports (18 independent audits, 944 input bindings and 4,236
  native command records). Next: pointer-free HTIF/memif/device/TestChip caller
  reconstruction and cross-owner coherence, then required active-workload CPU
  cuts and both independently restored levels. No CPU acceptance is claimed; no
  external dependency is missing. BOOM/Saturn remain pending; standalone Shuttle,
  physical FPGA validation and ASIC power remain deferred.

Iteration 101 (October 14):

- Added `firesim.tsi.serial-queues.v1`, complete request/response FIFOs with full
  validation before atomic restore. No services, context switch or target edge
  during component restore. See [tsi-serial-queues.md](tsi-serial-queues.md).
- Across sanitizer/VCS backends, 78 fresh fixture continuations, 1,560 full
  readbacks and 1,482 records pass; each backend passes 904 atomic/interruption
  checks. All 40 malformed images reject atomically; valid request/response corruption
  first differs at fixture C=108/C=112 with no divergent operation acknowledged.
  All 384 real installed-HTIF queue images restore in 768 fresh processes.
- Exact recipe rebuild adds precisely one unit to the prior 59; all three TSI
  consumers retain the owned base-header dependency. Both complete four-hart
  controls pass at C=3,329,794, with all full traces and workload/store labels
  matching the uninterrupted reference. These are controls, not CPU restores.
- All 245 Python tests and eight preserved native regressions pass. Prior TSI
  read/queue/bridge/host-control suites, actual HTIF child/poll restores, transport
  and four transport faults pass. Retained inventory/clock/memory/policy/TracerV
  audits and the full 318,637-word/seven-clock ordinary RTL diagnostic probe pass.
  Complete CPU requests still reject before execution/publication (widget/12).
- Published existing iteration-100 commits FireSim first, then Chipyard;
  independently queried remote tips and submodule pointer match. Push logs retain
  the local read-only tracking-ref diagnostic. No staging or local commits.
- Recovery: `automations/checkpoint_loop/runs/m11-iteration101/`; exact selection,
  native inputs, original commands, executable checks and all created paths are
  in the root JSON reports. Initial checker/path/dependency/source-stability
  failures remain separate. Neither plan nor environment input was edited.
  Next: serial read/caller and HTIF/TestChip progress, cross-owner coherence,
  then required active-workload CPU cuts and both independently restored levels.
  BOOM/Saturn remain pending; standalone Shuttle, physical FPGA and ASIC power
  remain deferred.

Iteration 100 (October 14):

- Added production `firesim.tsi.host-control.v1`: busy/loaded flags, exact idle
  yield cursor and reset wait/child phase, with full validation before mutation.
  The final idle yield remains explicit until its resume; escaping switches/
  child exceptions invalidate checkpoint access. No aggregate CPU support is
  enabled. See [tsi-host-control.md](tsi-host-control.md).
- Complete component suite passes 362 fresh sanitizer/VCS fixture restores,
  7,866 full readbacks, 7,504 continuation records and 1,100 atomic/interruption
  checks per backend. All 36 invalid images reject atomically. Valid idle/target
  corruption first differs at fixture C=125/C=129 before acknowledgement.
- Actual installed-FESVR loader retains all 14 read and 22 queue checks; 68
  complete actual host-control payloads match independently reconstructed bytes.
  All 68 restore in both fresh backends: 136 zero-edge/no-service readbacks.
  Additional actual TestChip child/reset and HTIF poll/idle checks pass all
  162 captured payloads / 324 fresh complete readbacks. The exact Rocket recipe
  rebuild links the owner and retains all 59 native units. Both complete four-
  hart controls pass at C=3,329,794; every full trace and workload/store label
  matches the uninterrupted reference. These remain CPU controls.
- Prior read/queue/bridge continuations and transport/fault checks pass. Four
  retained inventory/clock/memory/policy/TracerV audits and the complete ordinary
  Rocket RTL 318,637-word/seven-clock zero-edge diagnostic probe pass. Complete
  CPU preflight/capture/restore continue to reject before run/publication.
- All 245 Python tests and the final eight-check source-stable native regression
  batch pass, retaining 5,125 artifacts / 707 source bindings. Initial transcript
  formatting,
  VCS temporary-directory collision, source-stability rejection and actual-host
  pilot diagnostics are retained separately. Failed checks are not acceptance.
- Published existing iteration-99 controller commits FireSim
  `76250b8830fbd6371ff1f71a43ab23bb81a5d0e7`, then Chipyard
  `32b41598af5c621b5d88d655d1f32914491a8abf`; independently queried remote tips
  and the submodule pointer match. No staging, local commit or protected edit.
- Recovery root: `automations/checkpoint_loop/runs/m11-iteration100/`. All created
  paths are in `artifact-manifest.json`; selected results, original executed
  commands and executable native checks are in `selected-results.json`,
  `executed-native-commands.json` and `verification-commands-native.json`.
  `native-input-archives.json` retains 929 original native input bindings. Next
  ownership: FESVR private serial queues and suspended caller/read
  destination; HTIF poll/fromhost/device/stop/signature; TestChip loader/cache-
  flush/init-access progress; and cross-owner coherence. The nonvirtual HTIF
  run path still requires audited source integration or a pointer-free engine.
  Real early/warmed/outstanding-memory/late CPU checkpoint cuts remain pending.
  BOOM/Saturn remain pending; standalone Shuttle, physical FPGA and ASIC power
  remain deferred. Neither plan was edited or staged.

Iteration 99 (October 14):

- Added production `firesim.tsi.bridge-control.v1`: initialized state, remaining
  reset-delay cursor and one-time fast-loading transition, bound to MMIO/TSI/
  memory/argument/step configuration. Whole init/tick/status calls guard active,
  reentrant and interrupted access. Restore validates both words before mutation
  and executes no services. Aggregate TSI/CPU support remains disabled. See
  [tsi-bridge-control.md](tsi-bridge-control.md).
- All 228 fresh sanitizer/VCS component restores pass: 2,584 complete readbacks,
  2,356 continuation records and 3,090 atomic/lifecycle/callback checks per
  backend. Forty invalid images reject atomically. Valid wait-cursor corruption
  first differs at fixture C=119 / operation 19 (`RECEIVE` versus `GO`), with
  zero resumed operations acknowledged. These are component fixture cuts.
- Actual installed-FESVR transport retains all 1,012 requests / 566,096 records,
  invalid/callback/merge/reset tests and 24 independent actual bridge-control
  payload checks. All 24 actual images additionally restore in both fresh native
  sanitizer and VCS processes: 48 complete readbacks, no services or edges.
  Fourteen actual read images / 22 queue images pass. Prior read and queue suites
  pass again: 260 and 340 fresh continuations/restores, respectively. All four
  private transport faults still reject their first unacknowledged wrong word.
- All 245 Python tests and eight preserved native regressions pass; independent
  audits retain 5,116 artifacts / 698 original source bindings. Four retained
  inventory/clock/memory/policy/TracerV audits and a fresh ordinary Rocket RTL
  318,637-word / seven-clock diagnostic probe pass. Complete CPU preflight,
  capture and restore still reject before run/publication.
- Exact recipe rebuild binds the bridge-control owner with all 59 native units
  unchanged. Both complete four-hart default/buffered controls pass at C=3,329,794;
  all four full traces per mode and workload/store labels match the uninterrupted
  reference. These are CPU controls, not CPU checkpoint continuations.
- Published existing iteration-98 controller commits FireSim
  `bd38643e84405ca75f02092ce2e2615e6042d419`, then Chipyard
  `9d909c6ff114d8eb73268badc17663b8f84f73ca`; both independent remote tips match.
  Local read-only tracking-ref diagnostics are retained. No staging/local
  commits or protected plan/environment edits.
- Recovery: `runs/m11-iteration99/`; exact selected native paths and executable
  checks are recorded in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).
  All created paths are in `artifact-manifest.json`; original native artifacts
  and inputs are sealed in `native-input-archives.json`. Original executed
  commands/exits and runnable checks are retained in `executed-native-commands.json`
  and `verification-commands-native.json`.
  The next required ownership includes FESVR private serial queues and suspended
  caller/context, HTIF poll/fromhost/device state, TestChip load/init progress,
  FireSim idle/reset cursors and cross-owner validation. The nonvirtual HTIF
  run path prevents a derived-name override from replacing its suspended caller.
  Coherent early/warmed/outstanding-memory/late CPU cuts and both independent
  checkpoint levels remain pending. No dependency is missing. BOOM/Saturn remain
  pending; standalone Shuttle, physical FPGA and ASIC work remain deferred.

Iteration 98 (October 14):

- Added `firesim.tsi.loadmem-queues.v1` to the actual TSI: all four load-memory
  queues plus the active write/consumed-byte cursor, complete candidate validation
  and no-throw atomic restore. HTIF/context/serial/device and bridge owners remain
  pending; no complete TSI or CPU profile is enabled. See
  [tsi-loadmem-queues.md](tsi-loadmem-queues.md).
- All 340 fresh sanitizer/VCS component restores pass, with 5,950 complete state
  readbacks and 5,610 continuation records. Each backend passes 134 atomic checks;
  42 fresh invalid images reject before mutation/continuation. Actual valid data
  corruption first differs at fixture C=114 / operation 14, expected `00` versus
  `01`, with zero resumed operations acknowledged. These are component cuts,
  not Rocket target-cycle cuts.
- Actual installed-FESVR native/VCS ELF loader passes all fourteen original read
  images and 22 complete queue images, including partial write and pending response
  cuts. All 22 actual queue images restore in fresh processes and match their
  continuations. Exact recipe rebuild links the owner with all 59 native units
  unchanged; both full four-hart default/buffered controls pass at C=3,329,794.
  All four full traces per mode and workload/store labels match the uninterrupted
  reference. Fresh ordinary Rocket diagnostic readback matches all 318,637 words
  / seven clocks before edges. These are controls/probes, not CPU checkpoints.
- All 245 Python tests and eight preserved native regressions pass. Prior read
  ownership passes all 260 fresh continuations; repaired transport passes all
  1,012 requests / 566,096 records, and all four transport mutations reject at
  their first wrong word. Four retained inventory/clock/memory/policy/TracerV
  audits pass. Complete CPU preflight/capture/restore still reject before run or
  publication. Two initial guard-checker wording errors are retained separately;
  the corrected three-process check passes.
- Published existing iteration-97 controller commits FireSim
  `1bdd959cc68d4f31964d06841c6002c7fc62032c`, then Chipyard
  `db5af10d786b231fa512d45429e2cb781b55819b`; independent remote tips match.
  Local read-only tracking-ref diagnostics are retained. No staging/local commits
  or plan/environment edits; controller owns the next checkpoint publication.
- Recovery: `runs/m11-iteration98/`; exact component/native paths and commands
  are recorded in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).
  Selected native summaries and all created paths are in `artifact-manifest.json`;
  original artifacts/input bindings are sealed in `native-input-archives.json`;
  executable checks are in `verification-commands-native.json`.
  Complete HTIF/context/serial/device/idle/reset/bridge ownership, coherent CPU
  cuts and both independent checkpoint levels remain pending. No dependency is
  missing. BOOM/Saturn remain pending; physical FPGA/ASIC work remains deferred.

Iteration 97 (October 14):

- Fixed the production TSI multi-beat load-memory read path: advance translated
  addresses, select narrow response lanes, own the GMP export buffer/value and
  validate complete request arithmetic before I/O. No complete TSI schema is
  enabled. HTIF/context, all queues/devices and bridge/generated state remain
  separate pending owners. See [tsi-loadmem-transport.md](tsi-loadmem-transport.md).
- Final native sanitizer/VCS transport evidence passes all 1,012 requests /
  566,096 independent MMIO/response records, 32 invalid requests before I/O,
  four callback-unwind checks and four actual public TSI/FESVR ELF merge/reset
  runs. Selected original: `runs/m11-iteration97/loadmem-transport-final/`
  `invocation-dd0p5ayx/summary.json`. Both private repeated-beat/response-bit
  faults fail at the first unacknowledged wrong word in both backends:
  `loadmem-transport-faults-current/invocation-ea5fqt9a/summary.json`.
  These are host transport runs, not CPU checkpoint cuts or CPU corruption.
- Exact recipe rebuild binds the helper with all 59 native units unchanged.
  Both complete default/buffered four-hart controls pass at C=3,329,794; all
  four full traces per mode and workload/store labels match the uninterrupted
  reference. A fresh ordinary Rocket RTL diagnostic probe matches all
  318,637 words / seven clocks before edges. Current preflight/capture/restore
  requests still reject unsupported TSI/durable capability before run/output.
- The first eight-check regression suite correctly rejected a concurrent fixture
  source change after its checks ran. All 245 Python tests and eight final
  native checks pass: `native-regressions-current/invocation-u3d8wjhm/`.
  Initial link/argument/fixture literal/VCS-exit diagnostics are retained in
  `failure-ledger.json`.
- Published existing iteration-96 controller commits FireSim
  `5296b0f354ef6b0a323abfe4a3e0523a77511b8b`, then Chipyard
  `b84759da160e0abb4ee03e58fdb5b4ea10898d6d`; remote tips independently match.
  Local read-only tracking-ref diagnostics are retained. No staging/local
  commits; plans, environments, local heads and indexes remain protected.
- Recovery: `runs/m11-iteration97/`; detailed scope and executable native checks
  are in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md), with exact paths
  in `artifact-manifest.json` and commands in `verification-commands-native.json`.
  All 12,876 original native artifact/input bindings are sealed; both final
  retention audits pass. The inherited probe-command quoting record is retained
  separately; a corrected command and fresh native probe are checked and added
  in `native-input-archives-v2.json`. Complete pointer-free HTIF/serial/program-load/idle/
  reset/device/queue ownership,
  coherent CPU capture and both independent checkpoint levels at all required
  cuts remain pending. No dependency is missing. BOOM/Saturn remain pending;
  physical FPGA/ASIC work remains deferred.

Iteration 96 (October 14):

- Added a pointer-free production TSI load-memory read operation owner: phase,
  address/length and all consumed response words. Atomic restore performs no
  request/dequeue work; active/interrupted callbacks reject. The actual FireSim
  TSI uses the owner, while HTIF/context/queues remain independently pending.
  Initialize the bridge's previously indeterminate FESVR pointer to null.
- Actual installed-FESVR native/VCS ELF read/modify/write integration passes,
  including a one-word suspended response, seven complete owner images per
  backend, merged bytes and original reset request. Selected evidence:
  `runs/m11-iteration96/real-fesvr-native/invocation-4ed87qfs/summary.json`.
  All 260 fresh sanitizer/VCS read-component restores pass, with 520 complete
  pre-edge owners and 193,094 continued records. Each backend passes 306 atomic
  checks; 28 fresh invalid images reject. Actual valid response corruption first
  differs at fixture C=127 without acknowledging operation 27. Selected evidence:
  `loadmem-read-current/invocation-gauvuay_/summary.json`. Initial fixture/oracle
  diagnostics are preserved. These are host-component cuts, not CPU checkpoints.
- All 245 Python tests and eight final native regressions pass:
  `native-regressions-current/invocation-kf453gp_/summary.json`. Retained
  inventory, clocks, memory/policy, TracerV, driver and CPU-control audits pass.
  Both complete current four-hart default/buffered controls pass at C=3,329,794;
  all four complete instruction traces and workload/store labels match the
  uninterrupted reference. These are CPU controls, not CPU checkpoints.
- Exact recipe rebuild binds the new owner with all 59 native units unchanged.
  A fresh ordinary Rocket storage probe passes all 318,637 words / seven clocks
  before edges. Current CPU preflight/capture/restore still reject TSI or missing
  durable capability before execution or output publication.
- Published existing iteration-95 controller commits FireSim
  `b4e1daad6df62fda628ee56e69e5e71a43cac9d0`, then Chipyard
  `a20c3f2a2ddac0f63e3627575d25302a9c96890b`; remote tips independently confirmed.
  Read-only local tracking-ref update diagnostics are retained. No staging or
  local commits; plans, environments, indexes and local heads remain intact.
- Recovery: `runs/m11-iteration96/`; ownership details in
  [tsi-loadmem-read.md](tsi-loadmem-read.md). Selected controls:
  `rocket-controls/invocation-hh3w9zq2/summary.json`; exact executable checks in
  `verification-commands.json`. All 37,119 original native artifacts/input
  bindings are sealed in `native-input-archives.json`; both retention audits
  pass. Complete file paths are
  in `artifact-manifest.json`. Complete HTIF caller/context and
  transport ownership, coherent CPU capture and both independent checkpoint
  levels remain pending. BOOM/Saturn remain pending. No dependency is missing.

Iteration 95 (October 14):

- Added complete concrete FireSim host driver and per-bridge termination-loop
  ownership. Preserve every completed-call cursor, pending termination result,
  signed exit status, registry traversal and driver lifecycle. Fresh loads do
  no MMIO/task/init/finish work. Interrupted/reentrant calls and anonymous
  profiling tasks reject. Scheduler/base flow/bridges/RTL remain separate;
  FCFS behavior and schemas are preserved. No CPU profile is enabled.
- All 224 fresh sanitizer/VCS component continuations pass, including each
  early terminating bridge, signed errors and horizon cuts. Independent original
  loop oracle checks 2,464 complete pre-edge owners and 4,846 continued records.
  Each backend passes 871 atomic/configuration/lifecycle checks; sixteen fresh
  invalid-owner processes reject before partial restore/edges/publication.
  Actual valid cursor corruption first differs at fixture C=106, without
  acknowledging that operation. These are host fixtures, not CPU checkpoints.
- All 245 Python tests and eight preserved native regressions pass. Five
  independent retained audits pass, plus a fresh ordinary Rocket VCS zero-edge
  diagnostic readback of all 318,637 words / seven clocks. Earlier source-overlap,
  compile/oracle and fixture-clock licensing failures remain preserved. The
  final fixture leaves VCS/libc time intact. No dependency is missing.
- Exact-recipe VCS rebuilt with GCC/G++ 13; retain all 58 old native units and
  add only the audited loop. Both full four-hart default/buffered controls pass
  at C=3,329,794; all four complete traces and workload/store labels match the
  uninterrupted reference. These are controls, not CPU checkpoints. Requests reject TSI
  at widget/12 or missing durable capability before run/output. Next-owner
  source audit includes serial/loadmem queues, HTIF callbacks/local read state,
  program-load/idle/reset progress, contexts and device handles.
- Published existing iteration-94 controller commits FireSim
  `28f6aa38fb1033921c399509069eb1cbd6f0b04e`, then Chipyard
  `715088bb1364419f914264cc8c218723604d4c18`; remote tips independently confirmed.
  No staging/local commits; plans, environments, indexes and local heads intact.
- Recovery: `runs/m11-iteration95/`, especially
  `firesim-driver-native/invocation-_u5imb8v/summary.json`,
  `native-regressions/invocation-rovyvlmy/summary.json`,
  `rocket-controls/invocation-4sp34o9f/`, `firesim-driver-owner-audit.json`,
  `rocket-native-source-inventory-delta.json`,
  `rocket-tsi-fesvr-pending-owner-audit.json`, CPU request guard evidence,
  `verification-commands.json`, `native-input-archives.json` and final summary.
  Next: complete TSI/FESVR and transport ownership, coherent generated/semantic
  CPU capture, then both levels at all required active four-hart cuts. Complete
  Rocket Level-1 continuation and Level-2 CPU replay remain pending. BOOM/Saturn
  remain pending; physical FPGA/ASIC work remains deferred.

Iteration 94 (October 14):

- Added opt-in `+tracerv-checkpoint-buffered` Level-1 host ownership. Own the
  entire output prefix, initialization and cycle value; bind every MMIO address,
  stream, clock, trigger and output mode. Restore validates/allocates before
  mutation and never drains tokens or publishes files. Active/poisoned calls,
  finished/live-file/fireperf/tracker modes reject explicitly.
- All 256 fresh sanitized-native/VCS component continuations pass for the four
  actual Rocket constructors, four trace modes and eight host-call cuts with
  queued tokens. Independent byte/MMIO oracle verifies complete pre-edge
  readback and 1,152 continued calls. Each backend passes 1,482 atomic/config/
  lifecycle assertions. Actual valid history corruption first differs at
  fixture C=149; lifecycle corruption rejects before initialization MMIO.
  Sixteen separate fresh malformed requests reject before edges/publication.
  These are host components, not CPU checkpoints or generated queue captures.
- All 245 Python tests and eight preserved native regressions pass. Five retained
  independent audits pass, plus a fresh complete Rocket ordinary RTL diagnostic
  readback of 318,637 words / seven clocks before edges. Old CPU-control launcher
  hashes now use their exact previously recorded source snapshot; original
  native paths remain mandatory. Initial link/archive diagnostics are retained.
- Exact Rocket VCS rebuilt with the pinned environment and GCC/G++ 13. All three
  TracerV hooks and four constructor settings match the component evidence.
  Both complete four-hart default/buffered controls pass at C=3,329,794; all
  four full traces and decoded workload/store labels match the uninterrupted
  reference. These are controls, not CPU checkpoints. New CPU requests
  still reject before run; TSI is the first unsupported widget owner.
- Existing iteration-93 controller commits FireSim
  `e3b78c81021ac14a5db17e33725a1ebe477377af`, then Chipyard
  `30b335fba5a8f3f8c59981ba8851635dc17e12bf`, were published and remote tips
  independently confirmed. No local staging/commits; plans stay read-only.
- Recovery: `runs/m11-iteration94/`, especially
  `tracerv-native/invocation-ou6pxbr8/summary.json`,
  `tracerv-invalid-native/invocation-375e7cg0/summary.json`,
  `native-regressions/invocation-axtrckf_/summary.json`,
  `rocket-controls/invocation-s3q7sujf/`, `tracerv-owner-audit.json`,
  `rocket-tracerv-integration-audit.json`, `retained-audit-final-results.json`,
  `native-input-archives.json` (8,814 bindings), `verification-commands.json`
  and final summary.
  Next: finish complete runtime run-loop/TSI/FESVR and remaining owners, bind
  semantic state through actual FAME metasim/coherent CPU clock events, then
  both levels at all required active four-hart cuts. No dependency is missing.
  BOOM/Saturn remain pending; physical FPGA/ASIC work is deferred.

Iteration 93 (October 14):

- Fixed the previous controller verification failure without weakening the
  retained-evidence audit. The historical regression launcher overwrote four
  archived logs on rerun. Recovered their exact original bytes from recorded
  content-addressed snapshots; preserved displaced verification logs and the
  recovery ledger in `runs/m11-iteration93/retained-log-recovery.json`.
- Added maintained `tools.checkpoint_formats.native_regressions`: every call
  allocates separate build/runtime/log/result paths, seals all invocation files,
  and audits prior evidence before and after execution. Source snapshots preserve
  original inputs; a source change during execution rejects. Failed processes
  and failed evidence guards cannot publish a passing result. Five retention
  tests pass, including actual subprocess mutations.
- Both complete eight-check suites pass in separate native invocations. The
  first retains 4,416 bindings; the second preserves all those bytes and the
  iteration-92 archive, binds 672 source inputs, and passes all 245 final Python
  tests. Both include full M2/M3 metasim/ordinary RTL, widget/UART/blockdev/
  heartbeat continuation/negative checks and FCFS guards. Selected originals:
  `native-regressions/invocation-7e9aw5m8/summary.json` and
  `native-regressions/invocation-gk0gj8s_/summary.json`. Use the maintained module
  for future regressions; historical fixed-path launchers overwrite evidence.
- Six retained audits pass: original complete Rocket inventory/readback,
  controller archives, both full four-hart controls, complete memory/policy
  replay and clock-event recurrence/native waveforms. Fresh exact Rocket ordinary
  RTL VCS also reads all 318,637 diagnostic words with seven clocks and zero
  edges. This remains a storage probe; no new CPU workload checkpoint is claimed.
  Recovery includes `summary.json`, `verification-commands.json`,
  `native-input-archives.json`, `final-native-evidence-audit.json` and
  `protected-turn-check.json` under `runs/m11-iteration93/`.
- Published existing iteration-92 controller commits FireSim
  `0cba18f411f8fc98f74145f67b5854a546586553`, then Chipyard
  `1c55ffeb7c34b2f7bae6fd44b33a38a873e5a07d`; remote tips independently confirmed
  in `publication.json`. Local tracking refs remain read-only. Plans,
  environments, local heads and index are preserved; no staging/local commits.
- Next: bind semantic owners through actual FAME metasim and coherent CPU clock
  events, finish run-loop/TSI/FESVR/TracerV and remaining runtime ownership, then
  both complete levels at all required active four-hart cuts. No external
  dependency is missing. BOOM/Saturn remain pending; FPGA/ASIC work is deferred.

Iteration 92 (October 14):

- Added independent Level-2 v2 image/trace payloads with complete clock phases,
  completed-rise counters and explicit event scheduling. Only settled all-low
  cuts are supported. Falling edges, simultaneous/mixed transitions and repeated
  target-cycle labels are explicit; no frequencies are inferred. Schema-3
  inventories require this binding. Legacy single-clock and Level-1 contracts
  remain independent; unsupported phases reject.
- Actual ordinary RTL seven-clock component capture and four fresh restores
  pass at event/C pairs 0/0, 12/3, 80/23 and 164/47. All twelve words read back
  before edges; all 172 samples / 1,720 outputs match. Independent source
  recurrence and native waveform audits also match all 2,064 continued state
  words. Two actual post-readback corruptions fail at event 80 / C=23 with no
  acknowledged event. Seven invalid images reject before loader publication;
  four native invalid requests preserve complete baseline storage with zero
  edges. Thirteen fresh simulator processes plus five builds are retained.
  These are ordinary component captures, not CPU or metasim workload cuts.
- All 240 final Python tests, eight preserved regression checks and four retained
  evidence audits pass. Audits preserve exact Rocket inventory, original full
  four-hart controls, complete memory/policy evidence and controller-aware
  archives. Recovery: `runs/m11-iteration92/` contains
  `multiclock-replay-current/invocation-pub5jaqh/summary.json`,
  `multiclock-replay-current-independent-audit.json`, `regression-results.json`
  and `retained-audit-results.json`. Initial native invocations and an audit
  output-count correction remain retained. Commands and scope are in the CPU
  matrix. No external dependency is missing.
- Published existing iteration-91 controller commits FireSim
  `fde729a95721c4e5d0dd3dd00368600ea4cd9a7c`, then Chipyard
  `d13fca04982c1d9f311daa9ab6a096c4f927882d`; remote tips independently
  confirmed in `publication.json`. Local tracking refs are read-only. Plans,
  environments, local heads and index are preserved; no staging or local commits.
  The controller owns this iteration's later checkpoint/publication.
- Next: bind semantic owners through the actual generated metasim and capture
  coherent events during four-hart execution; finish all CPU runtime owners,
  then both levels at required active cuts. Complete Rocket Level-1 continuation
  and Level-2 CPU replay remain untested. BOOM and Shuttle + Saturn are pending;
  physical FPGA/ASIC work remains deferred.

Iteration 91 (October 14):

- Added opt-in discovery-only multi-clock schema 3. Every input/state clock and
  forwarded output clock source is explicit. Single-clock schemas/StateIDs and
  Level-1 ownership stay independent. Multi-clock image encoding/decoding and
  banked restore reject until a coherent event-phase cut protocol exists.
- Fixed actual Rocket clean emission losing constant-driven storage and renaming
  keyword paths. Preserve all registers/RAMs; obtain access paths from actual
  emitter-internal annotations, including local instance and implicit pipeline
  renames. Independent RTL parsing audits every storage owner and clock block.
  Exact Rocket VCS reads all 318,637 diagnostic words before edges; four invalid
  loader cases preserve complete baseline state, and actual storage corruption
  is detected. Two seven-clock components also pass, with 12/13 words. All
  22 Scala inventory and 235 final Python tests pass; eight preserved regression
  checks pass. Full current forwarded-clock and complete memory regressions also
  pass: 22 words / 108 samples, 37 words / 149 samples, all five memory policies /
  245 samples and 37 fresh native memory processes. No CPU workload checkpoint
  cut or continuation is claimed.
- Corrected durable retained-evidence auditing: the loop owns later index/HEAD
  changes. Verify authorized controller ancestry, unchanged protected inputs,
  all 1,321 original archive bindings and original native runtime evidence.
  Only evolving source inputs may use their exact recorded snapshots. Original
  initialized-owner waveform, complete memory and both full four-hart controls
  re-audit successfully. Index, local HEADs, plans and environments remain
  unchanged during this implementation turn; no staging/commits were performed.
- Published existing iteration 90 checkpoints FireSim
  `cc5681b967ead61edb31a13757586a117188c195`, then Chipyard
  `ab558a7d34eefd4262e0d4d0e11d94effe563c40`; remote tips confirmed independently.
  Local remote-tracking refs are read-only. The current controller will create
  this iteration's checkpoint; publication instructions above still apply.
- Recovery: `runs/m11-iteration91/rocket-semantic-retained-inventory/`,
  `rocket-native-complete-inventory/invocation-yfr_nr9p/summary.json`,
  `rocket-native-independent-audit.json`, `selected-multiclock-fixtures.json`,
  retained evidence audits, `regression-results.json` and final summary/catalog.
  Intermediate compiler/rename/rejection diagnostics remain retained. Next:
  preserve and bind semantic owners through the actual metasim, coherent event
  scheduling and complete run-loop/TSI/FESVR/TracerV ownership, then both levels
  at all required four-hart workload cuts. No external dependency is missing.
  Physical FPGA/ASIC work remains deferred; BOOM and Shuttle + Saturn pending.

Iteration 90 (October 14):

- Added exact semantic ownership for each non-SYNTHESIS plusarg model's
  initialized `myplus` value, binding original inline source and specialized
  width/default/format in a version-2 semantic manifest. Defaults never replace
  captured runtime values. Existing manifests/StateIDs and Level-1 ownership
  remain independent. Unknown/missing/altered/duplicated external implementations
  and unsupported specializations reject before publication. Clean RTL retains
  the exact original model once. Parent clock provenance now follows driven
  child input pins without accepting data, gates, undriven nets or cycles.
- All 19 final Scala inventory tests and 225 final Python tests pass. Native
  ordinary component restores pass with default/nondefault values, nested
  instances, 1/32/65-bit storage and conflicting fresh-process plusargs at
  component C=0/3/9/16. Both direct-clock and child-input-clock fanout fixtures
  read back all five words before edges and compare 160 combined samples /
  800 outputs. Sixteen actual post-readback corruptions fail at their first
  C=9 output with no acknowledged edge; twenty invalid images and sixteen
  native loader requests reject before partial restore. Independent audits
  bind original source, actual zero-edge waveform state and all captured
  input/output waveform rows, native commands and 52 distinct
  native processes. These are component checks, not CPU checkpoint cuts.
- Exact Rocket discovery passes six initialized external owners and now rejects
  seven distinct state clocks: memory, uncore, four tiles and serial-TL input.
  No partial semantic artifacts are emitted. Independent original-hierarchy
  diagnostics retain 1,488 instances, 7,734 explicit registers, 500 memories /
  310,493 words, 404 memory-pipeline owners and six initialized values. Their
  suggested 318,637 words remain a diagnostic, not a complete manifest.
- Eight preserved native regression checks and the full forwarded-clock native
  regression pass. The full memory rerun and independent audit pass with 37
  words / 149 metasim-captured continuation samples, all five ordinary memory
  policies / 245 samples, and 37 distinct fresh native processes. Current native
  CPU preflight/save/restore still reject incomplete runtime ownership before
  execution. Both full exact-recipe default/buffered four-hart controls pass at
  C=3,329,794; complete hart traces and decoded workload/store labels match
  the uninterrupted reference. Workload SHA256 remains
  `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
  The independent native build/control audit passes with 297 inputs / 58
  translation units. Controls and unsupported-request rejections do not
  establish CPU checkpoint continuation.
- Initial oversized wide test argument, declaration-order diagnostic, concurrent
  VCS temporary-directory collision and cross-tool PID-namespace audit diagnostic
  are retained alongside complete corrected retries. Native initialized-owner
  checks now use an invocation-specific temporary root and flush settled
  waveforms before comparisons, preserving failure evidence through DPI exits.
  All VCS shells source
  both environments then `vcs-env.sh` last, retaining Y-2026.03-SP1, `-full64`
  and GCC/G++ 13; reused Make builds use `VCS_FLAGS=-Mupdate`.
- Published existing controller checkpoints FireSim
  `6522d5f5343f153b38366debf81a6b4c598ec1b0`, then Chipyard
  `643ce6776acc49726d08a8473ac6dc977f082e12`, independently confirming remote
  tips. Local tracking refs are read-only; remote publication succeeded. Plans,
  environments, index and local heads are preserved; no local staging/commits.
- Recovery under `runs/m11-iteration90/`: initialized-owner native summaries and
  waveform audits (`selected-initialized-owner-evidence.json` selects the
  original invocations), `rocket-controls/invocation-6f3ulwfs/summary.json`,
  `rocket-semantic-verified-inventory/summary.json`,
  `rocket-initialized-owner-audit.json`, `independent-memory-final-audit.json`,
  `forwarded-native/summary.json`, `regression-results.json` and final
  `summary.json` / `artifact-manifest.json` / `native-input-archives.json`.
  Exact paths and
  executable native checks are in the CPU matrix. Next: seven-clock event
  scheduling, coherent CPU cuts and complete runtime run-loop/TSI/FESVR/TracerV
  ownership, then independent full CPU Level-1 continuation and Level-2 replay
  at the required active-workload cuts. No external dependency is missing.
  Physical FPGA/ASIC work remains deferred; CPU acceptance remains in progress.

Iteration 89 (October 14):

- Implemented exact one-cycle passthrough memory owners: read-first reader data,
  write-first/undefined reader addresses, and read-first/undefined readwriter data.
  Own exact field types/names and resolved port clocks, alongside every RAM word.
  Clean emission retains this layout. Unsupported policies/latencies/clocks and
  owner collisions still reject. All 15 final Scala inventory checks pass.
- Native self-checking metasim capture plus eight fresh ordinary RTL continuations
  pass at fixture C=0/5/13/21/24/26/28/30, with all 37 words / nine entries read
  back before any edge and all 149 samples / five outputs compared. Separate
  native ordinary checks cover all five policies, twenty fresh continuations,
  six words each, and 245 samples. Four metasim-captured and five ordinary
  stored-pipeline corruptions fail at their first boundary, acknowledging no
  edge. Five invalid images and four native loader cases reject without partial
  publication/deposit. Independent original-artifact audit passes with 37
  distinct fresh native process IDs. The combined evidence audit passes with
  1,340 retained original native input/report bindings. These are component tests,
  not CPU cuts.
- Exact Rocket ChipTop discovery passes memory ownership and now rejects opaque
  `plusarg_reader`, publishing no partial semantic outputs. Raw complete
  hierarchy diagnostics find 1,488 instances, 7,734 registers, 500 memories /
  310,493 logical words, six opaque cells and 404 candidate implicit read-data
  owners. All synchronous memories are undefined-policy readwriters. These
  counts are diagnostics, not a complete semantic manifest.
- Golden Gate changes undefined readers from stored addresses to read-first data;
  the unchanged-hierarchy oracle rejects this mapping. Its initial diagnostic,
  incorrect fixture readwriter hold expectation and missing ordinary initreg
  compile option are retained with corrected full retries. Undefined-reader
  ordinary checks pass; conversion across the GG policy change remains unsupported.
- All 221 final Python tests, eight preserved native regression checks and the
  full five-cut forwarded-clock native regression pass. Fresh current native
  CPU preflight/save/restore reject incomplete runtime ownership before execution.
  Both exact-recipe default/buffered four-hart controls pass at C=3,329,794;
  all full traces and decoded workload/store labels match the uninterrupted
  reference. Workload SHA256 remains
  `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
- Published controller checkpoints FireSim
  `a8d3ed98c000f2fa46ce31b5c12b3c2bc9ce878b`, then Chipyard
  `b0fb1ef48f5f8949c4c40f9187e28e8f453c77c3`, confirming remote tips. Local
  remote-tracking writes hit read-only metadata; remote pushes succeeded. No
  staging or local commits. Plans, environment inputs, indexes and heads remain
  preserved. The loop's prior artifact complaint came from reporting a directory
  where its validator requires a nonempty file; report concrete summary files.
- Recovery under `runs/m11-iteration89/`: `memory-complete-native/summary.json`,
  `ordinary-memory-policies-complete/summary.json`, `independent-memory-audit.json`,
  `rocket-semantic-final-inventory/summary.json`, `rocket-memory-policy-counts.json`,
  `forwarded-native/summary.json`, `regression-results.json` and
  `native-input-archives.json`. Complete controls are retained in
  `rocket-controls/invocation-t0bmlj86/`; final `summary.json`,
  `artifact-manifest.json`, `executed-native-commands.json` and
  `verification-commands.json` recover exact scope and original artifacts.
  Executable checks are in the CPU matrix.
  Next: exact plusarg semantic ownership and complete clock-event scheduling,
  then coherent CPU cuts, run-loop, TSI/FESVR, TracerV and remaining runtime
  owners; complete fresh CPU Level-1 continuation and independent Level-2
  capture/readback/replay at all active cuts with image rejection and corruption.
  Physical FPGA/ASIC work remains deferred; no external dependency is missing.

Iteration 88 (October 13–14):

- Implemented pre-FAME clock provenance through concrete nested/sibling outputs,
  transparent one-bit IO cells and exact Clock/UInt bitcasts. Dependencies resolve
  lazily and distinguish parent pins from child ports. Generated/gated/undriven/
  cyclic clocks, data inputs, registers used as aliases, opaque definitions and
  distinct state domains continue to reject. No CPU profile/schema is enabled.
- All 13 Scala inventory checks pass. The new forwarded-clock fixture passes
  native VCS metasim capture and five fresh ordinary RTL VCS restores/replays
  at fixture C=0/5/22/24/26: all 22 words / 15 semantic entries read back before
  edges, and all 108 continuation samples compare all 13 outputs. Five actual
  invalid/incompatible/incomplete images and four native loader cases reject
  before partial publication/deposit. Actual stored `a.saved` corruption after
  full readback first fails `io_left` at fixture C=26, acknowledging zero edges.
  The independent fixture audit passes. This is compiler/fixture evidence,
  not CPU checkpoint acceptance.
- Exact Rocket ChipTop discovery gets past the clock aliases and now rejects
  L2 directory `cc_dir_0` (read=1/write=1, readwrite port), publishing no partial
  semantic outputs. The raw hierarchy diagnostic records 1,488 instances,
  7,734 explicit registers and 500 memories / 310,493 logical words, including
  404 memory-pipeline obligations and six opaque plusarg readers. Implicit
  pipeline/opaque state remains unowned; these totals are not a full manifest.
- All 221 Python tests and eight preserved native regression checks pass,
  including M2/M3 metasim/ordinary RTL, 52 widget, 18 UART, 30 blockdev and
  96 heartbeat continuations and FCFS Make/generator guards. Full exact-recipe
  default/buffered four-hart controls pass at C=3,329,794; all full traces and
  decoded workload/store labels match the uninterrupted reference. All six
  complete generated source/inventory comparisons match the prior build.
  The workload hash remains `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
  Fresh CPU preflight/save/restore reject incomplete runtime support without
  partial images. These controls/rejections do not establish CPU continuation.
  The combined independent evidence audit passes with 527 retained native
  input/report bindings; plans/environment inputs/indexes/heads are preserved.
- Published existing controller checkpoints FireSim
  `aa143ccc404eb97faff3a23249e2d38027a6d969`, then Chipyard
  `c9b10d3634173bdd010df5092efcdff81ad83381`, confirming remote tips. Git could
  not update local remote-tracking refs on read-only metadata; both remote
  pushes succeeded. No local staging/commits or required external dependency
  failure. Initial compiler/fixture launcher diagnostics and complete retries
  remain under `runs/m11-iteration88/`.
- Recovery: `forwarded-verified-native/summary.json`,
  `independent-fixture-audit.json`, `rocket-semantic-final-inventory/summary.json`,
  `rocket-semantic-memory-obligations.json`, `regression-complete/`,
  `selected-evidence.json` and `native-input-archives.json` under that run root.
  `rocket-controls/invocation-8mdtqxuy/summary.json` retains the complete native
  controls; `verification-commands.json` and `verify-evidence.py` check the
  selected original artifacts without replacing them.
  `summary.json` and `artifact-manifest.json` enumerate final scope and full
  artifact paths. Exact native inner argv are in `executed-native-commands.json`.
  Executable native checks are in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).
  Next: own synchronous/readwrite memory pipeline state and multi-clock events;
  implement coherent CPU cuts, run-loop, TSI/FESVR, TracerV and remaining runtime
  owners; then fresh complete CPU Level-1 restores and independent Level-2
  capture/zero-edge readback/finite replay at all active cuts, with CPU image
  rejection and first-divergence cases. Physical FPGA/ASIC work stays deferred.

Iteration 87 (October 13):

- Fixed the preceding verifier failure: an up-to-date Make returned success
  without invoking VCS, and the overwritten build log then failed native source
  binding. `VCS_FORCE_REBUILD=1` now crosses both recursive Make layers for
  exact CPU recipe checks, without changing source timestamps or forcing RTL
  elaboration. Ordinary builds retain their existing caching behavior.
- Added maintained complete Rocket control/build auditing with separate retained
  invocation directories, executable-bound native argv, actual compiler
  dependencies, static FESVR archive and shared-library hashes. No CPU runtime
  profile or semantic schema is enabled by this infrastructure.
- Two exact-recipe native builds and all five full four-hart controls pass at
  C=3,329,794. Both default/buffered pairs and the frequent-heartbeat control
  match every complete hart trace and independently decoded workload/store
  label against the uninterrupted reference. Frequent polling retains 202 real
  clock samples, C=16,459 through 3,322,351. Workload SHA256 remains
  `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
- The independent maintained control audit passes. Each native build binds 297
  inputs / 58 translation units; all 594 bindings have retained original bytes.
  All 221 Python tests and eight preserved regression checks pass: full M2/M3
  VCS metasim/ordinary RTL, 52 widget, 18 UART, 30 blockdev and 96 heartbeat
  native/VCS continuations, plus eight FCFS Make/four generator guards. Historical
  iteration-84/85 audits pass using archived original recipe-helper Git bytes;
  the initial stale-source diagnostic is retained. Fresh CPU preflight/save/
  restore and ChipTop semantic discovery still reject incomplete ownership/
  `bdev_clock`, publishing no partial images or semantic outputs.
- Published controller checkpoints FireSim
  `06d8dd43b2162fdf943c255167404889d8afd95c`, then Chipyard
  `bc3878be2bf298af6217dc7db1c2383c871cc70a`, confirming remote tips. No
  staging or local commits. Plans, environments, indexes and heads are preserved.
- Recovery: `runs/m11-iteration87/summary.json`, `selected-evidence.json`,
  `native-input-archives.json`, `artifact-manifest.json` and
  `verification-commands.json`; the selected maintained run is
  `reusable-controls/invocation-yq4cdng6/summary.json`. Executable commands and
  exact scope are in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).
  Full CPU Level-1 restore, independent Level-2 semantic restore/replay, all
  required active-workload cuts and CPU image/corruption cases remain pending.
  No required external dependency is missing; no FPGA or ASIC claims.

Iteration 86 (October 13):

- Re-read the current read-only priorities, relevant simulator/semantic plan
  sections, progress/publication instructions and root-paper capture/replay
  extracts before editing. Protected inputs and controller heads/indexes are
  recorded under `runs/m11-iteration86/`.
- Implemented `firesim.widget.heartbeat.v1`, gated on explicit
  `+heartbeat-checkpoint-buffered`. Own the polling counter, last observed
  64-bit target count, sticky timeout, start epoch and complete log samples;
  bind interval/partition mode and the actual clock owner's six MMIO addresses.
  Completed calls before finish are supported. Live log files and
  finished/suspended/interrupted calls reject; decode/allocation precede mutation.
- Native ASan/UBSan and fresh VCS DPI pass 96 continuations, complete zero-edge
  readback, all MMIO/termination boundaries and full buffered log retention.
  Each backend passes 772 negative assertions without partial restore/MMIO.
  Actual valid poll-counter corruption first fails `heartbeat_poll` at fixture
  C=107, operation 1, before reading the cycle or returning termination status.
  Fixture wall time is deterministic; production timestamps remain diagnostic.
  These checks establish a host component, not complete CPU checkpoint support.
- Exact-recipe native Rocket rebuild links the adapter, with 207 current
  inputs, 58 host translation units and the pinned VCS/GCC/G++ setup.
  Default and buffered full four-hart controls pass at C=3,329,794, with all
  four complete traces and decoded workload/store labels matching the previous
  uninterrupted run. A third full control with actual frequent heartbeat
  polling also passes at C=3,329,794, retaining 202 real clock samples
  (C=16,459 through 3,322,351) and identical complete traces/store labels.
  Workload SHA256 remains
  `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
  All 219 Python tests, full M2/M3
  VCS metasim/ordinary RTL checks, 52 existing widget continuations, UART and
  blockdev native/VCS continuations and eight FCFS Make/four generator guards
  pass. Historical iteration-84/85 evidence passes with archived original
  heartbeat sources independently checked against pinned Git objects.
- Fresh current-source ChipTop discovery still rejects `bdev_clock`, emitting
  no partial semantic outputs. Rebuilt CPU preflight/save/restore still reject
  incomplete runtime ownership without partial checkpoint publication.
  The initial control wrapper incorrectly required heartbeat samples at the
  default interval; both actual native runs passed, and the corrected full
  audit passes. Preserve `run-rocket-controls.initial.py`, `rocket-controls.log`
  and the separate passing retry. Frequent polling is checked independently
  by the third full run, retaining the original control scope.
- Published existing controller commits FireSim
  `4e564603726d151e0a0ad020b13259148297ad01`, then Chipyard
  `5577b7b9288d77512d093e45bf3ddcac50478d75`, confirming both remote tips.
  No staging/local commits; plans, environment inputs, indexes and heads
  remain preserved. An interim direct Python checker lacked `PYTHONPATH`;
  the correct package invocation passes, and the original diagnostic remains.
- Complete CPU Level-1 ownership/continuation and independent
  multi-clock Level-2 inventory/zero-edge readback/replay remain pending.
  Recovery and executable native checks: [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).
  `runs/m11-iteration86/selected-evidence.json`, `summary.json`,
  `verification-commands.json`, `artifact-manifest.json` and `verify-evidence.py`
  recover exact artifacts and source-bound checks. No required external
  dependency is missing; physical FPGA/ASIC work remains deferred.

Iteration 85 (October 13):

- Re-read read-only current plan priorities, relevant simulator/semantic
  contracts, progress and publication instructions before editing. Rechecked
  root-paper hashes and complete-state/finite-I/O replay extracts.
- Added `firesim.widget.uart.v1`, gated on explicit
  `+uart-checkpoint-file0` with finite regular-file input and buffered output.
  Own all input bytes/cursor, output bytes and six handshake/data fields;
  bind the actual six MMIO addresses and UART index. Completed, unpoisoned
  calls before finish are the supported lifecycle; live stdio/signals/PTYs,
  ordinary descriptors and finished/interrupted/suspended calls reject.
- Native ASan/UBSan and fresh VCS DPI each pass all nine cuts, complete
  zero-edge readback, all bus operations and binary output prefix retention.
  Each passes 723 malformed/incompatible/incomplete/lifecycle assertions
  without partial owner mutation or MMIO. A valid cursor corruption first
  fails `uart_in_bits` at fixture C=128, operation 4, before its valid handshake.
  These are host component checks, not whole-CPU or semantic replay acceptance.
- Exact-recipe native Rocket rebuild links the adapter and binds 207 inputs,
  58 actual host translation units and GCC/G++ 13.3. Default and buffered UART
  full four-hart controls both pass at target count 3,329,794. All four complete
  traces, decoded workload/store/HTIF labels and generated artifacts match the
  prior uninterrupted control. These are controls, not CPU checkpoint restores.
  Fresh complete ChipTop semantic discovery still rejects `bdev_clock`,
  publishing no partial manifest/ordinary RTL. Native CPU preflight/save/
  restore still reject incomplete runtime ownership without partial images.
- All 219 Python tests, full M2/M3 VCS metasim/ordinary RTL regressions, 52
  existing widget continuations and eight FCFS Make/four generator guards pass.
  The independent retained iteration-84 audit now passes using pinned Git
  source objects for its old UART inputs. Persistent evidence checks retain
  protected file hashes and controller ancestry; raw index/HEAD preservation
  is checked at implementation-turn end. See [evidence-lifecycle.md](evidence-lifecycle.md).
- Published existing controller commits FireSim
  `9a0944cae10a90ca8f5950f013dad72e743efe2f`, then Chipyard
  `f9253bdbd7d469045389739b1f4db7c798737bec`, confirming both remote tips.
  No staging/local commits; plans, environments, indexes and heads preserved.
- Recovery: `runs/m11-iteration85/` contains executable controls, source and
  owner bindings, component selection and reusable evidence checks. Next:
  implement coherent CPU cuts, run-loop,
  TSI/FESVR, TracerV, heartbeat and remaining owners; independent multi-clock
  semantic inventory, fresh full CPU restores/replay and CPU image/fault cases.
  The initial buffered post-run audit lacked its command metadata; the actual
  native run passed, and the metadata correction plus independent re-audit/full
  comparison passes without rerunning or shortening the workload. Initial
  diagnostics are retained. No required external dependency is missing. Both
  CPU levels remain in progress.

Iteration 84 (October 13):

- Re-read current read-only plan priorities, relevant simulator/semantic
  sections, progress and publication instructions before editing. Revisited
  both papers' complete-state/finite-I/O replay contract through hash-checked
  saved extracts. Plans, environment inputs, indexes and heads are protected.
- Implemented `firesim.widget.blockdev.v1` for the actual Rocket private-memory
  disk and disconnected mode. Complete ordered queues, lifecycle/pending state,
  every tracker word, all backing bytes and FILE position are captured. Bind
  all actual MMIO/geometry/latency settings. Parse/allocation precedes mutation;
  suspended/interrupted calls and unsupported external disks/logs reject.
  CPU profile/whitelist and Level-2 schemas remain unchanged.
- Native ASan/UBSan and fresh VCS DPI each pass all 15 cuts, complete zero-edge
  owner readback, 128 read response words/two acks at the original fixture
  labels, and 1,639 negative assertions without partial restore or MMIO.
  Full varied-disk/end-position readback passes too. Actual partial-write
  tracker corruption first fails `bdev_rresp_data_lower` at fixture C=142,
  operation 6, exit 1, issuing no operation 7. These are component checks;
  they do not establish complete CPU restore or Level-2 semantic replay.
- A new exact-recipe VCS build links the current adapter and preserves prior
  evidence. Its full 16-GiB, four-hart control passes at C=3,329,794. Every
  complete hart instruction trace, independently decoded phase/completion/
  failure/HTIF store and CPU-print label matches the prior uninterrupted
  control. Generated RTL, compared headers and full inventory bytes match.
  These are workload controls, not restored CPU execution.
  Fresh current-source ChipTop discovery still explicitly rejects
  `FireSim.chiptop0.system.bdev_clock`, with no partial semantic outputs.
  Rebuilt native preflight/save/restore requests still reject unsupported CPU
  runtime ownership and publish no partial image.
- All 219 Python tests, full M2/M3 metasim/ordinary RTL regressions, 52 existing
  native/VCS widget continuations, eight FCFS Make/four generator guards pass.
  The initial M3 invocation used the wrong module name; its diagnostic remains
  in `banked-regression.log`, and the actual `verify_banked_vcs` retry passes
  the complete scope. The independent evidence audit caught a negative fixture
  overwriting the positive cut-5 trace; isolated its output, reran both complete
  native component suites and now retain/recheck all positive traces. Initial
  diagnostics remain preserved. Logs and executable commands stay under
  `runs/m11-iteration84/`; recovery is in the CPU matrix.
- Published existing controller checkpoints FireSim
  `2427333a9c89070d515cf02b553c79b28f9f5fd7`, then Chipyard
  `4eb16eae84b8dbad899c7070e9e941bed13b694b`; both remote tips independently
  confirmed. No staging or local commits; the controller owns its next one.
- Next: run-loop/TSI/FESVR/UART/TracerV/heartbeat and remaining native owners,
  coherent CPU cuts and full fresh Level-1 continuation; independent multi-clock
  semantic lowering, complete CPU zero-edge Level-2 restore/finite replay and
  CPU image/semantic corruption checks. No required external dependency is
  missing. Physical FPGA and ASIC power remain deferred.

Iteration 83 (October 13):

- Read current read-only plan priorities, relevant simulator/semantic sections,
  progress, previous verification and publication instructions before editing.
  Root papers' state capture/replay sections were read through pypdf; input
  hashes and extracts are under `runs/m11-iteration83/`. Plans/PDFs, native
  environment files, indexes and local heads remain protected.
- Added an exact non-SYNTHESIS metasim plusarg-register adapter, binding source
  bytes and every WIDTH/DEFAULT/FORMAT specialization. The independent emitted
  Verilog checker audits parameterized instances and requires complete owners;
  it rejects altered source/configuration, missing state and hidden registers.
  No CPU runtime whitelist extension or Level-2 schema substitution.
- Exact Rocket generated inventory and independent declaration audit pass:
  2,292 instances, 11,464 entries, 445,838 words, 21,000,837 bits. All seven
  plusarg registers are included. Eight actual Rocket artifact mutations reject,
  preserving positive bytes. Full simulator/host ownership remains unfinished.
- Fresh exact-recipe VCS metasim with full 16-GiB memory passes the real
  four-hart workload at C=3,329,794. All four complete instruction streams and
  independently decoded store values/cycle fields match iteration 82. Every
  generated word is captured at target-count 50,000 / 850,000 / 1,013,847 /
  3,200,000. Source-bound tag decoding confirms warm D-caches on all harts;
  the outstanding sample has real cached grants pending on harts 1/2/3 and
  an actual host read in flight. These are settled-host diagnostics, without
  complete runtime owners, an atomic cut or checkpoint continuation acceptance.
- Source audit distinguishes existing CPU-managed-stream/FASED/generic hooks
  needing CPU-specific validation from missing run-loop, TSI/FESVR coroutine,
  UART, blockdev, four trace-sink and heartbeat adapters. Native exact Rocket
  preflight/save/restore requests reject explicitly, publishing no partial
  image. Fresh current-source Level-2 discovery still rejects the ChipTop
  block-device clock alias and emits no partial semantic manifest/clean RTL.
  Multi-clock/reset/state lowering, fresh restores, full boundary replay and
  CPU malformed/incompatible/incomplete-image/semantic-fault tests remain.
- Native external-adapter microtest passes: real nondefault capture, fresh VCS
  with conflicting startup plusargs, all 33 bits read back at zero edges, four
  diagnostic boundaries, actual storage corruption first differing at boundary
  0 with exit 1. The initial `$fatal`/zero-exit diagnostic is preserved; the
  final check uses the existing native DPI failure function.
- All 16 Scala inventory tests, 219 Python tests, fresh full M2/M3 VCS metasim
  and ordinary RTL regressions, eight FCFS Make/four generator guards pass.
  Diagnostics and executable commands remain under `runs/m11-iteration83/`.
  `selected-evidence.json`, `verify-evidence.py`, `summary.json`,
  `verification-commands.json` and `artifact-manifest.json` recover the exact
  commands, complete native artifact paths and current-source audits.
- Published existing controller checkpoints FireSim
  `311ad96e583140632d3ab96f0758de79c075dff5`, then Chipyard
  `a12ae334cf6dad1fbb29b4cb7a2d69952efc2dd3`; remote tips independently confirmed.
  No staging or local commits; the controller owns its next checkpoint.

Iteration 82 (October 13):

- Read current read-only plan priorities, relevant semantic/simulator sections,
  previous verification, progress and publication instructions before editing.
  Exact recipe command generation records YAML/source hashes and manager-relative
  Makefrag resolution. Native Rocket elaboration includes all four tiles, six
  ChipTop clock inputs and async reset; no FPGA bitstream build.
- Added a self-checking RV64IMA/Zicsr workload requiring all four harts to check
  64 KiB each across four phases. Spike passes the actual ELF; all four actual
  memory-corruption ELFs return the expected hart failure codes. Workload hashes
  and commands are under `runs/m11-iteration82/workload/`. Native full-16-GiB
  VCS baseline passes at 3,329,794 target cycles. Independent actual retired-store
  decoding verifies phases 1/2/3/4, completion 1 and failure 0 on every hart,
  plus the real HTIF PASS store. This is workload evidence, not CPU checkpoint
  continuation/readback/replay acceptance.
- Complete generated inventory rejects an actual unadapted `plusarg_reader`
  inside Rocket's PlusArgTimeout. Independent pre-FAME ChipTop inventory rejects
  `FireSim.chiptop0.system.bdev_clock`. The actual registry contains a CPU stream,
  one functional-memory channel, four TracerV drivers, TSI/FESVR, UART, blockdev
  and added heartbeat, beyond the FCFS profile. Both complete CPU adapters,
  captured active cuts, fresh restores and negative images remain required.
- Fixed stale sbt assembly destination reuse when changing BUILD_DIR; output is
  reassembled into the requested directory and checked nonempty. Full isolated
  M2/M3 native VCS metasim/ordinary RTL regressions pass, including 22-word
  readback, first divergence C=29 and rejection checks. All 218 Python tests and
  eight FCFS Make/four generator guards pass. The exact Rocket build separately
  rejects the FCFS profile without changing baseline bytes. The observed empty
  reused M2 JAR is repaired from the isolated native-validated JAR. Initial
  cache/include-path/runtime diagnostics are preserved separately; no missing
  dependency is claimed. Final recovery includes `summary.json`,
  `verification-commands.json`, `artifact-manifest.json` and `verify-evidence.py`.
- Published existing controller checkpoints FireSim
  `5d9be59f8898ee9e93241126ef94e85924d080a0`, then Chipyard
  `87627ac6d0b7a8dd772ff903b2fa708ae1ada550`; remote tips independently confirmed.
  Local tracking-ref writes failed on the read-only filesystem, with exact logs
  in `runs/m11-iteration82/github-publication.json`. Plans/environment files,
  indexes and heads remain unchanged; no staging or local commits.

Previous milestone: M10-production-dut-formal-map, iteration 81. Ready for the actual FCFS production DUT: independently audited complete map, fresh full-state gate VCS restore/replay, separate fresh ordinary RTL/waveform audit, first-divergence mapped corruption and all rejection checks. The corrected ready report includes an explicitly executed native VCS verification command. Completed M6/M7/M8/M9 progress remains preserved; no process ASIC, FPGA or power validation.

Iteration 81 (October 12):

- The previous ready report was rejected because the submitted verification list omitted a VCS command. All twelve fresh native production gate commands and three separate ordinary RTL build/replay/conversion commands pass with their expected statuses. Gate VCS initializes/readbacks all 13,509,222 words / 102,992,412 bits at zero edges and matches all 250,185 actual trace cycles / 8,506,290 outputs / 12,008,880 boundary values. Mapped corruption first diverges at C=524453 without taking its edge. All nine full-state atomic loader rejections, four actual predicate faults and incomplete-map rejection pass. No native summary recovery is needed. Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md), with diagnostic logs under `runs/m10-iteration81/`.
- Independent fresh ordinary waveform audit verifies all 13,503,308 semantic words at zero edges, every recorded boundary and all 250,185 edges. Final acceptance independently audits current complete native CAD/map evidence, exact build bindings and all new gate/ordinary/metasim observations. All 215 Python tests pass; retained iteration-80 M2/M3 results are rechecked, with no new metasim/synthesis/Jasper execution claimed. `runs/m10-iteration81/{summary.json,evidence-selection.json,verification-commands.json,artifact-manifest.json}` preserve ready acceptance and exact full-path recovery. The submitted verification list includes the native gate `simv` command with both environments and `vcs-env.sh` sourced LAST, and the actual controller's report guards are checked before submission.
- Published existing controller checkpoints FireSim `6caedae3e9d3e066781eaedccf3a09ff81d87216`, then Chipyard `8812b6ae21437365a58283d130da9dfbfe74ed9f`; independently confirmed both remote tips. Local tracking-ref writes emit read-only-filesystem diagnostics, preserved in `runs/m10-iteration81/github-publication.json`. No staging, local commits, protected plan/PDF or conda edits. The controller owns its next checkpoint/publication.

Iteration 80 (October 12):

- Added independently audited production span translation and a complete streaming VCS gate harness, using the current native proof map and all 130 checkpoint predicates. All 7,457 storage spans / 201 memories are covered; unsupported or incomplete state rejects. The fixture loader remains separate. Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md).
- Fresh production gate VCS loads/readbacks all 13,509,222 words at zero edges, matches 250,185 cycles / 8,506,290 outputs / 12,008,880 boundary values against the actual metasim trace and fresh ordinary RTL, and ends at C=774638. A fresh mapped AR queue bit corruption first changes QoS at C=524453 with zero edges, without acknowledging the divergent boundary. The full fresh ordinary waveform audit also verifies all 13,503,308 semantic words and every boundary/edge. All nine full-DUT native atomic loader rejections pass, reading back every physical word before and after rejection. Four decoded actual predicate faults reject; an actual incomplete map rejects before publishing loader files.
- All 215 Python tests and both complete M2/M3 VCS metasim/ordinary RTL regressions pass. Initial VCS temporary-directory collisions, the initial SystemVerilog array-type diagnostic and a post-test summary path-variable collision remain preserved. The report-only fix has three regressions; independent recovery rechecks all twelve completed native commands, exact bound inputs, every sampled value and all rejection artifacts. No new native replay is claimed by recovery. Current proof/model/map identities are independently revalidated; no new synthesis/Jasper engine execution or weakened test scope. `runs/m10-iteration80/{summary.json,evidence-selection.json,verification-commands.json,artifact-manifest.json}` record ready acceptance, exact commands and full-path/hash recovery.
- Ordinary pushes publish FireSim `1d884e5cfda3f11accd72dd0d84f59a18ac42e32`, then Chipyard `1d2a1e21f1344285a5433b3f9ca9bef265b1e87b`; independent remote-tip checks confirm both. Local tracking-ref updates emit read-only-filesystem diagnostics, recorded with exact logs in `runs/m10-iteration80/github-publication.json`. The controller owns new staging/commits and its next publication. Protected inputs/index/heads and FireSim worktree remain unchanged. No conda edits. Level-1 remains independent; power characterization is not a dependency for this functional milestone.

Iteration 79 (October 12):

- Read the relevant read-only plans, progress/publication instructions, M6/M7/M8/M9/M10 recovery, previous verification and preserved root-paper matching/loading/replay extracts before editing. Protected-input/staging/FireSim baselines are under `runs/m10-iteration79/`; the existing dirty agent plan is preserved.
- Added a complete production map exporter composing the retained native original equality, register/predicate induction, independent read closure and universal memory-word theorems. Explicitly classifies all 7,256 mapped / 130 preserved-predicate / 875 irrelevant register bits and maps every word/bit in all 201 arrays. The independent auditor reconstructs every relationship and exact build dependency without importing the exporter. Both final audits pass 40 rejection checks each (39 altered actual maps and explicit unsupported-loader rejection), with positive CAD bytes preserved. The complete map format remains disabled in the flat/fixture loader pending a separately audited production translator and fresh gate process. Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md).
- All 207 Python tests, both complete fresh M2/M3 metasim/ordinary-RTL regressions and the complete actual metasim checkpoint/four predicate corruption checks pass. Twelve copied actual native CAD faults reject after rebinding component/map paths and recomputing every changed hash: shared read words, restricted watched addresses, failed/missing assertions, vacuous premises and missing engine completions in both original and gate memory proofs. Positive bytes remain unchanged. All 13 retained verification scopes pass: synthesis/model, register, memory, queue, hierarchy, both complete production waveforms (13,503,308 zero-edge words / 250,185 boundaries / 12,008,880 input/output values each), both memory-composition audits and both original-composition audits (33 rejection checks each). Canonical map comparison rejects boolean bit indices and floating-point counts. Exact report selections, argv, protected-input checks and full-path/hash recovery are under `runs/m10-iteration79/{evidence-selection.json,verification-commands.json,summary.json,artifact-manifest.json}`. No new CAD-engine execution, synthesis or production gate acceptance is claimed.
- Ordinary FireSim publication rejects as non-fast-forward. Pending FireSim `cecf8deb01fd9fbc6bdb517edcce244da2d5d4e3`, Chipyard `9861414b6db0266b1556ce3ce6a6942f5565baf0` and exact remote tips are in `runs/m10-iteration79/github-publication.json`; Chipyard awaits FireSim publication. No force push, staging, commit, reset, cleaning or protected-input edits. Next: actual production gate translation, zero-edge full readback, recorded full trace replay and first-divergence mapped-state corruption. No required CAD dependency is missing.

Iteration 78 (October 12):

- Read the relevant read-only plans, progress/publication instructions, M6/M7/M8/M9/M10 recovery and preserved root-paper matching/loading/replay extracts before editing. The protected-input/staging/FireSim baseline is under `runs/m10-iteration78/`; the existing dirty agent plan remains preserved.
- Added original production RTL/architecture composition retaining all 1,342 semantic registers, including every later optimized bit. Fresh installed Jasper proves 836 independent-read closure assertions / 1,070 covers and 3,017 register/port/universal-word assertions / 20,345 covers. One native unreachable upstream-opcode exploratory cover is preserved explicitly; every assertion precondition is covered. Five complete actual production native fault jobs reject. No assumptions/reset initialization/blackboxing or gate-load authorization. Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md).
- All 199 Python tests, both complete fresh M2/M3 VCS metasim/ordinary RTL regressions, complete actual metasim checkpoint decoding/four predicate faults, and retained synthesis/register/memory/queue audits pass. The independent auditor separately compares the complete actual original hierarchy/scalar logic/storage with the generated proof cut. Both full independent original-component audits pass, each rejecting 27 actual certificate/CAD mutations, revalidating all five native faults and rejecting incomplete gate loading (33 rejection checks). Positive CAD bytes remain unchanged. All 11 retained/regression commands pass, including both full production waveform audits (13,503,308 zero-edge words / 250,185 boundaries / 12,008,880 input/output values each) and both complete retained architecture/netlist memory-composition audits (31 rejection checks each, with all 130 native exploratory unreachable covers unchanged). No new production gate process is claimed. Immutable selected reports and exact argv are in `runs/m10-iteration78/{evidence-selection.json,verification-commands.json}`; finalization, protection and full-path/hash catalog are finalized under that run root. Initial setup/parser diagnostics remain separate from the selected successful native proof.
- Ordinary FireSim publication rejects as non-fast-forward. Pending FireSim `d19dd6601848d7857e2c713cc7ec8882d762a678`, Chipyard `60e8b8bb21650fcebd873e67cda65390e52d71dd` and exact remote tips are in `runs/m10-iteration78/github-publication.json`; Chipyard awaits FireSim publication. No force push, staging, commit, reset, cleaning or protected-input edits. Next: complete composed map export/independent audit, then fresh actual gate zero-edge readback/full trace replay/first-divergence corruption. No required CAD dependency is missing.

Iteration 77 (October 12):

- Read relevant read-only plans, progress/publication instructions, M6/M7/M8/M9/M10 recovery, previous verification and preserved root-paper matching/loading/replay extracts before editing. Protected input/staging/FireSim baselines remain under `runs/m10-iteration77/`; the existing dirty agent plan is preserved.
- Added build-bound complete production memory composition. Fresh installed Jasper proves 836 read-address/clock assertions / 1,070 covers with independently quantified words at every read port, preventing circular array-read premises. The complete word job proves 2,479 assertions / 19,807 covers, retaining every old result and all 130 unreachable exploratory covers. Every actual physical array has an unconstrained watched address and full-word next-state theorem. Audited continuous clock aliases reject gated/derived clocks. Conditional architecture/netlist memory induction is proven; original composition and gate loading remain explicit separate obligations. Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md).
- Both complete independent composition audits pass. Each rejects 26 actual certificate/CAD mutations, revalidates all four complete native negative scopes, rejects incomplete gate loading and preserves every positive CAD byte. All 191 Python tests and both fresh complete M2/M3 VCS metasim/ordinary RTL regressions pass. Actual complete metasim checkpoint checks all 1,543 records / 13,503,308 words at pre-edge C=524453 and rejects four separately encoded predicate faults. Complete synthesis/model binding, prior 17 memory theorems / 178 mutations, queue proofs / eight negatives / 24 mutations, hierarchy contexts / six negatives / 45 mutations and register proofs / eight negatives / 27 mutations pass fresh audits. Both retained full production RTL waveforms pass fresh conversions/audits of all 13,503,308 zero-edge words, 250,185 boundaries and 12,008,880 input/output values per process. No new production gate run is claimed. Exact selected proofs/audits and argv are in `runs/m10-iteration77/{evidence-selection.json,verification-commands.json}`.
- Ordinary FireSim publication rejects as non-fast-forward. Pending FireSim `3c3b7e194ec97f87ccf92bf7227515e768ffe946`, Chipyard `3d277821eec60c4b3ce767ea2548a24cf4e9d6c1` and exact remote tips are in `runs/m10-iteration77/github-publication.json`; Chipyard awaits FireSim publication. No force push, staging, local commit, reset, history cleanup or protected-input edits. Next: compose original-to-architecture relations, independently export/audit the complete map, then actual gate zero-edge readback/full trace replay/first-divergence mapped-state corruption. No required CAD dependency is missing.

Iteration 76 (October 12):

- Read relevant read-only plans, progress/publication instructions, M6/M7/M8/M9/M10 recovery, prior verification and preserved root-paper matching/loading/replay extracts before editing. Protected plan/PDF/conda inputs and staging/FireSim baselines remain under `runs/m10-iteration76/`; the pre-existing dirty agent plan is preserved.
- Added a build-bound conditional optimized-state certificate and independent auditor. Fresh complete production Jasper proves 2,278 assertions / 18,802 covers, all 7,256 physical register transitions, all 201 memory write enables and all 35 top outputs. Every optimized bit is classified: 130 independently preserved predicates and 875 bits universally irrelevant to this relation, conditional on equal memory read words. Both values of every free bit have native covers; covers alone never authorize irrelevance. All old obligations/pending covers remain unchanged. Original/memory composition and gate loading remain explicitly unproven. Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md).
- Two complete independent optimized audits each reject all 23 actual artifact mutations plus the incomplete gate-load attempt; two complete register audits each reject all 27 mutations and revalidate all eight retained negative CAD scopes. No new negative CAD execution is claimed. The initial optimized audits' missing simulation-root argument is corrected; a regression covers it, both complete retries pass and failed logs/artifacts remain diagnostic. All 184 Python tests and both fresh complete M2/M3 VCS metasim/ordinary RTL regressions pass. Complete actual metasim checkpoint decoding checks all 1,543 records / 13,503,308 words at pre-edge C=524453 and rejects four actual separately encoded predicate faults. These are semantic checks, not mapped gate corruption acceptance.
- Complete synthesis/model binding, all 17 prior memory theorems / 178 mutations, queue proofs / eight negatives / 24 mutations and hierarchy-context proofs / six negatives / 45 mutations pass fresh audits. Both complete prior production waveforms pass fresh conversions/audits, each checking all 13,503,308 zero-edge words and 250,185 boundaries / 12,008,880 input/output values. Exact immutable selections and argv are under `runs/m10-iteration76/{evidence-selection.json,verification-commands.json}`; summary, protection and full-path/hash catalog are finalized there. No new production gate run is claimed.
- Ordinary FireSim publication rejects as non-fast-forward. Pending FireSim `3d75c8aa0365f2d1aa2fcc1b7fd30481bdba1b53`, Chipyard `460b3e94e832a8675ef1f8d8e987b08e24f9926e` and exact remote tips are in `runs/m10-iteration76/github-publication.json`; Chipyard awaits FireSim publication. No force push, staging, commit, reset, history cleanup or protected-input edits. Next: complete original/architecture/netlist memory composition with the optimized classifications, independently export/audit the complete map, then actual gate zero-edge readback/full trace replay/first-divergence mapped-state corruption. No required CAD dependency is missing.

Iteration 75 (October 12):

- Read the relevant read-only plans, progress/publication instructions, M6/M7/M8/M9/M10 recovery, previous verification and root-paper matching/loading/replay extracts before editing. Protected inputs and staging/FireSim baselines are under `runs/m10-iteration75/`; the pre-existing dirty agent plan is preserved.
- Added the complete production flight-opcode predicate adapter. The actual whole production positive Jasper job proves 2,278 assertions / 18,802 covers, including all 7,256 physical register transitions, all 201 memory write enables and all 35 top outputs. All eleven prior decrement-memory enable counterexamples are discharged by separately proven, nonvacuous preservation of 130 opcode predicates. Every old obligation and all 1,005 optimized semantic bits remain explicit; no assumptions/reset initialization/blackboxing or gate-load authorization.
- Complete actual metasim checkpoint decoding verifies all 1,543 records / 13,503,308 words at pre-edge C=524453 against every predicate. Four separately encoded actual opcode-state corruptions reject for the exact changed semantic path. These are semantic compatibility checks, not mapped gate corruption acceptance. All 175 Python tests and full fresh M2/M3 VCS metasim/ordinary RTL regressions pass. All eight full negative CAD jobs complete: seven actual counterexample scopes and one explicitly rejected vacuous predicate. Omitting the selected-flight predicate reproduces all eleven former write-enable counterexamples. Two independent audits each reject all 27 actual artifact mutations and both incomplete loader artifacts without altering positive CAD bytes. Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md).
- Fresh prior synthesis/model binding, all 17 memory theorems / 178 mutations, queue proofs / eight negatives / 24 mutations, hierarchy-context proofs / six negatives / 45 mutations and both complete prior production RTL waveforms pass full audits. Each waveform checks all 13,503,308 zero-edge words and 250,185 boundaries / 12,008,880 input/output values. No new gate run is claimed. Exact immutable selections, commands, finalization and full-path/hash recovery are under `runs/m10-iteration75/{evidence-selection.json,verification-commands.json,summary.json,artifact-manifest.json}`.
- Ordinary FireSim publication rejects as non-fast-forward; exact pending commits/remotes are in `runs/m10-iteration75/github-publication.json`. Chipyard awaits FireSim publication. No force push, staging, commit, reset, history cleanup or protected-input edits. Next: complete original/architecture/netlist memory and optimized-state composition, independently audit the full map, then run actual gate zero-edge readback/replay/first-divergence corruption. No required CAD dependency is missing.

Iteration 74 (October 12):

- Read relevant read-only plans, progress/publication instructions, M6/M7/M8/M9/M10 recovery, previous verification and preserved root-paper matching/loading/replay extracts before editing. Protected-input/staging/FireSim baselines are under `runs/m10-iteration74/`; the dirty agent plan is preserved.
- Added whole production flattened-register and concrete memory-port obligations, using the exact original architecture and real Genus netlist/models. Jasper proves all 7,256 physical register-bit transitions and all 35 top output ports: 2,137 assertions / 18,671 covers. Eleven real decrement-memory write-enable counterexamples, every optimized bit and the unreachable omitted-opcode independence cover remain explicit. No assumptions/reset initialization/blackboxing and no gate-map authorization.
- A supplementary explicit opcode predicate proves preservation (2,138 assertions / 18,673 covers), but retains all eleven counterexamples. Complete actual metasim checkpoint decoding verifies all 1,543 records / 13,503,308 words at C=524453 before checking that predicate; actual semantic opcode corruption rejects. This is not gate corruption acceptance. Conditional relationship catalogs and complete negative/audit recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md).
- Both whole production positive jobs and all nine negative CAD jobs complete through the shared-budget Jasper launcher. Eight gate/port faults produce actual counterexamples; the wrong opcode predicate has unreachable preconditions and explicitly rejects as vacuous. Four independent audits (two per positive scope) each reject all 22 actual artifact mutations and both incomplete artifacts before gate loading, preserving every original CAD byte. Initial verifier failures remain diagnostic; recovery revalidates all retained scopes without altering CAD evidence.
- All 173 Python tests and fresh complete M2/M3 VCS metasim/ordinary RTL regressions pass. Prior synthesis/model binding, 17 memory theorems / 178 mutations, queue proofs / eight negatives / 24 mutations and hierarchy-context proofs / six negatives / 45 mutations pass fresh audits. Both full prior production RTL waveforms pass fresh conversions/audits of all 13,503,308 zero-edge words and 250,185 boundaries / 12,008,880 input/output values per process. Exact commands, immutable selections, finalization/protection and full-path/hash recovery are in `runs/m10-iteration74/{summary.json,verification-commands.json,artifact-manifest.json}`. Next: discharge eleven decrement-memory enable counterexamples and complete optimized-state/original/architecture/netlist memory composition before full-map audit and gate acceptance. No new production gate run is claimed.
- The ordinary FireSim push rejects as non-fast-forward. Exact pending FireSim `8df02579c7853497b8ed0757022ebba18d8464d4`, Chipyard `a02291bd38af13db915d2e7d7ee9f014e9539c9f` and remote tips are in `runs/m10-iteration74/github-publication.json`; Chipyard awaits FireSim publication. No force push, staging, commit, reset, history cleanup or protected-input edits. No required CAD dependency is missing.

Iteration 73 (October 12):

- Read the relevant read-only plans, M6/M7/M8/M9/M10 recovery, publication instructions, prior verification and root-paper matching/loading/replay extracts before editing. Protected plan/PDF/conda hashes and staging/FireSim baselines are under `runs/m10-iteration73/`; the pre-existing dirty agent plan is preserved.
- Added production context adapters for all 304 queue output counterexamples. All parent register transitions/child inputs are checked; two real parent echo-size output counterexamples remain explicit because bit 3 propagates through the top. The complete original-DUT hierarchy proof then proves 2,414 assertions / 5,404 covers, covering every one of the 8,261 captured register bits, every concrete memory input port and every top output under a complete current register relation. Universal common array read-word cuts retain all 201 memories / 102,985,156 contents bits as separate memory/composition obligations. All 144 supplemental live size-bit equalities prove while every original raw queue assertion/cover and all 304 counterexamples remain recorded. No assumptions/reset initialization/array blackboxing; no gate-map authorization.
- Nine installed Jasper jobs complete through the shared-budget launcher: three positive scopes and six real false-lemma counterexamples, including an actual whole-DUT `done` dependency on a propagated size bit. All 168 Python tests and fresh complete M2/M3 VCS metasim/ordinary RTL regressions pass. Prior 17 memory theorems / 178 actual mutations, retained queue proofs / eight negatives / 24 mutations and complete synthesis/model binding pass fresh re-audits. Both full prior production RTL waveforms pass fresh conversions/audits: all 13,503,308 zero-edge words, 201 memories / 50 boundary ports and 250,185 boundaries / 12,008,880 input/output values per process.
- Two independent context audits each pass six unchanged controls, reject all 45 actual artifact mutations, re-audit all six fresh negatives and reject incomplete map artifacts before gate loading, preserving every original CAD byte. Final proof/audit selections, exact argv and full-path/hash recovery are under `runs/m10-iteration73/` (`summary.json`, `verification-commands.json`, `artifact-manifest.json`, `protection-after.json`). Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md). Next: complete original/architecture/netlist register, optimized-state (including the 1,005-bit register count difference), memory and boundary composition; independently audit the full map before fresh gate zero-edge readback, actual trace replay and first-divergence mapped-state corruption. No required CAD dependency is missing.
- The ordinary FireSim publication push again rejects as non-fast-forward. Pending FireSim `37c468df99ea28725f12ff5f02649884245ea339` and Chipyard `6711aaa3dfc4db97efafbcb2aae2320ee5cda59f`, plus exact remote tips, are recorded in `github-publication.json`; Chipyard awaits FireSim publication. No force push, plan/PDF/conda edit, staging, commit, reset, history cleanup, FPGA or power claim.

Iteration 72 recovery (October 12):

- The retained October 11 finalizer actually failed: its independent pair bound `invocation-6oqtswfn`, while verification had changed the latest proof pointer to `invocation-mmcsiddt`. Prior claims of final summary/catalog publication were premature. Both original failure logs remain diagnostic.
- Added validated proof recovery from the explicit pair, independent of mutable latest-run pointers. The full finalizer now passes against that real retry state without changing either proof or pointer. All 161 Python tests pass; two fresh independent queue audits each reject all 24 actual mutations, re-audit eight prior negatives and preserve all original proof bytes. Every prior proof, counterexample, regression, waveform and protection obligation remains required. The standalone full-path artifact/hash/completeness/protection audit passes; its real stale-file rejection is retained, with the catalog regenerated for final documentation/report bytes.
- Corrected commands/evidence are under `runs/m10-iteration72/recovery-finalization/`; recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md). The FireSim publication push was rejected as non-fast-forward; exact pending FireSim/Chipyard commit IDs and remote tips are recorded in `github-publication.json`. Chipyard awaits FireSim publication. History, protected inputs and staging remain preserved. No required CAD dependency is missing; no new Jasper or gate acceptance claim.

Iteration 72 (October 11):

- Read relevant read-only plans, M6/M7/M8/M9/M10 recovery notes, progress, failed verification and root-paper matching/loading/replay extracts before editing. Protected plan/PDF/conda-request hashes and staging/FireSim baselines are under `runs/m10-iteration72/`; the pre-existing dirty agent plan remains unchanged.
- Fixed the prior finalizer's retry failure: verification added a third valid independent queue audit, but the old script required exactly two directories. New repository evidence selection binds two explicit nonempty absolute report files, their hashes, distinct invocation identities and the complete unchanged proof-file set. Duplicate/aliased/missing/changed/incomplete/forged artifacts reject; retries remain retained diagnostics. No proof obligation or test scope is reduced.
- Added a repository finalizer preserving all previous checks and additionally comparing selected independent audits, exact boundary data, per-invocation mutation artifacts and fresh synthesis/model-binding bytes. All 159 Python tests, both complete fresh 24-mutation queue audits/eight prior negatives, all 17 prior memory theorems/178 actual memory mutations, complete production synthesis/model binding and full M2/M3 VCS metasim/ordinary-RTL regressions pass. Prior Jasper proofs are re-audited, not rerun. Both full prior production waveform audits pass with fresh conversions: all 13,503,308 zero-edge words, 201 memories/50 ports and 250,185 boundaries/12,008,880 input/output values per process. The selector also passes against the exact prior three-real-audit failure state, with all reports retained. Final publication failed on the later proof-pointer mismatch corrected in the recovery above.
- Original argv/selection/diagnostics: `runs/m10-iteration72/{verification-commands.json,audit-pair.json,retry-reproduction.json,finalize-evidence.log}`. Use the recovery subdirectory above for corrected final evidence. Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md). Next: discharge all 304 local output counterexamples and complete top register/optimized-state/memory/boundary composition before exporting/auditing a complete map and fresh gate zero-edge readback/replay/first-divergence corruption. No required external dependency is missing. Level 1 remains independent; no plan/PDF/conda edits, staging, commits, resets, cleaning, FPGA or power claims.

Iteration 71 (October 11):

- Read the relevant read-only plans, M6/M7/M8/M9/M10 recovery notes, progress, prior verification and root-paper matching/loading/replay extracts before editing. Plans/PDF hashes and staging/FireSim baselines are under `runs/m10-iteration71/`; the previously dirty agent plan remains unchanged. Report concrete nonempty artifact files, not run directories, to address previous feedback.
- Added production queue proof/reconstruction and independent audit adapters for all 165 retained real Genus queue modules. Jasper proves every one of their 1,135 register-bit transitions, all 660 memory-port equalities and 917 output equalities: 2,712 assertions proven and 6,276 covers, zero assumptions/reset initialization/blackboxing. All 304 failed output assertions remain explicit counterexamples (160 dequeue-valid, 128 echo-size, 16 TL-size); no output obligation is removed or waived. Undriven dequeue-valid declarations are diagnostic only; global irrelevance remains unproven.
- Exact original/architecture/raw and selected netlists, concrete models, synthesis inputs/log, StateIDs, boundary manifest and all 7,457 physical storage spans are bound. The complete 1,543-entry semantic/physical/boundary composition catalog remains globally unproven. All eight fresh wrong-polarity/missing-register/wrong-enable/wrong-read-address challenges produce real counterexamples. Two independent audit passes each reject all 24 actual artifact mutations, audit all eight negatives and reject local proof artifacts before checkpoint decoding; original proof bytes are preserved.
- All 151 Python tests and complete M2/M3 VCS metasim/ordinary-RTL regressions pass. The first M2 VCS frontend `branch_bb == 0` assertion is retained; a fresh complete retry passes. Complete production synthesis/model binding, all 17 prior memory theorems/all 178 memory artifact rejections, and both full prior production RTL waveforms pass fresh audits. Final queue proof: `queue-proofs-final/invocation-6oqtswfn/positive/`; selections, exact commands/full-path catalogs and protection checks: `runs/m10-iteration71/{summary.json,verification-commands.json,artifact-manifest.json}`. Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md). Next: complete top register/optimized-state/memory/boundary composition and discharge the 304 local output counterexamples before exporting/auditing a complete map and running fresh gate readback/replay/first-divergence corruption. No required external dependency is missing. Level 1 remains independent; no plan/PDF/conda edits, staging, commits, resets, cleaning, FPGA or power claims.

Iteration 70 (October 11):

- Read the relevant read-only plans, M6/M7/M8/M9/M10 recovery notes, progress, prior verification and root-paper matching/loading/replay extracts before editing. Protected-input/staging/status baselines are under `runs/m10-iteration70/`; the previously dirty agent plan remains unchanged.
- Added production memory proof/reconstruction and independent audit adapters. All 201 original memory fragments/StateIDs, concrete models and port expressions are bound; a universal arbitrary-address word projection covers all 102,985,156 contents bits / 13,501,966 words. Jasper proves word transitions and each read port without assumptions, reset initialization or blackboxed arrays. Outside the selected valid word, reads stay independently unconstrained, including depth-one invalid addresses. This is a local grammar/projection theorem; surrounding registers and synthesized-netlist composition remain obligations. Candidates stay unproven and gate loading remains unauthorized.
- Final installed Jasper 2025.03 run passes all 17 production shapes: 41 assertions/1,522 covers. All 51 fresh wrong-enable/write-address/read-address trials produce real counterexamples. Two complete independent audit passes each pass two unchanged controls and reject all 178 actual artifact mutations, preserving positive proof bytes. Diagnostic automatic array blackboxing/failed assertion, interrupted array elaboration, preliminary projection and initial unit-test comment-match failure remain under runs; every final proof/counterexample/audit scope reran completely.
- All 147 Python tests and complete M2/M3 VCS metasim/ordinary RTL regressions pass. Repeated complete production synthesis/model-binding and both full prior production waveform audits pass. Final proof: `memory-proofs-final/invocation-ono1zw73/`; selections, exact commands/full-path catalogs and protection checks: `runs/m10-iteration70/{summary.json,verification-commands.json,artifact-manifest.json}`. Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md). Next: complete 8,261 semantic/7,256 physical register-bit proofs, optimized-state predicates and netlist/memory/boundary composition, then audit the complete map before fresh gate readback/replay/first-divergence corruption. No required external dependency is missing. Level 1 remains independent; no plan/PDF/conda edits, staging, commits, resets, cleaning, publication, FPGA or power claims.

Iteration 69 (October 11):

- Read the relevant read-only plan sections, M6/M7/M8/M9 recovery notes, progress, previous verification and root-paper matching/loading/replay extracts before editing. Initial protected hashes/staging/status are under `runs/m10-iteration69/`; the dirty agent plan remains unchanged.
- Added production architecture extraction and reconstruction audit for the actual `AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config` pre-FAME DUT: all 1,543 StateIDs / 102,993,417 bits / 13,503,308 words, including every pipeline/port register and 201 complete RAMs. Seventeen concrete memory shapes preserve asynchronous reads and exact target-clock writes. Unsupported guards/accesses/clocks/shapes/hidden state and forged proof status reject. All candidates remain explicitly unproven; no existing M8 map check was relaxed.
- Complete-DUT retiming-disabled Genus synthesis and independent repeated inventory/model-binding audits pass: 62,158 cells/macros, all 201 RAMs and 7,256 physical register bits / 102,992,412 physical bits. The 1,005-register-bit difference remains a formal obligation. Selected compilation definitions retain every emitted logic byte, omit only checked empty RAM interfaces and bind both raw/selected netlist plus concrete models. Fresh complete gate VCS compilation passes; no unproven gate state is loaded.
- Two fresh ordinary original/extracted-memory RTL VCS processes restore/read back all 13,503,308 words at zero edges and match all 250,185 captured boundaries / 8,506,290 outputs each, END C=774638. Both full waveform audits pass twice and independently check every initial word, all 201 memories/50 boundary ports and 12,008,880 sampled input/output values per process with exact cycle/edge timing. Repeated audits use fresh directories and preserve prior evidence. Final selections, exact commands and full-path/hash catalogs are under `runs/m10-iteration69/` (`summary.json`, `verification-commands.json`, `artifact-manifest.json`, `synthesis-model-audit/selection.json`, `waveform-audit/selection.json`).
- All 143 Python tests and complete M2/M3 VCS metasim/ordinary-RTL regressions pass. Diagnostic failures are retained; no scope was reduced. Recovery: [m10-production-dut-formal-map.md](m10-production-dut-formal-map.md). Next: complete original-to-netlist formal state proofs, independent map audit and fresh gate VCS complete readback/replay/first-divergence corruption. No required external dependency is missing. Level 1 remains independent; no plan/PDF/conda edits, staging, commits, resets, cleaning, publication, FPGA or power claims.

Iteration 68 (October 10):

- Read the read-only plans' formal/replay/activity requirements, previous progress/verification and the root papers' matching/loading/replay sections before edits. Protected input hashes and initial staging/FireSim status are under `runs/m9-iteration68/`; the dirty agent plan is preserved. Loop M9 corresponds to agent Phase 11/M10; numbering correction remains only in checkpointing docs.
- Added `gate_replay.py`: current complete formal-map revalidation, full original/netlist boundary coverage, independently bound semantic checkpoint/trace, complete deposits and zero-edge readback, finite pre-edge output checks, fresh netlist/model-only VCS harness and native SAIF over the settled replay window. Read-only bound probes corroborate SRAM activity in VCD without modifying the proven netlist/models. Native SAIF directly monitors physical storage, including arrays.
- Added `gate_activity.py` and reusable gate verification/audit modules: complete mapped-storage SAIF/VCD dwell/transition checks, exact clock edges/window, continuous/restored output and all native-SAIF signal equality, fresh ordinary RTL control, actual storage faults and nine generated-activity mutations per profile. Faults flip all physical copies of one semantic bit. Initial dump timing, unpacked-memory VCD visibility and single-clone fault diagnostics are retained under runs.
- All 50 profiles and final artifact audits pass: 100 fresh gate builds/processes and 50 fresh ordinary RTL replays; each restores C=17, compares 79 boundaries/237 outputs through C=95 and ends C=96. All 100 native SAIF files cover exactly 237 ns; every mapped bit agrees with same-run VCD, and every native-SAIF signal agrees with continuous execution. SRAM profiles cover all 35 storage bits, including 16 contents bits through read-only VCD witnesses, and record 875 storage transitions each. All 50 actual storage faults, 450 generated-activity mutations and 400 provenance mutations reject; 50 unchanged audit controls pass with original bytes preserved. Current preparation revalidates every proof/input and reproduces the exact compiled harness/deposits. Full-path selections and command/artifact catalogs are under `runs/m9-iteration68/` (`matrix-complete/matrix-results.json`, `verification-commands-final.json`, `summary.json`, `artifact-manifest.json`). Initial failed diagnostics are retained; no check was skipped or scope reduced.
- All 131 Python tests and complete M2/M3 VCS metasim/ordinary RTL regressions pass. M2 retains five cuts/all 22 words/C=29 divergence/four loader failures; M3 retains 717 transport edges, 23 advances, six captures, 242 boundary/five semantic replay samples/eight invalid reads. Gate acceptance samples originate in ordinary RTL VCS; production metasim DUTs still need their own complete formal maps. Recovery: [m9-gate-level-replay.md](m9-gate-level-replay.md). Joules is installed, but the proven CK* netlists' artificial libraries lack matching cell power/leakage data; conditional power analysis is not run. Protected inputs, staging, FireSim status and whitespace checks pass. Level 1 remains independent. No physical FPGA, process ASIC or power claims; no plan/PDF/conda edits, staging, commits, resets or cleaning.

Iteration 67 (October 10):

- Read relevant formal/replay sections of both read-only plans, progress/previous verification and hash-verified root-paper extracts before editing. Protected input hashes/staging baseline are under `runs/m8-iteration67/`; dirty agent plan preserved.
- Added version-2 audited cell shapes and version-8 maps covering all SRAM words, buffered write address/data/enable and registered read state. Full relational proof is mandatory; unsupported/hidden/initialized state rejects. Translation assembles complete words with bit membership and merged-source checks before deposits. Synthesis hashes original RTL, explicit macro architecture and stub; Jasper/VCS use the complete concrete model.
- Both new Genus/Jasper/VCS profiles and independent audits pass: 35 physical bits, 27 in macro, 16 deposited words, 38 unbounded assertions/109 covers. Pending-write C=17 restore/readback at zero edges; all 79 boundaries/237 outputs match, ending C=96. Uninterrupted gate and fresh ordinary RTL replay pass. Five actual SRAM state faults, four fresh counterexample proofs and six atomic loader failures pass per polarity. Two unchanged SRAM audit controls and 64 actual artifact mutation rejections pass twice after map hashes are recomputed.
- All 50 fresh CAD/VCS profiles/audits, all 122 Python tests and full M2/M3 VCS metasim/ordinary RTL regressions pass. M2 retains five cuts/all 22 words/C=29 divergence/four loader failures; M3 retains 717 transport edges, 23 advances, six captures, 242 boundary/five semantic replay samples/eight invalid reads. Full supplemental scope passes twice: 15 distinct unchanged controls and 333 distinct mutation rejections per pass; eight fresh missing-predicate CAD builds preserve prior proof bytes/inodes. No check skipped or scope reduced. `finalize-evidence.py` revalidates all 50 maps/current input bytes and metrics. Full-path selections/commands/catalog: `runs/m8-iteration67/matrix-results.json`, `sram-matrix-results.json`, `all-verification-commands.json`, `summary.json`, `artifact-manifest.json`. Protected inputs, staging, FireSim worktree and whitespace checks pass. Recovery: [m8-formal-state-map.md](m8-formal-state-map.md). Explicit artificial macro architecture; no automatic SRAM inference, production process macro, physical FPGA or power claims. Level 1 remains independent. No plan/PDF/conda edits, staging, commits, resets or cleaning.

Iteration 66 (October 10):

- Read both read-only plans' formal/replay sections, previous progress/verification and hash-verified root-paper matching/replay extracts before edits. Protected input hashes and initial staging/status are under `runs/m8-iteration66/`; the dirty agent plan remains unchanged.
- Added version-3 relational candidates and version-7 build-bound maps composing observable constants with native merging, duplication, unread optimization, either polarity and indexed reordering. Exact independent Jasper predicates establish constant bits/values after one arbitrary target edge; complete relation induction preserves those values and every retained relationship/output. All prior proof, inventory, hash and nonvacuity requirements remain. C=0, conflicting values, missing/mismatched predicates and unsupported state reject before deposits.
- Four new real Genus/Jasper/VCS profiles/audits pass: 36 semantic bits, 28 physical bits deposited/read back at zero edges, 32 relationships, 39 assertions/104 covers plus four independent constant assertions/five covers. All 79 boundaries/237 outputs match at C=17..95, ending C=96. Nine fresh counterexample proofs per profile include false/conditional constants and current/future unread influence. A conditional design passes complete relation proof but fails independent constants; relation PASS alone still rejects. Four conflicting constant bits and the horizon reject; fresh ordinary RTL exposes the bad checkpoint at C=17 before an edge. Six atomic loader failures, merged consistency, C=29 clone/shared faults and real vacuity rejection remain covered.
- All 48 fresh CAD/VCS profiles and independent audits, all 117 Python tests and complete M2/M3 metasim/ordinary RTL regressions pass. M2 retains five cuts/all 22 words/actual C=29 divergence/four loader failures; M3 retains 717 transport edges, 23 semantic advances, six captures, 242 boundary/five semantic replay samples and eight invalid reads. Both polarities' supplemental shared-flop faults/changed-D proofs pass too.
- Full supplemental scope passed twice: 13 unchanged controls and 269 distinct actual artifact mutations reject on each pass, including 53 new constant-composition mutations per polarity. Eight additional fresh missing-predicate Genus/Formality builds preserve prior proof bytes/inodes. All four formerly unsupported constant compositions now have complete positive profiles. No check was skipped or scope reduced. `finalize-evidence.py` revalidates all 48 maps against current input bytes and complete regression metrics. Exact commands/full-path hash catalog: `runs/m8-iteration66/verification-commands.json`, `finish-repeat-commands.json`, `summary.json`, `matrix-results.json`, `artifact-manifest.json`.
- Next: complete hash-bound SRAM macro contents/pipeline/port initialization with synthesis/proof/replay. Logical RAM remains DFF storage. No required external dependency is missing. Recovery: [m8-formal-state-map.md](m8-formal-state-map.md). Level 1 remains independent. No plans/PDFs/conda edits, staging, commits, resets, cleaning or FPGA/power claims.

Iteration 65 (October 10):

- Read both read-only plans' formal/replay sections, previous progress/verification feedback and hash-verified root-paper matching/replay extracts before edits. Protected-input hashes and initial staging/status are under `runs/m8-iteration65/`; the dirty agent plan remains unchanged.
- Added audited version-2 relational candidates and version-6 maps for unread optimization with simultaneous native merging/duplication, preserving all semantic StateIDs. Eliminated bits remain outside the relation: unbounded state preservation/output equivalence must hold for arbitrary unread values/evolution. Both values of every omitted bit require real covers. Existing proof, binding and gate completeness requirements remain intact; malformed schema/state rejects explicitly.
- All four new profiles pass in both polarities with/without indexed reordering: 32 semantic bits, 28 physical bits initialized/read back at zero edges, 32 relationships/35 assertions/100 covers; 79 boundaries/237 outputs match from C=17 through END C=96. Flipping every unread checkpoint bit preserves deposits and fresh RTL replay. Each profile has seven fresh counterexample proofs, including direct output and future next-state influence; observable omitted state rejects. Existing vacuity, merged consistency, six atomic loader failures and clone/shared C=29 faults remain covered.
- All 44 fresh CAD/VCS profiles and independent audits, all 115 Python tests and full M2/M3 metasim/ordinary RTL regressions pass. M2 retains five cuts/all 22 words/actual C=29 divergence/four loader failures. M3 retains 717 transport edges, 23 semantic advances, six captures, 242 boundary/five semantic replay samples and eight invalid reads. Supplemental shared-flop faults/changed-D proofs pass in both polarities too.
- The full supplemental scope passed twice: all 11 unchanged controls and 163 distinct actual artifact mutations reject as expected, including new unread covers, proof statuses, altered checkpoints/replays and both kinds of counterexample engine evidence. Eight additional fresh missing-proof synthesis/equivalence builds preserve first-pass proof hashes/inodes. Four former unsupported unread configurations are now proven profiles; four constant compositions still reject before tools launch. No check was skipped or scope reduced. `finalize-evidence.py` validates all 44 maps against current input bytes and regression metrics. Exact commands/full-path hash catalog: `runs/m8-iteration65/verification-commands.json`, `finish-repeat-commands.json`, `summary.json`, `matrix-results.json`, `artifact-manifest.json`.
- Next: complete hash-bound SRAM macro contents/pipeline/port initialization, then relational constant predicate/horizon composition. Logical RAM remains DFF storage. No required external CAD dependency is missing. Recovery: [m8-formal-state-map.md](m8-formal-state-map.md). Level 1 remains independent. No plans/PDFs/conda edits, staging, commits, resets, cleaning or FPGA/power claims.

Iteration 64 (October 10):

- Read both read-only plans' formal/replay sections, previous progress and failing verification log, and hash-verified root-paper extracts before edits. Protected-input hashes and initial staging/status are under `runs/m8-iteration64/`; the dirty agent plan remains unchanged.
- Previous feedback was a verifier rerun failure: iteration 63's missing-proof script used fixed synthesis directories and raised `FileExistsError` on its second execution. Added the reusable `tests.verify_formal_missing_proof` module with a fresh invocation for every call, explicit synthesis flags, command logs and input hashes. No exporter, loader or proof requirement changed. Previous diagnostic scripts/artifacts remain untouched.
- The real repeat check passed: two calls in the same populated output directory produced four fresh Genus/Formality builds, both polarities rejected missing constant predicates despite global equivalence PASS, and all 56 first-call files retained their bytes and inodes. No prior proof artifacts were consumed as new evidence.
- All 40 fresh CAD/VCS profiles and independent audits, all 111 Python tests and full M2/M3 metasim/ordinary RTL regressions pass. M2 retains five cuts/all 22 words/actual C=29 divergence/four loader failures. M3 retains 717 transport edges, 23 semantic advances, six captures, 242 boundary/five semantic replay samples and eight invalid reads. Shared-flop fault/changed-D audits pass in both polarities.
- The full supplemental scope passed twice: all nine independent controls and 107 distinct actual artifact mutations, raw negative-engine audits and eight unsupported compositions still behave correctly. These passes ran eight additional fresh missing-proof synthesis/equivalence builds; all first-pass proof files retained their hashes/inodes. `finalize-evidence.py` revalidates all 40 maps against current input bytes, complete regression metrics and protected inputs. Exact commands and full-path/hash catalog: `runs/m8-iteration64/verification-commands.json`, `finish-repeat-commands.json`, `finish-repeat-summary.json`, `summary.json`, `matrix-results.json`, `artifact-manifest.json`. No test scope was reduced or check skipped. No required external CAD dependency is missing.
- Next: complete hash-bound SRAM macro initialization, including contents and pipeline/port state, with synthesis/proof/replay; extend the relational adapter to unread/constant composition. Logical RAM currently remains DFF storage. Recovery: [m8-formal-state-map.md](m8-formal-state-map.md). Level 1 remains independent. No plan/PDF/conda edits, staging, commits, resets, cleaning or FPGA/power claims.

Iteration 63 (October 10):

- Read both read-only plans' formal/replay sections, progress/previous verification and hash-verified root-paper extracts before edits. Protected-input hashes and initial staging are under `runs/m8-iteration63/`; the dirty agent plan remains unchanged.
- Added `relational_state.py`: unchanged complete original RTL/netlist in an audited Jasper miter, `reset -none`, no assumptions. Every state relation must preserve the complete relation across an edge; every output must agree under that relation. Initial map consistency is explicit and enforced by the loader. Covered antecedents, an edge cover and zero/one covers for every physical bit prevent vacuity. Exact scripts/miter, complete interfaces/inventories, raw engine results and before/after input hashes are mandatory. No previous proof requirements were relaxed.
- Four new profiles prove 32 relationships with 35 assertions/92 covers over 28 semantic/physical bits. Four shared flops retain eight original sources; four counter bits each initialize two physical copies. All 28 bits deposit/read back at zero edges from C=17; 79 boundaries/237 outputs match clean RTL and uninterrupted gate execution through END C=96. Four logical RAM words remain DFFs. Conflicting checksummed checkpoints and missing alias/copy evidence reject. Each profile has five fresh counterexample proofs, a real contradictory-relation/vacuity rejection, six atomic loader failures and clone/shared faults first differing at C=29 after 12 edges.
- All 40 CAD/VCS profiles and independent audits pass, including all 36 previous profiles; all 111 Python tests and full M2/M3 metasim/ordinary RTL VCS regressions pass. M2 retains five cuts/all 22 words/actual C=29 divergence/four loader failures. M3 retains 717 transport edges, 23 semantic advances, six captures, 242 boundary/five semantic replay samples and eight invalid reads. Old supplemental shared-flop faults/changed-D proofs pass too.
- Nine isolated audit controls pass; all 107 actual artifact mutations reject. New audits rebind hashes, validate each negative engine result and reject weakened, missing, bounded, vacuous, stale or constrained proof evidence. Two fresh equivalence-only constant builds still reject absent predicates. Eight eliminated-state relational combinations reject before tool launch. `finalize-evidence.py` revalidates all 40 maps against actual current input bytes and regression metrics. Exact argv/results/full-path catalog: `runs/m8-iteration63/verification-commands.json`, `finish-commands.json`, `summary.json`, `matrix-results.json`, `artifact-manifest.json`.
- Attempted partial Formality partitions failed and were rejected; complete Jasper induction replaced them. An initial reserved-keyword label failed; the corrected retry passed. Raw diagnostics remain under runs. No required CAD dependency is missing, and no test scope was reduced.
- Next: complete hash-bound SRAM macro initialization, including contents and pipeline/port state, with synthesis/proof/replay; extend the relational adapter to audited unread/constant composition. Proposed Jasper proof-mode correction is only in [m8-formal-state-map.md](m8-formal-state-map.md). Level 1 remains independent. No plans/PDFs/conda edits, staging, commits, resets, cleaning or FPGA/power claims.

Previous iteration 62 status: In progress: combined native merging, unread optimization and independent Jasper constant predicates now have complete validated proof/map/replay profiles. SRAM macro initialization and combined merging/duplication remain. Artificial functional cells; no process ASIC, FPGA or power validation.

Iteration 62 (October 10):

- Read both plans' relevant formal/replay sections, progress/previous verification and root-paper extracts after checking their PDF input hashes. Protected-input hashes and initial staging are under `runs/m8-iteration62/`; the dirty agent plan remains read-only.
- Added original merging/unread and merging/unread/constant fixtures and enabled both polarities and scalar reordering. The verifier and independent auditor retain complete state inventories, gate-reference orientation and side-correct unread reports. No exporter schema or proof requirements were relaxed. Two new composition tests cover unread-value independence, merged consistency, wrong proof/report sides and missing aliases.
- Eight new combined profiles pass: version-3 maps retain 32 semantic bits; version-4 constant maps retain 36. All 24 physical bits initialize/read back at zero edges from C=17, and 79 boundaries/237 outputs match through END C=96. Four shared flops retain eight original sources; all four logical RAM words remain DFFs. Conflicting merged/constant checkpoints, early constant state, missing alias/classification and wrong proof side reject.
- All 36 real CAD/VCS profiles and independent audits pass, including all 28 previous profiles. All 105 Python tests and full M2/M3 metasim/ordinary RTL regressions pass. M2 retains five cuts, all 22 words, actual C=29 divergence and four loader failures. M3 retains 717 transport edges, 23 semantic advances, six captures, 242 boundary/five semantic replay samples and eight invalid reads. Previous and new combined shared-flop/changed-D fault checks pass in both polarities.
- Seven isolated audit controls pass; all 69 actual artifact mutations reject. New combined unread report/evidence hashes are rebound to exercise semantic checks. Two fresh equivalence-only constant builds still reject absent predicates. Eight unsupported merging/duplication combinations reject before tool launch. Exact commands/results/full-path catalog: `runs/m8-iteration62/verification-commands.json`, `summary.json`, `matrix-results.json`, `artifact-manifest.json`.
- Initial diagnostic audit clones omitted Tcl/Verilog files; complete clones/retries and all final controls pass. Raw failures remain under runs. `pdftotext` is unavailable; preserved extracts were read after checking their root-PDF input hashes. No required CAD tool/library/license is missing, and no test scope was reduced.
- Next: complete hash-bound SRAM macro initialization, including contents and pipeline/port state, with synthesis/proof/replay; add a separate combined merging/duplication proof adapter. Recovery: [m8-formal-state-map.md](m8-formal-state-map.md). Level 1 remains independent. No plans/PDFs/conda edits, staging, commits, resets, cleaning or FPGA/power claims.

Iteration 61 (October 10):

- Read both plans' relevant formal/state-replay sections, progress/previous verification and both papers' preserved matching/replay extracts before edits; fresh extracts from the root PDFs are retained too. Plan/PDF hashes and initial staging are under `runs/m8-iteration61/`; the dirty agent plan remains read-only.
- Added hash-bound `constant_state.py` Jasper predicates from arbitrary initial state with `reset -none`. All original constant bits require unbounded proven assertions, covered antecedents and an edge cover; audited script/binding, before/after input hashes, machine statuses and raw engine reports must agree. Version-4 maps keep every semantic StateID. C < 1 or conflicting constant checkpoint values reject before any deposits.
- Eight new constant profiles cover both polarities, indexed scalar reordering, duplication and unread optimization. Every profile retains 32 semantic bits and initializes all 24/28 physical bits at zero edges from C=17, matching 79 boundaries / 237 outputs through END C=96. All four RAM words remain flip-flops. Wrong-value and conditional-update predicates produce real counterexamples; four conflicting checksummed checkpoints and a C=0 cut reject. Conflicting constant state fails fresh ordinary RTL replay at C=17 before any edge.
- All 28 real CAD/VCS profiles and independent audits pass, including all 20 prior profiles. All 103 Python tests and full M2/M3 metasim/ordinary-RTL regressions pass. M2 retains five cuts, all 22 words, actual C=29 divergence and four loader failures. M3 retains 717 transport edges, 23 semantic advances, six captures, 242 boundary/five semantic replay samples and eight invalid reads. Both supplemental shared-flop fault audits pass.
- Four unchanged independent audit controls pass; all 37 actual artifact mutations reject, including 12 constant mutations whose input hashes are rebound to exercise semantic/raw-proof checks. Two fresh equivalence builds still reject absent constant predicates despite PASS. Exact commands/results/full-path catalog: `runs/m8-iteration61/verification-commands.json`, `summary.json`, `matrix-results.json`, `artifact-manifest.json`.
- Jasper launch probes and the initial integrated empty-`info script` failure are preserved; corrected explicit hashed-script-path retry and complete matrix pass. The first integrated driver's top-level log was reused by the matrix; its raw Jasper log/return code remain in the original invocation and command catalog. No test scope was reduced.
- Next: complete hash-bound SRAM macro initialization, including contents and pipeline/port state, with real synthesis/proof/replay. Combined merging/duplication proof and merging/optimization fixtures remain unsupported. No missing external dependency blocks this increment. Recovery: [m8-formal-state-map.md](m8-formal-state-map.md). No plan/PDF/conda edits, staging, commits, resets, cleaning or FPGA/power claims.

Iteration 60 (October 10):

- Read both plans' relevant formal sections, progress/previous verification and both papers' preserved matching/replay extracts before edits. Plan/PDF hashes and starting staging are under `runs/m8-iteration60/`; plans remain read-only, including the dirty agent plan.
- Added a dynamic four-bit unread-state original fixture. Native Genus synthesis removes it; Formality proves required state/output equivalence and explicitly classifies those four original DFFs as unread. Version-3 evidence/map retains every semantic bit and cross-checks the hash-bound raw human report's point set, side, filter and count. Extra/unproven gate state and missing/contradictory/unsupported classifications still fail.
- All eight new optimized profiles cover both polarities, indexed scalar reordering and duplication. All 28 semantic bits remain represented; all 24/28 physical bits deposit/read back at zero edges from C=17 and match 79 boundaries / 237 outputs through END C=96. All four RAM words remain flip-flops. Altering every unread checkpoint bit passes fresh ordinary RTL replay; connecting that actual state to an output fails fresh formal equivalence and removes unread classification.
- All 20 real CAD/VCS profiles and independent audits pass, including all 12 previous profiles. All 97 Python tests and full M2/M3 metasim/ordinary-RTL VCS regressions pass. M2 retains five cuts, all 22 words, real C=29 divergence and four loader failures; M3 retains 717 transport edges, 23 semantic advances, six captures, 242 boundary/five semantic replay samples and eight invalid reads. Both supplemental shared-flop fault audits pass. Three unchanged audit controls pass and all 25 actual artifact mutations reject. Fresh constant builds in both polarities pass equivalence but reject map export for four unclassified bits. Exact commands/results/full-path catalog: `runs/m8-iteration60/verification-commands.json`, `summary.json`, `matrix-results.json`, `artifact-manifest.json`. An initial supplemental import failure from omitted root PYTHONPATH is preserved; the complete corrected checks pass.
- Next: independent constant predicates/point evidence and complete audited SRAM macro initialization. Constant probes pass global equivalence but lack usable classification; they remain rejected. No external dependency blocks this increment. Recovery: [m8-formal-state-map.md](m8-formal-state-map.md). No plan/PDF/conda edits, staging, commits, resets, cleaning or FPGA/power claims.

Iteration 59 (October 10):

- Read both plans' formal correspondence sections, progress/previous verification and both papers' preserved matching/replay extracts before editing. Plan/PDF hashes and starting staging are under `runs/m8-iteration59/`; the dirty agent plan is preserved. Proposed permission for symmetric proof orientation is recorded only in checkpointing docs.
- Added an original DUT with two equivalent four-bit held registers. Native Genus synthesis merges each pair without rewriting its successful netlist. Formality supports one reference point to many implementation points, so the merging configuration loads the gate netlist as reference and original RTL as implementation. Each original alias and every output must pass, without reset/input assumptions or black boxes; retiming remains false. Export normalizes the raw oriented inventories into a build-bound version-2 StateID-to-gate map.
- All four merging profiles (direct/inverted, ordered/reordered) prove 28 state relationships + 12 outputs. Four shared flops retain eight semantic sources. Fresh gate VCS deposits/readbacks all 24 physical bits at zero edges from C=17 and matches 79 boundaries / 237 outputs through END C=96, as does uninterrupted gate execution. All four logical RAM words are covered; they remain synthesized flip-flops.
- Translation requires all semantic sources of shared storage to agree after proven XOR transforms, then emits one deposit per flop. A valid, independently checksummed conflicting checkpoint rejects before producing deposits; missing alias proof rejects despite global PASS. Wrong alias, polarity, permutation and changed D fail fresh formal/export. Five atomic loader failures preserve all storage and continuation. Actual counter and shared-flop faults first differ at C=29 after 12 restored edges. Changed shared D makes both original alias points fail; both polarities have independent raw-artifact fault audits.
- All 12 real CAD/VCS profiles and independent audits pass, including all eight previous profiles. Two unchanged isolated controls pass and all 16 actual audit mutations reject. All 94 Python tests and complete M2/M3 metasim/ordinary-RTL VCS regressions pass. M2 retains five cuts, all 22 words, actual C=29 divergence and four loader rejections; M3 checks 717 transport edges, 23 semantic advances, six captures, 242 boundary/five semantic replay samples and eight invalid reads. Exact commands/results/full-path catalog: `runs/m8-iteration59/verification-commands.json`, `summary.json`, `artifact-manifest.json`; profile locations: `matrix-results.json`. Recovery: [m8-formal-state-map.md](m8-formal-state-map.md).
- Next: prove constants/irrelevance without inferring missing state from global PASS, then implement complete hash-bound SRAM macro initialization. Combined merging/duplication currently rejects explicitly because this Formality orientation alone cannot express both transformations. No missing external dependency blocks this increment. Level 1 remains independent. No plan/PDF/conda edits, staging, commits, resets, cleaning or FPGA/power claims.

Iteration 58 (October 10):

- Read both plans' formal correspondence sections, progress/previous verification and both papers' preserved matching/replay extracts before editing. Starting plan/PDF hashes and staging are under `runs/m8-iteration58/`; the dirty agent plan is preserved. Numbering correction remains solely in checkpointing docs.
- Added native Genus `rename_obj` permutation of indexed scalar counter destinations, preserving actual D/Q connectivity and never rewriting successful netlists. Hash-bound formal configurations supply candidates; each state relation/output must pass. This validates scalar destination name/index permutation, not packed multibit-cell ordering or physical placement.
- All four reordered profiles prove complete 24/28-bit correspondence. Fresh ordinary gate VCS deposits/readbacks all bits at zero edges from pre-edge C=17 and matches 79 boundaries / 237 outputs through END C=96, as does uninterrupted gate execution. Five/six atomic loader failures preserve all bits and continuation. Actual storage fault first differs at C=29 after 12 edges. Changed D, wrong polarity and guessed same-index permutation each fail fresh formal/export; swapped map destinations reject before translation; a missing copy proof rejects despite global PASS.
- All eight CAD/VCS profiles and independent audits pass, including four prior-profile regressions. Unmodified isolated audit control passes and eight actual artifact mutations reject. All 92 Python tests and complete M2/M3 VCS metasim/ordinary-RTL regressions pass. M2 retains five cuts, all 22 words, real C=29 divergence and four loader rejections; M3 checks 717 transport edges, 23 semantic advances, six captures, 242 boundary/five semantic replay samples and eight invalid reads. Exact commands/results/full-path catalog: `runs/m8-iteration58/verification-commands.json`, `summary.json`, `artifact-manifest.json`; profile locations: `matrix-results.json`. Recovery: [m8-formal-state-map.md](m8-formal-state-map.md).
- No missing dependency blocks this increment. Next: proven merging/constants/irrelevance export and an audited SRAM macro initialization adapter. Preserve complete state membership and target-cycle semantics. Level 1 remains independent. No plan/PDF/conda edits, staging, commits, resets, cleaning or FPGA/power claims.

Iteration 57 (October 10):

- Read both plans' relevant formal sections, progress/previous verification and both papers' preserved matching/replay extracts before editing. Plan/PDF hashes and initial staging are under `runs/m8-iteration57/`; the dirty agent plan is preserved. Numbering correction remains only in checkpointing docs.
- Added native Genus counter-register cloning and grouped Formality one-to-many candidate matches. Every copy must pass independently; no successful netlist is rewritten. The inventory accepts actual escaped clone suffixes, with complete semantic/physical membership and build binding preserved.
- Both duplicated profiles prove 28 state + 12 output points; the inverted profile has 28 XOR=1 storage destinations. Fresh gate VCS deposits/readbacks all 28 bits at zero edges from C=17 and matches 79 boundaries / 237 outputs through END C=96, as does uninterrupted gate execution. Six atomic loader failures preserve all bits and continuation. Actual clone storage fault first differs at C=29 after 12 edges; changed clone D and wrong polarity fail fresh formal/export. A removed copy proof rejects despite global PASS.
- All four CAD/VCS profiles and independent audits pass, including renewed direct/inverted regressions. Six isolated actual audit mutations reject. All 92 Python tests and complete M2/M3 VCS metasim/ordinary-RTL regressions pass. M2 retains five cuts, all 22 words, real C=29 divergence and four loader rejections; M3 covers 717 transport edges, 23 semantic advances, six complete captures, 242 boundary/five semantic replay samples and eight invalid reads. Exact commands, summary and full-path catalog are under `runs/m8-iteration57/` (`verification-commands.json`, `summary.json`, `artifact-manifest.json`). Recovery/remaining scope: [m8-formal-state-map.md](m8-formal-state-map.md).
- No missing external dependency blocks this increment. Real reordering, merging, constants/irrelevance and SRAM macro initialization remain. No conda/PDF/plan edits, staging, commits, resets, cleaning or FPGA/power claims.

Iteration 56 (October 10):

- Read the plans' formal correspondence sections, previous progress/verification and both papers' preserved matching/replay extracts before editing. Saved plan/PDF hashes and staging baseline under `runs/m8-iteration56/`; plans remain read-only, including the dirty agent plan. Numbering correction stays only in checkpointing docs.
- Added a real inverted-output Genus synthesis profile with audited CKDFFN model/Liberty/adapter. Formal configuration is hash-bound before/after proof; name/polarity candidates must verify. Incomplete automatic inversion attempts and the reserved-Tcl-variable diagnostic are retained. Export also rejects a manifest whose original RTL identity differs from the proven reference.
- Formality proves all 24 state + 12 output points in both direct and inverted profiles; the latter has 24 proven XOR=1 storage mappings, including all four RAM words. Each fresh gate VCS verifies all 24 deposited bits at zero edges from C=17, matches 79 boundaries / 237 outputs, and reaches END C=96. Uninterrupted gate matches ordinary RTL; five loader faults preserve every bit and continuation. Actual storage fault first differs at C=29 after 12 edges; changed netlist and wrong polarity fail fresh proof/export.
- Both independent audits verify raw human polarity reports, complete identities/state/deposits/containers/traces/logs. Three isolated actual audit mutations reject. All 91 Python tests and complete M2/M3 VCS metasim/ordinary-RTL regressions pass. Exact commands and results are recorded in `runs/m8-iteration56/verification-commands.json`, `summary.json` and the full-path `artifact-manifest.json`. Final invocations: `inverted-complete/invocation-a7eywu05/` and `direct-complete/invocation-d8jx2kwp/`. Recovery/remaining scope: [m8-formal-state-map.md](m8-formal-state-map.md).
- No remaining external dependency blocks this increment. Real reordering, duplication, merging, optimization/irrelevance and SRAM macro initialization remain unvalidated. No plan/PDF/conda edits, staging, commits, resets, cleaning or FPGA/power claims.

Iteration 55 (October 10):

- Read both plans' formal state correspondence sections, progress/previous verification and both papers' preserved matching/replay extracts. Starting plan/PDF hashes and staging baseline are in `runs/m8-iteration55/`; the dirty agent plan is preserved. Numbering discrepancy (loop M8 vs agent-plan M9/Phase 10) is recorded only in checkpointing docs.
- Added a separate Formality passing-point exporter, complete semantic/gate inventories, hash-bound audited cell storage adapters and map revalidation before independent Level-2 translation. CAD scripts hash actual inputs before/after execution; synthesis exports its netlist hash and queried retiming=false. Missing proof/state, stale sources, retiming, unknown SRAM macros and optimized/merged reference bits fail explicitly. Unit-only XOR/permutation/duplication checks do not count as real formal acceptance.
- Genus and Formality licensed runs succeed. Formality proves all 24 sequential + 12 output compare points of the original small DUT against its actual 101-cell synthesized netlist, including all four logical RAM words mapped to flip-flops. No reset/input assumptions or black boxes. Test library timing/area is artificial. Added explicit VPI resolution of escaped gate instance components; every handle is still prevalidated before writes.
- Final gate verifier passes: C=17 checkpoint, 24-bit zero-edge deposit/readback, all 79 restored boundaries / 237 output values match ordinary RTL and uninterrupted gate execution through END C=96. Five real loader faults leave every bit unchanged before edges; all continuations match. Actual gate bit fault first differs at C=29 after 12 edges (exit 1); changed gate D input fails a fresh Formality run and map export. Independent report/container/netlist/state/trace/log audit passes.
- All 90 Python tests and complete M2/M3 VCS metasim/ordinary-RTL regressions pass: M2 covers five cuts, all 22 words, original C=29 mismatch and four loader rejections; M3 covers 717 transport edges, 23 semantic advances, six complete captures, 242 transport-boundary/five semantic replay samples and eight invalid client reads. Exact argv, summary and full-path catalog: `runs/m8-iteration55/verification-commands.json`, `summary.json`, `artifact-manifest.json`. Final invocation: `complete-validation/invocation-9q59xpcl/`. Recovery/remaining scope: [m8-formal-state-map.md](m8-formal-state-map.md). No conda/PDF/plan edits, staging, commits, resets, cleaning, physical FPGA or ASIC power claims.

Iteration 54 (October 10):

- Read the DESSERT/finite-replay sections of both read-only plans, prior progress/verification and both root papers' preserved state/I/O replay extracts. Saved fresh plan/PDF hashes and staging baseline under `runs/m7-iteration54/`; the existing dirty agent plan is preserved.
- Added `finite_replay.py`: independent Level-2 package/replay, complete container/inventory/boundary validation, schema-2 forwarded clocks, finite data-driven input delivery, complete pre-edge VPI readback, explicit failure and full hierarchy/RAM VPD. `vpd2vcd -full64 +includemda` preserves all RAM words. Retained failed timescale, 32-bit converter and memory-omitting VCD trials as diagnostics.
- All 84 Python / 24 Scala tests and full M2/M3 metasim/ordinary VCS regressions pass. Deliberate fixture output RTL XOR, triggered by actual DUT counter during a valid response transfer, first fails at C=29 from reset C=0 and in-flight C=24/C=26. Independent waveform audit verifies all 22 words at zero edges and every input/output/cycle through the divergence. Five real malformed-runtime trace checks pass after correcting the initial verifier's ineffective unknown-value mutation.
- Full verifier passes: `tools/checkpoint_formats/tests/verify_finite_replay_vcs.py`. Final invocation: `automations/checkpoint_loop/runs/m7-iteration54/finite-replay-final/invocation-tkq1rf1b/`. It packages all 250185 recorded FCFS boundaries from iteration-53's actual healthy metasim run into independent `.rtlckpt`/`.trace` inputs. Healthy ordinary VCS matches C=524453..774637, takes 250185 edges, ends at C=774638 and exits 0. Two fresh DUT QoS RTL-XOR defects first differ at C=524474 after 21 edges and exit 1. No state or trace corruption, live authority process, Level-1 restore or FASED model participates in these replays.
- All seven independent waveform audits pass. Each FCFS VPD/VCD exposes 1342 registers, all 13501966 words in all 201 RAMs and all 50 boundary/clock ports. The auditor verifies every restored word at zero edges, then every input/output boundary and actual clock timing through finite END or first divergence. Healthy waveform checks all 12008880 input/output values; both defect waveforms verify the divergent boundary and no faulting edge. Input containers retain their hashes.
- Exact commands, summary and full-path catalog: `runs/m7-iteration54/verification-commands.json`, `summary.json`, `artifact-manifest.json`; complete case evidence and `independent-waveform-audit.json` are in the final invocation. Recovery: [m7-dessert-replay.md](m7-dessert-replay.md). No remaining M7 acceptance work for the supported profiles. No plan/PDF/conda edits, staging, commits, resets, cleaning or physical FPGA/ASIC/formal claims.

Iteration 53 (October 10):

- Read both plans' relevant live-shadow sections, iteration-52 progress/recovery, previous healthy-END failure and both papers' replay/input-trace sections in preserved extracts. Saved fresh plan/PDF hashes and staging baseline; plans remain read-only and unstaged, including the existing dirty agent plan.
- Public FCFS capability loads the exact Y-2026.03-SP1 `liberrindex.so` / `libsystemcerror.so` paths before immutable runtime identity construction. Retained handles keep both tables present through shutdown; complete existing ELF hashing binds their bytes during capture and fresh restore. No late-load exception or post-entry identity refresh. Unsupported VCS_HOME and loader errors reject explicitly.
- Fresh capture and ordinary public restore both finish at reported cycle 774628 with exit 0. All 1543 entries / 13503308 semantic words agree across hardware readout, independent Level-2 image, fresh Level-1 readout and ordinary clean pre-edge readback. Zero-edge bootstrap, 13507456 generated words, 29 harness records and 17 native owners are independently verified.
- Live healthy pair matches C=524453..774637, with 250185 acknowledged edges / 8506290 output comparisons; both processes finish END at C=774638 and exit 0. A real clean AR queue-RAM bit flip first changes `ep_axi4_ar_bits_qos` at C=524553 after exactly 100 ACKs; both processes exit 1 with that cycle pending. The full audit verifies all 14 authoritative inputs, all 34 outputs and held payloads on every ready/valid channel.
- All 81 Python / 24 Scala tests, complete M2/M3, 46 native runtime-identity rejections, 24 transport ASan/UBSan cases (real 30-second timeout), 21 shadow-control cases, eight actual VCS readback cases and five public-entry VCS rejections pass. Schema-1 regression matches 107531 cycles and first detects its actual state fault at cycle 29. Native warmup independently verifies 14 ELF hashes and fresh load; complete captured production identity verifies 43 ELF hashes. Changed/late/missing ELF sets still reject.
- Exact argv, complete audit and full-path artifact catalog: `automations/checkpoint_loop/runs/m6-iteration53/verification-commands.json`, `independent-evidence.json`, `summary.json`, `artifact-manifest.json`. Paired invocation: `paired-semantic/invocation-t4usmy06/`; its `live/summary.json` records live acceptance. Recovery: [m6-restored-live-shadow.md](m6-restored-live-shadow.md). No remaining M6 acceptance work for the supported FCFS profile. No conda/PDF/plan edits, staging, commits, resets, cleaning or FPGA/formal/ASIC claims.


Iteration 52 (October 10):

- Read both plans' live-shadow sections, progress and previous verification; consulted both root papers' replay/input-trace sections in preserved extracts and recorded fresh PDF/plan hashes. Plans remain read-only and unstaged, including the existing dirty agent plan.
- Added `bridge_live_shadow.py`: all 14 authoritative inputs, all 34 data outputs (seven audited erased definitions), separate clock aliases, independent checkpoint/session binding, explicit restored semantic origin, actual gated DUT edges, complete boundary delivery and first-output-divergence termination. `semantic_verify` streams full VPI readback of all 13,503,308 clean words before any edge, including unknown-bit rejection.
- `FS_CHECKPOINT_SHADOW=1` links only the known host transport, preserves the strict production driver and 17 native owners, and enables typed restore-only observer controls. Partial/duplicate/unknown controls and malformed paths/hash/cycle labels reject before loading. Startup has a 600-second bound; each target-cycle ACK retains its independently tested 30-second deadline.
- All 81 Python / 24 Scala tests, complete M2/M3, eight actual VCS readback cases, 21 ASan/UBSan control cases, 24 renewed transport cases (real 30-second timeout), and five actual public VCS control rejections pass. The schema-1 regression matched 107531 cycles and detected the real state fault at cycle 29. Failed driver-link trials, the initial Scala diagnostic-directory error, and the SV-before-C++ rejection expectation are preserved.
- The first FCFS invocation passed its complete independent pre-edge audit, then rejected `+shadow-socket` through the production whitelist with zero compared cycles. The typed opt-in contract fixes that. The rebuilt invocation independently verifies all 1,543 entries / 13,503,308 words across hardware, Level 2, fresh Level-1 restore and clean readback; capture/ordinary restore both pass at reported cycle 774628. Input bindings/actual cut values match at FASED 524402 / semantic 524453 with zero restored edges.
- Live healthy case: C=524453..774637 matches every boundary output with no first mismatch. The authoritative workload reaches `*** PASSED *** after 774628 cycles`, then the strict runtime identity finalizer reports late `liberrindex.so` and `libsystemcerror.so`; both processes exit 1 before END. The full verifier correctly fails and no successful END is claimed. The mandatory fault case ran separately on the same source-bound executables/images: actual AR queue-RAM bit 0 flips, `ep_axi4_ar_bits_qos` first differs at C=524553, only C=524453..524552 are acknowledged, and both processes exit 1 with pending cycle 524553.
- Evidence and exact argv: `automations/checkpoint_loop/runs/m6-iteration52/verification-commands.json`, `independent-evidence.json`, `summary.json`, `artifact-manifest.json`; current paired invocation is `paired-semantic/invocation-7in7vzpj/`. The partial-live audit verifies the lifecycle failure explicitly while retaining all state, regression, timing/held-payload and real-corruption checks; it does not mark acceptance ready. Recovery: [m6-restored-live-shadow.md](m6-restored-live-shadow.md).
- Next: warm/pin the two release-specific VCS diagnostic libraries before native identity construction in both capture and restore, retain rejection of all late/changed ELF sets, recreate the source-bound Level-1 image, and rerun the complete scope through healthy END plus exact corruption. Do not ignore the libraries or refresh compatibility after entry. No conda/PDF/plan edits, staging, commits, resets, cleaning or FPGA/formal/ASIC claims.

Iteration 51 (October 10):

- Read both plans' relevant live-shadow sections, progress and the previous verification tail; consulted the root papers' replay sections in the prior extracts and verified the root PDF hashes. Plans retain their iteration-start hashes, including the existing dirty agent plan, and staging remains unchanged.
- Preserve bridge-extracted data inputs with opt-in `DontTouchAnnotation` before FAME/optimization. No pre-FAME circuit/reference, StateID, target logic or ordinary inventory changes. Response status feeds queued state/error handling; no noninterference assumption or guessed value replaces it. All four response fields now survive in the actual transformed DUT with exact original widths and directions.
- Record all 14 concrete input bindings and actual parked-cut values. Capture at FASED 524402 / semantic edge 524453 and fresh public restore agree on every defined input with zero restored host/target edges. Changed membership, mapping, shape, cycle and unknown/padded values reject. All seven erased outputs retain their independently checked definitions. This is paired-cut visibility, not live ready/valid synchronization.
- Both native processes pass at reported cycle 774628. All 1,543 entries / 13,503,308 words match the hardware readout, independent Level-2 image, fresh Level-1 readout and clean pre-edge readback. The real clean `num_resps` bit flip changes exactly one word at semantic cycle 524453 with zero edges; it remains a pre-edge corruption test. The independent audit verifies all 13,507,456 generated words, 29 harness records, 17 native owners, source/metadata bindings, actual VCS Y-2026.03-SP1 release and full regression coverage. The initial new Scala fixture's missing harness connections were fixed; its failed diagnostic is retained and the complete 24-test scope reran successfully.
- Evidence and exact argv: `automations/checkpoint_loop/runs/m6-iteration51/verification-commands.json`, `independent-evidence.json`, `summary.json`, `artifact-manifest.json`; paired invocation: `paired-semantic/invocation-pdu2jojj/`. Recovery: [m6-fcfs-semantic-cut.md](m6-fcfs-semantic-cut.md). Next: complete schema-2 delivery at actual gated DUT edges, initialize the restored observer from semantic origin 524453, then run sustained concurrent restored-metasim/clean RTL checking and actual first-output-divergence injection. Clean RTL still stops before its first edge. No conda/PDF/plan edits, staging, commits, resets, cleaning or FPGA/formal/ASIC claims.

Iteration 50 (October 10):

- Read both plans' relevant live-shadow sections, progress and the failed verification tail; consulted the prior extracted replay sections of both root papers. The repeated iteration-49 invocation lacked `production-build-metadata/`; its earlier manually archived evidence did not make the saved verifier reproducible. Plans retain their iteration-start hashes, including the existing dirty agent plan, and staging remains unchanged.
- Fixed the verifier to archive the complete native Make metadata immediately beside its own executable, pin exported VCS code libraries and copied RTL/probes, save the aggregate build identity, and decode the actual public Level-1 image against that identity and independent cut label. Added a reusable repository audit and rejection tests for missing metadata and changed metadata, executable, source or image. The final audit resolves `latest.json`, so it checks the newly repeated invocation.
- Audited six erased constant outputs and `ep_reset = reset` against both selected pre-FAME FIRRTL and clean SV. Source/membership changes, incorrect widths, conflicting/multiple drivers and unsupported expressions reject. Four erased inputs remain explicit obligations: `ep_axi4_b_bits_resp`, `ep_axi4_b_bits_user`, `ep_axi4_r_bits_resp`, `ep_axi4_r_bits_user`. No values are guessed and this audit does not enable live execution.
- Four fresh VCS Y-2026.03-SP1 processes pass. Both native executions finish at reported cycle 774628. The independent cut is FASED 524402 / semantic edge 524453, with initialization complete and four outstanding requests. All 1,543 entries / 13,503,308 words match the hardware readout, independent Level-2 image, fresh Level-1 readout and clean pre-edge readback. The real clean `num_resps` bit flip changes exactly one word at semantic cycle 524453 with zero edges; it is still a pre-edge test, not live first divergence.
- All 76 Python / 23 Scala tests and complete M2/M3 VCS regressions pass without scope reduction. The latest-invocation independent audit passes all native records (13,507,456 generated words, 29 harness records, 17 owners), complete semantic mappings/readbacks, actual runtime release, source bindings and plan/staging preservation. Evidence, exact argv and full-path catalogs: `automations/checkpoint_loop/runs/m6-iteration50/verification-commands.json`, `independent-evidence.json`, `summary.json`, `artifact-manifest.json`. Paired invocation: `paired-semantic/invocation-o3sns6y0/` beneath that directory.
- Recovery details and corrections remain in [m6-fcfs-semantic-cut.md](m6-fcfs-semantic-cut.md). Next: establish authoritative bindings or separately prove noninterference for the four erased response inputs, then implement complete schema-2 live delivery at actual gated DUT edges, initializing the restored observer from the paired semantic origin. Run sustained concurrent restored-metasim/clean RTL checking and actual first-output-divergence injection. Clean RTL still stops before its first edge in this scope. No conda/PDF/plan edits, staging, commits, resets, cleaning or FPGA/formal/ASIC claims.

Iteration 49 (October 10):

- Read both plans' live-shadow sections, current progress, prior verification and relevant extracted sections of both papers. Plans retain their initial hashes and remain read-only/unstaged, including the existing dirty agent plan. Numbering and cycle-origin corrections remain only under checkpointing docs.
- Added explicit `SEMANTIC_BRIDGE_CHECKPOINT_ROOT`, deferred until resolved bridge extraction and before FAME/instrumentation. Ordinary inventory behavior is preserved; mixed/duplicate roots, incompatible banked bindings, opaque state, generated clocks and unsupported pipelines reject. Forwarded `ep_clock` is independently audited and recorded as a schema-2 clock alias. The full 1,543-entry / 13,503,308-word semantic inventory exactly matches clean and transformed RTL state. All 11 erased data ports remain explicit live-adapter obligations.
- Added `bridge_semantic.py` and the full VCS verifier. A read-only observer samples original DUT values at the parked low-clock event beside actual public native capture. No Level-1 image is converted. Public operation 699275 reaches FASED cut 524402 after 524453 actual DUT edges; the independent `.rtlckpt` uses semantic origin 524453 and records both labels in its sidecar. Initialization is complete, four requests are issued and no responses completed. Both native executions pass at reported cycle 774628.
- All 13,503,308 semantic words match in the captured hardware readout, fresh public Level-1 restored readout, validated Level-2 image and ordinary clean VCS pre-edge readback. The restored sampler and clean process take zero target edges before observation. A second fresh clean process flips real `fuzzer.num_resps` bit 0; complete readback identifies only that word at semantic cycle 524453 with zero edges. This is not live first-divergence acceptance.
- Final scope and independent audit pass: 72 Python / 23 Scala tests, complete M2/M3, four fresh production/clean VCS processes, full native image/executable compatibility and all semantic words. Native inventory has 13,507,456 generated words, 29 harness records and 17 owners. Failed exploratory trials are preserved; every final scope ran afresh without reduction or skipped checks. Exact commands, source bindings and full-path catalog: `automations/checkpoint_loop/runs/m6-iteration49/verification-commands.json`, `independent-evidence.json`, `summary.json` and `artifact-manifest.json`. Final VCS evidence: `paired-semantic-final/invocation-uouy7dic/summary.json` beneath that run directory.
- Recovery and proposed plan corrections: [m6-fcfs-semantic-cut.md](m6-fcfs-semantic-cut.md). Next: audit erased boundary fields and target-cycle origin, extend the complete boundary adapter, then run sustained concurrent clean/Level-1-restored shadowing with actual first-output-divergence detection. The current paired-state verifier does not drive clean RTL beyond its restore boundary. No conda/PDF edits, staging, commits, resets, cleaning or physical FPGA/formal/ASIC claims.

Iteration 48 (October 10):

- Read both plans' live shadow sections, current progress, prior verification and both papers' relevant extracted sections. Plans remain read-only and unstaged at their initial hashes, including the existing dirty agent plan. The loop's M6 corresponds to Phase 8 / M7 in that input; the numbering correction remains under checkpointing docs.
- Added `live_shadow.py` and host-only `live_shadow_transport.cc`: independent `.rtlckpt` validation/readback, strict complete single-clock hierarchy mapping, checkpoint/source-bound handshake, complete boundary delivery at actual gated DUT edges, settled per-cycle output checking, one clean edge per acknowledgment and first-divergence failure. No finite trace supplies future inputs or clean-output feedback to the environment.
- Added an optional sustained InventoryFixture workload after all original directed checks. The final source-bound two-VCS run matches C=26..107556 (107531 cycles, 1397903 output comparisons), with 28675 held responses, 18434 transfers and 79872 blocked requests. Independent counter/FSM indexing and held valid/payload checks pass. Actual clean `responseData` corruption first diverges at C=29 with only C=26..28 acknowledged; both processes exit 1 and the authority names pending cycle 29. Ordinary `exit` hung in the first diagnostic trial; the corrected failure path flushes diagnostics and uses `_Exit(1)`. That failed trial was interrupted with exit 130 and preserved; the complete final scope ran afresh.
- All 67 Python tests, complete M2 replay, complete M3 banked capture/clean replay and 24 corrected native ASan/UBSan cases pass, including a real 30-second missing-ACK timeout. Final source-bound VCS evidence is `live-shadow-final/invocation-wf266xei/summary.json`; native evidence is under `native-transport-immediate/latest.json`. Exact commands, independent audit and full-path catalog: `automations/checkpoint_loop/runs/m6-iteration48/verification-commands.json`, `summary.json` and `artifact-manifest.json`.
- Recovery details: [m6-live-boundary-shadow.md](m6-live-boundary-shadow.md). Next: independent FCFS Level-2 inventory/mapping and same-cut semantic extraction, then live target-cycle adapter beside an actual public Level-1 restored metasim. The current authoritative fixture boots normally; this increment does not establish complete M6 acceptance. No conda/PDF edits, staging, commits, resets, cleaning, physical FPGA, formal or ASIC claims.

Iteration 47 (October 10):

- Added strict `+fs-checkpoint-target-timeout-cycles=N` paired with the existing bounded capture timeout and public periodic history or restore. The parked settled callback samples the compiled 14-bit `TLFuzzer.num_resps` and 20-bit `TLRAMModel.wipeIndex`. Completed work is `wipeIndex + 10000 - num_resps`: finite 524288-cell shadow initialization followed by response completion. Initialization cannot keep refreshing the deadline after it completes. Fresh restores initialize from their first actual settled sample; no MMIO, native loads, deposits or added target edges are used for sampling.
- Normal Make pins both complete lowered source modules (source locations excluded) and exact generated membership/shape/clock/reset/adapter before writing output. Unknown profiles/update semantics, X/padding/wrong VPI kind, regressing counters, out-of-range counts and responses before initialization completes reject. The auxiliary inventory uses generated Level-1 identity, preserving independent Level-2 manifests. Native ASan/UBSan passes eight watchdog scopes, 237 complete collector and 15 targeted sampler rejections; actual compiled inventory passes 26 altered-shape/semantics rejections.
- Public monitored history commits 250000/500000/750001, retains 500000/750001, and matches every byte of the uninterrupted 40-port reference. Restored execution commits 600001/700000; both images freshly restore/read back all 17 native owners with zero-edge bootstrap and exact continuation. Captures exceed the ordinary one-second deadlines without false alarms; capture suspension remains bounded. Independent production host/cycle monitors reproduce main-thread stalls at 600013. Live configuration/directory/history and early-reset rejections all pass.
- Two fresh processes from the retained 500000 cut inject an observer-only target response-valid fault at 600000. The production sampler detects frozen completed work at 610000 after another 10000 target cycles; all 3305 completed responses stay fixed. Both complete fault traces match byte-for-byte and match the reference through the causal cut. A healthy monitored replay matches all 366116 suffix rows. Nine malformed semantic controls reject before native platform construction or trace advancement. The retained index/image bytes remain unchanged.
- All 63 Python tests, full production five captures/fresh continuations and 56 public restore rejections, native history faults/crashes/concurrency, 142 native/VCS entry cases, full M2/M3/dispatcher/harness, native publication, eight Make/four generator rejections and ordinary clean RTL VCS pass. Independent audit confirms 68 fresh processes, 67537280 generated-word comparisons, 85 native-owner comparisons and all 40 target ports. Runtime identity ASan/UBSan passes 43 checks, including real late library load/unload diagnostics; the compatibility guard remains strict.
- Preserved all diagnostic trials: observer declaration ordering, missing control-file probes loading VCS runtime-error DSOs, response-only false startup alarm, and the verifier's mistaken assumption that an optional SV observer cannot create an empty trace before entry rejects. The observer now reads an existing numeric control file; semantic progress includes audited initialization work; malformed-request verification checks no native construction/edges/trace data. Every final production/history/replay scope ran on source-bound `normal-make-initialization`; no check was skipped or reduced for resources.
- Evidence, exact argv and full-path catalogs: `automations/checkpoint_loop/runs/m5-iteration47/verification-commands.json`, `independent-results.json`, `production-scope-results.json`, `summary.json` and `artifact-manifest.json`. Details: [m5-semantic-progress.md](m5-semantic-progress.md). Plans retain iteration-start hashes, remain read-only/unstaged, and their milestone-number correction stays solely in prior checkpointing docs. No conda/PDF edits, commits, resets, cleaning, physical FPGA, formal or ASIC claims. Monitoring before the first audited post-reset sample and unknown target profiles remain outside this capability. The loop can advance to its next assigned milestone.


Iteration 46 (October 10):

- Added strict public `+fs-checkpoint-host-timeout-ms=N`, `+fs-checkpoint-cycle-timeout-ms=N` and paired `+fs-checkpoint-capture-timeout-ms=N` for periodic Level-1 history or public restore. The settled callback samples the compiled manifested FASED target-cycle counter without MMIO or added target edges; monitoring arms after initial reset drains. Fresh restored sampling starts at the actual settled callback (500002 after the loaded 500000-cycle cut), with exact native readback and zero-edge bootstrap before continuation.
- An independent native thread watches coherent host copies with nonblocking sampling-lock attempts. A stuck sampler holding that lock cannot disable detection. Full collection/atomic publication/commit/readback/retention excludes only elapsed capture time from progress deadlines, preserving pre-capture stall age, under a separate bounded capture deadline. Failures exit without VCS teardown or worker acknowledgment; host policy remains outside both checkpoint levels.
- Native ASan/UBSan passes six scopes: deadline boundaries/28 parser rejections, healthy capture suspension/shutdown, real host/cycle/capture stalls and a deliberately blocked sampling critical section. Native history passes 18 I/O faults, seven SIGKILL boundaries, 12 corrupt/special cases, 24 parser rejections, eight competing writers and Python interoperability. All 63 Python tests, 225 native/VPI collector rejections, 142 native/VCS entry cases, full M2/M3, dispatcher/harness, native publication, clean RTL VCS and eight Make/four generator rejections pass. The final normal Make capability passes all five full captures/fresh continuations and 56 public restore rejections; independent audit verifies all 68 processes, 67537280 generated words and 85 native owners across 40 target ports.
- Current monitored live history passes all three original commits/newest-two retention, two external late-stall retained replays, two restored-run commits/fresh recapture replays, 29 public configuration/directory and six bad-history rejections plus early-reset restore rejection. Captures exceed the one-second progress deadlines without false alarms. The dedicated runtime verifier parks only the VCS main thread after 600000 using PTRACE_SEIZE/INTERRUPT; production host/cycle monitors independently detect stalls at 600025/600002 about 1.2 seconds after the confirmed stop. Both match every available reference byte and all 17 native owners; healthy monitored replay matches all 366116 continuation rows. All 27 watchdog argument rejections and unsupported early-reset monitoring reject.
- Fixed per-poll loaded-ELF hashing in the production coordinator and test observer for restore-only watchdog polling, retaining full restore/capture/finalization audits. Preserved the timed-out pre-fix trial, the insufficient 60-second capture deadline trial, a stale-binary periodic regression and an initial diagnostic-trace verifier assumption as diagnostics. Final source-bound evidence uses `normal-make-watchdog`, `live-history-watchdog`, `periodic-watchdog` and `watchdog-vcs-watchdog`. Complete scopes were rerun after source-binding changes; no check was reduced or skipped.
- Evidence, exact argv and full-path catalogs: `automations/checkpoint_loop/runs/m5-iteration46/verification-commands.json`, `regressions-final.json`, `summary.json` and `artifact-manifest.json`. Details: [m5-progress-watchdogs.md](m5-progress-watchdogs.md). Plans retain iteration-start hashes and remain read-only/unstaged; existing conda/PDF inputs are untouched. No commits, resets, cleaning, physical FPGA or ASIC claims. Next: audit a semantic completed-work/retirement counter against the compiled manifest and reproduce a target deadlock while its cycles keep advancing. Current monitoring covers post-reset/post-bootstrap sampling, not startup before that first audited sample.


Iteration 45 (October 10):

- Added `+fs-checkpoint-directory=PATH +fs-checkpoint-interval=N +fs-checkpoint-retention=N +fs-checkpoint-level=1`, including strict early configuration/capability rejection and capture during public restored execution. Added a native pinned-directory, locked immutable-image publisher with complete on-disk validation, atomic synced index/readback and bounded retention before worker acknowledgment. Post-index failures report explicit commit uncertainty; startup validates/recover-prunes retained state. Python `NativeRollingHistory` interoperates using a distinct build-bound index schema and strictly earlier pinned-byte selection.
- Native ASan/UBSan checks pass 18 I/O faults, seven actual SIGKILL boundaries, 12 corrupt/special-history cases, 24 parser rejections, eight competing writers, full Python byte identity/interoperability, replaced-directory pinning, exact immutable-orphan reuse/conflict rejection and unaudited-capability rejection. All 63 Python tests, complete native collector, parked-worker guard, native/VCS dispatcher/harness, native durable publisher, ordinary clean RTL VCS, full M2/M3 and eight Make/four generator rejections pass. The rebuilt source-bound normal Make capability passes all five full-size continuations and 56 public restore rejections; independent audit verifies 68 fresh processes, 67537280 generated-word and 85 native-owner comparisons. The complete iteration-44 periodic verifier also passes afresh.
- Public live history passes three actual commits observed under the runtime's lock, newest-two retention and complete 40-port reference equivalence. Two fresh 500000-cycle retained replays detect external SIGSTOP after 600000; killed replay matches every available byte and resumed replay matches all 366116 complete samples. Restored execution commits at 600001/700000; both images freshly restore with exact 17-owner pre-edge readback, zero-edge bootstrap and matching continuations. All 29 public configuration/directory rejections, six invalid-history rejections and early-reset restore rejection pass. Each image contains all 13507456 generated words and 29 harness banks. History commit/retention is native and live; watchdog sampling remains external.
- Iteration 44's run directory exists and contains real nonempty evidence. The loop's `validated_artifacts` requires nonempty regular files, so listing that directory caused the previous feedback. Report concrete summary/manifest files. New diagnostics and exact argv/full-path catalogs are under `automations/checkpoint_loop/runs/m5-iteration45/`. Details: [m5-live-history.md](m5-live-history.md). Plans remain at initial hashes with no staging, commits, resets, cleaning, conda/PDF edits or physical FPGA/ASIC claims.
- Next: independent production host sampling with explicit capture-suspension accounting and an audited target-progress sampler/watchdog. Existing Python watchdog policies and external late-SIGSTOP replay checks do not establish runtime watchdog integration. The proposed milestone-number correction remains only under these docs.

Iteration 44 (October 10):

- Added repeated settled-cut polling with a fresh acknowledgment per callback, including not-due polls. Consecutive software-only operations can park again without MMIO yields or added native/target edges. Existing single-operation scheduling remains supported.
- Added the C++ target deadline policy and the complete production collector adapter using `+test-live-periodic=PREFIX +test-live-interval=N`. Each actual due cut atomically publishes a separate complete image. Restore uses an explicit restored target-cycle origin; later resets/regressions and unsupported state reject. Initial startup waits for the audited manifested target-reset pulse to drain. Bootstrap refresh assertions now end when bootstrap completes, permitting subsequent capture refreshes.
- All 63 Python tests, ordinary clean RTL VCS, complete M2/M3, 225 native/VPI collector rejections, 32 native/VCS dispatcher continuations and five actual harness continuations pass. The real-worker ASan/UBSan guard adds eight repeated cuts, including four consecutive cuts without a yield, per-cut missing-ack rejection and native target deadline/overflow/retry checks. Final source-bound normal Make passes all five complete captures/fresh continuations and 56 restore rejections; eight Make/four generator rejections preserve the compiled inventory.
- One uninterrupted live run captures complete cuts at 250000, 500000 and 750001 target cycles and matches every byte of the full 40-port reference. History retains 500000/750001. Two fresh 500000-cycle replays detect external SIGSTOP stalls after 600000; the killed process matches all available bytes, and resumed execution matches all 366,116 complete continuation samples through 774628. Restored execution captures at 600001/700000; both recaptures restore with exact native pre-edge readback, zero-edge bootstrap and matching continuations. All 18 periodic argument rejections and the explicit early-reset restore rejection pass. Each image includes all 13,507,456 generated words, 29 harness banks and 17 native owners. History admission occurs after the live run; watchdog sampling is external.
- Evidence and exact commands: `automations/checkpoint_loop/runs/m5-iteration44/verification-commands.json`. Final source-bound runs use `normal-make-polling` and `periodic-vcs-polling/invocation-k7cie810`. The initial periodic simulation completed successfully; after correcting the verifier's host-sample lookup, its complete saved inputs/images/trace were revalidated and every remaining check ran afresh. Earlier wrong-path, startup regression, slow-poll timeout and superseded trials are preserved as diagnostics. Both root papers were read for checkpoint overhead, complete memory state and replay scope. Details and recovery scope: [m5-periodic-capture.md](m5-periodic-capture.md).
- Next: wire public periodic configuration and live retained-history commit/validation/retention before worker release, independent production host sampling with capture-time accounting, and audited target progress sampling. Plans remain preserved at initial hashes, with no staging, commits, resets, cleaning, conda/PDF edits or physical FPGA/ASIC validation.

Iteration 43 (October 10):

- Added `tools/checkpoint_formats/rolling.py`: complete v3 manifest/build/target-counter validation, locked immutable snapshots and atomic synced index commit, on-disk validation before commit, bounded retention only after durable commit/readback, explicit post-rename uncertainty, retry/recovery and pinned-byte selection strictly before a causal target cycle. Corrupt, unsupported, regressing and special-file inputs reject. Partial pending/foreign files remain uncommitted and preserved.
- Added target-cycle deadline policy with explicit restored origin, skipped-deadline/overflow handling and commit acknowledgment; independent monotonic-time host/target-cycle stall policies plus an advancing-target-cycle watchdog requiring audited target progress. These are host-side policies, not runtime capture/sampling adapters. Level-1 remains separate from Level-2.
- All 63 Python tests pass (53 prior plus 10 new), including nine I/O faults, five actual SIGKILL boundaries, concurrent writers/readers, special files, corruption, retry/recovery, replaced-directory pinning and both watchdog policies. Initial fixture errors are retained as diagnostics and the entire suite was rerun. Ordinary clean RTL compiles/runs on VCS Y-2026.03-SP1 full64 with the prescribed setup sourced last.
- Full-size verification admits existing live cuts at target cycles 0, 1, 524402 and 524404, retaining the last two. Fresh production VCS restores from the selected 524402 snapshot reproduce independently detected external SIGSTOP host stalls after cycle 600000. The first killed process matches every available reference byte, including its partial final trace row; the second resumes and matches all 333,580 complete 40-port samples through completion at 774628. Both load/read back all 17 native owners before any edge; snapshots include all 13,507,456 generated words and 29 harness banks. These snapshots were captured in separate earlier M4 cases; this does not establish periodic live capture or an injected target deadlock.
- Details and proposed milestone-number correction: [m5-rolling-history.md](m5-rolling-history.md). New evidence and full-path catalog: `automations/checkpoint_loop/runs/m5-iteration43/`. Plans are preserved at initial hashes; no plan/conda/PDF edits, staging, commits, resets or cleaning. M4's audited profile remains supported. Next: repeated settled-cut runtime adapter, public periodic options, restored-run capture and independent production watchdog sampling, then integrated late-failure replay acceptance.

Iteration 42 (October 10):

- Added `FS_CHECKPOINT_PROFILE=fcfs-fased-v1` to the ordinary Make flow, with complete FPGATop discovery, generated constructor-pass native enumeration, source/flag-bound compiled tables and a production zero-edge restore coordinator. Unsupported profiles/drivers/partial inventories/debug/gate-level/other backends reject. The checkpoint executable/companion data and C caches use separate paths. Regenerated table/header dependencies invalidate only stale checkpoint objects.
- The actual Make verifier uses the generated production coordinator; its optional monitor only observes. Corrected VCS test packaging to preserve the compiled executable basename and companion data/library paths. Omitted Make's injected `+no_notifier` only for the restrictive checkpoint profile. Complete fresh readback caught emitter initialization overwriting restored token/LFSR state at time zero; the corrected coordinator settles initialization with clocks reserved before loading. Initial failed trials are retained separately.
- Both complete Make runs pass all five fresh continuations and 56 public restore rejections per run. Each independently audits 68 fresh processes, 67,537,280 generated-word comparisons and 85 native-owner comparisons; all 40 transaction ports match through completion. All five additional diagnostic-free public captures/restarts pass exact native readback, independently bounded reporting timestamps, 19 scheduling rejections, four publication failures, unreachable and missing-callback checks. Eight Make/four generator rejections preserve the compiled inventory. Repeated verification uses a separate invocation directory and preserves 123 earlier immutable files' hashes/inodes.
- All 44 baseline and 15 focused scopes pass, including 53 Python/20 Scala tests, ordinary clean RTL VCS, full M2/M3, all native/VCS owners, counters/profiling, lifecycle/bootstrap, complete publication faults and independent state/timing audits. Corrected the independent executable-name assertion to follow the preserved `simv` alias to its canonical ELF path; all content hashes remain checked. Local runner setup/count diagnostics are retained, and every unfinished check was rerun without reducing scope.
- Recovery details: [m4-normal-make.md](m4-normal-make.md). Evidence/logs/full-path catalog: `automations/checkpoint_loop/runs/m4-iteration42/`. The supported workflow uses canonical Golden Gate emission for the named FCFS/FASED configuration; other drivers/profiles remain fail closed. Next milestone: M5 DMA transport. Plans/conda inputs remain preserved with initial hashes; no plan corrections, staging, commits, reset/clean, physical FPGA, formal or ASIC validation. Rolling capture and capture during a restored continuation remain later work.

Iteration 41 (October 9):

- Added `+fs-checkpoint=PATH +fs-checkpoint-operation=N` for the audited durable capability. Schedules count completed driver operations, with actual target cycle still collected from manifested FASED state. The capability arms the existing settled low-clock dispatcher before worker startup; diagnostic files/private capture requests are optional. Parser rejects malformed, duplicate, overflow, orphaned and conflicting schedules before construction.
- Added an `FS_CHECKPOINT_DURABLE` harness context callback to collect and atomically publish the complete live image while the worker remains parked. Publication acknowledgment is required before release, so a missing callback fails closed. Unreachable cuts fail at completion. The auxiliary host-edge counter only records observer metadata; it cannot affect target behavior. The harness audit now binds this source revision without changing the 29 bank geometries.
- All five final-code public captures match every byte of the complete Python oracle; fresh public restores match 3,765,516 complete 40-port samples through completion, including outstanding native/FASED writes and randomized host timing. Independent audit passes 68 processes, 67,537,280 generated-word and 85 native-owner comparisons, and all five live publications. All 56 public restore rejection cases pass. All five additional diagnostic-free public capture/restarts match the same complete state and transaction traces, with exact pre-edge native readback. All 19 schedule rejections, four complete publication failures, unreachable schedules and an actual missing-callback executable fail closed with output preserved.
- Passed all 44 retained baseline and 15 final-source focused scopes, including 225 native/VPI ASan/UBSan collector rejections, native publication faults and repeated checks preserving 503 old fixture/log hashes/inodes, real-worker capture/publication acknowledgment guards, 142 native/VCS entry dispatch cases, ordinary clean RTL VCS, full M2/M3, public/restricted/legacy-live continuations and independent audits, repeated rejection checks, counters/profiling, lifecycle/bootstrap and full-size writer faults. Evidence: `automations/checkpoint_loop/runs/m4-iteration41/`; recovery details: [m4-public-capture-scheduling.md](m4-public-capture-scheduling.md).
- Corrected the second-process oracle: the sole difference was the eight historical wall-clock reporting timestamp bytes in `runtime/simulation/base`. The corrected verifier independently bounds that timestamp by the capture process wall times, compares every other canonical image byte and restores/readbacks every original native byte, including the timestamp, before any edge. All five cases were rerun in full; production capture/state code was unchanged. Initial captures/traces and diagnostic details are retained. Earlier source-stale executable audits and an overbroad native-repeat catalog that included mutable summary files are retained separately; all final scopes pass with current executables and all 503 immutable prior fixtures/logs preserved.
- Next: opt-in normal Make integration with complete generated inventory and the existing all-owner zero-edge restore coordinator. Plans remain read-only with initial hashes retained. No plan corrections, staging, commit/reset/clean, conda/PDF edits, physical FPGA, formal or ASIC validation.

Iteration 40 (October 9):

- Added `capture_durable_snapshot`, reusing the complete compiled generated/harness/native inventory. It reads every generated address and harness bank, validates and rereads all native payloads, requires known low clocks/reset/finish and binds FASED target cycle separately from host sample. Collection performs no native loads, VPI deposits, MMIO or simulation edges.
- Added the real-worker parked-cut guard, rejecting unsupported stream/QSFP/memory topology, and a verification-only native collection/publication DPI hook in the public restore capability. Public `+fs-checkpoint` remains fail closed. The full verifier compares each live published image byte-for-byte with the independent complete Python oracle and restores that actual file in a fresh VCS process.
- All five final-code live captures match every byte of the complete Python oracle; fresh public restores match 3,765,516 complete 40-port samples, including outstanding native/FASED writes, with full pre-edge readback and zero-edge bootstrap. The independent audit passes 68 processes, 67,537,280 generated-word and 85 native-owner comparisons, plus all five live publications. All 56 public restore rejection cases pass. Final source-bound evidence is under `live-capture-current` / `public-restore-current`.
- ASan/UBSan passes the complete live staging oracle and 225 native/VPI failure cases, preserving output sentinels. The actual pthread guard passes its parked cut, unsupported topology and three unchanged native-owner checks with no added edges. Native publication passes all 149 malformed snapshots, 11 syscall faults, four special destinations, three kills and 16 concurrent writers; repeating preserves all 503 earlier fixture/log inodes and hashes. All 11 actual-entry live request rejections and four complete live publication failures pass with preserved outputs and no crash dumps. All 44 baseline and 15 focused scopes pass, including ordinary clean RTL VCS, full M2/M3, full public/restricted continuations and independent audits, repeated rejection checks, counters/profiling, dispatcher lifecycle, full-size publication faults and actual-trace mismatch diagnostics. Evidence: `automations/checkpoint_loop/runs/m4-iteration40/`; recovery details: [m4-live-capture.md](m4-live-capture.md).
- Corrected the capture failure path to flush diagnostics and call `_Exit(1)`, avoiding the VCS crash dump produced by the generic restore failure helper at a parked capture. Current full public/live runs and all failure checks pass with this fix. Earlier `*-final` artifacts predate it and must not authorize final source-bound acceptance. Initial synthetic fixture errors, the missing local audit hash catalog and the expected rejection of a source-stale public executable are retained separately; the catalog was generated from the saved initial hashes and every unfinished scope rerun without reducing checks.
- Next: connect public capture scheduling and opt-in normal Make integration to this tested complete live collector/publisher and existing all-owner zero-edge restore contract. Both plans remain read-only with original hashes retained. No plan corrections, staging, commit/reset/clean, physical FPGA, formal or ASIC validation.

Iteration 39 (October 9):

- Added `encode_durable_capture` and `publish_durable_capture` for canonical complete v3 `FSAGG1` snapshots, using the compiled generated/harness/native inventory and the same durable-consumer validation. Encoding binds the actual executable, every generated word/address and padding bit, native membership/schema/opaque bytes, low generated clocks/reset/finish and the manifested target-cycle counter. It does not collect live state or establish the settled cut; those remain caller responsibilities. Native payload semantics still require all-owner validation before restore.
- Publication validates before any output access, pins the destination directory, rejects special destinations, writes a private exclusive temporary, handles interrupted/short writes, syncs the file, atomically replaces the destination and syncs the directory. Pre-rename failures preserve the destination; post-rename failures explicitly report visible replacement. Killed-writer pending files remain uncommitted. No public capture request has been enabled.
- Native ASan/UBSan passes exact Python container-byte comparison, 149 malformed-snapshot rejections (each also tested before output-directory access), 11 syscall failures, four special destinations, three killed-writer boundaries and 16 concurrent writers/readers. Repeating it preserves all 587 earlier fixture/log inodes and hashes. The full-size native encoder matches every byte of the 65,157,247-byte Python oracle with all 13,507,456 generated words, 29 harness records and 17 opaque native owners; five full-size syscall failures pass. Final review corrected a misleading zero-byte-write errno message; both native verifiers pass again with the final code. This standalone oracle does not establish live capture/restore.
- Both new public/restricted VCS runs pass five fresh continuations, each matching 3,765,516 complete 40-port samples with outstanding native/FASED writes, complete pre-edge readback and zero-edge bootstrap. Independent audits pass 68 public / 42 restricted processes and 67,537,280 generated-word / 85 native-owner comparisons per run. All 44 baseline scopes pass, including ordinary clean RTL VCS, full M2/M3, counters/profiling, rejection liveness, complete owner comparisons and dispatcher/aggregate/bootstrap/reservation checks. All 15 focused scopes pass, including repeated native/public rejections, 90 entry dispatch cases, runtime identity, all 16 retained publication failures, restricted public requests and both sets of four actual-trace mismatch diagnostics. Evidence: `automations/checkpoint_loop/runs/m4-iteration39/`; recovery details: [m4-native-capture-publication.md](m4-native-capture-publication.md).
- Next: connect complete live settled-cut capture to these APIs, then integrate the opt-in Make workflow and verify public capture/fresh restore without advancing target time. Both plans remain read-only with initial hashes retained. No proposed plan corrections, staging, commit/reset/clean, physical FPGA, formal or ASIC validation.

Iteration 38 (October 9):

- The previous failure was `FileExistsError` while recreating `durable-native-final/symlink`. Fixed both durable verifiers without deleting/following previous fixtures or reducing checks. Native special-file rejections now also prove the output sentinel remains unchanged. Added actual repeated native and public VCS verification commands with retained fixture/log paths.
- Native repeated verification passes two complete ASan/UBSan runs in the same output directory: 192 rejections and both independent Python staging comparisons; seeded old symlink/FIFO/directory and sentinel remain unchanged. The exact previously failing iteration-37 command also passes all 96 rejections. Both new public/restricted VCS runs pass all five continuations, each matching 3,765,516 complete 40-port samples, including outstanding writes, with complete pre-edge readback and zero-edge bootstrap. Independent audits pass 68 public / 42 restricted processes and 67,537,280 generated-word / 85 native-owner comparisons per run. Both repeated public invocations pass all 56 rejections and complete audits with unchanged checkpoint/executable hashes and retained old fixtures/special-file logs. All 49 Python tests, 90 entry dispatch cases, runtime identity checks, 16 full-size publication failures, 15 restricted public request rejections and both sets of four mismatch mutations pass. All 44 baseline scopes pass, including ordinary clean RTL VCS, full M2/M3, counters/profiling, rejection liveness, complete owner comparisons, dispatcher/aggregate audits and bootstrap/reservation sanitizers. Evidence: `automations/checkpoint_loop/runs/m4-iteration38/`; recovery commands and details: [m4-verification-reruns.md](m4-verification-reruns.md).
- Next: implement public capture publication and opt-in Make integration through the existing complete settled-cut/all-owner zero-edge contract. Both plans remain read-only, with initial hashes retained. No plan corrections, staging, commit/reset/clean, physical FPGA, formal or ASIC validation.

Iteration 37 (October 9):

- Added a compiled-in complete v3 durable inventory and C++ regular-file consumer with integrity/canonical encoding, exact executable/build, owner/shape/padding/low-clock and target-cycle checks. The public capability retains one validated file image, passes in-memory staging to all-owner native/VPI preparation, reserves fresh clocks and keeps public capture/private staging bypasses fail closed.
- The native consumer's staging is byte-identical to the independent Python format oracle. All 96 native ASan/UBSan corruption/type/build/membership/padding/special-file rejections, 90 actual-entry native/VCS dispatch cases, 49 Python tests and runtime identity sanitizers (41 rejections/12 ELF hash comparisons) pass. All five final public continuations preserve 13,507,456 generated words, 29 harness records and 17 native owners per cut, with full readback and zero-edge bootstrap; all 3,765,516 complete 40-port samples match, including outstanding native/FASED writes. The independent audit passes 68 processes, 67,537,280 generated-word and 85 native-owner comparisons, and all 56 public rejection cases. All 16 full-size publication failures and four actual-trace mismatch diagnostics pass. The restricted capability also passes all five continuations, its 42-process independent audit, 23 malformed loads, six compatibility changes and 15 public request rejections. All 44 retained baseline scopes pass, including ordinary clean RTL VCS, full M2/M3, counters, profiling, rejection liveness, complete low-clock comparisons and independent dispatcher/aggregate audits. A development build predates the final staging-file failure-poisoning correction and is retained separately; final evidence is under `public-restore-final`.
- Recovery details: [m4-public-durable-restore.md](m4-public-durable-restore.md). Logs/artifacts: `automations/checkpoint_loop/runs/m4-iteration37/`. Next: connect public capture publication and the opt-in build workflow, preserving the current compiled inventory, complete settled cut and all-owner zero-edge restore contract. Plans/conda/PDFs preserved without staging, commit/reset/clean; no physical FPGA/formal/ASIC validation.

Iteration 36 (October 9):

- Added typed public request parsing before capability/platform construction, rejecting empty/malformed/duplicate/conflicting options without file access. Base capability authorization denies durable requests; the restricted aggregate capability retains this default. Entry passes the parsed request to prepare, checks generated widget and concrete driver support, and enforces restore reservation/capture run actions before startup.
- All 90 actual-entry observer dispatch cases pass with native ASan/UBSan and VCS DPI, including unsupported/null/empty driver inventories, widget failures, capability failures and incorrect prepare actions. Missing enabled factories fail to link. Checkpoint inputs remain unchanged; no fixture publishes a checkpoint. These fixtures establish dispatch only, not generated-state restore. All 49 Python tests and runtime identity ASan/UBSan (41 rejections/12 ELF hash comparisons) pass.
- All 15 public request cases against the full generated production-entry VCS build reject before platform construction, without touching checkpoint files. All five fresh continuations match 3,765,516 complete 40-port samples, preserving 13,507,456 generated words, 29 harness records and 17 native owners per cut, including outstanding native/FASED writes, with full pre-edge readback and zero-edge bootstrap. All 23 malformed loads, six runtime compatibility changes and unsupported profiling reject without loading/advancing. The independent audit passes 42 processes, 67,537,280 generated-word and 85 native-owner comparisons. All 16 publication failures, four actual-trace mismatch mutations and all 44 retained baseline scopes pass, including ordinary clean RTL VCS, full M2/M3, counters, low-clock comparisons, dispatcher/bootstrap and the 100-process fixture aggregate audit. The baseline audit's initial missing hash-catalog setup diagnostic is retained separately; generating the expected catalog from saved initial hashes allowed every unfinished scope to pass without changing test scope. Dispatch cases were rerun after placing VCS working-directory diagnostics under their run directory. Details and recovery commands: [m4-public-entry-contract.md](m4-public-entry-contract.md). Logs and full-path artifact catalog: `automations/checkpoint_loop/runs/m4-iteration36/`.
- Next: implement the concrete public durable capability through this contract, preserving complete settled-cut state, all-owner prevalidation/readback and zero-edge bootstrap. Plans/conda/PDFs preserved without staging, commit/reset/clean; no physical FPGA/formal/ASIC validation.

Iteration 35 (October 9):

- Added opt-in `FS_CHECKPOINT_ENTRY` factory/prepare hooks around production construction/startup. The full FCFS/FASED aggregate verifier now compiles actual `entry.cc`, preserving one generated registry/platform/simulation and reserving restore before `run`. Factory exceptions/null capabilities exit explicitly; missing factories fail to link. Default builds retain fail-closed public checkpoint/restore requests.
- Corrected the existing DPI raw-pointer declaration of entry's `unique_ptr<simif_t>`: shared declaration, checked derived view and owner reset after worker join. The harness dispatcher fixture follows the same contract. Native build identity/audit binds actual entry and compile capability, checks construction/reservation order before loading, and retains all state/timing comparisons.
- All five fresh production-entry VCS continuations match all 3,765,516 complete 40-port samples, preserving every one of 13,507,456 generated words, 29 harness records and 17 native owners per cut, including outstanding native/FASED writes, with full pre-edge readback and zero-edge bootstrap. All 23 malformed loads, six runtime compatibility changes and unsupported profiling reject before loading/edges. The independent audit passes 42 processes, 67,537,280 generated-word and 85 native-owner comparisons. The 49 Python tests, 16 full-size publication failures, four actual-trace mismatch mutations and runtime identity ASan/UBSan (41 rejections/12 ELF comparisons) pass. All 44 baseline scopes pass, including ordinary clean RTL VCS, full M2/M3, native/VCS owners, profiling/counters, rejection liveness, full low-clock comparisons and dispatcher/aggregate audits. Initial Python indentation diagnostic is retained separately. Details and exact commands: [m4-production-entry.md](m4-production-entry.md). Logs and full-path artifact catalog: `automations/checkpoint_loop/runs/m4-iteration35/`.
- Next: connect durable capture/loading to the public production API through this capability. Plans/conda/PDFs preserved without staging, commit/reset/clean; no physical FPGA/formal/ASIC validation.

Iteration 34 (October 9):

- Added validated `publish_aggregate` APIs for both word/packed profiles and atomic staging publication: private same-directory temporary, file sync, atomic replace and directory sync. Pre-rename failures preserve the old destination; post-rename sync errors explicitly report a visible replacement with unconfirmed durability. Killed-writer pending files are not committed checkpoints. The production restart verifier reopens the durable container before fresh-process staging.
- All 49 Python tests and 16 full-size publication failures pass. Five fresh VCS continuations match all 3,765,516 complete 40-port samples, preserving 13,507,456 generated words and 17 native owners per cut, including outstanding native/FASED writes, with complete pre-edge readback and zero-edge bootstrap. The independent audit passes 42 processes, 67,537,280 generated-word and 85 native-owner comparisons. All 23 malformed loads, six compatibility changes and unsupported profiling reject before loading/edges. Four actual-trace mutations and runtime identity ASan/UBSan (41 rejections/12 hash checks) pass. All 44 baseline scopes pass, including 20 Scala tests, ordinary clean RTL VCS, full M2/M3, native/VCS owners, profiling/counters, rejection liveness, complete low-clock comparisons and bootstrap/aggregate audits. Initial runner/audit setup diagnostics are retained separately; the resumed runner executes every unfinished scope without reducing comparisons.
- Recovery details and exact commands: [m4-durable-publication.md](m4-durable-publication.md). Logs are under `automations/checkpoint_loop/runs/m4-iteration34/`. Next: integrate these durable APIs with production entry capture/loading. Plans/conda/PDFs preserved without staging, commit/reset/clean; no physical FPGA/formal/ASIC validation.

Iteration 33 (October 9):

- Added a `runtime/compatibility` owner binding explicit memory/horizon, effective host timing/seed, zero VCS initialization, and SHA-256 of the executable and every loaded file-backed ELF object. Membership/hashes are rechecked at the cut, native validation/readback and exit; unknown/duplicate arguments and preload/audit library hooks fail closed. Native ASan/UBSan passes 41 rejections and 12 independent ELF hash comparisons, including changed contents at the same library pathname. All 43 Python tests pass.
- The production v3 packed profile binds its target-cycle field to the manifested 64-bit FASED `model.tCycle`; host samples and driver operations have separate meanings. Container validation and compiled prepared-state validation reject mismatches before loading any owner. V1/v2 fixtures and Level-2 formats remain independent.
- Five final-implementation fresh VCS continuations match all 3,765,516 complete 40-port transaction samples at 774,628/774,632 target cycles, preserving all 13,507,456 generated words and 17 native owners per cut, including outstanding native/FASED writes. The independent audit passes 42 processes, 67,537,280 generated words and 85 native owners. All 23 malformed loads and six runtime compatibility changes reject before loading/edges; four actual-trace mutations report the expected first cycle/port mismatch. All 44 retained baseline scopes pass, including 43 Python/20 Scala tests, ordinary clean RTL VCS, full M2/M3, native/VCS owners, profiling/counter expectations, rejection liveness and complete low-clock comparisons/audits. Exact commands, logs and full-path artifact catalog are under `automations/checkpoint_loop/runs/m4-iteration33/`. The resumed verifier checks the same current executable/source binding and every completed continuation before rerunning all rejection/sanitizer scopes. Earlier trials and the initial memory-geometry diagnostic expectation failure are retained separately.
- Details and next steps: [m4-runtime-compatibility.md](m4-runtime-compatibility.md). Production durable plusargs remain disabled; no milestone acceptance is claimed yet. Plans/conda/PDFs are preserved without staging, commit/reset/clean; no physical FPGA/formal/ASIC validation.
- Recovery: iteration-29 `results.json` contains 36 completed baseline checks; its dispatcher result file adds five scopes and its fixture result file confirms three scopes already included in those 36. The previous iteration's exit came from a Codex service-access failure. The older "audits finishing" note below describes the interrupted turn, not a verification failure.

Iteration 29 (October 9):

- Added a manifest-bound v2 aggregate encoding with one record per generated entry, preserving every address and checking each word's nibble padding. The production inventory has 2,856 entries and 13,507,456 words; it retains all 29 harness records and 16 native owners, including four complete 4 MiB memory channels. Existing per-word fixture and Level-2 formats remain independent.
- Added a test entry using the actual generated registry, metasim platform, FCFS driver, MMIO, native memory, harness and dispatcher. Five fresh continuations match all 3,765,516 complete 40-port transaction samples through completion at cycles 774,628/774,632, including outstanding native/FASED writes, with complete pre-edge readback and zero-edge bootstrap. The independent audit checks 34 processes, 67,537,280 generated words and 80 native owners. All 21 malformed loads reject with zero native loads/deposits/edges; unaudited profiling callbacks fail closed. Compact staging passes 314 ASan/UBSan rejections. Four actual-trace mutations produce the expected first target-cycle/signal mismatch. No full production runtime acceptance is claimed.
- All 42 Python/20 Scala tests pass. Existing component, ordinary clean RTL VCS, full M2/M3, GCD, production capture/profiling/counter expectations and rejection-liveness checks pass; retained low-clock comparisons and full baseline artifact audits are finishing. Preserve interrupted development trials and the initial shared-build collision as separate diagnostics; rerun shared Make builds sequentially. Exact evidence is under `automations/checkpoint_loop/runs/m4-iteration29/`.
- Next: finish retained baseline audits, then integrate the durable aggregate path with production `entry.cc`, bind runtime configuration/libraries and the explicit target-cycle indexing contract, and retain fail-closed unsupported drivers. Details: [m4-production-aggregate.md](m4-production-aggregate.md). Plans/conda/PDFs remain untouched and unstaged; no commit/reset/clean or physical FPGA/formal/ASIC validation.

Iteration 28 (October 9):

- Added profile/generated/harness/native schema and implementation binding plus exact executable/checksum validation, complete generated/harness/opaque-native membership, distinct target-cycle/host-sample indexing, and a single locally validated aggregate staging file. Both complete VPI tables and every native payload validate before any owner loads; retained prepared values avoid component rereads. Native and RTL readback precede bootstrap; failed or misordered coordinator calls consume/poison the destination.
- Added fresh clock-hold reservation before state loading, allowing generated nets to settle without workers, MMIO, native ticks or rising edges. Five actual VCS aggregate fixture continuations match all 55 complete state/bank/output samples and 35 native comparisons before the first edge, preserving 539 generated words, 29 harness words, seven native owners, full 4 KiB memory, a partial write and two held reads. Terminal restore has zero edges. Seventy malformed-native/late-section/schema/order processes reject with zero loads/deposits and unchanged native owners. Twenty bootstrap lifecycle processes, 25 arming guards and 15 reservation guards pass. The independent audit checks 100 distinct simulator processes, all container records/build binding and operation/edge timing. ASan/UBSan reservation checks pass 58 rejections/18 unchanged owners with zero workers/edges; all 40 Python tests pass. Driver MMIO remains a fixture; no production restart acceptance is claimed.
- All 44 executed verification scopes pass, retaining all 41 previous scopes plus aggregate restore/audit and reservation sanitizers: 40 Python/20 Scala tests, all native/VCS owners, ordinary clean RTL VCS, full M2/M3, GCD/FASED, profiling, rejection liveness and nonempty hardware-counter expectations. Existing fresh harness continuations match 483,409 samples and pass all malformed/lifecycle/native guards. Five production low-clock cuts retain all 13,507,456 generated words and four complete 4 MiB channels; full 40-port traces match at 774,628/774,632 target cycles, including outstanding native/FASED traffic. Seven negative requests and terminal capture pass; the paired audit checks 80 software owners and 67,537,280 generated words. The separate active-gate terminal fixture retains exactly 12 host/12 target edges. Exact commands/logs/evidence and the full-path catalog are under `automations/checkpoint_loop/runs/m4-iteration28/`; initial failed diagnostics remain separate. Plans/conda/PDFs remain untouched and unstaged, with no commit/reset/clean.
- Next: bind every production FCFS/FASED owner into this aggregate path and compare a fresh full VCS metasim continuation with outstanding native/FASED traffic against uninterrupted target-visible outputs and transaction timing. Details: [m4-aggregate-prevalidation.md](m4-aggregate-prevalidation.md). No physical FPGA, formal or ASIC validation is claimed.

Iteration 27 (October 9):

- Added guarded component arming/resume, VCS clock hold during fresh load, shared actual DPI output publication and settled incoming-latch refresh before first-edge release. Ordinary/repeated startup and unsupported driver/topology/phase/mode reject; a failed bootstrap consumes/poisons its destination. Terminal bootstrap finishes with zero host/target/native edges.
- Actual harness/generated/native/DPI/dispatcher integration passes five fresh continuations and all 55 complete state/bank/output samples, with 35 native owner comparisons before the first edge. All 539 generated words, 29 harness words, complete 4 KiB memory, a partial native write and two held reads survive loading/bootstrap. Final native owners and remaining host/active target edges match uninterrupted execution. Independent operation oracle, 35 malformed-owner processes, 20 negative processes, 25 arming guards and a 65-process independent artifact audit pass. Separate ASan/UBSan poisoning checks pass 36 failed-bootstrap/fallback rejections and 30 unchanged-owner comparisons across six destinations with zero workers/edges. Driver MMIO remains a fixture; no full runtime acceptance is claimed.
- All 41 executed verification scopes pass, including all 29 baseline scopes, 37 Python/20 Scala tests, native ASan/UBSan/VCS owners, ordinary clean RTL VCS, full M2/M3, GCD/FASED, profiling, rejection liveness and nonempty hardware-counter expectations. Existing fresh harness continuations match 477,131 samples and pass 53 malformed loads, four lifecycle guards and all native guards. Five production low-clock cuts retain all 13,507,456 generated words and four complete 4 MiB channels; complete 40-port traces match at 774,628/774,632 default/randomized target cycles with outstanding native/FASED traffic. Seven negative requests and terminal capture pass; the paired audit passes 80 software-owner and 67,537,280 generated-word comparisons. The active-gate terminal fixture passes exactly 12 host/12 target edges. Exact commands, independent evidence and the full-path artifact catalog are under `automations/checkpoint_loop/runs/m4-iteration27/`. Failed initial trials remain separate; plans/conda/PDFs preserved without staging, commit/reset/clean.
- Next: bind/prevalidate/load every owner in one `.fsckpt`, integrate this handshake with the actual production driver, then compare fresh full VCS metasim with outstanding native/FASED traffic. Details: [m4-harness-dispatcher-integration.md](m4-harness-dispatcher-integration.md). No physical FPGA, formal or ASIC acceptance is claimed.

Iteration 26 (October 9):

- Added `start_restored_driver` with fresh-flow/concrete-owner validation, low-clock/reset/finish guards and explicit rejection of managed stream IO, QSFP and diagnostic/repeated starts. Bootstrap bypasses initial native advancement and initialization, returning at the next yield or completion. Ordinary startup refuses loaded flows. Condition-variable flags are updated under their owning mutexes; terminal zero-yield startup cannot deadlock.
- Actual pthread dispatcher passes 32 fresh native ASan/UBSan/VCS DPI continuations, 160 owner comparisons before the first edge, 64 unchanged native-owner comparisons through bootstrap, 352 lifecycle/phase rejections and ten malformed fresh loads with zero edges/publication. Every MMIO submission/native tick matches an independent oracle, including success/error/timeout and terminal zero-yield cuts. Queued MMIO, an in-flight two-beat native write, two held reads, model cycle and all 4 KiB functional memory survive bootstrap unchanged. Target MMIO/RTL services remain fixtures; no whole-runtime restart is claimed. The independent artifact audit confirms 288 MMIO calls and 32 distinct fresh processes.
- All 29 baseline regression scopes pass, including 37 Python/20 Scala tests, compiler codecs, every native/VCS owner, full M2/M3, ordinary clean RTL VCS, GCD/FASED, profiling, both rejection-liveness suites and hardware-counter expectations. Fresh actual harness/generated components match all 493,039 continuation samples and pass 53 malformed loads, four lifecycle guards and all native lifecycle/readback checks. All five low-clock cuts retain 13,507,456 generated words and four full 4 MiB channels; complete 40-port target traces match uninterrupted runs at 774,628/774,632 default/randomized cycles, including in-flight native/FASED traffic. Seven negative requests and terminal capture pass. The paired audit passes 80 software-owner and 67,537,280 generated-word comparisons, allowing only historical reporting timestamps and falling clock-gate outputs. The active-gate terminal fixture passes 12 host/12 generated-clock edges with no extra edge. Independent audits pass. Final logs/commands/full-path catalog are under `automations/checkpoint_loop/runs/m4-iteration26/`.
- Next: integrate actual DPI outgoing-bank publication/incoming-bank refresh with fresh harness/generated loading, then aggregate all owners in one `.fsckpt` and compare fresh full VCS metasim with outstanding native/FASED traffic. Details: [m4-dispatcher-bootstrap.md](m4-dispatcher-bootstrap.md). Plans/conda/PDFs preserved without staging, commit/reset/clean; no physical FPGA, formal or ASIC acceptance is claimed.

Iteration 25 (October 9):

- Added strict `+fs-driver-settled +fs-driver-lowclock`, native packed-clock validation and a natural falling-edge cut without an extra native tick, delay draw or rising target edge. After resuming the same dispatcher, outgoing banks settle and incoming latches refresh before the next rising tick. Low-clock completion cancels the pending rising edge. Harness loading binds the updated audited source; generated diagnostic phases cannot be mixed silently.
- All five low-clock cuts retain 13,507,456 generated words, all 27 harness banks/flags and four complete 4 MiB memory channels. Complete 40-port target traces and generated observations match uninterrupted execution at 774,628/774,632 default/randomized target cycles. Cut 699275 retains an in-flight native write at cycle 699360 and outstanding FASED traffic. The independent paired audit passes 80 software-owner and 67,537,280 generated-word comparisons: only historical reporting timestamps and two falling clock-gate outputs differ. Seven negative requests and terminal capture pass. Native ASan/UBSan passes 80 boundary/configuration/phase rejections. The actual-harness terminal fixture, with an enabled generated clock gate, passes exactly 12 host/12 generated-clock edges and no edge after completion.
- All 29 existing regression scopes pass, including 37 Python/20 Scala tests, compiler codecs, every native/VCS owner, full M2/M3, ordinary clean RTL VCS, production GCD/FASED, profiling, both rejection-liveness suites and hardware-counter expectations. Fresh actual harness/generated components match all 491,151 continuation samples, 29 banks/539 generated words before the first edge, 53 malformed loads and four lifecycle guards. Native harness checks pass 2,014 validation, 2,016 readback, 2,015 interruption and nine initialization/advancement rejections. Both full artifact audits and the paired-owner audit pass. Exact commands/logs/evidence and the full-path catalog are under `automations/checkpoint_loop/runs/m4-iteration25/`.
- Next: reconstruct the fresh dispatcher/DPI continuation at this precise pre-resume low-clock phase without ordinary initialization/MMIO or an extra native tick; bind/prevalidate/load every owner in one `.fsckpt`, then compare fresh full VCS metasim with outstanding native/FASED traffic. Details: [m4-lowclock-cut.md](m4-lowclock-cut.md). Plans/conda/PDFs preserved without staging, commit/reset/clean. No whole-runtime, physical FPGA, formal or ASIC acceptance is claimed.

Iteration 24 (October 9):

- Added `harness_restore.py`/`.cc` for all 27 incoming/outgoing/published packed banks plus reset/finish (4,108 bits in InventoryFixture), including unused optional banks. The exact audited top.sv, generated build and emitted headers bind geometry/ownership. Initialization at time zero arms a first-edge guard; all handle/type/width/value validation precedes deposits. Loads after an edge or previous load, reset/finished cuts and DEBUG/gate-level state reject; failed readback remains poisoned even after repair. The shared generated RTL loader retains its existing behavior.
- Actual unmodified harness + generated RTL fresh VCS continuations pass active/outstanding/held-response cuts at samples 16,610/371,744/380,580. All 29 banks and 539 generated words agree before the first edge; all 491,501 continuation state/bank/output samples agree. Native ASan/UBSan passes 2,014 validation/lifecycle rejections, 2,016 readback-fault and 2,015 clock-interruption checks, plus nine early-advancement/initialization checks in separate processes. VCS passes 53 unchanged-state/zero-edge malformed loads and four lifecycle guards, including a separate DEBUG build. The independent artifact audit passes. Native host outputs and finish remain recorded/replayed fixtures; no whole-runtime restart acceptance is claimed.
- All 29 existing regression scopes pass, including 37 Python/20 Scala tests, compiler codecs, every native/VCS owner, generated loading, full M2/M3, ordinary clean RTL VCS and production default/randomized GCD/FASED. All five settled cuts retain 13,507,456 generated words and four full 4 MiB memory channels; complete 40-port transaction traces match uninterrupted references at 774,628/774,632 default/randomized cycles. The late cut preserves in-flight native/FASED traffic. Profiled FCFS, both rejection-liveness suites and actual counter expectations pass. Existing generated-only fresh components match 525,519 samples. Both independent evidence audits pass. Final commands/logs and the artifact catalog are under `automations/checkpoint_loop/runs/m4-iteration24/`; failed initial trials remain separate diagnostics.
- Next: establish a coherent supported runtime phase and reconstruct parked driver/DPI continuation without an extra native tick or target edge, then prevalidate/load all owners in one `.fsckpt` and compare fresh full VCS metasim with outstanding native/FASED traffic. Low-clock harness component captures cannot be combined with existing rising-edge parked software diagnostics. Details: [m4-harness-bank-load.md](m4-harness-bank-load.md). Plans/conda/PDFs preserved without staging, commit/reset/clean. No physical FPGA, formal or ASIC acceptance is claimed.

Iteration 23 (October 9):

- Added `firesim.simulation.fcfs.v1` for `runtime/simulation`, binding ordered effective counter expectations, optional profile interval, PeekPoke and bridge/model identities/schemas, and complete model address maps. Step/finalization guards reject suspended/reentrant/interrupted operations; fresh loading validates before mutation without MMIO, file output or clock advancement. Live/repeated loads, finalized drivers, missing counters and bridge/model traversal changes reject. A separate adapter preserves the multiply inherited scheduler's independent virtual methods. Unknown drivers and profiling callbacks remain unsupported.
- Native ASan/UBSan and fresh VCS DPI component checks pass 46 every-operation/terminal success/error/timeout continuations, 138 owner comparisons before the first fixture edge, 296 MMIO calls against an independent oracle, eight malformed fresh restores without edges/trace publication, and 2,972 rejections per backend. Platform MMIO/target services remain fixtures; these are not whole-runtime restart acceptance. Failed initial trials remain separate diagnostics; final results are in `runs/m4-iteration23/fcfs-driver-verified/summary.json`.
- All 29 final verification scopes pass, including 35 Python/20 Scala tests, compiler codecs, every native/VCS component, full M2/M3, ordinary clean RTL VCS and default/randomized GCD. All five settled production cuts retain 13,507,456 generated words and four full 4 MiB memory channels; complete 40-port target traces and generated observations match uninterrupted references at 774,628/774,632 default/randomized cycles. The late cut retains an in-flight native write and FASED traffic. Profiled FCFS and both rejection-liveness suites pass. Fresh generated-RTL components match all 515,923 continuation samples. Actual nonempty counter expectations (writes 2,418, reads 7,582) pass: uninterrupted, early and terminal captures have identical full traces at their own 774,631-cycle configuration; unknown counters reject without publication. Error/success termination's one final-sample difference and a GCC ABI-tag symbol-match correction are documented as separate diagnostic trials. Independent evidence, exact commands/logs and the full-path artifact catalog are under `automations/checkpoint_loop/runs/m4-iteration23/`.
- Next: restore harness banks and reconstruct parked dispatcher/DPI continuation at a supported clock phase, then prevalidate/load all generated/software state in one `.fsckpt` and compare a fresh full VCS metasim with outstanding native/FASED traffic against uninterrupted target outputs/transaction timing. Details: [m4-fcfs-driver-state.md](m4-fcfs-driver-state.md). Plans/conda/PDFs preserved without staging, commit/reset/clean. No whole-runtime, physical FPGA, formal or ASIC acceptance is claimed.

Iteration 22 (October 8–9):

- Added `firesim.simulation.base.v1` under `runtime/simulation/base`, binding effective initialization/fingerprint/loadmem flags and ordered widget identity/schema, initialized/running phase, completed-step flag and performance baselines. Fresh-flow load has no MMIO, timestamp, output or clock effects. Resumed execution skips initialization; terminal cuts go directly to finalization. Suspended/reentrant/interrupted/completed flows and live/repeated loads reject. Concrete `runtime/simulation` remains unsupported; whole-runtime requests still fail closed.
- Actual base-flow native ASan/UBSan and fresh VCS DPI component tests pass 24 continuations/264 MMIO calls, 24 owner comparisons before the first fixture edge, 1,911 rejections per backend and eight malformed fresh loads with zero edges/output. Success/error/timeout and terminal cuts match an independent oracle. Platform clock/MMIO and concrete driver remain fixtures; this is not full FireSim restart. Historical wall-clock baselines are preserved for reporting; elapsed-time output is not deterministic across restart.
- All 26 regression scopes pass: the existing 25 plus generated RTL loading, including 35 Python/20 Scala tests, compiler codecs, native/VCS owners, full M2/M3, ordinary clean RTL VCS and default/randomized GCD. Production diagnostics independently bind the base configuration to widget order and compare its completed flag with the FASED run-loop, including terminal timeout capture. All five settled cuts retain 13,507,456 generated words and four full 4 MiB memory channels; complete 40-port AXI/FAME traces and generated observations match uninterrupted references. Default/randomized completion remains 774,628/774,632 cycles, with in-flight native/FASED traffic retained at the late cut. Profiled FCFS and both rejection-liveness suites pass. Generated-component loading passes all three fresh continuations (521,695 samples), 557 VCS and 333 native rejections. Exact logs/results/commands and artifact catalog are under `automations/checkpoint_loop/runs/m4-iteration22/`.
- Next: concrete FCFS driver configuration/finalization, harness banks and parked dispatcher/DPI continuation; supported runtime phase/cut; aggregate `.fsckpt` and fresh full VCS metasim continuation with outstanding native/FASED traffic. Details: [m4-simulation-base-state.md](m4-simulation-base-state.md). Plans/conda/PDFs preserved without staging, commit/reset/clean. No whole-runtime, physical FPGA, formal or ASIC acceptance is claimed.

Iteration 21 (October 8):

- Added `generated_restore.py`/`.cc`: exact compiled entry table, independently checked emitted RTL/BUFGCE build binding, ordered complete memory/register staging, and all-owner handle/type/width/value validation before any deposit. Inventories all emitted clock sensitivities; clocks must be known low before/after load. High BUFGCE payloads reject before mutation. A complete post-settlement readback is required before another load or edge; failure leaves the loader poisoned. VCS's scalarized `vpiReg` memory-word representation is audited at exact indexed paths, with bank depth/kind bound by declaration coverage.
- Actual uninterrupted InventoryFixture VCS metasim captures 426,421 host samples. Three fresh generated-hardware VCS processes restore active/outstanding/held-response cuts at 14,374/376,226/385,388 and match all 539 words (2,512 bits) before the first edge, then every generated state/top-output vector through 503,275 continuation samples. Host inputs are recorded/replayed; native owners, harness and driver stacks are not reconstructed. These are generated RTL component continuations, not `.fsckpt` or whole FireSim restart acceptance.
- Real VCS passes 557 malformed/missing/reordered/duplicate/header/bit/high-clock rejections with complete unchanged-state and zero-edge guards. Native ASan/UBSan passes 333 byte-truncation/handle/type/shape/clock/unverified/readback-failure rejections and independent 257-bit scalar/two-word 9-bit memory packing checks. The current Python suite passes 35 tests. Diagnostic trials are preserved separately; the expanded capture trial was interrupted in favor of an equally complete packed vector, and initial handle/native naming failures are not passing evidence.
- All 25 existing regression scopes pass, including 20 Scala tests, compiler codec/emitted-memory checks, every existing native/VCS owner continuation, full M2/M3, ordinary clean RTL VCS, default/randomized GCD, profiled FCFS and both rejection-liveness suites. All five production settled cuts retain 13,507,456 generated words and four complete 4 MiB memory channels; full 40-port AXI/FAME traces and generated observations match uninterrupted references byte-for-byte. Default completion remains 774,628 cycles; randomized completion is 774,632. The late cut preserves an in-flight native write and outstanding FASED traffic. Every VCS shell sources both environments then `vcs-env.sh` last, using Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`.
- Next: own simulation initialization/finalization and output history, restore harness banks and parked dispatcher/DPI continuation, establish a supported runtime phase/cut, then bind/prevalidate/load complete generated/software state in one `.fsckpt`. Compare a fresh full VCS metasim with outstanding native/FASED traffic against uninterrupted target outputs/transaction timing. Details: [m4-generated-rtl-load.md](m4-generated-rtl-load.md). Exact commands/logs/artifact catalog: `automations/checkpoint_loop/runs/m4-iteration21/`. Plans/conda/PDFs preserved without staging, commit/reset/clean. No plan correction, whole-runtime, physical FPGA, formal or ASIC acceptance is claimed.

Iteration 20 (October 8):

- Added `firesim.widget.cpu-managed-stream.v1`: engine index, AXI beat bytes, both ordered direction vectors, names/DMA/count addresses/capacities/stream widths and initialization state. Save/validate/load perform no I/O or clock advancement; validation precedes mutation. Push/pull/init/flush calls reject suspended/reentrant entry and poison interrupted operations. Existing ordinary call ordering is preserved. Generated FIFO/AXI state remains separately owned. Generic and FPGA-managed stream drivers remain unsupported.
- Native ASan/UBSan and fresh VCS DPI pass 144 component continuations/1,656 operations across three AXI beat widths, 144 owner comparisons before the first fixture edge, 2,154 rejection checks per backend/width and 42 malformed fresh restores before any edge/trace. Complete operation order, accepted bytes, caller buffers, queued payloads and lifecycle match an independent byte-queue oracle. These are host component continuations using fixture queues, not generated stream hardware or whole FireSim restart acceptance.
- All 25 regression commands pass: 31 current Python/20 Scala tests, compiler codec/emitted-memory checks, native/VCS host-owner continuations, generated inventory, ordinary clean RTL VCS, full M2/M3 and default/randomized GCD. All five production settled cuts retain 13,507,456 generated words and four full 4 MiB memory channels; complete 40-port target AXI/FAME traces and generated observations match uninterrupted references byte-for-byte. Default completion remains 774,628 cycles and randomized completion 774,632. Cut 699275 retains an in-flight native write and outstanding FASED target writes; all four legacy cuts and standalone capture retain hash `b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`. Profiling retains four samples at 774,629 cycles. Both three-case rejection-liveness suites pass. Stream adapters are linked in all four actual executables; these designs have no generated CPU-managed streams.
- The final evidence audit independently rechecks every component cut, full target trace and generated observation. Every VCS shell sources both environments then `vcs-env.sh` last: Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`. Both plans' hashes are unchanged; conda/PDFs preserved without staging, commit/reset/clean. Failed initial component trials remain in separate diagnostic directories. No plan correction proposed.
- Next: simulation initialization/finalization/output ownership; load harness banks and reconstruct parked dispatcher/DPI continuation before the next edge; bind/prevalidate/load complete generated/software state in one `.fsckpt`; restore a fresh VCS metasim and compare target outputs/transaction timing with outstanding traffic. Details: [m4-cpu-stream-state.md](m4-cpu-stream-state.md). Commands/logs/artifact catalog: `automations/checkpoint_loop/runs/m4-iteration20/`. No whole-runtime, physical FPGA, formal or ASIC acceptance is claimed.

Iteration 19 (October 8):

- Added `firesim.widget.fased.v1`: complete model/memory/MMIO/user configuration, lifecycle, all histogram baselines/range buffers and logical profiling history. Load validates/allocates before mutation and performs no MMIO, file I/O or clock advancement. The next ordinary profile/finish materializes restored history. Suspended/reentrant/interrupted calls, output failures and finished-output checkpointing reject explicitly. Range buffers now use RAII; fixed histogram/range helpers retaining a temporary constructor address map rather than the owned map.
- Native ASan/UBSan and fresh VCS DPI pass 40 FASED component continuations/120 operations, 40 owner comparisons before the first fixture edge, 1,128 rejections per backend and eight malformed fresh restores before any edge/trace. Complete bus order, payload bytes, profiling history, histogram deltas and range output match an independent oracle. These are host component continuations, not whole FireSim restart acceptance.
- All five full production settled cuts pass with six audited widget payloads, all 13,507,456 generated words and four complete 4 MiB memory channels. Default cuts 3/11/699275/699276 finish at 774,628 target cycles; randomized cut 101 finishes at 774,632. Complete 40-port AXI/FAME traces and generated observations match uninterrupted references byte-for-byte. Cut 699275 retains an in-flight native write and outstanding FASED target writes. Standalone/all four legacy captures preserve default hash `b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`.
- All 23 existing regression scopes pass, including 29 current Python/20 Scala tests, compiler codec/emitted-memory checks, native/VCS owners, full M2/M3, ordinary clean RTL VCS, default/randomized GCD and profiled FCFS (four samples, 774,629 cycles). Both three-case rejection-liveness suites pass. Actual generated constructors independently bind FASED payloads; unknown drivers remain unsupported. Full requests still reject the runtime cut before initialization. Current adapters are linked in all four actual executables.
- Every VCS shell sources both environments then `vcs-env.sh` last: Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`. Failed initial compilation and the sanitizer lifetime diagnostic remain in separate run directories. Plans/conda/PDFs preserved without staging, commit/reset/clean; no plan correction proposed.
- Next: stream adapters and simulation initialization/finalization/output ownership; load harness banks and parked dispatcher/DPI continuation before the next edge; bind/prevalidate/load complete generated/software state in one `.fsckpt`; restore a fresh VCS metasim and compare target outputs/transaction timing with outstanding traffic. Details: [m4-fased-host-state.md](m4-fased-host-state.md). Commands/logs/artifact catalog: `automations/checkpoint_loop/runs/m4-iteration19/`. No whole-runtime, physical FPGA, formal or ASIC acceptance is claimed.

Iteration 18 (October 8):

- Added adapters for master, clock, loadmem, reset pulse and peek/poke. Payloads bind complete MMIO/configuration/port maps; peek/poke retains both result flags and initializes them deterministically. Hooks issue no MMIO or clock edges. Suspended/reentrant calls reject; interrupted operations poison the owner. Internal file/write and step/poll ordering stays unchanged. GMP buffers release on success and exception paths.
- Native ASan/UBSan and fresh VCS DPI pass 52 concrete-widget component continuations/650 operations, 260 owner comparisons before the first fixture edge and 2,470 rejection checks per backend, against an independent MMIO/flags/configuration oracle. These checks use a platform/time fixture and do not establish whole-runtime restore. The final component run preserves every reference/cut/restore artifact.
- All five production settled cuts pass with the five audited widgets, all 13,507,456 generated words and four full 4 MiB memory channels. Default cuts 3/11/699275/699276 finish at 774,628 cycles; randomized cut 101 finishes at 774,632. Complete 40-port target AXI/FAME token traces and outstanding generated observations match uninterrupted references. Cut 699275 retains a native write at cycle 699360 and outstanding FASED target writes. Default generated captures retain hash `b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`.
- Independent generated-constructor checks bind captured payloads to actual registry pass order. FCFS supports widget/0 (master), /1 (loadmem), /3 (clock), /4 (reset), /5 (peek/poke); FASED widget/2 remains unsupported. Full FCFS requests reject it before initialization. InventoryFixture requests reject the unsupported runtime cut. Unknown drivers remain default unsupported.
- Passed 27 Python/20 Scala tests, compiler codec/emitted-memory checks, all existing native/VCS owner continuations, full M2/M3, clean RTL VCS, default/randomized GCD, standalone FASED, late native traffic and current widget-symbol linkage in all four actual executables. Profiled FCFS retains four samples at 774,629 cycles; all four legacy cuts and both three-case worker rejection-liveness suites pass. Every VCS shell sources both environments then `vcs-env.sh` last, retaining Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`.
- Next: audit FASED configuration/profiling/output lifecycle, streams and simulation initialization/finalization; restore harness banks and parked dispatcher/DPI continuation before the next edge; bind/prevalidate complete generated/software state as one `.fsckpt`; restore a fresh VCS metasim before target advancement and compare target outputs/transaction timing with outstanding traffic. Details: [m4-widget-state.md](m4-widget-state.md). Commands/logs/artifacts: `automations/checkpoint_loop/runs/m4-iteration18/`. Plans/conda/PDFs preserved without staging, commit/reset/clean. No whole-runtime, FPGA, formal or ASIC acceptance is claimed.

Iteration 17 (October 8):

- Added opt-in `+fs-driver-settled` to the existing completed-operation diagnostic. A dedicated driver/main-thread handoff returns through DPI, settles the current rising edge, reads generated RTL and software/harness state, then resumes the same dispatcher/DPI invocation and republishes final AXI outputs before the next edge. No extra AXI model tick, host-delay draw or clock edge is issued. Unsupported incremental drivers, backends and malformed requests fail explicitly.
- Added immutable `diagnostic/harness-banks` observation: all nine input sync records, nine output sync records, nine published output records, clock/reset/fin and debug count. Current FCFS width is 4,145 bits. This schema has no load adapter; `runtime/harness`, execution contexts, full simulation, generated RTL load and concrete widgets remain explicitly unsupported. Full `.fsckpt` requests still fail closed.
- Corrected full-scope VCS checks pass five settled operation cuts: default 3/11/699275/699276 at 774,628 target cycles and randomized cut 101 at 774,632. Every cut matches its uninterrupted timing configuration in complete 40-port target AXI/FAME token traces and outstanding generated-state observations. Each settled cut captures all 13,507,456 generated words and four full 4 MiB functional-memory channels. Cut 699275 retains a native write at cycle 699360 and outstanding FASED target writes. The standalone full FASED refresh and preflight/save/restore rejections pass; complete default generated captures retain SHA-256 `b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`. All five full target-port traces and three-stage generated observations are byte-identical to their uninterrupted references. The default trace contains 1,032,949 host-edge samples; the randomized trace contains 1,032,973. Final standalone FASED, late-traffic, symbol and plan-preservation checks pass.
- Native ASan/UBSan passes 65 diagnostic/configuration/suspended/reentrant/observation-load rejections. Three settled and three legacy rejection-liveness checks exit promptly without partial publication or overwriting existing diagnostics. Terminal dispatcher capture precedes normal timeout finalization.
- Existing full checks pass: 25 Python/20 Scala tests, compiler codecs/emitted-memory coverage, all native/VCS component continuations, all 539 InventoryFixture words, full M2/M3, ordinary clean RTL VCS, default/randomized GCD and profiled/unprofiled production FCFS/legacy diagnostics. The profiled run retains four samples and 774,629 target cycles. All verification runs use Y-2026.03-SP1, `-full64`, GCC/G++ 13, environments followed by `vcs-env.sh` last, and reused Make `VCS_FLAGS=-Mupdate`.
- Two superseded trials remain under runs: a 39-port parser trial was interrupted to include the final port; the first 40-port trial passed all default cuts but exposed an incorrect shared completion-count expectation (randomized polling finishes at 774,632). The corrected verifier reruns the full scope and compares each cut with an uninterrupted reference using identical timing arguments. No reduced-scope or superseded trial is counted as a completed verification.
- Next: audit concrete widget/bridge/stream and simulation-lifecycle owners; implement restorable harness and driver/DPI continuation phase; bind/prevalidate all generated/software state in one `.fsckpt`; load a fresh VCS metasim before target advancement and compare target outputs and transaction timing with outstanding traffic. Details: [m4-settled-boundaries.md](m4-settled-boundaries.md). Logs/commands/artifacts: `automations/checkpoint_loop/runs/m4-iteration17/`. Plans/conda/PDFs remain preserved without staging, commit/reset/clean. No whole-runtime, FPGA, formal or ASIC acceptance is claimed.

Iteration 16 (October 8):

- Exposed opt-in incremental driver dispatch/finalization through `simulation_t`; the production FCFS flow returns after each completed dispatcher operation and invokes a coordinator callback. All widgets, including stream engines, now have stable enumerable owner identities. Full simulation/widget/stream/harness/context ownership remains unsupported.
- Added strict `+fs-driver-cut=N +fs-driver-diagnostic=PATH` software diagnostics. The hook checks driver/DPI ownership, rejects MMIO/stream/RTL advancement during capture, saves/validates/rechecks every audited software owner before publication, and explicitly records missing/unsupported owners. Each cut retains all four 4 MiB functional-memory channels. These diagnostics have no whole-runtime restore path and are not `.fsckpt`.
- Native ASan/UBSan passes 47 configuration, malformed inventory, moving-owner, suspended/reentrant, partial-publication and destination rejections. Three production worker failures exit with status 1 in under one second without publishing/overwriting diagnostics. The negative profiling request exposed VCS exit-handler deadlock from driver-thread `std::exit()`; the corrected path flushes and uses `std::_Exit()`. Failed trials/logs remain under runs.
- Full existing regressions pass: 24 Python/20 Scala tests, compiler codec/corruption checks, all software-owner continuations, generated InventoryFixture coverage, full M2/M3, ordinary clean RTL VCS and default/randomized GCD metasim. Run-loop native/VCS retains 372 fresh component continuations/10,810 operations, 270 pending-credit cuts and all rejection guards. The full 10,000-transaction FCFS fuzzer retains 774,628 target cycles and complete outstanding-traffic hash `b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`; profiling retains four samples at 774,629 cycles. Both earlier-built fixture/M3 checks were refreshed, and the worker-failure fix was rebuilt into all four actual executables.
- Cut 699275 captures channel-0 functional-memory write progress at native cycle 699360, with issued scheduler credit 1,000,000 and zero suspended host-delay ticks. It reproduces the uninterrupted generated-state hash and completion count. All five cuts pass against the rebuilt binaries. Early cuts 3/11/101/10001 have empty native queues and preserve the same observations; all three negative production requests also pass. The first late trials had empty native queues because harness samples and native memory counters have different reset offsets. These are software diagnostic comparisons, not fresh-process aggregate restore acceptance.
- Next: use the callback for an explicit parked-driver/settled-harness handshake; inventory/save harness AXI banks, clock/reset/DPI phase; finish initialization/finalization and concrete widgets/bridge/stream adapters; bind all state to a manifest/build-bound `.fsckpt`; prevalidate and load a fresh VCS metasim before target advancement; compare target-visible outputs and transaction timing with outstanding traffic. Details: [m4-driver-boundaries.md](m4-driver-boundaries.md). Commands/logs: `automations/checkpoint_loop/runs/m4-iteration16/`. Every VCS shell sources both environments then `vcs-env.sh` last, using Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`. Plans/conda/PDFs preserved without staging, commit/reset/clean. No full Level-1, FPGA, formal or ASIC acceptance is claimed.

Iteration 15 (October 8):

- Added `firesim.stepped-run-loop.v1` to the production FCFS driver: explicit horizon/task/step/poll/individual-bridge/sample/completion phases, next bridge index and target done. Stable owner `runtime/simulation/fased-run-loop` is separately enumerable alongside scheduler components. The full `runtime/simulation` owner remains unsupported. Corrected the profiling interval's dangling reference capture. Payload validation/load rejects atomically; suspended/reentrant operations reject and interrupted operations poison the owner.
- Native ASan/UBSan and fresh VCS DPI pass 372 component continuations/10,810 operations against the former nested-loop operation order, including 270 cuts with pending credit. All three owners match before the first edge and at completion. Each backend passes 467 malformed-payload rejections without mutation, 17 interrupted phases and all suspended/reentrant access guards. Twenty malformed fresh restore processes reject before opening a trace/advancing an edge. These are driver/scheduler component tests, not target-cycle metasim restart acceptance.
- All existing regressions pass: 24 Python/20 Scala tests, compiler codec/corruption/emitted-memory checks, host timing 136 continuations/861,432 operations, scheduler 36/2,090, MMIO/memory 104/7,168 edges, memory-only 64/1,704 edges, all 539 InventoryFixture words, full M2/M3, ordinary clean RTL VCS and GCD metasim (12 target cycles, default and four timing/seed configurations; six invalid arguments reject). The full 10,000-transaction FCFS fuzzer passes at 774,628 target cycles and retains complete outstanding-traffic capture hash `b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`. A separate profiled FCFS run passes at 774,629 cycles with four samples, exercising the interval-lifetime fix under different scheduler pauses. Full checkpoint requests still reject `widget/0` before initialization and publish no incomplete checkpoint. New hooks are linked in all four actual metasim executables. Commands/logs: `automations/checkpoint_loop/runs/m4-iteration15/`; details: [m4-stepped-run-loop.md](m4-stepped-run-loop.md). Every VCS shell sources both environments then `vcs-env.sh` last; Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate` retained.
- Next: expose incremental driver dispatch to a coordinator, audit/park both contexts at a settled harness boundary and complete simulation initialization/finalization plus concrete driver/stream owners; coherently capture generated RTL, memory, AXI queues, timing, scheduler and drivers in a manifest/build-bound `.fsckpt`; prevalidate/load a fresh VCS metasim before target advancement and compare target outputs/transaction timing with outstanding traffic. `simulation_run()` still consumes the dispatcher synchronously; no whole-runtime request boundary or full driver has been declared supported. Plans/conda/PDFs preserved without staging, commit/reset/clean. No full Level-1, FPGA, formal or ASIC acceptance is claimed.

Iteration 14 (October 8):

- Added `firesim.host-timing.mt19937-64.libstdcxx.v1` to production metasim: full 312-word PRNG/index, full-width seed, configured maximum, selected delay and pending ticks. `advance_target()` uses explicit progress with the existing draw/commit order. Stable owner `runtime/host-timing` is separately enumerable. Parse/allocation precedes mutation; invalid configuration, payload geometry/progress and malformed state reject atomically. Strict unsigned argument parsing prevents modulo-zero/negative delays and seed truncation.
- Native ASan/UBSan and fresh VCS DPI pass 136 component continuations/861,432 delay and tick operations against an independent Python MT19937-64 oracle. All owner words match before the first edge and at completion; cuts include pending delays and immediately before/after engine wraparound. Per backend/configuration, 2,574 malformed payloads reject without mutation; 32 fresh malformed restore processes reject before any edge. Legacy-loop parity, suspended/reentrant callbacks, poisoned interrupted ticks, full-width seeds and maximum-delay checks also pass. These are component tests, not target-cycle metasim restart acceptance.
- All existing regressions pass: 24 Python/20 Scala tests, compiler codec/corruption/emitted-memory checks, scheduler 36 continuations/2,090 operations, MMIO/memory 104 continuations/7,168 edges, memory-only 64 continuations/1,704 edges, all 539 generated InventoryFixture words, full M2/M3 and ordinary clean RTL VCS. GCD passes at 12 target cycles with default and four explicit timing/seed configurations; six invalid timing arguments fail before initialization. The full 10,000-transaction FCFS fuzzer passes at 774,628 target cycles, retaining complete outstanding-traffic capture hash `b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`. New timing and existing scheduler symbols are linked in all four actual metasim executables. Every VCS shell sources both environments then vcs-env.sh last; Y-2026.03-SP1, `-full64`, GCC/G++ 13 and `VCS_FLAGS=-Mupdate` on reused Make builds are retained.
- Whole-runtime requests remain unsupported. The synchronous delay owner rejects access while `do_tick()` is suspended: capturing explicit pending ticks does not reconstruct a driver stack, caller buffers, harness or thread phase. No concrete driver is newly supported. Details: [m4-host-timing-state.md](m4-host-timing-state.md). Commands/logs: `automations/checkpoint_loop/runs/m4-iteration14/`.
- Next: explicit resumable production driver/main-loop boundaries, complete driver/runtime inventory and coherent freeze; capture RTL, memory, AXI queues, timing, scheduler and callbacks as one manifest/build-bound `.fsckpt`; prevalidate/load into fresh VCS metasim before target advancement and compare target outputs/transaction timing with outstanding memory traffic. Plans/conda/PDFs preserved without staging, commit/reset/clean. No full Level-1, FPGA, formal or ASIC acceptance is claimed.

Iteration 13 (October 8):

- Added `firesim.scheduler.deadlines.v1` to the production scheduler: full horizon/credit/current-cycle and ordered initial/next deadlines, with stable callback identities and separately enumerated audited callback owners. Anonymous callbacks remain unsupported. Parse/allocation precedes mutation; incompatible/malformed payloads reject atomically. Hooks reject suspended callbacks; callback failure, zero intervals and deadline overflow fail closed. Full-width unsigned horizon parsing and bounded credit addition prevent truncation/wraparound.
- Native ASan/UBSan and fresh VCS DPI processes pass 36 continuations/2,090 component operations against an independent Python credit/callback/byte oracle. Eighteen cuts cover before/after callbacks and credits, coincident deadlines and scheduling completion. All three owners reserialize identically before the first edge and at completion. 237 malformed payloads reject through both validate/load without mutation; additional anonymous/unaudited callback, identity/order/schema, reentrancy/failure and 64-bit horizon negatives pass. These are scheduler component tests, not target-cycle metasim restart acceptance.
- All regressions pass: 24 Python/20 Scala tests, compiler codec/corruption/emitted-memory checks, MMIO/memory 104 continuations/7,168 edges and memory-only 64 continuations/1,704 edges, all 539 generated InventoryFixture words, full M2 (5 cases/108 samples/1,404 comparisons plus negatives), full M3 (6 captures/547 stalls/5 semantic and 242 transfer replay samples/8 invalid reads), ordinary clean RTL VCS and GCD VCS metasim (12 target cycles). Full 10,000-transaction FCFS fuzzer passes at 774,628 target cycles; all three complete outstanding-traffic captures retain hash `b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`. Preflight/save/restore still reject `widget/0` before initialization and publish no incomplete checkpoint. New scheduler symbols are linked in all four actual metasim executables. Every VCS shell sources both environments then vcs-env.sh last, retaining Y-2026.03-SP1, `-full64`, GCC/G++ 13 and `VCS_FLAGS=-Mupdate` for reused Make builds.
- Scheduler `current_cycle` is issued credit, not proof of completed target execution. Production profiling closures, concrete driver progress and all remaining harness/PRNG/thread/stream/runtime owners still require audits and a coherent freeze. No production driver has been newly declared checkpointable. Details: [m4-scheduler-state.md](m4-scheduler-state.md). Commands/logs: `automations/checkpoint_loop/runs/m4-iteration13/`.
- Next: integrate complete runtime/driver ownership at resumable boundaries; coherently capture RTL, memory, AXI queues, scheduler and callback state; publish manifest/build-bound `.fsckpt`; prevalidate/load into a fresh VCS metasim before target advancement; compare target-visible outputs and transaction timing with outstanding memory traffic. Plans/conda/PDFs preserved without staging, commit/reset/clean. No full Level-1, FPGA, formal or ASIC acceptance is claimed.

Iteration 12 (October 8):

- Added audited `firesim.mmio.full.v1` with complete AR/AW/W/R/B queues, bus payloads, geometry and in-flight flags. Write/read payloads own their bytes; queued writes survive driver-buffer mutation/destruction. Narrow write padding, bus-width strobe masking and existing reset/handshake behavior are explicit. Legal W-before-AW and later buffered W during held B are preserved. Parse/allocation precedes load mutation, and malformed queue ordering/counts, shapes, flags, IDs, geometry, truncation and trailing bytes fail closed.
- Exposed `simif_emul_t::checkpoint_axi_owners()` with stable names for the MMIO, functional-memory and optional CPU/FPGA-managed AXI owners. This is a subset inventory; full driver preflight still rejects unaudited `widget/0`. Driver stacks, stream engines, harness latches/clock/reset, PRNG/pending delays, thread handoff and scheduler owners remain unaudited.
- New independent AXI/byte-scoreboard regression passes 104 fresh native ASan/UBSan and VCS DPI component continuations with 7,168 compared edges. Both transport and all functional-memory bytes/queues restore and reserialize before the first edge. Cuts include simultaneous read/write bursts, partial write acceptance and queued R/B responses. Per width, 593/637/901/1,252 malformed/mismatched payloads reject atomically; narrow/maximum bursts, pointer lifetime and 64-bit address/ID geometry checks also pass. These are component tests, not full metasim restart acceptance.
- All regressions pass: 24 Python/20 Scala tests, compiler codec/corruption/emitted-memory coverage, memory-owner 64 fresh continuations/1,704 edges, all 539 generated InventoryFixture words, full M2 (5 cases/108 samples/1,404 comparisons plus negatives), full M3 (6 captures/547 stalls/5 semantic and 242 transfer replay samples/8 invalid reads), ordinary clean RTL VCS and GCD VCS metasim (12 target cycles). Full 10,000-transaction FCFS fuzzer passes at 774,628 target cycles; all three complete outstanding-traffic captures retain iteration 11's hash `b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`. Preflight/save/restore requests still fail before driver initialization and publish no incomplete checkpoint. Every VCS shell sources both environments then vcs-env.sh last, using Y-2026.03-SP1, `-full64`, GCC/G++ 13 and `VCS_FLAGS=-Mupdate` on reused Make builds.
- Next: complete runtime/driver inventory and resumable driver boundaries, coherent freeze/capture of generated RTL plus all software/functional-memory owners, manifest/build-bound `.fsckpt`, and fully prevalidated fresh-process VCS metasim load before target advancement. Compare target outputs and transaction timing with outstanding memory traffic. Details: [m4-mmio-runtime.md](m4-mmio-runtime.md). Diagnostic logs/commands: `automations/checkpoint_loop/runs/m4-iteration12/`. Plans/conda/PDFs preserved without staging, commit/reset/clean. No full Level-1, FPGA, formal or ASIC acceptance is claimed.

Iteration 11 (October 8):

- Actual FASED exposed FIRRTL emitter-created synchronous RAM state. Added an exact emitted-memory pipeline adapter for supported read-address/read-data and read/write-data registers without changing RTL or semantic IDs. Complex unhandled pipelines still fail closed. Five actual compiler fixtures independently match emitted declarations and shapes; all 20 Scala and 24 Python tests pass.
- Built the production 10,000-transaction AXI4Fuzzer with the host FCFS timing-model fragment (`FCFS16GBQuadRank_DefaultF1Config`). Independent emitted coverage matches all 513 instances, 2,856 entries, 13,507,456 words and 103,083,035 bits; FASED contributes 429 entries/2,751 words, including all 32 bank trackers and both synchronous read pipeline registers. Entry-based JSONL capture retains every generated RAM word, including the full target scoreboard, without expanding the probe into millions of ports.
- Actual VCS metasim passes after 774,628 target cycles. Three complete captures at host samples 699355/699368/699369 contain outstanding host/target reads, writes and overlapping target traffic; emitted AXI handshake bindings verify the diagnostic counter roles. All preflight/save/restore requests reject `widget/0` before driver initialization and publish no incomplete checkpoint. These are generated-state diagnostics, not `.fsckpt`, whole-runtime cuts or fresh-process Level-1 restores.
- All regressions pass: functional memory retains 64 fresh continuations/1,704 compared edges with ASan/UBSan and malformed-owner rejection; M2 retains all five cases/108 samples/1,404 comparisons and negative checks; M3 retains six byte-identical captures, 547 stalled boundaries, 5 semantic/242 transfer replay samples and eight invalid reads. Compiler codecs, all 539 generated InventoryFixture words, ordinary clean RTL VCS and GCD VCS metasim (12 target cycles) pass. Two full FCFS fuzzer runs produce the identical complete capture hash. Diagnostic commands/logs are under `automations/checkpoint_loop/runs/m4-iteration11/`; every VCS shell sources both environments, then vcs-env.sh last, using Y-2026.03-SP1, `-full64`, GCC/G++ 13 and `VCS_FLAGS=-Mupdate` for reused builds.
- Next: enumerate/integrate runtime MMIO/stream/memory/harness/PRNG/thread/scheduler owners and audited driver adapters; coordinate FASED and full functional-memory capture at a coherent freeze; bind a complete `.fsckpt` to manifests/builds; prevalidate every owner/RTL handle, then restore into fresh VCS metasim before target advancement and compare target outputs/transaction timing with outstanding traffic. No full Level-1 continuation, FPGA, formal or ASIC acceptance is claimed. Details: [m4-fased-state-capture.md](m4-fased-state-capture.md). Plans/conda/PDFs were preserved without staging, commit/reset/clean.

Iteration 10 (October 8):

- Added the audited `mm_magic_t` full-memory checkpoint owner: all DRAM bytes, pending read data/IDs/last flags, write-response IDs, active burst progress, idle data and cycle counter. Schema/geometry/structural validation precedes any mutation; default `mm_t` hooks remain unsupported. Initialized dormant state and corrected a 32-bit write-strobe shift exposed by wide-memory tests, preserving reset and AXI edge semantics.
- Actual production memory code passes ASan/UBSan and fresh VCS DPI continuation at eight cuts across four beat widths, including partial/narrow writes, held/queued responses and reset with an outstanding write: 64 continuations and 1,704 identical model edges against an independent byte/AXI scoreboard. Each snapshot and final owner is byte-identical. Every truncated prefix and malformed/mismatched payload rejects atomically (4,433/4,473/4,713/5,033 cases per width); unaudited/uninitialized owners fail closed. These `.owner` sections are not full `.fsckpt` files and these model edges are not certified target-cycle cuts.
- Corrected verification's stale VCS external-C cache handling using recorded source/header dependencies; actual memory-header consumers are rebuilt. Passed 22 Python tests, 19 Scala inventory/stage tests (after creating the initially missing artifact directory), compiler codec/corruption checks, ordinary clean InventoryDUT VCS, generated RTL capture and all three unsupported-driver requests. Full M2 passes all five fresh processes (108 samples/1,404 comparisons), mismatch and restore-negative tests. Full M3 passes six byte-identical captures, 547 stalled boundaries, 5 semantic/242 transfer-edge replay samples and eight invalid reads. GCD VCS metasim passes after 12 target cycles. Every VCS shell sources both environments then vcs-env.sh last, using Y-2026.03-SP1, `-full64`, GCC/G++ 13 and `VCS_FLAGS=-Mupdate` for reused Make builds.
- Next: actual FASED inventory/capture; integrate memory-owner enumeration with MMIO/stream/harness/PRNG/scheduler and audited driver adapters; establish a coherent cut, complete manifest-bound `.fsckpt`, prevalidated fresh-process load before target advancement, and target-visible output/transaction-timing comparison with outstanding memory traffic. No full Level-1, FASED, FPGA, formal or ASIC acceptance is claimed. Details: [m4-functional-memory.md](m4-functional-memory.md). Evidence: `automations/checkpoint_loop/runs/m4-iteration10/`. Plans/conda/PDFs were preserved without staging, commit/reset/clean.

Iteration 9 (October 8):

- Added opt-in post-emitter-lowering Level-1 inventory at the explicit FPGATop metasim root, separate from semantic StateIDs/manifests. Final instance connectors, registers, logical memories and explicit memory pipeline registers are covered. Opaque/unresolved/async/implicit-pipeline state fails explicitly. Exact AbstractClockGate and hash-bound metasim BUFGCE adapters account for stored clock-model state.
- InventoryFixture has 529 entries, 539 words, 2,512 bits and 83 instances: transformed DUT/SRAM/in-flight operation, FAME progress, LI-BDN queues, bridge/counter/control/interconnect state. Independent emitted RTL declaration coverage agrees exactly. VCS captures all words at active, queued/outstanding and held-response points. These are generated RTL diagnostics at host samples, not complete `.fsckpt` files or certified target-cycle cuts.
- Added default-unsupported software schema/save/validate/load hooks for widgets and stream engines and deterministic registry ownership. Real VCS preflight/save/restore requests exit 1 before driver initialization, identify unsupported widget/0 and publish no incomplete checkpoint. The metasim runtime cut also remains explicitly unsupported.
- Passed 22 Python tests, 19 Scala inventory/stage tests, compiler manifest/codec corruption checks, ordinary clean InventoryDUT VCS and GCD VCS metasim. Full M2 passes all five fresh-process cases (108 samples/1,404 comparisons) plus mismatch and restore-negative tests. Full M3 passes six byte-identical hardware/oracle captures, 547 stalled boundaries, 5 semantic/242 transfer-edge replay samples and eight invalid client reads. All VCS shells source both environments then vcs-env.sh last; Y-2026.03-SP1, `-full64`, GCC/G++ 13, `VCS_FLAGS=-Mupdate` for reused Make builds.
- Next: audited driver/runtime/transport/harness/PRNG/scheduler adapters; full `mm_t` functional DRAM plus `mm_magic_t` burst and response queues; actual FASED inventory/capture; atomic consistent cut, complete manifest-bound `.fsckpt`, prevalidated fresh-process load before target time, and target-visible output/transaction timing comparison with outstanding traffic. No full Level-1 continuation, FASED, FPGA, formal or ASIC validation is claimed. Plans/conda/PDFs were preserved without staging, commit/reset/clean. Details: [m4-generated-state-inventory.md](m4-generated-state-inventory.md). Evidence is under `automations/checkpoint_loop/runs/m4-iteration9/`.

Iteration 8 (October 8):

- Implemented synthesizable StateID-ordered register/logical-memory access, a two-entry FIFO, atomic freeze through final consumption, separate control reset, and explicit command/busy/bank errors. The four-bank InventoryBankedFixture holds all 22 semantic words, including SRAM writes and synchronous resets, while the controller progresses outside the semantic root. Functional reset edges retain M2 target-cycle indices; transfer edges never advance semantic time.
- Added compiler-checked explicit bank bindings and a manifest-hashed access sidecar. Omitted/added/reordered/reshaped/ambiguous state fails before emission. The host serializer requires exact ordered membership, widths, logical addresses and final marker, and refuses errored/incomplete captures. No hardware collector uses direct DUT simulator readout; the separate VCS bind is an independent oracle.
- Passed 19 Python tests, 15 Scala inventory/stage tests, compiler manifest/codec corruption checks, original M2's five fresh VCS replay cases and negative tests, ordinary clean InventoryDUT VCS, and GCD VCS metasim. M3 metasim/clean RTL acceptance also passes: six 22-word captures are byte-identical to the independent backdoor oracle at semantic cycles 13, 13, 15, 16, 18 and 22, with 547 stalled transfer boundaries; the bank-fault capture is rejected. Fresh VCS processes replay the unmodified hardware checkpoint for C=18..22 (75 output comparisons), plus all 242 transfer boundaries (3,630 comparisons), and reject eight invalid bank/slot/address selectors. Evidence is under `automations/checkpoint_loop/runs/m3-iteration8/acceptance/`. Every VCS shell sources both repository environments, then vcs-env.sh last; Y-2026.03-SP1, `-full64`, GCC/G++ 13.
- Explicit clients cover the small DUT; automatic compiler insertion/general FAME mapping, synchronous RAM pipelines and Rocket/BOOM are unsupported. CheckpointBridge/DMA is M5. No physical FPGA, Level-1 continuation, formal/ASIC activity or power validation is claimed. Plans and conda/PDF files were preserved without staging, commit, reset or git cleaning. Details and reproduction: [m3-banked-state-access.md](m3-banked-state-access.md).

Iteration 7 (October 8):

- Implemented VCS Level-2 backdoor capture on actual gated DUT rising edges, before sequential updates, with complete StateID-bound registers/memory contents and all target boundary I/O. Compiler emits DUT-only ordinary RTL and a boundary manifest from the exact pre-FAME IR. Unsupported identity mappings (lost/extra/renamed/reshaped/threaded state, multiple DUT instances) fail explicitly. Level-1 checkpoints remain independent.
- Extended InventoryFixture with a request queue, two-cycle memory operation, and held response. Five fresh ordinary clean RTL VCS processes restore checkpoints at reset C=0, active/write C=5, queued C=22, outstanding C=24, and stalled-response C=26. All 108 sampled target cycles and 1,404 output comparisons match; each process verifies all 22 restored semantic words before its first edge and writes a VCD. Capture records 37 DUT edges (0..36); bridge reports 38. Independent reset/counter checks establish indices without using PeekPoke's unstable reads.
- A checksummed trace error reports `FIRST_MISMATCH cycle=29 signal=io_respData expected=102 actual=103` and exits 1. VCS initially returned zero after `$fatal`; added explicit DPI failure exit. Missing/reshaped handles, malformed restore data, and incomplete deposits exit 1 before modifying state. Integrity/build/manifest/completeness checks precede replay generation. No DUT reset or draining is required at the in-flight checkpoints.
- Passed 14 Scala inventory/stage tests and 15 Python container/semantic/replay tests with no skips, the manifest codec verification, ordinary InventoryDUT VCS regression, and GCD VCS metasim regression. Every VCS shell sources both repository environments, then vcs-env.sh last; release Y-2026.03-SP1, `-full64`, GCC/G++ 13. Acceptance script rebuilds/runs all five cases and negative tests. Diagnostics are under `automations/checkpoint_loop/runs/m2-iteration7/`; details and reproduction: [m2-semantic-vcs-replay.md](m2-semantic-vcs-replay.md).
- Scope is the hierarchy-preserving small DUT and its explicit memory pipeline. Rocket/BOOM, general FAME renaming/threading mappings, physical FPGA capture, Level-1 continuation, formal/ASIC activity, and power are unvalidated. Next milestone M3: synthesizable extraction, checked through metasim without claiming physical FPGA validation. Plans, conda files, loop code, and PDFs were preserved; no staging, commit, reset, or cleaning performed.

Iteration 6 (October 8):

- Completed the previously blocked checks using VCS Y-2026.03-SP1, `-full64`, and GCC/G++ 13. Every VCS shell sourced Chipyard env.sh, FireSim env.sh, then vcs-env.sh last. Ordinary clean InventoryDUT RTL compiled and simulated successfully. InventoryFixture VCS metasim passed after 22 cycles reported by the fastest clock bridge (the driver requests five reset steps plus 16 explicit steps); GCD passed after 12 cycles. M2 must explicitly align bridge counts with checkpoint edge indices. Logs are under `automations/checkpoint_loop/runs/m1-iteration6/`.
- Fixed four reset checks in `TestInventoryFixture.cc`: `expect("signal", 0)` selected `expect(bool, const char *)`, silently skipping signal reads. Explicit `std::string_view` arguments select the signal-value overload. The rebuilt fixture logged 84 actual signal comparisons, including all four reset reads and all eight SRAM addresses, with no failed expectations. The driver syntax check also passed. PeekPoke emits its existing global unstable-value warnings; this run checks observed fixture values, and does not establish settled trace boundaries or checkpoint replay. Resolve precise boundary sampling in M2.
- Reran all 14 Scala inventory/stage tests and all 10 Python format/semantic tests; none skipped. Both actual eight-entry compiler manifests agree with Python's canonical encoding and reference hashes. Seeded `.rtlckpt` files round-trip bit-exactly and reject all 10,920 (InventoryDUT) / 11,152 (InventoryFixture) single-bit corruptions, plus omitted state with a valid checksum. Independent `.fsckpt` and `.trace` round trips and build/type/version rejection tests passed. The three Make verilog targets remain up to date; this iteration reused the full compiler outputs from iteration 5.
- Implementation remains opt-in at the resolved pre-FAME boundary, with instance-qualified StateIDs, complete manifest-bound semantic validation, separate versioned containers, SHA-256 integrity and build compatibility, and explicit unsupported-state failures. Level-1 ownership/capture, trace boundary completeness, state mapping through FAME, extraction, restore, and replay are later milestones. Artifacts contain seeded test data; no captured checkpoint, ASIC activity, formal proof, or FPGA validation is claimed.
- Plans were read and their SHA-256 snapshots rechecked without modification; all pre-existing dirty environment, loop, and plan files were preserved. No commit, staging, reset, or cleaning performed. Reproduction commands and artifact paths: [m1-state-inventory.md](m1-state-inventory.md).
- Next milestone M2: capture semantic values and a complete target-boundary trace in VCS metasim, restore into clean RTL VCS, and verify exact finite target-cycle replay. Keep Level-1 simulator checkpoints independent.

Environment recovery after iteration 5 (October 8):

- `vcs-env.sh` now sources `/ecad/tools/vlsi.bashrc`, which includes the reachable `1709@flex-lic.millennium.berkeley.edu` Synopsys server. The previous `~/flexlm.sh` listed only BWRC servers that failed connection checks. The helper pins VCS Y-2026.03-SP1 and system GCC/G++ 13, including wrappers for VCS's internal compiler/linker calls. Conda GCC 15 reproduces the implicit-declaration error in the older release's generated `rmapats.c`; GCC 13 compiles the same file successfully.
- The loop's `checkpoint` permission profile retains `:workspace` filesystem restrictions and enables outbound networking. The original agent sandbox denied license-server connections even when the server was up. A license query and actual runtime checkout passed inside the updated profile.
- Clean InventoryDUT RTL compiled and simulated successfully with Y-2026.03-SP1 and GCC 13. The bench passed registers, FSM, array, repeated instances, and SRAM checks. GCD `make run-vcs` also built and ran successfully inside the updated sandbox and reported PASS after 12 target cycles; `VCS_FLAGS=-Mupdate` refreshed cached build metadata from the older release. Logs: `runs/vcs-y2026-gcc13-check/compile.log`, `run.log`, and `gcd-metasim.log`. The eight loop tests and dry run passed. The saved state is unchanged; resume the loop for complete M1 verification, including InventoryFixture metasim and later checkpoint/replay work.

Iteration 5 report (before environment recovery):

- Added opt-in `--semantic-checkpoint-root Top.dut` at GoldenGateCompilerPhase.loweredTarget, before MidasTransforms. Emits a deterministic, instance-qualified manifest and the uninstrumented lowered reference. IDs hash canonical pre-FAME hierarchy/kind/namespace; arrays become lowered scalar members. The dependency-based FIRRTL compiler leaves the legacy form field unchanged, so the known lowering boundary is explicitly marked LowForm.
- Rejects opaque modules, non-bit/unresolved state, async resets, derived/gated clocks, multiple target clock domains, and memory pipelines not inventoried (read latency != 0, write latency != 1, readwrite ports). No ports/instrumentation added; no mapping through FAME or capture backend yet.
- Added manifest-bound encode_semantic/decode_semantic requiring manifest hash and exact complete record membership/width/depth. Existing low-level codecs remain independent format utilities. Added mandatory simulator_build_hash to .fsckpt compatibility; .rtlckpt/.trace remain independent of simulator/Golden Gate build identity.
- Fixed discovery of conditional Chisel SRAM writes: resolve combinational clock/enable nodes and `mux(enable, 1, 0)` only when the `validif` clock guard has exactly the port enable's Boolean identity. Added direct/node-aliased positive tests and unrelated-guard/conditional-register-clock/delayed-enable negative tests. Register next-state drivers are never treated as aliases of stored values. Derived/gated clocks still fail explicitly.
- Added synthesizable InventoryFixture DUT/harness and a target-cycle C++ driver exercising the counter, FSM, three array members, repeated leaf registers, and every SRAM word. Driver syntax check and full Golden Gate compilation passed. Make's opt-in SEMANTIC_CHECKPOINT_ROOT requests the manifest/reference sidecars and recompiles existing opt-out builds with missing sidecars; this was exercised on GCD.
- Actually passed this iteration: 14 Scala tests (inventory + stage suites), 10 Python tests (all three formats, corruption/truncation/build compatibility/wide values, semantic completeness), and cross-language checks of both actual eight-entry manifests. Seeded .rtlckpt files round-trip bit-exactly and reject every single-bit corruption (10,920 for InventoryDUT, 11,152 for InventoryFixture with its configuration label). Seeded .fsckpt/.trace round-trips passed. These values are test data, not captured execution.
- Refreshed full GCD compilation with discovery disabled/enabled and verified that Make/CLI manifests match exactly: nine DUT registers, bridge exclusion, canonical serialization, reference hashes. Key files are in runs/m1-inventory, runs/m1-metasim/f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config, and runs/m1-gcd-inventory. All paths are beneath automations/checkpoint_loop; report individual nonempty files, since the loop rejects directory artifacts.
- Sourced env.sh, sims/firesim/env.sh, then vcs-env.sh LAST for every VCS shell. The clean RTL build reports Y-2026.03-SP1_Full64 and exits 255: "Server node is down or not responding" / "Failed to obtain license". InventoryFixture and GCD metasim reach the same license queue and time out after 90 seconds each (exit 124). Missing dependency: a reachable Synopsys VCS license service permitting this release's compilation/runtime checkout. Logs: m1-clean-vcs-build.log, m1-fixture-vcs.log, m1-metasim-vcs-build.log. No VCS simulation, capture/restore, replay, formal, ASIC activity, or FPGA validation claimed.
- Next: retry clean RTL VCS and both VCS metasim tests once license access works. Level-1 ownership and trace boundary completeness validation remain outstanding; low-level codecs do not establish capture completeness. Commands and current scope: [m1-state-inventory.md](m1-state-inventory.md). Plans, loop code, conda files, and PDFs were not edited/staged by this iteration; no commit/reset/clean performed. Tests/builds/checks have separate logs under runs; whitespace check produces a nonempty success log.

Previous M0 context (source reconnaissance complete):

- Created the previously missing reconnaissance.md with 119 checked source links, current revisions, compiler pass order, an explicit post-target-lowering/pre-MidasTransforms StateID hook, GCD instance/register trace, and the known Level-1 RTL/software/transport owners.
- Documented exclusions: FAME5 missing rename handling, optional RAM replacement, opaque sequential state, unsupported clock/reset semantics, partitioned systems, unsaved drivers/external inputs and incomplete capture cuts. These are requirements for future rejection, not implemented checkpoint support.
- Verified documentation/source anchors, tool entry paths and the GCD VCS metasim make recipe with `make -n`. VCS identification succeeded using -full64 and the existing conda library path. Jasper identification succeeded using -allow_unsupported_OS. Logs are in verification.log.
- No RTL/compiler implementation changed. No metasim or clean-RTL execution, checkpoint/replay, license checkout, formal proof, ASIC power or FPGA validation was performed. M0's checks are source reconnaissance checks.
- Existing dirty conda/checkpoint-loop files and untracked plans/PDFs were preserved. No commit/reset/clean was performed.

Later: investigate the discarded host-lowering return value before depending on HostTransforms. M2 uses VCS metasim and ordinary clean RTL VCS; keep Level 1 and Level 2 independent. Unsupported/lost mappings must fail explicitly when capture instrumentation is introduced.

Environment note: Chipyard HEAD changed externally during M0 from f0914763d010669c2b194c7fcd6fd8290ba21750 to a6295df2d9e691aa115f5409ec4bfbfe6b5ed80b (test acct). Initial dirty files disappeared from status; this agent did not edit or commit them. FireSim HEAD stayed 2650ce60df882c32c18008357839c1856490a87c.
