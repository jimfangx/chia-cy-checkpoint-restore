# Original semantic storage in the transformed simulator

Iteration 138 adds opt-in `--semantic-fame-state-map`, requiring bridge-extracted
schema-3 semantic discovery. The Make equivalents are
`SEMANTIC_BRIDGE_CHECKPOINT_ROOT=FireSim.chiptop0`,
`SEMANTIC_MULTICLOCK_INVENTORY=1`, and `SEMANTIC_FAME_STATE_MAP=1`.
Use `SIMULATOR_CHECKPOINT_INVENTORY=FPGATop` to bind the generated inventory
and mapping to the same explicit simulator boundary.

The map carries original StateIDs through FIRRTL path resolution, module
duplication, inlining, FAME and actual emitter renames. It preserves original
registers and logical memories, including constant-driven registers, and
reinstalls preservation after FAME removes its model-port DontTouches.
Memory pipelines track their owning memory plus the exact emitter field;
initialized external values use the existing exact plusarg model adapter.
Local instance annotations preserve Verilog keyword renames in every emitted
path segment. The final map validates kind, width, depth and signedness against
the complete generated storage inventory, with distinct namespaces for original
and generated StateIDs. Missing, duplicated, aliased, reshaped, out-of-boundary
and ambiguously replicated owners fail explicitly.

`.semantic-fame-map.json` binds the original manifest, generated manifest and
raw emitted RTL hashes. `.semantic-fame-emitted.sv` preserves that exact RTL
before Make appends blackbox sources. The independent Python auditor checks
actual emitted declarations and exact external models, as well as complete
mapping membership. Unselected builds retain their existing behavior.

This is a storage mapping interface. `capture_supported` remains false.
It does not bind original clock events to FAME completion, establish a coherent
cut, observe complete boundary traffic, reconstruct erased boundary signals,
or authorize a CPU checkpoint profile. An audited storage path is necessary
for capture; storage correspondence alone does not prove finite replay.
Level-1 simulator restoration remains independent.

The exact Rocket audit resolves six original domains to
`FPGATop.sim.target.FireSim_.clockBridge_clocks_1_buffer.O` and uncore to
`clockBridge_clocks_0_buffer.O`. These are physical emitted clock connections;
the map does not substitute host ticks or scheduler credits for target events.
The next capture backend must bind settled event phases, independently count
actual edges, preserve the original target-cycle labels and sample every one
of the 116 retained ChipTop ports. It must capture a real workload state and
the following complete input/output trace together before ordinary RTL replay
can be accepted. The relevant snapshot/replay sections of both root papers
were re-read; their local source hashes and extracted text are retained under
`runs/m11-iteration138/papers/`. Neither scan chains nor ASIC power work are
introduced by this increment.

Native checks and exact recipe results are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics, failed pilots
and executable commands are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration138/`.
