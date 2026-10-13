"""Independently audit complete production semantic-to-gate map composition.

Do not import the map exporter or its partition/assembly code. Reconstruct the
native component proofs with their existing independent auditors, walk the
semantic manifest and actual physical inventory, and consume each storage
object exactly once. Rehashed map changes cannot bypass those obligations.
"""

import argparse
import copy
import json
from pathlib import Path
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.formal_state_map import gate_deposits, sha
from tools.checkpoint_formats.production_original import reconstruct as original_binding
from tools.checkpoint_formats.production_memory_composition import reconstruct as memory_binding
from tools.checkpoint_formats.semantic import manifest_hash
from .audit_production_original import audit as audit_original
from .audit_production_memory_composition import audit as audit_memory
from .audit_production_optimized import audit as audit_optimized


def audit_components(original_run, memory_run):
    original_run, memory_run = Path(original_run).resolve(), Path(memory_run).resolve()
    osaved = json.loads((original_run / 'binding.json').read_text())
    original = original_binding(osaved['architecture'], osaved['memory_proof'])
    require(osaved == original, 'stale independent original map binding')
    oreport = audit_original(original, original_run / 'original-composition.json')
    msaved = json.loads((memory_run / 'binding.json').read_text())
    memory = memory_binding(*(msaved[k] for k in ('architecture', 'synthesis_evidence', 'register_proof', 'memory_proof', 'optimized')))
    require(memory == msaved, 'stale independent memory map binding')
    mreport = audit_memory(memory, memory_run / 'memory-composition.json')
    preport = audit_optimized(memory['architecture'], memory['synthesis_evidence'], memory['optimized'])
    registers = memory['registers']
    require(original['architecture'] == memory['architecture'] and original['memory_proof'] == memory['memory_proof'] and
            original['arrays'] == memory['arrays'] and original['implementation_source'] == registers['reference_source'] and
            original['memory_source'] == registers['memory_source'] and original['top'] == registers['top'] and
            original['semantic_manifest_hash'] == registers['semantic_manifest_hash'] and
            original['retiming'] is False and registers['retiming'] is False, 'independent composition build mismatch')
    architecture, evidence = Path(original['architecture']), Path(memory['synthesis_evidence'])
    manifest = json.loads((architecture / 'manifest.json').read_text())
    inventory = json.loads((evidence / 'gate-storage-inventory.json').read_text())
    optimized = json.loads(Path(memory['optimized']).read_text())
    dependencies = dict(original['prerequisites'])
    dependencies.update(memory['prerequisite_artifacts'])
    paths = [original_run / 'binding.json', original_run / 'original-composition.json',
             memory_run / 'binding.json', memory_run / 'memory-composition.json', Path(memory['optimized'])]
    for run, cert_name, results_name in ((original_run, 'original-composition.json', 'original-results.tsv'),
                                       (memory_run, 'memory-composition.json', 'composition-results.tsv')):
        certificate = json.loads((run / cert_name).read_text())
        for scope in ('address', 'word'):
            directory = Path(certificate['proofs'][scope]['path'])
            paths.extend(directory / n for n in ('binding.json', 'miter.sv', 'prove.tcl', results_name, 'jasper.log'))
    paths.extend(evidence / n for n in ('audit.json', 'models.v', 'cell-adapter.json', 'gate-storage-inventory.json',
                                      'netlist-design.v', 'model-binding.json'))
    synthesis = Path(json.loads((evidence / 'audit.json').read_text())['run'])
    paths.extend(synthesis / n for n in ('commands.json', 'synthesis/netlist.v', 'synthesis/synth.log'))
    root = Path(__file__).resolve().parents[3]
    paths.append(root / 'tools/checkpoint_formats/production_synth.tcl')
    paths.extend(root / 'tools/checkpoint_formats/tests/fixtures/formal' / n for n in ('cells.lib', 'cells.v', 'cell-adapter.json'))
    for path in paths:
        dependencies[str(path.resolve())] = sha(path.read_bytes())
    require(all(sha(Path(p).read_bytes()) == digest for p, digest in dependencies.items()), 'changed independent map dependency')
    return dict(original=original, memory=memory, manifest=manifest, inventory=inventory, optimized=optimized,
                dependencies=dependencies, original_run=str(original_run), memory_run=str(memory_run),
                reports=dict(original=oreport, memory=mreport, optimized=preport))


