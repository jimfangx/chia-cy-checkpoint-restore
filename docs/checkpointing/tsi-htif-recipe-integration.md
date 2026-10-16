# HTIF lifecycle provider in exact-recipe metasim

Iteration 132 adds explicit production Make selection with
`CHECKPOINT_HTIF_SOURCE=/absolute/path/to/fesvr/htif.cc`. The default retains
installed HTIF. The selected lifecycle archive and extracted objects live in
`checkpoint-fesvr/lifecycle/`, separate from the default resource overlay.
The installed archive and headers are untouched. No CPU checkpoint profile
is enabled, and the twelve-component polling aggregate is unchanged.

The exact-recipe command generator and four-hart control launcher accept
`--htif-source`. Their VCS commands retain all six recipe settings and use
`VCS_FORCE_REBUILD=1`, `VCS_FLAGS=-Mupdate`, pinned Y-2026.03-SP1, `-full64`
and system GCC/G++ 13. Use forced native rebuilds when changing provider
selection. No FPGA implementation is invoked.

The recipe links `owned-htif.o` explicitly, alongside the existing loader and
context objects. This prevents a shared `libriscv.so` definition from satisfying
HTIF references before static archive extraction. The build identity audits
the actual VCS arguments, each extracted member's bytes, the lifecycle symbols,
the selected original source/header and generated provider hash. Only
`elfloader.o`, `context.o` and `htif.o` may differ from installed FESVR.
The provider still adds only a friend declaration to an exact matching header;
all original HTIF method bodies remain unchanged.

The control launcher now snapshots maintained native sources **before**
compilation in `pre-build-inputs.json` and checks them again after building
and after both full workloads. Generated artifacts and compiler dependencies
remain bound by the executed native build identity. A source change during
the run rejects the result.

`verify_tsi_htif_lifecycle_vcs --recipe-build-identity PATH` tests the archive
actually linked into that recipe. It checks the complete native build inputs
before compiling its fresh native/VCS consumers. Its independent audit binds
the recipe's archive and all three explicit objects, then repeats the complete
production-source lifecycle oracle, fresh private-field readbacks, malformed
images, signal guards and first-divergence tests. These are host component
tests; they are not Rocket checkpoint cuts or DUT corruption evidence.

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration132/`.
Recipe lifecycle suite:
`recipe-lifecycle/invocation-qzzg2vo_/summary.json` (passed: 1,216 captures,
2,432 fresh restores, 88 optional/raw/stopped restores, 282 invalid-image
processes, eighteen guards and twenty boundary-zero component divergences).
The incompatible source/header case preserves both destination archive and
report. The entire serial owner remains unchanged during restore/rejection.
Eight read-only build-record negative cases additionally reject missing/duplicate
provider objects, missing loader/context/serial owners, wrong VCS release and
missing 64-bit mode without replacing the destination record. They use mutated
copies of the executed build log, not fabricated simulator executions
(`build-rejections/invocation-n9vy_gbc/summary.json`).

Both exact-recipe complete four-hart controls pass at C=3,329,794, with full
16 GiB backing memory. All eight full hart traces and every workload/store
label match the uninterrupted reference. All eight active host samples / 64
known component images match, including the late cut. Independent audits pass.
Control summary: `rocket-controls/invocation-lnj9j73_/summary.json`.
The auditor also rejects five contradictory or untyped provider declarations
by deriving provider membership from the actual link arguments
(`audit-provider-flags.json`). The source snapshots precede this final read-only
auditor hardening; the new auditor's hash is retained with the negative checks.

Remaining HTIF ownership audit (actual installed headers and production
`firesim_tsi_t::run_host`, re-read in iteration 132):

| Owner | Required state / remaining work |
| --- | --- |
| `htif_t` | Lifecycle provider owns only actual `exitcode` and `stopped`. Existing startup metadata prepares the selected ELF, entry and symbols under its explicit policy; it does not establish a complete session image for arguments, payload/symbol lists, XLEN, signature policy, device registration and all private fields. |
| Active `default_devices_t::syscall` | A separate installed `syscall_t` is created after `start()`. Its constructor binds the virtual runtime memif and duplicates stdin/stdout into three descriptor slots. Own `fds`, `fds_index`, resources/offsets, chroot and command registration; reconstruct owner pointers and function tables rather than serializing addresses. |
| Dormant `htif_t::syscall_proxy` | The base constructor also constructs its own syscall proxy and duplicates three descriptors. Auditing only the active polling syscall object omits these session resources. Custom-device fallback still runs the installed device list and must remain unsupported until audited. |
| Active syscall caller | Installed `dispatch()` retains `magicmem[8]`, operation arguments and read/write return progress on the suspended stack. The generic memif reader owns its child progress, not that parent or the syscall destination. |
| Poll caller / device table | Existing explicit poll/BCD/identity/write owners cover restricted operations. The active runtime additionally retains `polling_services_t`, `default_devices->list`, callbacks and parent return state. Twelve-component sealed preparation does not reconstruct that default session. |
| Signal provider | Actual translation-unit `signal_exit`, INT/TERM/ABRT handlers, masks, pending signals and thread/session policy need explicit ownership or a complete supported-state rejection policy. The lifecycle guard only rejects unsupported observations under an externally established mask. |
| Outer context | Source-integrated TSI retains `host`, `target`, `host_initialized`, `host_suspended` and the executable return path through `run_host()` / `switch_to_target()`. Resource-safe context storage is distinct from semantic fresh-context continuation. |

These gaps are independent of the generated FAME/token/memory/bridge owners
and of the pre-FAME DUT semantic inventory. Linking the provider closes none
of those other gaps automatically.

For aggregate preparation, the current lifecycle adapter's
`validate_checkpoint()` parses the image only; destination/provider guards run
in `firesim_htif_lifecycle_restore()`. Iteration 133 adds a destination-bound
candidate with preparation and final-publication guards; see
[tsi-htif-lifecycle-preparation.md](tsi-htif-lifecycle-preparation.md).
A future aggregate must preflight those
guards and the pristine actual destination before publishing any other owner,
then commit the parsed fields under its supported thread/signal policy.
Appending `load_checkpoint()` after the existing twelve-owner publication would
permit a late guard rejection after other owners changed and is insufficient.

Complete CPU Level-1 continuation and Level-2 captured readback/replay remain
pending. Lifecycle source selection does not own HTIF sessions, descriptors,
signal state, syscall parents or the outer caller/context. Complete aggregate
preparation and coherent simulator-wide CPU cuts must still reject until those
owners and all configuration-specific simulator/bridge/memory state are
implemented and independently audited. BOOM/Saturn remain pending; physical
FPGA validation, standalone Shuttle and ASIC power remain outside this task.
