# M8 formal state mapping — iteration 56

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
