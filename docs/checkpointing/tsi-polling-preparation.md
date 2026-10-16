# Fresh preparation of known TSI polling components

## Iteration 125: parent identity dispatch returns blocked

Ordinary identity dispatch now unwinds both owner guards before yielding.
Complete parent images are readable at those host boundaries. See
[tsi-polling-dispatch.md](tsi-polling-dispatch.md). The existing prepared
ten-owner admission and aligned identity behavior remain in force; adding
dispatch predicates and atomic twelve-owner preparation is still pending.

## Iteration 124: explicit identity dispatch caller

Ordinary BCD identity dispatch additionally owns its raw command and the
write/response/return cursors. Its independent caller/write/FIFO group prepares
atomically and reconstructs no coroutine or response callback. See
[tsi-bcd-identity.md](tsi-bcd-identity.md). The parent poll caller and response
queue are outside that group; integrating active dispatch into the existing
ten-owner preparation contract remains pending. Existing prepared admission
therefore remains aligned-only. Complete HTIF/CPU continuation stays disabled.

## Iteration 123: ordinary identity write child

Ordinary BCD identity dispatch now uses an explicit copied-payload memif write
owner, including unaligned head/tail reads and merges. See
[tsi-memif-write.md](tsi-memif-write.md) for its independent component boundary
and native/VCS checks. Prepared polling retains its aligned-only admission;
resumable unaligned device dispatch and atomic preparation of its new child
remain pending. The existing ten-owner images still require an idle write
child. Complete HTIF/CPU continuation remains disabled.


## Iteration 122: aligned BCD identity without a suspended memif caller

The prepared caller additionally admits BCD command 255 when its 64-byte
destination is aligned to eight bytes. The BCD identity table still constructs
exactly the installed device's `read`, `write`, `bcd` or empty unknown-command
name, zero-padded to 64 bytes. Ordinary execution retains installed memif writes.
The prepared destination instead binds a non-suspending identity writer to its
own TSI object. It encodes sixteen little-endian words explicitly and enqueues
the entire serial write packet before returning. The response binds the new
poll owner. There is no retained memif buffer, stack pointer or callback from
the producer, and no additional mutable checkpoint state or component schema change.

The ownership argument is deliberately limited: at admitted polling boundaries,
all identity bytes reside in the existing serial FIFO, even if the packet has
been partially consumed. No memif call or target read occurs in this prepared
path. The active caller/device guards prohibit publication during dispatch;
service failure poisons continuation. Unaligned identity requires a suspended
read/modify/write caller and still rejects before tohost's clear is queued.
Syscall, exit/signals and other devices remain unsupported. Full `tick()` and
complete HTIF/CPU restore remain disabled.

Native sanitizer/VCS evidence and exact commands are retained under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration122/`.
The extended byte oracle retains the prior binary terminal/EOF/idle operations
and adds all four identity cases at addresses spanning both serial address
words, including eight-byte alignment without sixteen-byte alignment. It cuts
partial command reads, partial identity packet headers/data and queued response
traffic. Producers finish before fresh destinations prepare. Every component is
read back before service and after every host operation. All seven unaligned
address residues are tested for each identity selector, alongside syscall and
unknown-device rejection. A separate corruption changes the restored identity
packet's first data word and must stop before consuming that divergent word.
These are host-operation labels; no CPU semantic cut or replay is inferred.

`aligned-identity/invocation-iwxxvjyk/summary.json` passes 400 continuations,
19,800 host operations and 202,000 complete owner readbacks. All 132 unowned
command rejections, four external-exit guards and eight first-divergence cases
pass. The identity packet first differs at operation 61, request word 2,
expected 1,684,104,562 versus actual 1,684,104,563; that word stays unconsumed.
Atomic preparation passes 400 preparations, 4,040 complete readbacks, 3,200
malformed, 204 membership and 44 cross-owner/configuration rejections, 2,588
allocation failures and 2,000 execution guards. Native/VCS mutation controls
detect removal of the pre-clear command validation hook.

Repeat from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_continue_vcs --identity \
  --out automations/checkpoint_loop/runs/m11-iteration122-controller-rechecks/aligned-identity
```

