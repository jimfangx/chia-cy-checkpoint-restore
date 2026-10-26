# Atomic transport control shadow

Iteration 242 adds `CheckpointTransportControlSnapshot.sv`, a synthesizable
staging bank for the complete `481 + GATES`-bit source-register vector described
in [f2-transport-control-state.md](f2-transport-control-state.md). It samples the
whole vector and its target-cycle label on one accepting raw-clock positive
edge. The source values are those immediately before that edge, including the
physical mask settled at the preceding falling edge. Bank words are read from
the immutable copy, with zero padding and bounded 32-bit addresses.

The caller must explicitly certify the acknowledged cut and absence of owner
faults. A missing cut or owner fault rejects before publishing any word, with
sticky errors until reset. A busy bank backpressures new requests; release and
abort suppress visibility immediately and prevent acceptance on that edge.
Release without a snapshot is a sticky protocol fault. Abort discards an epoch
without clearing errors. Reset clears all staging storage and metadata.
After a successful copy, later source activity, target-cycle advancement and
source-owner failures cannot change the retained epoch. Snapshot release is a
consumer operation; reading words introduces no further source sampling edge.

This is a component, without a production owner or restore adapter. The caller's
cut certificate is an obligation, not proof that FASED, DRAM, reset, external
writers or host owners have stopped. Existing widget, inventory and image
emission guards remain unchanged. The shadow itself introduces storage needing
an explicit restore/reset mapping. The five native FSM encoding registers remain
unsupported, as do stream/MMIO queues and other external owners. No checkpoint
image, AFI, FPGA capture or CPU migration acceptance follows from this component.

`verify_transport_control_snapshot.py` binds the new RTL to the existing exact
transport source schema and retained generated readout. Its localhost Vivado
fixture connects the actual physical transport to the shadow with unconstrained
protocol inputs. It checks all native storage, raw clock polarity, four shadow
fields and the separately retained native FSM encodings. EDA VCS exercises every
packed bit for gate counts 1, 3 and 65, including the 512-bit crossing, randomized
epochs, valid and invalid bank addresses, publication, busy requests, source
advancement/faults, abort, reset and invalid admission. A separate compilation
zeros a captured bit and must fail on the first differing word.

The integration monitor independently reconstructs all 24 real transport
registers immediately before capture, then checks every bank word during actual
MMIO/DMA activity, owner faults, abort/drain and reset recovery. Hierarchical
reads belong only to this EDA component oracle. They are never hardware capture.
Full debug VCDs, exact sources/commands, native DCP/netlist/resource reports and
source hashes belong under `automations/checkpoint_loop/runs/aws-f2/iteration242/`.

The first native attempt synthesized but its source-immutability guard rejected
the receipt when the integration monitor was corrected during execution. Its
logs remain separate; successful results must come from the fixed-source rerun.
An additional final audit found that the nonzero DPI exit bypassed VCS waveform
flushing. The test oracles now explicitly `$dumpflush` before invoking that exit.
Both synthesis and the complete new EDA scope were rerun with those fixed sources;
the original time-zero-only negative wave and failed audit remain historical.
The initial flush injection altered the DPI declaration as well as its calls;
the actual EDA syntax diagnostic is retained. The final generator instruments
only failure calls and explicitly checks the unchanged DPI declaration.
The independent SP2 exit probe shows `$dumpflush` is scheduled at the end of the
time slot: calling the DPI exit immediately still loses the waveform. A one-ps
wait after the flush preserves it without reaching another clock edge. The probe
also records that `$fatal` alone exits with status zero in this environment, so
the nonzero DPI exit remains required. The final versioned verifier rejects every
time-zero-only wave and independently checks the negative wave's two cycle labels.

The fixed-source run passes native synthesis with **552 shadow registers**, all
on the positive raw clock, and **1,052 total registers**. The five existing native
FSM encodings are still separately accounted for and unsupported. EDA passes
**1,614 standalone captures / 80,952 word checks** and **eleven integration
scenarios**. The captured-bit defect fails on the first unequal word of snapshot
cut **100**, observed at source cycle **107**, word **0**, capture **1**. The final
audit independently reads both cycle labels from the negative VCD. This is a
component readout check, with no clean-RTL edge acknowledgement claim.
All **sixteen debug waves**, source files and native artifacts match their
receipts. The independent manager/EDA audit passes. The retained 318 Python and
40 loop tests plus generated-bank, widget, ASan/UBSan host, FCFS and cut-controller
regressions pass. The prior Scala sweep remains historical; no Scala source was
changed in this increment.
