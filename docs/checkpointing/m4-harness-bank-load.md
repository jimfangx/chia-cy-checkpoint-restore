# M4 fresh harness bank component — iteration 24

M4 remains in progress. `harness_restore.py` and `harness_restore.cc` add a
source/build/geometry-bound component loader for the actual non-debug VCS
`top.sv`. This adapter is separate from the read-only rising-edge diagnostic
and does not declare `runtime/harness` or the execution context restorable.
Aggregate `.fsckpt` publication/loading and fresh whole-runtime continuation
remain outstanding. Full runtime requests still fail closed.

The inventory contains all 27 packed banks: nine incoming RTL-to-host latches,
nine outgoing host-to-RTL latches, and nine published outgoing banks. Reset
and finish are separate records; the host clock is held low rather than
loaded. Unconnected optional banks remain included, including the actual
SystemVerilog widths of absent `[-1:0]` members. The current InventoryFixture
has 29 records / 4,108 bits. The layout binds the audited top.sv revision,
generated RTL build identity, both emitted Verilog headers and hierarchy.
Unknown source revisions, incomplete geometry, reset/finished cuts and
DEBUG/FSDB/gate-level configurations reject. Runtime handle checks also reject
externally compiled DEBUG state and a global gate-level reset model.

Initialization must occur at fresh simulation time zero with the host clock
known low. A VPI value-change callback permanently records clock advancement.
Load rejects an unarmed, advanced or already loaded harness. The shared VPI
implementation resolves every exact ordered handle, width, type and known
bit vector before depositing anything. Banks require `vpiStructVar`; reset
and finish require `vpiBitVar`. Validation failures leave the process unchanged.
The caller must hold clocks low and verify every bank after delta settlement
before permitting an edge. A failed readback or advancement during verification
poisons this adapter, including when a corrupted bank is subsequently repaired.
No saved simulator stack, pointer, waveform waiter or OS context is loaded.

The fresh component test compiles the unmodified production `top.sv` and the
complete InventoryFixture generated RTL. An actual uninterrupted FireSim VCS
metasim records all banks, generated state and top outputs at settled falling
edges. Three separate VCS processes load active, outstanding-operation and
held-response cuts; each checks all 29 banks and 539 generated words before
its first edge and compares every subsequent state/bank/output vector. The
actual harness performs the two latch phases. Native host DPI outputs and the
terminal finish flag are recorded/replayed fixtures. This does not reconstruct
functional-memory owners, the driver, scheduler or dispatcher. In particular,
these falling-edge component cuts cannot be mixed with the existing parked
rising-edge software diagnostics to claim an atomic runtime checkpoint.

ASan/UBSan exercises every byte-truncated prefix, missing/reshaped/wrong-type
handles, initialization/clock faults, repeated loads, and poisoned readback.
VCS checks malformed staging files without mutation or edges, late
initialization, rejection after a host edge, poisoned readback with zero
edges, and a separately compiled unsupported DEBUG harness.

The final harness suite matches 491,501 continuation samples across cuts
16,610 / 371,744 / 380,580, passes 53 malformed staging rejections and all four
VCS lifecycle guards. Native processes pass 2,014 validation/lifecycle checks,
2,016 readback-fault checks, 2,015 clock-interruption checks, and nine early
advancement/initialization checks. The independent full artifact audit passes.
All 29 existing regression scopes also pass: 37 Python / 20 Scala tests,
compiler codecs, all native/VCS owners, generated loading, full M2/M3, ordinary
clean RTL VCS and production GCD/FASED. All five settled production cuts retain
13,507,456 generated words and four full 4 MiB memory channels with identical
40-port target transaction traces; the late cut retains in-flight native/FASED
traffic. Profiled FCFS, both rejection-liveness suites and nonempty hardware
counter expectations pass. These production checks verify capture behavior;
they do not establish fresh whole-runtime restoration.

Final evidence and exact commands are beneath
`automations/checkpoint_loop/runs/m4-iteration24/`: `harness-final/summary.json`,
`harness-evidence.json`, `results.json`, `final-evidence.json`,
`verification-commands.json`, `source-integrity.json` and
`artifact-manifest.json`. Initial trials remain separate diagnostics: missing
callback timing metadata, unsupported VCS struct handle type, an omitted
fixture finish flag, and test-monitor errors were corrected. Their failing
logs are not passing evidence.

Reproduction from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_harness_restore_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration24/harness-final
python automations/checkpoint_loop/runs/m4-iteration24/audit-harness.py
python automations/checkpoint_loop/runs/m4-iteration24/run-regressions.py
```

Every VCS shell sources `vcs-env.sh` last: Y-2026.03-SP1, `-full64`, GCC/G++ 13,
and reused production Make builds use `VCS_FLAGS=-Mupdate`. Plans/conda/PDFs
are preserved without staging, commit/reset/clean. No plan correction is
proposed. Level-1 and Level-2 remain independent; no physical FPGA, formal or
ASIC activity/power acceptance is claimed.

Next: establish a coherent supported runtime phase and reconstruct the parked
driver/DPI continuation without an extra native tick or target edge; bind and
prevalidate every generated/software/harness owner in one `.fsckpt`, then
compare fresh full VCS metasim outputs and transaction timing with outstanding
native/FASED traffic. Unaudited drivers/callbacks and FPGA-managed streams
remain unsupported.
