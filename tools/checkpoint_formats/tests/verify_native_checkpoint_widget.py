"""Native bank/CE/router readout through the real FireSim Widget. No FPGA acceptance."""
import argparse
from datetime import datetime, timezone
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
from tools.checkpoint_formats.fpga_transport import crc32c, field
from tools.checkpoint_formats.tests.verify_native_clock_cut_bank import audit as audit_network, SOURCES as NETWORK_SOURCES
from tools.checkpoint_formats.tests.verify_native_descriptors import audit as audit_descriptors
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha, selectors, FLAGS
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.audit_native_constraints import audit as audit_constraints

ROOT=Path(__file__).resolve().parents[3]
RUNS=ROOT/'automations/checkpoint_loop/runs'
BASE='tools/checkpoint_formats/tests/'
SCALA='sims/firesim/sim/midas/src/'
SOURCES=tuple(sorted(set(NETWORK_SOURCES+(
    SCALA+'main/scala/midas/checkpoint/NativeCheckpointStateAccess.scala',
    SCALA+'main/scala/midas/checkpoint/NativeCheckpointConstraints.scala',
    SCALA+'main/scala/midas/widgets/CheckpointCaptureWidget.scala',
    SCALA+'main/scala/midas/widgets/CheckpointLiveWidgetSnapshot.scala',
    SCALA+'main/scala/midas/widgets/CheckpointNastiState.scala',
    SCALA+'main/scala/midas/checkpoint/CheckpointTransportControlState.scala',
    SCALA+'test/scala/midas/widgets/CheckpointNativeDescriptorsSpec.scala',
    BASE+'native_checkpoint_widget_fixture.sv',BASE+'native_checkpoint_widget_tb.sv',
    BASE+'verify_native_checkpoint_widget.py',
    BASE+'audit_native_constraints.py',
    *('sims/firesim/sim/midas/src/main/verilog/'+n+'.sv' for n in
      ('CheckpointPhysicalStateRouter','CheckpointCaptureTransport','CheckpointCaptureCut','CheckpointPhysicalCaptureTransport'))))))
PREFIX='FireSim-generated'
FILES=['generated/'+PREFIX+s for s in ('.native-clock-cut.sv','.native-state-access.sv',
    '.native-state-access-router.sv','.native-descriptors-physical-bank.sv')]+[
    'generated/widget/'+n for n in ('CheckpointCaptureWidget.v','CheckpointCaptureTransport.sv',
    'CheckpointCaptureCut.sv','CheckpointPhysicalCaptureTransport.sv','CheckpointPhysicalClockCut.sv')]+[
    'sources/native_checkpoint_widget_fixture.sv']
