# Current instructions: CPU checkpoint and live RTL acceptance (October 22, 2026)

The current user priority is working Level-1 and Level-2 checkpoint/restore
on the existing Rocket, BOOM, and Shuttle + Saturn FireSim targets below.
The endpoint is conventional VCS simulation of the original, untransformed
pre-FAME RTL, guided cycle by cycle by a concurrently running,
checkpoint-restored FireSim metasimulation. Both simulations must restore at
the same logical target cut; the metasim remains the environment authority.
Standalone finite trace replay remains a separate supported debugging mode.

ASIC synthesis, RTL-to-standard-cell state matching, gate-level replay,
switching-activity generation for power analysis, and ASIC power estimation
are outside this plan. Jasper, Formality, Conformal, Genus, Joules, Voltus,
standard-cell libraries and ASIC netlists are not required dependencies for
checkpoint/debug acceptance. Startup and verification for this scope must
not require those tools, licenses or their resource-limit services.
Physical FPGA validation remains future work. Preserve the existing FCFS
and historical formal/gate evidence without rerunning it as an acceptance
prerequisite. These instructions take precedence over older loop prompts,
milestone definitions and verification lists that still require the removed
ASIC work; align such runtime requirements with this scope when encountered.

Use `sims/firesim-staging/sample_config_build_recipes.yaml` as the source of
build settings. Start with these existing F2 recipes, in this order:

| Family | Recipe | TARGET_CONFIG |
| --- | --- | --- |
| Rocket | `firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3` | `WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig` |
| BOOM | `firesim_boom_singlecore_no_nic_l2_llc4mb_ddr3` | `WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.LargeBoomV3Config` |
| Shuttle + Saturn | `firesim_saturn_GENV256D128_shuttle_singlecore_no_nic_l2_llc4mb_ddr3` | `FireSimGENV256D128ShuttleConfig` |

Use each recipe's exact PLATFORM, TARGET_PROJECT, TARGET_PROJECT_MAKEFRAG,
DESIGN, TARGET_CONFIG and PLATFORM_CONFIG in VCS metasim builds. Run through
the metasim path without FPGA bitstream builds. Standalone Shuttle is excluded:
the user explicitly said not to add a recipe when none exists. NIC, MegaBOOM,
RAM-optimized, other-platform and other accelerator variants are later expansion,
not substitutes for or prerequisites of this initial three-recipe matrix.

Complete both levels for each recipe before advancing to the next family:

1. Level 1: inventory every generated simulator, FAME/token/channel, memory,
   bridge and host-driver state owner for the actual CPU configuration. Add
   missing adapters, preserving complete ownership and atomic cut validation.
   Checkpoint during real CPU execution, terminate the source process, and
   restore into a fresh VCS metasim process before any target edge. Compare
   target-visible behavior and transaction timing with an uninterrupted run.
2. Level 2: inventory the complete original pre-FAME DUT, including CPU,
   cache/uncore and memory state inside the selected boundary. For Saturn,
   include vector registers and in-flight vector execution/memory state.
   Capture an independent .rtlckpt and actual boundary .trace; restore and
   read back every semantic word in fresh ordinary RTL VCS before its first
   edge, then replay the captured inputs and compare every output per cycle.
   Select a complete, explicit boundary; a CPU architectural register dump
   or partial tile inventory cannot satisfy semantic checkpoint acceptance.
3. Live RTL shadow: restore a paired .fsckpt and .rtlckpt into separate fresh
   VCS metasim and untransformed RTL processes at the same logical target cut.
   Independently read back both complete states before target advancement.
   Keep restored metasim running as the authority for FASED and the environment;
   forward its actual target-boundary inputs to clean RTL, compare every output
   at the corresponding settled observation point, then acknowledge/advance
   the matching edge. Exercise ready/valid backpressure and outstanding traffic.
   Demonstrate sustained continuation beyond any prerecorded trace window,
   full-visibility clean RTL waveforms, healthy completion and first-divergence
   detection for deliberate semantic corruption. Independent finite replay
   alone does not establish this live mode.
4. Exercise reset/early execution, warmed caches, outstanding memory traffic,
   and late execution cuts. Run self-checking bare-metal CPU workloads first;
   Rocket must exercise all four cores, BOOM speculative/in-flight execution,
   and Shuttle + Saturn actual vector computation plus vector loads/stores
   while vector work is in flight. Record workload bytes/hash and pass status.
   Boot-only, idle-only and scalar-only Saturn runs are insufficient.
