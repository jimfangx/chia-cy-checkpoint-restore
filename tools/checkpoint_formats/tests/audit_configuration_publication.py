"""Independent full-byte and MMIO oracle for configuration-only publication."""
import argparse
import json
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.verify_widget_checkpoint_vcs import oracle

FATAL = ('expired', 'unsealed', 'consumed', 'stale', 'legacy', 'thread')


def audit(summary):
    summary = Path(summary).resolve()
    r = json.loads(summary.read_text())
    require(r['status'] == 'passed' and r['CPU_level1_verified'] is False, 'scope/status changed')
    for path, sha in r['artifact_sha256'].items():
        require(file_sha(path) == sha, 'configuration artifact hash mismatch ' + path)
    for b in r['source_inputs']:
        require(file_sha(b['snapshot']) == b['sha256'], 'source snapshot mismatch')
        require(file_sha(b['path']) == b['sha256'], 'source changed ' + b['path'])
    # Serialize every owner independently of the C++ implementation.
    values = ((1, 0, 4, 8), (2, 16, 20, 24, 28, 32, 36),
              (3, 64, 68, 72, 76, 80, 84, 88, 92, 96, 4, 40, 96, 3),
              (4, 112, 116, 20, 5, 7))
    expected = [struct.pack('<' + 'Q' * (len(v)+4), 0x3154504B43474457, 1, v[0], len(v)-1, *v[1:], 0)
                for v in values]
    traces, _ = oracle()
    traces = traces[:traces.index('OP 11')]
    mmio = sum(line.startswith(('W ', 'R ')) for line in traces)
    expected_rejections = 2*sum(map(len, expected)) + 4*10 + 2 + 2*mmio + 11*5
    seen = set(); totals = dict(fresh_restores=0, owner_comparisons=0, service_boundaries=0,
                               invalid_rejections=0, allocation_failures=0, fatal_checks=0)
    allocation_counts = []
    def state(folder, name):
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
            for n in range(12):
                state(folder, 'state-' + str(n))
            state(folder, 'final'); totals['service_boundaries'] += 11
        elif mode == 'restore':
            state(folder, 'initial'); state(folder, 'final')
            suffix = traces[traces.index('OP ' + str(cut)):] if cut < 11 else []
            require((folder / 'trace').read_text().splitlines() == suffix, 'restored service oracle mismatch')
            totals['fresh_restores'] += 1; totals['service_boundaries'] += 11-cut
        elif mode == 'negative':
            match = re.search(r'CONFIG_NEGATIVE rejections=(\d+) prepare_failures=(\d+) seal_failures=(\d+) unchanged=1 mmio=0', log)
            require(match is not None, 'negative checks missing')
            rejected, prepare, seal = map(int, match.groups())
            require(rejected == expected_rejections and prepare > 4 and seal > 4, 'negative/allocation coverage mismatch')
            allocation_counts.append((prepare, seal))
            totals['invalid_rejections'] += rejected; totals['allocation_failures'] += prepare+seal
        elif mode.startswith('fatal-'):
            require(f'CONFIG_FATAL mode={mode} unchanged=1 mmio=0' in log and
                    'CONFIG_PASS' not in log and 'CONFIGURATION_VCS_ZERO_TIME_PASS' not in log,
                    'fatal misuse acknowledged publication')
            totals['fatal_checks'] += 1
        else:
            require(False, 'unknown mode')
        if mode in ('reference', 'restore'):
            first = 0 if mode == 'reference' else cut
            count = sum(line.startswith(('W ', 'R ')) for line in (traces if mode == 'reference' else suffix))
            require(f'CONFIG_PASS first={first} services={11-first} mmio={count}' in log, 'continuation receipt missing')
        if backend == 'vcs-dpi' and not mode.startswith('fatal-'):
            require('CONFIGURATION_VCS_ZERO_TIME_PASS' in log, 'VCS time-zero receipt missing')
    wanted = {(b, 'reference', 0) for b in ('native', 'vcs-dpi')}
    wanted |= {(b, m, c) for b in ('native', 'vcs-dpi') for m in ('restore', 'negative') for c in range(12)}
    wanted |= {(b, 'fatal-'+m, c) for b in ('native', 'vcs-dpi') for m in FATAL for c in range(4)}
    require(seen == wanted, 'incomplete native/VCS process matrix')
    require(len(set(allocation_counts)) == 1, 'allocation sweep differs between processes')
    result = dict(status='passed', scope='four configuration-only host widgets; fixture MMIO',
                  CPU_level1_verified=False, **totals)
    (summary.parent / 'independent-audit.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--summary', required=True, type=Path)
    print(json.dumps(audit(p.parse_args().summary), indent=2))


if __name__ == '__main__':
    main()
