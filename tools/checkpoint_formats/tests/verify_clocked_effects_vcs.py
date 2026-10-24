"""EDA component verification of bank freeze for effects and retained Rocket DTLB.

The DTLB input is a retained exact-recipe subtree, not a newly generated whole
Rocket simulator. Original RTL hierarchy reads are independent test oracles;
only synthesized public bank ports provide the captured values. No F2 capture
or complete CPU acceptance is established here.
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

ROOT = Path(__file__).resolve().parents[3]
GENERATED = ('generated-bank-input.fir', 'generated-bank.fir', 'generated-bank.sv',
             'reference.sv', 'generated-bank-manifest.json', 'generated-bank-binding.json')
SOURCES = ('sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedClockGateAdapter.scala',
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedSynthesisConstantAdapter.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAnnotations.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/ClockedEffectsStateBankSpec.scala',
           'tools/checkpoint_formats/tests/verify_clocked_effects_vcs.py',
           'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bench(directory, binding, manifest):
    root = manifest['root_module']
    text = (directory / 'generated-bank-input.fir').read_text()
    body = re.search(r'^  module ' + re.escape(root) + r'\s*:.*?(?=^  (?:ext)?module |\Z)', text, re.M | re.S)[0]
    ports = re.findall(r'^    (input|output) (\w+) : (Clock|[US]Int<\d+>)', body, re.M)
    require(ports and sum(t == 'Clock' for _, _, t in ports) == 1, 'single-clock test contract required')
    declarations, connections, output_checks, randomize = [], [], [], []
    for direction, name, typ in ports:
        if typ == 'Clock':
            require(name == 'clock' and direction == 'input', 'unexpected clock contract')
            connections.append('.clock(reference_clock)')
            continue
        width = int(re.search(r'\d+', typ)[0])
        shape = f'[{width-1}:0] ' if width > 1 else ''
        if direction == 'input':
            declarations.append(f'reg {shape}{name}=0;')
            connections.append(f'.{name}({name})')
            if name not in ('reset', 'fault', 'eventEnable', 'io_sfence_valid'):
                randomize.append(f'{name}={{$urandom,$urandom,$urandom,$urandom}};')
        else:
            declarations += [f'wire {shape}{name};', f'wire {shape}reference_{name};']
            connections.append(f'.{name}(reference_{name})')
            output_checks.append(f'check({name} === reference_{name}, "output {name}");')
    # The original reference receives exactly the functional edges, never bank
    # transfer edges. Its storage is observed only by this independent oracle.
    rows = binding['state']
    require(len(rows) == len(manifest['state']), 'incomplete descriptor coverage')
    dense = root == 'DenseStorage'
    if dense:
        expected_paths = {f'DenseStorage.word_{i}' for i in range(257)} | {
            f'DenseStorage.child_{name}.saved' for name in 'abc'}
        require({row['hierarchy'] for row in rows} == expected_paths and len(rows) == 260,
                'incomplete dense local/repeated-child inventory')
    captures = []
    for index, row in enumerate(rows):
        require(row['width'] <= 64 and row['depth'] == 1, 'register-only subtree oracle required')
        original = 'original.' + row['hierarchy'].removeprefix(root + '.')
        if dense:
            name = row['hierarchy'].removeprefix(root + '.')
            if name.startswith('word_'):
                word = int(name.removeprefix('word_'))
                require(row['width'] == word % 64 + 1, 'dense state width differs from public-input oracle')
                expected = f"((64'd{word} + model_sum + model_steps * 64'd{word + 1}) & 64'h{(1 << row['width']) - 1:016x})"
            else:
                require(row['width'] == 64, 'dense child width differs from public-input oracle')
                expected = "(64'd9 + model_sum)"
            captures.append(f'check($unsigned({original}) === {expected}, "dense original/public-input oracle {index}");')
            captures.append(f'read_word({row["bank"]}, {row["slot"]}, {expected}, {index});')
            continue
        captures.append(f'read_word({row["bank"]}, {row["slot"]}, $unsigned({original}), {index});')
    effects = root == 'EffectsStorage'
    constant = root == 'SynthesisConstantStorage'
    if constant:
        output_checks.append('check(fixed === 9\'d341, "exact FPGA synthesis default despite process plusarg");')
    adverse = ('data=64\'hffffffffffffffff;' if dense else 'data=17\'h1abcd;' if constant else 'eventEnable=1; fault=1;' if effects else
               'io_sfence_valid=1; io_sfence_bits_rs1=1; io_sfence_bits_addr=0;')
    restore = 'data=0;' if constant or dense else 'fault=0; eventEnable=0;' if effects else 'io_sfence_valid=0;'
    event_drive = 'eventEnable=(i%3==0);' if effects else ''
    fault_trial = """if ($test$plusargs("functional_stop") || $test$plusargs("functional_assert")) begin
    ckpt_freeze=1; fault=1; eventEnable=$test$plusargs("functional_assert");
    repeat(8) tick();
    fault_test=1; ckpt_freeze=0;
    $display("FUNCTIONAL_EFFECT_ARMED"); tick();
    if ($test$plusargs("functional_assert")) begin
      $display("FUNCTIONAL_ASSERT_OBSERVATION_END"); checkpoint_network_fail();
    end
    $display("FUNCTIONAL_EFFECT_MISSING"); checkpoint_network_fail();
  end""" if effects else '' 
    invalid_task = '''task invalid_dense_read(input integer bank, input integer slot, input [31:0] address);
  begin
    ckpt_bank=bank; ckpt_slot=slot; ckpt_address=address;
    ckpt_req_valid=1; ckpt_resp_ready=0; #1;
    check(ckpt_match===0 && ckpt_data===0 && ckpt_req_ready===1,"invalid selector zero miss");
    tick(); ckpt_req_valid=0;
    ckpt_bank=0; ckpt_slot=0; ckpt_address=0;
    repeat(3) begin
      #1;
      check(ckpt_resp_valid===1 && ckpt_resp_error===1 && ckpt_resp_data===0,"held invalid selector response");
      tick();
    end
    ckpt_resp_ready=1; tick(); ckpt_resp_ready=0;
    check(ckpt_resp_valid===0,"invalid response retired");
  end
endtask''' if dense else ''
    invalid_calls = "invalid_dense_read(255,65535,0); invalid_dense_read(0,65535,0); invalid_dense_read(0,0,1); invalid_dense_read(0,0,32'hffffffff);" if dense else ""
    return f'''`timescale 1ns/1ps
module checkpoint_effects_tb;
import "DPI-C" function void checkpoint_network_fail();
reg clock=0, reference_clock=0;
{chr(10).join(declarations)}
reg ckpt_freeze=0, ckpt_reset=1, ckpt_req_valid=0, ckpt_resp_ready=0;
reg [7:0] ckpt_bank=0;
reg [15:0] ckpt_slot=0;
reg [31:0] ckpt_address=0;
wire ckpt_req_ready, ckpt_resp_valid, ckpt_resp_error, ckpt_match;
wire [63:0] ckpt_resp_data, ckpt_data;
{root} dut(.*);
Original{root} original({','.join(connections)});
integer checks=0, edges=0, reads=0, stalls=0, captures=0, i, j, fd;
reg [63:0] model_sum=0, model_steps=0;
bit corrupt=0, fault_test=0;
task check(input bit condition, input string message);
  begin
    checks++;
    if (!condition) begin
      $display("EFFECTS_FIRST_MISMATCH cycle=%0d reads=%0d frozen=%0d %s",edges,reads,ckpt_freeze,message);
      checkpoint_network_fail();
    end
  end
endtask
task tick;
  begin
    $display("EFFECTS_TICK frozen=%0d cycle=%0d",ckpt_freeze,edges);
    {'if (!ckpt_freeze) $display("SYNTHESIS_CONSTANT_INPUT cycle=%0d reset=%0d data=%0d",edges,reset,data);' if constant else ''}
    {'if (!ckpt_freeze) $display("DENSE_INPUT cycle=%0d reset=%0d data=%0d",edges,reset,data);' if dense else ''}
    #5; clock=1;
    if (!ckpt_freeze) begin
      if (!fault_test) reference_clock=1;
      {'if (reset) begin model_sum=0; model_steps=0; end else begin model_sum=model_sum+data; model_steps=model_steps+1; end' if dense else ''}
      edges++;
    end
    #1; clock=0; reference_clock=0; #4;
    if (!fault_test) begin
      {chr(10).join(output_checks)}
    end
  end
endtask
task read_word(input integer bank, input integer slot, input [63:0] expected, input integer index);
  reg [63:0] actual;
  begin
    ckpt_bank=bank; ckpt_slot=slot; ckpt_address=0;
    ckpt_req_valid=1; ckpt_resp_ready=0; #1;
    check(ckpt_req_ready===1,"ready"); tick(); ckpt_req_valid=0;
    for(j=0;j<4;j++) begin
      #1;
      actual=ckpt_resp_data ^ ((corrupt && index==0) ? 64'b1 : 64'b0);
      check(ckpt_resp_valid===1 && ckpt_resp_error===0,"valid complete bank response");
      check(actual===expected,$sformatf("state index=%0d got=%h expected=%h",index,actual,expected));
      ckpt_bank=255; ckpt_slot=65535; ckpt_address=32'hffffffff;
      tick(); stalls++;
    end
    $fdisplay(fd,"%0d %0d %016h",edges,index,ckpt_resp_data);
    ckpt_resp_ready=1; tick(); ckpt_resp_ready=0;
    check(ckpt_resp_valid===0,"response retired"); reads++;
  end
endtask
{invalid_task}
task capture;
  integer cut;
  begin
    cut=edges; ckpt_freeze=1; reset=1; {adverse}
    {chr(10).join(captures)}
    {invalid_calls}
    check(edges==cut,"no functional edge during capture");
    $display("EFFECTS_CAPTURE cycle=%0d words={len(rows)}",cut); captures++;
    {restore} reset=0; ckpt_freeze=0;
  end
endtask
initial begin
  $dumpfile("debug.vcd"); $dumpvars(0,checkpoint_effects_tb);
  fd=$fopen("capture.words","w"); check(fd!=0,"capture output");
  corrupt=$test$plusargs("semantic_corrupt");
  reset=1; tick(); tick(); ckpt_reset=0; reset=0;
  capture();
  {fault_trial}
  for(i=0;i<37;i++) begin {''.join(randomize)} {event_drive} tick(); end
  capture();
  for(i=0;i<93;i++) begin {''.join(randomize)} {event_drive} tick(); end
  capture();
  for(i=0;i<41;i++) begin {''.join(randomize)} {event_drive} tick(); end
  check(captures==3 && reads=={len(rows)*3},"all cuts and descriptors");
  $fclose(fd);
  $display("CLOCKED_EFFECTS_PASS root={root} checks=%0d edges=%0d reads=%0d stalls=%0d",checks,edges,reads,stalls);
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
            'run on EDA; source vcs-env.sh LAST')
    base = args.out.resolve()
    require(base.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='clocked-effects-', dir=base))
    constant = (args.generated / 'plusarg_reader.v').is_file()
    generated_names = (*GENERATED, 'plusarg_reader.v', 'original-input.fir', 'original-annotations.json',
                       'prepared-annotations.json') if constant else GENERATED
    source_names = (*SOURCES, 'sims/firesim/sim/midas/src/test/scala/midas/checkpoint/SynthesisConstantBankSpec.scala') if constant else SOURCES
    for label, source, names in [('generated', args.generated.resolve(), generated_names), ('sources', ROOT, source_names)]:
        for name in names:
            target = out / label / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
    snapshots = out / 'generated'
    binding = json.loads((snapshots / 'generated-bank-binding.json').read_text())
    manifest = json.loads((snapshots / 'generated-bank-manifest.json').read_text())
    for key, name in [('reference_sha256', 'generated-bank-input.fir'), ('instrumented_sha256', 'generated-bank.fir'),
                      ('manifest_sha256', 'generated-bank-manifest.json')]:
        require(binding[key] == sha(snapshots / name), 'unbound generated input: ' + key)
    (out / 'bench.sv').write_text(bench(snapshots, binding, manifest))
    commands = []

    def run(argv, directory, name):
        command = dict(argv=[str(a) for a in argv], cwd=str(directory), log=str(directory / name))
        commands.append(command)
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        with (directory / name).open('w') as log:
            result = subprocess.run(command['argv'], cwd=directory, stdout=log, stderr=subprocess.STDOUT)
        command['returncode'] = result.returncode
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        return result.returncode, (directory / name).read_text()

    code, _ = run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate',
                   '-debug_access+all', '+vcs+initreg+random', '-top', 'checkpoint_effects_tb',
                   '-Mdir=' + str(out / 'csrc'), '-o', out / 'simv', snapshots / 'generated-bank.sv',
                   snapshots / 'reference.sv', out / 'bench.sv', out / 'sources' / SOURCES[-1],
                   *(['+define+SYNTHESIS', snapshots / 'plusarg_reader.v'] if constant else [])], out, 'compile.log')
    require(code == 0, f'VCS compile failed: {out / "compile.log"}')
    healthy = out / 'healthy'; healthy.mkdir()
    extra_args = ['+checkpoint_constant=99'] if constant else []
    code, text = run([out / 'simv', '-no_save', '+vcs+initreg+0', *extra_args], healthy, 'run.log')
    match = re.search(r'CLOCKED_EFFECTS_PASS root=(\w+) checks=(\d+) edges=(\d+) reads=(\d+) stalls=(\d+)', text)
    require(code == 0 and match is not None, f'VCS simulation failed: {healthy / "run.log"}')
    require(int(match[3]) == 173 and int(match[4]) == len(binding['state']) * 3 and
            int(match[5]) == len(binding['state']) * 12, 'incomplete capture coverage')
    frozen = False
    effect_count = 0
    for line in text.splitlines():
        if line.startswith('EFFECTS_TICK '):
            frozen = 'frozen=1' in line
        if 'CHECKPOINT_EFFECT data=' in line:
            require(not frozen, 'side effect escaped frozen bank cut')
            effect_count += 1
    if match[1] == 'EffectsStorage':
        require(effect_count == 116, 'functional printf lost or duplicated')
    negative = out / 'semantic-negative'; negative.mkdir()
    code, bad = run([out / 'simv', '-no_save', '+vcs+initreg+0', '+semantic_corrupt', *extra_args], negative, 'run.log')
    require(code == 1 and 'EFFECTS_FIRST_MISMATCH cycle=2 reads=0 frozen=1 state index=0' in bad and
            'CLOCKED_EFFECTS_PASS' not in bad, 'semantic corruption failed to stop at first frozen word')
    effect_negatives = []
    if match[1] == 'EffectsStorage':
        for mode in ('functional_stop', 'functional_assert'):
            case = out / mode; case.mkdir()
            code, fault = run([out / 'simv', '-no_save', '+vcs+initreg+0', '+' + mode], case, 'run.log')
            require('FUNCTIONAL_EFFECT_ARMED' in fault and 'FUNCTIONAL_EFFECT_MISSING' not in fault and
                    'CLOCKED_EFFECTS_PASS' not in fault and 'EFFECTS_FIRST_MISMATCH' not in fault,
                    'functional effect was lost after release: ' + mode)
            if mode == 'functional_stop':
                require('Fatal:' in fault, 'released stop did not terminate')
            else:
                # FIRRTL emits an immediate assertion with the default $error
                # action, not $fatal. Preserve that policy and audit its native
                # diagnostic on the first released edge before the bench exits.
                diagnostic = re.search(r'started at (\d+)ps failed at (\d+)ps', fault)
                require(code == 1 and diagnostic is not None and diagnostic[1] == diagnostic[2] and
                        'FUNCTIONAL_ASSERT_OBSERVATION_END' in fault and
                        fault.index('FUNCTIONAL_EFFECT_ARMED') < diagnostic.start() <
                        fault.index('FUNCTIONAL_ASSERT_OBSERVATION_END'), 'released assertion failed to report')
            effect_negatives.append(dict(mode=mode, returncode=code, observed_after_release=True))
    (out / 'summary.json').write_text(json.dumps(dict(status='pass', backend='eda',
        observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(), original_root=str(ROOT),
        scope='component generated-bank capture and original RTL oracle only', physical_fpga_capture=False,
        complete_cpu_acceptance=False, root=match[1], checks=int(match[2]), functional_edges=int(match[3]),
        reads=int(match[4]), stalls=int(match[5]), effects=effect_count, functional_effect_negatives=effect_negatives,
        cuts=[dict(cycle=int(c), words=int(n)) for c,n in re.findall(r'EFFECTS_CAPTURE cycle=(\d+) words=(\d+)', text)],
        commands=commands, files={str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and
        not any(x in p.parts for x in ('csrc', 'simv.daidir')) and p.name != 'simv'}), indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
