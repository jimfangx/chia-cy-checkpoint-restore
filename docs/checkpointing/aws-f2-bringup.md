# AWS F2 Rocket baseline, iteration 175

Iteration 176 revalidated these original hardware records without relaunching
the terminated instance. Fresh receipts are in
`automations/checkpoint_loop/runs/aws-f2/iteration176/`: the strengthened
`baseline-complete-audit.json`, **14** rejected evidence corruptions,
**39** passing loop/config/inventory tests, successful AWS/HDK checks,
and a fresh EDA VCS SP2 run passing all **82** cut-coordinator checks.
The audit now requires all four native manager logs, their disabled-metasim
configuration, workload/result identity and exact localhost build recipe.
The new AWS inventory independently reconfirms scoped cleanup.

Real FPGA workload execution passed on October 23, 2026. This verifies the
baseline hardware path only. No FPGA checkpoint has been captured and no
checkpoint-enabled AFI has been built or deployed.

| Item | Actual evidence |
| --- | --- |
| Account / region / AZ | `832554215407` / `us-west-2` / `us-west-2b` |
| Instance / type | `i-04b9cc3f81f16b61f` / `f2.6xlarge` |
| AMI / private IP | `ami-07a164f1a402ab274` / `192.168.1.203` |
| Owned farm tag | `fsimcluster=checkpoint-f2-rocket-baseline-175` |
| Slot / PCI function | `0` / `0000:34:00.0`, vendor `1d0f`, device `f002` |
| Loaded public image | `agfi-0c5eedfce0e568971`, `afi-0505c12c75f5cedaf`, shell `0x10212415` |
| Exact recipe | `firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3` |
| Actual runtime | One node, `no_net_config`, `metasimulation_enabled: false` |
| Workload | Four-hart self-checking `rocket-quad.riscv`, 6,712 bytes |
| Workload SHA-256 | `f3d86f54caf42b9589385e8021dba46777f647134f19595e38a3d452b745f3d4` |
| Deployed driver SHA-256 | `dc6e4eaaf093eebcb65da294ddec11bc956ee7495e38891e005ad1112f0e05d9` |
| Target result | `*** PASSED *** after 44104832 cycles`, driver command exit 0 |

The target pass label is the FPGA driver's completion observation, not a
checkpoint cut or a migration comparison. The driver log records 0.3 seconds,
140.002 MHz host frequency and 131.897 MHz effective target frequency. These
are baseline measurements, not checkpoint overhead or achieved image Fmax.

Evidence root:
`automations/checkpoint_loop/runs/aws-f2/iteration175/`.

* `instance.json` and `aws-identity.json` record AWS API identity;
  `imds-document.stdout` independently records on-host instance identity.
* `loaded-slot.stdout` records loaded/error-free slot 0. `public-image.json`
  preserves AWS image metadata, including the public image producer commit.
* `deployed-hashes.stdout` binds the actual remote ELF, driver and run script;
  `driver-provenance.json` and `driver-source/` preserve the local driver and
  its C++/generated-header source snapshots. Public image source provenance is
  distinct from the modified local driver source provenance.
* `results-workload/checkpoint-f2-rocket-selfcheck-1750/` preserves `uartlog`,
  `sim-run.sh`, `HW_CFG_SUMMARY` and memory statistics. Original remote and
  manager paths remain in `native-paths.json` and the unmodified native logs.
* `baseline/manager-commands.json`, the four isolated YAMLs, native manager
  logs, task logs and return-code receipts preserve launch, deployment,
  workload execution and scoped teardown. The initialized manager YAMLs and
  AWS setup were reused. No managerinit, credentials setup or account bootstrap
  was run.

The retained workload ELF was independently rerun in Spike. A fresh GCC 16.1
rebuild also passed healthy four-hart execution and all four deliberately
corrupted-hart cases; it has its own different hash and was not the FPGA ELF.
Those fresh compiler and Spike logs are in `workload-fresh/`. Do not substitute
that ELF's hash for the actual FPGA workload hash.

