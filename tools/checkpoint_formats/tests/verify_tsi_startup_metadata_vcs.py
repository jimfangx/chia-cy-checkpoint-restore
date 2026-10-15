"""Fresh installed-HTIF metadata preparation, not complete TSI/CPU restore."""
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


def canonical(elf):
    def blob(b):
        return words(len(b))+b
    args=[b'+permissive', b'+no_hart0_msip', b'+permissive-off', str(elf).encode()]
    symbols=[(b'',0),(b'fromhost',0x80002008),(b'tohost',0x80002000)]
    return (config(25)+words(len(args))+b''.join(blob(a) for a in args)+blob(polling_elf())+
            words(0x80000000,len(symbols))+b''.join(blob(n)+words(a) for n,a in symbols))


def audit(path):
    path=path.resolve();out=path.parent;r=json.loads(path.read_text())
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'],'wrong metadata scope')
    require(set(r['artifact_sha256'])=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'changed metadata evidence membership')
    for f,d in r['artifact_sha256'].items():require(file_sha(f)==d,'changed metadata artifact '+f)
    bindings={b['path']:b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed metadata source snapshot')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    elf=out/'polling.elf';expected=canonical(elf)
    require(elf.read_bytes()==polling_elf(),'changed actual metadata ELF')
    peers=dict(program=config(23,1,0)+words(0),init=config(21,0,0)+words(0,0,0),
               host=config(18,10)+words(0,0,0),read=config(20,1024,4,2,2)+words(0,0,0,0),
               serial=config(19,4,2,2,1024)+words(0,0),
               **{'loadmem-read':config(14,4096,4)+words(0,0,0,0),'loadmem-queues':config(16,4096,4)+words(0,0,0,0,0,0,0)})
    require(len(r['restores'])==8 and len({c['pid'] for c in r['commands']})==len(r['commands']),'missing fresh metadata processes')
    invalid_count=0
    for producer in ('native','vcs-dpi'):
        require((out/producer/'startup.metadata').read_bytes()==expected,'captured installed metadata differs from independent ELF oracle')
        require('ACTUAL_METADATA_CAPTURE polling_components=8 source_exit=0' in (out/(producer+'-capture.log')).read_text(),'source HTIF did not finish')
    for c in r['restores']:
        dest=Path(c['destination'])
        require((dest/'preedge.metadata').read_bytes()==expected,'incomplete fresh metadata readback')
        require({p.name for p in dest.iterdir()}=={'preedge.metadata',*{'preedge.'+k for k in peers}},'incomplete peer inventory')
        for k,v in peers.items():require((dest/('preedge.'+k)).read_bytes()==v,'metadata preparation mutated '+k)
        log=Path(c['log']).read_text()
        require('COMPLETE_STARTUP_METADATA_READBACK target_edges=0 target_services=0 context_entries=0 unchanged_components=7 guards=3' in log,'preparation entered services/contexts')
        if c['mode']=='invalid':
            count=2*len(expected)+1;invalid_count+=count
            require(f'ATOMIC_METADATA_REJECTIONS count={count} unchanged_components=7 mailboxes=0 context_entries=0' in log,'missing atomic image cases')
    require(len(r['incompatible'])==14,'missing incompatible metadata cases')
    for c in r['incompatible']:
        require('INCOMPATIBLE_METADATA_REJECTION mode='+c['mode']+' unchanged_components=7 mailboxes=0' in Path(c['log']).read_text(),'incompatible preparation admitted')
        require(not list(Path(c['destination']).iterdir()),'incompatible preparation published state')
    for c in r['commands']:
        text=Path(c['log']).read_text()
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and text.rstrip().endswith('exit=0'),'unbound metadata native command')
        require(not any(s in text for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),'metadata sanitizer error')
    return dict(status='passed',fresh_metadata_readbacks=8,complete_unchanged_peer_images=56,
                atomic_invalid_images=invalid_count,incompatible_rejections=14,level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.audit:print(json.dumps(audit(a.audit),indent=2));return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs destination')
    require(os.environ.get('VCS_HOME')=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX')=='/usr/bin/g++-13','source vcs-env LAST')
    a.out.resolve().mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    elf=out/'polling.elf';elf.write_bytes(polling_elf())
    source=TESTS/'tsi_startup_metadata_fesvr.cc';sv=TESTS/'tsi_startup_metadata_fesvr_tb.sv';library=FESVR/'lib/libfesvr.a'
    sources=[source,STUBS/'fesvr/firesim_tsi.cc',STUBS/'fesvr/owned_fesvr_tsi.cc',TESTCHIP/'testchip_tsi.cc',TESTCHIP/'testchip_htif.cc']
    inputs=[*sources,sv,library,Path(__file__),TESTS/'tsi_polling_cut_checks.h',TESTS/'verify_tsi_host_control_fesvr_vcs.py',
            TESTS/'verify_firesim_tsi_loadmem_vcs.py',TESTS/'verify_semantic_vcs.py',TESTS/'verify_loadmem_read_checkpoint_vcs.py',
            *sorted((STUBS/'fesvr').glob('*.h')),*sorted(TESTCHIP.glob('*.h')),*sorted((FESVR/'include/fesvr').glob('*.h')),
            CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots=out/'sources';snapshots.mkdir();bindings=[]
    for f in inputs:
        digest=file_sha(f);snapshot=snapshots/digest
        if not snapshot.exists():shutil.copyfile(f,snapshot)
        bindings.append(dict(path=str(f),sha256=digest,snapshot=str(snapshot)))
    commands=[]
    def execute(argv,name,**extra):
        log=out/(name+'.log');argv=['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])]
        text=run(argv,log,cwd=out)
        import re
        c=dict(cwd=str(out.relative_to(ROOT)),argv=argv,log=str(log),pid=int(re.search(r'fresh_process_pid=(\d+)',text)[1]),**extra)
        commands.append(c);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');return c
    include=f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    native=out/'metadata-native';sanitized=out/'metadata-sanitized';simv=out/'metadata-simv'
    for binary,flags in ((native,[]),(sanitized,['-no-pie','-fsanitize=address,undefined','-fno-omit-frame-pointer'])):
        execute([os.environ['CXX'],*shlex.split(include),'-g',*flags,*sources,library,'-lpthread','-o',binary],binary.name+'-build')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_startup_metadata_fesvr_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_METADATA_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread','-o',simv,sv,*sources], 'vcs-build')
    def invoke(backend,mode,image,dest,name):
        argv=[native if mode=='capture' else sanitized,mode,elf,image,dest] if backend=='native' else [simv,'-no_save',
              '+mode='+mode,'+source='+str(elf),'+image='+str(image),'+destination='+str(dest)]
        return execute(argv,name,mode=mode,destination=str(dest),elf_sha256_at_run=file_sha(elf))
    for backend in ('native','vcs-dpi'):invoke(backend,'capture','unused',out/backend,backend+'-capture')
    restores=[];incompatible=[]
    for producer in ('native','vcs-dpi'):
        for backend in ('native','vcs-dpi'):
            for mode in ('prepare','invalid'):
                name=f'{producer}-{backend}-{mode}'
                restores.append(invoke(backend,mode,out/producer/'startup.metadata',out/name,name))
    for backend in ('native','vcs-dpi'):
        for mode in ('wrong-args','unsupported-long','unsupported-payload','unsupported-symbol-elf','unsupported-signature','unsupported-signature-granularity','changed-elf'):
            if mode=='changed-elf':
                mutant=bytearray(polling_elf());mutant[176]^=1;elf.write_bytes(mutant);(out/'mutant.elf').write_bytes(mutant)
            name=f'{backend}-{mode}'
            incompatible.append(invoke(backend,mode,out/'native/startup.metadata',out/name,name))
            elf.write_bytes(polling_elf())
    for b in bindings:require(file_sha(b['path'])==b['sha256'],'metadata source changed while native checks ran')
    report=dict(status='passed',scope='installed HTIF startup metadata component only; complete CPU restore pending',
                commands=commands,restores=restores,incompatible=incompatible,source_inputs=bindings,
                level1_verified=False,level2_verified=False,artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(audit(path),indent=2))


if __name__=='__main__':main()
