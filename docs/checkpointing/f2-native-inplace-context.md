# In-place compiler context projection

Iteration 235 adds `NativeCheckpointInPlaceContext.generate` at the resolved
post-lowering boundary. It separates the existing, explicitly supported inert
compiler context from storage annotations, validates it before banking, and
retains it alongside the checked in-place projection. Unknown annotations still
reach storage preflight and reject. Duplicate options, conflicting type metadata,
uncontracted deleted events and passive output conflicts retain their existing
fail-closed behavior.

The selected reference contains the actual reachable definitions and the required
rebased synthesis-constant contracts. Complete host preservation, initialization,
RAM policy, memory-model, hierarchy/history and correlated XDC annotations are
projected against the complete enclosing hierarchy. They are not independently
flattened into the selected subtree. Original and instrumented annotation sets,
selected reference, native binding and compiler context have separate hashes;
`validate` checks the retained state and a supplied downstream state before any
consumer changes the storage annotation contract.

Version-2 native functional companion emission now includes the original storage
annotations, context annotations and context snapshot. The ordinary compiler's
functional circuit remains unchanged by companion generation. The Rocket test
reads these actual compiler artifacts instead of treating bare FIRRTL as evidence
for production annotation support. Annotation JSON normalizes sets for hashing;
the test restores the original XDC sequence from the compiler translation binding
so lexical JSON order never becomes constraint policy. FIRRTL omits nested class hints when serializing
`DeletedAnnotation`; the test reconstructs only the two known consumed input-file
events and requires an exact serialization round trip.

The independent Python auditor reconstructs context records from the raw source
annotations, checks the complete source/storage/context partition and projection
bindings, and rejects eight context mutations even after outer hashes are
recomputed. For production it also checks the original seven XDC source events
in their compiler order and rejects a reordered, coherently rehashed mapping.
It checks context preservation; it does not certify all production annotation
semantics or missing physical owners. The retained independent bank, identity,
annotation/XDC and execution audits remain necessary.

The focused exact-Rocket test and independent audit pass for **2,456 source
annotations**, including **25 context annotations / 20 context kinds** and
**2,379 projected storage annotations**. The actual XDC consumer emits **14
constraint commands**. The selected endpoint still covers **10,149 functional +
two CE entries**, leaving **1,947 functional owners and one FASED CE owner**
uncovered. This is compiler integration evidence, not an FPGA checkpoint.

All **250 Scala / 21 localhost synthesis / 40 EDA scopes**, **309 Python / 40
loop tests** and retained **ASan/UBSan/host/FCFS** checks pass. Independent context
audits match **15 fixture / 17 production files / 44 sources** across backends.
Retained in-place execution passes **6,541 checks / four cuts / 128 words / 468
stalls** through cycle **409**, with six waves and **1,822 inputs / 42 sources**
matched. Native synthesis retains **884 LUTs / 590 registers / 194 raw-clock
registers**; full-image timing remains pending.

Final commands, execution receipts, resolved exploratory failures and
cross-backend audits belong under
`automations/checkpoint_loop/runs/aws-f2/iteration235/`. Consult its final
`summary.json`, `verification-commands.json` and `recovery-notes.json`.

The in-place CE endpoint/router/widget/MMIO/DMA connection, reset and external
writers, functional DRAM, FASED, bridges and software owners, physical CE restore
and independent pre-FAME mapping remain required. Full localhost image
implementation/timing/AFI and driver binding, active four-hart F2 captures,
FPGA-reference continuation, both independent zero-edge restores, finite replay,
sustained metasim-guided clean RTL and rolling recovery remain pending. No
checkpoint-enabled image, AFI or hardware-origin checkpoint is claimed.
