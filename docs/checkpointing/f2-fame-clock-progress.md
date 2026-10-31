# FAME consumed-token and launched-edge observations

Iteration 295 adds `--simulator-fame-clock-progress`. It requires exactly one
simulator inventory request and is consumed at the actual `FAMETransform`
construction site. Unselected builds keep their existing FAME rules. The
observer appends state and read-only wires without replacing original rules,
adding clock gates or changing the original module interface.

FAME consumes a new clock token while launching the previously latched token.
`ClockBridgeModule.tCycleFastest` counts tokens sent by a bridge which can run
ahead; it cannot establish the cut. The new observer separately retains:

- completed FAME steps, gated by completion and deasserted host reset;
- per-clock consumed-token counts, using the incoming clock flag;
- per-clock applied-edge counts, using the exact original native-gate CE;
- each original pending clock flag and both observation pulses;
- sticky overflow, with all 64-bit counts saturating rather than wrapping.

The two-clock Rocket hub adds five 64-bit counters and one overflow bit. These
are ordinary host-clock registers, preserved by actual FIRRTL renames and
included in generated Level-1 inventory. They need capture ownership alongside
all other simulator state; they are independent of original semantic Level-2
storage. Host reset restarts observer counts. The original target reset and
functional registers retain their existing behavior.

A Level-1 restore must load these counters before advancement and must not
reset them afterward to make cycle labels agree. Level-2 images exclude this
simulator-only state. A future collector binding must independently read back
all 321 bits and reject overflow. FIRRTL preservation alone does not retain an
unused observation in an FPGA image: the production bank consumer must actually
be connected; the current native component uses explicit verification probes.

Before overflow, an initialized local model obeys
`consumed[clock] = applied[clock] + pending[clock]`. This exposes the initial
token priming step, variable clock flags and stalls. It does **not** establish
a global semantic boundary: satellite/model progress, token/channel positions,
FASED timing, memory and host owners must still agree at the physical cut.
There is no authoritative scalar target-cycle output or automatic collector
acknowledgement. The iteration-294 root collector is not yet bound to these
internal observations. Overflow must invalidate any future cut binding.

The next binding step must carry exact observation and clock-gate reference
targets through actual compiler renames and final emission, then connect them
to the common-cut owner protocol. Name matching or selecting an arbitrary
64-bit root output does not establish that role mapping. FASED/native timing
owners and channel positions still need independent observations.

The verification sibling comes from the real FAME transform and native gate
specialization. A second compiler-emitted hierarchy has no observers. Native
verification adds only generated probe outputs so synthesis retains the
internal observations; those outputs are not a production capture transport.
EDA VCS uses the exact native vendor models, complete debug visibility,
independent actual gate-edge counting, original-state arithmetic and the
uninstrumented hierarchy. Producers retain payloads under backpressure.
Component-only initialization and impractical 64-bit overflow injection are
explicit testbench operations, never FPGA capture or restore evidence.

The execution covers 512 active host steps, stalls, different clock schedules,
each of five counter overflows, sticky failure/reset behavior and observation
corruption before the next comparison acknowledgement. A separate raw-VCD
auditor reconstructs all 321 observer register bits from input handshakes and
vendor gate edges and checks deliberate state-bit mutations. These are
component checks; physical FPGA and CPU migration acceptance remains pending.

Exact current commands, source manifests, compiler outputs, native reports,
EDA logs, raw debug waves, diagnostic attempts and closure receipts belong
under `automations/checkpoint_loop/runs/aws-f2/iteration295/`. The current exact
Rocket compiler trial enables this option while preserving the whole-image
admission guards. Reuse iteration 194's retained localhost build invocation.
Production clock/reset/collector ownership, ungated native transport, complete
functional-memory/FASED/host coverage, checkpoint-enabled AFI, four active
physical cuts, paired CPU zero-edge/finite/live continuation and rolling
hardware recovery remain required.

Current validation passes 363 Scala tests / 59 suites plus sixteen preparation
checks, 409 Python and 61 manager tests, including the retained EDA sanitizer /
host / bank / FCFS / cut scope. Native observer P&R at unchanged 140 MHz closes
+2.768/+0.051 ns, preserving 344 sequential identities and all 407 routable nets;
resources are 137 LUTs / 342 registers / two original gates. Full-shell timing
remains unmodeled. EDA SP2 passes 6,658 healthy comparisons over 512 host steps,
335 completed FAME steps, 177 stalls and 253/108 actual clock edges. All five
independent overflow cases pass; the independent auditor rejects all 321
raw-readback bit mutations. Observation corruption diverges at step 17 with
16 comparisons acknowledged. All seven raw full-visibility waves are retained. The exact Rocket
compiler emits all six observer registers (321 bits) and reaches the unchanged
missing-FASED-physical-CE-owner guard. No image/AFI or hardware checkpoint is
emitted, and no physical CPU migration acceptance advances.
