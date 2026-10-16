"""Independent retained artifact audit for complete Rocket semantic event replay."""
import argparse
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import decode, require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.replay import builds
from tools.checkpoint_formats.semantic import decode_semantic
from tools.checkpoint_formats.tests.verify_fame_event_replay_vcs import CONFIGURATION


def audit(report, capture_log=None):
    summary = json.loads(Path(report).read_text())
    require(summary['status'] == 'passed' and summary['CPU_level1_verified'] is False and
            summary['CPU_level2_verified'] is False and summary['cuts'], 'unsupported/incomplete CPU replay report')
    archived = summary['archived_inputs']
    for row in archived.values():
        require(file_sha(row['path']) == row['sha256'], 'changed retained CPU replay input')
    for path, digest in summary['artifacts'].items():
        require(file_sha(path) == digest, 'changed retained native CPU artifact ' + path)

    def input_file(suffix):
        rows = [row for path, row in archived.items() if path.endswith(suffix)]
        require(len(rows) == 1, 'missing/ambiguous retained original input ' + suffix)
        return Path(rows[0]['path'])

    manifest = json.loads(input_file('.semantic-state.json').read_text())
    boundary = json.loads(input_file('.semantic-boundary.json').read_text())
    mapping = json.loads(input_file('.semantic-fame-map.json').read_text())
    rtl_build, trace_build = builds(manifest, boundary, CONFIGURATION)
    ports = {p['name']: p for p in boundary['ports']}
    ports.update({a['name']: dict(name=a['name'], direction='output', width=1) for a in boundary['clock_aliases']})
    total = sum(e['depth'] for e in manifest['state'])
    require(total == summary['binding']['semantic_words'] == 318637 and len(manifest['state']) == 8644,
            'changed complete Rocket semantic owner inventory')
    samples = faults = negatives = 0
    for case in summary['cuts']:
        directory = Path(case['directory']); cycle = case['cycle']
        ckpt = decode_semantic((directory / 'capture.rtlckpt').read_bytes(), rtl_build, manifest)
        trace = decode((directory / 'capture.trace').read_bytes(), 'trace', trace_build)
        require(ckpt['event_phase'] == trace['event_phase'] and ckpt['target_cycle'] == trace['target_cycle'] == cycle,
                'native CPU checkpoint/trace label mismatch')
        raw_words = input_file(f'.{cycle}.state').read_text().splitlines()
        raw_events = [json.loads(line) for line in input_file(f'.{cycle}.jsonl').read_text().splitlines()]
        require(len(raw_words) == total == case['words'] and len(raw_events) == case['samples'] == 64,
                'incomplete captured CPU state/window')
        require(ckpt['event_phase'] == dict(event_index=raw_events[0]['event_index'],
                    cycle_clock=manifest['clock_inputs'][0], clock_levels=raw_events[0]['before'],
                    rising_edges=raw_events[0]['rising_edges']), 'captured original clock phase/counts differ from image')
        index = 0
        restored = (directory / 'restore.txt').read_text().splitlines()
        for owner, binding, record in zip(manifest['state'], mapping['state'], ckpt['records']):
            require(owner['state_id'] == binding['state_id'] == record['state_id'], 'reordered semantic owners')
            for address in range(owner['depth']):
                fields = raw_words[index].split(); restored_fields = restored[index].split(); index += 1
                suffix = f'[{address}]' if owner['kind'] == 'memory' else ''
                require(fields == ['emul.' + binding['rtl_path'] + suffix, str(owner['width']), record['values'][address]] and
                        restored_fields[1:] == fields[1:], 'captured/restored original semantic word differs')
        require(index == len(restored) == len(raw_words), 'incomplete native loader word membership')
        for raw, record in zip(raw_events, trace['records']):
            require({k: raw[k] for k in ('event_index', 'cycle', 'clock_levels', 'inputs', 'outputs')} == record,
                    'captured input/output/timing trace differs from replay')
            for direction in ('input', 'output'):
                require({k: v['width'] for k, v in record[direction+'s'].items()} ==
                        {k: p['width'] for k, p in ports.items() if p['direction'] == direction},
                        'incomplete native CPU boundary signals')
        require('-full64' in case['build_command'] and case['build_command'][0] ==
                '/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs', 'wrong ordinary CPU replay build')
        log = (directory / 'run.log').read_text()
        require('Y-2026.03-SP1_Full64' in log and f'ZERO_EDGE_READBACK words={total} edges=0' in log and 'exit=0' in log,
                'incomplete native CPU zero-edge readback')
        matches = re.findall(r'MATCH event=(\d+) cycle=(\d+) outputs=(\d+)', log)
        require(matches == [(str(r['event_index']), str(r['cycle']), str(len(r['outputs']))) for r in trace['records']] and
                f'PASS: event replay samples=64 words={total} acknowledged=64' in log, 'incomplete native CPU output comparisons')
        require(len(case['faults']) == 4 and len(case['native_invalid']) == 4 and len(case['invalid_images']) == 7,
                'missing CPU fault/invalid cases')
        for fault in case['faults']:
            log = Path(fault['log']).read_text()
            found = re.findall(r'DIVERGENCE event=(\d+) cycle=(\d+) signal=(\S+).* acknowledged=(\d+)', log)
            require(found == [(str(trace['event_phase']['event_index']), str(cycle),
                               f'trace_traces_{fault["hart"]}_trace_time', '0')] and
                    'MATCH event=' not in log and 'exit=1' in log and
                    f'ZERO_EDGE_READBACK words={total} edges=0' in log, 'missed first CPU semantic corruption')
            faults += 1
        for invalid in case['native_invalid']:
            log = Path(invalid['log']).read_text()
            require('PASS: invalid loader preserved complete baseline edges=0' in log and
                    'RESTORE: deposited' not in log and 'exit=0' in log, 'partial CPU invalid native load')
        require(all(row['published'] is False and row['error'] for row in case['invalid_images']), 'partial invalid CPU image publication')
        samples += len(trace['records']); negatives += len(case['native_invalid']) + len(case['invalid_images'])
    if capture_log:
        log = Path(capture_log).read_text()
        require('Y-2026.03-SP1_Full64' in log and '*** PASSED *** after 3329794 cycles' in log and
                'CAPTURE_COMPLETE' in log and log.rstrip().endswith('exit=0'), 'incomplete native four-hart capture run')
        require(log.count(f'FAME_CAPTURE_PRE_EDGE_READBACK words={total}') == len(summary['cuts']),
                'missing full pre-edge source-state audits')
        for case in summary['cuts']:
            require(f'CAPTURE_WINDOW cycle={case["cycle"]} events=64' in log, 'missing actual CPU capture window')
    return dict(status='passed', cuts=len(summary['cuts']), samples=samples, semantic_words_per_cut=total,
                actual_semantic_first_divergences=faults, invalid_images_and_native_loads=negatives,
                artifacts=len(summary['artifacts']), complete_source_run_checked=bool(capture_log),
                CPU_level1_verified=False, CPU_level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--capture-log', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = audit(args.summary, args.capture_log)
    if args.out: args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
