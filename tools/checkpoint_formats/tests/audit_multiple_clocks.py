"""Independent immutable evidence audit for direct, transparent and static metadata clock bank components."""
import argparse
import json
from pathlib import Path
import re
import zipfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_clocked_effects import checked_receipt
from tools.checkpoint_formats.tests.verify_clocked_effects_vcs import GENERATED, ROOT, sha
from tools.checkpoint_formats.tests.verify_multiple_clocks_vcs import SOURCES, bench


def audit(capture, synthesis):
    run, native = checked_receipt(capture), checked_receipt(synthesis)
    require(run['backend'] == 'eda' and native['backend'] == 'f2' and
            run['root'] == native['root'] == 'MultiClockStorage' and
            run['complete_cpu_acceptance'] is False and native['full_rocket_image_build'] is False,
            'incorrect scope/backend')
    for name in GENERATED:
        key = 'generated/' + name
        require(run['files'][key] == native['files'][key], 'VCS/native generated inputs differ: ' + name)
    for name in SOURCES:
        key = 'sources/' + name
        require(run['files'][key] == native['files'][key] == sha(ROOT / name), 'source identity differs: ' + name)
    generated = capture.parent / 'generated'
    binding = json.loads((generated / 'generated-bank-binding.json').read_text())
    manifest = json.loads((generated / 'generated-bank-manifest.json').read_text())
    # Python considers False == 0 and 1.0 == 1. Preserve the compiler's JInt
    # contract instead of admitting a differently typed clock origin.
    for row in binding['functional_clock_domains']:
        if 'constant_clock' in row:
            require(type(row['constant_clock']) is int and row['constant_clock'] in (0, 1) and
                    set(row) == {'clock_hierarchy', 'constant_clock'}, 'incomplete clock provenance')
    for key, name in [('reference_sha256', 'generated-bank-input.fir'), ('instrumented_sha256', 'generated-bank.fir'),
                      ('manifest_sha256', 'generated-bank-manifest.json')]:
        require(binding[key] == sha(generated / name), 'stale bank binding: ' + key)
    require((capture.parent / 'bench.sv').read_text() == bench(binding, manifest), 'executed bench differs from binding')
    require(binding['freeze_contract'] == 'externally_held_all_functional_owners_before_access_until_drain',
            'incorrect freeze contract')
    # Independent scheduling oracle for each target/domain edge, without relying
    # on the VCS runner's reported cut labels or instruction totals.
    step, edge_a, edge_b = 6, 6, 6
    cuts = []
    for count, mask in zip((0, 37, 83, 97), (0, 3, 1, 2)):
        for k in range(count):
            edge_a += bool((1 + k % 3) & 1)
            edge_b += bool((1 + k % 3) & 2)
        step += count
        cuts.append(dict(step=step, edges_a=edge_a, edges_b=edge_b, words=15, pulse_mask=mask))
    require(run['cuts'] == cuts, 'incorrect per-domain cut labels')
    expected = [(c['step'], c['edges_a'], c['edges_b'], index, address)
                for c in cuts for index, row in enumerate(binding['state']) for address in range(row['depth'])]
    words = (capture.parent / 'healthy/capture.words').read_text().splitlines()
    require(len(words) == len(expected) == 60, 'missing state words')
    for line, key in zip(words, expected):
        fields = line.split()
        require(len(fields) == 6 and tuple(map(int, fields[:5])) == key and
                re.fullmatch('[0-9a-f]{16}', fields[5]) is not None and
                int(fields[5], 16).bit_length() <= binding['state'][key[3]]['width'],
                'reordered/mislabelled/truncated/noncanonical word')
    for k in range(129):
        edge_a += bool((1 + k % 3) & 1)
        edge_b += bool((1 + k % 3) & 2)
    edge_counts = (352, edge_a, edge_b, 60, 180, 154, 154)
    healthy = (capture.parent / 'healthy/run.log').read_text()
    marker = re.search(r'MULTICLOCK_PASS checks=(\d+) steps=(\d+) edges_a=(\d+) edges_b=(\d+) reads=(\d+) stalls=(\d+) frozen_a=(\d+) frozen_b=(\d+)', healthy)
    require(marker is not None and tuple(map(int, marker.groups())) == (run['checks'], *edge_counts),
            'native run statistics disagree')
    require(tuple(run[k] for k in ('steps', 'edges_a', 'edges_b', 'reads', 'stalls', 'frozen_a', 'frozen_b')) == edge_counts,
            'receipt totals disagree')
    require('MULTICLOCK_FIRST_MISMATCH' not in healthy and (capture.parent / 'healthy/debug.vcd').stat().st_size > 1000,
            'missing healthy waveform or hidden mismatch')
    compile_command, healthy_command, bad_command = run['commands']
    require(compile_command['returncode'] == healthy_command['returncode'] == 0 and
            compile_command['argv'][0].endswith('/Y-2026.03-SP2/bin/vcs') and
            {'-full64', '-debug_access+all', '-Mupdate'}.issubset(compile_command['argv']), 'incorrect VCS invocation')
    require(str(generated / 'generated-bank.sv') in compile_command['argv'] and
            str(generated / 'reference.sv') in compile_command['argv'], 'VCS did not compile private snapshots')
    bad = (capture.parent / 'semantic-negative/run.log').read_text()
    require(bad_command['returncode'] == 1 and
            'MULTICLOCK_FIRST_MISMATCH step=6 edges_a=6 edges_b=6 reads=0 frozen=1 state index=0' in bad and
            'MULTICLOCK_PASS' not in bad and
            (capture.parent / 'semantic-negative/capture.words').stat().st_size == 0,
            'corruption did not stop frozen at first word')
    require(native['command']['returncode'] == 0 and
            'CLOCKED_EFFECTS_SYNTH_PASS root=MultiClockStorage' in (synthesis.parent / 'command.log').read_text(),
            'incomplete native synthesis')
    script = (synthesis.parent / 'synth.tcl').read_text()
    require(all(f'create_clock -period 7.142857 [get_ports {clock}]' in script
                for clock in ('clock_a', 'clock_b', 'ckpt_clock')), 'missing clock constraints')
    with zipfile.ZipFile(synthesis.parent / 'MultiClockStorage.dcp') as dcp:
        require(dcp.testzip() is None, 'native DCP CRC failure')
        metadata = dcp.read('dcp.xml').decode()
        for token in ('<Top Name="MultiClockStorage"', '<Part Name="xcvu47p-fsvh2892-2-e"',
                      '<OutOfContext Name="1"', 'Vivado v2025.2'):
            require(token in metadata, 'native DCP identity mismatch: ' + token)
    return dict(status='pass', scope='direct, transparent or static metadata clock component only', physical_fpga_capture=False,
                complete_cpu_acceptance=False, words_verified=len(words),
                clock_ports_verified=len(binding['functional_clock_domains']),
                static_clock_ports_verified=sum('constant_clock' in row for row in binding['functional_clock_domains']),
                checks=run['checks'], cuts=cuts,
                luts=native['luts'], registers=native['registers'], capture_receipt=str(capture),
                capture_sha256=sha(capture), synthesis_receipt=str(synthesis), synthesis_sha256=sha(synthesis),
                files_verified=len(run['files']) + len(native['files']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--synthesis', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    result = audit(args.capture.resolve(), args.synthesis.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
