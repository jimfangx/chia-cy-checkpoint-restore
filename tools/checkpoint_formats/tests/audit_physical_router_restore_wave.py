"""Independent raw-register and accepted-transaction oracle for physical routing."""
from pathlib import Path
import re


def samples(path, names):
    scopes, codes, values = [], {}, {}
    def row():
        if set(codes) != names:
            raise ValueError('missing physical-router debug fields: ' + str(names-set(codes)))
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
                prefix = 'physical_router_restore_tb.'
                if name.startswith(prefix) and name[len(prefix):] in names:
                    codes[name[len(prefix):]] = parts[3]
            elif line.startswith('#'):
                yield row()
            elif line[0] in 'bB' and len(parts) == 2:
                values[parts[1]] = parts[0][1:].lower()
            elif line[0] in '01xXzZ':
                values[line[1:].strip()] = line[0].lower()
    yield row()


def audit(path, enabled, image, *, destination=False, corrupt=False, geometry=True, mutate_bit=None):
    def check(ok, why):
        if not ok:
            raise ValueError('physical-router waveform: ' + why)
    names = {'clock', 'reset', 'capture_state', 'restore_hold', 'restore_load', 'restore_state', 'restore_error',
             'request_valid', 'request_ready', 'response_valid', 'response_ready', 'response_data', 'response_error',
             'bank', 'slot', 'address', 'endpoint_bank', 'endpoint_slot', 'endpoint_address',
             'dut.pending', 'dut.selected_ce'}
    for endpoint in ('functional', 'ce'):
        names.update(endpoint + '_' + field for field in ('request_valid', 'request_ready', 'response_valid',
                     'response_ready', 'response_data', 'response_error'))
    last = None
    expected = None
    loads = acknowledgements = held_edges = rows = 0
    states = set()
    divergence = None
    for v in samples(path, names):
        if v['clock'] is None or v['reset'] is None:
            continue
        if any(v[n] is None for n in names-{'restore_hold', 'restore_load', 'restore_state'}):
            check(v['reset'] != 0, 'unknown raw state/handshake after reset')
            last = v
            continue
        if last is not None and last['clock'] == 0 and v['clock'] == 1:
            if last['reset']:
                expected = 0
            elif enabled and last['restore_load'] and last['restore_hold'] and not last['restore_error']:
                expected = image[loads] if destination and loads < len(image) else last['restore_state']
                loads += 1
            elif not (enabled and (last['restore_hold'] or last['restore_error'])):
                if last['request_valid'] and last['request_ready']:
                    expected = (2 if last['bank'] == 255 else 0) | 1
                    acknowledgements += 1
                if last['response_valid'] and last['response_ready']:
                    check(expected is not None, 'response before owner initialization')
                    expected &= ~1
                    acknowledgements += 1
            else:
                held_edges += 1
        raw = v['dut.selected_ce'] * 2 + v['dut.pending']
        if expected is not None:
            observed = v['capture_state']
            if mutate_bit is not None and loads:
                observed ^= 1 << mutate_bit
            check(observed == raw, 'capture vector differs from individual original registers')
            if corrupt and loads and raw != expected:
                check(loads == 1 and acknowledgements == 0 and v['restore_hold'] == 1,
                      'semantic divergence acknowledged a transaction edge')
                divergence = dict(signal='capture_state', snapshot=0, expected=expected, observed=raw,
                                  acknowledged_edges=acknowledgements)
            else:
                check(raw == expected, 'raw owner disagrees with independent donor/transaction oracle')
            states.add(raw)
        holding = enabled and v['restore_hold']
        error = bool(enabled and v['restore_load'] and (not holding or not geometry))
        check(v['restore_error'] == error, 'load admission/error contract')
        running = not (v['reset'] or holding or error)
        ce = raw >> 1
        endpoint = 'ce' if ce else 'functional'
        valid = bool(running and (raw & 1) and v[endpoint + '_response_valid'])
        ready = bool(running and not (raw & 1) and geometry and
                     v[('ce' if v['bank'] == 255 else 'functional') + '_request_ready'])
        check(v['response_valid'] == valid and v['request_ready'] == ready, 'upstream handshake contract')
        check(v['response_data'] == (v[endpoint + '_response_data'] if valid else 0) and
              v['response_error'] == (v[endpoint + '_response_error'] if valid else 0),
              'response payload/error must belong to accepted endpoint')
        for name in ('functional', 'ce'):
            check(v[name + '_request_valid'] == bool(running and not (raw & 1) and geometry and
                  v['request_valid'] and (v['bank'] == 255) == (name == 'ce')), 'downstream request contract')
            check(v[name + '_response_ready'] == bool(running and (raw & 1) and
                  ce == (name == 'ce') and v['response_ready']), 'downstream response ownership')
        check(all(v['endpoint_' + n] == v[n] for n in ('bank', 'slot', 'address')), 'endpoint selector identity')
        rows += 1
        last = v
    check(rows > 0, 'empty debug waveform')
    if destination and not corrupt:
        check(loads == len(image) + 4 and held_edges >= 25 and states == {0, 1, 2, 3},
              'incomplete independent donor/exhaustive owner readback')
    if corrupt:
        check(divergence is not None, 'missing first semantic divergence')
    if not destination and geometry:
        check(states == {0, 1, 2, 3} and acknowledgements == 4, 'incomplete actual donor transactions')
    return dict(rows=rows, loads=loads, held_edges=held_edges, acknowledged_edges=acknowledgements,
                raw_states=sorted(states), first_divergence=divergence)
