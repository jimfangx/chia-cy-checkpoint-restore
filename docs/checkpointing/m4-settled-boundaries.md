# M4 parked driver and settled harness — iteration 17

M4 remains in progress. The production VCS harness can now park the FCFS
operation dispatcher, finish the current rising-edge RTL/NBA updates and
observe generated RTL, audited software owners and all harness AXI banks
while both contexts are stationary. These observations are diagnostics;
there is no aggregate `.fsckpt` publication or whole-runtime load path.

`+fs-driver-cut=N +fs-driver-diagnostic=PATH +fs-driver-settled` selects the
new path. N counts completed dispatcher operations, not target cycles or
host clocks. The modifier requires its diagnostic partners, rejects duplicate
or malformed spelling and requires VCS. Drivers without incremental dispatch
still reject before initialization. The original parked-DPI diagnostic remains
available when the modifier is absent.

At the selected operation boundary:

1. The driver enumerates every software owner, enables the existing MMIO,
   stream and RTL-advance guard, publishes a request and waits on a dedicated
   condition variable. Its host-delay and run-loop operations have returned.
2. The existing `to_sim()` wait returns through DPI without calling `do_tick()`.
   DPI publishes provisional software-to-RTL outputs. The harness finishes
   this rising edge's sequential and combinational updates.
3. One picosecond later (the audited default VCS harness uses a 1 ps timebase
   and 1,000 ps clock period), `checkpoint_settled_event` invokes the read-only
   generated-state probe. A delta yield lets it read every manifested register
   and memory word before native capture or driver release.
4. The main thread records immutable packed harness banks and invokes the
   software diagnostic serializer. It saves, validates and rechecks every
   audited owner while the worker remains parked. Unsupported categories are
   retained explicitly; publication retains the existing temporary-file and
   destination-refusal rules.
5. The main thread releases the worker and waits for its next ordinary yield
   or completion. DPI republishes the final software outputs, and the harness
   refreshes the published output bank before the next edge. It does not tick
   the AXI models a second time, draw a host delay or issue a target/host edge.

The intermediate output bank and pending continuation phase matter. At this
cut the current RTL edge has completed, while the dispatcher still has work
it would have performed within the original DPI invocation. A future loader
must reconstruct this continuation, republish the final outputs and finish
this phase before the next edge. Simply loading these samples at an arbitrary
negedge is not a valid restart protocol.

`diagnostic/harness-banks` has schema
`firesim.diagnostic.harness-banks.v1`: little-endian uint64 magic `HRNSOBS1`,
uint64 packed width, then little-endian uint32 words with zero high padding.
The payload owns its bytes. In MSB-first order, the packed SV observation
contains a 64-bit debug trace count (zero in non-debug builds), clock/reset/fin,
nine RTL-to-software sync records, nine software-to-RTL sync records and nine
published software-to-RTL records. All optional/absent-channel records are
included using the actual compiled types. The current FCFS build has 4,145
bits. Validation checks the immutable observation; load remains unsupported.
`runtime/harness` therefore remains an explicit unsupported owner, separate
from this read-only diagnostic.

Generated probes use entry-based JSONL with phase
`settled_host_posedge_parked_driver`. Validation requires this phase explicitly;
the existing default validator still requires `settled_host_negedge`.
Generated-state diagnostics, software diagnostics and full Level-1 containers
remain separate. The paired diagnostic files do not provide atomic aggregate
publication, complete driver ownership or build-bound integrity.

Verification uses all 40 actual target-facing FASED ports, including the final
port declaration without a trailing comma. A full trace records their packed
values, the FASED target-cycle counter and targetFire at every host rising edge.
Uninterrupted references are compared with operation cuts 3, 11, 699275 and
699276, plus cut 101 with randomized delays and a full-width seed. The late
cut checks outstanding target and native functional-memory traffic. Every
successful diagnostic observes all 13,507,456 generated words and all four
4 MiB functional-memory channels. The bound guard checks the parked request,
clock/fin and the 1 ps settlement phase. Timeout completion, profiling-owner,
unreached, malformed/duplicate modifier and destination failures are checked.

Reproduction (from the Chipyard root):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_settled_boundary_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration17/settled-boundary-verified
```

Completed results and exact commands are recorded under
`automations/checkpoint_loop/runs/m4-iteration17/`. The obsolete 39-port trial
was interrupted after correcting the final-port parser and remains in
`settled-boundary/`; it is not a completed acceptance check. The first 40-port
trial retained all default cut passes, then exposed an incorrect cross-config
completion-count assertion: randomized polling completes at 774,632 cycles,
versus 774,628 by default. The corrected verifier reruns all cuts and compares
each against its uninterrupted reference with identical timing arguments;
the earlier trial is retained in `settled-boundary-allports/`. Native diagnostic
checks retain ASan/UBSan, including modifier rejection, immutable packed-byte
ownership, padding geometry and unsupported observation load. Existing full
compiler, component, M2/M3, clean RTL, GCD and FCFS regressions are retained.

Next: audit concrete bridge/widget/stream adapters and simulation lifecycle
state; turn the observed harness/continuation phase into a restorable owner;
coordinate full inventory/build-bound aggregate publication and prevalidation;
load a fresh VCS metasim before target advancement and compare complete target
outputs and transaction timing with outstanding traffic. Full requests continue
to fail closed before initialization on unsupported owners. No external
dependency is missing. No whole-runtime, FPGA, formal or ASIC activity/power
acceptance is claimed. Both plans remain read-only; no plan correction is
proposed. The relevant DESSERT token-state and Strober exact-state/I/O passages
were reread from the root papers' text extractions under `runs/m2-iteration7/`.
