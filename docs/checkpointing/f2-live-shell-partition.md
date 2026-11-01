# Selective local banks with separately owned live transport registers

Iteration 301 adds an explicit `liveRegisters` partition to
`NativeCheckpointShellStateAccess.generate` and per-shell selections to
`NativeCheckpointRegions.generate`. This addresses the deadlock in which
freezing a local enclosing bank also stops the checkpoint widget's own
MMIO/DMA registers. Default generation still banks every local owner.

Selected live registers retain their exact original declarations, clocks and
next-state connections. The temporary bank reference replaces their values
with inputs; those synthetic ports disappear when the generated banks are
grafted back into the existing execution. The live storage has no bank selector.
Memories, hidden synchronous pipelines, child state, missing registers and
nontransparent clocks cannot be selected this way. Clock provenance follows
single-driver Clock wires/nodes to an original input; data casts are rejected.
Live declarations require synchronous reset and initialization expressions closed
over original inputs and self. Alias declarations precede the retained registers;
original next-state drivers follow the generated combinational declarations.
Children and unrelated definitions retain their original execution.

Both mapping and binding list every excluded StateID, original hierarchy,
width/depth, original clock expression, resolved input clock and declaration/
driver hashes as `unsupported_live_owners`. Capture and restore support remain
false. Shell identity independently reconciles the banked subset with the
original whole-host inventory and leaves live owners in its uncovered state.
Regional reconstruction includes the exact selection and rejects changed
selections, banks, mapping, source, annotations or ownership metadata.

`NativeCheckpointLiveTransportSelection.registers` derives selections from
the ONE actual reserved widget and the compiler's native-inline storage
history. It checks the peer route/reservation and concrete selected execution;
it does not infer ownership from register-name prefixes. The registered-widget
fixture has eight such local owners. Partitioning them removes its local
transport-freeze conflict. Its original reservation describes fourteen subtree
entries; the six remaining local owners require a new immutable descriptor ROM,
so the old reservation still refuses connection. Native-reader staging and
independent atomic transport owners remain separate production requirements. No second checkpoint controller is added.

Verification commands and original receipts are retained under
`automations/checkpoint_loop/runs/aws-f2/iteration301/`. The selective component
uses original public arithmetic/memory I/O, complete remaining bank readout,
response backpressure and all four component cuts. Its independent audit
reconstructs the original complete local inventory, checks the banked/live
partition and exact live equations, and rejects coherently rehashed omissions,
reshaping, false ownership claims and a changed live driver. Native synthesis
runs on this manager; VCS and debug-wave generation run exclusively on EDA.
See [progress.md](progress.md) for completed checks and retained failures.

This is selective readout, not atomic capture of those live owners. All eight
still need separate capture/restore adapters at the same cut as the remaining
simulator, including their dependencies on NASTI/DMA and host owners. Production
collector/snapshot integration, physical CE/FASED/functional-memory/host and
pre-FAME semantic completeness, target-time authority, a full localhost image/
AFI, real F2 cuts and FPGA-origin CPU zero-edge/finite/live migration and rolling
recovery remain pending. Image/restore admission flags stay false.
