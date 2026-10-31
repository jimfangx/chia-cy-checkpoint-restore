# Native transport image admission

Iteration 288 closes the production image guard gap introduced by the native
component endpoint. `NativeCheckpointWidgetReservation.requireBound` previously
recognized only the physical transport. Removing annotations and generated
headers from a native endpoint could therefore bypass this particular guard,
even with transport, response-bank and external-clock owners still missing.

The guard now rejects the native transport independently of manifest values,
clock-network flags and native-control readout options. It recognizes its
definition name, its native state-port signature, and a separate native
parameter/common-transport signature. Linked module bodies retain the port
check. Recognition deliberately does not require valid widths, parameter types
or parameter values: malformed unsupported hardware cannot gain admission by
failing an exact valid-ABI comparison. The existing physical reservation checks
remain in place.

`NativeCheckpointImageGuardSpec` elaborates both actual native endpoint wrappers,
including the internally bound original descriptor ROM. It removes every
annotation/header and exercises the direct guard and the ordinary Golden Gate
production boundary. Negative cases cover absent, duplicate and malformed
parameters, local-clock/control flags, damaged ports, renamed definitions,
independent structural signatures and linked unowned bodies. Positive controls
preserve ordinary and generic MMIO/DMA admission at this compiler boundary,
plus direct component elaboration. Per-case FIRRTL and rejection receipts belong under
`runs/aws-f2/iteration288/scala/`, not in tracked documentation.

The expanded full suite changes some suite-global Chisel name suffixes in its
generated fixtures. The complete byte-comparison diagnostic is retained; no
generated-byte equivalence is claimed. Retained component executions keep their
original dates. Their source audit permits only the exact read-only insertion
in `requireBound`, with all original generator code unchanged and the added
suite confined to tests. Artifact and raw-wave authentication remain required;
this exception cannot authorize another source change or a production image.

Validation passes 346 Scala tests / 55 suites plus twelve preparation tests,
394 Python tests, all 61 manager tests, ASan/UBSan, FCFS, generated-bank and cut
checks. All thirty retained component scopes and the bound-native/routed and
base/bound waveform audits pass; all 658 original raw files (217.523 GiB) were
freshly hashed this turn and their identities checked again at closure. Exact
replay commands and immutable receipts are under `runs/aws-f2/iteration288/`.

This is a production integration prerequisite. Native widget selection,
reservation/peer ABI and identity-bound driver installation must still change
together. Complete common-cut/reset/physical CE, reader-idle and functional-hold
bindings, atomic MMIO/stream/response-bank owners, memory/FASED/host coverage
and independent pre-FAME mapping remain required. Component observation and
bound stream descriptors do not provide these owners. Full localhost image
synthesis/place-and-route, AFI/AGFI deployment, actual FPGA checkpoints and
fresh paired CPU migration remain pending. No hardware acceptance advances.
