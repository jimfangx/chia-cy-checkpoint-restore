"""Checkpoint/restore, finite replay and restored-metasim-guided RTL work.

AWS F2 hardware capture is required. Historical milestone names are retained
only for completed component work; new F2 names require fresh hardware evidence.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Milestone:
    name: str
    task: str
    acceptance: str
    required_files: tuple[str, ...] = ()
    needs_vcs: bool = False
    needs_f2: bool = False


CPU_LIVE_TASK = (
    " Restore a matching FPGA-produced Level-1 and Level-2 pair into fresh metasim and original "
    "pre-FAME RTL VCS processes at the same logical target cut. Keep restored "
    "metasim running as the environment authority, drive clean RTL with its live "
    "target-boundary inputs, compare every output before acknowledging each edge, "
    "and retain full-visibility RTL debug waveforms. Exercise active workload, "
    "backpressure and outstanding memory traffic beyond the recorded trace window."
)
CPU_LIVE_ACCEPTANCE = (
    " A fresh restored metasim/clean-RTL pair passes independent complete zero-edge "
    "state readback and sustained cycle-exact live comparison beyond the recorded "
    "trace window, with healthy completion of both processes and debug waveforms. "
    "Deliberate semantic corruption stops at its first divergent signal/target "
    "cycle without acknowledging that edge. Finite replay or component restores "
    "alone cannot establish live CPU acceptance."
)

# Exact ordering used by state files without milestone_order. These names are
# migration metadata only; removed work has no executable milestone here.
LEGACY_MILESTONE_ORDER = (
    "M0-reconnaissance",
    "M1-schema-and-stateids",
    "M2-semantic-vcs-replay",
    "M3-banked-state-access",
    "M4-full-metasim-restore",
    "M5-rolling-checkpoints",
    "M6-live-clean-rtl-shadow",
    "M7-dessert-replay",
    "M8-formal-state-map",
    "M9-gate-level-replay",
    "M10-production-dut-formal-map",
    "M11-rocket-level1-level2",
    "M12-boom-level1-level2",
    "M13-shuttle-saturn-level1-level2",
)


MILESTONES = (
    Milestone(
        "M0-reconnaissance",
        "Trace the current Golden Gate pass order, semantic state before FAME, "
        "generated simulator state, bridges, DMA, FASED, host drivers, VCS "
        "metasim targets, and live clean-RTL interfaces. Record exact source "
        "paths and unsupported state. Do not assume names from older FireSim.",
        "A source-backed reconnaissance document identifies a viable StateID "
        "insertion point and all known Level-1 state owners.",
        ("docs/checkpointing/reconnaissance.md",),
    ),
    Milestone(
        "M1-schema-and-stateids",
        "Implement separate versioned .fsckpt and .rtlckpt schemas, .trace, "
        "checksums/build compatibility, and a pre-FAME semantic StateID inventory "
        "for registers and memories. Unsupported state must fail explicitly.",
        "Bit-exact format round trips, corruption rejection, and a semantic "
        "manifest for a test DUT with registers, FSM, register array, and SRAM.",
    ),
    Milestone(
        "M2-semantic-vcs-replay",
        "In VCS metasim, capture semantic DUT state and target-cycle boundary I/O; "
        "restore it in a fresh ordinary, untransformed RTL VCS process and replay "
        "a finite trace with waveform output. Include in-flight operations.",
        "Fresh-process clean RTL replay matches the reference for every sampled "
        "target cycle and reports the first mismatch with signal and cycle.",
        needs_vcs=True,
    ),
    Milestone(
        "M3-banked-state-access",
        "Implement synthesizable banked checkpoint access for semantic registers "
        "and memories with deterministic order, freeze, backpressure and errors. "
        "Compare its metasim output to the VCS backdoor oracle.",
        "Hardware-style extraction is bit-identical to the software oracle "
        "without direct readout of DUT internals.",
        needs_vcs=True,
    ),
    Milestone(
        "M4-full-metasim-restore",
        "Inventory and capture all generated FireSim simulator state, including "
        "FAME state, LI-BDN, FASED timing and functional memory, bridges, host "
        "driver state, counters, and in-flight transactions. Restore into a "
        "fresh VCS metasim process before target time advances.",
        "Checkpoint/restart and uninterrupted VCS metasim have identical "
        "target-visible outputs and transaction timing, including outstanding "
        "memory traffic; unsupported drivers fail closed.",
        needs_vcs=True,
    ),
    Milestone(
        "M5-rolling-checkpoints",
        "Add periodic target-cycle snapshots with atomic publish, integrity "
        "validation and bounded retention. Preserve old snapshots until a new "
        "one is committed. Support host and target progress watchdogs.",
        "A retained checkpoint replays through an injected late hang or stall.",
        needs_vcs=True,
    ),
    Milestone(
        "M6-live-clean-rtl-shadow",
        "Start a clean RTL VCS instance from Level-2 state alongside a Level-1 "
        "restored metasim. Drive the clean RTL with the authoritative target "
        "boundary inputs, preserve ready/valid timing, compare outputs per "
        "target cycle, and stop at first divergence.",
        "Long metasim/clean RTL shadow run matches cycle by cycle and detects "
        "deliberate corruption at the correct target cycle.",
        needs_vcs=True,
    ),
    Milestone(
        "M7-dessert-replay",
        "Support independent finite .rtlckpt + .trace replay in ordinary VCS RTL "
        "without metasim or FASED, with a full visibility waveform.",
        "A deliberate RTL bug replays at the same target cycle from a snapshot "
        "and finite trace, without a live FireSim process.",
        needs_vcs=True,
    ),
    Milestone(
        "F2-bringup-and-baseline",
        "Read docs/checkpointing/aws-f2-workflow.md and the linked official F2 guide. "
        "Use the existing checkout and the four initialized deploy/config_*.yaml "
        "files as the manager. AWS has already been configured: do not rerun "
        "managerinit, aws configure or account bootstrap. Source sourceme-manager.sh "
        "and use that setup, reporting actual AWS access failures if encountered. "
        "Generate per-invocation overrides using f2.py; "
        "launch/reuse one tagged f2.6xlarge, keep metasimulation_enabled false, deploy "
        "the existing Rocket recipe's public image for baseline bring-up, and run a "
        "self-checking workload on the real FPGA. Record the exact instance, slot, "
        "loaded AGFI, recipe, workload bytes/hash and hardware logs. Plan and start "
        "the checkpoint-enabled image implementation/build on this server for the "
        "following milestone. Use ExternallyProvisioned localhost for Vivado; never "
        "launch EC2 build hosts or run bitstream builds on EDA. "
        "Do not treat a public image or baseline run as checkpoint support.",
        "A real single-node AWS F2 workload completes with independently recorded "
        "AWS instance identity, loaded image/slot evidence, workload hash and target "
        "pass result; metasimulation is disabled in the actual runtime config. "
        "The manager commands/configs/results and scoped resource cleanup/resume "
        "inventory are saved locally. AWS credentials or a successful CLI preflight "
        "alone cannot satisfy bring-up. Missing quota/IAM/AMI/network/key access is "
        "reported with the exact failing command, without substituting metasim.",
        ("docs/checkpointing/aws-f2-bringup.md",),
        needs_f2=True,
    ),
    *(
        Milestone(
            name,
            "Implement actual AWS F2 checkpoint capture for " + family + ": use existing "
            "recipe " + recipe + " from sims/firesim-staging/sample_config_build_recipes.yaml. "
            "Re-read the current plan_agent.md and docs/checkpointing/aws-f2-workflow.md. "
            "Implement and synthesize banked state readout, an atomic freeze/cut "
            "controller, CheckpointBridge MMIO/DMA transport, functional-memory and "
            "host-owner capture as needed; DMA alone cannot expose arbitrary state. "
            "Reuse the initialized manager/AWS configs. Build the checkpoint-enabled "
            "FPGA image from this source on the CURRENT server using the "
            "ExternallyProvisioned localhost build farm and native Vivado, not an "
            "EC2 build instance or EDA. Bind its "
            "AFI/AGFI and host driver to exact generated manifests and recipes, deploy "
            "to a real F2 FPGA and execute a self-checking workload. " + workload +
            " Capture complete .fsckpt and .rtlckpt plus target-boundary .trace from "
            "that running hardware through the synthesized transport, at early, "
            "warmed-cache, outstanding-memory and late cuts. Audit all simulator, "
            "FAME/token/channel, memory, bridge, host-driver and pre-FAME semantic "
            "state; preserve timing and atomicity. Compare a continued FPGA reference "
            "with fresh EDA VCS metasim restored from the actual FPGA .fsckpt before "
            "any target edge. Independently restore hardware .rtlckpt and replay its "
            "real trace in fresh untransformed RTL VCS. Exercise corrupt/truncated "
            "images, incompatible builds, missing owners and semantic corruption. "
            "Retain existing FCFS/fixture regressions, implement rolling capture on "
            "F2 and recovery, and record complete per-cut provenance and commands "
            "in runs/ and docs/checkpointing/cpu-checkpoint-matrix.md. " + CPU_LIVE_TASK,
            "A checkpoint-enabled image of the exact " + family + " recipe executes "
            "on an identified AWS F2 FPGA. At every required active-workload cut, "
            "complete FPGA-captured Level-1 state restores in fresh EDA VCS metasim "
            "with independently audited zero-edge readback and continuation matching "
            "the FPGA reference's target behavior and transaction timing. Complete "
            "FPGA-captured Level-2 state and boundary trace pass independent fresh "
            "clean-RTL readback and cycle-exact finite replay. Image/driver/build, "
            "instance/slot/AGFI, workload, transport, state coverage, cycle labels, "
            "image hashes and negative tests are bound to actual execution logs. "
            "Periodic FPGA captures retain valid history and reproduce a later "
            "failure after migration. Public-image boot, VCS backdoors, synthetic "
            "fixtures and metasim-origin images cannot establish hardware capture. "
            "Incomplete hardware coverage remains in_progress, never silently omitted. "
            + CPU_LIVE_ACCEPTANCE,
            ("docs/checkpointing/cpu-checkpoint-matrix.md",),
            needs_vcs=True,
            needs_f2=True,
        )
        for name, family, recipe, workload in (
            ("F2-rocket-checkpoint-migration", "Rocket",
             "firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3",
             "Exercise all four Rocket harts, active caches and memory traffic."),
            ("F2-boom-checkpoint-migration", "BOOM",
             "firesim_boom_singlecore_no_nic_l2_llc4mb_ddr3",
             "Exercise speculative and in-flight BOOM execution and memory traffic."),
            ("F2-shuttle-saturn-checkpoint-migration", "Shuttle + Saturn",
             "firesim_saturn_GENV256D128_shuttle_singlecore_no_nic_l2_llc4mb_ddr3",
             "Exercise actual vector computation and vector loads/stores with "
             "in-flight Saturn state; scalar-only and standalone Shuttle are insufficient."),
        )
    ),
)
