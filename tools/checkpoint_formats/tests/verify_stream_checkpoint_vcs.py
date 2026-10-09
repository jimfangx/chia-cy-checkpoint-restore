"""CPU stream host components with independent byte queues and I/O oracle.

Actual StreamEngine/CPUManagedStreamWidget methods run under ASan/UBSan and
in fresh VCS DPI processes. The queue service is a fixture, not generated
stream hardware or full FireSim continuation. No acceptance is inferred from
the fixture clock edges or its independently snapshotted queue buffers.
"""
import argparse
import json
import os
from pathlib import Path
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
TESTS = Path(__file__).resolve().parent
PROGRAM = (
    (0,0,0,0,0), (1,0,3,2,0), (1,0,3,0,0), (2,0,4,2,0), (2,0,4,0,0),
    (1,1,5,3,0), (1,1,1,1,0), (2,1,5,0,0), (2,1,1,0,0), (3,0,0,0,0),
    (4,1,0,0,0), (1,0,2,1,1), (2,0,3,2,1), (1,0,0,0,0), (2,1,0,0,0),
    (1,1,4,3,3), (2,1,5,3,0), (1,0,3,1,2), (2,0,3,1,3), (2,1,5,1,3),
    (0,0,0,0,0), (3,1,0,0,0), (4,0,0,0,0))


def words(*values):
    return struct.pack('<' + 'Q' * len(values), *values)


def configuration(beat):
    config = words(0x3154504B43474457, 1, 7, 2, 0, beat)
    for direction, names in enumerate((('push0','push1'), ('pull0','pull1'))):
        config += words(2)
        for i, name in enumerate(names):
            q = direction * 2 + i
            config += words(len(name)) + name.encode() + words(
                (q+1)*4096, 256+q*4, (3,5)[i], beat*(i+1))
    return config