5. At every tested cut, independently audit complete state readback and cycle
   labels. Exercise corrupt/truncated images, incompatible builds, missing
   state owners and deliberate post-restore semantic corruption. Fail before
   partial restore for invalid images and report the first divergent signal
   and target cycle for execution faults; never acknowledge a divergent edge.
6. Extend common checkpoint infrastructure where needed. Do not reuse the
   fcfs-fased-v1 driver whitelist for CPUs without auditing their actual owners.
   Handle clocks, memory pipelines and external state explicitly. Unsupported
   features remain reported as incomplete work, not silently omitted state.
7. Retain FCFS and small-fixture regressions. Save exact build/runtime settings,
   workload and source hashes, checkpoint/trace paths, tested cuts, state totals,
   comparisons, negative cases and runnable VCS commands per recipe under
   automations/checkpoint_loop/runs/. Maintain pending/in_progress/verified
   results per recipe and level in docs/checkpointing/cpu-checkpoint-matrix.md.
   Mark a recipe verified only after its own complete Level-1, Level-2 finite
   replay and restored-metasim-guided live RTL tests and independent audits pass.
   Existing fuzzer acceptance cannot establish CPU support. Do not claim
   untested configurations as supported.

For this stage, complete checkpoint restore and sustained metasim-guided
untransformed RTL execution in VCS are the exit criterion. Keep future hardware
capture interfaces synthesizable, but do not delay CPU checkpoint acceptance
for physical FPGA validation or optimization of the DMA path. Preserve the
loop's previously verified M0-M10 history and
resume from its saved state without resetting milestone or iteration counters.
Historical formal/gate milestones remain evidence of past work, not continuing
requirements or dependencies for the current CPU checkpoint milestones.
Implementation agents must continue treating both plan files as read-only;
this priority section is a user-directed instruction update.

---

# New: Additional Resources:
https://github.com/ucb-bar/midas-top-release - MIDAS paper release repo
https://github.com/ucb-bar/midas-examples - MIDAS examples

These historical MIDAS artifacts are references for checkpointing and RTL
replay mechanisms where applicable to the current FireSim implementation.

# Implementation Plan: Two-Level Checkpointing for Modern FireSim

## 1. Project Objective

Implement a two-level checkpointing and replay framework for modern FireSim that supports full simulator migration, RTL debugging, deterministic replay, and live untransformed RTL simulation guided by restored FireSim metasimulation.

The implementation must support:

1. **Level 1 — Full FireSim simulator checkpointing:** Capture the complete state of the Golden Gate-generated FPGA simulator and restore it into FireSim metasimulation using VCS as its simulation backend.

2. **Level 2 — Semantic DUT checkpointing:** Capture the logical microarchitectural state of the original DUT before FireSim's FAME transformations. Restore that state into a conventional VCS simulation of the original RTL.

3. **Rolling checkpointing:** Maintain periodic checkpoints so that debugging can rewind to a point before a failure without rerunning the entire workload.

4. **DESSERT-style debugging:** Restore original RTL state and replay recorded target I/O traces over a finite region of interest, generating full-visibility RTL waveforms.

5. **Live clean-RTL cosimulation:** Restore Level-1 state into FireSim metasimulation and matching Level-2 state into conventional VCS simulation of the original RTL. Keep metasim running as the authoritative environment, guide clean RTL with its live target-boundary inputs, compare outputs cycle by cycle, and generate full-visibility RTL debug waveforms.

The two checkpoint levels must operate independently or together.

---

## 2. Terminology and Simulation Boundaries

Use the following terminology consistently throughout the source code, documentation, tests, and APIs.

### 2.1 FireSim FPGA Simulation

The Golden Gate-generated simulator executing on physical FPGA hardware.

This includes:

- The FAME-transformed DUT
- Golden Gate-generated simulator logic
- LI-BDN channels and token FIFOs
- FASED and other simulator models
- Bridge hardware and host software
- Functional target memory

The original DUT has already undergone FireSim transformations.

### 2.2 FireSim Metasimulation (VCS Backend)

Software RTL simulation of the **Golden Gate-generated FPGA simulator**, using VCS as the simulation backend.

Conceptually:

