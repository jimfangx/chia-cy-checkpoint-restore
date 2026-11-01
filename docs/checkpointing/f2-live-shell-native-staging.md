# Atomic live-shell and native-reader staging

Iteration 303 adds an explicit `stageNativeState` option to
`NativeCheckpointLiveShellSnapshot.generate`. One raw-clock snapshot now copies
both the unchanged original live registers and the entire source-bound native
synchronous-reader observation. The latter includes forwarding, shadow and
borrowed-reader state, selectors and phase, retained response bytes and the
emitter-owned RAM data register. Local generated identities are projected to
the original enclosing execution; original bank descriptors stay independent.

The original raw clock is checked through every routing ancestor and each
native state clock, including the implicit RAM register's memory-port driver.
The independent access clock is removed. Capture and release require both an
idle native-reader phase and no pending response. Testing pending alone would
admit a request while the borrowed reader is still working. Both bank
handshakes remain permission gated; a failed epoch retains its functional cut.

Opted-in explicit derived registers receive synchronous zero initialization
through their LowForm next-state muxes on bank-controller reset. Original live
register declarations/equations remain unchanged. The implicit RAM data register
is initialized only through original memory execution. Later inactive response
bytes and released snapshot payloads are retained and captured exactly.

The directed fixture contains eight original live owners / 237 bits and fourteen
native owners / 320 bits. Its common payload is 557 bits / nine words; its
separate staging/control owner is 628 bits. Independent FIRRTL inventory and
raw-wave checks reconstruct all owners and bit offsets, including signed and
cross-word original registers. Evidence is under
`automations/checkpoint_loop/runs/aws-f2/iteration303/`; progress.md records
completed checks and pending acceptance. Verification passes all 386 Scala tests /
60 suites and sixteen preparation checks. Native synthesis retains all 628
staging bits in 1,331 sequential cells / 598 LUTs. Fresh EDA SP2 VCS passes 419
checks at four component cuts, twenty bank transactions, fourteen fault cases
and first-word corruption in both original/live and native payload sections.
Independent raw-wave audits reject 1,185 bit mutations; seventeen full debug
waves remain. Separate EDA corruption audits prove cycle-zero divergence in
words zero and three, with no bank acknowledgement or functional edge. All four
full-suite fixtures match the synthesized inputs. Python, manager,
ASan/UBSan/host/bank/FCFS/cut and existing shell regressions pass. Final closure
is `final-audit-0bp02wws/summary.json` under the same evidence directory.

This remains a local observation adapter. It does not install capture in the
production reserved widget, resize its immutable descriptor table, restore the
original/live/native/staging owners, certify global target time or discharge
physical CE/FASED, functional-memory, host and pre-FAME ownership. Full-image
and restore admission flags remain false. A complete localhost FPGA image/AFI,
physical FPGA cuts, FPGA-origin CPU migration/live comparison and rolling
hardware recovery remain pending.

Production follow-up must preserve the existing refusal in
`NativeCheckpointRegionWidgetGraft.connect`: it rejects a live synchronous
observation until the ONE reserved widget has a complete atomic staging
protocol. The optional local snapshot is not a reason to remove that check.
Bind the original live StateIDs and every derived/staging owner to the actual
reserved descriptor layout and transport epoch, and account for retained
payload/control state as well as the copied data. Independent complete restore
readback remains necessary. Original native reader pipelines keep executing
while the immutable copy drains, so the live observation port itself must never
be substituted for staged checkpoint data.
