"""Ordered, independently verifiable work for plan_agent.md.

The FPGA bring-up milestone is deliberately absent: this machine has no FPGA.
The metasim and ordinary RTL paths remain separate throughout the loop.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Milestone:
    name: str
    task: str
    acceptance: str
    required_files: tuple[str, ...] = ()
    needs_vcs: bool = False


MILESTONES = (
    Milestone(
        "M0-reconnaissance",
        "Trace the current Golden Gate pass order, semantic state before FAME, "
        "generated simulator state, bridges, DMA, FASED, host drivers, VCS "
        "metasim targets, and available ASIC/formal tools. Record exact source "
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
        "M8-formal-state-map",
        "Use an available formal equivalence tool to prove original RTL to ASIC "
        "netlist state correspondence, with retiming disabled initially. Export "
        "a build-bound StateID-to-gate map; reject unproven or unmappable state.",
        "A small synthesized DUT has a complete validated mapping, including "
        "polarity, reordering, duplication, optimization, and memory cases.",
    ),
    Milestone(
        "M9-gate-level-replay",
        "Load semantic state through the formally validated map into fresh "
        "gate-level VCS, replay recorded inputs, compare outputs, and produce "
        "SAIF from the actual netlist. Run power analysis only when suitable "
        "libraries and a power tool are available.",
        "Restored gate-level replay matches continuous gate-level simulation "
        "at sampled cycles and generates real gate-level switching activity.",
        needs_vcs=True,
    ),
    Milestone(
        "M10-production-dut-formal-map",
        "Extend the M8 formal mapping and M9 gate replay flow to the actual "
        "pre-FAME DUT used by the completed M6/M7 metasim workflows. Start with "
        "AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config and its existing "
        "semantic-clean RTL, StateID manifest, boundary manifest, metasim-captured "
        ".rtlckpt and .trace. Read docs/checkpointing/m6-restored-live-shadow.md, "
        "m7-dessert-replay.md, m8-formal-state-map.md and m9-gate-level-replay.md. "
        "Synthesize the complete selected DUT with retiming disabled; implement "
        "the hierarchy, cell and memory adapters needed to prove and export a "
        "complete build-bound semantic StateID-to-gate map. Cover all captured "
        "registers, memory contents, pipeline and port state. Use real installed "
        "CAD tools and suitable cell/memory models, preserving every proof "
        "obligation and explicitly rejecting unsupported or unproven state. "
        "Small synthetic fixtures may support development but cannot satisfy "
        "this milestone. Validate the map by restoring the actual metasim "
        "checkpoint into fresh gate-level VCS and replaying its recorded trace. "
        "FPGA hardware is not a dependency for synthesis, formal mapping or "
        "gate replay. Power characterization is needed only for power analysis. "
        "Preserve completed milestone progress and write recovery details in "
        "docs/checkpointing/m10-production-dut-formal-map.md.",
        "The selected real metasim DUT has a complete independently audited "
        "formal state map bound to its exact RTL, netlist, models and semantic "
        "manifest. Fresh gate-level VCS initializes and reads back all mapped "
        "state before any target edge, replays the actual metasim-captured trace, "
        "matches every sampled output against ordinary RTL replay, and detects "
        "a deliberate mapped-state corruption at its first divergent cycle. "
        "Missing state or unproven mappings reject explicitly; fixture-only "
        "results cannot mark this milestone ready.",
        ("docs/checkpointing/m10-production-dut-formal-map.md",),
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
        'Standalone Shuttle, physical FPGA validation and ASIC power are outside the '
        'current task.',
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
        'cannot satisfy this milestone.',
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
        'Standalone Shuttle, physical FPGA validation and ASIC power are outside the '
        'current task.',
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
        'cannot satisfy this milestone.',
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
        'Standalone Shuttle, physical FPGA validation and ASIC power are outside the '
        'current task.',
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
        'cannot satisfy this milestone.',
        ("docs/checkpointing/cpu-checkpoint-matrix.md",),
        needs_vcs=True,
    ),
)
