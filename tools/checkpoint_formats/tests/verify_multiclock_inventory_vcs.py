"""Native ordinary RTL VCS discovery probe, not CPU checkpoint acceptance.

Audit actual emitted storage/clock ownership, resolve and deposit every word,
then independently read back all words with every clock low and zero edges.
Values are diagnostic patterns, not a workload checkpoint or a replay trace.
Run with both environments sourced and vcs-env.sh LAST.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.multiclock_inventory import access_paths, audit_inventory
from tools.checkpoint_formats.replay import state_words
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True, help='Prefix of compiler-emitted .semantic-* files.')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    temporary = out / 'vcs-tmp'; temporary.mkdir(); os.environ['TMPDIR'] = str(temporary)
    inputs = {kind: Path(str(args.base.resolve()) + '.semantic-' + suffix) for kind, suffix in
              [('manifest', 'state.json'), ('boundary', 'boundary.json'), ('reference', 'reference.fir'),
               ('clean', 'clean.sv'), ('access', 'clean-access.json')]}
    manifest = json.loads(inputs['manifest'].read_text()); boundary = json.loads(inputs['boundary'].read_text())
    clean = inputs['clean'].read_text(); access = json.loads(inputs['access'].read_text())
    report = audit_inventory(manifest, boundary, inputs['reference'].read_text(), clean, access)
    (out / 'independent-inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    clocks = [c[len(manifest['dut_root']) + 1:] for c in manifest['clock_inputs']]
    words = list(state_words(manifest))
    paths = access_paths(manifest, boundary, clean, access)
    for word in words:
        # Avoid searching the full CPU inventory once per memory word.
        word['path'] = paths[word['state_id']] + (f"[{word['address']}]" if '[' in word['path'] else '')
    initial = {m['hierarchy'][len(manifest['dut_root']) + 1:] + '.myplus': m['default'] for m in manifest['external_models']}
    valid, baseline = [], []
    for word in words:
        # Exercise all stored bits, including upper lanes, without materializing
        # an unaudited multi-clock .rtlckpt or assigning a fictitious cycle label.
        width = word['width']; count = (width + 3) // 4
        seed = hashlib.shake_256(word['path'].encode()).digest((width + 7) // 8)
        value = int.from_bytes(seed, 'little') & ((1 << width) - 1)
        valid.append(f"inventory_probe_tb.dut.{word['path']} {width} {value:0{count}x}")
        baseline.append(f"inventory_probe_tb.dut.{word['path']} {width} {initial.get(word['path'], 0):0{count}x}")
    baseline_path = out / 'initial-baseline.txt'; baseline_path.write_text('\n'.join(baseline) + '\n')
    valid_path = out / 'complete-pattern.txt'; valid_path.write_text('\n'.join(valid) + '\n')
    fault_word = next(w for w in words if w['path'] not in initial and '[' not in w['path'])
    source = ['`timescale 1ns/1ps', 'module inventory_probe_tb;',
              'import "DPI-C" context function int semantic_restore(input string path, input int unsigned expected_words);',
              'import "DPI-C" context function int semantic_verify(input string path, input int unsigned expected_words);',
              'import "DPI-C" context function void semantic_fail(input string message);',
              'integer edges = 0; string pattern, baseline; bit invalid, corrupt;']
    for clock in clocks:
        source += [f'reg {clock} = 0;', f'always @(posedge {clock}) edges = edges + 1;']
    for port in boundary['ports']:
        source.append(f"{'reg' if port['direction'] == 'input' else 'wire'} [{port['width'] - 1}:0] {port['name']}" +
                      (' = 0;' if port['direction'] == 'input' else ';'))
    source += [f"wire {alias['name']};" for alias in boundary['clock_aliases']]
    names = clocks + [p['name'] for p in boundary['ports']] + [a['name'] for a in boundary['clock_aliases']]
    source += [boundary['dut_module'] + ' dut(' + ', '.join(f'.{n}({n})' for n in names) + ');',
               'initial begin', '  invalid = $test$plusargs("invalid"); corrupt = $test$plusargs("corrupt");',
               '  if (!$value$plusargs("pattern=%s", pattern) || !$value$plusargs("baseline=%s", baseline)) semantic_fail("MISSING_PROBE_FILES");',
               '  #1;',
               f'  if (semantic_verify(baseline, {len(words)})) semantic_fail("BASELINE_READBACK_ERROR");',
               '  if (invalid) begin',
               f'    if (!semantic_restore(pattern, {len(words)})) semantic_fail("INVALID_PROBE_ACCEPTED");',
               f'    if (semantic_verify(baseline, {len(words)})) semantic_fail("PARTIAL_DEPOSIT_FROM_INVALID_PROBE");',
               '  end else begin',
               f'    if (semantic_restore(pattern, {len(words)})) semantic_fail("PATTERN_DEPOSIT_ERROR");',
               '    #1;',
               f'    if (semantic_verify(pattern, {len(words)})) semantic_fail("COMPLETE_PATTERN_READBACK_ERROR");',
               '    if (corrupt) begin',
               f"      dut.{fault_word['path']} = dut.{fault_word['path']} ^ {fault_word['width']}'h1;",
               f'      if (!semantic_verify(pattern, {len(words)})) semantic_fail("CORRUPT_STORAGE_UNDETECTED");',
               '    end', '  end',
               '  if (edges || ' + ' || '.join(clocks) + ') semantic_fail("INVENTORY_PROBE_ADVANCED_CLOCKS");',
               f'  $display("PASS: inventory probe words={len(words)} clocks={len(clocks)} edges=%0d invalid=%0d corrupt=%0d", edges, invalid, corrupt);',
               '  $finish;', 'end', 'endmodule']
    bench = out / 'probe.sv'; bench.write_text('\n'.join(source) + '\n')
    loader = ROOT / 'tools/checkpoint_formats/semantic_restore.cc'
    vcs = Path(os.environ['VCS_HOME']) / 'bin/vcs'
    command = [vcs, '-full64', '-sverilog', '-debug_access+all', '+vpi', '+vcs+initreg+random',
               '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-CFLAGS',
               '-std=c++17 -I' + os.environ['VCS_HOME'] + '/include', '-timescale=1ns/1ps', '-top', 'inventory_probe_tb',
               f'-Mdir={out / "csrc"}', '-o', out / 'simv', inputs['clean'], bench, loader]
    run(command, out / 'build.log')
    cases = [('complete', valid_path, []), ('corrupt-storage', valid_path, ['+corrupt'])]
    for name, lines in [('missing-word', valid[:-1]), ('duplicate-word', valid[:-1] + [valid[0]]),
                        ('unknown-word', valid[:-1] + ['inventory_probe_tb.dut.unknown 1 0']),
                        ('wrong-width', valid[:-1] + [valid[-1].split()[0] +
                         f" {words[-1]['width'] + 1} " + '0' * ((words[-1]['width'] + 4) // 4)])]:
        path = out / (name + '.txt'); path.write_text('\n'.join(lines) + '\n'); cases.append((name, path, ['+invalid']))
    results = []
    for name, path, options in cases:
        argv = [out / 'simv', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
                '+pattern=' + str(path), '+baseline=' + str(baseline_path), *options]
        text = run(argv, out / (name + '.log'))
        require(f'PASS: inventory probe words={len(words)} clocks={len(clocks)} edges=0' in text and
                _toolchain.VCS_VERSION in text, 'incomplete native ownership probe')
        require(text.count('RESTORE: deposited') == (0 if '+invalid' in options else 1), 'invalid probe partially deposited')
        results.append(dict(name=name, argv=[str(a) for a in argv], log=str(out / (name + '.log'))))
    paths = list(inputs.values()) + [bench, loader, Path(__file__).resolve(),
             ROOT / 'tools/checkpoint_formats/multiclock_inventory.py', ROOT / 'tools/checkpoint_formats/semantic.py',
             ROOT / 'tools/checkpoint_formats/replay.py', ROOT / 'tools/checkpoint_formats/codec.py']
    snapshots = out / 'inputs'; snapshots.mkdir()
    archived = {}
    for index, path in enumerate(paths):
        saved = snapshots / (f'{index:03d}-' + path.name); shutil.copyfile(path, saved)
        archived[str(path)] = dict(path=str(saved), sha256=file_sha(saved))
    summary = dict(report, scope='native ordinary RTL diagnostic inventory probe; no workload checkpoint/trace',
                   base=str(args.base.resolve()), artifact_root=str(out), vcs_home=os.environ['VCS_HOME'],
                   build_command=[str(a) for a in command], cases=results, archived_inputs=archived,
                   required_CPU_checkpoint_cuts_tested=False, CPU_level1_verified=False, CPU_level2_verified=False)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(status='passed', summary=str(out / 'summary.json'), words=len(words),
                          clock_inputs=len(clocks), zero_edge_only=True, CPU_level1_verified=False, CPU_level2_verified=False), indent=2))


if __name__ == '__main__':
    main()
