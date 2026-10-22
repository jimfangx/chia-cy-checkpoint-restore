"""Independently audit original block-device bytes, MMIO and native commands."""
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
    from tools.checkpoint_formats.tests.verify_blockdev_checkpoint_vcs import configuration, oracle, transaction_audit, CONFIG_BYTES
    path = Path(path).resolve(); out = path.parent; report = json.loads(path.read_text())
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
    require(len(headers) == 1, 'missing actual recipe block-device binding')
    snapshots = oracle(configuration(Path(headers[0]['snapshot']).read_text()))
    calls = 0; publication = []
    for backend in ('native-sanitized', 'vcs-dpi'):
        case = out / backend
        trace = (case / 'reference.trace').read_text().splitlines()
        transaction_audit(trace)
        for cut, snapshot in enumerate(snapshots):
            require((case / f'cut-{cut}.owner').read_bytes() == snapshot and
                    (case / f'restore-{cut}.initial.owner').read_bytes() == snapshot and
                    (case / f'restore-{cut}.final.owner').read_bytes() == snapshots[-1],
                    'incomplete pre-edge/final block-device readback')
            suffix = trace[trace.index(f'OP {cut} C {100+7*cut}'):] if cut < 14 else []
            require((case / f'restore-{cut}.trace').read_text().splitlines() == suffix,
                    'changed continued MMIO words/order/timing')
            calls += sum(line.startswith(('W ', 'R ')) for line in suffix)
            log = (case / f'restore-{cut}.log').read_text()
            require(log.rstrip().endswith('exit=0'), 'missing native completion')
            if backend == 'vcs-dpi':
                require('PASS: blockdev component continuation' in log, 'missing VCS continuation')
                require('BLOCKDEV_READBACK edges=0' in log and
                        log.index('BLOCKDEV_READBACK edges=0') < log.index('PASS: blockdev component continuation'),
                        'missing pre-edge VCS owner readback')
        require('PASS: blockdev atomic payload/configuration/suspension checks ' in
                (case / 'negative-0.log').read_text(), 'missing legacy lifecycle regressions')
        for i in range(4):
            bad = case / ('malformed-'+str(i)); log = (bad / 'restore-5.log').read_text()
            require(not (bad / 'restore-5.initial.owner').exists() and
                    not (bad / 'restore-5.trace').exists() and 'BLOCKDEV_READBACK' not in log and
                    'PASS: blockdev component continuation' not in log,
                    'invalid image published or advanced an edge')
        fault = case / 'actual-tracker-fault'; log = (fault / 'restore-5.log').read_text()
        bad = bytearray(snapshots[5]); bad[CONFIG_BYTES+24+4*8+24] ^= 1
        lines = (fault / 'restore-5.trace').read_text().splitlines()
        require((fault / 'restore-5.initial.owner').read_bytes() == bad and
                'FIRST_MISMATCH fixture_cycle=142 signal=bdev_rresp_data_lower op=6' in log and
                lines[-1] == f'W 576 {0x76540001}' and not any(s.startswith('OP 7 ') for s in lines) and
                'PASS: blockdev component continuation' not in log,
                'actual tracker corruption missed its first divergent boundary')
        if report['prepared']:
            log = (case / 'publication-negative.log').read_text()
            match = re.search(r'BLOCKDEV_PUBLICATION_NEGATIVE rejections=(\d+) prepare_failures=(\d+) seal_failures=(\d+) libc_failures=2 unchanged=1', log)
            require(match is not None, 'missing prepared rejection matrix')
            rejected, prepare, seal = map(int, match.groups())
            require(rejected > 600 and prepare > 0 and seal > 0, 'incomplete rejection/allocation sweeps')
            if backend == 'vcs-dpi': require('BLOCKDEV_PUBLICATION_ZERO_TIME_PASS' in log, 'negative checks advanced time')
            publication.append(dict(backend=backend, rejections=rejected, prepare_failures=prepare, seal_failures=seal))
            for mode in FATAL:
                log = (case / ('fatal-'+mode) / 'run.log').read_text()
                require(f'BLOCKDEV_PUBLICATION_FATAL mode={mode} unchanged=1 mmio=0' in log and
                        log.rstrip().endswith('exit=86') and 'UNEXPECTED_RETURN' not in log,
                        'fatal misuse did not reject before mutation')
            log = (case / 'fatal-returned/run.log').read_text()
            require('BLOCKDEV_PUBLICATION_UNEXPECTED_RETURN mode=returned' in log and
                    log.rstrip().endswith('exit=88') and 'BLOCKDEV_PUBLICATION_FATAL' not in log,
                    'unexpected return converted into passing fatal test')
    commands = report['commands']; count = 2 + 2*(22+(8 if report['prepared'] else 0))
    require(len(commands) == count and len({c['pid'] for c in commands}) == count,
            'missing/reused native process')
    require(json.loads((out / 'commands.json').read_text()) == commands, 'changed original command records')
    for command in commands:
        log = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and
                log.splitlines()[:2] == ['cwd='+str(ROOT / command['cwd']), 'argv='+json.dumps(command['argv'])] and
                'fresh_process_pid='+str(command['pid']) in log and
                log.rstrip().endswith('exit='+str(command['expected_exit'])), 'unbound native argv/environment/result')
    return dict(status='passed', fresh_continuations=30, complete_pre_edge_readbacks=30,
                matched_mmio_calls=calls, malformed_fresh_processes=8, first_divergences=2,
                fatal_contract_cases=12 if report['prepared'] else 0, publication=publication,
                native_processes=count, CPU_level1_verified=False, CPU_level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('summary', type=Path)
    print(json.dumps(audit(parser.parse_args().summary), indent=2))


if __name__ == '__main__':
    main()
