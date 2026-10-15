"""Read back real suspended program-loader components in fresh native/VCS processes."""
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
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import audit as integration_audit, CC, STUBS, TESTS

PHASES = (0, 1, 2, 2, 2, 3, 3)


def audit(path):
    path = path.resolve(); r = json.loads(path.read_text()); out = path.parent
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong loader scope')
    require(set(r['artifact_sha256']) == {str(f) for f in out.rglob('*') if f.is_file() and f != path}, 'changed loader membership')
    for f, digest in r['artifact_sha256'].items(): require(file_sha(f) == digest, 'changed loader artifact '+f)
    bindings = {b['path']: b for b in r['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed loader source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    parent = Path(r['integration_summary'])
    require(file_sha(parent) == r['integration_sha256'], 'changed suspended ELF integration')
    require(integration_audit(parent)['status'] == 'passed', 'actual ELF loader failed')
    require(len(r['restores']) == 28, 'missing fresh actual program-loader readbacks')
    for c in r['restores']:
        expected = config(23,1,0)+words(PHASES[c['cut']])
        require(Path(c['image']).read_bytes() == Path(c['readback']).read_bytes() == expected, 'incomplete loader readback')
        require('COMPLETE_PROGRAM_READBACK target_edges=0 context_entries=0 services=0' in Path(c['log']).read_text(),
                'loader restore serviced target/context')
        require('LOADER_OWNER_CHECKS invalids=7072 transitions=16 policies=4 phases=4' in Path(c['log']).read_text(),
                'missing atomic invalid images/configuration/phase checks')
    for c in r['commands']:
        log = Path(c['log']).read_text()
        require(c['argv'][:2] == ['bash','-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                log.rstrip().endswith('exit='+str(c['expected_exit'])), 'unbound loader native environment/exit')
        require(not any(e in log for e in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected')), 'loader sanitizer failed')
    require(len(r['corruptions']) == 2, 'missing component corruption checks')
    for c in r['corruptions']:
        require('FIRST_DIVERGENCE component_operation=0 signal=loader_phase expected=2 actual=3 acknowledged=0' in
                Path(c['log']).read_text(), 'wrong loader corruption divergence')
    return dict(status='passed', fresh_actual_loader_readbacks=28, actual_suspended_images=14,
                policies=4, phases=4, atomic_invalid_images_per_process=7072,
                component_first_divergences=2, level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path); p.add_argument('--integration-summary',type=Path); p.add_argument('--audit',type=Path)
    a = p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit),indent=2)); return
    require(a.out and a.integration_summary and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output/integration')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    parent = a.integration_summary.resolve(); require(integration_audit(parent)['status'] == 'passed','need actual suspended images')
    a.out.resolve().mkdir(parents=True,exist_ok=True); out = Path(tempfile.mkdtemp(prefix='invocation-',dir=a.out.resolve()))
    source = TESTS/'tsi_program_loader_checkpoint.cc'; sv = TESTS/'tsi_program_loader_checkpoint_tb.sv'
    inputs = [source, sv, Path(__file__), STUBS/'fesvr/tsi_program_loader.h', CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h',
              TESTS/'verify_firesim_tsi_loadmem_vcs.py', TESTS/'verify_semantic_vcs.py',
              TESTS/'verify_loadmem_read_checkpoint_vcs.py', ROOT/'env.sh',ROOT/'sims/firesim/env.sh',ROOT/'automations/checkpoint_loop/vcs-env.sh']
    snapshots = out/'sources'; snapshots.mkdir(); bindings = []
    for f in inputs:
        digest = file_sha(f); snapshot = snapshots/digest
        if not snapshot.exists(): shutil.copyfile(f,snapshot)
        bindings.append(dict(path=str(f),sha256=digest,snapshot=str(snapshot)))
    commands = []
    def execute(argv, log, expected=0):
        argv = ['bash','-lc',ENVIRONMENT+shlex.join([str(x) for x in argv])]
        run(argv,log,cwd=out,expected=expected)
        c = dict(cwd=str(out.relative_to(ROOT)),argv=argv,log=str(log),expected_exit=expected)
        commands.append(c); (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n'); return c
    native = out/'loader-native'; simv = out/'loader-simv'
    include = f'-std=c++17 -I{CC} -I{STUBS}'
    execute([os.environ['CXX'],*shlex.split(include),'-g','-no-pie','-fsanitize=address,undefined','-fno-omit-frame-pointer',source,'-o',native],out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-timescale=1ns/1ps','-top','tsi_program_loader_checkpoint_tb',
             '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],f'-Mdir={out/"csrc"}','-CFLAGS',include+' -DTSI_PROGRAM_LOADER_DPI',
             '-o',simv,sv,source],out/'vcs-build.log')
    def invoke(backend,image,dest,phase,expected=0):
        argv = [native,image,dest,phase] if backend=='native' else [simv,'-no_save','+source='+str(image),'+destination='+str(dest),'+phase='+str(phase)]
        return execute(argv,dest.with_suffix('.log'),expected)
    restores = []; corruptions = []
    for producer in ('native','vcs-dpi'):
        for cut,phase in enumerate(PHASES):
            image = parent.parent/producer/f'suspended-{cut}.program'
            require(image.read_bytes() == config(23,1,0)+words(phase),'actual suspended loader differs')
            for backend in ('native','vcs-dpi'):
                dest = out/f'{producer}-{cut}-{backend}.readback'
                c = invoke(backend,image,dest,phase)
                restores.append(dict(c,image=str(image),readback=str(dest),cut=cut))
    corrupt = out/'corrupt.program'; corrupt.write_bytes(config(23,1,0)+words(3))
    for backend in ('native','vcs-dpi'):
        dest = out/('corrupt-'+backend+'.readback')
        corruptions.append(invoke(backend,corrupt,dest,2,3))
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'loader source changed during checks')
    report = dict(status='passed',scope='program-loader routing component; ELF/memif/HTIF caller restore pending',
                  integration_summary=str(parent),integration_sha256=file_sha(parent),source_inputs=bindings,
                  commands=commands,restores=restores,corruptions=corruptions,level1_verified=False,level2_verified=False,
                  artifact_sha256={str(f):file_sha(f) for f in sorted(out.rglob('*')) if f.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(audit(path),indent=2))


if __name__ == '__main__': main()
