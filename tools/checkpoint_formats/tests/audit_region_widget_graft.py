"""Independently reconstruct the bounded native-region/widget attachment.

Only the explicitly supported reservation and ground FIRRTL contracts are
accepted. Passing establishes component structure, never an all-owner FPGA
checkpoint, descriptor identity admission, or a restore implementation.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.tests.audit_checkpoint_regions import inventory_from_firrtl
from tools.checkpoint_formats.tests.audit_native_regions import audit_routes
from tools.checkpoint_formats.tests.audit_native_inplace_annotations import protocol_json
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.audit_widget_graft import capture_ports, instances, lines

ROOT = Path(__file__).resolve().parents[3]
NO_DEDUP = 'firrtl.transforms.NoCircuitDedupAnnotation$'
EXECUTION = 'midas.checkpoint.NativeCheckpointWidgetExecutionAnnotation'
PIN = 'midas.checkpoint.NativeCheckpointWidgetPinAnnotation'
HISTORY = 'midas.passes.SimulationInlineResultAnnotation'
FLAGS = ('complete_fpga_capture', 'deployable_capture_image',
         'production_freeze_owners_bound', 'metasim_restore_supported')
PHYSICAL_PINS = dict(clock_mask='clock_mask', read_enable='physical_read_enable',
    captured_ce='captured_ce', logical_ce='ce', descriptor_entry='descriptor_entry',
    descriptor_valid='descriptor_valid', descriptor_bank='descriptor_bank',
    descriptor_slot='descriptor_slot', descriptor_width='descriptor_width',
    descriptor_depth='descriptor_depth', request_valid='bank_request_valid',
    request_ready='bank_request_ready', bank='bank', slot='slot', address='address',
    response_valid='bank_response_valid', response_ready='bank_response_ready',
    response_data='bank_response_data', response_error='bank_response_error')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def text_digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def regional_serialized(row):
    """Exact bounded Scala annotation spellings used by this fixture audit."""
    from tools.checkpoint_formats.tests.audit_widget_annotations import serialized, TYPED
    if row['class'] in TYPED:
        return serialized(row)
    simple = {'midas.stage.ConfigStringAnnotation': 'configString',
              'midas.passes.SimulationInlineResultAnnotation': 'body'}
    if row['class'] in simple:
        return row['class'].split('.')[-1] + '(' + row[simple[row['class']]] + ')'
    require(row['class'] == 'midas.stage.GoldenGateOutputFileAnnotation',
            'unsupported bounded regional context serialization')
    return 'GoldenGateOutputFileAnnotation(' + row['body'] + ',' + row['fileSuffix'] + ')'


def context_snapshot(rows, reference, instrumented):
    from tools.checkpoint_formats.tests.audit_native_inplace_context import context_row
    values = [context_row(row) for row in rows]
    singleton = [value['kind'] for value in values if value['kind'] not in {
        'enum_type', 'deleted_input', 'pre_link_renaming', 'bridge_extraction', 'golden_gate_output_file'}]
    require(len(singleton) == len(set(singleton)), 'duplicate regional compiler context option')
    suffixes = [v['value']['file_suffix'] for v in values if v['kind'] == 'golden_gate_output_file']
    require(len(suffixes) == len(set(suffixes)), 'duplicate regional passive output suffix')
    require(len(rows) == len({canonical(row) for row in rows}), 'duplicate regional context annotation')
    return dict(context_version=1, scope='compiler_context_only', deployable_capture_image=False,
                reference_sha256=reference, instrumented_sha256=instrumented,
                annotations=sorted(values, key=canonical))


def audit_source_policy(directory, inventory_doc, annotations):
    """Derive the exact source from the full original sequence, never a sidecar list."""
    from tools.checkpoint_formats.tests.audit_widget_annotations import TYPED
    from tools.checkpoint_formats.tests.audit_native_inplace_context import CONTEXT_CLASSES
    source = read(directory, 'host-annotations.json')
    if 'source_policy' not in inventory_doc:
        require(source == [{'class': NO_DEDUP}], 'unsupported regional source annotation policy')
        return None
    approved = [a for a in annotations if a['class'] in TYPED | CONTEXT_CLASSES]
    require(source == approved, 'regional source policy lost/reordered/changed original annotations')
    context = [a for a in source if a['class'] in CONTEXT_CLASSES]
    before = [a for a in read(directory, 'before-reserved-annotations.json') if a['class'] in CONTEXT_CLASSES]
    require(all(context.count(a) == 1 for a in before), 'lost or ambiguous original regional compiler context')
    expected = dict(policy_version=1, scope='exact_ordered_whole_host_typed_storage_and_inert_context',
        source_annotations_sha256=text_digest(protocol_json(source)),
        retained_annotations_sha256=text_digest(protocol_json([a for a in annotations if a not in source])),
        original_context=context_snapshot(before, sha(directory/'before-reserved.fir'), sha(directory/'before-reserved.fir')),
        source_context=context_snapshot(context, sha(directory/'native-inlined.fir'), sha(directory/'native-inlined.fir')))
    require(inventory_doc['source_policy'] == expected, 'regional source/context permission differs from original')
    return expected


def read(directory, name):
    return json.loads((directory / name).read_text())


def guarded(doc, extra=()):
    require(all(doc.get(k) is False for k in FLAGS + tuple(extra)),
            'unsupported image, owner or restore admission')


def root_of(text):
    match = re.search(r'^circuit (\w+) :', text, re.M)
    require(match, 'missing original circuit root')
    return match[1]


def body_lines(module):
    return [line for line in lines(module)[1:]
            if not re.match(r'(input|output) \w+ :', line)]


def route(module, start, stop, cast=False):
    result = []
    while True:
        require(start not in result, 'peer alias cycle')
        result.append(start)
        if start == stop:
            return result
        require(start in module['drivers'], 'undriven peer endpoint ' + start)
        value = module['drivers'][start]
        match = re.fullmatch(r'asUInt\(([\w.$]+)\)', value or '')
        if cast and match:
            value = match[1]
        require(re.fullmatch(r'[\w.$]+', value or ''), 'non-alias peer route')
        start = value


def inventory(text, root):
    """Ignore only the checked physical transport's explicitly unsupported state.

    This exception cannot hide concrete FIRRTL storage. Every register, memory,
    emitter pipeline and native gate in concrete definitions is still enumerated.
    Other opaque definitions reject rather than silently omitting contracts.
    """
    modules = parse_modules(text)
    replacements = {}
    reachable = {module for _, module in instances(modules, root)}
    for name, module in modules.items():
        if name not in reachable or module['kind'] != 'extmodule' or 'defname = BUFGCE' in module['body']:
            continue
        require(re.search(r'^  defname = CheckpointPhysicalCaptureTransport$',
                          module['body'], re.M), 'unsupported opaque original contract ' + name)
        replacements[name] = module
    for name in replacements:
        # Keep its port ABI but turn the already separately audited opaque owner
        # into an empty traversal leaf for the existing storage enumerator.
        pattern = r'^  extmodule ' + re.escape(name) + r' :[^\n]*\n(?:(?!  (?:extmodule|module) ).*\n?)*'
        match = re.search(pattern, text, re.M)
        require(match, 'missing original opaque transport')
        definition = replacements[name]
        replacement = '  module ' + name + ' :\n' + ''.join(
            '    ' + direction + ' ' + pin + ' : ' + tpe + '\n'
            for pin, (direction, tpe) in definition['ports'].items()) + '    skip\n'
        text = text[:match.start()] + replacement + text[match.end():]
    return inventory_from_firrtl(text, root)


def sv_port(name, direction, tpe, register=False):
    if tpe in ('Clock', 'Reset', 'AsyncReset'):
        signed, width = '', 1
    else:
        shape = re.fullmatch(r'(UInt|SInt)<(\d+)>', tpe)
        require(shape and int(shape[2]) > 0, 'nonground adapter port')
        signed, width = ('signed ' if shape[1] == 'SInt' else ''), int(shape[2])
    kind = 'reg' if register else 'wire'
    return f'  {direction} {kind} {signed}' + (f'[{width-1}:0] ' if width > 1 else '') + name


def packed(width, rows, field):
    return str(width * len(rows)) + "'h" + ''.join(
        format(row[field], '0' + str(width // 4) + 'x') for row in reversed(rows))


def parameters(rows):
    return '.REGIONS(' + str(len(rows)) + '), ' + ', '.join(
        '.' + key + '(' + packed(width, rows, field) + ')' for key, width, field in (
            ('BANK_BASE', 8, 'bank_base'), ('BANK_COUNT', 8, 'bank_count'),
            ('CE_BASE', 16, 'ce_base'), ('CE_COUNT', 16, 'ce_count')))


def audit_descriptors(directory, original_text, root, binding, manifest, descriptor, routing):
    original = inventory(original_text, root)
    functional = {row['state_id']: row for row in original if row['adapter'] != 'metasim-bufgce-v1'}
    physical = sorted((row for row in original if row['adapter'] == 'metasim-bufgce-v1'),
                      key=lambda row: row['hierarchy'])
    by_gate = {row['hierarchy'].removesuffix('.O') + '.CE_latch': (index, row)
               for index, row in enumerate(physical)}
    require(manifest.get('descriptor_version') == 1 and manifest.get('scope') == 'selected_native_regions_only' and
            descriptor.get('binding_version') == 1 and descriptor.get('scope') == 'same_host_native_region_composition_only' and
            descriptor.get('host_sha256') == text_digest(original_text) and descriptor.get('manifest_sha256') == digest(manifest) and
            manifest.get('routing') == routing, 'changed descriptor composition contract')
    guarded(manifest); guarded(descriptor)
    require(routing.get('routing_version') == 1 and routing.get('scope') == 'native_region_selector_routing_only' and
            routing.get('clock_contract') == 'shared_raw_clock_and_reset_all_endpoints' and
            routing.get('freeze_contract') == 'external_common_low_phase_all_owner_cut_required' and
            routing.get('complete_fpga_capture') is False and routing.get('deployable_capture_image') is False,
            'changed regional router/cut contract')
    router = ROOT / 'sims/firesim/sim/midas/src/main/verilog/CheckpointRegionStateRouter.sv'
    require(routing.get('router_sha256') == sha(router), 'changed region router implementation')
    regions = binding['regions']
    require(len(regions) == len(descriptor['regions']) and regions and
            [row['index'] for row in regions] == list(range(len(regions))), 'incomplete region ordering')
    scopes = []
    for index, (region, local) in enumerate(zip(regions, descriptor['regions'])):
        doc, pin = local['manifest'], local['binding']
        guarded(doc); guarded(pin)
        target = re.fullmatch(r'~(\w+)\|\1((?:/\w+:\w+)+)', region['target'])
        require(target and target[1] == root, 'foreign region target')
        hops = re.findall(r'/(\w+):(\w+)', target[2])
        selected = hops[-1][1]
        scope = root + ''.join('.' + name for name, _ in hops)
        require(all(not (scope == old or scope.startswith(old + '.') or old.startswith(scope + '.')) for old in scopes),
                'overlapping region executions')
        scopes.append(scope)
        require(doc.get('identity_version') == 1 and doc.get('scope') == 'selected_inplace_global_identities_only' and
                doc.get('target') == region['target'] and doc.get('selected_scope') == scope and
                doc.get('selector_namespace') == 'selected_endpoint_local_order_not_global_inventory_order' and
                doc.get('external_runtime_required') is True and
                doc.get('global_functional_entries') == len(functional) and doc.get('global_physical_gates') == len(physical) and
                pin.get('identity_binding_version') == 1 and pin.get('host_sha256') == text_digest(original_text),
                'changed local identity contract')
        selected_functional = [row for row in functional.values() if row['hierarchy'].startswith(scope + '.')]
        def local_hierarchy(row):
            return selected + row['hierarchy'][len(scope):]
        def local_id(row):
            return digest(dict(namespace='generated-simulator-state-v1', hierarchy=local_hierarchy(row), kind=row['kind']))
        selected_functional.sort(key=local_id)
        expected = []
        for ordinal, logical in enumerate(selected_functional):
            hierarchy = logical['hierarchy']
            storage = hierarchy
            if logical['adapter'] == 'firrtl-emitter-memory-pipeline-v1':
                owner, name = hierarchy.rsplit('.', 1)
                storage = owner + '.CheckpointPipeline_' + name
            expected.append(dict(ordinal=ordinal, domain='functional', selected_state_id=local_id(logical),
                state_id=logical['state_id'], selected_hierarchy=local_hierarchy(logical), hierarchy=hierarchy,
                storage_hierarchy=storage, bank=ordinal // 65536, slot=ordinal % 65536,
                width=min(64, logical['width']), depth=((logical['width'] + 63) // 64) * logical['depth'], logical_state=logical))
        selected_ce = sorted(gate for gate in by_gate if gate.startswith(scope + '.'))
        for slot, hierarchy in enumerate(selected_ce):
            global_index, output = by_gate[hierarchy]
            local_path = selected + hierarchy[len(scope):]
            expected.append(dict(ordinal=len(selected_functional) + slot, domain='physical_ce',
                selected_state_id=digest(dict(namespace='physical-bufgce-ce-latch-v1', hierarchy=local_path)),
                state_id=digest(dict(namespace='physical-bufgce-ce-latch-v1', hierarchy=hierarchy)),
                selected_hierarchy=local_path, hierarchy=hierarchy, bank=255, slot=slot,
                width=1, depth=1, ce_bit=slot, global_physical_index=global_index,
                metasim_output_state_id=output['state_id'], restore_adapter='unsupported'))
        require(doc['state'] == expected and doc.get('physical_clock_gates') == len(selected_ce),
                'local descriptor omitted, reassigned, reordered or reshaped original state')
        require(sorted(doc['uncovered_functional_state'], key=lambda row: row['state_id']) == sorted(
            (row for row in functional.values() if not row['hierarchy'].startswith(scope + '.')), key=lambda row: row['state_id']),
            'hidden local functional deficit')
        require({row['logical_latch_hierarchy'] for row in doc['uncovered_physical_gates']} == set(by_gate) - set(selected_ce),
                'hidden local physical deficit')
    audit_routes(manifest, descriptor, routing, original)
    covered = {row['state_id'] for row in manifest['state'] if row['domain'] == 'functional'}
    require(sorted(manifest['uncovered_functional_state'], key=lambda row: row['state_id']) == sorted(
        (row for state_id, row in functional.items() if state_id not in covered), key=lambda row: row['state_id']),
        'hidden global functional deficit')
    return dict(regions=len(regions), entries=len(manifest['state']), physical_clock_gates=sum(
        row['domain'] == 'physical_ce' for row in manifest['state']),
        functional_entries=len(covered), uncovered_functional_entries=len(functional) - len(covered))


def audit_region_hierarchy(directory, original, merged, root, binding):
    selected, ancestors, definitions = {}, {}, set(original)
    require(binding.get('regions_version') == 1 and binding.get('scope') == 'existing_disjoint_native_executions_only' and
            binding.get('original_execution_duplicated') is False, 'changed native region contract')
    guarded(binding)
    for region in binding['regions']:
        index = region['index']
        prefix = f'checkpoint_inplace_region{index}_'
        require(region['sideband_prefix'] == prefix, 'changed region namespace')
        target = re.fullmatch(r'~(\w+)\|\1((?:/\w+:\w+)+)', region['target'])
        require(target and target[1] == root, 'unrooted region execution')
        parent = root
        for instance, child in re.findall(r'/(\w+):(\w+)', target[2]):
            require(original[parent]['instances'].get(instance) == child, 'stale region execution')
            ancestors.setdefault(parent, []).append((index, instance, child))
            parent = child
        require(parent not in selected, 'reused region execution definition')
        selected[parent] = index
        local = parse_modules((directory / f'region-{index}.fir').read_text())
        pin = read(directory, f'region-{index}-binding.json')
        guarded(pin)
        require(pin.get('enclosing_raw_clock') == binding['raw_clock'] and pin.get('target') == region['target'] and
                pin.get('host_sha256') == binding['host_sha256'] and
                pin.get('instrumented_sha256') == sha(directory / f'region-{index}.fir'), 'changed independent native region pin')
        renames = {name: f'CheckpointRegion{index}_{name}' for name in local if name not in original}
        def rename(body):
            if not renames:
                return body
            return re.sub(r'(?m)^((?:extmodule|module) |  inst \w+ of )(' + '|'.join(map(re.escape, renames)) + r')(?=[ :\n]|$)',
                          lambda match: match[1] + renames[match[2]], body)
        for name, module in local.items():
            if name not in original or name == parent:
                emitted = renames.get(name, name)
                require(emitted in merged and merged[emitted]['body'] == rename(module['body']),
                        'changed selected native bank definition ' + emitted)
                definitions.add(emitted)
    require(set(merged) == definitions, 'extra or omitted native region definition')
    for name, before in original.items():
        if name in selected:
            continue
        after = merged[name]
        if name not in ancestors:
            require(after == before, 'changed unrelated original module ' + name)
            continue
        require(after['instances'] == before['instances'], 'duplicated or relocated ancestor execution')
        expected_ports, expected_drivers = dict(before['ports']), dict(before['drivers'])
        additions = []
        for index, _, _ in ancestors[name]:
            local = parse_modules((directory / f'region-{index}.fir').read_text())[name]
            prefix = f'checkpoint_inplace_region{index}_'
            for pin, value in local['ports'].items():
                if pin not in before['ports']:
                    require(pin.startswith(prefix) and pin not in expected_ports, 'crossed or duplicate regional port')
                    expected_ports[pin] = value
            local_body, original_body = body_lines(local), body_lines(before)
            require(local_body[:len(original_body)] == original_body, 'changed original ancestor statement')
            additions.extend(local_body[len(original_body):])
            for pin, value in local['drivers'].items():
                if pin not in before['drivers']:
                    require(pin not in expected_drivers, 'duplicate region driver')
                    expected_drivers[pin] = value
        require(after['ports'] == expected_ports and after['drivers'] == expected_drivers and
                body_lines(after) == body_lines(before) + additions, 'changed ancestor clock, logic or sideband')
    old_live, new_live = dict(instances(original, root)), dict(instances(merged, root))
    require(set(old_live) <= set(new_live), 'lost original concrete execution')
    return len(old_live)


def consume_instance(body, module, name, pins, params=''):
    pattern = r'\b' + re.escape(module) + r'(?:\s*#\(([^;]+?)\))?\s+' + re.escape(name) + r'\s*\((.*?)\);'
    matches = list(re.finditer(pattern, body, re.S))
    require(len(matches) == 1, 'missing or duplicated readout execution ' + name)
    match = matches[0]
    compact = lambda value: re.sub(r'\s+', '', value)
    require(compact(match[1] or '') == compact(params), 'changed readout selector parameters')
    pairs = re.findall(r'\.([A-Za-z_][A-Za-z0-9_$]*)\(([^()]*)\)', match[2])
    require(len(pairs) == len(dict(pairs)) and {key: value.strip() for key, value in pairs} == pins,
            'crossed, missing or duplicate readout pin ' + name)
    residue = re.sub(r'\.[A-Za-z_][A-Za-z0-9_$]*\([^()]*\)', '', match[2]).replace(',', '').strip()
    require(not residue, 'unknown readout port syntax')
    return body[:match.start()] + body[match.end():]


def consume_header(body, name, ports, register=()):
    matches = list(re.finditer(r'module \w+ \(.*?\n\);', body, re.S))
    require(len(matches) == 1, 'missing or extra readout module')
    expected = 'module ' + name + ' (\n' + ',\n'.join(
        sv_port(pin, direction, tpe, pin in register) for pin, (direction, tpe) in ports.items()) + '\n);'
    match = matches[0]
    require(match[0] == expected, 'changed readout port direction or geometry')
    return body[:match.start()] + body[match.end():]


def consume_rom(body, rows, prefix, selector):
    matches = list(re.finditer(r'  always @\* begin.*?\n  end', body, re.S))
    require(len(matches) == 1, 'missing or extra descriptor ROM logic')
    match = matches[0]
    assignments = lambda row: (f"{prefix}valid=1; {prefix}bank=8'd{row['bank']}; "
        f"{prefix}slot=16'd{row['slot']}; {prefix}width=16'd{row['width']}; {prefix}depth=32'd{row['depth']};")
    cases = '\n'.join(f"32'd{index}: begin {assignments(row)} end" for index, row in enumerate(rows))
    expected = f'''always @* begin
{prefix}valid=0; {prefix}bank=0; {prefix}slot=0;
{prefix}width=0; {prefix}depth=0;
case({selector})
{cases}
default: begin end
endcase
end'''
    compact = lambda value: re.sub(r'\s+', '', value)
    require(compact(match[0]) == compact(expected), 'changed immutable descriptor ROM order or selectors')
    return body[:match.start()] + body[match.end():]


def residue_lines(body):
    return [line.strip() for line in re.sub(r'//[^\n]*', '', body).splitlines() if line.strip()]


def audit_adapter_sv(directory, prefix, root, clock, access, captures, manifest, descriptor, routing):
    name = root + 'CheckpointRegionReadoutAdapter'
    ports = {clock: ('input', 'Clock')} | {
        pin: ('output' if direction == 'input' else 'input', tpe) for pin, (direction, tpe) in access.items()} | captures
    body = (directory / (prefix + '.native-region-graft.sv')).read_text()
    register = {pin for pin, (direction, _) in captures.items() if pin.startswith('capture_descriptor_') and direction == 'output'}
    body = consume_header(body, name, ports, register)
    body = consume_rom(body, manifest['state'], 'capture_descriptor_', 'capture_descriptor_entry')
    router = {pin: 'capture_' + pin for pin in ('request_valid', 'request_ready', 'bank', 'slot', 'address',
        'response_valid', 'response_ready', 'response_data', 'response_error')}
    router.update(clock=clock, reset='capture_reset')
    router.update({pin: pin for pin in ('region_request_valid', 'region_request_ready', 'region_bank', 'region_slot',
        'region_address', 'region_response_valid', 'region_response_ready', 'region_response_data', 'region_response_error')})
    body = consume_instance(body, 'CheckpointRegionStateRouter', 'router', router, parameters(routing['regions']))
    for index, allocation in enumerate(routing['regions']):
        local_prefix = f'checkpoint_inplace_region{index}_'
        local_ports = {clock: ('input', 'Clock')} | {pin: port for pin, port in ports.items() if pin.startswith(local_prefix)}
        pins = {pin: pin for pin in local_ports}
        pins.update({'capture_' + pin: 'capture_' + pin for pin in ('reset', 'clock_mask', 'read_enable')})
        for pin in ('captured_ce', 'logical_ce'):
            pins['capture_' + pin] = f"capture_{pin}[{allocation['ce_base']} +: {allocation['ce_count']}]"
        pins['capture_descriptor_entry'] = "32'd0"
        pins.update({'capture_descriptor_' + pin: '' for pin in ('valid', 'bank', 'slot', 'width', 'depth')})
        pins.update({'capture_' + pin: f'region_{pin}[{index}]' for pin in (
            'request_valid', 'request_ready', 'response_valid', 'response_ready', 'response_error')})
        pins.update({'capture_' + pin: 'region_' + pin for pin in ('bank', 'slot', 'address')})
        pins['capture_response_data'] = f'region_response_data[{index * 64} +: 64]'
        body = consume_instance(body, name + f'Region{index}', f'region{index}', pins)
        audit_local_adapter(directory, prefix, name + f'Region{index}', index, clock, local_ports,
                            descriptor['regions'][index]['manifest'])
    count = len(routing['regions'])
    expected = [f'wire [{count-1}:0] region_request_valid, region_request_ready, region_response_valid, region_response_ready, region_response_error;',
                f'wire [{count*64-1}:0] region_response_data;', 'wire [7:0] region_bank;',
                'wire [15:0] region_slot;', 'wire [31:0] region_address;', 'endmodule']
    require(residue_lines(body) == expected, 'unexpected shared readout logic, storage or execution')
    for suffix, source in (('.native-region-graft-router.sv', 'CheckpointRegionStateRouter.sv'),
                           ('.native-region-graft-physical-router.sv', 'CheckpointPhysicalStateRouter.sv')):
        require((directory / (prefix + suffix)).read_bytes() ==
                (ROOT / 'sims/firesim/sim/midas/src/main/verilog' / source).read_bytes(), 'changed immutable readout router')


def audit_local_adapter(directory, prefix, name, index, clock, ports, manifest):
    body = (directory / (prefix + f'.native-region-graft-{index}.sv')).read_text()
    gates = manifest['physical_clock_gates']
    # This companion uses grouped declarations for the public capture interface.
    match = re.search(r'module \w+ \(\n(.*?),\n  input wire capture_reset', body, re.S)
    require(match and match[0].split(' (')[0] == 'module ' + name and match[1] == ',\n'.join(
        sv_port(pin, direction, tpe) for pin, (direction, tpe) in ports.items()), 'changed local sideband/clock interface')
    capture_header = f'''  input wire capture_reset, capture_clock_mask, capture_read_enable,
  input wire [{gates-1}:0] capture_captured_ce,
  output wire [{gates-1}:0] capture_logical_ce,
  input wire [31:0] capture_descriptor_entry,
  output wire capture_descriptor_valid,
  output wire [7:0] capture_descriptor_bank,
  output wire [15:0] capture_descriptor_slot, capture_descriptor_width,
  output wire [31:0] capture_descriptor_depth,
  input wire capture_request_valid,
  output wire capture_request_ready,
  input wire [7:0] capture_bank,
  input wire [15:0] capture_slot,
  input wire [31:0] capture_address,
  output wire capture_response_valid,
  input wire capture_response_ready,
  output wire [63:0] capture_response_data,
  output wire capture_response_error'''
    header = re.search(r'module \w+ \(.*?\n\);', body, re.S)
    expected_header = 'module ' + name + ' (\n' + ',\n'.join(
        sv_port(pin, direction, tpe) for pin, (direction, tpe) in ports.items()) + ',\n' + capture_header + '\n);'
    require(header and header[0] == expected_header, 'changed local capture interface')
    body = body[:header.start()] + body[header.end():]
    functional = [row for row in manifest['state'] if row['domain'] == 'functional']
    body = consume_rom(body, functional, 'functional_descriptor_', 'functional_descriptor_entry')
    pins = {pin: 'capture_' + pin for pin in ('descriptor_entry', 'descriptor_valid', 'descriptor_bank', 'descriptor_slot',
        'descriptor_width', 'descriptor_depth', 'request_valid', 'request_ready', 'bank', 'slot', 'address',
        'response_valid', 'response_ready', 'response_data', 'response_error')}
    pins.update(clock=clock, reset='capture_reset')
    # The sole wildcard expands the separately enumerated declarations below.
    marker = '.__audited_wildcard()'
    require(body.count('.*);') == 1, 'unexpected local wildcard execution')
    body = body.replace('.*);', marker + ');')
    pins['__audited_wildcard'] = ''
    body = consume_instance(body, 'CheckpointPhysicalStateRouter', 'router', pins,
                            f'.ENTRIES({len(functional)}),.GATES({gates})')
    ce_text = (directory / (prefix + f'.native-region-graft-{index}-ce.sv')).read_text()
    ce_name = re.search(r'(?m)^module (\w+) \(', ce_text)
    require(ce_name, 'missing regional physical CE endpoint')
    pins = {pin: 'ce_' + pin for pin in ('descriptor_entry', 'descriptor_valid', 'descriptor_bank', 'descriptor_slot',
        'descriptor_width', 'descriptor_depth', 'request_valid', 'request_ready', 'response_valid', 'response_ready',
        'response_data', 'response_error')}
    pins.update(clock=clock, reset='capture_reset', read_enable='capture_read_enable', captured_ce='capture_captured_ce',
                bank='endpoint_bank', slot='endpoint_slot', address='endpoint_address')
    body = consume_instance(body, ce_name[1], 'ce_endpoint', pins)
    # Readout assignment directions follow the real sideband port, never a
    # guessed suffix. Reject bypasses, hidden drivers and new state in residue.
    pairs = dict(checkpoint_physical_mask='capture_clock_mask', checkpoint_physical_logical_ce='capture_logical_ce',
        ckpt_reset='capture_reset', ckpt_freeze='capture_clock_mask', ckpt_bank='endpoint_bank', ckpt_slot='endpoint_slot',
        ckpt_address='endpoint_address', ckpt_req_valid='functional_request_valid', ckpt_req_ready='functional_request_ready',
        ckpt_resp_valid='functional_response_valid', ckpt_resp_ready='functional_response_ready',
        ckpt_resp_data='functional_response_data', ckpt_resp_error='functional_response_error')
    assignments = []
    for pin, signal in pairs.items():
        pin = f'checkpoint_inplace_region{index}_' + pin
        require(pin in ports, 'missing original regional sideband')
        assignments.append(f'assign {signal} = {pin};' if ports[pin][0] == 'input' else f'assign {pin} = {signal};')
    declarations = '''wire [31:0] functional_descriptor_entry, ce_descriptor_entry;
reg functional_descriptor_valid;
reg [7:0] functional_descriptor_bank;
reg [15:0] functional_descriptor_slot, functional_descriptor_width;
reg [31:0] functional_descriptor_depth;
wire ce_descriptor_valid;
wire [7:0] ce_descriptor_bank;
wire [15:0] ce_descriptor_slot, ce_descriptor_width;
wire [31:0] ce_descriptor_depth;
wire functional_request_valid, functional_request_ready, functional_response_valid, functional_response_ready;
wire functional_response_error, ce_request_valid, ce_request_ready, ce_response_valid, ce_response_ready, ce_response_error;
wire [63:0] functional_response_data, ce_response_data;
wire [7:0] endpoint_bank;
wire [15:0] endpoint_slot;
wire [31:0] endpoint_address;'''.splitlines()
    require(residue_lines(body) == declarations + assignments + ['endmodule'], 'changed local sideband or raw-clock readout logic')


def audit_annotations(directory, original, connected, root, connection):
    from tools.checkpoint_formats.tests.audit_widget_annotations import (
        reconstruct, serialized, TYPED, CACHE)
    source = read(directory, 'native-inlined-annotations.json')
    actual = read(directory, 'connected-annotations.json')
    unique, retained, mappings, storage = reconstruct(source, original, connected, root)
    generated = read(directory, 'grafted-annotations.json')
    from tools.checkpoint_formats.tests.audit_native_inplace_context import CONTEXT_CLASSES
    context = [row for row in read(directory, 'host-annotations.json') if row['class'] in CONTEXT_CLASSES]
    require([row for row in generated if row['class'] in CONTEXT_CLASSES] == context,
            'generated regional compiler context changed')
    generated = [row for row in generated if row['class'] not in CONTEXT_CLASSES]
    require(all(row['class'] in TYPED for row in generated), 'unsupported generated regional annotation contract')
    expected = unique + retained
    expected += [row for row in generated if row['class'] != NO_DEDUP and row not in expected]
    require(actual == expected and len(actual) == len({canonical(row) for row in actual}),
            'lost, duplicated or changed host/generated annotation')
    old_executions, new_executions = {}, {}
    for paths, modules in ((old_executions, original), (new_executions, connected)):
        for path, name in instances(modules, root):
            paths.setdefault(name, set()).add(path)
    changed = {name for name in original if original[name] != connected[name] or
               old_executions.get(name, set()) != new_executions.get(name, set())}
    clocks = [row for row in source if row['class'] == 'midas.passes.HostClockSource']
    host = dict(instances(original, root))[connection['host']]
    require(len(clocks) == 1 and clocks[0] == dict(**{'class': 'midas.passes.HostClockSource'},
        target='~' + root + '|' + host + '>clock') and
        original[host]['ports'].get('clock') == connected[host]['ports'].get('clock') == ('input', 'Clock'),
        'unsupported or changed raw host clock annotation')
    # Recursive JSON traversal sees targets of unknown annotation classes too;
    # silently copying unknown targeted metadata cannot establish a contract.
    def values(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                yield from values(item)
        elif isinstance(value, list):
            for item in value:
                yield from values(item)
    for row in source:
        if row['class'] in TYPED | {PIN, EXECUTION, 'midas.passes.HostClockSource'}:
            continue
        require(not any(re.search(r'(?:\||:)' + re.escape(name) + r'(?=[/>]|$)', value)
                        for value in values(row) if value.startswith('~') for name in changed),
                'unsupported annotation targets a changed definition')
    projection = read(directory, 'annotation-projection.json')
    require(connection['annotation_projection_sha256'] == sha(directory / 'annotation-projection.json') and
            projection.get('projection_version') == 1 and projection.get('scope') == 'enclosing_host_typed_storage_annotations_only' and
            all(projection.get(key) is False for key in ('complete_fpga_capture', 'production_annotations_translated',
                'deployable_capture_image', 'production_freeze_owners_bound')), 'changed annotation projection contract')
    for key, value in (
        ('source_sha256', sha(directory / 'native-inlined.fir')),
        ('connected_sha256', sha(directory / 'connected.fir')),
        ('source_annotations_sha256', text_digest(protocol_json(source))),
        ('projected_annotations_sha256', text_digest(protocol_json(unique + retained))),
        ('retained_annotations_sha256', text_digest(protocol_json(retained)))):
        require(projection.get(key) == value, 'unbound annotation projection ' + key)
    normalize = lambda text: text.replace(',ArraySeq(', ',List(')
    normrow = lambda row: dict(source=normalize(row['source']), targets=list(map(normalize, row['targets'])))
    translation = projection['translation']
    require(translation.get('translation_version') == 2 and
            sorted(map(normrow, translation['mappings']), key=canonical) == sorted(mappings, key=canonical),
            'omitted or broadened annotation translation')
    for key, rows in (('source_sha256', storage), ('translated_sha256', unique)):
        ordered = sorted((row for row in rows if row['class'] != CACHE), key=serialized)
        require(translation.get(key) == text_digest(protocol_json(ordered)), 'changed original storage translation')
    require(sorted(map(normalize, projection['invalidated_path_caches'])) == sorted(
        serialized(row) for row in storage if row['class'] == CACHE), 'unbound invalidated annotation history')
    return dict(source=len(source), projected=len(actual), retained=len(retained), storage=len(storage))


def audit_peer(directory, original, root, execution, pins, peer):
    source = read(directory, 'native-inlined-annotations.json')
    before_annotations = read(directory, 'before-reserved-annotations.json')
    before = parse_modules((directory / 'before-reserved.fir').read_text())
    require([row for row in before_annotations if row['class'] == EXECUTION] == [execution] and
            [row for row in before_annotations if row['class'] == PIN] == pins, 'changed original reservation markers')
    histories = [row for row in source if row['class'] == HISTORY]
    require(len(histories) == 1, 'missing or duplicate native inline history')
    history = json.loads(histories[0]['body'])
    for key, value in (
        ('input_sha256', sha(directory / 'before-reserved.fir')),
        ('output_sha256', sha(directory / 'native-inlined.fir')),
        ('input_annotations_sha256', sha(directory / 'before-reserved-annotations.json')),
        ('output_annotations_sha256', text_digest(protocol_json([row for row in source if row != histories[0]])))):
        require(history.get(key) == value, 'changed actual inline provenance ' + key)
    require(peer.get('peer_routing_version') == 1 and peer.get('scope') == 'native_inlined_reserved_widget_peer_routes_only' and
            peer.get('source_sha256') == sha(directory / 'native-inlined.fir') and
            peer.get('annotations_sha256') == sha(directory / 'native-inlined-annotations.json') and
            peer.get('inline_history_sha256') == text_digest(histories[0]['body']) and
            peer.get('external_transport_state_owner') == 'unsupported_no_state_adapter' and
            peer.get('in_place_checkpoint_widget_connected') is False, 'changed original peer epoch or ownership')
    guarded(peer)
    live = dict(instances(original, root))
    target = re.fullmatch(r'~(\w+)\|(\w+)((?:/\w+:\w+)+)', execution['target'])
    require(target and target[1] == root, 'foreign execution reservation')
    selected_roots = [path for path, module in live.items() if module == target[2]]
    require(len(selected_roots) == 1, 'ambiguous reservation target root')
    selected_path = selected_roots[0]
    for instance, child in re.findall(r'/(\w+):(\w+)', target[3]):
        selected_path += '.' + instance
        require(live.get(selected_path) == child, 'stale reserved execution')
    transports = [(path, module) for path, module in live.items() if original[module]['kind'] == 'extmodule' and
                  re.search(r'^  defname = CheckpointPhysicalCaptureTransport$', original[module]['body'], re.M)]
    require(len(transports) == 1, 'missing or duplicated existing physical transport')
    transport_path, transport_module = transports[0]
    host_path, transport_instance = transport_path.rsplit('.', 1)
    require(peer.get('host') == host_path and peer.get('transport') == transport_path and peer.get('target') == execution['target'] and
            selected_path.startswith(host_path + '.'), 'changed peer host or selected execution')
    host_module = live[host_path]
    require(sum(module == host_module for module in live.values()) == 1, 'shared peer host definition')
    abi = capture_ports(execution['gates'])
    require(len(pins) == len(abi) == 20 and {pin['role'] for pin in pins} == set(abi) and
            len({pin['target'] for pin in pins}) == len(pins), 'incomplete or aliased twenty-role reservation')
    rows, by_role = [], {}
    for pin in sorted(pins, key=lambda row: row['role']):
        role = pin['role']
        match = re.fullmatch(r'~' + re.escape(root) + r'\|' + re.escape(host_module) + r'>(\w+)', pin['target'])
        require(match, 'unsupported peer endpoint contract')
        endpoint = match[1]
        by_role[role] = endpoint
        direction, tpe = abi[role]
        physical = 'reset' if role == 'reset' else transport_instance + '.' + PHYSICAL_PINS[role]
        path = route(original[host_module], endpoint, physical, role == 'reset') if direction == 'input' else route(
            original[host_module], physical, endpoint)
        if direction == 'output':
            value, seen = endpoint, set()
            while value in original[host_module]['drivers']:
                require(value not in seen, 'reserved placeholder alias cycle')
                seen.add(value); value = original[host_module]['drivers'][value]
            require(value == 'UInt<' + re.fullmatch(r'UInt<(\d+)>', tpe)[1] + '>("h0")', 'changed peer return placeholder')
        rows.append(dict(role=role, target=pin['target'], direction='from_transport' if direction == 'input' else 'to_transport',
                         physical_pin=physical, route=path))
    require(peer.get('pins') == rows and peer.get('raw_clock_route') == route(original[host_module], transport_instance + '.clock', 'clock') and
            peer.get('reset_route') == route(original[host_module], transport_instance + '.reset', 'reset', True),
            'crossed original physical peer or raw-clock route')
    require(transport_module in before and before[transport_module] == original[transport_module],
            'changed original opaque transport definition')
    params = dict(re.findall(r'^  parameter (\w+) = (\d+)$', original[transport_module]['body'], re.M))
    require(params == dict(GATES=str(execution['gates']), OWNERS=str(len(execution['owners'])),
        ENTRIES=str(execution['entries']), EXTERNAL_CLOCK_NETWORK='1', RESTORE_ENABLE='0', MANIFEST_SHA256=str(2**256 - 1)),
        'unbound descriptor sentinel, restore guard or transport geometry changed')
    header = (directory / 'reserved.h').read_text()
    require(header.count('#error Unbound_checkpoint_widget_reservation') == 1 and
            [row['body'] for row in source if row['class'] == 'midas.stage.GoldenGateOutputFileAnnotation' and
             row['fileSuffix'] == '.const.h'] == [header], 'unbound header emission guard removed')
    resources = ('CheckpointPhysicalCaptureTransport.sv', 'CheckpointPhysicalClockCut.sv',
                 'CheckpointCaptureTransport.sv', 'CheckpointCaptureCut.sv')
    hashes = {}
    for name in resources:
        sources = [row for row in source if row['class'] == 'firrtl.transforms.BlackBoxInlineAnno' and row['name'] == name]
        require(len(sources) == 1 and sources == [row for row in before_annotations
            if row['class'] == 'firrtl.transforms.BlackBoxInlineAnno' and row['name'] == name] and
            sources[0]['text'] == (directory / name).read_text() and
            (directory / name).read_bytes() == (ROOT / 'sims/firesim/sim/midas/src/main/verilog' / name).read_bytes(),
            'changed registered physical transport source ' + name)
        hashes[name] = sha(directory / name)
    unsupported = dict(hierarchy=transport_path, module=transport_module, defname='CheckpointPhysicalCaptureTransport',
        definition_sha256=text_digest(original[transport_module]['body']), sources=hashes,
        ownership='unsupported_no_atomic_capture_restore_adapter', analysis_projection='invalid_outputs_no_storage_no_emission',
        capture_supported=False, restore_supported=False)
    return host_path, by_role, unsupported


def audit_connection(original, graft, connected, root, host_path, abi, peers, doc):
    live = dict(instances(original, root))
    parts = host_path.split('.')
    require(parts[0] == root, 'peer outside original enclosing root')
    paths = ['.'.join(parts[:index + 1]) for index in range(len(parts))]
    chain = [live[path] for path in paths]
    require(len(set(chain)) == len(chain) and all(sum(module == name for module in live.values()) == 1 for name in chain),
            'shared reverse-routing execution')
    rows = [dict(path=path, module=module, peer_host=index == len(paths) - 1)
            for index, (path, module) in enumerate(zip(paths, chain))]
    require(doc.get('routes') == rows, 'changed reverse-routing ancestor receipt')
    require(doc.get('pins') == [dict(role=role, peer=peers[role], type=tpe) for role, (_, tpe) in abi.items()],
            'changed or omitted twenty-role connection receipt')
    require(set(connected) == set(graft), 'extra or omitted connected definition')
    for name in set(graft) - set(chain):
        require(connected[name] == graft[name], 'connection changed native bank, adapter or unrelated execution ' + name)
    for index, module in enumerate(chain):
        before, after = graft[module], connected[module]
        is_root, is_peer = index == 0, index == len(chain) - 1
        prefix = 'checkpoint_region_widget_'
        expected_ports = dict(original[module]['ports']) if is_root else dict(before['ports'])
        if not is_root:
            expected_ports.update({prefix + role: ('output' if direction == 'input' else 'input', tpe)
                                   for role, (direction, tpe) in abi.items()})
        require(after['ports'] == expected_ports and after['instances'] == before['instances'],
                'changed public interface, reverse role direction or original execution')
        drivers = dict(before['drivers'])
        statements = body_lines(before)
        additions = []
        for role, (direction, tpe) in abi.items():
            signal = 'capture_' + role if is_root else prefix + role
            if is_peer:
                endpoint = peers[role]
                if direction == 'input':
                    require(signal not in drivers, 'duplicate reverse role driver')
                    drivers[signal] = endpoint
                    additions.append(signal + ' <= ' + endpoint)
                else:
                    require(endpoint in drivers, 'missing peer return placeholder')
                    previous = drivers[endpoint]
                    drivers[endpoint] = signal
                    candidates = [i for i, line in enumerate(statements)
                                  if line in (endpoint + ' <= ' + previous, 'node ' + endpoint + ' = ' + previous)]
                    require(len(candidates) == 1, 'ambiguous peer placeholder replacement')
                    offset = candidates[0]
                    statements[offset] = ('node ' + endpoint + ' = ' if statements[offset].startswith('node ')
                                          else endpoint + ' <= ') + signal
            else:
                child_pin = parts[index + 1] + '.' + prefix + role
                lhs, rhs = (signal, child_pin) if direction == 'input' else (child_pin, signal)
                require(lhs not in drivers, 'duplicate reverse route driver')
                drivers[lhs] = rhs
                additions.append(lhs + ' <= ' + rhs)
        if is_root:
            statements = ['wire capture_' + role + ' : ' + tpe for role, (_, tpe) in abi.items()] + statements
        clean = lambda rows: [line for line in rows if line != 'skip']
        require(after['drivers'] == drivers and clean(body_lines(after)) == clean(statements + additions),
                'changed return, descriptor, cut, clock or original functional driver')
    require(connected[root]['ports'] == original[root]['ports'], 'changed original public root interface')
    require(set(dict(instances(original, root))) <= set(dict(instances(connected, root))), 'lost original concrete hierarchy')
    return rows


def audit_ce_endpoint(directory, prefix, index, selected, gates):
    expected = f'''module {selected}CheckpointPhysicalCEBank (
  input wire clock, reset, read_enable,
  input wire [{gates-1}:0] captured_ce,
  input wire [31:0] descriptor_entry,
  output wire descriptor_valid,
  output wire [7:0] descriptor_bank,
  output wire [15:0] descriptor_slot, descriptor_width,
  output wire [31:0] descriptor_depth,
  input wire request_valid,
  output wire request_ready,
  input wire [7:0] bank,
  input wire [15:0] slot,
  input wire [31:0] address,
  output reg response_valid,
  input wire response_ready,
  output reg [63:0] response_data,
  output reg response_error
);
  assign descriptor_valid = descriptor_entry < 32'd{gates};
  assign descriptor_bank = descriptor_valid ? 8'd255 : 8'd0;
  assign descriptor_slot = descriptor_valid ? descriptor_entry[15:0] : 16'd0;
  assign descriptor_width = descriptor_valid ? 16'd1 : 16'd0;
  assign descriptor_depth = descriptor_valid ? 32'd1 : 32'd0;
  assign request_ready = !reset && (!response_valid || response_ready);
  wire selection_valid = bank == 8'd255 && {{16'd0, slot}} < 32'd{gates} && address == 0;
  always @(posedge clock) begin
    if (reset) begin
      response_valid <= 0;
      response_data <= 0;
      response_error <= 0;
    end else begin
      if (response_ready) response_valid <= 0;
      if (request_valid && request_ready) begin
        response_valid <= 1;
        response_error <= !read_enable || !selection_valid;
        response_data <= read_enable && selection_valid ? {{63'd0, captured_ce[slot]}} : 64'd0;
      end
    end
  end
endmodule'''
    actual = (directory / (prefix + f'.native-region-graft-{index}-ce.sv')).read_text()
    require(residue_lines(actual) == residue_lines(expected), 'changed sampled CE selector, permission, clock or response ownership')


def audit_graft(directory, original, merged, graft, root, binding, manifest, descriptor, routing):
    name, instance, clock = root + 'CheckpointRegionReadoutAdapter', 'checkpoint_region_readout_adapter', binding['raw_clock']
    gates = sum(row['domain'] == 'physical_ce' for row in manifest['state'])
    captures = {'capture_' + role: port for role, port in capture_ports(gates).items()}
    access = {pin: port for pin, port in merged[root]['ports'].items() if pin not in original[root]['ports']}
    require(access and all(pin.startswith('checkpoint_inplace_region') for pin in access), 'unbound region access interface')
    require(set(graft) == set(merged) | {name} and all(graft[module] == merged[module] for module in merged if module != root),
            'graft changed native or unrelated execution')
    ports = {clock: ('input', 'Clock')} | {
        pin: ('output' if direction == 'input' else 'input', tpe) for pin, (direction, tpe) in access.items()} | captures
    require(graft[name]['kind'] == 'extmodule' and graft[name]['ports'] == ports and
            residue_lines(graft[name]['body']) == ['extmodule ' + name + ' :'] + [
                direction + ' ' + pin + ' : ' + tpe for pin, (direction, tpe) in ports.items()] + ['defname = ' + name],
            'changed adapter declaration or ABI')
    require(graft[root]['ports'] == original[root]['ports'] | captures and
            graft[root]['instances'] == merged[root]['instances'] | {instance: name}, 'changed root graft interface or execution')
    drivers = {instance + '.' + pin: pin for pin, (direction, _) in ports.items() if direction == 'input'}
    drivers.update({pin: instance + '.' + pin for pin, (direction, _) in ports.items() if direction == 'output'})
    require(not set(drivers) & set(merged[root]['drivers']) and graft[root]['drivers'] == merged[root]['drivers'] | drivers,
            'changed root mask, transaction or raw-clock connection')
    expected = ['wire ' + pin + ' : ' + tpe for pin, (_, tpe) in access.items()] + ['inst ' + instance + ' of ' + name]
    expected += body_lines(merged[root]) + [lhs + ' <= ' + rhs for lhs, rhs in drivers.items()]
    # The generator emits the exact original body between added declarations
    # and connections; connection iteration follows adapter port order.
    actual = body_lines(graft[root])
    additions = expected[:len(access) + 1] + [lhs + ' <= ' + rhs for lhs, rhs in drivers.items()]
    require(len(actual) == len(body_lines(merged[root])) + len(additions) and
            [line for line in actual if line not in additions] == body_lines(merged[root]) and
            sorted(line for line in actual if line in additions) == sorted(additions), 'unexpected root graft logic or storage')
    prefix = 'graft'
    graft_doc = read(directory, prefix + '.native-region-graft.json')
    suffixes = {'.native-region-graft.sv', '.native-region-graft-router.sv', '.native-region-graft-physical-router.sv'}
    suffixes |= {f'.native-region-graft-{index}{kind}.sv' for index in range(len(binding['regions'])) for kind in ('', '-ce')}
    require(set(graft_doc.get('files', {})) == suffixes, 'omitted or unknown generated readout artifact')
    expected_doc = dict(graft_version=1, scope='existing_native_regions_shared_readout_only', root=root,
        adapter_module=name, adapter_instance=instance, raw_clock=clock, regions_binding_sha256=digest(binding),
        grafted_sha256=sha(directory / 'grafted.fir'), descriptor_manifest_sha256=digest(manifest),
        files={suffix: sha(directory / (prefix + suffix)) for suffix in suffixes}, common_mask_and_sample_interface=True,
        **{key: False for key in FLAGS})
    require(graft_doc == expected_doc, 'changed generated graft binding or image admission')
    for suffix in suffixes | {'.native-region-graft.json'}:
        alias = directory / ('FireSim-generated' + suffix)
        if alias.exists():
            require(alias.read_bytes() == (directory / (prefix + suffix)).read_bytes(), 'different readout artifact alias')
    audit_adapter_sv(directory, prefix, root, clock, access, captures, manifest, descriptor, routing)
    for index, local in enumerate(descriptor['regions']):
        local_manifest = local['manifest']
        selected = local_manifest['target'].rsplit(':', 1)[1]
        audit_ce_endpoint(directory, prefix, index, selected, local_manifest['physical_clock_gates'])
    return graft_doc


def _audit(directory):
    directory = Path(directory)
    source_text = (directory / 'native-inlined.fir').read_text()
    require((directory / 'host.fir').read_text() == source_text, 'regional source differs from actual inlined execution')
    root = root_of(source_text)
    original = parse_modules(source_text)
    merged = parse_modules((directory / 'instrumented.fir').read_text())
    graft = parse_modules((directory / 'grafted.fir').read_text())
    connected = parse_modules((directory / 'connected.fir').read_text())
    require(all(root_of((directory / name).read_text()) == root for name in ('instrumented.fir', 'grafted.fir', 'connected.fir')),
            'changed regional/graft/connected circuit root')
    connection = read(directory, 'connection.json')
    require(set(connection) == set(FLAGS) | {
        'connection_version', 'scope', 'source_sha256', 'regions_binding_sha256', 'graft_binding_sha256',
        'peer_routing_sha256', 'annotation_projection_sha256', 'connected_sha256', 'descriptor_manifest_sha256',
        'descriptor_binding_sha256', 'host', 'routes', 'pins', 'in_place_checkpoint_widget_connected',
        'descriptor_identity_bound', 'external_transport_state_owner', 'reserved_inventory_binding_sha256',
        'unsupported_external_owners'}, 'missing or unknown connection contract field')
    binding, manifest, descriptor, routing = (read(directory, name) for name in (
        'binding.json', 'manifest.json', 'descriptor-binding.json', 'routing.json'))
    if (directory / 'descriptors.json').exists():
        require(read(directory, 'descriptors.json') == manifest, 'changed published descriptor manifest alias')
    require(connection.get('connection_version') == 1 and connection.get('scope') == 'reserved_widget_to_existing_disjoint_regions_routes_only' and
            connection.get('in_place_checkpoint_widget_connected') is True and connection.get('descriptor_identity_bound') is False and
            connection.get('external_transport_state_owner') == 'unsupported_no_atomic_capture_restore_adapter', 'changed bounded connection scope')
    guarded(connection)
    for key, filename in (('source_sha256', 'native-inlined.fir'), ('regions_binding_sha256', 'binding.json'),
        ('graft_binding_sha256', 'graft.native-region-graft.json'), ('peer_routing_sha256', 'peer-routing.json'),
        ('connected_sha256', 'connected.fir'), ('descriptor_manifest_sha256', 'manifest.json'),
        ('descriptor_binding_sha256', 'descriptor-binding.json')):
        require(connection.get(key) == sha(directory / filename), 'unbound connection epoch ' + key)
    for key, value in (('host_sha256', sha(directory / 'host.fir')), ('instrumented_sha256', sha(directory / 'instrumented.fir')),
        ('descriptor_manifest_sha256', digest(manifest)), ('descriptor_binding_sha256', digest(descriptor)), ('routing_sha256', digest(routing))):
        require(binding.get(key) == value, 'unbound native region epoch ' + key)
    annotations = read(directory, 'native-inlined-annotations.json')
    executions = [row for row in annotations if row['class'] == EXECUTION]
    require(len(executions) == 1 and annotations.count({'class': NO_DEDUP}) == 1, 'ambiguous reservation/source annotation policy')
    execution = executions[0]
    pins = [row for row in annotations if row['class'] == PIN]
    peer = read(directory, 'peer-routing.json')
    host_path, peers, unsupported = audit_peer(directory, original, root, execution, pins, peer)
    require(connection.get('host') == host_path, 'changed actual peer host')
    inventory_doc = read(directory, 'reserved-inventory.json')
    expected_inventory = dict(inventory_permission_version=1, scope='reserved_widget_global_analysis_only',
        host_sha256=sha(directory / 'native-inlined.fir'), host_annotations_sha256=sha(directory / 'native-inlined-annotations.json'),
        peer_routing_sha256=sha(directory / 'peer-routing.json'), unsupported_external_owners=[unsupported], **{key: False for key in FLAGS})
    source_policy = audit_source_policy(directory, inventory_doc, annotations)
    if source_policy is not None:
        expected_inventory['source_policy'] = source_policy
    require(inventory_doc == expected_inventory, 'unsupported external owner omitted, reclassified or changed')
    for doc in [connection, binding, manifest, descriptor] + [value for local in descriptor['regions'] for value in (local['manifest'], local['binding'])]:
        require(doc.get('unsupported_external_owners') == [unsupported], 'hidden or changed unsupported external owner')
        if doc is not manifest and doc is not descriptor:
            require(doc.get('reserved_inventory_binding_sha256') == digest(inventory_doc), 'unbound reserved inventory permission')
    checked = audit_descriptors(directory, source_text, root, binding, manifest, descriptor, routing)
    original_executions = audit_region_hierarchy(directory, original, merged, root, binding)
    for label in ('host', 'instrumented'):
        values = read(directory, label + '-annotations.json')
        require(len(values) == len({canonical(row) for row in values}) and
            binding.get(label + '_annotations_sha256') == text_digest(protocol_json(sorted(values, key=regional_serialized))),
            'unbound original/projected regional annotation policy')
    from tools.checkpoint_formats.tests.audit_native_inplace_context import CONTEXT_CLASSES
    source_context = [a for a in read(directory, 'host-annotations.json') if a['class'] in CONTEXT_CLASSES]
    require(binding.get('context') == context_snapshot(source_context,
        sha(directory/'host.fir'), sha(directory/'instrumented.fir')), 'changed generated regional compiler context binding')
    audit_graft(directory, original, merged, graft, root, binding, manifest, descriptor, routing)
    require(execution.get('entries') == checked['entries'] and execution.get('gates') == checked['physical_clock_gates'],
            'reservation does not match complete selected descriptor geometry')
    abi = capture_ports(execution['gates'])
    routes = audit_connection(original, graft, connected, root, host_path, abi, peers, connection)
    projection = audit_annotations(directory, original, connected, root, connection)
    require(read(directory, 'grafted-annotations.json') == read(directory, 'instrumented-annotations.json'),
            'shared readout changed regional storage annotations')
    return dict(status='pass', scope='independent reserved-widget native-region structural audit only',
        original_executions=original_executions, root=root, peer_host=host_path, routes=len(routes), pins=len(abi),
        annotations=projection, unsupported_external_owners=1, descriptor_identity_bound=False,
        physical_fpga_capture=False, deployable_capture_image=False, metasim_restore_supported=False, **checked)


def audit(directory):
    """Reject incomplete/unknown contracts with the ordinary format exception."""
    try:
        return _audit(Path(directory))
    except FormatError:
        raise
    except (KeyError, IndexError, TypeError, AttributeError, OSError, json.JSONDecodeError) as error:
        raise FormatError('missing or unsupported region/widget contract: ' + str(error)) from error


def refresh_receipts(directory):
    """Rehash corruption cases so rejection needs structural reconstruction."""
    def save(name, value):
        (directory / name).write_bytes(canonical(value))
    manifest = read(directory, 'manifest.json')
    if (directory / 'descriptors.json').exists():
        (directory / 'descriptors.json').write_bytes(canonical(manifest))
    descriptor = read(directory, 'descriptor-binding.json')
    for local in descriptor['regions']:
        local['binding']['manifest_sha256'] = digest(local['manifest'])
        local['manifest_sha256'] = digest(local['manifest'])
        local['binding_sha256'] = digest(local['binding'])
    descriptor['manifest_sha256'] = digest(manifest)
    save('descriptor-binding.json', descriptor)
    binding = read(directory, 'binding.json')
    binding.update(descriptor_manifest_sha256=digest(manifest), descriptor_binding_sha256=digest(descriptor),
                   routing_sha256=sha(directory / 'routing.json'))
    save('binding.json', binding)
    graft = read(directory, 'graft.native-region-graft.json')
    graft.update(regions_binding_sha256=digest(binding), descriptor_manifest_sha256=digest(manifest),
                 grafted_sha256=sha(directory / 'grafted.fir'))
    for suffix in graft['files']:
        graft['files'][suffix] = sha(directory / ('graft' + suffix))
    save('graft.native-region-graft.json', graft)
    for suffix in set(graft['files']) | {'.native-region-graft.json'}:
        alias = directory / ('FireSim-generated' + suffix)
        if alias.exists():
            alias.write_bytes((directory / ('graft' + suffix)).read_bytes())
    projection = read(directory, 'annotation-projection.json')
    projection['connected_sha256'] = sha(directory / 'connected.fir')
    save('annotation-projection.json', projection)
    connection = read(directory, 'connection.json')
    for key, filename in (('connected_sha256', 'connected.fir'), ('regions_binding_sha256', 'binding.json'),
        ('graft_binding_sha256', 'graft.native-region-graft.json'), ('descriptor_manifest_sha256', 'manifest.json'),
        ('descriptor_binding_sha256', 'descriptor-binding.json'), ('annotation_projection_sha256', 'annotation-projection.json')):
        connection[key] = sha(directory / filename)
    save('connection.json', connection)


def corruptions(directory, out):
    """Run independent connection, selector, resource and admission negatives."""
    directory, out = Path(directory), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rejected = []
    names = ('reverse-role-swap', 'raw-clock', 'functional-update', 'extra-state', 'public-interface',
             'missing-role', 'route-order', 'descriptor-slot', 'local-descriptor-order', 'ce-slice',
             'descriptor-rom', 'read-permission', 'ce-live-sample', 'unknown-annotation',
             'missing-owner', 'unknown-contract-field', 'capture-admission', 'identity-admission', 'restore-parameter', 'header-admission')
    for name in names:
        case = out / name
        case.mkdir()
        for source in directory.iterdir():
            if source.is_file():
                shutil.copyfile(source, case / source.name)
        connection = read(case, 'connection.json')
        source_modules = parse_modules((case / 'native-inlined.fir').read_text())
        root = root_of((case / 'native-inlined.fir').read_text())
        host = dict(instances(source_modules, root))[connection['host']]
        connected = case / 'connected.fir'
        text = connected.read_text()
        if name == 'reverse-role-swap':
            a, b = 'checkpoint_region_widget_request_ready', 'checkpoint_region_widget_response_valid'
            require(a in text and b in text, 'missing same-width route mutation site')
            text = text.replace(a, '__region_widget_swap__').replace(b, a).replace('__region_widget_swap__', b)
        elif name == 'raw-clock':
            old = 'checkpoint_region_readout_adapter.clock <= clock'
            require(old in text, 'missing raw readout clock')
            text = text.replace(old, 'checkpoint_region_readout_adapter.clock <= asClock(reset)', 1)
        elif name == 'functional-update':
            pattern = r'(cycles <= .*?)UInt<1>\("h1"\)'
            text, count = re.subn(pattern, r'\g<1>UInt<1>("h0")', text, count=1)
            require(count == 1, 'missing original functional update mutation site')
        elif name == 'extra-state':
            text = text.replace('  module ' + host + ' :', '  module ' + host + ' :\n    reg invented : UInt<1>, clock', 1)
        elif name == 'public-interface':
            text = text.replace('  module ' + root + ' :', '  module ' + root + ' :\n    output invented : UInt<1>\n    invented <= UInt<1>("h0")', 1)
        elif name == 'missing-role':
            connection['pins'].pop()
        elif name == 'route-order':
            connection['routes'].reverse()
        elif name == 'descriptor-slot':
            manifest = read(case, 'manifest.json')
            manifest['state'][0]['slot'] += 1
            (case / 'manifest.json').write_bytes(canonical(manifest))
        elif name == 'local-descriptor-order':
            descriptor = read(case, 'descriptor-binding.json')
            descriptor['regions'][0]['manifest']['state'][:2] = list(reversed(descriptor['regions'][0]['manifest']['state'][:2]))
            (case / 'descriptor-binding.json').write_bytes(canonical(descriptor))
        elif name in ('ce-slice', 'descriptor-rom'):
            path = case / 'graft.native-region-graft.sv'
            body = path.read_text()
            if name == 'ce-slice':
                old, new = 'capture_captured_ce[0 +: 2]', 'capture_captured_ce[2 +: 2]'
            else:
                old, new = "capture_descriptor_bank=8'd0;", "capture_descriptor_bank=8'd1;"
            require(old in body, 'missing shared readout mutation site')
            path.write_text(body.replace(old, new, 1))
        elif name == 'read-permission':
            path = case / 'graft.native-region-graft-0.sv'
            body = path.read_text()
            old = '.read_enable(capture_read_enable)'
            require(old in body, 'missing read permission mutation site')
            path.write_text(body.replace(old, ".read_enable(1'b1)", 1))
        elif name == 'ce-live-sample':
            path = case / 'graft.native-region-graft-0-ce.sv'
            body = path.read_text()
            old = "{63'd0, captured_ce[slot]}"
            require(old in body, 'missing sampled CE mutation site')
            path.write_text(body.replace(old, "{63'd0, read_enable}", 1))
        elif name == 'unknown-annotation':
            annotations = read(case, 'connected-annotations.json')
            annotations.append({'class': 'unknown.UncontractedRegionOwner', 'target': '~' + root + '|' + host + '>clock'})
            (case / 'connected-annotations.json').write_text(protocol_json(annotations))
            projection = read(case, 'annotation-projection.json')
            projection['projected_annotations_sha256'] = sha(case / 'connected-annotations.json')
            (case / 'annotation-projection.json').write_bytes(canonical(projection))
        elif name == 'missing-owner':
            manifest = read(case, 'manifest.json')
            manifest['unsupported_external_owners'] = []
            (case / 'manifest.json').write_bytes(canonical(manifest))
        elif name == 'unknown-contract-field':
            connection['uncontracted_owner_supported'] = True
        elif name == 'capture-admission':
            connection['complete_fpga_capture'] = True
        elif name == 'identity-admission':
            connection['descriptor_identity_bound'] = True
        elif name == 'restore-parameter':
            text, count = re.subn(r'parameter RESTORE_ENABLE = 0', 'parameter RESTORE_ENABLE = 1', text, count=1)
            require(count == 1, 'missing restore parameter mutation site')
        elif name == 'header-admission':
            header = case / 'reserved.h'
            header.write_text(header.read_text().replace('#error Unbound_checkpoint_widget_reservation', '#define INVENTED_IMAGE_ADMISSION 1'))
        connected.write_text(text)
        (case / 'connection.json').write_bytes(canonical(connection))
        refresh_receipts(case)
        try:
            audit(case)
        except FormatError as error:
            rejected.append(dict(case=name, error=str(error)))
        else:
            raise AssertionError('accepted coherently rehashed region/widget corruption ' + name)
    return rejected


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = audit(args.generated)
    result['auditor_sha256'] = sha(Path(__file__))
    result['generated'] = str(args.generated)
    if args.out:
        allowed = ROOT / 'automations/checkpoint_loop/runs'
        require(args.out.resolve().is_relative_to(allowed), 'checkpoint-loop evidence destination required')
        args.out.mkdir(parents=True, exist_ok=True)
        destination = Path(tempfile.mkdtemp(prefix='corruptions-', dir=args.out))
        result['corruption_directory'] = str(destination)
        result['rejected'] = corruptions(args.generated, destination)
        (args.out / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
