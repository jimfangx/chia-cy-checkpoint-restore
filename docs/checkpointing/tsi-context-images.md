# Bound TSI context images

Iteration 156 adds `firesim_tsi_context_image_t` to transport the existing
restricted sixteen-owner context aggregate as owned bytes. The caller supplies
the exact build SHA-256 and prepares startup metadata separately in the fresh
destination. Capture, preparation and publication execute on the TSI creator;
only bytes cross the VCS/driver boundary. The adapter deliberately does not
implement `checkpoint_owner_t` or grant complete simulator admission.

The canonical little-endian envelope uses widget kind 37, revision 1, sixteen
owners, a 32-byte build digest, the complete canonical startup metadata, then
ordered length-prefixed owner names and payloads. The metadata binds the exact
ELF, arguments, required XLEN, transport configuration and pristine sealed
terminal. Names are, in order: poll, program, init, host, read, serial,
loadmem-read, loadmem-queues, bcd, terminal, identity, write, syscall, lifecycle,
outer and wrapper. This includes the private provider lifecycle projection;
it differs from the earlier public-view diagnostic inventory, which includes
the separately idle ordinary memory reader instead. Existing owner schemas
and the diagnostic format are unchanged.

Image preparation checks the complete header, exact build and metadata,
bounded lengths, ordered membership and absence of trailing bytes before
preparing the existing destination-bound context transaction. That transaction
validates every payload and cross-owner boundary without publication. The
candidate owns its decoded bytes, rechecks metadata on the creator at commit,
and delegates single-use, nonthrowing peer publication to the existing guarded
transaction. The destination must outlive its candidate. An image does not
serialize native stacks, thread IDs, pointers or process-local owner bindings.

The context group now exposes `inspect_startup_metadata()` after its complete
restricted aggregate audit. This permits metadata observation at actual live
stop/return boundaries. The ordinary `save_startup_metadata()` retains its
existing narrower polling admission. Capture checks owners and metadata again
before returning bytes. These checks require external exclusive suspension;
they do not coordinate threads or replace the process-wide signal policy.

The test launches an actual source coroutine on its creator worker, executes to
the selected host-operation cut and captures its image, then exits the source
process before fresh imports. Each destination reads back all sixteen owners
before coroutine entry, recaptures canonical bytes, and continues without
startup/reset replay. Native ASan/UBSan and VCS producers and consumers cross
both ways. The independent oracle is the retained, separately audited context
matrix; comparisons include every subsequent owner at every operation. VCS
asserts time zero and zero RTL edges. These are host-component operations,
not CPU target-cycle cuts.

Negative coverage includes every byte truncation, incompatible build bytes,
metadata, malformed length/header/payload, missing/duplicate/unknown/reordered
owners, every successive preparation/publication allocation failure, foreign
thread access, a late signal-mask change with creator retry, consumed and
competing candidates, and actual semantic corruption at its first output
boundary. Evidence catalogs bind the original complete source list, commands,
provider archive and build digest; the independent auditor also tests omitted
and duplicated receipts and individual source omissions.

Exact results, full artifact paths and executable native commands are in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics remain under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration156/`.

Complete Rocket Level 1 remains disabled. Next: connect this creator-side
image/candidate API to a complete simulator restore coordinator, establish
production process-wide thread/mask/action/signal exclusion, and publish a
coherent generated RTL/FAME/bridge/functional-memory/host cut. The separately
prepared metadata is not part of an all-simulator atomic publication yet.
Level 2 remains independent. BOOM and Saturn remain pending; standalone
Shuttle, physical FPGA validation and ASIC power stay outside this increment.
