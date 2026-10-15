"""Fresh BCD identity caller/write/FIFO continuation at every operation cut.

Host component evidence only; complete HTIF and both CPU levels remain pending.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
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
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS
from tools.checkpoint_formats.tests.verify_tsi_memif_write_vcs import writer, reader, serial, initial

NAMES = ('identity', 'write', 'serial')
BACKENDS = ('native', 'vcs-dpi')


def identity(phase=0, command=0):
    return config(29, 1, 255, 64, 8, 1024)+words(phase, command)


def scenario():
    """Expand the installed BCD identity and head/tail/body write algorithms.

    Every serialized byte and service/response boundary is constructed outside
    C++; no production parser/serializer or callback supplies expected values.
    """
    plan, expected, states = [], [], []
    requests, responses = [], []
    command, phase, w = 0, 0, writer()

    def snapshot():
        states.append((identity(phase, command), w, serial(requests, responses)))

    def step(text, result=None):
        plan.append(text)
        expected.append(result or text)
        snapshot()

    def packet(cmd, address, data):
        requests.extend([cmd, address & 0xffffffff, address >> 32, len(data)//4-1, 0])
        if cmd:
            requests.extend(int.from_bytes(data[i:i+4], 'little') for i in range(0, len(data), 4))

    def drain():
        while requests:
            sent = requests[:3]
            del requests[:3]
            step('PACKET '+' '.join(map(str, sent)))

    snapshot()
    for residue in range(8):
        for what, name in ((0, b'read'), (1, b'write'), (255, b'bcd'), (2, b'')):
            address = 0x1280003000 + residue*0x10000 + what*128 + residue
            data = name.ljust(64, b'\0')
            command = (1 << 56) | (255 << 48) | (address << 8) | what
            phase = 1
            w = writer(1 if residue else 2, address, 0, data)
            step('BEGIN '+str(command))
            head = 8-residue if residue else 0
            for is_head in ((True, False) if residue else ()):
                offset, count, first = (0, head, residue) if is_head else (64-residue, residue, 0)
                a = (address+offset) & ~7
                original = bytes(initial(a+i) for i in range(8))
                incoming = [int.from_bytes(original[i:i+4], 'little') for i in (0, 4)]
                packet(0, a, bytes(8))
                write_phase = 1 if is_head else 2
                w = writer(write_phase, address, 0, data, reader(2, a))
                step('ADVANCE', 'ADVANCE BLOCKED')
                drain()
                step('ADVANCE', 'ADVANCE BLOCKED')
                responses.append(incoming[0])
                step('SEND '+str(incoming[0]))
                responses.clear()
                w = writer(write_phase, address, 0, data, reader(2, a, incoming[:1]))
                step('ADVANCE', 'ADVANCE BLOCKED')
                responses.append(incoming[1])
                step('SEND '+str(incoming[1]))
                responses.clear()
                merged = bytearray(original)
                merged[first:first+count] = data[offset:offset+count]
                packet(1, a, merged)
                w = writer(2 if is_head else 3, address, 0, data)
                step('ADVANCE', 'ADVANCE PROGRESS')
                drain()
            if not residue:
                w = writer(3, address, 0, data)
                step('ADVANCE', 'ADVANCE PROGRESS')
            packet(1, address+head, data[head:64-residue] if residue else data)
            phase, w = 2, writer()
            step('ADVANCE', 'ADVANCE PROGRESS')
            drain()
            phase = 3
            step('ADVANCE', 'ADVANCE COMPLETE RESPOND '+str((command & 0xffff000000000000) | 1))
            step('ADVANCE', 'ADVANCE COMPLETE')  # must not send a second response
            phase, command = 0, 0
            step('FINISH')
    return plan, expected, states


def audit(path):
    path = path.resolve()
    report = json.loads(path.read_text())
    out = path.parent
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'],
            'wrong identity acceptance scope')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path},
            'changed identity artifact membership')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed identity artifact '+name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed identity source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    plan, expected, states = scenario()
    require((out/'plan.txt').read_text().splitlines() == plan and
            (out/'expected.txt').read_text().splitlines() == expected, 'changed identity oracle')
    for backend in BACKENDS:
        capture = out/(backend+'-capture')
        for cut, state in enumerate(states):
            for name, image in zip(NAMES, state):
                require((capture/f'cut-{cut}.{name}').read_bytes() == image, 'incomplete producer readback')
    wanted = {(p, b, c) for p in BACKENDS for b in BACKENDS for c in range(len(states))}
    require(len(report['continuations']) == len(wanted) and
            {(c['producer'], c['backend'], c['cut']) for c in report['continuations']} == wanted,
            'missing identity continuation pairing')
    operations = readbacks = 0
    for case in report['continuations']:
        dest, cut = Path(case['destination']), case['cut']
        for name, image in zip(NAMES, states[cut]):
            require((dest/('preedge.'+name)).read_bytes() == image, 'wrong pre-service identity readback')
        require((dest/'continuation.bin').read_bytes() == b''.join(b for state in states[cut:] for b in state),
                'wrong complete identity continuation readback')
        require((dest/'trace').read_text() == ''.join(f'{i+1} {expected[i]}\n' for i in range(cut, len(plan))),
                'wrong identity response/service trace')
        operations += len(plan)-cut
        readbacks += 3*(len(states)-cut)
        require(f'IDENTITY_CONTINUATION operations={len(plan)-cut} complete_readbacks={3*(len(states)-cut)} '
                'restore_services=0 target_edges=0' in Path(case['log']).read_text(), 'incomplete identity process')
    for case in report['invalids']:
        require('REJECTED_BEFORE_MUTATION owners=3 target_edges=0' in Path(case['log']).read_text(),
                'invalid identity group changed an owner')
    require(len(report['invalids']) == 30 and len(report['corruptions']) == 12, 'incomplete negative coverage')
    for case in report['corruptions']:
        require((Path(case['destination'])/'first-divergence.txt').read_text() == case['expected_divergence'],
                'wrong first identity divergence')
    atomic = []
    for backend in BACKENDS:
        log = (out/(backend+'-check.log')).read_text()
        match = re.search(r'ATOMIC malformed=(\d+) membership=(\d+) cross=(\d+) allocation_failures=(\d+) hostile=(\d+) unchanged_on_failure=1', log)
        require(match is not None, 'missing atomic identity checks')
        atomic.append(list(map(int, match.groups())))
    require(atomic[0] == atomic[1], 'native/VCS identity atomic coverage differs')
    pids = []
    for command in report['commands']:
        log = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(command['expected_exit'])), 'unbound native identity command')
        require(not any(s in log for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')),
                'identity sanitizer failure')
        pids.append(int(re.search(r'fresh_process_pid=(\d+)', log)[1]))
    require(len(pids) == len(set(pids)), 'reused identity process')
    return dict(status='passed', scenarios=32, cuts=len(states), fresh_component_continuations=len(wanted),
                host_operations=operations, complete_owner_readbacks=readbacks, invalid_processes=30,
                first_divergence_cases=12, atomic_checks_per_backend=atomic[0],
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
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    source, sv, alloc = (TESTS/n for n in ('tsi_bcd_identity_checkpoint.cc', 'tsi_bcd_identity_checkpoint_tb.sv',
                                          'tsi_terminal_allocations.cc'))
    inputs = [source, sv, alloc, Path(__file__), STUBS/'fesvr/tsi_bcd_identity.h', STUBS/'fesvr/tsi_memif_write.h',
              STUBS/'fesvr/tsi_serial_read.h', STUBS/'fesvr/tsi_serial_state.h', CC/'core/checkpoint.h',
              CC/'core/widget_checkpoint.h', TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py',
              TESTS/'verify_firesim_tsi_loadmem_vcs.py', TESTS/'verify_tsi_memif_write_vcs.py',
              ROOT/'tools/checkpoint_formats/retained_evidence.py', ROOT/'tools/checkpoint_formats/evidence.py',
              ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh']
    (out/'sources').mkdir()
    bindings, commands = [], []
    for path in dict.fromkeys(inputs):
        digest = file_sha(path)
        snapshot = out/'sources'/digest
        if not snapshot.exists():
            shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))

    def execute(argv, log, expected=0):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        run(command, log, cwd=out, expected=expected)
        return dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log), expected_exit=expected)

    native, simv = out/'identity-native', out/'simv'
    include = f'-std=c++17 -I{CC} -I{STUBS}'
    commands.append(execute([os.environ['CXX'], *shlex.split(include), '-Wall', '-Wextra', '-Werror', '-g', '-no-pie',
                             '-fsanitize=address,undefined', '-fno-omit-frame-pointer', source, alloc, '-o', native], out/'native-build.log'))
    commands.append(execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
                             '-top', 'tsi_bcd_identity_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
                             '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_BCD_IDENTITY_DPI',
                             '-o', simv, sv, source, alloc], out/'vcs-build.log'))
    plan, expected, states = scenario()
    (out/'plan.txt').write_text('\n'.join(plan)+'\n')
    (out/'expected.txt').write_text('\n'.join(expected)+'\n')

    def invoke(backend, mode, name, producer='native', cut=0, source=None, code=0, **extra):
        dest = out/name
        values = list(map(str, [mode, dest, out/'plan.txt', out/'expected.txt',
                               source or out/(producer+'-capture')/f'cut-{cut}', cut]))
        argv = [native, *values] if backend == 'native' else [simv, '-no_save', *[
            '+'+k+'='+v for k, v in zip(('mode', 'out', 'plan', 'expected', 'source', 'cut'), values)]]
        return dict(execute(argv, out/(name+'.log'), code), backend=backend, producer=producer,
                    cut=cut, destination=str(dest), **extra)

    for backend in BACKENDS:
        commands.append(invoke(backend, 'check', backend+'-check'))
        commands.append(invoke(backend, 'capture', backend+'-capture'))
    jobs = [(b, 'restore', f'{p}-{b}-cut-{c}', p, c) for p in BACKENDS for b in BACKENDS for c in range(len(states))]
    with ThreadPoolExecutor(max_workers=4) as pool:
        continuations = list(pool.map(lambda job: invoke(*job), jobs))
    commands.extend(continuations)
    active_cut = next(c for c, (i, w, q) in enumerate(states) if w[64] == 1 and len(w) == 272)
    good = states[active_cut]
    invalids, corruptions = [], []
    invalid_cases = []
    for owner in range(3):
        for name in ('missing', 'truncated', 'build', 'extra'):
            invalid_cases.append((f'{owner}-{name}', owner, name))
    invalid_cases += [('caller-phase', 0, 'phase'), ('child-address', 1, 'address'), ('child-payload', 1, 'payload')]
    for name, owner, change in invalid_cases:
        prefix = out/('invalid-'+name)
        for index, (label, image) in enumerate(zip(NAMES, good)):
            if owner == index:
                if change == 'missing':
                    continue
                image = bytearray(image)
                if change == 'truncated':
                    image = image[:-1]
                elif change == 'extra':
                    image += b'\0'
                elif change == 'build':
                    image[16] ^= 1
                elif change == 'phase':
                    struct.pack_into('<Q', image, 72, 2)
                elif change == 'address':
                    # Address plus eight is independently valid for the child
                    # only if its nested reader changes with it.
                    struct.pack_into('<Q', image, 72, int.from_bytes(image[72:80], 'little')+8)
                    struct.pack_into('<Q', image, 240, int.from_bytes(image[240:248], 'little')+8)
                elif change == 'payload':
                    image[96] ^= 1
            Path(str(prefix)+'.'+label).write_bytes(image)
        for backend in BACKENDS:
            invalids.append(invoke(backend, 'invalid', backend+'-invalid-'+name, source=prefix))
    commands.extend(invalids)
    # Accepted actual semantic corruption: preserved head response, preserved
    # tail response, and a queued command word. The input/expected trace stays
    # byte-identical, and every divergent request word remains unconsumed.
    selected = []
    for label, phase in (('head-response', 1), ('tail-response', 2)):
        cut = next(c for c, (i, w, q) in enumerate(states) if w[64] == phase and len(w) == 272)
        # Head byte zero and tail byte one are outside the requested payload
        # at residue one. Corrupt a preserved byte, never a merged-away byte.
        selected.append((label, cut, 1, len(states[cut][1])-8+(phase == 2)))
    cut = next(c for c in range(active_cut, len(plan)) if plan[c].startswith('PACKET 1 '))
    selected.append(('packet', cut, 2, 72))
    for label, cut, owner, offset in selected:
        prefix = out/(label+'-corrupt')
        for index, (name, image) in enumerate(zip(NAMES, states[cut])):
            image = bytearray(image)
            if index == owner:
                image[offset] ^= 1
            Path(str(prefix)+'.'+name).write_bytes(image)
        first = cut if owner == 2 else next(c for c in range(cut, len(plan)) if plan[c].startswith('PACKET 1 '))+1
        word = 0 if owner == 2 else 2
        expected_word = int(plan[first].split()[word+1])
        mask = 256 if label == 'tail-response' else 1
        divergence = f'operation={first+1} word={word} expected={expected_word} actual={expected_word ^ mask} acknowledged=0\n'
        for producer in BACKENDS:
            for backend in BACKENDS:
                corruptions.append(invoke(backend, 'restore', f'{producer}-{backend}-{label}-corrupt', producer, cut,
                                          source=prefix, code=2, expected_divergence=divergence))
    commands.extend(corruptions)
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'source changed during identity verification')
    report = dict(status='passed', scope='identity caller/write/serial components; parent HTIF/CPU admission pending',
                  source_inputs=bindings, commands=commands, continuations=continuations, invalids=invalids,
                  corruptions=corruptions, level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(summary=str(path), **audit(path)), indent=2))


if __name__ == '__main__':
    main()
