"""Independent raw-wave audit of the generated local FAME cut owner.

Reconstructs progress from original handshakes and native clock edges. This
component audit cannot prove a global cut, physical capture, or CPU migration.
"""
from pathlib import Path
import re

from tools.checkpoint_formats.codec import FormatError, require

P = 'dut.model_.checkpoint_fame_'
COUNTERS = ['completed_steps', 'clockA_consumed', 'clockA_applied', 'clockB_consumed', 'clockB_applied']
WIDTHS = {P + n: 64 for n in COUNTERS} | {P + 'overflow': 1,
    'dut.model_.clockA_enabled': 1, 'dut.model_.clockB_enabled': 1}
NAMES = set(WIDTHS) | {'hostClock', 'hostReset', 'step_index', 'ack',
    'model_clocks_sink_valid', 'model_clocks_sink_ready', 'model_clocks_sink_bits_A', 'model_clocks_sink_bits_B',
    'dut.model_.clockA_buffer.O', 'dut.model_.clockB_buffer.O', 'dut.checkpoint_physical_root_gate.O',
    'checkpoint_f2_functional_reset', 'checkpoint_f2_clock_mask', 'checkpoint_f2_cut_cycle',
    'checkpoint_f2_read_enable', 'checkpoint_f2_failed', 'checkpoint_f2_freeze_request',
    'checkpoint_fame_cut_applied_cycle', 'checkpoint_fame_cut_consistent',
    'dut.model_.a', 'dut.model_.b', 'original.model_.a', 'original.model_.b'}


def check_readback(observed, expected, widths):
    require(set(expected) == set(WIDTHS), 'incomplete reconstructed FAME readback')
    for name, width in WIDTHS.items():
        require(widths[name] == width and observed[name] == expected[name],
                'FAME raw readback mismatch signal=' + name)


def snapshots(path):
    scopes, codes, widths, bits = [], {}, {}, {}
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
                top = 'fame_clock_cut_tb.'
                if name.startswith(top) and name[len(top):] in NAMES:
                    name = name[len(top):]; codes[name], widths[name] = w[3], int(w[2])
            elif line.startswith('#'):
                if set(codes) == NAMES and all(re.fullmatch('[01]+', bits.get(codes[n], 'x')) for n in NAMES):
                    yield {n: int(bits[codes[n]], 2) for n in NAMES}, widths
            elif line[0] in 'bB' and len(w) == 2:
                bits[w[1]] = w[0][1:].lower()
            elif line[0] in '01xXzZ':
                bits[line[1:].strip()] = line[0].lower()
    require(set(codes) == NAMES, 'missing debug signals: ' + str(NAMES - set(codes)))
    yield {n: int(bits[codes[n]], 2) for n in NAMES}, widths


