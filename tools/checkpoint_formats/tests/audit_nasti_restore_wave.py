"""Reconstruct opt-in restore and hold directly from original adapter VCD registers."""
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require


def audit(path, addr, ident, *, broken=False):
    top = 'checkpoint_nasti_restore_tb.'
    # Independent canonical ABI; never consult io_controlState or expected_state.
    address = [('addr', 64), ('len', 8), ('size', 3), ('burst', 2), ('lock', 1),
               ('cache', 4), ('prot', 3), ('qos', 4), ('region', 4), ('id', 64), ('user', 1)]
    fields = [(prefix + '_' + name, width) for prefix, layout in (
        ('aw', address), ('wd', [('data',32), ('last',1), ('id',64), ('strb',4), ('user',1)]),
        ('ar', address)) for name, width in layout]
    fields += [(n, 1) for n in ('haveAW', 'haveW', 'haveAR', 'badW', 'busy', 'writing', 'responseValid', 'responseError')]
    fields += [('responseData', 32), ('responseId', 64), ('errorReadRemaining', 8)]
    require(len(fields) == 38 and sum(w for _, w in fields) == 530, 'changed independent register inventory')
    roles = {n: top + n for n in ('clock', 'reset', 'restore_hold', 'restore_load',
        'restore_state', 'restore_accepted', 'restore_error', 'awready', 'wready', 'arready',
        'bvalid', 'rvalid', 'requestValid', 'responseReady')}
    roles.update({n: top + 'dut.' + n for n, _ in fields})
    scopes, codes, widths, values = [], {}, {}, {}
    previous = {}
    loaded = held = enabled = 0
    first = None
    timestamp = 0

    def original(sample):
        value = offset = 0
        for name, width in fields:
            require(name in sample, 'unknown original register at restore/hold ' + name)
            value |= sample[name] << offset
            offset += width
        return value

    def sample():
        nonlocal previous, loaded, held, enabled, first
        now = {n: int(values[c], 2) for n, c in codes.items()
               if re.fullmatch('[01]+', values.get(c, 'x'))}
        if now.get('clock') == 1 and previous.get('clock') == 0:
            p = previous
            if not p.get('reset', 1):
                if p.get('restore_hold') or p.get('restore_load'):
                    require(all(p.get(n) == 0 for n in ('awready', 'wready', 'arready',
                        'bvalid', 'rvalid', 'requestValid', 'responseReady')), 'restore barrier handshake')
                    if loaded == 0 and not p.get('restore_accepted'):
                        previous = now
                        return
                    actual = original(now)
                    if p.get('restore_accepted'):
                        require(p['restore_hold'] and p['restore_load'] and not p['restore_error'], 'load outside held epoch')
                        expected = p['restore_state']; loaded += 1
                        if actual != expected:
                            require(broken, 'original register differs on accepted restore edge')
                            if first is None:
                                diff = actual ^ expected
                                first = dict(timestamp=timestamp, canonical_bit=(diff & -diff).bit_length() - 1,
                                             enabled_edges=enabled)
                    else:
                        require(actual == original(p), 'original register changed during hold/rejected load')
                        held += 1
                else:
                    enabled += 1
        previous = now

    with Path(path).open() as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith('$scope '):
                scopes.append(line.split()[2])
            elif line.startswith('$upscope '):
                scopes.pop()
            elif line.startswith('$var '):
                parts = line.split(); full = '.'.join(scopes + [parts[4]])
                for role, target in roles.items():
                    if full == target:
                        codes[role], widths[role] = parts[3], int(parts[2])
            elif line.startswith('#'):
                sample(); timestamp = int(line[1:])
            elif line.startswith('b'):
                val, code = line[1:].split(); values[code] = val.lower()
            elif line and line[0] in '01xXzZ' and not line.startswith('$'):
                values[line[1:]] = line[0].lower()
        sample()
    require(set(codes) == set(roles), 'missing direct original registers in debug wave')
    for name, width in fields:
        actual_width = addr if name.endswith('_addr') else ident if name.endswith('_id') or name == 'responseId' else width
        require(widths[name] == actual_width, 'changed original debug width ' + name)
    require(loaded > 0 and (first is not None) == broken, 'incomplete restore waveform/mutation')
    return dict(original_registers=38, original_bits=sum(widths[n] for n, _ in fields),
                loaded_edges=loaded, held_edges=held, enabled_edges=enabled, first_divergence=first)
