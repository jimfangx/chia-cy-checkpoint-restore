"""Actual harness: a parked driver finishes low without an extra target edge.

Native services are fixtures; this is a terminal clock-scheduling guard, not a
checkpoint restart. Requires the existing generated InventoryFixture build.
"""
from tools.checkpoint_formats import toolchain as _toolchain
import argparse
import hashlib
import json
import os
from pathlib import Path

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.harness_restore import harness_layout
from tools.checkpoint_formats.tests.verify_semantic_vcs import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    generated = args.build.resolve() / 'f2/f2-midasexamples-InventoryFixture-NoConfig-DefaultF2Config'
    verilog = ROOT / 'sims/firesim/sim/midas/src/main/verilog'
    top = verilog / 'top.sv'
    constants = generated / 'FireSim-generated.const.vh'
    defines = generated / 'FireSim-generated.defines.vh'
    layout = harness_layout(top.read_text(), constants.read_text(), defines.read_text(), '0'*64)
    widths = [r['width'] for r in layout['records'][9:18]]
    fixture = r'''#include <svdpi.h>
#include <cstdio>
#include <cstdlib>
static unsigned ticks=0; static bool done=false;
static void zero(svBitVecVal **out) {
 const unsigned widths[]={WIDTHS};
 for(unsigned i=0;i<9;i++) for(unsigned j=0;j<(widths[i]+31)/32;j++) out[i][j]=0;
}
extern "C" void simulator_entry() {}
extern "C" svBit simulator_restore_pending() { return 0; }
extern "C" void simulator_restore_bootstrap(unsigned,const svBitVecVal*,svBit*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*,svBitVecVal*) { std::exit(1); }
extern "C" svBit simulator_checkpoint_pending() { return ticks==12 && !done; }
extern "C" svBit simulator_checkpoint_lowclock() { return 1; }
extern "C" void simulator_tick(svBit,svBit *fin,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,const svBitVecVal*,svBitVecVal*a,svBitVecVal*b,svBitVecVal*c,svBitVecVal*d,svBitVecVal*e,svBitVecVal*f,svBitVecVal*g,svBitVecVal*h,svBitVecVal*i) {
 if(++ticks>12) { std::fprintf(stderr,"extra native tick after low finish\n"); std::exit(1); }
 svBitVecVal *out[]={a,b,c,d,e,f,g,h,i};zero(out);*fin=0;
}
extern "C" void simulator_checkpoint_settled(unsigned,const svBitVecVal*,svBit*fin,svBitVecVal*a,svBitVecVal*b,svBitVecVal*c,svBitVecVal*d,svBitVecVal*e,svBitVecVal*f,svBitVecVal*g,svBitVecVal*h,svBitVecVal*i) {
 if(ticks!=12 || done) std::exit(1);
 svBitVecVal *out[]={a,b,c,d,e,f,g,h,i};zero(out);done=true;*fin=1;
}
extern "C" void terminal_failure() { std::exit(1); }
'''.replace('WIDTHS', ','.join(map(str, widths)))
    (out / 'fixture.cc').write_text(fixture)
    monitor = '''`timescale 1ps/1ps
module terminal_monitor;
import "DPI-C" function void terminal_failure();
integer host_edges=0, target_edges=0, captured_target=-1, captures=0;
// Exercise an active generated clock path independently of fixture MMIO.
initial force emul.FPGATop.sim.target.InventoryFixture_.RationalClockBridge_clocks_0_buffer.CE=1'b1;
always @(posedge emul.clock) host_edges=host_edges+1;
always @(posedge emul.FPGATop.sim.target.InventoryFixture_.RationalClockBridge_clocks_0_buffer.O) target_edges=target_edges+1;
always @(emul.checkpoint_settled_event) begin
 if(emul.clock || emul.reset || host_edges!=12 || target_edges!=12 || captures) terminal_failure();
 captured_target=target_edges; captures=captures+1;
end
always @(posedge emul.fin) begin
 #1001;
 if(emul.clock || host_edges!=12 || target_edges!=captured_target || captures!=1) terminal_failure();
 $display("LOW_FINISH_NO_EXTRA_EDGE host_edges=%0d target_edges=%0d",host_edges,target_edges);$finish;
end
initial begin #20000; terminal_failure(); end
endmodule
bind FPGATop terminal_monitor terminal();
'''
    (out / 'monitor.sv').write_text(monitor)
    (out / 'harness.sv').write_text(f'`include "{constants}"\n`include "{defines}"\n`include "{top}"\n')
    vcs = Path(os.environ['VCS_HOME']) / 'bin/vcs'
    require(str(vcs) == _toolchain.VCS, 'source vcs-env.sh LAST')
    run([vcs, '-full64', '-sverilog', '+define+VCS', '+define+CLOCK_PERIOD=1',
        '-timescale=1ps/1ps', '-top', 'emul', '-cc', os.environ['CC'], '-cpp', os.environ['CXX'],
        f'-Mdir={out/"csrc"}', '-o', out/'simv', out/'harness.sv', out/'monitor.sv',
        generated/'FireSim-generated.sv', verilog/'BUFGCE.v', out/'fixture.cc'], out/'build.log')
    text = run([out/'simv'], out/'run.log')
    require('LOW_FINISH_NO_EXTRA_EDGE host_edges=12 target_edges=12' in text, 'terminal edge guard did not run')
    result = dict(host_edges=12, target_edges=12, completed_at_low_clock=True, extra_native_or_target_edges=0,
        harness_source_sha256=hashlib.sha256(top.read_bytes()).hexdigest(),
        whole_runtime_restore_verified=False, physical_fpga_validated=False)
    (out/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print('PASS: low-clock completion cancels the scheduled rising edge')


if __name__ == '__main__':
    main()
