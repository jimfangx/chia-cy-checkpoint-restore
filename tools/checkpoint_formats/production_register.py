"""Build-bound flattened production register and memory-port proof obligations.

Names propose relationships; Jasper establishes their transitions. Array words
are common universal cuts, with all addresses/writes/clocks checked separately.
Optimized reference state remains unconstrained and explicitly pending. Neither
a partial proof nor this binding authorizes checkpoint deposits.
"""

import json
from pathlib import Path
import re

from .codec import canonical, require
from .formal_state_map import sha
from .production_context import ansi_shapes
from .production_dut import audit_architecture
from .production_queue import gate_expr, instances, port_shapes, reconstruct as queue_binding
from .replay import modules


SCRIPT = '''clear -all
set paths [list binding $env(CHECKPOINT_REGISTER_BINDING) miter $env(CHECKPOINT_REGISTER_MITER) script $env(CHECKPOINT_REGISTER_SCRIPT)]
set hashes [dict create]
foreach {role path} $paths {dict set hashes $role [lindex [exec sha256sum $path] 0]}
analyze -sv $env(CHECKPOINT_REGISTER_MITER)
elaborate -top production_register_miter
clock clock
reset -none
prove -all
report -summary
set out [open register-results.tsv w]
puts $out "FORMAT\tproduction-register-v1"
puts "CHECKPOINT_REGISTER_RESET=none"
foreach {role path} $paths {
  set digest [lindex [exec sha256sum $path] 0]
  if {$digest ne [dict get $hashes $role]} {error "Register input changed: $role"}
  puts $out "INPUT\t$role\t$digest"
  puts "CHECKPOINT_REGISTER_INPUT\t$role\t$digest"
}
foreach property [get_property_list] {
  set kind [get_property_info -list {type} $property]
  set status [get_property_info -list {status} $property]
  puts $out "PROPERTY\t$property\t$kind\t$status"
  puts "CHECKPOINT_REGISTER_PROPERTY\t$property\t$kind\t$status"
}
puts $out "END"
close $out
exit
'''


def reconstruct(architecture, synthesis_evidence, opcode_predicate=False):
    architecture, evidence = Path(architecture), Path(synthesis_evidence)
    candidate = audit_architecture(architecture)
    # Reconstruct the complete raw synthesis/model binding, including queried
    # retiming, every current input and every actual physical storage span.
    prior = queue_binding(architecture, evidence)
    netlist = (evidence / 'netlist-design.v').read_text()
    registers = [e for e in candidate['entries'] if e['kind'] == 'register']
    memories = [e for e in candidate['entries'] if e['kind'] == 'memory']
    flat = {}
    for entry in registers:
        path = entry['original_path'].replace('.', '_')
        require(path not in flat, 'ambiguous flattened semantic register')
        flat[path] = entry
    groups, matched, memory_matches = {}, set(), {}
    for storage in prior['physical_storage_obligations']:
        components = storage['instance_components']
        if storage['kind'] == 'memory':
            path = '_'.join(components)
            matches = [e for e in memories if e['architecture_path'].rsplit('.', 1)[0].replace('.', '_') == path]
            require(len(matches) == 1, 'unmatched/ambiguous flattened physical memory')
            entry = matches[0]
            require(storage['name'] == 'contents' and storage['cell'] == entry['memory']['cell'] and
                    (storage['width'], storage['depth']) == (entry['width'], entry['depth']) and
                    entry['state_id'] not in memory_matches, 'changed/duplicate physical memory shape')
            memory_matches[entry['state_id']] = dict(entry=entry, gate_components=components)
            continue
        require(storage['cell'] == 'CKDFF' and storage['name'] == 'state' and
                storage['width'] == storage['depth'] == 1, 'unsupported flattened sequential cell')
        match = re.fullmatch(r'(.*)_reg(?:\[(\d+)\])?', components[-1])
        require(match is not None, 'unsupported physical register candidate naming')
        stem = '_'.join(components[:-1] + [match[1]])
        require(stem in flat, 'unmatched flattened physical register')
        entry, bit = flat[stem], int(match[2] or 0)
        require(bit < entry['width'] and (entry['width'] == 1) == (match[2] is None),
                'reshaped flattened physical register')
        require((entry['state_id'], bit) not in matched, 'duplicate flattened register candidate')
        matched.add((entry['state_id'], bit))
        group = groups.setdefault(entry['state_id'], dict(entry=entry, bits=[]))
        group['bits'].append(dict(original_bit=bit, gate_components=components, xor=0, proof_status='unproven'))
    for group in groups.values():
        group['bits'].sort(key=lambda b: b['original_bit'])
    pending = [dict(entry=e, bits=[b for b in range(e['width']) if (e['state_id'], b) not in matched],
                    reason='optimized semantic bits require independent predicate/irrelevance composition')
               for e in registers if any((e['state_id'], b) not in matched for b in range(e['width']))]
    require(len(memory_matches) == len(memories) and len(matched) == prior['physical_register_bits'] and
            len(matched) + sum(len(e['bits']) for e in pending) == prior['semantic_register_bits'],
            'incomplete flattened storage membership')
    binding = dict(register_proof_version=1, artifact_type='production_flattened_state_obligations',
                top=candidate['top'], queue_binding_sha256=sha(canonical(prior)),
                synthesis_inputs=prior['synthesis_inputs'], synthesis_log_sha256=prior['synthesis_log_sha256'],
                model_binding=prior['model_binding'], inventory_sha256=prior['inventory_sha256'],
                semantic_manifest_hash=candidate['semantic_manifest_hash'],
                boundary_manifest_sha256=sha((architecture / 'boundary.json').read_bytes()),
                reference_source=(architecture / 'architecture.sv').read_text(), implementation_source=netlist,
                standard_models=prior['standard_models'], memory_source=(architecture / 'memory-models.v').read_text(),
                groups=[groups[k] for k in sorted(groups)], pending_registers=pending,
                memories=[memory_matches[k] for k in sorted(memory_matches)],
                semantic_register_bits=prior['semantic_register_bits'], physical_register_bits=len(matched),
                semantic_state_entries=candidate['state_entries'], retiming=False,
                formal_state_map_complete=False, gate_restore_authorized=False)
    if opcode_predicate:
        # The actual selected fuzzer omits atomics. This is an explicit proposed
        # predicate, not an inferred constant: preservation and every memory
        # port/output must prove, and the semantic checkpoint must satisfy it.
        entries = [e for e in registers if e['original_path'] == 'model.a__opcode']
        require(len(entries) == 1 and entries[0]['width'] == 3 and entries[0]['module'] == 'TLRAMModel' and
                (entries[0]['state_id'], 1) not in matched, 'unsupported opcode predicate candidate')
        binding['optimized_predicates'] = [dict(entry=entries[0], bit=1, value=0, proof_status='unproven')]
    return binding


