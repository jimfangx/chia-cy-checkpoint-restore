# HTIF polling caller ownership

Iteration 107 moves the default-device HTIF polling caller into
`firesim_tsi_htif_poll_t`. FireSim's host trampoline dispatches the virtual
`run_host()`. FireSim retains installed FESVR startup, ELF/symbol loading,
termination and signature handling; it runs the polling caller through an
explicit dispatcher after startup returns. Custom RFB/disk/chroot options retain
the installed HTIF loop and reject requests for this component's owner. All long
options conservatively retain that path too: installed `getopt_long` accepts
abbreviations, so matching only full option spellings could omit a configured
device/chroot. Eighteen native/VCS cases exercise default plusargs, the plus-form
chroot, all six long chroot prefixes and a long metadata option. The failed
pre-correction pilot is preserved separately from corrected checks.

The production dispatcher preserves the original order: check exit, read
tohost, clear a nonzero command before dispatch, otherwise idle, tick devices,
then check/write fromhost if a response is pending. A busy fromhost retains the
oldest response. Exit commands still complete the current devices/fromhost
iteration before the next exit check. With no tohost symbol, only idle and exit
checks execute. Default syscall/BCD implementations remain installed FESVR
implementations. Their private state is not certified by this caller component.

The tohost/fromhost reads use the production serial-read owner. A blocked read
returns to the caller before the coroutine switches to the target. Resumption
retains partial response words and does not repeat cache flushes or request
packets. The existing host-control owner supplies each idle yield and its
remaining count. Response callbacks bind the poll owner object rather than a
queue on a suspended stack. Device command execution can still suspend inside
upstream memif/syscall code; the caller's active-service guard rejects capture
there and permanently rejects an interrupted service.

`firesim.tsi.htif-poll.v1` uses widget kind 24. Its exact configuration binds the
two resolved ELF mailbox addresses and the response-queue limit (1,048,576 in
production). The payload contains a phase, pending tohost command, response
count and every ordered 64-bit response. The nine phases are ready, tohost read,
tohost clear, command dispatch, idle, device tick, fromhost read, fromhost write
and complete. Header/configuration, payload length, phase/command consistency,
queue bounds and required pending responses validate before allocating and
swapping a candidate. Restore itself calls no service, context or target edge.
Mailbox addresses must be eight-byte aligned; unsupported configurations and
queue-limit exhaustion fail explicitly.

This owner is one child of a future complete HTIF bundle. Startup/ELF/memif,
private installed HTIF metadata, syscall descriptors/chroot/host I/O, BCD pending
commands, stop/signature state, contexts and cross-owner coherence remain
required. The default device objects still live on the host run stack. The base
HTIF also retains its original, inactive device list and descriptor objects; a
complete inventory must account for them. No
complete TSI restore API or CPU checkpoint profile is enabled by this change.
The existing initialization bundle remains a separate component interface.

The native sanitizer/VCS fixture independently specifies every caller phase,
blocked reads, idle yields, delayed and ordered responses, occupied fromhost,
wide command/response words and exit ordering. Every cut restores in fresh
processes with a complete readback before services. Malformed images reject
atomically; valid command/response corruption must fail at its first
unacknowledged component operation. Real installed-FESVR tests separately capture
the caller at first-poll, partial-read and idle cuts. These host operation labels
are not Rocket target-cycle labels. Exact commands, artifacts and remaining CPU
acceptance requirements are in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

A separate native/VCS integration feeds one deterministic input byte to the
installed BCD device. Its actual retained command callback queues
`0x0100000000000141`; the dispatcher retains that response through a blocked and
half-complete fromhost read, writes it once, and then processes the installed
syscall device's pass command. Independently expected poll, serial-read, FIFO and
host-control images are compared at all five cuts. Fresh native ASan/UBSan and
VCS processes read back all ten captured polling images before any service,
context entry or edge. This validates the real callback route, not restoration
of BCD, terminal input, the syscall device or their host context.

## Remaining owner audit and next implementation boundary

The source references below are the installed FESVR headers and their repository
sources under `toolchains/riscv-tools/riscv-isa-sim/fesvr/`. Installed archive and
header hashes remain bound by each native integration/build report.

| Owner | Execution-relevant state still requiring reconstruction or explicit cut rejection |
| --- | --- |
| `htif_t` | expected XLEN, entry/load offset, arguments and payload/symbol ELF identities, resolved symbol map, mailbox addresses, signature destination/address/length/granularity, exit-code presence/value, stopped flag and process signal-exit state |
| `load_payload()` / `load_elf()` | payload index/return destination, mapped ELF bytes and segment/zero-fill/symbol cursors; source pointers must become offsets into hash-bound bytes if a supported cut can suspend here |
| `memif_t::read/write()` | head/tail/main ordering, original address/length, partial read/merge buffer, destination/source progress and zero-fill/chunk cursor; neither a serial-read image nor a transport phase owns these caller frames |
| Default syscall device | stable HTIF/memif binding, guest-to-host descriptor map and ownership, offsets, chroot and syscall dispatch/buffers; ordinary host file descriptors cannot be copied into a fresh process |
| BCD / terminal | queued commands, callback destinations, consumed input and published output; terminal stdin/stdout and termios are external process state |
| Device dispatch | device/command table identity and dynamic devices; callbacks must be rebound to the destination owner, including commands retained by BCD |
| Stop/signature | pending memory read and bytes, formatter/output cursor, publication status and stopped transition |
| `context_t` / host trampoline | fresh creator/target binding and dispatcher re-entry phase; saved stack/register addresses, `ucontext_t`, TLS current-context pointer and function/object pointers cannot be checkpoint payloads |
| Cross-owner cut | poll read phase versus serial child address/size/progress/FIFOs, idle phase versus host-control countdown, loader/init completion, device activity and simulator bridge/target cut labels |

Proposed next focus: prove the precise host phase at each required active CPU
cut before implementing more loader continuation. If native evidence establishes
that startup has returned, ELF mappings and loader/memif frames are no longer
live at that cut. A documented steady-state CPU profile can reconstruct the
hash-bound startup metadata and reject cuts with active loader/memif/device
children. It must not rerun target program writes, initialization or reset.
The proof must include the complete default-device state even when the selected
bare-metal workload only sends pass/fail commands. Raw coroutine snapshots and
an assumption that unused devices are empty do not establish ownership.

This is a proposed implementation boundary, not a newly supported CPU profile
or a relaxation of the required early/warm/outstanding-memory/late workload cuts.

Independent fresh-process restore cases use four workers, with command/catalog
updates under a lock. A group finishes before its producer/configuration changes.
Every submitted sibling runs even if another check fails; the first exception
is rethrown after joining all jobs. Runner tests cover ordered results, empty
groups, real subprocess siblings after failures and input-generator failure.
State images, process counts, negative cases, readbacks and comparisons retain
their complete original scope.
