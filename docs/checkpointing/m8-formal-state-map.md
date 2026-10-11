# M8 formal state mapping — iteration 66

Status: in progress. Implemented relational constant composition with native
merging, duplication, either polarity, indexed destination reordering and
unread state. Complete audited SRAM macro contents/pipeline/port initialization
remains unsupported. No required CAD dependency is missing. Artificial functional
cells; no process ASIC, physical FPGA or power validation.

Use `verify_formal_state_map.py --merge-registers --duplicate-registers
--constant-registers`, optionally adding `--profile inverted` and
`--reorder-registers`. The existing original constant fixture, Genus synthesis
and audited scalar-cell models are reused. Retiming remains queried false.
Relational candidate schema version 3 and build-bound map version 7 preserve
all semantic StateIDs, including eliminated unread and constant bits.

The complete initial relation includes constant values. Every candidate state
relationship and constant must preserve that relation across an edge, and every
output must agree under it. Separate `constant_state.py` proofs establish each
exact constant bit/value after one unconstrained target edge, with no input/reset
assumptions, covered antecedents, real raw engine results and complete source
hashes. The exporter requires exact agreement between relation candidates and
these independent predicates. Translation revalidates every artifact and rejects
C=0 or conflicting constant bits before returning any deposits. Unread original
state stays outside the relation, with zero/one covers and arbitrary evolution.

The independent auditor reconstructs the complete relation and constant binding,
checks exact scripts, hashes, assertion/cover statuses and individual engine
messages, including actual false predicates. A conditional constant update is a
control where complete relation induction/output equivalence PASS but independent
arbitrary-state predicates fail; relation PASS alone rejects missing predicates.
The verifier also checks all four conflicting constant bits, the horizon and
fresh ordinary RTL replay diverging before any restored edge at C=17.

All four new real Genus/Jasper/VCS profiles and independent audits pass in both
polarities, with/without reordering: 36 semantic bits, 28 physical bits initialized
and read back at zero edges, 32 relationships, 39 assertions/104 covers plus four
independent constant assertions/five covers. All 79 boundaries/237 outputs match
C=17..95, ending C=96. Every unread checkpoint bit is flipped with identical gate
deposits and matching fresh RTL replay. Nine fresh counterexample proofs per
profile, the conditional relation PASS control, the horizon/four conflicting
constant bits, six atomic loader failures, merged consistency, C=29 clone/shared
faults and a real contradictory-relation/vacuity rejection are all checked.

All 48 fresh CAD/VCS profiles/audits, all 117 Python tests and complete M2/M3
metasim/ordinary RTL regressions pass. M2 retains five cuts, all 22 words,
C=29 divergence and four loader failures. M3 retains 717 transport edges,
23 semantic advances, six captures, 242 boundary/five semantic replay samples and
eight invalid reads. Both polarities' supplemental shared-flop faults and fresh
changed-D proofs pass too.

The complete supplemental scope passed twice: 13 unchanged controls and 269
distinct actual artifact mutations reject per pass. The new constant composition
retains all prior relational/unread mutations and adds constant values, horizon,
predicate and relation mismatches, missing/bounded/vacuous proofs, constrained
scripts, weakened binding, false raw statuses/input identities, missing engine
messages, forged checkpoints/replay and unknown proof rows (53 per polarity).
All four formerly unsupported constant compositions now have complete positive
profiles. Eight additional fresh missing-predicate synthesis/equivalence builds
preserve prior proof hashes/inodes. No check was skipped or scope reduced.

`finalize-evidence.py` revalidates all 48 maps against current input bytes and
complete regression metrics. Commands, raw logs, proof/map artifacts and the
full-path/hash catalog are under `automations/checkpoint_loop/runs/m8-iteration66/`:
`verification-commands.json`, `finish-repeat-commands.json`, `summary.json`,
`matrix-results.json`, `artifact-manifest.json`. Initial pilot diagnostics are
preserved; the matrix selects the fresh final invocations for acceptance.

Next: complete audited SRAM macro contents and pipeline/port initialization with
real synthesis/proof/replay. Logical RAM still uses individual flip-flops.
Level-1 images remain independent of Level-2 state. Both plans/PDFs are read-only,
the dirty agent plan is preserved, and there are no conda edits, staging, commits,
resets, cleaning, FPGA claims or ASIC power claims.

## Historical iteration 65 evidence

Status: in progress. Relational unread-state composition now supports native
merging, duplication, either polarity and indexed destination reordering.
SRAM macro contents/pipeline/port initialization and relational constant
composition remain unsupported. No required CAD dependency is missing.
Artificial functional cells; no process ASIC, physical FPGA or power validation.

Use `verify_formal_state_map.py --merge-registers --duplicate-registers
--optimize-registers`, optionally adding `--profile inverted` and
`--reorder-registers`. Existing original RTL fixtures and successful Genus
netlists remain unchanged; retiming is queried false. The candidate schema is
version 2 and the resulting build-bound map is version 6. Every semantic StateID
remains represented, including four eliminated bits with empty gate destinations
and `kind=unread, proof_status=proven, report=relation_results`.

The complete miter relation constrains only retained original state and actual
gate storage. It never constrains eliminated original bits. Unbounded relation
preservation and equality of every output must therefore hold for their arbitrary
values and evolution; this proves irrelevance without an unread assumption or
inferred classification from global equivalence. All existing antecedent,
physical-bit and edge covers remain required, plus zero/one covers for each
omitted original bit. Complete input hashes, exact audited script/miter and
independent raw engine results still bind every assertion/cover. Missing,
observable, unknown, overlapping or unsupported eliminated state rejects.

All four new profiles and independent audits pass in both polarities,
with/without indexed reordering: 32 semantic bits, 28 initialized/read-back
physical bits at zero edges, 32 relationships, 35 assertions, 100 covers,
and 79 boundaries/237 outputs from C=17 through END C=96. All four unread
checkpoint bits are flipped; deposits remain identical and fresh ordinary RTL
replay matches. Each profile retains five previous counterexample proofs and
adds two: connecting omitted state directly to held_out fails output equivalence;
connecting it to the counter's next-state update fails relation preservation.
Both actual Jasper engine counterexamples reject in the proof adapter. The
independent audit also reconstructs both mutated originals and their miters.
Six atomic loader failures, clone/shared faults at C=29, merged checkpoint
consistency and the contradictory-relation/vacuity rejection remain covered.

All 44 fresh CAD/VCS profiles/audits, all 115 Python tests and full M2/M3 metasim
and ordinary RTL regressions pass. M2 retains five cuts, all 22 words, actual
C=29 divergence and four loader failures. M3 retains 717 transport edges,
23 semantic advances, six captures, 242 boundary/five semantic replay samples
and eight invalid reads. All previous shared-flop fault/changed-D checks pass.

The complete supplemental scope passed twice, with all 11 unchanged controls
passing and all 163 distinct actual artifact mutations rejecting on each pass.
The new unread-composition audit retains every prior relational mutation and
adds missing/misclassified unread entries, missing covers, false raw engine
status, wrong candidates, unchanged altered checkpoint, forged RTL replay,
and missing current/future counterexample engine reports (28 mutations per
polarity). Input hashes are rebound to exercise semantic/raw-proof checks.
Four previously rejected unread combinations now have full positive profiles;
the four constant combinations still reject before any tools launch.

