# FAME witness qualification of an existing transport

Iteration 9792 extracts `FAMEClockCutWiring.generateWitness` from the native-bank
composition. It exposes the existing all-domain consistency predicate and one
explicit domain's applied-edge count without adding storage, gates or a cut
controller. The exact-inventory overload still authenticates its complete
manifest and physical clock plan. The role-only overload permits an enclosing
opaque transport, whose state remains independently unsupported.

`FAMEClockCutTransportWiring.connect` attaches that witness to one existing
physical or native capture transport using a rooted compiler `InstanceTarget`.
It replaces the transport's old target-cycle input with the applied-edge count.
For one explicitly selected owner, present and frozen become their original
independent input AND consistency; error becomes its original input OR invalid.
Every other owner bit and all original storage are preserved. The witness
therefore cannot supply an absent acknowledgement. No second collector,
transport, epoch or clock-cut authority is instantiated.

The binding validates every hierarchy hop, a unique concrete execution at each
routing ancestor, the complete public transport ABI, parameters and exact
inline resource bytes. The actual transport and FAME observer must share a
proven raw root clock. All owner vectors must trace through transparent
wire/node aliases to distinct explicit root inputs; constants, sequential
aliases, alias cycles and hidden ancestor tieoffs reject. Existing widget owner
ordering must match when its execution annotation exists. Otherwise the receipt
explicitly records caller-supplied ordering without independent ownership.
Independent regeneration rejects coherently rehashed changed wiring, metadata
and actual rename maps. Repeated attachment rejects.

This is an explicit compiler API tested with the real Chisel physical/native
blackboxes at root and nested locations. The ordinary production pipeline does
not yet select/install it. The new tests qualify the transport's actual inputs;
they do not install a complete physical clock/bank network or run a capture
transaction. Existing transport/component regressions remain separate.

The complete Scala suite passes 397 tests / 62 suites plus sixteen preparation
checks. All four current-source native Vivado 2025.2 profiles retain the 321
original FAME observer bits and both original BUFGCEs. Unplaced component
synthesis uses the following resources; full-image timing is unproven:

| Existing transport / location | LUTs | Registers |
| --- | ---: | ---: |
| Physical / root | 2,221 | 826 |
| Physical / nested | 2,221 | 826 |
| Native / root | 2,748 | 1,169 |
| Native / nested | 2,749 | 1,169 |

Fresh source/compiler/native-bound EDA SP2 passes eight attachment cases, with
eight full debug waves. Each healthy profile independently audits 512 active
host steps, all 512 owner-input combinations and 177 backpressure stalls.
Actual counter corruption stops at host step 17 with sixteen acknowledgements;
the auditor scans through EOF, rejecting later edges/acknowledgements and state
repair. The retained FAME cut and native-bank suites add 28 passing fresh
processes / waves. The independent retained Python/host-ASan/UBSan/bank/FCFS/cut
scope passes all 422 Python tests; all 69 manager tests also pass.

From the Chipyard root, the replayable manager driver is
`python3 automations/checkpoint_loop/runs/aws-f2/iteration9792/run-native.py`.
On EDA, source `automations/checkpoint_loop/vcs-env.sh` last, then run
`python3 automations/checkpoint_loop/runs/aws-f2/iteration9792/run-eda.py`.
Their exact tool argv, current source/compiler/native hashes, immutable
attempts and original local/remote paths remain in the selected receipts.

Diagnostic evidence and raw commands belong under
`automations/checkpoint_loop/runs/aws-f2/iteration9792/`. Current execution and
final source/resource closure are recorded there and in `progress.md`; original
failed fixture attempts remain immutable. All VCS work runs on EDA with SP2,
`-full64`, debug visibility and `vcs-env.sh` sourced last. Native synthesis runs
on the manager after the large Scala compiler exits.

Production selection, atomic transport/stream/host ownership, physical CE/FASED
and common-cut/reset bindings, functional memory and complete semantic mapping
remain pending. So do complete restore, localhost full-image P&R/AFI, identified
four-hart F2 workload/captures at all four active cuts, paired zero-edge CPU
migration, finite replay, sustained live RTL beyond the recorded window and
rolling hardware recovery. All complete/deployable/global/restore flags stay
false. No component artifact here establishes FPGA capture or CPU acceptance.

Iteration 9793 adds an explicit shared-compiler selector for this attachment;
see [f2-fame-compiler-selection.md](f2-fame-compiler-selection.md). Its actual
registered-widget tests also repair saved-owner alias declaration ordering.
The default Rocket recipe still has no production checkpoint owner binding;
this later compiler path does not establish physical capture acceptance.
