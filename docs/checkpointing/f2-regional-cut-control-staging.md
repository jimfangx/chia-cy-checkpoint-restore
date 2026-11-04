# Atomic regional cut-control staging

Iteration 9809 routes the authenticated staged selection through
`NativeCheckpointRegionWidgetGraft.connectSnapshot` and
`NativeCheckpointWidgetIdentity.bindRegionSnapshot`. The factory independently
regenerates the attachment before accepting it, then uses that selected circuit
instead of rebuilding an unstaged graft. Seventeen existing transport roles
are connected; physical mask, read permission and captured logical CEs retain
their original controller ownership. Cut and snapshot controls remain explicit
top-level diagnostic ports. The registered transport manifest and executable
host descriptor table receive the same reconstructed identity.

Staged bindings retain the selected circuit, snapshot and all generated-resource
hashes. Every resource is appended exactly once; conflicting enclosing suffixes
reject. The ordinary unstaged binding format remains unchanged. The independent
Python auditor compares every selected driver, original declaration and
definition against the connected circuit, permits only the declared routes and
transport identity change, and checks resources and the executable host table.
The host identity must retain the original registered MMIO/stream allocation;
only the registered header may change during identity binding. A coherently
changed host allocation is included in the fourteen corruption cases.
Qualification commands and failures are retained under
`runs/aws-f2/iteration9809/`; consult progress.md for completed checks.
This factory path has structural/compiler qualification. The separately
retained staged-bank VCS runtime exercises the cut adapter, and does not
establish an end-to-end staged-widget/MMIO execution claim.

Final iteration-9809 qualification passes 443 Scala tests, fourteen independent
binding corruptions and the actual Rocket 2,702-definition / 34-route audit.
The complete native/restore scope and fresh 140-MHz component place/route pass
with 1,972 LUTs / 1,142 registers and +0.727/+0.034-ns setup/hold slack. Complete
current-source EDA retained/component, seventeen raw debug-wave cases / 75
waveform-checker mutations, transferred binding and 6,477-pair storage audits
pass. The closing 53-receipt audit is recorded in progress.md. No descriptor
coverage, image admission, physical capture or CPU migration status advances.

This does not own the readout/router response pipelines, the separate staging
owner or their destination restore. Next supply complete observation and held
restore for the shared router, each physical router, native functional reader
and CE response endpoint; wire staging and physical-controller/pending restore
before claiming complete destination state. Production MMIO cut controls,
functional memory, external writers, host owners and target-time authority also
remain pending. The exact recipe's diagnostic test overlay still forces absent
owners and cycle zero; it cannot capture workload execution. Full-image guards
remain mandatory, including when annotations are stripped. No hardware or CPU
migration acceptance follows from this factory connection.

The next owner inventory must derive widths and multiplicities from the actual
generated network, including inactive response payloads whose values survive
after occupancy clears:

| Owner | Sequential state | Current gap |
| --- | --- | --- |
| Shared region router | `pending`, `invalid`, `owner` | [Opt-in observation/held restore component](f2-regional-router-restore.md); production attachment/staging still pending |
| Each physical router | `pending`, `selected_ce` | [Opt-in complete observation/held restore component](f2-physical-router-restore.md); production attachment/staging still pending |
| Each functional reader endpoint | `ckpt_pending`, `ckpt_saved_data`, `ckpt_saved_error` | Reader state changes during checkpoint reads |
| Each CE response endpoint | `response_valid`, `response_data`, `response_error` | Response state changes during checkpoint reads |
| Physical controller and accepted-request tracking | Positive/negative-edge controller state and pending bit | Restore disabled and tied low |
| Cut-control staging | Payload, occupancy, cut cycle and sticky errors | Whole-owner restore disabled and tied low |

Freezing or restoring only the semantic DUT does not establish ownership of
these raw-clock pipelines. A destination must hold every relevant owner until
complete independent readback, before releasing either physical or target time.

Iteration 9808 adds the explicit compiler option
`--simulator-native-region-cut-snapshot-probe OWNER[,OWNER...]`, subordinate to
one `--simulator-native-region-compiler-probe` selection. Owner names preserve
the physical acknowledgement-bit order; they do not establish ownership.
Empty, duplicate, malformed or multiple requests, local shells and concurrent
register-snapshot requests reject. The request must remain identical across
the actual inline boundary.

