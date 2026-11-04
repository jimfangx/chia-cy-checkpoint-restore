"""Independently check staged regional widget routes without granting ownership.

Accepts the emitted bounded Scala fixture. All original definitions and every
driver are compared against the selected staged circuit; the only allowed
changes are the seventeen transport routes and the manifest identity binding.
"""
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha as sha
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.audit_widget_graft import capture_ports, instances


def audit(directory):
    p = Path(directory)
    read = lambda n: json.loads((p / n).read_text())
    connection, identity = read('connection.json'), read('identity.json')
    snapshot = read('snapshot-binding.json')
    cut, graft = read('cut-binding.json'), read('graft-binding.json')
    selected = parse_modules((p / 'selected.fir').read_text())
    connected = parse_modules((p / 'connected.fir').read_text())
    final = parse_modules((p / 'identity-bound.fir').read_text())
    root = re.search(r'^circuit (\w+) :', (p / 'selected.fir').read_text(), re.M)[1]
    require(connection['connection_version'] == 1 and connection['scope'] ==
            'reserved_widget_to_existing_disjoint_regions_routes_only' and
            connection['selected_cut_snapshot'] is True, 'changed staged connection scope')
    require(connection['selected_sha256'] == sha(p / 'selected.fir') == snapshot['attached_sha256'] and
            connection['selected_snapshot_binding_sha256'] == sha(p / 'snapshot-binding.json') and
            connection['connected_sha256'] == sha(p / 'connected.fir'), 'changed selected circuit binding')
    require(snapshot['cut_binding_sha256'] == sha(p / 'cut-binding.json') and
            cut['graft_binding_sha256'] == connection['graft_binding_sha256'] == sha(p / 'graft-binding.json') and
            cut['regions_binding_sha256'] == graft['regions_binding_sha256'] ==
            connection['regions_binding_sha256'] == sha(p / 'regions-binding.json'), 'changed selected parent chain')
    require(identity['scope'] == 'staged_disjoint_regions_transport_and_host_identity_only' and
            identity['connection_sha256'] == sha(p / 'connection.json') and
            identity['unbound_sha256'] == sha(p / 'connected.fir') and
            identity['bound_sha256'] == sha(p / 'identity-bound.fir'), 'changed identity binding')
    flags = ('production_freeze_owners_bound', 'complete_fpga_capture',
             'deployable_capture_image', 'metasim_restore_supported')
    require(all(connection[k] is False and identity[k] is False for k in flags) and
            all(connection[k] is False for k in ('cut_snapshot_mmio_controls_bound',
                'readout_router_state_atomically_owned', 'staging_owner_restore_supported')),
            'unsupported ownership admission')
    require(identity['descriptor_identity_bound'] is True and
            connection['descriptor_identity_bound'] is False, 'changed identity-only contract')
    roles = {n: v for n, v in capture_ports(identity['gates']).items()
             if n not in {'clock_mask', 'read_enable', 'captured_ce'}}
    require(len(roles) == 17 and len(connection['pins']) == 17 and
            {r['role'] for r in connection['pins']} == set(roles), 'missing or extra transport role')
    peers = {r['role']: r['peer'] for r in connection['pins']}
    require(all(r['type'] == roles[r['role']][1] for r in connection['pins']), 'changed role width')
    require(connection['source_sha256'] == sha(p / 'after.fir'), 'changed source binding')
    original_pins = [a for a in read('after.anno.json') if
                     a['class'] == 'midas.checkpoint.NativeCheckpointWidgetPinAnnotation']
    require(len(original_pins) == 20 and len({a['role'] for a in original_pins}) == 20,
            'missing or duplicate original registered pin')
    pin_refs = {a['role']: a['target'].split('>')[-1] for a in original_pins}
    require(peers == {role: pin_refs[role] for role in roles}, 'changed original registered peer')
    paths = dict(instances(selected, root))
    host = connection['host']
    chain = ['.'.join(host.split('.')[:i]) for i in range(1, len(host.split('.')) + 1)]
    require(chain[0] == root and len(set(paths[x] for x in chain)) == len(chain), 'ambiguous route ancestors')
    require(connection['routes'] == [dict(path=x, module=paths[x], peer_host=x == host) for x in chain],
            'changed route execution list')
    require(set(selected) == set(connected) == set(final), 'added or lost definition')
    require(instances(selected, root) == instances(connected, root) == instances(final, root),
            'changed original executions')
    for name, module in selected.items():
        if name not in {paths[x] for x in chain}:
            require(module == connected[name], 'changed non-route definition ' + name)
    for i, path in enumerate(chain):
        name = paths[path]
        before, after = selected[name], connected[name]
        ports, drivers = dict(before['ports']), dict(before['drivers'])
        require(before['instances'] == after['instances'] and before['consumers'] == after['consumers'] and
                before['effects'] == after['effects'], 'changed original owner ' + path)
        for role, (direction, tpe) in roles.items():
            signal = 'capture_' + role if i == 0 else 'checkpoint_region_widget_' + role
            if i == 0:
                require(ports.pop(signal) == (direction, tpe), 'changed selected role ABI')
            else:
                require(signal not in ports, 'route port collision')
                ports[signal] = ('output' if direction == 'input' else 'input', tpe)
            if path == host:
                if direction == 'input':
                    require(signal not in drivers, 'input route has original driver')
                    drivers[signal] = peers[role]
                else:
                    require(peers[role] in drivers, 'missing return placeholder')
                    drivers[peers[role]] = signal
            else:
                child = chain[i + 1].split('.')[-1] + '.checkpoint_region_widget_' + role
                destination, source = (signal, child) if direction == 'input' else (child, signal)
                require(destination not in drivers, 'route driver collision')
                drivers[destination] = source
        require(after['ports'] == ports and after['drivers'] == drivers, 'changed complete route or controller ' + path)
        def structure(module):
            lines = [re.sub(r' @\[.*$', '', line).strip() for line in module['body'].splitlines() if line.strip()]
            return [line for line in lines if not re.match(r'(input|output|node) \w+ ', line)
                    and ' <= ' not in line and not line.endswith(' is invalid')]
        expected = structure(before)
        if i == 0:
            expected = expected[:1] + ['wire capture_' + role + ' : ' + tpe for role, (_, tpe) in roles.items()] + expected[1:]
        require(structure(after) == expected, 'changed original declaration, width or statement ' + path)
    # Identity may change only the one reserved transport parameter.
    digest = sha(p / 'descriptors.json')
    require(identity['descriptor_manifest_sha256'] == connection['descriptor_manifest_sha256'] == digest and
            identity['descriptor_binding_sha256'] == connection['descriptor_binding_sha256'] ==
            sha(p / 'descriptor-binding.json'), 'changed descriptor identity')
    old, new = 'parameter MANIFEST_SHA256 = ' + str(2**256 - 1), 'parameter MANIFEST_SHA256 = ' + str(int(digest, 16))
    text = (p / 'connected.fir').read_text()
    require(text.count(old) == 1 and (p / 'identity-bound.fir').read_text() == text.replace(old, new),
            'identity changed non-identity circuit')
    annotations = read('identity-bound.anno.json')
    resources = dict(graft['files'])
    for suffix, digest in {'.native-region-graft.json': sha(p / 'graft-binding.json'),
            '.native-region-cut-controller.sv': cut['controller_source_sha256'],
            **snapshot['resource_hashes']}.items():
        require(suffix not in resources, 'conflicting generated resource suffix')
        resources[suffix] = digest
    require(connection['selected_resource_hashes'] == resources, 'incomplete selected generated resource set')
    for suffix, digest in connection['selected_resource_hashes'].items():
        resource = p / ('generated' + suffix)
        require(sha(resource) == digest and sum(a.get('fileSuffix') == suffix for a in annotations) == 1 and
                sum(a.get('body') == resource.read_text() and
                a.get('fileSuffix') == suffix for a in annotations) == 1, 'missing or changed emitted resource ' + suffix)
    for suffix, digest in snapshot['resource_hashes'].items():
        require(connection['selected_resource_hashes'].get(suffix) == digest, 'lost staging resource')
    headers = [a['body'] for a in annotations if a.get('fileSuffix') == '.const.h']
    require(len(headers) == 1 and '#error Incomplete_checkpoint_hardware_coverage' in headers[0] and
            hashlib.sha256(headers[0].encode()).hexdigest() == identity['header_after_sha256'],
            'changed registered header or missing image guard')
    original_headers = [a['body'] for a in read('after.anno.json') if a.get('fileSuffix') == '.const.h']
    connected_annotations = read('connected.anno.json')
    require(len(original_headers) == 1 and [a['body'] for a in connected_annotations
            if a.get('fileSuffix') == '.const.h'] == original_headers and
            hashlib.sha256(original_headers[0].encode()).hexdigest() == identity['header_before_sha256'],
            'changed original registered host header')
    allocation = re.findall(r'(?m)^// CHECKPOINT_WIDGET_RESERVATION_BEGIN base=(\d+) stream=(\d+)\n'
                            r'#error Unbound_checkpoint_widget_reservation\n'
                            r'// CHECKPOINT_WIDGET_RESERVATION_END\n', original_headers[0])
    require(allocation == [(str(identity['base']), str(identity['stream']))],
            'host identity differs from original registered allocation')
    require(annotations == [dict(a, body=headers[0]) if a.get('fileSuffix') == '.const.h' else a
            for a in connected_annotations], 'identity changed non-header annotations')
    state = read('descriptors.json')['state']
    require(len(state) == identity['entries'] and re.findall(r'// descriptor\[(\d+)\] StateID: ([^\n]+)',
            headers[0]) == [(str(i), row['state_id']) for i, row in enumerate(state)], 'descriptor entry loss')
    digest = sha(p / 'descriptors.json')
    manifest_bytes = ', '.join('0x' + digest[i:i+2] for i in range(62, -1, -2))
    rows = ', '.join('{' + ', '.join(str(row[k]) + 'U' for k in ('bank', 'slot', 'width', 'depth')) + '}' for row in state)
    cpp = 'checkpoint_capture_manifest_t{{{' + manifest_bytes + '}}, {' + rows + '}}'
    constructor = ('registry.add_widget(new checkpoint_capture_t(simif, *registry.get_stream_engine(), ' +
                   str(identity['base']) + 'ULL, ' + str(identity['stream']) + 'U,\n  ' + cpp + '));\n')
    code = re.sub(r'/\*[\s\S]*?\*/|//[^\n]*', '', headers[0])
    blocks = re.findall(r'(?m)^#ifdef GET_BRIDGE_CONSTRUCTOR\n([\s\S]*?)^#endif\n', code)
    require([b for b in blocks if 'new checkpoint_capture_t(' in b] == [constructor] and
            code.count('new checkpoint_capture_t(') == 1, 'changed executable host table or allocation')
    return dict(status='pass', definitions=len(final), routes=17 * len(chain),
                original_executions_preserved=True, complete_driver_comparison=True,
                complete_fpga_capture=False, deployable_capture_image=False)


