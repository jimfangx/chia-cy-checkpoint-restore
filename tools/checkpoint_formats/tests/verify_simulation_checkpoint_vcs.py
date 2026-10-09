"""Actual simulation_t base lifecycle continuation; no whole FireSim restart."""
import argparse
import json
import os
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
TESTS = Path(__file__).resolve().parent


def words(*values):
    return struct.pack('<' + 'Q' * len(values), *values)


def text(value):
    value = value.encode()
    return words(len(value)) + value


def oracle(cut):
    config = words(0x3154504B43474457, 1, 8, 5, 0, 0, 0, 0, 1) + text('') + text('') + words(3)
    for i, schema in enumerate(('firesim.widget.master.v1', 'firesim.widget.clock.v1', 'fixture.bridge.v1')):
        config += text(f'widget/{i}') + text(schema)
    return config + words(1, int(cut == 4), 1000100, 23)


def trace(scenario, cut=0):
    result = [] if cut else ['R 0 1', f'R 4 {0x46697265}', 'W 200 1', 'W 24 1', 'R 16 23', 'R 20 0']
    for i in range(cut, 4):
        result += [f'W 100 {i}', f'R 104 {i*9}']
    return result + [f'W 108 {7 if scenario == 1 else 0}', 'W 36 1', 'R 28 42', 'R 32 0',
                     'W 24 1', 'R 16 23', 'R 20 0', 'W 204 1']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    require(os.environ['VCS_HOME'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    require(os.environ['CXX'] == '/usr/bin/g++-13', 'keep system GCC/G++ 13')
    sources = [TESTS / 'simulation_checkpoint.cc', *[CC / path for path in (
        'core/simulation.cc', 'core/widget_registry.cc', 'core/widget.cc',
        'core/stream_engine.cc', 'core/bridge_driver.cc', 'bridges/master.cc',
        'bridges/clock.cc', 'bridges/loadmem.cc')]]
    native, simv = out / 'simulation-native', out / 'simulation-simv'
    run([os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
         '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', f'-I{CC}',
         *sources, '-lgmp', '-o', native], out / 'native-build.log')
    run([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
         '-top', 'simulation_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
         f'-Mdir={out / "simulation-csrc"}', '-CFLAGS', f'-std=c++17 -DSIMULATION_CHECKPOINT_DPI -I{CC}',
         '-LDFLAGS', '-Wl,--no-as-needed -lgmp', '-o', simv, TESTS / 'simulation_checkpoint_tb.sv', *sources], out / 'vcs-build.log')
    comparisons, matched_calls, rejections = 0, 0, {}
    for backend in ('native-sanitized', 'vcs-dpi'):
        def command(source, destination, restore, cut, scenario):
            if backend == 'native-sanitized':
                return [native, source, destination, int(restore), cut, scenario]
            return [simv, '-no_save', f'+source={source}', f'+outdir={destination}',
                    f'+restore={int(restore)}', f'+cut={cut}', f'+scenario={scenario}']
        case = out / backend; case.mkdir(exist_ok=True)
        for scenario in range(3):
            reference = case / str(scenario) / 'reference'; reference.mkdir(parents=True, exist_ok=True)
            run(command(reference, reference, False, 1, scenario), reference / 'run.log', reference)
            require((reference / 'trace').read_text().splitlines() == trace(scenario), 'initial flow differs from oracle')
            for cut in range(1, 5):
                restore = reference.parent / f'restore-{cut}'; restore.mkdir(exist_ok=True)
                log = run(command(reference, restore, True, cut, scenario), restore / 'run.log', restore)
                require((reference / f'cut-{cut}.owner').read_bytes() == oracle(cut), 'captured base differs from oracle')
                require((restore / 'initial.owner').read_bytes() == oracle(cut), 'base differs before first edge')
                expected = trace(scenario, cut)
                require((restore / 'trace').read_text().splitlines() == expected, 'initialization repeated or continuation order changed')
                require('entered simulation flow' not in log and 'FireSim fingerprint:' not in log and
                        'Commencing simulation.' not in log, 'initialization output repeated')
                require('Target Cycles Emulated: 42' in log and
                        f'PASS: simulation base continuation result={7 if scenario == 1 else 1 if scenario == 2 else 0}' in log,
                        'finalization or terminal status changed')
                if backend == 'vcs-dpi':
                    require(log.index('RESTORED_BEFORE_FIRST_EDGE') < log.index('FIXTURE_EDGE'), 'load followed edge')
                comparisons += 1; matched_calls += len(expected)
        negative = case / 'negative'; negative.mkdir(exist_ok=True)
        argv = [native, 'negative'] if backend == 'native-sanitized' else [simv, '-no_save', '+negative']
        log = run(argv, negative / 'run.log', negative)
        match = re.search(r'PASS: simulation base rejections (\d+)', log)
        require(match is not None, 'rejection suite failed')
        rejections[backend] = int(match[1])
        for i, bad in enumerate((b'', oracle(1)[:-1], oracle(1)+b'\0', b'\0'*len(oracle(1)))):
            failed = case / f'malformed-{i}'; failed.mkdir(exist_ok=True)
            (failed / 'cut-1.owner').write_bytes(bad)
            log = run(command(failed, failed, True, 1, 0), failed / 'run.log', failed, expected=1)
            require(not (failed / 'trace').exists() and not (failed / 'initial.owner').exists(), 'malformed load had side effects')
            if backend == 'vcs-dpi':
                require('REJECTED_BEFORE_FIRST_EDGE' in log and 'FIXTURE_EDGE' not in log, 'malformed load advanced fixture edge')
    summary = dict(scope='simulation_t base component; no generated RTL/harness/driver or whole FireSim restart',
                   fresh_continuations=comparisons, matched_mmio_calls=matched_calls,
                   before_first_edge_owner_comparisons=comparisons, malformed_fresh_processes=8,
                   rejections=rejections)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
