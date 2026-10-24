# Native inline constraint retirement

Iteration 212, `F2-rocket-checkpoint-migration`: compiler/component work only.
The exact Rocket recipe still cannot produce a checkpoint-enabled image.

FIRRTL 1.6's real `InlineInstances` pass removes module definitions selected
for full inlining, but leaves module-only `NoDedupAnnotation` targets behind.
The production bank preflight correctly rejected the stale
`~F1Shim|Nasti2AXI4IdentityModule` target. `ResolveSimulationInline` now checks
every incoming protected definition's circuit, existence, reachability and
uniqueness before running the native pass. At that pass's output, before native
annotation renaming, it retires protection only on definitions actually removed.
The removed module set must match the explicit module/circuit inline selection;
all surviving protection must remain unchanged. Unrelated stale annotations
still reject.

The version-2 immutable inline receipt adds an ordered `no_dedup` history with
each protected module target, original definition hash and retired/preserved
action. Existing circuit/annotation hashes, actual native rename history and
complete concrete register/RAM tracking remain required. The independent Python
audit reconstructs definition hashes from bound input FIRRTL and checks the
complete before/after protection sets, including coherently rehashed changes
that drop surviving protection or revive a removed target. Historical version-1
receipts remain historical inputs; they are not regenerated as current evidence.

Full module and circuit selections preserve all four register/RAM owners in
the repeated-instance fixture. Partial stateless inlining retains protection on
the surviving definition. A separate stateful partial-inline negative exposes
an existing FIRRTL 1.6 tracking alias: surviving `right:Leaf>ram` is renamed to
`right:InlineFixture>left_ram`. The complete state audit rejects this instead
of accepting an incorrect storage mapping. General support for that partial
stateful case remains pending.

The exact Rocket compiler now advances to a different explicit rejection:

```text
Generated checkpoint bank unsupported: XDC target requires an exact ground declaration or concrete instance port: ~F1Shim|F1Shim/top:FPGATop/CPUManagedStreamEngine_0:CPUManagedStreamEngine/TRACERVBRIDGEMODULE_0_to_cpu_stream_outgoingQueueIO_q:Queue_56>ram
```

The underlying preflight stack points to the external
`midas.targetutils.xdc.XDCAnnotation` case. The next increment needs an exact
memory-target contract for the existing `RAMStyleHint` annotation, including
its physical RAM-cell selection after banking and downstream emission. Keep
external/internal annotation identity and repeated-instance correlation; merely
allowing every memory reference would not establish the physical contract.
The three BUFGCE CE-latch owners/common low-phase atomic cut and complete
memory/timing/bridge/host/pre-FAME ownership also remain pending.

All iteration-212 diagnostics, fresh native/VCS evidence, exact runnable commands
and final provenance audit belong under
`automations/checkpoint_loop/runs/aws-f2/iteration212/`. See its `summary.json`,
`remaining-blockers.json` and `verification-commands.json`. Native synthesis is
on this server with Vivado 2025.2; every VCS process runs on EDA with SP2,
`-full64`, `-Mupdate` and debug access. These fixture results establish neither
FPGA-origin checkpoints nor CPU migration. The retained localhost full-build
invocation is still iteration194's `checkpoint-build`; reuse initialized manager
configs and do not create a substitute public-image checkpoint.
