# Implementation Plan: Two-Level Checkpointing for Modern FireSim

## 1. Objective

Implement a two-level checkpointing and replay infrastructure in modern FireSim that supports:

1. **Level 1 — Full FireSim simulator checkpointing:** Capture the complete FAME/Golden Gate-transformed simulator state from an FPGA using a banked state-access network and DMA. Restore the checkpoint into VCS metasimulation and continue execution for an arbitrary number of target cycles.

2. **Level 2 — Semantic DUT checkpointing:** Capture the original DUT's logical microarchitectural state before FAME transformations. Restore this state into untransformed RTL for debugging, deterministic replay, and ASIC power estimation.

3. **Rolling checkpointing:** Periodically preserve checkpoints so that late-detected bugs, including deadlocks, can be investigated without repeating the entire workload.

4. **DESSERT-style debugging:** Restore semantic RTL state and replay recorded input/output traces over a finite region of interest, producing full-visibility RTL waveforms.

5. **Live clean-RTL cosimulation:** Run the original untransformed RTL in sync with a Level-1-restored FireSim metasimulator, maintaining target-cycle accuracy while generating clean RTL waveforms.

6. **Strober-style ASIC power analysis:** Formally match pre-synthesis RTL sequential state to the synthesized ASIC gate-level netlist, load the appropriate state into gate-level VCS, replay the recorded target inputs, and generate actual gate-level switching activity for power estimation.

The two checkpoint levels must be usable independently or together.

### System Architecture

```text
                         FireSim FPGA
                              |
                  Checkpoint Controller
                              |
                +-------------+-------------+
                |                           |
             LEVEL 1                     LEVEL 2
          Full Simulator              Semantic DUT
           Checkpoint                 Checkpoint
                |                           |
             .fsckpt                    .rtlckpt
                |                           |
                v                           |
           VCS Metasim                      |
                |                           |
       Exact continuation                   |
                |                           |
                +----------+----------------+
                           |
                    Clean RTL VCS
                           |
                  +--------+--------+
                  |                 |
               Debugging       ASIC State
               Waveforms        Mapping
                                    |
                              Formal Tool
                                    |
                              ASIC Gate-Level
                                  VCS
                                    |
                              Gate-Level SAIF
                                    |
                              Joules / Voltus
                                    |
                                ASIC Power
```

The important distinction is that **Level 1 preserves the implementation state of the FireSim simulator, while Level 2 preserves the semantic state of the original RTL design**.

---

## 2. Core Requirements

### 2.1 Level-1 Checkpoint

A Level-1 checkpoint must capture the state necessary to resume the complete FireSim execution in VCS metasimulation.

This includes:

- FAME-transformed DUT state
- Golden Gate-generated model state
- LI-BDN token/channel state
- FIFO contents and pointers
- FASED timing-model state
- Bridge hardware state
- Target main-memory contents
- Relevant host-side bridge-driver state
- Target-cycle counters and clock phases
- Outstanding transactions and other state affecting future execution

The desired invariant is:

```text
Uninterrupted FireSim:
C ----------------------------------> C+N

Checkpoint/restored:
C ---- snapshot ----> VCS Metasim --> C+N
```

Both executions must produce identical target-visible behavior for corresponding target cycles.

This applies to target-cycle behavior, not the timing of physical FPGA clocks or PCIe transfers.

Indefinite continuation requires the simulation environment to remain deterministic, or for relevant external inputs to be recorded and reproduced.

### 2.2 Level-2 Checkpoint

A Level-2 checkpoint must represent the original pre-FAME RTL state.

It should include all relevant sequential microarchitectural state:

- ROB
- Rename tables
- Physical register files
- LSQ
- Pipeline registers
- Cache data and metadata
- MSHRs
- TLBs
- Branch predictors
- FSMs
- Other registers and memories

It must exclude simulator-only state introduced by Golden Gate.

The checkpoint must use stable semantic StateIDs that map to original RTL objects.

### 2.3 Supported Replay Modes

Support three execution modes.

**Mode A — Finite trace-driven replay**

```text
.rtlckpt + recorded I/O trace
               |
               v
        Original RTL VCS
               |
        finite exact replay
```

The trace may originate from an FPGA or metasim.

No live FireSim environment is required.

**Mode B — Live semantic cosimulation**

