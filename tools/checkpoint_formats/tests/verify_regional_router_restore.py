"""Synthesize generated held-router restore locally and qualify fresh EDA processes."""
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
from tools.checkpoint_formats.tests.audit_regional_router_restore import audit, negatives, wave
from tools.checkpoint_formats.tests.verify_native_functional_bank import sha
from tools.checkpoint_formats.codec import require

ROOT=Path(__file__).resolve().parents[3]
RUNS=ROOT/'automations/checkpoint_loop/runs'
SOURCES=tuple(sorted({str(p.relative_to(ROOT)) for tree in (
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets') for p in (ROOT/tree).glob('*.scala')} | {
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointRegionsSpec.scala',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalClockCut.sv',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointRegionStateRouter.sv',
    'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalStateRouter.sv',
    'tools/checkpoint_formats/tests/audit_regional_router_restore.py',
    'tools/checkpoint_formats/tests/verify_regional_router_restore.py',
    'tools/checkpoint_formats/tests/audit_native_regions.py',
    'tools/checkpoint_formats/tests/audit_checkpoint_regions.py',
    'tools/checkpoint_formats/tests/audit_physical_clock_plan.py',
    'tools/checkpoint_formats/tests/audit_native_inplace_annotations.py',
    'tools/checkpoint_formats/tests/verify_native_functional_bank.py',
    'tools/checkpoint_formats/codec.py',
    'tools/checkpoint_formats/tests/native_regions_fixture.sv',
    'tools/checkpoint_formats/tests/regional_router_restore_tb.sv',
    'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc',
    'tools/checkpoint_formats/toolchain.py'}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',required=True,choices=('vivado','vcs'))
    p.add_argument('--compiler',type=Path)
    p.add_argument('--native',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    require(a.out.resolve().is_relative_to(RUNS),'all evidence beneath runs required')
    a.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=a.mode+'-',dir=a.out.resolve()))
    doc=dict(status='running',backend='f2' if a.mode=='vivado' else 'eda',source_root=str(ROOT),
        host=socket.gethostname(),observed_utc=datetime.now(timezone.utc).isoformat(),
        sources={n:sha(ROOT/n) for n in SOURCES},commands=[],cases=[],
        scope='generated router-only attachment; destination endpoints prepared independently, never full checkpoint migration',
        physical_fpga_capture=False,full_image=False,CPU_migration_verified=False)
    summary=out/'summary.json'
    def save():summary.write_text(json.dumps(doc,indent=2)+'\n')
    def run(argv,name,cwd=out,expected=0):
        log=out/(name+'.log');row=dict(argv=list(map(str,argv)),cwd=str(cwd),log=str(log))
        doc['commands'].append(row);save()
        with log.open('x') as f:r=subprocess.run(row['argv'],cwd=cwd,stdout=f,stderr=subprocess.STDOUT)
        row.update(returncode=r.returncode,log_sha256=sha(log));save()
        require(r.returncode==expected,'inspect underlying compiler/runtime log '+str(log))
        return log.read_text()
    def local(path):
        path=Path(path)
        for root in ('/home/ubuntu/chia-cy-checkpoint-restore','/scratch/jfx/chia-cy-checkpoint-restore'):
            if path.is_relative_to(root):return ROOT/path.relative_to(root)
        return path if path.is_absolute() else ROOT/path
    save();print(out,flush=True)
    try:
        if a.mode=='vivado':
            require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and a.compiler is not None and a.native is None,
                    'native manager and compiler receipt required')
            cp=local(a.compiler);compiler=json.loads(cp.read_text())
            require(compiler['status']=='pass' and compiler['backend']=='f2','successful compiler required')
            for n,h in compiler['sources'].items():require(sha(local(n))==h,'compiler source changed '+n)
            doc['compiler']={'path':str(cp),'sha256':sha(cp)}
            doc['sources'].update(compiler['sources'])
            vendor=Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
            for name,src in [('BUFGCE.v',vendor/'unisims/BUFGCE.v'),('glbl.v',vendor/'glbl.v')]:
                shutil.copyfile(src,out/name)
            for n in (1,2):
                work=out/f'regions-{n}';work.mkdir()
                source=cp.parent/f'generated/bank/native-regions-router-restore-{n}'
                for f in source.rglob('*'):
                    if f.is_file():require(compiler['artifacts'].get(str(f.relative_to(cp.parent)))==sha(f),'unbound compiler artifact')
                shutil.copytree(source,work/'generated')
                row=dict(regions=n,attachment=audit(work/'generated'),negative_audits=negatives(work/'generated',work/'negative-audits'))
                original=(ROOT/'tools/checkpoint_formats/tests/native_regions_fixture.sv').read_text()
                restore=f'''  input wire capture_router_restore_hold, capture_router_restore_load,
  input wire [{2+2*n}:0] capture_router_restore_state,
  output wire [{2+2*n}:0] capture_router_state,
  output wire capture_router_restore_ready, capture_router_restore_error,
'''
                original=original.replace('module NativeRegionsFixture(\n','module NativeRegionsFixture(\n'+restore)
                original=original.replace('[3:0] capture_logical_ce',f'[{2*n-1}:0] capture_logical_ce').replace('.GATES(4)',f'.GATES({2*n})')
                (work/'fixture.sv').write_text(original)
                shutil.copyfile(ROOT/'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalClockCut.sv',work/'cut.sv')
                files=['generated/grafted.sv']+[str(f.relative_to(work)) for f in sorted((work/'generated').glob('FireSim-generated*.sv'))]+['cut.sv','fixture.sv']
                (work/'files.json').write_text(json.dumps(files,indent=2)+'\n')
                # Apply the original emitted native clock/pin contracts with
                # the same explicit component placement conversion as retained tests.
                (work/'fixture.synthesis.xdc').write_bytes((work/'generated/instrumented.synthesis.xdc').read_bytes())
                (work/'fixture.implementation.xdc').write_text((work/'generated/instrumented.implementation.xdc').read_text().replace('shell/CL/','host/'))
                # For one region the only legal owner index is zero. Vivado
                # eliminates that FF; prove its exact observation bit has one
                # GND driver instead of silently dropping it from coverage.
                constant_audit = '' if n!=1 else '''
set owner_nets [get_nets -segments -of_objects [get_ports {capture_router_state[2]}]]
if {[llength $owner_nets] != 1 || [get_property TYPE $owner_nets] ne "GROUND"} {error "one-region owner is not proven zero"}
set owner_drivers [get_pins -leaf -of_objects $owner_nets -filter {DIRECTION == OUT}]
if {[llength $owner_drivers] != 1 || [get_property REF_NAME [get_cells -of_objects $owner_drivers]] ne "GND"} {error "one-region owner lacks exact GND driver"}
puts "REGIONAL_ROUTER_CONSTANT_PASS bit=2 value=0 driver=$owner_drivers"
'''
                raw_bits=4 if n==1 else 7
                tcl='set_param general.maxThreads 4\nread_verilog -sv '+' '.join(files)+f'''
read_xdc fixture.synthesis.xdc
synth_design -top NativeRegionsFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
source fixture.implementation.xdc
create_clock -period 7.142857 [get_ports clock]
write_checkpoint -force routers.dcp
set regs [get_cells -hier -filter {{NAME =~ */router/* && REF_NAME =~ FD*}}]
puts "REGIONAL_ROUTER_ORIGINAL_REGISTERS count=[llength $regs] cells=$regs"
if {{[llength $regs] != {raw_bits}}} {{error "generated router original register coverage changed"}}
{constant_audit}
set raw [get_nets -of_objects [get_ports clock]]
foreach cell $regs {{
  set pins [get_pins -of_objects $cell -filter {{REF_PIN_NAME == C}}]
  if {{[lsearch -exact [get_nets -segments -of_objects $pins] $raw] < 0}} {{error "router left raw clock"}}
}}
report_utilization -file utilization.rpt
puts "REGIONAL_ROUTER_RESTORE_SYNTH_PASS regions={n} original_router_bits={3+2*n} raw_registers={raw_bits} proven_zero_bits={1 if n==1 else 0}"
'''
                (work/'synth.tcl').write_text(tcl)
                text=run(['vivado','-mode','batch','-source','synth.tcl'],f'regions-{n}-synthesis',cwd=work)
                require('REGIONAL_ROUTER_RESTORE_SYNTH_PASS' in text and not re.search('ERROR:|CRITICAL WARNING:',text),'native synthesis failed')
                row.update(original_router_bits=3+2*n,raw_registers=raw_bits,proven_zero_bits=1 if n==1 else 0);doc['cases'].append(row);save()
        else:
            require(ROOT==Path('/scratch/jfx/chia-cy-checkpoint-restore') and a.native is not None and a.compiler is None and
                    toolchain.VCS=='/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs','EDA native SP2 and synthesized fixture required')
            native=local(a.native);receipt=json.loads(native.read_text())
            require(receipt['status']=='pass' and receipt['backend']=='f2','successful localhost synthesis required')
            for n,h in receipt['sources'].items():require(sha(ROOT/n)==h,'native source changed '+n)
            for n,h in receipt['artifacts'].items():require(sha(native.parent/n)==h,'native artifact changed '+n)
            doc['native']={'path':str(native),'sha256':sha(native)}
            for n in (1,2):
                work=out/f'regions-{n}';work.mkdir()
                original=native.parent/f'regions-{n}'
                # Preserve exact synthesized fixture and generated readout.
                for name in ['generated','fixture.sv','cut.sv','files.json']:
                    src=original/name
                    if src.is_dir():shutil.copytree(src,work/name)
                    else:shutil.copyfile(src,work/name)
                row=dict(regions=n,attachment=audit(work/'generated'),modes=[])
                manifest=json.loads((work/'generated/manifest.json').read_text())
                slots=[next(r['slot'] for r in manifest['state'] if r['domain']=='functional' and r['region']==i and r['hierarchy'].endswith('.cycles')) for i in range(n)]
                require(all(next(r['bank'] for r in manifest['state'] if r['domain']=='functional' and r['region']==i and r['hierarchy'].endswith('.cycles'))==i for i in range(n)),'fixture cycle bank changed')
                files=[work/f for f in json.loads((work/'files.json').read_text())]
                binary=work/'simv'
                text=run([toolchain.VCS,'-full64','-sverilog','-Mupdate','-debug_access+all','-timescale=1ns/1ps',
                    '-cc',toolchain.CC,'-cpp',toolchain.CXX,f'+define+REGIONS={n}',f'+define+CYCLE_SLOT0={slots[0]}',
                    f'+define+CYCLE_SLOT1={slots[-1]}','-top','regional_router_restore_tb','-top','glbl',
                    '-Mdir='+str(work/'csrc'),'-o',binary,*files,native.parent/'BUFGCE.v',native.parent/'glbl.v',
                    ROOT/'tools/checkpoint_formats/tests/regional_router_restore_tb.sv',ROOT/'tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'],
                    f'regions-{n}-compile',cwd=work)
                require('Error-[' not in text,'VCS compilation failed')
                modes=['source','destination']+([f'corrupt-{bit}' for bit in range(7)] if n==2 else [])
                image=work/'source/router.state'
                for mode in modes:
                    dest=work/mode;dest.mkdir();corrupt=mode.startswith('corrupt-')
                    argv=[binary,'-no_save','+mode='+('destination' if corrupt else mode),'+image='+str(image)]
                    if corrupt:argv+=['+corrupt_bit='+mode.split('-')[1]]
                    text=run(argv,f'regions-{n}-{mode}',cwd=dest,expected=1 if corrupt else 0)
                    values=[tuple(int(x,16) for x in line.split()) for line in image.read_text().splitlines()]
                    require(len(values)==4*n+3 and all(label==38 for _,label in values),'independent actual donor cycle/state count')
                    if corrupt:require('REGIONAL_ROUTER_FIRST_DIVERGENCE' in text and 'acknowledged_edges=0' in text,'missing first unacknowledged semantic divergence')
                    else:require('REGIONAL_ROUTER_RESTORE_PASS' in text,'missing healthy fresh process completion')
                    row['modes'].append(dict(mode=mode,returncode=1 if corrupt else 0,
                        wave=wave(dest/'regional-router-restore.vcd',n,values,destination=mode!='source',corrupt=corrupt)))
                    if mode=='destination':
                        rejected=[]
                        for bit in range(3+2*n):
                            try:wave(dest/'regional-router-restore.vcd',n,values,destination=True,mutate_bit=bit)
                            except ValueError:rejected.append(bit)
                            else:raise ValueError('wave checker admitted mutated router bit '+str(bit))
                        row['rejected_wave_checker_mutation_bits']=rejected
                row['source_image']=dict(path=str(image),sha256=sha(image),values=values)
                doc['cases'].append(row);save()
        require(all(sha(ROOT/n)==h for n,h in doc['sources'].items()),'qualification source changed')
        doc['status']='pass'
    except BaseException as e:
        doc.update(status='fail',error=str(e));raise
    finally:
        doc['finished_utc']=datetime.now(timezone.utc).isoformat()
        doc['artifacts']={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and not f.is_symlink() and f!=summary}
        save();print(summary,flush=True)


if __name__=='__main__':main()
