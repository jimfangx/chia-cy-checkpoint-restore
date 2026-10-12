"""Reconstruct actual flattened production proof inputs and challenge evidence."""

import argparse
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.formal_state_map import gate_deposits, sha
from tools.checkpoint_formats.production_register import audit, reconstruct, relation_catalog, validate
from .verify_production_register import negative_binding


FILES = ('binding.json', 'miter.sv', 'prove.tcl', 'register-results.tsv', 'jasper.log')


def verify(architecture, synthesis_evidence, proof_run, out):
    architecture, synthesis_evidence, proof_run, out = (Path(p).resolve() for p in
        (architecture, synthesis_evidence, proof_run, out))
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    saved = json.loads((proof_run / 'summary.json').read_text())
    profile = saved.get('opcode_predicate', False)
    flight = saved.get('flight_opcode_predicates', False)
    require(type(profile) is bool and type(flight) is bool, 'unsupported predicate selection')
    binding = reconstruct(architecture, synthesis_evidence, profile, flight)
    proof = Path(saved['proof'])
    before = {n: sha((proof / n).read_bytes()) for n in FILES}
    report = audit(architecture, synthesis_evidence, proof, profile, flight)
    require(report == saved['positive'], 'changed positive register summary')
    catalog = relation_catalog(binding, proof)
    require((proof_run / 'register-relations.json').read_bytes() == canonical(catalog),
            'changed/incomplete conditional register catalog')
    original = {n: (proof / n).read_bytes() for n in FILES}
    rejections = {}

    def rejected(name, function, artifacts):
        try:
            function()
        except FormatError as error:
            rejections[name] = dict(reason=str(error), artifacts=str(artifacts))
        else:
            raise AssertionError('Altered register evidence accepted: ' + name)

    for mutation in ('missing_assertion', 'missing_cover', 'undetermined', 'vacuous', 'wrong_kind', 'unreachable_nonvacuity',
                     'forged_cex', 'raw_engine', 'conflicting_engine', 'raw_hash', 'blackbox', 'assumption',
                     'miter', 'script', 'binding_bit', 'binding_missing_state', 'binding_memory', 'binding_authority',
                     *(('binding_missing_predicate', 'binding_predicate_value', 'binding_predicate_order') if flight else ())):
        path = run / 'mutations' / mutation
        path.mkdir(parents=True)
        for name, data in original.items():
            (path / name).write_bytes(data)
        rows = [l.split('\t') for l in (path / 'register-results.tsv').read_text().splitlines()]
        prop = next(r for r in rows if len(r) == 4 and r[2:] == ['assert', 'proven'])
        if mutation in ('missing_assertion', 'missing_cover'):
            if mutation == 'missing_cover':
                prop = next(r for r in rows if len(r) == 4 and r[2] == 'cover')
            rows.remove(prop)
        elif mutation in ('undetermined', 'vacuous', 'wrong_kind', 'forged_cex', 'unreachable_nonvacuity'):
            if mutation == 'unreachable_nonvacuity':
                prop = next(r for r in rows if len(r) == 4 and r[1].endswith('.relation_edge'))
                prop[3] = 'unreachable'
            elif mutation == 'wrong_kind':
                prop[2] = 'cover'
            else:
                prop[3] = {'undetermined': 'undetermined', 'vacuous': 'vacuous', 'forged_cex': 'cex'}[mutation]
        elif mutation in ('raw_engine', 'conflicting_engine', 'raw_hash', 'blackbox', 'assumption'):
            log = (path / 'jasper.log').read_text()
            if mutation == 'raw_engine':
                name = prop[1].split('::', 1)[1]
                log, count = re.subn(r'^.*The property "' + re.escape(name) + r'" was proven.*\n', '', log, flags=re.M)
                require(count > 0, 'native engine mutation missed actual result')
            elif mutation == 'conflicting_engine':
                log += 'A counterexample (cex) was found for property "' + prop[1].split('::', 1)[1] + '"\n'
            elif mutation == 'raw_hash':
                log = re.sub(r'(CHECKPOINT_REGISTER_INPUT\t\w+\t)[a-f0-9]{64}',
                             lambda m: m[1] + '0' * 64, log, count=1)
            elif mutation == 'blackbox':
                log += '\nBLACK-BOX cell introduced\n'
            else:
                log = re.sub(r'(assumptions\s*:\s*)0\b', lambda m: m[1] + '1', log)
            (path / 'jasper.log').write_text(log)
        elif mutation in ('miter', 'script'):
            filename = 'miter.sv' if mutation == 'miter' else 'prove.tcl'
            (path / filename).write_bytes(original[filename] + b'\n// Changed proof input\n')
        else:
            changed = json.loads((path / 'binding.json').read_text())
            if mutation == 'binding_bit':
                changed['groups'][0]['bits'][0]['xor'] ^= 1
            elif mutation == 'binding_missing_state':
                changed['pending_registers'].clear()
            elif mutation == 'binding_memory':
                changed['memories'].pop()
            elif mutation == 'binding_missing_predicate':
                changed['optimized_predicates'].pop()
            elif mutation == 'binding_predicate_value':
                changed['optimized_predicates'][1]['value'] ^= 1
            elif mutation == 'binding_predicate_order':
                changed['optimized_predicates'].reverse()
            else:
                changed['gate_restore_authorized'] = True
                changed['formal_state_map_complete'] = True
            (path / 'binding.json').write_bytes(canonical(changed))
        (path / 'register-results.tsv').write_text('\n'.join('\t'.join(r) for r in rows) + '\n')
        rejected(mutation, lambda: validate(binding, path), path)

    for mutation in ('catalog_missing_register', 'catalog_missing_optimized_state', 'catalog_missing_memory', 'catalog_authority',
                     *(('catalog_missing_predicate', 'catalog_predicate_authority') if flight else ())):
        changed = json.loads(canonical(catalog))
        if mutation == 'catalog_missing_register':
            changed['registers'].pop()
        elif mutation == 'catalog_missing_optimized_state':
            changed['pending_registers'].clear()
        elif mutation == 'catalog_missing_memory':
            changed['memories'].pop()
        elif mutation == 'catalog_missing_predicate':
            changed['optimized_predicates'].pop()
        elif mutation == 'catalog_predicate_authority':
            changed['optimized_predicates'][1]['proof_status'] = 'proven'
        else:
            changed['formal_state_map_complete'] = changed['gate_restore_authorized'] = True
        path = run / 'mutations' / mutation / 'register-relations.json'
        path.parent.mkdir(parents=True)
        path.write_bytes(canonical(changed))
        rejected(mutation, lambda: require(path.read_bytes() == canonical(catalog), 'incomplete/forged conditional catalog'), path)

    negatives = {}
    kinds = {'polarity', 'missing_register', 'changed_data', 'read_address'}
    if profile:
        kinds.add('opcode_predicate')
    if flight:
        kinds.update(('flight_predicate', 'missing_flight_predicate', 'missing_d_flight_predicate'))
    require(set(saved['negative']) == kinds,
            'missing actual negative register trials')
    for kind, trial in saved['negative'].items():
        value, prop = negative_binding(binding, kind)
        negative_report = validate(value, trial['proof'], negative=True)
        require(trial['property'] == prop and trial['audit'] == negative_report, 'changed negative register result')
        if trial['status'] == 'cex':
            require(prop in negative_report['counterexamples'], 'missing actual negative counterexample')
        else:
            require(kind == 'opcode_predicate' and trial['status'] == 'rejected_nonvacuity' and
                    prop + ':precondition1' in negative_report['failed_nonvacuity_covers'], 'unsupported negative result')
            rejected('negative_nonvacuity', lambda: validate(value, trial['proof']), Path(trial['proof']))
        negatives[kind] = dict(property=prop, proof=trial['proof'], status=trial['status'])

    manifest = json.loads((architecture / 'manifest.json').read_text())
    rejected('gate_loader', lambda: gate_deposits(binding, manifest, {}, {}, b'', {}, 'tb.dut'), proof)
    rejected('gate_loader_catalog', lambda: gate_deposits(catalog, manifest, {}, {}, b'', {}, 'tb.dut'), proof)
    require(before == {n: sha((proof / n).read_bytes()) for n in FILES}, 'audit mutated original CAD proof bytes')
    summary = dict(status='passed', run=str(run), proof_run=str(proof_run), proof=str(proof), positive=report,
                   actual_artifact_mutations_rejected=sum(k not in ('gate_loader', 'gate_loader_catalog', 'negative_nonvacuity') for k in rejections), rejections=rejections,
                   negative=negatives, original_proof_files=before,
                   formal_state_map_complete=False, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'proof-run', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.architecture, args.synthesis_evidence, args.proof_run, args.out), indent=2))


if __name__ == '__main__':
    main()
