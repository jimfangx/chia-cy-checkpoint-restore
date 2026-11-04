"""Independent complete-state audit of shared-router VCS debug waves."""
from pathlib import Path
import re

TOP = 'region_router_restore_tb.'


def samples(path, names):
    scopes, codes, values = [], {}, {}
    def row():
        if set(codes) != names:
            raise ValueError('missing router debug fields: ' + str(names-set(codes)))
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


def audit(path, regions, enabled, image, *, destination=False, corrupt=False, mutate_bit=None):
    def check(ok, why):
        if not ok:
            raise ValueError('router waveform: ' + why)
    names = {'clock', 'reset', 'capture_state', 'restore_hold', 'restore_load', 'restore_state', 'restore_error',
             'request_valid', 'request_ready', 'response_valid', 'response_ready', 'region_request_valid',
             'region_response_ready', 'bank', 'slot', 'dut.pending', 'dut.invalid', 'dut.owner'}
    last = None
    expected = None
    loads = acknowledgements = held_edges = rows = 0
    divergence = None
    for value in samples(path, names):
        if value['clock'] is None or value['reset'] is None:
            continue
        if any(value[n] is None for n in names-{'restore_hold', 'restore_load', 'restore_state'}):
            check(value['reset'] != 0, 'unknown complete state after reset')
            last = value
            continue
        if last is not None and last['clock'] == 0 and value['clock'] == 1:
            if last['reset']:
                expected = 0
            elif enabled and last['restore_hold'] and last['restore_load'] and not last['restore_error']:
                # First loads must match the independent source image. Later
                # loads exhaust the separate bounded ABI, not donor coverage.
                expected = image[loads] if destination and loads < len(image) else last['restore_state']
                loads += 1
            elif not (enabled and (last['restore_hold'] or last['restore_error'])):
                if last['request_valid'] and last['request_ready']:
                    owner = last['slot'] if last['bank'] == 255 else last['bank']
                    valid = owner < regions
                    expected = ((owner if valid else 0) << 2) | (0 if valid else 2) | 1
                    acknowledgements += 1
                if last['response_valid'] and last['response_ready']:
                    check(expected is not None, 'response before initialized owner')
                    expected &= ~1
                    acknowledgements += 1
            else:
                held_edges += 1
        if expected is not None:
            raw = (value['dut.owner'] << 2) | (value['dut.invalid'] << 1) | value['dut.pending']
            observed = value['capture_state']
            if mutate_bit is not None and loads:
                observed ^= 1 << mutate_bit
            check(observed == raw, 'capture vector differs from individual raw owner registers')
            if corrupt and loads and raw != expected:
                check(loads == 1 and acknowledgements == 0 and value['restore_hold'] == 1,
                      'semantic corruption advanced before first divergence')
                divergence = dict(signal='capture_state', snapshot=0, expected=expected, observed=raw,
                                  acknowledged_edges=acknowledgements)
            else:
                check(raw == expected, 'complete raw owner differs from independent source/edge oracle')
        if enabled and (value['restore_hold'] or value['restore_error']):
            check(all(value[n] == 0 for n in ('request_ready', 'response_valid', 'region_request_valid',
                                             'region_response_ready')), 'held transaction acknowledged')
        rows += 1
        last = value
    check(rows > 0, 'empty debug waveform')
    if destination:
        if corrupt:
            check(divergence is not None, 'missing first semantic divergence')
        else:
            check(loads == 5 + regions * 4 and held_edges >= 5 * 5,
                  'missing complete donor and exhaustive ABI readback coverage')
    return dict(rows=rows, held_edges=held_edges, loads=loads, acknowledged_edges=acknowledgements,
                first_divergence=divergence)
