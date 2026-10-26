"""Native/EDA verification of permanently parked physical register restore.

No continuation, complete FPGA owner, stream replay or hardware capture claim.
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
from tools.checkpoint_formats.tests import verify_transport_control_state as control

ROOT, RUNS = control.ROOT, control.RUNS
VERILOG = 'sims/firesim/sim/midas/src/main/verilog/'
RTL = (*control.RTL, VERILOG+'CheckpointTransportPhysicalRestore.sv',
       VERILOG+'CheckpointTransportControlRestore.sv')
TB = 'tools/checkpoint_formats/tests/physical_transport_restore_tb.sv'
SPECIAL_TB = 'tools/checkpoint_formats/tests/physical_transport_restore_specialization_tb.sv'
SELF = 'tools/checkpoint_formats/tests/verify_physical_transport_restore.py'
SOURCES = (*RTL, TB, SPECIAL_TB, SELF, control.EXIT,
           'tools/checkpoint_formats/tests/verify_transport_control_state.py',
           'tools/checkpoint_formats/toolchain.py', 'tools/checkpoint_formats/codec.py')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows():
    return control.reconstruct({Path(n).name: (ROOT/n).read_text() for n in control.RTL}, 3)


def fixture():
    text = (ROOT/control.RTL[-1]).read_text()
    start = text.index('    input wire clock, reset,')
    ports = text[start:text.index('\n);', start)]
    ports = ports.replace('    input wire restore_hold, restore_load_pos, restore_load_neg,\n', '')
    ports = ports.replace('    input wire [GATES+480:0] restore_state,\n', '')
    require('restore_' not in ports, 'changed physical restore port declarations')
    ports = ports.replace('GATES+480', '483').replace('GATES-1', '2').replace('OWNERS-1', '3')
    names = []
    for line in re.sub(r'//[^\n]*', '', ports).splitlines():
        line = re.sub(r'^\s*(?:input|output) wire\s+(?:\[[^]]+\]\s*)?', '', line).strip().rstrip(',')
        if line:
            names.extend(n.strip() for n in line.split(','))
    ports += ''',
    input wire apply_valid, cut_valid, owners_quiescent, apply_owner_error,
    input wire [483:0] apply_state,
    input wire [63:0] apply_cycle, expected_cycle,
    output wire apply_ready, applied, busy,
    output wire [4:0] apply_error'''
    return ('module PhysicalRestoreSynthesisFixture(\n'+ports+');\n'
        '  wire restore_hold, restore_load_pos, restore_load_neg;\n'
        '  wire [483:0] restore_state;\n'
        '  CheckpointTransportPhysicalRestore #(.GATES(3)) supervisor(\n'
        '    .observed_state(control_state),.owner_error(apply_owner_error),.error(apply_error),.*);\n'
        '  CheckpointPhysicalCaptureTransport #(.GATES(3),.OWNERS(4),.ENTRIES(3),\n'
        '    .RESTORE_ENABLE(1),.EXTERNAL_CLOCK_NETWORK(1),.MANIFEST_SHA256(256\'h1234)) dut(\n'+
        ',\n'.join('    .'+n+'('+n+')' for n in names)+',\n'
        '    .restore_hold(restore_hold),.restore_load_pos(restore_load_pos),\n'
        '    .restore_load_neg(restore_load_neg),.restore_state(restore_state));\nendmodule\n')


def expected_fields():
    # Native fixture GATES=3 specializes only the unsupported-count fault away.
    # This supervisor bit is outside the physical restore vector; require its
    # explicit native constant binding instead of inventing retained storage.
    source=(ROOT/VERILOG/'CheckpointTransportPhysicalRestore.sv').read_text()
    require('assign fault_now[4] = apply_valid && (GATES < 1 || GATES > 65535);' in source and
        'error <= 0;' in source and 'error <= error | fault_now;' in source,
        'changed supervisor specialization constant contract')
    return [(r['relative_path'].replace('.', '/'), r['width'], r['clock'].startswith('negedge'), r['offset'])
            for r in rows()] + [('supervisor/'+n,w,n=='neg_done',-1) for n,w in
            [('state',3),('saved_state',484),('saved_cycle',64),('neg_done',1),('applied',1),('error',4)]]


def synthesis_tcl():
    fields = ' '.join('{'+f+' '+str(w)+' '+str(int(neg))+' '+str(offset)+'}'
                      for f,w,neg,offset in expected_fields())
    files = ' '.join('sources/'+Path(n).name for n in RTL[:-1])
    return '''set_param general.maxThreads 2
read_verilog -sv '''+files+''' fixture.sv
synth_design -top PhysicalRestoreSynthesisFixture -part xcvu47p-fsvh2892-2L-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw -period 7.142857 [get_ports clock]
set raw [get_nets -of_objects [get_ports clock]]
set fd [open native-storage.tsv w]
set classified {}
set falling 0
foreach row {'''+fields+'''} {
  lassign $row field width inverted offset
  set prefix $field
  if {![string match {supervisor/*} $field]} {set prefix dut/$field}
  set selected [get_cells -hier -filter "NAME =~ ${prefix}_reg* && REF_NAME =~ FD*"]
  if {[llength $selected] != $width} {error "changed field $field expected=$width actual=[llength $selected]"}
  foreach cell $selected {
    if {[lsearch -exact $classified $cell] >= 0} {error "duplicate sequential cell $cell"}
    set pin [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
    if {[llength $pin] != 1 || [get_property IS_INVERTED $pin] != $inverted ||
        [lsearch -exact [get_nets -segments -of_objects $pin] $raw] < 0} {error "wrong edge/clock $cell"}
    if {[get_property FSM_ENCODED_STATES $cell] ne ""} {error "unmapped encoded state $cell"}
    if {$inverted} {incr falling}
    set bit 0
    if {$width > 1 && ![regexp {\[([0-9]+)\]$} $cell unused bit]} {error "missing source bit $cell"}
    if {$offset >= 0} {
      set index [expr {$offset+$bit}]
      set port [get_ports [format {control_state[%d]} $index]]
      set q [get_pins -of_objects $cell -filter {REF_PIN_NAME == Q}]
      if {[llength $port] != 1 || [llength $q] != 1 ||
          [lsort [get_nets -segments -of_objects $port]] ne [lsort [get_nets -segments -of_objects $q]]} {error "physical readback Q mismatch $cell"}
    }
    if {$field eq "supervisor/error"} {
      set port [get_ports [format {apply_error[%d]} $bit]]
      set q [get_pins -of_objects $cell -filter {REF_PIN_NAME == Q}]
      if {[llength $port] != 1 || [llength $q] != 1 ||
          [lsort [get_nets -segments -of_objects $port]] ne [lsort [get_nets -segments -of_objects $q]]} {error "supervisor dynamic error Q mismatch $cell"}
    }
    puts $fd "$field\t$bit\t$cell\t[get_property REF_NAME $cell]\t$inverted"
    lappend classified $cell
  }
}
close $fd
# A legal fixed GATES=3 removes only supervisor/error[4]. Bind that absent
# source bit to the actual constant driver, separately from sequential census.
set constant_port [get_ports {apply_error[4]}]
set constant_nets [get_nets -segments -of_objects $constant_port]
set constant_driver [get_pins -leaf -of_objects $constant_nets -filter {DIRECTION == OUT}]
set constant_cell [get_cells -of_objects $constant_driver]
if {[llength $constant_port] != 1 || [llength $constant_driver] != 1 ||
    [llength $constant_cell] != 1 || [get_property REF_NAME $constant_cell] ne "GND" ||
    [get_property REF_PIN_NAME $constant_driver] ne "G"} {error "unbound supervisor specialization constant"}
set cf [open native-constants.tsv w]
puts $cf "supervisor/error\t4\tapply_error\[4\]\t0\tGND\t$constant_driver"
close $cf
set sequential [get_cells -hier -filter {IS_SEQUENTIAL == 1}]
set full [open all-native-storage.tsv w]
foreach cell [lsort $sequential] {puts $full "$cell\t[get_property REF_NAME $cell]"}
close $full
if {[lsort $sequential] ne [lsort $classified] || [llength $sequential] != 1041 || $falling != 2} {error "incomplete sequential census"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force physical-restore.dcp
write_verilog -force physical-restore-netlist.v
puts "PHYSICAL_RESTORE_SYNTH_PASS fields=30 registers=1041 falling=2"
'''


def audit_storage(directory):
    expected = {}
    for field,width,negative,_ in expected_fields():
        prefix = field if field.startswith('supervisor/') else 'dut/'+field
        for bit in range(width):
            cell = prefix+'_reg'+(f'[{bit}]' if width>1 else '')
            expected[cell] = (field,str(bit),str(int(negative)))
    actual = {}
    for line in (directory/'native-storage.tsv').read_text().splitlines():
        field,bit,cell,primitive,negative = line.split('\t')
        require(cell not in actual and primitive in ('FDRE','FDSE'), 'duplicate/unrepresented sequential primitive')
        actual[cell] = (field,bit,negative)
    require(actual == expected and len(actual)==1041, 'incomplete native source/edge census')
    complete={}
    for line in (directory/'all-native-storage.tsv').read_text().splitlines():
        cell,primitive=line.split('\t')
        require(cell not in complete and primitive in ('FDRE','FDSE'),'unrepresented native primitive '+line)
        complete[cell]=primitive
    require(set(complete)==set(expected),'native IS_SEQUENTIAL census differs from source fields')
    constants=[line.split('\t') for line in (directory/'native-constants.tsv').read_text().splitlines()]
    require(len(constants)==1 and constants[0][:5]==['supervisor/error','4','apply_error[4]','0','GND'] and
        len(constants[0])==6 and constants[0][5].endswith('/G'),
        'incorrect native supervisor specialization constant binding')
    return len(actual)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['vivado','vcs','audit'],required=True)
    for name in ('native','eda','out'):
        p.add_argument('--'+name,type=Path,required=name=='out')
    a=p.parse_args()
    require(a.out.resolve().is_relative_to(RUNS), 'evidence must remain below runs')
    a.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='physical-restore-'+a.mode+'-',dir=a.out.resolve()))
    sources={n:sha(ROOT/n) for n in SOURCES}
    summary=dict(status='pass',backend='eda' if a.mode=='vcs' else 'f2',sources=sources,
        scope='permanently parked physical restore component only',physical_fpga_capture=False,
        production_transport_owner=False,continuation_supported=False,
        observed_utc=datetime.now(timezone.utc).isoformat(),host=socket.gethostname(),original_root=str(ROOT))
    commands=[]
    def run(argv,name,expected=0,cwd=out):
        log=out/(name+'.log')
        row=dict(argv=list(map(str,argv)),cwd=str(cwd),log=str(log));commands.append(row)
        with log.open('w') as stream:
            result=subprocess.run(row['argv'],cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        row['returncode']=result.returncode
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        require(result.returncode==expected,'inspect '+str(log))
        return log.read_text()
    def validate(directory,backend):
        require(directory is not None,'missing '+backend+' evidence')
        doc=json.loads((directory/'summary.json').read_text())
        require(doc['status']=='pass' and doc['backend']==backend and doc['sources']==sources and
            not any(doc[n] for n in ('physical_fpga_capture','production_transport_owner','continuation_supported')),
            'stale or overstated evidence')
        for group in ('inputs','artifacts'):
            for name,digest in doc[group].items():
                require(sha(directory/name)==digest,'changed evidence '+name)
        if backend=='f2': audit_storage(directory)
        return doc
    if a.mode=='vivado':
        require(str(ROOT)=='/home/ubuntu/chia-cy-checkpoint-restore' and shutil.which('vivado'), 'native localhost Vivado required')
        (out/'sources').mkdir()
        for n in RTL: shutil.copyfile(ROOT/n,out/'sources'/Path(n).name)
        shutil.copyfile(ROOT/TB,out/'tb.sv');shutil.copyfile(ROOT/SPECIAL_TB,out/'special-tb.sv')
        shutil.copyfile(ROOT/control.EXIT,out/'exit.cc')
        (out/'fixture.sv').write_text(fixture());(out/'synth.tcl').write_text(synthesis_tcl())
        vendor=Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        summary['vendor_models']={}
        for name,path in [('BUFGCE.v',vendor/'unisims/BUFGCE.v'),('glbl.v',vendor/'glbl.v')]:
            shutil.copyfile(path,out/name)
            summary['vendor_models'][name]=dict(original_path=str(path),sha256=sha(path))
        summary['inputs']={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file()}
        log=run(['vivado','-mode','batch','-source','synth.tcl'],'synth')
        require('PHYSICAL_RESTORE_SYNTH_PASS fields=30 registers=1041 falling=2' in log and
            not re.search(r'ERROR:|CRITICAL WARNING:',log),'native physical restore synthesis failed')
        summary['registers']=audit_storage(out)
        summary['native_specialization']=dict(gates=3,physical_register_bits=484,
            retained_registers=1041,falling_edge_registers=2,dynamic_supervisor_error_bits=[0,1,2,3],
            constant_source_bit='supervisor/error[4]',constant_value=0,constant_driver='GND')
        census=(out/'native-storage.tsv').read_text()
        negative_results=[]
        for name,mutated in [('hidden-storage',census+'hidden\t0\thidden/extra_reg\tLDCE\t0\n'),
            ('omitted-storage','\n'.join(census.splitlines()[1:])+'\n'),
            ('wrong-edge',census.replace('\t0\n','\t1\n',1))]:
            case=out/('audit-negative-'+name);case.mkdir()
            (case/'native-storage.tsv').write_text(mutated)
            shutil.copyfile(out/'all-native-storage.tsv',case/'all-native-storage.tsv')
            shutil.copyfile(out/'native-constants.tsv',case/'native-constants.tsv')
            try: audit_storage(case)
            except ValueError as error: negative_results.append(dict(case=name,rejected=True,reason=str(error)))
            else: raise ValueError('native sequential audit accepted '+name)
        case=out/'audit-negative-wrong-constant';case.mkdir()
        for name in ('native-storage.tsv','all-native-storage.tsv'):
            shutil.copyfile(out/name,case/name)
        (case/'native-constants.tsv').write_text((out/'native-constants.tsv').read_text().replace('\t0\tGND\t','\t1\tGND\t'))
        try: audit_storage(case)
        except ValueError as error: negative_results.append(dict(case='wrong-constant',rejected=True,reason=str(error)))
        else: raise ValueError('native audit accepted wrong constant binding')
        (out/'audit-negatives.json').write_text(json.dumps(negative_results,indent=2)+'\n')
        summary['native_audit_corruptions_rejected']=len(negative_results)
        hidden=out/'synthesized-hidden-latch';hidden.mkdir();(hidden/'sources').mkdir()
        for n in RTL: shutil.copyfile(out/'sources'/Path(n).name,hidden/'sources'/Path(n).name)
        shutil.copyfile(out/'fixture.sv',hidden/'fixture.sv')
        mutant=hidden/'sources'/'CheckpointTransportPhysicalRestore.sv'
        source=mutant.read_text();marker='assign busy = state != IDLE;'
        require(source.count(marker)==1 and source.count('endmodule')==1,'hidden latch mutation boundary changed')
        mutant.write_text(source.replace(marker,'assign busy = (state != IDLE) ^ hidden;').replace('endmodule',
            'reg hidden;\n    always @* if(apply_valid) hidden = apply_state[0];\nendmodule'))
        (hidden/'synth.tcl').write_text(synthesis_tcl())
        log=run(['vivado','-mode','batch','-source','synth.tcl'],'synthesized-hidden-latch',expected=1,cwd=hidden)
        require('incomplete sequential census' in log and 'PHYSICAL_RESTORE_SYNTH_PASS' not in log,
            'native complete census failed to reject real synthesized hidden latch')
        hidden_census=[line.split('\t') for line in (hidden/'all-native-storage.tsv').read_text().splitlines()]
        require(len(hidden_census)==1042 and any(row[1]=='LDCE' for row in hidden_census),
            'hidden mutation did not retain a real additional synthesized latch')
        summary['native_hidden_storage_rejected']=True
        summary['artifacts']={n:sha(out/n) for n in ('native-storage.tsv','all-native-storage.tsv','native-constants.tsv','synth.log','commands.json',
            'physical-restore.dcp','physical-restore-netlist.v','utilization.rpt','timing.rpt','audit-negatives.json')}
        summary['artifacts'].update({str(f.relative_to(out)):sha(f) for f in hidden.rglob('*')
            if f.is_file() and f.suffix in ('.sv','.tcl','.tsv','.log')})
        summary['artifacts']['synthesized-hidden-latch.log']=sha(out/'synthesized-hidden-latch.log')
    elif a.mode=='vcs':
        require(str(ROOT)=='/scratch/jfx/chia-cy-checkpoint-restore' and os.environ.get('VCS_HOME')==toolchain.VCS_HOME,
            'EDA SP2 VCS environment required')
        native=validate(a.native,'f2')
        for name in native['inputs']:
            target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.native/name,target)
        common=[toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all']
        vendor=out/'BUFGCE.v'
        glbl=out/'glbl.v'
        results=[]
        for gates in (1,3,31,65):
            work=out/f'gates-{gates}';work.mkdir()
            compile_log=run([*common,'+define+PHYSICAL_RESTORE_GATES='+str(gates),'-top','physical_transport_restore_tb','-top','glbl',
                '-Mdir='+str(work/'csrc'),'-o',work/'simv',*[out/'sources'/Path(n).name for n in RTL],
                vendor,glbl,out/'tb.sv',out/'exit.cc'],'compile-'+work.name)
            require(not re.search(r'Warning-\[(?:PCWM|IPDW)',compile_log),'port/declaration mismatch')
            log=run([work/'simv','-no_save'],work.name,cwd=work)
            match=re.search(r'PHYSICAL_RESTORE_PASS gates=(\d+) bits=(\d+) restores=(\d+) rejections=(\d+) checks=(\d+) acks=(\d+) target_edges=(\d+)',log)
            require(match and tuple(map(int,[match[1],match[2],match[3],match[4],match[6],match[7]]))==
                (gates,481+gates,498+gates,34,498+gates,0),'incomplete physical restore coverage')
            results.append(dict(gates=gates,restores=int(match[3]),rejections=int(match[4]),checks=int(match[5]),target_edges=0))
        for gates in (0,65536):
            work=out/f'invalid-gates-{gates}';work.mkdir()
            run([*common,'+define+PHYSICAL_RESTORE_GATES='+str(gates),'-top','physical_transport_restore_specialization_tb',
                '-Mdir='+str(work/'csrc'),'-o',work/'simv',out/'sources'/'CheckpointTransportPhysicalRestore.sv',
                out/'special-tb.sv',out/'exit.cc'],'compile-'+work.name)
            log=run([work/'simv','-no_save'],work.name,cwd=work)
            require(f'PHYSICAL_RESTORE_SPECIALIZATION_REJECT gates={gates} acks=0 writes=0' in log,
                'invalid supervisor specialization not rejected')
        original=out/'sources'/'CheckpointPhysicalCaptureTransport.sv'
        text=original.read_text();marker='.restore_state(restore_state[410:0])'
        require(text.count(marker)==1,'physical semantic mutation boundary changed')
        corrupt=out/'corrupt.sv';corrupt.write_text(text.replace(marker,'.restore_state(restore_state[410:0] ^ 411\'h1)'))
        work=out/'semantic-corruption';work.mkdir()
        run([*common,'-top','physical_transport_restore_tb','-top','glbl','-Mdir='+str(work/'csrc'),'-o',work/'simv',
            *[out/'sources'/Path(n).name for n in RTL if Path(n).name!=original.name],corrupt,
            vendor,glbl,out/'tb.sv',out/'exit.cc'],'compile-corruption')
        log=run([work/'simv','-no_save'],'semantic-corruption',expected=1,cwd=work)
        require('PHYSICAL_RESTORE_DIVERGENCE cut=100 signal=physical readback bit=0 restores=0 acks=0 target_edges=0' in log,
            'semantic corruption did not stop at first divergent physical bit before acknowledgement')
        waves=list(out.rglob('*.vcd'))
        require(len(waves)==7 and all(re.search(r'^#[1-9][0-9]*$',f.read_text(),re.M) for f in waves),'missing full waves')
        summary.update(inputs=native['inputs'],results=results,semantic_corruption_rejected=True,
            debug_wave_count=7,native_receipt=str(a.native/'summary.json'))
        summary['artifacts']={str(f.relative_to(out)):sha(f) for f in out.rglob('*')
            if f.is_file() and f.suffix in ('.log','.vcd','.sv','.json')}
    else:
        native,eda=validate(a.native,'f2'),validate(a.eda,'eda')
        require(native['inputs']==eda['inputs'] and len(eda['results'])==4 and
            eda['debug_wave_count']==7 and eda['semantic_corruption_rejected'] and native['native_hidden_storage_rejected'],'incomplete cross-backend evidence')
        require((a.native/'fixture.sv').read_text()==fixture() and
            (a.native/'synth.tcl').read_text()==synthesis_tcl(),'changed native test contract')
        for n in RTL: require((a.native/'sources'/Path(n).name).read_bytes()==(ROOT/n).read_bytes(),'changed native source')
        summary.update(inputs={},artifacts={},matched_sources=len(sources),native_receipt=str(a.native/'summary.json'),
            eda_receipt=str(a.eda/'summary.json'))
    require(sources=={n:sha(ROOT/n) for n in SOURCES},'source changed during verification')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(out/'summary.json')


if __name__=='__main__': main()
