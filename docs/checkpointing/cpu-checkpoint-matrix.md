# CPU checkpoint matrix

Current milestone: M11 Rocket, iteration 114. Level-1 and Level-2 acceptance
remain **in_progress**. No CPU checkpoint continuation or clean CPU RTL replay
has passed. Physical FPGA validation, standalone Shuttle and ASIC power are
outside this matrix. The verified FCFS evidence remains in its existing docs.

| Family / existing recipe | Level 1 | Level 2 | Workload evidence |
| --- | --- | --- | --- |
| Rocket / `firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3` | in_progress: generated RTL inventory audited; TracerV and FireSim driver/termination-loop continuations pass; production TSI read, all four load-memory queues, bridge host control and FireSim idle/reset control pass fresh component restores; source-integrated FESVR serial FIFOs pass fresh component restores; serial-read progress passes complete fresh component restores; production TestChip initialization caller/serial-child dispatch and atomic four-owner component restores pass; program-load transport/entry/return ownership passes fresh component readbacks; production HTIF poll caller passes nine-phase fresh component continuations; suspended eight-owner inspection passes actual Rocket workload samples; exact-ELF startup metadata passes fresh host-component preparation/readback; default BCD pending commands pass fresh component continuation; metadata revision-2 transport contracts and installed-XLEN preflight reject atomically; build-local ELF-loader overlay closes tested descriptor/mapping exception leaks; context overlay owns inactive/thread-exit stack storage and rejects invalid lifetimes; complete HTIF/memif/device/context/TestChip-loader/cross-owner ownership and fresh CPU continuation pending | in_progress: complete ChipTop diagnostic inventory/readback retained; explicit event-phase image/replay contract passes ordinary RTL component checks; coherent metasim CPU capture/replay pending | Both complete default/buffered four-hart audit controls pass at C=3,329,794; every full trace and workload/store label matches; eight active host samples pass; CPU checkpoint cuts remain pending |
| BOOM / `firesim_boom_singlecore_no_nic_l2_llc4mb_ddr3` | pending | pending | No execution claimed |
| Shuttle + Saturn / `firesim_saturn_GENV256D128_shuttle_singlecore_no_nic_l2_llc4mb_ddr3` | pending | pending | No vector execution claimed |

## Rocket settings and artifacts

Read the current recipe YAML on every build; `tools.checkpoint_formats.cpu_recipe`
prepares source-hashed commands without enabling an unaudited checkpoint profile.
The exact settings are:

| Setting | Value |
| --- | --- |
| PLATFORM | `f2` |
| TARGET_PROJECT | `firesim` |
| TARGET_PROJECT_MAKEFRAG | `../../generators/firechip/chip/src/main/makefrag/firesim` |
| DESIGN | `FireSim` |
| TARGET_CONFIG | `WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig` |
| PLATFORM_CONFIG | `WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config` |

The manager resolves the recipe's relative Makefrag from `sims/firesim`.
Direct `make -C sims/firesim/sim` uses the same directory's absolute path.
The recipe also specifies frequency 140 MHz and TIMING build strategy; these
are retained in the recipe record, with no FPGA implementation invoked.
VCS uses Y-2026.03-SP1, `-full64`, `VCS_FLAGS=-Mupdate`, system GCC/G++ 13,
and the sourced Conda library/include directories. No Conda files are edited.

## Iteration 114: default HTIF device lifetime

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration114/`.
Both CPU levels remain **in_progress**. The production default HTIF syscall
device and device table now belong to the TSI object, with explicit release
after normal `stop()`. This releases their command tables and three duplicated
standard-stream descriptors when a suspended TSI is destroyed. See
[tsi-default-device-lifetime.md](tsi-default-device-lifetime.md) for ownership
and limits. Semantic device state and aggregate CPU restoration remain pending.

`device-lifetime/invocation-as3onvw3/summary.json` passes native ASan/UBSan and
VCS DPI checks: 176 actual TSI instances per backend, 11 cuts with 16 repetitions,
128 suspended callers and 32 completed callers per backend. Every teardown
preserves the exact descriptor map; initialized/active/completed counts, ELF
load/merge packets, BCD pending command, installed syscall packets and stop/exit
results also match. The original source/header reproduce three leaked
descriptors at the first polling cut. Earlier runner/packet-expectation pilots
remain separately retained. These are host resource tests, not CPU checkpoints.

Fresh native resource check (a new invocation is allocated on each run):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_device_lifetime_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration114-controller-rechecks/devices \
  --negative-control-source automations/checkpoint_loop/runs/m11-iteration114/original-default-devices/firesim_tsi.cc
```

All eight final preserved native suites pass, including 267 Python tests, FCFS
and both small fixtures. The first regression invocation was invalidated by a
test-source change; its failed source-stability guard is preserved separately.
The final invocation binds the unchanged final source. Startup metadata retains
12 fresh readbacks, 84 peer images, 13,852 atomic invalid images, 18 incompatible
cases, 192 installed-XLEN rejection/recovery checks and 704 loader resource cases.
Three complete CPU requests and all 16 invalid host-audit options reject before
execution/publication. All 11 retained host suites, serial and transport-fault
suites pass. All 17 independent component/native audits pass. The fresh ordinary RTL
pattern diagnostic passes all 318,637 words before any edge; it is not captured
semantic state/replay. All 137,659 sealed iteration-113 artifacts and 1,018
native input bindings pass preservation checks. Existing controller-created
iteration-113 commits are published FireSim first, then Chipyard; queried tips
match. Local tracking-ref refreshes failed on read-only `.git` after successful
remote updates. No staging, local commits or protected-input edits were made.

Fresh exact-recipe four-hart controls (complete runs and trace comparisons):

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration114-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration114-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration114-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration114/rocket-controls/invocation-ed0qjmsv/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

The resource test's actual native VCS executable is
`device-lifetime/invocation-as3onvw3/simv`; its `commands.json` records the exact
Y-2026.03-SP1 `-full64` build and `-no_save +source=... +destination=...` run.
The ordinary Rocket executable is
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/simv`;
`ordinary-command.json` records this iteration's fresh process, exact
`+pattern`/`+baseline` paths and required environment sourcing. Its
`ordinary-rocket-probe/run.log` reports seven clocks and zero edges. These
native checks retain distinct simulator/semantic scopes.

Both complete exact-recipe default/buffered four-hart controls pass at
C=3,329,794: `rocket-controls/invocation-ed0qjmsv/summary.json`. Every full hart
trace and workload/store print-cycle label matches the uninterrupted reference.
Workload ELF SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Both runs use the complete 16 GiB backing-memory configuration.
`rocket-host-audit-accepted.json` independently validates all 64 component
images across eight active samples at master credits 520,064, 700,032, 900,096
and 3,250,048. Startup rejects at zero. Clock tokens retain their one-token lead;
these samples do not certify the required semantic CPU or outstanding-memory cuts.
`native-device-build-audit.json` checks that both actual constructor/driver
translation units, `firesim_tsi.cc` and `tsibridge.cc`, were recompiled with
the current header. The native identity binds all 60 units and their dependencies.

Full initialization passes 1,471 native commands, including 768 actual and 320
mixed-policy fresh restores. Serial passes 905 commands, including 768 actual
fresh restores. Retained host tests include BCD's 68 fresh component restores
and four first semantic divergences, polling's 72 fresh continuations and
38,744 atomic invalid checks, and the independent transport oracle's 1,012
requests/four bridge runs. These are component checks; whole-CPU image rejection
and first-divergence cases remain pending.

`init-resume/invocation-7mx9t0i9/summary.json` passes all 240 fresh dispatcher
continuations, 7,012 complete peer readbacks, 5,112 atomic invalid images and
four first divergences. Both independently rerun preservation audits retain all
137,659 sealed iteration-113 artifacts; the original 1,018 native input bindings
also remain valid. Plans, environment/Conda inputs and both indices match their
guards. No staging or local commits were performed.

Recovery under this diagnostic root: `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json`, `pilots.json`,
`native-device-build-audit.json` and `artifact-manifest.json`. They preserve
exact native VCS commands/results, source bindings, host readbacks, full workload
traces and separately retained failed pilots. Complete CPU Level-1 and Level-2
acceptance remains pending.

Required early/warm/outstanding-memory/late CPU checkpoints, first CPU semantic
divergence cases, complete fresh Level-1 continuation and independently captured
Level-2 zero-edge readback/finite replay remain pending. The resource checks do
not certify these cuts. BOOM/Saturn remain pending. No FPGA or ASIC validation
is claimed.

## Iteration 113: FESVR context lifetime

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration113/`.
Both CPU levels remain **in_progress**. This increment manages process-local
FESVR stack resources; complete semantic context reconstruction remains pending.
See [tsi-context-lifetime.md](tsi-context-lifetime.md) for exact ownership and
unsupported lifetimes. The installed context header/class ABI is unchanged.
The build-local archive replaces only `context.o` and `elfloader.o`, with the
other 12 members checked byte-for-byte. Both replacement objects are explicit
native VCS linker inputs, independently recompiled and compared across Rocket
and all four final host suites. `verified/context-linkage-final/summary.json` binds
the actual executable caller and shared HTIF loader resolution. The shared
library has no FESVR context exports.

`verified/context/invocation-x679fyt3/summary.json` passes native sanitizer and VCS
DPI checks. Each backend accounts for 278 allocated/released stacks and zero
live stacks: 128 suspended and 128 returned principal lifetimes, 1,018 principal
switches, siblings, nested creators, allocation-failure recovery, worker-root
cleanup and a retained metasim-style worker object. The original-library control
retains both stacks. Six fresh death checks explicitly reject active/creator
destruction and active-child process exit before freeing an executing stack.
Raw native stack bytes are never checkpoint payloads.

`verified/transport/invocation-pri708pp/summary.json` passes the previously failing
native transport sanitizer check and native VCS checks: 1,012 requests, 566,096
compared direct records, four actual bridge runs, 32 invalid requests, four
callback-unwind checks and 24 bridge-control readbacks. The independent oracle
covers every bus beat/lane and actual ELF merge/reset trace. No sanitizer
suppression is used. Original failed iteration-112 transport evidence remains
unchanged.

The initial context pilot rejected metasim's intentionally retained registry at
driver-thread exit. A real short Rocket timeout reproduced it; the final
`verified/retained-context-exit/summary.json` passes normal deliberate-timeout termination
at 1,025 target cycles without a context abort. Earlier source-drift, strict-exit
and shared-provider-assumption pilots remain separately retained. They do not
certify final sources.

`verified/context-instrumented/summary.json` additionally passes normal and
three lifetime-rejection checks with both the fixture and actual context source
compiled under ASan/UBSan. `verified/startup-metadata/` passes 704 resource cases,
192 XLEN rejection/recovery checks, 12 fresh readbacks, 84 complete peer images,
13,924 malformed images and 18 incompatible cases. The production shared-HTIF
route independently passes the same checks with 13,916 malformed images.
All eight final native suites pass, including 267 Python tests and FCFS. Three
complete-CPU requests, 16 invalid audit options and five malformed/in-place
archive requests reject before execution or publication.

Both complete final default/buffered four-hart controls pass at C=3,329,794:
`verified/accepted/rocket-controls/invocation-0fmb4l0r/summary.json`. Every full
hart trace and workload/store print-cycle label matches the uninterrupted
reference. Workload ELF SHA-256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The independent host audit validates all 64 component images across eight active
samples at master credits 520,064, 700,032, 900,096 and 3,250,048. Startup rejects
at zero. Clock tokens retain their one-token lead; required semantic target-edge
and outstanding-memory checkpoint cuts remain uncertified. Build identity binds
all 60 driver translation units, both separate resource objects and dependencies.

All 11 retained host suites, serial and transport fault suites pass. Serial
records 905 commands. Full initialization records 1,471 commands, including 768
actual and 320 mixed-policy fresh restores; dispatch passes all 240 restores,
7,012 complete peer readbacks, 5,112 atomic invalid images and four first
divergences. BCD retains 68 fresh restores and four first semantic divergences.
These are host component checks, not complete CPU image restores.

The fresh ordinary RTL pattern probe passes all 318,637 semantic words and seven
clocks before any edge. It is not captured CPU state/replay. All 66,509 sealed
iteration-112 artifacts and 1,080 original native input bindings pass preservation
checks. Plans, environment, installed/protected Conda inputs and both indices
match their guards. Existing controller-created iteration-112 commits were
published FireSim first, then Chipyard; queried remote tips match. Tracking-ref
refreshes emitted read-only `.git` warnings after successful remote updates.
No staging or local commits were performed.

Recovery under the diagnostic root: `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json`, `pilots.json`,
and the complete `artifact-manifest.json`. These preserve current sources,
actual native commands/results, readbacks, workload traces and failed pilots.

Fresh native resource checks (each uses a new invocation directory):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_fesvr_context_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/context
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/transport
python -m tools.checkpoint_formats.tests.verify_tsi_startup_metadata_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/startup-metadata
```

Fresh exact-recipe four-hart controls (full trace comparisons; no bitstream):

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration113-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration113/verified/accepted/rocket-controls/invocation-0fmb4l0r/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

These controls do not certify checkpoint cuts. Full HTIF configuration/build/
XLEN, terminal/syscall, stop/signature/exit/signal and semantic caller ownership,
atomic host assembly, complete simulator/FAME/channel/memory/bridge ownership,
coherent required CPU cuts, fresh Level-1 CPU continuation and independent
Level-2 captured readback/replay remain pending. BOOM and Saturn remain pending.
No external dependency is missing. Physical FPGA validation and ASIC power stay
deferred; plans remain read-only and the controller owns local commits.

## Iteration 112: ELF-loader resource cleanup

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration112/`.
Both CPU levels remain **in_progress**. This increment closes a host startup
resource leak; it does not establish complete CPU continuation or semantic replay.

`final/startup-metadata/invocation-na1k5u8y/summary.json` passes native sanitizer
host checks and VCS DPI checks with the actual installed HTIF and a repository-owned
ELF-loader overlay. Only `elfloader.o` changes in a build-local FESVR archive;
the other 13 members and the installed Conda archive remain byte-identical.
The original ELF decoding/target-write source is retained exactly. See
[tsi-metadata-compatibility.md](tsi-metadata-compatibility.md) for scope and limits.

The suite passes 704 resource cases across 11 modes: XLEN 32/128 mismatch,
wrong endianness, first/second memory-write exceptions, empty/missing/directory
inputs, and successful XLEN 0/64 and BSS loading. Successful metadata and all
target writes match independent expectations. Kernel descriptor and mapping
counts return to baseline after every case. Original installed-loader native
and VCS negative controls each fail on the first leaked mapping as expected.
The metadata paths pass another 192 repeated installed-XLEN rejection/retry
checks, 12 fresh complete metadata readbacks, 84 unchanged peer images,
13,900 malformed images and 18 incompatible/legacy cases. All happen before
any target service, context entry or target edge in the destination.

`transport-context-diagnostic/summary.json` confirms a separate pre-existing
installed context-stack leak. Native sanitizer transport runs against both the
original archive and overlay exit 1 with two leaked 1 MiB stacks. Both native
runs and both VCS runs retain identical complete functional outputs; all compare
with the independent transport/bridge oracle. The native transport sanitizer
check remains **failed**, without suppression. Its source fixture and failed
module invocation remain under `transport/`; this diagnostic does not grant CPU
support. Context destruction and suspended-stack resource ownership remain pending.

The first final audit found a production linkage gap: the launcher resolved
`load_elf` from `libriscv.so`, so naming a patched archive did not force its member
to load. The Makefrag now extracts and passes the audited member as a driver
object, avoiding VCS's repeated inherited/explicit linker flags.
`rocket-loader-binding/summary.json` verifies its strong dynamic definition and
actual shared-HTIF resolution before any target edge. `rocket-loader-linkage-final/`
independently rebuilds that object with dependency output and audits actual
providers: shared HTIF/memif/syscall functions, static FESVR contexts and the
explicit loader. Both complete corrected controls pass under
`accepted/rocket-controls/invocation-f_4w073_/`. Earlier controls remain
uninterrupted workload reference evidence and cannot certify production loader binding.

`shared-metadata/invocation-4k5iq0tw/summary.json` additionally validates the
actual shared-HTIF route with the Rocket loader object, in native C++ and VCS:
704 resource cases, 192 XLEN rejections, 12 complete fresh readbacks / 84 peer
images, 13,844 invalid images and 18 incompatible cases pass. Both installed
negative controls still fail as expected. No target edge, context entry or
target service occurs during destination metadata preparation.

`accepted/rocket-controls/invocation-f_4w073_/summary.json` passes both complete
exact-recipe default/buffered four-hart controls at C=3,329,794. Every full trace
and workload/store cycle label matches the uninterrupted reference. The workload
ELF SHA-256 is
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The eight active host samples independently pass all 64 component images; master
credits and clock tokens remain distinct from uncertified semantic target edges.
`rocket-loader-linkage-final/summary.json` recompiles the loader with native dependency
output, binds its installed configuration/header inputs, and compares its object
byte-for-byte with the Rocket and metadata-test archive members. The 13 other
installed members are unchanged. The build retains 60 VCS driver translation
units plus the separately compiled loader replacement.

`final/native-regressions/invocation-5c4ntkpm/summary.json` passes all eight
preserved native suites, including 267 Python tests and FCFS. All 11 retained
host suites pass individually (`host-regression-results-final.json`); the serial
suite and production transport fault-injection suite also pass. Full initialization
passes 1,471 commands, including 768 actual and 320 mixed-policy fresh readbacks.
Initialization dispatch retains 240 fresh restores, 7,012 peer readbacks,
5,112 atomic invalid-image checks and four first divergences. BCD retains 68
fresh restores and four first divergences. These are host component checks.

The fresh ordinary RTL diagnostic passes 318,637 pattern-word readbacks across
seven clocks before any edge. It is not a captured CPU checkpoint or replay.
Three complete-CPU admission requests and all 16 invalid audit options reject
before execution. All 45,803 sealed iteration-111 artifacts and 1,050 retained
native input bindings pass preservation checks. Failed source-binding/runner
pilots and the unsuppressed transport sanitizer failure remain under the run
root and are indexed by `pilots.json`.

Recovery artifacts are `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json`, and the complete
`artifact-manifest.json`. Native commands include actual builds, simulator
invocations, source-bound audits and both original-library negative controls.

Executable fresh metadata recheck (allocates new artifacts):

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/metadata-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_startup_metadata_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/startup-metadata
```

Executable fresh exact-recipe controls (copies the tested build, regenerates
the overlay and invokes pinned native VCS; no bitstream build):

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/rocket-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration112/accepted/rocket-controls/invocation-f_4w073_/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

Executable production shared-HTIF metadata recheck:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/shared-metadata-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python automations/checkpoint_loop/runs/m11-iteration112/verify_shared_metadata.py \
  --out automations/checkpoint_loop/runs/m11-iteration112-controller-rechecks/shared-metadata
```

Retained full native regression audit:

```sh
python -m tools.checkpoint_formats.native_regressions --audit \
  automations/checkpoint_loop/runs/m11-iteration112/final/native-regressions/invocation-5c4ntkpm/summary.json
```

`overlay-rejections/summary.json` passes three atomic archive rejections:
unsupported missing/duplicate loader members and an attempt to overwrite the
input archive. No output archive/report is published; input bytes remain
unchanged. The source audit independently verifies identical decoding and
target-write code after the resource setup. Existing controller commits are
published FireSim first, then Chipyard; queried remote tips match.

Remaining: installed context-stack cleanup/lifetime, exact HTIF configuration/build/XLEN policy, terminal/syscall and
stop/signature/exit/signal/context state, atomic aggregate host reconstruction,
complete simulator/FAME/channel/memory/bridge ownership, coherent required CPU
cuts, fresh Level-1 CPU continuation, independent Level-2 captured state/readback
and finite replay, and whole-CPU negative/corruption cases. BOOM and Saturn
remain pending. No external dependency is missing.

## Iteration 111: metadata transport contract and atomic XLEN preflight

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration111/`.
See [tsi-metadata-compatibility.md](tsi-metadata-compatibility.md) for exact
ownership and limits. Both CPU levels remain **in_progress**.

`startup-metadata/invocation-i3dksq0b/summary.json` passes installed-FESVR native
sanitizer and Y-2026.03-SP1 `-full64` VCS checks. All 12 fresh preparations read
back every metadata byte and 84 unchanged peer-component images before target
services, context entry or edges. All 13,852 byte-flip/truncation/extension cases
reject atomically, then accept a valid image. Eighteen incompatible argument,
ELF, option, constructor-only load-memory and legacy-image cases reject before
publication. Both actual source loaders complete their partial-write read/merge
and finish through HTIF PASS.

Revision 2 includes endianness, chunk sizes, load-memory capability and all seven
named pristine component images as configuration contracts. These are not the
live CPU-cut component states. Capture/preparation preflight the sealed local
ELF through the installed HTIF loader with target writes suppressed. This
closes a path where incompatible expected XLEN could fail after metadata
publication and poison the caller. Six tests change the real nonvirtual setter
through an `htif_t` reference, observe expected=32/actual=64, then recover with
64 and complete readback. This checks ELF compatibility; it does not serialize
the exact zero/64 XLEN policy or certify complete build identity. Installed
ELF-loader XLEN errors bypass `munmap`; complete resource cleanup remains
pending, separately from the passing metadata/peer rejection checks.

Recheck the new component from the Chipyard root with fresh paths:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration111-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration111-controller-rechecks/metadata-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_startup_metadata_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration111-controller-rechecks/startup-metadata
```

`ordinary-rocket-probe/summary.json` passes fresh ordinary RTL VCS readback of
318,637 pattern words / seven clocks before any edge; it remains a diagnostic,
not a captured CPU image or replay. Three complete CPU admission requests and
all 16 invalid host-audit options reject before CPU execution/publication.
`retained-iteration110-audit.json` verifies all 51,399 sealed prior artifacts.
Both iteration-110 controller commits are published, FireSim first then
Chipyard; queried remote tips match. Local tracking-ref refreshes failed on
read-only `.git`; no local staging or commits were performed.

Both exact-recipe default/buffered four-hart controls pass at **C=3,329,794** in
`rocket-controls/invocation-djtgi36h/summary.json`. Every complete hart trace
and every workload/store CPU print-cycle label matches the uninterrupted
reference. `rocket-build-identity.json` binds all 60 current native translation
units/dependencies and the exact six recipe settings above. The unchanged
workload is `runs/m11-iteration82/workload/rocket-quad.riscv`, 6,712 bytes,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
No FPGA bitstream was built.

`rocket-host-audit.json` passes all 64 component images at eight active host
samples, preserving separate master-credit and clock-token labels. These
samples do not certify semantic DUT edges or the required outstanding-memory
checkpoint cut. All eight full native suites pass in
`native-regressions/invocation-ryjuskkw/summary.json`, including 267 Python tests
and FCFS. The complete initialization suite passes 1,470 native commands.
All 11 retained host suites pass in `host-regression-results.json`. Fresh
initialization dispatch in `init-resume/invocation-liex5fv3/summary.json` passes
240 fresh restores and four first-divergence cases. The BCD suite retains 68
fresh restores / four first divergences; polling retains 72 fresh continuations /
four first divergences. These labels are host-service boundaries, not certified
CPU target cycles.

Exact native commands are retained in each invocation's `commands.json` and in
`raw-native-commands.json`; fresh executable rechecks are in
`verification-commands-native.json`. Final recovery records are `summary.json`,
`selected-results.json`, `native-input-archives.json`,
`independent-audit-results.json` and `artifact-manifest.json` under the run root.
`elf-loader-resource-diagnostic/summary.json` records the confirmed cleanup gap,
with its exact sanitizer build/run commands and the rejected relative-argument
pilot retained separately.

Remaining work includes exact full HTIF configuration/build/XLEN policy,
terminal/syscall/stop/signature/signal/context resources and atomic host
assembly; complete simulator/FAME/channel/memory/bridge ownership; coherent
required CPU cuts, fresh Level-1 continuation and independent captured Level-2
zero-edge readback/finite replay. Whole-CPU rejection and first-divergence
corruption tests remain pending. `remaining-host-owner-audit.json` records
source-bound pending host fields. BOOM/Saturn remain pending. No external tool,
license, netlist or library dependency is missing for this increment.

