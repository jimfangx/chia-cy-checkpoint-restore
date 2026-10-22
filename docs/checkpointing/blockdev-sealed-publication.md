# Prepared block-device publication

Iteration 175 adds prepared/sealed publication to the returned-call
`firesim.widget.blockdev.v1` host owner. Rocket Level 1 remains in progress;
this component does not enable CPU checkpoint admission.

The unchanged v1 payload binds all 26 actual recipe MMIO addresses, latency
settings, sector geometry and tracker count. It owns initialization and
response-pending flags, the stream cursor, all request/data/response/ack queues,
every tracker word including inactive storage, and every private disk byte.
Disconnected devices are supported. External disk paths, debug logs, active
calls and poisoned calls reject explicitly. Generated device hardware and
transport remain separate owners.

Preparation stamps the complete destination, decodes all replacement queues,
trackers and disk bytes, opens a private replacement `fmemopen` stream and
positions it before touching destination state. Its RAII stream member is
destroyed before the decoded backing. Sealing checks lifetime, native thread,
generation, consumption and complete destination bytes before owner access or
publication. A failed seal can be retried. Legacy loading uses the same
prepare/seal/publish path and invalidates even identical-byte candidates.

Allocation-free `noexcept` publication validates the guard, swaps stream
ownership and all containers, and assigns two flags. It makes no libc stream
call, MMIO call or target edge. The candidate retains the retired stream and
backing until its later destruction. Destination exclusion between sealing and
publication is a production coordinator obligation; this adapter does not
supply process/thread/signal/descriptor exclusion.

Native ASan/UBSan and VCS exercise all fifteen original component cuts,
including queued request/data, partial writes, stalled responses and acks.
The independent byte oracle checks complete pre-edge and final state; the
MMIO oracle checks continued words, ordering and fixture labels. The matrix
also checks cancellation, expired/thread/stale/consumed/legacy candidates,
returned and interrupted services, full nonzero disk backing and an EOF cursor,
disconnected devices, every C++ allocation failure through successful
preparation/sealing, and injected `fmemopen`/`fseeko` failure with stream cleanup.
Publication is tested with the next C++ allocation forced to fail and libc
stream-call counters held constant. Fatal misuse must exit 86 with unchanged
state; the unexpected-return control must exit 88.

Fresh malformed images reject before readback or an edge. A structurally valid
tracker data corruption is actually restored and stops at the first changed
`bdev_rresp_data_lower` response at fixture cycle 142, before acknowledging the
remaining response or next operation. These are fixture cycle labels, not
captured Rocket target-cycle cuts. The CPU matrix records exact native receipts
and executable commands.

Remaining Level-1 integration includes prepared UART, FASED and all four
TracerV owners, complete generated/harness/memory/I/O ownership, runtime and
creator-side TSI coordination and process exclusion. The generic aggregate
still publishes legacy owners sequentially. Independent Level 2 is unchanged.
