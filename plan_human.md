Yes. I think the design has converged into something that cleanly subsumes both **DESSERT-style debugging** and **Strober-style power replay**, while adding a stronger capability neither paper really provides: **full FireSim execution migration from FPGA into VCS metasimulation**.

## Goal

Build a two-level checkpointing system for modern FireSim:

```text
                         FireSim FPGA
                              |
              +---------------+---------------+
              |                               |
          Level 1                         Level 2
     FireSim simulator                semantic DUT state
         checkpoint                       checkpoint
              |                               |
              v                               v
        VCS metasim                 clean pre-FAME RTL
              |                               |
   exact FireSim continuation        debug / replay / power
              |
              +-------- can drive -----------+
                       clean RTL live
```

The two levels should be usable independently or together.

---

# Level 1 — Full FireSim simulator checkpoint

### Purpose

Checkpoint the **actual Golden Gate/FAME-transformed FireSim simulator** running on the FPGA and restore it into VCS metasimulation.

The checkpoint should contain enough state that:

```text
FPGA FireSim @ cycle C
        |
        | checkpoint
        v
VCS metasim @ cycle C
        |
        v
continue for arbitrary future target cycles
```

with the same target-visible behavior as if the FPGA run had continued.

### What gets checkpointed

This is not just the processor:

```text
.fsckpt
|
+-- FAME-transformed DUT state
+-- Golden Gate model state
+-- LI-BDN/token FIFOs
+-- FASED timing-model state
+-- bridge hardware state
+-- target-cycle counters
+-- target main-memory contents
+-- other target-visible device state
+-- any host-side bridge state that affects future target behavior
```

The correctness goal is:

\[
\text{FireSim}_{FPGA}(C+n)
=
\text{FireSim}_{metasim}(C+n)
\]

in **target-cycle behavior**, not necessarily FPGA host-clock behavior.

### Capture mechanism

We do **not** want Strober's giant scan-chain architecture.

Instead, generate a checkpoint access network for simulator state:

```text
simulator state banks
       |
       v
checkpoint arbiter
       |
    wide FIFO
       |
      DMA
       |
      host
```

The simulator is stopped at an atomic checkpoint boundary, state is collected through the banked checkpoint network, and bulk data is moved off the FPGA using FireSim's DMA infrastructure.

A staging buffer/double buffer can eventually let the simulator resume before the host transfer finishes.

Restore works in the reverse direction:

```text
.fsckpt
   |
   v
VCS checkpoint loader
   |
   +--> transformed DUT
   +--> FASED
   +--> token queues
   +--> bridges
   +--> memory
   ...
```

Everything is initialized before target-time advancement resumes.

---

# Rolling Level-1 checkpoints

Rather than discovering a bug and rerunning the entire workload, maintain a rolling history:

```text
target time ---------------------------------------------------->

     S0          S1          S2          S3          S4
     |-----------|-----------|-----------|-----------|
          X cycles    X cycles    X cycles

retained:
                 [S1] [S2] [S3] [S4]

new checkpoint completes:
                      [S2] [S3] [S4] [S5]
```

For example:

```text
checkpoint every 100k target cycles
retain 32 checkpoints

=> ~3.2M cycles of rewind history
```

Only delete the oldest checkpoint after the newest checkpoint has been fully committed and verified.

This solves the DESSERT deadlock/window problem: if a machine hangs and detection occurs long after the causal bug, restore a sufficiently old Level-1 checkpoint and approach the failure again in metasim.

---

# Level 2 — Semantic DUT checkpoint + clean-RTL cosimulation

Level 2 operates at a completely different abstraction.

We want the state of the **original DUT before FAME/Golden Gate transforms**:

```text
ROB
rename tables
physical register files
LSQ
pipeline registers
caches
TLBs
MSHRs
branch predictor
FSMs
target SRAMs
...
```

not the implementation state of the FireSim simulator.

This is the modern equivalent of the state Strober/DESSERT snapshot.

