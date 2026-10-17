# Restricted TSI coroutine continuation

Iteration 150 adds a semantic `host_thread` wrapper and fresh process-local
coroutines to the restricted syscall-93 host component transaction. This is a
component continuation API, `firesim_tsi_context_group_t::resume()`. Complete
Rocket CPU Level 1 remains disabled; ordinary `tick()` still rejects restored
metadata/components.

`firesim.tsi.host-wrapper.v1` (configuration tag 36, revision 1) stores one
phase: fresh, execution, or tail. The production wrapper records execution before
calling `run_host()` and tail after its signed result has been collected into the
existing outer owner. An interrupted callback poisons the wrapper. The checkpoint
contains no native stack, callback address, `ucontext_t`, root/creator pointer or
signal mask.

The sixteen ordered images are the fifteen owners documented in
[tsi-host-aggregate.md](tsi-host-aggregate.md), followed by `wrapper`. Preparation
requires a pristine, uninitialized destination wrapper, parses/allocates all
replacements and validates the outer/provider/child suspension together. Only
these source suspension boundaries are accepted:

| Wrapper | Outer caller | Continuation |
| --- | --- | --- |
| execution | polling | Resume the next semantic polling advance |
| tail | returned | Yield repeatedly without calling a service |

Startup, fresh wrappers, and the component-only stop/return-code intermediate
cuts reject. Production does not suspend at those intermediate cuts. The
fifteen-owner component API retains them independently.

Publication rechecks the pristine wrapper and the existing metadata/protocol,
restricted proxy, caller and actual provider guards. The existing nonthrowing
publication callback swaps all sixteen owners and marks the fresh continuation
mode atomically. Abandoned, consumed or competing preparations cannot enter a
context or publish over an occupied destination.

Complete image readback occurs before allocating/entering a native coroutine.
The first explicit `resume()` initializes the existing audited 1 MiB context
trampoline and reconstructs the wrapper and `run_host` service frames. An
execution image enters the restored polling phase directly; it never calls
`start()`, reset or program loading. A tail image bypasses `run_host()` entirely.
The source and reconstructed polling/stop/return paths use the same production
services. Guards unwind before every target-context yield. Component-only
`advance()` rejects after wrapper reconstruction, preventing mixed callers.

The base adapter checks its original target context before child allocation or
service entry. Foreign-thread and nested-creator entry reject. Metadata-only
callers cannot bypass admission through the base `switch_to_host()` API. Fresh
stack-allocation failure leaves all semantic images and context initialization
unchanged and can be retried.

The current provider's all-thread blocked/pending/delivered-signal policy is
checked before each component resume, including after a native coroutine has
been initialized. Exclusive access and an external policy preventing concurrent
signal/thread changes are still mandatory. This change does not supply the
production signal coordinator or restore signal-caused exit callers.

The restricted mode retains no inherited proxy descriptors/table or ordinary
syscall session and only dispatches syscall 93. The retained four-hart CPU
workload uses an odd direct-exit command; its wrapper/outer aggregate integration
is still required, or a separately hashed self-checking CPU workload using the
supported syscall protocol. This host fixture is not a CPU workload substitute.

Simulator/FAME/bridge/functional-memory atomic publication and fresh complete
Rocket target-cycle continuation remain pending. Level-2 captured replay remains
independent. See [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) for executed
results and exact native commands. Diagnostics are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration150/`.
