"""Native F2-part synthesis and fresh EDA execution of reset-owned clock cuts.

This is component evidence. It supplies no complete Rocket owner manifest,
checkpoint-enabled AFI, hardware image or CPU migration acceptance.
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
import zipfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.regression_runner import local

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
RTL = 'sims/firesim/sim/midas/src/main/verilog/'
SOURCES = (RTL + 'CheckpointResetOwnedClockCut.sv', RTL + 'CheckpointPhysicalClockCut.sv',
           'tools/checkpoint_formats/tests/reset_owned_clock_cut_tb.sv',
           'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',
           'tools/checkpoint_formats/tests/verify_reset_owned_clock_cut.py')
FAULTS = ('reset0', 'reset1', 'release-reset', 'writer', 'owner')
FIXTURE = '''module ResetOwnedCutSynthesisFixture(
  input wire clock, controller_reset, freeze_request, reset_writer_present,
  input wire [1:0] reset_in,
  input wire [3:0] owner_present,
  output wire [1:0] functional_reset, captured_reset,
  output wire [2:0] captured_ce, physical_error, reset_error,
  output wire [63:0] cut_cycle,
  output wire stopped, read_enable, failed,
  output wire [77:0] control_state,
  output wire [95:0] state_out
);
  wire root_clock;
  wire [2:0] gate_clock;
  reg [63:0] target_cycle;
  reg [31:0] state0,state1,state2;
  wire [2:0] ce=functional_reset[0]?3'b111:
    {target_cycle[1]^target_cycle[0],target_cycle[2],!target_cycle[0]};
  CheckpointResetOwnedClockCut #(.GATES(3),.OWNERS(4),.RESETS(2)) cut(
    .clock(clock),.controller_reset(controller_reset),.freeze_request(freeze_request),
    .reset_writer_present(reset_writer_present),.reset_in(reset_in),
    .functional_reset(functional_reset),.captured_reset(captured_reset),
    .owner_present(owner_present),.ce(ce),.target_cycle(target_cycle),
    .root_clock(root_clock),.gate_clock(gate_clock),
    .captured_ce(captured_ce),.cut_cycle(cut_cycle),.stopped(stopped),
    .read_enable(read_enable),.failed(failed),.physical_error(physical_error),
    .reset_error(reset_error),.control_state(control_state));
  always @(posedge root_clock)
    if(controller_reset)target_cycle<=0;else target_cycle<=target_cycle+1;
  always @(posedge gate_clock[0])
    if(functional_reset[0])state0<=1;else state0<=(state0*33)^target_cycle[31:0];
  always @(posedge gate_clock[1])
    if(functional_reset[1])state1<=2;else state1<=(state1*33)^(target_cycle[31:0]+1);
  always @(posedge gate_clock[2])
    if(functional_reset[0])state2<=3;else state2<=(state2*33)^(target_cycle[31:0]+2);
  assign state_out={state2,state1,state0};
endmodule
'''
TCL = '''read_verilog -sv sources/CheckpointPhysicalClockCut.sv sources/CheckpointResetOwnedClockCut.sv fixture.sv
synth_design -top ResetOwnedCutSynthesisFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 4} {error "expected one root and three native gates"}
foreach gate $gates {
  if {[get_property CE_TYPE $gate] ne "SYNC"} {error "unexpected clock gate contract"}
}
set fall [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]
if {[llength $fall] != 3} {error "expected physical mask and two reset cut bits: $fall"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force reset-owned-cut.dcp
puts "RESET_CUT_SYNTH_PASS gates=4 falling_edge_registers=3"
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_native(path):
    path = local(ROOT, path).resolve()
    require(path.is_relative_to(RUNS), 'native evidence must be below runs')
    doc = json.loads((path / 'summary.json').read_text())
    require(doc['status'] == 'pass' and doc['backend'] == 'f2' and
            doc['physical_fpga_capture'] is False, 'successful native component execution required')
    require(doc['sources'] == {n: sha(ROOT / n) for n in SOURCES}, 'native sources changed')
    for name, digest in doc['sources'].items():
        require(sha(path / 'sources' / Path(name).name) == digest, 'native source snapshot changed: ' + name)
    require(set(doc['inputs']) == {str(Path('sources') / Path(n).name) for n in SOURCES} |
            {'fixture.sv', 'synth.tcl', 'BUFGCE.v', 'glbl.v'}, 'incomplete native input ledger')
    require(set(doc['artifacts']) == {'reset-owned-cut.dcp', 'utilization.rpt', 'timing.rpt',
                                      'synth.log', 'vivado.log', 'vivado.jou'}, 'incomplete native artifact ledger')
    for group in ('inputs', 'artifacts'):
        require(bool(doc[group]), 'missing native ' + group)
        for name, digest in doc[group].items():
            p = (path / name).resolve()
            require(p.is_relative_to(path) and p.is_file() and p.stat().st_size > 0 and
                    sha(p) == digest, 'changed native evidence: ' + name)
    require((path / 'fixture.sv').read_text() == FIXTURE and
            (path / 'synth.tcl').read_text() == TCL, 'changed native synthesis contract')
    require(len(doc['commands']) == 1 and doc['commands'][0]['returncode'] == 0 and
            doc['commands'][0]['argv'] == ['vivado', '-mode', 'batch', '-source', 'synth.tcl',
                                          '-log', 'vivado.log', '-journal', 'vivado.jou'],
            'missing native execution command')
    log = (path / 'synth.log').read_text()
    require('Vivado v2025.2' in log and 'RESET_CUT_SYNTH_PASS gates=4 falling_edge_registers=3' in log
            and not re.search(r'ERROR:|CRITICAL WARNING:', log), 'native tool did not complete')
    with zipfile.ZipFile(path / 'reset-owned-cut.dcp') as dcp:
        require(dcp.testzip() is None and any(n.endswith('.edf') for n in dcp.namelist()), 'invalid DCP')
    return path, doc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado', 'vcs', 'audit'), required=True)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--eda', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base = local(ROOT, args.out).resolve()
    require(base.is_relative_to(RUNS), 'evidence must be below runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=base))
    summary = dict(status='fail', backend='eda' if args.mode == 'vcs' else 'f2',
                   observed_utc=datetime.now(timezone.utc).isoformat(), source_root=str(ROOT),
                   physical_fpga_capture=False, full_rocket_image_build=False,
                   scope='synchronous-reset-owned common-source clock-cut component only',
                   sources={n: sha(ROOT / n) for n in SOURCES}, commands=[])

    def run(argv, name, work=out, expected=0):
        log = out / (name + '.log')
        row = dict(argv=list(map(str, argv)), cwd=str(work), log=str(log))
        summary['commands'].append(row)
        with log.open('x') as stream:
            row['returncode'] = subprocess.run(row['argv'], cwd=work, stdout=stream,
                                              stderr=subprocess.STDOUT).returncode
        row['log_sha256'] = sha(log)
        require(row['returncode'] == expected, 'inspect underlying compiler/runtime log: ' + str(log))
        return log.read_text()

    try:
        if args.mode == 'vivado':
            require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),
                    'source native HDK on manager; synthesis cannot run on EDA')
            (out / 'sources').mkdir()
            for name in SOURCES:
                shutil.copyfile(ROOT / name, out / 'sources' / Path(name).name)
            (out / 'fixture.sv').write_text(FIXTURE)
            (out / 'synth.tcl').write_text(TCL)
            vendor = Path(os.environ['XILINX_VIVADO']) / 'data/verilog/src'
            summary['vendor_models'] = {}
            for name, origin in [('BUFGCE.v', vendor / 'unisims/BUFGCE.v'), ('glbl.v', vendor / 'glbl.v')]:
                shutil.copyfile(origin, out / name)
                summary['vendor_models'][name] = dict(original_path=str(origin), sha256=sha(origin))
            run(['vivado', '-mode', 'batch', '-source', 'synth.tcl', '-log', 'vivado.log', '-journal', 'vivado.jou'], 'synth')
            summary['inputs'] = {str(p.relative_to(out)): sha(p) for p in (out / 'sources').iterdir()}
            summary['inputs'].update({n: sha(out / n) for n in ('fixture.sv', 'synth.tcl', 'BUFGCE.v', 'glbl.v')})
            summary['artifacts'] = {n: sha(out / n) for n in ('reset-owned-cut.dcp', 'utilization.rpt',
                                                                       'timing.rpt', 'synth.log', 'vivado.log', 'vivado.jou')}
            summary['status'] = 'pass'
            (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
            validate_native(out)
        elif args.mode == 'vcs':
            require(ROOT == Path('/scratch/jfx/chia-cy-checkpoint-restore') and
                    os.environ.get('VCS_HOME') == toolchain.VCS_HOME and Path(toolchain.VCS).is_file(),
                    'VCS requires EDA with vcs-env.sh sourced last')
            native_path, native = validate_native(args.native)
            for name in native['inputs']:
                p = out / name
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(native_path / name, p)
            work = out / 'healthy'
            work.mkdir()
            run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
                 '-top', 'reset_owned_clock_cut_tb', '-top', 'glbl', '-Mdir=' + str(work / 'csrc'),
                 '-o', work / 'simv', out / 'BUFGCE.v', out / 'glbl.v',
                 *[out / 'sources' / n for n in ('CheckpointPhysicalClockCut.sv', 'CheckpointResetOwnedClockCut.sv',
                   'reset_owned_clock_cut_tb.sv', 'checkpoint_widget_exit.cc')]], 'compile', work)
            text = run([work / 'simv', '-no_save'], 'healthy', work)
            match = re.search(r'RESET_CUT_PASS checks=(\d+) cycles=320 cuts=4 stalls=64', text)
            require(match is not None and 'RESET_CUT_DIVERGENCE' not in text, 'incomplete healthy execution')
            summary.update(checks=int(match[1]), cuts=[0, 17, 128, 256], cycles=320, stalls=64)
            for fault in FAULTS:
                trial = out / fault
                trial.mkdir()
                text = run([work / 'simv', '-no_save', '+fault=' + fault], fault, trial)
                require('RESET_CUT_REJECT fault=' + fault + ' target_cycle=17 acknowledged_edges=0' in text and
                        'RESET_CUT_PASS' not in text, 'fault was not rejected: ' + fault)
            trial = out / 'corrupt'
            trial.mkdir()
            text = run([work / 'simv', '-no_save', '+corrupt'], 'corrupt', trial, expected=1)
            require('RESET_CUT_DIVERGENCE target_cycle=17 reason=captured_reset[0]' in text and
                    'RESET_CUT_PASS' not in text, 'independent semantic oracle did not stop')
            waves = list(out.rglob('*.vcd'))
            require(len(waves) == 7 and all(p.stat().st_size > 0 for p in waves), 'missing debug waveforms')
            summary.update(inputs=native['inputs'], sources=native['sources'],
                           native_receipt=dict(path=str(native_path / 'summary.json'), sha256=sha(native_path / 'summary.json')),
                           negative_tests=[*FAULTS, 'captured_reset[0]'],
                           artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                                      if p.is_file() and p.suffix in ('.log', '.vcd')})
        else:
            native_path, native = validate_native(args.native)
            eda_path = local(ROOT, args.eda).resolve()
            require(eda_path.is_relative_to(RUNS), 'EDA evidence must be below runs')
            eda = json.loads((eda_path / 'summary.json').read_text())
            require(eda['status'] == 'pass' and eda['backend'] == 'eda' and
                    eda['sources'] == native['sources'] and eda['inputs'] == native['inputs'] and
                    eda['cuts'] == [0, 17, 128, 256] and eda['cycles'] == 320 and eda['stalls'] == 64 and
                    eda['negative_tests'] == [*FAULTS, 'captured_reset[0]'], 'incomplete/mismatched EDA execution')
            require(eda['native_receipt']['sha256'] == sha(native_path / 'summary.json'), 'wrong native receipt')
            for name, digest in eda['artifacts'].items():
                require(sha(eda_path / name) == digest, 'changed EDA artifact: ' + name)
            require(len(eda['commands']) == 8 and
                    [r['returncode'] for r in eda['commands']] == [0] * 7 + [1], 'incomplete EDA command scope')
            require(len(list(eda_path.rglob('*.vcd'))) == 7, 'incomplete debug wave scope')
            summary.update(checks=eda['checks'], matching_sources=len(SOURCES),
                           native_receipt=str(native_path / 'summary.json'), eda_receipt=str(eda_path / 'summary.json'))
        require(summary['sources'] == {n: sha(ROOT / n) for n in SOURCES}, 'sources changed during verification')
        summary['status'] = 'pass'
    except Exception as error:
        summary.update(status='fail', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        summary['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(out / 'summary.json', flush=True)


if __name__ == '__main__':
    main()
