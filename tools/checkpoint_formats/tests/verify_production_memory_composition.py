"""Run complete production read-closure and word-composition proofs in Jasper."""

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
from tools.checkpoint_formats.production_memory_composition import certificate, proof_inputs, reconstruct, validate
from tools.checkpoint_formats.production_queue import instances
from tools.checkpoint_formats.replay import modules
from .verify_formal_state_map import JASPER, ROOT


def negative_binding(binding, fault):
    value = copy.deepcopy(binding)
    # A real retained queue macro, not a synthetic replacement design.
    index, memory = next((i, m) for i, m in enumerate(value['registers']['memories'])
                         if len(m['gate_components']) == 2 and m['entry']['depth'] > 1)
    source = value['registers']['implementation_source']
    module, instance = memory['entry']['module'], memory['gate_components'][-1]
    _, body = modules(source)[module]
    child = instances(body)[instance]
    port = 'RA0' if fault.startswith('address') else 'WD' if fault == 'word_data' else 'WE'
    old = child['ports'][port]
    new = child['ports']['Q0'] if fault == 'address_feedback' else '~' + old
    before = body[child['start']:child['end']]
    after, count = re.subn(r'\.' + port + r'\s*\(\s*' + re.escape(old) + r'\s*\)',
                           lambda _: f'.{port}({new})', before)
    require(count == 1, 'ambiguous composition fault')
    changed = body[:child['start']] + after + body[child['end']:]
    declarations = list(re.finditer(r'\bmodule\s+' + re.escape(module) + r'\s*\([^;]*\);(.*?)endmodule\b', source, re.S))
    require(len(declarations) == 1 and declarations[0][1] == body, 'ambiguous selected production module')
    declaration = declarations[0]
    value['registers']['implementation_source'] = source[:declaration.start(1)] + changed + source[declaration.end(1):]
    kind = 'address' if fault.startswith('address') else 'word'
    property_name = (f'ckregister_memory_{index}_RA0_equal' if kind == 'address' else f'word_{index}_step')
    return value, kind, '<embedded>::production_composition_miter.' + property_name


def verify(architecture, synthesis_evidence, register_proof, memory_proof, optimized, out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    binding = reconstruct(architecture, synthesis_evidence, register_proof, memory_proof, optimized)
    require(binding['memory_instances'] == 201 and binding['memory_bits'] == 102985156 and
            binding['memory_words'] == 13501966 and binding['read_ports'] == 233 and
            binding['registers']['physical_register_bits'] == 7256,
            'verification requires the complete actual metasim DUT')
    (run / 'binding.json').write_bytes(canonical(binding))
    commands, lock = [], threading.Lock()
    env = dict(os.environ)
    env.pop('LD_LIBRARY_PATH', None)

    def prove(value, kind, destination):
        destination.mkdir(parents=True, exist_ok=False)
        for role, filename in (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')):
            (destination / filename).write_bytes(proof_inputs(value, kind)[role])
        tool_env = dict(env, CHECKPOINT_COMPOSITION_BINDING=str(destination / 'binding.json'),
                        CHECKPOINT_COMPOSITION_MITER=str(destination / 'miter.sv'),
                        CHECKPOINT_COMPOSITION_SCRIPT=str(destination / 'prove.tcl'))
        argv = [JASPER, '-allow_unsupported_OS', '-batch', '-tcl', str(destination / 'prove.tcl')]
        command = dict(cwd=str(destination.relative_to(ROOT)), argv=argv, log=str(destination / 'jasper.log'))
        with lock:
            commands.append(command)
            (run / 'commands.json').write_bytes(canonical(commands))
        with (destination / 'jasper.log').open('w') as stream:
            process = subprocess.run(argv, cwd=destination, env=tool_env, stdout=stream,
                                     stderr=subprocess.STDOUT, timeout=7200)
        with lock:
            command['exit_code'] = process.returncode
            (run / 'commands.json').write_bytes(canonical(commands))
        require(process.returncode == 0, 'Jasper composition failed: ' + command['log'])
        return destination

    with ThreadPoolExecutor(max_workers=2) as pool:
        positives = {kind: pool.submit(prove, binding, kind, run / kind) for kind in ('address', 'word')}
        proofs = {kind: job.result() for kind, job in positives.items()}
    result = certificate(binding, proofs['address'], proofs['word'])
    (run / 'memory-composition.json').write_bytes(canonical(result))
    negatives = {}

    def negative(fault):
        value, kind, prop = negative_binding(binding, fault)
        directory = prove(value, kind, run / 'negative' / fault)
        report = validate(value, kind, directory, negative=True)
        require(prop in report['counterexamples'], 'native composition fault did not produce expected counterexample: ' + fault)
        try:
            validate(value, kind, directory)
        except FormatError:
            pass
        else:
            raise AssertionError('Unproven memory composition accepted')
        return fault, dict(directory=str(directory), kind=kind, property=prop, status='cex')

    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(negative, fault) for fault in ('address_port', 'address_feedback', 'word_data', 'word_enable')]
        for job in jobs:
            name, report = job.result()
            negatives[name] = report
    require(certificate(binding, proofs['address'], proofs['word']) == result, 'negatives changed positive evidence')
    summary = dict(status='passed', run=str(run), results=result['results'], fresh_negative_proofs=negatives,
                   certificate=str(run / 'memory-composition.json'), formal_state_map_complete=False, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'register-proof', 'memory-proof', 'optimized', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.architecture, args.synthesis_evidence, args.register_proof, args.memory_proof, args.optimized, args.out)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
