"""Atomic bound HTIF poll/BCD/terminal component restoration in native and VCS.

Checks component operations, not a complete TSI or CPU target-cycle checkpoint.
"""
from tools.checkpoint_formats import toolchain as _toolchain
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
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, FESVR

READ = 1 << 56
INPUT = b'A\0\xff'
NAMES = ('poll', 'terminal', 'bcd')


def scenario():
    phase = command = cursor = pending = 0
    queue, output, plan, events, images = [], b'', [], [], []

    def snapshot():
        return dict(poll=config(24, 4096, 8192, 8) + words(phase, command, len(queue), *queue),
                    terminal=config(27, 1, 1048576, 3) + INPUT + words(cursor, len(output)) + output,
                    bcd=config(26, 1, 8) + words(pending, *([READ] * pending)))

    images.append(snapshot())

    def step(line, next_phase, next_command=None, enqueue=False, tick=False, emit=None, pop=False):
        nonlocal phase, command, cursor, pending, output
        plan.append(line)
        event = line + '\n'
        phase = next_phase
        if next_command is not None:
            command = next_command
        if enqueue:
            pending += 1
        if tick and pending and cursor < len(INPUT):
            queue.append(READ | 0x100 | INPUT[cursor])
            cursor += 1
            pending -= 1
        if emit is not None:
            output += bytes([emit])
            event += f'OUTPUT {emit}\n'
        if pop:
            queue.pop(0)
        events.append(event)
        images.append(snapshot())

    step('X 0', 1)
    step('R 4096 0 0', 1)
    step('R 4096 1 0', 4)
    step('I 0', 4)
    step('I 1', 5)
    step('T', 6, 0, tick=True)
    step('N', 0)

    def request(value, emit=None):
        step('X 0', 1)
        step(f'R 4096 1 {value}', 2, value)
        step('W 4096 0', 3)
        step(f'D {value}', 5, enqueue=value == READ, emit=emit)
        step('T', 6, 0, tick=True)

    request(READ)
    step('R 8192 0 0', 6)
    step('R 8192 1 9', 0)
    request(READ)
    step('R 8192 1 0', 7)
    response_cut = len(plan)
    step(f'W 8192 {READ | 0x141}', 0, pop=True)
    request(READ | (1 << 48) | 90, emit=90)
    step('R 8192 1 0', 7)
    step(f'W 8192 {READ | 0x100}', 0, pop=True)
    request(READ)
    step('R 8192 1 9', 0)
    request(READ)  # EOF leaves an outstanding BCD command and an older response.
    step('R 8192 1 9', 0)
    request(READ)
    step('R 8192 1 0', 7)
    step(f'W 8192 {READ | 0x1ff}', 0, pop=True)
    step('X 0', 1)
    step('R 4096 1 0', 4)
    step('I 0', 4)
    step('I 1', 5)
    step('T', 6, 0, tick=True)
    step('N', 0)
    step('X 1', 8)
    step('N', 8)
    # Cursor corruption immediately before the first real BCD tick changes the
    # first fromhost write. Until that boundary the component events agree.
    return plan, events, images, dict(terminal_cut=11, response_cut=response_cut)


