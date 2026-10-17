# Restricted TSI aggregate signal admission

Iteration 152 connects the actual build-local HTIF lifecycle provider to the
existing all-thread signal/action guard. The restricted polling, fifteen-owner
host and sixteen-owner context aggregates use this lifecycle API. Capture,
preparation and final publication now audit every Linux task's blocked
SIGINT/SIGTERM/SIGABRT mask and local/shared pending state, stable task
membership, and the exact provider-installed BSD signal actions. The context
aggregate also reaches this guard before each fresh or initialized coroutine
resume. A delivered signal still rejects; no signal-caused caller is restored.
The serialized owner schemas and lifecycle fields are unchanged.

This closes the admission connection identified in iteration 151. It does not
establish production exclusion: procfs inspection cannot suspend workers or
prevent a concurrent signal, mask/action change or thread lifetime change after
inspection. The caller must still hold the documented exclusive suspension
contract throughout access. Complete Rocket Level 1 stays disabled until that
contract is supplied by production coordination and simulator/FAME/bridge/
functional-memory state is captured and published coherently.

The new native ASan/UBSan and VCS harness calls the actual sixteen-owner API at
execution and returned-tail boundaries. For each of SIGINT, SIGTERM and SIGABRT
it installs a real unblocked worker mask, pending signal on either of two real
workers, process-shared pending signal, changed restart flags, or changed
handler mask. It exercises preparation, already-prepared commit, capture, and
resume before and after coroutine initialization. Both workers remain parked
and alive through repair and the valid retry. Before any retry it compares the
accessible peer images, the actual provider fields, syscall image, and all
sixteen images wherever the complete aggregate exists. Retried state is
compared with the separately executed parent coroutine's complete images.
Test parking and blocked inheritance supply only the test's exclusion contract.

The matrix contains 360 current-provider cases. The prior exact-recipe provider
is linked into a separate copy of the same harness: 300 worker-local/action
cases are sensitivity witnesses, and 60 shared-pending cases are positive
controls because the old calling-thread sigpending check already sees them. A missing rejection is an expected failing
harness process, not passing admission evidence. The independent auditor binds
all native argv/logs, source snapshots, both actual recipe archives, exact case
membership and parent state bytes; missing/duplicate evidence must reject.

Diagnostic attempts are retained. The first observer reused a helper that
read the guarded lifecycle while a violation was installed. The second still
read that provider through the syscall image. The corrected observer reads
only unguarded peers during the violation, then all guarded images after repair,
before retry or service. An initial full-context launcher masked the compiler
as well as runtime processes; the final diagnostic controller restricts its
inherited-mask launcher to the native test executable and VCS simulation.
A comparison pilot incorrectly expected the prior provider to miss shared
pending signals; another audit expected a procfs error after the calling-thread
check had already rejected shared pending state. The corrected complete
independent audit passes all 720 native processes and all six missing/duplicate
evidence variants. A final fresh fixed-input invocation is selected separately.
Earlier observers/expectations and the compiler timeout remain diagnostic.
The matrix writer now marks a failed builtin audit as failed in its summary;
the older audit-failing pilot receipt is preserved unchanged and is not selected.

The existing foreign-creator resource fixture originally joined its worker
before inspecting the aggregate. A disappearing procfs task correctly rejects
under the new guard. The fixture now keeps that worker parked on a future until
the complete parent readback finishes, then releases and joins it without another
provider audit. Twenty fresh native/VCS pilot processes pass with these exact
fixture bytes. The first source-copy pilot reused output paths in the already
failed context invocation and is unselected; its replacement and the complete
rerun use fresh directories. No accepted artifact or prior-iteration artifact was
changed. The guard continues to reject unstable task membership.

Exact current results and executable commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics and immutable
source/process artifacts are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration152/`.
The independent Level-2 captured replay remains separate. BOOM and Saturn are
pending; standalone Shuttle, physical FPGA validation and ASIC power are outside
this increment.
