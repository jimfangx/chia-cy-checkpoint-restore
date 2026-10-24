"""Production-compiler bank probe: native localhost synthesis or EDA VCS.

The public-input oracle checks both functional outputs and every bank word.
This fixture is not a Rocket image, a physical capture, or CPU migration.
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
NAMES = ('bank-probe-reference.fir', 'bank-probe-state.json', 'bank-probe-instrumented.fir',
         'bank-probe-binding.json', 'bank-probe-descriptors.json', 'bank-probe-emission.json')
SOURCES = ('sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SimulatorBankProbe.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedStateBankAccess.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/stage/GoldenGateCompilerPhase.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/stage/GoldenGateHostPipelineSpec.scala',
           'tools/checkpoint_formats/tests/production_bank_tb.sv',
           'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
           'tools/checkpoint_formats/tests/verify_production_bank.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_inputs(generated):
    emission = json.loads((generated/'bank-probe-emission.json').read_text())
    require(emission['binding_version'] == 1 and emission['scope'] == 'generated_rtl_probe_only'
            and emission['external_runtime_required'] is True
            and emission['deployable_capture_image'] is False, 'unsupported bank emission scope')
    require(emission['emitted_verilog_sha256'] == sha(generated/'bank-probe.sv'), 'unbound emitted probe')
    require(set(emission['inputs']) == {'.'+n for n in NAMES[:-1]}, 'incomplete probe input binding')
    for name in NAMES[:-1]:
        require(emission['inputs']['.'+name] == sha(generated/name), 'unbound probe input '+name)
    manifest = json.loads((generated/'bank-probe-state.json').read_text())
    binding = json.loads((generated/'bank-probe-binding.json').read_text())
    descriptors = json.loads((generated/'bank-probe-descriptors.json').read_text())
    require(manifest['reference_sha256'] == binding['reference_sha256'] ==
            sha(generated/'bank-probe-reference.fir'), 'unbound pre-bank circuit')
    require(binding['manifest_sha256'] == descriptors['manifest_sha256'] ==
            sha(generated/'bank-probe-state.json'), 'unbound complete pre-bank state')
    require(binding['instrumented_sha256'] == sha(generated/'bank-probe-instrumented.fir')
            and descriptors['bank_binding_sha256'] == sha(generated/'bank-probe-binding.json'),
            'unbound instrumented circuit/descriptors')
    require(binding['access_clock'] == 'ckpt_clock', 'wrong access clock')
    require(len(manifest['state']) == len(binding['state']) == len(descriptors['state']) == 2,
            'incomplete production fixture ownership')
    expected_paths = {'HostPipeline.host_owner', 'HostPipeline.consumer.always'}
    require({e['hierarchy'] for e in manifest['state']} == expected_paths, 'incorrect fixture ownership')
    selectors = {}
    for logical, actual, descriptor in zip(manifest['state'], binding['state'], descriptors['state']):
        require(logical['state_id'] == actual['state_id'] == descriptor['state_id'] and
                logical['hierarchy'] == actual['hierarchy'] and
                logical['width'] == actual['width'] == descriptor['width'] == 8 and
                logical['depth'] == actual['depth'] == descriptor['depth'] == 1 and
                actual['bank'] == descriptor['bank'] == 0 and actual['slot'] == descriptor['slot'],
                'altered complete word descriptor')
        selectors['HOST_SLOT' if logical['hierarchy'].endswith('host_owner') else 'COUNT_SLOT'] = actual['slot']
    require(len(set(selectors.values())) == 2, 'duplicate word selectors')
    return selectors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('vcs', 'vivado'), required=True)
    args = parser.parse_args()
    base = args.out.resolve()
    require(base.is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='production-bank-', dir=base))
    for label, root, names in [('generated', args.generated.resolve(), (*NAMES, 'bank-probe.sv')),
                               ('sources', ROOT, SOURCES)]:
        for name in names:
            target = out/label/name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root/name).read_bytes())
    generated = out/'generated'
    selectors = audit_inputs(generated)
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
        work = out/'healthy'; work.mkdir()
        run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate', '-debug_access+all',
             '-top', 'production_bank_tb', '-Mdir='+str(work/'csrc'), '-o', work/'simv',
             *['+define+'+k+'='+str(v) for k, v in selectors.items()], generated/'bank-probe.sv',
             out/'sources/tools/checkpoint_formats/tests/production_bank_tb.sv',
             out/'sources/tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc'],
            work, 'compile.log')
        text = run([work/'simv', '-no_save'], work, 'healthy.log')
        require(re.search(r'PRODUCTION_BANK_PASS checks=\d+ edges=1025 host_ticks=1105 reads=21 cuts=4', text),
                'incomplete production bank continuation')
        cuts = re.findall(r'PRODUCTION_BANK_CUT target_cycle=(\d+) count=(\d+) injected=(\d+) complete_words=2', text)
        require([int(c[0]) for c in cuts] == [2, 39, 132, 900], 'wrong complete cut labels')
        negative = out/'corrupt'; negative.mkdir()
        text = run([work/'simv', '-no_save', '+corrupt'], negative, 'corrupt.log', expected=1)
        require('PRODUCTION_BANK_MISMATCH target_cycle=2 reads=0 freeze=1 reason=complete bank word' in text
                and 'PRODUCTION_BANK_PASS' not in text, 'semantic corruption did not stop at first unacked word')
    else:
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),
                'native manager Vivado required')
        script = out/'synth.tcl'
        script.write_text('''set_param general.maxThreads 4
create_project -in_memory -part xcvu47p-fsvh2892-2-e
read_verilog -sv generated/bank-probe.sv
synth_design -top HostPipeline -part xcvu47p-fsvh2892-2-e -mode out_of_context
create_clock -name functional -period 7.142857 [get_ports clock]
create_clock -name access -period 7.142857 [get_ports ckpt_clock]
opt_design
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force HostPipeline.dcp
puts "PRODUCTION_BANK_SYNTH_PASS"
close_project
''')
        text = run(['vivado', '-mode', 'batch', '-source', script, '-log', 'vivado.log',
                    '-journal', 'vivado.jou'], out, 'vivado-command.log')
        require('PRODUCTION_BANK_SYNTH_PASS' in text and (out/'HostPipeline.dcp').stat().st_size,
                'missing synthesized probe')
    summary = dict(status='pass', backend='eda' if args.mode == 'vcs' else 'f2',
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   original_root=str(ROOT), scope='production compiler bank probe fixture only',
                   physical_fpga_capture=False, full_rocket_image_build=False, commands=commands,
                   generated={n: sha(generated/n) for n in (*NAMES, 'bank-probe.sv')},
                   sources={n: sha(ROOT/n) for n in SOURCES},
                   artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                              if p.is_file() and p.suffix in ('.log', '.rpt', '.dcp', '.vcd', '.tcl')})
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
