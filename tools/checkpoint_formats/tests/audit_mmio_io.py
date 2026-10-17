"""Independent MMIO schema, AXI timing, MT19937-64 and component readback audit."""
import argparse
import json
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha

MASK=(1<<64)-1

def pack(*words):
    return struct.pack('<'+'Q'*len(words),*words)

class Engine:
    def __init__(self):
        self.s=[165]
        for i in range(1,312): self.s.append((6364136223846793005*(self.s[-1]^(self.s[-1]>>62))+i)&MASK)
        self.index=312
    def draw(self):
        if self.index==312:
            for i in range(312):
                x=(self.s[i]&0xffffffff80000000)|(self.s[(i+1)%312]&0x7fffffff)
                self.s[i]=self.s[(i+156)%312]^(x>>1)^((x&1)*0xb5026f5aa96619e9)
            self.index=0
        y=self.s[self.index]; self.index+=1
        y^=(y>>29)&0x5555555555555555
        y^=(y<<17)&0x71d67fffeda60000
        y^=(y<<37)&0xfff7eee000000000
        return (y^(y>>43))&MASK
    def payload(self,maximum,total):
        return pack(0x3154504b434d5448,1,maximum,165,total,0,312,*self.s,self.index)


def oracle(maximum):
    # Independent scheduler: one request per blocking call; readiness varies
    # per channel, with delayed responses and host delay batches checked only
    # after the entire PRNG-selected batch has returned.
    rng=Engine(); tick=1; total=0; rows=[]; states=[]
    for op in range(12):
        states.append((tick,rng.payload(maximum,total)))
        rows.append(f'OP {op} {tick}')
        addr=0xfffffffc if op==11 else 0x100+op*4
        is_read=bool(op%2); accepted=aw=w=complete=False; due=0
        while not complete:
            total=rng.draw()%maximum+1
            for _ in range(total):
                tick+=1
                if is_read:
                    # Response cannot occur on the address handshake tick.
                    if accepted and not complete and tick>=due and tick%2==0:
                        rows.append(f'R {tick} {(addr*0x10203+0xfedcba98)&0xffffffff}'); complete=True
                    if not accepted and tick%3==2:
                        accepted=True; due=tick+3; rows.append(f'AR {tick} {addr}')
                else:
                    if aw and w and not complete and tick>=due and tick%2:
                        rows.append(f'B {tick}'); complete=True
                    if not aw and tick%4==1:
                        aw=True; due=tick+4; rows.append(f'AW {tick} {addr}')
                    if not w and tick%5==3:
                        w=True; rows.append(f'W {tick} {0xf0000000+op*0x10203}')
        rows.append(f'RETURN {op} {tick}')
    states.append((tick,rng.payload(maximum,total)))
    return rows,states


def audit(path):
    path=Path(path).resolve(); out=path.parent; r=json.loads(path.read_text())
    require(r['status']=='passed' and r['level1_verified'] is False and r['level2_verified'] is False,'MMIO IO scope')
    require(json.loads((out/'source-inputs.json').read_text())==r['source_inputs'],'MMIO bindings')
    for b in r['source_inputs']: require(file_sha(b['snapshot'])==b['sha256'],'MMIO source snapshot')
    require({str(f) for f in out.rglob('*') if f.is_file() and f!=path}==set(r['artifact_sha256']),'MMIO artifact membership')
    for f,h in r['artifact_sha256'].items(): require(file_sha(f)==h,'MMIO artifact changed '+f)
    require(json.loads((out/'commands.json').read_text())==r['commands'],'MMIO commands')
    require(len(r['cases'])==56 and len(r['commands'])==58,'MMIO process counts')
    require({(c['backend'],c['delay'],c['mode'],c['cut']) for c in r['cases']}==
            {(b,d,m,c) for b in ('native','vcs-dpi') for d in (1,7)
             for m,c in [('reference',0),*[('restore',c) for c in range(12)],('negative',0)]},'MMIO case membership')
    comparisons=active=nested=negative=queued=inflight=0
    for c in r['cases']:
        log=Path(c['log']).read_text(); lines=log.splitlines()
        require(lines[0]=='cwd='+str(out) and json.loads(lines[1][5:])==c['argv'] and
                lines[2].startswith('fresh_process_pid=') and lines[-1]=='exit=0','MMIO fresh process receipt')
        require('source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in c['argv'][2],'MMIO VCS environment')
        require(not any(s in log for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected','MMIO_IO_FAIL')),'MMIO sanitizer')
        if c['backend']=='vcs-dpi': require('MMIO_IO_VCS_ZERO_EDGES time=0 edges=0' in log,'MMIO VCS time zero')
        dest=Path(c['destination']); cut=c['cut']
        if c['mode']=='negative':
            m=re.search(r'MMIO_IO_NEGATIVE rejected=(\d+) partial_publication=0 target_edges=0',log)
            require(m and int(m[1])==206 and not list(dest.iterdir()),'MMIO invalid cases')
            negative+=int(m[1]); continue
        rows,states=oracle(c['delay']); start=rows.index(f'OP {cut} {states[cut][0]}')
        require((dest/'trace').read_text().splitlines()==rows[start:],'MMIO AXI timing and PRNG oracle')
        m=re.search(r'MMIO_IO_PASS operations=(\d+) active=(\d+) stream_active=(\d+) queued=(\d+) inflight=(\d+) rejections=(\d+) target_edges=0',log)
        require(m and int(m[1])==12-cut and int(m[6])==5*int(m[2])+3*int(m[3]),'MMIO suspension guards')
        require(int(m[2])>0 and int(m[4])>0 and int(m[5])>0,'MMIO queued and in-flight coverage')
        active+=int(m[2]); nested+=int(m[3]); queued+=int(m[4]); inflight+=int(m[5])
        for op in range(cut,13):
            prefix='final' if op==12 else f'cut-{op}'
            require((dest/(prefix+'.io')).read_bytes()==pack(0x3154504B43474457,1,25,3,12,32,32,0),'MMIO owner schema')
            require((dest/(prefix+'.axi')).read_bytes()==pack(0x3154504b434f494d,1,12,32,32,0,0)+bytes(44),'MMIO returned AXI state')
            require((dest/(prefix+'.stream')).read_bytes()==pack(0x3154504B43474457,1,24,3,16,64,512,0),'MMIO nested stream owner schema')
            require((dest/(prefix+'.timing')).read_bytes()==states[op][1],'MMIO complete timing owner')
            require(int((dest/(prefix+'.ticks')).read_text())==states[op][0],'MMIO host peer label')
        if c['mode']=='restore':
            require('MMIO_IO_PREEDGE_READBACK owners=4 target_edges=0' in log,'MMIO missing preedge readback')
            ref=Path(c['reference'])
            for kind in ('io','axi','timing','stream'):
                require((dest/f'readback.{kind}').read_bytes()==(ref/f'cut-{cut}.{kind}').read_bytes(),'MMIO preedge mismatch')
                require((dest/f'final.{kind}').read_bytes()==(ref/f'final.{kind}').read_bytes(),'MMIO continuation mismatch')
                comparisons+=2
    return dict(status='passed',fresh_component_restores=48,owner_comparisons=comparisons,
                suspended_boundaries=active,suspended_rejections=5*active+3*nested,
                nested_stream_boundaries=nested,queued_boundaries=queued,inflight_boundaries=inflight,
                invalid_rejections=negative,level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--summary',type=Path,required=True)
    print(json.dumps(audit(p.parse_args().summary),indent=2))


if __name__=='__main__': main()
