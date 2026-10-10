"""Public scheduling, diagnostic-free capture/restart, and fail-closed VCS checks."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import time

from tools.checkpoint_formats.codec import canonical, encode, require
from tools.checkpoint_formats import aggregate_packed as packed
from tools.checkpoint_formats.tests.simulation_inventory import check_simulation_base
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_production_aggregate_vcs import compare_target_trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--without-hook', type=Path,
                        help='Restore-capability executable compiled without the public harness callback')
    args = parser.parse_args()
    production = args.production.resolve()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    require(os.environ['VCS_HOME'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    summary = json.loads((production/'summary.json').read_text())
    require(summary['public_durable_capture_enabled'] and len(summary['cases']) == 5,
            'incomplete public continuations')
    sources = json.loads((production/'native-build-inputs.json').read_text())['sources']
    require(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == v for p, v in sources.items()),
            'public executable predates current sources')
    invocation = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    common = [production/'simv', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
              '+memsize=4194304', '+max-cycles=1000000']
    sentinel = invocation/'output.fsckpt'; sentinel.write_bytes(b'preserve checkpoint\n')
    request = f'+fs-checkpoint={sentinel}'
    schedule = '+fs-checkpoint-operation='
    good = production/'default/cut-3/capture.fsckpt'
    invalid = [[request], [schedule+'3'], [f'+fs-restore={good}', schedule+'3'],
               [request, schedule+'3', schedule+'3'], [request, schedule+'3', request],
               [request, schedule+'3', f'+fs-restore={good}'],
               [request, schedule+'3', '+test-live-capture='+str(sentinel)],
               [request, schedule+'3', '+fs-driver-cut=4', '+fs-driver-settled', '+fs-driver-lowclock',
                '+fs-driver-diagnostic='+str(invocation/'diagnostic')],
               [request, schedule+'3', '+profile-interval=250000'],
               [request, schedule+'3', '+loadmem=unbound'],
               [request, schedule+'3', '+test-aggregate=untrusted.load'],
               [request, '+fs-checkpoint-operation'], [request, '+fs-checkpoint-operation-typo=3']]
    invalid += [[request, schedule+v] for v in ('', '0', '-1', '+1', '1x', '18446744073709551616')]
    for index, options in enumerate(invalid):
        text = run([*common, *options], invocation/f'dispatch-{index}.log', invocation, expected=1)
        require('FS_CHECKPOINT_ENTRY_ERROR' in text and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text,
                'invalid public capture reached platform construction')
        require(sentinel.read_bytes() == b'preserve checkpoint\n' and not (invocation/'diagnostic').exists(),
                'dispatch rejection touched outputs')
    special = []
    for kind in ('symlink', 'fifo', 'directory', 'missing-directory'):
        directory = invocation/kind; directory.mkdir()
        destination = directory/'output.fsckpt'
        if kind == 'symlink': destination.symlink_to(sentinel)
        elif kind == 'fifo': os.mkfifo(destination)
        elif kind == 'directory': destination.mkdir()
        else: destination = directory/'absent/output.fsckpt'
        text = run([*common, f'+fs-checkpoint={destination}', schedule+'3'], directory/'run.log',
                   directory, expected=1)
        require('FS_DURABLE_LIVE_CAPTURE_ERROR' in text and 'FS_DURABLE_LIVE_CAPTURE_PUBLISHED' not in text,
                'invalid public capture destination was published')
        require(not any(s in text for s in ('unexpected termination', 'Dumping VCS', 'Segmentation fault')),
                'public capture rejection triggered a crash dump')
        require(sentinel.read_bytes() == b'preserve checkpoint\n' and
                not list(directory.glob('.fsckpt.pending-*')), 'publication failure changed output')
        special.append(kind)
    # A valid but unreachable schedule must fail explicitly, without publication.
    def verify_unreachable():
        text = run([*common, request, schedule+'18446744073709551615'],
                   invocation/'unreachable.log', invocation, expected=1)
        require('requested operation cut was never reached' in text and
                'FS_DURABLE_LIVE_CAPTURE_PUBLISHED' not in text and
                sentinel.read_bytes() == b'preserve checkpoint\n', 'unreachable cut did not fail closed')
    unreachable_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    unreachable = unreachable_pool.submit(verify_unreachable)
    if args.without_hook:
        without_hook = args.without_hook.resolve()
        inputs = json.loads((without_hook/'native-build-inputs.json').read_text())['sources']
        require(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == v for p, v in inputs.items()),
                'callback-free executable predates current sources')
        text = run([without_hook/'simv', *common[1:], request, schedule+'3'],
                   invocation/'missing-hook.log', invocation, expected=1)
        require('public checkpoint callback did not complete publication' in text and
                'FS_DURABLE_LIVE_CAPTURE_PUBLISHED' not in text and
                sentinel.read_bytes() == b'preserve checkpoint\n', 'missing callback did not fail closed')
    fields = json.loads((production/'target-port-layout.json').read_text())
    build, runtime, generated, layout = [json.loads((production/name).read_text()) for name in (
        'aggregate-build.json', 'runtime-manifest.json', 'generated-manifest.json', 'harness-layout.json')]
    def verify_case(case):
        directory = invocation/case['timing']/f'cut-{case["cut"]}'; directory.mkdir(parents=True)
        timing = ['+fuzz-host-timing=7', '+fuzz-seed=18446744073709551615'] if case['timing'] == 'randomized' else []
        destination = directory/'capture.fsckpt'
        original = production/case['timing']/f'cut-{case["cut"]}'
        reference = production/case['timing']/'reference/ports.trace'
        started_us = time.time_ns() // 1000
        text = run([*common, *timing, f'+fs-checkpoint={destination}', schedule+str(case['cut']),
                    f'+target_port_trace={directory/"capture.trace"}'], directory/'capture.log', directory)
        finished_us = time.time_ns() // 1000
        require('*** PASSED ***' in text and text.count('FS_DURABLE_LIVE_CAPTURE_PUBLISHED') == 1,
                'public capture without diagnostic controls failed')
        image = destination.read_bytes()
        doc = packed.decode_aggregate(image, build, runtime, generated, layout)
        native = {row['owner']: (row['schema'], bytes.fromhex(next(
            r['value'] for r in doc['records'] if r['owner'] == 'host/'+row['owner'])))
                  for row in runtime['native_owners']}
        base = check_simulation_base(native)
        require(started_us <= base['start_time'] <= finished_us,
                'captured reporting timestamp is outside this process wall-clock bounds')
        # Independent processes retain distinct gettimeofday reporting baselines.
        # Check every byte after substituting only that independently bounded
        # field, then require exact native readback of the ORIGINAL timestamp.
        oracle_image = (original/'capture.fsckpt').read_bytes()
        oracle = packed.decode_aggregate(oracle_image, build, runtime, generated, layout)
        actual_row = next(r for r in doc['records'] if r['owner'] == 'host/runtime/simulation/base')
        oracle_row = next(r for r in oracle['records'] if r['owner'] == actual_row['owner'])
        actual_payload, oracle_payload = bytes.fromhex(actual_row['value']), bytes.fromhex(oracle_row['value'])
        require(len(actual_payload) == len(oracle_payload) and actual_payload[:-16] == oracle_payload[:-16]
                and actual_payload[-8:] == oracle_payload[-8:], 'base state differs outside reporting timestamp')
        actual_row['value'] = (actual_payload[:-16]+oracle_payload[-16:-8]+actual_payload[-8:]).hex()
        require(encode('fsckpt', doc) == oracle_image,
                'diagnostic-free complete image differs from independent oracle after timestamp binding')
        (directory/'reporting-timestamp.json').write_bytes(canonical(dict(
            process_start_bound_us=started_us, process_end_bound_us=finished_us,
            captured_start_time_us=base['start_time'],
            oracle_start_time_us=struct.unpack('<Q', oracle_payload[-16:-8])[0],
            all_other_image_bytes_equal=True, original_image_sha256=hashlib.sha256(image).hexdigest())))
        require((directory/'capture.trace').read_bytes() == reference.read_bytes(),
                'public scheduling changed uninterrupted transaction timing')
        restored = run([*common, *timing, f'+fs-restore={destination}',
                        f'+test-loaded-native={directory/"loaded-native.txt"}',
                        f'+target_port_trace={directory/"restore.trace"}'], directory/'restore.log', directory)
        require('*** PASSED ***' in restored and 'PRODUCTION_BOOTSTRAP zero_edges=1' in restored and
                'PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in restored and
                f'Target Cycles Emulated: {case["target_completion"]}\n' in restored,
                'diagnostic-free fresh restore did not preserve zero-edge initialization/completion')
        loaded = dict(line.split() for line in (directory/'loaded-native.txt').read_text().splitlines())
        require(loaded == {name: payload.hex() for name, (_, payload) in native.items()},
                'diagnostic-free restart changed native state, including original reporting timestamp')
        require(destination.read_bytes() == image, 'public restart modified its durable input')
        compare_target_trace(reference.read_text().splitlines(keepends=True)[case['host_sample']:],
                             (directory/'restore.trace').read_text().splitlines(keepends=True),
                             fields, case['cut'], case['host_sample'])
        print('PASS: diagnostic-free public capture/restart', case['timing'], case['cut'], flush=True)
        return dict(**case, checkpoint=str(destination), diagnostic_controls=False,
                    independently_bounded_reporting_timestamp=True, exact_native_pre_edge_readback=True)
    # The executable is immutable; each process has distinct inputs/outputs.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        cases = list(pool.map(verify_case, summary['cases']))
    unreachable.result()
    unreachable_pool.shutdown(wait=True)
    result = dict(invocation=str(invocation), dispatch_rejections=len(invalid), special_destinations=special,
                  unreachable_cut_rejected=True, missing_hook_rejected=bool(args.without_hook),
                  cases=cases, output_sentinel_preserved=True)
    (out/'summary.json').write_bytes(canonical(result))
    print(f'PASS: {len(invalid)} public scheduling rejections, four publication failures, unreachable cut, '
          'and all five diagnostic-free public capture/restarts', flush=True)


if __name__ == '__main__': main()
