"""Full-size retained M4 images: fresh VCS replay and injected host stall.

The snapshots originate from separate existing live-capture cases, not a
periodic capture runtime. SIGSTOP is an external late worker-stall injection.
This establishes retained-image replay/host detection, not full M5 acceptance.
Run after sourcing vcs-env.sh LAST. All new evidence is written under --out.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.durable import atomic_output
from tools.checkpoint_formats.rolling import CycleSchedule, ProgressWatchdogs, RollingHistory
from tools.checkpoint_formats.tests.verify_production_aggregate_vcs import compare_target_trace
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT


def replay(production, directory, image, expected, cycle, *, resume):
    directory.mkdir()
    checkpoint = directory/'restore.fsckpt'
    with atomic_output(checkpoint, binary=True) as stream: stream.write(image)
    trace = directory/'ports.trace'
    native = directory/'loaded-native.txt'
    argv = [str(production/'simv'), '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
            '+memsize=4194304', '+max-cycles=1000000', f'+fs-restore={checkpoint}',
            f'+target_port_trace={trace}', f'+test-loaded-native={native}']
    cutoff = 600000
    started = time.monotonic_ns()
    stopped = detected = None
    host_rows = 0
    target = cycle
    offset = 0
    fragment = b''
    watchdog = None
    with (directory/'run.log').open('w') as log:
        log.write('argv='+json.dumps(argv)+'\n'); log.flush()
        process = subprocess.Popen(argv, cwd=directory, stdout=log, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                now = time.monotonic_ns()
                require(now - started < 240_000_000_000, 'VCS replay exceeded timeout')
                if trace.exists():
                    with trace.open('rb') as stream:
                        stream.seek(offset); chunk = stream.read(); offset += len(chunk)
                    rows = (fragment + chunk).split(b'\n'); fragment = rows.pop()
                    if rows:
                        target = int(rows[-1].split()[0]); host_rows += len(rows)
                if stopped is None and target >= cutoff:
                    process.send_signal(signal.SIGSTOP)
                    # Confirm the process is actually parked, independently of
                    # any generated RTL/driver diagnostic or wall-clock guess.
                    require(os.waitpid(process.pid, os.WUNTRACED)[1] == (signal.SIGSTOP << 8 | 0x7f),
                            'process did not stop for injected host stall')
                    stopped = dict(monotonic_ns=now, target_cycle=target, host_rows=host_rows,
                                   pid=process.pid, injection='SIGSTOP')
                    watchdog = ProgressWatchdogs(host_timeout_ns=300_000_000)
                if watchdog is not None and detected is None:
                    reason = watchdog.sample(monotonic_ns=now, host_progress=host_rows, target_cycle=target)
                    if reason:
                        require(reason == 'host_progress_stall', 'wrong watchdog classified stopped worker')
                        detected = dict(reason=reason, monotonic_ns=now, target_cycle=target, host_rows=host_rows)
                        if resume: process.send_signal(signal.SIGCONT)
                        else: process.kill()
                time.sleep(0.02)
            code = process.wait()
        finally:
            if process.poll() is None: process.kill(); process.wait()
        log.write(f'exit={code}\n')
    require(stopped is not None and detected is not None, 'late stall injection/detection was not exercised')
    require(code == (0 if resume else -signal.SIGKILL), 'unexpected injected replay exit')
    actual = trace.read_bytes()
    require(expected.startswith(actual), 'stalled continuation differs from uninterrupted transaction trace')
    text = (directory/'run.log').read_text()
    require('PRODUCTION_BOOTSTRAP zero_edges=1' in text and
            'PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in text,
            'fresh replay advanced before complete state load')
    if resume:
        require('*** PASSED ***' in text and 'Target Cycles Emulated: 774628\n' in text and actual == expected,
                'resumed late-stall replay did not match full continuation/completion')
    result = dict(argv=argv, cwd=str(directory), exit=code, stopped=stopped, detected=detected,
                  compared_bytes=len(actual), complete_rows=actual.count(b'\n'),
                  partial_last_row_bytes=len(actual.rsplit(b'\n', 1)[-1]), resumed_to_completion=resume,
                  zero_edge_bootstrap=True, trace=str(trace), checkpoint=str(checkpoint),
                  native_readback=str(native), log=str(directory/'run.log'))
    (directory/'result.json').write_bytes(canonical(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    production = args.production.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    print('ROLLING_VERIFICATION_OUTPUT '+str(out), flush=True)
    inputs = json.loads((production/'native-build-inputs.json').read_text())['sources']
    require(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == value for p, value in inputs.items()),
            'production executable predates current source')
    build, manifest, generated, layout = [json.loads((production/name).read_text()) for name in
        ('aggregate-build.json', 'runtime-manifest.json', 'generated-manifest.json', 'harness-layout.json')]
    history = out/'history'; history.mkdir()
    store = RollingHistory(history, retention=2, build=build, manifest=manifest, generated=generated, layout=layout)
    source_summary = json.loads((production/'summary.json').read_text())
    cases = sorted((c for c in source_summary['cases'] if c['timing'] == 'default'), key=lambda c: c['target_cycle'])
    require([c['target_cycle'] for c in cases] == [0, 1, 524402, 524404], 'missing complete live-cut cases')
    schedule = CycleSchedule(2)
    publications = []
    for case in cases:
        source = production/'default'/f'cut-{case["cut"]}'/'capture.fsckpt'
        record = store.publish(source.read_bytes())
        # The first two are seeded boot history. Later actual cuts cross the
        # target deadline; a large gap does not invent intervening snapshots.
        if schedule.due(case['target_cycle']): schedule.committed(case['target_cycle'])
        publications.append(dict(record, source=str(source)))
    retained = store.recover()
    require([r['target_cycle'] for r in retained] == [524402, 524404] and
            len(list(history.glob('*.fsckpt'))) == 2, 'bounded history retained wrong cuts')
    record, image = store.select(before_target_cycle=524404)
    require(record['target_cycle'] == 524402, 'causal-bound selection was not strictly earlier')
    case = next(c for c in cases if c['target_cycle'] == record['target_cycle'])
    expected = b''.join((production/'default/reference/ports.trace').read_bytes().splitlines(keepends=True)[case['host_sample']:])
    fields = json.loads((production/'target-port-layout.json').read_text())
    results = [replay(production, out/'stalled', image, expected, record['target_cycle'], resume=False),
               replay(production, out/'replayed', image, expected, record['target_cycle'], resume=True)]
    from tools.checkpoint_formats.aggregate_packed import decode_aggregate
    doc = decode_aggregate(image, build, manifest, generated, layout)
    native = {r['owner'][5:]: r['value'] for r in doc['records'] if r['owner'].startswith('host/')}
    for result in results:
        actual = dict(line.split() for line in Path(result['native_readback']).read_text().splitlines())
        require(actual == native, 'fresh retained replay changed opaque native pre-edge state')
    compare_target_trace(expected.decode().splitlines(keepends=True),
        Path(results[1]['trace']).read_text().splitlines(keepends=True), fields, case['cut'], case['host_sample'])
    require(store.select(before_target_cycle=524404) == (record, image), 'replays modified retained checkpoint')
    summary = dict(invocation=str(out), publications=publications, retained=retained, selected=record,
                   replays=results, generated_words=sum(e['depth'] for e in generated['state']),
                   native_owners=len(native), all_transaction_ports=len(fields),
                   periodic_runtime_capture_integrated=False, target_watchdog_runtime_integrated=False,
                   host_injection='external SIGSTOP', physical_fpga_validated=False)
    (out/'summary.json').write_bytes(canonical(summary))
    (args.out/'latest.json').write_bytes(canonical(dict(invocation=str(out), summary=str(out/'summary.json'))))
    print('PASS: four complete live images, two retained; two detected late host stalls; '
          'fresh retained replay matches all continuation bytes through completion', flush=True)


if __name__ == '__main__': main()