## Iteration 110: default BCD pending-command ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration110/`.
See [tsi-bcd.md](tsi-bcd.md) for the exact component boundary. Both CPU levels
remain **in_progress**; this adds a host device queue owner.

`bcd-current/invocation-yjvfpah0/summary.json` passes native sanitizer and
Y-2026.03-SP1 `-full64` VCS checks against the installed BCD implementation.
All 68 fresh restores read back every pending command before services or
contexts. All 64 continuation suffixes match the installed reference, including
12 continuations from actual TSI captures; identity memory writes and terminal
output bytes match. All 528 malformed images and four incompatible queue
configurations reject atomically, followed by valid readback. Twenty-two active
and interrupted-service guards pass. Four valid queue corruptions first diverge
at missing response `0x01000000000001ff`, host event **11**. These host-event
labels do not establish a CPU target-cycle boundary.

Both actual installed-FESVR source loaders complete their partial-write
read/merge, capture zero/one/two pending BCD commands at suspended polling cuts,
check both delayed-input serial fromhost writes and finish through HTIF PASS.
The new production queue owns ordered raw commands and reconstructs its response
sink from the destination polling owner. It serializes no source callbacks or
coroutine pointers. Terminal state remains external; the eight-component polling
inspection retains its original boundary. Complete CPU admission is disabled.

Commands are recorded in the selected BCD invocation's `commands.json`. Recheck
from the Chipyard root with fresh paths:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration110-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration110-controller-rechecks/bcd-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_bcd_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration110-controller-rechecks/bcd
```

The first BCD invocation finished native execution but failed audit because its
checker had an incorrect decimal constant for the 0xff response. The corrected
checker computes that value; the selected invocation reruns every native case
and additionally continues all actual production captures. The first full
regression invocation retains the checker-source change and is excluded from
current-source evidence. The fresh complete suite in
`native-regressions-current/invocation-rizi51yo/summary.json` passes all eight
checks, including 267 Python tests and FCFS. The complete initialization suite
passes all 1,470 commands. All 11 source-bound retained host suites pass;
results are in `host-regression-results.json`. Fresh dispatcher resumes pass all
240 restores, 7,012 complete readbacks, 5,112 atomic invalid images and four
first divergences in `init-resume/invocation-x2vflc9u/summary.json`. Initialization
retains 294 fixture continuations, 768 actual caller and 320 mixed-policy fresh
readbacks. Polling retains all 72 fresh continuations, 1,332 full readbacks,
38,744 atomic invalid checks and four first divergences. Actual polling retains
all 324 fresh component restores and 252 caller readbacks. Exact-ELF metadata
retains eight fresh readbacks, 56 unchanged peer images, 7,364 atomic invalid
cases and 14 incompatible/unsupported cases. These remain host-component tests.

Both exact-recipe default/buffered four-hart controls pass at **C=3,329,794** in
`rocket-controls/invocation-wwl99dud/summary.json`. Every complete hart instruction
trace and every workload/store CPU print-cycle label matches the uninterrupted
reference. `rocket-build-identity.json` binds the exact six recipe settings above,
all 60 native translation units and their actual dependencies, including the new
BCD header in both TSI and serial-bridge consumers. The unchanged workload is
`runs/m11-iteration82/workload/rocket-quad.riscv`, 6,712 bytes, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Its independently resolved mailboxes are `tohost=0x800003c0`,
`fromhost=0x80000400`. No FPGA bitstream was built.

`rocket-host-audit.json` verifies all 64 component images at eight active host
samples: master credits 520,064, 700,032, 900,096 and 3,250,048 in each mode.
Clock-token counts retain their separate one-token lead. These host credits do
not certify coherent semantic DUT edges or an outstanding-memory CPU cut.
The full ordinary RTL diagnostic in `ordinary-rocket-probe/` reads back all
318,637 words / seven clocks before edges; it remains a pattern diagnostic,
not a captured CPU image or replay. Three complete CPU admission requests and
all 16 malformed host-audit options still reject before CPU execution or
checkpoint publication. `retained-iteration109-audit.json` preserves all 45,237
previously sealed artifacts.

Exact native commands are retained in each invocation's `commands.json`, the
CPU control's build/runtime records and `raw-native-commands.json`; rechecks
with environment sourcing and fresh output paths are recorded in
`verification-commands-native.json`. Final recovery records are `summary.json`,
`selected-results.json`, `native-input-archives.json`,
`independent-audit-results.json` and `artifact-manifest.json` under the run root.
Both existing iteration-109 controller commits are published, FireSim first
then Chipyard, with queried remote tips matching. Local tracking-ref refreshes
failed on read-only `.git`. Both plans and protected inputs retain their bytes;
there is no staging or local commit.

Configuration/build/expected-XLEN binding, terminal and syscall resources,
HTIF stop/exit/signature/signal state, context replacement and atomic host
reconstruction remain pending. Complete simulator/FAME/channel/memory/bridge
ownership, coherent early/warm/outstanding-memory/late CPU cuts, fresh Level-1
continuation, independently captured Level-2 readback/replay and whole-CPU
rejection/first-divergence cases remain pending. BOOM/Saturn remain pending.

## Iteration 109: exact-ELF HTIF metadata preparation

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration109/`.
See [tsi-startup-metadata.md](tsi-startup-metadata.md) for the precise boundary.
Metadata preparation is a component operation; both complete CPU levels remain
**in_progress**.

`startup-metadata/invocation-0dk0d6t2/summary.json` passes native C++ and
Y-2026.03-SP1 `-full64` VCS checks linked to installed FESVR. Both actual source
loaders complete their partial-write read/merge, capture at a guarded polling cut
and finish through HTIF PASS/stop. All eight fresh sanitizer/VCS preparations
read back the entire metadata and 56 unchanged peer-component images before
services, contexts or edges. All 7,364 malformed byte-flip/truncation/extension
cases reject atomically, followed by valid preparation in the same fresh caller.
Fourteen changed-ELF/argument and unsupported-option cases reject without partial
publication. The image binds exact ELF bytes/arguments, entry and all symbols;
it reconstructs the installed private entry/mailboxes/symbol table without
startup target writes or reset. Library/build compatibility and aggregate host
ownership remain pending.

Native commands are recorded with environment sourcing and executable argv in
`startup-metadata/invocation-0dk0d6t2/commands.json`. Rechecks allocate fresh
invocations; the controller can run from the Chipyard root:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration109-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration109-controller-rechecks/metadata-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_startup_metadata_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration109-controller-rechecks/startup-metadata
```

The retained full native suite in
`native-regressions/invocation-86exlt3w/summary.json` passes all eight suites,
including 267 Python tests and FCFS. `retained-iteration108-audit.json` verifies
all 60,240 previously sealed artifacts with their original bytes preserved.
The fresh ordinary RTL pattern diagnostic in `ordinary-rocket-probe/` passes
all 318,637 semantic words / seven clocks before any edge; it remains a pattern
diagnostic rather than a captured CPU checkpoint/replay. All three complete CPU
admission requests and all 16 invalid host-audit options still reject before
CPU execution/publication.

Both complete exact-recipe default/buffered four-hart controls pass at
**C=3,329,794** in `rocket-controls/invocation-vhwno81s/summary.json`. Every
complete instruction trace and workload/store CPU print-cycle label matches the
uninterrupted reference. The native build identity binds all six recipe settings
listed above, all 60 translation units and their actual header dependencies.
The unchanged self-checking workload is
`runs/m11-iteration82/workload/rocket-quad.riscv`, 6,712 bytes, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
No bitstream was built. `rocket-host-audit.json` independently validates both
startup rejections and all 64 component images at the same eight active samples
(master credits 520,064, 700,032, 900,096 and 3,250,048 in each mode). Each has
79 serialized words, with the clock-token count recorded separately one ahead.
These credits still do not certify completed semantic target edges or an
outstanding-memory checkpoint cut.

All ten additional source-bound native/VCS host suites pass; their exact
commands/results are in `host-regression-results.json`. Retained polling passes
72 fresh continuations, 1,332 complete readbacks, 38,744 atomic invalid images,
eight fresh invalid images and four first divergences. Actual installed polling
passes all 324 fresh component restores / 252 polling readbacks, 1,008
independently expected component images and 54 cross-owner rejections. Actual
BCD/fromhost checks retain all 20 fresh caller readbacks; installed option
routing passes all 18 cases. Actual installed active syscall/memif checks still
reject pending and partial 64-byte reads and inspect all eight owners after the
service returns. Full initialization retention passes 294 fixture continuations,
768 actual caller and 320 mixed-policy readbacks. Fresh initialization dispatch
passes 240 restores, 7,012 complete readbacks, 5,112 atomic invalid images and
four first divergences. These are host-component checks, not CPU continuation.

Existing iteration-108 controller commits are published FireSim first, then
Chipyard; independent remote tips match. Read-only `.git` prevented local
tracking-ref refreshes after the successful remote updates. Protected plan,
environment, PDF and Conda inputs retain their original bytes. No staging,
local commits or history cleanup occurred.

Recovery records are `summary.json`, `selected-results.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json` and
`artifact-manifest.json`. Final audits bind complete readbacks, current native
sources/dependencies, all preserved artifacts and the unsupported CPU admission
guards. Both complete CPU levels remain in progress. Next: configuration/build
and expected-XLEN ownership, default devices/stop/signature/signal/context and
atomic cross-owner reconstruction, then coherent required CPU cuts and fresh
Level-1 continuation plus independently captured Level-2 zero-edge readback/
finite replay. Whole-CPU image rejection and first-divergence cases remain
pending; no external dependency is missing.

## Iteration 108: suspended polling cut audit

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration108/`.
See [tsi-polling-cut-audit.md](tsi-polling-cut-audit.md) for the exact eight-owner
boundary and production guards. All final selected native checks pass. This
increment inspects production state; complete HTIF/TSI restore and both CPU
checkpoint levels remain **in_progress**.

`inspect_polling_cut()` requires returned startup, complete loading and
initialization, empty load-memory state and an externally suspended host. It
cross-checks the polling caller against its partial serial-read or idle child,
validates all eight images and checks repeat-read stability. The bridge exposes
this optional diagnostic without changing aggregate checkpoint admission.

Both complete exact-recipe default/buffered four-hart controls pass at target
count **3,329,794** in `rocket-controls/invocation-ieqwwfrh/summary.json`.
Every complete instruction trace and workload/store CPU print-cycle label
matches the independent uninterrupted reference. The exact six recipe settings
above, all 60 native translation units and actual compiler header dependencies
are bound by `rocket-build-identity.json`. No bitstream was built. The unchanged
6,712-byte workload ELF is `runs/m11-iteration82/workload/rocket-quad.riscv`,
SHA-256 `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Its independently resolved mailboxes are `tohost=0x800003c0` and
`fromhost=0x80000400`.

Both actual CPU runs record these host inspections in
`rocket-runtime/tsi-host-audit/` and `rocket-buffered-runtime/tsi-host-audit/`:

| Requested master credit | Clock tokens enqueued | Host inspection in both modes |
| --- | --- | --- |
| 0 | 0 | startup not returned; explicit rejection, no component images |
| 520,064 | 520,065 | idle; eight complete component images |
| 700,032 | 700,033 | blocked tohost read; eight complete component images |
| 900,096 | 900,097 | blocked tohost read; eight complete component images |
| 3,250,048 | 3,250,049 | idle; eight complete component images |

`rocket-host-audit.json` independently checks all ten records and all 64 active
component images against the workload symbols and exact configurations. Each
active record has 79 serialized 64-bit words including configuration/header
words. This proves startup frames have returned at those samples. These labels
are distinct from completed semantic target edges and CPU print-cycle labels.
The memory-loop sample does not independently prove outstanding target memory;
coherent CPU checkpoint cuts and continuation/replay remain pending.

`current/active-service/invocation-1dlpa321/summary.json` passes actual installed
syscall/memif integration in native C++ and VCS. A real 64-byte syscall read
blocks before data and after one word; both cuts reject. After installed
`sys_exit` returns, all eight components become inspectable; response queuing,
fromhost publication and termination complete. Across both backends this gives
four active-service rejections, ten startup/termination rejections and 32
complete returned component images. Private device/context state is not restored.

`current/actual-poll/invocation-09a8u8xu/summary.json` passes all 324 fresh
component restores, including 252 polling-caller readbacks. Inspection at 126
actual suspended polling/partial-read/idle cuts yields 1,008 complete component
images with independently expected bytes. All 54 component-valid cross-owner
corruptions reject without changing peers. BCD/fromhost integration in
`actual-response/invocation-grnb1fz_/summary.json` retains all 20 fresh caller
readbacks and independently checks all 64 inspected peer images. None of these
host component tests establishes a CPU checkpoint.

`htif-poll/` retains all 72 fresh sanitizer/VCS caller continuations, 1,332 complete
readbacks, 38,744 atomic invalid-image checks, eight fresh invalid images and four
first divergences. The full initialization retention suite passes 294 fixture
continuations, all 768 actual caller and 320 mixed-policy readbacks. The fresh
initialization dispatcher passes all 240 restores, 7,012 complete peer readbacks,
5,112 atomic invalid images and four first divergences. The final source-bound
`current/native-regressions/invocation-089ltlrq/summary.json` passes all eight
suites, including 267 Python tests and FCFS. All 18 installed option-routing
cases pass in `current/htif-options/`.

Three complete CPU preflight/capture/restore requests still reject before CPU
execution/publication. All 16 malformed/duplicate/missing audit-option and
existing-directory cases reject without publication. The fresh ordinary RTL
pattern probe reads back all 318,637 words / seven clocks before any edge. It
remains a diagnostic, not a captured CPU image or captured trace replay.

One concurrent VCS build collided with another build's timestamp/PID temporary
directory. The failed log remains under `real-loader/`; the successful rerun is
`current/real-loader/invocation-fn0qobkp/summary.json`. Follow-up builds inherit
separate TMPDIR directories under this run. A wrong-directory ordinary-probe
launcher, a wrong-parent-summary polling launcher and an initial linkage audit
that omitted C++ ABI symbol tags are retained separately from their corrected
successful runs. No check was removed. Earlier source-bound
runs remain diagnostics; `selected-results.json` identifies the final evidence.

Existing iteration-107 controller commits are published FireSim first, then
Chipyard; independently queried remote tips match. Local tracking-ref refreshes
failed on read-only `.git` after successful remote pushes. Neither plan,
environment setup, PDF nor dirty Conda input was edited; no staging or local
commits occurred.

Recovery: `summary.json`, `selected-results.json`, `rocket-host-audit.json`,
`raw-native-commands.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json` and complete
`artifact-manifest.json`. Commands run from the Chipyard root. Fresh rechecks
allocate new destinations outside the sealed iteration; use separate TMPDIRs
when launching VCS builds from separate sandbox shells:

```sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration108-controller-rechecks
export TMPDIR="$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration108-controller-rechecks/active-tmp.XXXXXX")"
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_polling_cut_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration108-controller-rechecks/active-service
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration108-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration108/rocket-controls/invocation-ieqwwfrh/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json \
  --host-audit-cycles 0,520064,700032,900096,3250048
```

Complete configuration-specific simulator/FAME/channel/memory/bridge ownership,
HTIF metadata/device/stop/signature/context reconstruction and atomic CPU images,
coherent required active cuts, fresh Level-1 continuation, independently captured
Level-2 readback/replay and whole-CPU invalid-image/first-divergence cases remain
pending. BOOM/Saturn remain pending; no external dependency is missing.

## Iteration 107: production HTIF polling caller

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration107/`.
See [tsi-htif-poll.md](tsi-htif-poll.md) for the exact state boundary, production
dispatch and unsupported owners. The default-device production caller now owns
all nine polling phases, the pending command and ordered fromhost responses.
Review reproduced FESVR's abbreviated long-option routing in `options-pilot/`.
All long options now retain the installed HTIF loop, including abbreviations;
the new native/VCS option suite passes all 18 real installed-FESVR cases. Final source-bound checks are under `current/`; all corrected native checks and
both complete four-hart controls pass. Earlier source-bound runs remain separate
retained diagnostics.
Serial reads and idle yields return through their existing owners. Installed
startup/ELF/memif, private HTIF metadata, device internals, stop/signature and
context reconstruction remain pending. Complete CPU checkpoint requests remain
unsupported; these component checks cannot establish either CPU level.
Whole-CPU image admission and first-divergence cases at the required active cuts
remain pending alongside continuation and independent captured RTL replay.

`htif-poll/invocation-qkszzkjk/summary.json` passes 72 fresh native ASan/UBSan and
VCS caller continuations: 1,332 complete state readbacks, 38,744 atomic invalid-
image checks, eight fresh malformed/incompatible/incomplete image rejections and
four first divergences. The two valid-image command/response corruptions first differ
at component operation 0 (`tohost_command` and `write_data`) without acknowledging
that operation. These fixture labels are not Rocket target-cycle labels.
`current/real-loader/invocation-8f3k4bk4/summary.json` retains actual installed-FESVR ELF
read/merge/reset/idle checks. Fresh program-loader readbacks pass all 28 cases and
7,072 atomic invalid images per process.

`current/actual-response/invocation-ylajuuoz/summary.json` passes the installed-FESVR BCD
callback/fromhost route in native C++ and VCS. Each source consumes exactly one
deterministic input byte, retains `0x0100000000000141` across pending/partial
fromhost reads, writes it once and then handles the installed pass command.
All 40 complete caller/serial-read/FIFO/host-control peer images match independent
bytes. All 20 fresh native ASan/UBSan/VCS caller readbacks pass before services,
context entry or target edges. This does not restore the device or terminal.

`current/host-control/invocation-1bylj7_y/summary.json` passes all 362 fixture continuations,
7,866 complete readbacks and 136 real FESVR component readbacks. The unchanged
initialization dispatcher passes 240 fresh restores, 7,012 complete peer readbacks,
5,112 atomic invalid images and four first divergences in
`current/init-resume/invocation-yj592grc/summary.json`. All eight preserved native suites,
including 267 Python tests and FCFS, pass in
`current/native-regressions/invocation-h2edvc3m/summary.json`.
`current/actual-poll/invocation-sbahu7eu/summary.json` passes all 324 fresh component
restores, including 252 complete polling-caller readbacks of first-poll,
partial-read and idle states at all three idle-count policies. These valid peer
readbacks do not implement a complete atomic TSI restore bundle. The full initialization
retention suite also passes in `current/init-regression/invocation-m9aandn0/summary.json`: all 294 fixture continuations,
7,264 complete readbacks, 60 fresh invalid cases and four first divergences,
plus all 768 actual caller and 320 mixed cache-flush/MSIP fresh readbacks.

`current/rocket-controls/invocation-uknm8doa/summary.json` passes both complete
default and buffered four-hart controls at C=3,329,794. Every complete trace and
workload/store cycle label matches the independent uninterrupted reference.
The exact six recipe settings above and the unchanged 6,712-byte workload are
bound by `rocket-build-identity.json`: ELF
`runs/m11-iteration82/workload/rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These are uninterrupted CPU controls, not checkpoint continuations.

`current/htif-options/invocation-w9al62gy/summary.json` passes all 18 native/VCS
option cases, including all long chroot prefixes, the plusarg form and a long
metadata option. `options-pilot/` preserves the pre-correction failure. All
corrected native command logs, original input snapshots and independently audited
results remain source-bound. Independent restore batches run four workers, with
locked command records and complete sibling failure retention; all four runner
tests pass. No state image, process, negative case or comparison was removed.

The fresh ordinary Rocket diagnostic reads back all 318,637 words / seven clocks
before any edge. It deposits diagnostic patterns, not independently captured CPU
state. `current/rocket-poll-linkage.json` binds all 60 native translation units, the
production host dispatcher, the poll owner vtable/virtual checkpoint methods and
both TSI/bridge header consumers. Generated RTL, inventory, reference and constants
match iteration 106. The linkage pilot's out-of-line `advance()` symbol check
failed because the optimizer inlined it; its separate diagnostic is retained.
The generated inventory remains 2,292 instances, 11,464 state entries and 445,838
words. This is a storage inventory, not proof of complete runtime ownership.

Existing iteration-106 controller commits are published FireSim first, then
Chipyard. Both remote tips match. The local tracking-ref refreshes failed on
read-only `.git` after the successful remote pushes. No staging, local commits,
protected plan/environment/Conda edits or history cleanup occurred.

Native commands run from the Chipyard root. Fresh rechecks allocate new
invocations outside the sealed iteration; the exact raw VCS compiler/runtime
argv, source hashes, images, readbacks and results remain in each summary and
the run's `raw-native-commands.json`.

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_htif_poll_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks/htif-poll
python -m tools.checkpoint_formats.tests.verify_tsi_htif_response_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks/actual-response
python -m tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks/actual-poll \
  --component-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration107/current/host-control/invocation-1bylj7_y/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration107/current/rocket-controls/invocation-uknm8doa/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

The ordinary RTL storage diagnostic can be repeated with a fresh working
directory, preserving its independent pre-FAME boundary and all prior logs:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
mkdir -p automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks
checkpoint_probe_dir=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration107-controller-rechecks/ordinary-rocket-probe.XXXXXX")
(cd "$checkpoint_probe_dir" && \
 /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/simv \
 -no_save +vcs+initreg+0 +vcs+initmem+0 \
 +pattern=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/complete-pattern.txt \
 +baseline=/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/initial-baseline.txt \
 > run.log 2>&1)
```

`summary.json`, `selected-results.json`, `verification-commands-native.json`,
`native-input-archives.json`, `independent-audit-results.json` and
`artifact-manifest.json` provide recovery and complete diagnostic membership.
`remaining-host-owners.json` and [tsi-htif-poll.md](tsi-htif-poll.md) record the
pending owner audit and proposed next boundary. BOOM/Saturn remain pending;
no external dependency is missing.

## Iteration 106: production program-load phase and routing

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration106/`.
See [tsi-program-loader.md](tsi-program-loader.md) for exact ownership, schema
and production callers. Both CPU levels remain **in_progress**. The complete
HTIF/ELF/memif/device/context owners and cross-owner cut coherence, required
active CPU cuts, fresh Level-1 continuation and independently captured Level-2
readback/replay remain pending. No complete CPU checkpoint profile is enabled.

`real-loader/invocation-bx_ympkl/summary.json` passes actual installed-FESVR ELF loading in native
C++ and VCS, retaining exact request/partial-read/merge/reset/idle checks and
capturing seven suspended loader phases per backend. Independently expected phase
words are `0,1,2,2,2,3,3`. `program-loader/invocation-ryw_falz/summary.json` passes all 28 fresh
complete component readbacks, all four capability/cache-flush policies and four
phases, 7,072 atomic invalid-image cases per process, illegal-transition/poison
guards and two first-divergence phase-corruption cases at component operation 0.
These component labels are not Rocket target cycles. The 56-byte kind-23 image
owns program-load transport selection and entry/return, not ELF/memif caller
buffers or HTIF continuation. The existing four-owner initialization bundle is
unchanged; this increment does not reconstruct its complete host context.

`init-regression/invocation-bim6nr36/summary.json` passes 294 fixture continuations, 7,264 complete
readbacks, 60 fresh invalid cases and four first divergences; all 384 actual
caller images restore in 768 fresh processes, and all 160 mixed cache-flush/MSIP
captures restore in 320 fresh processes. `init-resume/invocation-pyjvrue0/summary.json` passes
240 fresh actual dispatches, 7,012 complete four-owner readbacks, 6,772 continued
operations, 5,112 atomic invalid-image cases and four first divergences.
`native-regressions/invocation-mp9b4hk7/summary.json` passes all eight preserved suites, including
263 Python tests and the full FCFS checks. These retain their component/fixture
scope and cannot establish complete CPU checkpoint support.

`rocket-controls/invocation-zsejlhrh/summary.json` passes both full default/buffered uninterrupted
four-hart controls at target C=3,329,794. Every full instruction trace and workload/
store label matches the independent uninterrupted reference. The unchanged
6,712-byte ELF is `runs/m11-iteration82/workload/rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The exact six recipe settings above are retained. `rocket-loader-linkage.json`
binds all 60 native translation units, the new production routing/owner symbols
and the header in both TSI/bridge consumers. Generated RTL, inventory, reference
and constant-header hashes match iteration 105. Native builds/runs use VCS
Y-2026.03-SP1, `-full64`, GCC/G++ 13 and the required environment sourcing order.