def audit(path):
    path = path.resolve()
    report = json.loads(path.read_text())
    out = path.parent
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'],
            'wrong polling-device scope')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path},
            'polling-device artifact membership changed')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed polling-device artifact ' + name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed polling-device source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    plan, events, images, cuts = scenario()
    require((out/'plan.txt').read_text() == '\n'.join(plan) + '\n', 'changed service inputs')
    phases = {int.from_bytes(image['poll'][len(config(24, 4096, 8192, 8)):][:8], 'little') for image in images}
    require(phases == set(range(9)), 'missing polling phase coverage')
    readbacks = 0
    for backend in ('native', 'vcs-dpi'):
        capture = out/(backend+'-capture')
        require((capture/'events.log').read_text() == ''.join(events), 'source events differ from independent oracle')
        for cut, expected in enumerate(images):
            for name in NAMES:
                require((capture/f'cut-{cut}.{name}').read_bytes() == expected[name], 'incomplete captured ' + name)
    require(len(report['restores']) == 4*len(images), 'missing backend/cut pairing')
    for case in report['restores']:
        dest = Path(case['destination'])
        cut = case['cut']
        require('POLLING_READBACK owners=3 target_edges=0 services=0' in Path(case['log']).read_text(), 'restore entered services')
        for name in NAMES:
            require((dest/('preedge.'+name)).read_bytes() == images[cut][name], 'incomplete pre-service readback')
            require((dest/('final.'+name)).read_bytes() == images[-1][name], 'final state differs')
            readbacks += 2
        for index in range(cut+1, len(images)):
            for name in NAMES:
                require((dest/f'cut-{index}.{name}').read_bytes() == images[index][name], 'continued state differs')
                readbacks += 1
        require((dest/'events.log').read_text() == ''.join(events[cut:]), 'continued component events differ')
    malformed = allocations = 0
    require(len(report['invalids']) == 4, 'missing invalid backend pairing')
    for case in report['invalids']:
        expected = images[cuts['response_cut']]
        count = sum(len(value)+2 for value in expected.values())
        text = Path(case['log']).read_text()
        match = re.search(r'POLLING_TRANSACTION malformed=(\d+) membership=8 allocation_failures=(\d+) '
                          r'binding_rejections=1 unchanged_on_failure=1 services_before_readback=0', text)
        require(match and int(match[1]) == count and int(match[2]) >= 6, 'incomplete atomic restore coverage')
        malformed += count
        allocations += int(match[2])
        for name in NAMES:
            require((Path(case['destination'])/('preedge.'+name)).read_bytes() == expected[name], 'incomplete valid restore after rejection')
    require(len(report['corruptions']) == 8, 'missing semantic corruption checks')
    for case in report['corruptions']:
        dest = Path(case['destination'])
        cut = case['cut']
        lines = (dest/'events.log').read_text().splitlines()
        expected = ''.join(events[cut:]).splitlines()
        first = next(i for i, (left, right) in enumerate(zip(lines, expected)) if left != right)
        operation = cuts['response_cut']
        actual = (READ | 0x100) if case['owner'] == 'terminal' else (READ | 0x140)
        marker = f'FIRST_DIVERGENCE host_operation={operation} expected=W 8192 {READ | 0x141} actual=W 8192 {actual} acknowledged=0'
        require(lines[first] == marker and first == operation-cut and len(lines) == first+1,
                'wrong first divergent component boundary or acknowledged corrupt write')
        require(case['first_divergence'] == dict(host_operation=operation, signal='fromhost_write',
                                               expected=READ | 0x141, actual=actual, acknowledged=False),
                'unbound first divergence')
        for name in NAMES:
            require((dest/('preedge.'+name)).read_bytes() == Path(str(case['source'])+'.'+name).read_bytes(),
                    'corruption was not loaded/read back')
    pids = []
    for command in report['commands']:
        text = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and
                text.rstrip().endswith('exit='+str(command['expected_exit'])), 'wrong native environment/result')
        require(not any(s in text for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')),
                'polling-device sanitizer error')
        pids.append(int(re.search(r'fresh_process_pid=(\d+)', text)[1]))
    require(len(pids) == len(set(pids)), 'component check reused a process')
    return dict(status='passed', fresh_three_owner_restores=len(report['restores']), caller_phases=9,
                continued_host_operations=4*sum(range(len(images))), complete_owner_readbacks=readbacks,
                atomic_malformed_rejections=malformed, owner_membership_rejections=32,
                unbound_callback_rejections=4, allocation_failures=allocations, first_divergences=8,
                level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit), indent=2))
        return
    require(args.out and args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    source = TESTS/'tsi_polling_devices_checkpoint.cc'
    sv = TESTS/'tsi_polling_devices_checkpoint_tb.sv'
    allocator = TESTS/'tsi_terminal_allocations.cc'
    library = FESVR/'lib/libfesvr.a'
    inputs = [source, sv, allocator, library, Path(__file__), *sorted((FESVR/'include/fesvr').glob('*.h')),
              *[STUBS/'fesvr'/name for name in ('tsi_bcd.h', 'tsi_terminal.h', 'tsi_htif_poll.h')],
              CC/'core/widget_checkpoint.h', CC/'core/checkpoint.h', TESTS/'verify_semantic_vcs.py',
              TESTS/'verify_firesim_tsi_loadmem_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py',
              ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots = out/'sources'
    snapshots.mkdir()
    bindings, commands = [], []
    for path in dict.fromkeys(inputs):
        digest = file_sha(path)
        snapshot = snapshots/digest
        if not snapshot.exists():
            shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))

    def execute(argv, log, expected=0):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        run(command, log, cwd=out, expected=expected)
        return dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log), expected_exit=expected)

    native, simv = out/'polling-native', out/'simv'
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{FESVR/"include"}'
    commands.append(execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer', source, allocator, library, '-lpthread', '-o', native], out/'native-build.log'))
    commands.append(execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
                            '-top', 'tsi_polling_devices_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
                            '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_POLLING_DEVICES_DPI',
                            '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread',
                            '-o', simv, sv, source, allocator], out/'vcs-build.log'))
    plan, events, images, cuts = scenario()
    plan_path = out/'plan.txt'
    plan_path.write_text('\n'.join(plan)+'\n')

    def invoke(backend, mode, name, source='unused', cut=0, expected=0):
        dest = out/name
        argv = [native, mode, source, plan_path, dest, cut] if backend == 'native' else [
            simv, '-no_save', '+mode='+mode, '+source='+str(source), '+plan='+str(plan_path),
            '+destination='+str(dest), '+cut='+str(cut)]
        return dict(execute(argv, out/(name+'.log'), expected), backend=backend, mode=mode,
                    destination=str(dest), source=str(source), cut=cut)

    for backend in ('native', 'vcs-dpi'):
        commands.append(invoke(backend, 'capture', backend+'-capture'))
    jobs, restores, invalids, corruptions = [], [], [], []
    for producer in ('native', 'vcs-dpi'):
        for backend in ('native', 'vcs-dpi'):
            prefix = f'{producer}-{backend}'
            for cut in range(len(images)):
                jobs.append((restores, (backend, 'restore', f'{prefix}-cut-{cut}', out/(producer+f'-capture/cut-{cut}'), cut)))
            jobs.append((invalids, (backend, 'invalid', prefix+'-invalid', out/(producer+f'-capture/cut-{cuts["response_cut"]}'))))
            for owner in ('poll', 'terminal'):
                cut = cuts['response_cut' if owner == 'poll' else 'terminal_cut']
                corrupt = dict(images[cut])
                if owner == 'poll':
                    corrupt[owner] = corrupt[owner][:-16] + words(READ | 0x140, READ | 0x100)
                else:
                    start = len(config(27, 1, 1048576, 3)) + len(INPUT)
                    corrupt[owner] = corrupt[owner][:start] + words(1) + corrupt[owner][start+8:]
                source_path = out/(prefix+'-'+owner+'-corrupt-image')
                for name, data in corrupt.items():
                    Path(str(source_path)+'.'+name).write_bytes(data)
                jobs.append((corruptions, (backend, 'corrupt', prefix+'-'+owner+'-corrupt', source_path, cut, 3)))
    # Each simulation gets a separate process and directory; independent jobs
    # may overlap, while all mutations within each restore remain sequential.
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [(destination, pool.submit(invoke, *argv)) for destination, argv in jobs]
        for destination, future in futures:
            case = future.result()
            if destination is corruptions:
                owner = 'terminal' if '-terminal-corrupt' in case['destination'] else 'poll'
                case.update(owner=owner, first_divergence=dict(host_operation=cuts['response_cut'], signal='fromhost_write',
                            expected=READ | 0x141, actual=READ | (0x100 if owner == 'terminal' else 0x140), acknowledged=False))
            commands.append(case)
            destination.append(case)
    (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'native source changed during verification')
    report = dict(status='passed', scope='bound poll/BCD/sealed-terminal components; complete CPU restore unsupported',
                  source_inputs=bindings, commands=commands, restores=restores, invalids=invalids, corruptions=corruptions,
                  level1_verified=False, level2_verified=False)
    summary = out/'summary.json'
    report['artifact_sha256'] = {str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p != summary}
    summary.write_text(json.dumps(report, indent=2)+'\n')
    result = audit(summary)
    print(json.dumps(dict(summary=str(summary), result=result), indent=2))


if __name__ == '__main__':
    main()
