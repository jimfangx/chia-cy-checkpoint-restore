"""Independent production memory audit and actual artifact rejection controls."""

import argparse
import copy
import json
from pathlib import Path
import shutil
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.production_dut import sha
from tools.checkpoint_formats.production_memory import audit, reconstruct, validate_proof


FILES = ('binding.json', 'miter.sv', 'prove.tcl', 'memory-results.tsv', 'jasper.log')


def verify(architecture, proof_run, out):
    architecture, proof_run, out = (Path(p).resolve() for p in (architecture, proof_run, out))
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    binding = reconstruct(architecture)
    original = {(proof_run / cell / name): (proof_run / cell / name).read_bytes()
                for cell in binding['shapes'] for name in FILES}
    original[proof_run / 'binding.json'] = (proof_run / 'binding.json').read_bytes()
    positive = audit(architecture, proof_run)
    (run / 'independent-audit.json').write_bytes(canonical(positive))
    rejections = {}

    def rejected(name, function, destination):
        try:
            function()
        except FormatError as error:
            rejections[name] = dict(rejected=str(error), artifacts=str(destination))
        else:
            raise AssertionError('Altered production proof accepted: ' + name)

    for cell, shape in binding['shapes'].items():
        for mutation in ('miter', 'script', 'missing_word', 'missing_read', 'missing_cover', 'unproven',
                         'vacuous', 'raw_engine', 'raw_hash', 'blackbox'):
            directory = run / 'mutations' / cell / mutation
            directory.mkdir(parents=True)
            for name in FILES:
                (directory / name).write_bytes(original[proof_run / cell / name])
            results = (directory / 'memory-results.tsv').read_text()
            if mutation in ('miter', 'script'):
                path = directory / ('miter.sv' if mutation == 'miter' else 'prove.tcl')
                if mutation == 'miter':
                    changed = path.read_text().replace('(WE &&', '(!WE &&', 1)
                else:
                    changed = path.read_text().replace('reset -none', 'reset -expression {WE}')
                path.write_text(changed)
                role = 'miter' if mutation == 'miter' else 'script'
                rows = [r.split('\t') for r in results.splitlines()]
                for row in rows:
                    if row[:2] == ['INPUT', role]:
                        row[2] = sha(path.read_bytes())
                (directory / 'memory-results.tsv').write_text('\n'.join('\t'.join(r) for r in rows) + '\n')
            elif mutation in ('missing_word', 'missing_read', 'missing_cover', 'unproven', 'vacuous'):
                suffix = {'missing_word': '.word_step', 'missing_read': '.read_0', 'missing_cover': '.last',
                          'unproven': '.word_step', 'vacuous': '.word_step:precondition1'}[mutation]
                rows = [r.split('\t') for r in results.splitlines()]
                match = next(r for r in rows if len(r) == 4 and r[1].endswith(suffix))
                if mutation.startswith('missing'):
                    rows.remove(match)
                else:
                    match[3] = 'undetermined' if mutation == 'unproven' else 'unreachable'
                (directory / 'memory-results.tsv').write_text('\n'.join('\t'.join(r) for r in rows) + '\n')
            else:
                path = directory / 'jasper.log'
                log = path.read_text()
                if mutation == 'blackbox':
                    log += '\n[WARN (VERI-9033)] array automatically BLACK-BOXED\n'
                elif mutation == 'raw_hash':
                    log = log.replace('CHECKPOINT_MEMORY_INPUT\tbinding\t', 'CHANGED_MEMORY_INPUT\tbinding\t')
                else:
                    log = '\n'.join(line for line in log.splitlines()
                                    if not ('The property "production_memory_miter.word_step" was proven' in line)) + '\n'
                path.write_text(log)
            rejected(cell + '/' + mutation, lambda: validate_proof(shape, binding, directory), directory)

    for mutation in ('missing_instance', 'changed_port', 'changed_state_id', 'authorize', 'shape'):
        directory = run / 'mutations' / 'binding' / mutation
        directory.mkdir(parents=True)
        changed = copy.deepcopy(binding)
        if mutation == 'missing_instance':
            changed['instances'].pop()
        elif mutation == 'changed_port':
            changed['instances'][0]['fragment']['reads'][0]['address'] = 'forged_address'
        elif mutation == 'changed_state_id':
            changed['instances'][0]['state_id'] = '0' * 16
        elif mutation == 'authorize':
            changed['gate_restore_authorized'] = True
        else:
            changed['shapes'][next(iter(changed['shapes']))]['depth'] //= 2
        (directory / 'binding.json').write_bytes(canonical(changed))
        rejected('binding/' + mutation, lambda: audit(architecture, directory), directory)

    for mutation in ('inverted_write', 'changed_read', 'hidden_state'):
        directory = run / 'mutations' / 'architecture' / mutation
        directory.mkdir(parents=True)
        for path in architecture.iterdir():
            if path.is_file():
                shutil.copyfile(path, directory / path.name)
        path = directory / 'memory-models.v'
        text = path.read_text()
        if mutation == 'inverted_write':
            text = text.replace('if (WE)', 'if (!WE)', 1)
        elif mutation == 'changed_read':
            text = text.replace('contents[RA0]', 'contents[WA]', 1)
        else:
            text = text.replace('endmodule', 'reg hidden;\nendmodule', 1)
        path.write_text(text)
        candidate_path = directory / 'architecture-candidate.json'
        candidate = json.loads(candidate_path.read_text())
        candidate['models_sha256'] = sha(path.read_bytes())
        candidate_path.write_bytes(canonical(candidate))
        rejected('architecture/' + mutation, lambda: audit(directory, proof_run), directory)

    require(all(path.read_bytes() == data for path, data in original.items()), 'audit changed original proof bytes')
    require(audit(architecture, proof_run) == positive, 'repeat audit differs')
    summary = dict(status='passed', run=str(run), architecture=str(architecture), proof_run=str(proof_run),
                   unchanged_control_audits=2, actual_artifact_mutations_rejected=len(rejections),
                   rejections=rejections, original_proofs_unchanged=True, memory_instances=positive['memory_instances'],
                   memory_bits=positive['memory_bits'], shape_proofs=positive['shape_proofs'],
                   formal_state_map_complete=False, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    print(json.dumps({k: v for k, v in summary.items() if k != 'rejections'}, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--architecture', type=Path, required=True)
    parser.add_argument('--proof-run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    verify(args.architecture, args.proof_run, args.out)


if __name__ == '__main__':
    main()
