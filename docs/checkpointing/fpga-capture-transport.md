# FPGA capture transport component

Iteration 202 preserves two additional explicit compiler-context contracts:
consumed AddCircuit/FirrtlFile and GetIncludes/InputAnnotationFile events, and
global channel clock-frequency metadata. Every event producer/type/path and
channel name/clock label/unreduced positive ratio is retained and hash-bound.
Deleted owners, nested wrappers, unknown/mismatched producers, live input files,
malformed ratios and duplicate metadata reject. Final emission independently
checks the context in both the bank state and returned emitted annotations;
changed/dropped events or frequencies cannot hide behind an old sidecar.
These global frequency labels do not establish physical clock-owner coverage.
Actual exact-Rocket production preflight rejects **8 annotation classes**,
down from 10, and emits no accepted whole-Rocket bank RTL.

All **130 Scala / 306 checkpoint Python / 40 loop tests** and the full retained
EDA ASan/UBSan/FCFS/bank/bridge/host scope pass. Native localhost Vivado 2025.2
bank and MMIO/DMA-top OOC synthesis pass; bank use is 125 LUTs / 82 registers,
estimated setup +6.435 ns / hold +0.054 ns at 140 MHz, with external I/O
unconstrained. Matching VCS passes 4,669 bank / 7,858 exact-native-top /
21,970 synchronous-policy checks with debug waveforms. Independent EDA auditing
matches ten generated files / nineteen sources and rejects 26 coherently
rehashed context corruptions (16 new consumed-input/clock cases), plus all six
XDC, five memory-policy and eight target-box corruptions. Commands and individual
receipts: `runs/aws-f2/iteration202/summary.json` relative to the loop.

This is compiler/component evidence. The remaining contracts are DedupedResult,
RunFirrtlTransformAnnotation, FirrtlCircuitAnnotation, UnrecognizedAnnotation,
BridgeExtraction$BridgeInstance, BlackBoxInlineAnno, PreLinkRenamingAnnotation
and GoldenGateOutputFileAnnotation. Three physical BUFGCE owners, complete
common-cut/memory/timing/bridge/host/pre-FAME integration, full image/P&R/AFI,
all-hart early/warm/outstanding/late FPGA cuts, paired CPU zero-edge restores,
finite replay, sustained live RTL beyond the trace window and rolling hardware
recovery remain pending. Reuse iteration-194's localhost invocation. Final
scoped inventory has no owned F2 instance or native Vivado/Java job; no new AFI
request was made.

Iteration 201 adds an explicit TargetBox clone/rename contract. Concrete,
reachable module and instance paths retain their root and all instance hops,
with every module reference specialized together. Foreign, stale, opaque,
unreachable and mismatched paths reject; dropped/changed markers fail descriptor
validation. Original and translated annotations, mapping rows and the marker's
actual class definition are hash-bound. The production compiler fixture's
independent audit derives the destination from actual instrumented IR and rejects
eight coherently rehashed marker corruptions. Actual exact-Rocket production
preflight now rejects **10 annotation classes**, down from 11, and still emits
no accepted whole-Rocket bank RTL.

All **125 Scala / 306 checkpoint Python / 40 loop tests** and the full retained
EDA ASan/UBSan/FCFS/bank/bridge/host scope pass. Native localhost Vivado 2025.2
bank and MMIO/DMA-top OOC synthesis pass. Matched bank VCS passes **4,669** checks,
exact-native-input top VCS **7,858**, and the read-first synchronous fixture
**21,970**, retaining full debug waveforms. Independent EDA auditing matches ten
generated files / sixteen sources and retains all six XDC, ten compiler-context
and five memory-policy corruption rejections plus the eight new target-box cases.
The bank fixture uses 125 LUTs / 82 registers; estimated setup +6.435 ns / hold
+0.054 ns at 140 MHz, with external I/O unconstrained. Commands and individual
receipts: `runs/aws-f2/iteration201/summary.json` relative to the loop.

This is compiler/component evidence. Full checkpoint image/P&R/AFI, physical
BUFGCE ownership, complete common-cut/memory/host/pre-FAME integration, four
active hardware cuts, paired CPU zero-edge restores, finite replay, sustained
live RTL beyond the trace window and rolling hardware recovery remain pending.
The iteration-194 localhost invocation is retained; final scoped inventory has
no owned runtime instance or native Vivado/Java job, and no new AFI was requested.

Iteration 200 preserves exact global InferReadWrite, default read-first/write-first
and passthrough synchronous-memory policies through bank specialization. Source
and translated annotation hashes plus explicit mapping rows bind every policy.
Duplicate/conflicting defaults reject; synchronous undefined read-under-write
must be resolved by the backend before inventory, because choosing a default
later can change a saved address pipeline into a data pipeline. Dropped or
swapped policies fail descriptor validation. Unknown owners remain unsupported.
Actual exact-Rocket production preflight now rejects **11 annotation classes**,
down from 14, and emits no accepted whole-Rocket banks.

All **122 Scala / 306 checkpoint Python / 40 loop tests** and the full retained
EDA ASan/UBSan/FCFS/bank/bridge/host scope pass. A new backend-resolved read-first
fixture passes **21,970 VCS checks**, 454 bank responses and ten complete-state
captures, with 2,905 sampled output boundaries across 202 functional edges,
against unchanged original RTL and an
independent input oracle, including collisions, masks, held responses and
continuation. Original synchronous-memory coverage remains intact. Native
localhost Vivado 2025.2 bank and MMIO/DMA-top OOC synthesis pass; bank use is
125 LUTs / 82 registers, estimated setup +6.435 ns / hold +0.054 ns at 140 MHz
with external I/O unconstrained. Matched bank VCS passes 4,669 checks and
exact-native-input top VCS passes 7,858, with full debug waveforms. Independent
EDA auditing matches all ten generated files / fifteen sources and rejects
five coherently rehashed memory-policy, ten compiler-context and six XDC
corruptions. Evidence and exact commands: `runs/aws-f2/iteration200/summary.json`
relative to the loop.

This remains compiler/component evidence. Full checkpoint image/P&R/AFI,
three physical BUFGCE owners, complete common-cut/memory/host/pre-FAME binding,
physical early/warm/outstanding/late captures, paired CPU zero-edge restores,
finite replay, sustained live RTL beyond the trace window and rolling hardware
recovery remain pending. Final scoped inventory finds no owned F2 runtime
instance or native Vivado/Java job; no new AFI request was made.

Iteration 199 adds an explicit post-lowering compiler-context contract for
InfoMode, OutputFile, TargetDir, ConfigPackage, ConfigString, OutputBaseFilename,
AllowUnrecognizedAnnotations and enum type definitions. Values remain unchanged
for downstream stage consumers, while `.bank-probe-context.json` binds their
complete values and pre/instrumented circuit hashes into final emission. The
parser permissiveness flag does not relax storage-owner admission. Unknown
annotations, embedded circuits, pending transforms, targeted enum instances and
arbitrary output payloads still reject; duplicate options/conflicting enum types
also reject. Actual Rocket production preflight rejects 14 remaining annotation
classes, down from 22; no accepted whole-Rocket bank RTL is emitted. This is a
compiler/component increment. Full checkpoint image, physical BUFGCE/common-cut,
functional-memory/host ownership, all four active FPGA cuts and complete paired
CPU zero-edge/finite/live/rolling acceptance remain pending. Evidence and raw
commands: `runs/aws-f2/iteration199/summary.json` relative to the loop.

