# M10 production DUT formal map — iteration 69

Status: in progress. Production synthesis and memory architecture validation are
the current increment. No production formal state map or gate restore is yet
authorized. M6/M7 and the small synthesized-DUT M8/M9 acceptance remain complete.
Both input plans remain read-only, including the previously dirty agent plan.
The loop's M10 extends the agent plan's Phase 10/11; it does not require FPGA
hardware or power characterization. No process ASIC, power or FPGA claim follows.

Selected configuration:
`AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config`, pre-FAME
`AXI4FuzzerDUT`, semantic root `AXI4Fuzzer.fuzzer_`. Self-contained real M6/M7
inputs are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m7-iteration54/finite-replay-final/invocation-tkq1rf1b/production/inputs/`.
Use its exact semantic-clean RTL, StateID and boundary manifests, `capture.rtlckpt`
and `capture.trace`. These contain 1,543 entries, 1,342 registers and 201 RAMs:
102,993,417 bits / 13,503,308 words. The trace covers all 250,185 pre-edge
boundaries C=524453..774637, END C=774638, with 34 outputs per boundary.

`tools/checkpoint_formats/production_dut.py` validates the complete original
hierarchy/boundary, applies restricted SYNTHESIS preprocessing, and extracts
the emitter's single-write, one/two asynchronous-read memories into concrete
unparameterized functional models. It retains every original StateID and every
register, including existing pipeline/port state. Memory contents move to
`ckmem_<original_name>.contents`; no extra pipeline latency or memory state is
introduced. There are 17 model shapes across the 201 instances. Nested write
guards, extra accesses, partial writes, unsupported clocks/ports, unknown active
macros, missing/hidden/reshaped state and changed generated artifacts reject.

`architecture-candidate.json` is explicitly an **unproven synthesis architecture**,
not `asic_state_map.json`. Every candidate is marked unproven. Its reconstruction
audit compares the complete candidate and generated source bytes against the
current original RTL and manifests. Merely changing hashes or labeling an entry
proven cannot pass. M8's flat-map/depth checks have not been weakened.

`production_synth.tcl` uses installed Genus, the existing concrete CK standard
cells and explicit preserved memory stubs. It synthesizes the complete selected
top, disables retiming, binds input/netlist hashes and exports the actual
preserved memory hierarchy. Stubs serve synthesis only; formal/VCS must use
`memory-models.v`. These are zero-delay functional models with artificial
standard-cell timing/area, without process characterization or power data.

`hierarchical_state.py` inventories every reachable cell and physical storage
shape using hash-bound concrete models. Complete memory spans avoid allocating
102 million individual Python objects. Instance components preserve escaped
names and hierarchy copies. Unknown/empty-model leaves, procedural netlist
state, hidden model state, missing memory words and disconnected/unsupported
target clocks reject. This inventory is also explicitly unproven; it supplies
physical membership obligations for the next formal adapter. Genus emits 17
declaration-only RAM interfaces alongside the mapped design definitions. These
interfaces must match the concrete models exactly. `bind_concrete_models`
selects a separate compilation source omitting only those empty interfaces;
all emitted logic definitions remain byte-identical and the raw netlist is
preserved. Bind both raw/selected netlist hashes and models in the future proof.

The completed real Genus netlist contains 62,158 cell/macro instances, including
all 201 memories and 7,256 physical register bits: 102,992,412 physical bits.
The original has 8,261 register bits. The 1,005-bit difference still requires
complete independent mapping, merging/constant/irrelevance proofs; it is not
excused by synthesis or finite replay. Independent synthesis/model-binding audits
pass, including a fresh repeated audit that preserves prior output files.
VCS compiles the complete selected netlist and concrete models successfully.
This is compile/elaboration evidence; no gate state is loaded and no gate replay
or mapped-state corruption test has been run.

`tests.verify_production_dut` creates a fresh invocation, starts complete Genus
synthesis, and prepares ordinary original-RTL and extracted-memory-architecture
VCS replays of the **full** captured trace. Both benches deposit/read back every
word before an edge, compare all outputs and dump all hierarchy/memory state to
VPD. Their matched boundary files must equal the exact recorded trace data.
This checks extraction behavior at the real checkpoint, not formal equivalence
or gate replay. `tests.audit_production_synthesis` independently reconstructs
the architecture and binds the current synthesis script/library/source/log,
emitted netlist, concrete models and complete physical memory shapes.

Diagnostics, protected input hashes and exact child commands are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m10-iteration69/`.
The current production invocation is `production/invocation-8yp22x6s/`.
Initial preprocessing whitespace, unittest-discovery import, emitted-interface
audit and JSON inventory round-trip revalidation failures are retained; all were
corrected. All 143 Python tests and the
complete M2/M3 metasim/ordinary-RTL regressions pass. Both fresh production RTL
VCS processes load/read back all 13,503,308 words at zero edges, replay all 250,185
cycles and match all 8,506,290 outputs per process, ending at C=774638.
Both independent waveform audits verify all initial words, every
memory declaration, all 50 boundary ports and 12,008,880 sampled input/output
values per process with exact cycle/edge timing. The fresh repeated whole
waveform audit passes too; both processes' full scope is checked twice.
Audits create fresh evidence on repetition; conversion outputs retain prior VCDs.

The latest synthesis evidence is selected by `synthesis-model-audit/selection.json`
(`invocation-wx2ert5m/evidence/`); the repeated whole waveform audit is selected by
`waveform-audit/selection.json` (`invocation-d6xmytyo/evidence/`). All paths are
under the iteration-69 directory above. `summary.json`, `verification-commands.json`
and `artifact-manifest.json` provide current validation, exact argv and a complete
full-path/hash file catalog. `finalize-evidence.py` reconstructs the current
architecture/inventory/model binding, checks both complete waveform results,
regression scope, protected plan/PDF hashes, staging, FireSim status and whitespace.

Next: audit emitted physical hierarchy, implement original-to-architecture and
architecture-to-netlist formal state relationships with all content/port/pipeline
obligations, independent optimized-state predicates and complete map provenance.
Every unmapped/unproven semantic or physical bit must still reject. Only after
that proof and independent audit may a fresh netlist/model-only VCS process
load/read back all mapped state, replay the full actual trace against fresh
ordinary RTL and detect deliberate mapped-state corruption at its first
divergent cycle. Finite architecture parity cannot satisfy those exit criteria.

Every VCS build/simulation/license shell must source Chipyard `env.sh`, FireSim
`env.sh`, and `automations/checkpoint_loop/vcs-env.sh` LAST. Use Y-2026.03-SP1,
`-full64`, the helper's GCC/G++ 13 and CC/CXX/VCS_CC. Reused Make builds use
`VCS_FLAGS=-Mupdate`. Level-1 simulator images remain independent of this
Level-2 mapping work. Preserve plans/PDFs/conda files, staging and git history.
