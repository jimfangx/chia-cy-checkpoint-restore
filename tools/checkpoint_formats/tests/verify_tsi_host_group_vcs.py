"""Restricted fifteen-owner outer/polling/provider component restoration.

Every existing polling cut and explicit stop/return boundary crosses native
ASan/UBSan and VCS in both directions. Host operations are not target cycles.
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
from tools.checkpoint_formats.tests import verify_tsi_polling_syscall_vcs as polling

NAMES = (*polling.NAMES, 'outer')
BACKENDS = ('native', 'vcs-dpi')
GUARDS = ('outer', 'peer', 'exit', 'stop', 'mask', 'pending')


def scenario(spec):
    s = polling.scenario(*spec, idle_rounds=2)
    states = [dict(state, outer=config(35, 1, 32)+words(1, 0)) for state in s['states']]
    response = polling.packets([1, polling.polling.FROMHOST, 0, 1, 0, 1, 0], spec[2])
    final = dict(s['final'], serial=polling.syscall.serial(response, []), outer=config(35, 1, 32)+words(2, 0))
    states.append(final)
    final = dict(final, serial=polling.syscall.serial([], [])); states.append(final)
    final = dict(final, lifecycle=config(32, 1, 32, 0)+words(1, s['raw'], 1), outer=config(35, 1, 32)+words(3, 0))
    states.append(final)
    raw = s['raw']; code = (raw if raw < 0x80000000 else raw-0x100000000)//2
    final = dict(final, outer=config(35, 1, 32)+words(4, code & 0xffffffff)); states.append(final)
    return dict(plan=s['plan']+['TICK', 'PACKET '+' '.join(map(str, response)), 'TICK', 'TICK'],
                states=states, base_count=len(s['states']), code=code)


def saved(prefix):
    return {name: Path(str(prefix)+'.'+name).read_bytes() for name in NAMES}


def audit(path):
    path = path.resolve(); r = json.loads(path.read_text()); out = path.parent
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong host group scope')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'host artifact membership')
    for p, digest in r['artifact_sha256'].items(): require(file_sha(p) == digest, 'changed host artifact '+p)
    bindings = {b['path']: b for b in r['source_inputs']}
    required = [Path(__file__), TESTS/'tsi_host_group_fesvr.cc', TESTS/'tsi_host_group_fesvr_tb.sv',
                STUBS/'fesvr/tsi_host_group.h', STUBS/'fesvr/tsi_syscall_exit.h', STUBS/'fesvr/firesim_tsi.cc',
                STUBS/'fesvr/firesim_tsi.h', STUBS/'fesvr/tsi_host_execution.h']
    require(len(bindings) == len(r['source_inputs']) and all(str(p) in bindings for p in required), 'missing host sources')
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'host snapshot drift')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    parent = Path(r['polling_summary']); require(file_sha(parent) == r['polling_sha256'], 'host parent changed')
    require(polling.audit(parent)['fresh_restores'] == 3452, 'incomplete host parent')
    commands = {c['log']: c for c in r['commands']}; used = set()
    require(len(commands) == len(r['commands']), 'duplicate host command')
    def command(log):
        log = str(log); c = commands[log]; used.add(log); text = Path(log).read_text()
        lines = text.splitlines()
        require(c['argv'][:2] == ['bash', '-lc'] and c['argv'][2].startswith(ENVIRONMENT) and
                text.rstrip().endswith('exit=0'), 'unbound host command result')
        require(lines[0] == 'cwd='+str(out) and json.loads(lines[1][5:]) == c['argv'] and
                lines[2].startswith('fresh_process_pid=') and int(lines[2].split('=')[1]) > 0,
                'host argv/cwd/process evidence differs')
        require(not any(x in text for x in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'host sanitizer failure')
        return c, text
    for name in ('native-build', 'vcs-build'): command(out/(name+'.log'))
    expected = {(i, p, b, c) for i, spec in enumerate(polling.SPECS) for p in BACKENDS for b in BACKENDS
                for c in range(len(scenario(spec)['states']))}
    actual = {(c['scenario'], c['producer'], c['backend'], c['cut']) for c in r['restores']}
    require(len(r['restores']) == len(expected) and actual == expected, 'incomplete host fresh cuts')
    comparisons = operations = 0
    for i, spec in enumerate(polling.SPECS):
        s = scenario(spec); folder = out/f'scenario-{i}'
        for b in BACKENDS:
            capture = folder/(b+'-capture'); extension = folder/(b+'-extension')
            _, text = command(capture.with_suffix('.log')); require('fresh=0' in text, 'not live host source')
            command(extension.with_suffix('.log'))
            for cut, state in enumerate(s['states']):
                source = (capture if cut < s['base_count'] else extension)/f'cut-{cut}'
                require(saved(source) == state, 'complete host source differs')
            require(saved(capture/'live-returned') == s['states'][-1], 'actual production return differs')
    for c in r['restores']:
        s = scenario(polling.SPECS[c['scenario']]); cut = c['cut']; dest = Path(c['destination'])
        cmd, text = command(c['log'])
        require('COMPLETE_HOST_READBACK owners=15 services=0 target_edges=0 context_entries=0' in text and
                f'operations={len(s["states"])-cut-1} owners=15 complete=1' in text and f'return={s["code"]}' in text,
                'host readback/continuation receipt missing')
        source_folder = out/f'scenario-{c["scenario"]}'/(c['producer']+('-capture' if cut < s['base_count'] else '-extension'))
        source = source_folder/f'cut-{cut}'
        argv = shlex.split(cmd['argv'][2][len(ENVIRONMENT):])
        require(str(source) in argv or '+source='+str(source) in argv, 'unbound host source')
        require(saved(dest/'preedge') == s['states'][cut], 'host pre-service state mismatch')
        expected_bytes = b''.join(state[name] for state in s['states'][cut+1:] for name in NAMES)
        require((dest/'continuation.bin').read_bytes() == expected_bytes, 'host continuation byte mismatch')
        comparisons += len(NAMES)*(len(s['states'])-cut); operations += len(s['states'])-cut-1
    require(len(r['invalids']) == 2*(3*len(NAMES)+6) and len(r['guards']) == 2*len(GUARDS) and len(r['faults']) == 8,
            'incomplete host negatives')
    require({(Path(c['destination']).name, c['backend']) for c in r['invalids']} ==
            {(f'invalid-{n}-{b}', b) for n in range(3*len(NAMES)+6) for b in BACKENDS}, 'invalid host case membership')
    require({(c['mode'], c['backend']) for c in r['guards']} == {('guard-'+g, b) for g in GUARDS for b in BACKENDS},
            'host guard membership')
    require({(c['scenario'], c['backend']) for c in r['faults']} == {(i, b) for i in (1, 3, 5, 7) for b in BACKENDS},
            'host corruption membership')
    for c in r['invalids']:
        _, text = command(c['log']); require('REJECTED owners=15 unpublished=1 target_edges=0 context_entries=0' in text and
              not list(Path(c['destination']).glob('preedge.*')), 'invalid host image partially restored')
    for c in r['guards']:
        _, text = command(c['log']); require('HOST_LATE_GUARD '+c['mode']+' unpublished=1 services=0 target_edges=0 context_entries=0' in text,
                                            'missing host late guard')
    for b in BACKENDS:
        dest = out/f'atomic-{b}'; command(dest.with_suffix('.log'))
        m = re.fullmatch(r'malformed=(\d+) membership=60 cross=5 allocation_failures=(\d+) unchanged_on_failure=1\n', (dest/'atomic.txt').read_text())
        require(m and int(m[1]) > 1800 and int(m[2]) > 40, 'incomplete host atomic coverage')
    for c in r['faults']:
        _, text = command(c['log']); d = c['divergence']
        require(isinstance(d, str) and d.startswith('FIRST_DIVERGENCE operation=') and d in text,
                'host fault not first divergent outgoing word')
    require(used == set(commands), 'unclassified host native commands')
    return dict(status='passed', fresh_restores=len(actual), complete_owner_comparisons=comparisons,
                host_operations=operations, live_sources=16, invalid_processes=len(r['invalids']),
                late_guards=len(r['guards']), first_divergences=8, level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path)
    p.add_argument('--polling-summary', type=Path); p.add_argument('--audit', type=Path); a = p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit), indent=2)); return
    require(a.out and a.polling_summary and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output and polling parent')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env LAST')
    parent = a.polling_summary.resolve(); polling.audit(parent); previous = json.loads(parent.read_text())
    require(previous['recipe_build_identity'], 'host needs recipe-bound parent')
    a.out.resolve().mkdir(parents=True, exist_ok=True); out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    source = TESTS/'tsi_host_group_fesvr.cc'; sv = TESTS/'tsi_host_group_fesvr_tb.sv'
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc', TESTCHIP/'testchip_tsi.cc',
               TESTCHIP/'testchip_htif.cc', TESTS/'tsi_terminal_allocations.cc']
    library = parent.parent/'libfesvr-checkpoint.a'
    inputs = [Path(__file__), sv, *sources, *[Path(b['path']) for b in previous['source_inputs']], parent, library,
              *sorted((STUBS/'fesvr').glob('*.h'))]
    (out/'sources').mkdir(); bindings = []
    for path in dict.fromkeys(inputs):
        digest = file_sha(path); snapshot = out/'sources'/digest
        if not snapshot.exists(): shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    commands = []
    def execute(argv, log):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]; run(command, log, cwd=out)
        c = dict(argv=command, cwd=str(out.relative_to(ROOT)), log=str(log)); commands.append(c)
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n'); return c
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
             *sources, library, '-lpthread', '-o', out/'native'], out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps', '-top', 'tsi_host_group_fesvr_tb',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_HOST_GROUP_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread', '-o', out/'simv', sv, *sources], out/'vcs-build.log')
    elf = parent.parent/'polling.elf'
    def invoke(i, backend, mode, name, producer='native', cut=0, source=None):
        folder = out/f'scenario-{i}'; s = scenario(polling.SPECS[i]); dest = folder/name if mode in ('capture', 'extend', 'restore', 'corrupt') else out/name
        source_dir = folder/(producer+('-capture' if cut < s['base_count'] else '-extension'))
        values = list(map(str, (mode, elf, parent.parent/f'scenario-{i}'/('flush.input' if polling.SPECS[i][2] else 'input'),
                      folder/(producer+'-capture')/'startup.metadata', source or source_dir/f'cut-{cut}',
                      folder/('base.plan' if mode == 'capture' else 'plan'), dest)))
        argv = [out/'native', *values] if backend == 'native' else [out/'simv', '-no_save',
                *['+'+k+'='+v for k, v in zip(('mode', 'elf', 'terminal', 'metadata', 'source', 'plan', 'destination'), values)]]
        return dict(execute(argv, dest.with_suffix('.log')), scenario=i, backend=backend, mode=mode,
                    destination=str(dest), producer=producer, cut=cut)
    for i, spec in enumerate(polling.SPECS):
        folder = out/f'scenario-{i}'; folder.mkdir(); s = scenario(spec)
        (folder/'base.plan').write_text('\n'.join(s['plan'][:s['base_count']-1])+'\n')
        (folder/'plan').write_text('\n'.join(s['plan'])+'\n')
        for b in BACKENDS:
            invoke(i, b, 'capture', b+'-capture', producer=b)
            invoke(i, b, 'extend', b+'-extension', producer=b, cut=s['base_count']-1)
    jobs = [(i, b, 'restore', f'{p}-{b}-cut-{c}', p, c) for i, spec in enumerate(polling.SPECS)
            for p in BACKENDS for b in BACKENDS for c in range(len(scenario(spec)['states']))]
    with ThreadPoolExecutor(max_workers=8) as pool: restores = list(pool.map(lambda j: invoke(*j), jobs))
    chosen = 1; s = scenario(polling.SPECS[chosen]); cut = next(c for c, state in enumerate(s['states']) if state['syscall'][88] == 3)
    for b in BACKENDS:
        invoke(chosen, b, 'atomic', 'atomic-'+b, cut=cut)
    guards = [invoke(chosen, b, 'guard-'+g, 'guard-'+g+'-'+b, cut=cut) for b in BACKENDS for g in GUARDS]
    bad_states = []
    for n in range(3*len(NAMES)):
        state = dict(s['states'][cut]); name = NAMES[n % len(NAMES)]; bad = bytearray(state[name])
        if n < len(NAMES): bad = bad[:-1]
        elif n < 2*len(NAMES): bad[16] ^= 1
        else: bad += b'\0'
        state[name] = bytes(bad); bad_states.append(state)
    # Valid standalone phases bound to incompatible actual child/provider state.
    for c, phase in [(cut, 0), (cut, 2), (len(s['states'])-1, 1), (len(s['states'])-1, 2), (len(s['states'])-3, 3)]:
        bad_states.append(dict(s['states'][c], outer=config(35, 1, 32)+words(phase, 0)))
    bad_states.append(dict(s['states'][-1], outer=config(35, 1, 32)+words(4, (s['code'] ^ 1) & 0xffffffff)))
    invalids = []
    for n, state in enumerate(bad_states):
        prefix = out/f'bad-{n}'
        for name in NAMES: Path(str(prefix)+'.'+name).write_bytes(state[name])
        for b in BACKENDS: invalids.append(invoke(chosen, b, 'invalid', f'invalid-{n}-{b}', source=prefix))
    faults = []
    for i in (1, 3, 5, 7):
        cut, bad, divergence = polling.fault_case(i, idle_rounds=2)
        prefix = out/f'scenario-{i}/native-capture'/f'cut-{cut}'; Path(str(prefix)+'.fault').write_bytes(bad)
        for b in BACKENDS: faults.append(dict(invoke(i, b, 'corrupt', 'corrupt-'+b, cut=cut), divergence=divergence))
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'host input changed during execution')
    report = dict(status='passed', scope='restricted outer/polling/provider components; wrapper/context and complete CPU pending',
                  polling_summary=str(parent), polling_sha256=file_sha(parent), source_inputs=bindings, commands=commands,
                  restores=restores, invalids=invalids, guards=guards, faults=faults,
                  level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in out.rglob('*') if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(summary=str(path), **audit(path)), indent=2))


if __name__ == '__main__': main()
