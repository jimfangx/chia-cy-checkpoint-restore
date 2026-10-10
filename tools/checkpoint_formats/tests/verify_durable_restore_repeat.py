"""Repeat the complete native durable check in one output directory."""
import argparse
import json
import os
from pathlib import Path
import stat
import sys

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    shared = out / 'shared'
    shared.mkdir(exist_ok=True)
    # Reproduce the stale fixtures from the original verifier. Preserve these
    # too when this regression itself is run again.
    sentinel = out / 'sentinel'
    if not sentinel.exists():
        sentinel.write_bytes(b'previous checkpoint must remain unchanged\n')
    link, fifo, directory = (shared / name for name in ('symlink', 'fifo', 'directory'))
    if not link.is_symlink():
        link.symlink_to(sentinel)
    if not fifo.exists():
        os.mkfifo(fifo)
    directory.mkdir(exist_ok=True)
    require(link.is_symlink() and stat.S_ISFIFO(fifo.stat().st_mode), 'wrong stale fixture types')
    paths = [sentinel, link, fifo, directory]
    before = [(p.lstat().st_ino, p.lstat().st_mode) for p in paths]
    original = sentinel.read_bytes()
    target = os.readlink(link)
    summaries = []
    for index in range(2):
        run([sys.executable, '-m', 'tools.checkpoint_formats.tests.verify_durable_restore',
             '--out', shared], out / f'repeat-{index}.log')
        summary = json.loads((shared / 'summary.json').read_text())
        require(summary['python_staging_byte_comparison'] and len(summary['rejections']) == 96,
                'incomplete native oracle/rejection coverage')
        for name, path in summary['special_file_inputs'].items():
            require(Path(path).parent.parent == shared and Path(path).parent != shared,
                    'special fixture escaped invocation directory')
            require((Path(path).parent / f'{name}.log').read_text().endswith('exit=1\n'),
                    'missing actual special-file rejection')
        summaries.append(summary)
        (out / f'summary-{index}.json').write_bytes(canonical(summary))
        require([(p.lstat().st_ino, p.lstat().st_mode) for p in paths] == before and
                sentinel.read_bytes() == original and os.readlink(link) == target,
                'rerun modified previous fixtures/checkpoint')
    require(summaries[0]['rejections'] == summaries[1]['rejections'] and
            all(summaries[0]['special_file_inputs'][name] != path
                for name, path in summaries[1]['special_file_inputs'].items()),
            'rerun reused special fixtures or changed rejection scope')
    summary = dict(invocations=2, rejections_per_invocation=96,
                   python_oracle_comparisons=2, stale_fixtures_unchanged=True,
                   invocation_summaries=[str(out / f'summary-{i}.json') for i in range(2)])
    (out / 'summary.json').write_bytes(canonical(summary))
    print('PASS: two complete native ASan/UBSan invocations in the same --out; '
          '192 rejections, both Python oracles, previous fixtures unchanged')


if __name__ == '__main__':
    main()
