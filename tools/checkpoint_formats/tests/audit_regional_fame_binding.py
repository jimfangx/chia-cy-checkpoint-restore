"""Check exact Rocket compiler/widget projection after regional freeze audit.

This compares raw pre-hookup and final role-owning definitions, traces the
physical mask through real aliases, and checks descriptor/header identity.
It supplies no missing owner, global target time, restore or image authority.
The caller must also run audit_regional_fame_freeze on the source regional pair.
"""
from pathlib import Path
import json
import re

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha as sha
from tools.checkpoint_formats.tests.audit_regional_fame_freeze import executions
from tools.checkpoint_formats.tests.audit_native_fame_progress import metadata, location
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.audit_region_widget_graft import consume_rom


def audit(directory):
    p = Path(directory)
    identity = json.loads((p / 'identity-binding.json').read_text())
    manifest = json.loads((p / 'descriptors.json').read_text())
    require(identity['identity_version'] == 1 and
            identity['scope'] == 'disjoint_regions_transport_and_host_identity_only' and
            identity['descriptor_identity_bound'] is True and
            identity['production_annotations_translated'] is False and
            identity['external_transport_state_owner'] == 'unsupported_no_state_adapter',
            'unsupported final binding scope or ownership admission')
    result = {}
    banked = parse_modules((p / 'regional-instrumented.fir').read_text())
    final = parse_modules((p / 'identity-bound.fir').read_text())
    root_name = 'F1Shim'
    (banked_models, banked_roles) = metadata(json.loads((p / 'regional-instrumented.anno.json').read_text()))
    (final_models, final_roles) = metadata(json.loads((p / 'identity-bound.anno.json').read_text()))
    require(banked_models and banked_roles and banked_models == final_models and banked_roles == final_roles, 'regional FAME final binding check failed')
    for (key, row) in banked_roles.items():
        (a, owner, ref) = location(banked, root_name, row['target'])
        (z, changed, ref2) = location(final, root_name, final_roles[key]['target'])
        require(a == z and ref == ref2 and (owner == changed), 'final hookup changed FAME role owner')
    root_module = final[root_name]
    paths = executions(final, root_name)
    adapter = 'checkpoint_region_readout_adapter'
    definition = root_module['instances'][adapter]
    require(final[definition] == parse_modules((p / 'grafted.fir').read_text())[definition], 'regional FAME final binding check failed')
    binding = json.loads((p / 'regions.json').read_text())
    main_sv = (p / 'generated.native-region-graft.sv').read_text()
    consume_rom(main_sv, manifest['state'], 'capture_descriptor_', 'capture_descriptor_entry')
    routed = 0
    for (index, region) in enumerate(binding['regions']):
        prefix = region['sideband_prefix']
        target = root_name + '.' + '.'.join(re.findall('/([^/:]+):', region['target']))
        parts = target.split('.')
        sv = (p / f'generated.native-region-graft-{index}.sv').read_text()
        for pin in ['ckpt_freeze', 'checkpoint_physical_mask']:
            signal = prefix + pin
            require(re.findall('^  wire ' + re.escape(signal) + ' : UInt<1>$', root_module['body'], re.M) == ['  wire ' + signal + ' : UInt<1>'], 'regional FAME final binding check failed')
            require(signal not in root_module['ports'] and root_module['drivers'][signal] == adapter + '.' + signal, 'regional FAME final binding check failed')
            require(final[definition]['ports'][signal] == ('output', 'UInt<1>'), 'regional FAME final binding check failed')
            require(sv.count('assign ' + signal + ' = capture_clock_mask;') == 1, 'regional FAME final binding check failed')
            require(main_sv.count('.' + signal + '(' + signal + ')') == 1, 'regional FAME final binding check failed')
            for level in range(1, len(parts)):
                parent = final[paths['.'.join(parts[:level])]]
                child = parts[level]
                endpoint = ('' if level == len(parts) - 1 else prefix) + pin
                require(parent['drivers'][child + '.' + endpoint] == signal, 'regional FAME final binding check failed')
                if level > 1:
                    require(parent['ports'][signal] == ('input', 'UInt<1>'), 'regional FAME final binding check failed')
            routed += 1
        region_instance = re.search(r'\bregion' + str(index) + r'\(([\s\S]*?)\);', main_sv)
        require(region_instance and region_instance[1].count('.capture_clock_mask(capture_clock_mask)') == 1,
                'missing region-specific physical mask connection')
    require(root_module['drivers'][adapter + '.capture_clock_mask'] == 'capture_clock_mask', 'regional FAME final binding check failed')
    scope = root_name
    net = 'capture_clock_mask'
    seen = set()
    chain = []
    while True:
        require((scope, net) not in seen, 'cyclic final physical mask route')
        seen.add((scope, net))
        chain.append(scope + '.' + net)
        module = final[paths[scope]]
        if module['kind'] == 'extmodule':
            require(scope == identity['transport'] and net == 'clock_mask' and (paths[scope] == identity['transport_module']), 'regional FAME final binding check failed')
            require(module['ports'][net] == ('output', 'UInt<1>'), 'regional FAME final binding check failed')
            require(re.search(r'^  defname = CheckpointPhysicalCaptureTransport$',
                              module['body'], re.M), 'physical mask reached a different opaque owner')
            break
        if net in module['drivers']:
            net = module['drivers'][net]
            continue
        match = re.fullmatch('([A-Za-z_][A-Za-z0-9_$]*)\\.([A-Za-z_][A-Za-z0-9_$]*)', net)
        require(match and match[1] in module['instances'], 'non-alias or undriven physical mask route')
        scope += '.' + match[1]
        net = match[2]
        require(final[paths[scope]]['ports'][net] == ('output', 'UInt<1>'), 'regional FAME final binding check failed')
    result.update(final_fame_owner_equations_preserved=True, final_regional_freeze_routes=routed, physical_mask_alias_chain=chain)
    digest = sha(p / 'descriptors.json')
    require(identity['descriptor_manifest_sha256'] == digest, 'regional FAME final binding check failed')
    binding_digest = sha(p / 'descriptor-binding.json')
    descriptor = json.loads((p / 'descriptor-binding.json').read_text())
    require(identity['descriptor_binding_sha256'] == binding_digest and
            descriptor['manifest_sha256'] == digest,
            'descriptor binding differs from the actual manifest')
    before = (p / 'connected.fir').read_text()
    after = (p / 'identity-bound.fir').read_text()
    old = 'parameter MANIFEST_SHA256 = ' + str(2 ** 256 - 1)
    new = 'parameter MANIFEST_SHA256 = ' + str(int(digest, 16))
    require(before.count(old) == 1 and after == before.replace(old, new), 'identity binding changed non-identity source')
    oldas = json.loads((p / 'connected.anno.json').read_text())
    newas = json.loads((p / 'identity-bound.anno.json').read_text())
    headers = [a['body'] for a in newas if a['class'] == 'midas.stage.GoldenGateOutputFileAnnotation' and a['fileSuffix'] == '.const.h']
    require(len(headers) == 1, 'regional FAME final binding check failed')
    header = headers[0]
    original_header = [a['body'] for a in oldas if a['class'] ==
                       'midas.stage.GoldenGateOutputFileAnnotation' and a['fileSuffix'] == '.const.h']
    require(len(original_header) == 1, 'missing original registered header')
    allocation = re.findall(r'(?m)^// CHECKPOINT_WIDGET_RESERVATION_BEGIN base=(\d+) stream=(\d+)\n', original_header[0])
    require(allocation == [(str(identity['base']), str(identity['stream']))],
            'final identity differs from the original MMIO/stream allocation')
    expected = []
    for a in oldas:
        if a['class'] == 'midas.stage.GoldenGateOutputFileAnnotation' and a['fileSuffix'] == '.const.h':
            a = dict(a, body=header)
        expected.append(a)
    require(newas == expected, 'changed non-header annotations')
    require('#error Incomplete_checkpoint_hardware_coverage' in header, 'regional FAME final binding check failed')
    require('#define CHECKPOINT_CAPTURE_MANIFEST_SHA256 "' + digest + '"' in header, 'regional FAME final binding check failed')
    require('#define CHECKPOINT_CAPTURE_DESCRIPTOR_BINDING_SHA256 "' + binding_digest + '"' in header,
            'host descriptor-binding identity differs')
    require('#define CHECKPOINT_CAPTURE_ENTRIES ' + str(len(manifest['state'])) + 'U' in header, 'regional FAME final binding check failed')
    ids = re.findall('// descriptor\\[(\\d+)\\] StateID: ([^\\n]+)', header)
    require(ids == [(str(i), row['state_id']) for (i, row) in enumerate(manifest['state'])], 'regional FAME final binding check failed')
    require(len(ids) == len(manifest['state']) and identity['entries'] == len(manifest['state']) and (identity['gates'] == 3), 'regional FAME final binding check failed')
    manifest_bytes = ', '.join('0x' + digest[i:i+2] for i in range(62, -1, -2))
    cpp_rows = ', '.join('{' + ', '.join(str(row[k]) + 'U' for k in
                        ('bank', 'slot', 'width', 'depth')) + '}' for row in manifest['state'])
    cpp = 'checkpoint_capture_manifest_t{{{' + manifest_bytes + '}}, {' + cpp_rows + '}}'
    constructor = ('registry.add_widget(new checkpoint_capture_t(simif, *registry.get_stream_engine(), ' +
                   str(identity['base']) + 'ULL, ' + str(identity['stream']) + 'U,\n  ' + cpp + '));\n')
    code = re.sub(r'/\*[\s\S]*?\*/|//[^\n]*', '', header)
    blocks = re.findall(r'(?m)^#ifdef GET_BRIDGE_CONSTRUCTOR\n([\s\S]*?)^#endif\n', code)
    actual = [block for block in blocks if 'new checkpoint_capture_t(' in block]
    require(actual == [constructor] and code.count('new checkpoint_capture_t(') == 1,
            'host executable descriptor table, digest byte order or allocation differs')
    require(all((identity[k] is False for k in ['complete_fpga_capture', 'deployable_capture_image', 'production_freeze_owners_bound', 'metasim_restore_supported'])), 'regional FAME final binding check failed')
    return dict(result, entries=len(ids), manifest_sha256=digest, descriptor_binding_sha256=binding_digest,
                executable_host_table_checked=True, descriptor_rom_checked=True,
                identity_only=True, complete_fpga_capture=False, deployable_capture_image=False)
