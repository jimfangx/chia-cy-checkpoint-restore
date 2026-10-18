"""Audit original heartbeat native/VCS execution, full state and MMIO history."""
import argparse
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.audit_base_publication import ENVIRONMENT, FATAL
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT


def audit(path):
    # Import here: the execution module also snapshots this independent auditor.
    from tools.checkpoint_formats.tests.verify_heartbeat_checkpoint_vcs import configuration, oracle, audit_case
    path = path.resolve(); out = path.parent; report = json.loads(path.read_text())
    require(report['status'] == 'passed' and report['level1_verified'] is False and
            report['level2_verified'] is False, 'component cannot certify CPU acceptance')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path},
            'changed native artifact membership')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed original native artifact '+name)
    bindings = {b['path']: b for b in report['source_inputs']}
    require(len(bindings) == len(report['source_inputs']), 'duplicate source bindings')
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed original source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    headers = [b for p, b in bindings.items() if p.endswith('FireSim-generated.const.h')]
    require(len(headers) == 1, 'missing actual recipe clock binding')
    configs = [configuration(Path(headers[0]['snapshot']).read_text(), i) for i in range(3)]
    calls = 0; publication = []
    for backend in ('native-sanitized', 'vcs-dpi'):
        base = out / backend
        for scenario, config in enumerate(configs):
            case = base / ('scenario-'+str(scenario))
            audit_case(case, config, scenario)
            trace, _, _ = oracle(config, scenario)
            for cut in range(16):
                log = (case / ('restore-'+str(cut)+'.log')).read_text()
                require('PASS: heartbeat component continuation' in log, 'missing native continuation')
                if backend == 'vcs-dpi':
                    require('HEARTBEAT_READBACK edges=0' in log and
                            log.index('HEARTBEAT_READBACK edges=0') < log.index('PASS: heartbeat component continuation'),
                            'missing pre-edge VCS owner readback')
                suffix = trace[trace.index(f'OP {cut} C {100+7*cut}'):] if cut < 15 else []
                calls += sum(line.startswith(('W ', 'R ')) for line in suffix)
        require('PASS: heartbeat atomic payload/configuration/suspension checks ' in
                (base / 'scenario-0/negative-0.log').read_text(), 'missing preserved lifecycle regressions')
        for i in range(4):
            case = base / ('malformed-'+str(i)); log = (case / 'restore-7.log').read_text()
            require(not (case / 'restore-7.initial.owner').exists() and
                    (case / 'restore-7.trace').read_bytes() == b'' and 'HEARTBEAT_READBACK' not in log and
                    'PASS: heartbeat component continuation' not in log,
                    'invalid image published or advanced an edge')
        case = base / 'actual-poll-counter-fault'; log = (case / 'restore-1.log').read_text()
        bad = bytearray(oracle(configs[0], 0)[1][1]); bad[160] = 2
        require((case / 'restore-1.initial.owner').read_bytes() == bad and
                'FIRST_MISMATCH fixture_cycle=107 signal=heartbeat_poll op=1' in log and
                (case / 'restore-1.trace').read_text().splitlines() == ['OP 1 C 107', 'W 1108 1'] and
                'PASS: heartbeat component continuation' not in log,
                'real polling corruption missed its first divergent boundary')
        if report['prepared']:
            log = (base / 'publication-negative.log').read_text()
            match = re.search(r'HEARTBEAT_PUBLICATION_NEGATIVE rejections=(\d+) prepare_failures=(\d+) seal_failures=(\d+) unchanged=1', log)
            require(match is not None, 'missing prepared rejection matrix')
            rejected, prepare, seal = map(int, match.groups())
            require(rejected > 400 and prepare > 0 and seal > 0, 'incomplete rejection/allocation sweeps')
            if backend == 'vcs-dpi': require('HEARTBEAT_PUBLICATION_ZERO_TIME_PASS' in log, 'negative checks advanced time')
            publication.append(dict(backend=backend, rejections=rejected, prepare_failures=prepare, seal_failures=seal))
            for mode in FATAL:
                log = (base / ('fatal-'+mode) / 'run.log').read_text()
                require(f'HEARTBEAT_PUBLICATION_FATAL mode={mode} unchanged=1 mmio=0' in log and
                        log.rstrip().endswith('exit=86') and 'UNEXPECTED_RETURN' not in log,
                        'fatal misuse did not reject before mutation')
            log = (base / 'fatal-returned/run.log').read_text()
            require('HEARTBEAT_PUBLICATION_UNEXPECTED_RETURN mode=returned' in log and
                    log.rstrip().endswith('exit=88') and 'HEARTBEAT_PUBLICATION_FATAL' not in log,
                    'unexpected return converted into passing fatal test')
    commands = report['commands']; count = 2 + 2*(3*17+1+4+1+(8 if report['prepared'] else 0))
    require(len(commands) == count and len({c['pid'] for c in commands}) == count,
            'missing/reused native process')
    require(json.loads((out / 'commands.json').read_text()) == commands, 'changed original command records')
    for command in commands:
        log = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and
                log.splitlines()[:2] == ['cwd='+str(ROOT / command['cwd']), 'argv='+json.dumps(command['argv'])] and
                'fresh_process_pid='+str(command['pid']) in log and
                log.rstrip().endswith('exit='+str(command['expected_exit'])), 'unbound native argv/environment/result')
    return dict(status='passed', fresh_continuations=96, complete_pre_edge_readbacks=96,
                matched_mmio_calls=calls, malformed_fresh_processes=8, first_divergences=2,
                fatal_contract_cases=12 if report['prepared'] else 0, publication=publication,
                native_processes=count, CPU_level1_verified=False, CPU_level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('summary', type=Path)
    print(json.dumps(audit(parser.parse_args().summary), indent=2))


if __name__ == '__main__':
    main()
