# Restricted TSI bridge context preparation

Iteration 157 connects the restricted context image to `tsibridge_t` without
adding a complete bridge checkpoint schema. `capture_restricted_context()`
returns owned metadata, bridge-control and sixteen-owner context bytes. The
context envelope retains its build binding and ordered owner validation.
Capture runs on the FESVR creator and checks the control and complete context
again before returning. Only owned bytes may cross to the VCS thread.

`prepare_restricted_context()` prepares a private FESVR instance and matching
control on the destination creator. It validates the complete startup metadata
and context, including the actual provider lifecycle, without publishing a
provider pointer, entering a native coroutine, issuing MMIO, replaying startup
or touching target memory. The supported boundary follows initialization,
wait ticks and fast loading: control must be initialized, wait must be zero,
fast loading must have ended, and FESVR must be loaded in host and target.
Earlier bridge phases remain explicitly unsupported by this adapter.

The single-use candidate rechecks the creator, private aggregate, startup
metadata, signal admission and fresh destination before publication. All
throwing checks and allocations precede the pointer/control swaps. Competing
candidates and changed destinations reject. The destination bridge must outlive
its candidates. After publication the actual bridge dispatches its FESVR
advance through restricted context resume; ordinary tick admission remains
unchanged. Restored bridge tick/status/capture calls check the creator before
control or MMIO access. The aggregate checkpoint schema remains unsupported.

Preparation isolates HTIF's argument parser. Each attempt gets private strings
and a null-terminated pointer array; a scope restores `optind`, `opterr`,
`optopt` and `optarg` on success and failure. The allocation pilot demonstrated
that HTIF can leave permissive `opterr` state on an exception; copying argv
alone did not repair retries. The installed syscall constructor also duplicates
stdio before allocating descriptor vectors. A constructor-scoped Linux descriptor
guard retains `/proc/self/fd` through construction and closes newly created
descriptors on failure without opening another directory or allocating C++
objects during cleanup. An uninspectable cleanup fails the process. Dynamic
HTIF RFB/disk/chroot options reject before construction. The installed library
is untouched. Callers must suspend all other descriptor operations and argument
parsers and have no active libc getopt continuation. Tests compare complete
descriptor tables and all four exposed parser globals after every failed
attempt. This does not snapshot libc's private parser state or establish
process-wide exclusion. Normal provider construction installs HTIF signal
actions; complete process signal-action ownership remains outside this adapter.

The native ASan/UBSan and VCS test links the actual production bridge, loadmem
widget and exact recipe's retained lifecycle provider. A serial MMIO device
feeds the independently retained context operation plan. Every completed
bridge boundary reads back all context bytes and bridge control before any
RTL edge. Its reference stops where the actual bridge reports host termination;
the standalone context oracle's later artificial response draining is not a
production bridge action. Sources are retained actual TSI component captures,
not complete Rocket simulator captures. Mutation cases change actual semantic
syscall image bytes and require the independently expected first divergent
serial boundary without target acknowledgement.

Complete Rocket Level 1 remains disabled. This API supplies creator-side
bridge/provider preparation and publication; the complete simulator coordinator
must still join it with generated RTL/FAME/channel, other bridges, functional
memory and driver/runtime state at one coherent cut. Production process-wide
thread/signal/descriptor/parser exclusion remains pending. Level 2 remains independent.
BOOM and Saturn remain pending; standalone Shuttle, physical FPGA validation
and ASIC power remain outside this increment. See cpu-checkpoint-matrix.md for
selected native receipts and executable commands; diagnostics stay under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration157/`.

Integration points for the next increment:

* `simif_emul_t::begin_restored_load()` still rejects CPU-managed streams and
  any empty-schema runtime owner. `tsibridge_t` deliberately retains that empty
  aggregate schema, so complete Rocket restoration still rejects there.
* `start_driver_impl()` creates the driver worker after the existing VCS-side
  restore setup. A complete CPU coordinator must reserve that worker under the
  pre-edge hold, construct/prepare the private TSI on it, and exchange immutable
  observations with VCS. It must not prepare TSI on the VCS thread and then
  transfer its mutable owner/candidate references to the driver.
* The settled driver diagnostic already freezes software observations on the
  creator. Its public polling path does not yet collect this bridge context
  image. Capturing the new component by itself does not freeze generated RTL,
  FAME channels, harness banks, stream AXI, functional memory or other drivers.
* The bridge candidate's atomic publication is a component contract. Its
  throwing final checks cannot be interleaved with already-published simulator
  peers. A complete coordinator needs a validated, jointly guarded publication
  across all owners before releasing either worker or RTL clocks.
