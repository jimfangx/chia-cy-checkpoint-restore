"""Audit original component state recurrence, images, event labels and VCS waves."""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import decode, require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.multiclock_inventory import audit_inventory
from tools.checkpoint_formats.replay import builds, state_words
from tools.checkpoint_formats.semantic import decode_semantic


def waveform(path):
    identities, widths, values, snapshots, stack = {}, {}, {}, {}, []
    time = 0
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == '$scope':
            stack.append(fields[2])
        elif fields[0] == '$upscope':
            stack.pop()
        elif fields[0] == '$var':
            name = '.'.join(stack + [fields[4]])
            require(name not in identities, 'duplicate native waveform declaration')
            identities[name], widths[name] = fields[3], int(fields[2])
        elif line.startswith('#'):
            snapshots[time] = dict(values)
            time = int(line[1:])
        elif fields[0].startswith(('b', 'B')) and len(fields) == 2:
            bits = fields[0][1:]
            values[fields[1]] = None if any(c in bits.lower() for c in 'xz') else int(bits, 2)
        elif fields[0][0] in '01xXzZ':
            values[fields[0][1:]] = None if fields[0][0].lower() in 'xz' else int(fields[0][0])
    snapshots[time] = dict(values)
    return identities, widths, snapshots


def check_wave(case, manifest, rows, start, length, fault=None):
    path = case / ('replay.vcd' if fault is None else 'fault-' + fault + '.vcd')
    ids, widths, snapshots = waveform(path)
    root = 'event_replay_tb.'
    clocks = {c: root + c[len(manifest['dut_root']) + 1:] for c in manifest['clock_inputs']}
    words = list(state_words(manifest))
    def value(time, name):
        require(name in ids, 'missing native waveform owner ' + name)
        return snapshots[max(t for t in snapshots if t <= time)].get(ids[name])
    for i, word in enumerate(words):
        probe = root + f'probe_{i:04d}'
        require(widths.get(probe) == word['width'] and
                value(1000, probe) == int(rows[start]['values'][i], 16), 'native waveform complete state readback mismatch')
    require(len({ids[root + f'probe_{i:04d}'] for i in range(len(words))}) == len(words), 'aliased native state probes')
    for time in snapshots:
        if time <= 2000:
            require(all(value(time, port) == 0 for port in clocks.values()), 'actual native edge precedes complete restore')
    for index, row in enumerate(rows[start:start + (length if fault is None else 1)]):
        time = 3000 + index * 3000
        require(all(value(time, clocks[c]) == level for c, level in row['before'].items()),
                'native sample is not at its captured event phase')
        require(value(time, root + 'acknowledged') == index, 'native replay acknowledges an unchecked event')
        mismatches = []
        for direction in ('inputs', 'outputs'):
            for signal, expected in sorted(row[direction].items()):
                if value(time, root + signal) != int(expected['value'], 16):
                    mismatches.append(signal)
        if fault:
            require(sorted(mismatches) == (['crossing', 'out0'] if fault == 'crossing' else ['readData']) and
                    all(value(time, p) == 0 for p in clocks.values()), 'native actual first-divergence fault mismatch')
        else:
            require(not mismatches and value(time, root + 'sampled_event') == row['event_index'],
                    'native waveform outputs/inputs or original event labels disagree')
            for i, word in enumerate(words):
                require(value(time, root + f'probe_{i:04d}') == int(row['values'][i], 16),
                        'native complete continued state differs from original source')
            require(all(value(time + 1000, clocks[c]) == level for c, level in row['clock_levels'].items()),
                    'native clock transition differs from the captured event')


