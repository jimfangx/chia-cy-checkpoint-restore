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

Recovery instruction (October 26, 2026): the user increased this manager to
61 GiB RAM and authorized resuming the loop. Ray killed the previous iteration
239 worker at its 95% memory threshold while exact-Rocket Java generation and
multiple Vivado jobs overlapped; iteration 238 is the last controller-verified
checkpoint. The host restarted and no previous loop/build workers remain.
Recover the existing dirty iteration-239 work and preserve its diagnostics;
its full regression sweep was interrupted, so do not claim it completed.
Schedule at most two local Vivado jobs from launch, and avoid overlapping the
large Java generation with the native synthesis sweep. Keep every required
test and sanitizer enabled, and keep Ray's memory protection enabled. Do not
restart the old PID-based native-concurrency helper after the host restart.

Current user priority (October 23, 2026): actual AWS F2 FPGA capture and
FPGA-to-EDA checkpoint migration. Follow the current top of `plan_agent.md`
and [aws-f2-workflow.md](aws-f2-workflow.md). Reuse the four initialized manager YAMLs and the already configured AWS setup.
Build bitstreams on this server with ExternallyProvisioned localhost; do not
launch EC2 build hosts or build on EDA. Run a real single-node Rocket F2 workload, then implement/build/deploy complete
capture hardware and validate FPGA-produced Level-1/Level-2 images in fresh
EDA VCS, including finite replay, rolling recovery and sustained live RTL.
FPGA synthesis/image builds and physical acceptance are required. ASIC
mapping/formal/gate/power remain excluded. Standalone Shuttle is excluded.

Follow [GitHub checkpoint publication](github-publication.md); the loop controller
owns staging/local commits and the agent may publish existing checkpoints.

Active milestone: `F2-rocket-checkpoint-migration`, iteration 284,
**in_progress; full-disk failure recovered and independent graft waveform audit verified**.

The controller's previous rerun exhausted EDA storage while saving the graft
mutation receipt, leaving it zero bytes. Its original files and diagnostics
remain intact. The new explicit EDA waveform-storage helper shares only
kernel-verified equal ranges, hashes every byte before and after, preserves
original regular files/independent inodes, and checks free bytes and inodes.
Four pairs shared 148,784,414,720 bytes; final EDA capacity is about 95 GiB.
Actual XFS equal/different-range and COW isolation selftests pass.

The independent plain-graft auditor reconstructs frontdoor input history,
checks all native fields and every ordered bank word, backpressure and dequeue
continuation. Fresh SP2 graft execution and audit pass 196,624 words /
5,899,136 native-vector samples; the exact compiled lane fault diverges at raw
VCD time 61,527,000 with zero requests/acknowledgements after a complete four-lane
fill. This component has no CPU target-cycle authority. Re-audited controller-
completed staging passes four cuts / 416 staged words / 5,913,197 native samples
and all three exact compiled faults before word acknowledgement.

All 331 Scala tests / 52 suites plus twelve preparation tests, 362 Python tests,
61 manager tests, 47,219 ASan/UBSan host assertions, all sixteen fresh SP2 scopes,
complete retained components and six additional waveform audits pass. The first
sweep correctly refused a regional native manifest missing the two new Python
files. Complete localhost synthesis refreshed ten source sets and retained six
matching historical receipts, with peak concurrency two and no large Java
synthesis overlap; the full EDA rerun then passed. Final aggregation verifies
exact current source sets, native-input namespaces, structured artifact ledgers
and compiled faults. Its original import/schema diagnostics are preserved.

Fresh exact-Rocket compilation still rejects the FASED physical BUFGCE CE latch
without a synthesized owner/common-low-phase cut. Production common-cut/reset,
all three physical CE owners, live MMIO/DMA self-state, complete functional
memory/FASED/host/pre-FAME ownership, full image/P&R/AFI, real all-hart FPGA cuts
and paired CPU zero-edge/finite/live/rolling migration remain pending. Next work
must bind the staged readout to the production widget and close those owners;
keep admission guards enabled. No checkpoint-enabled image or actual hardware
capture was produced. Reuse iteration194's localhost invocation and initialized
manager inputs. Final AWS/native inventory has no active loop farm, pending AFI
or owned Java/Vivado job; every test/transfer has completed and joined.

Both plans and all four manager YAMLs retain their entry hashes. No staging,
local commits or account bootstrap was performed. Existing controller commits
were pushed FireSim first, then Chipyard; direct remote observations confirm
them despite the preserved local tracking-ref filesystem warning. Publication
observations refer to those commits, not a future controller checkpoint.
Managed worker startup failed before execution; only the central agent ran and
no delegated LLM remains. Commands, receipts and per-cut gaps are under
`runs/aws-f2/iteration284/`: `verification-commands.json`,
`final-evidence-selected.json`, `recovery-diagnostics.json` and
`remaining-blockers.json`. See [GitHub checkpoint publication](github-publication.md)
for publication of the controller's next checkpoint.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 283,
**in_progress; compiled staging-fault provenance and interrupted sweep recovered**.
All three compiled semantic/handshake fault sources now join the immutable
staging artifact manifest. The independent auditor reconstructs each exact edit
from the original adapter; missing, changed, swapped, extra-edited or coherently
rehashed sources reject. The original iteration-282 receipt rejects at its
unbound premature-request source without changing historical bytes.

Complete checks pass 331 Scala tests / 52 suites plus twelve preparation tests,
354 Python tests, 52 manager tests and 47,219 ASan/UBSan host assertions. The full
localhost native sweep passes with peak concurrency two and no large JVM
synthesis overlap. Ten bank/region native source sets were refreshed; six
matching receipts retain their original provenance. All sixteen fresh SP2 EDA
scopes, complete retained regressions and six additional waveform audits pass.
Four-cut queue execution passes 78,343,201 checks / 983,220 stalls; complete
wave/input-history/word/CRC auditing passes all four cuts, eight corrupt or
rechecksummed streams and six compiled mutations. Staged shared-graft execution
passes four cuts / 416 staged words / 196,624 original words; independent debug
readback checks 5,913,197 native-vector samples and all three exact compiled
faults at component cut 9001 before any word acknowledgement. These remain
component results, with no physical CPU capture acceptance.

Every generated raw VCD remains a regular file at its original retained EDA
path. A streamed XFS audit verifies every byte before and after sharing
74,546,233,344 identical bytes across two waveform pairs, including four full
expected digests and a differing-range self-test. The first cache-thrashing
storage audit was deliberately stopped (helper exit 143); its runner/log and
restart diagnostic remain intact. The initial final-audit wrapper assumed a
queue VCS `inputs` field; version 2 checks every native-bound input plus all EDA
artifacts and source/receipt bindings. Its failed runner/log and schema diagnosis
are preserved. Corrected final aggregate receipt audit passes; all original diagnostics remain bound.
All regression jobs and transfers have completed and joined. Final AWS/native
inventory is clean: no active loop runtime, pending AFI or owned Java/Vivado job.

Production common-cut/reset, three physical CE owners, live MMIO/DMA self-state,
complete functional memory/FASED/host/pre-FAME ownership, full image/P&R/AFI,
active all-hart FPGA cuts and paired CPU zero-edge/finite/live/rolling migration
remain pending. The fresh exact-Rocket compile still rejects the FASED BUFGCE
CE latch without its synthesized owner/common-low-phase cut. Next implementation
must bind the staged readout to the production widget and complete those owners;
keep admission guards enabled. Reuse iteration194's localhost invocation and
initialized manager inputs. Both plans and all four manager YAMLs retain their
entry hashes. No agent staging/local commits, new runtime or AFI was requested.
Existing controller checkpoints were published FireSim first, then Chipyard;
direct remote tips match despite a local tracking-ref filesystem warning.
Managed worker creation failed before startup; only the central agent ran and
no delegated LLM remains. Commands, individual immutable receipts and explicit
per-cut gaps are under `runs/aws-f2/iteration283/`: `verification-commands.json`,
`remaining-blockers.json`, `complete-eda-recovery-selected.json` and the final
selected audit. See [GitHub checkpoint publication](github-publication.md) for
the controller's next checkpoint.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 282,
**in_progress; opt-in common staging for the shell-only shared queue graft**.
The adapter now samples the complete 6,656-bit native vector before any bank
request and gates both outer and internal request/response acknowledgements.
Missing owners, lost freeze, drift, premature traffic and busy release/capture
revoke permission. Its complete 6,727-bit payload/control output has explicit
capture-only ownership; mixed physical regions and ordinary widget integration
still reject.

Native Vivado 2025.2 synthesis passes all 64 original URAMs and an independent
per-bit D/Q/control/clock/enable audit: 6,624 dynamic payload bits, exactly 32
zero local-bank bits, and 71 control bits. OOC resources are 6,021 LUTs / 11,483
registers, with +4.481/+0.082 ns setup/hold estimates at unchanged 140 MHz.
Full-shell/I/O timing is pending. Fresh EDA SP2 staged execution passes four
cuts, 416 staged words, 196,624 original words, 589,872 stalls and dequeue
continuation. Eleven permission faults and three compiled semantic/handshake
mutations reject before a word acknowledgement. Full debug archives are retained.

Iteration-282 ended before its full Scala source-bound sweep, complete
native/EDA regressions and independent staged waveform auditing completed.
Do not interpret these interrupted sweeps as passes. Existing
52 manager tests and AWS/HDK/Vivado/Fabric preflight pass. Launch-path errors,
interrupted raw Scala setup and the initial overly strict register-count check
remain in original logs. Current native receipt:
`runs/aws-f2/iteration282/staging-native/vivado-9tv70ilp/summary.json`.
Use this iteration's scripts/selections for recovery; reuse iteration194's
ExternallyProvisioned localhost invocation and initialized manager inputs.
No new image, AFI, runtime, physical checkpoint or CPU migration is claimed.
Managed worker startup failed before execution; only the central agent ran.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 281,
**in_progress; native synchronous queue state through the shared region graft**.
The shared graft now retains each synchronous shell's live native observation
vector and exports it in immutable shell/field order. Shell-only readout uses
no physical CE ports or invented CE owner. Exact four-queue geometry produces
6,656 native bits alongside the twenty original bank descriptors; no original
queue execution is duplicated. The ordinary physical widget explicitly rejects
connection until an atomic native staging owner exists. The new output remains
live during borrowing and is not a snapshot or a restore interface.

Current checks pass 330 Scala tests / 52 suites plus twelve preparation tests,
348 Python tests, 52 manager tests and 47,219 ASan/UBSan host assertions. Fresh
FCFS passes 46 continuations / 138 pre-edge owner comparisons. The complete
native sweep passes with peak concurrency two and no large Java overlap. Six
affected bank/region source sets were rebuilt; ten receipts with matching source
hashes retain their original provenance, including five completed same-iteration
children recovered without changing their receipts.

The shared graft retains 64 URAMs, 3,671 LUTs and 4,760 registers, no LUT RAM.
At unchanged 140 MHz, OOC setup/hold estimates are +4.685/+0.084 ns; full-shell,
I/O budgets and image implementation remain pending. Six coherently rehashed
structural negatives reject. The final fresh EDA SP2 graft passes 196,624 original
words, 3,539,494 native-vector comparisons, 589,872 stalls and dequeue continuation.
A separately compiled lane substitution stops before any bank acknowledgement.
Full debug waves return as lossless archives. Its authenticated receipt is
`queue-graft-eda/vcs-vsdg4t1p/summary.json` under this iteration.

The original four-cut EDA queue scope passes cuts 6486/6622/6855/7185 with
78,343,201 checks / 983,220 stalls. Independent full-wave/input-history auditing
passes all 56 original native vectors, three router vectors / 28,146,316 samples
and all 786,912 words. Eight corrupt/rechecksummed streams and six compiled
mutations reject. All sixteen fresh EDA bank/region scopes, complete retained
capture/transport/snapshot/restore/widget scope and six additional waveform
audits pass. Both branches exited zero; all three helper stages returned their
artifacts and were joined. All VCS execution used EDA SP2.

Initial verifier metadata/timescale errors, source-pinning rejection and launcher
transfer/path-alias diagnostics remain immutable under `runs/aws-f2/iteration281/`.
The path alias invalidated the first graft receipt; a complete fresh rerun
produced the final receipt above. It was not reconstructed or rehashed to pass.
No core source changed during the final sweep. Final source/provenance/artifact/protected-input auditing passes; consult
`final-audit-selected.json` and its pinned `final-audit-rv20eox1/summary.json`. No tagged runtime,
pending AFI or owned Java/Vivado job remains. No instance or AFI was requested.
Plans and initialized manager YAMLs retain their entry hashes; existing controller
checkpoints were pushed FireSim first, then Chipyard. The agent made no staging
or local commit. Managed-worker startup failed before execution; no delegated
LLM work exists.

Reuse iteration194's ExternallyProvisioned localhost invocation. Complete
production common-cut/reset/memory/host/pre-FAME ownership, image/P&R/AFI,
actual active all-hart FPGA cuts, complete paired zero-edge/finite/live CPU
migration and rolling hardware recovery remain pending. No hardware column
advances. Plans and initialized manager YAMLs are read-only. Existing controller
checkpoints were published FireSim first, then Chipyard. Managed subagent startup
failed before execution; only the central agent runs and no delegated LLM exists.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 280,
**in_progress; complete native-cut fault qualification and component implementation**.
The native owner expands the complete snapshot failure policy at its boundary,
removing the remaining non-READ snapshot-failed/request-ready permission detour.
State/register layout, capture edges, latency and original diagnostic updates
stay unchanged. Fresh EDA SP2 passes all 131,072 binary phase/control combinations /
393,216 output comparisons and four additional compiled prerequisite-removal
mutations, alongside all seven capture geometries and 113 independent wave audits.

All 330 Scala tests / 52 suites plus twelve preparation tests, 348 Python tests,
52 manager tests and 47,219 ASan/UBSan host assertions pass. Fresh FCFS passes
46 continuations / 138 pre-edge owner comparisons. Seven affected broad native
source sets were rebuilt; nine unchanged receipts retain original provenance.
Native concurrency never exceeds two, without Java overlap.

The 64-URAM component retains 11,876 registers and no LUT RAM. Its unchanged
140 MHz OOC setup/hold estimate improves to -0.192/+0.073 ns from -0.832/+0.073 ns
(14 versus 17 logic levels). Native placement/routing passes +0.153/+0.019 ns,
7,771 logic LUTs, preserving all 11,943 original FD/URAM/BUFGCE identities/types
with DONT_TOUCH on those cells. Two rejected default-placement attempts preserve
Vivado's merger of nineteen synthesized forwarding-hit register copies and
before/after inventories; no guard was relaxed. The 1,666-bit transport separately
implements at +0.661/+0.054 ns. These are internal OOC results; full-shell/I/O
budgets and full-image timing remain pending.

Fresh EDA queue execution passes cuts 6486/6622/6855/7185 with 78,343,201 checks /
983,220 stalls. Full-wave/input-history auditing passes 56 original native vectors,
three router vectors / 28,146,316 samples and all 786,912 words. All six compiled
queue mutations and eight corrupt/rechecksummed stream cases reject. The complete
retained SP2 scope, all sixteen fresh bank/region scopes and six additional wave
audits pass. All EDA artifacts returned and the complete pipeline exited zero
and was joined. Full-visibility original wave bytes remain on EDA and return in
lossless archives. Commands and immutable receipts belong under
`runs/aws-f2/iteration280/`; the final source/artifact/protected-input/provenance
and resource audit passes. Consult `final-audit-selected.json` and its pinned
`final-audit-h44y7l18/summary.json`.

No active tagged runtime, pending AFI or owned Java/Vivado job remains. No new
instance or AFI was requested. Existing controller checkpoints were published
FireSim first, then Chipyard; the agent made no staging/local commit. Plans and
initialized manager YAMLs retain entry hashes. Managed-worker startup failed
before execution; only the central agent ran and no delegated LLM remains.

Reuse iteration194's localhost invocation. Production common-cut/complete owners
still reject the exact Rocket build at the FASED BUFGCE latch. Full image/P&R/AFI,
actual all-hart FPGA cuts/reference, paired complete zero-edge/finite/live CPU
migration beyond trace and rolling hardware recovery remain pending. No hardware
acceptance column advances.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 279,
**in_progress; registered native queue admission and exact readout build identity**.
The synchronous adapter reuses its existing phase register to borrow RAM only
on the edge after accepting/storing selectors. Version-3 policy records four-edge
latency; hold loss invalidates preparation even if hold returns before sampling.
Source proof, independent FIRRTL audit and fresh VCS check all reset/release phases,
transient hold loss, latency and admission before borrowing. Version-2 component
stream manifests bind emitted RTL, four complete bank bindings and transport RTL;
incompatible headers reject before their first DMA acknowledgement.

All 330 Scala tests / 52 suites plus twelve preparation tests, 348 Python tests,
52 manager tests and 47,219 ASan/UBSan host assertions pass. Ten affected native
source sets were rebuilt; six unchanged receipts retain original provenance.
All additional native snapshot/queue/NASTI/endpoint/physical/capture/transport
scope passes, with peak concurrency two and no Java overlap. The F2-part component
retains 64 URAMs, 11,876 flip-flops and 7,869 logic LUTs, no LUT RAM. At unchanged
140 MHz, OOC setup/hold estimates improve to -0.832/+0.073 ns from -1.704/+0.073 ns.
Timing closure remains pending; the 17-level permission path now ends at the
accepted-request native_active/D, rather than a URAM address.

Fresh EDA SP2 passes component cuts 6486/6622/6855/7185 with 78,343,201 checks /
983,220 stalls. Independent full-wave auditing passes 56 original native vectors,
three router vectors / 28,146,316 samples, input-history RAM reconstruction and
all 786,912 words. The full 151.84-GB VCD is retained losslessly in a 21-GiB
returned archive. Owner/fault/abort recovery, six compiled mutations (including
wrong build identity), eight corrupt/rechecksummed negatives, all sixteen fresh
bank/region scopes, complete retained bridge/capture/snapshot/restore/widget
scope and six additional waveform audits pass. All EDA artifacts returned;
the complete pipeline exited zero and was joined. Final source/protected-input/
artifact/provenance and resource audits pass. Consult
`runs/aws-f2/iteration279/final-audit-selected.json`; the exact per-cut receipt is
`queue-current-eda/vcs-5aviugut/summary.json`, independent waveform receipt
`queue-wave-audit/audit-3xcrdno7/summary.json`. Commands live in this iteration's
scripts and immutable receipts. The initial pre-final-source EDA pass and
exploratory queue run retain their diagnostic scope; they do not replace the
final source-bound evidence.

No active tagged runtime, pending AFI or owned Java/Vivado job remains. No instance
or AFI was requested. Existing controller checkpoints were published FireSim first,
then Chipyard. The agent made no staging/local commit; plans and initialized
manager YAMLs retain entry hashes. Managed worker startup failed before execution;
only the central agent ran and no delegated LLM remains. Reuse iteration194's
localhost invocation. Production common-cut/complete owners still reject the
exact Rocket build at the FASED BUFGCE latch. Full image/P&R/AFI, actual all-hart
FPGA cuts/reference, paired complete zero-edge/finite/live CPU migration beyond
trace and rolling hardware recovery remain pending. No hardware column advances.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 278,
**in_progress; exact ordered queue-stream coverage**. The independent auditor
now requires every original/native descriptor address exactly once in manifest
order, including the zero header sequence. Duplicate RAM words, complete owners
or native words with correct payloads and repaired CRCs can no longer hide an
omitted owner. The VCS monitor also validates the selector before its accepting
DMA edge. Seven focused cases, all 344 checkpoint Python tests, 52 manager tests,
47,219 ASan/UBSan host assertions and retained FCFS/bank/cut scope pass. Five
fresh EDA compiled mutations reject, including the selector before acceptance.
All seven affected native source sets plus two snapshot owners pass; nine
unchanged native receipts retain their original provenance. The final four-queue
localhost synthesis retains 64 URAMs, with -1.704/+0.073 ns OOC setup/hold at
140 MHz. Fresh SP2 VCS passes component cuts 6486/6622/6855/7185 with
61,925,913 checks and 491,720 stalls. Its 130-GiB full VCD is retained losslessly
in a 19-GiB returned artifact, with bounded hashing/readback and zero observed
swap. Missing-owner/fault/abort recovery passes. Independent full-wave auditing
passes all 56 original native vectors, three router vectors / 22,051,251 samples,
input-history memory reconstruction, all 786,912 data words and eight corrupt/
rechecksummed negatives. The unpublished unresolved-selector diagnostic is
retained and never acknowledges its staged-native words. The full retained
SP2 scope now passes: all sixteen fresh bank/region scopes, FCFS/host/cut/shared
queue/NASTI/endpoint/physical/coordinated-capture/transport, complete snapshot/
restore/widget scope and six additional independent waveform audits. All EDA
artifacts have returned locally. The final strict source/protected-input/resource
and artifact-hash audit passes; its catalog binds every per-cut capture and all
four complete debug waves. Final AWS/native inventory has no active tagged F2
runtime, pending AFI or owned Java/Vivado job. No instance or AFI was requested.
Commands and receipts belong under
`runs/aws-f2/iteration278/`; consult `final-audit-selected.json` for that result.
The completed queue attempt is `queue-current-eda/vcs-p2_l5nc9`, with independent
receipt `queue-wave-audit/audit-46ubzpqq/summary.json`. The EDA pipeline
`await-native-eda.py`/`eda-complete.sh` exited zero and has been joined.
This is component validation: no checkpoint-enabled full image or FPGA-produced
CPU state exists.
Production common-cut/complete owners, localhost full-image P&R/AFI, active
all-hart physical cuts, paired complete zero-edge/finite/live migration beyond
trace and rolling FPGA recovery remain pending. No hardware column advances.

Native managed-worker startup again failed before execution; only the central
agent runs and no delegated LLM remains. Initial two native jobs rejected a
source change made during verification; their diagnostics remain preserved.
Recovery selected only fully validated current-source receipts. Use at most two local
Vivado jobs and do not overlap Java generation. Plans/initialized configs stay
read-only; the controller owns staging/local commits. Existing checkpoints were
pushed FireSim first, then Chipyard; the Chipyard remote accepted its update but
local remote-tracking-ref update encountered a read-only `.git` filesystem.
Read-only remote-tip receipts retain the actual published IDs.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 277,
**in_progress; four exact-geometry native queue transport integration**.
See [f2-rocket-native-queues.md](f2-rocket-native-queues.md). The new synthesized
router joins all four native queue endpoints to one atomic staging/MMIO/DMA
controller, retains the response owner through drain and exposes its three
register vectors. It rejects overlapping and reserved-bank allocations. The
isolated fixture extracts the retained production Queue_56 definition and keeps
its 512-by-6,144 ULTRA geometry: twenty original descriptors and 6,656 native bits.
The original unused physical gate, transport self-state/composite restore and
complete production ownership remain explicitly unsupported. No hardware column
advances and no canonical CPU checkpoint is claimed.

Current checks: the complete Scala run passes **330 tests / 52 suites**, plus
all twelve preparation tests. The targeted generator passes; its first native
F2-part build maps sixteen URAMs per original queue, 64 total, without LUTRAM
fallback. That exploratory build estimates −1.704 ns setup at 140 MHz, so timing
closure remains pending. The final source-bound native rebuild, full four-cut
EDA transfer, independent waveform/input-history/CRC audit, compiled mutations
and retained regressions are still running; consult the iteration's selections
before claiming them. Original owner/fault/abort-recovery EDA probes pass.

The fresh exact-Rocket compiler still rejects production FASED physical CE/
common-cut ownership. Full localhost image/P&R/AFI, all simulator/FAME/memory/
timing/bridge/host/pre-FAME owners, actual four-hart captures/reference and paired
zero-edge/finite/live CPU migration beyond trace plus rolling hardware recovery
remain pending. Reuse iteration194's localhost invocation and initialized manager
inputs. AWS/native/HDK/Fabric preflight passes. No new runtime or AFI is requested.
Existing controller checkpoints were published FireSim first, then Chipyard;
the agent creates no local commit. Plans and manager YAMLs retain entry hashes.

Managed worker startup failed before execution; the central agent performs all
work and no delegated LLM remains. Initial fixture/elaboration, stale-source,
retained maybe_full, trailer-handshake and FIFO-VCD diagnostics are preserved in
`runs/aws-f2/iteration277/diagnostic-notes.json`. VCS needs a seekable dump file;
the final path preserves regular full-visibility VCD bytes on EDA and returns
lossless completed compression. Continue waiting for/joining active native/EDA
jobs before the final report. All current commands and evidence belong under
`runs/aws-f2/iteration277/`; final aggregate audit is not complete yet.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 276,
**in_progress; native READ policy and F2-part component implementation verified**.
See [f2-native-capture-transport.md](f2-native-capture-transport.md).
The timing-critical READ predicate now uses the existing registered snapshot
occupied/error/cut-label fields directly. The original complete fault network
still records errors; no storage or fault latency is added. Explicit three-bit
phase encoding preserves direct register readout after synthesis. Production
Rocket ownership/admission and composite restore remain unsupported.

Final-source localhost Vivado 2025.2 F2-part synthesis retains all 1,666 bits and
improves the OOC estimate from historical −0.859 ns to −0.529 ns at 140 MHz.
Component placement/routing preserves every original register output identity:
**+0.540 ns setup / +0.047 ns hold**, 2,507 LUTs, four default SYNC gates, one
falling-edge mask and zero routing errors. This implements the 1,036-bit native
vector component. Shell integration, I/O budgets, the HD.CLK_SRC insertion
reference and full-image closure remain pending. Original unloaded-net and
clock-reference warnings remain in their reports; this is no FPGA workload run.

Fresh EDA SP2 passes all 131,072 binary phase/control combinations / 393,216
output comparisons against the original hierarchical fault policy, including a
compiled missing-sticky-error mutation rejected in READ. Seven geometries pass
105 native fault processes, emitted-queue capture/drain, original-register audits
and 116 debug waves. MMIO/DMA passes 112 complete frame captures, 42 fault cases,
21 abort/recovery cases, thirteen bit-identity planes and four compiled mutations;
all 74 waves and independent full frame/register audits pass.

All 329 Scala / 51 suites plus twelve preparation, 52 manager, 337 checkpoint
Python, 47,219 ASan/UBSan host assertions, FCFS/cut/queue/NASTI/endpoint/physical/
widget, complete snapshot/restore matrices and sixteen fresh bank/region scopes
with six independent waveform audits pass. Seven broad native source sets and
two snapshot owners were refreshed, with nine unchanged native receipts retained
under their original provenance. Peak native concurrency was two after Java
exited. The initial broad stale-source rejection remains in its original log.

Fresh exact-Rocket compilation still explicitly rejects FASED physical CE/
common-cut ownership. Full localhost image/P&R/AFI, complete simulator/memory/
timing/bridge/host/pre-FAME ownership, physical all-hart early/warm/outstanding/
late cuts and FPGA reference, paired complete zero-edge/finite/live CPU migration
beyond the trace and rolling hardware recovery remain pending. No hardware
matrix column advances. Reuse iteration194's localhost invocation and initialized
manager inputs; next work is production common-cut and all-four-queue ownership.

Managed worker startup failed before execution; only the central agent ran.
Initial FSM readout, runner import, Scala pointer and stale-source diagnostics
are preserved under `runs/aws-f2/iteration276/diagnostic-notes.json`. The initial
exploratory native/Java overlap is recorded there; later launch guards enforce
separation. Plans and initialized manager YAMLs retain entry hashes; no staging,
local commits, conda/PDF/archive edits or ASIC work occurred. Existing controller
checkpoints were published FireSim first (`a4874f20`), then Chipyard (`da224858`);
remote tips match. No new AFI or runtime was requested. See
[GitHub publication](github-publication.md). Current commands, source/receipt
bindings, per-cut frames, debug waves, resource/aggregate audit and individual
artifact catalog belong under `runs/aws-f2/iteration276/`. Final resource inventory
has no active tagged runtime, pending AFI or owned Java/Vivado job. The aggregate
source/receipt/register/routing/protected-input audit passes; the catalog binds
individual nonempty files. No delegated LLM work remains.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 275,
**in_progress; native-vector MMIO/DMA component verified**. See
[f2-native-capture-transport.md](f2-native-capture-transport.md).
The synthesized adapter streams the entire atomic native snapshot with explicit
full-word/tail descriptors, rejects reserved-bank aliases, drains responses on
abort and prevents new starts from overtaking physical release. Original native
write guards use a separate sequencer hold so their last edge matches the
physical root. The transport request remains the additional-owner freeze request.
Production Rocket ownership/admission and composite restore remain unsupported.

Final-source localhost Vivado 2025.2 F2-part synthesis maps all 1,666 register bits
to separate outputs, uses 2,597 LUTs, retains four SYNC gates / one falling-edge
mask and has zero combinational/latch loops. OOC setup/hold at the unchanged
140 MHz recipe frequency is −0.859/+0.073 ns. Setup and full-image timing closure
remain pending. Fresh EDA SP2 passes seven geometries through 6,656 bits, thirteen
bit-identity planes per healthy process, 112 complete frame captures, 42 fault
processes, 21 abort/recovery processes and four compiled mutations before the
relevant acknowledgement. All 74 debug waves remain present; independent manager
auditing reconstructs all 33 underlying register vectors in each ordinary wave
and checks every native word, descriptor, target label, frame CRC and source pin.

All 329 Scala / 51 suites plus twelve preparation tests, 52 manager tests,
337 checkpoint Python tests, 47,219 ASan/UBSan host assertions, FCFS/cut/queue/
NASTI/endpoint/physical/widget scopes and all sixteen fresh bank/region scopes
with six independent waveform audits pass. Nine affected native builds were
refreshed, nine exact unchanged receipts retained with original provenance;
peak concurrency was two, after large Java generation exited. Fresh exact-Rocket
compilation still explicitly rejects the FASED physical BUFGCE CE latch lacking
its production owner/common-low-phase binding. No hardware matrix column advances.

The read-only managed reviewer completed and was joined. Its masked restart-guard
and modulo-seven bit-alias findings are fixed with consumed-response checks,
thirteen identity planes and compiled missing-guard/permutation negatives.
Central review also fixed the one-edge-early native hold. Initial zero-manifest,
permission-loop, import/path-map and stale native-source refusals remain in their
original logs. The new verifier legitimately changes seven broad native source
sets; every affected scope was rebuilt without weakening the consumer. See
`diagnostic-notes.json`, `managed-review.json` and immutable selected receipts.

Both plans and initialized manager YAMLs retain entry hashes. No staging/local
commits, conda/PDF/archive edits or ASIC work occurred. Existing controller
checkpoints were published FireSim first (`63c777bf`), then Chipyard (`27037c99`);
remote tips match. Final AWS/native inventories contain no active tagged runtime,
pending AFI or owned Java/Vivado job; no instance or AFI was requested. Reuse
iteration194's localhost invocation and [github-publication.md](github-publication.md).
Complete production physical/common-cut/all-four-queue/transport/restore and
memory/timing/bridge/host/pre-FAME ownership, full localhost image/P&R/AFI,
physical all-hart cuts/reference, paired zero-edge/finite/live CPU migration beyond
trace and rolling hardware recovery remain pending. Commands, provenance,
per-cut frames, debug waves, final audit and artifact catalog belong under
`runs/aws-f2/iteration275/`. All delegated LLM requests finished before this
central response; only the central agent returns the required JSON report.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 274,
**in_progress; coordinated physical/native capture and reader drain verified in
components**. See [f2-native-state-capture.md](f2-native-state-capture.md).
The synthesized sequencer waits for the physical common-low-phase cut, all
additional freeze acknowledgements and idle native readers before atomically
staging the whole native vector. It grants bank access only after staging,
revokes new access before release, drains a real backpressured native response,
and releases the snapshot before the physical mask/local hold. Missing owners,
CE/cycle drift, unsafe sampling and command/borrow faults fail closed. Rejected
sampling commands preserve the previous payload/label. Readiness is independent
of attempted commands; every new register reaches the composite live readout.
Composite restore and production Rocket admission remain unsupported.

