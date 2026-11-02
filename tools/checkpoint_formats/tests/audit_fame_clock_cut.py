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


class NativeCutAudit:
    """Check the actual native audit samples, including each whole cut epoch."""

    def __init__(self, rows):
        self.selectors = {(r['bank'], r['slot']): r['hierarchy'].replace('Top.', 'dut.', 1) for r in rows}
        require(bool(rows) and len(self.selectors) == len(rows), 'duplicate or empty native bank selectors')
        require(len(set(self.selectors.values())) == len(rows), 'duplicate native storage hierarchy')
        self.baseline = self.staged = self.outstanding = None
        self.acknowledged = set()
        self.reads = self.acks = self.cuts = self.completed_cuts = self.stalls = 0

    @staticmethod
    def occupied(v):
        return bool(v['checkpoint_f2_shadow_control_state'] >> 147 & 1)

    def check_original(self, v):
        for name, value in self.baseline.items():
            require(v[name] == value, 'native original storage changed during cut: ' + name)

    def check_response(self, v):
        require(self.baseline is not None and self.outstanding is not None,
                'unsolicited native bank response')
        require(v['checkpoint_f2_shadow_valid'] and v['checkpoint_f2_read_enable'] and
                not v['ckpt_resp_error'] and
                v['ckpt_resp_data'] == self.baseline[self.selectors[self.outstanding]],
                'native bank response differs before acknowledgement')

    def sample(self, previous, v, rising):
        if previous is None:
            require(not self.occupied(v) and not v['ckpt_resp_valid'], 'native audit starts inside an epoch')
            return
        was_occupied, occupied = self.occupied(previous), self.occupied(v)
        capture = rising and previous['checkpoint_f2_shadow_request'] and previous['checkpoint_f2_shadow_ready']
        if capture:
            require(self.baseline is None and not was_occupied and occupied,
                    'native staging overlaps or fails to open an epoch')
            self.baseline = {name: previous[name] for name in self.selectors.values()}
            self.staged = ((previous['checkpoint_f2_control_state'] << 66) |
                           (previous['dut.ckpt_saved_error'] << 65) |
                           (previous['dut.ckpt_saved_data'] << 1) | previous['dut.ckpt_pending'])
            self.acknowledged = set()
            self.cuts += 1
        require(not occupied or self.baseline is not None, 'native occupied epoch lacks staging')
        if was_occupied:
            require(self.baseline is not None, 'native epoch lost its baseline')
            self.check_original(previous)
            self.check_original(v)
        if occupied:
            self.check_original(v)
            require(v['checkpoint_f2_shadow_control_state'] & ((1 << 147)-1) == self.staged,
                    'native staged owner differs from independent pre-edge collector/endpoint')
        acknowledged = rising and previous['ckpt_resp_valid'] and previous['ckpt_resp_ready']
        if acknowledged:
            self.check_response(previous)
            require(self.outstanding not in self.acknowledged, 'duplicate native response acknowledgement')
            self.acknowledged.add(self.outstanding)
            self.outstanding = None
            self.acks += 1
        if rising and previous['ckpt_req_valid'] and previous['ckpt_req_ready']:
            key = previous['ckpt_bank'], previous['ckpt_slot']
            require(was_occupied and not capture and self.baseline is not None,
                    'native request outside staged cut')
            require(key in self.selectors and previous['ckpt_address'] == 0, 'unknown native selector')
            require(self.outstanding is None, 'overlapping native bank requests')
            require(key not in self.acknowledged, 'repeated native selector in cut')
            self.outstanding = key
            self.reads += 1
        if previous['ckpt_resp_valid'] and not acknowledged:
            require(v['ckpt_resp_valid'], 'native response withdrawn before acknowledgement')
        if v['ckpt_resp_valid']:
            self.check_response(v)
            self.stalls += int(rising and not v['ckpt_resp_ready'])
        if was_occupied and not occupied:
            require(rising and previous['checkpoint_f2_shadow_release'], 'native epoch disappeared without release')
            require(self.outstanding is None and self.acknowledged == set(self.selectors),
                    'native cut released before every selector was acknowledged')
            self.completed_cuts += 1
            self.baseline = self.staged = None

    def finish(self):
        require(self.baseline is None and self.outstanding is None and self.completed_cuts == self.cuts,
                'native audit ends inside an incomplete cut')


def snapshots(path, names=NAMES):
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
                if name.startswith(top) and name[len(top):] in names:
                    name = name[len(top):]; codes[name], widths[name] = w[3], int(w[2])
            elif line.startswith('#'):
                if set(codes) == names and all(re.fullmatch('[01]+', bits.get(codes[n], 'x')) for n in names):
                    yield {n: int(bits[codes[n]], 2) for n in names}, widths
            elif line[0] in 'bB' and len(w) == 2:
                bits[w[1]] = w[0][1:].lower()
            elif line[0] in '01xXzZ':
                bits[line[1:].strip()] = line[0].lower()
    require(set(codes) == names, 'missing debug signals: ' + str(names - set(codes)))
    yield {n: int(bits[codes[n]], 2) for n in names}, widths


def audit_wave(path, native_rows=None):
    previous, expected = None, None
    edges = dict(A=0, B=0)
    raw_edges = functional_edges = stalls = cut_samples = samples = 0
    fault_bits, readback_bits, cuts = set(), set(), set()
    lookahead = False
    names = set(NAMES)
    native = None
    if native_rows is not None:
        native = NativeCutAudit(native_rows)
        names |= set(native.selectors.values()) | {'ckpt_bank', 'ckpt_slot', 'ckpt_address', 'ckpt_req_valid',
            'ckpt_req_ready', 'ckpt_resp_valid', 'ckpt_resp_ready', 'ckpt_resp_data', 'ckpt_resp_error',
            'checkpoint_f2_shadow_request', 'checkpoint_f2_shadow_ready', 'checkpoint_f2_shadow_valid',
            'checkpoint_f2_shadow_release',
            'checkpoint_f2_shadow_control_state', 'checkpoint_f2_control_state',
            'dut.ckpt_saved_error', 'dut.ckpt_saved_data', 'dut.ckpt_pending'}
    for v, widths in snapshots(path, names):
        samples += 1
        if v['checkpoint_f2_functional_reset']:
            expected = {P + n: 0 for n in COUNTERS} | {P + 'overflow': 0,
                'dut.model_.clockA_enabled': 0, 'dut.model_.clockB_enabled': 0}
        rising = previous is not None and not previous['hostClock'] and v['hostClock']
        if rising:
            raw_edges += 1
        if native is not None:
            native.sample(previous, v, rising)
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
                held = v['checkpoint_f2_freeze_request'] or (native_rows is not None and
                    (v['checkpoint_f2_shadow_control_state'] >> 147 & 1))
                require(consistent and v['checkpoint_f2_clock_mask'] and held
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
    if native_rows is not None:
        native.finish()
        require(native.reads == native.acks == 4 * len(native_rows) and native.cuts == 4 and
                native.stalls >= 4 * native.reads, 'incomplete native readout/staging/backpressure scope')
    return dict(samples=samples, raw_edges=raw_edges, functional_edges=functional_edges, stalls=stalls,
                native_edges=edges, distinct_applied_cuts=sorted(cuts), cut_samples=cut_samples,
                local_single_bit_faults=len(fault_bits), independent_readback_bit_mutations=len(readback_bits),
                pending_lookahead_observed=lookahead, acknowledged=previous['ack'], global_target_cut_proven=False,
                native_reads=native.reads if native else 0, native_acks=native.acks if native else 0,
                staged_cuts=native.cuts if native else 0, native_stalls=native.stalls if native else 0)
