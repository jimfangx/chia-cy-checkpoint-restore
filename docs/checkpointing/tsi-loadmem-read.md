# TSI load-memory read ownership

Iteration 96 introduces `firesim.tsi.loadmem-read.v1` in the production
FireSim TSI program-loading path. This is one Level-1 component owner.
Complete TSI/FESVR migration and the Rocket checkpoint profile remain pending.

`generators/firechip/bridgestubs/src/main/cc/fesvr/loadmem_read.h` owns the read
phase (idle, drain previous writes, issue, receive, complete), 64-bit address,
byte length and every consumed response word. The number of stored words is
the response cursor. Its payload contains no process addresses or destination
pointers. Configuration binds four-byte words and a 4,096-byte maximum request.
The actual FESVR chunk maximum remains 1,024 bytes. Requests must have nonzero
aligned lengths and aligned addresses, and their address range must not wrap.

The operation first waits for previous load-memory writes to drain, enqueues
one read, consumes each returned word once and retains the completed result
until its caller acknowledges it. `firesim_tsi_t::load_mem_read` uses this
machine, yields only when the original loop would yield, then copies the result
to its original destination and finishes the operation. Callback-active and
interrupted calls reject checkpoint access. Response capacity is allocated
before issue/load, so consuming a response cannot trigger an allocation.
Every restore parses and allocates the entire candidate before changing state;
save, validation and load perform no MMIO, request issue or response dequeue.

The request/response queues remain separate owners:
`loadmem_write_reqs`, `loadmem_read_reqs`, `loadmem_write_data` and
`loadmem_out_data`. A complete TSI image must bind those queues to this operation
and preserve the suspended HTIF caller/destination, program-load progress,
serial queues, idle/reset progress, host context and devices. No raw `ucontext`
or callback-pointer image can reconstruct that caller in a fresh process.
`loadmem_read_owner()` exposes only const component inspection; it does not
enable an aggregate TSI checkpoint or provide a parent-context restore hook.
The TSI bridge continues to inherit the unsupported checkpoint contract.

Iteration 97 fixes and independently tests the bridge's multi-beat read helper;
see [tsi-loadmem-transport.md](tsi-loadmem-transport.md). The iteration-96
integration below still exercises only an eight-byte read. Its larger component
requests exercise the operation owner with fixture IO. Transport correctness
and read-operation ownership are separate evidence; neither reconstructs HTIF
or enables the complete CPU checkpoint profile.

Iteration 98 groups the four production request/data/response queues and a
partially drained write into one pointer-free owner; see
[tsi-loadmem-queues.md](tsi-loadmem-queues.md). The read-operation schema and
its independent evidence remain unchanged. Cross-owner validation, HTIF and
bridge transport ownership remain required before a complete TSI cut.

The native/VCS continuation suite independently expands the original drain,
enqueue and response-pop loop. It captures each completed component operation,
restores selected cuts in separate processes, reads both complete owners before
advancement and compares all subsequent calls, data and fixture-cycle labels.
The external queue scheduler is an explicitly separate fixture owner. All cuts
are exercised for 4/8/64/128-byte reads; 1,024/4,096-byte reads include every
phase, early/middle/late response cuts, completion and acknowledgement. These
are host-component labels and cannot establish any required Rocket CPU cut.

The integration suite also runs the actual installed FESVR archive with
production TestChip and FireSim TSI, in native C++ and VCS DPI. Its RISC-V ELF
has an aligned initial write followed by an unaligned upper-half write. This
forces a real eight-byte load-memory read, including a suspended one-word
response, before resuming the ELF loader and issuing the original reset serial
request. The independent audit checks all seven actual suspended owner images
per backend and the read/modify/write bytes. It does not restore HTIF itself.

Run from the Chipyard root; every nested native/VCS shell also sources the
environments and pinned compiler/license helper in this order:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration96/read-recheck
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs --out automations/checkpoint_loop/runs/m11-iteration96/fesvr-recheck
```

Exact selected evidence and remaining CPU acceptance requirements are recorded
in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Plans remain read-only;
physical FPGA and ASIC power validation remain deferred.
