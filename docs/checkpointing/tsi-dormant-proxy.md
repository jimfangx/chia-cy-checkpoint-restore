# Restricted inherited HTIF proxy lifetime

Iteration 147 retires the unused inherited `htif_t::syscall_proxy` resources
when constructing explicit `+checkpoint-syscall-exit` mode. That mode already
uses its own syscall-93 caller and never dispatches the inherited device list.
Ordinary dispatch retains its original proxy and default polling session.

The build-local exact-header provider adds friend declarations to the installed
`syscall_t` and `fds_t` declarations, without changing fields, virtual methods,
original HTIF method bodies or installed `syscall.o`. Its archive report binds
the installed syscall header and the adapted header hash. Installed files are
untouched. The normal provider selection and explicit `owned-htif.o` link remain
required. An older lifecycle provider without the dormant-proxy interface cannot
construct restricted mode.

Retirement requires the actual constructor's three canonical descriptor slots,
three distinct valid descriptors above stderr, its 2,048-entry dispatch table,
empty chroot, no dynamic devices and correct HTIF/base-memif owner links. It
closes each duplicate once and empties both descriptor containers and the
dispatch table. The installed destructor consequently has no descriptor indices
to close. This is a Linux resource-lifetime policy; it does not serialize host
descriptor numbers or implement general syscall migration.

Every restricted polling group inspection, preparation, publication admission
and continuation requires those resources to remain absent, with correct owner
links and no chroot or dynamic devices. A fresh TSI reconstructs its immutable
registrations and pointers through normal construction, then retires the unused
resources before metadata preparation. Image bytes remain the fourteen owned
protocol/caller/lifecycle images. Complete simulator images must still carry
their independent simulator-build compatibility binding.

Native ASan/UBSan and VCS checks compare complete process descriptor tables at
construction, polling, four suspended idle/read boundaries and destruction.
Restricted construction and polling retain no proxy/session descriptors;
ordinary construction adds three and polling adds three more. Existing
descriptor identities and flags must remain unchanged. Repeated retirement and
admitting the ordinary live proxy as retired must reject without changing the
descriptor table. A separately compiled prior production constructor must fail
the new restricted descriptor check.

The separate test-only provider fault fixture modifies real private fields:
descriptor containers, dispatch table, chroot, HTIF pointer, memif pointer and
dynamic devices. Each fault is applied before preparation, after preparation
but before commit, and after complete fresh readback. Rejection must preserve
all protocol/lifecycle peers and perform no target service or context entry.
Its provider extension is diagnostic only and is absent from production builds.

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration147/`.
Executed results, exact recipe/build identity, workload hashes and native VCS
commands are recorded in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

This increment establishes an absent-resource invariant for one unused owner.
It does not restore general sessions, inherited device callbacks or the complete
outer execution. Explicit outer startup/stop/return/context, production signal
coordination and coherent simulator/bridge/memory publication remain pending.
Complete Rocket Level-1 CPU continuation stays disabled. The separately
validated complete Rocket Level-2 finite replay remains independent.

Next ownership work, re-audited against the current production sources:

| Source | Required continuation |
| --- | --- |
| `firesim_tsi_t::run_host()` | Own startup, polling, stop and return phases; its current metadata guard rejects fresh context entry. A fresh polling continuation must bypass `start()` and preserve exactly when `polling_active` clears, `stop()` runs and `exit_code()` returns. |
| `firesim_fesvr_tsi_t::host_thread()` | Own the transition from `run_host()` to its infinite target-yield loop; the current wrapper discards the return value and has no serialized phase. |
| `switch_to_host()` / `switch_to_target()` | Reconstruct a fresh process-local `host`, `target` and trampoline with the correct initialized/suspended meaning. `context_t::init()` first yields from its wrapper before calling the host callback; do not count that handshake as a target service or serialize a ucontext/stack. |
| HTIF/session and signals | Establish the complete supported parsed-session/registration invariant and all-thread signal policy in production. The provider's externally suspended component guards do not establish a metasim-wide coordinator. |

The retired proxy must remain absent throughout this work. Adding an outer
owner does not by itself establish a coherent generated simulator, bridge and
functional-memory checkpoint, nor authorize complete CPU continuation.
