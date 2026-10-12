"""Prove the complete actual production flattened register candidates."""

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
from tools.checkpoint_formats.production_register import audit, proof_inputs, reconstruct, relation_catalog, validate
from tools.checkpoint_formats.production_queue import instances
from tools.checkpoint_formats.replay import modules
from .verify_formal_state_map import JASPER, ROOT


def negative_binding(binding, kind):
    value = copy.deepcopy(binding)
    index = next(i for i, g in enumerate(value['groups']) if g['entry']['original_path'] == 'fuzzer.num_reqs')
    group = value['groups'][index]
    prop = f'state_{index}_step'
    if kind == 'polarity':
        group['bits'][0]['xor'] ^= 1
    elif kind == 'missing_register':
        group['bits'].pop(0)
    elif kind == 'opcode_predicate':
        require(value.get('optimized_predicates'), 'negative requires opcode predicate profile')
        value['optimized_predicates'][0]['value'] ^= 1
        prop = 'predicate_0_step'
    else:
        require(kind in ('changed_data', 'read_address'), 'unsupported register negative')
        source = value['implementation_source']
        if kind == 'changed_data':
            components = group['bits'][0]['gate_components']
            require(len(components) == 1, 'negative requires flattened top register')
            module, instance, port = value['top'], components[0], 'D'
        else:
            mi = next(i for i, m in enumerate(value['memories']) if len(m['gate_components']) == 2 and
                      m['entry']['depth'] > 1)
            mem = value['memories'][mi]
            module = mem['entry']['module']
            instance, port = mem['gate_components'][-1], 'RA0'
            prop = f'port_ckregister_memory_{mi}_{port}'
        header, body = modules(source)[module]
        child = instances(body)[instance]
        connection = child['ports'][port]
        before = body[child['start']:child['end']]
        after, count = re.subn(r'\.' + port + r'\s*\(\s*' + re.escape(connection) + r'\s*\)',
                               lambda _: f'.{port}(~{connection})', before)
        require(count == 1, 'ambiguous actual register/memory port mutation')
        changed = body[:child['start']] + after + body[child['end']:]
        # Several emitted queue modules have byte-identical bodies. Identify
        # the selected declaration, never replace every matching body.
        declarations = list(re.finditer(r'\bmodule\s+' + re.escape(module) + r'\s*\([^;]*\);(.*?)endmodule\b', source, re.S))
        require(len(declarations) == 1 and declarations[0][1] == body, 'ambiguous actual module mutation')
        declaration = declarations[0]
        value['implementation_source'] = source[:declaration.start(1)] + changed + source[declaration.end(1):]
    return value, '<embedded>::production_register_miter.' + prop


def verify(architecture, synthesis_evidence, out, positive_proof=None, opcode_predicate=False, reuse_negative_run=None):
    architecture, synthesis_evidence, out = (Path(p).resolve() for p in (architecture, synthesis_evidence, out))
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    binding = reconstruct(architecture, synthesis_evidence, opcode_predicate)
    require(binding['semantic_state_entries'] == 1543 and binding['physical_register_bits'] == 7256 and
            binding['semantic_register_bits'] == 8261 and len(binding['memories']) == 201 and
            sum(len(e['bits']) for e in binding['pending_registers']) == 1005,
            'verification requires the complete selected actual production DUT')
    env = dict(os.environ)
    env.pop('LD_LIBRARY_PATH', None)
    commands, lock = [], threading.Lock()

    def prove(value, destination):
        destination.mkdir(parents=True, exist_ok=False)
        artifacts = proof_inputs(value)
        for role, filename in (('binding', 'binding.json'), ('miter', 'miter.sv'), ('script', 'prove.tcl')):
            (destination / filename).write_bytes(artifacts[role])
        tool_env = dict(env, CHECKPOINT_REGISTER_BINDING=str(destination / 'binding.json'),
                        CHECKPOINT_REGISTER_MITER=str(destination / 'miter.sv'),
                        CHECKPOINT_REGISTER_SCRIPT=str(destination / 'prove.tcl'))
        argv = [JASPER, '-allow_unsupported_OS', '-batch', '-tcl', str(destination / 'prove.tcl')]
        command = dict(cwd=str(destination.relative_to(ROOT)), argv=argv, log=str(destination / 'jasper.log'))
        with lock:
            commands.append(command)
            (run / 'commands.json').write_bytes(canonical(commands))
        with (destination / 'jasper.log').open('w') as stream:
            process = subprocess.run(argv, cwd=destination, env=tool_env, stdout=stream, stderr=subprocess.STDOUT,
                                     timeout=7200)
        with lock:
            command['exit_code'] = process.returncode
            (run / 'commands.json').write_bytes(canonical(commands))
        require(process.returncode == 0, 'Jasper failed: ' + command['log'])
        return destination

    proof = Path(positive_proof).resolve() if positive_proof else prove(binding, run / 'positive')
    result = audit(architecture, synthesis_evidence, proof, opcode_predicate)
    (run / 'positive-audit.json').write_bytes(canonical(result))
    (run / 'register-relations.json').write_bytes(canonical(relation_catalog(binding, proof)))

    def negative(kind):
        value, prop = negative_binding(binding, kind)
        retained = Path(reuse_negative_run).resolve() / 'negative' / kind if reuse_negative_run else None
        directory = retained if retained and retained.exists() else prove(value, run / 'negative' / kind)
        report = validate(value, directory, negative=True)
        status = 'cex'
        if prop not in report['counterexamples']:
            # An impossible proposed constant can make the entire relation
            # vacuous. Preserve its native unreachable precondition and verify
            # that the ordinary positive auditor rejects it explicitly.
            require(kind == 'opcode_predicate' and prop + ':precondition1' in report['failed_nonvacuity_covers'],
                    'false register candidate produced neither counterexample nor proven nonvacuity failure')
            try:
                validate(value, directory)
            except FormatError as error:
                require('incomplete/vacuous register obligation' in str(error), 'negative rejected for unrelated reason')
            else:
                raise AssertionError('Vacuous optimized predicate accepted')
            status = 'rejected_nonvacuity'
        return kind, dict(property=prop, proof=str(directory), audit=report, status=status)

    negatives = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        kinds = ['polarity', 'missing_register', 'changed_data', 'read_address']
        if opcode_predicate:
            kinds.append('opcode_predicate')
        jobs = [pool.submit(negative, kind) for kind in kinds]
        for job in jobs:
            kind, report = job.result()
            negatives[kind] = report
    require(audit(architecture, synthesis_evidence, proof, opcode_predicate) == result, 'negative jobs changed positive proof bytes')
    summary = dict(status='in_progress', run=str(run), proof=str(proof), positive=result, negative=negatives,
                   formal_state_map_complete=False, gate_restore_authorized=False, external_dependency_missing=None)
    if opcode_predicate:
        summary['opcode_predicate'] = True
    (run / 'summary.json').write_bytes(canonical(summary))
    (out / 'selection.json').write_bytes(canonical(dict(run=str(run), proof=str(proof), summary=str(run / 'summary.json'))))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('architecture', 'synthesis-evidence', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--positive-proof', type=Path)
    parser.add_argument('--opcode-predicate', action='store_true')
    parser.add_argument('--reuse-negative-run', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.architecture, args.synthesis_evidence, args.out, args.positive_proof,
                            args.opcode_predicate, args.reuse_negative_run), indent=2))


if __name__ == '__main__':
    main()
