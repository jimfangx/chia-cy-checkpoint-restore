"""Installed-FESVR child-reset/HTIF-poll control and fresh component readbacks.

These real host calls execute no CPU workload and cannot establish CPU support.
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
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import elf_bytes, FESVR, TESTCHIP
from tools.checkpoint_formats.tests.verify_tsi_host_control_vcs import CC, STUBS, TESTS, audit as audit_owner


def polling_elf():
    # Extend the actual two-segment loader ELF with a real linked symbol table.
    # FESVR resolves these two symbols and executes its original polling loop.
    source=bytearray(elf_bytes()[:196]); strings=b'\0tohost\0fromhost\0'
    source+=strings; source+=bytes(224-len(source))
    source+=bytes(24)+struct.pack('<IBBHQQ',1,0x11,0,1,0x80002000,8)
    source+=struct.pack('<IBBHQQ',8,0x11,0,1,0x80002008,8)
    assert len(source)==296
    # This FESVR loader resolves symbol sections by their actual names, not
    # only their ELF section types/link fields.
    names=b'\0.symtab\0.strtab\0.shstrtab\0'
    source+=names; source+=bytes(328-len(source)); source+=bytes(64)
    source+=struct.pack('<IIQQQQIIQQ',1,2,0,0,224,72,2,1,8,24)
    source+=struct.pack('<IIQQQQIIQQ',9,3,0,0,196,len(strings),0,0,1,0)
    source+=struct.pack('<IIQQQQIIQQ',17,3,0,0,296,len(names),0,0,1,0)
    struct.pack_into('<Q',source,40,328)
    struct.pack_into('<HH',source,60,4,3)
    return bytes(source)


def expected_images(count):
    def image(phase,remaining,flags): return config(18,count)+words(phase,remaining,flags)
    result={'constructed':image(0,0,0),'reset-wait':image(2,0,2),
            'reset-child':image(3,0,6),'first-poll':image(0,0,6)}
    result.update({f'child-wait-{i}':image(3,0,6) for i in range(3)})
    for loop in range(3):
        result[f'poll-half-{loop}']=image(0,0,6 if loop==0 else 7)
        result.update({f'idle-{loop}-{i}':image(1,count-1-i,6) for i in range(count)})
        result[f'busy-poll-{loop}']=image(0,0,7)
    return result


def audit(path):
    path=path.resolve(); r=json.loads(path.read_text()); out=path.parent
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'],'wrong actual component scope')
    catalog=r['artifact_sha256']
    require(set(catalog)=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'changed actual evidence membership')
    for p,digest in catalog.items(): require(file_sha(p)==digest,'changed actual artifact '+p)
    bindings={b['path']:b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed actual source snapshot')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    require((out/'polling.elf').read_bytes()==polling_elf(),'changed actual poll ELF')
    parent=Path(r['component_summary'])
    require(file_sha(parent)==r['component_summary_sha256'] and audit_owner(parent)['actual_fesvr_fresh_restores']==136,
            'missing complete parent component evidence')
    images=0
    for backend in ('native','vcs-dpi'):
        for count in (1,3,10):
            case=out/backend/str(count); expected=expected_images(count)
            require({p.stem for p in case.glob('*.host')}==set(expected),'changed actual image inventory')
            for name,payload in expected.items():
                require((case/(name+'.host')).read_bytes()==payload,'suspended actual phase/cursor/flags differ '+name)
                images+=1
            if str(STUBS/'fesvr/tsi_htif_poll.h') in bindings:
                polls={name:config(24,0x80002000,0x80002008,1048576)+words(4 if name.startswith('idle-') else 1,0,0)
                       for name in expected if name=='first-poll' or name.startswith(('poll-half-','idle-','busy-poll-'))}
                require({p.stem for p in case.glob('*.poll')}==set(polls),'missing real polling caller cuts')
                for name,payload in polls.items():
                    require((case/(name+'.poll')).read_bytes()==payload,'real polling caller phase differs '+name)
            require(f'REAL_HTIF_HOST_CONTROL idle_count={count} child_waits=3 poll_loops=3 serial_words=25' in
                    (case.parent/(str(count)+'.log')).read_text(),'actual child reset/HTIF poll did not finish')
    require(len(r['restores'])==2*images and len({a['pid'] for a in r['restores']})==2*images,'incomplete fresh restores')
    for a in r['restores']:
        require(file_sha(a['image'])==a['image_sha256'] and
                Path(a['readback']).read_bytes()==Path(a['image']).read_bytes(),'actual zero-edge restore differs')
        require('COMPLETE_READBACK zero_edges=1 restore_services=0' in Path(a['log']).read_text(),'missing no-service readback')
        if 'poll_image' in a:
            require(Path(a['poll_readback']).read_bytes()==Path(a['poll_image']).read_bytes(), 'incomplete fresh actual poll caller readback')
            require('COMPLETE_ACTUAL_POLL_READBACK target_edges=0 context_entries=0 services=0' in Path(a['log']).read_text(),
                    'actual polling restore entered context/services')
    if str(STUBS/'fesvr/tsi_htif_poll.h') in bindings:
        require(sum('poll_image' in a for a in r['restores'])==252,'missing fresh actual polling restores')
    for c in r['commands']:
        log=Path(c['log']).read_text()
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit=0'),'unbound native command/environment/exit')
        require(not any(e in log for e in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),
                'actual restore sanitizer error')
    return dict(status='passed',summary=str(path),actual_suspended_child_poll_idle_images=images,
                actual_fresh_component_restores=len(r['restores']),actual_fresh_poll_readbacks=sum('poll_image' in a for a in r['restores']),
                level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--out',type=Path)
    p.add_argument('--component-summary',type=Path); p.add_argument('--audit',type=Path); a=p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit),indent=2)); return
    require(a.out is not None and a.component_summary is not None and
            a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs output and parent summary')
    require(os.environ.get('VCS_HOME')=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX')=='/usr/bin/g++-13','source vcs-env.sh LAST')
    parent=a.component_summary.resolve(); require(audit_owner(parent)['actual_fesvr_fresh_restores']==136,'need actual readbacks')
    a.out.resolve().mkdir(parents=True,exist_ok=True); out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    elf=out/'polling.elf'; elf.write_bytes(polling_elf())
    source=TESTS/'tsi_host_control_fesvr.cc'; sv=TESTS/'tsi_host_control_fesvr_tb.sv'; library=FESVR/'lib/libfesvr.a'
    sources=[source,STUBS/'fesvr/firesim_tsi.cc',STUBS/'fesvr/owned_fesvr_tsi.cc',TESTCHIP/'testchip_tsi.cc',TESTCHIP/'testchip_htif.cc']
    inputs=[*sources,sv,library,Path(__file__),TESTS/'native_parallel.py',TESTS/'verify_tsi_host_control_vcs.py',TESTS/'verify_firesim_tsi_loadmem_vcs.py',
            TESTS/'verify_semantic_vcs.py',TESTS/'verify_loadmem_read_checkpoint_vcs.py',
            *sorted((STUBS/'fesvr').glob('*.h')),*sorted(TESTCHIP.glob('*.h')),*sorted((FESVR/'include/fesvr').glob('*.h')),
            CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',ROOT/'env.sh',ROOT/'sims/firesim/env.sh',
            ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots=out/'source-snapshots'; snapshots.mkdir(); bindings=[]
    for f in inputs:
        digest=file_sha(f); snapshot=snapshots/digest
        if not snapshot.exists(): shutil.copyfile(f,snapshot)
        bindings.append(dict(path=str(f),sha256=digest,snapshot=str(snapshot)))
    commands=[];command_lock=threading.Lock()
    def execute(argv,log):
        argv=['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])]
        result=run(argv,log,cwd=out)
        c=dict(cwd=str(out.relative_to(ROOT)),argv=argv,log=str(log),pid=int(re.search(r'fresh_process_pid=(\d+)',result)[1]))
        with command_lock:
            commands.append(c); (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        return c
    include=f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    native=out/'actual-native'; simv=out/'actual-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-g',*sources,library,'-lpthread','-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps',
             '-top','tsi_host_control_fesvr_tb','-cc',os.environ['CC'],'-cpp',os.environ['CXX'],
             f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_HOST_FESVR_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread',
             '-o',simv,sv,*sources],out/'vcs-build.log')
    restores=[]
    for backend in ('native','vcs-dpi'):
        base=out/backend; base.mkdir()
        for count in (1,3,10):
            case=base/str(count)
            argv=[native,elf,case,count] if backend=='native' else [simv,'-no_save',
                  '+elf='+str(elf),'+out='+str(case),'+count='+str(count)]
            execute(argv,base/(str(count)+'.log'))
            jobs=[(image,restored_backend,binary) for image in sorted(case.glob('*.host'))
                  for restored_backend,binary in [('native-sanitized',parent.parent/'host-native'),('vcs-dpi',parent.parent/'host-simv')]]
            def restore(job):
                image,restored_backend,binary=job
                dest=out/('restore-'+backend+'-'+str(count)+'-'+image.stem+'-'+restored_backend)
                values=list(map(str,['readback',dest,'unused','unused',image,0,count]))
                argv=[binary,*values] if restored_backend=='native-sanitized' else [binary,'-no_save',
                      *['+'+k+'='+v for k,v in zip(('mode','out','commands','expected','image','cut','variant'),values)]]
                c=execute(argv,out/(dest.name+'.log'))
                entry=dict(c,image=str(image),image_sha256=file_sha(image),readback=str(dest/'preedge.owner'))
                if image.with_suffix('.poll').exists():
                    entry.update(poll_image=str(image.with_suffix('.poll')),poll_readback=str(dest/'preedge.poll'))
                return entry
            restores.extend(checked_map(restore,jobs))
    for b in bindings: require(file_sha(b['path'])==b['sha256'],'source changed during actual child/poll check')
    report=dict(status='passed',scope='actual FESVR child reset/poll/idle control only; CPU acceptance pending',
                component_summary=str(parent),component_summary_sha256=file_sha(parent),commands=commands,
                source_inputs=bindings,restores=restores,elf_sha256=file_sha(elf),fesvr_library_sha256=file_sha(library),
                artifact_sha256={str(f):file_sha(f) for f in sorted(out.rglob('*')) if f.is_file()},
                level1_verified=False,level2_verified=False)
    path=out/'summary.json'; path.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(audit(path),indent=2))


if __name__=='__main__': main()
