"""Independent identity projection audit; no physical capture admission."""
import json
from pathlib import Path
import re
import shutil

from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.tests.audit_widget_graft import digest, load, parse_modules, sha


def audit(directory):
    from tools.checkpoint_formats.tests.audit_widget_graft import audit as audit_unbound
    directory = Path(directory)
    original = directory / 'unbound'
    require(not (original / 'identity.json').exists(), 'nested identity projection')
    doc = load(directory, 'identity.json')
    regional = doc.get('scope') == 'disjoint_regions_transport_and_host_identity_only'
    if regional:
        from tools.checkpoint_formats.tests.audit_region_widget_graft import audit as audit_unbound
    base_audit = audit_unbound(original)
    require(doc['identity_version'] == 1 and
            doc['scope'] == ('disjoint_regions_transport_and_host_identity_only' if regional else
                             'selected_readout_transport_and_host_identity_only') and
            doc['descriptor_identity_bound'] is True and
            doc['external_transport_state_owner'] == 'unsupported_no_state_adapter' and
            all(doc[k] is False for k in ('production_annotations_translated',
                    'production_freeze_owners_bound', 'complete_fpga_capture',
                    'deployable_capture_image', 'metasim_restore_supported')),
            'identity projection falsely admits owner or image')
    require(not (original/'identity').exists(), 'nested regional identity output')
    originals = {p.name for p in original.iterdir() if p.is_file()}
    require({p.name for p in directory.iterdir() if p.is_file()} == originals | {'identity.json'},
            'identity projection missing or adding files')
    changed = {'connected.fir', 'connected.sv', 'connected-annotations.json', 'reserved.h'}
    if regional:
        changed.add('connected-xdc-emission.json')
    require(all(sha(directory / n) == sha(original / n) for n in originals - changed),
            'identity projection changed unrelated input')
    for key, parent, filename in (
        ('connection_sha256', original, 'connection.json'),
        ('unbound_sha256', original, 'connected.fir'),
        ('bound_sha256', directory, 'connected.fir'),
        ('header_before_sha256', original, 'reserved.h'),
        ('header_after_sha256', directory, 'reserved.h')):
        require(doc[key] == sha(parent / filename), 'stale identity input ' + key)
    descriptors = [directory/'manifest.json'] if regional else list(directory.glob('*.native-inplace-graft-descriptors.json'))
    require(len(descriptors) == 1, 'ambiguous identity manifest')
    manifest = json.loads(descriptors[0].read_text())
    require(doc['descriptor_manifest_sha256'] == sha(descriptors[0]), 'wrong global manifest identity')
    binding = load(directory, 'descriptor-binding.json')
    require(doc['descriptor_binding_sha256'] == sha(directory / 'descriptor-binding.json') and
            load(directory, 'descriptors.json') == manifest and
            binding['manifest_sha256'] == doc['descriptor_manifest_sha256'],
            'wrong descriptor binding identity')
    old_text = (original / 'connected.fir').read_text()
    old = parse_modules(old_text)
    new_text = (directory / 'connected.fir').read_text()
    new = parse_modules(new_text)
    peer = load(original, 'peer-routing.json')
    require(doc['transport'] == peer['transport'], 'wrong identity transport instance')
    # Derive the actual definition from the concrete instance path.
    module = re.search(r'^circuit (\w+) :', old_text, re.M)[1]
    hops = doc['transport'].split('.')
    require(hops[0] == module, 'foreign transport root')
    for instance in hops[1:]:
        module = old[module]['instances'][instance]
    require(module == doc['transport_module'] and old.keys() == new.keys(), 'wrong transport definition')
    old_param = f'parameter MANIFEST_SHA256 = {2**256-1}'
    new_param = 'parameter MANIFEST_SHA256 = ' + str(int(doc['descriptor_manifest_sha256'], 16))
    require(old[module]['body'].count(old_param) == 1 and
            new[module]['body'] == old[module]['body'].replace(old_param, new_param) and
            all(new[n] == old[n] for n in old if n != module),
            'identity binding changed non-identity RTL')
    require(doc['transport_before_sha256'] == digest(old[module]['body']) and
            doc['transport_after_sha256'] == digest(new[module]['body']), 'wrong transport definition hashes')
    # The actual emitted executable RTL must differ at this parameter only.
    old_sv = (original / 'connected.sv').read_text()
    old_sv_param = f'.MANIFEST_SHA256(256\'d{2**256-1})'
    value = int(doc['descriptor_manifest_sha256'], 16)
    new_sv_param = f'.MANIFEST_SHA256({value.bit_length()}\'d{value})'
    require(old_sv.count(old_sv_param) == 1 and
            (directory / 'connected.sv').read_text() == old_sv.replace(old_sv_param, new_sv_param),
            'emitted transport identity does not match bound FIRRTL')
    annotations = load(original, 'connected-annotations.json')
    expected = []
    for a in annotations:
        if a['class'] == 'midas.stage.GoldenGateOutputFileAnnotation' and a['fileSuffix'] == '.const.h':
            a = dict(a, body=(directory / 'reserved.h').read_text())
        expected.append(a)
    require(load(directory, 'connected-annotations.json') == expected,
            'identity projection changed non-header annotation or source')
    header = (original / 'reserved.h').read_text()
    marker = re.compile(r'(?m)^// CHECKPOINT_WIDGET_RESERVATION_BEGIN base=(\d+) stream=(\d+)\n'
                        r'#error Unbound_checkpoint_widget_reservation\n// CHECKPOINT_WIDGET_RESERVATION_END\n')
    matches = list(marker.finditer(header))
    require(len(matches) == 1, 'one registered header reservation required')
    match = matches[0]
    base, stream = map(int, match.groups())
    execution = next(a for a in annotations if a['class'] ==
                     'midas.checkpoint.NativeCheckpointWidgetExecutionAnnotation')
    rows = manifest['state']
    require(doc['base'] == base and doc['stream'] == stream and
            doc['entries'] == execution['entries'] == len(rows) and
            doc['gates'] == execution['gates'] == (sum(r['domain'] == 'physical_ce' for r in rows) if regional else manifest['physical_clock_gates']) and
            doc['owners'] == execution['owners'] and doc['queue_depth'] == execution['queueDepth'],
            'identity allocation or descriptor geometry mismatch')
    prefix = 'CHECKPOINT_CAPTURE'
    require(doc['header_prefix'] == prefix, 'wrong header namespace')
    registers = [('COMMAND', 0), ('STATUS', 4), ('ERROR', 8), ('CUT_LO', 16), ('CUT_HI', 20),
        ('WORDS_LO', 24), ('WORDS_HI', 28), ('ENTRY_COUNT', 32), ('CRC32C', 36)]
    registers += [(f'MANIFEST_{i}', 64+4*i) for i in range(8)]
    registers += [('STREAM_INVALID', 96), ('STREAM_DRAIN_ACK', 100), ('PRODUCED_FRAMES_LO', 104),
        ('PRODUCED_FRAMES_HI', 108), ('HOST_DRAINED_FRAMES_LO', 112), ('HOST_DRAINED_FRAMES_HI', 116)]
    registers += [('SHADOW_COMMAND', 120), ('SHADOW_INDEX', 124), ('SHADOW_WORD_LO', 128),
        ('SHADOW_WORD_HI', 132), ('SHADOW_STATUS', 136), ('SHADOW_CUT_LO', 140),
        ('SHADOW_CUT_HI', 144), ('SHADOW_WORDS', 148),
        ('SHADOW_LAYOUT_VERSION', 152), ('SHADOW_BITS', 156)]
    replacement = '#error Incomplete_checkpoint_hardware_coverage\n'
    replacement += '// Global checkpoint transport; no complete CPU/host ownership claim.\n'
    def define(name, value):
        return f'#define {prefix}_{name} {value}\n'
    replacement += define('BASE', f'{base}ULL')
    for name, offset in registers:
        replacement += define(name+'_OFFSET', f'{offset}U') + define(name+'_ADDR', f'{base+offset}ULL')
    for name, value in [('TO_HOST_STREAM_IDX', stream), ('TO_HOST_QUEUE_DEPTH', doc['queue_depth']),
            ('ENTRIES', len(rows)), ('OWNERS', len(doc['owners'])), ('PHYSICAL_CLOCK_GATES', doc['gates']),
            ('EXTERNAL_CLOCK_NETWORK', 1)]:
        replacement += define(name, f'{value}U')
    replacement += define('MANIFEST_SHA256', '"'+doc['descriptor_manifest_sha256']+'"')
    replacement += define('DESCRIPTOR_BINDING_SHA256', '"'+doc['descriptor_binding_sha256']+'"')
    replacement += define('INTERNAL_DESCRIPTOR_ROM', '1U')
    for i, row in enumerate(rows):
        replacement += f'// descriptor[{i}] StateID: {row["state_id"]}\n'
    for name in ('CheckpointCaptureTransport.sv', 'CheckpointCaptureCut.sv',
                 'CheckpointPhysicalCaptureTransport.sv', 'CheckpointPhysicalClockCut.sv'):
        replacement += f'// {name} SHA256: {sha(directory/name)}\n'
    for name, value in [('FRAME_BYTES', 64), ('TRANSPORT_VERSION', 1), ('ABORT_REQUIRES_HOST_DRAIN', 1)]:
        replacement += define(name, f'{value}U')
    control_bits = 481 + doc['gates']
    for name, value in [('SHADOW_LAYOUT_VERSION', 2), ('SHADOW_CONTROL_BITS', control_bits),
                        ('SHADOW_BITS', control_bits + 758), ('SHADOW_ADAPTER_BITS', 530), ('SHADOW_RESTORE_SUPPORTED', 0)]:
        replacement += define(name, f'{value}U')
    offset = control_bits
    for name, width in [('invalid', 1), ('producedFrames', 64), ('producedSnapshot', 64),
                        ('hostDrainedFrames', 64), ('counterOverflow', 1),
                        ('localValid', 1), ('localData', 32), ('localError', 1)]:
        replacement += f'// shadow local {name}: bit {offset}, width {width}\n'
        offset += width
    address = [('addr',64),('len',8),('size',3),('burst',2),('lock',1),('cache',4),
               ('prot',3),('qos',4),('region',4),('id',64),('user',1)]
    adapter = [(prefix+'_'+name,width) for prefix, fields in
               [('aw',address),('wd',[('data',32),('last',1),('id',64),('strb',4),('user',1)]),
                ('ar',address)] for name,width in fields]
    adapter += [(name,1) for name in ('haveAW','haveW','haveAR','badW','busy','writing','responseValid','responseError')]
    adapter += [('responseData',32),('responseId',64),('errorReadRemaining',8)]
    for name,width in adapter:
        replacement += f'// shadow adapter {name}: bit {offset}, width {width}\n'
        offset += width
    for i, name in enumerate(doc['owners']):
        replacement += f'// owner[{i}]: {name}\n'
    manifest_bytes = ', '.join('0x'+doc['descriptor_manifest_sha256'][i:i+2] for i in range(62, -1, -2))
    cpp_rows = ', '.join('{'+', '.join(f'{r[n]}U' for n in ('bank', 'slot', 'width', 'depth'))+'}' for r in rows)
    cpp = 'checkpoint_capture_manifest_t{{{'+manifest_bytes+'}}, {'+cpp_rows+'}}'
    replacement += '#ifdef GET_INCLUDES\n#include "bridges/checkpoint_capture.h"\n#endif\n'
    replacement += '#ifdef GET_BRIDGE_CONSTRUCTOR\n'
    replacement += f'registry.add_widget(new checkpoint_capture_t(simif, *registry.get_stream_engine(), {base}ULL, {stream}U,\n'
    replacement += f'  {cpp}));\n#endif\n'
    require((directory/'reserved.h').read_text() == header[:match.start()] + replacement + header[match.end():],
            'host header/constructor identity or incomplete-owner guard mismatch')
    return dict(base_audit, descriptor_identity_bound=True, manifest_sha256=doc['descriptor_manifest_sha256'],
                identity_only=True, host_stream=stream, host_base=base)