def audit(summary_path):
    out = summary_path.resolve().parent; summary = json.loads(summary_path.read_text())
    require(summary['status'] == 'passed' and summary['artifact_root'] == str(out) and
            not summary['CPU_level1_verified'] and not summary['CPU_level2_verified'] and
            not summary['required_CPU_checkpoint_cuts_tested'], 'component replay misrepresented as CPU acceptance')
    selected = {}
    for original, binding in summary['archived_inputs'].items():
        path = Path(binding['path'])
        require(file_sha(path) == binding['sha256'], 'changed original native source archive')
        selected[Path(original).name] = path
    for name, digest in summary['artifact_sha256'].items():
        require(file_sha(name) == digest, 'changed original native image, waveform or execution evidence')
    def pick(suffix):
        choices = [p for name, p in selected.items() if name.endswith(suffix)]
        require(len(choices) == 1, 'ambiguous original input ' + suffix)
        return choices[0]
    manifest = json.loads(pick('.semantic-state.json').read_text())
    boundary = json.loads(pick('.semantic-boundary.json').read_text())
    access = json.loads(pick('.semantic-clean-access.json').read_text())
    report = audit_inventory(manifest, boundary, pick('.semantic-reference.fir').read_text(),
                             pick('.semantic-clean.sv').read_text(), access)
    words = list(state_words(manifest))
    require(len(words) == 12 and {w['path'] for w in words} ==
            {f's{i}' for i in range(7)} | {f'ram[{i}]' for i in range(4)} | {'ram_r_data'},
            'this independent recurrence covers only the complete original seven-clock component')
    rows = [json.loads(line) for line in (out / 'source/capture.jsonl').read_text().splitlines()]
    require(len(rows) == 192, 'reduced native source execution')
    state = dict.fromkeys([w['path'] for w in words], 0)
    levels = dict.fromkeys(manifest['clock_inputs'], 0); counts = dict(levels)
    simultaneous, mixed, no_cycle_increment = 0, 0, 0
    for index, row in enumerate(rows):
        require(row['event_index'] == index and row['cycle'] == counts[manifest['clock_inputs'][0]] and
                row['before'] == levels and row['values'] == [f"{state[w['path']]:04x}" for w in words],
                'native source state recurrence, completed cycles or event phases disagree')
        inputs = {p: int(v['value'], 16) for p, v in row['inputs'].items()}
        expected = {f'out{i}': state[f's{i}'] for i in range(7)}
        expected.update(crossing=state['s0'] ^ state['s6'], readData=state['ram_r_data'],
                        forwarded=levels[manifest['dut_root'] + '.clock6'])
        require({p: int(v['value'], 16) for p, v in row['outputs'].items()} == expected, 'native original output recurrence disagrees')
        rising = {c for c in levels if levels[c] == 0 and row['clock_levels'][c] == 1}
        falling = {c for c in levels if levels[c] == 1 and row['clock_levels'][c] == 0}
        simultaneous += int(len(rising) > 1); mixed += int(bool(rising and falling))
        no_cycle_increment += int(manifest['clock_inputs'][0] not in rising)
        next_state = dict(state)
        for i in range(7):
            clock = manifest['dut_root'] + f'.clock{i}'
            if clock in rising:
                operand = state[f's{i - 1}'] if i in (1, 3, 5, 6) else inputs['data']
                next_state[f's{i}'] = 0 if inputs['reset'] else (state[f's{i}'] + operand) & 65535
                counts[clock] += 1
        if manifest['clock_inputs'][0] in rising:
            address = f"ram[{inputs['address']}]"
            next_state['ram_r_data'] = state[address]
            if inputs['wen']:
                next_state[address] = inputs['data']
        state, levels = next_state, dict(row['clock_levels'])
    require(simultaneous and mixed and no_cycle_increment and all(counts.values()), 'missing staggered/simultaneous independent clock activity')
    pids = []
    def native_log(path, argv=None, exit_code=0):
        text = path.read_text()
        require(_toolchain.VCS_VERSION in text and text.rstrip().endswith('exit=' + str(exit_code)), 'missing actual native VCS execution')
        if argv is not None:
            require(json.loads(text.split('argv=', 1)[1].splitlines()[0]) == argv, 'changed original native argv')
        pid = re.findall(r'fresh_process_pid=(\d+)', text)
        require(len(pid) == 1, 'missing native process identity'); pids.append(int(pid[0]))
        return text
    native_log(out / 'source/build.log', summary['source_build'])
    native_log(out / 'source/run.log', summary['source_argv'])
    require([c['first_event'] for c in summary['cuts']] == [0, 12, 80, 164], 'reduced component cuts')
    rtl_build, trace_build = builds(manifest, boundary, 'seven-clock-component')
    samples = 0
    for cut in summary['cuts']:
        case = Path(cut['directory']); start = cut['first_event']; length = cut['samples']
        ckpt = decode_semantic((case / 'capture.rtlckpt').read_bytes(), rtl_build, manifest)
        trace = decode((case / 'capture.trace').read_bytes(), 'trace', trace_build)
        require(ckpt['event_phase'] == trace['event_phase'] and ckpt['target_cycle'] == rows[start]['cycle'] and
                [value for record in ckpt['records'] for value in record['values']] == rows[start]['values'],
                'original component image did not capture all actual source words')
        require(trace['records'] == [{k: row[k] for k in ('event_index', 'cycle', 'clock_levels', 'inputs', 'outputs')}
                                     for row in rows[start:start + length]], 'trace does not contain actual captured event rows')
        for c in manifest['clock_inputs']:
            preceding = rows[:start]
            require(ckpt['event_phase']['rising_edges'][c] == sum(row['before'][c] == 0 and row['clock_levels'][c] == 1 for row in preceding),
                    'checkpoint lost an independent clock count')
        build = cut['build_command']
        require(build[0] == _toolchain.VCS and '-full64' in build and
                build[build.index('-cc') + 1] == _toolchain.CC and build[build.index('-cpp') + 1] == _toolchain.CXX,
                'incompatible native compiler configuration')
        native_log(case / 'build.log', build)
        text = native_log(case / 'run.log', cut['argv'])
        require(f'ZERO_EDGE_READBACK words=12 edges=0' in text and
                re.findall(r'MATCH event=(\d+) cycle=(\d+) outputs=10', text) ==
                [(str(r['event_index']), str(r['cycle'])) for r in rows[start:start + length]],
                'native replay output coverage/cycle labels disagree')
        bench = (case / 'replay.sv').read_text()
        for i, line in enumerate((case / 'restore.txt').read_text().splitlines()):
            path, width, value = line.split()
            require(f'wire [{int(width) - 1}:0] probe_{i:04d} = {path};' in bench and value == rows[start]['values'][i],
                    'native state probe/restore oracle not bound to actual word')
        check_wave(case, manifest, rows, start, length)
        samples += length
    require({f['signal'] for f in summary['faults']} == {'crossing', 'readData'} and len(summary['faults']) == 2, 'reduced native corruptions')
    for fault in summary['faults']:
        text = native_log(Path(fault['log']), exit_code=1)
        require(f'DIVERGENCE event=80 cycle=23 signal={fault["signal"]}' in text and 'acknowledged=0' in text and
                'MATCH event=' not in text and 'RESTORE_VERIFY: matched 12' in text, 'wrong first divergent native boundary')
        check_wave(Path(fault['directory']), manifest, rows, 80, 48, fault['signal'])
    require(len(summary['invalid_images']) == 7 and len(summary['native_invalid']) == 4, 'reduced invalid image/loader checks')
    for case in summary['native_invalid']:
        text = native_log(Path(case['log']))
        require('RESTORE: deposited' not in text and 'PASS: invalid loader preserved complete baseline edges=0' in text,
                'invalid native load partially changed state')
    for name in ('waveform-rerun.log', 'waveform-final.log'):
        native_log(out / 'cut-80' / name)
    require(len(set(pids)) == len(pids), 'native processes were reused')
    return dict(report, scope='independent ordinary RTL component capture/replay audit; CPU workload acceptance pending',
                samples=samples, output_comparisons=samples * 10, complete_state_comparisons=samples * 12,
                distinct_native_processes=len(pids), simultaneous_rising_events=simultaneous,
                mixed_rising_falling_events=mixed, events_without_cycle_clock_rise=no_cycle_increment)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.summary), indent=2))


if __name__ == '__main__':
    main()
