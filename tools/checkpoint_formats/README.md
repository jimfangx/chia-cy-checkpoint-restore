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
| fsckpt | 4653434b50540001 | golden_gate_build_hash, state_manifest_hash | owner, width, value |
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
record lists are valid for empty inventories or zero-length traces. The future
manifest integration must enforce full membership, widths, depths, boundary
coverage, and supported clock/reset semantics. Hash comparison alone does not
prove these properties. ASIC netlist metadata is intentionally unsupported in
v1; no gate-level mapping or power analysis is claimed.

Run from the Chipyard root:

```sh
python -m unittest discover -s tools/checkpoint_formats/tests -v
```

These are serialization tests; VCS metasim and ordinary RTL VCS integration
remain outstanding alongside pre-FAME state discovery.
