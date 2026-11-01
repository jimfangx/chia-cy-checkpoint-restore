# Shared bank readout of staged live-shell state

Iteration 304 adds `NativeCheckpointLiveShellBankReadout`. It connects the
immutable copy produced by `NativeCheckpointLiveShellSnapshot` to the same
request/response bus as the shell's original banks. The source-bound descriptor
factory retains every original selector and enclosing StateID and appends one
64-bit-word descriptor for the packed staging copy. Constituent original/live
and derived/native identities, shapes and bit offsets remain in the binding.
The original register equations and raw clock remain unchanged.

The adapter retains the selected response owner while public selectors change
and backpressure delays acknowledgement. All bank handshakes require staging
permission. Capture/release additionally require the new readout to be idle;
all public requests reach the staging owner's premature-borrow check, including
requests selecting the new bank. A lost cut revokes both handshakes immediately
and retains outstanding response state. Bad slots/addresses return explicit
zero-data errors without inventing a successful read.

The new live owner has 69 bits: routing pending/owner bits and the separate
snapshot bank's 67 retained response/control bits. Its complete observation is
exposed and separately inventoried as **unsupported for capture and restore**.
It is excluded from its own immutable payload. Neither the descriptor factory
nor this local attachment installs the production reserved widget's descriptor
table or removes its ownership refusal. Full-image, production-freeze and restore
admission flags remain false.

The directed fixture has three original descriptors / six words and one staged
payload descriptor / nine words. The copy contains 237 original/live bits and
320 derived/native bits, with 19 zero padding bits in its last transfer word.
Its staging/control owner has 628 bits. Evidence and immutable attempts are
under `automations/checkpoint_loop/runs/aws-f2/iteration304/`. Native Vivado
synthesis passes and retains all 628 staging bits and 69 readout-owner bits;
its synthesized fixture uses 940 LUTs / 1,320 CLB registers. This is local synthesis,
not a completed full-image implementation or F2 deployment.

All 386 Scala tests / 60 suites plus sixteen preparation checks and four
focused checks pass. Fresh EDA SP2 VCS and independent raw-wave audits pass
1,019 comparisons at four component cuts / 68 bank transactions. Every original
descriptor and staged word is read, with nineteen fault cases and rejection
of all 69 readout-owner bit mutations. Native descriptor auditing rejects eight
schema corruptions. Twenty-two fixture debug waves remain. Separate original/live and native payload
corruptions stop at words zero and three of component cut zero, before
acknowledging the divergent response. The independent audit scans the waveform
tail for later acknowledgements or functional-cut advancement.

All retained native/EDA staging, shell, ASan/UBSan/host/bank/FCFS/cut checks and
409 Python / 61 manager tests pass. All five full-suite fixtures match native
and VCS inputs byte for byte. Both fresh exact-Rocket compiler trials retain
the real FASED physical CE owner/common-low-phase refusal. Final closure is
`final-audit-mjgcq2pu/summary.json`, binding 2,064 current source files. Final
AWS/native preflight reports no active loop F2 instance, pending AFI or native
build job. Preserve the initial FIRRTL declaration-order failure, the local
fixture's physical-cut descriptor-factory rejection and the VCD auditor's
empty-initial-sample failure as separate immutable attempts.

Production follow-up must bind the ONE reserved widget's immutable descriptor
layout and transport epoch to these actual banks, and provide complete capture/
restore ownership for original/live/native, staging, routing and response state.
Physical CE/FASED and common low-phase freeze, functional memory, host owners,
global target time and the complete pre-FAME boundary remain required. Then
build the exact Rocket image on localhost, obtain AFI/AGFI and physical cuts,
and establish FPGA-origin Level-1/Level-2 readback, finite replay, sustained live
metasim/clean-RTL comparison and rolling recovery. Component cut labels are not
active Rocket workload or FPGA execution evidence.

## Iteration 305: explicit local routing/response restore

`NativeCheckpointLiveShellBankReadout.generate(..., enableRestore = true)`
exposes a source-bound restore interface for the readout's complete 69-bit
owner. The default leaves restore disabled and ties its inputs to zero.
`CheckpointSnapshotStateBank` supplies the corresponding opt-in 67-bit leaf
load. Both use the original running raw clock, prioritize reset and suppress
request/response handshakes while held or loading. No new storage is introduced.

