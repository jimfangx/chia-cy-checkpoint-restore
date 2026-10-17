"""Run real four-hart syscall-93 computation in ordinary/restricted VCS HTIF.

Four complete 16-GiB controls, with identical CPU instructions and target labels.
This closes the workload/host-protocol mismatch, not complete CPU Level 1.
Reuse only an audited, source-bound exact-recipe native VCS build.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shlex
import shutil
import sys
import tempfile

from tools.checkpoint_formats.codec import require
from tools.checkpoint_formats.cpu_native import VCS_HOME, vcs_invocation
from tools.checkpoint_formats.cpu_recipe import ROOT, RECIPES, recipe_settings
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.tests.verify_rocket_controls_vcs import ENVIRONMENT, execute

MODES = ('ordinary', 'ordinary-buffered', 'restricted', 'restricted-buffered')


def build_inputs(identity_path):
    identity = json.loads(identity_path.read_text())
    require(identity['recipe'] == recipe_settings(RECIPES['Rocket']) and
            identity['vcs_home'] == VCS_HOME and identity['checkpoint_profile'] is None and
            identity['htif_lifecycle_provider_linked'] and
            not identity['level1_verified'] and not identity['level2_verified'],
            'need exact-recipe lifecycle-enabled VCS build')
    for path, digest in identity['sources_sha256'].items():
        require(file_sha(path) == digest, 'changed native build input '+path)
    binary = Path(identity['native_binary'])
    command, _ = vcs_invocation((identity_path.parent/'rocket-vcs-build.log').read_text(), binary)
    require(command == identity['vcs_build_command'], 'unbound native VCS build')
    return binary


def control(mode, binary, workload, out):
    runtime = out/mode
    runtime.mkdir()
    (runtime/'input.bin').write_bytes(b'')
    image = json.loads((workload/'summary.json').read_text())
    elf = Path(image['builds']['rocket-quad']['elf'])
    argv = [str(binary), '+permissive', '-no_save', '+vcs+initreg+0', '+vcs+initmem+0',
            '+memsize=17179869184', '+max-cycles=5000000', '+fesvr-step-size=128',
            '+blkdev-in-mem0=128', '+mm_useHardwareDefaultRuntimeSettings_0',
            '+tracefile='+str(runtime/'TRACEFILE'),
            '+checkpoint-terminal-input='+str(runtime/'input.bin')]
    if mode.startswith('restricted'):
        argv += ['+checkpoint-syscall-exit']
    if mode.endswith('buffered'):
        argv += ['+tracerv-checkpoint-buffered', '+heartbeat-checkpoint-buffered',
                 '+heartbeat-output='+str(runtime/'heartbeat.csv'), '+uart-checkpoint-file0',
                 '+uart-in0='+str(runtime/'input.bin'), '+uart-out0='+str(runtime/'output.bin')]
    argv += ['+permissive-off', str(elf)]
    # Absolute PYTHONPATH survives the runtime cwd; each VCS shell sources the
    # pinned environment last. The mask is established before exec/any threads.
    launch = [sys.executable, '-m', 'tools.checkpoint_formats.tests.exec_with_blocked_htif_signals', '--', *argv]
    command = dict(cwd='.', argv=['bash', '-lc', ENVIRONMENT+'cd '+shlex.quote(str(runtime))+
                                 ' && PYTHONPATH='+shlex.quote(str(ROOT))+' '+shlex.join(launch)])
    (runtime/'command.json').write_text(json.dumps(command, indent=2)+'\n')
    ran = execute(command, out, mode+'-workload')
    (runtime/'exit.json').write_text(json.dumps(dict(returncode=0, checkpoint_acceptance=False))+'\n')
    (runtime/'native-vcs.log').symlink_to(Path(ran['log']))
    audited = execute(dict(cwd='.', argv=[sys.executable, '-m', 'tools.checkpoint_formats.tests.audit_rocket_baseline',
                      '--runtime', str(runtime), '--workload', str(workload), '--out', str(runtime/'audit.json')]),
                      out, mode+'-audit')
    return [ran, audited]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-identity', type=Path, required=True)
    parser.add_argument('--workload', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--completed-controls', type=Path,
                        help='Re-audit four completed native executions without rerunning target edges')
    args = parser.parse_args()
    destination = args.out.resolve()
    require(destination.is_relative_to(ROOT/'automations/checkpoint_loop/runs'), 'need diagnostic output')
    identity_path, workload = args.build_identity.resolve(), args.workload.resolve()
    binary = build_inputs(identity_path)
    identity = json.loads(identity_path.read_text())
    image = json.loads((workload/'summary.json').read_text())
    require(image['status'] == 'passed' and image['harts'] == 4 and image['exit_protocol'] == 'syscall93' and
            set(image['builds']) == {'rocket-quad', *(f'corrupt-hart-{h}' for h in range(4))},
            'need full self-checking syscall workload')
    for build in image['builds'].values():
        require(file_sha(build['elf']) == build['sha256'], 'changed workload image')
    destination.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=destination))
    (destination/'latest.json').write_text(json.dumps(dict(artifact_root=str(out)))+'\n')
    paths = [Path(__file__), Path(__file__).with_name('exec_with_blocked_htif_signals.py'),
             Path(__file__).with_name('verify_rocket_workload.py'), Path(__file__).with_name('audit_rocket_baseline.py'),
             Path(__file__).with_name('verify_rocket_controls_vcs.py'),
             ROOT/'tools/checkpoint_formats/codec.py', ROOT/'tools/checkpoint_formats/evidence.py',
             ROOT/'tools/checkpoint_formats/retained_evidence.py',
             Path(__file__).with_name('audit_rocket_syscall.py'), identity_path,
             workload/'summary.json', workload/'commands.json', Path(image['compiled_source']),
             *[Path(b['elf']) for b in image['builds'].values()], *workload.glob('*.log'),
             *map(Path, image['source_hashes']), *map(Path, identity['sources_sha256'])]
    (out/'sources').mkdir()
    bindings = []
    for path in dict.fromkeys(paths):
        digest = file_sha(path); snapshot = out/'sources'/digest
        if not snapshot.exists(): shutil.copyfile(path, snapshot)
        bindings.append(dict(path=str(path), sha256=digest, snapshot=str(snapshot)))
    report = dict(status='in_progress', scope='four-hart syscall-93 CPU workload controls',
                  recipe=identity_path.as_posix(), workload=str(workload), artifact_root=str(out),
                  source_inputs=bindings, commands=[], level1_verified=False, level2_verified=False)
    if args.completed_controls:
        previous = args.completed_controls.resolve()
        prior = json.loads(previous.read_text())
        require(prior['status'] in ('failed', 'passed') and prior['recipe'] == str(identity_path) and
                prior['workload'] == str(workload), 'incompatible/incomplete native executions')
        report.update(native_artifact_root=str(previous.parent), completed_native_summary=str(previous),
                      completed_native_summary_sha256=file_sha(previous), native_source_inputs=prior['source_inputs'],
                      native_artifact_sha256={str(p): file_sha(p) for p in previous.parent.rglob('*') if p.is_file()})
    summary = out/'summary.json'
    summary.write_text(json.dumps(report, indent=2)+'\n')
    try:
        if args.completed_controls:
            for mode in MODES:
                native_root = args.completed_controls.resolve().parent
                ran = json.loads((native_root/(mode+'-workload-result.json')).read_text())
                require(ran['returncode'] == 0 and ran['purpose'] == mode+'-workload', 'native execution did not pass')
                audited = execute(dict(cwd='.', argv=[sys.executable, '-m', 'tools.checkpoint_formats.tests.audit_rocket_baseline',
                                  '--runtime', str(native_root/mode), '--workload', str(workload),
                                  '--out', str(out/(mode+'-audit.json'))]), out, mode+'-audit')
                report['commands'] += [ran, audited]
        else:
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [pool.submit(control, mode, binary, workload, out) for mode in MODES]
                for future in futures:
                    report['commands'] += future.result()
                    summary.write_text(json.dumps(report, indent=2)+'\n')
        build_inputs(identity_path)
        for binding in bindings:
            require(file_sha(binding['path']) == binding['sha256'], 'input drift')
        report['status'] = 'passed'
        report['artifact_sha256'] = {str(p): file_sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p != summary}
        summary.write_text(json.dumps(report, indent=2)+'\n')
        from tools.checkpoint_formats.tests.audit_rocket_syscall import audit
        print(json.dumps(audit(summary), indent=2))
    except Exception as error:
        report.update(status='failed', error=str(error))
        summary.write_text(json.dumps(report, indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
