"""Sustained fresh Level-1-restored FCFS metasim / ordinary RTL VCS lockstep.

Invoked by verify_bridge_semantic_vcs --live after its complete pre-edge scope.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

from tools.checkpoint_formats.bridge_live_shadow import prepare_bridge_clean
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def restored_pair(authority, clean, case, expected):
    processes, files = [], []
    try:
        for name, argv in [('clean', clean), ('authority', authority)]:
            if name == 'authority':
                deadline = time.monotonic() + 600
                while 'SHADOW_CLEAN_PRE_EDGE' not in (case / 'clean.log').read_text():
                    require(processes[0].poll() is None, 'clean startup failed; see ' + str(case))
                    require(time.monotonic() < deadline, 'clean startup timed out')
                    time.sleep(0.1)
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
            require(time.monotonic() < deadline, 'restored live pair timed out')
            time.sleep(0.1)
        codes = [p.returncode for p in processes]
        for file, code in zip(files, codes):
            file.write(f'exit={code}\n')
            file.flush()
        require(codes == [expected, expected], f'unexpected restored pair exits {codes}; see {case}')
        return codes
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait()
        for file in files:
            file.close()


def verify_live(out, manifest, boundary, mapping, erased, configuration):
    live = out / 'live'
    image = out / 'capture.rtlckpt'
    native = out / 'capture.fsckpt'
    original_hash = hashlib.sha256(native.read_bytes()).hexdigest()
    metadata = prepare_bridge_clean(manifest, boundary, mapping, erased, configuration, image.read_bytes(),
        json.loads(Path(str(image) + '.cut.json').read_text()), original_hash, live)
    start = metadata['first_cycle']
    fault_cycle = start + 100
    bench = (live / 'clean.sv').read_text().replace('// BRIDGE_LIVE_VERIFICATION_INJECTION',
        'if($test$plusargs("bridge-live-corrupt") && next_cycle == ' + str(fault_cycle) + ') begin\n'
        '        dut.axi4buf.nodeOut_ar_deq_q.ram_flattened[dut.axi4buf.nodeOut_ar_deq_q.deq_ptr_value] =\n'
        '          dut.axi4buf.nodeOut_ar_deq_q.ram_flattened[dut.axi4buf.nodeOut_ar_deq_q.deq_ptr_value] ^ 51\'h1;\n'
        '        $display("SHADOW_INJECT_STATE cycle=%0d signal=axi4buf.nodeOut_ar_deq_q.ram_flattened bit=0", next_cycle);\n'
        '      end\n      #1;')
    (live / 'clean.sv').write_text(bench)
    vcs = Path(os.environ['VCS_HOME']) / 'bin/vcs'
    run([vcs, '-full64', '-sverilog', '-debug_access+all', '+vpi', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
         '-CFLAGS', '-std=c++17', '-timescale=1ns/1ps', '-top', 'bridge_shadow_tb', f'-Mdir={live / "csrc"}',
         '-o', live / 'simv', out / 'FireSim-generated.semantic-clean.sv', live / 'clean.sv',
         ROOT / 'tools/checkpoint_formats/semantic_restore.cc',
         ROOT / 'tools/checkpoint_formats/live_shadow_transport.cc'], live / 'build.log')
    bindings = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
        live / 'clean.sv', live / 'authority.sv', live / 'restore.txt', live / 'simv', image, native,
        out / 'AXI4Fuzzer-checkpoint']}
    (live / 'source-inputs.json').write_bytes(canonical(bindings))
    results = []
    for name, expected in [('long', 0), ('state-corruption', 1)]:
        case = live / name
        case.mkdir()
        socket = Path(tempfile.mkdtemp(prefix='fcfs-shadow-', dir='/tmp')) / 'channel'
        authority = [out / 'AXI4Fuzzer-checkpoint', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
                     '+memsize=4194304', '+max-cycles=1000000', f'+fs-restore={native}',
                     f'+shadow-socket={socket}', f'+shadow-identity={metadata["session_identity"]}',
                     f'+shadow-first-cycle={start}', f'+shadow-level1-cycle={metadata["level1_cycle"]}']
        clean = [live / 'simv', '+vcs+initreg+0', '+vcs+initmem+0', f'+shadow-socket={socket}',
                 f'+shadow-audit={case / "matched.txt"}']
        if expected:
            clean.append('+bridge-live-corrupt')
        codes = restored_pair(authority, clean, case, expected)
        clean_text, authority_text = [(case / (name + '.log')).read_text() for name in ('clean', 'authority')]
        require(f'RESTORE_VERIFY: matched {metadata["restored_words"]} semantic words before first DUT edge' in clean_text
                and f'SHADOW_CLEAN_PRE_EDGE cycle={start} words={metadata["restored_words"]} target_edges=0' in clean_text,
                'missing complete clean pre-edge readback')
        require(f'SHADOW_RESTORED_ORIGIN semantic={start} level1={metadata["level1_cycle"]} host_edges=0 target_edges=0'
                in authority_text and 'PRODUCTION_BOOTSTRAP zero_edges=1' in authority_text,
                'missing fresh public Level-1 restore/semantic origin')
        cycles = []
        counters = dict(ar_transfers=0, aw_transfers=0, r_transfers=0, b_transfers=0,
                        held_ar=0, held_aw=0, held_r=0, held_b=0)
        ports = metadata['ports']
        for line in (case / 'matched.txt').read_text().splitlines():
            kind, cycle, *values = line.split()
            require(kind == 'DATA' and int(cycle) == start + len(cycles) and len(values) == len(ports),
                    'missing/duplicated/malformed compared target cycle')
            cycles.append(int(cycle))
            v = {p['name']: int(value, 16) for p, value in zip(ports, values)}
            for channel in ('ar', 'aw', 'r', 'b'):
                valid, ready = v[f'ep_axi4_{channel}_valid'], v[f'ep_axi4_{channel}_ready']
                counters[channel + '_transfers'] += bool(valid and ready)
                counters['held_' + channel] += bool(valid and not ready)
        result = dict(name=name, matched_cycles=len(cycles), first_cycle=start,
                      clean_exit=codes[0], authority_exit=codes[1], counters=counters,
                      output_comparisons=len(cycles) * sum(p['direction'] == 'output' for p in ports),
                      authority_argv=[str(a) for a in authority], clean_argv=[str(a) for a in clean], cwd=str(case))
        if name == 'long':
            require(len(cycles) > 100000 and counters['ar_transfers'] > 1000 and counters['aw_transfers'] > 1000
                    and counters['r_transfers'] > 1000 and counters['b_transfers'] > 1000,
                    'insufficient sustained actual AXI traffic')
            require('*** PASSED *** after 774628 cycles' in authority_text
                    and f'end={start+len(cycles)} target_edges={len(cycles)}' in authority_text
                    and f'end={start+len(cycles)} target_edges={len(cycles)}' in clean_text,
                    'missing successful complete authority/clean edge correspondence')
            result['last_cycle'] = cycles[-1]
        else:
            require(cycles == list(range(start, fault_cycle)) and
                    f'SHADOW_INJECT_STATE cycle={fault_cycle}' in clean_text and
                    re.search(rf'FIRST_MISMATCH cycle={fault_cycle} signal=ep_axi4_ar_bits_qos .*target_edges=100', clean_text)
                    and clean_text.count('FIRST_MISMATCH') == 1 and
                    f'target_cycle={fault_cycle} pending=1' in authority_text,
                    'actual clean-state corruption was not detected at its first target cycle')
            result.update(first_mismatch_cycle=fault_cycle, signal='ep_axi4_ar_bits_qos')
        (case / 'result.json').write_bytes(canonical(result))
        results.append(result)
    require(hashlib.sha256(native.read_bytes()).hexdigest() == original_hash and
            all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in bindings.items()),
            'live checkpoint/source bindings changed')
    summary = dict(session=metadata, results=results, live_shadow_acceptance=True,
                   physical_fpga_validated=False, asic_gate_activity_validated=False)
    (live / 'summary.json').write_bytes(canonical(summary))
    print(json.dumps(summary, indent=2), flush=True)
