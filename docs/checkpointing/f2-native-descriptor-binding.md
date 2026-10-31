# Typed native stream and original ROM binding

Iteration 287 adds `CheckpointNativeCaptureDescriptors.bind` and the component
`CheckpointNativeBoundWidgetEndpoint`. The factory accepts independently
validated original descriptors and explicit native geometry/owners. It derives
the exact ordered stream manifest, host C++ metadata and native endpoint params.
The wrapper wires the original descriptor ROM internally; external descriptor
replacement inputs are absent.

The native transport consumes only the original ROM count. It appends an
optional native-owner descriptor, full payload words and a partial tail. The
host manifest covers that complete stream in the same order. The native-owner
width is `BITS + GATES + 150`, padded to 64-bit words. A payload shorter than one
word still uses tail slot 1. Both reserved selectors are excluded from original
banks even when native-control capture is disabled. Validated bank-255 physical
CE entries retain their original identities; their count, when nonzero, must
match the native gate count.

Canonical metadata binds original manifests and bank bindings, native resource
hashes, named external owners, all geometry/options/selectors, descriptor order,
original/full counts and the coordinator-first shadow layout. The driver digest
uses the existing little-endian integer ABI. Synthetic native transport StateIDs
remain distinct from pre-FAME semantic state. No descriptor is invented for the
67 live response-bank bits: they remain a separately unsupported atomic owner.

The generated fixture has 130 native bits, three gates, two named external
owners, one original descriptor and four complete stream descriptors. Fresh
native OOC synthesis on this server passes 2,859 LUTs / 2,513 registers and
67 distinct bank drivers, with +0.711/+0.073 ns internal setup/hold estimates
at the unchanged requested 140 MHz period. Exact-DCP component place/route
passes +0.194/+0.048 ns estimates, preserving all 2,513 original sequential
identities/protection and all 67 bank drivers; 4,531 max and 4,531 min worst-per-
endpoint paths are enumerated. Vivado quantizes the unchanged requested
7.142857 ns period to 7.143 ns. These routed estimates exclude parent clock
source delay/skew (`HD.CLK_SRC` is absent) and shell/I/O budgets. Fresh SP2 EDA
passes cuts 35/68/112/167, all 827 layout planes / 25 shadow words, original ROM
bounds, native-owner/frame/CRC readback and owner-loss/abort recovery. Both exact
compiled faults stop at cut 35 before control/shadow acknowledgement, with raw
clock low and no later VCD timestamp/edge. Independent original-wave audits pass.
The complete affected-scope retained EDA sweep passes, including sixteen matrix
scopes, nine affected additional executions, complete large-wave/input-history
checks, eight corrupted streams, six queue faults, two bank faults and all
endpoint/widget/restore audits. The final 30-scope source/input/artifact audit
passes with 21 fresh scopes and nine unchanged original-date receipts. Every
large original waveform was fully rehashed; no raw-wave proof was reused.
Four exact checked-in C++ source aliases retain their literal target and complete
resolved-file hash; artifact/raw symlink rejection is unchanged. Final manager
and EDA inventories find no owned build/simulation processes, loop F2 instances
or pending AFIs.

The production widget selection, reserved-placeholder structural rejection,
peer routing, shared-graft hold/deadlock checks and image admission remain
unchanged. This component does not supply complete common-cut/reset/physical
CE, transport/stream/host, memory/FASED/FAME or independent pre-FAME ownership.
Full image/P&R/AFI, physical all-hart cuts, hardware-origin image/trace pairs,
zero-edge CPU restores, finite/live continuation and rolling hardware recovery
remain pending. Test results, immutable failed attempts and exact receipts are
under `runs/aws-f2/iteration287/`; pending hardware checks are not passing evidence.

The next production connection must extend
`NativeCheckpointWidgetReservation.requireBound` to recognize native transport
structure even if annotations and generated headers are removed. Its existing
physical sentinel is not a native ownership contract. The peer/reservation ABI
and identity-bound header flow must change together with any widget selection.
`NativeCheckpointRegionWidgetGraft` must retain its live-storage deadlock and
native-observation rejection until separate owners exist. Shell functional write
sites require `functional_hold`; physical gates require the low-phase mask.
All regional/router pending readers must participate in `reader_idle` before
staging or release. The live shadow and native response-bank observation do not
provide atomic self-capture or a zero-edge restore owner.

`EXTERNAL_OWNERS` counts caller-owned inputs (two in this fixture).
`COORDINATOR_OWNERS` / `abi.coordinator_owners` names the nested
`CheckpointCaptureTransport` input interface: external owners plus the native
certificate (three). That transport's `CheckpointCaptureCut` adds one internal
transport-fault sentinel, so its physical owner-vector width is four. The
sentinel is constant present/frozen and its error is the reduction of the four
`transport_error` bits. These error registers and the 72-bit cut state are in
the existing 411-bit composite; the sentinel introduces no additional sequential
state. This count does not claim an independently freezable/restorable transport
owner. Atomic transport self-state ownership remains unsupported.

Verification recovery notes: full Scala emits regional FIRRTL/annotations; run
actual `WriteXDCFile` emission for each regional widget/identity/source-policy
context and the identity's `unbound` comparison context before native audits.
Both identity directories must contain the same XDC namespace and bytes. Keep
those JVM steps separate from Vivado jobs. This iteration preserves the original
missing-XDC and namespace failures and uses new immutable retry receipts.

FIRRTL removes the constant-zero original-ROM slot output in this fixture. The
bound bench observes its actual connected transport input, without forcing any
index or data. After the trailer, owner loss immediately rejects shadow capture
and prevents DMA-valid/counter progress; `WAIT_PUBLISH` reports DMA abort at its
registered cut-failure boundary. The test checks both boundaries and preserves
all 1,585 prior shadow bits. The original compile failure and the actual SP2
publication-stage diagnostic remain under this iteration's `runs/` history.

The central evidence audit maps manager-absolute paths to the EDA mirror.
EDA independently hashes mirrored plans and exact manager-YAML snapshots under
`runs/`; the manager checks all live original inputs before and after the EDA
audit. Manager YAMLs remain excluded from repository sync into EDA. The original
failed path-mapping attempt is retained. Current selected summaries and raw
backend argv are in `current-final-audit-selected.json` and
`verification-commands.json` beneath this iteration's run directory.
