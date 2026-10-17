# Four-hart syscall-93 workload

Iteration 151 closes the workload/protocol mismatch identified in the restricted
TSI context recovery notes. The retained four-hart workload exits by writing an
odd HTIF command. The sixteen-owner fresh coroutine aggregate supports syscall
93. The new `verify_rocket_workload --exit-protocol syscall93` generates a separate
C source and ELF under its diagnostic output directory, leaving the retained
direct source and images untouched.

The generator changes only the exit transport and adds an aligned eight-word
request. Hart zero publishes selector 93, its independently computed four-hart
failure bitmask, and six zero arguments, then fences before publishing the
request pointer through tohost. The decoder separately checks the eight BSS-zero
stores made by the actual startup assembly before any computation. Every hart
still runs the same self-checking
64-KiB memory computation and all four synchronization phases. Spike checks the
success image and one real memory corruption per hart. This protocol uses an
ordinary HTIF syscall request, not an `ecall` trap or a host protocol fixture.

`verify_rocket_syscall_vcs` checks an existing exact-recipe native build and every
recorded input hash, then launches four fresh complete metasim processes:
ordinary/restricted HTIF, each with ordinary/buffered observers. Every process
uses 16 GiB of functional backing memory. The restricted process selects
`+checkpoint-syscall-exit` and sealed empty terminal input. A test-only exec helper
blocks SIGINT/SIGTERM/SIGABRT before any VCS threads exist. Actual lifecycle guards
remain active for the calling thread mask, pending signals and handlers. The
separate signal-owner API has an all-thread audit, but the restricted aggregate
does not invoke that API. The launcher supplies no lasting thread exclusion;
this helper is not a production signal coordinator and does not make delivered-
signal callers restorable.

The independent workload auditor decodes actual retired CPU stores. For the
syscall variant it additionally requires all eight ordered request stores by
hart zero and the subsequent sole pointer publication. `audit_rocket_syscall`
re-runs that decoder, compares all four complete hart traces and decoded cycle
labels across all four native modes, and binds sources, native build, process
identities, argv, artifacts and workload bytes. Mode-specific completion labels
are retained separately; protocol comparison does not relabel target cycles.

These uninterrupted CPU controls establish a real self-checking workload on the
protocol supported by the retained context aggregate. They do not restore CPU
state, simulator/FAME state, bridges or functional memory. Complete Level-1
Rocket admission stays disabled. Next work must connect the all-thread signal admission policy to the aggregate,
coordinate production signals,
publish one coherent complete cut, independently audit fresh readback and
compare continuation at original target-cycle labels. Level-2 retained ChipTop
capture and ordinary RTL finite replay remain independent. See
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) for final native results and
commands; diagnostics live under `runs/m11-iteration151/`.

The four native controls all pass at C=3,330,050; all sixteen complete hart
traces match. Observer repair does not rerun target execution: the explicit
`--completed-controls` path freezes all original native artifacts/source inputs
and launches fresh corrected checker processes in a new invocation. It retains
the original failed input-drift report, checks PID uniqueness within each launch
phase, and binds every process's own argv/log/runtime. The independent audit
re-reads the actual CPU logs and full traces. No checkpoint is inferred from a
workload-only pass.