Eight final and 28 retained independent audits pass. The fresh ordinary Rocket
VCS diagnostic in `ordinary-rocket-probe/summary.json` reads back all 318,637
words / seven clocks before any edge; its deposited pattern is not captured CPU
state. `cpu-request-rejections/summary.json` retains all three complete-CPU
preflight/capture/restore rejections before execution/publication. The prefix
checker pilot failed because buffered sinks publish their retained bytes at
completion; its diagnostic remains separate from the passing default-prefix
check and both full final comparisons. No check was omitted to pass verification.

`summary.json`, `selected-results.json`, `executed-native-commands.json`,
`verification-commands-native.json` and `native-input-archives.json` retain exact
native commands, selected results and original source bytes. The full
`artifact-manifest.json` enumerates every diagnostic file and dangling-link target;
`changed-source-artifacts.json` binds implementation/documentation files.
Protected plan/environment/Conda/index/HEAD checks are separate turn-local guards.
No external dependency is missing. Existing iteration-105 controller commits are
published FireSim first, then Chipyard. `github-publication.json` records matching
remote tips and local tracking-ref refresh failures on read-only `.git` after
successful remote pushes. The controller owns staging/new checkpoint commits.

Fresh native rechecks write outside the sealed iteration. Run from Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration106-controller-rechecks/real-loader
python -m tools.checkpoint_formats.tests.verify_tsi_program_loader_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration106-controller-rechecks/program-loader \
  --integration-summary /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration106/real-loader/invocation-bx_ympkl/summary.json
python -m tools.checkpoint_formats.tests.verify_tsi_init_resume_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration106-controller-rechecks/init-resume \
  --init-summary automations/checkpoint_loop/runs/m11-iteration104/init/invocation-tvmgxkbu/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration106-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration105/rocket-controls/invocation-2pjhmxlf/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

The complete initialization/native-regression and fresh ordinary RTL commands,
with cwd and argv arrays, are in `verification-commands-native.json`. The latter
runs the audited ordinary RTL `simv` with `-no_save`, `+vcs+initreg+0`,
`+vcs+initmem+0`, `+pattern=.../complete-pattern.txt` and
`+baseline=.../initial-baseline.txt` from a fresh diagnostic directory after
sourcing both environments and `vcs-env.sh` last. This is a storage diagnostic;
CPU zero-edge readback/replay still requires an actual independent capture.

## Iteration 105: fresh production initialization dispatch

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration105/`.
See [tsi-init-resume.md](tsi-init-resume.md) for exact ownership, supported
boundaries and atomic restore. Both CPU levels remain **in_progress**. Complete
HTIF/memif/device/TestChip loader/context ownership and cross-owner coherence,
all required early/warmed-cache/outstanding-memory/late CPU checkpoint cuts,
fresh Level-1 continuation and independently captured Level-2 replay remain pending.

The production `advance_initialization()` dispatcher resumes the caller and
serial-read child from owned phases without repeating a request or cache flush.
Its kind-22 component bundle binds the effective cache-flush address and the
complete host-control, ordered initialization, serial-read and serial-FIFO
images. Child configurations bind idle count, the entire ordered access list
and MSIP policy. Four private candidates pass complete parsing/configuration and
supported phase checks before four allocation-free state swaps commit. Restore
advances no service, host context or target edge. HTIF entry after component
restore rejects explicitly; no complete TSI/CPU checkpoint profile is enabled.

`init-resume/invocation-_rqnva1j/summary.json` passes 240 fresh actual dispatches in
native ASan/UBSan and native VCS processes, 7,012 complete four-owner
readbacks and 6,772 continued operations. Both old native and VCS actual
TestChip producers supply the images. Both destination backends test reset-wait,
queued/partly consumed requests, empty waits and queued responses for both
initialization reads, with cache flushing and MSIP independently on/off. All
5,112 malformed/incompatible/missing/reordered/incoherent component image
checks reject atomically. Four repeated fresh packet-corruption runs detect
`POP expected=1 actual=0` at fixture operation 1 / C=101 before acknowledgement.
Fixture operation labels are not CPU target cycles. `guards-summary.json`
retains native sanitizer/VCS unstarted-caller, HTIF-entry, atomic failed replacement
and repeated complete readback checks.

The original initialization regression passes in `init-regression/invocation-zk0my5ho/summary.json`:
294 fixture continuations, 7,264 complete readbacks,
6,970 continuation records, 60 fresh atomic invalid cases and
four first divergences. All 384 original actual caller images restore in
768 fresh processes; all 160 mixed cache-flush/MSIP captures restore
in 320 fresh processes. These remain component results.
All eight preserved native regression suites, including 263 Python tests and full
FCFS checks, pass in `native-regressions/invocation-zqng441k/summary.json`.

Both complete default/buffered Rocket controls pass in `rocket-controls/invocation-2pjhmxlf/summary.json`
at target C=3,329,794. Every full trace for all four harts and every workload/store
label matches the uninterrupted reference. The unchanged 6,712-byte workload is
`runs/m11-iteration82/workload/rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
`rocket-init-dispatch-linkage.json` binds the new production symbols and exact
header dependencies in both driver/bridge consumers. All 60 translation units
remain; generated RTL, reference, inventory and constant-header hashes match
iteration 104. These controls exercise the exact six recipe settings listed above.

All 32 final/retained audits pass. They include the full unchanged old artifact
catalog after all runs, original memory/clock/replay/TracerV inventories and a
fresh ordinary Rocket RTL 318,637-word/seven-clock diagnostic readback before
edges. That diagnostic uses a pattern, not captured CPU execution state.
`cpu-request-rejections/summary.json` records current complete-CPU preflight
rejection at TSI widget/12 and public capture/restore rejection before target
execution/publication. The first sanitizer pilot is separate: installed FESVR
context initialization allocated a retained 1 MiB stack. Lazy initialization at
first host service lets fresh component dispatch avoid creating that coroutine;
leak checking and installed FESVR bytes remain unchanged.

`selected-results.json`, `native-input-archives.json`,
`executed-native-commands.json` and `verification-commands-native.json` retain
exact results, original source bytes and executable native commands. The full
`artifact-manifest.json` binds every created diagnostic byte and dangling-link
target; `changed-source-artifacts.json` binds all implementation/documentation
files. Protected plan/environment/Conda/index/HEAD checks are recorded separately
in `implementation-turn-guard.json`. Existing iteration-104 commits are published
FireSim first, then Chipyard, with matching tips in `github-publication.json`.
The controller owns new staging and local checkpoint commits.

Fresh rechecks write outside the sealed iteration. Run from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_init_resume_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration105-controller-rechecks/init-resume \
  --init-summary automations/checkpoint_loop/runs/m11-iteration104/init/invocation-tvmgxkbu/summary.json
python -m tools.checkpoint_formats.tests.verify_tsi_init_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration105-controller-rechecks/init-regression \
  --serial-summary automations/checkpoint_loop/runs/m11-iteration103/serial-final/invocation-_z6k6wcy/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration105-controller-rechecks/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration104/rocket-controls/invocation-3e_6lfkl/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

Every nested native VCS build/run shell independently sources both environments
and `vcs-env.sh` last. The JSON command catalog also supplies the full eight-check
native regression and fresh ordinary Rocket RTL VCS probe. VCS remains
Y-2026.03-SP1 `-full64`, GCC/G++ 13 and `-Mupdate` on reused Make builds. All four
required actual CPU checkpoint cuts and both complete restored levels remain
pending. BOOM/Saturn, physical FPGA validation and ASIC power are unchanged.

## Iteration 104: durable complete artifact verification

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration104/`.
The previous verification failed on raw `.git/index` equality. Git cache refreshes
and authorized controller commits can change index bytes; the log does not
identify the exact cache writer. Index/HEAD invariance is a turn-local guard,
not a durable evidence invariant. The durable verifier validates permitted linear controller ancestry,
original protected file bytes, unstaged plans, archived native inputs and every
cataloged diagnostic byte. Source evolution requires original committed bytes
in that history. No source fallback is allowed for captured state, traces,
binaries or logs under `runs/`.

The original iteration-103 seal is unchanged, SHA-256
`08431527f96df89f7a75cb8a900775a1e5ce3d16ef75b45a829d4dd6b353f77d`.
It catalogs 142,367 files / 9,085,529,263 bytes. Fourteen dangling VCS cache links
were absent from its regular-file walk. Their paths and targets are separately
bound in `iteration103-dangling-links.json`, SHA-256
`eaec6ca08508c308a90bd8d6c13530e0be6f6bdbc1ddc047b7dc48d7cea4aebf`.
The audit requires exact combined membership and rejects new links, changed
targets, corrupt/missing/extra files and mismatched seals. The supplemental
catalog records present dangling-link metadata; the old seal made no historical
claim about those link targets. New seals bind such links directly.

All 18 new verifier tests pass. They create disposable Git repositories to test
post-turn controller commits, source provenance, rewritten/unexpected histories,
plan exclusion and diagnostic corruption. These are evidence-verifier tests,
not CPU checkpoint acceptance.

The full catalog/protected-input check passes in `retained-final-19.log`.
All 19 retained native audits pass, and a fresh ordinary Rocket RTL diagnostic
probe matches all 318,637 words / seven clocks before edges in
`retained-final-20.log`. All eight frozen-source native regressions pass in
`native-regressions-final/invocation-tjsmc73w/summary.json`, including all 263
Python tests and complete preserved FCFS checks. The preliminary regression
attempt ran all eight checks but its source-stability guard correctly rejected
the earlier verifier version; it remains separate in `native-regressions/`.
The initial strict catalog rejection for previously unlisted dangling links
also remains separate in `retained-19.log`; neither failure is selected as a
passing result.

The exact recipe rebuilt with all 60 native translation units and both complete
four-hart controls pass in `rocket-controls/invocation-3e_6lfkl/summary.json`.
Default and buffered runs finish at target C=3,329,794; every complete instruction
trace and workload/store label matches the independent uninterrupted reference.
The workload remains the original 6,712-byte `rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These runs establish uninterrupted controls, not fresh CPU checkpoint restores.

The full initialization component suite passes in
`init/invocation-tvmgxkbu/summary.json`: 294 fresh fixture continuations, 7,264
complete readbacks, 6,970 continuation records, 7,766 atomic/phase/interruption
checks per backend, 60 fresh atomic invalid-image rejections and four first
divergences at fixture C=102/C=105 with no failed operation acknowledged. All
384 actual caller images restore in 768 fresh processes, and all 160 mixed
cache-flush/MSIP images restore in 320 fresh processes before edges/services.
These restore caller components; fresh HTIF/child/context/CPU dispatch remains
unsupported. No complete CPU checkpoint profile is enabled.

`selected-results.json`, `native-input-archives.json`,
`executed-native-commands.json` and `verification-commands-native.json` retain
the selected native results, original input snapshots and executable commands.
The latter includes full native VCS builds/runs and a fresh ordinary Rocket RTL
probe, sourcing both environments and `vcs-env.sh` last. Recheck destinations
are outside the sealed iteration, so later verification preserves its membership.
`artifact-manifest.json` binds every created diagnostic file plus dangling-link
targets; `implementation-turn-guard.json` records the separate index/HEAD/input
checks before the controller's next commit. The implementation created no local
repository checkpoint commit and staged no plan. Existing iteration-103 commits
were published FireSim first, then Chipyard; remote tips and submodule pointer
match in `github-publication.json`.

Run the complete old catalog check from the Chipyard root with:

```sh
python -m tools.checkpoint_formats.run_artifacts \
  --manifest automations/checkpoint_loop/runs/m11-iteration103/artifact-manifest.json \
  --manifest-sha256 08431527f96df89f7a75cb8a900775a1e5ce3d16ef75b45a829d4dd6b353f77d \
  --dangling-links automations/checkpoint_loop/runs/m11-iteration104/iteration103-dangling-links.json \
  --dangling-links-sha256 eaec6ca08508c308a90bd8d6c13530e0be6f6bdbc1ddc047b7dc48d7cea4aebf
```

Native build/simulation commands and results are recorded under this iteration's
diagnostic root. Both Rocket levels remain in_progress: complete HTIF/context/
child-caller and cross-owner ownership, required early/warm/outstanding/late CPU
cuts, fresh-process Level-1 continuation and independently captured Level-2 CPU
replay remain pending. No external dependency is missing.

## Iteration 103: production TestChip initialization caller

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration103/`.
See [tsi-init-accesses.md](tsi-init-accesses.md). Both Rocket levels remain
in_progress; CPU early/warmed/outstanding-memory/late checkpoint cuts and
independent captured CPU RTL replay remain pending.

`firesim.tsi.init-accesses.v1` binds the full ordered initialization access list
and hart-0 MSIP policy. It owns the current access index, before/after child
phase and persistent read/result/write/MSIP buffer. Production reset uses these
buffers through the original TestChip virtual read/write and cache-flush paths.
Original packet order, MSIP behavior, empty-response yields and stderr results
are preserved. Complete image validation precedes a fixed-size, service-free
restore. Suspended child/context/caller dispatch remains unsupported; no complete
TSI or CPU profile is enabled.

The exact recipe controls pass in
`rocket-controls-final/invocation-u1tbio70/summary.json`. Both complete four-hart
default/buffered runs finish at C=3,329,794. Every full instruction trace and
workload/store label matches the independent uninterrupted reference. The workload
is the original 6,712-byte `runs/m11-iteration82/workload/rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These are uninterrupted CPU controls. `rocket-init-linkage-audit.json` binds the
new owner's actual native save/validate/load symbols and both driver/bridge
header dependencies. All 60 translation units, generated RTL/reference/manifest/
constants, installed FESVR archive and exact recipe settings are retained.

All 245 Python tests and eight preserved native regressions pass in
`native-regressions/invocation-p1knl8_q/summary.json`. Prior load-memory read/queue,
actual loader, bridge/host control, actual HTIF child/poll, transport and all four
transport-fault checks pass. Four retained state/clock/replay/memory-policy/TracerV
audits and a fresh ordinary Rocket RTL diagnostic zero-edge probe pass. Complete
CPU preflight still rejects TSI widget/12; public capture/restore reject unavailable
durable runtime support before execution or publication. These rejections do not
establish CPU image-loader acceptance.

The source-stable serial suite passes in
`serial-final/invocation-_z6k6wcy/summary.json`: 78 fresh fixture continuations,
1,560 full readbacks, 1,482 records, 40 atomic invalid cases and four first
component divergences; 384 actual HTIF FIFO images restore in 768 fresh processes.
The initialization suite passes in `init/invocation-kyjownt8/summary.json`:
294 fresh fixture continuations, 7,264 full readbacks, 6,970 records and 7,766
atomic/phase/interruption checks per backend. All 60 malformed/incompatible/
missing-owner cases reject before mutation. Valid cursor/result corruption
first differs at fixture C=102/operation 2 and C=105/operation 5, respectively,
in both backends with zero failed operations acknowledged. These are component
operation labels. All 384 actual HTIF caller captures restore in 768 fresh
processes before operations, edges or services. Eight real installed-HTIF runs
exercise mixed TestChip reads/writes with cache flushing and MSIP independently
on/off. Every serial packet word and all four complete init/read/FIFO/host-control
owner images match independent expected bytes at 160 selected host cuts. All
160 caller images additionally restore in 320 fresh sanitizer/VCS processes.
The fresh deposits restore the caller component; they do not reconstruct or
resume its HTIF/serial/cache-flush children.

The preserved read suite passes in `serial-read/invocation-r916gusa/summary.json`:
522 fresh fixture continuations, 71,828 complete read/FIFO readbacks, 35,392
records, 50 atomic invalid cases, four first-divergence cases and 768 fresh
complete actual HTIF read/FIFO pair restores. Host-control passes 362 fixture
continuations and 136 actual loader readbacks in
`host-control/invocation-0tegfw5n/summary.json`; actual child/poll checks retain
162 images/324 fresh readbacks in `host-fesvr/invocation-uen9jmrs/summary.json`.
The actual bridge suite retains all 48 fresh readbacks in
`actual-bridge-restores/invocation-_7u0_8qo/summary.json`. Complete CPU request
rejections are in `cpu-request-rejections/summary.json`. Retained audits and the
fresh ordinary RTL probe commands/results are in `retained-audit-results.json`.

All 19 independent final audits pass. `selected-results.json`,
`native-input-archives.json`, `executed-native-commands.json` and
`verification-commands-native.json` retain exact selections, 950 original input
bindings and 5,706 native command records. The eight-check regression summary
retains every original native artifact and source snapshot. Initial standalone
include and two source-stability failures remain separate diagnostic evidence;
only final frozen-source suites are selected. Existing iteration-102 controller
commits were published FireSim first, then Chipyard; independent remote tips
and the submodule pointer match (`github-publication.json`). No staging or local
commits were performed. No protected input or installed library was changed.

The actual native initialization command is retained in `init-command.json`.
Run its complete VCS/sanitizer check from the Chipyard root with:

```sh
source env.sh && source sims/firesim/env.sh
checkpoint_m11_init_tmp=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration103/recheck-init-XXXXXX")
export TMPDIR="$checkpoint_m11_init_tmp"
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_init_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration103/controller-init-recheck \
  --serial-summary automations/checkpoint_loop/runs/m11-iteration103/serial-final/invocation-_z6k6wcy/summary.json
```

Fresh component caller readbacks do not resume HTIF or a CPU. Full HTIF/memif/
device/stop/signature and TestChip loader/cache-flush child progress, fresh
caller/context reconstruction and cross-owner coherence remain necessary before
active CPU checkpoint cuts and independently restored Level 1 and Level 2.
No external dependency is missing. BOOM and Saturn remain pending.

## Iteration 102: production serial read progress

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration102/`.
See [tsi-serial-read.md](tsi-serial-read.md), including the explicit remaining
HTIF/memif/device/TestChip caller ownership audit. Complete Rocket Level-1 and
Level-2 acceptance remain in_progress. No coherent CPU checkpoint continuation
or captured CPU RTL replay has passed.

`firesim.tsi.serial-read.v1` owns the original serial read address, byte length,
issue/response/complete phase, collected response count and every collected
32-bit word. The FIFOs retain their separate complete owner. Production reads
issue the original packet once, consume responses in order, and switch to the
target only when the response FIFO is empty. Result storage is reserved before
issue/load, and complete configuration/phase/count/width validation precedes
owner mutation. Restore executes no services, context switch or target edge.
The HTIF destination/caller and context reconstruction remain unsupported.
No complete CPU/TSI checkpoint profile is enabled.

Serial-read verification passes in
`serial-read/invocation-avekamwh/summary.json`: 522 fresh fixture continuations,
71,828 complete read/FIFO readbacks, 35,392 continued records and 581 atomic/
interruption checks per backend. All 50 fresh malformed/incompatible/missing
read or FIFO cases reject before mutation. Valid address and collected-word
corruption first differ at fixture C=103/operation 3 and C=115/operation 15 in
both backends, with zero failed operations acknowledged.
The independent Python oracle covers 4/8/64/128/1024-byte reads, pre-issue,
partly transmitted packets, waiting/partial responses, completion, extra queued
responses and a second read. Native sanitizer and VCS DPI checks restore both
complete owners in fresh processes before any operation, compare every resumed
operation/state image, reject malformed/incompatible/missing owners atomically,
and detect valid address/collected-word corruption at its first unacknowledged
boundary. Fixture operation labels are not Rocket target cycles.

The preserved FIFO suite passes in `serial/invocation-hrgwtspy/summary.json`:
78 fresh fixture continuations, 1,560 complete readbacks, 1,482 continued records,
40 fresh invalid cases and four first-divergence cases. All 384 real installed-
HTIF serial images restore in 768 fresh processes. This checker now also retains
complete read-owner captures alongside every actual TestChip init/poll/idle
serial image; all 384 read/FIFO pairs additionally restore in 768 fresh
sanitizer/VCS processes with complete zero-edge/no-service readback. These host-protocol cuts
do not restore HTIF or a CPU.

Exact recipe controls pass in
`rocket-controls/invocation-6yxavjbu/summary.json`, with independent native linkage
and dependency evidence in `rocket-read-complete-linkage-audit.json`. The owned
implementation and all three TestChip/FireSim/bridge consumers bind the new
read header in their actual compiler dependencies. The exact settings,
all 60 native units, generated RTL/reference/manifests/constants and installed
FESVR archive remain unchanged. Both complete four-hart default/buffered runs
pass at C=3,329,794; all full instruction traces and workload/store labels match
the uninterrupted reference. Workload is the original 6,712-byte
`runs/m11-iteration82/workload/rocket-quad.riscv`, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These are controls, not restored CPU workloads or tested CPU checkpoint cuts.

All 245 Python tests and eight preserved native regressions pass in
`native-regressions/invocation-hupf6h08/summary.json`, retaining 5,131 artifacts /
713 original source bindings. Load-memory read/queue/ELF-loader, bridge-control,
transport and all four transport-fault suites pass. Host-control passes all
362 fixture continuations plus 136 actual loader readbacks (`host-control/invocation-dqnxed88/summary.json`). Actual child/poll
checks pass 162 images / 324 fresh readbacks
(`host-fesvr/invocation-lrceiw09/summary.json`); all 48 actual bridge restores pass
(`actual-bridge-restores/invocation-syplrv1t/summary.json`).
Four retained inventory/clock/replay/memory-policy/TracerV audits pass in
`retained-final-audit-results.json`. A fresh ordinary Rocket RTL diagnostic
probe matches all 318,637 semantic words across seven clocks before any edge;
this is diagnostic storage rather than a captured CPU image/replay.

Complete CPU requests reject before execution/checkpoint publication in
`cpu-request-rejections-verified/summary.json`: preflight identifies the unowned
TSI at `widget/12`; capture and restore reject the unavailable public durable
runtime capability. Preflight creates only the unchanged FASED CSV header and
an empty VCS key. Initial diagnostic assertions incorrectly expected no header
and identical rejection paths; their failed logs remain separate. No invalid
CPU-image restore or CPU semantic-corruption detection is claimed.

Existing iteration-101 controller commits were pushed FireSim first
(`f0a3772b537c4cc08942868471549efbb6a1fe12`), then Chipyard
(`b112499963188bcb8e5f8252ba1d31bb7edcaded`). Independent remote-tip and submodule-
pointer checks match; push logs retain the local read-only tracking-ref
messages. Neither plan, installed library nor environment input was edited.
No staging or local commits were performed. BOOM/Saturn remain pending;
standalone Shuttle, physical FPGA and ASIC power remain deferred.

Recovery metadata: `selected-results.json` binds the selected native summaries;
`native-input-archives.json` preserves their original inputs;
`executed-native-commands.json` records the actual native subprocess commands;
`verification-commands-native.json` provides runnable native checks. The root
artifact catalog records full paths and hashes, including initial diagnostics.
All 18 independent evidence audits pass, retaining 944 original input bindings
and 4,236 native command records. Remaining work is the explicit HTIF/memif/device/TestChip caller ledger,
cross-owner coherence, real early/warmed/outstanding-memory/late CPU cuts,
complete fresh Level-1 continuation and independent Level-2 captured replay.
No external dependency is missing.

Executable native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && checkpoint_m11_read_tmp=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration102/vcs-recheck-XXXXXX") && export TMPDIR="$checkpoint_m11_read_tmp" && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_serial_read_vcs --out automations/checkpoint_loop/runs/m11-iteration102/controller-serial-read-recheck --serial-summary automations/checkpoint_loop/runs/m11-iteration102/serial/invocation-hrgwtspy/summary.json
python -m tools.checkpoint_formats.tests.verify_tsi_serial_read_vcs --audit automations/checkpoint_loop/runs/m11-iteration102/serial-read/invocation-avekamwh/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration102/controller-rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration102/rocket-controls/invocation-6yxavjbu/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration102/native-regressions/invocation-hupf6h08/summary.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration102/rocket-controls/invocation-6yxavjbu/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration102/native-input-archives.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration102/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration102/protected-native-inputs.json
```

## Iteration 101: source-integrated FESVR serial FIFO ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration101/`.
See [tsi-serial-queues.md](tsi-serial-queues.md). Both complete Rocket checkpoint
levels remain in_progress. No coherent active CPU checkpoint, fresh CPU Level-1
continuation or captured CPU Level-2 replay has passed.

