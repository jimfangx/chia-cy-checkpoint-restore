"""Run all preserved native checks without rewriting any retained invocation.

Every call allocates new build, simulation, log and result paths under runs.
Optional retained-evidence guards execute before and after the complete suite.
These are prerequisite regressions; they do not establish CPU acceptance.
"""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

from .codec import require
from .cpu_recipe import ROOT
from .evidence import file_sha
from .retained_evidence import audit, check_native_input


def commands(out, rocket_header, production):
    """Construct the full eight-check suite with invocation-local destinations."""
    environment = ('source env.sh && source sims/firesim/env.sh && '
                   'export COURSIER_CACHE=' + shlex.quote(str(out / 'coursier-cache')) + ' && '
                   'export JAVA_TOOL_OPTIONS="-Xmx8G -Xss8M" && '
                   'source automations/checkpoint_loop/vcs-env.sh && ')
    result = [dict(purpose='All checkpoint-format Python tests', cwd='.',
                   argv=['python', '-m', 'unittest', 'discover', '-s', 'tools/checkpoint_formats/tests', '-v'])]
    for name, module, options in [
        ('semantic', 'verify_semantic_vcs', ['--build', out / 'm2-build']),
        ('banked', 'verify_banked_vcs', ['--build', out / 'm3-build']),
        ('widget', 'verify_widget_checkpoint_vcs', []),
        ('fcfs-make', 'verify_checkpoint_make', ['--production', production]),
        ('uart', 'verify_uart_checkpoint_vcs', ['--rocket-header', rocket_header]),
        ('blockdev', 'verify_blockdev_checkpoint_vcs', ['--rocket-header', rocket_header]),
        ('heartbeat', 'verify_heartbeat_checkpoint_vcs', ['--rocket-header', rocket_header]),
    ]:
        argv = ['python', '-m', 'tools.checkpoint_formats.tests.' + module,
                *options, '--out', out / (name + '-regression')]
        result.append(dict(purpose='Preserved complete ' + name + ' native regression', cwd='.',
                           argv=['bash', '-lc', environment + 'VCS_FLAGS=-Mupdate ' +
                                 shlex.join([str(a) for a in argv])]))
    return result


def run_suite(root, destination, make_commands, guards=(), sources=()):
    """Allocate once; never reopen another invocation's logs or simulator paths.

    Persist failure records too. Do not publish a passing result unless every
    command and both retained-evidence guards actually finished successfully.
    """
    root, destination = Path(root).resolve(), Path(destination).resolve()
    require(destination.is_relative_to(root / 'automations/checkpoint_loop/runs'),
            'native regression diagnostics must be under runs')
    destination.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='invocation-', dir=destination))
    checks = make_commands(out)
    require(checks, 'empty native regression suite')
    (out / 'commands.json').write_text(json.dumps(checks, indent=2) + '\n')
    summary = dict(status='in_progress', scope='preserved regressions; CPU checkpoint acceptance pending',
                   invocation=str(out), checks=[], retained_guards={},
                   CPU_level1_verified=False, CPU_level2_verified=False, source_inputs=[])
    report = out / 'summary.json'

    def persist():
        report.write_text(json.dumps(summary, indent=2) + '\n')

    def guard(phase):
        summary['retained_guards'][phase] = [
            dict(archive=str(Path(archive).resolve()), protected=str(Path(protected).resolve()),
                 result=audit(root, archive, protected)) for archive, protected in guards]
        persist()

    persist()
    try:
        snapshots = out / 'source-snapshots'
        snapshots.mkdir()
        for source in sorted({Path(p).resolve() for p in sources}):
            require(source.is_file(), 'missing native regression source ' + str(source))
            digest = file_sha(source)
            snapshot = snapshots / digest
            if not snapshot.exists():
                shutil.copyfile(source, snapshot)
            require(file_sha(source) == file_sha(snapshot) == digest, 'source changed while archiving ' + str(source))
            summary['source_inputs'].append(dict(path=str(source), sha256=digest, snapshot=str(snapshot)))
        persist()
        guard('before')
        for index, command in enumerate(checks):
            log = out / ('check-' + str(index) + '.log')
            with log.open('x') as stream:
                stream.write(json.dumps(command) + '\n')
                stream.flush()
                process = subprocess.Popen(command['argv'], cwd=root / command['cwd'],
                                           stdout=stream, stderr=subprocess.STDOUT)
                stream.write('fresh_process_pid=' + str(process.pid) + '\n')
                stream.flush()
                code = process.wait()
                stream.write('\nexit=' + str(code) + '\n')
            summary['checks'].append(dict(command, returncode=code, log=str(log), log_sha256=file_sha(log)))
            persist()
            require(code == 0, 'native regression failed; see ' + str(log))
        guard('after')
        for binding in summary['source_inputs']:
            require(file_sha(binding['path']) == binding['sha256'],
                    'native regression source changed during execution ' + binding['path'])
        # Include generated RTL, simulator binaries, captured images/traces,
        # readback, native logs and results. This seals the whole invocation;
        # rebuilding/verifying must allocate another directory.
        summary['artifact_sha256'] = {str(p): file_sha(p) for p in sorted(out.rglob('*'))
                                      if p.is_file() and p != report}
        summary['status'] = 'passed'
        persist()
    except Exception as error:
        summary.update(status='failed', error=str(error))
        persist()
        raise
    return report


