# Owned proxied syscall exit parent

Iteration 144 adds `firesim_tsi_syscall_exit_t`, an executable component for
little-endian FESVR device 0 / command 0 / syscall 93. It owns the eight
64-bit `magicmem` argument words, selector, invocation boundary, zero result,
complete 64-byte writeback, response boundary and both nested memif callers.
Partial serial responses and head/tail/body read/merge/write progress survive
fresh-process restoration. It calls the actual provider's `htif_exit` once;
a restored writeback never reissues that exit. Response 1 follows complete
writeback, including after the provider reports that it should exit.

The component's kind-34 / `firesim.tsi.syscall-exit.v1` image includes its
nested read and write images. The ordered restore transaction additionally
requires the serial FIFO and exact-provider lifecycle images. It parses and
allocates all three before checking caller/child/provider relationships and
publishing through the existing nonthrowing provider commit primitive.
Actual optional-exit presence and all 32 raw bits must agree with invocation
progress; stopped state is rejected. No service, startup, response or target
edge occurs during restoration. A component-only caller load additionally
requires its existing actual provider state to agree.

Other syscall selectors reject after request decoding and before host syscall,
exit, writeback or response. Unsupported endian policy and odd, nonzero-device
or wrapping commands reject explicitly. A callback exception poisons the
caller. Reentrant capture, restore, begin and advance reject. The existing
strict lifecycle signal policy and caller-held exclusion still apply.

This adapter is not wired into the live FireSim polling dispatch yet. Its
services require an independently owned polling response destination. Session
construction/descriptors, generic syscalls and their external effects, process
signal coordination, enclosing stop/return/context callers and coherent
simulator/bridge/memory publication remain pending. It does not enable complete
HTIF or CPU Level 1. The ordinary live path still uses installed `syscall_t`.

`verify_tsi_syscall_exit_vcs` compares the installed archive's unchanged
`syscall.o` and actual HTIF provider with an independent byte/transaction
oracle. Four scenarios cover command-address residues 0/2/4/6 and exit codes
0, 1, `0x7fffffff` and `0xffffffffffffffff`. Both native ASan/UBSan and VCS
producers capture every explicit operation boundary; fresh native/VCS consumers
restore every producer/cut pairing with complete pre-service readback. Operation
indices here are host-component boundaries, not Rocket target-cycle labels.
The CPU matrix records the accepted invocation and exact commands after all
checks finish. Diagnostic pilots and failures remain under
`automations/checkpoint_loop/runs/m11-iteration144/`.

The next integration must preserve these live-path details:

- `polling_services_t::dispatch` currently constructs the installed callback
  and calls `default_devices->list`. Route only the explicitly admitted parent
  through a resumable service; return blocked to unwind both guards before
  `run_host` switches context. Reentering installed dispatch would reread the
  request and can repeat an exit or writeback.
- Bind `respond(1)` to the destination polling owner's queue. Preserve pending
  fromhost traffic even after `should_exit()` becomes true; stop belongs after
  the polling caller reaches its complete boundary.
- Runtime reads and write-merge reads must retain the program's cache-flush
  packets. Writes must use the current FireSim write/flush policy. Immutable
  flush configuration belongs to startup/aggregate binding, not raw host
  pointers or a saved stack.
- The direct-exit recorder cannot represent syscall termination: it currently
  remains running when installed `sys_exit` sets the actual optional exit.
  Extend the enclosing termination ownership explicitly; do not manufacture
  a direct odd command or stop immediately after the syscall exit service.
- Extend cross-owner polling admission and simulator publication together.
  A restored parent alone does not authorize context entry, default-session
  reconstruction or CPU checkpoint requests.

Accepted iteration-144 evidence: `recipe-syscall/invocation-9b6f2981/summary.json`
and `syscall-independent-audit.json` under the diagnostic root above. All
1,200 restores / 141,408 owner readbacks / 45,936 host operations pass.
The independent auditor rejects twelve incomplete/duplicate evidence variants.
Both exact-recipe default/buffered four-hart controls pass at C=3,329,794;
eight native regression suites, thirty retained auditors and independent
four-cut ordinary RTL replay also pass. Full commands and artifact paths are
in the CPU matrix and the diagnostic catalogs. None of this enables CPU Level 1.
