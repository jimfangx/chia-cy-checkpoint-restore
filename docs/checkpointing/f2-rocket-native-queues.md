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

Iteration 279 registers request admission before selecting the native RAM
address. Adapter policy version 3 specifies four edges including acceptance:
phase 0 accepts/stores selectors, phase 3 borrows from those registers, phase 1
samples the returned raw data and re-primes the original reader, and phase 2
publishes the response. It reuses the existing two-bit phase register and all
fourteen original observation fields. The acceptance permission path no longer
selects the RAM address on the accepting edge. Reset still cancels/re-primes;
lost functional hold invalidates preparation even if hold returns before data
sampling. Reader drain and immediate transport fault revocation remain required.

The independent FIRRTL audit requires the actual borrow, phase and hold-loss
equations. Fresh EDA checks cover all four reset phases, every unfinished release
phase, transient preparation hold loss, exact latency and the actual borrow net
before each acceptance. Compiled admission and hold-loss mutations join retained
payload and observation corruption checks. These checks pass in fresh source-bound EDA SP2 processes;
consult current selected receipts under `runs/aws-f2/iteration279/`.

The old/new readout initially shared a state-shape-only stream identity. Capture
manifest version 2 now hashes the emitted queue RTL, all four complete bank
bindings and every transport RTL source. Shape-preserving protocol, emitted RTL
and transport changes must change the DMA header digest. The VCS oracle checks
that digest before acknowledging the header; incompatible-manifest mutation is
separate from payload/selector corruption. This remains a component protocol,
not canonical CPU images or production restore admission. Full-image ownership,
physical capture and paired CPU migration remain pending.

The iteration-279 F2-part synthesis retains 64 URAMs, 11,876 flip-flops and
7,869 logic LUTs, with zero LUT RAM. At unchanged 140 MHz its OOC setup/hold
estimates are -0.832/+0.073 ns, versus the preceding -1.704/+0.073 ns. The
remaining worst path is freeze_low -> physical/snapshot/transport permission
-> accepted-request native_active/D (17 levels, 4.185 ns data delay). The
permission chain no longer reaches the URAM address on its accepting edge.
Full-image timing closure and production physical/common-cut ownership remain
pending. Fresh SP2 queue execution passes all four component cuts with
78,343,201 checks / 983,220 stalls; the full-wave audit passes all 56 original native vectors, three router vectors /
28,146,316 samples and complete four-cut RAM/payload/CRC reconstruction. All
six compiled mutations and eight corrupt/rechecksummed stream negatives reject.
The complete retained EDA scope and six further waveform audits pass. Current
selected receipts retain exact provenance; final source/artifact/protected-input
and resource audits pass. The native and EDA pipelines have completed and joined.