`firesim.tsi.serial-queues.v1` owns every remaining word in the target-bound and
host-bound serial FIFOs. The distinct source-integrated `firesim_fesvr_tsi_t`
retains the original serial packet, read-yield, handshake, reset and terminal-loop
algorithms. TestChip's `tsi_t` spelling aliases this class through the FireSim
project header. Installed FESVR HTIF/context/library bytes are unchanged. Both
queues validate and allocate fully before no-throw swaps; wrong configuration,
truncation, missing queues, incorrect counts, trailing words and wide data reject
before mutation. Restore performs no services, context switches, serial traffic
or target edges. The suspended read cursor/destination and callers are separate,
still unsupported owners. No complete CPU/TSI profile is enabled.

Selected serial evidence: `serial/invocation-49f0z1gy/summary.json`. Across native
sanitizer and VCS backends, all 78 fresh fixture restores, 1,560 complete
readbacks and 1,482 continued records pass. Each backend passes 904 atomic/interruption
and maximum-chunk checks. All 40 fresh invalid images reject atomically. Valid
request/response corruption first differs at fixture C=108/operation 8 and
C=112/operation 12; zero resumed operations are acknowledged. These are component
operation labels and serial-word faults, not Rocket target cycles or corrupted
DUT-state replay cases.

Actual installed-HTIF checks reconstruct all 384 complete serial images at
loader/reset/poll/idle cuts, including every transmitted packet tail and queued
response, for idle counts 1/3/10. All 384 images additionally restore in both fresh
backends: 768 complete zero-edge component readbacks. The 584-byte polling ELF
has real tohost/fromhost symbols and an original TestChip init read. Its images
are host-protocol cuts, not CPU workload checkpoints. Prior loader checks pass
in `real-fesvr/invocation-t385u4pu/summary.json` (14 read, 22 queue and 68 host
payloads). Additional original HTIF child/poll/idle checks pass all 162 host
payloads and 324 fresh host-control readbacks in
`host-fesvr/invocation-j7o3qk13/summary.json`.

Exact recipe build/control evidence:
`rocket-controls/invocation-7ye21zyi/summary.json` and
`rocket-serial-linkage-audit.json`. The full 59-unit prior inventory is preserved;
only `owned_fesvr_tsi.cc` is added, totaling 60 units. Generated RTL/reference/
manifest/constants, exact recipe settings and installed FESVR archive remain
unchanged. Native symbols bind the owned serial adapter and omit the original
library TSI implementation. All three TSI consumers' compiler dependencies bind
the local base header. Its explicit normal include prevents GCC system-header
filtering from hiding that ABI dependency in cached VCS external-C builds.

Both complete four-hart default/buffered controls pass at C=3,329,794. All four
full instruction traces per mode and all workload/store labels match the
uninterrupted reference. Workload:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
6,712 bytes, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
FESVR archive SHA-256 remains
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
These are full workload controls; required early/warmed-cache/outstanding-memory/
late CPU checkpoint cuts remain pending.

Preserved checks pass: 260 read continuations
(`loadmem-read/invocation-wx0bmjtm`), 340 queue restores
(`loadmem-queues/invocation-ybj12acp`), 228 bridge-control restores
(`bridge-control/invocation-croiwf04`), 48 actual bridge restores
(`actual-bridge-restores/invocation-k8fxdo6a`), 362 host-control fixture restores
plus 136 actual loader readbacks (`host-control/invocation-la9bpo31`), and all
1,012 transport requests / 566,096 full records (`loadmem-transport/invocation-03_a7gew`).
All four private transport faults reject at their first wrong word
(`loadmem-transport-faults/invocation-e4tbgzka`). All 245 Python tests and eight
complete source-stable native regressions pass in
`native-regressions/invocation-e_jefvyh/summary.json`, retaining 5,128 artifacts /
710 original source bindings. Four retained inventory/clock/memory/policy/TracerV
audits and a fresh ordinary Rocket RTL diagnostic probe pass all 318,637 words /
seven clocks before edges (`retained-audit-results.json`). This is diagnostic
storage, not a captured CPU image or replay.

Complete CPU preflight/capture/restore still reject before execution/publication
with `FS_CHECKPOINT_UNSUPPORTED: unsupported host checkpoint owner widget/12`
(`cpu-request-rejections-final/summary.json`). Remaining ownership: serial read
cursor/destination and suspended caller; HTIF poll/fromhost/device/stop/signature;
TestChip loader/cache-flush/init-access progress; and cross-owner coherence.
Coherent active CPU cuts, fresh complete Level-1 continuation and independent
Level-2 complete zero-edge state readback plus captured finite replay remain
pending. No dependency is missing. BOOM/Saturn remain pending; standalone Shuttle,
physical FPGA and ASIC power remain deferred. Both levels remain independent.

Existing iteration-100 controller commits were published FireSim first
(`97900cda9a2f29ec834a9627b3f155812e15d78a`), then Chipyard
(`fd92b046c5e613b676111e791e6664b6789be584`). Independent remote-tip queries and
submodule pointer match (`github-publication.json`). Push logs preserve the
local read-only tracking-ref diagnostic. No staging, local commits or protected
input edits. Initial oracle formatting, symbol-substring, output-path, dependency
and source-stability failures remain diagnostic attempts, not passing evidence.

All created paths are in `artifact-manifest.json`. `selected-results.json` binds
the complete original passing reports; `native-input-archives.json` retains their
original native inputs. `executed-native-commands.json` records original argv,
logs and exits; `verification-commands-native.json` supplies executable native
checks. Independent audits are in `independent-audit-results.json`.

Executable native checks from the Chipyard root (VCS environment sourced last;
unique temporary root prevents tool-shell PID/temporary-directory collisions):

```sh
source env.sh && source sims/firesim/env.sh && checkpoint_m11_serial_tmp=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration101/vcs-recheck-XXXXXX") && export TMPDIR="$checkpoint_m11_serial_tmp" && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_serial_vcs --out automations/checkpoint_loop/runs/m11-iteration101/controller-serial-recheck
python -m tools.checkpoint_formats.tests.verify_tsi_serial_vcs --audit automations/checkpoint_loop/runs/m11-iteration101/serial/invocation-49f0z1gy/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration101/controller-rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration101/rocket-controls/invocation-7ye21zyi/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration101/rocket-controls/invocation-7ye21zyi/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration101/native-input-archives.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration101/native-regressions/invocation-e_jefvyh/summary.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration101/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration101/protected-native-inputs.json
```

## Iteration 100: production FireSim idle/reset control

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration100/`.
See [tsi-host-control.md](tsi-host-control.md). Complete Rocket Level-1 and
Level-2 acceptance remain in_progress. No real CPU checkpoint continuation or
captured CPU RTL replay has passed.

`firesim.tsi.host-control.v1` owns the production FireSim TSI's exact parsed idle
count, busy/host-loaded/target-loaded flags, remaining idle yields and explicit
ready/idle/reset-wait/reset-child phase. The idle cursor changes before each
original switch, including the final suspended yield. Reset enters the original
TestChip child exactly once after target drain. Every candidate word and
configuration byte validates before mutation; restore performs no context
switch, FESVR service, MMIO, serial traffic or target edge. Escaping switch/child
exceptions permanently invalidate component access. Production inspection is
const and the aggregate bridge/CPU checkpoint contract remains unsupported.

Selected component evidence:
`host-control/invocation-lknimday/summary.json`. All 362 fresh sanitizer/VCS
fixture restores pass for idle counts 0/1/3/10 and an active UINT64_MAX cursor.
The original-loop oracle compares 7,866 complete readbacks and 7,504 resumed
records. Each backend passes 1,100 phase/atomic/interruption checks. All 36 fresh
missing/truncated/extra/incompatible/configuration/phase/cursor/flag images
reject atomically. Valid semantic corruption first differs at fixture C=125 /
operation 25 (idle return versus yield) and C=129 / operation 29 (reset yield
versus child entry), with zero resumed operations acknowledged in both backends.
The additional independent exact-scope audit is
`host-control-independent-scope-audit.json`. These are component operation
labels, not Rocket target-cycle boundaries.

Installed-FESVR loader evidence:
`real-fesvr/invocation-dvoja8gh/summary.json`. All 14 prior complete read images
and 22 prior complete queue images pass, and all 68 actual host-control images
match independently constructed payloads at loader/reset-wait/idle-yield cuts.
All 68 images restore in both fresh sanitizer/native and VCS component processes:
136 complete zero-edge readbacks with no FESVR context or services. The installed
FESVR archive remains SHA-256
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
Additional actual TestChip child-reset/HTIF polling checks pass in
`host-fesvr/invocation-y60aa977/summary.json`: 162 independently checked payloads
restore in both fresh backends, totaling 324 complete zero-edge readbacks.
Its 584-byte ELF has real tohost/fromhost symbols,
an init read and duplicate idle-count arguments. It exercises all idle yields,
suspended child read, both poll-response halves and subsequent busy polls.
Its component restores still do not restore HTIF or a CPU.

Prior component regressions pass: 260 read continuations
(`loadmem-read/invocation-n2q6l21r/summary.json`), 340 queue restores
(`loadmem-queues/invocation-s3pe7v94/summary.json`), 228 bridge-control restores
(`bridge-control/invocation-7oto0h22/summary.json`), and 48 actual bridge restores
(`actual-bridge-restores/invocation-d9j8cfdz/summary.json`). Actual transport
retains all 1,012 requests / 566,096 records
(`loadmem-transport/invocation-gjd6k2h9/summary.json`); four private transport
faults still reject at their first wrong word
(`loadmem-transport-faults/invocation-242y_s17/summary.json`).

Exact recipe rebuild:
`rocket-controls/invocation-6ktgjmr4/rocket-build-identity.json` and
`rocket-host-control-linkage-audit.json` bind the new header and all three native
checkpoint methods, with all 59 translation units unchanged and no CPU profile.
Both complete four-hart default/buffered controls pass at target count
3,329,794 (`rocket-controls/invocation-6ktgjmr4/summary.json`). All four complete
traces per mode (37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes) and
all workload/store labels match the uninterrupted reference. These are CPU
controls, not checkpoint continuations. The self-checking
workload remains
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
6,712 bytes, SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
All 245 Python tests and the final eight-check preserved source-stable native
regression batch pass in `native-regressions/invocation-rxa8jg_3/summary.json`,
retaining 5,125 artifacts / 707 source bindings. Four retained complete inventory/
clock/memory/policy/TracerV audits and a fresh ordinary Rocket RTL probe pass
all 318,637 words / seven clocks before edges (`retained-audit-results.json`).
That probe remains diagnostic storage, not captured CPU state.

Complete CPU preflight/capture/restore reject before run/publication in
`cpu-request-rejections/summary.json`. Remaining ownership: FESVR private serial
queues and suspended caller/read destination, HTIF poll/fromhost/device/stop/
signature, TestChip loader/cache-flush/init-access progress, and cross-owner
coherence. HTIF's nonvirtual run path still needs audited source integration or
a pointer-free engine. Required early/warmed-cache/outstanding-memory/late CPU
checkpoint cuts and both independently restored checkpoint levels remain
pending. BOOM/Saturn remain pending; standalone Shuttle, physical FPGA and ASIC
power remain deferred. No dependency is missing.

Existing iteration-99 controller commits were published FireSim first
(`76250b8830fbd6371ff1f71a43ab23bb81a5d0e7`), then Chipyard
(`32b41598af5c621b5d88d655d1f32914491a8abf`). Independently queried remote tips
and the Chipyard submodule pointer match (`github-publication.json`). No staging,
local commits or protected input edits. Initial transcript formatting, VCS temp
collision, source-stability rejection and actual-host pilot diagnostics remain
separate. Failed runs are not passing evidence. VCS retries use distinct TMPDIR
roots because separate tool shells can share timestamp/PID namespaces.

All created paths are recorded in `artifact-manifest.json`; selected native
reports are in `selected-results.json`. Original executed argv/exit/log records
are in `executed-native-commands.json`; executable checks are in
`verification-commands-native.json`. `native-input-archives.json` retains 929
original native source/build bindings; `protected-native-inputs.json` and the
retained-evidence checks preserve protected files and controller ancestry.
Independent original native audits are in `independent-audit-results.json`.

Executable complete native checks from the Chipyard root (VCS environment
sourced last; separate temporary roots prevent tool-shell PID collisions):

```sh
source env.sh && source sims/firesim/env.sh && checkpoint_m11_recheck_tmp=$(mktemp -d "$PWD/automations/checkpoint_loop/runs/m11-iteration100/vcs-recheck-XXXXXX") && export TMPDIR="$checkpoint_m11_recheck_tmp" && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs --out automations/checkpoint_loop/runs/m11-iteration100/controller-real-fesvr-recheck
python -m tools.checkpoint_formats.tests.verify_tsi_host_control_vcs --out automations/checkpoint_loop/runs/m11-iteration100/controller-host-control-recheck --fesvr-summary automations/checkpoint_loop/runs/m11-iteration100/real-fesvr/invocation-dvoja8gh/summary.json
python -m tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs --out automations/checkpoint_loop/runs/m11-iteration100/controller-host-fesvr-recheck --component-summary automations/checkpoint_loop/runs/m11-iteration100/host-control/invocation-lknimday/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration100/native-regressions/invocation-rxa8jg_3/summary.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration100/rocket-controls/invocation-6ktgjmr4/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration100/native-input-archives.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration100/controller-rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration100/rocket-controls/invocation-6ktgjmr4/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration100/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration100/protected-native-inputs.json
```

## Iteration 99: production TSI bridge host control

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration99/`.
See [tsi-bridge-control.md](tsi-bridge-control.md). Complete Rocket checkpoint
acceptance remains in_progress; no real CPU workload image or captured CPU RTL
replay has passed.

`firesim.tsi.bridge-control.v1` owns the production bridge's initialization,
remaining reset-delay cursor and one-time early-fast transition. Its immutable
identity binds all nine MMIO addresses, selected TSI index/arguments, memory
availability/offset/beat width and configured steps/wait/fast settings. Restore
validates the entire identity and both mutable words before changing either;
it executes no services, MMIO or FESVR work. Every init/tick/status callback is
guarded; reentrant/active access and interrupted calls reject. The original
loading-step computation and original callback order are preserved. The bridge's
aggregate checkpoint schema remains unsupported, and its component is exposed
only for const inspection.

Selected evidence: `bridge-control/invocation-9t8x1ge_/summary.json`. All 228
fresh sanitizer/VCS component restores pass across both fast settings and waits
0/1/8 at every completed-operation cut. The independent original-flow oracle
compares 2,584 complete state readbacks and 2,356 continued callback records.
Each backend passes 476/488/572/482/494/578 atomic/lifecycle/callback checks
for variants 0-0/0-1/0-8/1-0/1-1/1-8 (3,090 checks per backend). Forty fresh
malformed/missing/truncated/incompatible/lifecycle image processes reject
before mutation or services. A valid wait-cursor corruption differs at fixture
C=119 / operation 19: expected `RECEIVE` after `DONE=1`, actual `GO`; neither
backend acknowledges any resumed operation. These are bridge-component fixture
labels, not Rocket target-cycle cuts. Two additional fresh executable native/VCS
restore commands pass in `executable-native-command-checks.json`.

Actual installed-FESVR transport evidence:
`loadmem-transport/invocation-ixxqv4xu/summary.json`. All 1,012 requests /
566,096 independent records, 32 invalid requests before I/O, four callback-unwind
checks and four actual public TSI bridge runs pass. Twenty-four complete actual
bridge-control images match independently reconstructed identity/state bytes
at construction, init and four ELF loader ticks for both beat widths/backends.
Capture/validation performs no MMIO. All 24 actual images additionally restore
in both fresh sanitizer/native and VCS processes: 48 complete zero-edge
readbacks with no services object or service calls in
`actual-bridge-restores/invocation-g3r7hq1g/summary.json`. This restores only
the bridge host component, not its FESVR caller or generated RTL.
The actual FESVR fourteen read images and
22 complete queue images pass in `real-fesvr/invocation-sqy1po4i/summary.json`.
The ELF/library hashes remain
`45a7f219e68180b49d557cad0c10277277af843c16e4a5e58dc8fb7fb6cb77be` /
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
Private repeated-beat/response-bit faults retain first wrong-word detection
in `loadmem-transport-faults/invocation-i4m8rpm4/summary.json`.

The exact-recipe rebuild binds the new bridge-control header and all three
checkpoint symbols, retaining all 59 native translation units and no CPU profile
(`rocket-bridge-control-linkage-audit.json`). Both complete four-hart default/
buffered controls pass at C=3,329,794 in
`rocket-controls/invocation-u5mnr995/summary.json`. All four complete traces
per mode (37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes) and all
workload/store labels match the uninterrupted reference.
Workload bytes/hash and original target-cycle labels remain bound by
`rocket-controls/invocation-u5mnr995/rocket-build-identity.json` and its runtime
commands; the self-checking ELF is 6,712 bytes at
`automations/checkpoint_loop/runs/m11-iteration82/workload/rocket-quad.riscv`,
with SHA-256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
These are uninterrupted CPU controls.

All 245 Python tests and eight preserved native checks pass in
`native-regressions/invocation-eatwfw4a/summary.json`; independent re-audit passes
with 5,116 retained artifacts and 698 original source bindings. Four retained
complete inventory/clock/memory/policy/TracerV audits pass, plus a fresh ordinary
Rocket RTL diagnostic probe of all 318,637 words / seven clocks before edges
(`native-rocket-probe-OwmYMm/run.log`, commands in
`retained-audit-results.json`). Complete CPU preflight/capture/restore still
reject before run/publication in `cpu-request-rejections-final/summary.json`.
All 260 prior production read-owner continuations pass again in
`loadmem-read/invocation-2ghbp73n/summary.json`; all 340 production queue
restores / 5,950 complete readbacks / 5,610 continuation records and 42 invalid
image processes pass in `loadmem-queues/invocation-wvii4cf1/summary.json`.

Remaining ownership includes FESVR's private serial queues, suspended read caller/
destination and HTIF/context; HTIF poll/fromhost callbacks and device/stop/signature
state; TestChip program-load/cache-flush/init-access progress; and FireSim idle/
reset flags/cursors and aggregate cross-owner validation. `htif_t::run()` is
nonvirtual, and `tsi_t::host_thread` calls it through `tsi_t*`: a derived method
with the same name cannot reconstruct or replace this execution path. A complete
adapter needs an audited pointer-free protocol engine or audited FESVR source
integration; restoring only the two serial queues would still omit the suspended
caller. Installed FESVR remains a hashed input, not a missing dependency.

Coherent four-hart cuts at early/warm-cache/outstanding-memory/late execution,
fresh Level-1 CPU continuation and independent Level-2 CPU .rtlckpt/.trace replay
remain pending. BOOM/Saturn remain pending. Physical FPGA, standalone Shuttle
and ASIC power remain deferred. Published existing iteration-98 controller commits
FireSim `bd38643e84405ca75f02092ce2e2615e6042d419`, then Chipyard
`9d909c6ff114d8eb73268badc17663b8f84f73ca`; both independently queried remote tips
match. Read-only local tracking-ref diagnostics are retained in
`github-publication.json`. No local commit, staging or protected-input edit.

All created paths are in `artifact-manifest.json`; original native artifacts and
source inputs are sealed in `native-input-archives.json`. Exact original commands
and exits are retained in `executed-native-commands.json`; runnable complete
checks are in `verification-commands-native.json`. Both fresh executable native/
VCS command forms pass independently.

Executable native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_tsi_bridge_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration99/bridge-recheck
python -m tools.checkpoint_formats.tests.verify_tsi_bridge_checkpoint_vcs --audit automations/checkpoint_loop/runs/m11-iteration99/bridge-control/invocation-9t8x1ge_/summary.json
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_vcs --out automations/checkpoint_loop/runs/m11-iteration99/transport-recheck
python -m tools.checkpoint_formats.tests.verify_tsi_bridge_actual_vcs --out automations/checkpoint_loop/runs/m11-iteration99/actual-bridge-recheck --transport-summary automations/checkpoint_loop/runs/m11-iteration99/loadmem-transport/invocation-ixxqv4xu/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration99/native-regressions/invocation-eatwfw4a/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration99/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration99/rocket-controls/invocation-u5mnr995/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

## Iteration 98: complete production TSI load-memory queues

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration98/`.
No CPU checkpoint acceptance is claimed. See
[tsi-loadmem-queues.md](tsi-loadmem-queues.md) for the payload contract and
remaining parent-state owners. The read-operation schema, FCFS profile and
independent Level-2 schemas are preserved.

`firesim.tsi.loadmem-queues.v1` owns all four production queues and the active
write request/consumed-byte cursor. Restore validates complete write-data
ownership, request arithmetic, configuration, queue lengths and response widths
before allocating/committing all candidate queues. No host I/O, HTIF work or
dequeue occurs during load/readback. The actual TSI delegates all queue accesses
to this owner; const component inspection does not enable aggregate restore.

Selected evidence: `loadmem-queues/invocation-isd5rmud/summary.json`.
All 340 fresh sanitizer/VCS component restores pass for 4/8/64/1,024/4,096-byte
writes/reads at every completed-call cut. The independent oracle compares 5,950
complete state readbacks and 5,610 subsequent records, including overlapping
read/write queues, zero/full/high-bit responses, FIFO order, address crossings
and byte-granular partial write drains. Each backend passes 134 atomic checks;
42 fresh malformed/missing/truncated/incompatible/incomplete image processes
reject before mutation/continuation/publication. Actual valid write-data
corruption first differs at fixture C=114 / operation 14: `DATA 1 00` versus
`DATA 1 01`, with zero resumed operations acknowledged in either backend.
These labels are host fixture labels, not Rocket target cycles.

Actual installed-FESVR evidence:
`real-fesvr-current/invocation-b_yth_n4/summary.json`. Both native/VCS ELF-load
runs preserve all fourteen suspended read-operation images and match 22 complete
queue images, including one-byte write drain and pending response cuts. All 22
actual queue images additionally restore in fresh native/VCS processes and match
their entire component continuations in `real-queue-restores/summary.json`.
HTIF itself is not restored. The ELF/library hashes remain
`45a7f219e68180b49d557cad0c10277277af843c16e4a5e58dc8fb7fb6cb77be` /
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
Historical iteration-96 read-only evidence still audits under its original scope.

The exact-recipe rebuild binds the new queue header and save/validate/load
symbols, with all 59 native translation units unchanged
(`rocket-queue-linkage-audit.json`). Both full four-hart default/buffered controls
pass at C=3,329,794 in `rocket-controls/invocation-evqkntda/summary.json`.
All four complete traces per mode (37,582,346 / 49,976,156 / 50,391,641 /
50,189,006 bytes) and all workload/store labels match the uninterrupted reference.
The self-checking four-hart workload hash remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Exact settings, source/workload hashes, original native argv/environment and
process/exit records are bound by the invocation's `rocket-build-identity.json`
and retained commands. These runs are CPU controls, not checkpoint continuations.
A fresh ordinary Rocket RTL diagnostic probe reads all 318,637 words / seven
clocks before edges in `native-rocket-probe-mW61Q6/run.log`. This remains a
storage probe, not a workload image.
Current complete CPU preflight/capture/restore requests reject unsupported TSI
or absent durable capability before run/publication in
`cpu-request-rejections-final/summary.json`. Two earlier rejection-checker
wording mistakes are retained as failures; the final three checks actually pass.

All 245 Python tests and all eight preserved native checks pass in
`native-regressions/invocation-1xwnfhz9/summary.json`; its independent audit seals
5,113 artifacts and 695 original source bindings. The 260 prior read-owner fresh
continuations pass again in `loadmem-read/invocation-zm4hqn4f/summary.json`.
Production transport retains all 1,012 requests / 566,096 records, 32 invalid
requests before I/O, four callback-unwind checks and four actual bridge runs in
`loadmem-transport/invocation-hff1svl3/summary.json`. Both private repeated-beat /
response-bit fault backends still detect their first unacknowledged wrong word in
`loadmem-transport-faults/invocation-alr14lc9/summary.json`. Four independent
retained complete inventory/clock/memory/policy/TracerV audits pass.

Complete HTIF/context/serial/device/idle/reset/bridge ownership and cross-owner
validation remain required. Both independent checkpoint levels at early,
warmed-cache, outstanding-memory and late four-hart cuts remain pending.
No dependency is missing. BOOM/Saturn remain pending; physical FPGA and ASIC
work remain deferred. Existing iteration-97 controller commits were published
FireSim first (`1bdd959cc68d4f31964d06841c6002c7fc62032c`), then Chipyard
(`db5af10d786b231fa512d45429e2cb781b55819b`); independently queried remote tips
match. Local read-only tracking-ref diagnostics are retained. No local commit,
staging or protected-input edit was performed.

All created run paths are enumerated in `artifact-manifest.json`; original
native artifacts/build inputs are sealed in `native-input-archives.json`.
Exact executed native commands and fresh-output rechecks are recorded in
`verification-commands-native.json`; both native/VCS command forms are themselves
tested in `executable-native-command-checks.json`. Parent HTIF/context remains
explicitly unsupported. Plans remain read-only.

Executable native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_loadmem_queues_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration98/queue-recheck
python -m tools.checkpoint_formats.tests.verify_loadmem_queues_checkpoint_vcs --audit automations/checkpoint_loop/runs/m11-iteration98/loadmem-queues/invocation-isd5rmud/summary.json
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs --out automations/checkpoint_loop/runs/m11-iteration98/fesvr-recheck
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs --audit automations/checkpoint_loop/runs/m11-iteration98/real-fesvr-current/invocation-b_yth_n4/summary.json
python -m tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration98/read-recheck
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration98/native-regressions/invocation-1xwnfhz9/summary.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration98/rocket-controls/invocation-evqkntda/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration98/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration98/rocket-controls/invocation-evqkntda/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

## Iteration 97: production multi-beat TSI read transport

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration97/`.
No CPU checkpoint acceptance is claimed. See
[tsi-loadmem-transport.md](tsi-loadmem-transport.md) for the transport contract
and the independently pending state owners.

