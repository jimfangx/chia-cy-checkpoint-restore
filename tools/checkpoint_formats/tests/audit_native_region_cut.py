"""Independent connectivity/ownership audit for an attached selective clock cut.

This checks original circuitry and interface routes separately from the compiler's
regeneration check. It supplies no FPGA or complete simulator acceptance.
"""
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha

ROOT = Path(__file__).resolve().parents[3]


def audit_cut(directory):
    d = Path(directory)
    read = lambda n: json.loads((d / n).read_text())
    binding, regions, manifest = map(read, ('cut-binding.json', 'binding.json', 'manifest.json'))
    before = parse_modules((d / 'grafted.fir').read_text())
    after = parse_modules((d / 'attached.fir').read_text())
    root = re.search(r'^circuit (\w+) :', (d / 'grafted.fir').read_text(), re.M)[1]
    collector = 'checkpoint_region_clock_cut'
    definition = 'CheckpointPhysicalClockCut'
    gates = sum(row['count'] for row in manifest['physical_ce_order'])
    require(binding['cut_version'] == 1 and binding['scope'] ==
            'selected_native_regions_common_low_phase_capture_only', 'changed selective cut ABI')
    for key, name in [('regions_binding_sha256', 'binding.json'),
                      ('graft_binding_sha256', 'graft-binding.json'), ('attached_sha256', 'attached.fir')]:
        require(binding[key] == sha(d / name), 'changed cut source binding ' + key)
    require(binding['controller'] == root + '.' + collector and binding['raw_clock'] == regions['raw_clock'] and
            binding['physical_clock_gates'] == gates and binding['physical_ce_order'] == manifest['physical_ce_order'],
            'changed raw clock, physical CE order or gate count')
    for key in ('uncovered_functional_state', 'uncovered_physical_gates'):
        require(binding[key] == manifest[key], 'hidden uncovered owner ' + key)
    for key in ('target_time_authority_proven', 'external_writer_owners_bound', 'reset_writer_owners_bound',
                'production_freeze_owners_bound', 'controller_state_atomically_owned', 'complete_fpga_capture',
                'deployable_capture_image', 'metasim_restore_supported'):
        require(binding[key] is False, 'changed incomplete admission ' + key)
    owners = binding['owners']
    require(owners and len(owners) == len(set(owners)), 'missing/aliased external owners')
    require(set(after) == set(before) | {definition}, 'unexpected circuit definition')
    for name in before:
        if name != root:
            require(before[name] == after[name], 'changed original region/readout definition ' + name)
    old, new = before[root], after[root]
    require(new['instances'] == dict(old['instances'], **{collector: definition}), 'duplicate/changed original execution')
    owned = {'capture_clock_mask': 1, 'capture_read_enable': 1, 'capture_captured_ce': gates}
    expected_ports = dict(old['ports'])
    for name, width in owned.items():
        require(expected_ports[name] == ('input', f'UInt<{width}>'), 'changed original collector input')
        expected_ports[name] = ('output', f'UInt<{width}>')
    for name, direction, width in [('freeze_request', 'input', 1), ('target_cycle', 'input', 64),
            ('owner_present', 'input', len(owners)), ('stopped', 'output', 1), ('failed', 'output', 1),
            ('cycle', 'output', 64), ('error', 'output', 3), ('control_state', 'output', gates + 71),
            ('pending', 'output', 1)]:
        expected_ports['capture_cut_' + name] = (direction, f'UInt<{width}>')
    require(new['ports'] == expected_ports, 'changed original or attached interface')
    raw_names = {f'capture_{name}': f'capture_cut_raw_{name}' for name in
                 ('request_valid', 'request_ready', 'response_valid', 'response_ready', 'response_data', 'response_error')}
    def rename(text):
        return re.sub(r'(?<![\w.])(' + '|'.join(raw_names) + r')\b', lambda m: raw_names[m[0]], text)
    for name, value in old['drivers'].items():
        require(new['drivers'].get(rename(name)) == (rename(value) if value is not None else None),
                'changed original connectivity ' + name)
    require(new['consumers'] == old['consumers'] + [('capture_cut_accepted_pending', 'register', regions['raw_clock'])] or
            new['consumers'] == [('capture_cut_accepted_pending', 'register', regions['raw_clock'])] + old['consumers'],
            'new pending owner missing or original state/clock changed')
    drivers = new['drivers']
    expected = {
        collector + '.clock': regions['raw_clock'], collector + '.reset': 'capture_reset',
        collector + '.freeze_request': 'or(capture_cut_freeze_request, capture_cut_accepted_pending)',
        collector + '.ce': 'capture_logical_ce', collector + '.target_cycle': 'capture_cut_target_cycle',
        collector + '.owner_present': 'capture_cut_owner_present',
        'capture_cut_pending': 'capture_cut_accepted_pending',
        'capture_cut_control_state': 'cat(capture_cut_accepted_pending, ' + collector + '.control_state)',
        'capture_cut_raw_request_valid': 'and(and(capture_request_valid, capture_read_enable), capture_cut_freeze_request)',
        'capture_request_ready': 'and(and(capture_cut_raw_request_ready, capture_read_enable), capture_cut_freeze_request)',
        'capture_response_valid': 'and(capture_cut_raw_response_valid, capture_read_enable)',
        'capture_cut_raw_response_ready': 'and(capture_response_ready, capture_read_enable)',
        'capture_response_data': 'mux(capture_read_enable, capture_cut_raw_response_data, UInt<64>("h0"))',
        'capture_response_error': 'and(capture_cut_raw_response_error, capture_read_enable)',
        'capture_cut_accepted_pending': 'mux(capture_reset, UInt<1>("h0"), mux(and(and(capture_request_valid, capture_cut_raw_request_ready), '
            'and(capture_read_enable, capture_cut_freeze_request)), UInt<1>("h1"), '
            'mux(and(and(capture_cut_raw_response_valid, capture_response_ready), capture_read_enable), '
            'UInt<1>("h0"), capture_cut_accepted_pending)))',
    }
    for name in ('restore_hold', 'restore_load_pos', 'restore_load_neg'):
        expected[collector + '.' + name] = 'UInt<1>("h0")'
    expected[collector + '.restore_state'] = f'UInt<{gates + 70}>("h0")'
    expected.update({name: collector + '.' + name.removeprefix('capture_') for name in owned})
    expected.update({'capture_cut_' + name: collector + '.' + output for name, output in
                     [('stopped', 'stopped'), ('failed', 'failed'), ('cycle', 'cut_cycle'), ('error', 'error')]})
    for name, value in expected.items():
        require(drivers.get(name) == value, 'changed cut/permission/pending route ' + name)
    controller = after[definition]
    require(hashlib.sha256(controller['body'].encode()).hexdigest() == binding['controller_definition_sha256'],
            'changed controller declaration binding')
    pins = {'clock': ('input', 'Clock'), 'root_clock': ('output', 'Clock')}
    for direction, shape in [('input', {'reset':1,'restore_hold':1,'restore_load_pos':1,'restore_load_neg':1,
            'restore_state':gates+70,'freeze_request':1,'ce':gates,'target_cycle':64,'owner_present':len(owners)}),
            ('output', {'gate_clock':gates,'clock_mask':1,'stopped':1,'read_enable':1,'failed':1,
            'captured_ce':gates,'cut_cycle':64,'error':3,'control_state':gates+70})]:
        pins.update({name:(direction,f'UInt<{width}>') for name,width in shape.items()})
    require(controller['ports'] == pins, 'changed physical controller pin ABI')
    for name, value in [('GATES', gates), ('OWNERS', len(owners)), ('EXTERNAL_CLOCK_NETWORK', 1), ('RESTORE_ENABLE', 0)]:
        require(re.search(r'\bparameter ' + name + r' = ' + str(value) + r'\b', controller['body']),
                'changed physical controller parameter ' + name)
    resource = d / 'FireSim-generated.native-region-cut-controller.sv'
    original = ROOT / 'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalClockCut.sv'
    require(sha(resource) == sha(original) == binding['controller_source_sha256'], 'changed physical controller source')
    require(binding['pending_owner'] == root + '.capture_cut_accepted_pending' and
            binding['control_state_bits'] == gates + 71 and binding['control_state_lsb0'] ==
            ['physical_controller', 'accepted_request_pending'], 'missing pending-state ownership')
    return dict(status='pass', physical_gates=gates, external_owners=len(owners),
                unchanged_definitions=len(before)-1, original_raw_registers=len(old['consumers']),
                new_raw_registers=1, complete_fpga_capture=False)


