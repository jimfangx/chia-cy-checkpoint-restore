# FPGA capture transport component

Iteration 188 adds a source-bound adapter for the exact MIDAS
`DefineAbstractClockGate.impl`. Its enable register updates on posedge I;
its output remains `I & enable`, including delta-cycle pulses when enable
changes. The bank generator freezes this owner alongside downstream storage.
It never substitutes CE as a downstream storage enable. Independent descriptor
validation reconstructs each ordered gate chain from actual specialized
wiring and checks the gate's enable clock, reset, next value and output.
Other gates/opaque implementations still reject. The adapter describes the
abstract RTL model, not platform-mapped BUFGCE state or a completed F2 image.

Conditional RAM clock validity now requires the exact same Boolean enable on
that memory port. Local aliases and mux(enable,1,0) identities are checked;
original clock wiring and synchronous pipeline ownership remain intact.
Unmatched guards and conditional register clocks reject. The retained exact
Rocket FASED subtree now elaborates **759 entries / 99,611 transfer words**;
this does not include functional host DRAM, host software or the full simulator.

The new component test runs on EDA after Scala emission:

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_registered_gate_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration188/scala/bank/registered-gate \
  --out automations/checkpoint_loop/runs/aws-f2/iteration188/registered-gate-vcs
```

`audit_registered_gate` independently recomputes every captured word and gate
edge from public inputs, validates immutable VCS/native snapshots and checks
first-word corruption stopped frozen. Native component synthesis uses
`synth_clocked_effects` with that generated directory after native HDK setup
from the HDK directory. This iteration's full commands, native FASED component
synthesis and independent audits are retained under `runs/aws-f2/iteration188/`.
All-owner freeze/CDC, physical clock primitive coverage and complete CPU/hardware
acceptance remain separate pending work.

Iteration 187 adds transparent hierarchical clock routing to generated bank
access. Output clock ports, sibling forwarding, connected child input pins,
local nodes/wires, and exact `Clock`/one-bit `UInt` casts through concrete IO
cells must resolve to named root clock inputs. Resolution is lazy per pin with
hierarchy-qualified cycle checks; unrelated clock dependencies cannot create a
false cycle. Data logic, register next-state drivers, constants, opaque modules,
gated clocks and asynchronous resets remain unsupported. Descriptor construction
reconstructs all clock-port provenance from the actual specialized circuit.

Materialized synchronous RAM pipeline clocks now use explicitly connected
clock wires. This preserves the original clock while allowing its alias node
to occur later than the new pipeline declaration. Original StateIDs and
pipeline ownership remain unchanged. No clock gate is replaced or treated as
a transparent wire.

`MultipleFunctionalClocksSpec` emits a second `forwarded-clocks` fixture with
14 checked clock-port routes and the same 9 entries / 15 words as the direct
fixture. On EDA, run `verify_multiple_clocks_vcs` with this generated directory;
on the manager, run `synth_clocked_effects` after native HDK setup. The same
independent `audit_multiple_clocks` verifies the private VCS/native inputs,
complete per-domain cuts, corruption stop, waveforms and native DCP. Current
commands and evidence are under `runs/aws-f2/iteration187/` relative to the loop.

The caller must still establish and hold all-owner freeze before reads through
response drain. This increment supplies neither a CDC acknowledgement nor a
common CPU cut. Complete Rocket/FAME/gated-clock/functional-memory/host
integration, localhost image P&R/AFI and FPGA-produced paired checkpoints remain
pending.

Iteration 186 extends the separate-clock bank generator to multiple direct
functional input clocks. Functional registers, RAM read/write ports and
materialized synchronous pipelines retain their distinct clocks. Child inputs
must trace directly to parent inputs. `functional_clock_domains` binds every
module/instance clock port to its root input and is independently reconstructed
from emitted wiring when constructing descriptors. Missing or altered clock
provenance rejects. Multiple clocks without a separate transport endpoint,
derived/gated clocks, opaque owners and asynchronous resets remain unsupported.

This is a wiring/freeze contract. The caller still must establish a stable
all-owner freeze in every domain before reads and hold it until responses drain;
this generator does not implement a CDC acknowledgement or a common CPU cut.
The new `MultipleFunctionalClocksSpec` emits 9 entries / 15 words with swapped
repeated children and RAMs read and written in different domains. The new EDA
check exercises independent/coincident functional clocks, stopped-clock and
adversarial frozen-clock captures, resets, backpressure, post-release execution
and first-word corruption with full debug waveforms:

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_multiple_clocks_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration186/scala/bank/multiple-clocks \
  --out automations/checkpoint_loop/runs/aws-f2/iteration186/multiple-clocks-vcs
```

