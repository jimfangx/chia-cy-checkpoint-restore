"""Full VPD/VCD state and boundary audit for production architecture parity.

The original semantic manifest and StateIDs never change. The alternative
memory paths are checked against the reconstructed unproven architecture, not
promoted to a formal map. Source vcs-env.sh LAST for VPD conversion.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
from itertools import zip_longest

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.finite_replay import check_clean
from tools.checkpoint_formats.production_dut import audit_architecture
from tools.checkpoint_formats.replay import builds
from tools.checkpoint_formats.semantic import decode_semantic
from .audit_finite_replay import audit_case
from .verify_finite_replay_vcs import audit_waveform
from .verify_formal_state_map import ROOT
from .verify_production_dut import file_sha


def audit(run, out):
    run = Path(run).resolve()
    candidate = audit_architecture(run / 'architecture')
    summary = json.loads((run / 'summary.json').read_text())
    require(summary['full_original_and_memory_architecture_RTL_replay'] and not summary['gate_replay'] and
            summary['run'] == str(run), 'wrong production replay scope')
    manifest = json.loads((run / 'architecture/manifest.json').read_text())
    boundary = json.loads((run / 'architecture/boundary.json').read_text())
    metadata = json.loads((run / 'ordinary-rtl/replay.json').read_text())
    original_rtl = (run / 'architecture/original.sv').read_text()
    check_clean(manifest, boundary, original_rtl)
    require(all(file_sha(p) == h for p, h in summary['inputs'].items()), 'changed production capture inputs')
    input_paths = {Path(p).name: Path(p) for p in summary['inputs']}
    checkpoint_path, trace_path = input_paths['capture.rtlckpt'], input_paths['capture.trace']
    require(metadata['checkpoint_sha256'] == file_sha(checkpoint_path) and
            metadata['trace_sha256'] == file_sha(trace_path), 'unbound production replay sample')
    checkpoint = decode_semantic(checkpoint_path.read_bytes(), builds(manifest, boundary, summary['configuration'])[0], manifest)
    values = {r['state_id']: r for r in checkpoint['records']}
    paths = {e['state_id']: e['architecture_path'] for e in candidate['entries']}

    def expected_restore():
        for entry in manifest['state']:
            original = entry['hierarchy'][len(manifest['dut_root'])+1:]
            for address, value in enumerate(values[entry['state_id']]['values']):
                suffix = f'[{address}]' if entry['kind'] == 'memory' else ''
                prefix = 'finite_replay_tb.dut.'
                yield (prefix + original + suffix, prefix + paths[entry['state_id']] + suffix, str(entry['width']), value)

    with (run / 'ordinary-rtl/restore.txt').open() as original, (run / 'memory-architecture-rtl/restore.txt').open() as adapted:
        words = 0
        for want, before, after in zip_longest(expected_restore(), original, adapted):
            require(want is not None and before is not None and after is not None, 'incomplete/extra production restore word')
            p, q, width, value = want
            require(before.split() == [p, width, value] and after.split() == [q, width, value],
                    'production restore oracle differs from actual semantic checkpoint')
            words += 1
        require(words == 13503308, 'incomplete production restore oracle')
    del checkpoint, values
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    reports, commands = [], []
    for label in ('ordinary-rtl', 'memory-architecture-rtl'):
        case = run / label
        # Each repeat gets its own converted waveform; retain prior evidence.
        view_directory = out / label
        view_directory.mkdir()
        for name in ('clean.sv', 'replay.sv', 'restore.txt', 'matched.txt'):
            (view_directory / name).symlink_to(case / name)
        (view_directory / 'trace.txt').symlink_to(run / 'ordinary-rtl/trace.txt')
        argv = [str(Path(os.environ['VCS_HOME']) / 'bin/vpd2vcd'), '-full64', '+includemda',
                str(case / 'replay.vpd'), str(view_directory / 'replay.vcd')]
        log = out / (label + '-conversion.log')
        with log.open('w') as stream:
            process = subprocess.run(argv, cwd=case, stdout=stream, stderr=subprocess.STDOUT, timeout=3600)
        commands.append(dict(cwd=str(case.relative_to(ROOT)), argv=argv, log=str(log), exit_code=process.returncode))
        (out / 'commands.json').write_bytes(canonical(commands))
        require(process.returncode == 0, 'VPD conversion failed: ' + str(log))
        # Construct only the expected waveform path view. This is not a new
        # semantic manifest/container and never authorizes initialization.
        view = copy.deepcopy(manifest)
        if label == 'memory-architecture-rtl':
            paths = {e['state_id']: e['architecture_path'] for e in candidate['entries']}
            for entry in view['state']:
                entry['hierarchy'] = manifest['dut_root'] + '.' + paths[entry['state_id']]
        declaration_report = audit_waveform(view_directory / 'replay.vcd', view, boundary)

        def clean_validator(m, b, actual):
            expected = original_rtl if label == 'ordinary-rtl' else (
                (run / 'architecture/architecture.sv').read_text() + (run / 'architecture/memory-models.v').read_text())
            require(actual == expected, 'changed production replay RTL/models')
            require(candidate == audit_architecture(run / 'architecture'), 'changed production architecture')

        result = dict(metadata=metadata, first_mismatch_cycle=None,
                      artifact_hashes={n: file_sha(view_directory / n) for n in
                                       ('clean.sv', 'replay.sv', 'restore.txt', 'trace.txt', 'replay.vcd', 'matched.txt')})
        report = audit_case(view_directory, manifest, boundary, result, clean_validator=clean_validator)
        require(report['zero_edge_waveform_state_words'] == 13503308 and report['checked_boundaries'] == 250185 and
                report['actual_edges'] == 250185, 'incomplete production waveform scope')
        reports.append(dict(case=str(case), waveform=str(view_directory / 'replay.vcd'), declarations=declaration_report, **report))
        (out / (label + '-audit.json')).write_bytes(canonical(reports[-1]))
    report = dict(status='pass', scope='production original/extracted-memory RTL parity, not formal map or gate replay',
                  cases=reports, formal_state_map_complete=False, gate_restore_authorized=False)
    (out / 'summary.json').write_bytes(canonical(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    destination = args.out.resolve()
    if destination.exists():
        destination = Path(tempfile.mkdtemp(prefix='invocation-', dir=destination)) / 'evidence'
    result = audit(args.run, destination)
    (args.out / 'selection.json').write_bytes(canonical(dict(evidence=str(destination), summary=str(destination / 'summary.json'))))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
