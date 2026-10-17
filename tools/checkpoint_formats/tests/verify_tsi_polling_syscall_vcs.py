"""Production restricted syscall polling, fresh native/VCS component restores.

This does not restore sessions/descriptors, signals, outer callers or CPU state.
All cut labels are explicit host-operation indices, never target cycles.
"""
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
from tools.checkpoint_formats.tests.fesvr_overlay import BUILDER, overlay_inputs
from tools.checkpoint_formats.tests import verify_tsi_syscall_exit_vcs as syscall
from tools.checkpoint_formats.tests import verify_tsi_polling_prepare_vcs as polling

NAMES = (*polling.NAMES, 'syscall', 'lifecycle')
BACKENDS = ('native', 'vcs-dpi')
SPECS = tuple((residue, code, flush) for flush in (0, 0x20004000) for residue, code in syscall.SPECS)
GUARDS = ('pending', 'mask', 'exit', 'stop', 'peer')
ADMISSION = ('entry-duplicate', 'entry-unsealed', 'entry-signature',
             'unsupported-odd', 'unsupported-device', 'unsupported-selector', 'terminal-corrupt')
DESCRIPTORS = ('descriptors-restricted', 'descriptors-ordinary')


def queues(image):
    data = [int.from_bytes(image[i:i+8], 'little') for i in range(64, len(image), 8)]
    n = data[0]; return data[1:1+n], data[2+n:]


