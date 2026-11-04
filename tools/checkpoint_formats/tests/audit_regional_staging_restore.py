"""Independently check the first restored regional staging epoch from raw VCD."""
from pathlib import Path
import re
from tools.checkpoint_formats.codec import require


def audit(path, bits, donor, *, corrupt=False, mutate_bit=None):
    top = 'regional_staging_restore_tb.'
    owner = 'dut.host.checkpoint_region_cut_snapshot.staging.'
    names = {'clock', 'capture_reset', 'restore_hold', 'restore_load', 'restore_ready', 'restore_state',
        'control_state', 'cycle', 'capture_clock_mask', 'capture_request_valid', 'capture_request_ready',
        'capture_response_valid', 'capture_response_ready', 'snapshot_valid', 'snapshot_word_data', 'snapshot_word_error'}
    names |= {owner+n for n in ('payload', 'occupied', 'cut_cycle', 'error')}
    scopes, codes, values = [], {}, {}

    def rows():
        def row():
            require(set(codes) == names, 'missing original regional staging fields '+str(names-set(codes)))
            return {n: int(values[c], 2) if re.fullmatch('[01]+', values.get(c, 'x')) else None for n, c in codes.items()}
        with Path(path).open() as stream:
            for line in stream:
                p = line.split()
                if not p:
                    continue
                if p[0] == '$scope':
                    scopes.append(p[2])
                elif p[0] == '$upscope':
                    scopes.pop()
                elif p[0] == '$var':
                    name = '.'.join(scopes+[p[4].lstrip('\\')])
                    if name.startswith(top) and name[len(top):] in names:
                        codes[name[len(top):]] = p[3]
                elif line.startswith('#'):
                    yield row()
                elif line[0] in 'bB' and len(p) == 2:
                    values[p[1]] = p[0][1:].lower()
                elif line[0] in '01xXzZ':
                    values[line[1:].strip()] = line[0].lower()
        yield row()

    previous = None
    loads = acks = rows_after = 0
    divergence = None
    for v in rows():
        if v['capture_reset'] != 0:
            previous = v
            continue
        require(all(x is not None for x in v.values()), 'unknown regional state after preparation reset')
        if previous and previous['clock'] == 0 and v['clock'] == 1:
            if previous['capture_request_valid'] and previous['capture_request_ready']:
                acks += 1
            if previous['capture_response_valid'] and previous['capture_response_ready']:
                acks += 1
            if previous['restore_load'] and previous['restore_ready']:
                require(previous['restore_hold'] == 1 and previous['restore_state'] == donor,
                        'first load differs from independent donor')
                loads += 1
        if v['restore_hold'] or v['restore_load']:
            require(v['capture_clock_mask'] == 1 and not v['capture_request_ready'] and
                    not v['capture_response_valid'] and not v['snapshot_valid'] and
                    v['snapshot_word_data'] == 0 and v['snapshot_word_error'] == 1,
                    'regional restore acknowledged before complete readback')
        if loads:
            rows_after += 1
            raw = v[owner+'payload'] | v[owner+'occupied'] << bits | v[owner+'cut_cycle'] << (bits+1) | v[owner+'error'] << (bits+65)
            observed = v['control_state'] ^ (0 if mutate_bit is None else 1 << mutate_bit)
            require(raw == observed, 'staging observation differs from individual original registers')
            if raw != donor:
                require(corrupt and loads == 1 and acks == 0 and v['restore_hold'] == 1 and v['cycle'] == 38,
                        'partial staging load or acknowledged divergent edge')
                require(raw ^ donor == 1, 'unexpected deliberate semantic corruption')
                divergence = dict(signal='payload[0]', target_cycle=v['cycle'], acknowledged_edges=acks)
            require(v['cycle'] == 38, 'target advanced beyond restored cut during readback')
        previous = v
    require(loads == 1 and rows_after > 0, 'missing independently checked first complete staging load')
    require((divergence is not None) == corrupt, 'missing or unexpected semantic divergence')
    return dict(loads=loads, original_register_bits=bits+71, acknowledged_edges=acks,
        checked_rows=rows_after, first_divergence=divergence)
