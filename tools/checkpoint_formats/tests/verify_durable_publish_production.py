"""Full FCFS/FASED snapshot encoding oracle (no live capture/restore claim)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from tools.checkpoint_formats import aggregate, aggregate_packed as packed
from tools.checkpoint_formats.codec import canonical, decode, encode, require
from tools.checkpoint_formats.durable_restore import prepare_durable_loader
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    production=args.production.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    case=Path(tempfile.mkdtemp(prefix='invocation-',dir=out))
    runtime=json.loads((production/'runtime-manifest.json').read_text())
    generated=json.loads((production/'generated-manifest.json').read_text())
    layout=json.loads((production/'harness-layout.json').read_text())
    original=json.loads((production/'aggregate-build.json').read_text())
    capture=production/'default/cut-699275/capture.fsckpt'
    initial=hashlib.sha256(capture.read_bytes()).hexdigest()
    doc=packed.decode_aggregate(capture.read_bytes(),original,runtime,generated,layout)
    require(len(generated['state'])==2856 and sum(e['depth'] for e in generated['state'])==13507456
            and len(layout['records'])==29 and len(runtime['native_owners'])==17,'incomplete production inventory')
    prepare_durable_loader(runtime,generated,layout,case)
    source=ROOT/'tools/checkpoint_formats'
    run([os.environ.get('CXX','/usr/bin/g++-13'),'-std=c++20','-g','-fsanitize=address,undefined',
         '-fno-omit-frame-pointer','-no-pie',f'-I{case}',source/'durable_restore.cc',source/'durable_publish.cc',
         source/'tests/durable_publish_native.cc','-lcrypto',
         *['-Wl,--wrap='+name for name in ('open','openat','write','fsync','close','renameat')],
         '-o',case/'verify'],case/'build.log')
    # The encoder runs in a standalone sanitizer executable. Bind its actual
    # executable hash, keeping the real snapshot's complete opaque payloads.
    # This artifact is an encoding oracle; its old runtime/compatibility payload
    # deliberately cannot authorize a restore into this standalone executable.
    build=aggregate.build_identity(runtime,generated,layout,case/'verify');doc['build']=build
    image=encode('fsckpt',doc);snapshot=case/'snapshot.load'
    packed.prepare_aggregate_restore(image,build,runtime,generated,layout,snapshot)
    destination=case/'encoded.fsckpt';destination.write_bytes(b'preserve\n')
    run([case/'verify',snapshot,destination,'none'],case/'valid.log')
    require(destination.read_bytes()==image,'full production native encoder differs from Python oracle')
    packed.decode_aggregate(destination.read_bytes(),build,runtime,generated,layout)
    failures=[]
    for fault in ('write','partial-write-error','file-sync','rename','directory-sync'):
        destination.write_bytes(b'preserve\n')
        visible=fault=='directory-sync'
        text=run([case/'verify',snapshot,destination,fault],case/(fault+'.log'),expected=3 if visible else 1)
        require(f'REJECT published={int(visible)}' in text and
                destination.read_bytes()==(image if visible else b'preserve\n'),'full-size publication fault changed status/content')
        require(not list(case.glob('.fsckpt.pending-*')),'full-size ordinary error left pending output')
        failures.append(fault)
    require(hashlib.sha256(capture.read_bytes()).hexdigest()==initial,'production input modified')
    (case/'oracle.fsckpt').write_bytes(image)
    summary=dict(sanitizers='ASan/UBSan',generated_entries=2856,generated_words=13507456,
                 harness_records=29,native_owners=17,container_bytes=len(image),
                 python_container_byte_comparison=True,full_size_syscall_faults=failures,
                 production_input_sha256=initial,production_input=str(capture),
                 live_capture_verified=False,restore_acceptance_claimed=False,invocation=str(case))
    (case/'summary.json').write_bytes(canonical(summary));(out/'summary.json').write_bytes(canonical(summary))
    print('PASS: native full-production encoder matches Python for every generated/harness/native byte; five full-size syscall failures (encoding oracle only)')


if __name__=='__main__':main()
