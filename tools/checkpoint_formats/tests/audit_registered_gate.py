"""Independent complete-word audit of registered-enable gate component evidence."""
import argparse
import json
from pathlib import Path
import re
import zipfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_clocked_effects import checked_receipt
from tools.checkpoint_formats.tests.verify_registered_gate_vcs import GENERATED, SOURCES, bench
from tools.checkpoint_formats.tests.verify_clocked_effects_vcs import ROOT, sha


def expected_cuts():
    """Compute solely from the public input schedule, including 1->0 gate pulses."""
    step, gated, enabled, saved, pipe = 0, 0, 0, 0, 0
    memory = [0] * 4

    def edge(ce, reset, wen, data, address):
        nonlocal step, gated, enabled, saved, pipe
        if enabled or ce:
            saved = 0 if reset else data
            if wen:
                pipe = memory[address]
                memory[address] = data & 8191
            gated += 1
        enabled = ce
        step += 1

    def segment(count, last_ce):
        for j in range(count):
            ce = last_ce if j == count - 1 else int((j * 7 + 3) % 11 < 5)
            edge(ce, j % 17 == 0, j % 3 != 1, (step * 977 + 31) & 131071, (step * 3 + 1) % 4)

    for i in range(6):
        edge(1, 1, 1, i + 100, i % 4)
    cuts = []
    for count, last_ce, pulse in [(0, 1, 0), (37, 0, 1), (83, 1, 1), (97, 0, 0)]:
        segment(count, last_ce)
        cuts.append((dict(step=step, gated_edges=gated, enable=enabled, words=7, pulse=pulse),
                     {'saved': [saved], 'ram_r_data': [pipe], 'ram': list(memory), 'gate.enable': [enabled]}))
    segment(129, 1)
    return cuts, gated


