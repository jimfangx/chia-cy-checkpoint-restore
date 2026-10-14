"""Fresh native/VCS continuations of the production TSI loadmem read owner.

An independent original-loop oracle audits complete owner/queue readback and
every continuation. These component cuts do not establish CPU acceptance.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

TESTS = Path(__file__).resolve().parent
CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
STUBS = ROOT / 'generators/firechip/bridgestubs/src/main/cc'
ENVIRONMENT = ('source ' + shlex.quote(str(ROOT / 'env.sh')) + ' && source ' +
               shlex.quote(str(ROOT / 'sims/firesim/env.sh')) + ' && source ' +
               shlex.quote(str(ROOT / 'automations/checkpoint_loop/vcs-env.sh')) + ' && ')
SIZES = (4, 8, 64, 128, 1024, 4096)
ADDRESS = 0x123456780


def words(*values):
    return struct.pack('<' + 'Q' * len(values), *values)


def config(kind, *values):
    return words(0x3154504b43474457, 1, kind, len(values), *values)


def response(index):
    return 0 if index % 3 == 0 else (0xf0000000 + index * 0x10203) & 0xffffffff


def oracle(size):
    """Original drain/enqueue/pop loop, with the independently scheduled IO.

    All explicit call cuts are expanded without invoking the new read owner.
    Partial response words belong to the read; unconsumed words stay in IO.
    """
    states, lines = [], []
    phase, op, writes, issued, supplied, result, queue = 1, 0, 2, 0, 0, [], []

    def snapshot():
        payload = config(14, 4096, 4) + words(phase, ADDRESS if phase else 0,
                                            size if phase else 0, len(result), *result)
        external = config(15, op, writes, issued, supplied, len(queue)) + words(*queue)
        states.append((payload, external))

    def call(*calls, status):
        nonlocal op
        op += 1
        lines.extend([f'CALL {op} C {100+op}', *calls, status])
        snapshot()

    snapshot()
    for pending in (2, 1):
        writes -= 1
        call(f'PENDING {pending}', status='BLOCKED')
    phase = 2
    call('PENDING 0', status='PROGRESS')
    phase, issued = 3, 1
    call(f'ISSUE {ADDRESS} {size}', status='PROGRESS')
    for i in range(size // 4):
        if not queue:
            queue = [response(j) for j in range(supplied, min(supplied + 3, size // 4))]
            supplied += len(queue)
            call('EMPTY', status='BLOCKED')
        value = queue.pop(0)
        result.append(value)
        if i + 1 == size // 4:
            phase = 4
        call(f'WORD {value}', status='COMPLETE' if phase == 4 else 'PROGRESS')
    op += 1
    lines += [f'CALL {op} C {100+op}', *[f'RESULT[{i}] {value}' for i, value in enumerate(result)]]
    phase, result = 0, []
    snapshot()
    return lines, states


def selected_cuts(size, states):
    if size <= 128:
        return list(range(len(states)))
    return sorted(set([*range(10), 63, 64, 65, len(states)//2,
                       *range(len(states)-4, len(states))]))


def suffix(lines, cut):
    label = f'CALL {cut+1} C {101+cut}'
    return lines[lines.index(label):] if label in lines else []


def audit_case(base, size):
    lines, states = oracle(size)
    reference = base / 'reference'
    require((reference / 'trace').read_text().splitlines() == lines, 'changed original-loop read behavior')
    for cut, (owner, queue) in enumerate(states):
        require((reference / f'cut-{cut}.owner').read_bytes() == owner and
                (reference / f'cut-{cut}.fixture').read_bytes() == queue,
                'incomplete source read owner/queue at ' + str((size, cut)))
    cuts = selected_cuts(size, states)
    continued = 0
    for cut in cuts:
        restored = base / f'restore-{cut}'
        require((restored / 'initial.owner').read_bytes() == states[cut][0] and
                (restored / 'initial.fixture').read_bytes() == states[cut][1],
                'changed complete fresh pre-edge readback at ' + str((size, cut)))
        wanted = suffix(lines, cut)
        require((restored / 'trace').read_text().splitlines() == wanted,
                'changed continued call/response/cycle at ' + str((size, cut)))
        continued += len(wanted)
    return dict(size_bytes=size, source_cuts=len(states), restored_cuts=cuts,
                pre_edge_owner_readbacks=2*len(cuts), continued_records=continued)


def audit(path):
    path = path.resolve()
    report = json.loads(path.read_text())
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'],
            'read component cannot certify CPU acceptance')
    catalog = report['artifact_sha256']
    require(set(catalog) == {str(p) for p in path.parent.rglob('*') if p.is_file() and p != path},
            'changed original read evidence membership')
    for name, digest in catalog.items():
        require(file_sha(name) == digest, 'changed native read evidence ' + name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    for backend in report['backends']:
        base = path.parent / backend['backend']
        require(backend['cases'] == [audit_case(base / str(size), size) for size in SIZES],
                'changed read continuation counts')
        log = (base / 'checks.log').read_text()
        require(int(re.search(r'ATOMIC_CHECKS (\d+)', log)[1]) == backend['atomic_checks'],
                'changed atomic test count')
        require(len(backend['invalid_cases']) == 14, 'missing malformed/incompatible read case')
        for case in backend['invalid_cases']:
            log = Path(case['log']).read_text()
            require('UNCHANGED BEFORE_EDGES 0 BEFORE_REQUESTS 0 BEFORE_PUBLICATION 0' in log and
                    'REJECT ' in log and not list(Path(case['output']).iterdir()),
                    'invalid read partially restored or published readback')
        expected_line = 'FIRST_DIVERGENCE fixture_cycle=127 acknowledged=26 expected=RESULT[0] 0 actual=RESULT[0] 1'
        corruption = (base / 'corruption.log').read_text()
        require(expected_line in corruption and
                (base / 'corruption/trace').read_text().splitlines() == suffix(oracle(64)[0], 7)[:-17],
                'corruption did not stop at first result boundary')
    require(len({c['pid'] for c in report['commands']}) == len(report['commands']), 'native process reused')
    for command in report['commands']:
        log = Path(command['log']).read_text()
        require(log.rstrip().endswith('exit=' + str(command['expected_exit'])) and
                command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT),
                'unbound VCS environment/command/result')
        require(not any(marker in log for marker in ('ERROR: AddressSanitizer', 'runtime error:',
                                                     'LeakSanitizer: detected')), 'sanitizer error')
    return dict(status='passed', summary=str(path), native_processes=len(report['commands']),
                fresh_continuations=sum(len(c['restored_cuts']) for b in report['backends'] for c in b['cases']),
                level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit), indent=2)); return
    require(args.out is not None and args.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'),
            'diagnostics must be under checkpoint runs')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env.sh LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    sources = [TESTS / 'loadmem_read_checkpoint.cc']
    inputs = [*sources, Path(__file__), TESTS / 'loadmem_read_checkpoint_tb.sv',
              STUBS / 'fesvr/loadmem_read.h', STUBS / 'fesvr/firesim_tsi.h',
              STUBS / 'fesvr/firesim_tsi.cc', STUBS / 'bridges/tsibridge.h',
              CC / 'core/checkpoint.h', CC / 'core/widget_checkpoint.h',
              ROOT / 'env.sh', ROOT / 'sims/firesim/env.sh', ROOT / 'automations/checkpoint_loop/vcs-env.sh']
    snapshots = out / 'source-snapshots'; snapshots.mkdir()
    bindings = []
    for p in inputs:
        digest = file_sha(p); snapshot = snapshots / digest
        if not snapshot.exists(): shutil.copyfile(p, snapshot)
        bindings.append(dict(path=str(p), snapshot=str(snapshot), sha256=digest))
    commands = []

    def execute(argv, log, expected=0):
        command = ['bash', '-lc', ENVIRONMENT + shlex.join([str(a) for a in argv])]
        result = run(command, log, cwd=out, expected=expected)
        pid = int(re.search(r'fresh_process_pid=(\d+)', result)[1])
        commands.append(dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log), pid=pid, expected_exit=expected))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return result

    include = f'-std=c++17 -I{CC} -I{STUBS}'
    native, simv = out / 'read-native', out / 'read-simv'
    execute([os.environ['CXX'], *shlex.split(include), '-Wall', '-Wextra', '-Werror',
             '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', *sources,
             '-o', native], out / 'native-build.log')
    execute([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'loadmem_read_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             f'-Mdir={out / "csrc"}', '-CFLAGS', include+' -DLOADMEM_READ_CHECKPOINT_DPI',
             '-o', simv, TESTS / 'loadmem_read_checkpoint_tb.sv', *sources], out / 'vcs-build.log')
    results = []
    for backend in ('native-sanitized', 'vcs-dpi'):
        base = out / backend; base.mkdir()

        def invoke(mode, target, size='', image='', queue='', expected='', log=None, failure=False):
            if backend == 'native-sanitized':
                argv = [native, mode, target]
                if mode == 'invalid': argv += [image]
                elif mode != 'check': argv += [size]
                if mode in ('restore', 'corrupt'): argv += [image, queue]
                if mode == 'corrupt': argv += [expected]
            else:
                argv = [simv, '-no_save', '+mode='+mode, '+out='+str(target),
                        '+bytes='+str(image if mode == 'invalid' else size),
                        '+image='+str(image), '+queue='+str(queue), '+expected='+str(expected)]
            return execute(argv, log or base / (target.name + '.log'),
                           2 if failure else 0)

        atomic = invoke('check', base / 'checks', log=base / 'checks.log')
        cases = []
        for size in SIZES:
            case = base / str(size); case.mkdir()
            reference = case / 'reference'
            invoke('reference', reference, size, log=case / 'reference.log')
            lines, states = oracle(size)
            for cut in selected_cuts(size, states):
                invoke('restore', case / f'restore-{cut}', size,
                       reference / f'cut-{cut}.owner', reference / f'cut-{cut}.fixture',
                       log=case / f'restore-{cut}.log')
            cases.append(audit_case(case, size))
        valid = (base / '64/reference/cut-7.owner').read_bytes()

        def alter(offset, value):
            data = bytearray(valid); struct.pack_into('<Q', data, offset, value); return bytes(data)

        invalids = dict(missing=None, truncated=valid[:-1], trailing=valid+b'\0',
                        version=alter(8, 2), kind=alter(16, 99), incompatible=alter(32, 2048),
                        phase=alter(48, 5), idle=alter(48, 0), premature_complete=alter(48, 4),
                        cursor=alter(72, 1 << 63), alignment=alter(56, 3),
                        zero_length=alter(64, 0), huge_length=alter(64, 8192),
                        response_width=alter(80, 1 << 32))
        rejected = []
        for name, payload in invalids.items():
            image = base / ('invalid-' + name + '.owner')
            if payload is not None: image.write_bytes(payload)
            target = base / ('invalid-' + name)
            log = base / ('invalid-' + name + '.log')
            invoke('invalid', target, image=image, log=log)
            rejected.append(dict(case=name, image=str(image), output=str(target), log=str(log)))
        corrupted = base / 'corrupted.owner'; corrupted.write_bytes(alter(80, 1))
        wanted = base / 'expected-continuation.txt'; wanted.write_text('\n'.join(suffix(oracle(64)[0], 7))+'\n')
        invoke('corrupt', base / 'corruption', 64, corrupted, base / '64/reference/cut-7.fixture', wanted,
               log=base / 'corruption.log', failure=True)
        results.append(dict(backend=backend, cases=cases, invalid_cases=rejected,
                            atomic_checks=int(re.search(r'ATOMIC_CHECKS (\d+)', atomic)[1])))
    for b in bindings:
        require(file_sha(b['path']) == b['sha256'], 'source changed during read continuations')
    report = dict(status='passed', scope='TSI loadmem read component, not complete HTIF/CPU',
                  commands=commands, backends=results, source_inputs=bindings,
                  artifact_sha256={str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
                  level1_verified=False, level2_verified=False)
    path = out / 'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(audit(path), indent=2))


if __name__ == '__main__':
    main()
