# M4 generated simulator inventory — iteration 9

This increment establishes a separate Level-1 generated RTL inventory and
tests complete diagnostic extraction on InventoryFixture. It does not provide
full `.fsckpt` publication or fresh-process restore. M4 remains in progress;
there is no missing external dependency.

`SIMULATOR_CHECKPOINT_INVENTORY=FPGATop` requests
`.simulator-state.json` and `.simulator-reference.fir` through Golden Gate's
CLI (`--simulator-checkpoint-inventory FPGATop`). The root is the actual
metasim FPGATop module, rather than the physical platform shim or the original
DUT. Every reachable instance, register and logical RAM is enumerated.
StateIDs use `generated-simulator-state-v1`, independently of semantic IDs.
The manifest hashes the reference IR and each instance's implementation and
explicitly declares `generated_rtl_only` / `external_runtime_required=true`.

FIRRTL's SystemVerilog emitter runs private lowering transforms but returns
its input circuit. Inventory reproduces that lowering on the returned input
without changing the emitted circuit or rerunning user HostTransforms. It
handles final instance connectors and explicitly lowered synchronous memory
pipeline registers. Remaining implicit pipelines, readwrite ports, opaque
modules without adapters, asynchronous resets, unresolved/non-bit state,
unsupported module wrappers and invalid hierarchies fail explicitly.

AbstractClockGate's exact inline implementation has an adapter for its stored
`enable` bit. The VCS BUFGCE model has a separate adapter for its procedural
output register `O`; the backend verifies the actual model file against the
pinned SHA-256 in the manifest. These are metasim model contracts, not a
claim about physical FPGA clock primitives. Other blackboxes fail closed.

The InventoryFixture manifest contains 529 entries, 539 words, 2,512 bits and
83 instances. This includes the transformed DUT/SRAM and its queued/in-flight
memory operation, FAME progress flags, LI-BDN channels/token queues, PeekPoke
bridge state, clock bridge counters, master and MMIO interconnect/reorder
queues. A separate scan of emitted RTL declarations checks exact membership
and shapes against the compiler inventory. It rejects missing, added,
reshaped and unsupported declarations. Only emitter initialization-only
`_RAND_<number>` temporaries are excluded; they do not affect continuation.

The VCS probe reads all 539 words after a settled host falling edge at three
execution points: active (DUT counter 1), outstanding plus queued (counter 19),
and held response (counter 20). These are host samples, not semantic target
cycle indices or a certified whole-runtime cut. All captured vectors are
known, correctly padded and complete. Files use `.generated-state.json` and
the explicit `generated_rtl_diagnostic` type; none is a full `.fsckpt`.

`checkpoint_owner_t` supplies default-unsupported schema/save/validate/load
hooks for widgets and stream engines. The registry inventories core widgets,
bridges and both stream engines in deterministic construction order.
`+fs-checkpoint-preflight`, `+fs-checkpoint=<path>` and `+fs-restore=<path>`
reject unsupported owners before simulation construction, initialization and
driver MMIO. All current drivers remain unsupported. Actual VCS processes
exit 1 for all three requests, identifying `widget/0` (the generated master
constructor), and never publish an incomplete checkpoint. Even if widget
adapters are later added, the currently unsupported runtime cut still rejects.

Reproduce from the Chipyard root (all diagnostics go under `runs`):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
python -m tools.checkpoint_formats.tests.verify_simulator_inventory_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration9/generated-inventory
python -m tools.checkpoint_formats.tests.verify_banked_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration9/m3-regression
python -m tools.checkpoint_formats.tests.verify_semantic_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration9/m2-regression
python -m unittest discover -s tools/checkpoint_formats/tests -v
```

Tests use VCS Y-2026.03-SP1, `-full64`, GCC/G++ 13, and `VCS_FLAGS=-Mupdate`
for reused Make builds. Scala tests cover namespace separation, repeated
instances, exact sidecar emission, emitter-introduced memory pipelines,
wide/signed state, opaque/altered clock models and async-reset rejection.
All 22 Python and 19 Scala tests pass without skips. Python tests cover complete
wide/memory capture, malformed manifests and independent RTL coverage rejection.
Full M2 passes all five fresh clean RTL processes (108 target samples and 1,404
comparisons), mismatch reporting and restore-negative tests. Full M3 retains
six byte-identical hardware/oracle captures, 547 stalled boundaries, 5 semantic
and 242 transfer-edge replay samples, and eight invalid client reads. Ordinary
clean InventoryDUT RTL and GCD VCS metasim (12 cycles) also pass. These regressions
validate the earlier semantic path; they do not establish full Level-1 restart.

Next: establish a coherent host/target clock and thread cut; implement audited
driver adapters and metasim harness/MMIO/PRNG/scheduler serialization; capture
`mm_t` functional DRAM and `mm_magic_t` burst/read/write response queues;
inventory and test an actual FASED configuration; bind all owner schemas and
builds to the independent `.fsckpt` codec; validate every handle/owner before
any restore deposit, then restore in a fresh process before target advancement.
Compare target-visible outputs and response timing with outstanding traffic.
InventoryFixture has no FASED bridge or host DRAM; their capture and continuation
remain unverified. General FPGA bank insertion, DMA and FPGA validation are
also unimplemented in this increment.

The two root papers' snapshot/trace and simulator-state synchronization
discussions were reread from existing text extractions under
`runs/m2-iteration7/`. No formal mapping, ASIC gate-level activity or power
result is claimed. Plans, conda files and PDFs were preserved; plan input hashes
are under `runs/m4-iteration9/plan-inputs.sha256`. No staging, commits, resets
or git cleaning occurred. The earlier proposed investigation of the discarded
HostTransforms result remains open; changing it could affect clock models and
requires separate regression evidence. No plan correction is proposed here.
