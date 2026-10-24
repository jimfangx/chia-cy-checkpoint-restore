# Physical clock-enable dependency prerequisites

Iteration 219 adds `.physical-clock-dependencies.json` to the separate physical
clock-wiring probe. The compiler traces the original **unmasked** CE expressions
through concrete hierarchy to inventoried register/memory state and external
root inputs. Definition-local summaries preserve distinct repeated-instance
identities. Each state terminal carries its exact StateID, adapter and complete
clock-consumer list from the topology plan. Both possible mux/validif branches
are retained conservatively. Unknown/invalid drivers, combinational cycles,
physical clock outputs used as data and root clocks used as CE data reject.

An asynchronous RAM read includes its memory contents, address and enable
dependencies. Synchronous reads use the actual emitter's saved address/data
state, and readwriters use the implicit rdata state. New/undefined read semantics
retain memory contents as well as the saved address. Asynchronous register
resets remain unsupported by the complete inventory; stopping their clock
cannot establish stable state. The audit does not change functional RTL.

The exact Rocket compiler identifies three original native gates. Their cones
contain 27, 179 and 179 clocked-state terminals (207 distinct owners) and one
external root input, `F1Shim.reset`, in both target-gate cones. This replaces an
unspecified CE-ownership obligation with a concrete reset-owner requirement.
It does **not** bind that reset owner: the reset must remain stable at the same
cut under a production contract, and a controller reset must invalidate an
unfinished capture. Merely stopping target clocks or sampling masked-zero CE
cannot discharge this requirement.

An independent Python oracle traverses concrete instances, rather than sharing
the compiler's summary algorithm. It reconstructs the complete document and
rejects omitted gates/terminals, changed StateIDs/clock consumers, coherently
removed external inputs, invented freeze owners and false capture/reset-support
claims. The native/VCS wiring harness now snapshots the dependency manifest,
compiler and test sources, and oracle alongside the exact generated netlist.
The retained full topology/wiring audits remain required independently.

These are compiler/component prerequisites. `production_freeze_owners_bound`,
`complete_fpga_capture` and `deployable_capture_image` stay false. The production
physical CE bank guard remains enabled. Bind the external reset, physical CE
StateIDs and zero-edge metasim restore mapping, translate production
annotations/XDC, connect ungated MMIO/DMA, and complete functional-memory,
timing, bridge, host and pre-FAME same-cut ownership next. Full localhost image
implementation/AFI, real active four-hart F2 captures, paired independent
zero-edge restores, finite replay, sustained live clean-RTL execution and rolling
hardware recovery remain pending. Reuse iteration194's initialized localhost
build invocation; do not deploy the probe as a checkpoint image.

Execution logs and exact commands are under
`automations/checkpoint_loop/runs/aws-f2/iteration219/`; see its `summary.json`
and `verification-commands.json` for the completed checks and individual files.
