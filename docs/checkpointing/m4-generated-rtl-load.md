# M4 generated RTL component loading — iteration 21

M4 remains in progress. `tools/checkpoint_formats/generated_restore.py` and
`generated_restore.cc` provide a manifest/build-bound VCS loader for the
generated RTL component. They do not publish or consume `.fsckpt`. Existing
production full-checkpoint requests still reject unsupported runtime owners
before initialization and cannot publish an incomplete checkpoint.

The trusted staging header binds the canonical generated manifest, independently
checked emitted RTL and pinned BUFGCE implementation. Its compiled table binds
the exact ordered register/memory membership, widths, depths and indexed paths.
The table scales with entries, not expanded RAM words. Python validates the
complete captured diagnostic before creating staging text; VPI rechecks the
header, every row, bits, padding and every handle before any deposit. VCS may
expose indexed memory words as `vpiReg`; this representation is supported only
at exact compiled indexed paths/widths, with bank shape separately established
by emitted declaration coverage. Nets and incompatible handles reject.

Only settled low-host-clock cuts are supported. High BUFGCE output payloads
reject before mutation because depositing one could create a target edge.
All emitted clock sensitivities, including memory pipeline clocks and gated
clock I/O, must resolve and be known low before load and after settlement.
Unsupported sensitivity syntax fails explicitly. A second load cannot begin
until the first has passed complete post-settlement readback. Readback failure
is terminal; its pending state remains poisoned and the process must exit.
The coordinator must hold clocks stopped throughout this operation.

The verifier captures the actual complete generated `InventoryFixture` hardware
in an uninterrupted FireSim metasimulation (VCS backend). Three fresh standalone
VCS processes load active, outstanding/queued and held-response cuts, compare
all 539 words before any host/target edge, then replay every recorded host input
through the remainder of the run. Every 2,512-bit generated state vector and
every generated top output is compared at every following host sample. No host
sample is removed. This tests generated hardware continuation with recorded
host inputs, not native host/harness/driver reconstruction or whole FireSim
restart. The fixture has no FASED model; production FASED remains covered by
the existing full capture/timing regressions.

The final component run captures 426,421 reference host samples. Cuts at
14,374/376,226/385,388 compare 412,047/50,195/41,033 samples respectively,
503,275 in total. All three fresh processes verify every word before their
first edge. Real VCS passes 557 atomic rejections; native sanitizers pass 333.
The current complete Python suite passes 35 tests.

All 25 prior regression scopes pass, including 20 Scala tests, compiler codecs
and memory coverage, all existing native/VCS owners, full M2/M3, ordinary clean
RTL VCS, default/randomized GCD, profiled FCFS and both rejection-liveness
suites. All five production settled cuts retain all 13,507,456 generated words
and four full 4 MiB functional-memory channels. Complete 40-port AXI/FAME
traces and generated observations match uninterrupted references byte-for-byte.
Default completion remains 774,628 target cycles; randomized completion is
774,632. The late cut retains an in-flight native write and outstanding FASED
traffic. These production regressions preserve capture/timing behavior; they
do not add full-runtime loading or FASED fresh-process restore acceptance.

Native ASan/UBSan checks the actual loader through a controllable VPI fixture:
257-bit scalar packing, both 9-bit memory words, every byte-truncated prefix,
missing/reshaped/net handles at each position, high/unknown clocks, unverified
loads and terminal readback failure. Real VCS also checks every missing-row
prefix, reordered/duplicate/extra owners, malformed headers/bits, final-row
corruption and a high clock output, with full state/edge guards.

Evidence and exact command arrays are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m4-iteration21/`.
The full prior 25 regression scopes are retained. Failed/superseded initial
trials remain in separate diagnostic directories, including the first expanded
reference trial, which was interrupted to use an equally complete packed
state vector, and the initial strict memory-handle and native naming trials.
The final evidence audit checks current component artifacts and full production
traces. The artifact catalog contains full paths and source hashes.

Reproduction from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_generated_restore_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration21/generated-restore-verified
python automations/checkpoint_loop/runs/m4-iteration21/run-regressions.py
```

Next: own simulation initialization/finalization and output history, restore
harness banks and parked dispatcher/DPI continuation, and establish a supported
runtime cut/clock phase. Bind/prevalidate/load all generated and software owners
in an aggregate manifest/executable-bound `.fsckpt`, then restore a fresh full
VCS metasim with outstanding native/FASED traffic and compare target outputs
and transaction timing. FPGA-managed streams remain unsupported.

The relevant DESSERT and Strober passages were read from the existing root-paper
text extractions under `runs/m2-iteration7/`: complete memory/state and exact
token/I/O timing remain necessary. Level-1 and Level-2 remain independent.
Every VCS shell sources both environments then `vcs-env.sh` last, using
Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`.
There is no missing external dependency. No whole-runtime, physical FPGA,
formal or ASIC activity/power acceptance is claimed. Both plans, conda files
and root PDFs remain untouched; no plan correction is proposed.
