"""Compose complete production StateID relationships from native CAD proofs.

Keep RAMs as universally proven full-word spans, rather than allocating an
entry for each of 102 million bits. Every scalar bit, including synthesized
away pipeline/port state, has an explicit classification. Component certificates
remain immutable and retain their conditional scope. This composed certificate
does not authorize a loader until a current independent audit and checkpoint
predicate validation are implemented by the production replay path.
"""

import argparse
import json
from pathlib import Path

from .codec import canonical, require
from .formal_state_map import sha
from .production_memory_composition import FILES as MEMORY_FILES
from .production_memory_composition import certificate as memory_certificate, reconstruct as memory_binding
from .production_optimized import certificate as optimized_certificate
from .production_original import FILES as ORIGINAL_FILES
from .production_original import certificate as original_certificate, reconstruct as original_binding
from .semantic import manifest_hash


REGISTER_PREFIX = '<embedded>::production_register_miter.'
ORIGINAL_PREFIX = '<embedded>::production_original_miter.'
MEMORY_PREFIX = '<embedded>::production_composition_miter.'


def components(original_run, memory_run):
    """Rebuild and validate every proof; saved summaries never authorize maps."""
    original_run, memory_run = Path(original_run).resolve(), Path(memory_run).resolve()
    original = json.loads((original_run / 'binding.json').read_text())
    ob = original_binding(original['architecture'], original['memory_proof'])
    require(original == ob, 'stale original map component binding')
    oc = json.loads((original_run / 'original-composition.json').read_text())
    require(oc == original_certificate(ob, *(oc['proofs'][k]['path'] for k in ('address', 'word'))),
            'changed/unproven original map component')
    memory = json.loads((memory_run / 'binding.json').read_text())
    mb = memory_binding(*(memory[k] for k in
                          ('architecture', 'synthesis_evidence', 'register_proof', 'memory_proof', 'optimized')))
    require(memory == mb, 'stale gate memory map component binding')
    mc = json.loads((memory_run / 'memory-composition.json').read_text())
    require(mc == memory_certificate(mb, *(mc['proofs'][k]['path'] for k in ('address', 'word'))),
            'changed/unproven gate memory map component')
    optimized = optimized_certificate(mb['architecture'], mb['synthesis_evidence'], mb['register_proof'])
    require(json.loads(Path(mb['optimized']).read_text()) == optimized, 'stale optimized map component')
    require(ob['architecture'] == mb['architecture'] and ob['memory_proof'] == mb['memory_proof'] and
            ob['arrays'] == mb['arrays'] and ob['implementation_source'] == mb['registers']['reference_source'] and
            ob['memory_source'] == mb['registers']['memory_source'] and
            ob['semantic_manifest_hash'] == mb['registers']['semantic_manifest_hash'] and
            ob['top'] == mb['registers']['top'] and ob['retiming'] is False and mb['registers']['retiming'] is False,
            'incompatible original/architecture/netlist composition')
    architecture, evidence = Path(ob['architecture']), Path(mb['synthesis_evidence'])
    manifest = json.loads((architecture / 'manifest.json').read_text())
    inventory = json.loads((evidence / 'gate-storage-inventory.json').read_text())
    dependencies = dict(ob['prerequisites'], **mb['prerequisite_artifacts'])
    paths = [original_run / 'binding.json', original_run / 'original-composition.json',
             memory_run / 'binding.json', memory_run / 'memory-composition.json', Path(mb['optimized'])]
    for cert, names in ((oc, ORIGINAL_FILES), (mc, MEMORY_FILES)):
        paths += [Path(p['path']) / n for p in cert['proofs'].values() for n in names]
    paths += [evidence / n for n in ('audit.json', 'models.v', 'cell-adapter.json', 'gate-storage-inventory.json',
                                    'netlist-design.v', 'model-binding.json')]
    synthesis_run = Path(json.loads((evidence / 'audit.json').read_text())['run'])
    paths += [synthesis_run / 'commands.json', synthesis_run / 'synthesis/netlist.v', synthesis_run / 'synthesis/synth.log']
    root = Path(__file__).resolve().parents[2]
    paths += [root / 'tools/checkpoint_formats/production_synth.tcl']
    paths += [root / 'tools/checkpoint_formats/tests/fixtures/formal' / n for n in ('cells.lib', 'cells.v', 'cell-adapter.json')]
    dependencies.update({str(p.resolve()): sha(p.read_bytes()) for p in paths})
    require(all(sha(Path(p).read_bytes()) == h for p, h in dependencies.items()), 'changed map CAD dependency')
    return dict(original=ob, memory=mb, optimized=optimized, manifest=manifest, inventory=inventory,
                dependencies=dependencies, original_run=str(original_run), memory_run=str(memory_run))


