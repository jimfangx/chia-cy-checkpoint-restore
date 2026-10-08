# Implementation Plan: Two-Level Checkpointing for Modern FireSim

## 1. Project Objective

Implement a two-level checkpointing and replay framework for modern FireSim that supports full simulator migration, RTL debugging, deterministic replay, and ASIC power estimation.

The implementation must support:

1. **Level 1 — Full FireSim simulator checkpointing:** Capture the complete state of the Golden Gate-generated FPGA simulator and restore it into FireSim metasimulation using VCS as its simulation backend.

2. **Level 2 — Semantic DUT checkpointing:** Capture the logical microarchitectural state of the original DUT before FireSim's FAME transformations. Restore that state into a conventional VCS simulation of the original RTL.

3. **Rolling checkpointing:** Maintain periodic checkpoints so that debugging can rewind to a point before a failure without rerunning the entire workload.

4. **DESSERT-style debugging:** Restore original RTL state and replay recorded target I/O traces over a finite region of interest, generating full-visibility RTL waveforms.

5. **Live clean-RTL cosimulation:** Run conventional VCS simulation of the original RTL alongside FireSim metasimulation, keeping them synchronized at the target-cycle level.

6. **Strober-style ASIC power analysis:** Use formal verification to establish correspondence between original RTL sequential state and the synthesized ASIC gate-level netlist, initialize the gate-level simulation, replay the recorded target execution, and generate gate-level switching activity for power estimation.

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

### 2.4 ASIC Gate-Level Simulation (VCS)

Conventional VCS simulation of the synthesized ASIC netlist.

This is a different simulation from both FireSim metasimulation and clean RTL simulation.

It receives checkpoint state through a formally validated correspondence between pre-synthesis RTL state and gate-level sequential state.

Its switching activity is used for ASIC power estimation.

### 2.5 Complete Architecture

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
                                             |
                                      Formal RTL-to-Gate
                                        State Mapping
                                             |
                                             v
                                    ASIC Gate-Level VCS
                                             |
                                      Gate-Level SAIF
                                             |
                                      Joules / Voltus
                                             |
                                         ASIC Power
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

**ASIC gate-level replay:**

The gate-level netlist must reproduce the same target-cycle logical behavior after formally validated state initialization and replay of the recorded target inputs.

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
12. Identify the available ASIC synthesis, formal verification, and gate-level simulation toolchains.

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
- Formal verification tool availability

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
4. Advance the clean RTL through the corresponding target clock event.
5. Compare the clean RTL outputs against those of the FAME-transformed DUT.
6. Optionally compare the semantic state represented by both DUTs.
7. Report the first divergence.

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

Demonstrate sustained cycle-exact cosimulation with matching boundary outputs.

Inject an intentional RTL-state mismatch and verify that the checker reports the divergence.

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

## 14. Phase 10 — Formal RTL-to-Gate State Mapping

Implement formal state correspondence as a dedicated subsystem, following Strober's approach.

This phase connects Level-2 semantic checkpoints to the actual synthesized ASIC netlist.

### Inputs

- Original, pre-FAME DUT RTL
- Corresponding ASIC synthesized netlist
- Level-2 StateID manifest
- Formal verification configuration

### Formal tool

Use Synopsys Formality or Cadence Conformal, depending on available licenses and integrations.

The agent must first determine how the available formal tool exports matching-point information.

### Required procedure

1. Load the original pre-FAME RTL as the reference design.
2. Load the ASIC synthesized netlist as the implementation.
3. Establish consistent clocks, resets, configurations, and assumptions.
4. Run formal equivalence.
5. Extract sequential matching points or proven state relationships.
6. Build a semantic-StateID-to-gate-level-state mapping.
7. Validate that the mapped state is sufficient to initialize the gate-level simulation.

### Mapping file

Generate:

```text
asic_state_map.json
```

Each mapping entry should describe:

```text
semantic StateID
original RTL signal
ASIC gate-level object(s)
bit positions
mapping transformation
formal proof/matching status
```

Support mapping transformations such as:

- Bit reordering
- Inverted register polarity
- Register duplication
- Register merging
- Constant propagation
- Optimized-away state

A successful formal equivalence result does not automatically provide a complete gate-level state initialization map.

Every required gate-level state element must be initialized consistently or shown to be functionally irrelevant/reconstructable.

Unsupported mappings must fail explicitly.