The production TSI bridge now advances translated read addresses across beats
and owns its GMP export destination and temporary value through exception
cleanup. Narrow requests select their actual lanes within aligned host-memory
beats. Whole-request validation rejects invalid sizes/alignment/beat widths,
address wrap and signed-offset underflow/overflow before MMIO or response
publication. This fixes the previously recorded repeated-first-beat bug and
export allocation leak; it introduces no aggregate TSI checkpoint schema.

Selected immutable component evidence:
`loadmem-transport-final/invocation-dd0p5ayx/summary.json`. All 1,012 native/
VCS requests and 566,096 independently expanded MMIO/response records match.
Requests cover 4/8/12/64/128/1,024/4,096 bytes, 1/2/4/16-word beats, first/last
lane starts, zero/sparse/full-bit words, signed offsets, crossings of the low
32-bit address boundary and valid unsigned/`INT64_MIN` boundaries. Thirty-two
malformed requests reject before I/O; four injected response/platform failures
exercise scoped cleanup in sanitizer/native and VCS runs. Four actual public
TSI bridge runs use the installed FESVR archive and original partial-write ELF;
all complete MMIO and serial transcripts match, including a two-beat read,
eight merged bytes, original aligned writes and six reset words. The integration
ELF hash remains `45a7f219e68180b49d557cad0c10277277af843c16e4a5e58dc8fb7fb6cb77be`;
the FESVR library hash remains
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
These are host transport runs, not CPU execution/checkpoint cuts.

Selected native/VCS fault evidence:
`loadmem-transport-faults-current/invocation-ea5fqt9a/summary.json`. Private
header mutations reproduce the original repeated beat and flip a real response
bit. All four processes reject at the first wrong response, with no wrong-word
acknowledgement or subsequent FESVR work. The repeated-beat fault first differs
at response word 1 / host address 4,294,967,284, expected 1,092,632,414 versus
actual zero, with one word acknowledged. The bit flip differs at response word
0 / host address 4,294,967,280, expected zero versus one, with zero words
acknowledged. These response labels are not target-cycle or post-restore
corruption evidence. Native failure status is propagated explicitly through DPI;
VCS's zero process exit for `$fatal` is retained as an initial rejected check.

The exact-recipe rebuild binds the new helper and retains all 59 translation
units (`rocket-tsi-transport-integration-audit.json`). Both complete default/
buffered four-hart controls pass at C=3,329,794 in
`rocket-controls/invocation-mvyq_wmu/summary.json`. All four full instruction
traces per mode (37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes) and
all workload/store labels match the uninterrupted reference. These are CPU
controls, not CPU checkpoint cuts. The self-checking four-hart workload hash
is `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Source/workload hashes and unchanged exact recipe settings are bound by
`rocket-build-identity.json` and the invocation record. The native build and
all command/environment/exit records are retained with their original paths.
Fresh ordinary Rocket RTL VCS reads all 318,637 words / seven clocks before
edges in `native-rocket-probe-*/run.log`; this is a diagnostic storage probe,
not a CPU image or captured CPU trace. Current CPU preflight/capture/restore
still reject unsupported TSI or missing durable capability before execution
and file publication (`cpu-request-rejections/summary.json`).

All 245 Python tests and eight final native regressions pass in
`native-regressions-current/invocation-u3d8wjhm/summary.json`; its independent
audit preserves 5,110 artifacts and 692 source bindings. The initial full
suite rejected a concurrent fixture source change; the entire final suite ran
again against the final sources. Retained complete inventory, clocks,
memory/policy, TracerV, driver, read-owner and real-FESVR audits pass. Earlier
link, argument, unsigned fixture-offset and VCS-exit diagnostics are preserved
in `failure-ledger.json`.
Both required checkpoint levels at early, warmed-cache, outstanding-memory and
late four-hart cuts remain pending, including complete HTIF/context/queue/device
ownership and coherent generated/semantic capture. BOOM/Saturn remain pending;
physical FPGA/ASIC work remains deferred. No dependency is missing.

Complete paths and immutable source/artifact bindings are recorded in
`artifact-manifest.json` and `native-input-archives.json`; both final retention
audits pass all 12,876 original bindings. The inherited saved probe command had
an escaping error; the original catalog is preserved, and the corrected command
is tested in a fresh native process. Its command/readback and original evidence
are additionally sealed in `native-input-archives-v2.json`. Exact executed native
argv, fresh process results and independently runnable checks are recorded in
`verification-commands-native.json` and each selected invocation's command records.

Executable native commands from the Chipyard root (every nested VCS build/run
also sources the pinned helper last):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_vcs --out automations/checkpoint_loop/runs/m11-iteration97/transport-recheck
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_faults_vcs --out automations/checkpoint_loop/runs/m11-iteration97/transport-faults-recheck
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_vcs --audit automations/checkpoint_loop/runs/m11-iteration97/loadmem-transport-final/invocation-dd0p5ayx/summary.json
python -m tools.checkpoint_formats.tests.verify_loadmem_transport_faults_vcs --audit automations/checkpoint_loop/runs/m11-iteration97/loadmem-transport-faults-current/invocation-ea5fqt9a/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration97/native-regressions-current/invocation-u3d8wjhm/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration97/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration97/rocket-controls/invocation-mvyq_wmu/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

## Iteration 96: explicit production TSI load-memory read operation

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration96/`.
No CPU checkpoint acceptance is claimed.

The production `firesim_tsi_t::load_mem_read` now uses the pointer-free
`firesim.tsi.loadmem-read.v1` operation owner. It owns drain/issue/response/
complete progress, address/length and every consumed response word. Save/load
does not issue requests or dequeue responses. Entire-candidate validation and
response-capacity allocation precede mutation. Configuration, phase, lengths,
alignment, address overflow and response cursors are checked. Active/interrupted
callbacks reject. Its four queue owners and HTIF's suspended caller/destination,
program loader, contexts and devices remain separate and incomplete. The TSI
bridge still rejects complete checkpointing. See
[tsi-loadmem-read.md](tsi-loadmem-read.md).

Selected component evidence:
`loadmem-read-current/invocation-gauvuay_/summary.json`. All 260 fresh sanitizer/
VCS continuations pass for 4/8/64/128/1,024/4,096-byte reads, including pending
writes, empty response queues, partial results, completion and acknowledgement.
All 520 complete owner/queue pre-edge readbacks and 193,094 continued call/data/
fixture-cycle records match the independent original-loop oracle. Each backend
passes 306 atomic/configuration/lifecycle checks. Twenty-eight fresh invalid
processes reject missing/truncated/trailing/version/kind/incompatible/phase/
cursor/alignment/length/response-width images before mutation/requests/readback.
Actual valid response corruption first differs at fixture C=127,
`RESULT[0] expected=0 actual=1`; operation 27 is never acknowledged (26 were).
All 306 component build/check/restore processes and original input snapshots
are retained. The final DPI failure exits with native status 2: earlier VCS
`$fatal` returned zero and correctly failed the runner's required exit check.
Earlier oracle-label and fixture-exit diagnostics remain separately retained.
These are host-component cuts; they do not satisfy required Rocket CPU cuts.

Actual installed-FESVR integration passes in native C++ and VCS DPI:
`real-fesvr-native/invocation-4ed87qfs/summary.json`. The generated RISC-V ELF
forces the production program-loader read/modify/write path with an incomplete
one-word response. All fourteen complete suspended-owner images match an
independent byte oracle; eight merged bytes and six reset serial words match.
This checks real FESVR integration, not CPU execution or context migration.
Integration ELF SHA256 is
`45a7f219e68180b49d557cad0c10277277af843c16e4a5e58dc8fb7fb6cb77be`;
the actual linked FESVR archive is
`08a1cc5ae67f20e6912b8add62ce6e24da0b2931a212f35b31d08c652943819d`.
The first VCS link diagnostic is retained; the final link explicitly retains
the static FESVR archive when VCS places link flags before its C++ objects.

Exact Rocket build settings remain those above. The current rebuild retains
all 59 native units and binds the new owner header, implementation and actual
save/validate/load symbols (`rocket-tsi-read-integration-audit.json`). Both full
four-hart default/buffered controls pass at C=3,329,794 in
`rocket-controls/invocation-hh3w9zq2/`. All four complete traces
(37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes) and workload/store
labels match the original uninterrupted reference. These are CPU controls;
complete CPU checkpoint cuts remain pending. The workload hash remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
A fresh ordinary Rocket VCS diagnostic storage probe reads all 318,637 words
with seven clocks held before edges; it is not a CPU checkpoint image/trace.
Current CPU preflight/capture/restore requests still reject unsupported TSI or
missing durable capability before run/image/bridge output.

The final complete eight-check regression suite passes, including all 245 Python
tests, full M2/M3 metasim/ordinary RTL, widget/UART/blockdev/heartbeat ownership
and FCFS guards. Selected evidence:
`native-regressions-current/invocation-kf453gp_/summary.json` (5,106 retained
artifacts / 688 source bindings). The earlier complete eight-check invocation
is also preserved. Retained complete Rocket inventory, clock-event replay,
memory/policy, TracerV, FireSim driver and original four-hart control audits pass.

Executable native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration96/read-recheck
python -m tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs --audit automations/checkpoint_loop/runs/m11-iteration96/loadmem-read-current/invocation-gauvuay_/summary.json
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs --out automations/checkpoint_loop/runs/m11-iteration96/fesvr-recheck
python -m tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs --audit automations/checkpoint_loop/runs/m11-iteration96/real-fesvr-native/invocation-4ed87qfs/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration96/native-regressions-current/invocation-kf453gp_/summary.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration96/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration96/rocket-controls/invocation-hh3w9zq2/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

Complete Level-1 fresh CPU continuation, Level-2 coherent CPU capture/readback/
captured-trace replay and all required early/warmed-cache/outstanding-memory/
late CPU cuts remain pending. Component labels cannot satisfy CPU cuts. No
dependency is missing. BOOM/Saturn remain pending; physical FPGA, standalone
Shuttle and ASIC power remain deferred. Existing iteration-95 controller
commits FireSim `b4e1daad6df62fda628ee56e69e5e71a43cac9d0`, then Chipyard
`a20c3f2a2ddac0f63e3627575d25302a9c96890b` are published and independently
confirmed (`publication.json`). Plans remain read-only; no staging/local commits.

`verification-commands.json` records executable argv, including a fresh complete
ordinary Rocket zero-edge VCS probe. `native-input-archives.json` seals 37,119
original native artifacts/input bindings, including failed invocations and
per-invocation source snapshots; every original runtime path remains mandatory.
The internal and executable CLI evidence audits pass
(`final-native-evidence-audit.json`, `final-archive-cli-audit.json`). Complete
artifact paths are in `artifact-manifest.json`; progress and remaining work are
in `summary.json`. Rechecks allocate new directories and preserve originals.

## Iteration 95: production FireSim driver and per-bridge termination ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration95/`.

The actual `firesim_top_t` now returns after completed synchronous host operations.
Its independent `firesim.bridge-run-loop.v1` owner preserves ready/tasks/issue/
poll/tick/terminate/status/finished phases, next bridge, termination and signed
32-bit exit code. It checks termination immediately after each bridge tick and
stops before touching later bridges. A successful termination query retains its
bridge until the exit-status call commits. Credit, PeekPoke and bridge calls
never replay after restore. Active/interrupted calls poison and reject.
`firesim.simulation.bridge-driver.v1` binds effective profiling configuration,
PeekPoke identity/schema and the complete post-heartbeat registry traversal.
It owns running/finalized lifecycle and requires fresh loading without MMIO,
callback execution, initialization or finalization. Anonymous profiling tasks
remain explicitly unsupported. Base flow, scheduler, each bridge, transport,
functional memory and generated RTL are separate owners. The FCFS driver,
loop and schemas are unchanged. See `firesim-driver-owner-audit.json`.

Selected original component evidence:
`firesim-driver-native/invocation-_u5imb8v/summary.json`. Native ASan/UBSan and
VCS DPI each exercise four distinct early terminating bridges with statuses
0/7/-9/INT_MIN, horizon exhaustion, and immediate zero-horizon completion.
Every completed host call is a cut: 18/20/22/24/27/1 per scenario. All 224 fresh
continuations pass; the independent original nested-loop oracle checks 2,464
complete owner payloads before edges and 4,846 continued boundary records.
Each backend passes 871 atomic/configuration/lifecycle assertions. Sixteen
separate invalid-owner processes reject missing/truncated/trailing/unknown/
incompatible/impossible-state images before loads, readback publication or
edges. Actual structurally valid next-bridge corruption first reports
`fixture_cycle=106 operation=6 acknowledged=5 expected=R 200 0 actual=R 208 0`;
the changed read is never acknowledged. These labels describe host fixtures,
not active Rocket target-cycle checkpoints or DUT semantic corruption.
All 258 executed component processes, input snapshots and complete artifact
catalogs are retained. No ASan/UBSan/leak diagnostics occur. A fixture's initial
global wall-clock stub incorrectly affected VCS licensing; the final fixture
pins only heartbeat's diagnostic clock and leaves libc/VCS time intact. Initial
compile/oracle/license diagnostics remain in separate failed invocations.

Exact Rocket VCS builds retain all 58 original native translation units and add
only `core/bridge_run_loop.cc`. Actual linked driver/loop hooks and all build
inputs are bound in `rocket-native-source-inventory-delta.json` and
`rocket-controls/invocation-4sp34o9f/rocket-build-identity.json`. Both full default
and buffered four-hart controls pass at C=3,329,794. All four complete traces
(37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes) and decoded workload/
store labels match the original uninterrupted reference. These are real active
CPU controls, not checkpoints. The independent current audit is
`rocket-controls-independent-audit.json`; original executable native build and
runtime argv are in the selected invocation's `summary.json`.
The existing self-checking workload hash remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Actual current CPU preflight still rejects TSI at `widget/12`; capture and
restore reject before run because no durable CPU capability exists. The three
native requests publish no image or bridge output. These are unsupported-owner
guards, not malformed CPU-image acceptance (`cpu-request-rejections/summary.json`).
`rocket-tsi-fesvr-pending-owner-audit.json` lists the full next-owner chain,
including HTIF's suspended fromhost queue/callback and read destinations,
program-load/reset/idle progress, contexts, serial/loadmem queues and device
handles. Capturing deques alone cannot reconstruct a fresh FESVR process.
Installed headers, checked source and actually linked FESVR library are hashed;
no TSI support is inferred.

All 245 Python tests and eight preserved native checks pass in
`native-regressions/invocation-rovyvlmy/summary.json` (5,100 retained artifacts /
682 source bindings). An earlier eight-check execution overlapped edits and
correctly failed its source-retention guard; it remains preserved. Independent
retained inventory, clock-event, memory, TracerV and original four-hart control
audits pass. A fresh ordinary Rocket VCS process reads all 318,637 diagnostic
semantic words with seven clocks held and zero edges. This remains a storage
probe, not a CPU image/trace. Current native commands source both repository
environments then `vcs-env.sh` last; VCS Y-2026.03-SP1, `-full64`, GCC/G++ 13.

Executable checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_firesim_driver_checkpoint_vcs --out automations/checkpoint_loop/runs/m11-iteration95/firesim-driver-recheck
python -m tools.checkpoint_formats.tests.verify_firesim_driver_checkpoint_vcs --audit automations/checkpoint_loop/runs/m11-iteration95/firesim-driver-native/invocation-_u5imb8v/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration95/native-regressions/invocation-rovyvlmy/summary.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration95/rocket-controls/invocation-4sp34o9f/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration95/native-input-archives.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration94/rocket-controls/invocation-s3q7sujf/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration94/native-input-archives.json
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration95/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration95/rocket-controls/invocation-4sp34o9f/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

`verification-commands.json` also records an executable fresh ordinary Rocket
zero-edge VCS probe with complete pattern/baseline paths, plus the retained-
evidence audit. `native-input-archives.json` seals original native bytes and
source snapshots; `artifact-manifest.json` lists full artifact paths. Rechecks
allocate new directories and never overwrite a selected native invocation.
The final archive binds 62,123 original native inputs/artifacts; both the
internal and executable CLI retention audits pass. A first sealing catalog
included its active stdout and correctly failed the later retention check.
`first-seal-diagnostic/` preserves that rejection. The final catalog excludes
only sealer stdout while all native build/runtime logs remain mandatory.

Acceptance remains **in_progress**. Complete TSI/FESVR, stream/transport and
remaining runtime owners; bind all semantic owners through actual FAME metasim
with coherent clock events; then verify fresh complete Level-1 CPU continuation
and independent Level-2 CPU image/readback/captured-trace replay at early,
warmed-cache, outstanding-memory and late cuts. No required CPU checkpoint cut
has passed. No external dependency is missing. BOOM/Saturn remain pending;
physical FPGA/standalone Shuttle/ASIC work is deferred. Existing iteration-94
controller commits FireSim `28f6aa38fb1033921c399509069eb1cbd6f0b04e`, then
Chipyard `715088bb1364419f914264cc8c218723604d4c18`, are published and their remote
tips independently confirmed (`publication.json`). No staging or local commits;
both plans remain read-only.

## Iteration 94: complete TracerV host ownership and exact-recipe controls

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration94/`.

`+tracerv-checkpoint-buffered` adds `firesim.bridge.tracerv.v1` for completed
host calls. Save/restore does not pull/flush streams, change MMIO or publish an
output file. Own initialization, `cur_cycle` and the entire serialized history,
including the clock header. Bind all fifteen MMIO addresses, stream index/depth,
core IPC, clock name/ratio, trace enable, output/test mode, and every cycle/PC/
instruction trigger field. An output path is a fresh-process sink; its history
comes from captured bytes. Base simulator/stream references are rebound to
separate owners. Active/poisoned calls, finished/live-file/fireperf/tracker modes
and nonzero legacy DMA state reject. Temporary serializer FILE/buffer state
exists only inside guarded calls. `tracerv-owner-audit.json` lists every member,
including explicitly absent/rebound fields and separately owned hardware.
Generated TracerV FIFO/trigger/cycle state and CPU AXI queues remain separate;
this host adapter does not authorize an aggregate CPU profile.

The selected original host-component invocation is
`tracerv-native/invocation-ou6pxbr8/summary.json`: 256 fresh continuations,
296 executed processes including two builds, all four exact Rocket constructors
(streams 0–3, depth 6,144, IPC 1, 1/1 clock ratio), human/binary/test/disabled
modes and trigger selectors 0–3. Eight host-call cuts per case have fixture
labels C=100/107/114/121/128/135/142/149. They include complete batches, queued
traffic below the drain threshold, flushes and the final pre-publication state.
An independent byte/MMIO oracle verifies every owner and separately captured
fixture queue before edges and all 1,152 continued calls. Each backend passes
1,482 unchanged-state/configuration/lifecycle assertions. Reentrant calls and
interrupted pulls poison/reject rather than expose a suspended buffer.
Valid lifecycle corruption rejects before init MMIO; valid captured-history
corruption first reports `tracerv_output` at fixture C=149 without completing
that boundary. These are host fixtures, not active CPU checkpoint cuts.

Separate original `tracerv-invalid-native/invocation-375e7cg0/summary.json`
records sixteen actual fresh native/VCS processes rejecting missing/truncated/
trailing/unknown/incompatible/invalid-length/lifecycle/empty images before
fixture edges or readback publication, preserving the fresh sink sentinel.
All 312 selected process logs have no ASan/UBSan/leak diagnostics. Original
source snapshots and complete artifact catalogs seal both invocations. The
first VCS link failed because as-needed linking discarded libraries placed
before its objects; corrected link flags retain libelf/libdwarf. The failed
invocation remains preserved separately.

The exact Rocket VCS build is retained under
`rocket-controls/invocation-s3q7sujf/`. `rocket-tracerv-integration-audit.json`
binds its actual binary/header/source hashes, all three linked hooks and exact
constructor equality with the component evidence. The default and buffered
UART/heartbeat/TracerV complete four-hart controls both pass at C=3,329,794.
All four full hart files match the uninterrupted reference byte-for-byte
(37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes); all decoded phase,
completion, failure and tohost labels match independently. This covers actual
active execution on all four cores through the late memory phase. These are
uninterrupted controls; complete CPU checkpoint continuation and CPU RTL
replay remain pending. Workload SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The new CPU binary still rejects preflight at TSI (`widget/12`) and rejects
capture/restore without a durable capability, before run or output publication.
Those requests do not establish malformed CPU-image loader acceptance.

All 245 Python tests and eight preserved native checks pass in
`native-regressions/invocation-axtrckf_/summary.json`, guarding the iteration-93
archive before/after. Five independent retained audits pass: complete Rocket
inventory/readback, both full original controls, complete memory/policy replay,
clock-event replay and original archived bytes. The old control launcher was
not in its iteration-90 archive; `rocket-original-input-archives.json` selects
only exact original recorded hashes/snapshots from later archives. No native
path or audit rule is relaxed. A fresh ordinary Rocket VCS process again reads
all 318,637 diagnostic words before seven clocks advance. This is a storage
probe, not a workload image/replay. Failed initial audit/link diagnostics are
retained alongside passing checks. `native-input-archives.json` seals 8,814
original bindings; both internal and executable CLI audits pass.
`verification-commands.json` records the exact executable argv/relative cwd.

Executable native checks from the Chipyard root (all native build/runtime
shells independently source `vcs-env.sh` last):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
checkpoint_rocket_header=automations/checkpoint_loop/runs/m11-iteration87/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h
python -m tools.checkpoint_formats.tests.verify_tracerv_checkpoint_vcs --rocket-header "$checkpoint_rocket_header" --out automations/checkpoint_loop/runs/m11-iteration94/tracerv-recheck
python -m tools.checkpoint_formats.tests.verify_tracerv_checkpoint_vcs --audit automations/checkpoint_loop/runs/m11-iteration94/tracerv-native/invocation-ou6pxbr8/summary.json
python -m tools.checkpoint_formats.tests.verify_tracerv_invalid_vcs --summary automations/checkpoint_loop/runs/m11-iteration94/tracerv-native/invocation-ou6pxbr8/summary.json --out automations/checkpoint_loop/runs/m11-iteration94/tracerv-invalid-recheck
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs --out automations/checkpoint_loop/runs/m11-iteration94/rocket-controls-recheck --seed-build automations/checkpoint_loop/runs/m11-iteration94/rocket-controls/invocation-s3q7sujf/build --workload automations/checkpoint_loop/runs/m11-iteration82/workload --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration94/rocket-controls/invocation-s3q7sujf/summary.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration94/native-regressions/invocation-axtrckf_/summary.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration94/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration94/protected-inputs.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration90/rocket-controls/invocation-6f3ulwfs/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration94/rocket-original-input-archives.json
```

