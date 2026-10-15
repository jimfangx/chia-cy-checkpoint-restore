"""Complete fresh initialization-caller components and real TestChip readbacks.

Independent ordered-access oracle; fixture labels are not CPU target cycles.
Every VCS shell sources vcs-env last. Complete HTIF/CPU restore stays pending.
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
import threading
from tools.checkpoint_formats.tests.native_parallel import checked_map

from tools.checkpoint_formats.tests.fesvr_overlay import overlay_inputs, build_overlay
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_tsi_serial_vcs import actual_images, audit as audit_serial
from tools.checkpoint_formats.tests.verify_tsi_serial_vcs import payload as serial_payload
from tools.checkpoint_formats.tests.verify_tsi_serial_read_vcs import payload as read_payload
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR


def settings(variant):
    if variant < 2:
        return [], variant == 1
    if variant == 2:
        return [(0x10000010, 0, False)], False
    if variant in (5, 6):
        return [(0x80000100, 0x12345678, True), (0x10000010, 0, False),
                (0x80000100, 0, True), (0x80000108, 0, False)], variant == 6
    require(variant in (3, 4), 'unknown variant')
    return [(0x10000010, 0, False), (0x80000000, 0xffffffff, True),
            (2**64-1, 0, False), (0x10000010, 0, True), (0x80000000, 0, False)], variant == 3


def payload(variant, phase=0, index=0, data=0):
    accesses, msip = settings(variant)
    return (config(21, int(msip), len(accesses)) +
            b''.join(words(address, value, int(store)) for address, value, store in accesses) +
            words(phase, index, data))


def oracle(variant):
    # Expand TestChip's original ordered range-for and optional final MSIP.
    # Calls and return/retire cuts are explicit; no C++ image drives this model.
    accesses, msip = settings(variant)
    ops, trace, states = [], [], [payload(variant)]
    def action(op, phase, index, data=0, result=None):
        ops.append(op)
        trace.append(f'OP {len(ops)} C {100+len(ops)} ' + (op if result is None else result))
        states.append(payload(variant, phase, index, data))
    for reset in range(2):
        action('BEGIN', 1, 0)
        for i, (address, value, store) in enumerate(accesses):
            child, returned = (4, 5) if store else (2, 3)
            action('SELECT', child, i, value if store else 0, f'SELECT {child} ADDRESS={address}')
            if store:
                action('WRITE_SOURCE', child, i, value, f'WRITE_SOURCE {value}')
                action('CHILD_RETURN', returned, i, value)
                action('WRITE_RESULT', returned, i, value, f'WRITE_RESULT {value}')
            else:
                value = (0x89abcdef + 0x1020304*i + reset) & 0xffffffff
                action(f'SET_READ {value}', child, i, value)
                action('CHILD_RETURN', returned, i, value)
                action('READ_RESULT', returned, i, value, f'READ_RESULT {value}')
            action('RETIRE', 1, i+1)
        if msip:
            action('SELECT', 6, len(accesses), 1, 'SELECT 6 ADDRESS=33554432')
            action('WRITE_SOURCE', 6, len(accesses), 1, 'WRITE_SOURCE 1')
            action('CHILD_RETURN', 7, len(accesses), 1)
            action('RETIRE', 8, len(accesses))
        else:
            action('SELECT', 8, len(accesses), result='SELECT COMPLETE')
    return ops, trace, states


def actual_init_images(count):
    result = {}
    for name in actual_images(count):
        if name in ('constructed', 'reset-wait'):
            result[name] = payload(2)
        elif name.startswith(('init-', 'child-wait-')) or name == 'reset-child':
            result[name] = payload(2, 2)
        else:
            result[name] = payload(2, 8, 1)
    return result


def mixed_images(flush, msip):
    # Original TestChip algorithm: optional line-flush write before each
    # serial access; ordered 4-byte accesses; optional MSIP; real HTIF poll.
    variant = 6 if msip else 5
    host = lambda phase, flags: config(18, 1)+words(phase, 0, flags)
    empty = serial_payload()
    result = {'constructed': (payload(variant), read_payload(), empty, host(0, 0)),
              'reset-wait': (payload(variant), read_payload(), empty, host(2, 2))}
    def request(write, address, data):
        packet = [int(write), address & 0xffffffff, address >> 32, len(data)-1, 0]
        return packet+data if write else packet
    def access(write, address, data):
        prefix = request(True, 0x10000100, [address & ~63 & 0xffffffff, address >> 32]) if flush else []
        return prefix+request(write, address, data)
    packets = {'first': access(True, 0x80000100, [0x12345678])+access(False, 0x10000010, [0]),
               'second': access(True, 0x80000100, [0])+access(False, 0x80000108, [0]),
               'poll': (access(True, 0x2000000, [1]) if msip else [])+access(False, 0x80002000, [0, 0])}
    for name, phase, index, address, length in [('first', 2, 1, 0x10000010, 4),
                                               ('second', 2, 3, 0x80000108, 4), ('poll', 8, 4, 0x80002000, 8)]:
        init, reader, control = payload(variant, phase, index), read_payload(2, address, length), host(0 if name=='poll' else 3, 6)
        packet = packets[name]
        result[name+'-queued'] = (init, reader, serial_payload(packet), control)
        for i in sorted({0, len(packet)//2, len(packet)-1}):
            result[name+f'-pop-{i}'] = (init, reader, serial_payload(packet[i+1:]), control)
        if name != 'poll':
            for i in range(2): result[name+f'-wait-{i}'] = (init, reader, empty, control)
            response = 0x89abcdef if name=='first' else 0xfedcba98
            result[name+'-response'] = (init, reader, serial_payload(responses=[response]), control)
    return result, sum(map(len, packets.values()))


def audit(path):
    path = path.resolve(); r = json.loads(path.read_text()); out = path.parent
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong init scope')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'changed evidence membership')
    for p, digest in r['artifact_sha256'].items():
        require(file_sha(p) == digest, 'changed init evidence '+p)
    bindings = {b['path']: b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed original source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    restores = readbacks = records = 0; atomic = {}
    for backend in ('native-sanitized', 'vcs-dpi'):
        base = out/backend
        atomic[backend] = int(re.search(r'ATOMIC_CHECKS (\d+)', (base/'checks.log').read_text())[1])
        require(atomic[backend] >= 6000, 'missing atomic/phase/interrupted checks')
        for variant in range(5):
            case = base/str(variant); ops, trace, states = oracle(variant)
            require((case/'commands.txt').read_text().splitlines() == ops and
                    (case/'expected.txt').read_text().splitlines() == trace, 'changed independent oracle')
            require((case/'reference/trace').read_text().splitlines() == trace, 'reference order/result differs')
            for cut, state in enumerate(states):
                require((case/f'reference/cut-{cut}.owner').read_bytes() == state, 'incomplete original init state')
                dest = case/f'restore-{cut}'
                require((dest/'preedge.owner').read_bytes() == state and
                        (dest/'trace').read_text().splitlines() == trace[cut:], 'fresh readback/continuation differs')
                for i in range(cut, len(states)):
                    require((dest/f'cut-{i}.owner').read_bytes() == states[i], 'continued complete state differs')
                    readbacks += 1
                restores += 1; records += len(trace)-cut
        for c in r['invalid_cases'][backend]:
            dest = Path(c['output'])
            require({p.name for p in dest.iterdir()} == {'unchanged.owner'} and
                    (dest/'unchanged.owner').read_bytes() == payload(3, 1), 'invalid image partially restored')
            require('REJECTED_BEFORE_MUTATION zero_edges=1' in Path(c['log']).read_text(), 'missing atomic rejection')
        for c in r['corruptions'][backend]:
            dest = Path(c['output']); cut = c['cut']; _, trace, _ = oracle(3)
            require(json.loads((dest/'first-divergence.json').read_text()) ==
                    dict(operation=cut+1, fixture_cycle=101+cut, acknowledged=0,
                         expected=trace[cut], actual=c['expected_actual']) and
                    (dest/'trace').read_bytes() == b'', 'wrong first divergent boundary/acknowledgement')
    parent = Path(r['serial_summary'])
    require(file_sha(parent) == r['serial_summary_sha256'] and audit_serial(parent)['actual_serial_images'] == 384,
            'missing real installed-FESVR input evidence')
    images = 0
    for backend in ('native', 'vcs-dpi'):
        for count in (1, 3, 10):
            case = parent.parent/('actual-'+backend)/str(count); expected = actual_init_images(count)
            require({p.stem for p in case.glob('*.init')} == set(expected), 'missing actual caller cuts')
            for name, image in expected.items():
                require((case/(name+'.init')).read_bytes() == image, 'actual caller/configuration differs '+name)
                images += 1
    require(len(r['actual_restores']) == 2*images, 'missing actual fresh component readbacks')
    for c in r['actual_restores']:
        require(Path(c['image']).read_bytes() == Path(c['readback']).read_bytes(), 'actual complete zero-edge readback differs')
        require('COMPLETE_READBACK zero_edges=1 restore_services=0' in Path(c['log']).read_text(), 'restore called services')
    mixed_count = 0
    for backend in ('native', 'vcs-dpi'):
        for flush in (0, 1):
            for msip in (0, 1):
                case = out/f'mixed-{backend}-{flush}-{msip}'; expected, packet_words = mixed_images(flush, msip)
                require({p.stem for p in case.glob('*.init')} == set(expected), 'changed mixed capture inventory')
                for name, owners in expected.items():
                    for kind, data in zip(('init', 'read', 'serial', 'host'), owners):
                        require((case/(name+'.'+kind)).read_bytes() == data, 'actual mixed owner differs '+name+'/'+kind)
                    mixed_count += 1
                log = (out/(case.name+'.log')).read_text()
                require(f'REAL_TESTCHIP_INIT flush={flush} msip={msip} accesses=4 read_results=89abcdef,fedcba98 serial_words={packet_words}' in log,
                        'mixed original protocol did not finish')
                require(' got 89abcdef' in log and ' got fedcba98' in log and
                        'Done writing 80000100 with 12345678' in log and 'Done writing 80000100 with 0' in log,
                        'production init result/diagnostic behavior changed')
    require(len(r['mixed_restores']) == 2*mixed_count, 'missing fresh mixed caller readbacks')
    for c in r['mixed_restores']:
        require(Path(c['image']).read_bytes() == Path(c['readback']).read_bytes() and
                'COMPLETE_READBACK zero_edges=1 restore_services=0' in Path(c['log']).read_text(), 'mixed readback differs/called services')
    for c in r['commands']:
        log = Path(c['log']).read_text()
        require(c['argv'][:2] == ['bash', '-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(c['expected_exit'])), 'unbound native environment/exit')
        require(not any(s in log for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'sanitizer error')
    require(len({c['pid'] for c in r['commands']}) == len(r['commands']), 'process identity reused')
    return dict(status='passed', summary=str(path), fresh_fixture_restores=restores,
                complete_fixture_readbacks=readbacks, continued_records=records, atomic_checks=atomic,
                invalid_processes=sum(map(len, r['invalid_cases'].values())), first_divergences=4,
                actual_init_images=images, actual_fresh_restores=len(r['actual_restores']),
                actual_mixed_images=mixed_count, actual_mixed_fresh_restores=len(r['mixed_restores']),
                level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path); p.add_argument('--serial-summary', type=Path); p.add_argument('--audit', type=Path)
    a = p.parse_args()
    if a.audit:
        print(json.dumps(audit(a.audit), indent=2)); return
    require(a.out is not None and a.serial_summary is not None and
            a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output and actual serial summary')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env.sh LAST')
    parent = a.serial_summary.resolve()
    require(audit_serial(parent)['actual_serial_images'] == 384, 'need current actual serial captures')
    for backend in ('native', 'vcs-dpi'):
        for count in (1, 3, 10):
            case = parent.parent/('actual-'+backend)/str(count)
            for name, image in actual_init_images(count).items():
                require((case/(name+'.init')).read_bytes() == image, 'incorrect actual init '+name)
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    fixture = TESTS/'tsi_init_checkpoint.cc'; sv = TESTS/'tsi_init_checkpoint_tb.sv'
    library = FESVR/'lib/libfesvr.a'
    actual_sources = [TESTS/'tsi_init_fesvr.cc', STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc',
                      TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc']
    inputs = [fixture, sv, Path(__file__), TESTS/'native_parallel.py', STUBS/'fesvr/tsi_init_accesses.h', STUBS/'fesvr/firesim_tsi.h',
              STUBS/'fesvr/firesim_tsi.cc', TESTS/'verify_tsi_serial_vcs.py', TESTS/'verify_firesim_tsi_loadmem_vcs.py',
              TESTS/'verify_loadmem_read_checkpoint_vcs.py', TESTS/'verify_semantic_vcs.py',
              CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h', ROOT/'env.sh', ROOT/'sims/firesim/env.sh',
              ROOT/'automations/checkpoint_loop/vcs-env.sh', *actual_sources, TESTS/'tsi_init_fesvr_tb.sv', library,
              TESTS/'verify_tsi_serial_read_vcs.py', TESTS/'verify_tsi_host_control_fesvr_vcs.py',
              *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')), *sorted((FESVR/'include/fesvr').glob('*.h'))]
    inputs = sorted(set(inputs))
    inputs = [*inputs, *overlay_inputs()]
    snapshots = out/'source-snapshots'; snapshots.mkdir(); bindings = []
    for f in inputs:
        digest = file_sha(f); snapshot = snapshots/digest
        if not snapshot.exists(): shutil.copyfile(f, snapshot)
        bindings.append(dict(path=str(f), sha256=digest, snapshot=str(snapshot)))
    commands = []; command_lock = threading.Lock()
    def execute(argv, log, expected=0):
        argv = ['bash', '-lc', ENVIRONMENT+shlex.join([str(x) for x in argv])]
        result = run(argv, log, cwd=out, expected=expected)
        c = dict(cwd=str(out.relative_to(ROOT)), argv=argv, log=str(log), expected_exit=expected,
                 pid=int(re.search(r'fresh_process_pid=(\d+)', result)[1]))
        with command_lock:
            commands.append(c); (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return c
    library = build_overlay(out, execute)
    include = f'-std=c++17 -I{CC} -I{STUBS}'; native = out/'init-native'; simv = out/'init-simv'
    execute([os.environ['CXX'], *shlex.split(include), '-Wall', '-Wextra', '-Werror', '-no-pie', '-g',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer', fixture, '-o', native], out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'tsi_init_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             f'-Mdir={out/"csrc"}', '-CFLAGS', include+' -DTSI_INIT_DPI', '-o', simv, sv, fixture], out/'vcs-build.log')
    def invoke(backend, mode, target, cmd='unused', wanted='unused', image='unused', cut=0, variant=3, expected=0):
        values = list(map(str, [mode, target, cmd, wanted, image, cut, variant]))
        binary = native if backend == 'native-sanitized' else simv
        argv = [binary, *values] if backend == 'native-sanitized' else [binary, '-no_save',
                *['+'+k+'='+v for k, v in zip(('mode', 'out', 'commands', 'expected', 'image', 'cut', 'variant'), values)]]
        return execute(argv, target.parent/(target.name+'.log'), expected)
    invalid_cases = {}; corruptions = {}; actual_restores = []
    for backend in ('native-sanitized', 'vcs-dpi'):
        base = out/backend; base.mkdir(); invoke(backend, 'check', base/'checks')
        for variant in range(5):
            case = base/str(variant); case.mkdir(); ops, trace, states = oracle(variant)
            cmd = case/'commands.txt'; wanted = case/'expected.txt'
            cmd.write_text('\n'.join(ops)+'\n'); wanted.write_text('\n'.join(trace)+'\n')
            invoke(backend, 'reference', case/'reference', cmd, wanted, variant=variant)
            checked_map(lambda cut:invoke(backend, 'restore', case/f'restore-{cut}', cmd, wanted,
                        case/f'reference/cut-{cut}.owner', cut, variant),range(len(states)))
        valid = payload(3, 2); start = len(valid)-24
        def change(offset, value):
            bad = bytearray(valid); struct.pack_into('<Q', bad, offset, value); return bytes(bad)
        invalids = {'missing-owner': None, 'empty': b'', 'truncated': valid[:-1], 'extra': valid+b'\0',
                    'extra-word': valid+words(0), 'incompatible-program': payload(4, 2),
                    **{name: change(at, value) for name, at, value in [
                        ('magic', 0, 0), ('version', 8, 2), ('kind', 16, 20), ('config-count', 24, 1),
                        ('msip-policy', 32, 0), ('access-count', 40, 4), ('address', 48, 0),
                        ('config-data', 56, 1), ('config-store', 64, 1), ('phase', start, 9),
                        ('huge-index', start+8, 2**64-1), ('read-past-end', start+8, 5),
                        ('read-on-write', start+8, 1), ('write-on-read', start, 4),
                        ('idle-cursor', start+8, 2), ('wide-data', start+16, 2**32)]}}
        invalids['idle-cursor'] = payload(3, 0, 2)
        invalids.update({'idle-data': payload(3, 0, 0, 1), 'ready-data': payload(3, 1, 0, 1),
                        'incomplete-complete': payload(3, 8, 0), 'complete-data': payload(3, 8, 5, 1),
                        'write-data': payload(3, 4, 1, 0), 'msip-index': payload(3, 6, 0, 1),
                        'msip-data': payload(3, 7, 5, 0), 'read-return-past-end': payload(3, 3, 5)})
        invalid_cases[backend] = []
        for name, image in invalids.items():
            source = base/('invalid-'+name+'.owner')
            if image is not None: source.write_bytes(image)
            dest = base/('invalid-'+name); c = invoke(backend, 'invalid', dest, image=source)
            invalid_cases[backend].append(dict(case=name, output=str(dest), log=c['log']))
        corruptions[backend] = []; ops, trace, states = oracle(3)
        for name, cut, offset, value, result in [
            ('cursor', ops.index('SELECT'), start+8, 2, 'SELECT 2 ADDRESS=18446744073709551615'),
            ('read-result', ops.index('READ_RESULT'), start+16, 0x89abcdee, 'READ_RESULT 2309737966')]:
            bad = bytearray(states[cut]); struct.pack_into('<Q', bad, offset, value)
            source = base/(name+'-corrupt.owner'); source.write_bytes(bad); dest = base/(name+'-corruption')
            c = invoke(backend, 'restore', dest, base/'3/commands.txt', base/'3/expected.txt', source, cut, expected=2)
            corruptions[backend].append(dict(case=name, cut=cut, output=str(dest), log=c['log'],
                                             expected_actual=f'OP {cut+1} C {101+cut} '+result))
    jobs=[(backend,count,name,restored) for backend in ('native','vcs-dpi') for count in (1,3,10)
          for name in actual_init_images(count) for restored in ('native-sanitized','vcs-dpi')]
    def restore_actual(job):
        backend,count,name,restored=job;image=parent.parent/('actual-'+backend)/str(count)/(name+'.init')
        dest=out/f'restore-actual-{backend}-{count}-{name}-{restored}'
        c=invoke(restored,'readback',dest,image=image,variant=2)
        return dict(c,image=str(image),readback=str(dest/'preedge.owner'))
    actual_restores.extend(checked_map(restore_actual,jobs))
    actual_include = include+f' -I{TESTCHIP} -I{FESVR/"include"}'
    actual_native = out/'actual-init-native'; actual_simv = out/'actual-init-simv'
    execute([os.environ['CXX'], *shlex.split(actual_include), '-g', *actual_sources, library, '-lpthread', '-o', actual_native],
            out/'actual-native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'tsi_init_fesvr_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             f'-Mdir={out/"actual-csrc"}', '-CFLAGS', actual_include+' -DTSI_INIT_FESVR_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread',
             '-o', actual_simv, TESTS/'tsi_init_fesvr_tb.sv', *actual_sources], out/'actual-vcs-build.log')
    elf = out/'polling.elf'; elf.write_bytes(polling_elf()); mixed_restores = []
    for backend in ('native', 'vcs-dpi'):
        for flush in (0, 1):
            for msip in (0, 1):
                case = out/f'mixed-{backend}-{flush}-{msip}'
                argv = [actual_native, elf, case, flush, msip] if backend=='native' else [actual_simv, '-no_save',
                        '+elf='+str(elf), '+out='+str(case), '+flush='+str(flush), '+msip='+str(msip)]
                execute(argv, out/(case.name+'.log'))
                for name, owners in mixed_images(flush, msip)[0].items():
                    for kind, data in zip(('init', 'read', 'serial', 'host'), owners):
                        require((case/(name+'.'+kind)).read_bytes()==data, 'actual mixed production state differs '+name+'/'+kind)
                jobs=[(name,restored) for name in mixed_images(flush,msip)[0] for restored in ('native-sanitized','vcs-dpi')]
                def restore_mixed(job):
                    name,restored=job;image=case/(name+'.init')
                    dest=out/f'restore-mixed-{backend}-{flush}-{msip}-{name}-{restored}'
                    c=invoke(restored,'readback',dest,image=image,variant=6 if msip else 5)
                    return dict(c,image=str(image),readback=str(dest/'preedge.owner'))
                mixed_restores.extend(checked_map(restore_mixed,jobs))
    for b in bindings:
        require(file_sha(b['path']) == b['sha256'], 'init source changed during native execution')
    report = dict(status='passed', scope='initialization caller components; HTIF/context/child/CPU restore pending',
                  serial_summary=str(parent), serial_summary_sha256=file_sha(parent), commands=commands,
                  source_inputs=bindings, invalid_cases=invalid_cases, corruptions=corruptions, actual_restores=actual_restores,
                  mixed_restores=mixed_restores,
                  artifact_sha256={str(f): file_sha(f) for f in sorted(out.rglob('*')) if f.is_file()},
                  level1_verified=False, level2_verified=False)
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(audit(path), indent=2))


if __name__ == '__main__':
    main()
