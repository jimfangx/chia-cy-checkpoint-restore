# M4 production aggregate — iteration 29

M4 remains in progress. The new entry-based aggregate and test entry connect
the actual generated FCFS registry, metasim platform, driver, MMIO, functional
memory, harness and dispatcher. Production `+fs-checkpoint`/`+fs-restore` in
`entry.cc` still fail closed. Integration of the durable runtime entry and
complete configuration/library binding remains acceptance work.

`aggregate_packed.py` binds `firesim.aggregate.lowclock.v2` and
`ascending_nibble_padded_words_v1` in the runtime manifest. A generated entry
owns every memory address, concatenated in ascending order with fixed-width
hexadecimal words. Its aggregate width includes nibble padding; validation
checks padding at every address. The exact generated manifest supplies actual
word width/depth and ordering. This is independent of Level-2 semantic state
and the existing fixture's per-word aggregate profile. Manifest construction
now validates geometry without constructing millions of invented zero words.

`FSGRTL2` staging retains the existing compiled entry/clock table and all-owner
native/VPI prevalidation before any load or deposit. Complete native and RTL
readback precedes actual DPI publication and incoming-bank refresh. The file
contains 2,856 generated entries representing all 13,507,456 words, 29 harness
records and 16 native owners, including four full 4 MiB memory channels,
FASED host state, widgets, driver lifecycle, scheduler and run loop. Retained
VPI handles/values still scale with word count; they are not a streaming
hardware implementation.

`production_aggregate_checkpoint.cc` is a test entry. It uses FireSim's real
`create_simif`, generated constructors and unmodified FCFS driver. Loading
reserves clocks before workers, MMIO or native ticks. Native load counters,
complete pre-edge native payload evidence and host/generated clock edge
monitors exercise fail-closed preparation. The capture process completes and
exits before a fresh process reads the checkpoint; it is not process cloning.
Target timing uses the captured FASED `model.tCycle`; host sample and completed
driver operation remain separate. The production runtime must explicitly
bind this indexing/configuration contract before enabling its durable API.

Five fresh full production continuations pass at default operations
3/11/699275/699276 and randomized operation 101. All 3,765,516 complete
40-port transaction samples match their uninterrupted suffixes, including
native and FASED outstanding write traffic. Completion remains exactly
774,628/774,632 target cycles. Every process reads back all generated/harness
state and all 16 native payloads before its first edge; bootstrap has zero
host/target edges. Each bound container is about 65 MB and preserves every
RAM word and all 16 MiB of configured functional memory.

The independent audit checks all 34 simulator processes, 67,537,280 generated
words, 80 native owners, all harness banks, container integrity/executable
binding, cut edge indexing and exact transaction timing. Sixteen malformed
native payloads, schema/order faults, late generated/harness shape faults and
trailing data (21 processes) reject with zero native loads/deposits and zero
edges. An actual unaudited profiling callback rejects before workers or loading.
Both word and entry staging pass native ASan/UBSan checks, including a 257-bit
register and per-word memory padding; compact staging passes 314 rejections.
The comparison helper reports the first target cycle and transaction port;
four mutations of actual VCS traces reject with the expected data/timing/fire
or truncated-continuation diagnostic.

Retained baseline verification is finishing under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m4-iteration29/`.
All 42 Python tests and the existing component, ordinary clean RTL VCS,
M2/M3, production capture, profiling, counter expectation and rejection-liveness
checks have passed. The final low-clock comparisons and artifact audit remain
in progress; their final results will replace this paragraph.

Reproduce from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_production_aggregate_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration29/production-bound-final
python -m tools.checkpoint_formats.tests.audit_production_aggregate \
  --out automations/checkpoint_loop/runs/m4-iteration29/production-bound-final
```

The test's compiled profile is seeded from the iteration-28 diagnostic owner
inventory and checks it against each current production capture. Initial
diagnostics remain separate: the first adapter incorrectly invoked the base
blocking interface instead of the metasim platform; a concurrent regression
build collided with another InventoryFixture build. Sequential reruns are
required for shared Make directories. Interrupted development trials are not
counted as completed verification scopes. Plans, conda files and PDFs remain
untouched and unstaged; no commit/reset/clean. No physical FPGA, formal or
ASIC gate-level validation is claimed.
