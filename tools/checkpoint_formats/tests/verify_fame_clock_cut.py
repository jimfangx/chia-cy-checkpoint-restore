"""Source-bound synthesis and fresh EDA execution of the local FAME cut owner.

This generated sibling is not a deployable image or hardware checkpoint donor.
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
VERILOG = 'sims/firesim/sim/midas/src/main/verilog/'
RTL = ['CheckpointF2ClockResetCut.sv', 'CheckpointF2ResetGuard.sv',
       'CheckpointResetOwnedClockCut.sv', 'CheckpointPhysicalClockCut.sv']
SOURCES = [SCALA + 'main/scala/midas/checkpoint/' + n + '.scala' for n in (
    'FAMEClockCutWiring', 'FAMEClockProgress', 'FAMEClockProgressBindings', 'F2ClockResetCutWiring',
    'PhysicalClockCutWiring', 'PhysicalClockCutPlan', 'PhysicalClockGateContract',
    'SynchronousResetCutWiring')] + [
    SCALA + 'main/scala/midas/stage/GoldenGateCli.scala',
    SCALA + 'test/scala/midas/checkpoint/FAMEClockProgressSpec.scala',
    *[VERILOG + n for n in RTL],
    'tools/checkpoint_formats/tests/fame_clock_cut_tb.sv',
    'tools/checkpoint_formats/tests/verify_fame_clock_cut.py',
    'tools/checkpoint_formats/tests/audit_fame_clock_cut.py',
    'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc']
GENERATED = ['reference.fir', 'reference.sv', 'wired.fir', 'wired.sv', 'binding.json',
             'collector-binding.json', 'manifest.json', 'plan.json']
NATIVE_GENERATED = ['staging-binding.json', 'banks-binding.json', 'banks.json',
                    'dependencies.json', 'witness.fir', 'witness-manifest.json', 'witness-plan.json', 'emission.json']
TCL = '''set_param general.maxThreads 4
read_verilog -sv [glob *.sv]
synth_design -top Top -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports hostClock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 3} {error "original two gates plus one root gate required"}
set observers [get_cells -hier -filter {NAME =~ *checkpoint_fame* && IS_SEQUENTIAL == 1}]
if {[llength $observers] != 321} {error "all 321 observer bits must drive the actual witness"}
report_utilization -file utilization.rpt
report_timing_summary -report_unconstrained -file timing.rpt
set f [open sequential.txt w]
foreach c [lsort [get_property NAME [get_cells -hier -filter {IS_SEQUENTIAL == 1}]]] {puts $f $c}
close $f
write_checkpoint -force synthesized.dcp
puts "FAME_CUT_NATIVE_PASS observer_bits=321 gates=3"
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('vivado', 'vcs'), required=True)
    p.add_argument('--generated', type=Path, required=True)
    p.add_argument('--native', type=Path)
    p.add_argument('--compiler-receipt', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--native-banks', action='store_true', help='Verify the composed staged native FAME banks')
    args = p.parse_args()
    rtl = RTL + (['CheckpointNativeStateSnapshot.sv'] if args.native_banks else [])
    generated_files = GENERATED + (NATIVE_GENERATED if args.native_banks else [])
    sources = SOURCES + ([SCALA + 'main/scala/midas/checkpoint/' + n + '.scala' for n in (
        'GeneratedStateBankAccess', 'GeneratedStateBankAnnotations', 'PhysicalClockStateBank',
        'PhysicalClockCutDependencies', 'F2NativeCollectorSnapshot')] +
        [VERILOG + 'CheckpointNativeStateSnapshot.sv',
         'tools/checkpoint_formats/tests/test_fame_native_cut_audit.py'] if args.native_banks else [])
    base, generated = (local(ROOT, x).resolve() for x in (args.out, args.generated))
    require(base.is_relative_to(RUNS) and generated.is_relative_to(RUNS), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=base))
    doc = dict(status='fail', backend='f2' if args.mode == 'vivado' else 'eda',
               source_root=str(ROOT), observed_utc=datetime.now(timezone.utc).isoformat(),
               scope='generated local FAME witness connected to native collector; component only',
               physical_fpga_capture=False, deployable_capture_image=False, global_target_cut_proven=False,
               native_banks=args.native_banks, sources={n: file_sha(ROOT / n) for n in sources},
               generated_path=str(generated), generated={n: file_sha(generated / n) for n in generated_files}, commands=[])

    def run(argv, name, work=out, expected=0):
        log = out / (name + '.log')
        row = dict(argv=list(map(str, argv)), cwd=str(work), log=str(log))
        doc['commands'].append(row)
        with log.open('x') as stream:
            row['returncode'] = subprocess.run(row['argv'], cwd=work, stdout=stream, stderr=subprocess.STDOUT).returncode
        require(row['returncode'] == expected, 'inspect underlying tool log: ' + str(log))
        return log.read_text()

    try:
        compiler_receipt = local(ROOT, args.compiler_receipt).resolve()
        require(compiler_receipt.is_relative_to(RUNS), 'compiler receipt outside runs')
        compiler = json.loads(compiler_receipt.read_text())
        require(compiler['status'] == 'pass' and compiler['backend'] == 'f2' and compiler['returncode'] == 0,
                'successful native Scala fixture emission required')
        require(SCALA + 'main/scala/midas/checkpoint/FAMEClockCutWiring.scala' in compiler['sources']
                and SCALA + 'test/scala/midas/checkpoint/FAMEClockProgressSpec.scala' in compiler['sources'],
                'compiler did not bind generator and real FAME fixture source')
        for n, digest in compiler['sources'].items():
            require(file_sha(local(ROOT, n)) == digest, 'compiler source changed: ' + n)
        for n in generated_files:
            key = 'generated/bank/' + ('fame-native-cut/' if args.native_banks else 'fame-cut/') + n
            require(compiler['artifacts'].get(key) == file_sha(generated / n),
                    'RTL or binding differs from compiler-produced fixture: ' + n)
            require(file_sha(compiler_receipt.parent / key) == compiler['artifacts'][key],
                    'compiler fixture changed: ' + n)
        doc['compiler_receipt'] = dict(path=str(compiler_receipt), sha256=file_sha(compiler_receipt))
        b = json.loads((generated / 'binding.json').read_text())
        require(b['scope'] == ('local_fame_witness_native_banks_staged_f2_collector_sibling_only' if args.native_banks
                              else 'local_fame_witness_connected_f2_collector_sibling_only')
                and b['reference_sha256'] == file_sha(generated / 'reference.fir')
                and b['wired_reference_sha256'] == file_sha(generated / 'wired.fir')
                and b['manifest_sha256'] == file_sha(generated / 'manifest.json')
                and b['plan_sha256'] == file_sha(generated / 'plan.json')
                and b['collector_binding_sha256'] == file_sha(generated / 'collector-binding.json')
                and b['primary_domain'] == 'clockA' and b['label_role'] == 'applied'
                and b['fame_owner_bit'] == b['external_owners'] == 3 and b['new_storage_bits'] == 0
                and b['global_target_cut_proven'] is False and b['deployable_capture_image'] is False,
                'generated witness binding differs')
        for n in generated_files:
            shutil.copyfile(generated / n, out / n)
        if args.native_banks:
            for field, name in [('bank_binding_sha256', 'banks-binding.json'),
                                ('staging_binding_sha256', 'staging-binding.json'),
                                ('dependencies_sha256', 'dependencies.json'),
                                ('witness_manifest_sha256', 'witness-manifest.json'),
                                ('witness_plan_sha256', 'witness-plan.json')]:
                require(b[field] == file_sha(generated / name), 'changed native binding ' + field)
            bank_rows = json.loads((generated / 'banks-binding.json').read_text())['state']
            require(len(bank_rows) == b['functional_entries'], 'native entry coverage differs')
            reads, saves, checks = [], [], []
            for index, row in enumerate(bank_rows):
                require(row['depth'] == 1 and 0 < row['width'] <= 64, 'fixture must cover scalar original storage')
                path = row['hierarchy'].replace('Top.', 'dut.', 1)
                saves.append(f"native_cut[{index}]=64'({path}); check(!$isunknown(native_cut[{index}]),\"known_cut_entry_{index}\");")
                checks.append(f"check(64'({path})===native_cut[{index}],\"atomic_native_cut_entry_{index}\");")
                reads.append(f"read_bank(8'd{row['bank']},16'd{row['slot']},native_cut[{index}]);")
            (out / 'fame-bank-reads.svh').write_text(
                f'reg [63:0] native_cut[0:{len(bank_rows)-1}];\n' +
                '\n'.join('task ' + name + ';\n' + '\n'.join(body) + '\nendtask' for name, body in
                          [('save_native_cut', saves), ('check_native_cut', checks), ('read_native_cut', reads)]) + '\n')
        for n in rtl:
            shutil.copyfile(ROOT / VERILOG / n, out / n)
        for n in ('fame_clock_cut_tb.sv', 'checkpoint_widget_exit.cc'):
            shutil.copyfile(ROOT / 'tools/checkpoint_formats/tests' / n, out / n)
        if args.mode == 'vivado':
            require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore'), 'native synthesis belongs on current manager')
            vendor = Path(os.environ['XILINX_VIVADO']) / 'data/verilog/src'
            doc['vendor_models'] = {}
            for n, source in [('BUFGCE.v', vendor / 'unisims/BUFGCE.v'), ('glbl.v', vendor / 'glbl.v')]:
                shutil.copyfile(source, out / n)
                doc['vendor_models'][n] = dict(original_path=str(source), sha256=file_sha(source))
            # Read only generated DUT and actual collector RTL, never the testbench or reference.
            (out / 'synth.tcl').write_text(TCL.replace('[glob *.sv]', '{wired.sv ' + ' '.join(rtl) + '}'))
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl', '-log', 'vivado.log', '-journal', 'vivado.jou'], 'native')
            require('Vivado v2025.2' in text and 'FAME_CUT_NATIVE_PASS observer_bits=321 gates=3' in text
                    and not re.search('ERROR:|CRITICAL WARNING:', text), 'native synthesis incomplete')
            doc['implementation_timing_proven'] = False
        else:
            require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore'), 'VCS belongs on EDA')
            native = local(ROOT, args.native).resolve()
            receipt = native / 'summary.json'; bound = json.loads(receipt.read_text())
            require(bound['status'] == 'pass' and bound['backend'] == 'f2' and bound['sources'] == doc['sources']
                    and bound['generated'] == doc['generated'], 'native inputs differ')
            for n, digest in bound['artifacts'].items():
                path = (native / n).resolve()
                require(path.is_relative_to(native) and file_sha(path) == digest, 'native artifact changed: ' + n)
            doc['native_receipt'] = dict(path=str(receipt), sha256=file_sha(receipt))
            for n in ('BUFGCE.v', 'glbl.v'):
                shutil.copyfile(native / n, out / n)
            reference = (out / 'reference.sv').read_text()
            for n in ('Top', 'Model'):
                reference = re.sub(r'\b' + n + r'\b', 'Reference' + n, reference)
            (out / 'reference-renamed.sv').write_text(reference)
            run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-debug_access+all',
                 '-debug_region+cell+encrypt', '-Mupdate', '-top', 'fame_clock_cut_tb', '-top', 'glbl',
                 '-Mdir=' + str(out / 'csrc'), '-o', out / 'simv',
                 *(['+define+FAME_NATIVE_BANKS', '+incdir+' + str(out)] if args.native_banks else []),
                 *[out / n for n in ('BUFGCE.v', 'glbl.v', 'wired.sv', 'reference-renamed.sv', *rtl, 'fame_clock_cut_tb.sv')],
                 out / 'checkpoint_widget_exit.cc', '-CFLAGS', '-std=c++17'], 'compile')
            doc['cases'] = {}
            cases = [('healthy', []), ('corrupt', ['+corrupt']),
                     *[('fault-' + str(i), ['+fault=' + str(i)]) for i in range(10)]]
            if args.native_banks:
                cases += [('native-fault-' + str(i), ['+native_fault=' + str(i)]) for i in range(3)]
                cases += [('native-drift', ['+native_drift'])]
            for case, extra in cases:
                work = out / case; work.mkdir()
                text = run([out / 'simv', '-no_save', *extra], case, work, 1 if case in ('corrupt', 'native-drift') else 0)
                if case == 'corrupt':
                    require(re.search(r'FAME_CUT_DIVERGENCE host_step=17 cycle=\d+ acknowledged=16 signal=clockA_applied', text),
                            'first divergence was acknowledged or missed')
                elif case == 'healthy':
                    require(re.search(r'FAME_CUT_PASS checks=\d+ cycles=512 .* cuts=4 mutations=261', text), 'active scope incomplete')
                elif case == 'native-drift':
                    require('signal=atomic_native_cut_entry_' in text and 'FAME_NATIVE_BANK_CAPTURE' not in text,
                            'original fired-flag drift escaped the cut baseline before read acknowledgement')
                elif case.startswith('native-fault-'):
                    require('FAME_NATIVE_REJECT fault=' + case[13:] + ' acknowledged=17 reads=0' in text,
                            'unsafe native bank traffic acknowledged')
                else:
                    require('FAME_CUT_REJECT fault=' + case[6:] + ' acknowledged=17' in text, 'unsafe cut accepted')
                require((work / 'fame-cut.vcd').stat().st_size > 1000, 'full debug waveform absent')
                doc['cases'][case] = dict(log=str(out / (case + '.log')), waveform=str(work / 'fame-cut.vcd'))
        if args.mode == 'vcs':
            from tools.checkpoint_formats.tests.audit_fame_clock_cut import audit_wave
            doc['raw_wave_audit'] = audit_wave(out / 'healthy/fame-cut.vcd', bank_rows if args.native_banks else None)
        require(doc['sources'] == {n: file_sha(ROOT / n) for n in sources}, 'sources changed during execution')
        require(doc['generated'] == {n: file_sha(generated / n) for n in generated_files}, 'compiler inputs changed')
        doc['status'] = 'pass'
    except Exception as error:
        doc['error'] = str(error)
        raise
    finally:
        doc['artifacts'] = {str(p.relative_to(out)): file_sha(p) for p in out.rglob('*')
                            if p.is_file() and p.suffix in {'.log', '.rpt', '.sv', '.svh', '.v', '.cc', '.fir', '.json', '.tcl', '.dcp', '.vcd', '.txt'}}
        receipt = out / 'summary.json'; receipt.write_text(json.dumps(doc, indent=2) + '\n'); print(receipt, flush=True)


if __name__ == '__main__':
    main()
