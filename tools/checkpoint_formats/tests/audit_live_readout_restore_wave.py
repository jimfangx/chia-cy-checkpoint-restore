"""Audit complete original routing/response registers at actual raw clock edges."""
from pathlib import Path
import re
from tools.checkpoint_formats.codec import require


def audit(path, *, broken=False, owner_bit=None, top='live_readout_restore_tb.', owner='dut.'):
    public = ('clock', 'reset', 'restore_hold', 'restore_load', 'restore_state', 'restore_ready',
              'permission', 'request_valid', 'request_ready', 'response_valid', 'response_ready',
              'original_request_valid', 'original_response_ready', 'control_state')
    registers = ('pending', 'snapshot_owner', 'snapshot_bank.saved_data',
                 'snapshot_bank.saved_error', 'snapshot_bank.pending', 'snapshot_bank.failed')
    signals = {n: top + n for n in public}
    signals.update({n: top + owner + n for n in registers})
    codes, values, scopes, previous = {}, {}, [], {}
    accepted = held = acknowledgements = 0
    initialized = False
    first = None

    def sample():
        nonlocal previous, accepted, held, acknowledgements, initialized, first
        now = {n: int(values[c], 2) for n, c in codes.items()
               if re.fullmatch('[01]+', values.get(c, 'x'))}
        if now.get('clock') == 1 and previous.get('clock') == 0:
            p = previous
            load = p.get('restore_load') == p.get('restore_ready') == 1 and not p.get('reset')
            if p.get('restore_hold') or p.get('restore_load'):
                require(all(p.get(n) == 0 for n in ('request_ready', 'response_valid',
                    'original_request_valid', 'original_response_ready')), 'parked bank handshake')
            if p.get('reset') or load:
                initialized = True
            if not initialized:
                require(p.get('restore_hold') == 1, 'fresh owner advanced before synthesized load')
                previous = now
                return
            require(all(n in now for n in registers + ('control_state',)), 'unknown initialized original register')
            packed = (now['pending'] | now['snapshot_owner'] << 1 |
                now['snapshot_bank.saved_data'] << 2 | now['snapshot_bank.saved_error'] << 66 |
                now['snapshot_bank.pending'] << 67 | now['snapshot_bank.failed'] << 68)
            observed = now['control_state'] ^ (0 if owner_bit is None else 1 << owner_bit)
            require(observed == packed, 'omitted original readout register bit')
            if p.get('reset'):
                require(packed == 0, 'reset missed original owner bit')
            elif load:
                require(p.get('restore_hold') and not p.get('permission'), 'unqualified synthesized load')
                diff = packed ^ p['restore_state']
                if diff:
                    require(broken, 'partial routing/response restore')
                    if first is None:
                        first = dict(canonical_bit=(diff & -diff).bit_length()-1,
                                     acknowledgements_before=acknowledgements)
                accepted += 1
            elif p.get('restore_hold') or p.get('restore_load'):
                # An unheld load may set the existing sticky fault on an
                # outstanding snapshot, but it cannot overwrite payload/route.
                require((packed & ((1 << 68)-1)) == (p['control_state'] & ((1 << 68)-1)),
                        'rejected/held load changed a route or response byte')
                held += 1
            if p.get('response_valid') and p.get('response_ready'):
                require(first is None, 'response acknowledged after first divergence')
                acknowledgements += 1
        previous = now

    for line in Path(path).read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == '$scope': scopes.append(parts[2])
        elif parts[0] == '$upscope': scopes.pop()
        elif parts[0] == '$var':
            name = '.'.join(scopes + [parts[4].lstrip('\\')])
            for role, target in signals.items():
                if name == target: codes[role] = parts[3]
        elif line.startswith('#'): sample()
        elif line[0] in 'bB' and len(parts) == 2: values[parts[1]] = parts[0][1:].lower()
        elif line[0] in '01xXzZ': values[line[1:].strip()] = line[0].lower()
    sample()
    require(codes.keys() == signals.keys(), 'missing raw owner fields ' + str(signals.keys()-codes.keys()))
    if broken:
        require(accepted == 1 and acknowledgements == 0 and first ==
                dict(canonical_bit=2, acknowledgements_before=0), 'semantic fault missed first independent readback')
    else:
        require(accepted >= 1 and held >= 8 and first is None, 'incomplete parked-owner waveform')
    return dict(original_registers=6, bits=69, accepted_loads=accepted,
                held_edges=held, acknowledgements=acknowledgements, first_divergence=first)
