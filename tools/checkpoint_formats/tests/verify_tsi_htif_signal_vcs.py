"""Fresh actual HTIF signal/provider readback and delivery in native ASan/VCS.

Component evidence only; session/caller/thread/process/CPU admission is pending.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, FESVR
from tools.checkpoint_formats.tests.fesvr_overlay import overlay_inputs, BUILDER

PROVIDER = ROOT/'toolchains/riscv-tools/riscv-isa-sim/fesvr/htif.cc'
STATES = [(present, raw, stopped) for present, raw in
          [(0, 0), (1, 0), (1, 1), (1, 3), (1, 0x80000001), (1, 0xffffffff)] for stopped in (0, 1)]
KINDS = ('none', 'int', 'term')
BACKENDS = ('native', 'vcs-dpi')
GUARDS = [(g, int(s)) for g in ('pending', 'mask', 'handler', 'flags', 'handler-mask')
          for s in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT)]
GUARDS += [('delivered', int(s)) for s in (signal.SIGINT, signal.SIGTERM)]
GUARDS += [(g, int(signal.SIGTERM)) for g in ('occupied-exit', 'occupied-stop', 'signature')]


def image(present=0, raw=0, stopped=0, delivered=0):
    return config(33, 1, 32, 1)+words(present, raw, stopped, delivered)


def fields(present, raw, stopped, delivered):
    signed = raw if raw < 0x80000000 else raw-0x100000000
    return f'{present} {raw} {stopped} {delivered} {int(bool(present or delivered))} {stopped} {signed//2} 0\n'


def trace(present, raw, stopped, delivered):
    signed = raw if raw < 0x80000000 else raw-0x100000000
    exiting = int(bool(present or delivered))
    return f'0 {exiting} {stopped} {signed//2} 0\n1 {exiting} {int(bool(stopped or exiting))} {signed//2} 0\n'


def bad_images():
    good = image(1, 1, 0, 1)
    result = [good[:n] for n in range(len(good))]+[good+b'\0']
    for n in range(len(config(33, 1, 32, 1))):
        bad = bytearray(good); bad[n] ^= 1; result.append(bytes(bad))
    return result+[image(2, 1), image(0, 1), image(1, 0x100000000), image(1, 1, 2), image(1, 1, 0, 2)]


def tag(kind, state):
    return kind+'-'+'-'.join(map(str, state))


def expected_cases(out, thread_guards=False):
    cases = []
    for backend in BACKENDS:
        for kind in KINDS:
            for state in STATES:
                name = backend+'-capture-'+tag(kind, state)
                cases.append(dict(backend=backend, mode='capture', name=name, source='none',
                                  scenario=kind, detail=','.join(map(str, state)), expected=0))
        for producer in BACKENDS:
            for kind in KINDS:
                for state in STATES:
                    source = out/(producer+'-capture-'+tag(kind, state))/'captured.signal'
                    name = producer+'-'+backend+'-restore-'+tag(kind, state)
                    cases.append(dict(backend=backend, mode='restore', name=name, source=str(source),
                                      scenario=kind, detail=','.join(map(str, state)), expected=0))
        for n, _ in enumerate(bad_images()):
            cases.append(dict(backend=backend, mode='reject', name=f'{backend}-reject-{n}',
                              source=str(out/f'bad-{n}.signal'), scenario='none', detail='0', expected=0))
        source = str(out/'native-capture-int-1-3-0/captured.signal')
        for g, sig in GUARDS:
            cases.append(dict(backend=backend, mode='guard', name=f'{backend}-guard-{g}-{sig}',
                              source=source, scenario=g, detail=str(sig), expected=0))
        for kind in KINDS:
            for state in STATES:
                cases.append(dict(backend=backend, mode='publish', name=backend+'-publish-'+tag(kind, state),
                                  source=str(out/('native-capture-'+tag(kind, state))/'captured.signal'),
                                  scenario=kind, detail='0', expected=0))
        for kind in KINDS:
            cases.append(dict(backend=backend, mode='abandon', name=backend+'-abandon-'+kind,
                              source=str(out/('native-capture-'+kind+'-1-3-0')/'captured.signal'),
                              scenario=kind, detail='0', expected=0))
        for kind in ('none', 'int'):
            cases.append(dict(backend=backend, mode='second', name=backend+'-second-'+kind,
                              source=str(out/('native-capture-'+kind+'-0-0-0')/'captured.signal'),
                              scenario=kind, detail='0', expected=255 if kind == 'int' else 0))
        for fault in ('delivered', 'stopped', 'raw'):
            cases.append(dict(backend=backend, mode='corrupt', name=backend+'-corrupt-'+fault,
                              source=str(out/('native-capture-none-'+('1' if fault == 'raw' else '0')+'-0-0')/'captured.signal'),
                              scenario=fault, detail='0', expected=0))
        if thread_guards:
            for kind, sig in (('none', 0), ('int', signal.SIGINT), ('term', signal.SIGTERM)):
                cases.append(dict(backend=backend, mode='thread-capture', name=backend+'-thread-capture-'+kind,
                                  source='none', scenario=kind, detail=str(int(sig)), expected=0))
                for producer in BACKENDS:
                    cases.append(dict(backend=backend, mode='thread-restore',
                                      name=producer+'-'+backend+'-thread-restore-'+kind,
                                      source=str(out/(producer+'-thread-capture-'+kind)/'captured.signal'),
                                      scenario=kind, detail=str(int(sig)), expected=0))
            for guard in ('worker-mask', 'worker-pending', 'second-worker-pending', 'shared-pending'):
                for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
                    cases.append(dict(backend=backend, mode='thread-guard', name=f'{backend}-{guard}-{int(sig)}',
                                      source=str(out/'native-thread-capture-int/captured.signal'),
                                      scenario=guard, detail=str(int(sig)), expected=0))
    # Every producer exits before any restore/negative process starts.
    return sorted(cases, key=lambda c: c['mode'] not in ('capture', 'thread-capture'))


def audit(path):
    path = path.resolve(); out = path.parent; r = json.loads(path.read_text())
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong signal scope')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'signal artifact membership changed')
    for p, digest in r['artifact_sha256'].items(): require(file_sha(p) == digest, 'changed signal artifact '+p)
    bindings = {b['path']: b for b in r['source_inputs']}
    require(len(bindings) == len(r['source_inputs']), 'duplicate signal source binding')
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed signal source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    overlay = json.loads((out/'libfesvr-checkpoint.json').read_text())
    require(overlay['status'] == 'passed' and overlay['output_sha256'] == file_sha(out/'libfesvr-checkpoint.a'), 'wrong signal provider archive')
    for p, digest in overlay['lifecycle_inputs'].items():
        if not p.endswith('_sha256'): require(bindings[p]['sha256'] == digest, 'unbound signal provider input')
    original = Path(bindings[str(PROVIDER)]['snapshot']).read_bytes()
    extension = Path(bindings[str(STUBS/'fesvr/htif_lifecycle_provider.inc')]['snapshot']).read_bytes()
    require(hashlib.sha256(original+b'\n'+extension).hexdigest() == overlay['lifecycle_inputs']['generated_provider_sha256'], 'changed original HTIF methods')
    expected = expected_cases(out, r.get('thread_guards', False))
    require([c['case'] for c in r['cases']] == expected, 'missing/duplicate/reordered signal evidence')
    for record, case in zip(r['cases'], expected):
        log = Path(record['log']).read_text(); folder = out/case['name']; mode = case['mode']
        values = [mode, case['source'], str(folder), case['scenario'], case['detail']]
        argv = [str(out/'native'), *values] if case['backend'] == 'native' else [str(out/'simv'), '-no_save',
                *['+'+k+'='+v for k,v in zip(('mode','source','destination','scenario','detail'), values)]]
        require(record['argv'] == argv and record['returncode'] == case['expected'] and
                record['log'] == str(out/(case['name']+'.log')) and record['cwd'] == str(out.relative_to(ROOT)),
                'signal command does not bind actual case')
        require(log.rstrip().endswith('exit='+str(case['expected'])), 'unexecuted signal check')
        if case['expected'] == 255:
            require('SECOND_SIGNAL before=1' in log, 'actual handler did not exit on second signal')
        else:
            require(f'HTIF_SIGNAL mode={mode} scenario={case["scenario"]} target_services=0 target_edges=0' in log, 'missing real provider check')
        if mode in ('capture', 'restore', 'publish'):
            state = tuple(map(int, case['detail'].split(','))) if mode != 'publish' else None
            if mode == 'publish':
                state = tuple(map(int, case['name'].split('-')[-3:]))
            delivered = int(case['scenario'] != 'none'); wanted = image(*state, delivered)
            prefix = {'capture':'captured', 'restore':'readback', 'publish':'after'}[mode]
            require((folder/(prefix+'.signal')).read_bytes() == wanted, 'incomplete signal/lifecycle readback')
            require((folder/(prefix+'.fields')).read_text() == fields(*state, delivered), 'actual private/provider observations differ')
            if mode in ('capture', 'restore'):
                require((folder/'continuation.txt').read_text() == trace(*state, delivered), 'first HTIF boundary/stop differs')
            if mode == 'restore':
                require((folder/'continuation.txt').read_bytes() == Path(case['source']).with_name('continuation.txt').read_bytes(),
                        'fresh continuation differs from uninterrupted actual provider')
        if mode == 'reject': require((folder/'unchanged.signal').read_bytes() == image(), 'invalid image partially published')
        if mode in ('guard', 'abandon', 'publish'):
            require((folder/'transaction.txt').read_text() == f'callbacks={int(mode == "publish")} target_services=0\n', 'late guard published peer')
            require((folder/'after.serial').read_bytes() == (folder/('candidate.serial' if mode == 'publish' else 'before.serial')).read_bytes(), 'serial peer publication mismatch')
            if mode == 'abandon': require((folder/'after.signal').read_bytes() == image(), 'abandoned candidate changed provider')
        if mode == 'corrupt':
            signal_name = {'delivered':'should_exit', 'stopped':'stopped', 'raw':'exit_code'}[case['scenario']]
            require((folder/'first-divergence.txt').read_text() == f'FIRST_DIVERGENCE boundary=0 signal={signal_name} acknowledged=0 target_services=0\n', 'incorrect first divergence')
            corrupted = {'delivered':image(delivered=1), 'stopped':image(stopped=1), 'raw':image(1,4)}[case['scenario']]
            require((folder/'corrupted.signal').read_bytes() == corrupted, 'fault did not change actual semantic provider state')
        if mode in ('thread-capture', 'thread-restore'):
            prefix = 'captured' if mode == 'thread-capture' else 'readback'
            delivered = int(case['scenario'] != 'none')
            require((folder/(prefix+'.signal')).read_bytes() == image(1, 3, 0, delivered), 'incomplete threaded readback')
            require((folder/(prefix+'.fields')).read_text() == fields(1, 3, 0, delivered), 'threaded fields differ')
            require((folder/'continuation.txt').read_text() == trace(1, 3, 0, delivered), 'threaded first boundary differs')
            if mode == 'thread-restore':
                require((folder/'continuation.txt').read_bytes() == Path(case['source']).with_name('continuation.txt').read_bytes(),
                        'threaded fresh continuation differs')
        if mode == 'thread-guard':
            require((folder/'unchanged.signal').read_bytes() == image(), 'thread guard published provider')
            require((folder/'after.serial').read_bytes() == (folder/'before.serial').read_bytes(), 'thread guard published peer')
            require((folder/'retry.signal').read_bytes() == Path(case['source']).read_bytes() and
                    (folder/'retry.serial').read_bytes() != (folder/'before.serial').read_bytes(), 'thread retry did not publish')
            require((folder/'transaction.txt').read_text() == 'rejected_callbacks=0 retry_callbacks=1 target_services=0\n', 'thread guard callback mismatch')
            rejected = (folder/'rejections.txt').read_text().splitlines()
            require(len(rejected) == 3 and [v.split()[0] for v in rejected] == ['capture', 'prepare', 'commit'], 'missing thread API guard')
            if case['scenario'] != 'shared-pending':
                reason = 'unblocked' if case['scenario'] == 'worker-mask' else 'pending'
                require(all(reason+' HTIF signal in thread: ' in v for v in rejected), 'guard did not inspect actual worker')
    case_logs = {c['log'] for c in r['cases']}
    require(len(case_logs) == len(expected) and len({c['log'] for c in r['commands']}) == len(r['commands']), 'duplicate signal execution')
    require({c['log'] for c in r['commands']} == case_logs | {str(out/n) for n in
            (['native-build.log', 'vcs-build.log', 'bad-commit-copy.log', 'bad-commit-move.log', 'bad-commit-throwing.log'] +
             ([] if r['recipe_build_identity'] else ['overlay-build.log']))}, 'missing signal build execution')
    for command in r['commands']:
        require(Path(command['log']).read_text().rstrip().endswith('exit='+str(command['returncode'])), 'signal build/run did not finish')
    vcs = next(c for c in r['commands'] if c['log'] == str(out/'vcs-build.log'))['argv']
    require(vcs[0] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs' and '-full64' in vcs and
            vcs[vcs.index('-cc')+1] == '/usr/bin/gcc-13' and vcs[vcs.index('-cpp')+1] == '/usr/bin/g++-13',
            'wrong signal VCS/compiler configuration')
    return dict(status='passed', fresh_processes=len(expected),
                captures=sum(c['mode']=='capture' for c in expected),
                fresh_restores=sum(c['mode']=='restore' for c in expected),
                invalid_images=sum(c['mode']=='reject' for c in expected),
                late_guard_transactions=sum(c['mode']=='guard' for c in expected),
                atomic_publications=sum(c['mode']=='publish' for c in expected),
                actual_handler_second_signal_exits=sum(c['expected']==255 for c in expected),
                actual_first_boundary_faults=sum(c['mode']=='corrupt' for c in expected),
                thread_captures=sum(c['mode']=='thread-capture' for c in expected),
                thread_restores=sum(c['mode']=='thread-restore' for c in expected),
                thread_guard_transactions=sum(c['mode']=='thread-guard' for c in expected),
                level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path); p.add_argument('--audit', type=Path)
    p.add_argument('--recipe-build-identity', type=Path)
    p.add_argument('--thread-guards', action='store_true', help='Also audit all-thread signal exclusion with real parked pthreads')
    a = p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit), indent=2)); return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    a.out.resolve().mkdir(parents=True, exist_ok=True); out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    source, sv = [TESTS/n for n in ('tsi_htif_signal_fesvr.cc', 'tsi_htif_signal_fesvr_tb.sv')]
    inputs = [source, sv, Path(__file__), PROVIDER, PROVIDER.with_suffix('.h'),
              STUBS/'fesvr/htif_lifecycle_provider.inc', *sorted((STUBS/'fesvr').glob('*.h')),
              *overlay_inputs(), *sorted((FESVR/'include/fesvr').glob('*.h')),
              FESVR/'lib/libfesvr.a', CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h',
              ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh']
    production = None
    if a.recipe_build_identity:
        identity = json.loads(a.recipe_build_identity.read_text())
        require(identity.get('htif_lifecycle_provider_linked') is True, 'recipe provider not linked')
        for name, digest in identity['sources_sha256'].items(): require(file_sha(name) == digest, 'changed recipe input '+name)
        production = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
        inputs += [a.recipe_build_identity.resolve(), production, production.with_suffix('.json')]
    snapshots = out/'sources'; snapshots.mkdir(); bindings = []
    for path in dict.fromkeys(inputs):
        digest = file_sha(path); snapshot = snapshots/digest
        if not snapshot.exists(): shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    commands = []
    def execute(argv, log, expected=0):
        argv = list(map(str, argv)); run(argv, log, cwd=out, expected=expected)
        record = dict(cwd=str(out.relative_to(ROOT)), argv=argv, log=str(log), returncode=expected)
        commands.append(record); return record
    library = out/'libfesvr-checkpoint.a'
    if production:
        shutil.copyfile(production, library); shutil.copyfile(production.with_suffix('.json'), library.with_suffix('.json'))
    else:
        execute(['python3', BUILDER, '--library', FESVR/'lib/libfesvr.a', '--include', FESVR/'include',
                 '--out', library, '--cxx', os.environ['CXX'], '--htif-source', PROVIDER], out/'overlay-build.log')
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{FESVR/"include"}'
    native, simv = out/'native', out/'simv'
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
             source, library, '-lpthread', '-o', native], out/'native-build.log')
    for name, statement in {'copy':'auto copy = next;', 'move':'auto moved = std::move(next);',
                            'throwing':'auto publish = []() {}; next.commit(publish);'}.items():
        bad = out/f'bad-commit-{name}.cc'
        bad.write_text('#include "fesvr/tsi_htif_signal.h"\n'
                       'void check(firesim_tsi_htif_signal_t &o, const std::vector<uint8_t> &i) {\n'
                       'auto next = o.prepare_checkpoint(i); '+statement+'\n}\n')
        execute([os.environ['CXX'], *shlex.split(include), '-fsyntax-only', bad], out/f'bad-commit-{name}.log', expected=1)
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps', '-top', 'tsi_htif_signal_fesvr_tb',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_HTIF_SIGNAL_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread', '-o', simv, sv, source], out/'vcs-build.log')
    for n, bad in enumerate(bad_images()): (out/f'bad-{n}.signal').write_bytes(bad)
    def invoke(case):
        values = list(map(str, (case['mode'], case['source'], out/case['name'], case['scenario'], case['detail'])))
        argv = [native, *values] if case['backend'] == 'native' else [simv, '-no_save',
                *['+'+k+'='+v for k,v in zip(('mode','source','destination','scenario','detail'), values)]]
        return dict(execute(argv, out/(case['name']+'.log'), case['expected']), case=case)
    cases = expected_cases(out, a.thread_guards); results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for producer in (True, False):
            results += list(pool.map(invoke, [c for c in cases if (c['mode'] in ('capture', 'thread-capture')) == producer]))
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'signal source changed during execution')
    report = dict(status='passed', scope='actual signal/lifecycle provider component; whole process/CPU pending',
                  source_inputs=bindings, commands=commands, cases=results, level1_verified=False, level2_verified=False,
                  recipe_build_identity=str(a.recipe_build_identity.resolve()) if a.recipe_build_identity else None,
                  thread_guards=a.thread_guards,
                  artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    try: result = audit(path)
    except Exception:
        report['status'] = 'failed'; path.write_text(json.dumps(report, indent=2)+'\n'); raise
    print(json.dumps(dict(summary=str(path), **result), indent=2))


if __name__ == '__main__': main()
