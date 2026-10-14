"""Independent fresh native/VCS restores of production TSI bridge host control.

Every state word and callback order is checked at every completed operation cut.
These fixture labels and service inputs cannot certify CPU/HTIF continuation.
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
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words

TESTS=Path(__file__).resolve().parent
CC=ROOT/'sims/firesim/sim/midas/src/main/cc'
STUBS=ROOT/'generators/firechip/bridgestubs/src/main/cc'
VARIANTS=[(fast,wait) for fast in (0,1) for wait in (0,1,8)]


def identity(fast,wait):
    result=config(17,4,0x1040,2,(-0x80000000) % 2**64)
    for text in (b'four-hart-program', b'+fesvr-step-size=128'):
        result+=words(len(text))+text
    return result+words(128,2004765,wait,fast)


def oracle(initial_fast,initial_wait):
    # Expand the original bridge control flow from independent scheduled
    # service results, without calling the new C++ state implementation.
    fast,wait,initialized=initial_fast,initial_wait,0
    commands,trace,states=[],[],[]
    def snapshot(): states.append(identity(initial_fast,initial_wait)+words(wait,initialized+2*fast))
    def op(command):
        nonlocal fast,wait,initialized
        fields=command.split(); actions=[]
        if fields[0]=='INIT':
            actions=['CREATE',f'STEP={2004765 if fast else 128}']
            if not fast: actions+=['LOADED_TARGET']
            actions+=['GO'];initialized=1
        elif fields[0]=='QUERY': actions=['QUERY='+fields[1]]
        else:
            done,before,after,pending,stop,loaded,sent=map(int,fields[1:])
            actions=[f'DONE={done}']
            if done:
                if wait: wait-=1;actions+=['GO']
                else:
                    actions+=['RECEIVE',f'AVAILABLE={before}']
                    if not before: actions+=['ADVANCE'];before=after
                    actions+=[f'REQUESTS={pending}']
                    if pending: actions+=['BYPASS']
                    actions+=[f'TERMINATED={stop}']
                    if not stop:
                        actions+=['SEND'];before=sent
                        if fast:
                            actions+=[f'LOADED_HOST={loaded}']
                            if loaded:
                                actions+=[f'AVAILABLE={before}']
                                if not before: actions+=['LOADED_TARGET','STEP=128'];fast=0
                        actions+=['GO']
        commands.append(command)
        trace.append(f'OP {len(commands)} C {100+len(commands)} '+fields[0]+' '+' '.join(actions))
        snapshot()
    snapshot();op('INIT');op('QUERY 0')
    for _ in range(initial_wait):
        op('TICK 0 1 1 1 1 1 1');op('TICK 1 1 1 1 1 1 1')
    cut=len(commands)
    # Both ways of supplying FESVR requests, loaded transition held by serial
    # data, no-done/terminated branches, one-time step write and signed bool queries.
    for command in ('TICK 1 0 1 1 0 0 1','TICK 0 0 0 0 0 1 0',
                    'TICK 1 1 0 0 0 1 1','QUERY 1','TICK 1 1 0 1 1 1 0',
                    'TICK 1 0 0 1 0 1 0','TICK 1 0 0 0 0 1 0',
                    'TICK 1 1 0 0 0 0 0','QUERY 0','TICK 1 0 0 0 1 0 0'):
        op(command)
    return commands,trace,states,cut


def audit(path):
    path=path.resolve(); report=json.loads(path.read_text()); out=path.parent
    require(report['status']=='passed' and report['level1_verified'] is False and
            report['level2_verified'] is False,'component cannot certify CPU acceptance')
    catalog=report['artifact_sha256']
    require(set(catalog)=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'changed evidence membership')
    for p,digest in catalog.items(): require(file_sha(p)==digest,'changed bridge evidence '+p)
    bindings={b['path']:b for b in report['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed bridge source snapshot')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    restores=readbacks=records=0; atomic={}
    for backend in ('native-sanitized','vcs-dpi'):
        base=out/backend; atomic[backend]={}
        for fast,wait in VARIANTS:
            name=f'{fast}-{wait}'; case=base/name
            ops,trace,states,_=oracle(fast,wait)
            require((case/'commands.txt').read_text().splitlines()==ops and
                    (case/'expected.txt').read_text().splitlines()==trace,'changed independent oracle')
            match=re.search(r'ATOMIC_CHECKS (\d+)',(case/'checks.log').read_text())
            require(match and int(match[1])>400,'missing lifecycle/atomic/callback checks')
            atomic[backend][name]=int(match[1])
            reference=case/'reference'
            require((reference/'preedge.owner').read_bytes()==states[0] and
                    (reference/'trace').read_text().splitlines()==trace,'changed reference')
            for cut,state in enumerate(states):
                require((reference/f'cut-{cut}.owner').read_bytes()==state,'incomplete source state')
                resumed=case/f'restore-{cut}'
                require((resumed/'preedge.owner').read_bytes()==state,'incomplete zero-edge readback')
                require((resumed/'trace').read_text().splitlines()==trace[cut:],'wrong callback timing/order')
                for j in range(cut,len(states)):
                    require((resumed/f'cut-{j}.owner').read_bytes()==states[j],'changed resumed state')
                    readbacks+=1
                restores+=1;records+=len(trace)-cut
        for invalid in report['invalid_cases'][backend]:
            dest=Path(invalid['output']);fast,wait=invalid['variant']
            sentinel=identity(fast,wait)+words(wait,1+2*fast)
            require(set(p.name for p in dest.iterdir())=={'unchanged.owner'} and
                    (dest/'unchanged.owner').read_bytes()==sentinel and
                    'REJECTED_BEFORE_MUTATION calls=0' in Path(invalid['log']).read_text(),
                    'invalid image partially restored/called services')
        ops,trace,states,cut=oracle(1,8)
        # A valid delayed cursor produces GO instead of the very next receive.
        actual=f'OP {cut+1} C {101+cut} TICK DONE=1 GO'
        failure=json.loads((base/'corruption/first-divergence.json').read_text())
        require(failure==dict(operation=cut+1,fixture_cycle=101+cut,acknowledged=0,
                              expected=trace[cut],actual=actual),'wrong first divergent boundary')
        require((base/'corruption/trace').read_bytes()==b'','divergent call acknowledged')
    for command in report['commands']:
        log=Path(command['log']).read_text()
        require(command['argv'][:2]==['bash','-lc'] and command['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(command['expected_exit'])),'unbound native environment/result')
        require(not any(t in log for t in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),
                'sanitizer failure')
    return dict(status='passed',summary=str(path),fresh_component_restores=restores,
                complete_state_readbacks=readbacks,continued_records=records,atomic_checks=atomic,
                invalid_processes=sum(map(len,report['invalid_cases'].values())),first_divergences=2,
                level1_verified=False,level2_verified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path);parser.add_argument('--audit',type=Path)
    args=parser.parse_args()
    if args.audit: print(json.dumps(audit(args.audit),indent=2));return
    require(args.out is not None and args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'diagnostics must be under runs')
    require(os.environ.get('VCS_HOME')=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX')=='/usr/bin/g++-13','source vcs-env.sh LAST')
    args.out.resolve().mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='invocation-',dir=args.out.resolve()))
    sources=[TESTS/'tsi_bridge_checkpoint.cc']
    inputs=[*sources,Path(__file__),TESTS/'tsi_bridge_checkpoint_tb.sv',TESTS/'verify_loadmem_read_checkpoint_vcs.py',
            STUBS/'bridges/tsi_bridge_state.h',STUBS/'bridges/tsibridge.h',STUBS/'bridges/tsibridge.cc',
            CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',ROOT/'env.sh',ROOT/'sims/firesim/env.sh',
            ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots=out/'source-snapshots';snapshots.mkdir();bindings=[]
    for p in inputs:
        digest=file_sha(p);snapshot=snapshots/digest
        if not snapshot.exists(): shutil.copyfile(p,snapshot)
        bindings.append(dict(path=str(p),sha256=digest,snapshot=str(snapshot)))
    commands=[]
    def execute(argv,log,expected=0):
        command=['bash','-lc',ENVIRONMENT+shlex.join([str(a) for a in argv])]
        result=run(command,log,cwd=out,expected=expected)
        commands.append(dict(cwd=str(out.relative_to(ROOT)),argv=command,log=str(log),expected_exit=expected,
                             pid=int(re.search(r'fresh_process_pid=(\d+)',result)[1])))
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    include=f'-std=c++17 -I{CC} -I{STUBS}';native=out/'bridge-native';simv=out/'bridge-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-Wall','-Wextra','-Werror','-g','-no-pie',
             '-fsanitize=address,undefined','-fno-omit-frame-pointer',*sources,'-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps',
             '-top','tsi_bridge_checkpoint_tb','-cc',os.environ['CC'],'-cpp',os.environ['CXX'],
             f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_BRIDGE_CHECKPOINT_DPI',
             '-o',simv,TESTS/'tsi_bridge_checkpoint_tb.sv',*sources],out/'vcs-build.log')
    invalid_cases={}
    for backend in ('native-sanitized','vcs-dpi'):
        base=out/backend;base.mkdir()
        def invoke(mode,target,variant,cmd='unused',wanted='unused',image='unused',cut=0,failure=False):
            values=list(map(str,[mode,target,cmd,wanted,image,cut,variant]))
            argv=[native,*values] if backend=='native-sanitized' else [simv,'-no_save',
                  *['+'+k+'='+v for k,v in zip(('mode','out','commands','expected','image','cut','variant'),values)]]
            log=target.parent/(target.name+'.log');execute(argv,log,2 if failure else 0);return log
        for fast,wait in VARIANTS:
            case=base/f'{fast}-{wait}';case.mkdir();variant=f'{fast}:{wait}'
            ops,trace,states,_=oracle(fast,wait)
            cmd=case/'commands.txt';wanted=case/'expected.txt'
            cmd.write_text('\n'.join(ops)+'\n');wanted.write_text('\n'.join(trace)+'\n')
            invoke('check',case/'checks',variant)
            invoke('reference',case/'reference',variant,cmd,wanted)
            for cut in range(len(states)):
                invoke('restore',case/f'restore-{cut}',variant,cmd,wanted,case/'reference'/f'cut-{cut}.owner',cut)
        ops,trace,states,cut=oracle(1,8);valid=states[cut];offset=len(identity(1,8))
        def change(pos,value):
            result=bytearray(valid);struct.pack_into('<Q',result,pos,value);return bytes(result)
        invalids={'missing':None,'empty':b'','truncated':valid[:-1],'trailing':valid+b'\0',
                  'magic':change(0,0),'version':change(8,2),'kind':change(16,1),'mmio':change(40,1),
                  'memory_offset':change(56,0),'args':valid[:72]+b'X'+valid[73:],
                  'step':change(offset-32,256),'loading_step':change(offset-24,8),
                  'initial_wait':change(offset-16,9),'initial_fast':change(offset-8,0),
                  'cursor_overflow':change(offset,2**32),'cursor_too_large':change(offset,9),
                  'flags':change(offset+8,4),'uninitialized_partial':change(offset+8,2)}
        # False fast flag cannot coexist with an undrained initial reset delay.
        lifecycle=bytearray(change(offset,1));struct.pack_into('<Q',lifecycle,offset+8,1)
        invalids['fast_transition_before_wait']=bytes(lifecycle)
        invalids['uninitialized_transition']=change(offset+8,0)
        rejected=[]
        for name,payload in invalids.items():
            image=base/('invalid-'+name+'.owner')
            if payload is not None:image.write_bytes(payload)
            target=base/('invalid-'+name);log=invoke('invalid',target,'1:8',image=image)
            rejected.append(dict(case=name,image=str(image),output=str(target),log=str(log),variant=[1,8]))
        invalid_cases[backend]=rejected
        image=base/'corrupted.owner';image.write_bytes(change(offset,1))
        invoke('restore',base/'corruption','1:8',base/'1-8/commands.txt',base/'1-8/expected.txt',image,cut,True)
    for b in bindings:require(file_sha(b['path'])==b['sha256'],'source changed during bridge check')
    report=dict(status='passed',scope='production bridge host control component; CPU and HTIF pending',
                commands=commands,source_inputs=bindings,invalid_cases=invalid_cases,
                artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
                level1_verified=False,level2_verified=False)
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(audit(path),indent=2))


if __name__=='__main__':main()
