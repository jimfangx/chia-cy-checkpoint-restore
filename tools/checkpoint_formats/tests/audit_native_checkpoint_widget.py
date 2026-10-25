"""Independent native Widget receipts, complete words, negative exits and waves."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.fpga_transport import crc32c
from tools.checkpoint_formats.tests import verify_native_checkpoint_widget as verify


def audit(native,eda):
    docs=[]
    for path,backend in ((native,'f2'),(eda,'eda')):
        doc=json.loads((path/'summary.json').read_text())
        require(doc['status']=='pass' and doc['backend']==backend and doc['physical_fpga_capture'] is False and
            doc['production_rocket_integrated'] is False,'wrong native Widget evidence scope')
        require(doc['sources']=={n:verify.sha(verify.ROOT/n) for n in verify.SOURCES},'stale source identity')
        expected={*(str(p.relative_to(path)) for p in (path/'generated').rglob('*') if p.is_file()),
            *(f'sources/{Path(n).name}' for n in verify.SOURCES),'synth.tcl','BUFGCE.v','glbl.v',
            'native-selectors.svh','native-widget-manifest.svh'}
        require(set(doc['inputs'])==expected,'incomplete native Widget input inventory')
        for group in ('inputs','artifacts'):
            for name,value in doc[group].items():require((path/name).stat().st_size>0 and verify.sha(path/name)==value,'changed evidence '+name)
        for name,value in doc['sources'].items():require(verify.sha(path/'sources'/Path(name).name)==value,'changed source snapshot')
        require((path/'synth.tcl').read_text()==verify.TCL,'changed native synthesis recipe')
        verify.audit(path/'generated')
        for model,row in doc['vendor_models'].items():require(verify.sha(path/model)==row['sha256'],'changed native primitive model')
        docs.append(doc)
    n,e=docs;require(n['inputs']==e['inputs'],'different native/EDA inputs')
    require(set(n['artifacts'])=={'native-widget.dcp','utilization.rpt','timing.rpt','synth.log','commands.json'},'missing native synthesis evidence')
    with zipfile.ZipFile(native/'native-widget.dcp') as archive:
        require(archive.testzip() is None,'bad native DCP')
        metadata=archive.read('dcp.xml').decode()
        require('<Top Name="NativeCheckpointWidgetFixture"' in metadata and 'Vivado v2025.2' in metadata and
            '<Part Name="xcvu47p-fsvh2892-2-e"' in metadata,'wrong native DCP top/tool/part')
    synth=(native/'synth.log').read_text()
    require('NATIVE_WIDGET_SYNTH_PASS gates=3 falling_edge_masks=1 raw_clock_endpoints=3' in synth and
        not re.search(r'ERROR:|CRITICAL WARNING:',synth),'native synthesis not established')
    commands=json.loads((eda/'commands.json').read_text())
    require([c['returncode'] for c in commands]==[0,0,0,0,0,1,0,1],'incomplete process exit evidence')
    for c in (commands[0],commands[-2]):
        require(c['argv'][0]==verify.toolchain.VCS and {'-full64','-Mupdate','-debug_access+all'}<=set(c['argv']),
            'wrong native SP2/debug build')
    required_logs={'compile.log','healthy.log','missing.log','ce.log','cycle.log','corrupt.log','mutated-compile.log','mutated.log'}
    waves={name+'/native-widget.vcd' for name in ('healthy','missing','ce','cycle','corrupt','mutated')}
    require(required_logs|waves|{'healthy/frames.hex'}<=set(e['artifacts']),'missing negative/frame/wave evidence')
    require({str(p.relative_to(eda)) for p in eda.rglob('*.vcd')}==waves,'missing full-visibility execution waves')
    for name in waves:
        times=re.findall(r'^#(\d+)$',(eda/name).read_text(),re.M)
        require(len(times)>1 and int(times[-1])>0,'unflushed waveform '+name)
    text=(eda/'healthy.log').read_text()
    marker=re.search(r'NATIVE_WIDGET_PASS checks=(\d+) cuts=5 words=170 stalls=(\d+) recovered_cycle=96',text)
    require(marker and int(marker[1])==e['checks']>1000 and int(marker[2])==e['dma_stalls']>100 and
        e['cuts']==5 and e['words']==170 and e['recovered_cycle']==96,'incomplete healthy native Widget execution')
    lines=(eda/'healthy/frames.hex').read_text().splitlines();require(len(lines)==180,'incomplete capture history')
    descriptors=json.loads((eda/'generated'/(verify.PREFIX+'.native-descriptors.json')).read_text())['state']
    expected_words=[(ordinal,address) for ordinal,row in enumerate(descriptors) for address in range(row['depth'])]
    for start in range(0,180,36):
        for word,(ordinal,address) in zip(lines[start+1:start+35],expected_words):
            frame=int(word,16)
            require((verify.field(frame,224,32),verify.field(frame,256,32))==(ordinal,address),
                'missing/duplicated/reordered native descriptor word')
    cuts=[verify.audit_frames(eda/'generated',lines[i:i+36]) for i in range(0,180,36)]
    require(cuts==e['frame_audits'],'changed frame oracle audits')
    logged=[int(c) for c in re.findall(r'NATIVE_WIDGET_CAPTURE requested=\d+ cut=(\d+) words=34',text)]
    require(logged==[row['target_cut'] for row in cuts],'changed execution/capture target labels')
    for name in ('missing','ce','cycle'):
        text=(eda/(name+'.log')).read_text()
        require('NATIVE_WIDGET_REJECT fault='+name in text and 'acknowledged_edges=0' in text,'missing sticky fault rejection')
    faults={}
    for name in ('corrupt','mutated'):
        text=(eda/(name+'.log')).read_text()
        marker=re.search(r'NATIVE_WIDGET_DIVERGENCE cycle=(\d+) checks=(\d+) reason=independent native bank and CE payload',text)
        require(marker and 'NATIVE_WIDGET_PASS' not in text,'missing first-divergence semantic rejection')
        faults[name]=dict(cycle=int(marker[1]),check=int(marker[2]))
    return dict(status='pass',scope='native Widget component evidence only',physical_fpga_capture=False,
        matched_inputs=len(n['inputs']),matched_sources=len(n['sources']),checks=e['checks'],cuts=cuts,waves=6,first_divergences=faults)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('native','eda','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();require(args.out.resolve().is_relative_to(verify.RUNS),'evidence below runs required')
    args.out.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='audit-',dir=args.out.resolve()))
    healthy=audit(args.native,args.eda);rejections=[]
    for fault in ('hardware-claim','missing-wave','semantic-frame','wrong-cut','missing-dcp','missing-negative','changed-model','coherent-native-reset','duplicate-word'):
        work=out/fault
        for original,side in ((args.native,'native'),(args.eda,'eda')):
            for src in original.rglob('*'):
                dest=work/side/src.relative_to(original)
                if src.is_dir():dest.mkdir(parents=True,exist_ok=True)
                elif src.is_file():dest.parent.mkdir(parents=True,exist_ok=True);dest.symlink_to(os.path.relpath(src.resolve(),dest.parent.resolve()))
        def replace(path,data):path.unlink();path.write_bytes(data)
        docs={side:copy.deepcopy(json.loads((work/side/'summary.json').read_text())) for side in ('native','eda')}
        if fault=='hardware-claim':docs['native']['physical_fpga_capture']=True
        elif fault=='missing-wave':
            name='ce/native-widget.vcd';(work/'eda'/name).unlink();docs['eda']['artifacts'].pop(name)
        elif fault in ('semantic-frame','duplicate-word'):
            name='healthy/frames.hex';frames=[int(line,16).to_bytes(64,'little') for line in (work/'eda'/name).read_text().splitlines()]
            if fault=='semantic-frame':frames[1]=(int.from_bytes(frames[1],'little')^(1<<336)).to_bytes(64,'little')
            else:
                # Copy all selector/payload bits while retaining the next sequence number.
                previous=int.from_bytes(frames[1],'little');mask=((1<<64)-1)<<160
                frames[2]=((previous&~mask)|(1<<160)).to_bytes(64,'little')
            trailer=int.from_bytes(frames[35],'little')&~(((1<<32)-1)<<224)
            frames[35]=(trailer|((crc32c(b''.join(frames[:35]))^0xffffffff)<<224)).to_bytes(64,'little')
            replace(work/'eda'/name,''.join(f'{int.from_bytes(f,"little"):0128x}\n' for f in frames).encode())
            docs['eda']['artifacts'][name]=verify.sha(work/'eda'/name)
        elif fault=='wrong-cut':docs['eda']['frame_audits'][0]['target_cut']+=1
        elif fault=='missing-dcp':(work/'native/native-widget.dcp').unlink()
        elif fault=='missing-negative':
            name='mutated.log';(work/'eda'/name).unlink();docs['eda']['artifacts'].pop(name)
        elif fault=='changed-model':
            replace(work/'native/BUFGCE.v',b'// substituted primitive\n');docs['native']['inputs']['BUFGCE.v']=verify.sha(work/'native/BUFGCE.v')
        else:
            name='generated/'+verify.PREFIX+'.native-state-access.sv';binding='generated/'+verify.PREFIX+'.native-state-access.json'
            data=(work/'native'/name).read_text().replace('.ckpt_reset(capture_reset)','.ckpt_reset(reset)').encode()
            for side in docs:
                replace(work/side/name,data);docs[side]['inputs'][name]=verify.sha(work/side/name)
                bound=json.loads((work/side/binding).read_text());bound['endpoint_sha256']=verify.sha(work/side/name)
                replace(work/side/binding,json.dumps(bound).encode());docs[side]['inputs'][binding]=verify.sha(work/side/binding)
        for side,doc in docs.items():replace(work/side/'summary.json',json.dumps(doc,indent=2).encode())
        try:audit(work/'native',work/'eda')
        except (ValueError,FileNotFoundError,KeyError) as exc:rejections.append(dict(name=fault,error=str(exc)))
        else:raise AssertionError('accepted native Widget evidence corruption '+fault)
    result=dict(**healthy,rejections=rejections,native_receipt=str(args.native/'summary.json'),eda_receipt=str(args.eda/'summary.json'),
        auditor_sha256=verify.sha(Path(__file__)))
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(out/'summary.json')

if __name__=='__main__':main()
