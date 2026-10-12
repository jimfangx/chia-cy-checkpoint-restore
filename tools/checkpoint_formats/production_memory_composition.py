"""Close the production architecture/netlist memory cuts by native induction.

Read-address congruence is proved with *independent* read words on both sides.
Consequently equal complete arrays supply equal read words without a circular
assumption. A second proof preserves every existing register/port obligation
and adds a universally addressed word transition for every physical memory.
Original RTL composition and a complete independently audited map remain
separate obligations; this certificate cannot authorize gate loading.
"""

import argparse
import json
from pathlib import Path
import re

from .codec import canonical, require
from .formal_state_map import sha
from .production_memory import audit as memory_audit, reconstruct as memory_binding
from .production_optimized import certificate as optimized_certificate
from .production_register import (
    _expression, _interface, cut_design, miter as register_miter, reconstruct as register_binding,
    validate as register_validate,
)
from .production_queue import instances as hierarchy_instances
from .replay import modules


FILES = ('binding.json', 'miter.sv', 'prove.tcl', 'composition-results.tsv', 'jasper.log')
SCRIPT = '''clear -all
set paths [list binding $env(CHECKPOINT_COMPOSITION_BINDING) miter $env(CHECKPOINT_COMPOSITION_MITER) script $env(CHECKPOINT_COMPOSITION_SCRIPT)]
set hashes [dict create]
foreach {role path} $paths {dict set hashes $role [lindex [exec sha256sum $path] 0]}
analyze -sv $env(CHECKPOINT_COMPOSITION_MITER)
elaborate -top production_composition_miter
clock clock
reset -none
prove -all
report -summary
set out [open composition-results.tsv w]
puts $out "FORMAT\tproduction-composition-v1"
puts "CHECKPOINT_COMPOSITION_RESET=none"
foreach {role path} $paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $hashes $role]} {error "Composition input changed: $role"}
  puts $out "INPUT\t$role\t$digest"
  puts "CHECKPOINT_COMPOSITION_INPUT\t$role\t$digest"
}
foreach property [get_property_list] {
  set kind [get_property_info -list {type} $property]
  set status [get_property_info -list {status} $property]
  puts $out "PROPERTY\t$property\t$kind\t$status"
  puts "CHECKPOINT_COMPOSITION_PROPERTY\t$property\t$kind\t$status"
}
puts $out "END"
close $out
exit
'''


