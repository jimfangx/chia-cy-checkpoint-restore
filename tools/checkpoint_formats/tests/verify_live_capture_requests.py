"""Actual VCS live-capture dispatch and publication failure checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True); args=parser.parse_args()
    production=args.production.resolve(); out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    require(os.environ['VCS_HOME']=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1','source vcs-env.sh LAST')
    summary=json.loads((production/'summary.json').read_text())
    require(summary['native_live_capture_verified'] and len(summary['cases'])==5,'incomplete live continuations')
    sources=json.loads((production/'native-build-inputs.json').read_text())['sources']
    require(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in sources.items()),
            'live executable predates current sources')
    case=Path(tempfile.mkdtemp(prefix='invocation-',dir=out))
    common=[production/'simv','-no_save','+vcs+initreg+0','+vcs+initmem+0','+memsize=4194304','+max-cycles=1000000']
    sentinel=case/'output.fsckpt'; sentinel.write_bytes(b'preserve checkpoint\n')
    diagnostic=case/'diagnostic'
    cut=['+fs-driver-cut=3',f'+fs-driver-diagnostic={diagnostic}','+fs-driver-settled','+fs-driver-lowclock']
    request=f'+test-live-capture={sentinel}'
    good=production/'default/cut-3/capture.fsckpt'
    requests=[['+test-live-capture'],['+test-live-capture='],[request],
             [request,'+fs-driver-cut=3',f'+fs-driver-diagnostic={diagnostic}'],
             [request,*cut[:-1]],[request,request,*cut],
             [request,*cut,f'+fs-restore={good}'],[request,*cut,'+fs-checkpoint-preflight'],
             [request,*cut,f'+fs-checkpoint={sentinel}'],
             [request,*cut,'+fs-driver-cut=4'],[request,*cut,'+profile-interval=250000']]
    for i,options in enumerate(requests):
        text=run([*common,*options],case/f'dispatch-{i}.log',case,expected=1)
        require('FS_CHECKPOINT_ENTRY_ERROR' in text and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text,
                'invalid live capture request reached platform construction')
        require(sentinel.read_bytes()==b'preserve checkpoint\n' and not diagnostic.exists(),
                'dispatch rejection touched an output')
    special=[]
    for kind in ('symlink','fifo','directory','missing-directory'):
        directory=case/kind; directory.mkdir()
        destination=directory/'output.fsckpt'; diag=directory/'diagnostic'
        if kind=='symlink': destination.symlink_to(sentinel)
        elif kind=='fifo': os.mkfifo(destination)
        elif kind=='directory': destination.mkdir()
        else: destination=directory/'absent/output.fsckpt'
        before=hashlib.sha256(sentinel.read_bytes()).hexdigest()
        text=run([*common,f'+test-live-capture={destination}','+fs-driver-cut=3',
                  f'+fs-driver-diagnostic={diag}','+fs-driver-settled','+fs-driver-lowclock'],
                 directory/'run.log',directory,expected=1)
        require('FS_DURABLE_LIVE_CAPTURE_ERROR' in text and 'FS_DURABLE_LIVE_CAPTURE_PUBLISHED' not in text,
                'invalid live destination was published')
        require('unexpected termination' not in text and 'Dumping VCS' not in text and
                'Segmentation fault' not in text,'live rejection triggered VCS crash/exit handlers')
        require(hashlib.sha256(sentinel.read_bytes()).hexdigest()==before and not diag.exists() and
                not list(directory.glob('.fsckpt.pending-*')),'live publication failure changed output')
        special.append(kind)
    result=dict(invocation=str(case),dispatch_rejections=len(requests),special_destinations=special,
                live_publication_failures_preserved_output=True)
    (out/'summary.json').write_bytes(canonical(result))
    print(f'PASS: {len(requests)} actual-entry live dispatch rejections and four complete live publication failures',flush=True)


if __name__=='__main__': main()
