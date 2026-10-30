# Shared capture of the four Rocket native queues

`CheckpointNativeQueueCapture.sv` connects one coordinated native cut and
MMIO/DMA transport to multiple original synchronous queue endpoints. Each
selected queue retains its original RAM and functional write/advance guards.
The caller binds those guards to `functional_hold`, supplies the complete native
observation vector in manifest order and acknowledges every relevant owner.
All endpoint readers, the routed pending request and backpressured responses
must drain before the sequencer releases its cut. The router holds the selected
owner through response acceptance; invalid banks return an error rather than
aliasing a queue. Overlapping ranges and the reserved snapshot bank reject at
elaboration. Its pending/invalid/owner registers join the live control readout.
That readout is not an atomic capture of the transport itself or a restore ABI.

`RocketNativeQueueCaptureSpec` extracts the original `Queue_56` definition from
the retained exact-recipe generated source and builds an explicitly isolated
four-lane component. It preserves the 512-bit by 6,144-entry geometry and ULTRA
policy, generates twenty independent original-state descriptors and forwards
all fourteen native fields per queue: 6,656 bits total. The synthetic host is
not the running Rocket simulator. Its original unused SYNC gate remains an
explicit uncovered owner; complete production physical-clock admission stays
rejected. No CPU, hart, functional DRAM or semantic coverage follows from this
component's complete queue readout.

`verify_rocket_native_queues.py` synthesizes on the localhost F2 part and requires
sixteen URAMs for each of the four original memories, without distributed or
BLOCK fallback. Fresh EDA SP2 VCS fills every memory through real enqueue traffic,
then exercises independent lanes, backpressure, common cuts and complete memory,
register and staged-native transfer. Original state expectations follow the
functional input history, including Chisel's retained `maybe_full` flag. It is
not equivalent to a full-occupancy predicate. Every offered payload is checked
before its accepting DMA edge. Missing/faulted owners and abort/drain are separate
processes. Debug waveforms retain the full signal scope with lossless compression.

`audit_rocket_native_queues.py` streams those waveforms, reconstructs each
sampled vector from all 56 underlying native register vectors and rebuilds every
original RAM word and pointer from the actual enqueue/dequeue inputs. It checks
each frame's selectors, cycle label, payload, manifest and CRC independently.
The router's three original register vectors must match the exposed control bits.
Compiled swapped-native, corrupted-payload and selector-overlap checks run in
separate fresh EDA processes. These component frames are not canonical `.fsckpt`
or `.rtlckpt` images.

Iteration-277 commands and receipts belong beneath
`automations/checkpoint_loop/runs/aws-f2/iteration277/`. Consult its selected
receipts and `progress.md` for completed verification. Production common-cut,
transport self-state/composite restore, all simulator/memory/timing/bridge/host
and pre-FAME owners, full-image timing/P&R/AFI, physical all-hart captures,
FPGA-reference comparison, paired zero-edge/finite/live CPU migration and rolling
hardware recovery remain required. No hardware acceptance column advances.

Iteration 278 strengthens complete stream ownership: the independent decoder
requires each original/native selector exactly once in immutable descriptor
order, and checks the header's zero sequence. A self-consistent duplicated
address with a repaired CRC cannot substitute for an omitted word. The VCS
oracle separately derives selectors from the generated manifest and checks
each offered data frame before DMA acknowledgement. Seven focused cases cover
healthy zero-valued state, duplicate RAM/native words, duplicate lane owners,
reordering, truncation and noncanonical header sequences. Additional actual
component-stream mutations retain genuine copied payloads and repaired CRCs.
Current native, EDA, independent-wave and compiled mutation evidence belongs
under `runs/aws-f2/iteration278/`; no CPU or hardware acceptance follows.

The final iteration-278 localhost F2-part synthesis retains all 64 URAMs,
11,876 flip-flops and 7,874 logic LUTs, with no LUT memory. Its unchanged 140 MHz
OOC setup/hold estimates are -1.704/+0.073 ns; timing closure and full-image
implementation remain pending. All seven affected broad source sets now have
strict current-source native receipts (three completed attempts recovered
without relabeling, four rebuilt), alongside the two refreshed snapshot owners.
Nine unrelated native receipts retain their exact original provenance. Peak
native concurrency is two. Fresh EDA four-cut transfer and its independent full-wave audit now pass;
all sixteen bank/region scopes and the complete retained regressions / six
additional waveform audits now have passing fresh EDA receipts.

The current critical setup path is concrete, not a URAM-capacity issue:
`physical/freeze_low_reg` (falling raw edge) -> physical readiness -> snapshot
failed/request-ready -> native failed -> transport cut/read-enable -> routed
borrow -> q0 URAM cascade address. It has 18 logic levels and a 3.572 ns
half-cycle requirement (4.558 ns estimated data delay). Next timing work should
shorten this permission/address path while preserving immediate owner/fault
revocation, accepted-reader drain and original queue state; do not mask the
path with a frequency change or an unsupported timing exception. The complete
production CE/common-cut binding remains a separate prerequisite for an image.

The final iteration-278 source/receipt/protected-input/resource/individual-artifact
audit passes. Its selected catalog binds all four 196,728-word cuts and complete
lossless waves. Original EDA paths remain in receipts. All non-LLM build/EDA jobs
and the failed managed delegation are finished; no worker remains. No canonical
CPU checkpoint, checkpoint-enabled AFI or physical migration is claimed.
