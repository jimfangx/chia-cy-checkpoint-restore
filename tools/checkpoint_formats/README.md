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
boundary manifest. ASIC mapping is a separate build-bound artifact; it does not
change either checkpoint container or combine Level-1 and Level-2 state. The
initial mapping capability and its limitations are described below. No ASIC power
analysis is implemented by these codecs.

Run from the Chipyard root:

```sh
python -m unittest discover -s tools/checkpoint_formats/tests -v
```

`formal_state_map.py` exports `asic_state_map.json` from actual Formality passing
sequential compare points. It checks complete original semantic bits and complete
gate storage independently, rejects black boxes, and binds the RTL, mapped
netlist, cell models, library, scripts and proof/synthesis evidence by SHA-256.
Both CAD scripts export hashes of the files they actually read, checked before
and after the tool run. Changing a netlist cannot reuse a stale successful proof.
The current capability is one flat DUT with retiming disabled and audited scalar
cell storage. RAM mapped to individual flip-flops is supported. Real Genus,
Formality and VCS profiles cover polarity, indexed scalar destination reordering,
duplication and merging. Shared storage requires agreement among every semantic
source after proven polarity transforms. Version-3 maps additionally preserve
unread original StateIDs with empty gate destinations, only when explicit tool
classification agrees with the hash-bound human unread-point report. Missing
classification, contradictory classifications, unproven gate storage and unknown
SRAM macros reject explicitly. Version-4 maps support omitted constant register
bits with separate hash-bound Jasper predicates from `constant_state.py`.
Unconstrained one-edge assertions must be proven, with covered antecedents and
edge coverage; bounded, vacuous or missing proofs reject. Checkpoints before
C=1 or with a conflicting constant value reject before deposits. SRAM macro
initialization requires an additional audited adapter.

`gate_deposits` revalidates the map and independent Level-2 checkpoint before
returning storage deposits. The existing VPI loader resolves escaped synthesized
instance names, prevalidates every handle before writes, and reads back complete
state before any target edge. It never forces output wires. The small-DUT verifier
uses Genus with an explicitly artificial standard-cell test library, Formality,
Jasper for constant predicates, and ordinary VCS. This establishes functional
state correspondence and replay,
not a process library's timing, power, physical ASIC or FPGA validation.

```sh
source env.sh
source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_formal_state_map \
  --out automations/checkpoint_loop/runs/m8-validation
```

Use `--constant-registers` to exercise observable constant propagation together
with unread state, optionally adding `--profile inverted`, `--duplicate-registers`
and `--reorder-registers`. The verifier launches Jasper in batch mode with the
required unsupported-OS switch on this machine; original RTL remains unchanged.

Combine `--merge-registers` with `--optimize-registers` or `--constant-registers`
to select original DUT fixtures with merging and eliminated state together.
Both polarities and `--reorder-registers` are supported. The gate-reference
proof must establish every original alias; unread evidence belongs to the
original RTL on the implementation side. Constants still require independent
Jasper predicates. Unread bits cannot excuse conflicting merged values or
constant checkpoint values. Combine `--merge-registers --duplicate-registers`
to select the complete-state Jasper adapter in `relational_state.py`, optionally
with inverted polarity and destination reordering. Version-5 maps require an
unbounded induction assertion for every candidate state relation and equivalence
of every output under the full relation, without reset or input assumptions.
Covered assertion antecedents, two-sample relation coverage and both values of
every physical bit prevent vacuous acceptance. The checkpoint loader enforces
the relation at initialization, including agreement among merged sources.
Every original and physical bit must be represented; missing aliases/copies,
bounded proofs and changed scripts/miter/input identities reject. Add
`--optimize-registers` for version-6 maps that also retain eliminated original
register bits. These bits are absent from the relation, so preservation and
output equality must hold for their arbitrary values and evolution. Both values
of every omitted bit must be covered under the relation. The map records proven
unread state with empty gate destinations; the verifier flips every unread
checkpoint bit and checks fresh RTL replay and identical gate deposits. A fresh
proof with that state connected to an output or a register's next-state update
must produce a counterexample.
Add `--constant-registers` for version-7 maps combining native merging,
duplication, unread state and observable constants. Constant bits remain in the
semantic inventory with empty gate destinations. Their candidate values enter
the initial relation and must preserve it across every edge. Separate Jasper
predicates must establish those exact bits/values from arbitrary original state
after one edge; the loader enforces C>=1 and the values before deposits. A
complete relation PASS cannot replace these independent predicates. Missing,
bounded, vacuous or mismatched proofs reject. The verifier also exercises a
conditional constant update whose complete relation passes while its independent
constant predicate fails, conflicting checkpoints and zero-edge RTL divergence.
These fixtures use flip-flops
for logical RAM; SRAM macros still require a complete storage adapter.