def reconstruct(architecture, synthesis_evidence, register_proof, memory_proof, optimized):
    architecture, synthesis_evidence, register_proof, memory_proof, optimized = (
        Path(p).resolve() for p in (architecture, synthesis_evidence, register_proof, memory_proof, optimized))
    registers = register_binding(architecture, synthesis_evidence, True, True)
    report = register_validate(registers, register_proof)
    require(not report['counterexamples'] and report['optimized_predicates_proven'] == 130,
            'unproven production register/port premises')
    classified = optimized_certificate(architecture, synthesis_evidence, register_proof)
    require(json.loads(optimized.read_text()) == classified, 'changed/unbound optimized premises')
    arrays = memory_binding(architecture)
    memory_audit(architecture, memory_proof)
    clocks = clock_tree(registers)
    validate_read_domains(registers)
    by_id = {m['state_id']: m for m in arrays['instances']}
    require(len(by_id) == len(arrays['instances']) == len(registers['memories']), 'incomplete memory composition')
    instances = []
    for index, item in enumerate(registers['memories']):
        entry = item['entry']
        original = by_id.pop(entry['state_id'])
        require(all(original[k] == entry[k] for k in
                    ('state_id', 'original_path', 'architecture_path', 'module', 'width', 'depth')) and
                original['cell'] == entry['memory']['cell'], 'unbound original/physical memory')
        shape = arrays['shapes'][original['cell']]
        instances.append(dict(index=index, state_id=entry['state_id'], original_path=entry['original_path'],
                              architecture_path=entry['architecture_path'], gate_components=item['gate_components'],
                              cell=original['cell'], width=entry['width'], depth=entry['depth'],
                              read_ports=shape['read_ports'], universal_original_adapter=str(memory_proof / original['cell']),
                              original_adapter_properties=['word_step'] + [f'read_{i}' for i in range(shape['read_ports'])]))
    require(not by_id and sum(i['width'] * i['depth'] for i in instances) == arrays['memory_bits'],
            'missing composed memory contents')
    prerequisite_paths = [register_proof / n for n in ('binding.json', 'miter.sv', 'prove.tcl', 'register-results.tsv', 'jasper.log')]
    prerequisite_paths += [memory_proof / 'binding.json']
    prerequisite_paths += [memory_proof / cell / n for cell in arrays['shapes']
                          for n in ('binding.json', 'miter.sv', 'prove.tcl', 'memory-results.tsv', 'jasper.log')]
    return dict(composition_version=1, artifact_type='production_memory_composition_obligations',
                architecture=str(architecture), synthesis_evidence=str(synthesis_evidence),
                register_proof=str(register_proof), memory_proof=str(memory_proof), optimized=str(optimized),
                optimized_sha256=sha(optimized.read_bytes()), registers=registers, arrays=arrays,
                clock_tree=clocks,
                prerequisite_artifacts={str(p): sha(p.read_bytes()) for p in prerequisite_paths},
                instances=instances, memory_instances=len(instances), memory_bits=arrays['memory_bits'],
                memory_words=arrays['memory_words'], read_ports=sum(i['read_ports'] for i in instances),
                formal_state_map_complete=False, gate_restore_authorized=False)


def validate_read_domains(registers):
    """Equal arrays imply equal reads only at valid addresses.

    Power-of-two depths fill the concrete model's address domain, except for
    depth one with its one-bit port. For those actual instances require literal
    zero or an exact continuous alias of zero on BOTH logic hierarchies.
    """
    for item in registers['memories']:
        depth = item['entry']['depth']
        require(depth > 0 and depth & (depth - 1) == 0, 'unsupported composed memory address domain')
        if depth != 1:
            continue
        for side in ('reference', 'implementation'):
            design = modules(registers[side + '_source'])
            name = registers['top']
            components = (item['entry']['architecture_path'].split('.')[:-1] if side == 'reference'
                          else item['gate_components'])
            for component in components:
                _, body = design[name]
                child = hierarchy_instances(body)[component]
                name = child['cell']
            for port, signal in child['ports'].items():
                if not port.startswith('RA'):
                    continue
                visited = set()
                while not re.fullmatch(r"1'[bhd]0", signal):
                    require(re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', signal) and signal not in visited,
                            'out-of-range/unproven single-word read address')
                    visited.add(signal)
                    drivers = re.findall(r'\bassign\s+' + re.escape(signal) + r'\s*=\s*([^;]+);', body)
                    require(len(drivers) == 1, 'out-of-range/unproven single-word read address')
                    signal = drivers[0].strip()


