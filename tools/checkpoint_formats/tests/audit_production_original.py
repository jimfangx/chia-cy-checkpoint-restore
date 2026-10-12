"""Independent original/architecture certificate reconstruction and challenges.

Do not import the certificate exporter. Inspect complete state relation/cut
membership, native engines and universal arrays before comparing exact export.
"""

import argparse
import copy
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.formal_state_map import gate_deposits, sha
from tools.checkpoint_formats.production_original import FILES, reconstruct, validate, validate_domains
from tools.checkpoint_formats.production_register import _interface
from tools.checkpoint_formats.production_queue import instances
from tools.checkpoint_formats.replay import modules
from .verify_production_original import negative_binding


def audit_original_cut(binding, text):
    """Independently compare every retained original module body to actual cut RTL.

    Recurse through the original instances, check all propagated cut ports, and
    remove only actual array statements and their exact generated witnesses.
    The remaining scalar logic/storage must be identical after whitespace
    normalization. This checker does not call the cut generator.
    """
    original, generated = modules(binding['reference_source']), modules(text)
    top = instances(generated['production_original_miter'][1])['reference']['cell']
    seen = set()

    def remove(pattern, body, reason):
        changed, count = re.subn(pattern, '', body)
        require(count == 1, reason)
        return changed

    def walk(name, cut, prefix):
        header, body = original[name]
        cut_header, actual = generated[cut]
        interface = _interface(header, body)
        if not re.search(r'\binput\b', header):
            body = re.sub(r'\b(?:input|output)\s+[^;]*;', '', body)
        exposure = {}
        child_removals, cut_removals = [], []
        children, cut_children = instances(body), instances(actual)
        require(children.keys() == cut_children.keys(), 'lost/added original cut hierarchy instance')
        for instance, child in children.items():
            selected = cut_children[instance]
            extra = walk(child['cell'], selected['cell'], prefix + instance + '.')
            require(selected['ports'] == dict(child['ports'], **{p: p for p in extra}), 'changed original hierarchy cut wiring')
            require(not exposure.keys() & extra.keys(), 'duplicate audited original cut port')
            exposure.update(extra)
            child_removals.append((child['start'], child['end']))
            cut_removals.append((selected['start'], selected['end']))
        for start, end in sorted(child_removals, reverse=True):
            body = body[:start] + body[end:]
        for start, end in sorted(cut_removals, reverse=True):
            actual = actual[:start] + actual[end:]
        for index, item in enumerate(binding['memories']):
            entry = item['entry']
            parent, _, leaf = entry['original_path'].rpartition('.')
            if (parent + '.' if parent else '') != prefix:
                continue
            require(index not in seen and entry['module'] == name, 'wrong audited original array owner')
            seen.add(index)
            width, depth = entry['width'], entry['depth']
            aw = max(1, (depth - 1).bit_length())
            write, reads = entry['memory']['write'], entry['memory']['reads']
            body = remove(r'\breg\s+(?:\[' + str(width-1) + r':0\]\s*)?' + re.escape(leaf) +
                          r'\s*\[0:' + str(depth-1) + r'\]\s*;', body, 'missing audited original array declaration')
            body = remove(r'\bif\s*\(' + re.escape(write['enable']) + r'\)\s*begin\s*' +
                          re.escape(leaf) + r'\[' + re.escape(write['address']) + r'\]\s*<=\s*' +
                          re.escape(write['data']) + r'\s*;\s*end\b', body, 'changed audited original array write')
            for read in reads:
                body = remove(r'\bassign\s+' + re.escape(read['data']) + r'\s*=\s*' + re.escape(leaf) +
                              r'\[' + re.escape(read['address']) + r'\]\s*;', body, 'changed audited original array read')
            ports = dict(CP=('output', 1, 'clock'), WE=('output', 1, write['enable']),
                         WA=('output', aw, write['address']), WD=('output', width, write['data']))
            for i, read in enumerate(reads):
                ports[f'RA{i}'] = ('output', aw, read['address'])
                ports[f'Q{i}'] = ('input', width, read['data'])
            for port, (direction, width, signal) in ports.items():
                extra = f'ckregister_memory_{index}_{port}'
                exposure[extra] = (direction, width)
                lhs, rhs = (signal, extra) if direction == 'input' else (extra, signal)
                actual = remove(r'\bassign\s+' + re.escape(lhs) + r'\s*=\s*' + re.escape(rhs) + r'\s*;',
                                actual, 'changed/omitted actual original cut witness')
        require(_interface(cut_header, actual) == dict(interface, **exposure), 'incomplete original cut module interface')
        # The original extractor may remove empty clocked blocks. No other
        # scalar procedural or combinational text is allowed to change.
        empty = r'\balways\s*@\s*\(posedge clock\)\s*begin\s*end\b'
        body, actual = re.sub(empty, '', body), re.sub(empty, '', actual)
        require(re.sub(r'\s+', '', body) == re.sub(r'\s+', '', actual), 'changed/dropped original scalar logic or storage')
        return exposure

    walk(binding['top'], top, '')
    require(seen == set(range(len(binding['memories']))), 'missing independently audited original array')


