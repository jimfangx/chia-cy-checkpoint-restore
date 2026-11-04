# Routers at the regional atomic cut

The explicit `--simulator-native-region-cut-router-snapshot-probe` compiler
option includes both layers of readout routing state in the existing regional
cut-control staging payload. Its argument is the existing comma-separated,
ordered external-owner list. The original cut-snapshot option keeps its ABI.
Both options retain the incomplete-image guard and diagnostic ports.

The generated readout adapter exposes the shared router's complete
`{owner, invalid, pending}` vector, followed by each physical router's
`{selected_ce, pending}` vector in native-region order. Inactive selection and
error bits remain part of the state. The immutable graft binding identifies
each instance, definition, width, offset and field order; observation adds no
storage. Restore controls remain disabled in these callers.

The common-cut snapshot concatenates that vector above the existing physical
controller and accepted-request bit. One raw positive edge stages all bits
before the first bank handshake. The original common-low-phase controller
retains clock authority. The version-two snapshot binding records controller
and router widths, packing, resources and parent hashes. Independent
regeneration authenticates the selection through the real compiler and widget
identity path. An occupied snapshot retains its original bytes while later
readout transactions change the live routing state.

This is bounded atomic observation. The existing staging protocol requires an
idle readout pipeline and does not capture arbitrary outstanding reader or
endpoint state. Complete router restore attachment, staging/controller/reader/
endpoint restore, external memory and host owners, pre-FAME semantic ownership,
complete localhost image implementation/AFI, F2 capture and FPGA-to-EDA CPU
migration remain pending. The observation cannot establish hardware acceptance.

Fresh qualification passes 445 Scala / 430 Python / 81 manager tests and the
retained EDA sanitizer/FASED/publication/bank/FCFS/82-cut scope. Ten serialized
localhost Vivado jobs pass. The new component has 2,299 LUTs / 1,149 total
registers; all 153 staging registers retain the original raw clock. Default and
router-enabled staging each pass seventeen fresh EDA SP2 cases, including
backpressure, occupied-snapshot retention, reset cancellation and fault
withdrawal. Seven separately compiled staging-input corruptions of router bits stop at their
first divergent vector/target label with zero acknowledged bank requests or
responses; all 82 single-bit waveform-checker mutations reject. Ten coherent
router binding/packing/resource defects reject independently. Full VCDs retain
all original router registers and the staging owner. This is component
synthesis and simulation, without full-image timing or hardware CPU acceptance.

The exact Rocket compiler diagnostic independently retains 2,701 definitions
and 33 adapter routes. Its three physical CE gates yield 74 cut/control bits
plus seven router bits: 81 observation bits and 152 staging-owner bits.
The actual compiler stops at the expected incomplete-image guard, preserving
1,245 uncovered functional entries and unbound cut MMIO controls. It creates
no deployable image, AFI or hardware-origin checkpoint.

Individual receipts, raw logs, waveforms and replayable commands remain beneath
`automations/checkpoint_loop/runs/aws-f2/iteration9812/`. The command index is
`verification-commands.json`; consult progress.md for the closing audit.