def _interface(header, body):
    return ansi_shapes(header) if re.search(r'\binput\b', header) else port_shapes(header, body)


def cut_design(binding, side):
    """Keep the exact logic/storage hierarchy, replacing only concrete arrays.

    All model ports have witnesses. Read words are arbitrary common inputs;
    write/clock/read-address witnesses are mandatory congruence obligations.
    Original and gate instance names are preserved for state relationships.
    """
    design = modules(binding[side + '_source'])
    models = modules(binding['standard_models'])
    memories = modules(binding['memory_source'])
    by_path = {}
    for index, item in enumerate(binding['memories']):
        path = (item['entry']['architecture_path'].rsplit('.', 1)[0] if side == 'reference' else
                '.'.join(item['gate_components']))
        require(path not in by_path, 'duplicate memory cut path')
        by_path[path] = index, item
    generated, seen, active = [], set(), set()

    def build(name, prefix):
        require(name not in active, 'recursive register proof hierarchy')
        active.add(name)
        header, body = design[name]
        require('ckregister_' not in header + body, 'register cut identifier collision')
        interface, exposure, changes = _interface(header, body), {}, []
        if not re.search(r'\binput\b', header):
            body = re.sub(r'\b(?:input|output)\s+[^;]*;', '', body)
        for instance, child in instances(body).items():
            cell, connections = child['cell'], child['ports']
            path = prefix + instance
            if cell in memories:
                require(path in by_path, 'unbound concrete memory cut')
                index, item = by_path[path]
                require(index not in seen and cell == item['entry']['memory']['cell'], 'changed/duplicate memory cut')
                seen.add(index)
                ports = ansi_shapes(memories[cell][0])
                require(ports.keys() == connections.keys(), 'incomplete concrete memory cut ports')
                replacement = []
                for port, (direction, width) in ports.items():
                    extra = f'ckregister_memory_{index}_{port}'
                    exposure[extra] = dict(direction='input' if direction == 'output' else 'output', width=width,
                                           role='read_word' if direction == 'output' else 'memory_input')
                    replacement.append(f'assign {connections[port]} = {extra};' if direction == 'output' else
                                       f'assign {extra} = {connections[port]};')
                replacement = '\n'.join(replacement)
            elif cell in models:
                require(side == 'implementation', 'unexpected reference standard cell')
                continue
            else:
                require(cell in design, 'unknown register proof hierarchy child')
                generated_name, child_interface, child_exposure = build(cell, path + '.')
                require(child_interface.keys() == connections.keys(), 'incomplete hierarchy child ports')
                require(not exposure.keys() & child_exposure.keys(), 'duplicate propagated memory cut')
                exposure.update(child_exposure)
                connections = dict(connections, **{p: p for p in child_exposure})
                replacement = generated_name + ' ' + instance + '(' + ', '.join(
                    f'.{p}({v})' for p, v in connections.items()) + ');'
            changes.append((child['start'], child['end'], replacement))
        for start, end, replacement in sorted(changes, reverse=True):
            body = body[:start] + replacement + body[end:]
        generated_name = f'ckregister_{side}_{len(generated)}'
        ports = [f'{d} [{w-1}:0] {p}' for p, (d, w) in interface.items()]
        ports += [f'{s["direction"]} [{s["width"]-1}:0] {p}' for p, s in exposure.items()]
        generated.append(f'module {generated_name}(' + ',\n'.join(ports) + ');\n' + body + '\nendmodule\n')
        active.remove(name)
        return generated_name, interface, exposure

    name, interface, exposure = build(binding['top'], '')
    require(seen == set(range(len(binding['memories']))), 'omitted complete-memory cut')
    return '\n'.join(generated), name, interface, exposure


