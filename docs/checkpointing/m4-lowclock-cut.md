# M4 parked driver at a low-clock cut — iteration 25

M4 remains in progress. The new `+fs-driver-lowclock` modifier requires
`+fs-driver-settled` and a completed-operation diagnostic request. It parks the
production driver through the natural falling edge, without another native
tick, host-delay draw or rising target edge. Capture follows NBA/combinational
settlement by one picosecond. Every generated register/RAM word and every
audited software owner is observed while that same worker remains parked.
All 27 incoming, outgoing and published packed harness banks, clock/reset/finish
flags and the diagnostic trace-count slot are included.

The returned-operation callback precedes the dispatcher's next normal yield.
After capture, the existing continuation resumes; its final outgoing banks
are published, then incoming wire latches refresh after one picosecond before
the next rising native tick. This resampling matters because the normal
driver finishes before the falling-edge sample, whereas this cut delays that
completion until afterwards. Resampling consumes no AXI transaction. If the
driver finishes at the low-clock cut without another yield, the scheduled
rising edge is cancelled.

The native adapter independently checks the packed clock bit against the
requested phase before observing owners or publishing a diagnostic. Invalid,
duplicate and unpaired modifiers reject. The immutable harness observation
still has no load adapter. Fresh harness component loading remains separately
bound to the exact updated top.sv source/geometry and rejects DEBUG/gate-level
configurations. No generated checkpoint transport hardware changed.

`verify_settled_boundary_vcs --lowclock` retains the complete five-cut scope:
default cuts 3/11/699275/699276 and randomized cut 101, four complete 4 MiB
functional-memory channels, every generated word, the entire 40-port target
AXI/FAME trace, terminal capture and fail-closed requests. The VCS monitor
requires input refresh before the next rising edge and prohibits a rising
edge during parked continuation. `verify_lowclock_cut` compares each cut
against its rising-edge capture: every software payload agrees except the
historical elapsed-time timestamp, and every generated word agrees except
the clock-gate outputs that fall to zero. It independently checks emitted
RTL coverage, build identity and harness bank geometry.

Final verification passes all five low-clock cuts, seven negative requests and
terminal capture. Each cut preserves 13,507,456 generated words and four full
4 MiB functional-memory channels. Default/randomized target completion remains
774,628/774,632 cycles; the complete 40-port traces and generated observations
match uninterrupted execution. Cut 699275 retains an in-flight native write
at cycle 699360 plus outstanding FASED traffic. All 16 audited software owners
agree across each falling edge, allowing only the historical reporting
timestamp to differ. The paired audit checks 67,537,280 generated words; only
the two clock-gate outputs fall to zero. The harness diagnostic is separately
checked against all source-derived bank widths and low-clock/reset/finish flags.

Native ASan/UBSan passes 80 boundary/configuration/suspended/phase rejections.
The actual-harness terminal fixture, with its generated clock gate enabled,
passes exactly 12 host/12 generated-clock edges and no edge after completion.
Its native services remain fixtures rather than a reconstructed driver.

All 29 existing regression scopes pass: 37 Python/20 Scala tests, compiler
codecs, all native/VCS owners, full M2/M3, ordinary clean RTL VCS, production
GCD/FASED, profiling, both rejection-liveness suites and nonempty hardware
counter expectations. The updated-source fresh harness component also passes
all 491,151 continuation samples, 29 banks/539 generated words before the first
edge, 53 malformed loads and four lifecycle guards. Its native checks pass
2,014 validation, 2,016 readback, 2,015 interruption and nine initialization/
advancement rejections. All independent artifact audits pass. The initial
unguarded low-clock trial and passive-gate terminal trial remain separate
successful diagnostics; the final guarded/active-gate results are authoritative.

Final evidence under `automations/checkpoint_loop/runs/m4-iteration25/`:
`lowclock-final/summary.json`, `lowclock-evidence.json`,
`lowclock-finish-active/summary.json`, `harness-final/summary.json`,
`results.json`, `final-evidence.json`, `verification-commands.json`,
`source-integrity.json` and `artifact-manifest.json`.

Reproduction from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_settled_boundary_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration25/lowclock-final --lowclock
python -m tools.checkpoint_formats.tests.verify_lowclock_finish_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration25/lowclock-finish-active
python automations/checkpoint_loop/runs/m4-iteration25/run-regressions.py --components
python automations/checkpoint_loop/runs/m4-iteration25/run-regressions.py --production
python -m tools.checkpoint_formats.tests.verify_lowclock_cut \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --high automations/checkpoint_loop/runs/m4-iteration25/settled-boundary-verified \
  --low automations/checkpoint_loop/runs/m4-iteration25/lowclock-final \
  --out automations/checkpoint_loop/runs/m4-iteration25/lowclock-evidence.json
```

VCS uses Y-2026.03-SP1, `-full64`, GCC/G++ 13, and `VCS_FLAGS=-Mupdate` for
reused production Make builds. Every VCS shell sources `vcs-env.sh` last.
Plans/conda/PDFs are preserved without staging, commit/reset/clean. No plan
correction, full Level-1 restore, physical FPGA, formal or ASIC acceptance is
claimed. Level-1 and Level-2 remain independent.
The relevant state/replay sections of both root papers were read: their RTL
snapshot plus finite I/O trace does not replace M4's native/runtime ownership.
Extracted reading diagnostics are retained under the iteration's run directory.

Next: reconstruct the fresh dispatcher/DPI continuation for this precise
pre-resume low-clock phase, bypass ordinary initialization/MMIO and the initial
native tick, and refresh outputs/inputs before the first resumed rising edge.
Then bind and prevalidate all generated/software/harness/context owners in
one `.fsckpt` and compare fresh full VCS metasim continuation with outstanding
native/FASED traffic. Unsupported drivers, callbacks and stream/runtime owners
must continue to fail closed. Full runtime checkpoint requests still reject.
