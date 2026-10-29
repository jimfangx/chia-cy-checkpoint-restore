# Synchronous checkpoint access to original queue RAM

Iteration 269 replaces the local shell bank's extra asynchronous checkpoint
reader for a narrow class of original synchronous queue memories. The previous
iteration's strict localhost Vivado BLOCK-policy rejection is retained under
`runs/aws-f2/iteration268/`; it remains a failed synthesis attempt.

`NativeSynchronousMemoryReadout` supports one original reader and writer,
one-cycle read/write latency, write-first semantics, an always-enabled reader,
and one common ungated functional clock. The access clock must be tied to that
same running raw clock. Unsupported shapes and clocks reject explicitly.
Existing other bank profiles retain their existing implementation.

The version-1 address-register form still failed strict native BLOCK and exact
Rocket ULTRA policies in iteration 269; both syntheses fell back to LUTRAM.
Their original failure receipts and source snapshots remain under this iteration.
Version 2 emits an Old/data-registered physical reader and adds raw-clock,
full-width collision-data and collision-hit registers. The hit includes the
actual freeze-gated write enable, write mask and current native read/write
address equality. Registered forwarding reconstructs the original New/write-first
public result, including immediately before freeze and at resumed execution.
The entry shadow captures that complete forwarded result; checkpoint payloads
use the raw physical RAM result while writes are held. The new data and
forwarding pipelines have no complete production capture/restore ownership.

The adapter retains the original native RAM port names and synchronous form.
It borrows the reader at request acceptance while functional owners are held,
captures the requested word on the next edge, and re-primes the reader with
the original saved address before completing the retained response. The
original materialized address register keeps its original logical StateID.
A raw-clock register tracks whether the current RAM output belongs to a
borrowed read; a shadow preserves the original public output during that
interval. Requests outside hold return an error without suppressing functional
execution. Premature release returns an error and restores the public reader
on the first resumed functional edge. Endpoint reset cancels the request and
primes the reader before accepting another request.

Selectors and word/chunk addresses latch on acceptance. Response data/error
remain stable under backpressure and after release. The sidecar records the
three-edge latency, raw-clock obligation, retained original ports and prime
contract. Full shell validation independently regenerates the transformation
and rejects changed equations, policy or ownership. New adapter registers
remain transport state; this component does not establish their complete
production capture/restore ownership.

The reduced three-queue fixture selects two original queues and leaves the
third execution unchanged and active. Its independent software oracle checks
all original RAM words, pointers, full bits and read-address owners, every
public queue output, four cuts, selector mutation, retained responses,
functional reset under hold, reset in each transport phase, premature release,
and directed write-first collisions before capture and at resumed execution.
Native synthesis must enforce the original BLOCK policy in all three queues
and reject distributed fallback. EDA VCS consumes those exact native inputs,
retains full debug waves and rejects a compiled first-word corruption before
acknowledgement. Current commands and results are recorded under
`automations/checkpoint_loop/runs/aws-f2/iteration269/`.

BLOCK component evidence cannot establish Rocket's 6144-by-512 ULTRA policy,
complete state coverage or a physical checkpoint. Physical CE/common-cut,
live transport, functional memory, host and pre-FAME ownership remain required
before full-image admission, localhost image P&R/AFI, deployment, FPGA-origin
paired migration, sustained live clean RTL and rolling hardware recovery.

Final version-2 native results: the reduced fixture maps each selected and
untouched queue to two RAMB primitives, totaling six BRAM tiles / 2,017 LUTs /
803 registers. The exact original Rocket Queue_56 source maps its 6144-by-512
RAM to 16 URAM / zero BRAM / zero LUTRAM, with 878 LUTs / 1,192 registers.
Final full compiler regression passes 327 tests / 51 suites plus twelve
preparation checks; 337 Python, 52 manager, 47,219 sanitizer assertions,
27 native OOCs and 26 native-bound fresh EDA SP2 scopes also pass. Thirteen
metadata negatives include the original eight plus bank policy/hash/latency/
port and canonical-byte checks. All actual hardware migration cuts remain
pending; these results establish native component feasibility and readout only.
