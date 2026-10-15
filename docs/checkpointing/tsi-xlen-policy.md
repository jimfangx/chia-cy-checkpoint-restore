# Installed HTIF XLEN policy

Iteration 115 binds the exact installed `htif_t::set_expected_xlen()` policy in
startup metadata revision 3. Both `0` (accept either ELF width) and `64`
(require a 64-bit ELF) previously produced the same component image for a
64-bit executable. These configurations now produce distinct images and reject
each other's images before publishing entry, mailboxes, symbols or owner state.
Revision 1 and revision 2 images reject explicitly.

The installed setter is nonvirtual and its field is private. A scoped,
thread-local observer records the actual `required_xlen` argument delivered by
the installed qualified `htif_t::load_payload()` to the build-local owned
`load_elf()`. This avoids changing installed headers or shadowing the setter.
Preflight suppresses all target writes through the existing preloaded-memory
guard. It must return exactly one matching path, entry destination and load
offset. Missing, unexpected, duplicate and nested provider calls reject; caught
errors cannot salvage an invalid observation scope. Thread scopes are isolated,
and exception unwinding releases the observer. Ordinary loads have no observer.

The observer is process-local and never serialized. It spans only a synchronous
preflight, with no coroutine yield. Images still bind the exact ELF, arguments,
transport policy and all seven pristine peer-owner configurations. A fresh
destination must already have the same expected-XLEN policy; component
preparation does not set that policy on the caller's behalf. Preparation still
rejects execution because complete HTIF/device/context ownership is pending.

Native sanitizer and VCS provider checks pass 352 cases: 16 repetitions of 11
modes per backend, including actual `load_elf()` calls, incompatible-XLEN
exceptions, sticky failures and thread isolation. Two installed-loader negative
controls fail at the missing-provider guard. Native/VCS metadata checks pass
24 fresh readbacks and 168 unchanged peer images, 13,964 atomic malformed-image
cases, 20 incompatible cases, eight exact-policy rejections, 192 incompatible
installed-XLEN rejection/recovery checks, and 704 loader-resource cases. Both
policies are set through an actual `htif_t` reference. No target services,
context entries or target edges occur during preparation.

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration115/`.
The final metadata invocation is
`startup-metadata-final/invocation-6lothuh5/summary.json`; the provider invocation
is `policy-provider/invocation-*/summary.json` (its exact path is indexed in the
run's `selected-results.json`). Each records native commands, source snapshots,
images, readbacks and artifact hashes. The first metadata attempt failed its
independent Python oracle's configuration-length check; that attempt and log
remain preserved. The corrected oracle passed a separate fresh invocation.

Reproduce from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_elfloader_policy_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration115-controller-rechecks/policy
python -m tools.checkpoint_formats.tests.verify_tsi_startup_metadata_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration115-controller-rechecks/metadata
```

Each invocation allocates a new retained directory. Audit a saved invocation
with its module's `--audit /absolute/path/to/summary.json` option. Every native
subprocess sources both repository environments and `vcs-env.sh` last, uses
Y-2026.03-SP1 `-full64` and system GCC/G++ 13. See the CPU matrix for the exact
recipe's complete workload controls and separate ordinary RTL diagnostic.

This closes one configuration distinction. It does not complete stop/exit/signal,
terminal, syscall/file-descriptor, memif, coherent coroutine or aggregate state
ownership. Complete Rocket Level-1 fresh-process continuation and independent
Level-2 captured readback/replay remain unsupported. No required CPU checkpoint
cut, CPU first-divergence case, FPGA validation or ASIC power result is claimed.
