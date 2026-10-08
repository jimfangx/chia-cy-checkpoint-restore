# M3 banked semantic state access

Iteration 8 adds `midas.checkpoint.BankedStateAccess`, a synthesizable Level-2
capture controller, and an explicit binding for `InventoryBankedFixture`.
Controller/FIFO registers live outside `InventoryBankedFixture.dut` and never
enter its semantic manifest. The original InventoryFixture keeps access
disabled by default. Level-1 capture/restore remains independent.

The fixture has four logical banks: local scalar/array/pipeline registers,
each repeated leaf's saved register, and the 8x9-bit SRAM. Ordinary wires,
read muxes and a logical asynchronous memory port supply values. The controller
uses StateID-sorted manifest ordinals, then ascending memory addresses; each
beat carries entry, address, width, 64-bit zero-extended value, error and last.
A two-entry FIFO separates read selection from consumption. Selectors advance
only when enqueue succeeds. Freeze covers the accepting request edge through
consumption of the final beat, including backpressure and functional reset
attempts. All target register, leaf and SRAM writes honor freeze; reads do not
alter stored state. No target clock is replaced or derived for capture.

Checkpoint-control reset initializes the controller on semantic edge zero,
separately from the DUT's functional reset. The next before-edge boundary has
index one. Functional reset edges count normally; frozen transfer edges do
not advance semantic time. Five functional reset edges precede the fixture's
first active edge, retaining the M2 convention. The VCS oracle independently
counts semantic advances from the DUT's public freeze input. Raw transfer-edge
indices are retained as separate diagnostics, not used as checkpoint cycles.

Unsupported commands, requests while busy and bank read failures have separate
sticky error bits. A failed bank produces a terminal error beat and stops
selection; the host refuses an incomplete/error stream before emitting a
checkpoint. Busy requests are rejected without restarting the accepted
capture. Invalid banks, slots and logical addresses return error and zero data.
Bindings reject widths above 64 until chunking is implemented. Existing
inventory rejections for opaque state, unsupported clocks and hidden memory
pipelines continue to apply.

`SemanticBankedAccessAnnotation` survives generator serialization and is
checked against the complete pre-FAME manifest before Golden Gate transforms.
Missing, added, reordered, reshaped, ambiguous or incorrectly rooted bindings
fail compilation. `.semantic-access.json` records the binding and manifest
hash; Python independently validates this sidecar before capture. This is an
explicit fixture binding, not automatic instrumentation of arbitrary targets.

The metasim driver collects words solely through PeekPoke bridge MMIO over
controller public ports, including both 32-bit chunks of each data word. A
public-port VCS monitor separately records actual stream handshakes. Their
beat lists must agree exactly. Only the independent oracle bind reads DUT
internals; the hardware controller, bank clients and host serializer do not
use VPI, DPI, hierarchical simulator references or deposited shadow values.
PeekPoke's global unstable-value warnings remain, so settled FIFO reads are
also checked against handshakes rather than treated as sufficient evidence.

The acceptance script captures active, immediate-repeat, queued, outstanding,
held-response and post-error-recovery state. It fills/stalls the FIFO, changes
functional inputs and attempts SRAM writes and resets while frozen. It checks
every semantic word at every frozen boundary, stream stability under stalls,
exact ordering/completeness and byte-identical manifest-bound `.rtlckpt`
containers against the independently counted oracle. A fault capture is
rejected. Fresh ordinary clean RTL VCS processes replay both the hardware
checkpoint with its original semantic cycle and a separate trace of every
transfer edge; the latter also tests eight invalid client read selectors.

The final VCS run passes six complete 22-word captures at semantic cycles
13, 13, 15, 16, 18 and 22. Each hardware container is byte-identical to its
oracle; the repeat pair is identical too. There are 717 actual transfer edges,
23 semantic advances including reset, and 547 stalled valid-output boundaries.
The seventh (fault) capture terminates with error and cannot serialize.
The two fresh clean RTL processes deposit all 22 words before their first
edge and pass 5 semantic samples (75 output comparisons) and 242 raw-edge
samples (3,630 comparisons), respectively. Eight invalid client selectors
also pass explicit error checks. All 19 Python and 15 Scala tests pass without
skips, as do the full M2 five-case/negative-test suite, compiler manifest codec
corruption checks, ordinary InventoryDUT VCS and GCD VCS metasim regressions.

Run from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
python -m tools.checkpoint_formats.tests.verify_banked_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m3-iteration8/acceptance
python -m tools.checkpoint_formats.tests.verify_semantic_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m3-iteration8/m2-regression
python -m unittest discover -s tools/checkpoint_formats/tests -v
```

Use the same build root for these targets: this repository's sbt assembly cache
can return a jar at a previous output path when switching build roots. VCS's
cached external-C makefile also omits `entry.d`; the M3 verifier invalidates
only stale generated `entry.o` when the generated bridge registry changes.
`VCS_FLAGS=-Mupdate` regenerates the cached VCS Makefile for the required
Y-2026.03-SP1 release. GCC/G++ 13 and `-full64` are used for all VCS checks.

Diagnostics reside under `automations/checkpoint_loop/runs/m3-iteration8/`.
The acceptance directory contains `summary.json`, public `ports.jsonl`, the
oracle's `capture.jsonl`, separate edge/semantic trace rows, each capture's
`beats.json`, `hardware.rtlckpt` and `oracle.rtlckpt`, and both clean replay
build/run logs and VCDs. Compiler sidecars and emitted simulator RTL are under
`runs/m3-metasim/f2/f2-midasexamples-InventoryBankedFixture-NoConfig-DefaultF2Config/`.
Regression/test logs, manifest codec checks and read-only plan hashes are
under the iteration directory; no diagnostics are stored in tracked docs.

Scope is the supported small DUT with explicit clients and asynchronous
logical SRAM reads. Automatic bank insertion, general FAME mapping/threading,
Rocket/BOOM state and synchronous-read memory pipelines remain unsupported.
CheckpointBridge/DMA is M5, not the PeekPoke verification transport. No physical
FPGA, FPGA synthesis/resource/timing validation, Level-1 continuation, formal
proof, ASIC gate-level activity or power validation is claimed. The root
papers' state/trace replay discussions were reread from their existing text
extractions under `runs/m2-iteration7/`; RTL VCDs are debugging artifacts.

Plans remain read-only; their hashes are in `runs/m3-iteration8/plan-inputs.sha256`.
No plan correction is proposed.
