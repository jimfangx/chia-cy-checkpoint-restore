# Fresh preparation of known TSI polling components

Iteration 120 adds `firesim_tsi_t::prepare_polling_components` and
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
