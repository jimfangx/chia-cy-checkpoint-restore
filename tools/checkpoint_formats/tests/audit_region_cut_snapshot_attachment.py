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
    bits = cut['control_state_bits']
    require(b['snapshot_version'] == 1 and b['scope'] ==
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


def audit_negatives(directory, out):
    """Coherently rehash connectivity mutations so a hash check cannot mask them."""
    directory, out = Path(directory), Path(out)
    text = (directory / 'staged.fir').read_text()
    mutations = {
        'clock': ('checkpoint_region_cut_snapshot.clock <= clock',
                  'checkpoint_region_cut_snapshot.clock <= asClock(UInt<1>("h0"))'),
        'reset': ('checkpoint_region_cut_snapshot.reset <= capture_reset',
                  'checkpoint_region_cut_snapshot.reset <= reset'),
        'pending': ('checkpoint_region_cut_snapshot.source_pending <= capture_cut_pending',
                    'checkpoint_region_cut_snapshot.source_pending <= UInt<1>("h0")'),
        'payload': ('checkpoint_region_cut_snapshot.live_control_state <= capture_cut_control_state',
                    'checkpoint_region_cut_snapshot.live_control_state <= UInt<75>("h0")'),
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
