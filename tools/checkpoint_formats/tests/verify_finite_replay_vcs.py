"""Standalone DESSERT acceptance with schema-1 and full FCFS schema-2 RTL.

--production selects retained real M6 capture evidence; --fixture selects a
complete freshly run M2 verifier output. Every replay child is ordinary VCS.
Source both repository environments, then vcs-env.sh LAST.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.finite_replay import package_boundary_trace, prepare_finite_replay
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def run(argv, log, cwd, expected=0):
    with log.open('w') as stream:
        stream.write(f'cwd={cwd}\nargv={json.dumps([str(a) for a in argv])}\n')
        stream.flush()
        process = subprocess.Popen([str(a) for a in argv], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        stream.write(f'fresh_process_pid={process.pid}\n')
        stream.flush()
        try:
            code = process.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise
        stream.write(f'exit={code}\n')
    require(code == expected, f'unexpected exit {code}; see {log}')
    return log.read_text()


def audit_waveform(path, manifest, boundary):
    """Audit the ACTUAL converted VPD hierarchy, including every RAM address."""
    prefix = 'finite_replay_tb.dut.'
    entries = {prefix + e['hierarchy'][len(manifest['dut_root'])+1:]: e for e in manifest['state']}
    seen_regs, memories, counts, stack = set(), {}, {}, []
    for name, e in entries.items():
        if e['kind'] == 'memory':
            memories[name] = bytearray((e['depth']+7)//8)
            counts[name] = 0
    ports = {prefix+p['name']: p['width'] for p in boundary['ports']}
    ports.update({prefix+a['name']: 1 for a in boundary.get('clock_aliases', [])})
    seen_ports, declarations, memory_words = set(), 0, 0
    with path.open() as stream:
        for line in stream:
            f = line.split()
            if not f:
                continue
            if f[0] == '$scope':
                stack.append(f[2])
            elif f[0] == '$upscope':
                stack.pop()
            elif f[0] == '$var':
                declarations += 1
                name = '.'.join(stack + [f[4].lstrip('\\')])
                width = int(f[2])
                if name in ports:
                    require(width == ports[name], 'wrong waveform boundary width: ' + name)
                    seen_ports.add(name)
                if name in entries and entries[name]['kind'] == 'register':
                    require(width == entries[name]['width'] and name not in seen_regs,
                            'wrong/duplicate waveform register: ' + name)
                    seen_regs.add(name)
                elif name.endswith(']'):
                    match = re.fullmatch(r'(.*)\[(\d+)\]', name)
                    if match and match[1] in memories:
                        base, address = match[1], int(match[2])
                        e = entries[base]
                        require(width == e['width'] and address < e['depth'], 'wrong waveform memory shape')
                        mask = 1 << (address % 8)
                        require(not memories[base][address//8] & mask, 'duplicate waveform memory word')
                        memories[base][address//8] |= mask
                        counts[base] += 1
                        memory_words += 1
            elif f[0] == '$enddefinitions':
                break
        else:
            require(False, 'missing waveform definitions')
    require(seen_regs == {n for n, e in entries.items() if e['kind'] == 'register'}
            and seen_ports == set(ports)
            and all(counts[n] == entries[n]['depth'] for n in counts), 'incomplete full-visibility waveform')
    return dict(hierarchy_declarations=declarations, registers=len(seen_regs), memory_words=memory_words,
                complete_memories=len(memories), boundary_ports=len(seen_ports),
                semantic_words=len(seen_regs)+memory_words, full_visibility=True)


def verify_case(vcs, case, manifest, boundary, configuration, image, trace, rtl, expected_cycle=None, signal=None):
    metadata = prepare_finite_replay(manifest, boundary, configuration, image, trace, rtl, case)
    build = [vcs/'bin/vcs', '-full64', '-sverilog', '-debug_access+all', '+vpi',
             '-cc', os.environ['CC'], '-cpp', os.environ['CXX'], '-CFLAGS', '-std=c++17',
             '-timescale=1ns/1ps', '-top', 'finite_replay_tb', f'-Mdir={case/"csrc"}', '-o', case/'simv',
             case/'clean.sv', case/'replay.sv', ROOT/'tools/checkpoint_formats/semantic_restore.cc']
    run(build, case/'build.log', case)
    argv = [case/'simv', '-no_save', f'+restore={case/"restore.txt"}', f'+trace={case/"trace.txt"}',
            f'+waveform={case/"replay.vpd"}', f'+audit={case/"matched.txt"}']
    text = run(argv, case/'run.log', case, 0 if expected_cycle is None else 1)
    require(f'RESTORE_VERIFY: matched {metadata["restored_words"]} semantic words before first DUT edge' in text
            and f'FINITE_PRE_EDGE cycle={metadata["first_cycle"]} words={metadata["restored_words"]} target_edges=0' in text,
            'missing full zero-edge semantic readback')
    samples = metadata['samples'] if expected_cycle is None else expected_cycle-metadata['first_cycle']
    with (case/'matched.txt').open() as matched, (case/'trace.txt').open() as original:
        for _ in range(samples):
            row = matched.readline()
            require(row and row == original.readline(), 'replay acknowledged wrong target boundary')
        require(not matched.readline(), 'replay acknowledged a boundary past its stop')
    if expected_cycle is None:
        require(f'PASS: standalone finite replay first={metadata["first_cycle"]} end={metadata["end_cycle"]} '
                f'target_edges={samples}' in text, 'incorrect finite end/edge count')
    else:
        require(re.search(rf'FIRST_MISMATCH cycle={expected_cycle} signal={signal} .*target_edges={samples}\b', text)
                and text.count('FIRST_MISMATCH') == 1 and 'PASS:' not in text,
                'RTL bug did not fail at its first original target cycle')
    require((case/'replay.vpd').stat().st_size > 100, 'missing VPD waveform')
    run([vcs/'bin/vpd2vcd', '-full64', '+includemda', case/'replay.vpd', case/'replay.vcd'],
        case/'conversion.log', case)
    waveform = audit_waveform(case/'replay.vcd', manifest, boundary)
    require(waveform['semantic_words'] == metadata['restored_words'], 'waveform loses semantic state')
    result = dict(metadata=metadata, matched_cycles=samples,
                  first_mismatch_cycle=expected_cycle, signal=signal, exit_code=0 if expected_cycle is None else 1,
                  waveform=waveform, simulator_argv=[str(a) for a in argv], cwd=str(case),
                  artifact_hashes={name: sha(case/name) for name in
                                  ('replay.sv', 'clean.sv', 'restore.txt', 'trace.txt', 'simv', 'replay.vpd', 'replay.vcd')})
    (case/'result.json').write_bytes(canonical(result))
    return result


def verify_fixture(vcs, fixture, build, out):
    base = build/'f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config/FireSim-generated'
    manifest, boundary = [json.loads(Path(str(base)+suffix).read_text()) for suffix in
                          ('.semantic-state.json', '.semantic-boundary.json')]
    rtl = Path(str(base)+'.semantic-clean.sv').read_text()
    original = 'assign io_respData = responseData;'
    require(rtl.count(original) == 1, 'ambiguous fixture RTL bug location')
    bug = rtl.replace(original, "assign io_respData = responseData ^ ((counter == 9'd24) ? 9'h1 : 9'h0);")
    results = []
    configuration = 'InventoryFixture-NoConfig-DefaultF2Config'
    # One full execution starting in reset and two in-flight snapshots must
    # reach the SAME real DUT counter-triggered RTL defect at cycle 29.
    for name in ('reset', 'outstanding', 'stalled'):
        image, trace = [(fixture/name/f).read_bytes() for f in ('capture.rtlckpt', 'capture.trace')]
        results.append(verify_case(vcs, out/name, manifest, boundary, configuration, image, trace, bug, 29, 'io_respData'))
    # Full healthy replay also provides an executable for actual runtime file
    # failures, independent of Python's preflight rejection tests.
    image, trace = [(fixture/'stalled'/f).read_bytes() for f in ('capture.rtlckpt', 'capture.trace')]
    healthy = out/'healthy'
    results.append(verify_case(vcs, healthy, manifest, boundary, configuration, image, trace, rtl))
    valid = (healthy/'trace.txt').read_text()
    unknown = valid.splitlines()
    fields = unknown[0].split()
    fields[2] = 'x'
    unknown[0] = ' '.join(fields)
    negative = []
    for name, text, error in [('short', '', 'FINITE_SHORT_TRACE'),
                              ('cycle', valid.replace('DATA 26', 'DATA 27', 1), 'FINITE_PACKET_OR_CYCLE_ERROR'),
                              ('extra-field', valid.replace('DATA 26', 'DATA 26 extra', 1), 'FINITE_PACKET_OR_CYCLE_ERROR'),
                              ('extra-row', valid+'DATA 37\n', 'FINITE_EXTRA_TRACE'),
                              ('unknown', '\n'.join(unknown)+'\n', 'FINITE_UNKNOWN_TRACE')]:
        case = out/('bad-'+name)
        case.mkdir(parents=True)
        (case/'trace.txt').write_text(text)
        log = run([healthy/'simv', '-no_save', f'+restore={healthy/"restore.txt"}', f'+trace={case/"trace.txt"}',
                   f'+waveform={case/"replay.vpd"}', f'+audit={case/"matched.txt"}'], case/'run.log', case, 1)
        require(error in log and 'PASS:' not in log, 'wrong explicit runtime trace rejection')
        negative.append(dict(name=name, error=error, exit_code=1))
    return dict(results=results, runtime_rejections=negative, bug_is_rtl_change=True,
                same_bug_cycle_from_reset_and_inflight_snapshots=29)


def verify_production(vcs, production, out):
    from tools.checkpoint_formats.tests.verify_bridge_semantic_vcs import CONFIGURATION
    manifest, boundary = [json.loads((production/('FireSim-generated'+suffix)).read_text()) for suffix in
                          ('.semantic-state.json', '.semantic-boundary.json')]
    summary = json.loads((production/'live/summary.json').read_text())
    require(summary['live_shadow_acceptance'] is True, 'retained production trace lacks healthy END acceptance')
    for filename in ('FireSim-generated.semantic-clean.sv', 'FireSim-generated.semantic-state.json',
                     'FireSim-generated.semantic-boundary.json', 'capture.rtlckpt'):
        require((production/filename).is_file(), 'missing retained capture artifact: ' + filename)
    source_hashes = json.loads((production/'source-inputs.json').read_text())
    for filename in ('FireSim-generated.semantic-clean.sv', 'FireSim-generated.semantic-state.json',
                     'FireSim-generated.semantic-boundary.json'):
        path = production/filename
        require(sha(path) == source_hashes[str(path)], 'changed retained source ' + filename)
    image = (production/'capture.rtlckpt').read_bytes()
    require(hashlib.sha256(image).hexdigest() == summary['session']['level2_sha256'], 'changed independent Level-2 image')
    raw = production/'live/long/matched.txt'
    package = out/'inputs'
    package_metadata = package_boundary_trace(manifest, boundary, CONFIGURATION, image, raw, package)
    require(package_metadata['samples'] == summary['results'][0]['matched_cycles'], 'incomplete retained finite trace')
    # The self-contained replay directory carries only Level 2 and finite I/O.
    for suffix in ('.semantic-state.json', '.semantic-boundary.json', '.semantic-clean.sv'):
        shutil.copy2(production/('FireSim-generated'+suffix), package/('FireSim-generated'+suffix))
    trace = (package/'capture.trace').read_bytes()
    rtl = (package/'FireSim-generated.semantic-clean.sv').read_text()
    results = [verify_case(vcs, out/'healthy', manifest, boundary, CONFIGURATION, image, trace, rtl)]
    # Deliberate cross-channel combinational defect, in the DUT RTL itself.
    # Its trigger uses an actual target input, never a bench cycle injection.
    original = 'assign ep_axi4_ar_bits_qos = axi4buf_auto_out_ar_bits_qos;'
    require(rtl.count(original) == 1, 'ambiguous production RTL bug location')
    bug = rtl.replace(original, "assign ep_axi4_ar_bits_qos = axi4buf_auto_out_ar_bits_qos ^ {3'b000, ep_axi4_r_valid};")
    ports = summary['session']['ports']
    index = next(i for i, p in enumerate(ports) if p['name'] == 'ep_axi4_r_valid')
    with raw.open() as stream:
        first = next(int(line.split()[1]) for line in stream if int(line.split()[index+2], 16))
    require(first > package_metadata['first_cycle'], 'bug must have a matching prefix')
    for name in ('rtl-bug-first', 'rtl-bug-repeat'):
        results.append(verify_case(vcs, out/name, manifest, boundary, CONFIGURATION, image, trace, bug,
                                   first, 'ep_axi4_ar_bits_qos'))
    require(sha(package/'capture.rtlckpt') == package_metadata['checkpoint_sha256'] and
            sha(package/'capture.trace') == package_metadata['trace_sha256'], 'replay modified its input containers')
    return dict(package=package_metadata, capture_provenance=str(production), results=results,
                bug_is_rtl_change=True, repeated_bug_cycle=first, no_level1_image_or_runtime_in_replay=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('production', 'fixture', 'build', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    (args.out/'latest.json').write_bytes(canonical(dict(output=str(out))))
    print('FINITE_REPLAY_OUTPUT '+str(out), flush=True)
    vcs = Path(os.environ['VCS_HOME'])
    fixture = verify_fixture(vcs, args.fixture.resolve(), args.build.resolve(), out/'fixture')
    (out/'fixture-summary.json').write_bytes(canonical(fixture))
    print('PASS: reset and in-flight fixture RTL bug at cycle 29, full waveforms and runtime rejections', flush=True)
    production = verify_production(vcs, args.production.resolve(), out/'production')
    result = dict(status='pass', milestone='M7-dessert-replay', fixture=fixture, production=production,
                  ordinary_vcs_only=True, full_visibility_waveforms=True,
                  physical_fpga_validated=False, asic_gate_activity_validated=False)
    (out/'summary.json').write_bytes(canonical(result))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
