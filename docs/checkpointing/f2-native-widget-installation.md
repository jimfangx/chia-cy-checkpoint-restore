# Native checkpoint widget installation

Iteration 289 adds an explicit, bound native mode to `CheckpointCaptureWidget`
and its `FPGATop` attachment. The validated binding supplies the complete stream
manifest, original descriptor ROM, ordered named owners, native payload and
clock geometry, reserved selectors and shadow layout. The selected widget uses
the native endpoint; its original ROM is internal. Compatibility descriptor
inputs cannot replace that ROM. Native `readerIdle` and `liveState` inputs and
all owner, cycle and CE inputs require explicit connections. Tests exercise
missing inputs at the actual `FPGATop` initialization boundary.

The generated driver constructor carries a typed native binding and complete
stream manifest. It checks a nullable stream engine before dereferencing it,
rejects invalid MMIO locations and validates the exact appended native
descriptors and shadow shape before device I/O. Native shadow widths are bound
to this metadata, including widths beyond the old physical-only limit. The
legacy constructor remains available for existing physical component users.

Review found that `CheckpointNativeBoundWidgetEndpoint` accepted a NASTI
parameter but dropped it when constructing its inner endpoint. The default
four-bit ID silently truncated the actual F2 twelve-bit ID. The parameter now
propagates through the complete hierarchy. The installed-widget fixture uses
the real F2 control parameters; its executable bench drives high write/read
IDs and independently reconstructs the canonical state with twelve-bit IDs.

The new verification runner authenticates emitted RTL and the layout probe
against the completed Scala receipt's generated-file ledger. Native synthesis
receipts require the exact tool commands, successful logs, unchanged 140 MHz
constraint, Vivado 2025.2 identity, reports, DCP, vendor models and generated
input hashes. Offline tests reject coherently rehashed incompatible evidence.
The VCS bench retains the original complete native/shadow readback, four cuts,
owner-loss, abort/recovery and compiled first-divergence oracles. Diagnostics,
interrupted attempts and commands belong under `runs/aws-f2/iteration289/`.

Validation passes all 350 Scala tests / 56 suites plus sixteen preparation
tests, 404 Python tests, 61 manager tests and EDA SP2 sanitizer/FCFS/bank/cut
checks. Fresh native execution passes cuts 35/68/112/167 and complete 1,585-bit
shadows. Both compiled faults stop at cut 35 without acknowledging the divergent
control word or advancing another raw edge. The actual generated constructor
passes 106 installation checks with 31 no-I/O rejections. The legacy physical
widget passes fresh synthesis, five VCS cuts / 170 words and independent audit.

Native synthesis estimates are +0.911/+0.073 ns at requested 140 MHz. Exact-DCP
place/route reaches +0.370/+0.026 ns, preserving all 2,577 sequential identities
and 67 bank drivers; 4,928 nets route with no errors or DRC violations. Vivado
quantizes the inherited period to 7.143 ns. Parent clock source/skew and shell
I/O budgets remain unmodeled. A separate immutable closure corrects an original
post-route audit that compared filename headers and its own documented
`DONT_TOUCH` preservation directive as if they were changed timing constraints.
The exact two differences and unchanged timing commands are independently
audited; the original failed wrapper receipt and actual successful tool logs
remain intact. These are component results, with all FPGA/CPU acceptance pending.

This installs a transport option in the production API. The exact Rocket
recipe still lacks complete atomic state ownership and cannot build an admitted
checkpoint image. The native endpoint continues to reject ordinary image
compilation even with stripped annotations and headers. Deferred physical
reservations and their peer/graft ABI explicitly reject the native transport;
they cannot substitute physical descriptors for the native stream manifest.
The generated header retains `#error Incomplete_checkpoint_hardware_coverage`.

Common-cut/reset/physical CE, functional-hold and reader-idle owner contracts,
atomic transport/stream/response-bank ownership, memory/FASED/host coverage and
independent pre-FAME mapping remain required. Observation outputs do not
capture or restore these owners. Full localhost image synthesis/place-and-route,
AFI/AGFI deployment, all four active all-hart FPGA cuts, FPGA-origin zero-edge
readback, finite replay, sustained paired live CPU continuation and rolling
hardware recovery remain pending. No hardware acceptance column advances.

The read-only production gap audit binds the retained exact-Rocket refusal to
the FASED BUFGCE CE latch and three gates sharing the raw clock. Their 207
distinct CE-cone state owners and the external reset writer still need one
common low-phase cut. An older regional diagnostic separately rejects freezing
eight live widget registers (228 bits) together with their collector. The stock
recipe currently has no production top binding. These observations retain
their original execution dates; they are not a fresh exact-recipe compilation.
The next coherent step is a real common-cut/reset/CE owner binding with selective
functional hold and an ungated collector, followed by native peer/reservation
integration and the retained localhost build invocation. Exact paths, widths,
clocks, StateIDs and build argv are in the iteration-289 owner-gap receipt.
