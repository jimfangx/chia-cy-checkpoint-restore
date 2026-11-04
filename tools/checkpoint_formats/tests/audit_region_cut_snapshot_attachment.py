"""Independent FIRRTL audit of compiler-installed regional control staging."""
import hashlib
import json
from pathlib import Path
import re
import shutil

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha


def audit(directory):
    d = Path(directory)
    b = json.loads((d / 'snapshot-binding.json').read_text())
    cut = json.loads((d / 'cut-binding.json').read_text())
    before = parse_modules((d / 'attached.fir').read_text())
    after = parse_modules((d / 'staged.fir').read_text())
    root = re.search(r'^circuit (\w+) :', (d / 'staged.fir').read_text(), re.M)[1]
    inst, definition = 'checkpoint_region_cut_snapshot', 'CheckpointRegionCutSnapshot'
    control_bits = cut['control_state_bits']
    router = b.get('router_state_observation')
    router_bits = router['bits'] if router else 0
    bits = control_bits + router_bits
    require((b['snapshot_version'] == 2) == bool(router), 'snapshot router ABI mismatch')
    if router:
        audit_router_observation(d, router)
        require(b['controller_state_bits'] == control_bits and b['router_state_offset'] == control_bits and
                b['router_state_bits'] == router_bits and b['router_observation_atomically_staged'] is True and
                b['payload_layout_lsb0'] == ['cut_control', 'router_state'], 'incomplete same-edge router layout')
    require(b['snapshot_version'] in (1, 2) and b['scope'] ==
            'selected_native_regions_atomic_cut_control_observation_only', 'changed snapshot ABI')
    require(b['cut_binding_sha256'] == sha(d / 'cut-binding.json') and
            b['attached_sha256'] == sha(d / 'staged.fir'), 'changed snapshot source binding')
    require(b['adapter'] == root + '.' + inst and b['raw_clock'] == cut['raw_clock'] and
            b['control_state_bits'] == bits and b['staging_owner_bits'] == bits + 71,
            'changed source clock or complete owner widths')
    require(b['controller_observation_atomically_staged'] is True, 'missing atomic observation')
    for key in ('readout_router_state_atomically_owned', 'staging_owner_restore_supported',
                'complete_fpga_capture', 'deployable_capture_image', 'metasim_restore_supported'):
        require(b[key] is False, 'unsupported complete owner admission ' + key)
    require(set(after) == set(before) | {definition}, 'duplicate or missing original definitions')
    for name in before:
        if name != root:
            require(before[name] == after[name], 'changed original cut/execution/readout definition ' + name)
    old, new = before[root], after[root]
    require(new['instances'] == dict(old['instances'], **{inst: definition}), 'changed original execution')
    require(new['consumers'] == old['consumers'], 'new/masked original state owner')
    expected_ports = dict(old['ports'])
    for direction, shape in [('input', {'request': 1, 'release': 1, 'word_address': 32}),
            ('output', {'ready': 1, 'valid': 1, 'failed': 1, 'word_data': 64, 'cut_cycle': 64,
                        'word_error': 1, 'error': 6, 'captured_control_state': bits, 'staging_control_state': bits + 71})]:
        expected_ports.update({'capture_snapshot_' + n: (direction, f'UInt<{w}>') for n, w in shape.items()})
    require(new['ports'] == expected_ports, 'changed snapshot or original port ABI')
    renamed = {'capture_' + n: 'capture_snapshot_source_' + n for n in
               ('request_valid', 'request_ready', 'response_valid', 'response_ready', 'response_data', 'response_error')}
    renamed['capture_cut_freeze_request'] = 'capture_snapshot_cut_freeze_request'
    def rename(text):
        return re.sub(r'(?<![\w.])(' + '|'.join(renamed) + r')\b', lambda m: renamed[m[0]], text)
    expected = {rename(n): rename(v) if v is not None else None for n, v in old['drivers'].items()}
    ins = {'clock': cut['raw_clock'], 'reset': 'capture_reset',
           'host_freeze_request': 'capture_cut_freeze_request', 'snapshot_request': 'capture_snapshot_request',
           'snapshot_release': 'capture_snapshot_release', 'physical_read_enable': 'capture_read_enable',
           'physical_failed': 'capture_cut_failed', 'source_pending': 'capture_cut_pending',
           'target_cycle': 'capture_cut_target_cycle', 'live_control_state': 'capture_cut_control_state',
           'request_valid': 'capture_request_valid', 'response_ready': 'capture_response_ready',
           'word_address': 'capture_snapshot_word_address'}
    for n in ('request_ready', 'response_valid', 'response_data', 'response_error'):
        ins['source_' + n] = 'capture_snapshot_source_' + n
    outs = {'cut_freeze_request': 'capture_snapshot_cut_freeze_request',
            'snapshot_ready': 'capture_snapshot_ready', 'snapshot_valid': 'capture_snapshot_valid',
            'snapshot_failed': 'capture_snapshot_failed', 'snapshot_error': 'capture_snapshot_error'}
    for n in ('word_data', 'cut_cycle', 'word_error', 'captured_control_state', 'staging_control_state'):
        outs[n] = 'capture_snapshot_' + n
    for n in ('request_ready', 'response_valid', 'response_data', 'response_error'):
        outs[n] = 'capture_' + n
    for n in ('request_valid', 'response_ready'):
        outs['source_' + n] = 'capture_snapshot_source_' + n
    if router:
        ins['live_control_state'] = 'cat(capture_router_state, capture_cut_control_state)'
    expected.update({inst + '.' + n: v for n, v in ins.items()})
    expected.update({v: inst + '.' + n for n, v in outs.items()})
    require(new['drivers'] == expected, 'changed staging/permission/pending route')
    adapter = after[definition]
    require(hashlib.sha256(adapter['body'].encode()).hexdigest() == b['adapter_definition_sha256'],
            'changed adapter declaration binding')
    pins = {'clock': ('input', 'Clock')}
    widths = {'target_cycle': 64, 'live_control_state': bits, 'source_response_data': 64, 'word_address': 32,
              'response_data': 64, 'word_data': 64, 'cut_cycle': 64, 'snapshot_error': 6,
              'captured_control_state': bits, 'staging_control_state': bits + 71}
    pins.update({n: ('input', f'UInt<{widths.get(n, 1)}>') for n in ins if n != 'clock'})
    pins.update({n: ('output', f'UInt<{widths.get(n, 1)}>') for n in outs})
    require(adapter['ports'] == pins, 'changed complete adapter port ABI')
    require(re.search(r'\bparameter CONTROL_BITS = ' + str(bits) + r'\b', adapter['body']),
            'changed control vector parameter')
    require(set(b['resource_hashes']) == {'.native-region-cut-snapshot.sv', '.native-region-cut-staging.sv'},
            'incomplete snapshot resources')
    for suffix, h in b['resource_hashes'].items():
        require(sha(d / ('FireSim-generated' + suffix)) == h, 'changed snapshot resource ' + suffix)
    return dict(status='pass', original_definitions=len(before), original_state_owners=len(old['consumers']),
                adapter_routes=len(ins) + len(outs), control_bits=bits, staging_bits=bits + 71,
                complete_fpga_capture=False)


