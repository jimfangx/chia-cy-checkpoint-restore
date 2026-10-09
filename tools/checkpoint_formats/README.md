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
`target_clock_phase: "before_rising_edge"`, `build`, and `records`. For Level-2
checkpoints and traces, cycle C means immediately before target rising edge C.
Level-1 profiles separately bind the model counter and consistent-cut indexing
contract; the production v3 contract is described below. Trace inputs are the values to
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
checkpoints. The low-level codec does not establish completeness. `replay.py`
enforces complete trace boundary membership and widths against the compiler's
boundary manifest. Level-1 production ownership is still incomplete. ASIC netlist metadata is intentionally unsupported in
v1; no gate-level mapping or power analysis is claimed.

Run from the Chipyard root:

```sh
python -m unittest discover -s tools/checkpoint_formats/tests -v
```

The opt-in Golden Gate CLI flag `--semantic-checkpoint-root Top.dut` invokes
`midas.checkpoint.SemanticStateInventory` after target lowering, before
`MidasTransforms`. It emits `<output-base>.semantic-state.json`, the same
uninstrumented circuit as `<output-base>.semantic-reference.fir`, a DUT-only
ordinary RTL reference as `<output-base>.semantic-clean.sv`, and a complete
port list as `<output-base>.semantic-boundary.json`. The FIRRTL reference includes
the enclosing harness; the clean RTL contains only the selected DUT and reachable modules.

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
No memory ports are added. General mapping through FAME and hardware capture are
future work; the reference manifest is retained as a separate artifact.

`replay.py` provides a VCS backdoor oracle for a single hierarchy-preserving DUT
instance. It rejects missing, extra, renamed, reshaped, or threaded state and
boundary ports before generating a module bind. The bind samples the actual
gated DUT clock in the active region, before sequential NBA updates, including
every memory address and every boundary port except the implicit clock. Host
stalls do not advance the sample index. Checkpoints and finite traces use the
manifest-bound containers above; `.fsckpt` is independent and is not used.

After checksum/build/completeness validation, the replay generator creates an
ordinary DUT bench and a deposit list. `semantic_restore.cc` resolves and checks
all VPI handles before depositing registers and memory words through a DPI call.
The bench verifies every restored word before its first clock edge, drives each
recorded input, settles combinational logic, and compares every output before
the corresponding rising edge. It writes VCD waveforms. A mismatch names the
original target cycle and signal, expected and actual bits, and exits nonzero
through DPI (`$fatal` alone returned zero in the tested VCS release).

The executable M2 acceptance check exercises reset, active execution and memory
writes, a nonempty queue, an outstanding memory pipeline operation, and a held
response under backpressure. Each checkpoint starts a fresh clean VCS process.
It also injects a checksummed trace error and rejects invalid runtime restore
handles, widths, malformed data, and incomplete deposits:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
python -m tools.checkpoint_formats.tests.verify_semantic_vcs \
  --build automations/checkpoint_loop/runs/m2-metasim \
  --out automations/checkpoint_loop/runs/m2-iteration7/acceptance
