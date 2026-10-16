"""Actual installed syscall reads through production memif; component readbacks.

An independent byte/packet oracle checks every suspended reader and FIFO word.
This deliberately does not restore the unowned syscall, descriptor or context.
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
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf
from tools.checkpoint_formats.tests.verify_tsi_memif_read_vcs import reader, child, serial, initial, words

SPECS = [(0, 0), (0, 8), (7, 1), (1, 7), (7, 9), (0, 1023), (0, 1024), (3, 1025), (7, 2057)] + [(r, 64) for r in range(8)]
MAILBOX, MAGIC = 0x80002000, 0x80004000
FLUSHES = (0, 0x1280001000)


def oracle(flush):
    """Expand installed head/tail/body order, protocol words and peer scheduling."""
    items, output = [], bytearray()

    def write(a, data):
        return (1, a, len(data), data)

    def read(a, data, r0=None, r1=None, prefix=()):
        items.append(dict(packets=[*prefix, (0, a, len(data), b'')], reply=data,
                          r0=r0 or reader(), r1=r1 or reader()))

    def memread(a, data, memory, prefix=()):
        size, residue = len(data), a % 8
        head = min(size, 8-residue) if residue else 0
        tail = (size-head) % 8
        result = bytearray(size)
        chunks = ([(1, a & ~7, 8, 0, residue, head, 0)] if head else [])
        if tail:
            chunks.append((2, a+size-tail, 8, size-tail, 0, tail, 0))
        chunks += [(3, a+head+pos, min(1024, size-head-tail-pos), head+pos, 0,
                    min(1024, size-head-tail-pos), pos) for pos in range(0, size-head-tail, 1024)]
        for phase, address, n, offset, first, count, cursor in chunks:
            payload = memory(address, n)
            r0 = reader(phase, a, cursor, result, child(2, address, n))
            r1 = reader(phase, a, cursor, result, child(2, address, n, [int.from_bytes(payload[:4], 'little')]))
            read(address, payload, r0, r1, prefix)
            result[offset:offset+count] = payload[first:first+count]
            prefix = ()

    prefix = ()
    for index, (residue, size) in enumerate(SPECS):
        a = 0x1280003000 + index*0x10000 + residue
        payload = bytes(initial(a+i) for i in range(size))
        output.extend(payload)
        read(MAILBOX, MAGIC.to_bytes(8, 'little'), prefix=prefix)
        request = words(64, 1, a, size, 0, 0, 0, 0)
        memread(MAGIC, request, lambda addr, n: request[addr-MAGIC:addr-MAGIC+n],
                prefix=[write(MAILBOX, bytes(8))])
        memread(a, payload, lambda addr, n: bytes(initial(addr+i) for i in range(n)))
        result = words(size, 1, a, size, 0, 0, 0, 0)
        read(MAILBOX+8, bytes(8), prefix=[write(MAGIC, result)])
        prefix = [write(MAILBOX+8, words(1))]
    read(MAILBOX, words(1), prefix=prefix)
    items.append(dict(packets=[write(MAILBOX, bytes(8))], reply=None, r0=reader(), r1=reader()))

    for item in items:
        packets = []
        for command, a, n, data in item['packets']:
            if flush:
                packets += [write(flush, words(base)) for base in range(a & ~63, a+n, 64)]
            packets.append((command, a, n, data))
        item['packets'] = packets

    def encode(packets):
        return [v for command, a, n, data in packets for v in
                [command, a & 0xffffffff, a >> 32, n//4-1, 0,
                 *[int.from_bytes(data[i:i+4], 'little') for i in range(0, len(data), 4)]]]

    states, events, ticks = [], [], 0
    requests, responses, image = encode(items[0]['packets']), [], items[0]['r0']

    def snapshot():
        states.append((ticks, image, serial(requests, responses)))

    for index, item in enumerate(items):
        for command, a, n, data in item['packets']:
            del requests[:2]
            snapshot()
            del requests[:3+len(data)//4]
            snapshot()
            events.append(f'{ticks} '+('WRITE' if command else 'READ')+f' {a} {n}'+(' '+data.hex() if command else ''))
        if item['reply'] is None:
            break
        payload = item['reply']
        responses.append(int.from_bytes(payload[:4], 'little'))
        snapshot()
        responses.clear()
        image = item['r1']
        ticks += 1
        snapshot()
        responses.extend(int.from_bytes(payload[i:i+4], 'little') for i in range(4, len(payload), 4))
        snapshot()
        responses.clear()
        requests, image = encode(items[index+1]['packets']), items[index+1]['r0']
        ticks += 1
        snapshot()
    return events, states, bytes(output), ticks


def audit(path):
    path = path.resolve()
    report = json.loads(path.read_text())
    out = path.parent
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'], 'wrong production-reader scope')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'changed production-reader artifacts')
    for p, digest in report['artifact_sha256'].items():
        require(file_sha(p) == digest, 'changed production-reader artifact '+p)
    bindings = {b['path']: b for b in report['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed production-reader snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    total, active = 0, 0
    oracles = {flush: oracle(flush) for flush in FLUSHES}
    for flush in FLUSHES:
        events, states, output, ticks = oracles[flush]
        for backend in ('native', 'vcs-dpi'):
            source = out/f'{backend}-capture-{flush}'
            require((source/'events.txt').read_text().splitlines() == events, 'changed actual syscall packet data/order/host timing')
            require((source/'actual-syswrite.bin').read_bytes() == output, 'actual installed sys_write received wrong bytes')
            require((source/'cuts.txt').read_text().splitlines() == [f'{c} {t} {int(r != reader())}' for c, (t, r, q) in enumerate(states)], 'wrong syscall cut/tick sequence')
            for cut, (_, r, q) in enumerate(states):
                require((source/f'cut-{cut}.read').read_bytes() == r and (source/f'cut-{cut}.serial').read_bytes() == q, 'actual complete production owner differs '+str((flush, backend, cut)))
            count = sum(r != reader() for _, r, _ in states)
            require((source/'result.txt').read_text() == f'reads={len(SPECS)*2} syscalls={len(SPECS)} cuts={len(states)} active={count} host_ticks={ticks} startup_loadmem=1 syscall_parent_owned=0 cpu_edges=0\n', 'ordinary syscall execution incomplete')
            total += len(states)
            active += count
    expected = {(p, b, f, c) for f in FLUSHES for p in ('native', 'vcs-dpi') for b in ('native', 'vcs-dpi')
                for c, (_, r, _) in enumerate(oracles[f][1]) if r != reader()}
    require(len(report['readbacks']) == len(expected) and {(c['producer'], c['backend'], c['flush'], c['cut']) for c in report['readbacks']} == expected, 'incomplete production component readbacks')
    for case in report['readbacks']:
        _, r, q = oracles[case['flush']][1][case['cut']]
        dest = Path(case['destination'])
        require((dest/'preedge.read').read_bytes() == r and (dest/'preedge.serial').read_bytes() == q, 'fresh production reader/FIFO readback differs')
        require('PRODUCTION_READER_READBACK context_entries=0 target_services=0 target_edges=0' in Path(case['log']).read_text(), 'readback entered unowned caller')
    for command in report['commands']:
        log = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and log.rstrip().endswith('exit=0'), 'unbound production native/VCS command')
        require(not any(x in log for x in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'production sanitizer failure')
    return dict(status='passed', actual_syscalls=4*len(SPECS), complete_source_cuts=total, active_source_cuts=active,
                fresh_component_readbacks=len(expected), level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path)
    p.add_argument('--audit', type=Path)
    args = p.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit), indent=2))
        return
    require(args.out and args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    source, sv = (TESTS/n for n in ('tsi_memif_read_fesvr.cc', 'tsi_memif_read_fesvr_tb.sv'))
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc', TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc']
    inputs = [*sources, sv, Path(__file__), TESTS/'verify_tsi_memif_read_vcs.py', TESTS/'verify_tsi_host_control_fesvr_vcs.py',
              TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py', TESTS/'verify_firesim_tsi_loadmem_vcs.py',
              FESVR/'lib/libfesvr.a', *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')), *overlay_inputs(),
              *sorted((FESVR/'include/fesvr').glob('*.h')), CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h',
              ROOT/'tools/checkpoint_formats/retained_evidence.py', ROOT/'tools/checkpoint_formats/evidence.py',
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
        result = dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log))
        commands.append(result)
        return result

    library = build_overlay(out, execute)
    native, simv = out/'read-fesvr-native', out/'simv'
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
             *sources, library, '-lpthread', '-o', native], out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps', '-top', 'tsi_memif_read_fesvr_tb',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_MEMIF_READ_FESVR_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread', '-o', simv, sv, *sources], out/'vcs-build.log')
    (out/'polling.elf').write_bytes(polling_elf())

    def invoke(backend, mode, name, source, flush, **extra):
        dest = out/name
        values = list(map(str, (mode, source, dest, flush)))
        argv = [native, *values] if backend == 'native' else [simv, '-no_save', *['+'+k+'='+v for k, v in zip(('mode', 'source', 'destination', 'flush'), values)]]
        result = execute(argv, out/(name+'.log'))
        return dict(result, backend=backend, flush=flush, destination=str(dest), **extra)

    for flush in FLUSHES:
        for backend in ('native', 'vcs-dpi'):
            invoke(backend, 'capture', f'{backend}-capture-{flush}', out/'polling.elf', flush)
    jobs = [(b, 'readback', f'{p}-{b}-{f}-cut-{c}', out/f'{p}-capture-{f}/cut-{c}', f, p, c)
            for f in FLUSHES for p in ('native', 'vcs-dpi') for b in ('native', 'vcs-dpi')
            for c, (_, r, _) in enumerate(oracle(f)[1]) if r != reader()]
    with ThreadPoolExecutor(max_workers=8) as pool:
        readbacks = list(pool.map(lambda j: invoke(*j[:5], producer=j[5], cut=j[6]), jobs))
    for b in bindings:
        require(file_sha(b['path']) == b['sha256'], 'source changed during production reader test')
    report = dict(status='passed', scope='production installed-syscall reader/FIFO only; full syscall/context/CPU restore pending',
                  source_inputs=bindings, commands=commands, readbacks=readbacks, level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(summary=str(path), **audit(path)), indent=2))


if __name__ == '__main__':
    main()