```text
VCS Metasim
    |
    +-- transformed DUT
    +-- FASED and devices
    |
    +-- target-cycle inputs
              |
              v
       Original RTL VCS
              |
       compare DUT outputs
```

Metasim remains authoritative. The clean DUT executes as a shadow.

**Mode C — Gate-level ASIC replay**

```text
.rtlckpt + recorded I/O trace
               |
     formal state translation
               |
               v
       ASIC gate-level VCS
               |
          gate-level SAIF
               |
          power analysis
```

This is the only supported ASIC power-estimation path.

### 2.4 Non-goals

Do not implement:

- ICAP/JTAG FPGA configuration readback
- Traditional long serial scan-chain checkpointing
- FASED-to-DRAMSim2 state translation
- Approximate RTL-activity-to-gate activity propagation
- Automatic gate-level switching inference from RTL SAIF
- Clean-DUT ownership handoff in the initial implementation
- Multi-FPGA checkpoint coordination initially

---

# 3. Phase 0 — Repository Reconnaissance

Before modifying FireSim, inspect the actual repository and identify the correct integration points.

Do not assume compiler class names, pass ordering, or bridge APIs from historical FireSim versions.

### Tasks

1. Identify the current FireSim/Chipyard revisions.
2. Find Golden Gate's compiler entry points.
3. Inspect FAME transformation passes.
4. Identify where registers and memories are rewritten or optimized.
5. Locate bridge and LI-BDN channel generation.
6. Inspect DMA and MMIO bridge infrastructure.
7. Examine FASED and its backing functional memory.
8. Identify host-side bridge-driver state.
9. Locate the VCS metasim infrastructure.
10. Identify the ASIC synthesis and formal verification toolchains available in the environment.

Likely source areas to investigate, after confirming actual repository layout:

```text
sim/midas/src/main/scala/midas/
sim/midas/src/main/scala/midas/passes/
sim/midas/src/main/scala/midas/widgets/
sim/midas/src/main/scala/midas/models/dram/
sim/src/main/cc/
sim/src/test/scala/
```

Check availability of Synopsys Formality or Cadence Conformal, and determine which formal matching/equivalence artifacts each can export.

### Deliverable

Create:

```text
docs/checkpointing/reconnaissance.md
```

Document the source-level integration points, compiler pass order, current tool versions, memory models, driver interfaces, and outstanding risks.

**Acceptance:** The agent can trace an original target register through Golden Gate transformations and identify where its logical checkpoint identity can be preserved.

---

# 4. Phase 1 — Shared Checkpoint Infrastructure

Implement the checkpoint metadata, file formats, and runtime abstractions.

### File formats

Use two versioned checkpoint types:

```text
.fsckpt     Full transformed simulator checkpoint
.rtlckpt    Original semantic DUT checkpoint
.trace      Recorded DUT boundary I/O
```

A checkpoint directory may contain:

```text
checkpoint/
    manifest.json
    simulator.fsckpt
    dut.rtlckpt
    boundary.trace
```

Each file is optional depending on the requested checkpoint mode.

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
asic_netlist_hash (when relevant)
state_manifest_hash
checkpoint_size
checksum
```

Reject incompatible checkpoint/build combinations before attempting restoration.

### State manifest

Each state element must be assigned a stable StateID.

For example:

```text
StateID:       0x000142
Hierarchy:     BoomCore.rob.head
Kind:          register
Width:         7
Clock Domain:  core_clock
```

For memories, also record depth, address indexing, and bit ordering.

Implement deterministic serialization and explicit handling of unsupported or unknown state.

### Deliverables

- Shared checkpoint schema
- Serialization/deserialization library
- Manifest generation
- Build compatibility checking
- Checkpoint validation utility

**Acceptance:** State serialization/deserialization round-trips bit-exactly, and corrupted or incompatible files fail clearly.

---

# 5. Phase 2 — Level-2 Semantic State Discovery

Implement this first because it establishes the Strober/DESSERT checkpoint foundation.

### Pre-FAME compiler pass

Create a state discovery pass before Golden Gate changes the logical state representation.

The pass should:

1. Traverse the selected DUT hierarchy.
2. Identify all sequential elements.
3. Assign semantic StateIDs.
4. Record hierarchy, type, width, depth, and clock domain.
5. Generate the state manifest.
6. Preserve sufficient information to instrument logical state readout later.

### Example

```text
StateID 0x00100 -> rob_head
StateID 0x00101 -> rob_tail
StateID 0x00200 -> rename_table[0]
StateID 0x00201 -> rename_table[1]
StateID 0x01000 -> dcache.tags
```

The manifest should describe the original RTL state rather than Golden Gate's implementation-specific state.

### Memory handling

Memories require special care.

Do not blindly add extra read ports that could prevent BRAM inference or interfere with memory optimizations.

Investigate checkpoint-time address iteration and memory-specific access mechanisms.

The logical memory contents must remain recoverable even if Golden Gate changes the FPGA implementation.

Any unsupported memory transformation should produce an explicit error.

### Deliverable

Generate `.rtlckpt`-compatible semantic state metadata from the original DUT.

**Acceptance:** A test circuit containing registers, an FSM, register arrays, and SRAM has a complete and correct semantic state manifest.

---

# 6. Phase 3 — Level-2 Checkpointing and Finite Replay in Metasim

Implement a software-backed proof of concept before developing the full hardware readout network.

### Workflow

```text
Original RTL
     |
