"""Fresh serial read/FIFO continuation and actual installed-HTIF read images.

The Python oracle expands the original serial packet/pop/yield protocol.
Component operation labels are not Rocket target-cycle checkpoint cuts.
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
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_tsi_serial_vcs import payload as serial_payload, actual_images, audit as audit_serial
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS

SIZES = (4, 8, 64, 128, 1024)
ADDRESS = 0x8000000100000000


def payload(phase=0, address=0, size=0, collected=()):
    return config(20, 1024, 4, 2, 2)+words(phase, address, size, len(collected), *collected)


def oracle(size):
    requests, responses, collected, ops, trace = [], [], [], [], []
    phase, address, length = 0, 0, 0
    states = [(payload(), serial_payload())]
    def action(text):
        nonlocal phase, address, length, collected
        f=text.split(); op=f[0]; result=text
        if op=='BEGIN':
            address, length=map(int,f[1:]); phase=1
        elif op=='ADVANCE':
            if phase==1:
                requests.extend([0,address & 0xffffffff,address >> 32,length//4-1,0]); phase=2
                result=f'ADVANCE ISSUE {address} {length} PROGRESS'
            elif phase==3: result='ADVANCE NO_SERVICE COMPLETE'
            elif not responses: result='ADVANCE EMPTY BLOCKED'
            else:
                value=responses.pop(0); collected.append(value)
                if len(collected)==length//4: phase=3
                result=f'ADVANCE WORD {value} '+('COMPLETE' if phase==3 else 'PROGRESS')
        elif op=='SEND': responses.append(int(f[1]))
        elif op=='REQUEST': result='REQUEST '+str(requests.pop(0))
        elif op=='RESULT': result='RESULT'+''.join(' '+str(v) for v in collected)
        elif op=='FINISH': phase, address, length, collected=0,0,0,[]
        elif op=='QUERY': result=f'QUERY REQUEST={int(bool(requests))} RESPONSE={int(bool(responses))}'
        else: raise ValueError(op)
        ops.append(text); trace.append(f'OP {len(ops)} C {100+len(ops)} '+result)
        states.append((payload(phase,address,length,collected),serial_payload(requests,responses)))
    action('QUERY'); action(f'BEGIN {ADDRESS} {size}'); action('ADVANCE')
    for _ in range(2): action('REQUEST')
    action('ADVANCE'); action('ADVANCE')
    for first in range(0,size//4,3):
        for i in range(first,min(first+3,size//4)):
            action('SEND '+str(0 if i%3==0 else (0xf0000000+i*0x10203)&0xffffffff))
        for _ in range(first,min(first+3,size//4)): action('ADVANCE')
        if phase!=3: action('ADVANCE')
    action('SEND 42'); action('ADVANCE'); action('QUERY'); action('RESULT'); action('FINISH'); action('QUERY')
    while requests: action('REQUEST')
    # The queued extra response becomes the next read's first word. No request
    # is duplicated by restoring an already-issued read.
    action('BEGIN 18446744073709551612 4'); action('ADVANCE'); action('ADVANCE'); action('RESULT'); action('FINISH')
    while requests: action('REQUEST')
    action('QUERY')
    return ops,trace,states


def cuts(size,states):
    if size<=128: return list(range(len(states)))
    return sorted({*range(12),63,64,65,len(states)//2,*range(len(states)-16,len(states))})


def actual_read_images(count):
    result={name:payload() for name in actual_images(count)}
    init=payload(2,0x10000010,4)
    poll=payload(2,0x80002000,8)
    for name in result:
        if name.startswith('init-') or name.startswith('child-wait-') or name=='reset-child': result[name]=init
        elif name=='first-poll' or name.startswith('first-') or name.startswith('busy-'): result[name]=poll
        elif name.startswith('poll-half-') or re.fullmatch(r'poll-response-\d+-1',name): result[name]=payload(2,0x80002000,8,[0])
        elif name.startswith('poll-response-'): result[name]=poll
    return result


def audit(path):
    path=path.resolve(); r=json.loads(path.read_text()); out=path.parent
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'],'incorrect serial read scope')
    require(set(r['artifact_sha256'])=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'changed evidence membership')
    for p,d in r['artifact_sha256'].items(): require(file_sha(p)==d,'changed read evidence '+p)
    bindings={b['path']:b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed source snapshot')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    restores=readbacks=records=0
    for backend in ('native-sanitized','vcs-dpi'):
        base=out/backend
        require(int(re.search(r'ATOMIC_CHECKS (\d+)',(base/'checks.log').read_text())[1])>=500,'missing atomic/interruption checks')
        for size in SIZES:
            case=base/str(size); ops,trace,states=oracle(size)
            require((case/'commands.txt').read_text().splitlines()==ops and (case/'expected.txt').read_text().splitlines()==trace,'changed oracle')
            require((case/'reference/trace').read_text().splitlines()==trace,'original serial read differs')
            for i,(reader,serial) in enumerate(states):
                require((case/f'reference/cut-{i}.read').read_bytes()==reader and
                        (case/f'reference/cut-{i}.serial').read_bytes()==serial,'incomplete original state')
            for cut in cuts(size,states):
                dest=case/f'restore-{cut}'; require((dest/'preedge.read').read_bytes()==states[cut][0] and
                     (dest/'preedge.serial').read_bytes()==states[cut][1],'incomplete zero-edge readback')
                require((dest/'trace').read_text().splitlines()==trace[cut:],'fresh continuation differs')
                for i in range(cut,len(states)):
                    require((dest/f'cut-{i}.read').read_bytes()==states[i][0] and
                            (dest/f'cut-{i}.serial').read_bytes()==states[i][1],'continued complete state differs'); readbacks+=2
                restores+=1; records+=len(trace)-cut
        for item in r['invalid_cases'][backend]:
            dest=Path(item['output'])
            require({p.name for p in dest.iterdir()}=={'unchanged.read','unchanged.serial'} and
                    (dest/'unchanged.read').read_bytes()==payload(2,0x123456789abcdef0,8,[42]) and
                    (dest/'unchanged.serial').read_bytes()==serial_payload([0,0x9abcdef0,0x12345678,1,0]),'partial invalid restore')
            require('REJECTED_BEFORE_MUTATION zero_edges=1' in Path(item['log']).read_text(),'invalid image not rejected')
        for item in r['corruptions'][backend]:
            dest=Path(item['output']); cut=item['cut']; _,trace,_=oracle(8)
            require(json.loads((dest/'first-divergence.json').read_text())==dict(operation=cut+1,fixture_cycle=101+cut,
                    acknowledged=0,expected=trace[cut],actual=item['expected_actual']) and
                    (dest/'trace').read_bytes()==b'','wrong first read divergence or acknowledged failure')
    parent=Path(r['serial_summary']); require(file_sha(parent)==r['serial_summary_sha256'],'changed actual parent evidence')
    require(audit_serial(parent)['actual_serial_images']==384,'missing real HTIF serial checks')
    images=0
    for backend in ('native','vcs-dpi'):
        for count in (1,3,10):
            case=parent.parent/('actual-'+backend)/str(count); wanted=actual_read_images(count)
            require({p.stem for p in case.glob('*.read')}==set(wanted),'missing actual read cuts')
            for name,image in wanted.items():
                require((case/(name+'.read')).read_bytes()==image,'actual original read differs '+name); images+=1
    require(len(r['actual_restores'])==2*images,'missing fresh actual readbacks')
    for c in r['actual_restores']:
        require(Path(c['readback']).read_bytes()==Path(c['image']).read_bytes() and
                Path(c['serial_readback']).read_bytes()==Path(c['serial_image']).read_bytes(),'actual complete fresh state differs')
        require('COMPLETE_READBACK zero_edges=1 restore_services=0' in Path(c['log']).read_text(),'actual restore called services')
    for c in r['commands']:
        log=Path(c['log']).read_text()
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(c['expected_exit'])),'unbound VCS environment/exit')
        require(not any(s in log for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),'sanitizer failure')
    return dict(status='passed',summary=str(path),fresh_fixture_restores=restores,complete_fixture_readbacks=readbacks,
                continued_records=records,invalid_processes=sum(map(len,r['invalid_cases'].values())),first_divergences=4,
                actual_read_images=images,actual_fresh_restores=len(r['actual_restores']),level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--out',type=Path); p.add_argument('--serial-summary',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit),indent=2));return
    require(a.out is not None and a.serial_summary is not None and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs output and actual serial summary')
    require(os.environ.get('VCS_HOME')==_toolchain.VCS_HOME and os.environ.get('CXX')==_toolchain.CXX,'source vcs-env.sh LAST')
    parent=a.serial_summary.resolve(); require(audit_serial(parent)['actual_serial_images']==384,'need actual serial capture')
    a.out.resolve().mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    fixture=TESTS/'tsi_serial_read_checkpoint.cc';sv=TESTS/'tsi_serial_read_checkpoint_tb.sv'
    inputs=[fixture,sv,Path(__file__),STUBS/'fesvr/tsi_serial_read.h',STUBS/'fesvr/tsi_serial_state.h',STUBS/'fesvr/tsi.h',
            STUBS/'fesvr/owned_fesvr_tsi.cc',TESTS/'verify_tsi_serial_vcs.py',TESTS/'verify_loadmem_read_checkpoint_vcs.py',
            TESTS/'verify_semantic_vcs.py',CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',
            ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots=out/'source-snapshots';snapshots.mkdir();bindings=[]
    for f in inputs:
        digest=file_sha(f);snapshot=snapshots/digest
        if not snapshot.exists(): shutil.copyfile(f,snapshot)
        bindings.append(dict(path=str(f),sha256=digest,snapshot=str(snapshot)))
    commands=[]
    def execute(argv,log,expected=0):
        argv=['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])]; result=run(argv,log,cwd=out,expected=expected)
        c=dict(cwd=str(out.relative_to(ROOT)),argv=argv,log=str(log),expected_exit=expected,pid=int(re.search(r'fresh_process_pid=(\d+)',result)[1]))
        commands.append(c);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');return c
    include=f'-std=c++17 -I{CC} -I{STUBS}';native=out/'read-native';simv=out/'read-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-Wall','-Wextra','-Werror','-no-pie','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',fixture,'-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_serial_read_checkpoint_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_SERIAL_READ_DPI','-o',simv,sv,fixture],out/'vcs-build.log')
    def invoke(backend,mode,target,cmd='unused',wanted='unused',image='unused',queue='unused',cut=0,expected=0):
        values=list(map(str,[mode,target,cmd,wanted,image,queue,cut]));binary=native if backend=='native-sanitized' else simv
        argv=[binary,*values] if backend=='native-sanitized' else [binary,'-no_save',*['+'+k+'='+v for k,v in zip(('mode','out','commands','expected','image','queue','cut'),values)]]
        return execute(argv,target.parent/(target.name+'.log'),expected)
    invalid_cases={};corruptions={};actual_restores=[]
    for backend in ('native-sanitized','vcs-dpi'):
        base=out/backend;base.mkdir(); invoke(backend,'check',base/'checks')
        for size in SIZES:
            case=base/str(size);case.mkdir();ops,trace,states=oracle(size);cmd=case/'commands.txt';wanted=case/'expected.txt'
            cmd.write_text('\n'.join(ops)+'\n');wanted.write_text('\n'.join(trace)+'\n');invoke(backend,'reference',case/'reference',cmd,wanted)
            for cut in cuts(size,states): invoke(backend,'restore',case/f'restore-{cut}',cmd,wanted,case/f'reference/cut-{cut}.read',case/f'reference/cut-{cut}.serial',cut)
        valid=payload(2,ADDRESS,8,[0xffffffff]); valid_queue=base/'valid.serial';valid_queue.write_bytes(serial_payload())
        def change(at,value):
            result=bytearray(valid);struct.pack_into('<Q',result,at,value);return bytes(result)
        invalids={'missing':None,'empty':b'','truncated':valid[:-1],'extra':valid+b'\0','extra-word':valid+words(0),
                  **{name:change(at,v) for name,at,v in [('magic',0,0),('version',8,2),('kind',16,19),('config-count',24,3),
                  ('max-size',32,4096),('word-size',40,8),('addr-chunks',48,1),('len-chunks',56,1),('phase',64,4),
                  ('idle',64,0),('issue-with-response',64,1),('early-complete',64,3),('zero-size',80,0),
                  ('unaligned-size',80,7),('huge-size',80,1028),('cursor',88,2**64-1),('wide-response',96,2**32)]}}
        invalid_cases[backend]=[]
        for name,state in invalids.items():
            image=base/('invalid-'+name+'.read')
            if state is not None: image.write_bytes(state)
            dest=base/('invalid-'+name);c=invoke(backend,'invalid',dest,image=image,queue=valid_queue)
            invalid_cases[backend].append(dict(case=name,output=str(dest),log=c['log']))
        # Both owners validate before deposits; a valid read + missing/bad FIFO
        # must not change the pre-existing read cursor/data.
        good=base/'valid.read';good.write_bytes(valid)
        for name,state in [('missing-queue',None),('truncated-queue',serial_payload()[:-1]),('incompatible-queue',config(19,4,2,2,512)+words(0,0))]:
            queue=base/(name+'.serial')
            if state is not None:queue.write_bytes(state)
            dest=base/name;c=invoke(backend,'invalid',dest,image=good,queue=queue)
            invalid_cases[backend].append(dict(case=name,output=str(dest),log=c['log']))
        corruptions[backend]=[];ops,trace,states=oracle(8);case=base/'8'
        for name,cut,offset in [('address',2,72),('response',ops.index('RESULT'),96)]:
            bad=bytearray(states[cut][0]);struct.pack_into('<Q',bad,offset,struct.unpack_from('<Q',bad,offset)[0]^1)
            image=base/(name+'-corrupt.read');image.write_bytes(bad);dest=base/(name+'-corruption')
            c=invoke(backend,'restore',dest,case/'commands.txt',case/'expected.txt',image,case/f'reference/cut-{cut}.serial',cut,2)
            actual=trace[cut].replace(str(ADDRESS),str(ADDRESS^1)) if name=='address' else trace[cut].replace('RESULT 0 ','RESULT 1 ')
            corruptions[backend].append(dict(case=name,cut=cut,output=str(dest),log=c['log'],expected_actual=actual))
    for source_backend in ('native','vcs-dpi'):
        for count in (1,3,10):
            case=parent.parent/('actual-'+source_backend)/str(count)
            for name,state in actual_read_images(count).items():
                image=case/(name+'.read');queue=case/(name+'.serial');require(image.read_bytes()==state,'actual original read differs '+name)
                for backend in ('native-sanitized','vcs-dpi'):
                    dest=out/f'restore-actual-{source_backend}-{count}-{name}-{backend}'
                    c=invoke(backend,'readback',dest,image=image,queue=queue)
                    actual_restores.append(dict(c,image=str(image),serial_image=str(queue),readback=str(dest/'preedge.read'),serial_readback=str(dest/'preedge.serial')))
    for b in bindings:require(file_sha(b['path'])==b['sha256'],'source changed during execution')
    report=dict(status='passed',scope='serial read and FIFO components only; HTIF caller/CPU restore pending',commands=commands,
                source_inputs=bindings,invalid_cases=invalid_cases,corruptions=corruptions,actual_restores=actual_restores,
                serial_summary=str(parent),serial_summary_sha256=file_sha(parent),
                artifact_sha256={str(f):file_sha(f) for f in sorted(out.rglob('*')) if f.is_file()},level1_verified=False,level2_verified=False)
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(audit(path),indent=2))


if __name__=='__main__': main()
