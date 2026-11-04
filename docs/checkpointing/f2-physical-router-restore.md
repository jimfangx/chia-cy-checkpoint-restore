# Physical-router state and held restore

Iteration 9811 adds an opt-in synthesized interface to
`CheckpointPhysicalStateRouter.sv`. The two-bit `capture_state` exposes every
original register: `{selected_ce, pending}`. Both inactive selection values are
retained. The interface introduces no new storage. It does not allocate a
production descriptor or cover the selected endpoint's payload or pending state.

`RESTORE_SUPPORTED` defaults to zero. The shared compiler renderer explicitly
ties restore controls/data low and leaves observation/error outputs open before
its existing wildcard connections. Fixture wildcard callers do the same.
Strict attachment audits require those exact tieoffs and reject coherently
rehashed changes. Disabled mode also ignores unknown controls. A caller that enables
restore must hold the router and its endpoints at the same destination cut.
Assert `restore_hold`, then `restore_load` with the complete two-bit vector.
The raw rising edge loads both original registers together. Keep hold asserted,
deassert load and independently read back both bits before releasing hold.
Hold suppresses upstream readiness/response validity and both endpoints'
request validity/response readiness. It preserves the original selection and
pending state even when selectors and endpoint responses change.

After release, a pending response still belongs to its original endpoint.
An unsolicited response from the other endpoint cannot drain it. Inactive
selection bits survive until the next accepted request. Ordinary shared reset
dominates loading. Loading without hold, or with unsupported descriptor
geometry, asserts `restore_error`, blocks all handshakes and preserves both
registers. Error is combinational; the caller must retain the control through
its detecting edge and supply global fault handling. Descriptor lookup remains
independent of transport handshakes.

The directed qualification runs source and destination in separate fresh EDA
SP2 VCS processes. The actual source publishes idle, pending-functional,
inactive-functional, pending-CE and inactive-CE words. The destination audits
all five independently before acknowledging a transaction edge, then exercises
all four ABI encodings, delayed selected responses, unsolicited responses,
backpressure, unheld loading and reset cancellation. Disabled mode drives
unknown restore inputs during real transactions. Descriptor geometries include
the maximum legal entry count and three unsupported configurations. Both
semantic bit corruptions must stop at their first divergent readback with no
acknowledged transaction edge. Full debug VCDs retain individual raw registers.
A separate waveform auditor derives state from accepted transactions and the
source file, checks every handshake and response payload, and rejects per-bit
mutations of its readback checker.

Replayable commands are recorded beneath
`automations/checkpoint_loop/runs/aws-f2/iteration9811/`. Native synthesis runs
on this manager; every VCS compilation/simulation runs on EDA. The entry point
is `python3 -m tools.checkpoint_formats.tests.verify_physical_router_restore`
with `--mode vivado` or `--mode vcs` and `--out` beneath loop `runs/`.
Final qualification passes 443 Scala / 430 Python / 81 manager tests,
six serialized localhost syntheses, sixteen fresh owner-debug waves and the
complete retained EDA sanitizer/FCFS scope. Standalone synthesis retains both
original raw-clock registers with 303 LUTs enabled / 298 disabled. Generated
in-place/widget callers pass 7,101 / 6,482 VCS checks and reject 12 / 17 coherent
attachment corruptions. Physical/regional routing regressions pass 4,912 /
6,155 checks and thirteen evidence substitutions reject. The initial wildcard
caller synthesis failure is preserved; all compiler/native/EDA scopes were
rerun after explicit tieoffs were added to both fixture and actual renderer.
Consult progress.md and the iteration's individual receipts for exact provenance.
This remains component synthesis, without full-image timing/Fmax acceptance.

Production graft and common-cut attachment remain pending. This component
does not own the shared regional router, functional reader/physical endpoint
responses, staging/controller state, functional memory, host/bridge state or
pre-FAME semantic state. Complete localhost image implementation, AFI creation,
physical FPGA checkpoint capture, paired CPU zero-edge restores, finite/live
RTL comparison and rolling hardware recovery remain pending/in_progress.
