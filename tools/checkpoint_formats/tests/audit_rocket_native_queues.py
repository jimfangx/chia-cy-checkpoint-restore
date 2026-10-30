"""Streaming independent original-register/input-history and DMA frame audit."""
import argparse
import hashlib
import gzip
import json
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.codec import require, FormatError
from tools.checkpoint_formats.fpga_transport import crc32c, field
from tools.checkpoint_formats.tests.verify_rocket_native_queues import ROOT, RUNS, audit_generated, sha


def wave_history(path, observations, expected_sha):
    prefix='rocket_native_queues_tb.dut'
    names={'clock':'clock','reset':'reset','functional_hold':'hold','target_cycle':'cycle','root_clock':'root_clock','priming':'priming','dma_valid':'dma_valid','dma_ready':'dma_ready','dma_data':'dma_data'}
    wanted={'rocket_native_queues_tb.'+n:v for n,v in names.items()}
    wanted.update({prefix+'.capture.'+n:n for n in ('pending','invalid','owner','control_state','transport_state')})
    snapshot=prefix+'.capture.transport.native_capture.snapshot.'
    for n in ('request','request_ready','payload','cut_cycle'):wanted[snapshot+n]='sample_'+n
    fields=[]
    for q,obs in enumerate(observations):
        for f in obs['state']:
            name=f'q{q}.'+f['emitted_register'];fields.append((name,q*1664+f['offset'],f['width']))
            wanted[prefix+'.host.'+name]=name
        for n in ('enq_valid','enq_bits','deq_ready'):
            wanted[prefix+f'.lane{q}_io_'+n]=f'q{q}_'+n
    codes,values,scopes,previous={},{},[],{}
    code_set=set()
    memory=[[None]*6144 for _ in range(4)];wp=[0]*4;rp=[0]*4;ra=[0]*4;count=[0]*4;fullflag=[0]*4
    captures=[];diagnostics=[];samples=0;root_model=0;diagnostic_words=0;diagnostic_frames=0
    def sample():
        nonlocal previous,samples,root_model,diagnostic_words,diagnostic_frames
        now={n:values[c] for n,c in codes.items() if c in values}
        binary=lambda d,n:n in d and re.fullmatch('[01]+',d[n]) is not None
        integer=lambda d,n:int(d[n],2)
        def expand(value,width):
            return value.rjust(width,value[0] if value[0] in 'xz' else '0')
        if all(binary(now,n) for n in ('pending','invalid','owner')) and all(n in now for n in ('control_state','transport_state')):
            expected=format(integer(now,'owner'),'02b')+now['invalid']+now['pending']+expand(now['transport_state'],7284)
            require(expected==expand(now['control_state'],7288),'router register readout mismatch');samples+=1
        if now.get('root_clock')=='1' and previous.get('root_clock')=='0':
            root_model=0 if previous.get('reset')=='1' else root_model+1
        if binary(now,'cycle') and binary(now,'root_clock'):
            require(integer(now,'cycle')==root_model,'native hold/target label diverges from actual vendor root edge history')
        if previous.get('priming')=='1' and now.get('priming')=='0':
            require(len(diagnostics)==1 and diagnostic_words==196624 and diagnostic_frames==196625,
                    'incomplete real frontdoor selector priming')
            diagnostics[0].update(original_words_acked=diagnostic_words,native_staged_words_acked=0)
        if now.get('clock')=='1' and previous.get('clock')=='0':
            if previous.get('priming')=='1' and previous.get('dma_valid')==previous.get('dma_ready')=='1':
                require(binary(previous,'dma_data'),'unresolved diagnostic native word was acknowledged')
                frame=integer(previous,'dma_data');diagnostic_frames+=1
                if field(frame,80,16)==2:
                    require(field(frame,224,32)<20,'diagnostic native word was acknowledged')
                    diagnostic_words+=1
            if previous.get('sample_request')==previous.get('sample_request_ready')=='1':
                require(all(n in previous for n,_,_ in fields),'missing native owner at sampling cut')
                vector=''.join(expand(previous[n],width) for n,offset,width in sorted(fields,key=lambda x:x[1],reverse=True))
                require(vector==expand(now['sample_payload'],6656),'snapshot differs from complete original queue register vector')
                require(integer(now,'sample_cut_cycle')==integer(previous,'cycle'),'sample target label mismatch')
                require(all(all(v is not None for v in lane) for lane in memory),'uninitialized original memory capture')
                unknown=[n for n,_,_ in fields if not binary(previous,n)]
                if previous.get('priming')=='1':
                    expected={f'q{q}.checkpoint_shell_region{q}_ckpt_native_{name}' for q in range(4) for name in ('bank','slot','address')}
                    require(set(unknown)==expected,'diagnostic warmup changed the original unreset selector set')
                    diagnostics.append(dict(target_cycle=integer(now,'sample_cut_cycle'),unresolved_fields=unknown,
                        complete_original_native_bits_msb_first=vector,published=False))
                else:
                    require(not unknown,'unknown native owner in a published cut')
                    captures.append(dict(target_cycle=integer(now,'sample_cut_cycle'),native=int(vector,2),
                        memory=[m.copy() for m in memory],wp=wp.copy(),rp=rp.copy(),ra=ra.copy(),count=count.copy(),fullflag=fullflag.copy()))
            if previous.get('reset')=='1':
                wp[:]=[0]*4;rp[:]=[0]*4;ra[:]=[0]*4;count[:]=[0]*4;fullflag[:]=[0]*4
            elif previous.get('hold')=='0':
                for q in range(4):
                    enq=integer(previous,f'q{q}_enq_valid') and count[q]<6144
                    deq=integer(previous,f'q{q}_deq_ready') and count[q]>0
                    ra[q]=(rp[q]+int(deq))%6144
                    if enq:memory[q][wp[q]]=integer(previous,f'q{q}_enq_bits');wp[q]=(wp[q]+1)%6144
                    if deq:rp[q]=(rp[q]+1)%6144
                    count[q]+=int(enq)-int(deq)
                    if bool(enq)!=bool(deq):fullflag[q]=int(enq)
        previous=now
    raw_hash=hashlib.sha256()
    with (gzip.open(path,'rb') if path.suffix=='.gz' else path.open('rb')) as stream:
        for raw_line in stream:
            raw_hash.update(raw_line)
            first=raw_line[:1]
            if first==b'$':
                parts=raw_line.decode('ascii').split()
                if parts[0]=='$scope':scopes.append(parts[2])
                elif parts[0]=='$upscope':scopes.pop()
                elif parts[0]=='$var':
                    name='.'.join(scopes+[parts[4].lstrip('\\')])
                    if name in wanted:
                        codes[wanted[name]]=parts[3];code_set.add(parts[3].encode('ascii'))
            elif first==b'#':sample()
            elif first in (b'b',b'B'):
                value,_,code=raw_line.rstrip().rpartition(b' ')
                if code in code_set:values[code.decode('ascii')]=value[1:].decode('ascii').lower()
            elif first in (b'0',b'1',b'x',b'X',b'z',b'Z'):
                code=raw_line[1:].rstrip()
                if code in code_set:values[code.decode('ascii')]=first.decode('ascii').lower()
    require(raw_hash.hexdigest()==expected_sha,'compressed waveform differs from original complete debug bytes')
    sample();require(codes.keys()==set(wanted.values()),'missing original waveform owners '+str(set(wanted.values())-codes.keys()))
    require(samples>0 and len(captures)==4 and len(diagnostics)==1,'incomplete independent original-state history')
    return captures,samples,diagnostics


