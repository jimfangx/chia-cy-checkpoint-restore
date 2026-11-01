"""Synthesized generated-shell staging-owner restore; all VCS runs on EDA.

Directed component images only. This does not restore original/native storage,
provide a global cut, or establish physical FPGA/CPU checkpoint acceptance.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests.audit_native_snapshot_restore_wave import audit

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
RTL = 'sims/firesim/sim/midas/src/main/verilog/CheckpointNativeStateSnapshot.sv'
TB = 'tools/checkpoint_formats/tests/live_shell_staging_restore_tb.sv'
EXIT = 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'
SELF = 'tools/checkpoint_formats/tests/verify_live_shell_staging_restore.py'
SOURCES = (RTL, TB, EXIT, SELF, 'tools/checkpoint_formats/tests/audit_native_snapshot_restore_wave.py',
    'tools/checkpoint_formats/codec.py', 'tools/checkpoint_formats/toolchain.py',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointLiveShellSnapshot.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointLiveShellSnapshotSpec.scala')
BITS = (237, 557)
CUTS = ('empty', 'occupied', 'released', 'error')
NEGATIVES = ('missing-owner', 'lost-freeze', 'bank-reset', 'request', 'release', 'borrow', 'unheld', 'busy')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode', choices=('vivado', 'vcs'), required=True)
    ap.add_argument('--generated', type=Path)
    ap.add_argument('--native', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), 'evidence must remain beneath runs')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=args.out.resolve()))
    sources = {n: sha(ROOT/n) for n in SOURCES}
    d = dict(status='running', backend='f2' if args.mode == 'vivado' else 'eda',
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), source_root=str(ROOT),
        sources=sources, scope='generated shell complete local staging owner only',
        physical_fpga_capture=False, full_image=False, cpu_live_acceptance=False,
        original_live_and_native_restore_supported=False, commands=[])

    def save():
        (out/'summary.json').write_text(json.dumps(d, indent=2)+'\n')

    def run(argv, name, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(out), log=name+'.log')
        d['commands'].append(row)
        with (out/row['log']).open('x') as log:
            r = subprocess.run(row['argv'], cwd=out, stdout=log, stderr=subprocess.STDOUT)
        row.update(returncode=r.returncode, log_sha256=sha(out/row['log']))
        if r.returncode != expected:
            d['status'] = 'fail'
        save()
        require(r.returncode == expected, 'inspect underlying compiler/runtime log '+str(out/row['log']))
        return (out/row['log']).read_text()

    save()
    print(out, flush=True)
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native localhost synthesis only')
        require(args.generated is not None and args.native is None, 'current compiler fixture required')
        for n in SOURCES:
            p = out/'sources'/n
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/n, p)
        for bits in BITS:
            folder = out/f'generated-{bits}'
            shutil.copytree(args.generated/f'live-shell-staging-restore-{bits}', folder)
            binding = json.loads((folder/'binding.json').read_text())
            require(binding['local_staging_restore_enabled'] is True and binding['bits'] == bits and
                binding['local_staging_restore_bits'] == bits+71 and binding['local_staging_restore_extra_storage_bits'] == 0 and
                binding['wired_sha256'] == sha(folder/'wired.fir') and binding['source_sha256'] == sha(ROOT/RTL), 'changed local owner binding')
            require(all(binding[n] is False for n in ('complete_fpga_capture', 'deployable_capture_image',
                'metasim_restore_supported', 'staging_restore_supported', 'original_live_and_native_restore_supported')), 'local owner admitted production restore')
            require('parameter RESTORE_ENABLE = 1' in (folder/'wired.fir').read_text(), 'restore parameter missing')
            tcl = f'''set_param general.maxThreads 4
read_verilog -sv sources/{RTL} generated-{bits}/wired.sv
synth_design -top LiveTop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none -keep_equivalent_registers
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set owners [get_cells -hier -filter {{NAME =~ shell/checkpoint_shell_live_snapshot_adapter/* && IS_SEQUENTIAL == 1}}]
if {{[llength $owners] != {bits+71}}} {{error "incomplete staging owner: [llength $owners]"}}
puts "GENERATED_STAGING_OWNER_STORAGE bits={bits+71}"
report_utilization -file utilization-{bits}.rpt
report_timing_summary -file timing-{bits}.rpt
write_checkpoint -force staging-{bits}.dcp
puts "GENERATED_STAGING_SYNTH_PASS"
'''
            (out/f'synth-{bits}.tcl').write_text(tcl)
        d['inputs'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and p.name != 'summary.json'}
        for bits in BITS:
            text = run(['vivado', '-mode', 'batch', '-source', f'synth-{bits}.tcl'], f'synth-{bits}')
            require('GENERATED_STAGING_SYNTH_PASS' in text and not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native synthesis failed')
        d['staging_register_bits'] = [bits+71 for bits in BITS]
    else:
        require(str(ROOT).startswith('/scratch/') and shutil.which('vcs') == toolchain.VCS and
            toolchain.VCS.endswith('Y-2026.03-SP2/bin/vcs'), 'EDA native SP2 only')
        require(args.native is not None and args.generated is None, 'explicit native receipt required')
        receipt = local(ROOT, str(args.native))
        native = json.loads(receipt.read_text())
        require(native['status'] == 'pass' and native['backend'] == 'f2' and native['sources'] == sources, 'stale native receipt')
        for group in ('inputs', 'artifacts'):
            for n, digest in native[group].items():
                require(sha(receipt.parent/n) == digest, 'changed native evidence '+n)
        for n in native['inputs']:
            p = out/n
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(receipt.parent/n, p)
        d['inputs'] = native['inputs']
        d['native_receipt'] = dict(path=str(receipt), sha256=sha(receipt))
        d['wave_audits'] = []
        common = [toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
            '-top', 'live_shell_staging_restore_tb']

        def compile_sim(bits, tag, rtl):
            folder = out/tag
            folder.mkdir()
            defines = [f'+define+STAGING_BITS={bits}'] + (['+define+NATIVE_STAGING'] if bits == 557 else [])
            run(common+defines+['-Mdir='+str(folder/'csrc'), '-o', folder/'simv',
                out/f'generated-{bits}/wired.sv', rtl, out/'sources'/TB, out/'sources'/EXIT], tag+'-compile')
            return folder/'simv'

        def simulate(simv, bits, cut, mode='restore', case='healthy', expected=0, tag=None):
            tag = tag or f'{bits}-{cut}-{mode}-{case}'
            image = out/f'{bits}-{cut}.hex'
            text = run([simv, '-no_save', '+MODE='+mode, '+CUT='+cut, '+CASE='+case, '+IMAGE='+str(image)], tag, expected)
            wave = out/(tag+'.vcd')
            shutil.move(out/'staging-restore.vcd', wave)
            return text, wave

        for bits in BITS:
            simv = compile_sim(bits, f'unit-{bits}', out/'sources'/RTL)
            for cut in CUTS:
                text, _ = simulate(simv, bits, cut, mode='donor')
                require(f'STAGING_DONOR_PASS bits={bits} cut={cut} owner_bits={bits+71}' in text, 'incomplete donor')
                image = out/f'{bits}-{cut}.hex'
                require(re.fullmatch('[0-9a-f]+\n', image.read_text()) and
                    len(image.read_text().strip()) == (bits+74)//4, 'unknown/truncated complete owner')
                text, wave = simulate(simv, bits, cut)
                require(f'STAGING_RESTORE_PASS bits={bits} case=healthy cut={cut} loads=1 ' in text, 'incomplete fresh-process restore')
                d['wave_audits'].append(audit(wave, bits, top='live_shell_staging_restore_tb.',
                    owner='dut.shell.checkpoint_shell_live_snapshot_adapter.', reset_signal='snapshot_reset', ready_signal='ready'))
            text, wave = simulate(simv, bits, 'occupied', case='bits')
            loads = 2*(bits+71)+2
            require(f'loads={loads} ' in text, 'incomplete every-bit restore')
            d['wave_audits'].append(audit(wave, bits, loads=loads, top='live_shell_staging_restore_tb.',
                owner='dut.shell.checkpoint_shell_live_snapshot_adapter.', reset_signal='snapshot_reset', ready_signal='ready'))
            for case in NEGATIVES:
                text, wave = simulate(simv, bits, 'occupied', case=case)
                require(f'STAGING_NEGATIVE_PASS bits={bits} case={case} loads=1 reads=0' in text, 'unsafe restore escaped')
                d['wave_audits'].append(audit(wave, bits, top='live_shell_staging_restore_tb.',
                    owner='dut.shell.checkpoint_shell_live_snapshot_adapter.', reset_signal='snapshot_reset', ready_signal='ready'))
        # Corrupt compiled storage loading, retaining the donor and oracle.
        needle = 'payload <= restore_state[BITS-1:0];'
        rtl = (ROOT/RTL).read_text()
        require(rtl.count(needle) == 1, 'ambiguous compiled mutation')
        bad = out/'corrupt.sv'
        bad.write_text(rtl.replace(needle, "payload <= restore_state[BITS-1:0] ^ 1'b1;"))
        simv = compile_sim(557, 'corrupt', bad)
        text, wave = simulate(simv, 557, 'occupied', expected=1, tag='compiled-corrupt')
        require('signal=complete-control-before-ack bits=557 mode=restore case=healthy loads=1 reads=0' in text,
            'compiled semantic fault escaped first complete readback')
        d['compiled_corruption'] = audit(wave, 557, broken=True, top='live_shell_staging_restore_tb.',
            owner='dut.shell.checkpoint_shell_live_snapshot_adapter.', reset_signal='snapshot_reset', ready_signal='ready')
        d.update(donor_processes=8, fresh_restore_processes=8, negative_processes=16,
            every_bit_processes=2, every_bit_loads=sum(2*(bits+71)+2 for bits in BITS),
            compiled_semantic_fault_rejected_before_ack=True)
    require(sources == {n: sha(ROOT/n) for n in SOURCES}, 'sources changed during verification')
    d.update(status='pass', artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob('*')
        if p.is_file() and p.suffix in ('.log', '.rpt', '.dcp', '.vcd', '.hex')})
    save()
    print(out/'summary.json', flush=True)


if __name__ == '__main__':
    main()
