"""Actual FCFS completed-operation cuts. Software diagnostics, not .fsckpt.

The production simulation flow performs incremental dispatch with VCS parked
in DPI at each hook. Captures retain explicit unsupported owners and are never
loaded as full checkpoints. Compare full generated-state observations and
completion counts to uninterrupted runs so the hook cannot add target edges.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.widget_inventory import check_widget_inventory
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
TESTS = Path(__file__).resolve().parent


def read_diagnostic(path):
    data = path.read_bytes()
    require(data[:8] == b'FSDIAG01', 'wrong diagnostic magic')
    pos = 8
    def integer():
        nonlocal pos
        require(pos + 8 <= len(data), 'truncated diagnostic integer')
        value, = struct.unpack_from('<Q', data, pos)
        pos += 8
        return value
    def blob():
        nonlocal pos
        size = integer()
        require(size <= len(data) - pos, 'truncated diagnostic blob')
        value = data[pos:pos + size]
        pos += size
        return value
    cut, count = integer(), integer()
    require(0 < count < 10000, 'invalid owner count')
    owners = {}
    for _ in range(count):
        identity, schema, payload = blob().decode(), blob().decode(), blob()
        require(identity and identity not in owners, 'duplicate/empty identity')
        require(schema or not payload, 'unsupported owner has payload')
        owners[identity] = (schema, payload)
    require(pos == len(data), 'trailing diagnostic data')
    return cut, owners


def words(payload):
    require(len(payload) % 8 == 0, 'unexpected payload shape')
    return struct.unpack('<' + 'Q' * (len(payload) // 8), payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    require(os.environ['VCS_HOME'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh last')
    require(os.environ['CXX'] == '/usr/bin/g++-13', 'keep system GCC/G++ 13')
    native = out / 'boundary-native'
    run([os.environ['CXX'], '-std=c++20', '-Wall', '-Wextra', '-Werror', '-g', '-no-pie',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer', f'-I{CC}',
         TESTS / 'driver_boundary_diagnostic.cc', CC / 'core/driver_boundary_diagnostic.cc',
         CC / 'core/stepped_run_loop.cc', CC / 'core/systematic_scheduler.cc',
         CC / 'emul/host_timing.cc', '-o', native], out / 'native-build.log')
    native_out = out / 'native'
    native_out.mkdir(exist_ok=True)
    result = run([native, native_out], out / 'native.log')
    require('PASS:' in result, 'native guards failed')
    cut, captured = read_diagnostic(native_out / 'good.diag')
    require(cut == 2 and captured == {'test/a': ('test.owner.v1', b'*'),
                                    'test/unsupported': ('', b''), 'test/missing': ('', b'')},
            'native inventory/payload differs')
    binary = args.build.resolve() / 'f2/f2-fasedtests-AXI4Fuzzer-FCFSConfig-FCFS16GBQuadRank_DefaultF1Config/AXI4Fuzzer'
    reference = json.loads((args.reference / 'summary.json').read_text())
    common = ['+vcs+initreg+0', '+vcs+initmem+0', '+memsize=4194304', '+max-cycles=1000000']
    cases = []
    for cut in (3, 11, 101, 10001):
        case = out / f'cut-{cut}'
        case.mkdir(exist_ok=True)
        diagnostic, rtl = case / 'software.diag', case / 'generated.jsonl'
        diagnostic.unlink(missing_ok=True)
        log = run([binary, *common, f'+fs-driver-cut={cut}', f'+fs-driver-diagnostic={diagnostic}',
                   f'+generated_capture={rtl}'], case / 'run.log', case)
        require('*** PASSED ***' in log and 'Target Cycles Emulated: 774628' in log,
                'diagnostic changed fuzzer completion/timing')
        with rtl.open('rb') as stream:
            hasher = hashlib.sha256()
            for block in iter(lambda: stream.read(1 << 20), b''):
                hasher.update(block)
            digest = hasher.hexdigest()
        require(digest == reference['capture_sha256'], 'hook changed complete generated-state observations')
        observed_cut, owners = read_diagnostic(diagnostic)
        require(observed_cut == cut, 'wrong operation cut')
        unsupported = [key for key, (schema, _) in owners.items() if not schema]
        supported = {key: payload for key, (schema, payload) in owners.items() if schema}
        audited_widgets, unsupported_widgets = check_widget_inventory(owners, (binary.parent / 'FireSim-generated.const.h').read_text())
        require(unsupported_widgets == {'widget/2'}, 'FASED ownership changed')
        require(set(('widget/2', 'runtime/simulation', 'generated/rtl', 'runtime/harness',
                     'runtime/execution-context')) <= set(unsupported), 'unaudited owners omitted')
        require(set(supported) == {'runtime/mmio', 'runtime/host-timing', 'runtime/scheduler',
                                  'runtime/simulation/fased-run-loop',
                                  *audited_widgets,
                                  *[f'runtime/functional-memory/{i}' for i in range(4)]},
                'unexpected supported software inventory')
        loop, scheduler, timing = (words(supported[key]) for key in
            ('runtime/simulation/fased-run-loop', 'runtime/scheduler', 'runtime/host-timing'))
        require(loop[:2] == (0x3154504B434C5253, 1) and loop[5] == 0, 'wrong production run-loop payload')
        require(scheduler[:2] == (0x3154504B43484353, 1) and scheduler[5] == 1000000,
                'issued credit must be distinct from completed target time')
        # The timing adapter's payload owns configuration, MT state and delay
        # progress. The production hook must see zero remaining synchronous ticks.
        require(timing[0] == 0x3154504B434D5448 and timing[5] == 0, 'suspended host delay captured')
        memory_states = []
        for i in range(4):
            payload = supported[f'runtime/functional-memory/{i}']
            header = struct.unpack_from('<' + 'Q' * 13, payload)
            require(header[0] == 0x3154504B434D4D46 and header[5] == 4194304,
                    'functional memory is incomplete')
            queue_offset = 13 * 8 + header[5] + header[4] // 8
            writes, = struct.unpack_from('<Q', payload, queue_offset)
            reads, = struct.unpack_from('<Q', payload, queue_offset + 8 + writes * 8)
            memory_states.append(dict(channel=i, payload_bytes=len(payload), cycle=header[7],
                                      inflight_write=bool(header[8]), queued_writes=writes, queued_reads=reads))
        cases.append(dict(cut=cut, phase=loop[3], next_bridge=loop[4], issued_credit=scheduler[5],
                          supported=list(supported), unsupported=unsupported, memories=memory_states,
                          generated_capture_sha256=digest, target_cycles=774628,
                          diagnostic=str(diagnostic)))
    # Production callback capture with an unaudited profiling closure fails;
    # incomplete diagnostics must not be published.
    negative = out / 'profile-rejected.diag'
    negative.unlink(missing_ok=True)
    log = run([binary, *common, '+profile-interval=250000', '+fs-driver-cut=3',
               f'+fs-driver-diagnostic={negative}'], out / 'profile-rejected.log', out, expected=1)
    require('unsupported anonymous/unaudited callback' in log and not negative.exists()
            and not negative.with_suffix('.diag.tmp').exists(), 'unaudited callback capture accepted')
    # Unreached requests fail before success/finalization even with a valid run.
    negative = out / 'unreached.diag'
    negative.unlink(missing_ok=True)
    log = run([binary, '+memsize=4194304', '+max-cycles=0', '+fs-driver-cut=2',
               f'+fs-driver-diagnostic={negative}'], out / 'unreached.log', out, expected=1)
    require('requested operation cut was never reached' in log and '*** PASSED ***' not in log
            and not negative.exists(), 'unreached request silently succeeded')
    gcd = args.build.resolve() / 'f2/f2-midasexamples-GCD-NoConfig-DefaultF2Config/GCD'
    negative = out / 'unsupported.diag'
    negative.unlink(missing_ok=True)
    log = run([gcd, '+fs-driver-cut=1', f'+fs-driver-diagnostic={negative}'],
              out / 'unsupported-driver.log', out, expected=1)
    require('unsupported incremental simulation driver' in log and 'FireSim fingerprint:' not in log
            and not negative.exists(), 'unsupported driver initialized')
    summary = dict(scope='parked DPI software component diagnostic; not settled RTL or full runtime restore',
                   cases=cases, native_guard_result=result.split('PASS:', 1)[1].splitlines()[0].strip(),
                   negative_production_requests=3, whole_runtime_restore_verified=False,
                   physical_fpga_validated=False)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
