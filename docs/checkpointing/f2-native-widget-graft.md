# Connecting the reserved widget to existing execution

`NativeCheckpointWidgetGraft.connect` connects the real, registered checkpoint
widget to a reconstructed readout graft inside its existing selected execution.
It consumes the checked pre/post-inline peer routes and the original selected
subtree. Every original selected definition must match the executing host.
Changed definitions cannot execute outside that subtree; generated definitions
cannot collide with the host. The connector changes the twenty explicit
transaction/CE connections and retains the original host ports, execution
instances, annotations, MMIO allocation and shared DMA streams.

The current API accepts only an exact, target-free NoCircuitDedup policy on
the standalone selected source and reconstructed graft. It rejects annotations
on changed selected definitions in the enclosing host. Production annotation
projection must be implemented explicitly before using annotated Rocket inputs;
this restriction must not become a blanket annotation exemption.

The descriptor identity remains the reservation sentinel. The generated driver
header still contains its unbound-reservation error, RESTORE_ENABLE stays zero,
and ordinary image emission and external-state ownership checks still reject.
The bounded descriptors use the standalone selected-source namespace
(`SimWrapper.network.*`); the connected execution is `FPGATop.sim.network.*`.
They are not an enclosing-host manifest or a production driver identity.
The connection receipt records `in_place_checkpoint_widget_connected=true`
only for these routes. Complete capture, production annotation translation,
owner admission, descriptor identity binding and metasim restore remain false.

The bounded execution fixture uses the actual generated FPGATop, NASTI adapter,
shared CPU DMA engine and native clock gates. Its selected SimWrapper contains
one running register/RAM fixture. Independent auditing reconstructs the original
physical peer routes and every circuit change, including unchanged annotations,
clocks, original resource header and transport sources. This is component
integration evidence; it is not a Rocket workload or an FPGA checkpoint.

The final component run passes 5,165 EDA VCS checks, four captures at target
cuts 81/184/324/36 (the last after reset), 136 state words and 900 stalled DMA
cycles. A separately compiled readout defect stops at cut 81, word 0, byte 42.
Independent waveform auditing confirms its actual bad payload with the target
still frozen, and 2,704 stable frozen source-clock samples in the healthy run.
The failure path must yield after dump flushing; earlier immediate-exit waves
omitted the final buffered values and remain preserved as failed debug evidence.

Native OOC synthesis uses 5,018 LUTs, 1,646 registers and three BUFGCEs, with
662 raw-clock control/readout registers checked. Estimated setup/hold slack is
+0.437/−0.074 ns at 140 MHz, with unconstrained external I/O. This does not
establish full-image implementation timing or a programmed FPGA.

Verification entry points are `NativeCheckpointWidgetGraftSpec` and
`tools.checkpoint_formats.tests.verify_widget_graft`, with localhost Vivado,
EDA SP2 VCS and matching-receipt audit modes. Current execution receipts and
retained failures belong under `automations/checkpoint_loop/runs/aws-f2/iteration247/`.
The progress handoff records completed checks.

Iteration 248 replaces the invocation-local replacement runner after controller
reruns encountered multiple old summaries. Run
`python3 -m tools.checkpoint_formats.regression_runner --plan PLAN --out OUTPUT`
on EDA with `vcs-env.sh` sourced last. Plans name every EDA scope, native receipt
and hash, and use workspace-relative paths in subprocess argv. Each call reserves
an exclusive attempt directory, verifies all native inputs before execution,
keeps logs and binds the sole explicitly returned fresh receipt. An independent
`--audit RESULT` checks every scope and pin without discovering a latest run.
Failures retain a failed attempt and its underlying logs. Previous attempts are
never reused, removed or overwritten. This is component regression plumbing.

The full six-scope command passed twice against an already populated output
tree on EDA SP2. Both complete source/artifact audits pass, alongside fresh
native synthesis, waveform and retained sanitizer/FCFS checks. The fixture
continues to pass 5,165 checks at the same four cuts; native/EDA binding now
includes 597 sources and 636 inputs. These new receipts live under
`automations/checkpoint_loop/runs/aws-f2/iteration248/`. Original iteration-247
receipts, including its failed controller rerun, remain unchanged.

The exact Rocket recipe still needs its uncovered functional and FASED clock
owners, production annotation/identity binding, complete reset/external-writer,
memory, timing, bridge, host and pre-FAME semantic coverage, full localhost image
implementation/AFI, active four-hart F2 captures and independent paired CPU
restores with finite and sustained live RTL continuation. Preserve those pending
entries in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).
