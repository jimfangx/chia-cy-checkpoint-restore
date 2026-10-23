"""Audited concrete host widget components, not full FireSim restart acceptance.

Native ASan/UBSan and fresh VCS DPI processes use actual widget implementations
with a deterministic MMIO/clock fixture. Compare all bus operations, responses,
GMP values and completed-call flags to an independent Python oracle. Full
production metasim regressions separately retain unsupported-owner rejection.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
import os
from pathlib import Path
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
TESTS = Path(__file__).resolve().parent
OPERATIONS = 25


def oracle():
    traces, snapshots, flags = [], [], 0
    def words(*values):
        return struct.pack('<' + 'Q' * len(values), *values)
    def owner(kind, *values):
        return words(0x3154504B43474457, 1, kind, len(values), *values)
    fixed = [owner(1, 0, 4, 8), owner(2, 16, 20, 24, 28, 32, 36),
             owner(3, 64, 68, 72, 76, 80, 84, 88, 92, 96, 4, 40, 96, 3),
             owner(4, 112, 116, 20, 5, 7)]
    peek = owner(5, 128, 132, 136)
    for name, addr in (('in', 144), ('out', 160)):
        peek += words(1, len(name)) + name.encode() + words(addr, 3)
    def states():
        return [p + words(0) for p in fixed] + [peek + words(flags)]
    for index in range(OPERATIONS):
        snapshots.append(states())
        lines, gmp = [f'OP {index}'], 0
        def write(addr, data):
            lines.append(f'W {addr} {data}')
        def read(addr):
            data = (1 if addr in (0, 84) else 0x46697265 if addr == 4 else
                    int(index not in (19, 22)) if addr == 132 else
                    int(index != 20) if addr == 136 else addr ^ 0x13579bdf)
            lines.append(f'R {addr} {data}')
            return data
        def result(value):
            lines.append(f'RESULT {value}')
        if index == 0:
            result(read(0) == 1)
        elif index == 1:
            result(read(4) != 0x46697265)
        elif index == 2:
            write(8, 0x12345678)
        elif index in (3, 4, 24):
            lo, hi, latch = (16, 20, 24) if index == 3 else (28, 32, 36)
            write(latch, 1)
            low, high = read(lo), read(hi)
            result((high << 32) | low)
        elif index == 5:
            write(112, 7); write(116, 1)
        elif index in (6, 8, 10):
            addr, gmp, beats = ((0x123456789, 0xfeedbeef, 1) if index == 6 else
                               (32, 0xabcdef0123456789fedcba98, 2) if index == 8 else
                               (0, 0x0123456789abcdefdeadbeef, 1))
            write(64, addr >> 32); write(68, addr & 0xffffffff); write(72, beats)
            for chunk in range(beats * 3):
                write(80, (gmp >> (32 * chunk)) & 0xffffffff)
            if index == 10:  # caller's separate GMP value remains zero
                gmp = 0
        elif index == 7:
            write(88, 3); write(92, 0x456789ab)
            for chunk in range(3):
                gmp |= read(96) << (32 * chunk)
        elif index == 9:
            write(76, 1); read(84)
        elif index in (11, 17, 22):
            flags = 0
            if index == 11 or read(132):
                write(144, {11: 123, 17: 321, 22: 777}[index])
            else:
                flags = 2
        elif index == 12:
            flags, gmp = 0, 0xabcdef0123456789fedcba98
            for chunk in range(3):
                write(144 + 4 * chunk, (gmp >> (32 * chunk)) & 0xffffffff)
        elif index in (13, 18, 19, 20):
            flags = 0
            if index == 13 or read(132):
                if index != 13 and not read(136):
                    flags = 1
                result(read(160))
            else:
                flags = 2; result(0)
        elif index in (14, 23):
            flags = 0
            for chunk in range(3):
                gmp |= read(160 + 4 * chunk) << (32 * chunk)
        elif index in (15, 21):
            write(128, 17 if index == 15 else 11)
            if index == 21:
                read(132)
        elif index == 16:
            result(bool(read(132)))
        lines.append(f'GMP {gmp:x} FLAGS {flags & 1} {(flags >> 1) & 1}')
        traces.extend(line.replace('True', '1').replace('False', '0') for line in lines)
    snapshots.append(states())
    return traces, snapshots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    require(os.environ['VCS_HOME'] == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    require(os.environ['CXX'] == _toolchain.CXX, 'keep GCC/G++ 13')
    sources = [TESTS / 'widget_checkpoint.cc', CC / 'core/widget.cc',
               *[CC / f'bridges/{name}.cc' for name in ('master', 'clock', 'loadmem', 'reset_pulse', 'peek_poke')]]
    native, simv = out / 'widget-native', out / 'widget-simv'
    run([os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Werror',
         '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', f'-I{CC}',
         *sources, '-lgmp', '-o', native], out / 'native-build.log')
    run([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
         '-top', 'widget_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
         f'-Mdir={out / "widget-csrc"}', '-CFLAGS', f'-std=c++17 -DWIDGET_CHECKPOINT_DPI -I{CC}',
         '-LDFLAGS', '-Wl,--no-as-needed -lgmp -Wl,--as-needed', '-o', simv, TESTS / 'widget_checkpoint_tb.sv', *sources], out / 'vcs-build.log')
    expected, snapshots = oracle()
    results = []
    for backend in ('native-sanitized', 'vcs-dpi'):
        case = out / backend; case.mkdir(exist_ok=True)
        def command(mode, cut):
            if backend == 'native-sanitized':
                return [native, mode, case, cut]
            return [simv, '-no_save', f'+outdir={case}', f'+restore={int(mode == "restore")}',
                    f'+cut={cut}', *(['+negative'] if mode == 'negative' else [])]
        run(command('reference', 0), case / 'reference.log')
        require((case / 'reference.trace').read_text().splitlines() == expected,
                f'{backend}: MMIO/response/flags differ from independent oracle')
        for cut in range(OPERATIONS + 1):
            run(command('restore', cut), case / f'restore-{cut}.log')
            suffix = expected[expected.index(f'OP {cut}'):] if cut < OPERATIONS else []
            require((case / f'restore-{cut}.trace').read_text().splitlines() == suffix,
                    f'{backend}: continuation mismatch at cut {cut}')
            for i in range(5):
                require((case / f'cut-{cut}.{i}.owner').read_bytes() == snapshots[cut][i], 'capture differs from oracle')
                require((case / f'restore-{cut}.initial.{i}.owner').read_bytes() == snapshots[cut][i],
                        'owner mismatch before first edge')
                require((case / f'restore-{cut}.final.{i}.owner').read_bytes() == snapshots[-1][i], 'final owner mismatch')
        log = run(command('negative', 0), case / 'negative.log')
        require('PASS: widget payload/suspension/reentry/interruption rejections' in log, 'negative checks incomplete')
        require((case / 'reference.trace').read_text().splitlines() == expected,
                'negative fixtures overwrote reference evidence')
        for i in range(5):
            require((case / f'reference.final.{i}.owner').read_bytes() == snapshots[-1][i],
                    'reference final owner differs from oracle')
        results.append(dict(backend=backend, cuts=OPERATIONS+1, rejection_log=str(case / 'negative.log')))
    summary = dict(scope='five concrete widget host owners; no whole-runtime/harness restore',
                   fresh_continuations=2*(OPERATIONS+1), matched_operations=2*sum(range(OPERATIONS+1)),
                   before_first_edge_owner_comparisons=2*(OPERATIONS+1)*5, backends=results)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
