"""Independently reconstruct FAME observations from raw inputs and vendor clocks.

No testbench scoreboard or packed observer state is trusted. Component only.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.regression_runner import local

ROOT = Path(__file__).resolve().parents[3]
P = 'dut.model_.checkpoint_fame_'
COUNTERS = ['completed_steps', 'clockA_consumed', 'clockA_applied', 'clockB_consumed', 'clockB_applied']
WIDTHS = {P + n: 64 for n in COUNTERS} | {P + 'overflow': 1}
NAMES = set(WIDTHS) | {'hostClock', 'hostReset', 'step_index', 'ack',
    'model_clocks_sink_valid', 'model_clocks_sink_ready', 'model_clocks_sink_bits_A', 'model_clocks_sink_bits_B',
    'dut.model_.clockA_enabled', 'dut.model_.clockB_enabled',
    'dut.model_.clockA_buffer.O', 'dut.model_.clockB_buffer.O',
    'dut.model_.a', 'dut.model_.b', 'original.model_.a', 'original.model_.b'}


def audit_wave(path, mutation=None):
    scopes, codes, widths, bits = [], {}, {}, {}
    previous = None
    expected = None
    samples = rising = stalls = 0
    edges = {'A': 0, 'B': 0}
    lookahead = False

    def sample():
        nonlocal previous, expected, samples, rising, stalls, lookahead
        raw = {n: bits.get(codes.get(n), 'x') for n in NAMES}
        if set(codes) != NAMES or any(not re.fullmatch('[01]+', s) for s in raw.values()):
            return
        v = {n: int(s, 2) for n, s in raw.items()}
        samples += 1
        if previous:
            if not previous['hostClock'] and v['hostClock']:
                rising += 1
                if previous['hostReset']:
                    expected = {n: 0 for n in COUNTERS}
                    expected['overflow'] = 0
                else:
                    require(expected is not None, 'observer was never initialized')
                    accepted = previous['model_clocks_sink_valid'] and previous['model_clocks_sink_ready']
                    expected['completed_steps'] += int(accepted)
                    stalls += int(not accepted)
                    for d in ('A', 'B'):
                        expected['clock' + d + '_consumed'] += int(accepted and previous['model_clocks_sink_bits_' + d])
                        expected['clock' + d + '_applied'] += int(accepted and previous['dut.model_.clock' + d + '_enabled'])
            for d in ('A', 'B'):
                gate = 'dut.model_.clock' + d + '_buffer.O'
                if not previous[gate] and v[gate] and not v['hostReset']:
                    edges[d] += 1
        if expected is not None:
            for n, value in expected.items():
                signal = P + n
                observed = v[signal]
                if mutation is not None and mutation[0] == signal:
                    observed ^= 1 << mutation[1]
                require(widths[signal] == WIDTHS[signal] and observed == value,
                        'FAME observer mismatch signal=' + n + ' host_step=' + str(v['step_index']) +
                        ' acknowledged=' + str(v['ack']))
            require(v['dut.model_.a'] == v['original.model_.a'] and v['dut.model_.b'] == v['original.model_.b'],
                    'original functional state changed')
            for d in ('A', 'B'):
                applied = expected['clock' + d + '_applied']
                consumed = expected['clock' + d + '_consumed']
                pending = v['dut.model_.clock' + d + '_enabled']
                require(applied == edges[d] and consumed == applied + pending,
                        'native edge or pending token not represented')
                lookahead |= consumed > applied
        previous = v

    with Path(path).open() as stream:
        for line in stream:
            words = line.split()
            if not words:
                continue
            if words[0] == '$scope':
                scopes.append(words[2])
            elif words[0] == '$upscope':
                scopes.pop()
            elif words[0] == '$var':
                name = '.'.join(scopes + [words[4].lstrip('\\')])
                top = 'fame_clock_progress_tb.'
                if name.startswith(top) and name[len(top):] in NAMES:
                    name = name[len(top):]
                    codes[name], widths[name] = words[3], int(words[2])
            elif line.startswith('#'):
                sample()
            elif line[0] in 'bB' and len(words) == 2:
                bits[words[1]] = words[0][1:].lower()
            elif line[0] in '01xXzZ':
                bits[line[1:].strip()] = line[0].lower()
    sample()
    require(set(codes) == NAMES and samples > 500 and rising == 515 and previous['ack'] == 512 and
            stalls > 80 and lookahead and edges['A'] > 60 and edges['B'] > 30, 'incomplete raw execution wave')
    return dict(samples=samples, host_edges=rising, acknowledged=previous['ack'], stalls=stalls,
                native_edges=edges, one_token_lookahead_observed=lookahead, observer_register_bits=321)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore'), 'raw wave auditing belongs on EDA')
    execution = local(ROOT, args.execution).resolve()
    require(execution.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'execution outside runs')
    doc = json.loads((execution / 'summary.json').read_text())
    require(doc['status'] == 'pass' and doc['backend'] == 'eda' and doc['physical_fpga_capture'] is False,
            'successful component execution required')
    for n, digest in doc['artifacts'].items():
        path = (execution / n).resolve()
        require(path.is_relative_to(execution) and file_sha(path) == digest, 'execution artifact changed: ' + n)
    healthy = execution / 'healthy/fame-progress.vcd'
    audit = audit_wave(healthy)
    try:
        audit_wave(execution / 'corrupt/fame-progress.vcd')
    except ValueError as error:
        require('FAME observer mismatch signal=clockA_applied host_step=17 acknowledged=16' in str(error),
                'corruption failed for unrelated reason: ' + str(error))
        corruption = str(error)
    else:
        raise ValueError('deliberate observation corruption was missed')
    rejected = 0
    for signal, width in WIDTHS.items():
        for bit in range(width):
            try:
                audit_wave(healthy, (signal, bit))
            except ValueError as error:
                require('FAME observer mismatch signal=' in str(error), 'unrelated mutation rejection')
                rejected += 1
            else:
                raise ValueError('observer bit corruption missed: ' + signal + ':' + str(bit))
    base = local(ROOT, args.out).resolve()
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'audit evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='audit-', dir=base))
    result = dict(status='pass', backend='eda', physical_fpga_capture=False,
                  observed_utc=datetime.now(timezone.utc).isoformat(), audit=audit,
                  corruption=corruption, rejected_state_bit_mutations=rejected,
                  execution=dict(path=str(execution / 'summary.json'), sha256=file_sha(execution / 'summary.json')),
                  auditor_sha256=file_sha(Path(__file__)))
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n'); print(out / 'summary.json')


if __name__ == '__main__':
    main()
