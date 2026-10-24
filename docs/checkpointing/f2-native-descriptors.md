# Native functional and physical CE descriptor composition

Iteration 226 closes the descriptor gap between the native functional-bank
companion and the physical CE endpoint. `CheckpointCaptureDescriptors.fromNativeGenerated`
reconstructs the native functional result from the original resolved circuit,
complete simulator inventory, clock plan and original CE dependencies. It rejects
a supplied result whose binding or selectors differ, then validates its actual
instrumentation and translated annotations. Only this explicit factory accepts
native functional coverage; `fromGenerated` retains its existing admission guard.

The factory combines all concrete functional descriptors with ordered bank-255
physical CE StateIDs from that same original circuit. Both the composition and
its binding retain `same_reference_sha256`. Physical CE identities remain
separate from metasim gate-output identities. The old component composition API
still permits distinct reference circuits and makes no same-reference claim.
Complete capture, deployable image, production freeze-owner admission and
metasim restore support remain explicitly false on every native companion.

The opt-in native probe emits a separate descriptor manifest/binding, physical
CE endpoint/binding, host constructor and emission receipt. The receipt binds
the unchanged native-functional emission contract, including original source,
all concrete storage, native gates, translated XDC and instrumented RTL. These
outputs do not replace Golden Gate's ordinary image. The independent Python
auditor reconstructs functional descriptors from complete storage ownership
and physical descriptors from the native primitive paths. It checks the common
reference, every selector/word shape, both inventories, host bytes and explicit
unsupported flags, rather than accepting a composition's own declarations.

The exact Rocket recipe compiler succeeds. Its new table contains **12,099**
descriptors: **12,096** functional and **three** physical CE owners, totaling
**619,016** 64-bit transfer words (**4,952,128** payload bytes). All three original
native gates and the two translated XDC files remain. This count is descriptor
readout coverage only; host DRAM, reset/external-writer ownership, pre-FAME
semantic completeness and physical CE restoration remain separate obligations.

A two-native-gate fixture includes the original 65-bit counters, 130-bit RAM and
old-read pipeline. Its same-reference table contains five functional and two
physical descriptors, totaling 34 words. The real FireSim MMIO/stream widget
elaborates with this immutable ROM and matching driver header. Native localhost
Vivado 2025.2 synthesis uses **1,591 LUTs / 764 registers**, one immutable ROM
and no duplicate native gates in the external-network widget. OOC 140 MHz
setup/hold estimates are **+0.611/+0.071 ns**; full-image implementation and
timing closure remain pending. All **233 Scala tests** pass, including independently
valid physical sidecars from a different circuit, coherently rehashed changed
instrumentation, altered selectors, identity substitution and admission claims.

Fresh EDA SP2 VCS passes **81 public-port ROM checks** over all seven entries,
invalid-index aliases and three reset phases. An independently recompiled
physical-slot fault stops at descriptor **5 / check 11**. Both full debug VCDs
contain execution. Independent native/EDA auditing matches **42 inputs /
17 sources** and rejects **six** coherently rehashed composition corruptions.
The exact Rocket table also passes independent complete EDA reconstruction,
matching all generated hashes with the native audit. All 17 localhost synthesis
scopes and the full retained EDA sanitizer/FCFS/host/bridge/bank/memory/clock/
CE/reset/top/ROM/widget/router scopes pass. Native functional readout retains
4,539 checks over four complete cuts, 128 words and 468 response stalls; the
physical widget retains 6,810 checks and the router 4,912. These remain component
results and cannot establish CPU capture or restore acceptance.

Execution receipts, current source hashes, exact commands, complete retained
regressions and EDA results belong under
`automations/checkpoint_loop/runs/aws-f2/iteration226/`. The principal new tool
is `tools.checkpoint_formats.tests.verify_native_descriptors`; it supports
production auditing, localhost synthesis, fresh EDA ROM verification and
independent native/EDA evidence matching. Initial execution failures and stale
intermediate receipts remain preserved and cannot authorize current acceptance.

Next: connect the native functional banks, physical CE endpoint and descriptor
ROM to the generated physical clock mask, ungated router and actual MMIO/DMA
widget. Bind `F1Shim.reset`, external memory writers and all host owners at the
same atomic cut. Complete simulator/functional-memory/FASED/bridge/host/pre-FAME
coverage, CE restore, localhost full image P&R/AFI and active all-hart F2 cuts
remain required. No checkpoint-enabled AFI, FPGA checkpoint or CPU migration is
established by descriptor composition. Independent paired zero-edge readback,
FPGA-reference continuation, finite clean-RTL replay, sustained live RTL beyond
the recorded trace and rolling hardware recovery all remain pending.
