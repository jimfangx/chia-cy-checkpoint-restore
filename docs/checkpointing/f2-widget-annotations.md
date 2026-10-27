# Typed host annotations at the widget graft

`NativeCheckpointWidgetGraft.connectProjected` projects the bank compiler's
explicit storage annotation contracts against the complete enclosing host.
It follows concrete original executions into specialized bank definitions,
validates the emitted declarations, and retains other host metadata in its
original order. Correlated XDC arguments stay together. Constraints on shared
BUFGCE definitions expand only over their original executions, excluding the
inserted root mask gate. The checked fixture resolves both CE/O pins and applies
`DONT_TOUCH` to their native cell; CE must not be treated as a timing startpoint.
The initial timing-exception fixture was rejected by real Vivado and its log is
retained. The normal downstream XDC pass emits constraints before Verilog emission.

The FPGATop OOC synthesis applies every hierarchy-bound emitted constraint. Its
board-pad placement snippets have no FPGATop ports: their original complete
file remains independently audited, and their hashes are explicitly recorded
as deferred to final F1Shim/image implementation. A separate independently
reconstructed component XDC retains all hierarchy-bound constraints. Deleting
one from that file rejects; OOC evidence cannot establish full-image placement
or timing closure.

Both connector paths reject unsupported targets in the selected source
namespace. An original shared leaf can remain as an unused definition after
its executing instances switch to specialized definitions; its presence must
not allow an unknown state contract to bypass the guard. The original strict
connector still requires explicit projection for typed selected targets.

The projection receipt binds source and connected circuits, complete original
and projected annotations, unchanged host metadata, concrete translation rows,
and invalidated combinational caches. The independent Python auditor rebuilds
the bounded fixture's projection and emitted Tcl from the original and connected
hierarchies. It rejects altered constraints, missing registers, cross-instance
arguments, mask aliases, broadened primitive targets, changed host metadata,
changed scope, incomplete mapping/cache history, and changed Tcl.

This API retains the exact source `NoCircuitDedup` policy and sentinel transport
identity. It supplies neither a complete enclosing simulator manifest nor a
state/freeze/restore adapter. Production source annotations, FASED CE ownership,
global cut/release, DRAM/external writers, bridge/software owners and pre-FAME
state still need implementation. Ordinary image admission continues to reject
the circuit even if all annotations are removed. Hardware capture and paired
CPU migration remain pending.

Iteration-250 execution logs and source-pinned attempts are under
`automations/checkpoint_loop/runs/aws-f2/iteration250/`. Initial failed and
superseded attempts are preserved separately. Complete final verification is
recorded in that invocation's receipt index and verification command list.

The final repaired source passes 269 Scala tests plus two preparation tests,
328 Python tests, 40 loop tests, all eight native scopes and all eight EDA SP2
scopes. Each of the sentinel, bound and projected executions passes 5,165 checks,
four cuts, 136 words and 900 DMA stalls. The bound host initializer passes 20
ASan/UBSan checks. The projection rejects 22 mutations and matches 641 sources /
684 inputs. Its native result uses 4,517 LUTs, 1,646 registers and three BUFGCEs;
662 raw clocks are audited. OOC estimates (+0.326/−0.074 ns) retain unconstrained
I/O and do not establish image timing closure. Independent waveform auditing
retains 2,704 frozen samples and the compiled payload defect at cut 81, word 0,
byte 42 before release. All nine variant waveforms and the initial rejected
native constraint remain under the invocation history. No new FPGA image,
hardware capture or CPU migration is established.