## Iteration 121: executable prepared polling components

`advance_prepared_polling_components()` reconstructs the executable polling
caller without constructing a coroutine or invoking `start`, `load_program`,
`reset` or `stop`. It runs until the next serial-read or idle yield. Ordinary
execution and this explicit component caller share `polling_services_t`, so
partial reads, request issue, cache-flush packets, device dispatch and idle
counts use the same code. Before and after each successful service, the
existing cross-owner predicate checks a supported polling boundary. Prepared
readback still requires an uninitialized host context; `tick()` remains disabled.

Only sealed BCD reads and writes are admitted here. The component caller does
not instantiate the default syscall/device list, execute identity requests
through the unowned memif path, or process an HTIF exit. A command-validation
hook runs immediately after the complete tohost read and before its clear is
queued. Syscall/exit, identity, unknown BCD, disk and unknown-device commands
reject at that point. A failed service poisons the caller and prevents retry or
checkpoint publication. An externally requested HTIF exit rejects before any
service. These restrictions do not establish complete HTIF or CPU ownership.

The native ASan/UBSan and Y-2026.03-SP1 VCS suite passes 224 fresh continuations
at all 56 retained operation cuts in all four producer/destination backend
pairings. Both producers finish before destinations prepare. Every destination
reads all ten images before service, then compares every image after each
operation with both the finished producer and an independent Python byte oracle.
The retained concatenated readbacks cover 6,160 host operations and 63,840
complete owner images, including initial readback. Metadata remains unchanged;
context entry stays disabled at every boundary. These are component operation
labels, not CPU target-cycle labels.

All 24 unowned-command rejections enqueue zero clear packets and preserve the
terminal. Four external-exit guards reject without service. Four deliberate
terminal-cursor corruptions first diverge at operation 21, request word 5:
expected 321, actual 256. The divergent word remains unconsumed. Removing the
pre-clear hook from diagnostic source copies is detected in both native and
VCS execution; production sources are unchanged by this mutation check.

The prerequisite ten-owner preparation suite also passes all 224 fresh
preparations, 2,280 readbacks, 3,200 malformed-image rejections, 204 membership
rejections, 44 cross-owner/configuration rejections, 2,588 allocation failures
and 1,120 execution/preparation guards. Full CPU restore and captured ordinary
RTL replay remain pending. In particular, complete syscall/file-descriptor,
process signal, stop/exit, memif and simulator ownership cannot be inferred
from this restricted caller.

Evidence root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration121/`.
Accepted component evidence is
`polling-continue-final/invocation-er_7mscr/summary.json`; the independent audit
is `polling-continue-independent-audit.json`. The preflight mutation is
`command-preflight-mutation/summary.json`. Source snapshots, complete readbacks,
process IDs and all native argv remain under those directories. Earlier
warning/source-race and diagnostic-import pilots are indexed separately in
`diagnostic-pilots.json` and do not count as accepted evidence.

Run from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_continue_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration121-controller-rechecks/polling-continue
```

Audit retained native commands, source bindings, every complete state image,
negative case and first divergent operation:

```sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_continue_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration121/polling-continue-final/invocation-er_7mscr/summary.json
```

Iteration 120 added `firesim_tsi_t::prepare_polling_components` and
`inspect_prepared_polling_components`. These restore and read back the ten
known polling components in a fresh TSI object after the separate startup
metadata preparation. They do not enable HTIF context or CPU continuation.
Complete Rocket Level-1 and Level-2 acceptance remains pending.

The ordered component list matches `inspect_polling_cut()`:

| Owner | Restored state / required relationship |
| --- | --- |
| `poll` | Poll phase, mailbox command and complete response queue; mailbox addresses come from the prepared ELF metadata |
| `program` | Completed loader and exact loadmem/cache-flush configuration |
| `init` | Completed initialization, configured ordered accesses and MSIP policy |
| `host` | Loaded flags and idle cursor; either ready for a pending read or suspended in idle |
| `read` | Serial-read phase, address, length and every received word; its pending address must match the poll caller |
| `serial` | Every remaining request and response word, including partially consumed packets and queued incoming words |
| `loadmem-read` | Complete image, required to be idle at this supported polling boundary |
| `loadmem-queues` | Complete four-queue image, required to be empty at this boundary |
| `bcd` | Every pending input command; reconstructed callback binds the new poll object |
| `terminal` | Same sealed input configuration, cursor and complete output transcript; no prefix output is emitted |