def corruptions(directory, out):
    directory, out = Path(directory), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rejected = []
    for name in ('image-admission', 'owner-admission', 'header-digest', 'host-selector',
                 'host-byte-order', 'host-stream', 'host-mmio', 'owner-guard',
                 'transport-digest', 'emitted-digest', 'descriptor-source', 'foreign-annotation',
                 'shadow-width', 'shadow-offset', 'shadow-restore', 'shadow-layout'):
        case = out / name
        shutil.copytree(directory, case)
        doc = load(case, 'identity.json')
        if name == 'image-admission':
            doc['deployable_capture_image'] = True
        elif name == 'owner-admission':
            doc['production_freeze_owners_bound'] = True
        elif name == 'transport-digest':
            text = (case/'connected.fir').read_text()
            value = str(int(doc['descriptor_manifest_sha256'], 16))
            text = text.replace('parameter MANIFEST_SHA256 = '+value,
                                'parameter MANIFEST_SHA256 = '+str(int(value)^1))
            (case/'connected.fir').write_text(text)
            module = parse_modules(text)[doc['transport_module']]
            doc['transport_after_sha256'] = digest(module['body'])
        elif name == 'emitted-digest':
            text = (case/'connected.sv').read_text()
            value = str(int(doc['descriptor_manifest_sha256'], 16))
            before = f".MANIFEST_SHA256({int(value).bit_length()}'d{value})"
            after = f".MANIFEST_SHA256({(int(value)^1).bit_length()}'d{int(value)^1})"
            (case/'connected.sv').write_text(text.replace(before, after))
        elif name == 'descriptor-source':
            path = case/'manifest.json' if (case/'manifest.json').is_file() else next(case.glob('*.native-inplace-graft-descriptors.json'))
            value = json.loads(path.read_text());value['state'][0]['slot'] += 1
            path.write_text(json.dumps(value))
            doc['descriptor_manifest_sha256'] = sha(path)
        elif name == 'foreign-annotation':
            annotations = load(case, 'connected-annotations.json')
            annotations.append({'class': 'firrtl.transforms.DontTouchAnnotation', 'target': '~foreign|foreign>state'})
            (case/'connected-annotations.json').write_text(json.dumps(annotations))
        else:
            text = (case/'reserved.h').read_text()
            if name == 'header-digest':
                text = text.replace('"'+doc['descriptor_manifest_sha256']+'"', '"'+'0'*64+'"')
            elif name == 'host-selector':
                text = text.replace('U, 0U, 64U, 1U}', 'U, 9U, 64U, 1U}', 1)
            elif name == 'host-byte-order':
                chunks = re.findall(r'0x[0-9a-f]{2}', text)
                require(len(chunks) == 32, 'missing C++ digest mutation site')
                text = text.replace(', '.join(chunks), ', '.join(reversed(chunks)), 1)
            elif name == 'host-stream':
                text = text.replace('get_stream_engine(), 0ULL, 1U,', 'get_stream_engine(), 0ULL, 0U,')
            elif name == 'host-mmio':
                text = text.replace('#define CHECKPOINT_CAPTURE_MANIFEST_0_ADDR 64ULL',
                                    '#define CHECKPOINT_CAPTURE_MANIFEST_0_ADDR 68ULL')
            elif name == 'shadow-width':
                text = re.sub(r'(?m)^(#define CHECKPOINT_CAPTURE_SHADOW_BITS )\d+U$', r'\g<1>640U', text)
            elif name == 'shadow-offset':
                text = text.replace('CHECKPOINT_CAPTURE_SHADOW_WORD_HI_OFFSET 132U',
                                    'CHECKPOINT_CAPTURE_SHADOW_WORD_HI_OFFSET 128U')
            elif name == 'shadow-restore':
                text = text.replace('CHECKPOINT_CAPTURE_SHADOW_RESTORE_SUPPORTED 0U',
                                    'CHECKPOINT_CAPTURE_SHADOW_RESTORE_SUPPORTED 1U')
            elif name == 'shadow-layout':
                text = text.replace('CHECKPOINT_CAPTURE_SHADOW_LAYOUT_VERSION 2U',
                                    'CHECKPOINT_CAPTURE_SHADOW_LAYOUT_VERSION 1U')
            else:
                text = text.replace('#error Incomplete_checkpoint_hardware_coverage', '#define INVENTED_ADMISSION 1')
            require(text != (case/'reserved.h').read_text(), 'missing actual header mutation '+name)
            (case/'reserved.h').write_text(text)
            # Rehash the enclosing annotation/header receipt too: checks must
            # reconstruct the ABI, not just notice a stale checksum.
            annotations = load(case, 'connected-annotations.json')
            for a in annotations:
                if a['class'] == 'midas.stage.GoldenGateOutputFileAnnotation' and a['fileSuffix'] == '.const.h':
                    a['body'] = text
            (case/'connected-annotations.json').write_text(json.dumps(annotations))
        doc['bound_sha256'] = sha(case/'connected.fir')
        doc['header_after_sha256'] = sha(case/'reserved.h')
        (case/'identity.json').write_text(json.dumps(doc))
        try:
            audit(case)
        except FormatError as error:
            rejected.append(dict(case=name, error=str(error)))
        else:
            raise AssertionError('accepted coherently rehashed identity corruption '+name)
    return rejected