Strober defines replay as restoring all target RTL state at cycle \(C\) and replaying recorded I/O from that point. 3007787.3001151 DESSERT similarly restores target state into software RTL simulation and drives recorded inputs while checking outputs. DESSERT_Debugging_RTL_Effective…

### State identification

Before Golden Gate transforms the target, assign stable IDs to every sequential state element:

```text
StateID 0x0100 -> rob_head
StateID 0x0101 -> rob_tail
StateID 0x0200 -> rename_table[0]
StateID 0x0201 -> rename_table[1]
...
StateID 0x1000 -> dcache metadata RAM
```

This produces a semantic checkpoint:

```text
.rtlckpt
```

whose meaning is independent of how Golden Gate or Vivado implemented the design.

The checkpoint instrumentation can then pass through Golden Gate and expose those logical values from FPGA or metasim.

---

# Clean-RTL cosimulation

Once we restore a Level-1 checkpoint into metasim, we can simultaneously restore the corresponding Level-2 state into an ordinary pre-FAME RTL instance in VCS:

```text
                 checkpoint cycle C
                         |
              +----------+----------+
              |                     |
              v                     v
       FireSim metasim        clean RTL VCS
          .fsckpt               .rtlckpt
              |                     |
              +---------+-----------+
                        |
                 target-cycle sync
```

The metasimulator remains the authoritative execution environment:

```text
                     FASED / devices
                           |
                       input I[t]
                           |
                 +---------+---------+
                 |                   |
                 v                   v
          transformed DUT        clean RTL
                 |                   |
              O_F[t]              O_R[t]
                 |                   |
                 +------ compare ----+
```

Every target cycle:

1. The clean RTL receives the same target-visible inputs as the transformed FireSim DUT.
2. It advances exactly one corresponding target cycle.
3. Its boundary outputs are compared against the transformed DUT.
4. Optionally, semantic state hashes are compared periodically.

The fundamental invariant is:

\[
S_{clean}(t)=S_{FireSim-target}(t)
\]

and:

\[
O_{clean}(t)=O_{FireSim-target}(t)
\]

for every target cycle.

If this holds, the clean RTL provides an ordinary hierarchy and waveform while representing exactly the target execution occurring inside FireSim.

---

# Why this can run indefinitely

DESSERT does not need a live environment because it only replays a finite \(L\)-cycle trace.

Our Level-2 cosimulation can instead leave:

```text
FASED
bridges
device models
```

running inside metasim.

Therefore the clean RTL never has to independently recreate DRAM behavior:

```text
                        FireSim metasim
                    +----------------------+
                    | FASED                |
                    | devices              |
                    | bridge models        |
                    +----------+-----------+
                               |
                      target-cycle behavior
                               |
                               v
                         clean RTL VCS
```

FASED continues to determine when memory responses happen.

If FireSim says:

```text
cycle 100: request A
cycle 180: response A
```

the clean RTL sees precisely:

```text
cycle 100: request A
cycle 180: response A
```

We do **not** translate FASED into DRAMSim2.

That avoids a major accuracy problem.

As long as all causally relevant external inputs are deterministic/replayed, this clean-RTL shadow execution can continue arbitrarily far into the future.

---

# DESSERT mode

Our Level-2 infrastructure directly supports the DESSERT use case.

Instead of keeping metasim alive:

```text
FPGA / metasim
      |
      | semantic checkpoint @ C
      | record boundary I/O C ... C+L
      v
   .rtlckpt
   + trace
      |
      v
clean RTL VCS
      |
      | restore state
      | replay inputs
      | compare outputs
      v
full waveform around bug
```

DESSERT uses exactly this basic strategy: restore the RTL snapshot in software simulation, feed recorded inputs, and compare outputs cycle-by-cycle. DESSERT_Debugging_RTL_Effective…

So for debugging we support two modes:

```text
finite standalone replay
    .rtlckpt + trace

or

indefinite live replay
    .rtlckpt + running Level-1 metasim
```

