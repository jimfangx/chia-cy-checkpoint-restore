"""Challenge composed production maps with rehashed actual native CAD artifacts.

All faults use copies of the complete selected production proof scopes. Positive
CAD files remain immutable. No synthetic design or invented formal result can
satisfy the positive control.
"""

import argparse
import copy
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.formal_state_map import sha
from .audit_production_state_map import audit_components, audit_map


def verify(path, out):
    path, out = Path(path).resolve(), Path(out).resolve()
    saved = json.loads(path.read_text())
    context = audit_components(saved['proof_components']['original'], saved['proof_components']['memory'])
    positive = audit_map(context, path)
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    before = context['dependencies']
    rejected = {}
    for role, cert_name, result_name in (('original', 'original-composition.json', 'original-results.tsv'),
                                         ('memory', 'memory-composition.json', 'composition-results.tsv')):
        source_run = Path(saved['proof_components'][role])
        original = json.loads((source_run / cert_name).read_text())
        for fault in ('shared_read', 'restricted_word', 'assertion_cex', 'missing_assertion', 'vacuous_word', 'missing_engine'):
            case = run / (role + '-' + fault)
            case.mkdir()
            scope = 'address' if fault == 'shared_read' else 'word'
            copied = case / scope
            copied.mkdir()
            cert = copy.deepcopy(original)
            source_scope = Path(original['proofs'][scope]['path'])
            for name in ('binding.json', 'miter.sv', 'prove.tcl', result_name, 'jasper.log'):
                (copied / name).write_bytes((source_scope / name).read_bytes())
            if fault in ('shared_read', 'restricted_word'):
                text = (copied / 'miter.sv').read_text()
                if fault == 'shared_read':
                    altered = text.replace('.ckregister_memory_0_Q0(implementation_ckregister_memory_0_Q0)',
                                           '.ckregister_memory_0_Q0(reference_ckregister_memory_0_Q0)')
                else:
                    altered = text.replace('wire word_relation_0 = watched_0 < ', 'wire word_relation_0 = watched_0 == 0 && watched_0 < ')
                require(altered != text, 'actual CAD source fault missed target')
                (copied / 'miter.sv').write_text(altered)
            else:
                rows = [line.split('\t') for line in (copied / result_name).read_text().splitlines()]
                prop = next(r for r in rows if len(r) == 4 and r[0] == 'PROPERTY' and r[1].endswith('.word_0_step'))
                if fault == 'missing_assertion': rows.remove(prop)
                elif fault == 'assertion_cex': prop[3] = 'cex'
                elif fault == 'vacuous_word':
                    next(r for r in rows if len(r) == 4 and r[1] == prop[1] + ':precondition1')[3] = 'unreachable'
                else:
                    text, count = re.subn(r'^.*The property "' + re.escape(prop[1].split('::', 1)[1]) + r'" was proven.*\n', '',
                                          (copied / 'jasper.log').read_text(), flags=re.M)
                    require(count > 0, 'actual native engine fault missed target')
                    (copied / 'jasper.log').write_text(text)
                (copied / result_name).write_text('\n'.join('\t'.join(r) for r in rows) + '\n')
            cert['proofs'][scope] = dict(path=str(copied), artifacts={n: sha((copied / n).read_bytes())
                for n in ('binding.json', 'miter.sv', 'prove.tcl', result_name, 'jasper.log')})
            (case / 'binding.json').write_bytes((source_run / 'binding.json').read_bytes())
            (case / cert_name).write_bytes(canonical(cert))
            # Rebind the map to the copied component and recompute every changed
            # dependency hash. Rejection must come from native proof obligations,
            # rather than the map merely retaining the old artifact digest.
            mapping = copy.deepcopy(saved)
            mapping['proof_components'][role] = str(case)
            replacement = {source_run / 'binding.json': case / 'binding.json', source_run / cert_name: case / cert_name}
            replacement.update({source_scope / n: copied / n for n in cert['proofs'][scope]['artifacts']})
            for source, destination in replacement.items():
                require(str(source) in mapping['dependency_artifacts'], 'unbound mutated CAD dependency')
                del mapping['dependency_artifacts'][str(source)]
                mapping['dependency_artifacts'][str(destination)] = sha(destination.read_bytes())
            artifact = case / 'asic_state_map.json'
            artifact.write_bytes(canonical(mapping))
            try:
                changed = audit_components(mapping['proof_components']['original'], mapping['proof_components']['memory'])
                audit_map(changed, artifact)
            except FormatError as error:
                rejected[role + '-' + fault] = dict(reason=str(error), artifact=str(artifact), certificate=str(case / cert_name),
                                                    mutated_proof=str(copied), map_sha256=sha(artifact.read_bytes()))
            else:
                raise AssertionError('Unproven composed production map accepted: ' + role + '-' + fault)
    require(all(sha(Path(p).read_bytes()) == digest for p, digest in before.items()), 'positive CAD bytes changed')
    result = dict(status='passed', run=str(run), positive=positive, rejection_checks=len(rejected), rejections=rejected,
                  preserved_positive_artifacts=True, formal_state_map_complete=True, gate_restore_authorized=False)
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
