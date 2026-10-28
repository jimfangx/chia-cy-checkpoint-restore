# Opt-in NASTI adapter restoration

Iteration 264 adds a synthesizable, explicitly enabled restore interface to
`CheckpointNastiAdapter`. The production widget leaves it disabled: its generated
adapter has no restore ports, and its header still declares shadow restore
unsupported. This component does not resolve the complete transport, stream,
reset, host, memory, physical-clock or pre-FAME ownership contracts.

The enabled adapter suppresses all seven frontend/backend handshake outputs
while held or while any load is asserted. One accepted positive edge loads all
38 original registers from the existing 530-bit canonical observation layout.
The load requires hold, inactive reset and zero padding in every address/ID slot.
A rejected load writes no original register and permits no handshake, including
a load asserted outside hold. Reset has priority. The combinational accepted
and error outputs describe that edge; the component adds no original storage.
Holding this adapter is insufficient to stop its upstream AXI master or backend
response owner. A future supervisor must capture and restore those owners at
the same epoch before production integration can enable this port.

Scala independently enumerates every original low-FIRRTL register and width
with restoration disabled and enabled at 8/1, 32/4, exact-Rocket 32/12 and 64/64
address/ID geometries. The native localhost OOC test retains the corresponding
RTL, original raw-clock checks, utilization, timing estimates and DCPs. It is
component synthesis, not FPGA execution or full-image timing closure.

The EDA test uses six explicitly asserted component protocol cuts: partial AW
with queued AR, malformed W burst draining, outstanding backend work, held B,
partially consumed error R burst and a backpressured backend read. A donor
saves the original registers directly, independently of the exported vector,
and saves every register of an explicit test backend response owner. A separate
fresh VCS process loads those owners while held, independently reads every
original adapter register before releasing either interface and compares all
settled outputs, original state and backend bookkeeping over 3,000 subsequent
cycles. The driver mixes legal and bounded malformed transactions, retains
master VALID/payload under backpressure and asserts that retention. Every
continuation requires successful reads, writes, backend responses and stalled
backend requests; all boundary inputs are also compared. A xorshift generator
avoids the correlated low-bit LCG defect found during independent review.
These fixture text images are not `.fsckpt` or `.rtlckpt` files.

Additional checks exercise unrelated full-register payloads, every individual
padding bit, loads outside hold, reset priority, malformed images, semantic image
corruption and a separately compiled original-register restore defect. Direct
original-register VCD reconstruction independently verifies accepted loads,
held state, handshake suppression and the first compiled-defect bit before any
interface is released. Complete component debug waves are retained.

Execution receipts and exact commands are under `runs/aws-f2/iteration264/`.
See the current progress entry for final results and preserved failed attempts.
Exact production image admission remains closed until all owners are supported.
Full localhost P&R/AFI, checkpoint-enabled deployment, actual four-hart FPGA cuts,
FPGA-produced paired migration/live clean RTL and rolling recovery remain pending.

Final verification passes 319 Scala tests / 49 suites plus twelve preparation,
336 Python / 45 manager tests and twenty-one native / twenty-one fresh EDA SP2
component scopes. The adapter matrix independently compares 24 cuts / 72,000
cycles and rejects sixteen malformed/semantic/compiled-defect processes.
Fresh continuations total 3,580 reads / 2,956 writes / 6,536 responses / 6,792
request stalls, with matching donor counts and successful responses in every
case. Every restored process executes exactly 3,000 normal edges after complete
held readback; the independent compiled-defect oracle stops at responseData
canonical bit 426 with zero normal edges. Exact-Rocket 32/12 OOC uses 289 LUTs /
258 original raw-clock registers. Final source/input/receipt/resource integrity
and all retained waveform/physical/ASan/UBSan/FCFS checks pass. Complete FPGA
capture and CPU acceptance remain in progress.