def audit_map(context, path):
    """Reconstruct map membership independently after immutable CAD auditing."""
    path = Path(path)
    saved = json.loads(path.read_text())
    require(all(Path(p).is_file() and sha(Path(p).read_bytes()) == h for p, h in context['dependencies'].items()),
            'CAD changed after independent component audit')
    original, memory, manifest = context['original'], context['memory'], context['manifest']
    inventory, optimized = context['inventory'], context['optimized']
    candidate = {e['state_id']: e for e in original['registers']}
    candidate.update({m['entry']['state_id']: m['entry'] for m in original['memories']})
    actual = saved.get('entries', [])
    require(len(actual) == len(manifest['state']) and [e['state_id'] for e in actual] == [e['state_id'] for e in manifest['state']],
            'missing/duplicate/reordered semantic map entry')
    retained, classified = {}, {}
    for gi, group in enumerate(memory['registers']['groups']):
        for bit in group['bits']:
            key = group['entry']['state_id'], bit['original_bit']
            require(key not in retained and candidate.get(key[0]) == group['entry'], 'duplicate/unbound independent register')
            retained[key] = gi, bit
    for item in optimized['classifications']:
        key = item['state_id'], item['bit']
        require(key not in classified and key not in retained and item['original_path'] == candidate[key[0]]['original_path'],
                'duplicate/unbound independent optimized bit')
        classified[key] = item
    physical = {tuple(s['instance_components']) + (s['name'],): s for s in inventory['storage']}
    require(len(physical) == len(inventory['storage']), 'duplicate independent physical inventory')
    used, consumed_bits = set(), set()
    memory_by_id = {i['state_id']: i for i in memory['instances']}
    require(len(memory_by_id) == len(memory['instances']), 'duplicate independent memory candidate')
    expected_entries = []
    for semantic in manifest['state']:
        state_id, width, depth, kind = (semantic[k] for k in ('state_id', 'width', 'depth', 'kind'))
        entry = candidate[state_id]
        relative = semantic['hierarchy'][len(manifest['dut_root'])+1:]
        require(relative == entry['original_path'] and all(entry[k] == semantic[k] for k in ('kind', 'width', 'depth')),
                'independent map/manifest shape mismatch')
        mapped = dict(state_id=state_id, original_path=relative, architecture_path=entry['architecture_path'],
                      kind=kind, width=width, depth=depth)
        if kind == 'register':
            oi = next(i for i, e in enumerate(original['registers']) if e['state_id'] == state_id)
            bits = []
            for bit in range(width):
                key = state_id, bit
                consumed_bits.add(key)
                if key in retained:
                    gi, proposed = retained[key]
                    location = tuple(proposed['gate_components']) + ('state',)
                    require(location in physical and location not in used and proposed['xor'] == 0,
                            'missing/duplicate/unsupported independent gate register')
                    storage = physical[location]
                    require(storage['cell'] == 'CKDFF' and storage['kind'] == 'register' and storage['width'] == storage['depth'] == 1,
                            'unproven independent gate register model')
                    used.add(location)
                    value = dict(bit=bit, classification='mapped',
                                 gate=dict(instance_components=proposed['gate_components'], storage='state', bit=0, xor=0),
                                 gate_induction=f'<embedded>::production_register_miter.state_{gi}_step')
                else:
                    require(key in classified, 'unproven independent semantic register bit')
                    item = classified[key]
                    value = dict(bit=bit, value_covers=item['value_covers'])
                    if item['classification'] == 'conditional_constant':
                        value.update(classification='preserved_predicate', value=item['value'], gate_induction=item['preservation_property'])
                    else:
                        require(item['classification'] == 'conditional_irrelevant', 'unsupported independent optimized state')
                        value.update(classification='irrelevant', gate_induction='all bound gate register/port/output assertions')
                bits.append(value)
            mapped.update(original_induction=f'<embedded>::production_original_miter.register_{oi}_step', bits=bits)
        else:
            require(kind == 'memory' and state_id in memory_by_id, 'unproven independent memory StateID')
            item = memory_by_id[state_id]
            oi = next(i for i, m in enumerate(original['memories']) if m['entry']['state_id'] == state_id)
            location = tuple(item['gate_components']) + ('contents',)
            require(location in physical and location not in used, 'missing/duplicate independent memory storage')
            storage = physical[location]
            require(storage['kind'] == 'memory' and storage['cell'] == entry['memory']['cell'] == item['cell'] and
                    storage['width'] == item['width'] == width and storage['depth'] == item['depth'] == depth and
                    item['architecture_path'] == entry['architecture_path'] and item['original_path'] == relative,
                    'reshaped/misbound independent full memory')
            used.add(location)
            mapped.update(mapping=dict(classification='mapped_full_array', instance_components=list(location[:-1]),
                                       storage=location[-1], address_transform='identity', bit_transform='identity',
                                       address_first=0, address_count=depth, bit_first=0, bit_count=width),
                          original_induction=f'<embedded>::production_original_miter.word_{oi}_step',
                          gate_induction=f'<embedded>::production_composition_miter.word_{item["index"]}_step',
                          read_closure=dict(original_scope='address', gate_scope='address', ports=item['read_ports']),
                          universal_adapter=dict(path=item['universal_original_adapter'], properties=item['original_adapter_properties']))
        expected_entries.append(mapped)
    require(canonical(actual) == canonical(expected_entries),
            'changed/incomplete independently reconstructed StateID relationships')
    require(used == set(physical) and consumed_bits == set(retained) | set(classified),
            'unmapped physical or extra semantic state')
    memory_bits = sum(e['width'] * e['depth'] for e in manifest['state'] if e['kind'] == 'memory')
    memory_words = sum(e['depth'] for e in manifest['state'] if e['kind'] == 'memory')
    register_bits = len(consumed_bits)
    expected = dict(production_state_map_version=1, artifact_type='complete_production_semantic_gate_state_map',
                    top=original['top'], semantic_manifest_hash=manifest_hash(manifest),
                    boundary_manifest_sha256=memory['registers']['boundary_manifest_sha256'], retiming=False,
                    proof_components=dict(original=context['original_run'], memory=context['memory_run'],
                                          registers=memory['register_proof'], optimized=memory['optimized']),
                    dependency_artifacts=context['dependencies'], model_binding=memory['registers']['model_binding'],
                    entries=expected_entries, semantic_state_entries=len(manifest['state']), semantic_state_bits=register_bits+memory_bits,
                    semantic_register_bits=register_bits, mapped_register_bits=len(retained),
                    predicate_bits=sum(c['classification'] == 'conditional_constant' for c in classified.values()),
                    irrelevant_register_bits=sum(c['classification'] == 'conditional_irrelevant' for c in classified.values()),
                    memory_instances=len(memory_by_id), memory_bits=memory_bits, memory_words=memory_words,
                    read_ports=sum(i['read_ports'] for i in memory_by_id.values()),
                    gate_storage_bits=sum(s['width'] * s['depth'] for s in physical.values()),
                    gate_storage_words=sum(s['depth'] for s in physical.values()),
                    proof_scope='inductive original/architecture equality composed with gate register/predicate, independent read closure and universal word theorems',
                    checkpoint_precondition='every preserved_predicate bit must equal its proven value; all other semantic values are unconstrained',
                    formal_state_map_complete=True, gate_restore_authorized=False,
                    gate_restore_requirement='current independent map audit and compatible checkpoint validation in the production loader; fresh gate replay pending')
    require(canonical(saved) == canonical(expected), 'changed/unbound production map header or build identity')
    return dict(status='passed', map=str(path.resolve()), map_sha256=sha(path.read_bytes()),
                semantic_state_entries=len(expected_entries), semantic_register_bits=register_bits,
                mapped_register_bits=len(retained), predicate_bits=expected['predicate_bits'],
                irrelevant_register_bits=expected['irrelevant_register_bits'], memory_instances=len(memory_by_id),
                memory_bits=memory_bits, memory_words=memory_words, gate_storage_bits=expected['gate_storage_bits'],
                gate_storage_words=expected['gate_storage_words'], formal_state_map_complete=True, gate_restore_authorized=False)


