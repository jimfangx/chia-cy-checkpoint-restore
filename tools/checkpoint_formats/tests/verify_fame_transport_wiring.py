"""Synthesize and execute compiler-bound qualification of existing transports.

This tests local owner qualification, not a complete physical capture network.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.regression_runner import local

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
SCALA = 'sims/firesim/sim/midas/src/'
RTL = 'sims/firesim/sim/midas/src/main/verilog/'
RESOURCES = ['CheckpointNativeCaptureTransport.sv', 'CheckpointNativeStateCapture.sv',
             'CheckpointNativeStateSnapshot.sv', 'CheckpointSnapshotStateBank.sv',
             'CheckpointPhysicalCaptureTransport.sv', 'CheckpointPhysicalClockCut.sv',
             'CheckpointCaptureTransport.sv', 'CheckpointCaptureCut.sv']
SOURCES = [SCALA + 'main/scala/midas/checkpoint/' + n + '.scala' for n in (
    'FAMEClockCutWiring', 'FAMEClockCutTransportWiring', 'FAMEClockProgressBindings', 'FAMEClockProgress')] + [
    SCALA + 'test/scala/midas/checkpoint/' + n + '.scala' for n in (
        'FAMEClockCutWitnessSpec', 'FAMEClockCutTransportWiringSpec')] + [RTL + n for n in RESOURCES] + [
    'tools/checkpoint_formats/tests/' + n for n in (
        'verify_fame_transport_wiring.py', 'audit_fame_transport_wiring.py',
        'fame_transport_wiring_tb.sv', 'checkpoint_widget_exit.cc')]
GENERATED = ['reference.fir', 'wired.fir', 'wired.sv', 'binding.json', 'witness-binding.json', 'emission.json']
PROFILES = ['physical-root', 'physical-nested', 'native-root', 'native-nested']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado', 'vcs'), required=True)
    parser.add_argument('--compiler-receipt', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--native', type=Path)
    args = parser.parse_args()
    base = local(ROOT, args.out).resolve()
    require(base.is_relative_to(RUNS), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=base))
    doc = dict(status='fail', backend='f2' if args.mode == 'vivado' else 'eda',
               source_root=str(ROOT), observed_utc=datetime.now(timezone.utc).isoformat(),
               physical_fpga_capture=False, deployable_capture_image=False, global_target_cut_proven=False,
               scope='existing physical/native transport local FAME qualification; no physical-network attachment',
               sources={n: file_sha(ROOT / n) for n in SOURCES}, commands=[], profiles={})

    def run(argv, name, work, expected=0):
        log = work / (name + '.log')
        row = dict(argv=list(map(str, argv)), cwd=str(work), log=str(log))
        doc['commands'].append(row)
        with log.open('x') as stream:
            row['returncode'] = subprocess.run(row['argv'], cwd=work, stdout=stream, stderr=subprocess.STDOUT).returncode
        require(row['returncode'] == expected, 'inspect underlying tool log: ' + str(log))
        return log.read_text()

    try:
        cp = local(ROOT, args.compiler_receipt).resolve()
        require(cp.is_relative_to(RUNS), 'compiler evidence outside runs')
        c = json.loads(cp.read_text())
        require(c['status'] == 'pass' and c['backend'] == 'f2' and c['returncode'] == 0, 'successful compiler fixture required')
        for n, digest in c['sources'].items():
            require(file_sha(local(ROOT, n)) == digest, 'compiler source changed: ' + n)
        require(all(n in c['sources'] for n in SOURCES if n.endswith('.scala')), 'compiler omits generator/test source')
        doc['compiler_receipt'] = dict(path=str(cp), sha256=file_sha(cp))
        if args.mode == 'vivado':
            require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore'), 'native Vivado belongs on manager')
            vendor = Path(os.environ['XILINX_VIVADO']) / 'data/verilog/src'
        else:
            require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore'), 'VCS belongs on EDA')
            np = local(ROOT, args.native).resolve()
            native = json.loads(np.read_text())
            require(native['status'] == 'pass' and native['backend'] == 'f2' and
                    native['sources'] == doc['sources'] and native['compiler_receipt']['sha256'] == file_sha(cp),
                    'matching source/compiler/native receipt required')
            for n, digest in native['artifacts'].items():
                require(file_sha(np.parent / n) == digest, 'native artifact changed: ' + n)
            doc['native_receipt'] = dict(path=str(np), sha256=file_sha(np))
        for profile in PROFILES:
            work = out / profile
            work.mkdir()
            generated = cp.parent / 'generated/bank/fame-transport' / profile
            for n in GENERATED:
                key = str(Path('generated/bank/fame-transport') / profile / n)
                require(c['artifacts'].get(key) == file_sha(generated / n), 'compiler fixture changed: ' + key)
                shutil.copyfile(generated / n, work / n)
            binding = json.loads((work / 'binding.json').read_text())
            require(binding['scope'] == 'existing_transport_local_fame_witness_qualification_only' and
                    binding['reference_sha256'] == file_sha(work / 'reference.fir') and
                    binding['wired_reference_sha256'] == file_sha(work / 'wired.fir') and
                    binding['witness_binding_sha256'] == file_sha(work / 'witness-binding.json') and
                    binding['fame_owner_bit'] == 1 and binding['owners'] == ['left', 'fame', 'right'] and
                    binding['new_storage_bits'] == binding['new_collectors'] == binding['new_transports'] == 0 and
                    binding['independent_owner_acknowledgements_required'] is True and
                    binding['complete_fpga_capture'] is binding['deployable_capture_image'] is False,
                    'wrong existing transport witness contract')
            for name in RESOURCES:
                shutil.copyfile(ROOT / RTL / name, work / name)
            for name in ('BUFGCE.v', 'glbl.v'):
                source = vendor / ('unisims/BUFGCE.v' if name == 'BUFGCE.v' else name) if args.mode == 'vivado' else np.parent / profile / name
                shutil.copyfile(source, work / name)
            if args.mode == 'vivado':
                (work / 'synth.tcl').write_text('''set_param general.maxThreads 4
read_verilog -sv {wired.sv ''' + ' '.join(RESOURCES) + '''}
synth_design -top Top -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports hostClock]
if {[llength [get_cells -hier -filter {REF_NAME == BUFGCE}]] != 2} {error "exact original two gates required"}
set observers [get_cells -hier -filter {NAME =~ *checkpoint_fame* && IS_SEQUENTIAL == 1}]
if {[llength $observers] != 321} {error "all 321 original FAME observer bits required"}
report_utilization -file utilization.rpt
report_timing_summary -report_unconstrained -file timing.rpt
write_checkpoint -force synthesized.dcp
puts "FAME_TRANSPORT_NATIVE_PASS observer_bits=321 original_gates=2"
''')
                text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl', '-log', 'vivado.log', '-journal', 'vivado.jou'], 'native', work)
                require('Vivado v2025.2' in text and 'FAME_TRANSPORT_NATIVE_PASS observer_bits=321 original_gates=2' in text
                        and not re.search('ERROR:|CRITICAL WARNING:', text), 'native synthesis failed or combinational loop')
            else:
                # Derive ONLY public bench declarations from compiler-emitted
                # ports; all behavioral expectations live in the independent TB.
                rtl = (work / 'wired.sv').read_text()
                header = re.search(r'module Top\((.*?)\);', rtl, re.S)
                require(header is not None, 'missing generated Top port list')
                ports = re.findall(r'\b(input|output)\s+(?:wire\s+)?(\[[^\]]+\]\s*)?(\w+)\s*[,\n]', header.group(1) + '\n')
                require(len(ports) > 60 and len({n for _, _, n in ports}) == len(ports), 'incomplete public ABI parse')
                (work / 'ports.svh').write_text('\n'.join(
                    f"{'reg' if d == 'input' else 'wire'} {w or ''}{n}" + ('=0;' if d == 'input' else ';')
                    for d, w, n in ports) + '\n')
                shutil.copyfile(ROOT / 'tools/checkpoint_formats/tests/fame_transport_wiring_tb.sv', work / 'tb.sv')
                shutil.copyfile(ROOT / 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc', work / 'exit.cc')
                transport = 'dut.peer.transport' if profile.endswith('nested') else 'dut.transport'
                run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-debug_access+all',
                     '-debug_region+cell+encrypt', '-Mupdate', '-top', 'fame_transport_wiring_tb', '-top', 'glbl',
                     '-Mdir=' + str(work / 'csrc'), '-o', work / 'simv', '+incdir+' + str(work),
                     '+define+TRANSPORT=' + transport, work / 'BUFGCE.v', work / 'glbl.v', work / 'wired.sv',
                     *[work / n for n in RESOURCES], work / 'tb.sv', work / 'exit.cc', '-CFLAGS', '-std=c++17'], 'compile', work)
                cases = {}
                for case in ('healthy', 'corrupt'):
                    case_dir = work / case
                    case_dir.mkdir()
                    text = run([work / 'simv', '-no_save', *(['+corrupt'] if case == 'corrupt' else [])], case, case_dir,
                               1 if case == 'corrupt' else 0)
                    if case == 'healthy':
                        require(re.search(r'FAME_TRANSPORT_PASS checks=\d+ cycles=512 patterns=512', text), 'active scope incomplete')
                    else:
                        require('FAME_TRANSPORT_DIVERGENCE host_step=17 cycle=' in text and
                                'acknowledged=16 signal=independent_applied_a' in text, 'first divergent edge acknowledged')
                    wave = case_dir / 'fame-transport.vcd'
                    require(wave.stat().st_size > 1000, 'full debug waveform missing')
                    from tools.checkpoint_formats.tests.audit_fame_transport_wiring import audit_wave
                    cases[case] = dict(waveform=str(wave), log=str(case_dir / (case + '.log')),
                                       raw_wave_audit=audit_wave(wave, profile.endswith('nested'), case == 'corrupt'))
                doc['profiles'][profile] = dict(status='pass', cases=cases)
        require(doc['sources'] == {n: file_sha(ROOT / n) for n in SOURCES}, 'source changed during execution')
        doc['status'] = 'pass'
    except Exception as error:
        doc['error'] = str(error)
        raise
    finally:
        doc['artifacts'] = {str(p.relative_to(out)): file_sha(p) for p in out.rglob('*')
                            if p.is_file() and p.suffix in {'.log', '.rpt', '.sv', '.svh', '.v', '.cc', '.fir', '.json', '.tcl', '.dcp', '.vcd'}}
        receipt = out / 'summary.json'
        receipt.write_text(json.dumps(doc, indent=2) + '\n')
        print(receipt, flush=True)


if __name__ == '__main__':
    main()
