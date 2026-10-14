"""Verify a sealed iteration's complete diagnostics across controller commits.

The manifest hash is an explicit caller-selected trust anchor. Diagnostic bytes
never fall back to source archives. Only source files may evolve, and their
original bytes must exist in the permitted controller checkpoint history.
Index/HEAD equality is checked during implementation, not after its controller
has committed. Protected file bytes and plan exclusion remain durable checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from .codec import require
from .evidence import file_sha
from .retained_evidence import audit as audit_native, git


def catalog_files(manifest_path, expected_sha256, dangling_links=None, dangling_links_sha256=None):
    """Read every cataloged byte and require exact file membership, including links."""
    manifest_path = Path(manifest_path).absolute()
    require(re.fullmatch(r'[0-9a-f]{64}', expected_sha256) is not None and
            file_sha(manifest_path) == expected_sha256, 'selected manifest changed')
    manifest = json.loads(manifest_path.read_text())
    run = manifest_path.parent
    require(manifest['status'] == 'cataloged' and manifest['artifact_root'] == str(run) and
            manifest['manifest_self'] == str(manifest_path), 'wrong catalog provenance')
    require(type(manifest['files']) is list and manifest['files'], 'empty artifact catalog')
    listed = set()
    total = 0
    for entry in manifest['files']:
        path = Path(entry['path'])
        require(path.is_absolute() and path.is_relative_to(run) and '..' not in path.parts and
                path != manifest_path and path not in listed, 'ambiguous catalog path: ' + str(path))
        listed.add(path)
        require(type(entry['bytes']) is int and entry['bytes'] >= 0 and path.is_file() and
                path.stat().st_size == entry['bytes'] and file_sha(path) == entry['sha256'],
                'changed/missing diagnostic: ' + str(path))
        total += entry['bytes']
    require((dangling_links is None) == (dangling_links_sha256 is None),
            'supplemental links require an explicit hash')
    links = manifest.get('dangling_links', [])
    if dangling_links is not None:
        # Old seals used is_file(), which omitted stale VCS cache symlinks.
        # Bind their exact paths/targets separately; never rewrite an old seal
        # or silently ignore unlisted links in the directory walk.
        require(not links and file_sha(dangling_links) == dangling_links_sha256,
                'supplemental link catalog changed/ambiguous')
        supplement = json.loads(Path(dangling_links).read_text())
        require(supplement['format_version'] == 1 and
                supplement['manifest_sha256'] == expected_sha256, 'wrong supplemental link provenance')
        links = supplement['links']
    require(type(links) is list, 'invalid dangling-link catalog')
    link_paths = set()
    for entry in links:
        path = Path(entry['path'])
        require(path.is_absolute() and path.is_relative_to(run) and '..' not in path.parts and
                path != manifest_path and path not in listed and path not in link_paths,
                'ambiguous dangling-link path: ' + str(path))
        require(path.is_symlink() and not path.exists() and str(path.readlink()) == entry['target'],
                'changed dangling link: ' + str(path))
        link_paths.add(path)
    # Include dangling links so removing a linked artifact cannot shrink scope.
    actual = {p for p in run.rglob('*') if (p.is_file() or p.is_symlink()) and p != manifest_path}
    expected = listed | link_paths
    require(actual == expected, 'diagnostic membership changed: missing=' +
            repr(sorted(str(p) for p in expected-actual)[:5]) + ' extra=' +
            repr(sorted(str(p) for p in actual-expected)[:5]))
    return manifest, dict(cataloged_files=len(listed), cataloged_bytes=total,
                          cataloged_dangling_links=len(link_paths),
                          supplemental_links_sha256=dangling_links_sha256)


def source_artifacts(root, entries, histories):
    """Verify final implementation bytes, allowing only committed later evolution."""
    require(type(entries) is list and entries, 'empty changed-source catalog')
    seen, evolved = set(), []
    for entry in entries:
        path = Path(entry['path'])
        require(path.is_absolute() and path.is_relative_to(root) and '..' not in path.parts and
                not path.is_relative_to(root/'automations/checkpoint_loop/runs') and
                path not in seen and path.is_file(), 'invalid changed-source path: ' + str(path))
        seen.add(path)
        if path.stat().st_size == entry['bytes'] and file_sha(path) == entry['sha256']:
            continue
        repo = root/'sims/firesim' if path.is_relative_to(root/'sims/firesim') else root
        relative = str(path.relative_to(repo))
        matched = []
        for commit in histories[str(repo)]:
            result = subprocess.run(['git', '--no-optional-locks', 'show', commit+':'+relative],
                                    cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if (result.returncode == 0 and len(result.stdout) == entry['bytes'] and
                    hashlib.sha256(result.stdout).hexdigest() == entry['sha256']):
                matched.append(commit)
        require(matched, 'changed source has no controller checkpoint provenance: ' + str(path))
        evolved.append(dict(path=str(path), committed_original=matched[-1]))
    return dict(changed_source_files=len(seen), evolved_sources=evolved)


def audit(root, manifest_path, expected_sha256, dangling_links=None, dangling_links_sha256=None):
    root = Path(root).resolve()
    manifest_path = Path(manifest_path).absolute()
    require(manifest_path.is_relative_to(root/'automations/checkpoint_loop/runs'),
            'diagnostics must be under checkpoint runs')
    manifest, report = catalog_files(manifest_path, expected_sha256,
                                     dangling_links, dangling_links_sha256)
    run = manifest_path.parent
    # These reports were read byte-for-byte above; never rewrite an old seal.
    native = audit_native(root, run/'native-input-archives.json', run/'protected-native-inputs.json')
    for repo in (root, root/'sims/firesim'):
        staged = git(repo, 'diff', '--cached', '--name-only', '--',
                     'plan_agent.md', 'plan_human.md').decode().splitlines()
        require(not staged, 'protected plan staged: ' + str(repo))
    changes_path = run/'changed-source-artifacts.json'
    require(manifest['changed_source_artifacts'] == str(changes_path), 'wrong changed-source binding')
    sources = source_artifacts(root, json.loads(changes_path.read_text()), native['controller_ancestry'])
    summary = json.loads((run/'summary.json').read_text())
    require(summary['status'] == 'in_progress' and summary['increment_status'] == 'passed' and
            summary['level1_verified'] is False and summary['level2_verified'] is False and
            summary['external_missing_dependencies'] == [], 'unexpected CPU acceptance claim')
    audits = json.loads((run/'independent-audit-results.json').read_text())
    require(audits and len(audits) == summary['independent_audits'] and
            all(type(c['returncode']) is int and c['returncode'] == 0 for c in audits),
            'incomplete independent audits')
    selected = json.loads((run/'selected-results.json').read_text())
    require(selected and selected == summary['selected_results'], 'selected results differ')
    for name, item in selected.items():
        require(file_sha(item['path']) == item['sha256'] and
                json.loads(Path(item['path']).read_text())['status'] == 'passed',
                'selected native result changed/failed: ' + name)
    return dict(status='passed', manifest=str(manifest_path), manifest_sha256=expected_sha256,
                **report, **sources, retained_inputs=native,
                independent_audits=len(audits), selected_native_results=len(selected),
                milestone_status='in_progress', level1_verified=False, level2_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--dangling-links', type=Path)
    parser.add_argument('--dangling-links-sha256')
    args = parser.parse_args()
    print(json.dumps(audit(args.root, args.manifest, args.manifest_sha256,
                           args.dangling_links, args.dangling_links_sha256), indent=2))


if __name__ == '__main__':
    main()
