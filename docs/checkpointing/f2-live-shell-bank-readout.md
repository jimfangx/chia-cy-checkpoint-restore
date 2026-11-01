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
