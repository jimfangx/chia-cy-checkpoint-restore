# Rocket checkpoint image implementation and build

Current build preparation: `automations/checkpoint_loop/runs/aws-f2/iteration176/checkpoint-build/`.
Original hardware baseline and initial synthesis: `automations/checkpoint_loop/runs/aws-f2/iteration175/`.
This document is a proposed implementation sequence, not an image receipt.
The stock Rocket public image is baseline-only. The existing
`BankedStateAccess.scala` has explicit client ports but no generated Rocket
bindings; `make/checkpoint.mk` currently admits only a VCS FCFS profile.
Setting that profile on an F2/Rocket build must continue to reject.

Preserve the exact Rocket recipe in `checkpoint-build/config_build_recipes.yaml`:
`f2`, project `firesim`, design `FireSim`, QuadRocket target config,
`WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config`, 140 MHz,
and build strategy `TIMING`. Never silently replace this target with a fixture.
The generated build config uses ExternallyProvisioned `[localhost]` and the
invocation-local `build-host/`; the manager's release operation is a no-op.

1. Bind complete pre-FAME semantic and final simulator inventories to a
   synthesizable bank network. Generate logical register/memory reads,
   width chunking and owner IDs from compiler IR; hierarchical VCS references
   cannot implement this. Fail generation on uncovered black boxes, storage,
   clocks or owner types. Preserve complete memory contents and in-flight work.
2. Add an atomic cut coordinator connected to all token/channel, timing-model,
   bridge and DUT owners. Use the authoritative target edge count. Gate the
   accepting edge and every relevant write/reset; acknowledge a common frozen
   cut before bank reads. Keep transport/control clocks operational. A DUT-only
   freeze or waiting for all traffic to drain does not establish an atomic cut.
3. Connect a CheckpointBridge with a versioned MMIO ABI and DMA stream. Bind
   manifest/build identity, owner and word counts, target cut, sequence numbers,
   terminal status and integrity checks. Hold data under backpressure and hold
   the global freeze through capture completion. Explicitly reject unsupported
   commands, busy requests, missing owners and DMA/bank errors.
4. Complete host-owner admission and snapshots: FASED/memory, UART, blockdev,
   four TracerV bridges, scheduler/driver and creator-side TSI state. The legacy
   CPU aggregate is disabled; do not remove that denial until a complete,
   atomic prepared publication protocol is validated. Publish both canonical
   checkpoint levels and the real boundary trace only after all transfers pass.
5. Add a distinct, explicit hardware-build opt-in that requires this coverage
   manifest and connected bridge. Regenerate the exact Rocket RTL, constants,
   driver and source hashes. Run bank/freeze/DMA regressions with VCS on EDA
   (SP2, `-full64`, `vcs-env.sh` sourced last), including outstanding traffic,
   backpressure, corrupt/truncated frames and first-edge rejection tests.
6. Start the generated `buildbitstream` argv on this manager after those
   implementation dependencies pass. Retain native results-build logs and
   local job/work-directory inventory. Record synth/P&R resources and timing,
   S3 DCP receipt, AFI/AGFI and availability. No EC2 build farm or EDA Vivado.
   Preserve failed and in-progress build/AFI IDs across turns.
7. Prepare a new hardware runtime with that private HWDB entry. Capture from
   active F2 execution, continue the FPGA reference, collect results, then
   validate fresh EDA metasim/clean-RTL restoration and sustained live shadow.

Build admission remains incomplete at steps 1–5. An uninstrumented custom
Rocket build must not be relabeled a checkpoint image or deployed for capture.
Local Vivado and HDK environment checks have run; no checkpoint-enabled
synthesis/P&R/AFI build is claimed by configuration preparation.

The first implementation increment is `CheckpointCaptureCut.sv`, currently
unconnected to the CPU recipe. Sixteen-owner native Vivado synthesis on this
server for the actual F2 part passes; source hash, DCP and reports are in
`local-build-receipt.json` and `cut-vivado/`. The behavioral testbench covers
accepting-edge freeze, delayed acknowledgements, capture/publication stalls,
missing/faulting owners, lost freeze, target-cycle drift, premature release,
explicit abort and recovery. Fresh iteration-176 EDA VCS SP2 compilation and
simulation pass all **82** checks, with native logs in `cut-vcs/`. The site
license setup `/tools/flexlm/flexlm.sh` is loaded by `vcs-env.sh` when needed;
the original iteration-175 missing-license failure remains unchanged.
Build admission still requires the complete network and owner integration.
Iteration 176 also repeats native localhost synthesis: **56 LUTs / 74 registers**
for the same 16-owner F2-device component. The new DCP, Tcl and reports are in
`iteration176/cut-vivado/`; `iteration176/summary.json` binds source snapshots,
build artifacts and EDA logs. No full-image build or AFI request has started.
