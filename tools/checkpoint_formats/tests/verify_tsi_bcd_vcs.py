"""Fresh pending BCD continuations against installed FESVR; not CPU restore."""
import argparse
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
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf

READ = 0x0100000000000000


def states():
    pending = []
    result = [config(26, 1, 1048576) + words(0)]
    for event in range(1, 13):
        if event in (1, 3, 7):
            pending.append(READ | {1: 0x123, 3: 0xbeef, 7: 0x987}[event])
        if event in (5, 8, 11):
            pending.pop(0)
        result.append(config(26, 1, 1048576) + words(len(pending), *pending))
    return result


def suffix(trace, cut):
    if cut == 12:
        return b''
    return trace[trace.index(f'EVENT {cut+1}\n'.encode()):]


def first_difference(expected, actual):
    cycle = None
    for left, right in zip(expected.splitlines(), actual.splitlines()):
        if left.startswith(b'EVENT '):
            cycle = int(left.split()[1])
        if left != right:
            return dict(host_event=cycle, expected=left.decode(), actual=right.decode())
    require(expected != actual, 'semantic corruption did not diverge')
    return dict(host_event=cycle, expected='end', actual='length mismatch')


def audit(path):
    path = path.resolve(); out = path.parent; report = json.loads(path.read_text())
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'], 'wrong BCD scope')
    require(set(report['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'changed BCD evidence membership')
    for name, digest in report['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed BCD evidence ' + name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for binding in bindings.values():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed BCD source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    require((out/'polling.elf').read_bytes() == polling_elf(), 'changed installed-loader ELF')
    oracle = states(); trace = (out/'native-reference/events.log').read_bytes()
    require(trace == (out/'vcs-dpi-reference/events.log').read_bytes(), 'installed BCD references differ')
    last_response = f'RESPONSE {READ | 0x1ff}'
    require(trace.count(b'RESPONSE ') == 7 and (last_response+'\n').encode() in trace, 'missing installed BCD/identity responses')
    for backend in ('native', 'vcs-dpi'):
        require((out/(backend+'-reference/terminal-output.bin')).read_bytes() == b'Z', 'installed terminal output differs')
        require((out/(backend+'-capture/events.log')).read_bytes() == trace, 'owned BCD differs from installed execution')
        require((out/(backend+'-capture/terminal-output.bin')).read_bytes() == b'Z', 'owned terminal output differs')
        for cut, image in enumerate(oracle):
            require((out/f'{backend}-capture/cut-{cut}.bcd').read_bytes() == image, 'incomplete BCD queue capture')
        require('BCD_SERVICE_GUARDS active=6 interrupted=5 total=11' in (out/(backend+'-guards.log')).read_text(), 'BCD service guard failed')
        require('ACTUAL_TSI_BCD pending_cuts=3 fromhost_writes=2 source_exit=0' in (out/(backend+'-integration.log')).read_text(), 'actual TSI BCD execution missing')
        for count, cut in enumerate((0, 1, 3)):
            require((out/f'{backend}-integration/pending-{count}.bcd').read_bytes() == oracle[cut], 'actual production pending commands differ')
            require((out/f'{backend}-integration/pending-{count}.poll').read_bytes() ==
                    config(24, 0x80002000, 0x80002008, 1048576)+words(1, 0, 0), 'actual TSI cut is not waiting at tohost')
    require(len(report['restores']) == 68 and len(report['corruptions']) == 4, 'missing fresh BCD cases')
    for case in report['restores']:
        dest = Path(case['destination']); image = Path(case['image']).read_bytes()
        require((dest/'preedge.bcd').read_bytes() == image, 'incomplete BCD fresh readback')
        if case['mode'] == 'restore':
            require((dest/'events.log').read_bytes() == suffix(trace, case['cut']), 'BCD continuation diverged')
            require((dest/'terminal-output.bin').read_bytes() == (b'Z' if case['cut'] < 10 else b''), 'fresh terminal write differs')
        elif case['mode'] == 'invalid':
            count = 48+len(image)+1+5+6
            require(f'BCD_ATOMIC_REJECTIONS malformed={count} incompatible=1 replies=0' in Path(case['log']).read_text(), 'missing atomic BCD rejection cases')
        require('target_edges=0 context_entries=0' in Path(case['log']).read_text(), 'fresh component entered target/context')
    for case in report['corruptions']:
        expected = suffix(trace, 4); actual = (Path(case['destination'])/'events.log').read_bytes()
        difference = first_difference(expected, actual)
        require(difference == case['first_divergence'] and difference['host_event'] == 11 and
                difference['expected'] == last_response, 'wrong first BCD semantic divergence')
    pids = []
    for command in report['commands']:
        log = Path(command['log']).read_text()
        require(command['argv'][:2] == ['bash', '-lc'] and command['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit=0'), 'unbound BCD native command/environment/result')
        require(not any(error in log for error in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'BCD sanitizer failure')
        pids.append(int(re.search(r'fresh_process_pid=(\d+)', log)[1]))
    require(len(pids) == len(set(pids)), 'BCD native checks reused a process')
    return dict(status='passed', fresh_component_restores=68, installed_reference_backends=2,
                actual_TSI_pending_cuts=6, actual_fromhost_writes=4,
                atomic_invalid_images=4*(48+len(oracle[4])+1+5+6), incompatible_images=4,
                service_guards=22, first_semantic_divergences=4, level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path); parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit), indent=2)); return
    require(args.out and args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    elf = out/'polling.elf'; elf.write_bytes(polling_elf())
    source = TESTS/'tsi_bcd_checkpoint.cc'; sv = TESTS/'tsi_bcd_checkpoint_tb.sv'; library = FESVR/'lib/libfesvr.a'
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc', TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc']
    inputs = [*sources, sv, library, Path(__file__), TESTS/'verify_tsi_host_control_fesvr_vcs.py',
              TESTS/'verify_firesim_tsi_loadmem_vcs.py', TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py',
              *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')), *sorted((FESVR/'include/fesvr').glob('*.h')),
              CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h', ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots = out/'sources'; snapshots.mkdir(); bindings = []
    for path in inputs:
        digest = file_sha(path); snapshot = snapshots/digest
        if not snapshot.exists(): shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    commands = []
    def execute(argv, name, **extra):
        log = out/(name+'.log'); argv = ['bash', '-lc', ENVIRONMENT+shlex.join([str(x) for x in argv])]
        run(argv, log, cwd=out)
        record = dict(cwd=str(out.relative_to(ROOT)), argv=argv, log=str(log), **extra)
        commands.append(record); (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return record
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    native = out/'bcd-native'; sanitized = out/'bcd-sanitized'; simv = out/'bcd-simv'
    for binary, flags in ((native, []), (sanitized, ['-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'])):
        execute([os.environ['CXX'], *shlex.split(include), '-g', *flags, *sources, library, '-lpthread', '-o', binary], binary.name+'-build')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps', '-top', 'tsi_bcd_checkpoint_tb',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], f'-Mdir={out/"csrc"}', '-CFLAGS', include+' -DTSI_BCD_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread', '-o', simv, sv, *sources], 'vcs-build')
    def invoke(backend, mode, name, image='unused', cut=-1):
        dest = out/name
        argv = [native if mode in ('capture', 'reference', 'integration') else sanitized, mode, elf, image, dest, cut] if backend == 'native' else [
            simv, '-no_save', '+mode='+mode, '+source='+str(elf), '+image='+str(image), '+destination='+str(dest), '+cut='+str(cut)]
        return execute(argv, name, mode=mode, destination=str(dest), image=str(image), cut=cut)
    for backend in ('native', 'vcs-dpi'):
        for mode in ('reference', 'capture', 'guards', 'integration'):
            invoke(backend, mode, backend+'-'+mode)
    restores = []; corruptions = []
    for producer in ('native', 'vcs-dpi'):
        for backend in ('native', 'vcs-dpi'):
            for cut in range(13):
                restores.append(invoke(backend, 'restore', f'{producer}-{backend}-cut-{cut}', out/f'{producer}-capture/cut-{cut}.bcd', cut))
            restores.append(invoke(backend, 'invalid', f'{producer}-{backend}-invalid', out/f'{producer}-capture/cut-4.bcd'))
            for count, cut in enumerate((0, 1, 3)):
                restores.append(invoke(backend, 'restore', f'{producer}-{backend}-actual-{count}',
                                       out/f'{producer}-integration/pending-{count}.bcd', cut))
            image = config(26, 1, 1048576)+words(1, READ|0xbeef)
            path = out/f'{producer}-{backend}-corrupt.bcd'; path.write_bytes(image)
            case = invoke(backend, 'corrupt', f'{producer}-{backend}-corrupt', path, 4)
            trace = (out/f'{producer}-reference/events.log').read_bytes()
            case['first_divergence'] = first_difference(suffix(trace, 4), (Path(case['destination'])/'events.log').read_bytes())
            corruptions.append(case)
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'BCD source changed during execution')
    report = dict(status='passed', scope='pending BCD queue component; terminal/syscall/complete CPU ownership pending', commands=commands,
                  restores=restores, corruptions=corruptions, source_inputs=bindings, level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(audit(path), indent=2))


if __name__ == '__main__':
    main()
