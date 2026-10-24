"""Production-compiler bank probe: native localhost synthesis or EDA VCS.

The public-input oracle checks both functional outputs and every bank word.
This fixture is not a Rocket image, a physical capture, or CPU migration.
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
import zipfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.native_input_guard import require_live_inputs_unchanged

ROOT = Path(__file__).resolve().parents[3]
NAMES = ('bank-probe-reference.fir', 'bank-probe-state.json', 'bank-probe-instrumented.fir',
         'bank-probe-binding.json', 'bank-probe-descriptors.json', 'bank-probe-context.json', 'bank-probe-emission.json')
XDC_NAMES = ('bank-probe.synthesis.xdc', 'bank-probe.implementation.xdc')
SOURCES = ('sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SimulatorBankProbe.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SimulatorBankProbeContext.scala',
           'tools/checkpoint_formats/native_input_guard.py',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedExternalOwners.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedClockGateAdapter.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/core/SimWrapper.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/TargetClockAnalysis.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/UpdateBridgeClockInfo.scala',
           'sims/firesim/sim/firesim-lib/src/main/scala/bridgeutils/RationalClock.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/WriteXDCFile.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/ShadowAnnotations.scala',
           'sims/firesim/sim/midas/targetutils/src/main/scala/midas/xdc/XDCAnnotation.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/stage/GoldenGateCompilerPhase.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/stage/GoldenGateHostPipelineSpec.scala',
           'tools/checkpoint_formats/tests/production_bank_tb.sv',
           'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
           'tools/checkpoint_formats/tests/verify_production_bank.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_inputs(generated):
    emission = json.loads((generated/'bank-probe-emission.json').read_text())
    require(emission['binding_version'] == 1 and emission['scope'] == 'generated_rtl_probe_only'
            and emission['external_runtime_required'] is True
            and emission['deployable_capture_image'] is False, 'unsupported bank emission scope')
    require(emission['emitted_verilog_sha256'] == sha(generated/'bank-probe.sv'), 'unbound emitted probe')
    require(set(emission['inputs']) == {'.'+n for n in NAMES[:-1]}, 'incomplete probe input binding')
    for name in NAMES[:-1]:
        require(emission['inputs']['.'+name] == sha(generated/name), 'unbound probe input '+name)
    context = json.loads((generated/'bank-probe-context.json').read_text())
    require(context['context_version'] == 1 and context['scope'] == 'compiler_context_only'
            and context['deployable_capture_image'] is False, 'unsupported compiler context scope')
    require(context['reference_sha256'] == sha(generated/'bank-probe-reference.fir') and
            context['instrumented_sha256'] == sha(generated/'bank-probe-instrumented.fir'),
            'unbound compiler context circuits')
    # Independent literal fixture contract: rehashing a missing/changed option
    # or enum label must not turn it into accepted native/VCS build provenance.
    expected_context = dict(info_mode='use', firrtl_output_file='fixture.fir',
                            target_directory='checkpoint-fixture', config_package='fixture.config',
                            config_string='FixtureConfig', output_base_filename='fixture',
                            allow_unrecognized_input_annotations=True,
                            enum_type=dict(name='fixture.Mode', values=dict(idle=0, busy=3)),
                            channel_clock_info={
                                'fixture_request': dict(name='fixture_core', multiplier=2, divisor=4),
                                'fixture_response': dict(name='fixture_uncore', multiplier=1, divisor=1)})
    expected_rows = [dict(kind=k, value=v) for k, v in expected_context.items()] + [
        dict(kind='deleted_input', value=dict(producer='firrtl.stage.phases.AddCircuit',
             annotation_class='firrtl.stage.FirrtlFileAnnotation', file='historical-fixture.fir')),
        dict(kind='deleted_input', value=dict(producer='firrtl.options.phases.GetIncludes',
             annotation_class='firrtl.options.InputAnnotationFileAnnotation', file='historical-fixture.anno.json'))]
    require(sorted(json.dumps(r, sort_keys=True) for r in context['annotations']) ==
            sorted(json.dumps(r, sort_keys=True) for r in expected_rows),
            'compiler context changed or missing')
    require(emission.get('emitted_xdc_sha256') ==
            {'.synthesis.xdc': sha(generated/XDC_NAMES[0]),
             '.implementation.xdc': sha(generated/XDC_NAMES[1])}, 'unbound emitted physical constraints')
    # Independent fixture contract. Hash-consistent dropped or retargeted
    # constraints must not pass merely by rewriting the emission receipt.
    expected = ('set_property DONT_TOUCH true [get_cells consumer]',
                'set_false_path -from [get_ports reset]')
    for name, line in zip(XDC_NAMES, expected):
        lines = [s for s in (generated/name).read_text().splitlines() if s and not s.startswith('#')]
        require(lines == [line], 'physical-constraint target or command changed: '+name)
    manifest = json.loads((generated/'bank-probe-state.json').read_text())
    binding = json.loads((generated/'bank-probe-binding.json').read_text())
    expected_policies = {'InferReadWriteAnnotation', 'DefaultReadFirstAnnotation',
                         'PassthroughSimpleSyncReadMemsAnnotation'}
    mappings = binding['annotation_translation']['mappings']
    policy_rows = [r for r in mappings
                   if r['source'] in expected_policies | {'DefaultWriteFirstAnnotation'}]
    require(len(mappings) == 8 and len(policy_rows) == 3 and {r['source'] for r in policy_rows} == expected_policies
            and all(r['targets'] == [r['source']] for r in policy_rows),
            'memory lowering policy changed or missing')
    # Independently derive the target-box destination from the actual emitted
    # hierarchy. A coherent rehash must not bless a stale, flattened or swapped
    # marker even when all storage descriptors still match.
    child = re.findall(r'^\s*inst consumer of (\w+)\s*$',
                       (generated/'bank-probe-instrumented.fir').read_text(), re.MULTILINE)
    require(len(child) == 1 and child[0].startswith('CheckpointStorage_'),
            'missing specialized target-box instance')
    target_rows = [r for r in mappings if r['source'].startswith('TargetBoxAnnotation(')]
    require(target_rows == [dict(source='TargetBoxAnnotation(~HostPipeline|HostPipeline/consumer:HostConsumer)',
                                 targets=['~HostPipeline|HostPipeline/consumer:'+child[0]])],
            'target-box hierarchy mapping changed or missing')
    # Historical originals deliberately need not exist in the current circuit.
    # Only the destination follows specialization; bind both fields and index.
    dedup_rows = [r for r in mappings if r['source'].startswith('DedupedResult(')]
    require(dedup_rows == [
        dict(source='DedupedResult(~Historical|OriginalConsumer,Some(~HostPipeline|HostPipeline/consumer:HostConsumer),0.25)',
             targets=['DedupedResult(~Historical|OriginalConsumer,Some(~HostPipeline|HostPipeline/consumer:'+child[0]+'),0.25)']),
        dict(source='DedupedResult(~Historical|Deleted,None,-1.0)',
             targets=['DedupedResult(~Historical|Deleted,None,-1.0)'])],
        'deduplication history mapping changed or missing')
    descriptors = json.loads((generated/'bank-probe-descriptors.json').read_text())
    require(manifest['reference_sha256'] == binding['reference_sha256'] ==
            sha(generated/'bank-probe-reference.fir'), 'unbound pre-bank circuit')
    require(binding['manifest_sha256'] == descriptors['manifest_sha256'] ==
            sha(generated/'bank-probe-state.json'), 'unbound complete pre-bank state')
    require(binding['instrumented_sha256'] == sha(generated/'bank-probe-instrumented.fir')
            and descriptors['bank_binding_sha256'] == sha(generated/'bank-probe-binding.json'),
            'unbound instrumented circuit/descriptors')
    require(binding['access_clock'] == 'ckpt_clock', 'wrong access clock')
    require(len(manifest['state']) == len(binding['state']) == len(descriptors['state']) == 2,
            'incomplete production fixture ownership')
    expected_paths = {'HostPipeline.host_owner', 'HostPipeline.consumer.always'}
    require({e['hierarchy'] for e in manifest['state']} == expected_paths, 'incorrect fixture ownership')
    selectors = {}
    for logical, actual, descriptor in zip(manifest['state'], binding['state'], descriptors['state']):
        require(logical['state_id'] == actual['state_id'] == descriptor['state_id'] and
                logical['hierarchy'] == actual['hierarchy'] and
                logical['width'] == actual['width'] == descriptor['width'] == 8 and
                logical['depth'] == actual['depth'] == descriptor['depth'] == 1 and
                actual['bank'] == descriptor['bank'] == 0 and actual['slot'] == descriptor['slot'],
                'altered complete word descriptor')
        selectors['HOST_SLOT' if logical['hierarchy'].endswith('host_owner') else 'COUNT_SLOT'] = actual['slot']
    require(len(set(selectors.values())) == 2, 'duplicate word selectors')
    return selectors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('vcs', 'vivado'), required=True)
    args = parser.parse_args()
    base = args.out.resolve()
    require(base.is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='production-bank-', dir=base))
    pinned = []
    for label, root, names in [('generated', args.generated.resolve(), (*NAMES, *XDC_NAMES, 'bank-probe.sv')),
                               ('sources', ROOT, SOURCES)]:
        for name in names:
            target = out/label/name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root/name).read_bytes())
            pinned.append(dict(path=str(root/name), sha256=sha(target)))
    require_live_inputs_unchanged(pinned)
    generated = out/'generated'
    selectors = audit_inputs(generated)
    commands = []

    def run(argv, cwd, name, expected=0):
        row = dict(argv=[str(a) for a in argv], cwd=str(cwd), log=str(out/name))
        commands.append(row)
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        with (out/name).open('w') as stream:
            result = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        require(result.returncode == expected, 'native failure; inspect '+str(out/name))
        return (out/name).read_text()

    if args.mode == 'vcs':
        require(Path(toolchain.VCS).is_file() and os.environ.get('VCS_HOME') == toolchain.VCS_HOME,
                'EDA with vcs-env.sh sourced last required')
        work = out/'healthy'; work.mkdir()
        run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
             '-top', 'production_bank_tb', '-Mdir='+str(work/'csrc'), '-o', work/'simv',
             *['+define+'+k+'='+str(v) for k, v in selectors.items()], generated/'bank-probe.sv',
             out/'sources/tools/checkpoint_formats/tests/production_bank_tb.sv',
             out/'sources/tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc'],
            work, 'compile.log')
        text = run([work/'simv', '-no_save'], work, 'healthy.log')
        require(re.search(r'PRODUCTION_BANK_PASS checks=\d+ edges=1025 host_ticks=1105 reads=21 cuts=4', text),
                'incomplete production bank continuation')
        cuts = re.findall(r'PRODUCTION_BANK_CUT target_cycle=(\d+) count=(\d+) injected=(\d+) complete_words=2', text)
        require([int(c[0]) for c in cuts] == [2, 39, 132, 900], 'wrong complete cut labels')
        negative = out/'corrupt'; negative.mkdir()
        text = run([work/'simv', '-no_save', '+corrupt'], negative, 'corrupt.log', expected=1)
        require('PRODUCTION_BANK_MISMATCH target_cycle=2 reads=0 freeze=1 reason=complete bank word' in text
                and 'PRODUCTION_BANK_PASS' not in text, 'semantic corruption did not stop at first unacked word')
    else:
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),
                'native manager Vivado required')
        script = out/'synth.tcl'
        script.write_text('''set_param general.maxThreads 4
create_project -in_memory -part xcvu47p-fsvh2892-2-e
read_verilog -sv generated/bank-probe.sv
read_xdc generated/bank-probe.synthesis.xdc
read_xdc generated/bank-probe.implementation.xdc
synth_design -top HostPipeline -part xcvu47p-fsvh2892-2-e -mode out_of_context
# Apply the exact compiler-emitted constraints to the actual synthesized
# hierarchy, then independently check that they hit the intended cell/ports.
set owner [get_cells -quiet consumer]
if {[llength $owner] != 1 || ![get_property DONT_TOUCH $owner]} { error "checkpoint XDC missed consumer" }
if {[llength [get_ports -quiet reset]] != 1 || [llength [get_ports -quiet clock]] != 1} { error "checkpoint XDC port mismatch" }
puts "PRODUCTION_XDC_PASS consumer=[get_property DONT_TOUCH $owner]"
create_clock -name functional -period 7.142857 [get_ports clock]
create_clock -name access -period 7.142857 [get_ports ckpt_clock]
opt_design
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force HostPipeline.dcp
puts "PRODUCTION_BANK_SYNTH_PASS"
close_project
''')
        text = run(['vivado', '-mode', 'batch', '-source', script, '-log', 'vivado.log',
                    '-journal', 'vivado.jou'], out, 'vivado-command.log')
        require(not re.search(r'(?:CRITICAL WARNING|WARNING|ERROR): \[Constraints ', text),
                'native constraint diagnostic; inspect '+str(out/'vivado-command.log'))
        require('PRODUCTION_XDC_PASS consumer=1' in text and 'PRODUCTION_BANK_SYNTH_PASS' in text and (out/'HostPipeline.dcp').stat().st_size,
                'missing synthesized probe')
        with zipfile.ZipFile(out/'HostPipeline.dcp') as dcp:
            require(dcp.testzip() is None, 'DCP integrity failure')
            retained = '\n'.join(dcp.read(name).decode() for name in dcp.namelist()
                                 if name.endswith('.xdc'))
            require('set_property DONT_TOUCH true [get_cells consumer]' in retained and
                    re.search(r'set_false_path[^\n]*-from[^\n]*reset', retained),
                    'native DCP dropped or changed emitted physical constraints')
    require_live_inputs_unchanged(pinned)
    summary = dict(status='pass', backend='eda' if args.mode == 'vcs' else 'f2',
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   original_root=str(ROOT), scope='production compiler bank probe fixture only',
                   physical_fpga_capture=False, full_rocket_image_build=False, commands=commands,
                   generated={n: sha(generated/n) for n in (*NAMES, *XDC_NAMES, 'bank-probe.sv')},
                   sources={n: sha(out/'sources'/n) for n in SOURCES},
                   artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                              if p.is_file() and p.suffix in ('.log', '.rpt', '.dcp', '.vcd', '.tcl')})
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