The verifier produces a fresh invocation directory, raw passing/matching reports,
source hashes, semantic checkpoint/trace, complete map, zero-edge gate readback,
healthy uninterrupted/restored comparisons and real formal/simulation failures.
`tests.audit_formal_state_map --run <invocation>` independently audits the reports,
containers, captured state, netlist inventory and every replay boundary without
importing the exporter or codec. Recovery and current M8 scope are recorded in
`docs/checkpointing/m8-formal-state-map.md`.
Use `tests.audit_relational_state_map --run <invocation>` for version-5/6/7 profiles;
it checks the miter, individual raw engine results, inventories and replay.

`python -m tools.checkpoint_formats.tests.verify_formal_missing_proof --out <runs-directory>`
performs fresh Genus/Formality builds in both polarities and checks that global
equivalence still rejects four unclassified constant bits without Jasper state
predicates. Source both project environments and `vcs-env.sh` last. Each call
allocates a new invocation directory, preserving prior raw evidence and recording
commands, input hashes and the exact export rejection in its own summary.

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

`finite_replay.py` supplies the independent DESSERT consumer for schema-1 and
schema-2 boundaries. Its `package` command converts complete recorded `DATA C
...` boundary rows to the checksummed `.trace` container beside an independent
`.rtlckpt`. Its `replay` command validates both containers, the complete state
and boundary inventories, and proven forwarded clock aliases, then generates
`replay.sv`, DUT-only `clean.sv`, `restore.txt`, `trace.txt` and hash metadata.
Trace rows remain data; the generated SV size does not grow with trace length.
All words are read back before the first edge. VPD captures the full hierarchy
and every semantic RAM address through explicit `$vcdplusmemon` calls. Convert
with `vpd2vcd -full64 +includemda` to retain memory visibility in VCD. Replay
requires the original RTL/manifests and finite Level-2 inputs; it does not load
a Level-1 image, link FireSim, or connect to FASED. Deliberate debug RTL variants
must retain the original state/port shapes and single-clock emitter grammar;
their RTL hash is recorded separately from the capture build identity.
Commands, acceptance scope and limitations are documented in
[M7 finite replay](../../docs/checkpointing/m7-dessert-replay.md).

`live_shadow.py` extends that same strict semantic oracle to two concurrent VCS
processes. It validates a standalone `.rtlckpt` and both complete RTL inventories,
then generates an authoritative gated-clock observer and an ordinary clean DUT
bench. For each actual target edge, the observer sends every boundary input and
output over `live_shadow_transport.cc`. The clean bench applies inputs, settles,
compares outputs, advances exactly one clock edge and acknowledges that cycle.
The authoritative edge remains blocked until acknowledgment. Clean outputs are
used only for comparison. No finite trace supplies future inputs.

The host transport binds the session to the checkpoint, manifests, configuration,
both RTL files and logical origin. It rejects malformed/unknown/padded values,
skipped cycles, incorrect acknowledgments, premature disconnects and existing
socket destinations; each peer operation has a 30-second deadline. A mismatch
exits immediately with its original target cycle and signal. The sustained
fixture option `+inventory-shadow-rounds=N` runs after all original directed
checks and alternates held responses and active traffic. Its default is disabled.
`tests.verify_live_shadow_vcs` exercises 1024 rounds and an actual clean-DUT
register corruption at cycle 29; `tests.verify_live_shadow_transport` checks the
native protocol with independent socket peers under ASan/UBSan.

