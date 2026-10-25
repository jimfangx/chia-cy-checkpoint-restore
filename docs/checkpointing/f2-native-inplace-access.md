# In-place functional and physical state routing

Iteration 236 adds `NativeCheckpointInPlaceAccess.emit`. It connects a single
existing instrumented host to the functional-bank endpoint, physical CE endpoint
and transaction router. It exposes the original host ports and a capture
sideband; it never elaborates a second simulator. The already-proven raw source
clocks the router and CE endpoint, while the original in-place graft supplies
the raw bank clock through the ancestors. Functional reset remains separate
from their common controller reset.

The generator reconstructs the complete context/graft/identity result from the
original source before emission. Rehashed changes to retained state, context,
physical topology, descriptor identities or annotation projection reject.
Descriptors use the original enclosing simulator's StateIDs, retaining the
selected endpoint's local selectors and physical CE bit order. Unselected
functional and physical owners remain explicit coverage deficits.

The standalone and in-place connections share a renderer. The original
standalone port/pin contract is retained. Original host XDC is emitted under
the wrapper's actual `network` instance, preserving source order, correlated
ancestor/descendant targets and primitive-local constraints. The independent
constraint auditor supports this enclosing-host placement in addition to the
original selected-root placement.

The new independent auditor checks every public port, descriptor row, pin,
remaining declaration and emitted constraint against the original hierarchy,
annotations and globally reconstructed identities. It rejects coherently
rehashed clock, reset, freeze, CE-sample, permission, response, descriptor,
extra-driver and original-constraint mutations. Native synthesis and EDA-only
SP2 execution checks are recorded under
`automations/checkpoint_loop/runs/aws-f2/iteration236/`.

The bounded execution fixture passes **7,101 EDA SP2 checks / four cuts /
136 words / 522 response stalls**, continuing through target cycle **419**.
It includes active wide-memory writes, original read pipelines, both CE samples,
complete descriptor enumeration, out-of-cut and invalid-selector rejection,
held responses with changing selectors, functional reset while frozen and
resumed execution. Missing owner and CE drift remain stopped; a separately
compiled corrupted CE connection fails on the first physical read at cycle
**25**, check **55**, before any functional word. Five debug VCDs remain.
Native synthesis with the original fixture constraints applied retains **1,091
LUTs / 595 registers**, with **199** parent/router/endpoint register clocks
independently proven raw. OOC setup/hold estimates are **+2.052/−0.074 ns**;
full-image timing closure is pending. Independent native/EDA matching binds
**817 input files / 54 sources**, rejecting ten coherently rehashed mutations.

The first Vivado attempt rejected fixture register selectors that did not name
actual synthesized cells. The next attempt was rejected for artificial clock
I-to-O max-delay path segmentation. This new execution fixture uses explicit
register-cell selection and primitive-cell preservation through its original
correlated I/O pins. The original structural fixture and all production
constraints remain unchanged. Diagnostic logs retain both rejected syntheses
and the initial Scala vararg-annotation constructor error. An early EDA launch
found no completed native receipt and never started VCS; its later execution
passes against the completed native receipt.

The exact annotated Rocket case independently passes **10,149 functional / two
CE descriptors / 320,587 words**, retaining **1,947 functional / one FASED CE**
coverage deficits. Its **2,431 source / 2,379 projected storage annotations**,
**25 context annotations / 20 kinds**, seven original XDC events and fourteen
emitted commands match across both backends. Native synthesis constants validate
source annotations, literal stateless definitions and concrete module hashes;
the metasim schema remains unchanged. Dedup history, preservation and memory-model
targets, complete path-cache invalidation and zero-argument XDC are independently
reconstructed. The annotation serializer accounts for json4s's indented empty
arrays without changing original constraint order. Unknown classes reject.
Four new Python tests exercise 23 coherent metadata corruption subcases.

All **251 Scala / 22 localhost synthesis / 41 EDA scopes**, **313 Python / 40 loop
tests** and retained **ASan/UBSan/host/FCFS** checks pass. The final inventory has
no loop runtime instances or native jobs. It observes one new pending account
AFI, `afi-0c48c4812ad82c73d`, which this turn did not request; no source/image
compatibility or capture acceptance is attributed to it. Both plans and
initialized manager inputs retain their entry hashes; no staging/local commits.

This is readout integration, not complete hardware capture. The registered
FPGATop widget/MMIO/DMA connection, complete freeze owners (including reset,
external CE, functional DRAM writers, FASED and bridges), host state, physical
CE restore and independent pre-FAME semantics remain required. Full localhost
image implementation, timing closure, AFI/AGFI/driver binding, active all-hart
F2 checkpoints, FPGA-reference continuation, independent complete zero-edge
restores, finite replay, sustained live RTL comparison and rolling recovery
remain pending. No checkpoint-enabled FPGA image or hardware-origin checkpoint
is claimed.