Repeated missing-proof checks perform eight additional fresh Genus/Formality
builds across both supplemental passes; first-pass proof hashes/inodes remain
unchanged. Previous evidence is preserved. `finalize-evidence.py` revalidates
all 44 maps against actual current input bytes and complete regression metrics.
Commands, raw logs, proof/map artifacts and full-path/hash catalog are under
`automations/checkpoint_loop/runs/m8-iteration65/`: `verification-commands.json`,
`finish-repeat-commands.json`, `finish-repeat-summary.json`, `summary.json`,
`matrix-results.json` and `artifact-manifest.json`. The initial pilot artifacts
remain too; the matrix selects the fresh final invocations for acceptance.

Next: complete audited SRAM macro contents/pipeline/port initialization, then
relational constant predicate/horizon composition. Logical RAM still uses DFFs.
Level-1 simulator images remain independent of Level-2 semantic state. Plans,
PDFs and dirty conda files are not edited or staged; no commit/reset/clean.

## Historical iteration 64 evidence

Status: in progress. Fixed the repeat verification failure reported by the loop.
SRAM macro initialization and relational unread/constant composition remain
unsupported. No required CAD dependency is missing. Artificial functional cells;
no process ASIC, physical FPGA or power validation.

The previous failure occurred in iteration 63's diagnostic missing-proof script:
its fixed synthesis directory already existed on verification replay. The new
`tools/checkpoint_formats/tests/verify_formal_missing_proof.py` allocates a fresh
invocation under `--out` on every call, records all CAD commands and input hashes,
and keeps every original semantic bit. Both direct and inverted Genus/Formality
builds must pass global equivalence and then reject export with exactly
`unproven or unmappable semantic state` when four optimized constant bits have no
Jasper state predicates. The complete inventory, synthesis/proof identities,
24 proven physical bits and four explicitly unread bits still validate first.
No exporter, loader, synthesis or proof adapter was changed.

Use `python -m tools.checkpoint_formats.tests.verify_formal_missing_proof`
with `--out automations/checkpoint_loop/runs/formal-missing-proof` after sourcing Chipyard
`env.sh`, FireSim `env.sh`, then `automations/checkpoint_loop/vcs-env.sh` LAST.
The repeat check under `runs/m8-iteration64/verify-repeat-missing-proof.py`
calls this module twice in the same output directory and verifies independent
invocations and unchanged hashes, sizes and inodes of all first-call files.
Its initial real run passed four fresh synthesis/proof builds and preserved
56 files. Previous iteration's evidence and diagnostic scripts are untouched.

All 40 fresh CAD/VCS profiles and independent audits pass, including complete
Jasper induction for merging/duplication. All 111 Python tests and full M2/M3
metasim/ordinary RTL regressions pass. M2 retains five cuts, all 22 words, actual
C=29 divergence and four loader failures. M3 retains 717 transport edges,
23 semantic advances, six captures, 242 boundary/five semantic replay samples
and eight invalid reads. All shared-flop fault/changed-D audits pass too.

`runs/m8-iteration64/verify-finish-repeat.py` executes the entire supplemental
scope twice, including nine isolated controls, 107 distinct actual artifact
mutations, individual negative-engine audits and eight unsupported compositions.
Both passes succeeded. Each pass runs the missing-proof module twice: eight
additional fresh synthesis/equivalence builds in total. The second supplemental
pass preserved both first-pass proof invocations' hashes and inodes. No previous
proof requirement was relaxed, and no scope was reduced or check skipped.
`finalize-evidence.py` validates every map against current input bytes, actual
regression metrics, mutation results, repeat results and protected inputs.

Commands, raw logs, proof artifacts and current maps are under
`automations/checkpoint_loop/runs/m8-iteration64/`: `verification-commands.json`,
`finish-repeat-commands.json`, `finish-repeat-summary.json`, `summary.json`,
`matrix-results.json` and the full-path/hash `artifact-manifest.json`.
The unchanged remaining work is audited SRAM macro contents and pipeline/port
initialization, followed by relational unread/constant composition. Current
logical RAM uses flip-flops. Unsupported state still rejects explicitly;
Level-1 simulator images remain independent of Level-2 semantic state.

## Historical iteration 63 evidence

Status: in progress. Simultaneous native merging/duplication now has complete
Jasper induction, version-5 mapping and gate replay in both polarities with
reordering. All 40 CAD/VCS profiles/audits, 111 Python tests and full M2/M3
regressions pass. SRAM macro initialization and relational unread/constant
composition remain unsupported. No required CAD tool/library/license is missing.
Artificial functional cells; no process ASIC, physical FPGA or power validation.

Use `verify_formal_state_map.py --merge-registers --duplicate-registers`, with
optional `--profile inverted` and `--reorder-registers`. The original merging DUT
and successful Genus netlist remain unchanged. Native cloning and renaming run
in Genus, with retiming queried false. `--optimize-registers`/`--constant-registers`
with this combination reject before tools launch; existing separate profiles
retain their Formality/Jasper adapters.

`relational_state.py` generates an audited miter of both complete designs.
Jasper runs with `reset -none` and unconstrained input/state. Each candidate
relationship has an unbounded `relation |=> relationship` assertion; all outputs
have `relation |-> output_equality` assertions. The initial-state condition is
explicit: the complete candidate relation must hold when the netlist is loaded.
The loader enforces all merged sources' consistency after proven XOR transforms
and initializes every physical bit. Induction then guarantees continuation under
arbitrary subsequent inputs, including resets. No independent arbitrary original
and gate states are claimed equivalent. Candidates alone are never proof.

Every assertion's antecedent must be covered; a two-sample relation cover and
zero/one covers for every physical bit prevent vacuous acceptance. Every original
and physical bit must be represented. Exact input/output directions and widths
are mandatory for this fixed flat interface, preventing unnoticed output
truncation. The script and generated miter must equal the audited implementation;
raw engine messages, machine statuses, raw input markers and before/after hashes
must agree. Bounded, missing, stale, constrained or vacuous evidence rejects.

All four new profiles prove 32 relationships with 35 assertions and 92 covers:
four shared held flops retain eight original sources, four counter bits each map
to two physical copies, and all 16 logical RAM bits map to DFF storage. There are
28 semantic bits and 28 physical bits. All initialize/read back at zero edges
from C=17, then match 79 boundaries / 237 outputs through END C=96 against clean
RTL and uninterrupted gate execution. Inverted profiles initialize all 28 bits
with XOR=1. Every new profile has five real false-candidate/changed-D proofs with
counterexamples and a contradictory relation whose covers are proven unreachable
and whose export rejects. Both original aliases fail changed shared D; changed
clone D fails that copy's relation. Clone/shared storage faults first differ at
C=29 after 12 restored edges. All six loader failures preserve storage/time and
continuation. Conflicting independently checksummed merged checkpoints and
missing alias/copy evidence reject before deposits/export.

