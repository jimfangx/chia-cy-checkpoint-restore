# Generated reset routing at the physical clock cut

Iteration 291 adds `SynchronousResetCutWiring`. The final LowForm pass follows
an explicitly selected root reset through repeated instances, combinational
child outputs, memory controls and asynchronous memory reads. It records
register next-state/reset/value uses, native CE pins, print/stop/verification
uses and combinational root outputs. Register outputs and synchronous memory
read pipelines terminate the combinational cone. Definition-local input
summaries retain instance identity without inventing combinational cycles on
registered ready/valid feedback. Explicit FIRRTL invalids have no reset-expression
dependency; their values and ownership are not inferred.

The pass requires the independently reconstructed complete inventory and clock
plan. It rejects asynchronous register resets, reset-derived sequential clocks,
unsupported opaque consumers, undriven dependencies, stale inputs and namespace
collisions. In its separate generated sibling, every original root reset use is
replaced by `checkpoint_reset_functional`. The existing common-source clock
wiring preserves native gate locations and original logical CEs. The raw root
reset remains a distinct input for the external controller. The held-reset port
must connect to `CheckpointResetOwnedClockCut.functional_reset`; collector
initialization must have a separate owner and an ungated clock.

The explicit compiler option is `--simulator-synchronous-reset-cut reset`, used
with `--simulator-checkpoint-inventory F1Shim`,
`--simulator-physical-clock-plan` and
`--simulator-physical-clock-wiring-probe`. It emits separate
`.synchronous-reset-cut` FIRRTL/Verilog, audit, binding and emission files.
Missing/duplicate requests and combinations with capture probes reject. The
ordinary deployable netlist is not replaced. The whole-root clock companion
still stops the original MMIO/stream engine; it cannot collect a checkpoint
until an independently owned, ungated transport is installed. No annotation or image guard
admits incomplete capture because this option is present.

The retained exact-Rocket structural input has three root-reset references.
Their complete transitive fanout includes 1,001 register next-state uses, two
native CE pins, 230 print uses and 228 verification-enable uses. The source
input retains its original date; this is a fresh analysis of that input, not a
new FPGA execution. Fresh compilation of the exact recipe is separately
recorded under `runs/aws-f2/iteration291/`. The fresh ordinary compiler run
passes and emits three replaced root references, with 969 register next-state
uses, two native CE pins, 224 print uses and 228 verification-enable uses. These
current counts are distinct from the retained structural input above; their
input hashes, dates and output bindings remain separate.

The actual F2 shell expression is
`!rst_firesim_n_sync || !ddr_ready_sync`, clocked by `firesim_internal_clock`.
Both synchronizer chains assert asynchronously from `rst_main_n`. Thus the
consumer audit cannot establish source synchrony or freeze ownership. The
literal source observation, hash, register names and excerpts are retained in
`runs/aws-f2/iteration291/shell-reset-writer-observation.json`. The shell writers,
external assertion source, collector initialization/cancellation and atomic
transport ownership still require a real common-cut binding. The pass explicitly
reports the writer unbound and the external sampling contract required.

Validation uses a small generated sibling connected to the real reset-owned
controller in external-clock-network mode, with an independently emitted
original RTL reference. Native Vivado synthesis runs only on this manager;
all VCS execution runs only on EDA SP2. Fresh EDA SP2 passes 1,865 checks over 320 cycles, cuts 0/17/128/256 and
32 collection stalls. Reset/writer/owner loss rejects; deliberate reset-route
corruption stops at `left.reset`, cycle 17, without a later acknowledged edge.
An independent audit checks all five raw full-visibility waves against the
original functional words, held reset and actual root/native clock nets.

The exact native DCP passes component place-and-route at the unchanged requested
140 MHz: +1.854 ns setup and +0.049 ns hold, preserving all 158 sequential
identities and routing all 190 routable nets without routing errors or reported
DRC violations. Synthesis alone had an unplaced -0.072 ns hold estimate. Parent
clock source/skew and shell/I/O budgets remain unmodeled.

Detailed commands, diagnostics and waveforms belong in
`runs/aws-f2/iteration291/`. These are component and compiler
prerequisites: they establish no checkpoint-enabled image, AFI/AGFI, physical
FPGA cut, complete Level-1/Level-2 owner set or finite/live CPU migration.
