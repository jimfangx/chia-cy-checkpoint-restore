"""Native microtest of the exact init-only plusarg state adapter.

This verifies generated-RTL ownership and zero-edge fresh-process deposits for
this external model only. It is not a CPU .fsckpt loader or CPU acceptance.
Source both env.sh files and vcs-env.sh LAST before running this module.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.simulator import check_generated_rtl, validate_generated_manifest

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='native-', dir=args.out.resolve()))
    require(os.environ['VCS_HOME'] == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    manifest = json.loads(args.inventory.read_text())
    validate_generated_manifest(manifest)
    require(manifest['root_module'] == 'Top' and len(manifest['state']) == 2, 'requires compiler plusarg fixture')
    require(all(e['adapter'] == 'metasim-plusarg-v1' for e in manifest['state']), 'unexpected state owner')
    model_path = ROOT / 'generators/rocket-chip/src/main/resources/vsrc/plusarg_reader.v'
    model = model_path.read_text()
    owners = {i['hierarchy']: i['external_adapter'] for i in manifest['instances'] if 'external_adapter' in i}
    declarations, instances = [], []
    for name, adapter in owners.items():
        leaf = name.split('.')[-1]
        declarations.append(f"wire [{adapter['width']-1}:0] {leaf}_out;")
        instances.append('plusarg_reader #(.DEFAULT(%d), .WIDTH(%d), .FORMAT(%s)) %s (.out(%s_out));' %
                         (adapter['default'], adapter['width'], json.dumps(adapter['format']), leaf, leaf))
    rtl = '\n'.join(['module Top();', *declarations, *instances, 'endmodule', model])
    reference = args.reference.read_text()
    check_generated_rtl(manifest, reference, rtl, '', plusarg_model=model)
    rejected = []
    for label, mutate in (
        ('missing-owner', lambda d: d['instances'].pop()),
        ('missing-storage', lambda d: d['state'].pop()),
        ('changed-format', lambda d: next(i['external_adapter'] for i in d['instances']
                                         if 'external_adapter' in i).update(format='different=%d')),
    ):
        altered = copy.deepcopy(manifest)
        mutate(altered)
        try:
            check_generated_rtl(altered, reference, rtl, '', plusarg_model=model)
        except FormatError:
            rejected.append(label)
        else:
            raise AssertionError('accepted ' + label)
    (out / 'Top.sv').write_text(rtl)
    commands = []

    def run(argv, label, expected=0):
        result = subprocess.run([str(a) for a in argv], cwd=out, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (out / (label + '.log')).write_text(result.stdout)
        commands.append(dict(argv=[str(a) for a in argv], cwd=str(out), expected_exit=expected, exit=result.returncode))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require(result.returncode == expected, f'{label} failed: see {out / (label + ".log")}')
        return result.stdout

    paths = [e['hierarchy'].replace('Top.', 'dut.', 1) for e in manifest['state']]
    width = [e['width'] for e in manifest['state']]
    capture = ['module test;', 'Top dut();', 'integer fd; initial begin #1;',
               'fd = $fopen("capture.txt", "w"); if (!fd) $fatal(1, "capture open");']
    capture += [f'$fdisplay(fd, "%h", {p});' for p in paths]
    capture += ['$fclose(fd); $display("PASS: actual plusarg storage captured"); $finish; end endmodule']
    def write_bench(name, lines):
        # VCS may return zero for $fatal; use the established native failure
        # adapter so a real divergence also fails shell/CI execution.
        source = '\n'.join(lines).replace('module test;', 'module test;\n' +
            'import "DPI-C" context function void semantic_fail(input string message);')
        source = source.replace('$fatal(1, ', 'semantic_fail(')
        (out / name).write_text(source + '\n')

    write_bench('capture.sv', capture)
    vcs = Path(os.environ['VCS_HOME']) / 'bin/vcs'

    def build(bench, binary):
        run([vcs, '-full64', '-sverilog', '-timescale=1ns/1ps', '-debug_access+all', '+vpi',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             '-CFLAGS', '-std=c++17 -I' + os.environ['VCS_HOME'] + '/include', '-top', 'test',
             '-Mdir=' + str(out / (binary + '.csrc')), '-o', out / binary,
             out / 'Top.sv', out / bench, ROOT / 'tools/checkpoint_formats/semantic_restore.cc'], 'build-' + binary)

    build('capture.sv', 'capture-simv')
    run([out / 'capture-simv', '-no_save', '+max_core_cycles=305419896', '+custom_boot_pin=1'], 'capture')
    values = [int(v, 16) for v in (out / 'capture.txt').read_text().splitlines()]
    expected = [305419896 if w == 32 else 1 for w in width]
    require(values == expected, 'did not capture actual nondefault plusarg storage')
    restore = ['module test;', 'Top dut();', 'integer boundary; initial begin #1;']
    for p, w, v in zip(paths, width, values):
        restore += [f'if ({p} === {w}\'h{v:x}) $fatal(1, "conflicting startup plusarg missing");',
                    f'{p} = {w}\'h{v:x};']
    restore += ['#0;']
    for p, w, v in zip(paths, width, values):
        restore += [f'if ({p} !== {w}\'h{v:x}) $fatal(1, "zero-edge readback {p}");']
    restore += ['$display("READBACK: 2 complete words before any edge");',
                f'if ($test$plusargs("corrupt")) {paths[0]} = {paths[0]} ^ 1;',
                'for (boundary = 0; boundary < 4; boundary = boundary + 1) begin #0;']
    for p, w, v in zip(paths, width, values):
        output = p.rsplit('.', 1)[0] + '.out'
        restore += [f'if ({output} !== {w}\'h{v:x}) begin',
                    f'$display("FIRST_DIVERGENCE: boundary=%0d signal={output} edges=0", boundary);',
                    '$fatal(1, "plusarg model divergence"); end']
    restore += ['#1; end', '$display("PASS: fresh plusarg restore stable boundaries=4 edges=0");',
                '$finish; end endmodule']
    write_bench('restore.sv', restore)
    build('restore.sv', 'restore-simv')
    startup = ['+max_core_cycles=8', '+custom_boot_pin=0']
    text = run([out / 'restore-simv', '-no_save', *startup], 'fresh-restore')
    require('READBACK: 2 complete words before any edge' in text and
            'PASS: fresh plusarg restore stable boundaries=4 edges=0' in text, 'incomplete native readback')
    text = run([out / 'restore-simv', '-no_save', *startup, '+corrupt'], 'corrupt', expected=1)
    require('FIRST_DIVERGENCE: boundary=0 signal=' in text and 'edges=0' in text and
            'PASS: fresh plusarg restore' not in text, 'first boundary corruption not detected')
    inputs = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (args.inventory, args.reference, model_path, Path(__file__), out / 'Top.sv',
                        ROOT / 'tools/checkpoint_formats/semantic_restore.cc', out / 'capture.sv', out / 'restore.sv')}
    summary = dict(status='passed', scope='plusarg_adapter_microtest_only_not_CPU_checkpoint_acceptance',
                   words=2, bits=sum(width), fresh_process=True, edges_before_readback=0,
                   conflicting_startup_plusargs=True, stable_boundaries=4, first_corrupt_boundary=0,
                   inventory_rejections=rejected, inputs_sha256=inputs, output=str(out), commands=commands)
    (out / 'summary.json').write_bytes(canonical(summary))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
