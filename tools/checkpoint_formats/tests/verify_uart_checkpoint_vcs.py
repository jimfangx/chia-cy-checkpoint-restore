"""Actual UART host owner in native sanitized and fresh VCS component processes.

Independently decode every captured byte and bus operation; fixture cycle
labels are not Rocket target cycles. Complete CPU acceptance remains pending.
"""
from tools.checkpoint_formats import toolchain as _toolchain
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
BRIDGES = ROOT / 'generators/firechip/bridgestubs/src/main/cc'
INPUT = bytes([0, 128, 255, 65])
OPERATIONS = 8


def configuration(header):
    matches = re.findall(r'registry.add_widget\(new uart_t\(\s*simif,\s*UARTBRIDGEMODULE_struct\{(.*?)\},\s*(\d+),\s*args\s*\)\);', header, re.S)
    require(len(matches) == 1, 'expected one actual Rocket UART constructor')
    fields, index = matches[0]
    pairs = re.findall(r'\.(\w+)\s*=\s*(\d+)\s*,', fields)
    require([p[0] for p in pairs] == 'out_bits out_valid out_ready in_bits in_valid in_ready'.split(),
            'missing/extra/reordered UART fields')
    addresses = [int(p[1]) for p in pairs]
    require(int(index) == 0 and addresses == list(range(1056, 1080, 4)), 'changed Rocket UART geometry')
    return words(0x3154504B43474457, 1, 9, 7, 0, *addresses)


def oracle(config):
    """Transaction algorithm independent of the C++ serializer and driver."""
    trace, snapshots, output, position = [], [], bytearray(), 0
    in_bits = out_bits = in_ready = out_ready = 0
    def state():
        h = words(0x3154504B43474457, 1, 10, 1, len(INPUT)) + INPUT
        h += words(position, len(output)) + output
        return config + words(in_bits, 0, in_ready, out_bits, 0, out_ready, len(h)) + h
    budgets = [0, 1, 0, 2, 10, 1, 0, 0]
    outputs = [[], [0], [128, 255], [65], [0, 129], [], [165, 66], []]
    for op in range(OPERATIONS):
        snapshots.append(state())
        trace.append(f'OP {op} C {100+7*op}')
        budget, outgoing = budgets[op], list(outputs[op])
        out_ready = 1
        while True:
            in_ready = int(budget > 0)
            trace += [f'R 1076 {in_ready}', f'R 1060 {int(bool(outgoing))}']
            fired_out = bool(outgoing)
            if fired_out:
                out_bits = outgoing.pop(0)
                trace.append(f'R 1056 {out_bits}')
            if in_ready and position < len(INPUT):
                in_bits = INPUT[position]; position += 1; budget -= 1
                # The existing signed-char host write retains these high bits;
                # the actual UART MMIO datapath consumes the low eight bits.
                bus_bits = in_bits if in_bits < 128 else (in_bits - 256) & 0xffffffff
                trace += [f'W 1068 {bus_bits}', 'W 1072 1']
            if fired_out:
                output.append(out_bits); trace.append('W 1064 1')
            else:
                break
    snapshots.append(state())
    return trace, snapshots, bytes(output)


