# Capturing original Rocket clock events

Iteration 139 adds a read-only native VCS observer for the retained, unthreaded
ChipTop boundary. It uses compiler-carried StateIDs for storage and independently
resolves every mapped owner's emitted clock and all original boundary ports.
It rejects missing/reshaped ports, wrong state clocks, derived clocks, replicated
boundaries and unsupported clock-buffer placement. This does not authorize a
CPU Level-1 profile or implement FPGA transport. The observer's counters,
previous/upcoming gate vectors, per-window cursor, saved boundary values,
VPI handles, saved readback values and open diagnostic files are additional
observation owners. They are outside the original ChipTop semantic boundary
and are not serialized into a Level-2 image. Active observation has no Level-1
restore adapter; complete CPU Level-1 admission remains rejected.

The observer samples settled state and boundary values one picosecond after
host-clock transitions, before the *next* original clock event. It records
explicit seven-clock vectors for both rises and falls. In the inactive region
of the upcoming host transition, before original register NBAs, it verifies the
predicted actual gate levels and every non-clock boundary value. At each cut it
also reads back every captured semantic word at that pre-edge boundary. Clock
aliases are sampled at their actual pre-event level; they are never replaced
with constants in the captured trace. Host stalls produce no target events.

Counts come from observed target buffer outputs, starting before their first
edge. They are independent of host-driver credits and printed CPU counters.
The explicit cycle clock is the first original manifest input, `clock_mbus_0`.
The first captured C=100 cut has 100 completed rises in each of six original
mbus/tile/serial domains and 50 in uncore, with original event index 200.
These are counts from this execution, not an assumed replay clock ratio.

`fame_capture.cc` resolves the complete compiler-bound storage plan before
opening a snapshot. It reads registers and logical memory words without any
deposits, reset, clocks or host-driver service. Unknown bits reject. The event
window packager validates every original state word, boundary signal, alias,
clock vector, event label and completed-rise count before returning independent
`.rtlckpt` and `.trace` bytes. Existing event-0 fixture packaging is unchanged.

Fresh ordinary RTL VCS restores every word and completes settled readback before
its first edge. Replay drives the captured inputs, compares every output, and
only then acknowledges the captured event. Native negative cases cover complete
baseline preservation for missing, duplicate, unknown and wrong-width loader
rows. Container negatives cover truncation, checksum, build identity, missing
or unknown owners, missing outputs and extra inputs. Real stored CSR counter
bits in each hart provide first-boundary semantic corruption cases.

Native evidence and current result totals are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). The complete source run must
pass its self-checking four-hart workload and all four full instruction traces
must match the uninterrupted reference before its capture results are accepted.
Capturing boot state alone cannot establish CPU acceptance. Required active
cuts and complete Level-1 continuation remain separate acceptance obligations.

All diagnostics belong under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration139/`.
The two root papers' snapshot/replay sections were re-read: both require the
complete selected state and the corresponding finite I/O trace. Their retained
local text and source hashes are under iteration 138 `papers/`. No ASIC activity
or physical FPGA validation is introduced here.

The accepted iteration-139 run completes the real four-hart workload, matches
all four full instruction traces, and passes C=100/700000/900000/3250000 fresh
ordinary RTL replay with complete zero-edge state readback. The matrix records
all 256 events, 21,760 output comparisons, sixteen actual semantic first
divergences and 44 invalid cases. Level 1 remains independently in progress.
