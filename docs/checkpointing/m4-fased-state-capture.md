# M4 FASED generated-state capture — iteration 11

M4 remains in progress. The actual FCFS FASED timing model is now inventoried
and captured during outstanding memory traffic in VCS metasim. The full runtime
still rejects checkpoint requests: coherent capture of all software/harness
owners, `.fsckpt` publication and fresh-process restoration remain outstanding.
No external dependency is missing. No FPGA validation is claimed.

The first FASED compilation exposed synchronous memory pipelines omitted by
the earlier supported inventory subset. Golden Gate enables FIRRTL 1.6's
`PassthroughSimpleSyncReadMemsAnnotation`: its Verilog emitter creates stored
read addresses for new/undefined synchronous reads, stored read data for old
reads, and stored read data for supported read/write ports. The new
`firrtl-emitter-memory-pipeline-v1` adapter enumerates those exact emitted
names/types using FIRRTL's memory-field and lowered-name utilities. It does
not change the emitted RTL, lower memories again, or invent semantic StateIDs.
Complex remaining pipelines and unsupported read/write policies fail closed.

Five compiler fixtures cover old/new/undefined readers and old/undefined
readwriters, including a non-power-of-two RAM depth. Scala checks the stored
field and its width; Python independently checks exact emitted register/RAM
declaration membership and shapes against each actual manifest. The complete
Scala suite passes 20 tests, and the complete Python suite passes 24 tests.
Streaming validation rejects missing, extra, reordered or reshaped entries,
incomplete RAM contents, wrong manifest/stage/sample metadata, duplicate JSON
keys, and unknown or improperly padded values. These diagnostics have no
checkpoint-container integrity contract; the evidence records their SHA-256.

The actual test configuration is `fasedtests.AXI4Fuzzer`, target `FCFSConfig`,
platform `FCFS16GBQuadRank_DefaultF1Config`, at the metasim `FPGATop` root.
The platform fragment selects `FIFOMASModel`; target `FCFSConfig` alone does
not select the host timing model. This is VCS metasim, with no physical F1/F2
hardware. The original 10,000-transaction workload and its complete target
RAM scoreboard are retained. Runtime `+memsize=4194304` covers the full 4 MiB
address space allocated by this generated target on each host memory owner.

Independent emitted-RTL coverage agrees with all 513 instances, 2,856 entries,
13,507,456 words and 103,083,035 bits. FASED itself contributes 429 entries,
2,751 words and 73,370 bits, including its two emitted read-pipeline registers,
32 bank trackers, rank/refresh/hazard counters, transaction scheduler/backend,
ingress queues, read/write egress queues and reorder/free-list state,
programmable timing registers, counters and clock-gate model state.
FAME state, LI-BDN queues, transformed target/scoreboard RAMs and all other
bridges/control/interconnect state under the root are also captured.

The diagnostic probe uses an entry-based JSONL stream and address loops, so
generation scales with entries rather than RAM words. It reads **every** RAM
word without advancing simulation time during a sample. Its explicit `emul`
harness hierarchy and manifested scalar predicates are checked before build.
The actual emitted AXI AR/AW handshakes bind the four counter roles used by
the predicates; the captured values independently prove outstanding traffic.

The full fuzzer passes after 774,628 bridge-reported target cycles. Three
settled host falling-edge captures each contain all 13,507,456 words:

| Host sample | FASED timing cycle | Target pending reads/writes | Host pending reads/writes |
| --- | --- | --- | --- |
| 699355 | 524391 | 1 / 0 | 1 / 0 |
| 699368 | 524401 | 2 / 1 | 0 / 1 |
| 699369 | 524401 | 2 / 1 | 0 / 1 |

Two independent full fuzzer runs produce the identical capture SHA-256
`b3f2c66bf6463abcd0cbe1fe81dc6dff523eaca9910a6e2764edbf63f55f597c`.
The complete functional-memory regression retains 64 fresh continuations and
1,704 compared model edges with ASan/UBSan and malformed-owner rejection.
Full M2 retains five fresh processes, 108 target samples, 1,404 comparisons
and negative tests. Full M3 retains six byte-identical captures, 547 stalled
boundaries, 5 semantic/242 transfer replay samples and eight invalid reads.
All 539 generated InventoryFixture words, ordinary clean InventoryDUT VCS,
and GCD VCS metasim (12 target cycles) also pass. These regressions establish
the existing component and semantic paths; they do not establish Level-1
continuation.

These are generated-state diagnostics, not certified whole-runtime cuts or
semantic checkpoint cycle indices. Functional DRAM bytes/queues are not in
this stream; iteration 10's independently tested memory-owner hooks still
need coordination with these captures. MMIO/stream buffers, harness input
and output latches, host clock/reset phase, PRNG, thread handoff, scheduler,
and host driver state likewise remain separate requirements. FASED's host
driver has configuration maps, profiling addresses/files, histogram baselines
and range-counter storage; it retains unsupported hooks pending an audit.
All three preflight/save/restore requests reject `widget/0` before driver
initialization, exit 1, and publish no incomplete `.fsckpt`.

Reproduce from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
python -m tools.checkpoint_formats.tests.verify_fased_inventory_vcs \
  --build automations/checkpoint_loop/runs/m3-metasim \
  --out automations/checkpoint_loop/runs/m4-iteration11/fased-inventory
```

The existing build root avoids sbt assembly's cached output-path issue: a new
root initially produced an empty touched JAR and could not find the generator.
The initial compiler attempt also correctly rejected the unhandled synchronous
RAM. Both failed attempts and the corrected runs are retained in diagnostics.
All VCS shells source both environments and `vcs-env.sh` last, with
Y-2026.03-SP1, `-full64`, GCC/G++ 13 and `VCS_FLAGS=-Mupdate` for reused builds.
Commands and diagnostic artifacts are recorded under
`automations/checkpoint_loop/runs/m4-iteration11/`.

Next: enumerate/integrate every runtime owner, implement audited driver and
transport/harness/scheduler adapters, establish a coherent freeze with
outstanding traffic, validate all owners/RTL handles and compatible build
identities before mutation, and load into a fresh VCS metasim process before
target advancement. Compare target-visible outputs and transaction timing
against uninterrupted execution. The root papers' snapshot/trace and full
off-chip-memory initialization discussions were reread from the existing
text extractions. Level 1 remains independent of Level 2. No plan correction,
formal result, ASIC activity/power result or physical FPGA validation is
proposed or claimed. Plans, conda files and PDFs were preserved without
staging, commit, reset or cleaning.