All 40 profiles and independent audits pass, including all 36 previous profiles.
All 111 Python tests and full M2/M3 metasim/ordinary RTL VCS regressions pass.
M2 retains five cuts/all 22 words/actual C=29 divergence/four loader failures.
M3 retains 717 transport edges, 23 semantic advances, six captures, 242 boundary
and five semantic replay samples, and eight invalid reads. Old supplemental
shared-flop faults and fresh changed-D proofs pass in both polarities too.

Nine isolated independent controls pass and all 107 actual mutations reject:
69 previous/combined mutations and 19 new rehashed mutations in each polarity.
New audits check exact miter/script/interface, individual positive and negative
raw engine results, all inventories, container checksums and every replay output.
Two fresh equivalence-only constant builds reject absent predicates despite
PASS. Eight relational unread/constant combinations reject before tool launch.
`finalize-evidence.py` revalidates all 40 maps against actual current input bytes,
all regression metrics and protected inputs. Exact argv/exit codes, profile paths,
summary and full-path/hash catalog are under `runs/m8-iteration63/`:
`verification-commands.json`, `finish-commands.json`, `supplemental-commands.json`,
`summary.json`, `matrix-results.json`, `artifact-manifest.json`. Inner commands,
raw reports/logs/checkpoint containers remain in each invocation directory.

Proposed plan correction, recorded only here: allow complete Jasper relational
induction as an alternative to passing compare-point extraction when one-to-many
Formality matching cannot represent simultaneous merging/duplication. Preserve
explicit initial relation, complete inventories and proof-mode metadata. The
two partial Formality attempts failed; their results were rejected. The initial
Jasper reserved-keyword label failed; corrected retry passed. Raw logs are under
`runs/m8-iteration63/dual-proof-probe/`. Root-paper extraction hashes match the
unchanged PDFs; relevant matching/loading/retiming and replay sections were read.
Protected plans/PDFs and initial staging remain unchanged.

Next: complete hash-bound SRAM macro initialization, including contents and
pipeline/port state, with synthesis/proof/replay. Current logical RAMs remain
flip-flops and do not establish macro acceptance. Relational unread/constant
composition is also unsupported. Level 1 remains independent. Every VCS shell
sources both project environments then `vcs-env.sh` LAST, retaining Y-2026.03-SP1,
-full64 and GCC/G++ 13; reused metasim builds use -Mupdate. No plan/PDF/conda edits,
staging, commits, resets, cleaning or FPGA/power claims.

## Historical iteration 62 evidence

Status: in progress. Native merging now composes with unread optimization and
observable constants in real synthesized/proven/replayed DUTs. SRAM macro
initialization and combined merging/duplication remain unsupported. No required
CAD tool, library or license is missing. Artificial functional cells; no
foundry ASIC, physical FPGA or power validation.

`verify_formal_state_map.py --merge-registers --optimize-registers` or
`--merge-registers --constant-registers` selects the corresponding original
fixture under `tests/fixtures/formal/merged/`. Direct/inverted polarity and
`--reorder-registers` are supported. Genus natively merges and eliminates state;
its successful netlist is never rewritten, and retiming is queried false.
Formality gate-reference orientation proves both original held aliases and all
outputs. Unread points belong to original RTL on the implementation side; the
machine rows, raw report labels/counts and complete original inventory agree.
Constants retain independent unconstrained Jasper predicates, checkpoint value
checks and minimum target cycle 1. No exporter schema/proof requirements were
relaxed; the prior adapter already supports this composition.

All eight new combined profiles pass. Version-3 maps retain 32 semantic bits;
version-4 maps retain 36. All 24 physical bits deposit/read back at zero edges
from pre-edge C=17. Four shared flops retain eight semantic sources. Every
profile matches 79 boundaries / 237 outputs against the clean RTL oracle and
uninterrupted gate execution through END C=96. All four logical RAM words are
synthesized flip-flops; they do not establish SRAM macro acceptance.

Unread bits do not excuse merged source conflicts, wrong constant values or
pre-horizon checkpoints. Every alias and physical storage relation still needs
proof. Wrong proof side, missing classification, swapped polarity/permutation,
wrong aliases and changed D fail. Altering all unread bits replays clean RTL
successfully; connecting them to an output fails real equivalence. False
constant predicates still yield real arbitrary-initial-state counterexamples.
Actual shared-flop faults first differ at C=29 after 12 restored edges; fresh
changed-D proofs fail both semantic aliases in both polarities.

All 36 CAD/VCS profiles and independent audits pass, including all 28 prior
profiles. All 105 Python tests and full M2/M3 metasim/ordinary RTL regressions
pass. M2 retains five cuts, all 22 words, actual C=29 divergence and four loader
rejections. M3 retains 717 transport edges, 23 semantic advances, six captures,
242 boundary/five semantic replay samples and eight invalid reads. The old
shared-storage fault checks and both new combined constant fault checks pass.

Seven isolated audit controls pass and all 69 actual mutations reject. The
new combined unread audit rebinds mutated raw-report/evidence input hashes, so
semantic checks must reject beyond stale identity. Two fresh equivalence-only
constant builds still reject missing predicates. All eight selected unsupported
merging/duplication combinations reject before tool launch/build artifacts.

Exact argv/exit codes, profile paths, summary and full-path/hash catalog:
`runs/m8-iteration62/verification-commands.json`, `matrix-results.json`,
`summary.json`, `artifact-manifest.json`. Every invocation retains inner tool
commands and raw reports/logs/containers. `finalize-evidence.py` revalidates all
36 maps against their current actual input bytes and checks all regression
metrics. Initial diagnostic audit clones omitted Tcl/Verilog files; corrected
complete clones and all final controls pass. Failures/retries remain recorded.

Read both read-only plans' relevant formal/replay sections, progress/previous
verification and hash-verified root-paper extracts before edits. `pdftotext` is
unavailable; preserved extraction input hashes match the unchanged root PDFs.
Protected input hashes and staging remain unchanged. Level 1 stays independent.
Every VCS shell sources both project environments then `vcs-env.sh` LAST,
retaining Y-2026.03-SP1, -full64 and GCC/G++ 13; reused metasim builds use -Mupdate.
Plans/PDFs/conda files and git history are preserved. Existing plan numbering
and symmetric proof-orientation proposals remain only in checkpointing docs.

Next: complete hash-bound SRAM macro initialization, including contents and
pipeline/port state, with real synthesis/proof/replay. Combined merging and
duplication requires a separate proof adapter. Combined merging/optimization
fixture support is complete for these audited flat DUTs.

## Historical iteration 61 evidence

Status: in progress. Observable constant propagation now has independent Jasper
predicate proofs, complete StateID preservation and fresh gate initialization/
replay evidence. SRAM macro initialization remains. No external dependency
blocks this increment. Artificial functional cells; no foundry ASIC, FPGA or
power validation.

