"""Fresh Jasper proofs of every real production memory adapter shape.

Run with the CAD license setup sourced. The full selected production
architecture is required. This evidence never authorizes gate restoration.
"""

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
from tools.checkpoint_formats.production_memory import SCRIPT, audit, miter, reconstruct
from .verify_formal_state_map import JASPER, ROOT


def verify(architecture, out):
    architecture, out = Path(architecture).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    binding = reconstruct(architecture)
    require(binding['memory_instances'] == 201 and binding['memory_bits'] == 102985156 and
            binding['memory_words'] == 13501966 and len(binding['shapes']) == 17,
            'verification requires the complete selected production DUT, not a fixture')
    (run / 'binding.json').write_bytes(canonical(binding))
    commands, lock = [], threading.Lock()
    tool_env = dict(os.environ)
    tool_env.pop('LD_LIBRARY_PATH', None)

    def prove(cell, shape, destination):
        destination.mkdir(parents=True)
        (destination / 'binding.json').write_bytes(canonical(binding))
        (destination / 'miter.sv').write_bytes(miter(shape))
        (destination / 'prove.tcl').write_text(SCRIPT)
        env = dict(tool_env, CHECKPOINT_MEMORY_BINDING=str(destination / 'binding.json'),
                   CHECKPOINT_MEMORY_MITER=str(destination / 'miter.sv'),
                   CHECKPOINT_MEMORY_SCRIPT=str(destination / 'prove.tcl'))
        argv = [JASPER, '-allow_unsupported_OS', '-batch', '-tcl', str(destination / 'prove.tcl')]
        command = dict(cwd=str(destination.relative_to(ROOT)), argv=argv, log=str(destination / 'jasper.log'))
        with lock:
            commands.append(command)
            (run / 'commands.json').write_bytes(canonical(commands))
        with (destination / 'jasper.log').open('w') as stream:
            process = subprocess.run(argv, cwd=destination, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                     timeout=600)
        with lock:
            command['exit_code'] = process.returncode
            (run / 'commands.json').write_bytes(canonical(commands))
        require(process.returncode == 0, 'Jasper failed: ' + command['log'])
        return cell

    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(prove, cell, shape, run / cell) for cell, shape in binding['shapes'].items()]
        for job in jobs:
            job.result()
    positive = audit(architecture, run)
    (run / 'independent-audit.json').write_bytes(canonical(positive))
    negatives = {}
    # Preserve every positive file. Fresh wrong-transition miters check that
    # the universal obligations themselves have counterexamples, independently
    # of the strict model-byte/fragment rejection in the production auditor.
    def negative(cell, original, kind):
        shape = copy.deepcopy(original)
        destination = run / 'negative-proofs' / cell / kind
        if kind == 'write_enable':
            shape['model_fragment']['write']['enable'] = '!WE'
            failing = 'word_step'
        elif kind == 'write_address':
            shape['model_fragment']['write']['address'] = "(WA ^ 1'b1)"
            failing = 'word_step'
        else:
            shape['model_fragment']['reads'][0]['address'] = "(RA0 ^ 1'b1)"
            failing = 'read_0'
        (run / 'negative-proofs' / cell).mkdir(parents=True, exist_ok=True)
        prove(cell, shape, destination)
        log = (destination / 'jasper.log').read_text()
        properties = dict((p, status) for p, _, status in
                          re.findall(r'^PROPERTY\t([^\t\n]+)\t([^\t\n]+)\t([^\t\n]+)$',
                                     (destination / 'memory-results.tsv').read_text(), re.M))
        prop = '<embedded>::production_memory_miter.' + failing
        require(properties.get(prop) == 'cex' and
                re.search(r'A counterexample \(cex\).*property "production_memory_miter\.' + failing + '"', log) and
                'BLACK-BOX' not in log.upper() and 'ERROR' not in log,
                'wrong memory transition/read did not produce a real counterexample')
        return cell + '/' + kind, dict(status='cex', property=prop, directory=str(destination))

    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(negative, cell, shape, kind) for cell, shape in binding['shapes'].items()
                for kind in ('write_enable', 'write_address', 'read_address')]
        for job in jobs:
            name, result = job.result()
            negatives[name] = result
    require(audit(architecture, run) == positive, 'negative runs changed positive proofs')
    summary = dict(status='passed', run=str(run), architecture=str(architecture),
                   proof_scope=positive['proof_scope'], memory_instances=201,
                   memory_bits=binding['memory_bits'], memory_words=binding['memory_words'],
                   shape_proofs=17, assertions=sum(s['assertions'] for s in positive['shapes'].values()),
                   covers=sum(s['covers'] for s in positive['shapes'].values()),
                   fresh_negative_proofs=negatives, formal_state_map_complete=False, gate_restore_authorized=False)
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--architecture', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.architecture, args.out)
    print(json.dumps({k: v for k, v in result.items() if k != 'fresh_negative_proofs'}, indent=2))


if __name__ == '__main__':
    main()
