"""Checkpoint/restore, finite replay and restored-metasim-guided RTL work.

Physical FPGA bring-up is deferred. Milestone names retain historical labels
so legacy state can migrate without restarting completed checkpoint work.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Milestone:
    name: str
    task: str
    acceptance: str
    required_files: tuple[str, ...] = ()
    needs_vcs: bool = False


CPU_LIVE_TASK = (
    " Restore a matching Level-1 and Level-2 pair into fresh metasim and original "
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
        'M11-rocket-level1-level2',
        'Implement and validate both Level-1 and Level-2 checkpoint/restore for Rocket,'
        ' using existing recipe firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3 from '
        'sims/firesim-staging/sample_config_build_recipes.yaml. Re-read the current '
        'instructions at the top of plan_agent.md. Use exact recipe build settings in '
        'VCS metasim without building an FPGA bitstream. Audit and implement all '
        'CPU/configuration-specific simulator, bridge, host-driver and semantic DUT '
        'state owners; do not assume fcfs-fased-v1 support applies. Test real '
        'self-checking CPU workloads at early, warmed-cache, outstanding-memory and '
        'late cuts. For Rocket exercise all four cores; for BOOM speculative/in-flight '
        'execution; for Shuttle + Saturn actual vector compute and vector memory '
        'operations with in-flight vector state. Restore Level 1 in fresh metasim and '
        'independently restore Level 2 in fresh pre-FAME ordinary RTL VCS, read back '
        'complete state before any edge, and compare captured target-cycle behavior. '
        'Add invalid-image/build/state-owner rejection and first-divergence corruption '
        'cases, preserve existing regressions, and record exact artifacts and '
        'executable native VCS checks in docs/checkpointing/cpu-checkpoint-matrix.md. '
        'Standalone Shuttle and physical FPGA validation are outside the '
        'current task.' + CPU_LIVE_TASK,
        'The exact Rocket recipe passes independently audited complete Level-1 '
        'fresh-process metasim continuation against an uninterrupted workload run, and '
        'complete Level-2 zero-edge state readback plus finite captured-trace replay in'
        ' ordinary RTL VCS. All sampled outputs and transaction timing match at '
        'original target-cycle labels across the required active-workload cuts. '
        'Required malformed/incompatible/incomplete images reject before partial '
        'restore, and actual semantic corruption is detected at its first divergent '
        'boundary. Per-recipe/per-level evidence records workload hashes, exact state '
        'ownership and build settings, tested cuts, native VCS commands and results. '
        'Fixture-only, FCFS-only, boot-only, idle-only and scalar-only Saturn tests '
        'cannot satisfy this milestone.' + CPU_LIVE_ACCEPTANCE,
        ("docs/checkpointing/cpu-checkpoint-matrix.md",),
        needs_vcs=True,
    ),
    Milestone(
        'M12-boom-level1-level2',
        'Implement and validate both Level-1 and Level-2 checkpoint/restore for BOOM, '
        'using existing recipe firesim_boom_singlecore_no_nic_l2_llc4mb_ddr3 from '
        'sims/firesim-staging/sample_config_build_recipes.yaml. Re-read the current '
        'instructions at the top of plan_agent.md. Use exact recipe build settings in '
        'VCS metasim without building an FPGA bitstream. Audit and implement all '
        'CPU/configuration-specific simulator, bridge, host-driver and semantic DUT '
        'state owners; do not assume fcfs-fased-v1 support applies. Test real '
        'self-checking CPU workloads at early, warmed-cache, outstanding-memory and '
        'late cuts. For Rocket exercise all four cores; for BOOM speculative/in-flight '
        'execution; for Shuttle + Saturn actual vector compute and vector memory '
        'operations with in-flight vector state. Restore Level 1 in fresh metasim and '
        'independently restore Level 2 in fresh pre-FAME ordinary RTL VCS, read back '
        'complete state before any edge, and compare captured target-cycle behavior. '
        'Add invalid-image/build/state-owner rejection and first-divergence corruption '
        'cases, preserve existing regressions, and record exact artifacts and '
        'executable native VCS checks in docs/checkpointing/cpu-checkpoint-matrix.md. '
        'Standalone Shuttle and physical FPGA validation are outside the '
        'current task.' + CPU_LIVE_TASK,
        'The exact BOOM recipe passes independently audited complete Level-1 '
        'fresh-process metasim continuation against an uninterrupted workload run, and '
        'complete Level-2 zero-edge state readback plus finite captured-trace replay in'
        ' ordinary RTL VCS. All sampled outputs and transaction timing match at '
        'original target-cycle labels across the required active-workload cuts. '
        'Required malformed/incompatible/incomplete images reject before partial '
        'restore, and actual semantic corruption is detected at its first divergent '
        'boundary. Per-recipe/per-level evidence records workload hashes, exact state '
        'ownership and build settings, tested cuts, native VCS commands and results. '
        'Fixture-only, FCFS-only, boot-only, idle-only and scalar-only Saturn tests '
        'cannot satisfy this milestone.' + CPU_LIVE_ACCEPTANCE,
        ("docs/checkpointing/cpu-checkpoint-matrix.md",),
        needs_vcs=True,
    ),
    Milestone(
        'M13-shuttle-saturn-level1-level2',
        'Implement and validate both Level-1 and Level-2 checkpoint/restore for Shuttle'
        ' + Saturn, using existing recipe '
        'firesim_saturn_GENV256D128_shuttle_singlecore_no_nic_l2_llc4mb_ddr3 from '
        'sims/firesim-staging/sample_config_build_recipes.yaml. Re-read the current '
        'instructions at the top of plan_agent.md. Use exact recipe build settings in '
        'VCS metasim without building an FPGA bitstream. Audit and implement all '
        'CPU/configuration-specific simulator, bridge, host-driver and semantic DUT '
        'state owners; do not assume fcfs-fased-v1 support applies. Test real '
        'self-checking CPU workloads at early, warmed-cache, outstanding-memory and '
        'late cuts. For Rocket exercise all four cores; for BOOM speculative/in-flight '
        'execution; for Shuttle + Saturn actual vector compute and vector memory '
        'operations with in-flight vector state. Restore Level 1 in fresh metasim and '
        'independently restore Level 2 in fresh pre-FAME ordinary RTL VCS, read back '
        'complete state before any edge, and compare captured target-cycle behavior. '
        'Add invalid-image/build/state-owner rejection and first-divergence corruption '
        'cases, preserve existing regressions, and record exact artifacts and '
        'executable native VCS checks in docs/checkpointing/cpu-checkpoint-matrix.md. '
        'Standalone Shuttle and physical FPGA validation are outside the '
        'current task.' + CPU_LIVE_TASK,
        'The exact Shuttle + Saturn recipe passes independently audited complete '
        'Level-1 fresh-process metasim continuation against an uninterrupted workload '
        'run, and complete Level-2 zero-edge state readback plus finite captured-trace '
        'replay in ordinary RTL VCS. All sampled outputs and transaction timing match '
        'at original target-cycle labels across the required active-workload cuts. '
        'Required malformed/incompatible/incomplete images reject before partial '
        'restore, and actual semantic corruption is detected at its first divergent '
        'boundary. Per-recipe/per-level evidence records workload hashes, exact state '
        'ownership and build settings, tested cuts, native VCS commands and results. '
        'Fixture-only, FCFS-only, boot-only, idle-only and scalar-only Saturn tests '
        'cannot satisfy this milestone.' + CPU_LIVE_ACCEPTANCE,
        ("docs/checkpointing/cpu-checkpoint-matrix.md",),
        needs_vcs=True,
    ),
)
