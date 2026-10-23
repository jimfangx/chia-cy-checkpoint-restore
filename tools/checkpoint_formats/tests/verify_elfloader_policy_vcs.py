"""Check scoped loader policy providers in native sanitizers and native VCS."""
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
from tools.checkpoint_formats.tests.fesvr_overlay import overlay_inputs, build_overlay
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, FESVR
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_tsi_host_control_fesvr_vcs import polling_elf


def audit(path):
    path=path.resolve();r=json.loads(path.read_text());out=path.parent
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'],'wrong provider scope')
    require(set(r['artifact_sha256'])=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'provider artifact membership changed')
    for f,d in r['artifact_sha256'].items():require(file_sha(f)==d,'changed provider artifact '+f)
    bindings={b['path']:b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed provider source snapshot')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    require((out/'polling.elf').read_bytes()==polling_elf(),'provider ELF changed')
    require(len(r['cases'])==4,'missing actual provider backends/negative controls')
    for c in r['cases']:
        log=Path(c['log']).read_text()
        marker=('FAIL missing or invalid HTIF loader policy provider' if c['expected_exit']==2 else
                'ELF_POLICY_PROVIDER cases=176 repetitions=16 modes=11 sticky_rejection=1 thread_isolation=1 resources_unchanged=1')
        require(marker in log,'missing actual provider check')
    for c in r['commands']:
        log=Path(c['log']).read_text()
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(c['expected_exit'])),'unbound provider command')
        require(not any(t in log for t in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),'provider sanitizer error')
    return dict(status='passed',actual_provider_cases=352,missing_provider_negative_controls=2,
                level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.audit:print(json.dumps(audit(a.audit),indent=2));return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs destination')
    require(os.environ.get('VCS_HOME')==_toolchain.VCS_HOME and os.environ.get('CXX')==_toolchain.CXX,'source vcs-env LAST')
    a.out.resolve().mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    source=TESTS/'elfloader_policy.cc';sv=TESTS/'elfloader_policy_tb.sv';library=FESVR/'lib/libfesvr.a'
    inputs=[source,sv,Path(__file__),TESTS/'elfloader_resource_checks.h',library,*overlay_inputs(),
            TESTS/'verify_semantic_vcs.py',TESTS/'verify_tsi_host_control_fesvr_vcs.py',
            TESTS/'verify_loadmem_read_checkpoint_vcs.py',TESTS/'verify_firesim_tsi_loadmem_vcs.py',
            *sorted((FESVR/'include/fesvr').glob('*.h')),
            ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots=out/'sources';snapshots.mkdir();bindings=[]
    for f in inputs:
        digest=file_sha(f);snapshot=snapshots/digest
        if not snapshot.exists():shutil.copyfile(f,snapshot)
        bindings.append(dict(path=str(f),sha256=digest,snapshot=str(snapshot)))
    commands=[]
    def execute(argv,name,expected=0):
        log=out/(name+'.log');argv=['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])]
        run(argv,log,cwd=out,expected=expected)
        c=dict(cwd=str(out.relative_to(ROOT)),argv=argv,log=str(log),expected_exit=expected)
        commands.append(c);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');return c
    library=build_overlay(out,execute,named_log=True)
    elf=out/'polling.elf';elf.write_bytes(polling_elf());cases=[]
    include=f'-std=c++17 -I{CC} -I{STUBS} -I{FESVR/"include"}'
    for original in (False,True):
        name='installed' if original else 'owned';lib=FESVR/'lib/libfesvr.a' if original else library
        native=out/(name+'-native');simv=out/(name+'-simv')
        flags=[] if original else ['-no-pie','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        execute([os.environ['CXX'],*shlex.split(include),'-g',*flags,source,lib,'-lpthread','-o',native],name+'-native-build')
        execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','elfloader_policy_tb',
                 '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/(name+"-csrc")}',
                 '-CFLAGS',include+' -DELF_POLICY_DPI','-LDFLAGS','-Wl,--whole-archive '+str(lib)+' -Wl,--no-whole-archive -lpthread',
                 '-o',simv,sv,source],name+'-vcs-build')
        cases.append(execute([native,elf],name+'-native-run',2 if original else 0))
        cases.append(execute([simv,'-no_save','+source='+str(elf)],name+'-vcs-run',2 if original else 0))
    for b in bindings:require(file_sha(b['path'])==b['sha256'],'provider source changed during checks')
    report=dict(status='passed',scope='loader policy provider only; CPU acceptance pending',commands=commands,
                cases=cases,source_inputs=bindings,level1_verified=False,level2_verified=False,
                artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(audit(path),indent=2))


if __name__=='__main__':main()
