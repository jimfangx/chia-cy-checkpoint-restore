# HTIF identity dispatch yield

Iteration 125 makes the ordinary HTIF parent's dispatch service return a
completion flag. An identity child that needs a merge-read response returns
blocked through both owner guards before `run_host()` switches to the target.
The parent retains its dispatch phase, raw tohost command and response queue;
the identity caller retains its command and writer phase. A retry checks the
same pending command and resumes the existing child without calling `begin()`
again. Completion queues one response, finishes the child and advances the
parent to device ticking. Request order, cache-flush packets and target timing
must remain identical to ordinary execution.

The existing parent schema and image bytes are unchanged. The service's
completion flag is control flow, not additional stored state. Exceptions still
poison the guarded owner. Other device callbacks may still enter unowned
services; an active guard continues to prohibit their capture.

This removes the suspended identity-dispatch callback from ordinary identity
cuts. It does **not** expand polling admission: `inspect_polling_cut()` still
rejects an active identity/write child. The prepared interface still requires
its existing ten owners and admits aligned identities only. The next increment
must validate dispatch/identity/write relationships and prepare all twelve
owners atomically before admitting unaligned dispatch cuts. Syscall, other
memif, descriptor, signal, stop/exit and simulator ownership remain pending.
Neither CPU checkpoint level meets acceptance.

For the next aggregate change, keep the following obligations explicit:

- Include `identity` and `write` alongside the existing ordered ten sealed
  polling components. An absent owner must reject even when its expected
  image would be idle. Revisit the unsealed inspection inventory separately;
  its existing eight-owner samples are intentionally incomplete audits.
- At a dispatch cut, require the parent's exact raw command to match the
  identity caller, its copied writer payload/address to match that command,
  and the independent poll reader to be idle. Program/init completion, loaded
  host flags, loadmem emptiness and host-ready requirements still apply.
  Keep the existing read/idle predicates and require idle identity/write peers
  there. A merely parseable phase combination does not establish a cut.
- Prepare destination-configured writer/transport/identity candidates and all
  cross-owner checks before terminal publication. The identity caller holds
  references to its actual writer and serial owners; copying a temporary
  caller must not leave references to candidates that will be destroyed.
  Publish only state with nonthrowing operations after the final allocation.
- Route prepared identities through the same non-suspending dispatch service
  and preserve pre-clear command validation. Test every selector and residue,
  partial head/tail responses and serial packets, queued parent responses,
  poisoned/reentrant services, every allocation failure and mismatched parent,
  caller and child images. Restore into fresh processes, compare all twelve
  images before service and after every operation, and corrupt retained merge
  bytes and commands to check the first divergent boundary.

The maintained HTIF parent checker exercises repeated blocked dispatch,
including a response queued before the child's final return. Every fresh
destination reads the whole parent image before any service, continues the
remaining operations, and compares all images with an independent Python
oracle. The actual ordinary HTIF identity checker additionally samples the
complete parent image at every FIFO, partial-read and merge boundary for all
four selectors, eight address residues and both cache-flush settings. Fresh
destinations read the parent and caller/write/FIFO images back. The parent
readback is independent of the three-owner atomic child preparation; these
four images do not constitute an aggregate restore interface or a CPU image.
All labels in these checks are host operations, not target cycles.

Run from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_htif_poll_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration125-controller-rechecks/poll
python -m tools.checkpoint_formats.tests.verify_tsi_memif_identity_fesvr_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration125-controller-rechecks/actual-identity
```

Both checkers accept `--audit /absolute/path/to/summary.json`. Exact executable
native/VCS commands, source snapshots and results are indexed in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostic artifacts are
under `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration125/`.