def audit_wave(path):
    previous, expected = None, None
    edges = dict(A=0, B=0)
    raw_edges = functional_edges = stalls = cut_samples = samples = 0
    fault_bits, readback_bits, cuts = set(), set(), set()
    lookahead = False
    for v, widths in snapshots(path):
        samples += 1
        if v['checkpoint_f2_functional_reset']:
            expected = {P + n: 0 for n in COUNTERS} | {P + 'overflow': 0,
                'dut.model_.clockA_enabled': 0, 'dut.model_.clockB_enabled': 0}
        rising = previous is not None and not previous['hostClock'] and v['hostClock']
        if rising:
            raw_edges += 1
        if previous:
            root = 'dut.checkpoint_physical_root_gate.O'
            if not previous[root] and v[root] and not v['checkpoint_f2_functional_reset']:
                functional_edges += 1
                require(expected is not None, 'no initialized FAME observations')
                accepted = previous['model_clocks_sink_valid'] and previous['model_clocks_sink_ready']
                expected[P + 'completed_steps'] += int(accepted)
                stalls += int(not accepted)
                for d in ('A', 'B'):
                    expected[P + 'clock' + d + '_consumed'] += int(accepted and previous['model_clocks_sink_bits_' + d])
                    expected[P + 'clock' + d + '_applied'] += int(accepted and previous['dut.model_.clock' + d + '_enabled'])
                    if accepted:
                        expected['dut.model_.clock' + d + '_enabled'] = previous['model_clocks_sink_bits_' + d]
            for d in ('A', 'B'):
                gate = 'dut.model_.clock' + d + '_buffer.O'
                if not previous[gate] and v[gate] and not v['checkpoint_f2_functional_reset']:
                    edges[d] += 1
        if expected is not None:
            require(all(widths[n] == w for n, w in WIDTHS.items()), 'observer widths changed')
            if rising:
                check_readback(v, expected, widths)
                require(v[P + 'clockA_applied'] == edges['A'] and v[P + 'clockB_applied'] == edges['B'],
                        'independent native edge count differs')
                require(v['dut.model_.a'] == v['original.model_.a'] and v['dut.model_.b'] == v['original.model_.b'],
                        'original functional state differs from uninstrumented reference')
                if not v['checkpoint_f2_functional_reset'] and not readback_bits:
                    # Exhaust every independently read observer/pending bit at
                    # a real raw-edge sample; do not mutate the retained VCD.
                    for name, width in WIDTHS.items():
                        for b in range(width):
                            changed = dict(v); changed[name] ^= 1 << b
                            try:
                                check_readback(changed, expected, widths)
                            except FormatError as error:
                                require(str(error) == 'FAME raw readback mismatch signal=' + name,
                                        'mutation rejected for a different signal')
                            else:
                                raise FormatError('readback mutation escaped the actual auditor')
                            readback_bits.add((name, b))
            consistent = not v['checkpoint_f2_functional_reset'] and not v[P + 'overflow']
            for d in ('A', 'B'):
                c, a = (v[P + 'clock' + d + '_' + n] for n in ('consumed', 'applied'))
                pending = v['dut.model_.clock' + d + '_enabled']
                consistent &= c == a + pending and c <= v[P + 'completed_steps']
                lookahead |= c == a + 1 and pending == 1
            require(v['checkpoint_fame_cut_consistent'] == int(consistent), 'local predicate differs from full-width arithmetic')
            require(v['checkpoint_fame_cut_applied_cycle'] == v[P + 'clockA_applied'], 'cycle label is not applied progress')
            if v['checkpoint_f2_read_enable']:
                require(consistent and v['checkpoint_f2_clock_mask'] and v['checkpoint_f2_freeze_request']
                        and not v['checkpoint_f2_failed'] and v['checkpoint_f2_cut_cycle'] == edges['A'],
                        'read permission at an invalid or mislabeled cut')
                cut_samples += 1; cuts.add(v['checkpoint_f2_cut_cycle'])
            changed = [(n, v[n] ^ e) for n, e in expected.items() if v[n] != e]
            if changed:
                require(not rising and v['checkpoint_f2_clock_mask'] and not consistent
                        and not v['checkpoint_f2_read_enable'] and previous is not None and v['ack'] == previous['ack'],
                        'corrupt owner advanced or retained permission/acknowledgement')
                if len(changed) == 1 and changed[0][1] & (changed[0][1] - 1) == 0:
                    fault_bits.add((changed[0][0], changed[0][1].bit_length() - 1))
        previous = v
    require(previous['ack'] == 512 and raw_edges > 550 and functional_edges > 500 and stalls > 80
            and edges['A'] > 60 and edges['B'] > 30 and cut_samples > 20 and len(cuts) == 4
            and len(fault_bits) >= 259 and len(readback_bits) == 323 and lookahead,
            'incomplete independent raw-wave cut scope')
    return dict(samples=samples, raw_edges=raw_edges, functional_edges=functional_edges, stalls=stalls,
                native_edges=edges, distinct_applied_cuts=sorted(cuts), cut_samples=cut_samples,
                local_single_bit_faults=len(fault_bits), independent_readback_bit_mutations=len(readback_bits),
                pending_lookahead_observed=lookahead, acknowledged=previous['ack'], global_target_cut_proven=False)
