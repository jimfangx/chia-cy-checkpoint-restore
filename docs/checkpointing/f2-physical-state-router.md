# Physical CE bank and DMA composition

Iteration 222 adds `CheckpointPhysicalStateRouter.sv`, a synthesizable read-only
composition of the functional bank network and the compiler-generated physical
CE endpoint. It appends the CE descriptors to the functional descriptors and
reserves bank 255 for physical CE state. Functional descriptors naming that bank
reject. CE descriptors must preserve exact slot order, width one and depth one;
invalid indices or shapes produce invalid zero-shaped descriptors. The total
entry count must fit the transport's existing 65,535-entry limit.

One accepted request owns the response path until it drains. The router saves
its endpoint selection, suppresses further requests while it is pending and
ignores unsolicited responses from the other endpoint. Upstream selector
changes cannot redirect a delayed or stalled response. Abort does not erase
this ownership: the transport drains its accepted read before admitting a new
capture. Reset immediately suppresses handshakes and cancels the route at its
edge. Both bank endpoints, the sampler, router and transport require the same
ungated source clock and reset.

The integration fixture uses the exact Rocket compiler-generated CE endpoint
and the compiler's separate three-gate workload network. It sends one cycle
word, three functional words and three separately addressed physical CE words
through the real component MMIO/DMA framing path. Its functional endpoint and
fixed test manifest are fixture contracts, not a production Rocket state image.
An independent host arithmetic oracle verifies all words, descriptor selectors,
post-stop cycle labels and CRCs. Standalone tests vary endpoint readiness,
selector changes, response errors, unsolicited responses, reset and descriptor
contracts. Deliberate oracle faults and independently compiled incorrect routing
must stop at the first bad response.

Fresh EDA SP2 passes **4,912 integrated checks / five complete cuts / 36
requests / 91 DMA stalls / 108 delayed functional-bank cycles**, through 320
functional cycles. Complete post-stop cuts are 2, 19, 130, 258 and 302.
Standalone routing passes **311 checks / six transactions**. Six runtime fault
cases, seven host-frame integrity cases (including physical CE and selector
corruption with corrected CRCs), five reset interruption/recovery phases, a
corrupt routing oracle and an independently compiled inverted routing register
are exercised. Fifteen full debug VCDs are retained. Independent native/EDA auditing matches
40 inputs / 21 sources and rejects thirteen evidence substitutions, including
physical CE StateID aliases, removed owners and reserved-bank aliases.
Native localhost synthesis
uses **1,867 LUTs / 669 registers**, four generated SYNC BUFGCEs and one
falling-edge mask. Out-of-context 140 MHz setup/hold estimates are
**+0.593/-0.062 ns**; full image implementation timing remains open.

Exact commands, native Vivado outputs, fresh EDA VCS logs, full debug waveforms,
corruption checks and protected-input receipts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration222/`. The verification entry
point is `tools.checkpoint_formats.tests.verify_physical_state_router_transport`;
its modes are `vivado` on localhost, `vcs` on EDA and independent receipt `audit`.

This is **in_progress component integration**. Production bank generation still
rejects the unsupported FASED physical CE owner. The router does not bind
production external reset/writers, prove complete simulator/functional-memory/
timing/bridge/host/pre-FAME ownership, or restore physical CE state into metasim.
Full localhost image implementation/P&R/AFI, four-hart active hardware cuts,
paired complete zero-edge readbacks, independent finite replay, sustained live
clean RTL beyond the recorded trace and rolling FPGA failure recovery remain
required. Reuse iteration194's initialized ExternallyProvisioned localhost build
invocation; do not deploy this fixture as a checkpoint image.
