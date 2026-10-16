"""Installed direct-exit/stop component, independently audited at host cuts.

Fresh destinations restore the explicit component and project its installed
exit/stop behavior; they do not restore the session, poll caller or CPU.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
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
from tools.checkpoint_formats.tests.verify_tsi_memif_read_vcs import child, serial

PAYLOADS = (1, 3, 0x7fffffff, 0x80000001, 0xffffffff, 0x100000001, 0x800000000001, 0xffffffffffff)
FLUSHES = (0, 0x1280001000)
TOHOST, FROMHOST, BCD, RESPONSE = 0x80002000, 0x80002008, 1 << 56, (1 << 56) | 0x141
OWNERS = ('exit', 'poll', 'read', 'serial', 'terminal')


def exit_image(phase=0, raw=0):
    return config(31, 1, 32, 0)+words(phase, raw & 0xffffffff)


def status(raw):
    raw &= 0xffffffff
    return (raw if raw < 0x80000000 else raw-0x100000000)//2


def oracle(raw, flush):
    """Expand the original packet protocol, FIFO consumption and poll phases."""
    packets = [[(0, TOHOST, 0)], [(1, TOHOST, 0), (0, FROMHOST, 0)],
               [(0, TOHOST, 0)], [(1, TOHOST, 0), (0, FROMHOST, 0)], [(1, FROMHOST, RESPONSE)]]
    if flush:
        packets = [[p for command, a, value in item for p in
                    ((1, flush, a & ~63), (command, a, value))] for item in packets]
    replies = (BCD, 7, raw, 0)
    addresses = (TOHOST, FROMHOST, TOHOST, FROMHOST, 0)
    polls = [(1, ()), (6, (RESPONSE,)), (1, (RESPONSE,)), (6, (RESPONSE,)), (8, ())]
    events, states = [], []
    tick, index, collected, queued, requests = 0, 0, [], [], []

    def encode(item):
        return [v for command, a, value in item for v in
                (command, a & 0xffffffff, a >> 32, 1, 0,
                 *([value & 0xffffffff, value >> 32] if command else []))]

    def snapshot():
        p, responses = polls[index]
        phase = 0 if index < 3 else 1 if index == 3 else 2
        images = dict(exit=exit_image(phase, raw if phase else 0),
                      poll=config(24, TOHOST, FROMHOST, 1048576)+words(p, 0, len(responses), *responses),
                      read=child(2, addresses[index], 8, collected) if index < 4 else child(),
                      serial=serial(requests, queued),
                      terminal=config(27, 1, 1048576, 1)+b'A'+words(int(index > 0), 0))
        states.append((tick, int(index == 4), status(raw) if phase else 0, images))

    requests = encode(packets[0])
    snapshot()
    for index in range(5):
        for command, a, value in packets[index]:
            del requests[:2]; snapshot()
            del requests[:5 if command else 3]; snapshot()
            events.append(f'{tick} '+('W' if command else 'R')+f' {a} {value}')
        if index == 4:
            break
        value = replies[index]
        queued = [value & 0xffffffff]; snapshot()
        queued, collected = [], [value & 0xffffffff]; tick += 1; snapshot()
        queued = [value >> 32]; snapshot()
        queued, collected = [], []; tick += 1
        index += 1
        requests = encode(packets[index]); snapshot()
    return events, states


def malformed():
    good = exit_image(1, 1)
    result = [good[:n] for n in range(len(good))]+[good+b'\0']
    for i in range(len(config(31, 1, 32, 0))):
        b = bytearray(good); b[i] ^= 1; result.append(bytes(b))
    result += [exit_image(3, 1), exit_image(0, 1), exit_image(1, 0), exit_image(2, 2),
               config(31, 1, 32, 0)+words(1, 0x100000001)]
    return result


def audit(path):
    path = path.resolve(); r = json.loads(path.read_text()); out = path.parent
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong exit component scope')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'exit artifact membership changed')
    for p, digest in r['artifact_sha256'].items():
        require(file_sha(p) == digest, 'exit artifact changed '+p)
    bindings = {b['path']: b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'exit snapshot changed')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    source_cuts, readbacks, requested = 0, 0, 0
    for raw in PAYLOADS:
        for flush in FLUSHES:
            events, states = oracle(raw, flush)
            for backend in ('native', 'vcs-dpi'):
                source = out/f'{backend}-capture-{raw}-{flush}'
                require((source/'events.txt').read_text().splitlines() == events, 'exit packet/timing mismatch')
                require((source/'cuts.txt').read_text().splitlines() ==
                        [f'{i} {t} {done} {code}' for i, (t, done, code, images) in enumerate(states)], 'exit cut/installed status mismatch')
                require((source/'reference.txt').read_text() == f'1 1 {status(raw)}\n', 'installed exit reference mismatch')
                require((source/'aggregate-rejections.txt').read_text() ==
                        str(sum(im['exit']==exit_image(1,raw) for _,_,_,im in states))+'\n', 'active exit omitted from polling aggregate')
                for cut, (_, done, code, images) in enumerate(states):
                    source_cuts += 1
                    requested += images['exit'] == exit_image(1, raw)
                    for owner in OWNERS:
                        require((source/f'cut-{cut}.{owner}').read_bytes() == images[owner], f'incomplete exit source {raw}/{flush}/{cut}/{owner}')
                    for dest in ('native', 'vcs-dpi'):
                        target = out/f'{backend}-{dest}-{raw}-{flush}-cut-{cut}'
                        require((target/'pre-service.exit').read_bytes() == images['exit'], 'incomplete fresh exit readback')
                        phase = int.from_bytes(images['exit'][56:64], 'little')
                        require((target/'bound.txt').read_text() == f'{int(phase>0)} {done} {code}\n', 'wrong installed exit projection')
                        require((target/'final.exit').read_bytes() == exit_image(2, raw) and
                                (target/'final.txt').read_text() == f'1 1 {status(raw)}\n', 'exit component continuation mismatch')
                        readbacks += 1
    for b in ('native', 'vcs-dpi'):
        require((out/f'{b}-internal/internal.txt').read_text() == 'checks=14 cpu_edges=0\n', 'missing exit service guards')
        for which in ('signal-int', 'signal-term', 'exit', 'stop', 'signature'):
            require((out/f'{b}-unowned-{which}/unowned.txt').read_text() ==
                    f'{which} rejected=1 serial_unchanged=1 context_entries=0\n', 'unowned lifecycle accepted')
        for i, payload in enumerate(malformed()):
            require((out/f'bad-{i}.exit').read_bytes() == payload and
                    (out/f'{b}-reject-{i}/unchanged.exit').read_bytes() == exit_image(), 'non-atomic malformed exit rejection')
        for raw in PAYLOADS:
            target = out/f'{b}-corrupt-{raw}'
            require((target/'pre-service.exit').read_bytes() == exit_image(1, raw ^ 2), 'corruption not loaded')
            require((target/'first-divergence.txt').read_text() ==
                    f'FIRST_DIVERGENCE boundary=0 signal=exit_code expected={status(raw)} actual={status(raw^2)} acknowledged=0 stop_services=0\n',
                    'first exit divergence mismatch')
            require(not (target/'final.exit').exists(), 'divergent stop acknowledged')
    for command in r['commands']:
        log = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and log.rstrip().endswith('exit=0'), 'unbound exit native command')
        require(not any(e in log for e in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'exit sanitizer failure')
    return dict(status='passed', source_cuts=source_cuts, complete_source_images=source_cuts*5,
                queued_response_exit_cuts=requested, fresh_component_projections=readbacks,
                invalid_image_processes=2*len(malformed()), unowned_lifecycle_processes=10,
                first_divergence_cases=16, level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path); p.add_argument('--audit', type=Path)
    a = p.parse_args()
    if a.audit:
        print(json.dumps(audit(a.audit), indent=2)); return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    source, sv = (TESTS/n for n in ('tsi_htif_exit_fesvr.cc', 'tsi_htif_exit_fesvr_tb.sv'))
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc', TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc']
    inputs = [*sources, sv, Path(__file__), TESTS/'verify_tsi_memif_read_vcs.py', TESTS/'verify_tsi_host_control_fesvr_vcs.py',
              TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py', TESTS/'verify_firesim_tsi_loadmem_vcs.py',
              FESVR/'lib/libfesvr.a', *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')), *overlay_inputs(),
              *sorted((FESVR/'include/fesvr').glob('*.h')), CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h',
              ROOT/'tools/checkpoint_formats/retained_evidence.py', ROOT/'tools/checkpoint_formats/evidence.py',
              ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots = out/'sources'; snapshots.mkdir(); bindings, commands = [], []
    for path in dict.fromkeys(inputs):
        digest = file_sha(path); snapshot = snapshots/digest
        if not snapshot.exists(): shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    def execute(argv, log):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        run(command, log, cwd=out); commands.append(dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log)))
    library = build_overlay(out, execute)
    native, simv = out/'exit-native', out/'simv'
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
             *sources, library, '-lpthread', '-o', native], out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps', '-top', 'tsi_htif_exit_fesvr_tb',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_HTIF_EXIT_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread', '-o', simv, sv, *sources], out/'vcs-build.log')
    (out/'polling.elf').write_bytes(polling_elf())
    def invoke(backend, mode, name, source, raw=1, flush=0):
        values = list(map(str, (mode, source, out/name, raw, flush)))
        argv = [native, *values] if backend == 'native' else [simv, '-no_save', *['+'+k+'='+v for k,v in zip(('mode','source','destination','raw','flush'), values)]]
        execute(argv, out/(name+'.log'))
    for b in ('native','vcs-dpi'):
        invoke(b, 'internal', b+'-internal', out/'polling.elf')
        for which in ('signal-int','signal-term','exit','stop','signature'):
            invoke(b, 'unowned', b+'-unowned-'+which, out/'polling.elf', which)
        for raw in PAYLOADS:
            for flush in FLUSHES:
                invoke(b, 'capture', f'{b}-capture-{raw}-{flush}', out/'polling.elf', raw, flush)
    jobs = [(b, 'project', f'{p}-{b}-{r}-{f}-cut-{c}', out/f'{p}-capture-{r}-{f}/cut-{c}.exit', r, f)
            for p in ('native','vcs-dpi') for b in ('native','vcs-dpi') for r in PAYLOADS for f in FLUSHES
            for c in range(len(oracle(r,f)[1]))]
    for i, image in enumerate(malformed()):
        (out/f'bad-{i}.exit').write_bytes(image)
        jobs += [(b,'reject',f'{b}-reject-{i}',out/f'bad-{i}.exit',1,0) for b in ('native','vcs-dpi')]
    for raw in PAYLOADS:
        (out/f'corrupt-{raw}.exit').write_bytes(exit_image(1,raw^2))
        jobs += [(b,'corrupt',f'{b}-corrupt-{raw}',out/f'corrupt-{raw}.exit',raw,0) for b in ('native','vcs-dpi')]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda j: invoke(*j), jobs))
    for b in bindings:
        require(file_sha(b['path']) == b['sha256'], 'source changed during exit component verification')
    report = dict(status='passed', scope='direct-exit/stop component projection; complete HTIF/CPU restore pending',
                  source_inputs=bindings, commands=commands, level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(summary=str(path), **audit(path)), indent=2))


if __name__ == '__main__':
    main()