Native synthesis uses `synth_clocked_effects` with that generated directory and
constrains both functional inputs and `ckpt_clock` at 140 MHz. Run only on this
manager after native F2 HDK setup. `audit_multiple_clocks` independently checks
immutable VCS/native input agreement, every recorded word/domain label, the
functional schedule, corruption stop, native DCP identity and all three clock
constraints. Component evidence does not establish a Rocket FPGA image or
hardware capture; complete integration, AFI and physical migration remain pending.

Iteration 185 adds `separateAccessClock = true` to generated bank access. The
root endpoint then uses a dedicated `ckpt_clock` while all functional storage
and synchronous RAM read owners keep their original clocks. The descriptor
validator checks the actual three endpoint register clocks against the binding's
`access_clock` and explicit freeze contract. The caller must acquire every
functional owner and hold freeze before reads until responses drain; this
option does not add a CDC handshake or establish an atomic CPU cut.

The retained exact Rocket `DCacheDataArray` passes complete original-RTL and
independent functional-model checks in fresh EDA VCS: **32,832 words** at
**C=513 / 611 / 869**, with **65,664** reads while its functional clock is
stopped, adversarial writes/clock pulses while frozen, backpressure, continuation,
first-word corruption and full debug VCD. Native localhost OOC synthesis uses
**9,568 LUTs / 522 registers**, estimated setup slack **+5.228 ns** at 140 MHz
with both clocks constrained. This is component evidence only; no complete
Rocket FPGA image or hardware checkpoint is claimed. Run the new check on EDA,
after the complete Scala suite emits `rocket-dcache-array`:

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_independent_clock_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration185/scala/bank/rocket-dcache-array \
  --out automations/checkpoint_loop/runs/aws-f2/iteration185/dcache-vcs
