"""Exercise the real registered widget joined to its existing simulator wrapper.

Native synthesis runs on the manager; VCS execution runs only on EDA SP2.
The sentinel image identity and missing external-state adapter remain unsupported.
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
from tools.checkpoint_formats.fpga_transport import crc32c, field
from tools.checkpoint_formats.tests.verify_native_checkpoint_top import STUB

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT/'automations/checkpoint_loop/runs'
TESTS = 'tools/checkpoint_formats/tests/'
RTL = ('CheckpointPhysicalCaptureTransport.sv', 'CheckpointPhysicalClockCut.sv',
       'CheckpointCaptureTransport.sv', 'CheckpointCaptureCut.sv')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_files():
    """Pin compiler sources as well as the independent auditor and executable bench."""
    scala = ROOT/'sims/firesim/sim/midas/src'
    files = set((scala/'main/scala').rglob('*.scala'))
    files.update((scala/'test/scala/midas/core').glob('*Checkpoint*.scala'))
    files.update((scala/'test/scala/midas/checkpoint').glob('NativeCheckpointWidget*.scala'))
    files.add(scala/'test/scala/midas/checkpoint/NativeCheckpointInPlaceSpec.scala')
    files.add(scala/'test/resources/checkpoint/NativeStorage.firrtl')
    files.update((ROOT/'tools/checkpoint_formats').rglob('*.py'))
    files.update(ROOT/TESTS/n for n in ('verify_widget_graft.py', 'widget_graft_tb.sv',
                 'audit_widget_graft.py', 'checkpoint_generated_network_exit.cc', 'widget_identity_host.cc'))
    for folder in ('core','bridges'):
        files.update((ROOT/'sims/firesim/sim/midas/src/main/cc'/folder).glob('*.h'))
    files.add(ROOT/'sims/firesim/sim/midas/src/main/cc/core/checkpoint_capture.cc')
    files.update(ROOT/'sims/firesim/sim/midas/src/main/verilog'/n for n in RTL)
    files.add(ROOT/'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalStateRouter.sv')
    files.update([scala/'main/scala/midas/core/FPGATop.scala',
                  scala/'main/scala/midas/widgets/CheckpointCaptureWidget.scala',
                  scala/'main/scala/midas/stage/GoldenGateCompilerPhase.scala'])
    return tuple(sorted(str(p.relative_to(ROOT)) for p in files))


def header_parameters(directory):
    annotations = json.loads((directory/'before-reserved-annotations.json').read_text())
    headers = [a['body'] for a in annotations
               if a['class']=='midas.stage.GoldenGateOutputFileAnnotation' and a['fileSuffix']=='.const.h']
    require(len(headers)==1, 'one real registered-widget header required')
    header=headers[0]
    match=re.search(r'// CHECKPOINT_WIDGET_RESERVATION_BEGIN base=(\d+) stream=(\d+)\n#error Unbound_checkpoint_widget_reservation',header)
    require(match and match[2]=='1', 'sentinel reservation header guard missing')
    streams=re.findall(r'CPUManagedStreams::StreamParameters\(\s*std::string\(R"ESC\((.*?)\)ESC"\),\s*(\d+)ULL,\s*(\d+)ULL,\s*(\d+),\s*(\d+)',header)
    require(len(streams)==2 and streams[1][3:]==('2','64'), 'real stream allocation changed')
    return dict(capture_base=int(match[1]),capture_dma=int(streams[1][1]),stream_count=int(streams[1][2]),
                baseline_dma=int(streams[0][1]),baseline_count=int(streams[0][2]))


def verilog_files(directory):
    names=['connected.sv']
    for suffix in ('.native-inplace-graft.sv','.native-inplace-graft-router.sv','.native-inplace-graft-ce.sv'):
        matches=list(directory.glob('*'+suffix));require(len(matches)==1,'one emitted graft resource '+suffix)
        names.append(matches[0].name)
    return ['generated/'+n for n in names]+['sources/'+n for n in RTL]+['target-clock-sink.sv']


def port_header(directory):
    text=(directory/'connected.sv').read_text()
    top=re.search(r'module FPGATop\((.*?)\);',text,re.S)
    require(top, 'real FPGATop missing')
    ports=re.findall(r'(input|output)\s*(\[\d+:\d+\])?\s*(\w+)',re.sub(r'//[^\n]*','',top[1]))
    require(len(ports)>30 and len({p[2] for p in ports})==len(ports),'invalid public host ports')
    return '\n'.join(f'{"reg" if d=="input" else "wire"} {w} {n}{"=0" if d=="input" else ""};' for d,w,n in ports)+'\nFPGATop dut('+','.join(f'.{n}({n})' for _,_,n in ports)+');\n', ports


def descriptor_rows(directory):
    paths=list(directory.glob('*.native-inplace-graft-descriptors.json'))
    require(len(paths)==1,'one global graft descriptor inventory required')
    rows=json.loads(paths[0].read_text())['state']
    require(len(rows)==7 and sum(r['depth'] for r in rows)==34,'changed bounded native storage geometry')
    return rows


def original_router(directory):
    matches=list(directory.glob('*.native-inplace-graft-router.sv'))
    require(len(matches)==1 and sha(matches[0])==sha(ROOT/'sims/firesim/sim/midas/src/main/verilog/CheckpointPhysicalStateRouter.sv'),
            'generated graft router differs from original source')


def bindings(parameters,ports,directory):
    lines=[f'localparam [63:0] {k.upper()}={v};' for k,v in parameters.items()]
    identity=directory/'identity.json'
    manifest=json.loads(identity.read_text())['descriptor_manifest_sha256'] if identity.is_file() else 'f'*64
    lines.append(f"localparam [255:0] EXPECTED_MANIFEST=256'h{manifest};")
    for suffix,width in [('reservedCycle','[63:0]'),('reservedPresent','[1:0]'),
                         ('reservedFrozen','[1:0]'),('reservedError','[1:0]'),('reservedFreeze','')]:
        matches=[n for _,w,n in ports if w==width and (n==suffix or n.endswith('_'+suffix))]
        require(len(matches)==1,'ambiguous generated owner port '+suffix)
        lines.append(f'`define {suffix.upper()} {matches[0]}')
    peer=json.loads((directory/'peer-routing.json').read_text())
    transport='dut.'+'.'.join(peer['transport'].split('.')[1:])
    for name,pin in [('MASK','clock_mask'),('READ_ENABLE','physical_read_enable'),('CAPTURED_CE','captured_ce')]:
        lines.append(f'`define {name} {transport}.{pin}')
    lines.append('`define CYCLE dut.sim.network.cycle')
    funcs={n:[] for n in ('bank','slot','width','depth','offset','kind')};offset=0
    for i,row in enumerate(descriptor_rows(directory)):
        if row['bank']==255:kind=5
        else:
            hierarchy=row.get('selected_hierarchy',row['hierarchy'])
            if hierarchy.endswith('.cycles'):kind=0
            elif hierarchy.endswith('.ram_r_data'):kind=1
            elif hierarchy.endswith('.ram'):kind=2
            elif re.search(r'\.left_?\.value$',hierarchy):kind=3
            elif re.search(r'\.right_?\.value$',hierarchy):kind=4
            else:raise ValueError('unknown independent fixture state '+hierarchy)
        for name,value in dict(bank=row['bank'],slot=row['slot'],width=row['width'],depth=row['depth'],offset=offset,kind=kind).items():
            funcs[name].append(f'{i}: entry_{name}={value};')
        offset+=row['depth']
    for name,values in funcs.items():
        lines.append(f'function automatic integer entry_{name}(input integer e); case(e)\n'+'\n'.join(values)+f'\ndefault: entry_{name}=-1; endcase endfunction')
    return '\n'.join(lines)+'\n'


def synthesis_tcl(directory, *, write_component=True):
    files=verilog_files(directory)
    synthesis=list(directory.glob('*.native-inplace-graft.synthesis.xdc'))
    implementation=list(directory.glob('*.native-inplace-graft.implementation.xdc'))
    require(len(synthesis)==len(implementation)==1,'original native graft constraints required')
    projected_synthesis = 'read_xdc generated/projected.synthesis.xdc\n' if (directory/'annotation-projection.json').is_file() else ''
    projected_implementation = ''
    if projected_synthesis:
        # FPGATop OOC has no board clock pads. Preserve and independently audit
        # the full final XDC, but defer its literal (zero-target) shell placement
        # snippets to F1Shim/image implementation. Apply EVERY hierarchy-bound
        # implementation constraint to this OOC netlist.
        annotations = json.loads((directory/'connected-annotations.json').read_text())
        implementation_text = (directory/'projected.implementation.xdc').read_text()
        for a in annotations:
            if (a['class'] in ('midas.InternalXDCAnnotation', 'midas.targetutils.xdc.XDCAnnotation') and
                    a['destinationFile']['class'].endswith('$Implementation$') and not a['argumentList']):
                require(implementation_text.count(a['formatString']) == 1, 'ambiguous literal shell XDC snippet')
                implementation_text = implementation_text.replace(a['formatString'], '', 1)
        component=directory/'projected-component.implementation.xdc'
        if write_component:
            component.write_text(implementation_text)
        else:
            require(component.read_text()==implementation_text, 'changed scoped component constraints')
        projected_implementation = 'source generated/projected-component.implementation.xdc\n'
    peer=json.loads((directory/'peer-routing.json').read_text())
    transport='/'.join(peer['transport'].split('.')[1:])
    connection=json.loads((directory/'connection.json').read_text())
    selected=connection['selected'].split('.')[1:]
    selected_module=connection['selected_module']
    require(selected and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', n) for n in selected+[selected_module]),
            'literal selected constraint scope required')
    # Graft files describe the selected source's local circuit. The unified
    # projected files describe the enclosing host. Exercise both consumers in
    # their actual scopes; a source-local network/... path cannot resolve at
    # FPGATop's root. Do not delete the original source constraints to hide it.
    local_synthesis='read_xdc -ref '+selected_module+' generated/'+synthesis[0].name+'\n'
    local_implementation='current_instance '+('/'.join(selected))+'\nsource generated/'+implementation[0].name+'\ncurrent_instance\n'
    return '''set_param general.maxThreads 4
read_verilog -sv '''+' '.join(files)+'''
'''+local_synthesis+projected_synthesis+'''synth_design -top FPGATop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
'''+local_implementation+projected_implementation+'''set gates [get_cells -hier -filter {REF_NAME == BUFGCE}]
if {[llength $gates] != 3} {error "expected original pair of native gates and single root mask"}
foreach gate $gates {if {[get_property CE_TYPE $gate] ne "SYNC"} {error "changed native gate semantics"}}
if {[llength [get_cells -hier -filter {REF_NAME == FDRE && IS_C_INVERTED == 1}]] != 1} {error "expected unique falling-edge mask"}
set raw [get_nets -of_objects [get_ports clock]]
set checked 0
foreach pattern {*CPUManagedStreamEngine*/* *ctrlInterconnect*/* *checkpoint_readout_adapter/router/* *checkpoint_readout_adapter/ce_endpoint/* '''+transport+'''/*} {
  set cells [get_cells -hier -filter "NAME =~ $pattern && REF_NAME =~ FD*"]
  if {[llength $cells] == 0} {error "missing actual raw-clock control/DMA/readout registers $pattern"}
  foreach cell $cells {
    if {[get_property IS_C_INVERTED $cell] eq "1"} {continue}
    set clocks [get_nets -segments -of_objects [get_pins -of_objects $cell -filter {REF_PIN_NAME == C}]]
    if {[lsearch -exact $clocks $raw] < 0} {error "masked control/DMA/readout register $cell"}
    incr checked
  }
}
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force widget-graft.dcp
puts "WIDGET_GRAFT_SYNTH_PASS raw_registers=$checked gates=3"
'''


def audit_frames(directory,work):
    rows=descriptor_rows(directory);audits=[]
    identity=directory/'identity.json'
    manifest=int(json.loads(identity.read_text())['descriptor_manifest_sha256'],16) if identity.is_file() else 2**256-1
    complete_order=[(ordinal,address) for ordinal,row in enumerate(rows) for address in range(row['depth'])]
    for path in sorted(work.glob('capture-*.hex')):
        raw=[int(line,16).to_bytes(64,'little') for line in path.read_text().splitlines()]
        require(len(raw)==36,'incomplete captured fixture stream')
        frames=[int.from_bytes(data,'little') for data in raw];cut=field(frames[0],96,64)
        require(12<=cut<10000,'fixture cut before initialized active state')
        memory=[max(c for c in range(cut) if c%8==address) for address in range(8)]
        expected_pipeline=cut-9
        word=0
        for index,frame in enumerate(frames):
            require(field(frame,0,64)==0x3154504b434d5346 and field(frame,64,16)==1 and field(frame,96,64)==cut,
                    'changed fixture frame identity/cut')
            require(field(frame,80,16)==(1 if index==0 else 3 if index==35 else 2),'bad frame order')
            if index==0:
                require(field(frame,224,32)==7 and field(frame,256,256)==manifest,'captured transport identity mismatch')
            elif index==35:
                require(field(frame,160,64)==34 and field(frame,224,32)==crc32c(b''.join(raw[:-1]))^0xffffffff,
                        'fixture CRC or complete word count changed')
            else:
                ordinal=field(frame,224,32);at=field(frame,256,32)
                require(ordinal<7,'unknown captured descriptor')
                row=rows[ordinal]
                require((ordinal,at)==complete_order[word] and field(frame,160,64)==word and at<row['depth'] and field(frame,288,16)==row['width'] and
                        field(frame,304,8)==row['bank'] and field(frame,312,16)==row['slot'],'changed frame selector')
                if row['bank']==255:value=1
                else:
                    hierarchy=row.get('selected_hierarchy',row['hierarchy'])
                    logical=row['logical_state'];chunks=(logical['width']+63)//64
                    if hierarchy.endswith('.ram'):value=memory[at//chunks]
                    elif hierarchy.endswith('.ram_r_data'):value=expected_pipeline
                    elif hierarchy.endswith('.cycles') or re.search(r'\.(?:left|right)_?\.value$',hierarchy):value=cut
                    else:raise ValueError('unknown independent fixture state '+hierarchy)
                    value=(value>>(64*(at%chunks)))&((1<<64)-1)
                require(field(frame,336,64)==value,'independent arithmetic/RAM DMA payload mismatch')
                word+=1
        require(word==34,'incomplete fixture state coverage')
        audits.append(dict(file=path.name,target_cut=cut,words=word,crc32c=field(frames[-1],224,32)))
    require(len(audits)==4,'four active captures including post-reset continuation required')
    return audits


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('vivado','vcs','audit','structure'),required=True)
    for name in ('generated','native','eda','out'):
        parser.add_argument('--'+name,type=Path,required=name=='out')
    args=parser.parse_args()
    from tools.checkpoint_formats.tests.audit_widget_graft import audit, corruptions
    require(args.out.resolve().is_relative_to(RUNS),'evidence below runs required')
    args.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=args.mode+'-',dir=args.out.resolve()))
    sources={n:sha(ROOT/n) for n in source_files()};commands=[]
    def run(argv,name,expected=0,cwd=out):
        row=dict(argv=list(map(str,argv)),cwd=str(cwd),log=str(out/(name+'.log')))
        commands.append(row)
        with Path(row['log']).open('w') as stream:
            # Successful C++ compilation can be silent. Retain the actual
            # invocation in every log so its nonempty evidence pin remains
            # auditable without weakening the regression receipt contract.
            stream.write('argv='+json.dumps(row['argv'])+'\ncwd='+str(cwd)+'\n')
            stream.flush()
            proc=subprocess.run(row['argv'],cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        row['returncode']=proc.returncode
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        require(proc.returncode==expected,'inspect underlying log '+row['log'])
        return Path(row['log']).read_text()
    def validate(directory,backend):
        require(directory and directory.resolve().is_relative_to(RUNS),'receipt below runs required')
        doc=json.loads((directory/'summary.json').read_text())
        require(doc['status']=='pass' and doc['backend']==backend and doc['sources']==sources and
                doc['physical_fpga_capture'] is False and doc['deployable_capture_image'] is False,
                'stale/wrong-scope widget graft evidence')
        for group in ('inputs','artifacts'):
            for n,digest in doc[group].items():
                require((directory/n).stat().st_size and sha(directory/n)==digest,'changed widget graft evidence '+n)
        require(audit(directory/'generated')==doc['audit'],'changed independent widget graft structure')
        require((directory/'synth.tcl').read_text()==synthesis_tcl(directory/'generated',write_component=False),
                'changed selected-source or enclosing-host constraint scope')
        original_router(directory/'generated')
        return doc
    summary=dict(status='pass',backend='eda' if args.mode=='vcs' else 'f2',sources=sources,
                 observed_utc=datetime.now(timezone.utc).isoformat(),host=socket.gethostname(),source_root=str(ROOT),
                 physical_fpga_capture=False,deployable_capture_image=False,metasim_restore_supported=False,
                 scope='existing wrapper readout through registered sentinel widget; component evidence only')
    if args.mode=='structure':
        summary.update(audit=audit(args.generated),inputs={},artifacts={})
    elif args.mode=='vivado':
        require(ROOT==Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),'native localhost Vivado required')
        require(args.generated and args.generated.resolve().is_relative_to(RUNS),'generated input below runs required')
        shutil.copytree(args.generated,out/'generated')
        synth = synthesis_tcl(out/'generated')
        summary['audit']=audit(out/'generated')
        original_router(out/'generated')
        summary['rejected_corruptions']=corruptions(out/'generated',out/'corruptions')
        for name in sources:
            dest=out/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        for name in RTL:
            shutil.copyfile(ROOT/'sims/firesim/sim/midas/src/main/verilog'/name,out/'sources'/name)
        vendor=Path(os.environ['XILINX_VIVADO'])/'data/verilog/src'
        summary['vendor_models']={}
        for name,src in (('BUFGCE.v',vendor/'unisims/BUFGCE.v'),('glbl.v',vendor/'glbl.v')):
            shutil.copyfile(src,out/name);summary['vendor_models'][name]=dict(original_path=str(src),sha256=sha(src))
        (out/'target-clock-sink.sv').write_text(STUB)
        port_text,ports=port_header(out/'generated');(out/'top_ports.svh').write_text(port_text)
        parameters=header_parameters(out/'generated')
        (out/'top_bindings.svh').write_text(bindings(parameters,ports,out/'generated'))
        (out/'synth.tcl').write_text(synth)
        if (out/'generated/annotation-projection.json').is_file():
            annotations = json.loads((out/'generated/connected-annotations.json').read_text())
            summary['ooc_deferred_shell_constraints'] = [dict(format_sha256=hashlib.sha256(a['formatString'].encode()).hexdigest(),
                destination='Implementation', reason='literal board-pad placement outside FPGATop OOC') for a in annotations
                if a['class'] in ('midas.InternalXDCAnnotation', 'midas.targetutils.xdc.XDCAnnotation') and
                a['destinationFile']['class'].endswith('$Implementation$') and not a['argumentList']]
        summary['inputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*')
                           if p.is_file() and 'corruptions' not in p.relative_to(out).parts}
        text=run(['vivado','-mode','batch','-source','synth.tcl'],'synth')
        require('WIDGET_GRAFT_SYNTH_PASS' in text and not re.search(r'ERROR:|CRITICAL WARNING:',text),'widget graft native synthesis failed')
        summary['artifacts']={n:sha(out/n) for n in ('widget-graft.dcp','utilization.rpt','timing.rpt','synth.log','commands.json')}
    elif args.mode=='vcs':
        require(shutil.which('vcs')==toolchain.VCS=='/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs','EDA native SP2 required')
        native=validate(args.native,'f2')
        for name in native['inputs']:
            dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.native/name,dest)
        summary.update(inputs=native['inputs'],vendor_models=native['vendor_models'],audit=audit(out/'generated'))
        files=verilog_files(out/'generated')+['BUFGCE.v','glbl.v','sources/'+TESTS+'widget_graft_tb.sv',
                                             'sources/'+TESTS+'checkpoint_generated_network_exit.cc']
        common=[toolchain.VCS,'-full64','-sverilog','-timescale=1ns/1ps','-Mupdate','-debug_access+all',
                '+incdir+'+str(out),'-top','widget_graft_tb','-top','glbl']
        run([*common,'-Mdir=csrc','-o','simv',*files],'compile')
        artifacts=['compile.log','commands.json']
        for case in ('healthy','missing-owner'):
            work=out/case;work.mkdir()
            text=run([out/'simv','-no_save']+([] if case=='healthy' else ['+'+case]),case,cwd=work)
            if case=='healthy':
                match=re.search(r'WIDGET_GRAFT_PASS checks=(\d+) cuts=(\d+) words=(\d+) stalls=(\d+)',text)
                require(match and int(match[1])>100 and int(match[2])>=3 and int(match[4])>20,'incomplete connected widget execution')
                summary['execution']=dict(zip(('checks','cuts','words','stalls'),map(int,match.groups())))
                summary['frame_audits']=audit_frames(out/'generated',work)
            else:
                require('WIDGET_GRAFT_REJECT missing_owner=1 reset_recovered=1' in text,'missing-owner/reset fault escaped')
            require((work/'widget-graft.vcd').stat().st_size>2000,'missing complete debug waveform '+case)
            artifacts += [case+'.log',case+'/widget-graft.vcd']
            artifacts += [str(p.relative_to(out)) for p in work.glob('capture-*.hex')]
        # Compile an actual emitted endpoint defect. The bench/oracle remains
        # byte-for-byte unchanged; no fabricated bank response is supplied.
        adapter=[n for n in files if n.endswith('.native-inplace-graft.sv')]
        require(len(adapter)==1,'one actual adapter source required')
        original=(out/adapter[0]).read_text()
        before='assign functional_response_data = checkpoint_inplace_ckpt_resp_data;'
        after="assign functional_response_data = checkpoint_inplace_ckpt_resp_data ^ 64'd1;"
        require(original.count(before)==1,'ambiguous actual endpoint corruption')
        (out/'corrupt-adapter.sv').write_text(original.replace(before,after))
        bad_files=['corrupt-adapter.sv' if n==adapter[0] else n for n in files]
        run([*common,'-Mdir=corrupt-csrc','-o','corrupt-simv',*bad_files],'corrupt-compile')
        work=out/'corrupt';work.mkdir()
        text=run([out/'corrupt-simv','-no_save'],'corrupt',expected=1,cwd=work)
        require('reason=independent captured bank payload' in text and
                re.search(r'WIDGET_GRAFT_PAYLOAD_MISMATCH cut=\d+ word=0 entry=0 address=0 .*payload_byte=42',text),
                'actual endpoint defect escaped first captured data word')
        require((work/'widget-graft.vcd').stat().st_size>2000,'missing corruption waveform')
        summary['compiled_payload_defect']=dict(source='corrupt-adapter.sv',first_word=0,first_frame_payload_byte=42,
                                                mutation_before=before,mutation_after=after)
        artifacts += ['corrupt-adapter.sv','corrupt-compile.log','corrupt.log','corrupt/widget-graft.vcd']
        if (out/'generated/identity.json').is_file():
            header=(out/'generated/reserved.h').read_text()
            expressions=re.findall(r'^  (checkpoint_capture_manifest_t.*)\)\);$',header,re.M)
            require(len(expressions)==1,'one actual generated host initializer required')
            (out/'bound_manifest.svh').write_text(expressions[0]+'\n')
            cc=ROOT/'sims/firesim/sim/midas/src/main/cc'
            common=[os.environ['CXX'],'-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
                    '-g','-O1','-fno-omit-frame-pointer','-fsanitize=address,undefined','-I'+str(cc),'-I'+str(out)]
            # The full registered header must still reject compilation. This
            # negative is separate from testing its extracted data initializer.
            (out/'guard.cc').write_text('#include "core/checkpoint_capture.h"\n#include "generated/reserved.h"\n')
            text=run([*common,'-c','guard.cc','-o','guard.o'],'host-guard',expected=1)
            require('Incomplete_checkpoint_hardware_coverage' in text,'incomplete-owner host guard escaped')
            run([*common,cc/'core/checkpoint_capture.cc','sources/'+TESTS+'widget_identity_host.cc',
                 '-o','identity-host'],'host-compile')
            captures=[]
            for source in sorted((out/'healthy').glob('capture-*.hex')):
                dest=source.with_suffix('.bin')
                dest.write_bytes(b''.join(int(row,16).to_bytes(64,'little') for row in source.read_text().splitlines()))
                captures.append(dest)
            require(len(captures)==4,'four actual captured VCS frame inputs required')
            text=run([out/'identity-host',*captures],'host-run')
            require('WIDGET_IDENTITY_HOST_PASS checks=20 cuts=4' in text,'generated host metadata failed')
            summary['identity_host']=dict(checks=20,cuts=4,sanitizers=['address','undefined'],
                production_header_rejected=True,actual_constructor_signature_checked=True)
            artifacts += ['bound_manifest.svh','guard.cc','host-guard.log','host-compile.log','host-run.log']
            artifacts += [str(p.relative_to(out)) for p in captures]
        summary['artifacts']={n:sha(out/n) for n in artifacts}
    else:
        native,eda=validate(args.native,'f2'),validate(args.eda,'eda')
        require(native['inputs']==eda['inputs'],'native/EDA inputs differ')
        summary.update(audit=native['audit'],execution=eda['execution'],frame_audits=eda['frame_audits'],
                       matched_inputs=len(native['inputs']),inputs={},artifacts={})
    require(sources=={n:sha(ROOT/n) for n in sources},'source changed during verification')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(out/'summary.json')


if __name__=='__main__':
    main()
