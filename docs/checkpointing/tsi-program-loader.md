# TestChip program-loader routing owner

Iteration 106 moves FireSim's effective TestChip program-load phase and transport
selection into `firesim_tsi_program_loader_t`. The production FireSim override
keeps TestChip's initial target yield, enters load-memory mode immediately before
`htif_t::load_program()`, and leaves it immediately after return. Read/write and
cache-flush routing now consume this owner. FireSim's capability still selects
load-memory mode whenever the target supports it, as before. The base TestChip
private routing fields remain present but FireSim's overridden paths no longer
consume them. Standalone TestChip users are unchanged.

| Production caller | Routing and remaining caller state |
| --- | --- |
| `htif_t::start()` → virtual `load_program()` | FireSim owns the initial yield and loading interval; upstream `load_payload()`/ELF/symbol progress remains pending |
| ELF preload-aware memif → virtual chunk calls | FireSim selects load-memory queues in the loading interval; unaligned memif read/merge buffers and ELF destinations remain pending |
| `htif_t::clear_chunk()` → virtual writes | The same owner selects transport for zero-fill chunks |
| FireSim initialization read/write/MSIP | Owned cache-flush address and serial transport; the existing initialization caller/read/FIFO components retain progress |
| `htif_t::run()` private memif polling | Serial transport after loader return; HTIF tohost/fromhost caller buffers, response callback/queue and device state remain pending |

The `firesim.tsi.program-loader.v1` component image is 56 bytes: the existing
`WDGCKPT1` version-1/kind-23 header, two configuration words (effective load-memory
capability and cache-flush address), and one phase word. Phases are unstarted=0,
initial target yield=1, ELF loader active=2, and loader returned=3. Serial routing
applies outside phase 2 and whenever the capability is false. Cache-flush packets
retain the original 64-byte line walk, order and address words. Escaping loader
exceptions poison the component; save, validate, restore and routing then reject.
Malformed/configuration/phase checks finish before the live phase assignment.

This component owns transport selection and loader entry/return only. The ELF
payload/symbol loader, memif partial-write buffers and caller return paths,
HTIF polling/fromhost/device/termination/signature state, contexts and complete
workload/build compatibility remain separate pending owners. Loading phase 2
does not authorize restarting or resuming the ELF loader. There is no complete
FireSim TSI restore API for this component, no new CPU checkpoint profile, and no
expansion of the existing four-owner initialization bundle.

The real installed-FESVR ELF regression captures the production owner at seven
suspended boundaries in native C++ and VCS: constructed, initial yield, waiting
for queued writes, waiting for a read response, half a read response, reset-wait
after the loader returned, and HTIF idle. Its independently expected phase words
are `0,1,2,2,2,3,3`. Existing request bytes, partial read/merge, reset and idle
checks remain mandatory. Fresh native ASan/UBSan and VCS component processes
restore every captured image and read back the whole owner before any service,
context entry or target edge. They exercise all four capability/cache-flush
policies and phases, malformed prefixes, every header/configuration bit,
incompatible owner identity, extra bytes, invalid phases, illegal transitions
and poisoned-owner rejection. A structurally valid phase corruption must report
its first unacknowledged component boundary. These labels are not CPU cycles.

Exact commands, workload identity, native results and remaining CPU acceptance
requirements are recorded in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).
No complete Level-1 continuation or captured Level-2 CPU replay is inferred from
these component checks or uninterrupted four-hart controls.
