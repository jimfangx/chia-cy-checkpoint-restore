# In-place host annotation projection

Iteration 234 supersedes the primitive-local constraint limitation described
below; see [original physical-instance projection](f2-native-primitive-xdc.md).

Iteration 233 adds an explicit annotation contract to `NativeCheckpointInPlace`.
It applies the existing checked bank annotation translator to the complete
original enclosing hierarchy, pairing each concrete instance path with its actual
post-graft module. This handles parent-rooted constraints that cross the selected
boundary and a shared definition with both banked and unchanged executions.

The original and resulting declarations are checked independently. Unknown
annotations, foreign or unreachable targets, stale instance hops, missing/wrong
kind declarations and hidden primitive pins fail before emission. The existing
contracts cover preservation, memory initialization/policies/model labels,
synthesis constants, hierarchy/deduplication history and correlated public/internal
XDC. The selected source still has its independent bank annotation validation.
Host and generated combinational-path caches are invalidated and bound as
retirement records, allowing the downstream compiler to recompute them.

Version-3 in-place bindings add a hashed version-1 annotation projection. It binds
complete source/generated/result annotation JSON and the host translation map,
alongside the original circuit, generated banks/wiring, global identity map and
final instrumented circuit. Tests save those annotation inputs and the real
`WriteXDCFile` synthesis/implementation outputs, with distinct pre/post-link paths.

A constraint rooted directly at a shared native primitive would expand onto the
new root mask gate. In-place integration explicitly rejects that form until an
original-instance projection exists. Use a concrete ancestor-rooted physical
constraint; admitting arbitrary primitive-local constraints would silently change
the constrained-cell set. This is an implementation limit, not a request to
weaken or discard production constraints.

The independent Python audit reconstructs the bounded fixture's original and
instrumented instance graph, translated targets, correlated XDC groups and actual
emitted paths. It rejects changed or missing constraints, stale/foreign modules,
cross-instance arguments, hidden pins, changed destinations/formats, duplicates,
changed emitted paths and dropped mapping records even after enclosing hashes
are updated. Its deliberately bounded supported class set fails explicitly on
other annotations; it does not certify the complete production annotation set.
The exact-Rocket test remains an original-source structural test, not a
production annotation or hardware capture receipt.

Fresh commands, diagnostics, native synthesis and EDA receipts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration233/`. All 247 Scala tests, 21 localhost synthesis scopes, 40 EDA scopes, 309 Python
and 40 loop tests pass, including the complete retained FCFS/component/ASan/UBSan
scope. The bounded in-place fixture passes 6,541 EDA SP2 checks at four cuts,
reading 128 words with 468 stalls through cycle 409 and retaining six debug VCDs.
Independent matching binds 1,530 inputs and 41 current sources. Local OOC synthesis
retains 884 LUTs, 590 registers and all 194 raw parent/readout clocks; full-image
timing closure remains pending. This increment does not supply
in-place CE endpoint/widget/transport attachment, complete freeze owners,
physical CE restore or pre-FAME semantics. Full image P&R/timing/AFI, actual F2
checkpoints, CPU migration/live RTL and rolling hardware recovery remain pending.