Validation passes: 119 Scala / 306 checkpoint Python / 40 loop tests and the
full retained EDA ASan/UBSan scope. Native localhost bank OOC uses 125 LUTs /
82 registers (estimated setup +6.435 ns / hold +0.054 ns at 140 MHz, external I/O
unconstrained). Matched-input bank VCS passes 4,669 checks and exact-native-input
MMIO/DMA top passes 7,858 with full debug VCDs. Independent EDA auditing matches
all ten generated files / fifteen sources and rejects ten compiler-context plus
six XDC missing/coherently rehashed corruptions. Final scoped inventory has no
owned F2 instance or native Vivado/Java build job; no new AFI was requested.

Iteration 198 preserves physical constraints through bank specialization with
explicit internal/external XDC contracts. Arguments sharing one explicit root
are cloned together; nested instance module references are rewritten without
crossing repeated roots. Ground declarations, concrete instances/ports and
format counts are validated. Unknown, opaque, foreign, aggregate and malformed
paths still reject. Global snippets remain singletons and external annotations
retain their original class. Exact logical-RAM memory-model labels also clone
with complete annotation/mapping provenance. Real WriteXDCFile output agrees
with the uninstrumented repeated hierarchy, and altered/dropped annotations
fail descriptor validation. Both actual emitted XDC files are hash-bound to
the production bank emission receipt; missing/duplicate files reject.

The native fixture initially used an invalid input-clock endpoint. Its exit-0
run is explicitly rejected from the real Constraints 18-401/18-512 diagnostics.
The corrected scalar-reset constraint is checked in every DCP XDC member along
with the real DONT_TOUCH cell property; native constraint warnings now fail
verification. A separate failed diagnostic inspected only the late XDC while
Vivado retained commands in the regular XDC; all raw outputs remain unchanged.
All 113 Scala / 306 checkpoint Python / 40 loop tests and the complete retained
EDA ASan/UBSan scope pass. The actual Rocket bank preflight still rejects 22
annotation classes, with no accepted whole-root bank output. Three physical
BUFGCE owners, common-cut/memory/host/transport integration and full image
P&R/AFI/capture/migration remain unsupported or pending. This increment supplies
compiler/component evidence only. Native OOC uses 125 LUTs / 82 registers, estimated setup +6.478 ns /
hold +0.081 ns at 140 MHz with unconstrained external I/O. Matching VCS
passes 4,669 bank / 7,858 exact-native-input top checks with debug VCDs; six
missing/coherently rehashed XDC cases reject. Per-run native/VCS, corruption
and provenance receipts are under `runs/aws-f2/iteration198/` relative to the loop.

Iteration 197 adds `--simulator-fpga-synthesis-constants` to the actual Golden
Gate CLI/backend. It requires exactly one whole-root inventory, rejects
incompatible semantic tracking and selects only the exact pinned model's FPGA
branch after native lowering. Ordinary compilation retains runtime-plusarg
owners. Four provenance sidecars retain original/prepared IR, exact inline
sources and definition/parameter/repeated-instance records; final emission
binds them to the emitted RTL. Unknown source bytes and missing/duplicate
requests/sidecars reject. Combined constant/bank compilation has an actual
production-path regression; pending NoDedup/Inline targets translate to all
concrete clones and remain hash-bound without flattening the bank hierarchy.
Passive blackbox output paths are preserved; unknown contracts still fail.
Native/VCS branch and production-bank verifiers pin immutable input snapshots,
reject live source/generated changes across execution, and derive receipt hashes
from those snapshots. An early receipt with a source edit during synthesis was
rejected by independent auditing; corrected guarded reruns retain that failure.

Independent parsing of the fresh exact Rocket output reconstructs all seven
constant instances across four definitions and every unchanged module. Four
per-hart timeout inputs, UART controls and the custom boot pin select their
source defaults. Final inventory has 11,459 generated-model entries / 618,247
words / 2,282 instances; three physical BUFGCEs remain unsupported. The actual
whole-root bank trial exits 1 on 25 remaining annotation classes, including
opaque/deleted/bridge/channel/memory/XDC contracts; it emits no accepted banks.
Complete physical/cut/memory/host/live-transport mapping and image P&R/AFI
remain pending. This option alone cannot establish a capture image.

All 109 Scala / 306 checkpoint Python / 40 loop tests and full retained EDA
ASan/UBSan regressions pass. Eight independent corruption test groups reject
coherently rehashed altered source, values, ownership and unchanged modules.
Three fresh EDA VCS SP2 variants separately test the production-selected
constant, the unmodified model under SYNTHESIS and ordinary runtime overrides:
6,150 output comparisons / 3,075 fixture edges pass. A wrong component oracle
stops before acknowledging edge zero. Full debug VCDs remain available.
Identical final inputs synthesize with native Vivado 2025.2 to 22 LUTs /
32 registers; OOC estimates are setup +6.443 ns / hold +0.065 ns at 140 MHz,
with external I/O unconstrained. Existing native-input top MMIO/DMA, all dense
word comparisons, primitive-model and bank/host/FCFS checks remain required.
No FPGA capture or finite/live CPU acceptance is claimed. Current commands
and immutable evidence: `runs/aws-f2/iteration197/summary.json` relative to the loop.

Iteration 196 separates reachable external owners from unused definitions.
The exact current ordinary Rocket compiler emits a report bound to its final
reference and emission identity; independent traversal verifies all 2,293
instances, three active BUFGCEs, seven active plusarg-model instances and eleven
unused external definitions. Both abstract-gate definitions are unused. Bank
preparation now scopes gate admission to reachable modules while preserving
unknown-annotation rejection and original source hashes. All 101 Scala / 298
checkpoint Python / 40 loop tests and the complete retained EDA sanitizer scope
pass. Full bank compilation gets past the dead gate and fails strict explicit
annotation translation (28 classes), without emitting accepted Rocket banks.

Native Vivado 2025.2's unmodified BUFGCE/glbl models, MIDAS's abstract gate and
the stock metasim model run together in fresh EDA VCS SP2. Across 256 source
edges, 682 phase observations and 3,658 checks, physical-model/metasim edge
counts are 110 while the abstract model has 183: 73 extra positive pulses are
hidden by settled-output agreement. The SYNC CE latch tracks low phases and
holds across 170 high-phase CE changes. Wrong expected output stops at edge 4;
healthy/corrupt full debug VCDs and original model/source hashes are retained.
This is component-model evidence only. A source-bound primitive/cut mapping,
explicit FPGA plusarg semantics and complete annotation translation remain
required, along with production memory/host/live-transport integration,
whole-image P&R/AFI and actual hardware migration. Current receipts/commands:
`runs/aws-f2/iteration196/summary.json` relative to the loop.

Iteration 195 adds `--simulator-bank-probe` to the actual post-mapping compiler
path, after host transforms and FPGA lowering. It generates the complete root's
bank network and binds pre-bank inventory/reference, instrumented IR, bank
binding and immutable descriptors to the emitted RTL body. The final emission
inventory independently includes the response latch and emitter-renamed state.
Only known compiler bookkeeping bypasses storage-annotation translation;
unknown contracts, duplicate requests and partial inventory roots reject.
The probe cannot surround a registered live capture transport. Its external
ports still require a real common-cut/MMIO binding; every binding explicitly
marks it non-deployable and requires external runtime ownership. Invoke it
with an isolated `-td` beneath runs; stock manager recipes/Make remain unchanged.