Final source-bound localhost Vivado 2025.2 synthesis for the F2 part passes:
1,189 owner bits / 575 LUTs, four default SYNC gates, one falling-edge mask and
zero combinational/latch loops. Representative owner parameters are 1036 bits /
3 gates / 2 owners; the emitted-queue integration is 1036 / 1 / 2 and retains two
RAMB primitives per queue and untouched sibling. These are OOC results, not a
routed full-image Fmax. Fresh SP2 VCS passes seven vector geometries (including
6656), 105 negative processes, seven pre-VCS receipt rejections and 113 independent
original-register waveform audits. All 114 new debug waves are retained. Four
actual emitted-queue cuts at component target labels 75/129/190/258 pass 180 bank
reads and 1,324 serial staging words while the raw vector changes 1,320 times.
A compiled readout fault stops at the first complete snapshot before any bank or
word acknowledgement. This is component evidence, not CPU acceptance.

All 329 Scala / 51 suites plus twelve preparation, 337 Python / 52 manager,
47,219 ASan/UBSan host assertions, sixteen fresh bank/region scopes, six independent
bank/shell waveform audits and retained queue/NASTI/widget/endpoint/physical/FCFS/
cut scopes pass. Full retained staging and complete staging/control restore
matrices pass, including their 68 / 147 debug waves. Seven stale native source
sets were rebuilt, nine immutable matching receipts retained; the sweep used at
most two native jobs after large Java generation exited. Current Rocket
compilation still explicitly rejects the FASED physical BUFGCE CE latch without
its production owner/common-low-phase binding. No full image, AFI, physical
checkpoint or paired CPU migration is claimed.

The managed review worker completed and was joined. Its rejected-SAMPLE retention
and coherently rehashed wrapper/model provenance findings are fixed and covered
by negatives. Native/VCS declaration/topology and vendor global-startup fixture
failures remain in original iteration-274 logs. Reset now spans unmodified vendor
startup and real gated reset edges, with complete original reset-state readback
before functional checking. Initially unknown queue selector bits remain verbatim
in the first diagnostic snapshot; no bits were masked or initialized through
backdoors. See `diagnostic-notes.json` and `managed-review.json` under this run.

Full production CE/common-cut and all-four-queue transport/restore, complete
simulator/memory/timing/host/pre-FAME ownership, localhost full image/P&R/AFI,
physical all-hart early/warm/outstanding/late cuts and reference, paired fresh
zero-edge/finite/live CPU migration beyond trace, and rolling hardware recovery
remain pending. No hardware matrix column advances. Reuse iteration194's existing
localhost invocation and initialized manager YAMLs. Plans/YAMLs retain entry
hashes; no staging/local commits, conda/PDF/archive edits or ASIC work. Existing
controller checkpoints were published FireSim first (`05014b60`), then Chipyard
(`82ebd43c`); remote tips match, with the read-only local tracking-ref warning
retained. Follow [github-publication.md](github-publication.md) for the next
controller-created checkpoint. Commands, immutable selections, final audit,
resource inventory and individual artifact catalog belong under
`runs/aws-f2/iteration274/`. The final aggregate audit passes, and independently
observed host/AWS inventories contain no active tagged runtime, pending AFI or
owned Java/Vivado job. No instance or AFI was requested this iteration. Only the central agent returns the JSON report.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 273,
**in_progress; complete native staging/control restore verified in components**.
See [f2-native-snapshot-restore.md](f2-native-snapshot-restore.md).
The opt-in raw-clock load restores every existing snapshot-owner bit: retained
payload, occupied, cut label and sticky errors. Hold and unsafe controls revoke
reads/borrowing before acknowledgement; invalid loads retain payload/label.
Qualified whole-owner restore preserves donor diagnostics and supports later
component execution. Default capture-only behavior and production admission
remain unchanged; this is not a complete queue or CPU restore owner.

Final current-source checks pass 329 Scala / 51 suites plus twelve preparation,
337 Python / 52 manager tests, 47,219 ASan/UBSan host assertions, all sixteen fresh
EDA bank/region scopes and six independent bank/shell waveform audits, plus all
retained queue/NASTI/widget/endpoint/physical/FCFS/cut scopes. Native F2-part OOC
synthesis retains all 1,107 bits in both capture-only and restore-enabled owners;
the standalone enabled owner uses 978 LUTs. Fresh SP2 VCS passes six geometries,
30 directed fresh restores and eight emitted/gated queue staging restores,
6,772 per-bit loads, 72 negative processes and 117 independent original-register
waveform audits. All 147 new restore debug waves and 68 retained staging waves
are present. Compiled restore-bit corruption stops at first full-state readback
before word acknowledgement. These are component results, not CPU acceptance.

Initial fixture selectors contain 112 unknown bits before any bank request.
Their original snapshots remain verbatim. Binary exports instead come from a
second atomic snapshot after legal reads finish, at the same frozen target cut;
every exported word is checked. No bits were masked or initialized through
backdoors. Seven stale native scopes were re-synthesized and nine exact matching
receipts retain their original provenance. At most two native jobs ran after
Java exited. The refresh classifier's original stale-source failure is retained;
all admitted receipts still pass the unchanged strict current-source consumer.

Fresh exact-Rocket compilation still refuses the FASED physical BUFGCE CE latch
without a synthesized capture owner/common-low-phase cut. All-four-queue
production snapshot/restore/transport, complete simulator/memory/timing/host and
pre-FAME ownership, full localhost image/P&R/AFI, physical all-hart early/warm/
outstanding/late captures, paired hardware-origin zero-edge/finite/live CPU
migration and rolling recovery remain pending. No hardware column advances.
Next: production common raw-clock/physical-cut and complete owner integration.

AWS/native/HDK/localhost preflight passes. Final AWS/AFI and independent localhost
host-/proc inventory show no active tagged runtime, pending AFI or owned Java/
Vivado job. No instance or AFI was requested. Host-view guards also retain actual
owned PID/cwd/argv observations. Direct OpenSSH inspection failed; the existing
FireSim Fabric setup works unchanged. Both plans and all four initialized YAMLs
retain entry hashes. No staging/local commits, conda/PDF/archive edits or ASIC
work. Existing controller checkpoints were pushed FireSim first (`c2632e80`),
then Chipyard (`acf29cfe`); remote tips match. The read-only tracking-ref warning
is retained. Managed spawn failed before execution; only the central agent ran
and no worker remains. Follow [github-publication.md](github-publication.md)
for publication of the controller's next local checkpoint.

Commands and immutable selections are under `runs/aws-f2/iteration273/`:
`verification-commands.json`, `*-selected.json`, final audit, artifact catalog,
`diagnostic-notes.json` and `remaining-blockers.json`. Complete Scala output is
`scala-attempt-gnoy_1qu`; native join is `native-refresh-_dhuicnf`; complete bank
run is `component-regressions/attempt-0blrtnc7`. Only the central agent returns
the JSON report.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 272,
**in_progress; atomic native queue-state staging verified in components**.
See [f2-native-state-snapshot.md](f2-native-state-snapshot.md).
`CheckpointNativeStateSnapshot.sv` samples the complete derived live vector and
cut label on one common raw edge before borrowing RAM readers. Indexed reads
retain that immutable payload; owner, freeze, busy-reader, cycle and overlapping
control faults revoke read/borrow permission before acknowledgement. All new
staging/control storage is exposed separately. Production clock, transport and
restore ownership remain incomplete; no FPGA capture image is admitted.

Final current-source checks pass 329 Scala / 51 suites plus twelve preparation,
337 Python / 52 manager tests, 47,219 ASan/UBSan host assertions, all sixteen
fresh EDA bank/region scopes and six independent waveform audits, and retained
queue/NASTI/widget/endpoint/physical/FCFS scope. New native OOC synthesis retains
1,107 staging/control bits and two RAMB primitives per selected queue and its
untouched sibling. Fresh source-bound SP2 VCS passes five vector geometries /
60 negative processes, four cuts of 28 actual emitted fields / 1,036 bits,
364 complete underlying queue reads and 360 additional gated-wrapper reads.
Each queue process verifies every one of seventeen staged words at each cut:
2,708 serial samples / 8,124 checks remain immutable through 2,707 live-vector
changes. A compiled semantic fault stops at the first snapshot before word ack;
all 68 new debug waveforms are retained. These are component results.

Seven global Python-source native scopes were re-synthesized; nine unchanged
receipts retain exact original provenance. At most two Vivado jobs ran, after
Java exited. Fresh native WriteXDCFile output supplies all regional fixtures,
including identity/unbound. Initial oracle-bound, receipt-schema, missing-XDC,
identity file-set and early artifact-fetch failures remain in original logs;
no test, sanitizer, source/ownership or constraint guard was relaxed.

Fresh exact-Rocket compilation still rejects the FASED physical BUFGCE CE latch
without a synthesized capture owner/common-low-phase cut. Retained regional
deficits, all-four-queue production staging/restore/transport ownership, full
localhost image/P&R/AFI, physical all-hart early/warm/outstanding/late captures,
paired hardware-origin zero-edge/finite/live CPU migration and rolling recovery
remain pending. No hardware acceptance column advances. AWS/native/HDK/localhost
checks pass; final inventory has no active tagged runtime, pending AFI or local
Java/Vivado job. No instance or AFI was requested. Both plans and all four
initialized manager YAMLs retain entry hashes. No staging/local commits,
conda/PDF/archive edits or ASIC work. Existing controller checkpoints were pushed
FireSim first (`f5bf5b62`), then Chipyard (`bf686818`); remote tips match, and the
read-only tracking-ref cache warning remains recorded. Managed worker startup
failed before execution; only the central agent ran and no worker remains.

Current commands and immutable selections are under `runs/aws-f2/iteration272/`:
`verification-commands.json`, `*-selected.json`, final audit, artifact catalog,
`diagnostic-notes.json` and `remaining-blockers.json`. Compiler output is
`scala-attempt-o79f5gwb`; final native join is `native-recovery-wxsj94q5` and the
complete fresh bank run is `component-regressions/attempt-z5fq_gcn`. Follow
[github-publication.md](github-publication.md) for the next controller checkpoint.
Only the central agent returns the JSON report.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 271,
**in_progress; synthesized derived queue-state taps and complete emitted-register observation verified**.
See [f2-synchronous-state-observation.md](f2-synchronous-state-observation.md).
Every added native synchronous reader/forwarding/shadow/endpoint register and the
implicit Old RAM data pipeline now reach a synthesized observation port. The
reduced queues expose fourteen fields / 518 bits each. Independent actual-Rocket
compiler auditing verifies all four queues: 56 fields / 6,656 bits and every
ancestor connection. Original StateIDs/selectors remain separate. The live vector
still has no complete atomic snapshot/restore owner or host transport binding.

Final current-source checks pass **329 Scala / 51 suites plus twelve preparation,
25 targeted Scala, 337 Python / 52 manager, 47,219 ASan/UBSan host assertions,
27 selected native OOC scopes and 26 EDA SP2 component scopes**. Native BLOCK
retains two RAMB primitives per selected queue and untouched sibling. Exact
Rocket ULTRA retains 16 URAM / zero LUTRAM. Fresh EDA queue execution passes
364 reads / four cuts and **185,836** added-state comparisons on both clock
phases, with full debug waves and two compiled faults stopped before ack.
All 24 coherent metadata/emitted-storage negatives reject. NASTI passes 72,000
compared cycles / sixteen negative processes. All retained bank/region, endpoint,
physical, waveform, host, FCFS and atomic-cut scopes remain covered.

Actual emission lowers the implicit data owner to `ram_r_data_pipe_0`; the
similarly named `ram_r_data` is a combinational wire. Native/EDA receipts now
bind every field to actual declared registers, account for the complete added
register set, and validate implicit-pipeline width, positive clock and sampling
equation. Source guards required seven native scopes to be re-synthesized after
verifier repairs; nine unchanged receipts retain exact current-source hashes.
No scope, sanitizer or owner guard was relaxed. All original parser/classifier,
wrong-oracle, nonunique fault-site and source-staleness failures remain in their
original logs/receipts. Small launch/count-check failures are also retained.

Fresh root generation still rejects the FASED physical CE/common-low-phase
owner. Regional generation retains 1,042 uncovered original entries and eight
live MMIO/DMA self-freeze conflicts. Generated target input IR is explicitly
reused by its immutable pin. Full localhost image P&R/AFI, active four-hart FPGA
cuts, paired hardware-origin zero-edge/finite/live migration and rolling hardware
recovery remain pending. No hardware acceptance column advances. Next: snapshot
these complete live vectors coherently before borrowing RAM readers, bind their
staging/transport/restore owners, and finish the remaining global clock/memory/
host/pre-FAME ownership; observing live words serially is not an atomic cut.

Current receipts/commands belong under `runs/aws-f2/iteration271/`:
`summary.json`, `verification-commands.json`, current `*-selected.json`, final
audit and artifact catalog. Full compiler output is `scala-attempt-3jhy2tyc`;
actual regional output is `rocket-region-production-wemukgis`. AWS/native/HDK/
localhost checks pass. Scoped inventory has no active tagged runtime, pending
AFI or local Java/Vivado job. No instance or AFI was requested. Both plans and
all initialized manager inputs retain entry hashes; no staging/local commits,
conda/PDF/archive edits or ASIC work. Existing controller checkpoints were pushed
FireSim first (`be2ca617`), then Chipyard (`8f693f91`); remote tips match. The
Chipyard local tracking-ref cache update failed read-only after remote success.
Follow [github-publication.md](github-publication.md) for the next checkpoint.
Managed worker startup failed before execution; only the central agent ran and
no delegated LLM request remains. Only the central agent returns the JSON report.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 270,
**in_progress; source-bound synchronous bank validation verified in components**.
See [f2-synchronous-bank-provenance.md](f2-synchronous-bank-provenance.md).
Each adapted bank now retains original New RAM/ordinary-bank provenance. The
factory reconstructs the ordinary bank; standalone validation reconstructs the
complete native reader, registered write-first forwarding, borrowed-read/shadow,
reset/reprime/control equations, selectors and canonical binding. Recomputed
hashes cannot admit changed equations or lost provenance. Generated RTL and the
version-2 binding remain unchanged; this adds no physical capture ownership.

Current-source checks pass 328 Scala tests / 51 suites plus twelve preparation
checks, targeted 24 Scala checks, 337 Python / 52 manager tests, 47,219 ASan/UBSan
host assertions, all retained native OOC scopes and fresh EDA SP2 scopes. The new
fault test rejects ten coherent equation corruptions and four provenance/selector/
policy negatives. Native BLOCK mapping retains two RAMB primitives in each of
two selected queues and their untouched sibling; exact Rocket ULTRA retains
16 URAM / zero LUTRAM. EDA queue execution passes 364 reads / four cuts and
compiled first-word rejection before acknowledgement; NASTI passes 72,000
compared cycles / sixteen negative processes. All bank/region, endpoint/staging,
physical, waveform, host, FCFS and atomic-cut scopes remain covered.

The fresh exact-Rocket root compiler still rejects the FASED physical CE latch/
common-low-phase owner. The actual regional diagnostic retains 11,110 functional
and three CE descriptors, 1,042 uncovered original entries and eight live MMIO/DMA
self-freeze conflicts. Input generated Rocket IR is explicitly reused by its
retained hash pin, rather than relabeled as regenerated. Derived queue pipeline,
complete clock/transport/reset/memory/host/pre-FAME owners, full localhost image
P&R/AFI, active four-hart FPGA cuts, paired zero-edge/finite/live migration and
rolling hardware recovery remain pending. No hardware acceptance column advances.

EDA source synchronization now excludes transient Git locks only inside root/
nested `.git` directories while retaining real metadata and other lock inputs.
Real rsync round trips pass. Initial source-state object equality, two actual
vanishing-index-lock transfers, the first glob's root-lock miss and the edited
waiting-shell launch failure remain in their original diagnostic logs; corrected
complete checks pass. No test, sanitizer or owner guard was relaxed.

Current receipts/commands belong under `runs/aws-f2/iteration270/`:
`verification-commands.json`, current `*-selected.json` and the final audit/catalog.
Full compiler output is `scala-attempt-cgskpv01`; actual regional output is
`rocket-region-production-_0jtb6p8`. Final scoped inventory has no active tagged
runtime, pending AFI or local Java/Vivado job. No instance or AFI was requested.
Both plans and all initialized manager YAMLs retain entry hashes. No staging,
local commits, conda/PDF/archive edits or ASIC work occurred. Existing controller
checkpoints were pushed FireSim first (`d3168060`), then Chipyard (`889b0ea6`),
and remote tips were independently checked; the latter push's local tracking-ref
cache update hit a read-only filesystem after remote success. Follow
[github-publication.md](github-publication.md) for the controller's next commit.
Managed worker startup failed before execution; only the central agent ran and
no delegated LLM request remains. Final physical/aggregate audits and the
nonempty local artifact catalog pass; use the hash-bound current selections.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 269,
**in_progress; synchronous native queue RAM inference and retained execution verified**.
See [f2-synchronous-queue-memory.md](f2-synchronous-queue-memory.md). Version 2
uses a physical Old/data-registered reader plus registered full-width collision
hit/data to preserve original New/write-first behavior. The hit includes actual
freeze-gated write enable, mask and current read/write address equality. Original
RAM ports and address StateIDs remain; derived readout/forwarding state still
lacks complete production capture/restore ownership.

Actual localhost Vivado passes strict BLOCK mapping: two RAMB primitives in each
of two selected reduced queues and their untouched sibling. The exact original
Rocket Queue_56 6144-by-512 ULTRA RAM passes with **16 URAM / zero LUTRAM / zero
BRAM**, 878 LUTs and 1,192 registers. Reduced fixture totals are 2,017 LUTs /
803 registers / six BRAM tiles. These are OOC component results, not complete
image P&R, timing closure, AFI construction or physical FPGA capture.

Final current-source checks pass **327 Scala tests / 51 suites plus twelve
preparation checks, 337 Python / 52 manager tests, 47,219 ASan/UBSan host
assertions, 27 native OOCs and 26 native-bound fresh EDA SP2 scopes**. Full
fixture exports are byte-identical to the independently source-bound targeted
six-test regeneration. Queue RTL passes 364 reads / four cuts, latched selectors,
backpressure, three reset-cancel phases, two premature releases, held release,
directed write-first collisions and running reset. A compiled first-word fault
stops frozen before acknowledgement; full debug waves and all thirteen metadata
negatives are retained. All legacy zero-edge/readback, continuation, waveform,
semantic/compiled corruption, FCFS and atomic-cut scopes remain covered.

Fresh exact-Rocket production retains 11,110 functional / three CE descriptors,
1,042 absent entries and eight live MMIO/DMA self-freeze conflicts. Whole-root
compilation still rejects the FASED BUFGCE latch/common-low-phase owner. Original
logical readout availability is not complete physical/host/semantic ownership.
All four active-hart hardware cuts, full localhost image P&R/AFI and execution,
paired FPGA-origin zero-edge/finite/live migration and rolling recovery remain
pending. No hardware acceptance column advances. Next bind complete physical
CE/common-cut, transport/reset/external-writer, remaining memory, host and
pre-FAME owners before image admission and deployment.

Commands and immutable receipts belong under `runs/aws-f2/iteration269/`:
`verification-commands.json`, current `*-selected.json`, `queue-resources.json`
and the final audit/catalog selections. Current full compiler output is
`scala-attempt-_nxougg7`; fresh production is `rocket-region-production-vj0cl9jq`.
V1's actual BLOCK/ULTRA inference failures are preserved as failures under
`shared-queue-native-h2aeyfc5` and `rocket-queue-ultra-native-25_5wrsy`, pinned by
`v1-superseded-attempts.json`. Keep the superseded compiler/source results separate.

Preserved development failures include ArraySeq/List annotation representation
roundtrip (exact public constructors recover all original bytes), original
FIRRTL source-location parser handling, and two aggregate-auditor schema fixes
for hash-pinned empty fixtures and native-referenced EDA inputs. Final independent
source/receipt/physical/protection/component audit passes; no acceptance check
was relaxed. Native concurrency stayed at most two and never overlapped Java.
All managed workers completed and joined. Final resource inventory has no active
tagged runtime, pending AFI or local Java/Vivado job; no instance/AFI was launched.
Existing iteration-268 checkpoints were published FireSim first (d3199ac8), then
Chipyard (20e9713f), and remote tips match. Plans and initialized YAMLs retain
entry hashes; no staging, commits, conda/PDF/archive edits or ASIC work occurred.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 268,
**in_progress; concrete shared trace-queue readout and independently rejected native RAM policy**.
The fresh exact-Rocket regional trial adds all twenty original Queue_56 owners:
11,110 functional plus three CE descriptors, 1,042 absent entries / 61,257 bits /
182 memories and eight mandatory live-transport freeze conflicts. Original
StateIDs, unselected siblings and concrete initialization/preservation/memory-model
owners are retained. See [f2-shared-queue-readout.md](f2-shared-queue-readout.md).
Descriptor availability does not establish native capture ownership.

Actual localhost Vivado 2025.2 rejects the new reduced queues' BLOCK policy:
instrumented q0/q1 fall back to LUTRAM, while untouched q2 uses two RAMB36E2s.
The strict primitive audit stops at host/q0 and publishes a failure receipt;
native_synthesis_passed/native_policy_accepted stay false. Rocket's original
ULTRA implementation and the twenty owners' 12,583,072 bits / four memories
remain physically unvalidated. Next implementation priority: synchronous native
memory-port access with retained responses and original pipeline preservation,
then complete production CE/common-cut/transport/memory/host/pre-FAME binding.

The complete Scala sweep passes 325 tests / 51 suites plus twelve preparation
checks. A separately source-bound four-test queue fixture regeneration avoids
public-port/flattened-child name collisions; only fixture boundary/resource and
bench bindings changed. Original full-sweep output remains untouched. Its
355 Scala source hashes match the fixture's 356 inputs minus that resource.
The narrow memory-clock fix proves validif guards against that same memory
port's enable; genuine gate/mux/cast/secondary clocks still reject.

Final retained Python (337), manager (52), ASan/UBSan host (47,219 assertions),
generated banks/widget, FCFS/atomic-cut and twenty-five positive native OOCs /
twenty-five fresh native-bound EDA SP2 scopes pass. Full legacy waveform,
zero-edge/readback, continuation and corruption checks retain their scope.
The separate EDA functional diagnostic of native-rejected queue RTL passes all
361 reads / four cuts / eight coherently rehashed metadata negatives and stops
a compiled first-word defect while frozen, before acknowledgement. Full debug
waves include original RAM-word aliases. This cannot grant native acceptance.

Receipts/raw backend commands are under runs/aws-f2/iteration268/; use
verification-commands.json and the *-selected.json pins. Current production is
rocket-region-production-wgm5t9bs/result.json. Reuse the initialized iteration194
localhost invocation; native concurrency remains at most two jobs and never
overlaps Java generation. Source-policy OOC retains negative 140 MHz setup/hold
estimates (-0.179/-0.074 ns), unconstrained I/O and no full-image timing closure.

Preserved failures: source-clock validif rejection and scoped interruption of
its now-stale first full sweep; initial HDK wrong-cwd setup; early aggregate
missing its full-Scala dependency; and emitted fixture port redeclarations/X
outputs. Fresh scoped recovery and complete affected checks pass. Failed native
memory-policy results remain failures and are independently audited explicitly.
All managed workers completed and joined; no delegated LLM work remains.

Full-image P&R/AFI, checkpoint-enabled F2 execution, all four active-hart cuts,
paired FPGA-origin zero-edge/finite/live migration and rolling hardware recovery
remain pending. Required hardware cuts are individually listed in the matrix;
no hardware column advances. No instance or AFI was launched. Existing controller
checkpoints were published FireSim first (5c796e00), then Chipyard (ab59c0eb);
both remote tips match. Plans and initialized YAMLs retain initial hashes;
no staging, local commits, conda/PDF/archive edits or ASIC work occurred.
Final independent source/receipt/protection/component audit passes; the local
artifact catalog contains individual nonempty files. Final scoped inventory has
no active tagged runtime, pending AFI or local Java/Vivado job.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 267,
**in_progress; retained widget staging recovery and complete iteration-266 regression recovery**.
The host session now explicitly retries interrupted reads of its own immutable
MMIO staging epoch. It revalidates freeze, cut, stream count, layout, descriptor
count and manifest before and after complete collection. Invalid observations
and attempted release revoke retry; foreign history survives. Sessions cannot
be copied/moved. See [f2-widget-shadow-recovery.md](f2-widget-shadow-recovery.md).

Final source passes **321 Scala tests / 50 suites plus twelve preparation,
337 Python / 52 manager tests, 25 native OOCs and 25 native-bound fresh EDA SP2
component scopes**. ASan/UBSan host executes 47,219 assertions: 739 safe retries /
81 unsafe rejections over every before/after MMIO interruption, one repeated
interruption and 26 invalid epochs (14 early / 12 final identity checks).
Actual three-gate Rocket source width 1242 is tested alongside 1169 and the
six-gate fixture's 1245; that last shape is not the full Rocket transport.

Iteration 266 stopped on a model-at-capacity error. Its unfinished opt-in
staging restoration now passes native synthesis and independent complete
fifty-register zero-edge readback in fresh EDA donor/restored processes. Both
profiles pass indexed continuation (312 total trace rows) and four negative
processes. Compiled saved-payload faults stop at canonical bit 759 while held,
with zero normal edges and no interface acknowledgement. Retained endpoint
24,000-cycle / adapter 72,000-cycle continuations, FCFS/atomic-cut, full debug
waves and physical corruption audits pass. All images here remain fixtures.

Fresh exact Rocket production still rejects physical CE/common-low-phase
ownership. Its regional diagnostic retains 11,090 functional / three physical-CE
readout descriptors, 1,062 uncovered entries and eight live-transport freeze
conflicts. The missing inventory includes 12,644,329 stored bits / 186 memories;
full functional DRAM and aggregate host/pre-FAME ownership are also incomplete.
See [f2-rocket-owner-deficits.md](f2-rocket-owner-deficits.md). No image is emitted.
Full localhost image P&R/timing/AFI, checkpoint-enabled F2 execution, active
all-hart hardware cuts, paired FPGA-origin zero-edge/finite/live migration and
rolling recovery remain pending. No hardware migration column advances.

Recovery commands and immutable receipts are under `runs/aws-f2/iteration267/`:
`verification-commands.json`, `*-selected.json`, `review-complete.json` and
`development-attempts.json`. Reuse iteration194's initialized localhost invocation.
Native generation/synthesis never overlap; native concurrency peaks at two.
The source-policy OOC retains negative 140 MHz setup/hold estimates of
-0.179/-0.074 ns with unconstrained I/O, not full-image timing closure.

Full-history worker startup failed; fresh-context managed review and follow-up
completed and are joined. The central agent integrated their complete/late
metadata-fault recommendation. No delegated LLM work remains. Existing
iteration-266 checkpoints were published FireSim first (`520a76c4`), then
Chipyard (`73fb6aa1`); remote tips match. Plans, initialized YAMLs and conda
inputs were not edited; no staging or local commits were made. The initial
manager integrity wrapper raced its second preflight selection; that error is
preserved and the sequenced recovery passes. The final independent integrity
audit passes; scoped inventory has no active F2 runtime, pending AFI or local
Java/Vivado job. The individual artifact catalog is under this iteration.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 265,
**in_progress; synthesized common-epoch widget/adapter restore and immutable evidence**.
The real widget now uses a shared endpoint builder preserving its eight original
locals and adapter/snapshot hierarchy. Its opt-in interface loads all 46 original
registers (758 canonical bits) on one accepted edge, suppressing AXI/MMIO/stream
handshakes, local updates and shadow access during hold/load. Epoch, owner,
reset and padding failures reject before restore writes. Production retains no
restore controls and all complete-image ownership guards. See
[f2-widget-epoch.md](f2-widget-epoch.md).

Final-source verification passes **320 Scala tests / 50 suites plus twelve
preparation checks, 337 Python / 52 manager tests, 23 native component OOCs and
23 native-bound fresh EDA SP2 component scopes**. ASan/UBSan host, FCFS/atomic-cut,
all retained debug waves and independent physical corruption audits pass.
The new integrated endpoint matrix covers 32/4 and exact Rocket 32/12 at six
explicit protocol cuts, with complete independent original-register readback,
every implemented bit loaded both ways, 24,000 continuation cycles and four
negative processes. Restored continuations execute 1,910 successful reads /
1,630 successful writes / 1,724 backend requests / 8,140 accepted stream frames.
Compiled localData faults stop at canonical bit 195 while held, before any normal
edge or interface acknowledgement. The retained adapter matrix separately passes
72,000 cycles / sixteen negative processes. These fixture images and epoch labels
are not FPGA-produced checkpoints or CPU live acceptance.

Exact Rocket endpoint OOC uses **700 LUTs / 519 raw positive-clock flops**;
486 bits belong to original endpoint registers, with shadow ownership separate.
Source-policy OOC retains 5,872 LUTs / 3,114 registers / six BUFGCEs and negative
140 MHz setup/hold estimates of -0.179/-0.074 ns with unconstrained I/O.
Full-image place/route and timing closure remain unestablished. Native concurrency
never exceeded two jobs and no native synthesis overlapped Java generation.

Fresh exact Rocket diagnostics retain **11,093 descriptors / 1,062 uncovered
entries / eight live-transport freeze conflicts** and reject the physical FASED
CE/common-low-phase owner. No deployable image is emitted. Complete transport,
stream, upstream/backend, host/reset, functional-memory and pre-FAME/common-cut
ownership remain pending. Full localhost image/P&R/AFI, checkpoint-enabled F2
execution, actual all-hart cuts, FPGA-origin paired migration/finite replay/live
clean RTL and rolling hardware recovery remain pending. No hardware migration
column advances. Next implementation target: concrete production owner/common-cut
binding, followed by complete localhost image generation and real F2 capture.

Iteration 264 correction: controller replay failed its final integrity audit
because preflight overwrote a pinned receipt. That receipt and failing audit
remain unchanged. New preflights use unique source/artifact-bound directories,
strict independent auditing and atomic success-only selection. Repeated real
AWS/native observations preserve prior pins; changed real inventories reject.
The final current-source/input/receipt/protection/resource integrity audit passes.
All 52 manager tests also retain immutable per-attempt logs and source bindings.

Preserved development failures include initial Scala imports/naming, the partial
Scala sweep restarted for exact 32/12 coverage, unreachable random cut selection,
EDA Python3.9 population-count compatibility, a missing copied metadata helper,
a duplicate inherited native source path and a positional testbench lookup.
The latter two now have order-preserving source deduplication, a closure
regression and named fixture paths. Complete recovery audited unchanged native
inputs and reran every affected closure; no test scope or sanitizer was removed.

Recovery receipts and raw commands are under `runs/aws-f2/iteration265/`:
`verification-commands.json`, `scala-selected.json`, `native-selected.json`,
`endpoint-native-selected.json`, `endpoint-eda-selected.json`,
`component-regressions/selected.json`, `retained-selected.json`,
`receipt-integrity-selected.json`, `diagnostics-selected.json`,
`physical-audit-selected.json`, `final-inventory-selected.json` and
`final-audit-selected.json`. The final inventory has no active tagged F2 runtime,
pending AFI or local Java/Vivado job. Reuse iteration194's initialized localhost
invocation; retain all native outputs and failed attempts. All three managed
workers, including the native-source recovery follow-up, completed and joined;
no delegated LLM work remains. Existing controller commits were published
FireSim first (`ce84b22e`), then Chipyard (`9595fad1`); remote tips match.
The Chipyard read-only local tracking-ref warning is retained. Plans, initialized
YAMLs and conda inputs were not edited; no staging or local commits were made.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 264,
**in_progress; synthesized opt-in complete NASTI adapter restoration**.
The adapter now holds both interfaces and atomically loads all 38 original
registers, rejecting geometry padding before mutation. Production keeps the
restore port absent and all image/ownership admission guards closed. See
[f2-nasti-restore.md](f2-nasti-restore.md).

Final-source verification passes **319 Scala tests / 49 suites plus twelve
preparation checks, 336 Python / 45 manager tests, twenty-one native OOC and
twenty-one native-bound fresh EDA SP2 component scopes**. ASan/UBSan host,
FCFS/atomic-cut, all retained waveform and physical corruption audits pass.
The new adapter matrix covers four geometries including exact Rocket 32/12,
six protocol cuts each, independent complete original-register zero-edge
readback and **72,000** cycle comparisons in separate donor/restored processes.
Fresh continuations execute **3,580 backend reads / 2,956 writes / 6,536 responses /
6,792 request stalls**, with matching donor counts and successful read/write
coverage in every case. Sixteen negative processes reject malformed/semantic
images and compiled loader defects; independent original-register waves find
the first compiled defect at canonical responseData bit 426 before releasing
either interface. All-slot padding, reset, no-hold and full-state payload sweeps
pass. Full component debug waves and per-cut hashes/commands are retained.

