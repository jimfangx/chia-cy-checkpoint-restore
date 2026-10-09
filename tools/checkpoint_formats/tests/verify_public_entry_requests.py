"""Fail-closed public requests against the full generated production-entry VCS build."""
import argparse
import hashlib
import json
from pathlib import Path

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    production = args.production.resolve(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    summary = json.loads((production/'summary.json').read_text())
    inputs = json.loads((production/'native-build-inputs.json').read_text())
    build = json.loads((production/'aggregate-build.json').read_text())
    require(summary['real_production_entry_verified'] and not summary['production_plusargs_enabled']
            and len(summary['cases']) == 5, 'requires completed restricted production-entry continuations')
    require(all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == value
                for name, value in inputs['sources'].items()), 'changed production native implementation')
    require(hashlib.sha256((production/'simv').read_bytes()).hexdigest() == build['simulator_build_hash'],
            'changed production executable')
    absent = out/'must stay absent.fsckpt'
    existing = out/'unchanged input.fsckpt'; existing.write_bytes(b'closed public API input\n')
    capture = f'+fs-checkpoint={absent}'; restore = f'+fs-restore={existing}'
    options = [[capture], [restore]]
    options += [[v] for v in ('+fs-checkpoint', '+fs-restore', '+fs-checkpoint=', '+fs-restore=',
                             '+fs-checkpoint-preflight=1', '+fs-checkpoint-typo=x', '+fs-restore-typo=x')]
    options += [[capture, capture], [restore, restore], [capture, restore], [restore, capture],
                ['+fs-checkpoint-preflight', restore],
                ['+fs-checkpoint-preflight', '+fs-checkpoint-preflight']]
    results = []
    common = [production/'simv', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
              '+memsize=4194304', '+max-cycles=1000000']
    for i, request in enumerate(options):
        log = out/f'public-{i}.log'
        text = run([*common, *request], log, out, expected=1)
        require('Y-2026.03-SP1_Full64' in text and 'FS_CHECKPOINT_ENTRY_ERROR' in text,
                'request did not explicitly fail in the pinned VCS release')
        if i < 2: require('runtime identity: unsupported argument:' in text, 'test capability enabled public API')
        else: require('Level-1 checkpoint' in text, 'malformed/conflicting request escaped parsing')
        for marker in ('FS_CHECKPOINT_ENTRY_CONFIGURED', 'FS_CHECKPOINT_ENTRY_CONSTRUCTED',
                       'PRODUCTION_AGGREGATE_RESERVED', 'PRODUCTION_AGGREGATE_LOADED',
                       'PRODUCTION_BOOTSTRAP', 'FireSim fingerprint:', 'Commencing simulation', '*** PASSED ***'):
            require(marker not in text, f'public rejection reached runtime stage: {marker}')
        require(not absent.exists() and existing.read_bytes() == b'closed public API input\n',
                'public rejection touched checkpoint files')
        results.append(dict(argv=[str(a) for a in [*common, *request]], log=str(log),
                            fresh_process_pid=int(text.split('fresh_process_pid=')[1].splitlines()[0])))
    require(len({r['fresh_process_pid'] for r in results}) == len(results), 'process reuse')
    result = dict(public_requests_rejected=len(results), before_platform=True,
                  production_executable_sha256=build['simulator_build_hash'], cases=results)
    (out/'summary.json').write_bytes(canonical(result))
    print(f'PASS: {len(results)} full generated production-entry VCS public requests fail before platform construction')


if __name__ == '__main__':
    main()
