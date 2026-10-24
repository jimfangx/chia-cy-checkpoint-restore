# RAM-style constraints in checkpoint banks

The exact Rocket recipe produces public RAMStyleHint XDC annotations on the
CPU-managed stream FIFO memories. The bank validator now accepts the five
native templates (ULTRA, BLOCK, REGISTERS, DISTRIBUTED and MIXED) only for one
exact retained logical memory in the synthesis destination. Memory ports,
indices, ordinary registers, foreign/dead/missing paths, arbitrary memory
snippets and regexp-active explicit names remain unsupported. Normal memory
inventory and bank-generation rules still apply; accepting a hint does not
establish a supported physical RAM mapping or complete checkpoint ownership.

Specialization preserves the annotation's public/internal class and correlated
instance path. Original and translated annotation hashes and mappings remain in
the bank binding. The final native WriteXDCFile consumer now handles both public
and internal annotations. This is necessary for host widgets elaborated after
the early external-to-internal conversion; their public hints were previously
left unconsumed. Both forms retire at actual XDC emission. Tests run the real
consumer without a test-only conversion and cover the final compiler path.

The initialized-memory fixture has two separately owned 9-bit, eight-word RAMs,
separate hex/binary initialization, one public hint and one internal hint. Its
emitted synthesis constraints select `a/ram_reg.*` and `b/ram_reg.*`; the
implementation file has no constraints. The independent literal audit checks
class, destination, format, complete memory identities, circuit/annotation hashes
and exact emitted constraints. Twelve corruptions reject, including coherent
annotation rehashes, aliases, missing/extra constraints and incomplete owners.
Native Vivado reads the actual generated synthesis XDC; fresh EDA VCS checks
complete initialized readout, stalled bank responses and continuation against
original RTL with a public-input oracle and debug waveforms.

This is a compiler/component increment. The native constraint uses Vivado's
memory-cell `_reg.*` suffix convention; it does not expose arbitrary state over
DMA. The exact Rocket production compiler and all physical CE-latch/common-cut,
memory/timing/bridge/host/pre-FAME coverage requirements remain authoritative.
Full image/P&R/AFI, physical FPGA cuts, paired CPU restore/finite/live acceptance
and rolling hardware recovery are still pending. Reuse the iteration-194
ExternallyProvisioned localhost invocation and initialized manager inputs.

Fresh iteration-213 logs and exact commands are beneath
`automations/checkpoint_loop/runs/aws-f2/iteration213/`. See `summary.json`,
`verification-commands.json`, `remaining-blockers.json` and `final-audit.json`
there for final results; original failed attempts are preserved separately.
