"""Independently reconstruct production queue obligations and mutate real evidence."""

import argparse
import copy
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.formal_state_map import gate_deposits, sha
from tools.checkpoint_formats.production_queue import audit, reconstruct, validate_proof
from .verify_production_queue import negative_binding


FILES = ('binding.json', 'miter.sv', 'prove.tcl', 'queue-results.tsv', 'jasper.log')


def verify(architecture, synthesis_evidence, proof_run, out):
    architecture, synthesis_evidence, proof_run, out = (Path(p).resolve() for p in
                                                       (architecture, synthesis_evidence, proof_run, out))
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    proof = proof_run / 'positive'
    binding = reconstruct(architecture, synthesis_evidence)
    original = {name: (proof / name).read_bytes() for name in FILES}
    initial_hashes = {str(p): sha(p.read_bytes()) for p in proof_run.rglob('*') if p.is_file() and not p.is_symlink()}
    positive = audit(architecture, synthesis_evidence, proof)
    require(len(binding['queues']) == 165 and positive['register_bits'] == 1135 and
            not positive['unproven_obligations']['register'] and not positive['unproven_obligations']['memory_port'],
            'retained queue local register/port proof incomplete')
    (run / 'independent-audit.json').write_bytes(canonical(positive))
    # Keep the complete semantic/physical/boundary obligation inventory visible;
    # local module proofs do not change the global unproven classifications.
    from tools.checkpoint_formats.production_dut import audit_architecture
    candidate = audit_architecture(architecture)
    obligations = dict(artifact_type='unproven_production_composition_obligations',
                       semantic_state=[dict(e, proof_status='unproven') for e in candidate['entries']],
                       physical_storage=binding['physical_storage_obligations'],
                       boundary_manifest=json.loads((architecture / 'boundary.json').read_text()),
                       boundary_manifest_sha256=binding['boundary_manifest_sha256'],
                       local_queue_proof=positive, formal_state_map_complete=False, gate_restore_authorized=False)
    require(len(obligations['semantic_state']) == 1543 and
            sum(s['width'] * s['depth'] for s in obligations['physical_storage']) == 102992412 and
            sum(s['width'] * s['depth'] for s in obligations['semantic_state']) == 102993417,
            'composition obligation inventory incomplete')
    (run / 'unproven-composition-obligations.json').write_bytes(canonical(obligations))
    rejections = {}

    def rejected(name, function, artifacts):
        try:
            function()
        except FormatError as error:
            rejections[name] = dict(rejected=str(error), artifacts=str(artifacts))
        else:
            raise AssertionError('Altered/incomplete production queue evidence accepted: ' + name)

    mutations = ('missing_step', 'missing_port', 'missing_output', 'missing_precondition', 'undetermined',
                 'vacuous', 'wrong_kind', 'forged_output_pass', 'forged_state_failure', 'miter', 'script',
                 'raw_engine', 'raw_hash', 'blackbox', 'assumption')
    for mutation in mutations:
        path = run / 'mutations' / mutation
        path.mkdir(parents=True)
        for name, data in original.items():
            (path / name).write_bytes(data)
        rows = [line.split('\t') for line in (path / 'queue-results.tsv').read_text().splitlines()]
        if mutation in ('miter', 'script'):
            filename = 'miter.sv' if mutation == 'miter' else 'prove.tcl'
            text = (path / filename).read_text()
            changed = text.replace("^ 1'b0", "^ 1'b1", 1) if mutation == 'miter' else text.replace('reset -none', 'reset -expression {clock}')
            require(changed != text, 'audit mutation did not change proof input')
            (path / filename).write_text(changed)
            role = 'miter' if mutation == 'miter' else 'script'
            next(r for r in rows if r[:2] == ['INPUT', role])[2] = sha((path / filename).read_bytes())
        elif mutation in ('raw_engine', 'raw_hash', 'blackbox', 'assumption'):
            log = (path / 'jasper.log').read_text()
            if mutation == 'raw_engine':
                changed = '\n'.join(line for line in log.splitlines() if not (
                    'The property "production_queue_miter.Queue_2_step_0" was proven' in line)) + '\n'
            elif mutation == 'raw_hash':
                changed = log.replace('CHECKPOINT_QUEUE_INPUT\tbinding\t', 'CHANGED_QUEUE_INPUT\tbinding\t')
            elif mutation == 'assumption':
                changed, count = re.subn(r'(assumptions\s*:\s*)0\b', r'\g<1>1', log)
                require(count > 0, 'missing assumptions audit target')
            else:
                changed = log + '\n[WARN] automatically BLACK-BOXED memory\n'
            require(changed != log, 'audit raw mutation did not alter evidence')
            (path / 'jasper.log').write_text(changed)
        else:
            suffix = dict(missing_step='Queue_2_step_0', missing_port='Queue_2_memory_WA',
                          missing_output='Queue_2_output_io_deq_valid',
                          missing_precondition='Queue_2_step_0:precondition1', undetermined='Queue_2_step_0',
                          vacuous='Queue_2_step_0:precondition1', wrong_kind='Queue_2_step_0',
                          forged_output_pass='Queue_39_output_io_deq_valid', forged_state_failure='Queue_2_step_0')[mutation]
            row = next(r for r in rows if len(r) == 4 and r[1].endswith('.' + suffix))
            if mutation.startswith('missing'):
                rows.remove(row)
            elif mutation == 'wrong_kind':
                row[2] = 'cover'
            else:
                row[3] = dict(undetermined='undetermined', vacuous='unreachable', forged_output_pass='proven',
                              forged_state_failure='cex')[mutation]
        (path / 'queue-results.tsv').write_text('\n'.join('\t'.join(row) for row in rows) + '\n')
        rejected(mutation, lambda: validate_proof(binding, path), path)

    for mutation in ('lost_state', 'lost_pending', 'lost_physical', 'boundary_hash', 'changed_state_id',
                     'changed_gate', 'authorize', 'complete', 'memory_port'):
        path = run / 'mutations' / mutation
        path.mkdir(parents=True)
        changed = copy.deepcopy(binding)
        spec = changed['queues']['Queue_2']
        if mutation == 'lost_state':
            spec['state'].pop()
        elif mutation == 'lost_pending':
            changed['pending_state'].pop()
        elif mutation == 'lost_physical':
            changed['physical_storage_obligations'].pop()
        elif mutation == 'boundary_hash':
            changed['boundary_manifest_sha256'] = '0' * 64
        elif mutation == 'changed_state_id':
            spec['state'][0]['state_id'] = '0' * 64
        elif mutation == 'changed_gate':
            spec['state'][0]['gate_instance'] = 'unproven_storage'
        elif mutation == 'authorize':
            changed['gate_restore_authorized'] = True
        elif mutation == 'complete':
            changed['formal_state_map_complete'] = True
        else:
            spec['memory_connections']['implementation']['WE'] = 'unproven_enable'
        (path / 'binding.json').write_bytes(canonical(changed))
        rejected(mutation, lambda: audit(architecture, synthesis_evidence, path), path)

    negatives = {}
    saved = json.loads((proof_run / 'summary.json').read_text())
    for name in ('Queue_2', 'Queue_39'):
        for kind in ('polarity', 'missing_register', 'write_enable', 'read_address'):
            value, prop = negative_binding(binding, name, kind)
            directory = proof_run / 'negative' / name / kind
            result = validate_proof(value, directory)
            category = 'register' if kind == 'polarity' else 'memory_port'
            require(prop in result['unproven_obligations'][category] and
                    saved['fresh_negative_proofs'][name + '/' + kind] == dict(status='cex', property=prop, directory=str(directory)),
                    'missing independent negative proof: ' + name + '/' + kind)
            negatives[name + '/' + kind] = result
    manifest = json.loads((architecture / 'manifest.json').read_text())
    loader_rejections = {}
    for label, value in (('binding', binding), ('audited_local_proof', dict(positive, top='AXI4FuzzerDUT'))):
        def load():
            gate_deposits(value, manifest, {}, {}, b'', {}, 'tb.dut')
        rejected('loader/' + label, load, proof)
        loader_rejections[label] = rejections.pop('loader/' + label)['rejected']
    require(audit(architecture, synthesis_evidence, proof) == positive, 'positive audit changed after mutations')
    require(all(sha(Path(p).read_bytes()) == h for p, h in initial_hashes.items()), 'original queue evidence changed')
    summary = dict(status='passed', run=str(run), proof_run=str(proof_run), unchanged_control_audits=2,
                   actual_artifact_mutations_rejected=len(rejections), rejections=rejections,
                   independent_fresh_negative_audits=negatives, incomplete_map_loader_rejections=loader_rejections,
                   original_proof_hashes=initial_hashes, original_proofs_unchanged=True,
                   formal_state_map_complete=False, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'proof-run', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.architecture, args.synthesis_evidence, args.proof_run, args.out)
    print(json.dumps({k: v for k, v in result.items() if k not in ('rejections', 'original_proof_hashes',
                                                                'independent_fresh_negative_audits')}, indent=2))


if __name__ == '__main__':
    main()
