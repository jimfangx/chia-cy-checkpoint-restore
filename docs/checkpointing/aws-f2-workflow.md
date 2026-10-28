# AWS F2 hardware checkpoint workflow

Current acceptance requires a workload running on an actual AWS F2 FPGA to
produce both checkpoint levels and its boundary trace. Restore those images
on EDA; metasim-only snapshots remain regressions. The loop changes are
orchestration and acceptance policy: the complete synthesized capture network
and CPU/host-owner support must still be implemented and validated.

## Manager setup

The user has already initialized the four manager YAMLs in
`sims/firesim/deploy/` and run `aws configure`. Use these files and the existing
AWS identity/role/region and FireSim infrastructure. Do not rerun `managerinit`,
`aws configure` or account bootstrap. Source `sourceme-manager.sh` from
`sims/firesim`; see the [official F2 guide](https://docs.fires.im/en/latest/getting-started-guides/aws-ec2-f2-getting-started/setting-up-the-firesim-repo/)
for reference rather than repeating initialization. Preserve custom settings.
`CHECKPOINT_F2_SETUP` can source additional local manager environment setup.
Report concrete AWS access errors if operations fail; configuration alone is
not evidence of FPGA execution.

Bitstream builds run on **this server** using FireSim's
`build-farm-recipes/externally_provisioned.yaml` and
`build_farm_hosts: [localhost]`. The initialized `config_build.yaml` has this
setting. Generated invocation configs enforce it and use an invocation-local
`build-host/` directory. They never launch EC2 build instances or build on EDA. Direct `firesim
buildbitstream` commands through the helper reject old AWS/remote build-farm
configs before execution.
FireSim uses SSH even for its localhost build host, so confirm its configured
key can reach localhost and that the native Vivado version satisfies the F2
HDK when starting a build. The build-host release operation is a no-op; it
must never terminate this server. AWS supplies the F2 runtime and AFI service.

With the local Chipyard environment active:

```bash
python automations/checkpoint_loop/f2.py check
```

This sources the manager environment noninteractively, checks key availability,
queries AWS caller identity and F2 instance-type access, and launches nothing.
It does not prove that quota, a particular AMI, SSH connectivity, a loaded FPGA
image or workload execution works. Record the actual error for any blocked
operation. Missing access must never cause substitution of metasim capture.

For replayable preflight evidence, run `automations/checkpoint_loop/f2_preflight.py`
through `f2.py run`. Supply the retained invocation, a protected-input hash
mapping, an output directory beneath `runs/`, and an optional selection file.
Every attempt owns a new directory containing its receipt, native-tool log and
AWS inventory. Only a successful attempt updates the selection, atomically.
Audit the selected receipt and all its bound artifacts with `audit_receipt`;
retain previous selections when comparing observations. Never overwrite a
receipt already referenced by an audit: AWS response IDs, timestamps and process
inventories legitimately change between observations.

## Baseline hardware run

Start with a fresh invocation directory and an installed self-checking FireSim
workload JSON. `WORKLOAD.json` below is a placeholder for that real workload,
not an installed example or a new checkpoint option:

```bash
python automations/checkpoint_loop/f2.py prepare \
  --family Rocket --phase baseline --workload WORKLOAD.json \
  --out automations/checkpoint_loop/runs/aws-f2/rocket-baseline-001
```

This writes isolated runtime/build/recipe/HWDB YAMLs and `manager-commands.json`.
It reads the initialized four manager configs as its base, preferring an existing
selected recipe/HWDB entry; it uses the staging CPU recipe or public AGFI only
when the selected entry is absent. It records input config paths/hashes and
preserves unrelated custom runtime options. It uses one `f2.6xlarge`, one non-networked
node, a dedicated `checkpoint-f2-*` tag and `metasimulation_enabled: false`.
Repeated launches reuse rather than unconditionally expand the tagged farm.
An existing invocation cannot be overwritten. Source recipe fields are retained;
Makefrag and bit-builder paths are resolved explicitly for the manager.

Use the exact argv arrays in `manager-commands.json`, in this order:
`launchrunfarm`, `infrasetup`, `runworkload`. For an exploratory command:

```bash
python automations/checkpoint_loop/f2.py run --cwd sims/firesim/deploy -- \
  firesim launchrunfarm -c /absolute/invocation/config_runtime.yaml \
  -b /absolute/invocation/config_build.yaml \
  -r /absolute/invocation/config_build_recipes.yaml \
  -a /absolute/invocation/config_hwdb.yaml
```

The local manager provisions and talks to AWS run-farm hosts; it is not a local
FPGA emulator. The official [single-node guide](https://docs.fires.im/en/latest/getting-started-guides/aws-ec2-f2-getting-started/running-simulations/running-a-single-node-simulation/)
describes launch, deployment and workload execution. Preserve raw AWS instance
ID/type/region and loaded-image/slot output, exact configs, source/driver/image
and workload hashes, target pass logs and a resource inventory. A public-image
baseline passes bring-up only, not checkpoint extraction. Write actual results
in `docs/checkpointing/aws-f2-bringup.md`; leave untested steps pending.

## Build the checkpoint-enabled image

Use `--phase checkpoint` (the default) and a new output directory. A matching
private entry in the initialized HWDB is reused, or select one with `--hwdb`.
If no checkpoint image exists yet, the generated HWDB is empty so image builds
can be prepared; deployment must wait for an available image. After implementing the
capture logic, use the generated `buildbitstream` command to build the exact
recipe. FPGA synthesis, place/route and AFI generation are required here;
ASIC synthesis/formal/gate/power tools remain outside scope.

FireSim's [F2 image-build guide](https://docs.fires.im/en/latest/getting-started-guides/aws-ec2-f2-getting-started/building-a-firesim-afi/)
explains custom builds and the generated HWDB entry. This checkout's manager
writes build results in `deploy/results-build/` and entries in
`deploy/built-hwdb-entries/`. Record exact source/generated manifest/driver hashes,
AFI/AGFI, availability state, region and build settings. Preserve in-flight
build IDs across turns instead of starting duplicate builds.

Prepare a new checkpoint-runtime invocation with `--hwdb` pointing to the
new entry and `--hwconfig` if its key differs. Known stock public AGFIs are
rejected for checkpoint phase. A custom AGFI alone still proves no checkpoint
functionality. The manifest records `build_execution: localhost`. The generator marks `checkpoint_hardware_verified: false` and
records intent only; its JSON is never hardware execution evidence.

Implement complete synthesized state readout, atomic global cut/freeze,
MMIO/control, DMA framing/backpressure, memory and host-owner capture before
attempting a hardware checkpoint. Do not invent nonexistent plusargs or claim
that existing DMA or VCS backdoor code can read arbitrary FPGA flip-flops.
Keep every recipe's instrumentation and coverage explicit and reproducible.

## FPGA capture to EDA restore

1. Run a self-checking CPU workload on the checkpoint-enabled image. Audit
   full simulator and semantic state ownership for the actual recipe. Capture
   both levels and real boundary I/O at common target cuts during active work.
2. Configure the installed workload JSON's `common_simulation_outputs` (or
   per-job simulation outputs) with the actual implemented checkpoint/trace
   filenames so FireSim collects them from the F2 run host. Keep raw manager
   logs and results. Copy the images, host-state payloads, traces, manifests
   and complete execution receipts into this invocation under loop `runs/`.
   Fail the step if collection is missing or incomplete.
3. Bind each cut to account/region/instance ID/type, slot/loaded AGFI, recipe,
   source/driver/manifests/workload hashes, target cycle, hardware transport,
   complete state totals and checksummed payloads. Record source-FPGA
   continuation as the reference, then stop its driver. Host-clock observations
   cannot replace target-cycle labels. State must come from F2, not a metasim
   image paired with an FPGA trace.
4. On EDA, restore `.fsckpt` in fresh VCS metasim before target advancement,
   independently read back the complete state and compare continued behavior
   and transaction timing to the FPGA reference. Restore `.rtlckpt` separately
   in fresh ordinary RTL VCS, read it back and replay hardware `.trace`.
5. Restore the matching hardware-produced pair into fresh metasim/clean RTL;
   run sustained live RTL comparison beyond the prerecorded window. Restored
   metasim is now the environment authority. Retain full RTL debug waveforms,
   healthy completion, malformed-image rejection and first-divergence tests.
6. Repeat early, warmed-cache, outstanding-memory and late cuts for all four
   Rocket harts, then speculative BOOM and vector-active Shuttle + Saturn.
   Add periodic FPGA snapshots, atomic retention and late-failure recovery.
   Record performance and capture/transfer/restore overhead independently.

## Loop verification routing and resume

Report raw command argv with `backend: f2` for local manager/AWS hardware work,
and `backend: eda` for all VCS and EDA audits. Omitted backend defaults to EDA
for older reports. `cwd` remains relative to Chipyard. Use `bash -c` for manager
scripts to preserve the manager environment; source `vcs-env.sh` last in nested
EDA shells. No VCS runs on the manager or FPGA hosts.

The controller keeps report order: F2 capture results are synced before the
next EDA check; EDA results are fetched before the next manager check, including
nonzero simulation exits. Both failed checks and transfer failures prevent
acceptance. Report local artifact paths; preserve the real remote paths inside
receipts. Stage only acceptance inputs under `runs/` for EDA; native build
results, manager logs/configs and credentials are not mirrored to EDA by default.

The public-image `F2-bringup-and-baseline` is verified in the retained
iteration-175 physical run. The next incomplete hardware milestone is
`F2-rocket-checkpoint-migration`, followed by `F2-boom-checkpoint-migration`
and `F2-shuttle-saturn-checkpoint-migration`. Existing M0-M7 component history,
iteration counters, feedback, commits and historical completion names are kept.
Completed old metasim CPU milestones do not complete new F2 milestones.
`--dry-run` is offline and does not rewrite saved state. `--check-backends`
performs read-only AWS and EDA checks without launching instances. Backend
requirements are otherwise checked when needed, so FPGA bring-up can proceed
before an EDA restore is ready.

Track hardware status separately in `docs/checkpointing/cpu-checkpoint-matrix.md`.
A successful shell command or an agent's summary cannot by itself establish
complete hardware capture: independently verify the recorded evidence against
the milestone's state-coverage and behavioral acceptance criteria.

Use only the invocation's tagged AWS run farm and local build workspace.
Generated run-farm teardown argv uses `--forceterminate` with explicit configs;
collect artifacts first. Keep an inventory of owned F2 instances, local Vivado
jobs and AFI requests. Reuse or terminate owned runtime instances deliberately;
never terminate this localhost build server/manager or unrelated farms. Local
`build-host/` and default local-build worktrees stay here and are excluded from
EDA synchronization. Copy only required restore inputs and evidence outside
those directories. Do not share images or delete unrelated AWS resources.
