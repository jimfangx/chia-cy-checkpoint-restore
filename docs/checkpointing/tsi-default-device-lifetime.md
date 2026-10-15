# Default HTIF device lifetime

Iteration 114 moves the default HTIF syscall device and device table from the
`run_host()` coroutine stack into the production `firesim_tsi_t` object. The
installed syscall device allocates command tables and duplicates stdin/stdout
three times. Discarding a suspended native stack does not invoke its destructors.
The previous implementation therefore leaked those three descriptors and device
allocations when a suspended TSI object was destroyed.

The new session owns the unchanged installed `syscall_t` and `device_list_t`.
Its table registers the same syscall and BCD devices in the same order. TSI
destruction releases the table/syscall before BCD and the polling callback owner;
normal HTIF completion explicitly releases the session after `stop()`, preserving
the former return-time descriptor release. No extra target services, reset,
memory access, coroutine entry or target edges are introduced.

This is process-local resource ownership. It does not serialize syscall tables,
descriptors, host files, terminal state or native frames. Semantic syscall,
terminal, HTIF configuration/stop/exit/signal and aggregate CPU reconstruction
remain pending. Custom-device/long-option execution keeps its existing installed
HTIF route. Intentionally retained TSI objects retain their device session until
normal completion or destruction. Open-file syscalls and constructor resource
exhaustion are outside this resource test; the installed implementation is
unchanged. Complete CPU checkpoint admission remains disabled.

The installed headers and production dispatch give this ownership inventory:

| State/resource | Lifetime after this change | Semantic checkpoint requirement |
| --- | --- | --- |
| Syscall `htif`/`memif` pointers | Session refers to its owning TSI/installed memif | Rebind in a fresh supported caller; never serialize pointers |
| Syscall dispatch/command tables | Installed `syscall_t`, destroyed with the session | Bind installed implementation/build and supported syscall policy |
| Syscall `fds`/`fds_index`, `chroot` | Installed object; tested default standard-stream duplicates close on return/destruction | Audit filesystem/descriptor state before admitting any affected cut |
| Device table, null device, registration count | Session owns the installed table; syscall is device 0, BCD device 1 | Reconstruct the exact configuration and reject unsupported devices |
| BCD pending commands | Existing pointer-free BCD component | Restore commands and rebind responses to the destination polling owner |
| Terminal input/output and process termios | External installed terminal service | Explicit replay/transport ownership remains required |
| Active syscall `magicmem` and nested memif locals | Suspended native frames remain unsupported checkpoint state | Reject active services; semantic reconstruction is separate work |
| HTIF startup/configuration, stop/exit/signal | Existing installed object/component contracts | Complete aggregate ownership remains required |

Native sanitizer and VCS DPI checks pass in:

`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration114/device-lifetime/invocation-as3onvw3/summary.json`.

Each backend checks 176 actual production TSI instances across 11 cuts, with
16 repetitions each: pristine, startup loader, first/partial poll, idle, pending
BCD read, pending/partial syscall read, returned `sys_exit` with its response
pending, and normal PASS/FAIL completion. This includes 128 suspended instances
and 32 completed instances per backend. Every destruction preserves the complete
external descriptor map; active sessions and completed callers also have their
expected descriptor counts checked. Actual ELF load/merge packets, pending BCD
command bytes, installed syscall packets and stop/exit results are checked.
No sanitizer suppression is used. ASan emits its standard limited
`makecontext`/`swapcontext` support warning; native VCS and descriptor readback
provide additional independent checks.

The retained original source/header reproduce three leaked descriptors at the
first polling cut (`original.log`, expected exit 3). Both original translation
units use the original class layout. The initial missing-include, output-path
collision and incorrect BCD packet-expectation pilots remain in separate
invocation directories. They do not certify the final source.

Run a fresh check from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_device_lifetime_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration114-controller-rechecks/devices \
  --negative-control-source automations/checkpoint_loop/runs/m11-iteration114/original-default-devices/firesim_tsi.cc
```

The optional retained-source control compares resource behavior; the positive
tests always compile current production sources. Each invocation records native
compiler/VCS commands, results, exact ELF bytes, source snapshots and artifact
hashes. Re-audit a saved invocation with `--audit /absolute/path/to/summary.json`.
The CPU matrix records the separate full-recipe and ordinary RTL checks.

## Next configuration increment

The installed nonvirtual `htif_t::set_expected_xlen()` can be called through a
base reference, so a derived shadow setter cannot own its policy. Current
preflight tests reject incompatible XLEN but accept both 0 and 64 for this
64-bit ELF. One possible follow-up is a scoped observer of the actual
`required_xlen` argument received by the explicitly linked owned `load_elf()`
during the qualified HTIF preflight. This could bind the exact installed policy
without private-member access or an installed-header edit. It would need native
production-provider checks, nested/unexpected-call rejection, a versioned image
contract and atomic source/destination policy tests. This proposal is not
implemented or verified in iteration 114.
