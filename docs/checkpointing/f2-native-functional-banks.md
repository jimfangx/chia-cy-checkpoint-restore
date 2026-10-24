# Native functional storage banks

Iteration 225 adds an opt-in functional readout companion for the exact Rocket
recipe. `GeneratedStateBankAccess.generatePhysicalCompanion` regenerates the
complete native clock plan and original CE dependencies before instrumenting
concrete FIRRTL registers, memories and emitter-owned memory pipelines. It
retains the actual BUFGCE definitions and instances. Native gate analysis uses
an internal clock-provenance view; no transparent gate implementation enters
an emitted circuit. Metasim's synthetic gate-output registers are excluded
from this inventory. They cannot stand in for physical CE state.

The ordinary generator still rejects physical CE ownership. The new result
uses a separate inventory type and coverage scope, and the ordinary descriptor
factory rejects it. Complete capture, production freeze ownership, deployable
image and metasim restore support remain false. Revalidation checks exact native
definitions/paths, clock provenance, instrumentation hash and all admission flags.
The endpoint has its own always-running access clock and held-response protocol.
Its externally held functional freeze is a prerequisite, not an atomic cut proof.

`--simulator-native-functional-bank-probe` emits a separate sibling netlist,
with inventory, original source, topology, CE dependencies, generated source,
bank binding and both XDC files. It never replaces the recipe's normal image.
This requires the explicit whole-root inventory and physical clock-plan request.
The real XDC consumer runs before emission optimization, preserving native cell
constraints without giving those cells an invalid ground-signal `dontTouch`
interpretation. A real-recipe failure exposed this ordering issue; the failed
log is retained under `runs/aws-f2/iteration225/rocket-native-banks.log`.

The corrected exact Rocket compiler invocation succeeds. Its companion contains
**12,096** concrete storage descriptors and **619,013** 64-bit transfer words
(**4,952,104** payload bytes), plus three transport-owned response registers.
All three original native BUFGCE instances remain. This inventory is taken at
the companion's pre-emission source boundary; it includes state that the stock
final emitter may optimize away. It is not the older 11,459-entry final stock
inventory. The separate stock output and physical sidecars remain available
from the same successful compiler invocation.

The independent production auditor checks every emitted register/memory owner
and shape against the complete mapping, including all specialized instance
paths; only the three named response registers are outside the functional
inventory. It checks chunk selectors, source hashes, clock provenance, native
primitive membership, original CE dependencies and both emitted constraint files.
The original CE dependency audit still identifies external `F1Shim.reset` as
requiring a same-cut owner.

The full Scala scope passes **230** tests. A separate two-native-gate fixture
covers 65-bit counters, a 130-bit RAM and its old-read pipeline. Native localhost
Vivado 2025.2 synthesis retains both SYNC BUFGCEs and uses **848 LUTs / 390
registers**. At 140 MHz, OOC estimated setup/hold slack is **+5.840/−0.151 ns**;
the hold estimate does not meet timing. This is synthesis evidence only;
full-image timing closure and implementation remain pending.
Fresh EDA SP2 VCS passes **4,539** checks, four complete reads at logical cuts
**14/66/180/325**, **128** total words, **468** held-response stall cycles,
endpoint reset recovery and continuation through cycle **405**. Public ports
and an independent arithmetic/memory oracle compare against the unmodified
reference. A corrupt first expected word stops at cut 14/check 17; an
independently recompiled incorrect native CE connection stops at cycle 12/check
1. All three debug VCDs contain execution. Native/EDA auditing matches 26 inputs and 13 sources; six coherent
inventory/selector/owner/native-RTL substitutions reject. All sixteen localhost
component synthesis scopes and the full retained EDA sanitizer/FCFS/host/bridge/
bank/memory/clock/widget/router/reset/top scope pass. The complete new Rocket
companion also passes independent EDA auditing, matching all eleven bound
source/output hashes with the native audit.

Current execution receipts and raw commands are under
`automations/checkpoint_loop/runs/aws-f2/iteration225/`. The new tools are
`verify_native_functional_bank`, `audit_native_functional_evidence` and
`audit_native_functional_production` under `tools/checkpoint_formats/tests/`.

Next integration must compose the native functional descriptors and physical CE
bank from this same original circuit, connect the generated clock mask and
ungated bank/MMIO/DMA path, and bind every reset/external-writer/host owner.
Freezing a whole root that contains the live transport is insufficient. Complete
functional-memory/FASED/bridge/host/pre-FAME state and physical CE restore remain
required. Full localhost image P&R/AFI, active four-hart FPGA cuts, independent
paired zero-edge readback, FPGA-reference continuation, finite RTL replay,
sustained live RTL and rolling hardware recovery remain pending. No FPGA
checkpoint, capture-enabled AFI or CPU migration is established here.