```text
                 FireSim Metasimulation
                       (VCS)
        +----------------------------------+
        | Golden Gate-generated simulator |
        |                                  |
        |  FAME-transformed DUT            |
        |  LI-BDN channels                 |
        |  FASED timing models             |
        |  BridgeModules                   |
        |  Simulator control logic         |
        |                                  |
        +----------------------------------+
                        |
                FireSim host driver
```

FireSim metasimulation is not conventional RTL simulation of the original DUT.

The purpose of Level 1 is to move execution from the physical FPGA into this equivalent software-hosted simulator.

### 2.3 Clean RTL Simulation (VCS)

Conventional VCS simulation of the original DUT RTL **before FireSim/FAME transformations**.

```text
                  Clean RTL VCS
        +----------------------------------+
        |                                  |
        | Original Rocket / BOOM / DUT RTL |
        |                                  |
        | ROB                              |
        | Rename tables                    |
        | Caches                           |
        | LSQ                              |
        | Pipeline registers               |
        | etc.                             |
        |                                  |
        +----------------------------------+
```

It does not contain the FAME-transformed DUT, Golden Gate token FIFOs, or FireSim simulator instrumentation.

It may obtain target inputs from either:

- A recorded boundary I/O trace
- A concurrently running FireSim metasimulation

### 2.4 Complete Architecture

```text
                         FireSim FPGA
                              |
                    Checkpoint System
                              |
               +--------------+--------------+
               |                             |
            Level 1                       Level 2
       Simulator Checkpoint          Semantic DUT Checkpoint
               |                             |
            .fsckpt                       .rtlckpt
               |                             |
               v                             v
     FireSim Metasimulation          Clean RTL Simulation
         (VCS backend)                    (VCS)
               |                             |
       FAME-transformed DUT           Original pre-FAME DUT
       FASED / bridges                Original RTL hierarchy
       LI-BDN channels                      |
               |                             |
               +--------- cosimulation ------+
               |                             |
       Arbitrary continuation          Debug waveforms
```

The essential separation is:

**FireSim metasimulation reproduces the transformed FPGA simulator. Clean RTL simulation reproduces the original target RTL.**

---

## 3. Core Checkpoint Requirements

### 3.1 Level 1 — Full Simulator Checkpoint

A Level-1 checkpoint captures sufficient state to resume the Golden Gate-generated simulator inside FireSim metasimulation.

The checkpoint must include:

- FAME-transformed DUT state
- Golden Gate-generated model state
- LI-BDN channels and token FIFOs
- FASED timing-model state
- BridgeModule state
- Functional target main-memory contents
- Target-cycle counters and relevant clock phases
- Relevant host-side driver/device state
- Outstanding transactions and other execution-relevant state

The goal is:

```text
FireSim FPGA:
C ------------------------------------> C+N
     |
     | Level-1 checkpoint
     v
FireSim Metasimulation (VCS backend):
C ------------------------------------> C+N
```

The target-visible executions must agree at every corresponding target cycle.

Physical host-clock and PCIe timing are not required to match.

The Level-1 checkpoint must represent a complete, consistent simulator state, not merely the registers of the FAME-transformed DUT.

### 3.2 Level 2 — Semantic DUT Checkpoint

A Level-2 checkpoint captures the state of the original DUT before FireSim/FAME transformations.

This includes all required microarchitectural sequential state:

- ROB
- Rename tables
- Physical register files
- Pipeline registers
- LSQ
- Cache data and metadata
- MSHRs
- TLBs
- Branch predictors
- FSMs
- Other sequential state and memories

It must exclude Golden Gate-only simulator state.

Assign stable semantic StateIDs to individual original RTL state elements.

### 3.3 Accuracy Contracts

**Level 1:**

Restored FireSim metasimulation must reproduce the same target-visible execution as uninterrupted FireSim execution.

**Level 2, finite trace replay:**

Clean RTL simulation must reproduce the same target-cycle behavior over the recorded trace window.

**Level 2, live cosimulation:**

Clean RTL simulation must stay synchronized with the FAME-transformed DUT executing inside FireSim metasimulation.

---

## 4. Phase 0 — Repository Reconnaissance

Before implementation, inspect the actual modern FireSim/Chipyard repository.

Do not assume historical compiler APIs or source locations are still valid.

### Tasks

