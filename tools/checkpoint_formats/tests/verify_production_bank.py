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
PRELINK_HISTORY_NAMES = ('pre-link-input.fir', 'pre-link-output.fir')
BRIDGE_HISTORY_NAMES = ('bridge-extraction-input.fir', 'bridge-extraction-promoted.fir',
                        'bridge-extraction-output.fir', 'bridge-extraction-connectivity.json')
INPUT_CIRCUIT_NAMES = ('compiler-input.fir',)
EMITTER_HISTORY_NAMES = ('compiler-emitter-request.json', 'golden-gate-emitter.json')
GATE_HISTORY_NAMES = ('clock-gate-input.fir', 'clock-gate-rewritten.fir',
                      'clock-gate-output.fir', 'clock-gate-source.v')
# Literal independent fixture oracle. These are retained build/driver outputs,
# not simulator storage or evidence of an integrated checkpoint host driver.
PASSIVE_OUTPUTS = {
    '.const.h': '// fixture driver metadata\n#define FIXTURE_CTRL_BASE 64\n',
    '.const.vh': '// fixture widths: λ\n`define FIXTURE_WIDTH 8\n',
    '.partition.const.h': '// fixture partition metadata\n#define FIXTURE_PARTITIONS 1\n',
    '.peer2peer.const.yaml': '',
    '.defines.vh': '// fixture platform defines\n`define USE_DDR_CHANNEL_A 0\n',
}
OUTPUT_NAMES = tuple('passive-output'+suffix for suffix in PASSIVE_OUTPUTS)
HISTORY_NAMES = (*PRELINK_HISTORY_NAMES, *BRIDGE_HISTORY_NAMES, *INPUT_CIRCUIT_NAMES,
                 *EMITTER_HISTORY_NAMES, *GATE_HISTORY_NAMES, *OUTPUT_NAMES)
