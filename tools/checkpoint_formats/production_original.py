"""Original production RTL to extracted memory architecture composition.

Keep every semantic register in the relation, including later optimized bits.
Arrays are universally projected using the separately proven original adapters;
independent read-word closure precedes common-read induction. This component
certificate is deliberately not a gate map or checkpoint-loading authority.
"""

import json
from pathlib import Path
import re

from .codec import canonical, require
from .formal_state_map import sha
from .production_dut import audit_architecture
from .production_memory import _fragments, audit as memory_audit, reconstruct as memory_binding
from .production_memory_composition import clock_tree
from .production_queue import instances
from .production_register import _interface, cut_design
from .replay import IDENT, modules


FILES = ('binding.json', 'miter.sv', 'prove.tcl', 'original-results.tsv', 'jasper.log')
SCRIPT = '''clear -all
set paths [list binding $env(CHECKPOINT_ORIGINAL_BINDING) miter $env(CHECKPOINT_ORIGINAL_MITER) script $env(CHECKPOINT_ORIGINAL_SCRIPT)]
set hashes [dict create]
foreach {role path} $paths {dict set hashes $role [lindex [exec sha256sum $path] 0]}
analyze -sv $env(CHECKPOINT_ORIGINAL_MITER)
elaborate -top production_original_miter
clock clock
reset -none
prove -all
report -summary
set out [open original-results.tsv w]
puts $out "FORMAT\tproduction-original-v1"
puts "CHECKPOINT_ORIGINAL_RESET=none"
foreach {role path} $paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $hashes $role]} {error "Original proof input changed: $role"}
  puts $out "INPUT\t$role\t$digest"
  puts "CHECKPOINT_ORIGINAL_INPUT\t$role\t$digest"
}
foreach property [get_property_list] {
  set kind [get_property_info -list {type} $property]
  set status [get_property_info -list {status} $property]
  puts $out "PROPERTY\t$property\t$kind\t$status"
  puts "CHECKPOINT_ORIGINAL_PROPERTY\t$property\t$kind\t$status"
}
puts $out "END"
close $out
exit
'''


def reconstruct(architecture, memory_proof):
    architecture, memory_proof = Path(architecture).resolve(), Path(memory_proof).resolve()
    candidate = audit_architecture(architecture)
    arrays = memory_binding(architecture)
    memory_audit(architecture, memory_proof)
    entries = sorted(candidate['entries'], key=lambda e: e['state_id'])
    memories = [dict(entry=e, gate_components=e['architecture_path'].split('.')[:-1])
                for e in entries if e['kind'] == 'memory']
    paths = [architecture / name for name in ('original.sv', 'normalized.sv', 'architecture.sv',
             'memory-models.v', 'memory-stubs.v', 'architecture-candidate.json', 'manifest.json', 'boundary.json')]
    paths += [memory_proof / 'binding.json']
    paths += [memory_proof / cell / name for cell in arrays['shapes'] for name in
              ('binding.json', 'miter.sv', 'prove.tcl', 'memory-results.tsv', 'jasper.log')]
    binding = dict(original_composition_version=1, artifact_type='production_original_composition_obligations',
                architecture=str(architecture), memory_proof=str(memory_proof), top=candidate['top'],
                semantic_manifest_hash=candidate['semantic_manifest_hash'], retiming=False,
                reference_source=(architecture / 'normalized.sv').read_text(),
                implementation_source=(architecture / 'architecture.sv').read_text(),
                standard_models='', memory_source=(architecture / 'memory-models.v').read_text(),
                registers=[e for e in entries if e['kind'] == 'register'], memories=memories, arrays=arrays,
                prerequisites={str(p): sha(p.read_bytes()) for p in paths},
                register_bits=sum(e['width'] for e in entries if e['kind'] == 'register'),
                state_entries=candidate['state_entries'], state_bits=candidate['state_bits'],
                memory_instances=arrays['memory_instances'], memory_bits=arrays['memory_bits'],
                memory_words=arrays['memory_words'],
                read_ports=sum(len(e['entry']['memory']['reads']) for e in memories),
                formal_state_map_complete=False, gate_restore_authorized=False)
    validate_domains(binding)
    return binding


