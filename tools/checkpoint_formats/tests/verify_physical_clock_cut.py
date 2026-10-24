"""Synthesize the common-clock physical cut here; test exact inputs on EDA VCS.

Component evidence only: no Rocket image, FPGA capture, or complete owner claim.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import zipfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
RTL = 'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalClockCut.sv'
TB = 'tools/checkpoint_formats/tests/physical_clock_cut_tb.sv'
EXIT = 'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc'
SOURCES = (RTL, TB, EXIT, 'tools/checkpoint_formats/tests/verify_physical_clock_cut.py')

FIXTURE = '''module ClockCutSynthesisFixture(
  input wire clock, reset, freeze_request,
  input wire [3:0] owner_present,
  output wire [2:0] captured_ce, error,
  output wire [63:0] cut_cycle,
  output wire stopped, read_enable, failed,
  output wire [95:0] state_out
);
  wire root_clock;
  wire [2:0] gate_clock;
  reg [63:0] target_cycle;
  reg [31:0] state0, state1, state2;
  wire [2:0] ce={target_cycle[1]^target_cycle[0], target_cycle[2], !target_cycle[0]};
  CheckpointPhysicalClockCut #(.GATES(3),.OWNERS(4)) cut(
    .clock(clock),.reset(reset),.freeze_request(freeze_request),.owner_present(owner_present),
    .ce(ce),.target_cycle(target_cycle),.root_clock(root_clock),.gate_clock(gate_clock),
    .captured_ce(captured_ce),.cut_cycle(cut_cycle),.stopped(stopped),.read_enable(read_enable),
    .failed(failed),.error(error));
  always @(posedge root_clock) if(reset) target_cycle<=0; else target_cycle<=target_cycle+1;
  always @(posedge gate_clock[0]) if(reset) state0<=1; else state0<=(state0*33)^target_cycle[31:0];
  always @(posedge gate_clock[1]) if(reset) state1<=2; else state1<=(state1*33)^(target_cycle[31:0]+1);
  always @(posedge gate_clock[2]) if(reset) state2<=3; else state2<=(state2*33)^(target_cycle[31:0]+2);
  assign state_out={state2,state1,state0};
endmodule
'''
TCL = '''read_verilog -sv sources/CheckpointPhysicalClockCut.sv fixture.sv
synth_design -top ClockCutSynthesisFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 4} {error "expected root and three native BUFGCEs: $gates"}
foreach gate $gates {
  if {[get_property CE_TYPE $gate] ne "SYNC"} {error "nondefault gate contract"}
  foreach pin {I CE O} {if {[llength [get_pins $gate/$pin]] != 1} {error "missing public pin"}}
}
set fall [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]
if {[llength $fall] != 1} {error "mask must use exactly one negative-edge register: $fall"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force physical-cut.dcp
puts "PHYSICAL_CUT_SYNTH_PASS gates=4 falling_edge_registers=1"
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado', 'vcs', 'audit'), required=True)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--eda', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base = args.out.resolve()
    require(base.is_relative_to(RUNS), 'evidence must be below runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=base))
    commands = []

    def run(argv, name, cwd=out, expected=0):
        log = out/(name+'.log')
        row = dict(argv=[str(a) for a in argv], cwd=str(cwd), log=str(log))
        commands.append(row)
        with log.open('w') as stream:
            result = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        require(result.returncode == expected, 'inspect underlying log '+str(log))
        return log.read_text()

    def native_input():
        require(args.native is not None and args.native.resolve().is_relative_to(RUNS), 'native execution directory below runs required')
        doc = json.loads((args.native/'summary.json').read_text())
        require(doc['status'] == 'pass' and doc['backend'] == 'f2' and
                doc['full_rocket_image_build'] is False and doc['physical_fpga_capture'] is False,
                'invalid native component receipt')
        for name in SOURCES:
            require(doc['sources'][name] == sha(ROOT/name), 'stale source '+name)
            require(sha(args.native/'sources'/Path(name).name) == doc['sources'][name],
                    'native source snapshot does not match current source '+name)
        for name, value in doc['inputs'].items():
            require(value == sha(args.native/name), 'changed native input '+name)
        for name, value in doc['artifacts'].items():
            require(value == sha(args.native/name), 'changed native artifact '+name)
        require((args.native/'fixture.sv').read_text() == FIXTURE and
                (args.native/'synth.tcl').read_text() == TCL, 'changed native contract')
        with zipfile.ZipFile(args.native/'physical-cut.dcp') as dcp:
            require(dcp.testzip() is None and any(n.endswith('.edf') for n in dcp.namelist()), 'invalid DCP')
        return doc

    summary = dict(status='pass', backend='f2' if args.mode != 'vcs' else 'eda',
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   original_root=str(ROOT), scope='common-clock physical cut component only',
                   physical_fpga_capture=False, full_rocket_image_build=False)
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore'), 'native manager required')
        require(shutil.which('vivado') is not None, 'source native HDK first')
        sources = out/'sources'; sources.mkdir()
        for name in SOURCES:
            (sources/Path(name).name).write_bytes((ROOT/name).read_bytes())
        (out/'fixture.sv').write_text(FIXTURE)
        (out/'synth.tcl').write_text(TCL)
        vendor = Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        origins = {}
        for name, path in [('BUFGCE.v', vendor/'unisims/BUFGCE.v'), ('glbl.v', vendor/'glbl.v')]:
            (out/name).write_bytes(path.read_bytes())
            origins[name] = dict(original_path=str(path), sha256=sha(path))
        summary['vendor_models'] = origins
        text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl', '-log', 'vivado.log', '-journal', 'vivado.jou'], 'synth')
        require('PHYSICAL_CUT_SYNTH_PASS gates=4 falling_edge_registers=1' in text, 'incomplete native synthesis')
        require(not re.search(r'ERROR:|CRITICAL WARNING:', text), 'native synthesis/clock error')
        summary['sources'] = {n: sha(sources/Path(n).name) for n in SOURCES}
        summary['inputs'] = {str(p.relative_to(out)): sha(p) for p in sources.iterdir()}
        summary['inputs'].update({n: sha(out/n) for n in ('fixture.sv','synth.tcl','BUFGCE.v','glbl.v')})
        summary['artifacts'] = {n: sha(out/n) for n in ('physical-cut.dcp','utilization.rpt','timing.rpt','synth.log','vivado.log','vivado.jou','commands.json')}
    elif args.mode == 'vcs':
        require(os.environ.get('VCS_HOME') == toolchain.VCS_HOME and Path(toolchain.VCS).is_file(),
                'VCS must run on EDA with vcs-env.sh sourced last')
        native = native_input()
        for name, value in native['inputs'].items():
            path = out/name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((args.native/name).read_bytes())
            require(sha(path) == value, 'copy mismatch')
        healthy = out/'healthy'; healthy.mkdir()
        run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
             '-top','physical_clock_cut_tb','-top','glbl','-Mdir='+str(healthy/'csrc'),'-o',healthy/'simv',
             out/'BUFGCE.v',out/'glbl.v',out/'sources'/Path(RTL).name,
             out/'sources'/Path(TB).name,out/'sources'/Path(EXIT).name], 'compile', healthy)
        text = run([healthy/'simv','-no_save'], 'healthy', healthy)
        match = re.search(r'PHYSICAL_CUT_PASS checks=(\d+) cycles=320 cuts=4 stalls=64', text)
        require(match is not None, 'missing complete healthy continuation')
        summary['checks'] = int(match[1])
        summary['cuts'] = [0,17,128,256]
        summary['functional_cycles'] = 320
        summary['stalls'] = 64
        summary['negative_tests'] = []
        for fault in ('missing','ce','cycle'):
            work = out/fault; work.mkdir()
            text = run([healthy/'simv','-no_save','+fault='+fault],fault,work)
            require(f'PHYSICAL_CUT_REJECT fault={fault} target_cycle=17 acknowledged_edges=0' in text and
                    'PHYSICAL_CUT_PASS' not in text, 'fault not rejected '+fault)
            summary['negative_tests'].append(fault)
        work = out/'corrupt'; work.mkdir()
        text = run([healthy/'simv','-no_save','+corrupt'],'corrupt',work,expected=1)
        require('PHYSICAL_CUT_DIVERGENCE target_cycle=17 reason=captured_ce[0]' in text and
                'PHYSICAL_CUT_PASS' not in text, 'semantic oracle failed to stop')
        summary['negative_tests'].append('captured_ce[0]')
        summary['inputs'] = native['inputs']
        summary['sources'] = native['sources']
        summary['native_receipt'] = str(args.native/'summary.json')
        summary['artifacts'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                                if p.is_file() and p.suffix in ('.log','.vcd')}
    else:
        native = native_input()
        require(args.eda is not None and args.eda.resolve().is_relative_to(RUNS), 'EDA execution directory below runs required')
        eda = json.loads((args.eda/'summary.json').read_text())
        require(eda['status'] == 'pass' and eda['backend'] == 'eda' and
                eda['inputs'] == native['inputs'] and eda['sources'] == native['sources'], 'EDA/native mismatch')
        require(eda['cuts'] == [0,17,128,256] and eda['functional_cycles'] == 320 and
                eda['stalls'] == 64 and eda['negative_tests'] == ['missing','ce','cycle','captured_ce[0]'],
                'incomplete component execution')
        for name, value in eda['artifacts'].items():
            require(value == sha(args.eda/name), 'changed EDA artifact '+name)
        require('PHYSICAL_CUT_PASS' in (args.eda/'healthy.log').read_text(), 'missing native runtime pass')
        require(len(list(args.eda.rglob('*.vcd'))) == 5, 'missing full debug waves')
        summary.update(matching_inputs=len(native['inputs']), matching_sources=len(SOURCES),
                       native_receipt=str(args.native/'summary.json'), eda_receipt=str(args.eda/'summary.json'),
                       checks=eda['checks'])
    require(all(sha(ROOT/n) == summary.get('sources', {n:sha(ROOT/n) for n in SOURCES})[n] for n in SOURCES), 'source changed during execution')
    summary['completed_utc'] = datetime.now(timezone.utc).isoformat()
    summary['commands'] = commands
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
