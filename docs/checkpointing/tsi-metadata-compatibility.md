# TSI metadata compatibility

Iteration 111 extends the startup metadata component to image revision 2.
The complete canonical image includes the ELF, arguments, entry and symbols,
the destination load-memory capability, target endianness, chunk alignment and
maximum size, and the seven named pristine component images. Those pristine
images bind transport, initialization, idle/reset and serialization contracts;
they are not the live component state at the CPU cut. Legacy revision-1 images
and callers with incompatible contracts reject before metadata publication.

The installed HTIF's `expected_xlen` is private and its public setter is
nonvirtual. Tracking a replacement setter would miss changes through an
`htif_t` reference. Instead, capture and preparation preflight the sealed local
ELF through the actual installed `htif_t::load_payload`, with all target writes
suppressed by the existing preloaded guard. Entry and symbols must match the
independent probe. A rejected preflight clears its guard without publishing
metadata, entering a context, resetting the target or poisoning the caller.
The same destination can correct its configured XLEN and then prepare normally.

This checks compatibility with the current ELF. It does **not** serialize the
exact installed XLEN policy: zero (automatic) and 64 both accept this RV64 ELF
and produce the same component image. Full runtime/build identity and exact
HTIF configuration/state preservation still need aggregate ownership. Terminal,
syscall resources, stop/signature/signal state and contexts also remain pending.
Complete CPU checkpoint admission stays disabled.

Iteration 112 fixes the installed-library cleanup gap through a build-local
archive overlay. The original installed `libfesvr.a` stays unchanged. Only
`elfloader.o` is replaced; the other 13 members, including HTIF's private XLEN
policy implementation, are checked byte-for-byte. The repository-owned loader
retains the original ELF decoding and target-write code and gives its descriptor
and mapping scope-based cleanup on normal returns and C++ exceptions. Both
FireSim driver Makefrags and the native host regression runners use this overlay.
The production Makefrag additionally links the extracted loader member as an
object: an ordinary archive reference can otherwise be satisfied first by
`libriscv.so`. Final verification checks actual executable/shared-HTIF binding,
not only the archive path or object bytes.
Requested native rebuilds regenerate it even when the seed directory contains
an older report with an absolute output path.

The historical iteration-111 sanitizer diagnostic still records two leaked
mappings from two original installed-loader XLEN rejections. Native and VCS
negative controls compiled against that unchanged archive independently fail
the new kernel-resource check. The corrected overlay passes repeated XLEN and
endianness rejection, failed open/mapping, injected first/second memory-write
exceptions, and successful RV64/automatic-XLEN/BSS loads. Tests count descriptors
and `/proc/self/maps` entries directly; LeakSanitizer alone cannot detect these
mapping leaks. Startup metadata capture and fresh preparation also retain zero
leaked ELF resources through repeated incompatible-XLEN rejection and valid
retry. Metadata image revision 2 and its canonical bytes are unchanged.

This closes the loader-resource gap for the tested exception paths. It does
not make arbitrary malformed local ELFs safe to parse: original parser asserts
remain, and untrusted checkpoint bytes still reject against a complete canonical
image before entering FESVR. It also does not roll back ordinary target writes
after a memory exception. Checkpoint preparation suppresses target writes and
has separate complete component/mailbox readback checks. Startup loader stacks,
terminal/syscall resources, signal/lifecycle state and complete CPU ownership
remain outside this metadata component. Historical metadata audits continue to
run and explicitly report that they did not check resource cleanup.

The native sanitizer and VCS checks use the installed FESVR library. Both real
source loaders perform the partial-write read/merge and finish through HTIF
PASS. Fresh destinations read back every metadata byte and seven unchanged
component images before services or edges. Byte flips, every truncation, an
extension, the old image revision and a constructor-only load-memory mismatch
reject atomically. XLEN tests use the actual setter through a base reference,
check the installed exception's expected/actual widths, then correct the
configuration and successfully read back the complete image in that process.
These are host-component checks, not CPU checkpoint continuation or captured
semantic RTL replay. Exact artifacts and commands are in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md).

The next host assembly must account for installed FESVR resources as well as
the replacement polling loop. `syscall_t` duplicates stdin and stdout and owns
the target descriptor map, cleanup indices and chroot; its active memif calls
also retain local arguments. The inherited HTIF proxy still owns its own
unused descriptors when the replacement loop constructs a second proxy.
`term.cc` owns process-global saved termios and a restore flag; input readiness,
input consumption and output effects remain external. HTIF separately owns
raw optional exit code, stopped/signature state and process-global signal state.
The source-bound field inventory is retained as
`runs/m11-iteration111/remaining-host-owner-audit.json`. None of these resources
can be inferred from the BCD queue or certified by this metadata component.

The extra iteration-112 production transport sanitizer check exposes a separate
installed context lifecycle leak: `context_t::init` allocates a 1 MiB ucontext
stack, while its destructor only asserts that the context is inactive. Destroying
the fixture's two bridges with suspended contexts leaves two stacks allocated.
`runs/m11-iteration112/transport-context-diagnostic/summary.json` reproduces the
same 2,097,152-byte LeakSanitizer failure with the original installed archive and
the loader overlay. Both versions' native and VCS functional outputs match the
independent transport oracle and complete bridge images byte-for-byte. No
sanitizer check is disabled, and the native transport check remains **failed**.
The diagnostic's passing status confirms the pre-existing failure; it does not
certify resource cleanup or a passing transport sanitizer run. Context lifetime,
unwinding and any resources on suspended stacks still need explicit ownership.