def audit_router_observation(d, router):
    """Derive every bit from actual routing geometry and emitted instance pins."""
    d = Path(d)
    graft = json.loads((d / 'graft-binding.json').read_text())
    routing = json.loads((d / 'routing.json').read_text())['regions']
    regions = json.loads((d / 'binding.json').read_text())['regions']
    count = len(routing)
    shared = max(1, (count - 1).bit_length()) + 2
    bits = shared + 2 * len(regions)
    require(graft.get('router_state_observation') == router, 'router observation differs from exact graft')
    require(router['version'] == 1 and router['port'] == 'capture_router_state' and router['bits'] == bits and
            router['extra_storage_bits'] == 0 and router['raw_clock'] == graft['raw_clock'] and
            router['atomic_snapshot_supported'] is False and router['restore_supported'] is False and
            router['sampling_contract'] == 'same_raw_preedge_as_cut_control_before_first_bank_handshake',
            'changed router observation scope/shape')
    instance = graft['adapter_instance']
    owners = [dict(instance=instance+'.router', definition='CheckpointRegionStateRouter', offset=0, bits=shared,
                   fields_lsb0=['pending', 'invalid', 'owner'])]
    owners += [dict(instance=instance+f'.region{i}.router', definition='CheckpointPhysicalStateRouter',
                    offset=shared+2*i, bits=2, fields_lsb0=['pending', 'selected_ce']) for i in range(len(regions))]
    require(router['owners'] == owners, 'lost or reordered router owner including inactive bits')
    top = (d / 'FireSim-generated.native-region-graft.sv').read_text()
    require(top.count(f'.capture_state(capture_router_state[0 +: {shared}])') == 1,
            'shared router observation pin is unbound or aliased')
    require(re.search(r'CheckpointRegionStateRouter #\([^;]+?\) router\(\s*\.capture_state', top, re.S),
            'shared observation attached to a different execution')
    for i in range(len(regions)):
        endpoint = re.search(r'\bregion' + str(i) + r'\((.*?)\);', top, re.S)
        require(endpoint and f'.capture_router_state(capture_router_state[{shared+2*i} +: 2])' in endpoint[1],
                'physical observation attached to a different regional instance')
        require(top.count(f'.capture_router_state(capture_router_state[{shared+2*i} +: 2])') == 1,
                'physical router observation slice is unbound or aliased')
        child = (d / f'FireSim-generated.native-region-graft-{i}.sv').read_text()
        require(child.count('.capture_state(capture_router_state)') == 1 and
                '.restore_hold(1\'b0),.restore_load(1\'b0),.restore_state(2\'b0),.restore_error()' in child,
                'physical observation or disabled restore contract changed')
        require(re.search(r'CheckpointPhysicalStateRouter #\([^;]+?\) router\(\s*\.capture_state', child, re.S),
                'physical observation attached to a different execution')
    return dict(status='pass', router_bits=bits, routers=len(owners), extra_storage_bits=0)


