"""Audit original native memory images, readback benches, traces and logs."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import decode, require
from tools.checkpoint_formats.replay import builds, inventory_rtl, modules, read_json, state_words
from tools.checkpoint_formats.semantic import decode_semantic


def check_inputs(hashes):
    for name, digest in hashes.items():
        require(hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, 'changed native input: ' + name)


def check_replay(case, manifest, boundary, configuration, rows, fields, cycle, words, outputs, fault=None):
    rtl_build, trace_build = builds(manifest, boundary, configuration)
    ckpt = decode_semantic((case / 'capture.rtlckpt').read_bytes(), rtl_build, manifest)
    trace = decode((case / 'capture.trace').read_bytes(), 'trace', trace_build)
    require(ckpt['target_cycle'] == trace['target_cycle'] == cycle, 'incorrect restore cycle label')
    values = dict(zip((f['path'] for f in fields), rows[cycle]['values']))
    records = {r['state_id']: r for r in ckpt['records']}
    expected_lines = []
    for word in state_words(manifest):
        value = records[word['state_id']]['values'][word['address']]
        require(value == values[word['path']], 'image differs from original captured state')
        expected_lines.append(f"semantic_replay_tb.dut.{word['path']} {word['width']} {value}")
    require((case / 'restore.txt').read_text().splitlines() == expected_lines and len(expected_lines) == words,
            'incomplete/different native restore rows')
    for row, record in zip(rows[cycle:], trace['records']):
        require(record['cycle'] == row['cycle'], 'shifted finite trace label')
        original = dict(zip((f['path'] for f in fields), row['values']))
        for direction in ('inputs', 'outputs'):
            for signal, value in record[direction].items():
                require(value['value'] == original[signal], 'changed captured trace sample')
    require(len(trace['records']) == len(rows) - cycle, 'truncated captured continuation')
    bench = (case / 'replay.sv').read_text()
    first_edge = bench.index('  clock = 1;')
    for line in expected_lines:
        path, width, value = line.split()
        guard = f"if ({path.removeprefix('semantic_replay_tb.')} !== {width}'h{value})"
        require(guard in bench and bench.index(guard) < first_edge, 'missing complete zero-edge readback guard')
    require(bench.count('FIRST_MISMATCH cycle=') == (len(rows) - cycle) * outputs,
            'finite replay omits boundary outputs')
    log = (case / 'run.log').read_text()
    require(f'RESTORE: deposited {words} semantic words before first DUT edge' in log
            and 'Y-2026.03-SP1_Full64' in log, 'missing native pinned-release readback')
    pids = re.findall(r'fresh_process_pid=(\d+)', log)
    require(len(pids) == 1, 'missing/ambiguous fresh native process')
    require((case / 'simv').stat().st_size > 0 and (case / 'replay.vcd').stat().st_size > 0, 'missing native binary/waveform')
    if fault:
        require(f'FIRST_MISMATCH cycle={cycle} signal={fault}' in log and log.count('FIRST_MISMATCH') == 1
                and 'ACKNOWLEDGED_TARGET_EDGE' not in log and 'exit=0' not in log,
                'semantic corruption did not stop at first boundary')
    else:
        require(f'samples={len(rows) - cycle} outputs_per_cycle={outputs} restored_words={words}' in log
                and 'PASS: fresh clean RTL replay' in log and 'exit=0' in log
                and log.count('ACKNOWLEDGED_TARGET_EDGE') == len(rows) - cycle, 'incomplete native continuation')
    return int(pids[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metasim-summary', type=Path, required=True)
    parser.add_argument('--policies-summary', type=Path, required=True)
    args = parser.parse_args()
    pids = []
    summary = read_json(args.metasim_summary)
    require(summary['status'] == 'passed' and summary['fixture_only']
            and not summary['CPU_level1_verified'] and not summary['CPU_level2_verified'], 'wrong evidence scope')
    check_inputs(summary['inputs_sha256'])
    manifest_path = next(Path(p) for p in summary['inputs_sha256'] if p.endswith('.semantic-state.json'))
    base = str(manifest_path).removesuffix('.semantic-state.json')
    manifest, boundary = read_json(manifest_path), read_json(base + '.semantic-boundary.json')
    expected = {e['hierarchy'].removeprefix(manifest['dut_root'] + '.'):
                (e['width'], e['depth'], e['kind']) for e in manifest['state']}
    for suffix in ('.semantic-clean.sv', '.sv'):
        require(inventory_rtl(modules(Path(base + suffix).read_text()), boundary['dut_module']) == expected,
                'incomplete independent emitted state inventory')
    out = args.metasim_summary.resolve().parent
    fields, rows = read_json(out / 'capture-layout.json'), [json.loads(s) for s in (out / 'capture.jsonl').read_text().splitlines()]
    from tools.checkpoint_formats.tests.verify_semantic_memory_vcs import audit_capture, CONFIGURATION
    audit_capture(fields, rows)
    require([c['cycle'] for c in summary['cases']] == [0, 5, 13, 21, 24, 26, 28, 30], 'reduced metasim cuts')
    for case in summary['cases']:
        c = case['cycle']
        pids.append(check_replay(out / f'cut-{c}', manifest, boundary, CONFIGURATION, rows, fields, c, 37, 5))
    require(len(summary['actual_state_faults']) == 4 and len(summary['image_rejections']) == 5
            and len(summary['loader_rejections']) == 4, 'reduced fault/rejection scope')
    for fault in summary['actual_state_faults']:
        pids.append(check_replay(out / ('fault-' + fault['state']), manifest, boundary, CONFIGURATION,
                                 rows, fields, 21, 37, 5, fault['signal']))
    for case in summary['image_rejections']:
        directory = out / ('invalid-' + case['case'])
        require(not (directory / 'restore.txt').exists() and not (directory / 'replay.sv').exists(), 'partial invalid image publication')
    for case in summary['loader_rejections']:
        log = (out / (case + '.log')).read_text()
        require('RESTORE_ERROR' in log and 'RESTORE: deposited' not in log
                and 'ACKNOWLEDGED_TARGET_EDGE' not in log and 'exit=0' not in log, 'partial native invalid restore')
    policies = read_json(args.policies_summary)
    require(policies['status'] == 'passed' and len(policies['ordinary_policies']) == 5, 'reduced ordinary policy scope')
    ordinary_samples = 0
    for policy in policies['ordinary_policies']:
        check_inputs(policy['inputs_sha256'])
        manifest_path = next(Path(p) for p in policy['inputs_sha256'] if p.endswith('.semantic-state.json'))
        base = str(manifest_path).removesuffix('.semantic-state.json')
        manifest, boundary = read_json(manifest_path), read_json(base + '.semantic-boundary.json')
        directory = args.policies_summary.resolve().parent / policy['policy']
        fields = read_json(directory / 'capture-layout.json')
        rows = [json.loads(s) for s in (directory / 'capture.jsonl').read_text().splitlines()]
        require([c['cycle'] for c in policy['cases']] == [0, 5, 10, 16], 'reduced ordinary cuts')
        for case in policy['cases']:
            c = case['cycle']
            pids.append(check_replay(directory / f'cut-{c}', manifest, boundary, policy['policy'], rows, fields, c, 6, 1))
            ordinary_samples += len(rows) - c
        pids.append(check_replay(directory / 'pipeline-fault', manifest, boundary, policy['policy'], rows, fields, 10, 6, 1, 'result'))
    require(len(pids) == len(set(pids)), 'native continuation reused a process')
    print(json.dumps(dict(status='passed', fixture_only=True, metasim_words=37,
                          metasim_samples=sum(c['samples'] for c in summary['cases']),
                          ordinary_policy_samples=ordinary_samples, fresh_native_processes=len(pids),
                          CPU_level1_verified=False, CPU_level2_verified=False), indent=2))


if __name__ == '__main__':
    main()