```

Iteration 184 adds a synchronous effect contract: `printf`, `stop` and FIRRTL
verification retain their original clock/predicate/reporting behavior, with
enables ANDed with `!ckpt_freeze`. Direct input clocks are required; derived
effect clocks, asynchronous/opaque state and analog attachments still reject.
A child clock must be driven directly by its parent's single clock. Stateless
clockless modules can route the combinational bank network; they cannot hide
independent clock domains. `NoCircuitDedupAnnotation` preserves instance clones
through resolution and is included in the checked annotation-policy hashes.

Fresh EDA VCS checks the retained exact Rocket recipe's actual DTLB subtree
(17 specialized modules, 101 state words): three complete bank captures at
**C=2 / 39 / 132**, **28,918** checks, **303** reads and **1,212** response-stall
cycles. Every public output and every captured register matches independently
emitted original RTL across **173** functional edges. The independent oracle
reads reference storage; only synthesized public bank ports supply the capture.
Full VCD, bank words and first-word corruption rejection are retained. A separate
effects fixture checks accepting-edge reset/effect freeze, **116** actual
functional print messages, stop after release and the immediate assertion's
original reporting policy. Its negative observer terminates after that report;
it does not reinterpret an immediate assertion as a fatal stop.

Native localhost Vivado 2025.2 OOC synthesis of the DTLB bank uses **3,084 LUTs /
1,859 registers**, estimated setup slack **+4.450 ns** at 140 MHz. The effects
bank uses **42 LUTs / 20 registers**. These are component checks from a retained
recipe intermediate, not fresh full-Rocket elaboration, a custom AFI, physical
capture or CPU migration. Exact commands and provenance live under
`automations/checkpoint_loop/runs/aws-f2/iteration184/`; both hardware checkpoint
levels, traces, four workload cuts, CPU restores/live comparison and rolling
F2 history remain pending.

Iteration 183 adds wide/deep generated bank mapping. A logical state entry keeps
its StateID, width and depth. For `chunks = ceil(width / 64)`, physical address
`a * chunks + c` selects bits `[64*c +: min(64, width - 64*c)]` of logical address
`a`, zero-padded to 64 bits. A single selector and descriptor cover each StateID;
chunking never invents independent semantic owners. Signed words preserve their
bit representation. RAM addresses divide by the exact chunk count, including
non-power-of-two counts. Transfers above **2^31-1** per entry fail explicitly;
physical address and descriptor depth ports remain 32 bits.

A circuit with any wide state uses `latched-banked64-chunked-v2`. Its binding
retains logical `width`/`depth` and adds `chunks`, `transfer_width`, and
`transfer_depth` to every entry. `CheckpointCaptureDescriptors` derives and
checks those fields before producing the ROM and host C++ metadata. Transport
frames remain version 1, carrying the physical shape. The Python host binding
uses `banked64-chunked-v2`, validates both shapes, checks final-chunk padding,
and reconstructs canonical `.rtlckpt` logical words only after full validation.
Narrow-only generated circuits retain the previous binding protocol; the old
explicit unchunked bank codec continues rejecting wide state.

Fresh EDA VCS SP2 connects the real generated storage and descriptor ROM to
production MMIO/DMA transport and captures **65,564** physical words at each
of **C=1 / 42 / 138**. Signed 65-bit, exact 128-bit and 512-bit registers,
129-bit x 5 RAM and 9-bit x 65,537 RAM pass independent original-RTL and
functional-input checks, reset/write freeze, **1,573,571** DMA stall cycles,
complete host reconstruction, sanitizer frame checks and frozen first-word
corruption rejection. Native localhost Vivado 2025.2 OOC synthesis uses
**20,687 LUTs / 259 registers**, estimated setup slack **+5.328 ns** at 140 MHz.
This is component evidence; complete Rocket compilation/integration, image
build/P&R/AFI and physical capture/migration remain pending.

After Scala elaboration, on EDA with `vcs-env.sh` sourced last:

```bash
python3 -m tools.checkpoint_formats.tests.verify_chunked_bank_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration183/scala/bank/chunked \
  --out automations/checkpoint_loop/runs/aws-f2/iteration183/chunked-reverify
```

On this manager, after native F2 HDK setup:

```bash
python3 -m tools.checkpoint_formats.tests.synth_chunked_bank \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration183/scala/bank/chunked \
  --out automations/checkpoint_loop/runs/aws-f2/iteration183/native-chunked-reverify
```

Iteration 182 adds explicit annotation translation during bank specialization.
Local `DontTouchAnnotation` and `MemoryFileInlineAnnotation` targets clone to
every reachable module instance; nonlocal targets resolve only the specified
subtree. Exact declaration kinds and every instance/module path are checked.
Overlapping initialization, dead/malformed/component targets, unknown annotation
types and contradictory synthesis initialization policies reject. Hex/binary
filenames and `MemorySynthInit` / `MemoryNoSynthInit` policies are preserved.
Canonical source/translated annotation hashes join the bank binding; descriptor
construction rejects dropped/changed initialization or extra unsupported metadata.
The compiler's derived path cache is still discarded and recomputed.

`InitializedStateBankSpec` uses two separately initialized repeated RAM instances.
Standard FIRRTL target-path resolution emits the independent original circuit;
the checkpoint generator does not supply that reference. EDA VCS checks all
16 initialized words at **C=0**, before any functional edge, then repeats complete
captures at **C=7 / 44 / 155** after writes. The public-input oracle and original
RTL agree through reset-independent transport, selector failures, accepting-edge
freeze, response stalls and release with a held response. Full debug waveforms
and both initialization files are retained. Native Vivado synthesis separately
checks every RAM INIT bit plane and both physical read-port copies. These are
component checks, not FPGA-origin CPU checkpoint acceptance.

After the full Scala suite elaborates the initialized fixture, run on EDA with
`vcs-env.sh` sourced last:

```bash
python3 -m tools.checkpoint_formats.tests.verify_initialized_bank_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration182/scala/bank/initialized \
  --out automations/checkpoint_loop/runs/aws-f2/iteration182/initialized-reverify
```

On this manager, after native F2 HDK setup:

```bash
python3 -m tools.checkpoint_formats.tests.synth_initialized_bank \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration182/scala/bank/initialized \
  --out automations/checkpoint_loop/runs/aws-f2/iteration182/native-initialized-reverify