The second mode is our extension, but using a trace (which is faster than cosim-ing metasimulation) should still be a supported mode.

---

# Strober mode

Power estimation is also a direct consumer of Level 2.

Run FireSim and select a sample at target cycle \(C\):

```text
FPGA
 |
 +-- semantic state S_D[C]
 |
 +-- record target boundary trace
       C ... C+N
```

Then replay that target execution against the clean design:

```text
.rtlckpt + trace
        |
        v
  clean RTL / ASIC representation
        |
        v
 switching activity
        |
        v
   power analysis
```

This is essentially Strober's methodology. Strober loads target RTL state into detailed gate-level simulation and feeds the captured input trace to reproduce the sampled execution before extracting switching activity.

FASED does not need to run during this replay because its observable behavior is already contained in the trace. Again, support both modes -- running strober via a trace or capture the input trace from metasim to feed into joules

---

# Mapping activity to the ASIC implementation

There are two routes we should investigate.

### Path A — direct gate-level replay

The most rigorous path is:

```text
.rtlckpt
    |
RTL-to-gate state mapping
    |
    v
post-synthesis / post-layout netlist

+ recorded input trace
    |
    v
gate-level VCS
    |
   SAIF
    |
Joules / other power analysis
```

This is closest to Strober.

The hard problem is mapping semantic RTL state into the optimized gate-level implementation.

Strober handled synthesis name/structure changes using formal-verification matching points. It also notes that retiming is particularly difficult because post-synthesis state may not correspond directly to individual RTL registers.

For an initial implementation we should probably disable retiming.

---

# The resulting system

The final architecture looks like:

```text
                         FireSim FPGA
                              |
                    rolling checkpoints
                              |
                +-------------+-------------+
                |                           |
              Level 1                     Level 2
             .fsckpt                     .rtlckpt
                |                           |
                v                           |
          VCS metasim                       |
                |                           |
       exact continuation                   |
                |                           |
                +---- target inputs --------+
                |                           |
                |                     clean RTL VCS
                |                           |
                |                   +-------+-------+
                |                   |               |
                |                waveform        RTL SAIF
                |                   |               |
                |                debugging        Joules?
                |                                   |
                |                                   |
                +-- generate finite trace ----------+
                                                    |
                                                    v
                                            ASIC gate-level VCS
                                                    |
                                                   SAIF
                                                    |
                                                  power
```

## Development order

I would implement this in the following order:

1. **Level-2 semantic checkpointing in metasim first.** Enumerate pre-FAME state, assign stable `StateID`s, extract `.rtlckpt`, restore clean RTL VCS, and prove finite trace replay.

2. **Build the synthesizable banked checkpoint/DMA path.** Replace VCS backdoor extraction with the same hardware mechanism that will eventually run on FPGA.

3. **Implement Level-1 checkpoint/restore.** Snapshot the complete generated FireSim simulator, terminate the simulator, restore into a fresh VCS metasim instance, and prove long-run target-cycle equivalence against an uninterrupted run.

4. **Add rolling checkpoints.** Periodically retain Level-1 checkpoints so hangs/deadlocks can be rewound without rerunning from boot.

5. **Add Level-1 + Level-2 cosimulation.** Restore both from the same target cycle and run clean RTL as a shadow of the transformed DUT with cycle-by-cycle checking.

6. **Build the DESSERT path.** `.rtlckpt + finite trace -> clean RTL VCS -> waveform`.

7. **Build the Strober path.** `.rtlckpt + finite trace -> ASIC power replay`, comparing direct gate-level activity against an RTL-SAIF/Joules flow.

The core architectural principle is therefore:

> **Level 1 preserves the complete FireSim execution so it can migrate from FPGA to metasim indefinitely. Level 2 preserves the semantic pre-FAME DUT state so the same target execution can be observed through clean RTL for debugging and through the ASIC implementation for power.**

That gives us DESSERT and Strober as natural subsets, rather than building two separate checkpoint systems.