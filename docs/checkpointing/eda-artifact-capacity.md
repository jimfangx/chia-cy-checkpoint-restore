# EDA artifact capacity recovery

Iteration 255's incoming failure occurred during input rsync, before VCS ran.
The EDA root filesystem had 9.6 MiB available and only 19,591 free inodes;
the loop's mirrored run history occupied 846 GiB. The original error and capacity
diagnostics are retained under `runs/aws-f2/iteration255/`.

`automations/checkpoint_loop/eda_dedupe.py` is an explicit maintenance command
for the claimed EDA mirror. It uses Linux `FIDEDUPERANGE` on the existing XFS
filesystem with `reflink=1`. The kernel compares every extent before sharing it;
size and sampled hashes only select candidates. Files retain separate inodes,
their contents, paths, permissions, ownership and modification times. Subsequent
writes use copy-on-write. No file is deleted, hard-linked, archived or excluded
from verification. Historical receipts keep their original execution identity.
Shared byte totals describe successful kernel operations, not necessarily newly
freed storage; filesystem capacity before/after is recorded separately.

The default command inventories candidates without changing extents. `--apply`
first executes an actual-filesystem self-test checking unequal-data rejection,
contents, metadata, separate inodes and isolation of subsequent writes. Sharing
uses bounded aligned ranges, checks short progress and kernel errors, and rejects
concurrent metadata/content changes detected through descriptor metadata. Only
generated `.fir`, `.v`, `.sv`, `.json` and `.dcp` files above the configured size
are candidates; local build worktrees, symlink directories and live `.Xil`
scratch stay outside the walk. Checkpoint images and boundary traces are not
candidates. Run maintenance while the mirror is idle, before synchronizing a new
verification batch.

Run on **EDA**, in `/scratch/jfx/chia-cy-checkpoint-restore`, with a new output
path below `automations/checkpoint_loop/runs/`:

```bash
python3 automations/checkpoint_loop/eda_dedupe.py --apply \
  --minimum-bytes 8388608 --target-free-bytes 17179869184 \
  --out automations/checkpoint_loop/runs/aws-f2/NEW-UNIQUE-RECOVERY
```

The free-space target bounds maintenance only. It does not change source/input
sync, artifact fetching, test selection, sanitizers, licenses or VCS flags.
An unsupported filesystem or kernel error fails explicitly. This is capacity
recovery for regression execution, with no FPGA checkpoint or CPU acceptance.

The initial smallest-first sweep was interrupted after safely sharing some
extents; its partial receipt and `KeyboardInterrupt` log remain untouched.
The revised sweep processes large candidates first and supports a free-space
target. During this recovery it was deliberately interrupted after recovering
enough room for the complete verification batch; its 16 GiB target was not
reached. Completed request receipts remain intact for independent full-file
hash, metadata and inode auditing. A trial with a 128 MiB minimum found no
candidate pairs and recovered no capacity; its receipt is retained separately.
Free space remains limited: run further maintenance before producing another
large exact-Rocket generation. All diagnostic logs and fresh component receipts belong under
`automations/checkpoint_loop/runs/aws-f2/iteration255/`, not this document.

The full 45 controller tests use the manager's existing Chia/Ray environment on
backend F2. An extra invocation of that manager-only scope on EDA failed with
`ModuleNotFoundError: No module named 'ray'` under `/usr/bin/python3` 3.9.25
(which also lacks pip). The failure remains in its original log. The same full
scope passes on the manager; no test is stubbed or omitted. VCS, bank, bridge,
sanitizer-host, FCFS, cut and all pinned component checks remain on EDA. The
corrected complete VCS batch is rerun with fresh output directories.
