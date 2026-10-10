# M4 native capture encoding and publication — iteration 39

M4 remains in progress. Native `encode_durable_capture(snapshot)` and
`publish_durable_capture(destination, snapshot)` now provide the durable
publication prerequisite for public capture. They accept a complete canonical
v3 `FSAGG1` settled-cut snapshot; they do not collect live owners, hold clocks,
or enable `+fs-checkpoint`. Public capture wiring and opt-in Make integration
remain the next increment. The existing public restore and default/restricted
fail-closed behavior remain in effect. Level-2 formats remain independent.

The encoder checks exact native names/schemas/byte lengths and complete
generated/harness section identities, membership, order and shapes against
the compiled inventory. It creates canonical sorted JSON, binds the actual
running executable, and reuses the consumer's complete image validation for
every word's padding, low generated clocks/reset/finish and agreement with
the manifested FASED target-cycle counter. Its validated round-trip staging
must equal the input bytes. No output access occurs on validation failure.
Native payloads remain opaque at this format boundary: the producer must save
supported live owners at one settled cut, and restore must still perform
all-owner semantic validation/readback and zero-edge bootstrap.

The publisher opens and pins the destination directory, rejects existing
symlinks/FIFOs/directories, checks directory-sync support, creates an exclusive
mode-0600 temporary with a random bounded name, writes completely despite
EINTR/short writes, syncs and closes the file, checks destination type again,
renames within the pinned directory and syncs/closes that directory. Cleanup
attempts to remove only this invocation's temporary, preserving the original
error if cleanup fails. A typed publication
error distinguishes an unchanged destination from a complete visible
replacement whose durability could not be confirmed. SIGKILL may leave a
private pending file; readers never treat it as the requested checkpoint.

The standalone fixture includes a 257-bit scalar, a 64-bit target counter,
multi-address 9-bit memory, a BUFGCE output, complete harness banks and opaque
native payloads. ASan/UBSan checks exact bytes against the independent Python
encoder, regular-file replacement, interrupted/short writes, all 149 staging
rejections before publication and again before directory access, 11 injected
syscall failures, four special destinations, three killed-writer boundaries,
and 16 simultaneous writers with independent complete-image readers. Each
invocation retains its own fixtures, logs and pending files for safe reruns.

The full-production encoding verifier uses the captured outstanding-write
cut with all 2,856 generated entries / 13,507,456 words, 29 harness records
and 17 native owners. It binds its standalone sanitizer executable and compares
the entire native encoding with Python, then exercises five full-size I/O
failures. This is an encoding oracle, not a live capture/restart: its opaque
runtime-compatibility payload still belongs to the original VCS executable
and cannot authorize loading into the standalone encoder.

All new publication checks pass. The full-size image is 65,157,247 bytes and
matches Python exactly; all five full-size syscall failures pass. The repeated
small-profile verifier preserves all 587 earlier fixture/log inodes and
hashes. Both new public/restricted VCS runs pass five fresh continuations,
each matching 3,765,516 complete 40-port samples, including outstanding
native/FASED writes, with complete pre-edge readback and zero-edge bootstrap.
Independent audits pass 68 public / 42 restricted processes and 67,537,280
generated-word / 85 native-owner comparisons per run. All 44 baseline and
15 focused scopes pass, including ordinary clean RTL VCS, full M2/M3,
counters/profiling, rejection liveness, complete owner comparisons, entry
dispatch, repeated consumer/public rejections, runtime identity, all retained
publication failures and actual-trace mismatch diagnostics.
Final review corrected a zero-byte-write diagnostic that had incorrectly used
unset `errno` text. Both native publication verifiers pass again with that fix;
the small verifier explicitly checks the diagnostic. Corrected-run logs end
in `native-publication-corrected.log` and
`native-production-publication-corrected.log`.

Run from the Chipyard root, sourcing both environments and the VCS helper last:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_durable_publish \
  --out automations/checkpoint_loop/runs/m4-iteration39/native-publication
python automations/checkpoint_loop/runs/m4-iteration39/run-all-regressions.py
python automations/checkpoint_loop/runs/m4-iteration39/run-focused.py
```

`run-focused.py` includes new full public/restricted VCS continuations,
independent complete audits, repeated consumer/public rejections, entry
dispatch, runtime identity, all retained publication failures and mismatch
diagnostics, and the standalone full-production encoding oracle. Exact argv
arrays and logs remain under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m4-iteration39/`.
`results.json` records all 44 baseline exits; `focused-results.json` records
all 15 focused exits. `artifact-manifest.json` lists full artifact paths and
source/input hashes; `executed-verification-commands.json` contains only
executed commands. Earlier small-profile development artifacts are retained;
the final repeated invocation and full-production oracle use the final publisher.
Both plans remain read-only. No required external dependency is missing;
no FPGA, formal, ASIC gate-level or power validation is claimed.
