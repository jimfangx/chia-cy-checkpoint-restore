# Suspended HTIF polling cut audit

Iteration 108 adds read-only inspection of a production TSI caller after HTIF
`start()` has returned. This addresses the proposed boundary in
[tsi-htif-poll.md](tsi-htif-poll.md). It does not enable a CPU checkpoint profile
or restore the installed HTIF metadata, devices, terminal, signature handling or
coroutine contexts.

`firesim_tsi_t::inspect_polling_cut()` returns complete images of these eight
existing component owners, in a fixed order:

| Name | State |
| --- | --- |
| `poll` | HTIF poll phase, pending command, ordered response queue |
| `program` | Program loader phase and transport/cache-flush configuration |
| `init` | TestChip initialization accesses, phase, cursor and pending data |
| `host` | Idle/reset phase, remaining yields, busy and loaded flags |
| `read` | Serial-read phase, address, length and retained response words |
| `serial` | Both serial FIFOs, including unconsumed response words |
| `loadmem-read` | Load-memory read phase, address, length and retained words |
| `loadmem-queues` | All four load-memory queues and active write-data cursor |

The caller must use the owned default-device path and be suspended at the
target. Startup must have returned; program loading and initialization must be
complete; the load-memory reader and every load-memory queue must be empty.
Supported polling cuts are a blocked mailbox read (including a partial response)
with the matching serial child, or an idle yield with its matching countdown.
The method validates every component image, then reads every image again to
check stability. It performs no context switch, target access, queue drain or
device service. A rejection returns no partial component collection.

The base TSI trampoline now records whether its host context is suspended at the
target. This boolean is an inspection guard, not a serialized context owner.
An actual installed syscall can yield inside `memif_t::read()` with that guard
set. The poll owner's active-call guard still rejects inspection there; an
external coroutine yield alone does not establish a supported cut.

`tsibridge_t` exposes this inspection through the optional bridge host-component
diagnostic interface, with scope `tsi-polling`. The default bridge interface
advertises no scope. Neither interface changes aggregate checkpoint admission.

The FireSim driver accepts `+tsi-host-audit=DIRECTORY` together with
`+tsi-host-audit-cycles=C0,C1,...`. Credits must be strictly increasing unsigned
integers; zero is permitted. Duplicate, incomplete, empty and malformed options
and existing destinations reject. The diagnostic schedules anonymous callbacks,
which remain unsupported by the scheduler's checkpoint contract. Each callback
writes one JSON record containing both the requested master credit and the clock
bridge's actual clock-token count, followed by either all component images or an
explicit rejection. These labels must not be substituted for completed semantic
DUT edges or for CPU print-cycle labels. A missing requested record is incomplete
evidence and must fail the independent audit.

Native/VCS integration tests inspect actual loader, reset, partial-read, idle,
BCD/fromhost and termination boundaries. Nine component-valid but mutually
inconsistent owner modifications test rejection without changing peers. Another
integration sends a real even-payload proxied syscall command: the installed
syscall and memif implementations block on a 64-byte target read, then block
again after one response word. Both cuts reject. After all words arrive, the
installed `sys_exit` returns, its response reaches the poll queue, all eight
component images become inspectable, and normal fromhost publication and
termination finish. Those are host component operations, not CPU checkpoint cuts.

The exact-recipe Rocket workload sampling and validation results are recorded
in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). No Level-1 continuation,
captured Level-2 state or captured boundary replay is implied by these audits.
