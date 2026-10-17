"""Independent schema, transfer-split, owner/readback and rejection audit."""
import argparse
import json
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.evidence import file_sha


def oracle(beat,cut):
    rows=[]
    for op in range(cut,14):
        rows.append(f'OP {op}')
        if op>=2:
            remaining=(0,1,255,256,257,513)[(op-2)//2]
            addr=4096+op*65536
            while remaining:
                # Production uses the remainder first, then 256-beat bursts.
                count=(remaining-1)%256+1
                rows.append(f'{"AW" if op%2==0 else "AR"} {op} {addr} {count}')
                if op%2==0: rows.extend(f'W {op} {addr+i*beat}' for i in range(count))
                remaining-=count; addr+=count*beat
        rows.append(f'RETURN {op}')
    return rows


def audit(path):
    path=Path(path).resolve(); out=path.parent; r=json.loads(path.read_text())
    require(r['status']=='passed' and r['level1_verified'] is False and r['level2_verified'] is False,'CPU IO scope')
    require(json.loads((out/'source-inputs.json').read_text())==r['source_inputs'],'IO bindings')
    for b in r['source_inputs']: require(file_sha(b['snapshot'])==b['sha256'],'IO source snapshot')
    require({str(f) for f in out.rglob('*') if f.is_file() and f!=path}==set(r['artifact_sha256']),'IO artifact membership')
    for f,h in r['artifact_sha256'].items(): require(file_sha(f)==h,'IO artifact changed '+f)
    require(json.loads((out/'commands.json').read_text())==r['commands'],'IO commands')
    require(len(r['cases'])==96 and len(r['commands'])==98,'IO process counts')
    require({(c['backend'],c['beat'],c['mode'],c['cut']) for c in r['cases']}==
            {(b,w,m,c) for b in ('native','vcs-dpi') for w in (8,16,64)
             for m,c in [('reference',0),*[('restore',c) for c in range(14)],('negative',0)]},'IO case membership')
    comparisons=active=negative=0
    for c in r['cases']:
        log=Path(c['log']).read_text(); rows=log.splitlines()
        require(rows[0]=='cwd='+str(out) and json.loads(rows[1][5:])==c['argv'] and
                rows[2].startswith('fresh_process_pid=') and rows[-1]=='exit=0','IO fresh process receipt')
        require('source /scratch/jfx/chia-cy-checkpoint-restore/automations/checkpoint_loop/vcs-env.sh && ' in c['argv'][2], 'IO VCS environment')
        require(not any(s in log for s in ('ERROR: AddressSanitizer','runtime error:','LeakSanitizer: detected','CPU_IO_FAIL')),'IO sanitizer')
        if c['backend']=='vcs-dpi': require('CPU_IO_VCS_ZERO_EDGES time=0 edges=0' in log,'IO VCS time zero')
        dest=Path(c['destination']); beat=c['beat']; cut=c['cut']
        if c['mode']=='negative':
            m=re.search(r'CPU_IO_NEGATIVE rejected=(\d+) partial_publication=0 target_edges=0',log)
            # 64-byte geometry-bound image: all truncations and all byte flips
            # in validate/load plus trailing, other geometry and poisoned calls.
            require(m and int(m[1])==205 and not list(dest.iterdir()),'IO invalid cases')
            negative+=int(m[1]); continue
        require((dest/'trace').read_text().splitlines()==oracle(beat,cut),'IO transfer oracle')
        m=re.search(r'CPU_IO_PASS operations=(\d+) active_boundaries=(\d+) rejections=(\d+) target_edges=0',log)
        require(m and int(m[1])==14-cut and int(m[3])==1+6*int(m[2]),'IO suspension guards')
        require(int(m[2])>0,'IO active transfer coverage'); active+=int(m[2])
        expected=struct.pack('<8Q',0x3154504B43474457,1,24,3,16,64,beat*8,0)
        for op in range(cut,14):
            require((dest/f'cut-{op}.io').read_bytes()==expected,'IO owner schema')
            # No caller-owned pending requests remain after a returned call.
            axi=(dest/f'cut-{op}.axi').read_bytes()
            require(struct.unpack('<7Q',axi[:56])==(0x3154504b434f494d,1,16,64,beat*8,0,0) and
                    axi[56:56+beat]==bytes(beat) and axi[56+beat:]==bytes(40),'IO idle AXI owner')
        require((dest/'final.io').read_bytes()==expected,'IO final owner')
        if c['mode']=='restore':
            require('CPU_IO_PREEDGE_READBACK owners=2 target_edges=0' in log,'IO missing preedge readback')
            ref=Path(c['reference'])
            for kind in ('io','axi'):
                require((dest/f'readback.{kind}').read_bytes()==(ref/f'cut-{cut}.{kind}').read_bytes(), 'IO preedge mismatch')
                require((dest/f'final.{kind}').read_bytes()==(ref/f'final.{kind}').read_bytes(),'IO continuation mismatch')
                comparisons+=2
    return dict(status='passed',fresh_component_restores=84,owner_comparisons=comparisons,
                suspended_boundaries=active,suspended_rejections=6*active,invalid_rejections=negative,
                level1_verified=False,level2_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--summary',type=Path,required=True)
    print(json.dumps(audit(p.parse_args().summary),indent=2))


if __name__=='__main__': main()