def oracle(beat):
    widths, caps = (beat,beat*2), (3,5)
    queues = [bytearray((q*41+n) & 255 for n in range(count*widths[q%2]))
              for q, count in enumerate((2,0,1,5))]
    traces, snapshots, initialized = [], [], 0
    def snapshot():
        return (configuration(beat) + words(initialized),
                b''.join(struct.pack('<H',len(q))+q for q in queues))
    for index, (kind, s, num, req, move) in enumerate(PROGRAM):
        snapshots.append(snapshot())
        traces.append(f'OP {index}')
        if move:
            traces.append(f'DEVICE {move}')
            for q in range(2):
                size = min(move*widths[q], len(queues[q]), caps[q]*widths[q]-len(queues[q+2]))
                queues[q+2] += queues[q][:size]; del queues[q][:size]
        data = bytearray([0xa5]) * (num*widths[s])
        result = 0
        if kind == 0:
            initialized = 1
        elif kind in (1,2):
            q = s if kind == 1 else s+2
            count = len(queues[q]) // widths[s]
            traces.append(f'R {256+q*4} {count}')
            available = caps[s]-count if kind == 1 else count
            if kind == 1:
                data = bytearray((index*17+n)&255 for n in range(len(data)))
            if available and available >= req:
                result = min(available,num)*widths[s]
                if kind == 1:
                    queues[q] += data[:result]
                    traces.append(f'W {(q+1)*4096} {result} {data[:result].hex()}')
                else:
                    data[:result] = queues[q][:result]
                    traces.append(f'D {(q+1)*4096} {result} {data[:result].hex()}')
                    del queues[q][:result]
        traces.append(f'RESULT {result} {data.hex()}')
    snapshots.append(snapshot())
    return traces, snapshots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    require(os.environ['VCS_HOME'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    require(os.environ['CXX'] == '/usr/bin/g++-13', 'keep GCC/G++ 13')
    sources = [TESTS/'stream_checkpoint.cc', CC/'core/stream_engine.cc', CC/'bridges/cpu_managed_stream.cc']
    native, simv = out/'stream-native', out/'stream-simv'
    run([os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Werror',
         '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', f'-I{CC}',
         *sources, '-o', native], out/'native-build.log')
    run([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
         '-top', 'stream_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
         f'-Mdir={out/"stream-csrc"}', '-CFLAGS', f'-std=c++17 -DSTREAM_CHECKPOINT_DPI -I{CC}',
         '-o', simv, TESTS/'stream_checkpoint_tb.sv', *sources], out/'vcs-build.log')
    results = []
    for backend in ('native-sanitized','vcs-dpi'):
        for beat in (8,16,64):
            case = out/backend/f'beat-{beat}'; case.mkdir(parents=True,exist_ok=True)
            def command(mode,cut,directory=case):
                if backend == 'native-sanitized':
                    return [native,mode,directory,cut,beat]
                return [simv,'-no_save',f'+outdir={directory}',f'+beat={beat}',f'+restore={int(mode=="restore")}',
                        f'+cut={cut}', *(['+negative'] if mode=='negative' else [])]
            expected, snapshots = oracle(beat)
            run(command('reference',0), case/'reference.log')
            require((case/'reference.trace').read_text().splitlines() == expected, 'stream I/O differs from oracle')
            for cut in range(len(PROGRAM)+1):
                run(command('restore',cut), case/f'restore-{cut}.log')
                suffix = expected[expected.index(f'OP {cut}'):] if cut<len(PROGRAM) else []
                require((case/f'restore-{cut}.trace').read_text().splitlines() == suffix, 'stream continuation mismatch')
                for ext, slot in (('owner',0),('fixture',1)):
                    require((case/f'cut-{cut}.{ext}').read_bytes() == snapshots[cut][slot], 'snapshot differs from oracle')
                    require((case/f'restore-{cut}.initial.{ext}').read_bytes() == snapshots[cut][slot], 'initial restore mismatch')
                    require((case/f'restore-{cut}.final.{ext}').read_bytes() == snapshots[-1][slot], 'final state mismatch')
                if backend=='vcs-dpi':
                    log=(case/f'restore-{cut}.log').read_text()
                    require(log.count('FIXTURE_EDGE') == len(PROGRAM)-cut+1, 'unexpected fixture edges')
            log = run(command('negative',0),case/'negative.log')
            require('PASS: stream payload/suspension/reentry/interruption rejections' in log, 'negative checks incomplete')
            good = snapshots[0][0]
            mutations = [b'', good[:-1], good+b'\0', bytes([good[0]^1])+good[1:],
                         good[:-8]+words(2), good[:-8]+words(256), configuration(beat*2)+words(0)]
            for n, bad in enumerate(mutations):
                failure=case/f'invalid-{n}'; failure.mkdir(exist_ok=True)
                (failure/'cut-0.owner').write_bytes(bad)
                (failure/'cut-0.fixture').write_bytes(snapshots[0][1])
                log=run(command('restore',0,failure),failure/'run.log',expected=1 if backend=='native-sanitized' else 0)
                require(not (failure/'restore-0.trace').exists(), 'invalid restore opened trace')
                if backend=='vcs-dpi':
                    require('REJECTED_BEFORE_FIRST_EDGE' in log and 'FIXTURE_EDGE' not in log, 'invalid restore advanced edge')
            require((case/'reference.trace').read_text().splitlines()==expected, 'negative tests changed reference evidence')
            results.append(dict(backend=backend,beat_bytes=beat,cuts=len(PROGRAM)+1,
                                invalid_fresh_processes=len(mutations),rejection_log=str(case/'negative.log')))
    summary=dict(scope='CPU-managed host stream component; fixture queues; no whole FireSim restore',
                 fresh_continuations=len(results)*(len(PROGRAM)+1),
                 matched_operations=len(results)*sum(range(len(PROGRAM)+1)),
                 before_first_edge_owner_comparisons=len(results)*(len(PROGRAM)+1),
                 malformed_fresh_processes=sum(r['invalid_fresh_processes'] for r in results),backends=results)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