def validate_domains(binding):
    # Check topology as well as sampled CP equality: extra/gated edges cannot
    # be excluded by a theorem that samples only the target clock.
    clock_tree(binding)
    for side in ('reference', 'implementation'):
        design = modules(binding[side + '_source'])
        for header, body in design.values():
            events = re.findall(r'\balways\s*@\s*\(([^)]*)\)', body)
            require(len(events) == len(re.findall(r'\balways\b', body)) and
                    all(e.strip() == 'posedge clock' for e in events), 'unsupported original storage event')
        for item in binding['memories']:
            entry = item['entry']
            depth = entry['depth']
            require(depth > 0 and depth & (depth - 1) == 0, 'unsupported original address domain')
            if depth != 1:
                continue
            _, body = design[entry['module']]
            if side == 'reference':
                signals = [r['address'] for r in _fragments(design, entry)['reads']]
            else:
                child = instances(body)[entry['memory']['instance']]
                signals = [v for p, v in child['ports'].items() if p.startswith('RA')]
            for signal in signals:
                seen = set()
                while signal not in ("1'b0", "1'h0", "1'd0"):
                    require(re.fullmatch(IDENT, signal) and signal not in seen, 'unproven original single-word read domain')
                    seen.add(signal)
                    drivers = re.findall(r'\bassign\s+' + re.escape(signal) + r'\s*=\s*([^;]+);', body)
                    require(len(drivers) == 1, 'unproven original single-word read domain')
                    signal = drivers[0].strip()


def original_cut(binding):
    """Cut the actual original declarations/accesses, not a regenerated macro RTL.

    Exact write expressions, read addresses, clocks and surrounding register
    transitions stay visible. Unsupported/missing/extra accesses reject before
    Jasper; reconstruction also checks the complete original source inventory.
    """
    design = modules(binding['reference_source'])
    by_path = {m['entry']['original_path']: (i, m['entry']) for i, m in enumerate(binding['memories'])}
    require(len(by_path) == len(binding['memories']), 'duplicate original memory cut')
    generated, seen, active = [], set(), set()

    def build(name, prefix):
        require(name not in active, 'recursive original proof hierarchy')
        active.add(name)
        header, body = design[name]
        require('ckregister_' not in header + body, 'original cut identifier collision')
        interface, exposure, changes, assignments = _interface(header, body), {}, [], []
        if not re.search(r'\binput\b', header):
            body = re.sub(r'\b(?:input|output)\s+[^;]*;', '', body)
        for path, (index, entry) in by_path.items():
            parent = path.rpartition('.')[0]
            if (parent + '.' if parent else '') != prefix:
                continue
            require(entry['module'] == name and index not in seen, 'unbound original array module')
            seen.add(index)
            leaf = path.rsplit('.', 1)[-1]
            fragment = _fragments({name: (header, body)}, entry)
            patterns = [re.escape(fragment['declaration']),
                        rf'\bif\s*\({re.escape(fragment["write"]["enable"])}\)\s*begin\s*'
                        rf'{leaf}\[{IDENT}\]\s*<=\s*{IDENT}\s*;\s*end\b']
            patterns += [rf'\bassign\s+{r["data"]}\s*=\s*{leaf}\[{r["address"]}\]\s*;'
                         for r in fragment['reads']]
            for pattern in patterns:
                matches = list(re.finditer(pattern, body))
                require(len(matches) == 1, 'missing/ambiguous original array access')
                changes.append((matches[0].start(), matches[0].end(), ''))
            remainder = body
            for start, end, _ in sorted(changes, reverse=True):
                remainder = remainder[:start] + remainder[end:]
            require(not re.search(r'\b' + re.escape(leaf) + r'\b', remainder), 'uncut original memory access')
            aw, width = max(1, (entry['depth'] - 1).bit_length()), entry['width']
            ports = dict(CP=('output', 1, 'clock'), WE=('output', 1, fragment['write']['enable']),
                         WA=('output', aw, fragment['write']['address']),
                         WD=('output', width, fragment['write']['data']))
            for i, read in enumerate(fragment['reads']):
                ports[f'RA{i}'] = ('output', aw, read['address'])
                ports[f'Q{i}'] = ('input', width, read['data'])
            for port, (direction, width, signal) in ports.items():
                extra = f'ckregister_memory_{index}_{port}'
                exposure[extra] = dict(direction=direction, width=width,
                                       role='read_word' if direction == 'input' else 'memory_input')
                assignments.append(f'assign {signal} = {extra};' if direction == 'input' else
                                   f'assign {extra} = {signal};')
        for instance, child in instances(body).items():
            generated_name, child_interface, child_exposure = build(child['cell'], prefix + instance + '.')
            require(child_interface.keys() == child['ports'].keys(), 'incomplete original hierarchy interface')
            require(not exposure.keys() & child_exposure.keys(), 'duplicate original propagated array cut')
            exposure.update(child_exposure)
            connections = dict(child['ports'], **{p: p for p in child_exposure})
            replacement = generated_name + ' ' + instance + '(' + ', '.join(
                f'.{p}({v})' for p, v in connections.items()) + ');'
            changes.append((child['start'], child['end'], replacement))
        for start, end, replacement in sorted(changes, reverse=True):
            body = body[:start] + replacement + body[end:]
        body = re.sub(r'\balways\s*@\s*\(posedge clock\)\s*begin\s*end\b', '', body)
        require(not re.search(r'\breg\s+[^;]*\[0:\d+\]\s*;', body), 'omitted original array')
        generated_name = f'ckregister_reference_{len(generated)}'
        ports = [f'{d} [{w-1}:0] {p}' for p, (d, w) in interface.items()]
        ports += [f'{s["direction"]} [{s["width"]-1}:0] {p}' for p, s in exposure.items()]
        generated.append(f'module {generated_name}(' + ',\n'.join(ports) + ');\n' + body + '\n' +
                         '\n'.join(assignments) + '\nendmodule\n')
        active.remove(name)
        return generated_name, interface, exposure

    name, interface, exposure = build(binding['top'], '')
    require(seen == set(range(len(binding['memories']))), 'missing original array cut')
    return '\n'.join(generated), name, interface, exposure


