"""Complete fresh native/VCS component restores of FireSim idle/reset control.

An independent original-loop oracle checks every completed transition and word.
Component operation labels are not Rocket target cycles or CPU acceptance.
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
import threading
from tools.checkpoint_formats.tests.native_parallel import checked_map

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import audit as audit_fesvr

TESTS = Path(__file__).resolve().parent
CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
STUBS = ROOT / 'generators/firechip/bridgestubs/src/main/cc'
COUNTS = (0, 1, 3, 10, 2**64-1)


def oracle(count):
    # Expand the original idle for-loop and reset while-loop, recording the
    # position of their next action. No C++ owner or image drives this oracle.
    phase, remaining, busy, host, target = 0, 0, 0, 0, 0
    ops, trace, states = [], [], []
    def snapshot(): states.append(config(18, count) + words(phase, remaining, busy+2*host+4*target))
    def action(op, result=None):
        ops.append(op)
        trace.append(f'OP {len(ops)} C {100+len(ops)} ' + (op if result is None else result))
        snapshot()
    def query(): action('QUERY', f'QUERY BUSY={busy} HOST={host}')
    def set_target(v):
        nonlocal target
        target=v; action(f'TARGET {v}')
    def idle():
        nonlocal phase, remaining, busy
        phase, remaining, busy = 1, count, 0; action('IDLE_BEGIN')
        for _ in range(min(count, 10)):
            remaining -= 1; action('IDLE_NEXT', 'IDLE_NEXT YIELD'); query()
        if count <= 10:
            phase, busy = 0, 1; action('IDLE_NEXT', 'IDLE_NEXT RETURN'); query()
    snapshot(); query(); set_target(1); set_target(0); idle()
    if count > 10: return ops, trace, states
    phase, host = 2, 1; action('RESET_BEGIN'); query()
    for _ in range(3): action('RESET_NEXT', 'RESET_NEXT YIELD')
    set_target(1); phase=3; action('RESET_NEXT', 'RESET_NEXT CHILD'); query()
    # Public target-loaded setter originally permits deassertion during child
    # reset; that does not undo the already-entered base reset operation.
    set_target(0); phase=0; action('RESET_END'); idle(); set_target(1)
    phase=2; action('RESET_BEGIN'); phase=3; action('RESET_NEXT', 'RESET_NEXT CHILD')
    phase=0; action('RESET_END'); query()
    return ops, trace, states


def audit(path):
    path=path.resolve(); r=json.loads(path.read_text()); out=path.parent
    require(r['status']=='passed' and r['level1_verified'] is False and r['level2_verified'] is False,
            'component evidence cannot certify CPU checkpoints')
    catalog=r['artifact_sha256']
    require(set(catalog)=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'changed evidence membership')
    for p,digest in catalog.items(): require(file_sha(p)==digest,'changed component artifact '+p)
    bindings={b['path']:b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed original source snapshot')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    restores=readbacks=records=0; atomic={}
    for backend in ('native-sanitized','vcs-dpi'):
        base=out/backend; atomic[backend]={}
        for count in COUNTS:
            case=base/str(count); ops,trace,states=oracle(count)
            require((case/'commands.txt').read_text().splitlines()==ops and
                    (case/'expected.txt').read_text().splitlines()==trace,'changed independent oracle')
            n=re.search(r'ATOMIC_CHECKS (\d+)',(case/'checks.log').read_text())
            require(n and int(n[1])>=200,'missing phase/atomic/interrupted checks')
            atomic[backend][str(count)]=int(n[1])
            require((case/'reference/preedge.owner').read_bytes()==states[0] and
                    (case/'reference/trace').read_text().splitlines()==trace,'reference mismatch')
            for cut,state in enumerate(states):
                require((case/f'reference/cut-{cut}.owner').read_bytes()==state,'incomplete original state')
                dest=case/f'restore-{cut}'
                require((dest/'preedge.owner').read_bytes()==state and
                        (dest/'trace').read_text().splitlines()==trace[cut:],'restore/readback/continuation mismatch')
                for i in range(cut,len(states)):
                    require((dest/f'cut-{i}.owner').read_bytes()==states[i],'wrong continued owner state')
                    readbacks+=1
                restores+=1; records+=len(trace)-cut
        for invalid in r['invalid_cases'][backend]:
            dest=Path(invalid['output'])
            require({p.name for p in dest.iterdir()}=={'unchanged.owner'} and
                    (dest/'unchanged.owner').read_bytes()==config(18,10)+words(0,0,4) and
                    'REJECTED_BEFORE_MUTATION zero_edges=1' in Path(invalid['log']).read_text(),
                    'invalid image partially restored')
        for item in r['corruptions'][backend]:
            actual=json.loads((Path(item['output'])/'first-divergence.json').read_text())
            ops,trace,states=oracle(10); cut=item['cut']
            result='IDLE_NEXT YIELD' if item['case']=='idle_cursor' else 'RESET_NEXT CHILD'
            require(actual==dict(operation=cut+1,fixture_cycle=101+cut,acknowledged=0,
                                 expected=trace[cut],actual=f'OP {cut+1} C {101+cut} '+result),
                    'wrong first divergent boundary')
            require((Path(item['output'])/'trace').read_bytes()==b'','divergent operation acknowledged')
    for c in r['commands']:
        log=Path(c['log']).read_text()
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(c['expected_exit'])),'unbound native command/environment/exit')
        require(not any(s in log for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),
                'sanitizer error')
    actual=r.get('actual_restores',[])
    if r.get('fesvr_summary'):
        parent=Path(r['fesvr_summary'])
        require(file_sha(parent)==r['fesvr_summary_sha256'] and audit_fesvr(parent)['actual_fesvr_complete_host_checks']==68,
                'actual source images did not pass independent audit')
        require(len(actual)==136 and len({a['pid'] for a in actual})==136,'missing fresh actual restores')
        for a in actual:
            require(file_sha(a['image'])==a['image_sha256'] and
                    Path(a['readback']).read_bytes()==Path(a['image']).read_bytes(),'actual pre-edge state mismatch')
            require('COMPLETE_READBACK zero_edges=1 restore_services=0' in Path(a['log']).read_text(),
                    'missing actual zero-edge/no-service readback')
    return dict(status='passed',summary=str(path),fresh_fixture_restores=restores,
                complete_fixture_readbacks=readbacks,continued_records=records,atomic_checks=atomic,
                invalid_processes=sum(map(len,r['invalid_cases'].values())),first_divergences=4,
                actual_fesvr_fresh_restores=len(actual),level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--out',type=Path)
    p.add_argument('--audit',type=Path); p.add_argument('--fesvr-summary',type=Path); a=p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit),indent=2)); return
    require(a.out is not None and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),
            'diagnostics must be under runs')
    require(os.environ.get('VCS_HOME')==_toolchain.VCS_HOME and
            os.environ.get('CXX')==_toolchain.CXX,'source vcs-env.sh LAST')
    parent=a.fesvr_summary.resolve() if a.fesvr_summary else None
    if parent: require(audit_fesvr(parent)['actual_fesvr_complete_host_checks']==68,'need complete actual images')
    a.out.resolve().mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    source=TESTS/'tsi_host_control_checkpoint.cc'; sv=TESTS/'tsi_host_control_checkpoint_tb.sv'
    inputs=[source,sv,Path(__file__),TESTS/'native_parallel.py',STUBS/'fesvr/tsi_host_control.h',STUBS/'fesvr/tsi_htif_poll.h',STUBS/'fesvr/firesim_tsi.h',
            STUBS/'fesvr/firesim_tsi.cc',CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',
            TESTS/'verify_semantic_vcs.py',TESTS/'verify_loadmem_read_checkpoint_vcs.py',
            TESTS/'verify_firesim_tsi_loadmem_vcs.py',ROOT/'env.sh',ROOT/'sims/firesim/env.sh',
            ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots=out/'source-snapshots'; snapshots.mkdir(); bindings=[]
    for f in inputs:
        digest=file_sha(f); snapshot=snapshots/digest
        if not snapshot.exists(): shutil.copyfile(f,snapshot)
        bindings.append(dict(path=str(f),sha256=digest,snapshot=str(snapshot)))
    commands=[];command_lock=threading.Lock()
    def execute(argv,log,expected=0):
        argv=['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])]
        result=run(argv,log,cwd=out,expected=expected)
        c=dict(cwd=str(out.relative_to(ROOT)),argv=argv,log=str(log),expected_exit=expected,
               pid=int(re.search(r'fresh_process_pid=(\d+)',result)[1]))
        with command_lock:
            commands.append(c); (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        return c
    include=f'-std=c++17 -I{CC} -I{STUBS}'; native=out/'host-native'; simv=out/'host-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-Wall','-Wextra','-Werror','-no-pie','-g',
             '-fsanitize=address,undefined','-fno-omit-frame-pointer',source,'-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps',
             '-top','tsi_host_control_checkpoint_tb','-cc',os.environ['CC'],'-cpp',os.environ['CXX'],
             f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_HOST_CHECKPOINT_DPI',
             '-o',simv,sv,source],out/'vcs-build.log')
    invalid_cases={}; corruptions={}; actual=[]
    for backend in ('native-sanitized','vcs-dpi'):
        base=out/backend; base.mkdir()
        def invoke(mode,target,count,cmd='unused',wanted='unused',image='unused',cut=0,failure=False):
            values=list(map(str,[mode,target,cmd,wanted,image,cut,count]))
            argv=[native,*values] if backend=='native-sanitized' else [simv,'-no_save',
                  *['+'+k+'='+v for k,v in zip(('mode','out','commands','expected','image','cut','variant'),values)]]
            return execute(argv,target.parent/(target.name+'.log'),2 if failure else 0)
        for count in COUNTS:
            case=base/str(count); case.mkdir(); ops,trace,states=oracle(count)
            cmd=case/'commands.txt'; wanted=case/'expected.txt'
            cmd.write_text('\n'.join(ops)+'\n'); wanted.write_text('\n'.join(trace)+'\n')
            invoke('check',case/'checks',count); invoke('reference',case/'reference',count,cmd,wanted)
            checked_map(lambda cut:invoke('restore',case/f'restore-{cut}',count,cmd,wanted,case/f'reference/cut-{cut}.owner',cut),range(len(states)))
        ops,trace,states=oracle(10); valid=config(18,10)+words(1,0,6)
        def change(pos,value):
            result=bytearray(valid); struct.pack_into('<Q',result,pos,value); return bytes(result)
        invalids={'missing':None,'empty':b'','truncated':valid[:-1],'trailing':valid+b'\0',
                  'magic':change(0,0),'version':change(8,2),'kind':change(16,17),
                  'config_count':change(24,0),'idle_config':change(32,11),'phase':change(40,4),
                  'idle_cursor':change(48,11),'idle_busy':change(56,7),'flags':change(56,8)}
        for name,phase,flags in [('ready_cursor',0,6),('reset_wait_cursor',2,6),('reset_child_cursor',3,6),
                                 ('reset_wait_no_host',2,4),('reset_child_no_host',3,4)]:
            invalids[name]=config(18,10)+words(phase,1 if name.endswith('cursor') else 0,flags)
        invalid_cases[backend]=[]
        for name,payload in invalids.items():
            image=base/('invalid-'+name+'.owner')
            if payload is not None: image.write_bytes(payload)
            target=base/('invalid-'+name); c=invoke('invalid',target,10,image=image)
            invalid_cases[backend].append(dict(case=name,image=str(image),output=str(target),log=c['log']))
        corruptions[backend]=[]
        for name,cut,payload in [('idle_cursor',ops.index('IDLE_NEXT',ops.index('IDLE_BEGIN'))+20,
                                 config(18,10)+words(1,1,0)),
                                ('reset_target',ops.index('RESET_NEXT'),config(18,10)+words(2,0,7))]:
            require(ops[cut]==('IDLE_NEXT' if name=='idle_cursor' else 'RESET_NEXT'),'bad corruption cut')
            image=base/(name+'.owner'); image.write_bytes(payload); target=base/('corruption-'+name)
            c=invoke('restore',target,10,base/'10/commands.txt',base/'10/expected.txt',image,cut,True)
            corruptions[backend].append(dict(case=name,cut=cut,output=str(target),log=c['log']))
        if parent:
            jobs=[(source_backend,image) for source_backend in ('native','vcs-dpi')
                  for image in sorted((parent.parent/source_backend).glob('*.host'))]
            def restore(job):
                source_backend,image=job;target=base/('actual-'+source_backend+'-'+image.stem)
                c=invoke('readback',target,10,image=image)
                return dict(c,image=str(image),image_sha256=file_sha(image),readback=str(target/'preedge.owner'))
            actual.extend(checked_map(restore,jobs))
    for b in bindings: require(file_sha(b['path'])==b['sha256'],'source changed during host check')
    report=dict(status='passed',scope='FireSim idle/reset component; FESVR caller and CPU acceptance pending',
                commands=commands,source_inputs=bindings,invalid_cases=invalid_cases,corruptions=corruptions,
                actual_restores=actual,fesvr_summary=str(parent) if parent else None,
                fesvr_summary_sha256=file_sha(parent) if parent else None,
                artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
                level1_verified=False,level2_verified=False)
    path=out/'summary.json'; path.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(audit(path),indent=2))


if __name__=='__main__': main()