Golden Gate
     |
VCS Metasim
     |
run to target cycle C
     |
capture semantic state
     |
record I/O [C, C+N)
     |
     v
.rtlckpt + .trace
     |
     v
Original RTL VCS
     |
restore state
replay inputs
compare outputs
```

### Tasks

- Use VCS simulator access, such as VPI, to implement an initial backdoor state-capture oracle.
- Generate the semantic checkpoint file.
- Implement a VPI/DPI state loader for clean RTL.
- Restore registers and memories before resuming target clocks.
- Record every relevant DUT boundary input/output per target cycle.
- Replay the recorded input values into the original RTL.
- Compare DUT outputs with the original execution.
- Generate VCS waveforms.

The checkpoint must be taken at a precisely defined target-clock phase.

### Required tests

Checkpoint while:

- The pipeline contains in-flight instructions.
- A cache miss is outstanding.
- A memory response is pending.
- An interface is stalled by backpressure.
- An internal queue is nonempty.

The DUT must not need to become idle.

**Acceptance:** A new clean-RTL VCS process can restore a checkpoint and reproduce a finite execution window cycle-by-cycle.

---

# 7. Phase 4 — Synthesizable Banked Checkpoint Network

Replace temporary simulator backdoor extraction with FPGA-compatible hardware instrumentation.

### Architecture

```text
Register Banks ----+
Memory Banks ------+
Other State Banks -+
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

### Implementation requirements

- Group registers and memories into local state banks.
- Implement checkpoint read commands.
- Serialize state in a deterministic order.
- Support memory address iteration.
- Preserve normal target execution behavior.
- Freeze appropriate state while capturing a consistent target-cycle snapshot.
- Implement backpressure and error detection.
- Reuse existing FireSim bridge infrastructure.

Initially, capture state while target-time advancement is paused.

Later, investigate local staging RAM to permit target execution to resume before DMA transfer completes.

### Validation

Compare the synthesized checkpoint network output against the VCS backdoor reference from Phase 3.

**Acceptance:** The hardware-style network produces an identical semantic checkpoint without requiring direct simulator access to internal DUT objects.

---

# 8. Phase 5 — Level-1 Full Simulator State Checkpointing

Implement the complete FireSim simulator checkpoint.

### State discovery

Create a second state inventory covering the generated simulator rather than just the original DUT.

Include:

```text
FAME transformed target
Golden Gate memory models
LI-BDN channels
Token FIFO state
FASED state
Bridge hardware state
Simulation cycle/control state
Functional main memory
Relevant host-driver/device state
```

### Consistent capture protocol

Implement a checkpoint FSM:

```text
RUNNING
   |
CHECKPOINT_REQUESTED
   |
REACH_CONSISTENT_CUT
   |
FREEZE
   |
CAPTURE_STATE
   |
CAPTURE_MEMORY_AND_DRIVERS
   |
VALIDATE
   |
RESUME
```

A target-cycle counter reaching C is not sufficient by itself.

The checkpoint must represent a coherent state across all affected simulator models and boundary channels.

Outstanding target memory requests do not have to complete, but their state must be preserved.

