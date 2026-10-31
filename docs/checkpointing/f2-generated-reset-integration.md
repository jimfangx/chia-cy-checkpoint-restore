# F2 shell adapter connected to generated clock/reset wiring

Iteration 293 adds `CheckpointF2ClockResetCut`, the common connection between
literal native shell reset writers and the compiler-generated physical clock
mask, logical CE vector and held functional reset. It composes the existing
source-cancellation guard and reset-owned cut controller in external-network
mode. The adapter instantiates no clock gates. The generated native hierarchy
retains the gates and their original logical CEs.

The shell's four synchronizer bits, three AXI reset consumers and clock-wizard
reset retain their original paths. The adapter observes the actual writer bits;
it does not clock or reset them. Collector initialization remains independent.
Raw reset/DDR loss cancels asynchronously and remains sticky even if the source
returns without another raw edge. Host withdrawal cannot release a failed cut.
The visible 81-bit control vector in the two-gate verification configuration
contains the entire collector/guard state; the three vendor hidden CE latches
remain distinct owners. Observing collector state does not capture the running
collector atomically.

Verification connects the adapter to retained, compiler-emitted reset/clock RTL,
not a handwritten replacement for that hierarchy. The original emitted RTL and
separately instantiated literal shell writers provide the reference. The input
files retain iteration 291's provenance and exact hashes; iteration 293 receipts
record fresh component synthesis/execution using those inputs. They are not
newly generated Rocket RTL or FPGA checkpoints.

Native Vivado 2025.2 synthesis and exact-DCP component place-and-route run on the
current manager at the unchanged requested 140 MHz. Setup/hold slack is
+1.262/+0.037 ns. All 168 sequential identities survive, all 216 routable nets
route without errors, and the component DRC reports no violations. Native
checks require three default-SYNC BUFGCEs, four original FDCE shell writers and
one asynchronous FDPE cancellation flop. Parent clock, shell I/O, source-pulse
width, recovery/removal and full-image timing remain unmodeled.

Fresh EDA SP2 VCS passes 4,547 checks, cuts 0/17/128/256, 320 active
cycles and 64 collection stalls. Six negatives exercise raw reset/DDR pulses,
both release races, writer drift and owner loss. A separate deliberate reset
route corruption stops at `left.reset`, cycle 17, before acknowledging another
edge. Independent auditing passes all eight full-visibility debug waves, including
all 80 functional, four shell-writer and 81 visible control bits plus generated
clock/reset routing. All 409 Python / 61
manager tests, host ASan/UBSan, generated-bank, FCFS and cut regressions pass.
Fresh exact-Rocket ordinary compilation still rejects the missing physical
FASED CE owner before emitting an image. No Scala source changed.

The implementation is not installed in a deployable shell. Complete production
CE/reset ownership, selective functional hold, separately owned ungated
collection, atomic collector/native transport/stream state, FASED/functional
memory, host and pre-FAME state remain required. The ordinary Rocket compiler
must continue rejecting missing owners. Reuse iteration 194's localhost build
invocation after those requirements are satisfied. No checkpoint-enabled AFI,
physical active Rocket cuts, FPGA-origin Level-1/Level-2 pair, CPU finite/live
migration or rolling hardware recovery is established by this component.

Commands, receipts, original input snapshots, debug waves and diagnostic logs
belong under `automations/checkpoint_loop/runs/aws-f2/iteration293/`.
