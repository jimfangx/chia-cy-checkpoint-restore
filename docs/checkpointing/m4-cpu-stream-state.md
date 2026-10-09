# M4 CPU-managed stream host state — iteration 20

M4 remains in progress. `CPUManagedStreamWidget` now implements
`firesim.widget.cpu-managed-stream.v1` at completed calls. Its two concrete
CPU-managed stream drivers retain no host queue, partial beat, read offset or
batching buffer. Generated stream FIFOs and CPU-managed AXI/MMIO transactions
remain separate generated/native owners; this adapter does not omit or drain
them. Generic and FPGA-managed stream engines still have no checkpoint schema.
FPGA-managed streams retain a mapped peer buffer, physical address and read
offset that have not been audited for restoration.

The payload binds the engine index, AXI beat bytes and both ordered direction
vectors. Each stream binds its name, DMA address, count-register address, FPGA
buffer capacity and stream beat width. One flag preserves whether initialization
has completed. Empty direction vectors also have an explicit payload. Loading
validates the entire configuration and flags before changing the lifecycle;
save/validate/load perform no MMIO, DMA, initialization or clock advancement.
Repeated ordinary initialization and the existing push/pull/flush ordering are
preserved. Suspended and reentrant calls reject before I/O; an exception escaping
an operation poisons the engine, so a partly completed transfer cannot be
declared an idle checkpoint. Caller buffers and suspended stacks are unsupported.

The independent generated-constructor verifier now recognizes the exact
CPU-managed emitter syntax and ordered parameters. Changed configuration, bus
width, lifecycle, malformed literals and unaudited driver declarations fail
closed. The current four production designs have no CPU-managed stream engine;
their verification checks linkage and existing state/timing, not actual
generated stream hardware continuation.

Native ASan/UBSan and fresh VCS DPI processes exercise actual production stream
methods against an independent Python byte-queue/I/O oracle. Across 8/16/64-byte
AXI beats and two stream widths, 144 fresh component continuations match 1,656
operations, including full/empty queues, minimum thresholds, partial transfers,
zero-byte requests, flushes, queued byte contents and repeated initialization.
All 144 restored host payloads agree before the first fixture edge. Each of the
six backend/width combinations passes 2,154 malformed/configuration/lifecycle/
suspended/reentrant/interrupted-call rejections. Another 42 malformed fresh
processes reject before opening a trace or dispatching a fixture edge. Queue
service snapshots are test fixture state, not generated RTL or `.fsckpt` files.
The initial compiler-warning trial and verifier keyword error remain in
separate run directories and are not passing evidence.

All 25 regression commands pass, including 31 Python/20 Scala tests, compiler
codecs/emitted-memory checks, existing native/VCS owners, full M2/M3, ordinary
clean RTL VCS and default/randomized GCD. All five production settled cuts
retain 13,507,456 generated words and four full 4 MiB memory channels. Their
complete 40-port target AXI/FAME traces and generated observations are
byte-identical to uninterrupted references. Default cuts finish at 774,628
cycles; randomized cut 101 finishes at 774,632. Cut 699275 retains an in-flight
native write and outstanding FASED target writes. Standalone and all four legacy
captures retain hash
`b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`.
Profiling preserves four samples at 774,629 cycles. Both three-case worker/
settled rejection-liveness suites pass, and current stream adapters are linked
in all four actual metasim executables. The final evidence audit independently
rechecks every component payload and full production trace before cataloging
source hashes and all artifact paths.

Reproduction from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_stream_checkpoint_vcs \
  --out automations/checkpoint_loop/runs/m4-iteration20/stream-owner-final
python automations/checkpoint_loop/runs/m4-iteration20/run-regressions.py
```

Exact command arrays, diagnostic logs and artifact catalogs are under
`automations/checkpoint_loop/runs/m4-iteration20/`. Every VCS shell sources both
repository environments then `vcs-env.sh` last, with Y-2026.03-SP1, `-full64`,
GCC/G++ 13 and reused Make `VCS_FLAGS=-Mupdate`.

Next: own simulation initialization/finalization and output artifacts; load
harness banks and reconstruct parked dispatcher/DPI continuation before the
next edge; prevalidate/load complete generated and software state in one
manifest/build-bound `.fsckpt`; restore a fresh VCS metasim and compare target
outputs and transaction timing with outstanding memory traffic. Full runtime,
harness, execution-context and generated RTL load remain unsupported. The
relevant DESSERT/Strober state and I/O replay passages were read from existing
root-paper text extractions under `runs/m2-iteration7/`. Level-1 and Level-2
remain independent. No external dependency is missing; no whole FireSim
restart, physical FPGA, formal or ASIC activity/power acceptance is claimed.
Both plans, conda files and root PDFs remain untouched; no plan correction is
proposed.