def clock_tree(registers):
    """Reject gated/derived clocks: sampled equality alone cannot exclude glitches."""
    memory_cells = set(modules(registers['memory_source']))
    standard_cells = set(modules(registers['standard_models']))
    result = {}
    for side in ('reference', 'implementation'):
        design = modules(registers[side + '_source'])
        checked = []
        for name, (header, body) in design.items():
            interface = _interface(header, body)
            has_clock = 'clock' in interface
            require(not has_clock or list(interface['clock']) == ['input', 1], 'unsupported composition module clock')
            if not has_clock:
                require(not re.search(r'\b(?:reg|always)\b', body), 'stateful composition module without target clock')

            def aliases(signal):
                chain = []
                while signal != 'clock':
                    require(signal not in chain, 'cyclic composition clock alias')
                    chain.append(signal)
                    drivers = re.findall(r'\bassign\s+' + re.escape(signal) + r'\s*=\s*([^;]+);', body)
                    require(len(drivers) == 1 and re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', drivers[0].strip()),
                            'derived/gated storage clock unsupported')
                    signal = drivers[0].strip()
                require(has_clock, 'composition clock alias has no target input')
                return chain + ['clock']

            for instance, child in hierarchy_instances(body).items():
                cell, ports = child['cell'], child['ports']
                if cell in memory_cells or cell == 'CKDFF':
                    require('CP' in ports, 'missing composition storage clock')
                    checked.append(dict(port=name + '.' + instance + '.CP', aliases=aliases(ports['CP'])))
                elif cell in design:
                    child_interface = _interface(*design[cell])
                    if 'clock' in child_interface:
                        require('clock' in ports, 'missing composition hierarchy clock')
                        checked.append(dict(port=name + '.' + instance + '.clock', aliases=aliases(ports['clock'])))
                else:
                    require(cell in standard_cells and 'CP' not in ports, 'unknown composition clock cell')
        result[side] = checked
    return result


def address_miter(binding):
    """No common read words: this proves the premise needed to close the cuts."""
    registers = binding['registers']
    reference, rn, ri, rexp = cut_design(registers, 'reference')
    implementation, gn, gi, gexp = cut_design(registers, 'implementation')
    require({p: list(s) for p, s in ri.items()} == {p: list(s) for p, s in gi.items()} and rexp == gexp,
            'incompatible read closure interfaces')
    ports, lines, connections = ['input clock'], [], [[], []]
    interface = dict(ri, **{p: (s['direction'], s['width']) for p, s in rexp.items()})
    for port, (direction, width) in interface.items():
        if direction == 'input':
            if rexp.get(port, {}).get('role') == 'read_word':
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
            if rexp.get(port, {}).get('role') == 'memory_input' and re.search(r'_(?:RA\d+|CP)$', port):
                lines.append(f'{port}_equal: assert property (@(posedge clock) relation |-> {pair[0]} == {pair[1]});')
                if port.endswith('_CP'):
                    for side in pair:
                        lines.append(f'{side}_target_clock: assert property (@(posedge clock) relation |-> {side} == clock);')
        for i in range(2):
            connections[i].append(f'.{port}({pair[i]})')
    for i, (side, name) in enumerate((('reference', rn), ('implementation', gn))):
        lines.append(name + ' ' + side + '(' + ', '.join(connections[i]) + ');')
    relation = [_expression(g) for g in registers['groups']]
    relation += [f"(reference.{p['entry']['original_path']}[{p['bit']}] == 1'b{p['value']})"
                 for p in registers.get('optimized_predicates', [])]
    lines.append('wire relation = ' + ' && '.join(relation) + ';')
    lines.append('closure_relation: cover property (@(posedge clock) relation);')
    return (registers['standard_models'] + reference + implementation + '\nmodule production_composition_miter(' +
            ',\n'.join(ports) + ');\n' + '\n'.join(lines) + '\nendmodule\n').encode()


