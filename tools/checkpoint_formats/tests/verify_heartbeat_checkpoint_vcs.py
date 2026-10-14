"""Heartbeat host owner: sanitized native and fresh VCS DPI processes.

An independent oracle checks complete state, polling MMIO, sticky termination
and full buffered CSV. Fixture labels and deterministic wall time do not grant
Rocket CPU checkpoint or ordinary CPU RTL replay acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_blockdev_checkpoint_vcs import words
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

TESTS = Path(__file__).resolve().parent
CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
OPERATIONS = 15
EPOCH = 1700000000
CYCLES = [0, 0, 0x100000009, 0x100000009, 0x100000009,
          0x100000011, 0x100000011, 0x100000011, 0x100000011,
          0x100000011, 0x100000011, 0x100000021, 0x100000021,
          0x100000021, 0x100000031]


def configuration(header, scenario):
    matches = re.findall(r'registry.add_widget\(new clockmodule_t\(\s*simif,\s*CLOCKBRIDGEMODULE_struct\{(.*?)\},\s*(\d+),\s*args\s*\)\);', header, re.S)
    require(len(matches) == 1, 'expected one actual Rocket clock constructor')
    fields, index = matches[0]
    pairs = re.findall(r'\.(\w+)\s*=\s*(\d+)\s*,', fields)
    require([p[0] for p in pairs] == 'hCycle_0 hCycle_1 hCycle_latch tCycle_0 tCycle_1 tCycle_latch'.split(),
            'missing/extra/reordered clock fields')
    addresses = [int(p[1]) for p in pairs]
    require(int(index) == 0 and addresses == list(range(1088, 1112, 4)), 'changed actual Rocket clock mapping')
    binding = words(0x3154504B43474457, 1, 2, 6, *addresses, 0)
    return words(0x3154504B43474457, 1, 11, 3, 0 if scenario == 2 else 2, int(scenario == 1), len(binding)) + binding


def oracle(config, scenario):
    """Polling algorithm and independent complete payload representation."""
    interval, ignored = (0 if scenario == 2 else 2), scenario == 1
    trace, snapshots, samples = [], [], []
    trips = last = timed_out = 0
    def state():
        return config + words(EPOCH, timed_out, trips, last, len(samples)) + b''.join(
            words(c, elapsed & ((1 << 64)-1)) for c, elapsed in samples)
    for op, cycle in enumerate(CYCLES):
        snapshots.append(state())
        trace.append(f'OP {op} C {100+7*op}')
        if trips == interval:
            trips = 0
            trace += ['W 1108 1', f'R 1100 {cycle & 0xffffffff}', f'R 1104 {cycle >> 32}']
            timed_out = int(bool(timed_out or (not ignored and cycle == last)))
            samples.append((cycle, -2 if op == 7 else 4*op))
            last = cycle
        else:
            trips += 1
        trace.append(f'RESULT {timed_out} {timed_out}')
    snapshots.append(state())
    csv = 'Target Cycle (fastest), Seconds Since Start\n' + ''.join(f'{c}, {elapsed}\n' for c, elapsed in samples)
    return trace, snapshots, csv.encode()


def audit_case(case, config, scenario):
    trace, snapshots, csv = oracle(config, scenario)
    require((case / 'reference.trace').read_text().splitlines() == trace, 'heartbeat oracle MMIO/termination mismatch')
    for cut, snapshot in enumerate(snapshots):
        for p in [case / f'cut-{cut}.owner', case / f'restore-{cut}.initial.owner']:
            require(p.read_bytes() == snapshot, 'incomplete heartbeat zero-edge owner readback ' + str(p))
        require((case / f'restore-{cut}.final.owner').read_bytes() == snapshots[-1], 'incomplete heartbeat final state')
        suffix = trace[trace.index(f'OP {cut} C {100+7*cut}'):] if cut < OPERATIONS else []
        require((case / f'restore-{cut}.trace').read_text().splitlines() == suffix, 'changed heartbeat polling/termination boundary')
    require((case / 'heartbeat.csv').read_bytes() == csv, 'full heartbeat output including captured prefix differs')
    return dict(cuts=len(snapshots), polling_interval=0 if scenario == 2 else 2,
                ignore_heartbeat=scenario == 1, captured_samples=15 if scenario == 2 else 5,
                fixture_cycles=[100+7*i for i in range(15)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rocket-header', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ['VCS_HOME'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    require(os.environ['CXX'] == '/usr/bin/g++-13', 'keep GCC/G++ 13')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='native-', dir=args.out.resolve()))
    header = args.rocket_header.resolve()
    configs = [configuration(header.read_text(), i) for i in range(3)]
    sources = [TESTS / 'heartbeat_checkpoint.cc', CC / 'core/widget.cc',
               CC / 'bridges/clock.cc', CC / 'bridges/heartbeat.cc']
    native, simv = out / 'heartbeat-native', out / 'heartbeat-simv'
    commands = []
    def execute(argv, log, expected=0):
        text = run(argv, log, expected=expected)
        commands.append(dict(cwd='.', argv=list(map(str, argv)), log=str(log), expected_exit=expected))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return text
    execute([os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Werror',
             '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', f'-I{CC}',
             *sources, '-Wl,--wrap=time', '-o', native], out / 'native-build.log')
    execute([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'heartbeat_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             f'-Mdir={out / "csrc"}', '-CFLAGS', f'-std=c++17 -DHEARTBEAT_CHECKPOINT_DPI -I{CC}',
             '-LDFLAGS', '-Wl,--wrap=time', '-o', simv, TESTS / 'heartbeat_checkpoint_tb.sv', *sources],
            out / 'vcs-build.log')
    results = []
    for backend in ['native-sanitized', 'vcs-dpi']:
        backend_root = out / backend; backend_root.mkdir()
        def invoke(mode, cut, scenario, directory, expected=0):
            argv = [native, mode, directory, cut, scenario] if backend == 'native-sanitized' else [
                simv, '-no_save', f'+outdir={directory}', f'+restore={int(mode == "restore")}',
                f'+cut={cut}', f'+mode={scenario}', *(['+negative'] if mode == 'negative' else [])]
            text = execute(argv, directory / f'{mode}-{cut}.log', expected)
            if backend == 'vcs-dpi' and expected == 0 and mode != 'negative':
                require('HEARTBEAT_READBACK edges=0' in text and 'PASS: fresh heartbeat component continuation' in text,
                        'missing complete pre-edge VCS heartbeat readback')
            return text
        scenarios = []
        for scenario, config in enumerate(configs):
            case = backend_root / f'scenario-{scenario}'; case.mkdir()
            invoke('reference', 0, scenario, case)
            csv = oracle(config, scenario)[2]
            for cut in range(OPERATIONS+1):
                invoke('restore', cut, scenario, case)
                require((case / 'heartbeat.csv').read_bytes() == csv, 'fresh output prefix lost')
            scenarios.append(audit_case(case, config, scenario))
        positive = backend_root / 'scenario-0'
        negative = invoke('negative', 0, 0, positive)
        count = re.search(r'PASS: heartbeat atomic payload/configuration/suspension checks (\d+)', negative)
        require(count is not None, 'missing heartbeat rejection checks')
        fault = backend_root / 'actual-poll-counter-fault'; fault.mkdir()
        bad = bytearray(oracle(configs[0], 0)[1][1]); bad[160] = 2
        (fault / 'cut-1.owner').write_bytes(bad)
        shutil.copyfile(positive / 'reference.trace', fault / 'reference.trace')
        text = invoke('restore', 1, 0, fault, expected=1)
        require('FIRST_MISMATCH fixture_cycle=107 signal=heartbeat_poll op=1' in text,
                'actual polling corruption did not diverge at its first changed boundary')
        lines = (fault / 'restore-1.trace').read_text().splitlines()
        require(lines == ['OP 1 C 107', 'W 1108 1'], 'acknowledged divergent poll/cycle/termination')
        # Negative cases must not overwrite any positive traces/readbacks.
        for i, config in enumerate(configs):
            audit_case(backend_root / f'scenario-{i}', config, i)
        results.append(dict(backend=backend, fresh_continuations=48, scenarios=scenarios,
                            negative_assertions=int(count[1]), first_actual_corruption_fixture_cycle=107))
    inputs = [header, *sources, CC / 'core/widget_checkpoint.h', CC / 'bridges/clock.h',
              CC / 'bridges/heartbeat.h', TESTS / 'heartbeat_checkpoint_tb.sv', Path(__file__)]
    summary = dict(status='passed', artifact_root=str(out),
                   scope='buffered heartbeat host component; CPU checkpoint acceptance pending',
                   fresh_continuations=96, backends=results, deterministic_fixture_wall_time=True,
                   level1_verified=False, level2_verified=False,
                   inputs_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (args.out.resolve() / 'latest.json').write_text(json.dumps(dict(summary=str(out / 'summary.json')), indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
