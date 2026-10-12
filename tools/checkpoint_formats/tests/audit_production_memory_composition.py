"""Independent production memory-composition export and native evidence audit.

Reconstruct the certificate without importing its exporter. Inspect the actual
read-word independence and universal word premises as well as native results.
Challenge complete actual artifacts while preserving all positive CAD bytes.
"""

import argparse
import copy
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.formal_state_map import gate_deposits, sha
from tools.checkpoint_formats.production_memory_composition import FILES, reconstruct, validate
from tools.checkpoint_formats.production_queue import instances
from tools.checkpoint_formats.replay import modules
from .audit_production_optimized import audit as optimized_audit
from .verify_production_memory_composition import negative_binding


def audit(binding, path):
    path = Path(path)
    saved = json.loads(path.read_text())
    require(set(saved.get('proofs', {})) == {'address', 'word'}, 'missing memory composition proof scope')
    proofs = {kind: Path(saved['proofs'][kind]['path']).resolve() for kind in ('address', 'word')}
    results = {kind: validate(binding, kind, proof) for kind, proof in proofs.items()}
    address = (proofs['address'] / 'miter.sv').read_text()
    word = (proofs['word'] / 'miter.sv').read_text()
    # Every physical read port has distinct top inputs with exact widths. The
    # relation may mention only retained state and preserved predicates.
    relation = re.findall(r'^wire relation = (.*);$', address, re.M)
    require(len(relation) == 1 and 'ckregister_memory_' not in relation[0], 'read words constrained in closure premise')
    for item in binding['instances']:
        index, width, depth = item['index'], item['width'], item['depth']
        require(depth > 0 and depth & (depth - 1) == 0, 'unsupported audited memory address domain')
        if depth == 1:
            for side in ('reference', 'implementation'):
                design = modules(binding['registers'][side + '_source'])
                name = binding['registers']['top']
                components = item['architecture_path'].split('.')[:-1] if side == 'reference' else item['gate_components']
                for component in components:
                    _, body = design[name]
                    child = instances(body)[component]
                    name = child['cell']
                for port, expression in child['ports'].items():
                    if not port.startswith('RA'):
                        continue
                    seen = set()
                    while expression not in ("1'b0", "1'h0", "1'd0"):
                        require(re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', expression) and expression not in seen,
                                'unproven audited single-word read domain')
                        seen.add(expression)
                        assignments = re.findall(r'\bassign\s+' + re.escape(expression) + r'\s*=\s*([^;]+);', body)
                        require(len(assignments) == 1, 'unproven audited single-word read domain')
                        expression = assignments[0].strip()
        aw = max(1, (depth - 1).bit_length())
        for port in range(item['read_ports']):
            name = f'ckregister_memory_{index}_Q{port}'
            for side in ('reference', 'implementation'):
                require(address.count(f'input [{width-1}:0] {side}_{name}') == 1 and
                        address.count(f'.{name}({side}_{name})') == 1,
                        'shared/missing/reshaped production read-word input')
            require(f'{name}_independent: cover property' in address,
                    'missing read-word independence nonvacuity')
        require(word.count(f'input [{aw-1}:0] watched_{index},') == 1 and
                f'old_reference_{index} == old_implementation_{index};' in word and
                f'word_{index}_step: assert property' in word and
                f'implementation_ckregister_memory_{index}_WA == watched_{index}' in word,
                'missing/nonuniversal production memory word obligation')
    expected = dict(composition_version=1, artifact_type='conditional_production_memory_composition',
                    binding_sha256=sha(canonical(binding)),
                    proofs={kind: dict(path=str(proof), artifacts={n: sha((proof / n).read_bytes()) for n in FILES})
                            for kind, proof in proofs.items()}, results=results, instances=binding['instances'],
                    memory_instances=binding['memory_instances'], memory_bits=binding['memory_bits'],
                    memory_words=binding['memory_words'], read_ports=binding['read_ports'],
                    read_closure='proven with independent reference/implementation read words',
                    architecture_to_netlist_memory_induction='proven conditional on retained register/predicate relation and complete current array equality',
                    original_to_architecture_composition='unproven', formal_state_map_complete=False, gate_restore_authorized=False)
    require(saved == expected, 'changed/incomplete/unauthorized memory composition certificate')
    return dict(status='passed', memory_instances=len(expected['instances']), memory_bits=expected['memory_bits'],
                memory_words=expected['memory_words'], read_ports=expected['read_ports'], results=results,
                certificate_sha256=sha(path.read_bytes()), formal_state_map_complete=False, gate_restore_authorized=False)


