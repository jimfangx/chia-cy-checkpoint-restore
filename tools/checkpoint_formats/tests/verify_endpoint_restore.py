"""Native synthesis and EDA fresh-process checks of the real opt-in widget endpoint.

Fixture state covers the endpoint and explicitly modeled master/backend only.
It is not an FPGA image and supplies no production ownership/admission waiver.
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
from tools.checkpoint_formats.tests.audit_endpoint_restore_wave import audit

ROOT=Path(__file__).resolve().parents[3]
RUNS=ROOT/'automations/checkpoint_loop/runs'
TB='tools/checkpoint_formats/tests/checkpoint_endpoint_restore_tb.sv'
EXIT='tools/checkpoint_formats/tests/checkpoint_widget_exit.cc'
SOURCES=(TB,EXIT,'tools/checkpoint_formats/tests/verify_endpoint_restore.py',
    'tools/checkpoint_formats/tests/audit_endpoint_restore_wave.py',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointWidgetEndpoint.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointNastiState.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureWidget.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointLiveWidgetSnapshot.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/widgets/CheckpointCaptureEndpointSpec.scala')
TCL='''set_param general.maxThreads 4
foreach ident {4 12} {
create_project -in_memory -part xcvu47p-fsvh2892-2-e
read_verilog $ident/endpoint.v
synth_design -top CheckpointEndpointComponent -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
if {[llength [get_cells -hier -filter {REF_NAME =~ BUFG*}]] != 0} {error "unexpected clock gating"}
set raw [get_nets -of_objects [get_ports clock]]
set flops [get_cells -hier -filter {REF_NAME =~ FD*}]
if {[llength $flops] < 400} {error "missing original endpoint storage"}
foreach cell $flops {
  set pin [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]
  if {[llength $pin] != 1 || [get_property IS_INVERTED $pin] != 0 ||
      [lsearch -exact [get_nets -segments -of_objects $pin] $raw] < 0} {error "changed original clock $cell"}
}
report_utilization -file $ident/utilization.rpt
report_timing_summary -file $ident/timing.rpt
write_checkpoint -force $ident/endpoint.dcp
puts "ENDPOINT_RESTORE_SYNTH_PASS id=$ident flops=[llength $flops] raw_clock=1"
close_project
}
'''


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('vivado','vcs'),required=True)
    parser.add_argument('--generated',type=Path)
    parser.add_argument('--native',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    require(args.out.resolve().is_relative_to(RUNS),'evidence under runs required')
    args.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=args.mode+'-',dir=args.out.resolve()))
    sources={n:sha(ROOT/n) for n in SOURCES};commands=[]
    for name in SOURCES:
        dest=out/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    def run(argv,name,cwd,expected=0):
        row=dict(argv=list(map(str,argv)),cwd=str(cwd),log=str(cwd/(name+'.log')));commands.append(row)
        with Path(row['log']).open('w') as stream:r=subprocess.run(row['argv'],cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        row.update(returncode=r.returncode,log_sha256=sha(row['log']))
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        require(r.returncode==expected,'inspect underlying log '+row['log'])
        return Path(row['log']).read_text()
    summary=dict(status='running',backend='f2' if args.mode=='vivado' else 'eda',
        observed_utc=datetime.now(timezone.utc).isoformat(),hostname=socket.gethostname(),original_root=str(ROOT),sources=sources,
        scope='actual shared endpoint equations; fixture master/backend; no complete transport/stream/shadow ownership',
        physical_fpga_capture=False,production_restore_enabled=False,complete_state_ownership=False)
    if args.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),'native manager Vivado required')
        require(args.generated is not None and args.generated.resolve().is_relative_to(RUNS),'generated source below runs required')
        for ident in (4,12):
            (out/str(ident)).mkdir()
            shutil.copyfile(args.generated/f'endpoint-state/{ident}/restore/CheckpointEndpointComponent.v',out/str(ident)/'endpoint.v')
        (out/'synth.tcl').write_text(TCL)
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'synth',out)
        matches=re.findall(r'ENDPOINT_RESTORE_SYNTH_PASS id=(\d+) flops=(\d+) raw_clock=1',text)
        require(len(matches)==2 and [int(m[0]) for m in matches]==[4,12] and not re.search(r'ERROR:|CRITICAL WARNING:',text),'native endpoint synth failed')
        summary.update(registers={m[0]:int(m[1]) for m in matches},tool_version=run(['vivado','-version'],'version',out),
            inputs={n:sha(out/n) for n in ('4/endpoint.v','12/endpoint.v','synth.tcl')})
    else:
        require(shutil.which('vcs')==toolchain.VCS and os.environ.get('VCS_HOME')==toolchain.VCS_HOME,'EDA native SP2 required; source vcs-env.sh last')
        require(args.native is not None and args.native.resolve().is_relative_to(RUNS),'native receipt required')
        native=json.loads((args.native/'summary.json').read_text())
        require(native['status']=='pass' and native['sources']==sources and native['backend']=='f2' and
            native['physical_fpga_capture'] is False and native['production_restore_enabled'] is False,'stale or wrong scope native receipt')
        for group in ('inputs','artifacts'):
            for name,digest in native[group].items():require(sha(args.native/name)==digest,'changed native input/artifact '+name)
        for name,digest in sources.items():require(sha(args.native/'sources'/name)==digest,'changed native source '+name)
        require((args.native/'synth.tcl').read_text()==TCL,'changed native synthesis recipe')
        results=[];defects=[]
        for ident in (4,12):
            work=out/str(ident);work.mkdir()
            shutil.copyfile(args.native/str(ident)/'endpoint.v',work/'endpoint.v')
            common=[toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',f'+define+NASTI_ID_BITS={ident}','-top','checkpoint_endpoint_restore_tb']
            run([*common,'-Mdir=csrc','-o','simv',work/'endpoint.v',ROOT/TB,ROOT/EXIT],'compile',work)
            for cut in range(6):
                donor=work/f'cut-{cut}-donor';donor.mkdir();dest=work/f'cut-{cut}-restored';dest.mkdir();image=donor/'state.txt'
                coverage={};waves={}
                for name,directory,options in [('donor',donor,['+SAVE='+str(image)]),('restored',dest,['+IMAGE='+str(image)])]:
                    text=run([work/'simv','-no_save',f'+CUT={cut}','+TRACE='+str(directory/'trace.txt'),*options],'run',directory)
                    match=re.search(rf'ENDPOINT_RESTORE_PASS cut={cut} reads=(\d+) writes=(\d+) backend=(\d+) frames=(\d+) good_reads=(\d+) good_writes=(\d+) checks=(\d+)',text)
                    require(match and int(match[7])>2000,'incomplete endpoint continuation')
                    coverage[name]=list(map(int,match.groups()[:6]));waves[name]=audit(directory/'endpoint-restore.vcd',ident)
                require(coverage['donor']==coverage['restored'],'different restored endpoint obligations/coverage')
                reference=(donor/'trace.txt').read_text().splitlines();actual=(dest/'trace.txt').read_text().splitlines()
                require(len(reference)==len(actual)==2000,'incomplete endpoint traces')
                for cycle,(e,a) in enumerate(zip(reference,actual)):require(e==a,f'first endpoint divergence cut={cut} cycle={cycle}')
                results.append(dict(id_bits=ident,cut=cut,compared_cycles=2000,coverage=coverage,wave_audits=waves,image_sha256=sha(image),trace_sha256=sha(donor/'trace.txt')))
            bad=work/'semantic';bad.mkdir()
            text=run([work/'simv','-no_save','+CUT=2','+IMAGE='+str(work/'cut-2-donor/state.txt'),'+CORRUPT=semantic',
                '+TRACE='+str(bad/'trace.txt')],'run',bad,expected=1)
            require('ENDPOINT_RESTORE_DIVERGENCE fresh complete original-register zero-edge readback' in text and not(bad/'trace.txt').exists(),'semantic corruption released endpoint')
            # Compile one faulty original local-register restore mux. The
            # independent original-register oracle must stop before release.
            original=(work/'endpoint.v').read_text()
            site=re.compile(r'(localData <= )(data_\d+)(;[^\n]*CheckpointWidgetEndpoint.scala)')
            require(len(site.findall(original))==1,'ambiguous original local restore mux mutation')
            (work/'broken.v').write_text(site.sub(r"\1(\2 ^ 32'h1)\3",original))
            run([*common,'-Mdir=broken-csrc','-o','broken-simv',work/'broken.v',ROOT/TB,ROOT/EXIT],'broken-compile',work)
            bad=work/'broken';bad.mkdir()
            text=run([work/'broken-simv','-no_save','+CUT=2','+SAVE='+str(bad/'state.txt'),
                '+TRACE='+str(bad/'trace.txt')],'run',bad,expected=1)
            require('ENDPOINT_RESTORE_DIVERGENCE complete original-register canonical readback' in text and
                not(bad/'trace.txt').exists(),'compiled local restore defect escaped original-register oracle')
            broken_wave=audit(bad/'endpoint-restore.vcd',ident,broken=True)
            defects.append(dict(id_bits=ident,wave_audit=broken_wave))
        summary.update(tool=toolchain.VCS,native_receipt=str(args.native/'summary.json'),native_receipt_sha256=sha(args.native/'summary.json'),
            results=results,compiled_defects=defects,compared_cycles=24000,negative_processes=4)
    summary['artifacts']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.suffix in ('.v','.log','.rpt','.dcp','.vcd','.txt','.json')}
    require(all(sha(ROOT/n)==h for n,h in sources.items()),'source changed during execution')
    summary['status']='pass';(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(out/'summary.json')


if __name__=='__main__':main()
