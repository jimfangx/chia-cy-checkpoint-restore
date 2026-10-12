"""Bind explicitly selected independent audit reports without counting retries."""

import argparse
import hashlib
import json
from pathlib import Path

from .codec import canonical, keys, require


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _file(path):
    path = Path(path)
    require(path.is_absolute() and path.is_file() and path.stat().st_size > 0,
            'evidence must be a nonempty absolute file: ' + str(path))
    return path.resolve()


def _reports(selection, proof_run):
    keys(selection, {'format_version', 'proof_run', 'reports'})
    require(type(selection['format_version']) is int and selection['format_version'] == 1,
            'unsupported audit pair version')
    proof_run = Path(proof_run).resolve()
    require(selection['proof_run'] == str(proof_run), 'audit pair belongs to another proof run')
    require(type(selection['reports']) is list and len(selection['reports']) == 2,
            'two explicitly selected independent audit reports required')
    paths, reports = [], []
    for entry in selection['reports']:
        keys(entry, {'path', 'sha256'})
        path = _file(entry['path'])
        require(file_sha(path) == entry['sha256'], 'selected audit report changed: ' + str(path))
        report = json.loads(path.read_text())
        required = {'run', 'proof_run', 'status', 'original_proofs_unchanged',
                    'formal_state_map_complete', 'gate_restore_authorized', 'original_proof_hashes'}
        require(type(report) is dict and required <= set(report), 'incomplete selected audit report')
        require(type(report['run']) is str and type(report['proof_run']) is str and
                type(report['original_proof_hashes']) is dict,
                'invalid selected audit report provenance')
        require(path == Path(report['run']).resolve() / 'summary.json' and
                report['proof_run'] == str(proof_run), 'audit report provenance differs')
        require(report['status'] == 'passed' and report['original_proofs_unchanged'] is True and
                report['formal_state_map_complete'] is False and report['gate_restore_authorized'] is False,
                'incomplete or falsely authorized local audit report')
        paths.append(path)
        reports.append(report)
    require(paths[0].parent != paths[1].parent and not paths[0].samefile(paths[1]),
            'audit reports must come from distinct independent invocations')
    actual = {str(p.resolve()): file_sha(p) for p in proof_run.rglob('*')
              if p.is_file() and not p.is_symlink()}
    require(actual and all(r['original_proof_hashes'] == actual for r in reports),
            'selected audits do not bind the complete unchanged proof artifacts')
    return list(zip(paths, reports))


def select_audit_pair(summaries, proof_run, destination):
    """Validate both reports before publishing the immutable pair selection."""
    selection = dict(format_version=1, proof_run=str(Path(proof_run).resolve()),
                     reports=[dict(path=str(_file(p)), sha256=file_sha(_file(p))) for p in summaries])
    _reports(selection, proof_run)
    Path(destination).write_bytes(canonical(selection))
    return selection


def audit_pair(selection_path, proof_run):
    return _reports(json.loads(_file(Path(selection_path).resolve()).read_text()), proof_run)


def selected_audit_pair(selection_path):
    """Recover the proof from the bound pair, independent of latest-run pointers.

    The pair still has to bind two independent reports and every proof byte.
    Callers must reconstruct and audit that selected proof before using it.
    """
    selection = json.loads(_file(Path(selection_path).resolve()).read_text())
    keys(selection, {'format_version', 'proof_run', 'reports'})
    require(type(selection['proof_run']) is str and Path(selection['proof_run']).is_absolute(),
            'selected proof run must be an absolute directory')
    proof_run = Path(selection['proof_run']).resolve()
    require(proof_run.is_dir(), 'selected proof run missing: ' + str(proof_run))
    return proof_run, _reports(selection, proof_run)


def artifact_catalog(paths):
    """Catalog concrete files, resolving links to their actual artifact bytes."""
    files = sorted({_file(p) for p in paths})
    return [dict(path=str(p), bytes=p.stat().st_size, sha256=file_sha(p)) for p in files]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, action='append', required=True)
    parser.add_argument('--proof-run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(select_audit_pair([p.resolve() for p in args.summary], args.proof_run,
                                      args.out), indent=2))


if __name__ == '__main__':
    main()
