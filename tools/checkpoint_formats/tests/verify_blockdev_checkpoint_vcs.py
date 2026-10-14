"""Complete exact-Rocket blockdev host component: sanitized native and fresh VCS.

The MMIO service is a deterministic component fixture. Its cycle labels are
fixture labels, not captured Rocket target cycles; no CPU acceptance is inferred.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

TESTS = Path(__file__).resolve().parent
CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
BRIDGES = ROOT / 'generators/firechip/bridgestubs/src/main/cc'
OPERATIONS = 14
CONFIG_BYTES = (4 + 8 + 26) * 8


def words(*values):
    return struct.pack('<' + 'Q' * len(values), *values)


def data_word(sector, beat):
    return ((0x12340000 + sector) << 32) | (0x76540000 + beat)


def configuration(header):
    """Bind addresses and tracker geometry to the actual generated constructor."""
    pattern = r'registry.add_widget\(new blockdev_t\(\s*simif,\s*BLOCKDEVBRIDGEMODULE_struct\{(.*?)\},\s*(\d+),\s*args\s*,\s*(\d+)\s*,\s*(\d+)\s*\)\);'
    found = re.findall(pattern, header, re.S)
    require(len(found) == 1, 'expected one exact Rocket blockdev constructor')
    fields, index, tags, bits = found[0]
    names = ('read_latency write_latency bdev_nsectors bdev_max_req_len '
             'bdev_req_valid bdev_req_write bdev_req_offset bdev_req_len bdev_req_tag bdev_req_ready '
             'bdev_data_valid bdev_data_data_upper bdev_data_data_lower bdev_data_tag bdev_data_ready '
             'bdev_rresp_data_upper bdev_rresp_data_lower bdev_rresp_tag bdev_rresp_valid bdev_rresp_ready '
             'bdev_wack_tag bdev_wack_valid bdev_wack_ready bdev_reqs_pending bdev_wack_stalled bdev_rresp_stalled').split()
    pairs = re.findall(r'\.(\w+)\s*=\s*(\d+)\s*,', fields)
    require([p[0] for p in pairs] == names, 'missing/extra/reordered MMIO fields')
    addresses = list(map(lambda p: int(p[1]), pairs))
    require((int(index), int(tags), int(bits)) == (0, 1, 24), 'changed exact recipe blockdev geometry')
    require(addresses == list(range(512, 616, 4)), 'fixture must follow actual recipe addresses')
    return words(0x3154504B43474457, 1, 8, 8, 1, 128, 24, 4096, 4096, 512, 16, 65536, *addresses)


def oracle(config):
    """Independent complete snapshots from the scripted transaction schedule."""
    snapshots = []
    disk = bytearray(65536)
    for cut in range(OPERATIONS + 1):
        reqs = [(1, 2, 1, 0)] if cut == 3 else [(1, 3, 1, 0)] if cut == 11 else []
        data = [(data_word(2, b), 0) for b in range(5)] if cut in (2, 3) else (
               [(data_word(3, b), 0) for b in range(64)] if cut == 11 else [])
        responses = [(data_word(2, b), 0) for b in range({7: 7, 8: 7, 9: 27}[cut], 64)] if cut in (7, 8, 9) else []
        acks = [0] if cut in (6, 7) else []
        pending = int(bool(responses or acks))
        if cut == 6:
            disk[1024:1536] = words(*(data_word(2, b) for b in range(64)))
        if cut == 12:
            disk[1536:2048] = words(*(data_word(3, b) for b in range(64)))
        position = 2048 if cut >= 12 else 1536 if cut >= 6 else 0
        tracker = (1024, 5 if cut == 4 else 21, 64) if cut in (4, 5) else (0, 0, 0)
        stored = [data_word(3 if cut >= 12 else 2, b) for b in
                  range(64 if cut >= 6 else 21 if cut == 5 else 5 if cut == 4 else 0)]
        payload = config + words(int(cut > 0), pending, position, len(reqs))
        payload += b''.join(words(*r) for r in reqs)
        payload += words(len(data)) + b''.join(words(*b) for b in data)
        payload += words(len(responses)) + b''.join(words(*b) for b in responses)
        payload += words(len(acks), *acks)
        payload += words(*tracker, *stored, *([0] * (1024 - len(stored)))) + disk
        snapshots.append(payload)
    return snapshots


def transaction_audit(trace):
    """Decode actual MMIO outputs, independently checking all data and labels."""
    responses, acks, initialized = [], [], []
    cycle, signals = None, {}
    for row in trace:
        fields = row.split()
        if fields[0] == 'OP':
            cycle = int(fields[3]); continue
        if fields[0] != 'W':
            continue
        address, value = map(int, fields[1:])
        signals[address] = value
        if cycle == 100:
            initialized.append((address, value))
        if address == 596:
            require(value == 1, 'write ack valid'); acks.append((cycle, signals[592]))
        if address == 584:
            require(value == 1, 'read response valid')
            responses.append((cycle, (signals[572] << 32) | signals[576], signals[580]))
    expected = [(142 if b < 7 else 156 if b < 27 else 163, data_word(2, b), 0) for b in range(64)]
    expected += [(184, data_word(3, b), 0) for b in range(64)]
    require(responses == expected, 'read words or release labels differ from transaction oracle')
    require(acks == [(149, 0), (177, 0)], 'write ack labels differ from oracle')
    require(initialized == [(520, 128), (524, 16), (512, 4096), (516, 4096)], 'init bindings')
    return dict(read_beats=len(responses), write_acks=len(acks), fixture_cycles=[100+7*c for c in range(14)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rocket-header', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ['VCS_HOME'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    require(os.environ['CXX'] == '/usr/bin/g++-13', 'keep GCC/G++ 13')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='native-', dir=args.out.resolve()))
    header = args.rocket_header.resolve()
    config = configuration(header.read_text()); snapshots = oracle(config)
    sources = [TESTS / 'blockdev_checkpoint.cc', CC / 'core/widget.cc', BRIDGES / 'bridges/blockdev.cc']
    native, simv = out / 'blockdev-native', out / 'blockdev-simv'
    includes = f'-I{CC} -I{BRIDGES}'
    run([os.environ['CXX'], '-std=c++17', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Werror',
         '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', f'-I{CC}', f'-I{BRIDGES}',
         *sources, '-o', native], out / 'native-build.log')
    run([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
         '-top', 'blockdev_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
         f'-Mdir={out / "csrc"}', '-CFLAGS', f'-std=c++17 -DBLOCKDEV_CHECKPOINT_DPI {includes}',
         '-o', simv, TESTS / 'blockdev_checkpoint_tb.sv', *sources], out / 'vcs-build.log')
    commands, results = [], []
    for backend in ('native-sanitized', 'vcs-dpi'):
        case = out / backend; case.mkdir()
        def invoke(mode, cut, directory=case, expected=0):
            if backend == 'native-sanitized':
                argv = [native, mode, directory, str(cut)]
            else:
                argv = [simv, '-no_save', f'+outdir={directory}', f'+restore={int(mode == "restore")}',
                        f'+cut={cut}', *(['+negative'] if mode == 'negative' else [])]
            log = directory / f'{mode}-{cut}.log'
            output = run(argv, log, expected=expected)
            commands.append(dict(cwd=str(ROOT), argv=list(map(str, argv)), log=str(log), expected_exit=expected))
            if backend == 'vcs-dpi' and expected == 0 and mode != 'negative':
                require('BLOCKDEV_READBACK edges=0' in output and 'PASS: blockdev component continuation' in output,
                        'missing zero-edge/native completion markers')
            return output
        invoke('reference', 0)
        trace = (case / 'reference.trace').read_text().splitlines()
        txns = transaction_audit(trace)
        for cut, snapshot in enumerate(snapshots):
            require((case / f'cut-{cut}.owner').read_bytes() == snapshot, f'complete independent snapshot cut={cut}')
            invoke('restore', cut)
            require((case / f'restore-{cut}.initial.owner').read_bytes() == snapshot, 'zero-edge complete owner readback')
            require((case / f'restore-{cut}.final.owner').read_bytes() == snapshots[-1], 'complete final owner readback')
            suffix = trace[trace.index(f'OP {cut} C {100+7*cut}'):] if cut < OPERATIONS else []
            require((case / f'restore-{cut}.trace').read_text().splitlines() == suffix, 'all MMIO timing/response continuation')
        output = invoke('negative', 0)
        require('PASS: blockdev atomic payload/configuration/suspension checks' in output, 'incomplete negative checks')
        # Negative fixtures must retain every successful continuation's raw
        # trace and snapshots, so the subsequent independent evidence audit
        # can review all cuts after the suite completes.
        require((case / 'reference.trace').read_text().splitlines() == trace, 'negative case overwrote reference')
        for cut, snapshot in enumerate(snapshots):
            suffix = trace[trace.index(f'OP {cut} C {100+7*cut}'):] if cut < OPERATIONS else []
            require((case / f'restore-{cut}.trace').read_text().splitlines() == suffix, 'negative case overwrote continuation')
            require((case / f'cut-{cut}.owner').read_bytes() == snapshot, 'negative case overwrote capture')
            require((case / f'restore-{cut}.initial.owner').read_bytes() == snapshot, 'negative case overwrote readback')
        # A structurally valid actual partial-write data fault must pass loading,
        # then stop at the first differing real response MMIO, without another op.
        fault = case / 'actual-tracker-fault'; fault.mkdir()
        bad = bytearray(snapshots[5]); bad[CONFIG_BYTES + 24 + 4*8 + 24] ^= 1
        (fault / 'cut-5.owner').write_bytes(bad)
        shutil.copyfile(case / 'reference.trace', fault / 'reference.trace')
        output = invoke('restore', 5, fault, expected=1)
        require('FIRST_MISMATCH fixture_cycle=142 signal=bdev_rresp_data_lower op=6' in output,
                'incorrect first actual corruption boundary')
        fault_trace = (fault / 'restore-5.trace').read_text().splitlines()
        require(fault_trace[-1] == f'W 576 {0x76540001}' and not any(s.startswith('OP 7 ') for s in fault_trace),
                'corruption continued past first divergence')
        results.append(dict(backend=backend, cuts=15, transactions=txns, actual_fault_first_cycle=142,
                            actual_fault_signal='bdev_rresp_data_lower', negative_log=str(case / 'negative-0.log')))
    inputs = [header, *sources, CC / 'core/widget_checkpoint.h', BRIDGES / 'bridges/blockdev.h',
              TESTS / 'blockdev_checkpoint_tb.sv', Path(__file__)]
    summary = dict(status='passed', scope='exact Rocket blockdev host component with scripted MMIO; no CPU restore acceptance',
                   artifact_root=str(out), complete_disk_bytes=65536, tracker_words=1024, fresh_continuations=30,
                   level1_verified=False, level2_verified=False, backends=results,
                   inputs_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (out / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (args.out.resolve() / 'latest.json').write_text(json.dumps(dict(summary=str(out / 'summary.json')),indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
