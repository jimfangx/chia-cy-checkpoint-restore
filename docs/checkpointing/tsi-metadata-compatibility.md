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

There is an additional installed-library resource limitation: `elfloader.cc`
throws `incompat_xlen` after `mmap` and before its final `munmap`. A rejected
XLEN preflight therefore retains that library-owned mapping until process exit.
The current checks establish unchanged metadata and seven peer components;
they do not certify resource-atomic rejection. Fix and audit the loader's error
cleanup before enabling complete host checkpoint admission. The installed
Conda library and headers have not been modified. The fresh sanitizer diagnostic
`runs/m11-iteration111/elf-loader-resource-diagnostic/summary.json` confirms two
retained mappings after two rejected preflights, followed by successful valid
retry. Its initial relative-ELF-argument pilot rejects the different argument
contract; the corrected invocation uses the captured absolute ELF argument.

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