Read both plans' relevant formal/state-replay sections, progress/previous
verification and both papers' preserved matching/replay extracts before edits.
Fresh extracts from the unchanged root PDFs are also retained. Plan/PDF hashes
and initial staging are under `automations/checkpoint_loop/runs/m8-iteration61/`;
the dirty agent plan remains read-only. Plan numbering and symmetric-orientation
proposals remain solely in these checkpointing documents.

`verify_formal_state_map.py --constant-registers` selects
`tests/fixtures/formal/constants/dut.v` and includes both its four unread bits
and four observable constant bits in the original semantic checkpoint. Genus
natively removes both sets; its successful netlist is never rewritten. Ordinary
Formality equivalence and complete original/gate inventories still apply, with
retiming queried false, every required gate storage relationship/output passing,
no black boxes, and unread-state evidence cross-checked separately.

The new `constant_state.py` adapter binds a separate Jasper proof to the exact
original RTL, candidate bit specification, generated SVA binding and audited
runner script. Each original register bit is asserted as `1'b1 |=> bit == value`,
with `reset -none` and arbitrary original initial state. The antecedent covers
and an explicit two-sample edge cover must all be covered. Every assertion must
be unbounded `proven`; missing, bounded, vacuous, constrained, stale, contradictory
or unsupported predicates reject. Machine results, raw tool status markers and
independent engine result messages must agree. Original `initial`, assumptions
and assertion constructs are unsupported by this adapter rather than silently
introducing constraints. Candidate names/values alone never prove a constant.

Version-4 maps retain every semantic StateID and bit. Constant entries have no
gate destination but carry the proven value, property and minimum target cycle
1. Before returning any gate deposit list, translation requires C >= 1 and each
checkpoint constant bit to equal its proven value. Target time never advances
while loading. Prior version-1/2/3 maps remain supported; extra/unproven physical
storage and SRAM macros without an audited storage interface still reject.

All eight new constant profiles cover direct/inverted storage, with/without
indexed scalar reordering and native duplication. Each retains 32 semantic bits:
24 mapped originals, four unread bits and four independently proved constants.
All 24/28 physical bits deposit and read back at zero edges from pre-edge C=17;
79 boundaries / 237 outputs match the clean RTL oracle and uninterrupted gate
execution through END C=96. All four logical RAM words remain flip-flops.

All four independently checksummed conflicting constant checkpoints and a C=0
checkpoint reject before deposits. Fresh ordinary RTL replay of a conflicting
observable constant first differs on held_out at C=17 before any replay edge.
Wrong-value and conditional-update predicates yield actual Jasper counterexamples
from arbitrary initial state. Missing predicate evidence still rejects despite
fresh equivalence PASS in both polarities. Unread-state arbitrary-value replay,
actual storage faults, fresh changed-D, polarity and permutation failures,
complete atomic loader faults and missing duplicate/merge proofs are preserved.

All 28 real CAD/VCS profiles and independent audits pass, including all 20 prior
profiles. All 103 Python tests and complete M2/M3 metasim/ordinary-RTL regressions
pass. M2 retains five cuts, all 22 words, actual C=29 divergence and four loader
rejections; M3 retains 717 transport edges, 23 semantic advances, six captures,
242 boundary/five semantic replay samples and eight invalid client reads.
Supplemental actual shared-flop/storage faults and changed-D proofs/audits pass
in both polarities. Four unchanged isolated audit controls pass and all 37
actual artifact mutations reject: 12 constant, nine unread, eight merging and
eight duplication/reordering. Constant input hashes are rebound in the mutation
checks so semantic/raw-proof validation must reject beyond a stale-hash check.

Exact argv/exit codes, profile paths, summary and full-path/hash catalog:
`runs/m8-iteration61/verification-commands.json`, `matrix-results.json`,
`summary.json` and `artifact-manifest.json`. Each invocation retains inner
`commands.json`. Initial Jasper launch probes diagnosed the OS switch and mutually
exclusive GUI/batch options. The first integrated run failed because Jasper's
batch interpreter leaves Tcl `info script` empty; explicit before/after-hashed
script path retry passed. These diagnostic failures/logs remain recorded.
The initial integrated driver log was reused by the final matrix; its original raw Jasper failure log and
recorded return code remain in `constants-direct/invocation-k9s772pe/`.

Next: add a complete hash-bound SRAM model initialization adapter, including
logical contents and pipeline/port state, and prove/replay it with a real
synthesized macro fixture. All currently validated RAM words are synthesized
flip-flops. Combined merging/duplication requires a separate proof adapter;
combined merging/optimization fixtures also remain unsupported. Level 1 stays
independent. Every VCS shell sources both project environments then `vcs-env.sh`
LAST, retaining Y-2026.03-SP1, -full64 and GCC/G++ 13. Plans/PDFs/conda files,
staging and git history are preserved.

## Historical iteration 60 evidence

Status: in progress. Explicit unused-state optimization now has real Genus,
Formality and fresh ordinary-RTL/gate VCS evidence. Constant propagation and
SRAM macro initialization remain. No external dependency blocks this increment.

Read both plans' formal correspondence sections, progress/previous verification,
and both papers' preserved matching/replay extracts before editing. Plan/PDF
hashes and initial staging are under `automations/checkpoint_loop/runs/m8-iteration60/`.
The dirty agent plan remains read-only. Prior numbering and symmetric-orientation
plan proposals remain solely in these checkpointing documents.

`verify_formal_state_map.py --optimize-registers` uses the new original fixture
`tools/checkpoint_formats/tests/fixtures/formal/optimized/dut.v`. Its four-bit
`unused` register updates dynamically from its own state and input data but has
no fanout to required outputs or mapped state. Genus removes it during ordinary
synthesis without rewriting the successful netlist. The independent Level-2
manifest/checkpoint still includes every original StateID and bit.

The proof adapter queries `report_unmatched_points -point_type reg -status unread`
after equivalence verification and retains both the human report and explicit
machine classifications. Evidence schema `formality-state-v3` records orientation
and every original/gate register inventory. The exporter cross-checks the exact
unread point set, report filter, side, and count before permitting empty gate
destinations. Version-3 maps bind this report along with all prior synthesis,
formal, configuration, model and netlist inputs. Version-1/2 proofs remain
supported. Every physical bit still requires a passing state relationship and
initialization; extra gate state, contradictory passing/unread classifications,
missing evidence and unknown memory models reject explicitly.

No constant or reset assumption is introduced. `unused` values may vary because
Formality explicitly classifies these original DFFs as unread. Changing all four
checkpoint bits produces identical gate deposits. A fresh ordinary RTL process
restores that altered checkpoint and checks all 79 recorded output boundaries.
Connecting the actual original unused register to `held_out` makes fresh formal
verification fail and removes its unread classification. Isolated missing,
constant-labelled and live-point classifications reject before map publication.

All eight new optimized profiles (both polarities, with/without duplication and
indexed scalar reordering) prove 24/28 required state relationships and all 12
outputs, plus explicit classification of four unread original bits. All 28
semantic bits remain represented. Fresh gate VCS deposits/readbacks every one of
24/28 physical bits at zero edges from pre-edge C=17, matches 79 boundaries / 237
outputs, and ends at C=96. Uninterrupted gate simulation agrees with the same
ordinary RTL oracle. Every profile covers all four logical RAM words, retains
five/six atomic loader failures and an actual storage fault at C=29 after 12
restored edges, and rejects changed D, wrong polarity and (when reordered)
wrong permutation. Duplicated storage still requires each copy's proof.

