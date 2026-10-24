"""Audit same-reference native descriptors, synthesize the widget, and check its ROM.

This companion proves no production freeze, restore support, or FPGA capture.
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
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.audit_native_functional_production import audit as audit_functional
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha, digest, FLAGS
from tools.checkpoint_formats.tests.verify_physical_descriptors import TCL

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
SCALA = 'sims/firesim/sim/midas/src/'
SOURCES = (
    SCALA+'main/scala/midas/widgets/CheckpointCaptureDescriptors.scala',
    SCALA+'main/scala/midas/widgets/CheckpointCaptureWidget.scala',
    SCALA+'main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
    SCALA+'main/scala/midas/checkpoint/NativeFunctionalBankProbe.scala',
    SCALA+'main/scala/midas/checkpoint/PhysicalClockStateBank.scala',
    SCALA+'main/scala/midas/checkpoint/PhysicalClockCutPlan.scala',
    SCALA+'main/scala/midas/checkpoint/PhysicalClockCutDependencies.scala',
    SCALA+'test/scala/midas/widgets/CheckpointNativeDescriptorsSpec.scala',
    SCALA+'test/resources/checkpoint/NativeStorage.firrtl',
    'tools/checkpoint_formats/tests/verify_native_descriptors.py',
    'tools/checkpoint_formats/tests/physical_descriptor_rom_tb.sv',
    'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',
    'tools/checkpoint_formats/tests/audit_native_functional_production.py',
    'tools/checkpoint_formats/tests/verify_native_functional_bank.py',
    'tools/checkpoint_formats/tests/verify_physical_descriptors.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_dependencies.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_plan.py',
)
PREFIX = 'FireSim-generated'
SUFFIXES = ('.native-descriptors.json', '.native-descriptors-binding.json',
    '.native-descriptors-physical-bank.json', '.native-descriptors-physical-bank.sv',
    '.native-descriptors-host.inc', '.native-descriptors-emission.json')
WIDGET_FILES = ('rom/NativeDescriptorROMProbe.v', 'constants.h', 'widget/CheckpointCaptureWidget.v',
    'widget/CheckpointCaptureTransport.sv', 'widget/CheckpointCaptureCut.sv',
    'widget/CheckpointPhysicalCaptureTransport.sv', 'widget/CheckpointPhysicalClockCut.sv')


def audit(generated, widget=False):
    """Reconstruct both domains from the complete native source, not composition rows."""
    generated = Path(generated)
    path = lambda suffix: generated/(PREFIX+suffix)
    read = lambda suffix: json.loads(path(suffix).read_text())
    functional = audit_functional(generated)
    manifest, bank = read('.native-functional-inventory.json'), read('.native-functional-binding.json')
    reference_hash = sha(path('.native-functional-reference.fir'))
    entries = []
    for index, (row, access) in enumerate(zip(manifest['state'], bank['state'])):
        # The native factory accepts the independently regenerated default banks.
        require(access['bank'] == index//65536 and access['slot'] == index%65536,
            'native default selector changed')
        entries.append(dict(state_id=row['state_id'], bank=access['bank'], slot=access['slot'],
            width=min(64, row['width']), depth=((row['width']+63)//64)*row['depth'], domain='functional'))
    rows = []
    for index, hierarchy in enumerate(functional['native_clock_gates']):
        logical = hierarchy+'.CE_latch'
        rows.append(dict(state_id=digest(dict(namespace='physical-bufgce-ce-latch-v1', hierarchy=logical)),
            hierarchy=logical, ce_bit=index, bank=255, slot=index, width=1, depth=1,
            metasim_output_state_id=digest(dict(namespace='generated-simulator-state-v1', hierarchy=hierarchy+'.O', kind='register')),
            restore_adapter='unsupported'))
    ce = dict(bank_version=1, scope='physical_ce_readout_companion_only', root_module=manifest['root_module'],
        endpoint_module=manifest['root_module']+'CheckpointPhysicalCEBank',
        reference_sha256=reference_hash,
        simulator_manifest_sha256=sha(path('.native-functional-simulator-state.json')),
        plan_sha256=sha(path('.native-functional-plan.json')),
        dependencies_sha256=sha(path('.native-functional-dependencies.json')),
        endpoint_sha256=sha(path('.native-descriptors-physical-bank.sv')),
        sample_contract='common_low_phase_unmasked_captured_ce_with_read_enable',
        access_clock='ungated_common_source', reset_contract='same_reset_as_sampler_transport_and_bank_endpoints',
        bank_reservation=255, state=rows, **FLAGS)
    require(read('.native-descriptors-physical-bank.json') == ce, 'native physical owners/endpoint binding changed')
    expected = dict(descriptor_version=1, scope='functional_and_physical_ce_descriptor_composition_only',
        functional_manifest_sha256=digest(manifest), functional_binding_sha256=digest(bank),
        physical_bank_binding_sha256=digest(ce), functional_entries=len(entries), physical_clock_gates=len(rows),
        state=entries+[dict(r, domain='physical_ce') for r in rows], same_reference_sha256=reference_hash, **FLAGS)
    require(read('.native-descriptors.json') == expected, 'native composition identities, shape, scope or same-reference binding changed')
    binding = dict(descriptor_binding_version=1, manifest_sha256=digest(expected),
        functional_manifest=manifest, functional_binding=bank, physical_bank_binding=ce,
        access_clock='ungated_common_source', reset_contract='same_reset_as_sampler_transport_and_bank_endpoints',
        same_reference_sha256=reference_hash, **FLAGS)
    require(read('.native-descriptors-binding.json') == binding, 'native composition source/coverage binding changed')
    cpp = 'checkpoint_capture_manifest_t{{{'+', '.join('0x'+digest(expected)[i:i+2] for i in range(62,-1,-2))+ \
        '}}, {'+', '.join('{%dU, %dU, %dU, %dU}' % tuple(r[k] for k in ('bank','slot','width','depth'))
        for r in expected['state'])+'}}'
    require(path('.native-descriptors-host.inc').read_text() == cpp, 'native host descriptor table changed')
    emission_inputs = {s: sha(path(s)) for s in SUFFIXES[:-1]+('.native-functional-emission.json',)}
    require(read('.native-descriptors-emission.json') == dict(binding_version=1,
        scope='same_reference_native_descriptor_companion_only', same_reference_sha256=reference_hash,
        inputs=emission_inputs, **FLAGS), 'native descriptor emission binding changed')
    if widget:
        header = (generated/'constants.h').read_text()
        for key,value in (('MANIFEST_SHA256',digest(expected)), ('DESCRIPTOR_BINDING_SHA256',digest(binding))):
            require(f'{key} "{value}"' in header, 'native widget driver digest mismatch '+key)
        for key,value in (('ENTRIES',len(expected['state'])), ('PHYSICAL_CLOCK_GATES',len(rows)),
            ('EXTERNAL_CLOCK_NETWORK',1), ('INTERNAL_DESCRIPTOR_ROM',1)):
            require(f'{key} {value}U' in header, 'native widget driver mode/count mismatch '+key)
        require(cpp in header and all('StateID: '+r['state_id'] in header for r in expected['state']),
            'native widget host identity/table mismatch')
        for name in WIDGET_FILES[-4:]:
            resource = Path(name).name
            require(sha(generated/name) == sha(ROOT/'sims/firesim/sim/midas/src/main/verilog'/resource)
                and resource+' SHA256: '+sha(generated/name) in header, 'stale native widget transport resource')
    return expected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('production','vivado','vcs','audit'), required=True)
    for name in ('generated','native','eda','out'):
        parser.add_argument('--'+name,type=Path,required=name=='out')
    args=parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS),'evidence below runs required')
    args.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=args.mode+'-',dir=args.out.resolve()))
    sources={n:sha(ROOT/n) for n in SOURCES}
    commands=[]

    def run(argv,name,expected=0,cwd=out):
        row=dict(argv=list(map(str,argv)),cwd=str(cwd),log=str(out/(name+'.log')))
        commands.append(row)
        with Path(row['log']).open('w') as stream:
            result=subprocess.run(row['argv'],cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        row['returncode']=result.returncode
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        require(result.returncode==expected,'inspect underlying log '+row['log'])
        return Path(row['log']).read_text()

    def validate(directory,backend):
        require(directory is not None and directory.resolve().is_relative_to(RUNS),'receipt below runs required')
        doc=json.loads((directory/'summary.json').read_text())
        require(doc['status']=='pass' and doc['backend']==backend and doc['sources']==sources
            and doc['physical_fpga_capture'] is False,'stale/wrong-scope native descriptor receipt')
        for group in ('inputs','artifacts'):
            for name,value in doc[group].items():
                require(sha(directory/name)==value,'changed native descriptor receipt '+name)
        audit(directory/'generated',widget=True)
        return doc

    summary=dict(status='pass',backend='eda' if args.mode=='vcs' or
        ROOT==Path('/scratch/jfx/chia-cy-checkpoint-restore') else 'f2',sources=sources,
        observed_utc=datetime.now(timezone.utc).isoformat(),host=socket.gethostname(),original_root=str(ROOT),
        scope='same-reference native descriptor companion only; no production cut/transport integration',
        physical_fpga_capture=False,production_rocket_integrated=False,metasim_restore_supported=False)
    if args.mode=='production':
        require(args.generated is not None and args.generated.resolve().is_relative_to(RUNS),'generated files below runs required')
        doc=audit(args.generated)
        summary['inputs']={str(p.resolve()):sha(p) for p in args.generated.glob(PREFIX+'.native-*') if p.is_file()}
        summary['artifacts']={}
    elif args.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),'native localhost required')
        require(args.generated is not None and args.generated.resolve().is_relative_to(RUNS),'generated files below runs required')
        names=[str(p.relative_to(args.generated)) for p in args.generated.glob(PREFIX+'.native-*')]+list(WIDGET_FILES)
        for name in names:
            dest=out/'generated'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.generated/name,dest)
        doc=audit(out/'generated',widget=True)
        for name in SOURCES:
            dest=out/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        (out/'synth.tcl').write_text(TCL)
        summary['inputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'synth')
        require('PHYSICAL_DESCRIPTOR_WIDGET_SYNTH_PASS immutable_rom=1 external_network=1' in text
            and not re.search(r'ERROR:|CRITICAL WARNING:',text),'native descriptor widget synthesis failed')
        summary['artifacts']={n:sha(out/n) for n in ('descriptor-widget.dcp','utilization.rpt','timing.rpt','synth.log','commands.json')}
    elif args.mode=='vcs':
        require(os.environ.get('VCS_HOME')==toolchain.VCS_HOME and Path(toolchain.VCS).is_file(),'EDA native VCS required')
        native=validate(args.native,'f2')
        for name in native['inputs']:
            dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.native/name,dest)
        doc=audit(out/'generated',widget=True)
        count=len(doc['state']);checks=9*count+18;first=doc['functional_entries']
        oracle=['localparam integer ENTRY_COUNT=%d;'%count,
            'integer banks[0:ENTRY_COUNT-1],slots[0:ENTRY_COUNT-1],widths[0:ENTRY_COUNT-1],depths[0:ENTRY_COUNT-1];','initial begin']
        for i,row in enumerate(doc['state']):
            oracle+=['%s[%d]=%d;'%(k,i,row[v]) for k,v in (('banks','bank'),('slots','slot'),('widths','width'),('depths','depth'))]
        (out/'descriptor_oracle.svh').write_text('\n'.join(oracle+['end'])+'\n')
        tb=out/'descriptor_tb.sv'
        tb.write_text((out/'sources/tools/checkpoint_formats/tests/physical_descriptor_rom_tb.sv').read_text()
            .replace('PhysicalDescriptorROMProbe dut','NativeDescriptorROMProbe dut'))
        def compile(rom,work,name):
            work.mkdir()
            run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
                '-top','physical_descriptor_rom_tb','+incdir+'+str(out),'-Mdir='+str(work/'csrc'),'-o',work/'simv',
                rom,tb,out/'sources/tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'],name,cwd=work)
        rom=out/'generated/rom/NativeDescriptorROMProbe.v'
        healthy=out/'healthy';compile(rom,healthy,'compile')
        text=run([healthy/'simv','-no_save'],'healthy',cwd=healthy)
        require(f'DESCRIPTOR_ROM_PASS checks={checks} entries={count}' in text,'incomplete native ROM execution')
        bad=out/'incorrect-rom.v'
        altered,n=re.subn(r'(assign io_slot = )([^;]+);',
            lambda m: f"{m[1]}({m[2]}) ^ (io_entry == 32'd{first} ? 16'h1 : 16'h0);",rom.read_text())
        require(n==1,'cannot construct independently compiled native slot fault')
        bad.write_text(altered)
        failure=out/'incorrect';compile(bad,failure,'incorrect-compile')
        text=run([failure/'simv','-no_save'],'incorrect',expected=1,cwd=failure)
        require(f'DESCRIPTOR_ROM_FAIL index={first} checks={2*first+1}' in text,'native slot fault failed to stop at first CE descriptor')
        for work in (healthy,failure):
            require(any(int(t)>0 for t in re.findall(r'^#(\d+)$',(work/'descriptor-rom.vcd').read_text(),re.M)),
                'missing full debug execution waveform')
        summary['inputs']=native['inputs'];summary['checks']=checks
        summary['artifacts']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and
            (p.suffix in ('.vcd','.log','.svh') or p.name=='commands.json' or p in (bad,tb))}
    else:
        native,eda=validate(args.native,'f2'),validate(args.eda,'eda')
        require(native['inputs']==eda['inputs'],'native/EDA generated bytes differ')
        doc=audit(args.native/'generated',widget=True)
        require(eda['checks']==9*len(doc['state'])+18,'incomplete EDA native descriptor checks')
        summary.update(matched_inputs=len(native['inputs']),matched_sources=len(sources),checks=eda['checks'],inputs={},artifacts={})
        negatives=[]
        for name,mutate in (
            ('missing-physical-owner',lambda d:d['state'].pop()),
            ('physical-slot-alias',lambda d:d['state'][-1].update(slot=0)),
            ('functional-bank-reservation',lambda d:d['state'][0].update(bank=255)),
            ('metasim-identity-alias',lambda d:d['state'][-1].update(state_id=d['state'][-1]['metasim_output_state_id'])),
            ('claimed-complete-ownership',lambda d:d.update(production_freeze_owners_bound=True)),
            ('different-source-circuit',lambda d:d.update(same_reference_sha256='0'*64)),
        ):
            directory=out/name;shutil.copytree(args.native/'generated',directory)
            p=lambda s:directory/(PREFIX+s)
            changed=json.loads(json.dumps(doc));mutate(changed)
            p('.native-descriptors.json').write_bytes(canonical(changed))
            binding=json.loads(p('.native-descriptors-binding.json').read_text())
            old=digest(binding);binding['manifest_sha256']=digest(changed)
            p('.native-descriptors-binding.json').write_bytes(canonical(binding))
            header=(directory/'constants.h').read_text().replace(digest(doc),digest(changed)).replace(old,digest(binding))
            (directory/'constants.h').write_text(header)
            emission=json.loads(p('.native-descriptors-emission.json').read_text())
            emission['inputs']={s:sha(p(s)) for s in emission['inputs']}
            p('.native-descriptors-emission.json').write_bytes(canonical(emission))
            try:
                audit(directory,widget=True)
            except (ValueError,AssertionError) as error:
                negatives.append(dict(name=name,error=str(error)))
            else:
                raise ValueError('accepted corrupt native composition '+name)
        summary['negative_cases']=negatives
    summary.update(functional_entries=doc['functional_entries'],physical_clock_gates=doc['physical_clock_gates'],
        descriptors=len(doc['state']),transfer_words=sum(r['depth'] for r in doc['state']),
        same_reference_sha256=doc['same_reference_sha256'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(out/'summary.json')


if __name__=='__main__':
    main()
