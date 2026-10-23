"""Native ASan/UBSan and VCS checks of original-thread TSI access policy.

Component evidence only. Signals and complete simulator coordination remain
separate obligations. Each execution owns a fresh immutable diagnostic root.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
from concurrent.futures import ThreadPoolExecutor
import itertools
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
from tools.checkpoint_formats.tests.audit_tsi_context_group import audit as parent_audit

OPERATIONS = (
    'context-prepare', 'context-prepare-invalid', 'context-commit', 'context-capture', 'context-initialized',
    'context-resume-fresh', 'context-resume-live', 'host-prepare', 'host-commit', 'host-capture', 'host-advance',
    'syscall-prepare', 'syscall-commit', 'syscall-capture', 'syscall-advance',
    'polling-prepare', 'polling-commit', 'polling-capture', 'polling-advance',
    'exit-prepare', 'exit-capture', 'exit-completed', 'serial-send', 'serial-recv', 'serial-front',
    'serial-available', 'serial-valid', 'serial-ready', 'serial-owner', 'wrapper-owner',
    'host-tick', 'host-switch', 'host-busy', 'host-loaded', 'host-set-loaded', 'loadmem-send',
    'loadmem-read-request', 'loadmem-write-request', 'loadmem-data', 'loadmem-available',
    'memory-read', 'memory-write', 'memory-interface', 'metadata-save', 'metadata-prepare')

OPERATIONS += tuple('retained-'+owner+'-'+method for owner in ('poll', 'program', 'init', 'host', 'read', 'serial', 'loadread', 'queues', 'bcd', 'terminal', 'identity', 'write', 'memread', 'syscall', 'outer', 'wrapper')
                    for method in ('schema','save','validate','load','invalid-load'))

BACKENDS = ('native', 'vcs-dpi')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--context-summary', type=Path, required=True)
    p.add_argument('--recipe-build-identity', type=Path, required=True)
    a = p.parse_args()
    require(a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env LAST')
    parent = a.context_summary.resolve(); parent_audit(parent)
    r = json.loads(parent.read_text()); scenario = parent.parent/'scenario-1'
    host = json.loads(Path(r['host_summary']).read_text()); polling = Path(host['polling_summary']).parent
    cuts = {'execution': 6, 'tail': len((scenario/'plan').read_text().splitlines())}
    source = TESTS/'tsi_thread_access_fesvr.cc'; sv = TESTS/'tsi_thread_access_fesvr_tb.sv'
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc',
               TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc', TESTS/'tsi_terminal_allocations.cc']
    identity_path = a.recipe_build_identity.resolve(); identity = json.loads(identity_path.read_text())
    require(identity['htif_lifecycle_provider_linked'], 'need actual recipe provider')
    for f, h in identity['sources_sha256'].items(): require(file_sha(f) == h, 'changed recipe input '+f)
    archive = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
    inputs = [Path(__file__), TESTS/'audit_tsi_thread_access.py', sv, *sources, parent, identity_path,
              archive, archive.with_suffix('.json'), *sorted((STUBS/'fesvr').glob('*.h')),
              *sorted(TESTS.glob('tsi*.cc')), *sorted(TESTS.glob('tsi*.h'))]
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve())); (out/'sources').mkdir()
    bindings = []
    for f in dict.fromkeys(inputs):
        digest = file_sha(f); snapshot = out/'sources'/digest
        if not snapshot.exists(): shutil.copyfile(f, snapshot)
        bindings.append(dict(path=str(f), sha256=digest, snapshot=str(snapshot)))
    shutil.copyfile(archive, out/'libfesvr-checkpoint.a'); library = out/'libfesvr-checkpoint.a'
    commands = []; lock = threading.Lock()
    def execute(argv, log):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        run(command, log, cwd=out)
        row = dict(argv=command, cwd=str(out.relative_to(ROOT)), log=str(log), expected_exit=0)
        with lock:
            commands.append(row); (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return row
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined',
             '-fno-omit-frame-pointer', *sources, library, '-lpthread', '-o', out/'native'], out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'tsi_thread_access_fesvr_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_THREAD_ACCESS_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread',
             '-o', out/'simv', sv, *sources], out/'vcs-build.log')
    def invoke(job):
        boundary, op, backend = job; dest = out/f'{boundary}-{op}-{backend}'
        values = list(map(str, [op, polling/'polling.elf', polling/'scenario-1/input',
                               scenario/'native-capture/startup.metadata', scenario/'native-capture'/f'cut-{cuts[boundary]}', dest]))
        argv = [out/'native', *values] if backend == 'native' else [out/'simv', '-no_save',
                *['+'+k+'='+v for k,v in zip(('operation','elf','terminal','metadata','source','destination'),values)]]
        return dict(execute(argv, dest.with_suffix('.log')), boundary=boundary, operation=op,
                    backend=backend, destination=str(dest), source=values[-2])
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(invoke, itertools.product(cuts, OPERATIONS, BACKENDS)))
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'access source changed during execution')
    report = dict(status='passed', scope='original-thread TSI access including retained views; signals and CPU pending',
                  retained_views=True,
                  context_summary=str(parent), context_sha256=file_sha(parent), recipe_build_identity=str(identity_path),
                  source_inputs=bindings, cuts=cuts, commands=commands, results=results,
                  level1_verified=False, level2_verified=False,
                  artifact_sha256={str(f):file_sha(f) for f in out.rglob('*') if f.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    from tools.checkpoint_formats.tests.audit_tsi_thread_access import audit
    try: checked = audit(path)
    except Exception:
        report['status'] = 'failed'; path.write_text(json.dumps(report, indent=2)+'\n'); raise
    print(json.dumps(dict(summary=str(path), **checked), indent=2))


if __name__ == '__main__': main()