def audit_negatives(directory, out):
    """Coherently rehash connectivity mutations so a hash check cannot mask them."""
    directory, out = Path(directory), Path(out)
    text = (directory / 'staged.fir').read_text()
    binding = json.loads((directory / 'snapshot-binding.json').read_text())
    bits = binding['control_state_bits']
    payload = ('cat(capture_router_state, capture_cut_control_state)' if binding.get('router_state_observation')
               else 'capture_cut_control_state')
    mutations = {
        'clock': ('checkpoint_region_cut_snapshot.clock <= clock',
                  'checkpoint_region_cut_snapshot.clock <= asClock(UInt<1>("h0"))'),
        'reset': ('checkpoint_region_cut_snapshot.reset <= capture_reset',
                  'checkpoint_region_cut_snapshot.reset <= reset'),
        'pending': ('checkpoint_region_cut_snapshot.source_pending <= capture_cut_pending',
                    'checkpoint_region_cut_snapshot.source_pending <= UInt<1>("h0")'),
        'payload': ('checkpoint_region_cut_snapshot.live_control_state <= ' + payload,
                    f'checkpoint_region_cut_snapshot.live_control_state <= UInt<{bits}>("h0")'),
        'request-bypass': ('capture_request_ready <= checkpoint_region_cut_snapshot.request_ready',
                           'capture_request_ready <= capture_snapshot_source_request_ready'),
        'response-bypass': ('capture_response_valid <= checkpoint_region_cut_snapshot.response_valid',
                            'capture_response_valid <= capture_snapshot_source_response_valid'),
        'freeze-bypass': ('or(capture_snapshot_cut_freeze_request, capture_cut_accepted_pending)',
                          'or(capture_cut_freeze_request, capture_cut_accepted_pending)'),
    }
    rejected = []
    for name in [*mutations, 'admission', 'resource', 'missing-resource']:
        work = out / name
        shutil.copytree(directory, work)
        b = json.loads((work / 'snapshot-binding.json').read_text())
        if name in mutations:
            before, after = mutations[name]
            require(text.count(before) == 1, 'ambiguous independent attachment mutation ' + name)
            (work / 'staged.fir').write_text(text.replace(before, after))
            b['attached_sha256'] = sha(work / 'staged.fir')
        elif name == 'admission':
            b['complete_fpga_capture'] = True
        elif name == 'resource':
            path = work / 'FireSim-generated.native-region-cut-snapshot.sv'
            path.write_text(path.read_text() + '\n// changed source\n')
        else:
            b['resource_hashes'].pop('.native-region-cut-staging.sv')
        (work / 'snapshot-binding.json').write_text(json.dumps(b, indent=2) + '\n')
        try:
            audit(work)
        except FormatError:
            rejected.append(name)
        else:
            raise FormatError('compiler attachment corruption escaped: ' + name)
    return rejected


