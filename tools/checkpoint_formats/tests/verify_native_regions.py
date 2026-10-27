"""Local native synthesis and EDA VCS for a shared multi-region native graft.

The receipt pins source, generated circuitry and vendor models. All functional
comparisons use public outputs and an independent memory/arithmetic oracle.
"""
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
from tools.checkpoint_formats.tests.audit_native_regions import audit
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha

ROOT=Path(__file__).resolve().parents[3]
RUNS=ROOT/'automations/checkpoint_loop/runs'
SOURCES=tuple('sims/firesim/sim/midas/src/main/scala/midas/checkpoint/'+n+'.scala' for n in (
    'NativeCheckpointInPlace','NativeCheckpointInPlaceContext','NativeCheckpointRegions','NativeCheckpointRegionGraft',
    'GeneratedStateBankAccess','PhysicalClockCutWiring','PhysicalClockStateBank','CheckpointRegionRouting','NativeCheckpointStateAccess'))+(
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureDescriptors.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointRegionsSpec.scala',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalClockCut.sv',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointRegionStateRouter.sv',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalStateRouter.sv',
    'tools/checkpoint_formats/tests/audit_native_regions.py',
    'tools/checkpoint_formats/tests/verify_native_regions.py',
    'tools/checkpoint_formats/tests/native_regions_fixture.sv',
    'tools/checkpoint_formats/tests/native_regions_tb.sv',
    'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc')

SOURCES=tuple(sorted(set(SOURCES) | {
    str(p.relative_to(ROOT)) for p in (ROOT/'sims/firesim/sim/midas/src/main/scala/midas/checkpoint').glob('*.scala')
} | {
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointInPlaceSpec.scala',
    'tools/checkpoint_formats/tests/audit_checkpoint_regions.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_plan.py',
    'tools/checkpoint_formats/tests/audit_native_inplace_annotations.py',
    'tools/checkpoint_formats/tests/verify_native_functional_bank.py',
    'tools/checkpoint_formats/codec.py', 'tools/checkpoint_formats/toolchain.py'
}))