Physical host-side transfers that affect the checkpoint may need to be paused, committed, or explicitly serialized.

### Memory contents

Preserve both:

- FASED timing-model state
- Functional target main-memory contents

These are separate components.

Start with full memory snapshots.

Optimize with incremental/dirty-page mechanisms later.

### Driver state

Add an interface resembling:

```text
save_state()
load_state()
```

for relevant host-side bridge drivers.

Unsupported drivers must be explicitly identified, and exact continuation must not be claimed when their state is missing.

### VCS restoration

Load the complete simulator checkpoint into a fresh process running the compatible generated metasim design.

Restore all required state before target execution resumes.

### Acceptance

Compare:

```text
A: uninterrupted VCS metasim

B: VCS metasim
       -> checkpoint
       -> exit process
       -> new process
       -> restore
       -> continue
```

Require identical target-visible outputs and transaction timing over the comparison interval, including tests with outstanding memory requests.

---

# 9. Phase 6 — DMA Transport

Implement FPGA-compatible checkpoint transfer using the existing FireSim infrastructure.

### CheckpointBridge

The bridge should provide:

```text
MMIO control registers
Checkpoint request/status
State-bank stream input
Wide streaming FIFO
DMA output path
Error/status reporting
```

### Host driver

The driver should:

1. Issue checkpoint requests.
2. Wait for a consistent capture point.
3. Transfer serialized state.
4. Capture associated memory/driver state.
5. Verify file size and checksum.
6. Commit the completed checkpoint.

Both Level 1 and Level 2 should use the same general transport infrastructure, although they require different state inventories.

### Acceptance

Checkpoint data produced through the hardware-style streaming/DMA interface must match the corresponding software reference format.

---

# 10. Phase 7 — Rolling Checkpoint Manager

Implement periodic checkpoints with bounded retention.

### Configuration

Support options resembling:

```text
checkpoint_interval_target_cycles
checkpoint_retention_count
checkpoint_directory
checkpoint_level
```

For example:

```text
interval = 100000 target cycles
retention = 32 checkpoints
```

### Workflow

```text
Target cycles ---------------------------------------->

        S0       S1       S2       S3       S4
        |--------|--------|--------|--------|

        retain [S1, S2, S3, S4]

        next checkpoint S5 completes

        retain [S2, S3, S4, S5]
```

Only delete an older checkpoint after the replacement has been fully committed and verified.

### Deadlock support

Support both:

- Target-cycle watchdogs, such as lack of instruction retirement.
- Host-progress watchdogs detecting when Golden Gate stops advancing target time.

A deadlocked simulation must not be required to produce a new checkpoint.

Instead, restore an earlier checkpoint and replay toward the failure.

### Acceptance

Recover from an injected late-detected bug or progress stall using a retained earlier checkpoint.

---

# 11. Phase 8 — Live Clean-RTL Cosimulation

Implement Level-1/Level-2 synchronized execution.

### Architecture

```text
                   VCS Metasim
           +------------------------+
           |                        |
           | FAME-transformed DUT   |
           | FASED                  |
           | Device/bridge models   |
           |                        |
           +-----------+------------+
                       |
                  Input I[t]
                       |
             +---------+---------+
             |                   |
             v                   v
      Transformed DUT        Clean RTL DUT
             |                   |
           O_F[t]              O_R[t]
             |                   |
             +------ compare ----+
```

Both DUT representations must begin from matching semantic states at the same target cycle.

### Execution protocol

For each target cycle:

1. Obtain target-visible input values from the authoritative FireSim execution.
2. Drive equivalent values into the clean RTL.
3. Advance the clean RTL through the corresponding target clock event.
4. Compare its boundary outputs against the transformed DUT.
5. Optionally compare semantic state hashes.
6. Stop and report any divergence.

The adapter must account for ready/valid handshakes and combinational boundary dependencies. It must preserve target-cycle semantics rather than assuming host simulation cycles correspond directly to target cycles.

### Authoritative execution

For the initial implementation:

```text
Transformed DUT -> FASED

Clean RTL -> comparison only
```

Do not implement an ownership handoff yet.

The transformed DUT continues to determine the reference execution.

### Acceptance

Demonstrate long-running synchronized execution and detect deliberate state or output corruption at the correct target cycle.

---

