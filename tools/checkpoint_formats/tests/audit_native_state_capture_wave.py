"""Reconstruct the composite owner's readout from original VCD registers.

The oracle observes each underlying owner, never the composite packing ports.
It also binds native staging to the entire preedge vector at the sampling edge.
"""
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require


def audit(path, bits, *, top="native_state_capture_tb.dut", gates=3):
    names = ["phase", "error", "control_state", "clock", "live_state", "snapshot_state"]
    snapshot_registers = ["snapshot." + n for n in ("payload", "occupied", "cut_cycle", "error")]
    physical_registers = ["physical." + n for n in
                          ("freeze_low", "sampled", "release_pending", "captured_ce", "cut_cycle", "error")]
    names += snapshot_registers + physical_registers + ["snapshot.request", "snapshot.request_ready"]
    wanted = {top + "." + n: n for n in names}
    codes, values, scopes, previous = {}, {}, [], {}
    samples = captures = 0
    unknown_captures = 0

    def sample():
        nonlocal previous, samples, captures, unknown_captures
        now = {n: values[c] for n, c in codes.items() if c in values}
        integer = lambda n: int(now[n], 2)
        binary = lambda n: n in now and re.fullmatch("[01]+", now[n])
        owners = names[:2] + snapshot_registers + physical_registers
        if all(binary(n) for n in owners + ["control_state"]):
            staging = integer("snapshot.payload") | integer("snapshot.occupied") << bits
            staging |= integer("snapshot.cut_cycle") << (bits + 1)
            staging |= integer("snapshot.error") << (bits + 65)
            physical = integer("physical.freeze_low") | integer("physical.sampled") << 1
            physical |= integer("physical.release_pending") << 2
            physical |= integer("physical.captured_ce") << 3
            physical |= integer("physical.cut_cycle") << (gates + 3)
            physical |= integer("physical.error") << (gates + 67)
            packed = staging | physical << (bits + 71)
            packed |= integer("phase") << (bits + gates + 141)
            packed |= integer("error") << (bits + gates + 144)
            require(integer("control_state") == packed, "composite readout omits/changes original register bits")
            require(now["snapshot_state"].zfill(bits) == now["snapshot.payload"].zfill(bits),
                    "snapshot output differs from underlying original payload")
            samples += 1
        if (now.get("clock") == "1" and previous.get("clock") == "0" and
                previous.get("snapshot.request") == previous.get("snapshot.request_ready") == "1"):
            require("snapshot.payload" in now and "live_state" in previous, "missing sampled vector")
            require(now["snapshot.payload"].zfill(bits) == previous["live_state"].zfill(bits),
                    "snapshot did not stage every preedge live bit")
            captures += 1
            unknown_captures += bool(re.search("[xz]", previous["live_state"]))
        previous = now

    for line in Path(path).read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "$scope":
            scopes.append(parts[2])
        elif parts[0] == "$upscope":
            scopes.pop()
        elif parts[0] == "$var":
            n = ".".join(scopes + [parts[4].lstrip("\\")])
            if n in wanted:
                codes[wanted[n]] = parts[3]
        elif line.startswith("#"):
            sample()
        elif line[0] in "bB" and len(parts) == 2:
            values[parts[1]] = parts[0][1:].lower()
        elif line[0] in "01xXzZ":
            values[line[1:].strip()] = line[0].lower()
    sample()
    require(codes.keys() == set(names), "missing complete original composite owner waveform")
    require(samples > 0, "no complete binary original-owner readback")
    return dict(original_register_vectors=12, samples=samples, captures=captures,
                unknown_captures=unknown_captures, complete_fpga_capture=False)
