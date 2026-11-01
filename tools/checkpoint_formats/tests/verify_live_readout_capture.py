"""Native synthesized local readout-owner capture and fresh EDA restore.

Directed component state is not a CPU checkpoint or evidence of FPGA capture.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import FormatError,require
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests import verify_live_readout_restore as retained
from tools.checkpoint_formats.tests.audit_live_readout_capture_wave import audit
from tools.checkpoint_formats.tests.audit_live_readout_restore_wave import audit as audit_restore
from tools.checkpoint_formats.tests import verify_live_readout_permission as permission

ROOT=retained.ROOT
SOURCES=retained.SOURCES+('tools/checkpoint_formats/tests/verify_live_readout_capture.py',
                        'tools/checkpoint_formats/tests/audit_live_readout_capture_wave.py',
                        permission.SELF, permission.TB)
sha=retained.sha


def wrapper():
    return retained.wrapper().replace('.RESTORE_ENABLE(1)', '.RESTORE_ENABLE(1),.CAPTURE_ENABLE(1)')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=('vivado','vcs'),required=True)
    ap.add_argument('--generated',type=Path)
    ap.add_argument('--native',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    require(args.out.resolve().is_relative_to(retained.RUNS),'evidence beneath runs required')
    args.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=args.mode+'-',dir=args.out.resolve()))
    sources={n:sha(ROOT/n) for n in SOURCES}
    doc=dict(status='running',backend='f2' if args.mode=='vivado' else 'eda',sources=sources,
        observed_utc=datetime.now(timezone.utc).isoformat(),source_root=str(ROOT),host=socket.gethostname(),
        scope='stateless local 69-bit readout-owner capture only; component donor',
        physical_fpga_capture=False,full_image=False,cpu_live_acceptance=False,
        complete_capture_owner=False,metasim_restore_supported=False,commands=[])
    def save(): (out/'summary.json').write_text(json.dumps(doc,indent=2)+'\n')
    def run(argv,name,expected=0):
        row=dict(argv=list(map(str,argv)),cwd=str(out),log=str(out/(name+'.log')))
        doc['commands'].append(row)
        with Path(row['log']).open('x') as f:r=subprocess.run(row['argv'],cwd=out,stdout=f,stderr=subprocess.STDOUT)
        row.update(returncode=r.returncode,log_sha256=sha(row['log']))
        if r.returncode!=expected:doc['status']='fail'
        save();require(r.returncode==expected,'inspect compiler/runtime log '+row['log'])
        return Path(row['log']).read_text()
    save();print(out,flush=True)
    if args.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),'native localhost only')
        require(args.generated is not None and args.native is None,'current emitted fixture required')
        for name in SOURCES:
            dest=out/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        shutil.copyfile(args.generated/'live-shell-bank-readout/banked-mapping.json',out/'permission-mapping.json')
        for suffix in ('','-restore'):
            shutil.copytree(args.generated/('live-shell-bank-readout-capture'+suffix),out/('generated'+suffix))
            binding=json.loads((out/('generated'+suffix)/'binding.json').read_text())
            require(binding['wired_sha256']==sha(out/('generated'+suffix)/'wired.fir') and
                binding['local_readout_capture_enabled'] and binding['readout_owner_bits']==69 and
                binding['local_readout_capture_words']==2 and binding['local_readout_capture_extra_storage_bits']==0 and
                binding['local_readout_restore_enabled']==bool(suffix) and
                binding['local_readout_capture_target_cycle_authority'] is False and
                binding['metasim_restore_supported'] is False,'changed source-bound capture scope')
        permission.geometry(out)
        (out/'wrapper.sv').write_text(wrapper())
        for top,tag,generated in [('LiveReadoutRestoreTop','unit','generated-restore'),
                                  ('LiveTop','generated','generated'),('LiveTop','paired','generated-restore')]:
            tcl='''set_param general.maxThreads 4
read_verilog -sv {sources/RTL sources/BANK sources/SNAPSHOT wrapper.sv GENERATED/wired.sv}
synth_design -top TOP -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none -keep_equivalent_registers
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set owner [get_cells -hier -filter {NAME =~ OWNER/* && IS_SEQUENTIAL == 1}]
if {[llength $owner] != 69} {error "incomplete capture owner or recursive extra storage"}
puts "LIVE_READOUT_CAPTURE_STORAGE bits=69 extra_bits=0"
report_utilization -file TAG-utilization.rpt
report_timing_summary -file TAG-timing.rpt
write_checkpoint -force TAG-capture.dcp
puts "LIVE_READOUT_CAPTURE_SYNTH_PASS"
'''.replace('RTL',retained.RTL).replace('BANK',retained.BANK).replace('SNAPSHOT',retained.SNAPSHOT).replace(
            'GENERATED',generated).replace('TOP',top).replace('OWNER','owner' if tag=='unit' else 'checkpoint_live_readout_adapter').replace('TAG',tag)
            (out/(tag+'.tcl')).write_text(tcl)
        doc['inputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='summary.json'}
        for tag in ('unit','generated','paired'):
            text=run(['vivado','-mode','batch','-source',tag+'.tcl'],tag+'-synth')
            require('LIVE_READOUT_CAPTURE_SYNTH_PASS' in text and not re.search(r'ERROR:|CRITICAL WARNING:',text),'native synthesis failed')
        doc.update(readout_register_bits=69,extra_capture_storage_bits=0)
    else:
        require(str(ROOT).startswith('/scratch/') and shutil.which('vcs')==toolchain.VCS and
                toolchain.VCS.endswith('Y-2026.03-SP2/bin/vcs'),'EDA native SP2 only')
        require(args.native is not None and args.generated is None,'source-bound native receipt required')
        receipt=local(ROOT,str(args.native));native=json.loads(receipt.read_text())
        require(native['status']=='pass' and native['backend']=='f2' and native['sources']==sources,'stale native receipt')
        for group in ('inputs','artifacts'):
            for name,digest in native[group].items():require(sha(receipt.parent/name)==digest,'changed native evidence '+name)
        for name in native['inputs']:
            dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(receipt.parent/name,dest)
        require((out/'wrapper.sv').read_text()==wrapper(),'changed source-bound wrapper')
        doc.update(inputs=native['inputs'],wave_audits=[],images=[])
        common=[toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all','+define+READOUT_CAPTURE']
        run(common+['-top','live_readout_generated_restore_tb','-Mdir='+str(out/'generated-csrc'),'-o',out/'generated-simv',
            out/'generated-restore/wired.sv',out/'sources'/retained.RTL,out/'sources'/retained.BANK,
            out/'sources'/retained.SNAPSHOT,out/'sources'/retained.GENERATED_TB,out/'sources'/retained.EXIT],'generated-compile')
        generated=run([out/'generated-simv','-no_save'],'generated-capture')
        require('GENERATED_READOUT_RESTORE_PASS loads=139 ' in generated and 'owner_bits=69 ack=0' in generated,
                'generated capture/restore incomplete')
        doc['generated_wave_audit']=audit(out/'generated-readout-restore.vcd',
            top='live_readout_generated_restore_tb.',owner='dut.checkpoint_live_readout_adapter.')
        doc['generated_fixture_loads']=139
        doc['occupied_staging_permission']=permission.verify(out,run,common,retained)
        unit=common+['-top','live_readout_restore_tb']
        run(unit+['+define+READOUT_BITS=557','+define+READOUT_CAPTURE_ONLY',
            '-Mdir='+str(out/'capture-only-csrc'),'-o',out/'capture-only-simv',out/'sources'/retained.RTL,
            out/'sources'/retained.BANK,out/'sources'/retained.TB,out/'sources'/retained.EXIT],'capture-only-compile')
        for cut in retained.CUTS:
            text=run([out/'capture-only-simv','-no_save','+MODE=donor','+CUT='+cut,
                '+IMAGE='+str(out/('capture-only-'+cut+'.hex'))],'capture-only-'+cut)
            require('READOUT_CAPTURE_PASS bits=557 cut='+cut+' ' in text,'capture incorrectly depends on restore opt-in')
            wave=out/('capture-only-'+cut+'.vcd');shutil.move(out/'live-readout-restore.vcd',wave)
            doc['wave_audits'].append(dict(path=str(wave),**audit(wave)))
        for bits in retained.GEOMETRIES:
            folder=out/f'unit-{bits}';folder.mkdir();simv=folder/'simv'
            run(unit+[f'+define+READOUT_BITS={bits}','-Mdir='+str(folder/'csrc'),'-o',simv,
                out/'sources'/retained.RTL,out/'sources'/retained.BANK,out/'sources'/retained.TB,out/'sources'/retained.EXIT],f'unit-{bits}-compile')
            for cut in retained.CUTS:
                image=folder/(cut+'.hex');argv=[simv,'-no_save','+CUT='+cut,'+IMAGE='+str(image)]
                text=run(argv+['+MODE=donor'],f'unit-{bits}-{cut}-capture')
                require(f'READOUT_CAPTURE_PASS bits={bits} cut={cut} ' in text,'hardware capture port not exercised')
                require(re.fullmatch('[0-9a-f]{18}\n',image.read_text()) is not None and int(image.read_text(),16)<1<<69,'bad capture bytes')
                wave=folder/(cut+'-capture.vcd');shutil.move(out/'live-readout-restore.vcd',wave)
                doc['wave_audits'].append(dict(path=str(wave),**audit(wave)))
                text=run(argv+['+MODE=restore'],f'unit-{bits}-{cut}-restore')
                require(f'READOUT_RESTORE_PASS bits={bits} cut={cut} ' in text and 'continuation=128 target_edges=0' in text,
                        'fresh captured-word continuation incomplete')
                wave=folder/(cut+'-restore.vcd');shutil.move(out/'live-readout-restore.vcd',wave)
                doc['wave_audits'].append(dict(path=str(wave),**audit_restore(wave)))
                doc['images'].append(dict(bits=bits,cut=cut,path=str(image),sha256=sha(image)))
            for case in ('permission','request','response','load','hold'):
                text=run([simv,'-no_save','+MODE=donor','+CUT=snapshot','+CASE='+case,
                    '+IMAGE='+str(folder/'never.hex')],f'unit-{bits}-unsafe-{case}')
                require(f'READOUT_CAPTURE_NEGATIVE_PASS bits={bits} ' in text and 'ack=0' in text,'unsafe capture admitted')
                require(not (folder/'never.hex').exists(),'unsafe capture published an image')
                wave=folder/('unsafe-'+case+'.vcd');shutil.move(out/'live-readout-restore.vcd',wave)
                doc['wave_audits'].append(dict(path=str(wave),**audit(wave)))
            text=run([simv,'-no_save','+MODE=restore','+CUT=snapshot','+CASE=bits',
                '+IMAGE='+str(folder/'snapshot.hex')],f'unit-{bits}-every-bit')
            require(f'READOUT_BITS_PASS bits={bits} owner_bits=69 loads=139 ' in text and 'ack=0' in text,'every-bit capture incomplete')
            wave=folder/'every-bit.vcd';shutil.move(out/'live-readout-restore.vcd',wave)
            doc['wave_audits'].append(dict(path=str(wave),**audit(wave)))
        source=(ROOT/retained.RTL).read_text();needle='capture_padded[capture_address * 64 +: 64]'
        require(source.count(needle)==1,'ambiguous synthesized capture mutation')
        (out/'corrupt-readout.sv').write_text(source.replace(needle,"(capture_padded[capture_address * 64 +: 64] ^ 64'b1)"))
        run(unit+['+define+READOUT_BITS=557','-Mdir='+str(out/'corrupt-csrc'),'-o',out/'corrupt-simv',
            out/'corrupt-readout.sv',out/'sources'/retained.BANK,out/'sources'/retained.TB,out/'sources'/retained.EXIT],'corrupt-compile')
        text=run([out/'corrupt-simv','-no_save','+MODE=donor','+CUT=snapshot','+IMAGE='+str(out/'never.hex')],
                 'corrupt-run',expected=1)
        require('signal=capture-complete-word-before-ack bits=557 cut=snapshot case=healthy ack=0 loads=0' in text,
                'corruption did not stop on first read word')
        require(not (out/'never.hex').exists(),'corrupt capture published bytes')
        shutil.move(out/'live-readout-restore.vcd',out/'corrupt.vcd')
        doc['compiled_corrupt_wave_audit']=audit(out/'corrupt.vcd',broken=True)
        mutations=[]
        for bit in range(69):
            try:audit(out/'unit-557/snapshot-capture.vcd',owner_bit=bit)
            except FormatError as error:mutations.append(dict(bit=bit,error=str(error)))
            else:raise FormatError('capture audit accepted omitted bit '+str(bit))
        doc.update(native_receipt=dict(path=str(receipt),sha256=sha(receipt)),geometries=list(retained.GEOMETRIES),
            capture_processes=18,capture_only_processes=6,fresh_restore_processes=18,unsafe_capture_processes=15,every_bit_processes=3,
            continuation_bank_transactions=18*128,raw_owner_bit_mutations=mutations,
            compiled_capture_corruption_rejected_before_ack=True)
    require(sources=={n:sha(ROOT/n) for n in SOURCES},'source changed during verification')
    doc.update(status='pass',artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*')
        if p.is_file() and p.suffix in {'.log','.rpt','.dcp','.vcd','.hex'}})
    save();print(out/'summary.json',flush=True)


if __name__=='__main__':main()
