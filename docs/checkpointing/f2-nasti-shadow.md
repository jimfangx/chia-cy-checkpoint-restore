# Checkpoint NASTI adapter observation

Iteration 263 extends the real `CheckpointCaptureWidget` shadow to layout 2.
One ungated positive edge samples the transport controls, eight original widget
locals and all 38 original NASTI adapter registers into the same immutable bank.
The accepting edge observes pre-edge values; the adapter and stream continue
servicing MMIO/DMA while the host reads the bank. This remains an observation,
not a complete Level-1 image or a capture/restore ownership exemption.

The adapter contributes 530 canonical bits. The ordered fields are `aw`, `wd`,
`ar`, followed by `haveAW`, `haveW`, `haveAR`, `badW`, `busy`, `writing`,
`responseValid`, `responseError`, `responseData`, `responseId` and
`errorReadRemaining`. Each address channel includes address, length, size,
burst, lock, cache, protection, QoS, region, ID and user. Write data includes
data, last, ID, strobes and user. Address/ID slots are zero-extended to 64 bits;
all other widths remain exact. Unsupported data/address/ID geometries and
changed channel fields reject elaboration. The generated header records every
canonical field's offset and width. At 32-bit address / four-bit ID geometry,
the 530-bit vector carries all 226 original register bits plus canonical zeros.
The fresh exact Rocket diagnostic instead has 32-bit addresses / 12-bit IDs:
its 38 original registers carry 258 bits, with 272 canonical zero-padding bits.
An independent audit binds every original StateID, native-inline storage rename,
width and canonical offset to that actual generated source and checks seven
corrupt ownership/slot descriptions. All 38 remain explicitly uncovered for
capture/restore ownership; observation does not reduce the ownership deficit.

The low control/local layout is preserved. Nonphysical snapshots are now
1,169 bits; physical snapshots are `1,239 + GATES` bits. Read-only MMIO at
`0x98` returns layout version 2, and `0x9c` returns the exact bit count.
The host checks both, then the word count, before requesting a staging epoch.
This rejects an old layout or a stale header even when its rounded word count
matches. Failure retains freeze and validated frame history; recovery discards
only an epoch the session could have created. A foreign occupied bank is
preserved. ASan/UBSan tests include incompatible version and exact-bit-count
failures before staging mutation, in addition to retained transfer/recovery cases.

The compiler coverage test independently lowers actual adapter elaborations at
8/1, 32/4 and 64/64 address/ID widths and enumerates every original register.
It rejects missing, invented or differently shaped entries. EDA VCS compares
canonical vectors with original registers under full protocol checks and 3,000
random traffic steps at each width, retaining debug waves. Widget MMIO tests
reconstruct expected snapshots directly from original transport, parent and
adapter registers at the accepting edge, never from the producer's exported
vector or saved payload. A separate waveform reader reconstructs the entire
bank from the original registers. Compiled observation and staging mutations
must fail these independent oracles.

Production image admission remains closed. The eight self-freezing parent
locals, opaque transport, stream engine, staging bank, physical primitive
encoding and complete host/reset/external-writer ownership still need an atomic
capture/restore contract. Functional DRAM, pre-FAME semantic mapping and complete
CPU/common-cut coverage remain required. Observation taken after a stopped
target does not by itself establish that these live owners represent a valid
restore epoch. No full image timing closure, AFI deployment, FPGA-origin capture
or paired CPU migration is established by component synthesis or EDA tests.

Current commands, source snapshots, native DCPs, EDA logs, debug waveforms and
independent audits are retained under `runs/aws-f2/iteration263/`. Verification
results and any failed development attempts are recorded there and in the
current progress entry; historical iteration-262 evidence remains unchanged.

Native verification passes seventeen OOC scopes. The expanded physical widget
uses 2,766 LUTs / 1,978 registers, including 1,040 audited positive-edge raw-clock
shadow registers. The source-policy component uses 5,872 LUTs / 3,114 registers /
six BUFGCEs; its 140 MHz OOC setup/hold estimates are −0.179/−0.074 ns with
unconstrained I/O. These are component resources and timing, not full-image
closure. Thirteen initial current-turn native receipts were retained only after
source/input/artifact validation; three missing-XDC preparation failures were
rerun after the actual native `WriteXDCFile` emitter produced all four required
connected constraint sets. Failed receipts remain unchanged. Java generation/emission finished before each native synthesis phase and did
not overlap synthesis, whose concurrency stayed at or below two.

Final EDA validation passes all seventeen native-bound scopes and all retained
waveform audits. The expanded physical fixture completes six component cuts /
240 complete shadow word reads / 65,361 checks / 3,851 stalls, with reset recovery
to cycle 96. Separate source-register waveform reconstruction and all eight
rehashed physical evidence corruptions pass. Retained checks pass 336 Python /
45 manager tests, 319 Scala / 49 suites plus twelve preparation tests, 9,366
adapter state comparisons across 9,000 random steps, 130 standalone captures /
4,992 word reads and 1,890 ASan/UBSan host checks. Both compiled observation and
staging defects reject; staging stops at its first differing word before AXI
read acknowledgement. Final independent source/receipt/protection/resource
integrity audit passes. These component results leave hardware/CPU acceptance
in progress.
