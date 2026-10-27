# Shared regional transport and host identity

`NativeCheckpointWidgetIdentity.bindRegions` reconstructs the complete disjoint
region graft before binding its combined manifest to the existing registered
checkpoint widget. The transport's `MANIFEST_SHA256` parameter and generated
host constructor use the same descriptor order, router-global selectors and
enclosing StateIDs. The constructor retains the allocated MMIO base, stream,
queue depth, owner names and little-endian digest bytes. Single-region and
multi-region bindings share the same checked header/parameter implementation.
This generated-simulator identity does not assign or certify Level-2 semantic
identities for original pre-FAME RTL.

Only the manifest parameter and registered header annotation change. Original
execution, ancestor routes, clock/control wiring, descriptor ROMs and generated
constraints remain intact. A different, internally valid regional descriptor
set still rejects when it disagrees with the reconstructed original network.
The unsupported-owner definition digest describes the retained unbound source.
The identity receipt separately binds both transport definitions and the sole
manifest-parameter change; it does not reinterpret that source owner as captured.

The independent auditor first reconstructs the entire unbound regional fixture,
including original storage, physical CE identities and uncovered owners. It then
reconstructs the sole allowed executable parameter change and every generated
host register, selector, digest byte and constructor argument. Its negative
cases rehash corrupted receipts; a digest match alone does not establish
structural or semantic correctness. The execution harness checks MMIO and DMA
against this bound digest and feeds the generated C++ initializer and actual
component frames into the production validator with ASan/UBSan enabled.

The generated header retains `#error Incomplete_checkpoint_hardware_coverage`.
The physical image guard also rejects after annotation removal. The opaque
transport owner, enclosing functional memory, clock/reset/external writers,
bridge/host state, pre-FAME mapping and restore ownership remain incomplete.
New readout/router/mask/control storage also needs explicit capture or a checked
exclusion and restore contract before production admission.
The identity contract explicitly keeps image, complete-capture, production-cut
and metasim-restore admission false. This is component implementation, with no
FPGA-origin CPU checkpoint or migration claim.

Iteration-257 commands and immutable test/build receipts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration257/`. Reuse iteration194's
ExternallyProvisioned localhost build invocation once complete production
ownership permits the exact Rocket image to compile. Do not remove its failing
physical FASED CE/common-low-phase-cut admission check to obtain a bitstream.

The bound component's native OOC synthesis uses 5,424 LUTs, 1,980 registers and
six BUFGCEs. Setup/hold estimates at 140 MHz are −0.031/−0.074 ns with
unconstrained I/O; these are component measurements and establish no timing
closure or complete image implementation.

Iteration 258 extends those source-context boundaries through the explicit
`ReservedCheckpointInventory.forReservedWidgetSource` permission. The legacy
permission retains its NoCircuitDedup-only source. The new mode derives and binds
ordered whole-host storage/context, checks original pre-inline context and
preserves typed projection and opaque-owner identity through regional connection.
Unknown annotations cannot lose shared-leaf executions or broaden to newly added
mask gates without rejection. See [f2-region-source-policy.md](f2-region-source-policy.md).
Production source-context hookup and all complete hardware ownership/image
requirements remain pending; this permission grants no capture or restore owner.