def selectors(manifest):
    lines=['task descriptors;']
    for i,r in enumerate(manifest['state']):
        lines += [f'capture_descriptor_entry={i}; #1;',
            f'check(capture_descriptor_valid && capture_descriptor_bank=={r["bank"]} && capture_descriptor_slot=={r["slot"]} && '
            f'capture_descriptor_width=={r["width"]} && capture_descriptor_depth=={r["depth"]},"complete descriptor {i}");']
    lines += [f'capture_descriptor_entry={len(manifest["state"])}; #1; check(!capture_descriptor_valid,"descriptor bound");','endtask','task allwords;']
    for r in manifest['state']:
        if r['domain']=='physical_ce':
            values=[f'64\'(expected_ce[{r["slot"]}])']
        else:
            path=r['hierarchy'].split('.')[-1]
            other='other_' if r['region']==1 else ''
            if path=='cycles': values=['expected_cycle']
            elif path=='value':
                side='left' if '.left_.' in r['hierarchy'] else 'right'
                values=[f'64\'(expected_{other}{side} >> {64*i})' for i in range(r['depth'])]
            elif path=='ram_r_data': values=[f'64\'(expected_{other}read >> {64*i})' for i in range(r['depth'])]
            else:
                require(path=='ram','unknown oracle storage')
                values=[f'64\'({other}memory[{i//3}] >> {64*(i%3)})' for i in range(r['depth'])]
        lines += [f'readword({r["bank"]},{r["slot"]},{i},{value},0);' for i,value in enumerate(values)]
    return '\n'.join(lines+['endtask',''])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('vivado','vcs'),required=True)
    p.add_argument('--generated',type=Path);p.add_argument('--native',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();require(a.out.resolve().is_relative_to(RUNS),'evidence under runs required')
    a.out.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix=a.mode+'-',dir=a.out.resolve()))
    sources={n:sha(ROOT/n) for n in SOURCES};commands=[]
    def run(argv,name,expected=0):
        row=dict(argv=list(map(str,argv)),cwd=str(out),log=str(out/(name+'.log')));commands.append(row)
        with Path(row['log']).open('w') as f:r=subprocess.run(row['argv'],cwd=out,stdout=f,stderr=subprocess.STDOUT)
        row['returncode']=r.returncode;(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        require(r.returncode==expected,'inspect underlying compiler/runtime log '+row['log'])
        return Path(row['log']).read_text()
    doc=dict(status='running',backend='f2' if a.mode=='vivado' else 'eda',observed_utc=datetime.now(timezone.utc).isoformat(),
        host=socket.gethostname(),source_root=str(ROOT),sources=sources,physical_fpga_capture=False,
        scope='multi-region graft component only; production owners and full image remain incomplete')
    (out/'summary.json').write_text(json.dumps(doc,indent=2)+'\n')
    print(out,flush=True)
    if a.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),'native localhost Vivado required')
        require(a.generated is not None and a.native is None,'explicit generated input required')
        shutil.copytree(a.generated,out/'generated');doc['audit']=audit(out/'generated')
        for name in SOURCES:
            dest=out/'sources'/Path(name).name;require(not dest.exists(),'source basename collision')
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        vendor=Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        for name,path in [('BUFGCE.v',vendor/'unisims/BUFGCE.v'),('glbl.v',vendor/'glbl.v')]:shutil.copyfile(path,out/name)
        manifest=json.loads((out/'generated/manifest.json').read_text())
        require(len(manifest['state'])==14 and manifest['uncovered_physical_gates']==[],'wrong directed fixture')
        (out/'native-regions-selectors.svh').write_text(selectors(manifest))
        # The test emitter records the original shell placement. Bind the
        # explicit component-fixture placement conversion; preserve originals.
        (out/'fixture.synthesis.xdc').write_text((out/'generated/instrumented.synthesis.xdc').read_text())
        (out/'fixture.implementation.xdc').write_text((out/'generated/instrumented.implementation.xdc').read_text().replace('shell/CL/','host/'))
        files=['generated/grafted.sv']+[str(p.relative_to(out)) for p in sorted((out/'generated').glob('FireSim-generated*.sv'))]
        files += ['sources/CheckpointPhysicalClockCut.sv','sources/native_regions_fixture.sv']
        (out/'files.json').write_text(json.dumps(files,indent=2)+'\n')
        tcl='set_param general.maxThreads 4\nread_verilog -sv '+' '.join(files)+'''\nread_xdc fixture.synthesis.xdc
synth_design -top NativeRegionsFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
source fixture.implementation.xdc
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 6} {error "duplicate or omitted original execution/gates"}
foreach region {network peer} {
  foreach leaf {checkpoint_physical_root_gate left_/gate right_/gate} {
    if {[llength [get_cells host/stage/$region/$leaf]] != 1} {error "changed existing native clock path"}
  }
}
set raw [get_nets -of_objects [get_ports clock]]
set raw_registers 0
foreach pattern {host/host_ticks_reg* host/stage/control_ticks_reg* *ckpt_pending_reg *ckpt_saved_data_reg* *ckpt_saved_error_reg *router/pending_reg *router/selected_ce_reg *router/owner_reg* *ce_endpoint/response_valid_reg *ce_endpoint/response_data_reg* *ce_endpoint/response_error_reg} {
  set cells [get_cells -hier -filter "NAME =~ $pattern && REF_NAME =~ FD*"]
  if {[llength $cells] == 0} {error "missing raw-clock owner $pattern"}
  foreach cell $cells {
    set pins [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
    if {[lsearch -exact [get_nets -segments -of_objects $pins] $raw] < 0} {error "masked raw control/readout state $cell"}
    incr raw_registers
  }
}
if {[llength [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]] != 1} {error "missing common low-phase mask"}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "changed native gate contract"}}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force native-regions.dcp
puts "NATIVE_REGIONS_SYNTH_PASS raw_registers=$raw_registers gates=6"
'''
        (out/'synth.tcl').write_text(tcl)
        doc['inputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='summary.json'}
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'synth')
        match=re.search(r'NATIVE_REGIONS_SYNTH_PASS raw_registers=(\d+) gates=6',text)
        require(match and not re.search(r'ERROR:|CRITICAL WARNING:',text),'native synthesis did not preserve shared clock/ownership')
        doc['raw_registers']=int(match[1]);doc['vendor_models']={n:sha(out/n) for n in ('BUFGCE.v','glbl.v')}
        doc['artifacts']={n:sha(out/n) for n in ('native-regions.dcp','synth.log','utilization.rpt','timing.rpt','commands.json')}
    else:
        require(str(ROOT).startswith('/scratch/') and toolchain.VCS=='/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs','EDA SP2 only')
        require(a.native is not None and a.generated is None,'explicit native receipt required')
        native=json.loads((a.native/'summary.json').read_text())
        require(native['status']=='pass' and native['backend']=='f2' and native['sources']==sources,'stale native source pins')
        for group in ('inputs','artifacts'):
            for name,value in native[group].items():require(sha(a.native/name)==value,'changed native input/artifact '+name)
        for name in native['inputs']:
            dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.native/name,dest)
        doc['audit']=audit(out/'generated');doc['native_receipt_sha256']=sha(a.native/'summary.json')
        files=json.loads((out/'files.json').read_text())+['BUFGCE.v','glbl.v','sources/native_regions_tb.sv','sources/checkpoint_widget_exit.cc']
        common=[toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
            '+incdir+'+str(out),'-top','native_regions_tb','-top','glbl']
        compiled=run([*common,'-Mdir=csrc','-o','simv',*files],'compile')
        require('Warning-[IPDASP]' not in compiled,'emitted ANSI-port/wire collision; inspect compile.log')
        text=run([out/'simv','-no_save'],'healthy')
        require(re.search(r'NATIVE_REGIONS_PASS checks=\d+ cuts=4 words=280 stalls=840 target_cycle=\d+',text),'incomplete four-cut execution')
        doc['execution']=re.search(r'NATIVE_REGIONS_PASS .*',text)[0]
        shutil.move(out/'native-regions.vcd',out/'healthy.vcd')
        for fault in ('missing-owner','ce-drift'):
            text=run([out/'simv','-no_save','+'+fault],fault)
            require(re.search(r'NATIVE_REGIONS_REJECTED kind=\s*'+re.escape(fault)+r'\s*$',text,re.M),'wrong rejection boundary')
            shutil.move(out/'native-regions.vcd',out/(fault+'.vcd'))
        # Real compiled payload defect: region 1 receives region 0 CE samples.
        path=out/'generated/FireSim-generated.native-region-graft.sv'
        good=path.read_text();bad=good.replace('.capture_captured_ce(capture_captured_ce[2 +: 2])',
            '.capture_captured_ce(capture_captured_ce[0 +: 2])')
        require(bad!=good,'fault must change compiled CE connection')
        fault=out/'wrong-ce.sv';fault.write_text(bad)
        faultfiles=[str(fault) if f==str(path.relative_to(out)) else f for f in files]
        run([*common,'-Mdir=fault-csrc','-o','fault-simv',*faultfiles],'fault-compile')
        text=run([out/'fault-simv','-no_save'],'wrong-ce',1)
        require('reason=exact selected regional word/error' in text and 'response_ack=0' in text,'fault acknowledged or failed at wrong boundary')
        shutil.move(out/'native-regions.vcd',out/'wrong-ce.vcd')
        doc['inputs']=native['inputs']
        doc['artifacts']={str(p.relative_to(out)):sha(p) for p in out.iterdir() if p.is_file() and p.name not in ('summary.json',) and p.suffix in ('.vcd','.log','.sv','.json')}
    require(sources=={n:sha(ROOT/n) for n in SOURCES},'source epoch changed during verification')
    doc['status']='pass';(out/'summary.json').write_text(json.dumps(doc,indent=2)+'\n');print(out/'summary.json')

if __name__=='__main__': main()
