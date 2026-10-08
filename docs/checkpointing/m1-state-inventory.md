# M1 inventory verification and recovery

Iteration 5 adds an executable FireSim inventory fixture and handles Chisel's
conditional SRAM write clock validity. VCS Y-2026.03-SP1 execution is blocked by
license checkout. Diagnostic logs are under
`automations/checkpoint_loop/runs`. Run from the Chipyard root unless stated otherwise.

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

Ordinary clean RTL VCS (attempted; license failure, exit 255):

The commands below now select Y-2026.03-SP1; iteration 4 logs used an older
release. Source `vcs-env.sh` last to load licenses and override login-shell
`VCS_HOME` before retrying.

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
timeout 90 "$VCS_HOME/bin/vcs" -full64 -sverilog \
  -timescale=1ns/1ps -top InventoryDUT_tb \
  -Mdir=automations/checkpoint_loop/runs/m1-inventory/y2026-clean-csrc \
  -o automations/checkpoint_loop/runs/m1-inventory/y2026-clean-simv \
  automations/checkpoint_loop/runs/m1-inventory/InventoryDUT.sv \
  tools/checkpoint_formats/tests/InventoryDUT_tb.sv
```

After successful compilation, run `runs/m1-inventory/y2026-clean-simv` using the full
path beneath automations/checkpoint_loop and the same library environment.
This runtime command has **not** run. The bench checks reset, FSM progression,
all array members, both leaf instances, and every RAM word; it does not restore.

Full Golden Gate build (passed) and VCS metasim attempt (license queue; timeout 124):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
cd sims/firesim/sim
make verilog DESIGN=GCD TARGET_CONFIG=NoConfig PLATFORM_CONFIG=DefaultF2Config \
  BUILD_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m1-metasim
timeout 90 make vcs DESIGN=GCD TARGET_CONFIG=NoConfig PLATFORM_CONFIG=DefaultF2Config \
  BUILD_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m1-metasim \
  "VCS=$VCS_HOME/bin/vcs -full64"
```

No metasim binary/runtime result is claimed. GCD is a compiler regression;
the SRAM/array fixture's pending VCS runtime check is described below.

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

Iteration 5 full-fixture metasim preparation:

`InventoryFixture.scala` and `TestInventoryFixture.cc` are executable counterparts
of the FIRRTL fixture. The driver checks reset, each target-cycle counter/FSM
transition, all three register array members, repeated leaf instances, and every
SRAM address. A C++ syntax check passed. A simulation pass requires VCS license
checkout; do not infer execution from compiler or syntax-check results.

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
  "VCS=$VCS_HOME/bin/vcs -full64"
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

The new clean RTL attempt uses the required release and ends with exit 255:
"Server node is down or not responding" / "Failed to obtain license".
Both InventoryFixture and GCD VCS metasim attempts time out after 90 seconds
in the license queue (exit 124).
No clean RTL simulation, metasim execution, capture, restore, or FPGA validation
is claimed. Report individual nonempty output files as artifacts; the loop's
artifact check does not accept directory paths or empty successful-check logs.