def compose_entries(original, memory, optimized, inventory):
    """Exhaustively partition semantic bits and consume physical storage spans."""
    registers = {e['state_id']: (i, e) for i, e in enumerate(original['registers'])}
    arrays = {m['entry']['state_id']: m['entry'] for m in original['memories']}
    require(len(registers) == len(original['registers']) and len(arrays) == len(original['memories']) and
            not registers.keys() & arrays.keys(), 'duplicate semantic map membership')
    mapped, omitted, used = {}, {}, set()
    physical = {(*s['instance_components'], s['name']): s for s in inventory['storage']}
    require(len(physical) == len(inventory['storage']), 'duplicate physical storage span')
    for index, group in enumerate(memory['registers']['groups']):
        entry = group['entry']
        require(entry['state_id'] in registers and entry == registers[entry['state_id']][1],
                'unbound semantic register relationship')
        for bit in group['bits']:
            key = entry['state_id'], bit['original_bit']
            path = tuple(bit['gate_components']) + ('state',)
            require(key not in mapped and path not in used and path in physical and
                    0 <= bit['original_bit'] < entry['width'] and type(bit['xor']) is int and bit['xor'] == 0,
                    'duplicate/unsupported production register relation')
            storage = physical[path]
            require(storage['kind'] == 'register' and storage['cell'] == 'CKDFF' and
                    storage['width'] == storage['depth'] == 1, 'unsupported gate register storage')
            used.add(path)
            mapped[key] = dict(bit=bit['original_bit'], classification='mapped',
                               gate=dict(instance_components=bit['gate_components'], storage='state', bit=0, xor=0),
                               gate_induction=REGISTER_PREFIX + f'state_{index}_step')
    for item in optimized['classifications']:
        key = item['state_id'], item['bit']
        require(key not in mapped and key not in omitted and key[0] in registers,
                'duplicate/unknown optimized map bit')
        entry = registers[key[0]][1]
        require(item['original_path'] == entry['original_path'] and item['width'] == entry['width'] and
                type(key[1]) is int and 0 <= key[1] < entry['width'], 'unbound optimized semantic bit')
        value = dict(bit=key[1], value_covers=item['value_covers'])
        if item['classification'] == 'conditional_constant':
            require(type(item['value']) is int and item['value'] in (0, 1), 'unsupported checkpoint predicate')
            value.update(classification='preserved_predicate', value=item['value'],
                         gate_induction=item['preservation_property'])
        else:
            require(item['classification'] == 'conditional_irrelevant', 'unproven optimized map classification')
            value.update(classification='irrelevant', gate_induction='all bound gate register/port/output assertions')
        omitted[key] = value
    entries = []
    for state_id, (index, entry) in registers.items():
        bits = []
        for bit in range(entry['width']):
            key = state_id, bit
            require(key in mapped or key in omitted, 'missing semantic register bit')
            bits.append(mapped.get(key, omitted.get(key)))
        entries.append(dict(state_id=state_id, original_path=entry['original_path'],
                            architecture_path=entry['architecture_path'], kind='register', width=entry['width'], depth=1,
                            original_induction=ORIGINAL_PREFIX + f'register_{index}_step', bits=bits))
    require(len(mapped) + len(omitted) == original['register_bits'], 'extra/missing semantic register bits')
    require(len(memory['instances']) == len(arrays), 'incomplete memory map')
    seen = set()
    for item in memory['instances']:
        state_id = item['state_id']
        require(state_id in arrays and state_id not in seen, 'unknown/duplicate mapped memory')
        seen.add(state_id)
        entry = arrays[state_id]
        require(all(item[k] == entry[k] for k in ('original_path', 'architecture_path', 'width', 'depth')) and
                item['cell'] == entry['memory']['cell'], 'reshaped/misbound semantic memory')
        path = tuple(item['gate_components']) + ('contents',)
        require(path in physical and path not in used and physical[path]['kind'] == 'memory' and
                all(physical[path][k] == item[k] for k in ('cell', 'width', 'depth')), 'missing/reshaped gate memory')
        used.add(path)
        original_index = next(i for i, m in enumerate(original['memories']) if m['entry']['state_id'] == state_id)
        entries.append(dict(state_id=state_id, original_path=entry['original_path'],
                            architecture_path=entry['architecture_path'], kind='memory', width=entry['width'], depth=entry['depth'],
                            mapping=dict(classification='mapped_full_array', instance_components=item['gate_components'],
                                         storage='contents', address_transform='identity', bit_transform='identity',
                                         address_first=0, address_count=entry['depth'], bit_first=0, bit_count=entry['width']),
                            original_induction=ORIGINAL_PREFIX + f'word_{original_index}_step',
                            gate_induction=MEMORY_PREFIX + f'word_{item["index"]}_step',
                            read_closure=dict(original_scope='address', gate_scope='address', ports=item['read_ports']),
                            universal_adapter=dict(path=item['universal_original_adapter'], properties=item['original_adapter_properties'])))
    require(used == set(physical), 'unmapped physical storage; gate map rejected')
    require(sum(s['width'] * s['depth'] for s in physical.values()) == inventory['physical_bits'] and
            sum(s['depth'] for s in physical.values()) == inventory['physical_words'], 'wrong physical map counts')
    return sorted(entries, key=lambda e: e['state_id'])