TCL='''set_param general.maxThreads 4
read_verilog -sv '''+' '.join(FILES)+'''
synth_design -top NativeCheckpointWidgetFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
# Apply the generated wrapper constraints in the concrete access instance.
# During application every cell/pin query must resolve; Vivado warnings alone
# are insufficient because an empty query can silently omit a constraint.
current_instance access
set native_constraint_queries 0
foreach kind {get_cells get_pins} {
  rename $kind native_original_$kind
  proc $kind {args} {
    set kind [lindex [info level 0] 0]
    set found [uplevel 1 [linsert $args 0 native_original_$kind]]
    if {[llength $found] != 1} {error "native constraint query must resolve once: $kind $args -> $found"}
    incr ::native_constraint_queries
    return $found
  }
}
source generated/FireSim-generated.native-state-access.synthesis.xdc
source generated/FireSim-generated.native-state-access.implementation.xdc
foreach kind {get_cells get_pins} {
  if {![catch {$kind -quiet network/missing_gate} reason] || ![string match {native constraint query must resolve once:*} $reason]} {
    error "empty native constraint query did not fail: $kind"
  }
  puts "NATIVE_CONSTRAINT_QUERY_REJECTED kind=$kind"
}
foreach kind {get_cells get_pins} {rename $kind {}; rename native_original_$kind $kind}
if {$native_constraint_queries != 6} {error "missing native cell/pin constraints"}
foreach leaf {left_ right_} {
  if {![get_property DONT_TOUCH [get_cells network/$leaf/gate]]} {error "native gate constraint was not applied"}
  set clocks [get_clocks -of_objects [get_pins network/$leaf/gate/O]]
  if {[llength $clocks] != 1 || [get_property NAME $clocks] ne "network/$leaf/gate/O"} {
    error "native output generated clock constraint was not applied"
  }
}
current_instance
puts "NATIVE_CONSTRAINTS_PASS queries=$native_constraint_queries scope=access/network"
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 3} {error "expected original native gates and single root mask"}
foreach name {access/network/checkpoint_physical_root_gate access/network/left_/gate access/network/right_/gate} {
  if {[llength [get_cells $name]] != 1} {error "lost native gate $name"}
}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "changed native CE semantics"}}
if {[llength [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]] != 1} {error "expected unique falling-edge mask"}
set raw [get_nets -of_objects [get_ports clock]]
foreach pattern {*ckpt_pending_reg *ckpt_saved_data_reg* *ckpt_saved_error_reg *router/pending_reg *ce_endpoint/response_valid_reg} {
  set cells [get_cells -hier -filter "NAME =~ $pattern && REF_NAME =~ FD*"]
  if {[llength $cells] == 0} {error "missing endpoint/router $pattern"}
  foreach cell $cells {
    set pins [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
    if {[lsearch -exact [get_nets -segments -of_objects $pins] $raw] < 0} {error "masked capture endpoint $cell"}
  }
}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force native-widget.dcp
puts "NATIVE_WIDGET_SYNTH_PASS gates=3 falling_edge_masks=1 raw_clock_endpoints=3"
'''


SOURCES = tuple(dict.fromkeys((*SOURCES, 'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointWidgetEndpoint.scala')))

