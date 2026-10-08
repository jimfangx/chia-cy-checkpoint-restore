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
)
