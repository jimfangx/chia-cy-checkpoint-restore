# Remaining HTIF owners after twelve-owner polling preparation

Iteration 126's sealed transaction restores twelve protocol/device components.
It still prohibits complete context entry. The following inventory explains the
remaining boundary; it does not grant whole-HTIF or CPU checkpoint support.

The installed `htif.h`, `syscall.h`, `memif.h` and `device.h` are byte-identical
to the checked-out FESVR headers. The actual Rocket build-local archive retains
the installed `htif.o`, `syscall.o` and `memif.o` bytes. Its symbol inventory
contains the local `signal_exit` state and the actual HTIF exit/stop methods.
These checks bind the inventory to actual headers and providers; they do not
prove binary equivalence to the checked-out implementation source. Exact
hashes, native `nm` commands and the current lifetime-test binding are in
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration126/htif-remaining-owner-audit.json`.

| Owner | State and continuation that still need an explicit contract |
| --- | --- |
| HTIF termination | Private `std::optional<int> exitcode`, `stopped`, and the caller's progress from exit request through final device/fromhost work, `stop()` and return. `exit_code()` shifts the stored value and cannot distinguish absent exit from a requested zero exit. Getter-only restoration would omit state. |
| Signals | Translation-unit `signal_exit`, registered handlers and the policy for delivery across a cut. The reference constructor installs handlers but does not reset the shared flag. A per-instance POD image cannot silently replace process-wide signal ownership. |
| Inherited devices | `htif_t` always contains its own syscall proxy, BCD, device table and dynamic-device vector. The supported FireSim caller uses a separate session table/syscall and its owned BCD. Binding one table does not inventory the other. |
| Active session and descriptors | The session owns `syscall_t` tables, `fds`, `fds_index`, `chroot` and destination HTIF/memif references. Preserve descriptor aliases/shared open-file descriptions, offsets and external input/output policy when affected; raw host descriptor numbers are process-specific. |
| Generic memif read | The serial-read owner holds one transport chunk. Installed `memif_t::read` also retains unaligned head/tail buffers, address/length/output cursor and aligned-body loop position on its native stack. Owning the serial child does not reconstruct this caller. |
| Proxied syscall | The eight-word `magicmem` request, syscall selection and arguments, input/output buffers, host-operation result/errno and the return-memory write cursor can outlive a nested target yield. Filesystem, cwd and chroot effects require explicit ownership or rejection. |
| Outer host execution | The component service bypasses startup/reset/stop and never initializes a coroutine. Restoring `tick()` additionally needs the host/target context lifecycle and executable outer caller, without replaying startup or consuming an extra host tick/target edge. |

The current native/VCS device-lifetime suite provides a useful distinction.
An installed HTIF construction adds three descriptors to the external baseline;
a live FireSim polling session adds three more. Destruction/normal return
releases the expected descriptors at all tested cuts. A metadata-only prepared
TSI does not construct that session. Lifetime correctness therefore cannot be
used as evidence that the active syscall session or its descriptor semantics
have been restored. See [tsi-default-device-lifetime.md](tsi-default-device-lifetime.md).

In the checked-out reference, an odd device-0 payload directly assigns the
optional exit value and returns without a response. A proxied `sys_exit` assigns
an encoded value through `htif_exit`, writes back its syscall result and queues
a response. Capturing only one exit path, or calling `stop()` immediately at the
first exit request, can change pending fromhost transactions. `stop()` can also
perform signature-memory reads/file output before setting `stopped`; current
metadata preparation rejects signature-mode arguments. Preserve these
restrictions until the corresponding paths have native continuation checks.

The next implementation should select and validate its supported lifecycle
explicitly, bind every actual state owner, and test restored exit/stop/signal
behavior against the actual installed provider. General memif/syscall services
must remain rejected whenever their complete caller or external state is not
owned. The existing eight-owner unsealed inspection and twelve-owner sealed
component preparation are audits/component interfaces, not CPU admission.
Coherent simulator-wide CPU cuts and independent Level-2 captured replay remain
pending. No physical FPGA or ASIC evidence is claimed.
