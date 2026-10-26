# Transport source encoding and physical bit ownership

Iteration 243 preserves the source encoding of `CheckpointCaptureCut.state`
and `CheckpointCaptureTransport.state` with `fsm_encoding = "none"`.
The source-register layout and public transport ABI are unchanged. The
source-pinned Scala observation schema now requires these exact implementations.
AMD documents the property in the
[FSM_ENCODING reference](https://docs.amd.com/r/2023.2-English/ug912-vivado-properties/FSM_ENCODING).
Native synthesis evidence must establish that the property is honored.

The previous native audit admitted more storage than its field layout: the
4-bit transport state selected 15 physical registers, and five additional
cut-controller encoding registers were separately classified. These extra
16 physical bits were not represented by the coherent source-vector shadow.
Historical receipts remain unchanged. This increment removes that synthesis
encoding and requires exact source/native widths instead of admitting it.

The native audit now checks each of the 24 fields against its exact width,
accounts for every physical sequential cell, checks raw-clock polarity, and
matches every register Q net to the corresponding exported `control_state`
bit through native hierarchical net segments. An independent Python audit
checks the complete physical-bit table, cell identities, indices and field
partition. The shadow fixture uses the same source-bit proof alongside its
separate shadow-register accounting.

Native negative builds remove the policy from each controller independently,
and separately permute exported state bits while keeping the storage widths.
Every negative must fail its physical-state audit for the expected reason.
The ordinary RTL VCS readout/shadow, corruptions, backpressure, owner faults,
abort/reset recovery and retained fixture/FCFS/sanitizer checks remain required.

Validation is in progress under `automations/checkpoint_loop/runs/aws-f2/iteration243/`.
Do not infer a completed run from the presence of this document.

This is a localhost out-of-context synthesis contract. It does not supply a
transport restore adapter, freeze all raw-clocked owners, map the shadow's own
restore state, or bind stream/MMIO, functional-memory, FASED, DRAM, reset,
external-writer, host and physical CE-latch owners. Production inventory and
image-emission guards remain unchanged. Full-image implementation/AFI and
FPGA-origin paired checkpoint migration, independent zero-edge readback,
finite/live clean-RTL comparison and rolling hardware recovery remain pending.
