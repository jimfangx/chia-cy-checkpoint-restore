# Atomic staging of original live shell registers

Iteration 302 adds `NativeCheckpointLiveShellSnapshot.generate`. It reconstructs
the selective shell before attaching one synthesized `CheckpointNativeStateSnapshot`
to its explicit live-register partition. The original registers retain their
declarations, reset expressions and next-state equations. They keep executing
while an immutable pre-edge copy is read in 64-bit words, with zero high padding.
Original enclosing StateIDs, widths, signedness, offsets and equation hashes bind
every copied bit.

The bank endpoint and snapshot use the same original clock. The independent
bank-access clock is removed from the selected execution and all routing
ancestors. Transparent Clock aliases must resolve through every ancestor to an
original root input; gates, data casts, multiple drivers and cycles are rejected.
All selected live registers must share that clock. Additional sidebands follow
the existing unique concrete execution; no functional execution is duplicated.

The caller must explicitly supply owner presence, owner freeze acknowledgement
and the target-cycle label. The local functional freeze must also be asserted,
and the original response endpoint must be idle when staging or releasing.
Functional bank requests and response acknowledgements remain closed until
staging succeeds. Early requests, simultaneous capture/read, duplicate capture,
unsafe release, lost freeze, missing owners, endpoint reset and target-label drift
revoke both handshakes and snapshot publication before another acknowledgement.
The occupied snapshot and retained errors hold the local functional cut without
feedback through the live fault cone. Recovering a failed epoch requires explicit
initialization of the snapshot and bank-response endpoint. Released payload
bytes remain owned state.

The actual reserved-widget fixture uses its compiler inline history to select
all eight original MMIO/DMA registers. Their 228 bits occupy four transfer words;
the snapshot's separate retained payload/control owner has 299 bits. Independent
inventory and equation checks reconcile this selection with the original host.
The directed simulation fixture also exercises a signed register and a 65-bit
register across word boundaries, using eight original owners / 237 bits and a
308-bit staging owner. Evidence and runnable commands are retained under
`automations/checkpoint_loop/runs/aws-f2/iteration302/`.

Verification passes all 23 focused checks and 384 complete-suite Scala tests /
60 suites plus sixteen preparation checks. Native Vivado synthesis retains all
308 staging bits in 675 registers / 244 LUTs. Fresh EDA SP2 VCS passes four cuts,
twelve fault cases and compiled payload corruption, retaining fourteen full debug
waves. Independent audits reject all 545 payload/control bit mutations and prove
first-word corruption at component cycle zero without a bank acknowledgement or
functional edge. The emitted full-suite fixture matches the independently used
native/VCS bytes. Retained shell, Python, ASan/UBSan, host, bank, FCFS and cut
regressions pass. Exact Rocket production compiles still refuse the unowned
FASED physical CE latch; no image is admitted. Final closure is
`runs/aws-f2/iteration302/final-audit-6w3l7fxi/summary.json`.

This adapter supplies atomic observation of the selected original live
registers. It does not install the adapter in the production reserved widget,
change the original descriptor ROM reservation, own native-reader or endpoint
staging/restore, prove global target time, or restore these registers and the
new staging owner. Original unsupported-owner records remain intact. All
complete-image and restore admission flags remain false. Physical CE/FASED,
functional-memory, host and pre-FAME completeness, the full localhost image/AFI,
physical FPGA cuts, FPGA-origin CPU migration, sustained paired live execution
and rolling hardware recovery remain pending.
