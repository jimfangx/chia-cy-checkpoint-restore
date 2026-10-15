# Default HTIF BCD pending reads

Iteration 110 adds the production `firesim_tsi_bcd_t` component. The default
HTIF dispatcher registers it as device 1 after startup. Custom-device and long
option configurations retain their installed HTIF path. This component does
not enable complete HTIF, TSI or CPU checkpoint admission.

Installed FESVR `bcd_t` retains pending reads as `command_t` objects containing
callbacks into its caller. The new component stores the ordered raw 64-bit
commands. Its destination response sink is constructed from the destination
polling owner, rather than deserialized from a source pointer or coroutine.
Each completed tick consumes at most one terminal byte and publishes exactly
the response that installed FESVR would produce, including NUL and 0xff input.
Writes, identity strings, command identities and null commands keep their
installed behavior.

The `firesim.tsi.bcd.v1` image has widget kind 26, fixed device number 1,
configured queue limit, pending count and every pending command. It validates
the entire image before swapping the live queue. Wrong schemas, configurations,
lengths, command tags and excessive counts reject atomically. Capture and
restore reject during a device service. An interrupted service poisons the
component because input or output may already have escaped to the terminal.

`firesim_tsi_t::bcd_owner()` exposes this separate component once default
polling starts. The existing eight-owner polling inspection remains an
inspection of its original boundary; it does not certify BCD, syscall or
terminal ownership. Metadata preparation does not construct or resume BCD.

The terminal remains external state. This component does not capture stdin
position/readiness, stdout effects, terminal modes or the installed process-wide
terminal object. A complete checkpoint must either own a deterministic terminal
transport or reject that configuration. Syscall file descriptors, HTIF
stop/exit/signature/signal state, expected XLEN/build compatibility, context
replacement and atomic cross-owner reconstruction also remain pending.

`verify_tsi_bcd_vcs` compares the production component against the installed
BCD implementation in separate native and VCS processes. It captures all
completed-call boundaries around multiple pending reads, absent input, ordered
responses, identity memory writes and terminal output. Fresh sanitizer and VCS
processes read back the complete queue before services and compare continuation
events and terminal bytes. Invalid images are followed by a valid load in the
same fresh process. A valid semantic image with a dropped pending read must
diverge at its first missing response, host event 11. These event labels are
host-component service boundaries, not semantic CPU target cycles.

The installed-FESVR integration path loads the real test ELF through FireSim's
partial-write read/merge, captures zero/one/two pending BCD reads at suspended
polling cuts, then supplies delayed terminal input, checks both actual serial
fromhost writes and finishes through HTIF PASS. Complete CPU continuation and
independently captured CPU RTL replay remain unverified. Exact artifacts and
commands are recorded in [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).
