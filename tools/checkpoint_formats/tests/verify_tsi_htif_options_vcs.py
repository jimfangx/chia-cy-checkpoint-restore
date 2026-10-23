"""Check real FESVR long-option aliases retain the original configured HTIF route."""
from tools.checkpoint_formats import toolchain as _toolchain
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
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR

OPTIONS=('default','--c=/','--ch=/','--chr=/','--chro=/','--chroo=/','--chroot=/','+chroot=/','--signature=/unused-signature')

def audit(path):
    path=path.resolve();r=json.loads(path.read_text());out=path.parent
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'],'wrong option scope')
    require(set(r['artifact_sha256'])=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'changed option artifact membership')
    for p,digest in r['artifact_sha256'].items():require(file_sha(p)==digest,'changed option artifact')
    bindings={b['path']:b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed option source snapshot');check_native_input(ROOT,b['path'],b['sha256'],bindings)
    require(len(r['cases'])==2*len(OPTIONS),'missing native/VCS option cases')
    for c in r['cases']:
        require('REAL_HTIF_OPTION option='+c['option']+' owned_default='+str(int(c['option']=='default'))+' contexts=1 cpu_edges=0' in Path(c['log']).read_text(),'configured HTIF loop bypassed')
    for c in r['commands']:
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and Path(c['log']).read_text().rstrip().endswith('exit=0'),'unbound native option command')
    return dict(status='passed',actual_installed_fesvr_option_checks=len(r['cases']),level1_verified=False,level2_verified=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.audit:print(json.dumps(audit(a.audit),indent=2));return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs output')
    require(os.environ.get('VCS_HOME')==_toolchain.VCS_HOME and os.environ.get('CXX')==_toolchain.CXX,'source vcs-env LAST')
    a.out.resolve().mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    source=TESTS/'tsi_htif_options_fesvr.cc';sv=TESTS/'tsi_htif_options_fesvr_tb.sv';library=FESVR/'lib/libfesvr.a'
    sources=[source,STUBS/'fesvr/firesim_tsi.cc',STUBS/'fesvr/owned_fesvr_tsi.cc',TESTCHIP/'testchip_tsi.cc',TESTCHIP/'testchip_htif.cc']
    inputs=[*sources,sv,library,Path(__file__),TESTS/'verify_semantic_vcs.py',TESTS/'verify_loadmem_read_checkpoint_vcs.py',
            *sorted((STUBS/'fesvr').glob('*.h')),*sorted(TESTCHIP.glob('*.h')),*sorted((FESVR/'include/fesvr').glob('*.h')),
            CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    inputs = [*inputs, *overlay_inputs()]
    snapshots=out/'sources';snapshots.mkdir();bindings=[]
    for f in inputs:
        digest=file_sha(f);snapshot=snapshots/digest
        if not snapshot.exists():shutil.copyfile(f,snapshot)
        bindings.append(dict(path=str(f),sha256=digest,snapshot=str(snapshot)))
    commands=[]
    def execute(argv,log):
        argv=['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])];run(argv,log,cwd=out)
        c=dict(cwd=str(out.relative_to(ROOT)),argv=argv,log=str(log));commands.append(c);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');return c
    library = build_overlay(out, execute)
    include=f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}';native=out/'options-native';simv=out/'options-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-g',*sources,library,'-lpthread','-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_htif_options_fesvr_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_HTIF_OPTIONS_DPI',
             '-LDFLAGS','-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread','-o',simv,sv,*sources],out/'vcs-build.log')
    cases=[]
    for backend in ('native','vcs-dpi'):
        for i,option in enumerate(OPTIONS):
            argv=[native,option] if backend=='native' else [simv,'-no_save','+option='+option]
            cases.append(dict(execute(argv,out/f'{backend}-{i}.log'),option=option))
    for b in bindings:require(file_sha(b['path'])==b['sha256'],'option source changed during execution')
    report=dict(status='passed',scope='configured HTIF option routing only; CPU acceptance pending',commands=commands,cases=cases,source_inputs=bindings,
                level1_verified=False,level2_verified=False,artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(audit(path),indent=2))

if __name__=='__main__':main()
