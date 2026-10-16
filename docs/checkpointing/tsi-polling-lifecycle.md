# Atomic polling and HTIF lifecycle publication

Iteration 136 adds `firesim_tsi_polling_lifecycle_t`, an opt-in fourteen-owner
host group. Iteration 137 adds explicit pending-exit caller continuation through
the no-signature provider stop. The group combines the polling components with the explicit
direct-exit recorder and the actual HTIF provider's optional exit and stopped
fields. Complete Rocket Level-1 restoration and captured Level-2 replay remain
pending. This interface does not enable a CPU checkpoint profile.

The ordered group is explicit; it does not reuse the FCFS driver whitelist:

| Image name | Owned component storage |
| --- | --- |
| `poll` | Mailbox caller phase, current command and response FIFO |
| `program` | Program-loader phase and transport/cache policy |
| `init` | Initialization/MSIP caller phase, access cursor and copied read value |
| `host` | Host step/idle phase, remaining idle count and loading flags |
| `read` | Serial-read request, partial response words and progress |
| `serial` | All serial request and response FIFO words |
| `loadmem-read` | Independent load-memory read caller; required idle here |
| `loadmem-queues` | Four load-memory queues and active burst; required empty here |
| `bcd` | Pending binary-terminal commands and exact configuration |
| `terminal` | Sealed binary input, cursor and output transcript |
| `identity` | Raw BCD identity command and dispatch/write/return cursor |
| `write` | Copied identity payload, unaligned head/tail merge reader and progress |
| `exit` | Explicit direct-exit phase and raw 32-bit status |
| `lifecycle` | Actual provider optional-exit presence/raw bits and stopped bit |

Startup metadata is a separately validated prerequisite. It binds exact ELF,
arguments, transport/XLEN policy and pristine destination components. These
fourteen images exclude session/descriptors/signals/context, target memory and
all generated RTL. The group is therefore not a complete `.fsckpt` owner list.

`prepare(images)` requires all fourteen ordered names. Its destination-bound,
noncopyable and nonmovable candidate owns every parsed replacement. Preparation
performs no publication, service, reset or context entry. Destroying an unused
candidate leaves the destination unchanged. The caller must exclusively suspend
the TSI, keep it alive through candidate destruction and obey the existing
provider's blocked-signal policy. Preparation does not reserve signal state.

The direct-exit recorder and provider must agree on the complete phase, optional
presence, raw 32-bit status and stopped bit. Absent exit, present zero, even raw
statuses and odd raw statuses are distinct. A running recorder requires absent
exit and stopped=false. A requested recorder requires the same present odd raw
status, stopped=false and an actual pending `fromhost_read` parent boundary.
The supported pending-exit source cuts retain response traffic while the peer's
fromhost mailbox was occupied. Stopped-parent restoration remains unsupported.

At commit, all allocating protocol/destination checks precede the provider's
final mask/pending-signal/handler/signature/optional-exit/stopped guards. The
private publication callback only swaps prepared protocol and direct-exit
storage. Provider assignments follow without allocating or throwing. It never
calls another public candidate's `commit()` inside that callback. Consumed or
competing candidates reject. Late peer or provider changes reject before
publishing any owner and preserve the actual changed destination.

The inspection reads every protocol word, the direct-exit recorder and the
actual private lifecycle fields. Existing twelve-owner inspection and service
admission retain their stricter exit rejection. Fresh running groups use the
existing explicit BCD/identity service. Pending-exit groups permit complete
readback and still reject `tick()` and ordinary polling continuation. The separate
`advance_pending_exit()` interface first inspects all protocol/provider owners,
including actual optional raw status and the signal/signature guards. It admits
only a fresh restored requested-exit group. Its private caller permits only
`fromhost_read`, `fromhost_write` and the loop's exit condition. An incomplete
read returns to the explicit caller; no service suspends inside a coroutine.
An empty mailbox receives the queued response before stopping. An occupied
mailbox preserves the queued response and stops without another write.
The actual provider's no-signature `stop()` sets its stopped field, and the
explicit exit recorder transitions with it. No syscall/device session is entered.

`inspect_completed_exit()` validates the stopped recorder/provider, complete poll
phase, idle children and every protocol word. It checks the actual provider
twice. Completed-exit inspection admits the poll's terminal phase only in this
private fresh-caller path; twelve-owner preparation and ordinary service retain
their earlier rules. Repeated exit service, ordinary polling and `tick()` reject
without mutation. Stopped images still reject restoration. The installed session,
its destruction/return caller and outer context remain separate owners.
Syscall/session/descriptors/signals/context and full simulator/bridge/memory
ownership remain required before complete CPU admission.

Native sanitizer and VCS checks, independent byte oracles, full source bindings,
workload plans, exact commands and results are recorded under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration137/`.
The final invocation and counts are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). This iteration preserves the
prior twelve-owner, lifecycle, FCFS and ordinary RTL diagnostic regressions.
No physical FPGA or ASIC result is claimed.
