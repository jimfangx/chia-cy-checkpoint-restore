"""Local native-synthesized routing/response restore; fresh VCS only on EDA.

Directed component donors are not FPGA-origin .fsckpt or .rtlckpt images.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import FormatError, require
from tools.checkpoint_formats.regression_runner import local
from tools.checkpoint_formats.tests.audit_live_readout_restore_wave import audit

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'automations/checkpoint_loop/runs'
BASE = 'sims/firesim/sim/midas/src/main/verilog/'
RTL = BASE + 'CheckpointLiveShellSnapshotReadout.sv'
BANK = BASE + 'CheckpointSnapshotStateBank.sv'
SNAPSHOT = BASE + 'CheckpointNativeStateSnapshot.sv'
TB = 'tools/checkpoint_formats/tests/live_readout_restore_tb.sv'
GENERATED_TB = 'tools/checkpoint_formats/tests/live_readout_generated_restore_tb.sv'
EXIT = 'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'
SOURCES = (RTL, BANK, SNAPSHOT, TB, GENERATED_TB, EXIT,
    'tools/checkpoint_formats/tests/verify_live_readout_restore.py',
    'tools/checkpoint_formats/tests/audit_live_readout_restore_wave.py',
    'tools/checkpoint_formats/toolchain.py', 'tools/checkpoint_formats/codec.py',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointLiveShellBankReadout.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointLiveShellSnapshotSpec.scala')
CUTS = ('empty', 'snapshot', 'original', 'released', 'error', 'fault')
NEGATIVES = ('permission', 'request', 'response', 'unheld', 'orphan', 'lost')
GEOMETRIES = (1, 65, 557)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wrapper():
    text = (ROOT / RTL).read_text().split(') (\n', 1)[1].split('\n);', 1)[0]
    text = re.sub(r'\bBITS\b', '557', text)
    return ('module LiveReadoutRestoreTop (\n' + text + '\n);\n'
            'CheckpointLiveShellSnapshotReadout #(.BITS(557),.SNAPSHOT_BANK(1),.RESTORE_ENABLE(1)) owner(.*);\nendmodule\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode', choices=('vivado', 'vcs'), required=True)
    ap.add_argument('--generated', type=Path)
    ap.add_argument('--native', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    require(args.out.resolve().is_relative_to(RUNS), 'evidence beneath runs required')
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=args.out.resolve()))
    sources = {n: sha(ROOT/n) for n in SOURCES}
    doc = dict(status='running', backend='f2' if args.mode == 'vivado' else 'eda', sources=sources,
        observed_utc=datetime.now(timezone.utc).isoformat(), source_root=str(ROOT), host=socket.gethostname(),
        scope='69-bit local routing and snapshot-response owner only; directed component donor',
        physical_fpga_capture=False, full_image=False, cpu_live_acceptance=False,
        complete_capture_owner=False, metasim_restore_supported=False, commands=[])
    def save(): (out/'summary.json').write_text(json.dumps(doc, indent=2)+'\n')
    def run(argv, name, expected=0):
        row=dict(argv=list(map(str,argv)), cwd=str(out), log=str(out/(name+'.log')))
        doc['commands'].append(row)
        with Path(row['log']).open('x') as f:
            result=subprocess.run(row['argv'],cwd=out,stdout=f,stderr=subprocess.STDOUT)
        row.update(returncode=result.returncode,log_sha256=sha(row['log']))
        if result.returncode != expected: doc['status']='fail'
        save(); require(result.returncode == expected,'inspect compiler/runtime log '+row['log'])
        return Path(row['log']).read_text()
    save();print(out,flush=True)
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'), 'native localhost only')
        require(args.generated is not None and args.native is None, 'current emitted fixture required')
        for name in SOURCES:
            dest=out/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        shutil.copytree(args.generated,out/'generated')
        binding=json.loads((out/'generated/binding.json').read_text())
        require(binding['wired_sha256']==sha(out/'generated/wired.fir') and
            binding['local_readout_restore_enabled'] and binding['readout_owner_bits']==69 and
            binding['original_and_staging_restore_supported'] is False and
            binding['metasim_restore_supported'] is False, 'changed source-bound local restore scope')
        require('parameter RESTORE_ENABLE = 1' in (out/'generated/wired.fir').read_text(), 'generated restore opt-in missing')
        (out/'wrapper.sv').write_text(wrapper())
        for top, tag in [('LiveReadoutRestoreTop','unit'),('LiveTop','generated')]:
            tcl='''set_param general.maxThreads 4
read_verilog -sv {sources/RTL sources/BANK sources/SNAPSHOT wrapper.sv generated/wired.sv}
synth_design -top TOP -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none -keep_equivalent_registers
create_clock -name raw_clock -period 7.142857 [get_ports clock]
set owner [get_cells -hier -filter {NAME =~ OWNER/* && IS_SEQUENTIAL == 1}]
if {[llength $owner] != 69} {error "incomplete 69-bit local readout restore owner"}
puts "LIVE_READOUT_RESTORE_STORAGE bits=69"
report_utilization -file TAG-utilization.rpt
report_timing_summary -file TAG-timing.rpt
write_checkpoint -force TAG-restore.dcp
puts "LIVE_READOUT_RESTORE_SYNTH_PASS"
'''.replace('RTL',RTL).replace('BANK',BANK).replace('SNAPSHOT',SNAPSHOT).replace('TOP',top).replace('OWNER','owner' if tag=='unit' else 'checkpoint_live_readout_adapter').replace('TAG',tag)
            (out/(tag+'.tcl')).write_text(tcl)
        doc['inputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='summary.json'}
        for tag in ('unit','generated'):
            text=run(['vivado','-mode','batch','-source',tag+'.tcl'],tag+'-synth')
            require('LIVE_READOUT_RESTORE_SYNTH_PASS' in text and not re.search(r'ERROR:|CRITICAL WARNING:',text),'native synth failed')
        doc['readout_register_bits']=69
    else:
        require(str(ROOT).startswith('/scratch/') and shutil.which('vcs')==toolchain.VCS and
            toolchain.VCS.endswith('Y-2026.03-SP2/bin/vcs'),'EDA native SP2 only')
        require(args.native is not None and args.generated is None,'source-bound native receipt required')
        receipt=local(ROOT,str(args.native));native=json.loads(receipt.read_text())
        require(native['status']=='pass' and native['backend']=='f2' and native['sources']==sources,'stale native receipt')
        for group in ('inputs','artifacts'):
            for name,digest in native[group].items():
                require(sha(receipt.parent/name)==digest,'changed native evidence '+name)
        for name in native['inputs']:
            dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(receipt.parent/name,dest)
        require((out/'wrapper.sv').read_text()==wrapper(),'changed source-bound wrapper')
        doc['inputs']=native['inputs'];doc['wave_audits']=[];doc['images']=[]
        run([toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
            '-top','live_readout_generated_restore_tb','-Mdir='+str(out/'generated-csrc'),'-o',out/'generated-simv',
            out/'generated/wired.sv',out/'sources'/RTL,out/'sources'/BANK,out/'sources'/SNAPSHOT,
            out/'sources'/GENERATED_TB,out/'sources'/EXIT],'generated-compile')
        generated=run([out/'generated-simv','-no_save'],'generated-restore')
        require('GENERATED_READOUT_RESTORE_PASS loads=139 ' in generated and 'owner_bits=69 ack=0' in generated,
                'actual generated restore ports do not restore the complete local owner')
        doc['generated_fixture_loads']=139
        doc['generated_wave_audit']=audit(out/'generated-readout-restore.vcd',
            top='live_readout_generated_restore_tb.',owner='dut.checkpoint_live_readout_adapter.')
        require(doc['generated_wave_audit']['accepted_loads']==139 and
            doc['generated_wave_audit']['acknowledgements']==0, 'generated original owner readback incomplete')
        common=[toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
                '-top','live_readout_restore_tb']
        for bits in GEOMETRIES:
            folder=out/f'unit-{bits}';folder.mkdir();simv=folder/'simv'
            run(common+[f'+define+READOUT_BITS={bits}','-Mdir='+str(folder/'csrc'),'-o',simv,
                out/'sources'/RTL,out/'sources'/BANK,out/'sources'/TB,out/'sources'/EXIT],f'unit-{bits}-compile')
            for cut in CUTS:
                image=folder/(cut+'.hex');argv=[simv,'-no_save','+CUT='+cut,'+IMAGE='+str(image)]
                text=run(argv+['+MODE=donor'],f'unit-{bits}-{cut}-donor')
                require(f'READOUT_DONOR_PASS bits={bits} cut={cut} ' in text,'donor did not finish')
                require(re.fullmatch('[0-9a-f]{18}\n',image.read_text()) is not None and
                    int(image.read_text(),16)<1<<69,'incomplete donor bytes')
                shutil.move(out/'live-readout-restore.vcd',folder/(cut+'-donor.vcd'))
                text=run(argv+['+MODE=restore'],f'unit-{bits}-{cut}-restore')
                require(f'READOUT_RESTORE_PASS bits={bits} cut={cut} ' in text and
                    'continuation=128 target_edges=0' in text,'fresh continuation incomplete')
                wave=folder/(cut+'-restore.vcd');shutil.move(out/'live-readout-restore.vcd',wave)
                audited=audit(wave)
                donor=int(image.read_text(),16)
                require(audited['accepted_loads']==1 and audited['acknowledgements']==
                    128+int(bool(donor & 1) and not bool(donor >> 68)), 'incomplete independently observed continuation')
                doc['wave_audits'].append(dict(path=str(wave),**audited))
                doc['images'].append(dict(bits=bits,cut=cut,path=str(image),sha256=sha(image)))
            for case in ('bits',*NEGATIVES):
                text=run([simv,'-no_save','+MODE=restore','+CUT=snapshot','+CASE='+case,
                    '+IMAGE='+str(folder/'snapshot.hex')],f'unit-{bits}-{case}')
                marker='READOUT_BITS_PASS' if case=='bits' else 'READOUT_NEGATIVE_PASS'
                require(f'{marker} bits={bits} ' in text and 'ack=0' in text,'unsafe or incomplete local restore')
                wave=folder/(case+'.vcd');shutil.move(out/'live-readout-restore.vcd',wave)
                audited=audit(wave)
                require(audited['acknowledgements']==0,'unsafe load acknowledged edge')
                if case=='bits': require(audited['accepted_loads']==139,'every-bit restore incomplete')
                doc['wave_audits'].append(dict(path=str(wave),**audited))
        # Mutate the actual compiled datapath; the donor file and independent
        # original-register oracle remain untouched. The first load must fail.
        text=(ROOT/BANK).read_text();needle='saved_data <= restore_state[63:0];'
        require(text.count(needle)==1,'ambiguous compiled mutation')
        (out/'corrupt-bank.sv').write_text(text.replace(needle,"saved_data <= restore_state[63:0] ^ 1'b1;"))
        run(common+['+define+READOUT_BITS=557','-Mdir='+str(out/'corrupt-csrc'),'-o',out/'corrupt-simv',
            out/'sources'/RTL,out/'corrupt-bank.sv',out/'sources'/TB,out/'sources'/EXIT],'corrupt-compile')
        text=run([out/'corrupt-simv','-no_save','+MODE=restore','+CUT=snapshot',
            '+IMAGE='+str(out/'unit-557/snapshot.hex')],'corrupt-run',expected=1)
        require('signal=complete-control-before-ack bits=557 cut=snapshot case=healthy ack=0 loads=1' in text,
                'semantic corruption escaped first complete readback')
        shutil.move(out/'live-readout-restore.vcd',out/'corrupt.vcd')
        doc['wave_audits'].append(dict(path=str(out/'corrupt.vcd'),**audit(out/'corrupt.vcd',broken=True)))
        mutations=[]
        for bit in range(69):
            try: audit(out/'unit-557/snapshot-restore.vcd',owner_bit=bit)
            except FormatError as error: mutations.append(dict(bit=bit,error=str(error)))
            else: raise FormatError('raw owner audit accepted omitted bit '+str(bit))
        doc.update(native_receipt=dict(path=str(receipt),sha256=sha(receipt)),geometries=list(GEOMETRIES),
            donor_processes=18,fresh_restore_processes=18,negative_processes=18,per_bit_processes=3,
            continuation_bank_transactions=18*128,compiled_semantic_fault_rejected_before_ack=True,
            raw_owner_bit_mutations=mutations)
    require(sources=={n:sha(ROOT/n) for n in SOURCES},'sources changed during verification')
    doc.update(status='pass',artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*')
        if p.is_file() and p.suffix in {'.log','.rpt','.dcp','.vcd','.hex'}})
    save();print(out/'summary.json',flush=True)


if __name__=='__main__':main()
