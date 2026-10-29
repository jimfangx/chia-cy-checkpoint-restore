# Native snapshot staging/control restore

`CheckpointNativeStateSnapshot.sv` has an opt-in `RESTORE_ENABLE` interface for
its complete independent staging/control owner. The default remains
capture-only. The state layout is unchanged: payload at offset zero, then
occupied, 64-bit cut label and six sticky error bits. A released snapshot's
retained payload and label are state too.

The destination asserts `restore_hold` before its first raw edge and parks the
original storage and target clocks. All original owners must be present and
frozen; the borrowed reader must be idle. No capture, release or borrow may
overlap restoration. `restore_ready` qualifies a single raw-clock `restore_load`
transaction, which replaces every register of this owner together. The verifier
uses this synthesized interface without internal hierarchical writes.

Hold revokes snapshot-word and borrow permissions before its edge. A qualified
restore loads donor error bits exactly, including a faulted donor's sticky
diagnostics. Prior destination diagnostics do not prevent an explicit complete
owner load; `restore_ready` describes input safety independently of `failed`.
Invalid loads retain payload, occupied and cut label while recording sticky
control/ownership errors. Reset takes precedence over loading.

After complete independent readback, the caller can withdraw hold only when
the other restored owners are ready. Occupied snapshots then require the live
target label to match their restored cut. Drift or missing owner/freeze revokes
read/borrow permission combinationally before acknowledgement. Healthy snapshots
can finish indexed reads, release and recapture. Restored errors remain sticky
until explicit reset or a complete qualified restore.

`tools/checkpoint_formats/tests/verify_native_snapshot_restore.py` synthesizes
the enabled interface for the F2 part on localhost. Its EDA mode requires that
exact source-bound native receipt and a current emitted-queue capture receipt.
The iteration-273 standalone 1,036-bit payload uses 978 LUTs and retains all
1,107 flip-flops on `xcvu47p-fsvh2892-2-e`. Its utilization, synthesis timing and
DCP are component evidence; they establish no routed full-image Fmax.
Fresh destination processes cover empty, occupied, released and faulted owners,
every original bit in both polarities, unsafe-load rejection, held-state
preservation, serial reads and subsequent component execution. Eight additional
fresh destinations consume four post-read restaging cuts from each of the actual
emitted-queue and gated-wrapper staging regressions. The original pre-borrow
snapshots are also retained verbatim: initially untouched selector registers can
be unknown in VCS. Exported binary donors come from a second atomic snapshot
after legal reads finish, at the same frozen target label, with every word
checked. Unknown or incomplete exported donors reject explicitly; no bits are
masked or initialized through backdoors. An independent VCD auditor reconstructs
state from the four underlying register vectors and checks complete loads,
held/rejected transactions and interface permissions. A compiled restore-bit
fault must stop at first readback before any word acknowledgement.

These are directed component images, not FPGA-produced `.fsckpt` or `.rtlckpt`.
The test has a running raw clock; it does not implement a CPU target clock or
establish live CPU acceptance. All-four-Rocket-queue production ownership,
common physical cut, complete memory/host and pre-FAME capture, image/AFI and
physical capture/migration remain pending. Whole-Rocket and regional admission
guards remain required. Iteration-273 commands, receipts, logs, native reports,
DCP and debug waves belong beneath
`automations/checkpoint_loop/runs/aws-f2/iteration273/`; consult `progress.md`
for completed verification.
