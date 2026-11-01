"""Independently reconstruct atomic collector/endpoint staging from raw VCS waves.

Uses original individual registers and pre-edge values, not the packed live
vector, producer counters or PASS markers. Component evidence only.
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
from tools.checkpoint_formats.tests.audit_f2_compiler_cut import (
    FIELDS, audit_native_bank_wave, audit_registers)
from tools.checkpoint_formats.tests.audit_f2_generated_cut import audit_wave

ROOT = Path(__file__).resolve().parents[3]
TOP = 'f2_generated_cut_tb.'
STAGE = 'dut.execution.checkpoint_f2_shadow_adapter.'
ENDPOINT = 'dut.execution.'
PREFIX = 'checkpoint_f2_shadow_'


def rows(path, names):
    scopes, codes, values = [], {}, {}
    def sample():
        require(set(codes) == names, 'missing complete staging waveform: ' + str(names - set(codes)))
        return {n: int(values[c], 2) if c in values and re.fullmatch('[01]+', values[c]) else None
                for n,c in codes.items()}
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
                yield sample()
            elif line[0] in 'bB' and len(p) == 2:
                values[p[1]] = p[0][1:].lower()
            elif line[0] in '01xXzZ':
                values[line[1:].strip()] = line[0].lower()
    yield sample()


def audit_stage(path, case, payload_mutation=None, state_mutation=None):
    names = {n for n,_,_ in FIELDS} | {
        'clock', 'controller_reset', 'clock_mask', 'read_enable', 'failed', 'target_cycle',
        'a', 'b', 'root_clock', 'gate_clock', 'ckpt_req_ready', 'ckpt_resp_valid',
        'ra', 'rb', 'reference_cycle', ENDPOINT + 'left.saved', ENDPOINT + 'right.saved', ENDPOINT + 'cycles',
        'ckpt_resp_ready', 'ckpt_req_valid', 'freeze_request',
        ENDPOINT + 'ckpt_pending', ENDPOINT + 'ckpt_saved_data', ENDPOINT + 'ckpt_saved_error'}
    names |= {PREFIX + n for n in ('request', 'release', 'word_address', 'ready', 'valid', 'failed',
                                 'word_error', 'word_data', 'cut_cycle', 'error', 'control_state')}
    names |= {STAGE + n for n in ('clock', 'occupied', 'payload', 'cut_cycle', 'error', 'live_state')}
    last = None
    saved = label = occupied = 0
    samples = captures = releases = reads = revocations = retained_fault_edges = 0
    cut_labels = []
    first_fault = None
    functional = ('a', 'b', 'target_cycle', 'ra', 'rb', 'reference_cycle',
                  ENDPOINT + 'left.saved', ENDPOINT + 'right.saved', ENDPOINT + 'cycles')
    for v in rows(path, names):
        if any(value is None for value in v.values()):
            require(v['controller_reset'] != 0, 'unknown collector/endpoint/staging state after controller initialization')
            continue
        if last and not last['clock'] and v['clock']:
            if last['controller_reset']:
                saved = label = occupied = 0
            elif not last[PREFIX + 'failed']:
                if last[PREFIX + 'request'] and last[PREFIX + 'ready']:
                    # Reconstruct BEFORE the accepting edge, including the
                    # settled negative-edge collector registers and the OLD
                    # endpoint payload left over from the preceding epoch.
                    require(last['clock_mask'] and last['read_enable'] and not last['failed'] and
                            not last[ENDPOINT + 'ckpt_pending'], 'capture without idle acknowledged cut')
                    control = sum(last[n] << offset for n,offset,_ in FIELDS)
                    saved = ((control << 66) | (last[ENDPOINT + 'ckpt_saved_error'] << 65) |
                             (last[ENDPOINT + 'ckpt_saved_data'] << 1) | last[ENDPOINT + 'ckpt_pending'])
                    label, occupied = last['target_cycle'], 1
                    captures += 1
                    cut_labels.append(label)
                elif last[PREFIX + 'release']:
                    require(not last[ENDPOINT + 'ckpt_pending'], 'staging release acknowledged busy reader')
                    occupied = 0
                    releases += 1
            if last[PREFIX + 'failed'] and not last['controller_reset']:
                retained_fault_edges += 1
        if v['controller_reset']:
            last = v
            continue
        samples += 1
        require((v['a'], v['b'], v['target_cycle']) == (v['ra'], v['rb'], v['reference_cycle']) ==
                (v[ENDPOINT + 'left.saved'], v[ENDPOINT + 'right.saved'], v[ENDPOINT + 'cycles']),
                'staging changed original functional state or acknowledged a target edge')
        control = sum(v[n] << offset for n,offset,_ in FIELDS)
        live = ((control << 66) | (v[ENDPOINT + 'ckpt_saved_error'] << 65) |
                (v[ENDPOINT + 'ckpt_saved_data'] << 1) | v[ENDPOINT + 'ckpt_pending'])
        require(v[STAGE + 'clock'] == v['clock'], 'staging clock stopped with functional clock')
        require(v[STAGE + 'live_state'] == live, 'staging input omitted original collector/endpoint bits')
        payload = v[STAGE + 'payload'] ^ (0 if payload_mutation is None or not occupied else 1 << payload_mutation)
        require(payload == saved and v[STAGE + 'cut_cycle'] == label and v[STAGE + 'occupied'] == occupied,
                'atomic staging differs from independent pre-edge state at target_cycle=' + str(v['target_cycle']))
        packed = saved | (occupied << 147) | (label << 148) | (v[STAGE + 'error'] << 212)
        observed = v[PREFIX + 'control_state'] ^ (0 if state_mutation is None else 1 << state_mutation)
        require(observed == packed, 'staging owner packing differs at target_cycle=' + str(v['target_cycle']))
        require(v[PREFIX + 'cut_cycle'] == label and v[PREFIX + 'error'] == v[STAGE + 'error'],
                'staging owner status omitted')
        if v[PREFIX + 'valid']:
            require(occupied and not v[PREFIX + 'failed'] and v['read_enable'] and v['clock_mask'] and
                    not v[PREFIX + 'release'] and v['target_cycle'] == label,
                    'staging publication without stable cut')
            address = v[PREFIX + 'word_address']
            valid_address = address < 3
            require(v[PREFIX + 'word_error'] == int(not valid_address) and
                    v[PREFIX + 'word_data'] == ((saved >> (64 * address)) & ((1 << 64)-1) if valid_address else 0),
                    'staging serial word differs from immutable full payload')
            reads += int(valid_address)
        else:
            require(v[PREFIX + 'word_error'] and v[PREFIX + 'word_data'] == 0,
                    'unpublishable staging data escaped')
            require(not v['ckpt_req_ready'] and not v['ckpt_resp_valid'], 'bank permission bypassed staging')
        if v[PREFIX + 'failed']:
            # A request/release is withdrawn after its accepting edge. The
            # generic component's combinational overlap check can revoke
            # publication during that withdrawal interval. Only an error
            # retained by an actual raw edge establishes a failed epoch.
            if first_fault is None and v[STAGE + 'error']:
                first_fault = v['target_cycle']
            require(not v[PREFIX + 'valid'] and not v['ckpt_req_ready'] and not v['ckpt_resp_valid'],
                    'staging fault acknowledged data')
            require(v['clock_mask'] and v['root_clock'] == v['gate_clock'] == 0,
                    'staging fault released a functional edge')
            revocations += 1
        last = v
    require(samples > 100, 'incomplete staging execution')
    if case == 'healthy':
        # Ordinary post-run DDR/reset loss is also required by the retained TB.
        require(captures == releases == 4 and cut_labels == [0,17,128,256] and reads >= 36,
                'incomplete four-cut staging scope')
    elif case == 'unstaged-read':
        require(captures == releases == 1 and first_fault == 17 and retained_fault_edges == 20,
                'unstaged read failure advanced or acknowledged')
    elif case != 'corrupt':
        require(captures == 2 and releases == 1 and first_fault == 17 and retained_fault_edges == 20,
                'staging cancellation did not retain exact failed cut')
        if case == 'busy-release':
            require(last[ENDPOINT + 'ckpt_pending'], 'busy staging release lost accepted response')
    else:
        require(captures == 2 and releases == 1 and retained_fault_edges == 0 and
                first_fault is None, 'semantic corruption reached another edge')
    return dict(samples=samples, captures=captures, releases=releases, labels=cut_labels,
                serial_word_samples=reads, revoked_samples=revocations,
                retained_fault_edges=retained_fault_edges, payload_bits=147, staging_owner_bits=218)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore'), 'wave audits belong on EDA')
    execution = local(ROOT, args.execution).resolve()
    require(execution.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'execution outside runs')
    receipt = execution / 'summary.json'
    doc = json.loads(receipt.read_text())
    require(doc['status'] == 'pass' and doc['backend'] == 'eda' and doc['collector_snapshot'] is True and
            doc['physical_fpga_capture'] is False, 'successful staged collector component receipt required')
    for name,digest in doc['artifacts'].items():
        p = (execution / name).resolve()
        require(p.is_relative_to(execution) and file_sha(p) == digest, 'changed execution artifact: ' + name)
    cases = {}
    for case in ('healthy', *doc['faults'], *doc['staging_faults'], 'corrupt'):
        path = execution / case / 'f2-generated-cut.vcd'
        cases[case] = dict(staging=audit_stage(path, case), collector=audit_registers(path))
        if case not in doc['staging_faults']:
            functional_case = 'owner' if case == 'raw-reset' or case.startswith('owner-') else case
            cases[case]['functional'] = audit_wave(path, functional_case, native_banks=True, collector_snapshot=True)
            cases[case]['banks'] = audit_native_bank_wave(path, doc['bank_entries'], case, collector_snapshot=True)
    rejected = {}
    wave = execution / 'healthy/f2-generated-cut.vcd'
    for name,bits,key,message in [('payload',147,'payload_mutation','atomic staging differs'),
                                  ('owner',218,'state_mutation','staging owner packing differs')]:
        rejected[name] = []
        for bit in range(bits):
            try:
                audit_stage(wave, 'healthy', **{key:bit})
            except ValueError as error:
                require(message in str(error), 'mutation failed for unrelated reason: ' + str(error))
                rejected[name].append(bit)
            else:
                require(False, f'undetected staging {name} corruption bit {bit}')
    out = local(ROOT, args.out).resolve()
    require(out.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    out.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix='staging-audit-', dir=out))
    sources = [Path(__file__), ROOT / 'tools/checkpoint_formats/tests/audit_f2_compiler_cut.py',
               ROOT / 'tools/checkpoint_formats/tests/audit_f2_generated_cut.py']
    result = dict(status='pass', backend='eda', observed_utc=datetime.now(timezone.utc).isoformat(), cases=cases,
                  execution_receipt=dict(path=str(receipt), sha256=file_sha(receipt)),
                  sources={str(p.relative_to(ROOT)):file_sha(p) for p in sources},
                  rejected_bits=rejected, physical_fpga_capture=False,
                  waves={str(execution/c/'f2-generated-cut.vcd'):file_sha(execution/c/'f2-generated-cut.vcd') for c in cases})
    (attempt / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(attempt / 'summary.json')


if __name__ == '__main__':
    main()