All 97 Scala / 290 checkpoint Python / 40 loop tests and retained EDA sanitizer
regressions pass. The production-path bank fixture passes 4,669 EDA VCS checks
with complete word reads at component cycles 2 / 39 / 132 / 900, reset/clock
pressure while frozen, held-response backpressure, invalid selectors/unfrozen
requests and continuation through 1,025 functional edges. Deliberate word
corruption stops at the first unacknowledged read, cycle 2, while frozen.
Both runs retain debug VCDs. Identical inputs synthesize locally to 44 LUTs /
26 registers for the F2 part, estimated OOC WNS +6.435 ns / WHS +0.049 ns;
external I/O is unconstrained. These remain compiler/component measurements.

Fresh full exact-Rocket compilation from retained target inputs reaches the
hook and exits 1 on `no exact registered-enable clock-gate adapter for
AbstractClockGate_0`. The retained ordinary final reference contains that
definition without any instance; reachability, exact primitive/plusarg semantics
and remaining annotation contracts require explicit audit. No failing source
check is weakened. No full Rocket bank output, complete image P&R/AFI, FPGA
checkpoint, paired CPU migration or live/rolling hardware acceptance is claimed.
Raw commands/diagnostics and immutable receipts:
`runs/aws-f2/iteration195/summary.json` relative to the loop.
The top MMIO/DMA fixture also passes 7,858 checks on exact native synthesis
inputs. Final independent EDA auditing verifies all probe source/generated/DCP
identities, each cut's independent accumulator values, the full-recipe failure,
top transport evidence and all 780 retained dense words. Fresh scoped inventory
finds no owned runtime instance or remaining native Vivado/Java job.

Iteration 194 repairs the production compiler's discarded post-mapping
host-transform result. Injected storage, clock wiring and annotations now
reach the FPGA backend and final emission. Simulator inventory observes the
actual emitter-prepared state; `.simulator-emission.json` binds host/backend
IR, final emission-state serialization, manifest and emitted RTL body before
blackbox append. These hashes describe generated RTL and still require
external runtime and complete image/driver ownership. Make tracks the new
binding as an inventory output.

The same production path is tested with observable injected state and a real
host-clock sink. All 94 Scala checks pass. EDA VCS passes 4,100 public-output
comparisons over 1,025 host edges, including reset, overflow and unrelated
clock pressure; old discarded-transform behavior fails at cycle 1. Full debug
VCDs are retained. Native Vivado synthesizes identical generated inputs for
the F2 part (12 LUTs / 16 registers; estimated OOC WNS +6.441 ns / WHS +0.073 ns,
external I/O unconstrained). Fresh full Golden Gate compilation of the exact
Rocket recipe from retained target inputs inventories 11,466 entries / 618,254
words / 2,293 instances. This ordinary recipe compilation lacks semantic
preservation and capture integration; it does not replace the retained
instrumented inventory or establish physical coverage. Instance-connector
serialization in the actual emission-state reference is diagnostic IR, not
FIRRTL parser input. Complete bank/common-cut/physical-memory/host binding,
image P&R/AFI, hardware checkpoint capture and CPU migration remain pending.
Top MMIO/DMA passes 7,858 checks using the exact native inputs. Independent
EDA emission/DCP/top and all 780 dense-word audits pass. No invocation F2
instance or native Vivado/Java build job remains.
Commands and receipts: `runs/aws-f2/iteration194/summary.json` relative to the loop.

Iteration 193 replaces module-local serial priority muxes with masked,
balanced two-input reductions. Selectors remain globally unique and checked
before specialization; a miss produces zero, including stateless children.
The request/response latency, frozen functional state, synchronous pipeline
ownership and held-response semantics remain unchanged. Source-structure checks
cover all 2,300 retained modules and 14,398 masked branches (12,099 storage
entries plus 2,299 child routes). The largest retained module replaces 198
inline priority muxes with eight pairwise OR stages. These are source
measurements; physical timing is measured independently.

A new dense fixture retains **260 owners**: 257 local registers spanning every
width from 1 through 64, plus three repeated child instances. Its largest
module uses nine OR stages. Fresh EDA VCS SP2 passes **13,558 checks / 780 word
reads / 3,120 stalled response boundaries**, with complete cuts at **2 / 39 /
132** and continued functional execution through 173 edges. Every word is
compared with both original RTL and a separate public-input accumulator model.
Original-only preservation annotations keep otherwise unobserved reference
registers through Verilog emission. Invalid banks, slots and oversized
addresses return held zero/error responses. First-word semantic corruption
stops frozen before any read completes; full debug VCDs are retained.
`audit_dense_words` reconstructs all 780 words independently from the recorded
public inputs, including width truncation and each repeated child. Its four
unit tests also reject altered/missing/reordered inputs, semantic corruption,
noncanonical padding, and incomplete/reshaped/unknown owners.

All **90 Scala / 290 checkpoint Python / 40 loop tests** and the full retained
EDA bank/transport/host/FCFS ASan/UBSan scope pass. The top MMIO/CPU-DMA VCS
fixture passes **7,858** checks using the actual immutable native synthesis
inputs. EDA synchronization excludes live Vivado `.Xil` scratch directories;
real rsync tests independently verify that DCP/report evidence still transfers.
The original failed reference compile and scratch-race diagnostics are retained
under `runs/aws-f2/iteration193/`, alongside the successful reruns.

All **15** native localhost OOC synthesis commands complete, including the
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

The production integration gap remains explicit: `CheckpointCaptureTopKey`
defaults to `None`, there is no production Rocket binding, and
`GoldenGateCompilerPhase`'s checkpoint path emits inventory without invoking
`GeneratedStateBankAccess`. A complete F1Shim bank probe cannot simply be
frozen behind its own MMIO/stream engine; the capture transport must remain
live, and external memory handshakes need a common-cut ownership protocol.
The materialized abstract gate adapter also does not establish the physical
BUFGCE implementation's state/clock mapping. Complete source-bound physical
and pre-FAME mapping, atomic functional-memory/host capture, production
integration, image P&R/AFI and actual FPGA-to-VCS migration remain pending.
No new checkpoint image or hardware checkpoint is claimed.

Iteration 192 represents one-bit combinational Clock-token origins explicitly
as `data_clock: {hierarchy, expression}`. Transparent casts/aliases/child pins
preserve the defining scope and expression. The generator and independent
post-generation descriptor reconstruction reject such origins on registers,
RAM ports/pipelines, registered gate sources and clocked effects. Bare storage
references, missing drivers, opaque outputs and actual derived clocks remain
unsupported. No root oscillator or extra state owner is invented.

The new `data-clocks` repeated-hierarchy fixture retains **9 owners / 15 words /
22 clock-port routes**, eight with computed origins. Tokens control functional
next-state data rather than remaining unused metadata. The existing EDA runner
independently reconstructs those token functions from public inputs and compares
every captured word with both original RTL and the functional-input model.
`verify_data_clock_audit` copies both immutable input sets and coherently updates
their outer hashes before corrupting token scope/expression/schema; a healthy
copied control must pass first. Evidence stays component-scoped.

The whole retained Rocket probe now completes generated-RTL bank emission and
descriptor construction (**12,099 entries / 619,016 words / 2,300 instances**).
The four FAME data-clock routes retain their exact ClockBridge counter comparison
expressions. Complete physical primitive mapping, atomic memory/host ownership,
transport integration, full image timing/P&R/AFI and physical FPGA checkpoint
migration remain pending. Fresh commands and evidence are under
`runs/aws-f2/iteration192/` relative to the loop.

