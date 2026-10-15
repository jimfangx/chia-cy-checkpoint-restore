"""Fresh complete serial FIFO restores and actual installed-HTIF protocol cuts.

All operations are component boundaries, not Rocket checkpoint target cycles.
The independent Python FIFO oracle never executes the C++ serializer.
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
from tools.checkpoint_formats.tests.fesvr_overlay import overlay_inputs, build_overlay
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf, expected_images
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTCHIP, FESVR, TESTS


def payload(requests=(), responses=()):
    return config(19, 4, 2, 2, 1024)+words(len(requests), *requests, len(responses), *responses)


def oracle():
    requests, responses, ops, trace, states = [], [], [], [], [payload()]
    def action(text):
        fields=text.split(); op=fields[0]; result=text
        if op in ('READ','WRITE'):
            address=int(fields[1]); data=list(map(int,fields[2:])) if op=='WRITE' else []
            length=len(data) if op=='WRITE' else int(fields[2])//4
            requests.extend([int(op=='WRITE'), address & 0xffffffff, address >> 32, length-1, 0, *data])
        elif op=='SEND': responses.append(int(fields[1]))
        elif op=='REQUEST': result='REQUEST '+str(requests.pop(0))
        elif op=='RESPONSE': result='RESPONSE '+str(responses.pop(0))
        elif op=='TICK':
            valid,word,ready=map(int,fields[1:])
            if valid: responses.append(word)
            if ready and requests: requests.pop(0)
        elif op=='QUERY': result=f'QUERY REQUEST={int(bool(requests))} RESPONSE={int(bool(responses))}'
        else: raise ValueError(op)
        ops.append(text); trace.append(f'OP {len(ops)} C {100+len(ops)} '+result)
        states.append(payload(requests,responses))
    action('QUERY'); action('READ 4294967292 8'); action('QUERY')
    action('WRITE 9223372036854775808 0 4294967295 2166572391 42')
    action('SEND 4294967295'); action('SEND 0'); action('QUERY')
    for _ in range(3): action('REQUEST')
    action('TICK 1 2309737967 1'); action('RESPONSE'); action('QUERY')
    while requests: action('REQUEST')
    while responses: action('RESPONSE')
    action('TICK 0 123 1'); action('QUERY'); action('READ 18446744073709551608 8')
    action('SEND 42'); action('TICK 1 305419896 0')
    while requests: action('REQUEST')
    while responses: action('RESPONSE')
    action('QUERY')
    return ops,trace,states


def actual_images(count):
    # Each original TestChip init read, HTIF tohost request and serial response
    # is independently reconstructed; no image contents drive the expected bytes.
    result={name:payload() for name in expected_images(count)}
    for name,packet in [('init',[0,0x10000010,0,0,0]),('first',[0,0x80002000,0,1,0]),
                        *[(f'busy-{i}',[0,0x80002000,0,1,0]) for i in range(3)]]:
        result[name+'-queued']=payload(packet)
        for i in range(5): result[name+f'-pop-{i}']=payload(packet[i+1:])
    result['init-response']=payload(responses=[0x89abcdef])
    for loop in range(3):
        for half in range(2): result[f'poll-response-{loop}-{half}']=payload(responses=[0])
    return result


def audit(path):
    path=path.resolve(); r=json.loads(path.read_text()); out=path.parent
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'],'incorrect serial component scope')
    require(set(r['artifact_sha256'])=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'changed evidence membership')
    for p,d in r['artifact_sha256'].items(): require(file_sha(p)==d,'changed serial evidence '+p)
    bindings={b['path']:b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed serial source snapshot')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    ops,trace,states=oracle(); restores=readbacks=records=0
    for backend in ('native-sanitized','vcs-dpi'):
        base=out/backend
        require((base/'commands.txt').read_text().splitlines()==ops and (base/'expected.txt').read_text().splitlines()==trace,'changed FIFO oracle')
        require(int(re.search(r'ATOMIC_CHECKS (\d+)',(base/'checks.log').read_text())[1])>=300,'missing atomic checks')
        require((base/'reference/preedge.owner').read_bytes()==states[0] and
                (base/'reference/trace').read_text().splitlines()==trace,'wrong original FIFO reference')
        for cut,state in enumerate(states):
            require((base/f'reference/cut-{cut}.owner').read_bytes()==state,'incomplete source FIFO state')
            dest=base/f'restore-{cut}'
            require((dest/'preedge.owner').read_bytes()==state and (dest/'trace').read_text().splitlines()==trace[cut:],'fresh FIFO continuation differs')
            for i in range(cut,len(states)):
                require((dest/f'cut-{i}.owner').read_bytes()==states[i],'continued FIFO state differs'); readbacks+=1
            restores+=1; records+=len(trace)-cut
        for item in r['invalid_cases'][backend]:
            dest=Path(item['output'])
            require({p.name for p in dest.iterdir()}=={'unchanged.owner'} and
                    (dest/'unchanged.owner').read_bytes()==payload([0,0x9abcdef0,0x12345678,1,0],[42]) and
                    'REJECTED_BEFORE_MUTATION zero_edges=1' in Path(item['log']).read_text(),'partial invalid FIFO restore')
        for item in r['corruptions'][backend]:
            dest=Path(item['output']); actual=json.loads((dest/'first-divergence.json').read_text()); cut=item['cut']
            require(actual==dict(operation=cut+1,fixture_cycle=101+cut,acknowledged=0,expected=trace[cut],actual=item['expected_actual']) and
                    (dest/'trace').read_bytes()==b'','wrong first FIFO divergence or acknowledged failure')
    require((out/'polling.elf').read_bytes()==polling_elf(),'changed actual ELF workload')
    actual_count=0
    for backend in ('native','vcs-dpi'):
        for count in (1,3,10):
            base=out/('actual-'+backend)/str(count); wanted=actual_images(count)
            require({p.stem for p in base.glob('*.serial')}==set(wanted),'incomplete actual serial cut inventory')
            for name,state in wanted.items():
                require((base/(name+'.serial')).read_bytes()==state,'actual serial bytes differ '+name); actual_count+=1
            for name,state in expected_images(count).items():
                require((base/(name+'.host')).read_bytes()==state,'retained actual host-control differs')
            require(f'REAL_HTIF_HOST_CONTROL idle_count={count} child_waits=3 poll_loops=3 serial_words=25' in
                    (base.parent/(str(count)+'.log')).read_text(),'actual installed HTIF protocol incomplete')
    require(len(r['actual_restores'])==2*actual_count and len({c['pid'] for c in r['actual_restores']})==2*actual_count,'missing fresh actual FIFO restores')
    for c in r['actual_restores']:
        require(file_sha(c['image'])==c['image_sha256'] and Path(c['readback']).read_bytes()==Path(c['image']).read_bytes() and
                'COMPLETE_READBACK zero_edges=1 restore_services=0' in Path(c['log']).read_text(),'actual FIFO pre-edge restore differs')
    for c in r['commands']:
        log=Path(c['log']).read_text()
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(c['expected_exit'])),'unbound FIFO VCS environment/exit')
        require(not any(s in log for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),'FIFO sanitizer failure')
    return dict(status='passed',summary=str(path),fresh_fixture_restores=restores,complete_fixture_readbacks=readbacks,
                continued_records=records,invalid_processes=sum(map(len,r['invalid_cases'].values())),first_divergences=4,
                actual_serial_images=actual_count,actual_fresh_restores=len(r['actual_restores']),level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit),indent=2));return
    require(a.out is not None and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs output')
    require(os.environ.get('VCS_HOME')=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX')=='/usr/bin/g++-13','source vcs-env.sh LAST')
    a.out.resolve().mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    fixture=TESTS/'tsi_serial_checkpoint.cc'; sv=TESTS/'tsi_serial_checkpoint_tb.sv'; library=FESVR/'lib/libfesvr.a'
    sources=[TESTS/'tsi_host_control_fesvr.cc',STUBS/'fesvr/firesim_tsi.cc',STUBS/'fesvr/owned_fesvr_tsi.cc',TESTCHIP/'testchip_tsi.cc',TESTCHIP/'testchip_htif.cc']
    inputs=[fixture,sv,*sources,TESTS/'tsi_host_control_fesvr_tb.sv',library,Path(__file__),
            TESTS/'verify_tsi_host_control_fesvr_vcs.py',TESTS/'verify_tsi_host_control_vcs.py',TESTS/'verify_firesim_tsi_loadmem_vcs.py',
            TESTS/'verify_loadmem_read_checkpoint_vcs.py',TESTS/'verify_semantic_vcs.py',
            *sorted((STUBS/'fesvr').glob('*.h')),*sorted(TESTCHIP.glob('*.h')),*sorted((FESVR/'include/fesvr').glob('*.h')),
            ROOT/'toolchains/riscv-tools/riscv-isa-sim/fesvr/tsi.h',ROOT/'toolchains/riscv-tools/riscv-isa-sim/fesvr/tsi.cc',
            CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    inputs = [*inputs, *overlay_inputs()]
    snapshots=out/'source-snapshots';snapshots.mkdir();bindings=[]
    for f in inputs:
        digest=file_sha(f);snapshot=snapshots/digest
        if not snapshot.exists(): shutil.copyfile(f,snapshot)
        bindings.append(dict(path=str(f),sha256=digest,snapshot=str(snapshot)))
    commands=[]
    def execute(argv,log,expected=0):
        argv=['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])];result=run(argv,log,cwd=out,expected=expected)
        c=dict(cwd=str(out.relative_to(ROOT)),argv=argv,log=str(log),expected_exit=expected,pid=int(re.search(r'fresh_process_pid=(\d+)',result)[1]))
        commands.append(c);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');return c
    library = build_overlay(out, execute)
    include=f'-std=c++17 -I{CC} -I{STUBS}';native=out/'serial-native';simv=out/'serial-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-Wall','-Wextra','-Werror','-no-pie','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',fixture,'-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_serial_checkpoint_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_SERIAL_DPI','-o',simv,sv,fixture],out/'vcs-build.log')
    def invoke(backend,mode,target,cmd='unused',wanted='unused',image='unused',cut=0,expected=0):
        values=list(map(str,[mode,target,cmd,wanted,image,cut]));binary=native if backend=='native-sanitized' else simv
        argv=[binary,*values] if backend=='native-sanitized' else [binary,'-no_save',*['+'+k+'='+v for k,v in zip(('mode','out','commands','expected','image','cut'),values)]]
        return execute(argv,target.parent/(target.name+'.log'),expected)
    invalid_cases={};corruptions={};actual_restores=[];ops,trace,states=oracle()
    for backend in ('native-sanitized','vcs-dpi'):
        base=out/backend;base.mkdir();cmd=base/'commands.txt';wanted=base/'expected.txt'
        cmd.write_text('\n'.join(ops)+'\n');wanted.write_text('\n'.join(trace)+'\n')
        invoke(backend,'check',base/'checks');invoke(backend,'reference',base/'reference',cmd,wanted)
        for cut in range(len(states)): invoke(backend,'restore',base/f'restore-{cut}',cmd,wanted,base/f'reference/cut-{cut}.owner',cut)
        valid=payload([0,0x10000010,0,0,0],[42])
        def change(at,value):
            result=bytearray(valid);struct.pack_into('<Q',result,at,value);return bytes(result)
        invalids={'missing':None,'empty':b'','truncated':valid[:-1],'extra':valid+b'\0','extra-word':valid+words(0),
                  'magic':change(0,0),'version':change(8,2),'kind':change(16,18),'config-count':change(24,0),
                  'word-size':change(32,8),'addr-chunks':change(40,1),'len-chunks':change(48,1),'chunk-size':change(56,512),
                  'request-count-huge':change(64,2**64-1),'request-count-short':change(64,4),
                  'missing-response-count':valid[:112],'response-count-huge':change(112,2**64-1),'response-count-short':change(112,0),
                  'request-wide':change(72,2**32),'response-wide':change(120,2**32)}
        invalid_cases[backend]=[]
        for name,state in invalids.items():
            image=base/('invalid-'+name+'.owner')
            if state is not None: image.write_bytes(state)
            dest=base/('invalid-'+name);c=invoke(backend,'invalid',dest,image=image)
            invalid_cases[backend].append(dict(case=name,image=str(image),output=str(dest),log=c['log']))
        corruptions[backend]=[]
        for name,op in [('request','REQUEST'),('response','RESPONSE')]:
            cut=ops.index(op);bad=bytearray(states[cut]);nr=struct.unpack_from('<Q',bad,64)[0]
            offset=72 if name=='request' else 80+8*nr
            struct.pack_into('<Q',bad,offset,struct.unpack_from('<Q',bad,offset)[0]^1)
            image=base/(name+'-corrupt.owner');image.write_bytes(bad);dest=base/(name+'-corruption')
            c=invoke(backend,'restore',dest,cmd,wanted,image,cut,2)
            value=int(trace[cut].split()[-1])^1
            corruptions[backend].append(dict(case=name,cut=cut,output=str(dest),log=c['log'],expected_actual=f'OP {cut+1} C {101+cut} {op} {value}'))
    elf=out/'polling.elf';elf.write_bytes(polling_elf());actual_native=out/'actual-native-bin';actual_simv=out/'actual-simv'
    include+=f' -I{TESTCHIP} -I{FESVR/"include"}'
    execute([os.environ['CXX'],*shlex.split(include),'-g',*sources,library,'-lpthread','-o',actual_native],out/'actual-native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_host_control_fesvr_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"actual-csrc"}','-CFLAGS',include+' -DTSI_HOST_FESVR_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread','-o',actual_simv,TESTS/'tsi_host_control_fesvr_tb.sv',*sources],out/'actual-vcs-build.log')
    for backend in ('native','vcs-dpi'):
        base=out/('actual-'+backend);base.mkdir()
        for count in (1,3,10):
            case=base/str(count)
            argv=[actual_native,elf,case,count] if backend=='native' else [actual_simv,'-no_save','+elf='+str(elf),'+out='+str(case),'+count='+str(count)]
            execute(argv,base/(str(count)+'.log'))
            wanted=actual_images(count)
            require({p.stem for p in case.glob('*.serial')}==set(wanted),'wrong actual cut inventory')
            for name,state in wanted.items():
                image=case/(name+'.serial');require(image.read_bytes()==state,'actual serial differs '+name)
                for restored in ('native-sanitized','vcs-dpi'):
                    dest=out/f'restore-actual-{backend}-{count}-{name}-{restored}'
                    c=invoke(restored,'readback',dest,image=image)
                    actual_restores.append(dict(c,image=str(image),image_sha256=file_sha(image),readback=str(dest/'preedge.owner')))
    for b in bindings: require(file_sha(b['path'])==b['sha256'],'serial source changed during execution')
    report=dict(status='passed',scope='complete serial FIFO components; HTIF/context/TestChip/CPU checkpoint pending',commands=commands,
                source_inputs=bindings,invalid_cases=invalid_cases,corruptions=corruptions,actual_restores=actual_restores,
                artifact_sha256={str(f):file_sha(f) for f in sorted(out.rglob('*')) if f.is_file()},level1_verified=False,level2_verified=False)
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(audit(path),indent=2))


if __name__=='__main__': main()
