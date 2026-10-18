"""Independent deadlines/phase/returned-service oracle; no CPU acceptance."""
import argparse
import json
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha


def words(*values):
    return struct.pack('<' + 'Q' * len(values), *values)


def text(value):
    b = value.encode()
    return words(len(b)) + b


def oracle(scenario):
    phase = index = stopped = code = cycle = remaining = ordinal = 0
    deadlines = [0, 0]
    states, events = [], []
    while True:
        scheduler = words(0x3154504b43484353, 1, 1, 20, 0xffffffff, cycle, 2)
        for name, deadline in zip(('a', 'b'), deadlines):
            scheduler += text(name) + text('test.stateless-callback.v1') + words(0, deadline)
        loop = words(0x3154504b434c5242, 1, 3, phase, index, stopped, code & 0xffffffff)
        states.append((scheduler, loop, bytes([remaining])))
        if phase == 7:
            break

        def emit(message):
            events.append(f'{ordinal} {message}')

        if phase == 0:
            done = cycle == 20
            emit(f'horizon {int(done)}')
            phase = 7 if done else 1
        elif phase == 1:
            emit('tasks')
            for i, period in enumerate((3, 5)):
                if deadlines[i] == cycle:
                    emit(f'task {i}')
                    deadlines[i] += period
            phase = 2
        elif phase == 2:
            next_cycle = min(20, *deadlines)
            emit(f'step {next_cycle - cycle}')
            cycle, remaining, phase = next_cycle, 2, 3
        elif phase == 3:
            remaining -= 1
            emit(f'done {int(remaining == 0)}')
            phase = 0 if remaining == 0 else 4
        elif phase == 4:
            emit(f'tick {index}')
            phase = 5
        elif phase == 5:
            stop = bool(scenario and ordinal >= 30 and index == 1)
            emit(f'terminate {index} {int(stop)}')
            if stop:
                phase = 6
            else:
                index += 1
                if index == 3:
                    index, phase = 0, 3
                else:
                    phase = 4
        elif phase == 6:
            emit(f'status {index} -7')
            stopped, code, index, phase = 1, -7, 0, 7
        ordinal += 1
    return states, events


def cuts(scenario):
    n = len(oracle(scenario)[0]) - 1
    return sorted(set([*range(9), n // 2, n - 1, n]))


MODES = ('restore', 'negative', 'fatal-unsealed', 'fatal-thread', 'fatal-expired',
         'fatal-consumed', 'fatal-stale', 'fatal-legacy')


def audit(path):
    path = Path(path).resolve()
    r = json.loads(path.read_text())
    out = path.parent
    require(r['status'] == 'passed' and r['scope'] == 'production scheduler/bridge-loop; synthetic services' and
            r['CPU_level1_verified'] is False, 'control scope')
    require(json.loads((out / 'source-inputs.json').read_text()) == r['source_inputs'], 'control source receipt')
    for b in r['source_inputs']:
        require(file_sha(b['snapshot']) == b['sha256'], 'control source snapshot')
    require({str(p) for p in out.rglob('*') if p.is_file() and p != path} == set(r['artifact_sha256']),
            'control artifact membership')
    for f, digest in r['artifact_sha256'].items():
        require(file_sha(f) == digest, 'control artifact changed')
    require(json.loads((out / 'commands.json').read_text()) == r['commands'], 'control commands')
    wanted = {(b, s, m, c) for b in ('native', 'vcs-dpi') for s in range(2)
              for m in MODES for c in cuts(s)} | {(b, s, 'reference', 0) for b in ('native', 'vcs-dpi') for s in range(2)}
    require(len(r['cases']) == len(wanted) and
            {(c['backend'], c['scenario'], c['mode'], c['cut']) for c in r['cases']} == wanted,
            'control complete matrix')
    require(len(r['commands']) == len(r['cases']) + 2, 'control build commands')
    comparisons = samples = rejects = preparation = sealing = fatals = continuations = 0
    for c in r['cases']:
        log = Path(c['log']).read_text()
        lines = log.splitlines()
        fatal = c['mode'].startswith('fatal-')
        require(lines[0] == 'cwd=' + str(out) and json.loads(lines[1][5:]) == c['argv'] and
                lines[2].startswith('fresh_process_pid=') and lines[-1] == ('exit=86' if fatal else 'exit=0'),
                'control native process receipt')
        require('source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in
                c['argv'][2], 'control environment')
        require(not any(s in log for s in ('ERROR: AddressSanitizer', 'runtime error:', 'LeakSanitizer: detected',
                                         'CONTROL_FAIL')), 'control sanitizer/runtime failure')
        dest = Path(c['destination'])
        if fatal:
            require(f'CONTROL_FATAL mode={c["mode"]} unchanged=1 service_calls=0' in log and
                    'CONTROL_PASS' not in log and 'CONTROL_VCS_ZERO_EDGES' not in log and not dest.exists(),
                    'control fatal publication guard')
            fatals += 1
            continue
        if c['backend'] == 'vcs-dpi':
            require('CONTROL_VCS_ZERO_EDGES time=0 edges=0' in log, 'control VCS zero edges')
        states, events = oracle(c['scenario'])
        if c['mode'] == 'negative':
            match = re.search(r'CONTROL_NEGATIVE rejections=(\d+) prepare_failures=(\d+) seal_failures=(\d+) unchanged=1', log)
            require(match is not None and all(int(v) > 0 for v in match.groups()) and not dest.exists(),
                    'control rejection and exhaustive allocation sweeps')
            # Exact truncations, ten structural invalids and seventeen guard cases.
            require(int(match[1]) == len(states[c['cut']][0]) + len(states[c['cut']][1]) + 27,
                    'control rejection count')
            rejects += int(match[1]); preparation += int(match[2]); sealing += int(match[3])
            continue
        if c['mode'] == 'reference':
            for n, state in enumerate(states):
                for owner in range(2):
                    require((dest / f'state-{n}.{owner}').read_bytes() == state[owner], 'control independent state oracle')
                    comparisons += 1
                require((dest / f'service-{n}').read_bytes() == state[2], 'control fixture service oracle')
            expected = events
        else:
            require(f'CONTROL_PRE_SERVICE_READBACK owners=2 ordinal={c["cut"]} service_calls=0' in log,
                    'control pre-service readback')
            for owner in range(2):
                require((dest / f'initial.{owner}').read_bytes() == states[c['cut']][owner], 'control complete initial state')
                comparisons += 1
            expected = [e for e in events if int(e.split()[0]) >= c['cut']]
            continuations += 1
        require((dest / 'events').read_text().splitlines() == expected, 'control first divergent service boundary')
        for owner in range(2):
            require((dest / f'final.{owner}').read_bytes() == states[-1][owner], 'control complete final state')
            comparisons += 1
        require(f'CONTROL_PASS ordinal={len(states) - 1} terminated={c["scenario"]} exit={-7 if c["scenario"] else 0}' in log,
                'control exact termination')
        samples += len(expected)
    return dict(status='passed',fresh_component_restores=continuations,complete_owner_comparisons=comparisons,
                service_boundaries=samples,rejections=rejects,prepare_allocation_failures=preparation,
                seal_allocation_failures=sealing,fatal_contracts=fatals,CPU_level1_verified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--summary', required=True, type=Path)
    print(json.dumps(audit(p.parse_args().summary), indent=2))


if __name__ == '__main__':
    main()
