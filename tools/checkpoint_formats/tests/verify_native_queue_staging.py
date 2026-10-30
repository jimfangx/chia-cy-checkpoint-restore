"""Common raw-edge staging of the shared four-queue graft; component evidence only.

Synthesis is native localhost Vivado; all VCS execution is restricted to EDA.
The full original graft bank-transfer/dequeue regression remains in the bench.
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
from tools.checkpoint_formats.codec import canonical, require, FormatError
from tools.checkpoint_formats.tests import verify_native_queue_graft as base
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules

ROOT, RUNS, sha = base.ROOT, base.RUNS, base.sha
SELF = 'tools/checkpoint_formats/tests/verify_native_queue_staging.py'
SOURCES = (*base.SOURCES, SELF)
GRAFT = 'Staged-generated.native-region-graft'
NEGATIVES = ('missing-owner', 'no-freeze', 'premature', 'same-edge', 'lost-owner',
             'lost-freeze', 'drift', 'busy-release', 'busy-recapture', 'release', 'reset')


def audit(g):
    rows, observations = base.audit(g)
    b = json.loads((g/(GRAFT+'.json')).read_text())
    old = json.loads((g/(base.GRAFT+'.json')).read_text())
    snapshot = b.pop('native_state_snapshot')
    require(snapshot == dict(version=1,module='CheckpointNativeStateSnapshot',
        instance='checkpoint_region_readout_adapter.native_snapshot',bits=6656,words=104,control_bits=6727,
        control_layout_lsb0=['payload','occupied','cut_cycle','error'],
        sampling='one_common_raw_positive_edge_preedge_values_before_any_bank_request',
        idle='router_ready_and_every_endpoint_ready_and_no_endpoint_response',
        bank_requests_and_responses_gated=True,restore_supported=False,global_freeze_owner_bound=False,
        owner='capture_only_native_staging_control'), 'changed native staging layout/ownership')
    require(set(b['files']) == set(old['files']) | {'.native-region-graft-snapshot.sv'}, 'missing staging source')
    for suffix, digest in b['files'].items():
        require(sha(g/('Staged-generated'+suffix)) == digest, 'changed staging source '+suffix)
    require((g/(GRAFT+'-snapshot.sv')).read_bytes() ==
        (ROOT/'sims/firesim/sim/midas/src/main/verilog/CheckpointNativeStateSnapshot.sv').read_bytes(),
        'foreign snapshot implementation')
    require(b['grafted_sha256'] == sha(g/'staged.fir'), 'changed staged circuit')
    for k in ('files','grafted_sha256'):
        b.pop(k);old.pop(k)
    require(b == old, 'staging changed original bank identities/admission')
    a, z = parse_modules((g/'grafted.fir').read_text()), parse_modules((g/'staged.fir').read_text())
    require(a.keys()==z.keys() and all(a[n]==z[n] for n in a if n not in
        ('RocketQueueHost','RocketQueueHostCheckpointRegionReadoutAdapter')), 'staging duplicated/changed original execution')
    extra = dict(request=1,release=1,owners_present=1,target_cycle=64,word_address=32,ready=1,valid=1,failed=1,
        borrow_enable=1,word_error=1,word_data=64,cut_cycle=64,error=6,state=6656,control_state=6727)
    inputs = {'request','release','owners_present','target_cycle','word_address'}
    for n in ('RocketQueueHost','RocketQueueHostCheckpointRegionReadoutAdapter'):
        require(z[n]['ports'] == dict(a[n]['ports'], **{'capture_snapshot_'+k:
            ('input' if k in inputs else 'output',f'UInt<{v}>') for k,v in extra.items()}), 'reshaped staging interface')
    rtl = (g/(GRAFT+'.sv')).read_text()
    require(re.findall(r'^  assign capture_native_state\[(\d+) \+: (\d+)\] = (\w+);$',rtl,re.M) ==
        [(str(q*1664),'1664',f'checkpoint_shell_region{q}_ckpt_native_state') for q in range(4)], 'crossed native lanes')
    required = ['wire staged_permission = capture_snapshot_borrow_enable;',
        'wire all_readers_idle = raw_request_ready && (&region_request_ready) && !(|region_response_valid);',
        'assign capture_request_ready = raw_request_ready && staged_permission;',
        'assign capture_response_valid = raw_response_valid && staged_permission;',
        'assign capture_response_data = staged_permission ? raw_response_data : 64\'b0;',
        'assign capture_response_error = raw_response_error && staged_permission;',
        '.request_valid(capture_request_valid && staged_permission), .request_ready(raw_request_ready),',
        '.response_valid(raw_response_valid), .response_ready(capture_response_ready && staged_permission),',
        '.functional_frozen(capture_clock_mask && capture_read_enable), .reader_idle(all_readers_idle),',
        '.borrow_attempt(capture_request_valid), .target_cycle(capture_snapshot_target_cycle),',
        '.live_state(capture_native_state), .word_address(capture_snapshot_word_address),',
        '.clock(clock), .reset(capture_reset), .restore_hold(1\'b0), .restore_load(1\'b0),',
        '.restore_state(6727\'d0), .restore_ready(),']
    require(all(rtl.count(s)==1 for s in required), 'changed raw clock, idle, gating or sample connection')
    for k in extra:
        if k in inputs:continue
        require(z['RocketQueueHost']['drivers']['capture_snapshot_'+k] ==
            'checkpoint_region_readout_adapter.capture_snapshot_'+k, 'lost staging output '+k)
    expected_drivers = dict(a['RocketQueueHost']['drivers'])
    for k in extra:
        pin = 'capture_snapshot_'+k
        left, right = ('checkpoint_region_readout_adapter.'+pin,pin) if k in inputs else (
            pin,'checkpoint_region_readout_adapter.'+pin)
        expected_drivers[left] = right
    require(z['RocketQueueHost']['drivers'] == expected_drivers, 'changed original or staged root wiring')
    return rows, observations


def negative_audits(g, out):
    results=[]
    for case in ('ungated-request','ungated-response','partial-idle','wrong-clock','wrong-sample',
                 'false-restore','truncated-control','wrong-root-wire'):
        d=out/case;shutil.copytree(g,d)
        p=d/(GRAFT+'.json');b=json.loads(p.read_text());rtl=d/(GRAFT+'.sv')
        if case=='false-restore':b['native_state_snapshot']['restore_supported']=True
        elif case=='truncated-control':b['native_state_snapshot']['control_bits']=6656
        elif case=='wrong-root-wire':
            f=d/'staged.fir';f.write_text(f.read_text().replace(
                'capture_snapshot_state <= checkpoint_region_readout_adapter.capture_snapshot_state',
                'capture_snapshot_state <= UInt<6656>(0)'))
        else:
            before,after={
                'ungated-request':('capture_request_valid && staged_permission','capture_request_valid'),
                'ungated-response':('capture_response_ready && staged_permission','capture_response_ready'),
                'partial-idle':('raw_request_ready && (&region_request_ready) && !(|region_response_valid)','raw_request_ready'),
                'wrong-clock':('.clock(clock), .reset(capture_reset), .restore_hold',".clock(1'b0), .reset(capture_reset), .restore_hold"),
                'wrong-sample':('.live_state(capture_native_state)',".live_state(6656'd0)"),
            }[case]
            require(rtl.read_text().count(before)==1,'ambiguous structural mutation '+case)
            rtl.write_text(rtl.read_text().replace(before,after))
        b['grafted_sha256']=sha(d/'staged.fir')
        b['files']={s:sha(d/('Staged-generated'+s)) for s in b['files']}
        p.write_bytes(canonical(b))
        try:audit(d)
        except FormatError as error:results.append(dict(case=case,rejected=True,reason=str(error)))
        else:raise AssertionError('coherently rehashed staging corruption accepted: '+case)
    return results


def bench(g, rows, observations):
    text = base.bench(g,rows,observations)
    decl = '''
 reg capture_snapshot_request=0,capture_snapshot_release=0,capture_snapshot_owners_present=1;
 reg [63:0] capture_snapshot_target_cycle=9001;
 reg [31:0] capture_snapshot_word_address=0;
 wire capture_snapshot_ready,capture_snapshot_valid,capture_snapshot_failed,capture_snapshot_borrow_enable,capture_snapshot_word_error;
 wire [63:0] capture_snapshot_word_data,capture_snapshot_cut_cycle;
 wire [5:0] capture_snapshot_error;
 wire [6655:0] capture_snapshot_state;
 wire [6726:0] capture_snapshot_control_state;
 reg [6655:0] saved;
 reg staged_active=0;
 integer snapshot_words=0,snapshot_cuts=0,changed_live=0;
 string fault;
'''
    ports = re.findall(r'\b(capture_snapshot_\w+)\b',decl)
    ports = list(dict.fromkeys(ports))
    text = text.replace(' RocketQueueHost dut(',decl+' RocketQueueHost dut('+''.join(f'.{p}({p}),' for p in ports))
    text = text.replace(' always @(posedge clock) if(armed) begin compare_native(); #1;compare_native();end', '''
 always @(posedge clock) if(armed) begin
   compare_native();
   if(!capture_snapshot_borrow_enable)check(
     !(|(dut.checkpoint_region_readout_adapter.region_request_valid & dut.checkpoint_region_readout_adapter.region_request_ready)) &&
     !(|(dut.checkpoint_region_readout_adapter.region_response_valid & dut.checkpoint_region_readout_adapter.region_response_ready)),
     "no hidden region acknowledgement without a staged owner");
   if(staged_active)begin
     check(capture_snapshot_valid && capture_snapshot_borrow_enable && !capture_snapshot_failed,"staged cut remains valid");
     check(capture_snapshot_state===saved,"staged vector immutable during native borrow");
     check(capture_snapshot_control_state==={6'b0,capture_snapshot_target_cycle,1'b1,saved},"complete staging/control owner");
     if(capture_native_state!==saved)changed_live++;
   end
   #1;compare_native();
 end
 task stage;
 begin
   @(negedge clock);capture_snapshot_request=1;compare_native();saved=expected_native;
   #1;check(capture_snapshot_ready && !capture_snapshot_borrow_enable && !capture_request_ready,"no borrowing at capture edge");
   tick();capture_snapshot_request=0;#1;
   check(capture_snapshot_valid && capture_snapshot_state===saved && capture_snapshot_cut_cycle==capture_snapshot_target_cycle,"one preedge vector and cut");
   staged_active=1;snapshot_cuts++;
   for(integer w=0;w<104;w++)begin
     @(negedge clock);capture_snapshot_word_address=w;#1;
     check(!capture_snapshot_word_error && capture_snapshot_word_data===saved[w*64+:64],"all staged words before bank ack");
     snapshot_words++;tick();
   end
   @(negedge clock);capture_snapshot_word_address=104;#1;
   check(capture_snapshot_word_error && capture_snapshot_word_data==0,"out of bounds staging word");
 end
 endtask
 task unstage;
 begin
   @(negedge clock);staged_active=0;capture_snapshot_release=1;#1;
   check(!capture_snapshot_valid && !capture_request_ready && !capture_response_valid,"release revokes permission before edge");
   tick();capture_snapshot_release=0;#1;check(!capture_snapshot_failed && !capture_snapshot_valid,"healthy release");
 end
 endtask
 task negative;
 begin
   staged_active=0;
   if(fault=="lost-owner")capture_snapshot_owners_present=0;
   if(fault=="lost-freeze")capture_clock_mask=0;
   if(fault=="drift")capture_snapshot_target_cycle++;
   if(fault=="release")capture_snapshot_release=1;
   if(fault=="reset")capture_reset=1;
   if(fault=="busy-release" || fault=="busy-recapture")begin
     @(negedge clock);capture_bank=0;capture_slot=0;capture_address=0;capture_request_valid=1;
     tick();@(negedge clock);capture_request_valid=0;
     while(!capture_response_valid)tick();
     if(fault=="busy-release")capture_snapshot_release=1;
     else capture_snapshot_request=1;
     capture_response_ready=1;
   end
   #1;check(!capture_request_ready && !capture_response_valid && !capture_snapshot_valid &&
      !capture_snapshot_borrow_enable && capture_snapshot_word_error,"fault revoked before any acknowledgement");
   if(fault!="release" && fault!="reset")check(capture_snapshot_failed,"unsafe cut fails");
   check(
     !(|(dut.checkpoint_region_readout_adapter.region_request_valid & dut.checkpoint_region_readout_adapter.region_request_ready)) &&
     !(|(dut.checkpoint_region_readout_adapter.region_response_valid & dut.checkpoint_region_readout_adapter.region_response_ready)),
     "no hidden region acknowledgement without a staged owner");
   tick();$display("NATIVE_STAGING_NEGATIVE_PASS case=%s words=%0d response_ack=0",fault,words);$finish;
 end
 endtask
''')
    text = text.replace(' reset=1;capture_reset=1;repeat(5)tick();','''
   if(!$value$plusargs("fault=%s",fault))fault="";
   reset=1;capture_reset=1;repeat(5)tick();''')
    needle=' repeat(3)tick();\n'
    require(text.count(needle)==1,'ambiguous staging cut insertion')
    text=text.replace(needle,needle+'''
 if(fault=="missing-owner" || fault=="no-freeze" || fault=="premature" || fault=="same-edge")begin
   if(fault=="missing-owner")capture_snapshot_owners_present=0;
   if(fault=="no-freeze")capture_clock_mask=0;
   if(fault!="premature")capture_snapshot_request=1;
   if(fault=="premature" || fault=="same-edge")capture_request_valid=1;
   negative();
 end
 stage();
 if(fault!="")negative();
''')
    text=text.replace(' @(negedge clock);capture_clock_mask=0;capture_read_enable=0;',
        ' unstage();\n @(negedge clock);capture_clock_mask=0;capture_read_enable=0;')
    text=text.replace(' for(i=0;i<128;i++) begin\n',''' for(i=0;i<128;i++) begin
 if(i==32 || i==64 || i==96)begin
   capture_clock_mask=1;capture_read_enable=1;capture_snapshot_target_cycle=9001+i;
   repeat(3)tick();stage();unstage();
   @(negedge clock);capture_clock_mask=0;capture_read_enable=0;
 end
''')
    text=text.replace(' $display("NATIVE_GRAFT_PASS', ''' check(snapshot_cuts==4 && snapshot_words==416 && changed_live>100,"complete staging scope");
 $display("NATIVE_STAGING_PASS cuts=%0d words=%0d live_changes=%0d",snapshot_cuts,snapshot_words,changed_live);
 $display("NATIVE_GRAFT_PASS''')
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',required=True,choices=('vivado','vcs'))
    p.add_argument('--generated',type=Path);p.add_argument('--native',type=Path)
    p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    require(a.out.resolve().is_relative_to(RUNS),'evidence must be under runs')
    a.out.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=a.mode+'-',dir=a.out.resolve()))
    sources={n:sha(ROOT/n) for n in SOURCES}
    doc=dict(status='running',backend='f2' if a.mode=='vivado' else 'eda',sources=sources,commands=[],
        observed_utc=datetime.now(timezone.utc).isoformat(),physical_fpga_capture=False,full_image=False,
        scope='shell-only shared graft atomic native staging; no production freeze, CPU migration or FPGA capture')
    def save(): (out/'summary.json').write_text(json.dumps(doc,indent=2)+'\n')
    def run(argv,label,expected=0):
        argv=list(map(str,argv));log=out/(label+'.log')
        with log.open('w') as f:r=subprocess.run(argv,cwd=out,stdout=f,stderr=subprocess.STDOUT)
        doc['commands'].append(dict(argv=argv,cwd=str(out),returncode=r.returncode,log=str(log),sha256=sha(log)));save()
        require(r.returncode==expected,'inspect underlying log '+str(log));return log.read_text()
    save();print(out,flush=True)
    if a.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),'native manager Vivado required')
        shutil.copytree(a.generated,out/'generated');rows,obs=audit(out/'generated')
        doc['negative_audits']=negative_audits(out/'generated',out/'audit-negatives')
        (out/'bench.sv').write_text(bench(out/'generated',rows,obs))
        shutil.copyfile(ROOT/'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',out/'exit.cc')
        vendor=Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        for n in ('BUFGCE.v','glbl.v'):shutil.copyfile(vendor/('unisims/'+n if n=='BUFGCE.v' else n),out/n)
        tcl='set_param general.maxThreads 4\nread_verilog -sv generated/staged.sv\n'+''.join(
            'read_verilog -sv '+str(f.relative_to(out))+'\n' for f in sorted((out/'generated').glob(GRAFT+'*.sv')))+'''
read_xdc generated/generated.synthesis.xdc
synth_design -top RocketQueueHost -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
foreach q {0 1 2 3} {
 set count 0
 foreach cell [get_cells -hier -filter {REF_NAME =~ URAM*}] {
  if {[string match "q$q/*" [get_property NAME $cell]]} {incr count}
 }
 if {$count != 16} {error "original queue $q requires sixteen URAMs, got $count"}
}
if {[llength [get_cells -hier -filter {REF_NAME =~ RAM*}]] != 0} {error "unexpected LUT/BLOCK RAM fallback"}
proc bit_driver {port bit} {
 set nets [get_nets -segments -of_objects [get_ports [format {%s[%d]} $port $bit]]]
 set pins [get_pins -leaf -of_objects $nets -filter {DIRECTION == OUT}]
 if {[llength $pins] != 1} {error "missing/ambiguous synthesized bit driver $port/$bit"}
 return $pins
}
set map [open payload-map.txt w]
set payload_cells {}
set ce_nets {}
for {set i 0} {$i<6727} {incr i} {
 set pin [bit_driver capture_snapshot_control_state $i]
 set cell [get_cells -of_objects $pin]
 set ref [get_property REF_NAME $cell]
 # Each region has one local functional bank. The actual local bank selector
 # and its saved byte are provably zero in this synthesized network. Admit
 # ONLY these independently enumerated 32 constant bits, never an arbitrary
 # missing payload register or a constant substitute for a dynamic field.
 set constant [expr {$i<6656 && ($i%1664)>=1059 && ($i%1664)<1067}]
 if {$constant} {
  if {$ref ne "GND" || [bit_driver capture_native_state $i] ne $pin} {error "changed constant native bank bit $i"}
 } else {
  if {$ref ne "FDRE"} {error "unstaged native/control bit $i"}
  set prefix checkpoint_region_readout_adapter/native_snapshot/
  if {$i<6656} {
   set expected [format {%spayload_reg[%d]/Q} $prefix $i]
   lappend payload_cells $cell
   set d [get_pins -of_objects $cell -filter {REF_PIN_NAME == D}]
   set input_nets [get_nets -segments -of_objects $d]
   set live_nets [get_nets -segments -of_objects [get_ports [format {capture_native_state[%d]} $i]]]
   set shared 0
   foreach net $live_nets {if {[lsearch -exact $input_nets $net]>=0} {set shared 1}}
   if {!$shared} {error "crossed original native payload D bit $i"}
   lappend ce_nets [get_nets -of_objects [get_pins -of_objects $cell -filter {REF_PIN_NAME == CE}]]
  } elseif {$i==6656} {set expected ${prefix}occupied_reg/Q
  } elseif {$i<6721} {set expected [format {%scut_cycle_reg[%d]/Q} $prefix [expr {$i-6657}]]
  } else {set expected [format {%serror_reg[%d]/Q} $prefix [expr {$i-6721}]]}
  if {$pin ne $expected} {error "crossed staging/control Q bit $i: $pin"}
  set c [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
  if {[get_clocks -of_objects $c] ne "raw_clock"} {error "foreign staging clock $i"}
 }
 if {$i<6656 && [bit_driver capture_snapshot_state $i] ne $pin} {error "payload/control readback differs at $i"}
 puts $map "$i|$pin|$ref"
}
close $map
if {[llength [lsort -unique $payload_cells]]!=6624 || [llength [lsort -unique $ce_nets]]!=1} {
 error "incomplete or non-atomic synthesized staging storage"
}
puts "NATIVE_STAGING_STORAGE_PASS dynamic_payload=6624 constant_bank_bits=32 control_bits=71"
report_utilization -file utilization.rpt
report_timing_summary -delay_type min_max -file timing.rpt
write_checkpoint -force native-queue-staging.dcp
puts "NATIVE_QUEUE_STAGING_SYNTH_PASS"
'''
        (out/'synth.tcl').write_text(tcl)
        doc['inputs']={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and f.name!='summary.json'};save()
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'native')
        require('NATIVE_QUEUE_STAGING_SYNTH_PASS' in text and not re.search(r'ERROR:|CRITICAL WARNING:',text),'native synthesis failure')
    else:
        require(str(ROOT).startswith('/scratch/') and toolchain.VCS.endswith('Y-2026.03-SP2/bin/vcs'),'EDA SP2 required')
        receipt=a.native/'summary.json';native=json.loads(receipt.read_text())
        require(native['status']=='pass' and native['sources']==sources,'stale native receipt')
        for group in ('inputs','artifacts'):
            for n,h in native[group].items():require(sha(a.native/n)==h,'changed native artifact '+n)
        for n in native['inputs']:
            dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.native/n,dest)
        doc['inputs']=dict(native['inputs'])
        rows,obs=audit(out/'generated');require((out/'bench.sv').read_text()==bench(out/'generated',rows,obs),'changed staging oracle')
        files=[out/'generated/staged.sv',*sorted((out/'generated').glob(GRAFT+'*.sv')),out/'BUFGCE.v',out/'glbl.v',out/'bench.sv',out/'exit.cc']
        def compile(label):
            run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all','-top','native_queue_graft_tb','-top','glbl',
                '-Mdir='+str(out/'csrc'),'-o',out/'simv',*files],label)
        compile('compile');text=run([out/'simv','-no_save'],'healthy')
        require('NATIVE_GRAFT_PASS words=196624 ' in text and 'NATIVE_STAGING_PASS cuts=4 words=416 ' in text,'incomplete staged graft execution')
        wave=out/'native-queue-graft.vcd';original_sha=sha(wave)
        with (out/'native-queue-staging.vcd.gz').open('wb') as f:subprocess.run(['pigz','-p','4','-1','-c',str(wave)],stdout=f,check=True)
        subprocess.run(['pigz','-p','4','-t',str(out/'native-queue-staging.vcd.gz')],check=True)
        retained=RUNS/'migration-source'/out.parent.parent.name/out.name/wave.name
        retained.parent.mkdir(parents=True,exist_ok=True);wave.rename(retained)
        doc['waveform']=dict(original_remote_path=str(wave),retained_remote_path=str(retained),original_sha256=original_sha,
            compressed_path=str(out/'native-queue-staging.vcd.gz'))
        for case in NEGATIVES:
            text=run([out/'simv','-no_save','+fault='+case],'fault-'+case)
            require('NATIVE_STAGING_NEGATIVE_PASS case='+case+' words=0 response_ack=0' in text,'unsafe case acknowledged '+case)
            (out/'native-queue-graft.vcd').rename(out/('fault-'+case+'.vcd'))
        rtl=out/'generated'/(GRAFT+'.sv');original=rtl.read_text()
        first='.live_state(capture_native_state),'
        require(original.count(first)==1,'nonunique mutation')
        rtl.write_text(original.replace(first,'.live_state({capture_native_state[1663:0],capture_native_state[6655:1664]}),'))
        compile('mutation-compile');text=run([out/'simv','-no_save'],'mutation',1)
        require('NATIVE_GRAFT_DIVERGENCE signal=one preedge vector and cut' in text and
            'words=0 response_ack=0' in text,'semantic staging corruption acknowledged')
        (out/'compiled-staging-swap.sv').write_text(rtl.read_text());rtl.write_text(original)
        (out/'native-queue-graft.vcd').rename(out/'mutation.vcd')
        for gate,case in (('capture_request_valid','premature'),('capture_response_ready','busy-release')):
            before=gate+' && staged_permission'
            require(original.count(before)==1,'ambiguous compiled handshake mutation')
            rtl.write_text(original.replace(before,gate))
            compile('mutation-'+case+'-compile')
            text=run([out/'simv','-no_save','+fault='+case],'mutation-'+case,1)
            require('NATIVE_GRAFT_DIVERGENCE signal=no hidden region acknowledgement without a staged owner' in text and
                'words=0 ' in text,'missing handshake gate escaped '+case)
            (out/('compiled-'+case+'.sv')).write_text(rtl.read_text());rtl.write_text(original)
            (out/'native-queue-graft.vcd').rename(out/('mutation-'+case+'.vcd'))
        doc.update(native_receipt=dict(path=str(receipt),sha256=sha(receipt)),compiled_mutation_rejected_before_ack=True)
    require(sources=={n:sha(ROOT/n) for n in SOURCES},'sources changed during execution')
    require(all(sha(out/n)==h for n,h in doc['inputs'].items()),'execution inputs changed')
    doc['artifacts']={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and
        (f.suffix in ('.log','.rpt','.dcp','.gz','.vcd') or
         (f.name.startswith('compiled-') and f.suffix == '.sv') or f.name == 'payload-map.txt')}
    doc['status']='pass';save();print(out/'summary.json',flush=True)

if __name__=='__main__':main()
