# GitHub checkpoint publication

The user requested that the loop publish its implementation checkpoint commits
to GitHub, including work-in-progress checkpoints and the final checkpoint.

The loop controller owns local commits. Publish completed checkpoints to these
configured fork remotes, in this order:

1. FireSim: `git -C sims/firesim push origin HEAD:refs/heads/main`
   (`jimfangx/chia-fsim-checkpoint-restore`).
2. Chipyard: `git push origin HEAD:refs/heads/main`
   (`jimfangx/chia-cy-checkpoint-restore`).

FireSim currently has a detached HEAD, so use the explicit destination branch.
Publish FireSim first so the Chipyard submodule pointer refers to an available
GitHub commit. Ensure the final controller-created checkpoint is published too.
The implementation agent may push already-created checkpoints; staging and
local checkpoint commits remain the controller's responsibility.

Use ordinary pushes and preserve existing history. If authentication or a remote
update prevents a push, record the exact failure and pending commit IDs for
recovery. Keep plan files read-only and excluded from checkpoint commits.
Diagnostic run artifacts remain under the ignored `runs/` directory.

Preserve the link to this instruction near the top of `progress.md` when updating
recovery notes so the already-running loop reads it on subsequent iterations.
