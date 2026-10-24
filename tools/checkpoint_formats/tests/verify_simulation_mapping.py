"""Native linked-boundary bank synthesis and fresh EDA VCS fixture checks.

This is a one-register compiler fixture, never a CPU or FPGA capture receipt.
"""
import argparse
from datetime import datetime, timezone
import hashlib
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
from tools.checkpoint_formats.native_input_guard import require_live_inputs_unchanged
from tools.checkpoint_formats.semantic import manifest_hash

ROOT = Path(__file__).resolve().parents[3]
GENERATED = ('inner.fir', 'outer.fir', 'outer.anno.json', 'linked.fir', 'linked.anno.json',
             'bank.fir', 'bank.anno.json', 'manifest.json', 'binding.json', 'bank.sv', 'reference.sv')
SOURCES = ('sims/firesim/sim/midas/src/main/scala/midas/passes/SimulationMapping.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/core/SimWrapper.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedClockGateAdapter.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/passes/SimulationMappingSpec.scala',
           'tools/checkpoint_formats/tests/verify_simulation_mapping.py',
           'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(generated):
    target_class = 'midas.core.TargetBoxAnnotation'
    def targets(name):
        return [a['target'] for a in json.loads((generated / name).read_text()) if a['class'] == target_class]
    require(targets('outer.anno.json') == ['~Host|Host/sim:Wrapper/target:Placeholder'], 'wrong original boundary')
    require(targets('linked.anno.json') == ['~Host|Host/sim:Wrapper/target:FAMETop'], 'stale or missing linked boundary')
    linked = (generated / 'linked.fir').read_text()
    require('inst target of FAMETop' in linked and 'Placeholder' not in linked, 'replacement circuit mismatch')
    binding = json.loads((generated / 'binding.json').read_text())
    manifest = json.loads((generated / 'manifest.json').read_text())
    require(binding['reference_sha256'] == manifest['reference_sha256'] == sha(generated / 'linked.fir'), 'unbound linked IR')
    require(binding['instrumented_sha256'] == sha(generated / 'bank.fir') and
            binding['manifest_sha256'] == manifest_hash(manifest), 'unbound bank or manifest')
    require(binding['access_clock'] == 'ckpt_clock', 'missing independent access clock')
    require(len(binding['state']) == len(manifest['state']) == 1, 'incomplete linked state')
    row = binding['state'][0]
    require((row['hierarchy'], row['width'], row['depth']) == ('Host.sim.target.count', 8, 1), 'wrong linked owner')
    require(all(row[k] == manifest['state'][0][k] for k in ('state_id', 'hierarchy', 'width', 'depth')), 'state mismatch')
    specialized = targets('bank.anno.json')
    require(len(specialized) == 1 and re.fullmatch(
        r'~Host\|Host/sim:[A-Za-z_][A-Za-z0-9_]*/target:[A-Za-z_][A-Za-z0-9_]*', specialized[0]), 'lost concrete bank boundary')
    return row


TB = r'''`timescale 1ns/1ps
module simulation_mapping_tb;
import "DPI-C" function void checkpoint_network_fail();
reg clock=0, reference_clock=0, reset=1, ckpt_clock=0;
reg ckpt_freeze=0, ckpt_reset=1, ckpt_req_valid=0, ckpt_resp_ready=0;
reg [7:0] ckpt_bank=0;
reg [15:0] ckpt_slot=0;
reg [31:0] ckpt_address=0;
wire ckpt_req_ready, ckpt_resp_valid, ckpt_resp_error, ckpt_match;
wire [63:0] ckpt_resp_data, ckpt_data;
wire [7:0] value, reference_value;
Host dut(.*);
OriginalHost original(.clock(reference_clock),.reset(reset),.value(reference_value));
reg [7:0] expected=0;
integer cycle=0, checks=0, captures=0, stalls=0, j, fd;
bit corrupt=0;
task check(input bit ok,input string message);
begin checks++; if(!ok) begin
  $display("MAPPING_FIRST_DIVERGENCE cycle=%0d captures=%0d signal=%s",cycle,captures,message);
  checkpoint_network_fail();
end end endtask
task outputs;
begin check(value===expected && reference_value===expected,"value"); end endtask
task access_tick;
begin #2; ckpt_clock=1; #2; ckpt_clock=0; #2; outputs(); end endtask
task capture;
reg [63:0] actual;
integer cut;
begin
  cut=cycle; ckpt_freeze=1; ckpt_req_valid=1; ckpt_resp_ready=0;
  ckpt_bank=BANK; ckpt_slot=SLOT; ckpt_address=0; #1;
  check(ckpt_req_ready===1,"request_ready"); access_tick(); ckpt_req_valid=0;
  for(j=0;j<4;j++) begin
    actual=ckpt_resp_data ^ ((corrupt && cycle==17) ? 64'b1 : 64'b0);
    check(ckpt_resp_valid===1 && ckpt_resp_error===0,"response_status");
    check(actual==={56'b0,expected},"bank_word");
    // Exercise functional-clock activity at the frozen cut. The original
    // reference receives no edge, and both complete states must stay fixed.
    clock=1; #1; clock=0; outputs();
    ckpt_bank=255; ckpt_slot=65535; ckpt_address=32'hffffffff;
    access_tick(); stalls++;
  end
  $fdisplay(fd,"cycle=%0d value=%0d bank=%016h",cycle,value,ckpt_resp_data);
  ckpt_resp_ready=1; access_tick(); ckpt_resp_ready=0;
  check(ckpt_resp_valid===0 && cycle==cut,"retire_at_same_cut");
  captures++; ckpt_freeze=0;
end endtask
initial begin
  corrupt=$test$plusargs("corrupt");
  $dumpfile("mapping.vcd"); $dumpvars(0,simulation_mapping_tb);
  fd=$fopen("readback.log","w");
  // Functional reset initializes this bounded fixture. Logical cut labels
  // start after reset and never count access-clock or frozen clock pulses.
  #2; clock=1; reference_clock=1; #2; clock=0; reference_clock=0;
  access_tick(); ckpt_reset=0; reset=0; outputs(); capture();
  for(integer k=0;k<256;k++) begin
    outputs(); #3; clock=1; reference_clock=1; expected=expected+1; cycle++;
    #3; clock=0; reference_clock=0; #1; outputs();
    if(cycle==17 || cycle==128 || cycle==256) capture();
  end
  check(captures==4 && stalls==16,"complete_cuts");
  $fclose(fd);
  $display("SIMULATION_MAPPING_PASS checks=%0d cycles=%0d captures=%0d stalls=%0d",checks,cycle,captures,stalls);
  $finish;
end
endmodule
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('vivado', 'vcs'), required=True)
    args = parser.parse_args()
    base = args.out.resolve()
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence must be under runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='mapping-', dir=base))
    inputs = args.generated.resolve()
    generated_hashes = {n: sha(inputs / n) for n in GENERATED}
    source_hashes = {n: sha(ROOT / n) for n in SOURCES}
    for directory, source, names in (('generated', inputs, GENERATED), ('sources', ROOT, SOURCES)):
        for name in names:
            dest = out / directory / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, dest)
    row = audit(out / 'generated')
    commands = []
    def run(argv, name, expected=0):
        log = out / (name + '.log')
        with log.open('w') as stream:
            result = subprocess.run([str(a) for a in argv], cwd=out, stdout=stream, stderr=subprocess.STDOUT)
        commands.append(dict(argv=[str(a) for a in argv], cwd=str(out), returncode=result.returncode, log=str(log)))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require(result.returncode == expected, f'{name} exit {result.returncode}; inspect {log}')
        return log.read_text()
    checks = 0
    if args.mode == 'vivado':
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore'), 'native manager required')
        (out / 'synth.tcl').write_text('''read_verilog -sv generated/bank.sv
synth_design -top Host -part xcvu47p-fsvh2892-2-e -mode out_of_context
if {[llength [get_cells -hier -filter {IS_SEQUENTIAL == 1}]] < 8} {error "linked state lost"}
report_utilization -file utilization.rpt
write_checkpoint -force mapping.dcp
puts "SIMULATION_MAPPING_SYNTH_PASS"
''')
        text = run(['vivado', '-mode', 'batch', '-source', 'synth.tcl', '-log', 'vivado.log', '-journal', 'vivado.jou'], 'synthesis')
        require('SIMULATION_MAPPING_SYNTH_PASS' in text and (out / 'mapping.dcp').stat().st_size > 0, 'incomplete synthesis')
    else:
        require(os.environ.get('VCS_HOME') == toolchain.VCS_HOME and Path(toolchain.VCS).is_file(), 'EDA VCS setup required')
        bench = TB.replace('BANK', str(row['bank'])).replace('SLOT', str(row['slot']))
        (out / 'bench.sv').write_text(bench)
        run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-debug_access+all',
             '-Mupdate', '-top', 'simulation_mapping_tb', '-o', out / 'simv',
             out / 'generated/bank.sv', out / 'generated/reference.sv', out / 'bench.sv',
             out / 'sources/tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc'], 'compile')
        text = run([out / 'simv', '-no_save'], 'simulation')
        match = re.search(r'SIMULATION_MAPPING_PASS checks=(\d+) cycles=256 captures=4 stalls=16', text)
        require(match is not None, 'incomplete readback')
        checks = int(match[1])
        (out / 'mapping.vcd').rename(out / 'healthy.vcd')
        (out / 'readback.log').rename(out / 'healthy-readback.log')
        negative = run([out / 'simv', '-no_save', '+corrupt'], 'semantic-corruption', 1)
        require('MAPPING_FIRST_DIVERGENCE cycle=17 captures=1 signal=bank_word' in negative and
                'SIMULATION_MAPPING_PASS' not in negative, 'wrong first divergence')
        (out / 'mapping.vcd').rename(out / 'corrupt.vcd')
    require_live_inputs_unchanged([dict(path=str(base_path / name), sha256=digest)
                                   for base_path, hashes in ((ROOT, source_hashes), (inputs, generated_hashes))
                                   for name, digest in hashes.items()])
    summary = dict(status='pass', backend='eda' if args.mode == 'vcs' else 'f2',
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   scope='one-register native-link/bank compiler fixture only', physical_fpga_capture=False,
                   generated=generated_hashes, sources=source_hashes, checks=checks, commands=commands,
                   artifacts={str(p): sha(p) for p in out.iterdir() if p.is_file()})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
