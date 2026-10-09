# M4 incremental production driver boundaries — iteration 16

M4 remains in progress. FCFS dispatch now returns to the simulation-flow
coordinator after each completed host operation. A diagnostic hook captures
the audited software owners together while VCS is parked inside DPI. This
is not a settled whole-runtime cut, a `.fsckpt`, or fresh-process FireSim
restoration. No external dependency is missing.

`simulation_t` exposes opt-in `simulation_supports_steps()`,
`simulation_run_step()` (true on completion), and
`simulation_run_finalize()`. Unsupported implementations reject incremental
access. `execute_simulation_flow()` drives the FCFS dispatcher and invokes an
optional callback after every returned operation, including completion, before
final checks. Other drivers retain their existing synchronous path. The FCFS
finalizer rejects an unfinished run loop. This separates run-loop continuation
from final event-counter MMIO checks; initialization, configuration, performance
baselines, concrete bridge state and full simulation ownership remain unaudited.

Metasim options `+fs-driver-cut=N +fs-driver-diagnostic=PATH` request one
software diagnostic after N completed dispatcher operations. N is **not**
target time, host-clock time or scheduler credit. Strict positive unsigned
parsing rejects missing partners, duplicates, malformed numbers and empty
paths before initialization. A driver without incremental dispatch rejects
before its first tick/initialization. An unreached request rejects before
finalization/success reporting. An unaudited profiling callback rejects capture.

The hook checks driver-thread identity and the published DPI ownership phase.
It prohibits MMIO, stream transactions, recursive capture and RTL advancement
during capture. It enumerates all registry widgets in generated constructor
order, the driver components, MMIO, every functional-memory channel and the
host timing owner. Unsupported schemas stay in the diagnostic inventory with
empty payloads; generated RTL, harness and execution-context owners are explicit
unsupported records. Stream wrappers and QSFP owners are also explicitly
unsupported when present. Audited payloads are saved/validated, then saved
again to check stability before any file opens. Duplicate/aliased identities,
changing schemas/payloads and failed adapters reject; errors poison that request.
Publication uses a temporary file and rename. Existing destinations are refused.
There is no diagnostic restore path or claim of build-bound integrity.

The diagnostic framing is `FSDIAG01`, followed by little-endian uint64 completed
operation count and record count. Each record has length-prefixed UTF-8 owner
identity, schema and byte payload (each length is uint64). An empty schema
means explicitly unsupported and has no payload. Full-memory payloads include
all bytes plus burst progress, dummy data and queued responses. The existing
component schemas remain independent. Python's verification reader is in
`tools/checkpoint_formats/tests/verify_driver_boundary_vcs.py`.

The distinction between the software boundary and the harness boundary is
essential: `top.sv` latches RTL-to-software records at a falling edge, calls DPI
at the next rising edge, then updates software-to-RTL latches. In the hook,
software's AXI tick has consumed the previous records but DPI output and RTL
NBA updates have not completed. Merely copying generated registers here could
pair them with the wrong transaction phase. To achieve a whole-runtime cut,
park the driver at this returned-operation boundary, explicitly transfer
control back through DPI, settle and capture all harness signal banks/clock,
reset and completion phase alongside generated state, and restore that phase
with fresh contexts before any target edge. Do not drain outstanding requests.

Verification and diagnostic artifacts are under
`automations/checkpoint_loop/runs/m4-iteration16/`. The complete reproduction
commands are recorded as argv arrays in `verification-commands.json`; the new
focused check is:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_driver_boundary_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration16/driver-boundary-fixed \
  --reference automations/checkpoint_loop/runs/m4-iteration16/fased-inventory
```

Results are recorded in `driver-boundary-fixed/summary.json`,
`driver-boundary-late/summary.json`, `rejection-liveness/summary.json` and
progress.md. The first late samples had empty native queues; accounting for
reset offsets aligned cut 699275 with an in-flight channel-0 functional write.
Failed trials remain in the run directory. Worker-thread `std::exit()` also
deadlocked VCS exit handlers while the main thread waited in DPI. The failure
path now flushes diagnostic output and calls `std::_Exit()`; three production
rejection cases verify failure exit within 30 seconds without partial files. Every VCS shell sources both environments and `vcs-env.sh` last,
using Y-2026.03-SP1, `-full64`, GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`.
The DESSERT deterministic token and Strober exact state/I/O replay sections
were reread from the root-paper text extractions under `runs/m2-iteration7/`.
No plan correction is proposed; both plans remain read-only inputs.

Next: use this callback boundary for a settled harness/coordinator handshake;
finish concrete widget/bridge/stream and simulation-lifecycle adapters; bind all
owners and generated RTL to one manifest/build-bound `.fsckpt`; prevalidate and
load into fresh VCS metasim before target advancement; compare target outputs
and transaction timing with outstanding traffic. No full Level-1, physical
FPGA, formal or ASIC activity/power acceptance is claimed.
