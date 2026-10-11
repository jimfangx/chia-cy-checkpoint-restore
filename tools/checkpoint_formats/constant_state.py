"""Audited Jasper one-edge constant predicates, independent of equivalence PASS.

Only original scalar register bits are supported. No DUT reset, initialization,
input constraints, or guessed missing-state values are used. The delayed SVA
assertions prove the candidate constants after any first target edge, including
from arbitrary original state. Translation enforces that horizon and every bit.
"""

import hashlib
import json
import re

from .codec import keys, require
from .replay import IDENT


ROLES = {"constant_spec", "constant_bind", "constant_script", "constant_log", "constant_results"}
INPUTS = ("rtl", "constant_spec", "constant_bind", "constant_script")
SCRIPT = '''clear -all
set input_paths [list rtl $env(CHECKPOINT_RTL) constant_spec $env(CHECKPOINT_CONSTANT_SPEC) constant_bind $env(CHECKPOINT_CONSTANT_BIND) constant_script $env(CHECKPOINT_CONSTANT_SCRIPT)]
set input_hashes [dict create]
foreach {role path} $input_paths {
  dict set input_hashes $role [lindex [exec sha256sum $path] 0]
}
analyze -sv $env(CHECKPOINT_RTL) $env(CHECKPOINT_CONSTANT_BIND)
elaborate -top $env(CHECKPOINT_CONSTANT_TOP)
clock clock
reset -none
prove -all
report -summary
set out [open constant-results.tsv w]
puts $out "FORMAT\tjasper-constant-v1"
puts "CHECKPOINT_CONSTANT_RESET=none"
foreach {role path} $input_paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $input_hashes $role]} {error "Constant proof input changed: $role"}
  puts $out "INPUT\t$role\t$digest"
  puts "CHECKPOINT_CONSTANT_INPUT\t$role\t$digest"
}
foreach property [get_property_list] {
  set kind [get_property_info -list {type} $property]
  set status [get_property_info -list {status} $property]
  puts $out "PROPERTY\t$property\t$kind\t$status"
  puts "CHECKPOINT_CONSTANT_PROPERTY\t$property\t$kind\t$status"
}
puts $out "END"
close $out
exit
'''


def predicates(spec):
    keys(spec, {"constant_version", "top", "bits"})
    require(spec["constant_version"] == 1 and type(spec["top"]) is str and re.fullmatch(IDENT, spec["top"]),
            "unsupported constant predicate specification")
    require(type(spec["bits"]) is list and spec["bits"], "empty constant predicates")
    seen = set()
    for bit in spec["bits"]:
        keys(bit, {"signal", "bit", "width", "value"})
        require(type(bit["signal"]) is str and re.fullmatch(IDENT, bit["signal"]) and
                type(bit["width"]) is int and bit["width"] > 0 and
                type(bit["bit"]) is int and 0 <= bit["bit"] < bit["width"] and
                type(bit["value"]) is int and bit["value"] in (0, 1), "unsupported constant predicate")
        point = (bit["signal"], bit["bit"])
        require(point not in seen, "duplicate constant predicate")
        seen.add(point)
    return spec["bits"]


def binding(spec):
    bits = predicates(spec)
    ports = ["input clock"] + [f"input c{n}" for n in range(len(bits))]
    lines = ["module checkpoint_constants(" + ", ".join(ports) + ");"]
    for n, bit in enumerate(bits):
        lines.append(f"constant_{n}: assert property (@(posedge clock) 1'b1 |=> c{n} == 1'b{bit['value']});")
    lines += ["checkpoint_edge: cover property (@(posedge clock) 1'b1 ##1 1'b1);", "endmodule"]
    connections = [".clock(clock)"] + [f".c{n}({b['signal']}" +
                    (f"[{b['bit']}]" if b["width"] > 1 else "") + ")" for n, b in enumerate(bits)]
    lines.append(f"bind {spec['top']} checkpoint_constants checkpoint_constant_proof(" +
                 ", ".join(connections) + ");")
    return ("\n".join(lines) + "\n").encode()


def validate_constants(artifacts, manifest, top):
    """Cross-check source, audited script, predicates, machine and raw statuses."""
    spec = json.loads(artifacts["constant_spec"])
    bits = predicates(spec)
    require(spec["top"] == top, "constant proof top mismatch")
    require(artifacts["constant_script"] == SCRIPT.encode() and
            artifacts["constant_bind"] == binding(spec), "unaudited constant proof script or predicates")
    rtl = re.sub(r"/\*.*?\*/|//[^\n]*", "", artifacts["rtl"].decode(), flags=re.S)
    require(not re.search(r"\b(assume|restrict|assert|cover|initial|force)\b", rtl),
            "constrained or initialized constant proof RTL unsupported")
    states = {s["hierarchy"][len(manifest["dut_root"]) + 1:]: s for s in manifest["state"]}
    constants = {}
    expected = {f"<embedded>::{top}.checkpoint_constant_proof.checkpoint_edge": ("cover", "covered")}
    for n, bit in enumerate(bits):
        state = states.get(bit["signal"])
        require(state is not None and state["kind"] == "register" and state["depth"] == 1 and
                state["width"] == bit["width"], "constant predicate outside scalar original state")
        point = f"r:/WORK/{top}/{bit['signal']}_reg" + (f"[{bit['bit']}]" if bit["width"] > 1 else "")
        prop = f"<embedded>::{top}.checkpoint_constant_proof.constant_{n}"
        constants[point] = dict(kind="constant", value=bit["value"], min_target_cycle=1,
                                proof_status="proven", property=prop, report="constant_results")
        expected[prop] = ("assert", "proven")
        expected[prop + ":precondition1"] = ("cover", "covered")
    rows = artifacts["constant_results"].decode("ascii").splitlines()
    require(rows[0:1] == ["FORMAT\tjasper-constant-v1"] and rows[-1:] == ["END"],
            "incomplete constant predicate proof")
    inputs, results = {}, {}
    for line in rows[1:-1]:
        row = line.split("\t")
        if len(row) == 3 and row[0] == "INPUT":
            require(row[1] not in inputs, "duplicate constant proof input")
            inputs[row[1]] = row[2]
        elif len(row) == 4 and row[0] == "PROPERTY":
            require(row[1] not in results, "duplicate constant proof property")
            results[row[1]] = tuple(row[2:])
        else:
            require(False, "unsupported constant proof row")
    require(inputs == {r: hashlib.sha256(artifacts[r]).hexdigest() for r in INPUTS},
            "stale constant proof identity")
    require(results == expected, "unproven, constrained or vacuous constant predicates")
    log = artifacts["constant_log"].decode("ascii")
    require("ERROR" not in log and "Exiting the analysis session with status 0." in log and
            "CHECKPOINT_CONSTANT_RESET=none" in log, "constant proof tool failure")
    human = re.findall(r"^CHECKPOINT_CONSTANT_PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$", log, re.M)
    require(len(human) == len(expected) and {p: (k, s) for p, k, s in human} == expected,
            "machine/raw constant proof mismatch")
    for prop, (_, status) in expected.items():
        name = prop.split("::", 1)[1]
        require(re.search(r'The (?:cover )?property "' + re.escape(name) +
                          r'" was ' + status + r' (?:in|at) ', log),
                "missing independent constant engine result")
    raw_inputs = re.findall(r"^CHECKPOINT_CONSTANT_INPUT\t([^\t\n]+)\t([a-f0-9]{64})$", log, re.M)
    require(len(raw_inputs) == len(INPUTS) and dict(raw_inputs) == inputs, "raw constant proof identity mismatch")
    return constants
