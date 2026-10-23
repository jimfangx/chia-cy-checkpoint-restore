"""Replay complete mapped Rocket CPU windows in fresh ordinary RTL VCS.

Source both repository environments and vcs-env.sh LAST. Capture is a separate
native exact-recipe metasim invocation; no Level-1 profile is admitted here.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from tools.checkpoint_formats.codec import FormatError, decode, encode, require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.fame_event import audit_event_boundary, package_window
from tools.checkpoint_formats.multiclock_inventory import access_paths
from tools.checkpoint_formats.multiclock_replay import prepare_replay
from tools.checkpoint_formats.replay import builds
from tools.checkpoint_formats.tests.verify_multiclock_replay_vcs import compile_native
from tools.checkpoint_formats.tests.verify_semantic_fame_map_vcs import read_inputs
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CONFIGURATION = 'firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3'


def read_snapshot(manifest, mapping, path):
    rows = path.read_text().splitlines(); values = []; index = 0
    for e, binding in zip(manifest['state'], mapping['state']):
        for address in range(e['depth']):
            require(index < len(rows), 'incomplete captured source snapshot')
            fields = rows[index].split(); index += 1
            expected = 'emul.' + binding['rtl_path'] + (f'[{address}]' if e['kind'] == 'memory' else '')
            require(len(fields) == 3 and fields[:2] == [expected, str(e['width'])], 'wrong captured source owner/width')
            values.append(fields[2])
    require(index == len(rows), 'extra captured snapshot words')
    return values


def instrument_case(case, manifest, boundary, access, clean, stats):
    """Four real CSR stored-bit faults plus atomic malformed native-loader cases."""
    paths = access_paths(manifest, boundary, clean, access)
    source = (case / 'replay.sv').read_text()
    declarations = 'integer fault_hart = -1; string invalid_file;'
    source = source.replace('integer edges = 0;', declarations + '\ninteger edges = 0;', 1)
    # Baseline is complete, including exact initialized external plusarg owners.
    defaults = {m['hierarchy'] + '.myplus': m['default'] for m in manifest['external_models']}
    baseline = []
    for e in manifest['state']:
        for address in range(e['depth']):
            path = paths[e['state_id']] + (f'[{address}]' if e['kind'] == 'memory' else '')
            baseline.append(f"event_replay_tb.dut.{path} {e['width']} {defaults.get(e['hierarchy'], 0):0{(e['width']+3)//4}x}")
    (case / 'baseline.txt').write_text('\n'.join(baseline) + '\n')
    clocks = [c[len(manifest['dut_root']) + 1:] for c in manifest['clock_inputs']]
    branch = ['  if ($value$plusargs("invalid=%s", invalid_file)) begin',
              f'    if (semantic_verify("{case / "baseline.txt"}", {stats["words"]})) semantic_fail("INVALID_BASELINE_ERROR");',
              f'    if (!semantic_restore(invalid_file, {stats["words"]})) semantic_fail("INVALID_LOADER_ACCEPTED");',
              f'    if (semantic_verify("{case / "baseline.txt"}", {stats["words"]})) semantic_fail("PARTIAL_INVALID_DEPOSIT");',
              '    if (edges || ' + ' || '.join(clocks) + ') semantic_fail("INVALID_LOAD_ADVANCED_CLOCK");',
              '    $display("PASS: invalid loader preserved complete baseline edges=0"); $finish;', '  end']
    source = source.replace('  if (semantic_restore(', '\n'.join(branch) + '\n  if (semantic_restore(', 1)
    fault_paths = []
    for hart in range(4):
        domain = 'tile_prci_domain' + (f'_{hart}' if hart else '')
        hierarchy = manifest['dut_root'] + f'.system.{domain}.element_reset_domain.rockettile.core.csr.small_1'
        owners = [e for e in manifest['state'] if e['hierarchy'] == hierarchy]
        require(len(owners) == 1 and owners[0]['width'] == 6 and owners[0]['kind'] == 'register',
                'Rocket CSR fault owner changed; audit it explicitly')
        fault_paths.append(paths[owners[0]['state_id']])
    fault = ['  if ($value$plusargs("fault_hart=%d", fault_hart)) begin', '    case (fault_hart)']
    fault += [f"    {i}: dut.{p} = dut.{p} ^ 6'h1;" for i, p in enumerate(fault_paths)]
    fault += ['    default: semantic_fail("UNKNOWN_FAULT_HART");', '    endcase', '  end']
    source = source.replace('  // POST_READBACK_FAULT_INSERTION', '\n'.join(fault))
    (case / 'replay.sv').write_text(source)
    return fault_paths


def invalid_images(case, out, manifest, boundary, clean, access, data, trace):
    rtl_build, trace_build = builds(manifest, boundary, CONFIGURATION)
    good = decode(data, 'rtlckpt', rtl_build)
    corrupted = bytearray(data); corrupted[-1] ^= 1
    variants = [('truncated', data[:-1], trace), ('checksum', bytes(corrupted), trace)]
    for name, mutate in [('incompatible-build', lambda d: d['build'].update(rtl_build_hash='f'*64)),
                         ('missing-owner', lambda d: d['records'].pop()),
                         ('unknown-owner', lambda d: d['records'][0].update(state_id='0'*64))]:
        bad = copy.deepcopy(good); mutate(bad); bad['records'].sort(key=lambda e: e['state_id'])
        variants.append((name, encode('rtlckpt', bad), trace))
    for name, mutate in [('missing-output', lambda t: t['records'][0]['outputs'].pop(next(iter(t['records'][0]['outputs'])))),
                         ('unknown-input', lambda t: t['records'][0]['inputs'].update(unknown=dict(width=1, value='0')))]:
        bad = decode(trace, 'trace', trace_build); mutate(bad)
        variants.append((name, data, encode('trace', bad)))
    result = []
    for name, bad, bad_trace in variants:
        reject = out / (case.name + '-reject-' + name)
        try:
            prepare_replay(manifest, boundary, CONFIGURATION, clean, access, bad, bad_trace, reject)
        except FormatError as exc:
            require(not reject.exists(), 'invalid image partially published native restore inputs')
            result.append(dict(name=name, error=str(exc), published=False))
        else:
            raise AssertionError('invalid CPU image admitted: ' + name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--capture', type=Path, required=True, help='Prefix of complete .C.state and .C.jsonl files')
    parser.add_argument('--cuts', required=True)
    parser.add_argument('--events', type=int, default=64)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME and
            os.environ.get('CC') == _toolchain.CC and os.environ.get('CXX') == _toolchain.CXX,
            'source both environments and vcs-env.sh LAST')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    tmp = out / 'vcs-tmp'; tmp.mkdir(); os.environ['TMPDIR'] = str(tmp)
    paths, text, docs, mapping_report = read_inputs(args.base.resolve())
    manifest, boundary = docs['manifest'], docs['boundary']
    binding = audit_event_boundary(manifest, boundary, docs['mapping'], docs['generated'], text['rtl'], text['bufgce'], text['gate'])
    archive = out / 'inputs'; archive.mkdir(); inputs = {}
    source_paths = list(paths.values()) + [Path(__file__).resolve(), ROOT / 'tools/checkpoint_formats/fame_event.py',
        ROOT / 'tools/checkpoint_formats/fame_capture.cc', ROOT / 'tools/checkpoint_formats/multiclock_replay.py',
        ROOT / 'tools/checkpoint_formats/codec.py', ROOT / 'tools/checkpoint_formats/semantic.py',
        ROOT / 'tools/checkpoint_formats/multiclock_inventory.py']
    cuts = [int(c) for c in args.cuts.split(',')]
    require(cuts == sorted(set(cuts)) and args.events > 0, 'invalid captured CPU cuts')
    source_paths += [Path(str(args.capture.resolve()) + f'.{c}.{suffix}') for c in cuts for suffix in ('state', 'jsonl')]
    for index, path in enumerate(source_paths):
        saved = archive / (f'{index:03d}-' + path.name); shutil.copyfile(path, saved)
        inputs[str(path)] = dict(path=str(saved), sha256=file_sha(saved))
    summary = dict(status='in_progress', scope='captured complete CPU semantic windows; full CPU milestone pending',
                   artifact_root=str(out), binding=binding, mapping=mapping_report, cuts=[], archived_inputs=inputs,
                   CPU_level1_verified=False, CPU_level2_verified=False)
    report = out / 'summary.json'
    report.write_text(json.dumps(summary, indent=2) + '\n')
    for cycle in cuts:
        state_path = Path(str(args.capture.resolve()) + f'.{cycle}.state')
        trace_path = Path(str(args.capture.resolve()) + f'.{cycle}.jsonl')
        rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
        require(len(rows) == args.events and rows[0]['cycle'] == cycle, 'incomplete/mislabeled captured CPU window')
        values = read_snapshot(manifest, docs['mapping'], state_path)
        data, trace = package_window(manifest, boundary, CONFIGURATION, rows, values)
        case = out / f'cut-{cycle}'
        stats = prepare_replay(manifest, boundary, CONFIGURATION, text['clean'], docs['access'], data, trace, case)
        (case / 'capture.rtlckpt').write_bytes(data); (case / 'capture.trace').write_bytes(trace)
        fault_paths = instrument_case(case, manifest, boundary, docs['access'], text['clean'], stats)
        build = compile_native(case, paths['clean'], case / 'replay.sv', 'event_replay_tb')
        argv = [str(case / 'simv'), '-no_save', '+vcs+initreg+0', '+vcs+initmem+0']
        log = run(argv, case / 'run.log')
        require(_toolchain.VCS_VERSION in log and f'ZERO_EDGE_READBACK words={stats["words"]} edges=0' in log and
                log.count('MATCH event=') == args.events and f'acknowledged={args.events}' in log and
                'PASS: event replay' in log, 'incomplete captured CPU finite replay')
        faults = []
        for hart, path in enumerate(fault_paths):
            fault_argv = argv + [f'+fault_hart={hart}']; logpath = case / f'fault-{hart}.log'
            log = run(fault_argv, logpath, expected=None)
            mismatch = re.findall(r'DIVERGENCE event=(\d+) cycle=(\d+) signal=(\S+).* acknowledged=(\d+)', log)
            require(mismatch == [(str(stats['first_event']), str(cycle), f'trace_traces_{hart}_trace_time', '0')]
                    and 'MATCH event=' not in log, 'semantic corruption did not stop at its first original boundary')
            faults.append(dict(hart=hart, path=path, first_event=stats['first_event'], first_target_cycle=cycle,
                               argv=fault_argv, log=str(logpath)))
        lines = (case / 'restore.txt').read_text().splitlines(); native_invalid = []
        for name, bad in [('missing', lines[:-1]), ('duplicate', lines[:-1] + lines[:1]),
                          ('unknown', lines[:-1] + ['event_replay_tb.dut.unknown 1 0']),
                          ('width', lines[:-1] + [lines[-1].split()[0] +
                            f' {int(lines[-1].split()[1]) + 1} ' + '0' * ((int(lines[-1].split()[1]) + 4) // 4)])]:
            invalid = case / (name + '.txt'); invalid.write_text('\n'.join(bad) + '\n')
            invalid_argv = argv + ['+invalid=' + str(invalid)]; logpath = case / (name + '.log')
            log = run(invalid_argv, logpath)
            require('PASS: invalid loader preserved complete baseline edges=0' in log and 'RESTORE: deposited' not in log,
                    'native invalid loader changed semantic storage')
            native_invalid.append(dict(name=name, argv=invalid_argv, log=str(logpath)))
        negatives = invalid_images(case, out, manifest, boundary, text['clean'], docs['access'], data, trace)
        summary['cuts'].append(dict(stats, cycle=cycle, directory=str(case), build_command=build, argv=argv,
                                    faults=faults, native_invalid=native_invalid, invalid_images=negatives,
                                    captured_state=str(state_path), captured_trace=str(trace_path)))
        report.write_text(json.dumps(summary, indent=2) + '\n')
    for path, row in inputs.items():
        require(file_sha(path) == file_sha(row['path']) == row['sha256'], 'capture/replay input changed during validation')
    summary['status'] = 'passed'
    summary['artifacts'] = {str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p != report}
    report.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(status='passed', summary=str(report), cuts=len(cuts), semantic_words=binding['semantic_words'])))


if __name__ == '__main__':
    main()