def audit(generated):
    generated=Path(generated)
    path=lambda s:generated/(PREFIX+s)
    network=audit_network(generated)
    constraints=audit_constraints(generated)
    descriptors=audit_descriptors(generated,widget=(generated/'widget').exists())
    load=lambda s:json.loads(path(s).read_text())
    bank=load('.native-functional-binding.json');deps=load('.native-functional-dependencies.json')
    root=load('.native-functional-inventory.json')['root_module']
    clock=load('.native-functional-plan.json')['common_source_clock']
    binding=load('.native-state-access.json')
    require(binding==dict(binding_version=1,scope='same_reference_native_state_router_companion_only',
        module=root+'CheckpointStateAccess',common_source_clock=clock,functional_entries=len(bank['state']),
        physical_clock_gates=descriptors['physical_clock_gates'],
        same_reference_sha256=sha(path('.native-functional-reference.fir')),
        wired_binding_sha256=sha(path('.native-clock-cut.json')),
        descriptor_binding_sha256=sha(path('.native-descriptors-binding.json')),
        descriptor_manifest_sha256=sha(path('.native-descriptors.json')),
        endpoint_sha256=sha(path('.native-state-access.sv')),router_sha256=sha(path('.native-state-access-router.sv')),
        physical_bank_sha256=sha(path('.native-descriptors-physical-bank.sv')),
        reset_contract='widget_controller_reset_shared_by_native_endpoint_router_and_ce_bank',
        external_inputs_require_freeze=deps['external_inputs_require_freeze'],**FLAGS),'changed native state routing binding')
    require(sha(path('.native-state-access-router.sv'))==sha(ROOT/'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalStateRouter.sv'),
        'changed router resource')
    rtl=path('.native-state-access.sv').read_text()
    def instance(name,module,expected,wildcard=False):
        matches=re.findall(r'\b'+re.escape(module)+r'(?:\s*#\(([^;]+?)\))?\s+'+name+r'\s*\((.*?)\);',rtl,re.S)
        require(len(matches)==1,'missing/duplicate instance '+name)
        params,body=matches[0]
        pins=re.findall(r'\.([A-Za-z_][A-Za-z0-9_$]*)\(([^()]*)\)',body)
        require(len(pins)==len(dict(pins)) and dict(pins)==expected,'changed native connection '+name)
        residue=re.sub(r'\.[A-Za-z_][A-Za-z0-9_$]*\([^()]*\)','',body).replace(',','').strip()
        require(residue==('.*' if wildcard else ''),'unexpected native connection '+name)
        return params
    ports=parse_modules(path('.native-functional-reference.fir').read_text())[root]['ports']
    declarations=[]
    for name,(direction,kind) in ports.items():
        if kind in ('Clock','Reset','AsyncReset'):signed,width='',1
        else:
            shape=re.fullmatch(r'(UInt|SInt)<(\d+)>',kind);require(shape,'unsupported original native port')
            signed,width=('signed ' if shape[1]=='SInt' else ''),int(shape[2])
        declarations.append(f"  {direction} wire {signed}"+(f"[{width-1}:0] " if width>1 else '')+name)
    gates=descriptors['physical_clock_gates']
    capture=f"""  input wire capture_reset, capture_clock_mask, capture_read_enable,
  input wire [{gates-1}:0] capture_captured_ce,
  output wire [{gates-1}:0] capture_logical_ce,
  input wire [31:0] capture_descriptor_entry,
  output wire capture_descriptor_valid,
  output wire [7:0] capture_descriptor_bank,
  output wire [15:0] capture_descriptor_slot, capture_descriptor_width,
  output wire [31:0] capture_descriptor_depth,
  input wire capture_request_valid,
  output wire capture_request_ready,
  input wire [7:0] capture_bank,
  input wire [15:0] capture_slot,
  input wire [31:0] capture_address,
  output wire capture_response_valid,
  input wire capture_response_ready,
  output wire [63:0] capture_response_data,
  output wire capture_response_error"""
    header=re.search(r'module '+re.escape(root)+r'CheckpointStateAccess \(\n(.*?)\n\);',rtl,re.S)
    require(header and header[1]==',\n'.join(declarations)+',\n'+capture,'changed native public port direction/shape')
    native={p:p for p in ports}
    native.update(checkpoint_physical_mask='capture_clock_mask',checkpoint_physical_logical_ce='capture_logical_ce',
        ckpt_clock=clock,ckpt_reset='capture_reset',ckpt_freeze='capture_clock_mask',
        ckpt_bank='endpoint_bank',ckpt_slot='endpoint_slot',ckpt_address='endpoint_address',ckpt_match='',ckpt_data='',
        ckpt_req_valid='functional_request_valid',ckpt_req_ready='functional_request_ready',
        ckpt_resp_valid='functional_response_valid',ckpt_resp_ready='functional_response_ready',
        ckpt_resp_data='functional_response_data',ckpt_resp_error='functional_response_error')
    instance('network',root,native)
    ce={n:'ce_'+n for n in ('descriptor_entry','descriptor_valid','descriptor_bank','descriptor_slot',
        'descriptor_width','descriptor_depth','request_valid','request_ready','response_valid','response_ready',
        'response_data','response_error')}
    ce.update(clock=clock,reset='capture_reset',read_enable='capture_read_enable',captured_ce='capture_captured_ce',
        bank='endpoint_bank',slot='endpoint_slot',address='endpoint_address')
    instance('ce_endpoint',root+'CheckpointPhysicalCEBank',ce)
    router={n:'capture_'+n for n in ('descriptor_entry','descriptor_valid','descriptor_bank','descriptor_slot',
        'descriptor_width','descriptor_depth','request_valid','request_ready','bank','slot','address',
        'response_valid','response_ready','response_data','response_error')}
    router.update(clock=clock,reset='capture_reset')
    params=instance('router','CheckpointPhysicalStateRouter',router,True)
    require(params==f'.ENTRIES({len(bank["state"])}),.GATES({descriptors["physical_clock_gates"]})','changed routing geometry')
    rows=[]
    for i,r in enumerate(bank['state']):
        rows.append(f"32'd{i}: begin functional_descriptor_valid=1; functional_descriptor_bank=8'd{r['bank']}; "
          f"functional_descriptor_slot=16'd{r['slot']}; functional_descriptor_width=16'd{r['transfer_width']}; "
          f"functional_descriptor_depth=32'd{r['transfer_depth']}; end")
    rom=re.search(r'  always @\* begin\n(.*?)\n  end',rtl,re.S)
    expected='''    functional_descriptor_valid=0; functional_descriptor_bank=0;
    functional_descriptor_slot=0; functional_descriptor_width=0; functional_descriptor_depth=0;
    case (functional_descriptor_entry)
'''+''.join('      '+r+'\n' for r in rows)+'''      default: begin end
    endcase'''
    require(rom and rom[1]==expected,'changed native descriptor ROM')
    require(len(re.findall(r'\b(?:always|initial|assign)\b',rtl))==1 and rtl.count('module ')==1 and
        rtl.count('endmodule')==1 and len(re.findall(r'\breg\b',rtl))==4,'unexpected native routing logic/storage')
    return dict(network=network,constraints=constraints,functional_entries=len(bank['state']),physical_clock_gates=descriptors['physical_clock_gates'],
        transfer_words=sum(r['depth'] for r in descriptors['state']))


