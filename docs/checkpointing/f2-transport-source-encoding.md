# Transport source encoding and physical bit ownership

Iteration 243 introduced `fsm_encoding = "none"`. Iteration 244 additionally
preserves `CheckpointCaptureCut.state` and `CheckpointCaptureTransport.state`
with `dont_touch = "true"` to prevent physical register replicas.
The source-register layout and public transport ABI are unchanged. The
source-pinned Scala observation schema now requires these exact implementations.
AMD documents the property in the
[FSM_ENCODING reference](https://docs.amd.com/r/2023.2-English/ug912-vivado-properties/FSM_ENCODING).
Native synthesis evidence must establish that both properties are honored.
The [DONT_TOUCH reference](https://docs.amd.com/r/en-US/ug912-vivado-properties/DONT_TOUCH)
describes RTL-level preservation through implementation. Full-image timing and
place/route remain required; this bounded policy does not establish FPGA Fmax.

The previous native audit admitted more storage than its field layout: the
4-bit transport state selected 15 physical registers, and five additional
cut-controller encoding registers were separately classified. These extra
16 physical bits were not represented by the coherent source-vector shadow.
Fresh native diagnosis separates five cut FSM encoding bits from eleven
transport register replicas; the latter are not inferred FSM encoding state.
Historical receipts remain unchanged. This increment prevents re-encoding and
replication and requires exact source/native widths instead of admitting extra
physical storage.

The native audit now checks each of the 24 fields against its exact width,
accounts for every physical sequential cell, checks raw-clock polarity, and
matches every register Q net to the corresponding exported `control_state`
bit through native hierarchical net segments. An independent Python audit
checks the complete physical-bit table, cell identities, indices and field
partition. The shadow fixture uses the same source-bit proof alongside its
separate shadow-register accounting.

Native negative builds remove the complete policy from each controller independently,
remove only transport preservation while retaining the FSM policy, and separately
permute exported state bits while keeping the storage widths.
Every negative must fail its physical-state audit for the expected reason.
The ordinary RTL VCS readout/shadow, corruptions, backpressure, owner faults,
abort/reset recovery and retained fixture/FCFS/sanitizer checks remain required.

Iteration 244 also requires a complete native `IS_SEQUENTIAL` census. Every
Vivado cell classified as sequential must be an explicitly mapped source or
shadow flip-flop. This closes the omission of sequential primitives outside the
`FD*` filter. Independent Python auditing checks exact cell identities and
primitive types. A synthesized hidden-latch mutation must fail this census
while retaining all original exported source bits.

The full-suite recovery also removes repeated structural hashing of large FIRRTL
module definitions in physical CE dependency discovery and native in-place
identity checks. Definition deduplication uses names only after the existing
canonical module map rejects duplicate definitions. Concrete instance paths,
owner multiplicity, order and structural executing-definition comparisons remain
unchanged. The original stopped run and thread dump are preserved separately;
all tests rerun against the corrected sources.

The initial full native sweep rejects both new control/shadow builds because
`fsm_encoding="none"` alone permits eleven transport register replicas. Its
source-copy probe identifies all replica cells and their independent D/Q nets;
a preservation probe passes the unchanged exact 484-register bit/census proof.
These isolated probes are diagnostics, not production acceptance. All original
logs remain under `automations/checkpoint_loop/runs/aws-f2/iteration244/`.

Full repaired-source component validation passes under
`automations/checkpoint_loop/runs/aws-f2/iteration244/repair/`:
262 Scala, 318 Python, 40 loop, 27 native and 46 EDA scopes, retained
ASan/UBSan/host/FCFS and independent audits. Accepted synthesis has exactly 484
source registers, no extra encoding state, and 552 shadow/1,036 total registers.
All five native negatives reject. VCS checks 5,051 live samples/50,510 words and
1,614 shadow captures/80,952 words, with eleven integration scenarios and 29
independently audited debug waves. Corruption stops at cut 100/observation 107.

Both full attached-top DCPs independently enumerate 1,016 raw control/stream
registers (777 widget, 55 stream engine, 184 interconnect), with every clock checked.
Legacy fixed totals 1,028/1,024 are preserved in original failed audit logs;
repaired exact-count assertions use these independently enumerated DCPs. The
nested producer lookup correction retains complete source circuit/storage/context
matching and keeps old and fresh compiler histories separate. No hardware capture
or complete production owner is admitted by these results.
The interrupted iteration-243 diagnostics and initial iteration-244 source epoch
remain separate; see the current summary and verification commands in `repair/`.

This is a localhost out-of-context synthesis contract. It does not supply a
transport restore adapter, freeze all raw-clocked owners, map the shadow's own
restore state, or bind stream/MMIO, functional-memory, FASED, DRAM, reset,
external-writer, host and physical CE-latch owners. Production inventory and
image-emission guards remain unchanged. Full-image implementation/AFI and
FPGA-origin paired checkpoint migration, independent zero-edge readback,
finite/live clean-RTL comparison and rolling hardware recovery remain pending.
