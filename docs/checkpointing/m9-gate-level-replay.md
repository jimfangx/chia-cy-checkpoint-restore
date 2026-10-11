# M9 gate replay and activity — iteration 68

Status: ready for small synthesized-DUT gate replay/activity acceptance.
All 50 proven profiles and final artifact audits pass. Diagnostic artifacts are in
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m9-iteration68/`.
The loop's M9 task corresponds to agent-plan Phase 11/M10. Both plans remain
read-only, including the pre-existing dirty agent plan.

`tools.checkpoint_formats.gate_replay` prepares a fresh ordinary VCS harness
from a complete, currently revalidated M8 formal map, independent `.rtlckpt`
and recorded trace. Its CLI takes `--proof-run`, `--checkpoint`, `--trace`,
`--configuration` and `--out`. All input validation completes before loader
files are created. Map transformations, constant horizons, merged-source
consistency and complete SRAM contents/pipeline/port state retain M8 checks.
Unsupported state fails explicitly; Level-1 simulator checkpoints are separate.

The only design compilation sources are the proven emitted Genus netlist and
its hash-bound functional cell models. VPI deposits initialize all gate words;
readback and combinational/input settling precede the first target edge.
Every recorded pre-edge output is checked. Native VCS toggle monitoring starts
after initialization and covers exactly three simulation nanoseconds per replayed
target cycle. `gate_level.saif` comes directly from VCS simulating those gates.
The native `rtl_on,mda` policy includes register/array data types inside gate
models; it does not select original RTL as the simulation design.

VCS VCD omits unpacked arrays during hierarchy dumping. Read-only bound probes
expose the actual mapped memory words as wires. The auditor compares physical
memory SAIF entries with those VCD witnesses and scalar storage directly, including
T0/T1/TX/TC, complete membership and clock transitions. Witnesses do not drive
state or alter the proven netlist/models. The initial VCD dump occurs a full
timestep before the first edge so it cannot absorb that edge's storage updates.

`tests.verify_gate_replay` accepts a proof run or multiple M8 `--catalog` files.
Each call creates new build directories and simulates restored and continuous
gates, plus ordinary clean RTL. Continuous inputs before the checkpoint come
from the recorded capture, not a regenerated stimulus formula. Sampled outputs
and every native-SAIF signal's metrics must agree. Actual faults corrupt all
physical copies of one semantic bit and must fail at the first sampled boundary.
Nine real SAIF/VCD mutations per profile test incorrect producer, window, clock
counts, missing state, unknown state and waveform integrity. Mutated artifacts
are saved under each invocation's `activity-mutations/`.

All profiles restore at pre-edge C=17, compare 79 boundaries/237 outputs and end
C=96. There are 100 fresh gate builds/processes, 50 fresh ordinary RTL replay
builds and 100 real native SAIF files with 237 ns windows. Scalar direct/inverted
profiles initialize 24 bits and record 308 storage transitions; SRAM profiles
initialize 35 bits and record 875 transitions, with all 16 contents bits checked
through memory VCD witnesses. Every mapped storage bit matches same-run VCD.
All native-SAIF signal metrics match the continuous run for every profile.

All 50 actual storage faults, 450 actual activity-file mutations and 400 actual
provenance mutations reject. Fifty unchanged provenance controls pass; mutation
checks restore all original bytes. Rehashed changed harnesses/deposits, changed
compiled netlists/models, RTL compilation sources, forged sampled outputs,
incorrect trace identity and removed zero-edge readback cannot pass the auditor.
All 131 Python tests and complete M2/M3 metasim/ordinary RTL regressions pass.
The final preparation audit revalidates all current inputs and regenerates the
exact harness/deposits used in the 50 successful fresh builds. Diagnostic pilot
failures are retained; no verification scope was reduced or skipped.

`tests.audit_gate_replay` rechecks the final artifacts, current proofs, exact
compiled sources/harness/deposits, native activity, recorded outputs and rejection
controls. Invoke it with `--catalog matrix-results.json --out audit-results.json`.
Every VCS shell must source Chipyard `env.sh`, FireSim `env.sh`, then
`automations/checkpoint_loop/vcs-env.sh` LAST; VCS Y-2026.03-SP1, `-full64` and
GCC 13 are required. Build/simulation commands and raw logs are saved per run.
Final selections, exact commands and full-path/hash catalogs:
`matrix-complete/matrix-results.json`, `verification-commands-final.json`,
`independent-audit.json`, `provenance-audit.json`, `current-input-audit.json`,
`summary.json` and `artifact-manifest.json` under the iteration run directory.

These are small zero-delay synthesized functional fixtures; the captured samples
used for gate acceptance originate in ordinary RTL VCS. M2/M3 independently
exercise real VCS metasim capture and ordinary RTL replay. Production metasim
DUTs need their own complete formal maps before this gate path can accept them.
No FPGA or process ASIC validation is claimed. Joules is installed and other
technology libraries exist, but they do not characterize the proven CK* cells
and explicit CKSRAM architecture. The matching fixture Liberty files lack
cell power/leakage tables. No power estimate is generated from those libraries.
Protected plans/PDFs, staging and FireSim status are unchanged. No conda edits,
commits, resets or cleaning were performed. Further process-library, timing-aware
or production metasim DUT acceptance requires its own synthesis/proof/map and
matching characterized models; no FPGA or production power claim follows from
these functional fixtures.
