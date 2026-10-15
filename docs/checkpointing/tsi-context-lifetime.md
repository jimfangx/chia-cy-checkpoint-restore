# FESVR context resource ownership

Iteration 113 addresses process-local coroutine lifetime for the exact Rocket
recipe. Complete Level-1 CPU continuation and Level-2 captured replay remain
unsupported. This change does not serialize native stacks or authorize more
checkpoint cuts.

`owned_context.cc` uses the installed, unchanged `fesvr/context.h` class layout.
A thread-local registry owns each child's 1 MiB stack separately from its
`ucontext_t`. Destruction of an inactive child releases its allocation; thread
exit releases remaining stacks and the native root context. The latter matters
because metasim deliberately retains its widget registry after its driver
thread returns. This releases stack storage without destroying retained bridge
objects or unwinding their suspended frames.

Initialization allocates before publishing callback/creator state. Allocation
failure leaves the child retryable. Initial entry still yields through the
original FESVR trampoline before invoking the callback. Explicit switches
preserve suspended stack locals. Normal callback return updates `current()`
before transferring through `uc_link`; subsequent entry rejects. Null callbacks,
reinitialization, fresh/finished/self switches and foreign-thread use reject.
Destroying an active context or a suspended child's creator aborts explicitly.
Process exit from an active child is explicitly unsupported and aborts before
TLS cleanup can free its executing stack. Non-glibc context implementations
fail at compile time.

The build-local FESVR archive now replaces `context.o` and `elfloader.o`.
The other 12 installed members and Conda inputs remain unchanged. The Makefrag
passes both audited objects once through `DRIVER_CC`, avoiding static archive
selection and VCS's repeated inherited/explicit linker flags. CPU build identity
requires exact replacement-source hashes and byte-identical explicit objects in
the actual native VCS command. Independent recompilation/provider evidence lives
under the diagnostic root below. The shared `libriscv.so` exports the installed
HTIF/loader, but has no FESVR `context_t` exports; the actual executable host
caller invokes its strong context definitions directly.

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration113/verified/`.
`context/invocation-x679fyt3/summary.json` records native sanitizer and VCS DPI
execution. Each backend checks 128 suspended and 128 completed lifetimes,
1,018 principal continuation switches, interleaved siblings, nested creators,
allocation failure/retry, 16 normally cleaned worker roots and an intentionally
retained metasim-style worker object. Allocation interception accounts for all
278 stacks: 278 released, zero live. The retained object remains reachable;
the check certifies its stack release, not destruction of that object. The
original-library control retains both tested stacks (zero released). Six
separate native/VCS death checks reject active/creator destruction and process
exit from an active child, before any executing stack can be freed. ASan reports
its standard limited `makecontext`/`swapcontext` support; explicit allocation
accounting and native VCS checks additionally cover lifetime and continuation.

`transport/invocation-pri708pp/summary.json` runs the actual TestChip/TSI bridge
with this overlay. Its independent bus oracle checks 1,012 requests, complete
bridge traces, 32 invalid requests, callback unwinding and 24 bridge-control
readbacks. Native sanitizer execution exits successfully without leak or
undefined-behavior diagnostics. This supersedes the failing iteration-112
transport sanitizer result for the current overlay; the original failed
artifacts remain preserved.

`context-instrumented/summary.json` also checks the actual context source and
fixture compiled together under ASan/UBSan, including all three fatal lifetime
rejections. No sanitizer suppression is used.

The initial context implementation incorrectly rejected metasim's retained
registry on driver-thread exit. A real short Rocket timeout reproduced that
abort. The corrected `retained-context-exit/` diagnostic finishes the deliberate
1,025-cycle timeout with the normal failure exit and no context abort. Earlier
context/build/audit/source-drift pilots remain outside `verified/` or are separately
indexed; they do not certify the final source.

Executable fresh resource check:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_fesvr_context_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/context
```

Run the actual bridge transport regression with the same environment:

```sh
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/transport
```

## Remaining semantic ownership

| Owner | Current treatment | Required before complete CPU restore |
| --- | --- | --- |
| Native root/current/creator/callback pointers and `ucontext_t` | Thread-local resources; never checkpoint bytes | Reconstruct supported callers from coherent semantic owner state in a fresh process |
| Suspended native frames and stack locals | Storage released without frame unwinding | Admit only explicitly audited suspension points; move live resources and future-relevant values to semantic owners |
| HTIF expected XLEN/configuration, arguments, metadata | Component metadata/XLEN checks exist | Bind complete configuration and native dependency policy to the atomic CPU image |
| HTIF memif, default devices, terminal/syscalls, stop/signature/exit/signal state | Aggregate restore remains disabled | Audit and reconstruct every relevant field/resource without repeating startup target writes/reset |
| Metasim driver/FAME/channels/memory/bridges | Existing component evidence retained | Complete independent ownership and coherent target-edge capture/restore across required workload cuts |
| Pre-FAME CPU/uncore boundary | Complete pattern inventory/readback only | Independently capture semantic words and boundary trace, then restore/read back before edges and replay in fresh ordinary RTL VCS |

Suspended native stack storage is not a substitute for semantic ownership.
Active services, cross-thread context transfer and complete CPU image requests
remain explicitly unsupported. See [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md)
for exact workload/build settings, native commands and per-level status.
