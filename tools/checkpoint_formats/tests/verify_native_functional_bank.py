"""Native functional-bank companion: synthesize locally, verify public ports on EDA.

No physical CPU capture, production cut admission or metasim restore is claimed.
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
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.audit_physical_clock_dependencies import audit as audit_dependencies

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
SCALA = 'sims/firesim/sim/midas/src/main/scala/midas/'
SOURCES = tuple(SCALA+n for n in (
    'checkpoint/GeneratedStateBankAccess.scala', 'checkpoint/GeneratedStateBankAnnotations.scala',
    'checkpoint/GeneratedExternalOwners.scala', 'checkpoint/NativeFunctionalBankProbe.scala',
    'checkpoint/PhysicalClockGateContract.scala', 'checkpoint/PhysicalClockCutPlan.scala',
    'checkpoint/PhysicalClockCutDependencies.scala', 'stage/GoldenGateCli.scala',
    'stage/GoldenGateCompilerPhase.scala')) + (
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeFunctionalBankSpec.scala',
    'tools/checkpoint_formats/tests/native_functional_bank_tb.sv',
    'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',
    'tools/checkpoint_formats/tests/verify_native_functional_bank.py')
GENERATED = ('reference.fir', 'manifest.json', 'physical-clock-plan.json', 'physical-clock-dependencies.json',
    'functional-inventory.json', 'binding.json', 'instrumented.fir', 'instrumented.sv', 'reference.sv')
# Literal fixture oracle. Expected values are computed separately by the SV bench.
ORACLE = {
    'NativeStorage.cycles': (64, 1, 'expected_cycle'),
    'NativeStorage.left_.value': (65, 1, 'expected_left'),
    'NativeStorage.right_.value': (65, 1, 'expected_right'),
    'NativeStorage.ram': (130, 8, 'memory[at/3]'),
    'NativeStorage.ram_r_data': (130, 1, 'expected_read'),
}
FLAGS = {k: False for k in ('complete_fpga_capture', 'deployable_capture_image',
    'production_freeze_owners_bound', 'metasim_restore_supported')}
TCL = '''set_param general.maxThreads 4
read_verilog -sv generated/instrumented.sv
synth_design -top NativeStorage -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name functional_clock -period 7.142857 [get_ports clock]
create_clock -name access_clock -period 7.142857 [get_ports ckpt_clock]
set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 2} {error "native primitive count changed"}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "native primitive semantics changed"}}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force native-functional.dcp
puts "NATIVE_FUNCTIONAL_SYNTH_PASS gates=2"
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(doc):
    return hashlib.sha256(canonical(doc)).hexdigest()


def audit_generated(path):
    path = Path(path)
    read = lambda n: json.loads((path/n).read_text())
    audit_dependencies(path/'reference.fir', path/'manifest.json', path/'physical-clock-plan.json',
                       path/'physical-clock-dependencies.json')
    manifest, plan, inventory, binding = map(read, ('manifest.json', 'physical-clock-plan.json',
        'functional-inventory.json', 'binding.json'))
    expected = dict(manifest, manifest_type='fsckpt-native-functional-companion',
        state=[r for r in manifest['state'] if r['adapter'] != 'metasim-bufgce-v1'],
        complete_fpga_capture=False, deployable_capture_image=False)
    require(inventory == expected, 'native functional inventory changed, omitted state or admitted capture')
    require(binding['scope'] == 'native_functional_readout_companion_only' and
        all(binding.get(k) is v for k, v in FLAGS.items()), 'native functional admission flags changed')
    require(binding['reference_sha256'] == sha(path/'reference.fir') == inventory['reference_sha256']
        and binding['instrumented_sha256'] == sha(path/'instrumented.fir')
        and binding['manifest_sha256'] == digest(inventory), 'native reference or instrumented source hash changed')
    require(binding['protocol'] == 'latched-banked64-chunked-v2' and binding['access_version'] == 2
        and binding['access_clock'] == 'ckpt_clock'
        and binding['freeze_contract'] == 'externally_held_all_functional_owners_before_access_until_drain',
        'native access-clock/freeze contract changed')
    require(binding['native_clock_gate_paths'] == [g['hierarchy'] for g in plan['physical_gates']]
        and binding['functional_clock_domains'] == plan['clock_domains'], 'native clocks changed or omitted')
    rows = inventory['state']
    require({r['hierarchy'] for r in rows} == set(ORACLE) and len(rows) == len(binding['state']) == 5,
        'independent complete native functional inventory required')
    require([r['state_id'] for r in rows] == sorted(r['state_id'] for r in rows), 'unordered native identities')
    for index, (row, access) in enumerate(zip(rows, binding['state'])):
        width, depth, _ = ORACLE[row['hierarchy']]
        require((row['width'], row['depth']) == (width, depth), 'native state reshaped')
        require(all(row[k] == access[k] for k in ('hierarchy','state_id','width','depth')) and
            access['bank'] == 0 and access['slot'] == index and access['storage_hierarchy'] and
            access['chunks'] == (width+63)//64 and access['transfer_width'] == min(width,64) and
            access['transfer_depth'] == depth*((width+63)//64), 'native selectors/chunk mapping changed')
        require(row['state_id'] == digest(dict(namespace='generated-simulator-state-v1',
            hierarchy=row['hierarchy'], kind=row['kind'])), 'native identity changed')
    rtl = (path/'instrumented.sv').read_text()
    require(len(re.findall(r'\bBUFGCE gate \(', rtl)) == 2 and 'module BUFGCE' not in rtl
        and 'assign gate_I = clock;' in rtl and rtl.count('assign gate_CE = enable;') == 2,
        'native primitive was replaced or rewired')
    return binding


def selectors(binding):
    depths = []
    values = []
    for row in binding['state']:
        width, depth, expression = ORACLE[row['hierarchy']]
        depths.append(f"{row['slot']}: depth={depth*((width+63)//64)};")
        values.append(f"{row['slot']}: oracle=({expression}) >> ((at%{(width+63)//64})*64);")
    return ('function automatic integer depth(input integer slot); case(slot)\n'+'\n'.join(depths)+
        '\ndefault: depth=0; endcase endfunction\n'+
        'function automatic [63:0] oracle(input integer slot,input integer at); case(slot)\n'+
        '\n'.join(values)+'\ndefault: oracle=0; endcase endfunction\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('vivado','vcs','audit'), required=True)
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
        require(doc['status']=='pass' and doc['backend']==backend and doc['sources']==sources
            and doc['physical_fpga_capture'] is False, 'stale or wrong-scope native functional receipt')
        for group in ('inputs','artifacts'):
            for name, value in doc[group].items():
                require(sha(path/name)==value, 'changed native functional evidence '+name)
        audit_generated(path/'generated')
        return doc

    summary = dict(status='pass',backend='eda' if args.mode=='vcs' else 'f2',
        observed_utc=datetime.now(timezone.utc).isoformat(),host=socket.gethostname(),original_root=str(ROOT),
        sources=sources,scope='native functional-bank companion only; no connected physical cut/transport or CPU image',
        physical_fpga_capture=False,production_rocket_integrated=False)
    if args.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native localhost required')
        require(args.generated is not None and args.generated.resolve().is_relative_to(RUNS), 'generated inputs below runs required')
        for name in GENERATED:
            dest=out/'generated'/name;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(args.generated/name,dest)
        binding=audit_generated(out/'generated')
        (out/'native-selectors.svh').write_text(selectors(binding))
        (out/'synth.tcl').write_text(TCL)
        for name in SOURCES:
            dest=out/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        vendor=Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        summary['vendor_models']={}
        for name, source in [('BUFGCE.v',vendor/'unisims/BUFGCE.v'),('glbl.v',vendor/'glbl.v')]:
            shutil.copyfile(source,out/name)
            summary['vendor_models'][name]=dict(original_path=str(source),sha256=sha(source))
        summary['inputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'synth')
        require('NATIVE_FUNCTIONAL_SYNTH_PASS gates=2' in text and not re.search(r'ERROR:|CRITICAL WARNING:',text),
            'native functional synthesis failed')
        names=('native-functional.dcp','utilization.rpt','timing.rpt','synth.log','commands.json')
        summary['artifacts']={n:sha(out/n) for n in names}
    elif args.mode=='vcs':
        require(shutil.which('vcs')==toolchain.VCS and toolchain.VCS=='/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs',
            'EDA native SP2 VCS required')
        native=validate(args.native,'f2')
        for name in native['inputs']:
            dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.native/name,dest)
        for name,value in sources.items(): require(sha(ROOT/name)==value,'changed live source')
        summary['inputs']=native['inputs']
        files=[out/'generated/instrumented.sv',out/'generated/reference.sv',out/'BUFGCE.v',out/'glbl.v',
            out/'sources/tools/checkpoint_formats/tests/native_functional_bank_tb.sv',
            out/'sources/tools/checkpoint_formats/tests/checkpoint_widget_exit.cc']
        common=[toolchain.VCS,'-full64','-sverilog','-debug_access+all','-timescale=1ns/1ps','-Mupdate',
            '+incdir+'+str(out),'-top','native_functional_bank_tb','-top','glbl']
        run([*common,'-Mdir=csrc','-o','simv',*files],'compile')
        text=run([out/'simv','-no_save'],'run')
        match=re.search(r'NATIVE_FUNCTIONAL_BANK_PASS checks=(\d+) cuts=4 words=128 stalls=(\d+) cycle=(\d+)',text)
        require(match and len(re.findall(r'NATIVE_BANK_WORD cut=',text))==128,'incomplete native functional execution')
        shutil.move(out/'native-functional.vcd',out/'healthy.vcd')
        bad=run([out/'simv','-no_save','+corrupt'],'semantic-negative',expected=1)
        require('reason=latched exact bank word/error' in bad,'semantic corruption did not stop at first word')
        shutil.move(out/'native-functional.vcd',out/'semantic-negative.vcd')
        fault=(out/'generated/instrumented.sv').read_text().replace('assign gate_CE = enable;','assign gate_CE = ~enable;',1)
        require(fault!=(out/'generated/instrumented.sv').read_text(),'missing independent native wiring mutation')
        (out/'fault.sv').write_text(fault)
        run([*common,'-Mdir=fault-csrc','-o','fault-simv',out/'fault.sv',*files[1:]],'fault-compile')
        bad=run([out/'fault-simv','-no_save'],'wiring-negative',expected=1)
        require('NATIVE_FUNCTIONAL_DIVERGENCE reason=independent running/frozen counter arithmetic' in bad,
            'native CE wiring fault escaped arithmetic oracle')
        shutil.move(out/'native-functional.vcd',out/'wiring-negative.vcd')
        for name in ('healthy.vcd','semantic-negative.vcd','wiring-negative.vcd'):
            require((out/name).stat().st_size>2000 and re.search(r'#[1-9]\d*', (out/name).read_text()), 'empty debug wave')
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