```

Exact commands, immutable inputs and diagnostic trials remain under
`automations/checkpoint_loop/runs/aws-f2/iteration182/`. Other annotation contracts,
wide/deep state, complete Rocket/FAME/bridge/memory/host integration and the full
localhost image build, AFI and physical migration remain pending.

Iteration 181 materializes synchronous memory pipeline owners already present
in both inventories: saved addresses for new/undefined readers, saved data for
old readers and old/undefined readwriters. RW data updates on enabled write
edges too, matching the actual passthrough emitter. Explicit physical pipeline
names bind to unchanged logical StateIDs. Pipeline updates and RAM writes
freeze together. Unsupported RW-new semantics and identifier collisions reject.

`SynchronousStateBankSpec` emits unchanged reference RTL with the inventoried
passthrough configuration and instrumented banks. Fresh EDA VCS passes
**21,970** checks, **454** reads, **1,816** response-stall cycles and ten complete
45-word fixture cuts. Every output matches that reference and an independent
public-input oracle over **2,905** observed edges / **202** functional edges.
Full debug VCD is retained. Native F2-part OOC synthesis passes at **133 LUTs /
32 registers**, estimated setup slack **+6.087 ns** at 140 MHz. Evidence lives
under `runs/aws-f2/iteration181/synchronous-vcs/synchronous-bank-m05mtez8/` and
`runs/aws-f2/iteration181/synchronous-vivado-ody0cfps/` (relative to the loop).
This is component evidence; complete Rocket hardware capture remains pending.

New `synth_checkpoint_top` / `audit_checkpoint_top` helpers preserve private
per-execution inputs and require exact VCS/native synthesis agreement. A later
mutable elaboration cannot substitute for actual compiled inputs. Audits check
current sources, execution, all cuts, sanitizer/negative logs, compile arguments,
native DCP CRC/identity and resource inventory. Fresh EDA audit passes and all
**14** `verify_checkpoint_top_audit` tamper cases reject. Historical iteration-180
receipts and its failed mutable-output audit remain unchanged.

After full Scala elaboration, run on EDA with `vcs-env.sh` sourced last:

```bash
python3 -m tools.checkpoint_formats.tests.verify_synchronous_bank_vcs \
  --generated automations/checkpoint_loop/runs/aws-f2/iteration181/scala/bank/synchronous \
  --out automations/checkpoint_loop/runs/aws-f2/iteration181/synchronous-reverify
```

Iteration 180 adds opt-in `CheckpointCaptureTopKey` / `CheckpointCaptureTopBinding`.
FPGATop registers the Widget on its real control interconnect and appends its
stream after existing bridge streams before constructing the CPU stream
engine. The binding executes after SimWrapper and bridge module construction,
in the parent hardware context. A generated descriptor ROM is mandatory;
owner, counter and bank ports have no default acknowledgements or tieoffs.
Missing hardware connections fail FIRRTL initialization checking. Stock
recipes keep capture disabled and complete CPU ownership remains unsupported.

`CheckpointCaptureTopSpec` emits an explicit generated-storage fixture in the
real FPGATop, alongside an existing diagnostic bridge stream. The EDA runner
`verify_checkpoint_top_vcs` uses only public MMIO/AXI4 and functional ports.
All **7,858** checks pass on **33** words at **C=109 / 167 / 305**, including
**660** stalled DMA cycles, **1,926** frozen edges, a full two-frame stream
FIFO, missing owners, reset/write freeze, abort/drain/reuse and independent
access to the original stream. Each cut passes **66** decoder negatives and
**5,532** ASan/UBSan host checks. The complete top-generated checkpoint registry
constructor compiles against production headers. An actual bank-response bit
flip stops at the first data word at **C=109** while frozen. Full fixture
waveforms, source/generated hashes and raw logs are under
`runs/aws-f2/iteration180/top-vcs-corrected/checkpoint-top-yxwt2f1i/`
(relative to the loop). Native Vivado synthesizes this integrated fixture
FPGATop at **3,528 LUTs / 1,383 registers**, estimated setup slack **+4.282 ns**
at 140 MHz. This is out-of-context fixture synthesis, not a Rocket image.

After elaborating `CheckpointCaptureTopSpec` with
`-Dcheckpoint.widget.out=DIR`, run on EDA with `vcs-env.sh` sourced last:

```bash
python3 -m tools.checkpoint_formats.tests.verify_checkpoint_top_vcs \
  --generated DIR/top/enabled \
  --out automations/checkpoint_loop/runs/aws-f2/iteration180/top-reverify
