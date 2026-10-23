"""Joint runtime IO preparation/publication, synthetic AXI traffic; no CPU acceptance."""
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
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT

CC = ROOT/'sims/firesim/sim/midas/src/main/cc'
TESTS = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--rocket-header', type=Path, required=True)
    a = p.parse_args()
    require(a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env LAST')
    header=a.rocket_header.resolve()
    require('.ctrl = AXI4Config{12, 32, 32}' in header.read_text(), 'need exact Rocket control geometry')
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    sources=[TESTS/'runtime_io_checkpoint.cc', *[CC/s for s in (
        'core/simif.cc','core/simulation.cc','core/widget_registry.cc','core/widget.cc',
        'core/stream_engine.cc','core/bridge_driver.cc','core/driver_boundary_diagnostic.cc',
        'emul/simif_emul.cc','emul/mm.cc','emul/mmio.cc','emul/qsfp.cc','emul/host_timing.cc',
        'bridges/master.cc','bridges/clock.cc','bridges/loadmem.cc')]]
    sv=TESTS/'runtime_io_checkpoint_tb.sv'
    inputs=[Path(__file__),TESTS/'audit_runtime_io.py',TESTS/'audit_mmio_io.py',sv,*sources,*CC.rglob('*.h'),header,
            ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    (out/'sources').mkdir(); bindings=[]
    for f in sorted(set(inputs)):
        h=file_sha(f); saved=out/'sources'/h
        if not saved.exists(): shutil.copyfile(f,saved)
        bindings.append(dict(path=str(f),sha256=h,snapshot=str(saved)))
    (out/'source-inputs.json').write_text(json.dumps(bindings,indent=2)+'\n')
    commands=[]
    def execute(argv,name,expected=0):
        cmd=['bash','-lc',ENVIRONMENT+shlex.join(map(str,argv))]
        log=out/(name+'.log'); run(cmd,log,cwd=out,expected=expected)
        result=dict(argv=cmd,cwd=str(out.relative_to(ROOT)),log=str(log))
        commands.append(result); (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        return result
    includes=f'-std=c++20 -DVCS -I{CC}'
    execute([os.environ['CXX'],*shlex.split(includes),'-g','-no-pie','-fsanitize=address,undefined',
             '-fno-omit-frame-pointer',*sources,'-pthread','-lgmp','-o',out/'native'],'native-build')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps',
             '-top','runtime_io_checkpoint_tb','-cc',os.environ['CC'],'-cpp',os.environ['CXX'],
             '-Mdir='+str(out/'csrc'),'-CFLAGS',includes+' -DRUNTIME_IO_DPI',
             '-LDFLAGS','-Wl,--no-as-needed -pthread -lgmp','-o',out/'simv',sv,*sources],'vcs-build')
    cases=[]
    for backend in ('native','vcs-dpi'):
        for delay in (0,1):
            reference=None
            modes=('reference','restore','sealed-restore','negative','fatal-unsealed','fatal-thread',
                   'fatal-destination','fatal-recycled','fatal-consumed','fatal-stale')
            for mode,cut in [(m,c) for c in range(3) for m in modes]:
                reference=out/f'{backend}-{delay}-reference-{cut}'
                dest=reference if mode=='reference' else out/f'{backend}-{delay}-{mode}-{cut}'
                argv=([out/'native',mode,reference,dest,cut,delay] if backend=='native' else
                      [out/'simv','-no_save',f'+mode={mode}',f'+source={reference}',
                       f'+destination={dest}',f'+cut={cut}',f'+beat={delay}'])
                cases.append(dict(execute(argv,dest.name,86 if mode.startswith('fatal-') else 0),backend=backend,delay=delay,mode=mode,cut=cut,
                                  destination=str(dest),reference=str(reference)))
    for b in bindings: require(file_sha(b['path'])==b['sha256'],'source changed '+b['path'])
    report=dict(status='passed',scope='joint production runtime IO; synthetic AXI traffic',
                level1_verified=False,level2_verified=False,runtime_io_transaction=True,
                sealed_publication=True,
                cases=cases,commands=commands,source_inputs=bindings,
                rocket_header=str(header),artifact_sha256={str(f):file_sha(f) for f in out.rglob('*') if f.is_file()})
    path=out/'summary.json'; path.write_text(json.dumps(report,indent=2)+'\n')
    from tools.checkpoint_formats.tests.audit_runtime_io import audit
    try: checked=audit(path)
    except Exception:
        report['status']='failed'; path.write_text(json.dumps(report,indent=2)+'\n'); raise
    print(json.dumps(dict(summary=str(path),**checked),indent=2))


if __name__=='__main__': main()