def _expression(group):
    path, width = group['entry']['original_path'], group['entry']['width']
    reference, implementation = [], []
    for bit in reversed(group['bits']):
        reference.append('reference.' + path + (f'[{bit["original_bit"]}]' if width > 1 else ''))
        components = bit['gate_components']
        gate = '.'.join(components[:-1] + [gate_expr(components[-1])])
        implementation.append(f'(implementation.{gate} ^ 1\'b{bit["xor"]})')
    require(reference, 'empty register relationship')
    return '({' + ','.join(reference) + '} == {' + ','.join(implementation) + '})'


def miter(binding):
    reference, rname, ri, rexp = cut_design(binding, 'reference')
    implementation, iname, ii, iexp = cut_design(binding, 'implementation')
    require({p: list(s) for p, s in ri.items()} == {p: list(s) for p, s in ii.items()} and rexp == iexp,
            'changed complete boundary/memory cut interface')
    ports, lines, connections = ['input clock'], [], [[], []]
    interface = dict(ri, **{p: (s['direction'], s['width']) for p, s in rexp.items()})
    for p, (direction, width) in interface.items():
        if direction == 'input':
            signals = [p, p]
            if p != 'clock':
                ports.append(f'input [{width-1}:0] {p}')
        else:
            signals = ['reference_' + p, 'implementation_' + p]
            lines.extend(f'wire [{width-1}:0] {signal};' for signal in signals)
            lines.append(f'port_{p}: assert property (@(posedge clock) relation |-> {signals[0]} == {signals[1]});')
        for i in range(2):
            connections[i].append(f'.{p}({signals[i]})')
    for i, (side, name) in enumerate((('reference', rname), ('implementation', iname))):
        lines.append(name + ' ' + side + '(' + ', '.join(connections[i]) + ');')
    expressions = [_expression(g) for g in binding['groups']]
    predicates = [f'(reference.{p["entry"]["original_path"]}[{p["bit"]}] == 1\'b{p["value"]})'
                  for p in binding.get('optimized_predicates', [])]
    lines.append('wire relation = ' + ' && '.join(expressions + predicates) + ';')
    for index, predicate in enumerate(predicates):
        lines.append(f'predicate_{index}_step: assert property (@(posedge clock) relation |=> {predicate});')
        lines.append(f'predicate_{index}_holds: cover property (@(posedge clock) relation && {predicate});')
    for index, (group, expression) in enumerate(zip(binding['groups'], expressions)):
        lines.append(f'state_{index}_step: assert property (@(posedge clock) relation |=> {expression});')
        for bit_index, bit in enumerate(group['bits']):
            path = '.'.join(bit['gate_components'][:-1] + [gate_expr(bit['gate_components'][-1])])
            for value in (0, 1):
                lines.append(f'state_{index}_bit_{bit_index}_{value}: cover property (@(posedge clock) relation && '
                             f'implementation.{path} == 1\'b{value});')
    for index, pending in enumerate(binding['pending_registers']):
        entry = pending['entry']
        for bit in pending['bits']:
            path = entry['original_path'] + (f'[{bit}]' if entry['width'] > 1 else '')
            for value in (0, 1):
                lines.append(f'pending_{index}_bit_{bit}_{value}: cover property (@(posedge clock) relation && '
                             f'reference.{path} == 1\'b{value});')
    lines.extend(['relation_edge: cover property (@(posedge clock) relation ##1 relation);',
                  'reset_seen: cover property (@(posedge clock) relation && reset);'])
    return (binding['standard_models'] + reference + implementation + '\nmodule production_register_miter(' +
            ',\n'.join(ports) + ');\n' + '\n'.join(lines) + '\nendmodule\n').encode()


