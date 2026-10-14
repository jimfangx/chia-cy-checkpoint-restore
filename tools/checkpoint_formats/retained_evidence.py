"""Audit immutable native evidence across controller-owned checkpoint commits.

Index/HEAD immutability is an implementation-turn check. A durable audit instead
checks permitted checkpoint ancestry and archived build inputs. It must survive
the controller committing the turn, without allowing lost or rewritten evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from .codec import require
from .evidence import file_sha


def git(repo, *argv):
    return subprocess.check_output(['git', '--no-optional-locks', *argv], cwd=repo)


def check_native_input(root, path, digest, archived):
    """Hash an original native input; allow immutable snapshots for evolving source.

    Generated RTL, binaries, captured state, traces and logs in runs always use
    their original paths. Archived source fallback must match the hash that the
    native invocation itself recorded, not just a later catalog's claim.
    """
    path = Path(path)
    require(path.is_file(), 'missing original native input: ' + str(path))
    if file_sha(path) == digest:
        return
    binding = archived.get(str(path))
    root = Path(root).resolve()
    require(path.is_relative_to(root) and not path.is_relative_to(root / 'automations/checkpoint_loop/runs') and
            binding is not None and binding['sha256'] == digest and file_sha(binding['snapshot']) == digest,
            'changed/unarchived original native build input: ' + str(path))


def controller_ancestry(repo, saved):
    current = git(repo, 'rev-parse', 'HEAD').decode().strip()
    require(subprocess.run(['git', 'merge-base', '--is-ancestor', saved, current], cwd=repo,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0,
            'retained checkpoint is not an ancestor: ' + str(repo))
    commits = git(repo, 'rev-list', '--reverse', saved + '..' + current).decode().splitlines()
    previous = saved
    for commit in commits:
        parents = git(repo, 'show', '-s', '--format=%P', commit).decode().split()
        subject = git(repo, 'show', '-s', '--format=%s', commit).decode().strip()
        require(parents == [previous] and re.fullmatch(r'checkpoint\(M[0-9]+-[a-z0-9-]+\): iteration [0-9]+ (wip|ready)', subject),
                'unexpected change to controller checkpoint history: ' + commit)
        changed = git(repo, 'diff-tree', '--no-commit-id', '--name-only', '-r', commit).decode().splitlines()
        require(not {'plan_agent.md', 'plan_human.md'}.intersection(changed),
                'controller checkpoint includes protected plan input: ' + commit)
        previous = commit
    return [saved] + commits


def audit(root, archive_path, protected_path):
    root = Path(root).resolve()
    saved = json.loads(Path(protected_path).read_text())
    histories = {root: controller_ancestry(root, saved['heads'][0]),
                 root / 'sims/firesim': controller_ancestry(root / 'sims/firesim', saved['heads'][1])}
    for name, digest in saved.items():
        # These were separately guarded during implementation. The loop owns
        # their later mutation. Do not infer an agent mutation from a new commit.
        if name == 'heads' or name.endswith('/index'):
            continue
        require(file_sha(root / name) == digest, 'changed protected input ' + name)
    bindings = json.loads(Path(archive_path).read_text())['files']
    require(bindings, 'empty retained native archive')
    evolved = []
    originals = set()
    for binding in bindings:
        path, snapshot = Path(binding['path']), Path(binding['snapshot'])
        require(path.is_absolute() and snapshot.is_absolute() and path not in originals,
                'ambiguous retained native input')
        originals.add(path)
        require(snapshot.is_file() and snapshot.stat().st_size == binding['bytes'] and
                file_sha(snapshot) == binding['sha256'], 'changed archived native input ' + str(snapshot))
        require(path.is_file(), 'missing retained native input ' + str(path))
        if file_sha(path) == binding['sha256']:
            continue
        require(path.is_relative_to(root) and not path.is_relative_to(root / 'automations/checkpoint_loop/runs'),
                'changed original retained evidence ' + str(path))
        repo = root / 'sims/firesim' if path.is_relative_to(root / 'sims/firesim') else root
        relative = str(path.relative_to(repo))
        matched = []
        for commit in histories[repo]:
            result = subprocess.run(['git', 'show', commit + ':' + relative], cwd=repo,
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if result.returncode == 0 and hashlib.sha256(result.stdout).hexdigest() == binding['sha256']:
                matched.append(commit)
        require(matched, 'archived evolving source has no controller checkpoint provenance: ' + str(path))
        evolved.append(dict(path=str(path), snapshot=str(snapshot), committed_original=matched[-1]))
    return dict(status='passed', retained_native_input_bindings=len(bindings),
                all_original_archive_bytes_preserved=True, protected_file_bytes_preserved=True,
                controller_ancestry={str(k): v for k, v in histories.items()},
                evolved_sources=evolved, index_and_head_guard_scope='implementation turn only')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--protected', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root, args.archive, args.protected), indent=2))


if __name__ == '__main__':
    main()
