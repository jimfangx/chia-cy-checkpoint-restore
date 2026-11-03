# Atomic regional cut-control staging

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
