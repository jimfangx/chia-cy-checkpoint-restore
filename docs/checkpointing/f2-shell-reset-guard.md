# F2 shell reset-source cancellation

Iteration 292 adds `CheckpointF2ResetGuard`, a synthesizable companion to the
common-source reset-owned clock cut. It observes the actual shell's four
reset/DDR-ready synchronizer bits and snapshots them at the common falling
cut. A writer change immediately withdraws capture permission and becomes
sticky on the ungated clock. The writer flops remain ungated; the original
shell reset paths retain their latency and asynchronous assertion.

This distinction matters because `rst_firesim_n_sync` also resets three AXI
clock-converter interfaces. The raw `rst_main_n` also resets the clock wizard.
Freezing these writers or connecting the shell reset to collector initialization
would change external behavior or erase cancellation evidence. Instead, loss
of raw reset or DDR readiness asynchronously sets a separate cancellation
flop. A source pulse that returns before another raw edge, including while the
clock generator is stopped, cannot repair an invalid capture. The common-cut
controller keeps functional clocks held on cancellation and host withdrawal.

Collector initialization is a separate, explicit operation after the sources
are ready and before a capture request. It discards a session; it is not an
adapter for restoring shell state. Pre-ready/uninitialized sessions are not
valid checkpoints. The guard exposes its six control bits alongside the four
observed writer bits, but supplies no atomic owner for the running collector,
MMIO/DMA engine or other shell/DDR state.

`tools/checkpoint_formats/f2_shell_reset.py` extracts the two original writer
blocks verbatim from the current native F2 shell. It checks their exact supported
logic, all uses of their four state names, the three unchanged named AXI-reset
connections, the original simulator-reset expression and clock-wizard reset.
Changes and extra uses reject. Source and extracted bytes have independent
hashes. This is a restricted source observation and a verification sibling,
not a whole-shell connectivity proof or a rewritten deployable shell. The
original shell, initialized manager YAMLs, exact CPU recipe and plans are
unchanged.

Fresh native Vivado 2025.2 synthesis verifies four original FDCE writer cells,
one asynchronous FDPE cancellation cell and four default-SYNC BUFGCEs. The
exact DCP passes component place-and-route at the unchanged requested 140 MHz,
with +1.627 ns setup and +0.044 ns hold slack. All 250 sequential identities
survive; all 461 routable nets route with no routing errors or reported DRC
violations. Parent-clock, shell I/O and asynchronous source timing remain
unmodeled. Digital pulse tests do not establish minimum device pulse widths,
recovery/removal margins, CDC closure or full-image timing.

Fresh EDA SP2 VCS passes 2,107 checks, cuts 0/17/128/256, 320 active target
cycles and 64 collection stalls against independently instantiated original
writer/functional RTL. Six negatives cover raw reset and DDR pulses, both
release races, writer drift and missing owners. Source pulses complete without
a raw edge; rejected sessions retain target cycle 17 and acknowledge no later
target edge, even after source/owner presence returns. A subsequent ordinary
reset-propagation exercise verifies unchanged shell behavior. Independent
waveform auditing checks all seven full-visibility raw waves, all 160 functional
state bits, four writer bits and the complete 82-bit visible control vector.
The four vendor-gate hidden latch owners remain separate from that vector.

All 409 Python tests, ASan/UBSan, host capture, generated-bank, FCFS and cut
regressions pass fresh, as do 61 manager tests. No Scala source changed. The
fresh exact-Rocket ordinary bank compiler still rejects the unowned FASED
physical CE latch, before emitting an image. Original receipts and diagnostics
are retained under `automations/checkpoint_loop/runs/aws-f2/iteration292/`;
the raw replay commands are in that iteration's `verification-commands.json`.

Next install the guard with the actual generated held-reset/clock network and
complete CE-cone ownership, selective functional hold and independently owned
ungated collection. Bind atomic collector/native transport/stream and memory,
FASED, host and pre-FAME state before building the full localhost image/AFI.
No checkpoint-enabled AFI, physical FPGA cut, paired CPU migration, finite/live
CPU acceptance or rolling hardware recovery is established by this component.
