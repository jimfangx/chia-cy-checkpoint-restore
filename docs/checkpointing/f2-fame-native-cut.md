# FAME native banks under a staged local cut

Iteration 9791 recovers the unfinished native composition in
`FAMEClockCutWiring.generateNative`. It connects the existing all-domain FAME
consistency witness and selected applied-edge label to native functional banks
through `F2NativeCollectorSnapshot`. Ordinary generation and its admission
guards remain in force. This API currently constructs a verification sibling;
the production compiler/ONE-widget image does not install this composition.

Before a functional bank opens, the running raw-clock staging owner samples
the collector and the complete idle response endpoint at the same pre-edge.
The component has thirteen original register entries, including all eight
stored FAME roles and both pending-token flags. The staged vector contains
81 collector bits and 66 endpoint bits; its separate payload/occupancy/cycle/error
owner has 218 bits. The local FAME witness itself adds no registers. Native
physical CE latches remain a separate unsupported restore owner.

Independent regeneration compares circuits, forms, annotations, actual rename
mappings, bank entries/bindings, witness provenance, both collectors and their
original reset audits. It
cannot use case-class equality for independently generated mutable FIRRTL
rename-map objects. The caller consumes the emitter request before banking,
as the existing native probe does; unknown storage annotations still reject.
Tests retain prepared emitter connectors, original StateIDs and negative cases
for altered staging, banks and coherently rehashed wiring.

Native Vivado 2025.2 synthesis on this manager passes and retains all 321 FAME
observer bits: 723 LUTs, 707 registers and three BUFGCEs. This is unplaced
component synthesis; no implementation timing closure or AFI is established.
The fresh EDA SP2 process suite passes sixteen cases and retains sixteen full
debug VCDs. At four component cuts (applied labels 33, 88, 167 and 251), the
bench reads all thirteen original entries through the generated bank interface,
checks all staged words and padding before access, and withdraws the host
request during held responses. The independent raw-wave auditor reconstructs
the FAME progression from original handshakes/native edges, verifies pre-edge
staging and each bank response before acknowledgement, and reports 52 reads /
52 acknowledgements, 260 backpressure samples and 512 healthy host steps.
Every entry is tied to a single outstanding request and acknowledged exactly
once per cut; all original entries, including the three fired flags, must
remain equal to their staging baseline through release. Thirteen directed
auditor tests reject missing/repeated selectors, unsolicited/duplicate
acknowledgements, original-state drift and corrupt responses. A separate VCS
fired-flag corruption case stops before its first bank-read acknowledgement.
The audit retains 323 real readback-checker mutations and 261 local predicate
fault trials. Premature borrowing, missing owners during a pending response and
release while busy reject without acknowledging that response. Deliberate
semantic corruption still stops at host step 17 with sixteen comparisons
acknowledged. All initialization/deposits are component testbench operations.

Evidence, original failed attempts, source hashes and replayable drivers are
under `automations/checkpoint_loop/runs/aws-f2/iteration9791/`. The new commands,
from the Chipyard root, are:

```bash
# f2 backend, in the manager environment
bash -c 'python3 automations/checkpoint_loop/runs/aws-f2/iteration9791/run-focused.py'
bash -c 'python3 automations/checkpoint_loop/runs/aws-f2/iteration9791/run-fame-native.py vivado'
# eda backend only
bash -lc 'export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"; source automations/checkpoint_loop/vcs-env.sh && python3 automations/checkpoint_loop/runs/aws-f2/iteration9791/run-fame-native.py vcs'
```

Selections name immutable attempt receipts and preserve their original local
or EDA paths. The initialized manager inputs and both read-only plans are
hash-protected. The retained localhost build invocation is still iteration 194.
The current AWS/native/localhost preflight passes; no loop-tagged run host is
active at entry. Account-owned AFIs are inventoried without asserting loop or
checkpoint compatibility.

Complete closure passes all 391 Scala tests / 60 suites, sixteen preparation
checks, 58 focused and 69 manager tests, 422 Python tests and the retained
native/EDA staging/readout/bank/shell/transport, host sanitizer, FCFS and cut
scope. The final audit binds 2,085 current source hashes and twelve matching
fixture sets; `final-audit-selected.json` selects its immutable receipt.
Historical storage-sharing evidence retains its original paths and observation
date and passes fresh file-identity/capacity checks. No native build or scoped
F2 runtime remains active at closure. The managed review is completed and all
findings are integrated; no delegated LLM work remains active.

Complete production CE/FASED, channel, memory, bridge and host ownership,
production MMIO/DMA/epoch attachment and complete restore remain required.
So do full localhost image P&R/AFI, identified four-hart FPGA execution, actual
early/warm/outstanding/late FPGA captures, independent paired zero-edge
readback, FPGA-reference continuation, finite replay, sustained live RTL and
rolling hardware recovery. All complete/deployable/global/restore flags stay
false. No component snapshot in this iteration establishes hardware capture
or CPU migration acceptance.
