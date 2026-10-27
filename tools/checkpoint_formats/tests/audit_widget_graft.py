"""Independently reconstruct reserved-widget connections into one execution.

This audit checks lowered circuit changes, not complete FPGA state ownership.
The descriptor sentinel and production emission rejection remain mandatory.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def load(directory, name):
    return json.loads((directory / name).read_text())


def lines(module):
    return [re.sub(r' @\[.*$', '', line).strip()
            for line in module['body'].splitlines() if line.strip()]


def instances(modules, root):
    result = []

    def visit(module, path, seen):
        require(module in modules and module not in seen, 'missing or recursive execution')
        result.append((path, module))
        for name, child in modules[module]['instances'].items():
            visit(child, path + '.' + name, seen | {module})

    visit(root, root, set())
    return result


def capture_ports(gates):
    return {name: ('input' if source else 'output', 'UInt<' + str(width) + '>')
            for name, width, source in (
                ('reset', 1, True), ('clock_mask', 1, True), ('read_enable', 1, True),
                ('captured_ce', gates, True), ('logical_ce', gates, False),
                ('descriptor_entry', 32, True), ('descriptor_valid', 1, False),
                ('descriptor_bank', 8, False), ('descriptor_slot', 16, False),
                ('descriptor_width', 16, False), ('descriptor_depth', 32, False),
                ('request_valid', 1, True), ('request_ready', 1, False),
                ('bank', 8, True), ('slot', 16, True), ('address', 32, True),
                ('response_valid', 1, False), ('response_ready', 1, True),
                ('response_data', 64, False), ('response_error', 1, False))}


def audit(directory):
    directory = Path(directory)
    if (directory / 'identity.json').is_file():
        from tools.checkpoint_formats.tests.audit_widget_identity import audit as audit_identity
        return audit_identity(directory)
    doc = load(directory, 'connection.json')
    peer = load(directory, 'peer-routing.json')
    before = parse_modules((directory / 'before-reserved.fir').read_text())
    old = parse_modules((directory / 'native-inlined.fir').read_text())
    original = parse_modules((directory / 'original-selected.fir').read_text())
    graft = parse_modules((directory / 'graft.fir').read_text())
    connected = parse_modules((directory / 'connected.fir').read_text())
    require(doc['connection_version'] == 1 and
            doc['scope'] == 'reserved_widget_to_existing_selected_graft_routes_only',
            'changed connection scope')
    require(doc['in_place_checkpoint_widget_connected'] is True and
            doc['external_transport_state_owner'] == 'unsupported_no_state_adapter' and
            doc['descriptor_identity_bound'] is False and
            all(doc[k] is False for k in ('complete_fpga_capture', 'deployable_capture_image',
                                         'production_annotations_translated',
                                         'production_freeze_owners_bound', 'metasim_restore_supported')),
            'connection falsely admits an image or owner')
    for key, filename in (
        ('peer_routing_sha256', 'peer-routing.json'), ('source_sha256', 'native-inlined.fir'),
        ('original_selected_sha256', 'original-selected.fir'), ('graft_sha256', 'graft.fir'),
        ('connected_sha256', 'connected.fir')):
        require(doc[key] == sha(directory / filename), 'stale connection input ' + key)
    graft_bindings = list(directory.glob('*.native-inplace-graft.json'))
    require(len(graft_bindings) == 1 and doc['graft_binding_sha256'] == sha(graft_bindings[0]),
            'unbound reconstructed graft')
    graft_binding = json.loads(graft_bindings[0].read_text())
    require(graft_binding['source_sha256'] == sha(directory / 'original-selected.fir') and
            graft_binding['grafted_sha256'] == sha(directory / 'graft.fir') and
            all(graft_binding[k] is False for k in ('complete_fpga_capture', 'deployable_capture_image',
                                                   'production_freeze_owners_bound', 'metasim_restore_supported')),
            'changed selected graft inputs or scope')
    # Native history remains an immutable record of the actual inline operation.
    annotations = load(directory, 'native-inlined-annotations.json')
    projection = None
    if (directory / 'annotation-projection.json').is_file():
        from tools.checkpoint_formats.tests.audit_widget_annotations import audit as audit_annotations
        projection = audit_annotations(directory)
    else:
        require('host_annotation_projection_sha256' not in doc, 'missing bound annotation projection')
        require(load(directory, 'connected-annotations.json') == annotations,
                'changed enclosing annotations or foreign selected targets')
    history = [a for a in annotations if a['class'] == 'midas.passes.SimulationInlineResultAnnotation']
    require(len(history) == 1, 'missing native inline history')
    history_doc = json.loads(history[0]['body'])
    require(history_doc['input_sha256'] == sha(directory / 'before-reserved.fir') and
            history_doc['output_sha256'] == sha(directory / 'native-inlined.fir'),
            'unbound actual inline circuit')
    require(peer['source_sha256'] == sha(directory / 'native-inlined.fir') and
            peer['annotations_sha256'] == sha(directory / 'native-inlined-annotations.json') and
            peer['inline_history_sha256'] == digest(history[0]['body']), 'unbound peer phase')
    execution = [a for a in annotations if a['class'] == 'midas.checkpoint.NativeCheckpointWidgetExecutionAnnotation']
    require(len(execution) == 1, 'ambiguous execution reservation')
    execution = execution[0]
    match = re.fullmatch(r'~(\w+)\|(\w+)((?:/\w+:\w+)+)', execution['target'])
    require(match and match[1] == match[2], 'execution must start at enclosing root')
    root = match[1]
    segments = re.findall(r'/(\w+):(\w+)', match[3])
    selected_path = root + ''.join('.' + name for name, _ in segments)
    selected_module = segments[-1][1]
    host_path = selected_path.rsplit('.', 1)[0]
    old_live = instances(old, root)
    by_path = dict(old_live)
    require(by_path.get(selected_path) == selected_module and
            doc['selected'] == selected_path and doc['selected_module'] == selected_module and
            doc['host'] == peer['host'] == host_path, 'changed selected execution or peer host')
    host = by_path[host_path]
    selected_instance = segments[-1][0]
    require(re.search(r'^circuit (\w+) :', (directory / 'original-selected.fir').read_text(), re.M)[1]
            == selected_module, 'wrong original selected circuit')
    selected_live = instances(original, selected_module)
    require(set(original) == {module for _, module in selected_live}, 'unreachable selected definitions')
    require(all(name in old and old[name] == module for name, module in original.items()),
            'different original selected implementation')
    require(graft[selected_module]['ports'] == original[selected_module]['ports'] |
            {'capture_' + role: port for role, port in capture_ports(execution['gates']).items()},
            'changed selected functional or capture interface')
    require(set(original) <= set(graft), 'lost original selected definition')
    allowed = [{'class': 'firrtl.transforms.NoCircuitDedupAnnotation$'}]
    require((directory / 'source-policy.json').is_file() or
            (load(directory, 'original-selected-annotations.json') == allowed and
            load(directory, 'graft-annotations.json') == allowed),
            'untranslated selected annotation or target')
    require(set(connected) == set(old) | set(graft), 'lost or additional enclosing definition')
    replaced, added = [], []
    for name, module in graft.items():
        if name in old:
            if old[name] != module:
                require(name in original and all(path == selected_path or path.startswith(selected_path + '.')
                                                for path, owner in old_live if owner == name),
                        'changed shared or unrelated executing definition')
                replaced.append(dict(module=name, before_sha256=digest(old[name]['body']),
                                     after_sha256=digest(module['body'])))
        else:
            added.append(dict(module=name, sha256=digest(module['body'])))
        require(connected[name] == module, 'changed grafted definition ' + name)
    # Every module outside the one changed peer and the validated graft survives.
    for name in set(old) - set(graft) - {host}:
        require(connected[name] == old[name], 'changed unrelated module ' + name)
    require(sorted(doc['replaced_modules'], key=lambda r: r['module']) == sorted(replaced, key=lambda r: r['module']) and
            sorted(doc['added_modules'], key=lambda r: r['module']) == sorted(added, key=lambda r: r['module']),
            'incomplete changed-module provenance')
    require(old[host]['ports'] == connected[host]['ports'] and
            old[host]['instances'] == connected[host]['instances'], 'changed host interface or duplicated execution')
    pins = [a for a in annotations if a['class'] == 'midas.checkpoint.NativeCheckpointWidgetPinAnnotation']
    abi = capture_ports(execution['gates'])
    require(len(pins) == len(abi) and {p['role'] for p in pins} == set(abi), 'missing or duplicated peer role')
    before_annotations = load(directory, 'before-reserved-annotations.json')
    require(pins == [a for a in before_annotations if a['class'] ==
                     'midas.checkpoint.NativeCheckpointWidgetPinAnnotation'], 'changed original peer markers')
    require(peer['scope'] == 'native_inlined_reserved_widget_peer_routes_only' and
            peer['external_transport_state_owner'] == 'unsupported_no_state_adapter' and
            all(peer[k] is False for k in ('in_place_checkpoint_widget_connected',
                                          'production_freeze_owners_bound', 'complete_fpga_capture',
                                          'deployable_capture_image', 'metasim_restore_supported')),
            'changed original peer scope')
    physical_pins = dict(clock_mask='clock_mask', read_enable='physical_read_enable',
                         captured_ce='captured_ce', logical_ce='ce',
                         descriptor_entry='descriptor_entry', descriptor_valid='descriptor_valid',
                         descriptor_bank='descriptor_bank', descriptor_slot='descriptor_slot',
                         descriptor_width='descriptor_width', descriptor_depth='descriptor_depth',
                         request_valid='bank_request_valid', request_ready='bank_request_ready',
                         bank='bank', slot='slot', address='address', response_valid='bank_response_valid',
                         response_ready='bank_response_ready', response_data='bank_response_data',
                         response_error='bank_response_error')
    transports = [name for name, definition in old[host]['instances'].items()
                  if old[definition]['kind'] == 'extmodule' and
                  'defname = CheckpointPhysicalCaptureTransport' in old[definition]['body']]
    require(len(transports) == 1 and peer['transport'] == host_path + '.' + transports[0],
            'ambiguous physical peer')
    transport = transports[0]

    def route(start, stop, cast=False):
        path = []
        while True:
            require(start not in path, 'original peer alias cycle')
            path.append(start)
            if start == stop:
                return path
            require(start in old[host]['drivers'], 'undriven original peer')
            value = old[host]['drivers'][start]
            match = re.fullmatch(r'asUInt\(([\w.$]+)\)', value or '')
            if cast and match:
                value = match[1]
            require(re.fullmatch(r'[\w.$]+', value or ''), 'non-alias original peer')
            start = value

    require(peer['raw_clock_route'] == route(transport + '.clock', 'clock') and
            peer['reset_route'] == route(transport + '.reset', 'reset', True),
            'changed original raw clock/reset route')
    expected_drivers = dict(old[host]['drivers'])
    expected_lines = lines(old[host])
    rows, peer_rows = [], []
    for pin in sorted(pins, key=lambda p: p['role']):
        role = pin['role']
        endpoint = re.fullmatch(r'~\w+\|\w+>(\w+)', pin['target'])
        require(endpoint, 'only exact peer module-local reference supported')
        endpoint = endpoint[1]
        direction, tpe = abi[role]
        physical = 'reset' if role == 'reset' else transport + '.' + physical_pins[role]
        path = route(endpoint, physical, role == 'reset') if direction == 'input' else route(physical, endpoint)
        if direction == 'output':
            zero = endpoint
            visited = set()
            while zero in old[host]['drivers']:
                require(zero not in visited, 'original placeholder cycle')
                visited.add(zero)
                zero = old[host]['drivers'][zero]
            width = re.fullmatch(r'UInt<(\d+)>', tpe)[1]
            require(zero == 'UInt<' + width + '>("h0")', 'changed original zero placeholder')
        peer_rows.append(dict(role=role, target=pin['target'],
                              direction='from_transport' if direction == 'input' else 'to_transport',
                              physical_pin=physical, route=path))
        selected_pin = selected_instance + '.capture_' + role
        if direction == 'input':
            require(selected_pin not in expected_drivers, 'duplicate selected capture driver')
            expected_drivers[selected_pin] = endpoint
            expected_lines.append(selected_pin + ' <= ' + endpoint)
        else:
            require(endpoint in expected_drivers, 'undriven peer return')
            previous = expected_drivers[endpoint]
            expected_drivers[endpoint] = selected_pin
            candidates = [i for i, line in enumerate(expected_lines)
                          if line in (endpoint + ' <= ' + previous, 'node ' + endpoint + ' = ' + previous)]
            require(len(candidates) == 1, 'ambiguous peer replacement')
            i = candidates[0]
            expected_lines[i] = ('node ' + endpoint + ' = ' if expected_lines[i].startswith('node ')
                                 else endpoint + ' <= ') + selected_pin
        rows.append(dict(role=role, peer=endpoint, selected_pin=selected_pin,
                         direction='from_transport' if direction == 'input' else 'to_transport', type=tpe))
    require(connected[host]['drivers'] == expected_drivers, 'changed direct transaction or raw clock wiring')
    require(sorted(lines(connected[host])) == sorted(expected_lines),
            'unexpected peer logic, storage or side effect')
    require(doc['pins'] == rows, 'changed direct connection receipt')
    require(peer['pins'] == peer_rows, 'changed original physical peer route receipt')
    # None of the resource/header identities may escape reservation admission.
    transports = [m for m in connected.values() if m['kind'] == 'extmodule' and
                  'defname = CheckpointPhysicalCaptureTransport' in m['body']]
    require(len(transports) == 1, 'ambiguous physical transport')
    params = dict(re.findall(r'^\s+parameter (\w+) = (\d+)$', transports[0]['body'], re.M))
    require(params.get('MANIFEST_SHA256') == str(2**256 - 1) and params.get('RESTORE_ENABLE') == '0',
            'unbound descriptor identity or restore guard removed')
    require('#error Unbound_checkpoint_widget_reservation' in (directory / 'reserved.h').read_text(),
            'unbound driver escaped emission guard')
    headers = [a['body'] for a in annotations if a['class'] == 'midas.stage.GoldenGateOutputFileAnnotation'
               and a['fileSuffix'] == '.const.h']
    require(headers == [(directory / 'reserved.h').read_text()], 'changed registered resource header')
    for name in ('CheckpointPhysicalCaptureTransport.sv', 'CheckpointPhysicalClockCut.sv',
                 'CheckpointCaptureTransport.sv', 'CheckpointCaptureCut.sv'):
        def source_annotations(values):
            return [a for a in values if a['class'] == 'firrtl.transforms.BlackBoxInlineAnno' and a['name'] == name]
        sources = source_annotations(annotations)
        require(len(sources) == 1 and sources == source_annotations(before_annotations) and
                sources[0]['text'] == (directory / name).read_text(), 'changed physical transport resource ' + name)
    require(len([path for path, _ in instances(connected, root) if path == selected_path]) == 1,
            'lost executing selected instance')
    return dict(pins=len(rows), selected=selected_path, replaced_modules=len(replaced), added_modules=len(added),
                physical_fpga_capture=False, descriptor_identity_bound=False,
                transport_state_owner='unsupported_no_state_adapter', **({'annotation_projection': projection} if projection else {}))


def corruptions(directory, out):
    directory, out = Path(directory), Path(out)
    if (directory / 'identity.json').is_file():
        from tools.checkpoint_formats.tests.audit_widget_identity import corruptions as identity_corruptions
        return identity_corruptions(directory, out)
    out.mkdir(parents=True, exist_ok=True)
    rejected = []
    for name in ('capture-admission', 'identity-admission', 'missing-pin', 'return-swap',
                 'wrong-clock', 'target-state', 'extra-state', 'changed-header', 'foreign-annotation'):
        case = out / name
        case.mkdir()
        for source in directory.iterdir():
            if source.is_file():
                shutil.copyfile(source, case / source.name)
        doc = copy.deepcopy(load(case, 'connection.json'))
        text = (case / 'connected.fir').read_text()
        if name == 'capture-admission':
            doc['complete_fpga_capture'] = True
        elif name == 'identity-admission':
            doc['descriptor_identity_bound'] = True
        elif name == 'missing-pin':
            doc['pins'].pop()
        elif name == 'return-swap':
            rows = [r for r in doc['pins'] if r['direction'] == 'to_transport' and r['type'] == 'UInt<1>']
            require(len(rows) >= 2, 'no same-width return mutation')
            a, b = rows[:2]
            require(a['selected_pin'] in text, 'missing return mutation site')
            text = text.replace(a['selected_pin'], b['selected_pin'])
        elif name == 'wrong-clock':
            match = re.search(r'(?m)^\s+\w+\.clock <= clock(?: @\[.*)?$', text)
            require(match, 'missing raw clock mutation')
            site = match[0]
            text = text.replace(site, site.replace('<= clock', '<= asClock(reset)'), 1)
        elif name == 'target-state':
            text, count = re.subn(r'(cycles <= .*?)UInt<1>\("h1"\)', r'\g<1>UInt<1>("h0")', text, count=1)
            require(count == 1, 'missing actual target update mutation')
        elif name == 'extra-state':
            text = text.replace('  module ' + doc['selected_module'] + ' :',
                                '  module ' + doc['selected_module'] + ' :\n    reg invented : UInt<1>, clock')
        elif name == 'changed-header':
            (case / 'reserved.h').write_text((case / 'reserved.h').read_text().replace(
                '#error Unbound_checkpoint_widget_reservation', '#define INVENTED_ADMISSION 1'))
        elif name == 'foreign-annotation':
            annotations = load(case, 'connected-annotations.json')
            annotations.append(dict({'class': 'firrtl.transforms.DontTouchAnnotation'},
                                    target='~foreign|foreign>state'))
            (case / 'connected-annotations.json').write_text(json.dumps(annotations))
        (case / 'connected.fir').write_text(text)
        doc['connected_sha256'] = sha(case / 'connected.fir')
        (case / 'connection.json').write_text(json.dumps(doc))
        try:
            audit(case)
        except FormatError as error:
            rejected.append(dict(case=name, error=str(error)))
        else:
            raise AssertionError('accepted coherently rehashed connection corruption ' + name)
    if (directory / 'annotation-projection.json').is_file():
        from tools.checkpoint_formats.tests.audit_widget_annotations import corruptions as annotation_corruptions
        rejected.extend(annotation_corruptions(directory, out / 'annotations'))
    return rejected
