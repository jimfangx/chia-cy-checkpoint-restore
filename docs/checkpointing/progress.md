# Checkpointing progress

Current milestone: M1-schema-and-stateids, iteration 3. In progress.

- Implemented strict independent v1 .fsckpt, .rtlckpt, and .trace container codecs in tools/checkpoint_formats/codec.py. Includes deterministic serialization, SHA-256 header/payload checksums, exact length checking, mandatory build compatibility, raw arbitrary-width bits, memory address ordering, and explicit rejection of X/Z, unsupported versions/phases and malformed records. Semantic/trace compatibility does not depend on the Golden Gate build.
- Six unittest cases actually passed, covering all single-bit corruptions and truncations of each sample format, round trips through 1025-bit memory words, build/type mismatch, invalid schemas with valid checksums, duplicate keys and target-cycle sequencing. Log: tools/checkpoint_loop/runs/m1-formats-tests.log. Format contract and limitations: tools/checkpoint_formats/README.md.
- This is a focused container increment, not M1 acceptance. Missing: pre-FAME discovery and StateID derivation, semantic/ownership/boundary manifest membership validation, test DUT with FSM/register array/SRAM and same-module instances, compiler tests, and VCS metasim/clean RTL execution. No capture/restore, formal, ASIC activity, or FPGA validation is claimed. No external dependency blocker was encountered in this increment.
- Next: implement the opt-in discovery hook at GoldenGateCompilerPhase.loweredTarget, retaining an uninstrumented replay reference; reject opaque/unsupported state explicitly. Connect generated manifests to codec validation so incomplete or wrong-shaped records fail even when the supplied manifest hash matches. Exercise the actual compiler and test DUT before declaring M1 ready.

Previous M0 context (source reconnaissance complete):

- Created the previously missing reconnaissance.md with 119 checked source links, current revisions, compiler pass order, an explicit post-target-lowering/pre-MidasTransforms StateID hook, GCD instance/register trace, and the known Level-1 RTL/software/transport owners.
- Documented exclusions: FAME5 missing rename handling, optional RAM replacement, opaque sequential state, unsupported clock/reset semantics, partitioned systems, unsaved drivers/external inputs and incomplete capture cuts. These are requirements for future rejection, not implemented checkpoint support.
- Verified documentation/source anchors, tool entry paths and the GCD VCS metasim make recipe with `make -n`. VCS identification succeeded using -full64 and the existing conda library path. Jasper identification succeeded using -allow_unsupported_OS. Logs are in verification.log.
- No RTL/compiler implementation changed. No metasim or clean-RTL execution, checkpoint/replay, license checkout, formal proof, ASIC power or FPGA validation was performed. M0's checks are source reconnaissance checks.
- Existing dirty conda/checkpoint-loop files and untracked plans/PDFs were preserved. No commit/reset/clean was performed.

Next milestone: M1 semantic discovery and independent checkpoint formats. Insert an opt-in explicit hook at GoldenGateCompilerPhase.loweredTarget; retain a clean replay reference and instance-qualified identity. Test two same-module instances, registers/FSM/array/SRAM, deterministic serialization and explicit unsupported/lost-state errors. Do not use final Verilog names as stable IDs. Investigate the discarded host-lowering return value before depending on HostTransforms. M2 uses VCS metasim and ordinary clean RTL VCS; keep Level 1 and Level 2 independent.

Environment note: Chipyard HEAD changed externally during M0 from f0914763d010669c2b194c7fcd6fd8290ba21750 to a6295df2d9e691aa115f5409ec4bfbfe6b5ed80b (test acct). Initial dirty files disappeared from status; this agent did not edit or commit them. FireSim HEAD stayed 2650ce60df882c32c18008357839c1856490a87c.
