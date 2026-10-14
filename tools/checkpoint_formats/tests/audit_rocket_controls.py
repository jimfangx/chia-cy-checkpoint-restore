"""Independently re-audit one immutable complete Rocket control invocation."""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

from tools.checkpoint_formats.retained_evidence import check_native_input

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.cpu_native import VCS_HOME, vcs_invocation
from tools.checkpoint_formats.cpu_recipe import ROOT, RECIPES, recipe_settings
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.simulator import check_generated_rtl


def audit(summary_path, source_archive=None):
    summary_path = Path(summary_path).resolve()
    summary = json.loads(summary_path.read_text())
    out = summary_path.parent
    require(summary['status'] == 'passed' and summary['artifact_root'] == str(out) and
            summary['level1_verified'] is False and summary['level2_verified'] is False,
            'incomplete or falsely authorized CPU control result')
    require(summary['recipe'] == recipe_settings(RECIPES['Rocket']), 'changed exact Rocket recipe')
    archived = {} if source_archive is None else {b['path']: b for b in json.loads(Path(source_archive).read_text())['files']}
    for path, digest in summary['input_hashes'].items():
        check_native_input(ROOT, path, digest, archived)
    identity = json.loads((out / 'rocket-build-identity.json').read_text())
    require(identity['recipe'] == summary['recipe'] and identity['checkpoint_profile'] is None and
            identity['level1_verified'] is False and identity['level2_verified'] is False and
            identity['vcs_home'] == VCS_HOME and len(identity['translation_units']) == 58,
            'incomplete or incompatible executed native CPU build')
    for path, digest in identity['sources_sha256'].items():
        check_native_input(ROOT, path, digest, archived)
    binary = Path(identity['native_binary'])
    require(binary.parent.parent.parent == out / 'build' and binary.name == 'FireSim',
            'CPU executable is outside its immutable invocation')
    log = (out / 'rocket-vcs-build.log').read_text()
    require(vcs_invocation(log, binary)[0] == identity['vcs_build_command'],
            'native build log no longer binds its executable')
    require('VCS_FORCE_REBUILD=1' in json.loads(log.splitlines()[0])['argv'][-1],
            'CPU control did not explicitly request a native rebuild')
    commands = summary['commands']
    require(len(commands) == 5 and all(c['returncode'] == 0 for c in commands),
            'incomplete executed native build/control/audit command scope')
    pids = set()
    for command in commands:
        text = Path(command['log']).read_text()
        require(text.rstrip().endswith('exit=0') and command['pid'] not in pids,
                'missing success or reused control/audit process')
        require('fresh_process_pid=' + str(command['pid']) in text,
                'missing actual executed process identity')
        pids.add(command['pid'])
        raw = json.loads(text.splitlines()[0])
        require(raw == {key: command[key] for key in ('cwd', 'argv')}, 'changed actual native argv')
    base = binary.parent / 'FireSim-generated'
    manifest = json.loads(base.with_suffix('.simulator-state.json').read_text())
    bufgce = (ROOT / 'sims/firesim/sim/midas/src/main/verilog/BUFGCE.v').read_text()
    check_generated_rtl(manifest, base.with_suffix('.simulator-reference.fir').read_text(),
                        base.with_suffix('.sv').read_text() + bufgce, bufgce,
                        plusarg_model=(binary.parent / 'plusarg_reader.v').read_text())
    require((len(manifest['instances']), len(manifest['state']),
             sum(entry['depth'] for entry in manifest['state'])) == (2292, 11464, 445838),
            'changed complete exact Rocket generated inventory')
    invocation = json.loads((out / 'invocation.json').read_text())
    workload = Path(invocation['args']['workload']).resolve()
    reference_audit = Path(invocation['args']['reference_audit']).resolve()
    reference = json.loads(reference_audit.read_text())
    workload_report = json.loads((workload / 'summary.json').read_text())
    for path, digest in workload_report['source_hashes'].items():
        require(file_sha(path) == digest, 'changed self-checking workload source ' + path)
    require({c['mode'] for c in summary['controls']} == {'rocket', 'rocket-buffered'} and
            len(summary['controls']) == 2, 'both complete control modes required')
    for control in summary['controls']:
        name = control['mode']
        runtime = out / (name + '-runtime')
        executed = next(c for c in commands if c['purpose'] == name + '-workload')
        require(json.loads((runtime / 'command.json').read_text()) ==
                {key: executed[key] for key in ('cwd', 'argv')},
                'runtime metadata differs from its actually executed native command')
        shell = executed['argv'][-1]
        require(executed['argv'][:2] == ['bash', '-lc'] and
                'source env.sh && source sims/firesim/env.sh && source automations/checkpoint_loop/vcs-env.sh &&' in shell,
                'native CPU shell did not pin its VCS environment last')
        native_argv = shlex.split(shell.rsplit(' && ', 1)[1])
        require(native_argv[0] == str(binary) and all(arg in native_argv for arg in
                ('-no_save', '+vcs+initreg+0', '+vcs+initmem+0', '+memsize=17179869184',
                 '+max-cycles=5000000', '+fesvr-step-size=128', '+blkdev-in-mem0=128',
                 '+mm_useHardwareDefaultRuntimeSettings_0')),
                'native control memory, initialization or driver settings differ')
        if name == 'rocket-buffered':
            require(all(arg in native_argv for arg in
                    ('+heartbeat-checkpoint-buffered', '+uart-checkpoint-file0',
                     '+uart-in0=' + str(runtime / 'input.bin'),
                     '+uart-out0=' + str(runtime / 'output.bin'),
                     '+heartbeat-output=' + str(runtime / 'heartbeat.csv'))) and
                    (runtime / 'input.bin').read_bytes() == b'' and
                    (runtime / 'output.bin').read_bytes() == b'', 'incomplete buffered CPU control endpoints')
        if control.get('tracerv_checkpoint_buffered', False):
            require(name == 'rocket-buffered' and '+tracerv-checkpoint-buffered' in native_argv,
                    'missing buffered TracerV native CPU control')
        require(control['status'] == 'passed' and control['level1_verified'] is False and
                control['level2_verified'] is False and control['native_binary'] == str(binary) and
                control['native_binary_sha256'] == file_sha(binary) and
                control['full_backing_memory_bytes'] == 17179869184 and
                control['workload_sha256'] == workload_report['builds']['rocket-quad']['sha256'],
                'incomplete CPU control native build/workload/memory binding')
        require(len(control['comparisons']) == 4, 'missing complete four-hart trace scope')
        for hart, comparison in enumerate(control['comparisons']):
            require(Path(comparison['current']) == runtime / f'TRACEFILE-C{hart}' and
                    file_sha(comparison['current']) == file_sha(comparison['reference']) == comparison['sha256'] and
                    Path(comparison['current']).stat().st_size == comparison['bytes'] > 0,
                    'changed complete hart trace ' + str(hart))
        matches = re.findall(r'\*\*\* PASSED \*\*\* after (\d+) cycles',
                             (runtime / 'native-vcs.log').read_text())
        require(matches == [str(control['end_target_count'])], 'changed actual CPU completion label')
        path = out / (name + '-independent-audit.json')
        subprocess.run([sys.executable, '-m', 'tools.checkpoint_formats.tests.audit_rocket_baseline',
                        '--runtime', str(runtime), '--workload', str(workload), '--out', str(path)],
                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        actual = json.loads(path.read_text())
        for key in ('hart_phases', 'completed_harts', 'failure_stores', 'tohost_stores', 'workload_retirements'):
            require(actual[key] == reference[key], 'independent CPU instruction/store labels differ ' + key)
    return dict(status='passed', summary=str(summary_path), full_four_hart_controls=2,
                generated_state_entries=11464, generated_state_words=445838,
                level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--source-archive', type=Path, help='Original immutable build-input catalog for a retained controller checkpoint.')
    args = parser.parse_args()
    print(json.dumps(audit(args.summary, args.source_archive), indent=2))


if __name__ == '__main__':
    main()