```

Iteration 177 adds `CheckpointCaptureTransport.sv`, connected to the existing
`CheckpointCaptureCut.sv`. This is a synthesized component with an EDA VCS
fixture, **not a CheckpointBridge integrated into the Rocket FPGA image**.
The exact CPU recipe and its initialized manager configs remain unchanged.

Iteration 178 adds `GeneratedStateBankAccess`, `CheckpointCaptureWidget` and
native `checkpoint_capture_t`/`checkpoint_capture_session_t`. Generated storage
and the real FireSim control/stream interfaces now have independent component
verification. FPGATop registration, complete Rocket ownership/mapping and
physical checkpoint-image deployment are still required; these classes do not
enable CPU admission by themselves.

Iteration 179 adds `CheckpointCaptureDescriptors.fromGenerated`: complete
ordered bindings and both reference/instrumented circuit hashes are checked
against the independent inventory before one immutable descriptor set is
constructed. `CheckpointCaptureDescriptorROM` returns invalid all-zero outputs
for every out-of-range 32-bit ordinal. When Widget parameters include this
descriptor set, its hash/count must match the transport and its internal ROM
drives descriptor inputs; external descriptor pins have no authority in this
mode. The existing external-descriptor mode remains a component interface.

The same immutable descriptors generate host `checkpoint_capture_manifest_t`
metadata (including exact little-endian digest bytes) and the actual
`checkpoint_capture_t` registry constructor. Headers retain binding SHA256,
StateIDs, MMIO base, stream allocation and transport source hashes. This joins
transport/driver compatibility; it does not supply functional-memory or host
snapshots, complete CPU ownership, or automatic checkpoint publication.

`verify_generated_capture_network_vcs` checks actual generated banks connected
to that ROM and Widget. No handwritten bank-data or descriptor source supplies
the captured state. An independent functional-input oracle checks every word
through reset/write freeze, DMA stalls, missing fixture owners and abort/reuse.
Three cuts pass **1,014** checks, **48** bank reads, **49** decoder negatives
and **2,940** ASan/UBSan host checks per cut. The exact generated C++ initializer
validates the real VCS streams independently. Deliberate semantic bit corruption
stops at the first state word at **C=30**, frozen before publication. This is
finite component checking, not live CPU comparison. Full component VCD,
canonical VCS-origin fixture images and original source/command receipts are in
`runs/aws-f2/iteration179/network-vcs-final/generated-network-0fzl_g1v/`
(relative to the loop). The native localhost bank/Widget-with-ROM synthesis
reports **138 / 1,725 LUTs**, **67 / 692 registers**, and estimated setup slack
**+6.298 / +4.425 ns** at 140 MHz for the F2 part. Full Rocket synthesis/P&R,
AFI creation, deployment and hardware capture remain pending.

After elaborating `CheckpointCaptureDescriptorsSpec` with
`-Dcheckpoint.widget.out=DIR`, run on EDA:

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_generated_capture_network_vcs \
  --generated DIR/generated-network \
  --out automations/checkpoint_loop/runs/aws-f2/iteration179/network-reverify
```

The opt-in LowForm generator checks the entire current input inventory before
specializing modules per instance. It reads actual registers and added logical
asynchronous RAM ports, gates functional reset/update/write with `ckpt_freeze`,
and returns registered responses held until consumption, even after release or
abort. Dedicated `ckpt_reset` is independent of functional reset. State wider
than 64 bits/deeper than 65,535 words, unsupported readwrite RAM policies,
opaque/derived-clock/analog state and annotations
outside the explicit contracts above reject. Derived CombinationalPath caches
are invalidated and recomputed. The generated simulator and semantic StateIDs
remain separate. The fixture verifies 16 storage words; no whole-CPU coverage
is inferred.

