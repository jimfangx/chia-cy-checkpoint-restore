# Transport restore staging

`CheckpointTransportControlRestore.sv` stages the exact `481 + GATES`-bit
layout-v1 transport register vector. It accepts mutually exclusive command
strobes: begin an epoch, write every padded 64-bit word in ascending order,
then commit on a separate edge. The header must match the nonzero compile-time
identity, complete bit/word counts and requested source cycle. CRC32C checks all
padded words; nonzero final padding rejects. CRC is transport integrity, not
authentication or proof of a valid semantic CPU image.

The caller must certify its acknowledged destination cut, quiescent owners and
absence of owner faults throughout loading and apply. The expected source cycle
must stay unchanged. That source label is independent of the destination target
counter, which may itself need restoration. Header and data buses can change
after acceptance without changing the retained image.

Commit offers the complete vector and source label through a backpressured
apply interface. Every current owner, cycle or command fault suppresses
`apply_valid` combinationally before an accepting edge. Invalid outputs are zero.
The first apply handshake produces exactly one `applied` pulse and consumes the
epoch. Explicit abort retirement or reset is necessary before another epoch.
Abort/reset invalidate even a ready-to-apply offer immediately. Errors are sticky
until reset; abort cannot forgive faults or conceal simultaneous illegal commands.

The component does **not** write the production transport's physical registers.
The falling-edge mask, stream/MMIO obligations, raw control state, physical clock
gates, shadow storage, host owners, complete state validation and common-cut
release still need a destination adapter. No production widget, compiler owner,
image-emission guard or driver binding is changed. Its native fixture identity
is diagnostic, not a generated production manifest. Full-image P&R/AFI and actual
F2 capture/migration acceptance remain pending.

`verify_transport_control_restore.py` synthesizes locally with native Vivado and
runs VCS only on EDA. Native auditing enumerates every sequential cell and
requires the exact eight-field register partition on the raw positive clock.
The VCS oracle distinguishes every offered bit, independently computes CRC by
bytes, stalls loading/apply, checks order/identity/owner/cycle/padding/truncation/
CRC faults and cancellation after partial or complete loading. Gate counts 1,
3, 31 and 65 cover partial words, a full final word and multiword gate masks.
Invalid counts 0/65536 and a zero identity reject. A separately compiled data
mutation must stop before its first apply acknowledgement. Full-visibility waves
and original remote paths are retained with source-bound receipts under
`automations/checkpoint_loop/runs/aws-f2/iteration245/`.
