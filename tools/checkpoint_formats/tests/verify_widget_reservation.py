"""Audit/synthesize a deliberately UNBOUND registered widget; VCS only on EDA.

This diagnostic cannot establish FPGA capture, complete state or image admission.
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
from tools.checkpoint_formats.codec import require, FormatError
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.verify_native_checkpoint_top import STUB

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
SOURCES = [
    'sims/firesim/sim/midas/src/main/scala/midas/core/FPGATop.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/core/NativeCheckpointWidgetReservationBinding.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointWidgetReservation.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureWidget.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/stage/GoldenGateCompilerPhase.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/core/NativeCheckpointWidgetReservationSpec.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/stage/GoldenGateHostPipelineSpec.scala',
    'tools/checkpoint_formats/tests/verify_widget_reservation.py',
    'tools/checkpoint_formats/tests/widget_reservation_tb.sv',
    'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc']
RTL = ['CheckpointPhysicalCaptureTransport.sv','CheckpointPhysicalClockCut.sv',
       'CheckpointCaptureTransport.sv','CheckpointCaptureCut.sv']
SOURCES += ['sims/firesim/sim/midas/src/main/verilog/'+n for n in RTL]
PINS = {
    'reset':('controllerReset',1,True),'clock_mask':('physical_clockMask',1,True),
    'read_enable':('physical_readEnable',1,True),'captured_ce':('physical_capturedCE',2,True),
    'logical_ce':('physical_logicalCE',2,False),'descriptor_entry':('descriptorEntry',32,True),
    'descriptor_valid':('descriptorValid',1,False),'descriptor_bank':('descriptorBank',8,False),
    'descriptor_slot':('descriptorSlot',16,False),'descriptor_width':('descriptorWidth',16,False),
    'descriptor_depth':('descriptorDepth',32,False),'request_valid':('bankRequestValid',1,True),
    'request_ready':('bankRequestReady',1,False),'bank':('bank',8,True),'slot':('slot',16,True),
    'address':('address',32,True),'response_valid':('bankResponseValid',1,False),
    'response_ready':('bankResponseReady',1,True),'response_data':('bankResponseData',64,False),
    'response_error':('bankResponseError',1,False)}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit(g):
    receipt=json.loads((g/'reservation.json').read_text())
    ann=json.loads((g/'reserved-annotations.json').read_text())
    modules=parse_modules((g/'reserved.fir').read_text())
    require(receipt['source_sha256']==sha(g/'reserved.fir') and
            receipt['annotations_sha256']==sha(g/'reserved-annotations.json'), 'unbound reservation source')
    require(receipt['scope']=='registered_widget_resources_and_unbound_lowered_readout_pins_only' and
            receipt['external_transport_state_owner']=='unsupported_no_state_adapter' and
            all(receipt[k] is False for k in ('complete_fpga_capture','deployable_capture_image',
                'production_freeze_owners_bound','metasim_restore_supported','in_place_checkpoint_widget_connected')),
            'reservation falsely admits capture')
    require(receipt['host']=='FPGATop' and receipt['target']=='~FPGATop|FPGATop/sim:SimWrapper' and
            receipt['entries']==7 and receipt['gates']==2 and receipt['owners']==['fixture.functional','fixture.host'],
            'changed bounded reservation contract')
    executions=[a for a in ann if a['class']=='midas.checkpoint.NativeCheckpointWidgetExecutionAnnotation']
    require(len(executions)==1 and executions[0]['target']==receipt['target'] and
            all(executions[0][k]==receipt[k2] for k,k2 in [('entries','entries'),('gates','gates'),('owners','owners'),('queueDepth','queue_depth')]),
            'changed execution reservation annotation')
    host=modules['FPGATop'];widget=receipt['widget'].split('.')[1]
    require(host['instances'][widget]=='CheckpointCaptureWidget' and host['drivers'][widget+'.clock']=='clock',
            'widget registration/raw clock changed')
    pins=[a for a in ann if a['class']=='midas.checkpoint.NativeCheckpointWidgetPinAnnotation']
    require(len(pins)==20 and {a['role'] for a in pins}==set(PINS) and len({a['target'] for a in pins})==20,
            'missing/aliased reservation pins')
    rows=[]
    for pin in sorted(pins,key=lambda p:p['role']):
        role=pin['role'];port,width,source=PINS[role]
        match=re.fullmatch(r'~FPGATop\|FPGATop>(\w+)',pin['target'])
        require(match is not None,'foreign reservation target')
        name=match[1];wp=widget+'.capture_'+port;value=host['drivers'][name]
        if source: require(value==wp,'changed widget reservation source')
        else:
            seen={name}
            while value in host['drivers']:
                require(value not in seen,'reservation alias cycle');seen.add(value);value=host['drivers'][value]
            require(value==f'UInt<{width}>("h0")' and host['drivers'][wp]==name,'changed zero placeholder/widget sink')
        rows.append(dict(role=role,target=pin['target'],type=f'UInt<{width}>',widget_pin=wp,
                         source='widget' if source else 'unbound_zero_placeholder'))
    require(rows==receipt['pins'],'changed lowered endpoint receipt')
    transport=modules['CheckpointPhysicalCaptureTransport']
    require(hashlib.sha256(transport['body'].encode()).hexdigest()==receipt['transport_definition_sha256'],
            'changed reserved transport definition')
    params=dict(re.findall(r'^  parameter (\w+) = (\d+)$',transport['body'],re.M))
    require(params==dict(GATES='2',OWNERS='2',ENTRIES='7',EXTERNAL_CLOCK_NETWORK='1',RESTORE_ENABLE='0',MANIFEST_SHA256=str(2**256-1)),
            'changed reservation transport parameters')
    for n in RTL:
        actual=[a for a in ann if a['class']=='firrtl.transforms.BlackBoxInlineAnno' and a['name']==n]
        require(len(actual)==1 and actual[0]['text']==(g/n).read_text() and
                sha(g/n)==receipt['transport_sources'][n]==sha(ROOT/'sims/firesim/sim/midas/src/main/verilog'/n),'changed actual transport source '+n)
    header=(g/'reserved.h').read_text()
    headers=[a for a in ann if a['class']=='midas.stage.GoldenGateOutputFileAnnotation' and a['fileSuffix']=='.const.h']
    require(len(headers)==1 and headers[0]['body']==header,'changed reserved driver/header context')
    h=re.search(r'// CHECKPOINT_WIDGET_RESERVATION_BEGIN base=(\d+) stream=(\d+)\n#error Unbound_checkpoint_widget_reservation\n// CHECKPOINT_WIDGET_RESERVATION_END\n',header)
    require(h and h[2]=='1' and 'registry.add_widget(new checkpoint_capture_t' not in header,'unbound driver escaped')
    streams=re.findall(r'CPUManagedStreams::StreamParameters\(\s*std::string\(R"ESC\((.*?)\)ESC"\),\s*(\d+)ULL,\s*(\d+)ULL,\s*(\d+),\s*(\d+)',header)
    require(len(streams)==2 and 'CHECKPOINTCAPTUREWIDGET_' in streams[1][0] and streams[1][3:]==('2','64'),
            'real stream resource allocation changed')
    return dict(pins=20,capture_base=int(h[1]),stream_count=int(streams[1][2]),
                baseline_dma=int(streams[0][1]),baseline_count=int(streams[0][2]))

def corruptions(g, out):
    rejected=[]
    names=['scope','pin_alias','widget_source','zero_placeholder','digest','header','transport_source','raw_clock']
    for name in names:
        d=out/name;d.mkdir(parents=True)
        for n in ['reserved.sv','reserved.fir','reserved-annotations.json','reservation.json','reserved.h',*RTL]: shutil.copyfile(g/n,d/n)
        doc=json.loads((d/'reservation.json').read_text());ann=json.loads((d/'reserved-annotations.json').read_text())
        text=(d/'reserved.fir').read_text()
        if name=='scope': doc['complete_fpga_capture']=True
        elif name=='pin_alias':
            pins=[a for a in ann if a['class']=='midas.checkpoint.NativeCheckpointWidgetPinAnnotation']
            pins[0]['target']=pins[1]['target']
        elif name=='widget_source':
            site='node checkpoint_widget_reset = '+doc['widget'].split('.')[1]+'.capture_controllerReset'
            require(text.count(site)==1,'ambiguous reset mutation');text=text.replace(site,'node checkpoint_widget_reset = reset')
        elif name=='zero_placeholder':
            site='node _checkpoint_widget_response_data_WIRE = UInt<64>("h0")'
            require(text.count(site)==1,'ambiguous zero mutation');text=text.replace(site,site.replace('h0','h1'))
        elif name=='digest':
            site='parameter MANIFEST_SHA256 = '+str(2**256-1)
            require(text.count(site)==1,'ambiguous digest mutation');text=text.replace(site,'parameter MANIFEST_SHA256 = 1')
            body=parse_modules(text)['CheckpointPhysicalCaptureTransport']['body']
            doc['transport_definition_sha256']=hashlib.sha256(body.encode()).hexdigest()
        elif name=='header':
            h=(d/'reserved.h').read_text().replace('#error Unbound_checkpoint_widget_reservation','#define FALSE_IMAGE_ID 1')
            (d/'reserved.h').write_text(h)
            for a in ann:
                if a['class']=='midas.stage.GoldenGateOutputFileAnnotation' and a['fileSuffix']=='.const.h': a['body']=h
        elif name=='transport_source':
            n='CheckpointCaptureCut.sv';(d/n).write_text((d/n).read_text()+'\n')
            for a in ann:
                if a['class']=='firrtl.transforms.BlackBoxInlineAnno' and a['name']==n:a['text']=(d/n).read_text()
            doc['transport_sources'][n]=sha(d/n)
        elif name=='raw_clock':
            site=doc['widget'].split('.')[1]+'.clock <= clock'
            require(text.count(site)==1,'ambiguous clock mutation');text=text.replace(site,site.replace('<= clock','<= asClock(reset)'))
        (d/'reserved.fir').write_text(text);(d/'reserved-annotations.json').write_text(json.dumps(ann,indent=2))
        doc['source_sha256']=sha(d/'reserved.fir');doc['annotations_sha256']=sha(d/'reserved-annotations.json')
        (d/'reservation.json').write_text(json.dumps(doc,indent=2))
        try:audit(d)
        except FormatError as error:rejected.append(dict(case=name,error=str(error)))
        else:raise AssertionError('accepted rehashed reservation corruption '+name)
    return rejected

TCL='''set_param general.maxThreads 4
read_verilog -sv reserved.sv target-clock-sink.sv '''+' '.join(RTL)+'''
synth_design -top FPGATop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set raw [get_nets -of_objects [get_ports clock]]
set count 0
foreach pattern {CheckpointCaptureWidget_*/* CPUManagedStreamEngine_*/* ctrlInterconnect/*} {
  set cells [get_cells -hier -filter "NAME =~ $pattern && REF_NAME =~ FD*"]
  if {[llength $cells] == 0} {error "missing registered control/stream state $pattern"}
  foreach cell $cells {
    if {[lsearch -exact [get_nets -segments -of_objects [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]] $raw] < 0} {error "masked control/stream state $cell"}
    incr count
  }
}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force reservation.dcp
puts "RESERVATION_SYNTH_PASS raw_registers=$count UNBOUND=1"
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['vivado','vcs','audit'],required=True)
    for n in ['generated','native','eda','out']: p.add_argument('--'+n,type=Path,required=n=='out')
    a=p.parse_args();require(a.out.resolve().is_relative_to(RUNS),'evidence below runs required')
    a.out.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=a.mode+'-',dir=a.out.resolve()))
    sources={n:sha(ROOT/n) for n in SOURCES};commands=[]
    def run(argv,name,expected=0):
        row=dict(argv=list(map(str,argv)),cwd=str(out),log=str(out/(name+'.log')));commands.append(row)
        with Path(row['log']).open('w') as f: result=subprocess.run(row['argv'],cwd=out,stdout=f,stderr=subprocess.STDOUT)
        row['returncode']=result.returncode;(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        require(result.returncode==expected,'inspect compiler/runtime log '+row['log'])
        return Path(row['log']).read_text()
    def validate(path,backend):
        d=json.loads((path/'summary.json').read_text())
        require(d['status']=='pass' and d['backend']==backend and d['sources']==sources and
                d['physical_fpga_capture'] is False,'stale/wrong backend reservation evidence')
        for group in ['inputs','artifacts']:
            for n,v in d[group].items(): require((path/n).stat().st_size>0 and sha(path/n)==v,'changed evidence '+n)
        require(audit(path)==d['audit'],'changed reservation structure')
        if backend=='f2': require(len(d['rejected_corruptions'])==8,'incomplete reservation corruptions')
        return d
    summary=dict(status='pass',backend='eda' if a.mode=='vcs' else 'f2',sources=sources,
        observed_utc=datetime.now(timezone.utc).isoformat(),host=socket.gethostname(),source_root=str(ROOT),
        physical_fpga_capture=False,scope='unbound widget reservation diagnostics only')
    if a.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),'localhost native Vivado required')
        require(a.generated.resolve().is_relative_to(RUNS),'generated evidence below runs required')
        for n in ['reserved.sv','reserved.fir','reserved-annotations.json','reservation.json','reserved.h',*RTL]: shutil.copyfile(a.generated/n,out/n)
        for n in SOURCES:
            dst=out/'sources'/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dst)
        summary['audit']=audit(out)
        summary['rejected_corruptions']=corruptions(out,out/'corruptions')
        (out/'target-clock-sink.sv').write_text(STUB);(out/'synth.tcl').write_text(TCL)
        summary['inputs']={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and 'corruptions' not in f.relative_to(out).parts}
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'synth')
        require('RESERVATION_SYNTH_PASS' in text and not re.search(r'ERROR:|CRITICAL WARNING:',text),'native reservation synthesis failed')
        summary['artifacts']={n:sha(out/n) for n in ['synth.log','utilization.rpt','timing.rpt','reservation.dcp','commands.json']}
    elif a.mode=='vcs':
        require(shutil.which('vcs')==toolchain.VCS and toolchain.VCS=='/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs','EDA SP2 required')
        native=validate(a.native,'f2')
        for n in native['inputs']:
            dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.native/n,dst)
        summary.update(inputs=native['inputs'],audit=audit(out))
        top=re.search(r'module FPGATop\((.*?)\);',(out/'reserved.sv').read_text(),re.S)[1]
        ports=re.findall(r'(input|output)\s*(\[\d+:\d+\])?\s*(\w+)',re.sub(r'//[^\n]*','',top))
        (out/'top_ports.svh').write_text('\n'.join(f'{"reg" if d=="input" else "wire"} {w} {n}{"=0" if d=="input" else ""};' for d,w,n in ports)+'\nFPGATop dut('+','.join(f'.{n}({n})' for _,_,n in ports)+');\n')
        bindings=[f'localparam [63:0] {k.upper()}={v};' for k,v in summary['audit'].items()]
        for suffix,macro,width in [('reservedCycle','RESERVED_CYCLE','[63:0]'),('reservedPresent','RESERVED_PRESENT','[1:0]'),
                                   ('reservedFrozen','RESERVED_FROZEN','[1:0]'),('reservedError','RESERVED_ERROR','[1:0]')]:
            actual=[n for direction,w,n in ports if direction=='input' and w==width and (n==suffix or n.endswith('_'+suffix))]
            require(len(actual)==1,'ambiguous/missing generated owner/cycle input '+suffix)
            bindings.append(f'`define {macro} {actual[0]}')
        (out/'top_bindings.svh').write_text('\n'.join(bindings)+'\n')
        files=[out/n for n in ['reserved.sv','target-clock-sink.sv',*RTL]]+[out/'sources/tools/checkpoint_formats/tests'/n for n in ['widget_reservation_tb.sv','checkpoint_generated_network_exit.cc']]
        run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all','+incdir+'+str(out),'-top','widget_reservation_tb','-Mdir=csrc','-o','simv',*files],'compile')
        text=run([out/'simv','-no_save'],'runtime')
        m=re.search(r'RESERVATION_VCS_PASS checks=(\d+) missing_owner_rejected=1 reset_recovered=1 baseline_stream=1',text)
        require(m and int(m[1])>30 and (out/'reservation.vcd').stat().st_size>2000,'incomplete reservation execution')
        summary['checks']=int(m[1]);summary['artifacts']={n:sha(out/n) for n in ['runtime.log','compile.log','reservation.vcd','commands.json']}
    else:
        native=validate(a.native,'f2');eda=validate(a.eda,'eda')
        require(native['inputs']==eda['inputs'] and eda['checks']>30,'incomplete reservation matching')
        summary.update(audit=native['audit'],inputs={},artifacts={},checks=eda['checks'],matched_inputs=len(native['inputs']))
    require(sources=={n:sha(ROOT/n) for n in SOURCES},'source changed during verification')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(out/'summary.json')

if __name__=='__main__': main()
