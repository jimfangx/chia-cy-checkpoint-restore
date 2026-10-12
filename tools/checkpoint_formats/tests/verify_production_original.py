"""Prove full actual original/architecture composition with native CAD faults."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.production_original import certificate, proof_inputs, reconstruct, validate
from tools.checkpoint_formats.production_queue import instances
from tools.checkpoint_formats.replay import modules
from .verify_formal_state_map import JASPER, ROOT


def negative_binding(binding, fault):
    value = copy.deepcopy(binding)
    index, memory = next((i, m) for i, m in enumerate(value['memories'])
                         if m['entry']['module'].startswith('Queue') and m['entry']['depth'] > 1)
    module, instance = memory['entry']['module'], memory['gate_components'][-1]
    source = value['implementation_source']
    _, body = modules(source)[module]
    child = instances(body)[instance]
    if fault == 'register_transition':
        entries = [(i, e) for i, e in enumerate(value['registers']) if e['module'] == module and e['width'] == 1]
        reg_index, entry = entries[0]
        leaf = entry['original_path'].rsplit('.', 1)[-1]
        changed, count = re.subn(r'\b' + re.escape(leaf) + r'\s*<=\s*([^;]+);',
                                lambda m: leaf + ' <= ~(' + m[1] + ');', body)
        require(count >= 1, 'no actual original-composition register transition fault')
        kind, prop = 'word', f'register_{reg_index}_step'
    else:
        port = 'RA0' if fault.startswith('address') else 'WD' if fault == 'word_data' else 'WE'
        old = child['ports'][port]
        # The audited emitter adapter accepts named-port expressions without
        # nested parentheses. Invert the actual selected term of the enable
        # cone (or full scalar/vector address/data signal) in that grammar.
        new = child['ports']['Q0'] if fault == 'address_feedback' else '~' + old
        before = body[child['start']:child['end']]
        after, count = re.subn(r'\.' + port + r'\s*\(\s*' + re.escape(old) + r'\s*\)',
                               lambda _: f'.{port}({new})', before)
        require(count == 1, 'ambiguous original composition port fault')
        changed = body[:child['start']] + after + body[child['end']:]
        kind = 'address' if fault.startswith('address') else 'word'
        prop = f'port_ckregister_memory_{index}_RA0' if kind == 'address' else f'word_{index}_step'
    declarations = list(re.finditer(r'\bmodule\s+' + re.escape(module) + r'\s*\([^;]*\);(.*?)endmodule\b', source, re.S))
    require(len(declarations) == 1 and declarations[0][1] == body, 'ambiguous original composition module')
    declaration = declarations[0]
    value['implementation_source'] = source[:declaration.start(1)] + changed + source[declaration.end(1):]
    return value, kind, '<embedded>::production_original_miter.' + prop


def verify(architecture, memory_proof, out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    binding = reconstruct(architecture, memory_proof)
    require(binding['state_entries'] == 1543 and binding['register_bits'] == 8261 and
            binding['memory_instances'] == 201 and binding['memory_bits'] == 102985156 and
            binding['memory_words'] == 13501966 and binding['read_ports'] == 233,
            'verification requires the complete actual selected metasim DUT')
    (run / 'binding.json').write_bytes(canonical(binding))
    commands, lock = [], threading.Lock()
    env = dict(os.environ)
    env.pop('LD_LIBRARY_PATH', None)

    def prove(value, kind, directory):
        directory.mkdir(parents=True, exist_ok=False)
        inputs = proof_inputs(value, kind)
        for role, name in (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')):
            (directory / name).write_bytes(inputs[role])
        tool_env = dict(env, CHECKPOINT_ORIGINAL_BINDING=str(directory / 'binding.json'),
                        CHECKPOINT_ORIGINAL_MITER=str(directory / 'miter.sv'),
                        CHECKPOINT_ORIGINAL_SCRIPT=str(directory / 'prove.tcl'))
        argv = [JASPER, '-allow_unsupported_OS', '-batch', '-tcl', str(directory / 'prove.tcl')]
        command = dict(cwd=str(directory.relative_to(ROOT)), argv=argv, log=str(directory / 'jasper.log'))
        with lock:
            commands.append(command)
            (run / 'commands.json').write_bytes(canonical(commands))
        with (directory / 'jasper.log').open('w') as stream:
            process = subprocess.run(argv, cwd=directory, env=tool_env, stdout=stream, stderr=subprocess.STDOUT, timeout=7200)
        with lock:
            command['exit_code'] = process.returncode
            (run / 'commands.json').write_bytes(canonical(commands))
        require(process.returncode == 0, 'Jasper original composition failed: ' + command['log'])
        return directory

    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {kind: pool.submit(prove, binding, kind, run / kind) for kind in ('address', 'word')}
        proofs = {kind: job.result() for kind, job in jobs.items()}
    result = certificate(binding, proofs['address'], proofs['word'])
    (run / 'original-composition.json').write_bytes(canonical(result))
    negatives = {}

    def negative(fault):
        value, kind, prop = negative_binding(binding, fault)
        directory = prove(value, kind, run / 'negative' / fault)
        report = validate(value, kind, directory, negative=True)
        require(prop in report['counterexamples'], 'missing expected actual original CAD counterexample: ' + fault)
        try:
            validate(value, kind, directory)
        except FormatError:
            pass
        else:
            raise AssertionError('Unproven original composition accepted')
        return fault, dict(directory=str(directory), kind=kind, property=prop, counterexamples=report['counterexamples'])

    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(negative, fault) for fault in
                ('address_port', 'address_feedback', 'word_data', 'word_enable', 'register_transition')]
        for job in jobs:
            name, report = job.result()
            negatives[name] = report
    require(certificate(binding, proofs['address'], proofs['word']) == result, 'negative proofs changed positive evidence')
    summary = dict(status='passed', run=str(run), certificate=str(run / 'original-composition.json'),
                   results=result['results'], fresh_negative_proofs=negatives,
                   state_entries=binding['state_entries'], register_bits=binding['register_bits'],
                   memory_bits=binding['memory_bits'], formal_state_map_complete=False, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'memory-proof', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.architecture, args.memory_proof, args.out), indent=2))


if __name__ == '__main__':
    main()
