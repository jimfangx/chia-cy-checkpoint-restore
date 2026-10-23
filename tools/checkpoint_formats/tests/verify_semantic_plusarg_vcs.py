"""Native ordinary RTL capture and fresh restore of exact semantic plusarg owners.

Consume actual Scala-emitted IR/RTL. Capture default and nondefault initialized
values, terminate the source, and override conflicting fresh-process plusargs
with the complete semantic image before any edge. This is component evidence,
not complete Rocket checkpoint acceptance. Source both environments, then
vcs-env.sh LAST before invoking this module.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from tools.checkpoint_formats.codec import FormatError, encode, require
from tools.checkpoint_formats.replay import package_capture, prepare_capture, prepare_replay, read_json
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run, verify_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scala-artifacts', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--clock-pin', action='store_true', help='Use the exact parent input-clock fanout compiler fixture.')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    # Independent native builds may see the same process ID in tool namespaces.
    # Give VCS a retained invocation-specific temporary root, preventing its
    # timestamp/PID directory from colliding with another compiler process.
    temporary = out / 'vcs-tmp'
    temporary.mkdir()
    os.environ['TMPDIR'] = str(temporary)
    base = args.scala_artifacts.resolve() / ('semantic-plusarg-clock-pin' if args.clock_pin else 'semantic-plusarg')
    manifest = read_json(str(base) + '.semantic-state.json')
    boundary = read_json(str(base) + '.semantic-boundary.json')
    clean = Path(str(base) + '.semantic-clean.sv')
    if args.clock_pin:
        require('always @(posedge relay_clock)' in clean.read_text() and '.clock(relay_clock)' in clean.read_text(),
                'missing actual child input-clock fanout')
    require(manifest['manifest_version'] == 2 and len(manifest['state']) == 5 and
            len(manifest['external_models']) == 4, 'changed complete compiler external ownership')
    require({m['hierarchy']: m['width'] for m in manifest['external_models']} ==
            {'Top.a': 32, 'Top.relay.a': 32, 'Top.b': 1, 'Top.w': 65}, 'changed specialized/nested owners')
    vcs = Path(os.environ['VCS_HOME']) / 'bin/vcs'
    require(str(vcs) == _toolchain.VCS, 'source vcs-env.sh LAST')
    ops = [(1, 0), (1, 7), (0, 3), (0, 0xffffffff), (0, 2), (0, 0), (0, 19),
           (0, 37), (0, 100), (0, 11), (0, 0), (0, 0x80000000), (0, 9), (0, 17),
           (0, 1), (0, 0), (0, 0x12345678)]
    results = []
    variants = [('defaults', (7, 0, 9), []),
                ('nondefault', (305419896, 1, 0x1edcba9876543210f),
                 ['+semantic_limit=305419896', '+semantic_flag=1', '+semantic_wide=1edcba9876543210f'])]
    for name, (limit, flag, wide), source_args in variants:
        case = out / name
        case.mkdir()
        bench = ['`timescale 1ns/1ps', 'module source_tb;',
                 'import "DPI-C" context function void semantic_fail(input string message);',
                 'reg clock = 0; reg reset = 0; reg [31:0] data = 0;',
                 'wire [31:0] result, repeated, count; wire flag; wire [64:0] wide;',
                 'Top dut(.clock(clock), .reset(reset), .data(data), .result(result), .repeated(repeated),',
                 '        .count(count), .flag(flag), .wide(wide));', 'initial begin']
        count = 0
        for cycle, (reset, data) in enumerate(ops):
            value = (count + limit) & 0xffffffff
            bench += [f"  reset = {reset}; data = 32'h{data:x}; #1;",
                      f"  if (result !== 32'h{value:x} || repeated !== 32'h{value:x} || count !== 32'h{count:x} ||",
                      f"      flag !== 1'b{flag} || wide !== 65'h{wide:x}) semantic_fail(\"SOURCE_WORKLOAD cycle={cycle}\");",
                      '  clock = 1; #1; clock = 0; #1;']
            count = 0 if reset else (count + data) & 0xffffffff
        bench += ['$display("PASS: self-checking ordinary initialized-owner workload"); $finish;', 'end', 'endmodule']
        text = '\n'.join(bench) + '\n'
        (case / 'source.sv').write_text(text)
        fields = prepare_capture(manifest, boundary, clean.read_text(), clean.read_text() + text, case)
        run([vcs, '-full64', '-sverilog', '-debug_access+all', '+vpi', '+vcs+initreg+random',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-CFLAGS',
             '-std=c++17 -I' + os.environ['VCS_HOME'] + '/include', '-timescale=1ns/1ps', '-top', 'source_tb',
             f'-Mdir={case / "source-csrc"}', '-o', case / 'source-simv',
             clean, case / 'source.sv', case / 'capture.sv', ROOT / 'tools/checkpoint_formats/semantic_restore.cc'],
            case / 'source-build.log')
        run([case / 'source-simv', '-no_save', '+vcs+initreg+0', *source_args,
             f'+semantic_capture={case / "capture.jsonl"}'], case / 'source-run.log')
        rows = [json.loads(line) for line in (case / 'capture.jsonl').read_text().splitlines()]
        require(len(rows) == len(ops), 'lost source boundary')
        count = 0
        for cycle, (row, (reset, data)) in enumerate(zip(rows, ops)):
            values = {f['path']: int(v, 16) for f, v in zip(fields, row['values'])}
            require(row['cycle'] == cycle and values ==
                    dict(data=data, reset=reset, count=count, result=(count + limit) & 0xffffffff,
                         repeated=(count + limit) & 0xffffffff, flag=flag, wide=wide, counter=count,
                         **{'a.myplus': limit, 'relay.a.myplus': limit, 'b.myplus': flag, 'w.myplus': wide}),
                    'independent complete initialized-state/cycle/output recurrence failed')
            count = 0 if reset else (count + data) & 0xffffffff
        conflicting = ['+semantic_limit=42', '+semantic_flag=' + str(1 - flag), '+semantic_wide=1']
        cuts = []
        for cycle in (0, 3, 9, 16):
            restore = case / f'cut-{cycle}'
            package_capture(manifest, boundary, name, case / 'capture.jsonl', cycle, len(rows) - cycle, restore)
            log = verify_case(vcs, clean, manifest, boundary, restore, configuration=name,
                              monitor_edges=True, runtime_args=conflicting, flush_waveform=True)
            require('RESTORE: deposited 5 semantic words before first DUT edge' in log and
                    log.count('ACKNOWLEDGED_TARGET_EDGE') == len(rows) - cycle, 'missing complete zero-edge restore')
            cuts.append(dict(cycle=cycle, samples=len(rows) - cycle, directory=str(restore)))
        faults = []
        for owner, width, output in (('a.myplus', 32, 'result'), ('relay.a.myplus', 32, 'repeated'),
                                     ('b.myplus', 1, 'flag'), ('w.myplus', 65, 'wide')):
            fault = case / ('fault-' + owner.replace('.', '-'))
            package_capture(manifest, boundary, name, case / 'capture.jsonl', 9, len(rows) - 9, fault)
            log = verify_case(vcs, clean, manifest, boundary, fault, expected=None, configuration=name,
                              post_restore_checks=f"  dut.{owner} = dut.{owner} ^ {width}'h1;",
                              monitor_edges=True, runtime_args=conflicting, flush_waveform=True)
            require('RESTORE: deposited 5 semantic words before first DUT edge' in log and
                    f'FIRST_MISMATCH cycle=9 signal={output}' in log and log.count('FIRST_MISMATCH') == 1 and
                    'ACKNOWLEDGED_TARGET_EDGE' not in log, 'corruption did not reject at first divergent boundary')
            faults.append(dict(owner=owner, cycle=9, signal=output, directory=str(fault)))
        original, trace = package_capture(manifest, boundary, name, case / 'capture.jsonl', 9, len(rows) - 9,
                                          case / 'negative-source')
        image = (case / 'negative-source/capture.rtlckpt').read_bytes()
        altered = copy.deepcopy(original)
        altered['records'] = [r for r in altered['records'] if r['state_id'] !=
                              next(e['state_id'] for e in manifest['state'] if e['hierarchy'] == 'Top.a.myplus')]
        missing = encode('rtlckpt', altered)
        altered = copy.deepcopy(original)
        altered['build']['rtl_build_hash'] = '0' * 64
        incompatible = encode('rtlckpt', altered)
        altered = copy.deepcopy(original)
        altered['records'][0]['state_id'] = '0' * 64
        altered['records'].sort(key=lambda r: r['state_id'])
        unknown = encode('rtlckpt', altered)
        corrupt = bytearray(image)
        corrupt[-1] ^= 1
        rejected = []
        for label, data in [('truncated', image[:-1]), ('checksum', bytes(corrupt)),
                            ('incompatible-build', incompatible), ('missing-initialized-owner', missing),
                            ('unknown-state-owner', unknown)]:
            dest = case / ('reject-' + label)
            dest.mkdir()
            (dest / 'invalid.rtlckpt').write_bytes(data)
            try:
                prepare_replay(manifest, boundary, name, data,
                               (case / 'negative-source/capture.trace').read_bytes(), dest)
            except FormatError as error:
                (dest / 'rejection.txt').write_text(str(error) + '\n')
                require(not (dest / 'restore.txt').exists() and not (dest / 'replay.sv').exists(),
                        'invalid image published partial restore')
                rejected.append(label)
            else:
                raise AssertionError('accepted ' + label)
        # The actual native loader also prevalidates all handles/rows before
        # depositing any of the earlier valid words.
        native_rejected = []
        valid_case = case / 'cut-9'
        valid_rows = (valid_case / 'restore.txt').read_text().splitlines()
        for label, rows_bad in [('missing-handle', valid_rows[:-1] + ['semantic_replay_tb.dut.absent 1 0']),
                                ('wrong-width', valid_rows[:-1] + [valid_rows[-1].replace(' 65 ', ' 64 ')
                                                                  if ' 65 ' in valid_rows[-1] else
                                                                  re.sub(r' (\d+) ', ' 66 ', valid_rows[-1])]),
                                ('missing-word', valid_rows[:-1]), ('malformed-row', valid_rows + ['bad'])]:
            dest = case / ('native-reject-' + label)
            dest.mkdir()
            (dest / 'restore.txt').write_text('\n'.join(rows_bad) + '\n')
            log = run([valid_case / 'simv', '-no_save', f'+restore={dest / "restore.txt"}',
                       f'+waveform={dest / "waveform.vcd"}', *conflicting], dest / 'run.log', expected=None)
            require('RESTORE_ERROR before first DUT edge' in log and 'RESTORE: deposited' not in log and
                    'ACKNOWLEDGED_TARGET_EDGE' not in log, 'native rejection partially restored/advanced')
            native_rejected.append(label)
        results.append(dict(name=name, values=dict(limit=limit, flag=flag, wide=hex(wide)),
                            source_args=source_args, conflicting_restore_args=conflicting, captured_edges=len(rows),
                            cuts=cuts, faults=faults, invalid_images=rejected, native_loader_rejections=native_rejected))
    inputs = [Path(str(base) + suffix) for suffix in ('.semantic-state.json', '.semantic-boundary.json',
              '.semantic-clean.sv', '.semantic-reference.fir')]
    inputs += [ROOT / 'tools/checkpoint_formats/semantic_restore.cc', ROOT / 'tools/checkpoint_formats/replay.py',
               ROOT / 'tools/checkpoint_formats/semantic.py', Path(__file__),
               ROOT / 'tools/checkpoint_formats/tests/verify_semantic_vcs.py',
               ROOT / 'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SemanticStateInventory.scala',
               ROOT / 'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/SemanticStateInventorySpec.scala',
               ROOT / 'generators/rocket-chip/src/main/resources/vsrc/plusarg_reader.v']
    archive = out / 'inputs'
    archive.mkdir()
    archived = {}
    for index, path in enumerate(inputs):
        target = archive / f'{index:03}-{path.name}'
        shutil.copy2(path, target)
        archived[str(path)] = dict(path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    report = dict(status='passed', scope='ordinary_semantic_initialized_owner_component_not_CPU_acceptance',
                  level1_verified=False, level2_cpu_verified=False, invocation=str(out),
                  clock_pin_fanout=args.clock_pin,
                  owned_words=5, initialized_owners=4, variants=results,
                  archived_inputs=archived,
                  compared_samples=sum(c['samples'] for r in results for c in r['cuts']), outputs_per_cycle=5,
                  inputs_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
