# Direct HTIF exit and stop component

Iteration 129 adds `firesim_tsi_htif_exit_t` for the default-device direct
pass/fail handler and no-signature stop path. The owner records `running`,
`requested` or `stopped`, and the exact low 32 bits of the original odd
48-bit payload. The installed `syscall_t` handler still performs the actual
exit assignment and failure printing. Its signed status, including truncation
and arithmetic right shift, is checked against the explicit component.
The installed stop runs inside the component guard before `stopped` is
published. Neither service may yield. Interrupted and reentrant services
cannot publish an image.

The kind-31/revision-1 image binds the installed 32-bit integer policy and
the no-signature policy. Parsing validates the complete configuration, length,
phase and raw status before assigning either field. A running image must
have zero status; requested/stopped images must retain an odd 32-bit status.
The image is a component payload, not a complete build-bound `.fsckpt`.

`save_htif_exit_component()` checks the component against installed
`should_exit()`, `done()` and `exit_code()` and rejects unsupported options.
The installed optional exit field, global signal latch and stopped flag
remain distinct unowned state; matching their visible projection does not
inventory or restore them. Generic syscall exit, signal-only exit, external
stop and signature configuration are tested rejection cases. In particular,
this component does not certify signals arriving after an owned exit request.
Historical polling inspection/preparation keeps its existing component
membership and rejects active exit/signal/stop state. It cannot silently omit
the new component at an exit cut. Complete HTIF/CPU admission stays disabled.

The actual proxied `sys_exit` regression now rejects aggregate inspection after
the syscall returns with its inherited exit field set. It retains all eight
historical component readbacks separately, so stronger admission rejection does
not remove the independent child-state checks. The retained earlier evidence
keeps its source-bound historical admission result.

`verify_tsi_htif_exit_vcs` runs production FireSim/TestChip TSI against the
installed FESVR library in native ASan/UBSan and VCS DPI processes. A sealed
BCD read creates a response; the peer holds fromhost occupied, then sends
pass/fail. The queued response forces a real serial-read yield after exit is
requested and before stop. The peer finally releases fromhost and checks stop.
Both cache policies and eight odd payloads exercise positive, negative and
truncating installed statuses. An independent oracle expands every packet,
host tick and complete exit/poll/read/FIFO/terminal image at every sampled cut.

Producers finish before fresh native/VCS destinations start. A destination
loads and reads back the complete explicit exit component before constructing
its installed HTIF reference. It then projects the captured exit/stop state
into that reference and continues the component to stopped. This deliberately
does not restore the source's polling stack, queued response, descriptors or
CPU. First-divergence cases flip a retained status bit, require exact complete
pre-service readback, and stop at projection boundary zero before a continued
stop service. These are host-component faults, not DUT semantic faults or
Rocket target-cycle replay. Production omission controls separately remove
exit recording or stop recording and require the capture checks to fail at
the first affected host boundary.

Exact results and executable commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics remain under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration129/`.
The remaining Level-1 work includes complete installed session/descriptors,
signals, exit/stop fields and outer caller ownership, atomic aggregate
restoration and coherent simulator/CPU cuts. Level-2 still requires actual
semantic CPU capture and boundary trace, complete fresh zero-edge readback
and captured-trace replay. BOOM and Saturn remain pending. No physical FPGA
or ASIC validation is claimed.

Iteration 130 corrects the signal rejection test's delivery assumption.
`raise()` queues a signal when the calling thread blocks it; a successful
return does not mean the installed FESVR handler ran. Passing a blocked
SIGINT/SIGTERM mask through the parent process reproduces the controller's
failure with the original native and VCS binaries. The test now checks the
installed handler, blocks and raises the selected signal, verifies that it
remains pending with the installed global exit latch clear, unblocks it,
verifies delivery and the exit latch, and restores the original mask before
checking production rejection and unchanged serial state. A pristine installed
HTIF reference observes the shared signal latch; the actual final TSI class
still performs the admission check. No host context is entered.

Native and VCS cases cover inherited, explicitly blocked and explicitly
unblocked starting masks for both signals. Revision-1 delivery evidence records
the initial mask, pending signal, observed latch and restored mask; the
independent audit checks all twelve records and all eighteen lifecycle
rejections. Historical summaries retain their original ten-case audit scope.
This only fixes the validation harness. Pending signals, installed lifecycle
fields and complete CPU checkpoints still require explicit ownership.
Iteration-130 diagnostics and commands are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration130/`.
