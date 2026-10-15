"""Capture actual installed-FESVR BCD/fromhost responses and read back fresh callers."""
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
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf

CUTS=('tohost-read','fromhost-pending','fromhost-half','next-poll','complete')
RESPONSE=0x0100000000000141


def expected():
    phases=(1,6,6,1,8)
    result={}
    for name,phase in zip(CUTS,phases):
        pending=phase==6
        poll=config(24,0x80002000,0x80002008,1048576)+words(phase,0,int(pending),*([RESPONSE] if pending else []))
        reader=config(20,1024,4,2,2)+(words(0,0,0,0) if phase==8 else
               words(2,0x80002008 if pending else 0x80002000,8,int(name=='fromhost-half'),*([0] if name=='fromhost-half' else [])))
        result[name]=dict(poll=poll,read=reader,serial=config(19,4,2,2,1024)+words(0,0),host=config(18,10)+words(0,0,6))
    return result


def audit(path):
    path=path.resolve();r=json.loads(path.read_text());out=path.parent
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'],'wrong response scope')
    require(set(r['artifact_sha256'])=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'changed response artifact membership')
    for p,digest in r['artifact_sha256'].items():require(file_sha(p)==digest,'changed response artifact '+p)
    bindings={b['path']:b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed response source snapshot')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    require((out/'polling.elf').read_bytes()==polling_elf(),'changed actual ELF')
    oracle=expected()
    for backend in ('native','vcs-dpi'):
        require((out/backend/'input.bin').read_bytes()==b'A','changed deterministic BCD input')
        for cut,owners in oracle.items():
            for kind,value in owners.items():require((out/backend/(cut+'.'+kind)).read_bytes()==value,'actual response peer/caller differs '+cut+'/'+kind)
        require('REAL_FESVR_HTIF_RESPONSE bcd_input_bytes=1 callback='+str(RESPONSE)+' fromhost_writes=1 terminal_exit=0 cuts=5' in
                (out/(backend+'.log')).read_text(),'actual callback/write/exit did not run')
    require(len(r['restores'])==20,'missing actual response readbacks')
    for c in r['restores']:
        require(Path(c['readback']).read_bytes()==Path(c['image']).read_bytes()==oracle[c['cut']]['poll'],'incomplete actual response readback')
        require('COMPLETE_ACTUAL_RESPONSE_READBACK target_edges=0 context_entries=0 services=0' in Path(c['log']).read_text(),'response restore entered context or serviced target')
    for c in r['commands']:
        log=Path(c['log']).read_text()
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and log.rstrip().endswith('exit=0'),'unbound native response command/environment/result')
        require(not any(s in log for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),'response sanitizer failure')
    return dict(status='passed',actual_bcd_callbacks=2,actual_fromhost_writes=2,actual_exit_commands=2,
                complete_actual_peer_images=40,fresh_actual_response_readbacks=20,level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.audit:print(json.dumps(audit(a.audit),indent=2));return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs output')
    require(os.environ.get('VCS_HOME')=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX')=='/usr/bin/g++-13','source vcs-env LAST')
    a.out.resolve().mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    elf=out/'polling.elf';elf.write_bytes(polling_elf());source=TESTS/'tsi_htif_response_fesvr.cc';sv=TESTS/'tsi_htif_response_fesvr_tb.sv';library=FESVR/'lib/libfesvr.a'
    sources=[source,STUBS/'fesvr/firesim_tsi.cc',STUBS/'fesvr/owned_fesvr_tsi.cc',TESTCHIP/'testchip_tsi.cc',TESTCHIP/'testchip_htif.cc']
    inputs=[*sources,sv,library,Path(__file__),TESTS/'verify_tsi_host_control_fesvr_vcs.py',TESTS/'verify_firesim_tsi_loadmem_vcs.py',
            TESTS/'verify_semantic_vcs.py',TESTS/'verify_loadmem_read_checkpoint_vcs.py',*sorted((STUBS/'fesvr').glob('*.h')),
            *sorted(TESTCHIP.glob('*.h')),*sorted((FESVR/'include/fesvr').glob('*.h')),CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',
            ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
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
    include=f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    native=out/'response-native';sanitized=out/'response-sanitized';simv=out/'response-simv'
    for binary,flags in ((native,[]),(sanitized,['-no-pie','-fsanitize=address,undefined','-fno-omit-frame-pointer'])):
        execute([os.environ['CXX'],*shlex.split(include),'-g',*flags,*sources,library,'-lpthread','-o',binary],out/(binary.name+'-build.log'))
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_htif_response_fesvr_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_HTIF_RESPONSE_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread','-o',simv,sv,*sources],out/'vcs-build.log')
    def invoke(backend,mode,source,dest):
        argv=[native if mode=='capture' else sanitized,mode,source,dest] if backend=='native' else [simv,'-no_save','+mode='+mode,'+source='+str(source),'+destination='+str(dest)]
        return execute(argv,dest.with_suffix('.log'))
    restores=[]
    for producer in ('native','vcs-dpi'):
        base=out/producer;invoke(producer,'capture',elf,base)
        for cut in CUTS:
            image=base/(cut+'.poll')
            for backend in ('native','vcs-dpi'):
                dest=out/(producer+'-'+cut+'-'+backend)
                restores.append(dict(invoke(backend,'readback',image,dest),image=str(image),readback=str(dest/'preedge.poll'),cut=cut))
    for b in bindings:require(file_sha(b['path'])==b['sha256'],'response source changed during execution')
    report=dict(status='passed',scope='actual default-device callback/fromhost caller only; CPU/device/context restore pending',commands=commands,
                source_inputs=bindings,restores=restores,level1_verified=False,level2_verified=False,
                artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(audit(path),indent=2))


if __name__=='__main__':main()
