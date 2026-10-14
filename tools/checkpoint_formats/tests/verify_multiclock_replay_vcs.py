"""Native seven-clock ordinary RTL capture and fresh-process finite replay.

Component evidence only: no FAME mapping, metasim coherent cut or CPU workload
acceptance is claimed. Source both environments and vcs-env.sh LAST.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile

from tools.checkpoint_formats.codec import FormatError, decode, encode, require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.multiclock_inventory import access_paths, audit_inventory
from tools.checkpoint_formats.multiclock_replay import package_capture, ports_with_aliases, prepare_replay
from tools.checkpoint_formats.replay import builds, state_words
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


CUTS = (0, 12, 80, 164)


def schedule():
    result = []
    for group in range(48):
        a = (1 << (group % 7)) | (1 << ((group + 2) % 7))
        b = 127 ^ a
        for mask in ([a, 127, b, 0] if group % 2 == 0 else [a, b, 127, 0]):
            result.append(dict(mask=mask, reset=int(group < 2), data=(group * 773 + len(result) * 13 + 1) & 65535,
                               address=group % 4, wen=int(group % 3 != 1)))
    return result


def capture_bench(manifest, boundary, clean, access, out):
    clocks = manifest['clock_inputs']; root = manifest['dut_root']
    names = [c[len(root) + 1:] for c in clocks]
    require(names == ['clock' + str(i) for i in range(7)], 'this native component workload requires its seven-clock fixture')
    ports = ports_with_aliases(manifest, boundary)
    require({p['name'] for p in ports if p['direction'] == 'input'} == {'reset', 'data', 'address', 'wen'},
            'this component workload is not a CPU workload')
    paths = access_paths(manifest, boundary, clean, access)
    words = list(state_words(manifest))
    for word in words:
        word['path'] = paths[word['state_id']] + (f"[{word['address']}]" if '[' in word['path'] else '')
    source = ['`timescale 1ns/1ps', 'module event_source_tb;',
              'integer fd; longint unsigned cycle = 0;',
              'import "DPI-C" context function void semantic_fail(input string message);']
    for name in names:
        source += [f'reg {name} = 0;']
    source += ['always @(posedge clock0) cycle = cycle + 1;']
    for port in ports:
        source += [f"{'reg' if port['direction'] == 'input' else 'wire'} [{port['width'] - 1}:0] {port['name']}" +
                   (' = 0;' if port['direction'] == 'input' else ';')]
    pins = names + [p['name'] for p in ports]
    source += [boundary['dut_module'] + ' dut(' + ', '.join(f'.{n}({n})' for n in pins) + ');', 'initial begin',
               f'  fd = $fopen("{out / "capture.jsonl"}", "w");',
               '  if (!fd) semantic_fail("CAPTURE_OPEN_ERROR");', '  #1;']
    for event, stimulus in enumerate(schedule()):
        for name in ('reset', 'data', 'address', 'wen'):
            source += [f'  {name} = {stimulus[name]};']
        source += ['  #1;']
        before = '{' + ','.join(json.dumps(c) + ':%0d' for c in clocks) + '}'
        next_levels = {c: (stimulus['mask'] >> i) & 1 for i, c in enumerate(clocks)}
        fmt = '{"event_index":' + str(event) + ',"cycle":%0d,"before":' + before + ',"clock_levels":' + json.dumps(next_levels)
        values = ['cycle'] + names
        for direction in ('input', 'output'):
            fmt += ',"' + direction + 's":{' + ','.join(json.dumps(p['name']) + ':{"width":' +
                      str(p['width']) + ',"value":"%h"}' for p in ports if p['direction'] == direction) + '}'
            values += [p['name'] for p in ports if p['direction'] == direction]
        fmt += ',"values":[' + ','.join('"%h"' for w in words) + ']}'
        values += ['dut.' + w['path'] for w in words]
        source += ['  $fdisplay(fd, ' + json.dumps(fmt) + ', ' + ', '.join(values) + ');', '  $fflush(fd);',
                   '  {' + ', '.join(names) + "} = 7'b" + ''.join(str(next_levels[c]) for c in clocks) + ';', '  #1;']
    source += ['  $fclose(fd); $display("PASS: complete seven-clock source capture events=192"); $finish;', 'end', 'endmodule']
    path = out / 'source.sv'; path.write_text('\n'.join(source) + '\n')
    return path


def compile_native(out, clean, bench, top):
    command = [Path(os.environ['VCS_HOME']) / 'bin/vcs', '-full64', '-sverilog', '-debug_access+all', '+vpi',
               '+vcs+initreg+random', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-CFLAGS',
               '-std=c++17 -I' + os.environ['VCS_HOME'] + '/include', '-timescale=1ns/1ps', '-top', top,
               '-Mdir=' + str(out / 'csrc'), '-o', out / 'simv', clean, bench,
               ROOT / 'tools/checkpoint_formats/semantic_restore.cc']
    run(command, out / 'build.log')
    return [str(a) for a in command]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    temporary = out / 'vcs-tmp'; temporary.mkdir(); os.environ['TMPDIR'] = str(temporary)
    inputs = {k: Path(str(args.base.resolve()) + '.semantic-' + suffix) for k, suffix in
              [('manifest', 'state.json'), ('boundary', 'boundary.json'), ('reference', 'reference.fir'),
               ('clean', 'clean.sv'), ('access', 'clean-access.json')]}
    manifest = json.loads(inputs['manifest'].read_text()); boundary = json.loads(inputs['boundary'].read_text())
    clean = inputs['clean'].read_text(); access = json.loads(inputs['access'].read_text())
    report = audit_inventory(manifest, boundary, inputs['reference'].read_text(), clean, access)
    source = out / 'source'; source.mkdir()
    bench = capture_bench(manifest, boundary, clean, access, source)
    source_build = compile_native(source, inputs['clean'], bench, 'event_source_tb')
    source_argv = [source / 'simv', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0']
    run(source_argv, source / 'run.log')
    rows = [json.loads(line) for line in (source / 'capture.jsonl').read_text().splitlines()]
    cuts, faults, negatives, native_invalid = [], [], [], []
    for start in CUTS:
        case = out / ('cut-' + str(start))
        data, trace = package_capture(manifest, boundary, 'seven-clock-component', rows, start,
                                      min(48, len(rows) - start), manifest['clock_inputs'][0])
        stats = prepare_replay(manifest, boundary, 'seven-clock-component', clean, access, data, trace, case)
        (case / 'capture.rtlckpt').write_bytes(data); (case / 'capture.trace').write_bytes(trace)
        # Actual waveform observations are separate from the generated assertions.
        bench = case / 'replay.sv'
        source_text = bench.read_text().replace('initial begin\n', 'initial begin\n  $dumpfile("' +
                                                 str(case / 'replay.vcd') + '"); $dumpvars(0, event_replay_tb);\n', 1)
        # VCS does not include memory words in ordinary $dumpvars. Direct
        # continuous probes expose *every* stored word to an independent reader.
        for index, line in enumerate((case / 'restore.txt').read_text().splitlines()):
            path, width, _ = line.split()
            source_text = source_text.replace('initial begin\n',
                          f'wire [{int(width) - 1}:0] probe_{index:04d} = {path};\ninitial begin\n', 1)
        if start == 80:
            mapping = access_paths(manifest, boundary, clean, access)
            s0 = next(e for e in manifest['state'] if e['hierarchy'] == manifest['dut_root'] + '.s0')
            memory_pipe = next(e for e in manifest['state'] if e['hierarchy'].endswith('.ram_r_data'))
            fault_source = '\n'.join(f'  if ($test$plusargs("fault={name}")) dut.{mapping[e["state_id"]]} = dut.{mapping[e["state_id"]]} ^ 16\'h1;'
                                     for name, e in [('crossing', s0), ('readData', memory_pipe)])
            source_text = source_text.replace('  // POST_READBACK_FAULT_INSERTION', '  // POST_READBACK_FAULT_INSERTION\n' + fault_source)
            baseline = case / 'initial-baseline.txt'
            baseline.write_text('\n'.join(' '.join(line.split()[:2]) + ' ' + '0' * len(line.split()[2])
                                          for line in (case / 'restore.txt').read_text().splitlines()) + '\n')
            source_text = source_text.replace('initial begin\n', 'string invalid_file;\ninitial begin\n', 1)
            branch = ['  if ($value$plusargs("invalid=%s", invalid_file)) begin',
                      f'    if (!semantic_restore(invalid_file, {stats["words"]})) semantic_fail("INVALID_LOADER_ACCEPTED");',
                      f'    if (semantic_verify("{baseline}", {stats["words"]})) semantic_fail("PARTIAL_INVALID_DEPOSIT");',
                      '    if (edges || clock0 || clock1 || clock2 || clock3 || clock4 || clock5 || clock6) semantic_fail("INVALID_LOAD_ADVANCED_CLOCK");',
                      '    $display("PASS: invalid loader preserved complete baseline edges=0"); $finish;', '  end']
            source_text = source_text.replace('  if (semantic_restore(', '\n'.join(branch) + '\n  if (semantic_restore(', 1)
        # Flush every sampled boundary, including expected failing exits.
        source_text = source_text.replace('  #1;\n  if (', '  #1; $dumpflush;\n  if (')
        bench.write_text(source_text)
        build_command = compile_native(case, inputs['clean'], bench, 'event_replay_tb')
        argv = [case / 'simv', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0']
        log = run(argv, case / 'run.log')
        require(f'PASS: event replay samples={stats["samples"]}' in log and log.count('MATCH event=') == stats['samples'],
                'native event replay incomplete')
        cuts.append(dict(stats, directory=str(case), build_command=build_command, argv=[str(a) for a in argv]))
        if start == 80:
            for signal in ('crossing', 'readData'):
                log = run(argv + ['+fault=' + signal], case / ('fault-' + signal + '.log'), expected=None)
                require(f'DIVERGENCE event=80 cycle={stats["first_target_cycle"]} signal={signal}' in log and
                        'acknowledged=0' in log and 'MATCH event=' not in log, 'fault did not fail at its first boundary')
                shutil.move(case / 'replay.vcd', case / ('fault-' + signal + '.vcd'))
                faults.append(dict(event_index=80, cycle=stats['first_target_cycle'], signal=signal, directory=str(case),
                                   log=str(case / ('fault-' + signal + '.log'))))
            # Retain an uncorrupted waveform after fault runs, from a new process.
            run(argv, case / 'waveform-rerun.log')
            lines = (case / 'restore.txt').read_text().splitlines()
            for name, bad in [('missing-word', lines[:-1]), ('duplicate-word', lines[:-1] + [lines[0]]),
                              ('unknown-word', lines[:-1] + ['event_replay_tb.dut.unknown 16 0000']),
                              ('wrong-width', lines[:-1] + [lines[-1].split()[0] + ' 17 00000'])]:
                invalid = case / (name + '.txt'); invalid.write_text('\n'.join(bad) + '\n')
                logpath = case / (name + '.log')
                log = run(argv + ['+invalid=' + str(invalid)], logpath)
                require('PASS: invalid loader preserved complete baseline edges=0' in log and
                        'RESTORE: deposited' not in log, 'invalid native load changed storage')
                native_invalid.append(dict(name=name, directory=str(case), log=str(logpath)))
            # Invalid runs deliberately use their own zero baseline. Restore the
            # valid native waveform so it remains paired with its original trace.
            run(argv, case / 'waveform-final.log')
    case = Path(cuts[2]['directory'])
    data = (case / 'capture.rtlckpt').read_bytes(); trace = (case / 'capture.trace').read_bytes()
    rtl_build, trace_build = builds(manifest, boundary, 'seven-clock-component')
    good = decode(data, 'rtlckpt', rtl_build)
    variants = [('truncated', data[:-1], trace)]
    broken = bytearray(data); broken[-1] ^= 1; variants.append(('checksum', bytes(broken), trace))
    for name, mutate in [('incompatible-build', lambda d: d['build'].update(rtl_build_hash='f' * 64)),
                         ('missing-owner', lambda d: d['records'].pop()),
                         ('unknown-owner', lambda d: d['records'][0].update(state_id='0' * 64)),
                         ('missing-clock', lambda d: (d['event_phase']['clock_levels'].pop(manifest['clock_inputs'][0]),
                                                     d['event_phase']['rising_edges'].pop(manifest['clock_inputs'][0]),
                                                     d['event_phase'].update(cycle_clock=manifest['clock_inputs'][1]),
                                                     d.update(target_cycle=d['event_phase']['rising_edges'][manifest['clock_inputs'][1]])))] :
        bad = copy.deepcopy(good); mutate(bad); bad['records'].sort(key=lambda r: r['state_id'])
        variants.append((name, encode('rtlckpt', bad), trace))
    bad_trace = decode(trace, 'trace', trace_build)
    bad_trace['records'][1]['outputs'].pop('out3')
    variants.append(('missing-output', data, encode('trace', bad_trace)))
    for name, bad_data, bad_trace_data in variants:
        reject = out / ('reject-' + name)
        try:
            prepare_replay(manifest, boundary, 'seven-clock-component', clean, access, bad_data, bad_trace_data, reject)
        except FormatError as exc:
            require(not reject.exists(), 'invalid image partially published a loader/bench')
            negatives.append(dict(name=name, error=str(exc)))
        else:
            raise AssertionError('invalid image accepted: ' + name)
    archive = out / 'inputs'; archive.mkdir()
    archived = {}
    paths = list(inputs.values()) + [Path(__file__).resolve(), ROOT / 'tools/checkpoint_formats/multiclock_replay.py',
             ROOT / 'tools/checkpoint_formats/codec.py', ROOT / 'tools/checkpoint_formats/semantic.py',
             ROOT / 'tools/checkpoint_formats/multiclock_inventory.py', ROOT / 'tools/checkpoint_formats/semantic_restore.cc']
    for index, path in enumerate(paths):
        saved = archive / (f'{index:03d}-' + path.name); shutil.copyfile(path, saved)
        archived[str(path)] = dict(path=str(saved), sha256=file_sha(saved))
    artifacts = [p for p in out.rglob('*') if p.is_file() and p.suffix in ('.jsonl', '.rtlckpt', '.trace', '.vcd', '.sv', '.log', '.txt')]
    summary = dict(report, scope='seven-clock ordinary RTL component capture/fresh replay only; CPU acceptance pending',
                   artifact_root=str(out), source_build=source_build, source_argv=[str(a) for a in source_argv],
                   cuts=cuts, faults=faults, invalid_images=negatives, native_invalid=native_invalid, archived_inputs=archived,
                   artifact_sha256={str(p): file_sha(p) for p in artifacts},
                   required_CPU_checkpoint_cuts_tested=False, CPU_level1_verified=False, CPU_level2_verified=False)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(status='passed', summary=str(out / 'summary.json'), samples=sum(c['samples'] for c in cuts),
                          zero_edge_words=report['semantic_words'], faults=len(faults), invalid_images=len(negatives)), indent=2))


if __name__ == '__main__':
    main()
