"""Independently inspect original initialized-owner native capture/restore evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import decode, require
from tools.checkpoint_formats.replay import builds, read_json
from tools.checkpoint_formats.tests.audit_semantic_memory import check_replay


def audit_waveform(case, expected_build, fault_signal=None):
    """Read actual VCS waveforms independently of the generated readback guards."""
    lines = (case / 'restore.txt').read_text().splitlines()
    state = {p: (int(w), int(v, 16)) for p, w, v in (line.split() for line in lines)}
    trace = decode((case / 'capture.trace').read_bytes(), 'trace', expected_build)
    clock = 'semantic_replay_tb.clock'
    ports = {signal: 'semantic_replay_tb.' + signal for direction in ('inputs', 'outputs')
             for signal in trace['records'][0][direction]}
    widths = dict(state)
    widths.update({ports[signal]: (value['width'], None) for direction in ('inputs', 'outputs')
                   for signal, value in trace['records'][0][direction].items()})
    widths[clock] = (1, None)
    identities, values, stack, restored, sampled, mismatches = {}, {}, [], False, 0, []
    with (case / 'replay.vcd').open() as stream:
        for line in stream:
            fields = line.split()
            if not fields:
                continue
            if fields[0] == '$scope':
                stack.append(fields[2])
            elif fields[0] == '$upscope':
                stack.pop()
            elif fields[0] == '$var':
                name = '.'.join(stack + [fields[4]])
                if name in widths:
                    require(int(fields[2]) == widths[name][0], 'changed native waveform state/port width')
                    identities[name] = fields[3]
            elif fields[0] == '$enddefinitions':
                break
        require(set(identities) == set(widths) and len({identities[p] for p in state}) == len(state),
                'missing/aliased complete native waveform state')
        time = 0

        def sample():
            nonlocal restored, sampled
            if time == 1000:
                require(all(values.get(identities[p]) == expected for p, (_, expected) in state.items())
                        and values.get(identities[clock]) == 0, 'actual zero-edge waveform differs from image')
                restored = True
            wanted = 1 if fault_signal else len(trace['records'])
            if sampled < wanted and time == 2000 + 3000 * sampled:
                record = trace['records'][sampled]
                require(values.get(identities[clock]) == 0, 'waveform comparison is outside the pre-edge phase')
                for direction in ('inputs', 'outputs'):
                    for signal, expected in sorted(record[direction].items()):
                        actual = values.get(identities[ports[signal]])
                        if actual != int(expected['value'], 16):
                            mismatches.append((record['cycle'], signal))
                sampled += 1

        for line in stream:
            if line.startswith('#'):
                next_time = int(line[1:])
                if next_time != time:
                    sample()
                    time = next_time
                continue
            fields = line.split()
            if not fields or fields[0].startswith('$'):
                continue
            if fields[0][0] in 'bB' and len(fields) == 2:
                bits, identity = fields[0][1:], fields[1]
            elif fields[0][0] in '01xXzZ':
                bits, identity = fields[0][0], fields[0][1:]
            else:
                continue
            values[identity] = None if any(x in bits.lower() for x in 'xz') else int(bits, 2)
            if identity == identities[clock] and not restored:
                require(values[identity] == 0, 'native waveform contains an edge before complete restore')
        sample()
    require(restored and sampled == (1 if fault_signal else len(trace['records'])), 'incomplete actual waveform replay')
    if fault_signal:
        require(mismatches == [(trace['target_cycle'], fault_signal)] and values.get(identities[clock]) == 0,
                'actual corruption waveform differs from its first divergent boundary')
    else:
        require(not mismatches, 'actual captured input/output waveform differs from original trace')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    args = parser.parse_args()
    summary = read_json(args.summary)
    require(summary['status'] == 'passed' and not summary['level1_verified'] and not summary['level2_cpu_verified'],
            'component evidence misrepresented as CPU acceptance')
    archived = summary['archived_inputs']
    inputs = {}
    for original, binding in archived.items():
        path = Path(binding['path'])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(digest == binding['sha256'] == summary['inputs_sha256'][original], 'changed original native input')
        inputs[Path(original).name] = path
    manifest = read_json(next(p for name, p in inputs.items() if name.endswith('.semantic-state.json')))
    boundary = read_json(next(p for name, p in inputs.items() if name.endswith('.semantic-boundary.json')))
    source = next(p for name, p in inputs.items() if name.endswith('.semantic-reference.fir')).read_text()
    clean = next(p for name, p in inputs.items() if name.endswith('.semantic-clean.sv')).read_text()
    require(hashlib.sha256(source.encode()).hexdigest() == manifest['reference_sha256'], 'wrong original pre-FAME reference')
    require(len(re.findall(r'^    reg ', source, re.M)) == 1 and 'reg counter : UInt<32>' in source and
            not re.search(r'^    (?:mem |smem |cmem )', source, re.M), 'unaccounted original concrete state')
    externals = re.findall(r'^  extmodule (\w+) :\n(.*?)(?=^  (?:module|extmodule) |\Z)', source, re.M | re.S)
    expected_specializations = {'Reader32': (32, 7, 'semantic_limit=%d'),
                                'Reader1': (1, 0, 'semantic_flag=%b'), 'Reader65': (65, 9, 'semantic_wide=%h')}
    require(len(externals) == 3, 'missing or added opaque module')
    for name, body in externals:
        require(name in expected_specializations and 'defname = plusarg_reader' in body, 'unbound original external model')
        specialization = (int(re.search(r'parameter WIDTH = (\d+)', body)[1]),
                          int(re.search(r'parameter DEFAULT = (\d+)', body)[1]),
                          re.search(r'parameter FORMAT = "([^"]+)"', body)[1])
        require(specialization == expected_specializations[name], 'changed original opaque specialization')
    require(source.count('inst a of Reader32') == 2 and source.count('inst b of Reader1') == 1 and
            source.count('inst w of Reader65') == 1 and source.count('inst relay of Relay') == 1,
            'incomplete original external instance hierarchy')
    model = inputs['plusarg_reader.v'].read_text()
    require(clean.count(model) == 1 and model.count('reg [WIDTH-1:0] myplus;') == 1,
            'missing/changed actual external storage implementation')
    ownership = {e['hierarchy']: (e['width'], e['depth'], e['clock_domain']) for e in manifest['state']}
    require(ownership == {'Top.counter': (32, 1, 'Top.clock'), 'Top.a.myplus': (32, 1, 'initial'),
                          'Top.relay.a.myplus': (32, 1, 'initial'), 'Top.b.myplus': (1, 1, 'initial'),
                          'Top.w.myplus': (65, 1, 'initial')}, 'missing complete concrete/initialized ownership')
    if summary['clock_pin_fanout']:
        require('reg counter : UInt<32>, relay.clock' in source and 'relay.clock <= clock' in source and
                'always @(posedge relay_clock)' in clean and '.clock(relay_clock)' in clean,
                'native evidence did not exercise actual child-input clock fanout')
    pids, samples, faults, invalid, native_invalid = [], 0, 0, 0, 0
    out = args.summary.resolve().parent
    require([v['name'] for v in summary['variants']] == ['defaults', 'nondefault'], 'reduced initialization variants')
    for variant in summary['variants']:
        name = variant['name']
        _, trace_build = builds(manifest, boundary, name)
        directory = out / name
        limit, flag, wide = (7, 0, 9) if name == 'defaults' else (305419896, 1, 0x1edcba9876543210f)
        fields = read_json(directory / 'capture-layout.json')
        rows = [json.loads(line) for line in (directory / 'capture.jsonl').read_text().splitlines()]
        require(len(rows) == 17 and len(fields) == 12, 'missing complete original captured fields/edges')
        count = 0
        for cycle, row in enumerate(rows):
            values = {f['path']: int(v, 16) for f, v in zip(fields, row['values'])}
            require(row['cycle'] == cycle and values['counter'] == values['count'] == count and
                    values['a.myplus'] == values['relay.a.myplus'] == limit and
                    values['b.myplus'] == values['flag'] == flag and values['w.myplus'] == values['wide'] == wide and
                    values['result'] == values['repeated'] == (count + limit) % (1 << 32),
                    'original complete state/output recurrence differs')
            count = 0 if values['reset'] else (count + values['data']) % (1 << 32)
        source_log = (directory / 'source-run.log').read_text()
        require('exit=0' in source_log and 'PASS: self-checking ordinary initialized-owner workload' in source_log,
                'native source did not finish its complete workload')
        pids += [int(re.search(r'fresh_process_pid=(\d+)', source_log)[1])]
        require([c['cycle'] for c in variant['cuts']] == [0, 3, 9, 16], 'reduced actual cuts')
        for cut in variant['cuts']:
            case = Path(cut['directory'])
            pids.append(check_replay(case, manifest, boundary, name, rows, fields, cut['cycle'], 5, 5))
            audit_waveform(case, trace_build)
            log = (case / 'run.log').read_text()
            require(all(argument in log for argument in variant['conflicting_restore_args']) and
                    variant['conflicting_restore_args'][0] == '+semantic_limit=42' and
                    variant['conflicting_restore_args'][1] == '+semantic_flag=' + str(1 - flag),
                    'fresh runtime initialization did not differ from captured values')
            samples += cut['samples']
        require({f['owner']: f['signal'] for f in variant['faults']} ==
                {'a.myplus': 'result', 'relay.a.myplus': 'repeated', 'b.myplus': 'flag', 'w.myplus': 'wide'},
                'reduced actual initialized-state corruptions')
        for fault in variant['faults']:
            case = Path(fault['directory'])
            bench = (case / 'replay.sv').read_text()
            mutation = '  dut.' + fault['owner'] + ' = dut.' + fault['owner'] + ' ^ '
            readback = '  if (dut.' + fault['owner'] + ' !== '
            require(bench.index(readback) < bench.index(mutation) < bench.index('  clock = 1;'),
                    'corruption was not injected after complete zero-edge readback')
            pids.append(check_replay(case, manifest, boundary, name, rows, fields, 9, 5, 5, fault['signal']))
            audit_waveform(case, trace_build, fault['signal'])
            faults += 1
        require(len(variant['invalid_images']) == 5 and len(variant['native_loader_rejections']) == 4,
                'reduced image/native loader rejections')
        for label in variant['invalid_images']:
            case = directory / ('reject-' + label)
            require((case / 'invalid.rtlckpt').stat().st_size > 0 and (case / 'rejection.txt').stat().st_size > 0 and
                    not (case / 'restore.txt').exists() and not (case / 'replay.sv').exists(), 'partial invalid publication')
            invalid += 1
        for label in variant['native_loader_rejections']:
            log = (directory / ('native-reject-' + label) / 'run.log').read_text()
            require('RESTORE_ERROR before first DUT edge' in log and 'RESTORE: deposited' not in log and
                    'ACKNOWLEDGED_TARGET_EDGE' not in log and 'exit=0' not in log, 'partial native invalid restore')
            pids.append(int(re.search(r'fresh_process_pid=(\d+)', log)[1]))
            native_invalid += 1
    require(len(pids) == len(set(pids)) == 26 and samples == summary['compared_samples'] == 80,
            'process reuse or incomplete continuation')
    print(json.dumps(dict(status='passed', scope='complete initialized-owner component audit; CPU acceptance pending',
                         owned_words=5, initialized_owners=4, samples=samples, output_comparisons=samples * 5,
                         actual_faults=faults, invalid_images=invalid, native_invalid=native_invalid,
                         distinct_native_processes=len(pids), clock_pin_fanout=summary['clock_pin_fanout'],
                         actual_waveform_zero_edge_and_complete_trace_audited=True), indent=2))


if __name__ == '__main__':
    main()
