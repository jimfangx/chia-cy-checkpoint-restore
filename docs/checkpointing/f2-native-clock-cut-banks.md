# Native functional banks behind a physical clock cut

Iteration 227 adds `PhysicalClockCutWiring.generateNative`. It first uses the
same-reference descriptor factory to reconstruct the supplied functional banks
from the original complete circuit, inventory, topology and CE dependencies.
Changed instrumentation, selectors, dependencies and capture claims reject.
Only then does it mask the generated functional network. The original native
BUFGCEs retain their locations, primitive definitions and raw source inputs;
unmasked logical CE samples propagate independently through hierarchy. One
additional root BUFGCE masks ordinary functional-clock consumers. The three bank
response registers keep their independent `ckpt_clock` input, which must connect
to the same ungated common source as the controller and future transport.

The explicit native probe emits an additional `.native-clock-cut` FIRRTL/RTL/
binding/XDC companion and emission receipt. It preserves the independently
validated bank annotations without renaming their targets. Both translated XDC
files match the functional-bank companion byte for byte. The original generated
image and existing functional/descriptor emission contracts remain separate.
Every new receipt explicitly declines complete capture, production freeze-owner
binding, deployment and metasim restore support.

The independent structural auditor compares every reachable native definition,
port, driver, storage declaration, reset expression, clocked effect and sequential
clock against the independently audited functional bank circuit. It checks the
original identity/descriptor documents and all outer bindings, rather than
trusting the new companion's ownership declarations. Eight deliberately changed
FIRRTL/binding/emission compositions are rehashed coherently: root-mask bypass,
cascaded native source, native-mask bypass, masked endpoint clock, changed
functional update, swapped CE order, false capture and false owner admission.
Each must fail for the changed structure or contract.

`NativeClockCutFixture` connects the generated network and bank endpoint to the
real `CheckpointPhysicalClockCut` in external-network mode. The source-clock
sampler, endpoint and controller share an explicit reset; the native functional
reset remains a separately controlled input. Native localhost Vivado synthesis
checks the original gates, single falling-edge mask register, absence of duplicate
gates and electrical connectivity of every bank response register to the raw
source. Net segments across hierarchy must be compared electrically, not by
local name. The first diagnostic incorrectly compared local names and is retained
with its underlying Vivado log under this iteration's `runs/` directory.

The EDA component test reads the actual generated banks using their public
ports. Its independent arithmetic and old-read RAM oracle compare continued
execution with an unmodified native reference. It exercises four physical cuts,
all wide-register/RAM transfer words, held responses and selector changes under
backpressure. A primitive clock-output monitor detects a root-mask bypass that
functional freeze muxes could otherwise hide. Separate missing-owner and CE-drift
runs require read permission to disappear and the cut to remain stopped after
host withdrawal. Deliberate payload corruption and an independently compiled
root-mask fault must stop on their first observed mismatch. Full execution VCDs
are retained for healthy and all negative runs. Results and exact commands belong
under `automations/checkpoint_loop/runs/aws-f2/iteration227/`.

Final execution passes **234 Scala / 309 checkpoint Python / 40 loop tests**,
all **18 localhost synthesis scopes** and **37 EDA scopes**, including the retained
ASan/UBSan/host/FCFS checks. The new native component uses **882 LUTs / 462
registers**, with OOC 140 MHz estimated setup/hold **+2.672/−0.074 ns**; hold timing
closure is pending. Fresh EDA SP2 VCS passes **5,343 comparisons / 128 words /
468 response stalls** over cuts **15/68/183/329**, then runs through cycle **409**.
Semantic corruption stops at cycle 15/check 24 and a separately compiled root-mask
bypass at cycle 15/check 14. Missing-owner/CE-drift cuts remain stopped. All five
execution VCDs survive the final **244-input / 24-source** native/EDA audit. The
exact Rocket companion passes independent reconstruction on both hosts over
**2,290 module / 14,313 sequential/effect definitions**, retaining **12,096
functional + three CE descriptors / 619,016 words** and all six original clock/CE
inputs byte for byte. Initial test-marker/receipt-metadata failures and their
fresh regenerated results remain in `recovery-notes.json`; no old receipt was
rewritten to pass.

This is a clock/bank composition increment. The descriptor table still describes
original simulator state; the added root mask and control registers are
capture-owned machinery, with no claimed restore mapping. A complete reset
protocol must keep all owners consistent when resetting the sampler, endpoint,
router or widget: resetting the sampler alone can open its mask. Production
`F1Shim.reset`, external CE inputs, functional DRAM writers, FASED/bridge/host
owners and pre-FAME state must receive complete same-cut contracts before image
admission. The CE endpoint/router and actual FireSim MMIO/DMA widget still need
connections to this generated native network. Full localhost image implementation,
timing closure, AFI deployment, FPGA captures, paired zero-edge restoration,
finite/live RTL migration and rolling hardware recovery remain pending.