A load requires hold, revoked readout permission and no public request or
response acknowledgement intent. The snapshot bank's pending bit must equal
the conjunction of the retained route's pending and snapshot-owner bits.
Contradictory routing images reject before either owner loads. All retained
data, inactive error/owner bits and sticky failures are loaded, independently
of whether a response is currently visible. Loading an outstanding response
does not borrow the source payload again.

The opt-in restores this local owner only. Original endpoint state, original
live registers, staged payload/control, physical CE, common-cut timing,
functional memory and host owners still need their complete independent
adapters. The generated manifest retains its unsupported production owner and
all image/CPU restore admission flags remain false. This interface cannot
establish a complete FPGA checkpoint or safely resume an incompletely restored
simulator. Production descriptor/epoch attachment remains pending.

Current evidence is under `automations/checkpoint_loop/runs/aws-f2/iteration305/`.
Directed donor images are component fixtures, not FPGA `.fsckpt`/`.rtlckpt`.
Native synthesis passes for the standalone owner (396 LUTs / 69 registers) and
generated wrapper (985 LUTs / 1,320 registers). Fresh source-bound EDA SP2 passes
18 donor/restore pairs, eighteen unsafe-load cases and three every-bit tests
at payload sizes 1, 65 and 557. Every restored process continues for 128 bank
transactions after independent complete readback, totaling 2,304 new transactions.
The actual generated wrapper also passes 139 owner loads without resetting the
readout or acknowledging a bank edge. Independent waveform auditing rejects all
69 omitted-bit mutations and identifies compiled response corruption at canonical
bit 2 on the first load, before any acknowledgement. Fifty-nine new debug waves
are retained. The original six-geometry bank/MMIO/DMA regression also passes.

All 386 Scala tests plus sixteen preparation / 25 focused checks, 409 Python /
61 manager tests and retained native/EDA/sanitizer/host/FCFS checks pass. Six
full-suite/native/VCS fixtures match byte for byte. Final source/evidence closure
is `final-audit-m72cd4la/summary.json` under this iteration, binding 2,068 sources.
Both fresh exact-Rocket trials retain the physical CE/common-cut refusal; no full
image or CPU hardware acceptance advances. The initial emitted-wrapper fixture
reset/freeze-order failure and its corrected independent restore remain separate
immutable attempts. The final preflight reports no active loop F2 instance,
pending AFI or native build job.

## Iteration 306: stateless local routing/response capture

`generate(..., enableCapture = true)` exposes a two-word, 64-bit, LSB-first
capture port for the same complete 69-bit local owner. Capture is independent
of restore enable. Its hold parks both the routing registers and the snapshot
response bank, including inactive data/error/owner bits and sticky failures.
The port adds no storage or response pipeline. Word one has 59 zero padding
bits. The caller asserts hold before sampling at a raw clock edge; all reads
then observe the held owner until release. Reset retains priority.

Valid capture requires revoked bank permission, no public request or response
acknowledgement intent, and no enabled restore hold/load. Unsafe controls return
an error with zero data and never permit a bank or load acknowledgement while
held. Invalid word addresses also return an error with zero data. Release must
hand ownership directly to qualified bank permission or restore hold when an
outstanding snapshot response exists, preserving the existing lost-permission
fault semantics. Disabled capture leaves the original behavior intact.

The generated binding identifies the transport, exact word/storage counts,
explicit enable and lack of target-cycle authority. The existing staging-copy
bank descriptor is unchanged. This port does not install the production widget's
MMIO/DMA attachment or freeze/restore original banks, staging/control, external
writers or the whole simulator. Production unsupported-owner and full-image
admission flags remain intact. Component images remain directed `.hex` payloads,
not FPGA `.fsckpt`/`.rtlckpt` files.

Verification evidence is collected under
`automations/checkpoint_loop/runs/aws-f2/iteration306/`; completion results and
remaining hardware work are recorded in the iteration's progress entry.

Production permission revocation remains a separate integration obligation.
The generated fixture captures while staging permission is independently
suppressed; it does not prove safe capture during a live staged transaction.
The production attachment must withdraw readout permission without releasing
or faulting the staging owner, including when a response is pending, and bind
that withdrawal to the common cut. The local capture hold supplies neither
that global permission owner nor its epoch/target-cycle authority.