### Retiming

Initially disable retiming in the ASIC synthesis flow used for checkpoint replay.

Later investigate retimed-state reconstruction using formal state relationships or recorded input histories.

### Memories

Support memory initialization through the appropriate ASIC SRAM macro or simulation model interface.

Do not assume all memories remain arrays of individual flip-flops in the ASIC netlist.

### Acceptance

For a small DUT, demonstrate that the formally generated mapping can initialize a gate-level simulation at an intermediate target cycle and reproduce the same trajectory as an uninterrupted reference.

---

## 15. Phase 11 — Strober-Style ASIC Gate-Level Replay and Power

Power analysis must use **actual gate-level simulation activity**, not RTL activity propagated to gates by a power tool.

### Complete workflow

```text
           FireSim FPGA
                OR
       FireSim Metasimulation
            (VCS backend)
                 |
                 v
      Semantic DUT checkpoint
            + I/O trace
                 |
                 v
          Formal State Map
                 |
                 v
       ASIC Gate-Level Simulation
                 (VCS)
                 |
        Restore ASIC state
        Replay target inputs
        Verify target outputs
                 |
                 v
          Gate-Level SAIF
                 |
                 v
           Joules / Voltus
                 |
                 v
             ASIC Power
```

### Checkpoint loading

Implement a VPI/PLI state loader that:

1. Reads the semantic `.rtlckpt`.
2. Loads the validated formal mapping.
3. Computes the corresponding ASIC register values.
4. Initializes gate-level sequential state.
5. Initializes SRAM contents.
6. Applies appropriate clock/reset conditions.
7. Allows combinational logic to settle.
8. Starts gate-level replay at the selected target cycle.

Do not permanently force functional state after initialization.

### Gate-level replay

Drive the exact recorded target-boundary input values into the ASIC netlist.

Compare its cycle-sampled outputs with the recorded reference.

Timing-aware gate-level simulation may produce intra-cycle glitches, but logical behavior at the defined target-cycle observation points must match.

### Switching activity

Generate:

```text
gate_level.saif
```

or gate-level VCD directly from VCS simulating the ASIC netlist.

The SAIF must reflect the actual gate-level simulation.

Do not substitute:

```text
Clean RTL SAIF -> Joules inferred gate activity
```

That path is explicitly excluded.

### Power analysis

Use Joules or Voltus to analyze gate-level activity with the appropriate:

- ASIC technology libraries
- Cell timing and power information
- Operating conditions
- Clock constraints
- ASIC netlist
- Physical/parasitic data when available
- Gate-level SAIF or VCD

Generate reports covering:

- Dynamic power
- Leakage power
- Total power
- Energy per target cycle
- Energy per instruction, where relevant
- Hierarchical power breakdown

### Two supported sample origins

**Direct FPGA sample:**

```text
FireSim FPGA
   |
.rtlckpt + trace
   |
Formal mapping
   |
ASIC Gate-Level VCS
   |
SAIF -> Power
```

**Metasim-generated sample:**

```text
FireSim Metasimulation
      (VCS backend)
          |
   .rtlckpt + trace
          |
     Formal mapping
          |
  ASIC Gate-Level VCS
          |
      SAIF -> Power
```

Both use the same gate-level replay and power flow.

### Acceptance

A semantic checkpoint and recorded trace can initialize the ASIC netlist, reproduce the original target behavior, and generate a valid gate-level power report.

---

## 16. Phase 12 — FPGA Validation

After completing development using FireSim metasimulation, validate on a supported physical FPGA platform.

### Tasks

1. Synthesize the checkpoint-enabled Golden Gate-generated simulator.
2. Validate banked state access.
3. Validate CheckpointBridge MMIO.
4. Validate DMA checkpoint transfers.
5. Capture Level-1 checkpoints from FPGA execution.
6. Restore them into FireSim metasimulation using VCS.
7. Capture Level-2 checkpoints from FPGA execution.
8. Restore them into conventional clean RTL VCS.
9. Replay FPGA-sourced traces against the ASIC gate-level netlist.
10. Generate ASIC power reports.

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

## 17. Implementation Milestones

### M0 — Repository reconnaissance

Identify compiler entry points, current simulation flows, available formal tools, and checkpoint state boundaries.

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

**Exit:** Cycle-exact shadow execution over a long interval.

### M8 — DESSERT workflow

