"""Independent audit of retained Rocket stopped-clock bank execution and synthesis.

Every recorded word, cut label, tool invocation and immutable input is audited.
This cannot promote component simulation to physical FPGA capture evidence.
"""
import argparse
import json
from pathlib import Path
import re
import zipfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_clocked_effects import checked_receipt
from tools.checkpoint_formats.tests.verify_clocked_effects_vcs import GENERATED, ROOT, sha
from tools.checkpoint_formats.tests.verify_independent_clock_vcs import SOURCES


def audit(capture, synthesis):
    run, native = checked_receipt(capture), checked_receipt(synthesis)
    require(run['backend'] == 'eda' and native['backend'] == 'f2' and
            run['root'] == native['root'] == 'DCacheDataArray' and
            run['complete_cpu_acceptance'] is False and native['full_rocket_image_build'] is False,
            'incorrect scope/backend')
    for name in GENERATED:
        key = 'generated/' + name
        require(run['files'][key] == native['files'][key], 'VCS/native generated inputs differ: ' + name)
    for name in SOURCES:
        key = 'sources/' + name
        require(run['files'][key] == native['files'][key], 'VCS/native implementation inputs differ: ' + name)
    generated = capture.parent / 'generated'
    binding = json.loads((generated / 'generated-bank-binding.json').read_text())
    manifest = json.loads((generated / 'generated-bank-manifest.json').read_text())
    require(binding['access_clock'] == 'ckpt_clock' and binding['freeze_contract'] ==
            'externally_held_all_functional_owners_before_access_until_drain', 'incorrect clock/freeze binding')
    for key, name in [('reference_sha256', 'generated-bank-input.fir'), ('instrumented_sha256', 'generated-bank.fir'),
                      ('manifest_sha256', 'generated-bank-manifest.json')]:
        require(binding[key] == sha(generated / name), 'stale hardware binding: ' + key)
    require(len(manifest['state']) == len(binding['state']) == 128, 'incomplete state membership')
    expected_names = {f'DCacheDataArray.rockettile_dcache_data_arrays_0_{n}{suffix}'
                      for n in range(64) for suffix in ('', '_rw_rdata')}
    require({r['hierarchy'] for r in binding['state']} == expected_names, 'actual byte/pipeline owners omitted')
    for row, logical in zip(binding['state'], manifest['state']):
        require(all(row[k] == logical[k] for k in ('state_id', 'hierarchy', 'width', 'depth')),
                'inventory/binding mismatch')
        require(row['width'] == 8 and row['depth'] == (1 if row['hierarchy'].endswith('_rw_rdata') else 512),
                'owner reshaped')
    require([(c['cycle'], c['words'], c['functional_clock_stopped']) for c in run['cuts']] ==
            [(513, 32832, True), (611, 32832, False), (869, 32832, True)], 'incorrect cuts')
    words = (capture.parent / 'healthy/capture.words').read_text().splitlines()
    expected = [(cut['cycle'], index, addr) for cut in run['cuts']
                for index, row in enumerate(binding['state']) for addr in range(row['depth'])]
    require(len(words) == len(expected) == 98496, 'missing state words')
    per_cut = {}
    for line, key in zip(words, expected):
        fields = line.split()
        require(len(fields) == 4 and tuple(map(int, fields[:3])) == key and
                re.fullmatch('[0-9a-f]{16}', fields[3]) is not None and int(fields[3], 16) <= 255,
                'reordered/mislabelled/truncated/noncanonical word')
        per_cut.setdefault(key[0], []).append(line)
    healthy = (capture.parent / 'healthy/run.log').read_text()
    marker = re.search(r'INDEPENDENT_CLOCK_PASS checks=(\d+) edges=(\d+) reads=(\d+) stalls=(\d+) stopped_reads=(\d+) frozen_edges=(\d+)', healthy)
    require(marker is not None and tuple(map(int, marker.groups())) ==
            (run['checks'], 952, 98496, 196992, 65664, 131328), 'native run statistics disagree')
    require('INDEPENDENT_CLOCK_FIRST_MISMATCH' not in healthy, 'unreported healthy mismatch')
    require((capture.parent / 'healthy/debug.vcd').stat().st_size > 1000, 'missing waveform')
    compile_command, healthy_command, bad_command = run['commands']
    require(compile_command['returncode'] == healthy_command['returncode'] == 0 and
            compile_command['argv'][0].endswith('/Y-2026.03-SP2/bin/vcs') and
            {'-full64', '-debug_access+all', '-Mupdate'}.issubset(compile_command['argv']), 'incorrect VCS invocation')
    require(str(generated / 'generated-bank.sv') in compile_command['argv'] and
            str(generated / 'reference.sv') in compile_command['argv'], 'VCS did not compile private snapshots')
    bad = (capture.parent / 'semantic-negative/run.log').read_text()
    require(bad_command['returncode'] == 1 and
            'INDEPENDENT_CLOCK_FIRST_MISMATCH cycle=513 reads=0 frozen=1 state index=0' in bad and
            'INDEPENDENT_CLOCK_PASS' not in bad and
            (capture.parent / 'semantic-negative/capture.words').stat().st_size == 0,
            'corruption did not stop frozen at first word')
    require(native['command']['returncode'] == 0 and
            'CLOCKED_EFFECTS_SYNTH_PASS root=DCacheDataArray' in (synthesis.parent / 'command.log').read_text(),
            'incomplete native synthesis')
    script = (synthesis.parent / 'synth.tcl').read_text()
    require('create_clock -period 7.142857 [get_ports clock]' in script and
            'create_clock -period 7.142857 [get_ports ckpt_clock]' in script, 'missing clock constraints')
    with zipfile.ZipFile(synthesis.parent / 'DCacheDataArray.dcp') as dcp:
        require(dcp.testzip() is None, 'native DCP CRC failure')
        metadata = dcp.read('dcp.xml').decode()
        for token in ('<Top Name="DCacheDataArray"', '<Part Name="xcvu47p-fsvh2892-2-e"',
                      '<OutOfContext Name="1"', 'Vivado v2025.2'):
            require(token in metadata, 'native DCP identity mismatch: ' + token)
    import hashlib
    return dict(status='pass', scope='retained Rocket data-array component only', physical_fpga_capture=False,
                complete_cpu_acceptance=False, words_verified=len(words), checks=run['checks'],
                cuts=[dict(cycle=cut, words=len(lines), words_sha256=hashlib.sha256(
                    ('\n'.join(lines) + '\n').encode()).hexdigest()) for cut, lines in per_cut.items()],
                luts=native['luts'], registers=native['registers'],
                capture_receipt=str(capture), capture_sha256=sha(capture),
                synthesis_receipt=str(synthesis), synthesis_sha256=sha(synthesis),
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