def audit_case(case, config):
    trace, snapshots, output = oracle(config)
    require((case / 'reference.trace').read_text().splitlines() == trace, 'UART transaction oracle mismatch')
    for cut, snapshot in enumerate(snapshots):
        for p in [case / f'cut-{cut}.owner', case / f'restore-{cut}.initial.owner']:
            require(p.read_bytes() == snapshot, 'complete UART owner readback ' + str(p))
        require((case / f'restore-{cut}.final.owner').read_bytes() == snapshots[-1], 'incomplete final UART owner')
        suffix = trace[trace.index(f'OP {cut} C {100+7*cut}'):] if cut < OPERATIONS else []
        require((case / f'restore-{cut}.trace').read_text().splitlines() == suffix, 'changed UART continuation/timing')
    require((case / 'output.bin').read_bytes() == output, 'full UART output including restored prefix')
    return dict(input_bytes=len(INPUT), output_bytes=len(output), cuts=len(snapshots), fixture_cycles=[100+7*i for i in range(8)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rocket-header', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ['VCS_HOME'] == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    require(os.environ['CXX'] == _toolchain.CXX, 'keep GCC/G++ 13')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='native-', dir=args.out.resolve()))
    header = args.rocket_header.resolve(); config = configuration(header.read_text())
    trace, snapshots, output = oracle(config)
    sources = [TESTS / 'uart_checkpoint.cc', CC / 'core/widget.cc', BRIDGES / 'bridges/uart.cc']
    native, simv = out / 'uart-native', out / 'uart-simv'
    run([os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Werror',
         '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', f'-I{CC}', f'-I{BRIDGES}',
         *sources, '-o', native], out / 'native-build.log')
    run([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
         '-top', 'uart_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
         f'-Mdir={out / "csrc"}', '-CFLAGS', f'-std=c++17 -DUART_CHECKPOINT_DPI -I{CC} -I{BRIDGES}',
         '-o', simv, TESTS / 'uart_checkpoint_tb.sv', *sources], out / 'vcs-build.log')
    commands, results = [], []
    for backend in ['native-sanitized', 'vcs-dpi']:
        case = out / backend; case.mkdir()
        def invoke(mode, cut, directory=case, expected=0):
            argv = [native, mode, directory, cut] if backend == 'native-sanitized' else [
                simv, '-no_save', f'+outdir={directory}', f'+restore={int(mode == "restore")}', f'+cut={cut}',
                *(['+negative'] if mode == 'negative' else [])]
            log = directory / f'{mode}-{cut}.log'
            text = run(argv, log, expected=expected)
            commands.append(dict(cwd='.', argv=list(map(str, argv)), log=str(log), expected_exit=expected))
            if backend == 'vcs-dpi' and expected == 0 and mode != 'negative':
                require('UART_READBACK edges=0' in text and 'PASS: fresh UART component continuation' in text,
                        'missing zero-edge native VCS checks')
            return text
        invoke('reference', 0)
        for cut in range(OPERATIONS+1):
            invoke('restore', cut)
            require((case / 'output.bin').read_bytes() == output, 'fresh complete output differs')
        negative = invoke('negative', 0)
        count = re.search(r'PASS: UART atomic payload/configuration/suspension checks (\d+)', negative)
        require(count is not None, 'missing actual UART negative checks')
        audit_case(case, config) # Recheck retained positive traces after negatives.
        fault = case / 'actual-cursor-fault'; fault.mkdir()
        bad = bytearray(snapshots[4]); bad[188] = 2 # Valid cursor; first new input is wrong.
        (fault / 'cut-4.owner').write_bytes(bad)
        shutil.copyfile(case / 'reference.trace', fault / 'reference.trace')
        text = invoke('restore', 4, fault, expected=1)
        require('FIRST_MISMATCH fixture_cycle=128 signal=uart_in_bits op=4' in text, 'wrong actual first UART divergence')
        lines = (fault / 'restore-4.trace').read_text().splitlines()
        require(lines[-1] == 'W 1068 4294967295' and 'W 1072 1' not in lines and
                not any(s.startswith('OP 5 ') for s in lines), 'acknowledged divergent input')
        results.append(dict(backend=backend, fresh_continuations=9, negative_assertions=int(count[1]),
                            first_actual_corruption_fixture_cycle=128, transactions=audit_case(case, config)))
    inputs = [header, *sources, CC / 'core/widget_checkpoint.h', BRIDGES / 'bridges/uart.h',
              BRIDGES / 'bridges/serial_data.h', TESTS / 'uart_checkpoint_tb.sv', Path(__file__)]
    summary = dict(status='passed', artifact_root=str(out), scope='UART buffered-file host component; no complete CPU restore acceptance',
                   fresh_continuations=18, backends=results, level1_verified=False, level2_verified=False,
                   inputs_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (out / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (args.out.resolve() / 'latest.json').write_text(json.dumps(dict(summary=str(out / 'summary.json')), indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
