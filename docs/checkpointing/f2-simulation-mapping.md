# Native target-boundary linking

Iteration 214, `F2-rocket-checkpoint-migration`, **in_progress**.

`SimulationMapping` replaced the generated `TargetBox` external instance with
`FAMETop` but returned only the inner circuit-name rename. Its retained
`TargetBoxAnnotation` still identified the removed placeholder. Strict bank
preflight correctly rejected that path.

The actual linker now validates the one absolute boundary, each concrete path
hop, the external placeholder, unique declaration and concrete instance,
disjoint pre-link namespaces and matching lowered port interfaces. It removes
the placeholder definition, links the inner top with its resolved instance type,
and returns both circuit and placeholder-module native FIRRTL renames. FIRRTL
updates the boundary and all local/nonlocal annotations together. A repeated
wrapper, stale/foreign/relative path, duplicate/missing boundary, nonexternal
placeholder, recursive/missing module, namespace collision or incompatible
interface rejects. Bank preflight remains strict.

Nine new Scala checks cover native transform-manager renaming, downstream
low-form checking, strict bank specialization and rejection paths. The exported
one-register linked fixture is synthesized on the current manager using native
Vivado and independently checked in fresh EDA VCS against unchanged original
RTL and an arithmetic oracle. Its complete state is read at cuts 0, 17, 128 and
256 through the synthesized bank interface with a separate access clock,
frozen functional-clock pulses and sixteen response stalls. Deliberate bank
word corruption rejects at cut 17 without further functional advancement.
Healthy and failed debug waveforms are retained. Independent audits compare
native/EDA generated and current-source snapshots and reject altered boundary
annotations, reference circuits and missing or coherently changed owners.
These are compiler/component checks, not hardware-produced CPU checkpoints or
live CPU migration acceptance.

The exact Rocket recipe now passes its previous target-box mismatch and fails
explicitly at the physical `BUFGCE` enable latch in
`F1Shim.top.FASEDMemoryTimingModel_0.gate`. Its vendor-owned transparent-low CE
state needs a synthesized capture owner and a common low-phase atomic cut;
the metasim output register cannot serve as that owner. Preserve this rejection
until the physical contract exists. Complete clock/memory/timing/bridge/host and
pre-FAME ownership, localhost full image/P&R/AFI, all-hart hardware cuts and
FPGA-to-EDA finite/live/rolling acceptance remain pending.

Evidence, exact commands and original failure logs are under
`automations/checkpoint_loop/runs/aws-f2/iteration214/`. Reuse iteration194's
initialized localhost build invocation; do not substitute a stock image or
backdoor/metasim capture for hardware acceptance. See
[aws-f2-workflow.md](aws-f2-workflow.md) and
[github-publication.md](github-publication.md).