The controller accepts a capture only while idle, freezes on the accepting
edge, waits for every declared owner, and reads logical bank words through
request/response handshakes. Descriptors come from an immutable generated ROM:
manifest ordinal, bank, slot, logical width and depth. Each descriptor is
latched before any bank request. Exactly one read can be outstanding. Bank
request and DMA payloads remain stable under backpressure; response latency
need not be fixed. Data with nonzero width padding rejects. Unsupported or
missing descriptors reject explicitly; this component supports widths 1–64,
1–65,535 entries, 8-bit bank and 16-bit slot selectors. Automatic wide-state
chunking and complete Rocket ownership remain required work.

The transport clock continues throughout freeze. All functional writes, resets,
token/channel movement, memory updates and host owners must honor the same
cut. Functional target reset must not reset the cut/transport controller.
Resetting the controller requires coordinated reset of the bank and DMA
endpoints; resetting it alone is not a cancellation protocol. An accepted bank
request must produce exactly one response, including on failure or abort.

An owner error, lost freeze, cycle drift, invalid descriptor, bank error or
noncanonical data invalidates the entire unpublished DMA stream and retains
freeze. An explicit abort releases owners and invalidates/flushes the stream.
If a bank read was already accepted, its response is discarded and a new
capture remains inadmissible until draining completes. An unresponsive endpoint
therefore prevents reuse rather than contaminating a later snapshot. The
bank must latch everything needed to return that response before accepting
its request. Premature publication reports an MMIO error and fails frozen.

The transport's MMIO interface is a single-request protocol with a backpressured
response; the global Widget adapts it to real FireSim NASTI. Register addresses
are byte offsets, all transfers are 32 bits, and writes to read-only/unaligned
addresses reject. Command values are exact, not composable bit masks.

| Address | Operation | Meaning |
| --- | --- | --- |
| `0x00` | write | `1` start, `2` publish/release, `4` abort |
| `0x04` | read | bit 0 ready, 1 freeze, 2 read enabled, 3 complete, 4 failed, 5 draining |
| `0x08` | read | bits 0–4 cut errors; 16 invalid descriptor, 17 bank error, 18 padding error, 19 sequence overflow |
| `0x10`, `0x14` | read | low/high halves of authoritative target cut |
| `0x18`, `0x1c` | read | low/high halves of transferred state-word count |
| `0x20` | read | generated entry count |
| `0x24` | read | complemented running CRC32C |
| `0x40` … `0x5c` | read | manifest SHA-256, least-significant 32-bit word first |

The global Widget wraps this request/response adapter in actual 32-bit FireSim
NASTI, independently buffers AW/W and holds all responses. It allocates a
256-byte control region and a real 512-bit StreamToHostCPU. Its clock continues
during the common freeze. Invalid/alignment/width/strobe/burst operations return
SLVERR without forwarding side effects. It adds these Widget-only registers:

| Address | Operation | Meaning |
| --- | --- | --- |
| `0x60` | read | bit 0 invalid shared stream; bit 1 lifetime frame-count overflow |
| `0x64` | write | exact `1`: acknowledge drain, only if producer quiescent and host count equals produced count |
| `0x68`, `0x6c` | read | cumulative accepted DMA frame count; low read latches a coherent high half |
| `0x70`, `0x74` | read/write | host cumulative consumed/discarded frame count for drain acknowledgement |

The produced counter survives capture, publication and abort, saturating with
sticky failure on overflow. Only a coordinated endpoint/stream reset clears
its epoch. An empty nonblocking pull does not establish drain completion;
the host must consume/discard every accepted frame and provide the exact
count. A new start stays blocked until acknowledgement succeeds. Shared
stream queues are not reset by a transport abort.

DMA frames are 64 bytes, little-endian at each integer field. `dma_last` marks
only the trailer. A generated manifest hash must be nonzero. The stream is a
transport envelope, independent of canonical checkpoint container formats.

| Bits | Common / header / data / trailer |
| --- | --- |
| 0–63 | magic bytes `FSMCKPT1` |
| 64–79 | version 1 |
| 80–95 | type: 1 header, 2 state word, 3 trailer |
| 96–159 | authoritative target cut |
| 160–223 | header zero; data zero-based word ordinal; trailer total words |
| 224–255 | header entry count; data entry ordinal; trailer CRC32C |
| 256–287 | header manifest hash starts at bit 256; data logical address |
| 288–303 | data logical bit width |
| 304–311 | data bank |
| 312–327 | data slot |
| 328–335 | data status, currently zero |
| 336–399 | data word |
| 400–511 | data reserved zero; header manifest hash ends at bit 511 |

