"""Keep retained build provenance separate from a new invocation's inputs."""
from pathlib import Path
import shutil

from .codec import require
from .evidence import file_sha
from .retained_evidence import check_native_input


def pin_reused_inputs(root, bindings, snapshots, *, compiled=()):
    """Audit inherited inputs, then archive the live bytes before execution.

    Retained executables use their original source snapshots. A new compilation
    must still consume the recorded native inputs, including headers/libraries.
    Live source evolution between invocations is allowed; evolution during an
    invocation is rejected by require_live_inputs_unchanged.
    """
    archived = {b['path']: b for b in bindings}
    require(len(archived) == len(bindings), 'ambiguous reused native input')
    compiled = {str(p) for p in compiled}
    require(compiled <= archived.keys(), 'unbound new compilation input')
    snapshots = Path(snapshots)
    snapshots.mkdir(parents=True, exist_ok=True)
    pinned = []
    for name, binding in archived.items():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed inherited source snapshot: '+name)
        check_native_input(root, name, binding['sha256'], archived)
        digest = file_sha(name)
        require(name not in compiled or digest == binding['sha256'],
                'changed new compilation input: '+name)
        snapshot = snapshots/digest
        if not snapshot.exists():
            shutil.copyfile(name, snapshot)
        require(file_sha(snapshot) == digest and file_sha(name) == digest,
                'source changed while pinning invocation input: '+name)
        pinned.append(dict(path=name, sha256=digest, snapshot=str(snapshot)))
    return pinned


def require_live_inputs_unchanged(bindings):
    for binding in bindings:
        require(file_sha(binding['path']) == binding['sha256'],
                'source changed during native invocation: '+binding['path'])


def audit_reused_input_guard(root, report, script, *, compiled=()):
    """Audit both generations; old reports predate invocation pinning."""
    inherited = {b['path']: b for b in report['source_inputs']}
    require(len(inherited) == len(report['source_inputs']), 'ambiguous inherited source input')
    required = 'pin_reused_inputs(' in Path(inherited[str(script)]['snapshot']).read_text()
    require(('invocation_source_inputs' in report) == required, 'missing/unexpected invocation source guard')
    if not required:
        return
    pinned = {b['path']: b for b in report['invocation_source_inputs']}
    require(len(pinned) == len(report['invocation_source_inputs']) and pinned.keys() == inherited.keys(),
            'incomplete invocation source guard')
    for name, binding in pinned.items():
        require(file_sha(binding['snapshot']) == binding['sha256'], 'changed invocation source snapshot: '+name)
        check_native_input(root, name, binding['sha256'], pinned)
    for name in map(str, compiled):
        require(pinned[name]['sha256'] == inherited[name]['sha256'], 'unbound new compilation source: '+name)
