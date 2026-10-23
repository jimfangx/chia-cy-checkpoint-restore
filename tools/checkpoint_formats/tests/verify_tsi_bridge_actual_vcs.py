"""Restore every actual FESVR bridge host-control image in fresh native/VCS.

This component check has no services and cannot certify complete CPU/HTIF state.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import tempfile
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT
from tools.checkpoint_formats.tests.verify_loadmem_transport_vcs import audit as audit_transport
TESTS=Path(__file__).resolve().parent
CC=ROOT/'sims/firesim/sim/midas/src/main/cc'
STUBS=ROOT/'generators/firechip/bridgestubs/src/main/cc'


def audit(path):
    path=path.resolve();r=json.loads(path.read_text());out=path.parent
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'],'invalid actual component scope')
    catalog=r['artifact_sha256']
    require(set(catalog)=={str(p) for p in out.rglob('*') if p.is_file() and p!=path},'changed actual restore membership')
    for p,digest in catalog.items():require(file_sha(p)==digest,'changed actual restore artifact '+p)
    bindings={b['path']:b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot'])==b['sha256'],'changed original actual bridge native source')
        check_native_input(ROOT,b['path'],b['sha256'],bindings)
    transport=Path(r['transport_summary'])
    require(file_sha(transport)==r['transport_summary_sha256'],'changed actual transport parent')
    require(audit_transport(transport)['actual_bridge_control_readbacks']==24,'incomplete independently audited actual source images')
    require(len(r['restores'])==48 and len({p['pid'] for p in r['restores']})==48,'incomplete fresh actual restore processes')
    for item in r['restores']:
        image=Path(item['image']);readback=Path(item['readback'])
        require(file_sha(image)==item['image_sha256'] and readback.read_bytes()==image.read_bytes(),'actual state mismatch')
        log=Path(item['log']).read_text()
        require(log.rstrip().endswith('exit=0') and 'ACTUAL_BRIDGE_CONTROL_RESTORE words=2 zero_edges=1 service_calls=0' in log,
                'missing actual complete restore readback/exit')
    for c in r['commands']:
        require(c['argv'][:2]==['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                Path(c['log']).read_text().rstrip().endswith('exit=0'),'unbound actual native environment/result')
        require(not any(e in Path(c['log']).read_text() for e in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')),
                'actual restore sanitizer error')
    return dict(status='passed',summary=str(path),original_actual_images=24,fresh_actual_component_restores=48,
                full_zero_edge_readbacks=48,service_calls=0,level1_verified=False,level2_verified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path)
    parser.add_argument('--transport-summary',type=Path);parser.add_argument('--audit',type=Path)
    args=parser.parse_args()
    if args.audit:print(json.dumps(audit(args.audit),indent=2));return
    require(args.out is not None and args.transport_summary is not None and
            args.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'),'need runs output and actual transport summary')
    require(os.environ.get('VCS_HOME')==_toolchain.VCS_HOME and
            os.environ.get('CXX')==_toolchain.CXX,'source vcs-env.sh LAST')
    parent=args.transport_summary.resolve();require(audit_transport(parent)['actual_bridge_control_readbacks']==24,'need actual images')
    args.out.resolve().mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='invocation-',dir=args.out.resolve()))
    source=TESTS/'tsi_bridge_actual_checkpoint.cc';sv=TESTS/'tsi_bridge_actual_checkpoint_tb.sv'
    inputs=[source,sv,Path(__file__),STUBS/'bridges/tsi_bridge_state.h',CC/'core/checkpoint.h',CC/'core/widget_checkpoint.h',
            TESTS/'verify_loadmem_transport_vcs.py',TESTS/'verify_loadmem_read_checkpoint_vcs.py',TESTS/'verify_semantic_vcs.py',
            ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots=out/'source-snapshots';snapshots.mkdir();bindings=[]
    for p in inputs:
        digest=file_sha(p);snapshot=snapshots/digest
        if not snapshot.exists():shutil.copyfile(p,snapshot)
        bindings.append(dict(path=str(p),snapshot=str(snapshot),sha256=digest))
    commands=[]
    def execute(argv,log):
        command=['bash','-lc',ENVIRONMENT+shlex.join([str(a) for a in argv])]
        text=run(command,log,cwd=out);result=dict(cwd=str(out.relative_to(ROOT)),argv=command,log=str(log),
                                                 pid=int(re.search(r'fresh_process_pid=(\d+)',text)[1]))
        commands.append(result);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');return result
    include=f'-std=c++17 -I{CC} -I{STUBS}';native=out/'actual-native';simv=out/'actual-simv'
    execute([os.environ['CXX'],*shlex.split(include),'-Wall','-Wextra','-Werror','-no-pie','-g',
             '-fsanitize=address,undefined','-fno-omit-frame-pointer',source,'-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_bridge_actual_checkpoint_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_BRIDGE_ACTUAL_DPI',
             '-o',simv,sv,source],out/'vcs-build.log')
    restores=[]
    for source_backend in ('native','vcs-dpi'):
        for chunk in (1,2):
            for cut in range(6):
                image=parent.parent/source_backend/f'bridge-{chunk}-control-{cut}.owner'
                for backend in ('native-sanitized','vcs-dpi'):
                    dest=out/f'{source_backend}-{chunk}-{cut}-{backend}';elf=parent.parent/'partial-write.elf'
                    argv=[native,image,dest,elf,chunk] if backend=='native-sanitized' else [simv,'-no_save',
                          '+image='+str(image),'+out='+str(dest),'+elf='+str(elf),'+chunk='+str(chunk)]
                    c=execute(argv,out/(dest.name+'.log'))
                    require((dest/'preedge.owner').read_bytes()==image.read_bytes(),'actual restore mismatch')
                    restores.append(dict(c,source_backend=source_backend,backend=backend,chunk=chunk,cut=cut,
                                         image=str(image),image_sha256=file_sha(image),readback=str(dest/'preedge.owner')))
    for b in bindings:require(file_sha(b['path'])==b['sha256'],'source changed during actual restore')
    report=dict(status='passed',scope='actual bridge host-control images only; full CPU/HTIF pending',
                transport_summary=str(parent),transport_summary_sha256=file_sha(parent),commands=commands,restores=restores,
                source_inputs=bindings,artifact_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
                level1_verified=False,level2_verified=False)
    path=out/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(audit(path),indent=2))


if __name__=='__main__':main()
