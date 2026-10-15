# Explicit TSI memif write child

Iteration 124 adds an explicit identity dispatch caller and atomic preparation
of its caller/write/FIFO group. See
[tsi-bcd-identity.md](tsi-bcd-identity.md). The parent HTIF polling caller and
prepared ten-owner contract still exclude active unaligned identity dispatch;
complete CPU continuation remains pending. The iteration-123 record below
describes the earlier child-only boundary.

Iteration 123 adds `firesim_tsi_memif_write_t` and routes ordinary BCD identity
writes through it. Complete Rocket Level-1 and Level-2 acceptance remains
pending. Prepared polling still rejects unaligned identity before clearing
tohost: reconstructing its dispatch caller is separate work.

The owner implements the installed FESVR `memif_t::write` order for FireSim's
eight-byte alignment and 1024-byte maximum chunk: head read/merge/write, tail
read/merge/write, then aligned body writes. Zero body data produces the same
write packets as installed HTIF's `clear_chunk`. It copies its input and keeps
the complete payload, original address, body cursor, phase and nested serial
read image, including every received word. Merge bytes are encoded explicitly
in little endian. No source pointer, destination buffer or saved coroutine
stack is serialized. The serial FIFOs remain a separate owner.

The image binds schema `firesim.tsi.memif-write.v1`, alignment, chunk limit and
one MiB payload bound. Parsing checks all sizes before slicing, validates the
nested reader and its address/length against the head/tail phase, and constructs
a complete candidate before a nonthrowing publication. Unsupported lengths and
wrapping address ranges reject. Active, interrupted and escaping service calls
cannot publish or restore a checkpoint. Read/merge completion cannot consume a
response twice or reissue an already pending request.

The production adapter retains ordinary cache-flush packet order. Context
switches occur only after the explicit child returns blocked. Inspection of an
ordinary polling cut and preparation of startup metadata require an idle write
child; active device dispatch is excluded. Existing ten-owner polling images
therefore retain their schemas. A separately inspected write image does not
authorize restoration of its device caller, HTIF context, syscall descriptors,
signals or exit/stop state. Other syscall/memif callers still use installed
memif and are unowned. No CPU checkpoint profile is enabled.
Cache-flush configuration still belongs to the program-loader owner; common
build/workload/cut identity and atomic preparation across all owners must be
validated by the future aggregate contract.

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration123/`.
Exact selected results and native commands are recorded in the iteration
manifest and [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

The write/FIFO suite independently builds every expected image byte and expands
the installed head/tail/body algorithm into explicit handshakes. A separate
reference invokes the unchanged installed `libfesvr.a` memif implementation and
checks every read/write transaction plus payload and neighboring sentinel bytes.
The cases cover all eight address residues, partial headers/data, partial reads,
repeated blocked service, zero-length and all-zero writes, lengths around eight
and 1024 bytes, and multiple aligned chunks. Native ASan/UBSan and VCS producers
finish before fresh destinations restore at every retained operation cut, in
all four backend pairings. Every complete child/FIFO byte is read back before
service and after every operation. Maximum-length and hostile service checks
are separate from these retained cuts.

`memif-write/invocation-nvr50hp8/summary.json` passes 19 scenarios and all 404
cuts: 1,616 fresh continuations, 325,624 operations and 654,480 complete owner
readbacks. All 28 separate malformed/incompatible/missing-owner processes
preserve both existing peers. Native and VCS each pass 554 additional atomic,
hostile-service and maximum-size checks. Twelve accepted semantic corruption
cases cover all four backend pairings. A changed preserved head byte first
differs at operation 19, request word 2, expected 2,272,551,317 versus actual
2,272,551,316. Changing the pending payload byte instead produces 2,272,551,061
at the same boundary. Changing a queued command first differs at operation 18,
word 0, expected 1 versus actual 0. Every divergent word remains unconsumed.

`memif-mutations-v2/summary.json` additionally detects both skipping the tail
merge and removing the nested-reader address relationship in native and VCS.
Only diagnostic header copies are mutated; production sources stay unchanged.
Earlier missing-include and static-archive link-order pilots are preserved in
`diagnostic-pilots.json` and excluded from passing evidence.

A second suite drives all four BCD identity selectors at all eight address
residues through actual ordinary HTIF/TestChip/FireSim execution, with cache
flushing both disabled and enabled. It independently checks all sampled child
and FIFO images, rejects polling inspection during active dispatch, completes
the source HTIF process, then restores every active sampled child/FIFO pair in
fresh native and VCS processes before any service. These child readbacks do not
resume the original HTIF caller. Neither suite labels host operations as CPU
target cycles.

`actual-identity/invocation-wvw9dhbn/summary.json` passes all 128 ordinary
identity commands and 2,892 sampled component cuts. All 1,344 active samples
reject ordinary polling-cut admission. After the four source processes finish,
2,688 fresh child/FIFO preparations in all backend pairings read back all 5,376
complete owner images before any service. The ELF is the retained host-loader
test input, not a self-checking CPU workload; these results establish only the
production write child and inspection guard.

Repeat from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_memif_write_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration123-controller-rechecks/memif-write
python -m tools.checkpoint_formats.tests.verify_tsi_memif_identity_fesvr_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration123-controller-rechecks/actual-identity
```

Each checker also accepts `--audit /absolute/path/to/summary.json` for independent
read-only checking of its sealed artifacts, byte oracle and native commands.

Next: integrate the write child into an explicit resumable device-dispatch
caller and the atomic preparation contract, preserving the existing fail-closed
prepared boundary until all new owners are represented. General syscall/memif
callers, file descriptors, signals, stop/exit and the complete simulator contract
remain required before fresh complete Rocket continuation. Coherent semantic
CPU capture and finite ordinary RTL replay also remain pending.
