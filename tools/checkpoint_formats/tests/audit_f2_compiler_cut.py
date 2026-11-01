"""Audit compiler-connected cut waves against every actual collector register.

Independent state reconstruction supplements original functional/reset/clock
comparison. This is component evidence, never FPGA or CPU migration acceptance.
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
from tools.checkpoint_formats.tests.audit_f2_generated_cut import audit_wave

ROOT = Path(__file__).resolve().parents[3]
TOP = 'f2_generated_cut_tb.'
ADAPTER = 'dut.execution.checkpoint_f2_adapter.'
# Independent layout: actual individual registers, not the adapter's packed wire.
FIELDS = [(ADAPTER + 'cut.physical.' + n, shift, width) for n, shift, width in (
    ('freeze_low', 0, 1), ('sampled', 1, 1), ('release_pending', 2, 1),
    ('captured_ce', 3, 2), ('cut_cycle', 5, 64), ('error', 69, 3))]
FIELDS += [(ADAPTER + 'cut.captured_reset', 72, 1), (ADAPTER + 'cut.reset_error', 73, 2),
           (ADAPTER + 'guard.captured_writers', 75, 4), (ADAPTER + 'guard.writer_drift', 79, 1),
           (ADAPTER + 'guard.source_lost', 80, 1)]
SIGNALS = {n for n, _, _ in FIELDS} | {'control_state', 'controller_reset', 'clock', 'target_cycle',
    ADAPTER + 'clock', ADAPTER + 'owner_present', 'owner_present', 'dut.execution.reset',
    ADAPTER + 'writer_state', 'raw_reset_xor', 'simulator_reset'}


def audit_native_bank_wave(path, entries, case, corrupt_bit=None):
    """Reconstruct accepted beats from selectors and ORIGINAL functional state.

    Track requests and acknowledgements at raw edges independently of the
    producer's packed data, counters and PASS markers. Cancelled beats must
    remain pending, and withdrawal must drain without accepting another beat.
    """
    names = {'clock', 'controller_reset', 'freeze_request', 'clock_mask', 'read_enable', 'failed',
             'ckpt_req_valid', 'ckpt_req_ready', 'ckpt_resp_valid', 'ckpt_resp_ready', 'ckpt_resp_data',
             'ckpt_resp_error', 'ckpt_bank', 'ckpt_slot', 'ckpt_address', 'target_cycle', 'a', 'b',
             'dut.execution.ckpt_clock', 'dut.execution.ckpt_freeze', 'dut.execution.ckpt_reset',
             'dut.execution.ckpt_pending', 'dut.execution.checkpoint_f2_bank_ckpt_resp_ready'}
    scopes, codes, values = [], {}, {}
    last, pending = None, None
    samples = accepted = acknowledged = draining = cancelled = 0
    draining_edges = cancelled_edges = 0
    sources = {'PhysicalPlanTop.cycles': 'target_cycle', 'PhysicalPlanTop.left.saved': 'a',
               'PhysicalPlanTop.right.saved': 'b'}
    require(len(entries) == len(sources) and {r['hierarchy'] for r in entries} == set(sources),
            'complete original bank inventory required')
    selectors = {(r['bank'], r['slot']): sources[r['hierarchy']] for r in entries}
    require(len(selectors) == len(sources), 'aliased bank selectors')

    def sample():
        nonlocal last, pending, samples, accepted, acknowledged, draining, cancelled, draining_edges, cancelled_edges
        if set(codes) != names:
            return
        raw = {n: values.get(codes[n], 'x') for n in names}
        if raw['controller_reset'] != '0':
            last, pending = None, None
            return
        if any(not re.fullmatch('[01]+', v) for n, v in raw.items()
               if n not in ('ckpt_resp_data', 'ckpt_resp_error')):
            return
        v = {n: int(bits, 2) if re.fullmatch('[01]+', bits) else None for n, bits in raw.items()}
        samples += 1
        if last and not last['clock'] and v['clock']:
            if pending is not None and not last['freeze_request'] and not last['failed']:
                draining_edges += 1
            if pending is not None and last['failed']:
                cancelled_edges += 1
            if last['ckpt_resp_valid'] and last['ckpt_resp_ready']:
                require(pending is not None, 'unowned bank acknowledgement')
                acknowledged += 1
                pending = None
            if last['ckpt_req_valid'] and last['ckpt_req_ready']:
                require(pending is None, 'bank overwrote pending response')
                source = selectors.get((last['ckpt_bank'], last['ckpt_slot']))
                valid = source is not None and last['ckpt_address'] == 0
                pending = (last[source] if valid else 0, int(not valid))
                accepted += 1
        require(v['dut.execution.ckpt_clock'] == v['clock'] and
                v['dut.execution.ckpt_freeze'] == v['clock_mask'] and
                v['dut.execution.ckpt_reset'] == v['controller_reset'], 'bank clock/freeze/reset ownership changed')
        require(v['dut.execution.ckpt_pending'] == int(pending is not None), 'bank pending state/handshake mismatch')
        require(v['ckpt_req_ready'] == int(pending is None and v['read_enable'] and v['freeze_request']) and
                v['ckpt_resp_valid'] == int(pending is not None and v['read_enable']) and
                v['dut.execution.checkpoint_f2_bank_ckpt_resp_ready'] ==
                (v['ckpt_resp_ready'] & v['read_enable']), 'bank permission bypass')
        if v['ckpt_resp_valid']:
            observed = v['ckpt_resp_data']
            if observed is not None and corrupt_bit is not None:
                observed ^= 1 << corrupt_bit
            require((observed, v['ckpt_resp_error']) == pending,
                    'bank response differs from original state at target_cycle=' + str(v['target_cycle']))
        if pending is not None and not v['freeze_request'] and not v['failed']:
            require(v['clock_mask'] and v['read_enable'] and not v['ckpt_req_ready'], 'pending response released cut')
            draining += 1
        if v['failed'] and pending is not None:
            require(v['clock_mask'] and not v['ckpt_resp_valid'] and not v['ckpt_req_ready'],
                    'cancelled beat acknowledged or functional clock released')
            cancelled += 1
        last = v

    with path.open() as stream:
        for line in stream:
            p = line.split()
            if not p:
                continue
            if p[0] == '$scope':
                scopes.append(p[2])
            elif p[0] == '$upscope':
                scopes.pop()
            elif p[0] == '$var':
                name = '.'.join(scopes + [p[4].lstrip('\\')])
                if name.startswith(TOP) and name[len(TOP):] in names:
                    codes[name[len(TOP):]] = p[3]
            elif line.startswith('#'):
                sample()
            elif line[0] in 'bB' and len(p) == 2:
                values[p[1]] = p[0][1:].lower()
            elif line[0] in '01xXzZ':
                values[line[1:].strip()] = line[0].lower()
    sample()
    require(set(codes) == names and samples > 50, 'complete bank waveform absent')
    require((accepted, acknowledged) == ((24, 24) if case == 'healthy' else
            (6, 6) if case == 'corrupt' else (7, 6)), 'incomplete bank acceptance/acknowledgement scope')
    expected_drain_edges = 20 if case == 'healthy' else 6 if case.startswith('release-') else 5
    require(draining_edges == expected_drain_edges and
            (case in ('healthy', 'corrupt') or cancelled_edges == 20),
            f'missing drain/cancellation edge scope: case={case} drain={draining_edges} cancelled={cancelled_edges}')
    return dict(samples=samples, accepted=accepted, acknowledged=acknowledged,
                draining_samples=draining, cancelled_samples=cancelled, draining_edges=draining_edges,
                cancelled_edges=cancelled_edges, functional_entries=len(entries))


def audit_registers(path, corrupt_bit=None):
    scopes, codes, widths, values = [], {}, {}, {}
    samples = 0
    saw_reset_mismatch = False

    def sample():
        nonlocal samples, saw_reset_mismatch
        if set(codes) != SIGNALS:
            return
        raw = {n: values.get(codes[n], 'x') for n in SIGNALS}
        if raw['controller_reset'] != '0' or any(not re.fullmatch('[01]+', bits) for bits in raw.values()):
            return
        v = {n: int(bits, 2) for n, bits in raw.items()}
        samples += 1
        state = 0
        for name, offset, width in FIELDS:
            require(widths[name] == width and v[name] < (1 << width), 'collector register width changed: ' + name)
            state |= v[name] << offset
        observed = v['control_state'] ^ (0 if corrupt_bit is None else 1 << corrupt_bit)
        require(observed == state, 'collector register reconstruction differs at target_cycle=' + str(v['target_cycle']))
        require(v[ADAPTER + 'clock'] == v['clock'], 'collector was placed on a stopped clock')
        writer = v[ADAPTER + 'writer_state']
        require(v['dut.execution.reset'] == v['simulator_reset'] ^ v['raw_reset_xor'],
                'raw reset fault injection changed shell wiring')
        consistent = v['dut.execution.reset'] == int(not (writer & 2 and writer & 8))
        require(widths[ADAPTER + 'owner_present'] == 5 and
                v[ADAPTER + 'owner_present'] == (int(consistent) << 4) | v['owner_present'],
                'external owners or raw-reset consistency bypassed')
        saw_reset_mismatch |= not consistent

    with path.open() as stream:
        for line in stream:
            p = line.split()
            if not p:
                continue
            if p[0] == '$scope':
                scopes.append(p[2])
            elif p[0] == '$upscope':
                scopes.pop()
            elif p[0] == '$var':
                name = '.'.join(scopes + [p[4].lstrip('\\')])
                if name.startswith(TOP) and name[len(TOP):] in SIGNALS:
                    name = name[len(TOP):]
                    codes[name], widths[name] = p[3], int(p[2])
            elif line.startswith('#'):
                sample()
            elif line[0] in 'bB' and len(p) == 2:
                values[p[1]] = p[0][1:].lower()
            elif line[0] in '01xXzZ':
                values[line[1:].strip()] = line[0].lower()
    sample()
    require(set(codes) == SIGNALS and samples > 50, 'complete original collector registers absent')
    return dict(samples=samples, collector_register_bits=81, actual_registers=len(FIELDS),
                reset_consistency_owner_bits=1, raw_reset_mismatch_observed=saw_reset_mismatch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore'), 'wave audit belongs on EDA')
    execution = local(ROOT, args.execution).resolve()
    require(execution.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'execution outside runs')
    receipt = execution / 'summary.json'
    doc = json.loads(receipt.read_text())
    require(doc['status'] == 'pass' and doc['backend'] == 'eda' and doc['compiler_connected'] is True and
            doc['physical_fpga_capture'] is False, 'compiler-connected component receipt required')
    for name, digest in doc['artifacts'].items():
        path = (execution / name).resolve()
        require(path.is_relative_to(execution) and file_sha(path) == digest, 'execution artifact changed: ' + name)
    cases = {}
    for case in ('healthy', *doc['faults'], 'corrupt'):
        path = execution / case / 'f2-generated-cut.vcd'
        cases[case] = dict(functional=audit_wave(path, 'owner' if case == 'raw-reset' or case.startswith('owner-') else case,
                                              native_banks=doc.get('native_banks', False)),
                           collector=audit_registers(path))
        if doc.get('native_banks', False):
            cases[case]['banks'] = audit_native_bank_wave(path, doc['bank_entries'], case)
        if case == 'raw-reset':
            require(cases[case]['collector']['raw_reset_mismatch_observed'], 'missing actual raw-reset fault')
    rejected = []
    for bit in range(81):
        try:
            audit_registers(execution / 'healthy/f2-generated-cut.vcd', corrupt_bit=bit)
        except ValueError as error:
            require('collector register reconstruction differs at target_cycle=' in str(error),
                    'mutation failed for an unrelated reason')
            rejected.append(bit)
        else:
            require(False, 'undetected packed collector corruption bit ' + str(bit))
    bank_rejected = []
    if doc.get('native_banks', False):
        for bit in range(64):
            try:
                audit_native_bank_wave(execution / 'healthy/f2-generated-cut.vcd', doc['bank_entries'], 'healthy', bit)
            except ValueError as error:
                require('bank response differs from original state at target_cycle=' in str(error),
                        'bank mutation failed for an unrelated reason')
                bank_rejected.append(bit)
            else:
                require(False, 'undetected bank response corruption bit ' + str(bit))
    out = local(ROOT, args.out).resolve()
    require(out.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    out.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix='register-audit-', dir=out))
    result = dict(status='pass', backend='eda', observed_utc=datetime.now(timezone.utc).isoformat(), cases=cases,
                  execution_receipt=dict(path=str(receipt), sha256=file_sha(receipt)),
                  sources={str(Path(__file__).relative_to(ROOT)): file_sha(__file__),
                           'tools/checkpoint_formats/tests/audit_f2_generated_cut.py': file_sha(
                               ROOT / 'tools/checkpoint_formats/tests/audit_f2_generated_cut.py')},
                  physical_fpga_capture=False, rejected_control_state_bits=rejected,
                  rejected_bank_response_bits=bank_rejected,
                  waves={str(execution / c / 'f2-generated-cut.vcd'): file_sha(
                      execution / c / 'f2-generated-cut.vcd') for c in cases})
    (attempt / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(attempt / 'summary.json')


if __name__ == '__main__':
    main()
