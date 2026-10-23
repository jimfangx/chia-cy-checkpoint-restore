"""Outer run_host component restores and actual source-coroutine observations.

Requires the complete recipe-bound polling suite. No complete CPU acceptance.
"""
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
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests import verify_tsi_polling_syscall_vcs as polling

BACKENDS = ('native', 'vcs-dpi')
CODES = (0, -1, -2147483648, 2147483647)


def scenario(code):
    events = ['START', 'POLL 0', 'POLL 1', 'POLL 1', 'POLL 0', 'POLL 2', 'STOP', f'EXIT {code}', 'NONE']
    phases = (0, 1, 1, 1, 1, 1, 2, 3, 4, 4)
    return events, [config(35, 1, 32)+words(p, (code & 0xffffffff) if p == 4 else 0) for p in phases]


def audit(path):
    path = path.resolve(); r = json.loads(path.read_text()); out = path.parent
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong outer scope')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'outer artifact membership')
    for p, digest in r['artifact_sha256'].items(): require(file_sha(p) == digest, 'changed outer artifact '+p)
    bindings = {b['path']: b for b in r['source_inputs']}
    required = [Path(__file__), TESTS/'tsi_host_execution_checkpoint.cc', TESTS/'tsi_host_execution_fesvr.cc',
                STUBS/'fesvr/tsi_host_execution.h', STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/firesim_tsi.h']
    require(len(bindings) == len(r['source_inputs']) and all(str(p) in bindings for p in required), 'missing outer sources')
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'outer snapshot drift')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    parent = Path(r['polling_summary']); require(file_sha(parent) == r['polling_sha256'], 'polling evidence changed')
    parent_audit = polling.audit(parent)
    require(parent_audit['fresh_restores'] == 3452, 'incomplete recipe polling scope')
    previous = json.loads(parent.read_text())
    require(previous['recipe_build_identity'], 'polling not recipe-bound')
    commands = {c['log']: c for c in r['commands']}; used = set()
    require(len(commands) == len(r['commands']), 'duplicate outer command')
    def command(log, expected=0):
        log = str(log); c = commands[log]; used.add(log); text = Path(log).read_text()
        require(c['expected_exit'] == expected and c['argv'][:2] == ['bash', '-lc'] and
                c['argv'][2].startswith(ENVIRONMENT) and text.rstrip().endswith('exit='+str(expected)), 'unbound outer result')
        require(not any(x in text for x in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'outer sanitizer error')
        return c, text
    for name in ('native-build', 'vcs-build', 'production-native-build', 'production-vcs-build'):
        command(out/(name+'.log'))
    expected_restores = {(code, producer, backend, cut) for code in CODES for producer in BACKENDS
                         for backend in BACKENDS for cut in range(len(scenario(code)[1]))}
    actual = {(c['code'], c['producer'], c['backend'], c['cut']) for c in r['restores']}
    require(len(r['restores']) == len(expected_restores) and actual == expected_restores, 'missing outer fresh restore')
    comparisons = 0
    for code in CODES:
        events, images = scenario(code)
        for producer in BACKENDS:
            dest = out/f'{code}-{producer}-capture'; command(dest.with_suffix('.log'))
            require((dest/'preedge.owner').read_bytes() == images[0], 'outer source initial state')
            for i, image in enumerate(images[1:]): require((dest/f'after-{i}.owner').read_bytes() == image, 'outer source phase')
    for c in r['restores']:
        events, images = scenario(c['code']); dest = Path(c['destination']); cut = c['cut']
        _, text = command(c['log'])
        require('COMPLETE_OUTER_READBACK target_edges=0 context_entries=0 services=0' in text and
                f'poisoned_services=4 return={c["code"]}' in text, 'outer readback/service guards missing')
        require((dest/'preedge.owner').read_bytes() == images[cut], 'outer pre-service state differs')
        for i, image in enumerate(images[cut+1:]): require((dest/f'after-{i}.owner').read_bytes() == image, 'outer continuation differs')
        comparisons += len(images)-cut
        argv = shlex.split(commands[c['log']]['argv'][2][len(ENVIRONMENT):])
        source = out/f'{c["code"]}-{c["producer"]}-capture'/('preedge.owner' if cut == 0 else f'after-{cut-1}.owner')
        require(str(source) in argv or '+source='+str(source) in argv, 'unbound cross-backend source')
    require(len(r['invalids']) == 8 and len(r['faults']) == 8 and len(r['production']) == 16, 'incomplete outer negative/production scope')
    for c in r['invalids']:
        command(c['log'], 2); require(not (Path(c['destination'])/'preedge.owner').exists(), 'invalid outer partially restored')
    for c in r['faults']:
        _, text = command(c['log'], 3)
        require('FIRST_DIVERGENCE operation=0 signal=service' in text and 'acknowledged=0' in text, 'outer corruption not first boundary')
    for c in r['production']:
        _, text = command(c['log']); spec = polling.SPECS[c['scenario']]
        raw = ((spec[1] << 1) | 1) & 0xffffffff
        expected = (raw if raw < 0x80000000 else raw-0x100000000) // 2
        dest = Path(c['destination'])
        for name, phase, code in [('new', 0, 0), ('polling', 1, 0), ('returned', 4, expected)]:
            require((dest/(name+'.outer')).read_bytes() == config(35, 1, 32)+words(phase, code & 0xffffffff), 'actual outer phase/return mismatch')
        require(f'operations={len(polling.scenario(*spec, idle_rounds=2)["plan"])} startup_rejections=2 tail_ticks=3 return={expected}' in text and
                'component_context_rejected=1 target_edges=0' in text, 'actual outer completion/guards missing')
    require(set(commands) == used, 'extra/missing outer process')
    return dict(status='passed', fresh_restores=len(r['restores']), complete_owner_comparisons=comparisons,
                production_processes=16, startup_rejections=32, tail_ticks=48, invalid_processes=8,
                first_divergences=8, level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path)
    p.add_argument('--polling-summary', type=Path); p.add_argument('--audit', type=Path); a = p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit), indent=2)); return
    require(a.out and a.polling_summary and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output and polling summary')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env LAST')
    parent = a.polling_summary.resolve(); polling.audit(parent); previous = json.loads(parent.read_text())
    require(previous['recipe_build_identity'], 'need recipe-bound polling')
    a.out.resolve().mkdir(parents=True, exist_ok=True); out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    component = TESTS/'tsi_host_execution_checkpoint.cc'; sv = TESTS/'tsi_host_execution_checkpoint_tb.sv'
    source = TESTS/'tsi_host_execution_fesvr.cc'; production_sv = TESTS/'tsi_host_execution_fesvr_tb.sv'
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc',
               TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc', TESTS/'tsi_terminal_allocations.cc']
    inputs = [component, sv, production_sv, Path(__file__), *sources,
              *[Path(b['path']) for b in previous['source_inputs']], parent,
              CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h', STUBS/'fesvr/tsi_host_execution.h']
    (out/'sources').mkdir(); bindings = []
    for path in dict.fromkeys(inputs):
        digest = file_sha(path); snapshot = out/'sources'/digest
        if not snapshot.exists(): shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    commands = []
    def execute(argv, log, expected=0):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]; run(command, log, cwd=out, expected=expected)
        c = dict(argv=command, cwd=str(out.relative_to(ROOT)), log=str(log), expected_exit=expected); commands.append(c)
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n'); return c
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    native_flags = ['-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    execute([os.environ['CXX'], *shlex.split(include), *native_flags, component, '-o', out/'native'], out/'native-build.log')
    vcs = [Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
           '-cc', os.environ['CC'], '-cpp', os.environ['CXX']]
    execute([*vcs, '-top', 'tsi_host_execution_checkpoint_tb', '-Mdir='+str(out/'csrc'),
             '-CFLAGS', include+' -DTSI_HOST_EXECUTION_DPI', '-o', out/'simv', sv, component], out/'vcs-build.log')
    library = parent.parent/'libfesvr-checkpoint.a'
    execute([os.environ['CXX'], *shlex.split(include), *native_flags, *sources, library, '-lpthread', '-o', out/'production-native'], out/'production-native-build.log')
    execute([*vcs, '-top', 'tsi_host_execution_fesvr_tb', '-Mdir='+str(out/'production-csrc'),
             '-CFLAGS', include+' -DTSI_HOST_EXECUTION_FESVR_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread',
             '-o', out/'production-simv', production_sv, *sources], out/'production-vcs-build.log')
    def invoke(backend, source, plan, dest, expected=0):
        argv = [out/'native', source, plan, dest] if backend == 'native' else [out/'simv', '-no_save',
                '+source='+str(source), '+plan='+str(plan), '+destination='+str(dest)]
        return dict(execute(argv, dest.with_suffix('.log'), expected), backend=backend, destination=str(dest))
    restores, invalids, faults, production = [], [], [], []
    for code in CODES:
        events, images = scenario(code); plan = out/f'{code}.plan'; plan.write_text('\n'.join(events)+'\n')
        for producer in BACKENDS: invoke(producer, 'new', plan, out/f'{code}-{producer}-capture')
        for cut in range(len(images)):
            plan = out/f'{code}-cut-{cut}.plan'; plan.write_text(''.join(line+'\n' for line in events[cut:]))
            for producer in BACKENDS:
                source = out/f'{code}-{producer}-capture'/('preedge.owner' if cut == 0 else f'after-{cut-1}.owner')
                for backend in BACKENDS:
                    restores.append(dict(invoke(backend, source, plan, out/f'{code}-{producer}-{backend}-cut-{cut}'), code=code, cut=cut, producer=producer))
    good = scenario(-1)[1][1]
    for i, bad in enumerate((good[:-1], good+b'\0', bytes([good[0]^1])+good[1:], config(35, 1, 64)+words(1, 0))):
        source = out/f'invalid-{i}.owner'; source.write_bytes(bad)
        for backend in BACKENDS: invalids.append(invoke(backend, source, out/'-1-cut-1.plan', out/f'invalid-{i}-{backend}', 2))
    for i, (phase, event) in enumerate(((2, 'POLL 1'), (1, 'STOP'), (3, 'STOP'), (4, 'EXIT -1'))):
        source = out/f'fault-{i}.owner'; source.write_bytes(config(35, 1, 32)+words(phase, 0))
        plan = out/f'fault-{i}.plan'; plan.write_text(event+'\n')
        for backend in BACKENDS: faults.append(invoke(backend, source, plan, out/f'fault-{i}-{backend}', 3))
    for i, spec in enumerate(polling.SPECS):
        folder = parent.parent/f'scenario-{i}'
        values = ['observe', parent.parent/'polling.elf', folder/('flush.input' if spec[2] else 'input'),
                  folder/'native-capture/startup.metadata', folder/'native-capture/cut-0', folder/'plan']
        for backend in BACKENDS:
            dest = out/f'production-{i}-{backend}'
            argv = [out/'production-native', *values, dest] if backend == 'native' else [out/'production-simv', '-no_save',
                    *['+'+k+'='+str(v) for k, v in zip(('mode', 'elf', 'terminal', 'metadata', 'source', 'plan', 'destination'), [*values, dest])]]
            production.append(dict(execute(argv, dest.with_suffix('.log')), scenario=i, backend=backend, destination=str(dest)))
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'outer input changed during tests')
    report = dict(status='passed', scope='outer caller component and production observation; wrapper/context and CPU pending',
                  polling_summary=str(parent), polling_sha256=file_sha(parent), source_inputs=bindings, commands=commands,
                  restores=restores, invalids=invalids, faults=faults, production=production,
                  level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in out.rglob('*') if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(audit(path), indent=2))


if __name__ == '__main__': main()
