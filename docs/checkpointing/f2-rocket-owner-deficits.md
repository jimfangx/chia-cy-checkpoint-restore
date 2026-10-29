# Rocket production ownership deficits

Iteration 268's fresh exact-recipe compiler rejects complete-image emission.
Its independently audited regional/local diagnostic exposes 11,110 functional
bank descriptors and three physical-CE descriptors. This establishes readout
addressability only: complete common-cut capture/restore ownership is still
false, and no deployable image is emitted.

Four original TRACERV Queue_56 executions now contribute twenty descriptors,
including 12,583,072 stored bits / four 6144-by-512 memories and their reader
address/pointer/full state. Their native RAM policy remains unsupported: the
reduced source-bound native test falls back to LUTRAM for the instrumented
queues despite BLOCK hints and fails its strict primitive audit. The untouched
queue maps to block RAM. Actual Rocket ULTRA implementation remains unvalidated;
these twenty owners must not be counted as physically captured or omitted from
the remaining hardware requirements.

The original functional inventory still absent from the descriptor network is:

| Original storage | Entries | Stored bits | Memories |
| --- | ---: | ---: | ---: |
| NASTI adapter | 38 | 258 | 0 |
| Widget shadow staging | 4 | 1,339 | 0 |
| Other absent original storage | 1,000 | 59,660 | 182 |
| Total absent descriptors | 1,042 | 61,257 | 182 |

Eight additional original widget-local registers are addressable but cannot
be frozen by the same transport needed to collect them. The compiler explicitly
rejects that self-freeze conflict. The host's immutable shadow observation and
opt-in endpoint/staging restore components do not waive either deficit. The
actual three-gate transport uses a 1242-bit source observation; the six-gate
component fixture's 1245-bit shape is separate.

The ordinary whole-root compiler first rejects the physical BUFGCE CE latch at
`F1Shim.top.FASEDMemoryTimingModel_0.gate`: it needs a synthesized capture owner
and common low-phase cut. Metasim's registered `O` is a different owner. The
regional CE descriptors also do not establish complete physical ownership.

Beyond these concrete generated-register/RAM deficits, complete functional DRAM
bytes (16 GiB allocated by this recipe), outstanding platform transactions,
stream/backend/upstream obligations, reset/external writers, resumable host
bridge/driver state, original pre-FAME semantic mapping and actual boundary
traces still require aggregate ownership. Full localhost image P&R/timing/AFI,
checkpoint-enabled F2 execution, active all-hart cuts, paired hardware-origin
migration, live RTL and rolling recovery remain pending.

Current-source receipts and runnable commands are under
`automations/checkpoint_loop/runs/aws-f2/iteration268/`: see
`owner-breakdown-selected.json`, `rocket-region-probe-selected.json`,
`remaining-blockers.json` and `verification-commands.json`. The owner breakdown
binds the exact compiler receipt, source hashes, raw descriptors and conflict
report; it retains every incomplete-coverage/admission flag as false.
