"""Verify the production host compiler path's emitted fixture on EDA or Vivado.

This is compiler/component evidence, never an FPGA capture or CPU migration.
Both modes retain immutable source/generated inputs and actual native commands.
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
GENERATED = ('host-pipeline.sv', 'host-pipeline.fir', 'host-pipeline-manifest.json',
             'host-pipeline-emission.json', 'host-pipeline-external-owners.json', 'original-input.fir', 'discarded-host.sv')
SOURCES = ('sims/firesim/sim/midas/src/main/scala/midas/stage/GoldenGateCompilerPhase.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/PhysicalClockCutPlan.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/GeneratedExternalOwners.scala',
           'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/SimulatorStateInventory.scala',
           'sims/firesim/sim/midas/src/test/scala/midas/stage/GoldenGateHostPipelineSpec.scala',
           'tools/checkpoint_formats/tests/host_pipeline_tb.sv',
           'tools/checkpoint_formats/tests/audit_external_owners.py',
           'tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc',
           'tools/checkpoint_formats/tests/verify_host_pipeline.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('vcs', 'vivado'), required=True)
    args = parser.parse_args()
    base = args.out.resolve()
    require(base.is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'evidence outside runs')
    base.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='host-pipeline-', dir=base))
    for label, root, names in [('generated', args.generated.resolve(), GENERATED), ('sources', ROOT, SOURCES)]:
        for name in names:
            target = out/label/name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root/name).read_bytes())
    generated = out/'generated'
    binding = json.loads((generated/'host-pipeline-emission.json').read_text())
    manifest = json.loads((generated/'host-pipeline-manifest.json').read_text())
    require(binding['binding_version'] == 1 and binding['host_pipeline_version'] == 2 and
            binding['scope'] == manifest['scope'] == 'generated_rtl_only' and
            binding['external_runtime_required'] is True and manifest['external_runtime_required'] is True,
            'unsupported production emission scope/version')
    for field, name in [('emission_reference_sha256', 'host-pipeline.fir'),
                        ('simulator_manifest_sha256', 'host-pipeline-manifest.json'),
                        ('external_owners_sha256', 'host-pipeline-external-owners.json'),
                        ('emitted_verilog_sha256', 'host-pipeline.sv')]:
        require(binding[field] == sha(generated/name), 'unbound production emission: '+field)
    from tools.checkpoint_formats.tests.audit_external_owners import audit as audit_external
    audit_external(generated/'host-pipeline.fir', generated/'host-pipeline-manifest.json',
                   generated/'host-pipeline-external-owners.json')
    require(manifest['reference_sha256'] == sha(generated/'host-pipeline.fir'), 'unbound storage reference')
    require({(e['hierarchy'], e['width'], e['depth']) for e in manifest['state']} ==
            {('HostPipeline.host_owner', 8, 1), ('HostPipeline.consumer.always_', 8, 1)} and
            len(manifest['state']) == 2, 'incomplete emitted host-owner inventory')
    commands = []

    def run(argv, cwd, log_name, expected=0):
        row = dict(argv=[str(a) for a in argv], cwd=str(cwd), log=str(out/log_name))
        commands.append(row)
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        with (out/log_name).open('w') as stream:
            result = subprocess.run(row['argv'], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        require(result.returncode == expected, 'native failure; inspect '+str(out/log_name))
        return (out/log_name).read_text()

    if args.mode == 'vcs':
        require(Path(toolchain.VCS).is_file() and os.environ.get('VCS_HOME') == toolchain.VCS_HOME,
                'EDA with vcs-env.sh sourced last required')
        for label, source in [('healthy', 'host-pipeline.sv'), ('discarded', 'discarded-host.sv')]:
            work = out/label; work.mkdir()
            run([toolchain.VCS, '-full64', '-sverilog', '-timescale=1ns/1ps', '-Mupdate',
                 '-debug_access+all', '-top', 'host_pipeline_tb', '-Mdir='+str(work/'csrc'),
                 '-o', work/'simv', generated/source,
                 out/'sources/tools/checkpoint_formats/tests/host_pipeline_tb.sv',
                 out/'sources/tools/checkpoint_formats/tests/checkpoint_generated_network_exit.cc'],
                work, label+'-compile.log')
            text = run([work/'simv', '-no_save'], work, label+'-run.log', 0 if label == 'healthy' else 1)
            if label == 'healthy':
                require('HOST_PIPELINE_PASS checks=4100 edges=1025' in text, 'incomplete functional comparison')
            else:
                require('HOST_PIPELINE_FIRST_MISMATCH cycle=1 ' in text and 'HOST_PIPELINE_PASS' not in text,
                        'old discarded-host compiler behavior was not detected')
    else:
        require(ROOT == Path('/home/ubuntu/chia-cy-checkpoint-restore') and shutil.which('vivado'),
                'native manager Vivado required')
        script = out/'synth.tcl'
        script.write_text('''set_param general.maxThreads 4
create_project -in_memory -part xcvu47p-fsvh2892-2-e
read_verilog -sv generated/host-pipeline.sv
synth_design -top HostPipeline -part xcvu47p-fsvh2892-2-e -mode out_of_context
create_clock -period 7.142857 [get_ports clock]
opt_design
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force HostPipeline.dcp
puts "HOST_PIPELINE_SYNTH_PASS"
close_project
''')
        text = run(['vivado', '-mode', 'batch', '-source', script, '-log', 'vivado.log',
                    '-journal', 'vivado.jou'], out, 'vivado-command.log')
        require('HOST_PIPELINE_SYNTH_PASS' in text and (out/'HostPipeline.dcp').stat().st_size,
                'missing synthesized component')
    summary = dict(status='pass', backend='eda' if args.mode == 'vcs' else 'f2',
                   observed_utc=datetime.now(timezone.utc).isoformat(), host=socket.gethostname(),
                   original_root=str(ROOT), scope='production host compiler path fixture only',
                   physical_fpga_capture=False, full_rocket_image_build=False, commands=commands,
                   generated={n: sha(generated/n) for n in GENERATED}, sources={n: sha(ROOT/n) for n in SOURCES},
                   artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                              if p.is_file() and p.suffix in ('.log', '.rpt', '.dcp', '.vcd', '.tcl')})
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(out/'summary.json')


if __name__ == '__main__':
    main()
