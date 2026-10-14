"""Actual TracerV host-owner capture and fresh VCS/native continuations.

An independent byte/MMIO oracle uses all four exact Rocket constructor settings.
Fixture stream queues are separate owners. This cannot certify a CPU restore.
Every build/runtime VCS shell sources vcs-env.sh last; every invocation is fresh.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import check_native_input
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run

TESTS = Path(__file__).resolve().parent
CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
BRIDGES = ROOT / 'generators/firechip/bridgestubs/src/main/cc'
ENVIRONMENT = ('source ' + shlex.quote(str(ROOT / 'env.sh')) + ' && source ' +
               shlex.quote(str(ROOT / 'sims/firesim/env.sh')) + ' && source ' +
               shlex.quote(str(ROOT / 'automations/checkpoint_loop/vcs-env.sh')) + ' && ')
FIELDS = ('initDone traceEnable hostTriggerPCStartHigh hostTriggerPCStartLow '
          'hostTriggerPCEndHigh hostTriggerPCEndLow hostTriggerCycleCountStartHigh '
          'hostTriggerCycleCountStartLow hostTriggerCycleCountEndHigh hostTriggerCycleCountEndLow '
          'hostTriggerStartInst hostTriggerStartInstMask hostTriggerEndInst hostTriggerEndInstMask triggerSelector').split()
SENTINEL = b'SAFE'


def words(*values):
    return struct.pack('<' + 'Q' * len(values), *values)


def constructors(header):
    regex = (r'registry.add_widget\(new tracerv_t\(\s*simif,\s*\*registry.get_stream_engine\(\),\s*'
             r'TRACERVBRIDGEMODULE_struct\{(.*?)\},\s*(\d+),\s*args\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*'
             r'ClockInfo\{R"ESC\((.*?)\)ESC",\s*(\d+),\s*(\d+)\}\s*\)\);')
    matches = re.findall(regex, header, re.S)
    require(len(matches) == 4, 'complete four-hart constructor inventory required')
    result = []
    for h, (raw, hart, stream, depth, ipc, clock, mult, div) in enumerate(matches):
        pairs = re.findall(r'\.(\w+)\s*=\s*(\d+)\s*,', raw)
        require([p[0] for p in pairs] == FIELDS, 'missing/unknown TracerV MMIO field')
        addresses = [int(p[1]) for p in pairs]
        require((int(hart), int(stream), int(depth), int(ipc), int(mult), int(div)) == (h, h, 6144, 1, 1, 1)
                and addresses == list(range(640+64*h, 700+64*h, 4))
                and clock == 'clock_1000.0MHz,harnessbinder_clock,reference', 'changed Rocket settings: audit explicitly')
        result.append(dict(mmio=addresses, hart=h, stream=h, depth=int(depth), ipc=int(ipc),
                           clock=clock, multiplier=int(mult), divisor=int(div)))
    return result


def configuration(c, mode):
    values = [*c['mmio'], c['stream'], c['depth'], c['ipc'], c['multiplier'], c['divisor'],
              int(mode != 3), int(mode in (0, 2)), int(mode == 2), 12345678, 0,
              0x12345678, 0, 0xabcdef01, 0, mode, 0x12345678, 0xabcdef01]
    require(len(values) == 32, 'incomplete independently owned TracerV fields')
    clock = c['clock'].encode()
    return words(0x3154504b43474457, 1, 12, 32, *values) + words(len(clock)) + clock


def oracle(c, mode):
    header = f"# Clock Domain: {c['clock']}, Relative Frequency: {c['multiplier']}/{c['divisor']} of Base Clock\n".encode()
    output = bytearray(header if mode != 3 else b'')
    queue, trace, states = bytearray(), [], []
    initialized = 0

    def snapshot():
        return configuration(c, mode) + words(initialized, 0, len(output)) + output, bytes(queue)

    def pull(minimum):
        count = min(c['depth']*64, len(queue))
        if count < minimum:
            count = 0
        tokens = bytes(queue[:count]); del queue[:count]
        trace.append(f"P {c['depth']*64} {minimum} {count} {tokens.hex()}")
        for i in range(0, count, 64):
            beat = struct.unpack('<8Q', tokens[i:i+64])
            if mode == 2:
                output.extend((''.join(f'{v:016x}' for v in reversed(beat))+'\n').encode())
            elif mode == 0:
                output.extend(f'Cycle: {beat[0]:016d} I0: {beat[1] & ((1<<63)-1):016x}\n'.encode())
            else:
                output.extend(tokens[i:i+16])
        return count

    def flush():
        trace.append('F')
        if mode != 3:
            while pull(0):
                pass

    for op in range(8):
        states.append(snapshot())
        trace.append(f'OP {op} C {100+7*op}')
        if op == 0:
            a = c['mmio']
            if mode == 3:
                trace.append(f'W {a[1]} 0')
            trace.append(f'W {a[14]} {mode}')
            if mode == 1:
                trace.extend(f'W {a[i]} {v}' for i, v in ((6,0),(7,12345678),(8,0),(9,0)))
            elif mode == 2:
                trace.extend(f'W {a[i]} {v}' for i, v in ((2,0),(3,0x12345678),(4,0),(5,0xabcdef01)))
            elif mode == 3:
                trace.extend(f'W {a[i]} {v}' for i, v in ((10,0x12345678),(11,0),(12,0xabcdef01),(13,0)))
            trace.append(f'W {a[0]} 1')
            initialized = 1
        elif op == 7:
            flush()
            trace.append('OUTPUT ' + (bytes(output) if mode != 3 else SENTINEL).hex())
        elif op == 4:
            flush()
        else:
            count = c['depth']-1 if op == 1 else 1 if op in (2,5) else 2 if op == 3 else 0
            for t in range(count):
                queue.extend(words(100+7*op, (1<<63) | (0x80000000+4096*c['hart']+4*t),0,0,0,0,0,0))
            if mode != 3:
                pull(c['depth']*64)
    return trace, states, bytes(output) if mode != 3 else SENTINEL


def audit_case(case, c, mode):
    trace, states, output = oracle(c, mode)
    require((case / 'reference.trace').read_text().splitlines() == trace, 'independent complete TracerV I/O mismatch')
    require((case / f'TRACEFILE-C{c["hart"]}').read_bytes() == output, 'complete output prefix mismatch')
    for cut, (owner, queue) in enumerate(states):
        for suffix, value in (('owner', owner), ('queue', queue)):
            for name in (f'cut-{cut}.{suffix}', f'restore-{cut}.initial.{suffix}'):
                require((case / name).read_bytes() == value, 'complete zero-edge owner/queue mismatch ' + name)
            require((case / f'restore-{cut}.final.{suffix}').read_bytes() == states[-1][int(suffix == 'queue')],
                    'complete final owner/queue mismatch')
        actual = (case / f'restore-{cut}.trace').read_text().splitlines()
        require(actual == trace[trace.index(f'OP {cut} C {100+7*cut}'):], 'TracerV first changed boundary')
    return dict(hart=c['hart'], mode=mode, cuts=8, output_bytes=len(output),
                queued_bytes_at_cuts=[len(q) for _, q in states])


def audit(summary_path):
    path = Path(summary_path).resolve()
    report = json.loads(path.read_text())
    require(report['status'] == 'passed' and report['artifact_root'] == str(path.parent) and
            not report['level1_verified'] and not report['level2_verified'], 'incomplete/falsely authorized result')
    catalog = report['artifacts_sha256']
    require(set(catalog) == {str(p) for p in path.parent.rglob('*') if p.is_file() and p != path}, 'missing/extra native evidence')
    for name, digest in catalog.items():
        require(file_sha(name) == digest, 'changed original native evidence ' + name)
    bindings = {b['path']: b for b in report['source_inputs']}
    for b in bindings.values():
        require(file_sha(b['snapshot']) == b['sha256'], 'changed original source snapshot')
        check_native_input(ROOT, b['path'], b['sha256'], bindings)
    for backend in report['backends']:
        require(len(backend['cases']) == 16, 'missing complete four-hart modes')
        for case in backend['cases']:
            audit_case(path.parent / backend['backend'] / f'hart-{case["hart"]}-mode-{case["mode"]}',
                       report['constructors'][case['hart']], case['mode'])
    commands = report['commands']
    require(len(commands) == 296 and len({c['pid'] for c in commands}) == len(commands), 'incomplete/reused native processes')
    for c in commands:
        log = Path(c['log']).read_text()
        require(log.rstrip().endswith('exit='+str(c['expected_exit'])) and
                c['argv'][:2] == ['bash', '-lc'] and c['argv'][-1].startswith(ENVIRONMENT), 'unbound native command/environment')
    return dict(status='passed', summary=str(path), fresh_continuations=256, native_processes=len(commands),
                level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rocket-header', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit), indent=2)); return
    require(args.rocket_header is not None and args.out is not None, 'out/header required')
    require(os.environ['VCS_HOME'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1' and os.environ['CXX'] == '/usr/bin/g++-13',
            'source vcs-env.sh LAST')
    args.out.resolve().mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    settings = constructors(args.rocket_header.read_text())
    generated = out / 'tracerv-recipe.h'
    generated.write_text('const TRACERVBRIDGEMODULE_struct recipe_mmio[4] = {\n' + ',\n'.join(
        '{'+','.join(map(str,c['mmio']))+'}' for c in settings) + '\n};\n' +
        'const unsigned recipe_depth=6144, recipe_ipc=1;\n' +
        'const ClockInfo recipe_clock{"'+settings[0]['clock']+'",1,1};\n')
    sources = [TESTS / 'tracerv_checkpoint.cc', CC / 'core/widget.cc', CC / 'core/bridge_driver.cc',
               CC / 'core/stream_engine.cc', BRIDGES / 'bridges/tracerv.cc',
               *sorted((BRIDGES / 'bridges/tracerv').glob('*.cc'))]
    inputs = [*sources, *sorted((BRIDGES / 'bridges/tracerv').glob('*.h')), BRIDGES / 'bridges/tracerv.h',
              TESTS / 'tracerv_checkpoint_tb.sv', Path(__file__), args.rocket_header.resolve(),
              *[CC / 'core' / n for n in ('widget_checkpoint.h','checkpoint.h','bridge_driver.h','clock_info.h',
                                        'stream_engine.h','widget.h','config.h','simif.h')]]
    snapshots = out / 'source-snapshots'; snapshots.mkdir()
    bindings = []
    for p in inputs:
        digest = file_sha(p); snapshot = snapshots / digest
        if not snapshot.exists(): shutil.copyfile(p, snapshot)
        bindings.append(dict(path=str(p), snapshot=str(snapshot), sha256=digest))
    commands = []
    def execute(argv, log, expected=0):
        command = ['bash', '-lc', ENVIRONMENT + shlex.join([str(a) for a in argv])]
        text = run(command, log, cwd=out, expected=expected)
        pid = int(re.search(r'fresh_process_pid=(\d+)', text)[1])
        commands.append(dict(cwd=str(out.relative_to(ROOT)), argv=command, log=str(log), pid=pid, expected_exit=expected))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        return text
    native, simv = out / 'tracerv-native', out / 'tracerv-simv'
    include = f'-std=c++17 -I{CC} -I{BRIDGES} -I{out} -isystem {os.environ["CONDA_PREFIX"]}/include'
    libs = ['-Wl,--no-as-needed', '-L'+os.environ['CONDA_PREFIX']+'/lib', '-ldwarf', '-lelf', '-lz']
    execute([os.environ['CXX'], *shlex.split(include), '-Wall', '-Wextra', '-Wno-unused-parameter', '-Werror',
             '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', *sources, *libs, '-o', native], out / 'native-build.log')
    execute([Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
             '-top', 'tracerv_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
             f'-Mdir={out / "csrc"}', '-CFLAGS', include+' -DTRACERV_CHECKPOINT_DPI',
             '-LDFLAGS', shlex.join(libs), '-o', simv, TESTS / 'tracerv_checkpoint_tb.sv', *sources], out / 'vcs-build.log')
    results = []
    for backend in ('native-sanitized', 'vcs-dpi'):
        base = out / backend; base.mkdir()
        def invoke(mode, cut, scenario, hart, case, expected=0):
            argv = [native, mode, case, cut, scenario, hart] if backend == 'native-sanitized' else [
                simv, '-no_save', f'+outdir={case}', f'+restore={int(mode=="restore")}', f'+cut={cut}',
                f'+mode={scenario}', f'+hart={hart}', *(['+negative'] if mode=='negative' else [])]
            text = execute(argv, case / f'{mode}-{cut}.log', expected)
            if backend == 'vcs-dpi' and expected == 0 and mode != 'negative':
                require('TRACERV_READBACK edges=0' in text and 'PASS: fresh tracerv component continuation' in text,
                        'missing VCS zero-edge complete readback/continuation')
            return text
        cases = []
        for h, c in enumerate(settings):
            for mode in range(4):
                case = base / f'hart-{h}-mode-{mode}'; case.mkdir()
                invoke('reference', 0, mode, h, case)
                output = oracle(c, mode)[2]
                for cut in range(8):
                    invoke('restore', cut, mode, h, case)
                    require((case / f'TRACEFILE-C{h}').read_bytes() == output, 'fresh prefix/continuation output mismatch')
                cases.append(audit_case(case, c, mode))
        positive = base / 'hart-0-mode-0'
        negative = invoke('negative', 0, 0, 0, positive)
        count = re.search(r'PASS: TracerV atomic payload/configuration/lifecycle checks (\d+)', negative)
        require(count is not None, 'missing native invalid/lifecycle checks')
        # Valid but corrupted lifecycle state skips init MMIO at the first boundary.
        fault = base / 'actual-lifecycle-fault'; fault.mkdir()
        bad = bytearray(oracle(settings[0],0)[1][0][0]); bad[len(configuration(settings[0],0))] = 1
        (fault / 'cut-0.owner').write_bytes(bad); (fault / 'cut-0.queue').write_bytes(b'')
        shutil.copyfile(positive / 'reference.trace', fault / 'reference.trace')
        # This fault is detected by lifecycle rejection before executing init MMIO.
        text = invoke('restore',0,0,0,fault,1)
        require('unsupported TracerV init lifecycle' in text and
                (fault / 'restore-0.trace').read_text().splitlines()==['OP 0 C 100'], 'corrupt lifecycle acknowledged a boundary')
        # Actual valid captured history corruption reaches its first visible output at finish.
        fault = base / 'actual-output-fault'; fault.mkdir()
        owner, queue = oracle(settings[0],0)[1][3]
        bad = bytearray(owner); bad[-2] ^= 1
        (fault / 'cut-3.owner').write_bytes(bad); (fault / 'cut-3.queue').write_bytes(queue)
        shutil.copyfile(positive / 'reference.trace', fault / 'reference.trace')
        text = invoke('restore',3,0,0,fault,1)
        require('FIRST_MISMATCH fixture_cycle=149 signal=tracerv_output' in text, 'missed first corrupted output boundary')
        for case in cases:
            audit_case(base / f'hart-{case["hart"]}-mode-{case["mode"]}',settings[case['hart']],case['mode'])
        results.append(dict(backend=backend, cases=cases, negative_assertions=int(count[1]),
                            first_actual_output_corruption_fixture_cycle=149))
    for b in bindings:
        require(file_sha(b['path']) == b['sha256'], 'source changed during native execution')
    summary = dict(status='passed', artifact_root=str(out), scope='TracerV host component; separate fixture token queues',
                   constructors=settings, source_inputs=bindings, commands=commands, backends=results,
                   level1_verified=False, level2_verified=False,
                   artifacts_sha256={str(p):file_sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (args.out.resolve() / 'latest.json').write_text(json.dumps(dict(summary=str(out / 'summary.json')))+'\n')
    print(json.dumps(audit(out / 'summary.json'), indent=2))


if __name__ == '__main__':
    main()
