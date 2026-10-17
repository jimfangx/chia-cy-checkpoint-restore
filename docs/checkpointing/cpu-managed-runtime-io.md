# Metasim CPU-managed stream I/O ownership

Iteration 164 adds the returned-call owner
`runtime/cpu-managed-stream-io`, schema
`firesim.emul.cpu-managed-stream-io.returned.v1`, to the production
`simif_emul_t` CPU-managed stream wrapper. The driver-boundary diagnostic now
includes this owner instead of an unsupported placeholder.

The wrapper retains only its simulator reference and AXI staging object between
calls. Its image binds all three AXI geometry fields and certifies that no
wrapper operation is active or poisoned. The simulator reference is rebuilt;
`runtime/cpu-managed-axi4` independently owns the complete pending AXI queues,
responses and in-flight flags. `CPUManagedStreamWidget` separately owns generated
stream parameters and its initialized flag. Generated RTL and harness owners
must cover the stream hardware queues and interface latches.

The exact Rocket header has no CPU-to-FPGA streams and four TracerV
FPGA-to-CPU streams, each 6,144 beats deep and 64 bytes wide:

| Hart | DMA address | Count-register address |
| --- | --- | --- |
| 0 | 0 | 1136 |
| 1 | 524288 | 1140 |
| 2 | 1048576 | 1144 |
| 3 | 1572864 | 1148 |

The complete generated inventory already includes the stream engine's 32
entries / 24,604 words: four queue RAMs, each 6,144 x 512 bits, plus 28
registers for pointers/full bits, read-beat counters, inferred read addresses
and control-register AXI state. These remain generated owners, not fields in
the new host image. The exact header/manifest hashes and every corresponding
state record are in `runs/m11-iteration164/rocket-stream-owner-inventory.json`.
This is a structural census, not a generated-state restore result.

An active DMA read owns its destination pointer, address, remaining transfer and
burst cursor on the driver stack. An active write additionally owns its source
pointer, strobe array and cursor. A count-register MMIO read can also suspend.
The new adapter rejects save, validation and loading while any such call is
active. Nested I/O rejects before another request or callback. Exceptions poison
the wrapper; loading an earlier idle image cannot erase an interrupted
continuation. These are rejected cuts, not serialized native stacks.

Checkpoint hooks perform no MMIO, DMA, initialization or advancement. Loading a
valid returned-call image only validates the exact configuration and zero flags.
It cannot clear an active/poisoned lifetime. Zero-byte transfers return zero
without issuing requests. Non-beat-aligned transfers fail explicitly: the CPU
stream drivers already require full beats, and the metasim request buffer copies
full beats. Unsupported transfer sizes also fail before submitting requests.

The caller must freeze both execution contexts before accessing these component
hooks, as for the existing AXI owners. This adapter supplies neither a process
exclusion policy nor a complete simulator transaction. CPU-managed streams still
reject in `begin_restored_load`, settled public capture and fresh dispatcher
admission. FPGA-managed host rings remain explicitly unsupported. The TSI schema
also remains unsupported for CPU aggregate admission.

The executable check exercises the actual production wrapper and dispatcher with
an independent synthetic AXI peer, under native ASan/UBSan and VCS DPI. Its
three geometries include the exact Rocket header's `{16,64,512}`; transfers cover
zero, one, 255, 256, 257 and 513 beats in each direction. A separate Python oracle
checks burst addresses/order, including remainder-first splitting. The C++ peer
checks every written byte/strobe and supplies independently calculated read
bytes. Fresh-process component restores read back both owners before starting
any dispatcher or allowing an RTL edge. Every suspended yield tests all three
checkpoint hooks and nested read/write/MMIO rejection. Malformed/configuration
images and interrupted lifetimes reject without changing AXI state.

This fixture does not restore a CPU `.fsckpt`, avoid ordinary fixture startup,
serialize target hardware or establish target-cycle equivalence. The matrix
records its scope separately from the retained Rocket workload and independent
Level-2 replay evidence. Complete Rocket Level 1 remains in progress. BOOM and
Saturn remain pending; standalone Shuttle, FPGA validation and ASIC power remain
outside scope. See [cpu-checkpoint-matrix.md](cpu-checkpoint-matrix.md) for exact
commands, source archives and results. Diagnostics are under
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration164/`.
