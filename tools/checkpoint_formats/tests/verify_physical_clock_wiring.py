"""Native localhost synthesis and EDA VCS of compiler-generated clock wiring.

This checks generated wiring, not a complete Rocket capture or image build.
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

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.audit_physical_clock_wiring import audit
from tools.checkpoint_formats.tests.audit_physical_clock_dependencies import audit as audit_dependencies

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
SOURCES = ('sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalClockCut.sv',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutWiring.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutPlan.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutDependencies.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/PhysicalClockCutDependenciesSpec.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/PhysicalClockCutPlanSpec.scala',
           'tools/checkpoint_formats/tests/audit_physical_clock_plan.py',
           'tools/checkpoint_formats/tests/audit_physical_clock_wiring.py',
           'tools/checkpoint_formats/tests/audit_physical_clock_dependencies.py',
           'tools/checkpoint_formats/tests/physical_clock_wiring_tb.sv',
           'tools/checkpoint_formats/tests/verify_physical_clock_wiring.py',
           'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc')
FILES = ('reference.fir','manifest.json','physical-clock-plan.json', 'physical-clock-wiring.fir',
         'physical-clock-wiring.json','physical-clock-wiring.sv','physical-clock-wiring-emission.json',
         'physical-clock-dependencies.json')
FIXTURE = '''module PhysicalClockWiringFixture(
  input wire clock, reset, freeze_request,
  output wire [7:0] a,b,
  output wire [63:0] count,
  output wire [1:0] ce,captured_ce,
  output wire clock_mask,stopped,read_enable,failed,
  output wire [63:0] cut_cycle,
  output wire [2:0] error
);
  PhysicalPlanTop network(.clock(clock),.reset(reset),.a(a),.b(b),.count(count),
    .checkpoint_physical_mask(clock_mask),.checkpoint_physical_logical_ce(ce));
  CheckpointPhysicalClockCut #(.GATES(2),.OWNERS(1),.EXTERNAL_CLOCK_NETWORK(1)) cut(
    .clock(clock),.reset(reset),.freeze_request(freeze_request),.ce(ce),
    .target_cycle(count),.owner_present(1'b1),.root_clock(),.gate_clock(),
    .clock_mask(clock_mask),.stopped(stopped),.read_enable(read_enable),.failed(failed),
    .captured_ce(captured_ce),.cut_cycle(cut_cycle),.error(error));
endmodule
'''
TCL = '''read_verilog -sv sources/CheckpointPhysicalClockCut.sv generated/physical-clock-wiring.sv fixture.sv
synth_design -top PhysicalClockWiringFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 3} {error "expected one root and two original native gates: $gates"}
foreach gate $gates {
  if {[get_property CE_TYPE $gate] ne "SYNC"} {error "nondefault gate contract"}
}
foreach name {network/checkpoint_physical_root_gate network/left/gate network/right/gate} {
  if {[llength [get_cells $name]] != 1} {error "lost original gate hierarchy $name"}
}
set fall [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]
if {[llength $fall] != 1} {error "expected one common falling-edge mask register: $fall"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force physical-clock-wiring.dcp
puts "CLOCK_WIRING_SYNTH_PASS gates=3 falling_edge_registers=1"
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--mode', choices=('vivado','vcs','audit'), required=True)
    parser.add_argument('--generated', type=Path)
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
        row = dict(argv=[str(a) for a in argv],cwd=str(cwd),log=str(log))
        commands.append(row)
        with log.open('w') as stream:
            result = subprocess.run(row['argv'],cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        require(result.returncode == expected,'inspect underlying log '+str(log))
        return log.read_text()

    def check_generated(directory):
        audit_dependencies(directory/'reference.fir',directory/'manifest.json',directory/'physical-clock-plan.json',
            directory/'physical-clock-dependencies.json')
        return audit(directory/'reference.fir',directory/'manifest.json',directory/'physical-clock-plan.json',
            directory/'physical-clock-wiring.fir',directory/'physical-clock-wiring.json',
            directory/'physical-clock-wiring.sv',directory/'physical-clock-wiring-emission.json')

    def native_input():
        require(args.native and args.native.resolve().is_relative_to(RUNS),'native receipt below runs required')
        doc = json.loads((args.native/'summary.json').read_text())
        require(doc['status']=='pass' and doc['backend']=='f2' and doc['physical_fpga_capture'] is False,
                'invalid native wiring receipt')
        for name in SOURCES:
            require(doc['sources'][name] == sha(ROOT/name) == sha(args.native/'sources'/Path(name).name),'changed source '+name)
        for group in ('inputs','artifacts'):
            for name,value in doc[group].items():
                require(value==sha(args.native/name),'changed native evidence '+name)
        require((args.native/'fixture.sv').read_text()==FIXTURE,'changed generated/controller composition')
        require((args.native/'synth.tcl').read_text()==TCL,'changed synthesis contract')
        check_generated(args.native/'generated')
        return doc

    summary = dict(status='pass',backend='eda' if args.mode=='vcs' else 'f2',host=socket.gethostname(),
        observed_utc=datetime.now(timezone.utc).isoformat(),scope='compiler-generated physical clock wiring fixture only',
        physical_fpga_capture=False,full_rocket_image_build=False)
    if args.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),'native Vivado manager required')
        require(args.generated is not None,'generated fixture required')
        summary['structural_audit']=check_generated(args.generated)
        (out/'generated').mkdir(); (out/'sources').mkdir()
        for name in FILES:
            shutil.copyfile(args.generated/name,out/'generated'/name)
        for name in SOURCES:
            shutil.copyfile(ROOT/name,out/'sources'/Path(name).name)
        vendor=Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        summary['vendor_models']={}
        for name,path in [('BUFGCE.v',vendor/'unisims/BUFGCE.v'),('glbl.v',vendor/'glbl.v')]:
            shutil.copyfile(path,out/name)
            summary['vendor_models'][name]=dict(original_path=str(path),sha256=sha(path))
        (out/'fixture.sv').write_text(FIXTURE)
        (out/'synth.tcl').write_text(TCL)
        text=run(['vivado','-mode','batch','-source','synth.tcl','-log','vivado.log','-journal','vivado.jou'],'synth')
        require('CLOCK_WIRING_SYNTH_PASS gates=3 falling_edge_registers=1' in text and not re.search('ERROR:|CRITICAL WARNING:',text),'native gate synthesis failure')
        summary['sources']={n:sha(ROOT/n) for n in SOURCES}
        summary['inputs']={str(p.relative_to(out)):sha(p) for d in ('generated','sources') for p in (out/d).iterdir()}
        summary['inputs'].update({n:sha(out/n) for n in ('fixture.sv','synth.tcl','BUFGCE.v','glbl.v')})
        summary['artifacts']={n:sha(out/n) for n in ('physical-clock-wiring.dcp','utilization.rpt','timing.rpt','synth.log','vivado.log','commands.json')}
    elif args.mode=='vcs':
        require(os.environ.get('VCS_HOME')==toolchain.VCS_HOME and Path(toolchain.VCS).is_file(),'EDA VCS environment required')
        native=native_input()
        for name,value in native['inputs'].items():
            path=out/name; path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(args.native/name,path)
            require(sha(path)==value,'input copy mismatch')
        healthy=out/'healthy'; healthy.mkdir()
        run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
            '-top','physical_clock_wiring_tb','-top','glbl','-Mdir='+str(healthy/'csrc'),'-o',healthy/'simv',
            out/'BUFGCE.v',out/'glbl.v',out/'generated/physical-clock-wiring.sv',
            out/'sources/CheckpointPhysicalClockCut.sv',out/'fixture.sv',
            out/'sources/physical_clock_wiring_tb.sv',out/'sources/checkpoint_generated_network_exit.cc'],'compile',healthy)
        text=run([healthy/'simv','-no_save'],'healthy',healthy)
        match=re.search(r'CLOCK_WIRING_PASS checks=(\d+) cycles=320 cuts=4 stalls=64',text)
        require(match is not None,'incomplete generated-wiring execution')
        bad=out/'corrupt'; bad.mkdir()
        text=run([healthy/'simv','-no_save','+corrupt'],'corrupt',bad,expected=1)
        require('CLOCK_WIRING_DIVERGENCE cycle=17 signal=logical_ce[0] acknowledged_edges=0' in text,'incorrect divergence')
        summary.update(checks=int(match[1]),functional_cycles=320,cuts=[0,17,128,256],stalls=64,
            negative_tests=['logical_ce[0]'],native_receipt=str(args.native/'summary.json'),
            sources=native['sources'],inputs=native['inputs'])
        summary['artifacts']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.suffix in ('.log','.vcd')}
    else:
        native=native_input()
        require(args.eda and args.eda.resolve().is_relative_to(RUNS),'EDA receipt below runs required')
        eda=json.loads((args.eda/'summary.json').read_text())
        require(eda['status']=='pass' and eda['backend']=='eda' and eda['sources']==native['sources'] and
                eda['inputs']==native['inputs'] and eda['functional_cycles']==320 and eda['stalls']==64 and
                eda['cuts']==[0,17,128,256] and eda['negative_tests']==['logical_ce[0]'],'incomplete EDA execution')
        for name,value in eda['artifacts'].items():
            require(value==sha(args.eda/name),'changed EDA execution artifact '+name)
        require(len(list(args.eda.rglob('*.vcd')))==2,'missing debug waveforms')
        summary.update(checks=eda['checks'],matching_sources=len(SOURCES),matching_inputs=len(native['inputs']),
            native_receipt=str(args.native/'summary.json'),eda_receipt=str(args.eda/'summary.json'))
    summary['commands']=commands
    summary['completed_utc']=datetime.now(timezone.utc).isoformat()
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(out/'summary.json')


if __name__=='__main__':
    main()