Implement standalone finite replay with clean RTL waveforms.

**Exit:** Reproduce a known bug without requiring live FireSim metasimulation.

### M9 — Formal state correspondence

Match original RTL sequential state against the synthesized ASIC netlist.

**Exit:** Validate gate-level initialization using a formally established state mapping.

### M10 — Strober power flow

Restore the ASIC gate-level netlist, replay recorded target inputs, generate gate-level activity, and estimate ASIC power.

**Exit:** Repeatable gate-level power results using checkpoints sourced from either FPGA or FireSim metasimulation.

### M11 — Physical FPGA validation

Validate extraction, DMA, and restoration using actual FPGA hardware.

**Exit:** FPGA-produced checkpoints restore successfully into the correct software simulation environments.

---

## 18. Engineering Requirements

1. Always distinguish **FireSim metasimulation** from conventional RTL simulation.

2. Use “FireSim metasimulation (VCS backend)” when referring to software simulation of the Golden Gate-generated FPGA simulator.

3. Use “clean RTL simulation (VCS)” when referring to conventional simulation of the original pre-FAME RTL.

4. Use “ASIC gate-level simulation (VCS)” for simulation of the synthesized ASIC netlist.

5. Do not treat FireSim metasimulation as equivalent to an untransformed DUT simulation.

6. Do not confuse FPGA host cycles with simulated target cycles.

7. Keep Level-1 and Level-2 state inventories separate.

8. Implement stable semantic StateIDs before FAME transformations.

9. Do not silently omit sequential state.

10. Do not assume DMA exposes arbitrary register state; synthesize the necessary readout network.

11. Do not assume freezing the DUT alone creates a consistent Level-1 checkpoint.

12. Preserve FASED timing state and functional memory for Level-1 continuation.

13. Use complete target-boundary traces for finite Level-2 replay.

14. Preserve both trace-driven replay and live clean-RTL cosimulation.

15. Keep the FAME-transformed DUT authoritative during initial live cosimulation.

16. Do not use transformed FireSim simulator activity for ASIC power.

17. Use formal verification to establish RTL-to-gate sequential state correspondence.

18. Generate ASIC switching activity through actual gate-level simulation.

19. Do not ask Joules or another power tool to infer gate-level activity from RTL activity.

20. Initially disable ASIC retiming to simplify gate-level state restoration.

21. Reject incomplete or unverified state mappings.

22. Keep checkpointing optional and disabled by default.

23. Implement small testable milestones before Rocket/BOOM integration.

24. Validate restore in fresh simulation processes.

25. Report the first target-cycle mismatch when equivalence checking fails.

---

## 19. Final Success Criteria

The implementation is complete when it can demonstrate:

### Level 1

The entire Golden Gate-generated FireSim simulator can be checkpointed during FPGA execution and restored into FireSim metasimulation using VCS, with cycle-identical target-visible continuation.

### Level 2

The original DUT's pre-FAME microarchitectural state can be extracted and restored into a conventional clean RTL VCS simulation.

### Rolling Recovery

Periodic checkpoints allow earlier execution to be reconstructed when a bug or deadlock is detected late.

### DESSERT

A semantic checkpoint and finite trace can reproduce a bug in clean RTL simulation without rerunning the full FireSim simulator.

### Live Cosimulation

A conventional VCS simulation of the original RTL can run in synchronization with FireSim metasimulation, receiving the same target-visible inputs and producing matching outputs.

### Strober

A semantic checkpoint can be translated using formally verified RTL-to-gate state correspondence, loaded into the synthesized ASIC netlist, and replayed with the recorded target I/O.

### ASIC Power

Gate-level VCS produces actual gate-level switching activity, which Joules or Voltus uses to calculate ASIC power.

No inferred RTL-to-gate activity propagation is used.

---

## 20. Central Design Principle

**Level 1 captures the complete Golden Gate-generated FPGA simulator and restores it into FireSim metasimulation.**

**Level 2 captures the original pre-FAME DUT state and restores it into conventional clean RTL simulation for debugging or formally mapped ASIC gate-level replay for power analysis.**

The two levels can work together through target-cycle-synchronized cosimulation, or independently through checkpoint and trace-driven replay.

The agent should prioritize complete, provably correct Level-2 replay and Level-1 FireSim metasimulation continuation before optimizing checkpoint performance or requiring physical FPGA access.