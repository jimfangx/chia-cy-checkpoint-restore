"""Resume actual suspended TestChip initialization in fresh native/VCS objects.

The independent original protocol oracle checks every peer owner and operation.
These host-only component cuts do not establish CPU checkpoint acceptance.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import tempfile

from tools.checkpoint_formats.tests.fesvr_overlay import overlay_inputs, build_overlay
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_tsi_init_vcs import audit as audit_init, mixed_images, payload as init_payload
from tools.checkpoint_formats.tests.verify_tsi_serial_vcs import payload as serial_payload
from tools.checkpoint_formats.tests.verify_tsi_serial_read_vcs import payload as read_payload
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR


def bundle(flush, owners):
    # Bundle order is explicit and independent of C++'s owner iteration.
    init, reader, serial, host = owners
    return config(22, 0x10000100 if flush else 0)+b''.join(words(len(b))+b for b in (host, init, reader, serial))


def packet(write, address, data):
    b = [int(write), address & 0xffffffff, address >> 32, len(data)-1, 0]
    return b+data if write else b


def continuation(flush, msip, name):
    images, _ = mixed_images(flush, msip)
    owners = list(images[name]); ops = []; states = [bundle(flush, owners)]
    variant = 6 if msip else 5
    def act(op):
        ops.append(op); states.append(bundle(flush, owners))
    if name == 'reset-wait':
        owners[3] = config(18, 1)+words(2, 0, 6); act('TARGET 1')
        owners[:] = images['first-queued']; act('ADVANCE 0'); stage = 'first'
    else:
        stage = name.split('-')[0]
    for current in ('first', 'second'):
        if current == 'first' and stage == 'second':
            continue
        # Parse only the independently specified FIFO encoding to schedule
        # its external consumer; no implementation result drives the oracle.
        start = len(config(19, 4, 2, 2, 1024))
        values = list(struct.unpack('<'+'Q'*((len(owners[2])-start)//8), owners[2][start:]))
        nr = values[0]; requests = values[1:1+nr]; responses = values[2+nr:]
        for _ in range(len(requests)):
            expected = requests.pop(0); owners[2] = serial_payload(requests, responses)
            act(f'POP {expected}')
        if not responses:
            act('ADVANCE 0'); act('ADVANCE 0')
            responses.append(0x89abcdef if current == 'first' else 0xfedcba98)
            owners[2] = serial_payload(responses=responses); act(f'SEND {responses[0]}')
        if current == 'first':
            owners[:] = images['second-queued']; act('ADVANCE 0')
        else:
            last = []
            if msip:
                if flush: last += packet(True, 0x10000100, [0x2000000, 0])
                last += packet(True, 0x2000000, [1])
            owners[:] = [init_payload(variant, 8, 4), read_payload(), serial_payload(last), config(18, 1)+words(0, 0, 6)]
            act('ADVANCE 1')
            while last:
                expected = last.pop(0); owners[2] = serial_payload(last); act(f'POP {expected}')
            act('ADVANCE 1')
    return ops, states


def audit(path):
    path = path.resolve(); out = path.parent; r = json.loads(path.read_text())
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong resume scope')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'changed resume membership')
    for p, digest in r['artifact_sha256'].items(): require(file_sha(p) == digest, 'changed resume artifact '+p)
    bindings = {b['path']: b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed resume source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    parent = Path(r['init_summary'])
    require(file_sha(parent) == r['init_summary_sha256'], 'changed actual suspended caller evidence')
    require(audit_init(parent)['actual_mixed_images'] == 160, 'incomplete real TestChip input evidence')
    readbacks = operations = 0
    require(len(r['restores']) == 240, 'missing actual fresh dispatches')
    for c in r['restores']:
        dest = Path(c['out']); ops, states = continuation(c['flush'], c['msip'], c['name'])
        expected = mixed_images(c['flush'], c['msip'])[0][c['name']]
        source = parent.parent/f"mixed-{c['source_backend']}-{c['flush']}-{c['msip']}"
        require(tuple((source/(c['name']+'.'+k)).read_bytes() for k in ('init','read','serial','host')) == expected,
                'changed actual suspended input owners')
        require(Path(c['image']).read_bytes() == states[0] == (dest/'preedge.bundle').read_bytes(), 'incomplete preedge readback')
        require(Path(c['plan']).read_text().splitlines() == ops == (dest/'trace').read_text().splitlines(), 'dispatch output/order differs')
        for i, state in enumerate(states[1:], 1):
            require((dest/f'after-{i}.bundle').read_bytes() == state, 'continued complete peer owner differs')
        log = Path(c['log']).read_text()
        require('COMPLETE_READBACK zero_edges=1 context_entries=0 restore_services=0' in log and
                f'FRESH_INIT_CONTINUATION operations={len(ops)} target_edges=0 context_entries=0' in log,
                'context or target entered during component continuation')
        operations += len(ops); readbacks += len(states)
    for c in r['invalids']:
        log = Path(c['log']).read_text()
        require(f"ATOMIC_REJECTIONS {c['count']} zero_edges=1 context_entries=0" in log, 'missing atomic bundle rejections')
        require((Path(c['out'])/'unchanged.owners').read_bytes() ==
                config(18,1)+words(0,0,0)+init_payload(6 if c['msip'] else 5)+read_payload()+serial_payload(),
                'invalid restore mutated a peer owner')
    require(len(r['corruptions']) == 4, 'missing native and VCS semantic corruption checks')
    for c in r['corruptions']:
        dest = Path(c['out']); ops, _ = continuation(1, 1, 'first-queued')
        require((dest/'trace').read_bytes() == b'' and (dest/'first-divergence.txt').read_text() ==
                'FIRST_DIVERGENCE fixture_cycle=101 operation=1 signal=POP expected=1 actual=0 acknowledged=0\n',
                'wrong first corruption boundary')
    for c in r['commands']:
        log = Path(c['log']).read_text()
        require(c['argv'][:2] == ['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(c['expected_exit'])), 'unbound VCS environment/exit')
        require(not any(s in log for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'sanitizer error')
    return dict(status='passed', fresh_actual_dispatches=len(r['restores']), complete_peer_readbacks=readbacks,
                continued_operations=operations, atomic_invalid_images=sum(c['count'] for c in r['invalids']),
                first_divergences=len(r['corruptions']), level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path); p.add_argument('--init-summary', type=Path); p.add_argument('--audit', type=Path)
    a = p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit), indent=2)); return
    require(a.out is not None and a.init_summary is not None and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),
            'diagnostics must be under runs')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env LAST')
    parent = a.init_summary.resolve(); require(audit_init(parent)['actual_mixed_images'] == 160, 'actual init input failed')
    a.out.resolve().mkdir(parents=True, exist_ok=True); out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    sources = [TESTS/'tsi_init_resume.cc', STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc', TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc']
    library = FESVR/'lib/libfesvr.a'; inputs = [*sources, library, Path(__file__), TESTS/'tsi_init_resume_tb.sv',
        *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')), *sorted((FESVR/'include/fesvr').glob('*.h')),
        CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h', TESTS/'verify_tsi_init_vcs.py', TESTS/'verify_tsi_serial_vcs.py',
        TESTS/'verify_tsi_serial_read_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py', TESTS/'verify_semantic_vcs.py',
        TESTS/'verify_firesim_tsi_loadmem_vcs.py', ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh']
    inputs = [*inputs, *overlay_inputs()]
    snapshots = out/'sources'; snapshots.mkdir(); bindings = []
    for f in sorted(set(inputs)):
        digest = file_sha(f); snapshot = snapshots/digest
        if not snapshot.exists(): shutil.copyfile(f, snapshot)
        bindings.append(dict(path=str(f), sha256=digest, snapshot=str(snapshot)))
    commands = []
    def execute(argv, log, expected=0):
        argv = ['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])]
        result = run(argv, log, cwd=out, expected=expected)
        c = dict(cwd=str(out.relative_to(ROOT)), argv=argv, log=str(log), expected_exit=expected,
                 pid=int(re.search(r'fresh_process_pid=(\d+)',result)[1]))
        commands.append(c); (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n'); return c
    library = build_overlay(out, execute)
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    native = out/'resume-native'; simv = out/'resume-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-g','-no-pie','-fsanitize=address,undefined','-fno-omit-frame-pointer',
             *sources, library, '-lpthread','-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_init_resume_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"csrc"}', '-CFLAGS',include+' -DTSI_INIT_RESUME_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread','-o',simv,TESTS/'tsi_init_resume_tb.sv',*sources],out/'vcs-build.log')
    elf = parent.parent/'polling.elf'
    def invoke(backend, mode, image, plan, dest, flush, msip, expected=0):
        values = list(map(str,[mode,elf,image,plan,dest,flush,msip]))
        argv = [native,*values] if backend=='native' else [simv,'-no_save',*['+'+k+'='+v for k,v in
                zip(('mode','elf','image','plan','out','flush','msip'),values)]]
        return execute(argv, dest.parent/(dest.name+'.log'), expected)
    restores = []; invalids = []; corruptions = []
    for flush in (0,1):
        for msip in (0,1):
            case = out/f'{flush}-{msip}'; case.mkdir(); images, _ = mixed_images(flush,msip)
            for name in images:
                if name == 'constructed' or name.startswith('poll'): continue
                ops, states = continuation(flush,msip,name); image = case/(name+'.bundle'); image.write_bytes(states[0])
                plan = case/(name+'.plan'); plan.write_text('\n'.join(ops)+'\n')
                for source_backend in ('native','vcs-dpi'):
                    original = parent.parent/f'mixed-{source_backend}-{flush}-{msip}'
                    require(bundle(flush, tuple((original/(name+'.'+k)).read_bytes() for k in ('init','read','serial','host'))) == states[0], 'original state differs')
                    for backend in ('native','vcs-dpi'):
                        dest = case/f'{name}-{source_backend}-{backend}'
                        c = invoke(backend,'resume',image,plan,dest,flush,msip)
                        restores.append(dict(c,out=str(dest),image=str(image),plan=str(plan),flush=flush,msip=msip,name=name,source_backend=source_backend))
            valid = bundle(flush,images['first-queued']); bads = [valid[:n] for n in range(len(valid))]
            bads += [valid+b'\0',valid+words(0)]
            def edit(data, offset, value):
                b = bytearray(data); struct.pack_into('<Q',b,offset,value); return bytes(b)
            # Incompatible outer build/policy, missing/reordered owner, and
            # individually valid but mutually inconsistent caller/child state.
            for offset,value in [(0,0),(8,2),(16,21),(24,0),(32,0x10000200),(40,2**64-1)]:
                bads.append(edit(valid,offset,value))
            init, reader, serial, host = images['first-queued']
            bads += [bundle(flush,[init,read_payload(),serial,host]),
                     bundle(flush,[init,read_payload(2,0x80000108,4),serial,host]),
                     bundle(flush,[init,reader,serial,config(18,1)+words(3,0,2)]),
                     bundle(flush,[init_payload(6 if msip else 5,2,1,1),reader,serial,host]),
                     config(22,0x10000100 if flush else 0)+words(len(host))+host,
                     bundle(flush,[init,serial,reader,host])]
            invalid_dir = case/'invalid-inputs'; invalid_dir.mkdir(); paths=[]
            for i,b in enumerate(bads):
                f = invalid_dir/f'{i}.bundle'; f.write_bytes(b); paths.append(str(f))
            paths.append(str(invalid_dir/'missing.bundle'))
            plan = case/'invalid.plan'; plan.write_text('\n'.join(paths)+'\n')
            for backend in ('native','vcs-dpi'):
                dest = case/('invalid-'+backend); c = invoke(backend,'invalid','unused',plan,dest,flush,msip)
                invalids.append(dict(c,out=str(dest),count=len(paths),flush=flush,msip=msip))
    # Alter actual owned semantic packet data while retaining valid structure.
    case = out/'1-1'; valid = (case/'first-queued.bundle').read_bytes(); cursor = len(config(22,0x10000100))
    for _ in range(3): cursor += 8+struct.unpack_from('<Q',valid,cursor)[0]
    first_word = cursor+8+len(config(19,4,2,2,1024))+8
    bad = bytearray(valid); struct.pack_into('<Q',bad,first_word,0)
    image = case/'corrupt-request.bundle'; image.write_bytes(bad)
    for backend in ('native','vcs-dpi'):
        for repeat in range(2):
            dest = case/f'corrupt-{backend}-{repeat}'; c = invoke(backend,'resume',image,case/'first-queued.plan',dest,1,1,3)
            corruptions.append(dict(c,out=str(dest)))
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'resume source changed during native checks')
    r = dict(status='passed',scope='fresh production reset/initialization component dispatch; HTIF/CPU restore pending',
             init_summary=str(parent),init_summary_sha256=file_sha(parent),source_inputs=bindings,commands=commands,
             restores=restores,invalids=invalids,corruptions=corruptions,level1_verified=False,level2_verified=False,
             artifact_sha256={str(f):file_sha(f) for f in sorted(out.rglob('*')) if f.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(r,indent=2)+'\n'); print(json.dumps(audit(path),indent=2))


if __name__ == '__main__': main()
