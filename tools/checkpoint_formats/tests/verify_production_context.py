"""Prove complete real parent contexts and queue live bits with installed Jasper."""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.production_context import SCRIPT, audit, proof_inputs, reconstruct
from .verify_formal_state_map import JASPER, ROOT


def negative_binding(binding, name, mutation):
    value = copy.deepcopy(binding)
    if mutation == 'whole_boundary':
        from tools.checkpoint_formats.replay import modules
        source = value['architecture_source']
        designs = modules(source)
        header, body = designs[value['top']]
        body, count = re.subn(r'\bassign\s+done\s*=\s*[^;]+;',
                             'assign done = axi4yank_auto_in_b_bits_echo_tl_state_size[3];', body)
        require(count == 1, 'ambiguous production whole-boundary negative')
        designs[value['top']] = (header, body)
        value['architecture_source'] = '\n'.join(f'module {n}({h});{b}endmodule\n' for n, (h, b) in designs.items())
        return value, 'whole', 'done_equal'
    if mutation == 'live_high_bit':
        value['cuts'][name]['io_deq_bits_echo_tl_state_size']['independent_mask'] = 0
        return value, 'live', name + '_live_io_deq_bits_echo_tl_state_size'
    spec = value['parents'][name]
    child_name, child = next((n, c) for n, c in spec['children'].items() if 'io_deq_valid' in c['cuts'])
    signal = child['ports']['io_deq_valid']
    if mutation == 'boundary':
        port = next(p for p, (d, w) in spec['ports'].items() if d == 'output' and w == 1)
        property_name = name + '_output_' + port
        destination = port
    else:
        require(mutation == 'child_input', 'unsupported context negative')
        port = 'io_enq_valid'
        destination = child['ports'][port]
        property_name = name + '_child_' + child_name + '_' + port + '_equal'
    body, count = re.subn(r'\bassign\s+' + re.escape(destination) + r'\s*=\s*[^;]+;',
                         f'assign {destination} = {signal};', spec['body'])
    require(count == 1, 'ambiguous context negative assignment')
    # Rebuild byte positions of all children after the real source edit.
    from tools.checkpoint_formats.production_queue import instances
    updated = instances(body)
    require(updated.keys() == spec['children'].keys(), 'negative changed hierarchy')
    for n, c in updated.items():
        spec['children'][n].update(c)
    spec['body'] = body
    return value, 'parent', property_name


def verify(architecture, synthesis_evidence, queue_proof, out):
    paths = [Path(p).resolve() for p in (architecture, synthesis_evidence, queue_proof, out)]
    architecture, synthesis_evidence, queue_proof, out = paths
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    binding = reconstruct(architecture, synthesis_evidence, queue_proof)
    require(set(binding['parents']) == {'AXI4Deinterleaver', 'AXI4UserYanker'} and
            len(binding['cuts']) == 160 and sum(len(c) for c in binding['cuts'].values()) == 304 and
            sum(sum(p['registers'].values()) for p in binding['parents'].values()) == 520,
            'verification requires complete selected production contexts')
    commands = []
    env = dict(os.environ)
    env.pop('LD_LIBRARY_PATH', None)

    def prove(value, kind, destination):
        destination.mkdir(parents=True, exist_ok=False)
        artifacts = proof_inputs(value, kind)
        for role, filename in (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')):
            (destination / filename).write_bytes(artifacts[role])
        tool_env = dict(env, CHECKPOINT_CONTEXT_BINDING=str(destination / 'binding.json'),
                        CHECKPOINT_CONTEXT_MITER=str(destination / 'miter.sv'),
                        CHECKPOINT_CONTEXT_SCRIPT=str(destination / 'prove.tcl'),
                        CHECKPOINT_CONTEXT_TOP='production_queue_miter' if kind == 'live' else 'production_context_miter')
        argv = [JASPER, '-allow_unsupported_OS', '-batch', '-tcl', str(destination / 'prove.tcl')]
        command = dict(cwd=str(destination.relative_to(ROOT)), argv=argv, log=str(destination / 'jasper.log'))
        commands.append(command)
        (run / 'commands.json').write_bytes(canonical(commands))
        with (destination / 'jasper.log').open('w') as stream:
            process = subprocess.run(argv, cwd=destination, env=tool_env, stdout=stream, stderr=subprocess.STDOUT,
                                     timeout=3600)
        command['exit_code'] = process.returncode
        (run / 'commands.json').write_bytes(canonical(commands))
        require(process.returncode == 0, 'Jasper failed: ' + command['log'])
        return destination

    positives = {}
    for kind in ('parent', 'live', 'whole'):
        path = prove(binding, kind, run / kind)
        positives[kind] = audit(architecture, synthesis_evidence, queue_proof, kind, path)
        (run / (kind + '-audit.json')).write_bytes(canonical(positives[kind]))
    negatives = {}
    trials = [(n, mutation) for n in sorted(binding['parents']) for mutation in ('boundary', 'child_input')]
    trials.append(('Queue_39', 'live_high_bit'))
    trials.append((binding['top'], 'whole_boundary'))
    for name, mutation in trials:
        value, kind, prop = negative_binding(binding, name, mutation)
        directory = prove(value, kind, run / 'negative' / name / mutation)
        qualified = '<embedded>::' + ('production_queue_miter' if kind == 'live' else 'production_context_miter') + '.' + prop
        require(f'PROPERTY\t{qualified}\tassert\tcex' in (directory / 'context-results.tsv').read_text() and
                re.search(r'A counterexample \(cex\).*property "' + re.escape(qualified.split('::', 1)[1]) + '"',
                          (directory / 'jasper.log').read_text()), 'false context lemma did not produce a counterexample')
        negatives[name + '/' + mutation] = dict(kind=kind, property=qualified, directory=str(directory), status='cex')
    for kind in positives:
        require(audit(architecture, synthesis_evidence, queue_proof, kind, run / kind) == positives[kind],
                'negative context proof changed positive artifacts')
    summary = dict(status='in_progress', run=str(run), positive=positives, fresh_negative_proofs=negatives,
                   queue_proof=str(queue_proof), formal_state_map_complete=False, gate_restore_authorized=False,
                   remaining='Complete original/architecture/netlist register, memory and boundary composition',
                   external_dependency_missing=None)
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'queue-proof', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.architecture, args.synthesis_evidence, args.queue_proof, args.out), indent=2))


if __name__ == '__main__':
    main()
