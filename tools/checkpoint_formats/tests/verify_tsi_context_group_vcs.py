"""Restricted sixteen-owner component restores with fresh native coroutines.

Explicit host-operation cuts; no complete CPU/simulator checkpoint acceptance.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
from concurrent.futures import ThreadPoolExecutor
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
from tools.checkpoint_formats.tests.verify_loadmem_read_checkpoint_vcs import ENVIRONMENT, config, words
from tools.checkpoint_formats.tests.verify_firesim_tsi_loadmem_vcs import CC, STUBS, TESTS, TESTCHIP, FESVR
from tools.checkpoint_formats.tests import verify_tsi_host_group_vcs as host

polling = host.polling
NAMES = (*host.NAMES, 'wrapper')
BACKENDS = host.BACKENDS
GUARDS = ('wrapper', 'peer', 'exit', 'stop', 'mask', 'pending')


def scenario(spec):
    s = polling.scenario(*spec, idle_rounds=2)
    states = [dict(state, outer=config(35, 1, 32)+words(1, 0), wrapper=config(36, 1)+words(1)) for state in s['states']]
    response = polling.packets([1, polling.polling.FROMHOST, 0, 1, 0, 1, 0], spec[2])
    final = dict(host.scenario(spec)['states'][-1], serial=polling.syscall.serial(response, []), wrapper=config(36, 1)+words(2))
    states.append(final)
    final = dict(final, serial=polling.syscall.serial([], [])); states.extend([final, final])
    return dict(plan=s['plan']+['TICK', 'PACKET '+' '.join(map(str, response)), 'TICK'],
                states=states, code=host.scenario(spec)['code'])


def saved(prefix):
    return {name: Path(str(prefix)+'.'+name).read_bytes() for name in NAMES}


def audit(path):
    path = path.resolve(); r = json.loads(path.read_text()); out = path.parent
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong context scope')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'context artifact membership')
    for p, digest in r['artifact_sha256'].items(): require(file_sha(p) == digest, 'changed context artifact '+p)
    bindings = {b['path']: b for b in r['source_inputs']}
    required = [Path(__file__), TESTS/'tsi_context_group_fesvr.cc', TESTS/'tsi_context_group_fesvr_tb.sv',
                STUBS/'fesvr/tsi_context_group.h', STUBS/'fesvr/tsi_host_wrapper.h',
                STUBS/'fesvr/owned_fesvr_tsi.cc', STUBS/'fesvr/owned_context.cc', STUBS/'fesvr/firesim_tsi.cc']
    require(len(bindings) == len(r['source_inputs']) and all(str(p) in bindings for p in required), 'missing context sources')
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'context snapshot drift')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    parent = Path(r['host_summary']); require(file_sha(parent) == r['host_sha256'], 'context parent changed')
    require(host.audit(parent)['fresh_restores'] == 3580, 'incomplete context parent')
    if r['recipe_build_identity']:
        identity = json.loads(Path(r['recipe_build_identity']).read_text())
        production = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
        require(file_sha(production) == file_sha(out/'libfesvr-checkpoint.a'), 'context provider differs from recipe')
        for name, digest in identity['sources_sha256'].items():
            if name in bindings: require(bindings[name]['sha256'] == digest, 'context/recipe source mismatch')
    commands = {c['log']: c for c in r['commands']}; used = set()
    require(len(commands) == len(r['commands']), 'duplicate context command')
    def command(log):
        c = commands[str(log)]; used.add(str(log)); text = Path(log).read_text(); lines = text.splitlines()
        require(c['argv'][:2] == ['bash', '-lc'] and c['argv'][2].startswith(ENVIRONMENT) and text.rstrip().endswith('exit=0'), 'unbound context result')
        require(lines[0] == 'cwd='+str(out) and json.loads(lines[1][5:]) == c['argv'] and
                lines[2].startswith('fresh_process_pid=') and int(lines[2].split('=')[1]) > 0, 'context native process binding')
        require(not any(x in text for x in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'context sanitizer failure')
        return c, text
    for name in ('native-build', 'vcs-build'): command(out/(name+'.log'))
    expected = {(i, p, b, c) for i, spec in enumerate(polling.SPECS) for p in BACKENDS for b in BACKENDS for c in range(len(scenario(spec)['states']))}
    actual = {(c['scenario'], c['producer'], c['backend'], c['cut']) for c in r['restores']}
    require(len(r['restores']) == len(expected) and actual == expected, 'incomplete context cuts')
    comparisons = operations = 0
    for i, spec in enumerate(polling.SPECS):
        s = scenario(spec)
        for b in BACKENDS:
            dest = out/f'scenario-{i}'/(b+'-capture'); _, text = command(dest.with_suffix('.log'))
            require('fresh=0' in text, 'not actual source coroutine')
            for cut, state in enumerate(s['states']): require(saved(dest/f'cut-{cut}') == state, 'source context/oracle mismatch')
    for c in r['restores']:
        s = scenario(polling.SPECS[c['scenario']]); cut = c['cut']; dest = Path(c['destination']); cmd, text = command(c['log'])
        require('COMPLETE_CONTEXT_READBACK owners=16 services=0 target_edges=0 context_entries=0' in text and
                f'operations={len(s["states"])-cut-1}' in text and f'return={s["code"]}' in text and 'tail_ticks=3 startup_replays=0' in text, 'context readback/continuation missing')
        source = out/f'scenario-{c["scenario"]}'/(c['producer']+'-capture')/f'cut-{cut}'
        argv = shlex.split(cmd['argv'][2][len(ENVIRONMENT):]); require(str(source) in argv or '+source='+str(source) in argv, 'unbound context image')
        require(saved(dest/'preedge') == s['states'][cut], 'context zero-entry complete readback')
        require((dest/'continuation.bin').read_bytes() == b''.join(state[n] for state in s['states'][cut+1:] for n in NAMES), 'context continuation differs')
        comparisons += len(NAMES)*(len(s['states'])-cut); operations += len(s['states'])-cut-1
    require(len(r['invalids']) == 2*(3*len(NAMES)+3) and len(r['guards']) == 2*len(GUARDS) and
            len(r['faults']) == 8 and len(r['resources']) == 8, 'incomplete context negatives')
    require({(Path(c['destination']).name, c['backend']) for c in r['invalids']} ==
            {(f'invalid-{n}-{b}', b) for n in range(51) for b in BACKENDS}, 'invalid context membership')
    require({(c['scenario'], c['backend']) for c in r['faults']} == {(i, b) for i in (1, 3, 5, 7) for b in BACKENDS}, 'context fault membership')
    require({(c['mode'], c['backend']) for c in r['resources']} ==
            {(m, b) for m in ('thread', 'allocation', 'resume-mask', 'resume-pending') for b in BACKENDS}, 'context resource membership')
    require({(c['backend'], c['mode']) for c in r['guards']} == {(b, 'guard-'+g) for b in BACKENDS for g in GUARDS}, 'missing context guard')
    for c in r['invalids']:
        _, text = command(c['log']); require('REJECTED owners=16 unpublished=1 context_entries=0 target_edges=0' in text and not list(Path(c['destination']).glob('preedge.*')), 'invalid context partially published')
    for c in r['guards']:
        _, text = command(c['log']); require('CONTEXT_LATE_GUARD '+c['mode']+' unpublished=1 services=0 target_edges=0 context_entries=0' in text, 'context guard missing')
    for b in BACKENDS:
        dest = out/('atomic-'+b); command(dest.with_suffix('.log'))
        m = re.fullmatch(r'malformed=(\d+) membership=64 cross=2 allocation_failures=(\d+) unchanged_on_failure=1 context_entries=0\n', (dest/'atomic.txt').read_text())
        require(m and int(m[1]) > 1800 and int(m[2]) > 40, 'incomplete context atomic coverage')
    for c in r['resources']:
        _, text = command(c['log'])
        expected = ('FOREIGN_CREATOR rejected=1 unpublished=1 context_entries=0 target_edges=0' if c['mode'] == 'thread' else
                    'CONTEXT_ALLOCATION stack_bytes=1048576 rejected=1 unchanged=1 retry=1' if c['mode'] == 'allocation' else
                    'CONTEXT_RESUME_GUARD '+c['mode']+' boundaries=2 unchanged=1 services=0 target_edges=0')
        require(expected in text, 'context resource rejection missing')
    for c in r['faults']:
        _, text = command(c['log']); require(c['divergence'] in text, 'context corruption not first divergent boundary')
    require(used == set(commands), 'unclassified context native commands')
    return dict(status='passed', fresh_restores=len(actual), complete_owner_comparisons=comparisons,
                host_operations=operations, actual_source_coroutines=16, invalid_processes=len(r['invalids']), late_guards=12,
                resource_checks=8, first_divergences=8, level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path); p.add_argument('--host-summary', type=Path)
    p.add_argument('--recipe-build-identity', type=Path); p.add_argument('--audit', type=Path); a = p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit), indent=2)); return
    require(a.out and a.host_summary and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output and host parent')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env LAST')
    parent = a.host_summary.resolve(); host.audit(parent)
    a.out.resolve().mkdir(parents=True, exist_ok=True); out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    source = TESTS/'tsi_context_group_fesvr.cc'; sv = TESTS/'tsi_context_group_fesvr_tb.sv'
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc', TESTCHIP/'testchip_tsi.cc',
               TESTCHIP/'testchip_htif.cc', TESTS/'tsi_terminal_allocations.cc']
    library = Path(json.loads(parent.read_text())['polling_summary']).parent/'libfesvr-checkpoint.a'
    extra = []
    if a.recipe_build_identity:
        identity = json.loads(a.recipe_build_identity.read_text())
        for name, digest in identity['sources_sha256'].items(): require(file_sha(name) == digest, 'changed recipe input '+name)
        require(identity['htif_lifecycle_provider_linked'], 'missing recipe provider')
        library = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'; extra = [a.recipe_build_identity.resolve()]
    inputs = [Path(__file__), sv, *sources, *extra, parent, library, STUBS/'fesvr/owned_context.cc',
              *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTS.glob('tsi*.cc')), *sorted(TESTS.glob('tsi*.h')),
              *[Path(b['path']) for b in json.loads(parent.read_text())['source_inputs']]]
    (out/'sources').mkdir(); bindings = []
    for path in dict.fromkeys(inputs):
        digest = file_sha(path); snapshot = out/'sources'/digest
        if not snapshot.exists(): shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    shutil.copyfile(library, out/'libfesvr-checkpoint.a'); library = out/'libfesvr-checkpoint.a'
    commands = []
    def execute(argv, log):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]; run(command, log, cwd=out)
        c = dict(argv=command, cwd=str(out.relative_to(ROOT)), log=str(log)); commands.append(c)
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n'); return c
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', *sources, library, '-lpthread', '-o', out/'native'], out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps', '-top', 'tsi_context_group_fesvr_tb',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_CONTEXT_GROUP_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread', '-o', out/'simv', sv, *sources], out/'vcs-build.log')
    polling_parent = Path(json.loads(parent.read_text())['polling_summary']); elf = polling_parent.parent/'polling.elf'
    def invoke(i, backend, mode, name, producer='native', cut=0, source=None):
        folder = out/f'scenario-{i}'; dest = folder/name if mode in ('capture', 'restore', 'corrupt', 'allocation') else out/name
        values = list(map(str, (mode, elf, polling_parent.parent/f'scenario-{i}'/('flush.input' if polling.SPECS[i][2] else 'input'),
                      folder/(producer+'-capture')/'startup.metadata', source or folder/(producer+'-capture')/f'cut-{cut}', folder/'plan', dest)))
        argv = [out/'native', *values] if backend == 'native' else [out/'simv', '-no_save', *['+'+k+'='+v for k, v in zip(('mode', 'elf', 'terminal', 'metadata', 'source', 'plan', 'destination'), values)]]
        return dict(execute(argv, dest.with_suffix('.log')), scenario=i, backend=backend, mode=mode, destination=str(dest), producer=producer, cut=cut)
    for i, spec in enumerate(polling.SPECS):
        folder = out/f'scenario-{i}'; folder.mkdir(); (folder/'plan').write_text('\n'.join(scenario(spec)['plan'])+'\n')
        for b in BACKENDS: invoke(i, b, 'capture', b+'-capture', producer=b)
    jobs = [(i, b, 'restore', f'{p}-{b}-cut-{c}', p, c) for i, spec in enumerate(polling.SPECS) for p in BACKENDS for b in BACKENDS for c in range(len(scenario(spec)['states']))]
    with ThreadPoolExecutor(max_workers=8) as pool: restores = list(pool.map(lambda j: invoke(*j), jobs))
    chosen = 1; s = scenario(polling.SPECS[chosen]); cut = next(c for c, state in enumerate(s['states']) if state['syscall'][88] == 3)
    for b in BACKENDS: invoke(chosen, b, 'atomic', 'atomic-'+b, cut=cut)
    guards = [invoke(chosen, b, 'guard-'+g, 'guard-'+g+'-'+b, cut=cut) for b in BACKENDS for g in GUARDS]
    resources = [invoke(chosen, b, m, m+'-'+b, cut=cut) for b in BACKENDS for m in ('thread', 'allocation', 'resume-mask', 'resume-pending')]
    bad_states = []
    for n in range(3*len(NAMES)):
        state = dict(s['states'][cut]); name = NAMES[n % len(NAMES)]; bad = bytearray(state[name])
        if n < len(NAMES): bad = bad[:-1]
        elif n < 2*len(NAMES): bad[16] ^= 1
        else: bad += b'\0'
        state[name] = bytes(bad); bad_states.append(state)
    for c, phase in [(cut, 0), (cut, 2), (len(s['states'])-1, 1)]:
        bad_states.append(dict(s['states'][c], wrapper=config(36, 1)+words(phase)))
    invalids = []
    for n, state in enumerate(bad_states):
        prefix = out/f'bad-{n}'
        for name in NAMES: Path(str(prefix)+'.'+name).write_bytes(state[name])
        for b in BACKENDS: invalids.append(invoke(chosen, b, 'invalid', f'invalid-{n}-{b}', source=prefix))
    faults = []
    for i in (1, 3, 5, 7):
        cut, bad, divergence = polling.fault_case(i, idle_rounds=2)
        prefix = out/f'scenario-{i}/native-capture'/f'cut-{cut}'; Path(str(prefix)+'.fault').write_bytes(bad)
        for b in BACKENDS: faults.append(dict(invoke(i, b, 'corrupt', 'corrupt-'+b, cut=cut), divergence=divergence.replace('context_entries=0', 'fresh_context=1')))
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'context source changed during execution')
    report = dict(status='passed', scope='restricted fresh wrapper/context component continuation; complete CPU pending', host_summary=str(parent), host_sha256=file_sha(parent),
                  recipe_build_identity=str(a.recipe_build_identity.resolve()) if a.recipe_build_identity else None, source_inputs=bindings, commands=commands,
                  restores=restores, invalids=invalids, guards=guards, resources=resources, faults=faults, level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in out.rglob('*') if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(dict(summary=str(path), **audit(path)), indent=2))


if __name__ == '__main__': main()
