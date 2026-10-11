"""Jasper induction over complete checkpoint state, including many-to-many maps.

No assumptions or reset sequence: each assertion's antecedent is the complete
candidate state relation. A loader enforces that relation when initializing the
netlist. Induction proves its preservation; output assertions prove observation
equivalence. Unread candidates remain unconstrained outside that relation, so
these assertions prove their irrelevance rather than assuming it. Independent
covers exercise both values of every physical and omitted original bit.
Constant candidates constrain the relation only after separate arbitrary-state
predicates prove their values and horizon; these predicates are never inferred
from relation preservation, even if every relational assertion passes.
This adapter supports the flat StateMapDUT interface and audited cell storage,
including packed registers and unpacked SRAM words with pipeline/port state.
"""

import json
import re

from .codec import keys, require


ROLES = {"rtl", "netlist", "models", "library", "synthesis_script", "synthesis_log",
         "relation_spec", "relation_miter", "relation_script", "relation_log", "relation_results"}
INPUTS = ("rtl", "netlist", "models", "relation_spec", "relation_miter", "relation_script")
SCRIPT = '''clear -all
set input_paths [list rtl $env(CHECKPOINT_RTL) netlist $env(CHECKPOINT_NETLIST) models $env(CHECKPOINT_CELLS) relation_spec $env(CHECKPOINT_RELATION_SPEC) relation_miter $env(CHECKPOINT_RELATION_MITER) relation_script $env(CHECKPOINT_RELATION_SCRIPT)]
set input_hashes [dict create]
foreach {role path} $input_paths {
  dict set input_hashes $role [lindex [exec sha256sum $path] 0]
}
analyze -sv $env(CHECKPOINT_CELLS) $env(CHECKPOINT_RELATION_MITER)
elaborate -top checkpoint_relation_miter
clock clock
reset -none
prove -all
report -summary
set out [open relation-results.tsv w]
puts $out "FORMAT\tjasper-relation-v1"
puts "CHECKPOINT_RELATION_RESET=none"
foreach {role path} $input_paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $input_hashes $role]} {error "Relation proof input changed: $role"}
  puts $out "INPUT\t$role\t$digest"
  puts "CHECKPOINT_RELATION_INPUT\t$role\t$digest"
}
foreach property [get_property_list] {
  set kind [get_property_info -list {type} $property]
  set status [get_property_info -list {status} $property]
  puts $out "PROPERTY\t$property\t$kind\t$status"
  puts "CHECKPOINT_RELATION_PROPERTY\t$property\t$kind\t$status"
}
puts $out "END"
close $out
exit
'''


def candidates(spec):
    require(type(spec) is dict, "unsupported relational proof interface")
    keys(spec, {"relation_version", "top", "relations"} |
         ({"unread"} if spec.get("relation_version") in (2, 3) else set()) |
         ({"constants"} if spec.get("relation_version") == 3 else set()))
    require(type(spec["relation_version"]) is int and spec["relation_version"] in (1, 2, 3) and spec["top"] == "StateMapDUT",
            "unsupported relational proof interface")
    require(type(spec["relations"]) is list and spec["relations"], "empty state relation")
    seen = set()
    for row in spec["relations"]:
        keys(row, {"original_rtl", "gate", "xor"})
        require(type(row["original_rtl"]) is str and
                re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\]){0,2}", row["original_rtl"]) and
                type(row["gate"]) is str and
                re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\])*[A-Za-z0-9_$]*\.[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\]){0,2}", row["gate"]) and
                type(row["xor"]) is int and row["xor"] in (0, 1), "unsupported state relation")
        pair = (row["original_rtl"], row["gate"])
        require(pair not in seen, "duplicate or conflicting state relation")
        seen.add(pair)
    unread(spec)
    constant_candidates(spec)
    return spec["relations"]


def unread(spec):
    """Candidates for omission, never assumptions on the reference state.

    The complete relation excludes these bits. Induction and output assertions
    must therefore hold for every value and evolution of this original state.
    Both values are independently covered under that same relation.
    """
    bits = spec.get("unread", [])
    require(type(bits) is list and (spec["relation_version"] != 2 or bits),
            "empty or unsupported unread state candidates")
    require(all(type(bit) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*\[\d+\]", bit)
                for bit in bits), "unsupported unread state candidate")
    require(len(bits) == len(set(bits)) and not
            (set(bits) & {row["original_rtl"] for row in spec["relations"]}),
            "duplicate or conflicting unread state candidate")
    return bits


