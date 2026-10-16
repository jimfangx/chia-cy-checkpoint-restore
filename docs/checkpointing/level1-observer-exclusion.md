# Level-1 exclusion for semantic capture observers

Iteration 141 makes the independent semantic capture observer an explicit
Level-1 exclusion. The current Rocket CPU profile remains disabled. This
change closes an admission gap; it does not serialize an observer or complete
the remaining CPU runtime owners.

The event observer is bound into the emitted simulator after the generated
Level-1 inventory is produced. Its storage therefore cannot be treated as
covered by that inventory. Its original ChipTop state is captured independently
for Level 2, but the observer itself owns additional state:

| Location | Additional observation state |
| --- | --- |
| Bound HDL monitor | Initialization/enabled flags, previous/planned/actual/upcoming clock vectors, completed-rise counters, event index, captured-cut flags, remaining window events, saved boundary samples and pending state verification |
| HDL trace writer | Open trace descriptor, output prefix/filename and current window cycle |
| Native capture backend | Ordered VPI handles, word widths/paths and saved pre-edge readback values |

None of these is original DUT state. No Level-2 image includes them, and no
Level-1 adapter currently owns them. Numeric host file descriptors and VPI
handles cannot be restored as portable owner values.

`checkpoint_request_t::parse` rejects a public Level-1 request combined with
either `+fame_capture=` or the older `+semantic_capture=` option. This includes
preflight, capture, restore, periodic history, restore with periodic history
and watchdog configurations. The check is independent of option ordering and
does not open any supplied checkpoint path or construct a capability.

The native FAME capture backend also exports a constant exclusion hook.
Production entry checks it before a public request can reach the capability
factory or platform construction. This covers a compiled monitor whose capture
option is absent. `checkpoint_entry_t` checks the same hook in its base
constructor, before any derived member initialization; a private diagnostic
capture capability cannot bypass the exclusion by omitting public options.
The optional weak reference can only deny admission. It cannot grant support,
replace an owner or enable the FCFS profile for a CPU. Ordinary builds without
the backend retain their existing behavior.

Standalone Level-2 capture continues through the ordinary metasim entry with
no Level-1 capability. The exact Rocket capture build explicitly links the
backend, and the native symbol audit requires its strong exclusion definition.
The older observer's runtime option is checked too; this increment does not
claim link-time detection of every independently implemented observer backend.

The final entry suite runs production entry in native ASan/UBSan and VCS
Y-2026.03-SP1 processes, with/without a capability and with/without the capture
backend. All **572 fresh cases** pass: **384 runtime-option exclusions**,
**24 compiled-backend exclusions before factory entry**, and **eight base
constructor exclusions**. The VCS cases link actual `fame_capture.cc`; only
the native dispatch checks use a constant hook stand-in because they have no
VPI runtime. Retained entry cases and the missing-factory link rejection also
pass. The independent audit rejects four missing/duplicate evidence sets.

Another **18 fresh exact-recipe Rocket VCS processes** reject the six public
request forms with the compiled monitor disabled, the FAME observer requested,
or the older observer option requested. No platform/simulation construction
marker, state deposit, capture window, image/history or capture trace is
published. The invalid restore-file sentinel remains byte-identical. These
are admission tests, not complete CPU restore or image-loader acceptance.

Artifacts and native reproduction commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration141/`.
The first entry pilot correctly rejected source changes during its test;
the first exact-recipe negative pilot used the capability-enabled error marker
instead of the ordinary build's `FS_CHECKPOINT_UNSUPPORTED` marker. Both remain
diagnostics, separate from accepted final invocations.

Before complete Rocket Level-1 admission, the implementation still needs the
session/descriptors, process signals, syscall parent, executable outer caller,
and coherent complete simulator/bridge/memory aggregate. A future observer
adapter must inventory and restore its complete HDL/native/file state before
this explicit exclusion can be relaxed. Independent Level-2 finite replay,
physical FPGA validation and ASIC power retain their existing separate scope.
