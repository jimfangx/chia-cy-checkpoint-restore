# Publish the restricted production TSI from its sealed creator

Iteration 163 connects the production bridge candidate to the staged creator
publication mechanism introduced in iteration 162. The restricted provider,
bridge control, prepared candidate and competing candidate stay on their
original creator through preparation, sealing, publication, launch or
cancellation. The candidate's private provider is initialized from all sixteen
host owners during preparation; the live bridge still has no provider then.
Those owners are `poll`, `program`, `init`, `host`, `read`, `serial`,
`loadmem-read`, `loadmem-queues`, `bcd`, `terminal`, `identity`, `write`,
`syscall`, `lifecycle`, `outer` and `wrapper`; bridge `control` is owner seventeen.
The independent image auditor checks their complete ordered payloads, startup
metadata and component build digest, including continuation boundaries.

`tsibridge_t::prepared_context_t::seal_publication()` performs the complete
creator, private owner, startup metadata, signal-policy and fresh destination
checks without publishing. Allocation failures leave the same candidate
retryable. A successful seal is single-use. The coordinator must acquire its
exclusion guards before sealing and retain them through publication/readback.

`publish_sealed()` transfers the prepared control/provider without allocation,
callbacks, context entry, MMIO or target advancement. It is `noexcept` and
terminates on unsealed, repeated, foreign-thread or occupied-destination use.
The existing `commit()` combines seal and publish for component callers that
already hold exclusion. The API does not establish process-wide exclusion.

The production bridge component now retains the candidate in the reserved
creator's resource bundle. It prepares the continuation and publication callback
before sealing, seals the actual TSI candidate under a retained component guard,
and publishes it through `publish_prepared()`. Publication runs with C++
allocation disabled; complete seventeen-owner readback follows on that creator
under the same guard. The controller checks the publication acknowledgment while
the creator remains parked under the guard. Launch releases the guard before
entering the provider continuation. Cancellation is exercised before sealing,
after sealing before publication, and after publication; candidates and live
providers are destroyed on their creator before cancellation returns.

The serial MMIO peer and exclusion mutex in this test remain component fixtures.
Complete Rocket Level 1 stays disabled: the complete simulator/FAME/channel,
CPU-managed stream, other bridges, functional memory and runtime cut still need
joint coordination. `simif_emul_t::begin_restored_load` and its fresh destination
checks still reject CPU-managed streams and unsupported widget schemas.
Production thread/signal/descriptor/parser exclusion also remains pending.
Do not remove these guards or claim the restricted provider as a complete TSI
or CPU checkpoint profile. Ordinary unrestricted HTIF sessions remain unsupported.
Level 2 remains independent; BOOM and Saturn remain pending.

Results, exact native VCS commands, build settings, source bindings and workload
hashes are recorded in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).
Diagnostic artifacts remain under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration163/`.
