"""Retained production replay through a late target hang with advancing cycles.

The optional compiled verification observer samples a fixed control file once
at cycle 600000 and suppresses the fuzzer's response input. Production polling
and detection use the audited register, never the observer or port activity.
Run this scope alone: the control file belongs to this production executable.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from tools.checkpoint_formats.aggregate_packed import decode_aggregate
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.rolling import NativeRollingHistory
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('production','live-history','reference-production','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    require(os.environ.get('VCS_HOME')=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1','source vcs-env.sh LAST')
    production=args.production.resolve()
    inputs=json.loads((production/'native-build-inputs.json').read_text())
    require(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in inputs['sources'].items()),
            'production executable predates current sources')
    build,manifest,generated,layout=[json.loads((production/n).read_text()) for n in
        ('aggregate-build.json','runtime-manifest.json','generated-manifest.json','harness-layout.json')]
    inventory=json.loads((production/'target-progress-inventory.json').read_text())
    live=json.loads((args.live_history/'latest.json').read_text())
    store=NativeRollingHistory(Path(live['invocation'])/'periodic/history',retention=2,build=build,
                              manifest=manifest,generated=generated,layout=layout)
    record,image=store.select(before_target_cycle=600000)
    require(record['target_cycle']==500000,'missing retained image before causal hang')
    doc=decode_aggregate(image,build,manifest,generated,layout)
    host_sample=int(next(r['value'] for r in doc['records'] if r['owner']=='cut/host_sample'),16)
    native={r['owner'][5:]:r['value'] for r in doc['records'] if r['owner'].startswith('host/')}
    remaining=int(next(r['value'] for r in doc['records']
                       if r['owner']=='generated-entry/'+inventory['path'].removeprefix('emul.')),16)
    reference=(args.reference_production/'default/reference/ports.trace').read_bytes()
    expected=b''.join(reference.splitlines(keepends=True)[host_sample:])
    causal_prefix=b''.join(row for row in expected.splitlines(keepends=True) if int(row.split()[0])<=600000)
    require(len(causal_prefix)>0,'empty pre-fault continuation')
    control=production/'inject-target-hang.control'
    require(control.read_bytes()==b'0\n','another target-fault verification is active')
    args.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='invocation-',dir=args.out.resolve()))
    print('TARGET_PROGRESS_VCS_VERIFICATION_OUTPUT '+str(out),flush=True)
    common=[production/'simv','-no_save','+vcs+initreg+0','+vcs+initmem+0',
            '+memsize=4194304','+max-cycles=1000000']
    target='+fs-checkpoint-target-timeout-cycles='
    capture='+fs-checkpoint-capture-timeout-ms='
    invalid=[[target+v,capture+'600000'] for v in ('','0','-1','+1','1x','18446744073709551616')]
    invalid += [[target+'10000'],[target+'10000',target+'10000',capture+'600000'],
                ['+fs-checkpoint-target-timeout-ms=10000',capture+'600000']]
    cp=out/'retained.fsckpt'; cp.write_bytes(image)
    for i,options in enumerate(invalid):
        trace=out/f'invalid-{i}.trace'
        text=run([*common,'+fs-restore='+str(cp),'+target_port_trace='+str(trace),*options],
                 out/f'invalid-{i}.log',out,expected=1)
        require('FS_CHECKPOINT_ENTRY_ERROR' in text and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text and
                'PRODUCTION_PRE_EDGE' not in text and
                (not trace.exists() or trace.stat().st_size==0),
                'invalid target watchdog constructed a platform or advanced trace')
    options=[target+'10000',capture+'600000','+fs-checkpoint-host-timeout-ms=5000',
             '+fs-checkpoint-cycle-timeout-ms=5000']
    results=[]
    hang_trace=None
    for kind in ('hang-original','hang-repeat','healthy'):
        directory=out/kind; directory.mkdir()
        trace=directory/'ports.trace'; readback=directory/'loaded-native.txt'; log=directory/'run.log'
        argv=[*common,'+fs-restore='+str(cp),'+target_port_trace='+str(trace),
              '+test-loaded-native='+str(readback),*options]
        try:
            if kind!='healthy':
                control.write_text('1\n')
            text=run(argv,log,directory,expected=0 if kind=='healthy' else 1)
        finally:
            control.write_text('0\n')
        require('PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in text and
                'PRODUCTION_BOOTSTRAP zero_edges=1' in text,'restore advanced before readback/bootstrap')
        require(dict(line.split() for line in readback.read_text().splitlines())==native,
                'restored native state differs from retained snapshot')
        armed=re.search(r'FS_CHECKPOINT_WATCHDOG_ARMED target_cycle=(\d+)',text)
        require(armed and 500000<=int(armed[1])<=500002,'monitor did not reinitialize at restored origin')
        actual=trace.read_bytes()
        result=dict(kind=kind,argv=[str(a) for a in argv],cwd=str(directory),log=str(log),
                    trace=str(trace),native_owners_compared=len(native),restored_remaining=remaining,
                    first_sample_cycle=int(armed[1]),rows=actual.count(b'\n'))
        if kind=='healthy':
            require('*** PASSED ***' in text and 'TEST_TARGET_HANG' not in text and actual==expected,
                    'healthy semantic watchdog continuation differs from full reference')
            result['full_reference_suffix_match']=True
        else:
            fault=re.search(r'TEST_TARGET_HANG target_cycle=(\d+) remaining=(\d+)',text)
            failure=re.search(r'FS_CHECKPOINT_WATCHDOG_FAILURE reason=target_progress_stall target_cycle=(\d+) '
                              r'samples=(\d+) captures=(\d+) capture_ns=(\d+) target_progress=(\d+)',text)
            require(fault and failure and int(fault[1])==600000 and
                    600000<int(failure[1])<=610002 and int(failure[2])>1 and
                    int(failure[5])==inventory['initialization_limit']+10000-int(fault[2]) and int(fault[2])>0,
                    'target cycles/completed work did not establish a semantic hang')
            require(actual.startswith(causal_prefix),'pre-fault retained continuation differs from reference')
            rows=actual.splitlines()
            require(int(rows[-1].split()[0])>600000 and len(rows[-1].split())==3,
                    'trace did not advance through the injected hang')
            if hang_trace is not None: require(actual==hang_trace,'repeated causal hang replay is not byte identical')
            hang_trace=actual
            result.update(fault_target_cycle=int(fault[1]),failure_target_cycle=int(failure[1]),
                          completed_transactions=int(failure[5])-inventory['initialization_limit'],
                          completed_initialization=inventory['initialization_limit'],failure_reason='target_progress_stall',
                          causal_prefix_bytes=len(causal_prefix),target_cycles_advance=True)
        results.append(result)
        (directory/'result.json').write_bytes(canonical(result))
    require(store.select(before_target_cycle=600000)==(record,image),'failure or restore mutated retained history')
    summary=dict(invocation=str(out),selected_checkpoint=record,progress_inventory=inventory,
                 results=results,configuration_rejections=len(invalid),
                 injected_fault='verification observer forces target response-valid low at cycle 600000',
                 repeated_hang_trace_byte_identical=True,production_semantic_watchdog=True,
                 physical_fpga_validated=False)
    (out/'summary.json').write_bytes(canonical(summary))
    (args.out/'latest.json').write_bytes(canonical(dict(invocation=str(out),summary=str(out/'summary.json'))))
    print('PASS: live-retained rewind reproduces late semantic target hang with advancing cycles; healthy replay matches')


if __name__=='__main__': main()