Exact-Rocket adapter OOC uses **289 LUTs / 258 registers**; all original storage
stays on the raw positive clock. The physical-widget fixture retains **2,766
LUTs / 1,978 registers / 1,040 raw shadow registers** and passes six component
cuts / 240 complete word reads / 65,361 checks / 3,851 stalls. Source-policy
OOC remains 5,872 LUTs / 3,114 registers / six BUFGCEs, with negative 140 MHz
setup/hold estimates **−0.179/−0.074 ns** and unconstrained I/O. Full-image
P&R/timing closure is unestablished. Java generation/emission finished before
native synthesis; native concurrency never exceeded two.

Fresh ordinary Rocket production still rejects the FASED physical CE/common-cut
owner. The regional/local diagnostic retains **11,093 descriptors / 1,062
uncovered entries and eight live-transport freeze conflicts**, emits no image
and grants no adapter ownership exemption. Complete transport/stream/parent,
upstream AXI/backend response, reset/host, functional DRAM and pre-FAME/common-cut
ownership remain pending. Full local image P&R/AFI, checkpoint-enabled F2
deployment, active all-hart hardware cuts, independent FPGA-origin Level-1/
Level-2 migration, finite replay, sustained live CPU shadowing and rolling
hardware recovery remain pending. Hardware migration columns remain pending.

Recovery: `verification-commands.json`, `scala-selected.json`,
`nasti-native-selected.json`, `nasti-eda-selected.json`, `native-selected.json`,
`component-regressions/selected.json`, `retained-selected.json`,
`physical-native-selected.json`, `physical-eda-selected.json`,
`physical-audit-selected.json`, `rocket-region-probe-selected.json`,
`nasti-owner-selected.json`, `source-policy-resources-selected.json`,
`final-inventory-selected.json` and `final-audit-selected.json` under
`runs/aws-f2/iteration264/`. The final independent current-source, native-input,
receipt, protection and resource audit passes. Reuse iteration194's initialized
localhost invocation; preserve every native output and historical failed attempt.

A fresh-context managed review recovered the initial delegation startup failure
and found a test-stimulus defect: low-bit LCG correlations made every randomized
continuation request malformed. The central agent replaced it with xorshift32,
explicit mixed legal/malformed traffic, master VALID/payload retention and
assertions under backpressure, and mandatory successful transaction counters.
Final receipts use the corrected source. Initial checks, the pre-initialization
wave-auditor correction, removed extra idle edge and raw-SSH environment failure
are preserved in `development-attempts.json`; none is relabeled final evidence.
The sole read-only worker completed and is joined; all tool sessions are joined.

Initialized AWS/manager/Vivado 2025.2/F2 HDK/Fabric localhost checks pass. Final
scoped inventory has no active tagged F2 runtime, pending AFI or Java/Vivado job;
none was requested. Existing controller commits were published FireSim first
(`85c6a241`), then Chipyard (`b63b1bef`), and independent remote tips match. The
read-only Chipyard tracking-ref warning is retained. Plans and initialized YAMLs
retain entry hashes; no staging, local commits or conda edits.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 263,

**in_progress; complete NASTI adapter shadow observation and runtime layout binding**.
The actual widget now samples all 38 original adapter registers atomically with
its transport controls/eight parent locals, while MMIO/DMA stay live. Layout 2
adds 530 canonical adapter bits, with bounded zero-extended address/ID slots.
Read-only layout/version and exact-bit-count MMIO reject stale driver layouts
before staging mutation. This is an observation, not a restore owner or a
complete hardware checkpoint. See [f2-nasti-shadow.md](f2-nasti-shadow.md).

Final-source Scala passes **319 tests / 49 suites plus twelve preparation
checks**, including complete low-FIRRTL adapter register enumeration at 8/1,
32/4 and 64/64 widths. Final fresh EDA retained checks pass **336 Python tests**,
all three adapter geometries (9,366 full-state comparisons / 9,000 random traffic
steps), 130 standalone captures / 4,992 word reads, compiled adapter/staging
corruptions and independent shadow waves. ASan/UBSan passes **1,890 host checks**,
four captures and thirteen failure/recovery cases. FCFS and atomic-cut checks pass.
Fresh exact Rocket diagnostics retain **11,093 descriptors / 1,062 uncovered
entries and eight live-transport conflicts**. An independent audit maps all 38
actual adapter StateIDs/native renames (258 original bits / 272 padding bits) and
rejects seven corrupted ownership descriptions without granting restore ownership.

Final verification also passes **seventeen native OOC and seventeen fresh
native-bound EDA SP2 component scopes**, all six retained independent waveform
audits, physical shadow-wave reconstruction and eight rehashed physical evidence
corruptions. The physical fixture passes **six component cuts / 240 complete
word reads / 65,361 checks / 3,851 stalls**, with reset recovery to cycle 96.
Compiled adapter and first-word staging defects reject independently; fixture
labels are not FPGA/CPU workload cuts. The physical widget uses **2,766 LUTs /
1,978 registers**, including **1,040** audited raw positive-edge shadow registers.
Source-policy OOC uses 5,872 LUTs / 3,114 registers / six BUFGCEs, with negative
140 MHz setup/hold estimates **−0.179/−0.074 ns** and unconstrained I/O. No full
image timing closure is established.

Recovery: `verification-commands.json`, `scala-selected.json`,
`native-selected.json`, `component-regressions/selected.json`,
`retained-selected.json`, `physical-native-selected.json`,
`physical-eda-selected.json`, `physical-audit-selected.json`,
`rocket-region-probe-selected.json`, `rocket-composition-audit-selected.json`,
`probe-audit-selected.json`, `nasti-owner-selected.json`,
`ownership-gap-summary.json`, `source-policy-resources-selected.json`,
`final-inventory-selected.json` and `final-audit-selected.json` under
`runs/aws-f2/iteration263/`. Final independent source/receipt/protection/resource
integrity audit passes. The fresh ordinary production check still rejects the
FASED physical CE/common-cut owner; the regional/local check still rejects all
eight self-freezing locals and emits no connected image.

Preserved development attempts include the initial Scala import error, the
explicitly terminated/joined pre-version full Scala run, pre-version EDA checks
and a failed native sweep with three missing connected-XDC preparation failures.
Recovery executes the actual native `WriteXDCFile` transform for all four
connected constraint sets (`emit-connected-xdc.py`), then `recover-local.sh`
validates and retains thirteen unchanged current-turn native receipts and reruns
all three failed scopes. Original failures are unchanged. Do not use the initial
`verify-local.sh` as a complete recipe: follow `verification-commands.json` and
`recover-local.sh`. Java generation/emission and synthesis never overlap; native concurrency
never exceeds two. Keep this order on subsequent iterations.

Initialized AWS/manager/Vivado 2025.2/F2 HDK/Fabric localhost checks and all 45
manager tests pass. Final scoped inventory records no active tagged F2 runtime,
pending AFI or native Java/Vivado process; none was requested. Existing controller
commits were published FireSim first (`1cdecc7b`), then Chipyard (`74c55cee`), with
independent remote tips matching. The Chipyard read-only tracking-ref warning is
retained. Plans and initialized YAMLs retain their entry hashes; no staging,
local commits or conda edits. Managed delegation failed before startup; the
managed tree contains only the central agent, and every tool session is joined.

Complete transport/stream/staging/reset/host restore ownership, functional DRAM,
pre-FAME/common-cut mapping, full local P&R/AFI, actual all-hart FPGA cuts,
zero-edge/finite/live paired CPU migration and rolling FPGA recovery remain
pending. Do not mark hardware acceptance from component results.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 262,
**in_progress; synthesized live-widget shadow MMIO and host observation/recovery**.
The actual CheckpointCaptureWidget now atomically copies its versioned source
control vector and eight original local registers into an immutable raw-clock
MMIO bank. Capture requires an acknowledged coordinator cut with the exact
label, every declared owner present/frozen and, in physical mode, the matching
post-stop sampler. MMIO/DMA continue during readout. The generated header binds
layout/offsets; the host session checks selectors, padding and both cut labels,
retains freeze on failures and explicitly discards uncertain writes. Existing
foreign staging history is preserved. See
[f2-live-widget-shadow.md](f2-live-widget-shadow.md).

Final verification passes **317 Scala / 48 suites plus twelve preparation tests,
336 checkpoint Python / 45 manager tests, seventeen native OOC and seventeen
source-matched fresh EDA SP2 component scopes**, retaining ASan/UBSan host, FCFS
and atomic-cut checks. All six retained independent waveform audits and the new
widget shadow waveform audits pass. Host ASan/UBSan executes **1,774 checks**, four
successful shadow reads and eleven failure/recovery cases. Both concrete widths
exercise **130 standalone captures / 2,816 word reads**. The actual MMIO widget
checks thirty retained word reads; the physical widget checks **six component
cuts / 144 complete word reads / 43,233 checks / 2,459 stalled cycles**, with
reset recovery to target cycle 96. A separately compiled staging defect stops at
component cut 42 / word 0 with AXI read-ready low. These are component labels,
not CPU or FPGA workload cuts.

Native physical-widget OOC uses **2,641 LUTs / 1,661 registers**. Its **811**
shadow registers are all on the ungated positive clock: 712 saved bits, 64 label
bits, 32 index bits, one valid bit and two native index replicas. The source-policy
component uses 5,714 LUTs / 2,757 registers / six BUFGCEs; 140 MHz OOC setup/hold
estimates remain **−0.172/−0.074 ns**, with unconstrained I/O. No full-image timing
closure is established. Independent physical source/native/EDA/frame/debug audit
and eight rehashed evidence corruptions pass; identity-header reconstruction and
all sixteen rehashed identity corruptions pass. Final independent current-source,
receipt, waveform, protected-input and resource integrity audit passes
(`final-audit-selected.json`).

Fresh exact Rocket diagnostics retain **11,093 descriptors / 1,062 uncovered
functional entries**, including four new staging registers. Connection still
rejects the eight original self-freezing widget locals. Ordinary production
compilation still rejects the FASED physical CE owner/common-cut contract. No
image is emitted or ownership exemption added. Complete transport/adapter/stream,
reset/external writer, functional DRAM, bridge/host and pre-FAME ownership and
restore mapping remain required. Full localhost P&R/AFI, real all-hart active cuts,
paired FPGA-origin zero-edge/finite/live migration beyond the recorded trace,
CPU debug waves and rolling FPGA recovery remain pending.

Recovery: `verification-commands.json`, `scala-selected.json`,
`rocket-region-probe-selected.json`, `rocket-composition-audit-selected.json`,
`probe-audit-selected.json`, `native-selected.json`, `component-regressions/selected.json`,
`retained-selected.json`, `physical-native-selected.json`,
`physical-eda-selected.json`, `physical-audit-selected.json`,
`source-policy-resources-selected.json`, `final-inventory-selected.json` and
`final-audit-selected.json` under `runs/aws-f2/iteration262/`. Original stale-JVM,
premature/mis-mapped EDA and old-header-audit failures remain in
`development-attempts.json`. Native recovery retains fourteen passing current-turn
receipts only after exact current source/input/artifact validation and reruns both
failed/stale scopes; original receipts are unchanged. The final retained EDA run
uses stable full Scala inputs and corrected manager-to-EDA path mapping.

Initialized AWS, Vivado 2025.2/F2 HDK and Fabric localhost checks pass. Native
concurrency never exceeds two, with no large Java/synthesis overlap. Final scoped
inventory records no active tagged F2 runtime, pending AFI or native Java/Vivado
job; none was requested. Reuse iteration194's initialized localhost invocation.
Existing controller checkpoints were published FireSim first (`20a41f34`), then
Chipyard (`7e8b26e7`); independent remote tips match. The Chipyard read-only
tracking-ref warning is retained. Plans and initialized YAML entry hashes remain
unchanged; no staging/local commits or conda edits. Managed delegation failed
before startup; no worker exists, and every central tool session is joined.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 261,
**in_progress; local ancestor/region readout composition and live-transport guard**.
`NativeCheckpointRegions.generate(..., shellTargets=...)` now reconstructs local
ancestor banks alongside disjoint native child regions. Exact Rocket reconstructs
**11,093 descriptors / 1,058 uncovered original functional entries**, including
181 FPGATop and two F1Shim original local owners. Connection explicitly rejects
**eight inlined CheckpointCaptureWidget owners** whose freeze would stop the same
MMIO/DMA stream required to drain capture. The guard follows original registered-
widget identity through actual native storage mappings, retains
`transport-freeze-conflicts.json` and emits no connected production image.
Independent source auditing checks local hold equations/selectors and all four
concrete original/composed hart RF memory owners and shapes. See
[f2-shell-region-routing.md](f2-shell-region-routing.md).

Full final-source validation passes **316 Scala tests / 47 suites plus twelve
preparation tests, 336 checkpoint Python / 45 manager tests, sixteen native OOC
and sixteen fresh EDA SP2 scopes**, with ASan/UBSan host, FCFS and atomic-cut
checks retained. All **six independent waveform audits** pass. The mixed
component passes **8,452 checks / four component cuts / 288 reads / 864 stalls**.
Native OOC uses **2,165 LUTs / 1,128 registers**, with 405 audited raw-clock state
registers and four original gates plus two generated root-mask gates. Eight
rehashed corruptions reject. Independent waves check 1,672 healthy falling-edge
samples, including 1,447 frozen samples. Separate compiled CE and local-payload
defects retain their exact source/log/waves. The local defect stops at fixture
cycle 36 / first local word 64 with freeze held and acknowledgment low. These
are component labels, not CPU cuts. No full-image timing closure is claimed.

Fresh initialized AWS/manager, native Vivado 2025.2/F2 HDK and Fabric localhost
checks pass. Native synthesis followed Java generation and peaked at two jobs.
Final resource inventory records no active tagged F2 runtime, pending AFI or
native Java/Vivado job; no new instance or AFI was requested. Complete independent
source/receipt/protection/resource/component auditing passes. Existing controller
checkpoints were published FireSim first (`0feb16b3`), then Chipyard (`38979b24`);
independent remote tips match. The read-only Chipyard tracking-ref warning is
retained. Both plans and initialized manager YAMLs retain entry hashes. No
staging/commits or dirty conda edits. Two managed spawn attempts failed before
startup; no worker was created and all LLM work remained central.

Recovery: `verification-commands.json`, `scala-selected.json`, `native-selected.json`,
`rocket-region-probe-selected.json`, `rocket-composition-audit-selected.json`,
`probe-audit-selected.json`, `component-regressions/selected.json`,
`shell-regions-wave-selected.json`, `final-audit-selected.json`,
`final-inventory-selected.json`, `development-attempts.json` and `delegation.json`
under `runs/aws-f2/iteration261/`. Original Scala syntax/type/equality diagnostics,
the interrupted stale-source exploratory JVM, source-info audit/parser repair,
standalone OpenSSH key failure (Fabric/plain manager inventory succeeds) and
fault-source provenance correction are preserved. No failed or interrupted
attempt is final verification. Follow [github-publication.md](github-publication.md).

Next: explicit atomic ownership of the eight live widget locals and opaque
transport, 1,058 remaining original raw/shared entries, common cut/reset/external
writers, functional DRAM, bridge/host/pre-FAME and added bank/router/control state.
Full localhost image/P&R/AFI, active all-hart early/warm/outstanding/late FPGA
captures, paired complete zero-edge/finite/live continuation beyond the trace,
full CPU debug waves and rolling hardware recovery remain required. Reuse
iteration194's initialized ExternallyProvisioned localhost invocation.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 260,
**in_progress; enclosing-module banked readout and annotation ownership fix**.
`NativeCheckpointShellStateAccess` banks local storage without replacing or
freezing original children. Separate exact-Rocket invocations reconstruct
**181 FPGATop + two F1Shim = 183 original owners**. These selectors are not yet
composed with the registered regional widget; the production manifest still
retains **1,241 uncovered functional entries and one unsupported transport
owner**. No complete image or FPGA capture is claimed. See
[f2-shell-state-access.md](f2-shell-state-access.md).

Independent review found and fixed nonlocal annotation broadening on unchanged
shared children. Source annotations now retain their exact vector/order/targets
except invalidated CombinationalPath caches. Validation uses distinct temporary
per-execution identities without applying translated copies. Nine focused tests
pass, including independent left/right initialization files, true overlap
rejection, caller-rehashed changes, child-clock rejection and all four original
Rocket hart register-file model annotations. Full final-source Scala passes
**311 tests / 46 suites plus twelve preparation tests**. Independent exact-source
and nine rehashed metadata audits pass. All **336 Python / 45 manager tests,
fifteen native synthesis scopes and fifteen fresh source-pinned EDA SP2 scopes**
pass, retaining ASan/UBSan host, FCFS and atomic-cut checks. All five independent
waveform audits pass. The new shell fixture uses **122 LUTs / 163 registers**
and rejects eight rehashed corruptions. Its native-bound VCS run passes
**4,280 checks / 69 reads / 347 stalls / four component cases**. Independent
waves retain 649 healthy samples, including 488 frozen samples; the compiled
payload defect stops at the first word with local cycle 7, freeze held and no
response acknowledgment. Case label 11 is a fixture identifier, not a CPU cut.
Retained source-policy OOC timing remains −0.031/−0.074 ns at 140 MHz with
unconstrained I/O; no full-image timing closure is claimed.

Fresh AWS/manager/Vivado 2025.2/F2 HDK/localhost SSH preflight passes. Existing
controller checkpoints were published FireSim first (`c5afd207`), then Chipyard
(`b319db32`); independent remote tips match. The read-only Chipyard tracking-ref
warning is retained. Plans and initialized YAMLs remain protected; no local
staging/commits. All three managed workers completed. Native synthesis followed
Java generation and peaked at two jobs. Final scoped inventory records no active
tagged F2 runtime, Java/Vivado job or new/pending AFI. Final independent source,
receipt, debug-wave, resource and protected-input integrity audit passes.

Recovery: `verification-commands.json`, `scala-selected.json`,
`native-selected.json`, `component-regressions/selected.json`,
`rocket-shell-audit-selected.json`, `shell-wave-selected.json`,
`final-audit-selected.json`, `final-inventory-selected.json`,
`development-attempts.json` and `delegation.json` under
`runs/aws-f2/iteration260/`. Original source-annotation decoding, stale-negative,
EDA import-path and VCS monitor/debug failures and their repairs are preserved. Complete MMIO/DMA-safe common-cut,
raw subtree/shared-definition, memory/host/pre-FAME and added bank/router/control
ownership, full localhost image/P&R/AFI, active all-hart physical cuts and paired
zero-edge/finite/live/rolling migration remain required. Reuse iteration194's
initialized ExternallyProvisioned localhost invocation.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 259,
**in_progress; exact Rocket regional compiler/widget/host identity hookup runs**.
The opt-in compiler probe now reconstructs and connects the actual Rocket DUT
and FASED regions through the registered widget. Its generated transport digest
and host constructor bind **10,910 descriptors / three original physical CE
slots**, MMIO base **0x200** and CPU stream **4**. The final exact-recipe run
reaches `identity_bound_incomplete_image_guard_required`; the existing image
emission guard then rejects. The manifest retains **1,241 uncovered functional
entries and one unsupported transport owner**. No checkpoint image or hardware
capture is claimed. See [f2-region-compiler-probe.md](f2-region-compiler-probe.md).

The probe resolves constant-generated metadata before recording inline history.
Its regional-only v3 inline producer also resolves native output Block/type/flow
metadata before its receipt, requiring identical FIRRTL, annotations and storage.
Strict regional AST comparison remains unchanged. A probe-only wrapper uses the
documented retaining host-clock API and validates the original scalar input;
the exact compiler retains `~F1Shim|FPGATop>clock`. Default native wiring and v2
compilation remain unchanged. Durable hashed diagnostics survive image rejection.
All **36 focused checks / five suites**, **302 full Scala tests / 45 suites**
and all **twelve preparation tests** pass on the final source. All **336 Python /
45 manager tests**, **fourteen native synthesis scopes** (two-job peak) and
**fourteen fresh source-pinned EDA SP2 scopes** pass, retaining ASan/UBSan host,
FCFS and atomic-cut checks. All four independent waveform audits and nine
fully rehashed metadata negatives pass. Native source-policy OOC resources are
5,276 LUTs / 1,979 registers / six BUFGCEs; 140 MHz setup/hold −0.031/−0.074 ns
with unconstrained I/O establishes no full-image timing closure.

Earlier exact trials exposed `LoadMemWidget` block nesting (317→437 statements)
and consumption of the native clock-source label. Both fixes retain their actual
producer history; no annotation or owner acknowledgement was invented. Two
partial Scala sweeps were deliberately interrupted and joined before any native
sweep; the complete final-source rerun supersedes them. Original failures,
parser/receipt repairs and logs remain under `runs/aws-f2/iteration259/`.

Complete production reset/external-writer/common-cut, functional-memory/timing,
bridge/host/pre-FAME and added router/mask/control/transport ownership or checked
exclusion/restore, full localhost image/P&R/AFI, all-hart physical cuts and paired
zero-edge/finite/live/rolling migration remain required. Reuse the initialized
manager inputs and iteration194's ExternallyProvisioned localhost invocation.

Fresh AWS/manager/native HDK/Vivado/Fabric setup passes. Final inventory has
no active tagged F2 runtime or local Java/Vivado job and no new AFI request.
All managed workers finished and their results were integrated. Protected plans
and four initialized YAMLs retain their original hashes; both indexes remain
unstaged. Existing controller checkpoints were published FireSim first
(`4f6fafb3`), then Chipyard (`d26230cf`); remote tips match. Chipyard's read-only
tracking-ref warning is preserved. The loop owns new commits and publication.

Recovery: `verification-commands.json`, `scala-selected.json`,
`native-selected.json`, `retained-selected.json`, `component-regressions/selected.json`,
`probe-audit-selected.json`, `final-audit-selected.json`, `development-attempts.json`
and `delegation.json` under `runs/aws-f2/iteration259/`. The actual successful
compiler diagnostic is `rocket-region-production-2xpokng1/`; its durable status,
source/descriptor/identity manifests and original compiler rejection log are
retained. Final independent source/receipt/resource/wave audit passes. No
physical capture, CPU migration or complete FPGA image is claimed.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 258,
**in_progress; ordered whole-host regional source policy verified as a component**.
`ReservedCheckpointInventory.forReservedWidgetSource` derives and binds typed
storage contracts and inert compiler context in original order from the actual
post-inline host. It checks pre-inline context before coalescing can hide
identical options, retains the full original/opaque-owner identity and preserves
the legacy permission. Regional generation/connection validate this permission,
retain compiler context and check the complete host/generated storage union.
See [f2-region-source-policy.md](f2-region-source-policy.md).

Read-only review found an existing unknown-owner gap: unchanged shared definitions
can lose executions to specialized banks or gain new mask-gate executions.
Compiler and independent auditor now compare concrete execution-path sets as well
as definition bodies. New negatives cover both cases. The source-policy audit
reconstructs all 152 original annotations (119 typed storage, 33 retained) into
153 connected annotations; 550 original functional entries and the opaque
transport owner remain uncovered. Nine compiler rejection cases and six Python
adversarial tests retain exact source/context and execution coverage contracts.

Full **287 Scala / 43 suites plus twelve preparation tests, 336 Python / 45
manager tests, fourteen native and fourteen fresh source-pinned EDA SP2 scopes**
pass, retaining ASan/UBSan host, FCFS and cut checks. The new source-policy
component passes **8,157 checks / four cuts / 272 words / 1,716 stalls**. Its
independent waves retain 4,064 healthy frozen samples and stop the actual compiled
payload defect at **cut 81 / word 32 / entry 5 / payload byte 42**, with both
counters held and no release. Retained bound identity has twenty generated-host
sanitizer checks; retained multi-region execution and all four independent wave
audits pass. Native source-policy OOC resources are **5,276 LUTs / 1,979 registers /
six BUFGCEs**; 140 MHz setup/hold −0.031/−0.074 ns with unconstrained I/O establishes
no full-image timing closure. All twenty rehashed connection mutations still reject.

The initial full Scala sweep was deliberately interrupted (exit 130) for the
review fix; the complete final-source rerun passes. Original logs, the corrected
ad hoc resource-field lookup and development history remain in
`runs/aws-f2/iteration258/development-attempts.json`. Native synthesis waited for
the large Java sweep and peaked at two jobs. EDA returned all artifacts before
the final independent source/receipt/resource/wave audit passed. Recovery files
include `verification-commands.json`, `native-selected.json`,
`component-regressions/selected.json`, `region-source-policy-wave-selected.json`,
`source-policy-resources-selected.json`, `final-audit-selected.json` and
`remaining-blockers.json` under that invocation.

The fresh exact-Rocket compiler still rejects the FASED physical CE/common-low-
phase-cut owner. Production source-context hookup and complete enclosing reset/
external-writer/memory/timing/bridge/host/pre-FAME ownership, router/mask/control
capture or checked exclusion/restore, full localhost image/P&R/AFI and all-hart
FPGA cuts and paired CPU zero-edge/finite/live/rolling migration remain pending.
No checkpoint-enabled image or FPGA-origin capture is claimed. Reuse
iteration194's ExternallyProvisioned localhost invocation and initialized inputs.

Fresh AWS, native Vivado 2025.2/F2 HDK and manager/Fabric localhost checks pass.
The final scoped inventory records no active local Vivado build or tagged F2
runtime and no new AFI request. Existing controller checkpoints were published FireSim first
(`3ec3d925`), then Chipyard (`c07853db`); remote tips match. Chipyard's read-only
local tracking-ref update warning is preserved. Plans and all four initialized
manager YAMLs keep their entry hashes; no staging or local commits. Managed
full-context worker startup failed before execution; a read-only reviewer started
with no inherited history, returned the execution-set finding, rechecked the fix
and finished. All delegated work is joined. Follow
[github-publication.md](github-publication.md) for the next controller checkpoint.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 257,
**in_progress; shared regional transport/host identity verified as a component**.
`NativeCheckpointWidgetIdentity.bindRegions` reconstructs the complete regional
network and binds its combined descriptor digest to the actual reserved transport
and registered host constructor. The shared implementation preserves selectors,
MMIO/stream allocation, digest byte order and owner metadata. Only one manifest
parameter and its registered header change. The unsupported transport owner,
550 uncovered functional entries and all image/restore guards remain explicit,
including after annotation removal. See
[f2-region-widget-identity.md](f2-region-widget-identity.md).

Full **285 Scala / 43 suites plus twelve preparation tests, 330 Python / 45
manager tests, thirteen fresh native and thirteen source-pinned EDA SP2 scopes**
pass, retaining ASan/UBSan host, FCFS and cut checks. The bound regional fixture
passes **8,157 checks / four component cuts / 272 words / 1,716 stalls**, plus
**20 generated-host sanitizer checks**. Twelve rehashed identity corruptions and
twenty retained connection corruptions reject. Independent bound/unbound waves
retain 4,064 healthy frozen samples each and stop the compiled payload defect at
**cut 81 / word 32 / entry 5 / payload byte 42**, with both counters held and no
release. The retained multi-region wave audit also passes. Native bound OOC
resources are **5,424 LUTs / 1,980 registers / six BUFGCEs**; 140 MHz setup/hold
−0.031/−0.074 ns with unconstrained I/O establishes no timing closure.

Initial focused immutable-descriptor compile and AnnotationSeq assertion failures
remain in `development-attempts.json`; corrected full checks pass. One EDA input
sync stopped before VCS because a temporary Git index.lock vanished; the unchanged
command retried successfully without exclusions. The invocation-only multi-region
wave selector was repaired before execution to consume the complete fresh receipt
index. Recovery receipts and final independent source/receipt/wave audit are under
`runs/aws-f2/iteration257/`, including `verification-commands.json`,
`final-audit-selected.json`, `native-selected.json`, `remaining-blockers.json`,
`component-regressions/selected.json` and `region-identity-wave-selected.json`.

The fresh exact-Rocket compile still rejects the FASED physical CE/common-low-phase
cut owner. Production source-context projection, complete enclosing memory/reset/
external-writer/bridge/host/pre-FAME ownership, added router/mask/control capture
or checked exclusion/restore, localhost full image/P&R/AFI, all-hart active FPGA
cuts and paired CPU zero-edge/finite/live/rolling migration remain pending. No
checkpoint-enabled image or FPGA-origin checkpoint is claimed. Reuse
iteration194's localhost invocation and the initialized manager inputs.

Fresh AWS, native Vivado 2025.2/F2 HDK and manager/Fabric localhost checks pass.
EDA's capacity probe has about 2 TiB available; no history was removed or newly excluded.
Final scoped inventory contains no loop runtime, active native job or new AFI
request. Existing controller checkpoints were published FireSim first (`49371e0d`), then
Chipyard (`74cc5778`); remote tips match. Chipyard's successful push also reported
a read-only local tracking-ref update; its original log is retained. Plans and
initialized manager inputs retain their entry hashes; no agent staging or local
commits. Managed worker startup failed before execution; the central agent ran
all work and no delegated worker remains. Follow
[github-publication.md](github-publication.md) for the controller's next checkpoint.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 256,
**in_progress; existing widget connected to disjoint native regions**.
`NativeCheckpointRegionWidgetGraft` routes twenty typed signals between the
common-root readout and the actual reserved widget through existing ancestors,
internalizes root capture ports and retains original execution/public interfaces.
It checks pre/post-inline history, reserved counts, the unchanged host clock
source, typed annotation projection and generated constraints. The immutable
`ReservedCheckpointInventory` permission is analysis-only: original transport
RTL remains emitted and its unsupported owner remains explicit in every region
identity/combined descriptor. Strict default inventory/image guards still reject.
See [f2-region-widget-graft.md](f2-region-widget-graft.md).

The sibling fixture retains **40 original executions / 14 descriptors / four CE
identities / twenty routes**; **550 original functional entries / 638 words and
the opaque transport owner remain uncovered**. Twenty independently rehashed
mutations reject. Final **283 Scala / 43 suites plus twelve preparation tests,
330 Python / 45 manager tests, all twelve current-source native and EDA SP2
component scopes**, retained ASan/UBSan host, FCFS and cut checks pass. Real
registered NASTI/MMIO/CPU-DMA execution passes **8,157 checks / four component
cuts / 272 words / 1,716 stalls**, delayed owners, cancellation/reset recovery
and missing-owner rejection. Independent VCD audit retains **4,064 frozen
samples** and the actual compiled payload defect at **cut 81 / word 32 / entry
5 / payload byte 42**, with both target counters held. Retained multi-region
checks remain 8,242 / four cuts / 280 words / 840 stalls, with independent waves.
These are component checks, not FPGA-origin checkpoints or CPU migration.

Native synthesis consumes complete final-host XDC from the actual compiled
`WriteXDCFile` pass, independently reconstructs both host RAM hints, and retains
all original bytes. Only four exact literal board-pad placements are deferred
outside the ReservationShell OOC boundary. Resources are **5,276 LUTs / 1,979
registers / six BUFGCEs**; 140 MHz OOC setup/hold **−0.031/−0.074 ns**, with
unconstrained I/O, establishes no timing closure. Both standalone XDC-runner
compiler failures and the first native audit's guessed transport-name failure
remain preserved. The query now follows the checked actual instance path.
After joining the original sweep, actual synthesis rebuilt that scope and the
source-policy receipt whose broad source pin became stale; ten untouched
current-source scopes retain their original passing receipts. No receipt was
relabelled or rewritten. Final source/receipt/wave/protected-input audit passes.

EDA capacity was recovered without deleting/excluding history: 91 completed
initial requests retain full SHA/metadata/inode/COW audit, and a bounded pass over
two completed Scala trees shares 110 additional identical pairs. The latter
increases free space from about 1.2 to 3.6 GB before VCS; its independent audit
also passes. The initial 12 GiB free-space target was not reached; its explicit
SIGINT receipt and partial completed-request history remain intact. The initial
retained EDA pass is superseded by a complete final-source rerun after harness
repairs. Keep this maintenance available before future large mirrored batches.

