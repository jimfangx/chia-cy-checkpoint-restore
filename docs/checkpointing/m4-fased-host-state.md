# M4 FASED host state — iteration 19

M4 remains in progress. `FASEDMemoryTimingModel` now implements
`firesim.widget.fased.v1` at completed initialization/profile calls. This is
a host component adapter, independent of the generated FASED timing state and
native functional-memory/AXI queue adapters. Whole `.fsckpt` publication and
fresh-process FireSim restoration remain outstanding.

The payload binds the model index, generated memory size, hardware-default
selection, both complete sorted MMIO maps, sorted user timing configuration,
and histogram/range names. It retains constructed/initialized lifecycle,
every 36-bit histogram baseline, every 48-bit range value and range-buffer
length, and the complete logical profiling CSV history. Hardware counters,
histogram/range readout controls, timing progress and outstanding target/host
transactions remain generated RTL and native memory/MMIO state.

Save/validate/load issue no MMIO, file operations or clock edges. Decoding,
CSV format/width checks, geometry checks and allocations precede mutation;
load copies histogram arrays and swaps allocated range/history buffers.
Fresh output destinations may differ. The next ordinary profile/finish call
materializes the restored logical profiling history before further work.
Constructor header output still occurs normally; load does not publish the
restored history immediately. An output failure poisons the owner before any
subsequent MMIO. Aggregate checkpoint publication must separately own output
artifacts and the simulation initialization/finalization phase.

All public init/profile/finish operations have suspended/reentrant and
interrupted-call guards. Repeated initialization, profiling/finalization
outside the initialized lifecycle, and checkpoint operations after finish
reject explicitly. Finished histogram/range/output publication is currently
unsupported rather than silently replayed. Range arrays now use RAII
vectors. Sanitizers exposed an existing lifetime bug: histogram/range helper
objects referenced the temporary constructor address-map argument. They now
reference the driver-owned immutable map.

The generated-constructor verifier independently binds actual FCFS FASED
payloads to model/memory configuration and both emitted address maps. Actual
FCFS now has six audited widgets: master, loadmem, FASED, clock, reset pulse
and peek/poke. Unknown drivers remain default unsupported. Full requests
still fail before initialization at the unsupported metasim runtime cut;
no incomplete `.fsckpt` is published. The production fixture has no host
histogram/range baselines; the independent component fixture exercises all
eight 1,024-bin histograms, both range counters, zero/three ranges and absent
instrumentation. Its verification scope does not establish full simulator
continuation.

Native ASan/UBSan and fresh VCS DPI pass 40 component continuations/120
operations against an independent Python oracle. All captured bytes,
complete MMIO operation/response order, histogram deltas, range output and
profiling history agree; 40 restored owners match before the first fixture
edge. Each backend passes 1,128 malformed/configuration/lifecycle/suspended/
reentrant/interrupted/output-failure rejections. Eight malformed fresh
processes reject during initialization before opening a trace or dispatching
an edge. Failed initial compilation and the sanitizer lifetime diagnostic
remain in separate run directories; they are not passing evidence.

All five production settled cuts pass with six independently bound widget
payloads, all 13,507,456 generated words, and four complete 4 MiB functional
memory channels. Default cuts 3/11/699275/699276 finish at 774,628 target
cycles; randomized cut 101 finishes at 774,632. Complete 40-port target
AXI/FAME traces and generated observations are byte-identical to their
uninterrupted references. Cut 699275 retains an in-flight native-memory write
and outstanding FASED target writes. Standalone and all four legacy cuts also
pass; the default full generated capture retains SHA-256
`b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`.

All 23 existing regression scopes pass, including 29 current Python/20 Scala
tests, compiler codecs/emitted-memory coverage, existing native/VCS owner
continuations, full M2/M3, ordinary clean RTL VCS and default/randomized GCD.
The profiled production FCFS run retains four samples at 774,629 target
cycles. Both three-case worker/settled rejection-liveness suites pass;
current FASED adapters and existing owners are linked in all four actual
executables. The full evidence audit rechecks all target traces, generated
observations and actual widget payloads, then verifies input-plan hashes and
records full source/artifact paths.

Reproduction from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_fased_checkpoint_vcs \
  --out automations/checkpoint_loop/runs/m4-iteration19/fased-owner-final
python -m tools.checkpoint_formats.tests.verify_settled_boundary_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration19/settled-boundary-verified
```

Exact command arrays, logs, summaries and the artifact catalog are under
`automations/checkpoint_loop/runs/m4-iteration19/`. Every VCS shell sources
both environments then `vcs-env.sh` last, retaining Y-2026.03-SP1, `-full64`,
GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`.

Next: stream adapters, simulation initialization/finalization and output
ownership; restore harness banks and reconstruct parked dispatcher/DPI
continuation before the next edge; prevalidate and load every generated and
software owner in a manifest/build-bound `.fsckpt`; compare a fresh VCS
metasim restart to uninterrupted target outputs and transaction timing with
outstanding traffic. `runtime/simulation`, `runtime/harness`, execution
contexts and generated RTL load remain unsupported. The relevant DESSERT
and Strober passages were read from their existing root-paper text
extractions under `runs/m2-iteration7/`: complete state and token/I/O timing
are necessary for exact continuation. Level-1 and Level-2 remain separate.
No required external dependency is missing. No whole-runtime restart,
physical FPGA, formal or ASIC activity/power acceptance is claimed. Plans,
conda files and root PDFs remain untouched; no plan correction is proposed.
