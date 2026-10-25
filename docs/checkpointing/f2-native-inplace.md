# In-place native bank integration

Iteration 231 adds `NativeCheckpointInPlace.generate`. It instruments an
existing concrete instance instead of embedding a second functional execution.
The selected source must match every reachable executing definition. The
generator reconstructs native functional banks and physical clock masking,
replaces that instance's implementation and carries its access sideband through
the existing ancestor hierarchy. The bank endpoint receives the proven raw
source; ancestor state and its ordinary connections keep their original clocks.
Functional reset stays distinct from the endpoint's explicit controller reset.

The bounded API rejects stale source, relative/missing paths, repeated selected
executions, shared ancestors, reserved identifiers, generated module collisions,
nontransparent raw clocks and unsupported enclosing annotations. It preserves
the selected bank generator's translated annotations. Complete production
annotation projection and all-owner capture admission remain separate work.

Scoped FAME clock-token inputs can be one-bit data at the new boundary. Their
provenance remains explicit data, including when routed through Clock-typed
metadata. They cannot become oscillators for registers, memories, effects or
native gate inputs. Compiler tests and the independent clock auditor enforce
that distinction.

The fixture contains two existing raw-clock ancestor counters around the
original gated counter/wide-RAM execution. Independent auditing reconstructs
every new port/connection, compares every original ancestor statement and
matches the complete selected native network. Rehashed access-clock, parent
clock, freeze, reset, original-update and duplicate-execution mutations must
reject. Native synthesis checks the existing gate paths and every ancestor and
bank-endpoint clock. Fresh EDA VCS exercises active writes, old-read pipelines,
four cuts, held responses, resumed execution and negative cases, retaining
hierarchical waveforms. This is component evidence, not FPGA-origin capture.

All **242 Scala tests** pass. Fresh EDA SP2 execution passes **6,541 checks /
four cuts / 128 words / 468 response stalls**, continuing through cycle **409**.
Semantic corruption fails at cut **15**, check **30**. A separately compiled
parent-control freeze fault fails at cut **15**, check **18**, before any bank
word is accepted; a physical root-mask bypass fails at check **19**. Missing
owner and CE drift stay stopped. Six hierarchical execution VCDs remain.
Native localhost synthesis uses **884 LUTs / 590 registers**, with all **194**
parent/readout register clocks independently checked. OOC 140 MHz setup/hold
estimates are **+2.672/−0.074 ns**; full-image timing closure remains pending.
All **21 native synthesis / 40 EDA scopes**, **309 checkpoint Python / 40 loop
tests**, and retained ASan/UBSan/host/FCFS checks pass.

Execution logs, commands and measured results belong under
`automations/checkpoint_loop/runs/aws-f2/iteration231/`; consult its final
`summary.json` and `verification-commands.json`.

The exact Rocket structural input has a selected `F1Shim.top.sim` boundary.
Independent auditing covers **10,149 functional descriptors** and **two
separately composed CE descriptors**, **1,994
generated module definitions / 11,590 sequential/effect definitions**, and both
unchanged ancestor bodies with **3,840** directly declared register bits.
The in-place host exposes the unmasked CE vector. Splicing its CE endpoint,
router and registered checkpoint widget into the raw control path remains
pending; descriptor composition does not establish that connection.
These descriptors retain their explicit selected-root namespace. Production
integration must reconcile them with the complete simulator's global manifest
and selectors before binding any image or restore driver.
Instrumenting that subtree does not cover the sibling FASED timing model,
functional DRAM, other bridges, software owners or independent pre-FAME semantic
mapping. Production annotation/XDC projection, actual in-place FPGATop MMIO/DMA
connection, physical CE restore, a complete localhost image/P&R/timing/AFI and
active all-hart F2 captures remain pending. Both FPGA-origin checkpoint restore
levels, finite replay, sustained live RTL comparison and rolling recovery remain
pending. No custom capture AFI or hardware checkpoint is claimed.