Fresh AWS, native Vivado 2025.2/F2 HDK and manager/Fabric localhost checks pass.
A standalone SSH-key probe failed public-key authentication; the initialized
manager/Fabric path passes. Final scoped inventory has no active loop runtime,
new AFI request or local build job. Existing controller checkpoints were pushed
FireSim first (`1d9e5d48`), then Chipyard (`5e6f1b51`); remote tips match. Both
managed workers completed and were joined. Plans and initialized manager inputs
retain their entry hashes; no staging, local commits, new runtime or AFI launch.
Follow [github-publication.md](github-publication.md) for the next controller commit.

The fresh exact-Rocket compiler still rejects the FASED physical CE/common-cut
owner. Production source-context projection and global descriptor identity,
complete enclosing state/reset/external-writer/functional-memory/bridge/host/
pre-FAME ownership, new router/mask/control capture or exclusion/restore, image
P&R/AFI, all-hart active FPGA cuts and paired zero-edge/finite/live/rolling CPU
migration remain pending. No checkpoint-enabled image or hardware checkpoint is
claimed. Reuse iteration194's localhost invocation. Commands and individual
immutable receipts are under `runs/aws-f2/iteration256/`, including
`verification-commands.json`, `native-selected.json`, `remaining-blockers.json`,
`component-regressions/selected.json`, `region-widget-wave-selected.json`,
`bounded-capacity-audit-selected.json` and `final-audit-selected.json`.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 255,
**in_progress; EDA verification capacity recovered and full regressions pass**.
The incoming controller failure was input rsync ENOSPC before VCS execution:
EDA had 9.6 MiB free and 846 GiB of mirrored run artifacts. Added explicit
copy-on-write extent deduplication for generated artifacts using XFS/Linux
`FIDEDUPERANGE`. The kernel compares bytes before sharing; original contents,
paths, independent inodes and modification times survive. No historical files
are deleted or excluded from synchronization. See
[eda-artifact-capacity.md](eda-artifact-capacity.md).

Actual EDA self-tests pass equal/unequal extent, metadata and subsequent-write
isolation checks. Independent full-file SHA-256, metadata and inode auditing
passes for 145 completed request pairs / 5,238,956,032 shared bytes. Both sweeps
were deliberately stopped after recovering verification capacity; their partial
receipts and interruption logs remain intact. The 16 GiB sweep target was not
reached. About 3 GiB remains free after syncing all inputs and running checks;
perform further maintenance before another large exact-Rocket generation.

Fresh full **330 Python / bank / widget / ASan/UBSan host / FCFS / cut / eleven
pinned component VCS** scopes pass in unique iteration-255 output paths. The
multi-region component retains 8,242 checks / four cuts / 280 words / 840 stalls;
independent debug-wave auditing passes, including the compiled CE defect before
acknowledgement. All **45 controller tests** pass on the native F2 manager.
An extra manager-only controller invocation on EDA failed importing Ray under
its native Python 3.9.25. That attempt remains recorded; the same complete scope
executes on the manager's existing Chia/Ray environment without omissions or
stubs. The corrected full VCS batch was independently rerun and passed.
Native/Scala/RTL sources are unchanged; existing native pins are re-audited,
with no claim of fresh synthesis this iteration.
Fresh AWS access, native Vivado 2025.2/F2 HDK and localhost Fabric checks pass.
Scoped inventory contains no loop-tagged runtime instance or new AFI request.
Existing controller checkpoints were published FireSim first (`01685716`), then
Chipyard (`636db36f`); remote tips independently match. Chipyard's local tracking
ref update reported read-only storage after the successful push; no history was
changed. Plans and initialized manager inputs remain read-only.

This increment repairs verification infrastructure. Production FASED physical
CE/common-cut ownership, complete enclosing memory/bridge/host/pre-FAME binding,
localhost checkpoint image/P&R/AFI, active all-hart hardware cuts and paired CPU
zero-edge/finite/live/rolling acceptance remain pending. No FPGA capture or CPU
migration is claimed. Managed worker startup failed before execution; the central
agent remains the only agent. Diagnostics, immutable fresh receipts and exact
commands are beneath `runs/aws-f2/iteration255/`; see `verification-commands.json`,
`recovery-attempts.json` and `final-audit-selected.json` there. Plans and initialized
manager inputs match the protected snapshot; no staging, commits or new runtime/
AFI launch occurred. No delegated worker or maintenance job remains.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 254,
**in_progress; checked multi-region graft and shared readout verified**.
`NativeCheckpointRegions` installs independently reconstructed native banks in
disjoint executions of one original host. Shared ancestors retain original
execution and raw clocks, carrying separate sidebands. Storage definitions and
all generated references are namespaced; original annotations are translated
once against the combined hierarchy. `NativeCheckpointRegionGraft` supplies one
raw-clock request/response router and descriptor ROM, a common mask/reset/read
interface and region-ordered logical/captured CE vectors. Rehashed changes to
source, context, identities or owners reject. See
[f2-native-region-graft.md](f2-native-region-graft.md).

Final repaired Scala generation passes **280 tests / 42 suites plus twelve
preparation tests**. Independent original/storage/hierarchy auditing verifies
**2,292 original executions retained**, **10,907 installed functional entries /
three CE identities**, and **1,189 uncovered functional entries / 198,818 words**.
The exact Rocket DUT/FASED banks now coexist in their original host. Nine rehashed
graft mutations and eight retained region mutations reject; five source
annotations become eleven valid annotations and ten correctly scoped XDC lines.
Six existing default FIRRTL/RTL/XDC outputs remain byte-identical. Fresh ordinary
production compilation still rejects its unbound FASED CE/common-cut owner.

The final shared-graft fixture synthesizes locally with **2,047 LUTs / 995
registers / six BUFGCEs / 272 raw-clock control/readout registers**. OOC setup/hold
estimates are **+2.027/−0.074 ns**, with unconstrained I/O; this is no image timing
closure. Source-matched fresh EDA SP2 passes **8,242 checks / four cuts / 280 words /
840 stalls**, reset cancellation and both owner rejections. Independent debug
waves verify **1,407 stable frozen samples** while both raw ancestors advance.
The compiled wrong-CE routing defect stops at **cut 1 / target cycle 36 / word 66**,
with response acknowledgement zero. These are component results, not CPU restore
or hardware-origin acceptance.

Failed attempts remain immutable in `runs/aws-f2/iteration254/recovery-notes.json`.
VCS exposed an ANSI-port collision in the hand-built fixture (`other` versus
`other_cycle`); its instance now uses `peer`, and redeclaration warnings reject.
The CE-drift label had formatting padding; the verifier now checks its exact
label with whitespace tolerance while retaining all rejection predicates. Two
native receipts rejected verifier edits during their execution. The complete
Scala scope reran after repair, and **all eleven source-matched native / eleven
fresh EDA SP2 scopes pass**. The **330 Python/bank/widget/ASan/UBSan host/FCFS/cut**
and **40 loop** scopes pass with current source snapshots. Four existing connected
variants retain 5,165 checks / four cuts / 136 words / 900 stalls, their complete
independent debug waves and the 20-check ASan/UBSan host initializer.
`final-audit-iy9345rp/summary.json` passes all source/receipt/wave/deficit/resource
checks. Final inventory has zero tagged instances and no native Vivado/Java jobs.
Commands and 31 immutable receipts are indexed by
`runs/aws-f2/iteration254/verification-commands.json` and `accepted-receipts.json`.

Production widget/complete common-cut integration, reset/external writers,
functional DRAM/timing/bridge/host/pre-FAME ownership, full localhost image/P&R/
AFI, actual active four-hart FPGA cuts, complete paired zero-edge CPU restore,
finite replay, sustained live RTL and rolling hardware recovery remain pending.
**No checkpoint-enabled image, FPGA capture or CPU migration acceptance exists.**
All FPGA-origin CPU matrix columns remain pending. AWS/native HDK/localhost checks
pass; no new AFI or runtime was launched. Existing controller checkpoints were
published FireSim first (`fe9b88c7`), then Chipyard (`787be4e4`), with remote tips
matched. Plans and initialized configs retain entry hashes. No staging/commits.
Managed worker startup failed before execution; the root remains the only agent.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 253,
**in_progress; native multi-region routing verified**.
`CheckpointRegionStateRouter.sv` routes accepted reads among native bank
endpoints, pins response ownership through latency/backpressure, translates
functional bank and physical CE slot ranges, and rejects invalid selectors.
`CheckpointRegionRouting` emits static parameters and source-bound contracts;
`CheckpointCaptureDescriptors.fromNativeRegions` rejects mixed original hosts,
overlapping executions and ABI overflow. Local/global ordinals, selectors and CE
sample bits remain distinct. See [f2-native-region-routing.md](f2-native-region-routing.md).

The retained exact Rocket DUT plus FASED structural check describes **10,910
entries / three physical CE identities**, leaving **1,189 functional entries /
198,818 words** outside the combined descriptor regions. Independent original
register/RAM/pipeline, topology and CE dependency reconstruction passes, with
**eight coherently rehashed mutations** rejected. This is descriptor composition,
not installation of both networks into a production common cut. The ordinary
single-region production census still has **1,947 uncovered entries / 298,428
words plus the unbound FASED CE owner**; fresh complete Rocket generation rejects
that missing physical owner/common cut.

Final validation passes **276 Scala / 41 suites plus twelve preparation tests**,
**330 Python / bank / widget / ASan/UBSan host / FCFS / cut**, **40 loop**,
**ten source-matched native** and **ten fresh EDA SP2** scopes. The router passes
**6,155 checks / 201 requests / 199 responses / four invalid selectors / 2,380
stalls / two reset cancellations**, one- and three-region boundary cases and
**five time-zero configuration rejections**. Independent full debug waves show
the compiled wrong-owner fault at **request 2 / response 1**, with both response
acknowledgements still zero. Its two-region OOC fixture uses **99 LUTs / three
registers**; unconstrained I/O prevents any full-image timing-closure claim.
Six existing generated FIRRTL/RTL/XDC files remain byte-identical. The four
existing connected variants retain 5,165 checks / four cuts / 136 words / 900
stalls and their independent waveform/source matching and sanitized initializer.

The superseded Scala attempt and two EDA harness failures remain preserved.
Boundary generation now preserves parameter names and supplies VCS timescales;
configuration negatives retain nonzero exits using the existing failure-status
helper in final blocks, since SP2's bare $fatal returned zero. All five source-
affected native scopes were regenerated with at most two joined Vivado jobs;
five unchanged native receipts were independently revalidated. Complete EDA and
retained scopes were rerun after repair. See `runs/aws-f2/iteration253/recovery-notes.json`.

The next compiler step is a checked multi-region in-place graft with separate
sideband namespaces, one raw transport and one common atomic cut. Complete
reset/external writers, functional DRAM, timing, enclosing bridge/host and
pre-FAME owners, full localhost image/P&R/AFI, active four-hart FPGA cuts, paired
complete zero-edge CPU migration, finite replay, sustained live RTL and rolling
hardware recovery remain pending. **No checkpoint-enabled image, FPGA capture
or CPU migration acceptance was established.** Every FPGA-origin CPU column
stays pending; physical-owner and image-admission guards remain active.

AWS/HDK/Vivado/localhost checks pass; final inventory has zero tagged instances
and no native Vivado/Java jobs. No new runtime or AFI launch. Existing controller
checkpoints were published FireSim first (`adc6c66a`), then Chipyard (`0bbd7c47`),
with remote tips independently matched. The latter's local tracking-ref update
was read-only after successful publication. Plans/initialized inputs retain
entry hashes; no staging or local commits. Managed subagent startup failed before
execution; no delegated worker remains. Central coordination rules above persist.
Commands and immutable receipts: `runs/aws-f2/iteration253/verification-commands.json`,
`accepted-receipts.json` and `final-audit-o98f41n4/summary.json`.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 252,
**in_progress; selected-source compiler context verified**.
`connectProjected` now checks the source's inert compiler context against both
original pre-inline and projected enclosing hosts, without insertion or historical
circuit renaming. The first new duplicate-context test exposed FIRRTL annotation
coalescing; validation now checks the original multiplicity. Independent auditing
reconstructs context snapshots and inline annotation hashes. Exact matching optional
nested input-file class hints are supported; deleted owners and mismatched hints
reject. See [f2-widget-source-context.md](f2-widget-source-context.md).

Fresh **272 Scala / 40 suites plus twelve preparation/directed executions**,
**330 Python / bank / widget / ASan/UBSan host / FCFS / cut**, **40 loop**,
**nine localhost native** and **nine EDA SP2** scopes pass. Seven source context
kinds retain eighteen connector rejections and **34 independent source-variant
mutations**. Matching binds **641 sources / 686 inputs**. All four connected
variants pass **5,165 checks / four cuts / 136 words / 900 stalls**; the bound
host initializer retains **20 ASan/UBSan checks**. Twelve complete debug waves
prove **2,704 stable frozen samples** per healthy variant and the compiled payload
defect at **cut 81 / word 0 / byte 42**, before release. Independent auditing also
rejects coherently rehashed omission of the selected-source Tcl constraint scope.

Six generated FIRRTL/RTL/XDC files are byte-identical to iteration 251. The
source-context component retains **4,570 LUTs / 1,655 registers / three BUFGCEs /
671 raw-clock registers**. OOC setup/hold **+0.326/−0.074 ns** retains unconstrained
I/O and does not establish timing closure. The complete Scala suite finishes in
about 28 minutes. Independent fresh exact-Rocket context auditing passes **2,456
source annotations / 25 context annotations / 20 context kinds / 2,379 projected
storage annotations**. Failed and superseded source epochs remain preserved in
`runs/aws-f2/iteration252/recovery-notes.json`; the final scope passes in full.

Fresh exact Rocket compilation still rejects its unowned FASED physical CE/common
low-phase cut. The current generated census retains **1,947 uncovered functional
entries / 298,428 words plus one physical CE owner**. The next hardware integration
target is the uncovered FASED timing-model execution and its common-cut/CE owner,
together with enclosing control and bridge state. Complete global identity/owners,
reset/external writers/DRAM/timing/host/pre-FAME state, physical CE restore/release,
full localhost image/P&R/AFI, active four-hart FPGA cuts, paired complete zero-edge
CPU migration, finite replay, sustained live RTL and rolling hardware recovery
remain pending. No checkpoint-enabled image, hardware capture or CPU migration
acceptance was established. Every FPGA-origin CPU acceptance column stays pending.

Native HDK/Vivado/Fabric and AWS/F2 checks pass. Final inventory has zero tagged
instances and no native Vivado/Java jobs; no new AFI or runtime launch. Existing
controller checkpoints were published FireSim first (`8ed8b1f5`), then Chipyard
(`e9c82ac0`), with remote tips matched. The latter's local tracking-ref update was
read-only after successful publication. Plans and initialized configs retain
entry hashes; no staging or local commits. Managed worker startup failed before
execution; no worker remains. Central coordination and recovery instructions above
remain in force. Commands and immutable receipts:
`runs/aws-f2/iteration252/verification-commands.json`, `accepted-receipts.json`
and `final-audit-0tka86tl/summary.json`.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 251,
**in_progress; typed selected-source contracts verified**.
`NativeCheckpointWidgetGraft.connectProjected` independently reconstructs and
merges typed source contracts through a FIRRTL circuit rename. It validates
the union, rejects conflicting memory policies/files, requires global policy
agreement and prevents contracts from broadening outside the selected
execution. The strict connector, sentinel identity and independent image guard
remain active. The independent auditor reconstructs both projections, rebasing
and final XDC. See [f2-widget-source-policy.md](f2-widget-source-policy.md).

Fresh **271 Scala / 40 suites plus two preparation and nine directed executions**,
**328 Python / bank / widget / ASan/UBSan host / FCFS / cut**, **40 loop**,
**nine localhost native** and **nine EDA SP2** scopes pass. Every connected
variant (sentinel, bound, host-projected and source-policy) passes **5,165 checks /
four cuts / 136 words / 900 stalls**; the bound host initializer retains **20
ASan/UBSan checks**. Source projection independently reconstructs **six source
contracts into eight translated contracts**, rejects **28 mutations**, and
matches **641 sources / 685 inputs**. A separately rehashed Tcl-scope mutation
rejects before acceptance. All twelve debug waves remain available; independent
auditing proves **2,704 stable frozen samples** per healthy variant and the
compiled payload defect at **cut 81 / word 0 / byte 42** before release.

The source-policy component uses **4,570 LUTs / 1,655 registers / three BUFGCEs /
671 audited raw clocks**. OOC setup/hold estimates **+0.326/−0.074 ns** retain
unconstrained external I/O and do not establish timing closure. Native synthesis
exposed unscoped source-local `network/...` XDC applied at FPGATop. The harness
now consumes source constraints in the selected module/instance scope and final
host constraints at the root; exact Tcl matching validates both without
rewriting retained files. The initial native failure and superseded source epochs
remain intact. All nine native scopes were regenerated with peak concurrency two.

Validation now reuses the enclosing hierarchy within each preflight, rebuilding
it for every new circuit and retaining every target check. Sixteen generated
artifacts, including exact-Rocket host/instrumented/reference FIRRTL and global
identity, are byte-identical to their pre-optimization outputs. The complete
Scala scope finishes in about **28 minutes**, versus the prior **38 minutes**.
Three superseded incomplete Scala epochs and the initial overbroad test assertion
failure remain preserved; the final full scope passes.

Fresh exact Rocket compilation still rejects the FASED physical CE owner/common
low-phase cut. The current generated census retains **1,947 uncovered functional
entries / 298,428 words plus one physical CE owner**. Complete source compiler
context and enclosing identity/owners, reset/external writers/DRAM/timing/bridge/
host/pre-FAME state, physical CE restore/release, full localhost image/P&R/AFI,
active four-hart FPGA cuts, complete paired zero-edge migration, finite replay,
sustained live RTL and rolling hardware recovery remain pending. Every
FPGA-origin CPU acceptance column remains pending; no image or capture was made.

Native HDK/Vivado/Fabric and AWS/F2 checks pass. Final inventory has zero tagged
instances and no native Vivado/Java jobs; no AFI request or runtime launch was
made. Existing controller checkpoints were published FireSim first (`ce3e59c0`),
then Chipyard (`7e7967ae`), with remote tips matched. The latter's local
tracking-ref update was read-only after successful publication. Protected plans
and initialized configs retain entry hashes; no staging/local commits. Managed
worker startup failed before execution; no worker remains. Central coordination
and recovery instructions above remain in force. Commands and immutable receipts:
`runs/aws-f2/iteration251/verification-commands.json`, `accepted-receipts.json`
and `final-audit-sikuzl_3/summary.json`.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 250,
**in_progress; typed enclosing-host annotation projection verified**.
`NativeCheckpointWidgetGraft.connectProjected` now follows original concrete
host executions into bank-specialized definitions, preserving correlated XDC,
register/RAM/hierarchy contracts and other host metadata. Both connector paths
reject unsupported selected-source targets even when an unused original shared
leaf definition remains. The downstream XDC consumer emits actual constraints
before Verilog emission. Sentinel identity and independent image guards remain
active. See [f2-widget-annotations.md](f2-widget-annotations.md).

Fresh **269 Scala / 40 suites plus two preparation**, **328 Python / bank /
widget / ASan/UBSan host / FCFS / cut**, **40 loop**, **eight localhost native**
and **eight EDA SP2** scopes pass. All native receipts were regenerated, with
peak concurrency two. Sentinel, identity-bound and projected variants each pass
**5,165 checks / four cuts / 136 words / 900 stalls**; the bound initializer adds
**20 ASan/UBSan checks**. The projection rejects **22 mutations**. Matching binds
**641 sources / 680 sentinel, 710 bound or 684 projected inputs**. Independent
waveform audits prove **2,704 stable frozen samples** per healthy variant and the
actual compiled payload defect at **cut 81 / word 0 / byte 42** before release;
all nine debug waves remain available.

The projected component uses **4,517 LUTs / 1,646 registers / three BUFGCEs /
662 audited raw clocks**. OOC setup/hold estimates **+0.326/−0.074 ns** have
unconstrained external I/O; full-image timing is pending. Real Vivado rejected
the initial CE timing-startpoint fixture. Its repaired pin-cardinality and
`DONT_TOUCH` constraint passed direct native checking, then the complete fresh
Scala/native/EDA sweep. All failed and superseded source epochs remain intact.
Final independent auditing passes; commands and receipts are in
`runs/aws-f2/iteration250/verification-commands.json`, `accepted-receipts.json`
and `final-audit-u_nf6_kt/summary.json`.

Fresh exact Rocket compilation still rejects the FASED physical CE owner/common
low-phase cut. The new generated census retains **1,947 uncovered functional
entries / 298,428 words plus one physical CE owner**. Source annotation policy,
complete enclosing identity/owners, reset/external writers/DRAM/timing/bridge/
host/pre-FAME state, common-cut release/restore, localhost full image/P&R/AFI,
active four-hart FPGA cuts, complete paired zero-edge migration, finite replay,
sustained live RTL and rolling hardware recovery remain pending. No AFI request
or runtime launch was made; final inventory has zero tagged instances and no
native Vivado/Java jobs. Native HDK/Vivado/Fabric and AWS/F2 setup pass. Existing
controller checkpoints were published FireSim first (`97d8b663`), then Chipyard
(`5bfbb620`), with remote tips matched; the latter's local tracking-ref update
was read-only after successful publication. Plans and initialized configs retain
entry hashes; no staging/local commits. Worker startup failed before execution
and no managed worker remains.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 249,
**in_progress; selected widget transport/host identity verified**.
`NativeCheckpointWidgetIdentity.bind` reconstructs the existing graft and its
selected descriptors, binds the real transport manifest parameter and emits
matching registered host metadata and constructor. It checks both original and
lowered header cardinality: native lowering can deduplicate ambiguous originals.
The incomplete-owner header error and external-clock-network image guard remain
active even after all annotations are stripped. This is selected readout identity,
not complete F1Shim identity or FPGA-image admission. See
[f2-widget-identity.md](f2-widget-identity.md).

The repaired complete Scala sweep passes **267/267 plus two preparation tests**;
the initial **266/267** duplicate-header rejection failure remains intact. All
**seven EDA SP2 scopes** pass in a fresh explicitly selected attempt. Sentinel
and bound variants each pass **5,165 checks / four cuts / 136 words / 900 stalls**.
The bound variant adds **20 ASan/UBSan checks** of the actual generated C++
initializer against four actual VCS capture streams and rejects the complete
host header at its coverage guard. Twelve independently rehashed identity
corruptions reject. Native/EDA matching binds **639 sources / 678 sentinel or
708 bound inputs**. Both waveform audits prove **2,704 stable frozen samples**
and the compiled actual data defect at **cut 81 / word 0 / byte 42** before
release, retaining all six full debug waves.

All five affected native scopes synthesize on localhost with at most two joined
Vivado jobs. The bound component has **4,753 LUTs / 1,647 registers / three
BUFGCEs / 662 audited raw register clocks**. OOC setup/hold estimates are
**+0.437/−0.074 ns**, with unconstrained external I/O; timing closure/full-image
implementation remain pending. The first seven-process EDA execution completed
but its aggregate rejected an empty successful C++ compiler log. The logger now
retains actual argv/cwd without weakening nonempty-file validation. Two affected
native scopes were regenerated and all seven EDA scopes rerun; unchanged native
inputs retain their original execution dates. Both failed epochs are preserved.
Fresh current-source **328 Python / bank / widget / ASan/UBSan host / FCFS / cut**
and **40 loop** checks pass. Final independent auditing passes.

Fresh exact Rocket compilation still rejects its FASED physical CE-latch owner
and common low-phase cut (underlying compiler: 116s). The exact generated
projection leaves **1,947 functional entries / 298,428 words plus one FASED
physical CE owner** outside the selected readout. Complete reset/external-writer,
functional DRAM, timing, bridge/host and pre-FAME ownership, common-cut release/
restore, full localhost image/P&R/AFI, active four-hart FPGA cuts, paired complete
zero-edge migration, finite replay, sustained live RTL and rolling hardware
recovery remain pending. All FPGA-origin CPU acceptance columns remain pending.

Native Vivado 2025.2/HDK/shell/Fabric localhost and AWS/F2 setup checks pass.
Final scoped inventory has zero tagged runtime instances and no native Vivado/
Java jobs. No AFI request or runtime launch was made. Existing controller
checkpoints were published FireSim first (`59508180`), then Chipyard (`19e520c4`),
with remote tips matched; the latter's local tracking-ref update failed read-only
after successful publication. Protected plans and initialized manager configs
retain entry hashes; no staging/local commits. Worker startup failed before
execution and no managed worker remains. Commands and immutable receipts are in
`runs/aws-f2/iteration249/verification-commands.json`, `accepted-receipts.json`
and `final-audit-6cvjxsj6/summary.json`. Follow
[GitHub publication](github-publication.md) for the next controller checkpoint.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 248,
**in_progress; controller rerun receipt-selection failure repaired**.
The previous controller verification passed retained sanitizer/FCFS checks but
stopped before connected execution: the replacement runner globbed all previous
attempts and asserted there was only one receipt. The tracked
`tools.checkpoint_formats.regression_runner` now reserves a fresh attempt per
invocation, prevalidates every native/source/artifact pin, preserves subprocess
logs, binds the explicitly returned fresh receipt and audits the complete ordered
scope. Ambiguous receipts, substitutions, failed subprocesses, changed sources,
missing scopes and evidence mutations reject. Ten new tests cover recovery and
negative cases. No historical evidence was overwritten.

Two actual complete EDA SP2 executions of the same populated output scope pass
all **six components per attempt**, including connected MMIO/DMA. Independent
auditing verifies both disjoint attempts and their original hashes. The connected
fixture again passes **5,165 checks / four cuts / 136 words / 900 DMA stalls**;
waveforms prove **2,704 stable frozen samples** and the compiled payload defect
at **cut 81 / word 0 / byte 42**, before release. Fresh localhost Vivado retains
**5,018 LUTs / 1,646 registers / three BUFGCEs / 662 audited raw registers**.
Native/EDA source and artifact matching binds **597 sources / 636 inputs**.
OOC setup/hold estimates remain **+0.437/−0.074 ns**, with unconstrained external
I/O; full-image timing is pending.

The complete fresh retained EDA **328 Python / bank / widget / ASan/UBSan host /
FCFS / cut** scope and **40 loop tests** pass. FCFS retains **46 continuations /
138 zero-edge owner comparisons / 2,972 rejections per backend**; the sanitized
host passes **1,384 checks**. The directed audit verifies **113 receipts / 13,516
files**, preserving all four historical stale aggregate-log mismatches explicitly.
The unchanged **265 Scala tests plus two preparation tests** remain original
iteration-247 execution evidence: their 266 source pins, logs and 29 generated
fixture comparisons verify; they were not relabelled as fresh execution.

Fresh exact Rocket compilation still rejects the missing **FASED physical
CE-latch capture owner/common low-phase cut**. Complete functional/reset/external
writer, DRAM, timing, bridge/host and pre-FAME semantic ownership, annotation and
driver/descriptor identity binding, common-cut release/restore, full localhost
image/P&R/AFI, active all-hart FPGA cuts, paired complete zero-edge migration,
finite replay, sustained live RTL and rolling hardware recovery remain pending.
No new FPGA checkpoint or CPU acceptance is claimed. Reuse iteration194's local
build invocation and the initialized manager inputs.

AWS access/HDK/native setup passes. Scoped inventory has zero tagged runtime
instances and zero native Vivado/Java jobs; 47 account-owned AFIs are observed,
with no AFI or instance requested by this turn. Existing controller checkpoints
were published FireSim first (`14b50a8e`), then Chipyard (`c69ef1eb`), with remote
tips independently matched. Chipyard's local tracking-ref update remains read-only
after the successful remote push. Protected plan/config/index bytes and HEADs
are unchanged; no staging or local commits. Managed worker startup failed before
execution, so only the central agent ran and no worker remains. The manager guard
rejected an audit-only command containing a `vcs-*` evidence path before execution;
the explicit read-only matching script then passed. Exact logs, immutable receipt
indexes and commands belong under `runs/aws-f2/iteration248/`, especially
`accepted-receipts.json`, `verification-commands.json` and `final-audit-*/summary.json`.
Follow [GitHub publication](github-publication.md) for the next controller checkpoint.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 247,
**in_progress; checked widget-to-existing-execution graft implemented**.
`NativeCheckpointWidgetGraft.connect` reconstructs the selected readout graft
and wires all twenty real post-inline widget pins inside the existing host.
It preserves the one execution, host ports/annotations, MMIO and shared DMA.
Its bounded annotation policy, sentinel descriptor identity, driver-header error
and production ownership/image guards remain explicit. See
[f2-native-widget-graft.md](f2-native-widget-graft.md).

Full Scala passes **265/265** across forty suites, plus its two preparation
tests; focused Scala passes 3/3 with ten rejections. All 29 connected-fixture
files match the native snapshot byte-for-byte. Native/EDA matching binds 595
sources and 634 inputs; the connected
component passes 5,165 VCS checks, four cuts, 136 state words and 900 DMA stalls.
The independent waveform audit caught buffered loss of the compiled-defect tail.
The repaired failure path yields after dump flushing; fresh native/EDA/audit
receipts pass and the final waveform proves cut 81, word 0, byte 42, actual
payload 0x50 versus expected 0x51 with the target still frozen. Independent
waveform auditing checks 2,704 stable frozen source-clock samples in the healthy
run. The original truncated debug epochs remain preserved.
Fresh exact-recipe production compilation rejects the missing FASED physical
CE-latch owner/common low-phase cut; no image or hardware checkpoint is emitted.
Its underlying compiler ran for 112 seconds. These are component/compiler
results. Current receipts, initial failures and exact invocation scripts are
under `runs/aws-f2/iteration247/`; `accepted-receipts.json`,
`scala-full-result.json`, `waveform-audit.json` and `remaining-blockers.json`
bind the evidence.

Fresh retained EDA ASan/UBSan/host/FCFS/bank/widget/cut and 318 Python/40 loop
checks pass. Five additional fresh EDA scopes replace four stale historical
aggregate-log references; their current pins pass while the original historical
index mismatches remain recorded. The directed audit checks 111 receipts and
11,747 files; all recorded source and indexed individual-receipt hashes match.
No historical evidence was rewritten. Unchanged older native/component scopes
retain their original execution timestamps rather than claiming new synthesis.
AWS/native/localhost setup passes; existing controller checkpoints were
published FireSim first (`98571a73`), then Chipyard (`7d965a14`). Plans and
initialized manager inputs retain entry hashes; no staging or local commits.
The final independent audit passes. Final inventory has zero tagged runtime
instances and zero native Vivado/Java jobs; all three managed workers and their
commands are joined. No AFI or runtime launch was requested. Final command and
artifact indexes are `verification-commands.json` and `final-audit.json` under
this iteration's evidence directory. Follow [GitHub publication](github-publication.md)
for the controller's next checkpoint.

Next: explicitly project production annotations and bind enclosing-host
descriptors/driver identity; cover the 1,947 functional owners and one FASED
clock owner outside the selected readout. Complete reset/external-writer,
functional DRAM, timing, bridge, host and pre-FAME semantic ownership, common
cut/release and restore remain required. Full localhost image/P&R/AFI, active
four-hart early/warm/outstanding/late F2 cuts, paired complete zero-edge CPU
restores, finite replay, sustained live RTL beyond trace and rolling hardware
recovery remain pending. Every FPGA-origin acceptance column remains pending.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 246,
**in_progress; parked physical apply component verified**.
`CheckpointTransportPhysicalRestore` loads the 23 positive-edge fields, then the
falling-edge mask, independently reads the complete vector and acknowledges
staging once. Its permanent mask and MMIO/bank/DMA isolation prevent any target
edge; there is no release or stream/host continuation. Production ties every
restore port off with `RESTORE_ENABLE=0`; strict ownership/image guards remain.
See [f2-transport-physical-restore.md](f2-transport-physical-restore.md).

Native Vivado 2025.2 passes **30 fields / 1,041 registers / 601 LUTs**, with
all **484 physical bits**, two falling-edge registers and an explicit native
GND binding for the valid-specialization-only supervisor `error[4]`. The original
1,042 draft assumed that constant bit retained a register; the pre-synthesis
source audit corrected it and added a required constant-driver proof. Four
receipt mutations and a separately synthesized extra **LDCE** reject; the latter
has **1,042 actual sequential cells**. Estimated OOC setup slack **+1.697ns** at
140MHz has unconstrained external I/O; full-image implementation remains pending.

