# Restricted TSI outer aggregate

Iteration 149 adds `firesim_tsi_host_group_t`: fifteen ordered component images
cover the existing twelve sealed polling owners, the syscall-93 caller, actual
HTIF lifecycle fields, and `firesim.tsi.host-execution.v1`. This is a host
component transaction. Complete CPU Level 1 remains disabled.
This group covers opt-in syscall-93 dispatch. The existing direct-exit polling
group remains separate and does not acquire outer/context restoration here.
The retained `rocket_quad/workload.c` writes an odd direct-exit command. Its
Level-1 run therefore also needs that outer integration, or a separately
hashed self-checking CPU workload using the supported syscall-93 protocol.

The ordered image names and owners are:

| Image | Owner/schema suffix under `firesim.tsi.` |
| --- | --- |
| poll | `htif-poll.v1`: mailbox caller, pending command and responses |
| program | `program-loader.v1`: completed load transport/entry/return |
| init | `init-accesses.v1`: completed reset/access caller |
| host | `host-control.v1`: idle cursor and loaded/busy flags |
| read | `serial-read.v1`: mailbox read cursor and partial words |
| serial | `serial-queues.v1`: complete outgoing/incoming FIFOs |
| loadmem-read | `loadmem-read.v1`: inactive load-memory read child |
| loadmem-queues | `loadmem-queues.v1`: all four empty startup queues |
| bcd | `bcd.v1`: pristine restricted-mode BCD |
| terminal | `terminal.sealed.v1`: immutable input plus pristine cursor/transcript |
| identity | `bcd-identity.v1`: inactive identity caller |
| write | `memif-write.v1`: inactive independent write/merge child |
| syscall | `syscall-exit.v1`: command, eight argument words, read/write children and response progress |
| lifecycle | `htif-lifecycle.v1`: actual provider exit presence/raw bits/stopped fields |
| outer | `host-execution.v1`: outer phase and signed return bits |

The outer phase must agree with the independently restored polling child and
provider:

| Outer phase | Polling child | Provider |
| --- | --- | --- |
| startup | rejected | startup stack remains unsupported |
| polling | incomplete | not stopped; syscall caller determines exit presence |
| stop | complete | exit present, not stopped |
| return-code collection | complete | exit present, stopped |
| returned | complete | exit present, stopped; exact signed installed return agrees |

The syscall component can now be inspected after stop only if it has completely
finished its read, writeback and response child. Its executable `advance()` and
the previous fourteen-owner polling group continue rejecting stopped providers.
Only the outer aggregate validates completed polling together with stop/return.

Preparation parses and allocates every replacement into destination-bound
candidates. Publication rechecks pristine protocol, caller, outer, metadata,
retired proxy and actual provider signal/lifecycle guards. The provider's
nonthrowing publication callback swaps protocol, syscall and outer state before
assigning its own fields. No startup, target service, coroutine entry or target
edge occurs during restore. Abandoned, competing and consumed candidates cannot
publish into an occupied destination.

Fresh component continuation calls the same production polling, stop and signed
return services as `run_host()`. It reaches a blocked child or exposes the next
stop/return boundary. Stop and return-code collection have explicit component
cuts; production does not yield there. The tests also observe the real source
coroutine through its actual returned state and repeated wrapper tail ticks.
All cut and divergence labels in this suite are host-operation indices.

The wrapper/context handshake remains unowned: `tick()` still rejects after
metadata/component restoration. Signal delivery requires the existing explicit
provider policy and exclusive suspended access; no production thread coordinator
is supplied here. Complete inherited-session policy, simulator/FAME/bridge/
functional-memory publication and fresh complete Rocket CPU continuation remain
pending. BOOM/Saturn, physical FPGA validation and ASIC power are not claimed.

Exact executed results and reproduction commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration149/`.