def audit_suite(summary_path):
    path = Path(summary_path).resolve()
    summary = json.loads(path.read_text())
    require(summary['status'] == 'passed' and summary['invocation'] == str(path.parent),
            'native regression invocation did not finish')
    require(len(summary['checks']) == 8 and all(c['returncode'] == 0 for c in summary['checks']),
            'incomplete preserved native regression suite')
    require(summary['CPU_level1_verified'] is False and summary['CPU_level2_verified'] is False,
            'prerequisite regressions cannot establish CPU acceptance')
    require(json.loads((path.parent / 'commands.json').read_text()) ==
            [{k: c[k] for k in ('purpose', 'cwd', 'argv')} for c in summary['checks']],
            'native command records changed')
    artifacts = summary['artifact_sha256']
    require(artifacts and set(artifacts) == {str(p) for p in path.parent.rglob('*') if p.is_file() and p != path},
            'missing/extra retained native regression artifacts')
    for name, digest in artifacts.items():
        require(file_sha(name) == digest, 'changed native regression artifact ' + name)
    for check in summary['checks']:
        text = Path(check['log']).read_text()
        require(check['log_sha256'] == artifacts[check['log']] and text.rstrip().endswith('exit=0') and
                text.splitlines()[0] == json.dumps({k: check[k] for k in ('purpose', 'cwd', 'argv')}),
                'unbound native regression command/result')
    require(set(summary['retained_guards']) == {'before', 'after'} and
            summary['retained_guards']['before'] == summary['retained_guards']['after'],
            'retained evidence changed during native regressions')
    for guard in summary['retained_guards']['after']:
        audit(ROOT, guard['archive'], guard['protected'])
    inputs = summary.get('source_inputs', [])
    require(len({b['path'] for b in inputs}) == len(inputs), 'duplicate native regression source')
    bindings = {b['path']: b for b in inputs}
    for binding in inputs:
        require(artifacts.get(binding['snapshot']) == binding['sha256'], 'unbound original regression source snapshot')
        check_native_input(ROOT, binding['path'], binding['sha256'], bindings)
    return dict(status='passed', summary=str(path), checks=8, retained_artifacts=len(artifacts),
                original_source_bindings=len(inputs), CPU_level1_verified=False, CPU_level2_verified=False)


def source_inputs(root):
    """Preserve the maintained checkers and local native/compiler implementation."""
    result = set()
    for directory in ('tools/checkpoint_formats', 'sims/firesim/sim/midas/src/main',
                      'sims/firesim/sim/src/main', 'sims/firesim/sim/make'):
        result.update(p for p in (root / directory).rglob('*') if p.is_file() and
                      (p.suffix in ('.py', '.cc', '.cpp', '.c', '.h', '.v', '.vh', '.sv', '.scala', '.mk') or
                       p.name == 'Makefile' or p.name.startswith('Makefrag')))
    result.update(root / p for p in ('env.sh', 'sims/firesim/env.sh', 'automations/checkpoint_loop/vcs-env.sh',
                                    'sims/firesim/sim/Makefile'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--rocket-header', type=Path)
    parser.add_argument('--production', type=Path)
    parser.add_argument('--guard', nargs=2, action='append', default=[], metavar=('ARCHIVE', 'PROTECTED'))
    parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.audit is not None:
        require(args.out is None and not args.guard and args.rocket_header is None and args.production is None,
                'audit and execution options are independent')
        print(json.dumps(audit_suite(args.audit), indent=2))
        return
    require(args.out is not None and args.rocket_header is not None and args.production is not None,
            'execution requires out, rocket-header and production')
    header, production = args.rocket_header.resolve(), args.production.resolve()
    require(header.is_file() and (production / 'native-build-inputs.json').is_file(),
            'missing real Rocket header or preserved compiled FCFS inventory')
    report = run_suite(ROOT, args.out, lambda out: commands(out, header, production), args.guard,
                       source_inputs(ROOT) | {header, production / 'native-build-inputs.json'})
    print(json.dumps(audit_suite(report), indent=2))


if __name__ == '__main__':
    main()
