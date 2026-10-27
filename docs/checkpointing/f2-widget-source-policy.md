# Selected-source contracts at the checkpoint widget

`NativeCheckpointWidgetGraft.connectProjected` can now carry supported typed
contracts from the selected source into the enclosing host. The strict
`connect` API retains its original `NoCircuitDedup` restriction. The projected
path requires exactly one source `NoCircuitDedup` policy and independently
reconstructs the source context, banks, identity and graft before consuming
its annotations.

The merge uses FIRRTL's typed circuit rename. Register, RAM, hierarchy and
correlated native-pin constraints keep their translated targets. Historical
deduplication origins remain historical. Source contracts cannot broaden to
executions outside the selected subtree; a circuit-wide inline request rejects.
Global source policies must already exist in the enclosing host. The union is
validated again, so conflicting initialization policies and overlapping RAM
initialization files reject even when each input is individually valid. Host
metadata retains its order and multiplicity. Validation reuses the enclosing
hierarchy within each preflight call; it rebuilds that hierarchy for every new
circuit and retains every concrete target check.

A separate source-policy receipt binds both circuits, original and grafted
source annotations, the host projection, rebased contracts and merged output.
The independent auditor reconstructs the bounded source projection and typed
rebase from the saved original and connected hierarchies, and checks actual
downstream XDC. Native synthesis and EDA verification use the same explicitly
selected source-pinned artifacts. Diagnostic execution history belongs under
`automations/checkpoint_loop/runs/aws-f2/iteration251/`.

The native harness consumes source-local graft constraints in the selected
module/instance scope, then consumes the unified enclosing-host constraints
from the root. It uses `read_xdc -ref` for synthesis and `current_instance` for
implementation, resetting the scope before host constraints and clock audits.
Native/EDA matching reconstructs the exact Tcl and checks scope without
rewriting retained files. The initial native attempt synthesized successfully
but rejected unscoped `network/...` source pins at the enclosing top; that
failure remains intact. No constraint was dropped to repair it.

This supports selected-source storage contracts. Iteration 252 also checks
[source compiler context](f2-widget-source-context.md) against the original and
projected enclosing host without inserting or renaming that context.
Complete production integration, enclosing simulator identity and ownership,
physical CE restore and release,
external writers, functional DRAM, bridge/host owners and pre-FAME capture
remain separate obligations. Sentinel transport identity, guarded host header
and independent image rejection remain active. No checkpoint-enabled full
image, F2 capture or CPU migration is established by this component.

The final iteration-251 scope passes 271 Scala tests across 40 suites plus two
preparation and nine directed executions, 328 Python tests, 40 loop tests,
nine localhost native scopes and nine EDA SP2 scopes. Each connected variant
passes 5,165 checks, four cuts, 136 words and 900 stalls. The source variant
rejects 28 mutations, matches 641 sources / 685 inputs, and retains three full
debug waves. Its native component has 4,570 LUTs, 1,655 registers, three BUFGCEs
and 671 audited raw-clock registers. OOC setup/hold (+0.326/−0.074 ns) has
unconstrained I/O and does not establish timing closure. Final independent
auditing also rejects a coherently rehashed Tcl scope omission. Complete
hardware capture and CPU migration remain pending.
