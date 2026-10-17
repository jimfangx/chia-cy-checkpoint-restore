# Original-thread access to restricted TSI state

Iteration 153 confines the supported TSI protocol and aggregate entry points to
their constructing OS thread. Previously the original-context check ran only at
coroutine entry: a foreign thread could inspect, prepare or publish protocol
owners before reaching that check. The new guard runs before mutable owner reads
and candidate consumption checks in the twelve-owner polling preparation,
fourteen-owner syscall/direct-exit groups, fifteen-owner outer group and
sixteen-owner context group. It also guards the serial transport, load-memory
transport, host control, memory interface and owner-reference getters.

The process-local guard holds the original thread ID and a weak reference to a
thread-local lifetime token. The lifetime check prevents a later thread with a
recycled ID from gaining the departed creator's access. These resources are
reconstructed in each destination process, never serialized. Existing owner
image schemas and the original coroutine-context check remain in effect.

The new native ASan/UBSan and VCS harness exercises 45 foreign entry operations at
execution and returned-tail boundaries, for 180 fresh processes. It tests valid
and malformed preparation, prepared commits, complete capture and context
continuation, along with the production serial/load-memory and host APIs. The
foreign worker remains parked through complete creator readback and valid retry.
Every rejection must name the thread policy, precede service or context creation,
preserve accessible owner bytes and leave all sixteen restored owner images equal
to an independently executed coroutine oracle. The separate auditor binds the
actual recipe archive, input snapshots, commands, process logs and owner bytes;
missing or duplicate evidence must reject.

The commit cases retain separate valid candidates and retry each exact candidate
on its creator. The twelve-owner candidate uses an ordinary sealed TSI; that API
correctly excludes restricted syscall mode. The fourteen-owner syscall candidate
uses the supported execution cut at both outer boundaries; completed stop/return
requires the larger host/context groups. These are host-operation cuts and do
not establish Rocket target-cycle continuation.

A separate native/VCS lifetime check constructs an owner in a thread, terminates
that creator and creates 64 successive replacement threads per backend. It
requires actual recycled thread IDs and rejects every expired owner while each
new creator retains access. All 128 recycled-ID attempts pass. Its exact sources,
commands and logs are retained under the iteration's `lifetime/` diagnostic root.

This confines supported TSI entries; it does not suspend foreign VCS threads,
coordinate process-wide signal masks/actions/lifetimes or prevent arbitrary
access through inherited HTIF APIs or previously retained raw owner references.
Independent lifecycle/signal component APIs retain their explicit exclusive
suspension contract. No process-wide production exclusion or coherent
simulator/FAME/bridge/functional-memory transaction is claimed. Complete Rocket
Level 1 remains disabled. Level 2 remains the independent retained four-cut
ordinary RTL replay. BOOM and Saturn remain pending; standalone Shuttle, physical
FPGA validation and ASIC power are outside this increment.

The final fixture orders each auxiliary destination before its candidate, so
the destination outlives candidate destruction even after publication. Its full
180-process rerun and six independent evidence rejections pass. Earlier complete
CPU/context/native receipts retain their original source epochs; no production
source changed during this test-only reorder. The later native artifact audit
validates the archived execution bytes again.

Exact receipts and executable native VCS checks are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostic files remain under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration153/`.
