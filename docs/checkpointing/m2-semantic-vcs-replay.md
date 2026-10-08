# M2 semantic VCS replay

Iteration 7 implements the Level-2 backdoor prototype on InventoryFixture.
The opt-in compiler emits the complete pre-FAME state inventory, retained
FIRRTL, DUT-only ordinary RTL, and complete boundary manifest. Capture and
restore do not use a Level-1 checkpoint.

The fixture has 15 semantic entries (22 register/memory words), including an
8x9-bit SRAM, repeated leaf registers, scalarized arrays, an FSM, a request
queue, a two-cycle memory operation, and a held response. It runs with work in
flight; checkpoint selection does not drain or reset it.

`tools/checkpoint_formats/replay.py` validates an identity mapping against
both emitted RTL inventories and all boundary ports, then generates a VCS
module bind. It explicitly rejects renamed, missing, extra, reshaped, or
threaded state and multiple DUT instances. This is an oracle for a single
hierarchy-preserving DUT, not general mapping through Golden Gate.

Each capture row C contains state S[C], inputs I[C], and settled combinational
outputs O[C] in the actual DUT rising-edge active region, before sequential
NBA updates. The gated target clock counts edges; host/model stalls do not
generate samples. The fixture produces 37 actual DUT edges (0..36); its clock
bridge reports 38. The verifier independently checks five reset edges and
the counter relation `counter[C] = C - 5` after reset. Bridge counts and
PeekPoke's unstable reads are not used as checkpoint indices.

The package/loader validates integrity, configuration, reference and manifest
hashes, exact state membership and shapes, complete boundary membership and
widths, consecutive trace indices, and checkpoint/trace cycle agreement.
Unknown X/Z values fail explicitly. A DPI/VPI loader resolves and checks
every register/memory-word handle before any deposit. The ordinary RTL bench
checks every deposited word before its first edge, applies I[C], settles,
compares all O[C], then clocks the DUT. It generates full DUT VCD waveforms.
Failure reports the first differing signal, original target cycle, expected
and actual values, and exits nonzero through DPI; this VCS release printed
`$fatal` but returned zero in the initial negative test.

The acceptance script starts five separate ordinary clean RTL VCS processes:

| Checkpoint | C | Samples through C=36 | Captured condition |
| --- | ---: | ---: | --- |
| reset | 0 | 37 | Before the first target reset edge |
| active | 5 | 32 | Active counter/FSM; SRAM write at the selected edge |
| queued | 22 | 15 | Nonempty request queue |
| outstanding | 24 | 13 | Memory operation active, one cycle remaining, queue nonempty |
| stalled | 26 | 11 | Response valid, ready low, queue nonempty |

All 108 sampled cycles and 1,404 output comparisons pass. Each process verifies
all 22 restored words. A checksummed trace with an intentionally changed
`io_respData` first fails at target cycle 29 and exits 1. Missing state handles,
incorrect widths, malformed rows, and incomplete restore lists also exit 1
before depositing state. The 14 Scala inventory/stage tests and 15 Python
format/semantic/replay tests pass without skips. Clean InventoryDUT VCS and
GCD VCS metasim regressions pass.

Run from the Chipyard root; all VCS work uses Y-2026.03-SP1, `-full64`, and the
GCC/G++ 13 toolchain supplied by the helper sourced last:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
python -m tools.checkpoint_formats.tests.verify_semantic_vcs \
  --build automations/checkpoint_loop/runs/m2-metasim \
  --out automations/checkpoint_loop/runs/m2-iteration7/acceptance
python -m unittest discover -s tools/checkpoint_formats/tests -v
```

The acceptance script performs Golden Gate generation, capture generation,
VCS metasim build/run, manifest-bound serialization, five clean RTL build/runs,
waveform generation, the trace mismatch test, and four loader failure tests.
`VCS_EXTRA_V` adds the generated bind as a real Make dependency. Build command
arguments, process IDs, results, and all diagnostics are recorded under the
selected output directory. `VCS_FLAGS=-Mupdate` refreshes VCS cached build files.

Compiler/unit regression command:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
cd sims/firesim/sim
CHECKPOINT_TEST_ARTIFACT_DIR=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m2-iteration7/compiler-fixture \
java -Xmx8G -Dsbt.server.forcestart=true -Dsbt.server.autostart=false \
  -jar sbt-launch.jar -Dsbt.ivy.home="$PWD/.ivy2" \
  -Dsbt.global.base="$PWD/.sbt" -Dsbt.boot.directory="$PWD/.sbt/boot" \
  -Dsbt.supershell=false \
  'midas/testOnly midas.checkpoint.SemanticStateInventorySpec midas.stage.*'
```

Evidence is under `automations/checkpoint_loop/runs/m2-iteration7/`:
`acceptance.log`, `acceptance/summary.json`, `acceptance/capture.jsonl`, each
case's `capture.rtlckpt`, `capture.trace`, `restore.txt`, `replay.sv`, `build.log`,
`run.log`, and `replay.vcd`; mismatch and loader-failure logs; compiler/Python
test logs, compiler-codecs log, inventory-clean build/run logs, and GCD logs.
The full compiler sidecars are under
`runs/m2-metasim/f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config/`.

This establishes the small-DUT M2 prototype. Rocket/BOOM processor pipelines,
FAME model extraction/threading/renaming, synchronous memory read pipelines,
general FPGA transport, Level-1 continuation, ASIC gate-level activity, and
power estimation are unvalidated. No physical FPGA is available. The memory
pipeline here is explicit ordinary target registers with asynchronous SRAM
reads, within the existing inventory's supported semantics. M3 must implement
synthesizable extraction and test it in metasim; the current bind is a VCS
oracle only. Both papers' replay discussions were read from text extracted
under runs; RTL VCD is a debugging artifact, not ASIC activity.

Both plans remain read-only. Their initial SHA-256 snapshots are in
`runs/m2-iteration7/plan-inputs.sha256`; no plan correction is proposed.
