"""Independent post-mapping inline provenance and fresh EDA VCS equivalence.

The fixture has repeated register/RAM owners. This is compiler/component
evidence, not FPGA capture or CPU migration acceptance.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(generated):
    generated = Path(generated)
    doc = json.loads((generated / 'receipt.json').read_text())
    assert doc['version'] == 1 and doc['producer'] == 'midas.passes.ResolveSimulationInline'
    assert doc['circuit'] == 'InlineFixture'
    for key, name in [('input_sha256', 'input.fir'), ('output_sha256', 'output.fir'),
                      ('input_annotations_sha256', 'input-annotations.json'),
                      ('output_annotations_sha256', 'output-annotations.json')]:
        assert doc[key] == sha(generated / name), ('unbound inline input/output', key)
    request = {'class': 'firrtl.stage.RunFirrtlTransformAnnotation', 'transform': 'firrtl.passes.InlineInstances'}
    inline = {'class': 'firrtl.passes.InlineAnnotation', 'target': 'InlineFixture.Leaf'}
    assert doc['request'] == [request] and doc['inline_annotations'] == [inline]
    before = json.loads((generated / 'input-annotations.json').read_text())
    after = json.loads((generated / 'output-annotations.json').read_text())
    assert before.count(request) == before.count(inline) == 1
    assert not any(a.get('class') in (request['class'], inline['class']) for a in after)
    touches = [a['target'] for a in after if a['class'] == 'firrtl.transforms.DontTouchAnnotation']
    assert sorted(touches) == ['~InlineFixture|InlineFixture>left_time', '~InlineFixture|InlineFixture>right_time']
    expected = []
    for inst in ('left', 'right'):
        for owner, shape in [('time', 'register:UInt<8>'), ('ram', 'memory:UInt<8>:4:0:1:undefined')]:
            expected.append(dict(from_=f'~InlineFixture|InlineFixture/{inst}:Leaf>{owner}',
                                 to=f'~InlineFixture|InlineFixture>{inst}_{owner}', shape=shape))
    expected = [dict({'from': r.pop('from_')}, **r) for r in expected]
    assert sorted(doc['storage'], key=lambda r: r['from']) == sorted(expected, key=lambda r: r['from'])
    assert isinstance(doc['renames'], str) and doc['renames']
    assert set(doc) == {'version', 'producer', 'circuit', 'request', 'inline_annotations', 'storage', 'renames',
                        'input_sha256', 'output_sha256', 'input_annotations_sha256', 'output_annotations_sha256'}
    output = (generated / 'output.fir').read_text()
    assert 'inst left of Leaf' not in output and 'inst right of Leaf' not in output
    for inst in ('left', 'right'):
        assert re.search(r'\breg ' + inst + r'_time : UInt<8>', output)
        assert re.search(r'\bmem ' + inst + r'_ram :', output)
    return dict(storage_instances=len(expected), repeated_registers=2, repeated_memories=2,
                receipt_sha256=sha(generated / 'receipt.json'))


TB = r'''module simulation_inline_tb;
  reg clock = 0, reset = 1, wen = 0;
  reg [7:0] data = 0;
  reg [1:0] addr = 0;
  wire [7:0] ref_value, ref_read, dut_value, dut_read;
  InlineReference reference (.clock(clock), .reset(reset), .data(data), .addr(addr), .wen(wen),
    .value(ref_value), .read(ref_read));
  InlineFixture dut (.clock(clock), .reset(reset), .data(data), .addr(addr), .wen(wen),
    .value(dut_value), .read(dut_read));
  integer checks = 0;
  initial begin
    $dumpfile("inline.vcd"); $dumpvars(0, simulation_inline_tb);
    for (integer cycle = 0; cycle < 512; cycle = cycle + 1) begin
      clock = 0;
      reset = cycle < 8 || cycle % 53 == 0;
      addr = cycle < 8 ? cycle % 4 : (cycle * 7 + cycle / 5) % 4;
      data = cycle * 17 + cycle / 7;
      wen = cycle < 8 || cycle % 5 != 0;
      #5;
      if (cycle >= 8) begin
        if ({dut_value, dut_read} !== {ref_value, ref_read})
          $fatal(1, "INLINE_DIVERGENCE cycle=%0d ref=%h/%h actual=%h/%h",
            cycle, ref_value, ref_read, dut_value, dut_read);
        if ($isunknown({dut_value, dut_read})) $fatal(1, "unknown initialized state cycle=%0d", cycle);
        checks = checks + 2;
      end
      clock = 1; #5;
      if (cycle >= 8) begin
        if ({dut_value, dut_read} !== {ref_value, ref_read}) $fatal(1, "INLINE_EDGE_DIVERGENCE cycle=%0d", cycle);
        checks = checks + 2;
      end
    end
    $display("SIMULATION_INLINE_PASS checks=%0d cycles=512", checks); $finish;
  end
endmodule
'''


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--generated', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--mode', choices=('audit', 'vcs', 'vivado'), default='audit')
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='inline-', dir=args.out)).resolve()
    generated = args.generated.resolve()
    positive = audit(generated)
    rejected = []
    original = json.loads((generated / 'receipt.json').read_text())
    import copy
    import shutil
    for name in ('request', 'missing-word', 'alias', 'shape', 'target', 'input-hash', 'output-hash', 'schema',
                 'annotation-hash', 'empty-renames', 'stale-input', 'stale-output', 'stale-annotation'):
        test = out / 'negative' / name
        shutil.copytree(generated, test)
        doc = copy.deepcopy(original)
        if name == 'request': doc['request'][0]['transform'] = 'firrtl.VerilogEmitter'
        elif name == 'missing-word': doc['storage'].pop()
        elif name == 'alias': doc['storage'][1]['to'] = doc['storage'][0]['to']
        elif name == 'shape': doc['storage'][0]['shape'] = 'register:UInt<9>'
        elif name == 'target': doc['storage'][0]['to'] += '_absent'
        elif name == 'input-hash': doc['input_sha256'] = '0' * 64
        elif name == 'output-hash': doc['output_sha256'] = '0' * 64
        elif name == 'schema': doc['deployable_capture_image'] = True
        elif name == 'annotation-hash': doc['output_annotations_sha256'] = '0' * 64
        elif name == 'empty-renames': doc['renames'] = ''
        elif name.startswith('stale-'):
            filename = {'stale-input': 'input.fir', 'stale-output': 'output.fir',
                        'stale-annotation': 'output-annotations.json'}[name]
            with (test / filename).open('a') as stream: stream.write(' ')
        (test / 'receipt.json').write_text(json.dumps(doc))
        try:
            audit(test)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError('accepted inline corruption: ' + name)
    commands = []
    def run(argv, name):
        commands.append(dict(argv=[str(a) for a in argv], cwd=str(out)))
        with (out / (name + '.log')).open('w') as log:
            r = subprocess.run(commands[-1]['argv'], cwd=out, stdout=log, stderr=subprocess.STDOUT)
        commands[-1]['returncode'] = r.returncode
        assert r.returncode == 0, out / (name + '.log')
    checks = None
    if args.mode == 'vcs':
        (out / 'reference.sv').write_text((generated / 'reference.sv').read_text().replace(
            'module InlineFixture(', 'module InlineReference('))
        (out / 'inlined.sv').write_bytes((generated / 'inlined.sv').read_bytes())
        (out / 'tb.sv').write_text(TB)
        run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
             '-top', 'simulation_inline_tb', '-o', 'simv', 'reference.sv', 'inlined.sv', 'tb.sv'], 'compile')
        run([out / 'simv', '-no_save'], 'simulate')
        assert 'SIMULATION_INLINE_PASS checks=2016 cycles=512' in (out / 'simulate.log').read_text()
        assert (out / 'inline.vcd').stat().st_size > 0
        checks = 2016
    if args.mode == 'vivado':
        (out / 'inlined.sv').write_bytes((generated / 'inlined.sv').read_bytes())
        (out / 'synth.tcl').write_text('''read_verilog -sv inlined.sv
synth_design -top InlineFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context
if {[llength [get_cells -hier -filter {IS_SEQUENTIAL == 1}]] == 0} { error "inline storage missing" }
report_utilization -file utilization.rpt
write_checkpoint -force inline.dcp
''')
        run(['vivado', '-mode', 'batch', '-source', 'synth.tcl', '-log', 'vivado.log',
             '-journal', 'vivado.jou'], 'synthesis')
        assert (out / 'inline.dcp').stat().st_size > 0
    source_paths = [Path('sims/firesim/sim/midas/src') / p for p in (
        'main/scala/midas/passes/ResolveSimulationInline.scala',
        'main/scala/midas/stage/GoldenGateCompilerPhase.scala',
        'main/scala/midas/passes/GoldenGateDedupGroups.scala',
        'main/scala/midas/passes/CheckpointGroupDedupModules.scala',
        'main/scala/midas/passes/EnableAndRunDedupOnce.scala',
        'main/scala/midas/checkpoint/SimulatorBankProbeContext.scala',
        'test/scala/midas/passes/ResolveSimulationInlineSpec.scala',
        'test/scala/midas/stage/GoldenGateHostPipelineSpec.scala')]
    source_paths.append(Path(__file__))
    result = dict(status='pass', scope='post-mapping inline compiler/component only; no FPGA capture',
                  backend='eda' if args.mode == 'vcs' else 'f2', positive=positive, rejected=rejected,
                  vcs_checks=checks, commands=commands,
                  inputs={str(p): sha(p) for p in generated.iterdir() if p.is_file()},
                  sources={str(p.resolve()): sha(p) for p in source_paths},
                  artifacts={str(p): sha(p) for p in out.iterdir() if p.is_file()})
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