1. Identify the FireSim and Chipyard revisions.
2. Locate Golden Gate's compiler entry points.
3. Inspect the FAME transformation passes.
4. Identify register and memory optimization passes.
5. Locate LI-BDN channel generation.
6. Identify BridgeModule insertion and extraction.
7. Inspect FASED and its functional memory backing store.
8. Inspect FireSim host drivers and DMA/MMIO interfaces.
9. Locate the FireSim metasimulation build and execution flow using VCS.
10. Identify the generated simulator hierarchy used by FireSim metasimulation.
11. Locate existing test infrastructure for Golden Gate and FireSim metasimulation.
12. Identify the VCS runtime, checkpoint loaders, waveform support, and target-cycle transport needed for restored-metasim-guided clean RTL execution.

Likely areas to inspect, after confirming the current repository layout:

```text
sim/midas/src/main/scala/midas/
sim/midas/src/main/scala/midas/passes/
sim/midas/src/main/scala/midas/widgets/
sim/midas/src/main/scala/midas/models/dram/
sim/src/main/cc/
sim/src/test/scala/
```

### Deliverable

Create:

```text
docs/checkpointing/reconnaissance.md
```

Document:

- Exact compiler insertion points
- Current pass ordering
- Original RTL versus transformed simulator hierarchy
- State extraction opportunities
- Available DMA interfaces
- FASED and bridge-driver state requirements
- FireSim metasimulation build/test commands
- VCS compile/runtime license availability and live cosimulation dependencies

**Acceptance:** The agent can trace an original DUT state element through FAME transformations to its implementation in the generated FPGA simulator, and can identify the full simulator state required for Level 1.

---

## 5. Phase 1 — Checkpoint Format and Shared Infrastructure

Implement common checkpoint metadata, serialization, and validation.

### Checkpoint formats

```text
.fsckpt    Full Golden Gate-generated simulator checkpoint
.rtlckpt   Original pre-FAME DUT semantic checkpoint
.trace     Recorded target-boundary input/output trace
```

Example:

```text
checkpoint/
    manifest.json
    simulator.fsckpt
    dut.rtlckpt
    boundary.trace
```

Not all checkpoint workflows require all files.

### Metadata

Store:

```text
format_version
checkpoint_type
target_cycle
target_clock_phase
target_configuration
rtl_build_hash
golden_gate_build_hash
simulator_build_hash
state_manifest_hash
checkpoint_size
checksum
```

### Semantic StateIDs

For Level 2, describe original pre-FAME RTL state using stable identifiers.

Example:

```text
StateID:       0x000142
Hierarchy:     BoomCore.rob.head
Kind:          register
Width:         7
Clock Domain:  core_clock
```

For memories, also record depth, word width, address indexing, and bit ordering.

Use deterministic serialization.

Reject corrupted or incompatible checkpoints.

### Acceptance

Checkpoint files round-trip bit-exactly and reject incompatible or corrupted data before restoration.

---

## 6. Phase 2 — Pre-FAME Semantic State Discovery

Implement a Golden Gate compiler pass that identifies the original DUT's state before FAME transformations.

### Responsibilities

1. Traverse the original DUT hierarchy.
2. Identify every sequential element.
3. Assign stable semantic StateIDs.
4. Record widths, depths, clock domains, and original hierarchy.
5. Generate a semantic state manifest.
6. Preserve the mapping through subsequent FireSim transformations where possible.
7. Generate or retain the checkpoint instrumentation needed to access the logical values.

Example:

```text
StateID 0x00100 -> rob_head
StateID 0x00101 -> rob_tail
StateID 0x00200 -> rename_table[0]
StateID 0x00201 -> rename_table[1]
StateID 0x01000 -> dcache.tags
```

### Memory handling

Do not indiscriminately add extra RAM read ports.

Investigate address-iterated checkpoint extraction compatible with Golden Gate memory optimization and FPGA memory inference.

The checkpoint must represent original logical memory contents regardless of how Golden Gate implements them.

Unsupported memory representations must produce explicit errors.

### Acceptance

Generate a complete semantic state manifest for a small DUT containing registers, an FSM, register arrays, and SRAM.

---

## 7. Phase 3 — Level-2 Checkpoint/Replay Prototype

Implement the semantic checkpoint proof of concept using FireSim metasimulation with VCS as its backend.

Initially use VCS backdoor access as an oracle, before implementing synthesizable hardware extraction.

### Workflow

