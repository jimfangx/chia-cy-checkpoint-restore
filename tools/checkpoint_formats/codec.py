"""Strict checkpoint containers with v1 cycle or v2 clock-event payloads."""

import hashlib
import json
import re
import struct


class FormatError(ValueError):
    """Invalid, unsupported, corrupt, or incompatible checkpoint."""


MAGIC = {"fsckpt": b"FSCKPT\x00\x01", "rtlckpt": b"RTLCKP\x00\x01", "trace": b"TRACE\x00\x00\x01"}
BUILD_KEYS = {
    "fsckpt": {"target_configuration", "rtl_build_hash", "golden_gate_build_hash", "simulator_build_hash", "state_manifest_hash"},
    "rtlckpt": {"target_configuration", "rtl_build_hash", "state_manifest_hash"},
    "trace": {"target_configuration", "rtl_build_hash", "boundary_manifest_hash"},
}
HEX = re.compile(r"[0-9a-f]+\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")


def require(condition, message):
    if not condition:
        raise FormatError(message)


def keys(obj, expected):
    require(type(obj) is dict and set(obj) == set(expected), "missing or unknown fields")


def natural(value):
    require(type(value) is int and value >= 0, "expected nonnegative integer")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def bit_value(record):
    natural(record["width"])
    require(record["width"] > 0, "zero-width state unsupported")
    value = record["value"]
    require(type(value) is str and HEX.fullmatch(value), "unknown/X/Z or non-hex state unsupported")
    require(len(value) == (record["width"] + 3) // 4, "incorrect bit-vector length")
    require(int(value, 16).bit_length() <= record["width"], "nonzero padding bits")


def event_phase(phase, cycle):
    """Version 2 cuts are settled, all-low boundaries before an explicit event.

    Counts are completed rising edges, never inferred from frequency or from
    the number of event rows. Input changes settle before output sampling;
    all clock transitions in a row are then applied together.
    """
    keys(phase, {"event_index", "cycle_clock", "clock_levels", "rising_edges"})
    natural(phase["event_index"])
    levels, counts = phase["clock_levels"], phase["rising_edges"]
    require(type(levels) is dict and levels and type(counts) is dict and set(levels) == set(counts),
            "incomplete event-phase clock ownership")
    require(type(phase["cycle_clock"]) is str and phase["cycle_clock"] in levels, "unknown cycle clock")
    for clock, level in levels.items():
        require(type(clock) is str and clock and type(level) is int and level == 0,
                "event-phase cut requires all clocks low")
        natural(counts[clock])
    require(cycle == counts[phase["cycle_clock"]] and
            all(2 * count <= phase["event_index"] for count in counts.values()),
            "inconsistent event-phase cycle counts")


def validate(kind, doc):
    require(kind in MAGIC, "unknown checkpoint type")
    require(type(doc) is dict, "checkpoint must be an object")
    version = doc.get("format_version")
    multi = type(version) is int and version == 2
    keys(doc, {"format_version", "checkpoint_type", "target_cycle", "target_clock_phase", "build", "records"} |
         ({"event_phase"} if multi else set()))
    require(type(version) is int and version in (1, 2) and (not multi or kind != "fsckpt"), "unsupported version")
    require(doc["checkpoint_type"] == kind, "checkpoint type mismatch")
    natural(doc["target_cycle"])
    require(doc["target_clock_phase"] == ("before_clock_event" if multi else "before_rising_edge"),
            "unsupported clock phase")
    if multi:
        event_phase(doc["event_phase"], doc["target_cycle"])
        levels = dict(doc["event_phase"]["clock_levels"])
        counts = dict(doc["event_phase"]["rising_edges"])
    keys(doc["build"], BUILD_KEYS[kind])
    for key, value in doc["build"].items():
        require(type(value) is str and value, "empty build identity")
        if key.endswith("_hash"):
            require(HASH.fullmatch(value), "expected SHA-256 build hash")
    require(type(doc["records"]) is list, "records must be an array")
    identities = []
    for record in doc["records"]:
        if kind == "rtlckpt":
            keys(record, {"state_id", "width", "depth", "values"})
            require(type(record["state_id"]) is str and HASH.fullmatch(record["state_id"]), "invalid semantic StateID")
            natural(record["depth"])
            require(record["depth"] > 0, "zero-depth state unsupported")
            require(type(record["values"]) is list and len(record["values"]) == record["depth"], "memory depth mismatch")
            for value in record["values"]:
                bit_value({"width": record["width"], "value": value})
            identities.append(record["state_id"])
        elif kind == "fsckpt":
            keys(record, {"owner", "width", "value"})
            require(type(record["owner"]) is str and record["owner"], "invalid simulator owner")
            bit_value(record)
            identities.append(record["owner"])
        else:
            keys(record, {"cycle", "inputs", "outputs"} | ({"event_index", "clock_levels"} if multi else set()))
            natural(record["cycle"])
            if multi:
                natural(record["event_index"])
                require(record["event_index"] == doc["event_phase"]["event_index"] + len(identities),
                        "trace must cover consecutive clock events")
                require(record["cycle"] == counts[doc["event_phase"]["cycle_clock"]],
                        "trace cycle does not match completed clock edges")
                next_levels = record["clock_levels"]
                require(type(next_levels) is dict and set(next_levels) == set(levels) and
                        all(type(v) is int and v in (0, 1) for v in next_levels.values()),
                        "incomplete or invalid event clocks")
                require(next_levels != levels, "clock event has no transitions")
                for clock in levels:
                    counts[clock] += int(levels[clock] == 0 and next_levels[clock] == 1)
                levels = dict(next_levels)
            else:
                require(record["cycle"] == doc["target_cycle"] + len(identities), "trace must cover consecutive target cycles")
            for direction in ("inputs", "outputs"):
                require(type(record[direction]) is dict, "boundary signals must be an object")
                for signal, value in record[direction].items():
                    require(type(signal) is str and signal, "invalid boundary signal")
                    keys(value, {"width", "value"})
                    bit_value(value)
            identities.append(record["event_index"] if multi else record["cycle"])
    require(identities == sorted(set(identities)), "duplicate or unsorted records")


def encode(kind, doc):
    validate(kind, doc)
    payload = canonical(doc)
    header = MAGIC[kind] + struct.pack(">Q", len(payload))
    return header + payload + hashlib.sha256(header + payload).digest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def decode(data, kind, expected_build):
    """Verify integrity and exact build identity before returning any state."""
    require(kind in MAGIC, "unknown checkpoint type")
    require(len(data) >= 48 and data[:8] == MAGIC[kind], "wrong magic/type/version or truncated header")
    size = struct.unpack(">Q", data[8:16])[0]
    require(len(data) == 16 + size + 32, "checkpoint size mismatch")
    require(hashlib.sha256(data[:-32]).digest() == data[-32:], "checksum mismatch")
    try:
        doc = json.loads(data[16:-32], object_pairs_hook=unique_object)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise FormatError("invalid JSON payload") from exc
    validate(kind, doc)
    require(canonical(doc) == data[16:-32], "noncanonical payload")
    keys(expected_build, BUILD_KEYS[kind])
    require(doc["build"] == expected_build, "incompatible build or manifest")
    return doc