Native-bound EDA SP2 VCS passes **2,092 physical restores / 7,504,531 checks /
136 rejections** at gate counts 1/3/31/65, plus invalid counts 0/65536. All target
edge counts are zero. A compiled physical-write defect stops at cut **100**, bit
**0**, with zero acknowledgements. Independent root waveform/source auditing
confirms those labels and every evidence hash. All **seven full waves** remain.
The fresh **27-scope native sweep** and staging synthesis pass with a joined
maximum-two-job scheduler. All retained EDA compiler/bank/widget/physical/owner
checks, **318 Python / 40 loop** tests and **ASan/UBSan host/FCFS** pass. Readout
retains **5,051 samples / 50,510 words**, shadow **1,614 captures / 80,952 words**
and staging **2,092 restores / 139,884 checks / 159 rejections**. Complete native/
EDA source, state, constraints, resource and waveform audits pass, including both
independent **1,016-register** raw-control recounts.

Fresh exact Rocket generation passes in **623s**. Initial Scala fullscope is
**260/262**, with exactly two test assertions incorrectly expecting inline
literal ties. The complete repaired widget suite passes **5/5**, checking each
connected net's sole width-exact zero driver. Main implementation is unchanged;
`scala-evidence-audit.json` explicitly records aggregate coverage, not a single
all-pass full run. The actual production compiler still rejects the FASED
physical CE-latch owner/common-low-phase cut. The initial sbt boot socket failure
is retained separately from the corrected runs-local runtime directory.

The reset-negative launcher needed its exact mutation anchor updated to preserve
the new `restoring` term. Its original failure remains separate; the corrected
compiled defect still fails at reset invalidation. Two summary-only errors
(quiet parent log and manager-source paths on EDA) retain their original logs;
completed child receipts and mapped source hashes now audit successfully. No
compiler/RTL behavior was weakened to repair these diagnostic launchers.

All delegated requests and root jobs have finished. Exact commands and individual
receipts are under `runs/aws-f2/iteration246/verification-commands.json` and
`summary.json`. Final fresh AWS/local inventory has no loop runtime or native
job and records **46 account-owned images**; this increment requested no instance
or AFI. Manager/AWS/HDK/Vivado/localhost checks pass. Existing controller checkpoints
were published FireSim first (`e751b993`), then Chipyard (`f229abac`), with remote
tips independently matched. The Chipyard push updated GitHub but its local
tracking-ref lock remained read-only; independent remote-tip verification passes.
Protected plans/configs retain their entry hashes.
Publish the next controller checkpoint per
[GitHub publication](github-publication.md); no agent staging or local commits.

Common-cut release, complete stream/MMIO/host state, immutable descriptor/driver
binding and production graft, FASED/DRAM/reset/external-writer/pre-FAME coverage,
full localhost image/P&R/AFI, active all-hart early/warm/outstanding/late F2 cuts,
paired complete zero-edge migration, finite replay, sustained live RTL beyond
trace and rolling hardware recovery remain pending. Every FPGA-origin acceptance
column remains pending.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 245,
**in_progress; transport restore staging component verified**.
Added a synthesizable transactional staging bank for the exact transport vector:
nonzero compile-time identity, source-cycle and complete-length binding, strictly
ascending words, zero padding, CRC32C, separate commit and one-shot backpressured
apply. Current owner/cycle/command faults suppress apply before its accepting
edge; abort cannot forgive sticky errors. Source-cycle binding does not compare
against a fresh destination's target counter. See
[f2-transport-restore-staging.md](f2-transport-restore-staging.md).

Native localhost Vivado 2025.2 audits every sequential cell: **655 registers /
eight fields**, raw positive clock, **1,442 LUTs**. Estimated OOC setup +4.874 ns /
hold +0.067 ns at 140 MHz has unconstrained external I/O; full image timing is
pending. A separately synthesized hidden latch rejects the complete storage
census. EDA SP2 VCS passes **2,092 staging restores / 139,884 checks /
159 protocol rejections**, at gate counts 1/3/31/65, plus three invalid
specializations. Full-word and padded tails, partial-load cancellation, stalled
apply, same-edge owner faults, malformed headers, truncated/incompatible staging
payloads and CRC faults are exercised. The compiled data defect stops at source cut **100**, word
**0**, with **zero apply acknowledgements**. Independent final auditing verifies
those labels directly in the negative waveform. All **eight debug waves** remain.

All **318 checkpoint Python / 40 loop tests** pass, along with retained EDA
generated-bank/widget, **ASan/UBSan host/FCFS** and cut checks. Unchanged Scala
and other compiler/native scopes retain iteration-244 evidence; they are not
relabeled as new runs. The first native wrapper failed a mistyped total (755
versus the independently enumerated 655), and the first separate hidden-latch
launcher lacked the Python import root. Both original diagnostics remain; their
corrected complete checks have separate logs/receipts. A managed reviewer found
two test gaps; both were fixed before accepted synthesis/EDA source epochs. The
reviewer's requests finished and were collected; no worker remains active.

AWS/F2, native HDK/Vivado and localhost SSH pass. Final scoped inventory has no
loop-tagged runtime instance or native job and records 45 account-owned images;
this increment requested no new instance or AFI. Reuse iteration194's localhost
invocation and the four initialized manager YAMLs. Protected plans/configs match
entry hashes. Existing controller heads were published FireSim first
(`8d74491d`), then Chipyard (`aeabdc39`); independent remote tips match. The
Chipyard push's local tracking-ref update failed on a read-only lock path after
the successful GitHub update; `ls-remote` independently verifies publication.
No agent staging/local commits. Publish the next controller checkpoint per
[github-publication.md](github-publication.md).

This is a restore **staging** component. It does not load the production
transport's mixed-edge registers or restore stream/MMIO/host obligations.
Production widget/inventory/image guards remain unchanged. Next: implement and
verify that physical apply adapter, including the falling-edge mask and complete
owner/stream state, then bind the immutable generated descriptor/driver and
production graft. Complete FASED/DRAM/reset/external-writer/pre-FAME state,
localhost full image/P&R/AFI, active all-hart early/warm/outstanding/late F2 cuts,
paired complete zero-edge migration, finite replay, sustained live CPU shadow
beyond trace and rolling hardware recovery remain pending. Every FPGA-origin
acceptance column remains pending. Exact commands and individual source-bound
receipts are under `runs/aws-f2/iteration245/`: `verification-commands.json`,
`summary.json`, `final-inventory.json`, `publication.json` and the native/EDA/
negative/audit/retained subreceipts referenced by `summary.json`.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 244,
**in_progress; source-preservation component increment verified**.
`CheckpointCaptureCut.state` and `CheckpointCaptureTransport.state` now require
both `fsm_encoding="none"` and `dont_touch="true"`, with exact refreshed Scala
source pins. The initial native failure proved that disabling FSM extraction
alone left eleven transport `state_reg[2/3]_rep*` copies: 495 physical registers
for 484 source bits. Preserve original failed builds and source-copy probes under
`runs/aws-f2/iteration244/`; all accepted repaired-source evidence is separate
under `runs/aws-f2/iteration244/repair/`.

The full repaired scope passes: **262 Scala / 39 suites, 318 Python / 40 loop,
27 native component / 46 EDA scopes**, retained **ASan/UBSan/host/FCFS**, and
independent complete source/state/constraint/wave/resource audits. Fresh exact
Rocket generation passes in **614s**; production compilation still explicitly
rejects the missing FASED BUFGCE latch/common-low-phase owner. Native readout maps
all **484 source bits** to exactly **484 registers**, with zero extra encoding
storage. Shadow synthesis has **552 shadow / 1,036 total registers**. The complete
`IS_SEQUENTIAL` census rejects unrepresented storage. All **five native negatives**
reject: complete policy removal per controller, transport-only preservation
removal (eleven replicas), exported-bit permutation and a hidden latch.

EDA SP2 VCS passes **5,051 readout samples / 50,510 words**, **1,614 shadow
captures / 80,952 words** at gate counts 1/3/65, and eleven integration scenarios.
The captured-bit defect stops at cut **100**, observation **107**, word **0**.
All **29 debug waves** are retained and independently audited. Both attached-top
DCPs independently enumerate **1,016 raw control/stream registers**, partitioned
777/55/184; exact count and every raw clock are checked. Legacy assertions
1,028/1,024 were updated only after those DCP recounts. Source-instance ownership
checks remain intact; three definition deduplication sites avoid deep structural
hashing only after global duplicate-name validation. No overall speedup is claimed.

Recovery evidence is preserved: the original Scala job was stopped/joined (143),
then both complete Scala source epochs passed. Initial missing-adapter EDA failure,
two native width failures, nested historical-producer lookup failure and both
stale raw-count audit failures retain separate logs. The corrected producer lookup
keeps complete circuit/storage/context equivalence checks and binds the fixture
to its actual iteration-239 producer, separately from fresh generation. All
native tasks were joined with at most two Vivados and no large-Java overlap.
One managed EDA worker hit model capacity; root collected its 44 earlier receipts,
observed its processes gone and ran all repaired-source checks centrally. Review
results were collected; no delegated request or build process remains.

AWS/F2, Vivado 2025.2/HDK and localhost checks pass. Final scoped inventory has no
loop runtime instance or native job; 44 account-owned images are recorded, with
no new instance/AFI requested by this increment. Plans and four manager YAMLs
match their entry hashes. Existing controller heads were published FireSim first
(`8ee6f51d`), then Chipyard (`59edaf9d`); no agent staging or local commits.
Publish the controller's next checkpoint per
[github-publication.md](github-publication.md).

Complete transport restore/stream/MMIO/host ownership, immutable descriptor/driver
binding and production graft, full FASED/DRAM/reset/external-writer/pre-FAME coverage,
localhost full-image P&R/timing/AFI, active all-hart early/warm/outstanding/late FPGA
captures, independent zero-edge/finite/live CPU migration beyond trace and rolling
hardware recovery remain pending. Every FPGA-origin matrix column remains pending.
Exact runnable commands and individual receipts: `repair/verification-commands.json`,
`repair/summary.json`, `repair/native-recovery.json`, `repair/manager-audit-result.json`,
`repair/remaining-blockers.json`, `repair/final-inventory.json` under iteration244.
See [f2-transport-source-encoding.md](f2-transport-source-encoding.md).

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 243,
**in_progress; interrupted verification**. Source encoding preservation and
exact register-Q/exported-bit mapping were implemented, but native/EDA checks
and the full Scala sweep were not completed. Preserve original diagnostics
under `runs/aws-f2/iteration243/`; do not mark those receipts freshly verified.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 242,
**in_progress**. Added `CheckpointTransportControlSnapshot.sv`: one-edge atomic
shadowing of the complete transport source-register vector and target label,
immutable bounded bank reads during source continuation, busy backpressure,
explicit cut/owner admission, sticky failures and abort/reset recovery. See
[f2-transport-control-snapshot.md](f2-transport-control-snapshot.md).

Local native Vivado synthesis passes with **552 shadow / 1,052 total register
cells** and exact raw-clock/polarity/storage accounting. EDA SP2 VCS passes
**1,614 standalone captures / 80,952 word checks / gate counts 1, 3, 65**, plus
**eleven integration scenarios** with independently reconstructed pre-edge
transport state. A separately compiled captured-bit defect fails at its first
unequal word of snapshot cut **100**, observed at source cycle **107**, word **0**,
capture **1**; the final audit independently checks both labels in its VCD.
**Sixteen debug VCDs** are retained. The fixed-source native/EDA comparison and retained **318 checkpoint
Python / 40 loop / generated-bank / widget / ASan/UBSan host / FCFS / cut** checks
pass. No Scala source changed; the prior 262-test Scala sweep remains historical.
The initial synthesized attempt correctly rejects its receipt because testbench
source changed during execution; its logs and the fixed-source rerun are separate.
The final negative-wave audit found the immediate DPI exit bypassed VCS flushing;
explicit `$dumpflush` now precedes failure exits, with another complete native/EDA
rerun. The first flush injection also matched the DPI declaration; the retained
EDA syntax diagnostic drove a call-only replacement and declaration guard before
the final complete rerun. An independent SP2 probe demonstrates that the flush
needs an end-of-time-slot wait before DPI exit; a one-ps wait preserves both
nonzero failure status and the waveform without another clock edge. The versioned
verifier now rejects time-zero-only waves and checks the negative cut/observation
labels itself. Original wave/path audit failures remain separate and remote paths remain
unchanged in receipts; local validation resolves their corresponding returned files.
Commands and evidence belong under `runs/aws-f2/iteration242/`.

This is a staging component, not a complete transport restore owner. Existing
production widget/inventory/image guards remain unchanged. Cut certificates
still need actual complete owner wiring; shadow storage mapping, the five native
FSM encodings, stream/MMIO, FASED/DRAM/host/reset/external-writer ownership,
immutable descriptors/driver binding and production graft remain pending.
Full-image localhost P&R/AFI, all-hart FPGA cuts, independent Level-1/Level-2
restores, finite/live RTL and rolling hardware recovery remain pending. All
FPGA-origin matrix columns stay pending. AWS/F2, native Vivado/HDK and localhost
SSH setup pass. No AFI or instance was requested; final inventory retains 42 owned
images and no loop-tagged runtime instance or native build job. Plans and manager
inputs retain entry hashes. No staging or commits. Existing controller heads were
published FireSim first, then Chipyard, and both remote tips match; the local
tracking-ref write denial is retained. Managed worker startup failed before
creation; root performed the work without any delegated request outstanding.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 241,
**in_progress**. Added synthesizable live readout for all 24 sequential
transport/cut-controller registers, including the falling-edge physical mask.
The packed vector has `481 + GATES` bits. A pinned Scala schema describes exact
offsets, widths, clock edges and reset values and emits a combinational 64-bit
bank. An independent source auditor reconstructs the actual storage and packing.
See [f2-transport-control-state.md](f2-transport-control-state.md).

All **262 Scala / 318 checkpoint Python / 40 loop tests**, **26 localhost
synthesis / 45 EDA scopes**, retained **ASan/UBSan/host/FCFS** and the combined
source/state/constraint/wave/resource audits pass after the recorded audit
repairs. The readout passes **5,051 samples / 50,510 bank words / eleven scenarios**,
with **13 debug waves**. An independently compiled field swap diverges at target
cycle **2**, sample **75**. Native synthesis accounts for **500 register cells**,
all raw-clocked with one falling-edge mask. **Five extra native FSM encoding
registers** have explicit source/encoding receipts; their capture/restore mapping
remains unsupported. The joined scheduler preserves its two original audit
failures and separate recoveries, with a peak of two jobs and no large-Java overlap.

Fresh exact-Rocket generation completes in **636 seconds**; its actual compiler
diagnostic still rejects the missing FASED CE-owner/common-low-phase cut. The full
Scala fixture used the retained iteration-239 producer named in its invocation.
The fresh iteration-241 producer has identical reference RTL and all 2,431 storage
annotations but distinct history/context. Both epochs are preserved; complete
fixture audits bind to the actual producer, without normalizing history hashes.
Initial fixture-order, script-import, implicit-wire, native clock-property and
encoding-accounting failures are retained with repairs under iteration 241.
The failed initial Java invocation was cancelled and joined. Managed worker startup failed before
creation; this central agent runs all work and has no delegated request pending.
Use iteration-241 scripts/evidence under `runs/aws-f2/iteration241/`.

The readout is live and the widget leaves it unused until an explicit coherent
capture/restore owner exists. No atomic snapshot is claimed; opaque inventory
and unbound image-emission guards still reject. Complete transport/stream/MMIO,
FASED/DRAM/host/reset/external-writer and pre-FAME ownership, immutable descriptor/
driver binding, production graft, full localhost image P&R/AFI, active all-hart
FPGA captures, independent restores, finite/live RTL and rolling hardware recovery
remain pending. Keep all FPGA-origin matrix columns pending. AWS/F2, native
Vivado/HDK and localhost SSH setup checks pass; no new instance or AFI is requested.
Plans and initialized manager inputs retain entry hashes. No staging or local
commits. Existing controller heads were published FireSim first, then Chipyard;
both remote tips match. The local tracking-ref write denial is retained. Final
inventory has no active loop-tagged F2 instance or native build job; existing AFIs
remain inventoried. No new image, AFI or runtime instance was requested.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 240,
**in_progress**. Added `NativeCheckpointWidgetPeerRouting.inspect(before, after)`
to reconstruct all twenty reserved endpoints after the actual native inline
pass, retaining exact phase circuit/annotation identities, original endpoint
markers, owner/CE order, physical transport ABI/sources and raw clock/reset.
It rejects swapped equal-zero returns, CE permutations, duplicate drivers,
alias loops and altered transport identity. Existing image-emission and opaque
transport-state rejections remain intact. See
[f2-widget-peer-routing.md](f2-widget-peer-routing.md).

The three new Scala tests pass with fourteen rejection cases. Independent
manager/EDA reconstruction passes **20 pins / 42 connection hops**, binding
**21 inputs / 23 sources** and rejecting seven receipt mutations. An initial
phase-hash audit error is preserved; exact reservations before and after adding
the real inline request are now retained and their request-only delta audited.
The recovered native sweep passes **25 synthesis scopes**, with all nineteen
launch tasks joined and a peak of two. The existing recovery generation and
**256 Scala tests** remain timestamped under iteration 239. All **44 EDA scopes**,
**313 checkpoint Python / 40 loop tests**, retained **ASan/UBSan/host/FCFS**,
and the combined source/state/constraint/wave/resource audits pass. Exact-Rocket
production compilation reaches the real missing FASED CE-owner/common-cut
rejection in **106 seconds**. Original failures remain preserved. Recovery fixes
bind the successful generation log and its unchanged source commit, use a
workspace sbt socket directory, require the complete actual **79-file** graft
set instead of counting two historical duplicate XDC aliases, and complete the
missing manager production-structure audit. Final receipts and runnable commands
belong under `runs/aws-f2/iteration240/`.

The next production step is an independently audited transport state owner and
immutable descriptor/driver identity, followed by a checked existing-root graft
connection to these peer routes. Complete FASED/DRAM/host/reset/external-writer
and pre-FAME ownership, localhost full-image P&R/timing/AFI, all-hart FPGA cuts,
independent zero-edge restores, finite replay, sustained live RTL and rolling
hardware recovery remain pending. All FPGA-origin acceptance columns remain
pending. AWS/F2, native Vivado/HDK and localhost/Fabric SSH setup pass. Existing
controller checkpoint heads were published FireSim first, then Chipyard; the
remote updates succeeded and the local tracking-ref write denial is retained.
Managed worker startup failed before creation; root only, with no delegated
request outstanding. Plans and initialized manager inputs retain entry hashes.
No staging/commits, runtime launches or new AFI requests.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 239,
**in_progress**. The actual FPGATop widget/MMIO/CPU-stream resources can now be
reserved before final host inventory, with twenty explicit lowered endpoint
annotations and no enclosing simulator copy. Owner/cycle inputs remain explicit.
A reserved sentinel and driver `#error` cannot reach ordinary FPGA emission;
the compiler rejects unresolved markers/header/parameter identity even without
an inventory request. See [f2-widget-reservation.md](f2-widget-reservation.md).

The transport's SystemVerilog blackboxes contain sequential state that the
current FIRRTL inventory cannot audit. That rejection remains intact, with an
explicit unsupported external-owner receipt. All twenty markers survive the actual native inline pass. Next: define peer
routing after widget inlining, complete that state owner and immutable
descriptor/driver identity, then connect the existing-root graft.
Full production freeze/reset/external writers/DRAM/FASED/host/pre-FAME ownership,
localhost full-image P&R/timing/AFI, all-hart active hardware cuts, independent
zero-edge restores, finite replay, sustained live RTL and rolling recovery remain
pending. All hardware-origin acceptance columns remain pending. Reuse the
initialized iteration-194 ExternallyProvisioned localhost invocation.

The unbound diagnostic passes **48 fresh EDA SP2 checks** with a debug wave,
missing-owner rejection, zero checkpoint DMA frames, baseline DMA and reset
recovery. Native synthesis proves **810 raw control/stream register clocks**;
independent matching binds **25 inputs / 14 sources** and rejects eight rehashed
mutations. The complete retained sweep is in progress under
`runs/aws-f2/iteration239/`; final
receipts and exact commands will be recorded there before returning. Both plans
and initialized manager configs remain read-only. Managed worker startup failed
before creation; only the central agent runs and no delegated worker exists.
Existing controller checkpoints were pushed FireSim first, then Chipyard; the
Chipyard remote update succeeded with a local tracking-ref write denial retained
in its log. No local commits/staging, new AFIs or runtime launches.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 238,
**in_progress**. `NativeCheckpointInPlaceGraft.generate` inserts a descriptor
ROM, transaction router and physical CE bank inside the one existing lowered
root. Original functional ports, selected instance paths, ancestor clocks and
storage annotations remain intact. It emits original-path synthesis/implementation
XDC through the real consumer, bound with source/context, global identity,
grafted circuit and RTL hashes. Explicit capture ports still require production
widget/owner binding. See [f2-native-inplace-graft.md](f2-native-inplace-graft.md).

The bounded graft passes **7,101 EDA SP2 checks / four cuts / 136 words / 522
stalls**, reaching cycle **419** with five waves. Native synthesis retains
**1,091 LUTs / 595 registers / three BUFGCEs**, proving **199** raw ancestor/
router/endpoint clocks. OOC setup/hold estimates are **+2.052/−0.074 ns**;
full-image closure remains pending. Independent native/EDA matching binds
**630 inputs / 59 sources** and rejects six rehashed adapter mutations plus
eight rehashed circuit/clock/hierarchy/constraint/scope/owner mutations. Settled
wave reconstruction proves two ancestor counters advance during **872** frozen
raw-clock edges at cuts **25/78/193/339**, without a selected target edge.
Compiled CE corruption stops on its first physical read at cycle **25**, check
**55**. Exact Rocket probe generation passes in **606 seconds**; the ordinary
compiler still rejects its missing FASED CE capture owner/common low-phase cut.
All **253 Scala / 24 localhost synthesis** scopes, **313 checkpoint Python / 40
loop tests** and retained **ASan/UBSan/host/FCFS** checks pass. All **43 EDA
scopes** and the combined source/word/constraint/waveform/resource audit pass.
Exact commands and individual receipts belong under `runs/aws-f2/iteration238/`
in `verification-commands.json`, `summary.json` and `final-audit.json`.
Manager/EDA production graft auditing matches all
**77 inputs / 59 sources**, with original execution and coverage gaps intact.

Next: connect the graft's explicit capture interface to the registered widget
inside the existing production FPGATop; complete reset/external CE/functional
DRAM/FASED/bridge/host ownership, physical CE restore and independent pre-FAME
semantics. Selected coverage still leaves **1,947 functional owners and one
FASED CE owner** uncovered. Full localhost image/P&R/timing/AFI/driver binding,
active all-hart F2 cuts and reference continuation, complete independent zero-edge
restores, finite replay, sustained live clean RTL and rolling recovery remain
pending. All FPGA-origin migration columns remain pending. Reuse iteration194's
initialized ExternallyProvisioned localhost invocation; no checkpoint image,
AFI, runtime or hardware-origin checkpoint is claimed.

Final inventory: **zero loop runtime instances / zero native jobs / 37 account
AFIs / no pending AFIs**, with no inventory delta. This turn requested no image
or runtime; none of those account images establishes this implementation.
AWS/F2, native Vivado/HDK and both localhost SSH access paths pass. Diagnostics
retain the corrected ScalaTest filter, FIRRTL declaration order, annotation
ordering and independent selector-path failures. Both existing controller
checkpoints were pushed FireSim first, then Chipyard; remote tips match. The
Chipyard push retains its successful remote update and
local tracking-ref write denial. Plans and initialized manager YAMLs remain
read-only. No staging/local commits. Managed worker startup failed before
creation; only the central agent ran and no worker remains.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 237,
**in_progress**. `NativeCheckpointInPlaceCaptureBinding` connects the validated
in-place component network to the registered FPGATop widget, actual MMIO
interconnect and CPU-managed DMA stream. The standalone binding shares the
same endpoint attachment. Global descriptor identities, original bank selectors,
CE bit order, original constraints and raw ancestor/control clocks survive.
Missing reset/owner connections fail elaboration; changed source/dependency
contracts and nested enclosing simulators reject. See
[f2-native-inplace-widget.md](f2-native-inplace-widget.md).

The new component passes **19,235 EDA SP2 checks / five cuts / 170 words /
1,110 DMA stalls**, reset recovery through cycle **200** and four execution
negatives, retaining **five debug waves**. Native synthesis retains **4,572
LUTs / 1,850 registers / three BUFGCEs**, proving **199** raw ancestor/router/
endpoint and **1,024** raw widget/MMIO/DMA register clocks. OOC setup/hold
estimates are **+0.590/−0.074 ns**; full-image closure remains pending.
Independent native/EDA matching binds **156 inputs / 68 sources** and rejects
**ten** attachment mutations. Independently reconstructed settled VCD values
prove both ancestor counters advance during **3,034** frozen raw-clock edges,
with no selected target advance. Payload corruption stops at frame **1**;
compiled CE corruption stops at frame **33**, both at cut **16**.

All **252 Scala / 23 localhost synthesis / 42 EDA scopes**, **313 checkpoint
Python / 40 loop tests** and retained **ASan/UBSan/host/FCFS** checks pass.
The exact Rocket probe generation passes in **593 seconds**; its ordinary
production compiler still rejects the missing FASED CE capture owner/common
low-phase cut. Exact commands and individual receipts belong under
`runs/aws-f2/iteration237/` in `summary.json`, `verification-commands.json` and
`final-audit.json`. AWS/F2, Vivado/HDK, default localhost SSH and actual Fabric
localhost access using the manager's `~/firesim.pem` setting pass. Existing controller checkpoints were published
FireSim first, then Chipyard; remote tips match. The successful Chipyard push's
local tracking-ref update was denied and is retained in its original log.

The new binding handles an instrumented component host inside FPGATop. It still
rejects embedding an enclosing production simulator. Next: a checked
post-lowering graft into the existing production FPGATop with immutable ROM
binding, complete reset/external CE/functional DRAM/FASED/bridge/host ownership,
physical CE restore and independent pre-FAME semantics. Selected production
coverage remains **10,149 functional + two CE** owners, leaving **1,947
functional + one FASED CE** owners uncovered. Full localhost image/P&R/timing/
AFI/driver binding, active all-hart hardware cuts, paired independent complete
zero-edge restores, finite replay, sustained live clean RTL and rolling recovery
remain pending. All FPGA-origin migration columns remain pending. Reuse
iteration194's initialized ExternallyProvisioned localhost invocation. No
checkpoint-enabled image, new AFI/runtime or hardware-origin checkpoint is
claimed. The final scoped inventory has **zero loop runtime instances / zero
native jobs / 36 account AFIs / no pending AFIs**; no account image is attributed
to this implementation. Plans and initialized manager YAMLs remain read-only. No staging/local
commits. Managed worker startup failed before creation; only the central agent
ran, and no worker remains.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 236,
**in_progress**. `NativeCheckpointInPlaceAccess.emit` connects one existing host
execution to a raw-clock functional/physical CE readout router. It reconstructs
source/context/graft/identity before emission, uses original global StateIDs with
unchanged local selectors, and preserves original correlated XDC under the
actual `network` instance. See [f2-native-inplace-access.md](f2-native-inplace-access.md).

All **251 Scala / 22 localhost synthesis / 41 EDA scopes**, **313 checkpoint
Python / 40 loop tests** and retained **ASan/UBSan/host/FCFS** checks pass.
The new bounded readout passes **7,101 SP2 checks / four cuts / 136 words / 522
stalls** through cycle **419**, retaining **five debug waves**. The compiled
CE-connection fault stops on its first physical read at cycle **25**, check
**55**, before a functional word; missing owner and CE drift remain stopped.
Native synthesis retains **1,091 LUTs / 595 registers**, independently proving
**199** raw parent/router/endpoint register clocks. OOC setup/hold estimates are
**+2.052/−0.074 ns**; full-image timing closure remains pending. Native/EDA
matching binds **817 inputs / 54 current sources** and rejects ten rehashed
mutations. The retained original in-place execution still passes **6,541 checks /
four cuts / 128 words / 468 stalls**, with six waves.

Fresh exact-Rocket generation and independent production readout audits pass.
They check **2,431 storage annotations / 2,379 projected annotations**, **25
compiler-context annotations / 20 kinds** and **14 actual XDC commands in seven
emitted annotation blocks**. Native plusarg constants are checked against exact
source annotations, stateless original definitions and concrete module hashes;
the generic metasim inventory schema stays unchanged. History, preservation,
memory-model/constant targets, retired path caches and shell-only XDC retain
complete explicit contracts. Four new Python tests exercise **23 negative
subcases**. Unknown classes still reject. Commands and receipts belong under
`runs/aws-f2/iteration236/` in `summary.json`, `verification-commands.json` and
`recovery-notes.json`.

Selected coverage remains **10,149 functional + two CE** entries, leaving
**1,947 functional owners and one FASED CE owner** uncovered. The ordinary
compiler still rejects that missing physical CE owner/common low-phase cut.
Next: actual registered FPGATop widget/MMIO/DMA attachment, complete reset/
external CE/functional DRAM/FASED/bridge/host ownership, physical CE restore and
independent pre-FAME semantics. Full localhost image/P&R/timing/AFI/driver binding,
active all-hart early/warm/outstanding/late F2 captures, independent complete
zero-edge restores, finite replay, sustained live RTL and rolling recovery remain
pending. Every FPGA-origin migration column remains pending. Reuse iteration194's
initialized ExternallyProvisioned localhost invocation. No capture image or AFI
is claimed.

Diagnostics preserve invalid fixture register selectors, artificial clock-pin
path segmentation, the vararg annotation constructor error, an EDA launch before
a native receipt existed, previously fixture-only production annotation/schema
assumptions, and the final annotation-block/command count mismatch. Corrections
retain original structural-fixture/production constraints and strict admission.
AWS, native Vivado/HDK and localhost SSH checks pass. Final inventory has **zero
loop runtime instances / zero native jobs / 35 account AFIs**. Newly observed
pending account AFI `afi-0c48c4812ad82c73d` was not requested by this turn;
its provenance is unverified and it provides no checkpoint-image acceptance.
The inventory delta preserves its ID without altering it. This iteration
requested no runtime or image. Both plans and the four initialized
manager YAMLs retain entry hashes. Existing iteration-235 controller checkpoints
are published FireSim first, then Chipyard; both live remote tips match. No
staging/local commits. Managed worker startup failed before creation; only the
central agent ran, and no worker remains.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 235,
**in_progress**. `NativeCheckpointInPlaceContext` binds the actual post-lowering
compiler context alongside complete host storage annotation projection. Native
functional emission version 2 retains the source annotation sets and context
snapshot. The exact Rocket test passes with **2,456 source annotations / 25
context annotations / 20 kinds / 2,379 projected storage annotations**. Its real
XDC consumer emits **14 commands**, preserving the original seven source
constraints' order from the compiler translation binding. Unknown owners reject.
See [f2-native-inplace-context.md](f2-native-inplace-context.md).

All **250 Scala / 21 localhost synthesis / 40 EDA scopes**, **309 checkpoint
Python / 40 loop tests** and retained **ASan/UBSan/host/FCFS** checks pass.
Independent context auditing matches **15 fixture / 17 production input files
and 44 current sources** on both backends, rejecting **eight fixture / nine
production** mutations, including coherently rehashed constraint reordering.
Positive audit inputs are retained as immutable copies with original paths.
The retained in-place network passes **6,541 SP2 checks / four cuts / 128 words /
468 stalls** through cycle **409**, with all **six debug waves**, and matches
**1,822 inputs / 42 sources**. Native synthesis retains **884 LUTs / 590 registers /
194 raw-clock registers**; full-image timing remains pending. Final receipts,
exact commands and preserved exploratory diagnostics are under
`runs/aws-f2/iteration235/` in `summary.json`, `verification-commands.json` and
`recovery-notes.json`.

Selected coverage remains **10,149 functional + two CE** entries, with **1,947
functional owners and the FASED CE owner** explicitly uncovered. The ordinary
production compiler still rejects the missing physical CE owner/common cut.
Next: actual in-place CE endpoint/router/widget/MMIO/DMA attachment; reset,
external CE and functional-memory writers, FASED/bridge/host owners, physical CE
restore and independent pre-FAME semantics. Full localhost image implementation,
timing/AFI/driver binding, active all-hart F2 cuts, paired complete zero-edge
migration, finite replay, sustained live RTL and rolling recovery remain pending.
Every FPGA-origin migration column stays pending. Reuse iteration194's initialized
ExternallyProvisioned localhost invocation. No capture image/AFI is claimed.