def audit(binding, path):
    path = Path(path)
    saved = json.loads(path.read_text())
    validate_domains(binding)
    require(all(sha(Path(p).read_bytes()) == h for p, h in binding['prerequisites'].items()), 'changed original CAD prerequisite')
    require(set(saved.get('proofs', {})) == {'address', 'word'}, 'missing original proof scope')
    proofs = {kind: Path(saved['proofs'][kind]['path']).resolve() for kind in ('address', 'word')}
    results = {kind: validate(binding, kind, proof) for kind, proof in proofs.items()}
    address = (proofs['address'] / 'miter.sv').read_text()
    word = (proofs['word'] / 'miter.sv').read_text()
    for text in (address, word):
        audit_original_cut(binding, text)
        relation = re.findall(r'^wire relation = (.*);$', text, re.M)
        expected = ' && '.join(f'(reference.{e["original_path"]} == implementation.{e["architecture_path"]})'
                               for e in binding['registers'])
        require(relation == [expected] and 'ckregister_memory_' not in expected, 'incomplete/constrained original state relation')
        require('assume property' not in text and 'initial ' not in text, 'constrained original miter')
    for index, entry in enumerate(binding['registers']):
        require(f'register_{index}_step: assert property' in word, 'missing original register induction')
        for bit in range(entry['width']):
            for value in (0, 1):
                require(f'register_{index}_bit_{bit}_{value}: cover property' in word, 'missing original register nonvacuity')
    for index, item in enumerate(binding['memories']):
        entry, width, depth = item['entry'], item['entry']['width'], item['entry']['depth']
        aw = max(1, (depth - 1).bit_length())
        for port in range(len(entry['memory']['reads'])):
            name = f'ckregister_memory_{index}_Q{port}'
            for side in ('reference', 'implementation'):
                require(address.count(f'input [{width-1}:0] {side}_{name}') == 1 and
                        address.count(f'.{name}({side}_{name})') == 1, 'shared/reshaped/missing original independent read word')
            require(f'{name}_independent: cover property' in address, 'missing original independent-read witness')
        require(word.count(f'input [{aw-1}:0] watched_{index},') == 1 and
                f'old_reference_{index} == old_implementation_{index};' in word and
                f'word_{index}_step: assert property' in word and
                f'implementation_ckregister_memory_{index}_WA == watched_{index}' in word,
                'nonuniversal/missing original array word obligation')
    expected = dict(original_composition_version=1, artifact_type='production_original_architecture_composition',
                    binding_sha256=sha(canonical(binding)),
                    proofs={kind: dict(path=str(proof), artifacts={n: sha((proof / n).read_bytes()) for n in FILES})
                            for kind, proof in proofs.items()}, results=results,
                    registers=binding['registers'], memories=binding['memories'],
                    state_entries=binding['state_entries'], state_bits=binding['state_bits'], register_bits=binding['register_bits'],
                    memory_instances=binding['memory_instances'], memory_bits=binding['memory_bits'], memory_words=binding['memory_words'],
                    read_ports=binding['read_ports'], original_to_architecture='inductive complete register/array equality',
                    read_closure='proven with independent read words',
                    memory_authority='all bound universal original word/read adapters and all actual port cones',
                    formal_state_map_complete=False, gate_restore_authorized=False)
    require(saved == expected, 'changed/incomplete/unauthorized original composition certificate')
    return dict(status='passed', state_entries=binding['state_entries'], register_bits=binding['register_bits'],
                memory_bits=binding['memory_bits'], memory_instances=binding['memory_instances'], read_ports=binding['read_ports'],
                results=results, certificate_sha256=sha(path.read_bytes()),
                formal_state_map_complete=False, gate_restore_authorized=False)


