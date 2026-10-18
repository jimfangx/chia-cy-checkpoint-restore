"""Independent byte/MMIO oracle and original-artifact audit for base publication."""
import argparse
import json
from pathlib import Path
import re
import shlex

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT
from tools.checkpoint_formats.tests.verify_simulation_checkpoint_vcs import oracle, trace

FATAL = ('expired', 'unsealed', 'consumed', 'stale', 'legacy', 'thread')
ENVIRONMENT = ('source '+shlex.quote(str(ROOT / 'env.sh'))+' && source '+
               shlex.quote(str(ROOT / 'sims/firesim/env.sh'))+' && source '+
               shlex.quote(str(ROOT / 'automations/checkpoint_loop/vcs-env.sh'))+' && ')


def audit(path):
    path = path.resolve(); out = path.parent; report = json.loads(path.read_text())
    require(report['status'] == 'passed' and report['CPU_level1_verified'] is False and
            report['CPU_level2_verified'] is False, 'component cannot certify CPU acceptance')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path},
            'changed native artifact membership')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed original native artifact '+name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    comparisons = calls = 0; publication = []
    for backend in ('native-sanitized', 'vcs-dpi'):
        base = out / backend
        for scenario in range(3):
            reference = base / str(scenario) / 'reference'
            require((reference / 'trace').read_text().splitlines() == trace(scenario), 'changed initial MMIO flow')
            for cut in range(1, 5):
                case = reference.parent / ('restore-'+str(cut))
                require((reference / ('cut-'+str(cut)+'.owner')).read_bytes() == oracle(cut) and
                        (case / 'initial.owner').read_bytes() == oracle(cut), 'incomplete base readback before first edge')
                wanted = trace(scenario, cut)
                require((case / 'trace').read_text().splitlines() == wanted, 'changed complete continuation or init replay')
                log = (case / 'run.log').read_text()
                require('RESTORED_BEFORE_FIRST_EDGE calls=0' in log and
                        'entered simulation flow' not in log and 'Commencing simulation.' not in log and
                        'FireSim fingerprint:' not in log and 'Target Cycles Emulated: 42' in log and
                        f'PASS: simulation base continuation result={7 if scenario == 1 else 1 if scenario == 2 else 0}' in log,
                        'missing zero-edge lifecycle readback/terminal result')
                if backend == 'vcs-dpi':
                    require(log.index('RESTORED_BEFORE_FIRST_EDGE') < log.index('FIXTURE_EDGE'), 'load followed edge')
                comparisons += 1; calls += len(wanted)
        require('PASS: simulation base rejections 1911' in (base / 'negative.log').read_text(), 'missing legacy lifecycle regressions')
        for i in range(4):
            case = base / ('malformed-'+str(i)); log = (case / 'run.log').read_text()
            require(not (case / 'initial.owner').exists() and not (case / 'trace').exists(), 'invalid restore partially published')
            if backend == 'vcs-dpi':
                require('REJECTED_BEFORE_FIRST_EDGE' in log and 'FIXTURE_EDGE' not in log, 'invalid image advanced edge')
        for cut in (3, 4):
            case = base / ('done-corruption-'+str(cut)); log = (case / 'run.log').read_text()
            bad = bytearray(oracle(cut)); bad[-24] ^= 1
            require((case / 'initial.owner').read_bytes() == bad, 'test did not actually corrupt restored semantic state')
            want = (f'FIRST_MISMATCH fixture_step={cut+1} expected=simulation_run_step actual=simulation_run_finalize acknowledged={cut}'
                    if cut == 3 else 'FIRST_MISMATCH fixture_step=5 expected=simulation_run_finalize actual=simulation_run_step acknowledged=4')
            require(want in log and (case / 'trace').read_bytes() == b'' and 'PASS: simulation base continuation' not in log,
                    'actual done-state corruption missed or acknowledged its first divergent boundary')
        if report['prepared']:
            log = (base / 'publication-negative.log').read_text()
            match = re.search(r'BASE_PUBLICATION_NEGATIVE rejections=(\d+) prepare_failures=(\d+) seal_failures=(\d+) unchanged=1 mmio=0', log)
            require(match is not None, 'missing prepared rejection matrix')
            rejected, prepare, seal = map(int, match.groups())
            require(rejected == 2*len(oracle(1))+80 and prepare > 0 and seal > 0, 'incomplete rejection/allocation sweeps')
            if backend == 'vcs-dpi': require('BASE_PUBLICATION_ZERO_TIME_PASS' in log, 'negative checks advanced VCS time')
            publication.append(dict(backend=backend, rejections=rejected, prepare_failures=prepare, seal_failures=seal))
            for mode in FATAL:
                log = (base / ('publication-'+mode+'.log')).read_text()
                require(f'BASE_PUBLICATION_FATAL mode={mode} unchanged=1 mmio=0' in log and
                        log.rstrip().endswith('exit=86') and 'ZERO_TIME_PASS' not in log,
                        'fatal contract did not reject before mutation')
            log = (base / 'publication-returned.log').read_text()
            require('BASE_PUBLICATION_UNEXPECTED_RETURN mode=returned' in log and
                    log.rstrip().endswith('exit=88') and 'BASE_PUBLICATION_FATAL mode=' not in log,
                    'unexpected return converted into passing fatal test')
    commands = report['commands']
    count = 2 + 2*(3*5 + 1 + 4 + 2 + (8 if report['prepared'] else 0))
    require(len(commands) == count and len({c['pid'] for c in commands}) == count, 'missing/reused native process')
    for command in commands:
        log = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(command['expected_exit'])), 'unbound native command/environment/result')
    return dict(status='passed', fresh_continuations=comparisons, complete_pre_edge_readbacks=comparisons,
                matched_mmio_calls=calls, malformed_fresh_processes=8, first_divergences=4,
                fatal_contract_cases=12 if report['prepared'] else 0, publication=publication,
                native_processes=count, CPU_level1_verified=False, CPU_level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('summary', type=Path); a = p.parse_args()
    print(json.dumps(audit(a.summary), indent=2))


if __name__ == '__main__':
    main()
