"""Actual FASED host owner continuation; no whole FireSim runtime restoration."""
import argparse
import json
import os
from pathlib import Path
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
TESTS = Path(__file__).resolve().parent
NAMES = ('hostReadLatency', 'hostWriteLatency', 'targetReadLatency', 'targetWriteLatency',
         'ingressReadLatency', 'ingressWriteLatency', 'totalReadLatency', 'totalWriteLatency')


def words(*values):
    return struct.pack('<' + 'Q' * len(values), *values)


def text(value):
    encoded = value.encode()
    return words(len(encoded)) + encoded


def configuration(read, write, model, memsize, defaults, user, histograms, ranges):
    data = words(0x3154504B43474457, 1, 6, 3, model, memsize, defaults)
    for mapping in (read, write):
        data += words(len(mapping))
        for name, address in sorted(mapping.items()):
            data += text(name) + words(address)
    data += words(len(user))
    for name, value in sorted(user.items()):
        data += text(name) + words(value)
    for names in (histograms, ranges):
        data += words(len(names)) + b''.join(text(name) for name in names)
    return data


def oracle(scenario):
    read = {'latency': 8, 'cycles': 12, 'requests': 16}
    write = {'latency': 8}
    histograms = NAMES if scenario not in (1, 3) else ()
    ranges = ('read', 'write') if scenario != 1 else ()
    for i, name in enumerate(histograms):
        base = 64 + i * 16
        read.update({name + 'Hist_dataH': base+8, name + 'Hist_dataL': base+12})
        write.update({name + 'Hist_enable': base, name + 'Hist_addr': base+4})
    if ranges:
        read['numRanges'] = 32
    for i, name in enumerate(ranges):
        base = 256 + i * 16
        read.update({name + 'Ranges_dataH': base+8, name + 'Ranges_dataL': base+12})
        write.update({name + 'Ranges_enable': base, name + 'Ranges_addr': base+4})
    config = configuration(read, write, 0, 1024, False, {'latency': 7}, histograms, ranges)
    history = 'cycles,requests,\n'
    snapshots, trace = [], []
    for stage in range(5):
        data = config + words(int(stage > 0)) + text(history)
        for i in range(len(histograms)):
            data += words(*[((1 << 32) + i*10000 + bin*13) if stage else 0 for bin in range(1024)])
        for i in range(len(ranges)):
            count = 3 if stage and scenario != 2 else 0
            data += words(count, *[(3 << 32) + i*10000 + bin*13 for bin in range(count)])
        snapshots.append(data)
        trace.append(f'OP {stage}')
        def w(addr, value):
            trace.append(f'W {addr} {value}')
        def r(addr, value):
            trace.append(f'R {addr} {value}')
        if stage in (0, 4):
            if stage == 0:
                w(8, 7)
            for i in range(len(histograms)):
                base = 64 + i * 16
                w(base, 1)
                for bin in range(1024):
                    value = (1 << 32) + i*10000 + bin*13 + stage*1000
                    w(base+4, bin); r(base+8, (value >> 32) | 0x80000000); r(base+12, value & 0xffffffff)
                w(base, 0)
            for i in range(len(ranges)):
                count = 0 if scenario == 2 else 3
                base = 256 + i*16
                if not stage:
                    r(32, count)
                w(base, 1)
                for bin in range(count):
                    value = (3 << 32) + i*10000 + bin*13 + stage*1000
                    w(base+4, bin); r(base+8, (value >> 32) | 0x80000000); r(base+12, value & 0xffffffff)
                w(base, 0)
        else:
            r(12, stage*100+12); r(16, stage*100+16)
            history += f'{stage*100+12},{stage*100+16},\n'
    histogram = ','.join(histograms) + (',' if histograms else '') + '\n'
    histogram += (('4000,'*len(histograms))+'\n')*1024
    range_output = None
    if ranges:
        range_output = 'Address,read,write,\n'
        if scenario != 2:
            for bin in range(3):
                range_output += f'{bin*1024//3:x},{(3<<32)+bin*13+4000},{(3<<32)+10000+bin*13+4000},\n'
    return trace, snapshots, {'stats.csv': history, 'latency_histogram.csv': histogram,
                              'range_counters.csv': range_output}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    require(os.environ['VCS_HOME'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    require(os.environ['CXX'] == '/usr/bin/g++-13', 'keep GCC/G++ 13')
    sources = [TESTS / 'fased_checkpoint.cc', CC / 'core/widget.cc', CC / 'core/address_map.cc',
               CC / 'bridges/fased_memory_timing_model.cc']
    native, simv = out / 'fased-native', out / 'fased-simv'
    run([os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Werror',
         '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', f'-I{CC}',
         *sources, '-o', native], out / 'native-build.log')
    run([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
         '-top', 'fased_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
         f'-Mdir={out / "fased-csrc"}', '-CFLAGS', f'-std=c++17 -DFASED_CHECKPOINT_DPI -I{CC}',
         '-o', simv, TESTS / 'fased_checkpoint_tb.sv', *sources], out / 'vcs-build.log')
    comparisons, operations, rejections = 0, 0, []
    for backend in ('native-sanitized', 'vcs-dpi'):
        def command(reference, restore, cut, scenario, negative=False):
            if backend == 'native-sanitized':
                return [native, 'negative' if negative else reference, int(restore), cut, scenario]
            return [simv, '-no_save', f'+reference={reference}', f'+restore={int(restore)}',
                    f'+cut={cut}', f'+scenario={scenario}', *(['+negative'] if negative else [])]
        for scenario in range(4):
            case = out / backend / str(scenario); reference = case / 'reference'
            reference.mkdir(parents=True, exist_ok=True)
            expected, snapshots, outputs = oracle(scenario)
            run(command(reference, False, 0, scenario), reference / 'run.log', reference)
            require((reference / 'trace').read_text().splitlines() == expected, 'reference MMIO differs from oracle')
            for cut in range(5):
                restore = case / f'restore-{cut}'; restore.mkdir(exist_ok=True)
                run(command(reference, True, cut, scenario), restore / 'run.log', restore)
                require((reference / f'cut-{cut}.owner').read_bytes() == snapshots[cut], 'captured host payload differs from oracle')
                require((restore / 'initial.owner').read_bytes() == snapshots[cut], 'owner differs before first edge')
                require((restore / 'trace').read_text().splitlines() == expected[expected.index(f'OP {cut}'):], 'restored MMIO differs from oracle')
                for filename, value in outputs.items():
                    if value is None:
                        require(not (restore / filename).exists(), 'unexpected range output')
                    else:
                        require((reference / filename).read_text() == value == (restore / filename).read_text(), 'output history/counters differ from oracle')
                comparisons += 1; operations += 5-cut
        negative = out / backend / 'negative'; negative.mkdir(exist_ok=True)
        log = run(command(negative, False, 0, 0, True), negative / 'run.log', negative)
        require('PASS: FASED malformed/configuration/suspension/interruption rejections' in log, 'negative guards incomplete')
        rejections.append(dict(backend=backend, log=str(negative / 'run.log')))
        # Malformed loads in separate native/VCS processes reject during init,
        # before a trace is opened or the first fixture edge is dispatched.
        for i, bad in enumerate((b'', snapshots[1][:-1], snapshots[1]+b'\0', b'\0'*len(snapshots[1]))):
            malformed = out / backend / f'malformed-{i}'; malformed.mkdir(exist_ok=True)
            source = malformed / 'input'; source.mkdir(exist_ok=True)
            (source / 'cut-1.owner').write_bytes(bad)
            run(command(source, True, 1, 3), malformed / 'run.log', malformed, expected=1)
            require(not (malformed / 'trace').exists() and not (malformed / 'initial.owner').exists(),
                    'malformed restore advanced an edge or published state')
    summary = dict(scope='FASED host component only; no whole FireSim restart', fresh_continuations=comparisons,
                   matched_operations=operations, before_first_edge_owner_comparisons=comparisons,
                   malformed_fresh_processes=8, negatives=rejections)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
