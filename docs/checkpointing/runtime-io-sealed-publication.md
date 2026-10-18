# Sealed runtime I/O publication

Iteration 167 separates the production `simif_emul_t` I/O component transaction
into preparation, sealing and nonthrowing publication. Complete Rocket Level 1
remains in progress and CPU aggregate admission remains disabled.

`prepare_checkpoint_io` still validates the exact ordered owner names, schemas,
configuration and complete payloads, builds private replacements, and retains
the complete destination image. `seal_checkpoint_io` checks destination lifetime,
native creator, single-use state and publication generation, then reads back
and compares every destination component. Every allocation and throwing check
finishes before sealing succeeds. Sealing and abandoning a sealed candidate
publish no owner state.

`publish_sealed_checkpoint_io` is `noexcept`. It checks the lifetime, creator,
seal, consumption and generation without allocations, then swaps the prepared
control AXI, optional CPU-managed DMA AXI and host timing state. The returned
MMIO/stream callers have already been validated at their returned boundaries.
A commit advances a destination-local generation, invalidating all other
prepared candidates, including candidates expecting identical state bytes.
The generation is transaction bookkeeping, not target state. Contract
violations terminate before another swap; they cannot unwind a partly
published aggregate into a runnable simulator. The existing
`publish_checkpoint_io` convenience call seals then publishes and retains its
throwing pre-publication checks.

The coordinator must hold both simulator contexts and exclude every other
owner user from before sealing through publication and complete readback.
No owner may change in that interval. These component APIs do not acquire
process exclusion or detect arbitrary unsynchronized writes after sealing.
They now allow the outer coordinator to finish all throwing I/O work before
publishing TSI or any other owner, using the same ordering discipline as the
existing sealed creator-side TSI API. They do not implement that coordinator.

The maintained native ASan/UBSan and time-zero VCS DPI matrix exercises queued,
in-flight and buffered-response traffic with and without DMA. Both convenience
and explicitly sealed fresh restorations require complete pre-edge readback
and finite AXI continuation against an independent byte/MT19937-64 oracle.
Allocation injection exhausts preparation, convenience publication and sealing;
sealed publication runs with the next allocation armed to fail. Separate fatal
processes exercise unsealed, foreign-thread, foreign-destination, recycled
lifetime, consumed and stale-sealed candidates. Every fatal handler reads back
the complete destination before exiting without returning to the simulator.
Successful-seal cancellation leaves every owner unchanged; repeated sealing
rejects without publication.

The existing production blocking-MMIO fixture checks the additional sealing
hook at suspended read/write and nested stream-count boundaries. Its retained
candidate is prepared after any component restore so suspension checks cannot
pass merely because an old candidate generation is stale. The CPU-managed
DMA fixture now checks joint capture/preparation/convenience publication/sealing
at every suspended DMA or stream-MMIO yield, alongside all existing per-owner
and reentry checks. Its historical two-owner restoration scope is unchanged.

Validation receipts and executable commands are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostics belong under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration167/`.

Next: prepare and seal every simulator/generated/harness/memory/widget/driver
owner under actual controller/creator/process exclusion; publish all owners
without remaining throwing checks; keep the destination held through complete
readback and pre-edge settlement. In particular,
`aggregate_restore_t::commit_native` still calls allocating per-owner
`load_checkpoint` hooks sequentially, and `checkpoint_owner_t` has no general
prepared/sealed publication interface. The new I/O API does not make that
existing aggregate commit safe for CPU admission. Then test complete
fresh-process Rocket Level-1 continuation at all four real workload cuts.
Level 2 stays independent.
BOOM/Saturn remain pending; standalone Shuttle, physical FPGA and ASIC power
remain outside this task.
