# M4 MMIO and CPU-managed AXI owners — iteration 12

M4 remains in progress. The metasim MMIO/CPU-managed AXI queues now own their
payload bytes and implement complete component save/validate/load hooks.
Fresh VCS DPI processes reproduce the transport and functional-memory
components together, including partially accepted bursts and queued responses.
Coherent whole-runtime capture and fresh-process FireSim metasim restoration
remain outstanding. No external dependency is missing.

`mmio_t` implements `firesim.mmio.full.v1`. Its little-endian payload stores
AXI ID/address/data geometry, read/write in-flight flags, idle bus data,
all AR/AW request IDs/addresses/sizes/lengths, all queued W data/strobes/last
flags, all queued R IDs/data/last flags and every queued B ID, in FIFO order.
Lengths count queue records, with every byte of every bus beat retained.
No C++ object layouts, pointers, driver stacks or padding are serialized.

Write requests previously retained pointers into the driver's stack or DMA
buffer. They now copy the payload at enqueue; ordinary synchronous callers
still wait for the same AXI handshakes, and caller mutation/destruction cannot
change queued writes. Narrow requests retain the existing low-byte layout with
zero padding; strobes are masked to the bus width as the DPI transport does.
Read responses likewise use owned vectors, releasing even unconsumed responses
when the owner is destroyed. Reset still gates handshakes without clearing the
MMIO queues or in-flight flags. No hook ticks, drains or issues MMIO.

Validation rejects unsupported geometry, wrong schema/version or AXI widths,
invalid Booleans, malformed request shapes, oversized/truncated queues, wrong
response IDs/last flags, inconsistent flags, impossible request/data counts,
reordered write last flags, responses preceding write completion, and trailing
bytes. AW/W independence is preserved: W may precede AW, and later write data
may already be buffered while B awaits driver service. Queued requests use
the production issuer's ID 0. Supported geometry
has 4/8/16/32/64-byte beats, up to 64-bit ID/address fields, and 0..255 AXI
burst lengths. Load parses and allocates the entire replacement before swapping
any state; every rejected payload leaves the owner unchanged.

`simif_emul_t::checkpoint_axi_owners()` exposes an **AXI-owner subset** using
stable names: `runtime/mmio`, `runtime/functional-memory/N`, optional
`runtime/cpu-managed-axi4`, and optional `runtime/fpga-managed-memory`.
Configuration order supplies memory indices; addresses are not identities.
This API is compiled in the actual metasim builds. It is not a complete
runtime inventory or an integrated freeze/capture coordinator. The generic
driver preflight remains unchanged and all full save/restore requests reject
the unaudited `widget/0` before driver initialization.

Remaining runtime inventory, checked against the current sources:

| Owner/source | State still requiring an adapter or explicit audit |
| --- | --- |
| `emul/simif_emul.h`, `.cc` | `maximum_host_delay`, `fuzz_seed`, full `fuzz_gen` state, `memsize`, `load_mem_path`; `advance_target`'s local `nticks`/loop index; outstanding `wait_read`/`wait_write` and stream-loop continuation/destination buffers. |
| `emul/simif_emul.h` | `finished`, `exit_code`, `driver_flag`, `rtlsim_flag`, thread ownership/handoff phase. Reconstruct synchronization primitives at a defined parked boundary; do not serialize mutex/thread objects. |
| `verilog/top.sv` | `clock`, `reset`, `fin`; incoming `*_fwd_sync` / `*_rev_sync`, DPI-written output `*_sync` and driven `ctrl_rev`, stream/memory/QSFP output records; pending edge/NBA phase. `simulator_tick` uses delayed inputs, so a settled generated `FPGATop` snapshot alone cannot reconstruct these latches. |
| `core/simulation.h`, `.cc` and concrete simulation drivers | Initialization/run/finish phase, load/zero/fingerprint settings, clock/performance baselines and concrete test/main-loop progress. Fresh restore must bypass initialization actions that overwrite loaded RTL or memory. |
| `core/systematic_scheduler.h` | `max_cycles`, `default_step_size`, `current_cycle`, each task's `next_cycle` and callback identity/closure state. A `std::function` address is not a restorable identity. |
| `bridges/cpu_managed_stream.h`, `fpga_managed_stream.h` | Stream geometry/order/configuration, pending calls; FPGA-managed `buffer_offset`, logical backing-buffer identity and address mapping. Pointer values must be rebound, not deposited. Stream engines retain default unsupported hooks. |
| `bridges/fased_memory_timing_model.h` | `user_configuration`, `profile_reg_addrs`, histogram latency baselines, range-counter bytes, stats-file continuation, `mem_size`, `useHardwareDefaults` and initialization/configuration phase. |
| `core/widget_registry.*` and all concrete bridges | Every registered widget/bridge remains unsupported pending audit, including passive-looking master/clock/loadmem/reset drivers; PeekPoke also has `req_timeout`/`req_unstable`. Generated bridge RTL is already independently inventoried. |
| `emul/qsfp.h`, `.cc` | TX/RX queues, saved receive bits/valid, shared-memory buffers, peer/semaphore protocol and external partition state. Reject QSFP/partitioned restoration until a coordinated adapter exists. |