Acceptance remains **in_progress**: complete run-loop/TSI/FESVR and remaining
runtime owners, bind all semantic owners through actual FAME metasim with
coherent clock events, then fresh complete Level-1 continuation and independent
Level-2 readback/captured CPU trace replay at early, warmed-cache,
outstanding-memory and late cuts. No required CPU checkpoint cut has passed.
BOOM/Saturn remain pending; standalone Shuttle/physical FPGA/ASIC work is
excluded. Existing iteration-93 commits FireSim
`e3b78c81021ac14a5db17e33725a1ebe477377af`, then Chipyard
`30b335fba5a8f3f8c59981ba8851635dc17e12bf`, were published and remote tips
confirmed in `publication.json`. No staging or local commits; plans are intact.

## Iteration 93: retain native evidence across verification reruns

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration93/`.

The iteration-92 controller verification failed because its fixed-path regression
launcher overwrote archived `regression-{0,5,6,7}.log` files when rerun. The audit
correctly rejected the changed bytes. Exact original logs have been recovered
from their original content-addressed snapshots. Displaced verifier output and
both hashes remain in `retained-log-recovery.json`; no audit rule was relaxed.
Use the maintained `tools.checkpoint_formats.native_regressions` module for new
checks. Historical launchers and their selected invocations remain preserved.

Every maintained invocation receives fresh build, simulation, log and result
directories. All generated RTL, images, traces, readback, binaries and native
logs are sealed in a complete file catalog. Prior native evidence is audited
before and after execution. Original local checker/compiler sources are copied
to content-addressed snapshots and must remain unchanged during the run; later
source evolution uses the exact original snapshot. Failed commands and failed
evidence guards retain diagnostics and cannot publish a passing result. Five
new tests pass, including actual processes that overwrite retained logs or
change source files, and changed/missing/extra artifact rejection.

Both full native eight-check suites actually pass:

| Selected original invocation | Python tests | Sealed files excluding summary | Original source bindings |
| --- | ---: | ---: | ---: |
| `native-regressions/invocation-7e9aw5m8/summary.json` | 243 | 4,415 | Original iteration-92 archive guard |
| `native-regressions/invocation-gk0gj8s_/summary.json` | 245 | 5,086 | 672 |

The second full suite additionally guards all 4,416 original first-invocation
bindings. Both runs preserve full M2/M3 metasim/ordinary RTL replay, 52 widget,
18 UART, 30 blockdev and 96 heartbeat continuations, their native rejection and
corruption cases, and eight FCFS Make/four generator guards. Separate source,
captured state, complete readback and native continuation artifacts remain
inside each selected invocation. Both catalogs and original controller archives
re-audit after the rerun. `first-native-archives.json` binds the original first
suite; `native-input-archives.json` binds the final selected evidence and source
snapshots. `verification-commands.json` records exact argv and relative cwd.

Six retained audits also pass: complete Rocket storage/clock/readback, original
controller archives, both full four-hart controls, complete memory/policy replay
and the 172-sample clock-event capture/replay (2,064 stored words / 1,720 outputs).
A new fresh ordinary RTL VCS process reads and deposits all 318,637 Rocket
diagnostic words before any of seven clocks advances; its log is under
`native-rocket-probe-*/run.log`. This uses the exact retained recipe's pre-FAME
RTL and pinned Y-2026.03-SP1 runtime. It is a storage probe. No CPU workload cut,
checkpoint continuation or captured CPU boundary replay is claimed. Original
four-hart workload SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Executable checks from the Chipyard root (the module also sources both repository
environments and `vcs-env.sh` last in every native build/run shell):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh
checkpoint_rocket_header=automations/checkpoint_loop/runs/m11-iteration87/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h
checkpoint_fcfs_inventory=automations/checkpoint_loop/runs/m3-metasim/f2/f2-fasedtests-AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config/checkpoint-native
python -m tools.checkpoint_formats.native_regressions --out automations/checkpoint_loop/runs/m11-iteration93/native-regressions --rocket-header "$checkpoint_rocket_header" --production "$checkpoint_fcfs_inventory" --guard automations/checkpoint_loop/runs/m11-iteration92/native-input-archives.json automations/checkpoint_loop/runs/m11-iteration92/protected-inputs.json --guard automations/checkpoint_loop/runs/m11-iteration93/first-native-archives.json automations/checkpoint_loop/runs/m11-iteration93/protected-inputs.json
python -m tools.checkpoint_formats.native_regressions --audit automations/checkpoint_loop/runs/m11-iteration93/native-regressions/invocation-gk0gj8s_/summary.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration93/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration93/protected-inputs.json
python -m tools.checkpoint_formats.tests.audit_multiclock_replay --summary automations/checkpoint_loop/runs/m11-iteration92/multiclock-replay-current/invocation-pub5jaqh/summary.json
```

The exact new Rocket diagnostic VCS command is recorded in
`verification-commands.json`; the full native build/probe commands remain in the
iteration-91 inventory summary. Recipe settings are freshly re-read in
`recipe.json`. Acceptance remains in progress: bind semantic owners through
actual FAME metasim/coherent clock events, complete CPU host/runtime owners,
then fresh Level-1 CPU continuation and independent Level-2 CPU readback/trace
replay at early, warmed-cache, outstanding-memory and late cuts. BOOM/Saturn
remain pending. No external dependency is missing; FPGA/ASIC work is deferred.
Existing iteration-92 commits FireSim
`0cba18f411f8fc98f74145f67b5854a546586553` and Chipyard
`1c55ffeb7c34b2f7bae6fd44b33a38a873e5a07d` were published in that order and
independently confirmed in `publication.json`. Plans, environments, index and
local HEADs remain preserved; no staging or local commits were performed.

## Iteration 92: clock-event images and fresh ordinary RTL replay

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration92/`.

Added an independent Level-2 version-2 payload for schema-3 inventories. Images
bind every boundary clock's settled level and completed rising-edge count, an
absolute event index and an explicitly selected cycle clock. Only all-low cuts
are supported. Traces capture every upcoming full clock vector, including
falling and simultaneous rising/falling transitions. Cycle labels count actual
completed rises of the selected clock; they can repeat across events. Inputs
settle and all outputs (including forwarded clocks) compare before the full
clock vector advances together. Both artifacts validate before loader files
are published; native restore/readback completes before any edge. Legacy
single-clock formats, StateIDs and Level-1 ownership remain independent.

Native evidence is **an ordinary RTL component capture**, not a Rocket workload
or metasim capture. The original compiler-emitted seven-clock component owns
seven counters, four RAM words and its synchronous read-data register: nine
entries / twelve words. Its 192 actual source events exercise every domain,
120 simultaneous-rise events, 24 mixed-rise/fall events and 137 events without
a cycle-clock rise. Independent source recurrence checks every stored word.
Source workload bench SHA256:
`e55ae29ea3e73b3ebd892c8315301ed7c12d8ca11b0c159023a43d173a799006`.
The source exits before fresh restore processes start. Component cuts are:

| Event index | Completed cycle-clock rises | Compared event samples |
| ---: | ---: | ---: |
| 0 | 0 | 48 |
| 12 | 3 | 48 |
| 80 | 23 | 48 |
| 164 | 47 | 28 |

The independent native waveform audit verifies every word before edges and at
all 172 continuation samples: 2,064 state comparisons and 1,720 output
comparisons. Direct continuous probes expose RAM words omitted by VCS's default
waveform dump. Two actual post-readback corruptions (`s0`, `ram_r_data`) fail at
event 80 / C=23, first reporting `crossing` and `readData`, respectively, with
zero acknowledged events. Seven invalid images (truncation, checksum, build,
missing/unknown owner, missing clock, missing output) reject without publishing
loader files. Four native loader requests (missing, duplicate, unknown,
wrong-width word) reject without depositing state and read back the complete
initial baseline with zero edges. Evidence includes thirteen fresh simulator
processes plus five builds, exact argv, snapshots, images, traces, logs and VCS
waveforms. Original final evidence is
`multiclock-replay-current/invocation-pub5jaqh/summary.json` and
`multiclock-replay-current-independent-audit.json`. Initial invocations and an
audit output-count correction remain retained.

All 240 final Python tests and eight preserved regression checks pass, including
M2/M3 metasim/ordinary RTL, 52 widget, 18 UART, 30 blockdev and 96 heartbeat
continuations and FCFS Make/generator guards. Results are in
`python-final.log` and `regression-results.json`. Four retained evidence audits
pass in `retained-audit-results.json`: complete Rocket inventory/readback,
controller-aware archives, both original full four-hart controls and complete
memory/policy evidence. Exact Rocket settings are re-read in `recipe.json`;
no new CPU workload run is claimed. Original four-hart workload SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Executable native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_multiclock_replay_vcs --base automations/checkpoint_loop/runs/m11-iteration91/scala-retained-artifacts/semantic-multiclock --out automations/checkpoint_loop/runs/m11-iteration92/multiclock-replay-recheck
python -m tools.checkpoint_formats.tests.audit_multiclock_replay --summary automations/checkpoint_loop/runs/m11-iteration92/multiclock-replay-current/invocation-pub5jaqh/summary.json
python -m unittest discover -s tools/checkpoint_formats/tests -v
# Use the maintained invocation-preserving suite in iteration 93 above.
```

Rocket acceptance remains in progress: bind original owners through the actual
metasim, capture coherent events at real four-hart workload cuts, finish
run-loop/TSI/FESVR/TracerV and other runtime owners, then demonstrate fresh
Level-1 continuation and independent complete Level-2 CPU replay at early,
warmed-cache, outstanding-memory and late cuts. This component contract cannot
authorize a CPU checkpoint profile. No external dependency is missing. The
iteration-91 controller commits FireSim
`fde729a95721c4e5d0dd3dd00368600ea4cd9a7c` and Chipyard
`d13fca04982c1d9f311daa9ab6a096c4f927882d` were published in that order;
`publication.json` confirms both remote tips. Local tracking refs are read-only.
No staging or local commits were performed.

## Iteration 91: complete Rocket clean storage and explicit clock ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration91/`.

The exact recipe now elaborates with discovery-only
`--semantic-multiclock-inventory`, independently of Level-1. Schema 3 lists all
seven boundary clock inputs, every state clock and six output clocks' proven
sources. It does not infer clock periods or authorize a multi-clock checkpoint.
High-level image encoding/decoding rejects until event phases and a coherent cut
are bound; multi-clock banked access also rejects. Legacy schemas 1/2 and
semantic StateIDs remain unchanged. Native VCS commands source both environments
and `vcs-env.sh` last; no FPGA bitstream build runs.

The clean emitter now preserves all original storage, including constant-driven
registers. A separate `.semantic-clean-access.json` binds original StateIDs to
the actual emitter's storage paths, its clean-source SHA256 and manifest SHA256.
It records register, memory and memory-pipeline keyword renames and each required
instance path segment. Stateless unused instances can disappear without deleting
storage owners. Compiler-internal emission state supplies these names; paths are
not guessed from keyword spellings. Independent RTL parsing audits all register
and array declarations, parameterized initialized owners, boundary widths,
sequential blocks and clock connections. Complete ChipTop ownership is:

| Owner clock / initialization | Entries | Words |
| --- | ---: | ---: |
| `clock_mbus_0` | 255 | 65,787 |
| `clock_sbus_rockettile_0` | 1,435 | 43,895 |
| `clock_sbus_rockettile_1` | 1,435 | 43,895 |
| `clock_sbus_rockettile_2` | 1,435 | 43,895 |
| `clock_sbus_rockettile_3` | 1,435 | 43,895 |
| `clock_uncore` | 2,321 | 76,942 |
| `serial_tl_0_clock_in` | 322 | 322 |
| Exact initialized external values | 6 | 6 |
| Total | 8,644 | 318,637 |

`rocket-semantic-retained-inventory/` retains the exact-recipe command, original
FIRRTL/reference, emitted manifest, clean access map, clean RTL and boundary.
The full ordinary RTL VCS build and six fresh native probes are retained at
`rocket-native-complete-inventory/invocation-yfr_nr9p/summary.json`.
Every probe reads all 318,637 original words before any edge. The valid probe
deposits deterministic diagnostic patterns and reads back every word, with all
seven clocks low. Four invalid loader requests (missing word, duplicate word,
unknown word, wrong width) reject without any deposit and preserve complete
baseline readback. Actual post-deposit corruption is detected by native readback.
`rocket-native-independent-audit.json` independently rechecks source/archive
hashes, complete storage/clock ownership, every pattern row, exact build/run argv,
native logs and all six fresh processes. **These are storage probes, with no CPU
workload cut, captured checkpoint, boundary trace, or continuation claim.**

The two final seven-clock component probes also pass, including a constant-driven
register, renamed nested instance and renamed memory pipeline: 12 and 13 words,
six fresh processes each. `selected-multiclock-fixtures.json` selects their exact
summaries and independent audits. All 22 Scala inventory tests and 235 final
Python tests pass. All eight preserved regression checks pass. Original memory,
initialized-owner waveform and full four-hart workload/control evidence is
retained and independently re-audited, using immutable source snapshots when
implementation sources have since changed.
The full current forwarded-clock native regression also passes (22 words / 108
samples). Both complete current memory suites and their independent audit pass:
37 metasim-captured words / 149 continuation samples, all five ordinary memory
policies / 245 samples, and 37 fresh native processes. Their current summaries
are `forwarded-native/summary.json`, `memory-native/summary.json` and
`memory-policy-native/summary.json`; `independent-memory-audit.json` binds the
original current images, logs and comparisons.

The previous verification incorrectly required `.git/index` and local HEADs to
remain identical after the loop controller created its checkpoint. The durable
audit now checks permitted controller ancestry, unchanged plan/environment bytes,
all 1,321 original archive bindings and original runtime evidence. Evolving
source bytes must match their recorded snapshot and controller commit; binaries,
generated artifacts, traces and logs cannot use that fallback. Index/HEAD
preservation is checked during this implementation turn and recorded separately.
The original failed verifier and all intermediate emission diagnostics remain
retained. Existing iteration 90 commits were published FireSim first
(`cc5681b967ead61edb31a13757586a117188c195`), then Chipyard
(`ab558a7d34eefd4262e0d4d0e11d94effe563c40`); remote tips were independently
confirmed. Local tracking-reference updates are read-only. No local staging or
commits were performed.

Executable native discovery probes (each writes a new invocation directory):

```sh
source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh && python -m tools.checkpoint_formats.tests.verify_multiclock_inventory_vcs --base automations/checkpoint_loop/runs/m11-iteration91/rocket-semantic-retained-inventory/FireSim-generated --out automations/checkpoint_loop/runs/m11-iteration91/rocket-native-recheck
python -m tools.checkpoint_formats.tests.audit_multiclock_inventory --summary automations/checkpoint_loop/runs/m11-iteration91/rocket-native-complete-inventory/invocation-yfr_nr9p/summary.json
python -m tools.checkpoint_formats.retained_evidence --archive automations/checkpoint_loop/runs/m11-iteration90/native-input-archives.json --protected automations/checkpoint_loop/runs/m11-iteration90/protected-inputs.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls --summary automations/checkpoint_loop/runs/m11-iteration90/rocket-controls/invocation-6f3ulwfs/summary.json --source-archive automations/checkpoint_loop/runs/m11-iteration90/native-input-archives.json
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration91/run-regressions.py
```

CPU acceptance is still in progress. Next: preserve/bind original semantic
owners through the actual generated simulator, capture coherent clock events
and CPU state during real four-hart execution, and complete runtime run-loop,
TSI/FESVR/TracerV ownership. Required early, warmed-cache, outstanding-memory and
late CPU checkpoint cuts, fresh Level-1 continuation, and independent Level-2
image readback/captured-trace replay remain untested. No external dependency is
missing. BOOM and Shuttle + Saturn remain pending; physical FPGA/ASIC work is
deferred.

## Iteration 90: initialized external state and parent clock pins

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration90/`.

Pre-FAME inventory now owns each exact non-SYNTHESIS `plusarg_reader.myplus`
register. These values initialize from runtime arguments; the compiler never
substitutes `DEFAULT` for checkpoint state. Version-2 semantic manifests bind
every reachable external instance, specialized width/default/format and the
exact inline source SHA256. Their initialized registers have `clock_domain`
`initial`, separate from the selected target clock. Ordinary version-1
manifests and Level-1 state identities remain unchanged. Missing, altered,
duplicated or wrong-circuit source annotations, unsupported parameters/ports
and all other opaque models reject before semantic publication. Clean RTL
retains the original parameterized implementation exactly once. The capture
oracle audits actual model bytes, parameters and complete storage declarations;
SYNTHESIS variants and lost/changed owners reject. This is VCS semantic
ownership, with no physical FPGA support claim for this simulation model.

Clock provenance also follows a concrete child's driven input pin back to its
parent net. Rocket's serial domain uses `serdesser.clock` this way. Types,
directions, drivers and dependency cycles are checked; an input pin cannot
turn data, a gate or an undriven net into a target clock. All 19 final Scala
inventory tests pass, including exact external-source negatives and actual
emitted input-clock fanout. All 225 final Python tests pass.

The native ordinary RTL component checks consume the actual compiler-emitted
circuits. Both default and nondefault initialized values are captured, including
nested repeated instances and widths 1, 32 and 65. Source processes exit before
fresh restore processes start with conflicting plusargs. Each fixture restores
and reads back all five words before any edge at component C=0/3/9/16, then
compares 80 samples and all five outputs at their original labels. The second
fixture clocks its counter through the child's driven input pin. These are
component cuts, not Rocket workload cuts or vector workloads. Original results:

| Component | Original native summary | Independent original-artifact audit |
| --- | --- | --- |
| Initialized values | `semantic-plusarg-waveform-native/invocation-x0nujzuh/summary.json` | `semantic-plusarg-waveform-native-independent-audit.json` |
| Parent input-clock fanout plus initialized values | `semantic-clock-pin-waveform-native/invocation-a8tf_532/summary.json` | `semantic-clock-pin-waveform-native-independent-audit.json` |

Each audit verifies actual source state and recurrence, exact image membership,
all zero-edge guards, actual complete native waveform readback and per-cycle
input/output comparisons, finite captured traces, conflicting fresh initialization,
native build/run logs and 26 distinct native processes. Each fixture has eight
actual post-readback stored-value corruptions: their corresponding output first
diverges at C=9 and no edge is acknowledged. Ten malformed/incompatible/missing/
unknown-owner images and eight actual native loader requests reject before
partial restore. Across both fixtures this is 160 samples / 800 output
comparisons, sixteen corruption cases, twenty image rejections and sixteen
native loader rejections. Archived original inputs and their hashes are bound
in each summary; native argv/PIDs/exits are in the actual build/run logs.

Exact-recipe Rocket discovery now visits its six initialized external owners
and rejects seven distinct state clock domains: `clock_mbus_0`,
`clock_sbus_rockettile_0` through `_3`, `clock_uncore` and
`serial_tl_0_clock_in`, all under `FireSim.chiptop0`. No partial semantic
artifacts are emitted. The original IR, recipe record, compiler argv and input
hashes are in `rocket-semantic-verified-inventory/summary.json`.
`rocket-initialized-owner-audit.json` independently binds all six original
opaque instances to exact source bytes and parameters. Its 1,488 instances,
7,734 explicit registers, 500 memories / 310,493 logical words, 404 implicit
memory-pipeline owners and six initialized values suggest 318,637 semantic
words. This total remains a raw diagnostic, not a complete semantic manifest.
Independent multi-clock event capture, complete readback and replay are pending.

Initial diagnostics are retained: an oversized 65-bit test argument was corrected
without reducing widths or cases; a fanout test moved its instance declaration
before its first reference; a concurrent VCS build collided in its timestamp/PID
temporary directory. The corrected verifier gives each invocation its own
temporary root. The native replay test explicitly flushes the settled waveform
before comparisons so a failing DPI exit retains the first divergent values.
Expected-rejection discovery retries retain each original
compiler diagnostic. Memory audits also retain a cross-tool PID-namespace
collision diagnostic; the full corrected memory checks run in one shell.

Executable native checks from the Chipyard root (same pinned VCS release,
`-full64`, GCC/G++ 13, no FPGA build):

```sh
source env.sh && source sims/firesim/env.sh
export JAVA_TOOL_OPTIONS="-Xmx8G -Xss8M"
export CHECKPOINT_TEST_ARTIFACT_DIR="$PWD/automations/checkpoint_loop/runs/m11-iteration90/scala-reproduction-artifacts"
source automations/checkpoint_loop/vcs-env.sh
make -C sims/firesim/sim testOnly FIRESIM_SBT_PROJECT=midas SCALA_TEST=midas.checkpoint.SemanticStateInventorySpec
python -m tools.checkpoint_formats.tests.verify_semantic_plusarg_vcs \
  --scala-artifacts "$CHECKPOINT_TEST_ARTIFACT_DIR" \
  --out automations/checkpoint_loop/runs/m11-iteration90/initialized-reproduction
python -m tools.checkpoint_formats.tests.verify_semantic_plusarg_vcs --clock-pin \
  --scala-artifacts "$CHECKPOINT_TEST_ARTIFACT_DIR" \
  --out automations/checkpoint_loop/runs/m11-iteration90/clock-pin-reproduction
python -m tools.checkpoint_formats.tests.audit_semantic_plusarg \
  --summary automations/checkpoint_loop/runs/m11-iteration90/semantic-plusarg-waveform-native/invocation-x0nujzuh/summary.json
python -m tools.checkpoint_formats.tests.audit_semantic_plusarg \
  --summary automations/checkpoint_loop/runs/m11-iteration90/semantic-clock-pin-waveform-native/invocation-a8tf_532/summary.json
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration90/discover-rocket-verified.py
python automations/checkpoint_loop/runs/m11-iteration90/audit-rocket-initialized-state.py
```

Both full exact-recipe default/buffered four-hart controls pass at C=3,329,794.
All four complete hart traces and independently decoded workload/store labels
match the uninterrupted reference. The original invocation is
`rocket-controls/invocation-6f3ulwfs/summary.json`; its independent audit is
`rocket-controls-independent-audit.json`. Native source binding retains 297
inputs / 58 translation units and 445,838 generated state words. Workload
SHA256 is `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Fresh current native CPU preflight/save/restore requests reject incomplete
runtime support before execution and publish no partial checkpoint. These
controls and unsupported requests do not establish CPU continuation. All eight
preserved native regression checks, the full forwarded-clock native checks,
the full metasim memory checks and all five ordinary memory-policy checks pass.
`independent-memory-final-audit.json` verifies the original complete memory
images and 37 distinct native processes. Final original scope, native argv,
source snapshots and all created files are bound by `summary.json`,
`verification-commands.json`, `executed-initialized-native-commands.json`,
`native-input-archives.json` and `artifact-manifest.json`.

Additional exact-recipe controls and retained regression reproduction commands:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration90/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration87/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls \
  --summary automations/checkpoint_loop/runs/m11-iteration90/rocket-controls/invocation-6f3ulwfs/summary.json
python -m tools.checkpoint_formats.tests.audit_semantic_memory \
  --metasim-summary automations/checkpoint_loop/runs/m11-iteration90/memory-verified-regression/summary.json \
  --policies-summary automations/checkpoint_loop/runs/m11-iteration90/ordinary-memory-policies-complete/summary.json
```

Complete CPU runtime ownership and fresh Level-1 continuation remain pending.
The Level-2 CPU boundary still needs seven-clock event scheduling and independent
active-workload capture/readback/replay, plus CPU image and corruption checks.
Required early, warmed-cache, outstanding-memory and late CPU checkpoint cuts
have not passed. BOOM and Shuttle + Saturn remain pending; physical FPGA and
ASIC work stay deferred. No required external dependency is missing.

## Iteration 89: synchronous and readwrite memory ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration89/`.

