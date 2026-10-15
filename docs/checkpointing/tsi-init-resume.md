# Fresh TestChip initialization dispatch

Iteration 105 replaces the suspended initialization read's local return path
with `firesim_tsi_t::advance_initialization()`. Production `reset()` calls this
same dispatcher and yields only when it returns blocked. A selected read
resumes the existing serial-read owner; it does not select, flush or issue that
request again. New accesses retain TestChip's original cache-flush calls,
serial packet order, diagnostic results and optional final hart-0 MSIP write.
The dispatcher returns at the same empty-response/reset-wait boundaries as the
original loop. No context switch occurs inside it.

`save_initialization_checkpoint()` and `load_initialization_checkpoint()` are
component APIs. Their bundle owns the four complete host-control,
initialization-caller, serial-read and serial-FIFO images, in that order. The
`WDGCKPT1` version-1/kind-22 prefix binds the effective TestChip cache-flush
address; each length-prefixed child retains its own exact configuration and
schema. Idle count, ordered accesses and MSIP policy are bound by those child
images. The bundle is not an `.fsckpt`, `.rtlckpt` or CPU checkpoint profile.

Supported external call boundaries are reset-wait with an idle reader and
unstarted/completed initialization; reset-child with target loaded, a selected
four-byte initialization read, zero caller result and its matching outstanding
reader; and completed initialization with a ready host and idle reader.
Intermediate selects/flushes/returns/retirements run without a yield. Other
combinations reject explicitly. The serial FIFO remains independently owned:
its entire payload is retained, including partially consumed requests and
queued responses. This does not certify coherence with bridge/target owners.

Restore first checks current owner usability and requires an unstarted host
context. It loads four private candidate copies, checks every length, complete
membership, child configuration and the supported caller/reader relationship,
then commits with four allocation-free, `noexcept` state swaps. No callback,
service, coroutine entry or target edge occurs during validation/readback.
Allocation/parse/compatibility failures leave every live owner unchanged.

The source-integrated FESVR adapter now initializes the host coroutine just
before its first host service. Upstream context initialization enters only its
trampoline and yields; normal HTIF service order is preserved. Fresh component
objects therefore need no coroutine stack. The first sanitizer pilot exposed
the installed FESVR context destructor's retained 1 MiB stack allocation. That
failed pilot is retained; the checks do not disable leak detection or change
the installed library. Component-restored objects explicitly reject `tick()`
HTIF continuation, which still needs its own complete migration implementation.
The lazy-initialization flag and component-entry guard are process controls,
not a serialized HTIF context; complete TSI ownership remains unsupported.

`verify_tsi_init_resume_vcs` takes actual native and VCS TestChip suspended
images retained by iteration 104. Its independent original-algorithm oracle
checks reset-wait, queued and partially consumed requests, repeated empty waits
and queued responses for both initialization reads, with cache flushing and
MSIP independently on/off. Every fresh native sanitizer and native VCS process
reads back all four owners before services, resumes without HTIF, compares
every external operation and complete owner image, and stops after initialization
and the final MSIP packet. Fixture operation labels are not Rocket target cycles.
Malformed prefixes, missing/reordered owners, configuration incompatibility and
individually valid but inconsistent caller/reader images must reject atomically.
Valid serial request corruption must identify its first unacknowledged divergent
consumer operation. Exact commands/results are in the iteration-105 section of
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

Complete HTIF startup/load/poll/fromhost/device/stop/signature and memif progress,
TestChip loader state, context migration and cross-owner CPU cut coherence
remain pending. Complete fresh Rocket Level-1 continuation and independently
captured Level-2 CPU readback/replay remain pending. No CPU support or physical
FPGA validation is inferred from these component checks.