Preparation requires a pristine, sealed, metadata-prepared destination with no
initialized context, active polling caller, default device list or previous
polling preparation. A live terminal or unsupported configured HTIF path cannot
enter this interface. The same cross-owner predicate now checks the source's
suspended inspection and the destination candidates.

All eight protocol candidates parse and allocate before cross-owner checks.
The bound poll/terminal/BCD transaction then prepares its three replacements
before changing the destination terminal. After that publication, only
nonthrowing state and ownership swaps and the prepared flag assignment remain.
An exception during any preparation leaves the eight pristine destination
peers, metadata and absent poll/BCD owners unchanged. Allocation-failure tests
cover the whole method, including candidate construction, configuration tables,
readback guards, list copies and the final three-owner preparation.

The fresh prepared object can read back all ten components and unchanged
startup metadata. It still rejects `tick()`, suspended-context inspection,
duplicate preparation, initialization-image loading and repeated startup
preparation. Existing initialization restore cannot replace the new state.
The syscall/device list and coroutine are deliberately not constructed here.
Syscall descriptors, process signals, stop/exit state, coherent execution-caller
reconstruction and complete simulator ownership remain required before admission.
Component membership and cross-owner invariants do not establish common CPU-cut
provenance or replace the future aggregate build/image identity contract.

Native ASan/UBSan and VCS DPI tests capture actual installed-FESVR polling
execution at 56 component operation boundaries. They cover partial requests,
queued incoming words, partially completed tohost and fromhost reads, three
idle yields, binary input, output and two pending EOF reads. Both source
processes exit before any destination preparation. An independent Python oracle
constructs every expected byte; it never calls the C++ serializer. All four
producer/destination pairings prepare all ten owners and compare their entire
readbacks before any context entry or target service.

The suite passes 224 fresh preparations, 2,280 complete prepared readbacks,
3,200 malformed/configuration-image rejections, 204 owner-membership rejections,
44 cross-owner/configuration rejections, 2,588 injected allocation failures and
1,120 execution/preparation guards. A diagnostic mutation that loads the terminal
before validating the protocol candidates fails for partial publication. These
are component checks, with no CPU target-cycle labels or resumed CPU execution.

An additional native sanitizer/VCS diagnostic prepares the ten actual Rocket
host-component images retained from iteration 119 at master credits 520,064,
700,032, 900,096 and 3,250,048. Eight fresh processes read back all 80 component
images and reject execution. Startup metadata for this diagnostic is reconstructed
independently from the trusted workload ELF, its complete symbol table and the
exact logged TSI arguments, including `+no_notifier`; it is not captured semantic
CPU state. These enqueue/credit samples still do not certify CPU cut labels.
Evidence is `actual-rocket-preparations-v2/summary.json`; the argument-count
pilot is retained separately. Its executable native commands and source are
retained under the diagnostic root.

`prepared-initialization-guard/summary.json` additionally checks a valid
destination-configured reset-wait initialization image in native sanitizer and
VCS. Both prepared callers reject it and preserve all ten owner images. A
diagnostic mutation removing the prepared-state guard accepts that same image
and is detected. This distinguishes the guard from ordinary format rejection.

Evidence and exact native argv are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration120/`.
The primary invocation is
`polling-prepare/invocation-p95inli2/summary.json`; the mutation is
`polling-prepare-mutation/summary.json`. See the CPU matrix for current workload,
ordinary RTL and preserved regression results.

From the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_prepare_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration120-controller-rechecks/polling-prepare
```

Audit retained native sources, complete byte-oracle readbacks, process identities,
rejections, native commands and environment:

```sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_prepare_vcs --audit \
  automations/checkpoint_loop/runs/m11-iteration120/polling-prepare/invocation-p95inli2/summary.json
```