Current component validation: **89 Scala / 286 checkpoint Python / 40 loop tests**
and the retained EDA sanitizer scope pass. Token-fixture EDA VCS passes **5,483**
checks / 60 words at four complete cuts. Native localhost OOC synthesis uses
**169 LUTs / 96 registers**, estimated WNS **+6.260 ns** / WHS **+0.038 ns** at
140 MHz, with external I/O unconstrained. All **13** retained/new component
syntheses complete. Whole-root OOC synthesis also completes with **715,823 LUTs /
107,016 registers / 64 DSPs / no block RAM**, zero synthesis errors/critical
warnings and zero OOC DRC errors. Its estimated setup WNS **-0.916 ns** / hold
WHS **-0.324 ns** fails timing (6,878 setup / 18,710 hold failing endpoints).
The worst setup path has 34 logic levels into `ckpt_saved_data[0]`. External I/O
is unconstrained and physical clock-buffer locations are unbound; this is not
whole-image timing closure. Final independent EDA audits pass, including the whole
root's complete inventory/source/DCP identity, all **14** token-origin semantic
corruptions and **23** new fixture receipt corruptions. Top VCS passes **7,858**
checks using exact native inputs. Fresh inventory confirms no invocation runtime
instance or remaining native Vivado/Java build job. Commands and immutable
receipts are cataloged in `runs/aws-f2/iteration192/summary.json` relative to the loop.

Iteration 191 adds explicit invalid metadata clock origins. A lowered FIRRTL
`is invalid` driver stays an exact `invalid_clock` hierarchy string through
transparent aliases/casts, one-bit IO and repeated children. It cannot become a
functional root clock, static zero, or gate source. Missing drivers and multiple
invalid/connected drivers reject. Every register, memory port/pipeline and
clocked effect is independently checked at generation and descriptor
reconstruction, including storage-clock rewiring with a refreshed circuit hash.
No port or owner is removed to support this case.

`MultipleFunctionalClocksSpec` emits `invalid-clocks`: **9 owners / 15 words /
22 clock-port routes**, eight with explicit invalid provenance. Fresh EDA
`verify_multiple_clocks_vcs` passes **5,483** checks / 60 word reads across the
four complete component cuts, with original RTL plus public-input oracles,
frozen clock/reset/write pressure, backpressure, continuation, debug VCD and
first-word corruption stop. All **86 Scala / 286 checkpoint Python / 40 loop
tests**, the full retained EDA sanitizer scope and all **12** native component
syntheses pass. The invalid metadata fixture uses **181 LUTs / 79 registers**,
estimated WNS **+6.298 ns** / WHS **+0.049 ns** at 140 MHz (OOC; external
I/O unconstrained). Complete image timing remains pending; FASED retains
negative hold slack. Independent audits verify all words/routes/source/DCPs.
`verify_invalid_clock_audit` passes a healthy copied control and rejects all
**12** coherently rehashed invalid-origin corruptions; the receipt suite rejects
all **23** corruptions. Top VCS passes **7,858** checks on exact immutable native
inputs. Final receipts and commands: `runs/aws-f2/iteration191/summary.json`.

The whole retained Rocket probe clears the PeekPoke dummy pin. Its dummy module
has no internal use of `tIO_clock`. The next rejection is a computed
Clock-typed FAME token-data value from
`ClockBridgeModule_0.clockTokenGen.eq(timeToNextEdge_0, minStepsToEdge)`.
That route feeds `asUInt` enable/fired-owner data; it is not admitted as a
functional clock. Complete bank output, simulator/physical/common-cut ownership,
checkpoint image P&R/AFI, actual hardware capture and CPU migration remain
pending. Retained-input hashes, raw probe failure, module excerpt and route
analysis are under `runs/aws-f2/iteration191/` relative to the loop.

Iteration 190 adds explicit static metadata clock provenance. Exact one-bit
zero/one constants can pass through concrete clock aliases, casts, IO cells and
repeated hierarchy, with `constant_clock` binding rows instead of invented root
clock names. Every sequential consumer still requires a functional root origin:
registers, memory ports/pipelines, gate enable state and clocked effects reject
static clocks. Descriptor reconstruction checks consumers even when an attacker
updates the instrumented-circuit hash. Unknown/invalid/undriven and derived
clock origins remain unsupported.

The new `static-clocks` fixture keeps 9 state owners / 15 words and 22 clock-port
routes, including eight repeated static metadata pins. It uses the same
`verify_multiple_clocks_vcs`, native `synth_clocked_effects` and independent
`audit_multiple_clocks` checks as the direct/forwarded fixtures.
`verify_static_clock_audit` corrupts the explicit static metadata in copied
receipts while coherently updating both outer input hashes; a healthy copied
control must pass before semantic negatives can count.

Fresh static-fixture VCS checks pass at component steps 6 / 43 / 126 / 223
(5,483 checks / 60 complete word reads) with full debug VCD and first-word
corruption stop. Native localhost OOC synthesis uses 181 LUTs / 79 registers;
independent audits verify all 22 routes and reject ten coherently rehashed
metadata corruptions, including Boolean/float values, plus 23 receipt negatives.
All 83 Scala / 286 checkpoint Python / 40 loop tests, retained full EDA
FCFS/fixture/host sanitizer scope and eleven native component syntheses pass.
Exact commands and immutable receipts: `runs/aws-f2/iteration190/summary.json`
relative to the loop. These results establish component behavior only.

The retained whole-Rocket probe now passes the old constant-zero bridge pin
rejection but stops at PeekPoke's explicitly invalid dummy `tIO_clock` pin:
`missing child clock at F1Shim.top.PeekPokeBridgeModule_0.hPort_dummyModule.tIO_clock`.
It still inventories 12,099 entries / 619,016 words and emits no complete banks.
The new raw failure is under `runs/aws-f2/iteration190/`; the iteration-189
failure below is historical. No invalid pin or functional owner was dropped.
Complete capture integration, image P&R/AFI, real F2 execution/capture and CPU
migration remain pending.

Iteration 189 adds `GeneratedSynthesisConstantAdapter.prepare`, an explicit
FPGA-only preparation step **before** simulator inventory and bank generation.
It accepts only the exact source-hashed Rocket `plusarg_reader` model, exact
output signature and WIDTH/DEFAULT/FORMAT parameters. Its `SYNTHESIS` branch
is a constant; its non-synthesis `myplus` register remains a separate metasim
owner. The default inventory and opaque-owner rejection are unchanged.

Preparation materializes the actual synthesis constant and retains a
`SynthesisPlusArgConstantAnnotation` with source hash, original circuit hash
and parameters. Simulator manifests bind every repeated instance explicitly.
Bank specialization clones that annotation; descriptor construction checks
the translated annotation hash and reconstructs each actual constant output,
rejecting changed, dropped, duplicated or hidden owners. Keep the returned
annotations with the circuit; never apply this preparation to a metasim donor.
FPGA-to-metasim mapping of these different primitive implementations still
requires explicit integration before CPU restore can be accepted.

The new `SynthesisConstantBankSpec` emits an original reference with opaque
plusarg instances plus their separately retained, exact Verilog source.
`verify_clocked_effects_vcs` compiles that original model with
`+define+SYNTHESIS` on EDA, runs with a conflicting `+checkpoint_constant=99`,
and compares its default 341, functional execution and complete bank cuts.
`audit_synthesis_constant` separately reconstructs every captured counter word
from public functional inputs, checks native/EDA source identity and DCP, and
`verify_synthesis_constant_audit` exercises receipt/semantic corruption.

