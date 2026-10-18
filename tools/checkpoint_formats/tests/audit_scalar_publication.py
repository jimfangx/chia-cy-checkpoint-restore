"""Independent full-byte and MMIO oracle for scalar-only publication."""
import argparse
import json
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha


FATAL = ('expired', 'unsealed', 'consumed', 'stale', 'legacy', 'thread')


def oracle():
    def words(*v):
        return struct.pack('<' + 'Q'*len(v), *v)
    peek = words(0x3154504B43474457, 1, 5, 3, 128, 132, 136)
    for name, addr in (('in', 144), ('out', 160)):
        peek += words(1, len(name)) + name.encode() + words(addr, 3)
    stream = words(0x3154504B43474457, 1, 7, 2, 0, 64)
    for name, addr, count in (('from', 512, 256), ('to', 1024, 260)):
        stream += words(1, len(name)) + name.encode() + words(addr, count, 4, 64)
    flags = initialized = 0
    traces, states = [], []
    def snapshot():
        return [peek + words(flags), stream + words(initialized)]
    for op in range(19):
        states.append(snapshot()); lines = [f'OP {op}']; gmp = 0
        def read(addr):
            value = (int(op not in (14, 17)) if addr == 132 else int(op != 15) if addr == 136 else
                     (4 if op == 3 else 1) if addr == 256 else (0 if op == 4 else 3) if addr == 260 else addr ^ 0x13579bdf)
            lines.append(f'R {addr} {value}'); return value
        def write(addr, value):
            lines.append(f'W {addr} {value}')
        def result(value):
            lines.append(f'RESULT {int(value)}')
        if op == 0:
            initialized = 1
        elif op in (1,3):
            count = read(256)
            if count < 4:
                data = ' '.join(str(i*3 % 256) for i in range(128))
                lines.append('DMA_W 512 128 ' + data)
                result(128)
            else:
                result(0)
        elif op in (2,4):
            count = read(260)
            if count:
                lines.append('DMA_R 1024 128'); result(128)
                data = list(range(128))
            else:
                result(0); data = [i*3 % 256 for i in range(128)]
            lines.append('BUFFER ' + ' '.join(map(str, data)))
        elif op in (5,6):
            pass
        elif op in (7,13,17):
            flags = 0
            if op == 7 or read(132):
                write(144, {7:123,13:321,17:777}[op])
            else:
                flags = 2
        elif op == 8:
            flags = 0; gmp = 0xabcdef0123456789fedcba98
            for i in range(3):
                write(144+4*i, (gmp >> (32*i)) & 0xffffffff)
        elif op in (9,14,15):
            flags = 0
            if op == 9 or read(132):
                if op != 9 and not read(136):
                    flags = 1
                result(read(160))
            else:
                flags = 2; result(0)
        elif op in (10,18):
            flags = 0
            for i in range(3):
                gmp |= read(160+4*i) << (32*i)
        elif op in (11,16):
            write(128, 17 if op == 11 else 11)
            if op == 16:
                read(132)
        elif op == 12:
            result(bool(read(132)))
        lines.append(f'GMP {gmp:x} FLAGS {flags & 1} {(flags >> 1) & 1}')
        traces.extend(lines)
    states.append(snapshot())
    return traces, states


