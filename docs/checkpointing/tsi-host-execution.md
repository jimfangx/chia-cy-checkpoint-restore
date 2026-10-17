# Explicit FireSim TSI outer caller

Iteration 148 replaces the owned-default-device branch of
`firesim_tsi_t::run_host()` with `firesim_tsi_host_execution_t`. Its five
serialized phases are startup, polling, stop, return-code collection and
returned. Its return value retains the exact installed 32-bit signed `int`
bits. The object belongs to the TSI, rather than its coroutine stack.

The production service adapter still runs the real `start()`, creates the
same poll/BCD objects and optional ordinary syscall session, advances the
same polling child, clears `polling_active` before the real `stop()`, releases
the ordinary session, and obtains the installed `exit_code()`. The BCD callback
captures the TSI pointer, not the temporary service adapter. Custom-device
dispatch continues through the installed HTIF path and is not covered by this
owner. Restricted mode retains its absent inherited-proxy/session invariants.

A service must return before the outer owner can be inspected or restored.
This deliberately rejects the real startup's suspended load/reset stack and
ordinary device callbacks that yield inside a child. Reentry and restore
during a service reject. An escaping service exception permanently poisons the
owner. Complete payload parsing precedes assignment; malformed headers,
configuration, phase/result combinations, truncation and trailing bytes reject
without changing its destination.

The standalone native ASan/UBSan and VCS test restores every component cut in
both backend directions, reads all bytes before service, and compares every
remaining phase and return value. It also checks actual phase corruption at
the first unacknowledged service boundary. These are host-operation labels,
not CPU target cycles. A separate production test executes the actual source
coroutine, observes rejected startup captures and polling/returned images,
drains the full syscall response before completion, and checks repeated ticks
in the wrapper's infinite yield loop. Restoring the existing fourteen-owner
polling group still leaves this outer owner at startup and rejects `tick()`.

Executable commands and exact results are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration148/`.

This does not add the outer owner to a complete checkpoint group or serialize
`host_thread()`/`context_t`. The stop and return-code cuts are independently
tested component cuts; normal execution has no target yield between them.
Complete Rocket Level 1 stays disabled. The independent Rocket Level-2 finite
captured replay remains separate.

Next, include this owner in a coherent restricted aggregate with explicit
cross-owner validation: polling requires a started child and an unstopped
provider; stop requires completed polling; return-code collection requires a
stopped provider; returned must bind the actual provider's signed exit result.
Reconstruct the wrapper's entered/returned meaning and its fresh process-local
context handshake without serializing stacks or replaying startup. Production
signal coordination, complete parsed-session/registration policy and atomic
simulator/bridge/functional-memory publication remain required before CPU
Level-1 continuation.