def audit_cut_negatives(directory, out):
    """Rehash altered receipts so hash validation cannot mask semantic gaps."""
    import shutil
    from tools.checkpoint_formats.codec import FormatError
    original, base = Path(directory), Path(out)
    base.mkdir(parents=True, exist_ok=False)
    changes = [
        ('raw-clock', 'attached.fir', 'checkpoint_region_clock_cut.clock <= clock',
         'checkpoint_region_clock_cut.clock <= capture_reset'),
        ('response-permission', 'attached.fir',
         'capture_response_valid <= and(capture_cut_raw_response_valid, capture_read_enable)',
         'capture_response_valid <= capture_cut_raw_response_valid'),
        ('request-permission', 'attached.fir',
         'capture_request_ready <= and(and(capture_cut_raw_request_ready, capture_read_enable), capture_cut_freeze_request)',
         'capture_request_ready <= capture_cut_raw_request_ready'),
        ('pending-reset', 'attached.fir',
         'capture_cut_accepted_pending <= mux(capture_reset, UInt<1>("h0"),',
         'capture_cut_accepted_pending <= mux(capture_reset, UInt<1>("h1"),'),
        ('cycle-authority', 'attached.fir', 'checkpoint_region_clock_cut.target_cycle <= capture_cut_target_cycle',
         'checkpoint_region_clock_cut.target_cycle <= host_ticks'),
        ('physical-network', 'attached.fir', 'parameter EXTERNAL_CLOCK_NETWORK = 1',
         'parameter EXTERNAL_CLOCK_NETWORK = 0'),
        ('restore-mode', 'attached.fir', 'parameter RESTORE_ENABLE = 0', 'parameter RESTORE_ENABLE = 1'),
        ('mask-direction', 'attached.fir', 'output capture_clock_mask : UInt<1>', 'input capture_clock_mask : UInt<1>'),
    ]
    results = []
    for name, filename, needle, replacement in changes:
        attempt = base / name
        shutil.copytree(original, attempt)
        path = attempt / filename
        text = path.read_text()
        require(text.count(needle) == 1, 'ambiguous semantic mutation ' + name)
        path.write_text(text.replace(needle, replacement))
        binding = json.loads((attempt / 'cut-binding.json').read_text())
        binding['attached_sha256'] = sha(attempt / 'attached.fir')
        controller = parse_modules((attempt / 'attached.fir').read_text())['CheckpointPhysicalClockCut']
        binding['controller_definition_sha256'] = hashlib.sha256(controller['body'].encode()).hexdigest()
        (attempt / 'cut-binding.json').write_text(json.dumps(binding, sort_keys=True) + '\n')
        try:
            audit_cut(attempt)
        except FormatError as error:
            results.append(dict(name=name, status='rejected', reason=str(error)))
        else:
            raise FormatError('semantic cut mutation escaped independent audit: ' + name)
    (base / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    return results


def audit_wave(path, *, fault=None, broken=False):
    """Audit settled raw VCD events through EOF, independently of bench markers."""
    names = {'clock', 'armed', 'capture_reset', 'freeze_request', 'enable',
             'capture_clock_mask', 'capture_read_enable', 'capture_captured_ce',
             'failed', 'error', 'cut_cycle', 'capture_request_valid', 'capture_request_ready',
             'capture_response_valid', 'capture_response_ready', 'capture_response_data',
             'capture_bank', 'capture_slot', 'capture_address',
             'dut.host.capture_cut_accepted_pending'}
    state = ['cycle', 'other_cycle', 'left_count', 'right_count', 'other_left_count',
             'other_right_count', 'read_data', 'other_read_data']
    # VCS suppresses celldefine vendor interiors in VCD. These are the exact
    # original parent nets connected to each primitive O pin, retained by the
    # independently audited unmodified regional definitions.
    gates = [f'dut.host.stage.{region}.{gate}' for region in ('network', 'peer')
             for gate in ('checkpoint_physical_root_gate_O', 'left_.gate_O', 'right_.gate_O')]
    names.update(state + gates)
    previous = None
    expected_pending = requests = responses = gate_events = withdrawal_stalls = 0
    samples = valid_cuts = 0
    outstanding = None
    first_fault = first_bad = None
    tail_edges = 0
    prefix = 'native_regions_common_cut_tb.'

    def snapshots():
        scopes, codes, bits = [], {}, {}
        with Path(path).open() as stream:
            for line in stream:
                w = line.split()
                if not w:
                    continue
                if w[0] == '$scope':
                    scopes.append(w[2])
                elif w[0] == '$upscope':
                    scopes.pop()
                elif w[0] == '$var':
                    name = '.'.join(scopes + [w[4].lstrip('\\')])
                    if name.startswith(prefix) and name[len(prefix):] in names:
                        codes[name[len(prefix):]] = w[3]
                elif line.startswith('#'):
                    if set(codes) == names:
                        yield {n: int(bits[c], 2) if re.fullmatch('[01]+', bits.get(c, 'x')) else None
                               for n, c in codes.items()}
                elif line[0] in 'bB' and len(w) == 2:
                    bits[w[1]] = w[0][1:].lower()
                elif line[0] in '01xXzZ':
                    bits[line[1:].strip()] = line[0].lower()
        require(set(codes) == names, 'missing common-cut raw wave signals ' + str(names-set(codes)))
        yield {n: int(bits[c], 2) if re.fullmatch('[01]+', bits.get(c, 'x')) else None
               for n, c in codes.items()}

    for now in snapshots():
        samples += 1
        if not now['armed']:
            previous = now
            continue
        require(all(now[n] is not None for n in names-set(state)), 'unknown common-cut control outside initialization')
        rising = previous is not None and previous['clock'] == 0 and now['clock'] == 1
        if previous is not None and previous['armed']:
            for gate in gates:
                if previous[gate] == 0 and now[gate] == 1:
                    gate_events += 1
                    require(not now['capture_clock_mask'] and not previous['capture_clock_mask'],
                            'physical gate edge while common mask held: ' + gate)
            if now['capture_clock_mask'] and previous['capture_clock_mask'] and not (
                    now['capture_reset'] or previous['capture_reset']):
                require(all(now[n] == previous[n] and now[n] is not None for n in state),
                        'original selected state changed while common cut held')
            if rising:
                if previous['capture_reset']:
                    expected_pending = 0
                    outstanding = None
                else:
                    accepted = previous['capture_request_valid'] and previous['capture_request_ready']
                    acknowledged = previous['capture_response_valid'] and previous['capture_response_ready']
                    if accepted:
                        require(not expected_pending and outstanding is None and previous['capture_read_enable'] and
                                previous['freeze_request'], 'accepted new request outside an owned cut')
                        requests += 1
                        outstanding = (previous['capture_bank'], previous['capture_slot'], previous['capture_address'])
                        expected_pending = 1
                    if acknowledged:
                        require(expected_pending and outstanding is not None and previous['capture_read_enable'],
                                'response acknowledged without pending owner/read permission')
                        responses += 1
                        outstanding = None
                        expected_pending = 0
                    if expected_pending and not previous['freeze_request']:
                        require(previous['capture_clock_mask'] and not previous['capture_request_ready'],
                                'pending withdrawal released cut or admitted replacement')
                    if previous['capture_response_valid'] and not previous['capture_response_ready'] and not previous['freeze_request']:
                        withdrawal_stalls += 1
                require(now['dut.host.capture_cut_accepted_pending'] == expected_pending,
                        'pending owner differs from independent raw handshakes')
            if now['capture_read_enable'] and not previous['capture_read_enable']:
                valid_cuts += 1
                expected_ce = ((~now['enable'] & 3) << 2) | now['enable']
                require(now['capture_captured_ce'] == expected_ce, 'captured CE order/sample differs from original logical drivers')
        if now['failed']:
            if first_fault is None:
                first_fault = dict(target_cycle=now['cut_cycle'], requests=requests, responses=responses)
            require(now['capture_clock_mask'] and not now['capture_read_enable'] and
                    not now['capture_request_ready'] and not now['capture_response_valid'],
                    'physical fault did not revoke both handshakes/retain stop')
            require(requests == first_fault['requests'] and responses == first_fault['responses'],
                    'request or response acknowledged after first physical fault')
            tail_edges += int(rising)
        elif first_fault is not None:
            require(False, 'fault repaired before EOF without shared reset')
        if outstanding is not None and now['capture_response_valid']:
            bank, slot, address = outstanding
            if bank == 255 and slot < 4 and address == 0:
                expected = (now['capture_captured_ce'] >> slot) & 1
                if now['capture_response_data'] != expected:
                    require(broken, 'physical CE response differs before acknowledgement')
                    if first_bad is None:
                        require(not now['capture_response_ready'], 'corrupted response acknowledged at first divergence')
                        first_bad = dict(target_cycle=now['cut_cycle'], bank=bank, slot=slot, requests=requests, responses=responses)
        if first_bad is not None:
            require(responses == first_bad['responses'], 'corrupted response or later beat acknowledged before EOF')
        previous = now
    require(samples > 100 and gate_events > 0, 'incomplete raw common-cut wave')
    if fault is not None:
        require(first_fault is not None and tail_edges >= 4, 'missing physical-fault tail through EOF')
        bit = 0 if 'owner' in fault else (1 if 'ce' in fault and 'cycle' not in fault else 2)
        require(previous['error'] & (1 << bit), 'wrong sticky physical fault owner')
    elif broken:
        require(first_bad is not None, 'compiled CE corruption escaped independent raw-wave audit')
    else:
        require(first_fault is None and first_bad is None and requests == 285 and responses == 284 and
                withdrawal_stalls == 64 and valid_cuts == 5 and expected_pending == 0,
                'incomplete healthy raw handshakes/cuts/reset cancellation')
    return dict(status='pass', requests=requests, responses=responses, valid_cuts=valid_cuts,
                withdrawal_stalls=withdrawal_stalls, physical_gate_edges=gate_events,
                first_fault=first_fault, first_divergence=first_bad, fault_tail_edges=tail_edges,
                tail_audited_through_eof=True, physical_fpga_capture=False)


def audit_wave_negatives(healthy, fault, out):
    """Prove the EOF checker rejects semantic repairs/acks after real failure."""
    from tools.checkpoint_formats.codec import FormatError
    out = Path(out);out.mkdir(parents=True, exist_ok=False)
    def codes(text):
        scopes, found = [], {}
        for line in text.splitlines():
            w = line.split()
            if not w:
                continue
            if w[0] == '$scope':scopes.append(w[2])
            elif w[0] == '$upscope':scopes.pop()
            elif w[0] == '$var':found['.'.join(scopes+[w[4].lstrip('\\')])] = w[3]
        return found
    good, bad = Path(healthy).read_text(), Path(fault).read_text()
    prefix = 'native_regions_common_cut_tb.'
    cases = [('fault-repaired',bad,{'failed':0},'fault repaired'),
             ('gate-after-fault',bad,{'dut.host.stage.network.checkpoint_physical_root_gate_O':1},'physical gate edge'),
             ('response-after-fault',bad,{'capture_response_valid':1},'physical fault did not revoke'),
             ('pending-owner',good,{'clock':1,'dut.host.capture_cut_accepted_pending':1},'pending owner differs')]
    results=[]
    for name,text,changes,reason in cases:
        c=codes(text);at=max(map(int,re.findall(r'^#(\d+)$',text,re.M)))+1
        candidate=out/(name+'.vcd')
        candidate.write_text(text+f'\n#{at}\n'+''.join(str(value)+c[prefix+signal]+'\n' for signal,value in changes.items()))
        try:
            audit_wave(candidate,fault=None if name=='pending-owner' else 'pending-owner')
        except FormatError as error:
            require(reason in str(error), 'raw-wave mutation rejected for wrong reason: '+str(error))
            results.append(dict(name=name,status='rejected',reason=str(error)))
        else:
            raise FormatError('semantic raw-wave mutation escaped EOF audit: '+name)
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    return results