def miter(binding, kind):
    require(kind in ('address', 'word'), 'unsupported original composition scope')
    reference, rn, ri, rexp = original_cut(binding)
    implementation, gn, gi, gexp = cut_design(binding, 'implementation')
    require(ri == gi and rexp == gexp, 'changed original/architecture full cut interface')
    ports, lines, connections = ['input clock'], [], [[], []]
    for port, (direction, width) in dict(ri, **{p: (s['direction'], s['width']) for p, s in rexp.items()}).items():
        role = rexp.get(port, {}).get('role')
        if direction == 'input':
            if role == 'read_word' and kind == 'address':
                pair = ['reference_' + port, 'implementation_' + port]
                ports.extend(f'input [{width-1}:0] {p}' for p in pair)
                lines.append(f'{port}_independent: cover property (@(posedge clock) relation && {pair[0]} != {pair[1]});')
            else:
                pair = [port, port]
                if port != 'clock':
                    ports.append(f'input [{width-1}:0] {port}')
        else:
            pair = ['reference_' + port, 'implementation_' + port]
            lines.extend(f'wire [{width-1}:0] {p};' for p in pair)
            if kind == 'word' or (role == 'memory_input' and re.search(r'_(?:RA\d+|CP)$', port)):
                lines.append(f'port_{port}: assert property (@(posedge clock) relation |-> {pair[0]} == {pair[1]});')
            if port.endswith('_CP'):
                for signal in pair:
                    lines.append(f'{signal}_clock: assert property (@(posedge clock) relation |-> {signal} == clock);')
        for i in range(2):
            connections[i].append(f'.{port}({pair[i]})')
    lines += [rn + ' reference(' + ', '.join(connections[0]) + ');',
              gn + ' implementation(' + ', '.join(connections[1]) + ');']
    expressions = [f'(reference.{e["original_path"]} == implementation.{e["architecture_path"]})'
                   for e in binding['registers']]
    require(expressions, 'empty original register relation')
    lines.append('wire relation = ' + ' && '.join(expressions) + ';')
    lines.append('relation_present: cover property (@(posedge clock) relation);')
    if kind == 'word':
        for index, (entry, expression) in enumerate(zip(binding['registers'], expressions)):
            lines.append(f'register_{index}_step: assert property (@(posedge clock) relation |=> {expression});')
            for bit in range(entry['width']):
                signal = 'reference.' + entry['original_path'] + (f'[{bit}]' if entry['width'] > 1 else '')
                for value in (0, 1):
                    lines.append(f'register_{index}_bit_{bit}_{value}: cover property (@(posedge clock) relation && {signal} == 1\'b{value});')
        for index, item in enumerate(binding['memories']):
            entry = item['entry']
            width, depth = entry['width'], entry['depth']
            aw = max(1, (depth - 1).bit_length())
            ports.extend([f'input [{aw-1}:0] watched_{index}',
                          f'input [{width-1}:0] old_reference_{index}, old_implementation_{index}'])
            lines.append(f"wire word_relation_{index} = watched_{index} < {aw+1}'d{depth} && old_reference_{index} == old_implementation_{index};")
            for side in ('reference', 'implementation'):
                p = f'{side}_ckregister_memory_{index}'
                lines.append(f'wire [{width-1}:0] next_{side}_{index} = ({p}_WE && {p}_WA == watched_{index}) ? {p}_WD : old_{side}_{index};')
            lines.append(f'word_{index}_step: assert property (@(posedge clock) relation && word_relation_{index} |-> next_reference_{index} == next_implementation_{index});')
            for label, condition in [('first', f'watched_{index} == 0'), ('last', f"watched_{index} == {aw}'d{depth-1}"),
                                     ('value_0', f'old_reference_{index} == 0'),
                                     ('value_1', f'old_reference_{index} == 1')]:
                lines.append(f'word_{index}_{label}: cover property (@(posedge clock) relation && word_relation_{index} && ({condition}));')
        lines += ['relation_edge: cover property (@(posedge clock) relation ##1 relation);',
                  'reset_seen: cover property (@(posedge clock) relation && reset);']
    return (reference + implementation + '\nmodule production_original_miter(' + ',\n'.join(ports) + ');\n' +
            '\n'.join(lines) + '\nendmodule\n').encode()