def audit(summary):
    summary = Path(summary).resolve()
    r = json.loads(summary.read_text())
    require(r['status'] == 'passed' and r['CPU_level1_verified'] is False, 'scope/status changed')
    for path, sha in r['artifact_sha256'].items():
        require(file_sha(path) == sha, 'scalar artifact hash mismatch ' + path)
    for b in r['source_inputs']:
        require(file_sha(b['snapshot']) == b['sha256'], 'source snapshot mismatch')
        require(file_sha(b['path']) == b['sha256'], 'source changed ' + b['path'])
    traces, snapshots = oracle()
    mmio = sum(line.startswith(('W ', 'R ', 'DMA_')) for line in traces)
    expected_rejections = 2*sum(map(len, snapshots[0])) + 16 + 125 + 2 + 2*mmio + 16*5
    seen = set(); totals = dict(fresh_restores=0, owner_comparisons=0, service_boundaries=0,
                               invalid_rejections=0, allocation_failures=0, fatal_checks=0)
    allocation_counts = []
    def state(folder, name, expected):
        for i, payload in enumerate(expected):
            require((folder / (name + '.' + str(i))).read_bytes() == payload, 'complete owner readback mismatch')
            totals['owner_comparisons'] += 1
    for case in r['cases']:
        backend, mode, cut = case['backend'], case['mode'], case['cut']
        require(backend in ('native', 'vcs-dpi'), 'unknown backend')
        key = backend, mode, cut
        require(key not in seen, 'duplicate case'); seen.add(key)
        folder = Path(case['destination']); log = Path(case['log']).read_text()
        if mode == 'reference':
            require((folder / 'trace').read_text().splitlines() == traces, 'reference service oracle mismatch')
            for n in range(20):
                state(folder, 'state-' + str(n), snapshots[n])
            state(folder, 'final', snapshots[-1]); totals['service_boundaries'] += 19
        elif mode == 'restore':
            state(folder, 'initial', snapshots[cut]); state(folder, 'final', snapshots[-1])
            suffix = traces[traces.index('OP ' + str(cut)):] if cut < 19 else []
            require((folder / 'trace').read_text().splitlines() == suffix, 'restored service oracle mismatch')
            totals['fresh_restores'] += 1; totals['service_boundaries'] += 19-cut
        elif mode == 'negative':
            match = re.search(r'SCALAR_NEGATIVE rejections=(\d+) prepare_failures=(\d+) seal_failures=(\d+) valid_flags=8 unchanged=1 mmio=0', log)
            require(match is not None, 'negative checks missing')
            rejected, prepare, seal = map(int, match.groups())
            require(rejected == expected_rejections and prepare > 2 and seal > 2, 'negative/allocation coverage mismatch')
            allocation_counts.append((prepare, seal))
            totals['invalid_rejections'] += rejected; totals['allocation_failures'] += prepare+seal
        elif mode.startswith('fatal-'):
            require(f'SCALAR_FATAL mode={mode} unchanged=1 mmio=0' in log and
                    'SCALAR_PASS' not in log and 'SCALAR_VCS_ZERO_TIME_PASS' not in log,
                    'fatal misuse acknowledged publication')
            totals['fatal_checks'] += 1
        else:
            require(False, 'unknown mode')
        if mode in ('reference', 'restore'):
            first = 0 if mode == 'reference' else cut
            count = sum(line.startswith(('W ', 'R ', 'DMA_')) for line in (traces if mode == 'reference' else suffix))
            require(f'SCALAR_PASS first={first} services={19-first} mmio={count}' in log, 'continuation receipt missing')
        if backend == 'vcs-dpi' and not mode.startswith('fatal-'):
            require('SCALAR_VCS_ZERO_TIME_PASS' in log, 'VCS time-zero receipt missing')
    wanted = {(b, 'reference', 0) for b in ('native', 'vcs-dpi')}
    wanted |= {(b, m, c) for b in ('native', 'vcs-dpi') for m in ('restore', 'negative') for c in range(20)}
    wanted |= {(b, 'fatal-'+m, c) for b in ('native', 'vcs-dpi') for m in FATAL for c in range(2)}
    require(seen == wanted, 'incomplete native/VCS process matrix')
    require(len(set(allocation_counts)) == 1, 'allocation sweep differs between processes')
    result = dict(status='passed', scope='two mutable-scalar host owners; fixture MMIO/DMA/clock',
                  CPU_level1_verified=False, **totals)
    (summary.parent / 'independent-audit.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--summary', required=True, type=Path)
    print(json.dumps(audit(p.parse_args().summary), indent=2))


if __name__ == '__main__':
    main()
