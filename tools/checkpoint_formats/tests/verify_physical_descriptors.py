"""Independent descriptor composition audit, localhost synthesis and EDA ROM checks.

The two component reference circuits are explicit. This cannot establish shared
production freeze ownership, FPGA capture, a restore adapter or CPU acceptance.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.semantic import validate_manifest
from tools.checkpoint_formats.tests.audit_physical_clock_state_bank import audit as audit_physical
from tools.checkpoint_formats.tests.verify_generated_bank_vcs import ORACLE

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
SCALA = 'sims/firesim/sim/midas/src/main/scala/midas/'
SOURCES = (
    SCALA+'widgets/CheckpointCaptureDescriptors.scala', SCALA+'widgets/CheckpointCaptureWidget.scala',
    SCALA+'widgets/CheckpointLiveWidgetSnapshot.scala',
    SCALA+'checkpoint/CheckpointTransportControlState.scala',
    SCALA+'checkpoint/PhysicalClockStateBank.scala',
    SCALA+'checkpoint/PhysicalClockCutPlan.scala', SCALA+'checkpoint/PhysicalClockCutDependencies.scala',
    SCALA+'checkpoint/GeneratedStateBankAccess.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointPhysicalDescriptorsSpec.scala',
    'tools/checkpoint_formats/tests/verify_physical_descriptors.py',
    'tools/checkpoint_formats/tests/physical_descriptor_rom_tb.sv',
    'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',
    'tools/checkpoint_formats/tests/audit_physical_clock_state_bank.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_dependencies.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_plan.py',
)
GENERATED = (
    'composition.json', 'composition-binding.json', 'functional-manifest.json', 'functional-binding.json',
    'functional-reference.fir', 'functional-instrumented.fir', 'physical_constants.h', 'physical_manifest.inc',
    'physical/reference.fir', 'physical/manifest.json', 'physical/physical-clock-plan.json',
    'physical/physical-clock-dependencies.json', 'physical/physical-clock-state-bank.json',
    'physical/physical-clock-state-bank.sv', 'rom/PhysicalDescriptorROMProbe.v',
    'widget/CheckpointCaptureWidget.v', 'widget/CheckpointCaptureTransport.sv', 'widget/CheckpointCaptureCut.sv',
    'widget/CheckpointPhysicalCaptureTransport.sv', 'widget/CheckpointPhysicalClockCut.sv',
)
FLAGS = {k: False for k in ('complete_fpga_capture', 'deployable_capture_image',
    'production_freeze_owners_bound', 'metasim_restore_supported')}
TCL = '''set_param general.maxThreads 4
read_verilog -sv generated/widget/CheckpointCaptureWidget.v generated/widget/CheckpointCaptureTransport.sv generated/widget/CheckpointCaptureCut.sv generated/widget/CheckpointPhysicalCaptureTransport.sv generated/widget/CheckpointPhysicalClockCut.sv
synth_design -top CheckpointCaptureWidget -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports clock]
if {[llength [get_cells -hier -filter {REF_NAME == BUFGCE}]] != 0} {error "duplicate physical gates"}
if {[llength [get_cells -hier -filter {ORIG_REF_NAME == CheckpointCaptureDescriptorROM}]] != 1} {error "missing immutable descriptor ROM"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force descriptor-widget.dcp
puts "PHYSICAL_DESCRIPTOR_WIDGET_SYNTH_PASS immutable_rom=1 external_network=1"
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def audit(generated):
    """Reconstruct exact composition from independently checked component owners."""
    generated = Path(generated)
    read = lambda n: json.loads((generated/n).read_text())
    manifest, binding = read('functional-manifest.json'), read('functional-binding.json')
    validate_manifest(manifest)
    require(binding['reference_sha256'] == manifest['reference_sha256'] == sha(generated/'functional-reference.fir')
        and binding['instrumented_sha256'] == sha(generated/'functional-instrumented.fir')
        and binding['manifest_sha256'] == digest(manifest), 'functional reference/binding mismatch')
    logical, bound = manifest['state'], binding['state']
    require(len(logical) == len(bound) == len(ORACLE) and {r['hierarchy'] for r in logical} == set(ORACLE),
        'complete independent functional inventory required')
    require(binding['scope'] == 'all_reachable_firrtl_state_only' and binding['access_version'] == 1
        and binding['protocol'] == 'latched-banked64-v1', 'unsupported functional bank protocol')
    entries = []
    for index, (row, access) in enumerate(zip(logical, bound)):
        require(all(row[k] == access[k] for k in ('state_id', 'hierarchy', 'width', 'depth')),
            'functional binding shape/order mismatch')
        require((row['width'], row['depth']) == ORACLE[row['hierarchy']][1:], 'functional oracle reshaped')
        # Default generated selectors are deterministic in this component.
        require(access['bank'] == 0 and access['slot'] == index and access['storage_hierarchy'],
            'functional selectors changed or physical reservation aliased')
        entries.append(dict(state_id=row['state_id'], bank=0, slot=index, width=row['width'],
            depth=row['depth'], domain='functional'))
    physical = audit_physical(generated/'physical')
    ce = read('physical/physical-clock-state-bank.json')
    expected = dict(descriptor_version=1, scope='functional_and_physical_ce_descriptor_composition_only',
        functional_manifest_sha256=digest(manifest), functional_binding_sha256=digest(binding),
        physical_bank_binding_sha256=digest(ce), functional_entries=len(entries),
        physical_clock_gates=physical['physical_gates'],
        state=entries+[dict(r, domain='physical_ce') for r in ce['state']], **FLAGS)
    require(read('composition.json') == expected, 'composition identities, ordering, scope or build hashes changed')
    expected_binding = dict(descriptor_binding_version=1, manifest_sha256=digest(expected),
        functional_manifest=manifest, functional_binding=binding, physical_bank_binding=ce,
        access_clock='ungated_common_source', reset_contract='same_reset_as_sampler_transport_and_bank_endpoints',
        **FLAGS)
    require(read('composition-binding.json') == expected_binding, 'composition source/reset/coverage binding changed')
    header = (generated/'physical_constants.h').read_text()
    for key, value in (('MANIFEST_SHA256', digest(expected)), ('DESCRIPTOR_BINDING_SHA256', digest(expected_binding))):
        require(f'{key} "{value}"' in header, 'driver digest mismatch '+key)
    for key, value in (('ENTRIES', len(expected['state'])), ('PHYSICAL_CLOCK_GATES', physical['physical_gates']),
                       ('EXTERNAL_CLOCK_NETWORK', 1), ('INTERNAL_DESCRIPTOR_ROM', 1)):
        require(f'{key} {value}U' in header, 'driver mode/count mismatch '+key)
    for name in GENERATED[-4:]:
        resource = Path(name).name
        require(sha(generated/name) == sha(ROOT/'sims/firesim/sim/midas/src/main/verilog'/resource)
            and resource+' SHA256: '+sha(generated/name) in header, 'stale native transport resource')
    cpp = 'checkpoint_capture_manifest_t{{{'+', '.join('0x'+digest(expected)[i:i+2] for i in range(62, -1, -2))+ \
        '}}, {'+', '.join('{%dU, %dU, %dU, %dU}' % tuple(r[k] for k in ('bank','slot','width','depth'))
        for r in expected['state'])+'}}'
    require((generated/'physical_manifest.inc').read_text() == cpp and cpp in header, 'host descriptor table mismatch')
    require(all('StateID: '+r['state_id'] in header for r in expected['state']), 'host StateID mapping incomplete')
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado', 'vcs', 'audit'), required=True)
    for name in ('generated', 'native', 'eda', 'out'):
        parser.add_argument('--'+name, type=Path, required=name == 'out')
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), 'evidence below runs required')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=args.out.resolve()))
    sources = {n: sha(ROOT/n) for n in SOURCES}
    commands = []

    def run(argv, name, expected=0, cwd=out):
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), log=str(out/(name+'.log')))
        commands.append(row)
        with Path(row['log']).open('w') as stream:
            result = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        require(result.returncode == expected, 'inspect underlying log '+row['log'])
        return Path(row['log']).read_text()

    def validate(path, backend):
        require(path is not None and path.resolve().is_relative_to(RUNS), 'receipt below runs required')
        doc = json.loads((path/'summary.json').read_text())
        require(doc['status'] == 'pass' and doc['backend'] == backend and doc['sources'] == sources
            and doc['physical_fpga_capture'] is False, 'stale or wrong-scope receipt')
        for group in ('inputs', 'artifacts'):
            for name, value in doc[group].items():
                require(sha(path/name) == value, 'changed receipt '+name)
        audit(path/'generated')
        return doc

    summary = dict(status='pass', backend='eda' if args.mode == 'vcs' else 'f2', sources=sources,
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), original_root=str(ROOT),
        scope='immutable descriptor composition component only; separate functional/physical reference circuits',
        physical_fpga_capture=False, production_rocket_integrated=False)
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native localhost required')
        require(args.generated is not None and args.generated.resolve().is_relative_to(RUNS), 'generated inputs below runs required')
        for name in GENERATED:
            dest = out/'generated'/name; dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.generated/name, dest)
        doc = audit(out/'generated')
        for name in SOURCES:
            dest = out/'sources'/name; dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, dest)
        (out/'synth.tcl').write_text(TCL)
        summary['inputs'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
        text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl'], 'synth')
        require('PHYSICAL_DESCRIPTOR_WIDGET_SYNTH_PASS immutable_rom=1 external_network=1' in text
            and not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native descriptor synthesis failed')
        summary['artifacts'] = {n: sha(out/n) for n in ('descriptor-widget.dcp','utilization.rpt','timing.rpt','synth.log','commands.json')}
    elif args.mode == 'vcs':
        require(os.environ.get('VCS_HOME') == toolchain.VCS_HOME and Path(toolchain.VCS).is_file(), 'EDA native VCS required')
        native = validate(args.native, 'f2')
        for name in native['inputs']:
            dest = out/name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(args.native/name, dest)
        doc = audit(out/'generated')
        oracle = ['localparam integer ENTRY_COUNT=%d;' % len(doc['state']),
            'integer banks[0:ENTRY_COUNT-1],slots[0:ENTRY_COUNT-1],widths[0:ENTRY_COUNT-1],depths[0:ENTRY_COUNT-1];',
            'initial begin']
        for i, row in enumerate(doc['state']):
            oracle += ['%s[%d]=%d;' % (k, i, row[v]) for k, v in
                (('banks','bank'),('slots','slot'),('widths','width'),('depths','depth'))]
        (out/'descriptor_oracle.svh').write_text('\n'.join(oracle+['end'])+'\n')
        def compile(rom, work, name):
            work.mkdir()
            return run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
                '-top', 'physical_descriptor_rom_tb', '+incdir+'+str(out), '-Mdir='+str(work/'csrc'), '-o', work/'simv',
                rom, out/'sources/tools/checkpoint_formats/tests/physical_descriptor_rom_tb.sv',
                out/'sources/tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'], name, cwd=work)
        rom = out/'generated/rom/PhysicalDescriptorROMProbe.v'
        healthy = out/'healthy'; compile(rom, healthy, 'compile')
        text = run([healthy/'simv','-no_save'], 'healthy', cwd=healthy)
        require('DESCRIPTOR_ROM_PASS checks=126 entries=12' in text, 'incomplete ROM execution')
        # Corrupt one generated physical slot, preserving compilation and all source inputs.
        bad = out/'incorrect-rom.v'
        text = rom.read_text()
        altered, count = re.subn(r'(assign io_slot = )([^;]+);',
            r"\1(\2) ^ (io_entry == 32'd9 ? 16'h1 : 16'h0);", text)
        require(count == 1, 'cannot construct independently compiled slot fault')
        bad.write_text(altered)
        failure = out/'incorrect'; compile(bad, failure, 'incorrect-compile')
        text = run([failure/'simv','-no_save'], 'incorrect', expected=1, cwd=failure)
        require('DESCRIPTOR_ROM_FAIL index=9 checks=19' in text, 'slot corruption did not stop at first physical descriptor')
        for work in (healthy, failure):
            require(any(int(t) > 0 for t in re.findall(r'^#(\d+)$', (work/'descriptor-rom.vcd').read_text(), re.M)),
                'missing full debug execution waveform')
        summary['inputs'] = native['inputs']
        summary['checks'] = 126
        summary['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*')
            if p.is_file() and (p.suffix in ('.vcd','.log','.svh') or p.name == 'commands.json' or p == bad)}
    else:
        native, eda = validate(args.native, 'f2'), validate(args.eda, 'eda')
        require(native['inputs'] == eda['inputs'], 'native/EDA generated bytes differ')
        require(eda['checks'] == 126, 'incomplete EDA descriptor audit')
        summary['matched_inputs'] = len(native['inputs'])
        summary['matched_sources'] = len(sources)
        summary['checks'] = eda['checks']
        summary['inputs'] = {}; summary['artifacts'] = {}
        doc = audit(args.native/'generated')
        negatives = []
        for name, mutate in (
            ('missing-physical-owner', lambda d: d['state'].pop()),
            ('physical-slot-alias', lambda d: d['state'][-1].update(slot=0)),
            ('functional-bank-reservation', lambda d: d['state'][0].update(bank=255)),
            ('metasim-identity-alias', lambda d: d['state'][-1].update(state_id=d['state'][-1]['metasim_output_state_id'])),
            ('claimed-complete-ownership', lambda d: d.update(production_freeze_owners_bound=True)),
            ('stale-functional-build', lambda d: d.update(functional_binding_sha256='0'*64)),
        ):
            directory = out/name; shutil.copytree(args.native/'generated', directory)
            changed = json.loads(json.dumps(doc)); mutate(changed)
            (directory/'composition.json').write_bytes(canonical(changed))
            # Even a coherently rehashed composition/header must reject.
            binding = json.loads((directory/'composition-binding.json').read_text())
            old_binding = digest(binding); binding['manifest_sha256'] = digest(changed)
            (directory/'composition-binding.json').write_bytes(canonical(binding))
            header = (directory/'physical_constants.h').read_text().replace(digest(doc), digest(changed)).replace(old_binding, digest(binding))
            (directory/'physical_constants.h').write_text(header)
            try:
                audit(directory)
            except (ValueError, AssertionError) as error:
                negatives.append(dict(name=name, error=str(error)))
            else:
                raise ValueError('accepted corrupt composition '+name)
        summary['negative_cases'] = negatives
    summary['functional_entries'] = doc['functional_entries']
    summary['physical_clock_gates'] = doc['physical_clock_gates']
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
