# M4 functional-memory owner — iteration 10

M4 remains in progress. This increment implements the metasim memory owner's
save/validate/load hooks and verifies its continuation in fresh VCS processes.
The whole FireSim runtime still rejects checkpoint requests; it has no certified
atomic cut or complete fresh-process loader. No external dependency is missing.

`mm_t` inherits the default-unsupported `checkpoint_owner_t` contract.
Only the audited final `mm_magic_t` implements `firesim.mm_magic.full.v1`.
Its deterministic little-endian owner payload contains:

- Full backing-memory bytes, including untouched locations; exact AXI ID,
  address and data widths, memory size and line size bind the geometry.
- The active write burst's flag, address, ID, beat size and remaining count.
- Every pending write response ID in FIFO order.
- Every pending read response's ID, saved data and last flag in FIFO order.
  These bytes may differ from the current backing memory after later writes.
- The model cycle counter and idle read-data buffer.

There are no pointer values, object padding, partial memory snapshots, drains,
MMIO operations, or clock advances in these hooks. Constructor initialization
makes previously indeterminate counter/dormant burst fields deterministic.
The existing reset behavior is preserved: response queues and the cycle counter
reset, while an accepted partial write burst remains active.

Validation rejects uninitialized/unsupported geometry, schema/version/geometry
mismatches, invalid Booleans, IDs, beat sizes and outstanding counts, impossible
queue lengths, incomplete final read bursts, truncation and trailing bytes.
Load parses and allocates all queue storage before changing backing memory;
rejected loads leave the entire memory owner unchanged. Supported checkpoint
beat widths are powers of two from 4 through 64 bytes. Memory size must contain
whole beats. The payload is an owner section, **not a `.fsckpt`**: integrity,
build identity, owner membership, cross-owner validation and the coherent cut
must be supplied by the future coordinator. Calling these hooks concurrently
with either metasim context is unsupported.

`verify_memory_checkpoint_vcs` exercises the actual production `mm.cc` with
ASan/UBSan and through a VCS DPI clock bench. Four beat widths (4/8/32/64 bytes)
and eight cuts (0/4/8/12/17/20/26/36 model edges) give 64 fresh continuations
and 1,704 compared edges, half in VCS. An independent Python byte/AXI scoreboard
checks every captured field, all 4,096 backing-memory bytes and every AXI output
at each edge. Tests include outstanding bursts, partial strobes, narrow writes,
held read responses, multiple queued write responses, and reset with a pending
write. Restore verifies the complete serialized owner before the first edge;
each final owner is byte-identical to the uninterrupted reference.

Per width, native negative checks reject 4,433/4,473/4,713/5,033 payloads,
including every truncated prefix, malformed fields and incompatible initialized
owners. Each rejected validation/load leaves the owner byte-identical. All
unaudited base-memory hooks and uninitialized restoration reject explicitly.
The 64-byte test exposed a pre-existing 32-bit shift in the write strobe mask;
the mask now uses a 64-bit operand, with sanitizer and oracle coverage.

VCS's external-C build cache retained objects compiled against the earlier
memory header. The M2/M3/M4 verification scripts now inspect recorded `.d`
dependencies and invalidate only stale generated objects, recording the exact
objects and newer dependencies. Actual `simif_emul.cc` and
`simif_emul_all.cc` recompilation is recorded in the M4 build log. This prevents
a passing run with a stale driver ABI.

All 22 Python and 19 Scala tests pass. The initial Scala run failed because its
artifact directory did not exist; creating that directory and rerunning all
four suites passed without skips. Compiler codec/corruption checks and ordinary
clean InventoryDUT VCS pass. Full M2 retains five fresh processes, 108 samples,
1,404 comparisons and mismatch/restore-negative checks. Full M3 retains six
byte-identical captures, 547 stalled boundaries, 5 semantic/242 transfer replay
samples and eight invalid reads. GCD VCS metasim passes after 12 target cycles.
Generated inventory still captures all 539 words at three samples and rejects
preflight/save/restore requests before unsupported-driver initialization.

Reproduce from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_memory_checkpoint_vcs \
  --out automations/checkpoint_loop/runs/m4-iteration10/memory-owner
```

All VCS checks use Y-2026.03-SP1, `-full64` and system GCC/G++ 13. Reused
metasim Make builds use `VCS_FLAGS=-Mupdate`. Diagnostics live under
`automations/checkpoint_loop/runs/m4-iteration10/`; `artifacts.json` records
absolute paths and hashes, and `verification-commands.json` records commands.

Next: inventory/test an actual FASED configuration and connect these memory
owners to the complete runtime inventory. Audit MMIO/stream transport,
harness clocks/reset, scheduler/thread handoff, fuzz PRNG and each driver.
Implement a coherent freeze and manifest/build-bound `.fsckpt`, validate all
owners and RTL handles before any deposit, then restore into fresh VCS metasim
before target time advances. Compare target-visible outputs and memory-response
timing with outstanding traffic. This test bench establishes memory-owner
continuation at model edges; it does not establish FASED timing, target-cycle
equivalence, full Level-1 restart, FPGA, formal or ASIC validation.

The DESSERT off-chip-memory initialization and Strober snapshot/trace sections
were reread from the existing paper text extractions under `runs/m2-iteration7/`.
Level-1 owner payloads remain independent of semantic checkpoints and traces.
No plan correction is proposed. Plans/conda/PDFs were preserved without staging,
commit, reset or cleaning.
