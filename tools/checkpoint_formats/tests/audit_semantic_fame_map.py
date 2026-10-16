"""Recheck every artifact, original word and fresh native storage probe."""
import argparse
import hashlib
import json
from pathlib import Path

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.semantic_fame import audit_mapping


def audit(path):
    summary = json.loads(path.read_text()); out = path.parent.resolve()
    require(summary['status'] == 'passed' and summary['artifact_root'] == str(out)
            and not summary['CPU_level1_verified'] and not summary['CPU_level2_verified'], 'incomplete probe')
    artifacts = {str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.resolve() != path.resolve()}
    require(artifacts == summary['artifacts'], 'changed/missing/extra native artifact')
    snapshots = {}
    for original, row in summary['archived_inputs'].items():
        saved = Path(row['path'])
        require(saved.is_relative_to(out / 'inputs') and file_sha(saved) == row['sha256'], 'changed original source snapshot')
        snapshots[Path(original).name] = saved
    def selected(suffix):
        matches = [p for name, p in snapshots.items() if name.endswith(suffix)]
        require(len(matches) == 1, 'missing/ambiguous original input ' + suffix)
        return matches[0].read_text()
    manifest = json.loads(selected('.semantic-state.json'))
    generated = json.loads(selected('.simulator-state.json'))
    mapping = json.loads(selected('.semantic-fame-map.json'))
    report = audit_mapping(manifest, mapping, generated, selected('.simulator-reference.fir'),
                           selected('.semantic-fame-emitted.sv'), selected('BUFGCE.v'), selected('plusarg_reader.v'),
                           selected('AbstractClockGate.v'))
    expected = []
    for e in manifest['state']:
        for address in range(e['depth']):
            raw = hashlib.shake_256(f"{e['state_id']}:{address}".encode()).digest((e['width'] + 7) // 8)
            expected.append(dict(state_id=e['state_id'], address=address, width=e['width'],
                                 value=int.from_bytes(raw, 'little') & ((1 << e['width']) - 1)))
    require([n['kind'] for n in summary['native']] == ['transformed', 'ordinary'], 'missing native layout')
    pids = []
    for native in summary['native']:
        directory = out / native['kind']
        require(json.loads((directory / 'words.json').read_text()) == expected, 'changed complete original word oracle')
        bindings = {b['state_id']: b['rtl_path'][len(generated['root_module']) + 1:]
                    for b in mapping['state']} if native['kind'] == 'transformed' else {
                    b['state_id']: b['rtl_path'] for b in json.loads(selected('.semantic-clean-access.json'))['state']}
        entries = {e['state_id']: e for e in manifest['state']}
        rows = []
        for word in expected:
            e = entries[word['state_id']]
            owner = bindings[word['state_id']] + (f"[{word['address']}]" if e['kind'] == 'memory' else '')
            rows.append(f"fame_map_probe_tb.dut.{owner} {word['width']} {word['value']:0{(word['width'] + 3) // 4}x}")
        require((directory / 'complete.txt').read_text().splitlines() == rows, 'native loader omits/changes original word')
        build = (directory / 'build.log').read_text()
        require(json.loads(build.split('argv=', 1)[1].splitlines()[0]) == native['build_command'] and
                native['build_command'][0] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs' and
                '-full64' in native['build_command'] and build.rstrip().endswith('exit=0'), 'missing pinned native build')
        require([c['name'] for c in native['cases']] == ['complete', 'corrupt', 'missing', 'duplicate', 'unknown', 'width'],
                'reduced native negative/corruption scope')
        bench = (directory / 'probe.sv').read_text()
        require('if (edges) semantic_fail("UNEXPECTED_EDGE")' in bench and
                bench.count('always @(posedge dut.') == native['clocks'] and native['clocks'] > 0,
                'missing zero-edge guards')
        for case in native['cases']:
            log = Path(case['log']).read_text()
            require(Path(case['log']).parent == directory and
                    json.loads(log.split('argv=', 1)[1].splitlines()[0]) == case['argv'] and
                    log.rstrip().endswith('exit=0') and 'Y-2026.03-SP1_Full64' in log and
                    f"PASS: {native['kind']} semantic map words={len(expected)} edges=0" in log, 'incomplete native readback')
            require(log.count('RESTORE: deposited') == (1 if case['name'] in ('complete', 'corrupt') else 0),
                    'invalid native image partially deposited')
            require(case['name'] != 'corrupt' or 'semantic readback mismatch' in log, 'actual semantic fault missed')
            pids.append(int(log.split('fresh_process_pid=', 1)[1].splitlines()[0]))
    require(len(pids) == len(set(pids)) == 12, 'not twelve fresh native processes')
    return dict(report, native_fresh_processes=12, zero_edge_words_per_layout=len(expected), summary=str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.summary.resolve()), indent=2))


if __name__ == '__main__':
    main()
