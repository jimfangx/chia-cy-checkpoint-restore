"""Production pre-FAME synthesis architecture, NOT a proven state map.

Extract the selected FIRRTL emitter's single-write asynchronous-read memories
into concrete, unparameterized functional macros. All surrounding registers
(including memory port/pipeline state) remain in the original hierarchy. These
macros are preserved only during synthesis; formal and simulation must use the
complete concrete models. No architecture candidate authorizes gate restore.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re

from .codec import canonical, require
from .finite_replay import check_clean
from .replay import IDENT, RANGE, inventory_rtl, modules
from .semantic import manifest_hash, validate_manifest


def sha(data):
    return hashlib.sha256(data).hexdigest()


def synthesis_text(text):
    """Restricted preprocessing under SYNTHESIS, with no random initialization.

    Unknown active directives/macros fail instead of silently changing RTL.
    This policy is also used for architecture parity and subsequent formal.
    The byte-exact original remains an independent proof input.
    """
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    defined, stack, active, output = {"SYNTHESIS"}, [], True, []
    for line in text.splitlines():
        directive = re.fullmatch(r"\s*`(\w+)(?:\s+(.*?))?\s*", line)
        if directive:
            command, argument = directive.groups()
            argument = (argument or "").strip() or None
            if command in ("ifdef", "ifndef"):
                require(argument is not None and re.fullmatch(IDENT, argument), "unsupported preprocessor guard")
                condition = (argument in defined) == (command == "ifdef")
                stack.append((active, condition, False))
                active = active and condition
            elif command == "else":
                require(argument is None and stack and not stack[-1][2], "unsupported/duplicate preprocessor else")
                parent, condition, _ = stack[-1]
                stack[-1] = (parent, condition, True)
                active = parent and not condition
            elif command == "endif":
                require(argument is None and stack, "unmatched preprocessor endif")
                active = stack.pop()[0]
            elif command == "define":
                if active:
                    require(argument is not None and argument.split()[0] == "RANDOM",
                            "unsupported active preprocessor define")
                    defined.add("RANDOM")
            else:
                require(not active, "unsupported active preprocessor directive: " + command)
        elif active:
            require("`" not in line, "unsupported active macro expansion")
            output.append(line)
    require(not stack, "unterminated preprocessor guard")
    return "\n".join(output) + "\n"


def _blocks(body):
    """Enumerate supported clocked begin/end blocks and their source bounds."""
    blocks = []
    for start in re.finditer(r"\balways\s*@\s*\(posedge clock\)\s*begin\b", body):
        depth = 1
        for token in re.finditer(r"\b(begin|end)\b", body[start.end():]):
            depth += 1 if token[0] == "begin" else -1
            if depth == 0:
                blocks.append((start.end(), start.end() + token.start()))
                break
        else:
            require(False, "unterminated sequential block")
    return blocks


def extract_architecture(manifest, boundary, rtl):
    validate_manifest(manifest)
    check_clean(manifest, boundary, rtl)
    normalized = synthesis_text(rtl)
    original = modules(normalized)
    # The parser cannot silently drop text, duplicate modules or extra state.
    require(len(re.findall(r"\bmodule\b", normalized)) == len(original), "duplicate or unsupported RTL module")
    require(not re.search(r"\b(initial|generate|parameter|localparam|function|task)\b", normalized),
            "unsupported production emitter syntax")
    blocks, definitions, stubs, local_memories = [], {}, [], {}
    for module, (header, body) in original.items():
        changes, instances = [], []
        sequential = _blocks(body)
        declarations = list(re.finditer(rf"\breg\s+{RANGE}({IDENT})\s*\[0:(\d+)\]\s*;", body))
        for decl in declarations:
            high, name, last = decl.groups()
            width, depth = (int(high) + 1 if high else 1), int(last) + 1
            address_width = max(1, (depth - 1).bit_length())
            require(depth & (depth - 1) == 0, "unsupported non-power-of-two memory")
            reads = list(re.finditer(rf"\bassign\s+({IDENT})\s*=\s*{name}\[({IDENT})\]\s*;", body))
            writes = list(re.finditer(rf"\bif\s*\(([A-Za-z0-9_$ &|~]+)\)\s*begin\s*"
                                     rf"{name}\[({IDENT})\]\s*<=\s*({IDENT})\s*;\s*end\b", body))
            require(1 <= len(reads) <= 2 and len(writes) == 1, "unsupported production memory ports: " + module + "." + name)
            write = writes[0]
            owners = [(a, b) for a, b in sequential if a <= write.start() < write.end() <= b]
            require(len(owners) == 1, "memory write outside supported target clock")
            before = body[owners[0][0]:write.start()]
            nesting = sum(1 if t == "begin" else -1 for t in re.findall(r"\b(begin|end)\b", before))
            require(nesting == 0 and not re.search(r"\b(?:else|if\s*\([^;]*\))\s*$", before),
                    "nested/conditional production memory write unsupported")
            # Every port is an exact-width existing wire. No implicit truncation,
            # slicing, synchronous read or hidden mask lane is inferred.
            wire_shapes = {n: int(w) + 1 if w else 1 for w, n in re.findall(rf"\bwire\s+{RANGE}({IDENT})", body)}
            condition, write_address, write_data = write.groups()
            require(wire_shapes.get(write_address) == address_width and wire_shapes.get(write_data) == width,
                    "unsupported memory write port shape")
            require(all(wire_shapes.get(q) == width and wire_shapes.get(a) == address_width for q, a in (r.groups() for r in reads)),
                    "unsupported memory read port shape")
            require(all(wire_shapes.get(n) == 1 for n in re.findall(IDENT, condition)), "unsupported memory write enable")
            # Check ALL references; unmatched accesses must never disappear.
            remainder = body
            for match in sorted([decl, write, *reads], key=lambda m: m.start(), reverse=True):
                remainder = remainder[:match.start()] + remainder[match.end():]
            require(not re.search(rf"\b{name}\b", remainder), "unsupported additional memory access: " + module + "." + name)
            cell = f"CKMEM_W{width}_D{depth}_R{len(reads)}"
            instance = "ckmem_" + name
            require(not re.search(rf"\b{instance}\b", body) and cell not in original, "memory architecture name collision")
            ports = ["input CP", "input WE", f"input [{address_width-1}:0] WA", f"input [{width-1}:0] WD"]
            connections = [".CP(clock)", f".WE({condition})", f".WA({write_address})", f".WD({write_data})"]
            read_statements = []
            for i, read in enumerate(reads):
                q, a = read.groups()
                ports += [f"input [{address_width-1}:0] RA{i}", f"output [{width-1}:0] Q{i}"]
                connections += [f".RA{i}({a})", f".Q{i}({q})"]
                read_statements.append(f"assign Q{i} = contents[RA{i}];")
            cell_header = f"module {cell}({', '.join(ports)});\n"
            definition = (cell_header + f"reg [{width-1}:0] contents [0:{depth-1}];\n" +
                          "\n".join(read_statements) + "\nalways @(posedge CP) begin\n" +
                          "  if (WE) contents[WA] <= WD;\nend\nendmodule\n")
            require(cell not in definitions or definitions[cell] == definition, "inconsistent memory model")
            if cell not in definitions:
                definitions[cell] = definition
                stubs.append(cell_header + "endmodule\n")
            instances.append(f"{cell} {instance}({', '.join(connections)});")
            changes.extend((m.start(), m.end()) for m in [decl, write, *reads])
            local_memories[(module, name)] = dict(cell=cell, instance=instance, width=width, depth=depth,
                                                reads=[dict(data=q, address=a) for q, a in (r.groups() for r in reads)],
                                                write=dict(enable=condition, address=write_address, data=write_data))
        for a, b in sorted(changes, reverse=True):
            body = body[:a] + body[b:]
        # Empty always blocks are legal in VCS but unnecessary in synthesis.
        body = re.sub(r"\balways\s*@\s*\(posedge clock\)\s*begin\s*end\b", "", body)
        blocks.append(f"module {module}({header});\n{body}\n" + "\n".join(instances) + "\nendmodule\n")
    architecture = "\n".join(blocks)
    models = "\n".join(definitions.values())
    result, visited = [], set()

    def walk(module, prefix=""):
        require(module not in visited, "recursive production hierarchy")
        visited.add(module)
        header, body = original[module]
        for high, name, last in re.findall(rf"\breg\s+{RANGE}({IDENT})\s*(?:\[0:(\d+)\])?\s*;", body):
            memory = local_memories.get((module, name))
            result.append(dict(original_path=prefix + name,
                               architecture_path=prefix + (memory['instance'] + '.contents' if memory else name),
                               width=int(high) + 1 if high else 1, depth=int(last) + 1 if last else 1,
                               kind="memory" if last else "register", module=module,
                               memory=memory, proof_status="unproven"))
        for child, instance in re.findall(rf"^[ \t]*({IDENT})[ \t]+({IDENT})[ \t]*\(", body, re.M):
            walk(child, prefix + instance + ".")
        visited.remove(module)
    walk(boundary['dut_module'])
    entries = {e['hierarchy'][len(manifest['dut_root'])+1:]: e for e in manifest['state']}
    require({e['original_path']: (e['width'], e['depth'], e['kind']) for e in result} ==
            {p: (e['width'], e['depth'], e['kind']) for p, e in entries.items()}, "production source inventory mismatch")
    for entry in result:
        entry['state_id'] = entries[entry['original_path']]['state_id']
    require(inventory_rtl(modules(architecture + models), boundary['dut_module']) ==
            {e['architecture_path']: (e['width'], e['depth'], e['kind']) for e in result},
            "hidden/lost/reshaped architecture state")
    candidate = dict(architecture_version=1, artifact_type="unproven_synthesis_architecture",
                     top=boundary['dut_module'], semantic_manifest_hash=manifest_hash(manifest),
                     original_rtl_sha256=sha(rtl.encode()), normalized_rtl_sha256=sha(normalized.encode()),
                     architecture_sha256=sha(architecture.encode()), models_sha256=sha(models.encode()),
                     stubs_sha256=sha(''.join(stubs).encode()), retiming=False,
                     state_entries=len(result), state_bits=sum(e['width'] * e['depth'] for e in result),
                     restored_words=sum(e['depth'] for e in result),
                     memory_instances=sum(e['kind'] == 'memory' for e in result),
                     memory_model_definitions=len(definitions), entries=result)
    return candidate, normalized, architecture, models, ''.join(stubs)


def prepare(manifest, boundary, rtl, out):
    candidate, normalized, architecture, models, stubs = extract_architecture(manifest, boundary, rtl)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    for name, data in (("original.sv", rtl), ("normalized.sv", normalized), ("architecture.sv", architecture),
                       ("memory-models.v", models), ("memory-stubs.v", stubs)):
        (out / name).write_text(data)
    (out / "architecture-candidate.json").write_bytes(canonical(candidate))
    (out / "manifest.json").write_bytes(canonical(manifest))
    (out / "boundary.json").write_bytes(canonical(boundary))
    return candidate


def audit_architecture(out):
    """Reconstruct every candidate from current original inputs, never a map."""
    out = Path(out)
    candidate, normalized, architecture, models, stubs = extract_architecture(
        json.loads((out / 'manifest.json').read_text()), json.loads((out / 'boundary.json').read_text()),
        (out / 'original.sv').read_text())
    require(json.loads((out / 'architecture-candidate.json').read_text()) == candidate,
            'changed/incomplete/unproven production architecture candidate')
    for name, data in (("normalized.sv", normalized), ("architecture.sv", architecture),
                       ("memory-models.v", models), ("memory-stubs.v", stubs)):
        require((out / name).read_bytes() == data.encode(), 'changed production architecture artifact: ' + name)
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "boundary", "rtl", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    candidate = prepare(json.loads(args.manifest.read_text()), json.loads(args.boundary.read_text()), args.rtl.read_text(), args.out)
    print(json.dumps({k: v for k, v in candidate.items() if k != "entries"}, indent=2))


if __name__ == "__main__":
    main()