AWS/F2/native Vivado/HDK/default localhost SSH checks pass. Final inventory has
**zero loop instances / zero native jobs / 33 existing AFIs / no pending AFIs**;
no resource was launched. Both plans and four initialized manager YAMLs retain
entry hashes. Existing iteration-234 controller commits were published FireSim
first, then Chipyard; both remote tips match. The successful Chipyard publication
and denied local tracking-ref update remain in raw logs. No staging/local commits.
Managed worker startup failed before creation; only the central agent ran.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 234,
**in_progress**. Native-bank annotation translation now anchors shared native
primitive-local XDC to each original concrete execution. Renamed ancestors and
correlated pins retain their original scope; the added mask primitive is excluded,
and unchanged siblings keep their constraints. Selected-reference and enclosing
host constraints use the same checked version-2 translation. Descriptor validation
requires that version. See [f2-native-primitive-xdc.md](f2-native-primitive-xdc.md).

All **248 Scala / 21 localhost synthesis / 40 EDA scopes**, **309 checkpoint
Python / 40 loop tests** and retained **ASan/UBSan/host/FCFS** regressions pass.
The changed fixture passes **6,541 EDA SP2 checks / four cuts / 128 words / 468
stalls** through cycle **409**, with all six debug waves. Native synthesis retains
**884 LUTs / 590 registers / 194 raw-clock registers**; full-image timing remains
pending. Independent in-place native/EDA matching covers **1,710 inputs / 41
current sources**, rejecting six structural/sixteen identity/fourteen annotation
mutations. Its independent annotation audit checks six actual emitted XDC lines;
the retained physical-gate synthesis applies all six original physical constraints.

Fresh exact-Rocket generation and original/global coverage auditing pass. The
selected **10,149 functional + two CE** entries still leave **1,947 functional
owners and the FASED CE owner** uncovered. The ordinary production compiler
correctly rejects that unbound physical CE latch/common cut. No capture image,
AFI or FPGA-origin checkpoint is emitted. Fresh receipts, exact runnable commands,
diagnostics and recovery context belong under `runs/aws-f2/iteration234/` in
`summary.json`, `verification-commands.json` and `recovery-notes.json`.

AWS identity/F2 type discovery, native Vivado/HDK and default localhost SSH pass.
Both plans and initialized manager YAMLs retain their entry hashes. Existing
iteration-233 controller commits are published FireSim first, then Chipyard;
remote tips match. The Chipyard push's local tracking-ref update was denied
following successful remote publication; preserve its exact log. No staging or
local commits. Managed worker startup failed before creation; work stays central.

Next: exact production stage-context projection and in-place CE endpoint,
router/widget/MMIO/stream attachment; bind reset/external CE/functional-memory,
FASED/bridge/host/pre-FAME owners and physical CE restore. Full localhost image
implementation/timing/AFI/driver binding, active all-hart F2 cuts, complete paired
zero-edge migration, finite/live RTL comparison beyond the trace and rolling
hardware recovery remain pending. Reuse iteration194's initialized localhost
invocation. All FPGA-origin migration columns remain pending.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 233,
**in_progress**. In-place banking now projects supported host annotations against
both complete original and instrumented concrete hierarchies. Parent-rooted XDC
arguments retain their correlated paths, repeated banked definitions specialize,
and unchanged shared siblings remain owners. Source/generated/result annotation
sets and every mapping bind version-3 in-place provenance; stale combinational
path caches are explicitly retired. Unknown owners, stale/foreign targets,
missing declarations and ambiguous physical-local constraints reject.
See [f2-native-inplace-annotations.md](f2-native-inplace-annotations.md).

All **247 Scala / 21 localhost synthesis / 40 EDA scopes**, **309 checkpoint
Python / 40 loop tests** and retained **ASan/UBSan/host/FCFS** checks pass.
The new independent annotation/XDC auditor checks four actual emitted constraint
lines and rejects **ten** coherently rehashed annotation mutations, alongside the
retained **six structural / sixteen identity** negatives. Fresh EDA SP2 passes
**6,541 checks / four cuts / 128 words / 468 stalls**, continuing through cycle
**409**, with all **six** debug waves. Native/EDA matching binds **1,530 inputs /
41 current sources**, including the actual annotation translator and XDC consumer.
Native bounded synthesis retains **884 LUTs / 590 registers / 194 raw-clock
registers**; full-image timing remains pending. Exact-Rocket structure and global
uncovered owners match independently on both hosts. The ordinary Rocket compiler
still rejects the unbound **FASED CE latch/common low-phase cut**; no deployable
capture image or physical checkpoint is emitted.

Fresh receipts, diagnostics, exact commands and recovery notes belong under
`runs/aws-f2/iteration233/` in `summary.json`, `verification-commands.json` and
`recovery-notes.json`. Plans and four manager YAMLs retain their entry hashes.
AWS/F2/native Vivado/HDK/default localhost SSH checks pass. Existing iteration-232
controller commits were published FireSim first, then Chipyard; remote tips match.
The latter's remote push succeeded while its local tracking-ref write was denied;
original logs are retained. No staging or local commits. Managed worker startup
failed before creation; all work remained central.

Next: exact production annotation/context projection (including primitive-local
XDC), in-place physical CE endpoint/router/widget/MMIO/stream attachment, complete
reset/external CE/functional-memory/FASED/bridge/host/pre-FAME ownership and
physical CE restore. Full localhost image implementation/timing/AFI/driver
binding, active four-hart F2 cuts, reference continuation, complete paired
zero-edge restores, finite replay, sustained live RTL beyond trace and rolling
hardware recovery remain pending. No checkpoint-enabled AFI or FPGA-origin
checkpoint is claimed. Reuse iteration194's initialized localhost invocation.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 232,
**in_progress**. In-place native banks now reconcile selected endpoint identities
with the original complete enclosing generated-RTL inventory. Functional and physical
StateIDs become global while hardware descriptor order, bank/slot, transfer shape
and CE bit order stay local. Version-2 in-place bindings and the new descriptor
factory bind both inventories, original topology/CE dependencies and every
uncovered global owner. No coverage or restore admission is inferred.
See [f2-native-inplace-identity.md](f2-native-inplace-identity.md).

All **244 Scala tests** pass. Independent original-FIRRTL auditing reconstructs
registers, RAMs and emitter pipelines, clocks/resets/shapes and complete global
clock/CE provenance. Exact Rocket maps **10,149 functional + two CE** selected
entries (**320,587 words**) into **12,096 functional + three CE** global owners.
Its **1,947 uncovered functional owners / 298,428 words** and the sibling
**FASED CE owner** remain explicit. Selected CE bits/slots **0/1** retain their
hardware meanings despite global physical indices **1/2**. Native bounded
in-place synthesis passes and rejects **six structural / sixteen coherently
rehashed metadata mutations**, including actual nonfunctional parent-clock
barriers. The native fixture uses **884 LUTs / 590 registers** and retains all
**194** raw parent/readout register clocks. OOC 140 MHz setup/hold estimates are
**+2.672/−0.074 ns**; full-image timing closure remains pending. Fresh EDA SP2
passes **6,541 checks / four cuts / 128 words / 468 response stalls**, continuing
through cycle **409**, with all six debug waveforms. Native/EDA input matching
covers **934 inputs / 33 current sources**. All **21 localhost synthesis / 40
EDA scopes**, **309 checkpoint Python / 40 loop tests** and retained
ASan/UBSan/host/FCFS checks pass. Final receipts, diagnostics and ordered commands
belong under `runs/aws-f2/iteration232/` in `summary.json`,
`recovery-notes.json` and `verification-commands.json`. The fresh ordinary exact
Rocket compiler still rejects the unbound FASED CE owner/common cut. No capture
image or FPGA-origin checkpoint is claimed.

Next: production annotation/XDC projection and actual in-place CE endpoint,
router, widget/MMIO/stream attachment while preserving raw parent control clocks.
Bind all resets, external CE/functional-memory writers, FASED/bridge/software
owners and independent pre-FAME semantics, including physical CE restore.
Full localhost image implementation/timing/AFI/driver binding, active all-hart
F2 captures at early/warm/outstanding/late cuts, FPGA reference continuation,
paired complete zero-edge restores, independent finite replay, sustained live
RTL beyond trace and rolling hardware recovery remain pending. All hardware
migration columns stay pending. Reuse iteration194's localhost invocation.

Both plans and initialized manager YAMLs remain protected inputs. AWS/F2 and
native Vivado 2025.2/HDK/default localhost SSH checks pass. Existing controller
checkpoints were pushed FireSim first and Chipyard second; remote tips match.
The Chipyard push's local tracking-ref update was denied by the sandbox after
remote publication succeeded; retain its exact log. No staging or local commits.
Follow [github-publication.md](github-publication.md). Managed worker startup
failed before creation; all work remains central and no worker remains.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 231,
**in_progress**. `NativeCheckpointInPlace.generate` now banks an existing
concrete instance and routes its sideband through its existing ancestors,
preserving parent control clocks and a separately proven raw readout clock.
It rejects stale executing definitions, ambiguous paths/executions, unsupported
enclosing annotations and nontransparent raw clocks. Scoped one-bit FAME clock
tokens remain explicit data and cannot drive sequential state/effects/gates.
See [f2-native-inplace.md](f2-native-inplace.md).

All **242 Scala tests** pass. Independent exact-Rocket structural auditing
passes over `F1Shim.top.sim`: **10,149 functional descriptors and two separately
composed CE descriptors**, **1,994
selected generated module definitions / 11,590 sequential/effect definitions**;
the existing FASED sibling remains outside that selected scope. Both ancestor
bodies remain unchanged, including **3,840** directly declared register bits.
The bounded fixture synthesizes on native localhost Vivado to **884 LUTs / 590
registers**, checking all **194** raw parent/readout registers. Six rehashed
structural mutations reject. OOC 140 MHz setup/hold estimates are
**+2.672/−0.074 ns**; full-image timing closure remains pending. Forty loop tests
pass. Fresh EDA SP2 in-place execution passes **6,541 checks / four cuts / 128
words / 468 stalls**, continuing through cycle **409**. Semantic and compiled
parent-control faults stop at cut **15**, checks **30/18**; the latter accepts
no bank word. Missing-owner, CE-drift and physical root-mask bypass negatives
also reject, retaining all six hierarchical VCDs. All **21 localhost synthesis /
40 EDA scopes**, **309 checkpoint Python / 40 loop tests**, and retained
ASan/UBSan/host/FCFS checks pass. Current-source results, independent matching,
diagnostics and ordered commands belong under `runs/aws-f2/iteration231/` in
`summary.json` and `verification-commands.json`. The retained structural input
matches the freshly regenerated exact recipe byte for byte; its original source
path remains in the receipt. The ordinary production compiler still rejects
the unbound FASED physical CE owner/common cut.

Next: reconcile the selected/global manifests, project production annotations/XDC and connect these in-place sidebands,
CE endpoint and router to the actual FPGATop widget/stream path, without gating its control/transport
execution. Bind F1Shim reset, all external CE and DRAM writers, complete
FASED/bridge/software owners and independent pre-FAME state; implement physical
CE restore. Full localhost image/P&R/timing/AFI/driver binding, active all-hart
early/warm/outstanding/late hardware cuts, FPGA-reference continuation, paired
independent zero-edge restore, finite replay, sustained live RTL beyond trace
and rolling hardware recovery remain pending. All FPGA-origin migration columns
remain pending; neither a capture AFI nor a hardware checkpoint is claimed.

AWS/F2, native Vivado 2025.2/HDK and default localhost SSH checks pass. Plans and
initialized manager YAMLs remain protected inputs. Existing controller commits
were pushed FireSim first, then Chipyard; staging and local commits remain the
controller's responsibility. Follow [github-publication.md](github-publication.md)
for its next checkpoint. Managed worker startup failed before creation; this
turn remains central only. Initial compiler/fixture-reader corrections and
all underlying diagnostics remain under this iteration's `runs/`.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 230,
**in_progress**. `NativeCheckpointCaptureBinding` now reconstructs and attaches
a bounded native network to the registered FPGATop widget, sharing its raw clock
and controller reset, physical mask/CE sampling and request/response protocol.
Actual FPGATop MMIO and CPU-managed AXI DMA preserve the existing bridge stream
at index zero and allocate checkpoint stream one. The callback must wire all
original non-clock ports, cycle authority and named freeze owners; omitted reset
or owner inputs fail FIRRTL initialization. Embedding an enclosing simulator is
explicitly rejected: complete Rocket F1Shim needs **in-place** production
instrumentation, not another copy of the simulator. See
[f2-native-fpgatop-attachment.md](f2-native-fpgatop-attachment.md).

All **238 Scala tests** pass. Fresh EDA SP2 native-FPGATop execution passes
**15,655 checks / five cuts / 170 words / 1,110 DMA stalls**, at cuts
**16/84/184/324**, then reset recovery at **21** and continuation through **200**.
Semantic and compiled CE faults stop at their first payload mismatch while frozen;
missing-owner/cycle faults acknowledge no target edges. Five hierarchical VCDs
remain. Local native synthesis passes at **4,582 LUTs / 1,726 registers**, with
**1,028** independently audited raw-clock control/transport/DMA registers and six
applied native constraint queries. OOC 140 MHz setup/hold estimates are
**+0.591/−0.095 ns**; full-image timing closure remains pending. Five changed top
connections reject. All **20 localhost synthesis / 39 EDA scopes**, **309 checkpoint
Python / 40 loop tests** and retained ASan/UBSan/host/FCFS checks pass. New
independent native/EDA matching covers **86 inputs / 41 sources**. Final
current-source results, commands, diagnostics and independent audits belong under
`runs/aws-f2/iteration230/summary.json` and `verification-commands.json`.
Exact Rocket native structural regeneration/auditing passes, while the ordinary
production compiler still rejects the unbound FASED physical CE owner/common cut.
The bounded attachment does not admit whole-Rocket capture or restore.

Next: instrument the existing production F1Shim execution in place while keeping
the control/stream path ungated. Bind `F1Shim.reset`, all external CE inputs and
functional DRAM writers, complete FASED/bridge/software owners and independent
pre-FAME semantic state; implement physical CE restore. Complete production XDC
attachment, localhost full-image P&R/timing/AFI/driver binding, actual all-hart
early/warm/outstanding/late F2 capture and FPGA-reference continuation, paired
independent zero-edge restoration, finite replay, sustained live RTL beyond trace
and rolling hardware recovery remain pending. Every FPGA-origin migration column
stays pending. Reuse iteration194's initialized localhost invocation.
No checkpoint-enabled AFI or hardware checkpoint is claimed.

The initialized AWS/F2 and native Vivado/HDK/localhost setup checks pass. Plans
and manager configs remain protected inputs; the controller owns staging and
commits. Existing controller checkpoints were published FireSim first and
Chipyard second; remote tips are checked. Follow
[github-publication.md](github-publication.md) for the next controller checkpoint.
The managed worker failed before creation; all work remains central. Initial
Scala, EDA naming and sync/dependency races and their repairs remain under this
iteration's `runs/` with `recovery-notes.json`.

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 229,
**in_progress**. The native state-access wrapper now emits separately bound
synthesis/implementation constraints at its concrete `network` instance.
`NativeCheckpointConstraints` validates original targets, preserves correlated
native pins and repeated instances, keeps shell-only clauses intact, and retains
distinct pre/post-link placements. A separate independent auditor reconstructs
both original and rebased Tcl from concrete FIRRTL targets. See
[f2-native-state-access-constraints.md](f2-native-state-access-constraints.md).

All **237 Scala tests** pass. Native connected-widget synthesis passes with
**2,637 LUTs / 1,157 registers**, three original/root gates and one falling-edge
mask. Six real cell/pin queries resolve in `access/network`, applied gate
properties/generated clocks are checked, and two deliberate empty queries reject.
Fifteen coherently rehashed RTL/XDC corruptions reject. OOC 140 MHz setup/hold
estimates are **+0.598/−0.104 ns**; full-image timing closure remains pending.
Fresh EDA SP2 passes **6,482 checks / five cuts / 170 words / 210 DMA stalls**;
all six execution VCDs remain. Independent native/EDA matching covers **94 inputs /
34 sources**, rejecting nine evidence corruptions. Semantic/compiled CE faults
stop at cut 63/checks 273/1,036. All **19 native synthesis / 38 EDA scopes**,
**309 checkpoint Python / 40 loop tests** and retained ASan/UBSan/host/FCFS checks
pass. Complete exact-Rocket structural auditing agrees on both hosts over
**2,290 modules / 14,313 sequential/effect definitions**, retaining **12,096
functional + three CE descriptors / 619,016 words**. Its seven constraint
specifications contain six concrete circuit arguments; original shell clauses
remain unchanged. Final evidence and commands belong below
`runs/aws-f2/iteration229/summary.json` and `verification-commands.json`.

The next implementation step remains production FPGATop raw-clock/reset MMIO/
stream and generated-network attachment, using the now-explicit wrapper placement
contract. Bind `F1Shim.reset`, all external CE and functional DRAM writers,
FASED/bridge/host owners and complete independent pre-FAME semantics; implement
physical CE restore. The ordinary production guard still requires a physical
FASED CE owner and common cut. Complete localhost full-image/P&R/timing/AFI/driver
binding, active all-hart F2 capture at early/warm/outstanding/late cuts, paired
independent zero-edge restores, finite replay, sustained live RTL beyond trace,
and rolling hardware recovery remain pending. Every FPGA-origin migration column
stays pending. Reuse iteration194's initialized ExternallyProvisioned localhost
invocation. No checkpoint-enabled AFI or FPGA capture is claimed.

The initialized AWS identity/F2 access and Vivado 2025.2/HDK/localhost SSH checks
pass. Protected plans/configs retain entry hashes. No staging or local commits.
Existing controller checkpoints were pushed FireSim first and then Chipyard;
remote tips are independently checked. The Chipyard push's local tracking-ref
update failed on protected git metadata after remote acceptance. Follow
[github-publication.md](github-publication.md) for the next controller checkpoint.
Final inventory records **zero loop runtime instances / native Vivado or Java
jobs**, and 29 account AFIs without attributing capture support to them. No new
AFI or runtime was requested. Native managed worker startup failed before
creation; the central agent continued alone. Original Scala and native constraint diagnostics and repairs are preserved
in `runs/aws-f2/iteration229/recovery-notes.json`.

## Iteration 228 (retained recovery note)

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 228,
**in_progress**. `NativeCheckpointStateAccess.emit` now emits the same-reference
native network/CE endpoint/router connection, retaining all original ports,
complete descriptor geometry and explicit raw-clock/reset/mask/sample wiring.
The separate binding reconstructs the input banks and clock network and declines
production capture/restore admission. See
[f2-native-state-access.md](f2-native-state-access.md).

The new connected component uses the actual FireSim AXI/MMIO and 512-bit stream
widget with the immutable native descriptor ROM. **236 Scala tests** pass.
Local native synthesis passes at **2,577 LUTs / 1,155 registers**, with three
original/root gates, one falling-edge mask and independently checked raw-clock
response endpoints. OOC 140 MHz setup/hold estimates are **+0.597/−0.074 ns**;
hold closure is pending. Fresh EDA SP2 passes **6,482 checks / five cuts / 170
words / 210 DMA stalls**.
Initial cuts **63/84/184/324** precede reset recovery at cut **21** and continued
execution through cycle **96**. Semantic corruption/compiled CE misconnection
stop at cut 63/checks **273/1,036**. Owner/CE/cycle faults acknowledge no target
edges; all six hierarchical execution VCDs remain. Independent matching covers **89 inputs /
32 sources**; eight coherent structural and nine evidence corruptions reject.
The exact Rocket companion compiles and independently passes native routing
reconstruction, retaining **12,096 functional + three CE descriptors / 619,016
words** and unchanged original ports. All **19 localhost synthesis scopes**, all
**38 EDA scopes**, **309 checkpoint Python / 40 loop tests** and the retained ASan/UBSan/host/FCFS checks pass.
Final source/artifact audits pass. Evidence and exact commands:
`runs/aws-f2/iteration228/summary.json`, `verification-commands.json` and
`artifact-manifest.json`.

Full production ownership remains incomplete: bind `F1Shim.reset`, all external
CE inputs and functional DRAM writers, FASED/bridge/host owners, physical CE
restore and complete independent pre-FAME semantics. Connect the generated
network in production FPGATop with one raw-clock/reset MMIO/stream contract and
rebase/validate XDC against the concrete wrapper instance.
Complete localhost full-image/P&R/timing/AFI/driver binding, active all-hart F2
capture at every cut, paired zero-edge restores, finite replay, sustained live
RTL beyond trace and rolling failure recovery remain pending. The ordinary
production bank admission guard still requires the FASED physical CE owner.
Reuse iteration194's ExternallyProvisioned localhost invocation; every FPGA
migration column remains pending.

AWS identity/F2 access and Vivado 2025.2/HDK/localhost SSH checks pass. No new
AFI or runtime was requested. Protected plans/configs retain entry hashes; no
staging or local commits. Existing controller checkpoints were pushed FireSim
first, then Chipyard; both remote tips match. The Chipyard remote accepted its
push but the protected local tracking-ref update failed; raw output is retained.
Follow [github-publication.md](github-publication.md) for the controller's next
checkpoint. Final inventory has no tagged runtime or local Vivado/Java job. It
records
29 account AFIs, including a newly observed pending Saturn image whose identity
is preserved in `resource-inventory-delta.json`; this turn requested no AFI and
binds none to complete capture. Initial native cell-filter, dependent-input race
and final audit log-location failures and their repairs remain in
`recovery-notes.json`, with original underlying logs. Worker startup failed
before creation; all work is central and no delegated LLM job exists.

## Iteration 227 (retained recovery note)

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 227,
**in_progress**. Native functional banks now compose with the hierarchy-preserving
physical clock-mask network from the **same original circuit**. The generator
independently reconstructs the banks before wiring, retains the original native
BUFGCEs, adds one root mask gate, exports unmasked logical CE and leaves the
response endpoint on `ckpt_clock`. Both translated XDC files remain byte-identical.
See [f2-native-clock-cut-banks.md](f2-native-clock-cut-banks.md).

The exact Rocket recipe compiles and passes complete independent structural
reconstruction: **2,290 module definitions / 14,313 sequential/effect definitions**,
**12,096 functional + three CE descriptors / 619,016 words**, three original
native gates plus the root gate. All six original clock/CE inputs are unchanged.
All **234 Scala tests** pass. The connected native counter/wide-RAM component
synthesizes with **882 LUTs / 462 registers** and independently checked raw-clock
bank endpoints, one falling-edge mask register and no duplicate gates. OOC
140 MHz setup/hold estimates are **+2.672/−0.074 ns**; hold timing and complete
image implementation/timing closure remain pending. Eight coherently rehashed
structural/admission corruptions reject.

Fresh EDA SP2 passes **5,343 checks / 128 words / four physical component
cuts / 468 response stalls**, then continues through cycle **409**. Cuts are
**15/68/183/329**. Payload corruption stops at cycle 15/check 24; an independently
compiled root-mask bypass stops at cycle 15/check 14. Missing-owner and CE-drift
cuts deny reads and remain stopped after host withdrawal. Five full execution
VCDs remain. Independent native/EDA auditing matches **244 inputs / 24 sources**.
Both localhost and EDA independently reconstruct the complete exact-Rocket clock/
bank companion with matching hashes. All **18 localhost synthesis scopes**, all
**37 retained/new EDA scopes**, **309 checkpoint Python / 40 loop tests** and the
retained ASan/UBSan/host/FCFS checks pass. Final execution receipts, commands,
underlying recovered failures and resource inventory belong under
`runs/aws-f2/iteration227/`. Ordinary production admission still rejects the
unbound FASED CE-latch owner. This is a separate clock/bank companion, not a
replacement production image or complete CPU capture.

Next: connect this generated native network to the CE endpoint/router and actual
FireSim MMIO/DMA widget. Bind `F1Shim.reset`, every external CE input/writer,
functional DRAM, FASED/bridge/host and pre-FAME owners to one cut. Resetting the
sampler alone can reopen its mask; complete reset ownership is mandatory. Complete
physical CE restore, localhost full image/P&R/AFI, active all-hart early/warm/
outstanding/late F2 captures, paired independent zero-edge readback, finite replay,
sustained live RTL beyond the trace and rolling hardware failure recovery remain
required. Every FPGA-origin migration column stays pending. Reuse iteration194's
initialized ExternallyProvisioned localhost invocation. No new checkpoint-enabled
AFI, FPGA capture or CPU migration is claimed.

The initialized AWS identity/F2 access and native Vivado 2025.2/HDK/localhost SSH
checks succeed. All native jobs have completed and no loop F2 runtime instance
remains. Account AFI IDs and the earlier pending-state observation remain in
separate inventory receipts; the final AWS query reports all 28 account images
available. This turn requested or modified no AFI and binds none of those existing
images to complete checkpoint capture. Protected plans and four manager inputs
retain their entry hashes. No staging or local commits. Existing controller checkpoints were published
FireSim first (`b53c2d9b`), then Chipyard (`fceaea68`), with remote tips checked
independently. The Chipyard push's local tracking-ref write failed on the protected
filesystem after the remote accepted it; raw output remains under `runs/`.
Follow [github-publication.md](github-publication.md) for the next controller
checkpoint. Managed worker startup failed before creation; the native managed
inventory contains only root and no delegated LLM job exists.

## Iteration 226 (retained recovery note)

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 226,
**in_progress**. Native functional and physical CE descriptor composition now
requires the **same original circuit**. The new factory independently regenerates
the native banks before accepting a result; differing references, coherently
rehashed instrumentation, selector/identity substitutions and unsupported
admission claims reject. The ordinary production descriptor path still rejects
native companions. The new probe emits separate immutable descriptor/endpoint/
host bindings without replacing the normal image or enabling capture coverage.
See [f2-native-descriptors.md](f2-native-descriptors.md).

The exact Rocket recipe compiles with **12,099 descriptors / 619,016 transfer
words**: 12,096 concrete functional owners and three distinct physical CE owners.
Both domains bind the original source, complete native inventory, original CE
dependencies and both translated XDC files. An independent auditor reconstructs
all selectors, word shapes and physical identities. The corrected final compiler
also reproduces all six stock clock/CE inputs used by the retained transport
checks byte-for-byte; original execution paths and receipts remain preserved.

All **233 Scala / 309 checkpoint Python / 40 loop tests** pass. All **17 localhost
component synthesis scopes** pass. The same-reference fixture's real MMIO/stream
widget retains one immutable ROM, matching host metadata and no duplicate gates;
it uses **1,591 LUTs / 764 registers**, with 140 MHz OOC estimated setup/hold
**+0.611/+0.071 ns**. Full image implementation and timing closure remain pending.
Fresh EDA SP2 passes **81 public-port ROM checks** and stops an independently
compiled slot fault at **descriptor 5 / check 11**, retaining two execution VCDs.
Independent native/EDA matching covers **42 inputs / 17 sources** and rejects
**six coherent composition corruptions**. All retained EDA sanitizer/host/FCFS/
bank/memory/clock and CE/network/reset/top/wiring/ROM/widget/router scopes pass.
Native functional readout retains **4,539 checks / 128 words / four cuts /
468 stalls**, the real physical widget **6,810 checks**, and the composed router
**4,912 checks**. The exact Rocket table also passes independent complete EDA
reconstruction with matching native hashes. Complete execution receipts, recovery
notes, hardware gaps and exact commands are under `runs/aws-f2/iteration226/`.

Production still rejects the unbound FASED physical CE-latch owner. Next: connect
the native banks and CE endpoint/descriptor ROM to the generated clock mask,
ungated router and actual MMIO/DMA widget, with complete same-cut reset and
external-writer ownership. Complete simulator/functional-memory/FASED/bridge/
host/pre-FAME coverage and physical CE restore, full localhost image/P&R/AFI,
active all-hart early/warm/outstanding/late F2 captures, independent paired
zero-edge readback, finite replay, sustained live RTL beyond the trace and
rolling hardware failure recovery remain required. Every FPGA-origin migration
column remains pending. No new checkpoint-enabled image, AFI, runtime instance,
FPGA checkpoint or CPU migration is claimed. Reuse iteration194's initialized
ExternallyProvisioned localhost invocation.

Protected plans and all four manager inputs retain their entry hashes. Native
jobs have completed and no loop F2 instance remains. Raw failures and recovery
are retained in `recovery-notes.json`; an intermediate source-stale synthesis
receipt was correctly rejected and rebuilt. No staging or local commits.
Existing controller checkpoints were published FireSim first (`ef77f95d`), then
Chipyard (`c4193c92`), with matched remote tips; these are the already-created
checkpoints, not publication of this turn's dirty edits. Follow
[github-publication.md](github-publication.md) for the next controller checkpoint.
Managed worker startup failed before creation. All work ran centrally; the
managed agent inventory contains only the root agent and no delegated LLM job.

## Iteration 225 (retained recovery note)

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 225,
**in_progress**. The exact Rocket recipe now emits a separate native functional
bank companion: **12,096** concrete storage descriptors, **619,013** transfer
words and all three original BUFGCEs. Native leaves retain their real primitive
identity; synthetic metasim `O` owners are excluded. The new inventory/scope
cannot pass the ordinary descriptor factory or production admission guard.
Original CE/topology, instrumentation and both translated XDC files are bound.
See [f2-native-functional-banks.md](f2-native-functional-banks.md).

The real recipe exposed XDC consumer ordering during companion emission. The
probe now runs the actual `WriteXDCFile` consumer before emitter optimization.
Independent auditing covers every emitted register/RAM owner and shape, all
specialized paths, all transfer words/selectors and the three separate response
registers. The standard production bank path still rejects the unbound FASED
physical latch/common-low-phase owner; this is an opt-in readout companion.

All **230 Scala**, **309 checkpoint Python** and **40 loop tests** pass. Native
fixture synthesis retains two SYNC gates and uses **848 LUTs / 390 registers**.
140 MHz OOC setup/hold estimates are **+5.840/−0.151 ns**; estimated hold timing
fails and full image implementation/timing closure remain pending. Fresh EDA
SP2 passes **4,539** component checks, **128 words / four cuts / 468 stalls**,
endpoint reset recovery and continuation through cycle **405**. Cuts are
**14/66/180/325**. The independent arithmetic/memory oracle compares public
ports with the unmodified reference. A corrupt word stops at cut 14/check 17;
an independently recompiled wrong native CE connection stops at cycle 12/check
1. Three full execution VCDs remain. Native/EDA auditing matches **26 inputs /
13 sources**; six coherent owner/selector/native-RTL substitutions reject.

All **sixteen** localhost component synthesis scopes and the full retained EDA
ASan/UBSan/FCFS/host/bridge/bank/memory/clock/widget/CE/router/reset/top scope pass.
The real widget retains 6,810 checks; the composed ROM retains 126 checks and
its independently compiled slot fault. Complete native/EDA input matching and
coherent evidence-substitution audits pass. The fresh Rocket native companion
also passes independent EDA reconstruction of every storage owner/shape and
matches all eleven source/output hashes with the native audit. Final commands,
underlying recovered failures and explicit hardware gaps are under
`runs/aws-f2/iteration225/`: `verification-commands.json`, `recovery-notes.json`
and `summary.json`. No live localhost Vivado/Java job or loop F2 instance remains.

Next: compose the native functional and physical CE descriptor tables from the
same original circuit, connect the physical mask/ungated bank/MMIO/DMA network,
and bind reset/external-writer ownership. Complete simulator/functional-memory/
FASED/bridge/host/pre-FAME state, physical CE restore, full localhost image/
P&R/AFI, active all-hart early/warm/outstanding/late FPGA captures, independent
paired zero-edge readback, finite replay, sustained live clean RTL beyond the
trace and rolling hardware failure recovery remain required. Reuse iteration194's
initialized ExternallyProvisioned localhost invocation. No new AFI/runtime
instance, FPGA checkpoint or CPU migration is claimed.

Both plans and the four initialized manager inputs retain their entry hashes.
No staging or local commits. Existing controller checkpoints were published
FireSim first (`d4215278`), then Chipyard (`c850ab30`), with matched remote tips.
Follow [github-publication.md](github-publication.md) for the next controller
checkpoint. Managed worker startup failed before creation; all work ran
centrally and no delegated LLM request exists.

