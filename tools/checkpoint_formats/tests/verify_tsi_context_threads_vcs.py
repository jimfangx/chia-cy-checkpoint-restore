"""Real worker/action admission faults through the sixteen-owner context API.

Uses archived independent context oracles, current exact-recipe provider, and
an optional prior-provider sensitivity witness. This is component evidence.
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

BACKENDS = ('native', 'vcs-dpi')
OPERATIONS = ('prepare', 'commit', 'capture', 'resume-fresh', 'resume-live')
FAULTS = ('worker-mask', 'worker-pending', 'second-worker-pending', 'shared-pending', 'action-flags', 'action-mask')
SIGNALS = (2, 15, 6)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--context-summary', type=Path, required=True)
    p.add_argument('--recipe-build-identity', type=Path, required=True)
    p.add_argument('--prior-recipe-build-identity', type=Path)
    a = p.parse_args()
    require(a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env LAST')
    parent = a.context_summary.resolve(); parent_audit(parent)
    r = json.loads(parent.read_text()); scenario = parent.parent/'scenario-1'
    host = json.loads(Path(r['host_summary']).read_text()); polling = Path(host['polling_summary']).parent
    plan = (scenario/'plan').read_text().splitlines()
    require(plan[6:8] == ['TICK', 'TICK'], 'oracle requires two adjacent polling yields')
    cuts = {'execution': 6, 'tail': len(plan)}
    source = TESTS/'tsi_context_threads_fesvr.cc'; sv = TESTS/'tsi_context_threads_fesvr_tb.sv'
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc',
               TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc', TESTS/'tsi_terminal_allocations.cc']
    identities = {'current': a.recipe_build_identity.resolve()}
    if a.prior_recipe_build_identity: identities['prior'] = a.prior_recipe_build_identity.resolve()
    inputs = [Path(__file__), TESTS/'audit_tsi_context_threads.py', sv, *sources, parent, *identities.values(),
              *sorted((STUBS/'fesvr').glob('*.h')), STUBS/'fesvr/htif_lifecycle_provider.inc',
              *sorted(TESTS.glob('tsi*.cc')), *sorted(TESTS.glob('tsi*.h'))]
    archives = {}
    for name, path in identities.items():
        identity = json.loads(path.read_text())
        require(identity['htif_lifecycle_provider_linked'], 'need actual recipe provider')
        if name == 'current':
            for f, h in identity['sources_sha256'].items(): require(file_sha(f) == h, 'changed recipe input '+f)
        archive = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
        archives[name] = archive; inputs += [archive, archive.with_suffix('.json')]
    a.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve())); (out/'sources').mkdir()
    bindings = []
    for f in dict.fromkeys(inputs):
        digest = file_sha(f); snapshot = out/'sources'/digest
        if not snapshot.exists(): shutil.copyfile(f, snapshot)
        bindings.append(dict(path=str(f), sha256=digest, snapshot=str(snapshot)))
    commands = []; command_lock = threading.Lock()
    def execute(argv, log, expected=0):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]
        run(command, log, cwd=out, expected=expected)
        row = dict(argv=command, cwd=str(out.relative_to(ROOT)), log=str(log), expected_exit=expected)
        with command_lock:
            commands.append(row); (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return row
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    for name, archive in archives.items():
        folder = out/name; folder.mkdir(); shutil.copyfile(archive, folder/'libfesvr-checkpoint.a')
        library = folder/'libfesvr-checkpoint.a'
        execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined',
                 '-fno-omit-frame-pointer', *sources, library, '-lpthread', '-o', folder/'native'], folder/'native-build.log')
        execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
                 '-top', 'tsi_context_threads_fesvr_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
                 '-Mdir='+str(folder/'csrc'), '-CFLAGS', include+' -DTSI_CONTEXT_THREADS_DPI',
                 '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread',
                 '-o', folder/'simv', sv, *sources], folder/'vcs-build.log')
    def invoke(job):
        version, boundary, op, fault, sig, backend = job
        dest = out/version/f'{boundary}-{op}-{fault}-{sig}-{backend}'
        values = list(map(str, [op, fault, sig, polling/'polling.elf', polling/'scenario-1/input',
                               scenario/'native-capture/startup.metadata', scenario/'native-capture'/f'cut-{cuts[boundary]}', dest]))
        argv = [out/version/'native', *values] if backend == 'native' else [out/version/'simv', '-no_save',
                *['+'+k+'='+v for k,v in zip(('operation','fault','signal_number','elf','terminal','metadata','source','destination'),values)]]
        # sigpending() already exposes process-shared pending signals to the
        # old calling-thread guard. Retain those as prior-provider controls;
        # only missing worker/action checks are sensitivity witnesses.
        expected = 2 if version == 'prior' and fault != 'shared-pending' else 0
        return dict(execute(argv, dest.with_suffix('.log'), expected),
                    version=version, boundary=boundary, operation=op, fault=fault, signal=sig,
                    backend=backend, destination=str(dest), source=values[-2])
    jobs = list(itertools.product(archives, cuts, OPERATIONS, FAULTS, SIGNALS, BACKENDS))
    with ThreadPoolExecutor(max_workers=8) as pool: results = list(pool.map(invoke, jobs))
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'thread source changed during execution')
    report = dict(status='passed', scope='sixteen-owner all-thread admission; production coordinator and CPU pending',
                  context_summary=str(parent), context_sha256=file_sha(parent), identities={k:str(v) for k,v in identities.items()},
                  source_inputs=bindings, cuts=cuts, commands=commands, results=results,
                  level1_verified=False, level2_verified=False,
                  artifact_sha256={str(f):file_sha(f) for f in out.rglob('*') if f.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    from tools.checkpoint_formats.tests.audit_tsi_context_threads import audit
    try: checked = audit(path)
    except Exception:
        report['status'] = 'failed'; path.write_text(json.dumps(report, indent=2)+'\n'); raise
    print(json.dumps(dict(summary=str(path), **checked), indent=2))


if __name__ == '__main__': main()
