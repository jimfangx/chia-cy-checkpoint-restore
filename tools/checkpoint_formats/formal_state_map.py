"""Build-bound, fail-closed Formality state-map exporter.

Initial capability: one flat pre-FAME DUT, no retiming, audited scalar-cell
simulation models, and memories explicitly synthesized into flip-flops. Only
passing sequential compare points may initialize state. In particular, a global
equivalence PASS never excuses missing semantic bits or extra gate storage.
"""

import hashlib
import re

from .codec import canonical, keys, require
from .replay import IDENT, inventory_rtl, modules, state_words
from .semantic import decode_semantic, manifest_hash, validate_manifest


ROLES = {"rtl", "netlist", "models", "library", "synthesis_script", "synthesis_log",
         "formal_script", "formal_log", "evidence", "blackboxes"}
NAME = r"(?:[A-Za-z_][A-Za-z0-9_$]*|\\[^\s,()]+)"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unescape(name):
    return name.strip().removeprefix("\\")


def flat_inventory(netlist, models_text, adapter, top):
    """Independent gate-storage audit; no implicit/unknown macro interfaces.

    The adapter's hash pins the *audited* simulation model bytes. Formality
    reads those same models, rather than blackboxing library cells. No cell
    name, library name, or synthesis naming convention is a state proof.
    """
    keys(adapter, {"adapter_version", "models_sha256", "cells"})
    require(adapter["adapter_version"] == 1, "unsupported cell adapter")
    require(adapter["models_sha256"] == sha(models_text.encode()), "unaudited cell simulation models")
    model_mods = modules(models_text)
    require(set(model_mods) == set(adapter["cells"]), "incomplete cell model adapter")
    for cell, spec in adapter["cells"].items():
        keys(spec, {"storage"})
        for storage in spec["storage"]:
            keys(storage, {"rtl_path", "formal_path", "xor"})
            require(re.fullmatch(IDENT, storage["rtl_path"]) and
                    re.fullmatch(IDENT, storage["formal_path"]) and
                    type(storage["xor"]) is int and storage["xor"] in (0, 1),
                    "unsupported scalar cell storage adapter")
        actual = inventory_rtl(model_mods, cell)
        expected = {s["rtl_path"]: (1, 1, "register") for s in spec["storage"]}
        require(actual == expected, "hidden or unsupported cell model state")
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", netlist, flags=re.S)
    parsed = re.fullmatch(rf"\s*module\s+{re.escape(top)}\s*\([^;]*\);(.*?)endmodule\s*", text, re.S)
    require(parsed is not None, "only one flat mapped netlist module supported")
    result, instances = {}, set()
    for statement in parsed[1].split(";"):
        statement = statement.strip()
        if not statement:
            continue
        if re.fullmatch(r"(?:input|output|wire)\s+(?:\[\d+:\d+\]\s*)?"
                        rf"{NAME}(?:\s*,\s*{NAME})*", statement):
            continue
        if statement.startswith("assign "):
            # Continuous expressions cannot introduce storage. No procedural,
            # hierarchical, delayed, or function-call constructs are accepted.
            require(re.fullmatch(r"assign\s+[^=;]+=[A-Za-z0-9_$'\\\s\[\]:{},.~!&|^()+*/?<>-]+", statement)
                    and "#" not in statement, "unsupported mapped assignment")
            continue
        instance = re.fullmatch(rf"({IDENT})\s+({NAME})\s*\((.*)\)", statement, re.S)
        require(instance is not None, f"unsupported mapped netlist statement: {statement[:120]}")
        cell, name, ports = instance.groups()
        name = unescape(name)
        require(re.fullmatch(rf"{IDENT}(?:\[\d+\])*", name),
                "unsupported escaped gate instance name")
        require(name not in instances, "duplicate netlist instance")
        instances.add(name)
        require(cell in adapter["cells"], f"unsupported cell or SRAM macro: {cell}")
        require(re.fullmatch(r"\s*\.\w+\s*\([^()]*\)(?:\s*,\s*\.\w+\s*\([^()]*\))*\s*", ports),
                "unsupported mapped cell connection")
        for storage in adapter["cells"][cell]["storage"]:
            formal = f"i:/WORK/{top}/{name}/{storage['formal_path']}"
            require(formal not in result, "duplicate gate storage")
            result[formal] = dict(cell=cell, instance=name, rtl_path=storage["rtl_path"],
                                  storage_xor=storage["xor"])
    require(result, "empty gate state inventory")
    return result


