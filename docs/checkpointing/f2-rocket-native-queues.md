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