All 20 real CAD/VCS profiles and independent audits pass, including all 12 prior
profiles. All 97 Python tests and complete M2/M3 metasim/ordinary-RTL regressions
pass. M2 retains five cuts, all 22 words, real C=29 divergence and four loader
rejections. M3 retains 717 transport edges, 23 semantic advances, six captures,
242 boundary/five semantic replay samples and eight invalid client reads.
Supplemental actual shared-flop/storage and changed-D proofs/audits pass in both
polarities. Three isolated unchanged audit controls pass and all 25 actual
artifact mutations reject (nine unread-state, eight merging, eight duplication/
reordering). Both fresh constant-propagation builds pass equivalence and still
reject with `unproven or unmappable semantic state` for four unclassified bits.

Exact commands, exit codes, profile directories, summary and the full-path/hash
catalog are `runs/m8-iteration60/verification-commands.json`, `matrix-results.json`,
`summary.json` and `artifact-manifest.json`. Each invocation retains its inner
`commands.json`. A supplemental launcher initially omitted root `PYTHONPATH`
and failed before CAD ran; its log/failed command are preserved. The corrected
complete checks pass, with recovery recorded in the command catalog and summary.
No test scope was reduced. Logs stay outside tracked documentation.

Next: obtain independent point/predicate evidence for constant propagation,
then add a complete hash-bound SRAM model initialization adapter, including
logical contents and pipeline/port state. Initial constant probes synthesized
all four constant bits away and passed equivalence, but this Formality adapter's
constant/unread/not-compared reports did not classify them. Fresh direct/inverted
builds with the current adapter confirm that map export rejects all four missing
constant relationships despite equivalence PASS. They remain unsupported;
global PASS is insufficient. Preserved original constant probe RTL (hash matching
the raw proof log): `runs/m8-iteration60/constant-probe-original.v`; diagnostics:
`probe/`, `probe2/`, `constant-rejection-direct/` and `constant-rejection-inverted/`.
`constant-rejection-summary.json` records both fresh rejected builds. A separate
invariant proof or a more precise tool export
is needed, including checkpoint-value validation for any observable constants.

Combined optimization/merging fixtures and combined merging/duplication proof
remain explicitly unsupported. All validated RAM words remain synthesized
flip-flops. The test cells have artificial functional/timing data; no foundry
ASIC, physical FPGA, gate-activity or power validation is claimed. Level 1 stays
independent. Every VCS shell sources both project environments and `vcs-env.sh`
LAST, retaining Y-2026.03-SP1, `-full64` and GCC/G++ 13. Plans/PDFs/conda files,
staging and git history are preserved.

## Historical iteration 59 evidence

Status: in progress. Native register merging now has real synthesis, formal
proof and gate restore/replay evidence with both polarities and with/without
indexed scalar reordering. Constants/irrelevance and SRAM macro initialization
remain; no external dependency blocks the supported flow.

Read both plans' relevant formal sections, progress/previous verification and
the two papers' preserved matching/replay extracts before edits. Starting plan/
PDF hashes and staging are under `automations/checkpoint_loop/runs/m8-iteration59/`.
Preserve the dirty agent plan. The loop M8 versus plan M9 numbering correction
remains only in checkpointing docs.

`verify_formal_state_map.py --merge-registers` uses the new original RTL fixture
`tools/checkpoint_formats/tests/fixtures/formal/merged/dut.v`. `held` and
`held_copy` have identical enabled updates and synchronous reset; both remain
independent semantic StateIDs in the 28-bit manifest. Genus natively merges
their four bit pairs into four shared `held_copy_reg` flops. No successful
emitted netlist is rewritten. The complete RTL, library, script, configuration,
netlist, retiming=false query and proof identities remain hash-bound.

Formality P-2019.03-SP2 allows one reference point to multiple implementation
points, but prohibits multiple reference points to one implementation point.
The merging configuration therefore reverses the symmetric equivalence proof:
the gate netlist is the tool reference and the exact original RTL is its
implementation. Each shared flop matches both original RTL aliases; every alias,
other state point and all 12 output points must pass. No reset/input assumptions
or black boxes are introduced. Diagnostic failed forward-cutpoint attempts are
preserved under `runs/m8-iteration59/probe*/`.

Proposed plan correction: permit this explicitly recorded symmetric orientation
for merging in the agent Phase 10 procedure, which currently prescribes original
RTL as the tool reference. Equivalence is symmetric; complete state/output proof
and checkpoint consistency remain required. This proposal changes no plan file.

Evidence schema `formality-state-v2` records `ORIENTATION gate-reference` and
retains actual raw tool inventories/passing relationships. The exporter
normalizes them to its canonical semantic `r:` and gate `i:` paths; these
normalized paths in `asic_state_map.json` differ from raw tool container names.
The resulting version-2 map preserves every semantic bit, even when multiple
StateIDs share physical storage. Version-1 forward proofs remain supported.
Missing aliases, missing storage, contradictory polarity, stale identities and
unsupported optimized state still reject explicitly.

`gate_deposits` applies every proven XOR transformation, requires all sources
of shared storage to agree, and emits exactly one deposit per physical bit.
A conflicting but structurally valid Level-2 checkpoint rejects before a deposit
list is returned. VPI retains its complete handle prevalidation, atomic rejection
and zero-edge readback. The reverse proof does not authorize arbitrary initial
alias values; checkpoint consistency enforces the proven state relation.

All four merging profiles (direct/inverted, ordered/reordered) prove 28 state
relationships and 12 outputs. They cover every semantic bit and all 24 physical
bits, including four shared flops and all four logical RAM words. Fresh ordinary
gate VCS restores from pre-edge C=17 with complete zero-edge readback and matches
79 boundaries / 237 outputs through END C=96. Uninterrupted gate execution agrees
with the ordinary original-RTL oracle. Inverted profiles have XOR=1 for all 24
physical storage bits. These RAM words are flip-flops, not SRAM macros.

Each profile retains five atomic loader rejections, actual counter fault,
changed-D formal failure, wrong-polarity failure and, when reordered, wrong
permutation/formal and swapped-map rejections. Merging adds a valid conflicting
checkpoint, missing alias proof despite global PASS, and a wrong-alias fresh
formal failure. Additional actual shared-flop faults in both reordered polarities
first differ on `held_out` at C=29 after 12 restored edges. Changed shared D fails
both original alias compare points. Independent supplemental audits check actual
netlist changes, storage paths, complete readback, exact healthy prefixes and raw
failed reports. An unchanged isolated merging audit control passes; eight actual
artifact mutations reject.

