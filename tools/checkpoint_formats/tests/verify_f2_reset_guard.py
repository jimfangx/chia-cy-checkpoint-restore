"""Synthesize literal F2 reset writers here; verify their guarded cut on EDA.

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
SOURCES = [RTL + n for n in ('CheckpointPhysicalClockCut.sv', 'CheckpointResetOwnedClockCut.sv', 'CheckpointF2ResetGuard.sv')]
SOURCES += [TEST + n for n in ('f2_reset_guard_fixture.sv', 'f2_reset_guard_tb.sv', 'checkpoint_widget_exit.cc',
                              'verify_f2_reset_guard.py', 'test_f2_shell_reset.py')]
SOURCES += ['tools/checkpoint_formats/f2_shell_reset.py']
FAULTS = ('reset', 'ddr', 'release-reset', 'release-ddr', 'writer', 'owner')
TCL = '''read_verilog -sv shell-writers.sv CheckpointPhysicalClockCut.sv CheckpointResetOwnedClockCut.sv CheckpointF2ResetGuard.sv f2_reset_guard_fixture.sv
synth_design -top F2ResetGuardFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 4} {error "expected root and three native gates"}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "unexpected CE_TYPE"}}
set cancel [get_cells guard/source_lost_reg]
if {[llength $cancel] != 1 || [get_property REF_NAME $cancel] ne "FDPE"} {error "source loss must retain an asynchronously set cancellation flop"}
set writers [get_cells -hier -filter {NAME =~ shell/* && IS_SEQUENTIAL == 1}]
if {[llength $writers] != 4} {error "original four shell writer flops required"}
foreach writer $writers {if {[get_property REF_NAME $writer] ne "FDCE"} {error "shell asynchronous assertion changed"}}
report_utilization -file synth-utilization.rpt
report_timing_summary -file synth-timing.rpt
write_checkpoint -force f2-reset-guard.dcp
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
puts "F2_RESET_GUARD_TIMING setup_ns=$setup hold_ns=$hold sequential=[llength $original]"
write_checkpoint -force implemented-f2-reset-guard.dcp
if {$setup < 0 || $hold < 0} {error "component failed unchanged 140 MHz timing"}
puts "F2_RESET_GUARD_NATIVE_PASS gates=4 shell_writers=4 asynchronous_cancel=1"
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ledger(path, doc):
    require(doc['status'] == 'pass' and doc['backend'] == 'f2' and doc['physical_fpga_capture'] is False,
            'successful native component receipt required')
    require(doc['sources'] == {n: sha(ROOT / n) for n in SOURCES}, 'native source mismatch')
    for name, digest in doc['artifacts'].items():
        p = (path / name).resolve()
        require(p.is_relative_to(path) and p.is_file() and p.stat().st_size and sha(p) == digest,
                'native artifact changed: ' + name)
    require((path / 'synth.tcl').read_text() == TCL, 'native synthesis contract changed')
    writers, binding = extract((path / 'original-cl_firesim.sv').read_text())
    require((path / 'shell-writers.sv').read_text() == writers and
            json.loads((path / 'shell-binding.json').read_text()) == binding, 'shell binding changed')
    for name in SOURCES:
        require(sha(path / Path(name).name) == doc['sources'][name], 'native source snapshot changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('vivado', 'vcs'))
    parser.add_argument('--native', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base = local(ROOT, args.out).resolve()
    require(base.is_relative_to(RUNS), 'evidence must be beneath runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=base))
    doc = dict(status='fail', backend='f2' if args.mode == 'vivado' else 'eda',
               observed_utc=datetime.now(timezone.utc).isoformat(), source_root=str(ROOT),
               scope='literal shell-reset boundary component only', physical_fpga_capture=False,
               deployable_capture_image=False, shell_restore_supported=False,
               complete_shell_timing=False, sources={n: sha(ROOT / n) for n in SOURCES}, commands=[])

    def run(argv, name, work=out):
        log = out / (name + '.log')
        row = dict(argv=list(map(str, argv)), cwd=str(work), log=str(log))
        doc['commands'].append(row)
        with log.open('x') as stream:
            row['returncode'] = subprocess.run(row['argv'], cwd=work, stdout=stream, stderr=subprocess.STDOUT).returncode
        require(row['returncode'] == 0, 'inspect underlying tool log: ' + str(log))
        return log.read_text()

    try:
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
            (out / 'synth.tcl').write_text(TCL)
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl', '-log', 'vivado.log', '-journal', 'vivado.jou'], 'native')
            match = re.search(r'F2_RESET_GUARD_TIMING setup_ns=([-0-9.]+) hold_ns=([-0-9.]+) sequential=(\d+)', text)
            require(match and 'Vivado v2025.2' in text and 'F2_RESET_GUARD_NATIVE_PASS gates=4 shell_writers=4 asynchronous_cancel=1' in text
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
            for name in ('original-cl_firesim.sv', 'shell-writers.sv', 'shell-binding.json', 'BUFGCE.v', 'glbl.v'):
                shutil.copyfile(native / name, out / name)
            doc['native_receipt'] = dict(path=str(native / 'summary.json'), sha256=sha(native / 'summary.json'))
            doc['shell_source'] = nd['shell_source']
            work = out / 'healthy'; work.mkdir()
            run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
                 '-top', 'f2_reset_guard_tb', '-top', 'glbl', '-Mdir=' + str(work / 'csrc'), '-o', work / 'simv',
                 *[out / n for n in ('BUFGCE.v', 'glbl.v', 'shell-writers.sv', 'CheckpointPhysicalClockCut.sv',
                                    'CheckpointResetOwnedClockCut.sv', 'CheckpointF2ResetGuard.sv', 'f2_reset_guard_fixture.sv',
                                    'f2_reset_guard_tb.sv', 'checkpoint_widget_exit.cc')]], 'compile', work=work)
            text = run([work / 'simv', '-no_save'], 'healthy', work=work)
            match = re.search(r'F2_RESET_GUARD_PASS checks=(\d+) cycles=320 cuts=4 stalls=64', text)
            require(match and re.findall(r'F2_RESET_GUARD_CUT target_cycle=(\d+)', text) == ['0', '17', '128', '256'],
                    'incomplete original-reference execution')
            doc.update(checks=int(match[1]), cycles=320, cuts=[0,17,128,256], stalls=64)
            for fault in FAULTS:
                trial = out / fault; trial.mkdir()
                text = run([work / 'simv', '-no_save', '+fault=' + fault], fault, work=trial)
                require('F2_RESET_GUARD_REJECT fault=' + fault + ' target_cycle=17 acknowledged_edges=0' in text
                        and 'F2_RESET_GUARD_PASS' not in text, 'fault did not reject: ' + fault)
            require(len(list(out.rglob('*.vcd'))) == 7 and all(p.stat().st_size for p in out.rglob('*.vcd')),
                    'seven full-visibility debug waves required')
            doc['faults'] = list(FAULTS)
        require(doc['sources'] == {n: sha(ROOT / n) for n in SOURCES}, 'source changed during verification')
        doc['status'] = 'pass'
    except Exception as error:
        doc.update(error=str(error), error_type=type(error).__name__)
        raise
    finally:
        doc['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()
                            and p.suffix in ('.log', '.jou', '.rpt', '.dcp', '.vcd', '.tcl', '.sv', '.v', '.py', '.cc', '.json')}
        doc['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (out / 'summary.json').write_text(json.dumps(doc, indent=2) + '\n')
        print(out / 'summary.json', flush=True)


if __name__ == '__main__':
    main()