def proof_inputs(binding):
    return dict(binding=canonical(binding), miter=miter(binding), script=SCRIPT.encode())


def properties(binding):
    result = {'<embedded>::production_register_miter.' + n: k for n, k in
              re.findall(r'^(\w+): (assert|cover) property', miter(binding).decode(), re.M)}
    result.update({n + ':precondition1': 'cover' for n, k in list(result.items()) if k == 'assert'})
    return result


def validate(binding, proof, negative=False):
    proof = Path(proof)
    artifacts = proof_inputs(binding)
    for role, name in (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')):
        require((proof / name).read_bytes() == artifacts[role], 'changed/unbound register proof inputs')
    rows = (proof / 'register-results.tsv').read_text().splitlines()
    require(rows[:1] == ['FORMAT\tproduction-register-v1'] and rows[-1:] == ['END'], 'incomplete register evidence')
    inputs, results = {}, {}
    for line in rows[1:-1]:
        row = line.split('\t')
        if len(row) == 3 and row[0] == 'INPUT':
            require(row[1] not in inputs, 'duplicate register input')
            inputs[row[1]] = row[2]
        else:
            require(len(row) == 4 and row[0] == 'PROPERTY' and row[1] not in results, 'unsupported register result')
            results[row[1]] = tuple(row[2:])
    expected = properties(binding)
    require(inputs == {r: sha(a) for r, a in artifacts.items()}, 'stale register proof identity')
    require(set(results) == set(expected), 'missing/extra register obligations')
    for name, kind in expected.items():
        # Pending-bit covers explore independence of optimized reference state.
        # A native unreachable result is retained as a failed independence
        # challenge, never promoted to a constant/irrelevance mapping. Every
        # transition/output precondition and physical-bit cover must be covered.
        pending = kind == 'cover' and '.pending_' in name
        require(results[name][0] == kind and results[name][1] in
                (('proven', 'cex') if kind == 'assert' else ('covered', 'unreachable') if pending or negative else ('covered',)),
                'incomplete/vacuous register obligation: ' + name)
    log = (proof / 'jasper.log').read_text()
    require('ERROR' not in log and 'BLACK-BOX' not in log.upper() and
            'CHECKPOINT_REGISTER_RESET=none' in log and 'Exiting the analysis session with status 0.' in log and
            re.search(r'assumptions\s*:\s*0\b', log), 'failed/constrained/blackboxed register proof')
    raw = re.findall(r'^CHECKPOINT_REGISTER_PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$', log, re.M)
    require(len(raw) == len(expected) and {p: (k, s) for p, k, s in raw} == results, 'raw register result mismatch')
    hashes = re.findall(r'^CHECKPOINT_REGISTER_INPUT\t([^\t\n]+)\t([a-f0-9]{64})$', log, re.M)
    require(len(hashes) == len(artifacts) and dict(hashes) == inputs, 'raw register identity mismatch')
    # Read native engine completions in one pass. Searching the whole CAD log
    # separately for every captured bit would repeatedly scan gigabytes.
    engine = {}
    for name, status in re.findall(r'The (?:cover )?property "([^"]+)" was (proven|covered) (?:in|at) ', log):
        engine.setdefault(name, set()).add(status)
    for name in re.findall(r'A counterexample \(cex\).*property "([^"]+)"', log):
        engine.setdefault(name, set()).add('cex')
    for name in re.findall(r'The cover property "([^"]+)" was proven unreachable in ', log):
        engine.setdefault(name, set()).add('unreachable')
    for prop, (_, status) in results.items():
        require(engine.get(prop.split('::', 1)[1]) == {status}, 'missing/conflicting register engine result: ' + prop)
    failures = {p: s for p, (k, s) in results.items() if k == 'assert' and s == 'cex'}
    proven_bits = sum(len(group['bits']) for i, group in enumerate(binding['groups']) if
                      results[f'<embedded>::production_register_miter.state_{i}_step'][1] == 'proven')
    report = dict(audit='passed', proof_scope='complete physical register candidate induction and universal memory-port congruence',
                assertions_proven=sum(k == 'assert' and s == 'proven' for k, s in results.values()),
                covers=sum(k == 'cover' and s == 'covered' for k, s in results.values()), counterexamples=failures,
                pending_independence_covers_unreachable={p: s for p, (k, s) in results.items() if k == 'cover' and s == 'unreachable'},
                transition_bits_proven=proven_bits, physical_register_bits=binding['physical_register_bits'],
                semantic_register_bits=binding['semantic_register_bits'],
                optimized_register_bits_pending=sum(len(e['bits']) for e in binding['pending_registers']),
                complete_memory_instances=len(binding['memories']),
                complete_memory_bits=sum(e['entry']['width'] * e['entry']['depth'] for e in binding['memories']),
                original_to_architecture_composition='unproven', memory_contents_composition='unproven',
                formal_state_map_complete=False, gate_restore_authorized=False)
    if binding.get('optimized_predicates'):
        report['optimized_predicates_proven'] = sum(
            results[f'<embedded>::production_register_miter.predicate_{i}_step'][1] == 'proven'
            for i in range(len(binding['optimized_predicates'])))
    if negative:
        report['failed_nonvacuity_covers'] = {p: s for p, (k, s) in results.items()
                                             if k == 'cover' and s == 'unreachable' and '.pending_' not in p}
        report['proof_acceptance'] = 'rejected: deliberate false mapping/transition candidate'
    return report


def audit(architecture, synthesis_evidence, proof, opcode_predicate=False):
    return validate(reconstruct(architecture, synthesis_evidence, opcode_predicate), proof)


def relation_catalog(binding, proof):
    """Export conditional lemmas and ALL remaining obligations, never a gate map."""
    report = validate(binding, proof)
    prefix = '<embedded>::production_register_miter.'
    registers = []
    for index, group in enumerate(binding['groups']):
        prop = prefix + f'state_{index}_step'
        registers.append(dict(group, proof_property=prop, native_transition_status='cex' if prop in report['counterexamples'] else 'proven',
                              global_state_map_status='unproven: full original/memory/optimized-state composition required'))
    return dict(catalog_version=1, artifact_type='conditional_production_register_relations',
                binding_sha256=sha(canonical(binding)),
                proof_artifacts={n: sha((Path(proof) / n).read_bytes()) for n in
                    ('binding.json', 'miter.sv', 'prove.tcl', 'register-results.tsv', 'jasper.log')},
                registers=registers, pending_registers=binding['pending_registers'],
                optimized_predicates=binding.get('optimized_predicates', []), memories=binding['memories'],
                unresolved_native_obligations=report['counterexamples'],
                pending_independence_covers_unreachable=report['pending_independence_covers_unreachable'],
                semantic_register_bits=binding['semantic_register_bits'], physical_register_bits=binding['physical_register_bits'],
                semantic_state_entries=binding['semantic_state_entries'],
                formal_state_map_complete=False, gate_restore_authorized=False)


def predicate_checkpoint(binding, manifest, boundary, configuration, data):
    """Check every semantic word before examining proposed optimization predicates.

    Predicate compatibility alone cannot authorize a map or gate loading.
    """
    from .replay import builds
    from .semantic import decode_semantic, manifest_hash
    require(manifest_hash(manifest) == binding['semantic_manifest_hash'] and
            sha(canonical(boundary)) == binding['boundary_manifest_sha256'], 'unbound predicate checkpoint manifests')
    checkpoint = decode_semantic(data, builds(manifest, boundary, configuration)[0], manifest)
    records = {r['state_id']: r for r in checkpoint['records']}
    observed = []
    for predicate in binding.get('optimized_predicates', []):
        entry, bit, expected = predicate['entry'], predicate['bit'], predicate['value']
        record = records[entry['state_id']]
        require(record['width'] == entry['width'] and record['depth'] == 1, 'reshaped optimization predicate state')
        value = (int(record['values'][0], 16) >> bit) & 1
        require(value == expected, 'semantic checkpoint violates unproven optimization predicate: ' + entry['original_path'])
        observed.append(dict(state_id=entry['state_id'], bit=bit, value=value))
    return dict(checkpoint_sha256=sha(data), target_cycle=checkpoint['target_cycle'], complete_semantic_records=len(records),
                complete_words=sum(r['depth'] for r in records.values()), predicates=observed,
                formal_state_map_complete=False, gate_restore_authorized=False)
