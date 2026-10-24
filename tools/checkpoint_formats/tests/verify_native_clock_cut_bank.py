"""Native bank plus physical clock-mask companion: localhost synthesis, EDA VCS.

Complete production capture, transport/host ownership and CPU migration remain unsupported.
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
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha, selectors, ORACLE
from tools.checkpoint_formats.tests.verify_native_descriptors import audit as audit_descriptors, SOURCES as DESCRIPTOR_SOURCES
from tools.checkpoint_formats.tests.audit_physical_clock_wiring import audit as audit_wiring

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
BASE = 'tools/checkpoint_formats/tests/'
RTL = 'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalClockCut.sv'
SOURCES = tuple(sorted(set(DESCRIPTOR_SOURCES + (
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutWiring.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeFunctionalBankSpec.scala',
    BASE+'audit_physical_clock_wiring.py', BASE+'native_clock_cut_bank_tb.sv',
    BASE+'native_clock_cut_fixture.sv', BASE+'verify_native_clock_cut_bank.py', RTL))))
PREFIX = 'FireSim-generated'
TCL = '''set_param general.maxThreads 4
read_verilog -sv generated/FireSim-generated.native-clock-cut.sv sources/CheckpointPhysicalClockCut.sv sources/native_clock_cut_fixture.sv
synth_design -top NativeClockCutFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 3} {error "expected original native gates plus one root mask gate"}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "wrong native gate semantics"}}
foreach name {network/checkpoint_physical_root_gate network/left_/gate network/right_/gate} {
  if {[llength [get_cells $name]] != 1} {error "lost native primitive $name"}
}
set fall [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]
if {[llength $fall] != 1} {error "expected one physical low-phase mask register"}
if {[llength [get_cells -hier -filter {NAME =~ *cut/internal_clock_network*}]] != 0} {error "duplicate gates"}
# Prove the response register clocks are the raw source, including when the
# generated functional network is physically stopped.
set raw_net [get_nets -of_objects [get_ports clock]]
foreach pattern {*ckpt_pending_reg *ckpt_saved_data_reg* *ckpt_saved_error_reg} {
  set cells [get_cells -hier -filter "NAME =~ $pattern"]
  if {[llength $cells] == 0} {error "missing bank endpoint $pattern"}
  foreach cell $cells {
    set pins [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
    # Hierarchy creates multiple segments of the same wire. Compare electrical
    # connectivity across those segments, rather than their local names.
    set segments [get_nets -segments -of_objects $pins]
    if {[lsearch -exact $segments $raw_net] < 0} {error "bank endpoint clock is masked: $cell"}
  }
}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force native-clock-cut.dcp
puts "NATIVE_CLOCK_CUT_SYNTH_PASS gates=3 falling_edge_registers=1"
'''


def audit(generated):
    generated = Path(generated)
    path = lambda suffix: generated/(PREFIX+suffix)
    composition = audit_descriptors(generated)
    result = audit_wiring(path('.native-functional-reference.fir'), path('.native-functional-simulator-state.json'),
        path('.native-functional-plan.json'), path('.native-clock-cut.fir'), path('.native-clock-cut.json'),
        path('.native-clock-cut.sv'), path('.native-clock-cut-emission.json'), native_generated=generated)
    result['functional_descriptors'] = composition['functional_entries']
    result['physical_ce_descriptors'] = composition['physical_clock_gates']
    return result


def audit_corruptions(generated, out):
    """Rehash changed FIRRTL and all outer bindings before structural rejection."""
    rejected = []
    for name in ('root-bypass','native-source-cascade','native-mask-bypass','endpoint-clock-masked',
                 'changed-functional-update','logical-ce-swap','claim-capture','claim-owner-closure'):
        altered = out/('negative-'+name)
        shutil.copytree(generated, altered)
        path = lambda suffix: altered/(PREFIX+suffix)
        wired = path('.native-clock-cut.fir')
        original = wired.read_text()
        text = original
        binding = json.loads(path('.native-clock-cut.json').read_text())
        if name=='root-bypass':
            text = text.replace('checkpoint_physical_root_gate.CE <= not(checkpoint_physical_mask)',
                'checkpoint_physical_root_gate.CE <= UInt<1>("h1")',1)
        elif name=='native-source-cascade':
            text = text.replace('.I <= checkpoint_physical_source_clock', '.I <= clock',1)
        elif name=='native-mask-bypass':
            text = text.replace('and(checkpoint_physical_ce_0, not(checkpoint_physical_mask))',
                'checkpoint_physical_ce_0',1)
        elif name=='endpoint-clock-masked':
            text = text.replace(', ckpt_clock with :', ', checkpoint_physical_root_gate.O with :',1)
        elif name=='changed-functional-update':
            text = text.replace('add(', 'sub(',1)
        elif name=='logical-ce-swap':
            binding['logical_ce_bit_order'].reverse()
        elif name=='claim-capture': binding['complete_fpga_capture']=True
        else: binding['production_freeze_owners_bound']=True
        require(text!=original or binding!=json.loads(path('.native-clock-cut.json').read_text()),
            'ineffective native clock-cut mutation '+name)
        wired.write_text(text)
        binding['wired_reference_sha256']=sha(wired)
        path('.native-clock-cut.json').write_text(json.dumps(binding))
        emission=json.loads(path('.native-clock-cut-emission.json').read_text())
        for suffix in ('.fir','.json'):
            emission['inputs']['.native-clock-cut'+suffix]=sha(path('.native-clock-cut'+suffix))
        path('.native-clock-cut-emission.json').write_text(json.dumps(emission))
        try: audit(altered)
        except ValueError as error: rejected.append(dict(name=name,error=str(error)))
        else: raise AssertionError('accepted coherently rehashed native clock-cut mutation '+name)
    return rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado','vcs','audit','production'), required=True)
    for name in ('generated','native','eda','out'):
        parser.add_argument('--'+name, type=Path, required=name=='out')
    args = parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), 'evidence below runs required')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=args.out.resolve()))
    sources = {n: sha(ROOT/n) for n in SOURCES}
    commands = []

    def run(argv, name, expected=0):
        row = dict(argv=list(map(str,argv)), cwd=str(out), log=str(out/(name+'.log')))
        commands.append(row)
        with Path(row['log']).open('w') as stream:
            proc = subprocess.run(row['argv'],cwd=out,stdout=stream,stderr=subprocess.STDOUT)
        row['returncode'] = proc.returncode
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        require(proc.returncode == expected, 'inspect underlying log '+row['log'])
        return Path(row['log']).read_text()

    def validate(path, backend):
        require(path is not None and path.resolve().is_relative_to(RUNS), 'receipt below runs required')
        doc = json.loads((path/'summary.json').read_text())
        require(doc['status']=='pass' and doc['backend']==backend and doc['sources']==sources and
            doc['physical_fpga_capture'] is False and doc['production_rocket_integrated'] is False,
            'stale or wrong-scope native clock-cut receipt')
        for group in ('inputs','artifacts'):
            for name, value in doc[group].items():
                require(sha(path/name)==value, 'changed native clock-cut evidence '+name)
        audit(path/'generated')
        binding=json.loads((path/'generated'/(PREFIX+'.native-functional-binding.json')).read_text())
        require((path/'synth.tcl').read_text()==TCL and
            (path/'native-selectors.svh').read_text()==selectors(binding), 'changed synthesis or independent word oracle')
        for name in SOURCES:
            require(sha(path/'sources'/Path(name).name)==sources[name], 'changed retained source snapshot '+name)
        for model in ('BUFGCE.v','glbl.v'):
            require(doc['vendor_models'][model]['sha256']==sha(path/model), 'changed native vendor model '+model)
        return doc

    summary = dict(status='pass',backend='eda' if args.mode=='vcs' else 'f2',
        observed_utc=datetime.now(timezone.utc).isoformat(),host=socket.gethostname(),original_root=str(ROOT),
        sources=sources,scope='native bank plus physical clock-mask companion; no production reset/transport/host admission',
        physical_fpga_capture=False,production_rocket_integrated=False)
    if args.mode=='production':
        require(args.generated is not None and args.generated.resolve().is_relative_to(RUNS), 'generated inputs below runs required')
        summary['audit'] = audit(args.generated)
        summary['inputs'] = {str(p):sha(p) for p in sorted(args.generated.glob(PREFIX+'*')) if p.is_file()}
        summary['artifacts'] = {}
    elif args.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native localhost required')
        require(args.generated is not None and args.generated.resolve().is_relative_to(RUNS), 'generated inputs below runs required')
        for source in [*args.generated.glob(PREFIX+'*'), args.generated/'NativeReference.sv']:
            if source.is_file():
                dest=out/'generated'/source.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        summary['audit'] = audit(out/'generated')
        summary['rejected_corruptions'] = audit_corruptions(out/'generated',out/'corruptions')
        binding=json.loads((out/'generated'/(PREFIX+'.native-functional-binding.json')).read_text())
        require({r['hierarchy']:(r['width'],r['depth']) for r in binding['state']} ==
            {name:(width,depth) for name,(width,depth,_) in ORACLE.items()}, 'independent fixture word inventory changed')
        (out/'native-selectors.svh').write_text(selectors(binding))
        (out/'synth.tcl').write_text(TCL)
        for name in SOURCES:
            dest=out/'sources'/Path(name).name
            require(not dest.exists(), 'source basename collision')
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        vendor=Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        summary['vendor_models']={}
        for name, source in [('BUFGCE.v',vendor/'unisims/BUFGCE.v'),('glbl.v',vendor/'glbl.v')]:
            shutil.copyfile(source,out/name)
            summary['vendor_models'][name]=dict(original_path=str(source),sha256=sha(source))
        summary['inputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'synth')
        require('NATIVE_CLOCK_CUT_SYNTH_PASS gates=3 falling_edge_registers=1' in text and
            not re.search(r'ERROR:|CRITICAL WARNING:',text), 'native clock-cut synthesis failed')
        names=('native-clock-cut.dcp','utilization.rpt','timing.rpt','synth.log','commands.json')
        summary['artifacts']={n:sha(out/n) for n in names}
    elif args.mode=='vcs':
        require(shutil.which('vcs')==toolchain.VCS and toolchain.VCS=='/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs', 'EDA native SP2 VCS required')
        native=validate(args.native,'f2')
        for name in native['inputs']:
            dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.native/name,dest)
        summary['inputs']=native['inputs']
        summary['vendor_models']=native['vendor_models']
        files=[out/'generated'/(PREFIX+'.native-clock-cut.sv'),out/'generated/NativeReference.sv',
            out/'sources/CheckpointPhysicalClockCut.sv',out/'sources/native_clock_cut_fixture.sv',
            out/'BUFGCE.v',out/'glbl.v',out/'sources/native_clock_cut_bank_tb.sv',out/'sources/checkpoint_widget_exit.cc']
        common=[toolchain.VCS,'-full64','-sverilog','-debug_access+all','-timescale=1ns/1ps','-Mupdate',
            '+incdir+'+str(out),'-top','native_clock_cut_bank_tb','-top','glbl']
        run([*common,'-Mdir=csrc','-o','simv',*files],'compile')
        text=run([out/'simv','-no_save'],'run')
        match=re.search(r'NATIVE_CLOCK_CUT_BANK_PASS checks=(\d+) cuts=4 words=128 stalls=(\d+) cycle=(\d+)',text)
        require(match and len(re.findall(r'NATIVE_CLOCK_CUT_WORD cut=',text))==128,'incomplete native clock-cut execution')
        shutil.move(out/'native-clock-cut.vcd',out/'healthy.vcd')
        bad=run([out/'simv','-no_save','+corrupt'],'semantic-negative',expected=1)
        require('reason=latched exact bank word/error' in bad,'semantic corruption escaped word oracle')
        shutil.move(out/'native-clock-cut.vcd',out/'semantic-negative.vcd')
        for fault in ('missing-owner','ce-drift'):
            text=run([out/'simv','-no_save','+'+fault],fault)
            require('NATIVE_CLOCK_CUT_REJECTED kind='+fault in text,'failed physical cut did not stay stopped')
            shutil.move(out/'native-clock-cut.vcd',out/(fault+'.vcd'))
        original=files[0].read_text()
        fault=original.replace('assign checkpoint_physical_root_gate_CE = ~checkpoint_physical_mask;',
            "assign checkpoint_physical_root_gate_CE = 1'b1;",1)
        require(fault!=original,'missing root mask mutation')
        (out/'fault.sv').write_text(fault)
        run([*common,'-Mdir=fault-csrc','-o','fault-simv',out/'fault.sv',*files[1:]],'fault-compile')
        # Freeze muxes retain functional storage; the physical CE/cycle audit
        # must also catch a bypass even when bank values happen to stay fixed.
        # The independent complete structural audit is the authority for this
        # coherent implementation fault; VCS checks the root clock directly.
        bad=run([out/'fault-simv','-no_save'],'wiring-negative',expected=1)
        require('reason=physical root clock stopped' in bad,'physical root bypass escaped public clock oracle')
        shutil.move(out/'native-clock-cut.vcd',out/'wiring-negative.vcd')
        for name in ('healthy','semantic-negative','missing-owner','ce-drift','wiring-negative'):
            wave=out/(name+'.vcd')
            require(wave.stat().st_size>2000 and re.search(r'#[1-9]\d*',wave.read_text()), 'empty debug wave')
        summary['checks'],summary['stalls'],summary['last_cycle']=map(int,match.groups())
        summary['artifacts']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()
            and (p.suffix in ('.log','.vcd','.sv') or p.name=='commands.json') and 'csrc' not in str(p)}
    else:
        native=validate(args.native,'f2');eda=validate(args.eda,'eda')
        require(native['inputs']==eda['inputs'],'native/EDA inputs differ')
        summary['matched_inputs']=len(native['inputs'])
        summary['checks']=eda['checks'];summary['last_cycle']=eda['last_cycle']
        summary['inputs']={};summary['artifacts']={}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(out/'summary.json')


if __name__=='__main__':
    main()
