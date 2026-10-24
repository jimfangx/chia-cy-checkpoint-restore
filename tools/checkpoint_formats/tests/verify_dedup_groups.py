"""Independent group-dedup provenance, native synthesis and EDA VCS equivalence.

This is compiler/component evidence. It cannot establish FPGA checkpoint capture.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.native_input_guard import require_live_inputs_unchanged


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(doc):
    return hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def audit(generated):
    generated = Path(generated)
    policy = json.loads((generated / 'policy.json').read_text())
    result = json.loads((generated / 'result.json').read_text())
    retired = json.loads((generated / 'retirement.json').read_text())
    for doc in (policy, result, retired):
        assert doc['version'] == 1 and doc['circuit'] == 'GroupFixture'
        assert doc['policy'] == 'firrtl-1.6-group-aware-forced-dedup-v1'
    groups = [dict(**{'class': 'firrtl.transforms.DedupGroupAnnotation'},
                   target='~GroupFixture|' + module, group=group)
              for module, group in [('A', 'alpha'), ('A2', 'alpha'), ('B', 'beta'), ('B2', 'beta')]]
    assert policy['groups'] == result['groups'] == groups
    outputs = [groups[0], groups[2]]
    assert result['output_groups'] == retired['groups'] == outputs
    assert result['policy_sha256'] == retired['policy_sha256'] == sha(generated / 'policy.json')
    assert retired['result_sha256'] == sha(generated / 'result.json')
    for key, filename in [('input_sha256', 'input.fir'), ('output_sha256', 'output.fir'),
                          ('input_annotations_sha256', 'input-annotations.json'),
                          ('output_annotations_sha256', 'output-annotations.json')]:
        assert result[key] == sha(generated / filename), ('unbound group pass input/output', key)
    assert retired['input_sha256'] == sha(generated / 'output.fir')
    assert re.fullmatch('[0-9a-f]{64}', policy['input_sha256'])
    assert re.fullmatch('[0-9a-f]{64}', policy['input_annotations_sha256'])
    names = ['A', 'A2', 'B', 'B2', 'C', 'C2', 'GroupFixture', 'N']
    expected = dict(zip(names, ['A', 'A', 'B', 'B', 'C', 'C', 'GroupFixture', 'N']))
    assert result['module_renames'] == [dict(**{'from': n}, to=expected[n]) for n in names]
    # Check the native map independently, including identities and all modules.
    assert set(result['renames'].splitlines()) == {
        f'~GroupFixture|{a}=>~GroupFixture|{b}' for a, b in expected.items()}
    before = (generated / 'input.fir').read_text()
    after = (generated / 'output.fir').read_text()
    assert re.findall(r'^  module (\w+) :', before, re.M) == [*names[:6], 'N', 'GroupFixture']
    assert set(re.findall(r'^  module (\w+) :', after, re.M)) == {'A', 'B', 'C', 'N', 'GroupFixture'}
    for name in names[:6] + ['N']:
        assert f'inst inst{name} of {name}' in before
        assert f'inst inst{name} of {expected[name]}' in after
    assert len(re.findall(r'\breg stored : UInt<8>', before)) == 7
    assert len(re.findall(r'\breg stored : UInt<8>', after)) == 4
    for filename, gs in [('input-annotations.json', groups), ('output-annotations.json', outputs)]:
        annos = json.loads((generated / filename).read_text())
        assert [a for a in annos if a['class'] == 'firrtl.transforms.DedupGroupAnnotation'] == gs
        assert annos.count({'class': 'firrtl.transforms.NoCircuitDedupAnnotation$'}) == 1
        assert annos.count({'class': 'firrtl.transforms.NoDedupAnnotation', 'target': '~GroupFixture|N'}) == 1
        assert annos.count({'class': 'midas.passes.DedupGroupPolicyAnnotation',
                            'body': (generated / 'policy.json').read_text()}) == 1
    assert set(policy) == {'version', 'policy', 'circuit', 'input_sha256', 'input_annotations_sha256', 'groups'}
    assert set(result) == {'version', 'policy', 'circuit', 'policy_sha256', 'input_sha256', 'output_sha256',
                           'input_annotations_sha256', 'output_annotations_sha256', 'groups', 'output_groups',
                           'module_renames', 'renames'}
    assert set(retired) == {'version', 'policy', 'circuit', 'policy_sha256', 'result_sha256', 'input_sha256', 'groups'}
    return dict(input_modules=8, output_modules=5, concrete_register_instances=7, grouped_merges=2,
                ungrouped_merges=1, no_dedup_preserved=True)


def negatives(generated, out):
    rejected = []
    for name in ('cross-group', 'group-to-default', 'default-to-group', 'drop-module', 'alias-module',
                 'native-map', 'drop-group', 'change-group', 'drop-output-group', 'policy-binding',
                 'result-binding', 'input-hash', 'output-hash', 'annotation-hash', 'suppression',
                 'no-dedup', 'stale-input', 'stale-output', 'schema'):
        test = out / 'negative' / name
        shutil.copytree(generated, test)
        doc = json.loads((test / 'result.json').read_text())
        if name in ('cross-group', 'group-to-default', 'default-to-group'):
            row = {'cross-group': ('B2', 'A'), 'group-to-default': ('A2', 'C'),
                   'default-to-group': ('C2', 'A')}[name]
            for r in doc['module_renames']:
                if r['from'] == row[0]:
                    r['to'] = row[1]
        elif name == 'drop-module':
            doc['module_renames'].pop()
        elif name == 'alias-module':
            doc['module_renames'].append(copy.deepcopy(doc['module_renames'][0]))
        elif name == 'native-map':
            doc['renames'] = doc['renames'].replace('~GroupFixture|B2=>~GroupFixture|B', '~GroupFixture|B2=>~GroupFixture|A')
        elif name == 'drop-group':
            doc['groups'].pop()
        elif name == 'change-group':
            doc['groups'][0]['group'] = 'beta'
        elif name == 'drop-output-group':
            doc['output_groups'].pop()
        elif name == 'policy-binding':
            doc['policy_sha256'] = '0' * 64
        elif name == 'result-binding':
            p = test / 'retirement.json'
            r = json.loads(p.read_text()); r['result_sha256'] = '0' * 64
            p.write_text(json.dumps(r))
        elif name in ('input-hash', 'output-hash', 'annotation-hash'):
            doc[{'input-hash': 'input_sha256', 'output-hash': 'output_sha256',
                 'annotation-hash': 'output_annotations_sha256'}[name]] = '0' * 64
        elif name in ('suppression', 'no-dedup'):
            p = test / 'output-annotations.json'
            a = json.loads(p.read_text())
            a = [r for r in a if r['class'] != 'firrtl.transforms.' + (
                'NoCircuitDedupAnnotation$' if name == 'suppression' else 'NoDedupAnnotation')]
            p.write_text(json.dumps(a)); doc['output_annotations_sha256'] = sha(p)
        elif name.startswith('stale-'):
            p = test / ('input.fir' if name == 'stale-input' else 'output.fir')
            p.write_text(p.read_text() + '\n')
        elif name == 'schema':
            doc['hardware_capture'] = True
        (test / 'result.json').write_text(json.dumps(doc, sort_keys=True, separators=(',', ':')))
        # Retain coherent outer integrity for semantic corruptions.
        if name != 'result-binding':
            p = test / 'retirement.json'; r = json.loads(p.read_text())
            r['result_sha256'] = sha(test / 'result.json')
            p.write_text(json.dumps(r))
        try:
            audit(test)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError('accepted dedup corruption: ' + name)
    return rejected


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('audit', 'vcs', 'vivado'), default='audit')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='dedup-', dir=args.out)).resolve()
    generated = args.generated.resolve()
    sources = [Path('sims/firesim/sim/midas/src') / p for p in (
        'main/scala/midas/passes/CheckpointGroupDedupModules.scala',
        'main/scala/midas/passes/GoldenGateDedupGroups.scala',
        'main/scala/midas/passes/EnableAndRunDedupOnce.scala',
        'main/scala/midas/stage/GoldenGateCompilerPhase.scala',
        'main/scala/midas/checkpoint/SimulatorBankProbe.scala',
        'main/scala/midas/checkpoint/SimulatorBankProbeContext.scala',
        'test/scala/midas/passes/GoldenGateDedupGroupsSpec.scala')]
    sources.append(Path(__file__))
    source_hashes = {str(p.resolve()): sha(p) for p in sources}
    inputs = {str(p): sha(p) for p in generated.iterdir() if p.is_file()}
    positive = audit(generated)
    rejected = negatives(generated, out)
    commands = []

    def run(argv, label):
        row = dict(argv=[str(a) for a in argv], cwd=str(out))
        commands.append(row)
        with (out / (label + '.log')).open('w') as log:
            result = subprocess.run(row['argv'], cwd=out, stdout=log, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        assert result.returncode == 0, out / (label + '.log')

    checks = None
    if args.mode == 'vcs':
        # Rename every reference-module definition and instantiation, preserving
        # the exact emitted bodies from each independent compiler invocation.
        reference = (generated / 'reference.sv').read_text()
        for n in ['GroupFixture', 'A2', 'B2', 'C2', 'A', 'B', 'C', 'N']:
            reference = re.sub(r'\b' + n + r'\b', 'Ref_' + n, reference)
        (out / 'reference.sv').write_text(reference)
        (out / 'deduped.sv').write_bytes((generated / 'deduped.sv').read_bytes())
        leaves = ['A', 'A2', 'B', 'B2', 'C', 'C2', 'N']
        wires = '\n'.join(f'wire [7:0] ref_{n}, dut_{n};' for n in leaves)
        ports = lambda prefix: ','.join(f'.out{n}({prefix}_{n})' for n in leaves)
        compares = '\n'.join(f'''if (dut_{n} !== ref_{n} || dut_{n} !== model[{i}])
          $fatal(1, "DEDUP_DIVERGENCE cycle=%0d phase=%0d signal=out{n} ref=%h actual=%h expected=%h",
            cycle, phase, ref_{n}, dut_{n}, model[{i}]); checks = checks + 1;'''
                             for i, n in enumerate(leaves))
        tb = f'''module dedup_groups_tb;
reg clock=0, reset=1; reg [7:0] data=0; reg [7:0] model[0:6];
{wires}
Ref_GroupFixture reference(.clock(clock),.reset(reset),.data(data),{ports('ref')});
GroupFixture dut(.clock(clock),.reset(reset),.data(data),{ports('dut')});
integer checks=0;
initial begin
  $dumpfile("dedup.vcd"); $dumpvars(0,dedup_groups_tb);
  for(integer cycle=0;cycle<512;cycle=cycle+1) begin
    clock=0; reset=cycle<4 || cycle%53==0; data=cycle*17+cycle/7;
    for(integer phase=0;phase<2;phase=phase+1) begin
      if(phase==1) begin
        clock=1;
        for(integer i=0;i<7;i=i+1) model[i]=reset ? 7 : model[i]+data+i;
      end
      #5;
      if(cycle>=4) begin {compares} end
    end
  end
  $display("DEDUP_GROUPS_PASS checks=%0d cycles=512",checks); $finish;
end
endmodule
'''
        (out / 'tb.sv').write_text(tb)
        run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
             '-top', 'dedup_groups_tb', '-o', 'simv', 'reference.sv', 'deduped.sv', 'tb.sv'], 'compile')
        run([out / 'simv', '-no_save'], 'simulate')
        checks = (512 - 4) * 7 * 2
        assert f'DEDUP_GROUPS_PASS checks={checks} cycles=512' in (out / 'simulate.log').read_text()
        assert (out / 'dedup.vcd').stat().st_size > 1000
    if args.mode == 'vivado':
        (out / 'deduped.sv').write_bytes((generated / 'deduped.sv').read_bytes())
        (out / 'synth.tcl').write_text('''read_verilog -sv deduped.sv
synth_design -top GroupFixture -part xcvu47p-fsvh2892-2-e -mode out_of_context
if {[llength [get_cells -hier -filter {IS_SEQUENTIAL == 1}]] != 56} {error "dedup concrete storage missing"}
report_utilization -file utilization.rpt
write_checkpoint -force dedup.dcp
''')
        run(['vivado', '-mode', 'batch', '-source', 'synth.tcl', '-log', 'vivado.log',
             '-journal', 'vivado.jou'], 'synthesis')
        assert (out / 'dedup.dcp').stat().st_size > 0
    require_live_inputs_unchanged([dict(path=k, sha256=v) for k, v in {**inputs, **source_hashes}.items()])
    result = dict(status='pass', scope='group-dedup compiler/component only; no FPGA capture',
                  backend='eda' if args.mode == 'vcs' else 'f2', positive=positive, rejected=rejected,
                  vcs_checks=checks, commands=commands, inputs=inputs, sources=source_hashes,
                  artifacts={str(p): sha(p) for p in out.iterdir() if p.is_file()})
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(out / 'summary.json')


if __name__ == '__main__':
    main()