SOURCES = ('sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SimulatorBankProbe.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SimulatorBankProbeContext.scala',
           'tools/checkpoint_formats/native_input_guard.py',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedExternalOwners.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockGateContract.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutPlan.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutWiring.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/PhysicalClockCutPlanSpec.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/stage/GoldenGateCli.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/PhysicalClockGateContractSpec.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedClockGateAdapter.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/core/SimWrapper.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/TargetClockAnalysis.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/UpdateBridgeClockInfo.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/PreLinkRenaming.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/ExtractBridges.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/passes/BridgeExtractionSpec.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/passes/PreLinkRenamingSpec.scala',
           'sims/firesim/sim/firesim-lib/src/main/scala/bridgeutils/RationalClock.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/WriteXDCFile.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/ShadowAnnotations.scala',
           'sims/firesim/sim/midas/targetutils/src/main/scala/midas/xdc/XDCAnnotation.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/stage/GoldenGateCompilerPhase.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/CheckpointGroupDedupModules.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/GoldenGateDedupGroups.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/EnableAndRunDedupOnce.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/passes/GoldenGateDedupGroupsSpec.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/ResolveSimulationInline.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/passes/ResolveSimulationInlineSpec.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/stage/GoldenGateEmitterPolicy.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/xilinx/package.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/package.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/xilinx/ClockGateRetirement.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/passes/xilinx/ClockGateRetirementSpec.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/stage/GoldenGateEmitterPolicySpec.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/stage/GoldenGateFileEmission.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/passes/SimulationMapping.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/platform/F1Shim.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/SimulatorBankProbeContextSpec.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/stage/GoldenGateHostPipelineSpec.scala',
           'tools/checkpoint_formats/tests/production_bank_tb.sv',
           'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
           'tools/checkpoint_formats/tests/verify_production_bank.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_emitter_policy(generated):
    """Specify the resolved request and actual emission independently of Scala."""
    request = generated/EMITTER_HISTORY_NAMES[0]
    expected_request = [{'class': 'firrtl.stage.RunFirrtlTransformAnnotation',
                         'transform': 'firrtl.VerilogEmitter'}]
    require(request.read_bytes() == b'[\n  {\n    "class":"firrtl.stage.RunFirrtlTransformAnnotation",\n'
            b'    "transform":"firrtl.VerilogEmitter"\n  }\n]',
            'consumed default emitter request changed')
    policy = dict(producer='midas.stage.GoldenGateCompilerPhase',
                  policy='golden-gate-system-verilog-v1', request=expected_request,
                  request_sha256=sha(request), output_language='SystemVerilog',
                  plain_emitter='firrtl.SystemVerilogEmitter',
                  observed_emitter='midas.checkpoint.SemanticCleanEmitter')
    canonical = json.dumps(policy, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    expected = dict(
        binding_version=1, scope='compiler_emitter_policy_only', deployable_capture_image=False,
        consumed_policy=policy,
        consumed_policy_sha256=hashlib.sha256(canonical.encode('utf-8')).hexdigest(),
        observed_emission=True, actual_emitter='midas.checkpoint.SemanticCleanEmitter',
        emitted_circuit='HostPipeline', output_suffix='.sv',
        emitted_verilog_sha256=sha(generated/'bank-probe.sv'))
    require(json.dumps(json.loads((generated/EMITTER_HISTORY_NAMES[1]).read_text()), sort_keys=True) ==
            json.dumps(expected, sort_keys=True),
        'resolved emitter policy or actual emission changed')
    return dict(kind='golden_gate_emitter_policy', value=policy)


def audit_gate_retirement(generated):
    """Check complete historical IR, including a globally unreachable owner."""
    modules = '''module GateTop :
    input I : Clock
    input CE : UInt<1>
    output O : Clock
    inst child of Child
    child.I <= I
    child.CE <= CE
    O <= child.O
  module Child :
    input I : Clock
    input CE : UInt<1>
    output O : Clock
    inst gate of AbstractClockGate_0
    gate.I <= I
    gate.CE <= CE
    O <= gate.O
  module Unreachable :
    inst deadGate of AbstractClockGate'''
    def definition(module, defname):
        return (f'extmodule {module} :\n  input I : Clock\n  input CE : UInt<1>\n'
                f'  output O : Clock\n  defname = {defname}')
    definitions = [dict(module=name, definition=definition(name, 'AbstractClockGate'))
                   for name in ('AbstractClockGate', 'AbstractClockGate_0')]
    physical = definition('BUFGCE', 'BUFGCE')
    prefix = 'FIRRTL version 1.2.0\ncircuit GateTop :\n'
    rewritten = modules.replace('of AbstractClockGate_0', 'of BUFGCE').replace(
        'of AbstractClockGate', 'of BUFGCE')
    for name, body, defs in (
            (GATE_HISTORY_NAMES[0], modules, definitions),
            (GATE_HISTORY_NAMES[1], rewritten, definitions),
            (GATE_HISTORY_NAMES[2], rewritten, [])):
        expected = prefix+body+'\n'+'\n'.join([d['definition'] for d in defs]+[physical])
        require(' '.join((generated/name).read_text().split()) == ' '.join(expected.split()),
                'historical clock-gate circuit changed: '+name)
    source = generated/GATE_HISTORY_NAMES[3]
    require(sha(source) == '4b0aadbcd127cc4ceb682c1b439a69fbdaf7f095791021b17b3437b2cde6af48',
            'retired clock-gate inline source changed')
    for row in definitions:
        row['definition_sha256'] = hashlib.sha256(row['definition'].encode('utf-8')).hexdigest()
    return dict(kind='xilinx_clock_gate_retirement', value=dict(
        producer='midas.passes.xilinx.HostSpecialization', circuit='GateTop',
        input_sha256=sha(generated/GATE_HISTORY_NAMES[0]),
        rewritten_sha256=sha(generated/GATE_HISTORY_NAMES[1]),
        output_sha256=sha(generated/GATE_HISTORY_NAMES[2]), definitions=definitions,
        source_target='~GateTop|AbstractClockGate', source_name='AbstractClockGate.v',
        source_text=source.read_text(), source_sha256=sha(source),
        instances=[dict(parent='Child', instance='gate', **{'from': 'AbstractClockGate_0'}, to='BUFGCE'),
                   dict(parent='Unreachable', instance='deadGate', **{'from': 'AbstractClockGate'}, to='BUFGCE')]))


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
        audit_emitter_policy(generated),
        audit_gate_retirement(generated),
        dict(kind='deleted_input', value=dict(producer='firrtl.stage.phases.AddCircuit',
             annotation_class='firrtl.stage.FirrtlFileAnnotation', file='historical-fixture.fir')),
        dict(kind='deleted_input', value=dict(producer='firrtl.options.phases.GetIncludes',
             annotation_class='firrtl.options.InputAnnotationFileAnnotation', file='historical-fixture.anno.json'))]
    output_hashes = {}
    for suffix, body in PASSIVE_OUTPUTS.items():
        payload = body.encode('utf-8')
        require((generated/('passive-output'+suffix)).read_bytes() == payload,
                'preserved output artifact changed: '+suffix)
        digest = hashlib.sha256(payload).hexdigest()
        output_hashes[suffix] = digest
        expected_rows.append(dict(kind='golden_gate_output_file', value=dict(
            file_suffix=suffix, body_sha256=digest, body_bytes=len(payload))))
    require(emission.get('preserved_output_sha256') == output_hashes,
            'preserved output emission binding changed or missing')
    # The stage consumes exactly one original input circuit, independently of
    # the mapped simulator later banked. Derive its receipt from complete,
    # independently specified input text; a coherently rehashed substitution
    # must fail even if the final bank RTL is unchanged.
    input_circuit = '''FIRRTL version 1.2.0
circuit HistoricalInput :
  module Worker :
    input clock : Clock
    output count : UInt<8>
    reg count_reg : UInt<8>, clock with :
      reset => (UInt<1>("h0"), count_reg)
    count_reg <= add(count_reg, UInt<8>("h1"))
    count <= count_reg
  module HistoricalInput :
    input clock : Clock
    output count : UInt<8>
    inst worker of Worker
    worker.clock <= clock
    count <= worker.count'''
    require(' '.join((generated/INPUT_CIRCUIT_NAMES[0]).read_text().split()) == ' '.join(input_circuit.split()),
            'consumed compiler input circuit changed')
    expected_rows.append(dict(kind='golden_gate_input_circuit', value=dict(
        producer='midas.stage.GoldenGateCompilerPhase', circuit='HistoricalInput',
        circuit_sha256=sha(generated/INPUT_CIRCUIT_NAMES[0]), modules=['Worker', 'HistoricalInput'])))
    # Independent historical pass oracle. The names and repeated instances
    # come from the actual pass invocation, never the current bank hierarchy.
    # Check both complete circuit texts before trusting the event's hashes.
    historical_input = '''FIRRTL version 1.2.0
circuit HistoricalWrapper :
  module Shared :
    skip
  extmodule External :
    defname = external_cell
  module HistoricalWrapper :
    inst left of Shared
    inst right of Shared
    inst ext of External'''
    historical_output = historical_input.replace('Shared', 'Shared_0').replace('External', 'External_0')
    for name, expected in zip(PRELINK_HISTORY_NAMES, (historical_input, historical_output)):
        require(' '.join((generated/name).read_text().split()) == ' '.join(expected.split()),
                'historical pre-link circuit changed: '+name)
    expected_rows.append(dict(kind='pre_link_renaming', value=dict(
        producer='midas.passes.PreLinkRenaming', circuit='HistoricalWrapper',
        input_sha256=sha(generated/HISTORY_NAMES[0]), output_sha256=sha(generated/HISTORY_NAMES[1]),
        module_renames=[{'from': source, 'to': dest} for source, dest in
                       (('Shared', 'Shared_0'), ('External', 'External_0'),
                        ('HistoricalWrapper', 'HistoricalWrapper'))])))
    # Independently specified full extraction fixture. The removed temporary
    # wrapper is history, not a target in the banked simulator. Audit all three
    # circuits and the complete generated clock/pipe connectivity, rather than
    # trusting a self-consistent rehash of changed historical artifacts.
    bridge_prefix = """FIRRTL version 1.2.0
  extmodule ClockSource :
    output clock : Clock
    defname = ClockSource
  extmodule DataBridge :
    input clock : Clock
    input value : UInt<8>
    defname = DataBridge"""
    input_worker = """module Worker :
    input clock : Clock
    input value : UInt<8>
    inst bridge of DataBridge
    bridge.clock <= clock
    bridge.value <= value"""
    input_top = """module ExtractionFixture :
    input value : UInt<8>
    inst clocks of ClockSource
    inst left of Worker
    inst right of Worker
    left.clock <= clocks.clock
    left.value <= value
    right.clock <= clocks.clock
    right.value <= value"""
    output_worker = """module Worker :
    input clock : Clock
    input value : UInt<8>
    input bridge : { flip clock : Clock, flip value : UInt<8>}
    bridge.clock <= clock
    bridge.value <= value"""
    output_top = """module ExtractionFixture :
    input value : UInt<8>
    input clocks : { clock : Clock}
    input right_bridge : { flip clock : Clock, flip value : UInt<8>}
    input left_bridge : { flip clock : Clock, flip value : UInt<8>}
    inst left of Worker
    left.bridge <= left_bridge
    inst right of Worker
    right.bridge <= right_bridge
    left.clock <= clocks.clock
    left.value <= value
    right.clock <= clocks.clock
    right.value <= value"""
    wrapper = """module DummyTop :
    inst realTopInst of ExtractionFixture
    inst realTopInst_left_bridge of DataBridge
    realTopInst.left_bridge <= realTopInst_left_bridge
    inst realTopInst_right_bridge of DataBridge
    realTopInst.right_bridge <= realTopInst_right_bridge
    inst realTopInst_clocks of ClockSource
    realTopInst.clocks <= realTopInst_clocks"""
    version, definitions = bridge_prefix.split('\n', 1)
    for name, circuit, modules in (
            (BRIDGE_HISTORY_NAMES[0], 'ExtractionFixture', (definitions, input_worker, input_top)),
            (BRIDGE_HISTORY_NAMES[1], 'DummyTop', (wrapper, definitions, output_worker, output_top)),
            (BRIDGE_HISTORY_NAMES[2], 'ExtractionFixture', (definitions, output_worker, output_top))):
        expected = version+'\ncircuit '+circuit+' :\n'+'\n'.join(modules)
        require(' '.join((generated/name).read_text().split()) == ' '.join(expected.split()),
                'historical bridge extraction circuit changed: '+name)
    connectivity = []
    root = '~ExtractionFixture|ExtractionFixture>'
    for port in ('left_bridge', 'right_bridge', 'clocks'):
        is_clock = port == 'clocks'
        channel = 'clock' if is_clock else 'value'
        connectivity.append(dict(
            **{'class': 'firesim.lib.bridgeutils.BridgeIOAnnotation'}, target=root+port,
            channelMapping={channel: port+'_'+channel},
            widgetClass='midas.widgets.ClockBridgeModule' if is_clock else 'fixture.DataBridgeModule'))
        row = dict(**{'class': 'midas.passes.fame.FAMEChannelConnectionAnnotation'},
                   globalName=port+'_'+channel, sinks=[root+port+'.'+channel])
        if is_clock:
            row['channelInfo'] = dict(**{'class': 'midas.passes.fame.TargetClockChannel'},
                clockInfo=[dict(name='base', multiplier=1, divisor=1)], perClockMFMR=[1])
        else:
            row['channelInfo'] = dict(**{'class': 'midas.passes.fame.PipeChannel'}, latency=0)
            row['clock'] = root+port+'.clock'
        connectivity.append(row)
    require(json.loads((generated/BRIDGE_HISTORY_NAMES[3]).read_text()) == connectivity,
            'historical bridge extraction connectivity changed')
    expected_rows.append(dict(kind='bridge_extraction', value=dict(
        producer='midas.passes.BridgeExtraction', circuit='ExtractionFixture', wrapper='DummyTop',
        input_sha256=sha(generated/BRIDGE_HISTORY_NAMES[0]),
        promoted_sha256=sha(generated/BRIDGE_HISTORY_NAMES[1]),
        output_sha256=sha(generated/BRIDGE_HISTORY_NAMES[2]),
        connectivity_sha256=sha(generated/BRIDGE_HISTORY_NAMES[3]),
        bridge_instances=['~DummyTop|DummyTop/realTopInst_'+instance+':'+module for instance, module in
                          (('clocks', 'ClockSource'), ('left_bridge', 'DataBridge'), ('right_bridge', 'DataBridge'))])))
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
    for label, root, names in [('generated', args.generated.resolve(), (*NAMES, *XDC_NAMES, *HISTORY_NAMES, 'bank-probe.sv')),
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
                   generated={n: sha(generated/n) for n in (*NAMES, *XDC_NAMES, *HISTORY_NAMES, 'bank-probe.sv')},
                   sources={n: sha(out/'sources'/n) for n in SOURCES},
                   artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                              if p.is_file() and p.suffix in ('.log', '.rpt', '.dcp', '.vcd', '.tcl')})
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
