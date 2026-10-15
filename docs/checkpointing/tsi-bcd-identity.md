# Explicit BCD identity caller

Iteration 124 adds `firesim_tsi_bcd_identity_t` between ordinary HTIF device
dispatch and the explicit memif write child. It owns the raw device-1,
command-255 request and the write, response and return cursors. Ordinary
dispatch routes all four identity selectors through this caller, at all eight
address residues. The caller constructs the installed 64-byte identity table,
advances the existing head/tail/body writer, and sends the installed encoded
response exactly once after the write completes. Host context switches occur
only after an explicit blocked result. No `command_t`, callback, input pointer,
buffer pointer or coroutine stack is serialized.

The schema is `firesim.tsi.bcd-identity.v1`; its configuration binds device,
command, identity length, alignment and maximum serial chunk. The independent
write child still owns copied bytes, merge responses and the body cursor; the
serial owner retains both FIFOs. The caller validates the child address and
complete copied payload against its command. Response/return and idle phases
require an idle writer. During a service, reentrant capture/preparation rejects;
an escaping service poisons the caller and prohibits retry or publication.

`load_components()` prepares the ordered `identity`, `write`, `serial` group
using independent candidates. Every parser, allocation and caller/child
relationship check precedes three nonthrowing publications. Missing, extra,
reordered, malformed and incompatible components cannot change an existing
destination. The native and VCS checks inject failure at every allocation in
this transaction and exercise hostile issue, receive, write and response
services. Diagnostic header mutations that skip the response or omit the
caller/child check are detected in both backends.
Cache-flush configuration remains in the program-loader owner. Common
build/workload/cut identity and service configuration must still be checked by
the future aggregate contract; the three-component interface supplies no CPU
checkpoint admission or complete image provenance.

This group does not restore the parent HTIF polling caller or its response
queue. Ordinary active identity dispatch remains excluded from polling-cut
inspection. The prepared ten-owner polling interface continues to accept only
sealed reads, writes and aligned identities; its schema and admission policy
are unchanged. Integrating resumable dispatch with that parent and its atomic
preparation contract remains next. Syscall/file-descriptor, signal, stop/exit,
other memif callers and the complete simulator contract are also pending.
Neither CPU checkpoint level meets acceptance.

The next integration must make the parent dispatch service return a blocked
result before publishing a cut, instead of suspending inside its `void`
callback. Extend the parent phase/child predicates and atomic preparation to
all twelve owners. Three child images captured while that parent callback is
suspended cannot reconstruct the parent stack or authorize continuation.

The new checker expands the installed identity and memif algorithms in Python,
constructing every expected owner byte and operation/response boundary without
calling the C++ serializer. It covers all selectors and residues, partial
packet headers/data, partial merge reads, repeated blocked calls and repeated
completion. Producers finish before fresh native/VCS destinations restore in
all four backend pairings. Every owner is read back before service and after
every operation. Separate processes reject invalid images; preserved head and
tail response bytes and an actual queued command are deliberately corrupted.
The first divergent request word must remain unconsumed. These are host
operation labels, never CPU target-cycle cuts.

The retained invocation `identity/invocation-x4mo5328/summary.json` passes all
32 scenarios, 1,005 cuts and 4,020 fresh continuations: 2,018,040 operations and
6,066,180 complete owner readbacks. All 30 invalid-image processes and twelve
semantic corruptions pass. Native and VCS each pass 486 malformed images,
twelve membership failures, seven phase/relationship failures, all 48 injected
allocation failures and 36 hostile-service guards. The independent invalid
readback audit matches all 90 unchanged destination images. Preserved head and
tail corruption first diverge at operations 63 and 74, request word 2;
queued-command corruption first diverges at operation 62, word 0. None of the
divergent words is consumed. Full details and native argv are sealed in the
iteration artifacts.

The actual HTIF suite independently checks caller/write/FIFO images sampled
from ordinary execution with cache flushing disabled and enabled. Fresh
destinations atomically prepare and read back all three owners after source
HTIF completion. This is component readback, not resumption of the parent HTIF
caller or a CPU.

Run from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_bcd_identity_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration124-controller-rechecks/identity
python -m tools.checkpoint_formats.tests.verify_tsi_memif_identity_fesvr_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration124-controller-rechecks/actual-identity
```

Both checkers accept `--audit /absolute/path/to/summary.json` for independent
artifact, source-binding, byte-oracle and native-command verification. Results
and the exact native VCS commands are indexed in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics remain under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration124/`.
