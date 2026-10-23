"""Native encoder/publication oracle, syscall faults, kills and concurrent I/O."""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor

from tools.checkpoint_formats import aggregate, aggregate_packed as packed
from tools.checkpoint_formats.codec import canonical, decode, encode, require
from tools.checkpoint_formats.durable_restore import prepare_durable_loader
from tools.checkpoint_formats.tests.test_aggregate_packed import PackedAggregateTest
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    # Retain all previous invocation artifacts, including killed-writer pending
    # files and special fixtures; never delete them to make a rerun pass.
    case=Path(tempfile.mkdtemp(prefix='invocation-',dir=out))
    build,runtime,generated,layout,data=PackedAggregateTest().fixture(case)
    doc=decode(data,'fsckpt',build)
    counter=next(e for e in generated['state'] if e['kind']=='register')
    wide=copy.deepcopy(counter); wide['hierarchy']='Top.wide'
    gate=copy.deepcopy(counter)
    gate.update(hierarchy='Top.gate.O',module='BUFGCE',kind='register',width=1,depth=1,adapter='metasim-bufgce-v1')
    for entry in (wide,gate):
        entry['state_id']=hashlib.sha256(canonical(dict(hierarchy=entry['hierarchy'],kind=entry['kind'],
            namespace='generated-simulator-state-v1'))).hexdigest()
    generated['instances'].append(dict(hierarchy='Top.gate',module='BUFGCE',implementation_sha256='b'*64))
    generated['state']=sorted([*generated['state'],wide,gate],key=lambda e:e['state_id'])
    doc['records'] += [dict(owner='generated-entry/Top.wide',width=260,value='1'+'f'*64),
                       dict(owner='generated-entry/Top.gate.O',width=4,value='0')]
    doc['records'].sort(key=lambda r:r['owner'])
    counter['width']=64
    runtime=packed.runtime_manifest(runtime['profile'],generated,layout,runtime['native_owners'],
                                    runtime['native_build_hash'],counter['hierarchy'])
    prepare_durable_loader(runtime,generated,layout,case)
    source=ROOT/'tools/checkpoint_formats'
    command=[os.environ.get('CXX',_toolchain.CXX),'-std=c++20','-g','-fsanitize=address,undefined',
             '-fno-omit-frame-pointer','-no-pie',f'-I{case}',source/'durable_restore.cc',
             source/'durable_publish.cc',source/'tests/durable_publish_native.cc','-lcrypto',
             *['-Wl,--wrap='+name for name in ('open','openat','write','fsync','close','renameat')],
             '-o',case/'verify']
    run(command,case/'build.log')
    build=aggregate.build_identity(runtime,generated,layout,case/'verify'); doc['build']=build
    next(r for r in doc['records'] if r['owner']=='generated-entry/'+counter['hierarchy']).update(width=64,value=f'{9:016x}')
    image=encode('fsckpt',doc)
    def staging(value,path):
        packed.prepare_aggregate_restore(value,build,runtime,generated,layout,path)
        return path.read_bytes()
    snapshot=case/'snapshot.load'; good=staging(image,snapshot)
    destination=case/'checkpoint with spaces.fsckpt'; destination.write_bytes(b'old destination\n')
    executable=case/'verify'
    def execute(label,path=snapshot,dest=destination,fault='none',expected=0):
        return run([executable,path,dest,fault],case/(label+'.log'),expected=expected)
    execute('valid')
    require(destination.read_bytes()==image,'native encoding differs from independent Python oracle')
    require(stat.S_IMODE(destination.stat().st_mode)==0o600,'publication mode is not private')
    execute('eintr-short-write',fault='eintr-short-write')
    require(destination.read_bytes()==image,'EINTR/short write changed image')
    altered=copy.deepcopy(doc)
    next(r for r in altered['records'] if r['owner']=='cut/host_sample')['value']='0000000000000002'
    second=encode('fsckpt',altered); other=case/'second.load'; staging(second,other)
    execute('replacement',path=other)
    require(destination.read_bytes()==second,'regular-file replacement differs')
    faults=[]
    for fault in ('directory-open','preflight-sync','temporary-open','write','zero-write',
                  'partial-write-error','file-sync','file-close','rename','directory-sync','directory-close'):
        destination.write_bytes(b'old destination\n')
        visible=fault in ('directory-sync','directory-close')
        text=execute(fault,fault=fault,expected=3 if visible else 1)
        require(f'REJECT published={int(visible)}' in text,'incorrect publication status')
        if fault=='zero-write':
            require('write checkpoint returned zero bytes' in text,'zero write has a misleading errno diagnostic')
        require(destination.read_bytes()==(image if visible else b'old destination\n'),
                'fault violated atomic replacement')
        require(not list(case.glob('.fsckpt.pending-*')),'ordinary fault left a pending file')
        faults.append(fault)
    # Each semantic/staging mutation must reject before temporary creation and
    # before even opening the destination directory (which is deliberately absent).
    variants=[('empty',b''),('trailing',good+b'x'),('nul',good+b'\0'),
              ('bad-native-schema',good.replace(runtime['native_owners'][0]['schema'].encode(),b'wrong',1)),
              ('bad-generated-path',good.replace((layout['root']+'.'+counter['hierarchy']).encode(),b'unknown',1)),
              ('bad-target-cycle',good.replace(b' 9 ',b' 10 ',1)),
              ('noncanonical-number',good.replace(b' 9 ',b' 09 ',1)),
              ('whitespace',b' '+good),('missing-last-byte',good[:-1])]
    # Recalculate section lengths independently for each changed row, so the
    # rejection exercises owner/shape/padding/phase validation, not framing.
    lines=good.decode().splitlines(keepends=True)
    gi=next(i for i,l in enumerate(lines) if l.startswith('GENERATED '))
    hi=next(i for i,l in enumerate(lines) if l.startswith('HARNESS '))
    def mutate(index,field,value):
        changed=lines.copy();parts=changed[index].split();parts[field]=value
        changed[index]=' '.join(parts)+'\n'
        changed[gi]=f'GENERATED {len("".join(changed[gi+1:hi]).encode())}\n'
        changed[hi]=f'HARNESS {len("".join(changed[hi+1:]).encode())}\n'
        return ''.join(changed).encode()
    for index in range(1,gi):
        parts=lines[index].split()
        for field,value in ((1,'unsupported'),(2,'unsupported'),(3,'0'),(3,'18446744073709551616'),
                            (4,parts[4][:-1]+'x')):
            variants.append((f'native-{index}-{field}-{value[:12]}',mutate(index,field,value)))
    for section,start,end in (('generated',gi+2,hi),('harness',hi+2,len(lines))):
        for index in range(start,end):
            parts=lines[index].split()
            for field,value in ((0,'unsupported'),(1,str(int(parts[1])+1)),
                                (len(parts)-1,parts[-1][:-1]+'x')):
                variants.append((f'{section}-{index}-{field}',mutate(index,field,value)))
            if section=='generated':variants.append((f'depth-{index}',mutate(index,2,str(int(parts[2])+1))))
            if int(parts[1])%4:
                variants.append((f'padding-{index}',mutate(index,len(parts)-1,'f'+parts[-1][1:])))
            if parts[0].endswith(('.O','.reset','.fin')):
                variants.append((f'high-clock-reset-finish-{index}',mutate(index,len(parts)-1,'1')))
            if section=='generated' and int(parts[2])>1 and int(parts[1])%4:
                digits=(int(parts[1])+3)//4;value=parts[-1];at=len(value)-digits
                variants.append((f'final-word-padding-{index}',mutate(index,3,value[:at]+'f'+value[at+1:])))
    for index in (0,gi+1,hi+1):
        for field,value in ((0,'wrong-magic'),(1,'0'*64),(len(lines[index].split())-1,'0')):
            variants.append((f'header-{index}-{field}',mutate(index,field,value)))
    rejected=[]
    for label,bad in variants:
        path=case/(label+'.load');path.write_bytes(bad)
        destination.write_bytes(b'old destination\n')
        text=execute(label,path=path,expected=1)
        require('REJECT validation=1' in text and destination.read_bytes()==b'old destination\n',
                'bad snapshot reached publication')
        require(not list(case.glob('.fsckpt.pending-*')),'bad snapshot created a temporary')
        text=execute(label+'-before-open',path=path,dest=case/'absent-parent/checkpoint',expected=1)
        require('REJECT validation=1' in text,'bad snapshot accessed output directory before validation')
        rejected.append(label)
    special=case/'special';special.mkdir()
    victim=special/'victim';victim.write_bytes(b'unchanged\n')
    for name in ('symlink','fifo','directory','missing-parent'):
        path=special/name
        if name=='symlink':path.symlink_to(victim)
        elif name=='fifo':os.mkfifo(path)
        elif name=='directory':path.mkdir()
        else:path=path/'checkpoint'
        text=execute('special-'+name,dest=path,expected=1)
        require('REJECT published=0' in text and victim.read_bytes()==b'unchanged\n','special destination followed')
    kill_results=[]
    for fault in ('kill-partial','kill-file-sync','kill-rename'):
        killed_dir=case/fault;killed_dir.mkdir();dest=killed_dir/'checkpoint.fsckpt';dest.write_bytes(second)
        execute(fault,dest=dest,fault=fault,expected=-signal.SIGKILL)
        require(dest.read_bytes()==(image if fault=='kill-rename' else second),'killed writer exposed partial image')
        pending=list(killed_dir.glob('.fsckpt.pending-*'))
        require(len(pending)==(0 if fault=='kill-rename' else 1),'wrong killed-writer pending membership')
        kill_results.append(dict(fault=fault,pending=[str(p) for p in pending]))
    # Concurrent actual native writers plus readers opening each destination
    # once must see a complete old or new image throughout replacement.
    concurrent=case/'concurrent';concurrent.mkdir(); dest=concurrent/'checkpoint';dest.write_bytes(image)
    def writer(i):
        run([executable,snapshot if i%2 else other,dest,'none'],concurrent/f'writer-{i}.log')
    observations=0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(writer,i) for i in range(16)]
        while not all(f.done() for f in futures):
            data=dest.read_bytes();require(data in (image,second),'reader observed partial publication')
            packed.decode_aggregate(data,build,runtime,generated,layout);observations+=1
        for future in futures:future.result()
    require(observations>0 and not list(concurrent.glob('.fsckpt.pending-*')),'concurrent publication incomplete')
    for name,value in [('runtime',runtime),('generated',generated),('layout',layout),('build',build)]:
        (case/(name+'.json')).write_bytes(canonical(value))
    (case/'oracle.fsckpt').write_bytes(image)
    summary=dict(sanitizers='ASan/UBSan',python_container_byte_comparison=True,syscall_faults=faults,
                 staging_rejections=rejected,special_destinations=4,killed_writers=kill_results,
                 concurrent_writers=16,complete_reader_observations=observations,invocation=str(case))
    (case/'summary.json').write_bytes(canonical(summary));(out/'summary.json').write_bytes(canonical(summary))
    print(f'PASS: native encoder byte-identical to Python; {len(faults)} syscall faults, {len(rejected)} staging rejections, 4 special destinations, 3 kills and 16 concurrent writers')


if __name__=='__main__':main()
