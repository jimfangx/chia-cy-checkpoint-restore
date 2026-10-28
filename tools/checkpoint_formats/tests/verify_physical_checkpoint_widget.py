"""Physical-cut FireSim Widget: localhost native synthesis and fresh EDA VCS.

The generated external clock network and exact Rocket CE endpoint are supporting
components. This does not admit a complete production Rocket checkpoint image.
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
from tools.checkpoint_formats.tests.audit_widget_shadow import audit as audit_shadow
from tools.checkpoint_formats.tests.verify_physical_state_router_transport import (
    audit_frames, check_network, audit_ce as check_ce, CE_FILES, NETWORK_FILES,
    SOURCES as ROUTER_SOURCES)

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
VERILOG = 'sims/firesim/sim/midas/src/main/verilog/'
WIDGET = 'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureWidget.scala'
TB = 'tools/checkpoint_formats/tests/physical_checkpoint_widget_tb.sv'
HEADER = 'tools/checkpoint_formats/tests/physical_state_router_fixture.svh'
EXIT = 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'
SOURCES = tuple(dict.fromkeys((WIDGET,
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointNastiState.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureNastiStateSpec.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointLiveWidgetSnapshot.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/CheckpointTransportControlState.scala',
    'tools/checkpoint_formats/tests/audit_widget_shadow.py',
    'tools/checkpoint_formats/tests/verify_transport_control_state.py',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureDescriptors.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureDescriptorsSpec.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureWidgetSpec.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/core/CheckpointCaptureTopSpec.scala', TB, HEADER, EXIT,
    VERILOG+'CheckpointPhysicalStateRouter.sv',
    *(VERILOG+n+'.sv' for n in ('CheckpointCaptureTransport', 'CheckpointCaptureCut',
                                'CheckpointPhysicalClockCut', 'CheckpointPhysicalCaptureTransport')),
    'tools/checkpoint_formats/tests/verify_physical_checkpoint_widget.py',
    'tools/checkpoint_formats/tests/verify_physical_state_router_transport.py', *ROUTER_SOURCES)))
WIDGET_FILES = ('CheckpointCaptureWidget.v','CheckpointCaptureTransport.sv','CheckpointCaptureCut.sv',
    'CheckpointPhysicalCaptureTransport.sv','CheckpointPhysicalClockCut.sv','physical_constants.h')
TCL = '''set_param general.maxThreads 4
read_verilog -sv widget/CheckpointCaptureWidget.v widget/CheckpointCaptureTransport.sv widget/CheckpointCaptureCut.sv widget/CheckpointPhysicalCaptureTransport.sv widget/CheckpointPhysicalClockCut.sv
synth_design -top CheckpointCaptureWidget -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name host_clock -period 7.142857 [get_ports clock]
if {[llength [get_cells -hier -filter {REF_NAME == BUFGCE}]] != 0} {error "physical widget must use the compiler external gate network"}
if {[llength [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]] != 1} {error "missing unique falling-edge mask"}
set shadow [get_cells -hier -filter {NAME =~ snapshot/* && REF_NAME =~ FD*}]
if {[llength $shadow] < 700} {error "missing immutable live-widget snapshot storage"}
set raw [get_nets -of_objects [get_ports clock]]
set sf [open shadow-registers.tsv w]
foreach cell $shadow {
  set pin [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
  if {[llength $pin] != 1 || [get_property IS_INVERTED $pin] != 0 ||
      [lsearch -exact [get_nets -segments -of_objects $pin] $raw] < 0} {error "snapshot lost ungated posedge $cell"}
  puts $sf "$cell\t[get_property REF_NAME $cell]"
}
close $sf
puts "LIVE_WIDGET_SNAPSHOT_SYNTH_PASS registers=[llength $shadow] ungated=1"
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force physical-widget.dcp
puts "PHYSICAL_WIDGET_SYNTH_PASS external_network=1 falling_edge_masks=1 duplicate_gates=0"
'''


SOURCES = (*SOURCES, 'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointWidgetEndpoint.scala')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado','vcs','audit'), required=True)
    for name in ('widget','network','ce-generated','native','eda','out'):
        parser.add_argument('--'+name, type=Path, required=name=='out')
    args = parser.parse_args()
    base = args.out.resolve()
    require(base.is_relative_to(RUNS), 'evidence below runs required')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=base))
    sources = {n:sha(ROOT/n) for n in SOURCES}
    commands=[]

    def run(argv, name, cwd=out, expected=0):
        row=dict(argv=[str(a) for a in argv],cwd=str(cwd),log=str(out/(name+'.log')))
        commands.append(row)
        with Path(row['log']).open('w') as stream:
            result=subprocess.run(row['argv'],cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        row['returncode']=result.returncode
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        require(result.returncode==expected,'inspect underlying log '+row['log'])
        return Path(row['log']).read_text()

    def validate(directory, backend):
        require(directory is not None and directory.resolve().is_relative_to(RUNS), 'receipt below runs required')
        doc=json.loads((directory/'summary.json').read_text())
        require(doc['status']=='pass' and doc['backend']==backend and doc['sources']==sources and
                doc['physical_fpga_capture'] is False and doc['production_rocket_integrated'] is False,
                'stale or wrong-scope receipt')
        for group in ('inputs','artifacts'):
            for name,digest in doc[group].items():
                require(sha(directory/name)==digest,'changed '+group+' '+name)
        for name,digest in sources.items():
            require(sha(directory/'sources'/Path(name).name)==digest,'changed source snapshot '+name)
        require((directory/'synth.tcl').read_text()==TCL,'changed native synthesis recipe')
        check_network(directory/'network'); check_ce(directory/'ce-generated')
        return doc

    summary=dict(status='pass',backend='eda' if args.mode=='vcs' else 'f2',
        observed_utc=datetime.now(timezone.utc).isoformat(),host=socket.gethostname(),original_root=str(ROOT),
        scope='physical FireSim Widget MMIO/stream with external generated clock network and exact Rocket CE endpoint',
        physical_fpga_capture=False,production_rocket_integrated=False,sources=sources)
    if args.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'localhost native Vivado required')
        for directory,group,names in ((args.widget,'widget',WIDGET_FILES),
                (args.network,'network',NETWORK_FILES),(args.ce_generated,'ce-generated',CE_FILES)):
            require(directory is not None and directory.resolve().is_relative_to(RUNS),'inputs below runs required')
            for name in names:
                target=out/group/name; target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(directory/name,target)
        check_network(out/'network'); ce=check_ce(out/'ce-generated')
        require(ce['physical_gates']==3,'three-gate verification scope required')
        layout=json.loads((out/'ce-generated/physical-clock-state-bank.json').read_text())
        summary['endpoint_module']=layout['endpoint_module']
        summary['original_inputs']={group:str(directory.resolve()) for group,directory in
            (('widget',args.widget),('network',args.network),('ce-generated',args.ce_generated))}
        for resource in WIDGET_FILES[1:5]:
            require(sha(out/'widget'/resource)==sha(ROOT/VERILOG/resource),'stale widget resource')
        text=(out/'widget/CheckpointCaptureWidget.v').read_text()
        require(text.count('CheckpointPhysicalCaptureTransport\n')==1 and
                '.EXTERNAL_CLOCK_NETWORK(1)' in text and '.GATES(3)' in text and '.OWNERS(2)' in text,
                'wrong generated physical Widget')
        header=(out/'widget/physical_constants.h').read_text()
        require('PHYSICAL_CLOCK_GATES 3U' in header and 'EXTERNAL_CLOCK_NETWORK 1U' in header,
                'missing physical ABI provenance')
        for resource in WIDGET_FILES[1:5]:
            require(resource+' SHA256: '+sha(ROOT/VERILOG/resource) in header,'wrong resource header hash')
        vendor=Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        for name,path in (('BUFGCE.v',vendor/'unisims/BUFGCE.v'),('glbl.v',vendor/'glbl.v')):
            shutil.copyfile(path,out/name)
        (out/'sources').mkdir()
        for name in SOURCES: shutil.copyfile(ROOT/name,out/'sources'/Path(name).name)
        (out/'synth.tcl').write_text(TCL)
        summary['inputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'synth')
        require('PHYSICAL_WIDGET_SYNTH_PASS external_network=1 falling_edge_masks=1 duplicate_gates=0' in text and
                not re.search(r'ERROR:|CRITICAL WARNING:',text),'physical Widget native synthesis failed')
        summary['artifacts']={n:sha(out/n) for n in ('physical-widget.dcp','utilization.rpt','timing.rpt','synth.log','commands.json','shadow-registers.tsv')}
    elif args.mode=='vcs':
        require(os.environ.get('VCS_HOME')==toolchain.VCS_HOME and Path(toolchain.VCS).is_file(), 'EDA native VCS SP2 required')
        native=validate(args.native,'f2'); summary['endpoint_module']=native['endpoint_module']
        for name,digest in native['inputs'].items():
            p=out/name; p.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(args.native/name,p)
            require(sha(p)==digest,'copy mismatch')
        def compile_widget(work, widget, name):
            run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
                '+incdir+'+str(out/'sources'),'+define+CE_BANK_MODULE='+native['endpoint_module'],
                '-top','physical_checkpoint_widget_tb','-top','glbl','-Mdir='+str(work/'csrc'),'-o',work/'simv',
                widget,*(out/'widget'/n for n in WIDGET_FILES[1:5]),out/'sources/CheckpointPhysicalStateRouter.sv',
                out/'ce-generated/physical-clock-state-bank.sv',out/'network/physical-clock-wiring.sv',
                out/'BUFGCE.v',out/'glbl.v',out/'sources/physical_checkpoint_widget_tb.sv',
                out/'sources/checkpoint_widget_exit.cc'],name,work)
        healthy=out/'healthy'; healthy.mkdir()
        compile_widget(healthy,out/'widget/CheckpointCaptureWidget.v','compile')
        text=run([healthy/'simv','-no_save','+frames='+str(healthy/'frames.hex')],'healthy',healthy)
        match=re.search(r'PHYSICAL_WIDGET_PASS checks=(\d+) cuts=6 stalls=(\d+) recovered_cycles=96',text)
        require(match is not None,'incomplete physical Widget execution')
        require('PHYSICAL_WIDGET_SHADOW_PASS captures=6 words=240' in text,
                'missing complete physical transport/local shadow readback')
        summary['shadow_wave_audit'] = audit_shadow(healthy/'physical-widget.vcd', physical=True)
        summary.update(checks=int(match[1]),cuts=6,dma_stalls=int(match[2]),recovered_cycles=96)
        captures=re.findall(r'PHYSICAL_WIDGET_CAPTURE requested=(\d+) accepted=(\d+) cut=(\d+) words=7',text)
        require(len(captures)==6 and all(int(c)==int(a) for _,a,c in captures),'bad actual adapter edge cut labels')
        summary['target_cuts']=[int(c) for _,_,c in captures]
        raw=[int(line,16).to_bytes(64,'little') for line in (healthy/'frames.hex').read_text().splitlines()]
        require(len(raw)==54,'incomplete six snapshot streams')
        summary['frame_audits']=[audit_frames(b''.join(raw[i:i+9])) for i in range(0,54,9)]
        for fault in ('missing','ce','cycle'):
            work=out/fault; work.mkdir()
            text=run([healthy/'simv','-no_save','+fault='+fault],fault,work)
            require('PHYSICAL_WIDGET_REJECT fault='+fault in text and 'acknowledged_edges=0' in text,
                    'missing physical fault rejection')
        corrupt=out/'corrupt'; corrupt.mkdir()
        text=run([healthy/'simv','-no_save','+corrupt'],'corrupt',corrupt,expected=1)
        require('reason=banked CE state' in text and 'PHYSICAL_WIDGET_PASS' not in text,'corrupt oracle did not stop')
        mutant=out/'mutated-widget'; mutant.mkdir()
        source=(out/'widget/CheckpointCaptureWidget.v').read_text()
        site='assign transport_physicalTransport_ce = capture_physical_logicalCE;'
        require(source.count(site)==1,'ambiguous emitted physical binding mutation')
        changed=mutant/'widget.v'; changed.write_text(source.replace(site,site[:-1]+" ^ 3'd1;"))
        compile_widget(mutant,changed,'mutated-compile')
        text=run([mutant/'simv','-no_save'],'mutated-widget',mutant,expected=1)
        require('reason=unmasked CE identity' in text and 'PHYSICAL_WIDGET_PASS' not in text,
                'wrong compiled widget CE connection escaped independent oracle')
        summary['negative_tests']=['missing','ce','cycle','corrupt','mutated-widget']
        summary['inputs']=native['inputs']; summary['native_receipt']=str(args.native/'summary.json')
        summary['artifacts']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.suffix in ('.log','.vcd','.hex')}
    else:
        native,eda=validate(args.native,'f2'),validate(args.eda,'eda')
        require(native['inputs']==eda['inputs'] and eda['cuts']==6 and eda['recovered_cycles']==96 and
                eda['negative_tests']==['missing','ce','cycle','corrupt','mutated-widget'], 'incomplete matching execution scope')
        require(len(list(args.eda.rglob('*.vcd')))==6,'missing full debug waveforms')
        summary.update(matched_inputs=len(native['inputs']),matched_sources=len(sources),
            native_receipt=str(args.native/'summary.json'),eda_receipt=str(args.eda/'summary.json'),inputs={},artifacts={})
    require(sources=={n:sha(ROOT/n) for n in SOURCES},'source changed during verification')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(out/'summary.json')


if __name__=='__main__':
    main()