def verify(proof_run, out):
    proof_run, out = Path(proof_run).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    saved_binding = json.loads((proof_run / 'binding.json').read_text())
    binding = reconstruct(saved_binding['architecture'], saved_binding['memory_proof'])
    require(binding == saved_binding, 'changed original composition binding')
    path = proof_run / 'original-composition.json'
    positive = audit(binding, path)
    saved = json.loads(path.read_text())
    originals = {kind: {n: (Path(p['path']) / n).read_bytes() for n in FILES} for kind, p in saved['proofs'].items()}
    rejected = {}

    def reject(name, function, artifact):
        try:
            function()
        except FormatError as error:
            rejected[name] = dict(reason=str(error), artifact=str(artifact))
        else:
            raise AssertionError('Unsupported original composition accepted: ' + name)

    for fault in ('missing_register', 'register_bit', 'state_id', 'register_path', 'missing_memory', 'memory_depth',
                  'memory_path', 'memory_port', 'missing_adapter', 'scope', 'native_hash', 'binding', 'count',
                  'read_authority', 'memory_authority', 'original_authority', 'gate_authority'):
        value = copy.deepcopy(saved)
        if fault == 'missing_register': value['registers'].pop()
        elif fault == 'register_bit': value['registers'][0]['width'] += 1
        elif fault == 'state_id': value['registers'][0]['state_id'] = '0' * 16
        elif fault == 'register_path': value['registers'][0]['architecture_path'] += '_missing'
        elif fault == 'missing_memory': value['memories'].pop()
        elif fault == 'memory_depth': value['memories'][0]['entry']['depth'] -= 1
        elif fault == 'memory_path': value['memories'][0]['gate_components'] = ['missing']
        elif fault == 'memory_port': value['memories'][0]['entry']['memory']['reads'].pop()
        elif fault == 'missing_adapter': value['memories'][0]['entry']['memory']['cell'] = 'Unproven'
        elif fault == 'scope': value['proofs'].pop('address')
        elif fault == 'native_hash': value['proofs']['word']['artifacts'].pop('jasper.log')
        elif fault == 'binding': value['binding_sha256'] = '0' * 64
        elif fault == 'count': value['register_bits'] -= 1
        elif fault == 'read_authority': value['read_closure'] = 'common reads assumed'
        elif fault == 'memory_authority': value['memory_authority'] = 'selected finite words'
        elif fault == 'original_authority': value['original_to_architecture'] = 'output equality only'
        else: value.update(formal_state_map_complete=True, gate_restore_authorized=True)
        artifact = run / (fault + '.json')
        artifact.write_bytes(canonical(value))
        reject(fault, lambda: audit(binding, artifact), artifact)

    for fault in ('missing_address', 'address_cex', 'missing_word', 'word_cex', 'vacuous_word',
                  'missing_engine', 'missing_hash', 'shared_read', 'restricted_address', 'lost_register'):
        kind = 'address' if fault in ('missing_address', 'address_cex', 'shared_read') else 'word'
        directory = run / fault
        directory.mkdir()
        for n, data in originals[kind].items():
            (directory / n).write_bytes(data)
        tsv, log = directory / 'original-results.tsv', directory / 'jasper.log'
        rows = tsv.read_text().splitlines()
        property_row = next(line for line in rows if line.startswith('PROPERTY\t') and '\tassert\tproven' in line)
        if fault.startswith('missing_') and fault not in ('missing_engine', 'missing_hash'):
            rows.remove(property_row)
            tsv.write_text('\n'.join(rows) + '\n')
        elif fault in ('address_cex', 'word_cex'):
            tsv.write_text(tsv.read_text().replace(property_row, property_row.replace('\tproven', '\tcex'), 1))
        elif fault == 'vacuous_word':
            p = property_row.split('\t')[1] + ':precondition1'
            tsv.write_text(tsv.read_text().replace(p + '\tcover\tcovered', p + '\tcover\tunreachable', 1))
        elif fault == 'missing_engine':
            text, count = re.subn(r'^.*The property "production_original_miter\.[^"]+" was proven (?:in|at) .*\n', '', log.read_text(), count=1, flags=re.M)
            require(count == 1, 'no independent native original engine message')
            log.write_text(text)
        elif fault == 'missing_hash':
            log.write_text(re.sub(r'^CHECKPOINT_ORIGINAL_INPUT\t[^\n]+\n', '', log.read_text(), count=1, flags=re.M))
        else:
            source = directory / 'miter.sv'
            text = source.read_text()
            if fault == 'shared_read':
                text, count = re.subn(r'implementation_ckregister_memory_\d+_Q0', 'reference_ckregister_memory_0_Q0', text)
            elif fault == 'restricted_address':
                text, count = re.subn(r'input \[\d+:0\] watched_0,', 'input [0:0] watched_0,', text, count=1)
            else:
                text, count = re.subn(r'^register_0_step: assert property[^\n]+\n', '', text, count=1, flags=re.M)
            require(count > 0 and text != source.read_text(), 'no actual original CAD mutation')
            source.write_text(text)
        changed = copy.deepcopy(saved)
        changed['proofs'][kind] = dict(path=str(directory), artifacts={n: sha((directory / n).read_bytes()) for n in FILES})
        artifact = run / (fault + '.json')
        artifact.write_bytes(canonical(changed))
        reject(fault, lambda: audit(binding, artifact), artifact)

    summary = json.loads((proof_run / 'summary.json').read_text())
    negatives = {}
    for fault in ('address_port', 'address_feedback', 'word_data', 'word_enable', 'register_transition'):
        value, kind, prop = negative_binding(binding, fault)
        report = summary['fresh_negative_proofs'][fault]
        directory = proof_run / 'negative' / fault
        require(report['directory'] == str(directory) and report['kind'] == kind and report['property'] == prop,
                'wrong original native negative binding')
        result = validate(value, kind, directory, negative=True)
        require(prop in result['counterexamples'] and result['counterexamples'] == report['counterexamples'], 'missing original native fault')
        reject('native_' + fault, lambda: validate(value, kind, directory), directory)
        negatives[fault] = dict(kind=kind, property=prop, counterexamples=result['counterexamples'])
    reject('gate_load', lambda: gate_deposits(saved, {}, {}, {}, b'', {}, 'tb.dut'), path)
    require(all((Path(saved['proofs'][kind]['path']) / n).read_bytes() == data
                for kind, files in originals.items() for n, data in files.items()), 'original audits changed positive CAD bytes')
    require(audit(binding, path) == positive, 'original positive changed after mutation scope')
    result = dict(status='passed', run=str(run), proof_run=str(proof_run), positive=positive,
                  rejected=rejected, rejection_checks=len(rejected), native_negatives=negatives,
                  preserved_positive_artifacts=True, formal_state_map_complete=False, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(result))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('proof-run', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.proof_run, args.out), indent=2))


if __name__ == '__main__':
    main()
