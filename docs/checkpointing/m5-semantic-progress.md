# M5 semantic progress watchdog — iteration 47

The audited `fcfs-fased-v1` Make capability adds
`+fs-checkpoint-target-timeout-cycles=N`. Pair this with
`+fs-checkpoint-capture-timeout-ms=N` and public periodic Level-1 history or
public restore. Host/cycle wall-clock watchdogs remain independently optional.
The semantic deadline measures target cycles since the last sampled unit of
completed target work, including bounded initialization and response completion.

`FPGATop.sim.target.AXI4Fuzzer_.fuzzer_.fuzzer.num_resps` is a manifested 14-bit
register initialized to 10000 and decremented only when the final response beat
is accepted. The 20-bit
`FPGATop.sim.target.AXI4Fuzzer_.fuzzer_.model.wipeIndex` counts the bounded
524288-cell shadow-memory initialization that blocks all traffic. The audited
completed-work count is `wipeIndex + 10000 - num_resps`. Initialization stops
advancing once all cells are cleared, so a later target hang cannot refresh the
deadline through unrelated activity. Normal Make pins both complete lowered
TLFuzzer/TLRAMModel modules ignoring source locations, verifies both counters'
generated membership/shape/clock/reset/adapter, and emits
`target-progress-inventory.json` and its compiled path. An unfamiliar profile,
module update, shape, X, padding, VPI kind or out-of-range remaining count fails
explicitly. This is workload transaction progress, not processor retirement.
Rocket/BOOM and other profiles remain unsupported.

The settled callback reads this register alongside the manifested FASED target
counter with clocks parked. It performs no MMIO, deposits, native loads or added
edges. Restore starts a new host policy epoch at the first actual settled
sample. Both counters must remain monotonic in that epoch. Completed work at the
cycle deadline refreshes the deadline; a frozen count triggers
`target_progress_stall`. Bounded capture suspension preserves the existing
independent wall deadlines and never advances the target-cycle deadline.
Monitoring starts after initial reset/zero-edge restore bootstrap; startup
before the first audited sample remains outside this profile's coverage.

Native ASan/UBSan covers 237 complete collector rejections and 15 targeted
sampler rejections, including impossible response-before-initialization state.
The actual compiled inventory rejects 26 altered shapes/update semantics. All
63 Python tests, eight native watchdog scopes, native history/publication,
142 entry cases, full M2/M3/dispatcher/harness, ordinary clean RTL VCS and Make
rejections pass. Full production passes all five complete captures/fresh
continuations and 56 public restore rejections. Independent audit confirms
68 fresh processes, 67537280 generated-word and 85 native-owner comparisons.

Current public history commits at 250000, 500000 and 750001 and retains the
newest two; restored execution commits 600001/700000 and both recaptures replay
exactly. All 13507456 generated words, 29 harness banks and 17 native owners are
included. Host/cycle production monitors independently detect late main-thread
stalls at 600013; healthy continuation matches all 366116 reference suffix rows.

The semantic verifier restores the live-retained 500000-cycle image into two
fresh processes. The optional verification observer reads an existing numeric
control file once at cycle 600000. With value 1 it forces the target client's
response-valid input low, preventing response completion while target clocks,
FASED cycles and host callbacks continue. This fault injector is only in the
verification observer passed through VCS_EXTRA_V, not the production coordinator,
sampler or FPGA transport. No checkpoint is captured while the fault is armed.
Both processes report target_progress_stall at cycle 610000 with 3305 completed
responses. The observer asserts that the response count stays fixed; the native
watchdog samples the actual manifested registers independently. Both fault
traces contain 146665 rows and match byte-for-byte, including their full
reference prefix through the causal cut. A separate value-0 healthy replay
matches all 366116 suffix rows. All native owners are read back before any edge,
bootstrap adds zero edges, and the selected history index/image remain unchanged.
Nine malformed semantic controls reject before native platform construction or
trace advancement. An optional SV observer may create an empty trace file at
elaboration; the verifier explicitly distinguishes that from target execution.

Failed trials remain diagnostics. The first SV observer insertion exposed a
declaration ordering error. Probing an absent fault-control file lazily loaded
liberrindex.so/libruntimeerror.so and correctly failed strict ELF compatibility;
the observer now reads an existing numeric file. Runtime identity reports exact
added/removed/changed ELF files without relaxing the guard; native ASan/UBSan
passes all 43 checks, including real dlopen/dlclose. A response-only live trial
then exposed a false alarm at 10001 during the intended shadow-memory clearing
phase; the current sampler includes its audited finite initialization work.
All final scopes ran against the source-bound normal-make-initialization build.

M5 acceptance is supported for this audited VCS profile. Concrete summaries,
exact argv, full paths and hashes are under
/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m5-iteration47/.
Root papers' interval/replay/full-state sections were reread from the preserved
extracted texts. Both plans retain their initial hashes and remain unstaged;
plan-number corrections stay in earlier checkpointing docs. Level-1 and Level-2
remain independent. There is no physical FPGA, formal or ASIC activity/power
validation claim. Startup before the first audited post-reset sample, processor
retirement and unfamiliar target profiles remain outside this capability.