Iteration-306 closure is `final-audit-6ustnh9b/summary.json` under that evidence
root: all 386 Scala plus sixteen preparation / 25 focused checks and complete
retained native/EDA/host/sanitizer/FCFS/bank/shell checks pass. Three native capture
profiles retain all 69 bits with no added storage. Fresh source-bound EDA passes
24 component donors, eighteen fresh restores, fifteen unsafe capture cases,
every-bit tests and 139 generated-wrapper load/capture cycles, with 2,304 new
bank transactions and 62 debug waves. All 69 omitted-bit mutations reject;
compiled capture corruption stops at word zero before acknowledgement/publication.
The final audit binds 2,070 sources and eight matching generated fixtures. Initial
ENOSPC and wildcard-port failures remain in separate attempts. Kernel-verified
sharing recovered 16 GiB without removing/replacing any original evidence; the
legacy bank fixture's inactive capture hold is explicitly tied low. Complete
native/EDA verification then passes. Physical FPGA/CPU acceptance remains pending.

## Iteration 307: local capture permission with occupied staging

An explicitly capture-enabled generated wrapper now connects readout permission
to `staging.borrow_enable && !capture_hold`. The same hold parks the routing and
snapshot-response registers. Staging retains its occupied payload and cut label;
capture neither releases nor resets it. Removing hold hands local permission
directly back to the existing staging owner. This adds no registers, epoch or
target-cycle authority. Default capture-disabled generation retains its previous
permission connection. Binding metadata records the exact permission contract,
zero added storage and the still-unbound global permission owner. Regeneration
validation rejects a removed mask even when circuit hashes are coherently updated.

The generated-wrapper regression uses original functional inputs and actual bank
transactions, without backdoor assignments or fabricated restore loads. It covers
occupied idle staging, every staged word, original register responses, in-flight
native-memory reads and resumed response backpressure. The two-word local capture
is checked against all six original routing/response registers. A separate raw
waveform audit compares all four staging registers, including inactive payload,
occupied bit, cut label and sticky errors, against the full 628-bit observation.
Both capture-only and capture/restore profiles exercise component cuts 0, 17,
128 and 256. These labels describe directed fixtures, not Rocket or FPGA cuts.

Unsafe public request/acknowledgement intent during hold must return zero/error
without accepting either edge. Releasing staging, drifting the target label or
losing a declared owner/freeze retains the unacknowledged response and fails the
staging epoch. A local owner capture can still expose its held bits after an
enclosing fault; its valid flag never authorizes global publication. Tests also
compile the actual emitted wrapper with its permission mask removed and inspect
the first divergence and waveform tail for later acknowledgements.

This closes the local permission-withdrawal gap only. The production ONE-widget
descriptor/MMIO/DMA and epoch attachment, complete original/native/staging restore,
physical CE/common cut, functional-memory and host ownership, full localhost image,
AFI/AGFI and active all-hart hardware migration remain pending. Current receipts
and immutable diagnostic attempts are under `runs/aws-f2/iteration307/`.

Iteration-307 closure passes all 386 Scala / 60 suites plus sixteen preparation
and 25 focused checks, 409 Python / 61 manager tests, complete native synthesis
and retained EDA SP2 capture/restore/bank/MMIO/DMA/shell/host/sanitizer/FCFS scope.
The occupied-staging cases pass both profiles, four component cuts and 112
continued transactions; all 628 observation-bit mutations and both compiled
missing-mask failures reject. The capture suite retains 84 debug VCDs. Native
capture-only and paired wrappers use 1,025 / 1,104 LUTs and 1,320 registers; the
standalone owner remains 514 LUTs / 69 registers. No capture storage was added.
The independent closure binds 2,075 current sources and eight matching fixtures;
`runs/aws-f2/iteration307/final-audit-selected.json` selects the immutable receipt.
Both fresh Rocket production trials retain the physical CE/common-cut refusal.
Final AWS/native inventory has no active loop instance, pending AFI or native
job. Full checkpoint image and FPGA-origin CPU acceptance remain pending.