# 12. Phase 9 — DESSERT-Style Debugging

Support finite trace-driven replay without live metasimulation.

### Capture

```text
FPGA or Metasim
       |
       +-- Level-2 state at C
       |
       +-- DUT boundary trace [C,C+N)
       |
       v
.rtlckpt + .trace
```

### Replay

```text
.rtlckpt + .trace
       |
       v
Original RTL VCS
       |
restore state
replay input trace
compare outputs
       |
       v
Full waveform
```

### Requirements

- Support traces captured directly from FPGA.
- Support traces captured from metasim.
- Use one common trace format.
- Record all relevant boundary input and output signals.
- Identify the first mismatching target cycle.
- Allow waveform generation over the selected ROI.

Trace replay should remain independently usable even when Level-1 checkpointing or live cosimulation is unavailable.

### Acceptance

Reproduce a deliberate RTL bug with a restored semantic checkpoint and a finite trace, without running FASED or metasim during replay.

---

# 13. Phase 10 — Strober-Style Formal State Mapping and ASIC Power Replay

This is the **only supported ASIC power-estimation methodology**.

Do not implement approximate RTL-SAIF-to-gate activity propagation.

The goal is to reproduce the sampled RTL execution directly on the actual synthesized ASIC gate-level netlist, using a formally validated mapping between RTL and gate-level sequential state.

## 13.1 Complete power flow

```text
             FPGA / Metasim
                    |
            Level-2 checkpoint
                    |
             DUT boundary trace
                    |
                    v
          Pre-synthesis RTL state
                    |
                    |
              FORMAL TOOL
            RTL ↔ Gate Matching
                    |
                    v
             State Mapping Table
                    |
                    v
             ASIC Gate Netlist
                    |
              VCS State Loader
                    |
              Recorded Inputs
                    |
                    v
            Gate-Level Simulation
                    |
             Gate-Level SAIF
                    |
                    v
              Joules / Voltus
                    |
                    v
                ASIC Power
```

## 13.2 Formal RTL-to-gate matching

Use a formal equivalence tool such as Synopsys Formality or Cadence Conformal, depending on available tools and licenses.

Do not rely on hierarchical name matching as the primary correspondence method.

The flow must:

1. Load the original, uninstrumented pre-FAME RTL.
2. Load the ASIC synthesized gate-level netlist.
3. Establish matching clocks, resets, parameters, and design configurations.
4. Perform sequential equivalence checking.
5. Extract formally justified sequential matching points.
6. Translate those matching points into a state correspondence manifest.
7. Validate that all relevant gate-level sequential state can be initialized consistently.

The RTL reference must come from the same original DUT configuration used to produce the semantic checkpoint.

Do not compare against the FAME-transformed implementation.

## 13.3 State mapping table

Generate an artifact resembling:

```text
asic_state_map.json
```

Each entry should identify:

```text
semantic StateID
original RTL object
gate-level object(s)
bit positions
mapping operation
proof/reference status
```

For simple cases:

```text
StateID 0x00142
    RTL:  BoomCore.rob.head
    Gate: U_ROB/U_REG_84/Q
```

More complicated cases may require:

- Bit reordering
- Inverted register polarity
- Duplicated registers
- Merged registers
- Constant-valued bits
- Optimized-away state

A formal equivalence pass alone is not sufficient proof that every checkpoint bit has a usable direct gate-level mapping.

The agent must establish whether the matching results can produce valid initialization values for the netlist.

A mapping may be an expression or relationship rather than one RTL register corresponding to one gate-level register.

If the required gate-level state cannot be reconstructed, fail the checkpoint-to-GLS translation explicitly.

## 13.4 Retiming

Retiming can move registers across combinational logic and change the temporal meaning of gate-level sequential state.

This may make direct RTL checkpoint restoration impossible without additional history or state reconstruction.

For the initial implementation:

**Disable retiming in the ASIC synthesis configuration used for replay validation.**

This is an initial simplification, not a permanent architectural restriction.

Later, evaluate support for retimed datapaths using formally derived state relationships or recorded input history, following the general strategy discussed in Strober.

Do not generate an unverified mapping for a retimed register.

## 13.5 Gate-level memory mapping

Treat ASIC SRAMs and register files explicitly.

The gate-level netlist may contain SRAM macro instances instead of individual flip-flops.

