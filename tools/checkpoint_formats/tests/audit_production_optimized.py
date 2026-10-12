"""Independently reconstruct optimized-bit classifications from native evidence.

This auditor does not import the optimized certificate exporter or its partition
code. It requires the whole production induction, then derives each free-bit or
preserved-predicate classification separately from the exact reconstructed miter.
"""

import argparse
import copy
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.formal_state_map import gate_deposits, sha
from tools.checkpoint_formats.production_register import reconstruct, validate


FILES = ('binding.json', 'miter.sv', 'prove.tcl', 'register-results.tsv', 'jasper.log')
PREFIX = '<embedded>::production_register_miter.'


def audit(architecture, synthesis_evidence, path):
    saved = json.loads(Path(path).read_text())
    binding = reconstruct(architecture, synthesis_evidence, True, True)
    proof = Path(saved['proof'])
    report = validate(binding, proof)
    require(not report['counterexamples'] and report['transition_bits_proven'] == binding['physical_register_bits'] and
            report['optimized_predicates_proven'] == 130, 'unproven optimized classification premises')
    results = {r[1]: tuple(r[2:]) for line in (proof / 'register-results.tsv').read_text().splitlines()
               if len(r := line.split('\t')) == 4 and r[0] == 'PROPERTY'}
    # Exact reconstruction above checks the entire miter. Additionally inspect
    # its actual relation: free pending bits may not be hidden in the antecedent.
    miter = (proof / 'miter.sv').read_text()
    relations = re.findall(r'^wire relation = (.*);$', miter, re.M)
    require(len(relations) == 1, 'ambiguous optimized induction relation')
    references = re.findall(r'reference\.([A-Za-z0-9_$.]+)(?:\[(\d+)\])?', relations[0])
    retained = {(g['entry']['original_path'], str(b['original_bit']) if g['entry']['width'] > 1 else '')
                for g in binding['groups'] for b in g['bits']}
    predicates = {(p['entry']['state_id'], p['bit']): (i, p) for i, p in enumerate(binding['optimized_predicates'])}
    constrained = {(p['entry']['original_path'], str(p['bit'])) for p in binding['optimized_predicates']}
    require(len(predicates) == 130 and len(references) == len(retained) + len(constrained) and
            set(references) == retained | constrained, 'free optimized bits constrained or retained/predicate premise omitted')
    expected, membership = [], set()
    for index, omitted in enumerate(binding['pending_registers']):
        entry = omitted['entry']
        for bit in omitted['bits']:
            key = entry['state_id'], bit
            require(key not in membership, 'duplicate optimized membership')
            membership.add(key)
            covers = [PREFIX + f'pending_{index}_bit_{bit}_{v}' for v in (0, 1)]
            item = dict(state_id=key[0], original_path=entry['original_path'], width=entry['width'], bit=bit,
                        value_covers=covers, global_state_map_status='unproven: original/memory composition required')
            if key in predicates:
                pi, predicate = predicates[key]
                value = predicate['value']
                require(results[covers[value]] == ('cover', 'covered') and
                        results[covers[1-value]] == ('cover', 'unreachable') and
                        results[PREFIX + f'predicate_{pi}_step'] == ('assert', 'proven') and
                        results[PREFIX + f'predicate_{pi}_holds'] == ('cover', 'covered'),
                        'unproven preserved optimized predicate')
                item.update(classification='conditional_constant', value=value,
                            preservation_property=PREFIX + f'predicate_{pi}_step')
            else:
                expression = entry['original_path'], str(bit) if entry['width'] > 1 else ''
                require(expression not in set(references) and all(results[c] == ('cover', 'covered') for c in covers),
                        'constrained/vacuous free optimized bit')
                item['classification'] = 'conditional_irrelevant'
            expected.append(item)
    expected.sort(key=lambda c: (c['state_id'], c['bit']))
    require(set(predicates) <= membership and len(membership) + len(retained) == binding['semantic_register_bits'],
            'incomplete optimized register partition')
    header = dict(optimized_proof_version=1, artifact_type='conditional_production_optimized_relations',
                  proof=str(proof.resolve()), binding_sha256=sha(canonical(binding)),
                  proof_artifacts={n: sha((proof / n).read_bytes()) for n in FILES},
                  semantic_manifest_hash=binding['semantic_manifest_hash'],
                  boundary_manifest_sha256=binding['boundary_manifest_sha256'],
                  synthesis_inputs=binding['synthesis_inputs'], model_binding=binding['model_binding'],
                  premise='complete retained-register equality, 130 preserved predicates, common universal memory read words',
                  conclusion='all retained next-state, predicates, concrete memory inputs and top outputs agree for every free optimized bit valuation',
                  semantic_register_bits=binding['semantic_register_bits'], physical_register_bits=len(retained),
                  optimized_register_bits=len(expected), conditional_constant_bits=len(predicates),
                  conditional_irrelevant_bits=len(expected)-len(predicates), classifications=expected,
                  universal_assertions={p: s for p, (k, s) in results.items() if k == 'assert'},
                  memory_instances=len(binding['memories']),
                  memory_contents_bits=sum(m['entry']['width'] * m['entry']['depth'] for m in binding['memories']),
                  original_to_architecture_composition='unproven', memory_contents_composition='unproven',
                  formal_state_map_complete=False, gate_restore_authorized=False)
    require(saved == header, 'changed/incomplete/unauthorized optimized certificate')
    return dict(status='passed', conditional_irrelevant_bits=len(expected)-len(predicates),
                conditional_constant_bits=len(predicates), universal_assertions=len(header['universal_assertions']),
                optimized_register_bits=len(expected), certificate_sha256=sha(Path(path).read_bytes()),
                formal_state_map_complete=False, gate_restore_authorized=False)


