"""Production monitor detects a late main-thread stall in retained VCS replay.

PTRACE_SEIZE/INTERRUPT parks only the VCS main thread, leaving the independent
monitor runnable. There is no test injection code or watchdog in the verifier.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

from tools.checkpoint_formats.aggregate_packed import decode_aggregate
from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.durable import atomic_output
from tools.checkpoint_formats.rolling import NativeRollingHistory
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production',type=Path,required=True)
    parser.add_argument('--live-history',type=Path,required=True)
    parser.add_argument('--initial-live-capture',type=Path,
                        help='Completed initial live run; remaining history regressions may run independently')
    parser.add_argument('--reference-production',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True); args=parser.parse_args()
    require(os.environ.get('VCS_HOME')==_toolchain.VCS_HOME,'source vcs-env.sh LAST')
    production=args.production.resolve()
    sources=json.loads((production/'native-build-inputs.json').read_text())['sources']
    require(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in sources.items()),
            'production executable predates current sources')
    build,manifest,generated,layout=[json.loads((production/n).read_text()) for n in
        ('aggregate-build.json','runtime-manifest.json','generated-manifest.json','harness-layout.json')]
    if args.initial_live_capture:
        initial=args.initial_live_capture.resolve(); live_out=initial.parent
        text=(initial/'run.log').read_text()
        argv=json.loads(next(line[5:] for line in text.splitlines() if line.startswith('argv=')))
        require(text.endswith('exit=0\n') and '*** PASSED ***' in text and
                Path(argv[0]).resolve()==(production/'simv').resolve() and
                '+fs-checkpoint-host-timeout-ms=1000' in argv and
                '+fs-checkpoint-cycle-timeout-ms=1000' in argv and
                len(re.findall('FS_CHECKPOINT_WATCHDOG_CAPTURE_ACCOUNTED',text))==3 and
                len(json.loads((initial/'observations.json').read_text()))==3,
                'initial live run has not completed monitored capture/retention')
        live=dict(summary=str(initial/'observations.json'))
    else:
        live=json.loads((args.live_history/'latest.json').read_text())
        live_out=Path(live['invocation']); summary=json.loads(Path(live['summary']).read_text())
        require(summary['production_watchdog_sampling'] and summary['watchdog_ms']>0,
                'live publication did not exercise watchdog capture accounting')
    store=NativeRollingHistory(live_out/'periodic/history',retention=2,build=build,manifest=manifest,
                               generated=generated,layout=layout)
    record,image=store.select(before_target_cycle=600000)
    require(record['target_cycle']==500000,'expected retained image before injected late stall')
    doc=decode_aggregate(image,build,manifest,generated,layout)
    host_sample=int(next(r['value'] for r in doc['records'] if r['owner']=='cut/host_sample'),16)
    reference=(args.reference_production/'default/reference/ports.trace').read_bytes()
    expected=b''.join(reference.splitlines(keepends=True)[host_sample:])
    native={r['owner'][5:]:r['value'] for r in doc['records'] if r['owner'].startswith('host/')}
    args.out.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='invocation-',dir=args.out.resolve()))
    print('WATCHDOG_VCS_VERIFICATION_OUTPUT '+str(out),flush=True)
    common=[production/'simv','-no_save','+vcs+initreg+0','+vcs+initmem+0',
            '+memsize=4194304','+max-cycles=1000000']
    host='+fs-checkpoint-host-timeout-ms='
    cycle='+fs-checkpoint-cycle-timeout-ms='
    capture='+fs-checkpoint-capture-timeout-ms='
    # Invalid controls cannot construct a platform, open a trace, or touch an
    # existing retained history. Also check restore during initial reset.
    bad=[]
    for key in (host,cycle,capture):
        for value in ('','0','-1','+1','1x','9223372036855','18446744073709551616'):
            bad.append([key+value])
    bad += [[host+'1000'],[capture+'600000'],[host+'1000',capture+'600000',host+'1000'],
            [cycle+'1000',capture+'600000',cycle+'1000'],[host+'1000',capture+'600000',capture+'600000'],
            ['+fs-checkpoint-host-timeout-ms-typo=1000',capture+'600000']]
    for i,options in enumerate(bad):
        trace=out/'must-stay-absent.trace'
        text=run([*common,'+fs-restore='+str(production/'default/cut-3/capture.fsckpt'),
                  *options],out/f'invalid-{i}.log',out,expected=1)
        require('FS_CHECKPOINT_ENTRY_ERROR' in text and 'FS_CHECKPOINT_ENTRY_CONFIGURED' not in text and
                not trace.exists(),'invalid watchdog request reached platform/trace')
    text=run([*common,'+fs-restore='+str(production/'default/cut-3/capture.fsckpt'),host+'1000',capture+'600000'],
             out/'early-reset.log',out,expected=1)
    require('periodic restore during initial target reset is unsupported' in text and
            'PRODUCTION_BOOTSTRAP' not in text,'unsupported reset-epoch watchdog restore accepted')
    results=[]
    libc=ctypes.CDLL(None,use_errno=True)
    libc.ptrace.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p]
    libc.ptrace.restype=ctypes.c_long
    def ptrace(request,pid):
        result=libc.ptrace(request,pid,None,None)
        require(result==0,f'ptrace request {request} failed: errno={ctypes.get_errno()}')

    for kind,options,reason in [('host',[host+'1000',cycle+'5000',capture+'600000'],'host_progress_stall'),
                                ('cycle',[host+'5000',cycle+'1000',capture+'600000'],'target_cycle_stall')]:
        directory=out/kind; directory.mkdir()
        checkpoint=directory/'restore.fsckpt'
        with atomic_output(checkpoint,binary=True) as stream: stream.write(image)
        trace=directory/'ports.trace'; readback=directory/'loaded-native.txt'; log_path=directory/'run.log'
        argv=[*common,'+fs-restore='+str(checkpoint),'+target_port_trace='+str(trace),
              '+test-loaded-native='+str(readback),*options]
        offset=0; fragment=b''; target=record['target_cycle']; stopped=None; started=time.monotonic_ns()
        with log_path.open('w') as log:
            log.write('argv='+json.dumps([str(a) for a in argv])+'\n'); log.flush()
            process=subprocess.Popen([str(a) for a in argv],cwd=directory,stdout=log,stderr=subprocess.STDOUT)
            traced=False
            try:
                while process.poll() is None:
                    require(time.monotonic_ns()-started<240_000_000_000,'retained watchdog replay exceeded timeout')
                    if trace.exists():
                        with trace.open('rb') as stream:
                            stream.seek(offset); chunk=stream.read(); offset+=len(chunk)
                        rows=(fragment+chunk).split(b'\n'); fragment=rows.pop()
                        if rows: target=int(rows[-1].split()[0])
                    if stopped is None and target>=600000:
                        ptrace(0x4206,process.pid); traced=True # SEIZE; no process-wide SIGSTOP.
                        ptrace(0x4207,process.pid) # INTERRUPT only this thread.
                        waited,status=os.waitpid(process.pid,os.WUNTRACED)
                        require(waited==process.pid and os.WIFSTOPPED(status) and status>>16==128,
                                'VCS main thread was not independently ptrace-stopped')
                        tasks={p.parent.name:p.read_text() for p in Path(f'/proc/{process.pid}/task').glob('*/status')}
                        require(len(tasks)>1 and all('TracerPid:\t0\n' in state for tid,state in tasks.items()
                                                    if tid!=str(process.pid)), 'injection stopped non-main threads')
                        stopped=dict(monotonic_ns=time.monotonic_ns(),observed_target_cycle=target,pid=process.pid,
                                     injection='PTRACE_SEIZE/PTRACE_INTERRUPT main thread only',wait_status=status,
                                     thread_count=len(tasks))
                        (directory/'stopped-threads.json').write_bytes(canonical(tasks))
                    time.sleep(0.01)
                code=process.wait()
            finally:
                if process.poll() is None:
                    if traced:
                        # A failed test still releases its traced child before killing it.
                        libc.ptrace(17,process.pid,None,None)
                    process.kill(); process.wait()
            log.write(f'exit={code}\n')
        text=log_path.read_text()
        failure=re.search(r'FS_CHECKPOINT_WATCHDOG_FAILURE reason=(\w+) target_cycle=(\d+) samples=(\d+) captures=(\d+) capture_ns=(\d+)',text)
        require(stopped and code==1 and failure and failure[1]==reason and int(failure[2])>=600000 and
                int(failure[3])>1,'production independent monitor did not detect injected late stall')
        armed=re.search(r'FS_CHECKPOINT_WATCHDOG_ARMED target_cycle=(\d+)',text)
        # The restored driver first yields two target cycles after bootstrap;
        # monitoring begins at that actual settled sample, never a synthetic
        # sample at the loaded cut or an added clock edge.
        require(armed and record['target_cycle']<=int(armed[1])<=record['target_cycle']+2 and
                'PRODUCTION_BOOTSTRAP zero_edges=1' in text and
                'PRODUCTION_PRE_EDGE owners_loaded=1 host_edges=0 target_edges=0' in text,
                'restore did not reinitialize watchdog at an audited zero-edge origin')
        actual=trace.read_bytes()
        require(len(actual)>0 and expected.startswith(actual),'late-stall replay differs from reference')
        require(dict(line.split() for line in readback.read_text().splitlines())==native,
                'retained watchdog replay changed pre-edge native state')
        results.append(dict(kind=kind,reason=reason,stopped=stopped,exit=code,argv=[str(a) for a in argv],
                            cwd=str(directory),log=str(log_path),trace=str(trace),checkpoint=str(checkpoint),
                            compared_bytes=len(actual),complete_rows=actual.count(b'\n'),
                            watchdog_target_cycle=int(failure[2]),watchdog_samples=int(failure[3]),
                            watchdog_first_sample_cycle=int(armed[1]),restored_target_cycle=record['target_cycle'],
                            detection_upper_bound_ns=time.monotonic_ns()-stopped['monotonic_ns']))
        (directory/'result.json').write_bytes(canonical(results[-1]))
    # Full healthy continuation from the same retained bytes with production
    # polling/monitor enabled, after both independent late failures.
    healthy=out/'healthy'; healthy.mkdir(); cp=healthy/'restore.fsckpt'; cp.write_bytes(image)
    trace=healthy/'ports.trace'; readback=healthy/'loaded-native.txt'
    text=run([*common,'+fs-restore='+str(cp),'+target_port_trace='+str(trace),
              '+test-loaded-native='+str(readback),host+'1000',cycle+'1000',capture+'600000'],healthy/'run.log',healthy)
    require('*** PASSED ***' in text and trace.read_bytes()==expected and
            dict(line.split() for line in readback.read_text().splitlines())==native,
            'healthy retained replay differs with runtime monitor enabled')
    require(store.select(before_target_cycle=600000)==(record,image),'watchdog failure mutated retained history')
    result=dict(invocation=str(out),selected=record,replays=results,parser_rejections=len(bad),
                healthy_trace=str(trace),healthy_continuation_rows=expected.count(b'\n'),
                live_history_summary=live['summary'],production_host_monitor=True,
                production_target_cycle_monitor=True,target_semantic_progress_monitor=False,
                intentional_capture_excluded_and_bounded=True,physical_fpga_validated=False)
    (out/'summary.json').write_bytes(canonical(result))
    (args.out/'latest.json').write_bytes(canonical(dict(invocation=str(out),summary=str(out/'summary.json'))))
    print('PASS: production independent host/cycle watchdogs detect late main-thread stalls from retained history; healthy replay matches')


if __name__=='__main__': main()