An explicit `midas/Test/runMain midas.checkpoint.RetainedRocketBankProbe`
probe inventories the complete reachable retained exact-recipe circuit after
this preparation: **12,099 entries / 619,016 transfer words / 21,005,343 logical
bits / 2,300 instances**. Seven plusarg instances have explicit constant
provenance. **Whole-root bank generation fails** at the constant-zero bridge
clock pins wired by FPGATop; the resolver currently requires root input/gate
clock provenance. Do not drop these ports or infer hidden-state coverage.
The failing raw command, input manifests and compiler diagnostic are retained
under `runs/aws-f2/iteration189/` relative to the loop. This is a source-bound
inventory and component increment, not complete synthesized Rocket banks,
a custom AFI, physical checkpoint capture or CPU migration acceptance.

Iteration 188 adds a source-bound adapter for the exact MIDAS
`DefineAbstractClockGate.impl`. Its enable register updates on posedge I;
its output remains `I & enable`, including delta-cycle pulses when enable
changes. The bank generator freezes this owner alongside downstream storage.
It never substitutes CE as a downstream storage enable. Independent descriptor
validation reconstructs each ordered gate chain from actual specialized
wiring and checks the gate's enable clock, reset, next value and output.
Other gates/opaque implementations still reject. The adapter describes the
abstract RTL model, not platform-mapped BUFGCE state or a completed F2 image.

Conditional RAM clock validity now requires the exact same Boolean enable on
that memory port. Local aliases and mux(enable,1,0) identities are checked;
original clock wiring and synchronous pipeline ownership remain intact.
Unmatched guards and conditional register clocks reject. The retained exact
Rocket FASED subtree now elaborates **759 entries / 99,611 transfer words**;
this does not include functional host DRAM, host software or the full simulator.

The new component test runs on EDA after Scala emission:

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_registered_gate_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration188/scala/bank/registered-gate \
  --out automations/checkpoint_loop/runs/aws-f2/iteration188/registered-gate-vcs
```

`audit_registered_gate` independently recomputes every captured word and gate
edge from public inputs, validates immutable VCS/native snapshots and checks
first-word corruption stopped frozen. Native component synthesis uses
`synth_clocked_effects` with that generated directory after native HDK setup
from the HDK directory. This iteration's full commands, native FASED component
synthesis and independent audits are retained under `runs/aws-f2/iteration188/`.
All-owner freeze/CDC, physical clock primitive coverage and complete CPU/hardware
acceptance remain separate pending work.

Iteration 187 adds transparent hierarchical clock routing to generated bank
access. Output clock ports, sibling forwarding, connected child input pins,
local nodes/wires, and exact `Clock`/one-bit `UInt` casts through concrete IO
cells must resolve to named root clock inputs. Resolution is lazy per pin with
hierarchy-qualified cycle checks; unrelated clock dependencies cannot create a
false cycle. Data logic, register next-state drivers, constants, opaque modules,
gated clocks and asynchronous resets remain unsupported. Descriptor construction
reconstructs all clock-port provenance from the actual specialized circuit.

Materialized synchronous RAM pipeline clocks now use explicitly connected
clock wires. This preserves the original clock while allowing its alias node
to occur later than the new pipeline declaration. Original StateIDs and
pipeline ownership remain unchanged. No clock gate is replaced or treated as
a transparent wire.

`MultipleFunctionalClocksSpec` emits a second `forwarded-clocks` fixture with
14 checked clock-port routes and the same 9 entries / 15 words as the direct
fixture. On EDA, run `verify_multiple_clocks_vcs` with this generated directory;
on the manager, run `synth_clocked_effects` after native HDK setup. The same
independent `audit_multiple_clocks` verifies the private VCS/native inputs,
complete per-domain cuts, corruption stop, waveforms and native DCP. Current
commands and evidence are under `runs/aws-f2/iteration187/` relative to the loop.

The caller must still establish and hold all-owner freeze before reads through
response drain. This increment supplies neither a CDC acknowledgement nor a
common CPU cut. Complete Rocket/FAME/gated-clock/functional-memory/host
integration, localhost image P&R/AFI and FPGA-produced paired checkpoints remain
pending.

Iteration 186 extends the separate-clock bank generator to multiple direct
functional input clocks. Functional registers, RAM read/write ports and
materialized synchronous pipelines retain their distinct clocks. Child inputs
must trace directly to parent inputs. `functional_clock_domains` binds every
module/instance clock port to its root input and is independently reconstructed
from emitted wiring when constructing descriptors. Missing or altered clock
provenance rejects. Multiple clocks without a separate transport endpoint,
derived/gated clocks, opaque owners and asynchronous resets remain unsupported.

This is a wiring/freeze contract. The caller still must establish a stable
all-owner freeze in every domain before reads and hold it until responses drain;
this generator does not implement a CDC acknowledgement or a common CPU cut.
The new `MultipleFunctionalClocksSpec` emits 9 entries / 15 words with swapped
repeated children and RAMs read and written in different domains. The new EDA
check exercises independent/coincident functional clocks, stopped-clock and
adversarial frozen-clock captures, resets, backpressure, post-release execution
and first-word corruption with full debug waveforms:

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_multiple_clocks_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration186/scala/bank/multiple-clocks \
  --out automations/checkpoint_loop/runs/aws-f2/iteration186/multiple-clocks-vcs
```

Native synthesis uses `synth_clocked_effects` with that generated directory and
constrains both functional inputs and `ckpt_clock` at 140 MHz. Run only on this
manager after native F2 HDK setup. `audit_multiple_clocks` independently checks
immutable VCS/native input agreement, every recorded word/domain label, the
functional schedule, corruption stop, native DCP identity and all three clock
constraints. Component evidence does not establish a Rocket FPGA image or
hardware capture; complete integration, AFI and physical migration remain pending.

Iteration 185 adds `separateAccessClock = true` to generated bank access. The
root endpoint then uses a dedicated `ckpt_clock` while all functional storage
and synchronous RAM read owners keep their original clocks. The descriptor
validator checks the actual three endpoint register clocks against the binding's
`access_clock` and explicit freeze contract. The caller must acquire every
functional owner and hold freeze before reads until responses drain; this
option does not add a CDC handshake or establish an atomic CPU cut.

The retained exact Rocket `DCacheDataArray` passes complete original-RTL and
independent functional-model checks in fresh EDA VCS: **32,832 words** at
**C=513 / 611 / 869**, with **65,664** reads while its functional clock is
stopped, adversarial writes/clock pulses while frozen, backpressure, continuation,
first-word corruption and full debug VCD. Native localhost OOC synthesis uses
**9,568 LUTs / 522 registers**, estimated setup slack **+5.228 ns** at 140 MHz
with both clocks constrained. This is component evidence only; no complete
Rocket FPGA image or hardware checkpoint is claimed. Run the new check on EDA,
after the complete Scala suite emits `rocket-dcache-array`:

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_independent_clock_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration185/scala/bank/rocket-dcache-array \
  --out automations/checkpoint_loop/runs/aws-f2/iteration185/dcache-vcs