## Iteration 224 (retained recovery note)

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 224,
**in_progress**. Immutable descriptor composition now appends generated physical
CE identities/slots to validated functional-bank descriptors. The factory
regenerates the CE endpoint and binds both complete component documents and
circuit references, rather than accepting an unverified physical table. The
widget rejects descriptor/transport physical-count disagreement in both modes;
its synthesized ROM and generated host constructor share the composition hash.
Complete production coverage and physical restore support remain explicitly
false. See [f2-physical-descriptors.md](f2-physical-descriptors.md).

The full Scala scope passes **226 tests**, checkpoint Python **309**, and loop
orchestration **40**. Native synthesis of the real widget with the composed ROM
uses **1,806 LUTs / 767 registers**, one immutable ROM and no duplicate BUFGCEs.
140 MHz OOC setup/hold estimates are **+0.553/+0.071 ns**; full image timing
remains pending. The fixture retains distinct functional and physical reference
circuits; it is not an actual Rocket checkpoint. Current commands and final
execution receipts belong under `runs/aws-f2/iteration224/`.

Fresh EDA SP2 VCS passes **126** public-port ROM checks, all twelve descriptors,
invalid-index alias cases and three reset phases. An independently compiled
physical-slot fault stops at index **9 / check 19**; both full debug waveforms
contain execution. Independent native/EDA auditing matches **34 inputs / 13
sources** and rejects **six** coherently rehashed manifest corruptions.

All **fifteen** localhost component synthesis scopes and the retained EDA
ASan/UBSan/FCFS/host/bridge/bank/memory/clock scope pass. Fresh physical-widget
execution retains **6,810 checks / six cuts / 130 DMA stalls**, complete raw
frames and full debug waves; router/CE/physical-transport/top checks retain
**4,912 / 2,722 / 4,739 per mode / 7,858** comparisons. These remain component
results. The final native inventory has no active Vivado/Java job or loop F2
instance. Execution commands, independent audits and explicit hardware gaps
are recorded in `runs/aws-f2/iteration224/verification-commands.json` and
`summary.json`.

The exact Rocket compiler still rejects the FASED physical BUFGCE CE-latch owner.
Production banks and same-cut reset/external-writer ownership, complete
simulator/functional-memory/FASED/bridge/host/pre-FAME state, physical CE restore,
full localhost image/P&R/AFI, active all-hart early/warm/outstanding/late hardware
cuts, paired independent zero-edge readback, finite replay, sustained live RTL
and rolling hardware failure recovery remain required. Reuse iteration194's
initialized ExternallyProvisioned localhost invocation. No new AFI/runtime or
FPGA checkpoint is claimed. Both plans and the four manager inputs retain their
entry hashes. No staging or local commits. Existing controller checkpoints were
published FireSim first (`771f1111`), then Chipyard (`9a654835`), with independently
matched remote tips. Follow [github-publication.md](github-publication.md) for
the next controller-created checkpoint. Managed worker startup failed before
creation; all work runs centrally and no delegated worker exists.

## Iteration 223 (retained recovery note)

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 223,
**in_progress**. The real FireSim NASTI/MMIO and 512-bit stream widget now has
an explicit physical-cut mode, using the external compiler-generated native
clock network. Typed sideband ports expose the unmasked CE inputs, mask,
captured CE/cycle and read/fault status. The driver header binds the physical
mode and both physical RTL resource hashes. Functional descriptor construction
rejects reserved bank 255; physical mode rejects functional-only immutable
ROMs. Complete physical descriptor composition remains required. See
[f2-physical-widget.md](f2-physical-widget.md).

Fresh EDA SP2 component execution passes **6,810 checks / six complete cuts /
130 DMA stalls**, with independent arithmetic/CRC/descriptor checks of seven
words per cut at **52/84/164/244/324/21**. It runs through target cycle **400**,
then resets an unpublished stalled capture, recovers and runs through **96**.
Abort/drain acknowledgement, missing-owner/CE/cycle faults, a corrupt oracle
and an independently compiled incorrect widget CE connection are exercised.
Failure handling must complete VCS shutdown before returning a nonzero exit;
the independent audit rejects time-zero-only debug waves. For registered AXI,
cut labels equal actual adapter-acceptance target counts, rather than the
late-setup direct-MMIO fixture's +1 offset. Hardware behavior was unchanged.
The native/EDA audit matches **52 inputs / 29 sources** and rejects **eight**
evidence substitutions, including removed owners, coherent widget rewiring,
corrected-CRC semantic corruption, wrong cuts and missing native/negative/debug
artifacts. All **six** full debug waves contain execution timestamps.

All **223 Scala / 309 checkpoint Python / 40 loop tests** pass. Retained
ASan/UBSan/FCFS/host/bridge/bank/memory/clock scope and all **fourteen localhost
component synthesis scopes** pass. The physical widget uses **1,967 LUTs /
830 registers**, one falling-edge mask and no duplicate BUFGCEs; native gates
remain in the external network. OOC 140 MHz setup/hold estimates are
**+0.550/+0.071 ns**; full image implementation timing is pending. Exact Rocket
compilation reproduces all six retained CE input files byte-for-byte and still
rejects the unsupported FASED physical owner. Retained CE/router/top/bank/
clock/reset and independent Rocket dependency/memory audits pass.

This remains component integration. Complete production functional-bank/
physical descriptor/bridge binding, `F1Shim.reset` and external writers,
simulator/functional-memory/FASED/bridge/host/pre-FAME ownership and physical
CE zero-edge metasim restore are pending. Full localhost image/P&R/AFI,
active four-hart early/warm/outstanding/late FPGA captures, paired complete
independent zero-edge readbacks, finite RTL replay, sustained live RTL beyond
the trace and rolling FPGA failure recovery remain required. Reuse
iteration194's initialized ExternallyProvisioned localhost invocation. No new
runtime instance or AFI was created and no FPGA checkpoint was produced.

Protected plans and initialized manager inputs retain entry hashes. No staging
or commits. Existing controller checkpoints were published FireSim first
(`ae01cc3c`), then Chipyard (`679a10fc`), with remote-tip evidence; the local
read-only tracking-ref warning did not prevent publication. The next controller
checkpoint must also be published; follow
[github-publication.md](github-publication.md). Managed worker startup failed
before creation; only the central agent ran and no delegated request remains.
Final scoped inventory has no active loop F2 instance or native Vivado/Java job.
All current commands, receipts, recovered compiler/testbench/waveform diagnostics
and explicit acceptance gaps are under `runs/aws-f2/iteration223/`.

## Iteration 222 (retained recovery note)

Active milestone: `F2-rocket-checkpoint-migration`, iteration 222,
**in_progress**. `CheckpointPhysicalStateRouter` now composes functional-bank
and exact compiler-generated physical CE descriptors/responses with the
physical cut/MMIO/DMA transport. Bank 255 is reserved; invalid descriptors,
wrong CE shapes/order and functional aliases reject. Accepted reads pin their
endpoint through stalls, selector changes and abort/drain; a common reset
cancels routing and all endpoints. See
[f2-physical-state-router.md](f2-physical-state-router.md).

Fresh EDA SP2 passes **4,912 integrated checks / five complete cuts / 36
requests / 91 DMA stalls / 108 delayed functional-bank cycles**, with independent
arithmetic/CRC/descriptor checks for all seven words at cuts **2/19/130/258/302**
and resumed functional execution through **320**. Standalone routing passes
**311 checks / six transactions**. Six runtime negatives, seven host-image
mutations (including physical CE/slot corruption with valid CRCs), five reset
interruption/recovery phases, a corrupt routing oracle and an independently
compiled incorrect routing register retain **fifteen full debug VCDs**.
Independent current-source native/EDA auditing matches **40 inputs / 21
sources** and rejects **thirteen** evidence/owner substitutions.

All **220 Scala / 309 checkpoint Python / 40 loop tests** pass. The retained
EDA ASan/UBSan/FCFS/host/bridge/bank/memory scope completes successfully.
All **thirteen localhost component synthesis scopes** pass. The new composition
uses **1,867 LUTs / 669 registers**, four generated SYNC BUFGCEs and one
falling-edge mask; OOC 140 MHz setup/hold estimates are **+0.593/-0.062 ns**.
Full image implementation timing remains open. Retained standalone CE,
both physical transport modes, physical cut, top, production bank and wiring
VCS scopes pass: **2,722 / 4,739 per mode / 1,968 / 7,858 / 4,669 / 1,813**
checks respectively. Independent Rocket dependency/topology/wiring and all six
memory-corpus audits pass. Final scoped inventory has no active loop F2
instance or native Vivado/Java job; final receipts preserve each scope.

This is component integration, not complete production capture admission.
The exact Rocket production compile still rejects the FASED physical CE owner.
Bind production simulator-bank arbitration/bridge wiring, `F1Shim.reset` and
external writers, complete simulator/functional-memory/timing/bridge/host/
pre-FAME owners and physical CE zero-edge metasim restore before removing that
guard. Full localhost image/P&R/AFI, active four-hart early/warm/outstanding/late
FPGA cuts, paired complete independent zero-edge readbacks, finite replay,
sustained live clean RTL beyond the trace and rolling FPGA failure recovery
remain required. Reuse iteration194's initialized ExternallyProvisioned localhost
invocation. No new runtime instance or AFI was created, and this increment
produced no FPGA checkpoint.

Original launcher-before-emission, native Vivado macro-option and setup-before-
inventory failures are retained with underlying logs; reruns in dependency order
and the native fileset define setting recover them. Plans and initialized manager
inputs retain entry hashes. No staging or commits. Existing controller
checkpoints were published FireSim first (`b07a487c`), then Chipyard (`0f4ed1bf`),
with independent remote-tip evidence. The local read-only tracking-ref warning
did not prevent the remote update. Follow
[github-publication.md](github-publication.md) for the next controller checkpoint.
Managed worker startup failed before creation; only the central agent ran and
no delegated LLM request remains. Exact commands, current receipts and pending
acceptance are under `runs/aws-f2/iteration222/`.

## Iteration 221 (retained recovery note)

Active milestone: `F2-rocket-checkpoint-migration`, iteration 221,
**in_progress**. The exact Rocket compiler now emits a read-only physical CE
bank companion: three distinct physical StateIDs, bank 255 / slots 0-2, one-bit
width/depth-one descriptors and an ungated backpressured response endpoint.
It reads the common-low-phase sampler's unmasked captured CE, with explicit
same-reset/read-enable contracts. The manifest binds the exact reference,
inventory, topology, original CE dependencies and generated RTL bytes. See
[f2-physical-ce-bank.md](f2-physical-ce-bank.md).

All **220 Scala / 309 checkpoint Python / 40 loop tests** pass. The full retained
EDA ASan/UBSan/FCFS/host/bridge/bank/memory/clock scope and all twelve localhost
component synthesis scopes pass. The exact generated CE endpoint plus compiler
three-gate workload/sampler synthesizes on localhost with **202 LUTs / 235
registers**, four native SYNC BUFGCEs and one falling-edge mask. OOC setup/hold
estimates are **+2.063/-0.072 ns** at 140 MHz; full image timing is pending.
Independent concrete-instance reconstruction rejects **14** layout corruptions,
including omitted owners, aliases, metasim O-as-physical IDs and unsupported
capture/restore claims. Fresh EDA SP2 passes **2,722 checks**, **five cuts /
52 reads / 140 stalled cycles**, reset cancellation/recovery and independent
resumed workload checks
through cycle **320**. Every CE bit is observed as both zero and one. The
corrupt oracle and an independently compiled inverted-bit endpoint each stop
at their first bad frozen readout, with three full debug VCDs. Both retained
physical transport modes still pass 4,739 checks, five complete cuts and all
fault/reset cases; physical cut/top/production bank/wiring scopes retain
1,968 / 7,858 / 4,669 / 1,813 checks. Six memory-corpus audits and independent
Rocket topology/wiring/CE reconstruction retain their complete scope.

No complete production capture/restore owner is admitted. The exact Rocket
production compilation still rejects the FASED physical CE latch. The new
endpoint still needs complete bank arbitration and MMIO/DMA composition,
production external reset/writer binding, physical CE zero-edge metasim restore,
and complete simulator/functional-memory/timing/bridge/host/pre-FAME ownership.
Full localhost image/P&R/AFI, active four-hart early/warm/outstanding/late FPGA
cuts, paired independent zero-edge readbacks, finite replay, sustained live
clean RTL beyond trace and rolling FPGA failure recovery remain pending.
Reuse iteration194's initialized localhost build invocation; do not deploy the
component fixture as a checkpoint image. No AFI or runtime instance requested.

The initial native run correctly rejected a verifier edit during execution;
its original source-integrity failure/log is retained. A fresh native run uses
current immutable inputs. Plans and initialized manager inputs retain entry
hashes. No staging or commits. Existing controller checkpoints were published
FireSim first (`af89e1d3`), then Chipyard (`a6b6c72a`); independent remote tips
match. Chipyard's local read-only tracking-ref warning did not prevent the
remote update. Follow [github-publication.md](github-publication.md) for the
controller's next checkpoint. Managed worker startup failed before creation;
only the central agent ran, and no delegated LLM request remains. Final AWS/
localhost inventory has no active loop F2 instance or native Vivado/Java job.
Independent current-source bank audit matches 30 inputs / 12 sources. Exact
commands, final audit, summary and pending requirements are under
`runs/aws-f2/iteration221/`.

## Iteration 220 (retained recovery note)

Active milestone: `F2-rocket-checkpoint-migration`, iteration 220,
**in_progress**. `CheckpointPhysicalCaptureTransport` now connects directly to
the compiler's hierarchy-preserving native clock mask/CE network, using its new
external-network parameter and mask output. A real compiler-generated
three-gate fixture connects this path to the bank/MMIO/DMA transport with no
duplicate gates. Reset now directly asserts DMA abort, fixing a complete
unpublished stream that could otherwise lose invalidation when reset removed
`freeze`. See [f2-generated-clock-transport.md](f2-generated-clock-transport.md).

Fresh EDA SP2 execution passes **4,739 checks in each network mode**, complete
cuts **2/19/130/258/302**, 88 DMA stalls, 128 delayed-bank cycles, accepted-read
abort/drain recovery and continuation through 320 functional cycles. Independent
host arithmetic/CRC oracles check every word; six runtime and four host integrity
negatives remain. Both modes pass five additional reset interruptions: freeze,
outstanding response, stalled data, unpublished completion and physical release.
Each recovers a fresh complete cut and resumes to cycle 64. Both retain twelve
full debug VCDs. Removing only the reset-abort term reproduces the first expected
unpublished-stream divergence in an independently compiled EDA fault injection.

Native localhost generated-network synthesis retains four SYNC BUFGCEs and one
falling-edge mask register: **1,779 LUTs / 660 registers**, estimated 140 MHz
setup **+0.545 ns**, unplaced hold **-0.062 ns**. Full image timing closure is
pending. All **218 Scala / 309 checkpoint Python / 40 loop tests**, the complete
retained EDA ASan/UBSan/FCFS/host/bank/memory/bridge scope, and all **eleven**
native component synthesis scopes pass. Fresh top, production bank, physical
cut and wiring VCS retain **7,858 / 4,669 / 1,968 / 1,813** checks. Independent
Rocket clock topology/wiring/original-CE and six memory-corpus audits pass;
physical/transport/production evidence corruption audits retain their scope.

This binds reset only in the explicit common-reset fixture. Production
`F1Shim.reset`, other external writers, complete simulator/memory/timing/bridge/
host/pre-FAME owners and physical CE StateIDs/zero-edge restore adapters remain
unbound. Exact Rocket production banking still explicitly rejects the FASED
BUFGCE owner. Do not deploy the fixture. Full localhost image/P&R/AFI, active
four-hart early/warm/outstanding/late hardware cuts, independent paired zero-edge
restores, finite replay, sustained live clean RTL beyond trace and rolling
hardware failure migration remain pending. Reuse iteration194's initialized
ExternallyProvisioned localhost invocation. No new runtime instance, AFI or
FPGA-produced checkpoint was requested or claimed; final inventory has no live
loop instances or native Vivado/Java jobs.

The initial EDA fixture compilation had a forward-declared `network_ce` error;
its declaration was corrected, both affected native snapshots were regenerated,
and both full execution scopes pass. The diagnostic launcher's initially
missing script dependency was recovered. Original failures remain in iteration220.
Exact commands, current-source receipts and pending requirements are in
`runs/aws-f2/iteration220/verification-commands.json`, `summary.json`,
`final-audit.json` and `remaining-blockers.json`.

Managed worker startup failed before creation; only the central agent ran and
no delegated LLM request remains. Existing controller checkpoints were published
FireSim first (`1c40186b`), then Chipyard (`92d5c41f`); independent remote tips
match. The local read-only tracking-ref warning did not prevent the Chipyard
remote update. Plans and the four initialized manager inputs retain entry
hashes. No staging or local commits. Follow
[github-publication.md](github-publication.md) for the controller's next checkpoint.

## Iteration 219 (retained recovery note)

Active milestone: `F2-rocket-checkpoint-migration`, iteration 219,
**in_progress**. The exact Rocket compiler now emits original, unmasked CE
combinational dependency prerequisites alongside the separate physical wiring
probe. Repeated/nested hierarchy and implicit synchronous memory pipeline
owners retain exact inventory StateIDs and stopped-clock coverage. The three
native gate cones contain **27/179/179 state terminals (207 distinct owners)**;
the two target gates also depend on external **`F1Shim.reset`**, whose same-cut
owner remains unbound. Unknown/invalid dependencies, combinational cycles and
oscillating/physical clocks used as CE data reject. No functional/deployable
RTL or capture admission changes. See
[f2-physical-clock-dependencies.md](f2-physical-clock-dependencies.md).

Independent concrete-instance reconstruction passes the exact Rocket and mask
fixture, rejects **11** dependency/ownership corruptions each (including
coherently removed external inputs), and agrees on **six** external-input/RAM
cases: asynchronous reads, saved synchronous address/data and both lowered and
emitter readwriters. Existing complete Rocket topology/wiring audits retain
**15/8** negative cases. Native and EDA wiring snapshots match **24 inputs /
12 sources**, now including the dependency manifest and compiler/oracle sources.

All **217 Scala / 309 checkpoint Python / 40 loop tests**, the complete retained
EDA ASan/UBSan/FCFS/host/bank/memory/bridge scope and all **ten** native localhost
component synthesis scopes pass. Fresh EDA SP2 wiring VCS passes **1,813** checks,
complete cuts 0/17/128/256, 64 stalls and 320 functional cycles, with both debug
VCDs and first-divergence rejection. Retained physical-cut/transport/top VCS
passes **1,968 / 4,739 / 7,858** checks; production bank passes **4,669**.
These remain compiler/component results, never FPGA capture or CPU acceptance.

Bind `F1Shim.reset` and complete external writers at the same production cut;
connect production clock/cut/bank and annotation/XDC translation, physical CE
StateIDs and zero-edge restore adapters, ungated MMIO/DMA and complete
functional-memory/timing/bridge/host/pre-FAME ownership next. Exact Rocket
production compilation still explicitly rejects the FASED physical CE owner.
Full localhost image/P&R/AFI, actual active four-hart early/warm/outstanding/late
F2 cuts, independent paired zero-edge restores, finite replay, sustained live
clean RTL beyond trace and rolling hardware failure migration remain pending.
Reuse iteration194's initialized ExternallyProvisioned localhost invocation;
no new instance or AFI was requested. Do not deploy the probe as a capture image.

Initial test-construction compiler-symbol/readwriter-enable failures and
independent-oracle module-name/import-path diagnostics remain in their original
iteration219 logs; corrected full checks pass. Exact commands and individual
receipts are in `runs/aws-f2/iteration219/verification-commands.json`,
`summary.json`, `final-audit.json` and `remaining-blockers.json`.

Managed worker startup failed before creation; only the central agent ran and
no delegated request remains. Existing controller checkpoints were published
FireSim first (`5d06691a`), then Chipyard (`de1575be`); independent remote tips
match. The local read-only tracking-ref warning did not prevent the Chipyard
remote update. Plans and the four initialized manager inputs retain entry
hashes; no staging or local commits. Follow
[github-publication.md](github-publication.md) for the controller's next checkpoint.

## Iteration 218 (retained recovery note)

Active milestone: `F2-rocket-checkpoint-migration`, iteration 218,
**in_progress**. The exact Rocket compiler now emits a separate physical
clock-mask wiring probe: one new root BUFGCE plus all three original native
SYNC gates, ungated source routing to their I pins and a deterministic unmasked
CE vector through repeated/nested hierarchy. Direct type/kind/flow resolution
preserves final emitter operations and memory IR. Independent reconstruction
checks every original driver, storage/reset declaration and clocked effect in
488 reachable module definitions (5,037 consumer definitions); eight coherent
wiring corruptions reject. The topology audit still covers all 13,234
instantiated consumers / 11,459 inventory entries and rejects 15 mutations.
See [f2-physical-clock-wiring.md](f2-physical-clock-wiring.md).

The physical sampler's new external-network mode drives this generated mask
without duplicate gates. Native localhost F2-device synthesis of the connected
64-bit fixture retains three SYNC gates and one falling-edge mask register:
**47 LUTs / 151 registers**, estimated 140 MHz setup **+2.750 ns**, unplaced hold
**-0.072 ns**; implementation timing closure is pending. Fresh EDA SP2 VCS
passes **1,813 checks**, complete cuts **0/17/128/256**, 64 stalled cycles and
continuation through 320 functional cycles. A test-only CE expectation mutation
stops at cycle 17 without acknowledging an edge; two full debug VCDs remain.
These are compiler/component results, never FPGA capture or CPU live acceptance.

All **214 Scala / 309 checkpoint Python / 40 loop tests** pass. The complete
retained EDA ASan/UBSan/FCFS/host/bank/memory/bridge scope passes, including
fresh exact-native-input top VCS (**7,858 checks**), production bank (**4,669**),
default physical cut (**1,968**) and bank/MMIO/DMA transport (**4,739**).
All ten native component synthesis scopes pass. Final native/EDA production
receipts match 28 generated files / 45 sources; the new wiring receipts match
20 inputs / nine sources. Existing production, mapping, physical and transport
corruption scopes pass; original execution evidence is preserved.

The probe does not replace deployable RTL, translate production annotations/XDC
or admit banks. Complete external CE/reset/memory writers, physical CE bank IDs
and zero-edge restore adapters, authoritative FAME target time, functional
memory/timing/bridge/host/pre-FAME ownership and ungated MMIO/DMA binding remain
pending. The exact Rocket production build still explicitly rejects the FASED
physical CE owner. Full localhost image/P&R/AFI, actual active four-hart FPGA
cuts and paired zero-edge/finite/live/rolling CPU migration are still required.
Reuse iteration194's initialized ExternallyProvisioned localhost invocation;
no new instance or AFI was requested. Final scoped inventory has no active loop
runtime or native Vivado/Java job. Do not deploy the probe as a capture image.

Initial final-IR text reparsing, unreachable-extmodule audit selection,
source-change-during-synthesis and vendor-global-reset startup failures retain
their original logs. The fixes preserve original IR, restrict primitive choice
to reachable native owners, pin final sources and respect vendor startup.
The evidence audit found a missing fresh top fixture and the full check was
subsequently run. Exact commands, final component receipts, `summary.json`,
`final-audit.json` and `remaining-blockers.json` are under
`runs/aws-f2/iteration218/`.

Managed worker startup failed before creation; only the central agent ran and
no delegated request remains. Existing controller checkpoints were published
FireSim first (`266d3f31`), then Chipyard (`421e0c42`); independent remote tips
match. The local read-only tracking-ref warning did not prevent the Chipyard
remote update. Plans and the four initialized manager YAMLs retain entry
hashes. No staging or local commits. Follow
[github-publication.md](github-publication.md) for the controller's next checkpoint.

## Iteration 217 (retained recovery note)

Active milestone: `F2-rocket-checkpoint-migration`, iteration 217,
**in_progress**. The exact Rocket compiler now emits a physical common-source
clock plan from its final emitted netlist: three native default-SYNC BUFGCEs,
2,107 clock pins, 13,234 sequential consumers and clock coverage for every one
of the 11,459 simulator inventory entries. All sequential origins resolve to
root input `clock`. The analysis handles final instance connectors and memory
pipeline owners without changing the netlist. Physical latch StateIDs remain
separate from metasim O owners. Independent reconstruction rejects 15 coherent
plan/binding corruptions. See [f2-physical-clock-plan.md](f2-physical-clock-plan.md).

The plan does not rewrite clocks, prove CE dependency closure, supply capture
owners or remove the strict physical bank guard. Actual generated root/derived
clock rewiring, CE bank/restore mappings, complete memory/timing/bridge/host and
pre-FAME common-cut ownership, full localhost image/P&R/AFI, active four-hart
FPGA cuts and paired zero-edge/finite/live/rolling CPU migration remain pending.
Reuse iteration194's initialized ExternallyProvisioned localhost invocation.
No new runtime instance or AFI was requested. Do not deploy this topology-only
emission as a checkpoint-enabled image.

Fresh 212 Scala / 309 checkpoint Python / 40 loop tests, the retained EDA
ASan/UBSan/FCFS/host/bank/memory/bridge scope and nine native localhost component
synthesis checks pass. Final native/EDA production audits match 28 generated
files and 44 sources; fresh bank/top/memory-policy VCS checks pass 4,669 /
7,858 / 21,970 comparisons. Physical-cut/transport VCS retain 1,968 / 4,739
checks and debug waveforms. Ten transport evidence substitutions reject with
162 original execution files preserved. Native and EDA Rocket clock-plan
audits match. Exact commands, `summary.json`, `final-audit.json` and
`remaining-blockers.json` are under `runs/aws-f2/iteration217/`. Final scoped
inventory has no active loop runtime or native Vivado/Java job.
Initial connector-reachability and independent-audit
canonical-hash/clocked-effect-identity failures remain in their original logs.
The corrected actual Rocket compiler and independent topology audit pass.

Managed worker startup failed before creation; only the central agent ran.
Existing controller checkpoints were published FireSim first (`53d08591`), then
Chipyard (`b30e3dff`); independent remote tips match. The local read-only remote
tracking-ref warning did not prevent the Chipyard remote update. Plans and the
four initialized manager YAMLs remain read-only. No staging or local commits.
Follow [github-publication.md](github-publication.md) for the controller's next
checkpoint.

## Iteration 216 (retained recovery note)

Active milestone: `F2-rocket-checkpoint-migration`, iteration 216,
**in_progress**. Added `CheckpointPhysicalCaptureTransport.sv`, connecting the
physical common-low-phase sampler to descriptor/bank/MMIO/DMA transport.
`CheckpointCaptureCut.DEFERRED_CUT=1` samples the settled target label only after
all owners acknowledge; its default preserves accepting-edge behavior. External
owners stay held through registered physical release. Physical faults suppress
transfers and remain stopped after host abort; healthy accepted-read aborts
drain before a later capture. See
[f2-physical-capture-transport.md](f2-physical-capture-transport.md).

Fresh native localhost OOC synthesis retains four native SYNC gates and exactly
one falling-edge mask register: **1,810 LUTs / 660 registers**, estimated 140 MHz
setup slack **+0.545 ns**, unplaced hold slack **-0.062 ns**. Full implementation
timing is pending. EDA SP2 VCS passes **4,739 checks**, five complete component
cuts **2/19/130/258/302**, 88 DMA stalls, 128 delayed-bank cycles and one
accepted-read abort/drain followed by a healthy capture through 320 functional
cycles. Independent host arithmetic/CRC audits cover every banked word and
label. Six runtime negative cases, including failed physical release and corrupt
CE readback, plus four host integrity cases including semantic corruption with
valid recomputed CRC, reject. Seven full debug VCDs are retained. Ten native/EDA evidence substitutions,
including coherent source rehash and altered models/waves, reject with all 162
original evidence files preserved. These are
component results, not CPU semantic-corruption or hardware checkpoint acceptance.

All **207 Scala / 309 checkpoint Python / 40 loop tests** and the complete
retained EDA ASan/UBSan/FCFS/host/bank/memory/bridge suite pass. Nine native
component synthesis checks pass. The exact Rocket compiler still explicitly
rejects `F1Shim.top.FASEDMemoryTimingModel_0.gate`; its complete generated physical
clock/CE/state ownership binding, memory/timing/bridge/host/pre-FAME common cut,
localhost full image/P&R/AFI, active four-hart hardware cuts and paired CPU
zero-edge/finite/live/rolling hardware migration remain pending. The initialized
iteration194 ExternallyProvisioned localhost invocation is retained. No new
instance or AFI is requested.

Managed worker startup failed before creation; only the central agent ran and
no worker remains. Existing controller checkpoints were pushed FireSim first
(`b98ec73c`), then Chipyard (`75b2c0fb`); independent remote tips match despite
the read-only local Chipyard remote-tracking ref warning. Current edits remain
for the controller to stage/commit. Plans and all four initialized manager
configs retain entry hashes. Follow
[github-publication.md](github-publication.md).

The first integrated VCS trial found a test-oracle error during the deliberately
aborted fifth transfer; its original failing log is retained. The corrected
oracle also independently checks CRC and arithmetic state. A synthesis trial
was explicitly rejected as source-stale during release-hold review; the final
native synthesis and VCS use matching final sources. Diagnostic logs, exact
commands, native/EDA receipts and remaining blockers are under
`runs/aws-f2/iteration216/`. `verification-commands.json`, `summary.json`,
`final-audit.json`, `physical-audit.json`, `production-audit.json` and
`remaining-blockers.json` locate the complete evidence. Final scoped AWS/native
inventory finds no active loop runtime, Vivado or Java job. Do not relabel
component state as an FPGA capture.

## Iteration 215 (retained recovery note)

Active milestone: `F2-rocket-checkpoint-migration`, iteration 215,
**in_progress**. Added a synthesizable common-clock physical cut component,
`CheckpointPhysicalClockCut.sv`, retaining the native default-SYNC BUFGCEs.
It masks a root gate and three example physical gates during their common low
phase, samples the complete unmasked logical CE vector and post-stop target
label, and keeps transport/control running. Missing owners, CE drift and cycle
drift withdraw read permission and latch fail-stop errors. Registered release
checks faults before unmasking, including simultaneous host withdrawal.
See [f2-physical-clock-cut.md](f2-physical-clock-cut.md).

This is a component with explicit single-source/positive-edge/complete-owner
obligations, **not yet wired into the Rocket compiler, bank network or bridge**.
The original accepting-edge cut coordinator cannot simply reuse its cycle label
for this delayed physical handshake. Preserve the strict compiler guard until
all root/derived clocks, CE drivers, memory/timing/bridge/host and pre-FAME
owners are bound at the same target cut. The fresh exact Rocket trial still
rejects `F1Shim.top.FASEDMemoryTimingModel_0.gate`; no full image is emitted.
Reuse iteration194's initialized ExternallyProvisioned localhost invocation.

Fresh native synthesis retains four SYNC BUFGCEs and exactly one falling-edge
mask register: **216 LUTs / 232 registers** including the functional fixture.
The initial combinational release path missed 140 MHz estimated setup timing
by 0.523 ns; registered validation yields **+2.657 ns** setup slack. The
unplaced report still has **-0.072 ns** hold slack: no implementation timing
closure is claimed. Original synthesis trials/receipts remain unchanged.
Fresh SP2 EDA VCS passes **1,968 checks**, complete cuts **0/17/128/256**, 64
transport stalls and 320 functional cycles against original native vendor
gates and independent state/edge oracles. Every logical CE is independently
checked against the uninstrumented vendor latch at each low cut; masked physical
latches are separately checked zero. Missing-owner/CE-drift/cycle-drift cases
stay stopped; corrupted readback expectation stops at CE bit 0 at cut 17 before
another functional edge. Five full debug VCDs are retained. Native/EDA/source
identity and eight evidence corruption cases, including coherent RTL rehash,
pass. These results establish neither CPU migration nor semantic corruption
acceptance on an actual CPU.

All **207 Scala / 309 checkpoint Python / 40 loop tests** and retained EDA
ASan/UBSan/FCFS/host/bank/memory/bridge scope pass. Eight current native component
synthesis checks pass. Complete FPGA common-cut/ownership integration, full
localhost image/P&R/AFI, actual four-hart active-workload hardware cuts, matching
FPGA Level-1/Level-2 zero-edge restores, finite/live CPU comparison beyond trace
and rolling hardware recovery remain pending. No runtime/AFI was requested.

