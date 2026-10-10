# M6 live boundary shadow — iteration 48

This increment implements the live semantic-DUT synchronization adapter and
tests it with ordinary clean RTL VCS beside VCS FireSim metasimulation. The
authoritative InventoryFixture boots normally; it is **not Level-1 restored**.
The audited FCFS/FASED restored profile still needs its Level-2 state mapping,
semantic cut alignment and target boundary adapter. M6 remains in progress.

`tools/checkpoint_formats/live_shadow.py` validates a standalone `.rtlckpt`,
complete semantic state inventories in both emitted RTL files, all boundary
ports, one concrete DUT instance and one supported target clock. Renamed,
threaded, missing, extra or reshaped state, incompatible images, unknown values
and unsupported cycle ranges reject. Session identity includes the image,
configuration, manifests, both RTL files and logical origin. This extends the
existing hierarchy-preserving Level-2 oracle; it does not establish a general
mapping through FAME transforms.

For S[C], I[C], O[C] before the actual gated target rising edge C:

1. The authoritative observer sends all target inputs and outputs and blocks
   in DPI before that edge's NBA updates. Host/model stalls produce no rows.
2. Clean RTL applies I[C], settles its combinational boundary and compares all
   13 outputs, including ready/valid and payload bits on every cycle.
3. Only a successful comparison advances the clean clock once and sends ACK C.
   The authoritative observer then returns, allowing its original edge to run.
4. First divergence exits immediately. No clean output drives the environment.
   An acknowledged END completes the session; premature EOF fails explicitly.

`live_shadow_transport.cc` is host-only UNIX-socket code. It validates exact
packet membership, canonical known hex bits, widths and padding, consecutive
target cycles and acknowledgments before SV parsing. Every connection or
message operation has a monotonic 30-second deadline. Existing socket paths
are preserved. Checkpoint capture/transport RTL is unaffected.

The clean process loads and reads back all 22 semantic register/memory words
at C=26, with a queued request and response held under backpressure, before
any clean target edge. Future inputs come from the concurrently running
metasim; neither process reads a finite trace. The matched-boundary audit is
an output diagnostic. `+inventory-shadow-rounds=1024` adds 107520 target edges
after every original directed fixture check. Each round alternates 32 held
cycles, 64 active cycles, a memory write and eight drain cycles; request address
stays stable during each valid interval. The option is disabled by default.

The first live trial matched all 107531 cycles C=26..107556 and 1397903 output
comparisons, including 28675 held responses, 18434 response transfers and
79872 blocked request cycles. A real clean `responseData` bit deposit first
diverged at C=29 (`io_respData`: expected 103, actual 102), after exactly three
matched cycles. The authoritative process printed EOF failure but hung in
ordinary `exit` teardown while its native worker waited for the blocked edge.
The final failure path flushes diagnostics and uses `_Exit(1)` to avoid VCS
teardown, reporting the authoritative target cycle and pending acknowledgment.
The failed diagnostic trial was interrupted with exit 130 and preserved. The
complete final source-bound two-VCS scope ran afresh: all 107531 cycles match,
independent DUT counter/FSM indexing and held response valid/payload checks
pass, and actual corruption stops both processes with exit 1 at C=29. The
authority reports `target_cycle=29 pending=1`; no failing edge is acknowledged.

All 67 Python tests, complete M2 replay (five fresh cases, trace mismatch and
four loader rejections), and complete M3 banked-capture/clean-replay scopes pass.
The corrected native ASan/UBSan scope passes all 24 independent socket-peer
cases, including malformed values/cycles/ACKs, EOF, wrong sessions/origins,
preservation of an existing socket destination and a real 30-second timeout.
The verifier archives the metasim executable under its compiled basename and
copies its VCS companion directory, pins source inputs before building and
checks their hashes again before publishing success. All VCS shells source
both repository environments and `vcs-env.sh` last; builds use Y-2026.03-SP1,
full64, GCC/G++ 13 and `VCS_FLAGS=-Mupdate` on the reused Make directory.

Diagnostics, exact command records and artifact catalogs belong under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m6-iteration48/`.
Final VCS evidence is `live-shadow-final/invocation-wf266xei/summary.json`,
the complete matched audit and both corruption logs beneath that invocation.
The corrected native evidence is selected by `native-transport-immediate/latest.json`.
`verification-commands.json` records actual argv arrays; `summary.json` and
`artifact-manifest.json` are independently checked by `final-integrity.py`.
The two root papers' replay/snapshot and gate-level activity sections were
read from their existing extracted text. No physical FPGA, formal state
correspondence, ASIC activity or power validation is claimed.

Next: establish the FCFS pre-FAME semantic inventory and a complete mapping to
its transformed DUT state; capture independent Level-1 and Level-2 images at
the same audited target cut; attach live authoritative input/output extraction
to the restored production target boundary, preserving FASED timing and
combinational dependencies. Reuse the tested transport/comparator and repeat
the sustained run and actual state-corruption check from a fresh Level-1
restored process. Do not turn the existing 40-port host-edge diagnostic trace
into a target-cycle input source without auditing FAME token consumption.

The loop names this M6, while the read-only agent plan calls live clean RTL M7
(Phase 8). Follow the assigned task; the numbering correction remains only in
checkpointing documentation. Both plans retain their iteration-start hashes
and remain unstaged. No conda/PDF edits, commits, resets or history cleaning.
