"""Fresh installed-HTIF metadata preparation, not complete TSI/CPU restore."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import tempfile

from tools.checkpoint_formats.tests.fesvr_overlay import overlay_inputs, build_overlay
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf


def pristine_peers():
    return dict(program=config(23,1,0)+words(0),init=config(21,0,0)+words(0,0,0),
                host=config(18,10)+words(0,0,0),read=config(20,1024,4,2,2)+words(0,0,0,0),
                serial=config(19,4,2,2,1024)+words(0,0),
                **{'loadmem-read':config(14,4096,4)+words(0,0,0,0),'loadmem-queues':config(16,4096,4)+words(0,0,0,0,0,0,0)})


def canonical(elf, legacy=False, revision=3, required_xlen=0, sealed_input=None, terminal=None,
              omit_terminal=False, reorder_peers=False):
    def blob(b):
        return words(len(b))+b
    args=[b'+permissive', b'+no_hart0_msip', b'+permissive-off', str(elf).encode()]
    if sealed_input is not None:
        args.insert(2, ('+checkpoint-terminal-input='+str(sealed_input)).encode())
    symbols=[(b'',0),(b'fromhost',0x80002008),(b'tohost',0x80002000)]
    peers=pristine_peers()
    if terminal is not None and not omit_terminal:
        peers['terminal']=terminal
    if reorder_peers:
        peers=dict(reversed(list(peers.items())))
    configuration=(config(25,revision,1,0,8,1024,*([required_xlen] if revision>=3 else []))+words(len(peers))+
                   b''.join(blob(n.encode())+blob(b) for n,b in peers.items()))
    header=config(25) if legacy else config(25,revision)+blob(configuration)
    return (header+words(len(args))+b''.join(blob(a) for a in args)+blob(polling_elf())+
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
    revision=r.get('metadata_revision',2)
    elf=out/'polling.elf';expected=canonical(elf,revision=revision)
    require(elf.read_bytes()==polling_elf(),'changed actual metadata ELF')
    peers=pristine_peers()
    require(len(r['restores'])==12 and len({c['pid'] for c in r['commands']})==len(r['commands']),'missing fresh metadata processes')
    invalid_count=0
    resources_checked='loader_resources' in r
    resource_marker='ELF_RESOURCE_ATOMIC_REJECTIONS count=32 leaked_descriptors=0 leaked_mappings=0'
    for producer in ('native','vcs-dpi'):
        require((out/producer/'startup.metadata').read_bytes()==expected,'captured installed metadata differs from independent ELF oracle')
        require('ACTUAL_METADATA_CAPTURE polling_components=8 source_exit=0' in (out/(producer+'-capture.log')).read_text(),'source HTIF did not finish')
        require('INSTALLED_XLEN_CAPTURE_REJECTION expected=32 actual=64 recovered=64 unchanged_components=8' in (out/(producer+'-capture.log')).read_text(),'capture missed actual installed XLEN')
        if resources_checked:require(resource_marker in (out/(producer+'-capture.log')).read_text(),'capture leaked loader resources')
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
        if c['mode']=='xlen-recovery':
            require('ATOMIC_INSTALLED_XLEN_REJECTION expected=32 actual=64 recovered=64 unchanged_components=7 mailboxes=0' in log,'missing installed XLEN rejection/recovery')
            if resources_checked:require(resource_marker in log,'prepare leaked loader resources')
    require(len(r['incompatible'])==(20 if revision>=3 else 18),'missing incompatible metadata cases')
    require((out/'legacy.metadata').read_bytes()==canonical(elf,legacy=True,revision=revision),'legacy-image oracle changed')
    for c in r['incompatible']:
        require('INCOMPATIBLE_METADATA_REJECTION mode='+c['mode']+' unchanged_components=7 mailboxes=0' in Path(c['log']).read_text(),'incompatible preparation admitted')
        require(not list(Path(c['destination']).iterdir()),'incompatible preparation published state')
    if revision>=3:
        expected64=canonical(elf,required_xlen=64)
        require(expected!=expected64,'policy oracle collapsed')
        require((out/'revision2.metadata').read_bytes()==canonical(elf,revision=2),'revision-2 oracle changed')
        for producer in ('native','vcs-dpi'):
            require((out/producer/'startup64.metadata').read_bytes()==expected64,'actual base-setter policy not captured')
        require(len(r['policy_cases'])==12,'missing exact-policy fresh processes')
        for c in r['policy_cases']:
            dest=Path(c['destination']);log=Path(c['log']).read_text()
            source=0 if c['mode']=='policy0to64' else 64
            require((dest/'preedge.metadata').read_bytes()==(expected if source==0 else expected64),'policy readback differs')
            require({p.name for p in dest.iterdir()}=={'preedge.metadata',*{'preedge.'+k for k in peers}},'incomplete policy peer inventory')
            for k,v in peers.items():require((dest/('preedge.'+k)).read_bytes()==v,'policy preparation mutated '+k)
            require('COMPLETE_STARTUP_METADATA_READBACK target_edges=0 target_services=0 context_entries=0 unchanged_components=7 guards=3' in log,'policy preparation entered services')
            if c['mode']!='prepare64':
                require(f'ATOMIC_EXACT_XLEN_POLICY_REJECTION source={source} destination={64 if source==0 else 0} unchanged_components=7 mailboxes=0 context_entries=0' in log,'missing atomic exact-policy rejection')
    for c in r['commands']:
        text=Path(c['log']).read_text()
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                text.rstrip().endswith('exit='+str(c.get('expected_exit',0))),'unbound metadata native command')
        require(not any(s in text for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),'metadata sanitizer error')
    # Historical metadata evidence retains its original source snapshots and
    # makes no claim about resource cleanup. Keep those audits executable.
    if resources_checked:
        require(len(r['loader_resources'])==2 and len(r['installed_negative_controls'])==2,'missing resource checks/negative controls')
        for c in r['loader_resources']:
            require('ELF_LOADER_RESOURCES cases=352 modes=11 repetitions=32 leaked_descriptors=0 leaked_mappings=0 exact_metadata=1 exact_writes=1' in
                    Path(c['log']).read_text(),'loader resource/error/target-write coverage incomplete')
        for c in r['installed_negative_controls']:
            require(c['expected_exit']==2 and 'FAIL ELF loader leaked descriptor or mapping' in Path(c['log']).read_text(),
                    'resource checker failed to detect installed loader regression')
        overlay=json.loads((out/'libfesvr-checkpoint.json').read_text())
        installed=FESVR/'lib/libfesvr.a';library=out/'libfesvr-checkpoint.a'
        require(overlay['installed_sha256']==file_sha(installed) and overlay['output_sha256']==file_sha(library),
                'loader overlay/archive binding changed')
        import subprocess
        names=subprocess.check_output(['ar','t',installed],text=True).splitlines()
        require(names==subprocess.check_output(['ar','t',library],text=True).splitlines(),'changed FESVR member inventory')
        replacements={'elfloader.o'}
        # Retained revision-112 evidence replaced only the loader. New builds
        # explicitly bind the separately owned context source too.
        if 'sources' in overlay:
            replacements.add('context.o')
            require(set(overlay['sources']) == {str(p) for p in overlay_inputs() if p.suffix=='.cc'},
                    'unexpected FESVR replacement source inventory')
        for name in names:
            equal=subprocess.check_output(['ar','p',installed,name])==subprocess.check_output(['ar','p',library,name])
            require(equal==(name not in replacements),'overlay changed unrelated installed state owner')
    return dict(status='passed',fresh_metadata_readbacks=24 if revision>=3 else 12,complete_unchanged_peer_images=168 if revision>=3 else 84,
                atomic_invalid_images=invalid_count,incompatible_rejections=len(r['incompatible']),
                exact_policy_rejections=8 if revision>=3 else 0,
                installed_xlen_rejections=192 if resource_marker in (out/'native-capture.log').read_text() else 6,
                loader_resource_cases=704 if resources_checked else 0,installed_negative_controls=2 if resources_checked else 0,
                loader_resources_unchanged=resources_checked,level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.audit:print(json.dumps(audit(a.audit),indent=2));return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs destination')
    require(os.environ.get('VCS_HOME')=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX')=='/usr/bin/g++-13','source vcs-env LAST')
    a.out.resolve().mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    elf=out/'polling.elf';elf.write_bytes(polling_elf())
    (out/'legacy.metadata').write_bytes(canonical(elf,legacy=True))
    (out/'revision2.metadata').write_bytes(canonical(elf,revision=2))
    source=TESTS/'tsi_startup_metadata_fesvr.cc';sv=TESTS/'tsi_startup_metadata_fesvr_tb.sv';library=FESVR/'lib/libfesvr.a'
    sources=[source,STUBS/'fesvr/firesim_tsi.cc',STUBS/'fesvr/owned_fesvr_tsi.cc',TESTCHIP/'testchip_tsi.cc',TESTCHIP/'testchip_htif.cc']
    inputs=[*sources,sv,library,Path(__file__),TESTS/'elfloader_resource_checks.h',TESTS/'tsi_polling_cut_checks.h',TESTS/'verify_tsi_host_control_fesvr_vcs.py',
            TESTS/'verify_firesim_tsi_loadmem_vcs.py',TESTS/'verify_semantic_vcs.py',TESTS/'verify_loadmem_read_checkpoint_vcs.py',
            *sorted((STUBS/'fesvr').glob('*.h')),*sorted(TESTCHIP.glob('*.h')),*sorted((FESVR/'include/fesvr').glob('*.h')),
            CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    inputs = [*inputs, *overlay_inputs()]
    snapshots=out/'sources';snapshots.mkdir();bindings=[]
    for f in inputs:
        digest=file_sha(f);snapshot=snapshots/digest
        if not snapshot.exists():shutil.copyfile(f,snapshot)
        bindings.append(dict(path=str(f),sha256=digest,snapshot=str(snapshot)))
    commands=[]
    def execute(argv,name,expected=0,**extra):
        log=out/(name+'.log');argv=['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])]
        text=run(argv,log,cwd=out,expected=expected)
        import re
        c=dict(cwd=str(out.relative_to(ROOT)),argv=argv,log=str(log),expected_exit=expected,
               pid=int(re.search(r'fresh_process_pid=(\d+)',text)[1]),**extra)
        commands.append(c);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');return c
    library = build_overlay(out, execute, named_log=True)
    include=f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    native=out/'metadata-native';sanitized=out/'metadata-sanitized';simv=out/'metadata-simv'
    for binary,flags in ((native,[]),(sanitized,['-no-pie','-fsanitize=address,undefined','-fno-omit-frame-pointer'])):
        execute([os.environ['CXX'],*shlex.split(include),'-g',*flags,*sources,library,'-lpthread','-o',binary],binary.name+'-build')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_startup_metadata_fesvr_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_METADATA_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread','-o',simv,sv,*sources], 'vcs-build')
    original_library=FESVR/'lib/libfesvr.a';negative_native=out/'installed-loader-native';negative_simv=out/'installed-loader-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-g',*sources,original_library,'-lpthread','-o',negative_native],'installed-native-build')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_startup_metadata_fesvr_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"installed-csrc"}','-CFLAGS',include+' -DTSI_METADATA_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(original_library)+' -Wl,--no-whole-archive -lpthread','-o',negative_simv,sv,*sources], 'installed-vcs-build')
    resources=[];negative_controls=[]
    for backend in ('native','vcs-dpi'):
        for original in (False,True):
            dest=out/('loader-resources-'+backend+('-installed' if original else '-owned'))
            binary=(negative_native if original else sanitized) if backend=='native' else (negative_simv if original else simv)
            argv=[binary,'loader-resources',elf,'unused',dest] if backend=='native' else [binary,'-no_save',
                  '+mode=loader-resources','+source='+str(elf),'+image=unused','+destination='+str(dest)]
            c=execute(argv,dest.name,expected=2 if original else 0)
            (negative_controls if original else resources).append(c)
    def invoke(backend,mode,image,dest,name):
        argv=[native if mode=='capture' else sanitized,mode,elf,image,dest] if backend=='native' else [simv,'-no_save',
              '+mode='+mode,'+source='+str(elf),'+image='+str(image),'+destination='+str(dest)]
        return execute(argv,name,mode=mode,destination=str(dest),elf_sha256_at_run=file_sha(elf))
    for backend in ('native','vcs-dpi'):invoke(backend,'capture','unused',out/backend,backend+'-capture')
    restores=[];incompatible=[];policy_cases=[]
    for producer in ('native','vcs-dpi'):
        for backend in ('native','vcs-dpi'):
            for mode in ('prepare','invalid','xlen-recovery'):
                name=f'{producer}-{backend}-{mode}'
                restores.append(invoke(backend,mode,out/producer/'startup.metadata',out/name,name))
            for mode in ('prepare64','policy0to64','policy64to0'):
                name=f'{producer}-{backend}-{mode}'
                image=out/producer/('startup.metadata' if mode=='policy0to64' else 'startup64.metadata')
                policy_cases.append(invoke(backend,mode,image,out/name,name))
    for backend in ('native','vcs-dpi'):
        for mode in ('wrong-args','unsupported-long','unsupported-payload','unsupported-symbol-elf','unsupported-signature','unsupported-signature-granularity','changed-elf','wrong-loadmem','legacy-image','revision2-image'):
            if mode=='changed-elf':
                mutant=bytearray(polling_elf());mutant[176]^=1;elf.write_bytes(mutant);(out/'mutant.elf').write_bytes(mutant)
            name=f'{backend}-{mode}'
            image=out/'legacy.metadata' if mode=='legacy-image' else out/'native/startup.metadata'
            if mode=='revision2-image':image=out/'revision2.metadata'
            incompatible.append(invoke(backend,mode,image,out/name,name))
            elf.write_bytes(polling_elf())
    for b in bindings:require(file_sha(b['path'])==b['sha256'],'metadata source changed while native checks ran')
    report=dict(status='passed',scope='installed HTIF startup metadata component only; complete CPU restore pending',
                commands=commands,restores=restores,incompatible=incompatible,source_inputs=bindings,
                metadata_revision=3,policy_cases=policy_cases,
                loader_resources=resources,installed_negative_controls=negative_controls,
                level1_verified=False,level2_verified=False,artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(audit(path),indent=2))


if __name__=='__main__':main()
