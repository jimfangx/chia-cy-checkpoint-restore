# HTIF startup metadata preparation

Iteration 109 adds `firesim_tsi_t::save_startup_metadata()` and
`prepare_startup_metadata()` for the single explicit-path ELF/default-device
configuration. This is a metadata component, not a complete HTIF, TSI or CPU
checkpoint. Complete CPU admission remains disabled.

Ordinary supported loads pass a sealed, process-local copy of the ELF to the
installed FESVR loader. The copy survives loader/memif yields, and its descriptor
is never serialized. The component image binds every ELF byte and every original
argument except argv[0], plus the resolved entry and complete ordered symbol map.
It does not merely bind a filename. Diagnostic reports separately hash the ELF,
installed archive, headers, sources and native executables.

Capture requires the existing guarded suspended polling cut. Preparation requires
a pristine object with no initialized host coroutine and seven unchanged caller/
transport components. A no-target-memory FESVR probe constructs the expected
complete image from the local ELF. Any image mismatch rejects before changing
HTIF metadata or peer owners. Invalid checkpoint bytes never enter the ELF parser.
After validation, the installed `htif_t::load_program()` reconstructs its private
entry/mailboxes/symbol table through a preloaded-memory override. It bypasses
TestChip's loading yield and never calls reset. Target reads, writes and reset
throw if attempted during preparation. Every resolved address/name and entry/
mailbox value is read back through installed HTIF accessors; duplicate-address
symbols follow HTIF's first-name-in-map rule.

A prepared object remains unusable for execution: `tick()`, repeated preparation
and polling inspection reject. No host context, program-load phase, initializer,
serial reader/FIFO or load-memory queue is restored by this API. Failed installed
metadata preparation poisons the object. Invalid images leave it pristine and a
subsequent valid preparation is tested.

Supported preparation excludes `none`, non-explicit ELF search paths, every long
option/custom-device/chroot path, extra payloads, symbol ELFs and signature
options. Ordinary execution retains its installed behavior for these options.
Expected XLEN policy, library/build compatibility, stop/exit/signal state,
signature ownership, default-device descriptors/terminal state, active memif or
syscall continuations, the polling dispatcher and coroutine replacement still
need complete aggregate ownership. This API must not be used to admit a CPU
checkpoint profile.

`verify_tsi_startup_metadata_vcs` uses the production FireSim/TestChip caller and
installed FESVR archive. Both source processes load a real two-segment ELF,
perform its partial-write read/merge, reach a guarded polling cut, capture the
metadata, then finish the default syscall PASS through HTIF stop. An independent
Python ELF oracle checks every serialized byte. Each producer's image is prepared
in fresh sanitizer and VCS processes, including after all byte-flip and truncation
rejections. Complete pre-service metadata and seven-peer readbacks are saved.
Changed ELF bytes at the same path, changed arguments and all excluded option
families reject without target services or partial metadata publication.

These host tests advance one remaining owner. They do not establish a coherent
CPU cut, fresh Level-1 CPU continuation, independently captured Level-2 CPU image
or finite captured-boundary replay. See [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md)
for exact evidence and pending acceptance work.
