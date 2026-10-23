"""Audit suspended production TSI components and real Rocket workload samples.

This grants neither complete HTIF ownership nor CPU checkpoint acceptance.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
import os
from pathlib import Path
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
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf

OWNERS={'poll','program','init','host','read','serial','loadmem-read','loadmem-queues'}
REJECTED=('unstarted','loader-entry','loader-memif','reset-wait','active-syscall-pending','active-syscall-partial','complete')


def audit_components(images, *, msip, mailboxes=(0x80002000,0x80002008)):
    require(set(images)==OWNERS,'incomplete polling component inventory')
    require(images['program']==config(23,1,0)+words(3),'startup loader still active/configuration changed')
    require(images['init']==config(21,int(msip),0)+words(8,0,0),'initialization not complete')
    require(images['loadmem-read']==config(14,4096,4)+words(0,0,0,0),'loadmem caller still active')
    require(images['loadmem-queues']==config(16,4096,4)+words(0,0,0,0,0,0,0),'loadmem queue not empty')
    def payload(kind, header):
        b=images[kind];require(b.startswith(header) and (len(b)-len(header))%8==0,'incompatible '+kind)
        return struct.unpack('<'+'Q'*((len(b)-len(header))//8),b[len(header):])
    poll=payload('poll',config(24,*mailboxes,1048576))
    host=payload('host',config(18,10))
    reader=payload('read',config(20,1024,4,2,2))
    serial=payload('serial',config(19,4,2,2,1024))
    require(len(poll)>=3 and poll[1]==0 and len(poll)==3+poll[2],'bad poll response queue/caller')
    require(len(host)==3 and host[2]&6==6 and host[2]<=7,'target/startup not loaded')
    require(len(reader)>=4 and len(reader)==4+reader[3],'incomplete serial reader')
    require(len(serial)>=2 and serial[0]<=len(serial)-2,'incomplete serial requests')
    n=serial[0];require(serial[n+1]==len(serial)-n-2 and all(x<=0xffffffff for x in (*serial[1:n+1],*serial[n+2:])),'incomplete/wide serial responses')
    phase=poll[0]
    if phase==4:
        require(host[0]==1 and host[1]<10 and host[2]==6 and reader==(0,0,0,0),'incoherent idle child')
    else:
        require(phase in (1,6) and (phase==1 or poll[2]>0),'unsupported polling read')
        require(host[0]==0 and host[1]==0 and reader[0:3]==(2,mailboxes[int(phase==6)],8) and reader[3] in (0,1),
                'poll caller/partial serial child mismatch')
        require(all(x<=0xffffffff for x in reader[4:]),'wide partial serial read')
    return dict(poll_phase=phase,partial_words=reader[3],serial_requests=n,serial_responses=serial[n+1])


def audit(path):
    path=path.resolve();r=json.loads(path.read_text());out=path.parent
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'],'wrong audit scope')
    require(set(r['artifact_sha256'])=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'changed audit membership')
    for f,digest in r['artifact_sha256'].items():require(file_sha(f)==digest,'changed audit artifact '+f)
    bindings={b['path']:b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed audit source snapshot')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    require((out/'polling.elf').read_bytes()==polling_elf(),'changed actual ELF')
    exit_rejection = r.get('unowned_exit_cut_rejection', False)
    for backend in ('native','vcs-dpi'):
        base=out/backend;text=(out/(backend+'.log')).read_text()
        require('ACTUAL_ACTIVE_SYSCALL_REJECTIONS count=2 returned_components=8 terminal_exit=0 cpu_edges=0' in text,'actual nested service did not complete')
        if exit_rejection:
            require('ACTUAL_UNOWNED_SYS_EXIT_REJECTION count=1 retained_unadmitted_components=8 cpu_edges=0' in text,
                    'missing production unowned exit rejection')
        for cut in (*REJECTED, *(['syscall-returned'] if exit_rejection else [])):
            require('POLLING_CUT_ADMISSION cut='+cut+' supported=0 complete_components=0 inspection_services=0' in text,
                    'unsupported cut admitted '+cut)
            require(not list(base.glob(cut+'.audit-*')),'partially published rejected component cut')
        for cut,phase in (('first-poll',1),('syscall-returned',6)):
            prefix = '.component-' if exit_rejection and cut=='syscall-returned' else '.audit-'
            images={kind:(base/(cut+prefix+kind)).read_bytes() for kind in OWNERS}
            actual=audit_components(images,msip=False)
            require(actual==dict(poll_phase=phase,partial_words=0,serial_requests=0,serial_responses=0),'wrong actual returned caller')
            require(images['host']==config(18,10)+words(0,0,6),'wrong actual host state')
            require(images['poll']==config(24,0x80002000,0x80002008,1048576)+words(phase,0,int(phase==6),*([1] if phase==6 else [])),
                    'actual syscall response did not return')
    for c in r['commands']:
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                Path(c['log']).read_text().rstrip().endswith('exit=0'),'unbound native command/result/environment')
    return dict(status='passed',actual_active_syscall_rejections=4,actual_startup_termination_rejections=10,
                actual_unowned_exit_rejections=2 if exit_rejection else 0,
                retained_unadmitted_component_images=16 if exit_rejection else 0,
                complete_returned_component_images=32,level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.audit:print(json.dumps(audit(a.audit),indent=2));return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs output')
    require(os.environ.get('VCS_HOME')==_toolchain.VCS_HOME and os.environ.get('CXX')==_toolchain.CXX,'source vcs-env LAST')
    a.out.resolve().mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    elf=out/'polling.elf';elf.write_bytes(polling_elf());source=TESTS/'tsi_polling_active_service_fesvr.cc';sv=TESTS/'tsi_polling_active_service_fesvr_tb.sv';library=FESVR/'lib/libfesvr.a'
    sources=[source,STUBS/'fesvr/firesim_tsi.cc',STUBS/'fesvr/owned_fesvr_tsi.cc',TESTCHIP/'testchip_tsi.cc',TESTCHIP/'testchip_htif.cc']
    inputs=[*sources,sv,library,Path(__file__),TESTS/'tsi_polling_cut_checks.h',TESTS/'verify_tsi_host_control_fesvr_vcs.py',TESTS/'verify_firesim_tsi_loadmem_vcs.py',
            TESTS/'verify_semantic_vcs.py',TESTS/'verify_loadmem_read_checkpoint_vcs.py',*sorted((STUBS/'fesvr').glob('*.h')),
            *sorted(TESTCHIP.glob('*.h')),*sorted((FESVR/'include/fesvr').glob('*.h')),CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',
            ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    inputs = [*inputs, *overlay_inputs()]
    snapshots=out/'sources';snapshots.mkdir();bindings=[]
    for f in inputs:
        digest=file_sha(f);snapshot=snapshots/digest
        if not snapshot.exists():shutil.copyfile(f,snapshot)
        bindings.append(dict(path=str(f),sha256=digest,snapshot=str(snapshot)))
    commands=[]
    def execute(argv,log):
        argv=['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])];run(argv,log,cwd=out)
        c=dict(cwd=str(out.relative_to(ROOT)),argv=argv,log=str(log));commands.append(c)
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');return c
    library = build_overlay(out, execute)
    include=f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    native=out/'active-native';simv=out/'active-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-g',*sources,library,'-lpthread','-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_polling_active_service_fesvr_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_ACTIVE_SERVICE_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread','-o',simv,sv,*sources],out/'vcs-build.log')
    execute([native,elf,out/'native'],out/'native.log')
    execute([simv,'-no_save','+source='+str(elf),'+destination='+str(out/'vcs-dpi')],out/'vcs-dpi.log')
    for b in bindings:require(file_sha(b['path'])==b['sha256'],'audit source changed during execution')
    report=dict(status='passed',scope='actual suspended syscall and unowned exit rejection; retained independent component readback',commands=commands,
                unowned_exit_cut_rejection=True,
                source_inputs=bindings,level1_verified=False,level2_verified=False,
                artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(audit(path),indent=2))


if __name__=='__main__':main()
