"""Synthesize generated held-reset wiring locally; execute it only on EDA VCS.

Component evidence only. Neither the retained Rocket structural audit nor this
small generated execution supplies production owners or physical FPGA capture.
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
from tools.checkpoint_formats.regression_runner import local

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
RTL = 'sims/firesim/sim/midas/src/main/verilog/'
TEST = 'tools/checkpoint_formats/tests/'
SCALA = 'sims/firesim/sim/midas/src/'
SOURCES = [RTL + n for n in ('CheckpointPhysicalClockCut.sv', 'CheckpointResetOwnedClockCut.sv')]
SOURCES += [TEST + n for n in ('reset_cut_wiring_fixture.sv', 'reset_cut_wiring_tb.sv',
                              'checkpoint_widget_exit.cc', 'verify_reset_cut_wiring.py')]
SOURCES += [SCALA + n for n in ('main/scala/midas/checkpoint/SynchronousResetCutWiring.scala',
                               'main/scala/midas/checkpoint/PhysicalClockCutWiring.scala',
                               'main/scala/midas/checkpoint/PhysicalClockCutPlan.scala',
                               'main/scala/midas/stage/GoldenGateCli.scala',
                               'test/scala/midas/checkpoint/SynchronousResetCutWiringSpec.scala')]
TCL = '''read_verilog -sv wired.sv CheckpointPhysicalClockCut.sv CheckpointResetOwnedClockCut.sv reset_cut_wiring_fixture.sv
synth_design -top ResetCutWiringFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 3} {error "expected generated root and two native gates"}
foreach gate $gates {
  if {[get_property CE_TYPE $gate] ne "SYNC"} {error "unexpected native gate"}
}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force reset-routing.dcp
puts "RESET_ROUTING_SYNTH_PASS gates=3"
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', required=True, choices=['vivado', 'vcs'])
    p.add_argument('--generated', required=True, type=Path)
    p.add_argument('--native', type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    base = local(ROOT, args.out).resolve()
    require(base.is_relative_to(RUNS), 'evidence must be beneath runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=base))
    generated = local(ROOT, args.generated).resolve()
    names = ('reference.fir', 'reference.sv', 'wired.fir', 'wired.sv', 'audit.json', 'binding.json')
    summary = dict(status='fail', backend='eda' if args.mode == 'vcs' else 'f2',
                   observed_utc=datetime.now(timezone.utc).isoformat(), source_root=str(ROOT),
                   physical_fpga_capture=False, full_rocket_image=False,
                   sources={n: sha(ROOT / n) for n in SOURCES}, generated_path=str(generated),
                   generated={n: sha(generated / n) for n in names}, commands=[])

    def run(argv, name, expected=0, work=out):
        log = out / (name + '.log')
        row = dict(argv=list(map(str, argv)), cwd=str(work), log=str(log))
        summary['commands'].append(row)
        with log.open('x') as stream:
            row['returncode'] = subprocess.run(row['argv'], cwd=work, stdout=stream, stderr=subprocess.STDOUT).returncode
        require(row['returncode'] == expected, 'inspect underlying tool log: ' + str(log))
        return log.read_text()

    try:
        for n in names:
            shutil.copyfile(generated / n, out / n)
        for n in SOURCES:
            shutil.copyfile(ROOT / n, out / Path(n).name)
        if args.mode == 'vivado':
            require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),
                    'native synthesis belongs on the current manager')
            vendor = Path(os.environ['XILINX_VIVADO']) / 'data/verilog/src'
            summary['vendor_models'] = {}
            for n, origin in [('BUFGCE.v', vendor / 'unisims/BUFGCE.v'), ('glbl.v', vendor / 'glbl.v')]:
                shutil.copyfile(origin, out / n)
                summary['vendor_models'][n] = dict(original_path=str(origin), sha256=sha(origin))
            (out / 'synth.tcl').write_text(TCL)
            text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl', '-log', 'vivado.log', '-journal', 'vivado.jou'], 'synth')
            require('Vivado v2025.2' in text and 'RESET_ROUTING_SYNTH_PASS gates=3' in text and
                    not re.search(r'ERROR:|CRITICAL WARNING:', text), 'incomplete native synthesis')
        else:
            require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore') and
                    os.environ.get('VCS_HOME') == toolchain.VCS_HOME, 'VCS requires EDA SP2 and native license setup')
            native = local(ROOT, args.native).resolve()
            doc = json.loads((native / 'summary.json').read_text())
            require(doc['status'] == 'pass' and doc['backend'] == 'f2' and doc['sources'] == summary['sources'] and
                    doc['generated'] == summary['generated'], 'native source/generation mismatch')
            for n, h in doc['artifacts'].items():
                require(sha(native / n) == h, 'native artifact changed: ' + n)
            for n in ('BUFGCE.v', 'glbl.v'):
                require(sha(native / n) == doc['vendor_models'][n]['sha256'], 'vendor model mismatch')
                shutil.copyfile(native / n, out / n)
            summary['native_receipt'] = dict(path=str(native / 'summary.json'), sha256=sha(native / 'summary.json'))
            # Only module identifiers change in the independently emitted original.
            text = (out / 'reference.sv').read_text()
            for before, after in [('Leaf', 'ResetReferenceLeaf'), ('PhysicalPlanTop', 'ResetRoutingReference')]:
                text = re.sub(r'\b' + before + r'\b', after, text)
            (out / 'reference-renamed.sv').write_text(text)
            work = out / 'healthy'; work.mkdir()
            run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
                 '-top', 'reset_cut_wiring_tb', '-top', 'glbl', '-Mdir=' + str(work / 'csrc'), '-o', work / 'simv',
                 *[out / n for n in ('BUFGCE.v', 'glbl.v', 'reference-renamed.sv', 'wired.sv', 'CheckpointPhysicalClockCut.sv',
                   'CheckpointResetOwnedClockCut.sv', 'reset_cut_wiring_fixture.sv', 'reset_cut_wiring_tb.sv',
                   'checkpoint_widget_exit.cc')]], 'compile', work=work)
            text = run([work / 'simv', '-no_save'], 'healthy', work=work)
            match = re.search(r'RESET_ROUTING_PASS checks=(\d+) cycles=320 cuts=4 stalls=32', text)
            require(match and re.findall(r'RESET_ROUTING_CUT target_cycle=(\d+)', text) == ['0', '17', '128', '256'],
                    'incomplete healthy generated execution')
            summary.update(checks=int(match[1]), cuts=[0, 17, 128, 256], cycles=320, stalls=32)
            for fault in ('reset', 'writer', 'owner', 'corrupt'):
                trial = out / fault; trial.mkdir()
                text = run([work / 'simv', '-no_save', '+corrupt' if fault == 'corrupt' else '+fault=' + fault], fault,
                           expected=1 if fault == 'corrupt' else 0, work=trial)
                required = ('RESET_ROUTING_DIVERGENCE target_cycle=17 signal=left.reset acknowledged_edges=0' if fault == 'corrupt'
                            else 'RESET_ROUTING_REJECT fault=' + fault + ' target_cycle=17 acknowledged_edges=0')
                require(required in text and 'RESET_ROUTING_PASS' not in text, 'fault did not stop: ' + fault)
            waves = list(out.rglob('*.vcd'))
            require(len(waves) == 5 and all(p.stat().st_size > 0 for p in waves), 'missing full debug waves')
        require(summary['sources'] == {n: sha(ROOT / n) for n in SOURCES}, 'sources changed during verification')
        require(summary['generated'] == {n: sha(generated / n) for n in names}, 'generated inputs changed')
        summary['status'] = 'pass'
    except Exception as error:
        summary.update(error=str(error), error_type=type(error).__name__)
        raise
    finally:
        summary['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                                if p.is_file() and p.suffix in ('.log', '.rpt', '.dcp', '.vcd', '.tcl', '.sv', '.v', '.fir', '.json')}
        summary['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(out / 'summary.json', flush=True)


if __name__ == '__main__':
    main()
