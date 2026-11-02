"""Actual FASED host owner continuation; no whole FireSim runtime restoration."""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import tempfile

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
    destination = args.out.resolve(); destination.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='attempt-', dir=destination))
    require(os.environ['VCS_HOME'] == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    require(os.environ['CXX'] == _toolchain.CXX, 'keep GCC/G++ 13')
    sources = [TESTS / 'fased_checkpoint.cc', CC / 'core/widget.cc', CC / 'core/address_map.cc',
               CC / 'bridges/fased_memory_timing_model.cc']
    bound_sources = sorted(set(sources + list(CC.rglob('*.h')) + [Path(__file__).resolve(),
        TESTS / 'fased_checkpoint_tb.sv', TESTS / 'verify_semantic_vcs.py',
        ROOT / 'tools/checkpoint_formats/toolchain.py', ROOT / 'tools/checkpoint_formats/codec.py',
        ROOT / 'automations/checkpoint_loop/vcs-env.sh']))
    source_records = []
    for source in bound_sources:
        relative = source.relative_to(ROOT)
        snapshot = out / 'sources' / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, snapshot)
        source_records.append(dict(path=str(source), snapshot=str(snapshot),
                                   sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest()))
    (out / 'sources.json').write_text(json.dumps(source_records, indent=2)+'\n')
    environment = {key: os.environ.get(key) for key in ('VCS_HOME', 'CC', 'CXX', 'VCS_FLAGS', 'ASAN_OPTIONS', 'UBSAN_OPTIONS')}
    (out / 'environment.json').write_text(json.dumps(environment, indent=2)+'\n')
    commands = []
    def invoke(argv, log, cwd=ROOT, expected=0):
        commands.append(dict(argv=[str(value) for value in argv], cwd=str(cwd), log=str(log),
                             expected_exit=expected, backend='eda'))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return run(argv, log, cwd, expected)
    native, simv = out / 'fased-native', out / 'fased-simv'
    invoke([os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Werror',
         '-g', '-no-pie', '-pthread', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', f'-I{CC}',
         *sources, '-o', native], out / 'native-build.log')
    invoke([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-Mupdate', '-sverilog', '-timescale=1ns/1ps',
         '-top', 'fased_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
         f'-Mdir={out / "fased-csrc"}', '-CFLAGS', f'-std=c++17 -pthread -DFASED_CHECKPOINT_DPI -I{CC}',
         '-LDFLAGS', '-pthread',
         '-o', simv, TESTS / 'fased_checkpoint_tb.sv', *sources], out / 'vcs-build.log')
    comparisons, operations, rejections = 0, 0, []
    for backend in ('native-sanitized', 'vcs-dpi'):
        def command(reference, restore, cut, scenario, negative=False):
            restore = int(restore)
            if backend == 'native-sanitized':
                return [native, 'negative' if negative else reference, restore, cut, scenario]
            return [simv, '-no_save', f'+reference={reference}', f'+restore={restore}',
                    f'+cut={cut}', f'+scenario={scenario}', *(['+negative'] if negative else [])]
        for scenario in range(4):
            case = out / backend / str(scenario); reference = case / 'reference'
            reference.mkdir(parents=True, exist_ok=True)
            expected, snapshots, outputs = oracle(scenario)
            invoke(command(reference, False, 0, scenario), reference / 'run.log', reference)
            require((reference / 'trace').read_text().splitlines() == expected, 'reference MMIO differs from oracle')
            for mode, name in ((1, 'legacy'), (2, 'prepared')):
                for cut in range(5):
                    restore = case / f'{name}-restore-{cut}'; restore.mkdir(exist_ok=True)
                    invoke(command(reference, mode, cut, scenario), restore / 'run.log', restore)
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
        log = invoke(command(negative, False, 0, 0, True), negative / 'run.log', negative)
        require('PASS: FASED malformed/configuration/suspension/interruption rejections' in log, 'negative guards incomplete')
        require('PASS: FASED prepared cancellation/ABA/lifetime/thread/aggregate/interruption checks' in log,
                'prepared publication checks incomplete')
        allocations = re.search(r'FASED_PREPARED_ALLOCATIONS prepare_failures=(\d+) seal_failures=(\d+) '
                                r'publication_allocations=0 unchanged=1 mmio=0 files=0', log)
        require(allocations is not None and all(int(value)>0 for value in allocations.groups()),
                'prepared allocation coverage incomplete')
        rejections.append(dict(backend=backend, log=str(negative / 'run.log'),
                               prepare_allocation_failures=int(allocations[1]),
                               seal_allocation_failures=int(allocations[2])))
        # Malformed loads in separate native/VCS processes reject during init,
        # before a trace is opened or the first fixture edge is dispatched.
        for mode, name in ((1, 'legacy'), (2, 'prepared')):
            for i, bad in enumerate((b'', snapshots[1][:-1], snapshots[1]+b'\0', b'\0'*len(snapshots[1]))):
                malformed = out / backend / f'{name}-malformed-{i}'; malformed.mkdir(exist_ok=True)
                source = malformed / 'input'; source.mkdir(exist_ok=True)
                (source / 'cut-1.owner').write_bytes(bad)
                invoke(command(source, mode, 1, 3), malformed / 'run.log', malformed, expected=1)
                require(not (malformed / 'trace').exists() and not (malformed / 'initial.owner').exists(),
                        'malformed restore advanced an edge or published state')
    deaths = []
    for i, name in enumerate(('unsealed', 'repeated', 'stale-sealed', 'wrong-thread', 'expired')):
        case = out / 'native-sanitized' / f'publish-{name}'; case.mkdir(exist_ok=True)
        log = invoke([native, 'death', 0, i, 0], case / 'run.log', case, expected=86)
        require('FASED_PUBLISH_REJECTED unchanged=1 mmio=0 files=0' in log,
                'fatal publication mutated destination or external state')
        deaths.append(dict(case=name, exit_status=86, log=str(case / 'run.log')))
    for source in source_records:
        require(hashlib.sha256(Path(source['path']).read_bytes()).hexdigest() == source['sha256'],
                'source changed while FASED verification was running')
    artifacts = [dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
                 for path in sorted(out.rglob('*')) if path.is_file() and 'sources' not in path.relative_to(out).parts]
    (out / 'artifacts.json').write_text(json.dumps(artifacts, indent=2)+'\n')
    summary = dict(scope='FASED host component only; no whole FireSim restart', output=str(out),
                   complete_fpga_capture=False, deployable_capture_image=False, cpu_migration_verified=False,
                   source_manifest=str(out / 'sources.json'), artifact_manifest=str(out / 'artifacts.json'),
                   commands=str(out / 'commands.json'), fresh_continuations=comparisons,
                   matched_operations=operations, before_first_edge_owner_comparisons=comparisons,
                   restore_paths=['legacy', 'prepared'], malformed_fresh_processes=16,
                   publish_misuse_fail_stops=deaths, negatives=rejections)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    selection = destination / '.selected.json.tmp'
    selection.write_text(json.dumps(dict(summary=str(out / 'summary.json'),
        sha256=hashlib.sha256((out / 'summary.json').read_bytes()).hexdigest()), indent=2)+'\n')
    os.replace(selection, destination / 'selected.json')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