```text
Original DUT RTL
       |
Golden Gate / FAME
       |
       v
FireSim Metasimulation
    (VCS backend)
       |
run to target cycle C
       |
capture pre-FAME semantic state
       |
record target I/O [C,C+N)
       |
       v
.rtlckpt + .trace
       |
       v
Clean RTL Simulation (VCS)
       |
restore original DUT state
replay recorded inputs
compare recorded outputs
       |
       v
RTL waveform
```

### Tasks

- Implement semantic-state extraction from FireSim metasimulation.
- Serialize it using the StateID manifest.
- Implement a VPI/DPI loader for clean RTL simulation.
- Restore registers and memories before normal DUT clock advancement.
- Record all DUT boundary signals on corresponding target cycles.
- Replay recorded inputs into the original pre-FAME RTL.
- Compare clean RTL outputs with the reference FireSim outputs.
- Generate waveforms.

### Required tests

Checkpoint while:

- The processor pipeline is active.
- Memory transactions are outstanding.
- Responses are pending.
- An interface is stalled.
- Internal queues are nonempty.

The DUT must not need to become idle.

**Acceptance:** A fresh conventional VCS simulation of the original RTL reproduces the target behavior captured by FireSim metasimulation over a finite window.

---

## 8. Phase 4 — Synthesizable Banked State-Access Network

Replace Level-2 backdoor extraction with FPGA-compatible state readout hardware.

### Architecture

```text
Original target state
         |
+--------+--------+--------+
|                 |        |
Register bank     RAM      Other banks
|                 |        |
+--------+--------+--------+
         |
    State Arbiter
         |
      Wide FIFO
         |
   CheckpointBridge
         |
        DMA
         |
        Host
```

### Requirements

- Bank state elements into manageable groups.
- Support register readout and logical memory iteration.
- Serialize state deterministically.
- Maintain target-cycle checkpoint consistency.
- Use checkpoint-control signals separate from functional target behavior.
- Support FIFO backpressure and error reporting.
- Use FireSim DMA for host transfer.

For clean RTL VCS restoration, continue using the direct VPI/DPI state loader rather than the FPGA readout network.

For initial hardware capture, pause relevant target-state updates until state extraction finishes.

### Acceptance

Hardware-style semantic extraction in FireSim metasimulation produces the same checkpoint as the VCS backdoor oracle.

---

## 9. Phase 5 — Level-1 Full FireSim Simulator Checkpointing

Implement checkpointing of the entire Golden Gate-generated simulator.

This is distinct from Level 2.

### State inventory

Capture all necessary state belonging to:

```text
Golden Gate-generated FPGA simulator
|
+-- FAME-transformed DUT
+-- LI-BDN channels and FIFOs
+-- FASED timing models
+-- other generated simulator models
+-- BridgeModules
+-- simulation control and counters
+-- functional target memory
+-- relevant host-driver state
```

### Consistency requirements

Implement a checkpoint controller with stages such as:

```text
RUNNING
   |
CHECKPOINT_REQUESTED
   |
REACH_CONSISTENT_CUT
   |
FREEZE
   |
CAPTURE_SIMULATOR_STATE
   |
CAPTURE_MEMORY_AND_DRIVER_STATE
   |
VALIDATE
   |
RESUME
```

Merely reaching a target-cycle count is not sufficient to guarantee a consistent checkpoint.

The implementation must account for partially processed tokens, model progress, memory updates, bridge state, and relevant host transactions.

Outstanding target memory requests do not need to finish; their state must be preserved.

### Functional memory

Snapshot both FASED timing state and the functional contents of target memory.

Begin with full memory snapshots.

Incremental snapshots and dirty-page tracking can be added later.

### Host driver state

Provide checkpoint save/load hooks for relevant FireSim drivers.

Unsupported stateful drivers must be identified, not silently omitted.

### Restoration

Load `.fsckpt` into a fresh **FireSim metasimulation instance using the VCS backend**, built from the compatible Golden Gate-generated simulator.

Restore all necessary simulator, memory, model, and driver state before allowing simulation to resume.

### Acceptance

Compare:

```text
Reference:
FireSim Metasimulation (VCS backend)
C -------------------------------------> C+N

Checkpointed:
FireSim Metasimulation (VCS backend)
C --> checkpoint --> exit process
                         |
                         v
                fresh FireSim Metasimulation
                      (VCS backend)
                         |
                      restore
                         |
                         v
                        C+N
```

