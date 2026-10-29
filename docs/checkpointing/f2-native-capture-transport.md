# Native staging in the MMIO/DMA capture path

`CheckpointNativeCaptureTransport.sv` connects the coordinated physical/native
cut controller to the existing checksummed MMIO/DMA transport. It is a component
integration interface. Production Rocket ownership checks remain unchanged;
this module does not establish complete capture, restore or a deployable image.

The MMIO start command requests the physical cut. The transport waits for the
sequencer to freeze every additional owner, stage the entire native vector on
one raw edge, and grant read access. Original functional bank requests can then
borrow native readers. Their descriptor ROM remains external and must include
every functional/physical owner assigned to that network. The complete generated
manifest must bind both those descriptors and the appended native descriptors.

The reserved snapshot bank defaults to `0xfc`. Original descriptors that alias
it are rejected. Native slot 0 contains `BITS/64` full 64-bit words when nonempty;
slot 1 contains a single `BITS%64`-bit tail when nonempty. Neither zero-depth nor
zero-width descriptors are emitted. Each native response is held in a separate
64-bit response register until accepted. DMA backpressure cannot resample the
live native pipeline. Target-cycle labels and CRC framing use the existing
transport format. These diagnostic component streams are not canonical CPU
`.fsckpt` or `.rtlckpt` images.

Publish or abort withdraws the transport request. The native sequencer revokes
new reads, drains existing native and staging responses, releases its snapshot,
then waits for the physical falling-edge unmask before allowing another start.
The wrapper's `freeze` requests additional-owner quiescence and includes the
accepting transport edge and the whole native release interval. Original
raw-clock functional write/advance sites use the separate `functional_hold`:
it starts after that last accepting edge, matching the physical root's last
edge before the falling mask. Using the transport request at those sites would
stop original native state one edge early and create an inconsistent cut.
`reader_idle` must cover all accepted original bank requests
and backpressured responses; it cannot mean merely that no new request is offered.
Other owner acknowledgements must remain valid until the extended hold ends.

Start backpressure is derived from the registered native phase and independent
owner inputs. It does not feed the release-qualified `capture_ready` back into
the accepting MMIO command. Borrow intent uses the literal registered transport
REQUEST state (4 in its existing non-recoded live-state ABI), before grant
or endpoint-ready qualification. Generated endpoints can qualify their ready
with native permission too. Feeding either ready or the accepted handshake through the transport's fault
qualification would create a structural permission loop. Native synthesis must
check for such loops; simulation convergence alone is insufficient. The original
transport's status idle bit describes its own phase; `mmio_ready` is authoritative
for the combined command handshake. Abort/status commands remain available during
release, while a new start waits for physical release and present, healthy owners.

The live `control_state` vector exposes every existing native-owner register,
every transport/coordinator register and all three new response registers. Its
width is `BITS + GATES + 627`; it is neither an atomic self-snapshot nor a restore
ABI. Complete transport/host ownership and a production restore mapping remain
required. Sticky native faults retain the physical/local hold after host abort;
a failed capture does not authorize functional execution to resume.

`tools/checkpoint_formats/tests/verify_native_capture_transport.py` binds native
F2-part synthesis to exact source/model bytes and a nonzero fixture manifest.
Its EDA-only SP2 checks use the installed vendor BUFGCE/glbl models, independent
functional and raw-pipeline oracles, preedge frame comparisons, original-register
waveform reconstruction and independent host CRC/descriptor/vector auditing.
Thirteen identity planes distinguish every native bit through the largest tested
vector. The restart test alternates consumed and stalled publish responses so an
unconsumed MMIO response cannot mask a missing physical-release guard. Compiled
mutations cover a staged-bit permutation, one-edge-early native hold, missing
restart guard and corrupt native DMA data.
All diagnostics belong under `automations/checkpoint_loop/runs/aws-f2/iteration275/`.
Consult that iteration's immutable receipts and progress note for actual test
results. No full-image, physical CPU capture or migration acceptance follows
from these component checks.

Iteration-275 final component receipts pass: native Vivado 2025.2 maps all
1,666 register outputs separately, with 2,597 LUTs, four SYNC gates, one
falling-edge mask and no combinational/latch loops. OOC setup/hold at the
unchanged 140 MHz frequency is −0.859/+0.073 ns; setup closure remains pending.
Fresh SP2 passes seven geometries through 6,656 bits, 112 complete frame
captures, 42 fault cases, 21 abort/recovery cases and all four compiled mutations.
The independent manager audit verifies every frame/native bit, all 33 underlying
register vectors in each of 70 ordinary process waves, and all 74 debug waves.
Exact source, native/EDA receipts and per-cut commands remain under this run.
