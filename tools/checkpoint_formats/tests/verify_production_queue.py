"""Run every retained real-DUT queue obligation and fresh false-relation proofs."""

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

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.production_queue import SCRIPT, audit, miter, reconstruct
from .verify_formal_state_map import JASPER, ROOT


def negative_binding(binding, name, kind):
    value = copy.deepcopy(binding)
    value['queues'] = {name: value['queues'][name]}
    spec = value['queues'][name]
    if kind == 'polarity':
        spec['state'][0]['xor'] ^= 1
        property_name = name + '_step_0'
    elif kind == 'missing_register':
        spec['state'].pop(0)
        property_name = name + '_memory_RA0'
    else:
        require(kind in ('write_enable', 'read_address'), 'unsupported negative queue proof')
        port = 'WE' if kind == 'write_enable' else 'RA0'
        source = spec['implementation_source']
        ports = spec['memory_connections']['implementation']
        pattern = r'\.' + port + r'\s*\(\s*' + re.escape(ports[port]) + r'\s*\)'
        source, count = re.subn(pattern, lambda _: f'.{port} (~{ports[port]})', source)
        require(count == 1, 'negative port mutation was ambiguous')
        spec['implementation_source'] = source
        property_name = name + '_memory_' + port
    return value, '<embedded>::production_queue_miter.' + property_name


def verify(architecture, synthesis_evidence, out):
    architecture, synthesis_evidence, out = (Path(p).resolve() for p in (architecture, synthesis_evidence, out))
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    binding = reconstruct(architecture, synthesis_evidence)
    require(len(binding['queues']) == 165 and binding['retained_queue_register_bits'] == 1135 and
            binding['semantic_register_bits'] == 8261 and binding['physical_register_bits'] == 7256 and
            len(binding['pending_state']) == 883, 'verification requires the complete selected production DUT')
    commands, lock = [], threading.Lock()
    env = dict(os.environ)
    env.pop('LD_LIBRARY_PATH', None)

    def prove(value, destination):
        destination.mkdir(parents=True, exist_ok=False)
        (destination / 'binding.json').write_bytes(canonical(value))
        (destination / 'miter.sv').write_bytes(miter(value))
        (destination / 'prove.tcl').write_text(SCRIPT)
        tool_env = dict(env, CHECKPOINT_QUEUE_BINDING=str(destination / 'binding.json'),
                        CHECKPOINT_QUEUE_MITER=str(destination / 'miter.sv'),
                        CHECKPOINT_QUEUE_SCRIPT=str(destination / 'prove.tcl'))
        argv = [JASPER, '-allow_unsupported_OS', '-batch', '-tcl', str(destination / 'prove.tcl')]
        command = dict(cwd=str(destination.relative_to(ROOT)), argv=argv, log=str(destination / 'jasper.log'))
        with lock:
            commands.append(command)
            (run / 'commands.json').write_bytes(canonical(commands))
        with (destination / 'jasper.log').open('w') as stream:
            process = subprocess.run(argv, cwd=destination, env=tool_env, stdout=stream, stderr=subprocess.STDOUT,
                                     timeout=1800)
        with lock:
            command['exit_code'] = process.returncode
            (run / 'commands.json').write_bytes(canonical(commands))
        require(process.returncode == 0, 'Jasper failed: ' + command['log'])
        return destination

    positive = prove(binding, run / 'positive')
    result = audit(architecture, synthesis_evidence, positive)
    (run / 'independent-audit.json').write_bytes(canonical(result))
    negatives = {}

    def negative(name, kind):
        value, prop = negative_binding(binding, name, kind)
        directory = prove(value, run / 'negative' / name / kind)
        rows = [line.split('\t') for line in (directory / 'queue-results.tsv').read_text().splitlines()]
        require(['PROPERTY', prop, 'assert', 'cex'] in rows and
                re.search(r'A counterexample \(cex\).*property "' + re.escape(prop.split('::', 1)[1]) + '"',
                          (directory / 'jasper.log').read_text()), 'false queue relation did not produce a real counterexample')
        return name + '/' + kind, dict(status='cex', property=prop, directory=str(directory))

    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(negative, name, kind) for name in ('Queue_2', 'Queue_39')
                for kind in ('polarity', 'missing_register', 'write_enable', 'read_address')]
        for job in jobs:
            name, value = job.result()
            negatives[name] = value
    require(audit(architecture, synthesis_evidence, positive) == result, 'negative proofs changed positive evidence')
    summary = dict(result, status='in_progress', run=str(run), proof=str(positive),
                   fresh_negative_proofs=negatives, external_dependency_missing=None)
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), proof=str(positive), summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.architecture, args.synthesis_evidence, args.out)
    print(json.dumps({k: v for k, v in result.items() if k not in ('fresh_negative_proofs', 'unproven_obligations')}, indent=2))
    print('unproven_obligations=' + json.dumps({k: len(v) for k, v in result['unproven_obligations'].items()}))


if __name__ == '__main__':
    main()
