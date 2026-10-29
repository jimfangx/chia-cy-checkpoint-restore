"""Independent VCD audit of original snapshot registers and restore permissions."""
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require


def audit(path, bits, *, loads=1, broken=False):
    top = "native_snapshot_restore_tb."
    signals = {n: top + n for n in ("clock", "reset", "restore_hold", "restore_load", "restore_state",
        "restore_ready", "valid", "borrow_enable", "request_ready", "word_error", "word_data", "control_state")}
    signals.update({n: top + "dut." + n for n in ("payload", "occupied", "cut_cycle", "error")})
    codes, values, scopes, previous = {}, {}, [], {}
    accepted = held = running = 0
    initialized = False
    first = None

    def sample():
        nonlocal previous, accepted, held, running, initialized, first
        now = {name: int(values[code], 2) for name, code in codes.items()
               if re.fullmatch("[01]+", values.get(code, "x"))}
        if now.get("clock") == 1 and previous.get("clock") == 0:
            p = previous
            load = p.get("restore_load") == p.get("restore_ready") == 1 and not p.get("reset")
            if p.get("restore_hold") or p.get("restore_load") or p.get("reset"):
                require(all(p.get(n) == 0 for n in ("valid", "borrow_enable", "request_ready", "word_data"))
                        and p.get("word_error") == 1, "parked/restoring owner acknowledged an interface")
            if p.get("reset") or load:
                initialized = True
            if not initialized:
                require(p.get("restore_hold") == 1, "fresh owner advanced before initial load/reset")
                previous = now
                return
            require(all(n in now for n in ("payload", "occupied", "cut_cycle", "error", "control_state")),
                    "unknown original register after owner initialization")
            packed = now["payload"] | now["occupied"] << bits | now["cut_cycle"] << (bits + 1) | now["error"] << (bits + 65)
            require(now["control_state"] == packed, "control readback omits original owner storage")
            if p.get("reset"):
                require(packed == 0, "reset did not clear every original snapshot register")
            elif load:
                require(p.get("restore_hold") == 1, "accepted load outside parked destination")
                diff = packed ^ p["restore_state"]
                if diff:
                    require(broken, "partial original snapshot-owner restore")
                    if first is None:
                        first = dict(canonical_bit=(diff & -diff).bit_length() - 1,
                                     enabled_edges_before=running, read_acknowledged=False)
                accepted += 1
            elif p.get("restore_hold") or p.get("restore_load"):
                require(now["payload"] == p["payload"] and now["occupied"] == p["occupied"] and
                        now["cut_cycle"] == p["cut_cycle"], "held/rejected transaction changed payload/label")
                held += 1
            else:
                running += 1
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
            name = ".".join(scopes + [parts[4].lstrip("\\")])
            for role, target in signals.items():
                if name == target:
                    codes[role] = parts[3]
        elif line.startswith("#"):
            sample()
        elif line[0] in "bB" and len(parts) == 2:
            values[parts[1]] = parts[0][1:].lower()
        elif line[0] in "01xXzZ":
            values[line[1:].strip()] = line[0].lower()
    sample()
    require(codes.keys() == signals.keys(), "missing original owner wave fields " + str(signals.keys() - codes.keys()))
    require(accepted == loads, "incomplete independent full-owner load waveform")
    if broken:
        require(first == dict(canonical_bit=0, enabled_edges_before=0, read_acknowledged=False),
                "compiled semantic fault escaped first original-register load")
    else:
        require(first is None and held >= 8, "incomplete parked snapshot-owner waveform")
    return dict(original_registers=4, bits=bits + 71, accepted_loads=accepted,
                held_edges=held, enabled_raw_edges=running, first_divergence=first)