def audit(capture, synthesis):
    run, native = checked_receipt(capture), checked_receipt(synthesis)
    require(run['backend'] == 'eda' and native['backend'] == 'f2' and run['root'] == native['root'] == 'GateStorage' and
            run['physical_fpga_capture'] is False and run['complete_cpu_acceptance'] is False and
            native['physical_fpga_capture'] is False and native['full_rocket_image_build'] is False,
            'incorrect gate scope/backend')
    for name in GENERATED:
        key = 'generated/' + name
        require(run['files'][key] == native['files'][key], 'VCS/native generated identity differs: ' + name)
    for name in SOURCES:
        key = 'sources/' + name
        require(run['files'][key] == native['files'][key] == sha(ROOT / name), 'VCS/native/current source differs: ' + name)
    generated = capture.parent / 'generated'
    binding = json.loads((generated / 'generated-bank-binding.json').read_text())
    manifest = json.loads((generated / 'generated-bank-manifest.json').read_text())
    for key, name in [('reference_sha256', 'generated-bank-input.fir'), ('instrumented_sha256', 'generated-bank.fir'),
                      ('manifest_sha256', 'generated-bank-manifest.json')]:
        require(binding[key] == sha(generated / name), 'stale gate input binding: ' + key)
    require(binding['clock_gate_adapters'] == [dict(hierarchy='GateStorage.gate', adapter='abstract-clock-gate-v1',
            source_sha256=sha(generated / 'AbstractClockGate.v'), state='enable', update_edge='posedge I', output='I & enable')],
            'incorrect exact gate implementation binding')
    require(binding['functional_clock_domains'] == [dict(clock_hierarchy='GateStorage.clock', root_clock='clock'),
            dict(clock_hierarchy='GateStorage.gate.I', root_clock='clock'),
            dict(clock_hierarchy='GateStorage.gate.O', root_clock='clock', gate_chain=['GateStorage.gate'])],
            'incorrect clock gate chain provenance')
    require(binding['freeze_contract'] == 'externally_held_all_functional_owners_before_access_until_drain', 'incorrect freeze contract')
    require((capture.parent / 'bench.sv').read_text() == bench(binding, manifest), 'executed gate bench differs')
    cuts, gated = expected_cuts()
    require(run['cuts'] == [c for c, _ in cuts], 'incorrect gate cut labels')
    expected = [(cut['step'], cut['gated_edges'], index, address, value)
                for cut, owners in cuts for index, row in enumerate(binding['state'])
                for address, value in enumerate(owners[row['hierarchy'].removeprefix('GateStorage.')])]
    words = (capture.parent / 'healthy/capture.words').read_text().splitlines()
    require(len(words) == len(expected) == 28, 'missing gate capture words')
    for line, key in zip(words, expected):
        fields = line.split()
        require(len(fields) == 5 and tuple(map(int, fields[:4])) == key[:4] and
                re.fullmatch('[0-9a-f]{16}', fields[4]) is not None and int(fields[4], 16) == key[4],
                'gate word differs from independent public-input model')
    healthy = (capture.parent / 'healthy/run.log').read_text()
    marker = re.search(r'REGISTERED_GATE_PASS checks=(\d+) steps=(\d+) gated=(\d+) reads=(\d+) stalls=(\d+) frozen=(\d+) high_ce=(\d+)', healthy)
    totals = (352, gated, 28, 84, 74, 352)
    require(marker is not None and tuple(map(int, marker.groups())) == (run['checks'], *totals) and
            tuple(run[k] for k in ('steps', 'gated_edges', 'reads', 'stalls', 'frozen_edges', 'high_ce_changes')) == totals,
            'incorrect gate runtime totals')
    require('REGISTERED_GATE_FIRST_MISMATCH' not in healthy and (capture.parent / 'healthy/debug.vcd').stat().st_size > 1000,
            'missing healthy gate waveform')
    compile_command, good_command, bad_command = run['commands']
    require(compile_command['returncode'] == good_command['returncode'] == 0 and
            compile_command['argv'][0].endswith('/Y-2026.03-SP2/bin/vcs') and
            {'-full64', '-Mupdate', '-debug_access+all'}.issubset(compile_command['argv']) and
            all(str(generated / name) in compile_command['argv'] for name in ('generated-bank.sv', 'reference.sv', 'AbstractClockGate.v')),
            'incorrect gate VCS invocation')
    bad = (capture.parent / 'semantic-negative/run.log').read_text()
    require(bad_command['returncode'] == 1 and
            'REGISTERED_GATE_FIRST_MISMATCH step=6 gated=6 reads=0 frozen=1 state index=0' in bad and
            'REGISTERED_GATE_PASS' not in bad and (capture.parent / 'semantic-negative/capture.words').stat().st_size == 0,
            'gate corruption was acknowledged')
    require(native['command']['returncode'] == 0 and 'CLOCKED_EFFECTS_SYNTH_PASS root=GateStorage' in
            (synthesis.parent / 'command.log').read_text(), 'missing native gate synthesis')
    script = (synthesis.parent / 'synth.tcl').read_text()
    require('create_clock -period 7.142857 [get_ports clock]' in script and 'get_ports ckpt_clock' in script,
            'unconstrained gate component root/access clocks')
    require('create_generated_clock -name registered_gate -source [get_ports clock] -divide_by 1 [get_pins gate/O]' in script and
            'registered_gate' in (synthesis.parent / 'clocks.rpt').read_text(), 'unconstrained registered gate output')
    with zipfile.ZipFile(synthesis.parent / 'GateStorage.dcp') as dcp:
        require(dcp.testzip() is None, 'gate native DCP CRC failure')
        metadata = dcp.read('dcp.xml').decode()
        for token in ('<Top Name="GateStorage"', '<Part Name="xcvu47p-fsvh2892-2-e"',
                      '<OutOfContext Name="1"', 'Vivado v2025.2'):
            require(token in metadata, 'incorrect native gate DCP: ' + token)
    return dict(status='pass', scope='registered-enable gate bank component only', physical_fpga_capture=False,
                complete_cpu_acceptance=False, words_verified=28, cuts=run['cuts'], checks=run['checks'],
                luts=native['luts'], registers=native['registers'], capture_receipt=str(capture), capture_sha256=sha(capture),
                synthesis_receipt=str(synthesis), synthesis_sha256=sha(synthesis))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--synthesis', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(audit(args.capture.resolve(), args.synthesis.resolve()), indent=2) + '\n')
    print(args.out)


if __name__ == '__main__':
    main()