def packets(data, flush):
    """Installed FireSim cache-flush walk before each actual chunk service."""
    result = []
    while data:
        command, low, high, size, zero = data[:5]
        count = 5 + (size+1 if command else 0)
        require(zero == 0 and len(data) >= count, 'incomplete oracle packet')
        address = low | high << 32
        if flush:
            for base in range(address//64*64, address+4*(size+1), 64):
                result += [1, flush, 0, 1, 0, base & 0xffffffff, base >> 32]
        result += data[:count]; data = data[count:]
    return result


def scenario(residue, code, flush, idle_rounds=0):
    """Compose two independent byte oracles, batching only internal advances.

    Lower PACKET drains are not simulator events: the live dispatcher keeps
    running until a child blocks. Accumulate every emitted packet, including
    writes preceding the next merge read, in the enclosing serial owner.
    """
    low = syscall.scenario(residue, code)
    base = polling.scenario()[1][0]
    base.update(program=config(23, 1, flush)+words(3),
                terminal=config(27, 1, 1048576, 0)+words(0, 0))
    phase, command, address, partial, response_queue = 1, 0, polling.TOHOST, [], []
    request = packets([0, polling.TOHOST, 0, 1, 0], flush)
    response, parent, life = [], low['states'][0][0], syscall.lifecycle()
    plan, states = [], []

    def snapshot():
        states.append(dict(base,
            poll=config(24, polling.TOHOST, polling.FROMHOST, 1048576)+words(phase, command, len(response_queue), *response_queue),
            read=config(20, 1024, 4, 2, 2)+(words(2, address, 8, len(partial), *partial) if address else words(0, 0, 0, 0)),
            serial=syscall.serial(request, response), syscall=parent, lifecycle=life))

    def step(text): plan.append(text); snapshot()

    def drain():
        while request:
            count = min(3, len(request)); part = request[:count]; del request[:count]
            step('PACKET '+' '.join(map(str, part)))

    snapshot(); drain()
    for _ in range(idle_rounds):
        # Original host-control idle_count=3: three target yields, including
        # the remaining=0 cut, before resuming mailbox polling. No device work.
        response.append(0); step('SEND 0')
        partial = [response.pop()]; step('TICK')
        response.append(0); step('SEND 0'); response.clear()
        phase, address, partial = 4, 0, []
        for remaining in (2, 1, 0):
            base['host'] = config(18, 3)+words(1, remaining, 6)
            step('TICK')
        base['host'] = config(18, 3)+words(0, 0, 7)
        phase, address = 1, polling.TOHOST
        request += packets([0, polling.TOHOST, 0, 1, 0], flush)
        step('TICK'); drain()
    response.append(low['address'] & 0xffffffff); step('SEND '+str(response[-1]))
    partial = [response.pop()]; step('TICK')
    response.append(low['address'] >> 32); step('SEND '+str(response[-1])); response.clear()
    phase, command, address, partial = 3, low['address'], 0, []
    request += packets([1, polling.TOHOST, 0, 1, 0, 0, 0], flush)
    # begin() and automatic advances run in the very same polling dispatch.
    parent = low['states'][1][0]
    index = 1

    def advance():
        nonlocal index, parent, life
        while index < len(low['plan']):
            line = low['plan'][index]
            if line.startswith('PACKET '): index += 1; continue
            require(line == 'ADVANCE', 'oracle tried to advance across unsupplied data')
            before_q, before_r = queues(low['states'][index][1])
            after_q, after_r = queues(low['states'][index+1][1])
            require(after_q[:len(before_q)] == before_q, 'oracle request prefix changed')
            request.extend(packets(after_q[len(before_q):], flush))
            consumed = len(before_r)-len(after_r)
            require(response[:consumed] == before_r[:consumed], 'oracle response order changed')
            del response[:consumed]
            parent, _, life = low['states'][index+1]
            result = low['expected'][index]; index += 1
            if 'BLOCKED' in result or 'COMPLETE' in result: return 'COMPLETE' in result
        raise AssertionError('missing syscall completion')

    complete = advance(); require(not complete, 'no initial read yield'); step('TICK'); drain()
    while not complete:
        while index < len(low['plan']) and low['plan'][index].startswith('PACKET '): index += 1
        line = low['plan'][index]
        if line.startswith('SEND '):
            response.append(int(line.split()[1])); step(line); index += 1
        else:
            complete = advance()
            if complete:
                phase, command, address, response_queue = 6, 0, polling.FROMHOST, [1]
                request += packets([0, polling.FROMHOST, 0, 1, 0], flush)
            step('TICK'); drain()
    # A partially received fromhost value after provider exit must still finish.
    response.append(0); step('SEND 0'); partial = [response.pop()]; step('TICK')
    response.append(0); step('SEND 0')
    final = dict(states[-1], poll=config(24, polling.TOHOST, polling.FROMHOST, 1048576)+words(8, 0, 0),
                 read=config(20, 1024, 4, 2, 2)+words(0, 0, 0, 0),
                 serial=syscall.serial([], []))
    return dict(plan=plan, states=states, final=final, raw=((code << 1)|1)&0xffffffff)


def fault_case(i, idle_rounds=0):
    s = scenario(*SPECS[i], idle_rounds); cut = next(c for c, state in enumerate(s['states']) if state['syscall'][88] == 3)
    bad = bytearray(s['states'][cut]['syscall']); bad[120] ^= 1
    read_size = int.from_bytes(bad[168:176], 'little'); write_start = 176+read_size+8
    bad[write_start+96+16] ^= 1
    address = syscall.scenario(*SPECS[i][:2])['address']
    body_address = (address+7)//8*8; offset = address+16-body_address
    stream, locations = [], []
    for op, line in enumerate(s['plan'][cut:], cut+1):
        if not line.startswith('PACKET '): continue
        values = list(map(int, line.split()[1:])); stream.extend(values)
        locations.extend((op, j) for j in range(len(values)))
        while len(stream) >= 5:
            count = 5+(stream[3]+1 if stream[0] else 0)
            if len(stream) < count: break
            if stream[:3] == [1, body_address & 0xffffffff, body_address >> 32]:
                at = 5+offset//4; op_index, word_index = locations[at]; value = stream[at]
                changed = value ^ (1 << (8*(offset % 4)))
                divergence = f'FIRST_DIVERGENCE operation={op_index} word={word_index} expected={value} actual={changed} acknowledged=0 context_entries=0'
                return cut, bytes(bad), divergence
            del stream[:count]; del locations[:count]
    raise AssertionError('missing independent semantic fault boundary')


def audit(path):
    path = Path(path).resolve(); out = path.parent; r = json.loads(path.read_text())
    idle_rounds = r.get('idle_rounds', 0)
    require(idle_rounds in (0, 2), 'unsupported polling idle schedule')
    case = lambda spec: scenario(*spec, idle_rounds)
    require(r['status'] == 'passed' and not r['level1_verified'] and not r['level2_verified'], 'wrong polling scope')
    require(set(r['artifact_sha256']) == {str(p) for p in out.rglob('*') if p.is_file() and p != path}, 'changed polling artifact membership')
    for p, digest in r['artifact_sha256'].items(): require(file_sha(p) == digest, 'changed polling artifact '+p)
    bindings = {b['path']: b for b in r['source_inputs']}
    require(len(bindings) == len(r['source_inputs']), 'duplicate polling input')
    required = {str(Path(__file__)), str(TESTS/'tsi_polling_syscall_fesvr.cc'), str(STUBS/'fesvr/firesim_tsi.cc'),
                str(STUBS/'fesvr/tsi_polling_syscall.h'), str(STUBS/'fesvr/tsi_syscall_exit.h'),
                str(STUBS/'fesvr/tsi_htif_poll.h'), str(syscall.PROVIDER), str(FESVR/'lib/libfesvr.a'),
                str(STUBS/'fesvr/firesim_tsi.h'), str(STUBS/'fesvr/owned_fesvr_tsi.cc'),
                str(STUBS/'fesvr/tsi_memif_read.h'), str(STUBS/'fesvr/tsi_memif_write.h'),
                str(STUBS/'fesvr/tsi_htif_lifecycle.h'), str(STUBS/'fesvr/htif_lifecycle_provider.inc'),
                str(TESTS/'tsi_terminal_allocations.cc'), str(TESTS/'tsi_polling_prepare_fesvr.cc'),
                str(TESTS/'tsi_polling_prepare_fesvr_tb.sv'), str(TESTS/'tsi_syscall_provider_absent.cc'),
                str(TESTS/'verify_tsi_syscall_exit_vcs.py'), str(TESTS/'verify_tsi_polling_prepare_vcs.py'),
                str(TESTCHIP/'testchip_tsi.cc'), str(TESTCHIP/'testchip_htif.cc'),
                str(CC/'core/checkpoint.h'), str(CC/'core/widget_checkpoint.h')}
    require(required <= bindings.keys(), 'missing actual polling implementation/source binding')
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed polling input snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    overlay = json.loads((out/'libfesvr-checkpoint.json').read_text())
    require(overlay['status'] == 'passed' and overlay['output_sha256'] == file_sha(out/'libfesvr-checkpoint.a'), 'unbound polling archive')
    require(overlay['members']['syscall.o']['installed'] == overlay['members']['syscall.o']['overlay'], 'changed installed syscall')
    for name, digest in overlay['lifecycle_inputs'].items():
        if not name.endswith('_sha256'): require(bindings[name]['sha256'] == digest, 'missing provider source binding')
    if r['recipe_build_identity']:
        identity_path = Path(r['recipe_build_identity']); require(str(identity_path) in bindings, 'missing recipe binding')
        identity = json.loads(identity_path.read_text())
        production = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
        require(identity['htif_lifecycle_provider_linked'] and str(production) in bindings and
                identity['sources_sha256'][str(production)] == file_sha(production) == file_sha(out/'libfesvr-checkpoint.a'),
                'component archive differs from actual linked recipe archive')
        for name, digest in identity['sources_sha256'].items():
            if name in bindings: require(bindings[name]['sha256'] == digest, 'recipe/component source differs')
    expected = {(i, p, b, c) for i, spec in enumerate(SPECS) for p in BACKENDS for b in BACKENDS
                for c in range(len(case(spec)['states']))}
    actual = {(c['scenario'], c['producer'], c['backend'], c['cut']) for c in r['restores']}
    require(len(r['restores']) == len(expected) and actual == expected, 'incomplete fresh polling matrix')
    readbacks = operations = 0
    for i, spec in enumerate(SPECS):
        s = case(spec); folder = out/f'scenario-{i}'
        require((folder/'plan').read_text().splitlines() == s['plan'], 'changed production polling schedule')
        for b in BACKENDS:
            capture = folder/(b+'-capture')
            for c, state in enumerate(s['states']):
                for name in NAMES: require((capture/f'cut-{c}.{name}').read_bytes() == state[name], 'production polling owner mismatch '+name)
            require((capture/'completion.txt').read_text() == f'raw_exit={s["raw"]} stopped=1 response=1 context_entries=source\n', 'source did not finish actual polling/stop')
    for c in r['restores']:
        s = case(SPECS[c['scenario']]); dest = Path(c['destination'])
        for name in NAMES:
            require((dest/('preedge.'+name)).read_bytes() == s['states'][c['cut']][name], 'incomplete zero-service polling readback')
            require((dest/('final.'+name)).read_bytes() == s['final'][name], 'incomplete final polling readback')
        expected_bytes = b''.join(state[name] for state in s['states'][c['cut']+1:] for name in NAMES)
        require((dest/'continuation.bin').read_bytes() == expected_bytes, 'polling continuation/timing differs')
        require((dest/'completion.txt').read_text() == f'raw_exit={s["raw"]} stopped=0 response=1 context_entries=0\n', 'restore reissued stop or lost response')
        readbacks += len(NAMES)*(2+len(s['states'])-c['cut']-1); operations += len(s['plan'])-c['cut']
    commands = {c['log']: c for c in r['commands']}
    require(len(commands) == len(r['commands']), 'duplicate polling process/build command')
    for c in r['commands']:
        require(c['argv'][:2] == ['bash', '-lc'] and c['argv'][2].startswith(ENVIRONMENT), 'unpinned polling tool environment')
        log = Path(c['log']).read_text()
        require(log.rstrip().endswith('exit=0') and not any(s in log for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected')), 'unfinished/failed native polling check')
    used = {str(out/n) for n in ('native-build.log', 'vcs-build.log', 'ordinary-overlay-build.log',
                               'absent-provider-build.log', 'absent-provider.log')}
    if not r['recipe_build_identity']: used.add(str(out/'overlay-build.log'))
    absent_command = commands[str(out/'absent-provider.log')]
    require(absent_command['argv'] == ['bash', '-lc', ENVIRONMENT+shlex.join(map(str,
            (out/'absent-provider', out/'polling.elf', out/'scenario-0/input')))] and
            'ABSENT_PROVIDER_REJECTED startup=0 target_edges=0 context_entries=0' in
            (out/'absent-provider.log').read_text(), 'ordinary archive did not reject opt-in provider request')
    ordinary = json.loads((out/'libfesvr-ordinary.json').read_text())
    require(ordinary['status'] == 'passed' and ordinary['output_sha256'] == file_sha(out/'libfesvr-ordinary.a') and
            ordinary['members']['htif.o']['installed'] == ordinary['members']['htif.o']['overlay'],
            'ordinary archive changed HTIF provider')
    def process(i, backend, mode, name, source=None, producer='native', cut=0):
        folder = out/f'scenario-{i}'; dest = folder/name
        source = source or folder/(producer+'-capture')/f'cut-{cut}'
        metadata = folder/(producer+'-capture')/'startup.metadata'
        values = list(map(str, (mode, out/'polling.elf', folder/('flush.input' if SPECS[i][2] else 'input'),
                               metadata, source, folder/'plan', dest)))
        argv = [out/'native', *values] if backend == 'native' else [out/'simv', '-no_save',
                *['+'+k+'='+v for k, v in zip(('mode', 'elf', 'terminal', 'metadata', 'source', 'plan', 'destination'), values)]]
        log = str(dest.with_suffix('.log')); require(log in commands, 'missing fresh polling command')
        command = commands[log]
        require(command['argv'] == ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))] and command['cwd'] == str(out.relative_to(ROOT)), 'unbound polling process')
        used.add(log); return command
    for i in range(len(SPECS)):
        for b in BACKENDS: process(i, b, 'capture', b+'-capture')
    if idle_rounds:
        for b in BACKENDS:
            for mode in DESCRIPTORS:
                process(0, b, mode, b+'-'+mode)
                dest = out/'scenario-0'/(b+'-'+mode)
                def fdmap(name):
                    rows = [shlex.split(line) for line in (dest/(name+'.fds')).read_text().splitlines()]
                    require(all(len(row) == 8 for row in rows), 'incomplete descriptor identity')
                    result = {int(row[0]): tuple(row[1:]) for row in rows}
                    require(len(result) == len(rows) and {0, 1, 2} <= result.keys(), 'duplicate/missing descriptors')
                    return result
                before, constructed, polling_fds = map(fdmap, ('before', 'constructed', 'polling'))
                def additions(old, new, count):
                    require(all(new.get(fd) == value for fd, value in old.items()) and
                            len(new) == len(old)+count, 'existing descriptors changed or wrong session count')
                    require(sorted(v for fd, v in new.items() if fd not in old) ==
                            sorted([old[0], old[1], old[1]]*(count//3)), 'wrong installed duplicate identities')
                additions(before, constructed, 3)
                count = 3 if mode == 'descriptors-ordinary' else 0
                additions(constructed, polling_fds, count)
                require(all(fdmap('idle-'+str(i)) == polling_fds for i in range(4)) and
                        fdmap('destroyed') == before, 'idle/suspended teardown changed descriptors')
                marker = f'DESCRIPTOR_LIFETIME inherited=3 polling_added={count} idle_cuts=4 teardown_equal=1 ordinary={int(bool(count))} target_edges=0'
                require(marker in dest.with_suffix('.log').read_text(), 'missing actual descriptor lifetime checks')
    for c in r['restores']:
        command = process(c['scenario'], c['backend'], 'restore', Path(c['destination']).name,
                          producer=c['producer'], cut=c['cut'])
        require(all(c[k] == v for k, v in command.items()), 'changed restore command binding')
    chosen = next(i for i, spec in enumerate(SPECS) if spec[0] == 2 and not spec[2])
    candidate_cut = next(c for c, s in enumerate(case(SPECS[chosen])['states']) if s['syscall'][88] == 3)
    candidate = out/f'scenario-{chosen}/native-capture'/f'cut-{candidate_cut}'
    expected_malformed = sum(len(image)+2 for image in case(SPECS[chosen])['states'][candidate_cut].values())
    atomic = []
    for b in BACKENDS:
        process(chosen, b, 'atomic', b+'-atomic', candidate)
        line = (out/f'scenario-{chosen}'/(b+'-atomic')/'atomic.txt').read_text()
        require(re.fullmatch(r'malformed='+str(expected_malformed)+r' membership=56 cross=7 allocation_failures=\d+ unchanged_on_failure=1\n', line), 'missing atomic owner/allocator checks')
        atomic.append(line)
        for guard in GUARDS: process(chosen, b, 'guard-'+guard, b+'-guard-'+guard, candidate)
        for mode in ADMISSION:
            process(0, b, mode, b+'-'+mode)
            marker = ('ENTRY_REJECTED '+mode if mode.startswith('entry-') else
                      'TERMINAL_CORRUPTION rejected=1' if mode=='terminal-corrupt' else
                      'UNSUPPORTED_SELECTOR rejected=1' if mode.endswith('selector') else 'UNSUPPORTED_COMMAND rejected=1')
            require(marker in (out/'scenario-0'/(b+'-'+mode+'.log')).read_text(), 'missing explicit admission rejection')
    require(atomic[0] == atomic[1], 'backend atomic coverage differs')
    require(len(r['invalids']) == 2*3*len(NAMES) and
            {(c['backend'], Path(c['destination']).name) for c in r['invalids']} ==
            {(b, f'{b}-invalid-{n}') for b in BACKENDS for n in range(3*len(NAMES))}, 'incomplete invalid-image processes')
    for n in range(3*len(NAMES)):
        for b in BACKENDS: process(chosen, b, 'invalid', f'{b}-invalid-{n}', out/f'bad-{n}')
    require([(c['scenario'], c['backend']) for c in r['faults']] == [(i, b) for i in (1, 3, 5, 7) for b in BACKENDS], 'incomplete semantic fault matrix')
    for c in r['faults']:
        cut, image, divergence = fault_case(c['scenario'], idle_rounds)
        require(c['cut'] == cut and c['divergence'] == divergence, 'changed semantic fault expectation')
        require((out/f'scenario-{c["scenario"]}/native-capture'/f'cut-{cut}.fault').read_bytes() == image, 'changed actual semantic fault')
        command = process(c['scenario'], c['backend'], 'corrupt', c['backend']+'-corrupt', cut=cut)
        require(all(c[k] == v for k, v in command.items()), 'unbound semantic fault process')
        text = Path(c['log']).read_text()
        require(c['divergence'] in text, 'semantic fault not detected at first unconsumed boundary')
    require(set(commands) == used, 'extra or missing polling native command')
    build = shlex.split(commands[str(out/'vcs-build.log')]['argv'][2][len(ENVIRONMENT):])
    require(build[0] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs' and '-full64' in build and
            build[build.index('-cc')+1] == '/usr/bin/gcc-13' and build[build.index('-cpp')+1] == '/usr/bin/g++-13', 'wrong VCS/compiler')
    return dict(status='passed', scenarios=len(SPECS), cuts=sum(len(case(s)['states']) for s in SPECS),
                fresh_restores=len(expected), owner_readbacks=readbacks, host_operations=operations,
                invalid_processes=len(r['invalids']), semantic_first_divergences=len(r['faults']),
                late_guards=2*len(GUARDS), admission_rejections=2*len(ADMISSION)+1,
                idle_rounds=idle_rounds, descriptor_processes=2*len(DESCRIPTORS) if idle_rounds else 0,
                atomic_per_backend=atomic[0].strip(), level1_verified=False, level2_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path); p.add_argument('--audit', type=Path)
    p.add_argument('--recipe-build-identity', type=Path); a = p.parse_args()
    if a.audit: print(json.dumps(audit(a.audit), indent=2)); return
    require(a.out and a.out.resolve().is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need runs output')
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ.get('CXX') == '/usr/bin/g++-13', 'source vcs-env LAST')
    a.out.resolve().mkdir(parents=True, exist_ok=True); out = Path(tempfile.mkdtemp(prefix='invocation-', dir=a.out.resolve()))
    idle_rounds = 2
    case = lambda spec: scenario(*spec, idle_rounds)
    source = TESTS/'tsi_polling_syscall_fesvr.cc'; sv = TESTS/'tsi_polling_prepare_fesvr_tb.sv'
    sources = [source, STUBS/'fesvr/firesim_tsi.cc', STUBS/'fesvr/owned_fesvr_tsi.cc',
               TESTCHIP/'testchip_tsi.cc', TESTCHIP/'testchip_htif.cc', TESTS/'tsi_terminal_allocations.cc']
    absent = TESTS/'tsi_syscall_provider_absent.cc'
    inputs = [*sources, absent, sv, Path(__file__), *sorted(TESTS.glob('verify_tsi*py')), TESTS/'tsi_polling_prepare_fesvr.cc',
              syscall.PROVIDER, syscall.PROVIDER.with_suffix('.h'), STUBS/'fesvr/htif_lifecycle_provider.inc', *overlay_inputs(),
              *sorted((STUBS/'fesvr').glob('*.h')), *sorted(TESTCHIP.glob('*.h')),
              *sorted((FESVR/'include/fesvr').glob('*.h')), *sorted((FESVR/'include/riscv').glob('*.h')),
              FESVR/'lib/libfesvr.a', CC/'core/checkpoint.h', CC/'core/widget_checkpoint.h',
              ROOT/'env.sh', ROOT/'sims/firesim/env.sh', ROOT/'automations/checkpoint_loop/vcs-env.sh']
    production = None
    if a.recipe_build_identity:
        identity = json.loads(a.recipe_build_identity.read_text()); require(identity['htif_lifecycle_provider_linked'], 'missing actual recipe provider')
        for name, digest in identity['sources_sha256'].items(): require(file_sha(name) == digest, 'changed recipe input '+name)
        production = Path(identity['native_binary']).parent/'checkpoint-fesvr/lifecycle/libfesvr-checkpoint.a'
        inputs += [a.recipe_build_identity.resolve(), production, production.with_suffix('.json')]
    (out/'sources').mkdir(); bindings = []
    for path in dict.fromkeys(inputs):
        digest = file_sha(path); snapshot = out/'sources'/digest
        if not snapshot.exists(): shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    commands = []
    def execute(argv, log):
        command = ['bash', '-lc', ENVIRONMENT+shlex.join(map(str, argv))]; run(command, log, cwd=out)
        c = dict(argv=command, cwd=str(out.relative_to(ROOT)), log=str(log)); commands.append(c); return c
    library = out/'libfesvr-checkpoint.a'
    if production:
        shutil.copyfile(production, library); shutil.copyfile(production.with_suffix('.json'), library.with_suffix('.json'))
    else:
        execute(['python3', BUILDER, '--library', FESVR/'lib/libfesvr.a', '--include', FESVR/'include',
                 '--out', library, '--cxx', os.environ['CXX'], '--htif-source', syscall.PROVIDER], out/'overlay-build.log')
    include = f'-std=c++17 -I{CC} -I{STUBS} -I{TESTCHIP} -I{FESVR/"include"}'
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
             *sources, library, '-lpthread', '-o', out/'native'], out/'native-build.log')
    execute([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps', '-top', 'tsi_polling_prepare_fesvr_tb',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-Mdir='+str(out/'csrc'), '-CFLAGS', include+' -DTSI_POLLING_SYSCALL_DPI',
             '-LDFLAGS', '-Wl,--whole-archive '+str(library)+' -Wl,--no-whole-archive -lpthread', '-o', out/'simv', sv, *sources], out/'vcs-build.log')
    ordinary = out/'libfesvr-ordinary.a'
    execute(['python3', BUILDER, '--library', FESVR/'lib/libfesvr.a', '--include', FESVR/'include',
             '--out', ordinary, '--cxx', os.environ['CXX']], out/'ordinary-overlay-build.log')
    execute([os.environ['CXX'], *shlex.split(include), '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
             absent, *sources[1:-1], ordinary, '-lpthread', '-o', out/'absent-provider'], out/'absent-provider-build.log')
    (out/'polling.elf').write_bytes(polling.polling_elf())
    def invoke(i, backend, mode, name, producer='native', cut=0, source=None):
        folder = out/f'scenario-{i}'; dest = folder/name
        values = list(map(str, (mode, out/'polling.elf', folder/('flush.input' if SPECS[i][2] else 'input'),
                               folder/(producer+'-capture')/'startup.metadata',
                               source or folder/(producer+'-capture')/f'cut-{cut}', folder/'plan', dest)))
        argv = [out/'native', *values] if backend == 'native' else [out/'simv', '-no_save',
                *['+'+k+'='+v for k, v in zip(('mode', 'elf', 'terminal', 'metadata', 'source', 'plan', 'destination'), values)]]
        return dict(execute(argv, dest.with_suffix('.log')), scenario=i, backend=backend, mode=mode,
                    destination=str(dest), producer=producer, cut=cut)
    for i, spec in enumerate(SPECS):
        folder = out/f'scenario-{i}'; folder.mkdir(); s = case(spec)
        (folder/'plan').write_text('\n'.join(s['plan'])+'\n')
        (folder/('flush.input' if spec[2] else 'input')).write_bytes(b'')
        for b in BACKENDS: invoke(i, b, 'capture', b+'-capture')
    for b in BACKENDS:
        for mode in ADMISSION: invoke(0, b, mode, b+'-'+mode)
        for mode in DESCRIPTORS: invoke(0, b, mode, b+'-'+mode)
    execute([out/'absent-provider', out/'polling.elf', out/'scenario-0/input'], out/'absent-provider.log')
    jobs = [(i, b, 'restore', f'{p}-{b}-cut-{c}', p, c) for i, spec in enumerate(SPECS)
            for p in BACKENDS for b in BACKENDS for c in range(len(case(spec)['states']))]
    with ThreadPoolExecutor(max_workers=8) as pool: restores = list(pool.map(lambda j: invoke(*j), jobs))
    chosen = 1; s = case(SPECS[chosen]); candidate_cut = next(c for c, state in enumerate(s['states']) if state['syscall'][88] == 3)
    candidate = out/f'scenario-{chosen}/native-capture'/f'cut-{candidate_cut}'
    for b in BACKENDS:
        invoke(chosen, b, 'atomic', b+'-atomic', source=candidate)
        for guard in GUARDS: invoke(chosen, b, 'guard-'+guard, b+'-guard-'+guard, source=candidate)
    invalids = []
    for n in range(3*len(NAMES)):
        prefix = out/f'bad-{n}'; state = dict(s['states'][candidate_cut]); name = NAMES[n % len(NAMES)]; bad = bytearray(state[name])
        if n < len(NAMES): bad = bad[:-1]
        elif n < 2*len(NAMES): bad[16] ^= 1
        else: bad += b'\0'
        state[name] = bytes(bad)
        for name in NAMES: Path(str(prefix)+'.'+name).write_bytes(state[name])
        for b in BACKENDS: invalids.append(invoke(chosen, b, 'invalid', f'{b}-invalid-{n}', source=prefix))
    faults = []
    for i in (1, 3, 5, 7):
        cut, bad, divergence = fault_case(i, idle_rounds)
        prefix = out/f'scenario-{i}/native-capture'/f'cut-{cut}'
        Path(str(prefix)+'.fault').write_bytes(bad)
        for b in BACKENDS: faults.append(dict(invoke(i, b, 'corrupt', b+'-corrupt', cut=cut), divergence=divergence))
    for b in bindings: require(file_sha(b['path']) == b['sha256'], 'polling source changed during execution')
    report = dict(status='passed', scope='restricted syscall polling components; complete CPU Level 1 disabled',
                  idle_rounds=idle_rounds, commands=commands, source_inputs=bindings, restores=restores, invalids=invalids, faults=faults,
                  recipe_build_identity=str(a.recipe_build_identity.resolve()) if a.recipe_build_identity else None,
                  level1_verified=False, level2_verified=False,
                  artifact_sha256={str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    path = out/'summary.json'; path.write_text(json.dumps(report, indent=2)+'\n')
    try: result = audit(path)
    except Exception:
        report['status'] = 'failed'; path.write_text(json.dumps(report, indent=2)+'\n'); raise
    print(json.dumps(dict(summary=str(path), **result), indent=2))


if __name__ == '__main__': main()