def audit_router_negatives(directory, out):
    """Coherently hash altered observations; exact route/geometry must reject."""
    directory, out = Path(directory), Path(out)
    mutations = {
        'shared-open': ('.native-region-graft.sv', '.capture_state(capture_router_state[0 +: 3])', '.capture_state()'),
        'physical-open': ('.native-region-graft-0.sv', '.capture_state(capture_router_state)', '.capture_state()'),
        'physical-slice-alias': ('.native-region-graft.sv',
            '.capture_router_state(capture_router_state[3 +: 2])', '.capture_router_state(capture_router_state[5 +: 2])'),
        'physical-instance-swap': ('.native-region-graft.sv', ' region0(', ' region_swapped('),
        'restore-enable': ('.native-region-graft-0.sv', ".restore_hold(1'b0)", ".restore_hold(1'b1)"),
    }
    rejected = []
    for name in [*mutations, 'owner-order', 'missing-inactive-bit', 'offset', 'staged-layout', 'staged-offset']:
        work = out / name
        shutil.copytree(directory, work)
        b = json.loads((work / 'snapshot-binding.json').read_text())
        g = json.loads((work / 'graft-binding.json').read_text())
        router = g['router_state_observation']
        if name in mutations:
            suffix, before, after = mutations[name]
            path = work / ('FireSim-generated' + suffix)
            text = path.read_text()
            require(text.count(before) == 1, 'ambiguous router corruption ' + name)
            path.write_text(text.replace(before, after))
            g['files'][suffix] = sha(path)
        elif name == 'owner-order':
            router['owners'][1:] = router['owners'][1:][::-1]
        elif name == 'missing-inactive-bit':
            router['owners'][1]['fields_lsb0'] = ['pending']
        elif name == 'offset':
            router['owners'][2]['offset'] = 3
        elif name == 'staged-layout':
            b['payload_layout_lsb0'].reverse()
        else:
            b['router_state_offset'] -= 1
        b['router_state_observation'] = router
        for path in ('graft-binding.json', 'FireSim-generated.native-region-graft.json'):
            (work / path).write_text(json.dumps(g, indent=2)+'\n')
        cut = json.loads((work / 'cut-binding.json').read_text())
        cut['graft_binding_sha256'] = sha(work / 'graft-binding.json')
        (work / 'cut-binding.json').write_text(json.dumps(cut, indent=2)+'\n')
        b['cut_binding_sha256'] = sha(work / 'cut-binding.json')
        (work / 'snapshot-binding.json').write_text(json.dumps(b, indent=2)+'\n')
        try:
            audit(work)
        except FormatError as error:
            rejected.append(dict(name=name, error=str(error)))
        else:
            raise FormatError('coherent router corruption escaped: ' + name)
    return rejected
