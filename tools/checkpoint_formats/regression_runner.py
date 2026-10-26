"""Run pinned component regressions in fresh, independently auditable attempts.

Each invocation keeps its own logs and receipt index. Re-running a controller
command never selects a previous receipt or overwrites historical evidence.
This is regression infrastructure, not FPGA checkpoint acceptance.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .codec import require
from .evidence import file_sha


ROOT = Path(__file__).resolve().parents[2]
WORKSPACES = (Path('/home/ubuntu/chia-cy-checkpoint-restore'),
              Path('/scratch/jfx/chia-cy-checkpoint-restore'))
RUNS = Path('automations/checkpoint_loop/runs')


def local(root, name):
    path = Path(name)
    for original in WORKSPACES:
        if path.is_relative_to(original):
            return root / path.relative_to(original)
    return path if path.is_absolute() else root / path


def below(path, directory):
    require(path.resolve().is_relative_to(directory.resolve()),
            'evidence escapes its output scope: ' + str(path))
    return path


def option(argv, name):
    require(argv.count(name) == 1 and argv.index(name) + 1 < len(argv),
            'one explicit ' + name + ' required')
    return argv.index(name) + 1


def plan_commands(plan):
    require(plan.get('format_version') == 1 and plan.get('backend') == 'eda',
            'version-1 EDA regression plan required')
    commands = plan.get('commands')
    require(isinstance(commands, list) and commands, 'empty regression scope')
    scopes = set()
    for command in commands:
        scope = command.get('scope', '')
        require(re.fullmatch('[a-z][a-z0-9-]*', scope) and scope not in scopes,
                'invalid or duplicate regression scope')
        scopes.add(scope)
        argv = command.get('argv')
        require(command.get('backend') == 'eda' and command.get('cwd') == '.' and
                isinstance(argv, list) and argv and all(isinstance(a, str) and a for a in argv),
                'explicit EDA argv and workspace cwd required')
        option(argv, '--out')
        require(argv[option(argv, '--mode')] == 'vcs', 'VCS regression mode required')
        option(argv, '--native')
    return commands


def native_receipt(root, command):
    pin = command['native_receipt']
    path = below(local(root, pin['path']), root / RUNS)
    require(path.name == 'summary.json' and file_sha(path) == pin['sha256'],
            'native receipt pin changed: ' + str(path))
    argv = command['argv']
    require(local(root, argv[option(argv, '--native')]).resolve() == path.parent.resolve(),
            'command native input differs from pinned receipt')
    doc = json.loads(path.read_text())
    require(doc['status'] == 'pass' and doc['backend'] == 'f2' and doc['sources'],
            'passing native source provenance required')
    for name, digest in doc['sources'].items():
        source = below(local(root, name), root)
        require(file_sha(source) == digest, 'native source stale: ' + str(source))
    check_files(path, doc)
    return path, doc


def check_files(receipt, doc):
    for group in ('inputs', 'artifacts'):
        require(isinstance(doc.get(group), dict) and doc[group],
                'missing regression ' + group)
        for name, digest in doc[group].items():
            path = below(receipt.parent / name, receipt.parent)
            require(path.is_file() and path.stat().st_size and file_sha(path) == digest,
                    'changed regression evidence: ' + str(path))


def check_child(receipt, native):
    doc = json.loads(receipt.read_text())
    require(doc['status'] == 'pass' and doc['backend'] == 'eda' and
            doc['sources'] == native['sources'] and doc['inputs'] == native['inputs'],
            'wrong, incomplete or stale regression receipt: ' + str(receipt))
    check_files(receipt, doc)
    return doc


def publish(path, result):
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(result, indent=2) + '\n')
    pending.replace(path)


def execute(plan_path, output, root=ROOT):
    root = root.resolve()
    plan_path = local(root, plan_path)
    plan_digest = file_sha(plan_path)
    plan = json.loads(plan_path.read_text())
    commands = plan_commands(plan)
    output = below(local(root, output), root / RUNS)
    output.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix='attempt-', dir=output))
    result_path = attempt / 'result.json'
    result = dict(status='running', backend='eda', historical_execution=False,
                  physical_fpga_capture=False, scope='pinned component regressions only',
                  observed_utc=datetime.now(timezone.utc).isoformat(), source_root=str(root),
                  plan=str(plan_path), plan_sha256=plan_digest,
                  runner_sha256=file_sha(Path(__file__)), commands=[], receipts={})
    publish(result_path, result)
    try:
        # Validate every scope before running any of them. Missing native inputs
        # cannot silently shrink the requested regression scope.
        for command in commands:
            native_receipt(root, command)
        for command in commands:
            native_path, native = native_receipt(root, command)
            scope = command['scope']
            directory = attempt / scope
            directory.mkdir()  # Exclusive creation; no historical child exists.
            argv = list(command['argv'])
            argv[option(argv, '--out')] = str(directory)
            log = attempt / (scope + '.log')
            row = dict(scope=scope, backend='eda', cwd=str(root), argv=argv,
                       log=str(log), native_receipt=str(native_path),
                       native_receipt_sha256=command['native_receipt']['sha256'])
            result['commands'].append(row)
            publish(result_path, result)
            with log.open('x') as stream:
                row['returncode'] = subprocess.run(argv, cwd=root, stdout=stream,
                                                    stderr=subprocess.STDOUT).returncode
            row['log_sha256'] = file_sha(log)
            require(row['returncode'] == 0, 'regression failed; inspect underlying log ' + str(log))
            candidates = list(directory.glob('*/summary.json'))
            require(len(candidates) == 1, 'fresh output scope contains ambiguous or missing receipts')
            receipt = below(candidates[0], directory)
            lines = log.read_text().splitlines()
            require(lines and local(root, lines[-1]).resolve() == receipt.resolve(),
                    'regression did not explicitly return its fresh receipt')
            child = check_child(receipt, native)
            native_receipt(root, command)
            result['receipts'][scope] = dict(path=str(receipt), sha256=file_sha(receipt),
                                            native_receipt=str(native_path),
                                            native_receipt_sha256=command['native_receipt']['sha256'],
                                            observed_utc=child.get('observed_utc'),
                                            historical_execution=False)
            publish(result_path, result)
            print(scope + ' PASS ' + str(receipt), flush=True)
        require(file_sha(plan_path) == plan_digest, 'regression plan changed during execution')
        require(file_sha(Path(__file__)) == result['runner_sha256'], 'regression runner changed during execution')
        for command in commands:
            native_receipt(root, command)
        result['status'] = 'pass'
        result['completed_utc'] = datetime.now(timezone.utc).isoformat()
        publish(result_path, result)
    except Exception as error:
        result.update(status='fail', error=str(error), completed_utc=datetime.now(timezone.utc).isoformat())
        publish(result_path, result)
        raise
    return result_path


def audit(result_path, root=ROOT):
    """Recheck an explicit attempt; never discover or choose the latest run."""
    root = root.resolve()
    result_path = below(local(root, result_path), root / RUNS)
    result = json.loads(result_path.read_text())
    require(result['status'] == 'pass' and result['backend'] == 'eda' and
            result['historical_execution'] is False and result['physical_fpga_capture'] is False,
            'complete passing component attempt required')
    require(result['runner_sha256'] == file_sha(Path(__file__)), 'regression runner changed')
    plan_path = local(root, result['plan'])
    require(file_sha(plan_path) == result['plan_sha256'], 'regression plan pin changed')
    commands = plan_commands(json.loads(plan_path.read_text()))
    scopes = [c['scope'] for c in commands]
    require([c['scope'] for c in result['commands']] == scopes and set(result['receipts']) == set(scopes),
            'missing, duplicate or reordered regression scopes')
    for command, row in zip(commands, result['commands']):
        native_path, native = native_receipt(root, command)
        scope = command['scope']
        directory = result_path.parent / scope
        expected_argv = list(command['argv'])
        expected_argv[option(expected_argv, '--out')] = str(Path(result['source_root']) /
                                                           directory.relative_to(root))
        require(row['argv'] == expected_argv and row['returncode'] == 0 and
                row['backend'] == 'eda' and local(root, row['cwd']) == root,
                'changed regression command')
        log = local(root, row['log'])
        require(log == result_path.parent / (scope + '.log') and file_sha(log) == row['log_sha256'],
                'changed regression log')
        pin = result['receipts'][scope]
        receipt = local(root, pin['path'])
        require(list(directory.glob('*/summary.json')) == [receipt] and
                local(root, log.read_text().splitlines()[-1]) == receipt and
                file_sha(receipt) == pin['sha256'], 'changed or substituted regression receipt')
        require(local(root, pin['native_receipt']) == native_path and
                pin['native_receipt_sha256'] == command['native_receipt']['sha256'] and
                local(root, row['native_receipt']) == native_path and
                row['native_receipt_sha256'] == pin['native_receipt_sha256'] and
                pin['historical_execution'] is False, 'changed native receipt binding')
        check_child(receipt, native)
    return dict(status='pass', backend='eda', physical_fpga_capture=False,
                result=str(result_path), result_sha256=file_sha(result_path), scopes=scopes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.audit:
        require(not args.plan and not args.out, 'audit takes one explicit result')
        print(json.dumps(audit(args.audit), indent=2))
    else:
        from . import toolchain
        require(shutil.which('vcs') == toolchain.VCS == '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs',
                'EDA native SP2 environment required')
        require(args.plan and args.out, 'plan and output required')
        print(execute(args.plan, args.out))


if __name__ == '__main__':
    main()