def parse_evidence(data):
    lines = data.decode("ascii").splitlines()
    require(len(lines) >= 3 and lines[:2] == ["FORMAT\tformality-state-v1", "VERIFY\t1"]
            and lines[-1] == "END", "missing, incomplete or unsuccessful formal proof")
    registers, relations, inputs = {"r": set(), "i": set()}, [], {}
    for line in lines[2:-1]:
        row = line.split("\t")
        if len(row) == 3 and row[0] == "INPUT":
            require(row[1] not in inputs, "duplicate formal input identity")
            inputs[row[1]] = row[2]
        elif len(row) == 3 and row[0] == "REGISTER" and row[1] in registers:
            require(row[2] not in registers[row[1]], "duplicate formal state inventory")
            registers[row[1]].add(row[2])
        elif len(row) == 4 and row[0] == "PROVEN" and row[1] in ("noninverted", "inverted"):
            relations.append((row[2], row[3], int(row[1] == "inverted")))
        else:
            require(False, "unsupported formal evidence row")
    require(relations and len(relations) == len(set(relations)), "missing or duplicate passing relationships")
    return registers, relations, inputs


def export_state_map(manifest, top, adapter, artifacts):
    """All artifact values are bytes from this synthesis/proof invocation.

    The returned map is reviewable data, not a declaration of ASIC acceptance.
    Callers must validate it again against the current bytes before loading.
    Optimized/merged reference state currently fails, rather than being guessed.
    """
    validate_manifest(manifest)
    require(re.fullmatch(IDENT, top), "invalid DUT module")
    require(set(artifacts) == ROLES and all(type(v) is bytes for v in artifacts.values()),
            "incomplete formal build artifacts")
    require(b"Verification SUCCEEDED\n" in artifacts["formal_log"] and
            b"Error:" not in artifacts["formal_log"], "formal tool did not prove equivalence")
    require(b"CHECKPOINT_RETIMING=false\n" in artifacts["synthesis_log"] and
            b"Error" not in artifacts["synthesis_log"], "retiming disabled synthesis not established")
    for role in ("rtl", "library", "synthesis_script"):
        marker = f"CHECKPOINT_SYNTH_INPUT\t{role}\t{sha(artifacts[role])}".encode()
        require(marker in artifacts["synthesis_log"].splitlines(), "stale synthesis input identity")
    marker = f"CHECKPOINT_SYNTH_OUTPUT\t{sha(artifacts['netlist'])}".encode()
    require(marker in artifacts["synthesis_log"].splitlines(), "netlist not bound to this synthesis")
    require(b"No 'black boxes' matched current 'reference and implementation designs'" in
            artifacts["blackboxes"], "blackboxed state or logic unsupported")
    rtl = artifacts["rtl"].decode()
    mods = modules(rtl)
    require(set(mods) == {top}, "only one flat original RTL module supported")
    expected_rtl = {e["hierarchy"][len(manifest["dut_root"]) + 1:]:
                    (e["width"], e["depth"], e["kind"]) for e in manifest["state"]}
    require(inventory_rtl(mods, top) == expected_rtl, "original RTL/semantic inventory mismatch")
    require(manifest["clock_domain"] == manifest["dut_root"] + ".clock" and
            all(event.strip() == "posedge clock" for event in re.findall(r"@\s*\(([^)]*)\)", rtl)),
            "unsupported reference clocks or reset edges")
    gates = flat_inventory(artifacts["netlist"].decode(), artifacts["models"].decode(), adapter, top)
    refs = {}
    for word in state_words(manifest):
        # Formality's elaborated scalar register convention. Complete membership
        # is checked below; deviations from this adapter fail explicitly.
        path, width = word["path"], word["width"]
        reg = re.sub(r"^(\w+)", r"\1_reg", path)
        for bit in range(width):
            ref = f"r:/WORK/{top}/{reg}" + (f"[{bit}]" if width > 1 else "")
            require(ref not in refs, "ambiguous reference register convention")
            refs[ref] = dict(state_id=word["state_id"], address=word["address"], bit=bit,
                             original_rtl=path + (f"[{bit}]" if width > 1 else ""))
    registers, proven, proof_inputs = parse_evidence(artifacts["evidence"])
    require(proof_inputs == {role: sha(artifacts[role]) for role in ("rtl", "models", "netlist", "formal_script")},
            "stale formal input identity")
    require(registers["r"] == set(refs), "unmappable or optimized reference state")
    require(registers["i"] == set(gates), "formal/netlist gate inventory mismatch")
    entries = {ref: dict(info, formal_reference=ref, gates=[]) for ref, info in refs.items()}
    covered = set()
    for ref, impl, polarity in proven:
        require(ref in entries and impl in gates, "passing point outside state inventory")
        require(impl not in covered, "gate storage has conflicting state relationships")
        covered.add(impl)
        storage = gates[impl]
        entries[ref]["gates"].append(dict(formal_implementation=impl, cell=storage["cell"],
                                          instance=storage["instance"], storage=storage["rtl_path"],
                                          bit=0, xor=polarity ^ storage["storage_xor"],
                                          proof_status="passing"))
    require(covered == set(gates), "unproven or unmappable gate state")
    require(all(e["gates"] for e in entries.values()), "unproven or unmappable semantic state")
    ordered = sorted(entries.values(), key=lambda e: (e["state_id"], e["address"], e["bit"]))
    for entry in ordered:
        entry["gates"].sort(key=lambda g: g["formal_implementation"])
    return dict(map_version=1, map_type="asic_state_map", top=top,
                state_manifest_hash=manifest_hash(manifest), retiming=False,
                build={role: sha(data) for role, data in sorted(artifacts.items())},
                cell_adapter_hash=sha(canonical(adapter)), entries=ordered,
                gate_storage_bits=len(gates), semantic_bits=len(refs),
                proof=dict(tool="Formality", export="passing sequential compare points",
                           assumptions=[], reset="unconstrained synchronous input"))


