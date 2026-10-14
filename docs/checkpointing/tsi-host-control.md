# FireSim TSI idle and reset control

Iteration 100 moves the production FireSim TSI's busy/host-loaded/target-loaded
flags and suspended idle/reset progress into `firesim.tsi.host-control.v1`.
The installed FESVR library and its original coroutine remain in use. Aggregate
TSI and CPU checkpoint support remain disabled.

The immutable identity is `WDGCKPT1`, version 1, component kind 18 and the exact
parsed idle count. Parsing preserves the original default 10, `atoi` conversion
to `size_t` and last matching argument behavior. The three mutable 64-bit words
are phase, remaining idle yields, and busy/host-loaded/target-loaded flag bits
0/1/2. There are no process addresses, callback objects or saved contexts.

| Phase | Meaning |
| --- | --- |
| 0 / ready | Outside FireSim idle/reset; the separate FESVR caller may still be suspended |
| 1 / idle | Busy is false; remaining counts future `switch_to_target()` calls |
| 2 / reset_wait | Host loading finished; waiting for target-loaded acknowledgement |
| 3 / reset_child | Target drain observed; original TestChip reset entered, with its caller/protocol owned separately |

Idle decrements its cursor before each original context switch. At the final
suspended yield, phase is still idle and remaining is zero; only the subsequent
resume sets busy and returns to ready. A zero idle count performs no switch.
Reset publishes host-loaded before waiting, enters the child exactly once after
the target flag becomes true, and returns to ready when that child finishes.
Public deassertion of target-loaded during the child does not undo child entry.

Every transition completes before a context switch can suspend its caller.
Save/validate/load perform no context switch, FESVR service, target edge, MMIO,
serial transaction or child reset. Full identity, exact length, phase, cursor
and flag validation precede the first assignment. Unknown flags/phases,
oversized idle cursors, idle-with-busy, non-idle cursors and reset-without-host-
loaded images reject atomically. Escaping context-switch/child exceptions
permanently invalidate component checkpoint access. Wrong-phase operations
reject before mutation. Production inspection is const; this owner cannot
restore or replace FESVR's suspended stack.

The independent native sanitizer/VCS checker expands the original idle for-loop
and reset while-loop. It restores every completed-transition cut in fresh
processes for counts 0, 1, 3 and 10, plus an active `UINT64_MAX` cursor, and
compares every full payload and resumed action. It tests all truncation lengths,
identity bytes, phase/interruption guards, fresh malformed images, and valid
idle-cursor/target-loaded corruption at the first differing action before
acknowledgement. Labels in this checker are component fixture operations,
not Rocket target cycles.

The actual installed-FESVR ELF read/merge/reset check additionally captures
34 complete host-control images per backend: construction/loader cuts, repeated
reset waits, and 26 suspended idle yields spanning multiple complete idle loops.
Both native and VCS execution are checked against independently constructed
payloads. Fresh native sanitizer and VCS processes restore these actual images
with complete zero-edge readback. They contain no FESVR context or services.

A second installed-FESVR checker uses a real symbol-table ELF with `tohost`/
`fromhost`, an original TestChip `+init_read`, and idle counts 1/3/10. It observes
the suspended reset child waiting for a serial read response, both halves of
HTIF's actual tohost read, every idle yield, and the subsequent busy poll, across
three poll loops. Duplicate idle-count arguments test the original last-match
parsing. It independently compares all phase/cursor/flag words and restores
every actual image into fresh sanitizer/native and VCS component processes.
These are real host-protocol cuts, not CPU execution or restored HTIF callers.

Remaining owners include FESVR private serial queues and suspended caller/read
destination, HTIF poll/fromhost/device/stop/signature state, TestChip loader/
cache-flush/init-access progress, and cross-owner coherence. Copying a context
or re-running `start()` cannot restore these. Coherent four-hart CPU cuts,
fresh Level-1 continuation and independent captured Level-2 CPU replay remain
pending. Physical FPGA and ASIC power remain deferred.

Exact results, artifacts, workload/build hashes and native VCS commands are
recorded in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostic
root: `/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration100/`.
