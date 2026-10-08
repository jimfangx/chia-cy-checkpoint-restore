"""Level-1 generated-RTL inventory and diagnostic VCS probes.

These snapshots deliberately are NOT .fsckpt files: host drivers, metasim
transport/harness, functional DRAM and a consistent runtime cut are required
before complete simulator checkpoints can be published or restored.
"""

import hashlib
import json
from pathlib import Path
import re

from .codec import HASH, bit_value, canonical, keys, natural, require
from .replay import IDENT, RANGE, modules


def validate_generated_manifest(manifest):
    keys(manifest, {"manifest_version", "manifest_type", "identity_scheme", "circuit", "root_module",
                    "scope", "external_runtime_required", "reference_sha256", "instances", "state"})
    require(type(manifest["manifest_version"]) is int and manifest["manifest_version"] == 1,
            "unsupported generated manifest version")
    require(manifest["manifest_type"] == "fsckpt-generated"
            and manifest["identity_scheme"] == "generated-simulator-state-v1"
            and manifest["scope"] == "generated_rtl_only"
            and manifest["external_runtime_required"] is True, "invalid Level-1 generated scope")
    for name in ("circuit", "root_module"):
        require(type(manifest[name]) is str and re.fullmatch(IDENT, manifest[name]), "invalid root module")
    require(type(manifest["reference_sha256"]) is str and HASH.fullmatch(manifest["reference_sha256"]),
            "invalid reference hash")
    require(type(manifest["instances"]) is list and manifest["instances"], "empty instance inventory")
    instances = {}
    for item in manifest["instances"]:
        keys(item, {"hierarchy", "module", "implementation_sha256"})
        require(type(item["hierarchy"]) is str and all(re.fullmatch(IDENT, p) for p in item["hierarchy"].split(".")),
                "invalid instance hierarchy")
        require(type(item["module"]) is str and re.fullmatch(IDENT, item["module"]), "invalid module")
        require(type(item["implementation_sha256"]) is str and HASH.fullmatch(item["implementation_sha256"]),
                "invalid implementation hash")
        require(item["hierarchy"] not in instances, "duplicate instance")
        instances[item["hierarchy"]] = item
    require(list(instances) == sorted(instances), "unsorted instances")
    root = manifest["root_module"]
    require(root in instances and instances[root]["module"] == root, "missing root instance")
    require(all(p == root or p.rsplit(".", 1)[0] in instances for p in instances), "orphan instance")
    require(type(manifest["state"]) is list and manifest["state"], "empty generated state")
    ids, paths = [], []
    for entry in manifest["state"]:
        keys(entry, {"state_id", "hierarchy", "module", "kind", "width", "depth", "signed",
                     "clock_expression", "reset_expression", "adapter", "bit_order", "address_order"})
        path = entry["hierarchy"]
        require(type(path) is str and all(re.fullmatch(IDENT, p) for p in path.split(".")), "invalid state hierarchy")
        owner = path.rsplit(".", 1)[0]
        require(owner in instances and entry["module"] == instances[owner]["module"], "missing state owner")
        require(entry["kind"] in ("register", "memory"), "unsupported generated state kind")
        expected = hashlib.sha256(canonical(dict(hierarchy=path, kind=entry["kind"],
                                                namespace="generated-simulator-state-v1"))).hexdigest()
        require(entry["state_id"] == expected, "generated StateID mismatch")
        for name in ("width", "depth"):
            natural(entry[name])
            require(0 < entry[name] <= 2**31 - 1, "unsupported generated state shape")
        require(entry["kind"] == "memory" or entry["depth"] == 1, "register depth mismatch")
        require(type(entry["signed"]) is bool and entry["bit_order"] == "lsb0"
                and entry["address_order"] == "ascending_zero_based", "unsupported bit/address ordering")
        for name in ("clock_expression", "reset_expression"):
            require(type(entry[name]) is str and entry[name], "missing clock/reset metadata")
        require(entry["adapter"] in ("firrtl-register-v1", "firrtl-memory-v1",
                                     "abstract-clock-gate-v1", "metasim-bufgce-v1"), "unknown state adapter")
        require((entry["kind"] == "memory") == (entry["adapter"] == "firrtl-memory-v1"), "adapter kind mismatch")
        ids.append(entry["state_id"])
        paths.append(path)
    require(ids == sorted(set(ids)) and len(set(paths)) == len(paths), "duplicate/unsorted generated state")


def generated_words(manifest):
    validate_generated_manifest(manifest)
    for entry in manifest["state"]:
        for address in range(entry["depth"]):
            yield dict(owner=entry["hierarchy"] + (f"[{address}]" if entry["kind"] == "memory" else ""),
                       width=entry["width"])


