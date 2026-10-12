"""Independent production context reconstruction and actual evidence mutations."""

import argparse
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.formal_state_map import gate_deposits, sha
from tools.checkpoint_formats.production_context import audit, proof_inputs, read_results, reconstruct, validate
from .verify_production_context import negative_binding


FILES = ('binding.json', 'miter.sv', 'prove.tcl', 'context-results.tsv', 'jasper.log')


def verify(architecture, synthesis_evidence, queue_proof, proof_run, out):
    architecture, synthesis_evidence, queue_proof, proof_run, out = (Path(p).resolve() for p in
        (architecture, synthesis_evidence, queue_proof, proof_run, out))
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    binding = reconstruct(architecture, synthesis_evidence, queue_proof)
    saved = json.loads((proof_run / 'summary.json').read_text())
    positive, rejections = {}, {}
    before = {str(p): sha(p.read_bytes()) for p in proof_run.rglob('*') if p.is_file() and not p.is_symlink()}

    def rejected(name, function, artifacts):
        try:
            function()
        except FormatError as error:
            rejections[name] = dict(rejected=str(error), artifacts=str(artifacts))
        else:
            raise AssertionError('Altered production context evidence accepted: ' + name)

    for kind in ('parent', 'live', 'whole'):
        proof = proof_run / kind
        positive[kind] = audit(architecture, synthesis_evidence, queue_proof, kind, proof)
        require(saved['positive'][kind] == positive[kind], 'changed context summary')
        original = {n: (proof / n).read_bytes() for n in FILES}
        for mutation in ('missing_assertion', 'missing_cover', 'undetermined', 'vacuous', 'wrong_kind',
                         'forged_cex', 'raw_engine', 'raw_hash', 'blackbox', 'assumption', 'miter', 'script',
                         'binding_mask', 'binding_state', 'binding_authority'):
            path = run / 'mutations' / kind / mutation
            path.mkdir(parents=True)
            for file, data in original.items():
                (path / file).write_bytes(data)
            rows = [l.split('\t') for l in (path / 'context-results.tsv').read_text().splitlines()]
            prop = next(r for r in rows if len(r) == 4 and r[2:] == ['assert', 'proven'])
            if mutation in ('missing_assertion', 'missing_cover'):
                if mutation == 'missing_cover':
                    prop = next(r for r in rows if len(r) == 4 and r[2] == 'cover')
                rows.remove(prop)
            elif mutation in ('undetermined', 'vacuous', 'wrong_kind', 'forged_cex'):
                if mutation == 'vacuous':
                    prop = next(r for r in rows if len(r) == 4 and r[2] == 'cover')
                if mutation == 'wrong_kind':
                    prop[2] = 'cover'
                else:
                    prop[3] = {'undetermined': 'undetermined', 'vacuous': 'unreachable', 'forged_cex': 'cex'}[mutation]
            elif mutation in ('raw_engine', 'raw_hash', 'blackbox', 'assumption'):
                text = (path / 'jasper.log').read_text()
                if mutation == 'raw_engine':
                    engine_name = prop[1].split('::', 1)[1]
                    text = '\n'.join(l for l in text.splitlines() if not (
                        'The property "' + engine_name + '" was proven' in l)) + '\n'
                elif mutation == 'raw_hash':
                    text = text.replace('CHECKPOINT_CONTEXT_INPUT\tbinding\t', 'CHANGED_CONTEXT_INPUT\tbinding\t')
                elif mutation == 'blackbox':
                    text += '\nAutomatically BLACK-BOXED storage\n'
                else:
                    text = re.sub(r'(assumptions\s*:\s*)0\b', r'\g<1>1', text)
                require(text.encode() != original['jasper.log'], 'raw mutation did not change evidence')
                (path / 'jasper.log').write_text(text)
            else:
                role, file = ('miter', 'miter.sv') if mutation == 'miter' else ('script', 'prove.tcl') if mutation == 'script' else ('binding', 'binding.json')
                if mutation.startswith('binding_'):
                    changed = json.loads(original[file])
                    value = changed['binding']
                    if mutation == 'binding_mask':
                        value['cuts']['Queue_39']['io_deq_bits_echo_tl_state_size']['independent_mask'] ^= 1
                    elif mutation == 'binding_state':
                        value['semantic_entries'].pop(0)
                    else:
                        value['gate_restore_authorized'] = True
                    (path / file).write_bytes(canonical(changed))
                else:
                    text = original[file].decode()
                    text = text.replace('assert property', 'cover property', 1) if mutation == 'miter' else text.replace('reset -none', 'reset -expression {reset}')
                    (path / file).write_text(text)
                next(r for r in rows if r[:2] == ['INPUT', role])[2] = sha((path / file).read_bytes())
            (path / 'context-results.tsv').write_text('\n'.join('\t'.join(r) for r in rows) + '\n')
            rejected(kind + '/' + mutation, lambda: validate(binding, kind, path), path)
    negatives = {}
    trials = [(n, m) for n in sorted(binding['parents']) for m in ('boundary', 'child_input')]
    trials.append(('Queue_39', 'live_high_bit'))
    trials.append((binding['top'], 'whole_boundary'))
    for name, mutation in trials:
        value, kind, prop = negative_binding(binding, name, mutation)
        path = proof_run / 'negative' / name / mutation
        results = read_results(value, kind, path)
        qualified = '<embedded>::' + ('production_queue_miter' if kind == 'live' else 'production_context_miter') + '.' + prop
        require(results[qualified] == ('assert', 'cex'), 'negative context proof missing counterexample')
        record = dict(kind=kind, property=qualified, directory=str(path), status='cex')
        require(saved['fresh_negative_proofs'][name + '/' + mutation] == record, 'changed context negative summary')
        negatives[name + '/' + mutation] = record
    manifest = json.loads((architecture / 'manifest.json').read_text())
    for label, value in (('binding', binding), ('whole_lemma', dict(positive['whole'], top=binding['top']))):
        rejected('loader/' + label, lambda: gate_deposits(value, manifest, {}, {}, b'', {}, 'tb.dut'), proof_run)
    loader_rejections = {k: rejections.pop(k) for k in list(rejections) if k.startswith('loader/')}
    for kind, result in positive.items():
        require(audit(architecture, synthesis_evidence, queue_proof, kind, proof_run / kind) == result,
                'positive context evidence changed')
    require(before == {str(p): sha(p.read_bytes()) for p in proof_run.rglob('*') if p.is_file() and not p.is_symlink()},
            'original context proofs changed')
    summary = dict(status='passed', run=str(run), proof_run=str(proof_run), queue_proof=str(queue_proof),
                   positive=positive, fresh_negative_proofs_reaudited=negatives,
                   unchanged_controls=6, actual_artifact_mutations_rejected=len(rejections), rejections=rejections,
                   incomplete_map_loader_rejections=loader_rejections, original_proof_hashes=before,
                   formal_state_map_complete=False, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'queue-proof', 'proof-run', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.architecture, args.synthesis_evidence, args.queue_proof, args.proof_run, args.out)
    print(json.dumps({k: v for k, v in result.items() if k not in ('rejections', 'original_proof_hashes')}, indent=2))


if __name__ == '__main__':
    main()
