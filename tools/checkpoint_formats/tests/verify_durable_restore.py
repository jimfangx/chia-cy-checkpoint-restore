"""ASan/UBSan public consumer differential check against the Python oracle."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile

from tools.checkpoint_formats import aggregate, aggregate_packed as packed
from tools.checkpoint_formats.codec import canonical, decode, encode, require
from tools.checkpoint_formats.durable_restore import prepare_durable_loader
from tools.checkpoint_formats.tests.test_aggregate_packed import PackedAggregateTest
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True); args=parser.parse_args()
    out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    build,runtime,generated,layout,data=PackedAggregateTest().fixture(out)
    doc=decode(data,'fsckpt',build)
    counter=next(e for e in generated['state'] if e['kind']=='register')
    counter['width']=64
    runtime=packed.runtime_manifest(runtime['profile'],generated,layout,runtime['native_owners'],
                                    runtime['native_build_hash'],counter['hierarchy'])
    prepare_durable_loader(runtime,generated,layout,out)
    source=ROOT/'tools/checkpoint_formats'
    run([os.environ.get('CXX','/usr/bin/g++-13'),'-std=c++20','-g','-fsanitize=address,undefined',
         '-fno-omit-frame-pointer','-no-pie',f'-I{out}',source/'durable_restore.cc',
         source/'tests/durable_restore_native.cc','-lcrypto','-o',out/'verify'],out/'build.log')
    build=aggregate.build_identity(runtime,generated,layout,out/'verify');doc['build']=build
    next(r for r in doc['records'] if r['owner']=='generated-entry/'+counter['hierarchy']).update(width=64,value=f'{9:016x}')
    data=encode('fsckpt',doc); good=out/'checkpoint with spaces.fsckpt';good.write_bytes(data)
    packed.prepare_aggregate_restore(data,build,runtime,generated,layout,out/'oracle.load')
    run([out/'verify',good,out/'actual.load'],out/'valid.log')
    require((out/'actual.load').read_bytes()==(out/'oracle.load').read_bytes(),'C++ consumer differs from Python oracle')
    variants=[('truncated',data[:-1]),('trailing',data+b'\0'),('integrity',data[:40]+bytes([data[40]^1])+data[41:])]
    def envelope(payload):
        header=data[:8]+struct.pack('>Q',len(payload));return header+payload+hashlib.sha256(header+payload).digest()
    for name,payload in [('duplicate-key',data[16:-32].replace(b'"format_version":1',b'"format_version":1,"format_version":1')),
                         ('whitespace',b' '+data[16:-32]),
                         ('unordered-keys',json.dumps(doc,separators=(',',':'),sort_keys=False).encode()),
                         ('negative-zero',data[16:-32].replace(b'"target_cycle":9',b'"target_cycle":-0')),
                         ('floating-version',data[16:-32].replace(b'"format_version":1',b'"format_version":1.0'))]:
        variants.append((name,envelope(payload)))
    changes=[('cycle',lambda d:d.update(target_cycle=10)),('overflow',lambda d:d.update(target_cycle=2**64)),
             ('negative',lambda d:d.update(target_cycle=-1)),('boolean',lambda d:d.update(target_cycle=True)),
             ('extra-key',lambda d:d.update(extra=1)),('missing-member',lambda d:d['records'].pop()),
             ('duplicate-owner',lambda d:d['records'].append(d['records'][-1])),
             ('unsorted',lambda d:d['records'].reverse())]
    for field in build:
        changes.append(('build-'+field,lambda d,f=field:d['build'].__setitem__(f,'0'*64)))
    for index,row in enumerate(doc['records']):
        changes.append((f'owner-{index}',lambda d,i=index:d['records'][i].update(owner='unknown/'+str(i))))
        changes.append((f'width-{index}',lambda d,i=index:d['records'][i].update(width=d['records'][i]['width']+1)))
    fifo=next(i for i,r in enumerate(doc['records']) if r['owner'].endswith('Top.fifo'))
    changes += [('final-word-padding',lambda d:d['records'][fifo].update(value='001fff')),
                ('unknown-bits',lambda d:d['records'][fifo].update(value='00100x'))]
    for name,change in changes:
        altered=copy.deepcopy(doc);change(altered);variants.append((name,envelope(canonical(altered))))
    # Ensure this deliberately unsorted payload differs even though the fixture
    # dictionary happened to start with a canonical root order.
    variants=[(n,b) for n,b in variants if n!='unordered-keys']
    reversed_doc=dict(reversed(list(doc.items())))
    variants.append(('unordered-keys',envelope(json.dumps(reversed_doc,separators=(',',':')).encode())))
    rejected=[]
    for name,bad in variants:
        path=out/(name+'.fsckpt');path.write_bytes(bad)
        output=out/'unchanged.load';output.write_bytes(b'unchanged\n')
        text=run([out/'verify',path,output],out/(name+'.log'),expected=1)
        require('REJECT no_publication=1' in text and output.read_bytes()==b'unchanged\n','failed consumer published state')
        rejected.append(name)
    # Retain earlier fixtures and diagnostics when the loop repeats --out.
    # In particular, never follow or unlink a stale symlink to make a rerun pass.
    special=Path(tempfile.mkdtemp(prefix='special-files-',dir=out))
    special_inputs={}
    for name in ('symlink','fifo','directory','missing','oversized'):
        path=special/name
        if name=='symlink':path.symlink_to(good)
        if name=='fifo':os.mkfifo(path)
        if name=='directory':path.mkdir()
        if name=='oversized':
            with path.open('wb') as stream:stream.truncate(256*1024*1024+1)
        output=out/'unchanged.load';output.write_bytes(b'unchanged\n')
        text=run([out/'verify',path,output],special/(name+'.log'),expected=1)
        require('REJECT no_publication=1' in text and output.read_bytes()==b'unchanged\n',
                'special file accepted or rejection published state')
        special_inputs[name]=str(path);rejected.append(name)
    summary=dict(sanitizers='ASan/UBSan',python_staging_byte_comparison=True,rejections=rejected,
                 special_file_inputs=special_inputs)
    (out/'summary.json').write_bytes(canonical(summary))
    print(f'PASS: native durable consumer matches Python oracle; {len(rejected)} ASan/UBSan rejections')


if __name__=='__main__':main()