def corruptions(generated,out):
    mutations={
        'native-reset':('.ckpt_reset(capture_reset)','.ckpt_reset(reset)'),
        'port-shape':('input wire [129:0] data','input wire [128:0] data'),
        'native-clock':('.ckpt_clock(clock)','.ckpt_clock(capture_clock_mask)'),
        'native-freeze':('.ckpt_freeze(capture_clock_mask)',".ckpt_freeze(1'b0)"),
        'ce-sample':('.captured_ce(capture_captured_ce)','.captured_ce(capture_logical_ce)'),
        'ce-reset':('.reset(capture_reset),.read_enable','.reset(reset),.read_enable'),
        'router-response':('.response_ready(capture_response_ready)',".response_ready(1'b1)"),
        'rom-depth':('functional_descriptor_depth=32\'d1;',"functional_descriptor_depth=32'd2;"),
    }
    rejected=[]
    for name,(old,new) in mutations.items():
        target=out/name;shutil.copytree(generated,target)
        path=target/(PREFIX+'.native-state-access.sv');original=path.read_text()
        changed=original.replace(old,new,1);require(changed!=original,'ineffective mutation '+name);path.write_text(changed)
        bind=target/(PREFIX+'.native-state-access.json');doc=json.loads(bind.read_text());doc['endpoint_sha256']=sha(path)
        bind.write_text(json.dumps(doc))
        try:audit(target)
        except ValueError as e:rejected.append(dict(name=name,error=str(e)))
        else:raise AssertionError('accepted coherent native routing mutation '+name)
    for name in ('missing-network','wrong-leaf','wrong-pin','missing-clause','wrong-placement',
                 'changed-specification','claim-constraints-attached'):
        target=out/name;shutil.copytree(generated,target)
        binding_path=target/(PREFIX+'.native-state-access-constraints.json')
        doc=json.loads(binding_path.read_text())
        suffix='.native-state-access.implementation.xdc'
        xdc=target/(PREFIX+suffix);original=xdc.read_text();changed=original
        if name=='missing-network':changed=original.replace('network/','')
        elif name=='wrong-leaf':changed=original.replace('left_/gate/O','right_/gate/O')
        elif name=='wrong-pin':changed=original.replace('/gate/O','/gate/I')
        elif name=='missing-clause':changed=original[:original.rfind('\n')]
        elif name=='wrong-placement':
            doc['original_post_link_path']='invented';doc['rebased_post_link_path']='invented/network'
            changed=original.replace('network/','invented/network/')
        elif name=='changed-specification':doc['constraint_specs'][-1]['format']='set_max_delay 0 -from [get_pins {}]'
        else:doc['production_constraints_attached']=True
        require(changed!=original or doc!=json.loads(binding_path.read_text()),'ineffective XDC mutation '+name)
        xdc.write_text(changed);doc['inputs'][suffix]=sha(xdc);binding_path.write_text(json.dumps(doc))
        try:audit(target)
        except ValueError as e:rejected.append(dict(name=name,error=str(e)))
        else:raise AssertionError('accepted coherent native constraint mutation '+name)
    return rejected


