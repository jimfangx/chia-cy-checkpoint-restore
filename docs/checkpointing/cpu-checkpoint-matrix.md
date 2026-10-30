# CPU checkpoint matrix

## Current AWS F2 hardware acceptance (October 23, 2026)

Actual F2 checkpoint capture is required. See [aws-f2-workflow.md](aws-f2-workflow.md).
The older results below are retained metasim/component evidence and do not
establish FPGA capture or FPGA-to-VCS migration. The new Rocket public-image
baseline ran on real F2 hardware and passed; see [aws-f2-bringup.md](aws-f2-bringup.md).
Checkpoint-enabled images and hardware-origin checkpoint migration remain separate.

| Family | F2 workload / custom capture image | FPGA Level-1 to EDA metasim | FPGA Level-2 finite RTL replay | Live RTL / rolling hardware recovery |
| --- | --- | --- | --- | --- |
| Rocket (all four harts) | baseline verified: real F2 slot 0, public AGFI, self-check PASS at 44,104,832 cycles; custom capture image in_progress: bank/MMIO/DMA fixtures synthesize locally, ordinary whole-root bank trial enforces 2,120 typed dedup groups and passes exact native BUFGCE XDC pin contracts and retires only NoDedup definitions removed by actual native inlining; exact native RAM-style memory hints now translate and the final consumer emits late public host-widget XDC; native SimulationMapping now links and renames the exact TargetBox boundary and all local/nonlocal targets together; the ordinary whole-root trial rejects the FASED physical BUFGCE CE latch lacking a synthesized capture owner/common-low-phase cut; the regional/local probe also rejects eight inlined widget-local MMIO/DMA owners before connection; post-mapping InlineInstances runs before inventory/banking with complete concrete register/RAM rename provenance; exact stage emitter policy and retired abstract clock-gate source have immutable final-emission/history provenance; passive generated headers/defines retain exact-byte emission provenance; stage input retains immutable circuit/module history; consumed bridge extraction retains immutable circuit/connectivity history; consumed pre-link requests retain immutable circuit/mapping history; deduplication-history and target-box instance paths, global memory policies, consumed-input/channel-frequency context, XDC and memory-model labels translate with provenance; all seven FPGA plusarg instances have source-checked constant semantics; three physical BUFGCE owners, complete common-cut/memory/host binding and image P&R/AFI remain pending | pending | pending | pending |
| BOOM (speculative/in-flight) | pending | pending | pending | pending |
| Shuttle + Saturn (vector-active) | pending | pending | pending | pending |

Iteration 279 registers native request admission before RAM address borrowing,
using the existing phase owner and a version-3/four-edge policy. Independent
FIRRTL and EDA checks cover acceptance, all reset/release phases and transient
preparation hold loss. Version-2 component stream manifests bind emitted RTL,
complete bank bindings and transport RTL, so the changed readout protocol has a
distinct DMA identity. Eleven focused identity/stream tests, all 330 Scala tests / 52 suites plus
twelve preparation tests and 52 manager tests pass. Exploratory fresh EDA
queue semantics pass. All affected native builds pass; the 64-URAM component
improves 140 MHz OOC setup/hold estimates to -0.832/+0.073 ns. Full EDA transfer
passes four component cuts with 78,343,201 checks; waveform readback and all eight corrupted/rechecksummed negatives pass. All six
compiled mutations, 348 Python / 47,219 ASan/UBSan host assertions, sixteen fresh
bank/region scopes and complete retained bridge/capture/snapshot/restore/widget
plus six additional waveform audits pass. Final source/artifact/protected-input/resource audits pass; exact commands and
receipts are under `runs/aws-f2/iteration279/`. Hardware CPU ownership, full image,
physical cuts and paired zero-edge/finite/live/rolling migration remain pending;
no hardware column advances.

Iteration 278 strengthens the exact-queue component's complete ordered owner
coverage. The auditor and pre-acceptance VCS monitor reject skipped/duplicated
addresses or owners even when the payload agrees with the reported selector
and the CRC is repaired. Seven focused tests, localhost 64-URAM synthesis,
fresh EDA transfer at component cuts 6486/6622/6855/7185 and all five compiled
mutations pass. Independent
full-wave readback checks 56 original native vectors, three router vectors /
22,051,251 samples and all four complete 196,728-word streams; eight corrupted/
rechecksummed negatives reject. All sixteen fresh bank/region scopes, complete
retained host/FCFS/queue/bridge/capture/transport/snapshot/restore/widget scope
and six additional waveform audits also pass. Commands and receipts are under
`runs/aws-f2/iteration278/`. Final source/receipt/artifact/protected-input and
AWS/native resource audits pass; no tagged runtime, pending AFI or build remains.
This closes a component evidence hole, without
advancing any FPGA CPU capture, restore, live comparison or rolling column.

Iteration 277 adds an isolated four-queue native capture/router using the exact
Rocket Queue_56 512-by-6,144 ULTRA shape. Its twenty original descriptors and
6,656-bit native vector remain component evidence. The complete Scala run passes
330 tests / 52 suites plus twelve preparation tests. Native exact-geometry
synthesis maps 64 URAMs without distributed-RAM fallback; full-image timing and
production common-cut/owner integration remain pending. Final source-bound native,
four-cut EDA and independent full-wave/frame checks are ongoing under
`runs/aws-f2/iteration277/`. See [f2-rocket-native-queues.md](f2-rocket-native-queues.md).
No FPGA image/capture, paired CPU restore/live or rolling acceptance advances.

Iteration 276 factors native READ qualification without adding state or fault
latency and explicitly preserves raw phase encoding. Native F2-part OOC
placement/routing preserves all 1,666 original register identities and meets
140 MHz with +0.540 ns setup / +0.047 ns hold, 2,507 LUTs and zero routing errors.
This is the 1,036-bit component; shell/I/O budgets, clock insertion reference and
full-image closure remain pending. Fresh EDA SP2 passes 131,072 policy combinations /
393,216 comparisons, the missing-error mutation, all seven native geometries /
105 faults / 116 debug waves and the full MMIO/DMA 112-capture / 42-fault /
21-recovery / 74-wave scope. All Scala/manager/Python/sanitizer/FCFS/fixture,
complete snapshot/restore and sixteen bank/region scopes with six independent
wave audits pass after the full seven-source-set native refresh. Receipts and
commands are under `runs/aws-f2/iteration276/`. Exact Rocket still rejects
production physical CE/common-cut ownership. Complete image/AFI, physical cuts,
paired zero-edge/finite/live CPU migration and rolling hardware recovery remain
pending/in_progress; no hardware acceptance column advances.

Iteration 275 connects the coordinated native snapshot to component MMIO/DMA.
Final-source localhost F2-part synthesis maps all 1,666 register bits, uses 2,597
LUTs and retains four SYNC gates / one falling-edge mask with no combinational
or latch loops. OOC setup at 140 MHz is −0.859 ns; full-image closure is pending.
Fresh EDA SP2 passes seven vector geometries, thirteen identity planes per healthy
process, 112 independently audited frame captures, 42 fault cases, 21 abort/
recovery processes and four compiled mutations before the relevant acknowledgement.
All 74 debug waves are retained. The separate original-native functional hold
matches the physical root's last edge. All affected native builds, full Scala/manager/Python/sanitizer/FCFS/fixture
checks, sixteen fresh bank/region scopes and six independent waveform audits
pass; nine immutable native receipts retain their original provenance. Final
source/receipt/resource auditing passes. See the iteration-275 receipts.

These are component results. Whole-Rocket production ownership still rejects
capture-image generation; full localhost P&R/AFI, physical all-hart cuts, paired
zero-edge/finite/live CPU migration and rolling hardware recovery remain pending.
No hardware acceptance column advances. See
[f2-native-capture-transport.md](f2-native-capture-transport.md).

Iteration 274 verifies the common physical/native cut, complete staging and
backpressured reader-drain/release sequencer. Native F2-part OOC synthesis retains
1,189 register bits / 575 LUTs, default SYNC gates and no combinational/latch loops;
the queue wrapper preserves native RAMB inference. Fresh source-bound EDA SP2
passes seven geometries, 105 negative processes, seven damaged/incompatible
receipt rejections, 113 independent register-wave audits and 114 debug waves.
Four emitted-queue component cuts (75/129/190/258) pass 180 bank reads, 1,324
serial words and stalled-reader release. Compiled corruption stops before the
first read acknowledgement. All Scala/manager/Python/sanitizer/FCFS/component,
sixteen bank/region and retained snapshot/restore scopes pass. Initial unknown
selector snapshots remain verbatim; no canonical hardware image is published.
See [f2-native-state-capture.md](f2-native-state-capture.md) and iteration-274
commands/receipts under `runs/aws-f2/iteration274/`.

These are component results. The whole-Rocket compiler still rejects physical
CE/common-cut production ownership. Composite restore, all-four-queue/host/
pre-FAME integration, full image/AFI, every physical CPU cut, paired zero-edge/
finite/live migration and rolling hardware recovery remain pending/in_progress.
No hardware acceptance column advances.

Iteration 273 adds opt-in complete snapshot staging/control restore. Native
localhost F2-part synthesis retains 1,107 owner bits; the enabled standalone
owner uses 978 LUTs. Fresh EDA SP2 passes six geometries, 30 directed fresh
restores plus eight emitted/gated queue staging restores, 6,772 per-bit loads,
72 negative processes and 117 independent original-register waveform audits.
Compiled restore corruption stops at the first complete readback before word
acknowledgement; all 147 new debug waveforms are retained. Binary queue donors
are separately restaged after completed legal reads at the same frozen target
label, retaining original initially unknown selector snapshots verbatim.
All 329 Scala / 51 suites plus twelve preparation, Python 337 / manager 52 /
sanitizer host 47,219 checks, sixteen fresh bank/region scopes, six independent
bank/shell waveform audits and retained component/FCFS scope pass. Seven stale
native scopes were rebuilt, nine immutable matching receipts retained, and the
strict source consumer remains unchanged. These are staging-owner component
results. Full Rocket compilation still rejects physical CE/common-cut ownership.
Production all-four-queue/common-clock/transport ownership, complete image/AFI,
physical captures and paired zero-edge/finite/live CPU migration/rolling recovery
remain pending/in_progress. No hardware column advances. See
[f2-native-snapshot-restore.md](f2-native-snapshot-restore.md) and iteration-273
commands and receipts under `runs/aws-f2/iteration273/`.

Iteration 272 verifies atomic staging of the native queue observation vector
before borrowing RAM readers. The reduced component samples 28 fields / 1,036
bits and exposes its separate staging/control owner. Native OOC retains all
1,107 new register bits and two RAMB primitives per selected queue and untouched
sibling. Fresh source-bound EDA SP2 passes five vector geometries / 60 negative
processes, all seventeen words at each of four cuts, 2,708 serial samples while
the live vector changes 2,707 times, 364 underlying queue reads and 360 gated
wrapper reads. Compiled semantic corruption stops before first acknowledgement;
68 new debug waves are retained. Complete compiler 329 Scala / 51 suites plus
twelve preparation, Python 337 / manager 52 / sanitizer host 47,219 assertions,
all sixteen fresh bank/region scopes, six independent waveform audits and all
retained component/FCFS scopes pass. Seven stale native scopes were re-synthesized
with complete native XDC; nine exact matching native receipts retain original
provenance. No source, owner, constraint or sanitizer guard was relaxed.

This is component staging, with all-four-queue production clock/transport/restore
ownership still pending. Root compilation still rejects physical CE/common-cut
ownership. Full image/AFI and every actual FPGA capture, paired CPU restore,
finite/live migration and rolling recovery requirement remain pending/in_progress.
No hardware column advances. See
[f2-native-state-snapshot.md](f2-native-state-snapshot.md) and iteration-272 runs.

Iteration 271 synthesizes complete derived synchronous queue-state observation:
fourteen fields / 518 bits per reduced selected queue and fourteen / 1,664 bits
per actual Rocket Queue_56. Independent compiler auditing verifies all four real
queues, 56 fields / 6,656 bits, and ancestor connectivity. Original StateIDs and
selectors remain separate. Native/EDA mapping accounts for every actual added
register, including `ram_r_data_pipe_0`, with exact clock/sampling equations.

Final checks pass 329 Scala / 51 suites plus twelve preparation, 25 targeted
Scala, 337 Python / 52 manager, 47,219 sanitizer host assertions, 27 selected
native OOC and 26 EDA SP2 scopes. BLOCK retains two RAMB primitives per selected
queue/sibling; exact ULTRA retains 16 URAM / zero LUTRAM. EDA passes 364 reads /
four cuts / 185,836 observation comparisons, 24 metadata/emission negatives and
two compiled faults before acknowledgement, with full waves. All retained
readback, continuation, corruption, waveform, FCFS and host scopes remain covered.
Source guards required seven native re-syntheses; nine exact source-matching
receipts remain valid. Original failures and repairs are retained in the logs.

The root still refuses CE/common-cut ownership, and the regional diagnostic
retains 1,042 uncovered original entries and eight live transport conflicts.
Derived observation has no atomic snapshot/restore/complete capture owner.
Full image/AFI, physical cuts, paired zero-edge/finite/live CPU migration and
rolling hardware recovery remain pending/in_progress; no hardware column
advances. See [f2-synchronous-state-observation.md](f2-synchronous-state-observation.md)
and current receipts/commands under `runs/aws-f2/iteration271/`.

Iteration 270 binds each synchronous native queue bank to immutable original
source and ordinary-bank provenance, then independently reconstructs the complete
adapter during standalone validation. Targeted 24 Scala checks pass, including
ten coherently rehashed equation faults and four provenance/selector/policy
negatives. Full current-source checks pass 328 Scala tests / 51 suites plus twelve
preparation, 337 Python / 52 manager tests, 47,219 sanitizer assertions, all
retained native and fresh EDA SP2 component scopes. Native BLOCK/ULTRA inference
is retained, with 16 URAM / zero LUTRAM for exact Rocket ULTRA. EDA queue reads
364 words at four cuts and rejects its compiled first-word fault before ack;
NASTI compares 72,000 cycles and sixteen negative processes. Fresh root/regional
compilers still refuse CE/common-cut and eight live transport conflicts, with
1,042 original entries uncovered. This changes no hardware acceptance column: complete image/AFI, physical capture, paired zero-edge/finite/
live migration and rolling FPGA recovery remain pending. See
[f2-synchronous-bank-provenance.md](f2-synchronous-bank-provenance.md).

Iteration 269 implements v2 synchronous native queue access. Actual localhost
Vivado passes BLOCK mapping with two RAMB primitives in each of two selected
queues and their untouched sibling, and exact Rocket Queue_56 ULTRA mapping
with 16 URAM / zero distributed-RAM or BRAM fallback. Registered full-width
write-first forwarding preserves original New semantics while the physical
reader uses an Old/data-register template. Original address StateIDs remain.
Targeted six Scala tests, thirteen metadata negatives and EDA VCS 364-read /
four-cut functional, cancellation, release and first-word corruption checks pass.
Final current-source checks pass 327 Scala / 51 suites plus twelve preparation,
337 Python / 52 manager / 47,219 sanitizer assertions, 27 native OOCs and
26 native-bound fresh EDA SP2 scopes. These remain component feasibility/readout
results. Fresh production still rejects physical CE/common-cut ownership and
eight live transport freeze conflicts, with 1,042 original entries uncovered. V1 address-register BLOCK/ULTRA
failures remain retained as failures. See
[f2-synchronous-queue-memory.md](f2-synchronous-queue-memory.md). No complete
image/AFI or FPGA-origin checkpoint/migration/live/rolling column advances.

Iteration 268 adds concrete shared trace-queue banks while retaining original
StateIDs and concrete storage annotation ownership. The fresh exact-Rocket probe
now has 11,113 descriptors (twenty new original queue owners), 1,042 absent
entries and eight mandatory live-transport freeze conflicts. The reduced native
queue test **fails** the original BLOCK RAM policy: instrumented queues fall
back to LUTRAM and the primitive audit rejects them. Actual ULTRA implementation
remains unvalidated. The twenty new descriptors are addressability evidence,
not physical capture coverage. The full compiler sweep (325 tests / 51 suites plus twelve preparation), four
separate fixture regeneration checks, Python 337 / manager 52 / sanitizer host
47,219 assertions and all twenty-five positive native / fresh EDA component
scopes pass. Separate diagnostic RTL passes 361 reads / four cuts and stops a
compiled first-word fault before acknowledgement, with full waves and eight
rehashed metadata rejections. Native RAM acceptance remains false.
See [f2-shared-queue-readout.md](f2-shared-queue-readout.md). Full image/AFI,
checkpoint-enabled F2 execution and every FPGA-origin migration/live/rolling
column remain pending/in_progress. No hardware column advances. Commands and
immutable current/failure receipts are under `runs/aws-f2/iteration268/`.

The required Rocket hardware cuts remain individually pending:

| Hardware cut, all four active harts | FPGA capture/reference | FPGA Level-1 / Level-2 zero-edge and finite restore | Sustained live RTL / recovery |
| --- | --- | --- | --- |
| Early active workload | pending: no checkpoint-enabled image | pending | pending |
| Warmed caches | pending: no checkpoint-enabled image | pending | pending |
| Outstanding memory traffic | pending: no checkpoint-enabled image | pending | pending |
| Late active workload | pending: no checkpoint-enabled image | pending | pending |

Iteration 267 adds exclusive host retry of an interrupted immutable MMIO shadow
and completes iteration-266 staging-restore verification. Final 321 Scala / 50
suites plus twelve preparation, 337 Python / 52 manager tests, 25 native OOCs
and 25 fresh native-bound EDA SP2 component scopes pass. The ASan/UBSan host
matrix executes 47,219 assertions, 739 safe retries, 81 unsafe rejections and
26 invalid epochs including twelve changes at the final identity check.
Fresh component processes independently read back all fifty endpoint/adapter/
staging registers, compare 312 indexed continuation rows and reject four
semantic/compiled negatives. Compiled saved-payload faults stop at bit 759
before a normal edge or interface acknowledgement. These are fixture images.

Current production still rejects CE/common-cut ownership and eight live-transport
freeze conflicts. The explicit 1,062-entry deficit covers 12,644,329 bits / 186
memories, beyond which complete functional DRAM, host and pre-FAME ownership
remain pending. Full local image P&R/AFI, actual F2 cuts, paired hardware-origin
migration, live CPU shadowing and rolling recovery remain pending/in_progress;
no hardware migration column advances. See
[f2-widget-shadow-recovery.md](f2-widget-shadow-recovery.md) and
[f2-rocket-owner-deficits.md](f2-rocket-owner-deficits.md). Current raw commands
and immutable receipts are under `runs/aws-f2/iteration267/`.

Iteration 265 shares the actual widget endpoint equations with an opt-in
common-epoch restore component: eight local plus 38 adapter registers, 758
canonical bits. Production retains absent restore controls and all complete
ownership guards. Final 320 Scala / 50 suites plus twelve preparation, 337 Python /
52 manager tests, 23 native OOCs and 23 fresh native-bound EDA SP2 component scopes
pass, including ASan/UBSan, FCFS, atomic-cut and independent wave/corruption audits.
The new 32/4 and exact Rocket 32/12 endpoint matrix passes twelve explicit cuts /
24,000 continuation cycles and four negatives; the retained adapter matrix adds
72,000 cycles / sixteen negatives. Independent original-register waves find
compiled localData corruption at bit 195 while held with zero normal edges and
no interface acknowledgement. Exact Rocket endpoint OOC uses 700 LUTs / 519 flops,
including separately unsupported shadow storage. All original registers remain
on the raw positive clock. These are component results, with no full-image timing
closure. No hardware migration column advances. See
[f2-widget-epoch.md](f2-widget-epoch.md).

The iteration-264 controller replay failed its final integrity audit: rerunning
preflight overwrote a pinned setup receipt. Iteration 265 preserves that failure
and uses unique, artifact/source-bound preflight attempts with atomic selection.
Real repeated AWS/native checks, strict source/receipt/protection/resource audits
and corruption rejection pass. Diagnostic helper-copy, inherited source-list and
positional fixture failures were preserved and fully recovered without reducing
scope. Exact production still rejects CE/common-cut ownership and eight live
transport-local conflicts, retaining 1,062 uncovered entries. Image P&R/AFI,
checkpoint-enabled F2 cuts, paired hardware-origin migration, live CPU shadowing
and rolling FPGA recovery remain pending/in_progress. Receipts and runnable
commands are under `runs/aws-f2/iteration265/`.

Iteration 264 adds opt-in held restoration of all 38 original NASTI adapter
registers. Production keeps the port absent and retains all ownership guards.
Final 319 Scala / 49 suites plus twelve preparation, 336 Python / 45 manager,
twenty-one native OOC and twenty-one fresh native-bound EDA SP2 scopes pass.
The adapter matrix independently reads back four geometries / 24 component cuts
and compares 72,000 continuation cycles, with successful active read/write/
response/backpressure coverage and sixteen negative processes. Exact-Rocket
adapter OOC uses 289 LUTs / 258 raw positive-edge registers. Independent review
found and corrected an all-malformed LCG stimulus; final artifacts use corrected
traffic and explicit coverage/VALID-retention assertions. Physical-widget and
all retained waveform/negative/ASan/UBSan/FCFS checks pass. Exact production
still rejects CE/common-cut ownership and eight self-freezing locals, retaining
1,062 uncovered entries. Complete image admission, physical capture and every
physical migration column remain pending/in_progress. No FPGA checkpoint or
CPU migration is established. Receipts and exact commands are under
`runs/aws-f2/iteration264/`; see [f2-nasti-restore.md](f2-nasti-restore.md).

Iteration 263 adds atomic observation of all 38 original NASTI adapter
registers to the real layout-2 widget shadow, with runtime layout/version and
exact-bit-count checks before capture. Independent exact Rocket mapping binds
258 original adapter bits / 272 padding bits to StateIDs/native renames and
rejects seven corrupted descriptions, retaining their unsupported restore status.
Final 319 Scala / 49 suites plus twelve preparation, 336 Python / 45 manager,
seventeen native OOC and seventeen native-bound EDA SP2 scopes pass. All waveform
and physical evidence corruption audits pass; ASan/UBSan host executes 1,890 checks.
The physical fixture completes six component cuts / 240 full word reads / 65,361
checks / 3,851 stalled cycles, with compiled first-divergence cases. Native widget
resources are 2,766 LUTs / 1,978 registers, including 1,040 audited raw positive-edge
shadow registers. OOC source-policy timing remains negative; full-image closure is
unestablished. The three missing-XDC preparation failures were preserved and
recovered through the actual native constraint emitter without reducing scope.
Exact production still rejects physical CE/common-cut ownership, and regional
connection still rejects eight self-freezing locals with 1,062 uncovered entries.
No complete image, AFI, FPGA checkpoint or CPU migration is established. Every
physical migration column remains pending. Receipts and exact commands are under
`runs/aws-f2/iteration263/`; see [f2-nasti-shadow.md](f2-nasti-shadow.md).

Iteration 262 connects an immutable live-widget MMIO shadow and host-session
observation/recovery API. Final 317 Scala / 48 suites plus twelve preparation,
336 Python / 45 manager, seventeen native OOC and seventeen source-matched EDA
component scopes pass, retaining ASan/UBSan host, FCFS, atomic-cut and all waveform
audits. Physical-widget OOC uses 2,641 LUTs / 1,661 registers, with 811 audited
raw positive-edge shadow registers. Six fixture cuts / 144 word reads pass;
a compiled staging defect stops at its first word without AXI acknowledgement.
Exact Rocket still refuses eight self-freezing locals and retains 1,062 uncovered
entries, including four staging owners. No complete owner mapping, image, AFI,
FPGA capture or CPU migration is established. All physical migration columns stay
pending. Exact receipts/commands are under `runs/aws-f2/iteration262/`. See
[f2-live-widget-shadow.md](f2-live-widget-shadow.md).

Iteration 261 composes the 181 FPGATop and two F1Shim original local owners
with the existing regional readout, yielding 11,093 diagnostic descriptors and
1,058 uncovered original functional entries. Independent exact-source audit
checks all local identities, equations, selectors and four hart RF annotations.
The actual compiler explicitly rejects eight inlined CheckpointCaptureWidget
owners: freezing them would stop the same MMIO/DMA transport required to drain
capture. Their original widget identity and exact native storage renames bind
`transport-freeze-conflicts.json`; no connected image or physical capture is
emitted. The opaque transport and full atomic/memory/host/pre-FAME coverage remain
unsupported. Full 316 Scala / 47 suites plus twelve preparation tests, 336 Python /
45 manager tests, sixteen native and sixteen fresh EDA SP2 scopes, ASan/UBSan,
FCFS/cut checks and six waveform audits pass. The mixed component uses 2,165 LUTs /
1,128 registers and passes 8,452 checks / four fixture cuts / 288 reads / 864
stalls. Eight rehashed corruptions reject, and the compiled local defect stops at
its first word with freeze held and no acknowledgment. Final source/receipt/
resource/protection audit passes. Receipts and raw commands are under
`runs/aws-f2/iteration261/`. Every physical migration column remains pending. See
[f2-shell-region-routing.md](f2-shell-region-routing.md).

Iteration 260 adds enclosing-module local-state banks, separately reconstructing
181 FPGATop and two F1Shim original owners while retaining original children and
annotation paths/order. The local selectors are not yet composed with the
regional transport; its 1,241 uncovered functional entries and one unsupported
transport owner remain explicit. Nine focused checks pass, including differing
nonlocal shared-memory initialization owners and preservation of all four hart
register-file model targets. Full 311 Scala / 46 suites plus twelve preparation
checks, 336 Python / 45 manager tests, fifteen native and fifteen fresh EDA SP2
scopes pass, with ASan/UBSan host, FCFS, atomic-cut and five independent waveform
audits retained. The shell fixture uses 122 LUTs / 163 registers and passes
4,280 checks / 69 reads / 347 stalls / four component cases; eight rehashed
corruptions reject and the compiled first-word defect stops before acknowledgment.
Complete source/receipt/resource integrity passes. Every physical migration
column remains pending. Receipts and exact commands are under
`runs/aws-f2/iteration260/`. See
[f2-shell-state-access.md](f2-shell-state-access.md).

Iteration 259 runs the real registered-widget regional compiler hookup for the
exact Rocket recipe, binding 10,910 descriptors / three CE slots to MMIO 0x200,
CPU stream 4 and the generated host constructor. Its final status is
`identity_bound_incomplete_image_guard_required`; image emission still rejects.
The manifest retains 1,241 uncovered functional entries and one transport owner.
Regional-only v3 inline normalization preserves exact FIRRTL/annotations/storage;
a native wiring wrapper retains and validates the original clock label. Default
v2/wiring behavior is unchanged. Thirty-six focused checks and the complete
final-source Scala sweep pass (302 tests / 45 suites plus twelve preparation
tests). All fourteen native and fourteen fresh EDA SP2 scopes pass, with all four
independent waveform audits, ASan/UBSan host, FCFS and cut checks retained.
All 336 Python / 45 manager tests and nine rehashed metadata negatives pass.
Full common-cut, memory/host/pre-FAME and added
control-state coverage, image/P&R/AFI and every physical migration column remain
pending. See [f2-region-compiler-probe.md](f2-region-compiler-probe.md).

Iteration 258 adds an explicit ordered whole-host source-policy permission for
regional banking, retaining typed storage, compiler history and opaque-owner
identity. Compiler and independent auditor reject unknown annotations whose
concrete execution sets change through shared-leaf specialization or added mask
gates. Full **287 Scala / 43 suites plus twelve preparation tests, 336 Python /
45 manager, fourteen native and fourteen fresh EDA SP2 scopes** pass, retaining
ASan/UBSan host, FCFS and cut checks. The new component passes 8,157 checks / four
cuts / 272 words / 1,716 stalls. Independent waves retain 4,064 frozen samples and
stop the compiled payload defect at cut 81 / word 32 before release. Nine compiler
source-policy rejection cases and six adversarial Python tests pass. Native OOC
resources are 5,276 LUTs / 1,979 registers / six BUFGCEs, with negative 140 MHz
setup/hold estimates and no full-image timing closure. The fixture retains forty
original executions / fourteen descriptors / twenty routes; **550 functional
entries plus transport state remain uncovered**. Exact production still rejects
the FASED physical CE/common-cut owner. Production hookup, complete ownership,
image/P&R/AFI and every hardware-origin CPU migration column remain pending. See
[f2-region-source-policy.md](f2-region-source-policy.md), the progress entry and
`runs/aws-f2/iteration258/verification-commands.json`.

Iteration 257 binds the combined regional descriptor identity to the real
reserved transport and registered host constructor. Full **285 Scala / 43 suites
plus twelve preparation tests, 330 Python / 45 manager, thirteen native and
thirteen fresh EDA SP2 scopes** pass, retaining ASan/UBSan host and FCFS checks.
The bound component passes 8,157 checks / four cuts / 272 words / 1,716 stalls and
20 generated-host sanitizer checks. Twelve rehashed identity mutations reject;
twenty retained connection mutations also reject. Independent waves retain 4,064
frozen samples and stop the actual compiled payload defect at cut 81 / word 32
before release. OOC resources are 5,424 LUTs / 1,980 registers / six BUFGCEs;
negative 140 MHz setup/hold estimates establish no timing closure. The generated
header/image guards remain active, with 550 original functional entries and
opaque transport state uncovered. Exact production still rejects the FASED
physical CE/common-cut owner. Source-context and complete simulator/host/pre-FAME
ownership, new control-state capture/exclusion, image/P&R/AFI and every
hardware-origin CPU migration column remain pending. See
[f2-region-widget-identity.md](f2-region-widget-identity.md), the progress entry and
`runs/aws-f2/iteration257/verification-commands.json`.

Iteration 256 connects the shared disjoint-region readout to the **existing**
registered widget across concrete enclosing ancestors. An immutable permission
allows global analysis of the exact reserved transport while preserving its
unsupported owner and actual emitted RTL; default inventory/image admission stays
strict. The new fixture retains 40 original executions / fourteen descriptors /
four CE identities / twenty routes and leaves 550 functional entries / 638 words
plus transport state uncovered. Twenty rehashed mutations reject. Final full
283 Scala / 43 suites plus twelve preparation tests, 330 Python / 45 manager,
twelve native and twelve fresh EDA SP2 scopes pass, including ASan/UBSan host and
FCFS checks. Actual component MMIO/DMA passes 8,157 checks / four cuts / 272 words /
1,716 stalls. Independent waves retain 4,064 frozen samples and stop the compiled
payload defect at cut 81 / word 32 before release. Complete native final-host XDC
includes both RAM hints; four literal board-pad placements are explicitly deferred
from OOC. Resources 5,276 LUTs / 1,979 registers / six BUFGCEs and 140 MHz OOC
setup/hold −0.031/−0.074 ns establish no full-image closure. Failed attempts remain
preserved; only failed/stale native receipts were actually regenerated after the
repair, with all twelve scopes retained. Independent bounded EDA COW maintenance
preserves all history and the full regression scope. Exact production generation
still rejects the FASED physical CE/common-cut owner. Production source-context,
identity, complete simulator/host/pre-FAME ownership, image/P&R/AFI and every
hardware-origin capture/CPU migration column remain pending. See
[f2-region-widget-graft.md](f2-region-widget-graft.md), the progress entry and
`runs/aws-f2/iteration256/verification-commands.json`.

Iteration 255 repairs the EDA input-sync ENOSPC failure through kernel-verified
copy-on-write extent sharing, preserving historical contents, independent inodes
and modification times. Independent full-file SHA-256/metadata auditing checks
145 completed pairs; actual XFS self-tests check unequal-data rejection and
subsequent-write isolation. Fresh complete 330 Python / bank / widget / ASan/
UBSan host / FCFS / cut and eleven pinned EDA SP2 component scopes pass. All 45
controller tests pass on the native manager. The first extra controller run on
EDA failed importing Ray; backend correction preserves the full test scope,
and the complete VCS batch reran successfully with fresh receipts. The shared
multi-region fixture retains 8,242 checks / four cuts / 280 words / 840 stalls
and independent full debug/first-divergence waveform auditing. Native/Scala/RTL
sources are unchanged and existing synthesis evidence is re-audited. Capacity
remains limited; see [eda-artifact-capacity.md](eda-artifact-capacity.md).
No new checkpoint image, FPGA capture or CPU migration acceptance follows.
All hardware-origin columns and the production common-cut/owner deficits remain
pending. Commands and immutable receipts: `runs/aws-f2/iteration255/`.

Iteration 254 implements the checked multi-region in-place graft and one raw
readout/descriptor adapter with a shared mask/reset/read interface. Final repaired
Scala passes 280 tests / 42 suites plus twelve preparation tests. Independent
original/installed storage auditing retains all 2,292 original executions and
10,910 selected entries / three CE identities, with 1,189 functional entries /
198,818 words still uncovered. Nine graft mutations and eight retained region
mutations reject. The new component passes native synthesis and source-matched
EDA SP2: 8,242 checks / four cuts / 280 words / 840 stalls, reset cancellation and
owner failures. Its independent waves retain 1,407 frozen samples and stop the
compiled CE defect at cut 1 / cycle 36 / word 66 before response acknowledgement.
OOC resources are 2,047 LUTs / 995 registers / six BUFGCEs; setup/hold +2.027/−0.074
ns has unconstrained I/O and establishes no full-image closure. The complete
repaired scope passes 330 Python / 40 loop / eleven source-matched native /
eleven fresh EDA SP2 checks, preserving all ASan/UBSan host, FCFS and connected
fixture scopes. Final source/receipt/wave/resource auditing passes; failed
attempts and source-epoch rejections remain preserved. See
[f2-native-region-graft.md](f2-native-region-graft.md) and the progress entry.
Production common-cut/widget admission remains unbound. No checkpoint image,
FPGA capture or CPU restore acceptance follows; all hardware columns stay pending.

Iteration 253 verifies native-region request/response routing and static selector
composition for the same original host. The retained exact Rocket DUT/FASED
selection describes **10,910 entries / all three physical CE identities**, leaving
**1,189 functional entries / 198,818 words**. Independent original register/RAM/
pipeline, topology and CE dependency reconstruction rejects **eight rehashed
mutations**. Global/local ordinals, selectors and CE sample bits are explicit.

Final **276 Scala / 41 suites plus twelve preparation tests / 330 Python / 40 loop /
ten source-matched native / ten fresh EDA SP2** scopes pass. The router passes
**6,155 checks / 201 requests / 199 responses / four invalid selectors / 2,380
stalls / two reset cancellations**, one- and three-region boundary configurations,
and five time-zero configuration rejections. Independent debug waves prove the
compiled wrong-owner fault stops at **request 2 / response 1** with both response
acknowledgements zero. Its OOC fixture uses **99 LUTs / three registers** with
unconstrained I/O; this is no image timing-closure result. Existing four connected
variants and ASan/UBSan host/FCFS checks pass. Failed harness attempts remain
preserved; five affected native scopes were regenerated after the repairs, and
the complete EDA scope reran. Six older generated FIRRTL/RTL/XDC files remain
byte-identical. See [f2-native-region-routing.md](f2-native-region-routing.md) and
`runs/aws-f2/iteration253/accepted-receipts.json`.

The router/metadata does not connect the FASED execution into a production
common cut. The ordinary single-region census still has **1,947 uncovered
functional entries / 298,428 words plus the FASED physical CE owner**; fresh
exact generation still rejects that missing owner. Multi-region in-place graft,
complete global ownership/identity, image/P&R/AFI, actual four-hart capture and
paired CPU zero-edge migration, finite/live RTL and rolling recovery remain
pending. No new runtime or AFI was launched. Every FPGA-origin acceptance column
remains pending.

Iteration 252 verifies selected-source compiler context at the widget connector.
Every source context annotation must already occur exactly once in the original
pre-inline and projected enclosing hosts; history is neither renamed nor inserted.
The original-input check rejects duplicates that FIRRTL inlining can coalesce.
Independent auditing reconstructs context snapshots and inline annotation hashes,
including strict matching of the optional nested consumed-input class hint.

Fresh **272 Scala / 40 suites plus twelve preparation/directed executions / 330
Python / 40 loop / nine native / nine EDA SP2** scopes pass. Seven source context
kinds retain eighteen connector rejections and **34 independently rejected
mutations**, with **641 sources / 686 inputs** matched. All four connected
variants pass **5,165 checks / four cuts / 136 words / 900 stalls**; the bound
host initializer retains **20 ASan/UBSan checks**. Twelve full debug waves prove
**2,704 frozen samples** per healthy variant and the actual compiled defect at
**cut 81 / word 0 / byte 42**, before release. Six generated FIRRTL/RTL/XDC files
remain byte-identical to the prior component. Resources stay **4,570 LUTs / 1,655
registers / three BUFGCEs / 671 raw-clock registers**; OOC setup/hold
**+0.326/−0.074 ns** retains unconstrained I/O and does not establish timing closure.
Fresh exact-Rocket bank-context auditing retains **2,456 source / 25 context /
20 context kinds / 2,379 projected storage annotations**.

Fresh complete Rocket compilation still rejects the FASED CE/common-cut owner;
**1,947 functional entries / 298,428 words and one physical CE owner** remain
uncovered. Complete enclosing ownership/identity, image/P&R/AFI, four-hart F2
captures and paired CPU migration with finite/live RTL and rolling recovery stay
pending. No image, AFI or runtime launch occurred. All FPGA-origin acceptance
columns remain pending. See [f2-widget-source-context.md](f2-widget-source-context.md)
and `runs/aws-f2/iteration252/accepted-receipts.json`.

Iteration 251 verifies typed selected-source contract merging at the existing
widget graft. Six source contracts become eight translated contracts through a
typed circuit rename and a validated union with host contracts. Conflicting
initialization policies/files, unmatched global policies, circuit-wide source
inlining and stale source state reject. Source-local XDC is applied in its
selected module/instance scope, followed by merged host XDC at the root. Exact
Tcl matching rejects a coherently rehashed scope omission. The initial real
Vivado unscoped-pin failure remains preserved; no constraint was dropped.

Fresh **271 Scala / 40 suites plus 11 preparation/directed executions / 328
Python / 40 loop / nine native / nine EDA SP2** scopes pass. All four connected
variants pass **5,165 checks / four cuts / 136 words / 900 stalls**; the bound
host initializer retains **20 ASan/UBSan checks**. Source projection rejects
**28 mutations** and matches **641 sources / 685 inputs**. Twelve full debug
waves retain **2,704 frozen samples** per healthy variant and first compiled
corruption at **cut 81 / word 0 / byte 42**, before release. Its OOC component
uses **4,570 LUTs / 1,655 registers / three BUFGCEs / 671 raw-clock registers**;
**+0.326/−0.074 ns** setup/hold estimates retain unconstrained I/O and do not
establish image timing closure. Sixteen byte-identical artifacts include exact
Rocket FIRRTL/identity after per-call hierarchy reuse. Full Scala duration is
about 28 minutes versus the prior 38, retaining every test.

Sentinel identity and independent image guards remain active. Fresh exact
Rocket compilation still rejects the FASED CE owner/common cut, retaining
**1,947 uncovered functional entries / 298,428 words and one physical CE owner**.
Complete context/owners, full image/P&R/AFI, actual four-hart cuts and paired
CPU migration remain pending. No AFI or runtime launch occurred. Every
FPGA-origin acceptance column remains pending. See
[f2-widget-source-policy.md](f2-widget-source-policy.md) and
`runs/aws-f2/iteration251/accepted-receipts.json`.

Iteration 250 adds explicit typed enclosing-host storage annotation projection
at the existing widget graft. Original concrete executions determine register,
RAM, hierarchy and correlated XDC targets; shared primitive constraints exclude
the inserted mask gate. Other host metadata stays intact, and unknown targets
on unused original selected leaves reject. The complete final XDC is retained;
FPGATop OOC defers literal board-pad placement to final image implementation and
checks every hierarchy-bound constraint independently. Fresh **269 Scala plus
two preparation / 328 Python / 40 loop / eight native / eight EDA SP2** scopes
pass. All three connected variants pass **5,165 checks / four cuts / 136 words /
900 stalls**; the bound host initializer passes **20 ASan/UBSan checks**. The
projection rejects **22 mutations**, retains nine debug waves across variants,
and independently matches **641 sources / 684 projected inputs**. Its component
uses **4,517 LUTs / 1,646 registers / three BUFGCEs / 662 audited raw clocks**;
OOC setup/hold **+0.326/−0.074 ns** has unconstrained I/O and does not establish
timing closure. The initial invalid CE timing-startpoint constraint and all
superseded epochs remain preserved; the correction passed the complete fresh
scope. Sentinel identity and image guards remain active; source annotation
policy, complete enclosing identity/owners and physical CPU capture remain
unsupported. Exact Rocket compilation still rejects the FASED physical
CE-latch owner/common cut. Every FPGA-origin acceptance column remains pending.
See [f2-widget-annotations.md](f2-widget-annotations.md) and
`runs/aws-f2/iteration250/`.

Iteration 249 binds the selected widget's reconstructed manifest to its actual
transport parameter and registered host metadata/constructor. All **267 Scala
plus two preparation / 328 Python / 40 loop** checks and the full **seven-scope
EDA SP2** attempt pass. Sentinel and bound transports each pass **5,165 checks /
four cuts / 136 words / 900 stalls**; the bound initializer passes **20 ASan/UBSan
checks** against actual VCS streams. Twelve identity mutations reject. Matching
binds **639 sources / 678 or 708 inputs**, with **2,704 frozen waveform samples**
per healthy variant and a real compiled payload defect at **cut 81 / word 0 /
byte 42**, before release. Native synthesis reports **4,753 LUTs / 1,647 registers /
three BUFGCEs / 662 checked raw clocks** for the bound component. OOC estimates
remain **+0.437/−0.074 ns** with unconstrained external I/O; full-image timing is
pending. Original Scala failure and empty-compiler-log aggregate rejection remain
preserved; both source repairs have fresh complete verification. The host coverage
error and independent image guard remain active, including after annotation removal.
The manifest covers the supplied selected context; complete F1Shim identity and
ownership remain unsupported. Fresh exact Rocket compilation still rejects the
FASED physical CE owner/common cut, with **1,947 functional entries / 298,428 words
and one physical CE owner** outside the selected readout. No new FPGA capture,
image or CPU migration acceptance is established. All hardware-origin columns
remain pending. See [f2-widget-identity.md](f2-widget-identity.md) and
`runs/aws-f2/iteration249/accepted-receipts.json`.

Iteration 248 repairs controller reruns without changing hardware acceptance:
each regression invocation gets an exclusive attempt directory and an explicit,
fully pinned receipt index. Two complete EDA SP2 runs against the populated scope
pass **six components each**, including **5,165 connected MMIO/DMA checks / four
cuts / 136 words / 900 stalls**. Native synthesis, independent waveform and
source matching pass (**597 sources / 636 inputs**). All **328 Python / 40 loop**
tests and retained **ASan/UBSan host/FCFS** checks pass. The directed historical
audit verifies 113 receipts and retains four stale-log mismatches explicitly;
unchanged Scala evidence retains its original execution date. Fresh exact Rocket
compilation still rejects the FASED physical CE-latch owner/common-low-phase cut.
No checkpoint-enabled full image, physical capture or CPU migration is established;
all FPGA-origin acceptance columns remain pending. Commands and immutable
receipts: `runs/aws-f2/iteration248/verification-commands.json` and
`accepted-receipts.json`.

Iteration 247 connects the real registered checkpoint widget to its existing
selected execution through a checked post-lowering graft. All twenty routes,
original host metadata, MMIO and shared DMA are independently audited. The
bounded native fixture has **three BUFGCEs / 1,646 registers / 5,018 LUTs**;
**662 raw-clock registers** are checked. EDA SP2 passes **5,165 checks / four
cuts (81/184/324/36 after reset) / 136 words / 900 DMA stalls**, with complete
payload/CRC comparison, missing-owner/reset recovery and an actual compiled
readout defect at **cut 81, word 0, byte 42**. The independent final waveform
shows the bad payload before release and **2,704 stable frozen source-clock
samples**. Initial truncated failure-wave epochs remain preserved.

These are component results. The descriptors still use the standalone selected
namespace; global driver identity, production annotation projection and complete
owners remain unsupported. Sentinel identity/header and ordinary image-emission
guards remain active. Fresh exact-recipe compilation still rejects the missing
FASED physical CE owner/common low-phase cut. All **265 Scala tests**, two
preparation tests, **318 Python / 40 loop** tests and retained EDA
**ASan/UBSan/host/FCFS** checks pass. Five fresh EDA scopes replace four stale
historical aggregate-log references, which remain explicitly failed in the
historical audit. Final receipts belong under `runs/aws-f2/iteration247/`.
Every FPGA-origin acceptance column remains pending. See
[f2-native-widget-graft.md](f2-native-widget-graft.md).

Iteration 246 verifies permanently parked **physical register apply** with
positive/falling-edge load muxes and complete readback before acknowledgement.
Native synthesis maps **484 physical bits / 1,041 total registers / 601 LUTs**,
two falling-edge cells and the explicitly bound constant-zero supervisor bit;
a real added LDCE rejects. Native-bound EDA passes **2,092 restores / 136
rejections / 7,504,531 checks / zero target edges**, plus invalid specializations
and corruption at cut100/bit0 before acknowledgement, retaining seven full waves.
The fresh 27-scope native sweep, all retained EDA/ASan/UBSan/host/FCFS checks,
318 Python/40 loop tests and independent source/resource/waveform audits pass.
Production restore remains disabled. Common-cut release, complete stream/MMIO/
host continuation, capture image and every FPGA-origin acceptance column remain
pending. See [f2-transport-physical-restore.md](f2-transport-physical-restore.md)
and `runs/aws-f2/iteration246/`.

Iteration 245 adds transactional transport restore **staging**, with exact
identity/length/cycle binding, ordered complete words, padding/CRC checks and
one-shot backpressured apply. Native synthesis audits **655 registers / eight
fields** and rejects an injected hidden latch. EDA SP2 VCS passes **2,092 staged
restores / 139,884 checks / 159 protocol rejections**, plus three invalid
specializations, at gate counts 1/3/31/65. The compiled data defect stops at cut
**100**, word **0**, before any apply acknowledgement; all **eight waves** and
independent waveform labels are retained. **318 Python / 40 loop** and retained
EDA generated-bank/widget/**ASan/UBSan host/FCFS**/cut checks pass. The component
does not physically load transport registers or restore stream/MMIO/host state.
Full production integration, capture image and every FPGA-origin acceptance
column remain pending. Commands/receipts: `runs/aws-f2/iteration245/`.
See [f2-transport-restore-staging.md](f2-transport-restore-staging.md).

Iteration 244 verifies source preservation and complete native transport storage
census. FSM policy alone left eleven unrepresented replicas; both controller
state registers now require source-level preservation. Fresh native synthesis
maps **484 source bits / 484 registers**, with **552 shadow / 1,036 total**
registers and no extra encoding storage. **Five native negatives** reject.
All **262 Scala / 318 Python / 40 loop / 27 native / 46 EDA scopes**, retained
**ASan/UBSan/host/FCFS**, cross-backend audits and **29 debug waves** pass.
Readout checks **5,051 samples / 50,510 words**; shadow checks **1,614 captures /
80,952 words** plus eleven integration scenarios, including corruption at cut
100/observation 107. Original failures and repaired-source evidence remain
separate under `runs/aws-f2/iteration244/` and its `repair/` source epoch.
These are component results. Full source/owner binding, checkpoint image and
all FPGA-origin acceptance columns remain pending. See
[f2-transport-source-encoding.md](f2-transport-source-encoding.md).

Iteration 242 adds a synthesizable atomic shadow of the complete transport
source-register vector and target label. Native Vivado accounts for **552 shadow /
1,052 total register cells**. EDA VCS passes **1,614 standalone captures / 80,952
word checks** at gate counts 1, 3 and 65, plus **eleven integration scenarios**,
retaining **sixteen waves**. A separately compiled captured-bit defect fails at
snapshot cut **100**, observed at source cycle **107**, word **0**, capture **1**.
Cross-backend source/evidence matching,
**318 Python / 40 loop tests**, and retained generated-bank/widget/**ASan/UBSan
host/FCFS** checks pass. The initial source-change receipt rejection and successful
fixed-source synthesis are separate. This is a staging component; complete
transport restore, production cut ownership and image binding remain pending.
Every FPGA-origin acceptance column stays pending. See
[f2-transport-control-snapshot.md](f2-transport-control-snapshot.md).

Iteration 241 adds synthesizable live readout of all **24 transport/controller
registers**, including the falling-edge physical mask, with an exact source-pinned
layout and a combinational 64-bit bank. All **262 Scala / 318 Python / 40 loop
tests / 26 native synthesis / 45 EDA scopes**, retained **ASan/UBSan/host/FCFS**
and combined audits pass after recorded repairs. The readout checks **5,051 samples /
50,510 words / eleven scenarios**, retains **13 waves** and detects a field swap
at cycle **2**, sample **75**. Native synthesis accounts for **500 register cells**;
five additional FSM encoding registers retain unsupported capture/restore mapping.
Actual retained and fresh compiler epochs are separately bound. This readout
does not freeze the raw controllers or provide a restore adapter. The widget
leaves it unused, opaque inventory and image guards still reject, and every
FPGA-origin acceptance column remains pending. See
[f2-transport-control-state.md](f2-transport-control-state.md).

Iteration 240 reconstructs all twenty reserved widget routes after native
inlining, without guessing flattened names or consuming unbound image markers.
The three Scala tests pass fourteen rejection cases; independent manager/EDA
reconstruction passes **20 pins / 42 hops / 21 inputs / 23 sources**, rejecting
seven receipt mutations. The prior interrupted native sweep now passes all
**25 synthesis scopes** with a joined maximum-two-job scheduler, **44 EDA scopes**,
retained **256 Scala / 313 Python / 40 loop tests** and **ASan/UBSan/host/FCFS**.
The combined source/state/constraint/wave/resource audit passes. Original failures,
phase/provenance repairs and complete file-set matching are preserved under
`runs/aws-f2/iteration240/`. Complete transport-state ownership, immutable identity, production
graft attachment and every FPGA-origin acceptance column remain pending.
See [f2-widget-peer-routing.md](f2-widget-peer-routing.md).

Iteration 239 reserves the registered FPGATop widget/MMIO/CPU stream before
host inventory and retains twenty explicit lowered readout endpoints. Owner/cycle
inputs have no defaults. Unbound annotation/header/sentinel identity rejects
before ordinary image emission. The opaque transport state owner and final
ROM/driver binding remain pending; the existing strict inventory still rejects
that external state. The diagnostic passes **48 EDA SP2 checks**, a debug wave,
missing-owner rejection, baseline DMA and reset recovery; native synthesis proves
**810 raw control/stream register clocks**. Independent matching binds **25 inputs /
14 sources** and rejects eight rehashed mutations. The retained sweep is being recorded under
`runs/aws-f2/iteration239/`. This reserves resources and establishes no new
hardware capture or CPU migration acceptance. See
[f2-widget-reservation.md](f2-widget-reservation.md).

Iteration 238 adds a checked readout graft inside the existing lowered root,
retaining original execution paths, raw ancestor clocks, global descriptor
identity and original-path XDC. The bounded graft passes **7,101 EDA SP2 checks /
four cuts / 136 words / 522 stalls**, five waves and six rehashed adapter
rejections. Native synthesis proves **199 raw register clocks / three BUFGCEs**,
retaining **1,091 LUTs / 595 registers**. Independent matching binds **630 inputs /
59 sources**; settled waves show both ancestors advance across **872** frozen
raw-clock edges without selected target advancement. Production widget/owner
binding and every FPGA-origin acceptance column remain pending. All **253
Scala / 24 localhost synthesis / 43 EDA scopes**, **313 checkpoint Python /
40 loop tests** and retained **ASan/UBSan/host/FCFS** checks pass. Production
manager/EDA graft audits match **77 inputs / 59 sources**. Final receipts and
commands belong under `runs/aws-f2/iteration238/`.
See [f2-native-inplace-graft.md](f2-native-inplace-graft.md).

Iteration 237 attaches the validated in-place **component** host to the
registered FPGATop widget and its actual MMIO/CPU DMA path. The new component
passes **19,235 EDA SP2 checks / five cuts / 170 words / 1,110 DMA stalls**,
reset recovery and four execution negatives, with five debug waves. Native
synthesis retains **4,572 LUTs / 1,850 registers / three BUFGCEs**, proving **199
raw ancestor/router/endpoint + 1,024 raw control/stream register clocks**.
Independent native/EDA matching binds **156 inputs / 68 sources** and rejects
ten mutations. Settled waveform reconstruction proves two ancestor counters
advance across **3,034** frozen raw-clock edges without a selected target edge.
All **252 Scala / 23 localhost synthesis / 42 EDA scopes**, **313 checkpoint
Python / 40 loop tests** and retained **ASan/UBSan/host/FCFS** checks pass.
Complete production post-lowering attachment, freeze owners, physical CE restore/pre-FAME semantics, full localhost
image/timing/AFI and every FPGA-origin acceptance column remain pending.
Commands and receipts belong under `runs/aws-f2/iteration237/`. See
[f2-native-inplace-widget.md](f2-native-inplace-widget.md).

Iteration 236 connects functional and physical CE readout to a router around
the existing host, preserving global identities, raw control clocks and original
constraint placement. All **251 Scala / 22 localhost synthesis / 41 EDA scopes**,
**313 Python / 40 loop tests** and retained **ASan/UBSan/host/FCFS** checks pass.
The new bounded execution passes **7,101 SP2 checks / four cuts / 136 words / 522
stalls** through cycle **419**, with **five debug waves**, **817 inputs / 54
sources** matched and ten rehashed mutations rejected. Native synthesis retains
**1,091 LUTs / 595 registers / 199 audited raw-clock registers**; full-image timing
remains pending. The compiled CE connection fault fails on its first physical
read at cycle **25**, check **55**. Independent exact-Rocket auditing covers all
**2,431 source / 2,379 projected storage annotations**, native synthesis constants,
retired caches, history and **14 XDC commands in seven annotation blocks**.
Complete widget/MMIO/DMA attachment, all freeze owners, physical CE restore,
pre-FAME mapping, full localhost image/AFI and every FPGA-origin acceptance
column remain pending. Final commands and receipts belong under
`runs/aws-f2/iteration236/`. See [f2-native-inplace-access.md](f2-native-inplace-access.md).

Iteration 235 adds actual in-place compiler-context projection. All **250 Scala /
21 localhost synthesis / 40 EDA scopes**, **309 Python / 40 loop tests** and
retained **ASan/UBSan/host/FCFS** checks pass. The exact Rocket test projects
**2,456 source annotations**, preserves **25 context annotations / 20 kinds** and
**2,379 storage annotations**, and emits **14 XDC commands** in the original
compiler constraint order. Independent context auditing matches **15 fixture /
17 production files / 44 sources** across both backends and rejects **eight /
nine** coherently rehashed mutations. Retained in-place SP2 execution passes
**6,541 checks / four cuts / 128 words / 468 stalls** through cycle **409**, with
six debug waves and **1,822 inputs / 42 sources** matched. Receipt and command
files are under `runs/aws-f2/iteration235/`. Full-image timing, endpoint/widget
attachment, complete freeze owners/physical CE restore/pre-FAME mapping, the
localhost capture image/AFI and every FPGA-origin capture/migration/recovery
column remain pending. See [f2-native-inplace-context.md](f2-native-inplace-context.md).

Iteration 234 projects primitive-local XDC to original physical executions,
including renamed selected ancestors and unchanged siblings. Added mask gates
receive no inherited original constraint. Both selected-reference and host input
constraints use version-2 translation and its required descriptor validator.
All **248 Scala / 21 localhost synthesis / 40 EDA scopes**, **309 checkpoint
Python / 40 loop tests** and retained **ASan/UBSan/host/FCFS** checks pass. Fresh
in-place EDA SP2 execution passes **6,541 checks / four cuts / 128 words / 468
stalls** through cycle **409**, with six debug waves. Native synthesis retains
**884 LUTs / 590 registers / 194 raw-clock registers**; full-image timing remains
pending. Independent matching covers **1,710 inputs / 41 sources**, including
six structural/sixteen identity/fourteen annotation negatives and six emitted XDC
lines. Fresh exact Rocket/global coverage matches on both hosts; the ordinary
compiler still rejects the missing FASED physical CE owner/common cut. Receipts,
source/recipe provenance and commands belong under `runs/aws-f2/iteration234/`.
Complete production context/physical endpoint attachment, all owners/physical CE
restore, localhost image/AFI and every FPGA-origin migration column remain pending.
See [f2-native-primitive-xdc.md](f2-native-primitive-xdc.md).

Iteration 233 adds checked in-place host annotation/XDC projection. Concrete
parent paths and repeated/shared executions retain correlation; full annotation
sets, mappings and invalidated caches bind version-3 provenance. Unknown/stale
owners and primitive-local constraints that would expand onto the added root
gate reject. An independent bounded auditor checks actual emitted XDC and adds
ten coherently rehashed annotation negatives. All **247 Scala / 21 native synthesis / 40 EDA scopes**, **309 Python / 40 loop
tests** and retained **ASan/UBSan/host/FCFS** checks pass. Fresh in-place EDA SP2
execution passes **6,541 checks / four cuts / 128 words / 468 stalls** through
cycle **409**, retaining six debug waveforms. Independent matching covers
**1,530 inputs / 41 sources**. The native fixture retains **884 LUTs / 590
registers / 194 raw-clock registers**; full-image timing closure remains pending.
Receipts and commands belong under `runs/aws-f2/iteration233/`. Full production annotation
context/primitive-local projection, physical endpoint/widget attachment and every
hardware migration column remain pending. See
[f2-native-inplace-annotations.md](f2-native-inplace-annotations.md).

Iteration 232 reconciles in-place selected banks with original global StateIDs
without changing endpoint selectors, word order or physical CE bit order.
All **244 Scala tests** pass. Exact-Rocket original-source auditing maps
**10,149 functional + two CE** entries (**320,587 words**) and explicitly leaves
**1,947 functional owners / 298,428 words** and **one FASED CE owner** uncovered.
Local CE slots **0/1** correspond to global physical indices **1/2**. The bounded
fixture synthesizes locally and rejects six structural and sixteen coherently
rehashed metadata corruptions, including omitted global owners and nonfunctional
parent clocks. All **21 localhost synthesis / 40 EDA scopes**, **309 checkpoint
Python / 40 loop tests** and retained ASan/UBSan/host/FCFS checks pass. The native
fixture uses **884 LUTs / 590 registers**, retaining **194** raw parent/readout
clocks; OOC 140 MHz setup/hold estimates are **+2.672/−0.074 ns** and full-image
closure is pending. Fresh EDA SP2 passes **6,541 checks / four cuts / 128 words /
468 stalls** through cycle **409**, with six debug waves and independent matching
of **934 inputs / 33 sources**. Final results and commands belong under
`runs/aws-f2/iteration232/`. This remains **in_progress identity integration**. Production annotation/XDC and CE endpoint/router/widget
attachment, complete owner binding/physical restore/pre-FAME mapping, full
localhost image/AFI and every FPGA-origin migration/recovery column remain
pending. See [f2-native-inplace-identity.md](f2-native-inplace-identity.md).

Iteration 231 adds in-place banking of an existing concrete execution with raw
parent/control clocks and a separately proven raw bank endpoint. All **242 Scala
tests** pass. Independent exact-Rocket structural auditing covers the existing
`F1Shim.top.sim` execution: **10,149 functional descriptors and two separately
composed CE descriptors / 1,994
generated module definitions / 11,590 sequential/effect definitions**. The
sibling FASED model remains outside that selected scope. The bounded fixture
synthesizes locally with **884 LUTs / 590 registers**; all **194** parent/readout
registers keep the raw source and six rehashed structural corruptions reject.
OOC 140 MHz setup/hold estimates are **+2.672/−0.074 ns**; full-image closure is
pending. Fresh EDA SP2 passes **6,541 checks / four cuts / 128 words / 468
response stalls**, continuing through cycle **409**, with six hierarchical
VCDs. Semantic and compiled parent-control faults stop at cut **15**, checks
**30/18**; the parent fault accepts no bank word. All **21 localhost synthesis /
40 EDA scopes**, **309 checkpoint Python / 40 loop tests** and retained
ASan/UBSan/host/FCFS checks pass. Evidence belongs under
`runs/aws-f2/iteration231/`; consult its summary and command manifest.
This remains **in_progress structural integration**. Complete production
annotation/XDC projection and in-place CE endpoint/router/widget/stream attachment, full reset/
CE/memory/FASED/bridge/software/pre-FAME ownership, physical CE restore,
localhost image/AFI, active four-hart FPGA cuts and every FPGA-origin migration/
recovery column remain pending. See [f2-native-inplace.md](f2-native-inplace.md).

Iteration 230 adds a reconstructed bounded native network attachment through
actual FPGATop AXI control and CPU-managed DMA. The registered widget and network
share the raw source and controller reset; all original functional inputs, cycle
authority and owners remain explicit. Missing reset/owner connections reject,
and an enclosing F1Shim simulator cannot be embedded as a second execution.
All **238 Scala tests** pass. Fresh EDA SP2 passes **15,655 checks / five cuts /
170 words / 1,110 DMA stalls**, including reset recovery and continuation through
cycle **200**, with five debug VCDs and first-payload semantic/compiled CE fault
rejection. Local native synthesis uses **4,582 LUTs / 1,726 registers**; **1,028**
control/transport/DMA registers retain the raw source, six native constraints apply
and five changed top connections reject. OOC 140 MHz setup/hold estimates are
**+0.591/−0.095 ns**; full-image closure is pending. Detailed current-source and
retained results, including all **20 native synthesis / 39 EDA scopes**, **309
checkpoint Python / 40 loop tests** and retained ASan/UBSan/host/FCFS checks, are
recorded in `runs/aws-f2/iteration230/summary.json` and its command manifest.
This is **in_progress bounded attachment integration**. Whole-Rocket in-place
instrumentation and ownership, physical CE restore, full image/timing/AFI/driver
binding, actual active all-hart FPGA cuts and every FPGA-origin migration/recovery
column above remain pending. See
[f2-native-fpgatop-attachment.md](f2-native-fpgatop-attachment.md).

Iteration 229 adds validated native state-access wrapper XDC placement at its
actual `network` instance, with separately bound pre/post-link paths and an
independent concrete-target reconstruction. All **237 Scala tests** pass. Native
connected-widget synthesis passes at **2,637 LUTs / 1,157 registers**; six
cell/pin queries and their gate/generated-clock effects are checked, and two
empty queries fail explicitly. Fifteen coherently rehashed RTL/XDC corruptions
reject. OOC 140 MHz setup/hold estimates are **+0.598/−0.104 ns**; full-image
closure remains pending. Fresh EDA SP2 passes **6,482 checks / five cuts /
170 words / 210 DMA stalls** with six debug VCDs. Independent matching covers
**94 inputs / 34 sources** and rejects nine evidence corruptions. All **19 native
synthesis / 38 EDA scopes**, **309 checkpoint Python / 40 loop tests** and retained
ASan/UBSan/host/FCFS checks pass. Both hosts independently reconstruct complete
exact-Rocket state/clock/XDC composition: **12,096 functional + three CE
descriptors / 619,016 words**, seven XDC specifications / six circuit arguments.
This remains **in_progress companion constraint integration**.
Production attachment, reset/external writers and complete memory/bridge/host/
pre-FAME ownership, localhost full image/AFI, actual active all-hart FPGA cuts,
and every FPGA-origin migration/recovery column above remain pending. See
[f2-native-state-access-constraints.md](f2-native-state-access-constraints.md) and
`runs/aws-f2/iteration229/verification-commands.json`.

Iteration 228 adds a generated same-reference native state-access wrapper:
the native bank network, physical CE endpoint and read/response router connect
through one raw source/reset contract. The connected component uses the actual
FireSim MMIO/stream widget and manifest-bound descriptor ROM. All **236 Scala
tests** pass; native synthesis passes with **2,577 LUTs / 1,155 registers**, three
native/root gates and one falling-edge mask. OOC 140 MHz setup/hold estimates are
**+0.597/−0.074 ns**; hold closure remains pending. Fresh EDA SP2 passes
**6,482 checks / five cuts / 170 words / 210 stalls**,
with independent native/EDA matching over **89 inputs / 32 sources** and all six
execution waveforms. Eight structural and nine evidence corruptions reject;
semantic/compiled CE payload faults stop at cut 63/checks 273/1,036. All **19 native
synthesis / 38 EDA scopes**, **309 checkpoint Python / 40 loop tests** and retained ASan/UBSan/host/FCFS regressions pass. Independent complete
exact-Rocket structural auditing agrees on both hosts over **2,290 modules /
14,313 sequential/effect definitions**, retaining **12,096 functional + three CE
descriptors / 619,016 words**. Final inventories/audits pass. Production reset,
external memory/CE writers, FASED/bridge/host/pre-FAME owners, production
FPGATop integration, full image/P&R/AFI and every FPGA-origin migration column
above remain pending. See [f2-native-state-access.md](f2-native-state-access.md)
and `runs/aws-f2/iteration228/verification-commands.json`.

Iteration 227 connects independently reconstructed native functional banks to
the generated physical clock-mask hierarchy from the same original Rocket circuit.
The separate clock/bank companion retains every original native gate and both
translated XDC files; the endpoint stays ungated. Independent auditing checks
**2,290 modules / 14,313 sequential/effect definitions**. The descriptor counts
remain **12,096 functional + three CE / 619,016 words**. All **234 Scala tests**
pass; eight coherently rehashed structural/admission corruptions reject. The
connected counter/wide-RAM component synthesizes with **882 LUTs / 462 registers**;
OOC 140 MHz setup/hold estimates are **+2.672/−0.074 ns**. Hold timing closure is
pending. Fresh EDA SP2 passes **5,343 checks / four component cuts / 128 words /
468 stalls**, continuing through cycle 409. Semantic/root-mask faults stop at
cycle 15/checks 24/14; missing-owner/CE-drift rejection and all five debug VCDs
remain. Independent native/EDA matching covers **244 inputs / 24 sources**; all
18 native synthesis and 37 EDA scopes pass. This is **in_progress clock/bank
integration**; production reset and
external-owner contracts, complete widget/network connection, full image/P&R/AFI
and all FPGA-origin migration columns above remain pending. See
[f2-native-clock-cut-banks.md](f2-native-clock-cut-banks.md) and
`runs/aws-f2/iteration227/verification-commands.json` for final execution receipts.

Iteration 226 composes native functional and physical CE descriptors from the
same original Rocket circuit: **12,099 descriptors / 619,016 transfer words**.
The factory independently reconstructs the native banks; different-circuit or
coherently rehashed caller results reject. A separate emitted binding retains
the common reference, every selector and both complete domain documents, with
all capture/production/restore admission flags false. The fixture's actual
MMIO/stream widget retains its immutable ROM and matching host header; native
localhost synthesis uses **1,591 LUTs / 764 registers**, OOC 140 MHz setup/hold
estimates **+0.611/+0.071 ns**. All **233 Scala tests** pass. Fresh EDA SP2
passes **81 ROM checks**; an independently compiled physical-slot fault stops
at descriptor 5/check 11, with both execution waveforms retained. This remains
**in_progress descriptor integration**: connected production cut/transport and
complete owners, full image/P&R/AFI and every FPGA-origin migration column
above remain pending. See [f2-native-descriptors.md](f2-native-descriptors.md)
and `runs/aws-f2/iteration226/verification-commands.json`.

Iteration 225 adds a separate native functional-bank companion for the exact
Rocket recipe: 12,096 concrete storage descriptors, 619,013 transfer words and
all three original BUFGCEs, with independent complete emitted-storage/shape,
clock/CE-dependency and XDC auditing. The ordinary production admission guard
remains. Native companion fixtures pass 230 Scala tests, synthesize with two
native gates (848 LUTs / 390 registers), and pass 4,539 EDA SP2 checks over four
complete 32-word cuts, 468 response stalls and execution through cycle 405.
Semantic and independently compiled native-wiring faults stop immediately;
three execution waveforms remain. This is **in_progress readout integration**;
connected production cut/transport/owners, full image/AFI and every FPGA-origin
migration column remain pending. See
[f2-native-functional-banks.md](f2-native-functional-banks.md) and
`runs/aws-f2/iteration225/verification-commands.json`.

Iteration 224 adds immutable functional/physical CE descriptor composition to
the real widget. Generated endpoint identities and selectors, both complete
component documents and distinct circuit references bind the synthesized ROM
and host constructor. Physical table/transport count mismatches reject in both
modes. The new fixture uses nine functional and three physical descriptors;
it does not establish common-cut Rocket ownership. All 226 Scala tests pass.
Native localhost synthesis uses 1,806 LUTs / 767 registers, one immutable ROM
and no duplicate BUFGCEs; 140 MHz OOC setup/hold estimates are +0.553/+0.071 ns.
Fresh EDA SP2 passes 126 ROM checks and stops an independently compiled physical
slot fault at descriptor 9; both debug waves are retained. Native/EDA auditing
matches 34 inputs / 13 sources and rejects six coherent manifest corruptions.
This remains **in_progress component integration**. Production ownership,
image/P&R/AFI and every hardware-origin migration column above remain pending.
See [f2-physical-descriptors.md](f2-physical-descriptors.md) and
`runs/aws-f2/iteration224/verification-commands.json`.

Iteration 223 adds physical-cut support to the actual FireSim NASTI/MMIO and
512-bit stream widget. Its external-network sideband exposes original CE,
mask, sampled CE/cycle and read/fault status; its header binds physical RTL
hashes. An immutable functional-only descriptor ROM rejects physical mode;
complete bank-255 physical descriptor composition is still required. Native
localhost component synthesis uses 1,967 LUTs / 830 registers and one falling-
edge mask, with no duplicate native gates; 140 MHz OOC setup/hold estimates
are +0.550/+0.071 ns. Full image implementation timing remains pending.
Fresh EDA SP2 passes 6,810 widget checks, six complete component cuts, abort/
drain, backpressure and reset recovery. All six debug waves contain execution;
52-input/29-source independent auditing rejects eight evidence substitutions,
including corrected-CRC semantic corruption and physical-owner removal.
This is **in_progress component integration**. Production ownership, image/AFI
and every hardware-origin migration column above remain pending. See
[f2-physical-widget.md](f2-physical-widget.md) and
`runs/aws-f2/iteration223/verification-commands.json` for execution evidence.

Iteration 222 composes the exact compiler CE endpoint with functional-bank
and MMIO/DMA transport using a synthesizable descriptor/response router. Bank
255 is reserved and malformed/aliased descriptors reject. Accepted reads retain
their endpoint through stalls and abort/drain. Native localhost synthesis uses
1,867 LUTs / 669 registers, four SYNC BUFGCEs and one falling-edge mask;
140 MHz OOC setup/hold estimates are +0.593/-0.062 ns. Fresh EDA SP2 passes
4,912 integrated checks, five complete cuts, seven independently checked state
words per cut, 36 requests and execution through cycle 320. Standalone routing
passes 311 checks; runtime, reset, CRC/semantic corruption and independently
compiled routing faults retain fifteen debug VCDs. This remains **in_progress
component integration**: production bank/bridge and complete same-cut owners,
physical CE restore, full image/P&R/AFI and every actual hardware migration
column remain pending. See [f2-physical-state-router.md](f2-physical-state-router.md)
and `runs/aws-f2/iteration222/verification-commands.json`.

Iteration 221 adds exact Rocket physical CE StateIDs and a generated bank-255
readout endpoint, with one bit and one slot per original native gate. It binds
the source/inventory/topology/CE dependencies and generated endpoint bytes;
complete capture, production freeze ownership and metasim restore support remain
explicitly false. The exact endpoint with the generated active three-gate
fixture synthesizes on localhost: 202 LUTs / 235 registers, four SYNC BUFGCEs,
one falling-edge mask, OOC setup/hold estimates +2.063/-0.072 ns at 140 MHz.
All 220 Scala tests and 14 independent layout corruption cases pass. Fresh EDA SP2 passes **2,722 checks / five cuts / 52 reads / 140 stalls**,
reset cancellation/recovery and resumed execution through cycle 320. Every bit
is read as both zero and one. Corrupt-oracle and independently compiled
inverted-bit endpoints stop at their first bad frozen readout; three full debug
VCDs remain. The production BUFGCE guard remains; complete bank arbitration,
owner/restore binding, full image/P&R/AFI and every physical capture/migration
column above remain pending. See [f2-physical-ce-bank.md](f2-physical-ce-bank.md)
and `runs/aws-f2/iteration221/verification-commands.json`.

Iteration 220 connects the compiler-generated native clock mask/CE network to
physical bank/MMIO/DMA transport without duplicate gates. Reset directly
invalidates unpublished DMA streams. Fresh native generated-network synthesis
uses 1,779 LUTs / 660 registers; OOC setup/hold estimates are +0.545/-0.062 ns
at 140 MHz. Both network modes pass 4,739 EDA checks, five complete cuts, the
retained fault/CRC/backpressure scope and five reset interruptions with fresh
capture recovery. Removing only reset invalidation reproduces the expected
publication failure. Twelve debug VCDs remain per mode. This is **in_progress**
component integration: the fixture's common reset does not bind production
`F1Shim.reset` or complete external writers. The physical bank guard, complete
owner/bank/restore binding, full image/P&R/AFI and every actual FPGA capture and
migration column remain pending. See
[f2-generated-clock-transport.md](f2-generated-clock-transport.md) and
`runs/aws-f2/iteration220/verification-commands.json`.

Iteration 219 adds complete original-CE dependency prerequisites to that probe.
The three actual Rocket gates have 27/179/179 clocked-state terminals (207
distinct owners), all bound to inventory StateIDs and clock consumers. The
two target gates also depend on external `F1Shim.reset`, whose same-cut owner
remains unbound. An independent concrete-instance oracle rejects omitted
dependencies and invented closure/ownership claims. This is **in_progress**
compiler/component work; the physical bank guard remains, and full localhost
image implementation/AFI, actual FPGA checkpoint cuts and every migration
column above remain pending. See
[f2-physical-clock-dependencies.md](f2-physical-clock-dependencies.md) and
`runs/aws-f2/iteration219/verification-commands.json` for current commands.

Iteration 218 emits a separate physical clock-mask wiring probe for the exact
Rocket compiler: one added root BUFGCE, the three original native gates,
dedicated ungated source routing and ordered unmasked CE output. Independent
reconstruction checks every original driver, storage/reset declaration and
clocked effect across 488 reachable module definitions and rejects eight
coherently rehashed corruptions. The existing physical sampler can drive this
generated network without duplicate gates. This remains **in_progress**:
production annotation/XDC, complete external-writer/common-cut ownership,
physical CE bank/restore mappings, MMIO/DMA binding and image/P&R/AFI are still
pending. Every hardware capture/migration column above remains pending.
See [f2-physical-clock-wiring.md](f2-physical-clock-wiring.md) and
`runs/aws-f2/iteration218/verification-commands.json` for current commands.

Iteration 217 adds a topology prerequisite for the generated physical cut:
the exact Rocket final-emission plan resolves all three native SYNC gates,
2,107 clock pins and 13,234 sequential consumers to root `clock`, with complete
clock coverage of 11,459 simulator inventory entries. Independent FIRRTL
reconstruction rejects 15 coherently rehashed plan corruptions. This is
**in_progress** compiler integration only: no clock rewrite or physical capture
owner is admitted, and the FASED BUFGCE bank guard remains. CE dependency
closure, full image/P&R/AFI, all four active-workload hardware cuts, Level-1
migration, Level-2 finite/live RTL and rolling hardware recovery stay pending.
See [f2-physical-clock-plan.md](f2-physical-clock-plan.md) and
`runs/aws-f2/iteration217/verification-commands.json` for current commands.

Iteration 216 connects the physical cut to the descriptor/bank/MMIO/DMA
transport through a deferred post-stop acknowledgement and holds external
owners until physical release completes. Fresh EDA SP2 passes 4,739 checks,
five complete component cuts 2/19/130/258/302, 88 DMA stalls, 128 delayed-bank
cycles and accepted-read abort/drain recovery through 320 functional cycles.
Independent host arithmetic/CRC checks cover every state word; six runtime
negatives, four host integrity mutations and ten evidence substitutions reject.
Seven full debug VCDs are
retained. Native localhost OOC synthesis retains four SYNC gates and one
falling-edge mask, using 1,810 LUTs / 660 registers; setup slack is +0.545 ns
at 140 MHz, while unplaced hold slack remains -0.062 ns. Implementation timing
and the actual image are pending. The exact Rocket compiler still rejects
`F1Shim.top.FASEDMemoryTimingModel_0.gate`; the new component has not removed
that guard or generated a complete clock/owner binding. All FPGA-origin CPU
restore, finite/live and rolling entries above remain pending.
See [f2-physical-capture-transport.md](f2-physical-capture-transport.md) and
`runs/aws-f2/iteration216/verification-commands.json`.

Iteration 215 adds a synthesized common-clock physical-cut component,
retaining native SYNC BUFGCEs and a falling-edge common mask. It samples the
unmasked logical CE vector after stopping, rejects missing-owner/CE/cycle drift
and validates release on a full control edge before unmasking. It is **not yet
connected to the Rocket compiler, bank network or bridge**. Exact Rocket
compilation still explicitly rejects the FASED physical owner; the three-clock
ownership mapping and complete global integration remain pending.

Native OOC fixture synthesis retains four gates and one falling-edge register,
using 216 LUTs / 232 registers. Registered release improves estimated 140 MHz
setup slack from -0.523 ns to +2.657 ns. Unplaced hold slack remains -0.072 ns;
full implementation timing is pending. Fresh EDA SP2 VCS passes 1,968 checks,
logical cuts 0/17/128/256, 64 stopped transport cycles and resumed functional
comparison through cycle 320. All logical CE words match independent original
vendor latch observations. Three fail-stop cases and a corrupt readback oracle
reject at cut 17, and eight evidence corruption cases reject. Full debug waves
and exact native/EDA inputs are retained. All 207 Scala / 309 checkpoint Python /
40 loop tests and retained sanitizers/FCFS/components pass. These are component
results; all hardware-origin CPU migration, finite/live and rolling entries
remain pending. See [f2-physical-clock-cut.md](f2-physical-clock-cut.md) and
`runs/aws-f2/iteration215/verification-commands.json` for exact commands.

Iteration 214 fixes the actual native TargetBox-to-FAMETop link producer.
Exactly one absolute concrete boundary, one external placeholder instance,
disjoint pre-link namespaces and matching lowered interfaces are required;
stale/foreign/relative/ambiguous paths and incompatible interfaces reject.
The placeholder definition retires and native FIRRTL circuit/module renames
update the boundary and all local/nonlocal annotations before strict banking.
All 207 Scala tests pass, including nine new link/negative tests. A separately
exported one-register fixture exercises native synthesis and fresh EDA VCS
bank readback with independent original-RTL/arithmetic comparisons, four cuts,
backpressure, frozen functional-clock pulses and corruption rejection.
Native synthesis uses 44 LUTs / 18 registers. Fresh SP2 VCS passes 595 checks
over 256 fixture cycles with complete cuts 0/17/128/256 and sixteen stalls;
healthy/failed VCDs are retained. Native/EDA matching covers 11 generated files /
eight current sources, and nine independent evidence corruptions reject.
All 207 Scala / 309 checkpoint Python / 40 loop tests and the full retained EDA
ASan/UBSan/FCFS/host/memory/bridge/bank scope pass. Retained production-bank/top
checks match 28 files / 41 sources with 4,669 / 7,858 comparisons, plus 21,970
synchronous-policy checks. These remain component results.
See [f2-simulation-mapping.md](f2-simulation-mapping.md).

The exact Rocket compiler passes the stale boundary and explicitly rejects
physical CE state at `F1Shim.top.FASEDMemoryTimingModel_0.gate`. The actual
compiler log, source hashes and exact command are under
`runs/aws-f2/iteration214/remaining-blockers.json`. Complete physical/common-cut,
memory/timing/bridge/host/pre-FAME ownership, localhost full image/P&R/AFI,
all-hart active hardware cuts, paired CPU zero-edge/finite/live continuation
beyond trace and rolling hardware recovery remain pending. Component fixtures
cannot establish those entries. No new AFI, runtime or FPGA capture is claimed.
Exact verification commands and final audits are under the same invocation.

Iteration 213 implements the exact RAMStyleHint logical-memory contract and
fixes real final emission of late public host-widget XDC. Internal/external
identity and correlated hierarchy remain bound through specialization; the native
consumer emits and retires both classes. Only the five native synthesis
RAM-style templates on one retained logical memory are admitted. Malformed,
foreign/dead, nonmemory, indexed/port and regexp-active explicit targets reject.

Actual Rocket compilation advances past the FIFO RAM constraint to a stale
`TargetBoxAnnotation`: the annotation names `target:TargetBox`, while retained
post-SimulationMapping FIRRTL has `SimWrapper.target of FAMETop`. Correct that
native hierarchy transition before banking, preserving the exact target boundary.
Physical CE-latch/common-cut and complete ownership/image requirements remain
unsupported. All FPGA-produced CPU image, zero-edge, finite/live and rolling
acceptance entries remain pending.

All 198 Scala / 309 checkpoint Python / 40 loop tests and the full retained EDA
sanitizer/FCFS/component scope pass. The initialized RAM fixture's actual emitted
XDC produces native distributed RAM (54 constrained cells, 18 initialized bit
planes, 36 read-port copies), 77 LUTs / 11 registers. Fresh EDA SP2 VCS passes
1,870 checks / 69 reads / 276 stalls / four complete cuts / 166 functional edges /
587 observations with original-RTL comparison and full debug waveform. Twelve
independent RAM-style corruption cases reject. Final native/EDA input matching
and retained production-bank/top checks are in the iteration receipt. This is
compiler/component evidence; no new AFI/runtime or physical capture is claimed.
Commands and individual files: `runs/aws-f2/iteration213/summary.json`,
`verification-commands.json`, `final-audit.json`, `remaining-blockers.json` and
`target-box-path-audit.json`. See [f2-ram-style-constraints.md](f2-ram-style-constraints.md).

Iteration 212 consumes NoDedup protection at the actual native inline pass:
only removed definitions retire, surviving protection remains, and stale/foreign/
duplicate input targets reject. Version-2 history binds exact original definition
hashes and retirement actions alongside complete storage/native-rename evidence.
The independent audit reconstructs definition hashes and rejects dropped surviving
or revived removed protection even with coherent annotation hashes.

The exact Rocket build passes its unreachable NoDedup barrier, then rejects an
external `midas.targetutils.xdc.XDCAnnotation` RAM target in the stream engine's
`TRACERVBRIDGEMODULE_0_to_cpu_stream_outgoingQueueIO_q:Queue_56>ram`. Next: exact
RAM-style XDC memory/cell selection through banking and downstream emission;
physical CE-latch/common-cut and complete memory/timing/bridge/host/pre-FAME
ownership also remain pending. Full image/AFI, hardware cuts and every FPGA-to-CPU
zero-edge/finite/live/rolling acceptance entry remain pending.

All 195 Scala / 309 checkpoint Python / 40 loop tests, full retained EDA
ASan/UBSan/FCFS scope and native OOC checks pass. Inline native/EDA receipts
match 7 files / 9 sources; 2,016 VCS comparisons / 512 fixture cycles and 20
corruption rejections pass, with debug VCD. Native inline synthesis retains
63 LUTs / 16 registers plus distributed RAM. Stateful partial inlining retains
an explicit rejection of FIRRTL 1.6's surviving-instance rename alias; stateless
partial and circuit/module selections pass. Retained physical/bank/top checks
and provenance audits pass. This is compiler/component evidence only.
Commands/receipts: `runs/aws-f2/iteration212/summary.json`; actual compiler
failure: `runs/aws-f2/iteration212/remaining-blockers.json`.
See [f2-inline-constraints.md](f2-inline-constraints.md).

Iteration 211 adds a source-free default-SYNC BUFGCE public-pin/cell contract,
with correlated specialization through shared physical leaves and real downstream
XDC emission. Unsupported latch state remains fail-closed, with exact definition,
missing owner and common-low-phase-cut requirements in external-owner reports.
Independent audits reject source overrides, altered parameters/ports, missing or
mistyped contracts, cross-instance constraints and false capture claims.

The actual Rocket compile passes its previous opaque-BUFGCE XDC failure, then
rejects an unreachable `firrtl.transforms.NoDedupAnnotation` on
`~F1Shim|Nasti2AXI4IdentityModule`; stack and fresh compiler bytes are retained.
Next: phase-correct native-inline constraint retirement and physical CE-latch/
common-cut implementation. All custom-image, FPGA checkpoint, CPU zero-edge,
finite replay, sustained live RTL and rolling hardware acceptance remain pending.
Commands/receipts: `runs/aws-f2/iteration211/summary.json`; concrete compiler
failure: `runs/aws-f2/iteration211/remaining-blockers.json`. This is compiler and
component work. All 193 Scala / 309 checkpoint Python / 40 loop tests, full
retained EDA sanitizer/FCFS scope and native OOC checks pass. Physical fixture:
two BUFGCEs / sixteen registers / six constraints, 4,064 VCS comparisons / 512
cycles, 14 corruptions and debug VCDs; native/VCS match 10 files / 10 sources.
Retained bank/top audit matches 28 files / 41 sources, with VCS counts
4,669 / 7,858 / 21,970. No physical capture or CPU acceptance is established.

Iteration 210 adds the exact Chisel group annotation missing from pinned FIRRTL
1.6, suppresses unaware generic dedup before any optimization, and executes
native dedup with group-aware bottom-up structural cliques. Native rename maps,
NoDedup and prior DupedResult behavior are retained. Immutable input, actual
pass and consumed-constraint history bind final emission; generic suppression
and all history receipts are required. Constraints retire at the forced pass
before FAME/inline removes definitions. A second forced pass rejects.

The exact Rocket compiler passes the unsupported annotation-class barrier, then
fails explicitly on `XDC target requires a reachable concrete module: BUFGCE`.
No whole-Rocket bank RTL/image is accepted. Physical constraint/enable-latch
ownership and complete common-cut/memory/timing/bridge/host/pre-FAME binding are
next; full localhost image/P&R/AFI, hardware active cuts and all paired CPU
restore/replay/live/rolling acceptance remain pending.

188 Scala / 306 checkpoint Python / 40 loop tests and full retained EDA sanitizer/
FCFS/component scope pass. Fresh group VCS: 7,112 comparisons / 512 fixture cycles
with debug VCD; 19 independent corruptions reject. Native group OOC retains all
seven owners (63 LUTs / 56 registers). Inline/native bank/MMIO-DMA OOC and retained
VCS pass; final audit matches 28 generated files / 39 sources, with bank/top/
synchronous-policy VCS counts 4,669 / 7,858 / 21,970. Commands and individual receipts: `runs/aws-f2/iteration210/summary.json`;
exact compiler failure: `runs/aws-f2/iteration210/remaining-blockers.json`.
These are compiler/component results, not hardware capture or CPU acceptance.

Iteration 209 executes the generated wrapper InlineInstances request using the
native pass on the final lowered simulator, before inventory/banking. Every
concrete register and memory instance is tracked across actual FIRRTL renames;
lost, duplicated, aliased or reshaped storage rejects. Immutable consumed
request/targets, input/output circuit and annotation hashes, complete native
rename history and storage mappings survive in final-emission-bound context.
Physical opaque owners remain separate and unsupported.

Exact Rocket preflight now rejects **one annotation class**, the 2,120 raw
dedup-group restrictions. InlineInstances is actually consumed; no whole-Rocket
bank or checkpoint image is emitted. Next: enforce group restrictions before
the mandatory dedup pass, which temporarily removes --no-dedup. The complete
common-cut/memory/timing/bridge/host/pre-FAME ownership, physical BUFGCE owners,
localhost full image/P&R/AFI, active FPGA cuts, fresh CPU zero-edge readbacks,
finite replay, sustained live RTL and rolling hardware recovery remain pending.
Reuse iteration194's localhost invocation; initialized manager configs survive.

180 Scala / 306 checkpoint Python / 40 loop tests and retained EDA ASan/UBSan/
FCFS/component regressions pass. The independent inline audit rejects 13
corruptions; fresh SP2 VCS compares 2,016 outputs over 512 fixture cycles and
retains a debug waveform. Native inline OOC synthesis: 63 LUTs / 16 registers.
Bank/top fixture OOC synthesis also passes. Final independent EDA audit matches
28 generated files / 35 current sources; SP2 VCS passes 4,669 bank / 7,858
exact-native-top / 21,970 synchronous-policy checks, with waveforms. Final-source
inline native/VCS inputs and six sources match; all retained negatives pass.
This is compiler/component evidence only. Commands and individual receipts:
`runs/aws-f2/iteration209/summary.json`; actual production failure and remaining work:
`runs/aws-f2/iteration209/remaining-blockers.json`.

Iteration 208 consumes the exact default FIRRTL emitter request at stage entry,
with immutable request/policy context and final selected-emitter/SystemVerilog
binding. It retires only exact AbstractClockGate source/definitions after the
actual Xilinx rewrite and global unreachability/reference checks. Complete
historical circuits, source bytes and instance mappings are independently audited.
Physical BUFGCE state is still unsupported.

Actual exact-Rocket preflight rejects **2 annotation classes**, down from 3.
The remaining RunFirrtlTransformAnnotation requests **InlineInstances**, produced
by actual wrapper elaboration with twelve inline targets; it remains live for
its own execution/mapping contract. The 2,120 unknown raw dedup-group constraints
also remain unsupported; forced dedup temporarily removes --no-dedup. No whole-
Rocket bank RTL or checkpoint-enabled image is emitted. These compiler changes
do not establish physical capture or CPU migration.

All 176 Scala / 306 checkpoint Python / 40 loop tests, retained EDA ASan/UBSan/
FCFS/bank/memory/bridge/host scope, localhost bank/top OOC synthesis and independent
EDA audit pass. Final SP2 VCS checks: 4,669 bank / 7,858 exact-native-top / 21,970
synchronous policy, retaining waveforms. The audit matches 28 files / 33 sources
and rejects 21 emitter plus 33 gate-history corruptions alongside all retained
negatives. Bank resources/timing: 125 LUTs / 82 registers, setup +6.435 ns /
hold +0.054 ns at 140 MHz; external I/O unconstrained. Full image/P&R/AFI,
physical all-hart active cuts, complete paired CPU zero-edge restores, finite
replay, sustained live RTL and rolling recovery remain pending. Reuse iteration194's
localhost invocation. Commands and individual receipts:
`runs/aws-f2/iteration208/summary.json`; exact remaining contracts and producer
replay: `runs/aws-f2/iteration208/remaining-blockers.json`.

Iteration 207 adds an exact passive output-file contract for `.const.h`,
`.const.vh`, `.partition.const.h`, `.peer2peer.const.yaml` and `.defines.vh`.
Original annotations and bytes remain unchanged; context binds each suffix,
UTF-8 byte count and SHA-256, and final emission binds every preserved output.
Duplicate suffixes, malformed/default-charset-mismatched bodies, unknown/IP
scripts, dropped/changed outputs and dropped/changed generated sidecars reject.
These headers remain metadata; they do not prove integrated checkpoint-driver
or physical-state coverage. Independent fixture inputs include UTF-8 and a
legitimate empty peer-to-peer map.

All 159 Scala / 40 loop tests pass. Actual exact-Rocket production preflight
rejects three annotation classes: RunFirrtlTransformAnnotation,
UnrecognizedAnnotation and BlackBoxInlineAnno. Complete image/P&R/AFI, physical
common-cut/memory/timing/bridge/host/pre-FAME binding, four active FPGA cuts,
paired CPU zero-edge restores, finite replay, sustained live RTL and rolling
hardware recovery remain pending. Reuse iteration194's localhost invocation.
All 306 checkpoint Python tests, full retained EDA ASan/UBSan/FCFS scope,
localhost bank/top OOC synthesis and independent EDA audit pass. SP2 VCS checks:
4,669 bank / 7,858 exact-native-top / 21,970 synchronous policy, with debug
waveforms. Twenty new output corruptions reject alongside all retained
negatives; native/VCS audits match 22 files / 27 sources. Bank resources are
125 LUTs / 82 registers; setup +6.435 ns / hold +0.054 ns at 140 MHz, external
I/O unconstrained. Exact commands and receipts: `runs/aws-f2/iteration207/summary.json`.
The saved remaining-blocker investigation identifies 2,120 target-bearing
unknown dedup-group requests and the forced dedup policy that prevents their
silent removal; no unsupported annotation was promoted to complete capture.
Scoped final inventory has no owned F2 runtime or native Vivado/Java job; no
new AFI was requested. Both read-only plan hashes remain unchanged.

Iteration 206 consumes the original FirrtlCircuitAnnotation at the actual
Golden Gate stage entry. Its immutable receipt retains the complete serialized
input-circuit SHA-256, original circuit name and ordered module identities.
Live circuit annotations remain unsupported at the bank boundary. FIRRTL's
outer DeletedWrapper can retain the original input as nested deleted history
after compilation; it is never admitted as bank state. Missing or
multiple stage inputs and already-consumed receipts reject; bank context and
both final-emission boundaries reject dropped, changed or reordered history.
The production-backend fixture uses the same stage consumer and saves the full
historical input. Independent auditing specifies that circuit separately and
rejects **14** missing or coherently rehashed input/history corruptions.
Actual exact-Rocket production preflight rejects **4 annotation classes**, down
from 5; no accepted whole-Rocket bank RTL is emitted.

All **153 Scala / 306 checkpoint Python / 40 loop tests** and the full retained
EDA ASan/UBSan/FCFS/bank/memory/bridge/host scope pass. Native localhost Vivado
2025.2 bank and MMIO/DMA-top OOC synthesis pass. EDA SP2 VCS passes 4,669 bank /
7,858 exact-native-top / 21,970 synchronous-policy checks with debug waveforms.
Independent audit matches seventeen generated files / twenty-three sources;
all prior extraction/pre-link/dedup/context/target-box/XDC/policy negatives remain.
Bank use is 125 LUTs / 82 registers, estimated setup +6.435 ns / hold +0.054 ns
at 140 MHz, with external I/O unconstrained. Commands and individual receipts:
`runs/aws-f2/iteration206/summary.json` relative to the loop.

This is compiler/component evidence. Remaining annotation contracts are
RunFirrtlTransformAnnotation, UnrecognizedAnnotation, BlackBoxInlineAnno and
GoldenGateOutputFileAnnotation. Three physical BUFGCE owners, complete common
cut/memory/timing/bridge/host/pre-FAME integration, full localhost image/P&R/AFI,
all-hart early/warm/outstanding/late FPGA captures, paired CPU zero-edge restores,
finite replay, sustained live RTL beyond the trace window and rolling hardware
recovery remain pending. Reuse iteration-194's localhost invocation. AWS access
checks pass; scoped inventory has no owned F2 instance or native Vivado/Java
job. No new AFI was requested. Both read-only plan hashes are unchanged.

Iteration 205 consumes BridgeExtraction's temporary instance markers at the
actual promote/commute/prune boundary and retains immutable historical input,
promoted/output circuit hashes, ordered bridge identities and complete generated
connectivity hash. Live/deleted markers remain unsupported. Duplicate promotion
requests for repeated bridge-bearing modules are coalesced. A pass-reuse fix
preserves a real input module whose name collides with a previous temporary
wrapper. Historical names remain independent of the later bank hierarchy;
context and both final-emission boundaries reject changed or dropped history.
The production-backend fixture runs actual clock/data bridge extraction with
repeated instances. Independent auditing checks all three complete historical
circuits and complete pipe/clock connectivity and rejects **25** missing or
coherently rehashed extraction corruptions. Exact Rocket production preflight
now rejects **5 annotation classes**, down from 6; no accepted whole-Rocket bank
RTL is emitted.

All **149 Scala / 306 checkpoint Python / 40 loop tests** and the complete
retained EDA ASan/UBSan/FCFS/bank/bridge/host scope pass. Native localhost Vivado
2025.2 bank and MMIO/DMA-top OOC synthesis pass. EDA SP2 VCS passes 4,669 bank /
7,858 exact-native-top / 21,970 synchronous-policy checks with debug waveforms.
Independent audit matches sixteen generated files / twenty-three sources,
retaining all prior sixteen pre-link, twelve deduplication, 26 context, eight
target-box, six XDC and five policy rejections. Bank use is 125 LUTs / 82
registers, estimated setup +6.435 ns / hold +0.054 ns at 140 MHz; external I/O
is unconstrained. Initial fixture compile/expectation failures remain diagnostic;
corrected full-suite logs establish the passes. Commands and individual receipts:
`runs/aws-f2/iteration205/summary.json` relative to the loop.

This is compiler/component evidence. Remaining annotation contracts are
RunFirrtlTransformAnnotation, FirrtlCircuitAnnotation, UnrecognizedAnnotation,
BlackBoxInlineAnno and GoldenGateOutputFileAnnotation. Three physical BUFGCE
owners, complete common-cut/memory/timing/bridge/host/pre-FAME integration,
full image/P&R/AFI, all-hart active FPGA cuts, paired CPU zero-edge restores,
finite replay, sustained live RTL beyond the trace window and rolling hardware
recovery remain pending. Reuse iteration-194's localhost invocation. AWS access
checks pass; final scoped inventory has no owned F2 instance or native
Vivado/Java job. No new AFI was requested. Both plan input hashes are unchanged.

Iteration 204 replaces the consumed mutable PreLinkRenaming namespace request
with immutable history from the actual pass: complete ordered module renames
and hashes of its exact historical input/output circuits. The request itself
and wrapped requests still reject. Duplicate requests reject before namespace
mutation. Historical names remain unchanged through bank specialization;
context and final emission bind every value, rejecting dropped/altered history.
A production-backend fixture uses a real collision/repeated-instance/external
definition pass invocation; its independent audit validates both complete
historical circuits and rejects sixteen missing or coherently rehashed history
corruptions. Exact Rocket production preflight now rejects **6 annotation
classes**, down from 7; no accepted whole-Rocket bank RTL is emitted.

All **142 Scala / 306 checkpoint Python / 40 loop tests** and the complete
retained EDA ASan/UBSan/FCFS/bank/bridge/host scope pass. Native localhost Vivado
2025.2 bank and MMIO/DMA-top OOC synthesis pass. EDA SP2 VCS passes 4,669 bank /
7,858 exact-native-top / 21,970 synchronous-policy checks, retaining debug
waveforms. Independent audit matches twelve generated files / twenty-one
sources, including both historical circuits, and retains all 26 context, twelve
deduplication, eight target-box, six XDC and five memory-policy rejections.
Bank use remains 125 LUTs / 82 registers, estimated setup +6.435 ns / hold
+0.054 ns at 140 MHz, with external I/O unconstrained. Initial fixture-only
compile/expectation failures and corrected full-suite logs remain diagnostic.
Commands and individual receipts: `runs/aws-f2/iteration204/summary.json`
relative to the loop.

This is compiler/component evidence. Remaining annotation contracts are
RunFirrtlTransformAnnotation, FirrtlCircuitAnnotation, UnrecognizedAnnotation,
BridgeExtraction$BridgeInstance, BlackBoxInlineAnno and
GoldenGateOutputFileAnnotation. Three physical BUFGCE owners, complete common
cut/memory/timing/bridge/host/pre-FAME integration, full image/P&R/AFI, all-hart
active FPGA cuts, paired CPU zero-edge restores, finite replay, sustained live
RTL beyond the trace window and rolling hardware recovery remain pending.
Reuse iteration-194's localhost invocation. AWS access checks pass; final scoped
inventory has no owned F2 instance or native Vivado/Java job. No new AFI was
requested. Both plan input hashes remain unchanged.

Iteration 203 adds an explicit FIRRTL DedupedResult specialization contract.
The historical original module identity and normalized index remain unchanged;
only the live destination and every instance hop follow bank specialization.
Removed-destination history retains FIRRTL's -1 sentinel. Invalid indices and
foreign, stale, opaque, unreachable or mismatched destinations reject. Complete
source/translated values and mapping rows are hash-bound, and both bank-state
and final emitted annotations are checked against the stored translation.
An independent fixture audit derives the destination from actual instrumented
IR and rejects twelve coherently rehashed history corruptions. Exact Rocket
production preflight now rejects **7 annotation classes**, down from 8; it still
emits no accepted whole-Rocket bank RTL.

All **135 Scala / 306 checkpoint Python / 40 loop tests** and the full retained
EDA ASan/UBSan/FCFS/bank/bridge/host scope pass. Native localhost Vivado 2025.2
bank and MMIO/DMA-top OOC synthesis pass; bank use is 125 LUTs /
82 registers, estimated setup +6.435 ns / hold
+0.054 ns at 140 MHz, with external I/O unconstrained. Matching
EDA SP2 VCS passes 4,669 bank / 7,858 exact-native-top / 21,970 synchronous-policy
checks with debug waveforms. Independent audit matches ten generated files /
nineteen sources, retaining all 26 context, six XDC, five memory-policy and
eight target-box corruption rejections alongside the twelve new history cases.
Commands and individual receipts: `runs/aws-f2/iteration203/summary.json`
relative to the loop.

This is compiler/component evidence. Remaining annotation contracts are
RunFirrtlTransformAnnotation, FirrtlCircuitAnnotation, UnrecognizedAnnotation,
BridgeExtraction$BridgeInstance, BlackBoxInlineAnno, PreLinkRenamingAnnotation
and GoldenGateOutputFileAnnotation. Three physical BUFGCE owners, complete
common-cut/memory/timing/bridge/host/pre-FAME integration, full image/P&R/AFI,
all-hart early/warm/outstanding/late FPGA cuts, paired CPU zero-edge restores,
finite replay, sustained live RTL beyond the trace window and rolling hardware
recovery remain pending. Reuse iteration-194's localhost invocation. Final
scoped inventory has no owned F2 instance or native Vivado/Java job; no new AFI
request was made.

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

Iteration 198 adds correlated per-instance XDC translation, exact logical-RAM
memory-model labels and emitted-XDC receipt hashes. Repeated-root constraints
retain their original physical paths; malformed or altered targets reject.
113 Scala / 306 checkpoint Python / 40 loop checks and the full retained EDA
ASan/UBSan scope pass. Native fixture constraints are checked against actual
cells and retained DCP commands; native OOC uses 125 LUTs / 82 registers.
Matched-input bank VCS passes 4,669 checks, exact-native-input MMIO/DMA top
passes 7,858, and six missing/coherently rehashed XDC corruptions reject.
An initial invalid endpoint trial remains explicitly rejected. The fresh real-recipe bank trial rejects 22 remaining
annotation classes and emits no accepted Rocket banks. This is compiler and
component evidence. Full checkpoint image/P&R/AFI, physical primitive/common-cut,
functional-memory/host ownership, all four active FPGA cuts and complete paired
CPU zero-edge, finite/live and rolling acceptance remain pending. Commands and
individual receipts: `runs/aws-f2/iteration198/summary.json` relative to the loop.

Iteration 197 integrates explicit FPGA SYNTHESIS plusarg selection into the
actual production compiler and emits source-bound original/prepared/emission
receipts. Independent reconstruction covers four definitions / seven instances,
including each hart's timeout input. Final model inventory has 11,459 entries /
618,247 words / 2,282 instances; all three physical BUFGCE owners remain
unsupported. NoDedup/Inline clone contracts and passive output-directory
preservation reduce the real bank preflight rejection to 25 classes without
admitting unknown state owners. All 109 Scala / 306 checkpoint Python / 40 loop
checks and full retained EDA ASan/UBSan scope pass. New branch verification
passes 6,150 comparisons / 3,075 fixture edges across explicit FPGA, original
SYNTHESIS and ordinary runtime variants; first wrong-oracle comparison stops
before edge zero, with debug waves. Identical final inputs synthesize locally
(22 LUTs / 32 registers, OOC only). These are compiler/component results.
No checkpoint-enabled full image, F2 capture, CPU restore, finite/live CPU
replay or rolling hardware acceptance is advanced. Current receipts/commands:
`runs/aws-f2/iteration197/summary.json` relative to the loop.

Iteration 196 fixes reachability-scoped gate admission and emits a source-bound
external-owner audit. Independent reconstruction covers all 2,293 emitted
instances: three physical BUFGCEs, seven plusarg-model instances and eleven
unused external definitions. All physical capture bindings remain unsupported.
101 Scala / 298 checkpoint Python / 40 loop tests and the full retained EDA
ASan/UBSan scope pass. The native-model EDA experiment passes (3,658 checks / 682
phase observations / 256 source edges). The abstract gate produces 73 extra
positive pulses despite matching settled outputs; it cannot substitute for
BUFGCE. The fresh production bank trial now fails explicit annotation
translation (28 classes). No complete image/AFI, F2 checkpoint, paired CPU
restore, finite/live CPU replay or rolling-hardware status is advanced.
Commands, scope and evidence: `runs/aws-f2/iteration196/summary.json` relative
to the loop. The iteration-194 localhost checkpoint-build invocation remains
available; no duplicate farm or AFI request was launched.

Iteration 195 invokes bank generation after actual production FPGA lowering
through an explicit, non-deployable diagnostic option. All 97 Scala / 290
checkpoint Python / 40 loop tests and retained EDA sanitizer regressions pass.
The production-path bank fixture passes 4,669 EDA VCS checks, reads complete
state at component cycles 2 / 39 / 132 / 900, continues through 1,025 functional
edges, and rejects first-word corruption frozen before acknowledgement.
Identical inputs synthesize natively to 44 LUTs / 26 registers (OOC only).
Top MMIO/DMA passes 7,858 checks on exact native inputs; final independent EDA
probe/DCP/top and all 780 dense-word audits pass.
Fresh exact-Rocket bank compilation **fails** the exact adapter check for
`AbstractClockGate_0`; it produces no accepted Rocket banks or capture image.
Physical primitive/annotation contracts, memory/host/common-cut and live
transport integration, image P&R/AFI, hardware cuts and paired CPU migration
remain pending. No hardware matrix status is advanced. Commands/evidence:
`runs/aws-f2/iteration195/summary.json` relative to the loop.

Iteration 194 repairs production post-mapping host-transform propagation and
binds inventory to the actual emitter state. All 94 Scala / 290 checkpoint
Python / 40 loop tests and the retained EDA sanitizer scope pass. New EDA VCS
performs 4,100 output comparisons over 1,025 host edges and detects discarded
host circuitry at cycle 1; identical fixture inputs synthesize natively.
Top MMIO/DMA passes 7,858 checks using exact native inputs; independent EDA
emission/DCP/top audits and all 780 dense-word reconstructions pass.
Fresh exact-recipe compiler emission inventories 11,466 entries / 618,254
words / 2,293 instances from retained target inputs. This ordinary compilation
has no semantic-preservation/capture binding and is distinct from the retained
instrumented probe. No AFI, physical checkpoint, CPU restore or live/rolling
hardware status is advanced. Commands/evidence:
`runs/aws-f2/iteration194/summary.json` relative to the loop.

Iteration 193 adds balanced masked state readout and a dense 260-owner fixture.
All **90 Scala / 290 checkpoint Python / 40 loop tests**, complete retained EDA
ASan/UBSan scope, **13,558** dense checks / **780** word reads and top MMIO/DMA
**7,858** checks pass. Dense cuts at **2 / 39 / 132** include original-RTL and
public-input oracles, **3,120** stalled boundaries, invalid selectors, first-word
corruption stop and debug waveforms. All **15** native OOC commands and final
independent EDA audits complete. Whole-root setup WNS improves **-0.916 ->
-0.287 ns** and setup violations **6,878 -> 72**; hold WHS remains **-0.324 ns**.
The parent exits 0 with a CRC-checked DCP despite a retained parallel-worker
shutdown exception. Complete image timing remains unverified. Detailed source,
resource and diagnostic scope: [fpga-capture-transport.md](fpga-capture-transport.md).
Commands/receipts: `runs/aws-f2/iteration193/summary.json` relative to the loop.
The production recipe still has no complete capture binding; custom AFI, actual
FPGA captures, paired CPU zero-edge restores, finite/live RTL comparison and
rolling hardware recovery remain **pending**.

Iteration 192 distinguishes computed Clock-typed FAME token data from physical
clock origins. The binding records the expression and its defining hierarchy;
registers, memory ports/pipelines, gate sources and clocked effects still reject
computed clocks. Descriptor reconstruction rejects altered provenance and
sequential rewiring even with an updated circuit hash. The new repeated-child
fixture uses tokens for functional data updates. Fresh EDA VCS passes **5,483**
checks and 60 complete word reads at component cuts **6 / 43 / 126 / 223**, with
independent clocks, frozen pressure, backpressure, continuation, full debug VCD
and first-word corruption stop. All **89 Scala / 286 checkpoint Python / 40
loop tests** and the retained EDA sanitizer scope pass.

The retained exact-recipe whole-root probe now emits and validates banks for
**12,099 entries / 619,016 words / 21,005,343 logical bits / 2,300 instances**.
Its 2,120 clock-port rows include four computed data routes, eight static pins,
one explicitly invalid pin and three registered gate adapters. This is the
retained iteration-184 generated RTL, with `external_runtime_required=true`;
it does not establish physical primitive, functional-memory/host, common-cut,
bridge integration or FPGA coverage. All **14** native OOC synthesis runs complete, including the retained whole root
(**715,823 LUTs / 107,016 registers / 64 DSPs / no block RAM**). Whole-root
estimated WNS **-0.916 ns** / WHS **-0.324 ns** fails setup/hold; external I/O is
unconstrained and OOC clock-buffer locations are unbound. The worst setup path
has 34 logic levels into the checkpoint response register. Complete image timing
closure remains pending. Final independent EDA audits pass, including whole-root
inventory/source/DCP checks, retained negatives, **14** coherently rehashed token
origin corruptions and **23** new fixture receipt corruptions. Top VCS passes
**7,858** checks on exact native inputs. Fresh inventory records no invocation
runtime instance or remaining native Vivado/Java job.
Complete checkpoint-image P&R/AFI, active F2 captures, paired zero-edge CPU
restores, finite/live comparison and rolling recovery remain **pending**.
Commands and immutable receipts are cataloged in `runs/aws-f2/iteration192/summary.json` relative to the loop.

Iteration 191 preserves explicit invalid metadata origins without fabricating
functional clocks or dropping pins. Independent descriptor checks reject invalid
origins on storage/RAM/effects, altered bindings and post-generation consumer
rewiring. All **86 Scala / 286 checkpoint Python / 40 loop tests** and the full
retained EDA bank/transport/host/FCFS ASan/UBSan scope pass. Fresh EDA VCS checks
all 15 words at **6 / 43 / 126 / 223**, with **5,483** checks, 60 readouts,
backpressure, frozen reset/write/clock pressure and first-word corruption stop.
Full debug VCD is retained. All **12** native component syntheses and final
independent audits pass, including **12** invalid-origin semantic corruptions
and **23** receipt corruptions. The invalid fixture uses **181 LUTs / 79
registers**, estimated WNS **+6.298 ns** / WHS **+0.049 ns** at 140 MHz.
These are OOC estimates with unconstrained external I/O; FASED retains negative
hold slack and whole-image timing remains pending. Top VCS passes **7,858**
checks on exact native-synthesis inputs. This remains component evidence only. The whole retained probe clears
the invalid PeekPoke dummy clock and exits **1** on computed Clock-typed token
data from `ClockBridgeModule_0.clockTokenGen.eq(timeToNextEdge_0,
minStepsToEdge)`. Inventory remains **12,099 entries / 619,016 words**; no
complete bank output or custom checkpoint AFI is claimed. Raw diagnostic,
exact inputs, route analysis and final verification catalog are under
`runs/aws-f2/iteration191/summary.json` relative to the loop. Complete memory/host/physical owners, image P&R/AFI, all active F2
cuts, paired CPU zero-edge restores, finite/live comparison and rolling
hardware recovery remain **pending**.

Iteration 190 binds exact zero/one metadata clock pins explicitly without
inventing functional domains, and independently rejects static clocks feeding
storage, RAM pipelines/ports or clocked effects. All **83 Scala / 286 checkpoint Python / 40 loop tests**, full retained EDA
FCFS/fixture/host ASan/UBSan scope and **11** native component syntheses pass.
Fresh EDA VCS passes **5,483** static-fixture checks at complete component cuts
**6 / 43 / 126 / 223**, with 60 word reads, frozen backpressure/clock/reset/write
pressure and first-word corruption rejection. Independent audits verify all 22
clock-port routes / eight static metadata pins and reject all **10** semantic
metadata corruptions plus **23** receipt corruptions. Native static-fixture OOC
synthesis uses **181 LUTs / 79 registers**, estimated setup WNS **+6.298 ns** /
hold WHS **+0.049 ns** at 140 MHz, with external I/O unconstrained. This is
component evidence; whole-image timing and physical capture remain pending.
Post-generation clock rewiring with an updated circuit hash rejects in Scala.
The whole retained recipe probe now clears the tied-off bridge clock rejection
and stops on the explicitly invalid PeekPoke dummy `tIO_clock` pin. Complete
inventory remains **12,099 entries / 619,016 transfer words**; no complete bank
output or custom checkpoint AFI is claimed. Fresh component verification and
raw compiler diagnostics are cataloged under
`automations/checkpoint_loop/runs/aws-f2/iteration190/summary.json`. Complete
hardware owners/common cut, checkpoint image, all active FPGA cuts, paired
restores, finite/live CPU comparison and rolling F2 recovery remain **pending**.

Iteration 189 explicitly materializes the exact source-bound FPGA plusarg
`SYNTHESIS` constants, retaining original-circuit/parameter provenance through
inventory and instance-specialized descriptors. Metasim `myplus` owners remain
independent. Fresh EDA VCS original-model comparison passes **608 checks**,
**173 functional edges**, complete component reads at **2 / 39 / 132** and
first-word semantic corruption rejection, with full debug VCD. All **80 Scala /
286 checkpoint Python / 40 loop tests** and the full retained EDA FCFS/fixture/
host ASan/UBSan scope pass. All ten native localhost component synthesis checks
pass; the new constant component uses **84 LUTs / 66 registers**, estimated
setup WNS **+6.232 ns** / hold WHS **+0.067 ns** (OOC, unconstrained external I/O;
not whole-image timing closure). Independent EDA audits pass, including all
**16** new receipt/semantic corruptions; the top fixture uses exactly the native
synthesis's immutable generated inputs after an initial elaboration mismatch
was correctly rejected. The whole retained exact-recipe source inventories
**12,099 entries / 619,016 transfer words**, then bank generation **fails** on
FPGATop's constant-zero bridge target-clock pins. Inventory is not synthesized
coverage. Raw failure, prepared manifests and commands are under
`automations/checkpoint_loop/runs/aws-f2/iteration189/`. Complete generated and
physical primitive mapping/common-cut memory/host coverage, image P&R/AFI,
actual quad-hart FPGA capture, paired zero-edge CPU restores, finite/live
comparison and rolling F2 recovery remain **pending**.

Iteration 188 implements exact registered-enable gate ownership and conditional
RAM-clock guard validation. The retained exact-recipe FASED subtree now emits
**759 entries / 99,611 transfer words**. Independent EDA component checks cover
four complete cuts, both enable values, original RTL/public-input oracles,
frozen clock/reset/write pressure and first-word corruption. Native localhost
component synthesis, full retained regressions and independent audits are
cataloged under `automations/checkpoint_loop/runs/aws-f2/iteration188/`.
All **77 Scala / 286 checkpoint Python / 40 loop tests** and the full retained
EDA regression scope pass. The gate component passes **3,023** checks / **28**
readouts, with all **23** receipt corruptions rejected. Native gate synthesis
uses **103 LUTs / 50 registers**. Native FASED component synthesis uses
**75,132 LUTs / 6,522 registers**, estimated setup WNS **+0.978 ns** and hold WHS
**-0.299 ns**, with **4,102** failing hold endpoints. This is OOC synthesis,
not timing closure; external I/O is unconstrained and FASED runtime remains pending.
This is abstract-gate/component evidence. Platform-mapped primitive state,
complete simulator/common-cut memory/host coverage, whole-image P&R/AFI,
quad-hart hardware capture, paired restores, finite/live CPU comparison and
rolling F2 recovery remain **pending**.

Iteration 187 adds transparent hierarchical clock forwarding through output
ports, siblings and concrete one-bit clock IO, with **14** independently checked
clock-port routes and preserved synchronous RAM pipeline clocks. Fresh EDA VCS
passes **5,483** checks and complete 15-word component cuts at **6 / 43 / 126 /
223**, including frozen resets/writes, independent clocks, backpressure,
post-release activity and first-word corruption rejection. Native localhost OOC
synthesis uses **181 LUTs / 79 registers**, estimated WNS **+6.298 ns** at 140 MHz.
All **71 Scala / 286 checkpoint Python / 40 loop tests**, retained full EDA
FCFS/fixture scope and seven native synthesis checks pass. Independent audits
verify the complete new cuts and 48 immutable files; all 23 forwarded-clock
receipt corruptions reject. This is component evidence only. Complete
Rocket/FAME/gated-clock/memory/host integration, whole-image P&R/AFI, all four
active quad-hart FPGA cuts, hardware-origin paired images/trace, CPU restores,
finite/live comparison and rolling hardware recovery remain **pending**.
Evidence and commands are under `automations/checkpoint_loop/runs/aws-f2/iteration187/`.

Iteration 186 adds explicit multiple direct functional clock domains to the
separate-transport-clock bank generator, with independently checked per-instance
root-clock provenance. EDA VCS checks all 15 words at each of four component cuts
against unchanged original RTL and a functional-input model, including swapped
children, split-clock RAMs, reset/write freeze, independent clock activity,
response backpressure and frozen first-word corruption rejection. **5,483**
checks pass across **352** functional steps; all four cuts retain complete
per-domain edge labels and full VCD. Native localhost OOC synthesis uses **181
LUTs / 79 registers**, with all three clocks constrained at 140 MHz; this is
component evidence only. Complete Rocket/gated-clock/FAME/
memory/host integration, checkpoint-image P&R/AFI, FPGA-produced paired images
and real traces, all four active quad-hart cuts, CPU restores/finite/live
comparison and rolling F2 recovery remain **pending**. Individual receipts and
commands are under `automations/checkpoint_loop/runs/aws-f2/iteration186/`.

Iteration 185 adds a separate always-running bank response clock and validates
the actual retained Rocket D-cache data array: **64 512-byte RAMs + 64 read-data
pipeline owners**, **32,832 words per component cut** at **C=513 / 611 / 869**.
Fresh EDA VCS passes **7,132,541** checks / **98,496** reads / **196,992** stalled-response cycles,
including **65,664** reads with the functional clock stopped and **131,328**
frozen functional-clock edges with writes enabled. Every word/output matches
unchanged original RTL and a separate functional-input model; first-word
corruption stops frozen at C=513. Full VCD is retained. Native localhost OOC
synthesis uses **9,568 LUTs / 522 registers**, estimated setup slack **+5.228 ns**
with both clocks constrained at 140 MHz. This is retained-source component
evidence; complete Rocket image/AFI and physical checkpoint capture remain
**pending**, as do hardware-origin paired images/trace, all four workload cuts,
CPU migration, finite/live comparison and rolling FPGA recovery. Exact commands
and individual receipts are under
`automations/checkpoint_loop/runs/aws-f2/iteration185/`.

Iteration 184 validates the actual retained Rocket DTLB subtree (17 specialized
modules / 101 register words) through generated public bank readout and native
localhost OOC synthesis. Complete cuts **C=2 / 39 / 132** pass **28,918** EDA VCS
checks / **303** reads / **1,212** response-stall cycles against independent
original RTL, with full VCD and first-word corruption stopped frozen at C=2.
A separate effects fixture checks print/stop/assertion freeze and release.
Native DTLB synthesis uses **3,084 LUTs / 1,859 registers**, estimated setup
slack **+4.450 ns** at 140 MHz. This is a retained-recipe component, not a new
Rocket image or hardware capture. Exact commands, per-cut words/hashes and
original-source provenance are under
`automations/checkpoint_loop/runs/aws-f2/iteration184/summary.json`.
Both FPGA-produced image levels and boundary trace, every required active
quad-hart cut, complete zero-edge CPU restores, finite/live CPU execution and
rolling F2 recovery remain **pending**.

Iteration 183 adds versioned wide/deep generated bank mapping, complete EDA
fixture readout/reconstruction through production MMIO/DMA, and native localhost
synthesis. Each of **C=1 / 42 / 138** captures **65,564** physical / **65,545**
logical words, including signed 65-bit and 128/512-bit registers, 129-bit RAM
and a 65,537-entry RAM. Original RTL, functional-input oracles, reset/write
freeze, backpressure, first-word semantic corruption and ASan/UBSan host frame
validation pass. Native OOC synthesis uses **20,687 LUTs / 259 registers**;
this is not Rocket image P&R or an AFI. Exact commands, per-cut hashes and logs
are under `automations/checkpoint_loop/runs/aws-f2/iteration183/`.
Rocket hardware capture, both FPGA-produced image levels, fresh CPU restores,
finite/live CPU execution and rolling hardware recovery remain pending.

Iteration 182 preserves initialization/preservation annotations through generated
module specialization, with explicit local/nonlocal target translation and
annotation hashes in the bank/driver binding. Initialized repeated RAMs pass
complete public-port readout at **C=0 / 7 / 44 / 155**, independent original-RTL
and functional-input checks, freeze/stall/release and selector negatives in EDA
VCS. Native localhost Vivado checks the actual initialized memory bit planes.
The initialized files, full waveforms, generated inputs and raw execution logs
are retained under `automations/checkpoint_loop/runs/aws-f2/iteration182/`.
No Rocket checkpoint-enabled AFI, hardware-origin CPU images/trace, CPU restore,
finite/live CPU comparison or rolling F2 recovery is claimed.

Iteration 181 adds complete synchronous RAM address/data pipeline owners to
generated bank capture. Fresh EDA VCS SP2 passes **21,970** checks, **454** reads,
ten complete 45-word fixture cuts and **2,905** observed edges / **202** functional
edges against unchanged passthrough reference RTL plus an independent oracle.
Native localhost OOC synthesis passes at **133 LUTs / 32 registers**, estimated
setup slack **+6.087 ns** at 140 MHz; full fixture VCD and native DCP are retained.
All **54** Scala / **283** checkpoint Python / **40** loop tests and complete
retained FCFS/bank/Widget/transport-host/cut/network/top scope pass. Independent
EDA audits bind private VCS/native synthesis inputs, complete cuts, native DCP
identity and final resource inventory; all **14** evidence-tamper cases reject.
The earlier mutable-generated-file audit failure is preserved historically.
Exact commands, individual files and hashes are cataloged in
`automations/checkpoint_loop/runs/aws-f2/iteration181/summary.json`.
Full Rocket source integration/image P&R/AFI/deployment, FPGA-origin captures,
CPU restores, finite/live CPU comparison and rolling recovery remain pending.

Iteration 180 registers the global manifest-bound Widget in FPGATop's actual
MMIO interconnect and CPU DMA stream engine, preserving existing bridge stream
indices. Unbound ROMs/ports reject. Fresh EDA VCS passes **7,858** checks on
**33** generated fixture words at **C=109 / 167 / 305**, with **660** stalled
DMA cycles and **1,926** frozen edges. Missing owners, full stream queues,
reset/write freeze, abort/drain/reuse and first-data-word corruption rejection
pass. Each cut passes **66** decoder negatives and **5,532** ASan/UBSan host
checks; the actual top-generated constructor compiles. Full fixture VCD is
retained. All **52** Scala / **283** checkpoint Python / **40** loop tests and
retained FCFS, bank, Widget, transport/host and cut regressions pass.
Native localhost Vivado synthesizes the integrated fixture FPGATop at
**3,528 LUTs / 1,383 registers**, estimated setup slack **+4.282 ns** at
140 MHz. This is out-of-context fixture synthesis. Commands, per-cut
receipts/hashes and native logs are cataloged by
`automations/checkpoint_loop/runs/aws-f2/iteration180/summary.json`.
No checkpoint-enabled AFI, hardware-origin CPU image/trace, CPU restore,
finite/live CPU comparison or rolling F2 recovery is claimed.

Iteration 179 joins actual generated register/RAM banks to an immutable,
manifest-bound descriptor ROM and the real NASTI/DMA Widget. The ROM and host
C++ metadata share one checked complete binding; generated constructors compile
against production registry/driver types. Fresh EDA VCS passes **1,014** network
checks, **48** bank reads and **82** DMA stall cycles at component cuts
**C=30 / 60 / 134**. Each 16-word stream passes **49** decoder negatives and
**2,940** ASan/UBSan host checks. A semantic bit flip stops at the first state
word at **C=30**, frozen before publication. Missing fixture-owner rejection
and counted abort/reuse pass. Full component waveforms are retained.
All **48** Scala, **283** checkpoint Python and **40** local loop tests pass;
retained full FCFS ASan/UBSan/VCS and bank/Widget/host/cut regressions pass.
Local Vivado synthesizes the generated bank (**138 LUTs / 67 registers**) and
Widget with ROM (**1,725 LUTs / 692 registers**), with estimated setup slack
**+6.298 / +4.425 ns** at 140 MHz. This is out-of-context component synthesis.
Receipts and exact per-cut commands are under
`automations/checkpoint_loop/runs/aws-f2/iteration179/`, including
`network-vcs-final/generated-network-0fzl_g1v/summary.json` and
`retained-lig9qsoz/summary.json`. No checkpoint-enabled AFI, F2 capture, complete
CPU restore/replay, live shadow or rolling hardware recovery is claimed.

Iteration 178 adds generated real-register/RAM endpoint readout and freeze,
global NASTI/StreamToHostCPU transport and a native MMIO/stream capture driver.
EDA VCS passes **571** endpoint checks / **53** reads, **73** NASTI adapter
checks and **133** complete Widget checks / five fixture frames. Native
ASan/UBSan host capture passes **1,384** checks, including cumulative-frame
drain recovery, corruption/truncation, incompatible manifests and frozen
publication. Full checkpoint Scala passes **40** tests; Widget Scala passes
four. Full required FCFS native/VCS regression passes with system GMP and
sanitizer libraries; the earlier missing-runtime block is resolved.
Local native Vivado 2025.2 synthesizes the generated endpoint at **138 LUTs /
67 registers** and the complete Widget at **1,878 LUTs / 756 registers** for
`xcvu47p-fsvh2892-2-e`. Estimated setup slack is **+6.298 / +4.432 ns** at
140 MHz; both DCPs and reports are retained. This is out-of-context component
synthesis, with full-image P&R and physical capture still pending.
Per-component source/generated hashes, cut labels, exact compiler commands
and raw native logs are cataloged by
`automations/checkpoint_loop/runs/aws-f2/iteration178/summary.json`.
Generated banks still reject real Rocket synchronous/readwrite RAM pipelines,
unchunked wide/deep storage and unretargeted annotations explicitly. No
FPGA-produced image/trace or CPU live comparison was created this iteration.

Iteration 177 component evidence: fresh EDA VCS SP2 passes **1,294** checks,
five successful publications, **36** bank requests and DMA/MMIO backpressure.
The host decoder rejects **39** corrupt/truncated/incompatible/incomplete
variants of that actual component stream. Local Vivado 2025.2 synthesizes
16-owner/1,024-entry transport for the F2 part with **2,055 LUTs / 423 registers**;
post-synthesis estimated setup slack is **+4.816 ns** at 140 MHz. This is not
place-and-route, an AFI, a Rocket checkpoint or a hardware-origin CPU restore.
The new fixture `.rtlckpt` is explicitly component/VCS-origin. All four real
Rocket cuts, source-FPGA references, independent complete CPU readbacks,
finite replay, sustained live RTL shadow/waveforms and rolling F2 recovery
remain **pending**. See [fpga-capture-transport.md](fpga-capture-transport.md)
for protocol, remaining integration work and executable commands.

## Historical metasim and component progress

Current milestone: M11 Rocket, iteration 175, **in_progress**. Rocket Level 2
passes complete captured ChipTop finite replay at four tested cuts. Complete
Level-1 CPU continuation remains pending. These historical entries did not validate physical FPGA capture. Standalone
Shuttle and ASIC power remain outside scope. The verified FCFS evidence remains in its existing docs.

| Family / existing recipe | Level 1 | Level 2 | Workload evidence |
| --- | --- | --- | --- |
| Rocket / `firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3` | in_progress: private blockdev now supports prepared/sealed publication with fresh native/VCS component readback and continuation; buffered heartbeat now supports prepared/sealed publication with complete native/VCS fresh component checks; base and concrete-driver lifecycle owners now support prepared/sealed publication in fresh native/VCS components; CPU-managed stream initialization and peek/poke result flags have audited prepared/sealed scalar publication in native/VCS fresh components; master/clock/loadmem/reset configuration-only sealed publication passes native/VCS fresh component checks; default-unsupported prepared-owner contract and scheduler/bridge-loop sealed publication pass fresh component checks; functional-memory preparation/sealing and allocation-free publication preserve backing aliases; joint runtime I/O preparation/publication passes fresh component restores and complete allocation-failure sweeps; generated RTL inventory audited; returned MMIO and CPU stream I/O component restores pass; TracerV and FireSim driver/termination-loop continuations pass; production TSI read, all four load-memory queues, bridge host control and FireSim idle/reset control pass fresh component restores; source-integrated FESVR serial FIFOs pass fresh component restores; serial-read progress passes complete fresh component restores; production TestChip initialization caller/serial-child dispatch and atomic four-owner component restores pass; program-load transport/entry/return ownership passes fresh component readbacks; production HTIF poll caller passes nine-phase fresh component continuations; suspended eight-owner inspection passes actual Rocket workload samples; exact-ELF startup metadata passes fresh host-component preparation/readback; default BCD pending commands pass fresh component continuation; metadata revision-3 transport and exact installed-XLEN policy reject atomically; build-local ELF-loader overlay closes tested descriptor/mapping exception leaks; context overlay owns inactive/thread-exit stack storage and rejects invalid lifetimes; opt-in sealed BCD terminal input/cursor/transcript passes fresh component restores; revision-4 sealed startup metadata binds all eight pristine peers, sealed polling audits include BCD/terminal, and paired terminal/BCD restoration and bound poll/terminal/BCD restoration reject allocation failures atomically; all twelve known sealed polling components prepare atomically in a fresh metadata-bound TSI, and a restricted sealed BCD caller passes fresh component continuations without startup/reset or context entry, including identity writes at every address residue with complete parent/caller/write/FIFO ownership; ordinary identity dispatch additionally owns its command and write/response/return cursor with atomic caller/write/FIFO component preparation, with twelve-owner atomic sealed polling preparation and fresh continuation through active identity merge cuts; generic memif read caller/FIFO passes fresh native/VCS continuations with and without cache flushing; the installed default syscall session now dispatches runtime reads through the owned virtual memif interface, with full syscall/session/context restoration pending; direct pass/fail/stop component projections pass and active unowned exit cuts reject; opt-in exact-header provider is linked and audited in the exact-recipe metasim build and passes actual private exit/stopped restores using that linked archive; destination-aware single-use lifecycle preparation and guarded nonthrowing peer publication pass native/VCS component checks; all twelve known polling owners now prepare without publication and commit after a fresh destination check; the fourteen-owner polling/direct-exit/lifecycle group now prepares and publishes atomically, including pending-exit readback and guarded direct-exit continuation through no-signature stop; completed direct-exit group restoration and terminal readback pass; an independent exact-provider delivered-signal/lifecycle component passes fresh readback, real handler delivery and atomic peer publication, with actual all-thread mask/pending audits and atomic rejection now passing, while the production thread coordinator and signal-caused caller ownership remain pending; an independent executable syscall-93 parent now restores all eight request words, nested memif progress, writeback and response order with actual lifecycle/serial peers, with explicit restricted live polling and atomic fourteen-owner group integration passing fresh native/VCS continuations and independent ownership audits; restricted polling now omits the unused default syscall session, audits actual descriptor lifetimes and extends fresh component coverage through zero-mailbox idle yields; restricted mode now retires inherited proxy descriptors/table and rejects repopulated resources at group boundaries; production run_host now owns its five outer phases and signed return value with fresh component restores and actual coroutine checks; the restricted fifteen-owner outer/polling/syscall/provider aggregate now passes atomic fresh native/VCS restoration through stop and signed return; the restricted sixteen-owner wrapper/outer/polling/provider aggregate now passes fresh native/VCS coroutine continuation without startup replay, with exact creator/stack/signal guards; the actual lifecycle provider now enforces all-thread blocked/pending and exact-action admission for the aggregate at capture, preparation, commit and resume; the supported aggregate, serial/load-memory entries and retained owner references now enforce lifetime-bound creator-thread access; a build/metadata-bound sixteen-owner image now passes actual live creator capture and fresh creator-side candidate preparation/publication with complete component continuation; the production bridge now privately prepares a fresh creator-side TSI plus control and publishes them together, with restored context service dispatch and constructor parser/descriptor rollback; an optional pre-edge driver creator mailbox now passes same-thread actual-harness continuation and explicit MMIO/tick hold checks, including poisoned bootstrap; creator-owned resource retention now keeps the actual restricted provider live through component launch and cancellation, with complete seventeen-owner launch readback and creator-side destruction; ordinary-session, production process coordination and full simulator aggregate integration remain pending; complete HTIF/memif/device/context/TestChip-loader/cross-owner ownership and fresh CPU continuation pending | verified for complete retained ChipTop: four actual cuts; all 318,637 words read back before any ordinary RTL edge; 256 captured events / 21,760 output comparisons; 16 real first-boundary corruptions and 44 atomic invalid cases | Complete 16-GiB four-hart capture control passes at C=3,329,794; every full hart trace and workload/store label matches. Prior default/buffered/sealed controls retained. Level-1 CPU continuation remains pending |
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

## Iteration 175: prepared block-device publication and explicit audit receipts

Complete Rocket Level 1 remains **in_progress**, with CPU admission disabled.
The private-memory/disconnected `firesim.widget.blockdev.v1` owner now prepares
all decoded queues, trackers, disk bytes and a positioned libc stream. Sealing
binds destination bytes, lifetime, native thread, generation and consumption.
Allocation-free `noexcept` publication swaps resources and assigns two flags;
it performs no libc stream I/O, MMIO or edge. Retired streams/backing are cleaned
up after publication. Legacy loads use the same guarded path. Payload v1 and
actual recipe settings above are unchanged. External disks/logs and
suspended/poisoned calls reject. See
[blockdev-sealed-publication.md](blockdev-sealed-publication.md).

Native ASan/UBSan and fresh VCS pass **30** prepared continuations and complete
pre-edge readbacks at all **15** component cuts, with **25,870** continued MMIO
calls. This includes partial writes, queued requests/data and stalled responses
and acks. Each backend passes **756** candidate rejections, **65** preparation
and **44** sealing allocation failures, plus both libc preparation failures.
The matrix also passes **12** fatal contract cases, **2** unexpected-return
controls, **8** malformed fresh loads and **2** actual tracker-data corruptions,
stopping at `bdev_rresp_data_lower` at fixture **C=142** before the next
operation. Full nonzero disk backing, EOF cursor, disconnected streams,
cancellation and retired-stream cleanup are checked. Publication keeps libc
call counters unchanged while the next C++ allocation is forced to fail.
These fixture cuts do not establish Rocket Level-1 continuation.

Prepared receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/blockdev-prepared/native-33p9_drw/summary.json`.
The preserved legacy block-device matrix also passes all **30** fresh
continuations with the current implementation:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/native-regressions/invocation-pdr771kk/blockdev-regression/native-qgl1k1yq/summary.json`.
All **eight** preserved regression scopes pass, including **280** Python tests,
semantic/banked, widget, FCFS, UART, blockdev and heartbeat. The prepared concrete
driver matrix independently passes **224** fresh native/VCS continuations.
Receipts:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/native-regressions/invocation-pdr771kk/summary.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/driver-regression/invocation-640sfx80/summary.json`.

The independent retained Rocket Level-2 audit passes C=100 / 700,000 / 900,000 /
3,250,000, **318,637** pre-edge semantic words per cut, **256** events, **16**
actual first divergences and **44** invalid cases. This re-audits original
ordinary RTL VCS capture/replay artifacts; it does not claim a new CPU replay
run. Receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/retained-replay-independent-audit.json`.
Six retained publication/I/O/base audits and the retained prepared heartbeat
audit pass. Three new exact-binary CPU capability/owner denials create no image;
these are not CPU-image parser tests.

Both exact-recipe 16-GiB four-hart VCS controls pass at **C=3,329,794**.
Every complete hart trace and decoded workload/store label matches the
uninterrupted reference. These are full CPU controls, not Level-1 restores.
Selected summary, native binary and build identity are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/rocket/invocation-_89nzq0u/`.
The workload ELF SHA-256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Complete source/workload hashes are in
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/change-and-workload-hashes.json`.
Original native receipts bind their frozen source snapshots and exact executed
commands. Every VCS subprocess sources both environments and `vcs-env.sh` last,
using Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`.

All **nine** final independent evidence audits pass, including prepared and
legacy blockdev, driver/native suite, Rocket controls, current ownership and
capability denials, and prepared/legacy heartbeat. Repeating the full final
suite also passes. Eight rehashed offline forged receipts reject. The maintained
integration audit now takes an explicit `--rocket-summary`; repeated selection
succeeds with sibling build directories present. This fixes the previous
verification failure caused by requiring exactly one build directory. The
final audit driver also binds each original receipt explicitly. Its blockdev
source guard requires current C++/header bytes to equal the executed build.
Checker-only native-completion/path corrections were made after the frozen
native runs; archived sources and all raw execution artifacts remain intact.
Final Python checks pass all 280 tests after those corrections.

Independent byte/MMIO receipts:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/blockdev-independent-audit-verified.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/blockdev-legacy-independent-audit.json`.
Final results and offline controls:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/final-audit-results.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/blockdev-offline-negative-audit.json`.
Full artifact catalog and executable argv arrays:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/artifact-manifest.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/verification-commands.json`.
Preserve `/tmp` compiler-IR storage and original-path links listed in
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration175/cold-artifact-storage.json`.
No tests were reduced, and no FPGA build or ASIC power work was performed.

Executable native checks from the Chipyard root:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_blockdev_checkpoint_vcs --prepared --rocket-header automations/checkpoint_loop/runs/m11-iteration87/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h --out automations/checkpoint_loop/runs/m11-iteration175/blockdev-prepared'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration175/run-native.py'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_firesim_driver_checkpoint_vcs --prepared --out automations/checkpoint_loop/runs/m11-iteration175/driver-regression'
python -m tools.checkpoint_formats.tests.audit_blockdev_publication automations/checkpoint_loop/runs/m11-iteration175/blockdev-prepared/native-33p9_drw/summary.json
python automations/checkpoint_loop/runs/m11-iteration175/final-audits.py --selected automations/checkpoint_loop/runs/m11-iteration175/selected-results.json
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build automations/checkpoint_loop/runs/m11-iteration174/rocket/invocation-f4dx6u0b/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out automations/checkpoint_loop/runs/m11-iteration175/rocket'
```

Prepared UART, FASED and all four TracerV owners and the production coordinator
remain pending. Full generated/harness, memory, runtime I/O and creator-side TSI
ownership plus process exclusion must be joined before enabling CPU admission.
The generic aggregate still uses sequential legacy publication. BOOM/Saturn
remain pending. No external dependency is missing; no plan correction is proposed.

## Iteration 174: prepared heartbeat publication

Complete Rocket Level 1 remains **in_progress**, with CPU admission disabled.
The buffered, unfinished `firesim.widget.heartbeat.v1` owner now prepares the
complete source history and full destination stamp, then seals lifetime,
native-thread, generation, consumption and complete-byte checks before
allocation-free `noexcept` publication. Publication swaps the sample vector and
assigns four scalars. It performs no tick/time/localtime/MMIO/output/edge.
Legacy load invalidates candidates, including identical-byte loads. The v1
payload is unchanged; the fresh destination retains its diagnostic output path.
Live-log, finished, suspended and poisoned lifecycles remain unsupported.
Ownership and remaining integration: [heartbeat-sealed-publication.md](heartbeat-sealed-publication.md).

Native ASan/UBSan and fresh VCS pass **96** prepared continuations at all sixteen
component cuts in three polling scenarios, **96** complete pre-edge readbacks,
and **1,260** continued MMIO calls against the independent byte/MMIO/CSV oracle.
The matrix includes ignored/zero-interval polling, sticky timeout, repeated and
64-bit cycle counts, and negative elapsed-time samples. Both backends pass
**904** candidate rejections, **102** preparation and **66** sealing allocation
failures, **twelve** fatal contract cases, **two** unexpected-return controls,
**eight** malformed fresh loads and **two** actual first-divergence polling
corruptions at fixture cycle **107**. These are component cuts and images,
not Rocket `.fsckpt` acceptance or target-cycle labels. Eight rehashed offline
forged-receipt controls reject; they are evidence-auditor checks, not CPU runs.

Selected receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/heartbeat-prepared/native-yun3bzvd/summary.json`.
Independent full-byte/MMIO/original-command audit:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/heartbeat-independent-audit.json`.
Offline adversarial auditor receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/heartbeat-offline-negative-audit.json`.
Executable native/VCS checks from the Chipyard root (fresh paths per invocation):

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_heartbeat_checkpoint_vcs --prepared --rocket-header automations/checkpoint_loop/runs/m11-iteration87/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h --out automations/checkpoint_loop/runs/m11-iteration174/heartbeat-prepared'
python automations/checkpoint_loop/runs/m11-iteration174/audit-heartbeat-independent.py automations/checkpoint_loop/runs/m11-iteration174/heartbeat-prepared/native-yun3bzvd/summary.json
```

The prepared concrete-driver regression passes **224** fresh native/VCS
continuations with the current heartbeat implementation. All **eight** preserved
native scopes pass, including **280** Python tests plus semantic/banked, widget,
FCFS, UART, blockdev and heartbeat checks. The preserved legacy heartbeat matrix
independently passes **96** continuations, complete pre-edge readbacks,
**1,260** MMIO calls, **eight** malformed fresh loads and **two** first-boundary
polling corruptions. Six unchanged publication/I/O/base evidence audits pass.
Original native receipts:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/driver-regression/invocation-i2hecxq3/summary.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/native-regressions/invocation-j8xhqpnf/summary.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/heartbeat-legacy-independent-audit.json`.
Further executable checks:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_firesim_driver_checkpoint_vcs --prepared --out automations/checkpoint_loop/runs/m11-iteration174/driver-regression'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration174/run-native.py'
```

The retained independent Rocket Level-2 audit passes all four original cuts at
**C=100 / 700,000 / 900,000 / 3,250,000**, with **318,637** pre-edge semantic words
per cut, **256** captured events, **sixteen** real first divergences and **44**
invalid cases. This iteration re-audits retained ordinary RTL VCS artifacts;
it does not claim a new Rocket replay simulation. Receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/retained-replay-independent-audit.json`.

The exact-recipe structural and native-link audits retain **15** host widgets,
**11,464** generated entries / **445,838** words, and all three CPU admission
guards. Heartbeat's prepare/seal/publish symbols are linked in the actual
exact-recipe binary. Three fresh native capability/owner denials create no
CPU image; they do not establish CPU-image parser acceptance. Receipts:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/cpu-integration-audit.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/linked-driver-api-audit.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/cpu-denial-independent-audit.json`.

Both new exact-recipe **16-GiB** four-hart controls pass at **C=3,329,794**.
Every complete hart instruction trace and decoded workload/store label matches
the uninterrupted reference. The executed `rocket-quad.riscv` SHA-256 is
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These are uninterrupted CPU controls with the current linked heartbeat adapter,
not Level-1 restores. Selected receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/rocket/invocation-qg7mpk66/summary.json`.
The independent audit binds exact recipe/build/source hashes, every native
translation unit and provider, complete generated ownership, actual workload
bytes and all four complete traces. Executable native control from Chipyard root:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build automations/checkpoint_loop/runs/m11-iteration173/rocket/invocation-vetn068e/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out automations/checkpoint_loop/runs/m11-iteration174/rocket'
```

The selected results, workload/source hashes, full original native argv records,
source archives and executable verification commands are respectively:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/selected-results.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/workloads.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/raw-native-commands.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/native-input-archives.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/verification-commands.json`.
Final independent audit results and full-path artifact catalog:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/final-audit-results.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/artifact-manifest.json`.

All VCS shells source both repository environments and vcs-env.sh last, using
Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`.
Workspace capacity required relocating **68** inactive compiler-IR files
(**2,971,569,360 bytes**) from retained diagnostic builds to `/tmp`, with
identical verified bytes and links at original paths. Preserve the full storage
paths/hashes in `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration174/cold-artifact-storage.json`.
Logs, images and traces remain under `runs/`; no test was reduced or cancelled.
Existing controller-created FireSim and Chipyard heads reached both forks in
that order, with matching remote tips despite local tracking-ref write warnings.
No staging or local commit occurred; both plans and environment inputs retain
their initial bytes. No external dependency is missing.

Blockdev, UART, FASED and all four TracerV owners still require prepared
publication. Full generated RTL/FAME/channel/harness state, memory, runtime I/O,
scheduler/loop and creator-side TSI need one production coordinator with
thread/signal/descriptor/parser exclusion. Generic aggregate loading remains
sequential legacy publication. Complete Rocket Level-1 continuation is pending;
independent Level 2 stays separate. BOOM/Saturn are pending. Standalone Shuttle,
physical FPGA validation and ASIC power remain outside scope.

## Iteration 173: prepared base lifecycle publication

Complete Rocket Level 1 remains **in_progress**, with CPU admission disabled.
The distinct `runtime/simulation/base` owner now prepares/seals its complete
v1 source image against a separately stamped fresh destination and publishes
only decoded lifecycle scalars through allocation-free `noexcept` code.
All configuration/registry and lifecycle/performance fields are stamped;
lifetime/thread/generation/consumption guards run before owner access. Legacy
load invalidates candidates. Publication performs no init, reset, timestamp,
MMIO, output or concrete-driver operation. Ownership and exclusions:
[base-lifecycle-publication.md](base-lifecycle-publication.md).

Native ASan/UBSan and fresh VCS pass **24** prepared and **24** legacy
continuations through all four returned steps for success/error/timeout.
Each matrix reads back every base payload byte before the first fixture edge
and matches **264** MMIO calls against the independent Python oracle. The
prepared matrix additionally passes **1,216** invalid-candidate rejections,
**64** preparation and **32** sealing allocation failures, **twelve** fatal
contract cases and **two** explicit unexpected-return controls. Eight malformed
fresh loads reject before publication/edges/output. Four actual valid `run_done`
corruptions first diverge at fixture steps 4/5 before any divergent MMIO or
operation is acknowledged. These are base lifecycle component cuts and images,
not Rocket target cycles or CPU parser acceptance. Eight explicitly offline
rehashed forged-receipt controls reject changed readback/transcript/counts,
fatal/return/divergence acknowledgment, build claims and raw command metadata.

Selected prepared and legacy receipts:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/base-prepared/invocation-8xtddnom/summary.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/base-legacy/invocation-nimpsq97/summary.json`.
Independent full-byte/MMIO/original-command audits:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/base-independent-audit.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/base-legacy-independent-audit.json`.
Offline adversarial auditor receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/base-offline-negative-audit.json`.
Executable checks from the Chipyard root (fresh paths per invocation):

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_base_publication_vcs --out automations/checkpoint_loop/runs/m11-iteration173/base-prepared'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_base_publication_vcs --legacy --out automations/checkpoint_loop/runs/m11-iteration173/base-legacy'
python automations/checkpoint_loop/runs/m11-iteration173/audit-base-independent.py automations/checkpoint_loop/runs/m11-iteration173/base-prepared/invocation-8xtddnom/summary.json
```

All **224** fresh prepared concrete-driver continuations and all eight preserved
native scopes pass; the latter includes **280** Python tests and semantic/banked,
widget, FCFS, UART, blockdev and heartbeat native checks. The independent original
Level-2 evidence audit retains **C=100 / 700,000 / 900,000 / 3,250,000**, **318,637**
pre-edge words per cut, **256** captured events, **sixteen** real first divergences
and **44** invalid cases. This is a re-audit of retained ordinary RTL VCS runs;
this iteration does not claim another Rocket replay simulation. Receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/retained-replay-independent-audit.json`.

Both new exact-recipe **16-GiB** four-hart direct-exit controls pass at
**C=3,329,794**. Every complete hart instruction trace and decoded workload/store
label matches the uninterrupted reference. These controls run the current linked
base adapter but are not Level-1 restores. Selected receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/rocket/invocation-vetn068e/summary.json`.
The independent exact-recipe audit verifies build/source hashes, actual native
link inputs, full generated ownership, workload bytes and complete four-hart
traces. The new base API's prepare/seal/publish symbols are present in that binary.

The base prepared and legacy receipts include every original native/VCS argv,
source snapshot and complete readback/transcript. All VCS shells source both
environments and `vcs-env.sh` last, with Y-2026.03-SP1, `-full64` and system GCC/G++
13. The reused exact-recipe build uses `VCS_FLAGS=-Mupdate`. Exact further checks:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_firesim_driver_checkpoint_vcs --prepared --out automations/checkpoint_loop/runs/m11-iteration173/driver-regression'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration173/run-native.py'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build automations/checkpoint_loop/runs/m11-iteration172/rocket/invocation-qq3b_tns/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out automations/checkpoint_loop/runs/m11-iteration173/rocket'
```

Current native driver and eight-scope receipts:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/driver-regression/invocation-vgnzf_76/summary.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/native-regressions/invocation-flll8xd8/summary.json`.
The selected results, full workload/source/recipe bindings and executable argv
arrays are `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/selected-results.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/workloads.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/native-input-archives.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/verification-commands.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/raw-native-commands.json`.
Current ownership/link receipts are `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/cpu-integration-audit.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/linked-driver-api-audit.json`.
The final independent current-source audit results are
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/final-audit-results.json`; the complete full-path catalog is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/artifact-manifest.json`.

The exact-recipe source census and native symbol audit retain **15** widgets,
**11,464** generated entries / **445,838** words, both lifecycle adapters and all
three CPU admission guards. Three fresh native capability/owner denials create
no CPU image; they do not establish malformed CPU-image parser support.
Five unchanged publication/I/O evidence audits pass. Complete base/driver/CPU
source bytes, command lines and receipts are preserved under `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173`.

Workspace capacity required moving 44 cold compiler-IR files from this new
invocation to byte-verified `/tmp` storage with links at their original paths;
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration173/cold-artifact-storage.json` lists every full storage path/hash.
Workspace capacity recovered during the controls; all 44 intermediates were
reinstated as regular files at their original paths with identical hashes.
`restore-cold-storage.json` records that check. Diagnostic logs, images and
traces stay under `runs/`. No test scope was reduced.
Existing controller-created commits were published FireSim first, then Chipyard;
no staging/local commit occurred. Plan/environment inputs remain unchanged.
No external dependency is missing.

Heartbeat, blockdev, UART, FASED and four TracerV owners still need prepared
publication. Full generated RTL/FAME/channel/harness state, memory, runtime I/O,
scheduler/loop and creator-side TSI must join one production coordinator under
process thread/signal/descriptor/parser exclusion. Generic aggregate loading
still calls legacy owners sequentially. Complete Rocket Level-1 continuation is
pending. Independent Level 2 remains separate; BOOM/Saturn remain pending.
Standalone Shuttle, physical FPGA validation and ASIC power remain outside scope.

## Iteration 172: prepared concrete-driver lifecycle publication

Complete Rocket Level 1 remains **in_progress** with CPU admission disabled.
`firesim_top_t::concrete_checkpoint_t` now explicitly prepares a running v1
source image for a strictly fresh destination. A separate destination stamp
checks idle/non-poisoned calls, `started == false`, `finalized == false`, profile
configuration, peek/poke identity/schema and every ordered bridge identity/schema.
Source capture still requires an unfinished running driver. The candidate retains
its own destination bytes and no caller-owned payload. Sealing checks lifetime,
native thread, generation, consumption and all destination bytes before mutation.
Publication is allocation-free `noexcept` and assigns only `started = true`.
Legacy loads invalidate candidates before that assignment. No init, reset, target
edge, MMIO, scheduler callback, bridge tick, finalization or output is performed.
The driver remains noncopyable/nonmovable. The coordinator must retain exclusion
from sealing through aggregate readback; this adapter acquires no process lock.

The maintained driver matrix has an explicit `--prepared` mode and retains
legacy loading. Both compile actual production driver/scheduler/bridge-loop code
with separate deterministic MMIO, bridge and heartbeat-clock fixtures. Only the
concrete driver uses the new adapter in the prepared fixture loader. This is not
an all-owner transaction; component service cursors and fixture cycle labels are
not Rocket target cycles or complete CPU checkpoints.

Final native ASan/UBSan and fresh VCS checks pass **224** component
continuations across all 112 returned-service cuts, **2,464** complete
owner readbacks before any service and **4,846** continued boundaries.
Six scenarios cover each of four bridge termination positions, signed statuses,
timeout and an already-finished loop. An independent Python oracle encodes every
owner byte and the original nested-loop call transcript. The legacy matrix also
passes all 224 fresh continuations.

Prepared publication passes **1,490** invalid-candidate rejections,
**82** preparation and **40** sealing allocation-failure points,
and **12** fatal contract cases. Cases include every source truncation and
configuration-byte mutation, all flag bits, trailing bytes, wrong owners/profile/
registry geometry, changed/started/finalized/poisoned destinations, cancellation,
repeated sealing, expiration, thread affinity, consumed/stale/legacy-load-stale
candidates and source-buffer independence. Publication runs with the next C++
allocation armed to fail. Every injected preparation/sealing allocation failure
preserves complete fixture state and permits a fresh retry without MMIO. Sixteen incomplete/invalid
fixture inventories reject before initial readback or trace creation. Two actual
valid cursor corruptions fail at fixture C=106 before acknowledging the divergent
MMIO response (`expected=R 200 0`, `actual=R 208 0`). These are fixture parser and
execution faults, not CPU image-parser acceptance.

Review found a weakness in the initial fatal-test fallback. An unexpected return
now exits 88 directly, bypassing the successful terminate handler. Both native
and VCS deliberately execute that return path and require exit 88. Both complete
driver matrices and the full eight-scope native suite were repeated with final
fixture bytes. Final selected driver receipts supersede preliminary driver runs.
Seven explicitly offline forged-receipt controls reject modified readback bytes,
service labels, invalid counts, acknowledged fatal misuse, acknowledged divergent
MMIO, a substituted legacy-build claim and an acknowledged unexpected return,
after recomputing artifact hashes. They test the auditor, not additional CPU runs.

Selected native/VCS driver receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/driver-final/invocation-rd6me6o5/summary.json`.
Independent full-byte/MMIO oracle:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/driver-final-independent-audit.json`.
Adversarial oracle receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/driver-final-oracle-negative-audit.json`.
Executable commands from the Chipyard root (each verifier allocates new paths):

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_firesim_driver_checkpoint_vcs --prepared --out automations/checkpoint_loop/runs/m11-iteration172/driver-final'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_firesim_driver_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration172/driver-legacy-final'
python automations/checkpoint_loop/runs/m11-iteration172/audit-driver-publication.py --summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/driver-final/invocation-rd6me6o5/summary.json
python automations/checkpoint_loop/runs/m11-iteration172/audit-driver-final-oracle-negatives.py
```

All eight final preserved scopes pass 280 Python tests plus semantic/banked,
widget, FCFS, UART, block-device and heartbeat native checks. Stream/MMIO/
CPU-managed I/O and scalar/configuration/control publication regressions pass.
The final eight-scope receipt is `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/native-final/invocation-hyx1jrze/summary.json`.
Fourteen final independent audits pass. The current exact-recipe census and
symbol audit retain 15 host widgets, 11,464 generated entries / 445,838 words,
the driver's prepared/seal/publish methods and all three CPU admission guards.
Three fresh native exact-recipe capability/owner denials create no CPU image;
they are not malformed CPU-image parser tests.

Fresh ordinary pre-FAME RTL VCS independently replays all four retained Rocket
cuts, **C=100 / 700,000 / 900,000 / 3,250,000**, reading every one of **318,637**
semantic words before any edge per cut. All **256** captured events and **21,760**
output comparisons match, with **sixteen** actual first divergences and **44**
invalid-image cases. The full-source independent audit binds the original capture
log and complete replay sources. Selected replay receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/regressions/native-replay/invocation-uy0e94is/summary.json`.
Independent audit: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/replay-full-source-independent-audit.json`.

Both exact-recipe 16-GiB four-hart direct-exit controls pass at **C=3,329,794**;
every full hart trace and decoded workload/store label matches the uninterrupted
reference. These are full CPU controls, not Level-1 continuations. Selected receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/rocket/invocation-yir8lv5x/summary.json`.
The production binary's 60 translation units remain unchanged by the later
fixture-only correction; its original pre-build source snapshots are retained.
The workload ELF is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Complete workload/source bindings are `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/workloads.json`.
Recipe settings are the exact YAML values above; native VCS uses Y-2026.03-SP1,
`-full64`, `VCS_FLAGS=-Mupdate`, system GCC/G++ 13 and `vcs-env.sh` sourced last.
No FPGA bitstream is built.

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration172/run-native-final.py'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out automations/checkpoint_loop/runs/m11-iteration172/regressions/native-replay'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build automations/checkpoint_loop/runs/m11-iteration171/verified/rocket/invocation-4cpr4qqv/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out automations/checkpoint_loop/runs/m11-iteration172/rocket'
```

All selected receipts, exact native compiler/runtime argv arrays, workload/source
hashes, archived inputs, diagnostic paths and full-path artifact catalog are:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/selected-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/verification-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/raw-native-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/native-input-archives.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/final-audit-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/artifact-manifest.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration172/remaining-owner-audit.json`.

Existing controller heads were pushed FireSim first and then Chipyard, with
independently verified remote tips despite local tracking-reference write
warnings. The controller still owns staging/local commits. Plans, environment
helpers, heads and indices retain their starting bytes; cached diffs are empty.
No test was cancelled or reduced; no external dependency is missing.

The separate `simulation_t::base_checkpoint_t` is another lifecycle owner and
still lacks prepared publication. Remaining widgets are heartbeat, blockdev,
UART, FASED and four TracerV owners. Complete generated state, harness, memory,
runtime I/O, scheduler/loop and creator-side TSI coordination plus process
exclusion remain required. Generic aggregate restoration still uses sequential
legacy loads. No complete CPU image-parser rejection or fresh Rocket Level-1
continuation is claimed. Independent Rocket Level 2 remains separate; BOOM and
Saturn remain pending. Standalone Shuttle, FPGA validation and ASIC power remain
outside this task.

## Iteration 171: prepared mutable scalar host publication

Production `CPUManagedStreamWidget` and `peek_poke_t` now explicitly prepare,
seal and publish their initialized/unstable/timeout host flags. The entire source
configuration and complete destination bytes validate before publication;
source and destination flags may differ. Publication is allocation-free
`noexcept`, assigning only decoded scalars without init, MMIO, DMA or stepping.
Lifetime/thread/generation/consumption guards precede owner access and assignments.
Identical-byte legacy loads invalidate candidates. Both concrete owners are
final and noncopyable/nonmovable. Suspended/interrupted calls still reject.
Ownership and exclusions: [scalar-sealed-publication.md](scalar-sealed-publication.md).

Final-source native ASan/UBSan and time-zero VCS DPI pass **40** fresh component
restores, **244** complete owner comparisons and **418** returned service
boundaries. Twenty cuts span stream initialization, full/empty and data-bearing
transfers, flushes, scalar/GMP peeks and pokes, step/done and both timeout paths.
Every restored payload is read back before the first service operation. An
independent Python oracle compares every payload byte and complete MMIO/DMA
request/response/data transcript. These are host components with deterministic
MMIO/DMA/clock fixtures; cuts are service cursors, not Rocket target-cycle cuts.
They do not establish complete CPU Level-1 support.

The matrix also passes **34,440** invalid rejections, **920** exhaustive paired
preparation allocation failures, **440** exhaustive paired sealing allocation
failures and **24** fatal contract checks. It exercises all reserved flag bits,
every truncation/configuration-byte mutation, foreign owners, changed destinations,
suspended/poisoned calls, cancellation, consumed/stale/expired/thread guards and
all eight legal flag combinations from differing destination scalars. The next
C++ allocation is armed to fail during valid publication. Five explicitly offline
forged-receipt controls reject altered initial/final bytes, a service label, a
rejection count and an acknowledged fatal misuse after recomputing artifact hashes.
Those controls test the auditor; they are not additional native CPU fault cases.

Selected receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/scalar-verified/invocation-ziqgcxqh/summary.json`.
Independent audit and adversarial receipts:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/scalar-verified/invocation-ziqgcxqh/independent-audit.json`
and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/scalar-oracle-negative-audit.json`.
Executable native/VCS checks from the Chipyard root:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_scalar_publication_vcs --out automations/checkpoint_loop/runs/m11-iteration171/scalar-verified'
python -m tools.checkpoint_formats.tests.audit_scalar_publication --summary automations/checkpoint_loop/runs/m11-iteration171/scalar-verified/invocation-ziqgcxqh/summary.json
python automations/checkpoint_loop/runs/m11-iteration171/audit-scalar-oracle-negatives.py
```

The receipt retains exact native/VCS compiler and runtime argv, source snapshots,
complete readbacks and transcripts, and hashes of diagnostic artifacts. VCS uses
Y-2026.03-SP1, `-full64`, system GCC/G++ 13 and `vcs-env.sh` sourced last.
The first diagnostic compile missed a fixture header; a later diagnostic run
correctly rejected source drift while the reserved-bit tests were expanded.
Neither is selected as passing evidence.

The final-source eight-scope native repeat passes **280** Python tests and the
preserved semantic, banked, widget, FCFS, UART, block-device and heartbeat native
checks. Stream, MMIO, CPU-managed I/O and configuration publication regressions
also pass. The earlier native envelope completed every check but then rejected
source drift in the new tests; the selected repeat has stable source bindings.
Fresh ordinary RTL VCS and a complete-source independent audit pass all four
retained Rocket cuts at C=100 / 700,000 / 900,000 / 3,250,000: **318,637** words
read back per cut before any edge, **256** captured events, **16** actual first
semantic divergences and **44** invalid cases. This replay remains independent
of Level 1. Receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/verified/native-confirmed/invocation-q8mph5lg/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/regressions/native-replay/invocation-s35wxbbl/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/replay-early-independent-audit.json`.

Executable preserved-suite and ordinary RTL checks:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration171/repeat-native-confirmed.py'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out automations/checkpoint_loop/runs/m11-iteration171/regressions/native-replay'
```

Both rebuilt exact-recipe **16-GiB four-hart direct-exit controls** pass at
target count **3,329,794**. Every complete hart trace and decoded workload label
matches the uninterrupted reference in ordinary and buffered output modes. These
are uninterrupted controls, not fresh Level-1 continuations. The selected receipt
is `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/verified/rocket/invocation-4cpr4qqv/summary.json`.
The actual workload is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
**6712 bytes**, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Exact executable metasim command from the Chipyard root:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build automations/checkpoint_loop/runs/m11-iteration170/verified/rocket/invocation-ziek3ho8/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out automations/checkpoint_loop/runs/m11-iteration171/verified/rocket'
```

The preserved scheduler/bridge-loop publication matrix also passes with complete
fresh component readback, invalid/lifetime/thread/generation guards, exhaustive
allocation failures and fatal misuse checks; the receipt is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/control-final/invocation-0o8rhmr0/summary.json`.

All **twelve** final independent audits pass. The source-bound census and linked
symbol audit retain **15** host widgets, **11,464** generated entries / **445,838**
words, both new scalar adapters, existing prepared adapters and all three CPU
admission guards. Three fresh native capability/owner denials and their
independent audit create no CPU image. These are capability denials, not malformed
CPU-image parser tests. Existing controller commits reached both GitHub forks,
FireSim first; remote tips independently match despite local tracking-reference
write warnings. Plans, environment helpers, heads and the root index retain
starting bytes; both cached diffs remain empty. No staging/local commit, test
cancellation or scope reduction occurred. No external dependency is missing.

Final selected receipts, workload/source bindings, exact native commands and
full-path artifact catalog:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/selected-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/workloads.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/native-input-archives.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/verification-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/raw-native-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/final-audit-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration171/artifact-manifest.json`.

Complete CPU admission remains disabled. The next smallest owner is the concrete
FireSim driver's strictly fresh lifecycle. Blockdev, UART, FASED, four TracerV
owners and heartbeat also need prepared publication before joining all owners
with generated RTL/FAME/channels/harness, memory, runtime I/O, scheduler/loop and
creator-side TSI under production process exclusion. The generic aggregate still
loads legacy owners sequentially. Complete Rocket Level-1 continuations at the
four active-workload cuts remain pending. Level 2 stays independent; BOOM and
Saturn remain pending. Physical FPGA validation and ASIC power remain deferred.

## Iteration 170: prepared configuration-only widget publication

Production `master_t`, `clockmodule_t`, `loadmem_t` and `reset_pulse_t` now
explicitly implement prepared publication. Complete payload validation requires
identical immutable configuration in the destination. Sealing checks complete
destination bytes plus lifetime/native-thread/generation/consumption guards;
publication is allocation-free `noexcept`, with no MMIO, target edge or host
state assignment. Identical-byte legacy loads invalidate candidates. These four
owners are noncopyable/nonmovable. Suspended/interrupted calls still reject.
Mutable peek/poke flags remain unsupported by this adapter. Ownership details:
[configuration-sealed-publication.md](configuration-sealed-publication.md).

The final-source native ASan/UBSan and time-zero VCS DPI matrix passes **24**
fresh component restores, **296** complete owner comparisons and **154** returned
service boundaries over twelve cuts across eleven MMIO-bearing operations.
Every restored payload is read back before the first service operation; all
MMIO requests/responses, latched clock values and GMP results match an independent
Python oracle. This is a host-component test with fixture MMIO; the cuts are
service cursors, not Rocket target-cycle labels or complete CPU checkpoints.

The same matrix passes **22,248** invalid rejections, **1,704** exhaustive paired
preparation allocation failures, **768** exhaustive paired sealing allocation
failures and **48** fatal contract checks. Cancellation before/after sealing
leaves all host payloads and MMIO untouched. Valid publication runs with the next
C++ allocation armed to fail. Expired, unsealed, consumed, stale, legacy-load-stale
and wrong-thread candidates reject or terminate without publication acknowledgment.
Five explicitly offline forged-receipt controls reject altered initial/final
bytes, a service cursor, a rejection count and a fatal acknowledgment after all
artifact hashes are recomputed. Those are auditor tests, not native CPU corruption
injections or additional execution.

Selected receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/configuration-final/invocation-4k90qdxr/summary.json`.
Executable native/VCS checks, from the Chipyard root:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_configuration_publication_vcs --out automations/checkpoint_loop/runs/m11-iteration170/configuration-final'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.audit_configuration_publication --summary automations/checkpoint_loop/runs/m11-iteration170/configuration-final/invocation-4k90qdxr/summary.json'
python automations/checkpoint_loop/runs/m11-iteration170/audit-configuration-oracle-negatives.py
```

The receipt binds exact native/VCS compiler/runtime argv, source snapshots,
complete host payload bytes, every service transcript and diagnostic artifact
hashes. VCS uses Y-2026.03-SP1, `-full64`, system GCC/G++ 13 and `vcs-env.sh`
sourced last; the reused exact-recipe Make build uses `VCS_FLAGS=-Mupdate`.

All **15** broader checks and **12** independent audits pass. The eight
preserved native scopes retain **280** Python tests plus semantic/banked, FCFS,
widget, UART, block-device and heartbeat native VCS checks. Creator/harness,
dispatcher, stream/DMA, MMIO, runtime I/O, memory, scheduler/bridge-loop and the
production TSI matrix pass. Thirty retained auditors and thirteen retained
I/O/memory receipts pass. The initial retained wrapper incorrectly selected the
DMA auditor for a memory receipt; corrected dispatch reruns all thirteen receipts
successfully. Both the diagnostic and recovery logs remain under this iteration.
The additional TSI audit confirms 336 unpublished invalid cases and 128
unpublished prepared/sealed cancellations; all 32 dispatcher diagnostics pass.

Fresh ordinary RTL VCS and the independent full-source audit pass all four
retained Rocket windows at C=100 / 700,000 / 900,000 / 3,250,000. Each reads back
all **318,637** semantic words before any edge; **256** captured events match,
**sixteen** actual semantic corruptions diverge at their first expected boundary,
and **44** invalid cases reject. These remain independent of Level 1.
Both exact-recipe **16-GiB four-hart direct-exit controls** pass at C=3,329,794.
All four ordinary/restricted and buffered/unbuffered syscall controls pass at
C=3,330,050. Complete hart traces and decoded workload labels match within each
protocol. These CPU controls are uninterrupted runs, not Level-1 restores.

The rebuilt exact-recipe binary contains all four new widget adapters and their
shared sealing/publication methods. The source-bound census retains **15** host
widgets, **11,464** generated entries / **445,838** words, and all three CPU
admission guards. Three fresh capability/owner denials and their independent
audit publish no CPU image; these are not malformed CPU-image parser tests.
Both existing controller heads reached GitHub, FireSim first, with independent
remote-tip confirmation despite local tracking-reference write warnings.
Plans, environment helpers, heads and indices retain their starting bytes.
No staging or local commit occurred. No external dependency is missing, and no
test was cancelled or reduced.

Current selected native receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/verified/rocket/invocation-ziek3ho8/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/verified/syscall/invocation-wzqj5t_a/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/regressions/native-replay/invocation-fnpd4kf2/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/verified/native-final/invocation-viol5h9v/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/control-final/invocation-pid40hwt/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/memory-final/invocation-pw53in7d/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/runtime-io-final/invocation-cuhbuer2/summary.json`.

Exact tested workload bytes (the full source and build bindings are in the
selected CPU/replay receipts and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/native-input-archives.json`):

| Workload | Bytes | SHA-256 |
| --- | --- | --- |
| `corrupt-hart-0.riscv` | 6712 | `4e15444e6f03e203ebd397a99be42c690f1603469e927703e86aed4f5012806b` |
| `corrupt-hart-1.riscv` | 6712 | `41056032c70d68e1634138e8d4e1578bb4efa3a8cf527dade0d58f0b9b54c5cf` |
| `corrupt-hart-2.riscv` | 6712 | `64c563fceb12fa367a3e9fe2c78eeb279cdc4f8778a8cbd7955ae19c15b403fa` |
| `corrupt-hart-3.riscv` | 6712 | `6e2e7e29699c904d0273e2c5ff20e712e8f69e97de98fdb8bad6dbd7403312f4` |
| `rocket-quad.riscv` | 6712 | `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4` |
| `corrupt-hart-0.riscv` | 6824 | `62fc8bc289c8aedb17ea7254fc1a07e0514b08ad3cd5fea0bf818699f9952ff4` |
| `corrupt-hart-1.riscv` | 6824 | `c201413fdaa394aa6a1b8a0dc6b362054de8a7948225fae0ce7d4276e6607f4c` |
| `corrupt-hart-2.riscv` | 6824 | `8f409ff6bf6e0366629c8fc54006d03d8c33e950d8cbbd3639327f10b5e89093` |
| `corrupt-hart-3.riscv` | 6824 | `2e7216e8dd80f1bae7a2999c80590ead25071518693f54199631934af0e8b432` |
| `rocket-quad.riscv` | 6760 | `1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958` |

Executable current native CPU/replay checks, from the Chipyard root:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/regressions/native-replay'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build automations/checkpoint_loop/runs/m11-iteration168/verified/rocket/invocation-ta72y7es/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/verified/rocket'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_syscall_vcs --build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/verified/rocket/invocation-ziek3ho8/rocket-build-identity.json --workload automations/checkpoint_loop/runs/m11-iteration151/workload --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/verified/syscall'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration170/repeat-native-final.py'
```

Complete actual argv arrays, selected receipt hashes and the full-path artifact
index are `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/verification-commands.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/raw-native-commands.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/selected-results.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/workloads.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/native-input-archives.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration170/artifact-manifest.json`.

Complete Rocket Level 1 remains disabled. Remaining prepared-publication owners
include CPU-managed stream control, peek/poke, block device, UART, FASED, four
TracerV instances, heartbeat and the concrete driver. Complete generated
RTL/FAME/channel/harness, runtime I/O, functional-memory and creator-side TSI
publication must be joined with all host owners under production
controller/creator/thread/signal/descriptor/parser exclusion. The aggregate still
loads legacy owners sequentially. No complete CPU image parser, fresh Rocket
Level-1 continuation or whole-simulator atomic transaction is claimed by this
component result. Independent Level 2 remains separate.

## Iteration 169: prepared scheduler and bridge-loop publication

The production `systematic_scheduler_t` and `bridge_run_loop_t` now implement
`checkpoint_owner_t::prepare_checkpoint_publication`. This generic interface
rejects unaudited owners by default, including owners with a legacy checkpoint
schema. Candidates own their decoded replacement storage; sealing completes all
throwing destination checks before allocation-free `noexcept` publication.
Lifetime, candidate-native-thread, seal/consumption and destination generation
guards reject invalid use. Identical-byte legacy loads invalidate candidates.
Full-byte destination comparison rejects changed, suspended or poisoned owners.
Both owners are noncopyable/nonmovable. Callback state remains separately owned;
scheduler cycles remain issued credits. Details:
[control-sealed-publication.md](control-sealed-publication.md).

The final-source native ASan/UBSan and time-zero VCS DPI matrix passes **48**
fresh component restores, **776** complete owner comparisons and **3,120**
returned-service boundaries. It covers both horizon completion and signed
bridge termination, with twelve cuts per path across phases, pending steps,
bridge indices and completion. Every restore reads back both complete owners
before its first service call. The independent Python deadline/phase oracle
checks every reference state, service cursor, event label and restored suffix.

The same matrix passes **12,336** invalid rejections, **1,776** exhaustive paired
preparation allocation failures, **1,296** exhaustive paired sealing allocation
failures and **288** fatal contract checks. Cancellation after preparation or
sealing changes neither owner. Valid sealed publication runs with the next C++
allocation armed to fail. Fatal expired/thread/unsealed/consumed/stale and
legacy-load-stale candidates terminate before that owner's first assignment.
These are synthetic returned-call services around two real host owners, not
Rocket instructions, target edges, a complete simulator transaction or a CPU
checkpoint image parser. CPU aggregate admission remains disabled.

Selected receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/control-final/invocation-92_ldc4m/summary.json`.
Executable native/VCS checks, from the Chipyard root:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_control_publication_vcs --out automations/checkpoint_loop/runs/m11-iteration169/control-final'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.audit_control_publication --summary automations/checkpoint_loop/runs/m11-iteration169/control-final/invocation-92_ldc4m/summary.json'
```

Five explicitly offline forged-receipt controls also pass. After recomputing
their artifact hashes, the auditor still rejects altered initial/final state,
a changed service label, an incorrect rejection count and a fatal case that
claims successful return. These copies are auditor tests, not additional native
execution or CPU corruption evidence. Their receipt is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/control-oracle-negative-audit.json`.

Each invocation retains exact compiler/runtime argv arrays, source snapshots,
zero-time VCS receipts, all state bytes/events and artifact hashes. VCS uses
Y-2026.03-SP1, `-full64` and GCC/G++ 13, with `vcs-env.sh` sourced last.

All fourteen broader checks and eleven independent audits pass. The eight
preserved native scopes retain 280 Python tests plus semantic/banked, FCFS,
widget, UART, block-device and heartbeat VCS checks. Creator/harness, dispatcher,
stream, MMIO, DMA, runtime I/O, memory and production TSI pass; thirty retained
auditors and nine retained component receipts pass. Four fresh ordinary RTL
windows again read back all **318,637** words before any edge, replay **256**
events, detect **sixteen** real first semantic divergences and reject **44**
invalid cases at C=100 / 700,000 / 900,000 / 3,250,000. The independent full-source
audit passes. Both complete **16-GiB four-hart direct-exit controls** pass at
C=3,329,794; all four ordinary/restricted and buffered/unbuffered syscall
controls pass at C=3,330,050. Every hart trace and decoded workload label matches
within its protocol. These are uninterrupted CPU controls, not Level-1 restores.

The exact-recipe linked-symbol audit confirms both new prepared adapters in the
rebuilt native executable. The source census retains **15** host widgets,
**11,464** generated entries / **445,838** words and all three CPU admission
guards. Three fresh capability/owner denials and their independent audit create
no CPU checkpoint. These are not malformed CPU-image parser tests.

Current receipts:
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/verified/rocket/invocation-0e_y8cfb/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/verified/syscall/invocation-mjpjhsr7/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/regressions/native-replay/invocation-agxq4470/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/verified/native-final/invocation-1ijfgn33/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/memory-final/invocation-0cxu1rpn/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/runtime-io-final/invocation-c74xbppm/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/mmio-io/invocation-ss0wg3ra/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/cpu-io/invocation-oc3iu4vh/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/verified/creator/invocation-e4p1p_xt/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/regressions/bridge/invocation-szp2rkkg/summary.json`.

Final selected receipts, exact executable argv arrays, workload hashes, native
source snapshots and artifact paths are collected in:
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/selected-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/verification-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/raw-native-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/workloads.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/native-input-archives.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/artifact-manifest.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/cpu-integration-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/linked-control-api-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/cpu-denial-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/publication.json`.

Native CPU/replay regression commands, from the Chipyard root:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/regressions/native-replay'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build automations/checkpoint_loop/runs/m11-iteration168/verified/rocket/invocation-ta72y7es/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/verified/rocket'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_syscall_vcs --build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/verified/rocket/invocation-0e_y8cfb/rocket-build-identity.json --workload automations/checkpoint_loop/runs/m11-iteration151/workload --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration169/verified/syscall'
```

Both existing controller heads were published to GitHub, FireSim first then
Chipyard. Queried remote tips match despite local tracking-reference warnings.
Plans, environment helpers, heads and indices retain their starting bytes;
no staging, local commit, test cancellation or scope reduction occurred.
No external dependency is missing.

The remaining transaction must join these prepared controls, functional memory,
runtime I/O, creator-side TSI, all remaining widgets and concrete driver,
generated RTL and harness state under actual process exclusion. The existing
generic aggregate still loads legacy owners sequentially. Complete fresh Rocket
Level-1 workload continuation remains pending. Level 2 stays independent;
BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA validation and
ASIC power remain outside this task.

## Iteration 168: prepared/sealed functional-memory publication

Complete Rocket Level 1 remains **in_progress**. The production `mm_magic_t`
owner now prepares and seals its complete existing payload before allocation-free
`noexcept` publication. Publication preserves the backing mapping address and
all existing `get_data` aliases, swaps preallocated dummy/read/write response
storage, and restores the pending-write cursor and memory-model cycle counter.
The destination lifetime, native thread, seal, consumption and generation are
checked before copying. A successful legacy `load_checkpoint`, including an
identical-byte load, also invalidates older candidates. Copying/moving owners
is disabled; reinitializing a live mapping rejects before replacing it.
The payload schema remains `firesim.mm_magic.full.v1`. Recovery:
[functional-memory-sealed-publication.md](functional-memory-sealed-publication.md).

The final-source native ASan/UBSan and time-zero VCS DPI matrix passes **16**
fresh component restores, **200** complete owner comparisons, **420** AXI boundary
samples, **728** invalid/stale rejections and **112** fatal contract checks.
Exhaustive allocation injection passes **1,392** preparation and **760** sealing
failures without partial publication. Sealed publication performs **zero** C++
allocations with the next allocation armed to fail. Cancellation after partial
or complete sealing leaves every owner unchanged. Every resumed process reads
back all bytes before any edge and matches a separate byte/queue/strobe oracle
through the complete finite AXI continuation.

These are **4,096-byte component mappings**, with one bank matching the exact
Rocket `{id=16, addr=34, data=64}` geometry and an additional four-bank group.
The exact Rocket recipe has **one** functional-memory channel. Component cuts
cover pristine state, outstanding AW/read responses, partial strobed writes
and buffered B/last-R responses. These are not whole-CPU workload cuts or
full 16-GiB memory-transaction acceptance. No CPU profile is enabled.
The outer coordinator must still supply process exclusion and join memory,
runtime I/O, creator-side TSI, widgets/driver, generated RTL and harness state.
The generic aggregate still invokes allocating owner loads sequentially.

Final memory receipt and independent audit:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/memory-final/invocation-h3ent2gp/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/memory-independent-audit.log`.

Executable native ASan/UBSan and VCS DPI check from the Chipyard root; the runner
allocates a fresh invocation and records every native argv, PID and result:

```sh
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_memory_publication_vcs --rocket-header automations/checkpoint_loop/runs/m11-iteration165/verified/rocket/invocation-l8hh65kl/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h --out automations/checkpoint_loop/runs/m11-iteration168/memory-final'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.audit_memory_publication --summary automations/checkpoint_loop/runs/m11-iteration168/memory-final/invocation-h3ent2gp/summary.json'
```

Five explicitly offline adversarial auditor controls pass. They recompute the
artifact hashes after changing a restored byte, final byte, cycle label,
rejection count or fatal acknowledgment; the independent oracle rejects every
case. They are not additional native executions or CPU semantic-fault tests:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/memory-oracle-negative-audit.json`.

The source-bound census and linked-symbol audit pass **15** host widgets,
**11,464** generated entries / **445,838** words, all three CPU admission guards,
and the new memory plus existing I/O APIs in the current exact-recipe binary.
Three fresh native requests and an independent audit preserve unsupported
owner/capability denial without creating a CPU checkpoint. These are not CPU
image-parser rejection tests. Receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/cpu-integration-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/linked-memory-api-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/cpu-denial-verified/invocation-r2f3xzc1/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/cpu-denial-independent-audit.json`.

All **fourteen** final checks and **ten** independent audits pass. All eight
preserved native scopes retain **280** Python tests; creator/harness, dispatcher,
stream-widget, MMIO, CPU-managed DMA and production TSI matrices pass. Thirty
retained auditors and five retained I/O receipts pass. The actual final-source
runtime I/O matrix again passes 24 fresh component restores, 336 owner
comparisons, 510 invalid/stale cases, 5,092 exhaustive allocation failures and
72 fatal checks. MMIO retains 48 fresh restores / 480 owner comparisons;
DMA retains 84 fresh restores / 336 owner comparisons, including all suspended
boundary and invalid-image checks. Implementation/test sources stayed fixed
through the final suite. No check was cancelled, reduced or skipped.

The independent full-source ordinary RTL audit passes the original target-cycle
cuts **100 / 700,000 / 900,000 / 3,250,000**: **318,637** complete words read back
before any edge per cut, **256** captured events / **21,760** sampled output
comparisons, **16** actual first-boundary semantic divergences and **44** invalid
cases. Level 2 remains independent. Both exact-recipe **16-GiB** direct-exit
four-hart controls pass at **C=3,329,794**; all four ordinary/restricted and
buffered/unbuffered syscall variants pass at **C=3,330,050**. Complete hart traces
and decoded workload labels match within each protocol. The direct ELF is
**6,712 bytes**, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`;
the syscall ELF is **6,760 bytes**, SHA-256
`1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.
These workload runs do not exercise a complete Level-1 CPU restore.

Selected full receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/runtime-io-final/invocation-mmq0qhrt/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/mmio-io/invocation-stw_90e1/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/cpu-io/invocation-4_0lj74o/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/verified/rocket/invocation-ta72y7es/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/verified/syscall/invocation-nf6fucyv/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/regressions/native-replay/invocation-gvedhet5/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/verified/native-final/invocation-ik5eh19w/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/replay-full-source-independent-audit.json`.

Executable fresh ordinary RTL check from the Chipyard root:

```sh
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out automations/checkpoint_loop/runs/m11-iteration168/regressions/native-replay'
```

Complete native argv arrays, build settings, source snapshots, workload hashes,
selected results and every created artifact's full path are:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/verification-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/raw-native-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/native-input-archives.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/workloads.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/selected-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/artifact-manifest.json`.

The initial exploratory memory run overlapped final edits and failed its source
binding after its complete case matrix ran; its retained logs are diagnostic.
Only the fixed-source final memory receipt is selected. The offline auditor
controls are explicitly forged receipt copies; their argv arrays are excluded
from the list of executed native commands.

Both existing controller heads reached GitHub, FireSim first then Chipyard,
with independent remote-tip confirmation. Local tracking-reference writes
warned. No staging or local commit occurred. Receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration168/publication.json`.
A fresh final remote-tip query also passes in `publication-final.json`. Plans,
environment helpers, both heads and indices retain their starting bytes.
No external dependency is missing. Complete Rocket Level 1 still requires the
whole-simulator transaction, process exclusion and fresh workload continuation.
Level 2 stays independent; BOOM/Saturn remain pending. Standalone Shuttle,
physical FPGA validation and ASIC power remain outside scope.

## Iteration 167: sealing before runtime I/O publication

Complete Rocket Level 1 remains **in_progress**. The exact recipe settings above
are unchanged. Production `simif_emul_t::seal_checkpoint_io` performs the complete
destination readback and all throwing checks before publication.
`publish_sealed_checkpoint_io` is allocation-free and `noexcept`, with fatal
lifetime/thread/seal/consumption/generation checks before any swap. A commit
invalidates other prepared candidates even for identical destination bytes.
The convenience publication call still seals and publishes in one call. CPU
aggregate admission stays disabled. External exclusion and the complete other
simulator owners remain required. Recovery:
[runtime-io-sealed-publication.md](runtime-io-sealed-publication.md).

The final-source native ASan/UBSan and time-zero VCS DPI matrix passes **24** fresh
component restores, **336** complete owner comparisons, **510** invalid/stale
rejections and **72** fatal contract checks, with no partial publication.
Exhaustive allocation injection passes **2,502** preparation, **1,212** convenience
publication and **1,378** sealing failures. Explicit sealed commits execute with
the next allocation armed to fail and perform zero allocations. Successful
seals can be abandoned without publication. The independent byte/AXI/complete
MT19937-64 oracle passes both convenience and explicitly sealed continuations.
These are component cuts, not complete Rocket CPU checkpoint acceptance.
Selected final-source receipt:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/runtime-io-final/invocation-taxn7a8r/summary.json`.

Executable native/VCS checks from the Chipyard root (fresh invocation paths are
allocated under the requested output directory):

```sh
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_runtime_io_vcs --rocket-header automations/checkpoint_loop/runs/m11-iteration165/verified/rocket/invocation-l8hh65kl/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h --out automations/checkpoint_loop/runs/m11-iteration167/runtime-io-final'
```

The independent runtime-I/O and MMIO audits pass. The expanded MMIO fixture
passes **48** fresh restores, **480** complete owner comparisons, **2,556**
suspended boundaries / **24,318** guard rejections and **824** invalid cases.
The candidate generation is current at every suspended-call check. All eight
preserved native scopes, creator/harness matrix, dispatcher guards, stream
widget, thirty retained auditors, production TSI matrix and all four ordinary
RTL replay windows pass. The expanded DMA fixture and independent audit pass
**84** fresh restores, **336** owner comparisons, **187,296** suspended boundaries /
**1,872,960** guard rejections and **1,230** invalid cases. All **thirteen** final
checks and **nine** independent audits pass. The native suite retains all
**280** Python tests. All implementation and test sources stayed fixed during
the final suite; no check was reduced, skipped or cancelled.

The source-bound structural census again records **15** host widgets and
**11,464** generated entries / **445,838** words, with all CPU admission guards
intact. Three fresh current-binary requests and their independent audit pass
unsupported owner/capability denial, without creating a CPU checkpoint. These
are denial checks, not malformed CPU-image parser validation. Additional audits
pass all 32 dispatcher diagnostics, 336 TSI invalid images and 128 unpublished
prepared/sealed cancellations. Receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/mmio-io/invocation-nh8s_2uw/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/cpu-io/invocation-ktfg_9ew/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/cpu-integration-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/cpu-denial-verified/invocation-nswl5u_f/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/cpu-denial-independent-audit.json`.

All **six** final-source exact-recipe **16-GiB** four-hart controls and their
independent audits pass. Both direct-exit modes finish at **C=3,329,794**;
all four ordinary/restricted and buffered/unbuffered syscall variants finish at
**C=3,330,050**. Complete hart traces and decoded workload labels match within
each protocol. The direct ELF is **6,712 bytes**, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`;
the syscall ELF is **6,760 bytes**, SHA-256
`1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.
These are uninterrupted workload regressions, not complete Level-1 restores.

The independent full-source ordinary RTL audit passes the original target-cycle
cuts **100 / 700,000 / 900,000 / 3,250,000**, with **318,637** complete words read
back before any edge at each cut, **256** captured events, **21,760** sampled
output comparisons, **16** first semantic divergences and **44** invalid cases.
Level 2 remains independent. Current native symbols confirm the split I/O APIs
are linked in the exact-recipe binary, with the receipt at
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/linked-io-api-audit.json`.
Final CPU receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/verified/rocket/invocation-dy6sy1of/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/verified/syscall/invocation-54mp4jji/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/regressions/native-replay/invocation-lwk9ty75/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/replay-full-source-independent-audit.json`.

Executable ordinary RTL and independent component audit checks, with the same
VCS environment and original captured inputs:

```sh
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out automations/checkpoint_loop/runs/m11-iteration167/regressions/native-replay'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.audit_runtime_io --summary automations/checkpoint_loop/runs/m11-iteration167/runtime-io-final/invocation-taxn7a8r/summary.json'
```

The complete executable native argv arrays, exact build settings, source
archives, workload hashes and artifact index are:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/verification-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/raw-native-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/native-input-archives.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/workloads.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/selected-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/artifact-manifest.json`.

Both existing controller heads were published to GitHub in FireSim/Chipyard
order; remote heads independently match. Plans, environment helpers, heads and
indices retain their starting bytes. No staging or local commits occurred.
No external dependency is missing. Complete simulator coordination and
production process exclusion remain pending. The existing generic native
aggregate still performs sequential allocating loads; seal all other owners
and retain actual controller/creator/process exclusion before any CPU admission.
Level 2 stays independent; BOOM/Saturn remain pending. Standalone Shuttle,
physical FPGA validation and ASIC power remain outside scope.

## Iteration 166: joint runtime I/O preparation and publication

Complete Rocket Level 1 remains **in_progress**. Production `simif_emul_t`
now prepares the returned MMIO caller, control AXI, returned CPU stream caller,
CPU DMA AXI and host timing as one component transaction. Exact ordered owner
membership, schema/configuration checks, complete destination recheck,
destination lifetime/thread binding and single-use publication precede
nonthrowing swaps. All other simulator owners and production process exclusion
remain required. CPU admission stays disabled. Recovery:
[runtime-io-transaction.md](runtime-io-transaction.md).

Native ASan/UBSan and time-zero VCS DPI pass **12** fresh component restores
across queued, in-flight and response-buffered AXI cuts, with and without DMA.
The independent Python byte oracle passes **240** complete owner comparisons,
including every queue byte, strobe, response and complete MT19937-64 state with
an explicit pending delay. All **474** invalid/configuration/membership/stale/
foreign/recycled-lifetime/consumed-candidate cases reject. Exhaustive successive
allocation injection passes **2,502** preparation and **1,212** publication
failures with no partial publication. These are synthetic component cuts;
complete Rocket Level-1 CPU continuation remains pending. Receipt:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/final/runtime-io-final/invocation-zn4latyn/summary.json`.

Executable native checks from the Chipyard root, with `vcs-env.sh` last:

```sh
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_runtime_io_vcs --rocket-header automations/checkpoint_loop/runs/m11-iteration165/verified/rocket/invocation-l8hh65kl/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h --out automations/checkpoint_loop/runs/m11-iteration166/final/runtime-io-final'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.audit_runtime_io --summary automations/checkpoint_loop/runs/m11-iteration166/final/runtime-io-final/invocation-zn4latyn/summary.json'
```

The original production blocking-MMIO fixture now restores through this
five-owner transaction and additionally rejects all three group hooks during
suspended calls. Final-source native ASan/UBSan and VCS DPI pass **48** fresh
restores, **240** complete pre-edge and **240** final owner comparisons,
**2,556** suspended boundaries / **21,762** guard rejections, and **824** invalid/
configuration/poisoned-state rejections. The independent original AXI/PRNG
oracle passes every handshake and returned-call label at both delay settings.
Receipt:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/final/mmio-io/invocation-4zzf8vs4/summary.json`.

All **eight** preserved native scopes (**280** Python tests), all **20** creator
continuations, dispatcher guards, **144** stream-widget continuations / **42**
malformed processes and **30** retained auditors pass. The production TSI matrix
passes **64** fresh restores, **192** cancellations, **336** invalid images,
**eight** fatal publication cases and **eight** first divergences. Additional
independent audits verify both MMIO diagnostic owners in **32** dumps, all 336
TSI invalids reject before publication and **128** staged cancellations remain
unpublished. The four ordinary RTL replay cuts again pass **318,637** pre-edge
words per cut; independent full-source replay auditing is recorded with the
final selected receipts below.

The current exact build also passes a source-bound structural census of all
**15** host widgets and **11,464** generated entries / **445,838** emitted
storage words. It confirms all three CPU-managed-stream admission guards and
FCFS-only build admission remain intact. Three fresh native CPU requests and
their independent audit pass unsupported-capability/owner denial: preflight
rejects TSI `widget/12`; capture/restore reject before platform construction.
No checkpoint image is created. Preflight's four ordinary trace files contain
only constructor clock headers. These denials do **not** establish malformed
CPU-image parser validation. Exact receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/cpu-integration-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/cpu-denial-verified/invocation-el8sj3ig/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/cpu-denial-independent-audit.json`.

The retained iteration-165 MMIO receipt also passes the backwards compatible
independent auditor. The final broader regression suite is recorded
under `runs/m11-iteration166/final/`; the earlier fixture corrections and
broader checks that overlapped the test-source correction are diagnostic only.
No check was cancelled. All **twelve** final checks and **nine** independent
audits pass. CPU-managed I/O again passes **84** fresh restores, **336** owner
comparisons, **187,296** suspended boundaries / **1,123,776** guard rejections
and **1,230** invalid/poisoned cases. The full-source ordinary RTL replay audit
passes **256** captured events, **16** first semantic divergences and **44**
invalid cases at the original target-cycle cuts **100 / 700,000 / 900,000 /
3,250,000**, with **318,637** complete pre-edge words at each cut. Level 2 stays
independent.

All **six** final-source exact-recipe **16-GiB** four-hart controls and their
independent audits pass. Both direct-exit modes finish at **C=3,329,794**;
all four syscall modes finish at **C=3,330,050**. Complete hart traces and decoded
workload labels match within each protocol. The direct Level-2 ELF remains
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`;
the syscall ELF is
`1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.
Native current receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/final/verified/rocket/invocation-7loyhnbs/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/final/verified/syscall/invocation-57sygbnp/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/final/regressions/native-replay/invocation-hrpb9xd3/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/final/replay-full-source-independent-audit.json`.

Current native blocking-I/O and ordinary RTL commands:

```sh
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_mmio_io_vcs --rocket-header automations/checkpoint_loop/runs/m11-iteration165/verified/rocket/invocation-l8hh65kl/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h --out automations/checkpoint_loop/runs/m11-iteration166/final/mmio-io'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out automations/checkpoint_loop/runs/m11-iteration166/final/regressions/native-replay'
```

Both plans, environment helpers, heads and indices retain their starting bytes.
Existing controller heads reached GitHub, FireSim first then Chipyard, with
fresh remote-head checks; local tracking-reference writes warned. No staging or
local commits occurred. Exact recipe settings, workload hashes, source archives,
selected receipts, all native commands and complete full-path artifact index:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/selected-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/workloads.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/native-input-archives.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/raw-native-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/verification-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration166/artifact-manifest.json`.

Complete Rocket Level 1 remains pending joint simulator coordination and
production thread/signal/descriptor/parser exclusion; the runtime I/O transaction
supplies neither policy. No external dependency is missing. BOOM/Saturn remain
pending; standalone Shuttle, physical FPGA validation and ASIC power remain
outside scope.

## Iteration 165: production control MMIO call owner

Complete Rocket Level 1 remains **in_progress**. Production `simif_emul_t`
now has a distinct returned-call MMIO owner. Suspended/interrupted reads and
writes, nested I/O and invalid/configuration images fail explicitly. AXI queues
remain independently owned by `runtime/mmio`. TracerV count reads nest both
MMIO and CPU stream returned-call owners. The diagnostic inventory includes
both. CPU aggregate admission remains disabled pending complete coordination
and production process exclusion. Recovery: [mmio-runtime-io.md](mmio-runtime-io.md).

Native ASan/UBSan and VCS DPI pass **48** fresh component restores, **192**
complete pre-edge and **192** final owner comparisons. Across **2,556** suspended
boundaries, **14,094** checkpoint/reentry checks reject without modifying AXI
state; **438** boundaries also exercise the nested CPU stream wrapper. Both
queued (**868**) and in-flight (**1,688**) boundaries occur. All **824**
truncated, byte-corrupt, trailing, incompatible-geometry and poisoned-lifetime
cases reject. An independent MT19937-64/AXI oracle checks all channel handshakes,
returned-call labels and complete host timing payloads at both delay settings.
These labels belong to a synthetic peer, not Rocket target cycles. All **32**
dispatcher diagnostics independently contain both the new MMIO caller and the
AXI owner. Exact receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration165/mmio-io/invocation-pmzg9zk1/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration165/mmio-diagnostic-audit.json`.

Executable checks from the Chipyard root (`vcs-env.sh` sourced last):

```sh
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_mmio_io_vcs --rocket-header automations/checkpoint_loop/runs/m11-iteration164/verified/rocket/invocation-lcl6e8rs/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h --out automations/checkpoint_loop/runs/m11-iteration165/mmio-io'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.audit_mmio_io --summary automations/checkpoint_loop/runs/m11-iteration165/mmio-io/invocation-pmzg9zk1/summary.json'
```

All **eight** preserved native scopes (**280** Python tests), the **144**
stream-widget continuations / **42** malformed processes, all **20** creator
continuations, dispatcher guards and **30** retained auditors pass. The
CPU-managed I/O regression again passes **84** fresh component restores. The
production TSI component matrix passes **64** fresh restores, **192**
cancellations, **336** invalid images, **eight** fatal publication cases and
**eight** semantic first divergences. Independent guard and publication audits
also pass; all 336 invalid TSI images reject before publication and 128 staged
cancellations remain unpublished.

All **four** fresh ordinary RTL VCS windows and the independent full-source
audit pass **318,637** pre-edge words per cut, **256** captured events,
**16** first-boundary semantic corruptions and **44** invalid cases. Original
target-cycle labels remain **100 / 700,000 / 900,000 / 3,250,000**. The direct
Level-2 ELF remains SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Level 2 stays independent. All **six** final-source exact-recipe **16-GiB**
four-hart controls and their independent audits pass. Direct-exit runs finish at
**C=3,329,794**; all four syscall modes finish at **C=3,330,050**. Complete hart
traces and decoded workload labels match within each protocol. The syscall ELF
SHA-256 is
`1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.
The independent native suite audit also passes. No external dependency is
missing. BOOM/Saturn remain pending; standalone Shuttle, physical FPGA validation
and ASIC power remain outside scope.

Current native ordinary RTL replay command:

```sh
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out automations/checkpoint_loop/runs/m11-iteration165/regressions/native-replay'
```

Both plans, environment helpers, heads and indices retain their starting bytes.
Existing controller commits reached GitHub, FireSim before Chipyard, with fresh
remote-head checks; local tracking-reference updates warned. No staging or local
commits occurred. Final receipts, workload hashes, source archives, all native
commands and a complete full-path artifact index:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration165/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration165/selected-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration165/workloads.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration165/native-input-archives.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration165/raw-native-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration165/verification-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration165/artifact-manifest.json`.

## Iteration 164: production CPU-managed stream I/O owner

Complete Rocket Level 1 remains **in_progress**. `simif_emul_t` now enumerates
`runtime/cpu-managed-stream-io` as a concrete returned-call owner instead of an
unsupported diagnostic placeholder. The image binds the complete DMA geometry;
AXI queues, initialized stream-widget state, generated stream hardware and
harness latches remain separate owners. Suspended MMIO/DMA and interrupted
calls explicitly reject capture/validation/loading and nested I/O. Zero-byte
transfers issue no requests; non-beat-aligned transfers reject before submitting
requests. Recovery: [cpu-managed-runtime-io.md](cpu-managed-runtime-io.md).

Native ASan/UBSan and VCS DPI pass **84** fresh component restores with **168**
complete pre-edge owner comparisons and **168** final owner comparisons, **187,296** suspended boundaries /
**1,123,776** checkpoint/nested-call rejections, and **1,230** malformed,
incompatible-geometry and poisoned-lifetime rejections. All three tested bus
widths (64/128/512 bits) retain complete byte/strobe/response checks and the
independent burst-order oracle. Transfers cover **0 / 1 / 255 / 256 / 257 / 513**
beats in both directions, plus suspended MMIO. The operation labels belong to
a synthetic AXI peer; they are not Rocket target cycles. Accepted receipt:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration164/verified/cpu-io/invocation-803gnv0j/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration164/cpu-io-independent-audit.json`.

The exact Rocket stream census records four TracerV output streams, no input
streams, and the generated engine's **32** entries / **24,604** words in
`runs/m11-iteration164/rocket-stream-owner-inventory.json`. This structural census
does not establish generated-state restore. CPU-managed aggregate admission
remains disabled pending complete coordination and production process exclusion.

All **eight** preserved native regression scopes (**280** Python tests) and the
independent native audit pass. The existing stream-widget suite separately
passes **144** fresh continuations and **42** malformed processes. All four
creator/harness modes pass **20** fresh continuations. Dispatcher guards and
all **30** retained auditors pass. The sealed production TSI component matrix
passes **64** fresh restores, **192** cancellations, **336** invalid images,
**eight** fatal publication cases and **eight** semantic first divergences.
An additional independent audit checks all 336 invalid images reject before
publication and 128 cancellations remain unpublished.

Four fresh ordinary RTL VCS windows pass **318,637** words before any edge at
each cut, **256** captured events, **16** first-boundary semantic corruptions and
**44** invalid cases. Original target-cycle labels remain **100 / 700,000 /
900,000 / 3,250,000**. The Level-2 ELF remains SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
All **six** final-source exact-recipe **16-GiB** four-hart controls and their
independent audits pass. Direct-exit runs terminate at **C=3,329,794**; all four
syscall protocols terminate at **C=3,330,050**. Complete hart traces and decoded
workload labels match within each protocol. The syscall ELF SHA-256 is
`1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.
The independent full-source Level-2 audit also passes. Level 2 remains independent.
BOOM/Saturn remain pending. No external dependency is missing. Standalone Shuttle, FPGA validation and ASIC power remain outside
scope.

Executable checks from the Chipyard root (`vcs-env.sh` sourced last):

```sh
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_cpu_managed_io_vcs --rocket-header automations/checkpoint_loop/runs/m11-iteration163/verified/rocket/invocation-r3oduduh/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h --out automations/checkpoint_loop/runs/m11-iteration164/verified/cpu-io'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.audit_cpu_managed_io --summary automations/checkpoint_loop/runs/m11-iteration164/verified/cpu-io/invocation-803gnv0j/summary.json'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out automations/checkpoint_loop/runs/m11-iteration164/regressions/native-replay'
```

The initial component/native runs were cancelled after correcting a configuration
reference lifetime in the new test fixture. Initial creator/guard catalogs and
the first Rocket control attempt include the older fixture snapshot. These
remain diagnostic. Affected checks were rerun under `verified/`; unaffected
replay, TSI and retained checks remain under `regressions/`. `selected-results.json`
identifies every accepted receipt. Implementation sources stayed fixed after that correction. Existing controller heads reached
GitHub, FireSim before Chipyard; local tracking-reference writes warned and
remote heads were independently checked. Both plans, environment helpers, heads
and indices retain their starting bytes. No staging or local commits occurred.

Final receipts, exact source archives, workload hashes and executable commands:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration164/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration164/selected-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration164/workloads.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration164/native-input-archives.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration164/raw-native-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration164/verification-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration164/artifact-manifest.json`.

## Iteration 163: publish the actual TSI candidate from its sealed creator

Complete Rocket Level 1 remains **in_progress**. The production bridge candidate
now separates throwing validation (`seal_publication`) from allocation-free,
nonthrowing publication (`publish_sealed`). The reserved creator retains the
candidate, seals it under a component guard, commits through the staged mailbox,
and reads back all seventeen owners before acknowledging publication. The guard
stays held until launch or cancellation. Recovery:
[tsi-sealed-publication.md](tsi-sealed-publication.md).

Native ASan/UBSan and native VCS DPI pass **64** fresh component restores,
**192** cancellations (**64** each before sealing, after sealing before commit,
and after commit), **336** malformed/incompatible/incomplete images and **eight**
actual semantic first divergences. Publication succeeds with all C++ allocations
disabled. Same-candidate sealing retries every injected allocation failure
without changing the live bridge. Unsealed, repeated, foreign-thread and
occupied-destination publication each terminate before acknowledgment on both
backends (**eight** processes). The component's serial MMIO peer and mutex are
fixtures; this is not CPU Level-1 continuation or production process exclusion.

Accepted final-source component receipt:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration163/verified/bridge/invocation-zkwt1pyu/summary.json`.

All **eight** preserved native regression scopes (**280** Python tests) and the
independent native audit pass. Four fresh ordinary RTL VCS windows and the
independent full-source audit pass **318,637** pre-edge words per cut, **256**
captured events, **16** semantic first divergences and **44** invalid cases.
The captured cuts retain original target-cycle labels **100**, **700,000**,
**900,000** and **3,250,000**. Independent TSI evidence checks **52,088** owner
comparisons over **3,000** serial boundaries and **136** sealed publications.
The same-candidate seal retry rejects **685** native and **688** VCS allocation
failures without publication. The additional publication audit rejects all
**336** invalid processes before sealing and verifies **128** unpublished
cancellations.
Level 2 retains the direct-exit ELF, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Workload hashes are recorded in `runs/m11-iteration163/workloads.json`.
All **six** final-source exact-recipe **16-GiB** four-hart controls and independent
audits pass: both direct-exit controls terminate at **C=3,329,794**; all four
syscall protocols terminate at **C=3,330,050**. Complete hart traces and decoded
workload labels match within each protocol. The syscall ELF SHA-256 is
`1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.
The creator/harness checks and independent audit pass all four modes (**20**
fresh continuations), **140** malformed processes and **80** lifecycle-negative
processes. Dispatcher guards and all **30** retained auditors pass.

Final receipts and complete executable commands/source archives:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration163/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration163/selected-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration163/workloads.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration163/native-input-archives.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration163/raw-native-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration163/verification-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration163/artifact-manifest.json`.

Independent results are under `verified/*-independent-audit.json`; the separate
336-case publication audit is `publication-negative-audit.json`. Both plans,
environment helpers, heads and indices retain their starting bytes. Existing
controller heads are published on GitHub, FireSim before Chipyard; local
tracking-ref writes warned, and remote heads were independently checked.

Executable native checks (Chipyard root; `vcs-env.sh` is sourced last):

```sh
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_tsi_bridge_context_vcs --context-summary automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json --recipe-build-identity automations/checkpoint_loop/runs/m11-iteration155/rocket-controls/invocation-53d1qw51/rocket-build-identity.json --out automations/checkpoint_loop/runs/m11-iteration163/verified/bridge'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.audit_tsi_bridge_context --summary automations/checkpoint_loop/runs/m11-iteration163/verified/bridge/invocation-zkwt1pyu/summary.json'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out automations/checkpoint_loop/runs/m11-iteration163/verified/native-replay'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build automations/checkpoint_loop/runs/m11-iteration160/rocket-final/invocation-ex54qx6f/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out automations/checkpoint_loop/runs/m11-iteration163/verified/rocket'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_syscall_vcs --build-identity automations/checkpoint_loop/runs/m11-iteration163/verified/rocket/invocation-r3oduduh/rocket-build-identity.json --workload automations/checkpoint_loop/runs/m11-iteration151/workload --out automations/checkpoint_loop/runs/m11-iteration163/verified/syscall'
```

The earlier `runs/m11-iteration163/bridge/` invocation overlapped source edits;
its source-drift rejection makes it diagnostic only. Accepted evidence is under
`verified/`. Complete simulator and process coordination remain pending; no
complete CPU milestone is accepted.

## Iteration 162: publish creator-affine owners while retaining guards

Complete Rocket Level 1 remains **in_progress**. The reserved mailbox can now
stage an owner commit/readback before sealing and execute it on its creator
while keeping the final guards held. The controller can then publish/read back
its remaining owners and RTL under the same loading hold. Publication capture
destruction precedes acknowledgment; cancellation destroys staged captures
before guards and resident owners. Duplicate, unsealed, foreign, recursive and
late calls reject. Skipped publication or throwing commit is fatal before
continuation. The complete coordinator and production process exclusion still
require implementation. Recovery: [driver-owner-publication.md](driver-owner-publication.md).

Native ASan/UBSan and VCS each pass **24** guarded creator commits, **16**
launches, **16** cancellations (eight before commit), **32** allocation failures
and **376** lifecycle rejections, in addition to the retained creator tests.
Both backends pass fatal throwing-commit and skipped-publication cases with
exit **73** before acknowledgment. The VCS component asserts time zero and zero
edges. All four harness modes pass **20** fresh continuations at cuts **13, 14,
16, 31, 32**; the ten reserved cases publish and read back on the creator, retain
the guard through complete pre-edge readback, and release it before execution.
The separate publication audit verifies **110** invalid processes never enter
creator publication. These operation cuts are component tests, not Rocket
Level-1 target-cycle restores.

Accepted creator receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/creator-verified/invocation-s3rdevgj/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/verified/creator-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/publication-negative-audit.json`.

Final-source regressions and audits pass: **eight** preserved native scopes
(**280** Python tests), **30** retained auditors, all dispatcher guards and
complete archive audits. Production TSI bridge component tests pass **64** fresh
restores and **64** cancellations, **52,088** owner comparisons, **3,000** serial
boundaries, **336** invalid processes and **eight** first divergences. That
component still publishes during initial preparation and does not yet exercise
the new sealed publication callback with a real TSI candidate.

Fresh ordinary RTL VCS and the independent full-source audit pass cuts
**100, 700,000, 900,000, 3,250,000**, with **318,637** words read back before any
edge per cut, **256** captured events, **16** semantic first divergences and
**44** invalid cases. All six exact-recipe 16-GiB four-hart controls and independent
audits pass: both direct controls at **C=3,329,794**, and ordinary,
ordinary-buffered, restricted and restricted-buffered syscall controls at
**C=3,330,050**. All full hart traces and decoded labels match within each
protocol. These are uninterrupted CPU controls, not Level-1 CPU restores.

Workload bytes and SHA-256:

- Direct exit / retained Level 2: **6,712** bytes,
  `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
- Syscall 93: **6,760** bytes,
  `1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.

Exact receipts and full artifact paths:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/selected-results.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/workloads.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/native-input-archives.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/raw-native-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/verification-commands.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/artifact-manifest.json`.

Executable checks (Chipyard root; each VCS shell sources `vcs-env.sh` last):

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_driver_creator_vcs --build automations/checkpoint_loop/runs/m3-metasim --out automations/checkpoint_loop/runs/m11-iteration162/creator-verified'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.audit_driver_creator --summary automations/checkpoint_loop/runs/m11-iteration162/creator-verified/invocation-s3rdevgj/summary.json'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration162/audit-publication-negatives.py'
```

Additional executed native VCS checks:

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/verified/native-replay'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/verified/repeat-native.py'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/rocket-final/invocation-ex54qx6f/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/verified/rocket'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_tsi_bridge_context_vcs --context-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration155/rocket-controls/invocation-53d1qw51/rocket-build-identity.json --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration162/verified/bridge'
```

Broader final-source checks pass under `runs/m11-iteration162/verified/`.
Earlier harness probes exposed a fixture override bypassing the MMIO guard,
then an aggregate guard check asserting publication too early; both test errors
were corrected. Earlier source epochs remain diagnostic and cannot certify the
final source. Complete Rocket Level 1 remains disabled; independent Level 2,
BOOM/Saturn, hardware and power scope are unchanged.

## Iteration 161: retain creator guards through publication and readback

Complete Rocket Level 1 remains **in_progress**. The optional staged creator
can now seal final validation with a retained guard bundle, keep it alive while
the controller publishes and reads back state, and release it on the creator
before continuation. Later preparation rejects. A throwing validator leaves
the same creator retryable. Cancellation destroys staged captures, then guards,
then the resident resource. CPU stream and empty-schema admission remain
unchanged. The complete simulator coordinator and production process-wide
exclusion still require implementation. Recovery:
[driver-publication-scope.md](driver-publication-scope.md).

Native ASan/UBSan and VCS each pass **32** sealed lifetimes: **16** launches,
**16** cancellations, **64** guard destructions including failed validation,
**64** controller/creator allocation failures and **416** lifecycle rejections.
Real creator mutex/mask lifetime and restoration checks pass at VCS time zero
with zero edges. Both legacy and both reserved actual harness modes pass
**20** fresh continuations, **140** malformed processes, **80** lifecycle cases
and **140** aggregate prevalidation cases (overlapping malformed cases).
The ten reserved continuations additionally test nine invalid/late operations
and one throwing final validator each. The creator mutex stays held during
native publication, generated RTL/harness deposit and complete pre-edge
readback, and releases before any driver step or finalization. All five cuts,
including terminal zero-edge continuation, retain original-label comparisons.
The independent audit passes, including four incomplete receipt rejections.
Accepted creator receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/creator/invocation-kojnlkk6/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/creator-independent-audit.json`.

Four-cut fresh ordinary RTL VCS replay and its independent full-source audit
pass at **100, 700,000, 900,000 and 3,250,000**: all **318,637** words read back
before any edge per cut, **256** captured events, sixteen actual first
divergences and **44** invalid-image/loader cases. The direct ELF SHA-256
remains `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Accepted replay receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/native-replay/invocation-wx32n7yp/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/replay-independent-audit.json`.

The production TSI bridge matrix and independent audit pass **64** fresh
restores, **64** cancellations, **52,088** complete-owner comparisons,
**3,000** serial boundaries / **4,652** words, **336** invalid processes,
**1,326** control truncations, **7,555** allocation failures, ten foreign
rejections, four late guards and eight first divergences. Fourteen incomplete
receipt variants and all **125** individual source omissions reject. These
serial MMIO labels are host operations, not Rocket target-cycle restores.

All eight preserved native scopes (**280** Python tests) and the independent
archive audit pass. All thirty retained auditors, the complete legacy dispatcher
matrix and poison/loading/capture guards pass. Accepted regression receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/bridge/invocation-j_ny6lbo/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/bridge-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/native-final/invocation-e5k5j6mm/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/native-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/retained-auditor-rechecks/invocation-bodrurbl/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/dispatcher/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/dispatcher-guards/invocation-55np9w71/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/dispatcher-guard-independent-audit.json`.

All six full final-source **16-GiB**, four-hart exact-recipe controls and
independent audits pass. The two direct controls finish at **C=3,329,794**;
ordinary, buffered, restricted and restricted-buffered syscall controls finish
at **C=3,330,050**. Complete hart traces and decoded workload labels match
within each protocol. Level 2 retains the direct ELF. Workload bindings:

| Image | Bytes | SHA-256 |
| --- | ---: | --- |
| Direct exit, `runs/m11-iteration82/workload/rocket-quad.riscv` | 6,712 | `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4` |
| Syscall 93, `runs/m11-iteration151/workload/rocket-quad.riscv` | 6,760 | `1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958` |

Full workload paths, build reports and hashes are in
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/workloads.json`.
Accepted CPU receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/rocket/invocation-mylvftgm/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/rocket-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/syscall/invocation-hiropy2o/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/syscall-independent-audit.json`.

The mutex/mask scenarios test retained scope; they do not establish production
all-thread/signal/descriptor/parser exclusion or complete CPU Level 1.
All selected receipts bind the completed final sources. Full artifact paths,
hashes, source archives and raw executable native commands are under this
iteration in `summary.json`, `selected-results.json`, `artifact-manifest.json`,
`native-input-archives.json`, `raw-native-commands.json` and
`verification-commands.json`. Both plans, environment helpers, heads and
indices retain their starting bytes. Existing controller heads reached GitHub,
FireSim first then Chipyard; only local tracking-ref writes warned. No staging
or local commits occurred. No external dependency is missing.

Native executable check (Chipyard root; VCS environment sourced last):

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_driver_creator_vcs --build automations/checkpoint_loop/runs/m3-metasim --out automations/checkpoint_loop/runs/m11-iteration161/creator'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out automations/checkpoint_loop/runs/m11-iteration161/native-replay'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration161/repeat-native.py'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/rocket-final/invocation-ex54qx6f/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/rocket'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_syscall_vcs --build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/rocket/invocation-mylvftgm/rocket-build-identity.json --workload /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/workload --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/syscall'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_tsi_bridge_context_vcs --context-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration155/rocket-controls/invocation-53d1qw51/rocket-build-identity.json --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration161/bridge'
```

## Iteration 160: stage the driver continuation before owner publication

Complete Rocket Level 1 remains **in_progress**. The optional creator mailbox
can stage its dispatcher continuation under the loading hold and commit it
without thread creation or callable allocation. Cancellation destroys its
captures on the creator before the retained owner bundle. The staged policy
rejects later checkpoint scheduling changes. CPU stream and empty-schema
admission remain unchanged. Recovery:
[driver-prepared-launch.md](driver-prepared-launch.md).

Final-source ASan/UBSan and VCS each pass thirty-two staged lifetimes: sixteen
launches, sixteen cancellations, thirty-two allocation failures before staging,
preparation exceptions after staging and **208** lifecycle rejections. Commit
runs with controller-side allocation failure enabled. All four actual harness
modes and independent audit pass **20** fresh continuations, **140** malformed
processes, **80** lifecycle cases and **140** aggregate prevalidation cases
(overlapping malformed counts). Ten reserved continuations additionally test
allocation-failure retry and six launch-policy guards each, then compare every
generated/native owner before any edge and the continued trace at original
labels. Terminal cuts retain zero edges. Accepted receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/creator-final/invocation-9c4qbbdg/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/creator-final-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/dispatcher-guards/invocation-_p49im9_/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/dispatcher-final-guard-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/native-replay/invocation-wuvevknt/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/replay-final-independent-audit.json`:
  four fresh ordinary RTL VCS cuts at **100, 700,000, 900,000 and 3,250,000**;
  **318,637** semantic words before any edge per cut, **256** captured events,
  sixteen actual first divergences and **44** invalid cases. The direct ELF
  SHA-256 remains `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

The final production TSI bridge component matrix and independent audit pass
**64** fresh restores and **64** cancellations, **52,088** complete-owner
comparisons, **3,000** serial boundaries / **4,652** words, **336** malformed
processes, **1,326** control truncations, **7,555** allocation failures, ten
foreign calls, four late guards and eight first divergences. Fourteen incomplete
receipt variants and all **125** individual source omissions reject. The serial
MMIO fixture labels remain host operations, not Rocket target cycles.

All eight preserved native scopes (**280** Python tests) and independent archive
audit pass. All thirty retained auditors, the legacy dispatcher matrix and
final sanitizer poison/loading/capture guards pass. Additional receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/bridge/invocation-tlkwhav8/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/bridge-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/native-final/invocation-c8e92cwn/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/native-final-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/retained-auditor-rechecks/invocation-70j1vmse/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/dispatcher-final/summary.json`.

All six final-source **16-GiB** four-hart workload controls pass: both direct
controls complete at **C=3,329,794** and all four ordinary/restricted syscall
controls at **C=3,330,050**. Complete hart traces and decoded workload/store
labels match within each protocol. The syscall-93 ELF SHA-256 remains
`1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.
Exact recipe/build and complete workload receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/rocket-final/invocation-ex54qx6f/rocket-build-identity.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/rocket-final/invocation-ex54qx6f/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/rocket-final-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/syscall-final/invocation-fkvgbq09/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration160/syscall-final-independent-audit.json`.

These uninterrupted workloads and component results do not establish complete
CPU Level 1. Earlier import/unsupported-auditor-option failures and source epochs
superseded by the late scheduling guard remain diagnostic only. Selected final
receipts bind the completed final sources. Full artifact paths/hashes, source
archives and raw executable native argv are under this iteration in
`summary.json`, `selected-results.json`, `artifact-manifest.json`,
`native-input-archives.json`, `raw-native-commands.json` and
`verification-commands.json`. Both plans, environment helpers, local heads and
indices retain their starting bytes. Existing controller heads reached GitHub,
FireSim first then Chipyard; only local tracking-ref writes warned. No staging
or local commits occurred.
No external dependency is missing. Full simulator coordination, jointly guarded
publication and production process exclusion remain pending.

Native executable checks (Chipyard root; VCS environment sourced last):

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_driver_creator_vcs --build automations/checkpoint_loop/runs/m3-metasim --out automations/checkpoint_loop/runs/m11-iteration160/creator-final'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build automations/checkpoint_loop/runs/m11-iteration159/rocket-verified/invocation-4jds5tta/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out automations/checkpoint_loop/runs/m11-iteration160/rocket-final'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_tsi_bridge_context_vcs --context-summary automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json --recipe-build-identity automations/checkpoint_loop/runs/m11-iteration155/rocket-controls/invocation-53d1qw51/rocket-build-identity.json --out automations/checkpoint_loop/runs/m11-iteration160/bridge'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_syscall_vcs --build-identity automations/checkpoint_loop/runs/m11-iteration160/rocket-final/invocation-ex54qx6f/rocket-build-identity.json --workload automations/checkpoint_loop/runs/m11-iteration151/workload --out automations/checkpoint_loop/runs/m11-iteration160/syscall-final'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out automations/checkpoint_loop/runs/m11-iteration160/native-replay'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration160/repeat-native-final.py'
```

## Iteration 159: creator-owned provider lifetime through launch and cancellation

Complete Rocket Level 1 remains **in_progress**. The optional pre-edge mailbox
now retains one creator-owned resource bundle through preparation retries,
continuation and cleanup, or destroys it on its worker during cancellation.
The actual harness tests the production `simif_emul_t` lifetime entry point;
the production TSI bridge component keeps its actual provider and peers live
through mailbox launch. It rereads all seventeen component owners before MMIO,
then services the restored context on the same creator. CPU stream/empty-schema
admission and the bridge aggregate schema stay unchanged. Recovery:
[driver-creator-lifetimes.md](driver-creator-lifetimes.md).

Native ASan/UBSan and VCS each pass the original 512 tasks / 512 exceptions /
17 launches / 16 cancellations / 1,296 rejections, plus 32 retained resource
lifetimes: sixteen launches, sixteen cancellations, 32 preparation exceptions
and 176 access/occupied-slot rejections. Continuation captures are destroyed
before the retained resource. All four actual harness modes pass 20 fresh
continuations, 140 malformed processes, 80 lifecycle cases and 140 aggregate
prevalidation cases (overlapping malformed cases). Ten reserved continuations
keep a resource alive through every step and finalization, including the
terminal zero-edge cuts, then destroy it on its creator before simulator
teardown. The independent audit rejects four incomplete receipt variants.

The actual restricted TSI bridge matrix and independent audit pass **64** fresh
restores and **64** fresh cancellations, **52,088** complete-owner comparisons,
**3,000** serial boundaries / **4,652** words, **336** malformed processes,
**1,326** control byte truncations, **7,555** allocation failures, ten foreign
calls, four late guards and eight actual first divergences. All launched
published providers additionally match their complete context/control at launch
before MMIO. Cancellation cuts cover all eight scenarios and every selected
early, active and terminal component cut, without serving the provider. Cleanup
runs on the creator before join/cancel returns. Fourteen missing/duplicate
receipt variants and all 125 source omissions reject. These are serial-MMIO
component operations, not Rocket target-cycle continuation.

Accepted receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/creator-verified/invocation-vbxl1fu3/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/creator-resource-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/bridge/invocation-ian9aw9x/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/bridge-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/native-replay/invocation-ey0ohtt6/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/replay-independent-audit.json`:
  fresh ordinary RTL VCS at cuts 100, 700,000, 900,000 and 3,250,000;
  **318,637** semantic words before any edge at each cut, **256** captured events,
  sixteen semantic first divergences and **44** invalid cases. Direct workload
  SHA-256 remains `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

All thirty retained auditors, the legacy dispatcher matrix, full sanitizer
poison/loading/capture guards and all eight preserved native scopes (280 Python
tests) with their independent archive audit pass. All six complete **16-GiB**
four-hart controls and independent audits pass: both direct controls at
**C=3,329,794**, all four ordinary/restricted syscall controls at **C=3,330,050**.
Complete instruction traces and decoded workload/store labels match within each
protocol. The syscall-93 ELF hash is
`1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.
The exact recipe identity and complete control receipts are:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/rocket-verified/invocation-4jds5tta/rocket-build-identity.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/rocket-verified/invocation-4jds5tta/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/rocket-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/syscall-controls/invocation-w6s7zg1l/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/syscall-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/native-regressions/invocation-mfa1rrvl/summary.json` and
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/native-independent-audit.json`.

These controls remain uninterrupted workloads, not complete CPU Level-1 restores.
The source-epoch failures and the
premature audit of a still-running replay remain diagnostic only. No external
dependency is missing. Full simulator coordination, process-wide exclusion and
jointly prepared publication/launch remain pending before Rocket Level 1 can
be enabled. Level 2 stays independent; BOOM/Saturn remain pending.

Native executable checks for iteration 159 (run from the Chipyard root):

```bash
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_driver_creator_vcs --build automations/checkpoint_loop/runs/m3-metasim --out automations/checkpoint_loop/runs/m11-iteration159/creator-verified'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_tsi_bridge_context_vcs --context-summary automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json --recipe-build-identity automations/checkpoint_loop/runs/m11-iteration155/rocket-controls/invocation-53d1qw51/rocket-build-identity.json --out automations/checkpoint_loop/runs/m11-iteration159/bridge'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --seed-build automations/checkpoint_loop/runs/m11-iteration159/rocket-controls/invocation-5g87lf1l/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc --out automations/checkpoint_loop/runs/m11-iteration159/rocket-verified'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_syscall_vcs --build-identity automations/checkpoint_loop/runs/m11-iteration159/rocket-verified/invocation-4jds5tta/rocket-build-identity.json --workload automations/checkpoint_loop/runs/m11-iteration151/workload --out automations/checkpoint_loop/runs/m11-iteration159/syscall-controls'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python automations/checkpoint_loop/runs/m11-iteration159/repeat-native.py'
bash -lc 'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out automations/checkpoint_loop/runs/m11-iteration159/native-replay'
```

All build/runtime argv arrays, independent audit commands and complete artifact
paths/hashes are retained under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration159/`.
`verification-commands.json` lists repeatable checks; `raw-native-commands.json`
records the actual native compile/simulation commands; `native-input-archives.json`
binds source catalogs and the separate recipe/provider identities. The exact
recipe settings above remain unchanged. No FPGA bitstream is built.

## Iteration 158: optional pre-edge driver creator reservation

Complete Rocket Level 1 remains **in_progress**. `simif_emul_t` now optionally
reserves the eventual driver worker after existing loading admission, runs
creator-side preparation callbacks synchronously, and launches the restored
continuation on that same worker. Callbacks cannot issue production MMIO or
advance RTL. Exceptions remain retryable; foreign/recursive/empty/repeated and
post-launch requests reject. Unused reservations cancel and join. A failed
bootstrap keeps MMIO/tick exclusion after consuming its pending-driver pointer.
CPU stream and empty-schema owner admission still reject, and the production
TSI bridge's aggregate schema stays empty. This adds no public CPU restore
plusarg or complete checkpoint profile. Recovery:
[driver-creator-reservation.md](driver-creator-reservation.md).

Native ASan/UBSan and VCS each pass **512** preparation tasks, **512** exceptions,
**17** launches, **16** cancellations and **1,296** rejection cases. Four actual
VCS harness modes (legacy/reserved, each separate-owner/aggregate) pass all five
cuts: **20** fresh continuations, **140** malformed native processes, **80**
lifecycle cases and **140** aggregate prevalidation cases; aggregate counts
overlap malformed cases. Every generated word, harness bank and seven native
owners read back before bootstrap, and all captured continuation rows and target
edge labels match. Ten reserved continuations check creator identity, including
terminal zero-edge cuts; **130** preparation guards and ten retryable exceptions
pass. The independent audit additionally rejects four missing/duplicate receipt
variants. Receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/creator-verified/invocation-qfpd726i/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/creator-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/dispatcher-guards/invocation-9k5w6aei/summary.json` and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/dispatcher-guard-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/dispatcher-final/summary.json`: all 32 native/VCS dispatcher continuations and ten
  malformed processes. The separate poison test covers both reservation modes
  at all six invalid clock/reset/finish/bank shapes: **108** rejections, twelve
  destinations, **60** unchanged native owner readbacks and zero launched workers.
  Loading reservation and full live/public/polling/deadline guard scopes pass too.

The actual restricted production TSI bridge component matrix uses this mailbox
for its creator-side preparation, publication, serial service and destruction.
The separate mailbox launch checks the worker identity; this does not join the
bridge to a Rocket simulator cut: the bridge fixture finishes provider lifetime
inside the mailbox callback, while the harness separately tests driver launch.
A live provider spanning that launch remains pending. **64** fresh restores,
**52,088** complete-owner comparisons, **3,000** serial boundaries and **4,652**
words match. All **336**
invalid-image processes, **1,326** control byte truncations, **7,555** successive
allocation failures, ten foreign calls, four late guards and eight semantic
first-divergence corruptions pass. Invalid cases leave descriptors, parser
globals and unpublished bridge state unchanged; VCS asserts zero time/edges.
Its independent audit rejects twelve missing/duplicate receipt variants and all
**125** individual source omissions. These labels remain host operations with a
serial MMIO fixture, not complete Rocket target cycles:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/bridge-verified/invocation-lq9v6sit/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/bridge-independent-audit.json`.

All **eight** preserved native scopes (**280 Python tests**) and their independent
archive audit pass. Thirty retained auditors pass. All **six full 16-GiB four-hart
controls** and independent audits pass: both direct modes at **C=3,329,794**, all
four ordinary/restricted syscall modes at **C=3,330,050**. Complete per-hart traces
and decoded workload/store labels match their respective uninterrupted references.
Workload SHA-256 values remain:

- Direct ELF / Level 2: `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
- Syscall-93 ELF: `1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.

The exact recipe settings above are read from YAML by the native builder; the
new executable retains all 11,464 generated entries / 445,838 words. Native
VCS Y-2026.03-SP1, `-full64`, `VCS_FLAGS=-Mupdate` and GCC/G++ 13 remain pinned.
No bitstream is built. Completed receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/rocket-final/invocation-l12vwy6a/summary.json` and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/rocket-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/syscall-controls/invocation-pbgmn24x/summary.json` and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/syscall-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/native-regressions/invocation-xba0vy2y/summary.json` and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/native-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/retained-auditor-rechecks/invocation-i6zkcjst/summary.json`.

Fresh ordinary RTL VCS and the independent full-source audit pass all four
retained complete ChipTop Level-2 cuts **C=100 / 700,000 / 900,000 / 3,250,000**:
all **318,637 semantic words** read back before any edge per cut, **256** captured
events, sixteen actual first divergences and 44 invalid cases. Level 2 remains
independent of the creator/bridge components:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/native-replay/invocation-tfxdbih7/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/replay-full-source-audit.json`.

Exact executable commands as argv arrays (including native build, runtime,
fault and invalid cases), complete source bindings and artifact paths/hashes:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/verification-commands.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/raw-native-commands.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/native-input-archives.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration158/artifact-manifest.json`. `summary.json` and `selected-results.json`
select completed receipts. Initial source-stability failures after the poison
guard/auditor corrections and the first bridge auditor's erroneous runtime-marker
requirement on build logs remain diagnostic. The creator/guard component source
catalogs precede the auditor-only correction; all selected maintained C++ bytes
match current sources. Full CPU/native controls use the final catalog.

Both plans, environment helpers, local heads and indices retain their initial
bytes. Existing controller commits are on GitHub, FireSim first then Chipyard;
remote heads match, with local tracking-ref writes warned after remote success.
No staging or local commits occurred. The complete coherent simulator/FAME/
channel/CPU-managed-stream/other-bridge/functional-memory/runtime cut, process-wide
thread/signal/descriptor/parser exclusion and jointly guarded publication remain
pending. BOOM/Saturn remain pending; standalone Shuttle, physical FPGA validation
and ASIC power remain outside scope. No external dependency is missing.

## Iteration 157: restricted production TSI bridge preparation and publication

Complete Rocket Level 1 remains **in_progress**. The actual `tsibridge_t` now
captures its control plus the restricted sixteen-owner context, prepares a
private fresh TSI/control candidate on the destination creator, and publishes
both together after final checks. Preparation and publication issue no MMIO,
enter no coroutine, and replay no startup/reset. Restored bridge service uses
the owned context continuation. The aggregate checkpoint schema stays empty;
complete CPU restore admission remains disabled. Supported cuts follow bridge
initialization/wait/fast loading and require host and target loading complete.
Earlier bridge phases reject. Recovery: [tsi-bridge-context.md](tsi-bridge-context.md).

The final native ASan/UBSan and VCS matrix and independent audit pass:
**64 fresh bridge restores**, **52,088 complete-owner comparisons**,
**3,000 serial boundaries / 4,652 words**,
**336 invalid-image processes**, **1,326 control byte truncations**,
and **7,555 successive allocation failures** with no publication or MMIO.
All metadata/context/control bytes read back before any edge. Invalid headers,
builds, metadata, missing/duplicate/unknown/reordered owners, malformed lengths,
trailing bytes and cross-owner control phases reject. Consumed, competing and
occupied-destination candidates reject. **10 foreign calls** and **4 late guards**
preserve state and allow creator retries. **8 actual semantic image corruptions** stop
at their independently expected first divergent serial boundary without target
acknowledgement. VCS asserts time zero and zero edges. These are host-component
operation labels, not Rocket target-cycle restores. Sources are independently
retained actual TSI captures; the serial MMIO device is a component fixture.
Continuation follows the production bridge's actual host-termination boundary,
including its remaining queued state, rather than draining artificial later
standalone-protocol operations.

The allocation sweep exposed process setup owners: HTIF can mutate argv and
leave getopt permissiveness on an exception; the installed syscall constructor
can leak duplicated stdio descriptors before its vector construction finishes.
Each private construction now uses owned null-terminated argv, restores all four
exposed getopt globals, and rolls back new descriptors with a retained procfs
directory handle. Every failed attempt compares the complete descriptor table
and parser globals. Dynamic HTIF devices reject before construction. The
installed library is unchanged. Caller-provided exclusive descriptor/parser/
thread/signal suspension remains required; this is not production process-wide
exclusion or a snapshot of libc's private parser continuation/signal actions.

Accepted component receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/bridge-verified/invocation-kzt3ygo7/summary.json`.
Independent audit, twelve missing/duplicate receipt rejections and all
**124** individual source omissions:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/bridge-independent-audit.json`.
The first complete runtime receipt remains failed because its independent
checker interpreted a normalized 32-bit exit word as signed 64-bit. A separate
corrected diagnostic and fresh final invocation preserve that history. Earlier
path/link/fixture, parser and source-epoch failures remain diagnostic.

All **eight** preserved native scopes (**280 Python tests**) and their final
independent archive audit pass, retaining **5,318 artifacts / 854 source bindings**.
Thirty retained auditors pass. All **six full 16-GiB four-hart controls** and
independent audits pass: both direct modes at **C=3,329,794**; all four ordinary/
restricted syscall modes at **C=3,330,050**. Every complete hart trace and decoded
workload label matches within its protocol. Workload SHA-256 values:

- Direct ELF: `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
- Syscall-93 ELF: `1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.

The CPU/native controls have a complete first source catalog. The final bridge
checker has a separate second catalog after correcting only its signed-int
interpretation. Production C++ remains identical throughout both completed
source epochs. Accepted CPU/native receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/rocket-verified/invocation-wauf7071/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/syscall-controls/invocation-wanba8c2/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/native-regressions/invocation-y5pezoks/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/retained-auditor-rechecks/invocation-iy1h_lff/summary.json`.

Fresh independent ordinary RTL VCS replay and the full-source audit pass all
four retained Rocket cuts **C=100 / 700,000 / 900,000 / 3,250,000**: every
**318,637 semantic words** before any edge per cut, **256 events**, sixteen
actual first divergences and 44 invalid cases. Level 2 uses the retained direct
ELF and remains independent of the component restore:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/native-replay/invocation-so72m0uq/summary.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/replay-full-source-audit.json`.

The complete simulator/FAME/channel/other-bridge/functional-memory/runtime cut,
creator-worker pre-edge restore rendezvous and production process-wide exclusion
remain pending. BOOM/Saturn remain pending; standalone Shuttle, physical FPGA
validation and ASIC power remain outside this increment. Both plans, environment
helpers, heads and indices retain their starting bytes. Existing controller
heads were published FireSim first and Chipyard second; only local tracking-ref
writes warned about read-only metadata after remote success. No staging or
local commits occurred. The new work awaits the controller's checkpoint.

Exact executed argv, source catalogs, diagnostics and full artifact paths/hashes:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/verification-commands.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/raw-native-commands.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/native-input-archives.json`,
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/selected-results.json`, `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/summary.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/artifact-manifest.json`.

Executable native checks, from the Chipyard root (each invocation gets fresh outputs):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_bridge_context_vcs \
  --context-summary automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json \
  --recipe-build-identity automations/checkpoint_loop/runs/m11-iteration155/rocket-controls/invocation-53d1qw51/rocket-build-identity.json \
  --out automations/checkpoint_loop/runs/m11-iteration157/bridge-verified
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000,900000,3250000 \
  --out automations/checkpoint_loop/runs/m11-iteration157/native-replay
python automations/checkpoint_loop/runs/m11-iteration157/repeat-native.py
```

Full exact-recipe rebuild, both direct controls, all four syscall modes, every
independent audit and their actual native VCS argv are in the command catalogs
above. They source both environments and `vcs-env.sh` last in every VCS shell.

## Iteration 156: bound context images and fresh creator-side candidates

Complete Rocket Level 1 remains **in_progress**. The restricted TSI context
aggregate now exports canonical owned bytes and prepares a destination-bound
publication candidate on the fresh TSI creator. The envelope binds the supplied
exact build SHA-256, complete canonical startup metadata and all sixteen ordered
owners, including the private lifecycle projection. It rejects malformed lengths,
headers, incompatible builds/metadata, missing/duplicate/unknown/reordered owners
and trailing bytes before publication. Existing payloads retain their schemas.
A complete-context metadata observation supports actual live returned sources;
ordinary polling metadata admission stays unchanged. The adapter does not grant
complete TSI or simulator admission. Recovery:
[tsi-context-images.md](tsi-context-images.md).

The native ASan/UBSan and VCS matrix and primary independent audit pass:
**64 live captures / 128 fresh cross-backend restores**, **136,320 complete-owner
comparisons / 8,388 host operations**, **336 invalid processes**, **8,912 byte
truncations**, and **2,284 successive allocation failures**. Every failing
preparation/publication preserves the metadata-prepared destination without
context entry; successful candidates own their input bytes, reject consumed and
competing publications, read back every owner, and recapture canonical bytes.
Eight foreign-thread calls reject before owner access. Two late mask guards reject
without publication and allow creator retries. All eight actual semantic
corruptions stop at their independently expected first output boundary without
acknowledging that output. VCS asserts time zero and zero RTL edges.

Source processes execute the actual coroutine to each selected host-operation
cut and exit before image imports. All eight retained protocol scenarios cover
startup polling, active serial/syscall requests, cache-flush variants and returned
tails; each selects four cuts. These component cuts are distinct from the Rocket
CPU target-cycle cuts below. The source oracle and every subsequent owner byte
come from the retained independently audited context suite. The component links
the exact recipe's retained iteration-155 lifecycle provider; its complete source
catalog and build-binding digest include the current image/group implementation.
No FCFS whitelist is used to admit CPU state.

Accepted component receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/context-image/invocation-uifjvkhy/summary.json`.
The separate independent auditor also rejects all **fourteen** missing/duplicate
receipt variants and all **99** individual source omissions:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/context-image-independent-audit.json`.
All eight stable native scopes (280 Python tests) and their independent archive
audit pass, preserving 5,317 artifacts and 850 source bindings. Thirty retained
auditors pass. The complete prior context matrix and its independent audit pass
**887 cuts / 3,548 fresh restores / 3,277,056 owner comparisons / 201,268 host
operations**, plus 102 invalid processes, twelve late guards, eight resource
cases, eight first divergences and fourteen evidence rejections. Both backends
reject 1,960 malformed images, 64 membership cases, two cross-owner cases and
927 allocations without publication. Receipts:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/context-regression/invocation-8xj33jgy/summary.json` and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/context-independent-audit.json`.
All **six full 16-GiB four-hart controls and their independent audits pass**:
both direct-exit controls finish at **C=3,329,794**, and all four ordinary/
restricted syscall modes finish at **C=3,330,050**. Every complete hart trace and
decoded workload label matches within its protocol. These remain uninterrupted
CPU controls, independent of component restoration. Exact receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/rocket-controls-stable/invocation-tqd5r683/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/rocket-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/syscall-controls/invocation-3jiqx_49/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/syscall-independent-audit.json`.

The first native invocation ran all eight scopes but rejected source drift during
fixture revision; its accepted stable repeat is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/native-regressions/invocation-v8tzubze/summary.json`.
Initial cut-selection/log-directory, live-return metadata admission and CPU
build source-epoch failures stay diagnostic. Accepted executions use stable
sources and fresh artifacts. Both plans, environment helpers, heads and indices
retain their starting bytes. Existing controller commits reached GitHub FireSim
first and then Chipyard; local tracking-ref writes warned about read-only
metadata after remote success. No staging or local commits occurred.

All exact executed build/runtime argv, source snapshots, selected receipts and
created artifact paths/hashes are cataloged under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/`
in `summary.json`, `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json` and
`artifact-manifest.json`. The catalog retains diagnostic failures separately
from passing selections.

Fresh independent Level-2 replay and its complete-source audit pass at original
Rocket target cuts **C=100/700000/900000/3250000**: **318,637 words / seven clocks
before any edge per cut**, **256 events / 21,760 output comparisons**, **sixteen
actual semantic first divergences** and **44 invalid cases**. Receipts:

- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/native-replay/invocation-lh1s0sup/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/replay-full-source-audit.json`.

The exact Rocket recipe settings remain those listed above. Native checks use
VCS Y-2026.03-SP1, `-full64`, GCC/G++ 13 and both repository environments with
`vcs-env.sh` last; cached Make builds use `VCS_FLAGS=-Mupdate`. No FPGA bitstream
is built. Workload ELF SHA-256 values remain:

- Direct exit: `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`,
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`.
- Syscall 93: `1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`,
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/workload/rocket-quad.riscv`.

Executable native checks from the Chipyard root, each using fresh outputs:

```json
[
  {
    "purpose": "Bound context image capture, fresh import, continuation and rejection matrix",
    "cwd": ".",
    "argv": ["bash", "-lc", "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_tsi_context_image_vcs --context-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration155/rocket-controls/invocation-53d1qw51/rocket-build-identity.json --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156-repeat/context-image"]
  },
  {
    "purpose": "Independent complete image/evidence audit",
    "cwd": ".",
    "argv": ["python", "-m", "tools.checkpoint_formats.tests.audit_tsi_context_image", "--summary", "/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/context-image/invocation-uifjvkhy/summary.json"]
  },
  {
    "purpose": "Four-cut fresh ordinary RTL VCS replay",
    "cwd": ".",
    "argv": ["bash", "-lc", "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156-repeat/native-replay"]
  }
]
```

Next: integrate creator-side image preparation/publication into the complete
simulator restore coordinator, establish production process-wide thread/mask/
action/signal exclusion, and validate one coherent simulator/FAME/bridge/
functional-memory/host CPU cut followed by fresh full Level-1 continuation.
Startup metadata preparation is still a separate operation. Level 2 stays
independent; BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA
validation and ASIC power stay outside scope. No external dependency is missing.

## Iteration 155: freeze software owners before the settled VCS handoff

Complete Rocket Level 1 remains **in_progress**. The production settled driver
diagnostic now captures and validates software owners on their driver creator
while VCS is parked in DPI. Only immutable names, schemas and bytes cross the
settled mutex. The VCS callback adds its harness observation without invoking
the original software owners. Unsupported records remain explicit; frozen
observations always reject loading. Diagnostic and owner schemas are unchanged.
Recovery: [driver-owner-snapshots.md](driver-owner-snapshots.md).

The new actual-TSI native ASan/UBSan and VCS checks pass at execution and
returned-tail component boundaries: **four processes / 128 complete owner
readbacks**, **1,544 successive allocation failures** with unchanged creator
state and successful retry, **64 direct foreign-reference rejections**, and
**128 each of invalid-image and mutable-load rejections**. All sixteen public
owners match the independently executed context oracle, including the separate
pristine ordinary memory reader. Both parked and post-creator-destruction
readbacks match; VCS asserts time zero and zero edges. This observes public
components; it does not replace the aggregate's private lifecycle/signal owner.
The accepted receipt is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration155/snapshot-final/invocation-7zj4kqy2/summary.json`.
The source catalog binds the full original list, including auxiliary headers.
The independent audit rejects all six missing/duplicate receipt variants and
all **96 individual source-binding omissions**; its result is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration155/snapshot-final-independent-audit.json`.
The initial auditor omission failure remains diagnostic; the corrected verifier
and auditor use a separate source epoch and fresh native/VCS output directory.
Production C++ bytes stay identical across both epochs.

| Check | Result / artifact under `runs/m11-iteration155/` |
| --- | --- |
| Original diagnostic guards and frozen inventory validation | Pass: 96 native ASan/UBSan rejections; `diagnostic-native.log` |
| Retained creator/view access and independent evidence audit | Pass: 500 processes / 125 operations; six missing/duplicate variants reject; `thread-access/invocation-cpxe6n4_/summary.json` |
| Production settled FCFS handoff, both clock phases | Pass: five cuts per phase, complete generated-state and target token/AXI trace comparison, outstanding native memory traffic, terminal cut and eleven invalid requests; `settled-high/summary.json`, `settled-low/summary.json` |
| Preserved complete native scopes and independent archive audit | Pass: eight scopes / 280 Python tests / 5,313 retained artifacts / 846 source bindings; `native-regressions/invocation-mjel1ubo/summary.json` |
| Retained independent auditors | Pass: all thirty; `retained-auditor-rechecks/` |
| Exact Rocket recipe / two complete direct-exit CPU controls | Pass: both C=3,329,794, full 16-GiB memory and all four hart traces; `rocket-controls/invocation-53d1qw51/summary.json` |
| Four complete ordinary/restricted syscall-93 CPU controls | Pass: all C=3,330,050, full 16-GiB memory and sixteen hart traces; `syscall-controls/invocation-j60m2f47/summary.json` |
| Independent Level-2 ordinary RTL VCS replay and complete-source audit | Pass: four cuts, 318,637 words / seven clocks before any edge per cut, 256 events / 21,760 output comparisons, sixteen real semantic first divergences and 44 invalid cases; `native-replay/invocation-saxubo1c/summary.json`, `replay-full-source-audit.json` |

FCFS diagnostic cuts are completed host operations **3, 11, 699275, 699276**
and randomized operation **101**. They preserve final target labels **774628**
and **774632**, respectively. These are separate from the retained Rocket
Level-2 target cuts **C=100/700000/900000/3250000**. Neither the component
handoff nor uninterrupted CPU controls establish a restored CPU execution.

Exact recipe settings remain those listed above. VCS uses Y-2026.03-SP1,
`-full64`, cached-build `-Mupdate`, GCC/G++ 13 and both repository environments
with `vcs-env.sh` last. No FPGA bitstream is built. Workload ELF SHA-256 values:

- Direct exit: `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`,
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`.
- Syscall 93: `1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`,
  `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/workload/rocket-quad.riscv`.

Exact executed build/simulation argv, independent audits, source epochs and full
created artifact paths/hashes are cataloged under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration155/`
in `verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json`, `selected-results.json`, `artifact-manifest.json`
and `summary.json`. Both plans, environment helpers, local heads and indices
retain their starting bytes. Existing controller checkpoints reached GitHub
FireSim first and then Chipyard, with read-only local tracking-ref warnings.
No staging or local commits occurred.

Executable native checks from the Chipyard root; repeated executions allocate
fresh invocation directories:

```json
[
  {
    "purpose": "Actual TSI immutable creator-to-VCS handoff",
    "cwd": ".",
    "argv": ["bash", "-lc", "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_tsi_snapshot_vcs --context-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration155/rocket-controls/invocation-53d1qw51/rocket-build-identity.json --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration155-repeat/snapshot"]
  },
  {
    "purpose": "Four-cut fresh ordinary RTL VCS replay",
    "cwd": ".",
    "argv": ["bash", "-lc", "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration155-repeat/native-replay"]
  }
]
```

Next: connect creator-side TSI capture and fresh creator-side preparation and
publication to complete simulator restoration, supply production process-wide
thread/mask/action/signal exclusion, then validate coherent simulator/FAME/
bridge/functional-memory CPU cuts and fresh full Level-1 target-cycle
continuation. The TSI bridge's aggregate schema remains unsupported. BOOM and
Saturn remain pending; standalone Shuttle, physical FPGA validation and ASIC
power stay outside scope. No external dependency is missing.

## Iteration 154: guard retained TSI owner references

Complete Rocket Level 1 remains **in_progress**. All sixteen public TSI owner
references now enforce the live creator at every checkpoint method, including
references borrowed before aggregate publication. Views follow actual optional
owner slots, allocate no storage and preserve all serialized owner schemas.
Recovery: [tsi-owner-views.md](tsi-owner-views.md).

The native ASan/UBSan and VCS matrix passes **500 processes / 125 operations**
at execution and returned-tail cuts: the original 45 entries plus five methods
on each of sixteen retained owners. Every foreign operation rejects before
owner access; complete readback and valid creator retries match the independent
context oracle. All six missing/duplicate evidence variants reject. The receipt
is `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154/thread-access/invocation-1ojny_2f/summary.json`.

The separate native/VCS lifetime check passes **128 actual recycled thread IDs /
640 expired-view operations**, ten foreign operations and ten absent-slot
operations, slot replacement and valid creator retries. No rejected operation
reaches its underlying owner. Its receipt is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154/lifetime/invocation-yj6ncrkj/summary.json`.
The same production access harness compiled with archived iteration-153 sources
reproduces sixteen expected failures across both boundaries and backends:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154/prior-view-witness/invocation-5af5yicv/summary.json`.
These are component-operation cuts, not Rocket target cycles.

The full fourteen-owner lifecycle regression passes 3,872 fresh readbacks,
1,105,584 host operations, 256 pending-exit continuations, 96 stopped restores,
64 first-divergence cases and all malformed/cross-owner/allocation/late-guard
cases. Its late terminal-cursor fault now uses a validated component image;
owner observations no longer expose a concrete terminal for downcasting.
The complete 720-case admission matrix, 686-case signal/thread suite, eight
native scopes (280 Python tests), thirty retained auditors and fresh four-cut
ordinary RTL VCS replay also pass. The complete context suite and independent
audit pass **887 cuts / 3,548 fresh restores / 3,277,056 owner comparisons /
201,268 operations**, 102 invalid processes, twelve late guards, eight resource
cases, eight first divergences and fourteen missing/duplicate evidence
rejections. Each backend rejects 1,960 malformed images, 64 membership variants,
two cross-owner inconsistencies and 927 successive allocation failures without
partial publication. Receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154/context-regression/invocation-saf8lf7z/summary.json`.
All six complete **16-GiB four-hart CPU controls and independent audits pass**:
both direct-exit controls finish at **C=3,329,794**, and all four ordinary/
restricted syscall-93 controls finish at **C=3,330,050**. Complete hart traces
and decoded workload labels match within each protocol. Direct controls:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154/rocket-stable/invocation-3p7m8gvx/summary.json`.
Syscall controls:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154/syscall-controls/invocation-a3o1o5l7/summary.json`.
These are uninterrupted controls, not complete Level-1 CPU restores.

Fresh ordinary RTL VCS and the complete-source audit pass **C=100/700000/
900000/3250000**: all **318,637 words / seven clocks before any edge** per cut,
256 captured events / 21,760 output comparisons, sixteen actual semantic first
divergences and 44 invalid cases. Receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154/native-replay/invocation-xndqb2ih/summary.json`.
The replay uses the independent retained direct-exit ELF.

Exact selected receipts, native build/simulation argv, immutable source epochs,
full created artifact paths and hashes are cataloged under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154/`
in `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `artifact-manifest.json`
and `summary.json`. Existing controller heads were pushed FireSim first and then
Chipyard; read-only local tracking refs warned after remote success. Both plans,
environment helpers, local heads and indices retain starting bytes. No staging,
local commits, reset or cleanup occurred.

The exact recipe settings above and both retained workload hashes are unchanged.
VCS uses Y-2026.03-SP1, `-full64`, `-Mupdate`, GCC/G++ 13, both repository
environments and `vcs-env.sh` last. The initial CPU/native source-snapshot drift
failures stay diagnostic; stable-source reruns use fresh directories.

Executable native checks from the Chipyard root (fresh output roots):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_thread_access_vcs \
  --context-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json \
  --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154/rocket-controls/invocation-8rzm9whm/rocket-build-identity.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154-repeat/thread-access
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000,900000,3250000 \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration154-repeat/native-replay
```

Process-wide signal/thread/mask/action exclusion and complete simulator aggregate
restoration remain pending. TSI state must be serialized on its driver creator
before handoff to the separate low-clock VCS callback. This access change does
not enable complete CPU checkpointing. BOOM and Saturn remain pending;
standalone Shuttle, physical FPGA validation and ASIC power stay outside scope.

## Iteration 153: confine supported TSI access to its original thread

Complete Rocket Level 1 remains **in_progress**. Restricted aggregate inspection,
preparation, commit and continuation now reject a foreign OS thread before
reading mutable owner state. Production serial/load-memory entries, host-control
access and owner-reference getters enforce the same policy. A weak thread-local
lifetime token rejects recycled creator IDs. These resources are process-local;
all serialized owner schemas stay unchanged. Recovery:
[tsi-thread-access.md](tsi-thread-access.md).

The new native ASan/UBSan and VCS matrix passes 180 fresh processes: 45 entries
at execution and returned-tail outer boundaries. Exact prepared candidates get
valid creator retries. The twelve-owner commit uses ordinary sealed polling;
the fourteen-owner syscall candidate uses its supported execution cut even when
the outer group is at returned tail. Larger groups retain their complete
stop/return ownership. Every tested foreign entry rejects before service or
context creation; complete owner bytes and creator continuation match the
independently executed parent coroutine. This is host-operation component
coverage, not Rocket target-cycle checkpoint continuation.

Selected native access receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration153/thread-access-final/invocation-otnosc2h/summary.json`.
The independent negative-evidence checker initially raised KeyError for a missing
build command; a structured membership check now rejects it explicitly. Its
corrected full audit passes all 180 entries and six incomplete-evidence cases.
Initial fixture compilation, ordinary-mode and completed-stop boundary mistakes
stay diagnostic; no accepted native evidence
or prior-iteration artifact is rewritten.

| Check | Current result |
| --- | --- |
| New 45-entry access matrix | 180 native/VCS processes and six incomplete-evidence rejections pass |
| Creator lifetime sensitivity check | Pass: 128 actual recycled-ID attempts rejected; 130 live-creator accesses succeed |
| Actual signal/thread provider and independent audit | Pass: 686 processes and all worker/shared-policy transactions |
| Fresh ordinary RTL VCS and complete-source independent audit | Pass: C=100/700000/900000/3250000; 318,637 words before any edge per cut; 256 events; sixteen semantic first boundaries; 44 invalid cases |
| Thirty retained auditors | Pass |
| Stable-source aggregate admission and independent audit | Pass: 360 current cases, 300 prior witnesses, 60 prior controls and six evidence rejections |
| Stable-source eight native scopes | All eight scopes, 280 Python tests and independent artifact audit pass |
| Complete syscall-93 controls and independent audit | Pass: all four modes at C=3,330,050; sixteen full hart traces and labels match |
| Stable-source full context suite and independent audit | Pass: 887 cuts / 3,548 restores / 3,277,056 comparisons / 201,268 host operations; 102 invalid processes, twelve late guards, eight resources, eight first divergences and fourteen evidence rejections |
| Stable-source complete direct-exit controls | Both controls and independent audit pass at C=3,329,794 |

The complete context receipt is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration153/context-stable/invocation-mrl1ypcu/summary.json`.
It also rejects 1,960 malformed images, 64 owner-membership variants, two
cross-owner inconsistencies and 927 successive allocation failures per backend,
without partial publication. The direct controls are retained at
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration153/rocket-stable/invocation-s_i4udu3/summary.json`;
the four syscall controls at
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration153/syscall-controls/invocation-rk2vqnnd/summary.json`.
All six use full 16-GiB backing memory and exercise all four harts. The captured
ordinary RTL replay remains independent and uses the retained direct-exit ELF.

A final test-only declaration reorder keeps each auxiliary TSI alive until its
prepared candidate is destroyed. Its final 180-process access matrix and all six
independent missing/duplicate evidence rejections pass.
Completed production/native/context receipts keep their original execution
snapshots; production code is unchanged across these fixture epochs. The source
catalog retains each receipt's bindings rather than rewriting earlier evidence.

The recipe settings above, direct workload SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`
and syscall workload SHA-256
`1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`
remain exact. The actual recipe provider archive and compiler dependencies bind
the new production header. Builds use VCS Y-2026.03-SP1, `-full64`, `-Mupdate`,
system GCC/G++ 13 and both repository environments with `vcs-env.sh` sourced last.
No bitstream is built.

Exact selected receipts, native build/simulation argv, source snapshots from
both fixture epochs, and every created artifact path/hash are cataloged under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration153/`
in `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `artifact-manifest.json`
and `summary.json`. The native core artifact audit passes again after the final
fixture reorder. Existing controller heads were pushed FireSim first and then
Chipyard; local tracking-ref updates warned about read-only git metadata after
remote success. Plans/environment helpers, local heads and indices retain their
starting bytes. No staging or local commits occurred.

Executable native checks from the Chipyard root (use fresh output roots):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_thread_access_vcs \
  --context-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json \
  --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration153/rocket-controls/invocation-agekim45/rocket-build-identity.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration153-repeat/thread-access
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000,900000,3250000 \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration153-repeat/native-replay
```

Supported-entry confinement does not suspend foreign VCS workers, coordinate
signals/actions/masks or authorize inherited HTIF methods and retained raw owner
references. Process-wide production exclusion and coherent simulator/FAME/bridge/
functional-memory publication remain pending. Complete CPU Level 1 stays
disabled. Level 2 remains independent retained direct-workload replay. BOOM and
Saturn remain pending; standalone Shuttle, physical FPGA validation and ASIC
power remain outside this increment.

## Iteration 152: connect aggregate admission to the all-thread provider guard

Complete Rocket Level 1 remains **in_progress**. The actual build-local lifecycle
provider now calls the existing delivered-signal provider's all-thread and
exact-action guard. Restricted polling, fifteen-owner host and sixteen-owner
context aggregates therefore audit every task's blocked INT/TERM/ABRT mask,
thread-local/shared pending signals and stable membership, as well as the
provider's exact installed signal actions. This runs at capture, preparation,
final publication and before fresh or initialized coroutine resume. Delivered
signals remain unsupported by these aggregates. The owner images are unchanged.
Recovery: [tsi-context-signal-admission.md](tsi-context-signal-admission.md).

The new matrix covers five aggregate operations, execution and returned-tail
boundaries, six real worker/action faults, all three signals and native ASan/UBSan
plus VCS. It compares all sixteen restored images before any service and retries
against an independently executed coroutine oracle. Its two real workers stay
parked and alive through repair. There are 360 current-provider admission cases,
300 prior-provider worker/action sensitivity witnesses and 60 prior shared-pending
controls. The old calling-thread check already rejects shared pending signals.

Fresh exact-recipe native build identity:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152/rocket-controls/invocation-ia5s6e20/rocket-build-identity.json`.
It uses the exact settings above, VCS Y-2026.03-SP1, `-full64`, `-Mupdate`, system
GCC/G++ 13, and the actual newly linked provider archive. No FPGA build is run.
The retained direct workload ELF hash is
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`;
the independently retained syscall-93 workload ELF hash is
`1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.
Both workloads still exercise all four harts' real memory computations.

| Check | Current result |
| --- | --- |
| Exact-recipe signal/thread provider regression and independent audit | Pass: 686 native processes, six threaded captures, twelve threaded restores, 24 worker/shared-policy transactions |
| Fresh ordinary RTL VCS and complete-source independent audit | Pass: C=100/700000/900000/3250000; 318,637 words before any edge per cut; 256 captured events; sixteen real semantic first divergences; 44 invalid cases |
| New aggregate admission matrix and independent audit | Pass: 360 current admission cases, 300 prior witnesses, 60 prior shared-pending controls; six missing/duplicate evidence variants reject |
| Full sixteen-owner native/VCS context continuation and independent audit | Pass: 887 host-operation cuts / 3,548 fresh restores / 3,277,056 owner comparisons / 201,268 operations; all 102 invalid processes, twelve late guards, eight resources, eight first divergences and fourteen incomplete-evidence rejections |
| Eight native core scopes | Final fixed-input run and independent artifact audit pass all eight scopes (280 Python tests); earlier changed-input receipts reject |
| Six full-memory four-hart CPU controls and independent audits | Pass: both direct controls at C=3,329,794 and all four ordinary/restricted syscall controls at C=3,330,050; complete hart traces and decoded labels match within each protocol |
| Thirty retained auditors | Pass |

Accepted aggregate receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152/admission-accepted/invocation-b6_40pk6/summary.json`.

The source signal/thread suite and complete-source Level-2 audit are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152/`.
Selected receipts, complete artifact/source catalogs and executable native
argv are recorded there in `selected-results.json`, `artifact-manifest.json`,
`native-input-archives.json`, `raw-native-commands.json` and
`verification-commands.json`.

Accepted complete context receipt:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152/context-accepted/invocation-88_6m1gp/summary.json`.
Both backends reject 1,960 malformed component images, 64 owner-membership cases,
two cross-owner inconsistencies and 927 successive allocation failures without
partial publication. The worker remains parked through the foreign-creator
readback; no guarded provider inspection follows its join. The separate lifetime
pilot passes twenty fresh native/VCS checks. Source snapshots retain the exact
execution epochs before and after this test-only fixture change; all accepted
native artifacts and all earlier-iteration artifacts remain intact.

The exact-recipe CPU receipts are:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152/rocket-controls/invocation-ia5s6e20/summary.json`
and
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152/syscall-controls/invocation-mkcp87z3/summary.json`.
The latter archives all native input/executable bytes and all sixteen hart traces.
Ordinary RTL VCS replay and its complete-source audit are bound by:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152/native-replay/invocation-541mjma5/summary.json`
and `native-replay-full-source-audit.json` in the iteration root.

Use a fresh output root for repetition. The saved command catalog records the
actual executed argv; the following are executable native VCS checks from the
Chipyard root, including the test-only runtime mask controller:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_context_threads_vcs \
  --context-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json \
  --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152/rocket-controls/invocation-ia5s6e20/rocket-build-identity.json \
  --prior-recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/rocket-controls/invocation-rso6xoh0/rocket-build-identity.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152-repeat/admission
python automations/checkpoint_loop/runs/m11-iteration152/run-context-masked.py \
  --host-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/host-final/invocation-2uwuywgo/summary.json \
  --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152/rocket-controls/invocation-ia5s6e20/rocket-build-identity.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152-repeat/context
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000,900000,3250000 \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152-repeat/native-replay
```

Test-only parking and inherited masks do not supply production exclusion.
Procfs inspection cannot prevent concurrent thread, mask/action or signal changes
after inspection. Production coordination and coherent simulator/FAME/bridge/
functional-memory publication remain pending, as does complete fresh-process
Rocket target-cycle continuation. CPU Level 1 remains disabled. Level 2 remains
the independent retained direct-exit-workload replay; there is no syscall-workload
Level-2 capture claim. BOOM/Saturn remain pending. Standalone Shuttle, physical
FPGA validation and ASIC power remain outside scope.

## Iteration 151: self-checking CPU workload on the restricted syscall path

Complete Rocket Level 1 remains **in_progress**. A separately generated syscall-93
variant preserves every four-hart computation in the retained workload and
replaces its final odd HTIF exit store with eight explicit request words, a
memory fence, and an aligned request-pointer publication. Each hart still checks
its own 64 KiB through early initialization, warm sequential validation, permuted
cache-line read/modify/write rounds and late validation. A compiler-backed Spike
matrix checks the success image and actual memory faults on all four harts.
The retained direct-exit source/images remain intact. Fresh direct builds pass
all five Spike checks and match every loadable byte of the retained images;
temporary compiler FILE symbols cause ELF-file hash differences.

The new native matrix runs the syscall image through ordinary and restricted
HTIF, both with ordinary and buffered observers. Each fresh VCS process has a
full 16-GiB backing memory. The selected exact-recipe Y-2026.03-SP1 build is
unchanged from iteration 150, with all native inputs rechecked before and after
execution and the executable/input bytes archived in this invocation. Both
repository environments and `vcs-env.sh` are sourced in every VCS shell.
There is no new FPGA build. A test-only launcher blocks SIGINT/SIGTERM/SIGABRT
before exec and VCS worker creation; it does not provide production signal
coordination or delivered-signal restoration.

The independent CPU decoder requires actual hart-zero stores of all eight
request words `[93,0,0,0,0,0,0,0]` before the sole tohost pointer store. It also
checks all four harts' real phase/completion/failure stores. The independent
matrix audit compares complete four-hart TracerV files and all decoded CPU
instruction/store cycle labels across the four modes, validates the native
build/protocol/argv/process bindings and every archived artifact. These are
uninterrupted workload controls, not restored CPU checkpoints.

Workload ELF:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/workload/rocket-quad.riscv`,
SHA-256 `1c5ebf741af82848ebfcba5194e4c813dce3cdc8aadc7ecae2ba454280604958`.
Compiled source SHA-256:
`3642c1fe901b5fd11791bf7b7ee51db727b8d795bf081803f2352f95f7250697`.

| Executed check | Result |
| --- | --- |
| Four complete exact-recipe 16-GiB native VCS controls | Ordinary/restricted HTIF, each with ordinary/buffered observers; all finish at C=3,330,050 |
| Complete CPU trace/label comparison | All sixteen full hart trace files match; all four harts' computation/phase/completion/failure stores and the request/pointer labels match |
| Independent CPU evidence audit | Complete native/build/source/protocol bindings and re-decoding pass; nine missing/duplicate/false-acceptance evidence variants reject |
| Actual request construction | Eight BSS-zero stores before computation, then eight ordered syscall words after every hart completes and before the sole pointer publication; all four executions pass |
| Spike workload/fault matrix | Success and four real hart-memory corruptions pass for both direct and syscall variants; all five direct load images match retained bytes |
| Fresh sixteen-owner native/VCS context regression | Eight scenarios / 887 host-operation cuts / 3,548 fresh restores / 3,277,056 comparisons / 201,268 operations; 102 invalid processes, twelve late guards, eight resources and eight first divergences pass |
| Independent context audit | All current recipe/provider bindings pass; fourteen missing/duplicate evidence variants reject |
| Eight native core scopes / thirty retained auditors | Pass, including all 280 Python tests and complete artifact/source audits |
| Fresh ordinary RTL VCS, retained C=100/700000/900000/3250000 | 318,637 semantic words read back before any edge per cut; 256 events / 21,760 output comparisons; sixteen actual semantic faults and 44 invalid cases; complete-source independent audit passes |

Selected controls:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/accepted-controls/invocation-36jsobc5/summary.json`.
Actual four native executions, argv, logs and sixteen full traces:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/syscall-controls/invocation-a6oe1ba6/`.
Context regression:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/context-regression/invocation-93o7agr0/summary.json`.
Ordinary RTL replay:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/native-replay/invocation-zcwq63zu/summary.json`.
The independent CPU evidence audit and all nine incomplete/duplicate evidence
rejections pass. Exact argv/cwd and native processes are cataloged in
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/verification-commands.json`
and `raw-native-commands.json`; all source archives and created artifact paths
are in `native-input-archives.json` and `artifact-manifest.json` in that same
directory. Selected receipts are bound in `selected-results.json`. Recovery:
[rocket-syscall-workload.md](rocket-syscall-workload.md).

The initial decoder counted BSS initialization as extra runtime request stores.
The corrected decoder checks both groups explicitly. The original harness's
input-drift guard rejects because its observer inputs changed during execution;
its failed summary remains intact. Fresh checker processes re-audit the four
completed successful native executions, binding all original native artifacts
and source snapshots plus the corrected checker bytes in a new invocation.
A first reuse audit falsely required PID numbers to remain distinct across
native and later checker launch namespaces. The accepted audit checks uniqueness
within each launch phase and independently binds every argv/log/runtime. An
initial launch also had a harness NameError before any VCS process ran. These
attempts are diagnostic; no failed report is rewritten or selected as passing.
All sixteen full traces match and all four native processes passed at the same
cycle before this observer repair. No CPU execution was omitted or repeated to
repair the checker.

The test mask does not connect the separate signal-owner all-thread audit to the
restricted aggregate's calling-thread lifecycle guard. Both production exclusion
and that admission connection remain pending. Complete Rocket Level 1 is still
disabled. The four-cut Level-2 result uses the retained original direct-exit
workload/capture; the new syscall workload has no Level-2 capture/replay claim.
Simulator/FAME/bridge/functional-memory coherent capture and fresh complete CPU
continuation are pending. BOOM/Saturn remain pending.

From Chipyard root, use a fresh output root for a new native matrix (the selected
artifact's `raw-native-commands.json` catalog retains the exact commands already
executed):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_workload \
  --exit-protocol syscall93 \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151-repeat/workload
python -m tools.checkpoint_formats.tests.verify_rocket_syscall_vcs \
  --build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/rocket-controls/invocation-rso6xoh0/rocket-build-identity.json \
  --workload /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151-repeat/workload \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151-repeat/controls
python -m tools.checkpoint_formats.tests.audit_rocket_syscall \
  --summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/accepted-controls/invocation-36jsobc5/summary.json
```

The actual accepted recovery command adds
`--completed-controls /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration151/syscall-controls/invocation-a6oe1ba6/summary.json`
to re-audit all four immutable native executions without advancing a target edge.
This path accepts only four successful, command-bound native result logs with
matching recipe/workload/build identities; it preserves the failed original
aggregate report and records all original bytes separately. The independent
auditor verifies both native and new checker artifact memberships and hashes,
then decodes all four real CPU logs again.

## Iteration 150: semantic wrapper and fresh restricted coroutines

Complete Rocket Level 1 remains **in_progress**. The new sixteen-owner
transaction includes `firesim.tsi.host-wrapper.v1`, with fresh/execution/tail
phases. It binds an execution wrapper to a polling outer caller and a tail
wrapper to a returned outer caller. Startup and component-only stop/return
intermediate cuts reject. All replacements prepare before guarded nonthrowing
publication. Complete readback precedes native coroutine creation; explicit
component `resume()` reconstructs the audited wrapper/run_host frames without
startup/reset/program replay. Ordinary restored `tick()` remains disabled.
See [tsi-context-continuation.md](tsi-context-continuation.md).

The base adapter enforces its original target/creator context before allocation
or service entry. The actual provider guards continuation before first entry
and after suspension. Production signal coordination, the retained workload's
direct-exit wrapper/outer integration, complete simulator/FAME/bridge/memory
publication and fresh Rocket target-cycle Level-1 continuation remain pending.
The sixteen-owner API dispatches restricted syscall 93 and owns no ordinary
syscall session. Its source fixture is a host protocol fixture, with explicit
host-operation cuts, not CPU target-cycle checkpoints.

Diagnostic root: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/`.
The exact six recipe settings above are read from the YAML for the rebuilt
VCS metasim, retaining 140 MHz and TIMING strategy without a bitstream. Both
environments are sourced, then `vcs-env.sh` last: Y-2026.03-SP1, `-full64`,
GCC/G++ 13 and `VCS_FLAGS=-Mupdate`. The final component suite uses the exact
provider archive linked in this current-recipe executable.

| Executed check | Result |
| --- | --- |
| Complete sixteen-owner fresh native ASan/UBSan and VCS context matrix, both backend directions | Eight scenarios; 887 host-operation cuts; 3,548 fresh restores; 3,277,056 complete owner comparisons; 201,268 continued operations |
| Actual source and fresh wrapper contexts | Sixteen actual sources; complete captured bytes agree with the independently executed fifteen-owner parent; every destination reads all sixteen owners before context creation and matches every continued owner byte; three unchanged tail ticks per continuation |
| Atomic format/membership/cross-owner/allocation scope | Both backends: `malformed=1960 membership=64 cross=2 allocation_failures=899 unchanged_on_failure=1 context_entries=0`; all truncations/configuration/trailing bytes, owner membership and wrapper/outer phase mismatches reject before publication |
| Fresh invalid-image processes / late guards | 102 invalid processes and twelve actual wrapper/peer/exit/stop/mask/pending guards reject before publication/context entry |
| Context creator / stack allocation / continuation signal guards | Eight processes: foreign-thread rejection, actual 1 MiB stack-allocation failure with unchanged owners and successful retry, and blocked-mask/pending-signal rejection before first entry and after suspension |
| Actual semantic corruption | Eight syscall/write-child corruptions report the first divergent outgoing word without consuming it, after fresh coroutine reconstruction |
| Independent context evidence audit | Full bytes and actual process/argv/cwd checked against the separately executed parent; fourteen missing/duplicate evidence variants reject |
| Full current-recipe polling / host / outer regressions | 3,452 / 3,580 / 160 fresh restores respectively; complete previous scope and independent audits pass |
| Recipe-bound syscall / signal-thread suites | 1,200 restores / 686 processes; all-thread guards and independent audits pass |
| Legacy polling/direct exits | 3,872 fresh readbacks; 1,105,584 operations; 256 pending-exit continuations and 96 stopped restores; independent audit passes |
| Context lifetime / actual bridge transport | All 278 stacks released per backend; six fatal lifetime rejections; 1,012 direct requests / 566,096 compared records, four actual bridge runs, 32 invalid requests and 24 control readbacks pass |
| Eight core native scopes / thirty retained auditors | Passed, including all 280 Python tests; selected native scopes independently audited |
| Fresh ordinary pre-FAME RTL VCS at C=100/700000/900000/3250000 | 318,637 words before any edge per cut; 256 captured events / 21,760 output comparisons; sixteen semantic faults and 44 invalid cases; independent audit passes |
| Exact-recipe default/buffered four-hart controls | Full 16-GiB backing each; both complete at C=3,329,794; all eight full hart traces and workload/store labels match uninterrupted references |

Accepted artifacts:

- Context matrix: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/context-final/invocation-kuad914v/summary.json`.
- Independent context audit, including fourteen evidence rejections: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/context-independent-audit.json`.
- Actual current build/source identity: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/rocket-controls/invocation-rso6xoh0/rocket-build-identity.json`; complete CPU controls: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/rocket-controls/invocation-rso6xoh0/summary.json`.
- Current polling parent: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/recipe-polling/invocation-z12o1hlz/summary.json`; fifteen-owner regression: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/host-regression/invocation-xluzx7ih/summary.json`; ordinary RTL replay: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/native-replay/invocation-u2zqrbcs/summary.json`.
- All selected summaries and independent receipts: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/selected-results.json` and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/*-independent-audit.json`.
- Exact executable argv/cwd: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/verification-commands.json`; individual native processes: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/raw-native-commands.json`.
- Immutable native inputs and every created artifact path: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/native-input-archives.json` and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/artifact-manifest.json`.

The CPU workload remains
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The separate host fixture is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/recipe-polling/invocation-e8aco1wi/polling.elf`,
SHA-256 `c51741a10138ca4ee2661a06bcdf250e04bb844f0f2be1ffdd36e247dc1a3993`.
The final context suite's source metadata and all component cut bytes are
retained in its invocation. The source-coroutine fixture and complete metasim
CPU controls are separate checks. No complete fresh CPU Level-1 continuation is
claimed. Independent Level-2 replay continues using the complete retained
ChipTop captures and trace at the four original cycle labels.

The initial context pilot uses superseded test/resource-guard inputs and is
diagnostic only. Its original late-exit test incorrectly tried to inspect a
syscall caller after deliberately making its provider incoherent; the corrected
test observes unaffected peers without saving that incoherent caller. An initial
diagnostic preflight had an import-path error; the corrected preflight passes
every scenario and eleven negative/resource
modes. All selected final scopes run completely with fixed current inputs.
ASan emits its documented `makecontext`/`swapcontext` support warning; explicit
resource accounting and native VCS context continuations also pass. Both plan
files and environment helpers retain their starting bytes. Existing controller
heads reached remote GitHub main branches, FireSim first, with local tracking-ref
write warnings after remote success. No staging or local commits. The first
catalog attempt expected an optional hash missing from the legacy descriptor
receipt; the accepted catalog binds its actual command and verified polling
summary. The initial failure is retained separately.

Run from Chipyard root, creating fresh invocation directories:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_context_group_vcs \
  --host-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/host-final/invocation-2uwuywgo/summary.json \
  --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/rocket-controls/invocation-rso6xoh0/rocket-build-identity.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/repeat-context
python -m tools.checkpoint_formats.tests.audit_tsi_context_group \
  --summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/context-final/invocation-kuad914v/summary.json
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/repeat-native-replay
```

Next: integrate the retained workload's direct-exit wrapper/outer path or use a
separately hashed self-checking syscall-93 CPU workload; coordinate production
signals; publish a coherent complete simulator/FAME/bridge/functional-memory
checkpoint and validate fresh Rocket CPU Level-1 target-cycle continuation.
BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA validation and
ASIC power remain outside scope. No external dependency is missing.

## Iteration 149: restricted outer/polling/provider aggregate

Complete Rocket Level 1 remains **in_progress**. The ordered fifteen-owner
transaction restores the twelve sealed polling owners, syscall-93 caller,
actual provider lifecycle and explicit outer caller. It rejects startup,
incompatible outer/polling/stop phases and a returned result that disagrees with
the installed provider's signed value before publication. Stop permits only a
completed syscall read/write/response child and completed polling. The previous
fourteen-owner group retains its stopped-provider rejection. See
[tsi-host-aggregate.md](tsi-host-aggregate.md) for exact state ownership.

All candidates own their replacement state and bind the fresh destination.
Publication rechecks metadata, pristine caller/outer/protocol, absent dormant
proxy/session resources and actual provider signal/lifecycle guards before
nonthrowing peer/provider assignment. Continuation invokes production poll,
stop and return services without startup or context entry. `tick()` remains
unsupported after restoration. The wrapper/context, production signal coordinator,
complete inherited-session policy and simulator/FAME/bridge/memory transaction
remain pending. No complete CPU checkpoint profile is enabled.

Diagnostic root: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/`.
The exact six Rocket recipe settings above are read from the current YAML for
the rebuilt VCS metasim; frequency 140 MHz and TIMING strategy are retained.
VCS Y-2026.03-SP1 uses `-full64`, `VCS_FLAGS=-Mupdate`, system GCC/G++ 13
and the VCS helper sourced last. No FPGA bitstream is built.

| Executed check | Result |
| --- | --- |
| Complete fifteen-owner fresh native ASan/UBSan and VCS matrix, both backend directions | Eight scenarios; 895 host-operation cuts; 3,580 restores; 3,125,940 complete owner comparisons; 204,816 continued operations |
| Actual production source coroutine | Sixteen sources; all polling images independently match the separate fourteen-owner parent; actual returned images and three tail ticks per source match |
| Component stop/return boundaries | Pending final response, drained response, stopped provider before return collection, and returned signed result all restore independently |
| Atomic format/membership/cross-owner/allocation scope, each backend | `malformed=1910 membership=60 cross=5 allocation_failures=868 unchanged_on_failure=1` |
| Fresh invalid-image processes | 102: per-owner truncation/configuration/trailing bytes and six individually parseable incompatible parent/provider/result combinations; no partial publication |
| Late destination/provider guards | Twelve: outer, serial peer, actual exit, actual stop, blocked-mask change and pending signal; repaired mask/pending candidates retry completely |
| Actual semantic corruption | Eight syscall argument/write-child faults detected at their first outgoing word, unconsumed |
| Independent aggregate evidence audit | Complete owner bytes, actual argv/cwd/processes and cross-backend sources checked; twelve missing/duplicate evidence variants reject |
| Full recipe-bound polling parent | 863 cuts / 3,452 fresh restores / 2,768,080 owner comparisons / 190,816 operations; all existing idle, malformed, membership, allocator, admission, late-guard and first-divergence scope passes |
| Recipe-bound syscall / signal-thread / outer regressions | 1,200 restores / 686 processes / 160 restores respectively; passed |
| Legacy polling/direct exits | 3,872 fresh readbacks; 1,105,584 continued operations; 256 pending-exit continuations and 96 stopped restores; passed |
| Eight native core suites / thirty retained auditors | Passed; all selected suites independently audited |
| Fresh ordinary pre-FAME RTL VCS at C=100/700000/900000/3250000 | 318,637 words before any edge per cut; 256 events / 21,760 output comparisons; sixteen actual semantic faults and 44 invalid cases; passed independent audit |
| Exact-recipe default/buffered four-hart controls | Full 16-GiB backing each; both pass at C=3,329,794; all eight complete hart traces and workload/store labels match |

Accepted artifacts:

- Aggregate: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/host-final/invocation-2uwuywgo/summary.json`.
- Polling parent: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/recipe-polling/invocation-e8aco1wi/summary.json`.
- Controls: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/rocket-controls/invocation-ru7ld1vr/summary.json`; exact build/source hashes: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/rocket-controls/invocation-ru7ld1vr/rocket-build-identity.json`.
- Ordinary RTL replay: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/native-replay/invocation-klc_nefy/summary.json`.
- All selected suites and independent receipts: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/selected-results.json` and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/host-independent-audit.json`, `outer-independent-audit.json`, `polling-independent-audit.json`, `descriptor-independent-audit.json`, `syscall-independent-audit.json`, `signals-independent-audit.json`, `lifecycle-independent-audit.json`, `regressions-independent-audit.json`, `controls-independent-audit.json`, `replay-independent-audit.json`.
- Exact executable argv/cwd: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/verification-commands.json`; individual native processes: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/raw-native-commands.json`.
- Immutable native inputs and full artifact paths: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/native-input-archives.json` and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/artifact-manifest.json`.

CPU workload: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The separate production host fixture is `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/recipe-polling/invocation-e8aco1wi/polling.elf`,
SHA-256 `c51741a10138ca4ee2661a06bcdf250e04bb844f0f2be1ffdd36e247dc1a3993`.
Aggregate cuts use explicit host-operation indices. Stop/return-code cuts are
component cuts: the real production coroutine does not yield between them.
The native source coroutine and metasim CPU controls are distinct tests;
complete fresh CPU Level-1 continuation is not claimed.

The corruption oracle returns a complete diagnostic string. The initial checker
expected dictionary fields; this was corrected before the accepted run and is
frozen in the replacement build. Initial aggregate/polling source guards reject their changed
inputs; the superseded control/coordinator processes are stopped. All remain
diagnostics. Only the complete replacement scopes under
`frozen/` are selected; every required native case is rerun. No accepted evidence
is overwritten.

Run from Chipyard root (fresh invocation directories):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_host_group_vcs \
  --polling-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/recipe-polling/invocation-e8aco1wi/summary.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/repeat-host
python -m tools.checkpoint_formats.tests.verify_tsi_polling_syscall_vcs \
  --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/frozen/rocket-controls/invocation-ru7ld1vr/rocket-build-identity.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/repeat-polling
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/repeat-native-replay
```

Next: reconstruct and audit the wrapper/context handshake, coordinate production
signals, finish inherited-session policy, and publish a coherent complete
simulator/bridge/memory checkpoint before fresh Rocket CPU Level-1 continuation.
BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA validation and
ASIC power remain outside scope. No external dependency is missing.

## Iteration 148: explicit production outer caller

Complete Rocket Level 1 remains **in_progress**. `run_host()` now uses a
64-byte `firesim.tsi.host-execution.v1` owner: startup, polling, stop,
return-code collection and returned. All signed 32-bit return bits survive
fresh restoration. Active startup/nested-service captures and reentry reject;
service exceptions permanently poison the owner. The real start/poll/stop/
session-release/exit-code order is preserved. The BCD callback binds the TSI,
not its temporary service adapter. See [tsi-host-execution.md](tsi-host-execution.md).
The wrapper/context and aggregate remain unowned; existing component restoration
still rejects `tick()`. No complete CPU checkpoint profile is enabled.

Diagnostic root: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/`.
The six recipe settings in the table above are unchanged and read from the
current recipe YAML. The native rebuild uses VCS Y-2026.03-SP1, `-full64`,
`VCS_FLAGS=-Mupdate`, system GCC/G++ 13 and the VCS helper sourced last.
The new owner/header/source hashes are bound by the actual recipe build.
No FPGA bitstream is built.

| Executed check | Result |
| --- | --- |
| Current-parent outer component, fresh native ASan/UBSan and VCS in both backend directions | 160 restores / 880 complete pre-service and continued owner comparisons; all five phases and return values 0/-1/INT_MIN/INT_MAX pass |
| Actual production coroutine | Sixteen processes; 32 active-startup rejections; complete polling/returned images and syscall response-before-stop ordering; 48 post-return tail ticks preserve lifecycle and issue no work |
| Outer malformed/incompatible images and service guards | All truncations, every configuration bit, trailing bytes, invalid phase/status and reentrant service calls reject atomically; every escaping service site poisons permanently; eight fresh invalid-image processes pass |
| Actual outer phase corruptions | Eight first divergent service boundaries at host operation zero; no divergent operation acknowledged |
| Independent outer evidence audit | All saved owner bytes and actual argv/cwd/results audited; twelve missing/duplicate process/source evidence variants reject |
| Full exact-recipe polling group | Eight scenarios / 863 host-operation cuts / 3,452 fresh restores / 2,768,080 complete owner comparisons / 190,816 operations; two zero-mailbox idle rounds per scenario |
| Polling negatives and ownership | Per backend: 1,844 malformed / 56 membership / seven cross-owner / 846 allocation failures preserve destination; 84 fresh invalid processes, ten late guards, fifteen admission checks and eight first divergent outgoing words pass |
| Recipe-bound syscall parent / signal-thread suites | 1,200 fresh restores / 686 processes, including all-thread guards; passed |
| Full legacy polling/direct-exit scope | 3,872 fresh readbacks / 1,105,584 operations, 256 pending-exit continuations and 96 stopped restores; passed |
| Eight native core suites / thirty retained auditors | Passed; core evidence has 5,291 artifacts / 824 source bindings |
| Ordinary pre-FAME RTL VCS, C=100/700000/900000/3250000 | All 318,637 words before any edge per cut; 256 events / 21,760 comparisons; sixteen actual semantic faults / 44 invalid cases; independent audit passes |
| Exact-recipe default/buffered four-hart controls | Both full 16-GiB controls pass at C=3,329,794; all eight complete hart traces and workload/store labels match |

Accepted artifacts:

- Outer: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/outer-final/invocation-321c0poi/summary.json`.
- Polling: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/recipe-polling-final/invocation-y3ahb_61/summary.json`.
- Controls and exact build identity: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/rocket-controls/invocation-7w9n3gl4/summary.json` and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/rocket-controls/invocation-7w9n3gl4/rocket-build-identity.json`.
- Ordinary RTL replay: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/native-replay/invocation-j34wtfql/summary.json`.
- All selected suites: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/selected-results.json`.
- Independent receipts: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/outer-independent-audit.json`, `polling-independent-audit.json`, `descriptor-independent-audit.json`, `syscall-independent-audit.json`, `signals-independent-audit.json`, `lifecycle-independent-audit.json`, `regressions-independent-audit.json`, `controls-independent-audit.json` and `replay-independent-audit.json`.
- Exact executable argv/cwd catalog: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/verification-commands.json`; individual native processes: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/raw-native-commands.json`.
- Immutable inputs and all full artifact paths: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/native-input-archives.json` and `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/artifact-manifest.json`.

CPU workload: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The production host fixture uses `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/recipe-polling-final/invocation-y3ahb_61/polling.elf`,
SHA-256 `c51741a10138ca4ee2661a06bcdf250e04bb844f0f2be1ffdd36e247dc1a3993`.
Standalone outer cuts are explicit host-operation labels, not CPU target cycles.
Stop/return-code cuts are component tests; live execution has no target yield
between them. The source-coroutine checks do not restore a complete CPU.

The initial polling run rejects at the source-drift guard and remains separate
in `source-drift-diagnostic.json`. Only the complete frozen-input replacement
above is accepted. The independently audited outer pilot uses retained
iteration-147 parent evidence; only the current-parent invocation is selected.
The diagnostic auditor's initial indentation error remains in a separate log;
its corrected complete audits pass. No accepted artifact is overwritten.

Run from Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_host_execution_vcs \
  --polling-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/recipe-polling-final/invocation-y3ahb_61/summary.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/repeat-outer
python -m tools.checkpoint_formats.tests.verify_tsi_polling_syscall_vcs \
  --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/rocket-controls/invocation-7w9n3gl4/rocket-build-identity.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/repeat-polling
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/repeat-native-replay
```

Next: validate/publish this outer owner together with completed polling and
actual lifecycle peers; reconstruct the wrapper and fresh process-local context
handshake without replaying startup; establish production signal coordination
and complete session policy; publish one coherent simulator/bridge/memory cut.
Complete fresh Rocket CPU Level-1 continuation remains pending. BOOM/Saturn
remain pending. Standalone Shuttle, physical FPGA validation and ASIC power
remain outside scope. No external dependency is missing.

## Iteration 147: retire the dormant inherited syscall proxy

Complete Rocket Level 1 remains **in_progress**. Restricted syscall-93 mode
now retires the inherited proxy's three descriptors and dispatch table. Every
restricted group admission, preparation, publication admission, inspection and
continuation requires those resources to remain absent. Fresh construction
rebuilds owner links and immutable registrations. Ordinary sessions retain their
original lifetimes. This is an absent-resource invariant for one unused owner;
see [tsi-dormant-proxy.md](tsi-dormant-proxy.md).

Diagnostic root: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/`.
All recipe-bound suites use the provider actually linked into
`rocket-controls/invocation-d8873709/rocket-build-identity.json`. The exact six
Rocket recipe settings above are unchanged; no bitstream is built. Native VCS
uses Y-2026.03-SP1, `-full64`, system GCC/G++ 13 and the helper sourced last;
Make uses `VCS_FLAGS=-Mupdate` and forces the native rebuild.

| Executed check | Result |
| --- | --- |
| Descriptor lifetimes, native ASan/UBSan and VCS | Four processes; restricted construction and polling add zero descriptors; ordinary construction/polling add three each; four idle/read boundaries and suspended destruction preserve complete expected tables |
| Repeated retirement / live ordinary proxy admission | Both backends reject without changing descriptor identities or flags |
| Actual private proxy faults in a separate test-only provider | Six faults × three boundaries × two backends = 36 fresh processes; descriptor/table/chroot/HTIF-link/memif-link/dynamic-device changes reject before preparation, at commit and during inspection/continuation; peers unchanged, services/context entries/target edges zero |
| Missing/incomplete proxy API and unsupported syscall header | Three cases pass; fresh native constructors reject before startup; header rejection preserves both sentinel archive and report |
| Separately compiled prior production constructor | Fails the new restricted descriptor-count check; expected rejection confirmed |
| Actual linked recipe provider audit | Installed `syscall.o` and `device.o` exact; friend-only syscall header; linked optional proxy API; test mutator absent |
| Live restricted polling / complete fourteen-owner readback | Eight scenarios / 863 host-operation cuts / 3,452 fresh native/VCS restores; 2,768,080 complete owner comparisons / 190,816 operations; no restore service or target edge |
| Malformed/configuration, membership, cross-owner and allocator checks | Both backends: `malformed=1844 membership=56 cross=7 allocation_failures=846 unchanged_on_failure=1` |
| Fresh invalid images / late guards / admission | 84 / 10 / 15; passed |
| Incompatible idle caller/host/reader/provider/response | Seven cases reject in fourteen fresh native/VCS processes before publication |
| Actual syscall argument/write-child faults | 8 first divergent outgoing words remain unconsumed |
| Independent evidence audit | Fourteen incomplete source/build/process/divergence sets and five altered descriptor tables reject |
| Recipe-bound syscall parent / signal-thread suites | 1,200 fresh restores / 686 processes; passed |
| Full legacy polling/direct-exit group | 3,872 fresh readbacks / 1,105,584 operations; 256 pending-exit continuations and 96 stopped restores; passed |
| Eight native core suites / retained auditors | Passed; 5,286 artifacts / 819 source bindings; all thirty retained auditors and the prior iteration-146 polling audit pass |
| Ordinary pre-FAME RTL VCS at C=100/700000/900000/3250000 | All 318,637 words read back before any edge per cut; 256 captured events / 21,760 comparisons; 16 actual semantic faults and 44 invalid cases; passed |
| Exact-recipe default/buffered four-hart controls | Full 16-GiB backing; both pass at C=3,329,794; all eight complete hart traces and workload/store labels match |

Accepted artifacts:

- polling_syscall: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/recipe-polling-syscall/invocation-jcm6k_dr/summary.json`.
- syscall: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/recipe-syscall/invocation-60chlgdj/summary.json`.
- signals: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/recipe-signals/invocation-_eyxffuh/summary.json`.
- lifecycle: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/polling-lifecycle-sealed/invocation-56dl6wlg/summary.json`.
- regressions: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/native-regressions/invocation-koyvs29g/summary.json`.
- controls: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/rocket-controls/invocation-d8873709/summary.json`.
- replay: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/native-replay/invocation-iaqofrfa/summary.json`.
- retained: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/retained-auditor-rechecks/invocation-e5ob_m5d/summary.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/proxy-rejections.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/proxy-api-rejections.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/proxy-provider-independent-audit.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/prior-proxy-mutation.json`.
- `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/idle-rejections.json`.

The separate full standalone polling suite also passes:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/polling-syscall/invocation-z4p4o067/summary.json`.
All native inputs remain sealed. The initial private-fault fixture had compile
errors in its test wrapper; its failed build is retained separately under
`proxy-rejections/`. Only `proxy-rejections-v2/` supplies the accepted 36 cases.
The production build and both complete polling scopes pass.

CPU workload:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Component fixture: `recipe-polling-syscall/invocation-jcm6k_dr/polling.elf`,
SHA-256 `c51741a10138ca4ee2661a06bcdf250e04bb844f0f2be1ffdd36e247dc1a3993`.
The component scenarios use an empty sealed terminal, two zero-mailbox idle
rounds, idle count 3, no hart-0 MSIP write, address residues 0/2/4/6, four raw
exit values and cache flushing disabled or at `0x20004000`.

`verification-commands.json` contains complete executable argv arrays and
working directories relative to Chipyard. `raw-native-commands.json` records
individual build/simulation/process commands. `native-input-archives.json`
binds immutable inputs; `artifact-manifest.json` enumerates full paths.
Independent receipts are `*-independent-audit.json`.

Run from Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_syscall_vcs \
  --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/rocket-controls/invocation-d8873709/rocket-build-identity.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/repeat-polling-syscall
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000,900000,3250000 \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/repeat-native-replay
```

Complete Level-1 CPU continuation remains disabled. Explicit outer startup,
stop/return/context, production signal coordination, complete inherited-session
policy and coherent simulator/bridge/memory publication remain pending. Fresh
component continuation never calls stop or enters a context. The complete
Level-2 captured finite replay is independently validated; these host-operation
cuts do not establish CPU Level-1 target-cycle continuation. BOOM/Saturn remain
pending. Standalone Shuttle, physical FPGA validation and ASIC power are outside
scope. No external dependency is missing.

## Iteration 146: restricted session lifetime and idle cuts

Complete Rocket Level 1 remains **in_progress**. Production restricted polling
now constructs its services without `default_devices_t`, and the atomic group
rejects that unowned session. The embedded HTIF proxy still owns three standard-
stream duplicates. See [tsi-restricted-session.md](tsi-restricted-session.md)
for the exact two-object resource inventory and remaining ownership.

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/`.
All three current archive-bound suites use the provider actually linked into
`rocket-controls/invocation-dn6w_xbn/rocket-build-identity.json`. The six recipe
settings above are unchanged. Builds use VCS Y-2026.03-SP1, `-full64`, system
GCC/G++ 13 and the VCS helper sourced last; cached Make builds use
`VCS_FLAGS=-Mupdate`. No bitstream is built.

| Executed check | Result |
| --- | --- |
| Actual process descriptor audit, native ASan/UBSan and VCS | Four processes; inherited proxy adds three descriptors; restricted polling adds zero and ordinary polling adds three; four idle/read boundaries and suspended destruction reproduce the expected complete tables |
| Prior production implementation compiled separately | New restricted descriptor check rejects the extra session before checkpoint inspection |
| Live restricted polling and two zero-mailbox idle rounds per scenario | Eight scenarios / 863 host-operation cuts / 3,452 fresh producer/consumer pairings; passed |
| Complete fourteen-owner readback and continuation | 2,768,080 owner-image comparisons / 190,816 operations; passed with no restore service or target edge |
| Malformed/configuration, membership, cross-owner and allocator checks | Both backends: `malformed=1844 membership=56 cross=7 allocation_failures=846 unchanged_on_failure=1` |
| Fresh invalid images / late guards / admission checks | 84 invalid-image processes, 10 late guards, 15 admission checks; passed |
| Incompatible idle caller/host/reader/provider/response state | Seven cases in fourteen fresh native/VCS processes reject before publication |
| Actual syscall argument and copied-write-child corruption | 8 first divergent outgoing words remain unconsumed |
| Independent polling evidence audit | Fourteen missing/duplicate/changed source/build/process/divergence sets reject; five altered descriptor identities/tables reject |
| Retained syscall parent / signal-thread suites | 1,200 fresh parent restores and 686 signal processes, including 24 worker transactions; passed using the exact recipe archive |
| Legacy polling/direct-exit group | 3,872 fresh readbacks / 1,105,584 operations; 256 pending-exit continuations and 96 stopped restores; passed |
| Eight native core suites / thirty retained auditors | Passed; 5,286 retained artifacts / 819 source bindings |
| Ordinary pre-FAME RTL VCS, C=100 / 700000 / 900000 / 3250000 | All 318,637 words before any edge per cut; 256 events / 21,760 comparisons, 16 actual semantic faults and 44 invalid cases; passed |
| Exact-recipe default/buffered four-hart controls | Full 16-GiB backing; both pass at C=3,329,794; all eight complete hart traces and workload/store labels match the uninterrupted reference |

Accepted artifacts (full paths are also in `selected-results.json`):

- polling_syscall: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/recipe-polling-syscall/invocation-s5uurlzp/summary.json`.
- syscall: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/recipe-syscall/invocation-gzgns2t0/summary.json`.
- signals: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/recipe-signals/invocation-ekflgrj5/summary.json`.
- lifecycle: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/polling-lifecycle-sealed/invocation-tb2picjd/summary.json`.
- regressions: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration145/native-regressions/invocation-kvn1pu5w/summary.json`.
- controls: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/rocket-controls/invocation-dn6w_xbn/summary.json`.
- replay: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/native-replay/invocation-bsbkcdab/summary.json`.
- retained: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/retained-auditor-rechecks/invocation-fgcc4uyx/summary.json`.

The copied core-suite runner retained its new invocation under iteration 145;
this invocation was created and independently audited during iteration 146.
Existing accepted artifacts were preserved. The separate full standalone
polling run also passes: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/polling-syscall/invocation-e2skvn6_/summary.json`.

The actual CPU workload remains
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The component ELF is `recipe-polling-syscall/invocation-s5uurlzp/polling.elf`,
SHA-256 `c51741a10138ca4ee2661a06bcdf250e04bb844f0f2be1ffdd36e247dc1a3993`.
It is a host-component fixture. Eight scenarios use an empty sealed terminal,
idle count 3, no hart-0 MSIP write, request address residues 0/2/4/6, four raw
exit values and cache flushing disabled or at `0x20004000`.

Complete executable checks, with argv arrays and relative working directories,
are in `verification-commands.json`; individual executed VCS/compiler/process
commands are in `raw-native-commands.json`. Source snapshots are cataloged in
`native-input-archives.json`; `artifact-manifest.json` enumerates full artifact
paths. Independent receipts are `*-independent-audit.json`. Initial diagnostic
CLI import and aligned-oracle preflight errors remain separate logs; accepted
full scopes and negative checks pass.

Run from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_syscall_vcs \
  --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/rocket-controls/invocation-dn6w_xbn/rocket-build-identity.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/repeat-polling-syscall
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000,900000,3250000 \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration146/repeat-native-replay
```

Fresh restricted component continuation completes the response and polling;
it never calls stop or enters a context. Inherited proxy/session ownership,
production signal coordination, explicit outer startup/stop/return/context and
coherent complete simulator/bridge/memory publication remain pending. These
host-operation cuts do not establish CPU target-cycle Level-1 continuation.
BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA validation and
ASIC power remain outside scope. No external dependency is missing.

## Iteration 145: connect the syscall parent to live polling

Complete Rocket Level 1 remains **in_progress**. Explicit
`+checkpoint-syscall-exit` mode now uses the owned parent in production polling.
The atomic fourteen-owner group binds the active dispatch, both nested memif
children, complete serial queues, actual lifecycle and inactive peers before
publication. It preserves cache-flush, writeback and response ordering and binds
pristine terminal state to startup metadata. Fresh component continuation does
not enter a context or call stop. See
[tsi-polling-syscall.md](tsi-polling-syscall.md) for state ownership and exclusions.

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration145/`.
All three archive-bound suites use the provider actually linked into
`rocket-controls-final-inputs/invocation-uv_o5b21/rocket-build-identity.json`.
The six exact recipe settings above are unchanged. Builds use Y-2026.03-SP1,
`-full64`, system GCC/G++ 13 and the VCS helper sourced last; cached Make builds
use `VCS_FLAGS=-Mupdate`. No bitstream is built.

| Executed check | Result |
| --- | --- |
| Live restricted polling, native ASan/UBSan and VCS | Eight scenarios; 703 host-operation cuts; 2,812 fresh producer/consumer pairings; passed |
| Complete fourteen-owner readback and continuation | 1,867,040 owner-image comparisons / 127,736 operations; passed, no restore service or target edge |
| Malformed/configuration and ownership faults | 1,844 malformed cases, 56 missing/duplicate/reordered owner cases and seven cross-owner faults per backend; rejected atomically |
| Fresh invalid-image processes | 84 native/VCS processes; rejected before group publication |
| Allocation failures | Every one of 846 failure positions per backend leaves destination owners unchanged |
| Late provider/mask/pending/peer guards | Ten transactions; no publication before successful guard/retry |
| Unsupported command/selector/mode, absent provider and terminal corruption | Fifteen checks; rejected before unowned service or group publication |
| Actual post-restore semantic corruption | Eight native/VCS argument plus copied-write-child faults; predicted first divergent word remains unconsumed |
| Independent group evidence audit | Passed; fourteen missing/duplicate/changed evidence variants rejected |
| Retained independent syscall parent | 300 cuts / 1,200 restores; installed-syscall differential, malformed/atomic/corruption checks and twelve evidence rejections; passed |
| Exact-provider signal/thread regression | 686 processes, 24 actual worker transactions, fourteen evidence rejections; passed |
| Full legacy polling/direct-exit regression | 3,872 fresh protocol readbacks, 1,105,584 operations, 256 pending-exit continuations and 96 stopped restores; passed |
| All eight native core suites / thirty retained auditors | Passed; 280 Python tests / 5,286 artifacts / 819 source bindings |
| Fresh ordinary RTL VCS at C=100 / 700000 / 900000 / 3250000 | Every one of 318,637 words before edges at each cut; 256 events / 21,760 comparisons, sixteen actual semantic faults and 44 invalid cases; passed |
| Exact-recipe default/buffered four-hart controls | Complete 16-GiB backing; both pass at C=3,329,794; eight full hart traces and every workload/store label match the uninterrupted reference |

Accepted artifacts, relative to the diagnostic root:

- Restricted polling: `recipe-polling-syscall-final-inputs/invocation-ckf8ipgj/summary.json`.
- Independent syscall parent: `recipe-syscall-final-inputs/invocation-6fmr8ise/summary.json`.
- Actual signal/thread owner: `recipe-signals-final-inputs/invocation-34075bwb/summary.json`.
- Legacy polling/direct-exit: `polling-lifecycle-sealed/invocation-p5x7sdd_/summary.json`.
- Native core regressions: `native-regressions/invocation-ix97vgmt/summary.json`.
- Ordinary RTL replay: `native-replay/invocation-gei9x9nv/summary.json`.
- Four-hart controls: `rocket-controls-final-inputs/invocation-uv_o5b21/summary.json`.

Independent results: `polling-syscall-current-independent-audit.json`,
`syscall-current-independent-audit.json`, `signals-current-independent-audit.json`,
`lifecycle-independent-audit.json`, `regressions-current-independent-audit.json`,
`controls-current-independent-audit.json` and `replay-independent-audit.json`.
The group auditor checks every producer byte against the independent oracle,
every fresh pre-service/final byte, every intermediate owner image, original
operation labels, actual archive membership and executed process commands.
The installed `syscall.o` remains byte-identical to its installed archive member.

The real CPU workload remains
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The separate **host-component fixture** ELF is `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration145/recipe-polling-syscall-final-inputs/invocation-ckf8ipgj/polling.elf`,
SHA-256 `c51741a10138ca4ee2661a06bcdf250e04bb844f0f2be1ffdd36e247dc1a3993`. It is not a CPU acceptance workload.
Component scenarios use an empty sealed terminal, idle count 3, no hart-0 MSIP
startup write, four exit values, request-address residues 0/2/4/6 and cache
flushing both disabled and at `0x20004000`.

Exact command arrays, native compiler/backend flags, source hashes and artifact
paths are in `verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and the selected invocation reports. Repeat the
accepted component and ordinary RTL scopes from the Chipyard root:

```bash
source env.sh
source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_syscall_vcs \
  --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration145/rocket-controls-final-inputs/invocation-uv_o5b21/rocket-build-identity.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration145/recipe-polling-syscall-final-inputs
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000,900000,3250000 \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration145/native-replay
```

Each verifier allocates a fresh invocation. The syscall/polling cuts are
**host-operation indices, not Rocket target cycles**. Complete simulator
publication still needs the independent build/container binding, session or
restricted-session construction, signal coordination, outer callers and every
simulator/bridge/memory owner. CPU Level 1 remains disabled. Initial pilots and
superseded incomplete runs remain separate diagnostics; the final selected
scopes use sealed source inputs. No plan, paper or environment input was edited
or staged, and no local commit was created. BOOM/Saturn remain pending.

## Iteration 144: own the proxied syscall-exit parent

Complete Rocket Level 1 remains **in_progress**. The new executable
`firesim_tsi_syscall_exit_t` owns the proxied syscall-93 request, invocation,
writeback and response cursor with nested read/write callers. Its ordered
caller/serial/actual-lifecycle restore validates all images and relationships
before nonthrowing publication. It is separate from the direct odd-command
exit recorder and is not wired into live polling dispatch or CPU admission.
See [tsi-syscall-exit.md](tsi-syscall-exit.md) for exact scope and next integration.

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration144/`.
The accepted component suite uses the actual HTIF archive linked into
`rocket-controls/invocation-iyg5oler/rocket-build-identity.json`. The installed
`syscall.o` member remains byte-identical and supplies the differential reference.
The exact recipe settings above are unchanged. Builds use Y-2026.03-SP1,
`-full64`, system GCC/G++ 13 and the VCS helper sourced last. No bitstream is built.

| Executed check | Result |
| --- | --- |
| Recipe archive-bound native ASan/UBSan and VCS syscall parent | Four scenarios, 300 cuts, 1,200 fresh cross-backend restores; passed |
| Complete caller/serial/lifecycle readback and service timing | 141,408 owner comparisons / 45,936 host operations; passed, zero restore services or target edges |
| Installed syscall differential | Eight actual installed dispatches; full read/merge/write/response order, memory and provider state match |
| Malformed/incompatible configuration | 814 cases per backend, plus eighteen fresh invalid-image processes; rejected without partial publication |
| Missing/duplicate/reordered owners and inconsistent children/provider | Twelve membership and eight relationship checks per backend; rejected atomically |
| Allocation failures and occupied provider | All 86 allocation-failure positions per backend preserve every owner; occupied destination rejects |
| Unsupported commands/endian/selector and callback guards | Fifteen checks per backend; no unowned exit/writeback/response; poisoned/reentrant callers reject |
| Actual post-restore semantic corruption | Four native/VCS argument/write-child edits; first outgoing word mismatch detected and unconsumed |
| Independent syscall evidence audit | Passed; twelve missing/duplicate source/build/process/artifact evidence variants rejected |
| All eight preserved native suites | Passed; 280 Python tests, 5,283 artifacts, 816 source bindings |
| All thirty retained independent auditors | Passed |
| Fresh ordinary RTL VCS at cuts 100 / 700000 / 900000 / 3250000 | All 318,637 words before edges at each cut; 256 events / 21,760 comparisons; sixteen semantic faults and 44 invalid cases; passed |
| Exact-recipe default/buffered four-hart controls | Both pass at C=3,329,794 with complete 16-GiB backing; all eight full hart traces and workload/store labels match the uninterrupted reference |

Accepted syscall evidence:
`recipe-syscall/invocation-9b6f2981/summary.json`.
Accepted native prerequisites:
`native-regressions/invocation-twt_pqzg/summary.json`.
Accepted ordinary RTL replay:
`native-replay/invocation-6e_cznpj/summary.json`.
Accepted complete four-hart controls:
`rocket-controls/invocation-iyg5oler/summary.json`.
Independent audits: `syscall-independent-audit.json`,
`regressions-independent-audit.json`, `replay-independent-audit.json`,
`controls-independent-audit.json` and `retained-independent-audit.json`.
Final catalogs: `summary.json`, `selected-results.json`,
`native-input-archives.json`, `verification-commands.json`,
`raw-native-commands.json` and `artifact-manifest.json`.
The source/ELF/build bindings and per-cut complete byte images are in those
invocations. The four-hart workload ELF remains
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Exact executable command arrays (including compiler/backend flags in native
subcommands) are in
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration144/verification-commands.json`
and `raw-native-commands.json`. To repeat the accepted component and ordinary
RTL checks from the Chipyard root:

```bash
source env.sh
source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_syscall_exit_vcs \
  --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration144/rocket-controls/invocation-iyg5oler/rocket-build-identity.json \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration144/recipe-syscall
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000,900000,3250000 \
  --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration144/native-replay
```

Each verifier allocates a new invocation and preserves retained artifacts.

These syscall cuts are **host-operation indices**, not Rocket target cycles.
The adapter binds component configuration; the eventual simulator container
must bind executable/build identity and own the polling response queue,
session/descriptors, generic syscall callers, signal coordination, outer
execution and coherent simulator/bridge/memory publication. Complete Level 1
is still disabled. BOOM and Shuttle + Saturn remain pending.

The initial pilot's unaligned corruption-oracle error and subsequent source-drift
rejections remain diagnostic failures. The accepted suite reruns the complete
scope against the final sources. No plans, environment helpers or conda inputs
were edited or staged; no local commits were created.

## Iteration 143: audit HTIF signal state in every host thread

Complete Rocket Level 1 remains **in_progress**. The opt-in actual-provider
signal guard now checks every kernel thread's blocked and pending SIGINT,
SIGTERM and SIGABRT state and rejects incomplete procfs or unstable task
inventory before capture/preparation/publication. It still requires exclusive
suspension and an external policy that prevents signal/thread-state changes;
a production coordinator is pending. Image contents and independent Level-2
ownership are unchanged. See [tsi-htif-signal-threads.md](tsi-htif-signal-threads.md).

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration143/`.
The exact recipe settings above were re-read. The rebuilt VCS executable links
`checkpoint-fesvr/lifecycle/owned-htif.o`; its actual archive supplies the
accepted signal consumers. The ordinary generated inventory remains 11,464 entries /
445,838 words, across sixty native translation units. The provider still compiles original HTIF method
bodies unchanged. The new helper is a source-hashed overlay input and Make
dependency. Builds use Y-2026.03-SP1, `-full64`, `VCS_FLAGS=-Mupdate` and GCC/G++
13, with no bitstream build.

| Executed check | Result |
| --- | --- |
| Recipe archive-bound native ASan/UBSan and VCS signal suite | 686 fresh processes; passed |
| Existing actual captures / fresh restores / malformed cases | 72 / 144 / 300; passed |
| Two-parked-worker captures / fresh cross-backend restores | Six / twelve; complete provider readback and next two HTIF boundaries match |
| Actual worker mask / worker-directed / shared pending signals | 24 transactions; capture, preparation and final commit reject with no provider/peer publication; repaired workers permit one atomic retry |
| Existing peer transactions / semantic faults | 72 serial peer publications; forty late guards; six first-boundary provider faults; passed |
| Independent state/archive/thread audit | Passed; fourteen missing/duplicate evidence variants rejected |
| Prior exact-recipe provider sensitivity | Six native/VCS tests fail as expected because the old provider omits worker checks |
| Strict lifecycle | 2,432 fresh restores, 282 malformed cases, 440 atomic transactions; passed |
| Fourteen-owner running/pending/stopped polling group | 3,872 fresh readbacks / 1,105,584 host operations / 256 pending-exit continuations / 96 stopped restores; passed |
| Retained independent auditors | All thirty passed |
| Fresh ordinary RTL VCS | Four cuts, all 318,637 words per zero-edge readback, 256 events / 21,760 output comparisons, sixteen actual first divergences and 44 invalid cases; passed |
| Preserved native suites | All eight pass: 280 Python tests / 5,280 artifacts / 813 source bindings; initial invocation rejected mid-run test-source drift |
| Complete default/buffered 16-GiB four-hart controls | Both pass at C=3,329,794; all eight full hart traces and every workload/store label match |

Accepted signal summary:
`recipe-signals/invocation-g9yeawcm/summary.json`;
strict/polling summaries:
`strict-lifecycle/invocation-piyjq56o/summary.json` and
`polling-lifecycle/invocation-ipwhoti0/summary.json`.
`signals-independent-audit.json`, `signals-builtin-audit.json` and
`prior-provider-witness/invocation-9k80fwnt/summary.json` record the independent
checks and prior-provider failures. Initial pilots exposed test teardown
requirements: explicitly drain pending SIGABRT and retain parked worker threads
during recovery rather than assuming `pthread_join` immediately removes their
procfs entries. They remain diagnostic failures, separate from accepted results.

Ordinary RTL evidence:
`native-replay/invocation-ugf9msom/summary.json` and
`replay-independent-audit.json`. These use the original complete iteration-139
captures at C=100/700000/900000/3250000, all seven clocks and 116 ports. No target
cycle labels are changed. The C=900000 window includes cached grants/writebacks;
external AXI is idle there. ELF SHA-256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Signal-provider faults are host component evidence; the sixteen ordinary RTL
faults mutate actual Rocket CSR state. This increment makes no complete CPU
Level-1 continuation claim. BOOM/Saturn remain pending.

Both complete four-hart controls pass in
`rocket-controls/invocation-8dy5111m/summary.json`; the fresh native-regression
rerun passes in `native-regressions/invocation-1s7q9cgo/summary.json`.
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json`, `selected-results.json` and
`artifact-manifest.json` seal the exact commands, inputs and diagnostic files.
`final-independent-audit.json` passes every selected native scope. Complete
Rocket Level-1 ownership/continuation and the production signal coordinator
remain pending.
Existing controller commits were published FireSim first, then Chipyard; both
remote main tips equal local HEADs despite read-only local tracking-ref errors.
No staging or local commits occurred. The plans and environment inputs retain
their starting bytes.

Executable native checks from the Chipyard root, as argv arrays:

```json
[
  {
    "purpose": "Exact Rocket recipe rebuild and complete default/buffered four-hart controls",
    "cwd": ".",
    "argv": [
      "bash",
      "-lc",
      "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration143/rocket-controls --seed-build /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration142/rocket-controls/invocation-xew5lebr/build --workload /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json --host-audit-cycles 0,520064,700032,900096,3250048 --htif-source /scratch/jfx/chia-cy-checkpoint-restore/toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc"
    ]
  },
  {
    "purpose": "recipe-signals complete native ASan/UBSan and VCS matrix",
    "cwd": ".",
    "argv": [
      "bash",
      "-lc",
      "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_tsi_htif_signal_vcs --thread-guards --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration143/rocket-controls/invocation-8dy5111m/rocket-build-identity.json --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration143/recipe-signals"
    ]
  },
  {
    "purpose": "Independent signal archive, state, continuation and incomplete-evidence audit",
    "cwd": ".",
    "argv": [
      "python",
      "-m",
      "tools.checkpoint_formats.tests.audit_tsi_htif_signal_threads",
      "/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration143/recipe-signals/invocation-g9yeawcm/summary.json"
    ]
  },
  {
    "purpose": "All eight preserved native suites, including FCFS and Python",
    "cwd": ".",
    "argv": [
      "python",
      "/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration143/repeat-native-regressions.py"
    ]
  },
  {
    "purpose": "Fresh ordinary RTL VCS four-cut complete state readback/replay and actual semantic faults",
    "cwd": ".",
    "argv": [
      "bash",
      "-lc",
      "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration143/native-replay"
    ]
  }
]
```

## Iteration 142: actual delivered-signal/lifecycle provider state

Complete Rocket Level 1 remains **in_progress**. The new independent
`firesim.tsi.htif-signal.v1` component owns the actual process-wide delivered
latch and private optional exit/stopped projection under its explicit
masked/no-pending/original-handler policy. It has destination-bound preparation,
final guards and nonthrowing peer publication. It does not enable the CPU
profile, reconstruct sessions/contexts or extend the fourteen-owner polling
group's delivered-signal admission. See [tsi-htif-signal.md](tsi-htif-signal.md).

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration142/`.
The actual exact-recipe executable links the selected provider as
`checkpoint-fesvr/lifecycle/owned-htif.o`; the signal consumers use that same
archive. Original HTIF method bodies remain unchanged. All six recipe settings
above are preserved, with Y-2026.03-SP1, `-full64`, `VCS_FLAGS=-Mupdate`, GCC/G++
13 and no FPGA build. The generated ordinary simulator inventory remains
11,464 entries / 445,838 words, separate from host provider/driver ownership.

| Executed check | Result |
| --- | --- |
| Exact-recipe archive-bound signal suite | 644 fresh native ASan/UBSan and VCS processes |
| Actual source signal captures / fresh complete provider restores | 72 / 144; all provider words and fields read back before service/edge |
| Uninterrupted source versus fresh provider continuation | Both next HTIF boundaries match for every restore |
| Invalid images and incompatible component configuration | 300 reject without provider publication |
| Late destination guards / real serial-peer publications | Forty / 72; rejected guards publish neither provider nor peer |
| Actual restored-latch subsequent signal | Two original-handler `exit(-1)` results; no restore-time signal delivery |
| Actual provider semantic faults | Six signal/stopped/raw-exit faults diverge at boundary zero before acknowledgement |
| Independent archive/state/trace audit | Pass; eight missing/duplicate evidence variants rejected |
| Strict lifecycle regression | 2,432 fresh restores / 282 malformed cases / 440 atomic transactions |
| Existing running/pending/stopped polling group | 3,872 fresh protocol readbacks / 1,105,584 operations / 256 pending-exit continuations / 96 stopped restores |
| Preserved native suites | All eight pass; 280 Python tests / 5,279 artifacts / 812 source bindings |
| Retained independent auditors | All thirty pass |
| Fresh ordinary RTL VCS | Four cuts; 318,637 words per zero-edge readback; 256 events / 21,760 output comparisons; sixteen actual DUT CSR first divergences; 44 invalid cases |

Accepted signal evidence:
`recipe-signals/invocation-68fia3n2/summary.json`,
`signals-independent-audit.json` and `signals-builtin-audit.json`.
Strict/polling evidence:
`strict-lifecycle/invocation-zn5bn3ip/summary.json` and
`polling-lifecycle/invocation-h4h4lmw4/summary.json`.
All provider faults above are host component evidence; the sixteen ordinary
RTL CSR faults are actual Rocket DUT evidence. Pending SIGABRT, altered handler
identities/masks/flags, signature mode and occupied destinations reject.
Cross-thread signal coordination and signal-caused stop callers remain pending.

Both exact-recipe complete default and buffered **16-GiB four-hart controls
pass at C=3,329,794**. All eight complete hart traces and every workload/store
label match the uninterrupted reference. Accepted control evidence:
`rocket-controls/invocation-xew5lebr/summary.json`.

Ordinary replay uses the original complete iteration-139 source files at
C=100/700000/900000/3250000 in
`native-replay/invocation-3j4qzhts/summary.json`. All seven original clocks and
116 ports retain their captured labels. `replay-independent-audit.json`
checks all source words/events and the retained complete four-hart source run.
At C=900000 the source retains two cached grants and two voluntary writebacks;
its external AXI window is idle. This increment makes no new CPU Level-1 cut
or continuation claim. ELF SHA-256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

`verification-commands.json` records the full reproduction commands;
`raw-native-commands.json` records executed native commands with pinned
environment wrappers. The final independent audit passes all selected scopes:
147,975 artifacts, 972 native source bindings and 8,573 executed native commands.
`final-independent-audit.json` records the result. The catalogs bind selected
summaries, source snapshots and diagnostic artifacts. Existing controller commits were
published FireSim first and then Chipyard; both remote tips match local HEADs.

Executable checks from the Chipyard root, as argv arrays:

```json
[
  {
    "purpose": "recipe-signals complete native ASan/UBSan and VCS matrix",
    "cwd": ".",
    "argv": [
      "bash",
      "-lc",
      "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_tsi_htif_signal_vcs --recipe-build-identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration142/rocket-controls/invocation-xew5lebr/rocket-build-identity.json --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration142/recipe-signals"
    ]
  },
  {
    "purpose": "Independent signal archive, state, continuation and incomplete-evidence audit",
    "cwd": ".",
    "argv": [
      "python",
      "/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration142/audit-signals.py",
      "/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration142/recipe-signals/invocation-68fia3n2/summary.json"
    ]
  },
  {
    "purpose": "polling-lifecycle complete native ASan/UBSan and VCS matrix",
    "cwd": ".",
    "argv": [
      "bash",
      "-lc",
      "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_tsi_polling_lifecycle_vcs --pending-exit --stopped-exit --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration142/polling-lifecycle"
    ]
  },
  {
    "purpose": "Fresh ordinary RTL VCS four-cut complete state readback/replay and actual semantic faults",
    "cwd": ".",
    "argv": [
      "bash",
      "-lc",
      "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration142/native-replay"
    ]
  },
  {
    "purpose": "All eight preserved native suites, including FCFS and Python",
    "cwd": ".",
    "argv": [
      "python",
      "/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration142/repeat-native-regressions.py"
    ]
  }
]
```

## Iteration 141: explicit Level-1 observer exclusions

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/`.
Complete Rocket Level 1 remains **in_progress**. This increment excludes the
semantic observer's unowned HDL counters/samples, native VPI plan/readback and
trace file state from Level-1 admission. The observer remains independent of
original semantic state. See [level1-observer-exclusion.md](level1-observer-exclusion.md).

Public Level-1 requests with `+fame_capture=` or `+semantic_capture=` reject
before factory entry, independently of argument ordering. The linked FAME
backend additionally rejects with no capture option supplied. The checkpoint
capability base constructor excludes private diagnostic paths before derived
initialization. Builds without the backend preserve their normal admission
rules. No CPU Level-1 capability is enabled.

| Executed check | Result |
| --- | --- |
| Native ASan/UBSan and actual VCS entry matrix | 572 fresh processes; capability enabled/disabled and observer linked/absent |
| Runtime observer options | 384 rejections before capability factory entry |
| Linked observer, disabled at runtime | 24 public rejections before factory entry |
| Capability base constructor | Eight rejections before derived initialization, including private capture |
| Entry evidence negative audit | Four missing/duplicate evidence sets rejected |
| Actual exact-recipe Rocket VCS | 18 pre-runtime public rejections across compiled-disabled/FAME/legacy observer modes |
| Preserved native suites | All eight pass; 280 Python tests / 5,276 artifacts / 809 source bindings |
| Retained independent audits | All thirty pass |

Accepted entry evidence is
`entry-observer-final/invocation-fjy_0l1n/summary.json`; the independent result is
`entry-observer-independent-audit.json`. The actual Rocket exclusion result is
`rocket-observer-exclusion-final/invocation-whola2r4/summary.json`. Every rejected
request preserves the restore sentinel and publishes no image, history or
capture trace. These are admission checks, not complete CPU checkpoint cuts.

Both exact-recipe native builds and all three complete **16-GiB four-hart
workload runs pass** at reported fastest-clock **C=3,329,794**. Source capture:
`rocket-capture-final/invocation-z48jyzzk/summary.json`; ordinary/buffered controls:
`rocket-controls/invocation-bb9qmkkw/summary.json`. Every full hart trace (twelve
across the three runs) and all workload/store cycle labels match the uninterrupted
reference. ELF SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

The source observer logs **3,329,793 actual completed mbus rises**, independently
of the reported fastest-clock count. Its complete original ChipTop inventory
remains **8,644 owners / 318,637 words / seven clocks / 116 ports**. The source
build has 62 native units and 11,746 generated entries / 446,120 words; ordinary
controls have 60 units and 11,464 entries / 445,838 words. The bound observer is
outside those generated inventories and is explicitly excluded from Level 1.

Fresh ordinary RTL VCS passes all four retained captured windows in
`native-replay/invocation-gnt43h6w/summary.json`: **318,637 words per zero-edge
readback**, **256 events / 21,760 output comparisons**, **sixteen actual stored-CSR
first divergences** before acknowledgement, and **44 invalid cases**. Replay
consumes the retained iteration-139 source files. The independent source audit
checks all eight new state/trace files at C=100/700000/900000/3250000 against
those exact replay inputs byte-for-byte before accepting the current evidence.
No source or target-cycle label is substituted. C=900000 retains the previously
audited two pending cached grants and two voluntary writebacks; its external
AXI window is idle.

`source-independent-audit.json`, `controls-independent-audit.json` and
`replay-independent-audit.json` bind the native builds, complete executions,
original captured words, zero-edge readbacks, finite comparisons and negatives.
`summary.json`, `selected-results.json`, `native-input-archives.json` and
`artifact-manifest.json` seal accepted results and retained diagnostics.
`verification-commands.json` records complete exact-recipe build/workload,
ordinary VCS replay and independent-audit commands. `raw-native-commands.json`
retains native argv plus environment-sourcing reproduction commands with cwd
relative to the Chipyard root.

Executable native checks from the Chipyard root, as argv arrays:

```json
[
  {
    "cwd": ".",
    "argv": [
      "bash",
      "-lc",
      "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_checkpoint_entry --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/entry-observer-final"
    ]
  },
  {
    "cwd": ".",
    "argv": [
      "python",
      "/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/audit-entry-observer.py",
      "/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/entry-observer-final/invocation-fjy_0l1n/summary.json"
    ]
  },
  {
    "cwd": ".",
    "argv": [
      "bash",
      "-lc",
      "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/verify-rocket-observer-exclusion.py --identity /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/rocket-capture-final/invocation-z48jyzzk/native-build-identity.json --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/rocket-observer-exclusion-final"
    ]
  },
  {
    "purpose": "Fresh ordinary RTL VCS complete readback/replay, actual semantic faults and invalid images",
    "cwd": ".",
    "argv": [
      "bash",
      "-lc",
      "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/native-replay"
    ]
  },
  {
    "purpose": "rocket-vcs-build",
    "cwd": ".",
    "argv": [
      "bash",
      "-lc",
      "source env.sh && source sims/firesim/env.sh && export COURSIER_CACHE=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/rocket-capture-final/invocation-z48jyzzk/coursier-cache && export CXXFLAGS=\"${CXXFLAGS} -isystem ${CONDA_PREFIX}/include\" && export LDFLAGS=\"${LDFLAGS} -L${CONDA_PREFIX}/lib\" && source automations/checkpoint_loop/vcs-env.sh && make -C sims/firesim/sim PLATFORM=f2 TARGET_PROJECT=firesim TARGET_PROJECT_MAKEFRAG=/scratch/jfx/chia-cy-checkpoint-restore/generators/firechip/chip/src/main/makefrag/firesim DESIGN=FireSim TARGET_CONFIG=WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig PLATFORM_CONFIG=WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config BUILD_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/rocket-capture-final/invocation-z48jyzzk/build SIMULATOR_CHECKPOINT_INVENTORY=FPGATop JAVA_HEAP_SIZE=32G CHECKPOINT_HTIF_SOURCE=/scratch/jfx/chia-cy-checkpoint-restore/toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc SEMANTIC_BRIDGE_CHECKPOINT_ROOT=FireSim.chiptop0 'VCS=/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs -full64' VCS_FLAGS=-Mupdate VCS_FORCE_REBUILD=1 vcs SEMANTIC_MULTICLOCK_INVENTORY=1 SEMANTIC_FAME_STATE_MAP=1 'VCS_EXTRA_V=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/rocket-capture-final/invocation-z48jyzzk/monitor/capture.sv /scratch/jfx/chia-cy-checkpoint-restore/tools/checkpoint_formats/fame_capture.cc /scratch/jfx/chia-cy-checkpoint-restore/tools/checkpoint_formats/semantic_restore.cc' 'VCS_FLAGS=-Mupdate -debug_access+all +vpi'"
    ]
  },
  {
    "purpose": "rocket-capture",
    "cwd": ".",
    "argv": [
      "bash",
      "-lc",
      "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && cd /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/rocket-capture-final/invocation-z48jyzzk/runtime && /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/rocket-capture-final/invocation-z48jyzzk/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim +permissive -no_save +vcs+initreg+0 +vcs+initmem+0 +memsize=17179869184 +max-cycles=5000000 +fesvr-step-size=128 +blkdev-in-mem0=128 +mm_useHardwareDefaultRuntimeSettings_0 +tracefile=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/rocket-capture-final/invocation-z48jyzzk/runtime/TRACEFILE +fame_capture=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/rocket-capture-final/invocation-z48jyzzk/runtime/capture +permissive-off /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv"
    ]
  }
]
```

Initial source-freeze, incorrect seed-path and test-only error-marker pilots are
retained separately from accepted final invocations. Session/descriptors,
process signals, syscall-parent/outer caller, complete simulator/bridge/memory
aggregation and fresh CPU continuation remain pending. BOOM/Saturn remain
pending. No external dependency, FPGA validation or ASIC power result is claimed.

## Iteration 140: completed direct-exit group restoration

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration140/`.
Complete Rocket Level 1 remains **in_progress**. This increment restores the
fourteen-owner sealed polling/direct-exit/provider group after its caller has
completed. It preserves the complete terminal transcript, pending response and
serial FIFO words, raw signed status and actual private provider stopped bit.
It performs no startup, stop service, target service or coroutine entry.
Session/descriptors/signals/syscall-parent/context and complete simulator-wide
ownership remain pending; CPU checkpoint admission remains disabled.

Only the lifecycle coordinator's private preparation path admits a completed
poll. The recorder must be stopped, the provider must contain the identical
present raw status and stopped bit, and the polling caller must be complete
with idle children. Public twelve-owner preparation still rejects completed
callers. Allocating checks finish before the existing guarded nonthrowing
publication. Repeated service, ordinary polling, tick, consumed candidates and
competing candidates reject without changing the restored group.

The complete native ASan/UBSan and Y-2026.03-SP1 VCS suite passes in
`polling-lifecycle-final/invocation-rsfaix44/summary.json`:

| Check | Executed result |
| --- | --- |
| Fresh stopped cuts, eight raw statuses, both source/destination backends | 96 complete fourteen-owner readbacks / 1,344 owner images, before any edge |
| Actual restored provider status corruptions | 32 first divergences at host boundary 0, no acknowledgement or stop |
| Individually valid but incompatible caller/provider combinations | 112 atomic rejections |
| Stopped malformed/member/configuration cases | 5,284 atomic rejections |
| Stopped preparation/publication allocation failures | 3,000 failures without partial publication |
| Stopped final provider guards | 24 rejections; three late-peer cases per backend pair also pass |
| Retained running/pending group matrix | 3,872 fresh readbacks, 1,105,584 continued host operations, 256 pending-exit continuations |
| Retained pending response corruptions | 32 first divergences before consuming the differing word |
| Nonempty stopped BCD/transcript/packet tails | 12 fresh restores / 168 owner images; two BCD commands, transcript `5a`, packet tails 7/5/0 words; output is not re-emitted |
| Public twelve-owner regression | 2,976 fresh preparations / 744 cuts; 4,368 malformed, 244 membership and 44 cross-owner rejections; 2,904 preparation and 172 commit allocation failures |

These are **host-component cuts**, not CPU target-cycle checkpoint cuts. The
first pilot passed its stopped readbacks but failed a test-only terminal offset
assumption. The final test mutates the destination through an actual sealed
terminal read and passes with both one-byte and three-byte inputs. The failed
pilot remains under `polling-lifecycle/`; it is not accepted evidence.
Ten missing/duplicate evidence matrices reject in
`stopped-auditor-rejections.json`.

Fresh ordinary RTL VCS additionally passes all four retained captured Level-2
windows in `native-replay/invocation-vht5xql1/summary.json`: 318,637 words per
cut, 256 events / 21,760 output comparisons, sixteen actual stored CSR faults
and 44 invalid-image/native-loader cases. These reuse the complete iteration-139
capture; this iteration does not claim a new source capture.

All eight preserved native suites pass, including FCFS and **280 Python tests**
/ 5,276 artifacts / 809 source bindings. All thirty retained independent audits
pass. The separate public twelve-owner result is
`twelve-owner-regression/invocation-sucm3irm/summary.json`; nonempty source and
stopped readbacks are independently checked in
`nonempty-stopped/invocation-_1d_cbzb/summary.json`.
Both final exact-recipe **16-GiB four-hart controls pass** at the reported
fastest-clock count **C=3,329,794**, with every full hart trace and workload/store
cycle label matching the uninterrupted reference. Accepted results are in
`rocket-controls-final/invocation-ezdigj8q/summary.json`. Workload ELF SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The native build audit binds all **60 translation units**, the actual lifecycle
provider and **11,464 generated entries / 445,838 words** in this ordinary recipe
build. `rocket-owner-symbol-audit.json` also checks the new constructor in the
actual compiled FireSim object. The separate retained semantic-preservation
capture still uses its own mapped inventory and observer, as documented below.
Earlier controls and broad regressions rejected their source-freeze mismatch
after the test-only helper correction; only the final invocations are accepted.
Neither CPU Level-1 continuation nor complete M11 acceptance is claimed.

`selected-results.json`, `summary.json`, `native-input-archives.json` and
`artifact-manifest.json` bind the exact accepted results and all retained
diagnostics. Both plans, papers, environment helpers and local HEADs are
unchanged; no staging or local commits were performed. Existing controller
checkpoints were published FireSim first, then Chipyard; remote main tips match.

Executable checks from the Chipyard root, as argv arrays:

```json
[
  {
    "cwd": ".",
    "argv": ["bash", "-lc", "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_tsi_polling_lifecycle_vcs --pending-exit --stopped-exit --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration140/polling-lifecycle-final"]
  },
  {
    "cwd": ".",
    "argv": ["python", "-m", "tools.checkpoint_formats.tests.verify_tsi_polling_lifecycle_vcs", "--audit", "/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration140/polling-lifecycle-final/invocation-rsfaix44/summary.json"]
  },
  {
    "cwd": ".",
    "argv": ["bash", "-lc", "source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs --base /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated --capture /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture --cuts 100,700000,900000,3250000 --out /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration140/native-replay"]
  }
]
```

Every reproduction allocates a fresh invocation. `verification-commands.json`
records the complete native rebuild/control/regression and independent-audit
commands; `raw-native-commands.json` retains the actual native compiler and
executable argv. Both catalogs use cwd relative to the Chipyard root.
The native group executables are `polling-lifecycle-final/invocation-rsfaix44/aggregate-native`
and `polling-lifecycle-final/invocation-rsfaix44/simv`. Their VCS build uses
Y-2026.03-SP1, `-full64` and GCC/G++ 13. The exact-recipe Make command and
executed native VCS invocation are retained in
`rocket-controls-final/invocation-ezdigj8q/rocket-vcs-build-result.json` and
`rocket-controls-final/invocation-ezdigj8q/rocket-vcs-build.log`.

## Iteration 139: actual semantic clock events and captured ordinary replay

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/`.
Level 2 is **verified for the complete ChipTop boundary at these four finite
workload windows**; Level 1 remains **in_progress**. See
[rocket-semantic-event-capture.md](rocket-semantic-event-capture.md).

The complete retained ChipTop boundary has **8,644 entries / 318,637 words**,
seven original clock inputs and **116 ports**. The new emitted-RTL audit checks
every mapped state clock, every port shape and all six actual output clock
aliases. Unsupported flattening, replication, clock expressions and gate
placement reject explicitly. Native VCS capture reads every register, logical
memory word, pipeline register and initialized external owner. It records
pre-event inputs/outputs and upcoming actual clock vectors for rises and falls;
no host-cycle or clock-bridge-credit labels are substituted for target edges.

The complete original ownership breakdown in `semantic-owner-totals.json` is:

| Original domain | Entries | Words |
| --- | ---: | ---: |
| mbus | 255 | 65,787 |
| tile 0 | 1,435 | 43,895 |
| tile 1 | 1,435 | 43,895 |
| tile 2 | 1,435 | 43,895 |
| tile 3 | 1,435 | 43,895 |
| uncore | 2,321 | 76,942 |
| serial clock | 322 | 322 |
| initialized external owners | 6 | 6 |

This includes **500 logical memories / 310,493 words** and **8,144 register
words**, including explicit memory pipeline state. Off-boundary functional DRAM
and host services are represented by the actual complete boundary input trace
for finite Level-2 replay; their restoration remains a Level-1 obligation.
The observer's own counters, cursors, handles and diagnostic files are separate
observation owners with no Level-1 restore adapter. CPU Level-1 admission
therefore stays disabled.

The current exact recipe build in `native-build/` executes Y-2026.03-SP1 VCS,
`-full64`, GCC/G++ 13 and `-Mupdate`, with all three original semantic discovery/
preservation flags. Its 62-unit native audit explicitly accounts for the 60
original recipe translation units plus `fame_capture.cc` and
`semantic_restore.cc`. This read-only diagnostic extension does not authorize a
CPU Level-1 profile. The exact recipe settings remain:

```text
PLATFORM=f2
TARGET_PROJECT=firesim
TARGET_PROJECT_MAKEFRAG=generators/firechip/chip/src/main/makefrag/firesim
DESIGN=FireSim
TARGET_CONFIG=WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig
PLATFORM_CONFIG=WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config
```

The first **real captured C=100** cut passes complete zero-edge readback and
ordinary pre-FAME RTL replay in `replay-pilot-100/`: **318,637 words**, **64 clock
events**, and **85 outputs per event** at original event indices 200..263 and
target cycles 100..132. All six mbus/tile/serial domains have 100 completed
rises at this cut; uncore has 50. No replay clock ratio is inferred.
The early negative pilot in `native-replay-early/` passes all four actual
per-hart CSR counter bit faults at its first divergent boundary, four atomic
invalid native loads and seven pre-publication invalid-image checks. Its
initial artifact catalog includes its own pre-final summary hash; accepted
final evidence must use the corrected catalog and independent auditor.

Accepted final-format native groups pass C=100 and C=700000 in
`native-replay-first/invocation-1fl2_ahc/summary.json`, plus C=900000 in
`native-replay-memory/invocation-ukuzwqaz/summary.json`. Both separate audits
pass **192 event samples / 16,320 output comparisons**, **twelve actual per-hart
first divergences**, **twelve atomic native-loader rejections** and **21 invalid
container/build/owner/boundary rejections**. Every cut restores and reads back
all **318,637 words before any of seven clocks rises**. At C=900000 the real
stored D-cache `cached_grant_wait` flags are nonzero in tiles 1 and 2, and
`release_state` is nonzero in tiles 0 and 3. All external AXI valid signals are
idle in this window; the outstanding evidence is internal cache traffic.

All eight preserved native suites pass with stable sources in
`native-regressions-final/invocation-zbkpupur/summary.json`, including FCFS and
**280 Python tests / 5,276 artifacts / 809 source bindings**. All **30 retained
audits** pass. The earlier native regression invocation finished every check but
rejected a source-stability guard while the new capture runner/auditor were
corrected; its logs remain separate from accepted evidence.

The complete source run now **passes at the reported fastest-clock
C=3,329,794**. `complete-source-control-summary.json` binds all four complete
instruction traces and all self-checking workload/store labels to the
uninterrupted reference. All nine mapped semantic/generated sidecars match the
running exact-recipe metasim build in `native-map-metasim-binding.json`.
`source-end-clock-audit.json` distinguishes the reported bridge count
(3,329,794) from the event observer's logged completed mbus rises (3,329,793).
All image and replay labels use the observed original-clock counts.
The late C=3250000 suite also passes, with its exact invocation recorded in
`selected-results.json`. Its independent audit completes **four cuts / 256
captured events / 21,760 output comparisons**, **16 actual per-hart first
semantic divergences**, **16 atomic malformed native loads** and **28 invalid
container/build/owner/boundary rejections**. All **36 native positive/fault/
invalid processes** are fresh. Every positive and fault run reads all **318,637
words before any of seven clocks rises**. Native commands, input archives,
workload/source hashes, images, raw traces and all results are cataloged in
`verification-commands.json`, `raw-native-commands.json`, `native-input-archives.json`,
`summary.json` and `artifact-manifest.json`.

Workload ELF SHA-256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The early C=100 window is real BootROM execution in the same completed source
run; the warmed, outstanding-cache and late windows execute the actual workload
on all four cores. This is finite Level-2 acceptance for the explicit ChipTop
boundary. Complete Level-1 fresh-process CPU continuation and its remaining
session/context/simulator/bridge/memory owners remain pending. No physical FPGA
or ASIC result is claimed, and no other CPU recipe is marked supported.

Executable native replay checks from the Chipyard root (each replay invocation
allocates a fresh artifact directory):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 100,700000 \
  --out automations/checkpoint_loop/runs/m11-iteration139/native-replay-first
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 900000 \
  --out automations/checkpoint_loop/runs/m11-iteration139/native-replay-memory
python -m tools.checkpoint_formats.tests.verify_fame_event_replay_vcs \
  --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --capture automations/checkpoint_loop/runs/m11-iteration139/runtime-pilot/capture \
  --cuts 3250000 \
  --out automations/checkpoint_loop/runs/m11-iteration139/native-replay-late
python -m tools.checkpoint_formats.tests.audit_fame_event_replay \
  --summary automations/checkpoint_loop/runs/m11-iteration139/native-replay-first/invocation-1fl2_ahc/summary.json
python -m tools.checkpoint_formats.tests.audit_fame_event_replay \
  --summary automations/checkpoint_loop/runs/m11-iteration139/native-replay-memory/invocation-ukuzwqaz/summary.json
python automations/checkpoint_loop/runs/m11-iteration139/repeat-native-regressions-final.py
```

`native-build-command.json` and `capture-command.json` retain the exact native
Make and complete 16-GiB workload commands actually executed in this iteration.
To reproduce the whole build/capture in a new directory, the maintained
`verify_rocket_fame_capture_vcs` runner accepts `--seed-build`, `--out`,
`--workload`, `--reference-runtime` and `--reference-audit`. It selects the same
six exact recipe settings and explicit semantic flags, and owns its new monitor,
build, source snapshots, workload logs and complete instruction traces.

## Iteration 138: preserve original semantic owners through FAME

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/`.
Both CPU checkpoint levels remain **in_progress**. The opt-in compiler map now
carries every original StateID through actual path resolution, inlining, FAME
and emitter renames. It preserves original storage, including constant-driven
registers, memory pipelines and exact initialized external owners. It rejects
missing, duplicated, aliased, reshaped or ambiguously replicated owners. See
[semantic-fame-state-map.md](semantic-fame-state-map.md).

The exact-recipe compiler output in `rocket-semantic-map-sealed/` maps all
**8,644 entries / 318,637 words** against **11,746 generated state entries**.
Original semantic manifest SHA-256 is
`c699c362e7531022810106dee9b7710c9cb4b5d00311baeffc55b84f83681521`;
map SHA-256 is
`0e41975c45339c36e4a4bcb97525cafad0c711367f4cb4ea53cea415c658881d`.
The independent declaration audit checks complete original membership, every
mapped kind/width/depth/signedness, generated ownership and exact external models.
The raw `.semantic-fame-emitted.sv` sidecar binds the actual compiler output
before Make appends blackbox sources. Original and generated StateID namespaces
and Level-1/Level-2 image formats remain independent.

The freshly rebuilt ordinary recipe has 11,464 entries / 445,838 generated
words; the preservation build has 11,746 / 446,120 with the same 2,292 instances.
`preserved-storage-delta.json` accounts for exactly **282 additional register
words**, with no removed or reshaped existing owner. Static independent audits
resolve all original state clocks and all **116 ChipTop boundary ports**
(103 data ports, seven clock inputs and six clock aliases). Six original domains
reach target clock buffer 1; uncore reaches buffer 0. These checks establish
static correspondence, with dynamic event phases still requiring capture.

Native Y-2026.03-SP1 VCS probes pass in
`native-map-sealed/invocation-ovekdx0g/summary.json`. All **318,637 original words**
restore and read back in each layout before any edge: transformed `FPGATop` and
ordinary pre-FAME ChipTop. Twelve fresh processes include four malformed loader
requests per layout (missing, duplicate, unknown and wrong-width words), each
rejecting before any deposit and retaining complete baseline readback. Actual
post-restore corruption of Rocket BTB `idxPages_23` is detected by native readback
in both layouts. All three actual transformed clock-buffer outputs and all
seven ordinary boundary clocks remain at zero edges. The independent
`native-map-independent-audit.json` rechecks every artifact, original word,
loader row, build/run argv, log and process identity. These are deterministic
diagnostic patterns, not captured CPU checkpoint values or target-cycle faults.

All **33 Scala tests** pass, including actual inlining, repeated module owners,
constant-driven registers, Verilog keyword renames, memory pipelines and an
explicit nested simulator root. The two added Python tests cover complete maps
and twelve malformed/incompatible source/membership/shape cases. Four exact-recipe
Make dry runs verify flag admission and reject missing roots, missing multi-clock
opt-in and invalid flag values. These checks do not authorize capture.

All eight preserved native suites pass, including **277 Python tests / 5,270
artifacts / 803 original source bindings** and the existing FCFS checks. All
30 retained audits pass. The prior ordinary Rocket diagnostic probe also
passes all 318,637 words before any of seven clocks advances.

Both default/buffered controls pass in each complete exact-recipe build:
`rocket-controls-final/invocation-vd1ngrsc/summary.json` and
`rocket-mapped-controls/invocation-h497o2iy/summary.json`. The latter enables the
semantic root, multi-clock discovery and storage-preservation flags in the
actual Make/VCS build. All **four complete 16-GiB four-hart controls** pass at
**C=3,329,794**; all sixteen full hart traces and workload/store-cycle labels
match the uninterrupted reference. Workload ELF SHA-256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
`native-map-metasim-binding.json` binds five byte-identical map/raw-RTL/original
and generated manifest/reference files between the native probe and the actual
running preservation-enabled metasim executable. These are full uninterrupted
workload controls, with no CPU checkpoint continuation or captured replay claim.
Both independent control audits pass. The preservation-specific auditor
retains every original control audit and additionally pins the full mapping
artifacts and all three explicit compiler flags; the default audit retains its
original strict inventory totals. Recovery catalogs are `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json`, `summary.json` and `artifact-manifest.json`.
The independently checked input archive preserves original source snapshots
across later controller checkpoints.

Executable native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_semantic_fame_map_vcs \
  --base automations/checkpoint_loop/runs/m11-iteration138/rocket-semantic-map-sealed/FireSim-generated \
  --out automations/checkpoint_loop/runs/m11-iteration138/repeated-native-map
python -m tools.checkpoint_formats.tests.audit_semantic_fame_map \
  --summary automations/checkpoint_loop/runs/m11-iteration138/native-map-sealed/invocation-ovekdx0g/summary.json
make -C sims/firesim/sim testOnly FIRESIM_SBT_PROJECT=midas SCALA_TEST='midas.checkpoint.*'
python automations/checkpoint_loop/runs/m11-iteration138/repeat-native-regressions-final.py
python automations/checkpoint_loop/runs/m11-iteration138/run-mapped-controls.py \
  --out automations/checkpoint_loop/runs/m11-iteration138/repeated-mapped-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration138/rocket-mapped-controls/invocation-h497o2iy/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048 \
  --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc
```

Native commands use both repository environments, then `vcs-env.sh` last,
Y-2026.03-SP1, `-full64` and GCC/G++ 13; reused Make builds use `-Mupdate`.
Compiler sources, assembly and exact recipe are preserved in `compiler-inputs.json`.
Failed compiler/root-binding pilots and source-change guard rejections remain
separate from accepted evidence. Both plans and environment helpers retain
their original bytes. The controller's iteration-137 commits were published
FireSim first, then Chipyard; both remote tips match despite rejected local
tracking-ref updates in read-only `.git`.

Next: bind actual FAME clock events and complete original boundary traffic,
capture real four-hart workload state at early/warmed/outstanding-memory/late
cuts, then fresh ordinary RTL zero-edge readback and captured finite replay.
Complete configuration-specific Level-1 ownership and fresh CPU continuation
also remain pending. `capture_supported` remains false; neither CPU checkpoint
level is accepted. BOOM/Saturn remain pending. No external dependency is missing.
Standalone Shuttle, physical FPGA and ASIC power remain outside this task.

## Iteration 137: continue restored pending direct exits through provider stop

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration137/`.
Both CPU checkpoint levels remain **in_progress**. The fourteen-owner group now
provides `advance_pending_exit()` and complete stopped-caller inspection.
Before any service, it checks every protocol owner, actual provider raw status,
blocked/pending/delivered signals, installed handlers and signature policy. The
private explicit caller finishes only the pending `fromhost` read/write and the
exit condition, then calls the actual no-signature provider stop. An occupied
mailbox preserves the queued response. Repeated exit service, ordinary polling
and `tick()` reject without changing the completed owners. No session, device
dispatch, startup or context entry occurs. Stopped-image restore and the actual
session destruction/return/context caller remain unsupported. See
[tsi-polling-lifecycle.md](tsi-polling-lifecycle.md).

Accepted aggregate invocation:
`aggregate-corrected/invocation-tm06fhlk/summary.json`.
Native ASan/UBSan and Y-2026.03-SP1 VCS pass the full previous matrix:
**1,936 captured host cuts / 3,872 fresh fourteen-owner readbacks**, including
1,105,584 continued host operations / 15,532,384 owner readbacks, 5,132 invalid
image/membership/cross-owner rejections, 3,012 allocation failures and 24 final
provider guards. The added **256 pending-exit continuations** pass **1,664 host
operations / 30,464 complete owner readbacks**, across eight original raw exit
payloads and all four producer/destination backend pairings. All intermediate
states match both the finished original caller and independent byte oracles.
Stopped boundaries retain their actual FIFO contents rather than substituting
the final drained queue. Thirty-two actual response-bit corruptions stop at
**original host operation 30 / request word 3**, expected 321 / actual 320,
without consuming the divergent word. Twenty-four late provider/signal changes
reject before service and preserve every protocol peer. These are host-operation
labels with zero DUT edges, not target-cycle CPU checkpoint cuts.

`recipe-pending-exit-d2zrsbaf/summary.json` repeats all 256 continuations, 30,464
owner readbacks, 32 first divergences and 24 service guards using a separate
native/VCS build linked to the **actual archive in this iteration's exact-recipe
Rocket executable**. Its SHA-256 is
`36646c4e1c7eab0b626be572a2e1a3174f4bae3686884341ad07d6302fa7a63e`.
`occupied-exit-2uflihjh/summary.json` additionally captures real production callers
with occupied mailbox values 7, 4294967296 and 18446744073709551615. Across all
eight raw exit payloads and four backend pairings, **768 fresh continuations /
3,456 host operations / 69,888 owner readbacks** preserve the queued response
and issue no extra write. Separate aggregate, recipe-provider and occupied-mailbox
audits pass; each binds all bytes, commands, native inputs and backend/cut coverage.

All eight preserved native suites pass (275 Python tests / FCFS included;
5,258 artifacts / 798 source bindings), as do all 30 retained audits. Ordinary
Rocket RTL again reads all 318,637 diagnostic words / seven clocks before any
edge. Both exact-recipe full 16-GiB four-hart controls pass at **C=3,329,794**
in `rocket-controls-final/invocation-8vn9ksop/summary.json`. All eight complete
hart traces and workload/store cycle labels match the uninterrupted reference.
The self-checking workload ELF SHA-256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Separate control/host audits pass eight active samples / 64 known component
images, including the late sample. Complete twelve-owner preparation and
continuation also pass all 2,976 fresh cases / 744 cuts, with 1,105,584 host
operations / 13,302,720 owner readbacks and eight first divergences. Active
dispatch and bound three-owner tests pass with their independent audits. The
actual recipe-linked lifecycle suite retains 440 atomic transactions and twenty
first divergences. The preserved actual-provider raw-bit fault suite passes all
32 first divergences / 96 atomic cross-owner rejections; candidate copy/move/
private-publication negatives and C++17 construction pass. All twelve commands
and independent audits in `host-regressions-summary.json` pass.

Recovery catalogs: `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `summary.json` and
`artifact-manifest.json`. The supplemental occupied-mailbox checker uses the
recipe's original native source snapshots and retained-source guards, preserving
its provenance across later controller source commits. Immutable binaries and
native inputs still require identical bytes; all 768 cases reran with this
checker. These diagnostic/host checks do not establish
a complete `.fsckpt`, captured CPU `.rtlckpt` or boundary `.trace` replay.

Executable native checks, from Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_lifecycle_vcs \
  --pending-exit --out automations/checkpoint_loop/runs/m11-iteration137/repeated-aggregate
python -m tools.checkpoint_formats.tests.verify_tsi_polling_lifecycle_vcs \
  --audit automations/checkpoint_loop/runs/m11-iteration137/aggregate-corrected/invocation-tm06fhlk/summary.json
python automations/checkpoint_loop/runs/m11-iteration137/verify-recipe-pending-exit.py \
  --capture automations/checkpoint_loop/runs/m11-iteration137/aggregate-corrected/invocation-tm06fhlk/summary.json \
  --identity automations/checkpoint_loop/runs/m11-iteration137/rocket-controls-final/invocation-8vn9ksop/rocket-build-identity.json
python automations/checkpoint_loop/runs/m11-iteration137/verify-occupied-exit.py \
  --recipe-summary automations/checkpoint_loop/runs/m11-iteration137/recipe-pending-exit-d2zrsbaf/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration137/repeated-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration137/rocket-controls-final/invocation-8vn9ksop/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048 \
  --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc
python automations/checkpoint_loop/runs/m11-iteration137/repeat-native-regressions.py
python automations/checkpoint_loop/runs/m11-iteration137/repeat-ordinary.py
```

Exact build/compiler/VCS arguments, source snapshots, original workload plans,
images, complete pre-service readbacks and intermediate/final comparisons are
bound in each invocation summary. Every VCS invocation inherits both repository
environments and `vcs-env.sh` sourced last, using Y-2026.03-SP1, `-full64`,
GCC/G++ 13 and `VCS_FLAGS=-Mupdate` for the reused Make build. Initial checker
compilation/FIFO-comparison diagnostics and source-change guard rejections are
retained separately and excluded from passing evidence. Complete CPU ownership,
coherent early/warmed/outstanding-memory/late cuts, fresh complete Level-1
continuation and independently captured Level-2 replay remain pending. There
is no missing external dependency. BOOM/Saturn remain pending; standalone
Shuttle, physical FPGA and ASIC power remain outside this task.

## Iteration 136: publish polling, direct-exit and lifecycle owners atomically

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration136/`.
Both complete CPU checkpoint levels remain **in_progress**. The new opt-in
fourteen-owner group prepares the twelve sealed polling owners, direct-exit
recorder and actual private HTIF lifecycle fields before any publication.
The final provider guard precedes nonthrowing swaps of every prepared peer.
It compares full optional presence, raw status and stopped state, preserving
absent versus present-zero and raw low-bit differences. See
[tsi-polling-lifecycle.md](tsi-polling-lifecycle.md).

Native ASan/UBSan and Y-2026.03-SP1 VCS pass **1,936 captured host cuts** and
**3,872 fresh fourteen-owner readbacks**, across all four producer/destination
backend pairings. This includes every prior 744 polling/identity host-operation
cut and all admitted running/requested cuts for eight original direct-exit
payloads. The **256 requested-exit readbacks** preserve actual provider raw
status and queued response traffic. Requested exits remain readback-only;
`tick()` and explicit polling continuation reject without consuming a service.
Stopped-parent boundaries explicitly reject. No complete exit/stop caller,
session/descriptors/signals/outer context or CPU continuation is inferred.

All **1,105,584 continued host operations / 15,532,384 complete owner readbacks**
match the finished producers and independent byte oracles. All **5,132 invalid
image/membership/cross-owner rejections**, **3,012 allocation failures** and
**24 late-provider guards** pass without partial publication. Candidate
abandonment, three late-peer mutations, consumed/competing candidates and
release of the input images before commit pass in all four backend pairings.
Separate native copy/move/private-publication compile negatives reject;
C++17 return-by-value construction passes.

A second native ASan/UBSan/VCS build uses the **actual archive linked into this
iteration's exact-recipe Rocket executable**. Thirty-two fresh fourteen-owner
restores pass 448 complete owner readbacks across all eight direct-exit
payloads and four backend pairings. Each process atomically rejects three
cross-owner images (96 total), including a raw low-bit mismatch with the same
`exit_code()` projection. After successful restore, the test changes the actual
provider's optional raw field by one bit. All **32 actual semantic faults**
report their first divergence at host boundary zero,
`owner=lifecycle.raw_exit`, without acknowledging serial traffic. This is a
host-component fault, not a DUT target-cycle corruption case. Accepted summary:
`raw-fault-rj61ff0w/summary.json`; separate audit:
`aggregate-raw-fault-independent-audit.json`. The earlier diagnostic-only C++
declaration error is retained in `raw-fault-8qt9ukh7/native-build.log` and is
excluded from passing evidence.

Accepted complete invocation:
`aggregate-pilot/invocation-9a5cvr7q/summary.json`.
The name retains its initial build label; this invocation ran the full matrix.
`aggregate-independent-audit.log` independently rechecks every retained byte,
all backend/cut memberships, complete initial/continued images and actual
command exits. `candidate-types/summary.json` records the separate type checks.
These are host-operation boundaries with zero DUT edges, not the required
active CPU checkpoint target-cycle cuts. There is no `.fsckpt`, captured CPU
`.rtlckpt` or replay `.trace` acceptance.

Executable native checks, from Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_lifecycle_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration136/repeated-aggregate
python -m tools.checkpoint_formats.tests.verify_tsi_polling_lifecycle_vcs \
  --audit automations/checkpoint_loop/runs/m11-iteration136/aggregate-pilot/invocation-9a5cvr7q/summary.json
python automations/checkpoint_loop/runs/m11-iteration136/verify-aggregate-raw-fault.py
python automations/checkpoint_loop/runs/m11-iteration136/audit-aggregate-raw-fault.py
```

The invocation's `summary.json` includes every exact native compiler/VCS
argument, source snapshot, workload plan/input hash and readback artifact hash.
VCS uses `-full64` and GCC/G++ 13. Every invocation is launched after both
repository environments and `vcs-env.sh` last; child processes inherit it.

The exact-recipe four-hart controls use the original self-checking workload
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Both full 16-GiB default/buffered controls pass at C=3,329,794 in
`rocket-controls/invocation-5xd7i_is/summary.json`. Every full hart trace and
workload/store cycle label matches the uninterrupted reference. The separate
control/host audits pass eight active samples / 64 known component images,
including the late cut. These remain uninterrupted CPU controls and partial
host inspections, not checkpoint restores. The preserved twelve-owner suite
passes all 2,976 fresh preparations and continuations / 744 cuts, including
eight first divergences; active dispatch and bound three-owner tests pass with
their separate audits. All eight preserved native suites pass (275 Python
tests / FCFS included; 5,258 artifacts / 798 source bindings), as do all 30
retained audits. Ordinary Rocket RTL passes the 318,637-word / seven-clock /
zero-edge diagnostic readback; captured CPU replay is still pending. The exact-recipe controls,
preserved regressions and their independent audits are recorded in this
iteration's `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `summary.json` and
`artifact-manifest.json`. Complete
configuration-specific simulator/bridge/memory ownership, coherent CPU cuts,
full fresh Level-1 continuation and independently captured Level-2 replay
remain pending. BOOM/Saturn remain pending. Standalone Shuttle, physical FPGA
validation and ASIC power remain outside this task.

## Iteration 135: preserve retained builds across auditor evolution

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration135/`.
Both CPU levels remain **in_progress**. The previous controller's continuation
sweep failed its final source check because the preparation auditor had evolved
after the retained native build. Its original hash is
`a6e9a77a9bed36f0def2510b4c7cdafdc19fe1659e31a604346c71168d1d9619`;
the current auditor hash is
`0dd996dca8142af9eb8cfc3d071ae031c20cd554135f05970cb3385ef3b2dfed`.
All 65 inherited non-Python dispatch build inputs still match. See
[native-input-provenance.md](native-input-provenance.md) for the validation
contract. No production state owner or CPU admission changed this iteration.

The new guard audits inherited snapshots, archives each invocation's live
inputs before native execution, and rejects later source changes. New dispatch
compilation requires unchanged C++/SV, headers, libraries and environment
scripts before starting either compiler. Independent audits bind guard
requirements to the executed checker snapshot and require complete membership
and unchanged native compilation identities. Historical reports remain
auditable. Eleven focused tests pass, including auditor evolution, edits during
execution, changed compiled headers/binaries, missing/duplicate inputs and
forged or omitted guards. Five separately resealed invocation-evidence mutations
reject; these are auditor tests, separate from actual semantic corruptions.

All 275 Python tests and all eight preserved native suites pass, retaining
5,256 artifacts / 796 source bindings. All 30 retained audits pass. The actual
recipe-linked lifecycle suite passes 1,216 captures, 2,432 fresh provider
readbacks, 88 optional/raw/stopped restores, 282 malformed images, eighteen
guards, twenty first divergences, 440 atomic transactions and three compile
rejections. The bound three-owner suite passes 224 fresh restores, 6,160 host
operations, 19,824 owner readbacks, 932 malformed images, 32 membership errors,
four binding errors, sixty allocation failures and eight first divergences.
Active dispatch passes all eight semantic corruptions at host operation 111 /
request word 1 without consuming the faulty word. Their independent audits
pass. Ordinary Rocket RTL diagnostic readback passes 318,637 words / seven
clocks / zero edges; coherent CPU capture and finite replay remain pending.

The complete native ASan/UBSan and VCS sweeps pass 2,976 preparations and
2,976 fresh continuations across all 744 cuts. Continuation passes 1,105,584
host operations and 13,302,720 complete owner readbacks; twenty unowned commands
and four external exits reject before service. All eight semantic corruptions
stop at their first divergent request word without consuming it. Preparation
rejects 4,368 malformed images, 244 membership errors, 44 cross-owner/config
errors and 2,904 allocation failures before publication. Candidate guards
additionally pass all twelve late-peer changes, 172 commit-allocation failures
and eight consumed/competing rejections. Both independent audits pass. The
continuation command deliberately reuses iteration 134's preparation summary,
reproducing the controller's formerly failing provenance path.

Both exact-recipe four-hart controls pass at **C=3,329,794**, each with
**16 GiB** memory. All eight complete hart traces and every workload/store
cycle label match the uninterrupted reference. All eight active host samples /
64 known component images match, including the late sample. Requested credits
are `0,520064,700032,900096,3250048`; active samples retain credit plus one
clock tokens. Separate control and host audits pass. These are uninterrupted
controls and partial host inspections, not complete CPU checkpoint restores.
Workload ELF SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The generated simulator inventory remains 11,464 entries / 445,838 words;
complete ownership/admission is pending and the CPU profile remains disabled.

`selected-results.json`, `verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json`, `summary.json` and `artifact-manifest.json` catalog
exact source/workload/build hashes, native commands, images, readbacks, traces
and negative cases. `source-guard-evolution.json` binds both auditor versions;
`failure-analysis.json` and `previous-verification.log` preserve the original
controller failure. Production C++ and all maintained checker sources stayed
unchanged during these native runs. Plans and environment helpers retain their
initial hashes. Existing controller iteration-134 commits were published
FireSim first, then Chipyard; no staging or local commits. No missing external
dependency is known. Complete fresh Level-1 CPU continuation and independently
captured Level-2 readback/replay remain pending, along with aggregate lifecycle,
session, descriptor, signal, context, simulator, bridge and memory ownership.

Accepted component summaries relative to the diagnostic root above:

- `polling-preparation/invocation-wrshg5gy/summary.json`
- `polling-continuation/invocation-92r4gved/summary.json`
- `polling-dispatch/invocation-ecf6k0o9/summary.json`
- `polling-devices/invocation-x3yd_8ce/summary.json`
- `recipe-lifecycle/invocation-gfp310ng/summary.json`
- `rocket-controls/invocation-38rhy04q/summary.json` (uninterrupted controls)
- `native-regressions/invocation-h0tkdoou/summary.json`
- `ordinary-npdvaijd/summary.json` (diagnostic pattern, no captured replay)

Executable checks from the Chipyard root, with the license/compiler helper
sourced last. Each native checker allocates new invocation paths:

```bash
source env.sh
source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_prepare_vcs --identity \
  --out automations/checkpoint_loop/runs/m11-iteration135/controller-rechecks/polling-preparation
python -m tools.checkpoint_formats.tests.verify_tsi_polling_continue_vcs --identity \
  --preparation-summary automations/checkpoint_loop/runs/m11-iteration134/polling-preparation/invocation-2fn8v3ab/summary.json \
  --out automations/checkpoint_loop/runs/m11-iteration135/controller-rechecks/polling-continuation
python -m tools.checkpoint_formats.tests.verify_tsi_polling_dispatch_vcs \
  --preparation-summary automations/checkpoint_loop/runs/m11-iteration134/polling-preparation/invocation-2fn8v3ab/summary.json \
  --out automations/checkpoint_loop/runs/m11-iteration135/controller-rechecks/polling-dispatch
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration135/controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration135/rocket-controls/invocation-38rhy04q/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048 \
  --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc
python -m tools.checkpoint_formats.tests.verify_tsi_htif_lifecycle_vcs \
  --recipe-build-identity automations/checkpoint_loop/runs/m11-iteration135/rocket-controls/invocation-38rhy04q/rocket-build-identity.json \
  --out automations/checkpoint_loop/runs/m11-iteration135/controller-rechecks/recipe-lifecycle
python automations/checkpoint_loop/runs/m11-iteration135/repeat-native-regressions.py
python automations/checkpoint_loop/runs/m11-iteration135/repeat-ordinary.py
```

## Iteration 134: separate polling preparation and publication

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration134/`.
Both CPU levels remain **in_progress**. The twelve-owner polling component
coordinator now owns parsed candidates without publishing them, rechecks the
fresh destination at commit, and publishes using nonthrowing operations. The
bound three-owner poll/BCD/terminal path provides its private preparation
primitive. See [tsi-polling-preparation.md](tsi-polling-preparation.md).
Lifecycle/direct-exit/session/context integration and complete CPU ownership
remain pending. No restored target edge or captured CPU replay is claimed.

The 744-cut native ASan/UBSan and VCS preparation suite passes **2,976 fresh
preparations**, with 4,368 malformed images, 244 membership errors, 44
cross-owner/configuration errors and 2,904 injected allocation failures rejected
before publication. Every successful candidate owns its input replacements and
rejects reuse. Four additional native/VCS producer/destination guard processes
pass abandonment, twelve late-peer changes, 172 commit-allocation failures and
eight consumed/competing-candidate rejections. Native compilation rejects both
copying and moving candidates and accepts C++17 return-by-value construction.
The actual exact-recipe binary independently contains all three new APIs.

The bound three-owner suite passes 224 fresh restores, 6,160 host operations,
19,824 owner readbacks, 932 malformed images, 32 membership rejections, four
binding rejections, 60 allocation failures and eight first divergences. The
actual recipe-linked lifecycle suite passes 1,216 captures, 2,432 fresh provider
readbacks, 88 raw/optional/stopped restores, 282 malformed processes, eighteen
guards, twenty first divergences, 440 atomic transactions and three compile
rejections. Their separate independent audits pass. All eight preserved native
suites pass (268 Python tests / FCFS included; 5,254 artifacts / 794 source
bindings), as do all 30 retained audits both before and after the final auditor
hardening. Ordinary Rocket RTL diagnostic readback
passes 318,637 words / seven clocks / zero edges; captured CPU replay is pending.

The complete twelve-owner continuation suite passes **2,976 fresh processes**,
**1,105,584 host operations** and **13,302,720 complete owner readbacks**.
Twenty unowned commands and four external exits reject before service; all
eight deliberate semantic corruptions stop at their first divergent request
word without consuming it. These are host-operation boundaries, not CPU target
cuts. Active-dispatch checks independently pass eight invalid-image processes,
9,312 malformed images, 392 membership errors, 104 cross-owner errors and 5,832
allocation failures. Eight actual semantic corruptions first diverge at host
operation 111, request word 1: expected 1,634,038,461 versus 1,634,038,460 for a
merge-byte fault or 189 for a command/payload fault. Neither divergent word is
consumed.

Both complete exact-recipe four-hart controls pass at **C=3,329,794**, each with
**16 GiB** target memory. All eight complete hart traces and every workload/store
cycle label match the uninterrupted reference. Eight active host samples / 64
known component images match, including the late sample. Requested credit labels
are `0,520064,700032,900096,3250048`. Active samples retain credit plus one
clock tokens; credit zero has zero tokens and rejects incomplete startup.
These are uninterrupted controls and partial host inspections, not restored CPU
cuts. Workload ELF SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The generated simulator inventory remains 11,464 entries / 445,838 words; full
ownership/admission is pending and the CPU checkpoint profile remains disabled.
Separate control and host/trace audits pass.

Five separately resealed auditor-evidence mutations reject: omitted split
contract, omitted guard pairing, lost input-lifetime marker, incomplete late
guards and unbound guard command. The maintained auditor binds the split
contract to the executed header snapshot and keeps earlier reports compatible.
These are auditor tests; the actual component semantic faults are recorded
separately above. The final 268-test Python suite passes after auditor hardening.
No missing external dependency is known.
Standalone Shuttle, physical FPGA and ASIC power remain outside this task;
BOOM/Saturn remain pending.

Accepted invocation summaries (relative to the diagnostic root above):

- `polling-preparation/invocation-2fn8v3ab/summary.json`
- `polling-continuation/invocation-eq_10vp8/summary.json`
- `polling-dispatch/invocation-5svpow5e/summary.json`
- `polling-devices/invocation-3mpohwsu/summary.json`
- `recipe-lifecycle/invocation-_71vif27/summary.json`
- `rocket-controls/invocation-92nr2hl7/summary.json`
- `native-regressions/invocation-ay_52sg4/summary.json`
- `ordinary-eutayxo7/summary.json` (diagnostic pattern, no captured replay)

`selected-results.json`, `verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json`, `final-auditor-inputs.json`, `summary.json` and
`artifact-manifest.json` catalog exact commands, original source snapshots,
workload/build hashes, images/readbacks, traces and negative cases. The final
auditor changes only evidence checking; production C++ stayed unchanged during
all native builds and simulations. The initial relative-path guard pilot is
excluded because its ELF/terminal arguments differed from the captured absolute
paths; the corrected pilot and all four final guard pairings pass.
Existing controller iteration-133 commits were published FireSim first, then
Chipyard, and both GitHub main tips match. No staging or local commits.
Both plans and environment helpers retain their initial hashes. Complete CPU
cut rejection/fault coverage, Level-1 continuation and independent captured
Level-2 readback/replay remain pending.

Repeat the current increment from the Chipyard root (every VCS shell sources
the helper last):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_prepare_vcs --identity \
  --out automations/checkpoint_loop/runs/m11-iteration134/controller-rechecks/polling-preparation
python -m tools.checkpoint_formats.tests.verify_tsi_polling_continue_vcs --identity \
  --preparation-summary automations/checkpoint_loop/runs/m11-iteration134/polling-preparation/invocation-2fn8v3ab/summary.json \
  --out automations/checkpoint_loop/runs/m11-iteration134/controller-rechecks/polling-continuation
python -m tools.checkpoint_formats.tests.verify_tsi_polling_dispatch_vcs \
  --preparation-summary automations/checkpoint_loop/runs/m11-iteration134/polling-preparation/invocation-2fn8v3ab/summary.json \
  --out automations/checkpoint_loop/runs/m11-iteration134/controller-rechecks/polling-dispatch
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration134/controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration134/rocket-controls/invocation-92nr2hl7/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048 \
  --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc
```

## Iteration 133: lifecycle preparation before peer publication

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration133/`.
Both Rocket checkpoint levels remain **in_progress**. The lifecycle adapter
now prepares a destination-bound, noncopyable, nonmovable, single-use candidate.
Preparation checks actual provider/destination guards without assignment;
commit repeats those guards before a `noexcept` callback publishes already
prepared peers, then assigns the private lifecycle fields without allocation.
The ordinary component loader uses the same path. The twelve-owner polling
aggregate remains unchanged. See
[tsi-htif-lifecycle-preparation.md](tsi-htif-lifecycle-preparation.md) for the
contract and concrete remaining aggregate work.

Both standalone and actual recipe-linked provider suites pass, each with
**440 paired lifecycle/serial-FIFO transactions**, **three compile rejections**,
**1,216 production source captures, 2,432 fresh final-class TSI readbacks,
88 optional/raw/stopped restores, 282 malformed-image processes, eighteen
provider guards and twenty boundary-zero raw-status divergences**.
Every malformed image rejects both preparation and ordinary loading.
The paired transaction tests preserve complete peer images on abandoned,
invalid-peer, changed-signal and occupied-destination cuts and reject duplicate
commit even when the restored lifecycle is entirely empty. These are host
component cuts, not coherent CPU checkpoint cuts or DUT faults.

Accepted summaries: `lifecycle/invocation-arsi0u2h/summary.json` and
`recipe-lifecycle/invocation-nu6bqm1v/summary.json`; independent audits:
`lifecycle-independent-audit.log` and
`recipe-lifecycle-independent-audit.log`. Five separately resealed evidence
mutations reject in `transaction-auditor-rejections.json`. Those are synthetic
auditor inputs, not altered native executions. Production Make provider
selection/header rejection passes (`provider-make/invocation-l17wwtyh/summary.json`),
as do eight read-only incompatible-build rejections
(`build-rejections/invocation-dqbahhmo/summary.json`).

All **eight preserved native suites** pass, including **268 Python tests**,
FCFS, fixture metasim/replay, banked capture and bridge checks:
`native-regressions/invocation-rak8ogkj/summary.json` (5,254 artifacts /
794 source bindings). The independent completed-suite audit passes in
`native-independent-audit-final.log`; an initial audit ran before the final
native check finished and is excluded. All **30 retained independent audits**
pass (`retained-rechecks/invocation-52hndpl4/summary.json`). Fresh ordinary
Rocket RTL VCS passes the complete **318,637-word / seven-clock / zero-edge
diagnostic readback** (`ordinary-i98t7inx/summary.json`). Captured CPU
readback/replay remains pending.

The exact recipe was rebuilt with all six settings above, the opt-in provider,
`VCS_FORCE_REBUILD=1`, `VCS_FLAGS=-Mupdate`, pinned Y-2026.03-SP1, `-full64`
and GCC/G++ 13. Executed build identity:
`rocket-controls/invocation-tbfiwdyq/rocket-build-identity.json`.
The workload ELF remains SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Both full **16 GiB / four-hart controls** pass at **C=3,329,794**:
`rocket-controls/invocation-tbfiwdyq/summary.json`. All eight full hart traces,
every workload/store label and instruction-retirement count match the
uninterrupted reference. All **eight active host samples / 64 known component
images** match at credits 520,064, 700,032, 900,096 and 3,250,048; clock-token
labels equal credit + 1. Credit zero preserves its startup rejection. These
are uninterrupted controls and host-component samples, not complete CPU
checkpoints. The independent control audit and full host audit pass in
`rocket-controls-independent-audit.log` and `rocket-host-audit.json`.
Five contradictory/untyped provider flags reject in the independent auditor
(`audit-provider-flags.json`). Native `nm` independently confirms all four
lifecycle APIs in the actual recipe object, whose hash matches the executed
build identity (`provider-symbols.json`). Generated inventory remains
11,464 entries / 445,838 words, with complete CPU ownership pending.

Recovery catalogs: `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `native-input-archives.json`, `summary.json` and
`artifact-manifest.json`. Source snapshots precede compilation and remain
unchanged through both complete controls. Native builds and simulations source
both environments then `vcs-env.sh` last. No FPGA implementation is invoked.

Executable native commands from the Chipyard root:

```bash
source env.sh
source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_htif_lifecycle_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration133-controller-rechecks/lifecycle \
  --recipe-build-identity automations/checkpoint_loop/runs/m11-iteration133/rocket-controls/invocation-tbfiwdyq/rocket-build-identity.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration133-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration133/rocket-controls/invocation-tbfiwdyq/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048 \
  --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc
python automations/checkpoint_loop/runs/m11-iteration133/repeat-native-regressions.py
python automations/checkpoint_loop/runs/m11-iteration133/repeat-ordinary.py
python -m tools.checkpoint_formats.tests.verify_tsi_htif_lifecycle_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration133/recipe-lifecycle/invocation-nu6bqm1v/summary.json
```

Complete CPU Level-1 continuation, captured Level-2 readback/replay and required
CPU-cut negative/fault cases remain pending. No missing external dependency is
known. BOOM/Saturn remain pending; physical FPGA and ASIC power remain deferred.
Both plan files and all environment helpers retain their initial hashes.
Existing controller iteration-132 commits were published FireSim first, then
Chipyard; both remote main tips match. No staging or local commit.

## Iteration 132: exact-recipe HTIF provider selection

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration132/`.
Both levels remain **in_progress**. The actual lifecycle provider is now an
explicit production Make option, `CHECKPOINT_HTIF_SOURCE`, and the recipe
command/control launcher accepts `--htif-source`. All six recipe settings
above remain unchanged. Forced VCS builds link the provider object explicitly,
with a separate lifecycle archive directory and audit of its actual link
inputs, original method bodies, exact header ABI, archive members and symbols.
The control launcher snapshots maintained source inputs before compilation
and rejects changes through the end of the full workloads. See
[tsi-htif-recipe-integration.md](tsi-htif-recipe-integration.md).

The linked exact-recipe archive passes the complete production lifecycle
suite: **1,216 source captures, 2,432 fresh private-field restores, 88 additional
raw/optional/stopped restores, 282 invalid-image processes, eighteen guards
and twenty boundary-zero component first divergences**. Full serial state
remains unchanged during restoration and rejection. Accepted summary:
`recipe-lifecycle/invocation-qzzg2vo_/summary.json`; separate independent audit:
`recipe-lifecycle-independent-audit.log`. These remain host-component tests,
not coherent CPU checkpoint cuts or DUT corruption evidence.

The production Make rule separately passes default/lifecycle/default link
selection and a mismatched-header build rejection that preserves the existing
archive, report and extracted objects (`provider-make/invocation-wp10cevc/summary.json`).
Use `VCS_FORCE_REBUILD=1` when switching providers, as all supplied native recipe
commands do. The installed archive and headers remain unchanged.

All **eight preserved native suites** pass, including **268 Python tests**,
FCFS, fixture metasim/replay, banked capture and bridge checks:
`native-regressions/invocation-rqazv26y/summary.json` (5,254 sealed artifacts /
794 source bindings). All **30 retained independent audits** pass:
`retained-rechecks/invocation-9uwupppu/summary.json`. Fresh ordinary Rocket RTL
VCS passes the complete **318,637-word / seven-clock / zero-edge diagnostic
pattern readback** (`ordinary-result.json`). The 30 audits also pass after the
final independent-auditor hardening. Captured CPU replay is pending.

Both exact-recipe complete four-hart controls pass at **C=3,329,794**, with
full **16 GiB** backing memory. All eight full hart traces, every workload
phase/completion/failure-store/tohost label and instruction-retirement count
match the uninterrupted reference. All **eight active host samples / 64 known
component images** match at credits 520,064, 700,032, 900,096 and 3,250,048;
clock-token labels equal credit + 1. Credit zero retains its startup rejection.
These are known host-component samples during uninterrupted execution, not
coherent complete CPU checkpoints. Accepted control summary:
`rocket-controls/invocation-lnj9j73_/summary.json`; independent audits:
`rocket-controls-independent-audit.log` and `rocket-host-audit.json`.
The generated inventory remains 11,464 entries / 445,838 words.

Eight read-only build-record negative cases reject missing/duplicate provider
objects, missing loader/context/serial owners, incompatible VCS release and
missing 64-bit mode without replacing the destination record
(`build-rejections/invocation-n9vy_gbc/summary.json`). These use altered copies
of the executed log and do not execute the altered native command. The
independent auditor additionally derives provider presence from the actual
link arguments: five false/missing/untyped capability declarations reject
(`audit-provider-flags.json`). The final current-source Python run passes all
268 tests (`final-python.log`).

The workload ELF remains SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Complete CPU Level-1 continuation, Level-2 captured replay, independent complete
state audits and the required CPU-cut negative/fault cases remain pending.
The remaining HTIF session, descriptor, syscall-parent, signal and outer-context
owners are enumerated in the integration note. No external dependency is
missing. BOOM/Saturn remain pending; physical FPGA and ASIC power are deferred.

Executable native checks from the Chipyard root (each native build retains all
six recipe settings and sources `vcs-env.sh` last):

```bash
source env.sh
source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration132-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration132/rocket-controls/invocation-lnj9j73_/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048 \
  --htif-source toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc
python -m tools.checkpoint_formats.tests.verify_tsi_htif_lifecycle_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration132-controller-rechecks/lifecycle \
  --recipe-build-identity automations/checkpoint_loop/runs/m11-iteration132/rocket-controls/invocation-lnj9j73_/rocket-build-identity.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls \
  --summary automations/checkpoint_loop/runs/m11-iteration132/rocket-controls/invocation-lnj9j73_/summary.json \
  --source-archive automations/checkpoint_loop/runs/m11-iteration132/native-input-archives.json
python -m tools.checkpoint_formats.tests.verify_tsi_htif_lifecycle_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration132/recipe-lifecycle/invocation-qzzg2vo_/summary.json
python automations/checkpoint_loop/runs/m11-iteration132/repeat-ordinary.py
```

All exact Make/VCS argv, workload hashes, provider/source hashes, complete
images/readbacks, negative cases and logs are cataloged by
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json`, `selected-results.json`, `summary.json` and
`artifact-manifest.json`. The optional initial live-prefix pilot assumed the
buffered TracerV files existed before finish and is excluded; the corrected
default-prefix diagnostic and both complete final trace comparisons pass.
No staging or local commit. Existing controller iteration-131 commits were
published FireSim first, then Chipyard, and both GitHub main tips match.
Both plans and all three environment helpers retain their initial hashes.

## Iteration 131: actual private HTIF lifecycle fields

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration131/`.
Both Rocket checkpoint levels remain **in_progress**. The opt-in provider
adapter now restores actual `optional<int> exitcode` and `stopped` storage,
including absent/present zero, even raw statuses and the sign bit. Full parsing
and provider guards precede assignments; restoring performs no target service.
The default exact-recipe archive still retains installed `htif.o`; recipe and
aggregate integration of this adapter remain pending. See
[tsi-htif-lifecycle.md](tsi-htif-lifecycle.md).

Native and VCS production TSI sources pass **1,216 complete lifecycle captures**
and **2,432 fresh cross-backend private-field restores**. Both cache policies,
all eight direct-exit payloads, the five historical complete component images,
packet ordering and host-tick labels match the independent original-loop
oracle. All producers exit before destinations start. Every fresh final-class
TSI reads back all lifecycle bytes before a service; installed stop behavior
then matches with the serial queues unchanged. Additional sources pass **88
optional/raw/stopped restores**, including a requested zero that cannot be
distinguished from absent exit by `exit_code()` alone.

**282 invalid-image processes**, **18 lifecycle guards**, a mismatched
source/header build rejection and **20 first-divergence faults** pass. Signals
reject both before and after an optional exit is set. Corrupting a low raw
status bit preserves the visible shifted exit code; actual private-field
comparison detects that semantic host-component corruption at boundary zero
before service/acknowledgement. This is not DUT corruption evidence. Accepted
summary: `lifecycle-final/invocation-y0rvbsmo/summary.json`; independent audit:
`lifecycle-independent-audit.log`. The audit reconstructs the friend-only
header extension and unchanged-method provider compilation, and verifies all
unrelated installed archive members byte for byte. The provider remains an
opt-in experiment; complete signal/session/context ownership is pending.

Fresh ordinary Rocket RTL VCS passes complete **318,637-word / seven-clock /
zero-edge diagnostic pattern readback** (`ordinary-result.json`). This does
not capture an active CPU cut or replay a captured boundary trace. Existing
four-hart workload hashes, exact recipe settings and target-cycle reference
labels remain those recorded below; the component tests do not establish a
new CPU workload continuation.

All **eight preserved native suites** pass, including **267 Python tests**,
fixture metasim/replay, banked capture, FCFS and bridge checks. The independent
audit binds **5,260 artifacts / 794 source inputs** in
`native-regressions/invocation-fixn0qrr/summary.json`. All **30 retained audits**
pass again (`retained-rechecks/invocation-lftt9_9r/summary.json`). The initial historical control audit
rejected the changed builder input; supplying its original immutable
`m11-iteration129/native-input-archives.json` resolves that audit without
changing retained source hashes or control evidence. Both plans and all three
environment helpers match their initial hashes.

The complete current-source default-provider exit suite and its independent
audit also pass: **1,216 cuts / 6,080 complete component images**, **2,432 fresh
projections**, **268 malformed images**, **eighteen lifecycle rejections**,
**twelve signal-delivery proofs** and **sixteen first divergences**
(`exit/invocation-0zsktmm6/summary.json`, `exit-independent-audit.log`).
Full recovery catalogs: `selected-results.json`, `verification-commands.json`,
`raw-native-commands.json`, `summary.json` and `artifact-manifest.json`.

Repeat from the Chipyard root (each execution allocates fresh artifacts):

```bash
source env.sh
source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_htif_lifecycle_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration131-controller-rechecks/lifecycle
python -m tools.checkpoint_formats.tests.verify_tsi_htif_lifecycle_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration131/lifecycle-final/invocation-y0rvbsmo/summary.json
python -m tools.checkpoint_formats.tests.verify_tsi_htif_exit_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration131-controller-rechecks/exit
python -m tools.checkpoint_formats.native_regressions --audit \
  automations/checkpoint_loop/runs/m11-iteration131/native-regressions/invocation-fixn0qrr/summary.json
```

The launcher pins Y-2026.03-SP1 / `-full64` / GCC/G++ 13, then invokes native
compiler and VCS children directly with that inherited environment. Exact
native argv, source snapshots, installed/provider hashes, images, complete
readbacks, faults and logs are sealed by the invocation's summary. The
interrupted initial lifecycle and changed-source native-regression pilots remain diagnostic
only. No local commit or staging; the controller's iteration-130 FireSim and
Chipyard checkpoints were published in that order and remote tips confirmed.
Next: production recipe/aggregate integration, remaining HTIF owners, complete
fresh Level-1 continuation and independent captured Level-2 replay.

## Iteration 130: repeatable native/VCS signal rejection validation

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration130/`.
Both Rocket checkpoint levels remain **in_progress**. This iteration repairs
the exit-component regression's signal delivery assumption; production state
owners and CPU admission are unchanged. See
[tsi-htif-direct-exit.md](tsi-htif-direct-exit.md).

The original native and VCS binaries each fail both signal cases when the
parent blocks SIGINT/SIGTERM. All four fresh fixed processes pass under that
same inherited mask (`masked-signals/invocation-o8s4roe1/summary.json`). Their
complete delivery records prove an initially blocked signal, a queued signal
with the installed FESVR latch clear, handler delivery with the latch set,
no remaining pending signal, restored mask, rejected production admission
and unchanged serial state. No context or target edge runs. The full exit
suite additionally covers explicitly unblocked and inherited starting masks.
It passes **1,216 production cuts / 6,080 complete source owner images**,
**2,432 fresh component projections**, **268 malformed/incompatible image
processes**, **eighteen unowned lifecycle rejections**, **twelve signal-delivery
proofs** and **sixteen component first-divergence cases**. All 320 requested-exit
cuts retain their queued response before stop. Accepted summary:
`exit/invocation-g8_32sg1/summary.json`; separate audit:
`exit-independent-audit.log`. The image, projection, rejection and corruption
test scope is retained. These remain host-component cuts and faults.

All **30 retained independent audits** pass (`retained-audits.json`), including
the historical exit suite, production reader, atomic twelve-owner preparation
and exact-recipe complete four-hart controls. The current native/VCS polling
rejection regression passes (`polling-cut.log`). Fresh ordinary Rocket RTL VCS
reads back all **318,637 diagnostic words / seven clocks before an edge**
(`ordinary-result.json`). This is pattern readback, not captured CPU replay.
All **eight preserved native suites** pass, including all **267 Python tests**,
fixture metasim/replay, banked capture, FCFS and bridge checks. Their independent
audit binds 5,249 retained artifacts and 791 source inputs
(`native-regressions/invocation-nlr8j59v/summary.json`,
`native-independent-audit.log`).

The exact recipe, four-hart workload hash, full 16 GiB memory requirement and
retained CPU execution evidence remain as recorded below. No new CPU control
run, full Level-1 continuation or captured Level-2 replay is claimed here.
The required early, warmed-cache, outstanding-memory and late coherent CPU
checkpoint cuts, complete state ownership, fresh continuation and semantic
first-divergence cases remain pending. No external dependency is missing.

Existing controller iteration-129 commits were published FireSim first, then
Chipyard; both GitHub main tips match (`github-publication.json`). The
controller owns staging, the next local checkpoint and its publication.
Both plans and environment helpers remain read-only inputs.

Repeat the focused checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_htif_exit_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration130-controller-rechecks/exit
python -m tools.checkpoint_formats.tests.verify_tsi_htif_exit_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration130/exit/invocation-g8_32sg1/summary.json
python automations/checkpoint_loop/runs/m11-iteration130/repeat-masked-signals.py
python automations/checkpoint_loop/runs/m11-iteration130/repeat-native-regressions.py
python -m tools.checkpoint_formats.native_regressions --audit \
  automations/checkpoint_loop/runs/m11-iteration130/native-regressions/invocation-nlr8j59v/summary.json
```

Each invocation creates fresh diagnostic paths. The native/VCS exit suite
archives inputs before compilation and checks them again after all processes;
its commands source the pinned helper last. The initial compile-only pilot
that attempted to subclass the final TSI class is excluded. The selected
test uses a separate installed reference for the shared signal latch.
`selected-results.json`, `verification-commands.json`, `raw-native-commands.json`,
`summary.json` and `artifact-manifest.json` retain full paths, exact executable
commands and source/artifact hashes. Both plans and environment helpers pass
their unchanged-byte checks (`protected-inputs-check.log`).

## Iteration 129: direct HTIF exit and no-signature stop component

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration129/`.
Both complete Rocket checkpoint levels remain **in_progress**.
The direct pass/fail path now records its exact installed 32-bit status and
stop completion in an explicit kind-31 component. The installed syscall handler
and no-signature stop still perform the actual services. Active exit/signal/stop
state rejects historical polling inspection rather than silently omitting the
new component. Installed session/descriptors/signals and the actual inherited
exit/stop fields and outer caller remain required separate owners. See
[tsi-htif-direct-exit.md](tsi-htif-direct-exit.md).

The final native ASan/UBSan and VCS exit suite passes **1,216 production cuts**,
**6,080 complete source owner images** and **2,432 fresh component projections**,
with both producers terminated before destinations start. All 320 requested-exit
cuts retain a queued response before stop. Eight original payloads exercise
positive, negative and truncating installed statuses under both cache policies.
Each fresh process reads back the explicit exit component before any installed
reference service, then projects its exit/stop behavior and continues to stopped.
This does not restore the source polling caller or CPU. All 268 malformed and
incompatible component image processes reject atomically; ten actual unowned
signal/exit/stop/signature cases reject without serial mutation. Sixteen valid
status-bit corruptions read back completely and report their first divergent
exit-code projection at boundary zero, before continuing stop. Native/VCS
service guards pass 28 checks. These are component faults, not DUT faults.
Accepted summary: `exit-final/invocation-iqc63m8o/summary.json`; independent
audit: `exit-independent-audit.log`.

The polling-cut regression now requires rejection after installed proxied
`sys_exit`, whose exit parent remains unowned. It preserves all eight historical
component readbacks using a separate, explicitly unadmitted inspection. Native
and VCS pass all four active-syscall and two unowned-exit rejections, ten
startup/termination rejections and 32 complete component readbacks, including
16 at the rejected exit cut (`polling-cut-final/invocation-omo0zrnb/summary.json`).
All 267 Python tests pass again after this expectation correction. Archived
earlier polling evidence retains its original source-bound expectations.

The actual installed syscall-reader regression also passes all 68 syscall
outputs, 3,424 complete source cuts and 4,048 fresh reader/FIFO readback pairs
(`reader-production/invocation-lpys96ka/summary.json`); its independent audit
passes (`reader-independent-audit.log`). Installed `htif.o`, `syscall.o` and
`memif.o` remain byte-identical in the build-local overlay. The exact Rocket
binary links the new exit accessor and runtime reader
(`installed-binding-audit.json`). `exit-fault-independent-audit.json` additionally
binds all sixteen status corruptions to a single actual captured status bit
at source cut 20 / host tick 6, with the first unacknowledged projection
boundary zero and no continued stop service.

Atomic twelve-owner polling preparation passes all **2,976 fresh preparations**
at 744 component cuts and **35,760 complete readbacks**, with zero context
execution. All 4,368 malformed, 244 membership and 44 configuration/cross-owner
rejections, 2,708 allocation failures and 14,880 context-execution guards pass
(`polling-prepare/invocation-0bd3_lzo/summary.json`). Its independent audit
passes (`polling-prepare-independent-audit.log`). This retains the complete
existing component transaction while excluding exit/session/context ownership.

The selected exact-recipe VCS rebuild and all three complete default/buffered/
sealed four-hart controls pass at **C=3,329,794**, with the full **16 GiB**
backing memory in each process. Every complete hart trace and workload/store
cycle label matches the uninterrupted reference. The independent host audit
checks twelve active samples and all 112 complete known component images;
the sealed input is `4100ff`, identical to the retained reference.
Accepted control summary: `rocket-controls-final/invocation-m4dnr1vl/summary.json`;
sealed result: `rocket-sealed-terminal/summary.json`; independent audits:
`rocket-independent-audit.log` and `rocket-host-audit.json`.
Workload SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These are uninterrupted CPU controls and component samples, not complete
CPU checkpoint cuts. No bitstream is built.

No complete HTIF or CPU continuation is claimed. All eight preserved native
suites pass (`native-regressions-final/invocation-mflxh2ih/summary.json`), including
267 Python tests, fixture metasim/ordinary replay, banked capture, FCFS and
bridge regressions. All 26 retained evidence audits pass (`retained-audits-final.json`).
Fresh ordinary Rocket RTL VCS passes all 318,637 diagnostic pattern words and
seven clocks before an edge (`ordinary-result.json`); captured CPU replay
remains pending. Native/VCS ownership omission controls detect missing exit
recording at cut 20 / host tick 6 and missing stop recording at cut 28 / host
tick 8 (`exit-mutations-final/summary.json`). The independent audit checks all
480 complete preceding component images and refuses the first affected cut
(`exit-omission-independent-audit.json`). These are host labels and component
faults, not target-cycle DUT semantic corruption.

Controller iteration-128 commits were published FireSim first, then Chipyard;
both remote tips match (`github-publication.json`). The upcoming local
checkpoint and its publication remain the controller's responsibility. Plans
and environment helpers remain unchanged. No external dependency is missing.
Required coherent CPU cuts, full fresh Level-1 continuation and independent
captured Level-2 zero-edge readback/replay remain pending.

Aggregate recovery catalogs are `summary.json`, `selected-results.json`,
`verification-commands.json`, `raw-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`. They retain exact
native/VCS argv, all source/build hashes and full artifact paths. Source-changing
pilots, the initial old polling expectation and diagnostic setup/path errors are
excluded. The early CPU pilot's wrapper reported pass because it hashed inputs
after compilation, while its TSI object preceded the source edit. The independent
`build-stability-audit.json` rejects that pilot: it lacks the new admission guard,
while the selected final executable contains it and its object postdates the
source. Proposed follow-up: archive and compare native inputs before and after
compilation. This is an evidence-tool correction, not a missing external tool.

Repeat the new direct-exit and admission checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_htif_exit_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration129-controller-rechecks/exit
python -m tools.checkpoint_formats.tests.verify_tsi_polling_cut_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration129-controller-rechecks/polling-cut
python -m tools.checkpoint_formats.tests.verify_tsi_polling_prepare_vcs --identity \
  --out automations/checkpoint_loop/runs/m11-iteration129-controller-rechecks/polling-prepare
python -m tools.checkpoint_formats.tests.verify_tsi_memif_read_fesvr_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration129-controller-rechecks/reader
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration129-controller-rechecks/rocket \
  --seed-build automations/checkpoint_loop/runs/m11-iteration129/rocket-controls-final/invocation-m4dnr1vl/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

The immutable summaries retain native compiler/VCS/runtime argv, source and
archive snapshots, all sampled owner bytes, projection readbacks and negatives.
Every VCS subprocess sources the environment helper last and uses
Y-2026.03-SP1, `-full64` and system GCC/G++ 13. These tests do not enable a
complete CPU checkpoint profile.

## Iteration 128: production runtime memif read integration

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration128/`.
Both complete Rocket checkpoint levels remain **in_progress**.
The default installed syscall session now retains the FireSim-derived virtual
memory interface. Runtime byte/typed reads use the explicit head/tail/body
reader; each transport chunk queues its cache flushes before its serial read.
Startup loadmem selects the separate installed caller/transport. The adapter
rejects malformed chunks, endpoint overflow, missing destinations and unsupported
lengths. Active readers reject twelve-owner polling inspection because their
syscall parent is unowned. See
[tsi-runtime-memif-read.md](tsi-runtime-memif-read.md).

Stable native ASan/UBSan and VCS continuation suites pass all four producer /
destination combinations at every component cut:

| Serial policy | Cuts | Fresh continuations | Continued host operations | Complete owner readbacks |
| --- | ---: | ---: | ---: | ---: |
| No cache flush | 423 | 1,692 | 357,012 | 717,408 |
| Flush address `0x1280001000` | 661 | 2,644 | 872,520 | 1,750,328 |

Accepted summaries: `read-default-final/invocation-6j7i6oni/summary.json` and
`read-policy/invocation-m9tpw5by/summary.json`. Each suite passes all 30
invalid-image/missing-owner processes, 78 injected allocation failures and
12 first-divergence corruptions. Each native/VCS internal check passes 594
checks, including final-address-space cache flushing and rejection before
queue mutation. The enabled policy additionally samples partially drained
flush packets. Independent audits are `read-default-independent-audit.log`
and `read-policy-independent-audit.log`. `read-independent-audit.json` additionally
checks all 48 complete corrupted pre-service owner images and independently
derives the first divergent boundary and exact unacknowledged trace prefix.
Retained response/output-byte faults first change byte 0 from 176 to 177 at
host operation 40 without flushing and 48 with flushing. FIFO faults first
change request word 0 at operation 24 (0 to 1) and 28 (1 to 0), respectively.
No divergent boundary is acknowledged. These labels are host operations,
not Rocket target cycles.

Actual installed `sys_write` sources exercise all eight address residues,
zero/partial/exact/multiple transport chunks and both cache policies in native
C++ and VCS. All 68 syscall outputs, every packet and host-operation label,
and all 3,424 complete source reader/FIFO cuts match the independent oracle.
Startup loadmem remains isolated from serial/cache requests. All **4,048
fresh native/VCS reader/FIFO readback pairs** pass at every one of the 2,024
active source cuts across all four producer/destination combinations. Both
producers exit before destinations start; no context or target service is
entered during preparation. Accepted summary:
`read-production/invocation-_0kcp4ci/summary.json`; independent audit:
`production-independent-audit.log`. This restores components; it does not
restore a syscall or CPU. `production-binding-audit.json` verifies unchanged
installed `syscall.o` and `memif.o` bytes and links the production virtual
adapter. `production-mutations/summary.json` detects ownership bypass at
cut 7 / host tick 2 and missing cache flush at packet 4 / host tick 2 in both
native and VCS controls, while actual output bytes still match.

All eight preserved native suites pass (`native-regressions/invocation-jozfoaj3/summary.json`),
including 267 Python tests, fixture metasim/clean-RTL replay, banked capture,
FCFS and bridge regressions. `native-independent-audit.log` independently
validates all eight zero exits. All 24 retained audits and the iteration-127
reader audit pass (`retained-audits.json`, `retained-reader-127-audit.log`).
Fresh ordinary Rocket RTL VCS repeats all 318,637 pattern words / seven clocks
before any edge (`ordinary-result.json`). Captured CPU replay remains pending.
The exact-recipe VCS rebuild and complete default/buffered/sealed four-hart
controls pass at **C=3,329,794**, with the full 16 GiB memory in every run.
Every full hart trace and workload/store print-cycle label matches the
uninterrupted reference. Build/control summary:
`rocket-controls/invocation-hzekq4xd/summary.json`, with independently audited
build identity in `rocket-independent-audit.log`. Sealed result:
`rocket-sealed-terminal/summary.json`. `rocket-host-audit.json` checks twelve
active host samples and all 112 complete known component images.

The sealed CPU control used an empty input file; the historical control used
`4100ff`. Its four terminal images are checked against the canonical image for
the actual empty input, and the other 108 images match the historical samples
exactly. No captured image is rewritten. All target workload traces and labels
still match. The existing nonempty terminal native/VCS integration regression passes
separately (`terminal-nonempty/invocation-kto0n13o/summary.json`, independently
checked in `terminal-nonempty-independent-audit.log`): 52 fresh paired
readbacks, 312 continued host events, two actual production TSI sources,
16,148 malformed metadata rejections, 44 atomic transaction allocation
failures and four first semantic divergences. This is an explicitly recorded runtime variant;
it does not establish a new nonempty-input CPU execution result.
Workload SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
No bitstream is built, and no coherent CPU checkpoint cut is claimed.

Repeat the new checks from the Chipyard root (all native VCS subprocesses
source `vcs-env.sh` last):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_memif_read_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration128-controller-rechecks/read
python -m tools.checkpoint_formats.tests.verify_tsi_memif_read_vcs \
  --flush 0x1280001000 \
  --out automations/checkpoint_loop/runs/m11-iteration128-controller-rechecks/policy
python -m tools.checkpoint_formats.tests.verify_tsi_memif_read_fesvr_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration128-controller-rechecks/production
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration128-controller-rechecks/rocket \
  --seed-build automations/checkpoint_loop/runs/m11-iteration128/rocket-controls/invocation-hzekq4xd/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

The stable summaries retain native compiler/VCS/runtime argv, exact source and
archive hashes, complete cut/readback images, host-operation schedules and
negative-case diagnostics. Aggregate recovery catalogs are `summary.json`,
`selected-results.json`, `raw-native-commands.json`, `verification-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`; the last enumerates
full paths and hashes for every retained artifact in this iteration. These are component cuts, not Rocket target-cycle
checkpoints or DUT corruption. The syscall request/buffer/return parent,
session/descriptors, signals, stop/exit and outer context remain unowned.
Required coherent CPU cuts, complete fresh Level-1 continuation and independent
captured Level-2 zero-edge readback/replay remain pending. BOOM/Saturn remain
pending. Standalone Shuttle, physical FPGA and ASIC power remain excluded.

Controller iteration-127 commits were published FireSim first, then Chipyard;
both GitHub tips match (`github-publication.json`). Remote publication succeeded
despite local tracking-ref updates failing on the read-only `.git` filesystem.
The controller owns iteration-128 staging/commits/publication. No dependency
is missing. The first changed-source reader invocation and the native wrapper's
post-check result-formatting error are diagnostic-only. The sealed wrapper's
missing runtime metadata was repaired from its observed native zero exit and
exact command; `audit-final.log` reran the full workload audit successfully.
Its initial historical-input comparison failure is retained separately from
the accepted configuration-aware host audit. Stable summaries and independent
audits determine accepted results.

## Iteration 127: explicit generic memif read caller

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration127/`.
Both complete Rocket levels remain **in_progress**. Added
`firesim_tsi_memif_read_t`: original address/length, owned output bytes,
head/tail/body phase and cursor, plus the complete pending serial-read child.
It preserves installed FESVR's head, tail, then aligned body ordering with
alignment 8 and maximum chunk 1,024. Its kind-30/revision-1 image rejects
incompatible layout, address wrap, unsupported length, malformed child state,
inconsistent cursors and nonzero unread output bytes. Reader/FIFO preparation
allocates and validates both candidates before nonthrowing publication.
See [tsi-memif-read.md](tsi-memif-read.md).

The independent byte oracle and actual installed `libfesvr.a` differential
control pass all 19 scenarios, all eight address residues and zero/partial/
multiple-chunk reads. All **1,692 fresh continuations** pass at every one of
423 host-operation cuts across all four native/VCS producer/destination pairs:
357,012 continued operations and **717,408 complete owner readbacks**. Both
producers finish before any destination starts. Every byte of both owners
matches before service and after every operation; VCS finishes at time zero.
Accepted summary:
`read-final/invocation-pkkpcbgv/summary.json`.

Native ASan/UBSan and VCS each pass 588 internal checks, including every one
of 39 two-owner preparation allocation failures, malformed images, hostile
callbacks, full 1 MiB reads, final-address-space reads and completed reads
with an extra unconsumed response. All 30 separate malformed/incompatible/
missing-owner processes preserve both destination images. Twelve semantic
fault cases change an actual retained child response byte, copied output byte
or pending request word. Changed result bytes first differ at operation 40,
byte 0, expected 176 versus 177; the changed request first differs at operation
24, word 0, expected 0 versus 1. Neither divergent boundary is acknowledged.
`read-independent-audit.json` additionally compares all 24 complete corrupted
pre-service owner images with their exact input bytes. Native and VCS detect
both isolated tail-read and body-chunk omission mutants
(`read-mutations-final/summary.json`). These are host component labels and
component memory faults, not Rocket target-cycle checkpoints or DUT corruption.

All eight preserved native suites pass, including 267 Python tests, fixture
metasim/clean-RTL replay, banked state capture, FCFS and bridge checks
(`native-regressions/invocation-tf3yrt83/summary.json`, independently re-audited
in `native-independent-audit.log`). All 24 retained component audits and
306,422 iteration-126 artifacts remain unchanged (`retained-audits.json`).
Fresh ordinary Rocket RTL VCS repeats the complete 318,637 diagnostic pattern
words and seven clocks before any edge (`ordinary-result.json`). This does
not establish captured CPU replay.

The exact recipe/settings table above is rebuilt in VCS with Y-2026.03-SP1,
`-full64`, GCC/G++ 13 and `VCS_FLAGS=-Mupdate`. All three complete default,
buffered and sealed-terminal four-hart controls pass at C=3,329,794. Every full
hart trace, workload retirement and phase/failure/tohost store cycle label
matches the uninterrupted reference. All twelve active host samples match
112 known component images. Exact build/source evidence and native commands:
`rocket-controls/invocation-yom27fih/summary.json`, its
`rocket-build-identity.json`, `rocket-sealed-terminal-final/summary.json`,
`rocket-host-audit-accepted.json` and `final-audits.json`. The new generic
reader remains separate from these production workload controls.
Workload SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Each control keeps the complete 16 GiB backing memory; no bitstream is built.

Production `firesim_tsi_t` has not yet dispatched the new generic read owner.
The twelve-owner sealed polling interface still rejects general syscalls and
exit/context entry. Production caller/parent integration and the remaining
session, descriptor, signal, stop/exit, simulator and semantic capture owners
are pending. Early, warmed-cache, outstanding-memory and late CPU checkpoint
cuts, complete fresh Level-1 CPU continuation and independent captured Level-2
readback/replay remain pending. BOOM/Saturn remain pending; physical FPGA,
standalone Shuttle and ASIC power remain outside this task.

Repeat from the Chipyard root (all VCS shells source `vcs-env.sh` last):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_memif_read_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration127-controller-rechecks/read
python -m tools.checkpoint_formats.tests.verify_tsi_memif_read_vcs \
  --audit /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration127/read-final/invocation-pkkpcbgv/summary.json
```

The accepted summary retains executable native VCS build/runtime commands,
all source/archive hashes, exact cut images, full pre-service/continued images,
transaction traces, invalid-image results and first-divergence diagnostics.
`summary.json`, `selected-results.json`, `raw-native-commands.json`,
`verification-commands.json`, `native-input-archives.json` and
`artifact-manifest.json` record the exact aggregate recovery evidence.
Existing controller iteration-126 commits are published FireSim first, then
Chipyard, with both remote tips confirmed (`github-publication.json`). Plans
and environments are preserved; no staging or local commits. No external
dependency is missing. Development pilots are diagnostic-only.

## Iteration 126: atomic twelve-owner identity dispatch preparation

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration126/`.
Both complete Rocket checkpoint levels remain **in_progress**. Sealed polling
now requires all twelve ordered owners, including idle `identity` and `write`
images. Active dispatch requires matching parent/caller commands, the exact
copied writer payload/address, a pending head/tail merge read and an idle
mailbox reader. Startup/loadmem/host constraints remain enforced. Candidates
validate before terminal publication; the final nonthrowing state publication
preserves destination-bound references. Prepared identities use the ordinary
explicit dispatch service for every address residue. See
[tsi-polling-dispatch-restore.md](tsi-polling-dispatch-restore.md).

The native ASan/UBSan and VCS suite passes **2,976
fresh continuations** at all 744 host-operation cuts across all four producer/
destination backend pairs, every identity selector and all eight address
residues. Producers finish before destinations prepare. All twelve images
match before service and after every continued operation: 1,105,584
operations and 13,302,720 complete owner readbacks.
The preparation suite passes all 2,976 fresh preparations,
4,368 malformed, 244 membership and
44 cross-owner/configuration rejections,
plus 2,708 injected allocation failures. Unowned commands
and external exit continue to reject before service; context entry remains
prohibited. Accepted summaries:
`polling-contained/invocation-r668nvfh/summary.json` and
`polling-final/invocation-7qeoxwxd/preparation/invocation-2zm0kdnr/summary.json`.

A separate active-dispatch suite passes all eight fresh head/tail invalid-image
processes, 9,312 malformed images,
392 owner-membership checks,
104 relationship checks and
5,440 injected allocation failures, preserving every pristine peer,
metadata and absent parent/device after rejection. Eight semantic fault cases
alter an actual retained merge byte or coherently change the parent/caller
command and child payload. Each first differs at host operation 111, request
word 1, expected 1,634,038,461 versus 1,634,038,460 or 189; the word remains
unconsumed. All twelve altered images are independently read back before
service. Accepted summary: `dispatch-final/invocation-hnqi0dlq/summary.json`. Both native/VCS mutation
controls detect early program-state publication and admission of a parseable
identity that has not reached a real yield
(`dispatch-restore-mutations-final/summary.json`). These are host component
operations and serial-word faults, not CPU target-cycle checkpoints or DUT
semantic corruption.

Actual ordinary installed-HTIF dispatch passes 128 identities with both cache-
flush settings, all selectors and all residues. All 2,892 sampled cuts match
the independent byte oracle; all 1,344 active cuts now admit sealed twelve-owner
inspection. The separate four-owner fresh readbacks retain 2,688 processes /
10,752 images (`actual-identity/invocation-_fb3nih6/summary.json`). The parent suite retains 78 fresh
continuations, 1,560 readbacks, 42,010 internal invalid checks, eight invalid
processes and four first-divergence cases (`poll/invocation-czmcqjws/summary.json`). Retained caller/
write/FIFO and write/FIFO evidence is independently re-audited; it is not
substituted for the new aggregate checks.

All eight preserved native suites (267 Python tests, FCFS and all native
checks), all seventeen host suites and all 24 independent component/native
audits pass (`native-regressions-contained/invocation-t2gizqw2/summary.json`, `host/host-regression-results.json`,
`independent-component-audits.json`). Fresh ordinary Rocket RTL VCS reads and
deposits all 318,637 diagnostic pattern words and seven clocks before any edge
(`ordinary-result.json`). No captured CPU replay is inferred.

The exact Rocket recipe above is rebuilt in native VCS with Y-2026.03-SP1,
`-full64`, GCC/G++ 13 and `VCS_FLAGS=-Mupdate`, without a bitstream. Default,
buffered and sealed controls all pass the self-checking four-hart workload at
C=3,329,794 with full 16 GiB backing memory each. Every full hart trace and
workload/store target-cycle label matches the uninterrupted reference. Twelve
active host samples match 112 known component images, including the sealed
mode's two added idle owners. Build and exact-source evidence:
`rocket-controls/invocation-wap5tvdb/summary.json`, `rocket-sealed-terminal-final/summary.json`,
`native-terminal-build-audit-final.json` and `workload-control-audits.json`.
Independent recompilation matches the actual TSI, bridge, loader and context
objects. Workload SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Executable build/simulation argv and relative working directories are indexed
in `raw-native-commands.json` and `verification-commands-native.json`.
`selected-results.json`, `native-input-archives.json`, `summary.json` and
`artifact-manifest.json` bind sources and results. All VCS shells source both
repository environments followed by `vcs-env.sh` last. The first expanded
preparation attempt hit the enclosing suite's old 600-second timeout; each
individual check keeps that bound, while the aggregate now has a separate
four-hour deadline. The interrupted invocation and development pilots remain
separate in `diagnostic-pilots.json`; no failed or interrupted result supplies
passing evidence. Continuation simulations now run inside their invocation
directory so VCS command-key diagnostics remain under `runs/`. Incidental keys
from retained regression helpers are preserved there after those helpers finish.
The full continuation and eight-suite regressions were repeated after this
working-directory correction.

The prior audit preserves all 145,341 iteration-125 artifacts and 1,043 native
input bindings, with controller provenance (`prior-preservation.log`). Existing
controller iteration-125 checkpoints were published FireSim first, then Chipyard,
and both remote tips were independently confirmed (`github-publication.json`).
Local remote-tracking updates were denied after successful remote pushes.
Plans/environments retain their original bytes; no staging or local commits.
The controller owns the upcoming iteration-126 checkpoint and its publication.
No external dependency is missing.

Complete memif/syscall, descriptor, signal, stop/exit and simulator ownership (see [htif-remaining-owners.md](htif-remaining-owners.md)),
coherent early/warmed/outstanding-memory/late CPU cuts, complete fresh-process
Level-1 CPU continuation and independent Level-2 CPU capture/readback/finite
trace replay remain pending. BOOM/Saturn remain pending. Physical FPGA
validation, standalone Shuttle and ASIC power remain outside this work.

Repeat from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_continue_vcs --identity \
  --out automations/checkpoint_loop/runs/m11-iteration126-controller-rechecks/polling
python -m tools.checkpoint_formats.tests.verify_tsi_polling_dispatch_vcs \
  --preparation-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration126/polling-final/invocation-7qeoxwxd/preparation/invocation-2zm0kdnr/summary.json \
  --out automations/checkpoint_loop/runs/m11-iteration126-controller-rechecks/dispatch
```

Both checkers also accept `--audit /absolute/path/to/summary.json`. The dispatch
checker requires a fully audited preparation summary; the continuation checker
optionally reuses one with `--preparation-summary`. Neither creates a CPU image.

## Iteration 125: parent identity dispatch returns blocked

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration125/`.
Both CPU levels remain **in_progress**. Ordinary unaligned identity dispatch now
returns blocked through the identity and HTIF parent guards before switching
to the target. The parent retains its command, dispatch phase and response
queue; retries resume the existing child and validate its command. See
[tsi-polling-dispatch.md](tsi-polling-dispatch.md). This closes the suspended
parent callback gap. Atomic twelve-owner polling preparation and its cross-owner
predicates remain pending; existing prepared admission remains aligned-only.
General memif/syscall, descriptors, signals, stop/exit and complete simulator
ownership remain pending.

The new parent suite passes 78 fresh native/VCS continuations, 1,560 complete
pre-service/continued readbacks, 42,010 internal invalid-image checks, eight
separate invalid-image processes and four first-divergence corruptions.
Repeated blocked dispatch and a response queued before the child's final return
preserve the complete parent image. A diagnostic mutation discarding the
child yield is detected in both native and VCS at the next service boundary.

Actual ordinary HTIF execution passes all 128 identity commands across both
backends, four selectors, eight address residues and both cache-flush settings.
The independent oracle matches 2,892 captured cuts, including 1,344 complete
parent images during active unaligned dispatch. All 2,688 fresh preparations
read back 10,752 complete parent/caller/write/FIFO images before service
(`actual-identity/invocation-vuq1hjdo/summary.json`). The parent is restored
separately from the atomic three-owner child transaction; this is component
readback, not an aggregate restore or CPU continuation. All active identity
cuts still reject polling admission. Both backends detect the diagnostic
reintroduction of the suspended callback at its first active cut, operation 54
(`suspended-dispatch-mutation-final/summary.json`). The preserved aligned suite
passes 400 fresh continuations and 202,000 complete owner readbacks, including
all atomic ten-owner negative cases
(`aligned-identity/invocation-jawcnuph/summary.json`).

The caller/write/FIFO suite also passes all 4,020 fresh continuations at
1,005 cuts, 2,018,040 host operations and 6,066,180 complete owner readbacks.
All 30 invalid-image processes and twelve first-divergence cases pass, together
with both backends' atomic malformed/membership/configuration, allocation and
hostile-service checks (`identity/invocation-rqf51t_j/summary.json`).

All eight preserved native suites pass, including 267 Python tests and FCFS
(`native-regressions/invocation-56a4mi7p/summary.json`). All seventeen host
suites pass (the sixteen entries in `host/host-regression-results.json` plus
the extended parent suite), as do all 23 independent component/native audits
(`independent-component-audits.json`). The unchanged writer/FIFO evidence is
independently re-audited from iteration 124. Ordinary RTL VCS again reads all
318,637 pattern words and seven clocks before any edge (`ordinary-result.json`);
captured CPU replay remains pending.

The rebuilt exact-recipe default, buffered and sealed four-hart controls all
pass at C=3,329,794. Complete hart traces and every workload/store target-cycle
label match the uninterrupted reference. Independent inspections match all
104 known component images at twelve active samples; these remain host-credit
samples, not coherent CPU checkpoint cuts. Each control retains full 16 GiB
backing memory. The workload SHA-256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Build settings and bindings are in
`rocket-controls/invocation-r1cy8bwm/rocket-build-identity.json`, its
`summary.json`, `rocket-sealed-terminal-final/summary.json` and
`workload-control-audits.json`. Rebuilt TSI/bridge/loader/context objects match
independent recompilation (`native-terminal-build-audit-final.json`).

Exact executable native VCS build/simulation argv with relative working
directories are indexed in `raw-native-commands.json` and
`verification-commands-native.json`. Source bytes are preserved in
`native-input-archives.json`; `selected-results.json`, `summary.json` and
`artifact-manifest.json` bind this iteration's results and artifacts. All
simulations/builds source both repository environments and then `vcs-env.sh`
last. VCS is Y-2026.03-SP1, full64, with GCC/G++ 13; reused Make builds use
`VCS_FLAGS=-Mupdate`. Earlier diagnostic import/include failures are retained
separately in `diagnostic-pilots.json` and supply no passing evidence.

The post-test prior audit preserves all 184,830 iteration-124 artifacts and
1,044 native input bindings (`prior-preservation-post-tests.log`). Existing
controller iteration-124 checkpoints were published FireSim first, then
Chipyard; independent remote queries confirm both tips
(`github-publication.json`). Both pushes succeeded remotely; the sandbox
prevented local remote-tracking ref updates. No staging or local commits.
Plans and environments retain their original bytes. The controller owns the
upcoming iteration-125 checkpoint and its publication. No external dependency
is missing.

Required complete fresh Level-1 CPU continuation and independently captured
Level-2 CPU readback/replay remain pending. Neither CPU level is verified.
Component labels above are host operations, not CPU semantic cuts.

Repeat the new checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_htif_poll_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration125-controller-rechecks/poll
python -m tools.checkpoint_formats.tests.verify_tsi_memif_identity_fesvr_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration125-controller-rechecks/actual-identity
```

## Iteration 124: explicit BCD identity dispatch caller

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration124/`.
Both CPU levels remain **in_progress**. Ordinary identity dispatch now owns its
raw command and write/response/return cursors, in addition to the existing
copied-payload write child and serial FIFOs. The three components prepare
atomically with complete pre-service readback. See
[tsi-bcd-identity.md](tsi-bcd-identity.md) for the state boundary and native VCS
reproduction commands. Integrating active dispatch with the parent polling
caller and its ten-owner preparation contract remains pending; prepared
identity admission remains aligned-only. General memif/syscall, descriptors,
signals, stop/exit and complete simulator ownership remain pending.

Native ASan/UBSan and Y-2026.03-SP1 VCS atomic checks each pass 486 malformed
images, twelve membership failures, seven phase/relationship failures, all 48
allocation failures and 36 hostile-service guards. Both backends detect
diagnostic header mutations that skip the identity response or omit the
caller/child relationship check (`identity-mutations/summary.json`).
`identity/invocation-x4mo5328/summary.json` passes all 32 selector/residue
scenarios, 1,005 cuts and 4,020 fresh continuations in all four backend
pairings. Its independent byte oracle matches 2,018,040 host operations and
6,066,180 complete owner readbacks, including every pre-service image.
All 30 invalid-image processes reject before publication; a separate audit
matches all 90 unchanged destination images (`identity-invalid-readback-audit.json`).
All twelve accepted semantic corruptions stop before consuming the first
divergent request word. Preserved head corruption first differs at operation
63/word 2 (1,634,038,421 versus 1,634,038,420); preserved tail corruption at
74/word 2 (975,171,584 versus 975,171,840); queued-command corruption at
62/word 0 (1 versus 0). These labels describe host operations, not CPU cycles.

Actual ordinary HTIF execution passes all 128 identity commands across native
and VCS with both cache-flush settings. All 2,892 sampled caller/write/FIFO
cuts match independently constructed images; all 1,344 active samples reject
ordinary polling admission. After source completion, 2,688 fresh preparations
read back all 8,064 complete owner images before service
(`actual-identity/invocation-h2xz5m4s/summary.json`). These are component images
from host-operation cuts, not CPU semantic cuts or parent HTIF continuation.
The retained write/FIFO suite passes 1,616 fresh continuations, 28 invalid
processes and twelve semantic corruptions
(`memif-write/invocation-by85e1mt/summary.json`). Prepared aligned identity
retains all 400 fresh continuations and 202,000 complete owner readbacks
(`aligned-identity/invocation-obpnflka/summary.json`).

The rebuilt exact-recipe default, buffered and sealed four-hart controls all
pass at target count 3,329,794. Complete traces and all workload/store labels
match the uninterrupted reference. Independent audits pass all 104 known
component images at twelve active samples. Each control uses full 16 GiB
backing memory. The workload SHA-256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Build/runtime settings and commands are bound in
`rocket-controls/invocation-f02jgf7u/rocket-build-identity.json`,
`rocket-controls/invocation-f02jgf7u/summary.json`,
`rocket-sealed-terminal-final/summary.json` and `workload-control-audits.json`.
These are uninterrupted controls, not CPU checkpoint continuations.

All eight preserved native suites pass, including 267 Python tests and FCFS
(`native-regressions/invocation-zexdye1q/summary.json`). Ordinary RTL VCS again
reads every one of the 318,637 pattern words and seven clocks before any edge
(`ordinary-result.json`); captured CPU replay remains pending. The rebuilt
TSI/bridge/loader/context objects equal independent recompilation
(`native-terminal-build-audit-final.json`), and the native binary contains the
new identity owner. Recipe settings and four-hart workload bytes/hash remain
as recorded above. Both plans and environments retain their original bytes.
All 17 retained host suites and 23 independent component/native audits pass
(`host/host-regression-results.json`, `independent-component-audits.json`).
Accepted results and exact executable argv with relative working directories
are indexed in `selected-results.json`, `raw-native-commands.json` and
`verification-commands-native.json`; source snapshots are indexed in
`native-input-archives.json`. `artifact-manifest.json` catalogs the complete
iteration. All invocations are fresh. Earlier include/corruption pilots and
the source-stability rejection remain separately recorded in
`diagnostic-pilots.json`; they supply no passing evidence. The final prior
audit preserves all 113,211 iteration-123 artifacts and 1,041 input bindings
(`prior-preservation-final.log`). No external dependency is missing.
The sealed audit passes all 184,830 iteration artifacts, 1,044 native input
bindings and 13,646 command records, with controller provenance verified. Its
result is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration124-manifest-audit.json`.
Existing controller iteration-123 commits were published FireSim first and
then Chipyard; independent remote queries confirm both tips
(`github-publication.json`). No staging or local commits. The controller must
publish the upcoming iteration-124 checkpoint after creating it.

Repeat the new component checks from the Chipyard root (each checker creates a
fresh invocation and records its actual `-full64` native VCS argv):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_bcd_identity_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration124-controller-rechecks/identity
python -m tools.checkpoint_formats.tests.verify_tsi_memif_identity_fesvr_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration124-controller-rechecks/actual-identity
```

Read-only audit of the sealed iteration:

```sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration124/audit-final-manifest.py
```

## Iteration 123: explicit ordinary BCD memif write child

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration123/`.
Both CPU levels remain **in_progress**. The new write owner retains copied
payload bytes, head/tail read/merge progress, every partial serial-read word and
the aligned-body cursor. Ordinary BCD identity uses this explicit child. The
destination-owned prepared caller retains aligned-only admission: its unaligned
device-dispatch caller and atomic preparation contract remain pending. See
[tsi-memif-write.md](tsi-memif-write.md) for the exact state boundary, unsupported
paths and next integration step. Other syscall/memif callers, file descriptors,
signals, stop/exit and complete simulator ownership remain unverified.

The two new native ASan/UBSan and Y-2026.03-SP1 VCS DPI suites check installed
memif transaction order and complete fresh write/FIFO component continuation,
and separately capture actual ordinary HTIF/BCD identity execution with cache
flushing disabled and enabled. All four identity selectors and all eight
address residues are covered. Operations and suspended host yields are not
semantic CPU target-cycle cuts. A child-only restore never resumes HTIF or a CPU.

`memif-write/invocation-nvr50hp8/summary.json` passes 19 scenarios, 404 cuts and
1,616 fresh continuations across all four backend pairings. The byte oracle
matches all 325,624 operations and 654,480 complete owner readbacks. Installed
FESVR independently matches every read/write event and payload/sentinel byte.
All 28 malformed/incompatible/incomplete-image processes reject before either
peer changes; each backend also passes 554 atomic/hostile/maximum-size checks.
All twelve semantic corruption cases stop at the first divergent request word,
which remains unconsumed. The head-response and payload corruptions first differ
at operation 19/word 2; queued-command corruption first differs at operation
18/word 0. These are component operations. Diagnostic native/VCS mutants that
skip the tail merge or drop the child-address ownership check are detected
(`memif-mutations-v2/summary.json`).

`actual-identity/invocation-wvw9dhbn/summary.json` passes 128 ordinary HTIF/BCD
identity commands across native/VCS and both cache-flush settings. All 2,892
sampled child/FIFO cuts match independently constructed complete images. All
1,344 active samples reject ordinary polling admission; after the source
processes finish, 2,688 fresh child/FIFO restores read back 5,376 complete owner
images before any service. This uses the host-loader test ELF and performs no
CPU execution. Prepared unaligned dispatch remains unsupported.

The exact recipe settings above and four-hart workload SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`
are unchanged. The current exact-recipe build is
`rocket-controls/invocation-8b48hflo/rocket-build-identity.json`.
`memif-provider-audit.json` binds the new owner and actual executable symbols;
`native-terminal-build-audit-final.json` independently recompiles and compares
its actual TSI/bridge/loader/context objects. No FPGA bitstream is built.
`memif-path-ownership.json` independently confirms byte-identical installed
`memif.o` members in the original archive, host-test overlay and exact Rocket
overlay; general memif callers have not acquired checkpoint ownership.

All three complete default/buffered/sealed four-hart controls pass at target
count 3,329,794. Full traces and every workload/store print-cycle label match
the uninterrupted reference; independent audits check all 104 known host-owner
images at 12 active samples. Each control retains full 16 GiB backing memory.
Results are `rocket-controls/invocation-8b48hflo/summary.json`,
`rocket-sealed-terminal-final/summary.json`, `workload-control-audits.json`,
`rocket-host-audit-accepted.json` and `sealed-workload-independent-audit.json`.
Host credits and one-ahead token-enqueue labels remain distinct from semantic
CPU checkpoint cuts. Ordinary RTL VCS also repeats all 318,637 pattern-word and
seven-clock readbacks before an edge (`ordinary-result.json`); captured CPU
state and trace replay remain pending.

All eight preserved native suites pass, including 267 Python tests and FCFS
(`native-regressions/invocation-31esocsb/summary.json`). All 17 retained host
suites and 22 independent component/native audits pass
(`host/host-regression-results.json`, `independent-component-audits.json`).
The aligned prepared-caller regression retains 400 fresh continuations, 202,000
complete owner readbacks, 132 unowned-command rejections and eight semantic
corruptions. Atomic ten-owner preparation retains 3,200 malformed-image,
204 membership and 44 cross-owner/configuration rejections, 2,588 allocation
failures and 2,000 execution guards. Accepted results and complete native argv
are indexed in `selected-results.json`, `raw-native-commands.json` and
`verification-commands-native.json`; source snapshots are indexed in
`native-input-archives.json`, and every iteration artifact is cataloged in
`artifact-manifest.json`. Earlier build/link/marker pilots remain separate in
`diagnostic-pilots.json`. All invocations are fresh. The preservation audit
passes all 88,831 prior iteration artifacts and 1,030 native input bindings.
Both plans and environments retain their original bytes; no staging or local
commit occurred. No external dependency is missing.
The final sealed audit passes 113,211 iteration artifacts and 1,041 native input
bindings, with controller provenance verified; 9,560 native command records
retain relative working directories. The result is the sibling
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration123-manifest-audit.json`.
The post-test prior preservation audit again passes all 88,831 iteration-122
artifacts and 1,030 input bindings
(`runs/m11-iteration123-prior-preservation-final.json`).

Audit the sealed iteration from the Chipyard root:

```sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration123/audit-final-manifest.py
```

Repeat from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_memif_write_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration123-controller-rechecks/memif-write
python -m tools.checkpoint_formats.tests.verify_tsi_memif_identity_fesvr_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration123-controller-rechecks/actual-identity
```

Existing controller iteration-122 commits were published FireSim first and
then Chipyard; independent remote queries match both HEADs
(`github-publication.json`). The controller owns the upcoming iteration-123
checkpoint. Both plans remain read-only.

## Iteration 122: aligned BCD identity transport

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration122/`.
Both CPU levels remain **in_progress**. See
[tsi-polling-preparation.md](tsi-polling-preparation.md) for the admitted boundary
and exact owner contract. The prepared identity writer copies all 64 bytes into
a complete destination-owned serial packet without invoking memif or entering a
coroutine. Partially consumed packets remain owned by the serial FIFO; responses
bind the destination poll. There is no additional serialized state or schema
change. Ordinary execution keeps installed memif semantics, independently tested
against the prepared path. Unaligned identity, syscall, exit/signals and other
devices still fail closed; full `tick()` remains disabled.

`aligned-identity/invocation-iwxxvjyk/summary.json` passes native ASan/UBSan and
Y-2026.03-SP1 VCS DPI: 400 fresh component continuations at 100 cuts in all four
backend pairings, 19,800 host operations and 202,000 complete owner readbacks.
The independent byte oracle covers all four identity selectors, high address
words, eight-byte alignment without sixteen-byte alignment, partial command
reads, partial identity packet headers/data, queued acknowledgments, binary
terminal I/O and EOF. Producers exit before destinations prepare. All ten owners
are read back before service and after every operation. Startup metadata remains
unchanged and no host context is entered. These are host-operation labels,
not CPU semantic cuts.

All 132 unowned-command rejections (all seven unaligned residues for each
identity selector, syscall and unknown-device/command cases) preserve the
terminal and enqueue zero clear packets. Four external-exit guards pass.
Four terminal-cursor and four identity-packet corruptions stop at their first
divergent request word without consuming it. Identity corruption diverges at
operation 61, word 2, expected 1,684,104,562 versus actual 1,684,104,563.
`command-preflight-mutation/summary.json` detects removal of the pre-clear hook
in native and VCS. The prerequisite atomic preparation suite passes 400 fresh
preparations, 4,040 complete readbacks, 3,200 malformed-image, 204 membership
and 44 cross-owner/configuration rejections, 2,588 allocation failures and
2,000 execution guards. `identity-path-ownership.json` records the exact source
and unchanged installed memif-object hashes and the remaining unsupported owners.

All eight preserved native suites pass, including 267 Python tests and FCFS:
`native-regressions/invocation-aylyik6v/summary.json`. Ordinary RTL VCS repeats
all 318,637 pattern-word/seven-clock readbacks before an edge
(`ordinary-rocket-probe/run.log`); this does not establish captured CPU replay.
The exact recipe settings above and workload SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`
are unchanged. Final-source build identity is
`rocket-controls/invocation-r3xamu9p/rocket-build-identity.json`. Its actual
loader/context/TSI/bridge objects match independent recompilation
(`native-terminal-build-audit-final.json`), and the executable binds the owner
headers and caller API (`native-polling-provider-audit.json`). All three complete
final-source default/buffered/sealed four-hart controls pass at C=3,329,794.
Their full traces and every workload/store print-cycle label match the reference,
with full 16 GiB backing memory in each run. Independent audits pass all 104
known owner images at 12 active samples; host credits and the one-ahead token
enqueue labels remain distinct from semantic CPU cuts. Exact results are
`rocket-controls/invocation-r3xamu9p/summary.json`,
`rocket-sealed-terminal-final/summary.json`, `rocket-host-audit-accepted.json`,
`sealed-workload-independent-audit.json` and `workload-control-audits.json`.
All 17 retained host suites and all 20 independent component/native audits
pass (`host/host-regression-results.json`, `independent-component-audits.json`).
Exact accepted paths, input snapshots and native argv are retained in
`selected-results.json`, `native-input-archives.json`, `raw-native-commands.json`
and `verification-commands-native.json`. `artifact-manifest.json` catalogs every
iteration artifact. The final sealed audit passes all 88,831 artifacts and
1,030 native input bindings with controller provenance verified; 5,192 native
command records retain relative working directories. Re-run the read-only audit:

```sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration122/audit-final-manifest.py
```

No previous invocation was overwritten. The final prior preservation audit passes 85,949 iteration-121 artifacts, 22,465 external
artifacts and 1,037 native input bindings (`prior-manifest-audit-final.json`).

Existing controller iteration-121 checkpoints were published FireSim first,
then Chipyard; queried remote tips match. Both successful pushes reported a
read-only local remote-tracking ref update, recorded with the confirmed remote
commit IDs in `github-publication.json`. The controller still owns the upcoming
iteration-122 commit and its publication. There was no staging or local commit;
protected plan and environment hashes remain unchanged.

Repeat the component continuation and audit from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_continue_vcs --identity \
  --out automations/checkpoint_loop/runs/m11-iteration122-controller-rechecks/aligned-identity
```

```sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_continue_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration122/aligned-identity/invocation-iwxxvjyk/summary.json
```

Exact-recipe complete default/buffered controls, using a fresh copied build:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration122-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration122-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration122-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration122/rocket-controls/invocation-r3xamu9p/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

General memif read/merge, syscall/file-descriptor, signals, stop/exit and complete
aggregate simulator ownership remain required before full CPU admission.
Complete Level-1 fresh metasim continuation, captured independent Level-2
zero-edge readback/replay, required semantic CPU cuts and whole-CPU rejection/
first-divergence cases remain pending. BOOM/Saturn remain pending; physical FPGA,
standalone Shuttle and ASIC power remain outside this task. Both plans are
read-only and the controller owns local commits. No external dependency is
missing.

## Iteration 121: prepared polling caller without startup or context replay

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration121/`.
Both CPU levels remain **in_progress**. The executable component caller shares
polling services with normal execution, restores child progress before any
service and returns at the next serial-read/idle yield. Only sealed BCD read/write
commands are supported. Syscall/exit, device identity through memif, unknown
BCD commands and other devices reject before a tohost-clear request is queued.
A failed service poisons subsequent component execution/readback. Full HTIF
`tick()` admission remains disabled. See
[tsi-polling-preparation.md](tsi-polling-preparation.md) for exact owner scope.

`polling-continue-final/invocation-er_7mscr/summary.json` passes native
ASan/UBSan and Y-2026.03-SP1 VCS DPI: 224 fresh component continuations at 56
operation cuts in all four backend pairings, 6,160 host operations and 63,840
complete owner readbacks including initial preparation. The source processes
finish before destination preparation. All ten owners are independently
compared after every operation, including partial serial packets, queued
responses, partial reads, idle yields, binary terminal I/O and pending EOF
reads. Startup metadata remains unchanged and no context is initialized.
These labels are host operations, not semantic CPU target cycles.

The same suite passes 24 unowned-command rejections, four external-exit guards
and four deliberate semantic-cursor corruptions. The first corrupted mailbox
request differs at operation 21, request word 5, expected 321 versus actual 256;
that word remains unconsumed. `command-preflight-mutation/summary.json` confirms
that native and VCS tests detect removal of the validation hook before mailbox
clear. Prerequisite ten-owner preparation retains all 224 preparations, 2,280
readbacks, 3,200 malformed rejections, 204 membership rejections, 44 cross-owner/
configuration rejections, 2,588 allocation failures and 1,120 execution guards.

The exact Rocket recipe settings above and workload SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`
are unchanged. All three complete final-source default/buffered/sealed four-hart
controls pass at C=3,329,794. All full hart traces and workload/store print-cycle
labels match the uninterrupted reference. Default/buffered evidence is
`rocket-controls-final/invocation-_zmvyqmc/summary.json`; sealed evidence is
`rocket-sealed-terminal-final/summary.json`. Independent audits pass all 104 known
host-component images at 12 active samples, preserving master-credit and one-ahead
enqueue labels without certifying semantic CPU cuts. Each control uses full 16 GiB backing memory. The actual loader/context/TSI/bridge objects equal
independent recompilation (`native-terminal-build-audit-final.json`), and the
executable contains the new API with all audited owner headers
(`native-polling-provider-audit.json`). Earlier warning/source-race builds are
separate diagnostic pilots (`diagnostic-pilots.json`). No CPU continuation,
captured Level-2 replay, required semantic CPU cuts or FPGA result is inferred
from these component tests or uninterrupted controls.

All eight preserved native suites pass, including 267 Python tests and FCFS:
`native-regressions/invocation-27qvwxe6/summary.json`. All 17 retained host suites
and all 19 independent component/native audits pass; the new caller audit passes
separately (`polling-continue-independent-audit.json`). Exact accepted paths,
source/input snapshots and all native argv are in `selected-results.json`,
`native-input-archives.json` and `raw-native-commands.json`. Four inherited host
commands allocated fresh invocations under earlier runs roots; their original
bytes/paths remain in place and are indexed in `external-evidence.json`.
The final preservation audit passes 57,348 iteration-120 cataloged artifacts and
1,015 prior native input bindings. The final sealed-manifest audit passes 85,949
iteration artifacts, 22,465 external artifacts and 1,037 native input bindings,
with controller provenance verified. `raw-native-commands.json` retains 4,727
exact native command records. Re-run that audit without modifying any artifact:

```sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration121/audit-final-manifest.py
```

Existing controller commits were published
FireSim first, then Chipyard, with queried remote tips matching. No local commit,
staging, protected plan or environment change was performed.

The ordinary RTL pattern
diagnostic again reads all 318,637 words and seven clocks before its first edge
(`ordinary-rocket-probe/run.log`); this remains independent of captured replay.

Executable component checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_continue_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration121-controller-rechecks/polling-continue
```

```sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_continue_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration121/polling-continue-final/invocation-er_7mscr/summary.json
python -m tools.checkpoint_formats.native_regressions --audit \
  automations/checkpoint_loop/runs/m11-iteration121/native-regressions/invocation-27qvwxe6/summary.json
```

Repeat complete exact-recipe default/buffered four-hart controls:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration121-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration121-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration121-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration121/rocket-controls-final/invocation-_zmvyqmc/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

Complete syscall/file-descriptor, signal, stop/exit, memif and simulator ownership
is still required before full HTIF/CPU admission. Atomic component membership
and matching host operation traces do not prove a common semantic CPU cut.
Fresh complete Level-1 continuation and independent captured Level-2 zero-edge
readback/replay, including whole-CPU invalid-image and first-divergence cases,
remain pending. BOOM and Shuttle + Saturn remain pending; physical FPGA and
ASIC power remain deferred. Both plans remain read-only; the controller owns
local commits.

## Iteration 120: atomic fresh preparation of ten polling owners

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration120/`.
Both CPU levels remain **in_progress**. `prepare_polling_components` prepares
all ten known owners after the separate metadata-only preparation. The source
inspection and destination candidate validation share one cross-owner predicate.
Every parse, allocation and relationship check precedes publication. Only
nonthrowing swaps follow the final poll/terminal/BCD transaction. The destination
can read back all components and metadata, while context entry remains disabled.
See [tsi-polling-preparation.md](tsi-polling-preparation.md) for the exact owner
contract and remaining ownership gaps.

`polling-prepare/invocation-p95inli2/summary.json` passes native ASan/UBSan and
Y-2026.03-SP1 VCS DPI. Two installed-FESVR source processes complete execution
before fresh preparation in all four backend pairings at 56 operation cuts.
An independent byte oracle checks every field in all ten owners, including
partial request packets, queued incoming words, partial tohost/fromhost reads,
three idle yields, binary input, output and two pending EOF commands. The
results are 224 fresh preparations and 2,280 complete prepared readbacks;
1,120 execution/duplicate-preparation guards prevent service or context entry.
These are host-component operation boundaries, not semantic CPU target cycles.

Four fresh rejection processes pass 3,200 malformed/configuration-image cases,
204 missing/extra/unknown/duplicate/reordered membership cases, 44 cross-owner
or incompatible mailbox/limit cases and 2,588 injected allocation failures.
Every failed preparation preserves all eight pristine destination peers and
metadata, and leaves the poll/BCD owners absent. The valid final image changes
program/init/host/read/BCD/terminal state together. The mutation in
`polling-prepare-mutation/summary.json` deliberately publishes the terminal
before parsing the protocol candidates; the same test detects partial state
publication and rejects it. Production sources are not mutated by that check.
The additional `prepared-initialization-guard/summary.json` checks a valid
reset-wait image in native sanitizer and VCS: both destinations preserve all
ten images, and removing the prepared-state guard is detected by the test.

`actual-rocket-preparations-v2/summary.json` additionally prepares all ten
actual Rocket host-owner images retained from iteration 119 at master credits
520,064, 700,032, 900,096 and 3,250,048 in fresh native sanitizer and VCS DPI
processes. All 80 complete owner readbacks and eight execution guards pass.
Its startup metadata is independently reconstructed from the exact logged TSI
arguments, trusted workload bytes and complete ELF symbol table. It is not a
captured CPU semantic image. Original credit/enqueue labels are preserved;
this check neither certifies CPU cut labels nor resumes a CPU. The diagnostic
argument-count pilot remains separate from accepted evidence.

The workload SHA-256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Build settings remain exactly those in the table above. Neither a bitstream nor
an FCFS owner whitelist is used for the Rocket build.

All three complete exact-recipe controls pass at C=3,329,794. Default/buffered
evidence is `rocket-controls/invocation-6uujvu27/summary.json`; sealed evidence
is `rocket-sealed-terminal/summary.json`. All full hart traces and every
workload/store print-cycle label match the uninterrupted reference. Independent
audits pass 104 known host images at 12 active samples. Each control retains
the complete 16 GiB backing memory. Actual loader/context/TSI/bridge objects
equal independent recompilation (`native-terminal-build-audit.json`); the
executable contains the new API with every audited owner header
(`native-polling-provider-audit.json`).

Fresh ordinary RTL VCS reads all 318,637 pattern words and seven clocks before
its first edge (`ordinary-rocket-probe/run.log`). This remains a pattern
diagnostic, with no captured CPU replay. All eight preserved native suites
pass, including 267 Python tests and FCFS
(`native-regressions/invocation-6xbkqrhy/summary.json`).
All 13 retained host suites and all 19 independent component/native audits pass
(`host-regression-results.json`, `independent-component-audits.json`). The
preserved three-owner continuation still detects all eight first divergent
mailbox writes. One passing invocation used the prior controller-recheck root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration119-controller-rechecks/polling-devices/invocation-4hbo5abo/summary.json`.
Its original files remain in place; `external-evidence.json` binds their exact
hashes. No original evidence was moved or overwritten. The final preservation
guard passes all 100,378 prior cataloged artifacts and 1,011 native input
bindings. Existing controller commits were published FireSim first, then
Chipyard, with queried remote tips matching (`github-publication.json`). No
staging, local commits or protected plan/environment changes were performed.


Executable native check from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_prepare_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration120-controller-rechecks/polling-prepare
```

Independent retained-image, byte-oracle, source and native-command audit:

```sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_prepare_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration120/polling-prepare/invocation-p95inli2/summary.json
```

Repeat the exact-recipe complete default/buffered four-hart controls:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration120-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration120-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration120-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration120/rocket-controls/invocation-6uujvu27/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

Repeat the ordinary RTL diagnostic in a fresh directory:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration120-controller-rechecks
checkpoint_probe_dir=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration120-controller-rechecks/ordinary.XXXXXX")
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
cd "$checkpoint_probe_dir"
/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/simv \
  -no_save +vcs+initreg+0 +vcs+initmem+0 \
  +pattern=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/complete-pattern.txt \
  +baseline=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/initial-baseline.txt
```

Complete CPU simulator/FAME/channel/memory/bridge ownership, syscall descriptors,
signals, stop/exit state and coherent executable caller reconstruction remain
pending. The ordered component list and cross-owner checks cannot prove common
CPU-cut provenance or replace aggregate build identity. Required active CPU cuts,
fresh complete Level-1 continuation, independent captured Level-2 zero-edge
readback/replay and whole-CPU first-divergence tests remain pending. BOOM and
Saturn stay pending; physical FPGA and ASIC power stay deferred.

## Iteration 119: bound polling/terminal/BCD transaction

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration119/`.
Both CPU levels remain **in_progress**. The production BCD now binds directly
to its destination polling owner. `load_sealed_polling_checkpoint` prepares
the complete poll phase, mailbox command and response queue, sealed input
cursor/output transcript and pending BCD commands before publishing any owner.
It rejects arbitrary response closures and unordered or incomplete membership.
No component image format changes. See [tsi-sealed-terminal.md](tsi-sealed-terminal.md).

`polling-devices/invocation-20wykfub/summary.json` and the independent
`polling-devices-independent-audit.json` pass native ASan/UBSan and VCS DPI
across all four producer/destination pairings at all 56 component cuts. An
independent byte oracle checks every semantic field in all three images before
services and after every continued operation: 224 fresh restores, 6,160 host
operations and 19,824 complete owner readbacks. All nine polling phases are
covered, including blocked reads, occupied mailboxes, two queued responses,
binary input, output, EOF with pending commands and completion. These are
component operation labels, not semantic CPU target-cycle cuts.

`polling-devices-rocket-parameters/invocation-8_b2bzms/summary.json` repeats the
entire check with workload mailbox addresses `0x800003c0`/`0x80000400` and
production polling/BCD queue limits 1,048,576. It adds another 224 fresh restores,
6,160 operations, 19,824 readbacks, 932 malformed rejections, 32 membership
rejections, four unbound callback rejections, 44 allocation failures and eight
first-divergence cases. The diagnostic variant's source and all native commands
are retained; this still exercises only the three component owners.
`polling-devices-rocket-parameters-independent-audit.json` binds those exact
addresses to the workload ELF and checks both queue configurations and complete
initial BCD/terminal bytes against all four actual sealed workload host samples.

Four fresh rejection processes pass 932 malformed/incompatible image cases,
32 missing/extra/reordered/duplicate/unknown owner sets, four unbound callback
rejections and 44 allocation failures (11 allocation points per process).
All three destination images differ from the source; every failed transaction
preserves their entire readbacks and enters no services. Eight structurally
valid terminal-cursor or polling-response corruptions first diverge at host
operation 20, `fromhost_write`, expected `0x0100000000000141`, actual
`0x0100000000000100` or `0x0100000000000140`. The divergent write is not
acknowledged and execution stops there.

`polling-group-guards-v2/summary.json` adds 24 native sanitizer/VCS guards for
unbound/missing/live owners, actual incompatible addresses, queue limits and
input bytes, and active or poisoned poll, terminal and BCD service boundaries.
`polling-group-guards-independent-audit.json` checks all 34 readable peer images
against independent expected bytes. Poisoned owners remain uninspectable; the
checks do not invent a saved image for interrupted state. Diagnostic source and
build/runtime argv are retained under the diagnostic root and in the command index.

`polling-transaction-mutation/summary.json` retains a negative control:
diagnostic headers using sequential validate/load fail the same test with
`polling transaction partially published state or entered services`. The
mutation does not modify production source. The initial VCS static-library
link-order pilot is retained separately and is not a passing check.

All eight preserved native suites pass, including 267 Python tests, FCFS and
the checkpoint fixtures (`native-regressions-accepted/invocation-4yitb3d4/summary.json`).
The earlier full-suite invocation ran its eight checks but failed its final
source-binding guard because test-harness link flags changed during that run;
the accepted invocation reruns every check against stable inputs. Actual Rocket
loader/context/TSI/bridge objects match independent recompilation
(`native-terminal-build-audit.json`). Fresh ordinary RTL VCS again reads all
318,637 pattern words and seven clocks before any edge
(`ordinary-rocket-probe/run.log`). Pattern readback is not captured CPU replay.

All three complete exact-recipe default/buffered/sealed four-hart controls pass
at C=3,329,794. Every full hart trace and workload/store print-cycle label matches
the uninterrupted reference. The workload SHA-256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Each control retains the full 16 GiB backing memory. Independent audits pass
all 104 known host images at 12 active samples: master credits 520,064, 700,032,
900,096 and 3,250,048 in each mode. The enqueue counter remains one ahead of
nonzero master credits; these samples are not certified CPU semantic cuts.
Results are retained in `rocket-controls/invocation-329hni1w/summary.json`,
`rocket-sealed-terminal/summary.json`, `rocket-independent-control-audit.json`,
`rocket-host-audit-accepted.json` and `sealed-workload-independent-audit.json`.

Executable native check from the Chipyard root (Y-2026.03-SP1, `-full64`,
system GCC/G++ 13; both environments sourced, license/compiler helper last):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_devices_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration119-controller-rechecks/polling-devices
```

Independent audit of the saved images, every continued image/event, exact
native commands, source snapshots and first-divergence records:

```sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_devices_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration119/polling-devices/invocation-20wykfub/summary.json
```

Repeat the exact-recipe complete default/buffered controls in fresh directories:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration119-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration119-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration119-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration119/rocket-controls/invocation-329hni1w/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

Repeat the ordinary RTL pattern diagnostic (zero captured CPU replay claimed):

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration119-controller-rechecks
checkpoint_probe_dir=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration119-controller-rechecks/ordinary.XXXXXX")
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
cd "$checkpoint_probe_dir"
/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/simv \
  -no_save +vcs+initreg+0 +vcs+initmem+0 \
  +pattern=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/complete-pattern.txt \
  +baseline=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/initial-baseline.txt
```

All 13 retained host suites and all 18 independent component/native evidence
audits pass (`independent-component-audits.json`). Three complete CPU requests,
16 invalid audit options and six invalid terminal-input cases reject before
execution; the existing-directory sentinel survives. The final preservation
guard passes all 53,043 prior cataloged artifacts and 1,006 prior native input
bindings. Existing controller commits were published FireSim
`383f97f46988b6168addf8c74f92357029a710a3`, then Chipyard
`b9e972b643dfc8664dfba2cc618679754c47173f`; queried remote tips match. Local
tracking refs report read-only warnings after successful remote updates. Both
plans and environment inputs remain unchanged from entry; no staging or local
commits were performed. No external dependency is missing.

Final results, actual native argv, executable checks, source snapshots and all
created diagnostics are indexed by `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json` and `artifact-manifest.json` under the diagnostic
root. The supported/active/poisoned guard diagnostic's initial compile pilot and
the changing-source-binding native-suite pilot are retained separately; only
completed, independently audited invocations are selected.

Complete HTIF restoration still requires serial transport, startup metadata,
syscall/file descriptors, signal, stop/exit and context/caller ownership. This
transaction does not certify that independently valid images came from one
coherent CPU cut. Complete simulator/FAME/channel/memory/bridge ownership,
required active CPU cuts, fresh Level-1 continuation and independently captured
Level-2 readback/replay remain pending. Exact recipe settings and workload hash
above remain the required configuration; no FPGA bitstream is built.

## Iteration 118: transactional sealed terminal and BCD restoration

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration118/`.
Both CPU levels remain **in_progress**. The production BCD component now
restores its bound sealed terminal and command queue as one transaction. It
parses and allocates both replacement states before nonthrowing publication,
rejecting unsupported/active owners and incomplete or unordered membership.
See [tsi-sealed-terminal.md](tsi-sealed-terminal.md).

`terminal/invocation-knyl8x5i/summary.json` passes native ASan/UBSan and VCS DPI
across all four backend pairings. All 52 fresh continuations/312 host events
retain complete pre-service readback and matching suffixes. Four additional
fresh transactions reject 576 malformed pairs, 28 missing/extra/reordered/
duplicate/unknown owner sets and 44 allocation failures (11 allocation points
per process). Both destination images intentionally differ from their source;
all failures leave both images unchanged and issue no service. Valid restores
retain the destination response binding and consume the correct next byte.
The independent byte oracle still detects all four cursor corruptions at host
event 2, expected response `0x0100000000000141`, actual `0x0100000000000100`.

The mutation control in `transaction-mutation/summary.json` compiles the old
validate-then-load sequence in a diagnostic header. Its transaction test exits
2 with `FAIL transaction partially published state or entered services`, as
required. This checks that the allocation-failure test detects the original
failure. The mutation is confined to diagnostic inputs under `runs/`.

All eight preserved native suites pass, including 267 Python tests, FCFS and
both checkpoint fixtures. Startup metadata/device lifetime checks pass. The
actual Rocket loader/context/TSI/bridge objects match independent recompilation
(`native-terminal-build-audit.json`). The ordinary RTL pattern diagnostic
again reads all 318,637 semantic words/seven clocks before its first edge
(`ordinary-command.json`, `ordinary-result.json`, `ordinary-rocket-probe/run.log`).
Those values are patterns; no captured CPU replay is claimed.

All three complete default/buffered/sealed four-hart workload controls pass at
C=3,329,794. Every full hart trace and workload/store print-cycle label matches
the uninterrupted reference. Independent audits pass all 104 known host images
at 12 active samples: credits 520,064, 700,032, 900,096 and 3,250,048 in each
mode. The eight protocol images agree between sealed and default controls at
the same credits. The enqueue counter remains one ahead of nonzero master
credits; these are not certified CPU semantic cuts. Workload SHA-256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Each control retains the full 16 GiB backing memory.

All 13 retained host suites and all 17 independent component/native evidence
audits pass. The dispatcher retains 240 fresh continuations, 7,012 complete
peer readbacks, 5,112 atomic invalid-image rejections and four first component
divergences. Three complete CPU requests, 16 invalid audit options and six
invalid terminal input cases reject before execution. The existing audit
directory's sentinel survives. These are prerequisite and component checks.
Complete CPU aggregate restoration, caller reconstruction, required semantic
CPU cuts, fresh Level-1
continuation and independently captured Level-2 readback/replay remain pending.
Exact recipe settings above are unchanged; no FPGA bitstream is built.

Executable native check from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_terminal_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration118-controller-rechecks/terminal
```

Audit the retained invocation independently:

```sh
python -m tools.checkpoint_formats.tests.verify_tsi_terminal_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration118/terminal/invocation-knyl8x5i/summary.json
```

Rebuild and repeat the exact-recipe complete default/buffered controls:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration118-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration118-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration118-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration118/rocket-controls/invocation-924uqcth/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

Current actual build/runtime argv, hashes and runtime logs are retained under
`rocket-controls/invocation-924uqcth/`. All VCS shells source both repository
environments and `vcs-env.sh` last, using Y-2026.03-SP1, `-full64`, system
GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`.

Final results, raw native argv and reproducible verification commands are
indexed by `summary.json`, `selected-results.json`, `raw-native-commands.json`,
`verification-commands-native.json`, `native-input-archives.json` and
`artifact-manifest.json` under the run root. Independent checks are retained in
`independent-component-audits.json`, `rocket-independent-control-audit.json`,
`rocket-host-audit-accepted.json` and `sealed-workload-independent-audit.json`.
Existing controller commits were published FireSim
`7e2fd428d35faa38bd376fd3ac59fb72989edf96`, then Chipyard
`205782abb91bd6a10e4d36a42829707514262570`; queried remote tips match.
Both plans and environment inputs remain unchanged from entry. No staging or
local commits were performed. The final preservation guard passes all 53,019
prior cataloged artifacts and 1,005 prior native input bindings. No external
dependency is missing.

## Iteration 117: bind sealed terminal metadata and polling peers

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration117/`.
Both CPU levels remain **in_progress**. Sealed mode now has revision-4 startup
metadata that binds the terminal's complete pristine image and input alongside
the seven existing protocol peers. Default live mode preserves revision-3 bytes.
The suspended polling audit now reads, validates and checks stability of ten
components: poll, program loader, initialization, host control, serial read,
serial queues, load-memory read, load-memory queues, BCD and terminal. This is
an inventory of these components, not a complete HTIF/CPU restore profile.
See [tsi-sealed-terminal.md](tsi-sealed-terminal.md).

`terminal/invocation-vszs_4d9/summary.json` passes native ASan/UBSan and VCS DPI.
Across all four producer/destination backend pairings, eight fresh preparations
read back complete metadata and 64 pristine peer images with zero target
services, context entries or edges. Replacing the input file after construction
preserves its captured bytes. All 16,004 malformed images and 16 incompatible
cases (live mode, different input, omitted terminal owner and reordered owners)
reject before peer/mailbox mutation. Twenty-four post-preparation guard checks
reject caller entry, duplicate preparation and polling inspection.

Two production TSI runs audit 60 complete component images at first polling,
after consuming binary input and after output. Startup metadata remains equal
through terminal progress. The original paired terminal/BCD checks retain all
52 fresh restores/312 host events, 568 atomic malformed rejections, four
incompatible images, eight incomplete pairs, 28 service guards and four first
response divergences after semantic cursor corruption. The first divergent
response remains host event 2, expected `0x0100000000000141`, actual
`0x0100000000000100`. These host events are not semantic CPU target cycles.

Executable native check from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_terminal_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration117-controller-rechecks/terminal
```

Rebuild and repeat the exact-recipe default/buffered controls:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration117-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration117-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration117-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration117/rocket-controls/invocation-jqd5_x7n/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

Exact recipe settings remain above. The rebuild and default/buffered workload
controls are retained in `rocket-controls/invocation-jqd5_x7n/`; the additional
sealed-terminal control is under `rocket-sealed-terminal/`. All three controls
pass at C=3,329,794. Every full hart trace and every
workload/store print-cycle label matches the uninterrupted reference. The sealed
run independently checks ten complete component images at each active credit
520,064, 700,032, 900,096 and 3,250,048, alongside the 64 default/buffered images.
All 104 host images pass independent component audits; sealed protocol images
are byte-identical to the default control at the same credits.
The clock-token enqueue counter remains one ahead of each nonzero master credit;
neither counter is a certified CPU semantic boundary. Exact VCS argv, source
hashes and images remain in the run tree; `rocket-independent-control-audit.json`,
`rocket-host-audit-accepted.json` and `sealed-workload-independent-audit.json`
retain the independent checks. The workload remains SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
No FPGA bitstream build is used. Every VCS shell sources both environments and
`vcs-env.sh` last, with Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make
`VCS_FLAGS=-Mupdate`.

All eight preserved native suites pass, including 267 Python tests, FCFS and
both small checkpoint fixtures. All 13 retained host suites and all 17
independent component/native audits pass. Dispatcher checks retain all 240 fresh
continuations, 7,012 complete peer readbacks, 6,772 continued operations, 5,112
atomic invalid images and four first component divergences. Default startup
metadata retains 24 fresh readbacks, 168 peer images, 13,916 malformed images,
20 incompatible cases, eight policy mismatches, 192 installed-XLEN rejections
and 704 loader-resource checks. Three complete CPU requests, 16 invalid audit
options and six invalid terminal input cases reject before execution; the
existing-directory sentinel survives. The actual loader, context, TSI and
bridge objects equal independent recompilation in `native-terminal-build-audit.json`.

Final recovery and native argv are indexed by `summary.json`,
`selected-results.json`, `raw-native-commands.json`,
`verification-commands-native.json`, `native-input-archives.json` and
`artifact-manifest.json`. The final preservation guard passes all 53,355 prior
cataloged files and 1,005 native input bindings. Existing controller checkpoints
were published FireSim `995e2a5b54bfd851b35dac96fcd4a1a3d68f8e69`, then
Chipyard `81e8082eae94c4f7cf1c2ee5c0560f748c160013`; queried remote tips match.
Local tracking-ref updates warned about read-only `.git` after successful pushes.
Both plans and guarded environment inputs remain unchanged. No staging or local
commits were performed.

The fresh ordinary-RTL diagnostic passes all 318,637 semantic words/seven clocks
before its first edge (`ordinary-command.json`, `ordinary-result.json` and
`ordinary-rocket-probe/run.log`). Its state values are patterns, not captured
CPU execution. It cannot establish Level-2 replay. Fresh complete Level-1
continuation, independently captured Level-2 readback/replay, required semantic
CPU cuts and whole-CPU corruption acceptance remain pending. Syscall/file
state, signals, stop/exit, coherent caller reconstruction and atomic aggregate
restoration still need owners. Complete CPU admission remains disabled. No
external dependency is missing; physical FPGA validation and ASIC power remain
deferred.

## Iteration 116: sealed BCD terminal owner

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration116/`.
Both CPU levels remain **in_progress**. The opt-in production
`+checkpoint-terminal-input=/absolute/path/to/input.bin` captures bounded regular
file bytes at construction. The terminal owner binds all input bytes and owns
their cursor and binary output transcript. Fresh restore consumes no input and
does not emit output before the cut again. Default live terminal checkpoints
reject explicitly. See [tsi-sealed-terminal.md](tsi-sealed-terminal.md).

`terminal/invocation-imxpr74q/summary.json` passes native ASan/UBSan and VCS DPI:
52 fresh terminal/BCD pair restores at 13 device cuts across all four backend
pairings, 312 continued host events, complete pre-service readback, and identical
event/output suffixes and final owners. The independent Python oracle checks
every image byte. All 568 malformed images, four incompatible configurations
and eight missing/invalid peer cases reject without partial restore or services.
Four actual cursor corruptions diverge first at host event 2's BCD response.
Both backends pass live/active/interrupted/overflow guards (28 total).

Two production TSI transport checks consume all three captured bytes after the
original file is replaced, emit exact fromhost packets and a real BCD stdout
write, and terminate successfully. Startup metadata rejects the new mode until
its peer contract includes this additional owner. The terminal component has
no CPU admission profile. Live terminal/termios, syscall descriptors, signals,
stop/exit, coherent caller and complete aggregate ownership remain pending.
These are host-device cuts and first divergences, not semantic CPU boundaries.

Reproduce the new native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_terminal_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration116-controller-rechecks/terminal
```

The unchanged exact recipe settings remain above. Current build bindings are
`rocket-controls/invocation-jcdvoxvh/rocket-build-identity.json` and
`rocket-vcs-build.log` in the same invocation. The independent
`native-terminal-build-audit.json` proves that actual TSI, bridge, context and
loader objects equal independent recompilation and that the executable contains
all terminal checkpoint methods. Every build/simulation shell sources both
environments, then `vcs-env.sh` last, retaining Y-2026.03-SP1, `-full64`, GCC/G++
13 and reused Make `VCS_FLAGS=-Mupdate`. No bitstream build is invoked.

Fresh ordinary RTL VCS again passes the complete 318,637-word/seven-clock pattern
readback before any edge; `ordinary-command.json` and
`ordinary-rocket-probe/run.log` bind the executed command/result. This diagnostic
does not contain captured CPU state or trace replay. The complete four-hart
workload remains SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The run root retains native command/results and a separately launched
`rocket-sealed-terminal/command.json` for a complete workload control with the
new mode. All three complete controls pass at C=3,329,794. Every full hart trace
and workload/store CPU print-cycle label matches the uninterrupted reference.
`rocket-independent-control-audit.json`, `rocket-host-audit-accepted.json` and
`sealed-workload-independent-audit.json` retain independent checks. The two
default/buffered controls again audit all 64 component images at eight active
samples. Credits 520,064/700,032/900,096/3,250,048 remain distinct from their
one-token-ahead enqueue labels and from uncertified semantic CPU cuts. Each
native run uses the full 16 GiB backing memory. None is a checkpoint continuation.

Reproduce the exact recipe controls with their complete comparisons:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration116-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration116-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration116-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration116/rocket-controls/invocation-jcdvoxvh/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

All eight preserved native suites pass, including 267 Python tests, FCFS and
both small checkpoint fixtures. Startup metadata retains all 24 fresh readbacks,
168 peer images, 13,964 malformed images, 20 incompatible cases, eight exact
XLEN-policy rejections, 192 installed-XLEN rejection/recovery cases and 704 loader
resource cases. Default device lifetime retains all 352 instances. The three
complete CPU requests, 16 invalid audit options and six malformed terminal input
options reject before execution; the existing-directory sentinel is preserved.
The latter reject missing/empty paths, a directory, FIFO, oversized file and
duplicate options in the real recipe executable. All 13 retained host suites and
17 independent component/native audits pass. The dispatcher retains 240 fresh
continuations, 7,012 complete peer readbacks, 5,112 atomic invalid images and four
first component divergences. Both independently allocated BCD regression runs
pass and remain preserved. Final source/command bindings, exact native argv and
results are indexed by `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json` and the exhaustive `artifact-manifest.json`.

The preservation audit passes all 54,064 cataloged iteration-115 artifacts and
1,005 native input bindings. Existing controller commits were published FireSim
`9be71efc6cd5d4ceb8b250001204c66210974bf2`, then Chipyard
`978ac1785de7295c2e08833612fd2d349a54e382`; queried remote tips match. Local
tracking-ref updates warned about read-only `.git` after successful pushes.
Both plans remain unchanged from the iteration guard. No staging or local
commits were performed. Complete Rocket Level-1 continuation, required CPU
checkpoint cuts, independent Level-2 captured readback/replay and CPU corruption
acceptance remain pending. No external dependency is missing.

## Iteration 115: exact installed HTIF XLEN policy

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration115/`.
Both CPU levels remain **in_progress**. Startup metadata revision 3 now binds
actual `required_xlen` received from the installed HTIF, including a policy set
through its nonvirtual base setter. Policies 0 and 64 produce distinct images
for the same 64-bit ELF; cross-policy and legacy revision-1/revision-2 images
reject before publishing state. See [tsi-xlen-policy.md](tsi-xlen-policy.md).
Complete device, terminal, syscall, stop/exit/signal, coherent caller and aggregate
CPU state ownership remain pending.

`policy-provider/invocation-l5ka4aye/summary.json` passes 352 native sanitizer/
VCS provider cases and two installed-loader negative controls. Unexpected path,
entry, offset, null-memory, duplicate, nested and missing calls reject, including
caught failures; thread-local observation and exception recovery pass.
`startup-metadata-final/invocation-6lothuh5/summary.json` passes 24 fresh
readbacks, 168 unchanged peer images, 13,964 malformed images, 20 incompatible
cases, eight exact-policy mismatches, 192 installed incompatible-XLEN rejection/
recovery checks and 704 loader-resource cases. The independent canonical oracle
checks every image byte, including both policies' configuration word counts.

`shared-metadata-lxr9oh8w/summary.json` independently exercises the installed
shared HTIF with explicitly linked owned loader/context objects: another 24
fresh readbacks, 168 peer images and eight exact-policy rejections, with zero
preparation services/context entries/target edges. Native ASan/UBSan and VCS
cover every source/destination backend pairing. `native-policy-build-audit.json`
proves that the actual exact-recipe loader, context, TSI and bridge objects equal
independent recompilation byte for byte. Dynamic symbols bind shared HTIF to the
executable's owned loader and observation scope. The Make overlay rule now
tracks the observer header as a rebuild dependency.

Fresh component checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_elfloader_policy_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration115-controller-rechecks/policy
python -m tools.checkpoint_formats.tests.verify_tsi_startup_metadata_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration115-controller-rechecks/metadata
```

The exact recipe settings above are unchanged. The workload remains the complete
four-hart self-checking ELF, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Both complete default/buffered controls pass at C=3,329,794 in
`rocket-controls/invocation-dp59tcr0/summary.json`. Every complete hart trace and
workload/store CPU print-cycle label matches the uninterrupted reference. The
independent control audit and `rocket-host-audit-accepted.json` verify all 64
host component images at eight active samples, plus startup rejection at zero.
Master credits 520,064, 700,032, 900,096 and 3,250,048 retain distinct clock-token
labels (one token ahead); required semantic CPU edges/outstanding-memory cuts
remain uncertified. Both native control processes use 16 GiB backing memory;
neither is a CPU checkpoint continuation. Reproduce the full controls with:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration115-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration115-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration115-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration115/rocket-controls/invocation-dp59tcr0/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

The native recipe executable is under that invocation's
`build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim`.
Its exact Make/VCS/driver commands and all 60 native units/dependencies are bound
by `rocket-vcs-build.log` and `rocket-build-identity.json` in the invocation.

The separate ordinary RTL pattern diagnostic uses
Y-2026.03-SP1 and passes all 318,637 words/seven clocks with zero edges. Its exact
argv is `ordinary-command.json`, and its fresh log is
`ordinary-rocket-probe/run.log`. This is not captured CPU state or replay.

All eight preserved native suites pass, including all 267 Python tests, FCFS and
both small fixtures. Default-device lifetime checks retain all 352 instances
and the original leaking-source negative control. All 13 retained host suites,
transport and context suites pass; all 19 independent component/native audits
pass. Serial retains 905 native commands and 768 fresh component restores;
full initialization retains 1,471 native commands. The fresh dispatcher suite
retains 240 continuations, 7,012 complete peer readbacks, 5,112 atomic invalid
images and four first semantic divergences. These are host component results.
All three complete CPU requests and all 16 invalid audit options reject; the
existing-directory sentinel remains unchanged. The publication tips match
controller commits FireSim `5a1da7a237c48f1039ffb26ab082c7cee11aa1d2`, then
Chipyard `5d1f3112ec8d66ef52664a57488dc9734b9368ee`; local tracking-ref updates
warned about read-only `.git` after successful remote pushes. All 58,484
cataloged iteration-114 artifacts and 999 original native bindings pass final
preservation checks. Required semantic CPU cuts,
fresh complete Level-1 continuation, independent Level-2 capture/readback/replay,
whole-CPU invalid images and first semantic divergence remain pending. No
external dependency is missing. Physical FPGA validation and ASIC power stay
deferred. No CPU checkpoint profile is enabled.

The first metadata attempt failed an independent Python oracle length check;
two provider-symbol diagnostic pilots missed the demangler's `[abi:cxx11]`
suffix. An existing-directory fixture omission and an unsupported context-audit
CLI option also remain preserved. Corrected checks pass separately. Recovery
summaries, exact native argv/results, source snapshots and artifact hashes are
indexed by `summary.json`, `selected-results.json`, `raw-native-commands.json`,
`verification-commands-native.json` and `pilots.json` under the diagnostic root.
Both plans remain read-only; no staging or local commits were performed.

## Iteration 114: default HTIF device lifetime

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration114/`.
Both CPU levels remain **in_progress**. The production default HTIF syscall
device and device table now belong to the TSI object, with explicit release
after normal `stop()`. This releases their command tables and three duplicated
standard-stream descriptors when a suspended TSI is destroyed. See
[tsi-default-device-lifetime.md](tsi-default-device-lifetime.md) for ownership
and limits. Semantic device state and aggregate CPU restoration remain pending.

`device-lifetime/invocation-as3onvw3/summary.json` passes native ASan/UBSan and
VCS DPI checks: 176 actual TSI instances per backend, 11 cuts with 16 repetitions,
128 suspended callers and 32 completed callers per backend. Every teardown
preserves the exact descriptor map; initialized/active/completed counts, ELF
load/merge packets, BCD pending command, installed syscall packets and stop/exit
results also match. The original source/header reproduce three leaked
descriptors at the first polling cut. Earlier runner/packet-expectation pilots
remain separately retained. These are host resource tests, not CPU checkpoints.

Fresh native resource check (a new invocation is allocated on each run):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_device_lifetime_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration114-controller-rechecks/devices \
  --negative-control-source automations/checkpoint_loop/runs/m11-iteration114/original-default-devices/firesim_tsi.cc
```

All eight final preserved native suites pass, including 267 Python tests, FCFS
and both small fixtures. The first regression invocation was invalidated by a
test-source change; its failed source-stability guard is preserved separately.
The final invocation binds the unchanged final source. Startup metadata retains
12 fresh readbacks, 84 peer images, 13,852 atomic invalid images, 18 incompatible
cases, 192 installed-XLEN rejection/recovery checks and 704 loader resource cases.
Three complete CPU requests and all 16 invalid host-audit options reject before
execution/publication. All 11 retained host suites, serial and transport-fault
suites pass. All 17 independent component/native audits pass. The fresh ordinary RTL
pattern diagnostic passes all 318,637 words before any edge; it is not captured
semantic state/replay. All 137,659 sealed iteration-113 artifacts and 1,018
native input bindings pass preservation checks. Existing controller-created
iteration-113 commits are published FireSim first, then Chipyard; queried tips
match. Local tracking-ref refreshes failed on read-only `.git` after successful
remote updates. No staging, local commits or protected-input edits were made.

Fresh exact-recipe four-hart controls (complete runs and trace comparisons):

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration114-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration114-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration114-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration114/rocket-controls/invocation-ed0qjmsv/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

The resource test's actual native VCS executable is
`device-lifetime/invocation-as3onvw3/simv`; its `commands.json` records the exact
Y-2026.03-SP1 `-full64` build and `-no_save +source=... +destination=...` run.
The ordinary Rocket executable is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/simv`;
`ordinary-command.json` records this iteration's fresh process, exact
`+pattern`/`+baseline` paths and required environment sourcing. Its
`ordinary-rocket-probe/run.log` reports seven clocks and zero edges. These
native checks retain distinct simulator/semantic scopes.

Both complete exact-recipe default/buffered four-hart controls pass at
C=3,329,794: `rocket-controls/invocation-ed0qjmsv/summary.json`. Every full hart
trace and workload/store print-cycle label matches the uninterrupted reference.
Workload ELF SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Both runs use the complete 16 GiB backing-memory configuration.
`rocket-host-audit-accepted.json` independently validates all 64 component
images across eight active samples at master credits 520,064, 700,032, 900,096
and 3,250,048. Startup rejects at zero. Clock tokens retain their one-token lead;
these samples do not certify the required semantic CPU or outstanding-memory cuts.
`native-device-build-audit.json` checks that both actual constructor/driver
translation units, `firesim_tsi.cc` and `tsibridge.cc`, were recompiled with
the current header. The native identity binds all 60 units and their dependencies.

Full initialization passes 1,471 native commands, including 768 actual and 320
mixed-policy fresh restores. Serial passes 905 commands, including 768 actual
fresh restores. Retained host tests include BCD's 68 fresh component restores
and four first semantic divergences, polling's 72 fresh continuations and
38,744 atomic invalid checks, and the independent transport oracle's 1,012
requests/four bridge runs. These are component checks; whole-CPU image rejection
and first-divergence cases remain pending.

`init-resume/invocation-7mx9t0i9/summary.json` passes all 240 fresh dispatcher
continuations, 7,012 complete peer readbacks, 5,112 atomic invalid images and
four first divergences. Both independently rerun preservation audits retain all
137,659 sealed iteration-113 artifacts; the original 1,018 native input bindings
also remain valid. Plans, environment/Conda inputs and both indices match their
guards. No staging or local commits were performed.

Recovery under this diagnostic root: `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json`, `pilots.json`,
`native-device-build-audit.json` and `artifact-manifest.json`. They preserve
exact native VCS commands/results, source bindings, host readbacks, full workload
traces and separately retained failed pilots. Complete CPU Level-1 and Level-2
acceptance remains pending.

Required early/warm/outstanding-memory/late CPU checkpoints, first CPU semantic
divergence cases, complete fresh Level-1 continuation and independently captured
Level-2 zero-edge readback/finite replay remain pending. The resource checks do
not certify these cuts. BOOM/Saturn remain pending. No FPGA or ASIC validation
is claimed.

## Iteration 113: FESVR context lifetime

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration113/`.
Both CPU levels remain **in_progress**. This increment manages process-local
FESVR stack resources; complete semantic context reconstruction remains pending.
See [tsi-context-lifetime.md](tsi-context-lifetime.md) for exact ownership and
unsupported lifetimes. The installed context header/class ABI is unchanged.
The build-local archive replaces only `context.o` and `elfloader.o`, with the
other 12 members checked byte-for-byte. Both replacement objects are explicit
native VCS linker inputs, independently recompiled and compared across Rocket
and all four final host suites. `verified/context-linkage-final/summary.json` binds
the actual executable caller and shared HTIF loader resolution. The shared
library has no FESVR context exports.

`verified/context/invocation-x679fyt3/summary.json` passes native sanitizer and VCS
DPI checks. Each backend accounts for 278 allocated/released stacks and zero
live stacks: 128 suspended and 128 returned principal lifetimes, 1,018 principal
switches, siblings, nested creators, allocation-failure recovery, worker-root
cleanup and a retained metasim-style worker object. The original-library control
retains both stacks. Six fresh death checks explicitly reject active/creator
destruction and active-child process exit before freeing an executing stack.
Raw native stack bytes are never checkpoint payloads.

`verified/transport/invocation-pri708pp/summary.json` passes the previously failing
native transport sanitizer check and native VCS checks: 1,012 requests, 566,096
compared direct records, four actual bridge runs, 32 invalid requests, four
callback-unwind checks and 24 bridge-control readbacks. The independent oracle
covers every bus beat/lane and actual ELF merge/reset trace. No sanitizer
suppression is used. Original failed iteration-112 transport evidence remains
unchanged.

The initial context pilot rejected metasim's intentionally retained registry at
driver-thread exit. A real short Rocket timeout reproduced it; the final
`verified/retained-context-exit/summary.json` passes normal deliberate-timeout termination
at 1,025 target cycles without a context abort. Earlier source-drift, strict-exit
and shared-provider-assumption pilots remain separately retained. They do not
certify final sources.

`verified/context-instrumented/summary.json` additionally passes normal and
three lifetime-rejection checks with both the fixture and actual context source
compiled under ASan/UBSan. `verified/startup-metadata/` passes 704 resource cases,
192 XLEN rejection/recovery checks, 12 fresh readbacks, 84 complete peer images,
13,924 malformed images and 18 incompatible cases. The production shared-HTIF
route independently passes the same checks with 13,916 malformed images.
All eight final native suites pass, including 267 Python tests and FCFS. Three
complete-CPU requests, 16 invalid audit options and five malformed/in-place
archive requests reject before execution or publication.

Both complete final default/buffered four-hart controls pass at C=3,329,794:
`verified/accepted/rocket-controls/invocation-0fmb4l0r/summary.json`. Every full
hart trace and workload/store print-cycle label matches the uninterrupted
reference. Workload ELF SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The independent host audit validates all 64 component images across eight active
samples at master credits 520,064, 700,032, 900,096 and 3,250,048. Startup rejects
at zero. Clock tokens retain their one-token lead; required semantic target-edge
and outstanding-memory checkpoint cuts remain uncertified. Build identity binds
all 60 driver translation units, both separate resource objects and dependencies.

All 11 retained host suites, serial and transport fault suites pass. Serial
records 905 commands. Full initialization records 1,471 commands, including 768
actual and 320 mixed-policy fresh restores; dispatch passes all 240 restores,
7,012 complete peer readbacks, 5,112 atomic invalid images and four first
divergences. BCD retains 68 fresh restores and four first semantic divergences.
These are host component checks, not complete CPU image restores.

The fresh ordinary RTL pattern probe passes all 318,637 semantic words and seven
clocks before any edge. It is not captured CPU state/replay. All 66,509 sealed
iteration-112 artifacts and 1,080 original native input bindings pass preservation
checks. Plans, environment, installed/protected Conda inputs and both indices
match their guards. Existing controller-created iteration-112 commits were
published FireSim first, then Chipyard; queried remote tips match. Tracking-ref
refreshes emitted read-only `.git` warnings after successful remote updates.
No staging or local commits were performed.

Recovery under the diagnostic root: `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json`, `pilots.json`,
and the complete `artifact-manifest.json`. These preserve current sources,
actual native commands/results, readbacks, workload traces and failed pilots.

Fresh native resource checks (each uses a new invocation directory):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_fesvr_context_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/context
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/transport
python -m tools.checkpoint_formats.tests.verify_tsi_startup_metadata_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/startup-metadata
```

Fresh exact-recipe four-hart controls (full trace comparisons; no bitstream):

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration113/verified/accepted/rocket-controls/invocation-0fmb4l0r/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

These controls do not certify checkpoint cuts. Full HTIF configuration/build/
XLEN, terminal/syscall, stop/signature/exit/signal and semantic caller ownership,
atomic host assembly, complete simulator/FAME/channel/memory/bridge ownership,
coherent required CPU cuts, fresh Level-1 CPU continuation and independent
Level-2 captured readback/replay remain pending. BOOM and Saturn remain pending.
No external dependency is missing. Physical FPGA validation and ASIC power stay
deferred; plans remain read-only and the controller owns local commits.

## Iteration 112: ELF-loader resource cleanup

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration112/`.
Both CPU levels remain **in_progress**. This increment closes a host startup
resource leak; it does not establish complete CPU continuation or semantic replay.

`final/startup-metadata/invocation-na1k5u8y/summary.json` passes native sanitizer
host checks and VCS DPI checks with the actual installed HTIF and a repository-owned
ELF-loader overlay. Only `elfloader.o` changes in a build-local FESVR archive;
the other 13 members and the installed Conda archive remain byte-identical.
The original ELF decoding/target-write source is retained exactly. See
[tsi-metadata-compatibility.md](tsi-metadata-compatibility.md) for scope and limits.

The suite passes 704 resource cases across 11 modes: XLEN 32/128 mismatch,
wrong endianness, first/second memory-write exceptions, empty/missing/directory
inputs, and successful XLEN 0/64 and BSS loading. Successful metadata and all
target writes match independent expectations. Kernel descriptor and mapping
counts return to baseline after every case. Original installed-loader native
and VCS negative controls each fail on the first leaked mapping as expected.
The metadata paths pass another 192 repeated installed-XLEN rejection/retry
checks, 12 fresh complete metadata readbacks, 84 unchanged peer images,
13,900 malformed images and 18 incompatible/legacy cases. All happen before
any target service, context entry or target edge in the destination.

`transport-context-diagnostic/summary.json` confirms a separate pre-existing
installed context-stack leak. Native sanitizer transport runs against both the
original archive and overlay exit 1 with two leaked 1 MiB stacks. Both native
runs and both VCS runs retain identical complete functional outputs; all compare
with the independent transport/bridge oracle. The native transport sanitizer
check remains **failed**, without suppression. Its source fixture and failed
module invocation remain under `transport/`; this diagnostic does not grant CPU
support. Context destruction and suspended-stack resource ownership remain pending.

The first final audit found a production linkage gap: the launcher resolved
`load_elf` from `libriscv.so`, so naming a patched archive did not force its member
to load. The Makefrag now extracts and passes the audited member as a driver
object, avoiding VCS's repeated inherited/explicit linker flags.
`rocket-loader-binding/summary.json` verifies its strong dynamic definition and
actual shared-HTIF resolution before any target edge. `rocket-loader-linkage-final/`
independently rebuilds that object with dependency output and audits actual
providers: shared HTIF/memif/syscall functions, static FESVR contexts and the
explicit loader. Both complete corrected controls pass under
`accepted/rocket-controls/invocation-f_4w073_/`. Earlier controls remain
uninterrupted workload reference evidence and cannot certify production loader binding.

`shared-metadata/invocation-4k5iq0tw/summary.json` additionally validates the
actual shared-HTIF route with the Rocket loader object, in native C++ and VCS:
704 resource cases, 192 XLEN rejections, 12 complete fresh readbacks / 84 peer
images, 13,844 invalid images and 18 incompatible cases pass. Both installed
negative controls still fail as expected. No target edge, context entry or
target service occurs during destination metadata preparation.

`accepted/rocket-controls/invocation-f_4w073_/summary.json` passes both complete
exact-recipe default/buffered four-hart controls at C=3,329,794. Every full trace
and workload/store cycle label matches the uninterrupted reference. The workload
ELF SHA-256 is
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The eight active host samples independently pass all 64 component images; master
credits and clock tokens remain distinct from uncertified semantic target edges.
`rocket-loader-linkage-final/summary.json` recompiles the loader with native dependency
output, binds its installed configuration/header inputs, and compares its object
byte-for-byte with the Rocket and metadata-test archive members. The 13 other
installed members are unchanged. The build retains 60 VCS driver translation
units plus the separately compiled loader replacement.

`final/native-regressions/invocation-5c4ntkpm/summary.json` passes all eight
preserved native suites, including 267 Python tests and FCFS. All 11 retained
host suites pass individually (`host-regression-results-final.json`); the serial
suite and production transport fault-injection suite also pass. Full initialization
passes 1,471 commands, including 768 actual and 320 mixed-policy fresh readbacks.
Initialization dispatch retains 240 fresh restores, 7,012 peer readbacks,
5,112 atomic invalid-image checks and four first divergences. BCD retains 68
fresh restores and four first divergences. These are host component checks.

The fresh ordinary RTL diagnostic passes 318,637 pattern-word readbacks across
seven clocks before any edge. It is not a captured CPU checkpoint or replay.
Three complete-CPU admission requests and all 16 invalid audit options reject
before execution. All 45,803 sealed iteration-111 artifacts and 1,050 retained
native input bindings pass preservation checks. Failed source-binding/runner
pilots and the unsuppressed transport sanitizer failure remain under the run
root and are indexed by `pilots.json`.

Recovery artifacts are `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json`, and the complete
`artifact-manifest.json`. Native commands include actual builds, simulator
invocations, source-bound audits and both original-library negative controls.

Executable fresh metadata recheck (allocates new artifacts):

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/metadata-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_startup_metadata_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/startup-metadata
```

Executable fresh exact-recipe controls (copies the tested build, regenerates
the overlay and invokes pinned native VCS; no bitstream build):

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration112/accepted/rocket-controls/invocation-f_4w073_/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

Executable production shared-HTIF metadata recheck:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/shared-metadata-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python automations/checkpoint_loop/runs/m11-iteration112/verify_shared_metadata.py \
  --out automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/shared-metadata
```

Retained full native regression audit:

```sh
python -m tools.checkpoint_formats.native_regressions --audit \
  automations/checkpoint_loop/runs/m11-iteration112/final/native-regressions/invocation-5c4ntkpm/summary.json
```

`overlay-rejections/summary.json` passes three atomic archive rejections:
unsupported missing/duplicate loader members and an attempt to overwrite the
input archive. No output archive/report is published; input bytes remain
unchanged. The source audit independently verifies identical decoding and
target-write code after the resource setup. Existing controller commits are
published FireSim first, then Chipyard; queried remote tips match.

Remaining: installed context-stack cleanup/lifetime, exact HTIF configuration/build/XLEN policy, terminal/syscall and
stop/signature/exit/signal/context state, atomic aggregate host reconstruction,
complete simulator/FAME/channel/memory/bridge ownership, coherent required CPU
cuts, fresh Level-1 CPU continuation, independent Level-2 captured state/readback
and finite replay, and whole-CPU negative/corruption cases. BOOM and Saturn
remain pending. No external dependency is missing.

## Iteration 111: metadata transport contract and atomic XLEN preflight

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration111/`.
See [tsi-metadata-compatibility.md](tsi-metadata-compatibility.md) for exact
ownership and limits. Both CPU levels remain **in_progress**.

`startup-metadata/invocation-i3dksq0b/summary.json` passes installed-FESVR native
sanitizer and Y-2026.03-SP1 `-full64` VCS checks. All 12 fresh preparations read
back every metadata byte and 84 unchanged peer-component images before target
services, context entry or edges. All 13,852 byte-flip/truncation/extension cases
reject atomically, then accept a valid image. Eighteen incompatible argument,
ELF, option, constructor-only load-memory and legacy-image cases reject before
publication. Both actual source loaders complete their partial-write read/merge
and finish through HTIF PASS.

Revision 2 includes endianness, chunk sizes, load-memory capability and all seven
named pristine component images as configuration contracts. These are not the
live CPU-cut component states. Capture/preparation preflight the sealed local
ELF through the installed HTIF loader with target writes suppressed. This
closes a path where incompatible expected XLEN could fail after metadata
publication and poison the caller. Six tests change the real nonvirtual setter
through an `htif_t` reference, observe expected=32/actual=64, then recover with
64 and complete readback. This checks ELF compatibility; it does not serialize
the exact zero/64 XLEN policy or certify complete build identity. Installed
ELF-loader XLEN errors bypass `munmap`; complete resource cleanup remains
pending, separately from the passing metadata/peer rejection checks.

Recheck the new component from the Chipyard root with fresh paths:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration111-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration111-controller-rechecks/metadata-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_startup_metadata_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration111-controller-rechecks/startup-metadata
```

`ordinary-rocket-probe/summary.json` passes fresh ordinary RTL VCS readback of
318,637 pattern words / seven clocks before any edge; it remains a diagnostic,
not a captured CPU image or replay. Three complete CPU admission requests and
all 16 invalid host-audit options reject before CPU execution/publication.
`retained-iteration110-audit.json` verifies all 51,399 sealed prior artifacts.
Both iteration-110 controller commits are published, FireSim first then
Chipyard; queried remote tips match. Local tracking-ref refreshes failed on
read-only `.git`; no local staging or commits were performed.

Both exact-recipe default/buffered four-hart controls pass at **C=3,329,794** in
`rocket-controls/invocation-djtgi36h/summary.json`. Every complete hart trace
and every workload/store CPU print-cycle label matches the uninterrupted
reference. `rocket-build-identity.json` binds all 60 current native translation
units/dependencies and the exact six recipe settings above. The unchanged
workload is `runs/m11-iteration82/workload/rocket-quad.riscv`, 6,712 bytes,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
No FPGA bitstream was built.

`rocket-host-audit.json` passes all 64 component images at eight active host
samples, preserving separate master-credit and clock-token labels. These
samples do not certify semantic DUT edges or the required outstanding-memory
checkpoint cut. All eight full native suites pass in
`native-regressions/invocation-ryjuskkw/summary.json`, including 267 Python tests
and FCFS. The complete initialization suite passes 1,470 native commands.
All 11 retained host suites pass in `host-regression-results.json`. Fresh
initialization dispatch in `init-resume/invocation-liex5fv3/summary.json` passes
240 fresh restores and four first-divergence cases. The BCD suite retains 68
fresh restores / four first divergences; polling retains 72 fresh continuations /
four first divergences. These labels are host-service boundaries, not certified
CPU target cycles.

Exact native commands are retained in each invocation's `commands.json` and in
`raw-native-commands.json`; fresh executable rechecks are in
`verification-commands-native.json`. Final recovery records are `summary.json`,
`selected-results.json`, `native-input-archives.json`,
`independent-audit-results.json` and `artifact-manifest.json` under the run root.
`elf-loader-resource-diagnostic/summary.json` records the confirmed cleanup gap,
with its exact sanitizer build/run commands and the rejected relative-argument
pilot retained separately.

Remaining work includes exact full HTIF configuration/build/XLEN policy,
terminal/syscall/stop/signature/signal/context resources and atomic host
assembly; complete simulator/FAME/channel/memory/bridge ownership; coherent
required CPU cuts, fresh Level-1 continuation and independent captured Level-2
zero-edge readback/finite replay. Whole-CPU rejection and first-divergence
corruption tests remain pending. `remaining-host-owner-audit.json` records
source-bound pending host fields. BOOM/Saturn remain pending. No external tool,
license, netlist or library dependency is missing for this increment.

## Iteration 110: default BCD pending-command ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration110/`.
See [tsi-bcd.md](tsi-bcd.md) for the exact component boundary. Both CPU levels
remain **in_progress**; this adds a host device queue owner.

`bcd-current/invocation-yjvfpah0/summary.json` passes native sanitizer and
Y-2026.03-SP1 `-full64` VCS checks against the installed BCD implementation.
All 68 fresh restores read back every pending command before services or
contexts. All 64 continuation suffixes match the installed reference, including
12 continuations from actual TSI captures; identity memory writes and terminal
output bytes match. All 528 malformed images and four incompatible queue
configurations reject atomically, followed by valid readback. Twenty-two active
and interrupted-service guards pass. Four valid queue corruptions first diverge
at missing response `0x01000000000001ff`, host event **11**. These host-event
labels do not establish a CPU target-cycle boundary.

Both actual installed-FESVR source loaders complete their partial-write
read/merge, capture zero/one/two pending BCD commands at suspended polling cuts,
check both delayed-input serial fromhost writes and finish through HTIF PASS.
The new production queue owns ordered raw commands and reconstructs its response
sink from the destination polling owner. It serializes no source callbacks or
coroutine pointers. Terminal state remains external; the eight-component polling
inspection retains its original boundary. Complete CPU admission is disabled.

Commands are recorded in the selected BCD invocation's `commands.json`. Recheck
from the Chipyard root with fresh paths:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration110-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration110-controller-rechecks/bcd-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_bcd_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration110-controller-rechecks/bcd
```

The first BCD invocation finished native execution but failed audit because its
checker had an incorrect decimal constant for the 0xff response. The corrected
checker computes that value; the selected invocation reruns every native case
and additionally continues all actual production captures. The first full
regression invocation retains the checker-source change and is excluded from
current-source evidence. The fresh complete suite in
`native-regressions-current/invocation-rizi51yo/summary.json` passes all eight
checks, including 267 Python tests and FCFS. The complete initialization suite
passes all 1,470 commands. All 11 source-bound retained host suites pass;
results are in `host-regression-results.json`. Fresh dispatcher resumes pass all
240 restores, 7,012 complete readbacks, 5,112 atomic invalid images and four
first divergences in `init-resume/invocation-x2vflc9u/summary.json`. Initialization
retains 294 fixture continuations, 768 actual caller and 320 mixed-policy fresh
readbacks. Polling retains all 72 fresh continuations, 1,332 full readbacks,
38,744 atomic invalid checks and four first divergences. Actual polling retains
all 324 fresh component restores and 252 caller readbacks. Exact-ELF metadata
retains eight fresh readbacks, 56 unchanged peer images, 7,364 atomic invalid
cases and 14 incompatible/unsupported cases. These remain host-component tests.

Both exact-recipe default/buffered four-hart controls pass at **C=3,329,794** in
`rocket-controls/invocation-wwl99dud/summary.json`. Every complete hart instruction
trace and every workload/store CPU print-cycle label matches the uninterrupted
reference. `rocket-build-identity.json` binds the exact six recipe settings above,
all 60 native translation units and their actual dependencies, including the new
BCD header in both TSI and serial-bridge consumers. The unchanged workload is
`runs/m11-iteration82/workload/rocket-quad.riscv`, 6,712 bytes, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Its independently resolved mailboxes are `tohost=0x800003c0`,
`fromhost=0x80000400`. No FPGA bitstream was built.

`rocket-host-audit.json` verifies all 64 component images at eight active host
samples: master credits 520,064, 700,032, 900,096 and 3,250,048 in each mode.
Clock-token counts retain their separate one-token lead. These host credits do
not certify coherent semantic DUT edges or an outstanding-memory CPU cut.
The full ordinary RTL diagnostic in `ordinary-rocket-probe/` reads back all
318,637 words / seven clocks before edges; it remains a pattern diagnostic,
not a captured CPU image or replay. Three complete CPU admission requests and
all 16 malformed host-audit options still reject before CPU execution or
checkpoint publication. `retained-iteration109-audit.json` preserves all 45,237
previously sealed artifacts.

Exact native commands are retained in each invocation's `commands.json`, the
CPU control's build/runtime records and `raw-native-commands.json`; rechecks
with environment sourcing and fresh output paths are recorded in
`verification-commands-native.json`. Final recovery records are `summary.json`,
`selected-results.json`, `native-input-archives.json`,
`independent-audit-results.json` and `artifact-manifest.json` under the run root.
Both existing iteration-109 controller commits are published, FireSim first
then Chipyard, with queried remote tips matching. Local tracking-ref refreshes
failed on read-only `.git`. Both plans and protected inputs retain their bytes;
there is no staging or local commit.

Configuration/build/expected-XLEN binding, terminal and syscall resources,
HTIF stop/exit/signature/signal state, context replacement and atomic host
reconstruction remain pending. Complete simulator/FAME/channel/memory/bridge
ownership, coherent early/warm/outstanding-memory/late CPU cuts, fresh Level-1
continuation, independently captured Level-2 readback/replay and whole-CPU
rejection/first-divergence cases remain pending. BOOM/Saturn remain pending.

## Iteration 109: exact-ELF HTIF metadata preparation

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration109/`.
See [tsi-startup-metadata.md](tsi-startup-metadata.md) for the precise boundary.
Metadata preparation is a component operation; both complete CPU levels remain
**in_progress**.

`startup-metadata/invocation-0dk0d6t2/summary.json` passes native C++ and
Y-2026.03-SP1 `-full64` VCS checks linked to installed FESVR. Both actual source
loaders complete their partial-write read/merge, capture at a guarded polling cut
and finish through HTIF PASS/stop. All eight fresh sanitizer/VCS preparations
read back the entire metadata and 56 unchanged peer-component images before
services, contexts or edges. All 7,364 malformed byte-flip/truncation/extension
cases reject atomically, followed by valid preparation in the same fresh caller.
Fourteen changed-ELF/argument and unsupported-option cases reject without partial
publication. The image binds exact ELF bytes/arguments, entry and all symbols;
it reconstructs the installed private entry/mailboxes/symbol table without
startup target writes or reset. Library/build compatibility and aggregate host
ownership remain pending.

Native commands are recorded with environment sourcing and executable argv in
`startup-metadata/invocation-0dk0d6t2/commands.json`. Rechecks allocate fresh
invocations; the controller can run from the Chipyard root:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration109-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration109-controller-rechecks/metadata-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_startup_metadata_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration109-controller-rechecks/startup-metadata
```

The retained full native suite in
`native-regressions/invocation-86exlt3w/summary.json` passes all eight suites,
including 267 Python tests and FCFS. `retained-iteration108-audit.json` verifies
all 60,240 previously sealed artifacts with their original bytes preserved.
The fresh ordinary RTL pattern diagnostic in `ordinary-rocket-probe/` passes
all 318,637 semantic words / seven clocks before any edge; it remains a pattern
diagnostic rather than a captured CPU checkpoint/replay. All three complete CPU
admission requests and all 16 invalid host-audit options still reject before
CPU execution/publication.

Both complete exact-recipe default/buffered four-hart controls pass at
**C=3,329,794** in `rocket-controls/invocation-vhwno81s/summary.json`. Every
complete instruction trace and workload/store CPU print-cycle label matches the
uninterrupted reference. The native build identity binds all six recipe settings
listed above, all 60 translation units and their actual header dependencies.
The unchanged self-checking workload is
`runs/m11-iteration82/workload/rocket-quad.riscv`, 6,712 bytes, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
No bitstream was built. `rocket-host-audit.json` independently validates both
startup rejections and all 64 component images at the same eight active samples
(master credits 520,064, 700,032, 900,096 and 3,250,048 in each mode). Each has
79 serialized words, with the clock-token count recorded separately one ahead.
These credits still do not certify completed semantic target edges or an
outstanding-memory checkpoint cut.

All ten additional source-bound native/VCS host suites pass; their exact
commands/results are in `host-regression-results.json`. Retained polling passes
72 fresh continuations, 1,332 complete readbacks, 38,744 atomic invalid images,
eight fresh invalid images and four first divergences. Actual installed polling
passes all 324 fresh component restores / 252 polling readbacks, 1,008
independently expected component images and 54 cross-owner rejections. Actual
BCD/fromhost checks retain all 20 fresh caller readbacks; installed option
routing passes all 18 cases. Actual installed active syscall/memif checks still
reject pending and partial 64-byte reads and inspect all eight owners after the
service returns. Full initialization retention passes 294 fixture continuations,
768 actual caller and 320 mixed-policy readbacks. Fresh initialization dispatch
passes 240 restores, 7,012 complete readbacks, 5,112 atomic invalid images and
four first divergences. These are host-component checks, not CPU continuation.

Existing iteration-108 controller commits are published FireSim first, then
Chipyard; independent remote tips match. Read-only `.git` prevented local
tracking-ref refreshes after the successful remote updates. Protected plan,
environment, PDF and Conda inputs retain their original bytes. No staging,
local commits or history cleanup occurred.

Recovery records are `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json` and
`artifact-manifest.json`. Final audits bind complete readbacks, current native
sources/dependencies, all preserved artifacts and the unsupported CPU admission
guards. Both complete CPU levels remain in progress. Next: configuration/build
and expected-XLEN ownership, default devices/stop/signature/signal/context and
atomic cross-owner reconstruction, then coherent required CPU cuts and fresh
Level-1 continuation plus independently captured Level-2 zero-edge readback/
finite replay. Whole-CPU image rejection and first-divergence cases remain
pending; no external dependency is missing.

## Iteration 108: suspended polling cut audit

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration108/`.
See [tsi-polling-cut-audit.md](tsi-polling-cut-audit.md) for the exact eight-owner
boundary and production guards. All final selected native checks pass. This
increment inspects production state; complete HTIF/TSI restore and both CPU
checkpoint levels remain **in_progress**.

`inspect_polling_cut()` requires returned startup, complete loading and
initialization, empty load-memory state and an externally suspended host. It
cross-checks the polling caller against its partial serial-read or idle child,
validates all eight images and checks repeat-read stability. The bridge exposes
this optional diagnostic without changing aggregate checkpoint admission.

Both complete exact-recipe default/buffered four-hart controls pass at target
count **3,329,794** in `rocket-controls/invocation-ieqwwfrh/summary.json`.
Every complete instruction trace and workload/store CPU print-cycle label
matches the independent uninterrupted reference. The exact six recipe settings
above, all 60 native translation units and actual compiler header dependencies
are bound by `rocket-build-identity.json`. No bitstream was built. The unchanged
6,712-byte workload ELF is `runs/m11-iteration82/workload/rocket-quad.riscv`,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Its independently resolved mailboxes are `tohost=0x800003c0` and
`fromhost=0x80000400`.

Both actual CPU runs record these host inspections in
`rocket-runtime/tsi-host-audit/` and `rocket-buffered-runtime/tsi-host-audit/`:

| Requested master credit | Clock tokens enqueued | Host inspection in both modes |
| --- | --- | --- |
| 0 | 0 | startup not returned; explicit rejection, no component images |
| 520,064 | 520,065 | idle; eight complete component images |
| 700,032 | 700,033 | blocked tohost read; eight complete component images |
| 900,096 | 900,097 | blocked tohost read; eight complete component images |
| 3,250,048 | 3,250,049 | idle; eight complete component images |

`rocket-host-audit.json` independently checks all ten records and all 64 active
component images against the workload symbols and exact configurations. Each
active record has 79 serialized 64-bit words including configuration/header
words. This proves startup frames have returned at those samples. These labels
are distinct from completed semantic target edges and CPU print-cycle labels.
The memory-loop sample does not independently prove outstanding target memory;
coherent CPU checkpoint cuts and continuation/replay remain pending.

`current/active-service/invocation-1dlpa321/summary.json` passes actual installed
syscall/memif integration in native C++ and VCS. A real 64-byte syscall read
blocks before data and after one word; both cuts reject. After installed
`sys_exit` returns, all eight components become inspectable; response queuing,
fromhost publication and termination complete. Across both backends this gives
four active-service rejections, ten startup/termination rejections and 32
complete returned component images. Private device/context state is not restored.

`current/actual-poll/invocation-09a8u8xu/summary.json` passes all 324 fresh
component restores, including 252 polling-caller readbacks. Inspection at 126
actual suspended polling/partial-read/idle cuts yields 1,008 complete component
images with independently expected bytes. All 54 component-valid cross-owner
corruptions reject without changing peers. BCD/fromhost integration in
`actual-response/invocation-grnb1fz_/summary.json` retains all 20 fresh caller
readbacks and independently checks all 64 inspected peer images. None of these
host component tests establishes a CPU checkpoint.

`htif-poll/` retains all 72 fresh sanitizer/VCS caller continuations, 1,332 complete
readbacks, 38,744 atomic invalid-image checks, eight fresh invalid images and four
first divergences. The full initialization retention suite passes 294 fixture
continuations, all 768 actual caller and 320 mixed-policy readbacks. The fresh
initialization dispatcher passes all 240 restores, 7,012 complete peer readbacks,
5,112 atomic invalid images and four first divergences. The final source-bound
`current/native-regressions/invocation-089ltlrq/summary.json` passes all eight
suites, including 267 Python tests and FCFS. All 18 installed option-routing
cases pass in `current/htif-options/`.

Three complete CPU preflight/capture/restore requests still reject before CPU
execution/publication. All 16 malformed/duplicate/missing audit-option and
existing-directory cases reject without publication. The fresh ordinary RTL
pattern probe reads back all 318,637 words / seven clocks before any edge. It
remains a diagnostic, not a captured CPU image or captured trace replay.

One concurrent VCS build collided with another build's timestamp/PID temporary
directory. The failed log remains under `real-loader/`; the successful rerun is
`current/real-loader/invocation-fn0qobkp/summary.json`. Follow-up builds inherit
separate TMPDIR directories under this run. A wrong-directory ordinary-probe
launcher, a wrong-parent-summary polling launcher and an initial linkage audit
that omitted C++ ABI symbol tags are retained separately from their corrected
successful runs. No check was removed. Earlier source-bound
runs remain diagnostics; `selected-results.json` identifies the final evidence.

Existing iteration-107 controller commits are published FireSim first, then
Chipyard; independently queried remote tips match. Local tracking-ref refreshes
failed on read-only `.git` after successful remote pushes. Neither plan,
environment setup, PDF nor dirty Conda input was edited; no staging or local
commits occurred.

Recovery: `summary.json`, `selected-results.json`, `rocket-host-audit.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json` and complete
`artifact-manifest.json`. Commands run from the Chipyard root. Fresh rechecks
allocate new destinations outside the sealed iteration; use separate TMPDIRs
when launching VCS builds from separate sandbox shells:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration108-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration108-controller-rechecks/active-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_cut_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration108-controller-rechecks/active-service
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration108-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration108/rocket-controls/invocation-ieqwwfrh/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

Complete configuration-specific simulator/FAME/channel/memory/bridge ownership,
HTIF metadata/device/stop/signature/context reconstruction and atomic CPU images,
coherent required active cuts, fresh Level-1 continuation, independently captured
Level-2 readback/replay and whole-CPU invalid-image/first-divergence cases remain
pending. BOOM/Saturn remain pending; no external dependency is missing.

## Iteration 107: production HTIF polling caller

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration107/`.
See [tsi-htif-poll.md](tsi-htif-poll.md) for the exact state boundary, production
dispatch and unsupported owners. The default-device production caller now owns
all nine polling phases, the pending command and ordered fromhost responses.
Review reproduced FESVR's abbreviated long-option routing in `options-pilot/`.
All long options now retain the installed HTIF loop, including abbreviations;
the new native/VCS option suite passes all 18 real installed-FESVR cases. Final source-bound checks are under `current/`; all corrected native checks and
both complete four-hart controls pass. Earlier source-bound runs remain separate
retained diagnostics.
Serial reads and idle yields return through their existing owners. Installed
startup/ELF/memif, private HTIF metadata, device internals, stop/signature and
context reconstruction remain pending. Complete CPU checkpoint requests remain
unsupported; these component checks cannot establish either CPU level.
Whole-CPU image admission and first-divergence cases at the required active cuts
remain pending alongside continuation and independent captured RTL replay.

`htif-poll/invocation-qkszzkjk/summary.json` passes 72 fresh native ASan/UBSan and
VCS caller continuations: 1,332 complete state readbacks, 38,744 atomic invalid-
image checks, eight fresh malformed/incompatible/incomplete image rejections and
four first divergences. The two valid-image command/response corruptions first differ
at component operation 0 (`tohost_command` and `write_data`) without acknowledging
that operation. These fixture labels are not Rocket target-cycle labels.
`current/real-loader/invocation-8f3k4bk4/summary.json` retains actual installed-FESVR ELF
read/merge/reset/idle checks. Fresh program-loader readbacks pass all 28 cases and
7,072 atomic invalid images per process.

`current/actual-response/invocation-ylajuuoz/summary.json` passes the installed-FESVR BCD
callback/fromhost route in native C++ and VCS. Each source consumes exactly one
deterministic input byte, retains `0x0100000000000141` across pending/partial
fromhost reads, writes it once and then handles the installed pass command.
All 40 complete caller/serial-read/FIFO/host-control peer images match independent
bytes. All 20 fresh native ASan/UBSan/VCS caller readbacks pass before services,
context entry or target edges. This does not restore the device or terminal.

`current/host-control/invocation-1bylj7_y/summary.json` passes all 362 fixture continuations,
7,866 complete readbacks and 136 real FESVR component readbacks. The unchanged
initialization dispatcher passes 240 fresh restores, 7,012 complete peer readbacks,
5,112 atomic invalid images and four first divergences in
`current/init-resume/invocation-yj592grc/summary.json`. All eight preserved native suites,
including 267 Python tests and FCFS, pass in
`current/native-regressions/invocation-h2edvc3m/summary.json`.
`current/actual-poll/invocation-sbahu7eu/summary.json` passes all 324 fresh component
restores, including 252 complete polling-caller readbacks of first-poll,
partial-read and idle states at all three idle-count policies. These valid peer
readbacks do not implement a complete atomic TSI restore bundle. The full initialization
retention suite also passes in `current/init-regression/invocation-m9aandn0/summary.json`: all 294 fixture continuations,
7,264 complete readbacks, 60 fresh invalid cases and four first divergences,
plus all 768 actual caller and 320 mixed cache-flush/MSIP fresh readbacks.

`current/rocket-controls/invocation-uknm8doa/summary.json` passes both complete
default and buffered four-hart controls at C=3,329,794. Every complete trace and
workload/store cycle label matches the independent uninterrupted reference.
The exact six recipe settings above and the unchanged 6,712-byte workload are
bound by `rocket-build-identity.json`: ELF
`runs/m11-iteration82/workload/rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These are uninterrupted CPU controls, not checkpoint continuations.

`current/htif-options/invocation-w9al62gy/summary.json` passes all 18 native/VCS
option cases, including all long chroot prefixes, the plusarg form and a long
metadata option. `options-pilot/` preserves the pre-correction failure. All
corrected native command logs, original input snapshots and independently audited
results remain source-bound. Independent restore batches run four workers, with
locked command records and complete sibling failure retention; all four runner
tests pass. No state image, process, negative case or comparison was removed.

The fresh ordinary Rocket diagnostic reads back all 318,637 words / seven clocks
before any edge. It deposits diagnostic patterns, not independently captured CPU
state. `current/rocket-poll-linkage.json` binds all 60 native translation units, the
production host dispatcher, the poll owner vtable/virtual checkpoint methods and
both TSI/bridge header consumers. Generated RTL, inventory, reference and constants
match iteration 106. The linkage pilot's out-of-line `advance()` symbol check
failed because the optimizer inlined it; its separate diagnostic is retained.
The generated inventory remains 2,292 instances, 11,464 state entries and 445,838
words. This is a storage inventory, not proof of complete runtime ownership.

Existing iteration-106 controller commits are published FireSim first, then
Chipyard. Both remote tips match. The local tracking-ref refreshes failed on
read-only `.git` after the successful remote pushes. No staging, local commits,
protected plan/environment/Conda edits or history cleanup occurred.

Native commands run from the Chipyard root. Fresh rechecks allocate new
invocations outside the sealed iteration; the exact raw VCS compiler/runtime
argv, source hashes, images, readbacks and results remain in each summary and
the run's `raw-native-commands.json`.

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_htif_poll_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks/htif-poll
python -m tools.checkpoint_formats.tests.verify_tsi_htif_response_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks/actual-response
python -m tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks/actual-poll \
  --component-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration107/current/host-control/invocation-1bylj7_y/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration107/current/rocket-controls/invocation-uknm8doa/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

The ordinary RTL storage diagnostic can be repeated with a fresh working
directory, preserving its independent pre-FAME boundary and all prior logs:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks
checkpoint_probe_dir=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks/ordinary-rocket-probe.XXXXXX")
(cd "$checkpoint_probe_dir" && \
 /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/simv \
 -no_save +vcs+initreg+0 +vcs+initmem+0 \
 +pattern=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/complete-pattern.txt \
 +baseline=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/initial-baseline.txt \
 > run.log 2>&1)
```

`summary.json`, `selected-results.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json` and
`artifact-manifest.json` provide recovery and complete diagnostic membership.
`remaining-host-owners.json` and [tsi-htif-poll.md](tsi-htif-poll.md) record the
pending owner audit and proposed next boundary. BOOM/Saturn remain pending;
no external dependency is missing.

## Iteration 106: production program-load phase and routing

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration106/`.
See [tsi-program-loader.md](tsi-program-loader.md) for exact ownership, schema
and production callers. Both CPU levels remain **in_progress**. The complete
HTIF/ELF/memif/device/context owners and cross-owner cut coherence, required
active CPU cuts, fresh Level-1 continuation and independently captured Level-2
readback/replay remain pending. No complete CPU checkpoint profile is enabled.

`real-loader/invocation-bx_ympkl/summary.json` passes actual installed-FESVR ELF loading in native
C++ and VCS, retaining exact request/partial-read/merge/reset/idle checks and
capturing seven suspended loader phases per backend. Independently expected phase
words are `0,1,2,2,2,3,3`. `program-loader/invocation-ryw_falz/summary.json` passes all 28 fresh
complete component readbacks, all four capability/cache-flush policies and four
phases, 7,072 atomic invalid-image cases per process, illegal-transition/poison
guards and two first-divergence phase-corruption cases at component operation 0.
These component labels are not Rocket target cycles. The 56-byte kind-23 image
owns program-load transport selection and entry/return, not ELF/memif caller
buffers or HTIF continuation. The existing four-owner initialization bundle is
unchanged; this increment does not reconstruct its complete host context.

`init-regression/invocation-bim6nr36/summary.json` passes 294 fixture continuations, 7,264 complete
readbacks, 60 fresh invalid cases and four first divergences; all 384 actual
caller images restore in 768 fresh processes, and all 160 mixed cache-flush/MSIP
captures restore in 320 fresh processes. `init-resume/invocation-pyjvrue0/summary.json` passes
240 fresh actual dispatches, 7,012 complete four-owner readbacks, 6,772 continued
operations, 5,112 atomic invalid-image cases and four first divergences.
`native-regressions/invocation-mp9b4hk7/summary.json` passes all eight preserved suites, including
263 Python tests and the full FCFS checks. These retain their component/fixture
scope and cannot establish complete CPU checkpoint support.

`rocket-controls/invocation-zsejlhrh/summary.json` passes both full default/buffered uninterrupted
four-hart controls at target C=3,329,794. Every full instruction trace and workload/
store label matches the independent uninterrupted reference. The unchanged
6,712-byte ELF is `runs/m11-iteration82/workload/rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The exact six recipe settings above are retained. `rocket-loader-linkage.json`
binds all 60 native translation units, the new production routing/owner symbols
and the header in both TSI/bridge consumers. Generated RTL, inventory, reference
and constant-header hashes match iteration 105. Native builds/runs use VCS
Y-2026.03-SP1, `-full64`, GCC/G++ 13 and the required environment sourcing order.

Eight final and 28 retained independent audits pass. The fresh ordinary Rocket
VCS diagnostic in `ordinary-rocket-probe/summary.json` reads back all 318,637
words / seven clocks before any edge; its deposited pattern is not captured CPU
state. `cpu-request-rejections/summary.json` retains all three complete-CPU
preflight/capture/restore rejections before execution/publication. The prefix
checker pilot failed because buffered sinks publish their retained bytes at
completion; its diagnostic remains separate from the passing default-prefix
check and both full final comparisons. No check was omitted to pass verification.

`summary.json`, `selected-results.json`, `executed-native-commands.json`,
`verification-commands-native.json` and `native-input-archives.json` retain exact
native commands, selected results and original source bytes. The full
`artifact-manifest.json` enumerates every diagnostic file and dangling-link target;
`changed-source-artifacts.json` binds implementation/documentation files.
Protected plan/environment/Conda/index/HEAD checks are separate turn-local guards.
No external dependency is missing. Existing iteration-105 controller commits are
published FireSim first, then Chipyard. `github-publication.json` records matching
remote tips and local tracking-ref refresh failures on read-only `.git` after
successful remote pushes. The controller owns staging/new checkpoint commits.

Fresh native rechecks write outside the sealed iteration. Run from Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration106-controller-rechecks/real-loader
python -m tools.checkpoint_formats.tests.verify_tsi_program_loader_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration106-controller-rechecks/program-loader \
  --integration-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration106/real-loader/invocation-bx_ympkl/summary.json
python -m tools.checkpoint_formats.tests.verify_tsi_init_resume_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration106-controller-rechecks/init-resume \
  --init-summary automations/checkpoint_loop/runs/m11-iteration104/init/invocation-tvmgxkbu/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration106-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration105/rocket-controls/invocation-2pjhmxlf/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

The complete initialization/native-regression and fresh ordinary RTL commands,
with cwd and argv arrays, are in `verification-commands-native.json`. The latter
runs the audited ordinary RTL `simv` with `-no_save`, `+vcs+initreg+0`,
`+vcs+initmem+0`, `+pattern=.../complete-pattern.txt` and
`+baseline=.../initial-baseline.txt` from a fresh diagnostic directory after
sourcing both environments and `vcs-env.sh` last. This is a storage diagnostic;
CPU zero-edge readback/replay still requires an actual independent capture.

## Iteration 105: fresh production initialization dispatch

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration105/`.
See [tsi-init-resume.md](tsi-init-resume.md) for exact ownership, supported
boundaries and atomic restore. Both CPU levels remain **in_progress**. Complete
HTIF/memif/device/TestChip loader/context ownership and cross-owner coherence,
all required early/warmed-cache/outstanding-memory/late CPU checkpoint cuts,
fresh Level-1 continuation and independently captured Level-2 replay remain pending.

The production `advance_initialization()` dispatcher resumes the caller and
serial-read child from owned phases without repeating a request or cache flush.
Its kind-22 component bundle binds the effective cache-flush address and the
complete host-control, ordered initialization, serial-read and serial-FIFO
images. Child configurations bind idle count, the entire ordered access list
and MSIP policy. Four private candidates pass complete parsing/configuration and
supported phase checks before four allocation-free state swaps commit. Restore
advances no service, host context or target edge. HTIF entry after component
restore rejects explicitly; no complete TSI/CPU checkpoint profile is enabled.

`init-resume/invocation-_rqnva1j/summary.json` passes 240 fresh actual dispatches in
native ASan/UBSan and native VCS processes, 7,012 complete four-owner
readbacks and 6,772 continued operations. Both old native and VCS actual
TestChip producers supply the images. Both destination backends test reset-wait,
queued/partly consumed requests, empty waits and queued responses for both
initialization reads, with cache flushing and MSIP independently on/off. All
5,112 malformed/incompatible/missing/reordered/incoherent component image
checks reject atomically. Four repeated fresh packet-corruption runs detect
`POP expected=1 actual=0` at fixture operation 1 / C=101 before acknowledgement.
Fixture operation labels are not CPU target cycles. `guards-summary.json`
retains native sanitizer/VCS unstarted-caller, HTIF-entry, atomic failed replacement
and repeated complete readback checks.

The original initialization regression passes in `init-regression/invocation-zk0my5ho/summary.json`:
294 fixture continuations, 7,264 complete readbacks,
6,970 continuation records, 60 fresh atomic invalid cases and
four first divergences. All 384 original actual caller images restore in
768 fresh processes; all 160 mixed cache-flush/MSIP captures restore
in 320 fresh processes. These remain component results.
All eight preserved native regression suites, including 263 Python tests and full
FCFS checks, pass in `native-regressions/invocation-zqng441k/summary.json`.

Both complete default/buffered Rocket controls pass in `rocket-controls/invocation-2pjhmxlf/summary.json`
at target C=3,329,794. Every full trace for all four harts and every workload/store
label matches the uninterrupted reference. The unchanged 6,712-byte workload is
`runs/m11-iteration82/workload/rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
`rocket-init-dispatch-linkage.json` binds the new production symbols and exact
header dependencies in both driver/bridge consumers. All 60 translation units
remain; generated RTL, reference, inventory and constant-header hashes match
iteration 104. These controls exercise the exact six recipe settings listed above.

All 32 final/retained audits pass. They include the full unchanged old artifact
catalog after all runs, original memory/clock/replay/TracerV inventories and a
fresh ordinary Rocket RTL 318,637-word/seven-clock diagnostic readback before
edges. That diagnostic uses a pattern, not captured CPU execution state.
`cpu-request-rejections/summary.json` records current complete-CPU preflight
rejection at TSI widget/12 and public capture/restore rejection before target
execution/publication. The first sanitizer pilot is separate: installed FESVR
context initialization allocated a retained 1 MiB stack. Lazy initialization at
first host service lets fresh component dispatch avoid creating that coroutine;
leak checking and installed FESVR bytes remain unchanged.

`selected-results.json`, `native-input-archives.json`,
`executed-native-commands.json` and `verification-commands-native.json` retain
exact results, original source bytes and executable native commands. The full
`artifact-manifest.json` binds every created diagnostic byte and dangling-link
target; `changed-source-artifacts.json` binds all implementation/documentation
files. Protected plan/environment/Conda/index/HEAD checks are recorded separately
in `implementation-turn-guard.json`. Existing iteration-104 commits are published
FireSim first, then Chipyard, with matching tips in `github-publication.json`.
The controller owns new staging and local checkpoint commits.

Fresh rechecks write outside the sealed iteration. Run from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_init_resume_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration105-controller-rechecks/init-resume \
  --init-summary automations/checkpoint_loop/runs/m11-iteration104/init/invocation-tvmgxkbu/summary.json
python -m tools.checkpoint_formats.tests.verify_tsi_init_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration105-controller-rechecks/init-regression \
  --serial-summary automations/checkpoint_loop/runs/m11-iteration103/serial-final/invocation-_z6k6wcy/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration105-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration104/rocket-controls/invocation-3e_6lfkl/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

Every nested native VCS build/run shell independently sources both environments
and `vcs-env.sh` last. The JSON command catalog also supplies the full eight-check
native regression and fresh ordinary Rocket RTL VCS probe. VCS remains
Y-2026.03-SP1 `-full64`, GCC/G++ 13 and `-Mupdate` on reused Make builds. All four
required actual CPU checkpoint cuts and both complete restored levels remain
pending. BOOM/Saturn, physical FPGA validation and ASIC power are unchanged.

## Iteration 104: durable complete artifact verification

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration104/`.
The previous verification failed on raw `.git/index` equality. Git cache refreshes
and authorized controller commits can change index bytes; the log does not
identify the exact cache writer. Index/HEAD invariance is a turn-local guard,
not a durable evidence invariant. The durable verifier validates permitted linear controller ancestry,
original protected file bytes, unstaged plans, archived native inputs and every
cataloged diagnostic byte. Source evolution requires original committed bytes
in that history. No source fallback is allowed for captured state, traces,
binaries or logs under `runs/`.

The original iteration-103 seal is unchanged, SHA-256
`08431527f96df89f7a75cb8a900775a1e5ce3d16ef75b45a829d4dd6b353f77d`.
It catalogs 142,367 files / 9,085,529,263 bytes. Fourteen dangling VCS cache links
were absent from its regular-file walk. Their paths and targets are separately
bound in `iteration103-dangling-links.json`, SHA-256
`eaec6ca08508c308a90bd8d6c13530e0be6f6bdbc1ddc047b7dc48d7cea4aebf`.
The audit requires exact combined membership and rejects new links, changed
targets, corrupt/missing/extra files and mismatched seals. The supplemental
catalog records present dangling-link metadata; the old seal made no historical
claim about those link targets. New seals bind such links directly.

All 18 new verifier tests pass. They create disposable Git repositories to test
post-turn controller commits, source provenance, rewritten/unexpected histories,
plan exclusion and diagnostic corruption. These are evidence-verifier tests,
not CPU checkpoint acceptance.

The full catalog/protected-input check passes in `retained-final-19.log`.
All 19 retained native audits pass, and a fresh ordinary Rocket RTL diagnostic
probe matches all 318,637 words / seven clocks before edges in
`retained-final-20.log`. All eight frozen-source native regressions pass in
`native-regressions-final/invocation-tjsmc73w/summary.json`, including all 263
Python tests and complete preserved FCFS checks. The preliminary regression
attempt ran all eight checks but its source-stability guard correctly rejected
the earlier verifier version; it remains separate in `native-regressions/`.
The initial strict catalog rejection for previously unlisted dangling links
also remains separate in `retained-19.log`; neither failure is selected as a
passing result.

The exact recipe rebuilt with all 60 native translation units and both complete
four-hart controls pass in `rocket-controls/invocation-3e_6lfkl/summary.json`.
Default and buffered runs finish at target C=3,329,794; every complete instruction
trace and workload/store label matches the independent uninterrupted reference.
The workload remains the original 6,712-byte `rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These runs establish uninterrupted controls, not fresh CPU checkpoint restores.

The full initialization component suite passes in
`init/invocation-tvmgxkbu/summary.json`: 294 fresh fixture continuations, 7,264
complete readbacks, 6,970 continuation records, 7,766 atomic/phase/interruption
checks per backend, 60 fresh atomic invalid-image rejections and four first
divergences at fixture C=102/C=105 with no failed operation acknowledged. All
384 actual caller images restore in 768 fresh processes, and all 160 mixed
cache-flush/MSIP images restore in 320 fresh processes before edges/services.
These restore caller components; fresh HTIF/child/context/CPU dispatch remains
unsupported. No complete CPU checkpoint profile is enabled.

`selected-results.json`, `native-input-archives.json`,
`executed-native-commands.json` and `verification-commands-native.json` retain
the selected native results, original input snapshots and executable commands.
The latter includes full native VCS builds/runs and a fresh ordinary Rocket RTL
probe, sourcing both environments and `vcs-env.sh` last. Recheck destinations
are outside the sealed iteration, so later verification preserves its membership.
`artifact-manifest.json` binds every created diagnostic file plus dangling-link
targets; `implementation-turn-guard.json` records the separate index/HEAD/input
checks before the controller's next commit. The implementation created no local
repository checkpoint commit and staged no plan. Existing iteration-103 commits
were published FireSim first, then Chipyard; remote tips and submodule pointer
match in `github-publication.json`.

Run the complete old catalog check from the Chipyard root with:

```sh
python -m tools.checkpoint_formats.run_artifacts \
  --manifest automations/checkpoint_loop/runs/m11-iteration103/artifact-manifest.json \
  --manifest-sha256 08431527f96df89f7a75cb8a900775a1e5ce3d16ef75b45a829d4dd6b353f77d \
  --dangling-links automations/checkpoint_loop/runs/m11-iteration104/iteration103-dangling-links.json \
  --dangling-links-sha256 eaec6ca08508c308a90bd8d6c13530e0be6f6bdbc1ddc047b7dc48d7cea4aebf
```

Native build/simulation commands and results are recorded under this iteration's
diagnostic root. Both Rocket levels remain in_progress: complete HTIF/context/
child-caller and cross-owner ownership, required early/warm/outstanding/late CPU
cuts, fresh-process Level-1 continuation and independently captured Level-2 CPU
replay remain pending. No external dependency is missing.

## Iteration 103: production TestChip initialization caller

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration103/`.
See [tsi-init-accesses.md](tsi-init-accesses.md). Both Rocket levels remain
in_progress; CPU early/warmed/outstanding-memory/late checkpoint cuts and
independent captured CPU RTL replay remain pending.

`firesim.tsi.init-accesses.v1` binds the full ordered initialization access list
and hart-0 MSIP policy. It owns the current access index, before/after child
phase and persistent read/result/write/MSIP buffer. Production reset uses these
buffers through the original TestChip virtual read/write and cache-flush paths.
Original packet order, MSIP behavior, empty-response yields and stderr results
are preserved. Complete image validation precedes a fixed-size, service-free
restore. Suspended child/context/caller dispatch remains unsupported; no complete
TSI or CPU profile is enabled.

The exact recipe controls pass in
`rocket-controls-final/invocation-u1tbio70/summary.json`. Both complete four-hart
default/buffered runs finish at C=3,329,794. Every full instruction trace and
workload/store label matches the independent uninterrupted reference. The workload
is the original 6,712-byte `runs/m11-iteration82/workload/rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These are uninterrupted CPU controls. `rocket-init-linkage-audit.json` binds the
new owner's actual native save/validate/load symbols and both driver/bridge
header dependencies. All 60 translation units, generated RTL/reference/manifest/
constants, installed FESVR archive and exact recipe settings are retained.

All 245 Python tests and eight preserved native regressions pass in
`native-regressions/invocation-p1knl8_q/summary.json`. Prior load-memory read/queue,
actual loader, bridge/host control, actual HTIF child/poll, transport and all four
transport-fault checks pass. Four retained state/clock/replay/memory-policy/TracerV
audits and a fresh ordinary Rocket RTL diagnostic zero-edge probe pass. Complete
CPU preflight still rejects TSI widget/12; public capture/restore reject unavailable
durable runtime support before execution or publication. These rejections do not
establish CPU image-loader acceptance.

The source-stable serial suite passes in
`serial-final/invocation-_z6k6wcy/summary.json`: 78 fresh fixture continuations,
1,560 full readbacks, 1,482 records, 40 atomic invalid cases and four first
component divergences; 384 actual HTIF FIFO images restore in 768 fresh processes.
The initialization suite passes in `init/invocation-kyjownt8/summary.json`:
294 fresh fixture continuations, 7,264 full readbacks, 6,970 records and 7,766
atomic/phase/interruption checks per backend. All 60 malformed/incompatible/
missing-owner cases reject before mutation. Valid cursor/result corruption
first differs at fixture C=102/operation 2 and C=105/operation 5, respectively,
in both backends with zero failed operations acknowledged. These are component
operation labels. All 384 actual HTIF caller captures restore in 768 fresh
processes before operations, edges or services. Eight real installed-HTIF runs
exercise mixed TestChip reads/writes with cache flushing and MSIP independently
on/off. Every serial packet word and all four complete init/read/FIFO/host-control
owner images match independent expected bytes at 160 selected host cuts. All
160 caller images additionally restore in 320 fresh sanitizer/VCS processes.
The fresh deposits restore the caller component; they do not reconstruct or
resume its HTIF/serial/cache-flush children.

The preserved read suite passes in `serial-read/invocation-r916gusa/summary.json`:
522 fresh fixture continuations, 71,828 complete read/FIFO readbacks, 35,392
records, 50 atomic invalid cases, four first-divergence cases and 768 fresh
complete actual HTIF read/FIFO pair restores. Host-control passes 362 fixture
continuations and 136 actual loader readbacks in
`host-control/invocation-0tegfw5n/summary.json`; actual child/poll checks retain
162 images/324 fresh readbacks in `host-fesvr/invocation-uen9jmrs/summary.json`.
The actual bridge suite retains all 48 fresh readbacks in
`actual-bridge-restores/invocation-_7u0_8qo/summary.json`. Complete CPU request
rejections are in `cpu-request-rejections/summary.json`. Retained audits and the
fresh ordinary RTL probe commands/results are in `retained-audit-results.json`.

All 19 independent final audits pass. `selected-results.json`,
`native-input-archives.json`, `executed-native-commands.json` and
`verification-commands-native.json` retain exact selections, 950 original input
bindings and 5,706 native command records. The eight-check regression summary
retains every original native artifact and source snapshot. Initial standalone
include and two source-stability failures remain separate diagnostic evidence;
only final frozen-source suites are selected. Existing iteration-102 controller
commits were published FireSim first, then Chipyard; independent remote tips
and the submodule pointer match (`github-publication.json`). No staging or local
commits were performed. No protected input or installed library was changed.

The actual native initialization command is retained in `init-command.json`.
Run its complete VCS/sanitizer check from the Chipyard root with:

```sh
source env.sh && source sims/firesim/env.sh
checkpoint_m11_init_tmp=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration103/recheck-init-XXXXXX")
export TMPDIR="$checkpoint_m11_init_tmp"
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_init_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration103/controller-init-recheck \
  --serial-summary automations/checkpoint_loop/runs/m11-iteration103/serial-final/invocation-_z6k6wcy/summary.json
```

Fresh component caller readbacks do not resume HTIF or a CPU. Full HTIF/memif/
device/stop/signature and TestChip loader/cache-flush child progress, fresh
caller/context reconstruction and cross-owner coherence remain necessary before
active CPU checkpoint cuts and independently restored Level 1 and Level 2.
No external dependency is missing. BOOM and Saturn remain pending.

## Iteration 102: production serial read progress

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration102/`.
See [tsi-serial-read.md](tsi-serial-read.md), including the explicit remaining
HTIF/memif/device/TestChip caller ownership audit. Complete Rocket Level-1 and
Level-2 acceptance remain in_progress. No coherent CPU checkpoint continuation
or captured CPU RTL replay has passed.

`firesim.tsi.serial-read.v1` owns the original serial read address, byte length,
issue/response/complete phase, collected response count and every collected
32-bit word. The FIFOs retain their separate complete owner. Production reads
issue the original packet once, consume responses in order, and switch to the
target only when the response FIFO is empty. Result storage is reserved before
issue/load, and complete configuration/phase/count/width validation precedes
owner mutation. Restore executes no services, context switch or target edge.
The HTIF destination/caller and context reconstruction remain unsupported.
No complete CPU/TSI checkpoint profile is enabled.

Serial-read verification passes in
`serial-read/invocation-avekamwh/summary.json`: 522 fresh fixture continuations,
71,828 complete read/FIFO readbacks, 35,392 continued records and 581 atomic/
interruption checks per backend. All 50 fresh malformed/incompatible/missing
read or FIFO cases reject before mutation. Valid address and collected-word
corruption first differ at fixture C=103/operation 3 and C=115/operation 15 in
both backends, with zero failed operations acknowledged.
The independent Python oracle covers 4/8/64/128/1024-byte reads, pre-issue,
partly transmitted packets, waiting/partial responses, completion, extra queued
responses and a second read. Native sanitizer and VCS DPI checks restore both
complete owners in fresh processes before any operation, compare every resumed
operation/state image, reject malformed/incompatible/missing owners atomically,
and detect valid address/collected-word corruption at its first unacknowledged
boundary. Fixture operation labels are not Rocket target cycles.

The preserved FIFO suite passes in `serial/invocation-hrgwtspy/summary.json`:
78 fresh fixture continuations, 1,560 complete readbacks, 1,482 continued records,
40 fresh invalid cases and four first-divergence cases. All 384 real installed-
HTIF serial images restore in 768 fresh processes. This checker now also retains
complete read-owner captures alongside every actual TestChip init/poll/idle
serial image; all 384 read/FIFO pairs additionally restore in 768 fresh
sanitizer/VCS processes with complete zero-edge/no-service readback. These host-protocol cuts
do not restore HTIF or a CPU.

Exact recipe controls pass in
`rocket-controls/invocation-6yxavjbu/summary.json`, with independent native linkage
and dependency evidence in `rocket-read-complete-linkage-audit.json`. The owned
implementation and all three TestChip/FireSim/bridge consumers bind the new
read header in their actual compiler dependencies. The exact settings,
all 60 native units, generated RTL/reference/manifests/constants and installed
FESVR archive remain unchanged. Both complete four-hart default/buffered runs
pass at C=3,329,794; all full instruction traces and workload/store labels match
the uninterrupted reference. Workload is the original 6,712-byte
`runs/m11-iteration82/workload/rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These are controls, not restored CPU workloads or tested CPU checkpoint cuts.

All 245 Python tests and eight preserved native regressions pass in
`native-regressions/invocation-hupf6h08/summary.json`, retaining 5,131 artifacts /
713 original source bindings. Load-memory read/queue/ELF-loader, bridge-control,
transport and all four transport-fault suites pass. Host-control passes all
362 fixture continuations plus 136 actual loader readbacks (`host-control/invocation-dqnxed88/summary.json`). Actual child/poll
checks pass 162 images / 324 fresh readbacks
(`host-fesvr/invocation-lrceiw09/summary.json`); all 48 actual bridge restores pass
(`actual-bridge-restores/invocation-syplrv1t/summary.json`).
Four retained inventory/clock/replay/memory-policy/TracerV audits pass in
`retained-final-audit-results.json`. A fresh ordinary Rocket RTL diagnostic
probe matches all 318,637 semantic words across seven clocks before any edge;
this is diagnostic storage rather than a captured CPU image/replay.

Complete CPU requests reject before execution/checkpoint publication in
`cpu-request-rejections-verified/summary.json`: preflight identifies the unowned
TSI at `widget/12`; capture and restore reject the unavailable public durable
runtime capability. Preflight creates only the unchanged FASED CSV header and
an empty VCS key. Initial diagnostic assertions incorrectly expected no header
and identical rejection paths; their failed logs remain separate. No invalid
CPU-image restore or CPU semantic-corruption detection is claimed.

Existing iteration-101 controller commits were pushed FireSim first
(`f0a3772b537c4cc08942868471549efbb6a1fe12`), then Chipyard
(`b112499963188bcb8e5f8252ba1d31bb7edcaded`). Independent remote-tip and submodule-
pointer checks match; push logs retain the local read-only tracking-ref
messages. Neither plan, installed library nor environment input was edited.
No staging or local commits were performed. BOOM/Saturn remain pending;
standalone Shuttle, physical FPGA and ASIC power remain deferred.

Recovery metadata: `selected-results.json` binds the selected native summaries;
`native-input-archives.json` preserves their original inputs;
`executed-native-commands.json` records the actual native subprocess commands;
`verification-commands-native.json` provides runnable native checks. The root
artifact catalog records full paths and hashes, including initial diagnostics.
All 18 independent evidence audits pass, retaining 944 original input bindings
and 4,236 native command records. Remaining work is the explicit HTIF/memif/device/TestChip caller ledger,
cross-owner coherence, real early/warmed/outstanding-memory/late CPU cuts,
complete fresh Level-1 continuation and independent Level-2 captured replay.
No external dependency is missing.

Executable native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && checkpoint_m11_read_tmp=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration102/vcs-recheck-XXXXXX") && export TMPDIR="$checkpoint_m11_read_tmp" && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_serial_read_vcs --out automations/checkpoint_loop/runs/m11-iteration102/controller-serial-read-recheck --serial-summary automations/checkpoint_loop/runs/m11-iteration102/serial/invocation-hrgwtspy/summary.json
python -m tools.checkpoint_formats.tests.verify_tsi_serial_read_vcs --audit automations/checkpoint_loop/runs/m11-iteration102/serial-read/invocation-avekamwh/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration102/controller-rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration102/rocket-controls/invocation-6yxavjbu/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration102/native-regressions/invocation-hupf6h08/summary.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration102/rocket-controls/invocation-6yxavjbu/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration102/native-input-archives.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration102/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration102/protected-native-inputs.json
```

## Iteration 101: source-integrated FESVR serial FIFO ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration101/`.
See [tsi-serial-queues.md](tsi-serial-queues.md). Both complete Rocket checkpoint
levels remain in_progress. No coherent active CPU checkpoint, fresh CPU Level-1
continuation or captured CPU Level-2 replay has passed.

`firesim.tsi.serial-queues.v1` owns every remaining word in the target-bound and
host-bound serial FIFOs. The distinct source-integrated `firesim_fesvr_tsi_t`
retains the original serial packet, read-yield, handshake, reset and terminal-loop
algorithms. TestChip's `tsi_t` spelling aliases this class through the FireSim
project header. Installed FESVR HTIF/context/library bytes are unchanged. Both
queues validate and allocate fully before no-throw swaps; wrong configuration,
truncation, missing queues, incorrect counts, trailing words and wide data reject
before mutation. Restore performs no services, context switches, serial traffic
or target edges. The suspended read cursor/destination and callers are separate,
still unsupported owners. No complete CPU/TSI profile is enabled.

Selected serial evidence: `serial/invocation-49f0z1gy/summary.json`. Across native
sanitizer and VCS backends, all 78 fresh fixture restores, 1,560 complete
readbacks and 1,482 continued records pass. Each backend passes 904 atomic/interruption
and maximum-chunk checks. All 40 fresh invalid images reject atomically. Valid
request/response corruption first differs at fixture C=108/operation 8 and
C=112/operation 12; zero resumed operations are acknowledged. These are component
operation labels and serial-word faults, not Rocket target cycles or corrupted
DUT-state replay cases.

Actual installed-HTIF checks reconstruct all 384 complete serial images at
loader/reset/poll/idle cuts, including every transmitted packet tail and queued
response, for idle counts 1/3/10. All 384 images additionally restore in both fresh
backends: 768 complete zero-edge component readbacks. The 584-byte polling ELF
has real tohost/fromhost symbols and an original TestChip init read. Its images
are host-protocol cuts, not CPU workload checkpoints. Prior loader checks pass
in `real-fesvr/invocation-t385u4pu/summary.json` (14 read, 22 queue and 68 host
payloads). Additional original HTIF child/poll/idle checks pass all 162 host
payloads and 324 fresh host-control readbacks in
`host-fesvr/invocation-j7o3qk13/summary.json`.

Exact recipe build/control evidence:
`rocket-controls/invocation-7ye21zyi/summary.json` and
`rocket-serial-linkage-audit.json`. The full 59-unit prior inventory is preserved;
only `owned_fesvr_tsi.cc` is added, totaling 60 units. Generated RTL/reference/
manifest/constants, exact recipe settings and installed FESVR archive remain
unchanged. Native symbols bind the owned serial adapter and omit the original
library TSI implementation. All three TSI consumers' compiler dependencies bind
the local base header. Its explicit normal include prevents GCC system-header
filtering from hiding that ABI dependency in cached VCS external-C builds.

Both complete four-hart default/buffered controls pass at C=3,329,794. All four
full instruction traces per mode and all workload/store labels match the
uninterrupted reference. Workload:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
6,712 bytes, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
FESVR archive SHA-256 remains
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
These are full workload controls; required early/warmed-cache/outstanding-memory/
late CPU checkpoint cuts remain pending.

Preserved checks pass: 260 read continuations
(`loadmem-read/invocation-wx0bmjtm`), 340 queue restores
(`loadmem-queues/invocation-ybj12acp`), 228 bridge-control restores
(`bridge-control/invocation-croiwf04`), 48 actual bridge restores
(`actual-bridge-restores/invocation-k8fxdo6a`), 362 host-control fixture restores
plus 136 actual loader readbacks (`host-control/invocation-la9bpo31`), and all
1,012 transport requests / 566,096 full records (`loadmem-transport/invocation-03_a7gew`).
All four private transport faults reject at their first wrong word
(`loadmem-transport-faults/invocation-e4tbgzka`). All 245 Python tests and eight
complete source-stable native regressions pass in
`native-regressions/invocation-e_jefvyh/summary.json`, retaining 5,128 artifacts /
710 original source bindings. Four retained inventory/clock/memory/policy/TracerV
audits and a fresh ordinary Rocket RTL diagnostic probe pass all 318,637 words /
seven clocks before edges (`retained-audit-results.json`). This is diagnostic
storage, not a captured CPU image or replay.

Complete CPU preflight/capture/restore still reject before execution/publication
with `FS_CHECKPOINT_UNSUPPORTED: unsupported host checkpoint owner widget/12`
(`cpu-request-rejections-final/summary.json`). Remaining ownership: serial read
cursor/destination and suspended caller; HTIF poll/fromhost/device/stop/signature;
TestChip loader/cache-flush/init-access progress; and cross-owner coherence.
Coherent active CPU cuts, fresh complete Level-1 continuation and independent
Level-2 complete zero-edge state readback plus captured finite replay remain
pending. No dependency is missing. BOOM/Saturn remain pending; standalone Shuttle,
physical FPGA and ASIC power remain deferred. Both levels remain independent.

Existing iteration-100 controller commits were published FireSim first
(`97900cda9a2f29ec834a9627b3f155812e15d78a`), then Chipyard
(`fd92b046c5e613b676111e791e6664b6789be584`). Independent remote-tip queries and
submodule pointer match (`github-publication.json`). Push logs preserve the
local read-only tracking-ref diagnostic. No staging, local commits or protected
input edits. Initial oracle formatting, symbol-substring, output-path, dependency
and source-stability failures remain diagnostic attempts, not passing evidence.

All created paths are in `artifact-manifest.json`. `selected-results.json` binds
the complete original passing reports; `native-input-archives.json` retains their
original native inputs. `executed-native-commands.json` records original argv,
logs and exits; `verification-commands-native.json` supplies executable native
checks. Independent audits are in `independent-audit-results.json`.

Executable native checks from the Chipyard root (VCS environment sourced last;
unique temporary root prevents tool-shell PID/temporary-directory collisions):

```sh
source env.sh && source sims/firesim/env.sh && checkpoint_m11_serial_tmp=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration101/vcs-recheck-XXXXXX") && export TMPDIR="$checkpoint_m11_serial_tmp" && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_serial_vcs --out automations/checkpoint_loop/runs/m11-iteration101/controller-serial-recheck
python -m tools.checkpoint_formats.tests.verify_tsi_serial_vcs --audit automations/checkpoint_loop/runs/m11-iteration101/serial/invocation-49f0z1gy/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration101/controller-rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration101/rocket-controls/invocation-7ye21zyi/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration101/rocket-controls/invocation-7ye21zyi/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration101/native-input-archives.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration101/native-regressions/invocation-e_jefvyh/summary.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration101/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration101/protected-native-inputs.json
```

## Iteration 100: production FireSim idle/reset control

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration100/`.
See [tsi-host-control.md](tsi-host-control.md). Complete Rocket Level-1 and
Level-2 acceptance remain in_progress. No real CPU checkpoint continuation or
captured CPU RTL replay has passed.

`firesim.tsi.host-control.v1` owns the production FireSim TSI's exact parsed idle
count, busy/host-loaded/target-loaded flags, remaining idle yields and explicit
ready/idle/reset-wait/reset-child phase. The idle cursor changes before each
original switch, including the final suspended yield. Reset enters the original
TestChip child exactly once after target drain. Every candidate word and
configuration byte validates before mutation; restore performs no context
switch, FESVR service, MMIO, serial traffic or target edge. Escaping switch/child
exceptions permanently invalidate component access. Production inspection is
const and the aggregate bridge/CPU checkpoint contract remains unsupported.

Selected component evidence:
`host-control/invocation-lknimday/summary.json`. All 362 fresh sanitizer/VCS
fixture restores pass for idle counts 0/1/3/10 and an active UINT64_MAX cursor.
The original-loop oracle compares 7,866 complete readbacks and 7,504 resumed
records. Each backend passes 1,100 phase/atomic/interruption checks. All 36 fresh
missing/truncated/extra/incompatible/configuration/phase/cursor/flag images
reject atomically. Valid semantic corruption first differs at fixture C=125 /
operation 25 (idle return versus yield) and C=129 / operation 29 (reset yield
versus child entry), with zero resumed operations acknowledged in both backends.
The additional independent exact-scope audit is
`host-control-independent-scope-audit.json`. These are component operation
labels, not Rocket target-cycle boundaries.

Installed-FESVR loader evidence:
`real-fesvr/invocation-dvoja8gh/summary.json`. All 14 prior complete read images
and 22 prior complete queue images pass, and all 68 actual host-control images
match independently constructed payloads at loader/reset-wait/idle-yield cuts.
All 68 images restore in both fresh sanitizer/native and VCS component processes:
136 complete zero-edge readbacks with no FESVR context or services. The installed
FESVR archive remains SHA-256
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
Additional actual TestChip child-reset/HTIF polling checks pass in
`host-fesvr/invocation-y60aa977/summary.json`: 162 independently checked payloads
restore in both fresh backends, totaling 324 complete zero-edge readbacks.
Its 584-byte ELF has real tohost/fromhost symbols,
an init read and duplicate idle-count arguments. It exercises all idle yields,
suspended child read, both poll-response halves and subsequent busy polls.
Its component restores still do not restore HTIF or a CPU.

Prior component regressions pass: 260 read continuations
(`loadmem-read/invocation-n2q6l21r/summary.json`), 340 queue restores
(`loadmem-queues/invocation-s3pe7v94/summary.json`), 228 bridge-control restores
(`bridge-control/invocation-7oto0h22/summary.json`), and 48 actual bridge restores
(`actual-bridge-restores/invocation-d9j8cfdz/summary.json`). Actual transport
retains all 1,012 requests / 566,096 records
(`loadmem-transport/invocation-gjd6k2h9/summary.json`); four private transport
faults still reject at their first wrong word
(`loadmem-transport-faults/invocation-242y_s17/summary.json`).

Exact recipe rebuild:
`rocket-controls/invocation-6ktgjmr4/rocket-build-identity.json` and
`rocket-host-control-linkage-audit.json` bind the new header and all three native
checkpoint methods, with all 59 translation units unchanged and no CPU profile.
Both complete four-hart default/buffered controls pass at target count
3,329,794 (`rocket-controls/invocation-6ktgjmr4/summary.json`). All four complete
traces per mode (37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes) and
all workload/store labels match the uninterrupted reference. These are CPU
controls, not checkpoint continuations. The self-checking
workload remains
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
6,712 bytes, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
All 245 Python tests and the final eight-check preserved source-stable native
regression batch pass in `native-regressions/invocation-rxa8jg_3/summary.json`,
retaining 5,125 artifacts / 707 source bindings. Four retained complete inventory/
clock/memory/policy/TracerV audits and a fresh ordinary Rocket RTL probe pass
all 318,637 words / seven clocks before edges (`retained-audit-results.json`).
That probe remains diagnostic storage, not captured CPU state.

Complete CPU preflight/capture/restore reject before run/publication in
`cpu-request-rejections/summary.json`. Remaining ownership: FESVR private serial
queues and suspended caller/read destination, HTIF poll/fromhost/device/stop/
signature, TestChip loader/cache-flush/init-access progress, and cross-owner
coherence. HTIF's nonvirtual run path still needs audited source integration or
a pointer-free engine. Required early/warmed-cache/outstanding-memory/late CPU
checkpoint cuts and both independently restored checkpoint levels remain
pending. BOOM/Saturn remain pending; standalone Shuttle, physical FPGA and ASIC
power remain deferred. No dependency is missing.

Existing iteration-99 controller commits were published FireSim first
(`76250b8830fbd6371ff1f71a43ab23bb81a5d0e7`), then Chipyard
(`32b41598af5c621b5d88d655d1f32914491a8abf`). Independently queried remote tips
and the Chipyard submodule pointer match (`github-publication.json`). No staging,
local commits or protected input edits. Initial transcript formatting, VCS temp
collision, source-stability rejection and actual-host pilot diagnostics remain
separate. Failed runs are not passing evidence. VCS retries use distinct TMPDIR
roots because separate tool shells can share timestamp/PID namespaces.

All created paths are recorded in `artifact-manifest.json`; selected native
reports are in `selected-results.json`. Original executed argv/exit/log records
are in `executed-native-commands.json`; executable checks are in
`verification-commands-native.json`. `native-input-archives.json` retains 929
original native source/build bindings; `protected-native-inputs.json` and the
retained-evidence checks preserve protected files and controller ancestry.
Independent original native audits are in `independent-audit-results.json`.

Executable complete native checks from the Chipyard root (VCS environment
sourced last; separate temporary roots prevent tool-shell PID collisions):

```sh
source env.sh && source sims/firesim/env.sh && checkpoint_m11_recheck_tmp=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration100/vcs-recheck-XXXXXX") && export TMPDIR="$checkpoint_m11_recheck_tmp" && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs --out automations/checkpoint_loop/runs/m11-iteration100/controller-real-fesvr-recheck
python -m tools.checkpoint_formats.tests.verify_tsi_host_control_vcs --out automations/checkpoint_loop/runs/m11-iteration100/controller-host-control-recheck --fesvr-summary automations/checkpoint_loop/runs/m11-iteration100/real-fesvr/invocation-dvoja8gh/summary.json
python -m tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs --out automations/checkpoint_loop/runs/m11-iteration100/controller-host-fesvr-recheck --component-summary automations/checkpoint_loop/runs/m11-iteration100/host-control/invocation-lknimday/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration100/native-regressions/invocation-rxa8jg_3/summary.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration100/rocket-controls/invocation-6ktgjmr4/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration100/native-input-archives.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration100/controller-rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration100/rocket-controls/invocation-6ktgjmr4/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration100/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration100/protected-native-inputs.json
```

## Iteration 99: production TSI bridge host control

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration99/`.
See [tsi-bridge-control.md](tsi-bridge-control.md). Complete Rocket checkpoint
acceptance remains in_progress; no real CPU workload image or captured CPU RTL
replay has passed.

`firesim.tsi.bridge-control.v1` owns the production bridge's initialization,
remaining reset-delay cursor and one-time early-fast transition. Its immutable
identity binds all nine MMIO addresses, selected TSI index/arguments, memory
availability/offset/beat width and configured steps/wait/fast settings. Restore
validates the entire identity and both mutable words before changing either;
it executes no services, MMIO or FESVR work. Every init/tick/status callback is
guarded; reentrant/active access and interrupted calls reject. The original
loading-step computation and original callback order are preserved. The bridge's
aggregate checkpoint schema remains unsupported, and its component is exposed
only for const inspection.

Selected evidence: `bridge-control/invocation-9t8x1ge_/summary.json`. All 228
fresh sanitizer/VCS component restores pass across both fast settings and waits
0/1/8 at every completed-operation cut. The independent original-flow oracle
compares 2,584 complete state readbacks and 2,356 continued callback records.
Each backend passes 476/488/572/482/494/578 atomic/lifecycle/callback checks
for variants 0-0/0-1/0-8/1-0/1-1/1-8 (3,090 checks per backend). Forty fresh
malformed/missing/truncated/incompatible/lifecycle image processes reject
before mutation or services. A valid wait-cursor corruption differs at fixture
C=119 / operation 19: expected `RECEIVE` after `DONE=1`, actual `GO`; neither
backend acknowledges any resumed operation. These are bridge-component fixture
labels, not Rocket target-cycle cuts. Two additional fresh executable native/VCS
restore commands pass in `executable-native-command-checks.json`.

Actual installed-FESVR transport evidence:
`loadmem-transport/invocation-ixxqv4xu/summary.json`. All 1,012 requests /
566,096 independent records, 32 invalid requests before I/O, four callback-unwind
checks and four actual public TSI bridge runs pass. Twenty-four complete actual
bridge-control images match independently reconstructed identity/state bytes
at construction, init and four ELF loader ticks for both beat widths/backends.
Capture/validation performs no MMIO. All 24 actual images additionally restore
in both fresh sanitizer/native and VCS processes: 48 complete zero-edge
readbacks with no services object or service calls in
`actual-bridge-restores/invocation-g3r7hq1g/summary.json`. This restores only
the bridge host component, not its FESVR caller or generated RTL.
The actual FESVR fourteen read images and
22 complete queue images pass in `real-fesvr/invocation-sqy1po4i/summary.json`.
The ELF/library hashes remain
`45a7f219e68180b49d557cad0c10277277af843c16e4a5e58dc8fb7fb6cb77be` /
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
Private repeated-beat/response-bit faults retain first wrong-word detection
in `loadmem-transport-faults/invocation-i4m8rpm4/summary.json`.

The exact-recipe rebuild binds the new bridge-control header and all three
checkpoint symbols, retaining all 59 native translation units and no CPU profile
(`rocket-bridge-control-linkage-audit.json`). Both complete four-hart default/
buffered controls pass at C=3,329,794 in
`rocket-controls/invocation-u5mnr995/summary.json`. All four complete traces
per mode (37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes) and all
workload/store labels match the uninterrupted reference.
Workload bytes/hash and original target-cycle labels remain bound by
`rocket-controls/invocation-u5mnr995/rocket-build-identity.json` and its runtime
commands; the self-checking ELF is 6,712 bytes at
`automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
with SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These are uninterrupted CPU controls.

All 245 Python tests and eight preserved native checks pass in
`native-regressions/invocation-eatwfw4a/summary.json`; independent re-audit passes
with 5,116 retained artifacts and 698 original source bindings. Four retained
complete inventory/clock/memory/policy/TracerV audits pass, plus a fresh ordinary
Rocket RTL diagnostic probe of all 318,637 words / seven clocks before edges
(`native-rocket-probe-OwmYMm/run.log`, commands in
`retained-audit-results.json`). Complete CPU preflight/capture/restore still
reject before run/publication in `cpu-request-rejections-final/summary.json`.
All 260 prior production read-owner continuations pass again in
`loadmem-read/invocation-2ghbp73n/summary.json`; all 340 production queue
restores / 5,950 complete readbacks / 5,610 continuation records and 42 invalid
image processes pass in `loadmem-queues/invocation-wvii4cf1/summary.json`.

Remaining ownership includes FESVR's private serial queues, suspended read caller/
destination and HTIF/context; HTIF poll/fromhost callbacks and device/stop/signature
state; TestChip program-load/cache-flush/init-access progress; and FireSim idle/
reset flags/cursors and aggregate cross-owner validation. `htif_t::run()` is
nonvirtual, and `tsi_t::host_thread` calls it through `tsi_t*`: a derived method
with the same name cannot reconstruct or replace this execution path. A complete
adapter needs an audited pointer-free protocol engine or audited FESVR source
integration; restoring only the two serial queues would still omit the suspended
caller. Installed FESVR remains a hashed input, not a missing dependency.

Coherent four-hart cuts at early/warm-cache/outstanding-memory/late execution,
fresh Level-1 CPU continuation and independent Level-2 CPU .rtlckpt/.trace replay
remain pending. BOOM/Saturn remain pending. Physical FPGA, standalone Shuttle
and ASIC power remain deferred. Published existing iteration-98 controller commits
FireSim `bd38643e84405ca75f02092ce2e2615e6042d419`, then Chipyard
`9d909c6ff114d8eb73268badc17663b8f84f73ca`; both independently queried remote tips
match. Read-only local tracking-ref diagnostics are retained in
`github-publication.json`. No local commit, staging or protected-input edit.

All created paths are in `artifact-manifest.json`; original native artifacts and
source inputs are sealed in `native-input-archives.json`. Exact original commands
and exits are retained in `executed-native-commands.json`; runnable complete
checks are in `verification-commands-native.json`. Both fresh executable native/
VCS command forms pass independently.

Executable native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_bridge_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration99/bridge-recheck
python -m tools.checkpoint_formats.tests.verify_tsi_bridge_checkpoint_vcs --audit automations/checkpoint_loop/runs/m11-iteration99/bridge-control/invocation-9t8x1ge_/summary.json
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_vcs --out automations/checkpoint_loop/runs/m11-iteration99/transport-recheck
python -m tools.checkpoint_formats.tests.verify_tsi_bridge_actual_vcs --out automations/checkpoint_loop/runs/m11-iteration99/actual-bridge-recheck --transport-summary automations/checkpoint_loop/runs/m11-iteration99/loadmem-transport/invocation-ixxqv4xu/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration99/native-regressions/invocation-eatwfw4a/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration99/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration99/rocket-controls/invocation-u5mnr995/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

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