```

Iteration 184 adds a synchronous effect contract: `printf`, `stop` and FIRRTL
verification retain their original clock/predicate/reporting behavior, with
enables ANDed with `!ckpt_freeze`. Direct input clocks are required; derived
effect clocks, asynchronous/opaque state and analog attachments still reject.
A child clock must be driven directly by its parent's single clock. Stateless
clockless modules can route the combinational bank network; they cannot hide
independent clock domains. `NoCircuitDedupAnnotation` preserves instance clones
through resolution and is included in the checked annotation-policy hashes.

Fresh EDA VCS checks the retained exact Rocket recipe's actual DTLB subtree
(17 specialized modules, 101 state words): three complete bank captures at
**C=2 / 39 / 132**, **28,918** checks, **303** reads and **1,212** response-stall
cycles. Every public output and every captured register matches independently
emitted original RTL across **173** functional edges. The independent oracle
reads reference storage; only synthesized public bank ports supply the capture.
Full VCD, bank words and first-word corruption rejection are retained. A separate
effects fixture checks accepting-edge reset/effect freeze, **116** actual
functional print messages, stop after release and the immediate assertion's
original reporting policy. Its negative observer terminates after that report;
it does not reinterpret an immediate assertion as a fatal stop.

Native localhost Vivado 2025.2 OOC synthesis of the DTLB bank uses **3,084 LUTs /
1,859 registers**, estimated setup slack **+4.450 ns** at 140 MHz. The effects
bank uses **42 LUTs / 20 registers**. These are component checks from a retained
recipe intermediate, not fresh full-Rocket elaboration, a custom AFI, physical
capture or CPU migration. Exact commands and provenance live under
`automations/checkpoint_loop/runs/aws-f2/iteration184/`; both hardware checkpoint
levels, traces, four workload cuts, CPU restores/live comparison and rolling
F2 history remain pending.

Iteration 183 adds wide/deep generated bank mapping. A logical state entry keeps
its StateID, width and depth. For `chunks = ceil(width / 64)`, physical address
`a * chunks + c` selects bits `[64*c +: min(64, width - 64*c)]` of logical address
`a`, zero-padded to 64 bits. A single selector and descriptor cover each StateID;
chunking never invents independent semantic owners. Signed words preserve their
bit representation. RAM addresses divide by the exact chunk count, including
non-power-of-two counts. Transfers above **2^31-1** per entry fail explicitly;
physical address and descriptor depth ports remain 32 bits.

A circuit with any wide state uses `latched-banked64-chunked-v2`. Its binding
retains logical `width`/`depth` and adds `chunks`, `transfer_width`, and
`transfer_depth` to every entry. `CheckpointCaptureDescriptors` derives and
checks those fields before producing the ROM and host C++ metadata. Transport
frames remain version 1, carrying the physical shape. The Python host binding
uses `banked64-chunked-v2`, validates both shapes, checks final-chunk padding,
and reconstructs canonical `.rtlckpt` logical words only after full validation.
Narrow-only generated circuits retain the previous binding protocol; the old
explicit unchunked bank codec continues rejecting wide state.

Fresh EDA VCS SP2 connects the real generated storage and descriptor ROM to
production MMIO/DMA transport and captures **65,564** physical words at each
of **C=1 / 42 / 138**. Signed 65-bit, exact 128-bit and 512-bit registers,
129-bit x 5 RAM and 9-bit x 65,537 RAM pass independent original-RTL and
functional-input checks, reset/write freeze, **1,573,571** DMA stall cycles,
complete host reconstruction, sanitizer frame checks and frozen first-word
corruption rejection. Native localhost Vivado 2025.2 OOC synthesis uses
**20,687 LUTs / 259 registers**, estimated setup slack **+5.328 ns** at 140 MHz.
This is component evidence; complete Rocket compilation/integration, image
build/P&R/AFI and physical capture/migration remain pending.

After Scala elaboration, on EDA with `vcs-env.sh` sourced last:

```bash
python3 -m tools.checkpoint_formats.tests.verify_chunked_bank_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration183/scala/bank/chunked \
  --out automations/checkpoint_loop/runs/aws-f2/iteration183/chunked-reverify
```

On this manager, after native F2 HDK setup:

```bash
python3 -m tools.checkpoint_formats.tests.synth_chunked_bank \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration183/scala/bank/chunked \
  --out automations/checkpoint_loop/runs/aws-f2/iteration183/native-chunked-reverify
```

Iteration 182 adds explicit annotation translation during bank specialization.
Local `DontTouchAnnotation` and `MemoryFileInlineAnnotation` targets clone to
every reachable module instance; nonlocal targets resolve only the specified
subtree. Exact declaration kinds and every instance/module path are checked.
Overlapping initialization, dead/malformed/component targets, unknown annotation
types and contradictory synthesis initialization policies reject. Hex/binary
filenames and `MemorySynthInit` / `MemoryNoSynthInit` policies are preserved.
Canonical source/translated annotation hashes join the bank binding; descriptor
construction rejects dropped/changed initialization or extra unsupported metadata.
The compiler's derived path cache is still discarded and recomputed.

`InitializedStateBankSpec` uses two separately initialized repeated RAM instances.
Standard FIRRTL target-path resolution emits the independent original circuit;
the checkpoint generator does not supply that reference. EDA VCS checks all
16 initialized words at **C=0**, before any functional edge, then repeats complete
captures at **C=7 / 44 / 155** after writes. The public-input oracle and original
RTL agree through reset-independent transport, selector failures, accepting-edge
freeze, response stalls and release with a held response. Full debug waveforms
and both initialization files are retained. Native Vivado synthesis separately
checks every RAM INIT bit plane and both physical read-port copies. These are
component checks, not FPGA-origin CPU checkpoint acceptance.

After the full Scala suite elaborates the initialized fixture, run on EDA with
`vcs-env.sh` sourced last:

```bash
python3 -m tools.checkpoint_formats.tests.verify_initialized_bank_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration182/scala/bank/initialized \
  --out automations/checkpoint_loop/runs/aws-f2/iteration182/initialized-reverify
```

On this manager, after native F2 HDK setup:

```bash
python3 -m tools.checkpoint_formats.tests.synth_initialized_bank \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration182/scala/bank/initialized \
  --out automations/checkpoint_loop/runs/aws-f2/iteration182/native-initialized-reverify
```

Exact commands, immutable inputs and diagnostic trials remain under
`automations/checkpoint_loop/runs/aws-f2/iteration182/`. Other annotation contracts,
wide/deep state, complete Rocket/FAME/bridge/memory/host integration and the full
localhost image build, AFI and physical migration remain pending.

Iteration 181 materializes synchronous memory pipeline owners already present
in both inventories: saved addresses for new/undefined readers, saved data for
old readers and old/undefined readwriters. RW data updates on enabled write
edges too, matching the actual passthrough emitter. Explicit physical pipeline
names bind to unchanged logical StateIDs. Pipeline updates and RAM writes
freeze together. Unsupported RW-new semantics and identifier collisions reject.

`SynchronousStateBankSpec` emits unchanged reference RTL with the inventoried
passthrough configuration and instrumented banks. Fresh EDA VCS passes
**21,970** checks, **454** reads, **1,816** response-stall cycles and ten complete
45-word fixture cuts. Every output matches that reference and an independent
public-input oracle over **2,905** observed edges / **202** functional edges.
Full debug VCD is retained. Native F2-part OOC synthesis passes at **133 LUTs /
32 registers**, estimated setup slack **+6.087 ns** at 140 MHz. Evidence lives
under `runs/aws-f2/iteration181/synchronous-vcs/synchronous-bank-m05mtez8/` and
`runs/aws-f2/iteration181/synchronous-vivado-ody0cfps/` (relative to the loop).
This is component evidence; complete Rocket hardware capture remains pending.

New `synth_checkpoint_top` / `audit_checkpoint_top` helpers preserve private
per-execution inputs and require exact VCS/native synthesis agreement. A later
mutable elaboration cannot substitute for actual compiled inputs. Audits check
current sources, execution, all cuts, sanitizer/negative logs, compile arguments,
native DCP CRC/identity and resource inventory. Fresh EDA audit passes and all
**14** `verify_checkpoint_top_audit` tamper cases reject. Historical iteration-180
receipts and its failed mutable-output audit remain unchanged.

After full Scala elaboration, run on EDA with `vcs-env.sh` sourced last:

```bash
python3 -m tools.checkpoint_formats.tests.verify_synchronous_bank_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration181/scala/bank/synchronous \
  --out automations/checkpoint_loop/runs/aws-f2/iteration181/synchronous-reverify
