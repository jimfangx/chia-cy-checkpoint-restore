# Generated live-shell staging-owner restore

Iteration 309 exposes the existing native snapshot RTL's complete restore
interface through `NativeCheckpointLiveShellSnapshot.generate(...,
enableRestore = true)`. The default keeps the interface disabled and its
inputs tied low. Optional ports route through every original enclosing module
on the same proven raw clock. Regeneration validation rejects changed options,
missing hold wiring and coherently rehashed circuit changes.

A qualified raw-clock load replaces the entire local owner: retained payload,
occupancy, cut-cycle label and all six sticky error bits. Existing sticky errors
are donor state and do not prevent a safe complete load. Missing owners, lost
functional freeze, a busy reader, borrow/request/release overlap or an unheld
load refuse it. Reset retains priority. Hold revokes staged-word/bank permission
before the load and keeps functional bank storage parked even for an empty
donor. This adds no registers and preserves original live-register equations.

The binding names this local scope and exact owner width. Production restore
and complete image flags remain false. This adapter does not restore original
live registers, original/native reader state, functional memory, the separate
readout owner or global target time. In a composed readout, every other owner
still requires its own coordinated hold/load/readback. Production ONE-widget
descriptor/epoch attachment, physical CE/common-low-phase ownership and host
state remain required before a deployable checkpoint image can be built.

Evidence and exact commands are under
`automations/checkpoint_loop/runs/aws-f2/iteration309/`. The generated original
live-only fixture has a 237-bit payload / 308-bit complete staging owner. The
synchronous-reader variant has 557 payload bits / 628 owner bits. Native
localhost Vivado synthesis preserves every staging bit in both variants;
utilization is respectively 406 LUTs / 675 registers and 850 LUTs / 1,251
registers. These are unplaced component results, not full-image timing closure.

Fresh EDA SP2 verification passes eight donor/restore pairs, sixteen unsafe
loads and 1,876 whole-owner loads in bit-coverage processes, including 1,872
one-hot/complement loads covering every bit in both polarities.
Compiled payload corruption stops at canonical bit zero on the first readback
with no acknowledgement or enabled continuation; 35 debug waveforms are retained.

The generated-wrapper EDA test obtains directed donor images from original
functional execution and real snapshot requests. Fresh destination processes
leave staging reset deasserted, load every owner word through the generated
ports, independently compare the four original RTL registers, check every
staged word and padding, and retain full debug VCDs. Empty, occupied, released
and sticky-error donors, one-hot/complement loads of every bit, unsafe load
controls and compiled payload corruption are separate cases. The independent
raw-wave audit uses the generated hierarchy's actual reset/ready signals and
rejects continuation after a divergent load. Component `.hex` donors are never
FPGA `.fsckpt` or `.rtlckpt` images or evidence of CPU live shadowing.

The shared auditor retains its standalone defaults. A separate compatibility
check re-audits 117 explicitly historical iteration286 waveforms with the current
auditor; it does not relabel those simulations as fresh execution.

Full localhost exact-Rocket image/P&R/AFI, identified F2 deployment, active
four-hart FPGA-origin cuts, independently restored CPU Level-1/Level-2 readback,
finite RTL replay, sustained restored-metasim-guided clean RTL and rolling
hardware recovery remain pending. Reuse the initialized iteration194 localhost
build invocation; do not request a duplicate AFI or treat account-owned images
as this loop's checkpoint image without source/transport ownership evidence.
