"""Real native retained-history publication: independent oracle, faults and kills.

Run every case in a fresh ASan/UBSan process. Keep earlier artifacts intact.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import tempfile
from concurrent.futures import ThreadPoolExecutor

from tools.checkpoint_formats import aggregate, aggregate_packed as packed
from tools.checkpoint_formats.codec import FormatError, canonical, decode, encode, require
from tools.checkpoint_formats.durable_restore import prepare_durable_loader
from tools.checkpoint_formats.rolling import NativeRollingHistory, RollingHistory
from tools.checkpoint_formats.tests.test_rolling import fixture
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    configuration, fake_image = fixture(out)
    build, manifest, generated, layout = [configuration[n] for n in ('build', 'manifest', 'generated', 'layout')]
    prepare_durable_loader(manifest, generated, layout, out)
    source = ROOT/'tools/checkpoint_formats'
    cc = ROOT/'sims/firesim/sim/midas/src/main/cc'
    run([os.environ.get('CXX', '/usr/bin/g++-13'), '-std=c++20', '-g', '-no-pie',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer', f'-I{out}', f'-I{cc}',
         source/'durable_restore.cc', source/'durable_history.cc', source/'tests/durable_history_native.cc',
         '-lcrypto', *['-Wl,--wrap='+n for n in ('openat', 'write', 'fsync', 'close', 'linkat', 'renameat', 'unlinkat')],
         '-o', out/'verify'], out/'build.log')
    build = aggregate.build_identity(manifest, generated, layout, out/'verify')
    configuration = dict(configuration, build=build)
    images, snapshots = {}, {}
    for cycle in (10, 20, 30, 40):
        doc = decode(fake_image(cycle), 'fsckpt', json.loads(fake_image(cycle)[16:-32])['build'])
        doc['build'] = build
        images[cycle] = encode('fsckpt', doc)
        snapshots[cycle] = out/f'{cycle}.load'
        packed.prepare_aggregate_restore(images[cycle], build, manifest, generated, layout, snapshots[cycle])

    def execute(label, directory, cycle=20, fault='none', expected=0, recover=False, retention=1):
        return run([out/'verify', snapshots[cycle], directory, retention, fault,
                    'recover' if recover else 'publish'], out/(label+'.log'), expected=expected)

    def store(directory, retention=1):
        return NativeRollingHistory(directory, **dict(configuration, retention=retention))

    normal = out/'normal'; normal.mkdir()
    foreign = normal/'foreign.fsckpt'; foreign.write_bytes(b'foreign')
    pending = normal/'.history.pending-foreign'; pending.write_bytes(b'partial')
    for cycle in (10, 20, 30):
        execute(f'normal-{cycle}', normal, cycle, retention=2)
        policy = store(normal, 2)
        record, data = policy.select(before_target_cycle=cycle+1)
        require(data == images[cycle] and record['target_cycle'] == cycle, 'native bytes differ from Python oracle')
        require(len(policy.recover()) == min(cycle//10, 2) and
                stat.S_IMODE((normal/record['name']).stat().st_mode) == 0o600, 'invalid retention or mode')
    require([r['target_cycle'] for r in store(normal, 2).recover()] == [20, 30], 'wrong retained cycles')
    require(foreign.read_bytes() == b'foreign' and pending.read_bytes() == b'partial', 'foreign/pending input removed')
    for conflict in (False, True):
        directory = out/('immutable-conflict' if conflict else 'immutable-orphan-reuse'); directory.mkdir()
        policy = store(directory)
        name = f'{policy.prefix}{20:020d}-{hashlib.sha256(images[20]).hexdigest()}.fsckpt'
        original = b'conflicting immutable bytes' if conflict else images[20]
        (directory/name).write_bytes(original)
        execute('immutable-'+str(conflict), directory, expected=1 if conflict else 0)
        require((directory/name).read_bytes() == original, 'immutable image was overwritten')
        if conflict: require(not (directory/'history.json').exists(), 'immutable conflict was committed')
        else: require(policy.select(before_target_cycle=21)[1] == images[20], 'exact orphan reuse failed')
    # Cross-implementation publication/selection/recovery uses the same canonical
    # schema and lock. Ordinary policy indexes are explicitly incompatible.
    store(normal, 2).publish(images[40])
    execute('python-native-recover', normal, recover=True, retention=2)
    require(store(normal, 2).select(before_target_cycle=40)[0]['target_cycle'] == 30, 'strict selection failed')
    try:
        RollingHistory(normal, **dict(configuration, retention=2)).recover()
        raise AssertionError('policy history accepted native schema')
    except FormatError:
        pass

    faults = ['preflight-sync', 'image-open', 'write', 'zero-write', 'partial-error', 'image-sync',
              'image-close', 'image-link', 'image-directory-sync', 'image-readback', 'index-open',
              'index-sync', 'index-close', 'index-rename', 'index-directory-sync', 'index-readback',
              'prune', 'retention-sync']
    postcommit = {'index-directory-sync', 'index-readback', 'prune', 'retention-sync'}
    for fault in faults:
        directory = out/fault; directory.mkdir()
        execute(fault+'-initial', directory, 10)
        before = (directory/'history.json').read_bytes()
        first = json.loads(before)['records'][0]['name']
        log = execute(fault, directory, fault=fault, expected=3 if fault in postcommit else 1)
        require(f'REJECT index_committed={int(fault in postcommit)}' in log, 'wrong failure commit status')
        if fault not in postcommit:
            require((directory/'history.json').read_bytes() == before and
                    (directory/first).read_bytes() == images[10], 'uncommitted failure removed old snapshot')
        elif fault != 'retention-sync':
            require((directory/first).read_bytes() == images[10], 'failure before prune removed old snapshot')
        require(not list(directory.glob('.history.pending-*')), 'ordinary failure left pending file')
        if fault == 'image-readback':
            # Corruption remains fail-closed; do not erase it to make recovery pass.
            execute(fault+'-recover', directory, recover=True, expected=1)
            require((directory/'history.json').read_bytes() == before, 'corrupt recovery changed index')
        elif fault in postcommit:
            execute(fault+'-recover', directory, recover=True)
            require(store(directory).recover()[0]['target_cycle'] == 20 and
                    len(list(directory.glob('*.fsckpt'))) == 1, 'committed recovery failed retention')
        else:
            execute(fault+'-retry', directory)
            require(store(directory).select(before_target_cycle=21)[1] == images[20], 'precommit retry failed')

    short = out/'short'; short.mkdir()
    execute('eintr-short-write', short, fault='eintr-short-write')
    require(store(short).select(before_target_cycle=21)[1] == images[20], 'short/EINTR changed bytes')
    pinned = out/'pinned-directory'; pinned.mkdir()
    run([out/'verify', snapshots[20], pinned, 1, 'none', 'pin'], out/'pinned-directory.log')
    require(not list(pinned.iterdir()) and
            store(Path(str(pinned)+'-pinned')).select(before_target_cycle=21)[1] == images[20],
            'native publisher followed a replaced directory pathname')
    kills = ['kill-partial', 'kill-image-sync', 'kill-image-link', 'kill-index-sync',
             'kill-before-index', 'kill-after-index', 'kill-prune']
    for fault in kills:
        directory = out/fault; directory.mkdir()
        execute(fault+'-initial', directory, 10)
        before = (directory/'history.json').read_bytes(); first = json.loads(before)['records'][0]['name']
        execute(fault, directory, fault=fault, expected=-signal.SIGKILL)
        committed = fault in ('kill-after-index', 'kill-prune')
        require((directory/first).read_bytes() == images[10], 'killed writer removed prior state')
        if not committed: require((directory/'history.json').read_bytes() == before, 'killed precommit changed index')
        require(store(directory).select(before_target_cycle=21)[0]['target_cycle'] == (20 if committed else 10),
                'reader selected an uncommitted image')
        # Recover with the actual native constructor and preserve abandoned partials.
        abandoned = {p.name: p.read_bytes() for p in directory.glob('.history.pending-*')}
        execute(fault+'-recover', directory, recover=True)
        require(len(list(directory.glob('*.fsckpt'))) == 1 and
                all((directory/n).read_bytes() == b for n, b in abandoned.items()), 'recovery lost pending evidence')

    # Reject corrupt/special history objects before constructing the platform.
    rejections = []
    for kind in ('index-symlink', 'index-fifo', 'index-directory', 'lock-symlink', 'lock-fifo',
                 'snapshot-symlink', 'snapshot-fifo', 'snapshot-corrupt', 'index-corrupt',
                 'directory-symlink', 'retention', 'regression'):
        directory = out/kind; directory.mkdir(); execute(kind+'-initial', directory, 10)
        index = json.loads((directory/'history.json').read_text()); old_name = index['records'][0]['name']
        name = 'history.json' if kind.startswith('index-') else '.history.lock' if kind.startswith('lock-') else old_name
        target = directory/name
        if kind.endswith(('symlink', 'fifo', 'directory')) and kind != 'directory-symlink':
            target.rename(directory/(name+'.original'))
            if kind.endswith('symlink'): target.symlink_to(directory/(name+'.original'))
            elif kind.endswith('fifo'): os.mkfifo(target)
            else: target.mkdir()
        elif kind.endswith('corrupt'): target.write_bytes(b'corrupt')
        original = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file() and not p.is_symlink()}
        use_directory = directory
        if kind == 'directory-symlink':
            use_directory = out/'history-alias'; use_directory.symlink_to(directory)
        execute(kind, use_directory, cycle=10 if kind == 'regression' else 20,
                retention=2 if kind == 'retention' else 1, expected=1)
        require(all((directory/n).read_bytes() == b for n, b in original.items()), 'rejection modified existing history')
        rejections.append(kind)

    # Actual competing native writers and Python locked readers. Same-cycle
    # writers reject explicitly; every reader sees a complete committed image.
    concurrent = out/'concurrent'; concurrent.mkdir(); execute('concurrent-initial', concurrent, 10)
    import subprocess
    def competing(i):
        with (out/f'concurrent-{i}.log').open('w') as log:
            return subprocess.call([str(out/'verify'), str(snapshots[20]), str(concurrent), '1', 'none', 'publish'],
                                   stdout=log, stderr=subprocess.STDOUT)
    observations = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(competing, i) for i in range(8)]
        while not all(f.done() for f in futures):
            r, data = store(concurrent).select(before_target_cycle=21)
            require(data == images[r['target_cycle']], 'concurrent reader saw incomplete bytes'); observations += 1
        codes = [f.result() for f in futures]
    require(codes.count(0) == 1 and codes.count(1) == 7 and observations > 0, 'competing writers were not serialized')

    options = ['+fs-checkpoint-directory=/tmp/history', '+fs-checkpoint-interval=10',
               '+fs-checkpoint-retention=2', '+fs-checkpoint-level=1']
    run([out/'verify', 'parse', *options], out/'parser-valid.log')
    run([out/'verify', 'parse', *options, '+fs-restore=some.fsckpt'], out/'parser-restore.log')
    text = run([out/'verify', 'parse-disabled', *options], out/'parser-disabled.log', expected=1)
    require('unsupported public durable checkpoint capability' in text, 'unaudited capability accepted periodic options')
    invalid = [options[:i]+options[i+1:] for i in range(4)] + [options+[o] for o in options]
    for key in ('interval', 'retention'):
        for value in ('', '0', '-1', '+1', '1x', '18446744073709551616'):
            invalid.append([o for o in options if not o.startswith('+fs-checkpoint-'+key)] + ['+fs-checkpoint-'+key+'='+value])
    invalid += [[*options, '+fs-checkpoint=x', '+fs-checkpoint-operation=1'], [*options, '+fs-checkpoint-preflight'],
                [*options[:-1], '+fs-checkpoint-level=2'], [*options, '+fs-checkpoint-interval-typo=1']]
    for i, arguments in enumerate(invalid):
        require('REJECT parser' in run([out/'verify', 'parse', *arguments], out/f'parser-{i}.log', expected=1),
                'invalid periodic options parsed')
    summary = dict(invocation=str(out), native_python_byte_identity=True, syscall_faults=faults, killed_writers=kills,
                   special_corrupt_rejections=rejections, parser_rejections=len(invalid), concurrent_writers=8,
                   complete_reader_observations=observations, pinned_directory_replacement=True,
                   unaudited_capability_rejected=True, immutable_orphan_reuse=True,
                   immutable_conflict_rejected=True, sanitizers='ASan/UBSan')
    (out/'summary.json').write_bytes(canonical(summary)); (args.out/'summary.json').write_bytes(canonical(summary))
    print(f'PASS: native live history, {len(faults)} faults, {len(kills)} SIGKILLs, {len(rejections)} corrupt/special cases, '
          f'{len(invalid)} parser rejections, 8 competing writers and Python interop', flush=True)


if __name__ == '__main__': main()
