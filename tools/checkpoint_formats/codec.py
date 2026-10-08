"""Strict, deterministic v1 checkpoint containers (no capture/restore backend)."""

import hashlib
import json
import re
import struct


class FormatError(ValueError):
    """Invalid, unsupported, corrupt, or incompatible checkpoint."""


MAGIC = {"fsckpt": b"FSCKPT\x00\x01", "rtlckpt": b"RTLCKP\x00\x01", "trace": b"TRACE\x00\x00\x01"}
BUILD_KEYS = {
    "fsckpt": {"target_configuration", "rtl_build_hash", "golden_gate_build_hash", "state_manifest_hash"},
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


def validate(kind, doc):
    require(kind in MAGIC, "unknown checkpoint type")
    keys(doc, {"format_version", "checkpoint_type", "target_cycle", "target_clock_phase", "build", "records"})
    require(type(doc["format_version"]) is int and doc["format_version"] == 1, "unsupported version")
    require(doc["checkpoint_type"] == kind, "checkpoint type mismatch")
    natural(doc["target_cycle"])
    require(doc["target_clock_phase"] == "before_rising_edge", "unsupported clock phase")
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
            keys(record, {"cycle", "inputs", "outputs"})
            natural(record["cycle"])
            require(record["cycle"] == doc["target_cycle"] + len(identities), "trace must cover consecutive target cycles")
            for direction in ("inputs", "outputs"):
                require(type(record[direction]) is dict, "boundary signals must be an object")
                for signal, value in record[direction].items():
                    require(type(signal) is str and signal, "invalid boundary signal")
                    keys(value, {"width", "value"})
                    bit_value(value)
            identities.append(record["cycle"])
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
