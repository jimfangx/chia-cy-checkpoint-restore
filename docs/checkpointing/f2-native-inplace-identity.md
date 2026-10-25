# Global identities for in-place native banks

Iteration 232 adds `NativeCheckpointIdentity.discover`. It reconstructs the
selected native banks and descriptors from their original FIRRTL and validates
the actual enclosing instance path and every selected executing definition.
It separately inventories the original complete enclosing generated RTL, including
its physical clock topology and original CE dependency cones.

The projection assigns each selected functional entry its original global
generated-simulator StateID, and each physical CE entry its original global
physical-latch StateID. It preserves the selected endpoint's descriptor order,
bank/slot, flattened word shape and CE bit order. A global inventory ordinal or
physical-gate index is never substituted for a local hardware selector. The
original metasim BUFGCE output StateID remains distinct from physical CE state.

`NativeCheckpointInPlace.generate` binds the projection into its version-2
integration binding. `CheckpointCaptureDescriptors.fromNativeInPlace` supplies
the matching global identities and manifest hash for the widget and host table.
The manifest includes every uncovered global functional and physical owner;
complete FPGA capture, production freeze-owner binding, deployable image and
metasim restore support remain false. Functional-memory, software-owner and
independent pre-FAME coverage still require separate complete contracts.

The independent Python auditor reconstructs original register, RAM and
emitter-owned memory-pipeline membership, shapes, signedness, reset/clock
expressions and StateIDs from FIRRTL. It audits complete global physical clock
topology and CE dependencies, then derives the projection and uncovered
partition independently of its hashes. Its source-topology API asserts no RTL
emission. Invalid FAME clock metadata retains explicit invalid provenance;
invalid/data/constant origins still cannot clock sequential consumers or native
gate inputs.

The bounded fixture retains active wide-RAM writes, old-read pipelines, raw
ancestor clocks, four physical cuts and held-response backpressure. In addition
to six structural mutations, sixteen metadata mutations recompute all enclosing
hashes: global/local ID aliases, selector/word order/storage path, physical
slot/global index, metasim alias, uncovered owners/shapes, coherently omitted or
reshaped global storage, data/constant parent clocks and false capture/restore claims. Current execution,+synthesis, exact-Rocket auditing and retained regression results belong under
`automations/checkpoint_loop/runs/aws-f2/iteration232/`; consult its final summary
and ordered command manifest. This increment does not establish FPGA capture.

All **244 Scala / 309 checkpoint Python / 40 loop tests** and all **21 native
synthesis / 40 EDA scopes**, including retained ASan/UBSan/host/FCFS checks, pass.
The fixture uses **884 LUTs / 590 registers**; all **194** parent/readout clocks
remain raw. OOC 140 MHz setup/hold estimates are **+2.672/−0.074 ns**; full-image
closure is pending. Fresh SP2 VCS passes **6,541 checks / four cuts / 128 words /
468 response stalls** through cycle **409**, preserving all six hierarchical
execution VCDs. Native/EDA auditing matches **934 inputs / 33 current sources**.
Exact Rocket independently reconciles **10,149 functional + two CE** entries
(**320,587 words**) and leaves **1,947 functional / 298,428 words** plus one FASED
CE owner uncovered. Local CE slots **0/1** remain distinct from global physical
indices **1/2**. Fresh exact-recipe generation matches the original structural
input byte for byte; the ordinary production compiler still rejects the unbound
FASED physical CE owner/common cut.

Next: production annotation/XDC projection and actual in-place CE endpoint,
router, widget/MMIO/stream attachment without masking parent control execution.
Bind F1Shim reset, every external CE/DRAM writer, FASED, other bridges and host
owners; implement physical CE restore and independent pre-FAME mapping. Full
localhost image implementation, timing closure, AFI/driver binding, active
all-hart F2 captures, paired zero-edge restores, finite replay, sustained live
RTL and rolling hardware recovery remain pending.
