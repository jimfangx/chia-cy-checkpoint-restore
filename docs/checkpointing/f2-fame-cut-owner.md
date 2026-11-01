# Local FAME progress owner connected to the F2 collector

Iteration 310 adds `--simulator-f2-fame-clock-cut PRIMARY_DOMAIN:EXTERNAL_OWNER_COUNT`.
It requires the complete root inventory, FAME progress observations, physical
clock plan/wiring and an explicit synchronous-reset cut. The generic-cycle
collector option cannot be combined with it. Ordinary builds remain unchanged.

The generator resolves the existing typed FAME roles through actual compiler
renames. It requires exactly one concrete observed model execution and an
explicit domain from that model. It routes that domain's **applied-edge count**
to the generated raw-clock collector's cycle input. Completed FAME steps,
consumed tokens and bridge-source counters do not provide that label.

One internal owner bit checks all model domains, using full 65-bit addition:
`consumed == applied + pending`, with `consumed <= completed_steps`.
Host reset or sticky overflow invalidates it. Missing external owners still
refuse the cut. The existing collector samples only after its common low-phase
stop; a fault withdraws read permission immediately and remains sticky after
sampling, including when the host withdraws its request. There are no new
storage bits in the witness and no additional functional edges. The binding
field `new_storage_bits: 0` refers to this witness, not the composed collector.
The existing collector retains its separate control state and is not made an
atomically captured owner by this adapter.

The emitter's prepared instance connectors already have local pin wires.
Reopening those connectors for a second emission can collide with freshly
emitted pin wires, creating duplicate declarations and multiple CE drivers.
This new generator moves the existing connector-connected `DefWire`s to fresh
names using a FIRRTL RenameMap before reopening. It preserves ports, original
registers and StateIDs, revalidates all FAME roles, and reconnects the original
native gates. Native synthesis must reject critical warnings; the initial
failed synthesis is retained separately. This repair is scoped to this new
path; it does not certify older generic physical-wiring sidecars from prepared
emitter IR for deployment.

The binding records source/manifest/plan/reopened/final circuit hashes,
construction-site identity, exact resolved role paths, selected applied label,
external-owner count and internal-owner bit. The role rows describe the
validated source before clock/reset masking; the generated native CE pins
receive the mask and the collector observes the original unmasked logical CE
vector. Independent regeneration rejects
changed wiring even with coherently updated hashes. Native/VCS verification
checks all eight component fixture files against a successful source-bound
Scala emission receipt; merely rehashing a supplied Verilog file is insufficient. Emission produces separate
`.f2-fame-clock-cut` FIRRTL, Verilog, binding, collector binding and emission
receipt files. It does not replace the production simulator netlist.

This is a **local FAME witness**, not a global target-time authority. It does
not prove that channels, satellite models, FASED, functional memory, physical
CE latches, bridges, shell writers or host owners agree at that cut. It does
not load original state or implement a physical-latch-to-metasim restore
adapter. Production descriptor/epoch/transport attachment, coordinated owners,
full localhost image implementation/AFI, four-hart FPGA-origin cuts, paired
CPU readback, independent finite replay, sustained live RTL and rolling
hardware recovery remain required. All deployment/complete/global flags stay
false and the existing physical ownership refusal remains enforced.

Evidence, original failed attempts and commands are retained beneath
`automations/checkpoint_loop/runs/aws-f2/iteration310/`. The component bench
executes the actual generated hierarchy beside an unobserved FAME reference,
counts original native gate edges independently, exercises multirate clocks,
backpressure and repeated cuts, and injects local predicate faults without
acknowledging corrupt state. Component initialization and directed fault
deposits are explicitly testbench operations, never FPGA checkpoint transport.
The raw-wave auditor reconstructs observations from original handshakes and
native edges. Its readback mutation checks invoke the same rejection function
used at actual waveform samples and require the exact divergent signal.
All VCS runs and raw-wave audits belong on EDA; Vivado belongs on this manager.
Reuse iteration 194's retained localhost build invocation and the initialized
manager inputs. Do not treat unbound account-owned AFIs as checkpoint images.

Source-bound validation passes 389 Scala tests / 60 suites plus sixteen
preparation checks, 56 focused tests and 69 manager tests. Both fresh exact
Rocket bank trials preserve the FASED physical CE refusal. The new exact
Rocket collector sibling binds 21 FAME roles and 11,465 inventory entries,
with all complete/deployment flags false.

Native localhost synthesis retains every observer bit in the component,
using 302 LUTs, 423 registers and three BUFGCEs. The 423 registers include the
existing 81-bit collector and the original 342 functional/observer bits; the
witness itself adds no registers. This is unplaced synthesis, not image timing
closure or an AFI. Fresh SP2 EDA passes twelve processes and retains twelve
full debug VCDs. The healthy run has 7,870 checks / 512 host steps, 344 completed
FAME steps, 527 functional root edges, 183 stalls, and 262 / 108 actual native
edges. Applied-label cuts are 33 / 88 / 167 / 251, each with pending-token
lookahead retained. All 261 predicate fault trials pass; the auditor rejects
323 observer/pending readback bit mutations through its actual comparison
function. A separate deliberate corruption stops at host step 17 with sixteen
comparisons acknowledged. Ten unsafe cuts remain stopped without publication
or another acknowledgement. These are component cuts, not four-hart CPU cuts.

The complete retained native and EDA staging/readout/bank/shell/corruption-wave,
ASan/UBSan/host/FCFS/cut scope and 409 Python tests pass. Historical iteration286
wave audits remain explicitly historical. Root DESSERT and Strober papers
were read for complete state, I/O trace and target-time requirements; their
scan-chain and ASIC power flows are not this implementation or acceptance.