The loader must restore logical memory contents through an appropriate simulation-memory initialization mechanism.

The state-mapping verification must account for:

- SRAM macro interfaces
- Behavioral simulation models
- Physical memory organization
- Bit and address ordering
- Synthesis optimizations around memory interfaces

Do not assume the formal tool automatically generates memory initialization procedures.

## 13.6 Build-specific mapping

A state mapping must be bound to the exact RTL and ASIC netlist builds.

Record:

```text
rtl_hash
netlist_hash
formal_tool_version
formal_run_configuration
state_manifest_hash
mapping_hash
```

Reject mismatched builds.

A successful prior mapping cannot be assumed valid after a new synthesis or RTL build.

## 13.7 Gate-level checkpoint loader

Implement a VCS VPI/PLI loader for the ASIC netlist.

The loader should:

1. Read the `.rtlckpt`.
2. Load the formally validated state map.
3. Compute gate-level initialization values.
4. Initialize required sequential state.
5. Initialize SRAM macro contents.
6. Apply the correct clocks, reset conditions, and static test/configuration pins.
7. Allow combinational logic to settle.
8. Begin replay at the checkpoint target cycle.

Use deposits or equivalent initialization techniques that allow normal sequential behavior after restoration.

Avoid permanent forces on functional state.

For performance, load state in bulk through VPI/PLI rather than generating individual simulator console commands.

## 13.8 Replay against the gate-level netlist

Drive the exact target-boundary inputs recorded from FPGA or metasim.

For each target cycle:

- Apply the recorded inputs.
- Advance the ASIC simulation through the intended clock event.
- Compare the gate-level DUT outputs against the recorded target outputs.
- Stop on a mismatch.
- Record the first divergence and relevant diagnostic signals.

The gate-level simulation must reproduce the same target-cycle logical behavior as the original FireSim execution.

Timing-aware simulation may include intra-cycle gate delays and glitches, but sampled target-cycle outputs must still match at the defined observation points.

If using post-layout SDF, ensure the specified clock period and timing constraints produce a valid timing simulation.

## 13.9 Generate real gate-level activity

After successfully restoring the ASIC netlist and replaying the desired execution:

```text
ASIC gate-level VCS
        |
        v
gate_level.saif
```

The SAIF or VCD must be generated from the actual gate-level netlist simulation.

This is the authoritative switching-activity source for power analysis.

RTL VCD/SAIF may still be generated for debugging, but must not be substituted for gate-level activity in the power workflow.

## 13.10 Power analysis

Feed the gate-level activity into the available ASIC power analysis tool, such as Joules or Voltus.

Use the appropriate:

- ASIC technology libraries
- Cell timing and power models
- Clock definitions
- Operating conditions
- Post-synthesis or post-layout netlist
- Parasitic information, if available
- Gate-level SAIF/VCD

The power analysis tool's responsibility is to compute power from the gate-level implementation and its measured activity.

**It must not be responsible for inferring that activity from RTL activity.**

Report:

```text
average dynamic power
leakage power
total power
energy per target cycle
energy per instruction (where applicable)
hierarchical power breakdown
```

For sample-based power estimation, support aggregation of multiple independent replay windows.

Statistical sampling and confidence-interval computation can be added after single-window correctness is established.

## 13.11 Activity-source independence

The gate-level replay must support checkpoints/traces originating from either source.

**Source A: FPGA**

```text
FPGA
 |
.rtlckpt + .trace
 |
Formal state mapping
 |
Gate-level VCS
 |
SAIF -> power
```

**Source B: Metasim**

```text
VCS metasim
 |
.rtlckpt + .trace
 |
Formal state mapping
 |
Gate-level VCS
 |
SAIF -> power
```

The trace captured from metasim may itself be generated while the original RTL shadow is running.

However, the final activity used for ASIC power must still come from gate-level replay.

## 13.12 Formal mapping validation

Before computing power, create a dedicated correctness test.

For a small DUT:

1. Run the original RTL from reset.
2. Generate an ASIC netlist.
3. Perform formal equivalence checking.
4. Generate the state mapping.
5. Capture an RTL checkpoint at cycle C.
6. Restore the ASIC netlist directly at C.
7. Replay the same target inputs.
8. Compare outputs over a substantial window.
9. Compare against a gate-level simulation that ran continuously from reset.

