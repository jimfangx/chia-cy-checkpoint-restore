# Concrete shared queue readout

Iteration 269 implements the synchronous native-port adapter described below;
see [f2-synchronous-queue-memory.md](f2-synchronous-queue-memory.md) for its
contract and current validation. The iteration-268 BLOCK-policy failure retained
here is historical evidence and is not rewritten as a successful synthesis.

Iteration 268 adds instance-specific local banks for repeated module definitions.
The exact Rocket diagnostic selects the four existing TRACERV `Queue_56`
executions beneath `CPUManagedStreamEngine_0`, leaving the live checkpoint
transport queue outside that selection. Their original RAM, pointer, full and
synchronous-reader-address state retain original global StateIDs. Only the
selected emitted definitions acquire checkpoint ports and freeze equations;
untouched sibling definitions and original functional connections are preserved.
Shared ancestors must still have unique executions; unsupported selections reject.

`NativeCheckpointRegions` merges each selected instance declaration and its
independent sideband through common ancestors. Local-only compositions are
allowed when their clock identities resolve to the same original raw clock;
they still need the existing global physical-clock audit and do not acquire
physical CE ownership. Duplicate executions, namespace collisions, stale paths,
changed state and descriptor/annotation drift reject.

Shared storage initialization, preservation and FIRRTL memory-model annotations
retain concrete original execution paths during both local banking and final
composition. Flattening a nonlocal annotation onto an unchanged shared module
could otherwise change multiple untouched siblings. The existing correlated XDC
projection remains authoritative; the default translation behavior for previous
unique-execution banks is preserved.

The component fixture uses three original depth-six, 130-bit write-first
synchronous queues. Two get independent readout banks; the third continues
normal enqueue/dequeue and RAM traffic during capture. An independent software
queue/RAM oracle checks public outputs, every selected logical word and padding,
read-address pipelines, pointer wrapping, reset during freeze, retained responses
under backpressure, control-reset cancellation and release. Native synthesis
must consume its emitted BLOCK RAM policy and find physical block-memory
primitives in each original queue. Its bound wrapper ties access clocks to the
raw clock and consumes the registered transport endpoint, following the region
graft; unused combinational bank-probe outputs remain internal. EDA VCS tests
the same wrapper and must consume source-bound native inputs and retain full debug waves, including explicit original RAM-word
aliases. A compiled first-response fault must stop before acknowledging that word.
The reduced fixture does not establish implementation feasibility of Rocket's
6144-by-512 ULTRA memories or CPU/hardware migration.

The production queues retain their original ULTRA RAM hints. If forced native
inference cannot implement the extra checkpoint reader, the next increment
needs a synchronous memory access adapter with acknowledged read latency,
retained responses and original read-address/pipeline preservation. Stealing
a native RAM port during hold also requires a validated re-prime step before
release. This is a proposed implementation direction, not verified hardware.

Full original-state coverage, physical CE/common-low-phase ownership, complete
transport/stream/backend/reset/external-writer ownership, functional DRAM,
host-driver state and pre-FAME semantic mapping remain required. No local bank
or descriptor grants complete-image admission. Full localhost image P&R/AFI,
checkpoint-enabled F2 execution, FPGA-origin paired zero-edge/finite/live restore
and rolling hardware recovery remain pending.

Native localhost Vivado 2025.2 rejected the reduced queues under their emitted
BLOCK policy: `Synth 8-6849` reports that instrumented `host/q0` and `host/q1`
fall back to LUTRAM, while untouched `host/q2` maps to two RAMB36E2s. The strict
primitive audit stops at `host/q0`, before DCP publication. This is a real
remaining implementation failure, not a positive synthesis result. Separate
EDA functional diagnostics of those rejected inputs cannot grant native or
hardware acceptance. Rocket's ULTRA implementation remains unvalidated.

The fresh exact-Rocket trial also exposed Chisel's memory-clock validity aliases.
The local clock checker now accepts a Clock `validif` only when its condition
matches that same memory port's enable through supported scalar aliases.
Register/ancestor clock rules and genuine gate/mux/cast/secondary-clock
rejections remain intact. Targeted tests cover matching and mismatched guards.

Current commands, immutable receipts and diagnostic attempts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration268/`. The full compiler sweep passes 325 tests / 51 suites plus twelve preparation
checks; a separate four-test fixture regeneration binds its boundary rename.
The original full-sweep output is preserved. All 337 Python / 52 manager tests,
ASan/UBSan host checks and twenty-five retained positive native / EDA component
scopes pass. The separate fresh EDA queue diagnostic passes 361 reads / four
cuts and eight rehashed metadata negatives; a compiled payload fault stops at
the first word with freeze held and acknowledgement low. Both debug waves are
retained. Native memory-policy acceptance remains false.