def validate_state_map(mapping, manifest, adapter, artifacts):
    require(type(mapping) is dict and "top" in mapping, "invalid ASIC state map")
    rebuilt = export_state_map(manifest, mapping["top"], adapter, artifacts)
    require(mapping == rebuilt, "ASIC map or build/proof identity mismatch")


def gate_deposits(mapping, manifest, adapter, artifacts, checkpoint_data, expected_build, root):
    """Translate independent Level-2 values, without advancing any target edges.

    This returns scalar writable storage paths for semantic_restore.cc. Its VPI
    resolver prevalidates every handle before any write; semantic_verify checks
    the complete zero-edge readback. These are deposits, never output forces.
    """
    validate_state_map(mapping, manifest, adapter, artifacts)
    require(re.fullmatch(rf"{IDENT}(?:\.{IDENT})*", root), "invalid gate simulation root")
    checkpoint = decode_semantic(checkpoint_data, expected_build, manifest)
    records = {r["state_id"]: r for r in checkpoint["records"]}
    deposits = []
    for entry in mapping["entries"]:
        value = int(records[entry["state_id"]]["values"][entry["address"]], 16)
        for gate in entry["gates"]:
            bit = ((value >> entry["bit"]) & 1) ^ gate["xor"]
            deposits.append((f"{root}.{gate['instance']}.{gate['storage']}", 1, f"{bit:x}"))
    require(len(deposits) == mapping["gate_storage_bits"], "incomplete gate initialization")
    return checkpoint["target_cycle"], sorted(deposits)