The two gate-level executions should agree at the selected observation points.

Repeat over multiple checkpoint positions.

Test mapping scenarios involving:

- Bit reordering
- Register polarity inversion
- Register duplication
- Optimized state
- Small memories

Reject cases that cannot be mapped correctly.

### Phase 10 acceptance criteria

A Level-2 semantic checkpoint can be translated into valid gate-level sequential state using formally validated correspondence.

A fresh gate-level VCS simulation can then reproduce the original target execution cycle-by-cycle and generate gate-level SAIF for power analysis.

No RTL-activity propagation shortcut is permitted.

---

# 14. Phase 11 — FPGA Bringup

Only begin actual FPGA validation when hardware becomes available.

The project must be substantially testable through metasim alone.

### Tasks

1. Synthesize the instrumented FireSim simulator.
2. Verify state bank access.
3. Validate CheckpointBridge MMIO.
4. Validate DMA checkpoint transfer.
5. Produce Level-1 FPGA checkpoints.
6. Restore them into VCS metasim.
7. Produce Level-2 FPGA checkpoints.
8. Restore them into clean RTL VCS.
9. Replay captured FPGA traces against the ASIC gate-level netlist.
10. Generate gate-level power reports.

### Performance measurements

Measure:

```text
LUT utilization
FF utilization
BRAM/URAM utilization
Fmax
simulation throughput
snapshot size
snapshot latency
DMA transfer time
restore latency
```

Separate state-capture latency from DMA transfer time.

---

# 15. Testing Strategy

Progress through increasingly complex targets.

### Stage 1 — Small RTL

- Counter
- FSM
- Register array
- Small SRAM

Verify Level-2 checkpointing and formal state matching.

### Stage 2 — Protocols and memory

- Ready/valid handshakes
- Outstanding reads/writes
- Backpressure
- FIFO state
- Memory responses crossing checkpoint boundaries

Verify replay correctness.

### Stage 3 — Golden Gate

- FAME-transformed DUT
- LI-BDN channels
- FASED
- Host bridge drivers
- Functional main memory

Verify Level-1 checkpoint consistency.

### Stage 4 — Rocket

- Bare-metal execution
- Memory-intensive workloads
- Long-running tests
- RTL and gate-level replay

### Stage 5 — BOOM

- Out-of-order execution
- ROB/rename/LSQ state
- Long-running benchmarks
- Deadlock recovery
- Power sampling

### Correctness matrix

| Test | Expected result |
|---|---|
| Level-2 capture → RTL restore | Exact finite replay |
| Hardware state banks vs VCS oracle | Identical semantic checkpoint |
| Level-1 capture → fresh metasim | Exact target-visible continuation |
| Restore with pending FASED transactions | Same future target-cycle responses |
| Restore with nonempty LI-BDN channels | No lost or duplicated events |
| FPGA → metasim | Exact target-visible continuation |
| Live clean-RTL cosimulation | Cycle-by-cycle equivalence |
| FPGA trace → clean RTL | Exact replay |
| Metasim trace → clean RTL | Exact replay |
| RTL vs ASIC netlist formal equivalence | Proven under documented assumptions |
| Semantic checkpoint → ASIC state mapping | All necessary state reconstructable |
| ASIC GLS restored replay | Cycle-exact logical outputs |
| ASIC GLS gate-level activity | Valid SAIF/VCD |
| Gate-level activity → power tool | Valid ASIC power report |
| Corrupted checkpoint | Rejected |
| Incompatible build/mapping | Rejected |
| Rolling checkpoint after deadlock | Successful rewind |

---

# 16. Milestone Order

### M0 — Repository reconnaissance

Document exact compiler insertion points, available toolchains, and state/model boundaries.

### M1 — Semantic StateID infrastructure

Implement pre-FAME state discovery, manifests, and checkpoint serialization.

### M2 — Level-2 metasim checkpoint/replay

Capture semantic state and finite I/O traces from metasim. Restore them into clean RTL VCS.

**Exit criterion:** Bit-exact finite replay.

### M3 — Hardware-compatible state access

Implement the banked state network and checkpoint transport.

**Exit criterion:** Hardware-style extraction matches the simulator backdoor oracle.

### M4 — Level-1 metasim checkpoint/restore