All 12 real CAD/VCS profiles and independent audits pass, including every one
of the eight previous profiles. Both unchanged isolated controls pass and all
16 actual audit mutations reject. All 94 Python tests and full M2/M3 metasim/
ordinary-RTL VCS regressions pass. M2 retains five cuts, all 22 words, real C=29
divergence and four loader failures. M3 checks 717 transport edges, 23 semantic
advances, six captures, 242 boundary/five semantic replay samples and eight
invalid client reads. Exact argv arrays and complete profile locations are
recorded in `runs/m8-iteration59/summary.json`, `verification-commands.json` and
`matrix-results.json`. Every CAD/VCS invocation
retains its inner `commands.json`; `artifact-manifest.json` catalogs full paths
and hashes. Every VCS shell sources Chipyard env, FireSim env, then `vcs-env.sh`
LAST, retaining Y-2026.03-SP1 `-full64` and GCC/G++ 13. Reused metasim Make builds
regenerate cached VCS C Makefiles with `-Mupdate`.

Next: independently prove constants/irrelevance and implement complete hash-bound
SRAM macro initialization, including memory and any pipeline/port state.
Combined `--merge-registers --duplicate-registers` rejects explicitly: this
Formality orientation alone cannot express both transformations in one proof.
A future multi-proof adapter must preserve complete coverage and shared-source
consistency; no combined-profile acceptance is claimed. Scalar reordering remains
native name/index permutation, not packed multibit-cell ordering or placement.
Artificial functional cells establish no foundry ASIC, FPGA, gate-activity or
power acceptance. Level 1 remains independent. No plan/PDF/conda edits, staging,
commits, resets or cleaning.

## Historical iteration 58 evidence

Status: in progress. The new increment proves and replays a nonidentity
permutation of indexed scalar gate destinations, combined with duplication
and both storage polarities. Merging, constants/irrelevance and SRAM macro
initialization remain. No external dependency blocks the supported flow.

Read the agent Phase 10/M9 and human formal correspondence/retiming sections,
progress, previous verification and both papers' preserved matching/replay
extracts before edits. Plan/PDF hashes and starting staging are under
`automations/checkpoint_loop/runs/m8-iteration58/`. Preserve the dirty agent
plan. The loop M8 versus plan M9 numbering correction remains only here.

`verify_formal_state_map.py --reorder-registers` invokes Genus' native
`rename_obj` on mapped counter flops after ordinary synthesis and optional
native duplication. Original counter bits 0,1,2,3 occupy scalar destination
slots 2,0,3,1; D/Q connectivity is retained. The emitted successful netlist is
never rewritten. This exercises name/index permutation of scalar storage,
not packed multibit-cell bit ordering, automatic physical placement or retiming.
The actual netlist, complete inventory, native rename log, retiming=false and
all input identities are bound to the build.

The two new hash-bound `reordered/config.tcl` files supply candidate name
relations and polarity. Formality must prove each state relationship and all
outputs without reset/input assumptions or black boxes. Only passing compare
points enter the StateID map. The exporter/translator remains independent of
the candidate permutation. Unknown or unproven state still rejects explicitly.

All four reordered profiles (direct/inverted, with/without duplication) prove
complete correspondence for 24 semantic bits and 24/28 physical bits, including
all four logical RAM words. These memories are synthesized flip-flops.
Fresh gate VCS deposits/readbacks every bit at zero edges from pre-edge C=17
and matches 79 boundaries / 237 output values through END C=96. Uninterrupted
gate execution agrees with the same ordinary-RTL oracle. The inverted profiles
have XOR=1 at every storage destination. Five/six loader failures preserve all
bits and continuation; a real counter-storage fault first differs at C=29 after
12 restored edges.

Fresh proofs of a changed D input, wrong polarity and the plausible guessed
same-index permutation each fail and reject export. Swapping counter
destinations in the exported map rejects before checkpoint translation.
Omitting a duplicate's passing relation still rejects despite global PASS.
Independent audits cross-check native renames, human/machine passing relations,
complete inventories, all build identities, deposits and trace/log boundaries.
An unmodified isolated control passes; eight isolated mutations reject,
including swapped bit destinations and a guessed-order summary.

All eight real CAD/VCS profiles and independent audits pass: the four new
reordered combinations and four unchanged direct/inverted/duplicated
regressions. All 92 Python tests and complete M2/M3 VCS regressions pass.
M2 retains five cuts, 22 state words, actual C=29 divergence and four loader
rejections. M3 checks 717 transport edges, 23 semantic advances, six complete
captures, 242 boundary/five semantic replay samples and eight invalid reads.

Final profile locations, all exact argv arrays, summaries and a full-path
artifact catalog are under `automations/checkpoint_loop/runs/m8-iteration58/`:
`matrix-results.json`, `verification-commands.json`, `summary.json` and
`artifact-manifest.json`. Each invocation retains its inner `commands.json`.
Every VCS shell sources Chipyard env, FireSim env, then `vcs-env.sh` LAST,
retaining VCS Y-2026.03-SP1 `-full64` and GCC/G++ 13. Reused metasim builds
regenerate cached VCS C Makefiles with `-Mupdate`.

Next: extend export to independently proven merging and constants/irrelevance,
then add a hash-bound SRAM macro adapter covering its complete array and any
pipeline/port state with zero-edge initialization. Do not infer optimized-away
state from global equivalence PASS. Artificial functional test cells establish
no process ASIC, FPGA, gate-activity or power acceptance. Level 1 remains
independent. No plan/PDF/conda edits, staging, commits, resets or cleaning.

## Historical iteration 57 evidence

Status: in progress. Real Genus/Formality/VCS evidence now validates register
duplication with both direct and inverted polarity, alongside the existing
24-bit register/RAM correspondence. Real bit reordering, merging, constant
propagation/irrelevance and SRAM macro initialization still require proof and
replay evidence. No missing external dependency blocks this increment.

The read-only plans call this agent Phase 10/M9; the loop calls it M8. Preserve
that numbering correction only here. Read the relevant sections, progress,
previous verification and both papers' preserved matching/replay extracts.
Plan/PDF hashes and starting staging are under `runs/m8-iteration57/`; preserve
the existing dirty agent plan. No assumptions about reset or initial state are
added to the formal flow. Retiming remains disabled.

Changes and verified evidence:

- `verify_formal_state_map.py --duplicate-registers` invokes Genus' native
  `duplicate_register -num_copies 2` after ordinary mapping/optimization. Four
  original counter flops become eight, with loads split between the copies.
  Successful emitted netlists are never rewritten. The native tool log, queried
  retiming=false, exact script/library/RTL identities and output netlist hash
  remain bound to each map.
- Formality groups inventory-derived name candidates, including the native
  `_SYNTHESIS_SEQ_DUP_0` suffix, into one-to-many user matches. Each copy is
  individually verified against its reference bit. Only *passing* relationships
  enter the map. There are 40 passing points: 28 physical state and 12 outputs.
  The inverted duplicated profile proves all 28 storage values have XOR=1.
- The flat gate inventory accepts escaped register names with suffixes after
  bracketed indices. Unsupported names/cells, hidden state, unmatched state,
  merging/optimized reference bits and retiming still reject explicitly.
