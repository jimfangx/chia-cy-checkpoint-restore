"""Repeated live target-cycle cuts, restored-run capture and retained replay.

The production collector/dispatcher is exercised using paired test controls.
Retained-history admission happens after the live run; public live commit and
production watchdog sampling are not established by this verifier.
Source env.sh, FireSim env.sh, then vcs-env.sh LAST.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.aggregate_packed import decode_aggregate
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.rolling import CycleSchedule, RollingHistory
from tools.checkpoint_formats.tests.verify_rolling_history_vcs import replay
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reference-production', type=Path,
                        help='Independent completed reference with identical generated RTL/port layout')
    parser.add_argument('--initial-capture', type=Path,
                        help='Recheck an already completed identical initial live run; run every remaining check afresh')
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    production = args.production.resolve()
    sources = json.loads((production/'native-build-inputs.json').read_text())['sources']
    require(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h for p, h in sources.items()),
            'production executable predates current sources')
    build, manifest, generated, layout = [json.loads((production/n).read_text()) for n in
        ('aggregate-build.json', 'runtime-manifest.json', 'generated-manifest.json', 'harness-layout.json')]
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    print('PERIODIC_VERIFICATION_OUTPUT '+str(out), flush=True)
    common = [production/'simv', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
              '+memsize=4194304', '+max-cycles=1000000']
    initial_restore = production/'default/cut-3/capture.fsckpt'
    prefix = out/'snapshot'
    destination = '+test-live-periodic='+str(prefix)
    interval = '+test-live-interval='
    invalid = [[destination], [interval+'10'], [destination, interval+'10', destination],
               [destination, interval+'10', interval+'10'],
               [destination, interval+'10', '+fs-checkpoint-preflight'],
               [destination, interval+'10', '+fs-checkpoint='+str(out/'single'), '+fs-checkpoint-operation=3'],
               [destination, interval+'10', '+test-live-capture='+str(out/'single')],
               [destination, interval+'10', '+fs-driver-cut=3', '+fs-driver-settled',
                '+fs-driver-lowclock', '+fs-driver-diagnostic='+str(out/'diagnostic')],
               [destination, '+test-live-interval'], [destination, '+test-live-interval-typo=10'],
               ['+test-live-periodic', interval+'10'], ['+test-live-periodic=', interval+'10']]
    invalid += [[destination, interval+v] for v in ('', '0', '-1', '+1', '1x', '18446744073709551616')]
    for i, options in enumerate(invalid):
        text = run([*common, *options], out/f'invalid-{i}.log', out, expected=1)
        require('FS_CHECKPOINT_ENTRY_ERROR' in text and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text,
                'invalid periodic controls reached platform construction')
        require(not list(out.glob('snapshot.*.fsckpt')) and not (out/'single').exists() and
                not (out/'diagnostic').exists(), 'invalid controls touched outputs')

    def capture(directory, *, interval_cycles, origin, restore=None, expected, reuse=False):
        if not reuse: directory.mkdir()
        trace = directory/'ports.trace'
        native = directory/'loaded-native.txt'
        argv = [*common, '+test-live-periodic='+str(directory/'snapshot'),
                interval+str(interval_cycles), '+target_port_trace='+str(trace)]
        if restore:
            argv += ['+fs-restore='+str(restore), '+test-loaded-native='+str(native)]
        if reuse:
            text = (directory/'run.log').read_text()
            recorded = next(line[5:] for line in text.splitlines() if line.startswith('argv='))
            require(json.loads(recorded) == [str(a) for a in argv] and text.endswith('exit=0\n') and
                    _toolchain.VCS_VERSION in text, 'reused run is incomplete or has different inputs')
        else:
            text = run(argv, directory/'run.log', directory)
        require('*** PASSED ***' in text and 'Target Cycles Emulated: 774628\n' in text,
                'periodic live run failed completion')
        require(trace.read_bytes() == expected, 'periodic polling changed target-visible timing/ports')
        published = re.findall(r'FS_DURABLE_PERIODIC_CAPTURE_PUBLISHED target_cycle=(\d+) host_sample=(\d+)', text)
        paths = sorted(directory.glob('snapshot.*.fsckpt'), key=lambda p: int(p.name.split('.')[1]))
        require(len(paths) == len(published) > 1, 'missing repeated live images')
        policy = CycleSchedule(interval_cycles, origin)
        records = []
        for path, (reported_cycle, reported_sample) in zip(paths, published):
            doc = decode_aggregate(path.read_bytes(), build, manifest, generated, layout)
            cycle = doc['target_cycle']
            sample = int(next(r['value'] for r in doc['records'] if r['owner'] == 'cut/host_sample'),16)
            require(cycle == int(reported_cycle) == int(path.name.split('.')[1]) and
                    sample == int(reported_sample) and policy.due(cycle), 'invalid live cut/deadline')
            # The first eligible operation cut must not skip a target period.
            require(cycle < origin+(len(records)+2)*interval_cycles, 'target deadline skipped by live poller')
            policy.committed(cycle)
            records.append(dict(path=str(path), target_cycle=cycle, host_sample=sample,
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if restore:
            require('PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in text and
                    'PRODUCTION_BOOTSTRAP zero_edges=1' in text, 'periodic restore advanced before readback')
            original = decode_aggregate(restore.read_bytes(), build, manifest, generated, layout)
            require(dict(line.split() for line in native.read_text().splitlines()) ==
                    {r['owner'][5:]: r['value'] for r in original['records'] if r['owner'].startswith('host/')},
                    'restored periodic run changed native pre-edge payloads')
        return records

    reference_production = args.reference_production.resolve() if args.reference_production else production
    require(json.loads((reference_production/'generated-manifest.json').read_text()) == generated and
            json.loads((reference_production/'target-port-layout.json').read_text()) ==
            json.loads((production/'target-port-layout.json').read_text()), 'different reference RTL/ports')
    require((reference_production/'default/reference/run.log').read_text().endswith('exit=0\n'),
            'reference run has not completed')
    reference = (reference_production/'default/reference/ports.trace').read_bytes()
    initial_directory = out/'periodic'
    if args.initial_capture:
        initial_directory = args.initial_capture.resolve()
        (out/'periodic').symlink_to(initial_directory, target_is_directory=True)
    initial = capture(initial_directory, interval_cycles=250000, origin=0, expected=reference,
                      reuse=bool(args.initial_capture))
    require(len(initial) == 3, 'expected three target-cycle snapshots from one live process')
    early = out/'early-reset-restore'; early.mkdir()
    text = run([*common, '+fs-restore='+str(initial_restore),
                '+test-live-periodic='+str(early/'snapshot'), interval+'100000'],
               early/'run.log', early, expected=1)
    require('periodic restore during initial target reset is unsupported' in text and
            'PRODUCTION_BOOTSTRAP' not in text and not list(early.glob('*.fsckpt')),
            'early reset restore did not fail explicitly before bootstrap/publication')
    history = out/'history'; history.mkdir()
    store = RollingHistory(history, retention=2, build=build, manifest=manifest, generated=generated, layout=layout)
    for record in initial: store.publish(Path(record['path']).read_bytes())
    retained = store.recover()
    require(len(retained) == len(list(history.glob('*.fsckpt'))) == 2, 'incorrect bounded retention')
    record, image = store.select(before_target_cycle=initial[-1]['target_cycle'])
    selected = next(r for r in initial if r['target_cycle'] == record['target_cycle'])
    expected = b''.join(reference.splitlines(keepends=True)[selected['host_sample']:])
    results = [replay(production, out/'stalled', image, expected, record['target_cycle'], resume=False),
               replay(production, out/'replayed', image, expected, record['target_cycle'], resume=True)]
    original = decode_aggregate(image, build, manifest, generated, layout)
    native_values = {r['owner'][5:]: r['value'] for r in original['records'] if r['owner'].startswith('host/')}
    for result in results:
        require(dict(line.split() for line in Path(result['native_readback']).read_text().splitlines()) == native_values,
                'retained late-stall replay changed native pre-edge payloads')
    restored = capture(out/'restored-periodic', interval_cycles=100000, origin=record['target_cycle'],
                       restore=Path(results[0]['checkpoint']), expected=expected)
    require(len(restored) == 2, 'expected two live images captured during restored continuation')
    restored_reference = (out/'restored-periodic/ports.trace').read_bytes().splitlines(keepends=True)
    # Every recaptured image must itself be usable by a fresh all-owner restore.
    for index, cut in enumerate(restored):
        case = out/f'recapture-replay-{index}'; case.mkdir()
        trace = case/'ports.trace'; native = case/'loaded-native.txt'
        text = run([*common, '+fs-restore='+cut['path'], '+target_port_trace='+str(trace),
                    '+test-loaded-native='+str(native)], case/'run.log', case)
        require('*** PASSED ***' in text and 'PRODUCTION_BOOTSTRAP zero_edges=1' in text and
                trace.read_bytes() == b''.join(restored_reference[cut['host_sample']:]),
                'fresh recapture replay changed the continuation')
        doc = decode_aggregate(Path(cut['path']).read_bytes(), build, manifest, generated, layout)
        require(dict(line.split() for line in native.read_text().splitlines()) ==
                {r['owner'][5:]: r['value'] for r in doc['records'] if r['owner'].startswith('host/')},
                'recapture native state changed before first edge')
    require(store.select(before_target_cycle=initial[-1]['target_cycle']) == (record, image),
            'replays changed retained image')
    summary = dict(invocation=str(out), initial_live_cuts=initial, restored_live_cuts=restored,
                   retained=retained, selected=record, replays=results, parser_rejections=len(invalid),
                   initial_restore_fixture=str(initial_restore), generated_words=sum(e['depth'] for e in generated['state']),
                   reference_production=str(reference_production),
                   initial_capture_reused=str(initial_directory) if args.initial_capture else None,
                   early_reset_restore_rejected=True,
                   native_owners=len(native_values), periodic_runtime_capture_integrated=True,
                   public_periodic_configuration=False, live_retained_history_commit=False,
                   production_watchdog_sampling=False, physical_fpga_validated=False)
    (out/'summary.json').write_bytes(canonical(summary))
    (args.out/'latest.json').write_bytes(canonical(dict(invocation=str(out), summary=str(out/'summary.json'))))
    print('PASS: three live target-cycle cuts, two retained, two late host stalls, '
          'two restored-run recaptures and fresh all-owner continuations', flush=True)


if __name__ == '__main__': main()
