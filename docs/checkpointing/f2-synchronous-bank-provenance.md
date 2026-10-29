# Synchronous native bank provenance

Iteration 270 strengthens validation of the native synchronous queue adapter.
The standalone bank validator previously checked the instrumented circuit hash,
RAM shape, selected register types/clocks and adapter policy. A changed forwarding
or endpoint equation with a recomputed circuit hash could pass that layer. The
outer shell reconstruction was stricter, so this was a standalone validation gap,
not evidence of an accepted FPGA checkpoint.

Each adapted bank now retains an immutable, in-memory origin containing its
original New/write-first reference and ordinary bank. The factory independently
regenerates the ordinary bank before creating that origin. Validation reconstructs
the complete Old/data-register adapter, registered collision forwarding, borrowed
reader, public shadow, reset/cancel/reprime endpoint and response logic. It
compares typed circuit structure, form, renames, annotation contents, selectors
and canonical binding. Hash replacement cannot excuse changed equations.
Serialized artifacts must be regenerated from original source to acquire this
proof; sidecars alone cannot construct it. No new capture ownership is implied.

Directed tests reject ten independently rehashed equation faults, missing origin,
altered selectors, a substituted ordinary bank and removed policy. The existing
functional, cancellation, release, RAM policy and corruption regressions remain
required. The generated circuit and binding format remain version 2.

This change does not resolve the three physical CE/common-low-phase owners,
derived queue pipeline capture/restore ownership, live MMIO/DMA transport and
external reset/writers, full functional memory, host adapters or semantic mapping.
Whole-image generation must keep rejecting those missing owners. Full localhost
image implementation/AFI, actual F2 captures, matching Level-1/Level-2 restores,
finite replay, sustained live RTL and rolling FPGA recovery remain pending.

Current commands, compiler diagnostics and receipts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration270/`. Initial compiler-state
object comparison failures and the first EDA rsync failure (transient Git
`index.lock` disappeared) are retained as failures in that directory. Final
verification results will be recorded in `progress.md` and the iteration summary.

EDA recovery also excludes transient Git `*.lock` files specifically inside
root/nested `.git` directories from source synchronization. Real HEAD/index
metadata, dirty source and non-Git lock inputs still transfer. Real rsync
round-trip tests cover root and nested submodule locks and retain the full
52-test manager scope. The first broad glob missed a root lock; that failed
check remains in the iteration diagnostics, followed by the passing exact
root/nested patterns.

The full source-bound compiler sweep passes 328 tests / 51 suites plus twelve
preparation checks. An orchestration script edited while its waiting shell was
active caused a launch-wrapper syntax failure; no native test had started. Its
original log is preserved and the syntax-checked stable script was relaunched.

The complete retained native and EDA component checks also pass on the final
sources, including BLOCK/ULTRA inference, all bank/region/endpoint/physical
scopes, complete readback/continuation/corruption/waveform checks, 337 Python /
52 manager tests, 47,219 sanitizer assertions, host, FCFS and atomic cut. Whole
Rocket emission still rejects the physical CE owner and eight transport conflicts;
1,042 original entries remain uncovered. Current selections distinguish these
fresh component results from the explicitly retained generated source-IR input
and the historical version-1 native failures.
