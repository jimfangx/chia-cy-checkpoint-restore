"""Fresh HTIF caller component continuations in native ASan/UBSan and VCS.

This exercises the run-loop owner, not a complete CPU checkpoint or device owner.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS


def scenario():
    # Independent expected caller images after each observable FESVR action.
    phase, command, queue = 0, 0, []
    events, images = [], [config(24,4096,8192,4)+words(0,0,0)]
    def step(event, after, value=None, responses=(), pop=False):
        nonlocal phase, command
        if value is not None: command = value
        queue.extend(responses)
        if pop: queue.pop(0)
        phase = after; events.append(event)
        images.append(config(24,4096,8192,4)+words(phase,command,len(queue),*queue))
    step('X 0',1)
    step('R 4096 0 0',1)
    step('R 4096 1 0',4)
    step('I 0',4)
    step('I 1',5)
    step('T 1 17',6,responses=(17,))
    step('R 8192 0 0',6)
    step('R 8192 1 9',0)  # fromhost occupied: retain the oldest response
    command_value = 0x1020304050607080
    step('X 0',1)
    step('R 4096 1 '+str(command_value),2,value=command_value)
    step('W 4096 0',3)
    # A blocked dispatch must unwind the parent guard, retain its command and
    # queue, and retry only the child on the next call. A child may publish a
    # response before its final explicit return; the queue must survive too.
    step('D '+str(command_value)+' 0 0',3)
    step('D '+str(command_value)+' 1 34 0',3,responses=(34,))
    step('D '+str(command_value)+' 0 0',3)
    step('D '+str(command_value)+' 0 1',5)
    step('T 1 18446744073709551615',6,value=0,responses=(2**64-1,))
    step('R 8192 1 0',7)
    step('W 8192 17',0,pop=True)
    for response in (34,2**64-1):
        step('X 0',1)
        step('R 4096 1 0',4)
        step('I 1',5)
        step('T 0',6)
        step('R 8192 1 0',7)
        step('W 8192 '+str(response),0,pop=True)
    # Exit is checked at the top of the next loop, after devices/fromhost.
    step('X 0',1)
    step('R 4096 1 1',2,value=1)
    step('W 4096 0',3)
    step('D 1 0 1',5)
    step('T 0',6,value=0)
    step('N',0)
    step('X 1',8)
    step('N',8)
    return events, images


def audit(path):
    path = path.resolve(); r = json.loads(path.read_text()); out = path.parent
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'],'wrong poll scope')
    require(set(r['artifact_sha256'])=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'changed poll evidence membership')
    for name,digest in r['artifact_sha256'].items(): require(file_sha(name)==digest,'changed poll artifact '+name)
    bindings={b['path']:b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed poll source snapshot')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    events,images=scenario()
    require(len(r['restores'])==2*len(images),'missing fresh poll cuts')
    for c in r['restores']:
        cut=c['cut']; dest=Path(c['destination'])
        require((dest/'preedge.owner').read_bytes()==images[cut],'incomplete zero-edge poll readback')
        for i,expected in enumerate(images[cut+1:]):
            require((dest/f'after-{i}.owner').read_bytes()==expected,'changed continued poll caller')
        require('COMPLETE_POLL_READBACK target_edges=0 context_entries=0 services=0' in Path(c['log']).read_text(),'readback advanced a service')
    require(len(r['corruptions'])==4 and len(r['invalids'])==8,'missing corruption/invalid cases')
    for c in r['corruptions']:
        require('FIRST_DIVERGENCE fixture_operation=0 signal='+c['signal'] in Path(c['log']).read_text() and
                'acknowledged=0' in Path(c['log']).read_text(),'wrong first divergent component operation')
    for c in r['invalids']:
        require(not (Path(c['destination'])/'preedge.owner').exists(),'invalid image partially restored')
    for c in r['commands']:
        log=Path(c['log']).read_text()
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(c['expected_exit'])),'unbound poll native environment/result')
        require(not any(s in log for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),'poll sanitizer failure')
    return dict(status='passed',fresh_poll_cuts=len(r['restores']),caller_phases=9,
                complete_continued_readbacks=sum(len(images)-c['cut'] for c in r['restores']),
                atomic_invalid_checks=sum(int(Path(c['log']).read_text().split('atomic_invalids=')[1].split()[0]) for c in r['restores']),
                fresh_invalids=8,first_divergences=4,level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--out',type=Path); p.add_argument('--audit',type=Path); a=p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit),indent=2)); return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs output')
    require(os.environ.get('VCS_HOME')==_toolchain.VCS_HOME and os.environ.get('CXX')==_toolchain.CXX,'source vcs-env LAST')
    a.out.resolve().mkdir(parents=True,exist_ok=True); out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    source=TESTS/'tsi_htif_poll_checkpoint.cc'; sv=TESTS/'tsi_htif_poll_checkpoint_tb.sv'
    inputs=[source,sv,Path(__file__),STUBS/'fesvr/tsi_htif_poll.h',CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',
            TESTS/'verify_semantic_vcs.py',TESTS/'verify_loadmem_read_checkpoint_vcs.py',
            ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots=out/'sources'; snapshots.mkdir(); bindings=[]
    for f in inputs:
        digest=file_sha(f); snapshot=snapshots/digest
        if not snapshot.exists(): shutil.copyfile(f,snapshot)
        bindings.append(dict(path=str(f),sha256=digest,snapshot=str(snapshot)))
    commands=[]
    def execute(argv,log,expected=0):
        argv=['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])]
        run(argv,log,cwd=out,expected=expected)
        c=dict(cwd=str(out.relative_to(ROOT)),argv=argv,log=str(log),expected_exit=expected)
        commands.append(c); (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n'); return c
    native=out/'poll-native'; simv=out/'poll-simv'; include=f'-std=c++17 -I{CC} -I{STUBS}'
    execute([os.environ['CXX'],*shlex.split(include),'-g','-no-pie','-fsanitize=address,undefined','-fno-omit-frame-pointer',source,'-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_htif_poll_checkpoint_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_HTIF_POLL_DPI','-o',simv,sv,source],out/'vcs-build.log')
    events,images=scenario(); restores=[]; corruptions=[]; invalids=[]
    def invoke(backend,image,plan,dest,expected=0):
        argv=[native,image,plan,dest] if backend=='native' else [simv,'-no_save','+source='+str(image),'+plan='+str(plan),'+destination='+str(dest)]
        return dict(execute(argv,dest.with_suffix('.log'),expected),destination=str(dest))
    for cut,image in enumerate(images):
        src=out/f'cut-{cut}.owner'; src.write_bytes(image)
        plan=out/f'cut-{cut}.plan'; plan.write_text('\n'.join(events[cut:])+ ('\n' if events[cut:] else ''))
        for backend in ('native','vcs-dpi'):
            c=invoke(backend,src,plan,out/f'{backend}-cut-{cut}'); restores.append(dict(c,cut=cut))
    dispatch_cut = next(i for i, e in enumerate(events) if e.startswith('D '))
    response_cut = next(i for i, e in enumerate(events) if e == 'W 8192 17')
    for cut,signal,offset in ((dispatch_cut+1,'tohost_command',64),(response_cut,'write_data',80)):
        image=bytearray(images[cut]); image[offset]^=1
        src=out/f'corrupt-{cut}.owner'; src.write_bytes(image)
        plan=out/f'cut-{cut}.plan'
        for backend in ('native','vcs-dpi'):
            corruptions.append(dict(invoke(backend,src,plan,out/f'corrupt-{backend}-{cut}',3),signal=signal))
    for i,image in enumerate((images[0][:-1],bytes(80),config(23,4096,8192,4)+words(0,0,0),config(24,4096,8192,4)+words(7,0,0))):
        src=out/f'invalid-{i}.owner'; src.write_bytes(image)
        for backend in ('native','vcs-dpi'):
            invalids.append(invoke(backend,src,out/'cut-0.plan',out/f'invalid-{backend}-{i}',2))
    for b in bindings: require(file_sha(b['path'])==b['sha256'],'poll source changed during execution')
    report=dict(status='passed',scope='HTIF caller component only; complete CPU and device ownership pending',
                source_inputs=bindings,commands=commands,restores=restores,corruptions=corruptions,invalids=invalids,
                level1_verified=False,level2_verified=False,artifact_sha256={str(f):file_sha(f) for f in sorted(out.rglob('*')) if f.is_file()})
    path=out/'summary.json'; path.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(audit(path),indent=2))


if __name__=='__main__': main()
