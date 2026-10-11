# M8 formal state mapping — iteration 55

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