```

This prototype covers the small InventoryFixture, including its target SRAM.
It does not establish Rocket/BOOM, multi-model/threaded FAME mappings, physical
FPGA capture, ASIC gate-level activity, or power estimation.

For real compiler-artifact verification, run the Scala inventory suite with
`CHECKPOINT_TEST_ARTIFACT_DIR` set to a directory, then from the Chipyard root run:

```sh
python -m tools.checkpoint_formats.tests.verify_inventory automations/checkpoint_loop/runs/m1-inventory
```

The emitted checkpoint values are deterministic test data, not a captured execution.
The clean VCS testbench is `tests/InventoryDUT_tb.sv`; it exercises the emitted
pre-FAME RTL. Verification outcomes and current tool blockers are recorded in
`docs/checkpointing/progress.md`.

`harness_restore.py`/`.cc` provide a separate fresh non-debug VCS harness
component loader at a settled low-clock cut, with exact source/geometry binding,
all-handle validation before deposits, first-edge guards and poisoned readback
failure. `verify_harness_restore_vcs` tests the actual harness and generated RTL
with recorded native DPI outputs. This is independent of semantic replay and
does not reconstruct the driver/DPI context or load a whole `.fsckpt`. Scope
and evidence are in `docs/checkpointing/m4-harness-bank-load.md`.

`+fs-driver-settled +fs-driver-lowclock` keeps the completed-operation driver
parked through the natural falling edge, captures all generated words and
software/harness banks with clocks low, then resumes the same dispatcher.
Published outputs settle and incoming latches refresh before the next rising
tick. Native phase checks reject mismatched harness clock flags. The strict
modifier requires a settled diagnostic request; it does not enable `.fsckpt`
loading. `verify_settled_boundary_vcs --lowclock` checks complete production
transaction traces, and `verify_lowclock_cut` compares every software/generated
owner with its rising-edge cut. See `docs/checkpointing/m4-lowclock-cut.md`.

`simif_emul_t::start_restored_driver` bootstraps the dispatcher component from
a freshly loaded incremental simulation flow at a low-clock returned-operation
cut. It skips the initial native tick and initialization, and returns at the
next normal yield or completion. Packed clock/reset/finish checks and unsupported
owner/lifecycle checks precede worker creation. The caller must separately load
native/generated/harness owners, publish outgoing banks and refresh incoming
banks before the first rising edge. Full checkpoint requests remain unsupported.
`verify_dispatcher_checkpoint_vcs` exercises the real pthread dispatcher with
fixture MMIO/RTL services, native sanitizers and fresh VCS DPI processes,
including outstanding native traffic and terminal zero-edge completion. See
`docs/checkpointing/m4-dispatcher-bootstrap.md`.

`simif_emul_t::arm_restored_driver` and the VCS harness task
`checkpoint_resume_restored` connect component loading to the actual DPI
publisher. The harness holds its clock low while armed, reconstructs the worker,
publishes its outgoing banks, and refreshes incoming latches before allowing the
first edge. Terminal bootstrap finishes with zero edges. Unsupported/repeated
startup and invalid phases fail explicitly. `verify_harness_dispatcher_vcs`
compares actual harness/generated/native/DPI continuations with a small audited
driver using fixture MMIO services. No production `.fsckpt` loader is enabled.
See `docs/checkpointing/m4-harness-dispatcher-integration.md`.

`aggregate.py` binds a complete aggregate to an explicitly audited runtime
profile, generated/harness inventories, ordered native owner IDs/schemas,
native implementation/configuration hash, and exact simulator executable hash.
It uses the existing `.fsckpt` container; generated and harness words have
separate namespaces and opaque native payloads preserve every byte, including
leading zeros. The cut records actual target time separately from host samples
and completed driver operations. Invalid checksum/build/membership/shape/phase
or reset/finish/clock values reject before staging publication.

`aggregate_packed.py` adds the explicitly bound v2 runtime encoding
`ascending_nibble_padded_words_v1` for large generated memories. Each
`generated-entry/<hierarchy>` record contains every address in ascending order,
with exactly ceil(word_width/4) hexadecimal digits per word. Its container
width includes that per-word padding; padding is checked at every address.
The manifest supplies actual word width/depth and rejects mixed encodings.
Native payloads and harness records retain their independent namespaces.
`FSGRTL2` local staging uses the same complete compiled entry table and VPI
prevalidation/readback as `FSGRTL1`, without millions of repeated path strings
in the durable file. Retained VPI handles/values still scale with word count.

The v3 packed profile also binds its target-cycle field to a manifested 64-bit
counter and records the separate host-sample indexing contract. Both the
container decoder and compiled coordinator check that counter before loading
any owner. The existing v1/v2 profiles and Level-2 formats remain independent.

Both aggregate APIs expose `publish_aggregate(...)` for validated durable
`.fsckpt` publication. `prepare_aggregate_restore(...)` also publishes staging
atomically. Complete container validation precedes temporary-file creation.
Each writer uses an exclusive private mode-0600 file in the destination
directory, flushes and fsyncs its contents, atomically replaces the destination,
then fsyncs that directory. Existing regular files are replaced; symlinks and
special files reject. Readers open once and validate those bytes. Concurrent
writers expose complete snapshots, with the last rename winning.

I/O errors propagate and never indicate success. `PublicationError.published`
is true if rename completed but directory durability was not confirmed;
the complete replacement may already be visible and must not be treated as
an unchanged previous checkpoint. A killed writer may leave a private
`.pending-*` file; it is neither a committed checkpoint nor automatically
removed by another writer. These APIs do not implement production entry
plusargs, rolling retention, FPGA transport, or Level-2 publication.

`verify_production_aggregate_vcs` uses a test entry that constructs the actual
generated production registry, metasim platform and FCFS driver. It captures
the complete parked low-clock cut, writes a bound `.fsckpt`, loads all owners
in fresh VCS processes and compares every target FASED transaction port against
uninterrupted execution. It exercises native and late generated/harness
rejections before loading or clock advancement. Production `+fs-checkpoint`
and `+fs-restore` remain unsupported; the durable runtime entry still requires
integration before milestone acceptance. The test entry's immutable
`runtime/compatibility` owner binds the explicit memory size, cycle horizon,
host delay/seed, zero VCS initialization, and SHA-256 of the executable and
every file-backed ELF object reported by `dl_iterate_phdr`. Unknown arguments
and preload/audit library hooks fail closed. Hashes and library membership are
rechecked at the cut, native
prevalidation/readback and exit. This test-only owner uses OpenSSL libcrypto;
it does not capture library internal state or authorize arbitrary plugins.
`verify_runtime_identity` checks it with native ASan/UBSan and an independent
SHA-256 oracle, including changed library contents at the same pathname.

`aggregate_restore.cc` consumes trusted local staging produced by the validated
container, using a compiled profile table. It validates every native payload
and both complete VPI tables before any native load or RTL deposit. Prepared
values are retained in memory, so commit does not reread component files.
Any failure consumes the coordinator; the caller must terminate that process.
Native readback, RTL settlement/readback, and the existing DPI bootstrap must
all finish with clocks held before release. `begin_restored_load` reserves that
fresh clock hold before any state is loaded; ordinary/direct startup and a
different or repeated reservation reject.

`verify_harness_dispatcher_vcs --aggregate` verifies this path with five fresh
fixture-profile checkpoints, actual generated RTL/harness/native/DPI state,
and fixture driver MMIO. This does not enable production `+fs-restore` or
establish production FCFS/FASED continuation. See
`docs/checkpointing/m4-aggregate-prevalidation.md` for the scope and evidence.