The regional compiler now selects the staged circuit itself and retains the
parent cut, graft and snapshot bindings, original/attached FIRRTL, annotation
history and every emitted resource. It returns before ordinary widget binding,
which would regenerate an unstaged graft. This explicit diagnostic still has
unconnected snapshot control ports; MMIO/host integration, router/staging
restore, external writers, functional memory and target-time ownership remain
unsupported. Resource annotations are appended to the returned state after its
FIRRTL/annotation snapshots; the separately saved resources are hash-bound.
The unchanged reservation and physical-owner guards reject image emission,
including after annotations are stripped. No deployable-image or physical
capture claim follows from this compiler selection. Qualification commands and
attempts are under `runs/aws-f2/iteration9808/`; consult progress.md for results.

Fresh exact Rocket selection passes an independent audit of 2,701 original
definitions and 33 adapter routes, with 74 control bits and a separate 145-bit
staging owner. All 10,916 descriptors / 1,245 unadmitted functional entries
remain, and the actual compiler rejects the unbound lowered readout/image.
The separate four-gate fixture passes current-source native OOC place/route at
140 MHz (+0.727/+0.034-ns setup/hold), seventeen EDA SP2 cases and all 75
waveform-checker mutations. The complete retained/component and storage scopes
pass; the closing receipt is `iteration9808/increment-audit-hmxg3y6o/summary.json`
under loop `runs/aws-f2/`. This does not establish complete image ownership,
an AFI, physical F2 capture or CPU migration/live/rolling acceptance.

`CheckpointRegionCutSnapshot.sv` connects the existing generated regional
common-cut controller to atomic control-state staging. The controller remains
the only clock authority. This is a bounded synthesizable adapter; production
Rocket installation and complete checkpoint-image admission remain pending.

Connect `live_control_state` to the generated `capture_cut_control_state` and
`source_pending` to `capture_cut_pending`. The complete vector has `GATES + 71`
bits: the physical controller's mask, sample/release flags, captured logical
CEs, cut cycle and sticky errors, followed by the accepted-request pending bit.
The adapter uses the same running raw clock and reset as the source controller.
Every bank request/response handshake passes through its permission gates.

The caller first asserts the host freeze request and waits for physical read
permission. Only then may it request staging, with the reader idle and no bank
request present. Staging copies the complete pre-edge control vector before
any bank acceptance. Its payload has a separate two-word serial port for the
four-gate fixture, including checked zero padding and invalid-address errors.
The additional whole staging owner includes payload, occupancy, cut cycle and
six sticky errors: 146 bits for that fixture's 75-bit source vector.

Occupied staging holds the original common cut through host withdrawal and
response backpressure. Host withdrawal blocks new requests while permitting an
accepted response to drain. Explicit idle snapshot release revokes permission
before its edge; the source controller subsequently releases on its existing
registered common-low-phase protocol. A new fault revokes both handshake
directions combinationally. Inputs obey the raw source-clock contract: retain
the offending control through its detecting edge to latch a sticky error.
Occupied or error-bearing epochs cannot release the cut by host withdrawal.

The adapter exposes its staging owner independently; destination restore is
disabled. It does not capture bank/router payload, functional memory, external
writers, host owners or pre-FAME semantic state. These owners, complete target
time, production MMIO/DMA installation and state admission still require their
own generated bindings. No complete FPGA or CPU migration flag is granted.

The verifier attaches the adapter to the retained, independently audited
compiler-generated regional circuit. It authenticates original compiler,
source, descriptor and native receipts, preserves original executions/gates,
and checks every staging register's raw clock in native Vivado. EDA VCS uses
those exact native inputs and vendor models, an independent functional oracle,
full debug waves and an independent pre-edge register/serial-word auditor.
It also compiles a separate staging-input bit corruption with an unchanged
oracle, and checks that the first divergent control vector receives no bank
acknowledgement. This remains component corruption evidence.

The final localhost Vivado OOC component has 2,301 LUTs, 1,142 registers and
six original BUFGCEs. All 75 payload bits and all 146 staging registers survive,
with their clocks independently checked against the raw source. At 140 MHz
the unplaced setup/hold estimates are -0.043/-0.074 ns. These results establish
neither timing closure nor full-image implementation or achieved FPGA Fmax.

Subsequent native OOC place/route passes at the unchanged 140 MHz constraint:
1,964 LUTs / 1,142 registers, setup/hold +0.911/+0.044 ns, all 3,124 routable nets
fully routed, zero routing errors and no DRC checks found. The implemented DCP
retains all 75 payload bits, all 146 staging registers on the raw clock and six
original SYNC BUFGCEs. This closes component timing; full-image timing, AFI
creation and physical FPGA acceptance remain pending. Both original unplaced
reports and the separate implemented reports/checkpoint remain retained.

