# Coordinated physical cut and native reader staging

`CheckpointNativeStateCapture.sv` composes the common-source physical clock cut
and the complete native-vector snapshot with an ungated sequencer. It is a
component integration interface. Whole-Rocket compilation still requires the
production physical, memory, bridge, host and semantic ownership contracts;
this interface does not discharge them or admit a checkpoint-enabled image.

An accepted capture enters `WAIT_CUT`. The controller holds original raw-clock
native storage through `functional_hold` and requests the physical falling-edge
mask. Native borrowed readers and checkpoint control keep their original raw
clock. Other covered positive-edge owners use the masked root or native gates.
The caller must implement the hold at every original native advance/write site
and supply independently established owner presence, freeze and error signals.
The sequencer waits for the physical post-stop acknowledgement, all additional
freeze acknowledgements and idle readers before entering its single `SAMPLE`
edge. That edge stages every native observation bit and the settled target cut
label together. Sampling precedes borrowed-reader permission.

`READ` exposes indexed staging words and permits native bank requests. Release
revokes both permissions before its accepting edge, then enters `DRAIN`. An
already accepted native response can still complete and encounter backpressure;
the physical mask and original native hold remain asserted. Only idle readers
permit snapshot release. The next phase withdraws the physical request while
retaining local hold until the physical controller validates and opens the mask
at a falling edge. Original execution can then resume. New capture/release
commands use the stated phase/ready contract; invalid commands and unauthorized
borrow attempts fail closed.

Missing or faulted owners, lost freeze or physical-cut acknowledgement, CE/cycle
drift and snapshot faults revoke publication/borrow permission before an edge.
Sticky failure holds the entire component until reset, even after host commands
are withdrawn. The readout exposes every snapshot register, every physical-cut
register including the falling-edge mask, and the sequencer phase/errors. This
live composite readout is neither an atomic snapshot of its own control domain
nor a production restore ABI. Existing snapshot-owner restore remains separate;
restoration of this whole composite owner is not implemented.

Capture readiness is independent of the command input, including when an owner
is absent. A producer may qualify its command pulse with readiness without
creating a ready/request loop. Rejected commands on the sampling edge preserve
the prior retained payload and cut label. Sampling qualification uses independent
command inputs, avoiding feedback through the snapshot's ready/error outputs.

The native/EDA harness is
`tools/checkpoint_formats/tests/verify_native_state_capture.py`. It requires an
unchanged source-bound emitted-queue synthesis receipt and uses the installed
native BUFGCE/glbl models. Its queue wrapper connects the generated original
hold/write guards and bank request handshakes directly to the new controller.
The host's original unused always-on BUFGCE remains separately identified; it
is not silently counted in the controller's captured-CE vector. Independent
software queue/RAM and emitted-register oracles test original-state preservation,
raw reader activity, staged-vector immutability and release with a real stalled
RAM response. A separate waveform audit reconstructs the complete composite
readout from twelve underlying register vectors and checks preedge sampling.
The fixture holds reset through the unmodified vendor global startup and real
gated reset edges, then checks every original target/gated edge. Initially
unknown native selector bits remain visible in the first queue snapshot; they
are neither masked nor initialized through a backdoor. These diagnostic hex
snapshots are not canonical published checkpoint images.

All diagnostic logs, commands, native DCPs/reports, models, directed component
snapshots and debug waves belong under
`automations/checkpoint_loop/runs/aws-f2/iteration274/`. They are component
evidence, not FPGA-produced `.fsckpt`/`.rtlckpt`, CPU replay or live acceptance.
Consult the current progress note and immutable selected receipts for completed
verification and the remaining hardware acceptance requirements.

Iteration-274 final component checks pass: native owner 1,189 registers / 575
LUTs (OOC setup +0.913 ns / hold +0.073 ns at 140 MHz), seven VCS geometries /
105 negative processes, seven receipt corruptions, 113 independent original-register
wave audits and 114 debug waves. Four queue cuts (75/129/190/258) pass 180 bank
reads and 1,324 serial words while the live vector changes 1,320 times. All
retained regression scopes pass; full-image and hardware CPU acceptance remain
pending. Exact commands and immutable source/native/EDA receipts are in the run.
