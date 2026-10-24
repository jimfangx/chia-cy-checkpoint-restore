"""Independent immutable execution audit for clocked-effect/DTLB components.

This audits original test evidence, never upgrades it to physical FPGA evidence.
"""
import argparse
import json
from pathlib import Path
import re
import zipfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_clocked_effects_vcs import GENERATED, ROOT, sha


def checked_receipt(path):
    document = json.loads(path.read_text())
    require(document['status'] == 'pass' and document['physical_fpga_capture'] is False, 'invalid component scope')
    for name, digest in document['files'].items():
        require(sha(path.parent / name) == digest, 'mutated execution evidence: ' + name)
    return document


def audit_dense_words(capture, binding):
    """Reconstruct every dense-fixture word from public functional inputs only."""
    rows = binding['state']
    expected_paths = {f'DenseStorage.word_{i}' for i in range(257)} | {
        f'DenseStorage.child_{name}.saved' for name in 'abc'}
    require(len(rows) == 260 and {r['hierarchy'] for r in rows} == expected_paths,
            'dense oracle requires complete local and repeated-child membership')
    log = (capture.parent / 'healthy/run.log').read_text()
    inputs = re.findall(r'^DENSE_INPUT cycle=(\d+) reset=([01]) data=(\d+)$', log, re.M)
    require(len(inputs) == 173 and [int(r[0]) for r in inputs] == list(range(173)),
            'missing, duplicate or reordered dense public-input edges')
    mask64 = (1 << 64) - 1
    total = steps = 0
    cuts = {}
    for cycle, reset, data in inputs:
        value = int(data)
        require(value <= mask64, 'oversized dense public input')
        if reset == '1':
            total = steps = 0
        else:
            total = (total + value) & mask64
            steps += 1
        if int(cycle) + 1 in (2, 39, 132):
            cuts[int(cycle) + 1] = (total, steps)
    observed = (capture.parent / 'healthy/capture.words').read_text().splitlines()
    require(len(observed) == 780, 'incomplete dense capture')
    for line, (cycle, index) in zip(observed, ((c, i) for c in cuts for i in range(260))):
        fields = line.split()
        require(len(fields) == 3 and fields[:2] == [str(cycle), str(index)], 'dense cut/order mismatch')
        row = rows[index]
        require(row['depth'] == 1, 'unexpected dense memory owner')
        total, steps = cuts[cycle]
        if row['hierarchy'].startswith('DenseStorage.word_'):
            word = int(row['hierarchy'].removeprefix('DenseStorage.word_'))
            width = word % 64 + 1
            expected = (word + total + steps * (word + 1)) & ((1 << width) - 1)
        else:
            width = 64
            expected = (9 + total) & mask64
        require(row['width'] == width and re.fullmatch('[0-9a-f]{16}', fields[2]) is not None and
                int(fields[2], 16) == expected, f'dense public-input oracle cycle={cycle} index={index}')
    return len(observed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--synthesis', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    capture, synthesis = args.capture.resolve(), args.synthesis.resolve()
    out = args.out.resolve()
    require(out.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    run, native = checked_receipt(capture), checked_receipt(synthesis)
    require(run['backend'] == 'eda' and native['backend'] == 'f2' and
            run['root'] == native['root'] and native['full_rocket_image_build'] is False and
            run['complete_cpu_acceptance'] is False, 'incorrect backend/scope')
    root = run['root']
    require(root in ('DTLB', 'EffectsStorage', 'DenseStorage'), 'unexpected root')
    for name in GENERATED:
        require(run['files']['generated/' + name] == native['files']['generated/' + name],
                'VCS and native synthesis have different actual generated inputs: ' + name)
    for name in ('GeneratedStateBankAccess.scala', 'GeneratedStateBankAnnotations.scala', 'GeneratedClockGateAdapter.scala'):
        key = 'sources/sims/firesim/sim/midas/src/main/scala/midas/checkpoint/' + name
        require(run['files'][key] == native['files'][key], 'different hardware generator: ' + name)
    binding = json.loads((capture.parent / 'generated/generated-bank-binding.json').read_text())
    manifest = json.loads((capture.parent / 'generated/generated-bank-manifest.json').read_text())
    require(len(binding['state']) == {'DTLB': 101, 'EffectsStorage': 1, 'DenseStorage': 260}[root],
            'incomplete state membership')
    require(len(manifest['state']) == len(binding['state']), 'binding omits state')
    require([(c['cycle'], c['words']) for c in run['cuts']] == [(c, len(binding['state'])) for c in (2,39,132)],
            'incorrect target cuts')
    words = (capture.parent / 'healthy/capture.words').read_text().splitlines()
    expected = [(c['cycle'], index) for c in run['cuts'] for index in range(len(binding['state']))]
    require([(int(line.split()[0]), int(line.split()[1])) for line in words] == expected,
            'capture is incomplete, reordered or mislabelled')
    for line, (_, index) in zip(words, expected):
        require(int(line.split()[2], 16).bit_length() <= binding['state'][index]['width'], 'invalid state width')
    require((capture.parent / 'healthy/debug.vcd').stat().st_size > 1000, 'missing full debug waveform')
    compile_command = run['commands'][0]
    require(compile_command['returncode'] == 0 and compile_command['argv'][0].endswith('/Y-2026.03-SP2/bin/vcs') and
            {'-full64', '-debug_access+all', '+vcs+initreg+random'}.issubset(compile_command['argv']), 'wrong VCS toolchain')
    healthy = (capture.parent / 'healthy/run.log').read_text()
    marker = re.search(r'CLOCKED_EFFECTS_PASS root=(\w+) checks=(\d+) edges=(\d+) reads=(\d+) stalls=(\d+)', healthy)
    require(marker is not None and marker[1] == root and int(marker[2]) == run['checks'] and
            int(marker[3]) == 173 and int(marker[4]) == len(expected) and
            int(marker[5]) == len(expected)*4, 'native run statistics disagree')
    bad = (capture.parent / 'semantic-negative/run.log').read_text()
    require('EFFECTS_FIRST_MISMATCH cycle=2 reads=0 frozen=1 state index=0' in bad and
            'CLOCKED_EFFECTS_PASS' not in bad and run['commands'][2]['returncode'] == 1,
            'semantic corruption did not stop frozen before first completed read')
    require(native['command']['returncode'] == 0 and
            f'CLOCKED_EFFECTS_SYNTH_PASS root={root}' in (synthesis.parent / 'command.log').read_text(), 'synthesis incomplete')
    with zipfile.ZipFile(synthesis.parent / (root + '.dcp')) as dcp:
        require(dcp.testzip() is None, 'native DCP CRC failure')
        metadata = dcp.read('dcp.xml').decode()
        require(f'<Top Name="{root}"' in metadata and '<Part Name="xcvu47p-fsvh2892-2-e"' in metadata,
                'native DCP identity mismatch')
    result = dict(status='pass', scope='component execution only', physical_fpga_capture=False,
                  root=root, cuts=run['cuts'], words_verified=len(words), checks=run['checks'],
                  luts=native['luts'], registers=native['registers'],
                  capture_receipt=str(capture), capture_sha256=sha(capture),
                  synthesis_receipt=str(synthesis), synthesis_sha256=sha(synthesis),
                  files_verified=len(run['files']) + len(native['files']))
    if root == 'DenseStorage':
        result['public_input_oracle_words'] = audit_dense_words(capture, binding)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