Final source/native-bound EDA SP2 qualification passes seventeen fresh cases,
retaining seventeen full debug waves. The independent auditor reconstructs five
snapshots at component cuts 37/66/102/145/195: four complete captures/releases
and a fifth explicitly cancelled by shared reset. Healthy execution checks 280
bank words, 285 requests / 284 responses and 64 withdrawal/backpressure edges.
The separately compiled input corruption first differs on
`captured_control_state` at component cycle 37 (expected 4811, observed 4810),
with zero bank requests or responses acknowledged. All 75 payload-bit checker
mutations reject. These labels belong to the directed component fixture.

Iteration-9806 attempts and selected receipts are under
`automations/checkpoint_loop/runs/aws-f2/iteration9806/`. Replayable entry points
from the Chipyard root are:

```bash
# f2 backend, initialized manager/native environment
bash -c 'python3 automations/checkpoint_loop/runs/aws-f2/iteration9806/run-control-snapshot.py vivado'
# eda backend only
bash -lc 'export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"; source automations/checkpoint_loop/vcs-env.sh && python3 automations/checkpoint_loop/runs/aws-f2/iteration9806/run-control-snapshot.py vcs'
# f2 backend, after EDA evidence returns
bash -c 'python3 automations/checkpoint_loop/runs/aws-f2/iteration9806/run-control-snapshot.py audit'
```

Consult `progress.md` for completed checks. Preserve failed attempts separately
from the final source-bound qualification. The strict exact-Rocket physical
CE-owner refusal remains in force; full localhost image P&R/AFI, actual F2 cuts,
paired CPU restores, finite replay, sustained live RTL and rolling hardware
recovery remain pending.


Iteration 9807 adds `NativeCheckpointRegionCutSnapshot.generate`: an opt-in
compiler attachment that regenerates the original regional cut, installs the
staging adapter on its proven raw clock and shared reset, and interposes all
six bank-handshake/data directions and the freeze request. The original
physical controller remains the sole clock authority; its accepted-request
pending register now observes the qualified inner handshake. Twelve explicit
`capture_snapshot_*` ports expose staging request/release, serial readout and
complete control/staging vectors. Physical `capture_read_enable` retains its
original meaning; callers must also honor snapshot validity/failure.

The binding authenticates the parent cut, attached FIRRTL, adapter declaration
and both emitted RTL resources. Regeneration validation and an independent
FIRRTL audit retain every original definition, execution, state owner and
connection. Ten coherent corruption cases cover raw clock, shared reset,
pending, payload, request/response/freeze bypass, admission and resource
integrity. The native/VCS verifier can now consume this actual compiler
attachment with its unchanged public functional oracle and raw-wave auditor.

This attachment observes only the controller/pending vector. It does not
admit the readout/router, separate staging owner, functional memory, host
owners, target-time authority or complete simulator/semantic state. Production
Rocket pipeline selection, whole-owner destination restore, full-image
implementation/AFI and actual F2 capture remain pending. Qualification attempts,
commands and selections belong under `runs/aws-f2/iteration9807/`; consult
progress.md for completed results.

The iteration-9807 compiler-installed component passes fresh localhost native
synthesis with 2,301 LUTs / 1,142 registers and OOC place/route with 1,972 LUTs /
1,142 registers. All 75 payload bits, all 146 staging registers on the raw clock
and all six retained BUFGCEs survive. At the unchanged 140-MHz constraint,
setup/hold slack is +0.727/+0.034 ns; all 3,123 routable nets are routed, with
zero routing errors and no DRC findings. This establishes component timing;
full-image timing, AFI creation and physical capture remain pending.

Fresh source/native-bound EDA SP2 qualification of this compiler-installed
variant passes seventeen directed cases and all 75 independent waveform-checker
mutations, retaining seventeen full debug waves. The independent auditor
reconstructs five component snapshots at cuts 37/66/102/145/195, four releases
and one shared-reset cancellation, with 285 requests / 284 responses. A real
compiled control-input bit mutation first differs on `captured_control_state`
at component cycle 37 (4811 versus 4810), before any bank acknowledgement.
The complete retained/component regression and storage scopes also pass; see
progress.md and the iteration-9807 closing receipt. These results grant no
production coverage, FPGA capture, CPU restore or live CPU acceptance.
