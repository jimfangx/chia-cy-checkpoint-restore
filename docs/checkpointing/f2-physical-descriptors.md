# Immutable functional and physical CE descriptor composition

Iteration 224 adds `CheckpointCaptureDescriptors.withPhysicalClockState`.
It appends bank-255 CE entries to an already validated generated functional
bank table. The factory regenerates physical StateIDs, slot order, endpoint
RTL and its binding from the resolved circuit, complete simulator inventory,
clock plan and original CE dependencies. It accepts no caller-supplied physical
descriptor list. Repeated composition, stale provenance, identity/selector
aliases and transport-count overflow reject.

The canonical composition manifest binds both component inventories, the
functional bank binding and the physical endpoint binding. The composition
binding retains the complete component documents and their distinct circuit
references. Physical StateIDs remain separate from metasim clock-output IDs;
the physical restore adapter remains unsupported. Complete capture, deployable
image, production freeze ownership and metasim restore support stay false.
This API establishes descriptor composition, not common-cut production coverage.

The real FireSim widget can now elaborate with this immutable table in physical
mode. Its generated host constructor and synthesized ROM use the same ordered
descriptors and composition hash. The header also binds the complete composition
binding. Physical CE count must agree in both directions: a physical table
cannot silently use logical transport, and a functional-only table cannot
enable physical transport. External descriptor pins remain overridden by the
internal ROM, as in the retained generated-network regression.

The new Scala fixture deliberately retains separate functional and physical
reference circuits: nine functional entries, including an eight-word RAM, and
three native-gate CE entries. These are component fixtures, not Rocket hardware
state. Its independent Python auditor reconstructs functional identities/shapes,
physical identities/dependencies, selectors, composition documents and the exact
little-endian C++ manifest constructor. It checks matching native/EDA bytes and
retains coherent missing-owner, slot/namespace/identity alias, stale-build and
false-ownership mutations as negative cases.

The complete Scala scope passes 226 tests. Native localhost Vivado 2025.2
synthesis of the actual physical widget with the composed ROM uses 1,806 LUTs
and 767 registers, one immutable descriptor ROM and no duplicate BUFGCEs.
140 MHz out-of-context setup/hold estimates are +0.553/+0.071 ns. This is not
full-image implementation timing. Fresh VCS verification belongs exclusively
on EDA; `tools.checkpoint_formats.tests.verify_physical_descriptors` provides
native `vivado`, EDA `vcs` and independent `audit` modes.

Fresh EDA SP2 VCS passes 126 public-port ROM checks over all twelve descriptors,
forward/reverse ordering, alternating invalid indices and three reset phases.
The independently compiled slot fault stops at the first physical descriptor,
index 9 / check 19. Both full debug VCDs contain execution timestamps. Native/EDA
auditing matches 34 inputs and 13 current sources and rejects six coherently
rehashed manifest corruptions. This verifies descriptor construction and
readback; the retained physical widget scope separately exercises MMIO/DMA.
All fifteen native component synthesis scopes and the complete retained EDA
sanitizer/FCFS/host/bridge/bank/memory/clock scope pass. Fresh physical-widget
execution retains 6,810 checks, six complete cuts, 130 DMA stalls, raw frames
and full debug waves. The final native inventory has no running Vivado/Java
job or loop F2 instance.

Current exact Rocket production compilation still rejects the unsupported
FASED physical BUFGCE CE-latch owner. Production bank generation and common-cut
reset/external-writer/functional-memory/FASED/bridge/host/pre-FAME ownership,
physical CE zero-edge restore, full localhost image/P&R/AFI, active all-hart
FPGA captures, complete paired readback, finite replay, sustained live clean RTL
and rolling FPGA recovery remain required. Reuse iteration194's initialized
ExternallyProvisioned localhost build invocation. No FPGA checkpoint or new
capture image is established by this component change.

Execution commands and individual receipts are retained under
`automations/checkpoint_loop/runs/aws-f2/iteration224/`; see
`verification-commands.json` and `remaining-blockers.json`.