def word_miter(binding):
    """Keep EVERY existing native obligation and add ALL memory word updates."""
    text = register_miter(binding['registers']).decode().replace('production_register_miter', 'production_composition_miter')
    ports, lines = [], []
    for item in binding['instances']:
        index, width, depth = item['index'], item['width'], item['depth']
        aw = max(1, (depth - 1).bit_length())
        ports.extend([f'input [{aw-1}:0] watched_{index}',
                      f'input [{width-1}:0] old_reference_{index}, old_implementation_{index}'])
        lines.append(f"wire word_relation_{index} = watched_{index} < {aw+1}'d{depth} && "
                     f'old_reference_{index} == old_implementation_{index};')
        for side in ('reference', 'implementation'):
            prefix = f'{side}_ckregister_memory_{index}'
            lines.append(f'wire [{width-1}:0] next_{side}_{index} = '
                         f'({prefix}_WE && {prefix}_WA == watched_{index}) ? {prefix}_WD : old_{side}_{index};')
        lines.append(f'word_{index}_step: assert property (@(posedge clock) relation && word_relation_{index} |-> '
                     f'next_reference_{index} == next_implementation_{index});')
        for end, address in (('first', 0), ('last', depth - 1)):
            lines.append(f"word_{index}_{end}: cover property (@(posedge clock) relation && word_relation_{index} && "
                         f"watched_{index} == {aw}'d{address});")
        for value in (0, 1):
            lines.append(f"word_{index}_value_{value}: cover property (@(posedge clock) relation && word_relation_{index} && "
                         f"old_reference_{index} == {width}'d{value});")
    marker = 'module production_composition_miter(input clock'
    require(text.count(marker) == 1 and text.endswith('endmodule\n'), 'unsupported production register miter')
    text = text.replace(marker, 'module production_composition_miter(' + ',\n'.join(ports) + ',\ninput clock', 1)
    text = text[:-len('endmodule\n')] + '\n'.join(lines) + '\nendmodule\n'
    return text.encode()


def proof_inputs(binding, kind):
    require(kind in ('address', 'word'), 'unsupported production composition scope')
    return dict(binding=canonical(dict(binding=binding, kind=kind)),
                miter=(address_miter if kind == 'address' else word_miter)(binding), script=SCRIPT.encode())


def properties(binding, kind):
    text = proof_inputs(binding, kind)['miter'].decode()
    result = {'<embedded>::production_composition_miter.' + p: k for p, k in
              re.findall(r'^(\w+): (assert|cover) property', text, re.M)}
    result.update({p + ':precondition1': 'cover' for p, k in list(result.items()) if k == 'assert'})
    return result


