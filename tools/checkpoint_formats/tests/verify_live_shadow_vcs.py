"""Live semantic-oracle increment, not yet restored Level-1 M6 acceptance.

Run after the complete verify_semantic_vcs scope; --reference is its output.
Each case launches two independent VCS processes concurrently. No captured
trace is passed to either process, and the authority waits for each ACK.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.live_shadow import prepare_live_shadow
from tools.checkpoint_formats.replay import read_json
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run, invalidate_stale_driver_objects


def pair(authority, clean, case, expected_clean, expected_authority):
    processes = []
    files = []
    try:
        for name, argv in (('clean', clean), ('authority', authority)):
            file = (case / (name + '.log')).open('w')
            files.append(file)
            file.write(f'cwd={case}\nargv={json.dumps([str(a) for a in argv])}\n')
            file.flush()
            process = subprocess.Popen([str(a) for a in argv], cwd=case, stdout=file, stderr=subprocess.STDOUT)
            processes.append(process)
            file.write(f'fresh_process_pid={process.pid}\n')
            file.flush()
        deadline = time.monotonic() + 1800
        while any(p.poll() is None for p in processes):
            require(time.monotonic() < deadline, 'live VCS pair exceeded deadline')
            time.sleep(0.1)
        codes = [p.returncode for p in processes]
        require(codes == [expected_clean, expected_authority], f'unexpected live pair exits {codes}; see {case}')
        for file, code in zip(files, codes):
            file.write(f'exit={code}\n')
        return codes
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait()
        for file in files:
            file.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'reference', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=1024)
    args = parser.parse_args()
    require(os.environ.get('VCS_HOME') == _toolchain.VCS_HOME, 'source vcs-env.sh LAST')
    require(1024 <= args.rounds <= 1000000, 'sustained verification requires at least 1024 rounds')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=args.out.resolve()))
    print('LIVE_SHADOW_VCS_OUTPUT ' + str(out), flush=True)
    generated = args.build.resolve() / 'f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config'
    base = generated / 'FireSim-generated'
    manifest, boundary = [read_json(str(base) + suffix) for suffix in
                          ('.semantic-state.json', '.semantic-boundary.json')]
    clean = Path(str(base) + '.semantic-clean.sv')
    image = (args.reference.resolve() / 'stalled/capture.rtlckpt').read_bytes()
    adapter = out / 'adapter'
    metadata = prepare_live_shadow(manifest, boundary, 'InventoryFixture-NoConfig-DefaultF2Config',
                                   image, clean.read_text(), Path(str(base) + '.sv').read_text(), adapter)
    require(metadata['first_cycle'] == 26, 'missing held-response checkpoint')
    (adapter / 'capture.rtlckpt').write_bytes(image)
    # Optional test observer deposits a real hidden DUT register immediately
    # before comparing cycle 29, while the response remains under backpressure.
    source = (adapter / 'clean.sv').read_text()
    source = source.replace('integer parsed;', 'integer parsed;\nlongint unsigned corrupt_cycle;\nbit inject_corruption;')
    source = source.replace('  audit_fd =',
                            '  inject_corruption = $value$plusargs("shadow-corrupt-cycle=%d", corrupt_cycle);\n  audit_fd =')
    source = source.replace('// LIVE_SHADOW_VERIFICATION_INJECTION',
                            'if (inject_corruption && next_cycle == corrupt_cycle) begin\n'
                            '        dut.responseData = dut.responseData ^ 9\'h1;\n'
                            '        $display("SHADOW_INJECT_STATE cycle=%0d", next_cycle);\n'
                            '      end\n      #1;')
    (adapter / 'clean.sv').write_text(source)
    vcs = Path(os.environ['VCS_HOME']) / 'bin/vcs'
    native = ROOT / 'tools/checkpoint_formats'
    drivers = ROOT / 'sims/firesim/sim/src/main/cc/midasexamples'
    source_files = (native / 'live_shadow.py', native / 'live_shadow_transport.cc',
                    native / 'semantic_restore.cc', Path(__file__),
                    drivers / 'TestInventoryFixture.cc', drivers / 'TestHarness.cc',
                    clean, Path(str(base) + '.sv'), Path(str(base) + '.semantic-state.json'),
                    Path(str(base) + '.semantic-boundary.json'),
                    args.reference.resolve() / 'stalled/capture.rtlckpt')
    source_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    (out / 'source-inputs.json').write_bytes(canonical(source_hashes))
    make = ['make', 'DESIGN=InventoryFixture', 'TARGET_CONFIG=NoConfig', 'PLATFORM_CONFIG=DefaultF2Config',
            'SEMANTIC_CHECKPOINT_ROOT=InventoryFixture.dut', f'BUILD_DIR={args.build.resolve()}',
            f'VCS={vcs} -full64', 'VCS_FLAGS=-Mupdate', f'VCS_EXTRA_V={adapter / "authority.sv"}',
            'DRIVER_CC=' + ' '.join(str(p) for p in (drivers / 'TestHarness.cc', drivers / 'TestInventoryFixture.cc',
                                                    native / 'live_shadow_transport.cc', native / 'semantic_restore.cc'))]
    invalidate_stale_driver_objects(generated, out / 'rebuilt-driver-objects.json')
    run(make + ['vcs'], out / 'metasim-build.log', ROOT / 'sims/firesim/sim')
    executable = generated / 'InventoryFixture'
    shutil.copy2(executable, out / executable.name)
    shutil.copytree(Path(str(executable) + '.daidir'), out / (executable.name + '.daidir'))
    for library in generated.glob('*.so'):
        shutil.copy2(library, out / library.name)
    run([vcs, '-full64', '-sverilog', '-debug_access+all', '+vpi', '-cc', os.environ['CC'],
         '-cpp', os.environ['CXX'], '-CFLAGS', f'-std=c++17 -I{os.environ["VCS_HOME"]}/include',
         '-timescale=1ns/1ps', '-top', 'live_shadow_tb', f'-Mdir={out / "clean-csrc"}', '-o', out / 'clean-simv',
         clean, adapter / 'clean.sv', native / 'semantic_restore.cc', native / 'live_shadow_transport.cc'],
        out / 'clean-build.log')
    results = []
    for name in ('long', 'state-corruption'):
        case = out / name
        case.mkdir()
        # Short UNIX-socket paths avoid Linux's 108-byte pathname limit.
        socket_dir = Path(tempfile.mkdtemp(prefix='fs-shadow-', dir='/tmp'))
        socket_path = socket_dir / 'channel'
        authority = [out / 'InventoryFixture', '+vcs+initreg+0', '+vcs+initmem+0',
                     f'+shadow-socket={socket_path}', f'+inventory-shadow-rounds={args.rounds}']
        clean_argv = [out / 'clean-simv', '+vcs+initreg+0', '+vcs+initmem+0',
                      f'+shadow-socket={socket_path}', f'+restore={adapter / "restore.txt"}',
                      f'+shadow-audit={case / "matched.jsonl"}']
        if name == 'state-corruption':
            clean_argv.append('+shadow-corrupt-cycle=29')
        codes = pair(authority, clean_argv, case, 0 if name == 'long' else 1, 0 if name == 'long' else 1)
        text = (case / 'clean.log').read_text()
        authority_text = (case / 'authority.log').read_text()
        require('SHADOW_CLEAN_PRE_EDGE cycle=26 words=22 target_edges=0' in text,
                'clean RTL did not verify complete Level-2 state before its first edge')
        audit = (case / 'matched.jsonl').read_text().splitlines()
        cycles = [int(row.split()[1]) for row in audit]
        require(cycles == list(range(26, 26 + len(cycles))), 'missing/duplicated compared target edge')
        result = dict(name=name, matched_cycles=len(cycles), clean_exit=codes[0], authority_exit=codes[1],
                      authority_argv=[str(a) for a in authority], clean_argv=[str(a) for a in clean_argv],
                      cwd=str(case), audit=str(case / 'matched.jsonl'))
        if name == 'long':
            require('*** PASSED ***' in authority_text and 'PASS: live clean RTL shadow' in text,
                    'live shadow or original directed checks failed')
            require(len(cycles) == 11 + 105 * args.rounds, 'sustained target edge count differs')
            require('FIRST_MISMATCH' not in text and 'SHADOW_PROTOCOL_ERROR' not in authority_text,
                    'healthy shadow failed')
            ports = metadata['ports']
            idx = {p['name']: i + 2 for i, p in enumerate(ports)}
            rows = [[int(v, 16) for v in row.split()[2:]] for row in audit]
            index = lambda p: idx[p] - 2
            require(all(r[index('io_count')] == (cycle - 5) % 512 and
                        r[index('io_phase')] == (cycle - 5) % 3 for cycle, r in zip(cycles, rows)),
                    'actual DUT counter/FSM disagree with target-edge indexing')
            require(all(not (previous[index('io_respValid')] and not previous[index('io_respReady')]) or
                        (current[index('io_respValid')] and
                         current[index('io_respData')] == previous[index('io_respData')])
                        for previous, current in zip(rows, rows[1:])),
                    'response valid/payload changed during backpressure')
            held = sum(r[index('io_respValid')] and not r[index('io_respReady')] for r in rows)
            transfers = sum(r[index('io_respValid')] and r[index('io_respReady')] for r in rows)
            blocked_requests = sum(r[index('io_reqValid')] and not r[index('io_reqReady')] for r in rows)
            require(held > 10000 and transfers > 10000 and blocked_requests > 10000,
                    'sustained run did not exercise ready/valid timing')
            result.update(first_cycle=26, last_cycle=cycles[-1], held_responses=held,
                          response_transfers=transfers, blocked_requests=blocked_requests,
                          independent_edge_counter_and_held_payload_checks=True,
                          output_comparisons=len(cycles) * sum(p['direction'] == 'output' for p in ports))
        else:
            require('SHADOW_INJECT_STATE cycle=29' in text and
                    'FIRST_MISMATCH cycle=29 signal=io_respData' in text and text.count('FIRST_MISMATCH') == 1,
                    'hidden-state corruption was not detected at the first exact target cycle')
            require(cycles == [26, 27, 28] and
                    'SHADOW_PROTOCOL_ERROR: target_cycle=29 pending=1' in authority_text,
                    'authority advanced after first divergence or clean compared extra cycles')
            result.update(first_mismatch_cycle=29, signal='io_respData', corruption='clean DUT responseData bit 0')
        results.append(result)
        (case / 'result.json').write_bytes(canonical(result))
    require(all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in source_hashes.items()),
            'shadow source inputs changed during verification')
    summary = dict(session=metadata, results=results, level1_restore_integrated=False,
                   milestone_acceptance=False, physical_fpga_validated=False,
                   sources=source_hashes)
    (out / 'summary.json').write_bytes(canonical(summary))
    (args.out / 'latest.json').write_bytes(canonical(dict(invocation=str(out), summary=str(out / 'summary.json'))))
    print('PASS: sustained live semantic-DUT VCS shadow and exact first-cycle state corruption; Level-1 integration pending')


if __name__ == '__main__':
    main()
