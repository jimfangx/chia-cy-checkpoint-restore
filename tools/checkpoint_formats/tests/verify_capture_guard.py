"""ASan/UBSan real worker guard checks at and outside the settled cut."""
import argparse
import os
from pathlib import Path
import tempfile

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True); args=parser.parse_args()
    out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    case=Path(tempfile.mkdtemp(prefix='invocation-',dir=out))
    cc=ROOT/'sims/firesim/sim/midas/src/main/cc'
    source=ROOT/'tools/checkpoint_formats/tests/dispatcher_capture_guard.cc'
    sources=[source,*[cc/p for p in (
        'core/simif.cc','core/simulation.cc','core/widget_registry.cc','core/widget.cc','core/stream_engine.cc',
        'core/bridge_driver.cc','core/driver_boundary_diagnostic.cc','emul/simif_emul.cc','emul/mm.cc','emul/mmio.cc',
        'emul/qsfp.cc','emul/host_timing.cc','bridges/master.cc','bridges/clock.cc','bridges/loadmem.cc')]]
    run([os.environ['CXX'],'-std=c++20','-g','-no-pie','-fsanitize=address,undefined',
         '-fno-omit-frame-pointer','-DVCS',f'-I{cc}',*sources,'-pthread','-lgmp','-o',case/'verify'],case/'build.log')
    text=run([case/'verify',case],case/'run.log')
    require('PASS: live capture guard cuts=1' in text and 'unchanged_native=3 added_edges=0' in text,
            'capture guard did not preserve native owners and edge count')
    (out/'summary.json').write_bytes(canonical(dict(invocation=str(case),settled_cuts=1,
        unchanged_native_owners=3,added_edges=0,sanitizers='ASan/UBSan')))
    print('PASS: real parked-worker capture guard, unsupported topology and unchanged native state',flush=True)


if __name__=='__main__': main()
