# Selected widget transport and host identity

`NativeCheckpointWidgetIdentity.bind` reconstructs the existing selected-execution
widget graft and its descriptors before binding their manifest digest into the
actual `CheckpointPhysicalCaptureTransport` parameter. The registered host header
gets the same digest, descriptor-binding digest, ordered StateIDs, little-endian
C++ manifest initializer, allocated MMIO base/stream, owner names, queue depth and
production driver constructor. It changes one external-module parameter and one
header annotation; it does not change the readout implementation or duplicate
the selected execution.

The API checks both original and lowered header cardinality. This matters because
native lowering can deduplicate identical annotations: checking only its output
would miss an ambiguous original reservation. Missing, repeated, conflicting and
out-of-range header reservations reject. The source/graft/descriptor reconstruction
and existing annotation restrictions remain mandatory.

This is a selected readout identity contract. Its StateIDs retain the supplied
in-place compiler context's namespace; it does not establish a complete enclosing
F1Shim image identity or ownership. The host header still contains
`#error Incomplete_checkpoint_hardware_coverage`. The image guard also detects the
external clock network independently of digest and annotations, so deleting all
annotations after binding cannot admit an image. Production annotations,
transport/stream/MMIO freeze owners, complete functional/FASED/DRAM/bridge/software
state, physical CE restore, pre-FAME state and full image/driver compatibility
remain separate requirements.

The independent Python auditor first checks the complete unbound graft, then
reconstructs the sole permitted FIRRTL/Verilog parameter change and the complete
host header/constructor. It derives digest bytes and every selector from the
retained manifests and checks unchanged files and annotations. Twelve mutations
rehash the affected receipts and exercise image/owner admission, header digest,
selector, byte order, stream, MMIO, guard removal, transport/emitted parameters,
descriptor substitution and foreign annotations.

The connected execution harness accepts both the original sentinel fixture and
the separately bound fixture. Its MMIO and DMA checks use the independently
verified manifest digest. The bound variant additionally compiles and exercises
the actual generated C++ initializer with the production frame validator and
ASan/UBSan on all four VCS capture streams; the complete registered header must
still fail compilation at the incomplete-coverage guard. All such streams remain
component simulation evidence. Actual FPGA-produced CPU checkpoints and migration
are pending.

Iteration-249 logs and isolated receipts are under
`automations/checkpoint_loop/runs/aws-f2/iteration249/`. See that invocation's
`verification-commands.json` and `final-audit-*/summary.json` for executed results.

Next integration must lift the existing bounded annotation policy and bind the
complete enclosing host namespace. The retained exact Rocket projection still
leaves 1,947 functional owners and the FASED physical CE owner outside the
selected subtree. Do not use the selected manifest as a complete F1Shim build
manifest or turn its identity flag into a physical-capture flag. The exact
production compiler must continue rejecting that missing owner/common cut until
its hardware and external-memory/reset/host contracts exist.

Verification completed across October 26–27, 2026: 267 Scala tests plus two
preparation tests, seven EDA SP2 component scopes, 328 Python and 40 loop tests,
and all five affected native synthesis scopes pass. The bound component uses
4,753 LUTs, 1,647 registers and three BUFGCEs; 662 raw register clocks are audited.
Each connected variant passes 5,165 checks over four cuts, 136 words and 900 DMA
stalls. The bound generated initializer passes 20 ASan/UBSan checks. Independent
waveform audits retain 2,704 frozen samples and the compiled payload defect at
cut 81, word 0, byte 42 before release. OOC estimates (+0.437/−0.074 ns) have
unconstrained external I/O and do not establish full-image timing closure.

The successful compiler can produce an empty stdout/stderr log. The initial
runtime-complete EDA attempt correctly failed its aggregate nonempty-evidence
contract. The repaired logger includes actual argv/cwd in each log; two affected
native receipts and the entire seven-scope EDA attempt were regenerated. The
initial Scala duplicate-header failure and initial aggregate failure remain
unchanged. No test scope, sanitizer or receipt validation was removed.
