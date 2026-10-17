"""Prepare/publish and continue the actual restricted production TSI bridge.

The serial device is a component MMIO fixture. This is not CPU acceptance.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shlex
import shutil
import tempfile
import threading

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests.audit_tsi_context_group import audit as parent_audit, images
from tools.checkpoint_formats.tests.audit_tsi_context_image import canonical
from tools.checkpoint_formats.tests.verify_tsi_context_image_vcs import malformed

BACKENDS = ('native', 'vcs-dpi')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--context-summary', type=Path, required=True)
    p.add_argument('--recipe-build-identity', type=Path, required=True)
    a = p.parse_args()
    require(a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    parent = a.context_summary.resolve(); parent_audit(parent)
    r = json.loads(parent.read_text()); host = json.loads(Path(r['host_summary']).read_text())
    polling = Path(host['polling_summary']).parent
    identity_path = a.recipe_build_identity.resolve(); identity = json.loads(identity_path.read_text())
    require(identity['htif_lifecycle_provider_linked'], 'need actual recipe provider')
    archive = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
    # A retained, source-bound provider archive is linked with the current bridge
    # sources below. The resulting component binary has its own build identity;
    # the historical recipe executable is never called this component's build.
    source = TESTS/'tsi_bridge_context.cc'; sv = TESTS/'tsi_bridge_context_tb.sv'
    sources = [source, STUBS/'bridges/tsibridge.cc', CC/'core/widget.cc', CC/'bridges/loadmem.cc',
               STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc',
               TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc', TESTS/'tsi_terminal_allocations.cc']
    inputs = [Path(__file__), TESTS/'audit_tsi_bridge_context.py', TESTS/'audit_tsi_context_group.py',
              TESTS/'audit_tsi_context_image.py', TESTS/'verify_tsi_context_image_vcs.py',
              TESTS/'verify_semantic_vcs.py', TESTS/'verify_loadmem_read_checkpoint_vcs.py',
              TESTS/'verify_firesim_tsi_loadmem_vcs.py', sv, *sources, parent, identity_path,
              archive, archive.with_suffix('.json'),
              ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh',
              *sorted((CC/'core').glob('*.h')), CC/'bridges/loadmem.h', STUBS/'bridges/serial_data.h',
              *sorted((STUBS/'fesvr').glob('*.h')), STUBS/'bridges/tsibridge.h', STUBS/'bridges/tsi_bridge_state.h',
              *sorted(TESTS.glob('tsi*.cc')), *sorted(TESTS.glob('tsi*.h'))]
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve())); (out/'sources').mkdir()
    bindings = []
    for f in dict.fromkeys(inputs):
        digest = file_sha(f); snapshot = out/'sources'/digest
        if not snapshot.exists(): shutil.copyfile(f, snapshot)
        bindings.append(dict(path=str(f), sha256=digest, snapshot=str(snapshot)))
    (out/'source-inputs.json').write_text(json.dumps(bindings, indent=2)+'\n')
    binding = dict(recipe_identity_sha256=file_sha(identity_path),
                   sources={b['path']:b['sha256'] for b in bindings}, cxx=os.environ['CXX'],
                   vcs_home=os.environ['VCS_HOME'], language='c++17')
    (out/'build-binding.json').write_text(json.dumps(binding, sort_keys=True, indent=2)+'\n')
    build = bytes.fromhex(file_sha(out/'build-binding.json')); (out/'build.sha256').write_bytes(build)
    shutil.copyfile(archive, out/'libfesvr-checkpoint.a'); library = out/'libfesvr-checkpoint.a'
    commands = []; command_lock = threading.Lock()
    def execute(argv, log):
        log.parent.mkdir(parents=True, exist_ok=True)
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        run(command, log, cwd=out)
        result = dict(argv=command, cwd=str(out.relative_to(ROOT)), log=str(log), expected_exit=0)
        with command_lock:
            commands.append(result); (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return result
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined',
             '-fno-omit-frame-pointer', *sources, library, '-lpthread', '-lgmp', '-o', out/'native'], out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'tsi_bridge_context_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_BRIDGE_CONTEXT_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread -Wl,--no-as-needed -lgmp -Wl,--as-needed',
             '-o', out/'simv', sv, *sources], out/'vcs-build.log')
    def invoke(i, backend, mode, cut, image, dest):
        scenario = parent.parent/f'scenario-{i}'; folder = polling/f'scenario-{i}'
        values = list(map(str, [mode, polling/'polling.elf', folder/('flush.input' if i >= 4 else 'input'),
                      scenario/'native-capture/startup.metadata', scenario/'native-capture'/f'cut-{cut}',
                      scenario/'plan', dest, image, out/'build.sha256']))
        argv = [out/'native', *values] if backend == 'native' else [out/'simv', '-no_save',
                *['+'+k+'='+v for k,v in zip(('mode','elf','terminal','metadata','source','plan','destination','image_path','build_path'),values)]]
        return dict(execute(argv, Path(str(dest)+'.log')), scenario=i, backend=backend, mode=mode,
                    cut=cut, destination=str(dest), image=str(image))
    cuts = {}; restore_jobs = []
    for i in range(8):
        scenario = parent.parent/f'scenario-{i}'; last = len((scenario/'plan').read_text().splitlines())
        phases = [images(scenario/'native-capture'/f'cut-{c}')['syscall'][88] for c in range(last+1)]
        active = phases.index(3) if 3 in phases else phases.index(1)
        cuts[i] = sorted({0, 6, active, last})
        metadata = (scenario/'native-capture/startup.metadata').read_bytes()
        for cut in cuts[i]:
            image = out/f'source-{i}-{cut}.context'
            image.write_bytes(canonical(build, metadata, images(scenario/'native-capture'/f'cut-{cut}')))
            for backend in BACKENDS:
                restore_jobs.append((i, backend, 'restore', cut, image, out/f'restore-{i}-{cut}-{backend}'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        restores = list(pool.map(lambda job: invoke(*job), restore_jobs))
    chosen = cuts[1][2]; source_image = out/f'source-1-{chosen}.context'
    invalid_dir = out/'invalid-images'; invalid_dir.mkdir()
    owners = images(parent.parent/'scenario-1/native-capture'/f'cut-{chosen}')
    metadata = (parent.parent/'scenario-1/native-capture/startup.metadata').read_bytes()
    invalid_jobs = []
    for name, payload in malformed(build, metadata, owners).items():
        image = invalid_dir/name; image.write_bytes(payload)
        for backend in BACKENDS:
            invalid_jobs.append((name,backend,image))
    def invalid(job):
        name,backend,image = job
        return dict(invoke(1,backend,'invalid',chosen,image,out/f'invalid-{name}-{backend}'),case=name)
    with ThreadPoolExecutor(max_workers=4) as pool:
        invalids = list(pool.map(invalid, invalid_jobs))
    specials = [invoke(1,b,m,chosen,source_image,out/(m+'-'+b))
                for b in BACKENDS for m in ('atomic','foreign','guard-mask','guard-control')]
    faults = []
    for f in r['faults']:
        i, cut = f['scenario'], f['cut']
        scenario = parent.parent/f'scenario-{i}'
        owners = images(scenario/'native-capture'/f'cut-{cut}')
        owners['syscall'] = (scenario/'native-capture'/f'cut-{cut}.fault').read_bytes()
        image = out/f'fault-{i}.context'
        if not image.exists():
            image.write_bytes(canonical(build, (scenario/'native-capture/startup.metadata').read_bytes(), owners))
        faults.append(dict(invoke(i,f['backend'],'corrupt',cut,image,out/f'fault-{i}-{f["backend"]}'),
                           divergence=f['divergence']))
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'source changed during bridge check '+b['path'])
    report = dict(status='passed', scope='restricted production bridge candidate and serial-MMIO continuation only',
                  context_summary=str(parent), context_sha256=file_sha(parent), recipe_build_identity=str(identity_path),
                  source_inputs=bindings, cuts=cuts, restores=restores, invalids=invalids, specials=specials,
                  faults=faults, commands=commands, build_sha256=build.hex(), level1_verified=False, level2_verified=False,
                  artifact_sha256={str(f):file_sha(f) for f in out.rglob('*') if f.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    from tools.checkpoint_formats.tests.audit_tsi_bridge_context import audit
    try: checked = audit(path)
    except Exception:
        report['status'] = 'failed'; path.write_text(json.dumps(report, indent=2)+'\n'); raise
    print(json.dumps(dict(summary=str(path), **checked), indent=2))


if __name__ == '__main__': main()
