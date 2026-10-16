"""Atomic preparation of twelve production TSI polling components, native and VCS.

No host context is resumed after preparation. CPU acceptance remains pending.
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
from tools.checkpoint_formats.tests.fesvr_overlay import overlay_inputs, build_overlay
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf
from tools.checkpoint_formats.tests.verify_tsi_memif_identity_fesvr_vcs import identity_image
from tools.checkpoint_formats.tests.verify_tsi_memif_write_vcs import writer, reader, initial

NAMES = ('poll', 'program', 'init', 'host', 'read', 'serial', 'loadmem-read', 'loadmem-queues', 'bcd', 'terminal', 'identity', 'write')
READ = 1 << 56
TOHOST, FROMHOST = 0x80002000, 0x80002008
INPUT = b'A\0\xff'


def scenario(identity=False):
    """Independent byte oracle for the installed caller's explicit operations."""
    phase, host_phase, remaining, flags = 1, 0, 0, 6
    command, w = 0, writer()
    address, partial, requests, responses = TOHOST, [], [0, TOHOST, 0, 1, 0], []
    queue, pending, cursor, output = [], 0, 0, b''
    plan, images = [], []

    def snapshot():
        images.append(dict(
            poll=config(24, TOHOST, FROMHOST, 1048576)+words(phase, command, len(queue), *queue),
            program=config(23, 1, 0)+words(3), init=config(21, 0, 0)+words(8, 0, 0),
            host=config(18, 3)+words(host_phase, remaining, flags),
            read=config(20, 1024, 4, 2, 2)+(words(2, address, 8, len(partial), *partial) if address else words(0, 0, 0, 0)),
            serial=config(19, 4, 2, 2, 1024)+words(len(requests), *requests, len(responses), *responses),
            **{'loadmem-read': config(14, 4096, 4)+words(0, 0, 0, 0),
               'loadmem-queues': config(16, 4096, 4)+words(0, 0, 0, 0, 0, 0, 0)},
            bcd=config(26, 1, 1048576)+words(pending, *([READ]*pending)),
            terminal=config(27, 1, 1048576, 3)+INPUT+words(cursor, len(output))+output,
            identity=identity_image(w), write=w))

    def step(line):
        plan.append(line)
        snapshot()

    def packet(count=None):
        count = len(requests) if count is None else count
        expected = requests[:count]
        del requests[:count]
        step('PACKET '+' '.join(map(str, expected)))

    def send(value):
        responses.append(value)
        step('SEND '+str(value))

    def read_partial():
        nonlocal partial
        partial = [responses.pop(0)]
        step('TICK')

    snapshot()
    packet(2)  # A partially consumed request is an owned transport cut.
    packet()
    send(0)
    read_partial()
    send(0)
    responses.clear()
    phase, host_phase, remaining, address, partial = 4, 1, 2, 0, []
    step('TICK')
    for remaining in (1, 0):
        step('TICK')
    phase, host_phase, remaining, flags, address = 1, 0, 0, 7, TOHOST
    requests = [0, TOHOST, 0, 1, 0]
    step('TICK')
    packet()

    for ch in INPUT:
        send(0)
        read_partial()
        send(0x01000000)
        responses.clear()
        partial, phase, address = [], 6, FROMHOST
        queue.append(READ | 0x100 | ch)
        cursor += 1
        requests = [1, TOHOST, 0, 1, 0, 0, 0, 0, FROMHOST, 0, 1, 0]
        step('TICK')
        packet(4)
        packet()
        send(0)
        read_partial()
        send(0)
        responses.clear()
        requests = [1, FROMHOST, 0, 1, 0, queue.pop(0) & 0xffffffff, 0x01000000, 0, TOHOST, 0, 1, 0]
        partial, phase, address = [], 1, TOHOST
        step('TICK')
        packet()

    send(90)
    send(0x01010000)
    responses.clear()
    output = b'Z'
    requests = [1, TOHOST, 0, 1, 0, 0, 0, 0, TOHOST, 0, 1, 0]
    step('TICK')
    packet()
    for _ in range(2):
        send(0)
        send(0x01000000)
        responses.clear()
        pending += 1
        requests = [1, TOHOST, 0, 1, 0, 0, 0, 0, TOHOST, 0, 1, 0]
        step('TICK')
        packet()
    if identity:
        for residue in range(8):
            for what, text in ((0, b'read'), (1, b'write'), (255, b'bcd'), (2, b'')):
                destination = 0x1280003008 + 0x10000*residue + 64*what + residue
                value = (1 << 56) | (255 << 48) | (destination << 8) | what
                data = text.ljust(64, b'\0')
                send(value & 0xffffffff)
                read_partial()
                send(value >> 32)
                responses.clear()
                partial, address = [], 0
                requests = [1, TOHOST, 0, 1, 0, 0, 0]
                if residue:
                    phase, command = 3, value
                    head, start = 8-residue, destination & ~7
                    requests += [0, start & 0xffffffff, start >> 32, 1, 0]
                    w = writer(1, destination, 0, data, reader(2, start))
                    step('TICK')
                    packet(10)  # Partially consumed merge-read header.
                    packet()
                    original = bytes(initial(start+i) for i in range(8))
                    low, high = (int.from_bytes(original[i:i+4], 'little') for i in (0, 4))
                    send(low)
                    responses.clear()
                    w = writer(1, destination, 0, data, reader(2, start, [low]))
                    step('TICK')
                    send(high)
                    responses.clear()
                    merged = original[:residue]+data[:head]
                    payload = [int.from_bytes(merged[i:i+4], 'little') for i in (0, 4)]
                    tail = destination+head+56
                    requests = [1, start & 0xffffffff, start >> 32, 1, 0, *payload,
                                0, tail & 0xffffffff, tail >> 32, 1, 0]
                    w = writer(2, destination, 0, data, reader(2, tail))
                    step('TICK')
                    packet(4)
                    packet()
                    original = bytes(initial(tail+i) for i in range(8))
                    low, high = (int.from_bytes(original[i:i+4], 'little') for i in (0, 4))
                    send(low)
                    responses.clear()
                    w = writer(2, destination, 0, data, reader(2, tail, [low]))
                    step('TICK')
                    send(high)
                    responses.clear()
                    merged = data[head+56:]+original[residue:]
                    payload = [int.from_bytes(merged[i:i+4], 'little') for i in (0, 4)]
                    body = data[head:head+56]
                    payload_body = [int.from_bytes(body[i:i+4], 'little') for i in range(0, 56, 4)]
                    body_address = destination+head
                    requests = [1, tail & 0xffffffff, tail >> 32, 1, 0, *payload,
                                1, body_address & 0xffffffff, body_address >> 32, 13, 0, *payload_body]
                else:
                    payload = [int.from_bytes(data[i:i+4], 'little') for i in range(0, 64, 4)]
                    requests += [1, destination & 0xffffffff, destination >> 32, 15, 0, *payload]
                queue.append((1 << 56) | (255 << 48) | 1)
                partial, phase, command, address, w = [], 6, 0, FROMHOST, writer()
                requests += [0, FROMHOST, 0, 1, 0]
                step('TICK')
                packet(10)
                packet()
                send(0)
                read_partial()
                send(0)
                responses.clear()
                response = queue.pop(0)
                requests = [1, FROMHOST, 0, 1, 0, response & 0xffffffff, response >> 32,
                            0, TOHOST, 0, 1, 0]
                partial, phase, address = [], 1, TOHOST
                step('TICK')
                packet()
    return plan, images


