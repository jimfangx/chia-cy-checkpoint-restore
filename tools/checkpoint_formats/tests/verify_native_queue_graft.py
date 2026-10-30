"""Synthesize the existing four Rocket queue executions with their shared graft.

Fresh EDA execution audits all native vector fields and every original bank
word. This is a readout component, not an atomic snapshot or an FPGA image.
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
from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.tests.audit_physical_clock_plan import parse_modules
from tools.checkpoint_formats.tests.verify_rocket_native_queues import SOURCES as QUEUE_SOURCES, audit_generated, sha

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
SELF = 'tools/checkpoint_formats/tests/verify_native_queue_graft.py'
SOURCES = (*QUEUE_SOURCES, SELF)
GRAFT = 'FireSim-generated.native-region-graft'
FLAGS = ('complete_fpga_capture', 'deployable_capture_image', 'production_freeze_owners_bound', 'metasim_restore_supported')


def audit(g):
    rows, observations = audit_generated(g)
    binding = json.loads((g/(GRAFT+'.json')).read_text())
    region_binding = json.loads((g/'binding.json').read_text())
    require(binding['graft_version']==1 and binding['scope']=='existing_native_regions_shared_readout_only' and
        binding['root']=='RocketQueueHost' and binding['raw_clock']=='clock' and
        binding['adapter_module']=='RocketQueueHostCheckpointRegionReadoutAdapter' and
        binding['adapter_instance']=='checkpoint_region_readout_adapter' and
        binding['common_mask_and_sample_interface'] is True, 'unsupported graft version/interface')
    require(binding['descriptor_manifest_sha256']==sha(g/'descriptors.json') and
        region_binding['descriptor_manifest_sha256']==sha(g/'descriptors.json'), 'changed graft descriptor identity')
    require(set(binding['files'])=={'.native-region-graft.sv','.native-region-graft-router.sv',
        '.native-region-graft-physical-router.sv'}, 'missing graft source owner')
    require(all(binding[k] is False for k in FLAGS), 'changed graft admission')
    require(binding['grafted_sha256'] == sha(g/'grafted.fir') and
            binding['regions_binding_sha256'] == sha(g/'binding.json'), 'changed graft source')
    for suffix, digest in binding['files'].items():
        require(sha(g/('FireSim-generated'+suffix)) == digest, 'changed graft file '+suffix)
    native = binding['native_state_observation']
    expected_regions = []
    for q in range(4):
        bank = json.loads((g/f'shell-{q}-banks-binding.json').read_text())
        expected_regions.append(dict(region=q, selected_execution=f'RocketQueueHost.q{q}',
            port=f'checkpoint_shell_region{q}_ckpt_native_state', offset=q*1664, bits=1664,
            banks_binding_sha256=sha(g/f'shell-{q}-banks-binding.json'), observation=bank['native_state_observation']))
    require(native == dict(version=1, port='capture_native_state', bits=6656, bit_order='shell_order_lsb0',
        regions=expected_regions, sampling_contract='atomically_stage_entire_vector_before_any_borrow_or_bank_request',
        stable_while_functional_freeze=False, atomic_snapshot_supported=False,
        complete_capture_owner=False, metasim_restore_supported=False), 'changed native vector layout/owner policy')
    old = parse_modules((g/'generated.fir').read_text())
    new = parse_modules((g/'grafted.fir').read_text())
    root = 'RocketQueueHost'
    adapter = root+'CheckpointRegionReadoutAdapter'
    require(set(new) == set(old) | {adapter}, 'changed concrete execution definitions')
    require(all(new[n] == old[n] for n in old if n != root), 'changed original queue/primitive definition')
    require(new[root]['instances'] == dict(old[root]['instances'], checkpoint_region_readout_adapter=adapter),
        'changed original concrete executions')
    require(new[root]['ports'].get('capture_native_state') == ('output', 'UInt<6656>'), 'reshaped aggregate port')
    require(not {'capture_logical_ce', 'capture_captured_ce'} & new[root]['ports'].keys(), 'invented CE owner')
    drivers = new[root]['drivers']
    require(drivers['capture_native_state'] == 'checkpoint_region_readout_adapter.capture_native_state', 'lost aggregate output')
    rtl = (g/(GRAFT+'.sv')).read_text()
    assignments = re.findall(r'^  assign capture_native_state\[(\d+) \+: (\d+)\] = (\w+);$', rtl, re.M)
    require(assignments == [(str(q*1664), '1664', f'checkpoint_shell_region{q}_ckpt_native_state') for q in range(4)],
        'crossed/omitted/aliased native aggregate')
    for q in range(4):
        pin = f'checkpoint_shell_region{q}_ckpt_native_state'
        require(drivers[f'checkpoint_region_readout_adapter.{pin}'] == pin and
            drivers[pin] == f'q{q}.{pin}', 'changed native observation wire identity')
    return rows, observations


def bench(g, rows, observations):
    # The native field oracle reads actual original registers directly. Layout
    # offsets and emitter register names were reconstructed independently above.
    header = re.search(r'module RocketQueueHost\((.*?)\n\);', (g/'grafted.sv').read_text(), re.S)[1]
    declarations, pins = [], []
    for line in header.splitlines():
        if not line.strip(): continue
        m = re.fullmatch(r'\s*(input|output)\s*(\[\d+:\d+\])?\s*(\w+),?', line)
        require(m is not None, 'unsupported grafted interface')
        direction, width, name = m.groups()
        init = "=0" if direction == 'input' else ''
        declarations.append(f"  {'reg' if direction=='input' else 'wire'} {width or ''} {name}{init};")
        pins.append(f'.{name}({name})')
    text = '''`timescale 1ns/1ps
module native_queue_graft_tb;
 import "DPI-C" function void checkpoint_widget_failed();
'''+ '\n'.join(declarations) + '\n RocketQueueHost dut('+','.join(pins)+');\n'
    text += ''' always #5 clock=~clock;
 integer checks=0, words=0, native_checks=0, stalls=0;
 integer i,j,q,cut;
 reg armed=0;
 task check(input bit ok,input string why);
   checks++;
   if(!ok) begin
     $display("NATIVE_GRAFT_DIVERGENCE signal=%s bank=%0d slot=%0d address=%0d words=%0d response_ack=%b",why,capture_bank,capture_slot,capture_address,words,capture_response_ready);
     checkpoint_widget_failed();$finish;
   end
 endtask
 function automatic [511:0] payload(input integer lane,input integer address);
   for(integer w=0;w<8;w++) payload[w*64+:64]=64'hcafe100000000000 ^ (64'(lane)<<48) ^ (64'(address)<<8) ^ 64'(w);
 endfunction
 reg [6655:0] expected_native;
 task compare_native;
 begin
'''
    for q, obs in enumerate(observations):
        for f in obs['state']:
            text += f" expected_native[{q*1664+f['offset']} +: {f['width']}] = dut.q{q}.{f['emitted_register']};\n"
    text += ''' check(capture_native_state===expected_native,"all 56 original native register vectors");
 native_checks++;
 end
 endtask
 always @(posedge clock) if(armed) begin compare_native(); #1;compare_native();end
 task tick; @(posedge clock); #2; endtask
 task readword(input integer bank,input integer slot,input integer address,input reg [63:0] expected);
 begin
   @(negedge clock);capture_bank=bank;capture_slot=slot;capture_address=address;
   capture_request_valid=1;capture_response_ready=0;
   while(!capture_request_ready) tick();
   tick();@(negedge clock);capture_request_valid=0;
   capture_bank=255;capture_slot=65535;capture_address=32'hffffffff;
   while(!capture_response_valid) tick();
   repeat(3) begin
     check(capture_response_valid && !capture_response_error && capture_response_data===expected,"word before acknowledgement");
     stalls++;tick();
   end
   @(negedge clock);capture_response_ready=1;words++;tick();
   @(negedge clock);capture_response_ready=0;
 end
 endtask
 initial begin
   $dumpfile("native-queue-graft.vcd");$dumpvars(0,native_queue_graft_tb);
   reset=1;capture_reset=1;repeat(5)tick();
   @(negedge clock);reset=0;capture_reset=0;
'''
    for q in range(4):
        text += f' lane{q}_io_enq_valid=1; lane{q}_io_deq_ready=0;\n'
    text += ' for(i=0;i<6144;i++) begin\n'
    for q in range(4):
        text += f' lane{q}_io_enq_bits=payload({q},i);\n'
    text += ' tick();@(negedge clock);end\n'
    for q in range(4):
        text += f' lane{q}_io_enq_valid=0; check(!lane{q}_io_enq_ready,"filled original RAM lane {q}");\n'
    text += ''' repeat(4)tick();armed=1;
 @(negedge clock);capture_clock_mask=1;capture_read_enable=1;
 repeat(3)tick();
'''
    for i, row in enumerate(rows):
        q = row['region']
        name = row['hierarchy'].split('.')[-1]
        text += f' capture_descriptor_entry={i};#1;check(capture_descriptor_valid && capture_descriptor_bank=={row["bank"]} && capture_descriptor_slot=={row["slot"]} && capture_descriptor_depth=={row["depth"]},"descriptor {i}");\n'
        if name == 'ram':
            text += f' for(j=0;j<6144;j++) for(i=0;i<8;i++) readword({row["bank"]},{row["slot"]},j*8+i,64\'(payload({q},j)>>(i*64)));\n'
        else:
            # Original pointers, full flag and original reader-address latch
            # follow the directed frontdoor fill: all pointer addresses are zero.
            expected = 1 if name == 'maybe_full' else 0
            require(name in ('enq_ptr_value', 'deq_ptr_value', 'maybe_full', 'ram_io_deq_bits_MPORT_addr'), 'unexpected original queue register '+name)
            text += f' readword({row["bank"]},{row["slot"]},0,64\'d{expected});\n'
    text += ''' capture_descriptor_entry=20;#1;check(!capture_descriptor_valid,"descriptor bound");
 @(negedge clock);capture_clock_mask=0;capture_read_enable=0;
'''
    for q in range(4):
        text += f' lane{q}_io_deq_ready=1;\n'
    text += ' for(i=0;i<128;i++) begin\n'
    for q in range(4):
        text += f' check(lane{q}_io_deq_valid && lane{q}_io_deq_bits===payload({q},i),"frontdoor resume lane {q}");\n'
    text += ''' tick();@(negedge clock);end
 check(words==196624 && native_checks>1000000 && stalls==3*words,"complete transfer scope");
 $display("NATIVE_GRAFT_PASS words=%0d native_checks=%0d stalls=%0d checks=%0d",words,native_checks,stalls,checks);$finish;
 end
 initial begin #30000000;$display("NATIVE_GRAFT_TIMEOUT");checkpoint_widget_failed();$finish;end
endmodule
'''
    return text


def negative_audits(g, out):
    results = []
    for case in ('swapped-lane', 'aliased-offset', 'omitted-lane', 'false-atomic-owner', 'wrong-root-wire', 'unsupported-version'):
        d = out / case
        shutil.copytree(g, d)
        binding_path = d / (GRAFT+'.json')
        binding = json.loads(binding_path.read_text())
        if case == 'swapped-lane':
            rtl = d / (GRAFT+'.sv')
            rtl.write_text(rtl.read_text().replace(
                '1664] = checkpoint_shell_region0_ckpt_native_state;',
                '1664] = checkpoint_shell_region1_ckpt_native_state;'))
        elif case == 'aliased-offset':
            binding['native_state_observation']['regions'][1]['offset'] = 0
        elif case == 'omitted-lane':
            binding['native_state_observation']['regions'].pop()
        elif case == 'false-atomic-owner':
            binding['native_state_observation']['atomic_snapshot_supported'] = True
        elif case == 'unsupported-version':
            binding['graft_version'] = 2
        else:
            fir = d / 'grafted.fir'
            fir.write_text(fir.read_text().replace(
                'capture_native_state <= checkpoint_region_readout_adapter.capture_native_state',
                'capture_native_state <= UInt<6656>(0)'))
        binding['grafted_sha256'] = sha(d/'grafted.fir')
        binding['files'] = {suffix: sha(d/('FireSim-generated'+suffix)) for suffix in binding['files']}
        binding_path.write_bytes(canonical(binding))
        try:
            audit(d)
        except FormatError as error:
            results.append(dict(case=case, rejected=True, reason=str(error)))
        else:
            raise AssertionError('coherently rehashed corruption accepted: '+case)
    return results


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
        scope='shared exact queue graft readout; atomic native staging and production capture remain unsupported')
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
        tcl='set_param general.maxThreads 4\nread_verilog -sv generated/grafted.sv\n'+''.join(
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
report_utilization -file utilization.rpt
report_timing_summary -delay_type min_max -file timing.rpt
write_checkpoint -force native-queue-graft.dcp
puts "NATIVE_QUEUE_GRAFT_SYNTH_PASS"
'''
        (out/'synth.tcl').write_text(tcl)
        doc['inputs']={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and f.name!='summary.json'};save()
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'native')
        require('NATIVE_QUEUE_GRAFT_SYNTH_PASS' in text and not re.search(r'ERROR:|CRITICAL WARNING:',text),'native synthesis failure')
        doc.update(uram_primitives=64,native_bits=6656,original_entries=20)
    else:
        require(str(ROOT).startswith('/scratch/') and toolchain.VCS.endswith('Y-2026.03-SP2/bin/vcs'),'EDA SP2 required')
        receipt=a.native/'summary.json';native=json.loads(receipt.read_text())
        require(native['status']=='pass' and native['sources']==sources,'stale native receipt')
        for group in ('inputs','artifacts'):
            for n,h in native[group].items():require(sha(a.native/n)==h,'changed native artifact '+n)
        for n in native['inputs']:
            dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.native/n,dest)
        doc['inputs']=dict(native['inputs'])
        rows,obs=audit(out/'generated');require((out/'bench.sv').read_text()==bench(out/'generated',rows,obs),'changed oracle')
        files=[out/'generated/grafted.sv',*sorted((out/'generated').glob(GRAFT+'*.sv')),out/'BUFGCE.v',out/'glbl.v',out/'bench.sv',out/'exit.cc']
        def compile(label):
            run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all','-top','native_queue_graft_tb','-top','glbl',
                '-Mdir='+str(out/'csrc'),'-o',out/'simv',*files],label)
        compile('compile');text=run([out/'simv','-no_save'],'healthy')
        require('NATIVE_GRAFT_PASS words=196624 ' in text,'incomplete graft execution')
        wave=out/'native-queue-graft.vcd';original_sha=sha(wave)
        with (out/'native-queue-graft.vcd.gz').open('wb') as f:subprocess.run(['pigz','-p','4','-1','-c',str(wave)],stdout=f,check=True)
        subprocess.run(['pigz','-p','4','-t',str(out/'native-queue-graft.vcd.gz')],check=True)
        retained=RUNS/'migration-source'/out.parent.parent.name/out.name/wave.name
        retained.parent.mkdir(parents=True,exist_ok=True);wave.rename(retained)
        doc['waveform']=dict(original_remote_path=str(wave),retained_remote_path=str(retained),original_sha256=original_sha,
            compressed_path=str(out/'native-queue-graft.vcd.gz'))
        # Separately compiled wrong lane routes must diverge before any bank ack.
        rtl=out/'generated'/(GRAFT+'.sv');original=rtl.read_text()
        first='assign capture_native_state[0 +: 1664] = checkpoint_shell_region0_ckpt_native_state;'
        require(original.count(first)==1,'nonunique compiled mutation site')
        rtl.write_text(original.replace(first,first.replace('region0_','region1_')))
        compile('mutation-compile');text=run([out/'simv','-no_save'],'mutation',1)
        require('NATIVE_GRAFT_DIVERGENCE signal=all 56 original native register vectors' in text and
            'words=0 response_ack=0' in text,'native corruption was acknowledged')
        mutation_source=out/'compiled-native-swap.sv'
        mutation_source.write_text(rtl.read_text())
        doc['compiled_mutation_source']=dict(path=str(mutation_source),sha256=sha(mutation_source))
        rtl.write_text(original)
        # The full negative waveform is retained separately as evidence.
        (out/'native-queue-graft.vcd').rename(out/'native-queue-graft-mutation.vcd')
        doc['native_receipt']=dict(path=str(receipt),sha256=sha(receipt));doc['compiled_native_swap_rejected_before_ack']=True
    require(sources=={n:sha(ROOT/n) for n in SOURCES},'sources changed during execution')
    require(all(sha(out/n)==h for n,h in doc['inputs'].items()),'execution inputs changed')
    doc['artifacts']={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and
        (f.suffix in ('.log','.rpt','.dcp','.gz','.vcd') or f.name=='compiled-native-swap.sv')}
    doc['status']='pass';save();print(out/'summary.json',flush=True)

if __name__=='__main__':main()
