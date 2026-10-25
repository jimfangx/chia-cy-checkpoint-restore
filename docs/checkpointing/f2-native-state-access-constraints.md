# Native state-access wrapper constraint placement

Iteration 229 adds `NativeCheckpointConstraints`. `NativeCheckpointStateAccess`
places the generated native circuit under its literal `network` instance; its
constraints must include that extra hierarchy level. The explicit native probe
now passes its original pre-link and post-link placement to the constraint
emitter. It emits separate `.native-state-access.synthesis.xdc`,
`.native-state-access.implementation.xdc` and a constraint binding, alongside the
existing readout wrapper. The ordinary production output remains guarded by
complete physical ownership requirements.

Constraints are regenerated from the specialized, clock-wired circuit's
annotations through the real `WriteXDCFile` consumer. The emitter validates all
targets first, preserves correlated multi-argument targets and repeated-instance
specialization, and appends `network` to each phase's placement. Literal parent
paths reject empty components, Tcl substitutions and wildcard/relative syntax.
Shell-only clauses without circuit arguments retain their exact text. The
binding includes the original/rebased placements, translated annotation hash,
wired circuit hash, complete constraint specifications and both XDC hashes.
It explicitly denies production attachment, complete capture and restore support.

The independent Python auditor walks the concrete wired FIRRTL hierarchy,
resolves each public declaration or pin and renders every constraint argument.
It checks the unchanged original XDC and the rebased XDC independently, including
ordering and shell-only clauses. The native MMIO/DMA fixture applies the generated
constraints inside its actual `access/network` hierarchy. During application,
every cell/pin query must resolve exactly once; deliberate empty cell and pin
queries must fail. It also checks applied native-gate properties and generated
output clocks. Coherently rehashed missing/altered paths, pins, clauses, placement,
specifications and production-attachment claims must reject.

All 237 Scala tests pass. The connected fixture synthesizes on native Vivado
2025.2 with 2,637 LUTs / 1,157 registers, three native/root gates and one
falling-edge mask. Six real cell/pin queries and their applied properties/clocks
pass; two deliberately empty queries reject. OOC 140 MHz setup/hold estimates
are +0.598/−0.104 ns, with hold and full-image closure still pending. Fifteen
coherently rehashed RTL/XDC corruptions reject. Fresh EDA SP2 passes 6,482 checks,
five complete cuts, 170 words and 210 DMA stalls; all six full execution VCDs
remain. Independent native/EDA matching covers 94 inputs / 34 sources and rejects
nine evidence corruptions. Semantic and compiled CE-wiring faults stop at cut
63/checks 273/1,036. The exact Rocket companion retains 12,096 functional plus
three CE descriptors / 619,016 words and its original ports; its seven constraint
specifications have six concrete circuit arguments, with shell clauses preserved.

The first native fixture used `set_max_delay` at native clock outputs. Vivado
reported path-segmentation critical warnings. The fixture now uses generated
clocks rooted at the native input pins, matching the clock-constraint use case;
critical warnings remain fatal to verification. Initial Scala failures from
new output-count and annotation-count assertions and that native diagnostic are
preserved below `runs/aws-f2/iteration229/`; no old receipts are rewritten.

This closes constraint placement for the separate readout companion. It does
not attach the companion to production FPGATop, bind reset/external memory and
host writers, restore physical CE state, or establish full-image timing closure.
The current native mask covers the original whole F1Shim circuit. Simply
enabling a widget inside that masked FPGATop would stop its control and stream
logic too. Production integration must keep the actual MMIO/DMA service on the
raw clock and explicitly account for its state/ownership across the common cut.
A localhost checkpoint-enabled image/AFI, real all-hart F2 capture at every cut,
paired independent zero-edge restore, finite RTL replay, sustained live RTL
beyond trace and rolling hardware recovery remain pending. Every hardware-origin
migration column in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) stays
pending until those execution artifacts exist.

Execution evidence and exact commands belong under
`automations/checkpoint_loop/runs/aws-f2/iteration229/`.

Full retained validation passes all 19 localhost synthesis scopes, all 38 EDA
scopes, 309 checkpoint Python tests and 40 loop tests, including ASan/UBSan,
host and FCFS checks. Complete exact-Rocket structural/constraint reconstruction
agrees independently on both hosts over 2,290 module definitions / 14,313
sequential/effect definitions. The ordinary production compiler still rejects
the unbound FASED physical CE owner; its actual command/error log is retained.
No new AFI or runtime was requested. The final inventory records zero loop
runtime instances or native Vivado/Java jobs and retains all 29 observed account
AFI identities without claiming they implement capture.
