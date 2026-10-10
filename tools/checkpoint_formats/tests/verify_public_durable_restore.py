"""Full-size corruption, compatibility and dispatch checks of public restore."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile

from tools.checkpoint_formats.codec import canonical, decode, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import run


def verify_rejections(common,out,build,runtime,manifest,layout):
    good=(out/'default/cut-3/capture.fsckpt').read_bytes()
    doc=decode(good,'fsckpt',build)
    def envelope(payload):
        header=good[:8]+struct.pack('>Q',len(payload))
        return header+payload+hashlib.sha256(header+payload).digest()
    cases=[]
    def change(name,fn,native=False):
        altered=copy.deepcopy(doc);fn(altered)
        cases.append((name,envelope(canonical(altered)),native))
    def row(d,owner):return next(r for r in d['records'] if r['owner']==owner)
    for owner in runtime['native_owners']:
        def truncate(d,name=owner['owner']):
            r=row(d,'host/'+name);r['value']=r['value'][:-2];r['width']-=8
        change('native-'+owner['owner'].replace('/','-'),truncate,True)
    generated=manifest['state'][-1]
    harness=layout['records'][0]
    change('late-generated-shape',lambda d:row(d,'generated-entry/'+generated['hierarchy']).update(
        width=4*((generated['width']+3)//4)*generated['depth']+4,
        value=row(d,'generated-entry/'+generated['hierarchy'])['value']+'0'))
    change('late-harness-shape',lambda d:row(d,'harness/'+harness['owner']).update(
        width=harness['width']+4,value='0'+row(d,'harness/'+harness['owner'])['value']))
    change('target-cycle',lambda d:d.update(target_cycle=d['target_cycle']+1))
    change('missing-owner',lambda d:d['records'].pop())
    change('unknown-owner',lambda d:d['records'][-1].update(owner='zz/unknown'))
    change('duplicate-owner',lambda d:d['records'].append(d['records'][-1]))
    change('unsorted-owners',lambda d:d['records'].reverse())
    for key in build:change('build-'+key,lambda d,k=key:d['build'].__setitem__(k,'0'*64))
    fifo=next(e for e in manifest['state'] if e['kind']=='memory' and e['width']%4 and e['depth']>1)
    def padding(d):
        r=row(d,'generated-entry/'+fifo['hierarchy']);digits=(fifo['width']+3)//4
        v=r['value'];index=len(v)-digits;r['value']=v[:index]+'f'+v[index+1:]
    change('final-memory-word-padding',padding)
    cases.extend([('truncated',good[:-1],False),('trailing',good+b'\0',False),
                  ('checksum',good[:-1]+bytes([good[-1]^1]),False),
                  ('duplicate-json-key',envelope(good[16:-32].replace(b'"format_version":1',
                                        b'"format_version":1,"format_version":1')),False)])
    results=[]
    for name,data,native in cases:
        case=out/'public-negative'/name;case.mkdir(parents=True,exist_ok=True)
        path=case/'rejected.fsckpt';path.write_bytes(data)
        text=run([*common,f'+fs-restore={path}'],case/'run.log',case,expected=1)
        require(path.read_bytes()==data,'rejected public checkpoint changed')
        if native:
            require('FS_DURABLE_RESTORE_ERROR' in text and 'native_loads=0 deposits=0' in text
                    and 'PRODUCTION_REJECTION zero_edges=1' in text,'native prevalidation advanced or loaded state')
        else:
            require('FS_CHECKPOINT_ENTRY_ERROR' in text and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text,
                    'container rejection reached platform construction')
        require('PRODUCTION_AGGREGATE_LOADED' not in text and 'PRODUCTION_BOOTSTRAP' not in text,
                'rejected public restore bootstrapped')
        results.append(dict(name=name,stage='native' if native else 'container',log=str(case/'run.log')))
    first=out/'default/cut-3/capture.fsckpt';digest=hashlib.sha256(first.read_bytes()).hexdigest()
    runtime_results=[]
    for label,extra in [('memory',['+memsize=4194305']),('horizon',['+max-cycles=1000001']),
                        ('host-delay',['+fuzz-host-timing=2']),('seed',['+fuzz-seed=1'])]:
        case=out/'public-runtime-negative'/label;case.mkdir(parents=True,exist_ok=True)
        keys={v.split('=')[0] for v in extra};configured=[a for a in common if str(a).split('=')[0] not in keys]+extra
        text=run([*configured,f'+fs-restore={first}'],case/'run.log',case,expected=1)
        require('native_loads=0 deposits=0' in text and 'PRODUCTION_REJECTION zero_edges=1' in text,
                'configuration mismatch loaded state/advanced time');runtime_results.append(label)
    options=[['+fs-checkpoint'],['+fs-restore'],['+fs-checkpoint='],['+fs-restore='],
             ['+fs-checkpoint-preflight=1'],['+fs-checkpoint-typo=x'],['+fs-restore-typo=x'],
             [f'+fs-restore={first}',f'+fs-restore={first}'],
             [f'+fs-restore={first}',f'+fs-checkpoint={out/"absent.fsckpt"}'],
             [f'+fs-checkpoint={out/"absent.fsckpt"}'],
             [f'+test-aggregate={out/"untrusted.load"}'],
             [f'+fs-restore={first}','+profile-interval=250000'],
             [f'+fs-restore={first}','+fs-driver-cut=3'],
             [f'+fs-restore={first}','+loadmem=unbound'],
             [f'+fs-restore={out/"missing.fsckpt"}']]
    for index,request in enumerate(options):
        case=out/'public-dispatch-negative'/str(index);case.mkdir(parents=True,exist_ok=True)
        text=run([*common,*request],case/'run.log',case,expected=1)
        require('FS_CHECKPOINT_ENTRY_ERROR' in text and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text,
                'unsupported public request reached platform')
    special_inputs={}
    for name in ('symlink','fifo','directory'):
        case=out/'public-special-negative'/name;case.mkdir(parents=True,exist_ok=True)
        # A repeated verification must exercise fresh special files without
        # removing or following any previous run's fixture.
        path=Path(tempfile.mkdtemp(prefix='inputs-',dir=case))/'input'
        if name=='symlink':path.symlink_to(first)
        if name=='fifo':os.mkfifo(path)
        if name=='directory':path.mkdir()
        text=run([*common,f'+fs-restore={path}'],path.parent/'run.log',case,expected=1)
        require('FS_CHECKPOINT_ENTRY_ERROR' in text and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text,
                'special public input reached platform')
        special_inputs[name]=str(path)
    require(not (out/'absent.fsckpt').exists() and hashlib.sha256(first.read_bytes()).hexdigest()==digest,
            'public rejection modified checkpoint files')
    result=dict(public_restore_rejections=results,public_runtime_rejections=runtime_results,
                public_dispatch_rejections=len(options),public_special_file_rejections=3,
                public_special_file_inputs=special_inputs,
                malformed_processes=[],runtime_compatibility_rejections=[])
    (out/'public-rejection-summary.json').write_bytes(canonical(result))
    print(f'PASS: {len(cases)+len(runtime_results)+len(options)+3} full-size public restore rejections',flush=True)
    return result
