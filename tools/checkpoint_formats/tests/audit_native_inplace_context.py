"""Audit retained compiler context independently of the in-place Scala producer.

This checks context and its complete source/projection bindings. It does not
certify freeze ownership, physical CE restore, or complete CPU capture.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require

CONTEXT_CLASSES = {
    'midas.stage.ConfigPackageAnnotation', 'midas.stage.ConfigStringAnnotation',
    'midas.stage.OutputBaseFilenameAnnotation', 'firrtl.stage.InfoModeAnnotation',
    'firrtl.stage.OutputFileAnnotation', 'firrtl.options.TargetDirAnnotation',
    'midas.passes.ChannelClockInfoAnnotation', 'midas.stage.GoldenGateOutputFileAnnotation',
    'firrtl.stage.AllowUnrecognizedAnnotations$', 'midas.passes.DedupGroupPolicyAnnotation',
    'midas.passes.DedupGroupResultAnnotation', 'midas.passes.DedupGroupRetirementAnnotation',
    'midas.passes.SimulationInlineResultAnnotation', 'firrtl.annotations.DeletedAnnotation',
    'chisel3.experimental.EnumAnnotations$EnumDefAnnotation', 'midas.stage.GoldenGateInputCircuitAnnotation',
    'midas.stage.GoldenGateEmitterPolicyAnnotation', 'midas.passes.BridgeExtractionResultAnnotation',
    'midas.passes.PreLinkRenamingResultAnnotation',
    'midas.passes.xilinx.XilinxClockGateRetirementAnnotation',
}


def normalized_context(a):
    """JsonProtocol may emit a nested class hint when that class occurs elsewhere
    in the enclosing annotation list. A context-only list has no such live input.
    Accept only the two exact consumed input producers and their matching hint.
    """
    if a['class'] != 'firrtl.annotations.DeletedAnnotation':
        return a
    a = copy.deepcopy(a)
    nested = {'firrtl.stage.phases.AddCircuit': 'firrtl.stage.FirrtlFileAnnotation',
              'firrtl.options.phases.GetIncludes': 'firrtl.options.InputAnnotationFileAnnotation'}
    require(a.get('xFormName') in nested, 'unsupported deleted context producer')
    hint = a['anno'].pop('class', None)
    require(hint is None or hint == nested[a['xFormName']], 'mismatched deleted context class hint')
    return a


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def context_row(a):
    a = normalized_context(a)
    kind = a['class']
    simple = {
        'midas.stage.ConfigPackageAnnotation': ('config_package', 'packageName'),
        'midas.stage.ConfigStringAnnotation': ('config_string', 'configString'),
        'midas.stage.OutputBaseFilenameAnnotation': ('output_base_filename', 'name'),
        'firrtl.stage.InfoModeAnnotation': ('info_mode', 'modeName'),
        'firrtl.stage.OutputFileAnnotation': ('firrtl_output_file', 'file'),
        'firrtl.options.TargetDirAnnotation': ('target_directory', 'directory'),
        'midas.passes.ChannelClockInfoAnnotation': ('channel_clock_info', 'infoMap'),
    }
    if kind in simple:
        label, field = simple[kind]
        require(set(a) == {'class', field}, 'changed context annotation fields: ' + kind)
        return dict(kind=label, value=a[field])
    if kind == 'midas.stage.GoldenGateOutputFileAnnotation':
        require(set(a) == {'class', 'body', 'fileSuffix'} and a['fileSuffix'] in
                {'.const.h', '.const.vh', '.partition.const.h', '.peer2peer.const.yaml', '.defines.vh'},
                'unsupported passive output')
        payload = a['body'].encode('utf-8')
        return dict(kind='golden_gate_output_file', value=dict(file_suffix=a['fileSuffix'],
                    body_sha256=hashlib.sha256(payload).hexdigest(), body_bytes=len(payload)))
    if kind == 'firrtl.stage.AllowUnrecognizedAnnotations$':
        require(set(a) == {'class'}, 'changed parser policy')
        return dict(kind='allow_unrecognized_input_annotations', value=True)
    histories = {
        'midas.passes.DedupGroupPolicyAnnotation': 'dedup_group_policy',
        'midas.passes.DedupGroupResultAnnotation': 'dedup_group_result',
        'midas.passes.DedupGroupRetirementAnnotation': 'dedup_group_retirement',
        'midas.passes.SimulationInlineResultAnnotation': 'simulation_inline',
    }
    if kind in histories:
        require(set(a) == {'class', 'body'}, 'changed consumed history fields')
        return dict(kind=histories[kind], value=json.loads(a['body']))
    if kind == 'firrtl.annotations.DeletedAnnotation':
        require(set(a) == {'class', 'xFormName', 'anno'} and set(a['anno']) == {'file'},
                'changed deleted input fields')
        nested = {'firrtl.stage.phases.AddCircuit': 'firrtl.stage.FirrtlFileAnnotation',
                  'firrtl.options.phases.GetIncludes': 'firrtl.options.InputAnnotationFileAnnotation'}
        require(a['xFormName'] in nested and a['anno']['file'], 'unsupported deleted owner or request')
        return dict(kind='deleted_input', value=dict(producer=a['xFormName'],
                    annotation_class=nested[a['xFormName']], file=a['anno']['file']))
    if kind == 'chisel3.experimental.EnumAnnotations$EnumDefAnnotation':
        require(set(a) == {'class', 'typeName', 'definition'}, 'changed enum fields')
        return dict(kind='enum_type', value=dict(name=a['typeName'], values=a['definition']))
    if kind == 'midas.stage.GoldenGateInputCircuitAnnotation':
        require(set(a) == {'class', 'circuit', 'circuitSHA256', 'modules'}, 'changed consumed circuit fields')
        return dict(kind='golden_gate_input_circuit', value=dict(producer='midas.stage.GoldenGateCompilerPhase',
                    circuit=a['circuit'], circuit_sha256=a['circuitSHA256'], modules=a['modules']))
    if kind == 'midas.stage.GoldenGateEmitterPolicyAnnotation':
        require(set(a) == {'class', 'requestJSON', 'policy'} and a['policy'] == 'golden-gate-system-verilog-v1' and
                json.loads(a['requestJSON']) == [{'class': 'firrtl.stage.RunFirrtlTransformAnnotation',
                                                'transform': 'firrtl.VerilogEmitter'}], 'changed emitter request')
        return dict(kind='golden_gate_emitter_policy', value=dict(producer='midas.stage.GoldenGateCompilerPhase',
                    policy=a['policy'], request=json.loads(a['requestJSON']), request_sha256=digest(a['requestJSON']),
                    output_language='SystemVerilog', plain_emitter='firrtl.SystemVerilogEmitter',
                    observed_emitter='midas.checkpoint.SemanticCleanEmitter'))
    if kind == 'midas.passes.BridgeExtractionResultAnnotation':
        names = {'circuit': 'circuit', 'wrapper': 'wrapper', 'inputSHA256': 'input_sha256',
                 'promotedSHA256': 'promoted_sha256', 'outputSHA256': 'output_sha256',
                 'connectivitySHA256': 'connectivity_sha256', 'bridgeInstances': 'bridge_instances'}
        require(set(a) == set(names) | {'class'}, 'changed bridge history fields')
        return dict(kind='bridge_extraction', value=dict(producer='midas.passes.BridgeExtraction',
                    **{v: a[k] for k, v in names.items()}))
    if kind == 'midas.passes.PreLinkRenamingResultAnnotation':
        require(set(a) == {'class', 'circuit', 'inputSHA256', 'outputSHA256', 'moduleRenames'} and
                all(len(pair) == 1 for pair in a['moduleRenames']), 'changed pre-link history fields')
        pairs = [dict(from_=k, to=v) for pair in a['moduleRenames'] for k, v in pair.items()]
        pairs = [{'from': p['from_'], 'to': p['to']} for p in pairs]
        return dict(kind='pre_link_renaming', value=dict(producer='midas.passes.PreLinkRenaming', circuit=a['circuit'],
                    input_sha256=a['inputSHA256'], output_sha256=a['outputSHA256'], module_renames=pairs))
    if kind == 'midas.passes.xilinx.XilinxClockGateRetirementAnnotation':
        require(set(a) == {'class', 'circuit', 'inputSHA256', 'rewrittenSHA256', 'outputSHA256',
                          'definitions', 'sourceTarget', 'sourceName', 'sourceText', 'instances'} and
                all(len(pair) == 1 for pair in a['definitions']), 'changed clock retirement fields')
        definitions = [dict(module=k, definition=v, definition_sha256=digest(v))
                       for pair in a['definitions'] for k, v in pair.items()]
        require(digest(a['sourceText']) == '4b0aadbcd127cc4ceb682c1b439a69fbdaf7f095791021b17b3437b2cde6af48',
                'changed original gate source')
        return dict(kind='xilinx_clock_gate_retirement', value=dict(producer='midas.passes.xilinx.HostSpecialization',
                    circuit=a['circuit'], input_sha256=a['inputSHA256'], rewritten_sha256=a['rewrittenSHA256'],
                    output_sha256=a['outputSHA256'], definitions=definitions, source_target=a['sourceTarget'],
                    source_name=a['sourceName'], source_text=a['sourceText'], source_sha256=digest(a['sourceText']),
                    instances=a['instances']))
    raise FormatError('unsupported context annotation in independent audit: ' + kind)


def audit(directory, source=None):
    directory = Path(directory)
    read = lambda name: json.loads((directory / name).read_text())
    binding, native = read('binding.json'), read('native-binding.json')
    original, context, owners = (read(n) for n in
        ('host-annotations.json', 'host-context-annotations.json', 'host-storage-annotations.json'))
    projected, storage = read('instrumented-annotations.json'), read('instrumented-storage-annotations.json')
    keys = lambda values: [canonical(a) for a in values]
    require(set(keys(original)) == set(keys(context)) | set(keys(owners)) and
            len(original) == len(context) + len(owners), 'context/storage partition changed')
    require(set(keys(projected)) == set(keys(context)) | set(keys(storage)) and
            len(projected) == len(context) + len(storage), 'retained context or storage changed')
    require(len(projected) == len(set(keys(projected))), 'duplicate projected annotation')
    if source is not None:
        prefix = str(source)
        require(read('host-storage-annotations.json') == json.loads(Path(prefix + '-reference.anno.json').read_text()) and
                context == json.loads(Path(prefix + '-context.anno.json').read_text()),
                'projection source differs from actual compiler annotations')
        require(sha(directory / 'host.fir') == sha(prefix + '-reference.fir'),
                'projection source differs from actual compiler circuit')
    rows = sorted((context_row(a) for a in context), key=canonical)
    snapshot = dict(context_version=1, scope='compiler_context_only', deployable_capture_image=False,
                    reference_sha256=sha(directory / 'host.fir'),
                    instrumented_sha256=sha(directory / 'instrumented.fir'), annotations=rows)
    require(read('compiler-context.json') == snapshot, 'compiler context differs from original raw annotations')
    projection = read('annotation-projection.json')
    if source is not None:
        def order(mappings):
            return [r['source'].replace(',ArraySeq(', ',List(') for r in mappings
                    if r['source'].startswith(('XDCAnnotation(', 'InternalXDCAnnotation('))]
        original_order = order(json.loads(Path(str(source) + '-binding.json').read_text())['annotation_translation']['mappings'])
        require(original_order and order(projection['host_translation']['mappings']) == original_order,
                'XDC source order differs from original compiler execution')
    for key, file in [('host', 'host-storage'), ('generated', 'generated'), ('instrumented', 'instrumented-storage')]:
        require(projection[key + '_annotations_sha256'] == sha(directory / (file + '-annotations.json')),
                'storage projection is not bound to complete annotations')
    require(native['annotation_projection_sha256'] == sha(directory / 'annotation-projection.json'),
            'native projection binding changed')
    expected = dict(context_binding_version=1, scope='inplace_compiler_projection_only', target=native['target'],
        host_sha256=sha(directory / 'host.fir'), instrumented_sha256=sha(directory / 'instrumented.fir'),
        host_annotations_sha256=sha(directory / 'host-annotations.json'),
        storage_annotations_sha256=sha(directory / 'host-storage-annotations.json'),
        context_annotations_sha256=sha(directory / 'host-context-annotations.json'),
        instrumented_annotations_sha256=sha(directory / 'instrumented-annotations.json'),
        selected_reference_annotations_sha256=sha(directory / 'reference-annotations.json'),
        native_binding_sha256=sha(directory / 'native-binding.json'), compiler_context_sha256=sha(directory / 'compiler-context.json'),
        complete_fpga_capture=False, deployable_capture_image=False, production_freeze_owners_bound=False,
        metasim_restore_supported=False)
    require(binding == expected, 'changed compiler context projection binding')
    require(native['host_sha256'] == expected['host_sha256'] and
            native['instrumented_sha256'] == expected['instrumented_sha256'] and
            native['reference_sha256'] == sha(directory / 'reference.fir'), 'native/source circuit identity changed')
    return dict(status='pass', scope='compiler context projection only', source_annotations=len(original),
                context_annotations=len(context), projected_storage_annotations=len(storage),
                context_kinds=sorted({r['kind'] for r in rows}), physical_fpga_capture=False,
                source_constraint_order_checked=source is not None)


def corruptions(directory, out, source_prefix=None):
    """Rehash the enclosing binding, so structure/value checks must reject."""
    out = Path(out)
    rejected = []
    cases = ['drop-context', 'change-context', 'duplicate-context', 'drop-storage', 'snapshot-value',
             'source-partition', 'claim-capture', 'unknown-owner']
    if source_prefix is not None:
        cases.append('constraint-order')
    for name in cases:
        dest = out / name
        shutil.copytree(directory, dest)
        load = lambda n: json.loads((dest / n).read_text())
        actual, source, snapshot = load('instrumented-annotations.json'), load('host-context-annotations.json'), load('compiler-context.json')
        if name == 'drop-context': actual.remove(source[0])
        elif name == 'change-context':
            actual[actual.index(source[0])] = dict(source[0], class_='changed')
        elif name == 'duplicate-context': actual.append(copy.deepcopy(source[0]))
        elif name == 'drop-storage': actual.remove(load('instrumented-storage-annotations.json')[0])
        elif name == 'snapshot-value': snapshot['annotations'][0]['value'] = 'changed'
        elif name == 'source-partition': source.pop()
        elif name == 'unknown-owner': actual.append({'class': 'fixture.UnknownOwner'})
        (dest / 'instrumented-annotations.json').write_bytes(canonical(actual))
        (dest / 'host-context-annotations.json').write_bytes(canonical(source))
        (dest / 'compiler-context.json').write_bytes(canonical(snapshot))
        binding = load('binding.json')
        if name == 'constraint-order':
            projection = load('annotation-projection.json')
            mappings = projection['host_translation']['mappings']
            indices = [i for i, r in enumerate(mappings) if r['source'].startswith(
                ('XDCAnnotation(', 'InternalXDCAnnotation('))]
            require(len(indices) >= 2, 'constraint-order negative needs two actual constraints')
            i, j = indices[:2]
            mappings[i], mappings[j] = mappings[j], mappings[i]
            (dest / 'annotation-projection.json').write_bytes(canonical(projection))
            native = load('native-binding.json')
            native['annotation_projection_sha256'] = sha(dest / 'annotation-projection.json')
            (dest / 'native-binding.json').write_bytes(canonical(native))
            binding['native_binding_sha256'] = sha(dest / 'native-binding.json')
        for field, file in [('instrumented_annotations_sha256', 'instrumented-annotations.json'),
                            ('context_annotations_sha256', 'host-context-annotations.json'),
                            ('compiler_context_sha256', 'compiler-context.json')]:
            binding[field] = sha(dest / file)
        if name == 'claim-capture': binding['complete_fpga_capture'] = True
        (dest / 'binding.json').write_bytes(canonical(binding))
        try:
            audit(dest, source_prefix)
        except FormatError as error:
            rejected.append(dict(name=name, rejected=str(error)))
        else:
            raise AssertionError('accepted context corruption: ' + name)
    return rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    require(args.out.resolve().is_relative_to(root / 'automations/checkpoint_loop/runs'), 'evidence must stay below runs')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='context-audit-', dir=args.out))
    generated = out / 'generated'
    shutil.copytree(args.generated, generated)
    result = audit(generated, args.source)
    result['original_generated'] = str(args.generated.resolve())
    result['rejected_corruptions'] = corruptions(generated, out / 'negative', args.source)
    result['auditor_sha256'] = sha(__file__)
    from tools.checkpoint_formats.tests.verify_native_inplace import SOURCES
    result['sources'] = {name: sha(root / name) for name in sorted(set(SOURCES) | {
        str(Path(__file__).resolve().relative_to(root)),
        'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SimulatorBankProbeContext.scala',
    })}
    result['artifacts'] = {str(p.resolve()): sha(p) for p in generated.iterdir() if p.is_file()}
    result['source_inputs'] = {} if args.source is None else {
        str(Path(str(args.source) + suffix).resolve()): sha(str(args.source) + suffix)
        for suffix in ('-reference.fir', '-reference.anno.json', '-context.anno.json', '-binding.json')}
    (out / 'summary.json').write_bytes(canonical(result))
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