Require identical target-visible behavior, including transaction ordering and target-cycle response timing.

---

## 10. Phase 6 — FPGA-Compatible DMA Checkpoint Transport

Implement the transport that will eventually extract checkpoints from physical FPGA hardware.

### Components

**CheckpointBridge hardware**

- MMIO control registers
- Checkpoint request/status
- Banked state-stream interface
- Wide FIFO
- DMA-compatible streaming output
- Error reporting

**Host driver**

- Request checkpoint
- Wait for consistent capture
- Transfer serialized state
- Snapshot associated memory and software state
- Verify checksum
- Commit checkpoint

Level 1 and Level 2 may share the transport implementation but must maintain independent state manifests and correctness guarantees.

### Acceptance

The same canonical checkpoint representation can be produced through the FPGA-compatible hardware stream in FireSim metasimulation.

No physical FPGA is required to validate this stage.

---

## 11. Phase 7 — Rolling Checkpointing

Maintain a bounded history of checkpoint states.

### Configuration

```text
checkpoint_interval_target_cycles
checkpoint_retention_count
checkpoint_directory
checkpoint_level
```

Example:

```text
interval = 100000 target cycles
retention = 32 checkpoints
```

### Timeline

```text
Target time ---------------------------------------->

       S0       S1       S2       S3       S4
       |--------|--------|--------|--------|

       Retained:
                S1 S2 S3 S4

       After new S5:
                   S2 S3 S4 S5
```

Only delete an older checkpoint after its replacement has been fully written, validated, and committed.

### Deadlock support

Detect both:

- Target-level failures, including lack of instruction retirement.
- FireSim simulator progress stalls, where target cycles stop advancing.

The second case requires a host-progress watchdog independent of the target-cycle counter.

When a failure occurs, select a checkpoint before the suspected causal error and restore it into FireSim metasimulation.

### Acceptance

Restore an earlier checkpoint and reproduce an injected target deadlock or simulator-progress stall.

---

## 12. Phase 8 — Live Clean-RTL Cosimulation

Run two distinct simulations in sync:

1. FireSim metasimulation with the VCS backend, containing the Golden Gate-generated simulator and FAME-transformed DUT.
2. Conventional VCS simulation of the original, pre-FAME DUT RTL.

### Architecture

```text
            FireSim Metasimulation
                 (VCS backend)
       +-----------------------------+
       |                             |
       | FAME-transformed DUT        |
       | FASED                       |
       | LI-BDN                      |
       | Other BridgeModules         |
       |                             |
       +--------------+--------------+
                      |
              Target-cycle inputs
                      |
                      v
        +---------------------------+
        | Clean RTL Simulation      |
        | (conventional VCS)        |
        |                           |
        | Original pre-FAME DUT     |
        |                           |
        +-------------+-------------+
                      |
                 DUT outputs
                      |
                      v
             Cycle-by-cycle compare
             with transformed DUT
```

### Startup

Both executions must begin at the same logical target cycle.

Restore:

```text
.fsckpt -> FireSim metasimulation (VCS backend)

.rtlckpt -> conventional clean RTL VCS
```

The semantic state represented inside the transformed DUT must match the clean RTL's restored state.

### Execution protocol

For every target cycle:

1. Advance the authoritative FireSim metasimulation to the appropriate target-cycle observation boundary.
2. Extract the target-visible inputs consumed by its FAME-transformed DUT.
3. Supply equivalent inputs to the original clean RTL simulation.
4. Settle the clean RTL at the corresponding observation boundary and compare every output against the FAME-transformed DUT before acknowledging that edge.
5. On a match, advance the corresponding target clock event and acknowledge it to the synchronization adapter.
6. Optionally compare the semantic state represented by both DUTs.
7. On a mismatch, report the first divergent signal and original target-cycle label, then stop without acknowledging the divergent edge.

The synchronization adapter must handle target-cycle timing, ready/valid signaling, and relevant combinational boundary dependencies correctly.

### Authority

Initially:

```text
FAME-transformed DUT -> FASED and FireSim environment

Clean original RTL -> output comparator only
```

The original clean RTL does not drive FASED directly in this mode.

Do not implement authoritative ownership handoff for v1.

### Arbitrary continuation

FireSim metasimulation continues generating target-visible environment behavior.

Consequently, the clean RTL shadow is not limited by a prerecorded trace length.

