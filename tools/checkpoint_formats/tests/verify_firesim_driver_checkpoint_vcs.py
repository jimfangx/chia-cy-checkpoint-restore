"""Production FireSim loop ownership, independent oracle and fresh VCS restores.

These are completed host-operation fixtures, not coherent CPU checkpoint cuts.
Every invocation retains original native bytes; rechecks allocate new paths.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

TESTS = Path(__file__).resolve().parent
CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
FIRECHIP = ROOT / 'generators/firechip/chip/src/main/cc'
FATAL = ('expired', 'unsealed', 'consumed', 'stale', 'legacy', 'thread')
ENVIRONMENT = ('source ' + shlex.quote(str(ROOT / 'env.sh')) + ' && source ' +
               shlex.quote(str(ROOT / 'sims/firesim/env.sh')) + ' && source ' +
               shlex.quote(str(ROOT / 'automations/checkpoint_loop/vcs-env.sh')) + ' && ')


def words(*values):
    return struct.pack('<' + 'Q' * len(values), *values)


def text(value):
    value = value.encode()
    return words(len(value)) + value


def config(kind, *values):
    return words(0x3154504b43474457, 1, kind, len(values), *values)


def oracle(mode):
    """Expand the original nested loop's calls, including each early break.

    Each call has a completed-operation cursor; no implementation is invoked.
    Fixture clock labels describe host calls, never actual Rocket cycles.
    """
    clock = config(2, 16, 20, 24, 28, 32, 36) + words(0)
    peek = config(5, 100, 104, 108) + words(0, 0, 0)
    driver = config(13, 0, 0) + text('widget/1') + text('firesim.widget.peek-poke.v1') + words(5)
    for i in range(2, 7):
        driver += text('widget/' + str(i)) + text('fixture.bridge.v1' if i < 6 else 'firesim.widget.heartbeat.v1')
    driver += words(1)
    trace, states = [], []
    polls, issued, trips, ticks = 0, 0, 0, [0] * 4
    code = (0, 7, -9, -(1 << 31))[mode] if mode < 4 else 0

    def call(phase, index=0, output=(), stopped=0, status=0):
        n = len(states) + 1
        trace.extend([f'OP {n} C {100+n}', *output])
        scheduler = words(0x3154504b43484353, 1, 1, 0 if mode == 5 else 100,
                          (1 << 32)-1, 100 if issued else 0, 0)
        loop = words(0x3154504b434c5242, 1, 5, phase, index, stopped, status & 0xffffffff)
        heartbeat = config(11, 1000, 0, len(clock)) + clock + words(1000, 0, trips, 0, 0)
        mmio = words(mode, polls, issued, *ticks)
        states.append([driver, scheduler, loop, clock, peek,
                       *[words(i) for i in range(4)], heartbeat, mmio])

    if mode == 5:
        call(7)
    else:
        call(1)  # outer horizon query
        call(2)  # scheduled callbacks
        issued = 1
        call(3, output=['W 100 100'])
        for round_index in range(2):
            polls += 1
            call(4, output=['R 104 0'])
            for i in range(5):
                if i < 4:
                    ticks[i] += 1
                    call(5, i, [f'W {200+8*i} 1'])
                else:
                    trips += 1
                    call(5, i)
                terminal = mode < 4 and i == mode and round_index == 1
                lines = [f'R {200+8*i} {int(terminal)}'] if i < 4 else []
                call(6 if terminal else 4 if i < 4 else 3,
                     i if terminal else i+1 if i < 4 else 0, lines)
                if terminal:
                    call(7, output=[f'R {204+8*i} {code & 0xffffffff}'], stopped=1, status=code)
                    break
            if mode < 4 and round_index == 1:
                break
        if mode == 4:
            polls += 1
            call(0, output=['R 104 1'])
            call(7)
    trace.extend(['FINAL', f'RESULT {code} TIMEOUT {int(mode >= 4)}'])
    return trace, states


def audit_case(case, mode):
    expected, states = oracle(mode)
    require((case / 'reference/trace').read_text().splitlines() == expected,
            'production driver calls differ from independent original nested loop')
    comparisons = continued = 0
    for cut, state in enumerate(states, 1):
        restored = case / f'restore-{cut}'
        for owner, payload in enumerate(state):
            require((case / f'reference/cut-{cut}.{owner}.owner').read_bytes() == payload and
                    (restored / f'initial.{owner}.owner').read_bytes() == payload,
                    'complete pre-edge owner mismatch: mode/cut/owner ' + str((mode, cut, owner)))
            comparisons += 1
        start = expected.index(f'OP {cut+1} C {101+cut}') if cut < len(states) else expected.index('FINAL')
        wanted = expected[start:]
        require((restored / 'trace').read_text().splitlines() == wanted, 'changed continued boundary/timing/status')
        continued += len(wanted)
    return dict(mode=mode, cuts=len(states), complete_owner_readbacks=comparisons,
                continued_boundaries=continued, fixture_cycles=[101, 100+len(states)])


def audit(path):
    path = path.resolve()
    report = json.loads(path.read_text())
    require(report['status'] == 'passed' and not report['level1_verified'] and not report['level2_verified'],
            'component cannot certify CPU acceptance')
    catalog = report['artifact_sha256']
    require(set(catalog) == {str(p) for p in path.parent.rglob('*') if p.is_file() and p != path},
            'changed native evidence membership')
    for name, digest in catalog.items():
        require(file_sha(name) == digest, 'changed original native evidence: ' + name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed original source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    for backend in report['backends']:
        require(len(backend['cases']) == 6, 'missing early termination/horizon cases')
        for case in backend['cases']:
            require(case == audit_case(path.parent / backend['backend'] / str(case['mode']), case['mode']),
                    'changed native comparison counts')
        if report.get('prepared_driver', False):
            log = (path.parent / backend['backend'] / 'publication-negative.log').read_text()
            match = re.search(r'DRIVER_PUBLICATION_NEGATIVE rejections=(\d+) prepare_failures=(\d+) seal_failures=(\d+) unchanged=1 mmio=0', log)
            require(match is not None, 'missing prepared driver negative checks')
            rejected, prepare, seal = map(int, match.groups())
            require(rejected == 2*len(oracle(0)[1][0][0])+85 and prepare > 0 and seal > 0,
                    'prepared driver negative/allocation coverage changed')
            require(backend['publication'] == dict(rejections=rejected, prepare_failures=prepare, seal_failures=seal,
                                                  fatal_checks=len(FATAL)), 'changed publication counts')
            if backend['backend'] == 'vcs-dpi':
                require('DRIVER_PUBLICATION_ZERO_TIME_PASS' in log, 'publication negatives advanced VCS time')
            for mode in FATAL:
                log = (path.parent / backend['backend'] / ('publication-fatal-'+mode+'.log')).read_text()
                require(f'DRIVER_PUBLICATION_FATAL mode={mode} unchanged=1 mmio=0' in log and
                        'exit=86' in log and 'PASS:' not in log and 'ZERO_TIME_PASS' not in log,
                        'invalid publication acknowledged or changed owner state')
            log = (path.parent / backend['backend'] / 'publication-returned.log').read_text()
            require('DRIVER_PUBLICATION_UNEXPECTED_RETURN mode=returned' in log and
                    log.rstrip().endswith('exit=88') and 'DRIVER_PUBLICATION_FATAL mode=' not in log,
                    'unexpected return accepted by fatal publication test harness')
    commands = report['commands']
    require(len({c['pid'] for c in commands}) == len(commands), 'reused native process')
    for c in commands:
        log = Path(c['log']).read_text()
        require(log.rstrip().endswith('exit='+str(c['expected_exit'])) and
                c['argv'][:2] == ['bash', '-lc'] and c['argv'][-1].startswith(ENVIRONMENT),
                'unbound native command/environment')
    return dict(status='passed', summary=str(path),
                fresh_continuations=sum(c['cuts'] for b in report['backends'] for c in b['cases']),
                native_processes=len(commands), prepared_driver=report.get('prepared_driver', False),
                publication=[b['publication'] for b in report['backends']] if report.get('prepared_driver', False) else [],
                level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--prepared', action='store_true', help='use prepared publication for the concrete driver')
    args = parser.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit), indent=2)); return
    require(args.out is not None, 'out required')
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CXX') == _toolchain.CXX, 'source vcs-env.sh LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    sources = [TESTS / 'firesim_driver_checkpoint.cc', TESTS / 'firesim_driver_heartbeat_clock.cc', *[CC / p for p in (
        'core/bridge_run_loop.cc', 'core/simulation.cc', 'core/systematic_scheduler.cc',
        'core/widget_registry.cc', 'core/widget.cc', 'core/bridge_driver.cc', 'core/stream_engine.cc',
        'core/address_map.cc', 'bridges/clock.cc', 'bridges/master.cc', 'bridges/loadmem.cc',
        'bridges/peek_poke.cc', 'bridges/fased_memory_timing_model.cc')]]
    inputs = [*sources, CC / 'bridges/heartbeat.cc', FIRECHIP / 'firesim/firesim_top.cc', Path(__file__),
              TESTS / 'firesim_driver_checkpoint_tb.sv', *sorted((CC / 'core').glob('*.h')),
              *sorted((CC / 'bridges').glob('*.h'))]
    snapshots = out / 'source-snapshots'; snapshots.mkdir()
    bindings = []
    for p in inputs:
        digest = file_sha(p); snapshot = snapshots / digest
        if not snapshot.exists(): shutil.copyfile(p, snapshot)
        bindings.append(dict(path=str(p), snapshot=str(snapshot), sha256=digest))
    commands = []
    def execute(argv, log, expected=0):
        command = ['bash', '-lc', ENVIRONMENT + shlex.join([str(a) for a in argv])]
        result = run(command, log, cwd=out, expected=expected)
        pid = int(re.search(r'fresh_process_pid=(\d+)', result)[1])
        commands.append(dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log), pid=pid, expected_exit=expected))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return result
    include = f'-std=c++17 -I{CC} -I{FIRECHIP}'
    if args.prepared:
        include += ' -DFIRESIM_DRIVER_PREPARED_PUBLICATION'
    native, simv = out / 'driver-native', out / 'driver-simv'
    execute([os.environ['CXX'], *shlex.split(include), '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
             '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', *sources,
             '-lgmp', '-o', native], out / 'native-build.log')
    execute([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'firesim_driver_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             f'-Mdir={out / "csrc"}', '-CFLAGS', include+' -DFIRESIM_DRIVER_CHECKPOINT_DPI',
             '-LDFLAGS', '-Wl,--no-as-needed -lgmp', '-o', simv, TESTS / 'firesim_driver_checkpoint_tb.sv',
             *sources], out / 'vcs-build.log')
    results = []
    for backend in ('native-sanitized', 'vcs-dpi'):
        base = out / backend; base.mkdir()
        def invoke(source, destination, restore, cut, mode, expected=0):
            argv = [native, source, destination, int(restore), cut, mode] if backend == 'native-sanitized' else [
                simv, '-no_save', f'+source={source}', f'+outdir={destination}', f'+restore={int(restore)}',
                f'+cut={cut}', f'+mode={mode}']
            return execute(argv, destination / 'run.log', expected)
        cases = []
        for mode in range(6):
            case = base / str(mode); case.mkdir()
            reference = case / 'reference'; reference.mkdir()
            invoke(reference, reference, False, 0, mode)
            for cut in range(1, len(oracle(mode)[1])+1):
                destination = case / f'restore-{cut}'; destination.mkdir()
                log = invoke(reference, destination, True, cut, mode)
                require('FIRESIM_DRIVER_READBACK edges=0 mmio_calls=0' in log and
                        'PASS: fresh FireSim driver continuation' in log, 'missing complete readback/continuation')
            cases.append(audit_case(case, mode))
        log = execute([native, 'negative'] if backend == 'native-sanitized' else [simv, '-no_save', '+negative'],
                      base / 'negative.log')
        rejections = int(re.search(r'PASS: FireSim driver atomic/configuration/lifecycle rejections (\d+)', log)[1])
        reference = base / '0/reference'
        invalid = 0
        for name, owner, payload in [
            ('missing-owner', 10, None), ('truncated-loop', 2, b''),
            ('trailing-loop', 2, oracle(0)[1][4][2]+b'\0'),
            ('incompatible-count', 2, words(0x3154504b434c5242,1,4,5,0,0,0)),
            ('unknown-loop-version', 2, words(0x3154504b434c5242,2,5,5,0,0,0)),
            ('invalid-phase', 2, words(0x3154504b434c5242,1,5,8,0,0,0)),
            ('incompatible-driver', 0, b'\0'*len(oracle(0)[1][4][0])),
            ('invalid-status', 2, words(0x3154504b434c5242,1,5,5,0,0,1)),
        ]:
            case = base / name; case.mkdir()
            for i, data in enumerate(oracle(0)[1][4]):
                if i != owner or payload is not None:
                    (case / f'cut-5.{i}.owner').write_bytes(payload if i==owner else data)
            log = invoke(case, case, True, 5, 0, 1)
            require('REJECTED_BEFORE_FIRST_EDGE' in log and not (case / 'trace').exists() and
                    not list(case.glob('initial.*')), 'invalid owner partially restored/published')
            invalid += 1
        # A structurally valid actual cursor change must fail at the first next
        # MMIO read, before acknowledging the divergent operation.
        case = base / 'actual-cursor-corruption'; case.mkdir()
        for i, data in enumerate(oracle(0)[1][4]):
            if i == 2:
                data = bytearray(data); struct.pack_into('<Q', data, 32, 1)
            (case / f'cut-5.{i}.owner').write_bytes(data)
        shutil.copyfile(reference / 'trace', case / 'trace-reference')
        shutil.copyfile(reference / 'trace', case / 'trace')
        # Loader reads reference trace before opening its separate output sink.
        destination = case / 'restore'; destination.mkdir()
        log = invoke(case, destination, True, 5, 0, 1)
        require('FIRST_MISMATCH fixture_cycle=106 operation=6 acknowledged=5 expected=R 200 0 actual=R 208 0' in log,
                'actual cursor corruption missed its first divergent boundary')
        require((destination / 'trace').read_text().splitlines() == ['OP 6 C 106'], 'divergent MMIO was acknowledged')
        results.append(dict(backend=backend, cases=cases, atomic_rejections=rejections,
                            invalid_fresh_processes=invalid, first_divergence_fixture_cycle=106))
        if args.prepared:
            log = execute([native, 'publication-negative'] if backend == 'native-sanitized' else
                          [simv, '-no_save', '+publication-negative'], base / 'publication-negative.log')
            match = re.search(r'DRIVER_PUBLICATION_NEGATIVE rejections=(\d+) prepare_failures=(\d+) seal_failures=(\d+)', log)
            require(match is not None, 'missing driver publication matrix')
            results[-1]['publication'] = dict(zip(('rejections', 'prepare_failures', 'seal_failures'), map(int, match.groups())))
            results[-1]['publication']['fatal_checks'] = len(FATAL)
            for mode in FATAL:
                execute([native, 'publication-fatal', mode] if backend == 'native-sanitized' else
                        [simv, '-no_save', '+publication-fatal='+mode],
                        base / ('publication-fatal-'+mode+'.log'), 86)
            # A valid publication deliberately returns here: prove that the
            # fatal-test harness cannot convert that return into a passing trap.
            execute([native, 'publication-fatal', 'returned'] if backend == 'native-sanitized' else
                    [simv, '-no_save', '+publication-fatal=returned'], base / 'publication-returned.log', 88)
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'], 'source changed during execution')
    report = dict(status='passed', scope='production FireSim host driver component; CPU/harness/TSI ownership pending',
                  backends=results, commands=commands, source_inputs=bindings,
                  prepared_driver=args.prepared, level1_verified=False, level2_verified=False)
    report['artifact_sha256'] = {str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    summary = out / 'summary.json'; summary.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(audit(summary), indent=2))


if __name__ == '__main__':
    main()
