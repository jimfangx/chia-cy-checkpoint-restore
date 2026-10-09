# M4 dispatcher bootstrap — iteration 26

M4 remains in progress. `simif_emul_t::start_restored_driver(sim, bits, banks)`
reconstructs the dispatcher component for a freshly loaded, incremental
`simulation_t` flow. The packed harness clock must be low, with reset and finish
deasserted. All driver/widget owners must have explicit schemas and successful
save/validation hooks; the base flow must have been loaded and must be idle,
running, off-stack and unpoisoned. Diagnostics, managed stream IO, QSFP, repeated
starts, unloaded concrete drivers and unknown owners reject before worker creation.

The new worker bypasses the ordinary initial `do_tick`, fastloadmem and simulation
initialization. It starts at the next completed-operation dispatch point, with
the existing base flow preserving the terminal flag. It returns at the next
ordinary yield or completion. A terminal flow that never yields completes
without another native or RTL edge; startup waits for either yield or completion.
Ordinary startup refuses a loaded flow so it cannot accidentally reinitialize
restored state. Calling `to_sim` before startup rejects instead of waiting for
an absent worker. Both dispatch flags now change under the mutex used by their
condition-variable predicates.

This is a component API. No production restore plusarg or `.fsckpt` loader was
enabled, and `runtime/execution-context` stays unsupported in full diagnostics.
A future aggregate coordinator must bind/prevalidate/load native, generated,
harness and driver owners before calling bootstrap, publish the resulting
outgoing DPI banks, refresh incoming latches, then allow the first rising edge.
The current API rejects managed stream IO/QSFP because their complete runtime
continuation has not been audited. Historical reporting time remains independent
of target time; the fresh worker's transient synchronization objects are
reconstructed rather than serialized.

The verification uses the actual `simif_emul_t` pthread worker, normal settled
low-clock diagnostic capture, `simulation_t` base loader and native MMIO/memory
owners. Target MMIO responses and RTL edges are fixtures. Four operation cuts
are tested for success, driver error, timeout and terminal completion without
another yield, in native ASan/UBSan and fresh VCS DPI processes. The independent
oracle specifies every MMIO submission and native tick. Every restored owner is
compared before bootstrap; queued MMIO, an in-flight two-beat native memory write,
two held read responses, the model cycle and all 4 KiB of functional memory must
remain unchanged through bootstrap. Five truncated-owner inputs per backend
must reject before any worker, edge, trace or restored-state publication.

Final dispatcher evidence: `dispatcher-current/summary.json` and
`dispatcher-evidence.json` report 32 fresh continuations, 160 owner comparisons
before the first edge, 64 unchanged native-owner comparisons through bootstrap,
288 matched MMIO calls, 352 lifecycle/phase rejections and ten malformed fresh
processes. The zero-yield terminal VCS continuation emits no fixture edge.
Native runs use ASan/UBSan; VCS is a separately compiled fresh-process backend.

The initial trial used the wrong MMIO inventory identity; two subsequent trials
exposed an invalid 96-bit memory beat/64-byte line fixture configuration. Those
failed diagnostics are retained. The fixture now uses a supported 64-bit memory
channel. Intermediate successes remain distinct from final verification.

Reproduction from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_dispatcher_checkpoint_vcs \
  --out automations/checkpoint_loop/runs/m4-iteration26/dispatcher-current
python automations/checkpoint_loop/runs/m4-iteration26/run-regressions.py --components
python automations/checkpoint_loop/runs/m4-iteration26/run-regressions.py --production
python automations/checkpoint_loop/runs/m4-iteration26/run-additional.py
python automations/checkpoint_loop/runs/m4-iteration26/audit-dispatcher.py
python automations/checkpoint_loop/runs/m4-iteration26/final-integrity.py
```

Final results, full commands and artifact paths are recorded under
`automations/checkpoint_loop/runs/m4-iteration26/`: `dispatcher-current/summary.json`,
`dispatcher-evidence.json`, `results.json`, `final-evidence.json`,
`lowclock-evidence.json`, `verification-commands.json`, `source-integrity.json`
and `artifact-manifest.json`. All 29 baseline regression scopes pass, including
37 Python/20 Scala tests, ordinary clean RTL VCS, full M2/M3 and production
FCFS/FASED. Fresh actual harness components match 493,039 continuation samples
and pass all negative/lifecycle checks. The five low-clock cuts preserve
13,507,456 generated words and four full 4 MiB channels each, with byte-identical
40-port target traces at 774,628/774,632 default/randomized target cycles.
The paired audit checks 80 software owners and 67,537,280 generated words,
permitting historical reporting timestamps and two falling clock-gate outputs.
The active-gate terminal fixture ends after exactly 12 host/12 target edges.
All independent audits pass. The harness tests retain recorded native DPI
outputs and remain separate from the new dispatcher component test.

VCS uses Y-2026.03-SP1,
`-full64`, GCC/G++ 13 and the required environment helper sourced last. Reused
production builds use `VCS_FLAGS=-Mupdate`. Level-1 remains independent of Level-2.
Plans, conda and PDFs are preserved without staging, commit/reset/clean.
No full runtime restore, physical FPGA, formal or ASIC acceptance is claimed.

Next: connect this bootstrap to the actual harness/generated loader and DPI
publication/resampling path, bind and prevalidate all owners in one `.fsckpt`,
then compare a fresh full FCFS VCS metasim process with outstanding native/FASED
traffic against uninterrupted target outputs and transaction timing.
