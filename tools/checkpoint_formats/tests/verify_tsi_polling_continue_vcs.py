"""Resume prepared sealed polling components without an HTIF coroutine.

These are host-operation boundaries, not complete CPU checkpoint continuations.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT
from tools.checkpoint_formats.tests import verify_tsi_polling_prepare_vcs as preparation

UNSUPPORTED = (1, 0x80001000, (1 << 56) | (255 << 48) | 0x80003000,
               (1 << 56) | (2 << 48), 2 << 56, 255 << 56)


def audit(path):
    path = path.resolve()
    report = json.loads(path.read_text())
    out = path.parent
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'],
            'wrong continuation acceptance scope')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path},
            'changed continuation artifact membership')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed continuation artifact '+name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed continuation source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    base = Path(report['preparation_summary'])
    prepared = preparation.audit(base)
    plan, images = preparation.scenario()
    expected_cases = {(p, b, c) for p in ('native', 'vcs-dpi') for b in ('native', 'vcs-dpi') for c in range(len(images))}
    require(len(report['continuations']) == len(expected_cases) and
            {(c['producer'], c['backend'], c['cut']) for c in report['continuations']} == expected_cases,
            'missing continuation backend/cut pairing')
    readbacks = operations = 0
    for case in report['continuations']:
        dest, cut = Path(case['destination']), case['cut']
        expected = b''.join(image[n] for image in images[cut+1:] for n in preparation.NAMES)
        require((dest/'continuation.bin').read_bytes() == expected, 'incomplete continuation state readback')
        for n in preparation.NAMES:
            require((dest/('preedge.'+n)).read_bytes() == images[cut][n], 'incomplete pre-service readback')
        require((dest/'preedge.metadata').read_bytes() == Path(case['metadata']).read_bytes(), 'changed startup metadata')
        count = len(plan)-cut
        require(f'CONTINUATION operations={count} complete_owner_readbacks={10*count} startup_replays=0 target_edges=0 context_entries=0'
                in Path(case['log']).read_text(), 'missing completed component continuation')
        operations += count
        readbacks += 10*(count+1)
    require(len(report['unsupported']) == 4*len(UNSUPPORTED), 'incomplete unowned service checks')
    for case in report['unsupported']:
        require(Path(case['plan']).read_text() == str(UNSUPPORTED[case['command_index']])+'\n', 'changed unowned command')
    require(len(report['exit_guards']) == 4, 'missing external exit guards')
    for case in report['unsupported']+report['exit_guards']:
        require('UNOWNED_REJECTED clear_packets=0 terminal_unchanged=1 reentry_guards=3 context_entries=0'
                in Path(case['log']).read_text(), 'unowned operation acknowledged')
    require(len(report['corruptions']) == 4, 'missing corruption backend pairing')
    for case in report['corruptions']:
        require('FIRST_DIVERGENCE operation=21 request_word=5 expected=321 actual=256 acknowledged=0 context_entries=0'
                in Path(case['log']).read_text(), 'wrong first divergent operation')
    pids = []
    for command in report['commands']:
        log = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit=0'), 'unbound continuation command/environment/result')
        require(not any(s in log for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')),
                'continuation sanitizer failure')
        pids.append(int(re.search(r'fresh_process_pid=(\d+)', log)[1]))
    require(len(pids) == len(set(pids)), 'reused continuation process')
    return dict(status='passed', fresh_component_continuations=len(expected_cases),
                host_operations=operations, complete_owner_readbacks=readbacks,
                unowned_command_rejections=len(report['unsupported']), external_exit_guards=4,
                first_divergence_cases=4, preparation=prepared, level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit), indent=2))
        return
    require(args.out and args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    commands = []

    def execute(argv, log):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        run(command, log, cwd=ROOT)
        return dict(cwd='.', argv=command, log=str(log), expected_exit=0)

    commands.append(execute(['python', '-m', preparation.__name__, '--out', out/'preparation'], out/'preparation.log'))
    bases = list((out/'preparation').glob('invocation-*/summary.json'))
    require(len(bases) == 1, 'ambiguous preparation invocation')
    base = bases[0].parent
    # Original preparation archived the production C++ sources and libraries.
    bindings = json.loads(bases[0].read_text())['source_inputs']
    snapshot = out/'continuation-source.py'
    shutil.copyfile(__file__, snapshot)
    bindings = bindings+[dict(path=str(Path(__file__).resolve()), sha256=file_sha(snapshot), snapshot=str(snapshot))]
    plan, images = preparation.scenario()

    def invoke(backend, mode, name, producer, cut=0, plan_path=None, **extra):
        dest = out/name
        source, metadata = base/(producer+f'-capture/cut-{cut}'), base/(producer+'-capture/startup.metadata')
        plan_path = plan_path or base/'plan.txt'
        argv = [base/'prepare-native', mode, base/'polling.elf', base/'terminal.bin', metadata, source, plan_path, dest] if backend == 'native' else [
            base/'simv', '-no_save', '+mode='+mode, '+elf='+str(base/'polling.elf'), '+terminal='+str(base/'terminal.bin'),
            '+metadata='+str(metadata), '+source='+str(source), '+plan='+str(plan_path), '+destination='+str(dest)]
        return dict(execute(argv, out/(name+'.log')), backend=backend, producer=producer, cut=cut,
                    source=str(source), metadata=str(metadata), destination=str(dest), plan=str(plan_path), **extra)

    jobs = [(b, 'continue', f'{p}-{b}-continue-{c}', p, c)
            for p in ('native', 'vcs-dpi') for b in ('native', 'vcs-dpi') for c in range(len(images))]
    with ThreadPoolExecutor(max_workers=4) as pool:
        continuations = list(pool.map(lambda j: invoke(*j), jobs))
    commands.extend(continuations)
    unsupported, exit_guards, corruptions = [], [], []
    for p in ('native', 'vcs-dpi'):
        for b in ('native', 'vcs-dpi'):
            for index, command in enumerate(UNSUPPORTED):
                plan_path = out/f'unowned-{index}.txt'
                if not plan_path.exists():
                    plan_path.write_text(str(command)+'\n')
                unsupported.append(invoke(b, 'unsupported', f'{p}-{b}-unowned-{index}', p,
                                          plan_path=plan_path, command_index=index))
            exit_guards.append(invoke(b, 'exit-guard', f'{p}-{b}-exit-guard', p))
            corruptions.append(invoke(b, 'corrupt', f'{p}-{b}-corrupt', p))
    commands.extend(unsupported+exit_guards+corruptions)
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'source changed during continuation checks')
    report = dict(status='passed', scope='sealed BCD polling components without coroutine; no CPU continuation',
                  preparation_summary=str(bases[0]), continuations=continuations, unsupported=unsupported,
                  exit_guards=exit_guards, corruptions=corruptions, commands=commands, source_inputs=bindings,
                  level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(summary=str(path), **audit(path)), indent=2))


if __name__ == '__main__':
    main()
