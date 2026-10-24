"""EDA-only exact MIDAS registered-enable gate bank verification.

Original RTL plus a functional input model independently check every gate,
register, RAM and pipeline word. This is component evidence, not F2 capture.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.tests.verify_clocked_effects_vcs import GENERATED as BASE_GENERATED, ROOT, sha

GENERATED = (*BASE_GENERATED, 'AbstractClockGate.v')
SOURCES = (
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedClockGateAdapter.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedExternalOwners.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/passes/package.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/RegisteredClockGateBankSpec.scala',
    'tools/checkpoint_formats/tests/verify_registered_gate_vcs.py',
    'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
)


def bench(binding, manifest):
    require(manifest['root_module'] == 'GateStorage' and binding['access_clock'] == 'ckpt_clock', 'gate fixture required')
    require(len(binding['clock_gate_adapters']) == 1 and len(binding['state']) == len(manifest['state']) == 4,
            'incomplete gate coverage')
    captures = []
    oracles = {'saved': ('model_saved', 17, 1), 'ram': ('model_mem[a]', 13, 4),
               'ram_r_data': ('model_pipe', 13, 1), 'gate.enable': ('model_enable', 1, 1)}
    for index, (row, logical) in enumerate(zip(binding['state'], manifest['state'])):
        require(all(row[k] == logical[k] for k in ('state_id', 'hierarchy', 'width', 'depth')), 'unbound logical owner')
        name = row['hierarchy'].removeprefix('GateStorage.')
        require(name in oracles, 'unknown gate fixture owner')
        oracle, width, depth = oracles[name]
        require((row['width'], row['depth']) == (width, depth), 'wrong gate fixture shape')
        call = f'read_word({row["bank"]},{row["slot"]},'
        if depth == 4:
            captures.append(f'for(a=0;a<4;a++) {call}a,{index},original.{name}[a],{oracle});')
        else:
            captures.append(f'{call}0,{index},original.{name},{oracle});')
    return r'''`timescale 1ns/1ps
module checkpoint_registered_gate_tb;
import "DPI-C" function void checkpoint_network_fail();
reg clock=0, reference_clock=0, ckpt_clock=0;
reg reset=0, ce=0, wen=0;
reg [16:0] data=0;
reg [1:0] address=0;
wire [16:0] result,ref_result;
wire [12:0] ram_result,ref_ram_result;
reg ckpt_freeze=0,ckpt_reset=1,ckpt_req_valid=0,ckpt_resp_ready=0;
reg [7:0] ckpt_bank=0;
reg [15:0] ckpt_slot=0;
reg [31:0] ckpt_address=0;
wire ckpt_req_ready,ckpt_resp_valid,ckpt_resp_error,ckpt_match;
wire [63:0] ckpt_resp_data,ckpt_data;
GateStorage dut(.*);
OriginalGateStorage original(.clock(reference_clock),.reset(reset),.ce(ce),.wen(wen),
 .data(data),.address(address),.result(ref_result),.ram_result(ref_ram_result));
bit model_enable=0;
reg [16:0] model_saved=0;
reg [12:0] model_mem[0:3],model_pipe=0;
integer checks=0,steps=0,gated_edges=0,reads=0,stalls=0,frozen_edges=0,high_ce_changes=0;
integer captures=0,fd,a,i,j;
bit pulse_frozen=0,corrupt=0;
task check(input bit ok,input string message);
 begin checks++;
  if(!ok) begin
   $display("REGISTERED_GATE_FIRST_MISMATCH step=%0d gated=%0d reads=%0d frozen=%0d %s",steps,gated_edges,reads,ckpt_freeze,message);
   checkpoint_network_fail();
  end
 end
endtask
task outputs;
 begin
  check(result===ref_result && result===model_saved,"saved output/oracle");
  check(ram_result===ref_ram_result && ram_result===model_pipe,"RAM pipeline output/oracle");
 end
endtask
task functional_tick;
 begin
  check(!ckpt_freeze && !clock,"functional phase");
  // Original gate updates enable at posedge I. O has a positive edge when
  // either the old enable or newly accepted CE is one. In particular 1->0 CE
  // still produces a pulse; substituting CE as a storage enable is incorrect.
  if(model_enable || ce) begin
   model_saved=reset?0:data;
   if(wen) begin model_pipe=model_mem[address];model_mem[address]=data[12:0]; end
   gated_edges++;
  end
  model_enable=ce;
  #3;clock=1;reference_clock=1;steps++;#3;outputs();
  // CE changes during the high phase must not act as a transparent gate.
  ce=~ce;high_ce_changes++;#2;outputs();ce=~ce;#2;
  clock=0;reference_clock=0;#2;outputs();
 end
endtask
task access_tick;
 begin
  #2;ckpt_clock=1;#1;
  if(pulse_frozen) begin clock=1;frozen_edges++; end
  #2;ckpt_clock=0;clock=0;ce=~ce;#2;outputs();
 end
endtask
task read_word(input integer bank,input integer slot,input integer address,
 input integer index,input [63:0] reference_value,input [63:0] oracle_value);
 reg [63:0] actual;
 integer k;
 begin
  check(reference_value===oracle_value,"independent original owner/oracle");
  ckpt_bank=bank;ckpt_slot=slot;ckpt_address=address;ckpt_req_valid=1;#1;
  check(ckpt_req_ready===1,"ready without functional edges");access_tick();ckpt_req_valid=0;
  for(k=0;k<3;k++) begin
   actual=ckpt_resp_data ^ ((corrupt && reads==0)?64'b1:64'b0);
   check(ckpt_resp_valid===1 && ckpt_resp_error===0,"latched complete response");
   check(actual===oracle_value,$sformatf("state index=%0d address=%0d",index,address));
   ckpt_bank=255;ckpt_slot=65535;ckpt_address=32'hffffffff;
   access_tick();stalls++;
  end
  $fdisplay(fd,"%0d %0d %0d %0d %016h",steps,gated_edges,index,address,ckpt_resp_data);
  ckpt_resp_ready=1;access_tick();ckpt_resp_ready=0;
  check(ckpt_resp_valid===0,"response drained");reads++;
 end
endtask
task capture(input bit pulse);
 integer start_steps,start_gated,start_reads;
 begin
  start_steps=steps;start_gated=gated_edges;start_reads=reads;
  ckpt_freeze=1;pulse_frozen=pulse;reset=1;wen=1;data=17'h1abcd;address=2;#3;
  $CAPTURE
  ckpt_reset=1;access_tick();ckpt_reset=0;access_tick();
  check(steps==start_steps && gated_edges==start_gated && reads-start_reads==7,"zero functional advancement");
  $display("REGISTERED_GATE_CAPTURE step=%0d gated=%0d enable=%0d words=%0d pulse=%0d",steps,gated_edges,model_enable,reads-start_reads,pulse);
  pulse_frozen=0;ckpt_freeze=0;reset=0;wen=0;#2;captures++;
 end
endtask
task segment(input integer count,input bit last_ce);
 begin
  for(j=0;j<count;j++) begin
   ce=(j==count-1)?last_ce:((j*7+3)%11<5);
   data=(steps*977+31)&17'h1ffff;address=(steps*3+1)%4;
   wen=(j%3!=1);reset=(j%17==0);functional_tick();
  end
 end
endtask
initial begin
 corrupt=$test$plusargs("semantic_corrupt");
 $dumpfile("debug.vcd");$dumpvars(0,checkpoint_registered_gate_tb);
 fd=$fopen("capture.words","w");
 for(i=0;i<4;i++) model_mem[i]=0;
 access_tick();ckpt_reset=0;access_tick();
 // Initialize every functional RAM address through the original public ports.
 for(i=0;i<6;i++) begin ce=1;reset=1;wen=1;data=i+100;address=i%4;functional_tick();end
 capture(0);segment(37,0);capture(1);segment(83,1);capture(1);segment(97,0);capture(0);
 segment(129,1);outputs();
 check(captures==4 && reads==28 && stalls==84 && steps==352,"complete execution");
 $fclose(fd);
 $display("REGISTERED_GATE_PASS checks=%0d steps=%0d gated=%0d reads=%0d stalls=%0d frozen=%0d high_ce=%0d",checks,steps,gated_edges,reads,stalls,frozen_edges,high_ce_changes);
 $finish;
end
endmodule
'''.replace('$CAPTURE', '\n  '.join(captures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(Path(toolchain.VCS).is_file() and os.environ.get('VCS_HOME') == toolchain.VCS_HOME,
            'run on EDA with vcs-env.sh sourced LAST')
    base = args.out.resolve()
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='registered-gate-', dir=base))
    for label, source, names in [('generated', args.generated.resolve(), GENERATED), ('sources', ROOT, SOURCES)]:
        for name in names:
            target = out / label / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
    generated = out / 'generated'
    binding = json.loads((generated / 'generated-bank-binding.json').read_text())
    manifest = json.loads((generated / 'generated-bank-manifest.json').read_text())
    for key, name in [('reference_sha256', 'generated-bank-input.fir'), ('instrumented_sha256', 'generated-bank.fir'),
                      ('manifest_sha256', 'generated-bank-manifest.json')]:
        require(binding[key] == sha(generated / name), 'unbound generated input: ' + key)
    require(binding['clock_gate_adapters'][0]['source_sha256'] == sha(generated / 'AbstractClockGate.v'),
            'unbound original gate implementation')
    (out / 'bench.sv').write_text(bench(binding, manifest))
    commands = []

    def run(argv, directory, name):
        row = dict(argv=[str(a) for a in argv], cwd=str(directory), log=str(directory / name))
        commands.append(row)
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        with (directory / name).open('w') as log:
            result = subprocess.run(row['argv'], cwd=directory, stdout=log, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        return result.returncode, (directory / name).read_text()

    code, _ = run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate',
                   '-debug_access+all', '+vcs+initreg+random', '-top', 'checkpoint_registered_gate_tb',
                   '-Mdir=' + str(out / 'csrc'), '-o', out / 'simv', generated / 'generated-bank.sv',
                   generated / 'reference.sv', generated / 'AbstractClockGate.v',
                   out / 'bench.sv', out / 'sources' / SOURCES[-1]], out, 'compile.log')
    require(code == 0, f'VCS compile failed: {out / "compile.log"}')
    healthy = out / 'healthy'; healthy.mkdir()
    code, text = run([out / 'simv', '-no_save', '+vcs+initreg+0'], healthy, 'run.log')
    marker = re.search(r'REGISTERED_GATE_PASS checks=(\d+) steps=(\d+) gated=(\d+) reads=(\d+) stalls=(\d+) frozen=(\d+) high_ce=(\d+)', text)
    require(code == 0 and marker is not None, f'VCS simulation failed: {healthy / "run.log"}')
    cuts = [dict(step=int(c), gated_edges=int(g), enable=int(e), words=int(n), pulse=int(m))
            for c, g, e, n, m in re.findall(r'REGISTERED_GATE_CAPTURE step=(\d+) gated=(\d+) enable=(\d+) words=(\d+) pulse=(\d+)', text)]
    require([c['step'] for c in cuts] == [6, 43, 126, 223] and [c['enable'] for c in cuts] == [1, 0, 1, 0],
            'incomplete gate enable cuts')
    require((int(marker[2]), int(marker[4]), int(marker[5]), int(marker[7])) == (352, 28, 84, 352), 'incomplete execution')
    negative = out / 'semantic-negative'; negative.mkdir()
    code, bad = run([out / 'simv', '-no_save', '+vcs+initreg+0', '+semantic_corrupt'], negative, 'run.log')
    require(code == 1 and 'REGISTERED_GATE_FIRST_MISMATCH step=6 gated=6 reads=0 frozen=1 state index=0' in bad and
            'REGISTERED_GATE_PASS' not in bad, 'corruption did not stop at first state word')
    require((healthy / 'debug.vcd').stat().st_size > 1000, 'missing full debug waveform')
    (out / 'summary.json').write_text(json.dumps(dict(status='pass', backend='eda',
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), original_root=str(ROOT),
        scope='exact registered-enable clock-gate bank component; caller-established freeze', root='GateStorage',
        physical_fpga_capture=False, complete_cpu_acceptance=False, cuts=cuts,
        checks=int(marker[1]), steps=int(marker[2]), gated_edges=int(marker[3]), reads=int(marker[4]),
        stalls=int(marker[5]), frozen_edges=int(marker[6]), high_ce_changes=int(marker[7]), commands=commands,
        files={str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and
        not any(x in p.parts for x in ('csrc', 'simv.daidir')) and p.name != 'simv'}), indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
