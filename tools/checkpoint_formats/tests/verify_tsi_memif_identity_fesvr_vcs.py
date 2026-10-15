"""Audit write-child images from actual installed-HTIF BCD identity dispatch.

Ordinary host execution and fresh child-only readback; no CPU admission.
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
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf
from tools.checkpoint_formats.tests.fesvr_overlay import build_overlay, overlay_inputs
from tools.checkpoint_formats.tests.verify_tsi_memif_write_vcs import writer, reader, serial, initial
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import config, words

TOHOST, FROMHOST = 0x80002000, 0x80002008


def identity_image(w):
    phase = 0 if w == writer() else 1
    command = 0
    if phase:
        address = int.from_bytes(w[72:80], 'little')
        payload = w[96:160].rstrip(b'\0')
        require(payload in (b'read', b'write', b'bcd', b''), 'unexpected BCD identity payload')
        what = {b'read': 0, b'write': 1, b'bcd': 255, b'': 2}[payload]
        command = (1 << 56) | (255 << 48) | (address << 8) | what
    return config(29, 1, 255, 64, 8, 1024)+words(phase, command)


def scenario(flush):
    plan, states = [], []
    w, requests, responses = writer(), [], []

    def snapshot():
        states.append((w, serial(requests, responses)))

    def step(line):
        plan.append(line)
        snapshot()

    def raw(command, address, size, data=b''):
        requests.extend([command, address & 0xffffffff, address >> 32, size//4-1, 0])
        if command:
            requests.extend(int.from_bytes(data[i:i+4], 'little') for i in range(0, size, 4))

    def packet(command, address, size, data=b''):
        if flush:
            for base in range(address & ~63, address+size, 64):
                raw(1, flush, 8, base.to_bytes(8, 'little'))
        raw(command, address, size, data)

    def drain():
        # A partially consumed header is a separate retained operation cut.
        for _ in range(2):
            if not requests:
                break
            n = min(3, len(requests)) if _ == 0 else len(requests)
            words = requests[:n]
            del requests[:n]
            step('PACKET '+' '.join(map(str, words)))

    def send(value):
        responses.append(value)
        step('SEND '+str(value))

    packet(0, TOHOST, 8)
    snapshot()
    drain()
    for residue in range(8):
        for what, name in ((0, b'read'), (1, b'write'), (255, b'bcd'), (2, b'')):
            address = 0x1280003000 + residue*0x10000 + what*128 + residue
            data = name.ljust(64, b'\0')
            value = (1 << 56) | (255 << 48) | (address << 8) | what
            send(value & 0xffffffff)
            responses.clear()
            step('TICK')
            send(value >> 32)
            responses.clear()
            packet(1, TOHOST, 8, bytes(8))
            if residue:
                head = 8-residue
                start = address & ~7
                packet(0, start, 8)
                w = writer(1, address, 0, data, reader(2, start))
                step('TICK')
                drain()
                original = bytes(initial(start+i) for i in range(8))
                a, b = (int.from_bytes(original[i:i+4], 'little') for i in (0, 4))
                send(a)
                responses.clear()
                w = writer(1, address, 0, data, reader(2, start, [a]))
                step('TICK')
                send(b)
                responses.clear()
                merged = original[:residue]+data[:head]
                packet(1, start, 8, merged)
                tail_address = address+head+56
                packet(0, tail_address, 8)
                w = writer(2, address, 0, data, reader(2, tail_address))
                step('TICK')
                drain()
                original = bytes(initial(tail_address+i) for i in range(8))
                a, b = (int.from_bytes(original[i:i+4], 'little') for i in (0, 4))
                send(a)
                responses.clear()
                w = writer(2, address, 0, data, reader(2, tail_address, [a]))
                step('TICK')
                send(b)
                responses.clear()
                packet(1, tail_address, 8, data[head+56:]+original[residue:])
                packet(1, address+head, 56, data[head:head+56])
            else:
                packet(1, address, 64, data)
            packet(0, FROMHOST, 8)
            w = writer()
            step('TICK')
            drain()
            send(0)
            responses.clear()
            step('TICK')
            send(0)
            responses.clear()
            packet(1, FROMHOST, 8, ((1 << 56) | (255 << 48) | 1).to_bytes(8, 'little'))
            packet(0, TOHOST, 8)
            step('TICK')
            drain()
    return plan, states


def audit(path):
    path = path.resolve()
    report = json.loads(path.read_text())
    out = path.parent
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'],
            'incorrect actual memif acceptance scope')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path},
            'changed actual memif artifact membership')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed actual memif artifact '+name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed actual memif source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    count = active = 0
    for flush in (0, 0x10000000):
        plan, states = scenario(flush)
        require((out/f'plan-{flush}.txt').read_text().splitlines() == plan, 'changed actual dispatch oracle')
        expected_active = sum(w != writer() for w, _ in states)
        for backend in ('native', 'vcs-dpi'):
            name = f'{backend}-capture-{flush}'
            require(f'ACTUAL_IDENTITY cuts={len(states)} active_child_cuts={expected_active} polling_guards={expected_active} source_exit=0 cpu_edges=0'
                    in (out/(name+'.log')).read_text(), 'ordinary source did not finish or active caller admitted')
            for cut, (w, q) in enumerate(states):
                require((out/name/f'cut-{cut}.write').read_bytes() == w and
                        (out/name/f'cut-{cut}.serial').read_bytes() == q and
                        (out/name/f'cut-{cut}.identity').read_bytes() == identity_image(w),
                        'actual complete caller/child/queue bytes differ')
            count += len(states)
            active += expected_active
    expected_cases = {(p, b, f, c) for f in (0, 0x10000000) for p in ('native', 'vcs-dpi')
                      for b in ('native', 'vcs-dpi') for c, (w, _) in enumerate(scenario(f)[1]) if w != writer()}
    require(len(report['readbacks']) == len(expected_cases) and
            {(c['producer'], c['backend'], c['flush'], c['cut']) for c in report['readbacks']} == expected_cases,
            'missing actual child readback backend/cut pairing')
    for case in report['readbacks']:
        source, dest = Path(case['source']), Path(case['destination'])
        require((dest/'preedge.write').read_bytes() == Path(str(source)+'.write').read_bytes() and
                (dest/'preedge.serial').read_bytes() == Path(str(source)+'.serial').read_bytes() and
                (dest/'preedge.identity').read_bytes() == Path(str(source)+'.identity').read_bytes(),
                'actual fresh complete readback differs')
        require('COMPLETE_CHILD_READBACK context_entries=0 target_services=0 target_edges=0' in Path(case['log']).read_text(),
                'fresh child restore entered services')
    pids = []
    for c in report['commands']:
        log = Path(c['log']).read_text()
        require(c['argv'][:2] == ['bash', '-lc'] and c['argv'][2].startswith(ENVIRONMENT) and log.rstrip().endswith('exit=0'),
                'unbound actual memif native environment/result')
        require(not any(s in log for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'actual sanitizer failure')
        pids.append(int(re.search(r'fresh_process_pid=(\d+)', log)[1]))
    require(len(pids) == len(set(pids)), 'reused actual readback process')
    return dict(status='passed', ordinary_identity_commands=128, captured_component_cuts=count,
                active_child_cuts=active, polling_admission_rejections=active,
                fresh_child_readbacks=len(report['readbacks']), complete_owner_readbacks=3*len(report['readbacks']),
                level1_verified=False, level2_verified=False)


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
    source, sv = (TESTS/n for n in ('tsi_memif_identity_fesvr.cc', 'tsi_memif_identity_fesvr_tb.sv'))
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc', TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc']
    inputs = [*sources, sv, Path(__file__), TESTS/'verify_tsi_memif_write_vcs.py', TESTS/'verify_tsi_host_control_fesvr_vcs.py',
              TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py', TESTS/'verify_firesim_tsi_loadmem_vcs.py',
              FESVR/'lib/libfesvr.a', *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')),
              *sorted((FESVR/'include/fesvr').glob('*.h')), *overlay_inputs(), CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h',
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
        return dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log), expected_exit=0)

    def build(argv, log):
        commands.append(execute(argv, log))

    library = build_overlay(out, build)
    native, simv = out/'identity-native', out/'simv'
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    build([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           *sources, library, '-lpthread', '-o', native], out/'native-build.log')
    build([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps', '-top', 'tsi_memif_identity_fesvr_tb',
           '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_MEMIF_IDENTITY_DPI',
           '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread', '-o', simv, sv, *sources], out/'vcs-build.log')
    (out/'polling.elf').write_bytes(polling_elf())
    (out/'terminal.bin').write_bytes(b'A\0\xff')

    def invoke(backend, mode, name, flush, producer='native', cut=0):
        source = out/(f'{producer}-capture-{flush}')/f'cut-{cut}'
        dest = out/name
        values = list(map(str, [mode, out/'polling.elf', out/'terminal.bin', out/f'plan-{flush}.txt', dest, f'{flush:x}', source]))
        argv = [native, *values] if backend == 'native' else [simv, '-no_save', *[
            '+'+k+'='+v for k, v in zip(('mode', 'elf', 'input', 'plan', 'out', 'flush', 'source'), values)]]
        return dict(execute(argv, out/(name+'.log')), backend=backend, producer=producer, cut=cut, flush=flush,
                    source=str(source), destination=str(dest))

    jobs = []
    for flush in (0, 0x10000000):
        plan, states = scenario(flush)
        (out/f'plan-{flush}.txt').write_text('\n'.join(plan)+'\n')
        for backend in ('native', 'vcs-dpi'):
            commands.append(invoke(backend, 'capture', f'{backend}-capture-{flush}', flush))
        jobs.extend((b, 'readback', f'{p}-{b}-readback-{flush}-{c}', flush, p, c)
                    for p in ('native', 'vcs-dpi') for b in ('native', 'vcs-dpi')
                    for c, (w, _) in enumerate(states) if w != writer())
    with ThreadPoolExecutor(max_workers=4) as pool:
        readbacks = list(pool.map(lambda job: invoke(*job), jobs))
    commands.extend(readbacks)
    for b in bindings:
        require(file_sha(b['path']) == b['sha256'], 'source changed during actual identity checks')
    report = dict(status='passed', source_inputs=bindings, commands=commands, readbacks=readbacks,
                  level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(summary=str(path), **audit(path)), indent=2))


if __name__ == '__main__':
    main()
