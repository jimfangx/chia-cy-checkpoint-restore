"""Synthesize in-place CE/functional routing locally; execute only on EDA SP2.

No complete FPGA image, checkpoint capture, or CPU migration is admitted here.
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
from tools.checkpoint_formats.tests.audit_native_inplace_access import audit, corruptions, PREFIX
from tools.checkpoint_formats.tests.verify_native_inplace import SOURCES as INPLACE_SOURCES
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha, selectors

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
SOURCES = tuple(sorted(set(INPLACE_SOURCES + (
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointInPlaceAccess.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointStateAccess.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointConstraints.scala',
    'tools/checkpoint_formats/tests/audit_native_inplace_access.py',
    'tools/checkpoint_formats/tests/audit_native_inplace_context.py',
    'tools/checkpoint_formats/tests/audit_native_constraints.py',
    'tools/checkpoint_formats/tests/verify_native_inplace_access.py',
    'tools/checkpoint_formats/tests/native_inplace_access_fixture.sv',
    'tools/checkpoint_formats/tests/native_inplace_access_tb.sv',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalStateRouter.sv'))))
ORACLE_BINDING_FILE = PREFIX+'.native-functional-binding.json'
REFERENCE_FILE = 'generated/NativeReference.sv'
TESTBENCH_FILE = 'sources/native_inplace_access_tb.sv'
FILES = ['generated/instrumented.sv', 'generated/'+PREFIX+'.native-inplace-access.sv',
         'generated/'+PREFIX+'.native-inplace-access-router.sv',
         'generated/'+PREFIX+'.native-inplace-access-ce.sv',
         'sources/CheckpointPhysicalClockCut.sv', 'sources/native_inplace_access_fixture.sv']
TCL = '''set_param general.maxThreads 4
read_verilog -sv '''+' '.join(FILES)+'''
read_xdc generated/FireSim-generated.native-state-access.synthesis.xdc
synth_design -top NativeInPlaceAccessFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
source generated/FireSim-generated.native-state-access.implementation.xdc
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 3} {error "duplicate or omitted functional execution/gates"}
foreach name {host/network/stage/network/checkpoint_physical_root_gate host/network/stage/network/left_/gate host/network/stage/network/right_/gate} {
  if {[llength [get_cells $name]] != 1} {error "existing instance path changed $name"}
}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "changed native gate semantics"}}
set raw [get_nets -of_objects [get_ports clock]]
set raw_registers 0
foreach pattern {host/network/host_ticks_reg* host/network/stage/control_ticks_reg* *ckpt_pending_reg *ckpt_saved_data_reg* *ckpt_saved_error_reg *router/pending_reg *router/selected_ce_reg *ce_endpoint/response_valid_reg *ce_endpoint/response_data_reg* *ce_endpoint/response_error_reg} {
  set cells [get_cells -hier -filter "NAME =~ $pattern && REF_NAME =~ FD*"]
  if {[llength $cells] == 0} {error "missing raw-clocked state $pattern"}
  foreach cell $cells {
    set pins [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
    if {[lsearch -exact [get_nets -segments -of_objects $pins] $raw] < 0} {error "masked parent/router/endpoint $cell"}
    incr raw_registers
  }
}
if {[llength [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]] != 1} {error "missing unique falling-edge mask"}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force native-inplace-access.dcp
puts "NATIVE_INPLACE_ACCESS_SYNTH_PASS raw_registers=$raw_registers gates=3"
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado','vcs','audit','structure'), required=True)
    for name in ('generated','native','eda','out'):
        parser.add_argument('--'+name, type=Path, required=name=='out')
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), 'evidence below runs required')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=args.out.resolve()))
    sources = {n:sha(ROOT/n) for n in SOURCES}
    commands = []

    def run(argv, name, expected=0):
        row = dict(argv=list(map(str,argv)), cwd=str(out), log=str(out/(name+'.log')))
        commands.append(row)
        with Path(row['log']).open('w') as stream:
            proc = subprocess.run(row['argv'], cwd=out, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = proc.returncode
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        require(proc.returncode == expected, 'inspect underlying log '+row['log'])
        return Path(row['log']).read_text()

    def validate(directory, backend):
        require(directory and directory.resolve().is_relative_to(RUNS), 'receipt below runs required')
        doc = json.loads((directory/'summary.json').read_text())
        require(doc['status']=='pass' and doc['backend']==backend and doc['sources']==sources and
                doc['physical_fpga_capture'] is False, 'stale or wrong-backend attachment receipt')
        for group in ('inputs','artifacts'):
            for name, digest in doc[group].items():
                require(sha(directory/name)==digest, 'changed attachment evidence '+name)
        audit(directory/'generated')
        require((directory/'synth.tcl').read_text()==TCL, 'changed synthesis scope')
        for name in SOURCES:
            require(sha(directory/'sources'/Path(name).name)==sources[name], 'changed retained source '+name)
        binding = json.loads((directory/'generated'/ORACLE_BINDING_FILE).read_text())
        require((directory/'native-selectors.svh').read_text()==selectors(binding), 'changed independent selector/oracle')
        for name in ('BUFGCE.v','glbl.v'):
            require(sha(directory/name)==doc['vendor_models'][name], 'changed original vendor model')
        return doc

    summary = dict(status='pass', backend='eda' if args.mode=='vcs' or str(ROOT).startswith('/scratch/') else 'f2',
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), original_root=str(ROOT),
        sources=sources, physical_fpga_capture=False, production_rocket_integrated=False,
        scope='in-place functional/physical readout routing only; no widget/complete-owner/restore admission')
    if args.mode=='structure':
        require(args.generated and args.generated.resolve().is_relative_to(RUNS), 'source below runs required')
        summary['audit'] = audit(args.generated)
        summary['inputs'] = {str(p):sha(p) for p in args.generated.rglob('*') if p.is_file()}
        summary['artifacts'] = {}
    elif args.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native localhost required')
        require(args.generated and args.generated.resolve().is_relative_to(RUNS), 'source below runs required')
        shutil.copytree(args.generated, out/'generated')
        summary['audit'] = audit(out/'generated')
        summary['rejected_corruptions'] = corruptions(out/'generated',out/'corruptions')
        for name in SOURCES:
            dest = out/'sources'/Path(name).name
            require(not dest.exists(),'source basename collision')
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,dest)
        vendor = Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        for name,source in (('BUFGCE.v',vendor/'unisims/BUFGCE.v'),('glbl.v',vendor/'glbl.v')):
            shutil.copyfile(source,out/name)
        binding = json.loads((out/'generated'/ORACLE_BINDING_FILE).read_text())
        (out/'native-selectors.svh').write_text(selectors(binding))
        (out/'synth.tcl').write_text(TCL)
        summary['inputs'] = {str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
        text = run(['vivado','-mode','batch','-source','synth.tcl'],'synth')
        match = re.search(r'NATIVE_INPLACE_ACCESS_SYNTH_PASS raw_registers=(\d+) gates=3',text)
        require(match and int(match[1])>=198 and not re.search(r'ERROR:|CRITICAL WARNING:',text), 'incomplete native synthesis')
        summary['raw_registers'] = int(match[1])
        summary['vendor_models'] = {n:sha(out/n) for n in ('BUFGCE.v','glbl.v')}
        summary['artifacts'] = {n:sha(out/n) for n in
            ('native-inplace-access.dcp','utilization.rpt','timing.rpt','synth.log','commands.json')}
    elif args.mode=='vcs':
        require(shutil.which('vcs')==toolchain.VCS and toolchain.VCS=='/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'EDA SP2 required')
        native = validate(args.native,'f2')
        for name in native['inputs']:
            dest = out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.native/name,dest)
        summary.update(inputs=native['inputs'],vendor_models=native['vendor_models'])
        files = FILES + [REFERENCE_FILE,'BUFGCE.v','glbl.v',
            TESTBENCH_FILE,'sources/checkpoint_widget_exit.cc']
        common = [toolchain.VCS,'-full64','-sverilog','-debug_access+all','-timescale=1ns/1ps','-Mupdate',
            '+incdir+'+str(out),'-top','native_inplace_access_tb','-top','glbl']
        run([*common,'-Mdir=csrc','-o','simv',*files],'compile')
        text = run([out/'simv','-no_save'],'run')
        match = re.search(r'NATIVE_INPLACE_ACCESS_BANK_PASS checks=(\d+) cuts=4 words=136 stalls=(\d+) cycle=(\d+)',text)
        require(match and len(re.findall(r'NATIVE_INPLACE_ACCESS_WORD cut=',text))==128, 'incomplete routing execution')
        summary['execution'] = dict(checks=int(match[1]),cuts=4,words=136,stalls=int(match[2]),last_cycle=int(match[3]))
        shutil.move(out/'native-inplace-access.vcd',out/'healthy.vcd')
        for fault,expected in (('corrupt',1),('missing-owner',0),('ce-drift',0)):
            text = run([out/'simv','-no_save','+'+fault],fault,expected)
            require(('reason=latched exact bank word/error' if fault=='corrupt' else
                'NATIVE_INPLACE_ACCESS_REJECTED kind='+fault) in text, 'wrong negative failure boundary')
            shutil.move(out/'native-inplace-access.vcd',out/(fault+'.vcd'))
        # Compile a genuine attachment error separately. The sampled CE differs
        # from the live/masked vector; the independent oracle must detect it.
        wrapper = out/FILES[1]
        original = wrapper.read_text()
        changed = original.replace('.captured_ce(capture_captured_ce)', '.captured_ce(~capture_captured_ce)',1)
        require(changed!=original,'ineffective CE connection fault')
        (out/'ce-fault.sv').write_text(changed)
        bad_files = [str(out/'ce-fault.sv') if f==FILES[1] else f for f in files]
        run([*common,'-Mdir=fault-csrc','-o','fault-simv',*bad_files],'ce-fault-compile')
        text = run([out/'fault-simv','-no_save'],'ce-fault',1)
        require('reason=latched exact bank word/error' in text and 'NATIVE_INPLACE_ACCESS_WORD' not in text,
                'CE semantic corruption escaped first physical read')
        shutil.move(out/'native-inplace-access.vcd',out/'ce-fault.vcd')
        waves = ['healthy','corrupt','missing-owner','ce-drift','ce-fault']
        for name in waves:
            require((out/(name+'.vcd')).stat().st_size>1000,'missing debug waveform '+name)
        summary['artifacts'] = {n:sha(out/n) for n in
            ('synth.tcl','commands.json','compile.log','run.log','corrupt.log','missing-owner.log','ce-drift.log',
             'ce-fault-compile.log','ce-fault.log',*(n+'.vcd' for n in waves))}
    else:
        native,eda = validate(args.native,'f2'),validate(args.eda,'eda')
        require(native['inputs']==eda['inputs'],'native/EDA input mismatch')
        summary['matched_inputs'] = len(native['inputs'])
        summary['matched_sources'] = len(sources)
        summary['execution'] = eda['execution']
        summary['native_receipt'] = str(args.native/'summary.json')
        summary['eda_receipt'] = str(args.eda/'summary.json')
        summary['inputs'],summary['artifacts'] = {},{}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(out/'summary.json')


if __name__=='__main__': main()