def ordered_selectors(rows, native_words=104):
    """Manifest order is coverage, not merely a hint attached to each word.

    Never let a stream choose the expected address used by the payload oracle:
    a duplicate with a repaired CRC would then conceal a missing original word.
    """
    for ordinal, row in enumerate(rows):
        for address in range(row['depth']):
            yield ordinal, address, row['width'], row['bank'], row['slot']
    for address in range(native_words):
        yield len(rows), address, 64, 252, 0


def check_selector(frame, expected, sequence):
    actual = tuple(field(frame, offset, width) for offset, width in
                   ((224,32),(256,32),(288,16),(304,8),(312,16)))
    require(actual == expected,
            f'missing/duplicate/out-of-order owner word at sequence={sequence}: expected={expected} actual={actual}')


def frames(path,rows,capture,digest):
    words=sum(r['depth'] for r in rows)+104
    raw=path.read_bytes();require(len(raw)==(words+2)*64,'truncated four-queue stream')
    crc=crc32c(raw[:-64])^0xffffffff
    selectors=iter(ordered_selectors(rows))
    for i in range(words+2):
        f=int.from_bytes(raw[i*64:(i+1)*64],'little')
        require(field(f,0,64)==0x3154504b434d5346 and field(f,64,16)==1 and
            field(f,96,64)==capture['target_cycle'],'frame identity/target label changed')
        if i==0:
            require(field(f,80,16)==1 and field(f,160,64)==0 and field(f,224,32)==len(rows)+1 and field(f,256,256)==int(digest,16),'manifest header mismatch')
        elif i==words+1:
            require(field(f,80,16)==3 and field(f,160,64)==words and field(f,224,32)==crc and f>>256==0,'CRC/trailer mismatch')
        else:
            ordinal=field(f,224,32);address=field(f,256,32)
            require(field(f,80,16)==2 and field(f,160,64)==i-1 and f>>400==0 and field(f,328,8)==0,'noncanonical frame order/bits')
            check_selector(f,next(selectors),i-1)
            if ordinal==20:
                require(field(f,304,8)==252 and field(f,312,16)==0 and field(f,288,16)==64 and address<104,'native descriptor mismatch')
                expected=(capture['native']>>(address*64))&((1<<64)-1)
            else:
                require(ordinal<20,'unknown original descriptor');r=rows[ordinal];q=r['region']
                require(address<r['depth'] and field(f,304,8)==r['bank'] and field(f,312,16)==r['slot'] and field(f,288,16)==r['width'],'original descriptor mismatch')
                name=r['hierarchy'].split('.')[-1]
                if name=='ram':expected=(capture['memory'][q][address//8]>>(64*(address%8)))&((1<<64)-1)
                else:expected=capture[{'enq_ptr_value':'wp','deq_ptr_value':'rp','maybe_full':'fullflag','ram_io_deq_bits_MPORT_addr':'ra'}[name]][q]
            require(field(f,336,64)==expected,f'original input-history word mismatch frame={i} ordinal={ordinal} address={address}')
    require(next(selectors,None) is None,'incomplete original owner coverage')
    return dict(path=str(path),sha256=sha(path),target_cycle=capture['target_cycle'],words=words)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--eda',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    require(a.out.resolve().is_relative_to(RUNS),'evidence outside runs');a.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='audit-',dir=a.out.resolve()))
    eda=a.eda.resolve();doc=json.loads((eda/'summary.json').read_text());require(doc['status']=='pass','failed EDA receipt')
    for n,h in doc['sources'].items():require(sha(ROOT/n)==h,'stale EDA sources '+n)
    for n,h in doc['artifacts'].items():require(sha(eda/n)==h,'changed EDA artifact '+n)
    rows,obs=audit_generated(eda/'generated')
    wave=eda/'rocket-native-queues-healthy.vcd.gz'
    wave_binding=next(x for x in doc['waveforms'] if Path(x['compressed_path']).name==wave.name)
    captures,samples,diagnostics=wave_history(wave,obs,wave_binding['original_sha256'])
    digest=sha(eda/'capture-manifest.json')
    audited=[frames(eda/f'queue-cut-{i}.bin',rows,c,digest) for i,c in enumerate(captures)]
    negatives=[]
    first=(eda/'queue-cut-0.bin').read_bytes()
    for case in ['truncated','crc','semantic-rehashed','manifest-rehashed',
                 'duplicate-address-rehashed','duplicate-owner-rehashed',
                 'duplicate-native-address-rehashed','header-sequence-rehashed']:
        raw=bytearray(first)
        if case=='truncated':raw.pop()
        elif case=='crc':raw[-36]^=1
        elif case=='semantic-rehashed':raw[64+42]^=1
        elif case=='manifest-rehashed':raw[32]^=1
        elif case=='header-sequence-rehashed':raw[20]^=1
        else:
            # Copy a genuine word and its selector, preserving the destination
            # sequence number and recomputing the complete stream CRC. Both
            # payloads match their reported selectors: only complete ordered
            # ownership detects the missing original word.
            native_start=1+sum(r['depth'] for r in rows)
            source,destination={'duplicate-address-rehashed':(1,2),
                'duplicate-owner-rehashed':(1,1+sum(r['depth'] for r in rows if r['region']==0)),
                'duplicate-native-address-rehashed':(native_start,native_start+1)}[case]
            raw[destination*64+28:(destination+1)*64]=raw[source*64+28:(source+1)*64]
        if case.endswith('-rehashed'):
            raw[-36:-32]=(crc32c(raw[:-64])^0xffffffff).to_bytes(4,'little')
        bad=out/(case+'.bin');bad.write_bytes(raw)
        try:frames(bad,rows,captures[0],digest)
        except FormatError as error:negatives.append(dict(case=case,rejected=True,error=str(error),path=str(bad),sha256=sha(bad)))
        else:raise AssertionError('corrupt component stream accepted '+case)
    summary=dict(status='pass',scope='independent exact-queue original waveform/input-history/CRC audit; no CPU or FPGA acceptance',
        eda_receipt=dict(path=str(eda/'summary.json'),sha256=sha(eda/'summary.json')),
        original_register_vectors=56,router_register_vectors=3,router_samples=samples,cuts=audited,unpublished_diagnostic_samples=diagnostics,negative_streams=negatives,
        source=dict(path=str(Path(__file__)),sha256=sha(__file__)),physical_fpga_capture=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(out/'summary.json')

if __name__=='__main__':main()
