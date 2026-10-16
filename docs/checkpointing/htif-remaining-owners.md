# Remaining HTIF owners after protocol/lifecycle preparation

As of iteration 140 the guarded sealed transaction restores fourteen
protocol/device/direct-exit/provider components, including completed direct-exit
images. It still prohibits complete context entry. The following inventory explains the
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
| HTIF termination | The fourteen-owner group now owns the actual private optional exit/stopped fields and direct-command caller through no-signature stop, including fresh complete stopped-group readback. The proxied-syscall exit caller, signature stop, session destruction/return and outer context remain unowned. `exit_code()` still cannot substitute for raw optional-state ownership. |
| Signals | Iteration 142 adds an independent exact-provider signal/lifecycle component with actual delivered-latch restoration, fixed masked/no-pending/action policy and atomic peer publication ([contract](tsi-htif-signal.md)). The fourteen-owner polling group still rejects delivered signals. Cross-thread coordination, signal-caused stop callers and complete process ownership remain pending; the reference constructor does not reset the shared latch. |
| Inherited devices | `htif_t` always contains its own syscall proxy, BCD, device table and dynamic-device vector. The supported FireSim caller uses a separate session table/syscall and its owned BCD. Binding one table does not inventory the other. |
| Active session and descriptors | The session owns `syscall_t` tables, `fds`, `fds_index`, `chroot` and destination HTIF/memif references. Preserve descriptor aliases/shared open-file descriptions, offsets and external input/output policy when affected; raw host descriptor numbers are process-specific. |
| Generic memif read | Iteration 127 adds an explicit head/tail/body caller with owned output bytes, body cursor and pending serial child ([contract](tsi-memif-read.md)). Iteration 128 binds it through the default syscall session's virtual memory interface, preserving per-chunk cache flushing and separate startup loadmem dispatch ([production contract](tsi-runtime-memif-read.md)). The installed syscall parent, destination buffer, arguments and return continuation still use their native stack and remain unowned. Active generic reads cannot enter the twelve-owner polling aggregate. |
| Proxied syscall | Iteration 144 adds a restricted executable syscall-93 parent with nested memory callers and atomic caller/serial/actual-lifecycle restoration ([contract](tsi-syscall-exit.md)); it is not wired into live polling dispatch. General syscalls remain unowned. The eight-word `magicmem` request, syscall selection and arguments, input/output buffers, host-operation result/errno and the return-memory write cursor can outlive a nested target yield. Filesystem, cwd and chroot effects require explicit ownership or rejection. |
| Outer host execution | The component service bypasses startup/reset/stop and never initializes a coroutine. Restoring `tick()` additionally needs the host/target context lifecycle and executable outer caller, without replaying startup or consuming an extra host tick/target edge. |

The current native/VCS device-lifetime suite provides a useful distinction.
An installed HTIF construction adds three descriptors to the external baseline;
a live FireSim polling session adds three more. Destruction/normal return
releases the expected descriptors at all tested cuts. A metadata-only prepared
TSI does not construct that session. Lifetime correctness therefore cannot be
used as evidence that the active syscall session or its descriptor semantics
have been restored. See [tsi-default-device-lifetime.md](tsi-default-device-lifetime.md).

Iteration 131 added an opt-in exact-header provider adapter for the actual
private exit/stopped fields, with fresh native/VCS component readback and
atomic rejection checks ([contract](tsi-htif-lifecycle.md)). It distinguishes
absent/present zero and all raw status bits without executing a restore-time
service. Later opt-in exact-recipe builds explicitly link that provider;
iteration 140 restores complete direct-exit groups through the guarded aggregate
([contract](tsi-polling-lifecycle.md)). The ordinary recipe does not implicitly
select the provider or enable a CPU profile. This does not restore process
signals, the exit caller, sessions/descriptors or any context. The inventory
above therefore remains the list of owners required for full HTIF acceptance.

In the checked-out reference, an odd device-0 payload directly assigns the
optional exit value and returns without a response. A proxied `sys_exit` assigns
an encoded value through `htif_exit`, writes back its syscall result and queues
a response. Capturing only one exit path, or calling `stop()` immediately at the
first exit request, can change pending fromhost transactions. `stop()` can also
perform signature-memory reads/file output before setting `stopped`; current
metadata preparation rejects signature-mode arguments. Preserve these
restrictions until the corresponding paths have native continuation checks.

Next implementation work must own the session, descriptor, syscall-parent,
process signal and executable outer-context boundary. The restricted direct-exit
component no longer lacks stopped-image preparation. General memif/syscall services
must remain rejected whenever their complete caller or external state is not
owned. The existing eight-owner unsealed inspection and twelve-owner sealed
component preparation are audits/component interfaces, not CPU admission.
Coherent simulator-wide Level-1 CPU cuts and fresh continuation remain pending.
Independent Level-2 captured Rocket replay passes separately at four retained
cuts. No physical FPGA or ASIC evidence is claimed.