def constant_candidates(spec):
    """Initial relation predicates; separate arbitrary-state proofs are mandatory.

    Relation preservation alone cannot establish that these values are reachable
    from arbitrary reference state. validate_constants supplies that proof and
    its one-edge horizon; the loader enforces both before any deposit.
    """
    bits = spec.get("constants", [])
    require(type(bits) is list and (spec["relation_version"] != 3 or bits),
            "empty or unsupported relational constant candidates")
    seen = set()
    retained = {row["original_rtl"] for row in spec["relations"]} | set(unread(spec))
    for bit in bits:
        require(type(bit) is dict, "unsupported relational constant candidate")
        keys(bit, {"original_rtl", "value"})
        require(type(bit["original_rtl"]) is str and
                re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*\[\d+\]", bit["original_rtl"]) and
                type(bit["value"]) is int and bit["value"] in (0, 1),
                "unsupported relational constant candidate")
        require(bit["original_rtl"] not in seen | retained,
                "duplicate or conflicting relational constant candidate")
        seen.add(bit["original_rtl"])
    return bits


def gate_expression(path):
    instance, storage = path.split(".")
    return f"implementation.\\{instance} .{storage}"


def validate_interface(text):
    """Reject unobserved ports/width truncation in this fixed-interface adapter."""
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    parsed = re.fullmatch(r"\s*module\s+StateMapDUT\s*\((.*?)\);(.*?)endmodule\s*", clean, re.S)
    require(parsed is not None, "unsupported relational DUT interface")
    header, body = parsed.groups()
    ansi = bool(re.search(r"\b(input|output|inout)\b", header))
    declarations = [header] if ansi else re.findall(r"\b(?:input|output|inout)\b[^;]*", body)
    ports = {}
    for declaration in declarations:
        direction, width = None, None
        for item in declaration.split(","):
            match = re.fullmatch(r"\s*(?:(input|output)\s*(?:\[(\d+):0\]\s*)?)?([A-Za-z_][A-Za-z0-9_$]*)\s*", item)
            require(match is not None, "unsupported relational DUT port declaration")
            kind, high, name = match.groups()
            if kind:
                direction, width = kind, int(high) + 1 if high is not None else 1
            require(direction is not None and name not in ports, "duplicate or unsupported relational DUT port")
            ports[name] = (direction, width)
    if not ansi:
        names = [p.strip() for p in header.split(",")]
        require(len(names) == len(set(names)) and set(names) == set(ports), "incomplete relational DUT ports")
    else:
        require(not re.search(r"\b(input|output|inout)\b", body), "mixed relational DUT port declarations")
    expected = {name: ("input", width) for name, width in
                (("clock", 1), ("reset", 1), ("enable", 1), ("write", 1), ("address", 2), ("data", 4))}
    expected.update({name: ("output", 4) for name in ("held_out", "count_out", "read_out")})
    require(ports == expected, "incomplete or wrong-width relational DUT interface")


def miter(spec, rtl, netlist):
    rows = candidates(spec)
    texts = []
    for text, name in ((rtl, "checkpoint_reference"), (netlist, "checkpoint_implementation")):
        validate_interface(text)
        clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
        require(not re.search(r"\b(assume|restrict|assert|cover|initial|force)\b", clean),
                "constrained or initialized relational DUT unsupported")
        renamed, count = re.subn(r"\bmodule\s+StateMapDUT\b", "module " + name, text)
        require(count == 1, "unsupported relational DUT module")
        texts.append(renamed)
    lines = texts + ["module checkpoint_relation_miter(input clock, reset, enable, write,",
                    "  input [1:0] address, input [3:0] data);",
                    "wire [3:0] r_held, r_count, r_read, i_held, i_count, i_read;"]
    for prefix, module, instance in (("r", "checkpoint_reference", "reference"),
                                     ("i", "checkpoint_implementation", "implementation")):
        lines.append(f"{module} {instance}(.clock(clock),.reset(reset),.enable(enable),.write(write),"
                     f".address(address),.data(data),.held_out({prefix}_held),"
                     f".count_out({prefix}_count),.read_out({prefix}_read));")
    expressions = [f"(reference.{r['original_rtl']} == ({gate_expression(r['gate'])} ^ 1'b{r['xor']}))"
                   for r in rows]
    expressions += [f"(reference.{b['original_rtl']} == 1'b{b['value']})" for b in constant_candidates(spec)]
    lines.append("wire relation = " + " &&\n  ".join(expressions) + ";")
    for n, expression in enumerate(expressions):
        lines.append(f"step_{n}: assert property (@(posedge clock) relation |=> {expression});")
    for port in ("held", "count", "read"):
        lines.append(f"output_{port}: assert property (@(posedge clock) relation |-> r_{port} == i_{port});")
    lines.append("checkpoint_edge: cover property (@(posedge clock) relation ##1 relation);")
    for n, gate in enumerate(sorted({r["gate"] for r in rows})):
        for value in (0, 1):
            lines.append(f"bit_{n}_{value}: cover property (@(posedge clock) relation && "
                         f"{gate_expression(gate)} == 1'b{value});")
    for n, bit in enumerate(unread(spec)):
        for value in (0, 1):
            lines.append(f"unread_{n}_{value}: cover property (@(posedge clock) relation && "
                         f"reference.{bit} == 1'b{value});")
    return ("\n".join(lines + ["endmodule", ""]).encode())