The source paths in this table are relative to
`sims/firesim/sim/midas/src/main/` (`cc/` for C++ sources). This is a source
inventory of outstanding work, not proof of complete runtime coverage.

The new `verify_mmio_checkpoint_vcs` connects the actual production `mmio_t`
to `mm_magic_t` under independent channel stalls. A Python AXI/byte scoreboard
checks every observed transport output, consumed read response, write
completion, captured queue field, and all 4,096 backing-memory bytes. Both
owners validate before either loads, and both must reserialize byte-identically
before the first edge in the fresh process. Both final owners also match.

Thirteen cuts (0/1/3/6/9/12/16/19/23/27/35/42/55), four beat widths
(4/8/32/64 bytes), and native ASan/UBSan plus VCS DPI give 104 fresh
continuations and 7,168 compared component edges, half in VCS. For example:

| Cut | Transport AR/AW/W/R/B queues | Peer remaining write beats | Peer queued read beats |
| --- | --- | --- | --- |
| 6 | 4 / 3 / 7 / 0 / 0 | 3 | 4 |
| 16 | 4 / 4 / 6 / 4 / 1 | 0 | 0 |
| 23 | 3 / 3 / 5 / 2 / 0 | 2 | 1 |

Native negative checks reject 593/637/901/1,252 malformed/mismatched payloads
per beat width, including every truncated prefix and incompatible owners.
Additional checks cover narrow requests, a 256-beat burst, caller-buffer
mutation/destruction, 64-bit address/ID geometry and unsupported geometry.
Native and VCS checks also accept/continue W-before-AW and later buffered W
bursts during a held B response; the memory model's W-ready policy alone
would not exercise those legal AXI states.

Reproduce from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_mmio_checkpoint_vcs \
  --out automations/checkpoint_loop/runs/m4-iteration12/mmio-owner
```

All existing regressions pass: 24 Python and 20 Scala tests; compiler
codec/corruption and emitted-memory coverage; full memory-owner continuation
(64 fresh cases/1,704 edges); generated InventoryFixture coverage (539 words)
and all three unsupported requests; full M2 (five fresh cases/108 samples/
1,404 comparisons and negative tests); full M3 (six byte-identical captures,
547 stalled boundaries, 5 semantic/242 transfer replay samples and eight invalid
reads); ordinary clean InventoryDUT VCS; and GCD VCS metasim (12 target cycles).
The complete 10,000-transaction FCFS fuzzer passes after 774,628 target cycles,
with all 513 generated instances/2,856 entries/13,507,456 words captured at
three outstanding-traffic samples. Its complete capture SHA-256 is unchanged
from iteration 11:
`b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`.
FASED full save/restore requests still reject `widget/0` explicitly and publish
no incomplete checkpoint.

The complete regression run is recorded in
`automations/checkpoint_loop/runs/m4-iteration12/regression-results.json` and
`verification-commands.json`; `artifacts.json` lists absolute artifact paths
and hashes. Diagnostic files remain under that run directory.
All VCS shells source both repository environments, then `vcs-env.sh` last;
Y-2026.03-SP1, `-full64`, GCC/G++ 13, and `VCS_FLAGS=-Mupdate` on reused Make
builds are retained. The DESSERT DMA/token and Strober snapshot/trace sections
were reread from the existing root-paper text extractions under
`runs/m2-iteration7/`. No plan correction is proposed.

Next: enumerate/audit the remaining runtime and driver owners, including stream
engines, harness AXI input/output latches and clock/reset phase, PRNG and pending
host-delay loop progress, thread handoff, simulation/scheduler progress, and
FASED driver configuration/profiling baselines. An arbitrary suspended C++ call
stack is not restored by an AXI queue payload. Establish an explicit resumable
driver boundary with both contexts frozen, coordinate complete generated RTL
and functional memory capture without draining traffic, and publish a
manifest/build-bound `.fsckpt`. Prevalidate every owner and RTL handle before
loading a fresh VCS metasim process and advancing target time, then compare
target-visible outputs and transaction timing with uninterrupted execution.

These `.owner` payloads require the future coordinator's integrity/build/owner
membership contract and coherent freeze. Component edges are not target-cycle
acceptance. Level-1 owners remain independent of Level-2 checkpoints. No full
Level-1 continuation, physical FPGA, formal or ASIC activity/power validation
is claimed. Plans, conda files and PDFs were preserved without staging, commit,
reset or cleaning.