Capture and restore complete generated simulator state, including supported memory and driver state.

**Exit criterion:** Fresh-process continuation matches uninterrupted execution.

### M5 — Rolling checkpoints

Implement periodic snapshots and bounded retention.

**Exit criterion:** An earlier checkpoint can be used to investigate an injected hang.

### M6 — Live clean-RTL cosimulation

Run clean RTL as a synchronized shadow of a Level-1-restored metasimulator.

**Exit criterion:** Long-running cycle-by-cycle equivalence.

### M7 — DESSERT workflow

Integrate standalone semantic snapshot and trace replay with waveform generation.

**Exit criterion:** Reproduce a known RTL bug without running metasim during replay.

### M8 — Formal RTL-to-gate matching

Implement formal equivalence and extraction of a validated semantic-StateID-to-netlist-state map.

**Exit criterion:** State mappings can restore a small ASIC netlist and reproduce its original trajectory.

### M9 — Strober gate-level replay and power

Load semantic checkpoints into the ASIC netlist, replay exact input traces, generate gate-level SAIF, and run Joules/Voltus.

**Exit criterion:** Repeatable gate-level replay and ASIC power estimation from both FPGA-sourced and metasim-sourced checkpoints.

### M10 — FPGA validation

Validate checkpoint capture through DMA on supported hardware and restore into VCS.

**Exit criterion:** Real FPGA checkpoints work with the established metasim, clean RTL, and gate-level replay flows.

---

# 17. Engineering Requirements for the Agent

1. Inspect the current repository before making architectural assumptions.

2. Keep checkpointing optional and disabled by default.

3. Implement small independently testable changes.

4. Always preserve target-cycle semantics.

5. Do not silently omit sequential state.

6. Use deterministic semantic StateIDs rather than depending on physical FPGA locations.

7. Keep Level-1 and Level-2 checkpoint formats separate.

8. Do not assume DMA provides state extraction; implement the required access logic.

9. Do not assume target-cycle freeze automatically produces a consistent full-system checkpoint.

10. Preserve FASED state for Level-1 continuation.

11. Use recorded DUT boundary traces for finite Level-2 replay.

12. Preserve both finite trace replay and live clean-RTL cosimulation.

13. Do not claim arbitrary Level-2 standalone continuation without a live environment.

14. Do not use FAME-transformed simulator activity for ASIC power.

15. **Do not ask Joules or another power tool to map RTL activity to gates.**

16. **Use a formal equivalence tool to establish RTL-to-gate state correspondence.**

17. **Restore actual ASIC gate-level sequential state before gate-level replay.**

18. **Generate ASIC power activity only from gate-level simulation.**

19. Reject unproven or incomplete mappings instead of silently approximating them.

20. Initially disable ASIC register retiming to simplify state restoration.

21. Validate restoration against uninterrupted reference executions.

22. Report the first mismatching target cycle and signal whenever possible.

23. Preserve build hashes and formal mapping metadata.

24. Document unsupported constructs and limitations.

25. Keep implementation milestones reviewable and independently verifiable.

---

# 18. Final Success Criteria

The implementation is complete when it demonstrates:

**Level 1:** A full FireSim simulator checkpoint can be extracted, restored in a fresh VCS metasim process, and continued with the same target-cycle behavior.

**Level 2:** Original pre-FAME microarchitectural state can be checkpointed and restored into clean RTL.

**Rolling recovery:** Earlier checkpoints remain available for investigating late-detected bugs and hangs.

**DESSERT:** A semantic checkpoint plus a finite I/O trace can reproduce an RTL bug with full waveform visibility.

**Live cosimulation:** The original RTL can execute alongside metasim while preserving cycle-by-cycle equivalence.

**Strober:** A semantic checkpoint and trace can be mapped through formally validated RTL-to-gate state correspondence, restored into the ASIC netlist, and replayed to produce real gate-level switching activity.

**ASIC power:** Joules or Voltus can consume that gate-level activity and generate ASIC power estimates. No approximate RTL-to-gate activity inference is part of the implementation.

The central architectural principle is:

**Level 1 preserves the complete FireSim execution. Level 2 preserves the original DUT's semantic state. Formal state matching connects Level 2 to the actual ASIC implementation, enabling accurate replay, debugging, and gate-level power analysis.**