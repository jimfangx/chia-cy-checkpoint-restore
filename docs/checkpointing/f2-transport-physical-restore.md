# Parked physical transport restore

`CheckpointTransportPhysicalRestore.sv` applies the staged layout-v1 register
vector to real `CheckpointPhysicalCaptureTransport` registers. It is a
permanently parked destination component, not a production restore owner.
The existing capture modules default to `RESTORE_ENABLE=0`; the production
Scala widget explicitly disables and ties off every restore input. Both
production reservation and register-observation contracts reject enabled
restore specializations. Source hashes bind the changed implementation.

The supervisor holds the physical clock mask from initialization, including
reset. It retains the producer's offered vector and source-cycle label,
loads the 23 positive-edge register fields, then loads the falling-edge
`freeze_low` field on the following negative edge. It checks the entire live
register vector before presenting the final apply handshake. The staging
producer must retain its offer until that handshake; the supervisor checks
offer stability, source-cycle identity and the external cut/owner certificates
through every phase. Current faults suppress write strobes and acknowledgement
before the relevant edge. Errors remain sticky until reset.
Offers and certificates obey the ungated source clock's synchronous contract;
asynchronous owners need their own captured and synchronized fault protocol.

The additional mask stays asserted even when the restored `freeze_low` bit is
zero. MMIO request/response, bank request/response and DMA handshakes remain
isolated. The retained MMIO response register is still observable in the exact
state vector while its external valid is masked. Normal controller updates
remain disabled, allowing complete pre-target-edge readback of arbitrary raw
encodings, including pending responses, outstanding reads and transport errors.
Reset must cross both source-clock edges to initialize both edge domains.

There is deliberately no release. A failure after positive-edge loading can
leave a partially written destination; permanent parking quarantines it until
reset. This component neither rolls back partial loads nor validates complete
semantic CPU state. Restored raw encodings must not be admitted to execution
without a complete owner and continuation protocol.

Production integration still needs stream buffers, pending bank responses,
MMIO and host obligations, shadow/staging/supervisor ownership, functional
memory, FASED/native clock owners and pre-FAME semantic state. A common-cut
release must preserve all of those obligations and their target timing.
Local full-image implementation/timing/AFI, actual active Rocket F2 captures,
complete paired EDA readback, finite replay, sustained live clean-RTL execution
and rolling hardware recovery remain pending. No image-emission guard is
relaxed by the parked component.

`tools/checkpoint_formats/tests/verify_physical_transport_restore.py` routes
native synthesis to localhost and VCS to EDA. Its verification includes actual
positive/falling-edge writes, every-bit independent readback, hostile external
inputs while parked, phase-specific faults, staging/CRC integration, debug
waveforms and a separately compiled physical-data defect. Execution evidence
and exact commands belong under `runs/aws-f2/iteration246/`; the progress handoff
records which checks have actually completed.

Iteration 246 verifies 2,092 physical restores, 136 phase/entry rejections and
7,504,531 checks at gate counts 1/3/31/65, with zero target edges. Counts 0/65536
reject without writes/acknowledgements. A compiled write defect stops at source
cut 100, bit 0, before acknowledgement; independent waveform auditing confirms
those labels. Seven full VCDs remain. Native Vivado maps all 484 physical bits
and 557 supervisor bits to 1,041 registers across 30 fields, including two falling
edges. Supervisor error[4] is explicitly bound to native GND for valid GATES=3,
not omitted storage. A real extra LDCE produces 1,042 sequential cells and fails
the complete census. OOC resources are 601 LUTs; estimated setup slack is +1.697ns
at 140MHz with unconstrained external I/O. Full-image timing remains pending.

Exact source-bound native/EDA/audit receipts, per-process commands, waves and
retained regression evidence are indexed in
`automations/checkpoint_loop/runs/aws-f2/iteration246/summary.json` and
`verification-commands.json`. The exact Rocket compiler still rejects the
missing FASED physical gate owner/common-low-phase cut. No checkpoint-enabled
AFI or hardware checkpoint was produced by this increment.