def audit(path):
    path = path.resolve()
    report = json.loads(path.read_text())
    out = path.parent
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'], 'wrong preparation scope')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'changed preparation artifact membership')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed preparation artifact '+name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed preparation source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    plan, images = scenario(report.get('aligned_identity', False))
    require((out/'polling.elf').read_bytes() == polling_elf() and (out/'terminal.bin').read_bytes() == INPUT, 'changed source configuration')
    require((out/'plan.txt').read_text() == '\n'.join(plan)+'\n', 'changed polling service plan')
    for backend in ('native', 'vcs-dpi'):
        capture = out/(backend+'-capture')
        require((capture/'output.bin').read_bytes() == b'Z', 'wrong source terminal execution')
        require(f'CAPTURE cuts={len(images)} owners=12 source_exit=0 cpu_edges=0' in (out/(backend+'-capture.log')).read_text(), 'source did not finish')
        for cut, expected in enumerate(images):
            for name in NAMES:
                require((capture/f'cut-{cut}.{name}').read_bytes() == expected[name], f'independent captured byte mismatch {backend}/{cut}/{name}')
    require(len(report['preparations']) == 4*len(images), 'missing backend/cut pairing')
    require(len({(c['producer'], c['backend'], c['cut']) for c in report['preparations']}) == 4*len(images), 'duplicate preparation pairing')
    for case in report['preparations']:
        dest = Path(case['destination'])
        for name in NAMES:
            require((dest/('preedge.'+name)).read_bytes() == images[case['cut']][name], 'incomplete prepared readback '+name)
        require((dest/'preedge.metadata').read_bytes() == Path(case['metadata']).read_bytes(), 'changed prepared metadata')
        require('PREPARATION_READBACK owners=12 target_edges=0 target_services=0 context_entries=0 guards=5' in Path(case['log']).read_text(), 'prepared caller executed')
    malformed = allocations = 0
    require(len(report['invalids']) == 4, 'missing negative backend pair')
    for case in report['invalids']:
        match = re.search(r'PREPARATION_ATOMIC malformed=(\d+) membership=61 cross=11 allocation_failures=(\d+) unchanged_on_failure=1 context_entries=0 target_edges=0', Path(case['log']).read_text())
        require(match and int(match[1]) == sum(len(v)+2 for v in images[-1].values()) and int(match[2]) >= 30, 'incomplete atomic negative coverage')
        malformed += int(match[1])
        allocations += int(match[2])
        for name in NAMES:
            require((Path(case['destination'])/('preedge.'+name)).read_bytes() == images[-1][name], 'incomplete restore after failure')
    pids = []
    for command in report['commands']:
        log = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and log.rstrip().endswith('exit=0'), 'unbound preparation native command/environment/result')
        require(not any(s in log for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'preparation sanitizer failure')
        pids.append(int(re.search(r'fresh_process_pid=(\d+)', log)[1]))
    require(len(pids) == len(set(pids)), 'reused preparation process')
    return dict(status='passed', fresh_twelve_owner_preparations=len(report['preparations']),
                complete_prepared_readbacks=12*(len(report['preparations'])+len(report['invalids'])),
                component_cuts=len(images), malformed_rejections=malformed, membership_rejections=244,
                cross_owner_or_config_rejections=44, allocation_failures=allocations,
                context_execution_guards=5*len(report['preparations']), level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--identity', action='store_true', help='also exercise aligned BCD identity writes')
    args = parser.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit), indent=2))
        return
    require(args.out and args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    source, sv, allocator = (TESTS/name for name in ('tsi_polling_prepare_fesvr.cc', 'tsi_polling_prepare_fesvr_tb.sv', 'tsi_terminal_allocations.cc'))
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc', TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc', allocator]
    library = FESVR/'lib/libfesvr.a'
    inputs = [*sources, sv, library, Path(__file__), TESTS/'verify_tsi_host_control_fesvr_vcs.py',
              TESTS/'verify_firesim_tsi_loadmem_vcs.py', TESTS/'verify_tsi_memif_identity_fesvr_vcs.py',
              TESTS/'verify_tsi_memif_write_vcs.py', TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py',
              ROOT/'tools/checkpoint_formats/retained_evidence.py', ROOT/'tools/checkpoint_formats/evidence.py',
              *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')), *sorted((FESVR/'include/fesvr').glob('*.h')),
              CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h', *overlay_inputs(),
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

    def execute(argv, log):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        run(command, log, cwd=out)
        return dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log), expected_exit=0)

    def build(argv, log):
        command = execute(argv, log)
        commands.append(command)
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')

    library = build_overlay(out, build)
    native, simv = out/'prepare-native', out/'simv'
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    build([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           *sources, library, '-lpthread', '-o', native], out/'native-build.log')
    build([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
           '-top', 'tsi_polling_prepare_fesvr_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
           '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_POLLING_PREPARE_DPI',
           '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread', '-o', simv, sv, *sources], out/'vcs-build.log')
    plan, events = scenario(args.identity)
    elf, terminal, plan_path = out/'polling.elf', out/'terminal.bin', out/'plan.txt'
    elf.write_bytes(polling_elf())
    terminal.write_bytes(INPUT)
    plan_path.write_text('\n'.join(plan)+'\n')

    def invoke(backend, mode, name, producer='native', cut=0):
        dest = out/name
        source = out/(producer+f'-capture/cut-{cut}')
        metadata = out/(producer+'-capture/startup.metadata')
        argv = [native, mode, elf, terminal, metadata, source, plan_path, dest] if backend == 'native' else [
            simv, '-no_save', '+mode='+mode, '+elf='+str(elf), '+terminal='+str(terminal), '+metadata='+str(metadata),
            '+source='+str(source), '+plan='+str(plan_path), '+destination='+str(dest)]
        return dict(execute(argv, out/(name+'.log')), backend=backend, producer=producer, cut=cut,
                    source=str(source), metadata=str(metadata), destination=str(dest))

    for backend in ('native', 'vcs-dpi'):
        commands.append(invoke(backend, 'capture', backend+'-capture'))
    jobs = [(backend, 'restore', f'{producer}-{backend}-cut-{cut}', producer, cut)
            for producer in ('native', 'vcs-dpi') for backend in ('native', 'vcs-dpi') for cut in range(len(events))]
    with ThreadPoolExecutor(max_workers=8) as pool:
        preparations = list(pool.map(lambda job: invoke(*job), jobs))
    commands.extend(preparations)
    invalids = []
    for producer in ('native', 'vcs-dpi'):
        for backend in ('native', 'vcs-dpi'):
            invalids.append(invoke(backend, 'invalid', f'{producer}-{backend}-invalid', producer, len(events)-1))
    commands.extend(invalids)
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'source changed during preparation checks')
    report = dict(status='passed', scope='twelve known polling components; no context or CPU continuation',
                  commands=commands, preparations=preparations, invalids=invalids, source_inputs=bindings,
                  aligned_identity=args.identity, level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(summary=str(path), **audit(path)), indent=2))


if __name__ == '__main__':
    main()
