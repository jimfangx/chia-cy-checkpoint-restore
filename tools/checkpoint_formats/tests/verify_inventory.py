"""Cross-language verification of actual compiler artifacts; never fabricates a manifest."""
import copy
import hashlib
import json
import random
import argparse
from pathlib import Path

from tools.checkpoint_formats.codec import FormatError, canonical, encode, decode
from tools.checkpoint_formats.semantic import decode_semantic, encode_semantic, manifest_hash


def verify(directory, basename="InventoryDUT", dut_root="Harness.dut", configuration="InventoryDUT"):
    directory = Path(directory)
    raw = (directory / (basename + ".semantic-state.json")).read_bytes()
    manifest = json.loads(raw)
    assert canonical(manifest) == raw, "Scala/Python canonical JSON disagreement"
    reference = (directory / (basename + ".semantic-reference.fir")).read_bytes()
    assert hashlib.sha256(reference).hexdigest() == manifest["reference_sha256"]
    assert len(manifest["state"]) == 8
    assert manifest["dut_root"] == dut_root
    assert {s["hierarchy"] for s in manifest["state"]} == {
        dut_root + "." + name for name in ("counter", "fsm", "bank_0", "bank_1", "bank_2", "sram", "a.saved", "b.saved")
    }
    for entry in manifest["state"]:
        name = entry["hierarchy"].removeprefix(dut_root + ".")
        assert (entry["kind"], entry["width"], entry["depth"]) == (
            "memory" if name == "sram" else "register", 2 if name == "fsm" else 9, 8 if name == "sram" else 1)
    rng = random.Random(441)
    doc = dict(format_version=1, checkpoint_type="rtlckpt", target_cycle=42,
               target_clock_phase="before_rising_edge",
               build=dict(target_configuration=configuration, rtl_build_hash=manifest["reference_sha256"],
                          state_manifest_hash=manifest_hash(manifest)), records=[])
    for entry in manifest["state"]:
        doc["records"].append(dict(state_id=entry["state_id"], width=entry["width"], depth=entry["depth"],
                                   values=[format(rng.getrandbits(entry["width"]), f"0{(entry['width'] + 3) // 4}x")
                                           for _ in range(entry["depth"])]))
    data = encode_semantic(doc, manifest)
    assert decode_semantic(data, doc["build"], manifest) == doc
    assert encode_semantic(decode_semantic(data, doc["build"], manifest), manifest) == data
    (directory / (basename + ".rtlckpt")).write_bytes(data)
    for byte in range(len(data)):
        for bit in range(8):
            damaged = bytearray(data)
            damaged[byte] ^= 1 << bit
            try:
                decode_semantic(bytes(damaged), doc["build"], manifest)
            except FormatError:
                continue
            raise AssertionError("accepted corrupt semantic checkpoint")
    incomplete = copy.deepcopy(doc)
    incomplete["records"].pop()
    try:
        decode_semantic(encode("rtlckpt", incomplete), doc["build"], manifest)
    except FormatError:
        pass
    else:
        raise AssertionError("accepted omitted state with valid checksum")
    # Independent format artifacts; these are synthetic values, not captured DUT execution.
    for kind, records, builds in (
        ("fsckpt", [dict(owner="test:simulator", width=9, value="101")],
         dict(golden_gate_build_hash="b" * 64, simulator_build_hash="e" * 64, state_manifest_hash="c" * 64)),
        ("trace", [dict(cycle=42, inputs=dict(data=dict(width=9, value="101")),
                        outputs=dict(count=dict(width=9, value="02a")))],
         dict(boundary_manifest_hash="d" * 64)),
    ):
        example = dict(format_version=1, checkpoint_type=kind, target_cycle=42,
                       target_clock_phase="before_rising_edge", records=records,
                       build=dict(target_configuration=configuration, rtl_build_hash=manifest["reference_sha256"], **builds))
        encoded = encode(kind, example)
        assert decode(encoded, kind, example["build"]) == example
        (directory / (basename + "." + kind)).write_bytes(encoded)
    print(f"PASS: compiler's 8-entry manifest, reference hash, complete bit-exact roundtrip, {len(data) * 8} single-bit corruptions, omitted state rejection, independent fsckpt/trace")
    print("Scope: synthetic serialization values; no capture or replay is claimed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--basename", default="InventoryDUT")
    parser.add_argument("--dut-root", default="Harness.dut")
    parser.add_argument("--configuration", default="InventoryDUT")
    args = parser.parse_args()
    verify(args.directory, args.basename, args.dut_root, args.configuration)
