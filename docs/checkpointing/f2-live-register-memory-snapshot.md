# Coherent register and asynchronous-memory staging

The opt-in `--simulator-native-register-memory-snapshot-probe` extends the
existing concrete register-subtree diagnostic to bounded asynchronous memories.
It requires the same explicit regional compiler request and selects one concrete
execution. The default register-only option still rejects every memory.

For each selected memory, the transform adds one permanently enabled,
constant-address, zero-latency read port per word. Original readers, writer,
enable, mask, data, address and clock equations remain unchanged. The observed
words, local registers and descendant vectors feed one existing
`CheckpointNativeStateSnapshot`. They are sampled before the same accepting
positive raw-clock edge, including when that edge writes an observed memory.
Original storage continues running while the staging copy is read serially.

Supported memories have scalar UInt/SInt elements, positive depth at most 1,024,
zero read latency, unit write latency, one writer, no readwriter and undefined
read-under-write. Every original memory port must share the checked root clock.
A lowered `validif(enable, clock)` is accepted only after independently resolving
its validity guard to exactly the effective port enable. Other guarded clocks,
unresolved storage, opaque descendants and oversized vectors reject. This is
deliberately bounded observation, not a bulk-DRAM capture strategy.

The version-2 binding retains each original memory StateID, declaration hash,
element width, depth, signedness and flattened vector offset. Address zero
occupies the least significant element of each memory field. No reader state
is added; the staging payload, occupancy, cycle and errors remain a separate
owner. The capture-only mode disables original and staging restore. The explicit
version-3 mode below adds only whole staging-owner destination loading.

The exact Rocket control fabric contains 395 registers and thirteen memories:
408 entries / 1,749 bits, including all fifteen words of the W-route FIFO and
both AW/AR reorder queues. One combined vector uses 28 serial words and a
separate 1,820-bit staging owner. The independent auditor reconstructs original
state, all added memory ports and their pins, vector ordering, clock aliases,
source equations, annotation evidence and staging ABI. It also checks a fresh
original debug oracle with complete register/memory DontTouch annotations.

The component tests exercise a shared-instance signed/masked-memory fixture and
the exact control-fabric definitions. Testbench initialization uses functional
writes. A valid port-zero transaction initializes the original round-robin
arbiter's unreset `lastGrant` before exercising the error port. Original
assertion failures reject even when VCS returns zero. VCS belongs exclusively
on EDA; native Vivado belongs on this manager.
Iteration-9800 commands, raw attempts and qualification receipts are retained
under `automations/checkpoint_loop/runs/aws-f2/iteration9800/`; consult progress.md
for completed checks.

The iteration-9800 localhost Vivado reports retain all 220 / 1,749 staging
payload bits. The signed/masked fixture uses 371 LUTs / 502 registers; the
control-fabric component uses 3,468 LUTs / 3,567 registers. These are unplaced
component results, not implemented full-image resources or achieved Fmax.

This diagnostic does not change production descriptor coverage or permit image
emission. Global target-cut/reset/external-writer ownership, MMIO/DMA attachment,
production original/staging/host restore attachment, complete FAME/FASED/functional-memory/bridge and
pre-FAME ownership, full-image P&R/AFI, actual F2 captures, paired CPU replay/live
continuation and rolling recovery remain required.

## Opt-in whole staging-owner restore

The version-3 generator can expose `restore_hold`, `restore_load`,
`restore_state` and `restore_ready` for the separate staging owner. The actual
compiler diagnostic selects this with
`--simulator-native-register-memory-staging-restore-probe`. Defaults retain the
capture-only ABI. The complete 1,820-bit Rocket owner packs payload, occupancy,
cut-cycle and six sticky errors; released payload and donor errors are retained.
The load uses the running raw clock with hold asserted before the destination's
first edge. Target clocks and all original owners require independent parking,
restoration and readback before complete simulator execution can resume.

The independent auditor checks the explicit version/policy, complete original
state/equations, every restore pin and direction, owner width and native resource.
The component verifier exercises occupied/released/error-bearing whole-owner
patterns, unsafe-input rejection and continued original traffic. Fresh VCS
processes load a retained healthy component staging image on their first raw
edge and read back all bits/serial words before a second edge. A separately
compiled restore-payload mutation must stop before any word acknowledgement;
raw debug waves retain the first divergence. This fresh test holds the original
component in reset and supplies no original-state or CPU migration acceptance.

Iteration-9801 attempts and receipts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration9801/`; see progress.md for
completed verification. Original control-fabric restore, common-cut/transport/
host attachment and every complete-image/physical CPU obligation remain pending.
Production descriptors and image admission are unchanged.

The iteration-9801 restore variants retain all 219 / 1,820 sequential staging
bits in native Vivado. They use 426 LUTs / 432 registers and 4,384 LUTs / 3,569
registers, respectively. These are unplaced component resources, with no full
image timing, P&R or AFI acceptance implied.
