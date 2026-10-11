# M10 production DUT formal map — iteration 71

Status: in progress. All retained real queue modules now have audited local
register-induction and memory-port-congruence proofs. Complete production
hierarchy/optimized-state/memory/boundary composition remains unproven.
No production map, gate initialization, gate replay or mapped-state corruption
acceptance is claimed. Completed M6/M7 and small synthesized-DUT M8/M9
acceptance remain preserved. There is no required missing external dependency.

`tools/checkpoint_formats/production_queue.py` reconstructs the actual 165
retained Genus queue modules from the selected FCFS DUT. It binds every original
StateID/bit to a candidate module-relative CKDFF storage relationship and checks
complete membership of all local semantic and physical register bits. Unknown
cells, changed models, missing state/ports, unsupported clocks, shared/extra
queue hierarchy and changed synthesis identities reject. The original and
architecture RTL, raw/selected netlists, concrete cell/memory models, synthesis
inputs/log, semantic and boundary manifests and complete physical inventory
are bound. Module-relative candidates do not establish global instance bindings.

The formal adapter removes only the exact memory instance, exposes every
memory input (write enable/address/data and read address), and supplies a common
unconstrained read word. The real original queue logic and emitted gates/cell
models remain in the miter. Every register relationship must preserve the
complete local relation over a target edge; every memory input and every queue
output has its own equality assertion. Independent zero/one state covers,
edge, reset, write/hold and read-word covers plus every generated implication
precondition remain mandatory. There are no assumptions, reset sequences,
blackboxes or instantiated arrays. These are local array-cut obligations:
composition with equal complete memory contents and the surrounding hierarchy
is still required. No gate state may be loaded from this artifact.

The final installed Jasper 2025.03 run covers **all 165 retained modules**:
**1,135 register-bit transitions**, **660 complete memory-port equalities** and
**917 output equalities** prove, with **6,276 covers**. All **304 other output
assertions produce actual counterexamples**, retained explicitly in the result:
160 `io_deq_valid`, 128 `io_deq_bits_echo_tl_state_size` and 16
`io_deq_bits_tl_state_size`. The selected netlist declares the 160 dequeue-valid
ports without drivers in their leaf bodies. This diagnostic is recorded in
`undriven-local-output-diagnostic.json`; it does not prove global irrelevance.
Full-DUT boundary equivalence must discharge these obligations or synthesis
must change. Ready/valid qualification or finite trace agreement cannot waive
any sampled output requirement.

All **eight fresh negative CAD runs** produce counterexamples: wrong polarity,
missing register relation, inverted write enable and wrong read address, each
on real `Queue_2` and `Queue_39`. The independent auditor rebuilds the exact
miters/scripts/bindings, checks every property and raw individual engine result,
zero assumptions, nonvacuity and absence of blackboxing. **Two final audit
passes** each reject all **24 actual artifact mutations**, audit all eight
negative proofs and pass two unchanged controls. Changed/rehashed miters,
scripts, missing assertions/preconditions, forged statuses, missing raw engine
or input identities, hidden assumptions/blackboxes, missing StateIDs/physical
state/pending obligations and forged completeness/authorization reject.
Positive and negative proof bytes remain unchanged. Both raw and audited local
proof artifacts reject at the existing gate loader before checkpoint decoding.

The full composition catalog retains all **1,543 semantic entries** and
**7,457 physical storage spans / 102,992,412 bits**, plus the exact boundary
manifest. Every global storage relationship stays explicitly unproven. Of
8,261 semantic and 7,256 physical register bits, 7,126 and 6,121 respectively
remain outside the local queue theorem. The 1,005-bit difference still needs
independent merging/constant/irrelevance proofs; counts do not classify state.
The four flattened depth-one queues, all other pipelines/port registers and
all 201 complete memories remain full-DUT composition obligations.

