"""Audit native gate SAIF against mapped storage and the same-run VCD.

This is an activity audit, not a power estimator. The supported VCD contains
scalar/vector wires and registers, ascending/descending packed indices and
unpacked memory words emitted by VCS. Unsupported encodings fail explicitly.
"""

from decimal import Decimal
import re

from .codec import require


def unescape(name):
    return re.sub(r"\\(.)", r"\1", name)


def read_saif(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|(?:\\.|[^\s()])+', text)
    stack, roots = [], []
    for token in tokens:
        if token == "(":
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            require(bool(stack), "malformed SAIF parentheses")
            stack.pop()
        else:
            require(bool(stack), "unexpected SAIF text")
            stack[-1].append(token)
    require(not stack and len(roots) == 1 and roots[0][0] == "SAIFILE", "invalid SAIF root")
    root = roots[0]
    header = {row[0]: row[1:] for row in root[1:] if row[0] != "INSTANCE"}
    require(header.get("DIRECTION") == ['"backward"'] and header.get("SAIFVERSION") == ['"2.0"'],
            "unsupported SAIF direction/version")
    require(header.get("TIMESCALE") == ["1", "ns"], "unsupported SAIF timescale")
    require('VCS Y-2026.03-SP1_Full64' in " ".join(header.get("PROGRAM_NAME", [])),
            "SAIF did not originate in pinned VCS")
    duration = Decimal(header["DURATION"][0]) * 1000
    require(duration > 0, "empty activity duration")
    nets = {}

    def walk(node, path):
        require(node[0] == "INSTANCE" and len(node) >= 2, "malformed SAIF instance")
        path = (*path, unescape(node[1]))
        for row in node[2:]:
            if row[0] == "INSTANCE":
                walk(row, path)
            else:
                require(row[0] in ("NET", "PORT"), "unsupported SAIF instance data")
                for signal in row[1:]:
                    key = ".".join((*path, unescape(signal[0])))
                    require(key not in nets, "duplicate SAIF signal")
                    metrics = {entry[0]: Decimal(entry[1]) for entry in signal[1:]}
                    require(len(metrics) == len(signal)-1 and set(metrics) == {"T0", "T1", "TX", "TC", "IG"}
                            and all(v >= 0 for v in metrics.values()), "unsupported SAIF metrics")
                    require(metrics["TC"] == int(metrics["TC"]) and metrics["IG"] == int(metrics["IG"]),
                            "fractional SAIF transition count")
                    require(sum(metrics[k] for k in ("T0", "T1", "TX"))*1000 == duration,
                            "SAIF dwell times do not sum to window duration")
                    nets[key] = {k: int(v) if k in ("TC", "IG") else v*1000 for k, v in metrics.items()}
    instances = [row for row in root[1:] if row[0] == "INSTANCE"]
    require(len(instances) == 1 and instances[0][1] == "tb", "incorrect SAIF simulation root")
    walk(instances[0], ())
    require(nets and all(name.startswith("tb.dut.") for name in nets), "activity outside gate DUT")
    return duration, nets


def read_vcd(text, start, end):
    require(0 <= start < end, "invalid VCD activity window")
    header, body = text.split("$enddefinitions $end", 1)
    require(re.search(r"\$timescale\s+1ps\s+\$end", header) and
            "VCS version Y-2026.03-SP1_Full64" in header, "unsupported VCD producer/timescale")
    scopes, codes, paths = [], {}, {}
    for line in header.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "$scope":
            require(parts[1] == "module", "unsupported VCD scope")
            scopes.append(parts[2].lstrip("\\"))
        elif parts[0] == "$upscope":
            require(scopes, "invalid VCD scope nesting")
            scopes.pop()
        elif parts[0] == "$var":
            require(parts[1] in ("wire", "reg"), "unsupported VCD value type")
            width, code, name = int(parts[2]), parts[3], parts[4].lstrip("\\")
            suffix = parts[5:-1]
            require(width > 0 and len(suffix) <= 1, "unsupported VCD variable geometry")
            if suffix:
                match = re.fullmatch(r"\[(-?\d+)(?::(-?\d+))?\]", suffix[0])
                require(match is not None, "unsupported VCD packed indices")
                left = int(match[1]); right = int(match[2]) if match[2] else left
                indices = list(range(left, right + (1 if right >= left else -1), 1 if right >= left else -1))
                require(len(indices) == width, "VCD width/index mismatch")
            else:
                indices = list(reversed(range(width))) if width > 1 else [None]
            require(code not in codes or codes[code]["width"] == width, "VCD alias width mismatch")
            codes.setdefault(code, dict(width=width, values=[]))
            for position, bit in enumerate(indices):
                path = ".".join((*scopes, name)) + (f"[{bit}]" if bit is not None else "")
                require(path not in paths, "duplicate VCD path")
                paths[path] = (code, position)
    require(not scopes and paths and all(p.startswith("tb.dut.") for p in paths), "incorrect gate VCD scope")
    time = None
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("$"):
            continue
        if line.startswith("#"):
            stamp = int(line[1:])
            require(time is None or stamp >= time, "VCD time reversed")
            time = stamp
        else:
            require(time is not None and start <= time <= end, "VCD includes initialization or out-of-window activity")
            if line[0].lower() == "b":
                value, code = line[1:].split()
            else:
                require(line[0].lower() in "01xz", "unsupported VCD value")
                value, code = line[0], line[1:]
            require(code in codes and re.fullmatch("[01xXzZ]+", value), "unknown VCD code/value")
            width = codes[code]["width"]
            require(len(value) <= width, "oversized VCD vector")
            value = value.lower().rjust(width, value[0].lower() if value[0].lower() in "xz" else "0")
            codes[code]["values"].append((time, value))
    result = {}
    for path, (code, position) in paths.items():
        events = codes[code]["values"]
        require(events and events[0][0] == start, "missing initial VCD value")
        state, previous = None, start
        metrics = dict(T0=0, T1=0, TX=0, TC=0)
        for stamp, value in events:
            bit = value[position]
            if state is not None:
                metrics["T" + state if state in "01" else "TX"] += stamp-previous
                if state in "01" and bit in "01" and state != bit:
                    metrics["TC"] += 1
            state, previous = bit, stamp
        metrics["T" + state if state in "01" else "TX"] += end-previous
        result[path] = metrics
    return result


def audit_activity(saif_text, vcd_text, mapping, start, end, samples, witnesses=None):
    duration, saif = read_saif(saif_text)
    require(duration == end-start == 3000*samples, "incorrect gate activity window")
    vcd = read_vcd(vcd_text, start, end)
    storage = set()
    for entry in mapping["entries"]:
        for gate in entry["gates"]:
            path = f"tb.dut.{gate['instance']}.{gate['storage']}"
            if gate.get("width", 1) > 1:
                path += f"[{gate['bit']}]"
            storage.add(path)
    require(len(storage) == mapping["gate_storage_bits"], "activity inventory is incomplete")
    witnesses = witnesses or {}
    require(set(witnesses) <= storage, "unknown memory activity witness")
    for path in storage | {"tb.dut.clock"}:
        vcd_path = witnesses.get(path, path)
        require(path in saif and vcd_path in vcd, f"mapped gate activity absent: {path}")
        require(saif[path]["TX"] == 0 and vcd[vcd_path]["TX"] == 0, f"unknown gate state activity: {path}")
        require(all(saif[path][metric] == vcd[vcd_path][metric] for metric in ("T0", "T1", "TX", "TC")),
                f"SAIF/VCD activity mismatch: {path}")
    require(saif["tb.dut.clock"]["TC"] == 2*samples, "incorrect gate clock switching")
    toggles = sum(saif[path]["TC"] for path in storage)
    require(toggles > 0, "no actual gate storage switching")
    return dict(duration_ps=int(duration), mapped_storage_bits=len(storage),
                storage_transitions=toggles, clock_transitions=2*samples,
                native_saif_signals=len(saif), vcd_signals=len(vcd),
                vcd_memory_witness_bits=len(witnesses),
                mapped_storage_saif_vcd_equal=True)
