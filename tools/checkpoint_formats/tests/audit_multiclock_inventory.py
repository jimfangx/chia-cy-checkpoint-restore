"""Independently audit retained native multi-clock inventory probes only."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.multiclock_inventory import audit_inventory


def audit(summary_path):
    summary_path = Path(summary_path).resolve()
    summary = json.loads(summary_path.read_text()); out = summary_path.parent
    require(summary['status'] == 'passed' and summary['artifact_root'] == str(out) and
            summary['CPU_level1_verified'] is False and summary['CPU_level2_verified'] is False and
            summary['required_CPU_checkpoint_cuts_tested'] is False, 'inventory probe misrepresented as CPU execution')
    archived = {}
    for original, binding in summary['archived_inputs'].items():
        snapshot = Path(binding['path'])
        require(file_sha(snapshot) == binding['sha256'], 'changed original native inventory source')
        if '/automations/checkpoint_loop/runs/' in original:
            require(file_sha(original) == binding['sha256'], 'changed original generated inventory input')
        archived[Path(original).name] = snapshot
    def selected(suffix):
        matches = [p for name, p in archived.items() if name.endswith(suffix)]
        require(len(matches) == 1, 'missing/ambiguous original inventory input ' + suffix)
        return matches[0]
    manifest = json.loads(selected('.semantic-state.json').read_text())
    boundary = json.loads(selected('.semantic-boundary.json').read_text())
    access = json.loads(selected('.semantic-clean-access.json').read_text())
    report = audit_inventory(manifest, boundary, selected('.semantic-reference.fir').read_text(),
                             selected('.semantic-clean.sv').read_text(), access)
    require(report['semantic_words'] == summary['semantic_words'] and report['clock_owners'] == summary['clock_owners'],
            'changed complete native word/clock totals')
    paths = {e['state_id']: e['rtl_path'] for e in access['state']}
    expected = []
    for e in manifest['state']:
        for address in range(e['depth']):
            path = paths[e['state_id']] + (f'[{address}]' if e['kind'] == 'memory' else '')
            raw = hashlib.shake_256(path.encode()).digest((e['width'] + 7) // 8)
            value = int.from_bytes(raw, 'little') & ((1 << e['width']) - 1)
            expected.append(f"inventory_probe_tb.dut.{path} {e['width']} {value:0{(e['width'] + 3) // 4}x}")
    require((out / 'complete-pattern.txt').read_text().splitlines() == expected,
            'incomplete/reshaped/changed complete native diagnostic pattern')
    bench = archived['probe.sv'].read_text()
    require(f'semantic_restore(pattern, {len(expected)})' in bench and
            f'semantic_verify(pattern, {len(expected)})' in bench and
            f'semantic_verify(baseline, {len(expected)})' in bench and
            'if (edges || ' in bench and ' = 1;' not in bench, 'missing complete zero-edge native guard')
    for clock in manifest['clock_inputs']:
        port = clock[len(manifest['dut_root']) + 1:]
        require(f'always @(posedge {port}) edges = edges + 1;' in bench, 'native probe omits a clock guard')
    require(summary['vcs_home'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and
            summary['build_command'][0] == summary['vcs_home'] + '/bin/vcs' and
            all(flag in summary['build_command'] for flag in ('-full64', '+vpi', '-debug_access+all')),
            'native ownership probe used incompatible compiler settings')
    build = (out / 'build.log').read_text()
    require(json.loads(build.split('argv=', 1)[1].splitlines()[0]) == summary['build_command'] and
            'Y-2026.03-SP1_Full64' in build and build.rstrip().endswith('exit=0'), 'missing native build provenance')
    require({c['name'] for c in summary['cases']} ==
            {'complete', 'corrupt-storage', 'missing-word', 'duplicate-word', 'unknown-word', 'wrong-width'} and
            len(summary['cases']) == 6, 'reduced native inventory probe scope')
    pids = []
    for case in summary['cases']:
        log = Path(case['log']).read_text()
        require(Path(case['log']).parent == out and json.loads(log.split('argv=', 1)[1].splitlines()[0]) == case['argv'] and
                log.rstrip().endswith('exit=0') and 'Y-2026.03-SP1_Full64' in log and
                f'PASS: inventory probe words={len(expected)} clocks={len(manifest["clock_inputs"])} edges=0' in log,
                'missing native full zero-edge readback or changed argv')
        invalid = '+invalid' in case['argv']
        require(log.count('RESTORE: deposited') == (0 if invalid else 1), 'invalid native inventory probe partially deposited')
        require(not invalid or 'RESTORE_ERROR' in log, 'invalid native storage request did not reject')
        if case['name'] == 'corrupt-storage':
            require('semantic readback mismatch' in log, 'actual native storage corruption was undetected')
        matches = re.findall(r'fresh_process_pid=(\d+)', log)
        require(len(matches) == 1, 'missing/ambiguous native process ID'); pids.append(int(matches[0]))
    require(len(set(pids)) == 6 and (out / 'simv').is_file(), 'native probes did not use six distinct processes')
    require(not list(out.glob('*.rtlckpt')) and not list(out.glob('*.trace')), 'diagnostic inventory probe has unbound semantic images')
    return dict(report, native_fresh_processes=len(pids), native_zero_edge_words=len(expected),
                scope='native diagnostic pattern readback only; CPU workload capture/replay pending',
                native_binary_sha256=file_sha(out / 'simv'), summary=str(summary_path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.summary), indent=2))


if __name__ == '__main__':
    main()
