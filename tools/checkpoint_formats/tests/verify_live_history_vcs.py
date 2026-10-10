"""Public production target-cycle history, live retention and late-stall rewind.

Sources/builds are checked before invocation. Real live indexes are observed
under the shared history lock; the verifier never commits or prunes them.
Watchdog injection/sampling is still external to the production simulator.
Source env.sh, FireSim env.sh and vcs-env.sh LAST.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from tools.checkpoint_formats.aggregate_packed import decode_aggregate
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.durable import atomic_output
from tools.checkpoint_formats.rolling import CycleSchedule, NativeRollingHistory
from tools.checkpoint_formats.tests.verify_rolling_history_vcs import replay
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production', type=Path, required=True)
    parser.add_argument('--reference-production', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--watchdog-ms',type=int,default=0,
                        help='Exercise production host/cycle monitor and bounded capture accounting')
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    production = args.production.resolve()
    sources = json.loads((production/'native-build-inputs.json').read_text())['sources']
    require(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h for p, h in sources.items()),
            'production executable predates current sources')
    build, manifest, generated, layout = [json.loads((production/n).read_text()) for n in
        ('aggregate-build.json', 'runtime-manifest.json', 'generated-manifest.json', 'harness-layout.json')]
    reference_production = args.reference_production.resolve()
    require(json.loads((reference_production/'generated-manifest.json').read_text()) == generated and
            json.loads((reference_production/'target-port-layout.json').read_text()) ==
            json.loads((production/'target-port-layout.json').read_text()), 'different reference RTL/ports')
    require((reference_production/'default/reference/run.log').read_text().endswith('exit=0\n'),
            'reference has not completed')
    reference = (reference_production/'default/reference/ports.trace').read_bytes()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    print('LIVE_HISTORY_VERIFICATION_OUTPUT '+str(out), flush=True)
    common = [production/'simv', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
              '+memsize=4194304', '+max-cycles=1000000']
    history_args = dict(build=build, manifest=manifest, generated=generated, layout=layout, retention=2)

    def options(history, interval):
        return ['+fs-checkpoint-directory='+str(history), '+fs-checkpoint-interval='+str(interval),
                '+fs-checkpoint-retention=2', '+fs-checkpoint-level=1']

    watchdog_options = ([f'+fs-checkpoint-host-timeout-ms={args.watchdog_ms}',
                         f'+fs-checkpoint-cycle-timeout-ms={args.watchdog_ms}',
                         '+fs-checkpoint-capture-timeout-ms=600000'] if args.watchdog_ms else [])

    bad_directory = out/'invalid-output'
    good_options = options(bad_directory, 10)
    invalid = [good_options[:i]+good_options[i+1:] for i in range(4)] + [good_options+[o] for o in good_options]
    for key in ('interval', 'retention'):
        for value in ('', '0', '-1', '+1', '1x', '18446744073709551616'):
            invalid.append([o for o in good_options if not o.startswith('+fs-checkpoint-'+key)] +
                           ['+fs-checkpoint-'+key+'='+value])
    invalid += [[*good_options, '+fs-checkpoint='+str(out/'single'), '+fs-checkpoint-operation=3'],
                [*good_options, '+fs-checkpoint-preflight'], [*good_options[:-1], '+fs-checkpoint-level=2'],
                [*good_options, '+fs-checkpoint-interval-typo=1'],
                [*good_options, '+test-live-periodic='+str(out/'single'), '+test-live-interval=10'],
                [*good_options, '+test-live-capture='+str(out/'single')],
                [*good_options, '+fs-driver-cut=3', '+fs-driver-settled', '+fs-driver-lowclock',
                 '+fs-driver-diagnostic='+str(out/'diagnostic')],
                [*good_options], [*good_options, '+fs-checkpoint-directory=']]
    for i, request in enumerate(invalid):
        text = run([*common, *request], out/f'invalid-{i}.log', out, expected=1)
        require('FS_CHECKPOINT_ENTRY_ERROR' in text and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text,
                'invalid public periodic configuration reached platform')
        require(not bad_directory.exists() and not (out/'single').exists() and not (out/'diagnostic').exists(),
                'invalid options created outputs')

    def capture(directory, *, interval, origin, expected, restore=None):
        directory.mkdir(); history = directory/'history'; history.mkdir(); observed = directory/'observed'; observed.mkdir()
        trace = directory/'ports.trace'; native = directory/'loaded-native.txt'
        argv = [*common, *options(history, interval), *watchdog_options, '+target_port_trace='+str(trace)]
        if restore: argv += ['+fs-restore='+str(restore), '+test-loaded-native='+str(native)]
        store = NativeRollingHistory(history, **history_args)
        captures, observations = {}, []
        def observe():
            # Take the SAME lock as native commit. No index publication/recovery
            # API is invoked, so live retention is performed solely by runtime.
            with store._locked() as fd:
                index = store._index(fd)
                records = index['records']
                if not records: return
                require(len(records) == len(list(history.glob('*.fsckpt'))) <= 2, 'live retention exceeded bound')
                if not observations or observations[-1]['records'] != records:
                    observations.append(dict(monotonic_ns=time.monotonic_ns(), records=records))
                for record in records:
                    if record['target_cycle'] not in captures:
                        data = store._image(fd, record)
                        doc = decode_aggregate(data, build, manifest, generated, layout)
                        sample = int(next(r['value'] for r in doc['records'] if r['owner'] == 'cut/host_sample'), 16)
                        path = observed/(str(record['target_cycle'])+'.fsckpt')
                        with atomic_output(path, binary=True) as stream: stream.write(data)
                        captures[record['target_cycle']] = dict(record, path=str(path), host_sample=sample)
        started = time.monotonic()
        with (directory/'run.log').open('w') as log:
            log.write('argv='+json.dumps([str(a) for a in argv])+'\n'); log.flush()
            process = subprocess.Popen([str(a) for a in argv], cwd=directory, stdout=log, stderr=subprocess.STDOUT)
            try:
                while process.poll() is None:
                    require(time.monotonic()-started < 600, 'public live history capture exceeded timeout')
                    if (history/'history.json').exists(): observe()
                    time.sleep(0.05)
                code = process.wait(); observe()
            finally:
                if process.poll() is None: process.kill(); process.wait()
            log.write(f'exit={code}\n')
        text = (directory/'run.log').read_text()
        require(code == 0 and '*** PASSED ***' in text and 'Target Cycles Emulated: 774628\n' in text,
                'public live history failed completion')
        require(trace.read_bytes() == expected, 'history capture changed target ports/timing')
        published = re.findall(r'FS_DURABLE_PERIODIC_CAPTURE_PUBLISHED target_cycle=(\d+) host_sample=(\d+) history_committed=1', text)
        require(len(published) == len(captures) > 1, 'observer missed a live history commit')
        if args.watchdog_ms:
            accounted=re.findall(r'FS_CHECKPOINT_WATCHDOG_CAPTURE_ACCOUNTED target_cycle=(\d+) elapsed_ns=(\d+) total_ns=(\d+) captures=(\d+)',text)
            require('FS_CHECKPOINT_WATCHDOG_ARMED' in text and len(accounted)==len(published) and
                    [int(r[0]) for r in accounted]==[int(r[0]) for r in published] and
                    any(int(r[1])>args.watchdog_ms*1000000 for r in accounted),
                    'runtime capture exclusion not exercised beyond the progress timeout')
            total=0
            for number,(_,elapsed,accumulated,count) in enumerate(accounted,1):
                total+=int(elapsed)
                require(int(accumulated)==total and int(count)==number,'incorrect capture time accounting')
        policy = CycleSchedule(interval, origin)
        cuts = [captures[c] for c in sorted(captures)]
        for i, (cut, (cycle, sample)) in enumerate(zip(cuts, published)):
            require(cut['target_cycle'] == int(cycle) and cut['host_sample'] == int(sample) and
                    policy.due(int(cycle)) and int(cycle) < origin+(i+2)*interval, 'invalid live target-cycle deadline')
            policy.committed(int(cycle))
        require([r['target_cycle'] for r in observations[-1]['records']] == [r['target_cycle'] for r in cuts[-2:]],
                'runtime did not retain newest complete cuts')
        if restore:
            require('PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in text and
                    'PRODUCTION_BOOTSTRAP zero_edges=1' in text, 'restored periodic capture advanced before readback')
            doc = decode_aggregate(restore.read_bytes(), build, manifest, generated, layout)
            require(dict(line.split() for line in native.read_text().splitlines()) ==
                    {r['owner'][5:]: r['value'] for r in doc['records'] if r['owner'].startswith('host/')},
                    'restored periodic native pre-edge payload changed')
        (directory/'observations.json').write_bytes(canonical(observations))
        return store, cuts, observations

    store, initial, observations = capture(out/'periodic', interval=250000, origin=0, expected=reference)
    require(len(initial) == 3 and len(observations) == 3, 'expected three actual live history commits')
    # Read retained state without changing the live-produced history index.
    record, image = store.select(before_target_cycle=initial[-1]['target_cycle'])
    selected = next(r for r in initial if r['target_cycle'] == record['target_cycle'])
    expected = b''.join(reference.splitlines(keepends=True)[selected['host_sample']:])
    results = [replay(production, out/'stalled', image, expected, record['target_cycle'], resume=False),
               replay(production, out/'replayed', image, expected, record['target_cycle'], resume=True)]
    doc = decode_aggregate(image, build, manifest, generated, layout)
    native = {r['owner'][5:]: r['value'] for r in doc['records'] if r['owner'].startswith('host/')}
    for result in results:
        require(dict(line.split() for line in Path(result['native_readback']).read_text().splitlines()) == native,
                'retained replay changed native pre-edge state')
    _, restored, _ = capture(out/'restored-periodic', interval=100000, origin=record['target_cycle'],
                             expected=expected, restore=Path(results[0]['checkpoint']))
    require(len(restored) == 2, 'expected two live retained restored-run recaptures')
    restored_reference = (out/'restored-periodic/ports.trace').read_bytes().splitlines(keepends=True)
    for i, cut in enumerate(restored):
        case = out/f'recapture-replay-{i}'; case.mkdir(); trace = case/'ports.trace'; readback = case/'loaded-native.txt'
        text = run([*common, '+fs-restore='+cut['path'], '+target_port_trace='+str(trace),
                    '+test-loaded-native='+str(readback)], case/'run.log', case)
        require('*** PASSED ***' in text and 'PRODUCTION_BOOTSTRAP zero_edges=1' in text and
                trace.read_bytes() == b''.join(restored_reference[cut['host_sample']:]), 'recapture continuation differs')
        doc = decode_aggregate(Path(cut['path']).read_bytes(), build, manifest, generated, layout)
        require(dict(line.split() for line in readback.read_text().splitlines()) ==
                {r['owner'][5:]: r['value'] for r in doc['records'] if r['owner'].startswith('host/')},
                'recapture pre-edge native state differs')
    # Invalid existing histories and special files reject before platform/worker.
    runtime_rejections = []
    for fault in ('binding', 'retention', 'corrupt-image', 'index-fifo', 'index-symlink', 'directory-symlink'):
        directory = out/('invalid-history-'+fault); directory.mkdir(); clone = directory/'history'
        shutil.copytree(out/'periodic/history', clone)
        index = clone/'history.json'; index_doc = json.loads(index.read_text())
        if fault in ('binding', 'retention'):
            index_doc[fault] = '0'*64 if fault == 'binding' else 3; index.write_bytes(canonical(index_doc))
        elif fault == 'corrupt-image': (clone/index_doc['records'][0]['name']).write_bytes(b'corrupt')
        elif fault.startswith('index-'):
            index.rename(clone/'original-index')
            if fault == 'index-fifo': os.mkfifo(index)
            else: index.symlink_to(clone/'original-index')
        use_directory = clone
        if fault == 'directory-symlink':
            use_directory = directory/'alias'; use_directory.symlink_to(clone)
        before = {p.name: p.read_bytes() for p in clone.iterdir() if p.is_file() and not p.is_symlink()}
        text = run([*common, *options(use_directory, 250000)], directory/'run.log', directory, expected=1)
        require('FS_CHECKPOINT_ENTRY_ERROR' in text and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text and
                all((clone/n).read_bytes() == b for n, b in before.items()), 'bad live history reached platform or changed inputs')
        runtime_rejections.append(fault)
    early = out/'early-reset-restore'; early.mkdir(); history = early/'history'; history.mkdir()
    text = run([*common, '+fs-restore='+str(production/'default/cut-3/capture.fsckpt'),
                *options(history, 100000)], early/'run.log', early, expected=1)
    require('periodic restore during initial target reset is unsupported' in text and
            'PRODUCTION_BOOTSTRAP' not in text and not list(history.glob('*.fsckpt')), 'early-reset restore accepted')
    require(store.select(before_target_cycle=initial[-1]['target_cycle']) == (record, image), 'replays changed retained state')
    summary = dict(invocation=str(out), initial_live_cuts=initial, restored_live_cuts=restored,
                   live_index_observations=observations, retained=observations[-1]['records'], selected=record,
                   replays=results, parser_rejections=len(invalid), history_rejections=runtime_rejections,
                   reference_production=str(reference_production), native_owners=len(native),
                   generated_words=sum(e['depth'] for e in generated['state']), early_reset_restore_rejected=True,
                   public_periodic_configuration=True, live_retained_history_commit=True,
                   production_watchdog_sampling=bool(args.watchdog_ms), watchdog_ms=args.watchdog_ms,
                   host_stall_injection='external SIGSTOP', physical_fpga_validated=False)
    (out/'summary.json').write_bytes(canonical(summary))
    (args.out/'latest.json').write_bytes(canonical(dict(invocation=str(out), summary=str(out/'summary.json'))))
    print('PASS: public live target-cycle history commits/retention, two late-stall retained replays, '
          'two restored-run recaptures and fresh all-owner continuations', flush=True)


if __name__ == '__main__': main()