Use the raw argv in `baseline/manager-commands.json` to reproduce manager tasks
through `f2.py run`. The installed workload JSON and directory were symlinks
into this evidence root; preserve or recreate those same invocation-local
inputs before another workload run. The official
[manager setup](https://docs.fires.im/en/latest/getting-started-guides/aws-ec2-f2-getting-started/setting-up-the-firesim-repo/),
[single-node](https://docs.fires.im/en/latest/getting-started-guides/aws-ec2-f2-getting-started/running-simulations/running-a-single-node-simulation/)
and [image-build](https://docs.fires.im/en/latest/getting-started-guides/aws-ec2-f2-getting-started/building-a-firesim-afi/)
guides were consulted. This checkout's required localhost build farm takes
precedence over the guide's EC2 build-host example.

Resource cleanup completed through the exact isolated `terminaterunfarm`
command after collecting hardware results. `resources-after-cleanup.json`
independently confirms this instance is **terminated**; its native localhost
process inventory records no active Vivado/Java build jobs. The manager and
localhost build server remain untouched. New checkpoint image requests: none.

`baseline-audit.json` independently cross-checks the saved configs, AWS API
and on-host identities, image metadata, loaded slot, deployed bytes, target
pass and final cleanup. `baseline-audit-negatives.json` records nine rejected
offline evidence forgeries. All 37 loop/config/inventory tests pass. The raw
hardware-probe diagnostic failure described below is preserved separately.

Checkpoint-image implementation has started with
`CheckpointCaptureCut.sv`: a synthesized owner-acknowledgement/freeze component,
not a connected Rocket capture implementation. Local Vivado 2025.2 and F2 HDK
`80b34d3` pass environment/version checks. Native FPGA out-of-context synthesis
for `xcvu47p-fsvh2892-2-e`, with 16 owners, passes at 56 LUTs and 74 registers.
The DCP, utilization and timing reports are in `cut-vivado/`. This is an
unplaced component result; full-image synthesis, place/route, AFI creation,
complete state binding, bridge MMIO/DMA and host-owner capture remain pending.
Exact future build configs use ExternallyProvisioned `[localhost]` and an
invocation-local `build-host/`. See [f2-rocket-image.md](f2-rocket-image.md).

At the stopped iteration 175, the component's EDA check failed before RTL
parsing with `Cannot find license file` (exit 255). The original `cut-vcs/`
logs preserve that failure and the empty license environment.

The subsequent license recovery is verified: `.zshrc` sources
`/tools/flexlm/flexlm.sh`, whereas noninteractive bash does not read `.zshrc`.
The updated `vcs-env.sh` now loads that site setup if licenses are absent,
preserving inherited settings and supporting `CHECKPOINT_EDA_LICENSE_SETUP`.
A fresh native EDA SP2 compile and simulation pass with
`CHECKPOINT_CUT_PASS checks=82`, proving compile/runtime license checkout.
The compile uses `-timescale=1ns/1ps` to set the component's default timescale
consistently with its testbench. No behavioral checks were removed.

Recovery artifacts under
`automations/checkpoint_loop/runs/aws-f2/iteration175/eda-license-confirmed-7rd4saf_/`:
`summary.json` (source/log hashes), `verification-commands.json` (exact EDA argv),
`license-environment.log`, `compile.log`, `run.log` and `transport.log`.
The initial post-license timescale failure is retained separately in
`eda-license-recovery-ub66p4av/`. These results verify the cut component only;
no checkpoint-enabled FPGA image or complete hardware checkpoint is claimed.
The controller's saved progress is unchanged pending the next normal turn.

Known diagnostics retained: a `firesim.pem`-only localhost OpenSSH check failed,
while actual Fabric/default-key localhost access passed. The optional
`/dev/xdma*` probe failed because the actual F2 implementation attaches BAR4
PCIS rather than F1 XDMA; required identity, image and byte-hash probes passed.
Neither diagnostic establishes an outstanding baseline access dependency.
