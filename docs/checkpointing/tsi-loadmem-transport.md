# TSI load-memory read transport

Iteration 97 fixes the production `tsibridge_t::handle_loadmem_read` path used
by the Rocket recipe. Previously, reads spanning multiple host-memory beats
repeated the first address and leaked each GMP export allocation. The earlier
eight-byte FESVR integration did not exercise that failure for Rocket's
two-word host beat.

`fesvr/loadmem_read_transport.h` now advances the translated address after each
consumed beat. It reads aligned host-memory beats and selects only requested
32-bit lanes, preserving zero, partial and full-width values in order. A bounded
word buffer owns the GMP export destination; a scoped GMP value is cleared on
normal return and on response/platform exceptions. The original bridge resumes
FESVR once after all requested response words have been sent.

Before any MMIO or response publication, the helper rejects zero, oversized
(greater than 4,096 bytes), non-word-sized, unaligned and wrapping requests;
zero, non-power-of-two and oversized beat widths; translated address underflow,
overflow and misalignment. Signed offset translation handles `INT64_MIN`
without signed overflow. These checks bind transport arithmetic, not the
complete CPU memory-region configuration or checkpoint image compatibility.

The native/VCS tests compile the production TSI bridge, loadmem widget,
FireSim/TestChip TSI and installed FESVR archive. Only the platform MMIO service
is a fixture. The independent Python oracle checks every address write, every
complete returned beat, selected response lane and word order. The matrix has
4/8/12/64/128/1,024/4,096-byte requests; 1/2/4/16-word beats; first/last lane
starts; zero/sparse/full-bit data; positive, zero and negative host offsets;
crossings of the low 32-bit address boundary; and valid unsigned/`INT64_MIN`
limits. Thirty-two malformed requests reject before I/O across both backends;
four injected callback faults exercise scoped cleanup under sanitizers.

The actual TSI bridge also loads the earlier partial-write RISC-V ELF through
its public `init`/`tick` interface. Its real FESVR read/modify/write path spans
two one-word beats and one two-word beat in separate runs. The complete MMIO
and serial transcripts match independent expectations, including original
aligned writes, eight merged bytes and six hart-reset serial words. These
fixture runs contain no CPU execution or target-cycle checkpoint cuts.

Two private header mutations reproduce a repeated beat and flip an actual
response bit. Native C++ and VCS each stop at the first wrong response without
acknowledging it. The DPI wrapper propagates native failure status because VCS
can return a successful process exit for `$fatal`. First-divergence labels here
are response-word positions, not Rocket target cycles or post-restore faults.

This synchronous helper introduces no checkpoint schema. Its caller, request
and response queues, bridge lifecycle, HTIF program/idle/reset continuations,
contexts, devices and generated MMIO/memory pipelines remain separate owners.
The aggregate TSI bridge remains explicitly unsupported; no checkpoint may
cut inside this transport call. Full Rocket Level-1 continuation and independent
Level-2 capture/readback/replay at active four-hart workload cuts remain pending.

Run from the Chipyard root; each nested native/VCS shell independently sources
the environments and pins the compiler/license helper last:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_vcs --out automations/checkpoint_loop/runs/m11-iteration97/transport-recheck
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_faults_vcs --out automations/checkpoint_loop/runs/m11-iteration97/transport-faults-recheck
```

Selected immutable evidence, source/workload hashes, exact recipe settings,
ordinary RTL readback and remaining CPU acceptance are recorded in
[cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md). Diagnostic runs remain
under `automations/checkpoint_loop/runs/`; plans remain read-only.
