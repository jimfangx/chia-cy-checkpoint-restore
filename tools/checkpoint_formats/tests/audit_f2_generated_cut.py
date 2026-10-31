"""Independent raw-wave audit of the generated F2 clock/reset connection.

Checks every functional and visible collector bit, not just testbench markers.
This is component simulation evidence and establishes no FPGA/CPU acceptance.
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
NAMES = ['controller_reset', 'clock', 'freeze_request', 'rst_main_n', 'ddr_ready', 'writer_xor',
         'owner_present', 'clock_mask', 'read_enable', 'failed', 'root_clock', 'gate_clock', 'logical_ce',
         'physical_error', 'reset_error', 'writer_state', 'captured_writers', 'axi_reset_n', 'simulator_reset',
         'functional_reset', 'target_cycle', 'cut_cycle', 'a', 'b', 'control_state',
         'ref_axi_reset_n', 'ref_reset', 'ref_writers', 'reference_cycle', 'ra', 'rb', 'edges',
         'dut.execution.left.saved', 'dut.execution.right.saved', 'dut.execution.cycles',
         'dut.execution.left.reset', 'dut.execution.right.reset',
         'dut.execution.checkpoint_physical_root_gate_CE', 'dut.execution.left.gate_I',
         'dut.execution.right.gate_I', 'dut.execution.left.gate_CE', 'dut.execution.right.gate_CE']


def audit_wave(path, case):
    scopes, codes, values = [], {}, {}
    last = None
    samples = holds = 0
    cuts = []
    max_cycle = 0
    pulse_without_edge = False
    reset_divergence = False

    def sample():
        nonlocal last, samples, holds, max_cycle, pulse_without_edge, reset_divergence
        raw = {n: values.get(code, 'x') for n, code in codes.items()}
        if raw.get('controller_reset') != '0' or any(not re.fullmatch('[01]+', raw.get(n, 'x')) for n in NAMES):
            return
        v = {n: int(bits, 2) for n, bits in raw.items()}
        samples += 1
        s = v['control_state']
        if not (s >> 80) & 1:
            max_cycle = max(max_cycle, v['target_cycle'])
        require(v['writer_state'] == v['ref_writers'] and v['axi_reset_n'] == v['ref_axi_reset_n'] and
                v['simulator_reset'] == v['ref_reset'], 'original shell paths changed')
        require((v['a'], v['b'], v['target_cycle']) == (v['ra'], v['rb'], v['reference_cycle']),
                'complete original functional state differs')
        require(v['a'] == v['dut.execution.left.saved'] and v['b'] == v['dut.execution.right.saved'] and
                v['target_cycle'] == v['dut.execution.cycles'], 'functional internal state omitted')
        mask, sampled = s & 1, (s >> 1) & 1
        require(v['clock_mask'] == mask and v['physical_error'] == (s >> 69) & 7 and
                v['reset_error'] == (s >> 73) & 3 and v['captured_writers'] == (s >> 75) & 15,
                'visible collector state decode differs')
        require(v['functional_reset'] == (((s >> 72) & 1) if mask else v['simulator_reset']),
                'functional reset bypassed hold')
        if sampled:
            require(v['cut_cycle'] == (s >> 5) & ((1 << 64) - 1), 'cut cycle decode differs')
        require(v['dut.execution.checkpoint_physical_root_gate_CE'] == 1-mask and
                v['dut.execution.left.gate_I'] == v['clock'] == v['dut.execution.right.gate_I'] and
                v['dut.execution.left.gate_CE'] == (v['logical_ce'] & 1) * (1-mask) and
                v['dut.execution.right.gate_CE'] == ((v['logical_ce'] >> 1) & 1) * (1-mask),
                'generated native clock wiring differs')
        if v['dut.execution.left.reset'] != v['functional_reset']:
            require(case == 'corrupt' and v['target_cycle'] == 17 and mask and v['root_clock'] == v['gate_clock'] == 0,
                    'unexpected reset route divergence')
            reset_divergence = True
        require(v['dut.execution.right.reset'] == v['functional_reset'], 'right reset route differs')
        if v['read_enable']:
            require(mask and sampled and not v['failed'] and v['freeze_request'] and
                    v['target_cycle'] == v['cut_cycle'] and v['root_clock'] == v['gate_clock'] == 0 and
                    v['captured_writers'] == v['writer_state'] == 15 and s >> 73 == 15 << 2 and
                    (s >> 3) & 3 == v['logical_ce'], 'invalid read permission or packed cut state')
            if last and not last['read_enable']:
                cuts.append(v['target_cycle'])
        if last and last['clock_mask'] and mask:
            holds += 1
            require((v['a'], v['b'], v['target_cycle']) == (last['a'], last['b'], last['target_cycle']) and
                    v['root_clock'] == v['gate_clock'] == 0 and v['captured_writers'] == last['captured_writers'],
                    'state advanced during held cut')
        if (last and last['clock_mask'] and mask and last['rst_main_n'] and last['ddr_ready'] and
                (not v['rst_main_n'] or not v['ddr_ready'])):
            require(v['failed'] and not v['read_enable'] and (s >> 80) & 1, 'source loss not retained')
            pulse_without_edge |= last['clock'] == v['clock']
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
                prefix = 'f2_generated_cut_tb.'
                if name.startswith(prefix) and name[len(prefix):] in NAMES:
                    codes[name[len(prefix):]] = p[3]
            elif line.startswith('#'):
                sample()
            elif line[0] in 'bB' and len(p) == 2:
                values[p[1]] = p[0][1:].lower()
            elif line[0] in '01xXzZ':
                values[line[1:].strip()] = line[0].lower()
    sample()
    require(set(codes) == set(NAMES) and samples > 50 and holds > 15, 'missing full-visibility state')
    require(cuts == ([0, 17, 128, 256] if case == 'healthy' else [0, 17]), 'incomplete cuts')
    if case == 'healthy':
        require(max_cycle == 320 and last['edges'] == 320, 'incomplete active execution')
    else:
        require(last['target_cycle'] == 17 and last['clock_mask'], 'fault acknowledged later edge')
        if case == 'corrupt':
            require(reset_divergence and not last['failed'], 'missing independent route corruption')
        else:
            require(last['failed'] and not last['read_enable'], 'missing cancellation')
            if case not in ('writer', 'owner'):
                require(pulse_without_edge and (last['control_state'] >> 80) & 1, 'pulse not independently observed')
            if case == 'writer':
                require((last['control_state'] >> 79) & 1, 'writer drift not sticky')
    return dict(samples=samples, held_samples=holds, cuts=cuts, max_target_cycle=max_cycle,
                last_target_cycle=last['target_cycle'], pulse_without_raw_edge=pulse_without_edge,
                functional_bits=80, control_bits=81, shell_writer_bits=4, reset_divergence=reset_divergence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore'), 'wave verification belongs on EDA')
    execution = local(ROOT, args.execution).resolve()
    receipt = execution / 'summary.json'
    doc = json.loads(receipt.read_text())
    require(doc['status'] == 'pass' and doc['backend'] == 'eda' and doc['physical_fpga_capture'] is False,
            'successful component receipt required')
    for name, digest in doc['artifacts'].items():
        path = (execution / name).resolve()
        require(path.is_relative_to(execution) and file_sha(path) == digest, 'execution artifact changed: ' + name)
    cases = {case: audit_wave(execution / case / 'f2-generated-cut.vcd', case)
             for case in ('healthy', *doc['faults'], 'corrupt')}
    out = local(ROOT, args.out).resolve()
    require(out.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    out.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix='wave-audit-', dir=out))
    result = dict(status='pass', backend='eda', observed_utc=datetime.now(timezone.utc).isoformat(), cases=cases,
                  execution_receipt=dict(path=str(receipt), sha256=file_sha(receipt)),
                  producer_sha256=file_sha(__file__), physical_fpga_capture=False,
                  waves={str(execution/c/'f2-generated-cut.vcd'):file_sha(execution/c/'f2-generated-cut.vcd') for c in cases})
    (attempt / 'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print(attempt / 'summary.json')


if __name__ == '__main__':
    main()
