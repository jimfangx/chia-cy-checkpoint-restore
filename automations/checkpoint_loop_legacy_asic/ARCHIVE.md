# Archived checkpoint loop with ASIC and Jasper support

This is the pre-removal source snapshot from October 22, 2026, including the
Jasper launcher, systemd/cgroup memory broker, its tests, and formal/gate
milestones. `README.md` is the original documentation. `plans/` contains the
old plans, and `saved-state.json` captures the controller state at archival.
`archive-manifest.json` records SHA-256 hashes of every snapshot file.

Large build artifacts and logs were not duplicated. Their existing location is
`../checkpoint_loop/runs/`; historical paths in the state remain unchanged.
The active loop and its current state remain in `../checkpoint_loop/`.

This is a source archive, not a second running controller. Original scripts
contain paths to `automations/checkpoint_loop`; restore the archived source
there before using the old workflow. Back up the active source and state first,
and never run both controllers against the same repositories or run directory.
Any restoration of `saved-state.json` or old plans must be deliberate; the new
loop migrates legacy milestone positions on resume.
