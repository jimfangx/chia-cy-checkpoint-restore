"""Independent complete byte audit of joint runtime IO candidate evidence."""
import argparse
import json
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.audit_mmio_io import Engine, pack


def axi(ident,addr,bits,stage):
    beat=bits//8
    result=pack(0x3154504b434f494d,1,ident,addr,bits,int(stage>=1),int(stage>=1))+bytes(beat)
    if stage==3: return result+pack(0,0,0,0,0)
    result+=pack(1,0,0x120,2,2,1,0,0x240,2,2)
    start=(0,1,3)[stage]
    result+=pack(3-start)
    for i in range(start,3):
        data=bytes((j*13+7)&255 for j in range(i*4,i*4+4))+bytes(beat-4)
        result+=pack((5,10,15)[i],int(i==2))+data
    result+=pack(3 if stage==2 else 0)
    if stage==2:
        for i in range(3): result+=pack(0,int(i==2))+struct.pack('<I',0x12345678)*(beat//4)
    result+=pack(1,0) if stage==2 else pack(0)
    return result


def expected(no_dma,stage,final=False):
    mmio=axi(12,32,32,3 if final else stage)
    if final: mmio=pack(0x3154504b434f494d,1,12,32,32,0,0)+bytes(44)
    result=[('runtime/mmio-io','firesim.emul.mmio-io.returned.v1',pack(0x3154504b43474457,1,25,3,12,32,32,0)),
            ('runtime/mmio','firesim.mmio.full.v1',mmio)]
    if not no_dma:
        dma=axi(16,64,512,stage) if not final else pack(0x3154504b434f494d,1,16,64,512,0,0)+bytes(104)
        result += [('runtime/cpu-managed-stream-io','firesim.emul.cpu-managed-stream-io.returned.v1',pack(0x3154504b43474457,1,24,3,16,64,512,0)),
                   ('runtime/cpu-managed-axi4','firesim.mmio.full.v1',dma)]
    rng=Engine(166);delay=rng.draw()%7+1
    result.append(('runtime/host-timing','firesim.host-timing.mt19937-64.libstdcxx.v1',rng.payload(7,delay,delay,166)))
    return result


def check_image(dest,prefix,wanted):
    manifest=(dest/(prefix+'.owners')).read_text().splitlines()
    require(manifest==[name+' '+schema for name,schema,_ in wanted],'runtime IO owner membership')
    for i,(_,_,payload) in enumerate(wanted):
        require((dest/(prefix+'.'+str(i))).read_bytes()==payload,'runtime IO full payload '+prefix+' '+str(i))
    return len(wanted)


def audit(path):
    path=Path(path).resolve();out=path.parent;r=json.loads(path.read_text())
    require(r['status']=='passed' and not r['level1_verified'] and not r['level2_verified'],'runtime IO scope')
    require(json.loads((out/'source-inputs.json').read_text())==r['source_inputs'],'runtime IO bindings')
    for b in r['source_inputs']:require(file_sha(b['snapshot'])==b['sha256'],'runtime IO input snapshot')
    require({str(f) for f in out.rglob('*') if f.is_file() and f!=path}==set(r['artifact_sha256']),'runtime IO artifact membership')
    for f,h in r['artifact_sha256'].items():require(file_sha(f)==h,'runtime IO artifact changed')
    require(json.loads((out/'commands.json').read_text())==r['commands'],'runtime IO command receipts')
    sealed=r.get('sealed_publication',False)
    modes=('reference','restore','sealed-restore','negative','fatal-unsealed','fatal-thread',
           'fatal-destination','fatal-recycled','fatal-consumed','fatal-stale') if sealed else ('reference','restore','negative')
    require(len(r['commands'])==2+12*len(modes) and len(r['cases'])==12*len(modes),'runtime IO process counts')
    require({(c['backend'],c['delay'],c['mode'],c['cut']) for c in r['cases']}==
            {(b,n,m,c) for b in ('native','vcs-dpi') for n in (0,1) for m in modes for c in range(3)},'runtime IO case membership')
    comparisons=rejects=preparation=publication=sealing=fatals=0
    for c in r['cases']:
        log=Path(c['log']).read_text();lines=log.splitlines()
        fatal=c['mode'].startswith('fatal-')
        require(lines[0]=='cwd='+str(out) and json.loads(lines[1][5:])==c['argv'] and
                lines[2].startswith('fresh_process_pid=') and lines[-1]==('exit=86' if fatal else 'exit=0'),'runtime IO fresh process receipt')
        require('source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in c['argv'][2],'runtime IO VCS environment')
        require(not any(s in log for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected','RUNTIME_IO_FAIL')),'runtime IO sanitizers')
        if fatal:
            require(f'RUNTIME_IO_FATAL mode={c["mode"]} unchanged=1 target_edges=0' in log,'runtime IO fatal boundary')
            require('RUNTIME_IO_PASS' not in log and 'RUNTIME_IO_VCS_ZERO_EDGES' not in log,'runtime IO fatal must not return to simulator')
            require(not Path(c['destination']).exists(),'runtime IO fatal published output')
            fatals+=1;continue
        if c['backend']=='vcs-dpi':require('RUNTIME_IO_VCS_ZERO_EDGES time=0 edges=0' in log,'runtime IO zero edges')
        no_dma=c['delay'];stage=c['cut'];dest=Path(c['destination'])
        if c['mode']=='negative':
            m=re.search(r'RUNTIME_IO_NEGATIVE rejected=(\d+) preparation_failures=(\d+) publication_failures=(\d+) partial_publication=0 target_edges=0',log)
            require(m and int(m[1])==((50 if not no_dma else 35) if sealed else (47 if not no_dma else 32)) and int(m[2])>0 and int(m[3])>0,'runtime IO atomic rejections')
            rejects+=int(m[1]);preparation+=int(m[2]);publication+=int(m[3])
            if sealed:
                s=re.search(r'RUNTIME_IO_SEAL failures=(\d+) publication_allocations=0 cancellation_unchanged=1',log)
                require(s and int(s[1])>0,'runtime IO seal allocation/cancellation checks');sealing+=int(s[1])
            comparisons+=check_image(dest,'published',expected(no_dma,stage));continue
        require(f'RUNTIME_IO_PASS owners={3 if no_dma else 5} stage={stage} target_edges=0' in log,'runtime IO continuation')
        comparisons+=check_image(dest,'cut' if c['mode']=='reference' else 'readback',expected(no_dma,stage))
        comparisons+=check_image(dest,'final',expected(no_dma,stage,True))
        if c['mode'] in ('restore','sealed-restore'):
            ref=Path(c['reference'])
            for i in range(3 if no_dma else 5):
                require((dest/f'readback.{i}').read_bytes()==(ref/f'cut.{i}').read_bytes(),'runtime IO independent restore readback')
                require((dest/f'final.{i}').read_bytes()==(ref/f'final.{i}').read_bytes(),'runtime IO finite continuation')
    return dict(status='passed',fresh_component_restores=24 if sealed else 12,complete_owner_comparisons=comparisons,
                invalid_rejections=rejects,preparation_allocation_failures=preparation,
                publication_allocation_failures=publication,sealing_allocation_failures=sealing,
                fatal_contract_rejections=fatals,partial_publication=0,
                level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--summary',type=Path,required=True)
    print(json.dumps(audit(p.parse_args().summary),indent=2))

if __name__=='__main__':main()
