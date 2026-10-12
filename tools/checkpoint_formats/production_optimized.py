"""Classify omitted production register bits using complete native induction.

The relation contains every physical register candidate and explicit preserved
predicates. All other reference register bits are universally quantified. If
every transition, predicate, concrete memory port and boundary output proves,
those free bits are irrelevant to this relation, conditional on common memory
read words. Covers establish nonvacuity, never independence by themselves.
Original/architecture/memory composition and gate loading remain separate.
"""

import argparse
import json
from pathlib import Path

from .codec import canonical, require
from .formal_state_map import sha
from .production_register import reconstruct, validate


FILES = ('binding.json', 'miter.sv', 'prove.tcl', 'register-results.tsv', 'jasper.log')
PREFIX = '<embedded>::production_register_miter.'


def partition(binding, results):
    """Partition ALL omitted bits; reject missing, duplicate or vacuous members."""
    pending, mapped, predicates = {}, set(), {}
    for group in binding['groups']:
        for bit in group['bits']:
            key = group['entry']['state_id'], bit['original_bit']
            require(key not in mapped, 'duplicate retained register bit')
            mapped.add(key)
    for index, item in enumerate(binding['pending_registers']):
        for bit in item['bits']:
            key = item['entry']['state_id'], bit
            require(key not in pending and key not in mapped and 0 <= bit < item['entry']['width'],
                    'duplicate/overlapping/out-of-range optimized register bit')
            pending[key] = index, item['entry']
    for index, predicate in enumerate(binding.get('optimized_predicates', [])):
        key = predicate['entry']['state_id'], predicate['bit']
        require(key in pending and key not in predicates and predicate['entry'] == pending[key][1] and
                type(predicate['value']) is int and predicate['value'] in (0, 1),
                'unbound/duplicate/unsupported optimized predicate')
        require(results.get(PREFIX + f'predicate_{index}_step') == ('assert', 'proven') and
                results.get(PREFIX + f'predicate_{index}_holds') == ('cover', 'covered'),
                'unproven/vacuous optimized predicate')
        predicates[key] = index, predicate
    require(len(mapped) == binding['physical_register_bits'] and
            len(mapped) + len(pending) == binding['semantic_register_bits'],
            'incomplete semantic/physical register partition')
    classified = []
    for (state_id, bit), (index, entry) in sorted(pending.items()):
        covers = [PREFIX + f'pending_{index}_bit_{bit}_{value}' for value in (0, 1)]
        item = dict(state_id=state_id, original_path=entry['original_path'], width=entry['width'], bit=bit,
                    value_covers=covers, global_state_map_status='unproven: original/memory composition required')
        if (state_id, bit) in predicates:
            pi, predicate = predicates[state_id, bit]
            value = predicate['value']
            require(results.get(covers[value]) == ('cover', 'covered') and
                    results.get(covers[1-value]) == ('cover', 'unreachable'),
                    'inconsistent conditional constant covers')
            item.update(classification='conditional_constant', value=value,
                        preservation_property=PREFIX + f'predicate_{pi}_step')
        else:
            require(all(results.get(c) == ('cover', 'covered') for c in covers),
                    'unproven independence nonvacuity: ' + entry['original_path'])
            item['classification'] = 'conditional_irrelevant'
        classified.append(item)
    return classified


def certificate(architecture, synthesis_evidence, proof):
    """Rebuild current inputs and require complete, nonvacuous native proofs."""
    proof = Path(proof).resolve()
    binding = reconstruct(architecture, synthesis_evidence, True, True)
    report = validate(binding, proof)
    require(not report['counterexamples'] and
            report['transition_bits_proven'] == binding['physical_register_bits'] and
            report['optimized_predicates_proven'] == len(binding['optimized_predicates']),
            'unproven complete production induction; optimized classification rejected')
    results = {}
    for line in (proof / 'register-results.tsv').read_text().splitlines():
        row = line.split('\t')
        if len(row) == 4 and row[0] == 'PROPERTY':
            results[row[1]] = tuple(row[2:])
    classifications = partition(binding, results)
    return dict(optimized_proof_version=1, artifact_type='conditional_production_optimized_relations',
                proof=str(proof), binding_sha256=sha(canonical(binding)),
                proof_artifacts={n: sha((proof / n).read_bytes()) for n in FILES},
                semantic_manifest_hash=binding['semantic_manifest_hash'],
                boundary_manifest_sha256=binding['boundary_manifest_sha256'],
                synthesis_inputs=binding['synthesis_inputs'], model_binding=binding['model_binding'],
                premise='complete retained-register equality, 130 preserved predicates, common universal memory read words',
                conclusion='all retained next-state, predicates, concrete memory inputs and top outputs agree for every free optimized bit valuation',
                semantic_register_bits=binding['semantic_register_bits'],
                physical_register_bits=binding['physical_register_bits'],
                optimized_register_bits=len(classifications),
                conditional_constant_bits=sum(c['classification'] == 'conditional_constant' for c in classifications),
                conditional_irrelevant_bits=sum(c['classification'] == 'conditional_irrelevant' for c in classifications),
                classifications=classifications,
                universal_assertions={p: s for p, (k, s) in results.items() if k == 'assert'},
                memory_instances=len(binding['memories']),
                memory_contents_bits=sum(m['entry']['width'] * m['entry']['depth'] for m in binding['memories']),
                original_to_architecture_composition='unproven', memory_contents_composition='unproven',
                formal_state_map_complete=False, gate_restore_authorized=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'proof', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = certificate(args.architecture, args.synthesis_evidence, args.proof)
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / 'optimized-relations.json'
    path.write_bytes(canonical(result))
    summary = dict(status='passed', certificate=str(path.resolve()),
                   optimized_register_bits=result['optimized_register_bits'],
                   conditional_constant_bits=result['conditional_constant_bits'],
                   conditional_irrelevant_bits=result['conditional_irrelevant_bits'],
                   formal_state_map_complete=False, gate_restore_authorized=False)
    (args.out / 'summary.json').write_bytes(canonical(summary))
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
