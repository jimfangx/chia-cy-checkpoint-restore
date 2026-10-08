"""Manifest-bound Level-2 codec. Low-level codec.py only validates containers."""

import hashlib
import re

from .codec import HASH, canonical, decode, encode, keys, natural, require


PATH = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*(?:\.[A-Za-z_][A-Za-z0-9_$]*)*\Z")


def state_id(hierarchy, kind):
    return hashlib.sha256(canonical(dict(hierarchy=hierarchy, kind=kind,
                                         namespace="pre-fame-state-v1"))).hexdigest()


def validate_manifest(manifest):
    keys(manifest, {"manifest_version", "manifest_type", "identity_scheme", "circuit", "dut_root",
                    "clock_domain", "reference_sha256", "state"})
    require(type(manifest["manifest_version"]) is int and manifest["manifest_version"] == 1,
            "unsupported semantic manifest version")
    require(manifest["manifest_type"] == "rtlckpt", "wrong semantic manifest type")
    require(manifest["identity_scheme"] == "pre-fame-state-v1", "unsupported StateID scheme")
    for key in ("circuit", "dut_root", "clock_domain"):
        require(type(manifest[key]) is str and PATH.fullmatch(manifest[key]), "invalid semantic path")
    root = manifest["dut_root"]
    require(root.split(".")[0] == manifest["circuit"], "DUT root outside circuit")
    require(manifest["clock_domain"].startswith(root + "."), "clock outside selected DUT")
    require(type(manifest["reference_sha256"]) is str and HASH.fullmatch(manifest["reference_sha256"]),
            "invalid reference circuit hash")
    require(type(manifest["state"]) is list and manifest["state"], "empty semantic inventory")
    identities, paths = [], []
    for entry in manifest["state"]:
        keys(entry, {"state_id", "hierarchy", "kind", "width", "depth", "signed", "clock_domain",
                     "reset", "bit_order", "address_order"})
        require(type(entry["hierarchy"]) is str and PATH.fullmatch(entry["hierarchy"])
                and entry["hierarchy"].startswith(root + "."), "state outside selected DUT")
        require(entry["kind"] in ("register", "memory"), "unsupported state kind")
        for key in ("width", "depth"):
            natural(entry[key])
            require(0 < entry[key] <= 2**31 - 1, "unsupported state shape")
        require(entry["kind"] != "register" or entry["depth"] == 1, "register depth must be one")
        require(type(entry["signed"]) is bool, "invalid signedness")
        require(entry["clock_domain"] == manifest["clock_domain"], "multiple target clocks unsupported")
        require(entry["reset"] in ("none", "synchronous"), "unsupported reset semantics")
        require(entry["kind"] != "memory" or entry["reset"] == "none", "memory reset unsupported")
        require(entry["bit_order"] == "lsb0" and entry["address_order"] == "ascending_zero_based",
                "unsupported state ordering")
        require(entry["state_id"] == state_id(entry["hierarchy"], entry["kind"]), "invalid derived StateID")
        identities.append(entry["state_id"])
        paths.append(entry["hierarchy"])
    require(identities == sorted(set(identities)), "duplicate or unsorted manifest IDs")
    require(len(paths) == len(set(paths)), "duplicate semantic state path")


def manifest_hash(manifest):
    validate_manifest(manifest)
    return hashlib.sha256(canonical(manifest)).hexdigest()


def validate_records(doc, manifest):
    require(doc["build"]["state_manifest_hash"] == manifest_hash(manifest), "semantic manifest hash mismatch")
    expected = {entry["state_id"]: (entry["width"], entry["depth"]) for entry in manifest["state"]}
    actual = {record["state_id"]: (record["width"], record["depth"]) for record in doc["records"]}
    require(actual == expected, "incomplete, unknown, or wrong-shaped semantic state")


def encode_semantic(doc, manifest):
    data = encode("rtlckpt", doc)
    validate_records(doc, manifest)
    return data


def decode_semantic(data, expected_build, manifest):
    """Return values only after integrity, compatibility, and complete membership checks."""
    doc = decode(data, "rtlckpt", expected_build)
    validate_records(doc, manifest)
    return doc