def verify(proof_run, out):
    proof_run, out = Path(proof_run).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    saved_binding = json.loads((proof_run / 'binding.json').read_text())
    args = [saved_binding[k] for k in ('architecture', 'synthesis_evidence', 'register_proof', 'memory_proof', 'optimized')]
    binding = reconstruct(*args)
    require(saved_binding == binding, 'changed memory composition binding')
    optimized_audit(binding['architecture'], binding['synthesis_evidence'], binding['optimized'])
    path = proof_run / 'memory-composition.json'
    positive = audit(binding, path)
    certificate = json.loads(path.read_text())
    originals = {kind: {n: (Path(p['path']) / n).read_bytes() for n in FILES}
                 for kind, p in certificate['proofs'].items()}
    before = {kind: {n: sha(data) for n, data in files.items()} for kind, files in originals.items()}
    rejected = {}

    def reject(name, function, artifact):
        try:
            function()
        except FormatError as error:
            rejected[name] = dict(reason=str(error), artifact=str(artifact))
        else:
            raise AssertionError('Unsupported memory composition accepted: ' + name)

    for fault in ('missing_memory', 'duplicate_memory', 'state_id', 'gate_path', 'width', 'depth', 'read_ports',
                  'missing_adapter', 'missing_scope', 'missing_native_hash', 'binding', 'counts',
                  'read_authority', 'word_authority', 'original_authority', 'gate_authority'):
        value = copy.deepcopy(certificate)
        item = value['instances'][0]
        if fault == 'missing_memory': value['instances'].pop()
        elif fault == 'duplicate_memory': value['instances'].append(copy.deepcopy(item))
        elif fault == 'state_id': item['state_id'] = '0' * 16
        elif fault == 'gate_path': item['gate_components'] = ['missing']
        elif fault == 'width': item['width'] += 1
        elif fault == 'depth': item['depth'] -= 1
        elif fault == 'read_ports': item['read_ports'] += 1
        elif fault == 'missing_adapter': item['original_adapter_properties'].clear()
        elif fault == 'missing_scope': value['proofs'].pop('address')
        elif fault == 'missing_native_hash': value['proofs']['word']['artifacts'].pop('jasper.log')
        elif fault == 'binding': value['binding_sha256'] = '0' * 64
        elif fault == 'counts': value['memory_bits'] -= 1
        elif fault == 'read_authority': value['read_closure'] = 'common read words assumed'
        elif fault == 'word_authority': value['architecture_to_netlist_memory_induction'] = 'unconditional'
        elif fault == 'original_authority': value['original_to_architecture_composition'] = 'proven'
        else: value.update(formal_state_map_complete=True, gate_restore_authorized=True)
        artifact = run / (fault + '.json')
        artifact.write_bytes(canonical(value))
        reject(fault, lambda: audit(binding, artifact), artifact)

    for fault in ('missing_address_property', 'address_cex', 'missing_word_property', 'word_cex',
                  'vacuous_word', 'missing_engine', 'missing_input_identity', 'shared_read_word',
                  'restricted_watched_address', 'lost_existing_transition'):
        kind = 'address' if fault in ('missing_address_property', 'address_cex', 'shared_read_word') else 'word'
        directory = run / fault
        directory.mkdir()
        for n, data in originals[kind].items():
            (directory / n).write_bytes(data)
        rows = [r.split('\t') for r in (directory / 'composition-results.tsv').read_text().splitlines()]
        suffix = '.ckregister_memory_0_RA0_equal' if kind == 'address' else '.word_0_step'
        prop = next(r for r in rows if len(r) == 4 and r[1].endswith(suffix))
        if fault in ('missing_address_property', 'missing_word_property'):
            rows.remove(prop)
        elif fault in ('address_cex', 'word_cex'):
            prop[3] = 'cex'
        elif fault == 'vacuous_word':
            next(r for r in rows if len(r) == 4 and r[1] == prop[1] + ':precondition1')[3] = 'unreachable'
        elif fault == 'lost_existing_transition':
            rows.remove(next(r for r in rows if len(r) == 4 and r[1].endswith('.state_0_step')))
        elif fault == 'missing_input_identity':
            rows.remove(next(r for r in rows if r[:2] == ['INPUT', 'miter']))
        elif fault == 'missing_engine':
            name = prop[1].split('::', 1)[1]
            text, count = re.subn(r'^.*The property "' + re.escape(name) + r'" was proven.*\n', '',
                                  (directory / 'jasper.log').read_text(), flags=re.M)
            require(count > 0, 'native composition engine mutation missed result')
            (directory / 'jasper.log').write_text(text)
        else:
            text = (directory / 'miter.sv').read_text()
            if fault == 'shared_read_word':
                text = text.replace('.ckregister_memory_0_Q0(implementation_ckregister_memory_0_Q0)',
                                    '.ckregister_memory_0_Q0(reference_ckregister_memory_0_Q0)')
            else:
                text = text.replace('wire word_relation_0 = watched_0 < ', 'wire word_relation_0 = watched_0 == 0 && watched_0 < ')
            require(text.encode() != originals[kind]['miter.sv'], 'native composition source mutation missed target')
            (directory / 'miter.sv').write_text(text)
        (directory / 'composition-results.tsv').write_text('\n'.join('\t'.join(r) for r in rows) + '\n')
        value = copy.deepcopy(certificate)
        value['proofs'][kind] = dict(path=str(directory), artifacts={n: sha((directory / n).read_bytes()) for n in FILES})
        artifact = directory / 'memory-composition.json'
        artifact.write_bytes(canonical(value))
        reject(fault, lambda: audit(binding, artifact), artifact)

    summary = json.loads((proof_run / 'summary.json').read_text())
    require(set(summary['fresh_negative_proofs']) == {'address_port', 'address_feedback', 'word_data', 'word_enable'},
            'missing native negative memory composition scope')
    negatives = {}
    for fault, saved in summary['fresh_negative_proofs'].items():
        value, kind, prop = negative_binding(binding, fault)
        report = validate(value, kind, saved['directory'], negative=True)
        require(saved['kind'] == kind and saved['property'] == prop and prop in report['counterexamples'],
                'unproven native composition negative')
        negatives[fault] = report
        reject('negative_' + fault, lambda: validate(value, kind, saved['directory']), Path(saved['directory']))
    reject('incomplete_gate_load', lambda: gate_deposits(certificate, {}, {}, {}, b'', {}, 'tb.dut'), path)
    after = {kind: {n: sha((Path(certificate['proofs'][kind]['path']) / n).read_bytes()) for n in FILES} for kind in originals}
    require(before == after and reconstruct(*args) == binding and audit(binding, path) == positive,
            'mutation audits changed production positive/prerequisite evidence')
    result = dict(status='passed', run=str(run), positive=positive, rejected_mutations=rejected,
                  native_negatives=negatives, positive_artifacts_unchanged=True,
                  formal_state_map_complete=False, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(result))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof-run', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.proof_run, args.out)
    print(json.dumps(dict(status=result['status'], run=result['run'],
                          rejections=len(result['rejected_mutations']), native_negatives=len(result['native_negatives']),
                          formal_state_map_complete=False, gate_restore_authorized=False)))


if __name__ == '__main__':
    main()
