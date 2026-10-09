"""Fresh actual harness/generated/native/DPI integration; fixture driver MMIO.

This verifies publication and input refresh at the low-clock cut. It does not
load .fsckpt or certify the production FCFS driver/full runtime.
"""
import argparse
import json
import os
import re
from pathlib import Path
import struct

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.generated_restore import generated_build_identity, prepare_generated_loader, prepare_generated_restore
from tools.checkpoint_formats.harness_restore import harness_layout, harness_capture, prepare_harness_loader, prepare_harness_restore
from tools.checkpoint_formats.simulator import generated_capture, generated_words
from tools.checkpoint_formats.tests.verify_generated_restore_vcs import ports, pack, unpack_state
from tools.checkpoint_formats.tests.verify_driver_boundary_vcs import read_diagnostic
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    require(os.environ['VCS_HOME']=='/ecad/tools/synopsys/vcs/Y-2026.03-SP1','source vcs-env.sh LAST')
    generated=args.build.resolve()/'f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config'
    verilog=ROOT/'sims/firesim/sim/midas/src/main/verilog';cc=ROOT/'sims/firesim/sim/midas/src/main/cc'
    manifest=json.loads((generated/'FireSim-generated.simulator-state.json').read_text())
    rtl=(generated/'FireSim-generated.sv').read_text()
    identity=generated_build_identity(manifest,(generated/'FireSim-generated.simulator-reference.fir').read_text(),rtl,(verilog/'BUFGCE.v').read_text())
    layout=harness_layout((verilog/'top.sv').read_text(),(generated/'FireSim-generated.const.vh').read_text(),(generated/'FireSim-generated.defines.vh').read_text(),identity)
    words=list(generated_words(manifest));banks=layout['records']
    outputs=[p for p in ports(rtl) if p['direction']=='output']
    prepare_harness_loader(layout,out);prepare_generated_loader(manifest,identity,out,'emul.FPGATop',rtl=rtl)
    (out/'layout.json').write_bytes(canonical(layout));(out/'manifest.json').write_bytes(canonical(manifest))
    fmt='{"state":"%h","banks":['+','.join('"%h"' for _ in banks)+'],"outputs":"%b"}'
    expressions=[pack(words,'emul.')]+[r['owner'] for r in banks]+[pack(outputs,'emul.FPGATop.')]
    # The same actual harness drives reference and fresh restoration. Force an
    # active target gate so an accidental rising edge changes generated state.
    monitor=['`timescale 1ps/1ps','module harness_dispatcher_monitor;',
        'import "DPI-C" context function int harness_restore_initialize();',
        'import "DPI-C" context function int harness_restore(input string filename);',
        'import "DPI-C" context function int harness_restore_verify();',
        'import "DPI-C" context function int generated_restore(input string filename);',
        'import "DPI-C" context function int generated_restore_verify();',
        'import "DPI-C" context function void harness_restore_fail(input string message);',
        'import "DPI-C" context function void harness_dispatcher_check_native();',
        'integer fd=0, cutfd=0, edges=0, target_edges=0, refreshes=0; bit restoring=0, cut_seen=0;',
        'string outdir, hfile, gfile, negative;',
        'initial force emul.FPGATop.sim.target.InventoryFixture_.RationalClockBridge_clocks_0_buffer.CE=1;',
        'always @(posedge emul.clock) edges=edges+1;',
        'always @(posedge emul.FPGATop.sim.target.InventoryFixture_.RationalClockBridge_clocks_0_buffer.O) target_edges=target_edges+1;',
        'task sample; $fdisplay(fd,'+json.dumps(fmt)+','+','.join(expressions)+'); endtask',
        'initial begin',
        ' restoring=$test$plusargs("restore");',
        ' if (!$value$plusargs("outdir=%s",outdir)) harness_restore_fail("outdir");',
        ' fd=$fopen({outdir,"/rows.jsonl"},"w"); if(!fd) harness_restore_fail("trace open");',
        ' if(restoring) begin',
        ' if(harness_restore_initialize()) harness_restore_fail("initialize");',
        # Deliberately wait beyond several ordinary clock periods.
        ' #2002;',
        ' if(edges || target_edges || emul.clock || !emul.checkpoint_restore_waiting) harness_restore_fail("clock escaped while armed");',
        ' if(!$value$plusargs("harness=%s",hfile) || !$value$plusargs("generated=%s",gfile)) harness_restore_fail("load args");',
        ' if(harness_restore(hfile) || generated_restore(gfile)) harness_restore_fail("load");',
        ' #1; if(harness_restore_verify() || generated_restore_verify() || edges || target_edges) harness_restore_fail("pre-edge readback");',
        ' cutfd=$fopen({outdir,"/loaded.jsonl"},"w");',
        ' $fdisplay(cutfd,'+json.dumps(fmt)+','+','.join(expressions)+'); $fclose(cutfd);',
        ' if($value$plusargs("negative=%s",negative)) begin',
        ' if(negative=="reset") emul.reset=1;',
        ' if(negative=="finish") emul.fin=1;',
        ' if(negative=="highclock") force emul.clock=1;',
        ' end',
        ' emul.checkpoint_resume_restored();',
        ' if(edges || target_edges || emul.clock || refreshes!=1) harness_restore_fail("bootstrap edge/refresh");',
        ' harness_dispatcher_check_native();',
        ' $display("HARNESS_DISPATCHER_BOOTSTRAP zero_edges=1 refreshes=%0d finished=%0d",refreshes,emul.fin);',
        ' #1; sample();',
        ' if(negative=="repeat") emul.checkpoint_resume_restored();',
        ' if(emul.fin) begin #1001; if(edges || target_edges || emul.clock) harness_restore_fail("terminal edge"); $display("HARNESS_DISPATCHER_TERMINAL zero_edges=1"); $finish; end',
        ' end end',
        'always @(emul.checkpoint_settled_event) begin',
        ' cut_seen=1; cutfd=$fopen({outdir,"/cut.jsonl"},"w");',
        ' $fdisplay(cutfd,'+json.dumps(fmt)+','+','.join(expressions)+');$fclose(cutfd);',
        ' $display("HARNESS_DISPATCHER_CUT edges=%0d",edges); end',
        'always @(emul.checkpoint_input_refresh) begin',
        ' if(restoring && (edges || target_edges || emul.clock || refreshes)) harness_restore_fail("refresh phase");',
        ' refreshes=refreshes+1; end',
        'always @(negedge emul.clock) begin #3; if(cut_seen || restoring) sample(); end',
        'always @(posedge emul.fin) if(!restoring || edges) begin',
        ' #4; $display("HARNESS_DISPATCHER_DONE edges=%0d target_edges=%0d",edges,target_edges);$finish;end',
        'initial begin #100000; harness_restore_fail("watchdog"); end',
        'final if(fd) $fclose(fd); endmodule',
        'bind FPGATop harness_dispatcher_monitor dispatcher_monitor();']
    (out/'monitor.sv').write_text('\n'.join(monitor)+'\n')
    (out/'harness.sv').write_text(''.join(f'`include "{p}"\n' for p in (generated/'FireSim-generated.const.vh',generated/'FireSim-generated.defines.vh',verilog/'top.sv')))
    tests=Path(__file__).resolve().parent
    sources=[tests/'harness_dispatcher_checkpoint.cc',*[cc/p for p in (
        'core/simif.cc','core/simulation.cc','core/widget_registry.cc','core/widget.cc','core/stream_engine.cc',
        'core/bridge_driver.cc','core/driver_boundary_diagnostic.cc','emul/simif_emul.cc','emul/dpi.cc',
        'emul/mm.cc','emul/mmio.cc','emul/qsfp.cc','emul/host_timing.cc','bridges/master.cc','bridges/clock.cc','bridges/loadmem.cc')],
        ROOT/'tools/checkpoint_formats/harness_restore.cc',ROOT/'tools/checkpoint_formats/generated_restore.cc']
    run([Path(os.environ['VCS_HOME'])/'bin/vcs','-full64','-sverilog','-debug_access+all','+vpi','+vcs+initreg+random',
         '+define+VCS','+define+CLOCK_PERIOD=1','-timescale=1ps/1ps','-top','emul',
         '-cc',os.environ['CC'],'-cpp',os.environ['CXX'],'-CFLAGS',f'-std=c++20 -DVCS -I{cc} -I{out}',
         '-LDFLAGS','-Wl,--no-as-needed -pthread -lgmp',f'-Mdir={out/"csrc"}','-o',out/'simv',
         out/'harness.sv',out/'monitor.sv',generated/'FireSim-generated.sv',verilog/'BUFGCE.v',*sources],out/'build.log')
    common=[out/'simv','-no_save','+vcs+initreg+0','+vcs+initmem+0']
    cases=[]
    for cut in (13,14,16,31,32):
        case=out/f'cut-{cut}';ref=case/'reference';dst=case/'restore'
        ref.mkdir(parents=True,exist_ok=True);dst.mkdir(exist_ok=True)
        (ref/'software.diag').unlink(missing_ok=True)
        log=run([*common,f'+cut={cut}',f'+outdir={ref}'],ref/'run.log',ref)
        require('*** PASSED ***' in log,'reference did not complete')
        seen,owners=read_diagnostic(ref/'software.diag');require(seen==cut,'wrong cut')
        # Keep exactly the C++ coordinator's native/driver/widget membership.
        identities=['runtime/mmio','runtime/functional-memory/0','runtime/host-timing',
                    'runtime/simulation','runtime/simulation/base','widget/0','widget/1']
        for i,name in enumerate(identities):
            require(owners[name][0],f'unsupported {name}');(ref/f'owner-{i}').write_bytes(owners[name][1])
        row=json.loads((ref/'cut.jsonl').read_text())
        harness=case/'harness.load';gen=case/'generated.load'
        prepare_harness_restore(layout,harness_capture(layout,row['banks'],cut),harness)
        prepare_generated_restore(manifest,generated_capture(manifest,unpack_state(words,row['state']),cut),identity,gen,'emul.FPGATop')
        command=[*common,'+restore',f'+cut={cut}',f'+source={ref}',f'+harness={harness}',f'+generated={gen}']
        log=run([*command,f'+outdir={dst}'],dst/'run.log',dst)
        require('HARNESS_DISPATCHER_ARM_GUARDS count=5' in log,'arming lifecycle guards missing')
        require('HARNESS_DISPATCHER_NATIVE_UNCHANGED' in log and 'HARNESS_DISPATCHER_BOOTSTRAP zero_edges=1 refreshes=1' in log,'publication integration did not run')
        require(json.loads((dst/'loaded.jsonl').read_text())==row,'generated/harness changed before bootstrap')
        for i in range(7): require((ref/f'owner-{i}').read_bytes()==(dst/f'initial-{i}').read_bytes(),'owner changed before first edge')
        reference_log=(ref/'run.log').read_text()
        captured_edge=int(re.search(r'HARNESS_DISPATCHER_CUT edges=(\d+)',reference_log)[1])
        reference_edges=re.search(r'HARNESS_DISPATCHER_DONE edges=(\d+) target_edges=(\d+)',reference_log)
        require(reference_edges and reference_edges[1]==reference_edges[2],'active target gate edge mismatch')
        if cut!=32:
            restored_edges=re.search(r'HARNESS_DISPATCHER_DONE edges=(\d+) target_edges=(\d+)',log)
            require(restored_edges and restored_edges[1]==restored_edges[2]
                    and int(restored_edges[1])==int(reference_edges[1])-captured_edge,'extra/missing continuation edge')
        for owner in ('mmio','memory'):
            require((ref/f'final.{owner}').read_bytes()==(dst/f'final.{owner}').read_bytes(),'final native owner differs')
        finish_calls=['W 36 1','R 28 42','R 32 0','W 24 1','R 16 23','R 20 0']
        require((dst/'driver.trace').read_text().splitlines()==[f'OP {i}' for i in range(cut,32)]+finish_calls,
                'driver submission/initialization differs from independent operation oracle')
        expected=(ref/'rows.jsonl').read_text().splitlines();actual=(dst/'rows.jsonl').read_text().splitlines()
        require(expected==actual,'actual harness/generated continuation differs')
        require('entered simulation flow' not in log and 'Commencing simulation' not in log,'repeated initialization')
        if cut==32: require('HARNESS_DISPATCHER_TERMINAL zero_edges=1' in log,'terminal edge guard missing')
        memory=owners['runtime/functional-memory/0'][1]
        h=struct.unpack_from('<13Q',memory)
        require(h[5]==4096 and h[7]>0 and h[8]==1 and h[12]==2,'in-flight native memory lost')
        require(struct.unpack_from('<2Q',memory,4208)==(0,2),'held native responses missing')
        require(memory[104:4200]==bytes((i*13+7)%256 for i in range(4096)),'functional memory incomplete')
        cases.append(dict(cut=cut,samples=len(actual),generated_words=len(words),harness_words=len(banks),native_owners=7,terminal_zero_edges=cut==32))
        # Every malformed native owner is rejected before any partial publication.
        for i in range(7):
            failed=case/f'malformed-{i}';failed.mkdir(exist_ok=True)
            for j in range(7):
                b=(ref/f'owner-{j}').read_bytes();(failed/f'owner-{j}').write_bytes(b[:-1] if j==i else b)
            bad=[x for x in command if not str(x).startswith('+source=')]+[f'+source={failed}',f'+outdir={failed}']
            text=run(bad,failed/'run.log',failed,expected=1)
            require('HARNESS_DISPATCHER_REJECTED_BEFORE_EDGE' in text and not list(failed.glob('initial-*')) and not (failed/'driver.trace').exists(),'malformed owner published state')
        for negative in ('unsupported','reset','finish','repeat'):
            failed=case/negative;failed.mkdir(exist_ok=True)
            text=run([*command,f'+negative={negative}',f'+outdir={failed}'],failed/'run.log',failed,expected=1)
            require(('HARNESS_DISPATCHER_REJECTED_BEFORE_EDGE' if negative=='unsupported' else 'FS_RESTORE_BOOTSTRAP_ERROR') in text,'lifecycle guard did not run')
            if negative=='unsupported': require(not list(failed.glob('initial-*')),'unknown driver published state')
    summary=dict(scope=__doc__,cases=cases,fresh_continuations=len(cases),samples=sum(c['samples'] for c in cases),
        before_first_edge_native_owner_comparisons=7*len(cases),malformed_native_processes=7*len(cases),
        arming_lifecycle_rejections=5*len(cases),lifecycle_negative_processes=4*len(cases),generated_build_hash=identity,whole_runtime_restore_verified=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
