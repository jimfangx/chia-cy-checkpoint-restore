"""Serialize Level-2 public-port banked readout; no DUT handle access."""

from .codec import keys, natural, require
from .semantic import encode_semantic, manifest_hash, validate_manifest


def validate_binding(manifest, binding):
    validate_manifest(manifest)
    keys(binding, {"access_version", "protocol", "dut_root", "state_manifest_sha256", "state"})
    require(type(binding["access_version"]) is int and
            (binding["access_version"], binding["protocol"]) in
            ((1, "banked64-v1"), (2, "banked64-chunked-v2")), "unsupported banked protocol")
    chunked = binding["access_version"] == 2
    require(binding["dut_root"] == manifest["dut_root"]
            and binding["state_manifest_sha256"] == manifest_hash(manifest), "incompatible banked binding")
    require(type(binding["state"]) is list and len(binding["state"]) == len(manifest["state"]),
            "incomplete banked binding")
    slots = []
    for bound, entry in zip(binding["state"], manifest["state"]):
        keys(bound, {"state_id", "bank", "slot", "width", "depth"} |
             ({"chunks", "transfer_width", "transfer_depth"} if chunked else set()))
        for key in ("bank", "slot", "width", "depth"):
            natural(bound[key])
        require((bound["state_id"], bound["width"], bound["depth"]) ==
                (entry["state_id"], entry["width"], entry["depth"]), "banked binding state/shape/order mismatch")
        require(bound["bank"] < 256 and bound["slot"] < 65536 and (chunked or bound["width"] <= 64),
                "unsupported banked state/selector")
        if chunked:
            for key in ("chunks", "transfer_width", "transfer_depth"):
                natural(bound[key])
            chunks = (entry["width"] + 63) // 64
            require(bound["chunks"] == chunks and bound["transfer_width"] == min(entry["width"], 64)
                    and bound["transfer_depth"] == entry["depth"] * chunks
                    and bound["transfer_depth"] <= 2**31 - 1, "incompatible chunk mapping")
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


def transport_shape(binding, entry):
    """Physical descriptor shape after validate_binding, distinct from logical state."""
    return ((entry["transfer_width"], entry["transfer_depth"]) if binding["access_version"] == 2
            else (entry["width"], entry["depth"]))


def encode_chunked_banked(manifest, configuration, cycle, beats):
    """Reassemble address-major, little-endian 64-bit chunks without changing StateIDs.

    Strict full-list validation precedes canonical serialization; final chunk
    padding is checked even though the transport descriptor itself is 64 bits.
    The legacy encode_banked entry point remains deliberately narrow-only.
    """
    validate_manifest(manifest)
    natural(cycle)
    require(type(beats) is list, "beats must be a complete collected list")
    count = sum(e["depth"] * ((e["width"] + 63) // 64) for e in manifest["state"])
    require(len(beats) == count, "incomplete or extra chunked state")
    offset = 0
    records = []
    for index, entry in enumerate(manifest["state"]):
        chunks = (entry["width"] + 63) // 64
        values = []
        for address in range(entry["depth"]):
            value = 0
            for chunk in range(chunks):
                beat = beats[offset]
                keys(beat, {"entry", "address", "width", "data", "error", "last"})
                for key in beat:
                    natural(beat[key])
                require(beat["error"] == 0, "bank reported unsupported/incomplete state")
                require((beat["entry"], beat["address"], beat["width"]) ==
                        (index, address * chunks + chunk, min(entry["width"], 64)),
                        "chunked state metadata/order mismatch")
                require(beat["last"] == int(offset == count - 1), "incorrect end-of-checkpoint marker")
                require(beat["data"] < 1 << min(64, entry["width"] - chunk * 64),
                        "noncanonical final chunk padding")
                value |= beat["data"] << (chunk * 64)
                offset += 1
            values.append(f"{value:0{(entry['width'] + 3) // 4}x}")
        records.append(dict(state_id=entry["state_id"], width=entry["width"], depth=entry["depth"], values=values))
    doc = dict(format_version=1, checkpoint_type="rtlckpt", target_cycle=cycle,
               target_clock_phase="before_rising_edge",
               build=dict(target_configuration=configuration, rtl_build_hash=manifest["reference_sha256"],
                          state_manifest_hash=manifest_hash(manifest)), records=records)
    return encode_semantic(doc, manifest)
