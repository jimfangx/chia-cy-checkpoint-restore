# TSI bridge host control ownership

Iteration 99 adds `firesim.tsi.bridge-control.v1` to the production
`tsibridge_t`. The bridge delegates its original init/tick decision sequence to
`tsi_bridge_state_t`; status queries use the same completed-call guard. This
component owns initialization, the remaining reset-delay ticks and the one-time
fast-loading transition. Its immutable identity binds the selected TSI number,
all nine bridge MMIO addresses, memory availability/offset/beat width, the exact
selected TSI arguments, configured steady/loading steps and initial wait/fast
settings. The image has two mutable 64-bit words: remaining wait and initialized/
fast flags. It contains no process addresses, callback objects or contexts.

Load validates the complete identity, length, cursor and lifecycle before
assigning either word. Unknown flags, oversized waits, partial uninitialized
states and a fast transition before the reset delay drains reject. Save,
validate and load do no MMIO, FESVR construction/advancement, serial delivery,
request dequeue or target-time work. Every init/tick/status call guards the
whole callback sequence; active/reentrant access rejects, and any escaping
callback exception permanently rejects checkpoint access to that instance.
Repeated init and uninitialized operations reject before calling services.

The existing control decisions are preserved, including the original loading
step computed before argument parsing (2,004,765 even with early-fast enabled).
Changing that behavior is separate work. The independent oracle uses the
original control flow and externally scheduled service results, covering both
fast settings, waits 0/1/8, incomplete token steps, request bypass, pending serial
data, loaded transitions, termination and status queries. All completed-call
cuts are restored into separate native sanitizer and VCS processes. Every image
word and continued callback/label is compared with the oracle; no services are
called during restore/readback. Reentrancy is attempted at each callback, and
exceptions are injected at every init/tick/query callback and after a reset-delay
cursor decrement. A valid wait-cursor corruption checks the first differing
callback boundary before acknowledgement. These are component fixture labels,
not Rocket target cycles.

The production bridge exposes const inspection of this owner. Its aggregate
checkpoint schema remains unsupported. The generated bridge RTL and its FIFOs,
TSI serial queues and suspended read destination, HTIF caller/context, program
loader/cache-flush/init-access progress, FireSim idle/reset cursors, device
state and cross-owner coherence remain separate requirements. Restoring this
component does not construct or restore FESVR. The current identity deliberately
binds the complete selected argv; a future aggregate must audit canonical
configuration separately from its capture/restore control options before enabling
CPU migration. Matching this component alone cannot authorize such normalization. Copying `ucontext`, replaying
`start()` or restoring a host program counter would not satisfy that contract.

The actual installed-FESVR transport check independently compares all 24
complete production bridge-control payloads across two beat widths and both
native/VCS backends, including construction, initialization and four program
loader ticks. Capture and validation perform no MMIO. All 24 actual images also restore in
both fresh native sanitizer and VCS processes (48 complete zero-edge readbacks);
those processes have no services object and cannot call FESVR or MMIO.
Full four-hart workload
controls, complete pre-FAME storage probes and prior regressions retain their
own scope; they cannot establish CPU checkpoint acceptance.

Exact native results, source/workload hashes, executable commands and remaining
work are in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics are
under `automations/checkpoint_loop/runs/m11-iteration99/`. Complete Rocket
Level-1 continuation and independent Level-2 captured CPU replay remain pending.
Physical FPGA validation and ASIC power remain deferred.