def manifest_header(generated, descriptor_suffix=".native-descriptors.json"):
    bank=json.loads((generated/(PREFIX+'.native-functional-binding.json')).read_text())
    widths=[];offsets=[];offset=0
    for r in bank['state']:
        widths.append(f"{r['slot']}: native_width={r['transfer_width']};")
        offsets.append(f"{r['slot']}: native_offset={offset};");offset+=r['transfer_depth']
    return 'localparam [255:0] MANIFEST=256\'h'+sha(generated/(PREFIX+descriptor_suffix))+';\n'+\
        'function automatic integer native_width(input integer e); case(e)\n'+'\n'.join(widths)+\
        '\ndefault: native_width=0; endcase endfunction\n'+\
        'function automatic integer native_offset(input integer e); case(e)\n'+'\n'.join(offsets)+\
        '\ndefault: native_offset=32; endcase endfunction\n'


def audit_frames(generated,lines, descriptor_suffix=".native-descriptors.json"):
    rows=json.loads((generated/(PREFIX+descriptor_suffix)).read_text())['state']
    bank=json.loads((generated/(PREFIX+'.native-functional-binding.json')).read_text())['state']
    require(len(lines)==36,'incomplete native snapshot')
    raw=[int(s,16).to_bytes(64,'little') for s in lines];frames=[int.from_bytes(v,'little') for v in raw]
    cut=field(frames[0],96,64);require(12<=cut<1024,'unexpected native fixture cut')
    memory=[None]*8;left=right=0;read=None
    mask130=(1<<130)-1
    pattern=lambda c:((c%4)<<128)|((0xfedcba9876543210^(c*0x10001))&((1<<64)-1))<<64|((0x123456789abcdef0^(c*0x12345))&((1<<64)-1))
    for c in range(cut):
        enable=3 if c<8 else c%4
        left+=bool(enable&1);right+=bool(enable&2)
        read=memory[c%8]
        if c<8 or c%3!=0:memory[c%8]=pattern(c)&mask130
    expected={'NativeStorage.cycles':cut,'NativeStorage.left_.value':left,'NativeStorage.right_.value':right,
        'NativeStorage.ram':memory,'NativeStorage.ram_r_data':read}
    word=0
    for i,frame in enumerate(frames):
        require(field(frame,0,64)==0x3154504b434d5346 and field(frame,64,16)==1 and field(frame,96,64)==cut,'bad native frame identity/cycle')
        require(field(frame,80,16)==(1 if i==0 else 3 if i==35 else 2),'bad native frame order')
        if i==0:require(field(frame,256,256)==int(sha(generated/(PREFIX+descriptor_suffix)),16) and field(frame,224,32)==7,'bad native manifest header')
        elif i==35:require(field(frame,160,64)==34 and field(frame,224,32)==crc32c(b''.join(raw[:-1]))^0xffffffff,'native trailer CRC/count mismatch')
        else:
            ordinal=field(frame,224,32);require(ordinal<7,'unknown native descriptor')
            row=rows[ordinal];at=field(frame,256,32)
            require(field(frame,160,64)==word and at<row['depth'] and field(frame,288,16)==row['width'] and
                field(frame,304,8)==row['bank'] and field(frame,312,16)==row['slot'],'native frame selector mismatch')
            if ordinal<5:
                r=bank[ordinal];chunks=(r['width']+63)//64;v=expected[r['hierarchy']]
                if isinstance(v,list):v=v[at//chunks]
                value=(v>>((at%chunks)*64))&((1<<64)-1)
            else:value=((3 if cut<8 else cut%4)>>(ordinal-5))&1
            require(field(frame,336,64)==value,'independent native word mismatch')
            word+=1
    require(word==34,'native word coverage incomplete')
    return dict(target_cut=cut,words=word,crc32c=field(frames[-1],224,32))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('production','vivado','vcs','audit'),required=True)
    for name in ('generated','native','eda','out'):parser.add_argument('--'+name,type=Path,required=name=='out')
    args=parser.parse_args();require(args.out.resolve().is_relative_to(RUNS),'evidence below runs required')
    args.out.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=args.mode+'-',dir=args.out.resolve()))
    sources={s:sha(ROOT/s) for s in SOURCES};commands=[]
    def run(argv,name,cwd=out,expected=0):
        row=dict(argv=list(map(str,argv)),cwd=str(cwd),log=str(out/(name+'.log')));commands.append(row)
        with Path(row['log']).open('w') as stream:p=subprocess.run(row['argv'],cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        row['returncode']=p.returncode;(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        require(p.returncode==expected,'inspect underlying log '+row['log']);return Path(row['log']).read_text()
    def validate(path,backend):
        require(path is not None and path.resolve().is_relative_to(RUNS),'receipt below runs required')
        doc=json.loads((path/'summary.json').read_text())
        require(doc['status']=='pass' and doc['backend']==backend and doc['sources']==sources and
            doc['physical_fpga_capture'] is False and doc['production_rocket_integrated'] is False,'stale or wrong-scope native widget receipt')
        for group in ('inputs','artifacts'):
            for name,value in doc[group].items():require((path/name).stat().st_size>0 and sha(path/name)==value,'changed native widget evidence '+name)
        for name in sources:require(sha(path/'sources'/Path(name).name)==sources[name],'changed source snapshot '+name)
        require((path/'synth.tcl').read_text()==TCL,'changed synthesis recipe')
        audit(path/'generated')
        bank=json.loads((path/'generated'/(PREFIX+'.native-functional-binding.json')).read_text())
        require((path/'native-selectors.svh').read_text()==selectors(bank) and
            (path/'native-widget-manifest.svh').read_text()==manifest_header(path/'generated'),'changed independent word inventory')
        return doc
    summary=dict(status='pass',backend='eda' if args.mode=='vcs' else 'f2',observed_utc=datetime.now(timezone.utc).isoformat(),
        host=socket.gethostname(),original_root=str(ROOT),sources=sources,
        scope='same-reference native state/CE/router and actual Widget component; complete production ownership unsupported',
        physical_fpga_capture=False,production_rocket_integrated=False)
    if args.mode=='production':
        summary.update(audit=audit(args.generated),inputs={str(p):sha(p) for p in args.generated.glob(PREFIX+'*')},artifacts={})
    elif args.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),'native localhost Vivado required')
        require(args.generated.resolve().is_relative_to(RUNS),'generated input below runs required')
        shutil.copytree(args.generated,out/'generated');summary['audit']=audit(out/'generated')
        summary['rejected_corruptions']=corruptions(out/'generated',out/'corruptions')
        for name in SOURCES:
            dest=out/'sources'/Path(name).name;require(not dest.exists(),'source basename collision')
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        bank=json.loads((out/'generated'/(PREFIX+'.native-functional-binding.json')).read_text())
        (out/'native-selectors.svh').write_text(selectors(bank));(out/'native-widget-manifest.svh').write_text(manifest_header(out/'generated'))
        (out/'synth.tcl').write_text(TCL)
        vendor=Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        summary['vendor_models']={}
        for name,src in [('BUFGCE.v',vendor/'unisims/BUFGCE.v'),('glbl.v',vendor/'glbl.v')]:
            shutil.copyfile(src,out/name);summary['vendor_models'][name]=dict(original_path=str(src),sha256=sha(src))
        summary['inputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and 'corruptions' not in p.parts}
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'synth')
        require('NATIVE_WIDGET_SYNTH_PASS gates=3 falling_edge_masks=1 raw_clock_endpoints=3' in text and
            'NATIVE_CONSTRAINTS_PASS queries=6 scope=access/network' in text and
            all('NATIVE_CONSTRAINT_QUERY_REJECTED kind='+kind in text for kind in ('get_cells','get_pins')) and
            not re.search(r'ERROR:|CRITICAL WARNING:',text),'native Widget synthesis failed')
        summary['artifacts']={n:sha(out/n) for n in ('native-widget.dcp','utilization.rpt','timing.rpt','synth.log','commands.json')}
    elif args.mode=='vcs':
        require(shutil.which('vcs')==toolchain.VCS and toolchain.VCS=='/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs','EDA native SP2 VCS required')
        native=validate(args.native,'f2')
        for name in native['inputs']:
            dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.native/name,dest)
        files=[out/n for n in FILES]+[out/'BUFGCE.v',out/'glbl.v',out/'sources/native_checkpoint_widget_tb.sv',out/'sources/checkpoint_widget_exit.cc']
        common=[toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
            '+incdir+'+str(out),'-top','native_checkpoint_widget_tb','-top','glbl']
        run([*common,'-Mdir=csrc','-o','simv',*files],'compile')
        healthy=out/'healthy';healthy.mkdir()
        text=run([out/'simv','-no_save','+frames='+str(healthy/'frames.hex')],'healthy',healthy)
        match=re.search(r'NATIVE_WIDGET_PASS checks=(\d+) cuts=5 words=170 stalls=(\d+) recovered_cycle=96',text)
        require(match,'incomplete native Widget execution')
        lines=(healthy/'frames.hex').read_text().splitlines();require(len(lines)==180,'incomplete native streams')
        summary.update(checks=int(match[1]),cuts=5,words=170,dma_stalls=int(match[2]),recovered_cycle=96,
            frame_audits=[audit_frames(out/'generated',lines[i:i+36]) for i in range(0,180,36)])
        for fault in ('missing','ce','cycle'):
            work=out/fault;work.mkdir();text=run([out/'simv','-no_save','+fault='+fault],fault,work)
            require('NATIVE_WIDGET_REJECT fault='+fault in text and 'acknowledged_edges=0' in text,'physical fault escaped')
        work=out/'corrupt';work.mkdir();text=run([out/'simv','-no_save','+corrupt'],'corrupt',work,expected=1)
        require('reason=independent native bank and CE payload' in text,'semantic corruption escaped')
        # Independently compile an actual native CE input misconnection.
        source=files[1].read_text();site='.captured_ce(capture_captured_ce)';require(source.count(site)==1,'ambiguous mutation')
        fault=out/'mutated-access.sv';fault.write_text(source.replace(site,'.captured_ce(~capture_captured_ce)'))
        run([*common,'-Mdir=fault-csrc','-o','fault-simv',files[0],fault,*files[2:]],'mutated-compile')
        work=out/'mutated';work.mkdir();text=run([out/'fault-simv','-no_save'],'mutated',work,expected=1)
        require('reason=independent native bank and CE payload' in text,'misconnected actual CE payload escaped')
        summary['negative_tests']=['missing','ce','cycle','corrupt','mutated']
        for name in ['healthy',*summary['negative_tests']]:
            wave=out/name/'native-widget.vcd';require(wave.stat().st_size>2000 and re.search(r'#[1-9]\d*',wave.read_text()),'missing full debug wave')
        summary.update(inputs=native['inputs'],vendor_models=native['vendor_models'],native_receipt=str(args.native/'summary.json'),
            artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.suffix in ('.log','.vcd','.hex')})
    else:
        native=validate(args.native,'f2');eda=validate(args.eda,'eda')
        require(native['inputs']==eda['inputs'] and eda['negative_tests']==['missing','ce','cycle','corrupt','mutated'] and
            eda['cuts']==5 and eda['words']==170 and eda['recovered_cycle']==96,'incomplete native/EDA scope')
        for name,doc in ((args.native,native),(args.eda,eda)):
            for model,row in doc['vendor_models'].items():require(sha(name/model)==row['sha256'],'changed native model')
        lines=(args.eda/'healthy/frames.hex').read_text().splitlines()
        require([audit_frames(args.eda/'generated',lines[i:i+36]) for i in range(0,180,36)]==eda['frame_audits'],'changed word audits')
        summary.update(matched_inputs=len(native['inputs']),matched_sources=len(sources),checks=eda['checks'],inputs={},artifacts={})
    require(sources=={s:sha(ROOT/s) for s in SOURCES},'source changed during verification')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(out/'summary.json')

if __name__=='__main__':main()
