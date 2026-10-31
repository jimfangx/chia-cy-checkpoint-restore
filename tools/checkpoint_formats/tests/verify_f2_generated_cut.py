"""Synthesize the F2 shell adapter plus generated clock/reset wiring locally; run VCS on EDA.

This nondeployable component cannot establish shell CDC/timing, production
ownership, an AFI, FPGA capture, or CPU migration. No source shell is edited.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.f2_shell_reset import extract
from tools.checkpoint_formats.regression_runner import local

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
RTL = 'sims/firesim/sim/midas/src/main/verilog/'
TEST = 'tools/checkpoint_formats/tests/'
SHELL = 'sims/firesim/platforms/f2/aws-fpga-firesim-f2/hdk/cl/developer_designs/cl_firesim/design/cl_firesim.sv'
SOURCES = [RTL + n for n in ('CheckpointPhysicalClockCut.sv', 'CheckpointResetOwnedClockCut.sv', 'CheckpointF2ResetGuard.sv', 'CheckpointF2ClockResetCut.sv')]
SOURCES += [TEST + n for n in ('f2_generated_cut_fixture.sv', 'f2_generated_cut_tb.sv', 'checkpoint_widget_exit.cc',
                              'verify_f2_generated_cut.py', 'test_f2_shell_reset.py')]
SOURCES += ['tools/checkpoint_formats/f2_shell_reset.py']
SOURCES += [TEST + 'f2_compiler_cut_fixture.sv', TEST + 'f2_compiler_cut_tb.sv']
SOURCES += ['sims/firesim/sim/midas/src/' + n for n in (
    'main/scala/midas/checkpoint/F2ClockResetCutWiring.scala',
    'main/scala/midas/checkpoint/SynchronousResetCutWiring.scala',
    'main/scala/midas/checkpoint/PhysicalClockCutWiring.scala',
    'main/scala/midas/checkpoint/PhysicalClockCutPlan.scala',
    'main/scala/midas/stage/GoldenGateCli.scala',
    'test/scala/midas/checkpoint/F2ClockResetCutWiringSpec.scala')]
FAULTS = ('reset', 'ddr', 'release-reset', 'release-ddr', 'writer', 'owner')
TCL = '''read_verilog -sv wired.sv shell-writers.sv CheckpointPhysicalClockCut.sv CheckpointResetOwnedClockCut.sv CheckpointF2ResetGuard.sv CheckpointF2ClockResetCut.sv f2_generated_cut_fixture.sv
synth_design -top F2GeneratedCutFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 3} {error "expected generated root and two native gates, with no adapter gates"}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "unexpected CE_TYPE"}}
set cancel [get_cells adapter/guard/source_lost_reg]
if {[llength $cancel] != 1 || [get_property REF_NAME $cancel] ne "FDPE"} {error "source loss must retain an asynchronously set cancellation flop"}
set writers [get_cells -hier -filter {NAME =~ shell/* && IS_SEQUENTIAL == 1}]
if {[llength $writers] != 4} {error "original four shell writer flops required"}
foreach writer $writers {if {[get_property REF_NAME $writer] ne "FDCE"} {error "shell asynchronous assertion changed"}}
report_utilization -file synth-utilization.rpt
report_timing_summary -file synth-timing.rpt
write_checkpoint -force f2-generated-cut.dcp
set original [lsort [get_property NAME [get_cells -hier -filter {IS_SEQUENTIAL == 1}]]]
set_property DONT_TOUCH true [get_cells $original]
opt_design
place_design
phys_opt_design
route_design
set final [lsort [get_property NAME [get_cells -hier -filter {IS_SEQUENTIAL == 1}]]]
if {$original ne $final} {error "sequential identity changed"}
report_utilization -file utilization.rpt
report_timing_summary -report_unconstrained -file timing.rpt
report_route_status -file route-status.rpt
report_drc -file drc.rpt
set setup [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
puts "F2_GENERATED_CUT_TIMING setup_ns=$setup hold_ns=$hold sequential=[llength $original]"
write_checkpoint -force implemented-f2-generated-cut.dcp
if {$setup < 0 || $hold < 0} {error "component failed unchanged 140 MHz timing"}
puts "F2_GENERATED_CUT_NATIVE_PASS gates=3 shell_writers=4 asynchronous_cancel=1"
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def synthesis_contract(compiler_connected):
    if not compiler_connected:
        return TCL
    return TCL.replace('f2_generated_cut_fixture.sv', 'f2_compiler_cut_fixture.sv').replace(
        'get_cells adapter/guard/source_lost_reg',
        'get_cells execution/checkpoint_f2_adapter/guard/source_lost_reg')


def ledger(path, doc):
    require(doc['status'] == 'pass' and doc['backend'] == 'f2' and doc['physical_fpga_capture'] is False,
            'successful native component receipt required')
    require(doc['sources'] == {n: sha(ROOT / n) for n in SOURCES}, 'native source mismatch')
    for name, digest in doc['artifacts'].items():
        p = (path / name).resolve()
        require(p.is_relative_to(path) and p.is_file() and p.stat().st_size and sha(p) == digest,
                'native artifact changed: ' + name)
    require((path / 'synth.tcl').read_text() == synthesis_contract(doc['compiler_connected']),
            'native synthesis contract changed')
    writers, binding = extract((path / 'original-cl_firesim.sv').read_text())
    require((path / 'shell-writers.sv').read_text() == writers and
            json.loads((path / 'shell-binding.json').read_text()) == binding, 'shell binding changed')
    for name in SOURCES:
        require(sha(path / Path(name).name) == doc['sources'][name], 'native source snapshot changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('vivado', 'vcs'))
    parser.add_argument('--native', type=Path)
    parser.add_argument('--generated', required=True, type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--compiler-connected', action='store_true',
                        help='Require the adapter inside the compiler-emitted hierarchy, with no external adapter')
    args = parser.parse_args()
    faults = (*FAULTS, 'raw-reset', 'owner-0', 'owner-1', 'owner-2') if args.compiler_connected else FAULTS
    bench = 'f2_compiler_cut_tb.sv' if args.compiler_connected else 'f2_generated_cut_tb.sv'
    base = local(ROOT, args.out).resolve()
    require(base.is_relative_to(RUNS), 'evidence must be beneath runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=base))
    doc = dict(status='fail', backend='f2' if args.mode == 'vivado' else 'eda',
               observed_utc=datetime.now(timezone.utc).isoformat(), source_root=str(ROOT),
               scope='F2 adapter connected to compiler-emitted reset/clock network; component only', physical_fpga_capture=False,
               deployable_capture_image=False, shell_restore_supported=False,
               complete_shell_timing=False, compiler_connected=args.compiler_connected,
               sources={n: sha(ROOT / n) for n in SOURCES}, commands=[])

    generated = local(ROOT, args.generated).resolve()
    doc['generated_path'] = str(generated)
    names = ('reference.fir', 'reference.sv', 'wired.fir', 'wired.sv', 'audit.json', 'binding.json')
    doc['generated'] = {n: sha(generated / n) for n in names}

    def run(argv, name, work=out, expected=0):
        log = out / (name + '.log')
        row = dict(argv=list(map(str, argv)), cwd=str(work), log=str(log))
        doc['commands'].append(row)
        with log.open('x') as stream:
            row['returncode'] = subprocess.run(row['argv'], cwd=work, stdout=stream, stderr=subprocess.STDOUT).returncode
        require(row['returncode'] == expected, 'inspect underlying tool log: ' + str(log))
        return log.read_text()

    try:
        for name in names:
            shutil.copyfile(generated / name, out / name)
        binding = json.loads((out / 'binding.json').read_text())
        require(binding['deployable_capture_image'] is False and
                sha(out / 'wired.fir') == binding['wired_reference_sha256'] and
                sha(out / 'reference.fir') == binding['reference_sha256'], 'generated binding mismatch')
        if args.compiler_connected:
            require(binding['scope'] == 'compiler_connected_f2_collector_sibling_only' and
                    binding['gates'] == 2 and binding['owners'] == 4 and
                    binding['production_shell_installed'] is False and
                    binding['collector_state_atomically_owned'] is False,
                    'compiler-connected sibling binding required')
            text = (out / 'wired.sv').read_text()
            require(text.count('CheckpointF2ClockResetCut #(') == 1 and
                    'checkpoint_f2_adapter' in text, 'adapter absent from emitted hierarchy')
        for name in SOURCES:
            shutil.copyfile(ROOT / name, out / Path(name).name)
        if args.mode == 'vivado':
            require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),
                    'native Vivado belongs on the current manager')
            shutil.copyfile(ROOT / SHELL, out / 'original-cl_firesim.sv')
            writers, binding = extract((ROOT / SHELL).read_text())
            doc['shell_source'] = dict(path=SHELL, sha256=sha(ROOT / SHELL))
            (out / 'shell-writers.sv').write_text(writers)
            (out / 'shell-binding.json').write_text(json.dumps(binding, indent=2) + '\n')
            vendor = Path(os.environ['XILINX_VIVADO']) / 'data/verilog/src'
            doc['vendor_models'] = {}
            for name, original in [('BUFGCE.v', vendor / 'unisims/BUFGCE.v'), ('glbl.v', vendor / 'glbl.v')]:
                shutil.copyfile(original, out / name)
                doc['vendor_models'][name] = dict(original_path=str(original), sha256=sha(original))
            (out / 'synth.tcl').write_text(synthesis_contract(args.compiler_connected))
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl', '-log', 'vivado.log', '-journal', 'vivado.jou'], 'native')
            match = re.search(r'F2_GENERATED_CUT_TIMING setup_ns=([-0-9.]+) hold_ns=([-0-9.]+) sequential=(\d+)', text)
            require(match and 'Vivado v2025.2' in text and 'F2_GENERATED_CUT_NATIVE_PASS gates=3 shell_writers=4 asynchronous_cancel=1' in text
                    and not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native closure incomplete')
            require(re.search(r'Checks found:\s+0\b', (out / 'drc.rpt').read_text()) and
                    re.search(r'# of nets with routing errors\.+\s+:\s+0\b', (out / 'route-status.rpt').read_text()),
                    'native routing/DRC failed')
            doc['timing'] = dict(setup_ns=float(match[1]), hold_ns=float(match[2]), sequential=int(match[3]))
        else:
            require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore') and os.environ.get('VCS_HOME') == toolchain.VCS_HOME,
                    'VCS requires EDA SP2 with vcs-env.sh sourced last')
            require(args.native is not None, 'native receipt required')
            native = local(ROOT, args.native).resolve()
            require(native.is_relative_to(RUNS), 'native receipt must be beneath runs')
            nd = json.loads((native / 'summary.json').read_text()); ledger(native, nd)
            require(nd['generated'] == doc['generated'], 'native generated input mismatch')
            require(nd['compiler_connected'] == args.compiler_connected, 'native compiler connection mode mismatch')
            for name in ('original-cl_firesim.sv', 'shell-writers.sv', 'shell-binding.json', 'BUFGCE.v', 'glbl.v'):
                shutil.copyfile(native / name, out / name)
            doc['native_receipt'] = dict(path=str(native / 'summary.json'), sha256=sha(native / 'summary.json'))
            doc['shell_source'] = nd['shell_source']
            text = (out / 'reference.sv').read_text()
            for before, after in [('Leaf', 'ResetReferenceLeaf'), ('PhysicalPlanTop', 'ResetRoutingReference')]:
                text = re.sub(r'\b' + before + r'\b', after, text)
            (out / 'reference-renamed.sv').write_text(text)
            work = out / 'healthy'; work.mkdir()
            fixture = 'f2_compiler_cut_fixture.sv' if args.compiler_connected else 'f2_generated_cut_fixture.sv'
            run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
                 '-top', 'f2_generated_cut_tb', '-top', 'glbl', '-Mdir=' + str(work / 'csrc'), '-o', work / 'simv',
                 *[out / n for n in ('BUFGCE.v', 'glbl.v', 'reference-renamed.sv', 'wired.sv', 'shell-writers.sv', 'CheckpointPhysicalClockCut.sv',
                                    'CheckpointResetOwnedClockCut.sv', 'CheckpointF2ResetGuard.sv', 'CheckpointF2ClockResetCut.sv', fixture,
                                    bench, 'checkpoint_widget_exit.cc')]], 'compile', work=work)
            text = run([work / 'simv', '-no_save'], 'healthy', work=work)
            match = re.search(r'F2_GENERATED_CUT_PASS checks=(\d+) cycles=320 cuts=4 stalls=64', text)
            require(match and re.findall(r'F2_GENERATED_CUT_CUT target_cycle=(\d+)', text) == ['0', '17', '128', '256'],
                    'incomplete original-reference execution')
            doc.update(checks=int(match[1]), cycles=320, cuts=[0,17,128,256], stalls=64)
            for fault in faults:
                trial = out / fault; trial.mkdir()
                text = run([work / 'simv', '-no_save', '+fault=' + fault], fault, work=trial)
                require('F2_GENERATED_CUT_REJECT fault=' + fault + ' target_cycle=17 acknowledged_edges=0' in text
                        and 'F2_GENERATED_CUT_PASS' not in text, 'fault did not reject: ' + fault)
            trial = out / 'corrupt'; trial.mkdir()
            text = run([work / 'simv', '-no_save', '+corrupt'], 'corrupt', work=trial, expected=1)
            require('F2_GENERATED_CUT_DIVERGENCE target_cycle=17 signal=left.reset acknowledged_edges=0' in text,
                    'semantic reset corruption did not stop at first divergent signal')
            require(len(list(out.rglob('*.vcd'))) == len(faults) + 2 and all(p.stat().st_size for p in out.rglob('*.vcd')),
                    'complete positive/negative full-visibility debug waves required')
            doc['faults'] = list(faults)
        require(doc['sources'] == {n: sha(ROOT / n) for n in SOURCES}, 'source changed during verification')
        require(doc['generated'] == {n: sha(generated / n) for n in names}, 'generated inputs changed')
        doc['status'] = 'pass'
    except Exception as error:
        doc.update(error=str(error), error_type=type(error).__name__)
        raise
    finally:
        doc['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()
                            and p.suffix in ('.log', '.jou', '.rpt', '.dcp', '.vcd', '.tcl', '.sv', '.v', '.py', '.cc', '.json', '.fir')}
        doc['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (out / 'summary.json').write_text(json.dumps(doc, indent=2) + '\n')
        print(out / 'summary.json', flush=True)


if __name__ == '__main__':
    main()