This increment uses a freshly booted authoritative InventoryFixture. It does not
yet connect the semantic adapter to the audited FCFS/FASED Level-1 restored
metasim, and therefore does not establish the live restore milestone acceptance.

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

`verify_production_aggregate_vcs` links the actual production `entry.cc` with an
explicit `FS_CHECKPOINT_ENTRY` test capability. Entry constructs the generated
registry, metasim platform and FCFS driver once, using its normal construction
order. The capability factory validates configuration/libraries before platform
creation; its prepare hook runs before ordinary startup and can reserve the
fresh harness clock hold. A missing factory fails at link time and a null or
throwing capability fails the process. Default builds have no capability hook.
`checkpoint_request_t` parses public Level-1 requests before any factory or
platform construction. Empty paths, malformed options, duplicates and mixed
save/restore/preflight requests fail explicitly. A capability must override
`authorize_request` to support public durable requests; the test capability
inherits rejection. Entry checks generated widgets and concrete driver schemas
before passing the parsed request to `prepare`. Public restores must return
`restore_reserved`, so they cannot fall through to ordinary initialization;
captures must return `run`. This is a dispatch contract, not a durable runtime
implementation. `verify_checkpoint_entry` compiles actual entry with observer
platform/registry/driver declarations and verifies the dispatch paths with
native ASan/UBSan and VCS DPI. Its observers do not establish generated-state
restore correctness.

The full production aggregate verifier captures
the complete parked low-clock cut, writes a bound `.fsckpt`, loads all owners
in fresh VCS processes and compares every target FASED transaction port against
uninterrupted execution. It exercises native and late generated/harness
rejections before loading or clock advancement. Its default test capability
rejects public requests. With `--public-restore`, it instead links the concrete
`durable_restore_entry.cc` capability and feeds `.fsckpt` directly to public
`+fs-restore=PATH`. Public capture publication and normal Make integration
remain prerequisites for milestone acceptance. The capability's immutable
`runtime/compatibility` owner binds the explicit memory size, cycle horizon,
host delay/seed, zero VCS initialization, and SHA-256 of the executable and
every file-backed ELF object reported by `dl_iterate_phdr`. Unknown arguments
and preload/audit library hooks fail closed. Hashes and library membership are
rechecked at the cut, native
prevalidation/readback and exit. This compatibility owner uses OpenSSL libcrypto;
it does not capture library internal state or authorize arbitrary plugins.
`verify_runtime_identity` checks it with native ASan/UBSan and an independent
SHA-256 oracle, including changed library contents at the same pathname.
The public VCS capability loads Y-2026.03-SP1's `liberrindex.so` and
`libsystemcerror.so` before constructing this owner, retaining their handles
through shutdown. Both diagnostic tables are included in the complete hashed
ELF inventory for capture and fresh restore; any later ELF change still rejects.
Warmup requires the exact supported `VCS_HOME` and fails explicitly if either
absolute library path cannot be loaded.

`durable_restore.py` compiles the v3 profile's complete generated/harness/native
membership, shapes, schemas and build identities into the native consumer.
`durable_restore.cc` uses Boost.JSON compiled into the executable and OpenSSL
to validate one regular-file image: magic/size/SHA-256, canonical JSON and key
order, exact running-executable identity, all owners, every memory word's
padding, low clock/reset/finish values and the manifested FASED cycle counter.
Symlinks, special files and images over this audited profile's 256 MiB limit
fail explicitly. It produces an in-memory staging image; no external helper,
profile file or staging pathname is consumed by public restore. The capability
validates the container before platform construction, reserves fresh clocks,
and runs aggregate native/VPI prevalidation, complete readback and zero-edge
bootstrap. Capture requests and private staging bypasses remain fail closed.
`verify_durable_restore` compares native staging with the Python oracle under
ASan/UBSan; the full public verifier retains every continuation and transaction
comparison. The feature is opt-in for this audited VCS profile. Default builds,
other drivers and physical FPGA transport remain unsupported.

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