def check_generated_rtl(manifest, reference, rtl, bufgce_model):
    """Independent emitted-declaration coverage check for the restricted FIRRTL syntax.

    Init-only _RAND_ temporaries are excluded by the established emitter parser.
    The only procedural output-register adapter is the exact pinned BUFGCE model.
    Missing/extra/reshaped declarations fail instead of changing the inventory.
    """
    validate_generated_manifest(manifest)
    require(hashlib.sha256(reference.encode()).hexdigest() == manifest["reference_sha256"], "reference hash mismatch")
    # Comments and diagnostic strings may contain words such as "reg.name";
    # lex them out together before scanning declarations and hierarchy.
    syntax = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/',
                    lambda match: re.sub(r"[^\n]", " ", match.group()), rtl, flags=re.S)
    mods = modules(syntax)
    def inventory(module, prefix, ancestors):
        require(module in mods and module not in ancestors, "missing/recursive generated RTL module")
        header, body = mods[module]
        if re.search(r"\breg\b", header):
            require(module in ("AbstractClockGate", "BUFGCE"), "unadapted procedural output state")
        result = {}
        for declaration in re.findall(r"\breg\b[^;]*;", body):
            match = re.fullmatch(rf"reg\s+{RANGE}({IDENT})\s*(?:\[0:(\d+)\])?\s*;", declaration)
            require(match is not None, f"unsupported generated RTL register syntax in {module}: {declaration[:160]}")
            high, name, depth_high = match.groups()
            if re.fullmatch(r"_RAND_\d+", name):
                continue
            path = prefix + name
            require(path not in result, "duplicate RTL declaration")
            result[path] = (int(high) + 1 if high else 1, int(depth_high) + 1 if depth_high else 1,
                            "memory" if depth_high is not None else "register")
        for child, instance in re.findall(rf"^[ \t]*({IDENT})[ \t]+({IDENT})[ \t]*\(", body, re.M):
            child_state = inventory(child, prefix + instance + ".", ancestors | {module})
            require(not set(result).intersection(child_state), "duplicate RTL hierarchy")
            result.update(child_state)
        return result
    actual = inventory(manifest["root_module"], manifest["root_module"] + ".", set())
    for entry in manifest["state"]:
        instance = entry["hierarchy"].rsplit(".", 1)[0]
        if entry["adapter"] == "metasim-bufgce-v1":
            record = next(i for i in manifest["instances"] if i["hierarchy"] == instance)
            require(hashlib.sha256(bufgce_model.encode()).hexdigest() == record["implementation_sha256"],
                    "BUFGCE metasim model mismatch")
            # Output O is declared in the port header rather than the module body.
            require(mods[entry["module"]][0].count("output reg O") == 1, "BUFGCE output adapter mismatch")
            actual[entry["hierarchy"]] = (1, 1, "register")
    expected = {e["hierarchy"]: (e["width"], e["depth"], e["kind"]) for e in manifest["state"]}
    require(actual == expected, f"generated RTL membership/shape mismatch: missing={sorted(set(expected)-set(actual))} "
            f"extra={sorted(set(actual)-set(expected))}")


def generated_capture(manifest, values, host_sample):
    words = list(generated_words(manifest))
    natural(host_sample)
    require(type(values) is list and len(values) == len(words), "incomplete generated RTL capture")
    records = []
    for word, value in zip(words, values):
        bit_value(dict(width=word["width"], value=value))
        records.append(dict(word, value=value))
    return dict(capture_version=1, capture_type="generated_rtl_diagnostic", scope="generated_rtl_only",
                external_runtime_required=True, manifest_sha256=hashlib.sha256(canonical(manifest)).hexdigest(),
                host_sample=host_sample, sample_phase="settled_host_negedge", records=records)


def prepare_generated_probe(manifest, out):
    """Probe all manifested words, with no semantic inventory or DUT-only mapping.

    Captures one active, one outstanding and one held-response diagnostic for
    InventoryFixture. A new target needs an explicit diagnostic trigger; this
    prototype is not a general consistent-cut controller or FPGA transport.
    """
    words = list(generated_words(manifest))
    root = manifest["root_module"]
    def index(suffix):
        matches = [i for i, w in enumerate(words) if w["owner"].endswith(suffix)]
        require(len(matches) == 1, f"ambiguous/missing diagnostic trigger {suffix}")
        return matches[0]
    counter, busy, queued, held = (index(".dut." + p) for p in ("counter", "busy", "qValid", "responseValid"))
    decl = [f"input wire [{w['width']-1}:0] f{i}" for i, w in enumerate(words)]
    args = [f".f{i}({w['owner'][len(root)+1:]})" for i, w in enumerate(words)]
    fmt = '{"host_sample":%0d,"stage":%0d,"values":[' + ','.join('"%h"' for _ in words) + ']}'
    source = ["`timescale 1ps/1ps", "module generated_state_probe(input wire clock,", ",\n".join(decl) + ");",
              "integer fd = 0; integer stage = 0; longint unsigned host_sample = 0; string filename;",
              "initial if ($value$plusargs(\"generated_capture=%s\", filename)) begin",
              "  fd = $fopen(filename, \"w\"); if (!fd) $fatal(1, \"cannot open generated probe\"); end",
              "always @(negedge clock) begin", "  #1; host_sample = host_sample + 1;",
              f"  if (fd && ((stage == 0 && f{counter} > 0) || (stage == 1 && f{busy} && f{queued}) ||",
              f"             (stage == 2 && f{held}))) begin",
              f"    $fdisplay(fd, {json.dumps(fmt)}, host_sample, stage, " + ', '.join(f"f{i}" for i in range(len(words))) + ");",
              "    $fflush(fd); stage = stage + 1;", "  end", "end", "final if (fd) $fclose(fd);", "endmodule",
              f"bind {root} generated_state_probe generated_probe(.clock(clock), " + ', '.join(args) + ");"]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "generated-probe.sv").write_text('\n'.join(source) + '\n')
    (out / "generated-layout.json").write_bytes(canonical(words))
    return words
