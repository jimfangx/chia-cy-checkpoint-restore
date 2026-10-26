# Registered widget reservation before final inventory

Iteration 239 adds `NativeCheckpointWidgetReservationBinding`, an explicit
FPGATop elaboration mode for the future post-lowering graft. It registers the
actual widget, MMIO interconnect and CPU-managed stream before host inventory.
Existing streams retain their indices. Twenty annotated ground endpoints
identify the descriptor, bank transaction and physical CE signals after lowering;
there is no embedded copy of the enclosing simulator. Owner presence/frozen/error
and target-cycle inputs have no defaults. The selected execution is evaluated
when Chisel annotations materialize, after module hierarchy is available.

This is deliberately an **unbound reservation**. Readout-return placeholders
remain zero until a checked graft replaces them. Its digest is a reserved
sentinel, not an image identity. Header generation emits `#error` and no capture
driver constructor. The production compiler rejects unresolved annotations,
headers or sentinel transport parameters before ordinary FPGA emission, even
without an inventory request. Stock descriptor-bound attachments retain their
existing requirements. Only the concrete reservation binding can register this
mode without an immutable descriptor ROM.

`NativeCheckpointWidgetReservation.inspect` checks complete endpoint coverage,
unique concrete execution/host paths, local and absolute annotation targets,
exact direct widget connections and zero-return placeholders, raw widget clock,
transport parameters and complete public ABI, and the actual expanded inline
transport sources. It rejects changed/duplicated/unresolved sources. The receipt
binds source, annotations, concrete transport definition and all four source
files. It retains explicit unsupported transport state and false admission flags.

The transport contains sequential state in SystemVerilog blackboxes. The existing
FIRRTL inventory rejects those modules; this change preserves that rejection.
It does not substitute a stateless module, omit opaque owners, infer state totals
from DMA, or use a descriptor digest from a host without these resources. The
current inspector requires the concrete widget boundary. All twenty endpoint
markers survive the actual Golden Gate native inline pass and still block image
emission; peer routing after that promotion remains unsupported. The next step
needs that routing contract, an independently audited external transport state
owner, complete generated owner accounting, and final immutable ROM/digest/header
binding before connecting the existing-root graft. Ordinary synthesis cannot
turn the reserved sentinel or missing ownership into checkpoint admission.

The current-source diagnostic passes **48 fresh EDA SP2 checks**, with a full
debug waveform, missing-owner rejection, zero checkpoint DMA frames, continued
baseline DMA and reset recovery. Native synthesis proves **810** raw-clocked
control/stream registers. Independent matching binds **25 inputs / 14 sources**
and rejects **eight** coherently rehashed mutations. These checks establish
resource/endpoint contracts only; they grant no hardware capture admission.

Fresh verification inputs, commands, diagnostics and receipts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration239/`. The diagnostic reservation
may be synthesized in isolation and executed on EDA to test resource retention,
MMIO rejection/reset recovery and the original stream. It is not a deployable
checkpoint image. All physical captures, complete CPU zero-edge restores,
finite/live continuation and rolling migration remain pending. Reuse the
iteration-194 localhost build invocation; do not launch a substitute public
image or relabel fixture execution as FPGA capture.

Recovery of the interrupted iteration is recorded separately under
`runs/aws-f2/iteration239/recovery/`. The original logs remain available there;
the recovery uses a joined two-worker native scheduler, with all large Java
generation finished before that scheduler starts. Its final audit requires
fresh receipts for every retained native/EDA scope and checks that the copied
EDA phase-one inputs match the final Scala output bytes. The complete sweep
must finish before the recovery can be reported as passing.

The next production binding must follow the surviving annotations through
native inlining. The concrete widget hierarchy used by the current inspector
is deliberately insufficient after its ports become peer wires. Reconstruct
each of the twenty routes to the actual physical transport, including the raw
clock, return placeholders, CE ordering and selected execution; preserve the
original MMIO/stream allocation. Do not infer these connections from emitted
Verilog names or remove unresolved markers merely to pass the emission guard.
Account for the opaque transport state before final inventory and distinguish
the pre-binding descriptor identity from the final emitted-circuit hash, so
rewriting the manifest parameter cannot create an unchecked self-reference.
Only a checked final binding may replace placeholders and the sentinel header.
Complete FASED, DRAM, reset/external-writer and host ownership remains a separate
requirement before a deployable capture image can be admitted.
