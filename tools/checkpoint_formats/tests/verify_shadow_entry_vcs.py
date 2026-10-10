"""Actual public-entry rejection of partial, duplicate and mistyped shadow controls."""
import argparse
import os
from pathlib import Path

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    production, out = args.production.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    valid = ['+shadow-socket=/tmp/unused-shadow-entry', '+shadow-identity='+'a'*64,
             '+shadow-first-cycle=524453', '+shadow-level1-cycle=524402']
    source = out / 'untouched.fsckpt'
    source.write_bytes(b'untouched rejected input\n')
    common = [production / 'AXI4Fuzzer-checkpoint', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
              '+memsize=4194304', '+max-cycles=1000000']
    cases = [('partial', [f'+fs-restore={source}', *valid[:-1]], 'all four controls'),
             ('duplicate', [f'+fs-restore={source}', *valid, valid[0]], 'invalid/duplicate'),
             ('unknown', [f'+fs-restore={source}', *valid, '+shadow-invented=x'], 'invalid/duplicate'),
             ('bad-origin', [f'+fs-restore={source}', *valid[:2], '+shadow-first-cycle=01', valid[3]], 'cycle origin'),
             ('capture', ['+fs-checkpoint='+str(out/'must-stay-absent.fsckpt'),
                          '+fs-checkpoint-operation=1', *valid], 'public restore')]
    results = []
    for name, controls, error in cases:
        text = run([*common, *controls], out / (name + '.log'), out, expected=1)
        # At time zero the SV observer can reject a missing origin/restore
        # before the C++ entry executes. Both guards forbid platform loading.
        rejected = 'FS_CHECKPOINT_ENTRY_ERROR' in text and error in text
        if name in ('partial', 'capture'):
            rejected |= 'SHADOW_RESTORE_ORIGIN_REQUIRED' in text
        require(rejected and 'Runtime version Y-2026.03-SP1_Full64' in text, 'wrong actual VCS rejection')
        require(all(marker not in text for marker in ['FS_CHECKPOINT_ENTRY_CONFIGURED',
                'FS_CHECKPOINT_ENTRY_CONSTRUCTED', 'PRODUCTION_AGGREGATE_LOADED', 'PRODUCTION_BOOTSTRAP']),
                'rejected observer arguments reached platform/state loading')
        require(source.read_bytes() == b'untouched rejected input\n' and
                not (out/'must-stay-absent.fsckpt').exists(), 'rejection touched checkpoint files')
        results.append(dict(name=name, exit=1))
    (out / 'summary.json').write_bytes(canonical(dict(status='pass', results=results)))
    print('PASS: five actual public VCS shadow-control rejections before platform construction')


if __name__ == '__main__':
    main()
