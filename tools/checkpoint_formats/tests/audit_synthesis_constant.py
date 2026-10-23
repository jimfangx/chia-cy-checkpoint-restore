"""Audit exact FPGA plusarg constants against original-model VCS and native synthesis.

This is component evidence, not a checkpoint image or physical FPGA capture.
"""
import argparse
import json
from pathlib import Path
import re
import zipfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_clocked_effects import checked_receipt
from tools.checkpoint_formats.tests.verify_clocked_effects_vcs import GENERATED, ROOT, sha

MODEL_SHA256 = '482a63c1f24a7ac920909620bd0df108e6954eabf9520de6e72334a2b5450efb'


def audit(capture, synthesis):
    run, native = checked_receipt(capture), checked_receipt(synthesis)
    require(run['backend'] == 'eda' and native['backend'] == 'f2' and
            run['root'] == native['root'] == 'SynthesisConstantStorage' and
            not native['full_rocket_image_build'] and not run['complete_cpu_acceptance'], 'incorrect component scope')
    for name in (*GENERATED, 'plusarg_reader.v', 'original-input.fir', 'original-annotations.json',
                 'prepared-annotations.json'):
        require(run['files']['generated/' + name] == native['files']['generated/' + name],
                'different native/EDA input: ' + name)
    for name in ('GeneratedStateBankAccess', 'GeneratedStateBankAnnotations', 'GeneratedSynthesisConstantAdapter',
                 'GeneratedClockGateAdapter'):
        key = 'sources/sims/firesim/sim/midas/src/main/scala/midas/checkpoint/' + name + '.scala'
        require(run['files'][key] == native['files'][key], 'different generator: ' + name)
    generated = capture.parent / 'generated'
    require(sha(generated / 'plusarg_reader.v') == MODEL_SHA256, 'unrecognized original model')
    prepared = json.loads((generated / 'prepared-annotations.json').read_text())
    constants = [row for row in prepared if row['class'].endswith('.SynthesisPlusArgConstantAnnotation')]
    require(len(constants) == 1 and constants[0] == dict(
        constants[0], target='~SynthesisConstantStorage|Plus', sourceSHA256=MODEL_SHA256,
        originalCircuitSHA256=sha(generated / 'original-input.fir'), width=9, default=341,
        format='checkpoint_constant=%d'), 'unbound synthesis preparation')
    original = json.loads((generated / 'original-annotations.json').read_text())
    inline = [row for row in original if row['class'].endswith('.BlackBoxInlineAnno')]
    require(len(inline) == 1 and inline[0]['target'] == 'SynthesisConstantStorage.Plus' and
            inline[0]['text'] == (generated / 'plusarg_reader.v').read_text(), 'original source not bound')
    binding = json.loads((generated / 'generated-bank-binding.json').read_text())
    manifest = json.loads((generated / 'generated-bank-manifest.json').read_text())
    require(binding['manifest_sha256'] == sha(generated / 'generated-bank-manifest.json') and
            binding['reference_sha256'] == sha(generated / 'generated-bank-input.fir') and
            binding['instrumented_sha256'] == sha(generated / 'generated-bank.fir'), 'bank hash mismatch')
    require(len(binding['state']) == len(manifest['state']) == 1 and
            manifest['state'][0]['hierarchy'] == 'SynthesisConstantStorage.count' and
            (manifest['state'][0]['width'], manifest['state'][0]['depth']) == (32, 1), 'hidden/extra state')
    owners = [row for row in manifest['instances'] if 'external_adapter' in row]
    require({row['hierarchy'] for row in owners} == {'SynthesisConstantStorage.a', 'SynthesisConstantStorage.b'},
            'incomplete constant instances')
    for row in owners:
        require(row['external_adapter'] == dict(adapter='fpga-synthesis-plusarg-constant-v1',
            source_sha256=MODEL_SHA256, original_circuit_sha256=sha(generated / 'original-input.fir'),
            width=9, default=341, format='checkpoint_constant=%d'), 'wrong synthesis instance identity')
    compile = run['commands'][0]
    require(compile['returncode'] == 0 and compile['argv'][0].endswith('/Y-2026.03-SP2/bin/vcs') and
            {'-full64', '-debug_access+all', '+define+SYNTHESIS'}.issubset(compile['argv']) and
            any(str(arg).endswith('/plusarg_reader.v') for arg in compile['argv']), 'missing original-model compilation')
    require(all('+checkpoint_constant=99' in row['argv'] for row in run['commands'][1:]) and
            [row['returncode'] for row in run['commands']] == [0, 0, 1], 'override/negative execution missing')
    text = (capture.parent / 'healthy/run.log').read_text()
    inputs = [(int(c), int(r), int(d)) for c, r, d in re.findall(
        r'SYNTHESIS_CONSTANT_INPUT cycle=(\d+) reset=(\d+) data=(\d+)', text)]
    require(len(inputs) == 173 and [row[0] for row in inputs] == list(range(173)), 'incomplete functional inputs')
    values, count = {0: 0}, 0
    for cycle, reset, data in inputs:
        require(reset in (0, 1) and 0 <= data < 2**17, 'invalid input')
        count = 0 if reset else (count + data + 341) % 2**32
        values[cycle + 1] = count
    expected = [(cut, 0, values[cut]) for cut in (2, 39, 132)]
    actual = [(int(c), int(i), int(v, 16)) for c, i, v in
              (line.split() for line in (capture.parent / 'healthy/capture.words').read_text().splitlines())]
    require(actual == expected, 'independent functional oracle mismatch')
    require(run['functional_edges'] == 173 and run['reads'] == 3 and run['stalls'] == 12 and
            [(c['cycle'], c['words']) for c in run['cuts']] == [(2, 1), (39, 1), (132, 1)], 'incomplete capture')
    require((capture.parent / 'healthy/debug.vcd').stat().st_size > 1000, 'missing debug waveform')
    negative = (capture.parent / 'semantic-negative/run.log').read_text()
    require('EFFECTS_FIRST_MISMATCH cycle=2 reads=0 frozen=1 state index=0' in negative and
            'CLOCKED_EFFECTS_PASS' not in negative, 'semantic corruption did not stop frozen')
    require(native['command']['returncode'] == 0 and
            'CLOCKED_EFFECTS_SYNTH_PASS root=SynthesisConstantStorage' in
            (synthesis.parent / 'command.log').read_text(), 'native synthesis failed')
    with zipfile.ZipFile(synthesis.parent / 'SynthesisConstantStorage.dcp') as dcp:
        require(dcp.testzip() is None, 'DCP CRC failure')
        metadata = dcp.read('dcp.xml').decode()
        require('<Top Name="SynthesisConstantStorage"' in metadata and
                '<Part Name="xcvu47p-fsvh2892-2-e"' in metadata and 'Vivado v2025.2' in metadata, 'DCP identity mismatch')
    return dict(status='pass', scope='component original-model and synthesis-constant agreement only',
        physical_fpga_capture=False, complete_cpu_acceptance=False,
        independently_verified_cuts=expected, checks=run['checks'], luts=native['luts'], registers=native['registers'],
        capture_receipt=str(capture), capture_sha256=sha(capture), synthesis_receipt=str(synthesis),
        synthesis_sha256=sha(synthesis), files_verified=len(run['files']) + len(native['files']))


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
