"""Sanitized complete live collector oracle and fail-closed adapter checks."""
import argparse
import copy
import hashlib
import os
from pathlib import Path
import tempfile

from tools.checkpoint_formats import aggregate, aggregate_packed as packed
from tools.checkpoint_formats.codec import canonical, decode, encode, require
from tools.checkpoint_formats.generated_restore import prepare_generated_loader
from tools.checkpoint_formats.harness_restore import prepare_harness_loader
from tools.checkpoint_formats.tests.test_aggregate_packed import PackedAggregateTest
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    case = Path(tempfile.mkdtemp(prefix='invocation-', dir=out))
    build, runtime, generated, layout, data = PackedAggregateTest().fixture(case)
    doc = decode(data, 'fsckpt', build)
    counter = next(e for e in generated['state'] if e['kind']=='register')
    wide = copy.deepcopy(counter); wide['hierarchy']='Top.wide'
    gate = copy.deepcopy(counter)
    gate.update(hierarchy='Top.gate.O', module='BUFGCE', width=1, adapter='metasim-bufgce-v1')
    progress = copy.deepcopy(counter)
    progress.update(hierarchy='Top.progress',width=14)
    initialization = copy.deepcopy(counter)
    initialization.update(hierarchy='Top.initialization',width=20)
    for e in (wide, gate, progress, initialization):
        e['state_id']=hashlib.sha256(canonical(dict(hierarchy=e['hierarchy'],kind=e['kind'],
                                                   namespace='generated-simulator-state-v1'))).hexdigest()
    generated['instances'].append(dict(hierarchy='Top.gate',module='BUFGCE',implementation_sha256='b'*64))
    generated['state']=sorted([*generated['state'],wide,gate,progress,initialization],key=lambda e:e['state_id'])
    counter['width']=64
    runtime=packed.runtime_manifest(runtime['profile'],generated,layout,runtime['native_owners'],
                                    runtime['native_build_hash'],counter['hierarchy'])
    build=aggregate.build_identity(runtime,generated,layout,case/'simv'); doc['build']=build
    next(r for r in doc['records'] if r['owner']=='generated-entry/'+counter['hierarchy']).update(
        width=64,value=f'{9:016x}')
    doc['records'] += [dict(owner='generated-entry/Top.wide',width=260,value='1'+'f'*64),
                       dict(owner='generated-entry/Top.gate.O',width=4,value='0'),
                       dict(owner='generated-entry/Top.progress',width=16,value='1388'),
                       dict(owner='generated-entry/Top.initialization',width=20,value='80000')]
    for r in doc['records']:
        if r['owner'].startswith('harness/') and r['owner'] not in ('harness/emul.reset','harness/emul.fin'):
            r['value']=f'{(1<<r["width"])-1:0{(r["width"]+3)//4}x}'
    doc['records'].sort(key=lambda r:r['owner'])
    packed.prepare_aggregate_restore(encode('fsckpt',doc),build,runtime,generated,layout,case/'oracle.load')
    aggregate.prepare_aggregate_loader(runtime,case)
    with (case/'aggregate-restore-table.h').open('a') as table:
        table.write('\n#define AGGREGATE_TARGET_PROGRESS_PATH "emul.Top.progress"\n')
        table.write('#define AGGREGATE_TARGET_INITIALIZATION_PATH "emul.Top.initialization"\n')
    prepare_generated_loader(generated,layout['generated_build_hash'],case,'emul.Top')
    prepare_harness_loader(layout,case)
    source=ROOT/'tools/checkpoint_formats'
    cc=ROOT/'sims/firesim/sim/midas/src/main/cc'
    require(os.environ['VCS_HOME']=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    run([os.environ['CXX'],'-std=c++20','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',
         '-no-pie',f'-I{case}',f'-I{cc}',f'-I{os.environ["VCS_HOME"]}/include',
         source/'durable_capture.cc',source/'tests/durable_capture_native.cc','-o',case/'verify'],case/'build.log')
    run([case/'verify',case/'oracle.load',case/'actual.load','valid'],case/'valid.log')
    require((case/'actual.load').read_bytes()==(case/'oracle.load').read_bytes(),
            'live collector staging differs from independent Python oracle')
    run([case/'verify',case/'oracle.load',case/'unused','poll-valid'],case/'poll-valid.log')
    run([case/'verify',case/'oracle.load',case/'unused','poll-initialization'],case/'poll-initialization.log')
    poll_modes=['missing:emul.Top.progress','width:emul.Top.progress','kind:emul.Top.progress',
                'unknown:emul.Top.progress','padding:emul.Top.progress','range',
                'high:emul.clock','high:emul.Top.gate.O']
    poll_modes += [kind+':emul.Top.initialization' for kind in ('missing','width','kind','unknown','padding')]
    poll_modes += ['initialization-range','bad-epoch']
    for i,mode in enumerate(poll_modes):
        text=run([case/'verify',case/'oracle.load',case/'unused','poll-'+mode],case/f'poll-negative-{i}.log',expected=1)
        require('REJECT' in text and 'FIXTURE ERROR' not in text,'target-progress sampler failed to reject')
    modes=['missing-owner','extra-owner','order','alias','null','schema','empty-payload',
           'validator','native-change','schema-change','cross-owner-change','rtl-side-effect','unsupported-harness']
    paths=[]
    for e in generated['state']:
        for i in range(e['depth']):
            paths.append(('emul.'+e['hierarchy']+(f'[{i}]' if e['kind']=='memory' else ''),e['width']))
    paths += [(r['owner'],r['width']) for r in layout['records']]
    for path,width in paths:
        modes += [kind+':'+path for kind in ('missing','width','kind','unknown','changed')]
        if width%32: modes.append('padding:'+path)
    for path in ('emul.Top.clock','emul.Top.gate.I','emul.clock'):
        modes += [kind+':'+path for kind in ('missing','width','unknown','high')]
    modes += ['high:'+p for p in ('emul.Top.gate.O','emul.reset','emul.fin')]
    for index,mode in enumerate(modes):
        sentinel=case/'preserved.load'; sentinel.write_bytes(b'preserve output\n')
        text=run([case/'verify',case/'oracle.load',sentinel,mode],case/f'negative-{index}.log',expected=1)
        require('REJECT' in text and sentinel.read_bytes()==b'preserve output\n',
                'live capture rejection changed output')
    summary=dict(invocation=str(case),python_staging_byte_comparison=True,
                 rejections=modes,semantic_sampler_rejections=poll_modes,
                 sanitizers='ASan/UBSan',real_vcs_validation=False)
    (out/'summary.json').write_bytes(canonical(summary))
    print(f'PASS: complete live snapshot matches Python; {len(modes)} fail-closed native/VPI checks',flush=True)


if __name__=='__main__': main()
