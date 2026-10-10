"""Repeat all public VCS rejections against a completed full production run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_public_durable_restore import verify_rejections
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ['VCS_HOME'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1',
            'source vcs-env.sh LAST')
    production, out = args.production.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    summary = json.loads((production / 'summary.json').read_text())
    require(summary['public_durable_restore_enabled'] and len(summary['cases']) == 5,
            'repeat requires a completed full public VCS run')
    inputs = json.loads((production / 'native-build-inputs.json').read_text())
    require(all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value
                for name, value in inputs['sources'].items()), 'stale production implementation')
    build, runtime, generated, layout = [json.loads((production / name).read_text()) for name in (
        'aggregate-build.json', 'runtime-manifest.json', 'generated-manifest.json', 'harness-layout.json')]
    checkpoints = [production / r['timing'] / f'cut-{r["cut"]}' / 'capture.fsckpt'
                   for r in summary['cases']]
    immutable = [production / 'simv', *checkpoints]
    digests = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in immutable}
    require(digests[str(production / 'simv')] == build['simulator_build_hash'], 'stale executable')
    # Seed exactly the fixed paths left by the earlier public verifier.
    stale = []
    for name in ('symlink', 'fifo', 'directory'):
        case = production / 'public-special-negative' / name
        case.mkdir(parents=True, exist_ok=True)
        path = case / 'input'
        if not os.path.lexists(path):
            if name == 'symlink':
                path.symlink_to(checkpoints[0])
            elif name == 'fifo':
                os.mkfifo(path)
            else:
                path.mkdir()
        stale.append(path)
    metadata = [(p.lstat().st_ino, p.lstat().st_mode) for p in stale]
    common = [production / 'simv', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
              '+memsize=4194304', '+max-cycles=1000000']
    snapshots = []
    for index in range(2):
        rejections = verify_rejections(common, production, build, runtime, generated, layout)
        count = (len(rejections['public_restore_rejections']) +
                 len(rejections['public_runtime_rejections']) +
                 rejections['public_dispatch_rejections'] + rejections['public_special_file_rejections'])
        require(count == 56, 'incomplete public rejection coverage')
        summary.update(rejections)
        (production / 'summary.json').write_bytes(canonical(summary))
        (out / f'summary-{index}.json').write_bytes(canonical(rejections))
        run([sys.executable, '-m', 'tools.checkpoint_formats.tests.audit_production_aggregate',
             '--out', production], out / f'audit-{index}.log')
        audit = json.loads((production / 'independent-evidence.json').read_text())
        require(audit['public_restore_rejections'] == 56 and audit['fresh_processes'] == 68,
                'incomplete independent public audit')
        (out / f'audit-{index}.json').write_bytes(canonical(audit))
        require(all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == value
                    for p, value in digests.items()) and
                [(p.lstat().st_ino, p.lstat().st_mode) for p in stale] == metadata,
                'rerun modified production executable, checkpoints or previous fixtures')
        snapshots.append(rejections['public_special_file_inputs'])
    require(all(snapshots[0][name] != path for name, path in snapshots[1].items()),
            'reused public special fixtures')
    for inputs in snapshots:
        require(all((Path(path).parent / 'run.log').read_text().endswith('exit=1\n')
                    for path in inputs.values()), 'rerun lost special-file diagnostics')
    result = dict(invocations=2, rejections_per_invocation=56, independent_audits=2,
                  stale_fixtures_unchanged=True, checkpoint_and_executable_sha256=digests,
                  special_file_inputs=snapshots)
    (out / 'summary.json').write_bytes(canonical(result))
    print('PASS: repeated all 56 public VCS rejections twice in the same production directory; '
          'both complete audits, immutable checkpoints, previous fixtures and special-file logs preserved')


if __name__ == '__main__':
    main()
