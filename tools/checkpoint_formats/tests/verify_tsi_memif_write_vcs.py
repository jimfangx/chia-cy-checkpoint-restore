"""Fresh write-child/FIFO continuations and installed-memif differential checks.

These are host-operation cuts, not complete CPU checkpoints or target cycles.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
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
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, FESVR

MAXIMUM = 1048576


def reader(phase=0, address=0, collected=()):
    return config(20, 1024, 4, 2, 2)+words(phase, address, 8 if phase else 0, len(collected), *collected)


def writer(phase=0, address=0, cursor=0, data=b'', child=None):
    child = reader() if child is None else child
    return config(28, 1, 8, 1024, MAXIMUM)+words(phase, address, cursor, len(data))+data+words(len(child))+child


def serial(requests=(), responses=()):
    return config(19, 4, 2, 2, 1024)+words(len(requests), *requests, len(responses), *responses)


def initial(address):
    return ((address*37) ^ (address >> 8) ^ 0xa5) & 255


def scenario():
    """Expand installed memif.cc's head, tail, body order into handshakes.

    Construct every byte independently; the C++ serializer is never invoked.
    Each region is disjoint, so neighboring sentinel bytes have known values.
    """
    plan, expected, states, events, cases = [], [], [], [], []
    phase, address, cursor, data, child = 0, 0, 0, b'', reader()
    requests, responses = [], []

    def snapshot():
        states.append((writer(phase, address, cursor, data, child), serial(requests, responses)))

    def step(text, result=None):
        plan.append(text)
        expected.append(result or text)
        snapshot()

    def packet():
        # Retain a partially consumed header and payload as separate cuts.
        chunks = 0
        while requests:
            n = min(len(requests), 3) if chunks < 2 else len(requests)
            chunks += 1
            sent = requests[:n]
            del requests[:n]
            step('PACKET '+' '.join(map(str, sent)))

    def enqueue(command, a, n, content=b''):
        requests.extend([command, a & 0xffffffff, a >> 32, n//4-1, 0])
        if command:
            requests.extend(int.from_bytes(content[i:i+4], 'little') for i in range(0, n, 4))

    def merge(a, offset, count, first, next_phase):
        nonlocal child, phase
        original = bytes(initial(a+i) for i in range(8))
        values = [int.from_bytes(original[i:i+4], 'little') for i in (0, 4)]
        enqueue(0, a, 8)
        child = reader(2, a)
        events.append(f'READ {a} 8 {original.hex()}')
        step('ADVANCE', 'ADVANCE BLOCKED')
        packet()
        # Repeated empty service must not duplicate the request.
        step('ADVANCE', 'ADVANCE BLOCKED')
        responses.append(values[0])
        step('SEND '+str(values[0]))
        responses.clear()
        child = reader(2, a, values[:1])
        step('ADVANCE', 'ADVANCE BLOCKED')
        responses.append(values[1])
        step('SEND '+str(values[1]))
        responses.clear()
        merged = bytearray(original)
        merged[first:first+count] = data[offset:offset+count]
        enqueue(1, a, 8, merged)
        child, phase = reader(), next_phase
        events.append(f'WRITE {a} 8 {merged.hex()}')
        step('ADVANCE', 'ADVANCE PROGRESS')
        packet()

    snapshot()
    specs = [(r, 64, r == 7) for r in range(8)] + [
        (0, 0, False), (7, 1, False), (1, 7, False), (0, 8, False),
        (7, 9, False), (1, 63, False), (3, 65, False), (0, 1023, False),
        (0, 1024, True), (3, 1025, False), (7, 2057, True)]
    for index, (residue, size, zeros) in enumerate(specs):
        address = 0x1280003000 + index*0x10000 + residue
        data = bytes(size) if zeros else bytes((i*19+0x61) & 255 for i in range(size))
        cases.append(dict(address=address, size=size, sha256=hashlib.sha256(data).hexdigest(),
                          zero_payload=zeros))
        prefix = min(size, 8-residue) if residue else 0
        tail = (size-prefix) % 8
        phase, cursor = (4 if not size else 1 if residue else 2), 0
        step(f'BEGIN {address} '+(data.hex() or '-'))
        if prefix:
            merge(address & ~7, 0, prefix, residue, 2)
        if tail:
            merge(address+size-tail, size-tail, tail, 0, 3)
        elif size:
            phase = 3
            step('ADVANCE', 'ADVANCE PROGRESS')
        body = size-prefix-tail
        while size and phase != 4:
            n = min(1024, body-cursor)
            if n:
                content = data[prefix+cursor:prefix+cursor+n]
                enqueue(1, address+prefix+cursor, n, content)
                events.append(f'WRITE {address+prefix+cursor} {n} {content.hex()}')
                cursor += n
            phase = 4 if cursor == body else 3
            step('ADVANCE', 'ADVANCE COMPLETE' if phase == 4 else 'ADVANCE PROGRESS')
            packet()
        step('ADVANCE', 'ADVANCE COMPLETE')
        phase, address, cursor, data = 0, 0, 0, b''
        step('FINISH')
    return plan, expected, states, events, cases


def audit(path):
    path = path.resolve()
    report = json.loads(path.read_text())
    out = path.parent
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'],
            'wrong memif acceptance scope')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path},
            'changed memif artifact membership')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed memif artifact '+name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed memif source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    plan, expected, states, events, cases = scenario()
    require(report['cases'] == cases and (out/'plan.txt').read_text().splitlines() == plan and
            (out/'expected.txt').read_text().splitlines() == expected, 'changed memif oracle')
    for backend in ('native', 'vcs-dpi'):
        require((out/(backend+'-installed/installed-events.txt')).read_text().splitlines() == events,
                'installed FESVR memif transaction ordering/data differs')
        require(int(re.search(r'ATOMIC_CHECKS (\d+)', (out/(backend+'-check.log')).read_text())[1]) >= 500,
                'incomplete atomic/hostile/max-size checks')
        source = out/(backend+'-capture')
        for cut, (w, q) in enumerate(states):
            require((source/f'cut-{cut}.write').read_bytes() == w and
                    (source/f'cut-{cut}.serial').read_bytes() == q, 'incomplete original memif state')
        require((source/'trace').read_text().splitlines() == [f'{i+1} {s}' for i, s in enumerate(expected)],
                'wrong original memif execution')
    wanted = {(p, b, c) for p in ('native', 'vcs-dpi') for b in ('native', 'vcs-dpi') for c in range(len(states))}
    require(len(report['continuations']) == len(wanted) and
            {(c['producer'], c['backend'], c['cut']) for c in report['continuations']} == wanted,
            'missing memif backend/cut pairing')
    readbacks = operations = 0
    # Cache each suffix once; every destination must retain all complete words.
    suffixes = [b''.join(part for state in states[c:] for part in state) for c in range(len(states))]
    for case in report['continuations']:
        dest, cut = Path(case['destination']), case['cut']
        require((dest/'preedge.write').read_bytes() == states[cut][0] and
                (dest/'preedge.serial').read_bytes() == states[cut][1], 'incomplete pre-service memif readback')
        require((dest/'continuation.bin').read_bytes() == suffixes[cut], 'changed continued complete memif state')
        require((dest/'trace').read_text().splitlines() == [f'{i+1} {s}' for i, s in enumerate(expected) if i >= cut],
                'changed continued memif transaction timing')
        count = len(plan)-cut
        require(f'WRITE_CONTINUATION operations={count} complete_readbacks={2*(count+1)} target_edges=0 restore_services=0'
                in Path(case['log']).read_text(), 'continuation did not finish')
        readbacks += 2*(count+1)
        operations += count
    for case in report['invalids']:
        require('REJECTED_BEFORE_MUTATION zero_edges=1' in Path(case['log']).read_text(),
                'invalid memif image partially restored')
        require((Path(case['destination'])/'unchanged.write').read_bytes() == writer(1, 7, 0, b'\1\2\3', reader(2, 0, [42])) and
                (Path(case['destination'])/'unchanged.serial').read_bytes() == serial([0, 0, 0, 1, 0]),
                'invalid image changed a pristine peer')
    require(len(report['corruptions']) == 12, 'missing semantic corruption pairings')
    for case in report['corruptions']:
        require((Path(case['destination'])/'first-divergence.txt').read_text() == case['expected_divergence'],
                'corruption was not detected at its first request word')
    pids = []
    for command in report['commands']:
        log = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(command['expected_exit'])), 'unbound native VCS environment/result')
        require(not any(s in log for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')),
                'memif sanitizer failure')
        pids.append(int(re.search(r'fresh_process_pid=(\d+)', log)[1]))
    require(len(pids) == len(set(pids)), 'reused memif process')
    return dict(status='passed', scenarios=len(cases), component_cuts=len(states),
                fresh_component_continuations=len(wanted), complete_readbacks=readbacks, host_operations=operations,
                invalid_processes=len(report['invalids']), first_divergence_cases=len(report['corruptions']),
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
    source, sv = (TESTS/n for n in ('tsi_memif_write_checkpoint.cc', 'tsi_memif_write_checkpoint_tb.sv'))
    library = FESVR/'lib/libfesvr.a'
    inputs = [source, sv, Path(__file__), library, STUBS/'fesvr/tsi_memif_write.h', STUBS/'fesvr/tsi_serial_read.h',
              STUBS/'fesvr/tsi_serial_state.h', CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h',
              *sorted((FESVR/'include/fesvr').glob('*.h')), FESVR/'include/riscv/cfg.h',
              TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py',
              TESTS/'verify_firesim_tsi_loadmem_vcs.py', ROOT/'tools/checkpoint_formats/retained_evidence.py',
              ROOT/'tools/checkpoint_formats/evidence.py', ROOT/'env.sh', ROOT/'sims/firesim/env.sh',
              ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots = out/'sources'
    snapshots.mkdir()
    bindings = []
    for path in dict.fromkeys(inputs):
        digest = file_sha(path)
        snapshot = snapshots/digest
        if not snapshot.exists():
            shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    commands = []

    def execute(argv, log, expected=0):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        run(command, log, cwd=out, expected=expected)
        return dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log), expected_exit=expected)

    native, simv = out/'write-native', out/'simv'
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{FESVR/"include"}'
    commands.append(execute([os.environ['CXX'], *shlex.split(include), '-Wall', '-Wextra', '-Werror', '-g', '-no-pie',
                             '-fsanitize=address,undefined', '-fno-omit-frame-pointer', source, library, '-o', native], out/'native-build.log'))
    commands.append(execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
                             '-top', 'tsi_memif_write_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
                             '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_MEMIF_WRITE_DPI',
                             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread',
                             '-o', simv, sv, source], out/'vcs-build.log'))
    plan, expected, states, events, cases = scenario()
    (out/'plan.txt').write_text('\n'.join(plan)+'\n')
    (out/'expected.txt').write_text('\n'.join(expected)+'\n')
    (out/'installed-expected.txt').write_text('\n'.join(events)+'\n')

    def invoke(backend, mode, name, producer='native', cut=0, image=None, queue=None, code=0, **extra):
        dest = out/name
        values = list(map(str, [mode, dest, out/'plan.txt', out/'expected.txt',
                               image or out/(producer+f'-capture/cut-{cut}.write'),
                               queue or out/(producer+f'-capture/cut-{cut}.serial'), cut]))
        argv = [native, *values] if backend == 'native' else [
            simv, '-no_save', *['+'+k+'='+v for k, v in zip(('mode', 'out', 'plan', 'expected', 'image', 'queue', 'cut'), values)]]
        return dict(execute(argv, out/(name+'.log'), code), backend=backend, producer=producer, cut=cut,
                    destination=str(dest), **extra)

    for backend in ('native', 'vcs-dpi'):
        for mode in ('check', 'installed', 'capture'):
            commands.append(invoke(backend, mode, backend+'-'+mode))
    jobs = [(b, 'restore', f'{p}-{b}-cut-{c}', p, c)
            for p in ('native', 'vcs-dpi') for b in ('native', 'vcs-dpi') for c in range(len(states))]
    with ThreadPoolExecutor(max_workers=4) as pool:
        continuations = list(pool.map(lambda job: invoke(*job), jobs))
    commands.extend(continuations)
    invalids, corruptions = [], []
    good = next(w for w, _ in states if w[64] == 1 and w[-8:] == words(0))
    invalid_images = {'missing': None, 'empty': b'', 'truncated': good[:-1], 'extra': good+b'\0'}
    for name, at, value in [('kind', 16, 27), ('alignment', 40, 4), ('maximum', 56, 4096), ('phase', 64, 5),
                            ('cursor', 80, 1), ('huge-size', 88, 2**64-1), ('idle-payload', 64, 0)]:
        changed = bytearray(good)
        struct.pack_into('<Q', changed, at, value)
        invalid_images[name] = changed
    for name, image in invalid_images.items():
        path = out/('invalid-'+name+'.write')
        if image is not None:
            path.write_bytes(image)
        for backend in ('native', 'vcs-dpi'):
            invalids.append(invoke(backend, 'invalid', backend+'-invalid-'+name, image=path))
    good_path = out/'valid.write'
    good_path.write_bytes(good)
    for name, image in [('missing-peer', None), ('truncated-peer', serial()[:-1]),
                        ('incompatible-peer', config(19, 4, 2, 2, 512)+words(0, 0))]:
        path = out/(name+'.serial')
        if image is not None:
            path.write_bytes(image)
        for backend in ('native', 'vcs-dpi'):
            invalids.append(invoke(backend, 'invalid', backend+'-'+name, image=good_path, queue=path))
    commands.extend(invalids)
    # Valid semantic state changes, not checksums/expected results. Mutate a
    # preserved head byte, an unwritten payload byte, and an unconsumed packet.
    selected = []
    for cut, (w, q) in enumerate(states):
        size = int.from_bytes(w[88:96], 'little')
        if w[64] == 1 and size == 64 and len(w) == 104+size+104 and not selected:
            selected.append(('head-response', cut, 'write', len(w)-8, 1))
            selected.append(('payload', cut, 'write', 96, 1))
        if selected and len(selected) == 2 and plan[cut].startswith('PACKET 1 ') and len(q) > 112:
            selected.append(('packet', cut, 'serial', 72, 1))
    require(len(selected) == 3, 'missing corruption cuts')
    for name, cut, owner, offset, mask in selected:
        changed = bytearray(states[cut][0 if owner == 'write' else 1])
        changed[offset] ^= mask
        path = out/(name+'-corrupt.'+owner)
        path.write_bytes(changed)
        # The expected first packet is calculated independently from the plan.
        first = next(i for i in range(cut, len(plan)) if plan[i].startswith('PACKET 1 ')) if owner == 'write' else cut
        expected_words = list(map(int, plan[first].split()[1:]))
        word_index = 0 if name == 'packet' else None
        if name != 'packet':
            # The write header is drained in groups of three; data starts in
            # the second group at index two. Low byte is the preserved head
            # sentinel; byte one is payload[0] for residue one.
            first += 1
            expected_words = list(map(int, plan[first].split()[1:]))
            word_index = 2
        expected_word = expected_words[word_index]
        actual_word = expected_word ^ (1 if name in ('head-response', 'packet') else 256)
        divergence = f'operation={first+1} word={word_index} expected={expected_word} actual={actual_word} acknowledged=0\n'
        for producer in ('native', 'vcs-dpi'):
            for backend in ('native', 'vcs-dpi'):
                corruptions.append(invoke(backend, 'restore', f'{producer}-{backend}-{name}-corrupt', producer, cut,
                                          **{('image' if owner == 'write' else 'queue'): path}, code=2,
                                          expected_divergence=divergence))
    commands.extend(corruptions)
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'source changed during memif verification')
    report = dict(status='passed', scope='memif write child and serial FIFOs; HTIF/CPU admission pending',
                  source_inputs=bindings, commands=commands, continuations=continuations, cases=cases,
                  invalids=invalids, corruptions=corruptions, level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(summary=str(path), **audit(path)), indent=2))


if __name__ == '__main__':
    main()