The two executions can continue for an arbitrary number of target cycles, subject to their actual progress and the determinism/completeness of the environment.

### Acceptance

Start both simulations in fresh processes from matching Level-1 and Level-2
checkpoints, with independent complete state readback before the first target
edge. Demonstrate sustained cycle-exact cosimulation with matching boundary
outputs, active workload and outstanding memory traffic, and healthy completion
of both processes. Restored metasim must supply live environment inputs beyond
any prerecorded trace window. Retain full-visibility clean RTL debug waveforms.

Inject an intentional RTL-state mismatch and verify that the checker reports
the first divergent signal and target cycle before acknowledging that edge.
Run this acceptance for each supported CPU recipe after its individual
checkpoint/replay acceptance. This live restored pair is the project endpoint.

---

## 13. Phase 9 — DESSERT-Style Debugging

Implement standalone finite replay of the original RTL.

### Capture

Either FireSim FPGA execution or FireSim metasimulation may generate the checkpoint and trace.

```text
FireSim FPGA / FireSim Metasimulation
               |
               +-- semantic DUT checkpoint @ C
               |
               +-- DUT I/O trace [C,C+N)
               |
               v
        .rtlckpt + .trace
```

### Replay

```text
.rtlckpt + .trace
         |
         v
Clean RTL Simulation
 (conventional VCS)
         |
restore original DUT
replay recorded inputs
compare outputs
         |
         v
Full RTL waveform
```

No FireSim metasimulation needs to remain running during finite trace replay.

The trace substitutes for FASED and other external simulation models over the recorded interval.

Support traces recorded from both physical FPGA and FireSim metasimulation.

### Acceptance

Reproduce a known RTL bug using only the semantic checkpoint, recorded trace, and conventional clean RTL VCS simulation.

---

## 14. Future Work — Physical FPGA Validation

Physical FPGA validation is deferred and is not a prerequisite for completing this plan. A future hardware effort may validate the checkpoint/debug flow on a supported FPGA platform.

### Tasks

1. Synthesize the checkpoint-enabled Golden Gate-generated simulator.
2. Validate banked state access.
3. Validate CheckpointBridge MMIO.
4. Validate DMA checkpoint transfers.
5. Capture Level-1 checkpoints from FPGA execution.
6. Restore them into FireSim metasimulation using VCS.
7. Capture Level-2 checkpoints from FPGA execution.
8. Restore them into conventional clean RTL VCS.
9. Run clean RTL VCS guided by the restored FireSim metasimulation and compare target-cycle behavior.

### Measurements

Record:

```text
LUT utilization
FF utilization
BRAM/URAM utilization
Fmax
checkpoint-enabled throughput
snapshot size
snapshot capture latency
DMA transfer time
restore latency
```

Separate state capture overhead from host transfer overhead.

---

## 15. Implementation Milestones

The design milestone labels below retain their historical numbering; the
removed ASIC milestones are no longer part of this plan. These labels are
separate from the controller's saved milestone indices. Preserve controller
history and saved progress when applying the current CPU acceptance above.

### M0 — Repository reconnaissance

Identify compiler entry points, current VCS simulation flows, live cosimulation interfaces, and checkpoint state boundaries.

### M1 — Level-2 semantic state infrastructure

Implement pre-FAME state discovery, StateIDs, manifests, and serialization.

### M2 — Level-2 checkpoint/replay prototype

Capture semantic state and boundary traces from FireSim metasimulation using VCS, then restore into conventional VCS simulation of clean RTL.

**Exit:** Exact finite target-cycle replay.

### M3 — Synthesizable checkpoint hardware

Implement the banked checkpoint readout network.

**Exit:** Hardware-style extraction matches the simulator backdoor oracle.

### M4 — Level-1 simulator checkpointing

Capture and restore complete Golden Gate-generated simulator state between separate FireSim metasimulation runs.

**Exit:** Restored execution matches uninterrupted execution at the target-cycle level.

### M5 — DMA transport

Implement FPGA-compatible CheckpointBridge streaming and host transfer.

**Exit:** Both checkpoint levels produce their intended formats through the hardware-style transport path.

### M6 — Rolling checkpoints

Implement checkpoint scheduling, retention, and recovery.

**Exit:** Rewind and reproduce an injected deadlock.

### M7 — Live clean-RTL cosimulation