```

Iteration 180 adds opt-in `CheckpointCaptureTopKey` / `CheckpointCaptureTopBinding`.
FPGATop registers the Widget on its real control interconnect and appends its
stream after existing bridge streams before constructing the CPU stream
engine. The binding executes after SimWrapper and bridge module construction,
in the parent hardware context. A generated descriptor ROM is mandatory;
owner, counter and bank ports have no default acknowledgements or tieoffs.
Missing hardware connections fail FIRRTL initialization checking. Stock
recipes keep capture disabled and complete CPU ownership remains unsupported.

`CheckpointCaptureTopSpec` emits an explicit generated-storage fixture in the
real FPGATop, alongside an existing diagnostic bridge stream. The EDA runner
`verify_checkpoint_top_vcs` uses only public MMIO/AXI4 and functional ports.
All **7,858** checks pass on **33** words at **C=109 / 167 / 305**, including
**660** stalled DMA cycles, **1,926** frozen edges, a full two-frame stream
FIFO, missing owners, reset/write freeze, abort/drain/reuse and independent
access to the original stream. Each cut passes **66** decoder negatives and
**5,532** ASan/UBSan host checks. The complete top-generated checkpoint registry
constructor compiles against production headers. An actual bank-response bit
flip stops at the first data word at **C=109** while frozen. Full fixture
waveforms, source/generated hashes and raw logs are under
`runs/aws-f2/iteration180/top-vcs-corrected/checkpoint-top-yxwt2f1i/`
(relative to the loop). Native Vivado synthesizes this integrated fixture
FPGATop at **3,528 LUTs / 1,383 registers**, estimated setup slack **+4.282 ns**
at 140 MHz. This is out-of-context fixture synthesis, not a Rocket image.

After elaborating `CheckpointCaptureTopSpec` with
`-Dcheckpoint.widget.out=DIR`, run on EDA with `vcs-env.sh` sourced last:

```bash
python3 -m tools.checkpoint_formats.tests.verify_checkpoint_top_vcs \
  --generated DIR/top/enabled \
  --out automations/checkpoint_loop/runs/aws-f2/iteration180/top-reverify
```

Iteration 177 adds `CheckpointCaptureTransport.sv`, connected to the existing
`CheckpointCaptureCut.sv`. This is a synthesized component with an EDA VCS
fixture, **not a CheckpointBridge integrated into the Rocket FPGA image**.
The exact CPU recipe and its initialized manager configs remain unchanged.

Iteration 178 adds `GeneratedStateBankAccess`, `CheckpointCaptureWidget` and
native `checkpoint_capture_t`/`checkpoint_capture_session_t`. Generated storage
and the real FireSim control/stream interfaces now have independent component
verification. FPGATop registration, complete Rocket ownership/mapping and
physical checkpoint-image deployment are still required; these classes do not
enable CPU admission by themselves.

Iteration 179 adds `CheckpointCaptureDescriptors.fromGenerated`: complete
ordered bindings and both reference/instrumented circuit hashes are checked
against the independent inventory before one immutable descriptor set is
constructed. `CheckpointCaptureDescriptorROM` returns invalid all-zero outputs
for every out-of-range 32-bit ordinal. When Widget parameters include this
descriptor set, its hash/count must match the transport and its internal ROM
drives descriptor inputs; external descriptor pins have no authority in this
mode. The existing external-descriptor mode remains a component interface.

The same immutable descriptors generate host `checkpoint_capture_manifest_t`
metadata (including exact little-endian digest bytes) and the actual
`checkpoint_capture_t` registry constructor. Headers retain binding SHA256,
StateIDs, MMIO base, stream allocation and transport source hashes. This joins
transport/driver compatibility; it does not supply functional-memory or host
snapshots, complete CPU ownership, or automatic checkpoint publication.

`verify_generated_capture_network_vcs` checks actual generated banks connected
to that ROM and Widget. No handwritten bank-data or descriptor source supplies
the captured state. An independent functional-input oracle checks every word
through reset/write freeze, DMA stalls, missing fixture owners and abort/reuse.
Three cuts pass **1,014** checks, **48** bank reads, **49** decoder negatives
and **2,940** ASan/UBSan host checks per cut. The exact generated C++ initializer
validates the real VCS streams independently. Deliberate semantic bit corruption
stops at the first state word at **C=30**, frozen before publication. This is
finite component checking, not live CPU comparison. Full component VCD,
canonical VCS-origin fixture images and original source/command receipts are in
`runs/aws-f2/iteration179/network-vcs-final/generated-network-0fzl_g1v/`
(relative to the loop). The native localhost bank/Widget-with-ROM synthesis
reports **138 / 1,725 LUTs**, **67 / 692 registers**, and estimated setup slack
**+6.298 / +4.425 ns** at 140 MHz for the F2 part. Full Rocket synthesis/P&R,
AFI creation, deployment and hardware capture remain pending.

After elaborating `CheckpointCaptureDescriptorsSpec` with
`-Dcheckpoint.widget.out=DIR`, run on EDA:

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_generated_capture_network_vcs \
  --generated DIR/generated-network \
  --out automations/checkpoint_loop/runs/aws-f2/iteration179/network-reverify
```

The opt-in LowForm generator checks the entire current input inventory before
specializing modules per instance. It reads actual registers and added logical
asynchronous RAM ports, gates functional reset/update/write with `ckpt_freeze`,
and returns registered responses held until consumption, even after release or
abort. Dedicated `ckpt_reset` is independent of functional reset. State wider
than 64 bits/deeper than 65,535 words, unsupported readwrite RAM policies,
opaque/derived-clock/analog state and annotations
outside the explicit contracts above reject. Derived CombinationalPath caches
are invalidated and recomputed. The generated simulator and semantic StateIDs
remain separate. The fixture verifies 16 storage words; no whole-CPU coverage
is inferred.

The controller accepts a capture only while idle, freezes on the accepting
edge, waits for every declared owner, and reads logical bank words through
request/response handshakes. Descriptors come from an immutable generated ROM:
manifest ordinal, bank, slot, logical width and depth. Each descriptor is
latched before any bank request. Exactly one read can be outstanding. Bank
request and DMA payloads remain stable under backpressure; response latency
need not be fixed. Data with nonzero width padding rejects. Unsupported or
missing descriptors reject explicitly; this component supports widths 1–64,
1–65,535 entries, 8-bit bank and 16-bit slot selectors. Automatic wide-state
chunking and complete Rocket ownership remain required work.

The transport clock continues throughout freeze. All functional writes, resets,
token/channel movement, memory updates and host owners must honor the same
cut. Functional target reset must not reset the cut/transport controller.
Resetting the controller requires coordinated reset of the bank and DMA
endpoints; resetting it alone is not a cancellation protocol. An accepted bank
request must produce exactly one response, including on failure or abort.

