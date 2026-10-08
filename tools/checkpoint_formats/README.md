# Checkpoint container v1

`codec.py` is a standard-library-only container prototype. It does not capture,
restore, discover state, or certify completeness. The caller must provide an
expected build identity to `decode(data, kind, expected_build)` before state is
returned. `encode(kind, document)` validates and returns deterministic bytes.

Each file contains an eight-byte type/version magic, an unsigned big-endian
64-bit JSON payload length, canonical ASCII JSON, and a 32-byte SHA-256 digest
of the header and payload. The exact file size must be `16 + payload_length +
32`. The checksum detects accidental corruption; it is not authentication.
JSON uses sorted keys, no whitespace, and no duplicate keys. Unknown fields,
versions, noncanonical encoding, trailing data, and invalid values fail with
`FormatError`.

All documents have `format_version: 1`, `checkpoint_type`, `target_cycle`,
`target_clock_phase: "before_rising_edge"`, `build`, and `records`. Cycle C
means immediately before target rising edge C. Trace inputs are the values to
apply for that edge; outputs are the values to compare immediately before that
edge after input settling. No host-cycle interpretation is implied. Other
phases and multiple clock domains are not represented by this prototype.

| Type | Magic (hex) | Build keys in addition to target_configuration and rtl_build_hash | Record fields |
| --- | --- | --- | --- |
| fsckpt | 4653434b50540001 | golden_gate_build_hash, simulator_build_hash, state_manifest_hash | owner, width, value |
| rtlckpt | 52544c434b500001 | state_manifest_hash | state_id, width, depth, values |
| trace | 5452414345000001 | boundary_manifest_hash | cycle, inputs, outputs |

Build hashes and semantic IDs are lowercase 64-digit SHA-256 strings.
Simulator owner names refer to entries in a future simulator ownership
manifest, independently of semantic StateIDs. Records are sorted by owner or
StateID and cannot repeat. Semantic memory `values` are in ascending zero-based
address order; registers have depth one. Values are unsigned raw bits written
as lowercase hexadecimal with exactly ceil(width/4) digits, bit zero least
significant, and zero padding above width. Signed state preserves its raw
two's-complement bits. Width and depth must be positive; X/Z fail explicitly.

Trace records cover consecutive target cycles starting at `target_cycle`.
`inputs` and `outputs` map signal names to `{width, value}` bit vectors. Empty
record lists are valid at the container level for empty inventories or zero-length
traces. `semantic.py` enforces complete Level-2 membership, widths and depths against
the compiler manifest; its `encode_semantic(document, manifest)` and
`decode_semantic(data, expected_build, manifest)` are the entry points for semantic
checkpoints. The low-level codec does not establish completeness. Level-1 ownership
and trace boundary coverage validation remain future work. ASIC netlist metadata is intentionally unsupported in
v1; no gate-level mapping or power analysis is claimed.

Run from the Chipyard root:

```sh
python -m unittest discover -s tools/checkpoint_formats/tests -v
```

The opt-in Golden Gate CLI flag `--semantic-checkpoint-root Top.dut` invokes
`midas.checkpoint.SemanticStateInventory` after target lowering, before
`MidasTransforms`. It emits `<output-base>.semantic-state.json` and the same
uninstrumented circuit as `<output-base>.semantic-reference.fir`. The reference
includes the enclosing harness; select the recorded DUT module and its reachable
modules when emitting clean RTL (as the compiler test does).

The v1 manifest contains a single selected DUT clock domain and sorted entries
for each lowered scalar register and logical memory. Aggregate registers/arrays
become individual lowered members (e.g. `bank_0`). StateID is SHA-256 of canonical
JSON `{hierarchy,kind,namespace:"pre-fame-state-v1"}`. Width/depth and reference
hash are part of manifest/build compatibility, not the ID. IDs are independent
of declaration order and final Verilog names; this does not promise stability
across source renames or different target lowering algorithms. Manifest hash is
SHA-256 of its canonical JSON bytes. Signed values keep their raw bits.

Opaque modules, unresolved/non-bit state, derived/gated clocks, asynchronous
resets, multiple target clocks, and memories with read latency other than zero,
write latency other than one, or readwrite ports fail explicitly. Synchronous
memory read pipelines need their own inventory before support can be enabled.
No memory ports are added. This is discovery/serialization, not hardware capture
or mapping through FAME; the reference manifest is retained as a separate artifact.

For real compiler-artifact verification, run the Scala inventory suite with
`CHECKPOINT_TEST_ARTIFACT_DIR` set to a directory, then from the Chipyard root run:

```sh
python -m tools.checkpoint_formats.tests.verify_inventory automations/checkpoint_loop/runs/m1-inventory
```

The emitted checkpoint values are deterministic test data, not a captured execution.
The clean VCS testbench is `tests/InventoryDUT_tb.sv`; it exercises the emitted
pre-FAME RTL. Verification outcomes and current tool blockers are recorded in
`docs/checkpointing/progress.md`.
