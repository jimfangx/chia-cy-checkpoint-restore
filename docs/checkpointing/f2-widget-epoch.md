# Widget endpoint restore epoch

Iteration 265 moves the actual checkpoint widget endpoint equations into a
shared Scala builder. The production widget and the restore-enabled component
use the same adapter, eight original local registers, MMIO arbitration, DMA
accounting and shadow access. The builder emits these registers in its caller;
it preserves the production hierarchy rather than adding a new RTL owner.

The opt-in interface restores 758 canonical bits: 228 local bits followed by
the existing 530-bit NASTI adapter layout. One accepted positive edge loads all
46 original registers. Acceptance requires hold, matching epoch labels,
quiescent-owner certification, no owner error, inactive reset and valid adapter
padding. A rejected load performs no restore writes; reset retains priority.
Hold or any load attempt
suppresses MMIO/AXI and stream handshakes, autonomous local updates and shadow
access. The opt-in endpoint also suppresses handshakes during reset.

Production has no restore controls. The transport controller, physical cut,
stream engine, upstream master, backend response owner, shadow staging,
functional memory and host state still need complete common-epoch ownership.
A caller-supplied quiescence certificate does not establish those owners. The
regional compiler continues rejecting the eight self-freezing transport locals;
this component does not waive that guard or admit a complete checkpoint image.
The six protocol cuts and epoch 42 used by the component test are fixture
labels, not measured FPGA target cycles. Its text images are neither `.fsckpt`
nor `.rtlckpt` files.

The previous iteration's reported final audit did not survive controller replay:
its preflight script overwrote a pinned receipt with a later observation.
`f2_preflight.py` now creates a fresh directory per attempt, binds its evidence
and producer sources, and atomically selects successful receipts. Failed checks
retain the previous selection. Its strict auditor rehashes every artifact and
protected input. Iteration 264's overwritten receipt and failing audit remain
unchanged; new recovery evidence belongs to iteration 265.

Execution receipts, failed development attempts and runnable commands are under
`automations/checkpoint_loop/runs/aws-f2/iteration265/`. Full image place/route,
AFI creation, checkpoint-enabled F2 deployment, active four-hart cuts, paired
FPGA-origin migration, live clean RTL and rolling FPGA recovery remain pending.

Native localhost synthesis passes both integrated geometries. The exact Rocket
32/12 component uses 700 LUTs / 519 flops; the 32/4 component uses 699 LUTs /
487 flops. All flops remain on the raw positive clock. The restored original
registers implement 486 and 454 bits respectively; the additional shadow
storage is separately unsupported. These are component OOC results with
unconstrained I/O, not full-image timing closure. Source-policy OOC retains
negative 140 MHz setup/hold estimates of -0.179/-0.074 ns.

Final verification passes 320 Scala tests / 50 suites plus twelve preparation
checks, 337 Python / 52 manager tests and all 23 native / 23 fresh native-bound
EDA SP2 component scopes. At each of six protocol cuts in both geometries,
separate donor/restored processes compare 2,000 continuation cycles after
independent complete original-register readback. All implemented bits load both
zero and one. The four semantic/compiled negatives reject; direct original-state
waves find the compiled localData fault first at bit 195 while held, with zero
normal edges and no acknowledgement. ASan/UBSan, FCFS/atomic-cut and all retained
physical/waveform audits pass. The final source/input/receipt/protection/resource
audit passes. No checkpoint-enabled image or FPGA-origin migration is established.