def verify(path, out):
    path, out = Path(path).resolve(), Path(out).resolve()
    saved = json.loads(path.read_text())
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    context = audit_components(saved['proof_components']['original'], saved['proof_components']['memory'])
    positive = audit_map(context, path)
    before = dict(context['dependencies'])
    rejected = {}
    faults = ('missing_entry', 'duplicate_entry', 'state_id', 'original_path', 'width', 'depth', 'missing_bit',
              'duplicate_bit', 'gate_path', 'gate_storage', 'gate_polarity', 'gate_bit', 'wrong_register_theorem',
              'predicate_value', 'predicate_as_irrelevant', 'free_as_predicate', 'missing_cover',
              'memory_path', 'memory_storage', 'memory_address_first', 'memory_address_count', 'memory_bit_count',
              'memory_transform', 'wrong_word_theorem', 'missing_read_closure', 'missing_adapter',
              'missing_dependency', 'changed_dependency', 'missing_component', 'model_binding', 'manifest_identity',
              'boundary_identity', 'physical_bits', 'physical_words', 'retiming', 'unconditional_state', 'gate_authority',
              'boolean_gate_bit', 'float_storage_count')
    for fault in faults:
        value = copy.deepcopy(saved)
        reg = next(e for e in value['entries'] if e['kind'] == 'register' and any(b['classification'] == 'mapped' for b in e['bits']))
        bit = next(b for b in reg['bits'] if b['classification'] == 'mapped')
        mem = next(e for e in value['entries'] if e['kind'] == 'memory')
        predicate = next(b for e in value['entries'] if e['kind'] == 'register' for b in e['bits'] if b['classification'] == 'preserved_predicate')
        free = next(b for e in value['entries'] if e['kind'] == 'register' for b in e['bits'] if b['classification'] == 'irrelevant')
        if fault == 'missing_entry': value['entries'].pop()
        elif fault == 'duplicate_entry': value['entries'].append(copy.deepcopy(reg))
        elif fault == 'state_id': reg['state_id'] = '0' * 64
        elif fault == 'original_path': reg['original_path'] += '_wrong'
        elif fault == 'width': reg['width'] += 1
        elif fault == 'depth': mem['depth'] -= 1
        elif fault == 'missing_bit': reg['bits'].remove(bit)
        elif fault == 'duplicate_bit': reg['bits'].append(copy.deepcopy(bit))
        elif fault == 'gate_path': bit['gate']['instance_components'][-1] += '_wrong'
        elif fault == 'gate_storage': bit['gate']['storage'] = 'Q'
        elif fault == 'gate_polarity': bit['gate']['xor'] = 1
        elif fault == 'gate_bit': bit['gate']['bit'] = 1
        elif fault == 'wrong_register_theorem': bit['gate_induction'] = reg['original_induction']
        elif fault == 'predicate_value': predicate['value'] ^= 1
        elif fault == 'predicate_as_irrelevant': predicate['classification'] = 'irrelevant'
        elif fault == 'free_as_predicate': free.update(classification='preserved_predicate', value=0)
        elif fault == 'missing_cover': free['value_covers'].pop()
        elif fault == 'memory_path': mem['mapping']['instance_components'] = ['missing']
        elif fault == 'memory_storage': mem['mapping']['storage'] = 'read_data'
        elif fault == 'memory_address_first': mem['mapping']['address_first'] = 1
        elif fault == 'memory_address_count': mem['mapping']['address_count'] -= 1
        elif fault == 'memory_bit_count': mem['mapping']['bit_count'] -= 1
        elif fault == 'memory_transform': mem['mapping']['address_transform'] = 'reverse'
        elif fault == 'wrong_word_theorem': mem['gate_induction'] = mem['original_induction']
        elif fault == 'missing_read_closure': del mem['read_closure']
        elif fault == 'missing_adapter': mem['universal_adapter']['properties'].clear()
        elif fault == 'missing_dependency': value['dependency_artifacts'].pop(next(iter(value['dependency_artifacts'])))
        elif fault == 'changed_dependency': value['dependency_artifacts'][next(iter(value['dependency_artifacts']))] = '0' * 64
        elif fault == 'missing_component': del value['proof_components']['original']
        elif fault == 'model_binding': value['model_binding'] = {}
        elif fault == 'manifest_identity': value['semantic_manifest_hash'] = '0' * 64
        elif fault == 'boundary_identity': value['boundary_manifest_sha256'] = '0' * 64
        elif fault == 'physical_bits': value['gate_storage_bits'] -= 1
        elif fault == 'physical_words': value['gate_storage_words'] -= 1
        elif fault == 'retiming': value['retiming'] = True
        elif fault == 'unconditional_state': value['checkpoint_precondition'] = 'none'
        elif fault == 'boolean_gate_bit': bit['gate']['bit'] = False
        elif fault == 'float_storage_count': value['gate_storage_bits'] = float(value['gate_storage_bits'])
        else: value['gate_restore_authorized'] = True
        artifact = run / (fault + '.json')
        artifact.write_bytes(canonical(value))
        try:
            audit_map(context, artifact)
        except FormatError as error:
            rejected[fault] = dict(reason=str(error), artifact=str(artifact), sha256=sha(artifact.read_bytes()))
        else:
            raise AssertionError('Corrupt production map accepted: ' + fault)
    # Generic flat/fixture loader must still reject this separate map format.
    try:
        gate_deposits(saved, {}, {}, {}, b'', {}, 'tb.dut')
    except FormatError as error:
        rejected['unsupported_loader'] = dict(reason=str(error), artifact=str(path))
    else:
        raise AssertionError('Production map accepted by unsupported loader')
    require(all(sha(Path(p).read_bytes()) == h for p, h in before.items()), 'positive production CAD bytes changed')
    result = dict(status='passed', run=str(run), positive=positive, component_audits=context['reports'],
                  rejection_checks=len(rejected), rejections=rejected, preserved_positive_artifacts=True,
                  formal_state_map_complete=True, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(result))
    (out / 'selection.json').write_bytes(canonical(dict(summary=str(run / 'summary.json'))))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.map, args.out), indent=2))


if __name__ == '__main__':
    main()
