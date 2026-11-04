"""Reconstruct regional control staging from individual raw VCD registers."""
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require

TOP = 'native_region_cut_snapshot_tb.'
CUT = 'dut.host.checkpoint_region_clock_cut.'


def samples(path, names):
    scopes, codes, values = [], {}, {}
    def row():
        require(set(codes) == names, 'missing snapshot debug fields: ' + str(names - set(codes)))
        return {n: int(values[c], 2) if c in values and re.fullmatch('[01]+', values[c]) else None
                for n, c in codes.items()}
    with Path(path).open() as stream:
        for line in stream:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == '$scope':
                scopes.append(parts[2])
            elif parts[0] == '$upscope':
                scopes.pop()
            elif parts[0] == '$var':
                name = '.'.join(scopes + [parts[4].lstrip('\\')])
                if name.startswith(TOP) and name[len(TOP):] in names:
                    codes[name[len(TOP):]] = parts[3]
            elif line.startswith('#'):
                yield row()
            elif line[0] in 'bB' and len(parts) == 2:
                values[parts[1]] = parts[0][1:].lower()
            elif line[0] in '01xXzZ':
                values[line[1:].strip()] = line[0].lower()
    yield row()


def audit(path, *, healthy=False, corrupt=False, mutate_bit=None, semantic_corruption=False, router_bits=0):
    fields = [('freeze_low', 0), ('sampled', 1), ('release_pending', 2),
              ('captured_ce', 3), ('cut_cycle', 7), ('error', 71)]
    pending = 'dut.host.capture_cut_accepted_pending'
    names = {CUT + n for n, _ in fields} | {pending, 'clock', 'capture_reset',
        'snapshot_request', 'snapshot_release', 'snapshot_ready', 'snapshot_valid',
        'snapshot_failed', 'snapshot_error', 'snapshot_cut_cycle', 'snapshot_word_address',
        'snapshot_word_data', 'snapshot_word_error', 'captured_control_state',
        'staging_control_state', 'physical_read_enable', 'capture_clock_mask',
        'capture_request_valid', 'capture_request_ready', 'capture_response_valid',
        'capture_response_ready', 'cycle'}
    require(router_bits in (0, 7), 'directed fixture router geometry unsupported')
    control_bits = 75 + router_bits
    router_prefix = 'dut.host.checkpoint_region_readout_adapter.'
    router_fields = [('router.pending', 0), ('router.invalid', 1), ('router.owner', 2),
                     ('region0.router.pending', 3), ('region0.router.selected_ce', 4),
                     ('region1.router.pending', 5), ('region1.router.selected_ce', 6)]
    if router_bits:
        names |= {router_prefix + n for n, _ in router_fields} | {'capture_router_state', 'capture_bank', 'capture_slot'}
    expected_router = 0
    last = None
    saved = label = occupied = captures = releases = requests = responses = 0
    serial_addresses, labels, router_cuts = set(), [], []
    failed_seen = False
    divergence = None
    rows = 0
    for v in samples(path, names):
        if any(x is None for x in v.values()):
            require(v['capture_reset'] != 0, 'unknown complete control state after reset')
            continue
        if last and not last['clock'] and v['clock']:
            if router_bits:
                if last['capture_reset']:
                    expected_router = 0
                else:
                    if last['capture_request_valid'] and last['capture_request_ready']:
                        bank, slot = last['capture_bank'], last['capture_slot']
                        route = bank if bank in (0, 1) else slot // 2 if bank == 255 and slot < 4 else None
                        expected_router = (expected_router & ~7) | 1 | ((route or 0) << 2) | (2 if route is None else 0)
                        if route is not None:
                            offset = 3 + 2 * route
                            expected_router = (expected_router & ~(3 << offset)) | ((1 | (2 if bank == 255 else 0)) << offset)
                    if last['capture_response_valid'] and last['capture_response_ready']:
                        if not (expected_router & 2):
                            offset = 3 + 2 * ((expected_router >> 2) & 1)
                            expected_router &= ~(1 << offset)
                        expected_router &= ~1
            if last['capture_reset']:
                saved = label = occupied = 0
            else:
                requests += last['capture_request_valid'] and last['capture_request_ready']
                responses += last['capture_response_valid'] and last['capture_response_ready']
                if not last['snapshot_failed']:
                    if last['snapshot_request'] and last['snapshot_ready']:
                        require(last['physical_read_enable'] and not last[pending] and
                                not last['capture_response_valid'], 'staging without stopped idle source')
                        saved = sum(last[CUT + n] << offset for n, offset in fields) | (last[pending] << 74)
                        if router_bits:
                            saved |= sum(last[router_prefix + n] << (75 + offset) for n, offset in router_fields)
                        label, occupied = last['cycle'], 1
                        captures += 1
                        labels.append(label)
                        if router_bits:
                            router_cuts.append(saved >> 75)
                    elif last['snapshot_release']:
                        occupied = 0
                        releases += 1
        if v['capture_reset']:
            failed_seen = False
            last = v
            continue
        rows += 1
        if router_bits:
            raw_router = sum(v[router_prefix + n] << offset for n, offset in router_fields)
            require(raw_router == expected_router and v['capture_router_state'] == expected_router,
                    'router original/inactive state differs from independent accepted transaction history')
        observed = v['captured_control_state'] ^ ((1 << mutate_bit) if mutate_bit is not None and occupied else 0)
        if semantic_corruption and divergence is not None:
            require(observed != saved and requests == responses == 0 and v['cycle'] == label,
                    'continued or repaired execution after first semantic divergence')
        if semantic_corruption and observed != saved:
            if divergence is None:
                require(captures == 1 and occupied and requests == responses == 0,
                        'semantic corruption acknowledged a bank edge')
                divergence = dict(target_cycle=label, signal='captured_control_state',
                                  expected=saved, observed=observed, acknowledged_requests=0,
                                  acknowledged_responses=0)
            require(requests == responses == 0, 'continued bank acknowledgement after semantic divergence')
            last = v
            continue
        require(observed == saved and v['snapshot_cut_cycle'] == label,
                'control payload/label differs from independent pre-edge registers at target_cycle=' + str(v['cycle']))
        packed = saved | (occupied << control_bits) | (label << (control_bits + 1)) | (v['snapshot_error'] << (control_bits + 65))
        require(v['staging_control_state'] == packed, 'incomplete staging-owner packing')
        if v['snapshot_valid']:
            require(occupied and not v['snapshot_failed'] and v['physical_read_enable'] and
                    v['capture_clock_mask'] and v['cycle'] == label and not v['snapshot_release'],
                    'snapshot exposed outside common target cut')
            address = v['snapshot_word_address']
            require(v['snapshot_word_error'] == (address >= 2), 'serial selector error')
            require(v['snapshot_word_data'] == ((saved >> (64 * address)) & ((1 << 64) - 1) if address < 2 else 0),
                    'serial payload/padding corruption')
            serial_addresses.add(address)
        if not v['snapshot_valid']:
            require(not v['capture_request_ready'] and not v['capture_response_valid'],
                    'bank handshake bypassed atomic snapshot permission')
        # The caller withdraws an accepted request after the positive edge.
        # Its overlap predicate can pulse during those settling deltas; only
        # the source-clock-latched error is a sticky fault owner.
        if v['snapshot_error']:
            failed_seen = True
        if failed_seen:
            require(v['snapshot_failed'] and not v['capture_request_ready'] and not v['capture_response_valid'],
                    'fault repaired or acknowledged before shared reset')
        last = v
    require(rows > 0, 'empty snapshot waveform')
    if healthy:
        require(captures == 5 and releases == 4 and requests == responses + 1 and
                {0, 1, 2}.issubset(serial_addresses), 'incomplete cuts/reads/releases/reset-cancellation')
    if healthy and router_bits:
        require(any(v & 2 for v in router_cuts) and any(v & 4 for v in router_cuts) and
                any(v & 16 for v in router_cuts) and any(v & 64 for v in router_cuts),
                'missing nonzero inactive error/owner/endpoint selection at common cut')
    if corrupt:
        require(captures == 1 and requests == responses == 0, 'corruption acknowledged bank access')
    if semantic_corruption:
        require(divergence is not None and requests == responses == 0, 'missing first semantic divergence')
    return dict(status='pass', captures=captures, releases=releases, cut_cycles=labels,
                requests=requests, responses=responses, waveform_samples=rows,
                serial_addresses=sorted(serial_addresses), fault_observed=failed_seen,
                first_divergence=divergence, router_cuts=router_cuts, complete_fpga_capture=False)
