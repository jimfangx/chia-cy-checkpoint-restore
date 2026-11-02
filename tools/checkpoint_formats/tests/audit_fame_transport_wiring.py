"""Independent full-debug-wave audit of actual existing-transport input pins."""
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require


def snapshots(path, names):
    scopes, codes, widths, values = [], {}, {}, {}
    def sample():
        if set(codes) == names and all(re.fullmatch('[01]+', values.get(codes[n], 'x')) for n in names):
            return {n: int(values[codes[n]], 2) for n in names}
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
                prefix = 'fame_transport_wiring_tb.'
                if name.startswith(prefix) and name[len(prefix):] in names:
                    name = name[len(prefix):]
                    codes[name], widths[name] = parts[3], int(parts[2])
            elif line.startswith('#'):
                value = sample()
                if value is not None:
                    yield value, widths
            elif line[0] in 'bB' and len(parts) == 2:
                values[parts[1]] = parts[0][1:].lower()
            elif line[0] in '01xXzZ':
                values[line[1:].strip()] = line[0].lower()
    require(set(codes) == names, 'missing debug signals: ' + str(names - set(codes)))
    value = sample()
    require(value is not None, 'unknown final debug state')
    yield value, widths


def check_qualification(v, transport):
    p = 'dut.model_.checkpoint_fame_'
    valid = not v['hostReset'] and not v[p + 'overflow']
    for domain in ('A', 'B'):
        # Python integers retain the carry bit and cannot silently wrap.
        valid &= (v[p + 'clock' + domain + '_consumed'] ==
                  v[p + 'clock' + domain + '_applied'] + v['dut.model_.clock' + domain + '_enabled'])
        valid &= v[p + 'clock' + domain + '_consumed'] <= v[p + 'completed_steps']
    require(v['checkpoint_fame_cut_consistent'] == valid, 'raw FAME predicate differs')
    applied = v[p + 'clockA_applied']
    require(v['checkpoint_fame_cut_applied_cycle'] == applied and v[transport + '.target_cycle'] == applied,
            'actual transport used a different target label')
    for role, original in [('owner_present', 'ownerPresent'), ('owner_frozen', 'ownerFrozen'), ('owner_error', 'ownerError')]:
        expected = v[original] | (0 if valid else 2) if role == 'owner_error' else v[original] & (7 if valid else 5)
        require(v[transport + '.' + role] == expected, 'actual transport qualification differs: ' + role)


def audit_wave(path, nested=False, corrupt=False):
    transport = 'dut.peer.transport' if nested else 'dut.transport'
    p = 'dut.model_.checkpoint_fame_'
    counters = [p + n for n in ('completed_steps', 'clockA_consumed', 'clockA_applied', 'clockB_consumed', 'clockB_applied')]
    names = set(counters) | {p + 'overflow', 'dut.model_.clockA_enabled', 'dut.model_.clockB_enabled',
        'hostClock', 'hostReset', 'host_step', 'acknowledged', 'patterns', 'ownerPresent', 'ownerFrozen', 'ownerError',
        'model_clocks_sink_valid', 'model_clocks_sink_ready', 'model_clocks_sink_bits_A', 'model_clocks_sink_bits_B',
        'checkpoint_fame_cut_applied_cycle', 'checkpoint_fame_cut_consistent'} | {
        transport + '.' + n for n in ('target_cycle', 'owner_present', 'owner_frozen', 'owner_error')}
    previous = None
    expected = dict.fromkeys(counters, 0)
    samples = edges = active_edges = stalls = 0
    first_divergence = None
    combinations = set()
    for v, widths in snapshots(path, names):
        samples += 1
        require(all(widths[n] == 64 for n in counters), 'changed original counter widths')
        check_qualification(v, transport)
        rising = previous is not None and not previous['hostClock'] and v['hostClock']
        if first_divergence is not None:
            require(not rising and v['host_step'] == 17 and v['acknowledged'] == 16,
                    'execution or acknowledgement continued after first divergence')
        if rising:
            edges += 1
            if v['hostReset']:
                expected = dict.fromkeys(counters, 0)
            else:
                active_edges += 1
                accepted = previous['model_clocks_sink_valid'] and previous['model_clocks_sink_ready']
                expected[p + 'completed_steps'] += bool(accepted)
                stalls += not accepted
                for domain in ('A', 'B'):
                    expected[p + 'clock' + domain + '_consumed'] += bool(accepted and previous['model_clocks_sink_bits_' + domain])
                    expected[p + 'clock' + domain + '_applied'] += bool(accepted and previous['dut.model_.clock' + domain + '_enabled'])
        divergent = [n for n in counters if v[n] != expected[n]]
        if divergent:
            require(corrupt and v['host_step'] == 17 and v['acknowledged'] == 16 and
                    divergent == [p + 'clockA_applied'], 'unexpected or acknowledged first divergence: ' + str(divergent))
            require(v[divergent[0]] == (expected[divergent[0]] ^ 1), 'corruption changed after first divergence')
            if first_divergence is None:
                first_divergence = dict(status='expected_divergence', host_step=17, acknowledged=16, signal=divergent[0])
        elif first_divergence is not None:
            require(False, 'divergent state was repaired after stop')
        if v['host_step'] == 512:
            combinations.add((v['ownerPresent'], v['ownerFrozen'], v['ownerError']))
        previous = v
    if corrupt:
        require(first_divergence is not None, 'corrupt state never diverged')
        return first_divergence | dict(samples=samples, tail_audited_through_eof=True)
    require(samples > 1000 and active_edges == 512 and previous['acknowledged'] == 512 and
            previous['patterns'] == 512 and len(combinations) == 512 and stalls > 80, 'incomplete raw-wave scope')
    return dict(status='pass', samples=samples, raw_edges=edges, active_edges=active_edges, owner_combinations=len(combinations),
                acknowledged=previous['acknowledged'], stalls=stalls)
