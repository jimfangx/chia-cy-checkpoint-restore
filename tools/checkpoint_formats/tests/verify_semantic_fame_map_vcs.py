"""Native complete storage probe in transformed and ordinary CPU RTL.

Diagnostic values only: no workload checkpoint, coherent event cut or replay.
Source both repository environments and vcs-env.sh LAST before invoking.
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
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.multiclock_inventory import access_paths, audit_inventory
from tools.checkpoint_formats.replay import IDENT, RANGE, modules
from tools.checkpoint_formats.semantic_fame import audit_mapping
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def read_inputs(base):
    paths = {k: Path(str(base) + suffix) for k, suffix in {
        'manifest': '.semantic-state.json', 'boundary': '.semantic-boundary.json',
        'access': '.semantic-clean-access.json', 'clean': '.semantic-clean.sv',
        'semantic_reference': '.semantic-reference.fir', 'mapping': '.semantic-fame-map.json',
        'generated': '.simulator-state.json', 'reference': '.simulator-reference.fir', 'rtl': '.semantic-fame-emitted.sv',
    }.items()}
    paths.update(bufgce=ROOT / 'sims/firesim/sim/midas/src/main/verilog/BUFGCE.v',
                 plusarg=base.parent / 'plusarg_reader.v', gate=base.parent / 'AbstractClockGate.v',
                 loader=ROOT / 'tools/checkpoint_formats/semantic_restore.cc')
    text = {k: p.read_text() for k, p in paths.items()}
    docs = {k: json.loads(text[k]) for k in ('manifest', 'boundary', 'access', 'mapping', 'generated')}
    report = audit_mapping(docs['manifest'], docs['mapping'], docs['generated'],
                           text['reference'], text['rtl'], text['bufgce'], text['plusarg'], text['gate'])
    audit_inventory(docs['manifest'], docs['boundary'], text['semantic_reference'], text['clean'], docs['access'])
    return paths, text, docs, report


def probe(out, kind, paths, text, docs):
    directory = out / kind; directory.mkdir()
    manifest = docs['manifest']
    if kind == 'transformed':
        root = docs['generated']['root_module']
        locations = {e['state_id']: e['rtl_path'][len(root) + 1:] for e in docs['mapping']['state']}
        clocks = [i['hierarchy'][len(root) + 1:] + '.O' for i in docs['generated']['instances']
                  if i['module'] in ('AbstractClockGate', 'BUFGCE')]
        sources = [paths['rtl'], paths['gate'], paths['plusarg'], paths['bufgce']]
    else:
        root = docs['boundary']['dut_module']
        locations = access_paths(manifest, docs['boundary'], text['clean'], docs['access'])
        clocks = [c[len(manifest['dut_root']) + 1:] for c in manifest['clock_inputs']]
        sources = [paths['clean']]
    header = modules(text['rtl'] if kind == 'transformed' else text['clean'])[root][0]
    inputs = [n for d, _, n in re.findall(rf'\b(input|output)\s+{RANGE}({IDENT})', header) if d == 'input']
    plusargs = {e['state_id']: e for e in manifest['state'] if e['clock_domain'] == 'initial'}
    defaults = {e['hierarchy'] + '.myplus': e['default'] for e in manifest['external_models']}
    valid, baseline, ordered = [], [], []
    fault = None
    for e in manifest['state']:
        for address in range(e['depth']):
            path = locations[e['state_id']] + (f'[{address}]' if e['kind'] == 'memory' else '')
            seed = hashlib.shake_256(f"{e['state_id']}:{address}".encode()).digest((e['width'] + 7) // 8)
            value = int.from_bytes(seed, 'little') & ((1 << e['width']) - 1)
            row = f"fame_map_probe_tb.dut.{path} {e['width']} "
            valid.append(row + f"{value:0{(e['width'] + 3) // 4}x}")
            baseline.append(row + f"{defaults.get(e['hierarchy'], 0):0{(e['width'] + 3) // 4}x}")
            ordered.append(dict(state_id=e['state_id'], address=address, width=e['width'], value=value))
            if fault is None and e['state_id'] not in plusargs and e['kind'] == 'register':
                fault = path
    (directory / 'words.json').write_text(json.dumps(ordered) + '\n')
    for name, rows in [('complete', valid), ('baseline', baseline), ('missing', valid[:-1]),
                       ('duplicate', valid[:-1] + valid[:1]), ('unknown', valid[:-1] + ['fame_map_probe_tb.dut.absent 1 0']),
                       ('width', valid[:-1] + [valid[-1].split()[0] + f" {manifest['state'][-1]['width'] + 1} 0"])]:
        (directory / (name + '.txt')).write_text('\n'.join(rows) + '\n')
    source = ['`timescale 1ns/1ps', 'module fame_map_probe_tb;',
              'import "DPI-C" context function int semantic_restore(input string path, input int unsigned expected_words);',
              'import "DPI-C" context function int semantic_verify(input string path, input int unsigned expected_words);',
              'import "DPI-C" context function void semantic_fail(input string message);',
              'integer edges = 0; string pattern, baseline; bit invalid, corrupt;',
              root + ' dut(' + ', '.join(f'.{n}(\'0)' for n in inputs) + ');']
    source += [f'always @(posedge dut.{c}) edges = edges + 1;' for c in clocks]
    source += ['initial begin',
               '  invalid = $test$plusargs("invalid"); corrupt = $test$plusargs("corrupt");',
               '  if (!$value$plusargs("pattern=%s", pattern) || !$value$plusargs("baseline=%s", baseline)) semantic_fail("MISSING_FILES");',
               '  #1;', f'  if (semantic_verify(baseline, {len(valid)})) semantic_fail("BASELINE_ERROR");',
               '  if (invalid) begin',
               f'    if (!semantic_restore(pattern, {len(valid)})) semantic_fail("INVALID_ACCEPTED");',
               f'    if (semantic_verify(baseline, {len(valid)})) semantic_fail("PARTIAL_RESTORE");',
               '  end else begin', f'    if (semantic_restore(pattern, {len(valid)})) semantic_fail("LOAD_ERROR");',
               f'    if (semantic_verify(pattern, {len(valid)})) semantic_fail("READBACK_ERROR");',
               '    if (corrupt) begin', f'      dut.{fault} = dut.{fault} ^ 1;',
               f'      if (!semantic_verify(pattern, {len(valid)})) semantic_fail("CORRUPTION_MISSED");',
               '    end', '  end', '  #1;', '  if (edges) semantic_fail("UNEXPECTED_EDGE");',
               f'  $display("PASS: {kind} semantic map words={len(valid)} edges=0 invalid=%0d corrupt=%0d", invalid, corrupt);',
               '  $finish;', 'end', 'endmodule']
    bench = directory / 'probe.sv'; bench.write_text('\n'.join(source) + '\n')
    command = [Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-debug_access+all',
               '+vpi', '+vcs+initreg+random', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
               '-CFLAGS', '-std=c++17 -I' + os.environ['VCS_HOME'] + '/include',
               '-timescale=1ns/1ps', '-top', 'fame_map_probe_tb', f'-Mdir={directory / "csrc"}',
               '-o', directory / 'simv', *sources, bench, paths['loader']]
    run(command, directory / 'build.log')
    cases = []
    for name in ('complete', 'corrupt', 'missing', 'duplicate', 'unknown', 'width'):
        argv = [directory / 'simv', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
                '+pattern=' + str(directory / (('complete' if name == 'corrupt' else name) + '.txt')),
                '+baseline=' + str(directory / 'baseline.txt')]
        if name == 'corrupt': argv += ['+corrupt']
        elif name != 'complete': argv += ['+invalid']
        log = run(argv, directory / (name + '.log'), cwd=directory)
        require(f'PASS: {kind} semantic map words={len(valid)} edges=0' in log
                and 'Y-2026.03-SP1_Full64' in log, 'incomplete native map probe')
        require(log.count('RESTORE: deposited') == (1 if name in ('complete', 'corrupt') else 0),
                'partial invalid restore')
        require(name != 'corrupt' or 'semantic readback mismatch' in log, 'missed actual storage fault')
        cases.append(dict(name=name, argv=list(map(str, argv)), log=str(directory / (name + '.log'))))
    return dict(kind=kind, words=len(valid), clocks=len(clocks), build_command=list(map(str, command)), cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    temporary = out / 'vcs-tmp'; temporary.mkdir(); os.environ['TMPDIR'] = str(temporary)
    paths, text, docs, report = read_inputs(args.base.resolve())
    snapshots = out / 'inputs'; snapshots.mkdir()
    inputs = {}
    for name, path in {**paths, 'checker': Path(__file__),
                       'auditor': ROOT / 'tools/checkpoint_formats/semantic_fame.py'}.items():
        snapshot = snapshots / (name + '-' + path.name); shutil.copyfile(path, snapshot)
        inputs[str(path.resolve())] = dict(path=str(snapshot), sha256=file_sha(snapshot))
    cases = [probe(out, kind, paths, text, docs) for kind in ('transformed', 'ordinary')]
    require((out / 'transformed/words.json').read_bytes() == (out / 'ordinary/words.json').read_bytes(),
            'independent layouts use different original words')
    report.update(artifact_root=str(out), base=str(args.base.resolve()), native=cases, archived_inputs=inputs,
                  scope='native complete transformed/ordinary diagnostic storage map; CPU capture/replay pending')
    for path, row in inputs.items():
        require(file_sha(path) == row['sha256'], 'source changed during native mapping probe')
    report['artifacts'] = {str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='passed', summary=str(out / 'summary.json'), words=report['semantic_words'])))


if __name__ == '__main__':
    main()
