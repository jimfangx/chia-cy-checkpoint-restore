# Restricted syscall-93 polling ownership

Iteration 145 connects `firesim_tsi_syscall_exit_t` to production FireSim
polling through explicit `+checkpoint-syscall-exit` mode. This requires a
sealed terminal, supported default startup metadata and the opt-in exact-header
HTIF provider. Ordinary execution retains installed syscall dispatch. Restricted
mode admits only nonzero, even device-0/command-0 request addresses; other
commands reject before clearing tohost. A decoded selector other than 93
rejects before host exit, writeback or response.

The executable service uses the original cache-flush walk for request reads,
write-merge reads, writeback and mailbox access. Blocked nested reads return
through the syscall and polling guards before `run_host` switches context.
The exit service does not end dispatch: all 64 writeback bytes and `respond(1)`
complete first. The response belongs to the destination polling queue and its
fromhost transaction runs before the polling loop next checks `should_exit()`.

`firesim_tsi_polling_syscall_t` captures and restores fourteen ordered components:

| Component | Owned state |
| --- | --- |
| poll | Mailbox caller phase, pending tohost command and response queue |
| program / init / host | Completed loader/initialization and current idle/host-control progress |
| read / serial | Mailbox serial-read cursor and both complete transport FIFOs |
| loadmem-read / loadmem-queues | Independent loadmem child and all four queues, required inactive |
| bcd / terminal | Complete sealed images, required pristine in this restricted mode |
| identity / write | Independent BCD identity/write owners, required inactive |
| syscall | Eight request words, selection/invocation/writeback/response cursor and nested memif read/write children |
| lifecycle | Actual provider optional-exit presence, all 32 raw exit bits and stopped field |

The direct-exit recorder must remain pristine. Cross-owner validation binds
the active syscall to the pending dispatch command, requires an empty polling
response queue during dispatch, and checks its actual provider exit against
invocation/writeback progress. Completed syscall cuts admit the queued response
read or completed polling with an empty response queue. Stopped provider images
reject; the outer stop/return caller is not owned by this group.

Preparation parses and allocates every replacement without publishing a peer.
The destination-bound, single-use candidate rechecks startup identity, pristine
protocol/caller and provider/signal policy immediately before nonthrowing
publication. Input-image lifetime does not constrain the candidate. Restore
never issues startup, an exit service, memory traffic, a context entry or a
target edge. The narrower polling and direct-exit APIs cannot restore or
continue this mode while omitting its syscall owner.

Fresh continuation uses the actual polling services with no installed session
or coroutine reconstruction. It may finish the response and reach completed
polling, but does not call `stop()`. Source capture separately exercises the
live context and actual stop. Session/descriptors, general syscalls, signal
coordination, enclosing startup/stop/return/context and coherent simulator,
bridge and memory publication remain pending. **Complete CPU Level 1 remains
disabled.** Caller-held exclusion and the existing provider signal policy
remain required; this work does not implement a process signal coordinator.

Iteration 146 removes the unused `default_devices_t` from restricted polling
and extends fresh component coverage through two zero-mailbox idle rounds.
The inherited HTIF syscall proxy still owns three duplicated standard-stream
descriptors. Its session ownership, the outer caller/completion and coherent
simulator publication remain pending. See
[tsi-restricted-session.md](tsi-restricted-session.md) for the actual descriptor
inventory and suspended-lifetime checks. General syscall support remains a
separate pending feature.

`verify_tsi_polling_syscall_vcs` compares every captured owner byte against an
independent Python protocol/serial/syscall oracle, with fresh native ASan/UBSan
and VCS producer/consumer pairings at every explicit host-operation boundary.
Scenarios cover address residues 0/2/4/6, four raw exit values and both cache
flush policies. A fresh consumer reads all fourteen owners before any service,
then checks complete owner images after every operation and final response
timing. Deliberate semantic faults change an actual syscall argument and its
copied write-child byte; the first outgoing divergent word stays unconsumed.
These cuts are **host-operation indices, not Rocket target-cycle labels**.

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration145/`.
Accepted invocations, exact commands and executed results are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Failed and superseded pilots
remain separate diagnostics. Next work must restore the remaining external and
outer owners before publishing a coherent simulator cut or enabling CPU Level 1.