Managed worker startup failed before creation; only the central agent ran and
no worker remains. Existing controller checkpoints were published FireSim first
(`9b0bdfe3`), then Chipyard (`95a7ebc4`); independent remote tips match despite
Chipyard's read-only local remote-tracking update error. New edits remain for
the controller to stage/commit. Plans and all four manager configs retain their
entry hashes. Follow [github-publication.md](github-publication.md).
The first final-audit wrapper failed because a retained native receipt's manager
absolute paths were not mapped when auditing on EDA. The audit now resolves both
original roots without altering receipt provenance; the original failed log is
retained and the complete final EDA retry and local final audit pass. Final
scoped AWS inventory finds no runtime instance or native Vivado/Java job.
Exact commands, scope, source hashes, remaining compiler error and
final results are under `runs/aws-f2/iteration215/`: `verification-commands.json`,
`remaining-blockers.json`, `physical-audit.json`, `final-audit.json`, `summary.json`.

## Iteration 214 (retained recovery note)

Active milestone: `F2-rocket-checkpoint-migration`, iteration 214,
**in_progress**. The actual `SimulationMapping` linker now replaces its exact
validated external target placeholder and returns native circuit/module renames,
so the absolute target boundary and all local/nonlocal annotations follow
`TargetBox` to `FAMETop` together. It rejects ambiguous repeated instances,
stale/foreign/relative paths, malformed namespaces, missing definitions and
incompatible lowered interfaces. Strict downstream bank validation is unchanged.
See [f2-simulation-mapping.md](f2-simulation-mapping.md).

The exact Rocket recipe now passes the stale TargetBoxAnnotation barrier and
explicitly rejects physical `BUFGCE` enable-latch state at
`F1Shim.top.FASEDMemoryTimingModel_0.gate`. A synthesized capture owner and common
low-phase cut are still required; the metasim output register cannot establish
that ownership. No full Rocket bank/capture image is emitted. Reuse
iteration194's initialized ExternallyProvisioned localhost build invocation.

All **207 Scala / 309 checkpoint Python / 40 loop tests** and the retained EDA
ASan/UBSan/FCFS/host/bank/memory/bridge scope pass. Seven native Vivado component
synthesis jobs pass. The new linked-boundary fixture uses **44 LUTs / 18 registers**
and passes **595** fresh SP2 VCS checks over 256 functional cycles, complete bank
cuts 0/17/128/256 and sixteen response stalls, against unchanged original RTL and
an arithmetic oracle. Corrupt bank readout fails at cut 17 before any further
functional edge. Healthy/failed full debug VCDs are retained. Native/EDA matching
covers **11 generated files / 8 current sources**; nine independent boundary,
reference and owner corruptions reject, including a coherently changed owner.
Retained production-bank/top audits match 28 files / 41 sources and pass
4,669 / 7,858 checks, plus 21,970 synchronous-policy checks. These are compiler/
component results; CPU/F2 zero-edge/finite/live acceptance remains pending.

Physical CE-latch/common-cut ownership, complete memory/timing/bridge/host and
pre-FAME binding, full localhost image/P&R/AFI, all-four-hart active early/warm/
outstanding/late hardware cuts, paired CPU restores/live comparison beyond trace
and rolling hardware recovery remain pending. No new AFI or runtime was
requested. Plans and the four manager YAMLs retain their entry hashes; no staging
or local commits. Existing controller checkpoints were published FireSim first
(`db522bae`), then Chipyard (`7baa5956`); the Chipyard remote-tracking update
reported read-only metadata after the push, and independent remote-tip checks
confirm publication. Follow [github-publication.md](github-publication.md).

Managed worker creation failed before startup; only this central agent ran and
no delegated worker remains. Initial native-test harness, VCS testbench syntax,
compiler-diagnostic parser and coherent-negative audit setup failures remain in
original logs. The final native/EDA audit uses a separate artifact exchange,
after an initial audit reached EDA before native-top outputs were transferred.
Exact commands, compiler failure, protected inputs and receipts are under
`runs/aws-f2/iteration214/` relative to the loop: `verification-commands.json`,
`remaining-blockers.json`, `mapping-audit.json`, `final-audit.json` and `summary.json`.
Hardware acceptance remains incomplete.

## Iteration 213 (retained recovery note)

Active milestone: `F2-rocket-checkpoint-migration`, iteration 213,
**in_progress**. Added exact native RAMStyleHint logical-memory contracts and
fixed the actual final WriteXDCFile consumer to emit late public host-widget
constraints as well as internal constraints. Specialization preserves class,
instance path, memory identity and annotation provenance. Only the five native
synthesis templates on one retained memory are accepted; arbitrary memory XDC,
ports/indices, registers, foreign/dead paths and regexp-active explicit names
remain unsupported. See [f2-ram-style-constraints.md](f2-ram-style-constraints.md).

The exact Rocket compiler passes the FIFO RAM-style XDC barrier. It now rejects
`target-box instance path mismatch: ~F1Shim|F1Shim/top:FPGATop/sim:SimWrapper/target:TargetBox`.
Independent inspection of retained post-SimulationMapping FIRRTL finds
`SimWrapper.target of FAMETop`. Next: repair TargetBoxAnnotation at the actual
TargetBox-to-FAMETop hierarchy/rename producer, preserving exact target-boundary
identity; do not drop it or guess a substitute. This mismatch predates the final
inline pass in the retained input. No whole-Rocket bank or capture image emits.

All **198 Scala / 309 checkpoint Python / 40 loop tests** pass, including the
actual final compiler path for late public constraints. The retained full EDA
ASan/UBSan/FCFS/bank/memory/bridge/host scope passes. Native Vivado reads the actual
emitted XDC for two initialized RAM banks and retains **18 bit planes / 36 read-port
copies**, with `RAM_STYLE=distributed` on all **54** cells. Initialized storage uses
**77 LUTs / 11 registers**. Fresh SP2 VCS passes **1,870** checks, **69** reads,
**276** stalls, four complete cuts (including zero-edge readout), **166** functional
edges and **587** observations against original RTL, retaining a full debug VCD.
The independent RAM-style audit rejects **12** corruptions, including coherent
annotation rehashes; four native RAM property/initialization corruptions reject.
Final native/EDA matching covers **16 generated files / 10 current sources**;
retained bank/top audits also pass. Complete results are recorded in `runs/aws-f2/iteration213/final-audit.json`.

The physical CE-latch/common-low-phase atomic cut, complete memory/timing/bridge/
host/pre-FAME binding, full localhost image/P&R/AFI, all-hart early/warm/outstanding/
late FPGA cuts, paired CPU zero-edge/finite/live continuation beyond trace and
rolling recovery remain pending. Reuse iteration194's localhost build invocation
and initialized manager configs. No new AFI or runtime was requested. Plans and
manager inputs retain their entry hashes; no staging/local commits. Existing
controller checkpoints were published FireSim first (`eb51ab80`), then Chipyard
(`39623f90`), and remote tips independently match. The Chipyard push updated GitHub
but could not update the local remote-tracking ref on the read-only metadata
filesystem; exact push output is retained. Follow
[github-publication.md](github-publication.md) for the next controller checkpoint.

Managed worker startup failed before creation; all work ran centrally with no
worker remaining. Initial syntax/blank-line test failures and source-change guard
failures remain in original logs; final full tests and immutable-source retries
are separate. Exact commands, inventory and individual receipts are under
`runs/aws-f2/iteration213/` relative to the loop: `summary.json`,
`verification-commands.json`, `remaining-blockers.json`, `target-box-path-audit.json`
and `final-audit.json`. Hardware acceptance remains incomplete.

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

## Iteration 198: physical-constraint and memory-label clone contracts

Internal/external XDC targets retain their common explicit root and correlated
arguments for each concrete clone; nested instance module names are rewritten.
Global snippets remain singletons. Ground nets/ports, concrete instances and
instance ports are validated; foreign/unreachable/opaque/mismatched/aggregate
references and format-count errors reject. External XDC remains its original
annotation class rather than being silently promoted into emitted constraints.
Memory-model labels translate onto actual retained logical RAMs, with source,
translated annotation and mapping provenance. Dropping/changing translated
labels or constraints rejects descriptor construction. Repeated-root constraints
produce identical physical paths through the real WriteXDCFile pass before and
after instrumentation; independent target-pair checks forbid cross-instance
constraints. The production bank receipt additionally binds exact synthesis and
implementation XDC bytes, refusing missing/duplicate output files.

The first native trial returned 0 despite Constraints 18-401/18-512 diagnostics
because the fixture used an input clock as a timing endpoint. It is explicitly
rejected. The repaired fixture constrains scalar reset paths; the verifier now
rejects constraint warnings and requires retained DCP commands plus the actual
DONT_TOUCH cell property. An intermediate verifier inspected only the DCP late
constraint file; Vivado had correctly stored both commands in its regular XDC.
That failed verifier run and its DCP remain diagnostic. Validation now inspects
all DCP XDC members without discarding any constraint requirement.

All 113 Scala tests and complete retained EDA bank/bridge/host/memory/FCFS
ASan/UBSan, 306 Python and 40 loop tests pass. The matched production-bank
fixture passes 4,669 checks / 1,025 edges at cuts 2/39/132/900; a corrupt first
word stops frozen at cycle 2. Exact native-input MMIO/DMA top VCS passes 7,858
checks. Full debug VCDs remain. Native Vivado 2025.2 OOC synthesis retains
125 LUTs / 82 registers, setup +6.478 ns / hold +0.081 ns at 140 MHz, with
external I/O unconstrained. Independent EDA auditing matches all nine generated
files / 14 sources, validates DCP constraints and rejects six missing or
coherently rehashed dropped/retargeted/extra XDC cases. Final scoped inventory
finds no owned F2 instance or native Vivado/Java build job. Actual production compilation
still exits 1 on 22 unsupported annotation classes: stage/pass/deleted/opaque,
bridge/channel, dedup/pre-link/target-box and remaining output contracts.
No full image, AFI request, FPGA checkpoint, CPU restore or rolling/live CPU
acceptance is established. The existing controller checkpoints were published
FireSim first then Chipyard; the latter remote update succeeded with the
read-only local tracking-ref error retained. Both plan inputs remain unchanged.
Managed-worker startup failed twice before any worker was created; all work
stayed in the central turn and no delegated job remains. Final receipts and
raw commands: `runs/aws-f2/iteration198/summary.json` relative to the loop.

## Iteration 197: production FPGA constants and hierarchy annotation contracts

The exact Rocket production run selects the pinned `plusarg_reader.v` SYNTHESIS
branch explicitly after FPGA lowering. Preparation and final emission receipts
bind original/prepared references, every source/parameter/definition and all
repeated instances. An independent parser compares every unchanged definition
and rejects eight classes of coherently rehashed corruption. Source-selected
constants are not physical storage; the three active BUFGCE owners remain
unsupported. The original metasim path retains its seven init-only model words.

NoDedup and legacy circuit/module/exact-instance Inline requests translate to
all concrete clones and participate in descriptor hashes. Foreign, unreachable,
opaque and non-instance targets reject. Standard SV emission retains pending
Inline requests without consuming or flattening the bank hierarchy. Any future
pass that consumes those requests needs a new complete mapping contract.
Only the passive blackbox-output directory annotation bypasses translation;
unknown/deleted/bridge/channel/XDC/memory contracts still reject explicitly.
The actual full bank compile exits 1 with 25 unsupported classes and emits no
accepted whole-Rocket bank RTL. Its complete failing native log is retained.
The final audit rejected an early native probe receipt after a source edit
occurred during synthesis; its snapshot/hash mismatch remains diagnostic.
Both new branch and production-bank verifiers now hash their immutable source
snapshots and reject live generated/source changes before and after execution.
Affected native and VCS runs are regenerated under `*-guarded/`; old receipts
are preserved. The first final-audit sync also hit a vanished Git index lock;
its exit-24 log remains separate from retries. Neither failure is acceptance.

Fresh EDA VCS SP2 checks compare production-selected constants with both the
unmodified model under SYNTHESIS and ordinary runtime plusargs. Each variant
passes 2,050 comparisons / 1,025 fixture edges; a wrong component oracle stops
at cycle 0 with zero acknowledged edges. All runs retain full debug VCDs.
This is branch/compiler evidence, not CPU checkpoint or semantic-corruption
acceptance. Native Vivado 2025.2 OOC synthesis of identical inputs uses 22 LUTs /
32 registers, estimated setup +6.443 ns / hold +0.065 ns at 140 MHz; external I/O
is unconstrained. Full retained bank/bridge/host/FCFS sanitizers, dense 780-word
reconstruction, native primitive contracts and exact-native-input MMIO/DMA top
checks remain in the verification scope. Both source plans are unchanged.
Existing controller checkpoints were pushed FireSim first, then Chipyard;
Chipyard's remote update succeeded despite the local tracking-ref write error.
No worker or native build job remains; scoped inventory finds no owned runtime
instance. Full image, hardware cuts, complete memory/host/cut ownership,
independent paired CPU restores, finite/live RTL and rolling FPGA recovery
remain pending. Commands and immutable receipts: `runs/aws-f2/iteration197/`.

## Iteration 196: reachable physical-owner audit and native gate contract

`GeneratedClockGateAdapter` checks only reachable instances, retains source
identity and leaves unsupported annotation admission intact. New regressions
verify unused definitions, reachable missing implementations, unknown unused
inline annotations, repeated children, missing/recursive/duplicate hierarchy
and final emitter instance connectors. A mixed live/dead gate regression also
checks that the resolver cannot collide on a shared Verilog defname. Resolution
uses the reachable graph only after complete inventory and annotation admission;
targeted preservation/initialization on dead modules explicitly rejects before
compiler cleanup can erase it. All **101 Scala tests** pass. The first
new unused-gate fixture conflicted with FIRRTL's concrete defname rule; the
corrected fixture and full rerun are retained separately from that failure.

The compiler emits `.simulator-external-owners.json` with the exact final
reference hash, per-definition/inline-source hashes and distinct reachable vs
unused records; `.simulator-emission.json` binds it and Make tracks it. An
independent Python traversal verifies all 2,293 instances, ten reachable
external owners and eleven unused definitions; eight corruption tests cover
omission, duplication/reordering, definition/root/reference changes, forged
capture/adapter claims and malformed source provenance. The ordinary exact
Rocket build inventories 11,466 entries / 618,254 words. These are generated
RTL/model inventories, not complete physical state. Seven plusarg instances
still require explicit source-checked SYNTHESIS selection. Three active
BUFGCEs need physical-state/common-cut mapping: the FASED gate and the two
FAME clockBridge buffers. Both AbstractClockGate definitions are unused.

The exact installed unmodified Vivado 2025.2 BUFGCE/glbl model, retained MIDAS
abstract implementation and stock metasim model run together on EDA VCS SP2.
**3,658 checks / 682 phase observations / 256 source edges** pass. The vendor
SYNC model and stock metasim observe 110 positive edges; the abstract model
observes 183, including **73 extra pulses** on enable deassertion. The vendor
model's low-transparent CE latch holds across 170 high-phase CE changes.
The HARDSYNC specialization observes 109 edges in this window and is recorded
separately. A deliberately wrong expected signal stops at source edge 4.
Both runs retain full debug VCDs. The first harness counted an uninitialized
startup event; its raw failure is preserved and counters now explicitly start
after initialization. This is model-contract evidence, not an FPGA capture or
CPU semantic-corruption acceptance test. AMD's
[BUFGCE documentation](https://docs.amd.com/r/2022.2-English/ug974-vivado-ultrascale-libraries/BUFGCE)
distinguishes SYNC, ASYNC and HARDSYNC behavior.

Fresh actual production bank compilation now reaches strict annotation
preflight, then exits **1** with 28 unsupported annotation classes, including
clock/channel, bridge, memory-model, XDC, inline/rename and opaque contracts.
The native full diagnostic remains an explicit failed trial; no source check
is relaxed and no full Rocket bank output is claimed. Translate these owners
explicitly and implement physical primitive/common-cut and functional-memory/
host binding before image P&R/AFI. All four active hardware cuts, complete
paired zero-edge CPU restores, finite replay, sustained live RTL/debug waves
and rolling hardware recovery remain pending. No hardware matrix status is
advanced. Preserve the historical iteration-195 audit at its actual path;
its reported missing temporary filename was not fabricated or repaired by
relabelling a different run. This iteration reports only verified nonempty
individual files and publishes a stable current audit copy.

Full **101 Scala / 298 checkpoint Python / 40 loop** regressions and the
retained EDA bank/Widget/host/FCFS ASan/UBSan scope pass. Production bank-path
VCS again passes 4,669 checks; host-path outputs pass 4,100 comparisons. Top
MMIO/DMA passes 7,858 checks using exact native synthesis inputs. Local Vivado
OOC synthesis passes for both fixtures (bank 44 LUTs / 26 registers; top 3,542
LUTs / 1,383 registers). These remain fixture measurements. Independent EDA
checks verify all source/generated/DCP hashes, complete instance reachability,
all 780 dense words and actual delta-cycle VCD counts (physical/metasim 110,
abstract 183). Its immutable native receipt has an explicit remote path;
`runs/aws-f2/iteration196/final-audit.json` is the stable current copy, verified
nonempty locally. All reported artifacts are individual files.

Fresh AWS access succeeds and the scoped inventory records no owned runtime
instance or remaining native Vivado/Java job. No AFI request or duplicate build
farm was launched. Existing controller checkpoints were pushed FireSim first
(`bae5e119`), then Chipyard (`d42e937f`); independent remote tips agree. The
successful Chipyard remote update retains the local read-only tracking-ref
error. Native managed worker startup failed before a worker began; final
agent inventory is root only. No staging/commits or plan/conda/archive edits;
plan hashes match the start of the iteration. Exact commands, source snapshots,
failed and successful logs, provenance and all pending physical/CPU acceptance
are cataloged by `runs/aws-f2/iteration196/summary.json` relative to the loop.

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

## Iteration 199: explicit inert compiler context at the bank boundary

Eight parser/config/output/enum-type annotation contracts now preserve complete
values through the real host-to-FPGA compiler without treating them as storage
owners. The context sidecar binds both actual IR representations and final
emission; unknown annotations, pass requests, stale circuits, targeted enums
and arbitrary output payloads remain unsupported. Duplicate options and
conflicting enum definitions reject. The exact Rocket production compiler
exits 1 on 14 remaining contracts and emits no accepted whole-Rocket banks.

All 119 Scala, 306 checkpoint Python and 40 loop tests, full retained EDA
ASan/UBSan/FCFS/bank/bridge/host regressions, 4,669 bank and 7,858 exact-native
top VCS checks pass. Independent native/VCS/DCP/source auditing rejects ten
context and six XDC corruptions, including coherently rehashed changes. The
component DCPs are from localhost Vivado 2025.2, not full image builds. No new
AFI request, FPGA capture or CPU migration is established. Final inventory has
no owned runtime instance or native Vivado/Java build job. Next work needs
explicit contracts for the remaining stage/pass/deleted/opaque/bridge/channel/
pre-link/target-box/output annotations, physical BUFGCE ownership and complete
common-cut/memory/host/semantic integration before full image/P&R/AFI and
hardware cuts. Existing controller commits were pushed in the required order;
no worker or delegated request remains. Receipts: `runs/aws-f2/iteration199/`.

## Iteration 200: memory policy and inventory-order contracts

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

## Iteration 201: target-box hierarchy specialization

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

## Iteration 202: consumed inputs and channel clock metadata

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

## Iteration 203: deduplication-history specialization

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

## Iteration 205: retained recovery note

Active milestone: `F2-rocket-checkpoint-migration`, iteration 205,
**in_progress**. BridgeExtraction now consumes temporary instance markers and
retains immutable historical circuit/connectivity hashes and bridge identities.
Repeated bridge-bearing modules and pass reuse are covered. Actual Rocket
production preflight rejects **5 annotation classes**, down from 6; whole-Rocket
banks, complete physical state coverage and the checkpoint-enabled image remain
pending.

All **149 Scala / 306 checkpoint Python / 40 loop tests**, full retained EDA
ASan/UBSan/FCFS scope, localhost Vivado bank/top OOC synthesis and independent
EDA audit pass. VCS checks: 4,669 bank / 7,858 MMIO-DMA top / 21,970 synchronous
policy. Twenty-five new extraction corruptions reject alongside every retained
history/context/XDC/policy/target-box case. Full FPGA capture and paired CPU
zero-edge/finite/live/rolling migration remain pending. Commands and individual
files: `runs/aws-f2/iteration205/summary.json`; see
[fpga-capture-transport.md](fpga-capture-transport.md).

Existing controller checkpoints were published FireSim first (`0724e2c4`), then
Chipyard (`3bf3bd4f`); independent remote tips agree. Chipyard's local tracking
ref update warned read-only after the successful remote push. Current edits
await the loop controller's checkpoint/publication; follow
[github-publication.md](github-publication.md). AWS access checks pass; final
scoped inventory has no owned F2 instance or native Vivado/Java job. No new AFI
was requested. Managed-worker startup failed before creation; the central agent
completed the work, and no worker remains. Plans are unchanged, with no agent
staging or commits. Initial fixture compile/expectation failures remain under
`runs/aws-f2/iteration205/`; corrected full-suite logs establish the passes.


## Iteration 206: consumed stage circuit identity

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

## Iteration 207: passive generated-output provenance

The bank compiler now retains exact driver/header/define artifact bytes with
suffix, UTF-8 size and hash in compiler context and final emission. It rejects
unknown/IP scripts, duplicate suffixes, malformed/default-charset-mismatched
bodies and missing/changed outputs or generated sidecars. Independent EDA audit
rejects 20 missing or coherently rehashed output corruptions, including swapped
bodies, Unicode byte counts and legitimate empty maps. All 159 Scala / 306
checkpoint Python / 40 loop tests and full retained EDA ASan/UBSan/FCFS scope
pass. Native bank and MMIO/DMA-top OOC synthesis pass; matching SP2 VCS checks
are 4,669 / 7,858, plus 21,970 synchronous-policy checks. Audit matches 22
files / 27 sources. Bank resources/timing remain 125 LUTs / 82 registers,
setup +6.435 ns / hold +0.054 ns at 140 MHz, external I/O unconstrained.

Actual Rocket preflight rejects three annotation classes rather than four;
whole-Rocket banks and complete checkpoint image remain unsupported. The
runtime FIRRTL default emitter request, 2,120 unknown target-bearing dedup-group
restrictions, abstract clock-gate source retirement and physical BUFGCE owners
have concrete provenance in `runs/aws-f2/iteration207/remaining-blockers.json`.
Existing --no-dedup does not discharge group constraints because forced dedup
removes it temporarily. Full physical cuts, paired CPU restores, finite replay,
live comparison beyond trace and rolling migration remain pending. Reuse the
iteration194 localhost invocation. Exact commands and complete receipts:
`runs/aws-f2/iteration207/summary.json`. Plans remain byte-identical; no agent
staging/commits, new AFI requests or runtime launches. Three workers completed
and were joined; existing controller checkpoints were published in required
order. See [github-publication.md](github-publication.md).


## Iteration 208: stage emitter policy and exact Xilinx source retirement

Consumed the exact default stage emitter request and retained its complete input,
policy, actual final emitter and output-byte binding. Retired only exact known
abstract gate source/definitions after the actual Xilinx rewrite, including
instances in globally unreachable modules. Typed and raw annotation references,
unknown sources, duplicate/colliding definitions and altered receipts reject.
Independent historical-circuit auditing rejects 54 new corruption cases.

Exact Rocket preflight rejects two annotation classes. Investigation distinguishes
the remaining generated InlineInstances request from the consumed stage default;
it remains live and unsupported. Raw dedup-group restrictions and physical
clock-gate/common-cut/full-image/CPU migration coverage remain pending. Full
176 Scala / 306 Python / 40 loop scope, retained EDA sanitizers/FCFS, native OOC
and final independent audit pass. Exact receipts and commands:
`runs/aws-f2/iteration208/summary.json`. Both plans remain byte-identical, with
no agent staging/commits or new runtime/AFI requests.

## Iteration 209: native post-mapping inline consumption before bank inventory

The generated wrapper InlineInstances request now executes before inventory and
banking. Native renames update real annotations; concrete register/RAM instance
tracking rejects loss, duplication, aliases and shape changes. Consumed request,
targets, circuit/annotation hashes, native rename history and complete storage
mappings bind final bank context. Unknown transform requests remain unsupported.
The actual exact-Rocket compile reaches strict preflight with one unsupported
class (2,120 raw dedup-group constraints), down from two; no whole-Rocket bank or
checkpoint image is emitted. Enforce those constraints before mandatory dedup next.

180 Scala / 306 checkpoint Python / 40 loop tests, full retained EDA sanitizer/
FCFS/component scope, native OOC bank/top/inline synthesis and independent source/
artifact audits pass. Fresh inline SP2 VCS: 2,016 comparisons / 512 fixture cycles,
with waveform; 13 independent evidence corruptions reject. Native inline fixture:
63 LUTs / 16 registers. EDA bank/top/synchronous-policy counts: 4,669 / 7,858 /
21,970; native/VCS audits match 28 generated files / 35 current sources. Initial
fixture-equality and audit-import diagnostics remain in their original logs;
corrected complete checks establish passes. Actual image/P&R/AFI, complete
physical/common-cut/host/pre-FAME coverage, active FPGA images/traces, paired CPU
zero-edge restores, finite replay, sustained live RTL and rolling recovery remain
pending. Reuse iteration194's localhost build invocation. Evidence and commands:
`runs/aws-f2/iteration209/summary.json`. Plans are byte-identical to entry. No worker
was created (managed runtime rejected both spawn requests); all work ran centrally.

## Iteration 210: phase-correct typed dedup group enforcement

All 2,120 actual Rocket group restrictions now deserialize into a compatibility
annotation for pinned FIRRTL 1.6. Stage suppression prevents unaware early
dedup. The forced pass uses literal-group structural cliques and native complete
renaming, then consumes constraints before FAME/inline removes definitions.
Immutable policy/pass/retirement history and suppression bind both bank emission
boundaries. Exact Rocket preflight advances to an explicit opaque BUFGCE XDC
contract failure; no whole-Rocket bank or capture image is emitted.

188 Scala / 306 checkpoint Python / 40 loop tests and full EDA sanitizer/FCFS/
component scope pass. New group fixture: 7,112 VCS comparisons / 512 cycles,
debug waveform, 19 corruption rejections; native OOC 63 LUTs / 56 registers.
Final independent bank/top audit matches 28 generated files / 39 sources, with
4,669 / 7,858 / 21,970 bank/top/synchronous-policy VCS checks. All CPU/F2 capture
and migration requirements remain pending. Commands and nonempty receipts:
`runs/aws-f2/iteration210/summary.json`. Plans/configs are unchanged; no staging,
local commits, new AFI/runtime or remaining managed worker. Existing controller
checkpoints were published in the required order.


## Iteration 211: native physical-clock constraint contract

Exact default-SYNC BUFGCE pin/cell constraints now validate and survive
specialization through shared physical leaves, with real WriteXDCFile output.
Exact definition and unsupported CE-latch/common-low-phase-cut ownership bind
external-owner reports. Unknown/modified sources, parameters, ports, hidden or
indexed pins, foreign/dead paths, cross-instance constraint products, missing
or mistyped reports and coherent rehash attempts reject. Bank generation still
rejects physical latch state rather than reusing the metasim O owner.

Actual Rocket compilation advances to unreachable NoDedupAnnotation on
Nasti2AXI4IdentityModule; the compiler stack identifies the producer contract.
193 Scala / 309 Python / 40 loop tests, full EDA sanitizers/FCFS/components,
native OOC and independent audits pass. Physical fixture: two BUFGCEs / sixteen
registers / six constraints, 4,064 fresh SP2 VCS comparisons, 14 corruptions,
healthy/failed VCDs and matching 10-file/10-source snapshots. Retained bank/top
source audit: 28 files / 41 sources; VCS 4,669 / 7,858 / 21,970 checks.

No checkpoint-enabled full image, physical checkpoint, CPU restore/finite/live
acceptance or rolling hardware recovery is claimed. Reuse iteration194's local
build invocation. Current commands and individual receipts:
`runs/aws-f2/iteration211/summary.json`. Plans retain their entry hashes; no
staging/commits, new AFI/runtime or remaining worker/native job. Existing
controller checkpoints were published in the required order. Initial physical
audit definition-indentation mismatch, fixture timescale/failure-status issue,
wrong-CWD HDK setup attempt, production-diagnostic expectation and final-audit
import failures remain in their original logs; corrected full checks establish
the passes. See [github-publication.md](github-publication.md).


## Iteration 212: native NoDedup retirement (retained recovery note)

Historical milestone: `F2-rocket-checkpoint-migration`, iteration 212,
**in_progress**. The actual native inline pass now retires NoDedup protection
only for definitions it removes. Every protected input definition must be
reachable, local and unique; removed modules must match the explicit inline
selection, and surviving protection is unchanged. Version-2 inline history binds
every protected target, definition hash and retirement/preservation action,
alongside complete concrete storage tracking and actual native renames. The
independent audit checks complete annotation sets and definition hashes, including
coherently rehashed dropped/revived protection. See
[f2-inline-constraints.md](f2-inline-constraints.md).

The exact Rocket compiler passes the previous unreachable NoDedup failure on
`Nasti2AXI4IdentityModule`. It now rejects a stream-engine queue RAM target:
`~F1Shim|F1Shim/top:FPGATop/CPUManagedStreamEngine_0:CPUManagedStreamEngine/TRACERVBRIDGEMODULE_0_to_cpu_stream_outgoingQueueIO_q:Queue_56>ram`.
The actual stack identifies external `midas.targetutils.xdc.XDCAnnotation` at
GeneratedStateBankAnnotations.scala:200. Next: exact RAM-style XDC memory/cell
selection through banking and downstream emission, preserving external/internal
identity and correlation. Do not simply admit arbitrary memory targets. No
whole-Rocket bank RTL or checkpoint-enabled image is emitted.

All **195 Scala / 309 checkpoint Python / 40 loop tests**, the full retained EDA
ASan/UBSan/FCFS/bank/memory/bridge/host scope and all native OOC checks pass.
Fresh native/EDA inline evidence matches **7 generated files / 9 current
sources**; VCS passes **2,016** comparisons over 512 fixture cycles, **20**
independent corruptions reject and debug VCD is retained. Native inline OOC
uses **63 LUTs / 16 registers** plus distributed RAM. Physical native/EDA checks
retain 2 BUFGCEs / 16 registers / 6 constraints, 4,064 comparisons and 14
negative cases. Retained production bank/top audit matches **28 generated
files / 41 current sources**, with VCS counts **4,669 / 7,858 / 21,970**.
These are compiler/component results, not FPGA capture or CPU acceptance.

Partial stateless inlining preserves protection on surviving definitions.
A new explicit stateful partial-inline negative retains rejection of an existing
FIRRTL 1.6 rename alias onto a promoted copy; complete storage auditing stays
fail-closed. Initial two failing Scala checks and diagnostic class-metadata
correction remain in original iteration-212 logs/receipts; final full tests and
independent audit pass.

The three physical CE-latch owners/common low-phase atomic cut, complete memory/
timing/bridge/host/pre-FAME binding, full localhost image/P&R/AFI, all-hart active
early/warm/outstanding/late FPGA captures, paired CPU zero-edge/finite/live
continuation beyond the trace and rolling hardware recovery remain pending.
Reuse iteration194's localhost build invocation and initialized manager configs.
Fresh AWS, localhost SSH, Vivado 2025.2 and F2 HDK checks pass; final scoped
inventory has no owned runtime or native Vivado/Java job. No new AFI/runtime was
requested. Both plans and the four manager inputs retain their entry hashes;
no staging or local commits. Existing controller checkpoints were published
FireSim first (`19289d2e`), then Chipyard (`f3999a66`); independent remote tips
match. Follow [github-publication.md](github-publication.md) for the controller's
next checkpoint. Managed worker creation failed before startup; only the central
agent ran, and no delegated worker remains. Exact commands and individual
receipts: `runs/aws-f2/iteration212/summary.json`, `verification-commands.json`,
`remaining-blockers.json` and `final-audit.json` relative to the loop.