- Both duplicated profiles deposit/read back all 28 bits at zero edges from
  pre-edge C=17. Restored and uninterrupted gate runs match all 79 boundaries /
  237 outputs through C=95, END C=96. All four logical RAM words participate;
  these are synthesized flip-flops, not SRAM macro validation.
- Each duplicated profile retains all five loader failures and adds omission of
  exactly one physical copy. Every rejection preserves all 28 bits at zero edges
  and matches continuation. An actual duplicate storage fault first differs at
  C=29 after 12 restored edges. A changed duplicate D input and wrong polarity
  each fail fresh formal proof/export. Omitting one copy's passing relationship
  rejects export despite the retained global equivalence PASS.
- The independent audit reads every implementation row in human one-to-many
  passing reports; it checks complete reference/gate inventories, raw machine
  relationships, netlist/model/configuration identities, all deposits and trace
  boundaries, and actual clone faults. Six isolated actual artifact mutations
  reject, including a missing human copy row, exchanged copy sources and an
  omitted copy deposit.

Final invocations (relative to Chipyard):

- Duplicated direct: `automations/checkpoint_loop/runs/m8-iteration57/duplicated-direct/invocation-yj3u05lt/`
- Duplicated inverted: `automations/checkpoint_loop/runs/m8-iteration57/duplicated-inverted/invocation-s_x4ijml/`
- Direct regression: `automations/checkpoint_loop/runs/m8-iteration57/direct-regression/invocation-kpprxnrf/`
- Inverted regression: `automations/checkpoint_loop/runs/m8-iteration57/inverted-regression/invocation-m3f10yby/`

All four real CAD/VCS profiles and independent audits pass. All 92 Python tests
and complete M2/M3 metasim/ordinary-RTL VCS regressions pass. M2 retains five
cuts, all 22 state words, actual C=29 divergence and four loader failures. M3
checks 717 transport edges, 23 semantic advances, six complete captures, 242
boundary/five semantic replay samples and eight invalid client reads. Exact
argv, summary and full-path catalog are under `runs/m8-iteration57/`; inner CAD/simulator
commands are in each invocation's `commands.json`. Every VCS shell sources
Chipyard env, FireSim env, then `vcs-env.sh` LAST, retaining system GCC/G++ 13
and VCS Y-2026.03-SP1 `-full64`; reused M2 Make uses `VCS_FLAGS=-Mupdate`.

Next: obtain real reordering and merging/constants/irrelevance proof cases,
then implement an audited SRAM macro adapter covering its complete array and
pipeline/port state with zero-edge initialization. Unit-only transforms and
an equivalence PASS without complete state correspondence do not establish
acceptance. These artificial test libraries validate functional synthesis,
not a foundry ASIC or power result. Level 1 remains independent. No plan/PDF/
conda edits, staging, commit/reset/clean or physical FPGA validation.

## Historical iteration 56 evidence

Status: in progress. Real Genus/Formality/VCS evidence now validates both direct
and inverted state correspondence for the complete 24-bit register/RAM DUT.
Real permutation, duplication, merging, optimization/irrelevance and SRAM macro
initialization still need proof and replay evidence. No external dependency
blocks this increment; test-cell timing/area remain artificial.

Read the read-only agent Phase 10/M9 and human formal-matching/retiming sections,
progress, previous verification and both papers' preserved matching/replay
extracts before edits. Plan/PDF hashes and initial staging are under
`automations/checkpoint_loop/runs/m8-iteration56/`. Preserve the dirty agent plan.
The loop M8 versus agent M9/Phase 10 numbering correction remains only here.

Changes:

- Added an audited CKDFFN Liberty library, zero-delay model and storage adapter
  under `tools/checkpoint_formats/tests/fixtures/formal/inverted/`. Genus actually
  synthesizes the original DUT into this cell library with retiming disabled;
  the netlist is never rewritten to manufacture inversion. QN storage captures
  the complement of D, with no hidden state; all 24 physical stored bits differ
  in polarity from semantic RTL, including all four RAM words.
- Added `--profile direct|inverted` to the complete existing CAD/VCS verifier.
  Both profiles retain all restore, uninterrupted-continuation, real storage
  fault, changed-netlist and five atomic loader rejection checks. Added a fresh
  wrong-polarity formal proof that must fail and reject map export.
- Formal configuration is a mandatory hash-bound build artifact, hashed before
  and after the proof. Exact inventory-derived name matches and configured
  polarity are *candidates*. Formality must prove every state relation and all
  outputs; only passing-point reports produce the StateID map. No reset/input
  assumptions or black boxes. This release defaults inversion matching off;
  automatic inversion discovery swaps some candidate registers and misses a RAM
  word even with fixed names. Those failed attempts and one reserved-Tcl-variable
  error are retained as diagnostics, never passing evidence.
- The restricted flat-RTL adapter now requires the semantic manifest's reference
  hash to equal the actual proven original RTL bytes. A new test rejects an
  unrelated reference hash. This capability uses an explicit fixture manifest;
  future Golden Gate/FIRRTL reference identity needs a separately audited adapter.
- Independent audit cross-checks both human passing-polarity reports, the complete
  netlist inventory, adapter/model and original-RTL identities, every translated
  checkpoint bit, trace boundary and actual simulator log. Three isolated actual
  artifact mutations (map XOR, passing report and deposit value) are rejected.

Final real-tool evidence (relative to Chipyard):

- Inverted: `automations/checkpoint_loop/runs/m8-iteration56/inverted-complete/invocation-a7eywu05/`
- Direct: `automations/checkpoint_loop/runs/m8-iteration56/direct-complete/invocation-d8jx2kwp/`

Each Formality run proves 36 compare points: 24 state and 12 output bits.
The inverted map has 24 XOR=1 destinations; direct has 24 XOR=0. Each ordinary
RTL VCS capture at pre-edge C=17 creates independent Level-2 checkpoint/trace
inputs. Fresh gate VCS deposits and verifies every stored bit with zero edges,
then matches all 79 boundaries / 237 output values through C=95, END C=96.
Uninterrupted gate simulation matches the same original RTL oracle after 96
edges. Reset at C=37, enables and complete RAM reads/writes remain included.
Five malformed loads each preserve all 24 bits before edges and still match
continuation. The real storage fault first differs at C=29 after 12 restored
edges; the changed D-input netlist and wrong polarity both fail fresh formal
proof and export. Both independent audits pass.

All 91 Python tests and complete M2/M3 VCS regressions pass. M2 retains five cuts,
all 22 state words, real C=29 divergence and four loader rejections. M3 checks
717 transport edges, 23 semantic advances, six complete captures, 242 boundary
and five semantic replay samples, and eight invalid reads. Evidence and commands
are cataloged under `runs/m8-iteration56/`. Top-level reproducible argv,
summary and full-path artifact catalog are `verification-commands.json`,
`summary.json` and `artifact-manifest.json`; per-invocation CAD/simulator commands
remain in `commands.json`. Every VCS shell sources Chipyard env, FireSim env,
then `vcs-env.sh` LAST, using Y-2026.03-SP1 and system GCC/G++ 13. The reused M2
Make build uses `VCS_FLAGS=-Mupdate`.

