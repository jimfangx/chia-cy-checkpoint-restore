# Retained widget shadow recovery

Iteration 267 adds an explicit host retry for an interrupted MMIO read of the
immutable widget staging bank. `retry_live_widget_shadow(bits)` never starts a
new capture, adopts another session's bank, or resumes the target. The session
is noncopyable and nonmovable so ownership cannot be duplicated accidentally.

Each attempt reads the complete payload from index zero and checks freeze,
errors, stream accounting, target cut, layout/version/width/count, all eight
manifest words, descriptor count, occupied status and staging label before and
after collection. Padding and selector readback must be canonical. A transport
exception retains the original occupied bank and returns no partial result.
Observed invalid state irrevocably revokes retry. A release attempt also revokes
retry before issuing its write because its completion may be ambiguous. Explicit
abort/drain remains the recovery path for those failures and foreign banks are
never discarded. Allocations precede MMIO mutations.

The EDA ASan/UBSan test interrupts every public MMIO operation both before and
after possible acceptance at widths 1169, the three-gate Rocket transport's
1242, and the six-gate component fixture's 1245. It compares the
recovered payload with an uninterrupted reference, verifies one capture and one
release, and forbids publication while failed. It also covers a repeated
interruption and 26 invalid epochs: fourteen early faults and twelve metadata
changes at the final identity check. These include all identity fields, selector
mismatch and corrupt padding; repairing the fake observations cannot re-enable
retry after validation has failed.

The previous iteration's opt-in staging restore is checked separately with
native localhost synthesis and fresh EDA donor/restored processes. Those fixture
images contain all fifty original endpoint/adapter/staging registers. They are
not FPGA-produced `.fsckpt`/`.rtlckpt` images. Production retains absent restore
controls and complete-image admission guards.

Run commands, immutable receipts and preserved development failures belong to
`automations/checkpoint_loop/runs/aws-f2/iteration267/`. The full physical
CE/common-cut, stream/backend/upstream, reset, host, functional-memory and
pre-FAME ownership contracts remain incomplete. Full localhost image P&R/AFI,
checkpoint-enabled F2 deployment, active four-hart cuts, paired hardware-origin
migration, live clean RTL and rolling FPGA recovery remain pending.

The exact remaining production inventory is recorded in
[f2-rocket-owner-deficits.md](f2-rocket-owner-deficits.md).

Native OOC synthesis passes both opt-in staging profiles on localhost Vivado
2025.2. The 32/4, 1169-bit source uses 2,018 LUTs / 1,727 raw positive-clock
flops; the 32/12, six-gate 1245-bit source uses 2,073 LUTs / 1,837 flops.
All 25 retained/current component OOCs pass with at most two native jobs.
The source-policy component retains negative 140 MHz setup/hold estimates of
-0.179/-0.074 ns and unconstrained I/O. Full-image P&R and timing closure remain
unestablished.

Fresh native-bound EDA SP2 processes pass complete independent readback of all
fifty original registers in both profiles, 312 indexed continuation rows and
four semantic/compiled negative processes. The compiled saved-payload mutation
is first visible at canonical bit 759 while held, with no normal edge or
interface acknowledgement. Full retained compiler/Python/manager, sanitizer,
FCFS/atomic-cut and 25 native / 25 EDA component scopes pass. The finite text
images and fixture cut 42 do not establish FPGA-origin or CPU live acceptance.
