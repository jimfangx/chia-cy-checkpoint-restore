"""Serialize Level-2 public-port banked readout; no DUT handle access."""

from .codec import keys, natural, require
from .semantic import encode_semantic, manifest_hash, validate_manifest


def validate_binding(manifest, binding):
    validate_manifest(manifest)
    keys(binding, {"access_version", "protocol", "dut_root", "state_manifest_sha256", "state"})
    require(type(binding["access_version"]) is int and binding["access_version"] == 1
            and binding["protocol"] == "banked64-v1", "unsupported banked protocol")
    require(binding["dut_root"] == manifest["dut_root"]
            and binding["state_manifest_sha256"] == manifest_hash(manifest), "incompatible banked binding")
    require(type(binding["state"]) is list and len(binding["state"]) == len(manifest["state"]),
            "incomplete banked binding")
    slots = []
    for bound, entry in zip(binding["state"], manifest["state"]):
        keys(bound, {"state_id", "bank", "slot", "width", "depth"})
        for key in ("bank", "slot", "width", "depth"):
            natural(bound[key])
        require((bound["state_id"], bound["width"], bound["depth"]) ==
                (entry["state_id"], entry["width"], entry["depth"]), "banked binding state/shape/order mismatch")
        require(bound["bank"] < 256 and bound["slot"] < 65536 and bound["width"] <= 64,
                "unsupported banked state/selector")
        slots.append((bound["bank"], bound["slot"]))
    require(len(set(slots)) == len(slots), "duplicate banked client slot")


def encode_banked(manifest, configuration, cycle, beats):
    """Fail closed before emitting a file on errors, omissions or reordering.

    The entry number is the manifest's StateID-sorted ordinal. Memory addresses
    are logical word addresses. Current hardware supports one <=64-bit word
    per beat; wider state must be rejected rather than truncated.
    """
    validate_manifest(manifest)
    natural(cycle)
    require(type(beats) is list, "beats must be a complete collected list")
    expected = [(index, address, entry) for index, entry in enumerate(manifest["state"])
                for address in range(entry["depth"])]
    require(all(e["width"] <= 64 for e in manifest["state"]), "wide state requires chunking; unsupported")
    require(len(beats) == len(expected), "incomplete or extra banked state")
    records = [dict(state_id=e["state_id"], width=e["width"], depth=e["depth"], values=[])
               for e in manifest["state"]]
    for offset, (beat, (index, address, entry)) in enumerate(zip(beats, expected)):
        keys(beat, {"entry", "address", "width", "data", "error", "last"})
        for key in beat:
            natural(beat[key])
        require(beat["error"] == 0, "bank reported unsupported/incomplete state")
        require((beat["entry"], beat["address"], beat["width"]) == (index, address, entry["width"]),
                "banked state metadata/order mismatch")
        require(beat["last"] == int(offset == len(expected) - 1), "incorrect end-of-checkpoint marker")
        require(beat["data"] < 1 << entry["width"], "banked state exceeds semantic width")
        records[index]["values"].append(f"{beat['data']:0{(entry['width'] + 3) // 4}x}")
    doc = dict(format_version=1, checkpoint_type="rtlckpt", target_cycle=cycle,
               target_clock_phase="before_rising_edge",
               build=dict(target_configuration=configuration, rtl_build_hash=manifest["reference_sha256"],
                          state_manifest_hash=manifest_hash(manifest)), records=records)
    return encode_semantic(doc, manifest)
