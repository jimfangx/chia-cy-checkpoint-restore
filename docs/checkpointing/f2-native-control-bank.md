# Native-owner control through the bank transport

`CheckpointNativeCaptureTransport` has an explicit
`CAPTURE_NATIVE_CONTROL=1` option. In addition to its existing staged-payload
entries, it inserts a descriptor for the complete native owner at ordinal
`ENTRIES`. The native owner contains the staged payload, occupied flag, cut
label and errors, the physical low-phase cut state, and sequencer phase/errors.
For three physical clocks its width is `BITS + 153` bits.

The descriptor uses `NATIVE_CONTROL_BANK` (default 251), slot zero, width 64,
and depth `ceil((BITS + GATES + 150)/64)`. Its last word is zero padded.
The existing full-word/tail payload descriptors follow it. The generated
manifest and driver must bind this exact order and the selected option.
An original descriptor using either reserved bank is rejected before a bank
request. The control and payload banks cannot alias each other or bank 255.
The default option remains the previous payload-only component ABI; neither
mode admits an FPGA image or establishes complete capture ownership.

`CheckpointSnapshotStateBank` reads an already immutable vector. It accepts
one request, latches its data/error, and retains the response through
backpressure. Full-width bounds checks prevent large-address truncation.
Permission loss revokes response acknowledgement combinationally. A pending
transfer then remains failed until common reset; it cannot be repaired by
reasserting permission. An MMIO abort may drain an already valid response
on its still-frozen accepting edge, while immediately revoking publication. These rules intentionally do
not manufacture a completion to release an incomplete cut.

The bank introduces 67 separately observable live bits: data, error, pending,
and failure. They are exported as `native_control_bank_state`; they are not
part of the immutable native-owner image. Transport/stream/MMIO self-state
still needs separate atomic ownership and restore before production use.
The existing composite `control_state` retains its previous layout.

The directed integration uses the actual native capture sequencer and transport,
not an alternate model of their equations. Independent audits reconstruct the
complete original owner registers from full debug waves, compare every owner
word with DMA frames, and check ordering, selectors, cut labels, tail padding
and CRC. The test also retains original functional-bank and staged-payload
transfer. Local native synthesis must account for every added register and
all 6,727 staged input bits; all VCS compilation and execution runs on EDA SP2.

Production installation at the exact Rocket widget remains pending. This
component does not supply global common-cut/reset authority, the three physical
CE owner contracts, complete functional memory/FASED/bridge/host/pre-FAME
ownership, a full image/AFI, or hardware-origin checkpoints. Per-cut hardware
migration and live CPU acceptance remain in_progress.

The next production binding must use an explicit native transport interface in
`CheckpointCaptureWidget`, with a checked native vector and complete reader-idle
and hold wiring from the shared graft. A direct transport swap is unsafe:
`CheckpointLiveWidgetSnapshot.acknowledgedCut` currently assumes the transport
coordinator occupies the low 411 bits, whereas the native composite places the
native owner below that transport slice. The shadow predicate, widths, generated
header, resource hashes and descriptor order must change together. The separate
67 bank bits must also have an explicit owner; appending descriptors alone does
not supply it. Preserve the last accepting raw functional edge: native write
sites use `functional_hold`, while physical gates use the low-phase mask.

`NativeCheckpointRegionWidgetGraft` still rejects native observations and live
widget storage freeze conflicts. Its existing staging path is shell-only and
cannot yet cover Rocket's mixed physical regions. Keep the physical CE,
reservation and image-admission guards until common-cut/reset, complete owners
and zero-edge restore mapping exist. A useful next bounded test is the real
widget endpoint through the native transport and shared queue graft, with exact
shadow/descriptor identity, backpressure and hold/fault timing; it remains
component evidence until actual F2 capture and complete CPU migration pass.

Receipt validation also binds the exact frozen source namespace, every consumed
source byte and the reconstructed native Tcl to the current source hashes.
Self-consistent rehashing of stale source copies must reject. Frame auditing
requires canonical zero trailer reserved bits as well as CRC and native-owner
readback; both cases have explicit negative tests.

Current native characterization (iteration 285) uses the F2 part at unchanged
140 MHz. The 6,727-input standalone bank has 2,080 LUTs and 67 registers. The
enabled BITS=1036/GATES=3/OWNERS=2 transport has 3,137 LUTs and 1,733 registers;
its OOC setup/hold estimates are -0.619/+0.078 ns. These estimates lack complete
shell/I/O budgets, and the integrated setup estimate is negative. FPGA image
implementation and timing closure remain pending; frequency was not relaxed.
Exact reports and source-bound receipts are under this iteration's `runs/`.
