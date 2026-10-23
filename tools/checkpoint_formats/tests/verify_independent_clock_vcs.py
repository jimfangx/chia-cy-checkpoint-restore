"""EDA VCS readout of the retained Rocket DCacheDataArray with its clock stopped.

Every physical byte and read pipeline is checked against unchanged original RTL
and an independent functional-port model. This is component evidence, not FPGA
capture or complete Rocket migration.
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
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala',
    'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/IndependentAccessClockSpec.scala',
    'tools/checkpoint_formats/tests/verify_independent_clock_vcs.py',
    'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
)


def bench(binding, manifest):
    require(manifest['root_module'] == 'DCacheDataArray' and binding['access_clock'] == 'ckpt_clock',
            'actual data-array independent-clock contract required')
    require(len(binding['state']) == len(manifest['state']) == 128, 'incomplete actual data array')
    capture = []
    for index, (row, logical) in enumerate(zip(binding['state'], manifest['state'])):
        require(all(row[k] == logical[k] for k in ('state_id', 'hierarchy', 'width', 'depth')),
                'binding differs from independent inventory')
        name = row['hierarchy'].removeprefix('DCacheDataArray.')
        match = re.fullmatch(r'rockettile_dcache_data_arrays_0_(\d+)(_rw_rdata)?', name)
        require(match is not None and row['width'] == 8, 'unexpected real array owner')
        number = int(match[1]); way, lane = divmod(number, 8)
        require(way < 8 and row['depth'] == (1 if match[2] else 512), 'wrong RAM shape')
        if match[2]:
            capture.append(f'read_word({row["bank"]},{row["slot"]},0,{index},'
                           f'original.{name},modelpipe[{way}][{lane*8}+:8]);')
        else:
            capture.append(f'for (a=0;a<512;a++) read_word({row["bank"]},{row["slot"]},a,{index},'
                           f'original.{name}[a],modelmem[{way}][a][{lane*8}+:8]);')
    outputs = '\n'.join(f'check(io_resp_{i} === reference_resp_{i},"original output {i}"); '
                        f'check(io_resp_{i} === modelpipe[{i}],"functional oracle output {i}");'
                        for i in range(8))
    declarations = '\n'.join(f'wire [63:0] io_resp_{i}, reference_resp_{i};' for i in range(8))
    connections = ','.join(f'.io_resp_{i}(reference_resp_{i})' for i in range(8))
    return f'''`timescale 1ns/1ps
module checkpoint_independent_clock_tb;
import "DPI-C" function void checkpoint_network_fail();
reg clock=0, reference_clock=0, ckpt_clock=0;
reg io_req_valid=0, io_req_bits_write=0;
reg [11:0] io_req_bits_addr=0;
reg [63:0] io_req_bits_wdata=0;
reg [7:0] io_req_bits_eccMask=0, io_req_bits_way_en=0;
{declarations}
reg ckpt_freeze=0, ckpt_reset=1, ckpt_req_valid=0, ckpt_resp_ready=0;
reg [7:0] ckpt_bank=0;
reg [15:0] ckpt_slot=0;
reg [31:0] ckpt_address=0;
wire ckpt_req_ready, ckpt_resp_valid, ckpt_resp_error, ckpt_match;
wire [63:0] ckpt_resp_data, ckpt_data;
DCacheDataArray dut(.*);
OriginalDCacheDataArray original(.clock(reference_clock),.io_req_valid(io_req_valid),
  .io_req_bits_write(io_req_bits_write),.io_req_bits_addr(io_req_bits_addr),
  .io_req_bits_wdata(io_req_bits_wdata),.io_req_bits_eccMask(io_req_bits_eccMask),
  .io_req_bits_way_en(io_req_bits_way_en),{connections});
reg [63:0] modelmem[0:7][0:511], modelpipe[0:7];
integer checks=0, edges=0, reads=0, stalls=0, captures=0, stopped_reads=0;
integer frozen_clock_edges=0, i, w, b, a, fd;
bit initialized=0, pulse_frozen_clock=0, corrupt=0;
task check(input bit condition, input string message);
  begin
    checks++;
    if (!condition) begin
      $display("INDEPENDENT_CLOCK_FIRST_MISMATCH cycle=%0d reads=%0d frozen=%0d %s",edges,reads,ckpt_freeze,message);
      checkpoint_network_fail();
    end
  end
endtask
task outputs;
  begin {outputs} end
endtask
task functional_tick;
  integer way, lane, addr;
  begin
    check(!ckpt_freeze && !clock,"functional tick phase");
    addr=io_req_bits_addr>>3;
    if(io_req_valid) for(way=0;way<8;way++) begin
      modelpipe[way]=modelmem[way][addr];
      if(io_req_bits_write && io_req_bits_way_en[way])
        for(lane=0;lane<8;lane++) if(io_req_bits_eccMask[lane])
          modelmem[way][addr][lane*8+:8]=io_req_bits_wdata[lane*8+:8];
    end
    #3; clock=1; reference_clock=1; edges++;
    #2; clock=0; reference_clock=0; #2;
    if(initialized) outputs();
  end
endtask
task access_tick;
  begin
    #2; ckpt_clock=1; #1;
    if(pulse_frozen_clock) begin
      check(ckpt_freeze,"functional clock pulse only while frozen");
      clock=1; frozen_clock_edges++;
    end
    #2; ckpt_clock=0; clock=0; #2;
    if(initialized) outputs();
  end
endtask
task read_word(input integer bank, input integer slot, input integer address,
               input integer index, input [7:0] original_value, input [7:0] oracle_value);
  reg [63:0] actual;
  integer j, start_edges;
  begin
    start_edges=edges;
    check(original_value===oracle_value,"independent original RAM/pipeline oracle");
    ckpt_bank=bank; ckpt_slot=slot; ckpt_address=address;
    ckpt_req_valid=1; ckpt_resp_ready=0; #1;
    check(ckpt_req_ready===1,"ready without functional clock");
    access_tick(); ckpt_req_valid=0;
    for(j=0;j<2;j++) begin
      actual=ckpt_resp_data ^ ((corrupt && reads==0) ? 64'b1 : 64'b0);
      check(ckpt_resp_valid===1 && ckpt_resp_error===0,"complete access-clock response");
      check(actual==={{56'b0,oracle_value}},$sformatf("state index=%0d address=%0d got=%h expected=%h",index,address,actual,oracle_value));
      ckpt_bank=255; ckpt_slot=65535; ckpt_address=32'hffffffff;
      access_tick(); stalls++;
    end
    $fdisplay(fd,"%0d %0d %0d %016h",edges,index,address,ckpt_resp_data);
    ckpt_resp_ready=1; access_tick(); ckpt_resp_ready=0;
    check(ckpt_resp_valid===0 && edges==start_edges,"retired without target advancement");
    reads++; if(!pulse_frozen_clock) stopped_reads++;
  end
endtask
task capture;
  integer cut, before_reads;
  begin
    cut=edges; before_reads=reads; ckpt_freeze=1;
    // An enabled write to every way/byte must be harmless, whether the
    // functional clock remains stopped or pulses during the frozen transfer.
    io_req_valid=1; io_req_bits_write=1; io_req_bits_addr=0;
    io_req_bits_wdata=64'hfedcba9876543210; io_req_bits_way_en=255; io_req_bits_eccMask=255;
    #3;
    {chr(10).join(capture)}
    check(edges==cut && reads-before_reads==32832,"all owners at one cut");
    $display("INDEPENDENT_CLOCK_CAPTURE cycle=%0d words=%0d stopped=%0d",cut,reads-before_reads,!pulse_frozen_clock);
    captures++; io_req_valid=0; ckpt_freeze=0; pulse_frozen_clock=0;
  end
endtask
task work(input integer count);
  integer k;
  begin for(k=0;k<count;k++) begin
    io_req_valid=(k%7!=0); io_req_bits_write=(k%3!=0);
    io_req_bits_addr=((k*71+edges)%512)*8;
    io_req_bits_wdata=64'h9182736455aabbcc ^ (64'h0102040810204081*k);
    io_req_bits_way_en=(k*37+3); io_req_bits_eccMask=(k*53+7);
    functional_tick();
  end end
endtask
initial begin
  $dumpfile("debug.vcd"); $dumpvars(0,checkpoint_independent_clock_tb);
  fd=$fopen("capture.words","w"); check(fd!=0,"capture output");
  corrupt=$test$plusargs("semantic_corrupt");
  access_tick(); access_tick(); ckpt_reset=0;
  // Initialize every physical byte through ordinary requests, without deposits.
  for(i=0;i<512;i++) begin
    io_req_valid=1; io_req_bits_write=1; io_req_bits_addr=i*8;
    io_req_bits_way_en=255; io_req_bits_eccMask=255;
    io_req_bits_wdata=64'h0123456789abcdef ^ (64'h0101010101010101*i);
    functional_tick();
  end
  io_req_bits_write=0; io_req_bits_addr=8; functional_tick(); initialized=1; outputs();
  capture();
  work(97); io_req_valid=1; io_req_bits_write=0; functional_tick();
  pulse_frozen_clock=1; capture();
  work(257); io_req_valid=1; io_req_bits_write=0; functional_tick(); capture();
  work(83);
  check(captures==3 && reads==98496 && stopped_reads==65664 && frozen_clock_edges==131328,
        "complete stopped-clock and adversarial frozen-clock coverage");
  $fclose(fd);
  $display("INDEPENDENT_CLOCK_PASS checks=%0d edges=%0d reads=%0d stalls=%0d stopped_reads=%0d frozen_edges=%0d",checks,edges,reads,stalls,stopped_reads,frozen_clock_edges);
  $finish;
end
endmodule
'''


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
    out = Path(tempfile.mkdtemp(prefix='independent-clock-', dir=base))
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
                   '-debug_access+all', '+vcs+initreg+random', '-top', 'checkpoint_independent_clock_tb',
                   '-Mdir=' + str(out / 'csrc'), '-o', out / 'simv', generated / 'generated-bank.sv',
                   generated / 'reference.sv', out / 'bench.sv', out / 'sources' / SOURCES[-1]], out, 'compile.log')
    require(code == 0, f'VCS compile failed: {out / "compile.log"}')
    healthy = out / 'healthy'; healthy.mkdir()
    code, text = run([out / 'simv', '-no_save', '+vcs+initreg+0'], healthy, 'run.log')
    marker = re.search(r'INDEPENDENT_CLOCK_PASS checks=(\d+) edges=(\d+) reads=(\d+) stalls=(\d+) stopped_reads=(\d+) frozen_edges=(\d+)', text)
    require(code == 0 and marker is not None, f'VCS simulation failed: {healthy / "run.log"}')
    require(tuple(map(int, marker.groups()[1:])) == (952, 98496, 196992, 65664, 131328), 'incomplete execution')
    cuts = [dict(cycle=int(c), words=int(n), functional_clock_stopped=bool(int(s)))
            for c, n, s in re.findall(r'INDEPENDENT_CLOCK_CAPTURE cycle=(\d+) words=(\d+) stopped=(\d+)', text)]
    require([c['cycle'] for c in cuts] == [513, 611, 869] and all(c['words'] == 32832 for c in cuts), 'incomplete cuts')
    negative = out / 'semantic-negative'; negative.mkdir()
    code, bad = run([out / 'simv', '-no_save', '+vcs+initreg+0', '+semantic_corrupt'], negative, 'run.log')
    require(code == 1 and 'INDEPENDENT_CLOCK_FIRST_MISMATCH cycle=513 reads=0 frozen=1 state index=0' in bad and
            'INDEPENDENT_CLOCK_PASS' not in bad, 'corruption did not stop before first accepted state word')
    require((healthy / 'debug.vcd').stat().st_size > 1000, 'missing full debug waveform')
    (out / 'summary.json').write_text(json.dumps(dict(status='pass', backend='eda',
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), original_root=str(ROOT),
        scope='retained Rocket DCacheDataArray component only', root='DCacheDataArray',
        physical_fpga_capture=False, complete_cpu_acceptance=False, cuts=cuts,
        checks=int(marker[1]), functional_edges=int(marker[2]), reads=int(marker[3]), stalls=int(marker[4]),
        stopped_clock_reads=int(marker[5]), frozen_clock_edges=int(marker[6]), commands=commands,
        files={str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and
        not any(x in p.parts for x in ('csrc', 'simv.daidir')) and p.name != 'simv'}), indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