Trailer bits above 255 are zero. CRC32C uses the reflected Castagnoli
polynomial `0x82f63b78`, initial state `0xffffffff`, and final complement.
It covers every byte of the header and every data frame, excluding the
trailer. The host decoder also independently checks the trailer's common
fields, count and reserved bits. CRC detects transfer corruption; it does not
authenticate provenance or establish complete state ownership.

`tools/checkpoint_formats/fpga_transport.py` validates complete length, manifest
compatibility, cut labels, word order, selectors, widths, padding, reserved
bits and CRC before returning any state. Its Level-2 adapter produces the
existing canonical `.rtlckpt` representation. This does not implement Level-1
ownership. The new C++ driver uses actual MMIO and StreamEngine calls, with
page-aligned bounded nonblocking transfers, independently supplied immutable
descriptor metadata, complete frame/CRC/cut/count validation and an explicit
post-publication release. Raw state bytes are exposed only after validation.
Transfer faults poison the session; abort drains against the cumulative
hardware frame count. Unknown consumed byte counts require coordinated reset.
The global coordinator must still snapshot all software/memory owners,
validate both independent images and trace, atomically publish without
overwriting valid history, and then authorize release. The new driver retains
the default unsupported aggregate checkpoint schema.

Fresh EDA verification (source the remote build environment first, then
`vcs-env.sh` last):

```bash
source automations/checkpoint_loop/vcs-env.sh
python3 -m tools.checkpoint_formats.tests.verify_fpga_transport_vcs \
  --out automations/checkpoint_loop/runs/aws-f2/iteration177/transport-verified
```

The runner creates a unique directory with frozen sources, compiler argv,
native logs, fixture manifest/binding, actual public-port frames, canonical
component image and hashes. The fixture's independently sampled register/RAM
values are compared against every handshake. It exercises delayed bank reads,
DMA/MMIO stalls, five complete publications, malformed descriptors, owner
failures, lost freeze, cycle drift, stale-response draining, early publication
and fresh capture after failure. The strict host decoder rejects 39 damaged
variants of the actual VCS-produced stream, including rechecksummed semantic
framing corruption. This finite component test establishes no CPU live-shadow
or physical FPGA acceptance.

Local native Vivado synthesis uses `capture_transport_synth.tcl`,
`xcvu47p-fsvh2892-2-e`, 16 owners and 1,024 entries, with 140 MHz constraint.
The component uses 2,055 LUTs and 423 registers. Estimated post-synthesis
register-to-register setup slack is +4.816 ns; this is not routed F2 timing.
The HDK setup must be sourced from its own repository directory. Run through
the local F2 helper with backend `f2`; never synthesize on EDA.

Fresh iteration-178 runners (all VCS on EDA) are
`verify_generated_bank_vcs`, `verify_checkpoint_widget_vcs` and
`verify_fpga_capture_host` in `tools.checkpoint_formats.tests`. Generated inputs
come from `GeneratedStateBankAccessSpec` and `CheckpointCaptureWidgetSpec`;
native localhost synthesis uses `capture_components_synth.tcl`. Each runner
retains exact sources/generated artifacts, raw commands and native logs under
loop `runs/`. No fixture image is relabeled as FPGA origin.

Next: connect the registered FPGATop binding to the real compiler flow with complete
independent simulator/semantic mappings and descriptor ROMs, support the real
Rocket memory/width/annotation cases, connect global write/reset/token freeze,
and join complete
functional-memory/FASED/host ownership. Then build the exact checkpoint-enabled
Rocket recipe on localhost, create/bind AFI/AGFI and driver manifests, deploy
and capture actual F2 execution at every required cut. FPGA-reference
continuation, independent fresh EDA Level-1/Level-2 restores, sustained live
comparison beyond trace, waveforms and rolling FPGA recovery remain pending.

Use the existing [F2 workflow](aws-f2-workflow.md) and official
[custom-image guide](https://docs.fires.im/en/latest/getting-started-guides/aws-ec2-f2-getting-started/building-a-firesim-afi/).
