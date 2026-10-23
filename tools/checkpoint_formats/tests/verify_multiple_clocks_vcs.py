"""EDA-only readout with independent functional and transport clocks.

Checks all register, split-clock RAM and synchronous read owners against original
RTL and a model driven only by functional requests. Component evidence only;
the testbench establishes freeze and supplies no CPU/global CDC acceptance.
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
from tools.checkpoint_formats.tests.verify_clocked_effects_vcs import GENERATED, ROOT, sha

SOURCES = (
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedClockGateAdapter.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/MultipleFunctionalClocksSpec.scala',
    'tools/checkpoint_formats/tests/verify_multiple_clocks_vcs.py',
    'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
)


def bench(binding, manifest):
    require(manifest['root_module'] == 'MultiClockStorage' and binding['access_clock'] == 'ckpt_clock',
            'multiple-clock fixture contract required')
    expected_domains = [dict(clock_hierarchy='MultiClockStorage.' + name, root_clock=root)
                        for name, root in [('clock_a', 'clock_a'), ('clock_b', 'clock_b'),
                                           ('left_.a', 'clock_a'), ('left_.b', 'clock_b'),
                                           ('right_.a', 'clock_b'), ('right_.b', 'clock_a')]]
    forwarded = any(row['clock_hierarchy'].startswith('MultiClockStorage.route_')
                    for row in binding['functional_clock_domains'])
    if forwarded:
        for instance, roots in [('route_a', ('clock_a', 'clock_a')), ('route_b', ('clock_b', 'clock_a'))]:
            for pin, root in [('a', roots[0]), ('b', roots[1]),
                              ('input_a', roots[0]), ('input_b', roots[1])]:
                expected_domains.append(dict(clock_hierarchy=f'MultiClockStorage.{instance}.{pin}', root_clock=root))
        expected_domains.sort(key=lambda row: row['clock_hierarchy'])
    static = any(row['clock_hierarchy'].startswith('MultiClockStorage.static_')
                 for row in binding['functional_clock_domains'])
    if static:
        require(forwarded, 'static metadata fixture must retain functional forwarding')
        for side, name, value in [('left_', 'zero', 0), ('right_', 'one', 1)]:
            for path in (f'{side}.metadata', f'{side}.metadata_out',
                         f'static_{name}.unused', f'static_{name}.forwarded'):
                expected_domains.append(dict(clock_hierarchy='MultiClockStorage.' + path, constant_clock=value))
        expected_domains.sort(key=lambda row: row['clock_hierarchy'])
    require(binding['functional_clock_domains'] == expected_domains, 'incomplete clock provenance')
    require(len(binding['state']) == len(manifest['state']) == 9, 'incomplete state')
    capture = []
    for index, (row, logical) in enumerate(zip(binding['state'], manifest['state'])):
        require(all(row[k] == logical[k] for k in ('state_id', 'hierarchy', 'width', 'depth')),
                'binding differs from independent inventory')
        name = row['hierarchy'].removeprefix('MultiClockStorage.')
        if name == 'saved':
            require((row['width'], row['depth']) == (9, 1), 'wrong root shape')
            oracle = 'model_root'
        else:
            match = re.fullmatch(r'(left_|right_)\.(saved_a|saved_b|ram|ram_r_data)', name)
            require(match is not None, 'unexpected state owner: ' + name)
            side, kind = (0 if match[1] == 'left_' else 1), match[2]
            width = {'saved_a': 9, 'saved_b': 17, 'ram': 13, 'ram_r_data': 13}[kind]
            require((row['width'], row['depth']) == (width, 4 if kind == 'ram' else 1), 'wrong owner shape')
            oracle = {'saved_a': f'model_a[{side}]', 'saved_b': f'model_b[{side}]',
                      'ram': f'model_mem[{side}][a]', 'ram_r_data': f'model_pipe[{side}]'}[kind]
        call = f'read_word({row["bank"]},{row["slot"]},'
        if row['depth'] > 1:
            capture.append(f'for(a=0;a<4;a++) {call}a,{index},original.{name}[a],{oracle});')
        else:
            capture.append(f'{call}0,{index},original.{name},{oracle});')
    return r'''`timescale 1ns/1ps
module checkpoint_multiple_clocks_tb;
import "DPI-C" function void checkpoint_network_fail();
reg clock_a=0, clock_b=0, ckpt_clock=0, reference_a=0, reference_b=0;
reg reset_a=1, reset_b=1, wen=0;
reg [16:0] data=0;
reg [1:0] address=0;
wire [8:0] result,left_a,right_a,ref_result,ref_left_a,ref_right_a;
wire [16:0] left_b,right_b,ref_left_b,ref_right_b;
wire [12:0] left_ram,right_ram,ref_left_ram,ref_right_ram;
reg ckpt_freeze=0, ckpt_reset=1, ckpt_req_valid=0, ckpt_resp_ready=0;
reg [7:0] ckpt_bank=0;
reg [15:0] ckpt_slot=0;
reg [31:0] ckpt_address=0;
wire ckpt_req_ready,ckpt_resp_valid,ckpt_resp_error,ckpt_match;
wire [63:0] ckpt_resp_data,ckpt_data;
MultiClockStorage dut(.*);
OriginalMultiClockStorage original(.clock_a(reference_a),.clock_b(reference_b),
  .reset_a(reset_a),.reset_b(reset_b),.wen(wen),.data(data),.address(address),
  .result(ref_result),.left_a(ref_left_a),.left_b(ref_left_b),.left_ram(ref_left_ram),
  .right_a(ref_right_a),.right_b(ref_right_b),.right_ram(ref_right_ram));
reg [8:0] model_root,model_a[0:1];
reg [16:0] model_b[0:1];
reg [12:0] model_mem[0:1][0:3],model_pipe[0:1];
integer checks=0,steps=0,edges_a=0,edges_b=0,reads=0,stalls=0,captures=0;
integer frozen_a=0,frozen_b=0,stopped_reads=0,fd,a,i,j,pulse_mask=0;
bit initialized=0,corrupt=0;
task check(input bit ok,input string message);
  begin
    checks++;
    if(!ok) begin
      $display("MULTICLOCK_FIRST_MISMATCH step=%0d edges_a=%0d edges_b=%0d reads=%0d frozen=%0d %s",steps,edges_a,edges_b,reads,ckpt_freeze,message);
      checkpoint_network_fail();
    end
  end
endtask
task outputs;
  begin
    check(result===ref_result && result===model_root,"root output/oracle");
    check(left_a===ref_left_a && left_a===model_a[0],"left domain-a output/oracle");
    check(left_b===ref_left_b && left_b===model_b[0],"left domain-b output/oracle");
    check(left_ram===ref_left_ram && left_ram===model_pipe[0],"left RAM pipeline/oracle");
    check(right_a===ref_right_a && right_a===model_a[1],"swapped right domain-a output/oracle");
    check(right_b===ref_right_b && right_b===model_b[1],"swapped right domain-b output/oracle");
    check(right_ram===ref_right_ram && right_ram===model_pipe[1],"swapped right RAM pipeline/oracle");
  end
endtask
task functional_tick(input integer mask);
  begin
    check(!ckpt_freeze && mask>0 && mask<4,"functional phase");
    // Read-before-write at coincident edges; both RAMs have independent clocks.
    if(mask&1) begin
      model_root=reset_a?0:data[8:0]; model_a[0]=reset_a?0:data[8:0];
      model_b[1]=reset_a?0:data; model_pipe[0]=model_mem[0][address];
    end
    if(mask&2) begin
      model_a[1]=reset_b?0:data[8:0]; model_b[0]=reset_b?0:data;
      model_pipe[1]=model_mem[1][address];
    end
    if(wen && (mask&1)) model_mem[1][address]=data[12:0];
    if(wen && (mask&2)) model_mem[0][address]=data[12:0];
    #3; clock_a=(mask&1)!=0; reference_a=clock_a;
    clock_b=(mask&2)!=0; reference_b=clock_b;
    // Coincident input clocks retain read-before-write semantics on each RAM.
    steps++; if(mask&1) edges_a++; if(mask&2) edges_b++;
    #2; clock_a=0;clock_b=0;reference_a=0;reference_b=0; #2;
    if(initialized) outputs();
  end
endtask
task access_tick;
  begin
    #2; ckpt_clock=1; #1;
    if(pulse_mask&1) begin clock_a=1; frozen_a++; end
    #1;
    if(pulse_mask&2) begin clock_b=1; frozen_b++; end
    #2; ckpt_clock=0;clock_a=0;clock_b=0; #2;
    if(initialized) outputs();
  end
endtask
task read_word(input integer bank,input integer slot,input integer address,
               input integer index,input [63:0] reference_value,input [63:0] oracle_value);
  reg [63:0] actual;
  integer k;
  begin
    check(reference_value===oracle_value,"independent original owner/oracle");
    ckpt_bank=bank; ckpt_slot=slot; ckpt_address=address; ckpt_req_valid=1; #1;
    check(ckpt_req_ready===1,"ready without functional clocks");
    access_tick();ckpt_req_valid=0;
    for(k=0;k<3;k++) begin
      actual=ckpt_resp_data ^ ((corrupt && reads==0)?64'b1:64'b0);
      check(ckpt_resp_valid===1 && ckpt_resp_error===0,"complete latched response");
      check(actual===oracle_value,$sformatf("state index=%0d address=%0d",index,address));
      ckpt_bank=255; ckpt_slot=65535; ckpt_address=32'hffffffff;
      access_tick();stalls++;
    end
    $fdisplay(fd,"%0d %0d %0d %0d %0d %016h",steps,edges_a,edges_b,index,address,ckpt_resp_data);
    ckpt_resp_ready=1;access_tick();ckpt_resp_ready=0;
    check(ckpt_resp_valid===0,"retired response");reads++;if(pulse_mask==0)stopped_reads++;
  end
endtask
task capture(input integer mask);
  integer start_steps,start_a,start_b,start_reads;
  begin
    start_steps=steps;start_a=edges_a;start_b=edges_b;start_reads=reads;
    // Caller establishes a settled freeze in both domains before transport.
    ckpt_freeze=1;pulse_mask=mask;reset_a=1;reset_b=1;wen=1;data=17'h1abcd;address=2;
    #3;
    $CAPTURE
    check(steps==start_steps && edges_a==start_a && edges_b==start_b && reads-start_reads==15,"complete common cut with zero functional advancement");
    // Endpoint reset is independent of all frozen RAM/register/reset owners.
    ckpt_reset=1;access_tick();ckpt_reset=0;access_tick();
    $display("MULTICLOCK_CAPTURE step=%0d edges_a=%0d edges_b=%0d words=%0d mask=%0d",steps,edges_a,edges_b,reads-start_reads,mask);
    captures++;pulse_mask=0;reset_a=0;reset_b=0;wen=0;ckpt_freeze=0;
  end
endtask
task work(input integer count);
  integer k;
  begin for(k=0;k<count;k++)begin
    data=(steps*7919+k*313);address=(k+steps)%4;wen=(k%3!=0);
    functional_tick(1+k%3);
  end end
endtask
initial begin
  $dumpfile("debug.vcd");$dumpvars(0,checkpoint_multiple_clocks_tb);
  fd=$fopen("capture.words","w");check(fd!=0,"capture output");
  corrupt=$test$plusargs("semantic_corrupt");
  for(i=0;i<2;i++)for(j=0;j<4;j++)model_mem[i][j]=0;
  access_tick();access_tick();ckpt_reset=0;
  functional_tick(3);reset_a=0;reset_b=0;
  for(i=0;i<4;i++)begin address=i;data=17'h16321^(i*917);wen=1;functional_tick(3);end
  wen=0;address=1;functional_tick(3);initialized=1;outputs();
  capture(0);work(37);capture(3);work(83);capture(1);work(97);capture(2);work(129);
  check(captures==4 && reads==60 && stalls==180 && stopped_reads==15,"full four-cut coverage");
  $fclose(fd);
  $display("MULTICLOCK_PASS checks=%0d steps=%0d edges_a=%0d edges_b=%0d reads=%0d stalls=%0d frozen_a=%0d frozen_b=%0d",checks,steps,edges_a,edges_b,reads,stalls,frozen_a,frozen_b);
  $finish;
end
endmodule
'''.replace('$CAPTURE', '\n    '.join(capture))


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
    out = Path(tempfile.mkdtemp(prefix='multiple-clocks-', dir=base))
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
                   '-debug_access+all', '+vcs+initreg+random', '-top', 'checkpoint_multiple_clocks_tb',
                   '-Mdir=' + str(out / 'csrc'), '-o', out / 'simv', generated / 'generated-bank.sv',
                   generated / 'reference.sv', out / 'bench.sv', out / 'sources' / SOURCES[-1]], out, 'compile.log')
    require(code == 0, f'VCS compile failed: {out / "compile.log"}')
    healthy = out / 'healthy'; healthy.mkdir()
    code, text = run([out / 'simv', '-no_save', '+vcs+initreg+0'], healthy, 'run.log')
    marker = re.search(r'MULTICLOCK_PASS checks=(\d+) steps=(\d+) edges_a=(\d+) edges_b=(\d+) reads=(\d+) stalls=(\d+) frozen_a=(\d+) frozen_b=(\d+)', text)
    require(code == 0 and marker is not None, f'VCS simulation failed: {healthy / "run.log"}')
    require(int(marker[2]) == 352 and (int(marker[5]), int(marker[6])) == (60, 180), 'incomplete execution')
    cuts = [dict(step=int(c), edges_a=int(a), edges_b=int(b), words=int(n), pulse_mask=int(m))
            for c, a, b, n, m in re.findall(r'MULTICLOCK_CAPTURE step=(\d+) edges_a=(\d+) edges_b=(\d+) words=(\d+) mask=(\d+)', text)]
    require([c['step'] for c in cuts] == [6, 43, 126, 223] and all(c['words'] == 15 for c in cuts), 'incomplete cuts')
    negative = out / 'semantic-negative'; negative.mkdir()
    code, bad = run([out / 'simv', '-no_save', '+vcs+initreg+0', '+semantic_corrupt'], negative, 'run.log')
    require(code == 1 and 'MULTICLOCK_FIRST_MISMATCH step=6 edges_a=6 edges_b=6 reads=0 frozen=1 state index=0' in bad and
            'MULTICLOCK_PASS' not in bad, 'corruption did not stop at first state word')
    require((healthy / 'debug.vcd').stat().st_size > 1000, 'missing full debug waveform')
    (out / 'summary.json').write_text(json.dumps(dict(status='pass', backend='eda',
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), original_root=str(ROOT),
        scope='transparent hierarchical functional clock component only; caller-established freeze', root='MultiClockStorage',
        physical_fpga_capture=False, complete_cpu_acceptance=False, cuts=cuts,
        checks=int(marker[1]), steps=int(marker[2]), edges_a=int(marker[3]), edges_b=int(marker[4]),
        reads=int(marker[5]), stalls=int(marker[6]), frozen_a=int(marker[7]), frozen_b=int(marker[8]), commands=commands,
        files={str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and
        not any(x in p.parts for x in ('csrc', 'simv.daidir')) and p.name != 'simv'}), indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