def verify(architecture, synthesis_evidence, certificate, out):
    certificate, out = Path(certificate).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    positive = audit(architecture, synthesis_evidence, certificate)
    saved = json.loads(certificate.read_text())
    proof = Path(saved['proof'])
    original = {n: (proof / n).read_bytes() for n in FILES}
    before = {n: sha(data) for n, data in original.items()}
    rejected = {}

    def reject(name, function, path):
        try:
            function()
        except FormatError as error:
            rejected[name] = dict(reason=str(error), artifact=str(path))
        else:
            raise AssertionError('Unsupported optimized state accepted: ' + name)

    for mutation in ('missing_bit', 'duplicate_bit', 'changed_state_id', 'changed_path', 'changed_bit', 'changed_width',
                     'predicate_as_irrelevant', 'irrelevant_as_constant', 'constant_value', 'missing_preservation',
                     'changed_cover', 'missing_assertion', 'forged_assertion', 'manifest', 'model', 'counts',
                     'composition_authority', 'gate_authority'):
        value = copy.deepcopy(saved)
        free = next(c for c in value['classifications'] if c['classification'] == 'conditional_irrelevant')
        constant = next(c for c in value['classifications'] if c['classification'] == 'conditional_constant')
        if mutation == 'missing_bit': value['classifications'].pop()
        elif mutation == 'duplicate_bit': value['classifications'].append(copy.deepcopy(free))
        elif mutation == 'changed_state_id': free['state_id'] = constant['state_id']
        elif mutation == 'changed_path': free['original_path'] += '_wrong'
        elif mutation == 'changed_bit': free['bit'] = free['width']
        elif mutation == 'changed_width': free['width'] += 1
        elif mutation == 'predicate_as_irrelevant': constant['classification'] = 'conditional_irrelevant'
        elif mutation == 'irrelevant_as_constant': free.update(classification='conditional_constant', value=0)
        elif mutation == 'constant_value': constant['value'] ^= 1
        elif mutation == 'missing_preservation': del constant['preservation_property']
        elif mutation == 'changed_cover': free['value_covers'][1] = free['value_covers'][0]
        elif mutation == 'missing_assertion': value['universal_assertions'].pop(next(iter(value['universal_assertions'])))
        elif mutation == 'forged_assertion': value['universal_assertions'][next(iter(value['universal_assertions']))] = 'cex'
        elif mutation == 'manifest': value['semantic_manifest_hash'] = '0' * 64
        elif mutation == 'model': value['model_binding'] = {}
        elif mutation == 'counts': value['conditional_irrelevant_bits'] -= 1
        elif mutation == 'composition_authority': value['memory_contents_composition'] = 'proven'
        else: value.update(formal_state_map_complete=True, gate_restore_authorized=True)
        path = run / (mutation + '.json')
        path.write_bytes(canonical(value))
        reject(mutation, lambda: audit(architecture, synthesis_evidence, path), path)

    # Actual CAD-file mutations are rehashed in the certificate, so its hashes
    # alone cannot reject a forged transition/cover/engine/predicate result.
    for mutation in ('native_missing_transition', 'native_free_cover_unreachable', 'native_predicate_cex',
                     'native_engine_missing', 'native_relation_constrained'):
        directory = run / mutation
        directory.mkdir()
        for name, data in original.items(): (directory / name).write_bytes(data)
        rows = [line.split('\t') for line in (directory / 'register-results.tsv').read_text().splitlines()]
        prop = next(r for r in rows if len(r) == 4 and r[1].endswith('.state_0_step'))
        if mutation == 'native_missing_transition': rows.remove(prop)
        elif mutation == 'native_free_cover_unreachable':
            free = next(c for c in saved['classifications'] if c['classification'] == 'conditional_irrelevant')
            next(r for r in rows if len(r) == 4 and r[1] == free['value_covers'][0])[3] = 'unreachable'
        elif mutation == 'native_predicate_cex':
            next(r for r in rows if len(r) == 4 and r[1].endswith('.predicate_0_step'))[3] = 'cex'
        elif mutation == 'native_engine_missing':
            name = prop[1].split('::', 1)[1]
            log, count = re.subn(r'^.*The property "' + re.escape(name) + r'" was proven.*\n', '',
                                 (directory / 'jasper.log').read_text(), flags=re.M)
            require(count > 0, 'native optimized engine mutation missed result')
            (directory / 'jasper.log').write_text(log)
        else:
            free = next(c for c in saved['classifications'] if c['classification'] == 'conditional_irrelevant')
            text = (directory / 'miter.sv').read_text()
            text, count = re.subn(r'^wire relation = ',
                                 f"wire relation = (reference.{free['original_path']}[{free['bit']}] == 1'b0) && ",
                                 text, flags=re.M)
            require(count == 1, 'native relation mutation missed antecedent')
            (directory / 'miter.sv').write_text(text)
        (directory / 'register-results.tsv').write_text('\n'.join('\t'.join(r) for r in rows) + '\n')
        value = copy.deepcopy(saved)
        value['proof'] = str(directory)
        value['proof_artifacts'] = {n: sha((directory / n).read_bytes()) for n in FILES}
        path = directory / 'optimized-relations.json'
        path.write_bytes(canonical(value))
        reject(mutation, lambda: audit(architecture, synthesis_evidence, path), path)

    reject('incomplete_gate_load', lambda: gate_deposits(saved, {}, {}, {}, b'', {}, 'tb.dut'), certificate)
    require(before == {n: sha((proof / n).read_bytes()) for n in FILES} and
            audit(architecture, synthesis_evidence, certificate) == positive, 'optimized audits altered original proof/certificate')
    summary = dict(status='passed', run=str(run), positive=positive, actual_mutations_rejected=len(rejected)-1,
                   rejections=rejected, original_proof_sha256=before, original_proof_unchanged=True,
                   incomplete_gate_load_rejected=True, formal_state_map_complete=False, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'certificate', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.architecture, args.synthesis_evidence, args.certificate, args.out)))


if __name__ == '__main__':
    main()