def audit_negatives(directory, out):
    """Coherently rehash route mutations so independent connectivity must reject."""
    from tools.checkpoint_formats.codec import FormatError
    directory, out = Path(directory), Path(out)
    rejected = []
    names = ('cut-pending', 'snapshot-clock', 'request-bypass', 'response-bypass',
             'mask-owner', 'peer', 'resource', 'missing-resource-annotation',
             'missing-controller-resource', 'missing-router-resource', 'duplicate-resource',
             'host-allocation', 'header-guard', 'admission')
    for name in names:
        work = out / name
        work.mkdir(parents=True)
        for p in directory.iterdir():
            if p.is_file():
                (work / p.name).symlink_to(p.resolve())

        def write(n, text):
            p = work / n
            if p.is_symlink():
                p.unlink()
            p.write_text(text)

        def read(n):
            return json.loads((work / n).read_text())

        connection, identity = read('connection.json'), read('identity.json')
        if name in names[:5]:
            text = (work / 'connected.fir').read_text()
            patterns = {
                'cut-pending': r'checkpoint_region_cut_snapshot.source_pending <= [^\n]+',
                'snapshot-clock': r'checkpoint_region_cut_snapshot.clock <= [^\n]+',
                'request-bypass': r'checkpoint_region_cut_snapshot.request_valid <= [^\n]+',
                'response-bypass': r'capture_response_valid <= checkpoint_region_cut_snapshot.response_valid',
                'mask-owner': r'(?m)^    capture_clock_mask <= [^\n]+',
            }
            matches = re.findall(patterns[name], text)
            require(len(matches) == 1, 'ambiguous staged mutation ' + name)
            old = matches[0]
            value = 'asClock(UInt<1>("h0"))' if name == 'snapshot-clock' else 'UInt<1>("h0")'
            new = old.split(' <= ')[0] + ' <= ' + value
            write('connected.fir', text.replace(old, new))
            write('identity-bound.fir', (work / 'identity-bound.fir').read_text().replace(old, new))
            connection['connected_sha256'] = sha(work / 'connected.fir')
            identity['unbound_sha256'] = connection['connected_sha256']
            identity['bound_sha256'] = sha(work / 'identity-bound.fir')
        elif name == 'peer':
            connection['pins'][0]['peer'] += '_changed'
        elif name == 'resource':
            suffix = '.native-region-cut-snapshot.sv'
            n = 'generated' + suffix
            write(n, (work / n).read_text() + '\n// corrupted resource\n')
            connection['selected_resource_hashes'][suffix] = sha(work / n)
            snapshot = read('snapshot-binding.json')
            snapshot['resource_hashes'][suffix] = sha(work / n)
            write('snapshot-binding.json', json.dumps(snapshot))
            connection['selected_snapshot_binding_sha256'] = sha(work / 'snapshot-binding.json')
        elif name == 'missing-resource-annotation':
            write('identity-bound.anno.json', json.dumps([a for a in read('identity-bound.anno.json')
                  if a.get('fileSuffix') != '.native-region-cut-snapshot.sv']))
        elif name in ('missing-controller-resource', 'missing-router-resource'):
            suffix = '.native-region-cut-controller.sv' if name == 'missing-controller-resource' else '.native-region-graft-router.sv'
            connection['selected_resource_hashes'].pop(suffix)
            write('identity-bound.anno.json', json.dumps([a for a in read('identity-bound.anno.json')
                  if a.get('fileSuffix') != suffix]))
        elif name == 'duplicate-resource':
            annotations = read('identity-bound.anno.json')
            resource = next(a for a in annotations if a.get('fileSuffix') == '.native-region-cut-controller.sv')
            annotations.append(dict(resource, body=resource['body'] + '\n// conflicting duplicate\n'))
            write('identity-bound.anno.json', json.dumps(annotations))
        elif name == 'host-allocation':
            annotations = read('identity-bound.anno.json')
            old = str(identity['base']) + 'ULL, ' + str(identity['stream']) + 'U,'
            identity['base'] += 8
            new = str(identity['base']) + 'ULL, ' + str(identity['stream']) + 'U,'
            for a in annotations:
                if a.get('fileSuffix') == '.const.h':
                    require(a['body'].count(old) == 1, 'ambiguous host allocation mutation')
                    a['body'] = a['body'].replace(old, new)
                    identity['header_after_sha256'] = hashlib.sha256(a['body'].encode()).hexdigest()
            write('identity-bound.anno.json', json.dumps(annotations))
        elif name == 'header-guard':
            annotations = read('identity-bound.anno.json')
            for a in annotations:
                if a.get('fileSuffix') == '.const.h':
                    a['body'] = a['body'].replace('#error Incomplete_checkpoint_hardware_coverage', '')
                    identity['header_after_sha256'] = hashlib.sha256(a['body'].encode()).hexdigest()
            write('identity-bound.anno.json', json.dumps(annotations))
        else:
            connection['complete_fpga_capture'] = identity['complete_fpga_capture'] = True
        write('connection.json', json.dumps(connection))
        identity['connection_sha256'] = sha(work / 'connection.json')
        write('identity.json', json.dumps(identity))
        try:
            audit(work)
        except FormatError:
            rejected.append(name)
        else:
            raise FormatError('staged widget mutation escaped: ' + name)
    return rejected
