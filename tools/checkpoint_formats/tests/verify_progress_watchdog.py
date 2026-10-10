"""Native independent thread, deadline/capture boundaries and public parser."""
import argparse
import os
from pathlib import Path
import tempfile

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True); args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    case=Path(tempfile.mkdtemp(prefix='invocation-',dir=args.out.resolve()))
    source=ROOT/'tools/checkpoint_formats'
    run([os.environ['CXX'],'-std=c++20','-g','-no-pie','-fsanitize=address,undefined',
         '-fno-omit-frame-pointer',f'-I{source}',f'-I{ROOT}/sims/firesim/sim/midas/src/main/cc',
         source/'progress_watchdog.cc',source/'tests/progress_watchdog_native.cc',
         '-pthread','-o',case/'verify'],case/'build.log')
    results=[]
    for mode,reason in [('policy',None),('healthy',None),('host','host_progress_stall'),
                        ('cycle','target_cycle_stall'),('capture','capture_stall'),
                        ('sample-lock','host_progress_stall'),('target','target_progress_stall'),
                        ('target-healthy',None)]:
        text=run([case/'verify',mode],case/(mode+'.log'),expected=1 if reason else 0)
        require((f'reason={reason}' in text) if reason else 'PASS:' in text,'wrong deadline classification')
        require('AddressSanitizer' not in text and 'runtime error:' not in text,'sanitizer failure')
        results.append(dict(mode=mode,reason=reason,log=str(case/(mode+'.log'))))
    (args.out/'summary.json').write_bytes(canonical(dict(invocation=str(case),results=results,
        sanitizers='ASan/UBSan',capture_time_excluded_but_bounded=True,
        cycle_stall_with_live_host_samples=True,semantic_stall_with_advancing_cycles=True)))
    print('PASS: independent host/cycle monitor, semantic target-cycle deadline, bounded capture exclusion and public parser')


if __name__=='__main__': main()