The pre-FAME inventory now owns one-cycle FIRRTL passthrough memory storage,
including the exact stored address for write-first/undefined readers, stored
data for read-first readers, and stored read data for read-first/undefined
readwriters. Each is a distinct semantic register, with its port field's actual
width, lowered name, reset semantics and resolved target clock, alongside every
logical array word. Clean RTL emission preserves the same passthrough layout.
Longer/readwrite-asynchronous/write-first-readwrite pipelines, unrelated port
clocks and colliding owner paths reject before semantic publication. All 15
Scala inventory tests pass, including emitted-layout and collision checks.
No CPU runtime profile or new checkpoint schema is enabled.

`memory-complete-native/summary.json` records actual VCS metasim capture from
the self-checking `MemoryPipelineFixture`, then eight fresh ordinary RTL VCS
restores at fixture C=0/5/13/21/24/26/28/30. All 37 words / nine semantic entries
are read back before any edge; all 149 continuation samples compare all five
outputs at their original labels. An independent recurrence checks every word
and output across all 37 captured edges, including enabled/disabled reads,
same-address collisions, and held data differing from address-selected contents.
These are component cuts, not Rocket CPU cuts. Five actual malformed/build/
missing-pipeline/unknown-owner images and four native loader cases reject without
partial publication/deposit. Four actual stored-pipeline corruptions first fail
at fixture C=21 on their corresponding output, acknowledging zero edges.

`ordinary-memory-policies-complete/summary.json` separately consumes actual
Scala-emitted circuits for all five supported reader/readwriter policies,
including a non-power-of-two RAM. Twenty fresh ordinary RTL continuations
restore all six words per circuit at C=0/5/10/16 and compare 245 samples. Five
actual pipeline corruptions fail `result` at C=10 before acknowledging an edge.
`independent-memory-audit.json` checks original images, complete native readback
benches, captured traces, pinned-release logs and 37 distinct fresh process IDs.

An initial undefined-reader metasim fixture correctly rejected changed ownership:
Golden Gate resolves its undefined policy to read-first and stores data, whereas
the earlier semantic reference stores an address. Both layouts have independent
ordinary RTL tests; no conversion between them is claimed. The passing metasim
fixture uses defined reader policies and both supported readwriter policies.
The initial ownership diagnostic, incorrect readwriter hold expectation and
missing ordinary-VCS initreg compile switch, plus their full corrected native
runs, are retained. The test expectation now follows the actual emitter, which
captures old readwriter data on enabled write edges too.

Exact Rocket ChipTop discovery now passes the synchronous/readwrite memories
and rejects `opaque external module plusarg_reader`, with no partial semantic
outputs. Its exact-recipe compiler argv, input hashes, original pre-FAME IR and
rejection are under `rocket-semantic-final-inventory/`. A separate complete raw
hierarchy diagnostic still finds 1,488 instances, 7,734 explicit registers,
500 memories / 310,493 logical words and six opaque instances. All 404
synchronous memories are undefined-policy readwriters with 404 additional
candidate stored-read-data owners; the other 96 memories are asynchronous
readers. These declaration counts are diagnostics, not a complete semantic
manifest. Multi-clock event capture/readback/replay remains pending.

Executable checks from the Chipyard root, using VCS Y-2026.03-SP1, `-full64`,
system GCC/G++ 13 and no FPGA build:

```sh
source env.sh && source sims/firesim/env.sh
export JAVA_TOOL_OPTIONS="-Xmx8G -Xss8M"
export CHECKPOINT_TEST_ARTIFACT_DIR="$PWD/automations/checkpoint_loop/runs/m11-iteration89/scala-final-artifacts"
source automations/checkpoint_loop/vcs-env.sh
make -C sims/firesim/sim testOnly FIRESIM_SBT_PROJECT=midas SCALA_TEST=midas.checkpoint.SemanticStateInventorySpec
python -m tools.checkpoint_formats.tests.verify_semantic_memory_vcs \
  --build automations/checkpoint_loop/runs/m11-iteration89/memory-defined-build \
  --out automations/checkpoint_loop/runs/m11-iteration89/memory-reproduction-native
python -m tools.checkpoint_formats.tests.verify_semantic_memory_policies_vcs \
  --scala-artifacts automations/checkpoint_loop/runs/m11-iteration89/scala-final-artifacts \
  --out automations/checkpoint_loop/runs/m11-iteration89/ordinary-memory-reproduction
python -m tools.checkpoint_formats.tests.audit_semantic_memory \
  --metasim-summary automations/checkpoint_loop/runs/m11-iteration89/memory-complete-native/summary.json \
  --policies-summary automations/checkpoint_loop/runs/m11-iteration89/ordinary-memory-policies-complete/summary.json
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration89/discover-rocket-semantic.py
```

Both full exact-recipe native default/buffered four-hart controls pass at
C=3,329,794. Every complete hart trace and decoded workload/store label matches
the uninterrupted reference. The retained run is
`rocket-controls/invocation-t0bmlj86/summary.json`, with 297 bound native inputs /
58 translation units. Workload SHA256 is
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
All 221 final Python tests, eight preserved native regression checks and the
full five-cut forwarded-clock native regression pass. Fresh current CPU
preflight/save/restore requests reject incomplete ownership before execution.
These controls/rejections do not establish CPU continuation. Reproduce into a
new retained invocation, then audit the selected original evidence:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration89/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration87/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls \
  --summary automations/checkpoint_loop/runs/m11-iteration89/rocket-controls/invocation-t0bmlj86/summary.json
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration89/verify-evidence.py
```

The existing controller commits were published FireSim first
(`a8d3ed98c000f2fa46ce31b5c12b3c2bc9ce878b`), then Chipyard
(`b0fb1ef48f5f8949c4c40f9187e28e8f453c77c3`), with independently confirmed
remote tips. Local remote-tracking updates hit read-only metadata. No local
staging or commits. Protected plans, environments, indexes and heads remain
unchanged during this turn. `summary.json`, `selected-evidence.json`,
`native-input-archives.json`, `executed-native-commands.json` and
`verification-commands.json` retain the final scope, source bindings and exact
native argv; the report references concrete files listed in
`artifact-manifest.json`.

The loop's iteration-88 artifact complaint came from listing a directory where
its report validator requires a nonempty file. The iteration-89 report names
concrete summary/manifest files; `artifact-manifest.json` enumerates all retained
files. The diagnostic directory itself is not a report artifact.

Complete CPU Level-1 runtime ownership/fresh continuation and independent
Level-2 opaque owners, multi-clock events, active-workload capture/readback/replay
and CPU image/corruption cases remain pending. Physical FPGA and ASIC work
remain deferred. No required external dependency is missing.

## Iteration 88: semantic clock provenance

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration88/`.

Pre-FAME discovery now follows clock outputs through concrete nested and sibling
instances. Dependency keys distinguish a parent instance pin from its child's
port, and input dependencies resolve lazily. Clock provenance also follows
exact one-bit `asUInt`/`asClock` casts and one-bit `bits(..., 0, 0)` identities
through transparent IO cells. It never follows a register's next-state driver,
invents a clock from a data input, or assumes all Rocket clocks share a domain.
Generated/gated/undriven/cyclic clocks, opaque cells, distinct state clock
domains and forwarded clocks outside the state domain still reject. Existing
manifest and boundary schemas and the CPU runtime whitelist are unchanged.

All 13 Scala inventory tests pass. The new
`ForwardedClockInventoryFixture` passes native VCS metasim capture and five
fresh ordinary RTL VCS restores/replays at actual fixture cuts C=0, 5, 22, 24
and 26. Each restores and reads back all 22 words / 15 semantic entries before
any edge. All 108 captured continuation samples compare all 13 outputs at
their original labels. Native capture observes 37 actual DUT edges; the clock
bridge reports 38, and the independent counter/input checks preserve that
distinction. These are fixture checks, not Rocket checkpoint cuts.

Five actual fixture images with truncation, checksum corruption, an incompatible
build and missing/unknown state owners reject before publishing `restore.txt`
or `replay.sv`. Four native loader cases reject missing handles, wrong widths,
malformed rows and incomplete word sets before any deposit. After complete
zero-edge readback, actual stored `a.saved` corruption first diverges on
`io_left` at fixture C=26; the native process exits nonzero and acknowledges
zero edges. The existing valid trace corruption case still first diverges on
`io_respData` at C=29. Exact artifacts are in `forwarded-verified-native/`,
including each `.rtlckpt`, `.trace`, readback/replay bench, native executable,
build/run log and waveform.

Reproduce from the Chipyard root with the pinned native VCS environment:

```sh
source env.sh && source sims/firesim/env.sh
export JAVA_TOOL_OPTIONS="-Xmx8G -Xss8M"
source automations/checkpoint_loop/vcs-env.sh
make -C sims/firesim/sim testOnly FIRESIM_SBT_PROJECT=midas SCALA_TEST=midas.checkpoint.SemanticStateInventorySpec
python -m tools.checkpoint_formats.tests.verify_semantic_vcs \
  --forwarded-clocks \
  --build automations/checkpoint_loop/runs/m11-iteration88/forwarded-bitcast-build \
  --out automations/checkpoint_loop/runs/m11-iteration88/forwarded-verified-native
```

Exact-recipe complete ChipTop discovery now reaches and explicitly rejects
`FireSim.chiptop0.system.coh_wrapper.l2.inclusive_cache_bank_sched.directory.cc_dir_0`
with `read=1, write=1` and a readwrite port. No partial semantic artifacts are
published. Retain its actual pre-FAME FIRRTL, annotations, recipe settings,
compiler command, source hashes and rejection under
`rocket-semantic-final-inventory/`. Clock alias support does not establish
complete memory-pipeline ownership or multi-clock replay. Reproduce discovery:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration88/verify-rocket-semantic-final-rejection.py
```

`rocket-semantic-memory-obligations.json` separately traverses the selected
original IR hierarchy and checks every concrete raw register/memory
declaration. It records 1,488 instances, 7,734 raw registers and 500 logical
memories / 310,493 words; 404 memories require read/readwrite pipeline ownership.
It also identifies six opaque `plusarg_reader` instances whose ownership remains
pending. These totals exclude implicit pipeline/opaque state and are diagnostic,
not a semantic manifest or complete state audit. The executable diagnostic is
`PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration88/audit-semantic-memory-obligations.py`.

Both full exact-recipe default/buffered native VCS controls pass at
C=3,329,794, with all four complete hart traces and independently decoded
workload/store labels matching the uninterrupted reference. Workload SHA256
remains `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The retained invocation is `rocket-controls/invocation-8mdtqxuy/`; its native
build binds 297 inputs / 58 translation units. All six complete generated
source/header/inventory files match the previous exact recipe build. All
221 Python tests and eight preserved native regression checks pass, including
M2/M3 metasim/ordinary RTL, 52 widget, 18 UART, 30 blockdev and 96 heartbeat
continuations and the existing FCFS Make/generator guards. Native CPU
preflight/save/restore still reject incomplete runtime ownership before any
partial image is published. Reproduce the full controls into a new retained
invocation and independently audit the selected original run:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration88/rocket-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration87/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
python -m tools.checkpoint_formats.tests.audit_rocket_controls \
  --summary automations/checkpoint_loop/runs/m11-iteration88/rocket-controls/invocation-8mdtqxuy/summary.json
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration88/verify-evidence.py
```

`summary.json`, `selected-evidence.json`, `native-input-archives.json`,
`artifact-manifest.json`, `executed-native-commands.json` and
`verification-commands.json` retain exact scope and commands. The latter also
runs the selected ordinary RTL VCS executable in a fresh process, preserving
its original images, traces, binaries and waveforms. Regression commands/results
are under `regression-complete/`. Controller checkpoints FireSim
`aa143ccc404eb97faff3a23249e2d38027a6d969` and Chipyard
`c9b10d3634173bdd010df5092efcdff81ad83381` were published in that order with
confirmed remote tips. Local remote-tracking ref updates hit read-only Git
metadata; the remote pushes succeeded. No local staging or commits.

Complete CPU Level-1 runtime ownership/fresh continuation and independent
Level-2 synchronous-memory/readwrite pipelines, complete multi-clock inventory,
capture/readback/replay, all required active-workload cuts and CPU image/fault
cases remain pending. No external dependency is missing. Physical FPGA and
ASIC work remain deferred.

## Iteration 87: reproducible exact-recipe native controls

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration87/`.

The previous loop verification failed before running either control. Its Make
call reused the existing executable and replaced `rocket-vcs-build.log` with
an up-to-date-build log containing no VCS command. The subsequent native build
recorder correctly rejected that log. The failed log is retained as
`previous-verification.log`; `actual-noop-build-rejection.json` records its
rejection by the maintained native invocation validator.

`VCS_FORCE_REBUILD=1` now adds a phony prerequisite at both the outer FireSim
Make target and the recursive native VCS target. `cpu_recipe.native_build_command`
requests this explicitly for VCS checks. It retains `-full64`, `-Mupdate` and
all exact recipe settings above. It changes no source timestamps and forces
the native invocation without forcing target elaboration. Ordinary builds
retain their existing caching behavior. A real two-layer Make regression with
a mock compiler proves repeated forced rebuilds and unchanged-source caching;
this mock test is explicitly separate from licensed native VCS evidence.

The maintained launcher is
`tools/checkpoint_formats/tests/verify_rocket_controls_vcs.py`. Each invocation
gets its own build directory, executable, logs, actual process IDs, commands,
full 16-GiB controls and complete four-hart traces. `cpu_native.py` binds 297
native inputs and 58 host translation units, including actual compiler `.d`
dependencies, generated RTL/inventory, the static FESVR archive, compiler
executables, VCS executable and linked shared libraries. Successful Make logs
must contain exactly one executed VCS command for the selected executable.
No-op, failed, ambiguous, wrong-release, wrong-mode and wrong-output logs
reject. No CPU checkpoint profile is enabled.

Both exact-recipe native builds and all five full four-hart controls pass at
target count 3,329,794: two independently rebuilt default/buffered pairs and
the frequent-heartbeat control. Every full hart trace and independently decoded
phase/completion/failure/HTIF store label matches the uninterrupted reference.
The frequent control retains 202 actual clock samples from C=16,459 through
3,322,351. Workload ELF SHA256 is
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The independent maintained control audit passes. All 221 Python tests, full M2/M3 native VCS
metasim and ordinary RTL checks, 52 existing widget continuations, UART's 18,
blockdev's 30, heartbeat's 96 native/VCS continuations and eight FCFS Make/four
generator guards have passed. Earlier iteration-84/85 evidence passes with
its original `cpu_recipe.py` bound to an archived snapshot and pinned Git
object. It remains historical evidence.

Reproduce both complete controls from the Chipyard root. Repeated invocations
retain earlier build and runtime artifacts:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_rocket_controls_vcs \
  --out automations/checkpoint_loop/runs/m11-iteration87/reusable-controls \
  --seed-build automations/checkpoint_loop/runs/m11-iteration87/build \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --reference-runtime automations/checkpoint_loop/runs/m11-iteration85/rocket-runtime \
  --reference-audit automations/checkpoint_loop/runs/m11-iteration85/rocket-workload-audit.json
```

The selected initial immutable invocation is
`reusable-controls/invocation-yq4cdng6/`. Its passing independent audit command is:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.audit_rocket_controls \
  --summary automations/checkpoint_loop/runs/m11-iteration87/reusable-controls/invocation-yq4cdng6/summary.json
```

This checks complete generated inventory, every native input, actual argv and
process completion, full instruction traces and independently decoded workload
phase/completion/failure/HTIF stores at their original CPU-print labels. These
labels are workload controls, not checkpoint-cut target-cycle evidence.
No early/warmed/outstanding/late CPU checkpoint cut has passed. Complete
runtime ownership, fresh-process Level-1 continuation and independent
multi-clock Level-2 capture, zero-edge readback and finite replay remain pending.

Fresh current-source ChipTop discovery still rejects
`FireSim.chiptop0.system.bdev_clock`, with no partial semantic outputs. Native
CPU preflight/save/restore still reject incomplete runtime ownership before
partial checkpoint publication. Required CPU malformed/incompatible/incomplete
image validation and actual semantic first-divergence corruption cases remain
pending. The new build-log rejection cases are infrastructure checks.

`summary.json`, `selected-evidence.json`, `native-input-archives.json` and
`artifact-manifest.json` retain the exact selected artifacts and all 594 native
input bindings with archived original bytes. The combined saved evidence check
uses the selected immutable invocation independently of later `latest.json`
updates. Reproduce the remaining complete native checks from the Chipyard root:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration87/run-rocket-polling-control.py
python automations/checkpoint_loop/runs/m11-iteration87/run-regressions.py
python -m automations.checkpoint_loop.runs.m11-iteration87.verify-evidence
```

Each nested VCS shell independently sources `vcs-env.sh` last. Existing
controller commits FireSim `06d8dd43b2162fdf943c255167404889d8afd95c` and then
Chipyard `bc3878be2bf298af6217dc7db1c2383c871cc70a` were published with confirmed
remote tips. Plans/environment inputs/indexes/heads are preserved; no local
staging/commits or required external dependency failure.

## Iteration 86: heartbeat host ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration86/`.

`firesim.widget.heartbeat.v1` supports completed, unpoisoned calls before
`finish()` with explicit `+heartbeat-checkpoint-buffered`. The payload owns
`trip_count`, `last_cycle`, sticky `has_timed_out`, the signed 64-bit start epoch
and every `(target count, signed elapsed seconds)` log sample. Configuration
binds `polling_interval`, `ignore_heartbeat` and the complete clock host
configuration: actual Rocket MMIO addresses 1088 through 1108. Generated
clock counters/latches and transport queues remain separate owners. A fresh
process may choose a new `+heartbeat-output` destination; construction and
restore leave its existing bytes untouched, and successful `finish()` publishes
the full log including the restored prefix. Default live-file mode rejects
checkpointing. Finished, suspended/reentrant and interrupted calls reject.
Parse, consistency checks and allocations precede all restore mutations.
The CPU profile/whitelist and independent Level-2 schemas remain unchanged.

`heartbeat-native/latest.json` selects `native-wshv6rpb/summary.json`.
Native ASan/UBSan and VCS DPI each pass 48 fresh continuations across all 16
cuts in three scenarios: interval two with termination enabled/ignored, and
interval zero polling every call. The independent oracle checks every state
byte before the first edge, full final state, every MMIO operation/termination
result at its original **fixture** boundary, and all published CSV bytes.
Cuts cover startup, pre-poll counts, 64-bit cycle progress, no-progress timeout,
sticky timeout and late samples. Test-only wall time also steps backwards;
the saved signed diagnostic timestamps survive independently of termination.
Production wall-clock timestamps remain diagnostic and may reflect restore
downtime; target behavior depends only on polling/observed cycle state.

Each backend passes 772 malformed/incompatible/incomplete/lifecycle assertions
without partial owner mutation or MMIO. Checks bind all clock addresses,
interval/partition settings and reject missing rows, bad counters/epochs/flags,
inconsistent timeout/history, live logs, reentrancy and interrupted operations.
Structurally valid actual polling-counter corruption first fails
`heartbeat_poll` at fixture C=107, operation 1; no cycle read, termination
result or next operation occurs. All positive readbacks/traces are re-audited
after negative cases. These are host component checks, not Rocket target-cycle
cuts, complete `.fsckpt` continuation or semantic CPU replay acceptance.

Run from the Chipyard root (new retained component directory per invocation):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_heartbeat_checkpoint_vcs \
  --rocket-header automations/checkpoint_loop/runs/m11-iteration85/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h \
  --out automations/checkpoint_loop/runs/m11-iteration86/heartbeat-native
```

The exact-recipe current native rebuild links the heartbeat adapter, binds 207
actual inputs and 58 host translation units, and uses the pinned native
VCS/GCC/G++ settings above. Full default/buffered four-hart controls pass at
target count 3,329,794, with all four complete traces and decoded phase,
completion, failure, retired-store and HTIF labels matching the previous
uninterrupted control. A third full run through `run-rocket-polling-control.py`
uses `+heartbeat-polling-interval=1024 +partitioned=1`, exercising real clock
MMIO with timeout checks disabled during boot stalls. It also passes at target
count 3,329,794 and captures 202 actual clock samples from C=16,459 through
3,322,351. Every full hart trace and decoded workload/store label matches the
same uninterrupted reference. Physical host timing differs; sampled target
labels remain identical. Workload ELF SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
The earlier controls retain the default interval 1,000,000 and correctly emit
header-only heartbeat logs for this workload. All 219 Python tests, full M2/M3 VCS metasim/ordinary RTL,
52 existing widget continuations, current UART/blockdev native/VCS component
checks and eight FCFS Make/four generator guards pass. All seven executable
checks/results are `regression-commands.json` / `regression-results.json`.
Historical iteration-84/85 evidence remains independently audited using
archived original heartbeat sources bound to exact pinned FireSim Git objects;
it does not substitute for current native source binding.
Fresh current-source ChipTop discovery still rejects `bdev_clock`, publishing
no partial semantic manifest/ordinary RTL. Rebuilt CPU preflight/save/restore
still reject incomplete runtime ownership without partial images.

The initial control wrapper incorrectly asserted a heartbeat sample at the
legacy interval. Both full native runs passed; the corrected complete audit
passes using the exact executed command metadata and archived launcher
`run-rocket-controls.initial.py`. Initial diagnostics remain in
`rocket-controls.log` and the passing re-audit is
`rocket-controls-audit-retry.log`. No native run was shortened or skipped.

Reproduce complete exact-recipe native VCS controls and the regression scope
from the Chipyard root (no FPGA build):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration86/run-rocket-controls.py
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration86/run-rocket-polling-control.py
python automations/checkpoint_loop/runs/m11-iteration86/run-regressions.py
```

Every nested VCS shell independently sources both environments and
`vcs-env.sh` last. `rocket-native-commands.json`, `rocket-polling-commands.json`
and the component `commands.json` retain executed argv, logs and results.
`selected-evidence.json` selects complete current artifacts;
`artifact-manifest.json` lists generated artifacts by full path and hash.
`summary.json` preserves both CPU levels as incomplete. Independently audit:

```sh
python -m automations.checkpoint_loop.runs.m11-iteration86.verify-evidence
```

The reusable check binds current native sources, generated declarations,
every component readback/transaction, complete CPU controls, preserved
regressions, explicit runtime/semantic rejection, historical source objects
and publication/protected-input/controller ancestry. Raw index/HEAD bytes
are separately checked only at implementation-turn end, preserving the loop
controller's next staging/commit. Existing controller commits were published
FireSim first (`4e564603726d151e0a0ad020b13259148297ad01`), then Chipyard
(`5577b7b9288d77512d093e45bf3ddcac50478d75`), with confirmed remote tips.
No new commits/staging, protected plan/environment edits or external dependency
failure. Complete CPU restore/replay and all required active cuts remain pending.
Complete run-loop, TSI/FESVR, TracerV and remaining owners, coherent CPU cuts,
fresh full Level-1 restores and independent multi-clock semantic CPU
capture/restore/finite replay remain pending.

## Iteration 85: UART ownership and reusable evidence

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration85/`.

`firesim.widget.uart.v1` supports completed, unpoisoned host calls before
`finish()` with explicit `+uart-checkpoint-file0`, `+uart-in0=<regular-file>`
and `+uart-out0=<destination>`. The constructor owns every input byte; the
image binds those bytes, the UART index and all six actual Rocket MMIO
addresses (1056 through 1076). It captures the entire input cursor, binary
output prefix, both data bytes and all four handshake flags. Active/poisoned
call state and finished lifecycle are rejected rather than omitted. Output
stays in owned memory until successful `finish()`, so construction, validation
and restore do not overwrite an existing destination. A fresh process may
select a new output destination but must supply the identical input bytes.
Default stdin/signals, PTYs and ordinary file descriptors explicitly reject
checkpointing. No CPU whitelist or semantic schema is extended.

`uart-native/latest.json` selects the retained component summary. Native
ASan/UBSan and VCS DPI each pass all nine cuts in independent processes,
including startup, binary input/output and EOF. An independent Python oracle
compares every state byte before the first edge, full final readback, every
MMIO transaction with its original **fixture** label, and the complete output
including its restored prefix. Each backend passes 723 rejection assertions
without owner/MMIO/destination mutation. Structurally valid actual cursor
corruption first fails `uart_in_bits` at fixture C=128, operation 4; no input
valid acknowledgement or operation 5 is issued. Positive raw traces are
rechecked after all negative cases. These checks establish the host component,
not Rocket CPU `.fsckpt` or Level-2 semantic replay acceptance.

Run from the Chipyard root; each invocation preserves previous component runs:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_uart_checkpoint_vcs \
  --rocket-header automations/checkpoint_loop/runs/m11-iteration85/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h \
  --out automations/checkpoint_loop/runs/m11-iteration85/uart-native
```