Next: obtain real synthesis/proof evidence for nontrivial bit permutation and
one-to-many state, then proven merging/constants/irrelevance, plus an audited
SRAM macro model with complete array/pipeline state and zero-edge initialization.
Do not count unit-only transformations or global equivalence PASS as acceptance.
Level 1 remains independent. No plan/PDF/conda edits, staging, commits, resets,
cleaning, FPGA, process ASIC or power validation are claimed.

## Historical iteration 55 evidence

Status: in progress. A real Genus/Formality/VCS flow proves and replays complete
direct correspondence for a small original RTL DUT. The remaining acceptance
cases are real polarity/permutation/duplication/merging/optimization proofs and
an audited SRAM macro state-loading interface. Unit evidence for a transformation
does not count as a formal tool proof. No external dependency blocks this increment.

Read-only plan inputs: agent Phase 10 (formal state mapping, lines 841–918), its
M9 formal correspondence exit, human direct gate-level replay/matching discussion,
and progress/previous verification. Read both root papers' preserved extracts,
including Strober's sequential matching and retiming discussion. Their hashes
and starting staging list are in `automations/checkpoint_loop/runs/m8-iteration55/`.
The existing dirty agent plan is preserved. The loop calls this M8; the agent plan
calls it M9/Phase 10. This note records that numbering discrepancy; do not edit
either plan to correct it.

Implementation:

- `tools/checkpoint_formats/formal_state_map.py`: separate `asic_state_map.json`,
  complete per-StateID/address/bit relationships, gate storage destinations,
  explicit XOR polarity, one-to-many destinations and passing proof status.
  Complete semantic and gate membership are mandatory independently of the
  global equivalence result. Unknown cells/macros, hidden cell state, missing
  proofs, retiming, unsupported clocks and optimized/merged reference state reject.
- Tool-specific elaborated reference naming is an explicit restricted adapter:
  `held` → `held_reg[bit]`, `ram[address]` → `ram_reg[address][bit]`. Complete
  actual Formality `all_registers` membership must agree; unsupported conventions
  fail instead of guessing. Gate names come from passing relationships, with an
  independently parsed flat standard-cell netlist inventory and hash-bound model
  storage adapter. No black boxes are allowed.
- The two Tcl scripts export the hashes of their actual input bytes before/after
  execution. Synthesis also exports the netlist hash and queried retiming=false.
  The map binds all artifacts and the manifest/adapter. Translation rebuilds and
  checks the map against current evidence before decoding `.rtlckpt` values.
- The existing ordinary RTL VPI loader now handles bracketed escaped intermediate
  instance components; final register/RAM-word handling is preserved. A real VCS
  diagnostic showed that `tb.dut.\count_reg[0] .state` resolves while the unescaped
  form does not. Handle resolution, type/width/count/bit checks precede any write.

The small DUT is a flat original pre-FAME Verilog fixture with two four-bit
registers and a four-word/four-bit logical RAM, a single rising-edge clock,
synchronous register reset, enables and RAM writes. Its schema-1 semantic
manifest is constructed explicitly by the verifier, not emitted by Golden Gate.
Genus 21.15-s080_1 maps it to 101 cells (24 CKDFF storage bits); retiming is
explicitly disabled. `cells.lib` has artificial test timing/area and `cells.v`
has audited zero-delay functional models. They establish an actual synthesized
standard-cell topology and functional proof, not a foundry/process ASIC result.
Production ASIC/FCFS netlists and SRAM macros are not yet supported.

Final invocation (all paths relative to Chipyard unless stated otherwise):

`automations/checkpoint_loop/runs/m8-iteration55/complete-validation/invocation-9q59xpcl/`

- Formality P-2019.03-SP2 checks out a license and proves 36 compare points:
  all 24 state bits and 12 output bits. It exports final *passing* sequential
  relationships, with separate noninverted/inverted queries and complete
  reference/implementation register inventories. No reset/input assumptions or
  constants are supplied. RAM is explicitly synthesized to flip-flops in this
  capability; no assumption is made about production RAM implementations.
- Ordinary VCS Y-2026.03-SP1 `-full64` captures an independent Level-2 checkpoint
  at pre-edge C=17. Fresh gate VCS deposits all 24 storage bits, reads all back
  with zero edges, then matches all 79 pre-edge boundaries/237 output values
  through C=95, ending C=96 after 79 edges. An uninterrupted gate run ends after
  96 edges and matches every corresponding original-RTL boundary. Reset at C=37,
  register enables and RAM read/write behavior are included.
- Five actual gate-loader faults (missing handle, wrong width, duplicate handle,
  X value and incomplete payload) reject before writes. All 24 previously loaded
  bits remain unchanged at zero edges and each continuation still matches.
  A real gate storage-bit fault first differs at C=29 after 12 restored edges,
  with exit 1. A separate modified gate D input produces Formality Verification
  FAILED / VERIFY=0, and export rejects it.
- `independent-audit.json` cross-checks raw human passing reports, all source
  hashes, the 24 netlist storage instances, every semantic bit, checkpoint values
  against ordinary RTL capture, each trace input/output and all gate log boundaries,
  atomic rejections and both actual failures. The auditor imports no exporter/codec.
- All 90 Python tests pass (six new map tests). XOR polarity, permuted destinations
  and duplicated destinations are *unit* translation evidence only. Full M2 VCS
  metasim plus clean-RTL regression passes all five cuts, 22-word restores, real
  C=29 semantic divergence and four existing loader rejections.
- Complete M3 banked VCS regression also passes: 717 transport edges, 23 target
  semantic advances, six 22-word public-port captures, 242 transfer-boundary
  replay samples, five semantic replay samples and eight invalid client reads.

Formality and Genus licenses are available. Genus must remove inherited
`LD_LIBRARY_PATH` for its subprocess to avoid Conda ICU/libstdc++ conflicts;
the VCS subprocess retains the helper's complete environment. Design Compiler
T-2022.03-SP5 fails to launch with `libpthread.so.0: GLIBC_PRIVATE not found`;
O-2018.06-SP4 lacks `libmng.so.1`. These diagnostics do not block the working
Genus/Formality path. Jasper was not needed for this increment.

Exact reproducible top-level argv, summary, full-path artifact catalog and all
diagnostic attempts live under `runs/m8-iteration55/`. Inner CAD/VCS commands are
in the final invocation's `commands.json`. Every VCS shell sources Chipyard
`env.sh`, FireSim `env.sh`, then `vcs-env.sh` LAST; reused M2 Make uses `-Mupdate`.
No conda/PDF/plan edits, staging, commits, reset/clean or physical FPGA validation.
Level-1 remains separate. No ASIC switching/power acceptance is claimed.

Next: extend formal export to proven equivalence classes/constants/irrelevance
without dropping required state, exercise actual synthesis polarity, permutation,
duplication and merging in fresh formal/replay runs, and add a hash-bound SRAM
model adapter with complete array/pipeline/port state and zero-edge initialization.
Do not promote unit-only transforms or a global equivalence PASS to acceptance.
