# M1 inventory verification and recovery

Iteration 4 implements discovery and semantic manifest validation. VCS execution
is blocked by license checkout. Diagnostic logs are under
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

Compiler tests (13 passed; no skipped/pending tests):

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

```sh
source env.sh && source sims/firesim/env.sh
export LD_LIBRARY_PATH="$PWD/.conda-env/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
timeout 90 /ecad/tools/synopsys/vcs/W-2024.09-1/bin/vcs -full64 -sverilog \
  -timescale=1ns/1ps -top InventoryDUT_tb \
  -Mdir=automations/checkpoint_loop/runs/m1-inventory/clean-csrc \
  -o automations/checkpoint_loop/runs/m1-inventory/clean-simv \
  automations/checkpoint_loop/runs/m1-inventory/InventoryDUT.sv \
  tools/checkpoint_formats/tests/InventoryDUT_tb.sv
```

After successful compilation, run `runs/m1-inventory/clean-simv` using the full
path beneath automations/checkpoint_loop and the same library environment.
This runtime command has **not** run. The bench checks reset, FSM progression,
all array members, both leaf instances, and every RAM word; it does not restore.

Full Golden Gate build (passed) and VCS metasim attempt (license queue; timeout 124):

```sh
source env.sh && source sims/firesim/env.sh
export LD_LIBRARY_PATH="$PWD/.conda-env/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
cd sims/firesim/sim
make verilog DESIGN=GCD TARGET_CONFIG=NoConfig PLATFORM_CONFIG=DefaultF2Config \
  BUILD_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m1-metasim
timeout 90 make vcs DESIGN=GCD TARGET_CONFIG=NoConfig PLATFORM_CONFIG=DefaultF2Config \
  BUILD_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m1-metasim \
  'VCS=/ecad/tools/synopsys/vcs/W-2024.09-1/bin/vcs -full64'
```

No metasim binary/runtime result is claimed. GCD is a compiler regression,
not metasim coverage of the full SRAM/array fixture; add that coverage later.

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
