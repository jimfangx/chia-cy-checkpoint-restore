"""Native ordinary RTL checks of all five exact FIRRTL passthrough policies.

Consume actual Scala inventory artifacts, run a directed memory workload,
capture state/trace, then restore into independent ordinary VCS processes.
The undefined-reader policy is checked here because GG resolves that policy
to read-first; unchanged-hierarchy metasim mapping must reject that change.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.replay import package_capture, prepare_capture, read_json
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run, verify_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scala-artifacts', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    vcs = Path(os.environ['VCS_HOME']) / 'bin/vcs'
    require(str(vcs) == _toolchain.VCS, 'source vcs-env.sh LAST')
    ops = [(1, 1, i, 0x100 + i) for i in range(5)]
    ops += [(1, 0, i, 0) for i in range(5)]
    ops += [(0, 0, 2, 0)] * 3
    ops += [(1, 1, 2, 0x1a2), (1, 0, 2, 0), (1, 1, 2, 0x155)]
    ops += [(0, 0, 4, 0)] * 2 + [(1, 0, 4, 0), (1, 0, 2, 0)]
    results = []
    for port, policy in (('reader', 'old'), ('reader', 'new'), ('reader', 'undefined'),
                         ('readwriter', 'old'), ('readwriter', 'undefined')):
        name = f'{port}-{policy}'
        case = out / name
        case.mkdir(exist_ok=True)
        base = args.scala_artifacts.resolve() / ('semantic-' + name)
        manifest = read_json(str(base) + '.semantic-state.json')
        boundary = read_json(str(base) + '.semantic-boundary.json')
        clean = Path(str(base) + '.semantic-clean.sv')
        field = 'rdata' if port == 'readwriter' else 'data' if policy == 'old' else 'addr'
        saved = 'ram_p_' + field
        width = 3 if field == 'addr' else 9
        require({e['hierarchy']: (e['width'], e['depth'], e['kind']) for e in manifest['state']} ==
                {'Top.ram': (9, 5, 'memory'), 'Top.' + saved: (width, 1, 'register')},
                'changed actual compiler policy ownership')
        bench = ['`timescale 1ns/1ps', 'module source_tb;',
                 'reg clock = 0; reg enable = 0; reg write = 0; reg [2:0] address = 0; reg [8:0] data = 0;',
                 'wire [8:0] result;', 'Top dut(.clock(clock), .enable(enable), .write(write), .address(address), .data(data), .result(result));',
                 'initial begin']
        for en, wr, addr, value in ops:
            bench.append(f'  enable = {en}; write = {wr}; address = 3\'d{addr}; data = 9\'d{value}; #1; clock = 1; #1; clock = 0; #1;')
        bench += ['$display("PASS: directed ordinary memory source"); $finish;', 'end', 'endmodule']
        text = '\n'.join(bench) + '\n'
        (case / 'source.sv').write_text(text)
        fields = prepare_capture(manifest, boundary, clean.read_text(), clean.read_text() + text, case)
        run([vcs, '-full64', '-sverilog', '-debug_access+all', '+vpi', '+vcs+initreg+random', '-cc', os.environ['CC'],
             '-cpp', os.environ['CXX'], '-timescale=1ns/1ps', '-top', 'source_tb',
             f'-Mdir={case / "source-csrc"}', '-o', case / 'source-simv',
             clean, case / 'source.sv', case / 'capture.sv'], case / 'source-build.log')
        run([case / 'source-simv', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
             f'+semantic_capture={case / "capture.jsonl"}'], case / 'source-run.log')
        rows = [json.loads(line) for line in (case / 'capture.jsonl').read_text().splitlines()]
        require(len(rows) == len(ops), 'lost directed source edge')
        memory, pipeline = [0] * 5, 0
        for cycle, (row, op) in enumerate(zip(rows, ops)):
            value = {f['path']: int(v, 16) for f, v in zip(fields, row['values'])}
            en, wr, addr, data = op
            require(row['cycle'] == cycle and [value[k] for k in ('enable', 'write', 'address', 'data')] == list(op),
                    'incorrect source cycle/input labels')
            require([value[f'ram[{i}]'] for i in range(5)] == memory and value[saved] == pipeline,
                    'incorrect complete contents/port recurrence')
            require(value['result'] == (memory[pipeline] if field == 'addr' else pipeline), 'incorrect source output recurrence')
            if en:
                pipeline = addr if field == 'addr' else memory[addr]
            if (en if port == 'readwriter' else True) and wr:
                memory[addr] = data
        cuts = []
        for cycle in (0, 5, 10, 16):
            restore = case / f'cut-{cycle}'
            package_capture(manifest, boundary, name, case / 'capture.jsonl', cycle, len(rows) - cycle, restore)
            log = verify_case(vcs, clean, manifest, boundary, restore, configuration=name, monitor_edges=True)
            require('RESTORE: deposited 6 semantic words before first DUT edge' in log
                    and log.count('ACKNOWLEDGED_TARGET_EDGE') == len(rows) - cycle, 'missing complete zero-edge policy restore')
            cuts.append(dict(cycle=cycle, samples=len(rows) - cycle))
        fault = case / 'pipeline-fault'
        package_capture(manifest, boundary, name, case / 'capture.jsonl', 10, len(rows) - 10, fault)
        # Address four -> zero remains in range for this non-power-of-two RAM.
        mask = 4 if field == 'addr' else 1
        log = verify_case(vcs, clean, manifest, boundary, fault, expected=None, configuration=name,
                          post_restore_checks=f"  dut.{saved} = dut.{saved} ^ {width}'d{mask};",
                          monitor_edges=True)
        require('RESTORE: deposited 6 semantic words before first DUT edge' in log
                and 'FIRST_MISMATCH cycle=10 signal=result' in log
                and log.count('FIRST_MISMATCH') == 1 and 'ACKNOWLEDGED_TARGET_EDGE' not in log,
                'policy pipeline corruption failed to stop at first boundary')
        inputs = [Path(str(base) + s) for s in ('.semantic-clean.sv', '.semantic-state.json',
                                                              '.semantic-boundary.json', '.semantic-reference.fir')]
        results.append(dict(policy=name, words=6, cases=cuts, first_fault=dict(cycle=10, signal='result', acknowledged_edges=0),
                            inputs_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}))
    summary = dict(status='passed', fixture_only=True, CPU_level1_verified=False, CPU_level2_verified=False,
                   ordinary_policies=results)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
