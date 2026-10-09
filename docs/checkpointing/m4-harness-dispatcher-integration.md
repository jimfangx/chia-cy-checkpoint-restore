# M4 harness/dispatcher integration — iteration 27

M4 remains in progress. A component coordinator can now load native/driver
owners, call `simif_emul_t::arm_restored_driver`, load and verify generated RTL
and harness banks, then invoke `emul.checkpoint_resume_restored()` before any
host or target rising edge. Production `+fs-restore`/`+fs-checkpoint` requests
still fail closed. Aggregate `.fsckpt` publication/loading and fresh production
FCFS/FASED continuation remain outstanding.

The actual VCS harness waits for entry to finish. If restoration is armed, it
holds the clock low until bootstrap publishes outgoing DPI banks, settles the
wires, refreshes incoming latches, and finishes their NBA settlement. The fresh
worker bypasses ordinary initialization, memory loading, timing draws and the
initial native tick. The native AXI models are not ticked again during bootstrap.
Ordinary ticks, parked diagnostic continuations and fresh bootstrap share the
same read-only DPI output publisher. A terminal restored flow joins/deletes its
native simulator and publishes finish before clock startup, producing zero
edges. Transient entry/restore handshake flags are reconstructed from fresh
construction; they are not target state or a serialized process stack.

Arming requires a freshly loaded incremental flow and audited concrete/widget
owners. It rejects diagnostics, managed stream IO, QSFP, more than four memory
channels, ordinary/repeated startup and unsupported drivers before creating a
worker. Resume validates low clock and deasserted reset/finish. Failed bootstrap
consumes and poisons the destination, preventing fallback to ordinary or direct
restored startup. The harness task also rejects premature/repeated entry and
DEBUG/gate-level modes through an explicit nonzero DPI failure. The component
coordinator remains responsible for complete membership/build binding and all
native/RTL prevalidation/readback; this API does not assert aggregate ownership.

`verify_harness_dispatcher_vcs` uses the actual `top.sv`, 539 generated words,
all 29 harness words, actual `dpi.cc`, pthread dispatcher, simulation base and
native MMIO/functional-memory/host-timing owners. A small audited incremental
driver uses fixture MMIO services for base initialization/finalization. An active
generated clock gate makes accidental edges observable. Native memory requests
are seeded explicitly; the harness subsequently services them through real DPI.
The fresh process waits beyond two normal clock periods while armed, with zero
host/target edges, then loads and verifies all components before bootstrap.
This is component integration, not production driver or whole-runtime acceptance.

Five cuts (operations 13, 14, 16, 31, 32) match all 55 complete generated-state,
harness-bank and top-output continuation samples. All 35 native owner comparisons
match before the first edge; native MMIO and memory remain byte-identical through
bootstrap and at completion. Each cut retains all 4 KiB functional memory, a
partial two-beat write, two held read responses and the native model cycle.
An independent operation oracle checks every resumed driver submission and
finalization call; restored host/active target edge counts equal the remaining
reference edges. The terminal cut completes without an edge. Thirty-five fresh
malformed-owner processes reject before any restored-owner/driver-trace
publication. Twenty fresh unsupported-driver/reset/finish/repeated-bootstrap
processes reject explicitly, and 25 arming lifecycle checks pass. The independent
artifact audit verifies 65 distinct simulator processes and actual DPI linkage.
A separate ASan/UBSan API test injects finish/reset/high-clock/null/invalid-geometry
failures into six armed destinations. All 36 bootstrap/fallback calls reject,
all 30 loaded-owner comparisons stay unchanged, and no worker or edge starts.

Two failed initial diagnostics remain separate: the first omitted VCS's compile
option enabling register initialization, so generated values contained Xs; the
second incorrectly expected the real native model's cycle field to stay at one,
as in the earlier fixture-only dispatcher test. The final run checks complete
native cycle/state equality instead. Neither failed trial is reported as passing.

Reproduction from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_harness_dispatcher_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration27/harness-dispatcher-final
python automations/checkpoint_loop/runs/m4-iteration27/audit-harness-dispatcher.py
PYTHONPATH=. python automations/checkpoint_loop/runs/m4-iteration27/verify-arm-poison.py
python automations/checkpoint_loop/runs/m4-iteration27/run-regressions.py --components
python automations/checkpoint_loop/runs/m4-iteration27/run-regressions.py --production
python automations/checkpoint_loop/runs/m4-iteration27/run-fixture-additional.py
python automations/checkpoint_loop/runs/m4-iteration27/run-additional.py
```

All 41 executed verification scopes pass, including the 29 baseline scopes,
37 Python/20 Scala tests, every native/VCS owner, ordinary clean RTL VCS, full
M2/M3, GCD/FASED, profiling, rejection liveness and hardware-counter expectations.
Existing fresh harness continuations match 477,131 samples and pass 53 malformed
loads, four lifecycle guards and all native validation/readback/clock guards.
Five low-clock production cuts retain 13,507,456 generated words and four full
4 MiB channels, with identical complete 40-port traces at 774,628/774,632 target
cycles. In-flight native/FASED traffic survives these diagnostic captures.
Seven negative requests and terminal capture pass. The independent paired audit
checks 80 software owners and 67,537,280 generated words, allowing historical
reporting timestamps and two falling clock-gate outputs. The active-gate terminal
fixture finishes after exactly 12 host/12 target edges. These production runs
remain capture/continuation diagnostics, not fresh production restart acceptance.

Diagnostics, commands and full-path artifact catalogs are under
`automations/checkpoint_loop/runs/m4-iteration27/`. VCS uses Y-2026.03-SP1,
`-full64`, system GCC/G++ 13, with the required environment helper sourced last;
reused production Make builds use `VCS_FLAGS=-Mupdate`. Plans remain read-only,
with progress/corrections only here. No FPGA, formal or ASIC validation is claimed.

Next: use this component handshake in a complete manifest/build-bound `.fsckpt`
coordinator. Bind and prevalidate every native/generated/harness/driver owner,
load and verify all state before arming/releasing the first edge, then compare a
fresh full production FCFS/FASED VCS process with outstanding traffic against
uninterrupted target outputs and transaction timing. Preserve Level-2 independence.