def export_state_map(original_run, memory_run):
    context = components(original_run, memory_run)
    original, memory = context['original'], context['memory']
    entries = compose_entries(original, memory, context['optimized'], context['inventory'])
    manifest = context['manifest']
    expected = {e['state_id']: (e['hierarchy'][len(manifest['dut_root'])+1:], e['kind'], e['width'], e['depth'])
                for e in manifest['state']}
    require({e['state_id']: tuple(e[k] for k in ('original_path', 'kind', 'width', 'depth')) for e in entries} == expected and
            manifest_hash(manifest) == original['semantic_manifest_hash'], 'incomplete semantic manifest map')
    return dict(production_state_map_version=1, artifact_type='complete_production_semantic_gate_state_map',
                top=original['top'], semantic_manifest_hash=manifest_hash(manifest),
                boundary_manifest_sha256=memory['registers']['boundary_manifest_sha256'], retiming=False,
                proof_components=dict(original=context['original_run'], memory=context['memory_run'],
                                      registers=memory['register_proof'], optimized=memory['optimized']),
                dependency_artifacts=context['dependencies'], model_binding=memory['registers']['model_binding'],
                entries=entries, semantic_state_entries=original['state_entries'], semantic_state_bits=original['state_bits'],
                semantic_register_bits=original['register_bits'], mapped_register_bits=memory['registers']['physical_register_bits'],
                predicate_bits=context['optimized']['conditional_constant_bits'],
                irrelevant_register_bits=context['optimized']['conditional_irrelevant_bits'],
                memory_instances=original['memory_instances'], memory_bits=original['memory_bits'], memory_words=original['memory_words'],
                read_ports=original['read_ports'], gate_storage_bits=context['inventory']['physical_bits'],
                gate_storage_words=context['inventory']['physical_words'],
                proof_scope='inductive original/architecture equality composed with gate register/predicate, independent read closure and universal word theorems',
                checkpoint_precondition='every preserved_predicate bit must equal its proven value; all other semantic values are unconstrained',
                formal_state_map_complete=True, gate_restore_authorized=False,
                gate_restore_requirement='current independent map audit and compatible checkpoint validation in the production loader; fresh gate replay pending')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original-proof', 'memory-composition', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = export_state_map(args.original_proof, args.memory_composition)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        require(args.out.read_bytes() == canonical(result), 'existing production map disagrees with current proofs; refusing overwrite')
    else:
        args.out.write_bytes(canonical(result))
    print(json.dumps(dict(artifact=str(args.out.resolve()), formal_state_map_complete=True,
                         semantic_state_entries=result['semantic_state_entries'], gate_storage_bits=result['gate_storage_bits'],
                         gate_storage_words=result['gate_storage_words'], gate_restore_authorized=False)))


if __name__ == '__main__':
    main()
