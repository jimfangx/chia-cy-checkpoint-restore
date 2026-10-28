"""Independently bind physical Widget synthesis, SP2 execution and exact frames.

Reject coherently rehashed owner/binding/frame substitutions as well as absent
native/debug/negative evidence. This is still component evidence only.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.fpga_transport import crc32c
from tools.checkpoint_formats.tests import verify_physical_checkpoint_widget as verify


def audit(native, eda):
    documents=[]
    for directory,backend in ((native,'f2'),(eda,'eda')):
        doc=json.loads((directory/'summary.json').read_text())
        require(doc['status']=='pass' and doc['backend']==backend and
                doc['physical_fpga_capture'] is False and doc['production_rocket_integrated'] is False,
                'wrong physical Widget evidence scope')
        require(doc['sources']=={n:verify.sha(verify.ROOT/n) for n in verify.SOURCES},'stale source binding')
        expected={*(f'widget/{n}' for n in verify.WIDGET_FILES),
            *(f'network/{n}' for n in verify.NETWORK_FILES),
            *(f'ce-generated/{n}' for n in verify.CE_FILES),
            *(f'sources/{Path(n).name}' for n in verify.SOURCES),'synth.tcl','BUFGCE.v','glbl.v'}
        require(set(doc['inputs'])==expected,'incomplete input inventory')
        for group in ('inputs','artifacts'):
            for name,digest in doc[group].items():
                require(verify.sha(directory/name)==digest,'changed '+group+' '+name)
        for name,digest in doc['sources'].items():
            require(verify.sha(directory/'sources'/Path(name).name)==digest,'changed current source snapshot')
        require((directory/'synth.tcl').read_text()==verify.TCL,'wrong native synthesis recipe')
        verify.check_network(directory/'network');verify.check_ce(directory/'ce-generated')
        rtl=(directory/'widget/CheckpointCaptureWidget.v').read_text()
        require(rtl.count('CheckpointPhysicalCaptureTransport\n')==1 and '.EXTERNAL_CLOCK_NETWORK(1)' in rtl and
                '.GATES(3)' in rtl and '.OWNERS(2)' in rtl and '.ENTRIES(5)' in rtl,'wrong physical Widget parameters')
        for lhs,rhs in (('transport_physicalTransport_ce','capture_physical_logicalCE'),
                ('capture_physical_clockMask','transport_physicalTransport_clock_mask'),
                ('transport_physicalTransport_clock','clock'),('transport_physicalTransport_reset','reset')):
            require(len(re.findall(r'\bassign\s+'+lhs+r'\s*=\s*'+rhs+r'\s*;',rtl))==1,
                    'changed physical Widget connection '+lhs)
        header=(directory/'widget/physical_constants.h').read_text()
        for resource in verify.WIDGET_FILES[1:5]:
            require(verify.sha(directory/'widget'/resource)==verify.sha(verify.ROOT/verify.VERILOG/resource) and
                    resource+' SHA256: '+verify.sha(directory/'widget'/resource) in header,'wrong physical header/resource identity')
        require('PHYSICAL_CLOCK_GATES 3U' in header and 'EXTERNAL_CLOCK_NETWORK 1U' in header and
                '0123456789abcdef'*4 in header,'wrong physical ABI header')
        documents.append(doc)
    n,e=documents
    require(n['inputs']==e['inputs'],'native/EDA input mismatch')
    native_artifacts={'physical-widget.dcp','utilization.rpt','timing.rpt','synth.log','commands.json','shadow-registers.tsv'}
    require(set(n['artifacts'])==native_artifacts,'missing native implementation evidence')
    with zipfile.ZipFile(native/'physical-widget.dcp') as z:
        require(z.testzip() is None,'bad native DCP')
        metadata=z.read('dcp.xml').decode()
        require('<Top Name="CheckpointCaptureWidget"' in metadata and 'Vivado v2025.2' in metadata and
                '<Part Name="xcvu47p-fsvh2892-2-e"' in metadata,'wrong native DCP top/tool/part')
    synth=(native/'synth.log').read_text()
    require('PHYSICAL_WIDGET_SYNTH_PASS external_network=1 falling_edge_masks=1 duplicate_gates=0' in synth and
            not re.search('ERROR:|CRITICAL WARNING:',synth),'native synthesis not established')
    shadow = (native/'shadow-registers.tsv').read_text().splitlines()
    require(len(shadow) >= 700 and len(shadow) == len(set(shadow)) and
            f'LIVE_WIDGET_SNAPSHOT_SYNTH_PASS registers={len(shadow)} ungated=1' in synth,
            'missing raw-clock live transport shadow storage audit')
    logs={'compile.log','healthy.log','missing.log','ce.log','cycle.log','corrupt.log','mutated-compile.log','mutated-widget.log'}
    waves={f'{name}/physical-widget.vcd' for name in ('healthy','missing','ce','cycle','corrupt','mutated-widget')}
    require(logs|waves|{'healthy/frames.hex'} <= set(e['artifacts']),'missing negative/debug/frame evidence')
    require(set(str(p.relative_to(eda)) for p in eda.rglob('*.vcd'))==waves and
            all((eda/p).stat().st_size>100 for p in waves),'incomplete full debug waveforms')
    for name in waves:
        timestamps=re.findall(r'^#(\d+)$',(eda/name).read_text(),re.M)
        require(len(timestamps)>1 and int(timestamps[-1])>0,'unflushed debug waveform '+name)
    text=(eda/'healthy.log').read_text()
    require('PHYSICAL_WIDGET_SHADOW_PASS captures=6 words=144' in text,
            'missing complete physical transport/local shadow MMIO readback')
    match=re.search(r'PHYSICAL_WIDGET_PASS checks=(\d+) cuts=6 stalls=(\d+) recovered_cycles=96',text)
    require(match is not None and int(match[1])==e['checks'] and e['checks']>1000 and
            int(match[2])==e['dma_stalls'] and e['dma_stalls']>50 and e['cuts']==6 and e['recovered_cycles']==96,
            'incomplete physical Widget execution')
    cuts=re.findall(r'PHYSICAL_WIDGET_CAPTURE requested=(\d+) accepted=(\d+) cut=(\d+) words=7',text)
    require(len(cuts)==6 and all(int(c)==int(a) for _,a,c in cuts) and
            e['target_cuts']==[int(c) for _,_,c in cuts],'wrong actual adapter/target cut labels')
    raw=[int(line,16).to_bytes(64,'little') for line in (eda/'healthy/frames.hex').read_text().splitlines()]
    require(len(raw)==54,'incomplete six frame streams')
    frame_audits=[verify.audit_frames(b''.join(raw[i:i+9])) for i in range(0,54,9)]
    require(frame_audits==e['frame_audits'],'changed frame arithmetic/CRC audits')
    for name in ('missing','ce','cycle'):
        require('PHYSICAL_WIDGET_REJECT fault='+name in (eda/(name+'.log')).read_text() and
                'acknowledged_edges=0' in (eda/(name+'.log')).read_text(),'missing fault rejection')
    for name,reason in (('corrupt','banked CE state'),('mutated-widget','unmasked CE identity')):
        require('reason='+reason in (eda/(name+'.log')).read_text() and
                'PHYSICAL_WIDGET_PASS' not in (eda/(name+'.log')).read_text(),'missing first-divergence rejection')
    commands=json.loads((eda/'commands.json').read_text())
    require([c['returncode'] for c in commands]==[0,0,0,0,0,1,0,1], 'incomplete positive/negative process exits')
    for c in (commands[0],commands[-2]):
        require('/Y-2026.03-SP2/bin/vcs' in c['argv'][0] and
                {'-full64','-Mupdate','-debug_access+all'}<=set(c['argv']),'wrong EDA compile/debug scope')
    return dict(status='pass',matched_inputs=len(n['inputs']),matched_sources=len(n['sources']),
        checks=e['checks'],cuts=e['target_cuts'],waves=len(waves),physical_fpga_capture=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('native','eda','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    require(args.out.resolve().is_relative_to(verify.RUNS),'evidence below runs required')
    args.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='audit-',dir=args.out))
    healthy=audit(args.native,args.eda)
    rejections=[]
    for fault in ('hardware-claim','missing-owner','coherent-widget-binding','missing-wave','semantic-frame','wrong-cut','missing-dcp','missing-negative'):
        work=out/fault;work.mkdir()
        # Every input remains immutable. Link copies only for read-only auditing;
        # changed files are unlinked before writing their replacement bytes.
        for src,name in ((args.native,'native'),(args.eda,'eda')):
            for p in src.rglob('*'):
                target=work/name/p.relative_to(src)
                if p.is_dir():target.mkdir(parents=True,exist_ok=True)
                elif p.is_file():
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.symlink_to(os.path.relpath(p.resolve(),target.parent.resolve()))
        def replace(path,data):
            path.unlink();path.write_bytes(data)
        docs={name:copy.deepcopy(json.loads((work/name/'summary.json').read_text())) for name in ('native','eda')}
        if fault=='hardware-claim':docs['native']['physical_fpga_capture']=True
        elif fault=='missing-owner':
            name='ce-generated/physical-clock-state-bank.json'
            doc=json.loads((work/'native'/name).read_text());doc['state'].pop()
            data=json.dumps(doc).encode()
            for side in docs:
                replace(work/side/name,data);docs[side]['inputs'][name]=verify.sha(work/side/name)
        elif fault=='coherent-widget-binding':
            name='widget/CheckpointCaptureWidget.v'
            text=(work/'native'/name).read_text().replace('assign transport_physicalTransport_ce = capture_physical_logicalCE;',
                "assign transport_physicalTransport_ce = capture_physical_logicalCE ^ 3'd1;")
            for side in docs:
                replace(work/side/name,text.encode());docs[side]['inputs'][name]=verify.sha(work/side/name)
        elif fault=='missing-wave':
            name='ce/physical-widget.vcd';(work/'eda'/name).unlink();docs['eda']['artifacts'].pop(name)
        elif fault=='semantic-frame':
            name='healthy/frames.hex';frames=[int(s,16).to_bytes(64,'little') for s in (work/'eda'/name).read_text().splitlines()]
            frame=int.from_bytes(frames[5],'little')^(1<<336);frames[5]=frame.to_bytes(64,'little')
            trailer=int.from_bytes(frames[8],'little');trailer &= ~(((1<<32)-1)<<224)
            trailer |= (crc32c(b''.join(frames[:8]))^0xffffffff)<<224;frames[8]=trailer.to_bytes(64,'little')
            replace(work/'eda'/name,(''.join(f'{int.from_bytes(f,"little"):0128x}\n' for f in frames)).encode())
            docs['eda']['artifacts'][name]=verify.sha(work/'eda'/name)
        elif fault=='wrong-cut':docs['eda']['target_cuts'][0]+=1
        elif fault=='missing-dcp':(work/'native/physical-widget.dcp').unlink()
        else:
            name='mutated-widget.log';(work/'eda'/name).unlink();docs['eda']['artifacts'].pop(name)
        for side,doc in docs.items():replace(work/side/'summary.json',(json.dumps(doc,indent=2)+'\n').encode())
        try:audit(work/'native',work/'eda')
        except (ValueError,FileNotFoundError,KeyError) as exc:rejections.append(dict(name=fault,error=str(exc)))
        else:raise RuntimeError('accepted evidence substitution '+fault)
    result=dict(**healthy,rejections=rejections,native_receipt=str(args.native/'summary.json'),
        eda_receipt=str(args.eda/'summary.json'),auditor_sha256=verify.sha(Path(__file__)))
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(out/'summary.json')


if __name__=='__main__':main()
