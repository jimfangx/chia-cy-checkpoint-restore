# M6 FCFS paired semantic cut — iteration 49

M6 remains in progress. The complete FCFS target now has an independent
Level-2 inventory, a same-cut hardware readout beside public Level-1 capture,
and full state correspondence in a fresh Level-1 restored VCS metasim and an
ordinary clean RTL VCS process. Clean RTL stops before its first edge. These
processes do **not** yet perform live per-cycle boundary comparison.

`SEMANTIC_BRIDGE_CHECKPOINT_ROOT=AXI4Fuzzer.fuzzer_` selects the explicit
bridge-extracted, resolved LowForm boundary before AutoCounter, assertion/
print synthesis and FAME. The earlier `SEMANTIC_CHECKPOINT_ROOT` hook retains
its behavior. Mixed phases, duplicate selections, banked bindings at the
deferred phase, opaque state and unsupported clocks/memory pipelines reject.
The new hook changes no circuit state or target logic. The emitted inventory
contains all 1,543 entries / 13,503,308 words; complete emitted declarations
and the independent generated inventory agree at
`FPGATop.sim.target.AXI4Fuzzer_.fuzzer_` without relative-path renaming.

Extracted `ep_clock` is accepted only as a resolved alias of the incoming
target clock, with a second emitted-RTL alias check. Boundary schema 2 records
this clock separately from data. The current schema-1 live adapter rejects
this boundary. The audit records all 11 erased data ports as unresolved
obligations, including response status/user inputs and constant or forwarded
outputs. It does not reconstruct values or silently drop them.

`tools/checkpoint_formats/bridge_semantic.py` emits compact, read-only VCS
observers using one loop per semantic memory. At the harness's settled
low-clock event, the production worker is parked and the observer reads only
the original DUT. The public native collector subsequently writes the
independent `.fsckpt`; no Level-1 image is converted into Level 2. A second
observation follows the fresh public restore's existing bootstrap, with
explicit zero-host-edge, zero-target-edge and low-clock guards.

The real public request is `+fs-checkpoint-operation=699275`, a completed
driver-operation index. Its actual cut is FASED cycle **524402**, after
**524453** DUT rising edges. FASED's timing-model counter resets with target
reset; do not equate its epoch with all DUT edges. The `.rtlckpt` uses the
observed semantic edge count, including functional reset, and a `.cut.json`
sidecar records both labels. This measures their relationship at this cut;
it does not establish live continuation alignment or a universal offset.
The cut has completed all 524288 initialization steps, issued four requests
and completed no responses. Both native runs finish successfully at the
same reported 774628 target cycles.

All 13,503,308 semantic words agree in the independent captured readout,
fresh Level-1 restored readout, checksummed `.rtlckpt` and clean pre-edge
readback. The ordinary clean process uses the existing VPI loader and a
streamed restore file, without expanding millions of SV assertions. A second
fresh clean process deposits a real bit flip in `fuzzer.num_resps` at semantic
cycle 524453. Complete independent readback identifies exactly that changed
word while the clean target has taken zero edges. This is a pre-edge restore
check, **not** the milestone's live first-divergence test.

All 72 Python tests, 23 Scala compiler/stage tests, complete M2 replay and
complete M3 banked capture/clean replay pass. An independent audit additionally
decodes the full native image against its archived executable/build metadata:
13,507,456 generated words, 29 harness records and 17 native owners. It checks
every semantic word, actual outstanding traffic, the real bit flip, source
bindings and both read-only plan hashes. The failed assembly-cache/new-build
trial, initial root/clock discoveries, two test-fixture errors, unsupported
public target-cycle request, mistaken counter-origin guard and audit import
trial remain diagnostic logs. The final complete scope ran afresh on the
corrected source; no scope was reduced or skipped.

Evidence lives under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m6-iteration49/`.
The final VCS invocation is `paired-semantic-final/invocation-uouy7dic/`.
Its `capture.fsckpt`, `capture.rtlckpt`, `capture.rtlckpt.cut.json`, both native
logs, three original/restored/clean readouts and corruption readout are
preserved. `independent-evidence.json`, `verification-commands.json`,
`summary.json` and `artifact-manifest.json` provide the audit and full paths.

Next: audit the erased boundary fields against their pre-FAME drivers and
FAME channels; extend the live adapter for the complete schema-2 boundary;
initialize the restored observer from the paired semantic origin and check
actual gated target edges. Load/read back clean state before allowing the
authority to send its first boundary. Then run both VCS processes concurrently,
preserve ready/valid and all causal inputs, compare every target cycle and
stop both processes at the first actual output divergence. Repeat the long
run and deliberate state corruption beside the fresh public Level-1 restore.
The old adapter's large per-word SV generation should not be used for this
13-million-word target; retain complete memory coverage with compact loops.

Proposed plan correction, confined to this document: require an explicit
cycle-origin contract between checkpoint levels and the actual target edge;
a bridge cycle counter or driver-operation index is not interchangeable with
the semantic edge count. The loop's M6 corresponds to the input agent plan's
Phase 8 / M7. Both plans remain unchanged and unstaged, including the existing
dirty agent plan. No conda/PDF edits, commits, resets, cleaning, physical FPGA,
formal equivalence, ASIC activity or power validation are claimed.
