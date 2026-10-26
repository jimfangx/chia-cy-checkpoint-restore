# Reserved widget routes after native inlining

`NativeCheckpointWidgetPeerRouting.inspect(before, after)` follows the twenty
reserved endpoints through the actual native FIRRTL inline result. It requires
the original reservation and the consumed inline history, with exact circuit and
annotation hashes at both phase boundaries. The existing reservation inspector
still validates the original widget, public transport ABI, sentinel parameters
and four inline SystemVerilog sources. The new checker requires that exact
transport definition and those sources after promotion into the original host.

The checker follows FIRRTL nodes and connections; it does not guess flattened
widget names from emitted Verilog. Every source reaches its physical transport
output. Every return route reaches the original annotated endpoint before its
zero placeholder is inspected. Thus two equal zero placeholders cannot conceal
a swapped connection. CE vectors must travel intact. Raw clock and reset routes
are checked separately, with only the existing reset `asUInt` cast permitted.
Missing/multiple drivers, alias loops, non-alias expressions, stale history,
changed endpoint markers, owner order, ABI, identity or source text reject.

This contract currently requires endpoints to remain in their original host and
the physical transport to be promoted into that same host. A future transform
that promotes the host itself needs an explicit extension; ambiguous/shared
host definitions reject. Both the exact pre-inline reservation and post-inline
states must be retained when integrating this checker into the production graft.

The checker emits a routing receipt. It does not replace placeholders, consume
the reserved digest/header, connect a bank graft, or account for opaque transport
state. Ordinary image emission and strict external-owner inventory still reject
the unbound reservation. The next implementation step remains an independently
audited transport state owner, immutable descriptor/driver identity without a
manifest self-reference, and a checked graft connection to these routes. Complete
FASED/DRAM/host/reset/external-writer and pre-FAME ownership remains required
before building a deployable checkpoint image.

`NativeCheckpointWidgetPeerRoutingSpec` loads the actual registered-widget
fixture and native-inline result produced by the retained Scala suite. Its
fault cases rehash the inline history to exercise semantic route checks.
Set `checkpoint.peer.input` to that emitted `reservation/` directory and
`checkpoint.peer.out` to a fresh directory under loop `runs/` when invoking
the test, including from a broader `midas.checkpoint.*` suite. The current
invocation's `scala-peer.sh` records both properties explicitly.
`audit_widget_peer_routing.py` independently reconstructs all routes from the
lowered FIRRTL and checks the receipt against the original reservation. Evidence
and runnable commands belong under `automations/checkpoint_loop/runs/aws-f2/iteration240/`.
These are compiler/component prerequisites; no hardware capture, CPU restore,
finite replay, live clean-RTL comparison or rolling recovery is established.

The three Scala tests pass with fourteen rejection cases. The independent
manager/EDA audit reconstructs **20 pins / 42 connection hops**, binds **21 inputs /
23 sources**, and rejects seven receipt mutations. The original reservation and
the reservation after adding the inline request are distinct phase identities;
both are retained and the auditor requires exactly that one added request.
The initial audit's incorrect phase-hash comparison and its input artifacts are
preserved under iteration 240. Manager/EDA matching passes all 21 inputs and
23 sources. The recovered sweep passes 25 native synthesis and 44 EDA scopes,
retaining the original 256 Scala tests, 313 Python/40 loop tests and sanitizer,
host and FCFS scope. The recovery also replaces a stale graft file count with
exact recursive set/hash equality: the 79 current files omit only two historical
byte-identical XDC aliases; the canonical constraints remain mandatory. The
successful generation log and pinned unchanged source commit remain distinct
from the killed original log. All corrected scripts and original diagnostics
are retained under the current invocation.
