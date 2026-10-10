# M7 independent finite DESSERT replay

The loop's M7 corresponds to Phase 9 / M8 in the read-only agent plan. The
numbering correction is recorded here; neither input plan is modified.

`tools/checkpoint_formats/finite_replay.py` accepts the independent semantic
checkpoint, a finite checksummed boundary trace, the semantic/boundary manifests,
configuration and original DUT-only RTL. It supports both boundary schemas,
including schema-2 output clock aliases proven to forward the input clock.
No `.fsckpt`, cut sidecar, native runtime, socket, FASED or running FireSim
process participates in replay. The package command accepts complete `DATA`
rows from either capture transport; FPGA execution remains unvalidated.

Row C means S[C], I[C], O[C] before target rising edge C. The bench loads and
settles every register and RAM word, reads back every word before its first
edge, applies all inputs, settles outputs, compares every output, then takes
exactly one edge. It terminates at the first mismatch or finite END, retaining
original target labels. The VCS image contains ordinary selected target RTL,
the generated bench and the existing host VPI loader. Trace rows are a data
file, keeping SV compilation independent of trace length. The replay metadata
binds checkpoint, trace and actual replay RTL bytes independently.

Checksum, configuration, manifests, exact state/port membership, widths/depths,
consecutive cycles, clock aliases and X/Z/padding checks precede publication of
restore inputs. Unsupported state declarations, procedural syntax or clocks
reject explicitly. Runtime file errors, short/extra rows, bad cycle labels and
unknown values fail nonzero. The supported grammar remains the existing
single-clock FIRRTL reg/wire emitter; general pipelines, threaded mappings,
opaque state and Rocket/BOOM coverage are not established.

Full hierarchy dumping uses VPD with `-debug_access+all` and an explicit
`$vcdplusmemon` for every entire semantic RAM. Hierarchy-only `$dumpvars` and
dynamic memory-word `$dumpvars` omitted RAM words in this release; the retained
diagnostic demonstrates that. `vpd2vcd -full64 +includemda` exports all memory
words. Omitting `-full64` selected the installation's 32-bit utility and failed
before conversion; the 64-bit utility works. VPD/VCD are RTL debugging artifacts,
with no ASIC switching-activity or power claim.

Generate an ordinary bench from self-contained inputs, from the Chipyard root:

```sh
python -m tools.checkpoint_formats.finite_replay replay \
  --manifest "$INPUTS/FireSim-generated.semantic-state.json" \
  --boundary "$INPUTS/FireSim-generated.semantic-boundary.json" \
  --configuration AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config \
  --checkpoint "$INPUTS/capture.rtlckpt" --trace "$INPUTS/capture.trace" \
  --clean "$INPUTS/FireSim-generated.semantic-clean.sv" --out "$REPLAY"

source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
"$VCS_HOME/bin/vcs" -full64 -sverilog -debug_access+all +vpi \
  -cc "$CC" -cpp "$CXX" -CFLAGS '-std=c++17' -timescale=1ns/1ps \
  -top finite_replay_tb -Mdir="$REPLAY/csrc" -o "$REPLAY/simv" \
  "$REPLAY/clean.sv" "$REPLAY/replay.sv" tools/checkpoint_formats/semantic_restore.cc
"$REPLAY/simv" -no_save +restore="$REPLAY/restore.txt" +trace="$REPLAY/trace.txt" \
  +waveform="$REPLAY/replay.vpd" +audit="$REPLAY/matched.txt"
"$VCS_HOME/bin/vpd2vcd" -full64 +includemda "$REPLAY/replay.vpd" "$REPLAY/replay.vcd"
```

Use absolute `INPUTS` and `REPLAY` paths. The full verifier creates fresh
invocation directories and retains all failed diagnostic attempts. Its
schema-1 cases change actual `io_respData` RTL using the DUT counter, then
reproduce the defect at C=29 from reset and in-flight checkpoints C=24/C=26.
Its schema-2 cases replay the complete retained healthy FCFS metasim suffix,
then change actual DUT AR QoS logic to XOR response-valid and repeat that
defect twice. Neither case modifies the trace, corrupts state or injects a
bench-cycle fault. Original and debug RTL hashes are recorded separately.

`audit_finite_replay.py` independently reads the generated waveform, checks all
semantic words against the restore oracle at the zero-edge cut, then checks
every boundary value and actual edge/cycle timing, including the divergent
boundary and absence of a faulting edge. The main verifier separately audits
every semantic waveform declaration, including every memory address.

Iteration-54 acceptance passes. The fixture's actual response-transfer RTL
defect appears at C=29 from reset and both in-flight snapshots. Healthy FCFS
replays C=524453..774637, compares all 8,506,290 outputs, takes exactly 250,185
edges and exits 0 at C=774638. Two fresh FCFS RTL-defect processes first change
`ep_axi4_ar_bits_qos` at C=524474, after 21 matching edges, and both exit 1.
Full boundary comparison includes payload values regardless of valid; the
FCFS QoS difference is on an invalid AR payload at that first divergent cycle.
The fixture defect occurs during an actual valid/ready response transfer.

All seven VPD/VCD pairs pass the independent waveform audit. Each FCFS pair
contains all 1,342 registers and 13,501,966 words in all 201 semantic RAMs,
plus all 50 boundary/clock ports. Every initial word agrees with the restore
oracle before any edge; every replayed boundary agrees at its original cycle,
including the fault and absence of its edge. The healthy waveform verifies
all 12,008,880 input/output values. All 84 Python / 24 Scala tests and complete
M2/M3 metasim/ordinary-VCS regressions also pass. No FPGA or ASIC validation
is claimed.

Full-path catalogs, exact argv and summarized evidence are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m7-iteration54/`:
`artifact-manifest.json`, `verification-commands.json` and `summary.json`.
The final invocation is
`finite-replay-final/invocation-tkq1rf1b/`, with `summary.json`,
`independent-waveform-audit.json`, self-contained `production/inputs/` and
each case's VCS executable, recorded build/run commands, sources, complete
restore/trace data, VPD and memory-inclusive VCD.
