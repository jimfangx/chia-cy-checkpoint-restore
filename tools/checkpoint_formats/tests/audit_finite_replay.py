"""Independent waveform audit of zero-edge restore and every finite I/O row."""
import argparse
import json
from pathlib import Path
import time

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.finite_replay import check_clean
from tools.checkpoint_formats.tests.verify_finite_replay_vcs import sha


def audit_case(case, manifest, boundary, result, clean_validator=check_clean):
    metadata = result['metadata']
    clean_validator(manifest, boundary, (case/'clean.sv').read_text())
    require(all(sha(case/n) == h for n, h in result['artifact_hashes'].items()), 'changed replay artifact')
    # One expected value per semantic word, including all memory addresses.
    expected = {}
    with (case/'restore.txt').open() as stream:
        for line in stream:
            name, width, value = line.split()
            expected[name] = [int(width), int(value, 16), False]
    require(len(expected) == metadata['restored_words'], 'incomplete restore oracle')
    state_ids, port_ids, stack = {}, {}, []
    prefix = 'finite_replay_tb.'
    names = {'next_cycle', 'target_edges', 'clock'} | {p['name'] for p in metadata['ports']}
    with (case/'replay.vcd').open() as wave, (case/'trace.txt').open() as trace:
        for line in wave:
            f = line.split()
            if not f:
                continue
            if f[0] == '$scope':
                stack.append(f[2])
            elif f[0] == '$upscope':
                stack.pop()
            elif f[0] == '$var':
                name = '.'.join(stack + [f[4].lstrip('\\')])
                if name in expected:
                    require(int(f[2]) == expected[name][0] and f[3] not in state_ids,
                            'missing/aliased/reshaped semantic waveform word')
                    state_ids[f[3]] = expected.pop(name)
                if name.startswith(prefix) and name[len(prefix):] in names:
                    port_ids[name[len(prefix):]] = f[3]
            elif f[0] == '$enddefinitions':
                break
        require(not expected and len(state_ids) == metadata['restored_words'], 'waveform state membership differs')
        require(set(port_ids) == names, 'waveform boundary membership differs')
        wanted = set(port_ids.values())
        values = {}
        time, restored_matches, audited, mismatches, restored_checked = 0, 0, 0, [], False
        start = metadata['first_cycle']
        # At time 2 ns the load and its combinational settle have completed;
        # input delivery for C also settles in this same time step. Edge C is
        # at time 3 ns. Each subsequent cycle occupies exactly 3 ns.
        def finish_time():
            nonlocal restored_checked, audited
            if time == 2000:
                require(restored_matches == metadata['restored_words'], 'waveform differs from complete pre-edge snapshot')
                require(values[port_ids['clock']] == 0 and values[port_ids['target_edges']] == 0,
                        'waveform load advances an edge')
                restored_checked = True
                state_ids.clear()
            if time == (2 + 3*audited)*1000 and audited < metadata['samples']:
                f = trace.readline().split()
                require(f and f[0] == 'DATA' and int(f[1]) == start+audited, 'trace timing/index differs')
                require(values[port_ids['next_cycle']] == start+audited and
                        values[port_ids['target_edges']] == audited and values[port_ids['clock']] == 0,
                        'waveform cycle/clock/edge timing differs')
                for p, v in zip(metadata['ports'], f[2:]):
                    actual = values.get(port_ids[p['name']])
                    if actual != int(v, 16):
                        mismatches.append(dict(cycle=start+audited, signal=p['name'],
                                               expected=int(v, 16), actual=actual))
                audited += 1
        for line in wave:
            if line.startswith('#'):
                new_time = int(line[1:])
                if new_time != time:
                    finish_time()
                    time = new_time
                continue
            f = line.split()
            if not f or f[0].startswith('$'):
                continue
            if f[0][0] in 'bB' and len(f) == 2:
                bits, identity = f[0][1:], f[1]
            elif f[0][0] in '01xXzZ':
                bits, identity = f[0][0], f[0][1:]
            else:
                continue
            if identity not in wanted and identity not in state_ids:
                continue
            actual = None if any(x in bits.lower() for x in 'xz') else int(bits, 2)
            if identity in wanted:
                values[identity] = actual
            if identity in state_ids:
                state = state_ids[identity]
                correct = actual == state[1]
                if correct != state[2]:
                    restored_matches += 1 if correct else -1
                    state[2] = correct
        finish_time()
        require(restored_checked, 'waveform ends before the pre-edge observation')
        fault = result['first_mismatch_cycle']
        if fault is None:
            require(audited == metadata['samples'] and not mismatches and
                    values[port_ids['target_edges']] == metadata['samples'] and
                    values[port_ids['next_cycle']] == metadata['end_cycle'], 'healthy waveform finite replay differs')
        else:
            require(audited == fault-start+1 and mismatches and
                    mismatches[0]['cycle'] == fault and mismatches[0]['signal'] == result['signal'] and
                    values[port_ids['target_edges']] == fault-start and
                    values[port_ids['next_cycle']] == fault, 'waveform bug cycle or stop timing differs')
        return dict(zero_edge_waveform_state_words=restored_matches, checked_boundaries=audited,
                    checked_input_output_values=audited*len(metadata['ports']), first_mismatches=mismatches,
                    actual_edges=values[port_ids['target_edges']], full_waveform_state_and_timing_verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--wait', action='store_true', help='audit completed cases while the verifier finishes')
    args = parser.parse_args()
    out = args.run.resolve()
    deadline = time.monotonic() + 1800
    def read_result(path):
        while args.wait and not path.is_file():
            require(time.monotonic() < deadline, 'timed out waiting for verifier evidence: '+str(path))
            time.sleep(1)
        return json.loads(path.read_text())
    if args.wait:
        summary = dict(fixture=read_result(out/'fixture-summary.json'), production=dict(results=[
            dict(cwd=str(out/'production'/name)) for name in ('healthy', 'rtl-bug-first', 'rtl-bug-repeat')]))
    else:
        summary = read_result(out/'summary.json')
    evidence = []
    for group, inputs in [('fixture', args.build.resolve()/'f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config'),
                          ('production', out/'production/inputs')]:
        manifest, boundary = [json.loads((inputs/('FireSim-generated'+s)).read_text()) for s in
                              ('.semantic-state.json', '.semantic-boundary.json')]
        for result in summary[group]['results']:
            case = Path(result['cwd'])
            result = read_result(case/'result.json')
            print('WAVEFORM_AUDIT '+str(case), flush=True)
            result = audit_case(case, manifest, boundary, result)
            evidence.append(dict(case=str(case), **result))
    completed = read_result(out/'summary.json')
    require(completed['status'] == 'pass' and {c['case'] for c in evidence} ==
            {r['cwd'] for group in ('fixture', 'production') for r in completed[group]['results']},
            'verifier did not complete the identical whole audit scope')
    report = dict(status='pass', cases=evidence, complete_state_and_cycle_waveform_audit=True)
    (out/'independent-waveform-audit.json').write_bytes(canonical(report))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