def proof_inputs(binding, kind):
    return dict(binding=canonical(dict(binding=binding, kind=kind)), miter=miter(binding, kind), script=SCRIPT.encode())


def properties(binding, kind):
    result = {'<embedded>::production_original_miter.' + p: k for p, k in
              re.findall(r'^(\w+): (assert|cover) property', miter(binding, kind).decode(), re.M)}
    result.update({p + ':precondition1': 'cover' for p, k in list(result.items()) if k == 'assert'})
    return result


def validate(binding, kind, proof, negative=False):
    proof = Path(proof)
    artifacts = proof_inputs(binding, kind)
    require(all((proof / name).read_bytes() == artifacts[role] for role, name in
                (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl'))), 'changed/unbound original proof input')
    rows = (proof / 'original-results.tsv').read_text().splitlines()
    require(rows[:1] == ['FORMAT\tproduction-original-v1'] and rows[-1:] == ['END'], 'incomplete original proof')
    inputs, results = {}, {}
    for line in rows[1:-1]:
        row = line.split('\t')
        if len(row) == 3 and row[0] == 'INPUT':
            require(row[1] not in inputs, 'duplicate original proof input')
            inputs[row[1]] = row[2]
        else:
            require(len(row) == 4 and row[0] == 'PROPERTY' and row[1] not in results, 'unsupported original proof result')
            results[row[1]] = tuple(row[2:])
    expected = properties(binding, kind)
    require(inputs == {r: sha(a) for r, a in artifacts.items()} and set(results) == set(expected), 'incomplete/stale original obligations')
    for prop, pk in expected.items():
        # Bit-value probes explore reachable values; they are not antecedents
        # of induction or authorities for eliminating captured state. Keep
        # their native unreachable results explicit. Every assertion and its
        # precondition cover must still prove/be nonvacuous in a positive job.
        exploratory = re.search(r'\.register_\d+_bit_\d+_[01]$', prop) is not None
        allowed = ('proven', 'cex') if negative and pk == 'assert' else ('proven',) if pk == 'assert' else ('covered', 'unreachable') if negative or exploratory else ('covered',)
        require(results[prop][0] == pk and results[prop][1] in allowed, 'unproven/vacuous original composition: ' + prop)
    log = (proof / 'jasper.log').read_text()
    require('ERROR' not in log and 'BLACK-BOX' not in log.upper() and 'CHECKPOINT_ORIGINAL_RESET=none' in log and
            'Exiting the analysis session with status 0.' in log and re.search(r'assumptions\s*:\s*0\b', log), 'failed/constrained/blackboxed original proof')
    raw = re.findall(r'^CHECKPOINT_ORIGINAL_PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$', log, re.M)
    require(len(raw) == len(expected) and {p: (k, s) for p, k, s in raw} == results, 'raw original results mismatch')
    hashes = re.findall(r'^CHECKPOINT_ORIGINAL_INPUT\t([^\t\n]+)\t([a-f0-9]{64})$', log, re.M)
    require(len(hashes) == len(artifacts) and dict(hashes) == inputs, 'raw original hashes mismatch')
    engine = {}
    for name, status in re.findall(r'The (?:cover )?property "([^"]+)" was (proven|covered) (?:in|at) ', log):
        engine.setdefault(name, set()).add(status)
    for name in re.findall(r'A counterexample \(cex\).*property "([^"]+)"', log):
        engine.setdefault(name, set()).add('cex')
    for name in re.findall(r'The cover property "([^"]+)" was proven unreachable in ', log):
        engine.setdefault(name, set()).add('unreachable')
    for prop, (_, status) in results.items():
        require(engine.get(prop.split('::', 1)[1]) == {status}, 'missing/conflicting original engine result: ' + prop)
    return dict(status='passed' if not negative else 'rejected', kind=kind,
                assertions_proven=sum(k == 'assert' and s == 'proven' for k, s in results.values()),
                covers=sum(k == 'cover' and s == 'covered' for k, s in results.values()),
                counterexamples={p: s for p, (k, s) in results.items() if k == 'assert' and s == 'cex'},
                unreachable_covers={p: s for p, (k, s) in results.items() if k == 'cover' and s == 'unreachable'},
                register_bits=binding['register_bits'], memory_bits=binding['memory_bits'])


def certificate(binding, address_proof, word_proof):
    validate_domains(binding)
    require(all(sha(Path(p).read_bytes()) == digest for p, digest in binding['prerequisites'].items()), 'changed original composition prerequisite')
    proofs = dict(address=Path(address_proof).resolve(), word=Path(word_proof).resolve())
    return dict(original_composition_version=1, artifact_type='production_original_architecture_composition',
                binding_sha256=sha(canonical(binding)),
                proofs={kind: dict(path=str(path), artifacts={n: sha((path / n).read_bytes()) for n in FILES}) for kind, path in proofs.items()},
                results={kind: validate(binding, kind, path) for kind, path in proofs.items()},
                registers=binding['registers'], memories=binding['memories'],
                state_entries=binding['state_entries'], state_bits=binding['state_bits'], register_bits=binding['register_bits'],
                memory_instances=binding['memory_instances'], memory_bits=binding['memory_bits'], memory_words=binding['memory_words'],
                read_ports=binding['read_ports'], original_to_architecture='inductive complete register/array equality',
                read_closure='proven with independent read words',
                memory_authority='all bound universal original word/read adapters and all actual port cones',
                formal_state_map_complete=False, gate_restore_authorized=False)