The exact-recipe native VCS rebuild links the adapter and retains the settings
above, full 16-GiB functional backing, GCC/G++ 13.3 and 58 actual host translation
units. `rocket-build-identity.json` binds 207 current native inputs, including
actual compiler dependencies. Two complete four-hart workload controls, with
default and explicit buffered UART modes, independently pass at target count
3,329,794. Every complete hart trace matches the prior uninterrupted control
(37,582,346 / 49,976,156 / 50,391,641 / 50,189,006 bytes), as do independently
decoded phase/completion/failure/HTIF store and CPU-print labels. The generated
RTL, compared constant headers and complete simulator inventory match too.
These are uninterrupted controls; all four required CPU checkpoint cuts and
fresh CPU restore comparisons remain pending. Workload ELF SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Full M2/M3 metasim/ordinary RTL VCS, 52 existing widget continuations, all 219
Python tests and eight FCFS Make/four generator guards pass. Fresh exact-source
ChipTop discovery still rejects `FireSim.chiptop0.system.bdev_clock`, emitting
no partial semantic manifest/clean RTL. Fresh native CPU preflight/save/restore
requests still reject unsupported runtime ownership without publishing an
incomplete image. Full CPU cuts, fresh Level-1 continuation, independent
multi-clock semantic capture, fresh ordinary RTL zero-edge readback/replay and
CPU-level image/corruption tests remain pending.

The initial buffered post-run audit lacked `command.json`; the full native
run had passed. The executed launcher is retained as
`run-buffered-rocket-control.initial.py`. Command metadata was reconstructed
from that exact launcher, and the independent decoder/full trace comparison
was rerun against the complete finished run. Initial diagnostics and the
passing `rocket-buffered-control-audit-retry.log` are retained; no workload
was shortened or reported passing without actual execution. The interim
combined audit also correctly rejected while the buffered summary was pending.
The completed reusable audit checks all artifacts after both controls finish.

The previous verification failure was an old Git index/HEAD snapshot compared
after the controller's next checkpoint. Historical logs remain intact. The
retained-evidence audit now binds old UART sources to exact archived bytes and
pinned Git objects; current native evidence separately binds current sources.
The reusable check validates immutable protected inputs and controller
ancestry. `verify-protected-turn.py` additionally checks raw index/HEAD bytes
at turn end. See [evidence-lifecycle.md](evidence-lifecycle.md).

Executable native controls (no FPGA build):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration85/run-rocket-control.py
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration85/record-rocket-build.py
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration85/run-buffered-rocket-control.py
```

Independent saved-evidence verification:

```sh
python -m automations.checkpoint_loop.runs.m11-iteration85.verify-evidence
```

## Iteration 84: block-device host ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration84/`.

Added `firesim.widget.blockdev.v1` for completed host calls with a private
in-memory disk, including the actual workload's `+blkdev-in-mem0=128`, and for a
disconnected device. The disk now has an explicit owned, initially zeroed byte
buffer behind `fmemopen`; both memory and external FILE streams close at
destruction. The adapter binds all 26 generated MMIO addresses, the actual one
tracker/24-bit latency configuration, sector geometry and runtime latencies.
It captures initialization, response-pending status, ordered request/data/read
response/ack queues, every tracker offset/count/size and all 1,024 tracker data
words, all 65,536 disk bytes and the logical FILE position. FILE buffering is
flushed at the completed-call boundary; restore reconstructs an independent
stream at the captured position without MMIO or target advancement.

Decode and allocation precede all restore mutation. Invalid booleans, lengths,
tags, ranges, tracker shapes, pending flags, lifecycle contradictions,
configuration mismatches and incomplete disk bytes reject. Every public host
operation guards suspended/reentrant cuts and poisons interrupted calls.
External disk paths, debug logs and failed/EOF FILE state explicitly reject;
they need external ownership adapters. No CPU runtime whitelist is extended.

`blockdev-native/latest.json` selects the final component run under
`blockdev-native/native-xb8o3fpu/`. ASan/UBSan native execution and native VCS
DPI each terminate the source and independently restore all 15 cuts in fresh
processes. An independent Python oracle checks every owner byte, including
inactive tracker words and the full disk; native VCS reports readback at zero
edges. All MMIO operations, 128 actual read response words and two write
acknowledgements retain their fixture release labels. Cuts include data queued
before a request, queued requests, partial writes with 5/21 beats retained,
stalled acks and partially drained read responses. Each backend passes 1,639
negative assertions, including malformed/incompatible payloads, unsupported
external modes and interrupted calls, without partial owner mutation or MMIO.
A separate zero-edge roundtrip varies every disk byte, including its first and
last bytes, at a legal end-of-file position, checking libc reconstruction.
The final evidence audit also rechecks every positive raw continuation after
the negatives. It caught the initial negative fixture overwriting cut 5's
trace; the corrected suite isolates that fixture and retains all 15 traces.
Earlier diagnostics remain under their original run directories.

Actual partial-write tracker corruption passes structural loading, then fails
at the first changed `bdev_rresp_data_lower` write at **fixture** cycle 142,
operation 6, exit 1; no operation 7 is issued. These are host component fixtures,
not Rocket target-cycle cuts, CPU `.fsckpt` acceptance, or Level-2 semantic
replay. The complete Rocket run loop, TSI/FESVR, UART, four TracerV sinks and
heartbeat owners, coherent cuts, fresh full CPU restores and CPU image/fault
checks still remain. Independent current-source ChipTop discovery continues to
reject `FireSim.chiptop0.system.bdev_clock`, emitting no partial semantic
manifest or ordinary CPU RTL. The six clocks, async reset and original CPU
storage require a separate versioned semantic adapter.

Executable component check from the Chipyard root (creates a new run directory):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_blockdev_checkpoint_vcs \
  --rocket-header automations/checkpoint_loop/runs/m11-iteration84/build/f2/f2-firesim-FireSim-WithDefaultFireSimBridges_WithFireSimTestChipConfigTweaks_chipyard.QuadRocketConfig-WithAutoILA_FRFCFS16GBQuadRankLLC4MB_BaseF2Config/FireSim-generated.const.h \
  --out automations/checkpoint_loop/runs/m11-iteration84/blockdev-native
```

The exact-recipe build and complete four-hart control are reproducible through
`run-rocket-control.py`; its `rocket-native-commands.json` records each native
build/runtime/audit argv and result. Every VCS shell sources both environments,
then `vcs-env.sh` last. The source-bound recipe helper retains
all settings above and builds no bitstream. Native build artifacts use a new
iteration-84 directory, preserving prior controls.

The current exact-recipe build and full 16-GiB workload pass at C=3,329,794.
All four complete TracerV files match iteration 83 byte-for-byte (37,582,346 /
49,976,156 / 50,391,641 / 50,189,006 bytes). Independent retired-store decoding
confirms phases 1/2/3/4, completion 1, failure 0 on every hart and the actual
HTIF PASS store; every audited CPU-print cycle field also matches the prior
control. Workload ELF SHA256 remains
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.
Generated RTL, both compared constant headers and the complete generated-state
manifest retain their original bytes. `rocket-build-identity.json` binds 130
current input files and 58 native host translation units, GCC/G++ 13.3, the
normal executable and the newly linked blockdev methods. These are workload
and build controls, not restored CPU execution or complete boundary replay.

Full-path selection and executable checks are `selected-evidence.json`,
`verification-commands.json`, `verify-evidence.py`, `summary.json` and
`artifact-manifest.json`. The independent evidence checker re-audits complete
generated ownership, current source hashes, every component cut's full disk
and tracker words, all retained raw MMIO traces, native process statuses, CPU
controls, explicit runtime/semantic rejection, regressions and protected inputs.

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration84/run-rocket-control.py
```

Run the independent saved-evidence audit without rerunning the workload:

```sh
python -m automations.checkpoint_loop.runs.m11-iteration84.verify-evidence
```

## Iteration 83: exact generated RTL ownership

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration83/`.

The exact recipe now emits its complete generated RTL manifest and reference.
The metasim-only `plusarg_reader` adapter owns `myplus`, including its runtime
value rather than assuming `DEFAULT`. Each instance binds the exact inline
Verilog SHA256, WIDTH, DEFAULT and FORMAT; unknown models, ports and parameter
shapes still reject. This adapter describes the non-SYNTHESIS simulation model.
It does not add FPGA storage or change the target RTL. Level-2 IDs and the
FCFS runtime profile remain independent.

| Generated storage adapter | Entries | Words | Bits |
| --- | ---: | ---: | ---: |
| FIRRTL registers | 10,278 | 10,278 | 94,592 |
| FIRRTL memories | 742 | 435,116 | 20,899,468 |
| Emitter memory pipelines | 434 | 434 | 6,581 |
| Metasim plusarg registers | 7 | 7 | 193 |
| Metasim BUFGCE outputs | 3 | 3 | 3 |
| Total | 11,464 | 445,838 | 21,000,837 |

There are 2,292 generated instances. The seven plusarg registers belong to the
four cores' PlusArgTimeout instances, two UART transmit controls and the custom
boot pin. `rocket-generated-state-owners.json` also groups all storage by its
actual top-level owner, including the CPU-managed stream buffers, all four
TracerV bridges, TSI, blockdev, UART, FRFCFS/LLC, FAME and interconnect state.
This is generated RTL coverage; 16 GiB functional backing memory, native host
queues, MMIO/transport, scheduler and driver state still need complete owners.

`rocket-generated-independent-audit.json` independently checks emitted register
and memory declarations, including parameterized external instances, and passes
eight mutations of the actual Rocket artifacts: missing storage/owner, unbound
default, altered source, changed bound format, changed emitted width, an actual
extra register and missing model. Original files retain their hashes. These are
inventory rejection checks, not CPU checkpoint-image loader acceptance.

`plusarg-native/` contains separate capture and fresh ordinary VCS processes
using the compiler-produced two-owner inventory. Nondefault native values are
captured, conflicting startup plusargs are replaced, and both complete words
(33 bits) read back before any edge and match four diagnostic boundaries.
An actual storage-bit fault first diverges at boundary 0, edges=0, exit 1.
The initial diagnostic found VCS returning zero for `$fatal`; the final check
uses the existing DPI failure function and verifies nonzero native status.
This microtest establishes the external adapter only, not clean CPU RTL replay.

Executable native adapter verification, from the Chipyard root (each invocation
keeps prior evidence and creates a fresh output directory):

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.verify_plusarg_inventory_vcs \
  --inventory automations/checkpoint_loop/runs/m11-iteration83/scala-artifacts/plusarg-inventory.json \
  --reference automations/checkpoint_loop/runs/m11-iteration83/scala-artifacts/plusarg-reference.fir \
  --out automations/checkpoint_loop/runs/m11-iteration83/plusarg-native
```

All 16 compiler inventory tests and 219 Python tests pass. Fresh complete M2
and M3 native VCS metasim/ordinary RTL regressions pass, retaining their five
cuts/22-word readback/C=29 divergence and 717 transport edges/23 advances/six
captures/242 boundary samples/eight invalid reads respectively. Eight FCFS Make
and four generator guards pass without changing its compiled inventory.

### Native Rocket execution and generated-state samples

The exact recipe's native VCS build with read-only probes passes. The full
16-GiB, four-hart workload passes at 3,329,794 fastest-clock target cycles.
`rocket-workload-audit.json` independently decodes all harts' phase 1/2/3/4,
completion=1, failure=0 and the real HTIF PASS store from native execution.
The workload ELF remains SHA256
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

Every sample in `rocket-generated-probe/generated-state.jsonl` contains all
445,838 generated words at one settled host falling edge. The sample's actual
`ClockBridgeModule_0.tCycleFastest` value supplies its target-count label:

| Diagnostic sample | Target count | Host sample | Valid D-cache lines, harts 0/1/2/3 | Harts waiting for a cached grant | Host reads in flight |
| --- | ---: | ---: | --- | --- | ---: |
| Startup/early execution | 50,000 | 467,603 | 313 / 1 / 1 / 1 | 0 | 0 |
| Warmed-cache execution | 850,000 | 3,421,115 | 498 / 507 / 501 / 501 | 0, 1, 2 | 0 |
| Outstanding workload memory | 1,013,847 | 3,737,220 | 511 / 511 / 510 / 510 | 1, 2, 3 | 1 |
| Late execution | 3,200,000 | 8,002,559 | 511 / 512 / 510 / 512 | none | 0 |

`rocket-active-sample-audit.json` binds the actual DCache/ClientMetadata sources
and lowered bit extraction: coherence state is bits 24:23 of each of eight
64-word tag banks, and Nothing=0. `cached_grant_wait` is set when an actual
cached TileLink request fires and cleared by the final grant beat. All four
saved PC payloads at the outstanding sample are in the workload's memory loop.
These observations establish active generated state. They do not certify an
atomic simulator/host cut or original multi-clock semantic state at those
labels; all four required checkpoint/restore cut tests remain pending.

`rocket-trace-comparison.json` compares all four complete TracerV files against
the iteration-82 uninterrupted control: 37,582,346 / 49,976,156 / 50,391,641 /
50,189,006 bytes match respectively. Independently decoded phase, completion,
failure and HTIF store cycle fields also match. This establishes that the
read-only probes preserve the recorded instruction behavior and timing. It is
not restored execution or complete original-DUT boundary replay.

Current native artifacts are `rocket-generated-summary.json`,
`rocket-generated-independent-audit.json`, `rocket-build-identity.json` (145
bound inputs, 58 actual host translation units and GCC/G++ 13.3),
`rocket-native-commands.json` (exact build, full workload and audit argv/results),
`rocket-generated-runtime/{command.json,exit.json,native-vcs.log,TRACEFILE-C0..C3}`
and the two sample/trace audits above. The emitted RTL and all three headers
are byte-identical to iteration 82 (`rocket-baseline-build-byte-comparison.json`).

The following reproduces the native build/control/probe check using this run's
diagnostic build/output directory. Exact individual VCS commands and all recipe
settings are also recorded in `rocket-native-commands.json`:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration83/run-rocket-generated.py
```

Fresh native unsupported-runtime checks create their own output directory:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
PYTHONPATH="$PWD" python automations/checkpoint_loop/runs/m11-iteration83/verify-rocket-runtime-rejection.py
```

Preflight/save/restore each exits 1 before driver initialization and publishes
no partial checkpoint. Actual CPU image decoding remains unsupported. A fresh
exact-source semantic compiler request also rejects
`FireSim.chiptop0.system.bdev_clock` and emits no partial semantic manifest or
clean CPU RTL (`rocket-semantic-inventory/{command.json,summary.json,native-compiler.log}`).
Complete Level-1 fresh-process continuation, independent Level-2 zero-edge CPU
readback/finite boundary replay, CPU image rejection and first semantic
divergence remain required. No CPU recipe/level is verified.

## Retained iteration 82 evidence

Diagnostic root:
`/scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/runs/m11-iteration82/`.

Workload ELF SHA256:
`f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4`.

* `rocket-recipe.json`: exact YAML bytes/hash, raw and resolved settings,
  executable complete-inventory Make commands.
* `rocket-elaboration-audit.json`: source-bound high-form elaboration with all
  four RocketTile instance paths, six ChipTop clock inputs, async reset and
  original external modules. This is not a complete lowered state manifest.
* `rocket-native-owners.json`: actual header's three constructor passes and
  the separately audited heartbeat construction. State adapters remain pending.
* `rocket-build-identity.json`: emitted baseline RTL, headers, concrete
  blackboxes, executable and tool/setup hashes. No checkpoint profile enabled.
* `rocket-verilog-cache.log`: complete generated inventory rejects the actual
  unadapted `plusarg_reader` inside core 0's `PlusArgTimeout`. Earlier writable
  cache setup failure is preserved in `rocket-verilog.log`.
* `rocket-semantic-inventory-retry.log`: independent pre-FAME ChipTop inventory
  rejects `FireSim.chiptop0.system.bdev_clock`; no semantic manifest, checkpoint
  image or clean CPU RTL acceptance is claimed. The initial missing output
  directory diagnostic remains in `rocket-semantic-inventory.log`.
* `rocket-baseline-vcs-build-retry.log`: exact regular recipe VCS build passes.
  The earlier include-path error is preserved in `rocket-baseline-vcs-build.log`;
  installed `libdwarf.h` and its library were found in the existing Conda env.
* `workload/{summary.json,commands.json,rocket-quad.riscv}`: RV64IMA/Zicsr
  bare-metal program, source/ELF hashes, native compiler and Spike commands.
  Each of four harts checks 64 KiB through early stores, sequential reads,
  three rounds of cache-line-strided read/write work and late verification.
  All four must complete before HTIF PASS. Fault ELFs corrupt real memory on
  harts 0/1/2/3 and return failure codes 1/2/4/8 respectively in Spike.
* `rocket-baseline-runtime-full-retry/command.json`: executable native VCS
  workload command, full 16 GiB functional backing memory, native output and
  four TracerV streams. PASS after 3,329,794 fastest-clock target cycles;
  native exit 0. Initial wrong-unit memory and argument-position diagnostics remain
  in the separate `rocket-baseline-runtime*` directories.
* `rocket-baseline-audit.json`: independent decoding of actual retired SD
  instructions and their source-register values. Every hart wrote phases
  1/2/3/4, completion 1 and failure 0; hart 0 actually stored HTIF PASS 1.
  Per-hart print labels are recorded separately from checkpoint target-cycle
  labels. This audit establishes workload execution, not checkpoint replay.
* `rocket-fcfs-profile-rejection.json`: the actual exact Rocket Make request
  rejects `FS_CHECKPOINT_PROFILE=fcfs-fased-v1` before generation, preserving
  the baseline RTL/header/executable bytes. This is a build preflight check;
  invalid CPU-image loader rejection remains unverified.

## State ownership and remaining acceptance

The constructor order is master, loadmem, CPUManagedStreamWidget, peek-poke,
reset-pulse, blockdev, UART, FASED, four TracerV instances, TSI and clock.
`firesim_top_t` adds heartbeat after construction. The actual F2 configuration
has one functional-memory channel, rather than the FCFS profile's four. Audit
complete generated storage, FAME/channel/clock state, MMIO, full functional
memory and host timing independently for this configuration.

`firesim_top_t` currently inherits the unsupported checkpoint schema and lacks
incremental dispatch. Its termination/run-loop state, scheduler and base
lifecycle need explicit owners. TSI/FESVR needs loading flags, wait/step state,
loadmem and serial queues, HTIF state and suspended execution accounted for.
UART, blockdev, four trace sinks, CPU stream, heartbeat and FRFCFS/LLC model
state also require configuration-specific audit. The FCFS whitelist remains
restricted; constructor membership alone never certifies a driver adapter.

Iteration 83's source-bound `rocket-runtime-owner-audit.json` distinguishes
existing hooks from missing ones. CPUManagedStreamWidget already implements
`firesim.widget.cpu-managed-stream.v1`: its host drivers have no persistent
queue offsets, but initialization, stream parameters, suspended stream calls
and the actual CPU AXI transport still need native cut/restore validation.
FASED already has a host adapter for configuration, lifecycle, statistics,
histograms and range counters; its presence does not certify this FRFCFS/LLC
recipe or its one 16-GiB memory channel. Generic master/loadmem/peek-poke/reset/
clock hooks likewise require exact CPU configuration binding.

| Missing concrete runtime adapter | State that cannot be omitted |
| --- | --- |
| FireSim run loop | `terminated`, local exit/run-loop phase, scheduler credits/deadlines/callbacks, base lifecycle and completed-operation dispatch |
| TSI/FESVR | Wait/step/loading flags; loadmem and serial queues; inherited testchip/HTIF state; suspended `context_t` execution, which contains process-specific pointers and a ucontext or pthread |
| Blockdev integration / external modes | Private-memory/disconnected host hooks now pass native component checks; complete CPU atomic cut integration and external disk/log ownership remain pending |
| UART | Serial handshake data, handler/input positions, pending external bytes, global `specialchar` and endpoint/signal behavior |
| Four TracerV sinks | Cycle/trigger/clock state, file history and positions, tracker/mode state, stream identities and any suspended token buffer; draining streams affects target timing |
| Heartbeat | Poll/trip/last-cycle/timeout state, time origin, configuration and log history; it can terminate execution |

The audit hashes the actual generated header, reviewed driver implementations,
testchip inheritance and installed FESVR headers. It explicitly remains an
in-progress source audit. Native preflight/save/restore requests on the exact
Rocket binary still reject unsupported CPU runtime ownership and publish no
partial checkpoint; this is not malformed-image loader acceptance.

Proposed Level-2 boundary is the complete `FireSim.chiptop0`, containing all
four CPUs, caches and uncore. Its external memory/device/serial inputs must be
recorded at the actual boundary. Six named clock inputs include 500 MHz uncore
and 1000 MHz tile/memory clocks. Alias resolution, async reset, clock phase and
multiple-clock trace/replay require an explicit versioned adapter; do not force
them into the current single-clock semantic schema or omit crossing state.

No early/warmed/outstanding-memory/late checkpoint cut is verified yet. Phase
markers in the workload help select cuts but cannot establish actual cache or
in-flight state. Complete fresh-process Level-1 continuation, independent
Level-2 zero-edge readback/replay, all sampled timing comparisons, atomic
invalid-image/build/owner rejections and first-divergence semantic corruption
remain required. No `.fsckpt`, `.rtlckpt` or boundary `.trace` is claimed here.

## Executable native regressions

Run from the Chipyard root. Source `vcs-env.sh` last in every VCS shell.

```sh
source env.sh && source sims/firesim/env.sh
export COURSIER_CACHE="$PWD/automations/checkpoint_loop/runs/m11-iteration82/coursier-cache"
export TMPDIR="$PWD/automations/checkpoint_loop/runs/m11-iteration82/tmp-semantic"
export JAVA_TOOL_OPTIONS='-Xmx8G -Xss8M'
source automations/checkpoint_loop/vcs-env.sh
VCS_FLAGS=-Mupdate python -m tools.checkpoint_formats.tests.verify_semantic_vcs \
  --build automations/checkpoint_loop/runs/m11-iteration82/semantic-build \
  --out automations/checkpoint_loop/runs/m11-iteration82/semantic-regression-retry
```

M2 passes all five cuts, all 22 words, actual first divergence C=29 and four
loader rejections. M3's analogous `verify_banked_vcs` command uses `banked-build`,
`banked-regression` and `tmp-banked`; it passes 717 transport edges, 23 semantic
advances, six captures, 242 clean replay samples and eight invalid reads.
`assembly-destination-audit.json` checks all three newly requested JARs contain
the native generator/Golden Gate main classes. The Make helper now disables
sbt-assembly's stale destination cache and checks nonempty output before touch.
The observed zero-byte reused M2 build cache was repaired from the isolated,
native-validated JAR; `empty-cache-repair.json` records before/after bytes.

All 218 Python tests and the eight FCFS Make/four generator rejection checks
pass. Exact logs are `python-tests-final.log`, `fcfs-make-regression/summary.json`
and the two native regression directories. These regressions preserve earlier
support; they cannot substitute for CPU checkpoint acceptance.

The native Rocket baseline command can be rerun verbatim from
`rocket-baseline-runtime-full-retry/command.json`. Audit its actual output with:

```sh
source env.sh && source sims/firesim/env.sh
source automations/checkpoint_loop/vcs-env.sh
python -m tools.checkpoint_formats.tests.audit_rocket_baseline \
  --runtime automations/checkpoint_loop/runs/m11-iteration82/rocket-baseline-runtime-full-retry \
  --workload automations/checkpoint_loop/runs/m11-iteration82/workload \
  --out automations/checkpoint_loop/runs/m11-iteration82/rocket-baseline-audit.json
```

`verify-evidence.py` rechecks selected current-source native evidence and
protected inputs. `summary.json`, `verification-commands.json` and
`artifact-manifest.json` record the final in-progress result and full-path
recovery. No CPU checkpoint acceptance is inferred from the native baseline.
