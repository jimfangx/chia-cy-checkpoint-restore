# M1 inventory verification and recovery

Iteration 6 verifies M1 acceptance after the license/environment recovery in
[progress.md](progress.md). Clean InventoryDUT VCS, InventoryFixture VCS metasim,
and GCD VCS metasim pass with Y-2026.03-SP1 and GCC/G++ 13. The fixture's four
reset checks now explicitly select the signal-value `expect` overload; literal
zero previously selected the Boolean overload and skipped those reads.
Diagnostic logs are under
`automations/checkpoint_loop/runs`. Run from the Chipyard root unless stated otherwise.

Current verification logs are in `runs/m1-iteration6`: `compiler-tests.log`
(14 Scala tests), `formats.log` (10 Python tests), `inventory-codecs.log` and
`fixture-codecs.log` (both actual manifests and seeded containers),
`clean-build.log`, `clean-run.log`, `fixture-vcs.log`,
`fixture-output/InventoryFixture.vcs.out`, `gcd-vcs.log`, and
`gcd-output/GCD.vcs.out`. All commands completed successfully. The existing
full Golden Gate artifacts were reused; Make's three verilog targets were up to date.

The source fixture is
`sims/firesim/sim/midas/src/test/resources/checkpoint/InventoryDUT.firrtl`;
the extension avoids FireSim's ignored `*.fir` build products. Selecting
`Harness.dut` excludes a harness register and inventories a counter, FSM,
three array members, two Leaf instances, and an 8x9-bit async-read SRAM.
The Scala test lowers actual FIRRTL, checks all eight state entries, and emits
clean DUT-only SystemVerilog for VCS. The retained reference includes the harness.
StateIDs use lowered member names, independent of final Verilog names. A source
rename or different lowering algorithm may change IDs; build/manifest hashes
reject incompatible inventories. No state mapping through FAME is implemented.

Compiler tests (14 passed; no skipped/pending tests):

```sh
source env.sh && source sims/firesim/env.sh
cd sims/firesim/sim
CHECKPOINT_TEST_ARTIFACT_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m1-inventory \
java -Xmx8G -Dsbt.server.forcestart=true -Dsbt.server.autostart=false \
  -jar sbt-launch.jar -Dsbt.ivy.home="$PWD/.ivy2" \
  -Dsbt.global.base="$PWD/.sbt" -Dsbt.boot.directory="$PWD/.sbt/boot" \
  -Dsbt.supershell=false \
  'midas/testOnly midas.checkpoint.SemanticStateInventorySpec midas.stage.*'
```

`sbt.server.forcestart` permits batch startup despite denied server socket
creation. Environment/conda files are sourced without modification.

Format tests and verification of the actual Scala manifest in Python (passed):

```sh
python -m unittest discover -s tools/checkpoint_formats/tests -v
python -m tools.checkpoint_formats.tests.verify_inventory automations/checkpoint_loop/runs/m1-inventory
```

Artifacts: InventoryDUT.semantic-state.json, InventoryDUT.semantic-reference.fir,
InventoryDUT.sv, InventoryDUT.rtlckpt, InventoryDUT.fsckpt, InventoryDUT.trace.
Checkpoint values are seeded synthetic data. They do not claim capture, trace
recording, simulator ownership completeness, or replay. Semantic decode rejects
missing/extra/wrong-shaped state even with valid checksum and manifest hash.
Restoration must use manifest-bound validation, not the low-level container API.

Ordinary clean RTL VCS (iteration 6 compiled and simulated successfully):

The commands below now select Y-2026.03-SP1; iteration 4 logs used an older
release. Source `vcs-env.sh` last to load licenses and override login-shell
`VCS_HOME` before retrying.

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
timeout 90 "$VCS_HOME/bin/vcs" -full64 -sverilog \
  -timescale=1ns/1ps -top InventoryDUT_tb \
  -Mdir=automations/checkpoint_loop/runs/m1-iteration6/clean-csrc \
  -o automations/checkpoint_loop/runs/m1-iteration6/clean-simv \
  automations/checkpoint_loop/runs/m1-inventory/InventoryDUT.sv \
  tools/checkpoint_formats/tests/InventoryDUT_tb.sv
automations/checkpoint_loop/runs/m1-iteration6/clean-simv
```

The bench checks reset, FSM progression,
all array members, both leaf instances, and every RAM word; it does not restore.

Full Golden Gate build (passed) and GCD VCS metasim (passed after environment recovery):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
cd sims/firesim/sim
make verilog DESIGN=GCD TARGET_CONFIG=NoConfig PLATFORM_CONFIG=DefaultF2Config \
  BUILD_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m1-metasim
timeout 90 make run-vcs DESIGN=GCD TARGET_CONFIG=NoConfig PLATFORM_CONFIG=DefaultF2Config \
  SEMANTIC_CHECKPOINT_ROOT=GCD.dut \
  BUILD_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m1-metasim \
  OUTPUT_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m1-iteration6/gcd-output \
  "VCS=$VCS_HOME/bin/vcs -full64" VCS_FLAGS=-Mupdate
```

