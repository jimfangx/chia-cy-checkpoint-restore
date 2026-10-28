# Enclosing-module state banks

`NativeCheckpointShellStateAccess.generate` adds synthesizable banked readout
for the local storage of one existing, unique execution. This addresses state
that native inlining moved into an enclosing module, where selecting more child
regions cannot reach it. It does not connect those banks to the production
widget or establish a complete simulator cut.

The implementation temporarily replaces immediate child pins with explicit
ground boundary ports and inventories every local register, memory and emitter
read pipeline. The existing bank generator provides chunked 64-bit reads,
latched responses and backpressure using a separate access clock. Grafting
restores the original children and pin equations, carries prefixed access ports
through existing ancestors and verifies the unchanged concrete execution set.
Children continue executing while local registers, memory writes and saved read
pipelines hold. A caller must provide the required freeze timing; the API supplies
no handshake between independent clocks.

The mapping records original full-hierarchy StateIDs separately from local
selectors and emitted pipeline names. Validation reconstructs the extraction,
banks, graft and identity from the original source. Unknown annotation owners,
shared selected definitions, ambiguous ancestors, namespace collisions,
unsupported boundaries and child-produced local clocks reject explicitly.
These are Level-1 generated-simulator identities; no Level-2 semantic image is
produced by this API. Additional asynchronous RAM read ports can affect memory
inference; the 183 actual Rocket enclosing owners are registers.

Original annotation values, paths, duplicates and order remain intact; only
invalidated `CombinationalPath` caches are removed. Annotation translation runs
as validation only, using distinct temporary identities for concrete executions.
Applying its emitted copies here would broaden nonlocal references to unchanged
shared definitions. Tests cover distinct initialization files on two shared
children, preservation of nonlocal memory-model and `DontTouch` targets, and
rejection of genuinely overlapping initialization owners. The exact Rocket
check also retains all four per-hart register-file model annotations.

The exact generated Rocket source contains **181 FPGATop local registers and two
F1Shim local counters**. Separate shell invocations can bank these 183 original
owners. Iteration 260 generated these separately from the 10,910 regional
descriptors. Iteration 261 composes the local and regional readout in one
diagnostic network, with **11,093 descriptors / 1,058 uncovered original
functional entries**. Connection to the registered widget now explicitly rejects
eight inlined widget-local owners whose freeze would stop the checkpoint stream.
See [f2-shell-region-routing.md](f2-shell-region-routing.md). The opaque transport
owner remains unsupported. Remaining original entries include 956 under 22 unique
raw subtrees and 102 under eleven shared-definition subtrees. Stream/control
owners and the eight transport locals require explicit separation and atomic
capture ownership; a readout descriptor alone does not establish that ownership.

Iteration 260 evidence and exact commands are retained under
`automations/checkpoint_loop/runs/aws-f2/iteration260/`. The directed component
exercises a 65-bit register, a synchronous old-read memory and its saved read
pipeline while original child and sibling counters remain live. Independent
verification reads every word, stresses held responses, checks reset during
freeze, rejects unfrozen/missing-selector reads and compiles a corrupted payload
variant. Native Vivado OOC synthesis passes at 122 LUTs / 163 registers, with
eight independently rehashed audit rejections. Fresh source-pinned EDA SP2 VCS
passes 4,280 checks, 69 reads and 347 stalled cycles across four component cases.
The independent full-wave oracle verifies all local storage, original memory
semantics and live children over 649 healthy samples, including 488 frozen
samples. VCS memory words are exposed through read-only debug aliases; all
readout data expectations come from independent arithmetic and functional input
history. The compiled payload defect stops at the first word, local cycle 7,
with freeze held and no acknowledgment. Case labels are fixture identifiers.

The complete iteration also passes 311 Scala tests in 46 suites plus twelve
preparation tests, 336 Python / 45 manager tests, fifteen native and fifteen EDA
scopes and all five waveform audits, retaining ASan/UBSan host, FCFS and atomic
cut regressions. Native jobs follow Java generation and peak at two. Final
resource inventory and complete source/receipt/protected-input auditing pass.

All complete-capture, deployable-image, transport-owner and metasim-restore flags
remain false. Production image rejection remains enabled. Global common-cut,
reset/external writers, functional memory, bridge/host/pre-FAME and added access
state coverage, full localhost P&R/AFI, real four-hart FPGA captures and paired
zero-edge/finite/live/rolling migration remain required.
