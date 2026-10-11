"""Build-bound, fail-closed Formality/Jasper state-map exporter.

Initial capability: one flat pre-FAME DUT, no retiming, audited scalar-cell
simulation models, and memories explicitly synthesized into flip-flops. Passing
sequential compare points or complete Jasper relational induction initialize
state. A global equivalence PASS never excuses missing bits or extra storage.
Gate-reference proofs support merged RTL registers; all checkpoint sources of
shared storage must agree after their proven polarity transformations.
Unread original registers may be omitted only with explicit tool classification,
independently cross-checked against the hash-bound human unread-point report.
Constant original register bits require separate Jasper predicates proved from
arbitrary state after one edge, with raw results and nonvacuity coverage. Every
checkpoint must satisfy both their horizon and values before any gate deposits.
Complete relational induction supports simultaneous merging and duplication;
all original/gate bits, output equivalence and nonvacuity covers are mandatory.
"""

import hashlib
import re

from .codec import canonical, keys, require
from .constant_state import ROLES as CONSTANT_ROLES, validate_constants
from .relational_state import ROLES as RELATION_ROLES, validate_relations
from .replay import IDENT, inventory_rtl, modules, state_words
from .semantic import decode_semantic, manifest_hash, validate_manifest


ROLES = {"rtl", "netlist", "models", "library", "synthesis_script", "synthesis_log",
         "formal_script", "formal_configuration", "formal_log", "evidence", "blackboxes"}
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
        require(re.fullmatch(rf"{IDENT}(?:\[\d+\]|[A-Za-z0-9_$])*", name),
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
    require(len(lines) >= 3 and lines[0] in ("FORMAT\tformality-state-v1", "FORMAT\tformality-state-v2",
                                          "FORMAT\tformality-state-v3")
            and lines[1] == "VERIFY\t1"
            and lines[-1] == "END", "missing, incomplete or unsuccessful formal proof")
    oriented = lines[0] != "FORMAT\tformality-state-v1"
    if oriented:
        require(lines[2] in ("ORIENTATION\tgate-reference", "ORIENTATION\trtl-reference"),
                "unsupported formal proof orientation")
        require(lines[0] != "FORMAT\tformality-state-v2" or lines[2] == "ORIENTATION\tgate-reference",
                "unsupported formal proof orientation")
    reversed_proof = oriented and lines[2] == "ORIENTATION\tgate-reference"
    registers, relations, inputs, optimized = {"r": set(), "i": set()}, [], {}, {}
    for line in lines[3 if oriented else 2:-1]:
        row = line.split("\t")
        if len(row) == 3 and row[0] == "INPUT":
            require(row[1] not in inputs, "duplicate formal input identity")
            inputs[row[1]] = row[2]
        elif len(row) == 3 and row[0] == "REGISTER" and row[1] in registers:
            require(row[2] not in registers[row[1]], "duplicate formal state inventory")
            registers[row[1]].add(row[2])
        elif len(row) == 4 and row[0] == "PROVEN" and row[1] in ("noninverted", "inverted"):
            relations.append((row[2], row[3], int(row[1] == "inverted")))
        elif (lines[0] == "FORMAT\tformality-state-v3" and len(row) == 3 and
              row[:2] == ["OPTIMIZED", "unread"]):
            require(row[2] not in optimized, "duplicate optimized state classification")
            optimized[row[2]] = row[1]
        else:
            require(False, "unsupported formal evidence row")
    require(relations and len(relations) == len(set(relations)), "missing or duplicate passing relationships")
    require(len({(ref, impl) for ref, impl, _ in relations}) == len(relations),
            "conflicting passing polarity relationships")
    require(all(point in registers["i" if reversed_proof else "r"] for point in optimized),
            "optimized point outside original state inventory")
    if reversed_proof:
        require(all(name.startswith(side + ":/WORK/") for side, names in registers.items() for name in names),
                "invalid oriented formal inventory")
        require(all(ref in registers["r"] and impl in registers["i"] for ref, impl, _ in relations),
                "passing point outside oriented state inventory")
        registers = {"r": {"r" + name[1:] for name in registers["i"]},
                     "i": {"i" + name[1:] for name in registers["r"]}}
        relations = [("r" + impl[1:], "i" + ref[1:], polarity) for ref, impl, polarity in relations]
        optimized = {"r" + point[1:]: status for point, status in optimized.items()}
    require(lines[0] != "FORMAT\tformality-state-v3" or optimized, "empty optimization evidence")
    return registers, relations, inputs, reversed_proof, optimized


def export_state_map(manifest, top, adapter, artifacts):
    """All artifact values are bytes from this synthesis/proof invocation.

    The returned map is reviewable data, not a declaration of ASIC acceptance.
    Callers must validate it again against the current bytes before loading.
    Missing/unclassified state fails; omissions need unread or constant evidence.
    """
    validate_manifest(manifest)
    require(re.fullmatch(IDENT, top), "invalid DUT module")
    require(type(artifacts) is dict and all(type(v) is bytes for v in artifacts.values()),
            "incomplete formal build artifacts")
    has_optimization = artifacts.get("evidence", b"").startswith(b"FORMAT\tformality-state-v3\n")
    has_constants = bool(set(artifacts) & CONSTANT_ROLES)
    has_relations = "relation_spec" in artifacts
    require(set(artifacts) == (RELATION_ROLES if has_relations else
            ROLES | ({"optimization_report"} if has_optimization else set()) |
            (CONSTANT_ROLES if has_constants else set())),
            "incomplete formal build artifacts")
    if not has_relations:
        require(b"Verification SUCCEEDED\n" in artifacts["formal_log"] and
                b"Error:" not in artifacts["formal_log"], "formal tool did not prove equivalence")
    require(b"CHECKPOINT_RETIMING=false\n" in artifacts["synthesis_log"] and
            b"Error" not in artifacts["synthesis_log"], "retiming disabled synthesis not established")
    for role in ("rtl", "library", "synthesis_script"):
        marker = f"CHECKPOINT_SYNTH_INPUT\t{role}\t{sha(artifacts[role])}".encode()
        require(marker in artifacts["synthesis_log"].splitlines(), "stale synthesis input identity")
    marker = f"CHECKPOINT_SYNTH_OUTPUT\t{sha(artifacts['netlist'])}".encode()
    require(marker in artifacts["synthesis_log"].splitlines(), "netlist not bound to this synthesis")
    if not has_relations:
        require(b"No 'black boxes' matched current 'reference and implementation designs'" in
                artifacts["blackboxes"], "blackboxed state or logic unsupported")
    rtl = artifacts["rtl"].decode()
    require(manifest["reference_sha256"] == sha(artifacts["rtl"]),
            "semantic manifest/reference RTL identity mismatch")
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
    if has_relations:
        proven = validate_relations(artifacts, refs, gates)
        reversed_proof, optimized = False, {}
    else:
        registers, proven, proof_inputs, reversed_proof, optimized = parse_evidence(artifacts["evidence"])
        require(proof_inputs == {role: sha(artifacts[role]) for role in
                                ("rtl", "models", "netlist", "formal_script", "formal_configuration")},
                "stale formal input identity")
        require(registers["r"] == set(refs), "unmappable or optimized reference state")
        require(registers["i"] == set(gates), "formal/netlist gate inventory mismatch")
    constants = validate_constants(artifacts, manifest, top) if has_constants else {}
    require(set(constants) <= set(refs) and not (set(constants) & set(optimized)),
            "constant state outside inventory or classified unread")
    if optimized:
        # Read the tool's independently retained human report, including its
        # filter and total. A global PASS or a hand-added machine row is never
        # sufficient to classify omitted state. Only original unread DFFs are
        # supported; constrained constants/clock gates and extra gate state fail.
        report = artifacts["optimization_report"].decode("ascii")
        require(re.search(r"^\s*-point_type reg\s*$", report, re.M) and
                re.search(r"^\s*-status unread\s*$", report, re.M), "wrong optimization report filter")
        reported = re.findall(r"^\s*(Ref|Impl)\s+DFF\s+([ri]:\S+)\s*$", report, re.M)
        require(len(reported) == len(set(reported)) == len(optimized), "incomplete unread-point report")
        side, label = ("i", "Impl") if reversed_proof else ("r", "Ref")
        require(all(kind == label and point.startswith(side + ":/WORK/") for kind, point in reported),
                "unsupported unread gate state")
        require({"r" + point[1:] for _, point in reported} == set(optimized),
                "machine/human optimization evidence mismatch")
        counts = (0, len(optimized)) if reversed_proof else (len(optimized), 0)
        require(f"{len(optimized)} Unmatched points ({counts[0]} reference, {counts[1]} implementation):"
                in report, "incomplete unread-point report count")
    entries = {ref: dict(info, formal_reference=ref, gates=[]) for ref, info in refs.items()}
    covered = set()
    for ref, impl, polarity in proven:
        require(ref in entries and impl in gates, "passing point outside state inventory")
        require(ref not in optimized, "state classified both passing and unread")
        require(ref not in constants, "state classified both passing and constant")
        require(reversed_proof or has_relations or impl not in covered, "gate storage has conflicting state relationships")
        covered.add(impl)
        storage = gates[impl]
        entries[ref]["gates"].append(dict(formal_implementation=impl, cell=storage["cell"],
                                          instance=storage["instance"], storage=storage["rtl_path"],
                                          bit=0, xor=polarity ^ storage["storage_xor"],
                                          proof_status="passing"))
    require(covered == set(gates), "unproven or unmappable gate state")
    require(all(e["gates"] or ref in optimized or ref in constants for ref, e in entries.items()),
            "unproven or unmappable semantic state")
    for ref in optimized:
        entries[ref]["optimization"] = dict(kind="unread", proof_status="tool_classified",
                                             report="optimization_report")
    for ref, proof in constants.items():
        entries[ref]["optimization"] = proof
    ordered = sorted(entries.values(), key=lambda e: (e["state_id"], e["address"], e["bit"]))
    for entry in ordered:
        entry["gates"].sort(key=lambda g: g["formal_implementation"])
    proof = (dict(tool="Jasper", export="complete state relation induction and output equivalence",
                  assumptions=[], reset="unconstrained synchronous input",
                  initial_state="complete map relation; loader enforces merged source consistency")
             if has_relations else
             dict(tool="Formality", export="passing sequential compare points" +
                  ("; gate-reference orientation" if reversed_proof else "") +
                  ("; explicit unread original DFF classification" if optimized else ""),
                  assumptions=[], reset="unconstrained synchronous input",
                  **(dict(constant_tool="Jasper", constant_horizon="one unconstrained target edge")
                     if constants else {})))
    return dict(map_version=5 if has_relations else 4 if constants else 3 if optimized else 2 if reversed_proof else 1, map_type="asic_state_map", top=top,
                state_manifest_hash=manifest_hash(manifest), retiming=False,
                build={role: sha(data) for role, data in sorted(artifacts.items())},
                cell_adapter_hash=sha(canonical(adapter)), entries=ordered,
                gate_storage_bits=len(gates), semantic_bits=len(refs),
                proof=proof)


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
    deposits = {}
    for entry in mapping["entries"]:
        value = int(records[entry["state_id"]]["values"][entry["address"]], 16)
        proof = entry.get("optimization", {})
        if proof.get("kind") == "constant":
            require(checkpoint["target_cycle"] >= proof["min_target_cycle"],
                    "checkpoint precedes proven constant horizon")
            require(((value >> entry["bit"]) & 1) == proof["value"],
                    f"checkpoint conflicts with proven constant state: {entry['original_rtl']}")
        for gate in entry["gates"]:
            bit = ((value >> entry["bit"]) & 1) ^ gate["xor"]
            path = f"{root}.{gate['instance']}.{gate['storage']}"
            require(path not in deposits or deposits[path] == bit,
                    f"inconsistent merged semantic state for gate storage: {path}")
            deposits[path] = bit
    require(len(deposits) == mapping["gate_storage_bits"], "incomplete gate initialization")
    return checkpoint["target_cycle"], sorted((path, 1, f"{value:x}") for path, value in deposits.items())