def validate(binding, kind, proof, negative=False):
    proof = Path(proof)
    artifacts = proof_inputs(binding, kind)
    require(all((proof / name).read_bytes() == artifacts[role] for role, name in
                (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl'))),
            'changed/unbound memory composition inputs')
    rows = (proof / 'composition-results.tsv').read_text().splitlines()
    require(rows[:1] == ['FORMAT\tproduction-composition-v1'] and rows[-1:] == ['END'], 'incomplete memory composition proof')
    inputs, results = {}, {}
    for line in rows[1:-1]:
        row = line.split('\t')
        if len(row) == 3 and row[0] == 'INPUT':
            require(row[1] not in inputs, 'duplicate composition input')
            inputs[row[1]] = row[2]
        else:
            require(len(row) == 4 and row[0] == 'PROPERTY' and row[1] not in results, 'unsupported composition result')
            results[row[1]] = tuple(row[2:])
    expected = properties(binding, kind)
    require(inputs == {r: sha(a) for r, a in artifacts.items()} and set(results) == set(expected),
            'stale/incomplete memory composition identity or obligations')
    for prop, property_kind in expected.items():
        status = results[prop][1]
        pending = '.pending_' in prop
        require(results[prop][0] == property_kind and status in
                (('proven', 'cex') if property_kind == 'assert' and negative else ('proven',) if property_kind == 'assert'
                 else ('covered', 'unreachable') if pending or negative else ('covered',)),
                'unproven/vacuous memory composition: ' + prop)
    log = (proof / 'jasper.log').read_text()
    require('ERROR' not in log and 'BLACK-BOX' not in log.upper() and 'CHECKPOINT_COMPOSITION_RESET=none' in log and
            'Exiting the analysis session with status 0.' in log and re.search(r'assumptions\s*:\s*0\b', log),
            'failed/constrained/blackboxed memory composition')
    raw = re.findall(r'^CHECKPOINT_COMPOSITION_PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$', log, re.M)
    require(len(raw) == len(expected) and {p: (k, s) for p, k, s in raw} == results, 'raw composition property mismatch')
    hashes = re.findall(r'^CHECKPOINT_COMPOSITION_INPUT\t([^\t\n]+)\t([a-f0-9]{64})$', log, re.M)
    require(len(hashes) == len(artifacts) and dict(hashes) == inputs, 'raw composition identity mismatch')
    engine = {}
    for name, status in re.findall(r'The (?:cover )?property "([^"]+)" was (proven|covered) (?:in|at) ', log):
        engine.setdefault(name, set()).add(status)
    for name in re.findall(r'A counterexample \(cex\).*property "([^"]+)"', log):
        engine.setdefault(name, set()).add('cex')
    for name in re.findall(r'The cover property "([^"]+)" was proven unreachable in ', log):
        engine.setdefault(name, set()).add('unreachable')
    for prop, (_, status) in results.items():
        require(engine.get(prop.split('::', 1)[1]) == {status}, 'missing/conflicting composition engine result: ' + prop)
    if kind == 'word' and not negative and 'register_proof' in binding:
        for line in (Path(binding['register_proof']) / 'register-results.tsv').read_text().splitlines():
            row = line.split('\t')
            if len(row) == 4 and row[0] == 'PROPERTY':
                prop = row[1].replace('production_register_miter', 'production_composition_miter')
                require(results.get(prop) == tuple(row[2:]), 'changed/lost retained native register obligation: ' + prop)
    return dict(status='passed' if not negative else 'rejected', kind=kind,
                assertions_proven=sum(k == 'assert' and s == 'proven' for k, s in results.values()),
                covers=sum(k == 'cover' and s == 'covered' for k, s in results.values()),
                counterexamples={p: s for p, (k, s) in results.items() if k == 'assert' and s == 'cex'},
                unreachable_covers={p: s for p, (k, s) in results.items() if k == 'cover' and s == 'unreachable'},
                memory_instances=binding['memory_instances'], memory_bits=binding['memory_bits'],
                memory_words=binding['memory_words'], read_ports=binding['read_ports'],
                formal_state_map_complete=False, gate_restore_authorized=False)


def certificate(binding, address_proof, word_proof):
    validate_read_domains(binding['registers'])
    require(all(sha(Path(p).read_bytes()) == digest for p, digest in binding['prerequisite_artifacts'].items()),
            'changed native memory composition prerequisite')
    proofs = dict(address=Path(address_proof).resolve(), word=Path(word_proof).resolve())
    results = {kind: validate(binding, kind, proof) for kind, proof in proofs.items()}
    return dict(composition_version=1, artifact_type='conditional_production_memory_composition',
                binding_sha256=sha(canonical(binding)),
                proofs={kind: dict(path=str(path), artifacts={n: sha((path / n).read_bytes()) for n in FILES})
                        for kind, path in proofs.items()}, results=results, instances=binding['instances'],
                memory_instances=binding['memory_instances'], memory_bits=binding['memory_bits'],
                memory_words=binding['memory_words'], read_ports=binding['read_ports'],
                read_closure='proven with independent reference/implementation read words',
                architecture_to_netlist_memory_induction='proven conditional on retained register/predicate relation and complete current array equality',
                original_to_architecture_composition='unproven',
                formal_state_map_complete=False, gate_restore_authorized=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'register-proof', 'memory-proof', 'optimized',
                 'address-proof', 'word-proof', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    binding = reconstruct(args.architecture, args.synthesis_evidence, args.register_proof, args.memory_proof, args.optimized)
    result = certificate(binding, args.address_proof, args.word_proof)
    args.out.mkdir(parents=True, exist_ok=False)
    path = args.out / 'memory-composition.json'
    path.write_bytes(canonical(result))
    print(json.dumps(dict(status='passed', certificate=str(path.resolve()), memory_instances=result['memory_instances'],
                          memory_bits=result['memory_bits'], formal_state_map_complete=False, gate_restore_authorized=False)))


if __name__ == '__main__':
    main()