An owner error, lost freeze, cycle drift, invalid descriptor, bank error or
noncanonical data invalidates the entire unpublished DMA stream and retains
freeze. An explicit abort releases owners and invalidates/flushes the stream.
If a bank read was already accepted, its response is discarded and a new
capture remains inadmissible until draining completes. An unresponsive endpoint
therefore prevents reuse rather than contaminating a later snapshot. The
bank must latch everything needed to return that response before accepting
its request. Premature publication reports an MMIO error and fails frozen.

The transport's MMIO interface is a single-request protocol with a backpressured
response; the global Widget adapts it to real FireSim NASTI. Register addresses
are byte offsets, all transfers are 32 bits, and writes to read-only/unaligned
addresses reject. Command values are exact, not composable bit masks.

| Address | Operation | Meaning |
| --- | --- | --- |
| `0x00` | write | `1` start, `2` publish/release, `4` abort |
| `0x04` | read | bit 0 ready, 1 freeze, 2 read enabled, 3 complete, 4 failed, 5 draining |
| `0x08` | read | bits 0–4 cut errors; 16 invalid descriptor, 17 bank error, 18 padding error, 19 sequence overflow |
| `0x10`, `0x14` | read | low/high halves of authoritative target cut |
| `0x18`, `0x1c` | read | low/high halves of transferred state-word count |
| `0x20` | read | generated entry count |
| `0x24` | read | complemented running CRC32C |
| `0x40` … `0x5c` | read | manifest SHA-256, least-significant 32-bit word first |

The global Widget wraps this request/response adapter in actual 32-bit FireSim
NASTI, independently buffers AW/W and holds all responses. It allocates a
256-byte control region and a real 512-bit StreamToHostCPU. Its clock continues
during the common freeze. Invalid/alignment/width/strobe/burst operations return
SLVERR without forwarding side effects. It adds these Widget-only registers:

| Address | Operation | Meaning |
| --- | --- | --- |
| `0x60` | read | bit 0 invalid shared stream; bit 1 lifetime frame-count overflow |
| `0x64` | write | exact `1`: acknowledge drain, only if producer quiescent and host count equals produced count |
| `0x68`, `0x6c` | read | cumulative accepted DMA frame count; low read latches a coherent high half |
| `0x70`, `0x74` | read/write | host cumulative consumed/discarded frame count for drain acknowledgement |

The produced counter survives capture, publication and abort, saturating with
sticky failure on overflow. Only a coordinated endpoint/stream reset clears
its epoch. An empty nonblocking pull does not establish drain completion;
the host must consume/discard every accepted frame and provide the exact
count. A new start stays blocked until acknowledgement succeeds. Shared
stream queues are not reset by a transport abort.

DMA frames are 64 bytes, little-endian at each integer field. `dma_last` marks
only the trailer. A generated manifest hash must be nonzero. The stream is a
transport envelope, independent of canonical checkpoint container formats.

| Bits | Common / header / data / trailer |
| --- | --- |
| 0–63 | magic bytes `FSMCKPT1` |
| 64–79 | version 1 |
| 80–95 | type: 1 header, 2 state word, 3 trailer |
| 96–159 | authoritative target cut |
| 160–223 | header zero; data zero-based word ordinal; trailer total words |
| 224–255 | header entry count; data entry ordinal; trailer CRC32C |
| 256–287 | header manifest hash starts at bit 256; data logical address |
| 288–303 | data logical bit width |
| 304–311 | data bank |
| 312–327 | data slot |
| 328–335 | data status, currently zero |
| 336–399 | data word |
| 400–511 | data reserved zero; header manifest hash ends at bit 511 |

Trailer bits above 255 are zero. CRC32C uses the reflected Castagnoli
polynomial `0x82f63b78`, initial state `0xffffffff`, and final complement.
It covers every byte of the header and every data frame, excluding the
trailer. The host decoder also independently checks the trailer's common
fields, count and reserved bits. CRC detects transfer corruption; it does not
authenticate provenance or establish complete state ownership.

`tools/checkpoint_formats/fpga_transport.py` validates complete length, manifest
compatibility, cut labels, word order, selectors, widths, padding, reserved
bits and CRC before returning any state. Its Level-2 adapter produces the
existing canonical `.rtlckpt` representation. This does not implement Level-1
ownership. The new C++ driver uses actual MMIO and StreamEngine calls, with
page-aligned bounded nonblocking transfers, independently supplied immutable
descriptor metadata, complete frame/CRC/cut/count validation and an explicit
post-publication release. Raw state bytes are exposed only after validation.
Transfer faults poison the session; abort drains against the cumulative
hardware frame count. Unknown consumed byte counts require coordinated reset.
The global coordinator must still snapshot all software/memory owners,
validate both independent images and trace, atomically publish without
overwriting valid history, and then authorize release. The new driver retains
the default unsupported aggregate checkpoint schema.

Fresh EDA verification (source the remote build environment first, then
`vcs-env.sh` last):

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_fpga_transport_vcs \
  --out automations/checkpoint_loop/runs/aws-f2/iteration177/transport-verified
```

The runner creates a unique directory with frozen sources, compiler argv,
native logs, fixture manifest/binding, actual public-port frames, canonical
component image and hashes. The fixture's independently sampled register/RAM
values are compared against every handshake. It exercises delayed bank reads,
DMA/MMIO stalls, five complete publications, malformed descriptors, owner
failures, lost freeze, cycle drift, stale-response draining, early publication
and fresh capture after failure. The strict host decoder rejects 39 damaged
variants of the actual VCS-produced stream, including rechecksummed semantic
framing corruption. This finite component test establishes no CPU live-shadow
or physical FPGA acceptance.

Local native Vivado synthesis uses `capture_transport_synth.tcl`,
`xcvu47p-fsvh2892-2-e`, 16 owners and 1,024 entries, with 140 MHz constraint.
The component uses 2,055 LUTs and 423 registers. Estimated post-synthesis
register-to-register setup slack is +4.816 ns; this is not routed F2 timing.
The HDK setup must be sourced from its own repository directory. Run through
the local F2 helper with backend `f2`; never synthesize on EDA.

Fresh iteration-178 runners (all VCS on EDA) are
`verify_generated_bank_vcs`, `verify_checkpoint_widget_vcs` and
`verify_fpga_capture_host` in `tools.checkpoint_formats.tests`. Generated inputs
come from `GeneratedStateBankAccessSpec` and `CheckpointCaptureWidgetSpec`;
native localhost synthesis uses `capture_components_synth.tcl`. Each runner
retains exact sources/generated artifacts, raw commands and native logs under
loop `runs/`. No fixture image is relabeled as FPGA origin.

Next: connect the registered FPGATop binding to the real compiler flow with complete
independent simulator/semantic mappings and descriptor ROMs, support the real
Rocket memory/width/annotation cases, connect global write/reset/token freeze,
and join complete
functional-memory/FASED/host ownership. Then build the exact checkpoint-enabled
Rocket recipe on localhost, create/bind AFI/AGFI and driver manifests, deploy
and capture actual F2 execution at every required cut. FPGA-reference
continuation, independent fresh EDA Level-1/Level-2 restores, sustained live
comparison beyond trace, waveforms and rolling FPGA recovery remain pending.

Use the existing [F2 workflow](aws-f2-workflow.md) and official
[custom-image guide](https://docs.fires.im/en/latest/getting-started-guides/aws-ec2-f2-getting-started/building-a-firesim-afi/).
