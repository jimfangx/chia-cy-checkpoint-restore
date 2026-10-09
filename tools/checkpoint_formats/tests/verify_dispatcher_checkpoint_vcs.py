"""Actual pthread dispatcher bootstrap; fixture MMIO/RTL, no full restart."""
import argparse
import json
import os
from pathlib import Path
import re
import struct

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run
from tools.checkpoint_formats.tests.verify_driver_boundary_vcs import read_diagnostic

CC = ROOT / 'sims/firesim/sim/midas/src/main/cc'
TESTS = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    require(os.environ['VCS_HOME'] == '/ecad/tools/synopsys/vcs/Y-2026.03-SP1', 'source vcs-env.sh LAST')
    sources = [TESTS/'dispatcher_checkpoint.cc', *[CC/p for p in (
        'core/simif.cc', 'core/simulation.cc', 'core/widget_registry.cc', 'core/widget.cc',
        'core/stream_engine.cc', 'core/bridge_driver.cc', 'core/driver_boundary_diagnostic.cc',
        'emul/simif_emul.cc', 'emul/mm.cc', 'emul/mmio.cc', 'emul/qsfp.cc',
        'emul/host_timing.cc', 'bridges/master.cc', 'bridges/clock.cc', 'bridges/loadmem.cc')]]
    native, simv = out/'dispatcher-native', out/'dispatcher-simv'
    run([os.environ['CXX'], '-std=c++20', '-Wall', '-Wextra', '-Wno-unused-parameter',
         '-g', '-no-pie', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-DVCS',
         f'-I{CC}', *sources, '-pthread', '-lgmp', '-o', native], out/'native-build.log')
    run([Path(os.environ['VCS_HOME'])/'bin/vcs', '-full64', '-sverilog', '-timescale=1ns/1ps',
         '-top', 'dispatcher_checkpoint_tb', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
         f'-Mdir={out/"csrc"}', '-CFLAGS', f'-std=c++20 -DVCS -DDISPATCHER_CHECKPOINT_DPI -I{CC}',
         '-LDFLAGS', '-Wl,--no-as-needed -pthread -lgmp', '-o', simv,
         TESTS/'dispatcher_checkpoint_tb.sv', *sources], out/'vcs-build.log')
    cases=[]; malformed=0
    for backend in ('native-sanitized', 'vcs-dpi'):
        def command(source, dest, restore, cut, scenario, ticks=0):
            if backend == 'native-sanitized':
                return [native, source, dest, int(restore), cut, scenario, ticks]
            return [simv, '-no_save', f'+source={source}', f'+outdir={dest}',
                    f'+restore={int(restore)}', f'+cut={cut}', f'+scenario={scenario}', f'+ticks={ticks}']
        for scenario in range(4):
            for cut in range(1,5):
                case=out/backend/f'{scenario}-{cut}'; case.mkdir(parents=True,exist_ok=True)
                ref=case/'reference'; ref.mkdir(exist_ok=True)
                dst=case/'restore'; dst.mkdir(exist_ok=True)
                (ref/'software.diag').unlink(missing_ok=True)
                reference_log=run(command(ref,ref,False,cut,scenario),ref/'run.log',ref)
                captured,owners=read_diagnostic(ref/'software.diag')
                require(captured==cut,'wrong operation boundary')
                for name,identity in dict(base='runtime/simulation/base',driver='runtime/simulation',
                                          timing='runtime/host-timing',mmio='runtime/mmio',
                                          memory='runtime/functional-memory/0').items():
                    require(identity in owners and owners[identity][0], f'missing {identity}')
                    (ref/name).write_bytes(owners[identity][1])
                ticks=int.from_bytes((ref/'cut.ticks').read_bytes(),'little')
                memory=(ref/'memory').read_bytes()
                header=struct.unpack_from('<13Q',memory)
                require(header[5]==4096 and header[7]==1 and header[8]==1 and header[12]==2,
                        'native memory cut lost in-flight write progress')
                require(memory[104:104+4096]==bytes((i*13+7)%256 for i in range(4096)),
                        'native functional memory is incomplete')
                queued_b,queued_r=struct.unpack_from('<2Q',memory,104+4096+8)
                require((queued_b,queued_r)==(0,2),'native held read responses are missing')
                log=run(command(ref,dst,True,cut,scenario,ticks),dst/'run.log',dst)
                rows=(ref/'trace').read_text().splitlines()
                # Independent MMIO and host tick oracle: each call yields once;
                # the returned-operation cut is before the next submission.
                calls=['R 0 1', 'R 4 1181315685', 'W 24 1', 'R 16 23', 'R 20 0']
                for i in range(4):
                    calls += [f'W 100 {i}', f'R 104 {i*9}']
                calls += ['W 36 1','R 28 42','R 32 0','W 24 1','R 16 23','R 20 0']
                oracle=[f'{min(i,14) if scenario==3 else i} {call}' for i,call in enumerate(calls,1)]
                oracle.insert(5+2*cut, f'CUT {6+2*cut}')
                require(rows==oracle,'uninterrupted dispatcher differs from independent oracle')
                expected=rows[rows.index(f'CUT {ticks}')+1:]
                actual=(dst/'trace').read_text().splitlines()
                require(actual==expected,'dispatcher inserted a tick, initialization or MMIO')
                for name in ('base','driver','timing','mmio','memory'):
                    require((ref/name).read_bytes()==(dst/f'initial.{name}').read_bytes(), 'owner changed before bootstrap')
                for name in ('mmio','memory'):
                    require((ref/name).read_bytes()==(dst/f'bootstrap.{name}').read_bytes(), 'bootstrap ticked outstanding native traffic')
                zero_edge = scenario==3 and cut==4
                require(f'BOOTSTRAP_NO_EDGE ticks={ticks} finished={int(zero_edge)}' in log, 'bootstrap advanced a native tick')
                require('entered simulation flow' not in log and 'Commencing simulation' not in log,'initialization repeated')
                final=lambda value: re.search(r'PASS: real dispatcher result=(\d+) ticks=(\d+) rejections=(\d+)',value)
                a,b=final(reference_log),final(log)
                require(a and b and a.group(1,2)==b.group(1,2),'completion code or native timing changed')
                require(int(b[3])==11,'lifecycle/phase rejections did not run')
                if backend=='vcs-dpi':
                    if zero_edge:
                        require('FIXTURE_EDGE' not in log,'terminal bootstrap advanced an edge')
                    else:
                        require(log.index('BOOTSTRAP_NO_EDGE')<log.index('FIXTURE_EDGE'),'bootstrap followed edge')
                cases.append(dict(backend=backend,scenario=scenario,cut=cut,
                                  restored_before_first_edge=True,mmio_calls=len(expected),ticks=int(b[2])))
        for name in ('base','driver','timing','mmio','memory'):
            failed=out/backend/f'malformed-{name}'; failed.mkdir(exist_ok=True)
            for owner in ('base','driver','timing','mmio','memory'):
                data=(ref/owner).read_bytes()
                (failed/owner).write_bytes(data[:-1] if owner==name else data)
            log=run(command(failed,failed,True,4,3,ticks),failed/'run.log',failed,expected=1)
            require('DISPATCHER_REJECTED_BEFORE_FIRST_EDGE' in log and 'FIXTURE_EDGE' not in log,
                    'malformed load started dispatcher or fixture clock')
            require(not (failed/'trace').exists() and not list(failed.glob('initial.*')),
                    'malformed owner published partial restored state')
            malformed+=1
    summary=dict(scope='actual simif_emul_t pthread dispatcher and simulation_t; fixture MMIO/RTL',
                 fresh_continuations=len(cases),before_first_edge_owner_comparisons=5*len(cases),
                 outstanding_native_owner_bootstrap_comparisons=2*len(cases),
                 lifecycle_rejections=11*len(cases),malformed_fresh_processes=malformed,
                 cases=cases,whole_runtime_restore_verified=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
