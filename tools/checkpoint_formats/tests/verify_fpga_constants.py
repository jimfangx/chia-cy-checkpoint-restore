"""Verify explicit production FPGA constant selection using native tools.

VCS runs only on EDA. Vivado runs only on the native manager. The unchanged
original model is tested in both SYNTHESIS and ordinary runtime-plusarg modes.
This fixture is compiler/branch evidence, never a checkpoint-enabled CPU image.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.native_input_guard import require_live_inputs_unchanged
from tools.checkpoint_formats.tests.audit_fpga_constants import audit

ROOT = Path(__file__).resolve().parents[3]
GENERATED = tuple('fpga-constants-'+n for n in [
    'original.fir', 'prepared.fir', 'sources.json', 'preparation.json', 'emission.json']) + (
    'selected.sv', 'ordinary.sv', 'plusarg_reader.v', 'selected-reference.fir', 'selected-manifest.json')
SOURCES = ('sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SimulatorFPGASynthesisConstants.scala',
           'tools/checkpoint_formats/native_input_guard.py',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedSynthesisConstantAdapter.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/stage/GoldenGateCompilerPhase.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/stage/FPGASynthesisConstantsSpec.scala',
           'tools/checkpoint_formats/tests/audit_fpga_constants.py',
           'tools/checkpoint_formats/tests/verify_fpga_constants.py',
           'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc')
BENCH = '''`timescale 1ns/1ps
module fpga_constants_tb;
import "DPI-C" function void checkpoint_network_fail();
reg clock=0, reset=1;
reg [16:0] data=0;
wire [31:0] result;
wire [8:0] fixed;
FPGAConstants dut(.*);
integer expected_constant, i, checks=0, edges=0;
reg [31:0] expected_result=0;
task check(input bit condition, input string message);
  begin
    checks++;
    if (!condition) begin
      $display("FPGA_CONSTANT_MISMATCH cycle=%0d edges=%0d %s", i, edges, message);
      checkpoint_network_fail();
    end
  end
endtask
initial begin
  $dumpfile("fpga-constants.vcd"); $dumpvars(0,fpga_constants_tb);
  if (!$value$plusargs("expected_constant=%d",expected_constant)) checkpoint_network_fail();
  for (i=0;i<1025;i++) begin
    reset=(i==0);
    data=((i*33)^17'h1a35b)&17'h1ffff;
    #2;
    // Compare before acknowledging this edge. The negative must stop at zero.
    check(fixed === (expected_constant ^ ($test$plusargs("corrupt") ? 1 : 0)), "source branch/default");
    expected_result=reset ? 0 : expected_result+data+expected_constant;
    #3; clock=1; edges++;
    #1; check(result === expected_result,"independent arithmetic continuation");
    clock=0; #4;
  end
  $display("FPGA_CONSTANT_PASS checks=%0d edges=%0d constant=%0d", checks,edges,expected_constant);
  $finish;
end
endmodule
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=['vcs', 'vivado'], required=True)
    args = parser.parse_args()
    base = args.out.resolve()
    require(base.is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='fpga-constants-', dir=base))
    pinned = []
    for label, root, names in [('generated', args.generated.resolve(), GENERATED), ('sources', ROOT, SOURCES)]:
        for name in names:
            target = out/label/name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root/name).read_bytes())
            pinned.append(dict(path=str(root/name), sha256=sha(target)))
    require_live_inputs_unchanged(pinned)
    generated = out/'generated'
    coverage = audit(*(generated/('fpga-constants-'+n) for n in [
        'original.fir', 'prepared.fir', 'sources.json', 'preparation.json', 'emission.json']), generated/'selected.sv')
    require(coverage['replaced_definitions'] == 1 and coverage['reachable_constant_instances'] == 2,
            'incomplete repeated constant fixture')
    commands = []

    def run(argv, cwd, name, expected=0):
        row = dict(argv=[str(a) for a in argv], cwd=str(cwd), log=str(out/name))
        commands.append(row)
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        with (out/name).open('w') as stream:
            result = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        require(result.returncode == expected, 'native failure; inspect '+str(out/name))
        return (out/name).read_text()

    if args.mode == 'vcs':
        require(Path(toolchain.VCS).is_file() and os.environ.get('VCS_HOME') == toolchain.VCS_HOME,
                'EDA with vcs-env.sh sourced last required')
        (out/'bench.sv').write_text(BENCH)
        for label, source, defines, expected in [
            ('selected', 'selected.sv', [], 341),
            ('original-fpga', 'ordinary.sv', ['+define+SYNTHESIS'], 341),
            ('ordinary-runtime', 'ordinary.sv', [], 17)]:
            work = out/label; work.mkdir()
            run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate',
                 '-debug_access+all', '-top', 'fpga_constants_tb', '-Mdir='+str(work/'csrc'),
                 '-o', work/'simv', *defines, generated/source, generated/'plusarg_reader.v',
                 out/'bench.sv', out/'sources/tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc'],
                work, label+'-compile.log')
            text = run([work/'simv', '-no_save', '+checkpoint_constant=17', '+expected_constant='+str(expected)],
                       work, label+'-run.log')
            require(f'FPGA_CONSTANT_PASS checks=2050 edges=1025 constant={expected}' in text,
                    'missing full branch/continuation comparisons')
        negative = out/'negative'; negative.mkdir()
        text = run([out/'selected/simv', '-no_save', '+checkpoint_constant=17', '+expected_constant=341', '+corrupt'],
                   negative, 'negative-run.log', 1)
        require('FPGA_CONSTANT_MISMATCH cycle=0 edges=0' in text and 'FPGA_CONSTANT_PASS' not in text,
                'negative did not stop before its first edge')
    else:
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),
                'native manager Vivado required')
        script = out/'synth.tcl'
        script.write_text('''set_param general.maxThreads 4
create_project -in_memory -part xcvu47p-fsvh2892-2-e
read_verilog -sv generated/selected.sv
synth_design -top FPGAConstants -part xcvu47p-fsvh2892-2-e -mode out_of_context
create_clock -period 7.142857 [get_ports clock]
opt_design
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force FPGAConstants.dcp
puts "FPGA_CONSTANT_SYNTH_PASS"
close_project
''')
        text = run(['vivado', '-mode', 'batch', '-source', script, '-log', 'vivado.log',
                    '-journal', 'vivado.jou'], out, 'vivado-command.log')
        require('FPGA_CONSTANT_SYNTH_PASS' in text and (out/'FPGAConstants.dcp').stat().st_size,
                'missing synthesized constant fixture')
    require_live_inputs_unchanged(pinned)
    summary = dict(status='pass', backend='eda' if args.mode == 'vcs' else 'f2',
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   original_root=str(ROOT), scope='production FPGA branch selection fixture only',
                   physical_fpga_capture=False, full_rocket_image_build=False, commands=commands, coverage=coverage,
                   generated={n: sha(generated/n) for n in GENERATED}, sources={n: sha(out/'sources'/n) for n in SOURCES},
                   artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                              if p.is_file() and p.suffix in ('.log', '.rpt', '.dcp', '.vcd', '.tcl', '.sv')})
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
