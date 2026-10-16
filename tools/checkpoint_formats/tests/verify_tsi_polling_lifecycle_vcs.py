"""Atomic polling/direct-exit/provider preparation, native ASan/UBSan and VCS.

Fourteen host owners only; neither CPU checkpoint level is admitted.
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
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.fesvr_overlay import overlay_inputs, BUILDER
from tools.checkpoint_formats.tests.verify_tsi_htif_lifecycle_vcs import PROVIDER, image as lifecycle
from tools.checkpoint_formats.tests import verify_tsi_polling_prepare_vcs as polling
from tools.checkpoint_formats.tests import verify_tsi_htif_exit_vcs as exiting

NAMES = (*polling.NAMES, 'exit', 'lifecycle')
BACKENDS = ('native', 'vcs-dpi')
GUARDS = ('pending', 'delivered', 'mask', 'handler', 'occupied-exit', 'occupied-stop')


def exit_scenario(raw):
    """Independent original serial mailbox plan and all fourteen owner bytes."""
    packets = [[(0, exiting.TOHOST, 0)], [(1, exiting.TOHOST, 0), (0, exiting.FROMHOST, 0)],
               [(0, exiting.TOHOST, 0)], [(1, exiting.TOHOST, 0), (0, exiting.FROMHOST, 0)],
               [(1, exiting.FROMHOST, exiting.RESPONSE)]]
    plan = []
    for index, group in enumerate(packets):
        for command, address, value in group:
            packet = [command, address, 0, 1, 0, *([value & 0xffffffff, value >> 32] if command else [])]
            plan += ['PACKET '+' '.join(map(str, packet[:2])), 'PACKET '+' '.join(map(str, packet[2:]))]
        if index < 4:
            reply = (exiting.BCD, 7, raw, 0)[index]
            plan += ['SEND '+str(reply & 0xffffffff), 'TICK', 'SEND '+str(reply >> 32), 'TICK']
    _, cuts = exiting.oracle(raw, 0)
    require(len(plan)+1 == len(cuts), 'exit oracle/plan length differs')
    states = []
    for _, done, _, old in cuts:
        if done:
            states.append(None)  # stopped parent is explicitly unsupported
            continue
        phase = old['exit'][56]
        states.append(dict(old, program=config(23, 1, 0)+words(3),
                           init=config(21, 0, 0)+words(8, 0, 0), host=config(18, 3)+words(0, 0, 6),
                           **{'loadmem-read': config(14, 4096, 4)+words(0, 0, 0, 0),
                              'loadmem-queues': config(16, 4096, 4)+words(0, 0, 0, 0, 0, 0, 0)},
                           bcd=config(26, 1, 1048576)+words(0),
                           identity=polling.identity_image(polling.writer()), write=polling.writer(),
                           lifecycle=lifecycle(int(phase != 0), raw & 0xffffffff if phase else 0)))
    return plan, states


def scenarios():
    plan, images = polling.scenario(True)
    result = {'polling': (plan, [dict(b, exit=exiting.exit_image(), lifecycle=lifecycle()) for b in images], polling.INPUT)}
    result.update({f'exit-{raw}': (*exit_scenario(raw), b'A') for raw in exiting.PAYLOADS})
    return result


def completed_exit(raw, cut=-1):
    """Original packet/exit oracle, independent of restored caller methods."""
    _, states = exit_scenario(raw)
    protocol = next(s for s in reversed(states) if s is not None)
    _, direct = exiting.oracle(raw, 0)
    return dict(protocol, **direct[cut][3], lifecycle=lifecycle(1, raw & 0xffffffff, 1))


def audit(path):
    path = path.resolve(); out = path.parent; r = json.loads(path.read_text())
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong aggregate scope')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'changed aggregate artifact membership')
    for name, digest in r['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed aggregate artifact '+name)
    bindings = {b['path']: b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed aggregate source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    overlay = json.loads((out/'libfesvr-checkpoint.json').read_text())
    require(overlay['status'] == 'passed' and overlay['output_sha256'] == file_sha(out/'libfesvr-checkpoint.a') and
            {m for m,v in overlay['members'].items() if v['installed'] != v['overlay']} == {'elfloader.o','context.o','htif.o'},
            'aggregate provider archive mismatch')
    for name, digest in overlay['lifecycle_inputs'].items():
        if not name.endswith('_sha256'):
            require(bindings[name]['sha256'] == digest, 'unbound aggregate provider input')
    cases = scenarios()
    captures = readbacks = operations = requested = 0
    for name, (plan, images, terminal) in cases.items():
        require((out/(name+'.plan')).read_text() == '\n'.join(plan)+'\n' and
                (out/(name+'.input')).read_bytes() == terminal, 'changed aggregate workload')
        for producer in BACKENDS:
            dest = out/(producer+'-capture-'+name)
            for cut, expected in enumerate(images):
                if expected is None:
                    require((dest/f'cut-{cut}.stopped').read_text() == 'rejected\n', 'stopped aggregate admitted')
                else:
                    for owner in NAMES:
                        require((dest/f'cut-{cut}.{owner}').read_bytes() == expected[owner],
                                f'aggregate source differs {name}/{cut}/{owner}')
                    captures += 1
    expected_pairs = {(n,p,b,c) for n,(_,images,_) in cases.items() for p in BACKENDS for b in BACKENDS
                      for c,image in enumerate(images) if image is not None}
    require(len(r['restores']) == len(expected_pairs) and
            {(c['scenario'],c['producer'],c['backend'],c['cut']) for c in r['restores']} == expected_pairs,
            'incomplete aggregate cut/backend pairs')
    for case in r['restores']:
        name, cut = case['scenario'], case['cut']; dest = Path(case['destination'])
        plan, images, _ = cases[name]; expected = images[cut]
        for owner in NAMES:
            require((dest/('preedge.'+owner)).read_bytes() == expected[owner], 'incomplete aggregate pre-service readback')
        has_exit = expected['exit'][56] == 1
        require(f'AGGREGATE_READBACK owners=14 requested_exit={int(has_exit)} target_edges=0 target_services=0 context_entries=0'
                in Path(case['log']).read_text(), 'missing zero-edge aggregate readback')
        readbacks += 14
        requested += int(has_exit)
        if name == 'polling':
            require((dest/'continuation.bin').read_bytes() ==
                    b''.join(image[n] for image in images[cut+1:] for n in NAMES), 'aggregate continuation incomplete')
            count = len(plan)-cut
            require(f'AGGREGATE_CONTINUATION operations={count} owners=14 target_edges=0 context_entries=0' in
                    Path(case['log']).read_text(), 'missing aggregate continuation completion')
            operations += count; readbacks += 14*count
    expected_guards = {(p,b,g) for p in BACKENDS for b in BACKENDS for g in GUARDS}
    require(len(r['guards']) == len(expected_guards) and
            {(c['producer'],c['backend'],c['guard']) for c in r['guards']} == expected_guards, 'incomplete aggregate final guards')
    for c in r['guards']:
        dest = Path(c['destination'])
        for n in ('program','init','host','read','serial','loadmem-read','loadmem-queues','terminal','identity','write'):
            require((dest/('before.'+n)).read_bytes() == (dest/('after.'+n)).read_bytes(), 'late provider guard published '+n)
        require(f"AGGREGATE_LATE_GUARD {c['guard']} rejected=1 peers_unchanged=1 context_entries=0 target_edges=0" in
                Path(c['log']).read_text(), 'missing late provider rejection')
    require(len(r['atomic']) == 4, 'incomplete aggregate atomic backend pairs')
    allocations = invalids = 0
    for c in r['atomic']:
        match = re.search(r'AGGREGATE_ATOMIC malformed_membership_cross=(\d+) late_peers=3 prepare_allocations=(\d+) '
                          r'commit_allocations=(\d+) abandoned=1 consumed_competing=2 owners=14 target_edges=0 context_entries=0',
                          Path(c['log']).read_text())
        require(match and int(match[1]) > 1000 and int(match[2]) > 30 and int(match[3]) > 0, 'incomplete aggregate atomic tests')
        invalids += int(match[1]); allocations += int(match[2])+int(match[3])
        for n in NAMES:
            require((Path(c['destination'])/('preedge.'+n)).read_bytes() == cases['polling'][1][-1][n], 'atomic aggregate lost owner')
    exit_operations = exit_readbacks = 0
    if r.get('pending_exit_revision') == 1:
        required = {(n,p,b,c) for n,(_,images,_) in cases.items() for p in BACKENDS for b in BACKENDS
                    for c,image in enumerate(images) if image is not None and image['exit'][56] == 1}
        require(len(r['pending_exit']) == len(required) and
                {(c['scenario'],c['producer'],c['backend'],c['cut']) for c in r['pending_exit']} == required,
                'incomplete pending exit cut/backend matrix')
        for c in r['pending_exit']:
            name, cut = c['scenario'], c['cut']; raw = int(name.removeprefix('exit-'))
            plan, images, _ = cases[name]; final = completed_exit(raw); dest = Path(c['destination'])
            for owner in NAMES:
                require((dest/('preedge.'+owner)).read_bytes() == images[cut][owner] and
                        (dest/('final.'+owner)).read_bytes() == final[owner] and
                        (out/(c['producer']+'-capture-'+name)/('completed.'+owner)).read_bytes() == final[owner],
                        'incomplete pending exit initial/final/source owner '+owner)
            wanted = b''.join((image or completed_exit(raw,index))[n]
                              for index,image in enumerate(images) if index > cut for n in NAMES)
            for index,image in enumerate(images):
                if image is None:
                    expected = completed_exit(raw,index)
                    for n in NAMES:
                        require((out/(c['producer']+'-capture-'+name)/f'cut-{index}.completed.{n}').read_bytes() == expected[n],
                                'incomplete uninterrupted stopped caller cut')
            require((dest/'continuation.bin').read_bytes() == wanted, 'pending exit continuation bytes differ')
            count = len(plan)-cut
            require(f'EXIT_CONTINUATION operations={count} owners=14 stopped=1 code={exiting.status(raw)} '
                    'startup_replays=0 reentry_guards=3 target_edges=0 context_entries=0' in Path(c['log']).read_text(),
                    'pending exit completion/status missing')
            exit_operations += count; exit_readbacks += 14*(count+2)
        require(len(r['exit_faults']) == len(exiting.PAYLOADS)*4 and
                {(c['scenario'],c['producer'],c['backend']) for c in r['exit_faults']} ==
                {(f'exit-{raw}',p,b) for raw in exiting.PAYLOADS for p in BACKENDS for b in BACKENDS},
                'incomplete pending exit faults')
        for c in r['exit_faults']:
            plan, images, _ = cases[c['scenario']]
            require(c['cut'] == next(i for i,s in enumerate(images) if s is not None and s['exit'][56] == 1),
                    'wrong original pending exit fault cut')
            require(f'EXIT_FIRST_DIVERGENCE operation={len(plan)} request_word=3 expected=321 actual=320 '
                    'acknowledged=0 context_entries=0' in Path(c['log']).read_text(), 'missing actual exit response first divergence')
            for n in NAMES:
                require((Path(c['destination'])/('preedge.'+n)).read_bytes() == images[c['cut']][n], 'fault before complete readback')
        expected_service_guards = {(p,b,g) for p in BACKENDS for b in BACKENDS for g in GUARDS}
        require(len(r['exit_service_guards']) == len(expected_service_guards) and
                {(c['producer'],c['backend'],c['guard']) for c in r['exit_service_guards']} == expected_service_guards,
                'incomplete exit service guards')
        for c in r['exit_service_guards']:
            require('EXIT_SERVICE_GUARD '+c['guard']+' rejected=1 peers_unchanged=1 acknowledged=0 '
                    'context_entries=0 target_edges=0' in Path(c['log']).read_text(), 'unguarded pending exit service')
    pids = []
    for command in r['commands']:
        log = Path(command['log']).read_text()
        require(log.rstrip().endswith('exit='+str(command['returncode'])), 'aggregate native command failed')
        require(not any(s in log for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')), 'aggregate sanitizer diagnostic')
        pids.append(int(re.search(r'fresh_process_pid=(\d+)', log)[1]))
    require(len(pids) == len(set(pids)), 'aggregate process reused')
    return dict(status='passed', captured_host_cuts=captures, fresh_fourteen_owner_readbacks=len(r['restores']),
                requested_exit_readbacks=requested, continued_host_operations=operations, complete_owner_readbacks=readbacks,
                invalid_image_rejections=invalids, allocation_failures=allocations, late_provider_guards=len(r['guards']),
                pending_exit_continuations=len(r.get('pending_exit', [])), pending_exit_operations=exit_operations,
                pending_exit_owner_readbacks=exit_readbacks, exit_first_divergences=len(r.get('exit_faults', [])),
                exit_service_guards=len(r.get('exit_service_guards', [])), level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--pending-exit', action='store_true', help='also continue every requested exit to provider stop')
    args = parser.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit), indent=2)); return
    require(args.out and args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-',dir=args.out.resolve()))
    source, sv = TESTS/'tsi_polling_lifecycle_fesvr.cc', TESTS/'tsi_polling_prepare_fesvr_tb.sv'
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc',
               TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc', TESTS/'tsi_terminal_allocations.cc']
    inputs = [*sources, sv, Path(__file__), TESTS/'tsi_polling_prepare_fesvr.cc', TESTS/'verify_tsi_polling_prepare_vcs.py',
              TESTS/'verify_tsi_htif_exit_vcs.py', TESTS/'verify_tsi_htif_lifecycle_vcs.py',
              TESTS/'verify_tsi_memif_read_vcs.py', TESTS/'verify_tsi_host_control_fesvr_vcs.py',
              TESTS/'verify_tsi_memif_identity_fesvr_vcs.py', TESTS/'verify_tsi_memif_write_vcs.py',
              TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py', TESTS/'verify_firesim_tsi_loadmem_vcs.py',
              FESVR/'lib/libfesvr.a', *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')), *overlay_inputs(),
              PROVIDER, PROVIDER.with_suffix('.h'), STUBS/'fesvr/htif_lifecycle_provider.inc',
              *sorted((FESVR/'include/fesvr').glob('*.h')), *sorted((FESVR/'include/riscv').glob('*.h')),
              CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h', ROOT/'tools/checkpoint_formats/retained_evidence.py',
              ROOT/'tools/checkpoint_formats/evidence.py',ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    (out/'sources').mkdir(); bindings, commands = [], []
    for p in dict.fromkeys(inputs):
        digest = file_sha(p); saved = out/'sources'/digest
        if not saved.exists(): shutil.copyfile(p, saved)
        bindings.append(dict(path=str(p), sha256=digest, snapshot=str(saved)))
    def execute(argv, log, expected=0):
        # Entry point requires the pinned environment. Children inherit it.
        argv = list(map(str, argv)); run(argv, log, cwd=out, expected=expected)
        command = dict(cwd=str(out.relative_to(ROOT)), argv=argv, log=str(log), returncode=expected)
        commands.append(command); return command
    library = out/'libfesvr-checkpoint.a'
    execute(['python3',BUILDER,'--library',FESVR/'lib/libfesvr.a','--include',FESVR/'include','--out',library,
             '--cxx',os.environ['CXX'],'--htif-source',PROVIDER],out/'provider-build.log')
    native, simv = out/'aggregate-native', out/'simv'
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    execute([os.environ['CXX'],*shlex.split(include),'-g','-no-pie','-fsanitize=address,undefined','-fno-omit-frame-pointer',
             *sources,library,'-lpthread','-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_polling_prepare_fesvr_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],'-Mdir='+str(out/'csrc'),'-CFLAGS',include+' -DTSI_AGGREGATE_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread','-o',simv,sv,*sources],out/'vcs-build.log')
    elf = out/'polling.elf'; elf.write_bytes(polling.polling_elf())
    cases = scenarios()
    for n,(plan,_,terminal) in cases.items():
        (out/(n+'.plan')).write_text('\n'.join(plan)+'\n'); (out/(n+'.input')).write_bytes(terminal)
    def invoke(backend, mode, name, scenario='polling', producer='native', cut=0, **extra):
        dest = out/name; source = out/(producer+'-capture-'+scenario)/f'cut-{cut}'
        metadata = source.parent/'startup.metadata'
        values = [mode,elf,out/(scenario+'.input'),metadata,source,out/(scenario+'.plan'),dest]
        argv = [native,*values] if backend == 'native' else [simv,'-no_save',*['+'+k+'='+str(v) for k,v in
                zip(('mode','elf','terminal','metadata','source','plan','destination'),values)]]
        return dict(execute(argv,out/(name+'.log')),backend=backend,producer=producer,cut=cut,scenario=scenario,
                    destination=str(dest),**extra)
    for n in cases:
        for b in BACKENDS: invoke(b,'capture',b+'-capture-'+n,n)
    jobs = [(b,'continue' if n=='polling' else 'restore',f'{p}-{b}-{n}-cut-{c}',n,p,c)
            for n,(_,images,_) in cases.items() for p in BACKENDS for b in BACKENDS for c,image in enumerate(images) if image is not None]
    with ThreadPoolExecutor(max_workers=8) as pool:
        restores = list(pool.map(lambda a:invoke(*a),jobs))
    atomic = [invoke(b,'atomic',p+'-'+b+'-atomic','polling',p,len(cases['polling'][1])-1) for p in BACKENDS for b in BACKENDS]
    guards = [invoke(b,'guard-'+g,p+'-'+b+'-guard-'+g,producer=p,guard=g) for p in BACKENDS for b in BACKENDS for g in GUARDS]
    pending_exit, exit_faults, service_guards = [], [], []
    if args.pending_exit:
        jobs = [(b,'continue-exit',f'{p}-{b}-{n}-exit-continue-{c}',n,p,c)
                for n,(_,images,_) in cases.items() for p in BACKENDS for b in BACKENDS
                for c,image in enumerate(images) if image is not None and image['exit'][56] == 1]
        with ThreadPoolExecutor(max_workers=8) as pool:
            pending_exit = list(pool.map(lambda a:invoke(*a),jobs))
        for raw in exiting.PAYLOADS:
            n = f'exit-{raw}'; images = cases[n][1]
            cut = next(i for i,s in enumerate(images) if s is not None and s['exit'][56] == 1)
            for p in BACKENDS:
                for b in BACKENDS:
                    exit_faults.append(invoke(b,'exit-response-fault',f'{p}-{b}-{n}-exit-fault',n,p,cut))
                    if raw == 1:
                        service_guards += [invoke(b,'exit-service-guard-'+g,f'{p}-{b}-exit-service-guard-'+g,n,p,cut,guard=g)
                                           for g in GUARDS]
    for b in bindings: require(file_sha(b['path']) == b['sha256'],'source changed during aggregate checks')
    report = dict(status='passed',scope='fourteen host components; complete HTIF/session/context/CPU pending',
                  source_inputs=bindings,commands=commands,restores=restores,atomic=atomic,guards=guards,
                  pending_exit_revision=int(args.pending_exit),pending_exit=pending_exit,exit_faults=exit_faults,
                  exit_service_guards=service_guards,
                  level1_verified=False,level2_verified=False,
                  artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(summary=str(path),**audit(path)),indent=2))


if __name__ == '__main__':
    main()