GCD reported PASS after 12 target cycles in iteration 6. GCD is a compiler and
execution regression; the SRAM/array fixture's VCS runtime check is described below.

Full compiler with opt-in discovery (passed):

```sh
mkdir -p automations/checkpoint_loop/runs/m1-gcd-inventory
source env.sh && source sims/firesim/env.sh
java -Xmx8G -Xss8M -cp automations/checkpoint_loop/runs/m1-metasim/firesim-main.jar \
  midas.stage.GoldenGateMain \
  -i automations/checkpoint_loop/runs/m1-metasim/f2/f2-midasexamples-GCD-NoConfig-DefaultF2Config/firesim.midasexamples.GCD.NoConfig.fir \
  -td automations/checkpoint_loop/runs/m1-gcd-inventory \
  -faf automations/checkpoint_loop/runs/m1-metasim/f2/f2-midasexamples-GCD-NoConfig-DefaultF2Config/firesim.midasexamples.GCD.NoConfig.anno.json \
  -ggcp firesim.midasexamples -ggcs DefaultF2Config \
  --output-filename-base FireSim-generated --allow-unrecognized-annotations \
  --no-dedup --semantic-checkpoint-root GCD.dut
```

Outputs under runs/m1-gcd-inventory include FireSim-generated.semantic-state.json
and FireSim-generated.semantic-reference.fir alongside the simulator. Python
validated nine distinct DUT register IDs, bridge exclusion, canonical JSON,
and reference hash. Capture, hardware transport, replay, ASIC activity, and FPGA
validation remain later work. Unsupported state stays an explicit compile error.

Full-fixture metasim (iteration 6 passed):

`InventoryFixture.scala` and `TestInventoryFixture.cc` are executable counterparts
of the FIRRTL fixture. The driver checks reset, each target-cycle counter/FSM
transition, all three register array members, repeated leaf instances, and every
SRAM address. The corrected driver compiled and passed 84 actual signal checks,
including four reset reads, after 22 reported target cycles. A C++ syntax check
also passed. The PeekPoke bridge's global precise-peek flag did not assert and
the driver emitted unstable-value warnings. Observed values matched; settled
trace-boundary sampling remains an M2 requirement. No replay is claimed.

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
cd sims/firesim/sim
make verilog DESIGN=InventoryFixture TARGET_CONFIG=NoConfig PLATFORM_CONFIG=DefaultF2Config \
  SEMANTIC_CHECKPOINT_ROOT=InventoryFixture.dut \
  BUILD_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m1-metasim
timeout 90 make run-vcs DESIGN=InventoryFixture TARGET_CONFIG=NoConfig PLATFORM_CONFIG=DefaultF2Config \
  SEMANTIC_CHECKPOINT_ROOT=InventoryFixture.dut \
  BUILD_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m1-metasim \
  OUTPUT_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m1-iteration6/fixture-output \
  "VCS=$VCS_HOME/bin/vcs -full64" VCS_FLAGS=-Mupdate
```

`SEMANTIC_CHECKPOINT_ROOT` passes the opt-in compiler argument through Make.
The `verilog` and `compile` targets request both semantic sidecars, so selecting
discovery also recompiles an existing opt-out build with missing sidecars. Use a
separate build directory when changing the selected root of an existing inventory.

Verify the actual full-compiler eight-entry manifest and seeded format artifacts
from the Chipyard root:

```sh
python -m tools.checkpoint_formats.tests.verify_inventory \
  automations/checkpoint_loop/runs/m1-metasim/f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config \
  --basename FireSim-generated --dut-root InventoryFixture.dut \
  --configuration InventoryFixture-NoConfig-DefaultF2Config
```

Conditional memory writes lower to clock nodes containing `validif(enable, clock)`
and enable nodes containing `mux(enable, 1, 0)`. Discovery resolves only those
aliases with equal Boolean identities. The validity guard is harmless while
that memory port is disabled. Unrelated guards, conditional register clocks,
and derived/gated clocks continue to fail explicitly. Regression tests cover
direct and node-aliased guarded memory clocks and their rejected counterparts.
Only combinational nodes/wires are enable aliases: a register's next-state
driver must never stand in for its stored value. A delayed-enable negative test
checks this distinction.

Iteration 5's license failures are historical; iteration 6 successfully compiled
and executed clean RTL and both VCS metasim targets with the required release.
Capture, restore, replay, ASIC activity, and FPGA validation remain later work.
Report individual nonempty output files as artifacts; the loop's
artifact check does not accept directory paths or empty successful-check logs.