Diagnostics are only under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m10-iteration71/`.
Final proof: `queue-proofs-final/invocation-6oqtswfn/positive/`, selected by
`queue-proofs-final/selection.json`. Final independent audits:
`queue-audit-final/invocation-393al0sn/` and `invocation-qgpj8qej/`, each with
`summary.json`, `independent-audit.json` and
`unproven-composition-obligations.json`. Use the selection/catalog files rather
than treating the run directory itself as a report artifact: the loop requires
nonempty regular files. The initial property/input reset-name collision and an
incorrect evidence-directory invocation are retained as diagnostics; the
complete final production proof and negative scope reran after correction.

All **151 Python tests** and complete **M2/M3 VCS metasim/ordinary-RTL
regressions** pass. An initial M2 VCS frontend `branch_bb == 0` assertion is
retained; the fresh complete retry passes with unchanged test scope and pinned
Y-2026.03-SP1/-full64/GCC 13. Complete production synthesis/disabled-retiming/
concrete model binding passes a fresh audit. All 17 prior universal memory
adapter theorems and all 178 memory evidence mutations pass fresh audits.
Both complete prior production original/extracted-memory RTL waveform audits
pass with fresh conversions: each checks all 13,503,308 zero-edge words, all
201 memories/50 boundary ports and 250,185 boundaries/12,008,880 sampled
input/output values, ending at C=774638. These are prior RTL executions
re-audited now, not new gate simulations.

`summary.json`, `verification-commands.json`, `artifact-manifest.json` and
`protected-and-whitespace-audit.json` provide scope, exact argv, full-path/hash
catalog and protected-input/staging checks. Recover with the self-contained
M7 inputs and preserved iteration-69 synthesis described below. Next: construct
the complete top/hierarchy state relation, discharge every local output
counterexample at the real DUT boundary, prove optimized-state predicates and
compose all memory transitions/ports, then independently audit a complete map.
Only then run fresh gate VCS complete zero-edge deposits/readback, the entire
actual metasim trace against fresh ordinary RTL, and real mapped-state
corruption with first-divergence checks. Source both repository environments
and `vcs-env.sh` LAST in every VCS shell. FPGA hardware and power characterization
are not dependencies. Level-1 images remain independent. Plans/PDFs/conda files,
staging and history are preserved; no FPGA, process ASIC or power claim.

## Preserved iteration-70 memory adapter evidence

Status: in progress. The original-to-architecture memory adapter now has
independently audited universal word proofs for the selected real production
DUT. Complete original/architecture/netlist register and boundary composition,
optimized-state predicates, the production map, gate restore/replay and actual
mapped-state corruption remain pending. No gate restoration is authorized.
Completed M6/M7 and small synthesized-DUT M8/M9 acceptance is preserved.

`tools/checkpoint_formats/production_memory.py` reconstructs all 201 original
memory fragments and their semantic StateIDs from the exact iteration-69
architecture inputs. It independently checks the concrete models' interfaces,
single target-clock writes, asynchronous reads and absence of hidden state.
The proof binding includes exact original/normalized RTL, architecture, models,
candidate and semantic-manifest identities, original module bodies, port
expressions and all instance relationships. It does not bind a proven netlist
relation or export `asic_state_map.json`.

The restricted array grammar permits a universal one-step word projection:
an arbitrary valid address holds unless its write enable/address select it,
then receives the full data word. Jasper proves complete word-relation
preservation and every asynchronous read port, with unconstrained old words,
data, enable and addresses, no reset sequence and zero assumptions. Quantifying
the arbitrary address covers all **102,985,156 contents bits / 13,501,966 words**
in the 201 production RAMs. This is an audited grammar/projection adapter theorem,
not a whole-DUT equivalence run over instantiated arrays. The unchanged
surrounding pipeline/port registers still require composition with the emitted
netlist. Reads outside the selected valid word have independent unconstrained
values; depth-one out-of-range reads are never assigned a fabricated value or
claimed equivalent. Final composition must discharge their address/behavior
obligations too.

The final installed Jasper 2025.03 run proves all 17 real shapes: **41 assertions
and 1,522 covers**, including every bit's zero/one value, both memory endpoints,
enabled writes, disabled writes, other-address holds and each read port.
All **51 fresh negative proofs** (inverted enable, wrong write address, wrong
read address for each shape) produce actual counterexamples. The separate
auditor reconstructs the exact miters/scripts and checks input hashes, exact
property membership, precondition nonvacuity, raw individual engine messages,
zero assumptions and absence of blackboxing. Both complete audit passes reject
all **178 actual artifact mutations** each and pass two unchanged controls;
positive proof bytes are preserved. Changed/rehashed models, hidden state,
missing StateIDs/ports/properties, unproven/vacuous properties, altered reset,
forged gate authorization and missing raw engine/hash evidence reject.

Diagnostic logs remain under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m10-iteration70/`.
The final proof is `memory-proofs-final/invocation-ono1zw73/`; use
`memory-proofs-final/selection.json` and `memory-audit/selection.json` for the
selected complete proof and repeated independent audit. The preliminary
default-array experiment automatically blackboxed the largest arrays and
returned a counterexample. The no-blackboxing/automatic-RAM experiment was
interrupted during elaboration and is diagnostic only, not a passing check.
The preliminary projection run is also retained; the final run repeats all
68 CAD invocations with independent unconstrained unobserved read values.
An initial unit-test substring check accidentally matched a comment; its
diagnostic is retained and the complete corrected suite reran.

All 147 Python tests and complete M2/M3 VCS metasim/ordinary-RTL regressions
pass. The complete production synthesis/model-binding audit passes again.
The previous two full production RTL replays are independently waveform-audited
again without changing their immutable evidence; these remain original and
extracted-memory RTL replays, not gates. Exact commands, scope, full-path/hash
catalog and protected-input checks are in the iteration-70 `summary.json`,
`verification-commands.json` and `artifact-manifest.json`.

Next: compose these memory adapter theorems with a complete hierarchical
original/architecture/netlist state relation and boundary equivalence. Discharge
all 8,261 semantic register bits, all 7,256 physical register bits and the
1,005-bit count difference using independently proven relationships/constants/
irrelevance; do not infer a classification from counts or finite replay.
Bind the raw and selected netlists, concrete cell/memory models, exact synthesis
and proof inputs, semantic manifest, and complete physical inventory. Reject
any unproven semantic or physical state. After independent full-map audit,
run fresh gate VCS complete zero-edge readback/full metasim trace replay against
fresh ordinary RTL and actual first-divergence state corruption. FPGA hardware
and power data are not dependencies for this work; no required external
dependency is missing. Level-1 images remain independent. Plans/PDFs/conda files,
staging and history are preserved; no FPGA, process ASIC or power claim.

## Preserved iteration-69 synthesis and replay evidence

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