def validate_relations(artifacts, refs, gates, constants=None):
    """Validate input identity, audited miter, membership and real engine statuses."""
    from .formal_state_map import sha

    spec = json.loads(artifacts["relation_spec"])
    rows = candidates(spec)
    require(artifacts["relation_script"] == SCRIPT.encode() and
            artifacts["relation_miter"] == miter(spec, artifacts["rtl"].decode(), artifacts["netlist"].decode()),
            "unaudited relational script or miter")
    by_original = {v["original_rtl"]: k for k, v in refs.items()}
    by_gate = {v["instance"] + "." + v["rtl_path"]: k for k, v in gates.items()}
    omitted = unread(spec)
    require(set(omitted) <= set(by_original), "unread state outside complete semantic inventory")
    optimized = {by_original[bit]: "unread" for bit in omitted}
    constants = constants or {}
    candidates_by_ref = {}
    for bit in constant_candidates(spec):
        require(bit["original_rtl"] in by_original, "constant state outside complete semantic inventory")
        candidates_by_ref[by_original[bit["original_rtl"]]] = bit["value"]
    require(candidates_by_ref == {ref: proof["value"] for ref, proof in constants.items()},
            "relational constants lack matching independent predicates")
    proven = []
    for row in rows:
        require(row["original_rtl"] in by_original and row["gate"] in by_gate,
                "relation outside complete state inventory")
        gate = by_gate[row["gate"]]
        proven.append((by_original[row["original_rtl"]], gate, row["xor"] ^ gates[gate]["storage_xor"]))
    require({r for r, _, _ in proven} | set(optimized) | set(constants) == set(refs), "unproven or unmappable semantic state")
    require({g for _, g, _ in proven} == set(gates), "unproven or unmappable gate state")
    expected = {}
    for name in [f"step_{n}" for n in range(len(rows) + len(constants))] + [f"output_{p}" for p in ("held", "count", "read")]:
        prop = "<embedded>::checkpoint_relation_miter." + name
        expected[prop] = ("assert", "proven")
        expected[prop + ":precondition1"] = ("cover", "covered")
    expected["<embedded>::checkpoint_relation_miter.checkpoint_edge"] = ("cover", "covered")
    for n in range(len(gates)):
        for value in (0, 1):
            expected[f"<embedded>::checkpoint_relation_miter.bit_{n}_{value}"] = ("cover", "covered")
    for n in range(len(omitted)):
        for value in (0, 1):
            expected[f"<embedded>::checkpoint_relation_miter.unread_{n}_{value}"] = ("cover", "covered")
    lines = artifacts["relation_results"].decode("ascii").splitlines()
    require(lines[:1] == ["FORMAT\tjasper-relation-v1"] and lines[-1:] == ["END"],
            "incomplete relational proof")
    inputs, results = {}, {}
    for line in lines[1:-1]:
        row = line.split("\t")
        if len(row) == 3 and row[0] == "INPUT":
            require(row[1] not in inputs, "duplicate relational proof input")
            inputs[row[1]] = row[2]
        elif len(row) == 4 and row[0] == "PROPERTY":
            require(row[1] not in results, "duplicate relational proof property")
            results[row[1]] = tuple(row[2:])
        else:
            require(False, "unsupported relational proof row")
    require(inputs == {r: sha(artifacts[r]) for r in INPUTS}, "stale relational proof identity")
    require(results == expected, "unproven or vacuous state correspondence")
    log = artifacts["relation_log"].decode("ascii")
    require("ERROR" not in log and "Exiting the analysis session with status 0." in log and
            "CHECKPOINT_RELATION_RESET=none" in log, "relational proof tool failure")
    human = re.findall(r"^CHECKPOINT_RELATION_PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$", log, re.M)
    require(len(human) == len(expected) and {p: (k, s) for p, k, s in human} == expected,
            "machine/raw relational proof mismatch")
    for prop, (_, status) in expected.items():
        name = prop.split("::", 1)[1]
        require(re.search(r'The (?:cover )?property "' + re.escape(name) + r'" was ' + status + r' (?:in|at) ', log),
                "missing independent relational engine result")
    raw_inputs = re.findall(r"^CHECKPOINT_RELATION_INPUT\t([^\t\n]+)\t([a-f0-9]{64})$", log, re.M)
    require(len(raw_inputs) == len(INPUTS) and dict(raw_inputs) == inputs, "raw relational proof identity mismatch")
    return proven, optimized
