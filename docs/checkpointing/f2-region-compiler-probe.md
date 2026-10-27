# Regional capture at the production compiler boundary

`--simulator-native-region-compiler-probe` selects explicit, comma-separated
concrete executions in the final generated simulator. The diagnostic runs after
backend lowering and before the existing image-emission guard. It reserves no
new permission to capture state or deploy an image.

The opt-in branch prepares the source-checked FPGA plusarg constants before
`ResolveSimulationInline`. Its exact pre/post-inline pair then supplies
`ReservedCheckpointInventory.forReservedWidgetSource`, regional bank generation,
the existing widget connector and descriptor/host-header identity binding.
Changing the circuit or annotation sequence after inline would invalidate that
pair. Compilation without the diagnostic keeps the previous ordering.

The diagnostic resolves expression type/kind/flow metadata after preparing the
constants and before recording inline history. This uses the same resolution
passes as banking, requires byte-identical serialized FIRRTL, checks types and
flows, and records the first hidden structural difference per affected module.
The strict regional comparison still rejects any unrelated typed definition
change. Independent auditing reconstructs the original annotation bytes before
both appended receipts, including the native JSON formatting of empty objects.

`ResolveSimulationInline.forCheckpointRegions` also resolves the native inline
pass's output before that producer records its history. Native inlining can
introduce nested statement blocks into unrelated definitions. The region-only
producer requires identical FIRRTL text, original annotations and complete
storage mappings; its strict v3 receipt binds the resolution passes, equal
before/after hashes and changed-module statement counts. Ordinary compilation
continues using the original v2 path. The downstream regional merge still
compares complete typed definitions.

The probe-only `CheckpointRegionHostClockWiring` uses FireSim's documented
source-retaining wiring API. Ordinary wiring consumes that label. The wrapper
validates exactly one original scalar Clock input on a unique execution and
retains that same annotation through native wiring. It supplies no clock label
or freeze acknowledgement for a missing source. Default wiring is unchanged.

The explicit target directory receives a new
`checkpoint-region-compiler-probe/` subdirectory. Original phase circuits and
annotations, source policy, regional manifests, physical clock dependencies,
routes and connected identities are written before image rejection. Each file
has a checksum in the atomically replaced status record. An existing diagnostic
directory rejects instead of overwriting evidence. Failures retain their actual
exception and the completed intermediate artifacts.

The test-only `WithRocketRegionCompilerProbeReservation` overlay elaborates the
real widget, MMIO and CPU-DMA allocation with the unchanged Rocket target and
base platform configuration. The overlay deliberately has no cycle authority
and reports every external owner missing and erroneous. It cannot execute a
checkpoint. Reservation entry/gate counts must equal freshly reconstructed
descriptors. The incomplete host-header error, physical-clock owner checks and
opaque transport guard remain mandatory, including after annotation removal.

Invocation scripts, immutable receipts and raw diagnostics are under
`automations/checkpoint_loop/runs/aws-f2/iteration259/`. Reuse the initialized
manager inputs and iteration194's ExternallyProvisioned localhost invocation for
future image work. Complete common-cut/reset/external-writer, memory, bridge,
host and pre-FAME ownership, FPGA image/P&R/AFI, physical capture and CPU migration
remain required. These diagnostic artifacts cannot satisfy any FPGA acceptance
column in the CPU checkpoint matrix.


Iteration 259 verification passes 302 Scala tests across 45 suites plus twelve
preparation tests, 336 Python / 45 manager tests, fourteen native and fourteen
EDA SP2 component scopes, all four independent waveform audits and nine rehashed
metadata negatives. ASan/UBSan, FCFS and atomic-cut regressions remain enabled.
The exact Rocket diagnostic binds 10,910 selected descriptors and three CE slots
at MMIO 0x200 / stream 4. It retains 1,241 uncovered functional entries and the
opaque transport owner, and ends at the mandatory incomplete-image guard.
This establishes compiler integration, not physical checkpoint acceptance.