Run conventional clean RTL VCS alongside a checkpoint-restored FireSim metasimulation.

**Exit:** Both fresh processes restore at the same cut with complete zero-edge state readback; restored metasim guides clean RTL cycle by cycle beyond the recorded trace window, produces RTL debug waveforms, completes healthy execution and detects deliberate corruption at its first divergent boundary.

### M8 — DESSERT workflow

Implement standalone finite replay with clean RTL waveforms.

**Exit:** Reproduce a known bug without requiring live FireSim metasimulation.

### M11 — Physical FPGA validation (future work)

Outside current completion criteria: validate extraction, DMA, and restoration using actual FPGA hardware in a future hardware effort.

**Exit:** FPGA-produced checkpoints restore successfully into the correct software simulation environments.

---

## 16. Engineering Requirements

1. Always distinguish **FireSim metasimulation** from conventional RTL simulation.

2. Use “FireSim metasimulation (VCS backend)” when referring to software simulation of the Golden Gate-generated FPGA simulator.

3. Use “clean RTL simulation (VCS)” when referring to conventional simulation of the original pre-FAME RTL.

4. Do not treat FireSim metasimulation as equivalent to an untransformed DUT simulation.

5. Do not confuse FPGA host cycles with simulated target cycles.

6. Keep Level-1 and Level-2 state inventories separate.

7. Implement stable semantic StateIDs before FAME transformations.

8. Do not silently omit sequential state.

9. Do not assume DMA exposes arbitrary register state; synthesize the necessary readout network.

10. Do not assume freezing the DUT alone creates a consistent Level-1 checkpoint.

11. Preserve FASED timing state and functional memory for Level-1 continuation.

12. Use complete target-boundary traces for finite Level-2 replay.

13. Preserve both trace-driven replay and live clean-RTL cosimulation.

14. Keep the FAME-transformed DUT authoritative during initial live cosimulation.

15. Reject incomplete or unverified semantic-to-generated state mappings used for checkpoint capture and clean RTL restoration.

16. Keep checkpointing optional and disabled by default.

17. Implement small testable milestones before Rocket/BOOM integration.

18. Validate restore in fresh simulation processes.

19. Report the first target-cycle mismatch when equivalence checking fails.

---

## 17. Final Success Criteria

The implementation is complete when it can demonstrate:

### Level 1

The entire Golden Gate-generated FireSim simulator can be checkpointed during active VCS metasim execution and restored into a fresh FireSim metasimulation process using VCS, with complete pre-edge state readback and cycle-identical target-visible continuation. Physical FPGA capture is future work.

### Level 2

The original DUT's pre-FAME microarchitectural state can be extracted and restored into a conventional clean RTL VCS simulation.

### Rolling Recovery

Periodic checkpoints allow earlier execution to be reconstructed when a bug or deadlock is detected late.

### DESSERT

A semantic checkpoint and finite trace can reproduce a bug in clean RTL simulation without rerunning the full FireSim simulator.

### Live Cosimulation — Project Endpoint

A fresh conventional VCS simulation of the original, untransformed pre-FAME
RTL restores its Level-2 checkpoint at the same logical target cut as a fresh
Level-1-restored FireSim metasimulation. Both complete state readbacks precede
any target edge. The restored metasim remains running in the background,
authoritatively driving FASED and the environment and supplying live
boundary inputs to clean RTL. Cycle-by-cycle comparison preserves ready/valid
and transaction timing beyond the recorded trace window, supports full RTL
debug waveforms, completes healthy execution, and detects deliberate corruption
at the first divergent signal and target cycle without acknowledging that edge.

All current CPU recipes must satisfy Level 1, independent Level-2 finite replay,
and this live cosimulation acceptance before they are marked verified.

---

## 18. Central Design Principle

**Level 1 captures the complete Golden Gate-generated FPGA simulator and restores it into FireSim metasimulation.**

**Level 2 captures the original pre-FAME DUT state and restores it into conventional, untransformed RTL VCS for debugging, with live environment guidance from checkpoint-restored metasim or independent finite trace replay.**

The two levels can work together through target-cycle-synchronized cosimulation, or independently through checkpoint and trace-driven replay.

The agent should prioritize complete Level-2 replay, Level-1 FireSim metasimulation continuation, and restored-metasim-guided live clean RTL execution before optimizing checkpoint performance or requiring physical FPGA access.
