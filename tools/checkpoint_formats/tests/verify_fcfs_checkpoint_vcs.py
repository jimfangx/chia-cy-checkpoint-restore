"""Concrete production FCFS component, native sanitizers and fresh VCS DPI."""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
import os
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
RUNTIME = ROOT / 'sims/firesim/sim/src/main/cc'
TESTS = Path(__file__).resolve().parent


def words(*values):
    return struct.pack('<' + 'Q'*len(values), *values)


def text(value):
    value = value.encode()
    return words(len(value)) + value


def oracle():
    # Original GCC 13 unordered-map traversal is explicitly captured/bound by
    # the driver; duplicate eventA uses its final value, signed B becomes u32.
    config = words(0x3154504B43474457, 1, 9, 2, 0, 0, 2)
    config += text('eventsB') + words(0xffffffff) + text('eventsA') + words(17)
    def identity(i, schema):
        return text(f'widget/{i}') + text(f'firesim.widget.{schema}.v1')
    config += identity(1, 'peek-poke') + words(2)
    config += identity(2, 'fased') + identity(3, 'fased') + words(2)
    for i in range(2):
        config += identity(2+i, 'fased') + words(2)
        config += text('eventsA') + words(200+i*100)
        config += text('eventsB') + words(208+i*100) + words(0)
    return config + words(1)


def trace(scenario, cut=0):
    result = []
    total = 1 if scenario == 2 else 11
    calls = {3: ['W 100 1000'], 4: ['R 104 0'], 7: ['R 112 0'],
             8: ['R 104 0'], 11: ['R 112 1']}
    for i in range(cut+1, total+1):
        result += [f'OP {i}', *calls.get(i, [])]
    result += ['FINAL', 'R 208 4294967295', 'R 200 17',
               f'R 308 {4 if scenario == 1 else 4294967295}', 'R 300 17']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    require(os.environ['VCS_HOME'] == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    require(os.environ['CXX'] == _toolchain.CXX, 'keep GCC/G++ 13')
    sources = [TESTS / 'fcfs_checkpoint.cc', *[CC / p for p in (
        'core/simulation.cc', 'core/widget_registry.cc', 'core/widget.cc',
        'core/stream_engine.cc', 'core/bridge_driver.cc', 'core/address_map.cc',
        'core/stepped_run_loop.cc', 'core/systematic_scheduler.cc',
        'bridges/master.cc', 'bridges/clock.cc', 'bridges/loadmem.cc',
        'bridges/peek_poke.cc', 'bridges/fased_memory_timing_model.cc')]]
    native, simv = out / 'fcfs-native', out / 'fcfs-simv'
    includes = [f'-I{CC}', f'-I{RUNTIME}']
    run([os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
         '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', *includes,
         *sources, '-lgmp', '-o', native], out / 'native-build.log')
    run([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
         '-top', 'fcfs_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
         f'-Mdir={out / "fcfs-csrc"}', '-CFLAGS', ' '.join(['-std=c++17', '-DFCFS_CHECKPOINT_DPI', *includes]),
         '-LDFLAGS', '-Wl,--no-as-needed -lgmp', '-o', simv, TESTS / 'fcfs_checkpoint_tb.sv', *sources], out / 'vcs-build.log')
    comparisons, matched_calls, owner_comparisons, rejections = 0, 0, 0, {}
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
            require((reference / 'trace').read_text().splitlines() == trace(scenario), 'FCFS reference differs from independent oracle')
            for cut in range(1, 2 if scenario == 2 else 12):
                restore = reference.parent / f'restore-{cut}'; restore.mkdir(exist_ok=True)
                log = run(command(reference, restore, True, cut, scenario), restore / 'run.log', restore)
                require((reference / f'cut-{cut}.0.owner').read_bytes() == oracle(), 'driver config differs from independent oracle')
                for i in range(3):
                    require((restore / f'initial.{i}.owner').read_bytes() == (reference / f'cut-{cut}.{i}.owner').read_bytes(), 'owner differs before first edge')
                    require((restore / f'terminal.{i}.owner').read_bytes() == (reference / f'terminal.{i}.owner').read_bytes(), 'terminal owner differs')
                    owner_comparisons += 1
                expected = trace(scenario, cut)
                require((restore / 'trace').read_text().splitlines() == expected, 'operation/finalization order differs')
                require(f'result={int(scenario == 1)}' in log, 'terminal result differs')
                require(('did not match: Measured 4, Expected -1' in log) == (scenario == 1), 'counter error output differs')
                if backend == 'vcs-dpi':
                    require(log.index('RESTORED_BEFORE_FIRST_EDGE') < log.index('FIXTURE_EDGE'), 'load followed fixture edge')
                comparisons += 1; matched_calls += sum(line[0] in 'RW' for line in expected)
        negative = case / 'negative'; negative.mkdir(exist_ok=True)
        argv = [native, 'negative'] if backend == 'native-sanitized' else [simv, '-no_save', '+negative']
        log = run(argv, negative / 'run.log', negative)
        match = re.search(r'PASS: FCFS rejections (\d+)', log)
        require(match is not None, 'rejection suite failed'); rejections[backend] = int(match[1])
        reference = case / '0/reference'
        for i, bad in enumerate((b'', oracle()[:-1], oracle()+b'\0', b'\0'*len(oracle()))):
            failed = case / f'malformed-{i}'; failed.mkdir(exist_ok=True)
            for j in (1, 2):
                (failed / f'cut-1.{j}.owner').write_bytes((reference / f'cut-1.{j}.owner').read_bytes())
            (failed / 'cut-1.fixture').write_bytes(b'\0')
            (failed / 'cut-1.0.owner').write_bytes(bad)
            log = run(command(failed, failed, True, 1, 0), failed / 'run.log', failed, expected=1)
            require(not (failed / 'trace').exists() and not (failed / 'initial.0.owner').exists(), 'malformed load had side effects')
            if backend == 'vcs-dpi':
                require('REJECTED_BEFORE_FIRST_EDGE' in log and 'FIXTURE_EDGE' not in log, 'malformed load advanced edge')
    summary = dict(scope='concrete FCFS + scheduler/run-loop components with fixture MMIO; no generated RTL/harness or whole-runtime restart',
                   fresh_continuations=comparisons, matched_mmio_calls=matched_calls,
                   before_first_edge_owner_comparisons=owner_comparisons,
                   malformed_fresh_processes=8, rejections=rejections)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
