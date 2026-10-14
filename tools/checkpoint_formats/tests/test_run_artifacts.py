import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.run_artifacts import audit, catalog_files


class RunArtifactsTests(unittest.TestCase):
    """Real disposable Git histories model the controller's post-turn commit."""
    def git(self, repo, *argv):
        return subprocess.check_output(['git', '--no-optional-locks', *argv], cwd=repo,
                                       stderr=subprocess.DEVNULL).decode().strip()

    def commit(self, repo, *paths, subject='checkpoint(M11-rocket-level1-level2): iteration 103 wip'):
        self.git(repo, 'add', '--', *paths)
        self.git(repo, '-c', 'user.name=Evidence test', '-c', 'user.email=test@example.invalid',
                 'commit', '-qm', subject)
        return self.git(repo, 'rev-parse', 'HEAD')

    def write(self, name, value):
        (self.run/name).write_text(json.dumps(value))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.firesim = self.root/'sims/firesim'; self.firesim.mkdir(parents=True)
        for repo in (self.root, self.firesim):
            self.git(repo, 'init', '-q')
        self.plan = self.root/'plan_agent.md'; self.plan.write_text('user priorities')
        (self.root/'plan_human.md').write_text('read only input')
        self.source = self.root/'driver.cc'; self.source.write_text('original implementation')
        (self.firesim/'driver.cc').write_text('original simulator')
        first_root = self.commit(self.root, 'driver.cc', 'plan_agent.md', 'plan_human.md')
        first_firesim = self.commit(self.firesim, 'driver.cc')
        self.run = self.root/'automations/checkpoint_loop/runs/test'; self.run.mkdir(parents=True)
        self.original = self.run/'native.log'; self.original.write_text('complete native result')
        snapshot = self.run/'snapshot'; snapshot.write_bytes(self.original.read_bytes())
        (self.run/'empty').touch()
        (self.run/'native-link.log').symlink_to('native.log')
        self.write('native-input-archives.json', dict(files=[dict(path=str(self.original),
            snapshot=str(snapshot), bytes=snapshot.stat().st_size, sha256=file_sha(snapshot))]))
        self.write('protected-native-inputs.json', {'plan_agent.md': file_sha(self.plan),
            '.git/index': file_sha(self.root/'.git/index'),
            'heads': [first_root, first_firesim]})
        self.write('changed-source-artifacts.json', [dict(path=str(self.source),
            bytes=self.source.stat().st_size, sha256=file_sha(self.source))])
        self.write('result.json', dict(status='passed'))
        selected = {'native': dict(path=str(self.run/'result.json'), sha256=file_sha(self.run/'result.json'))}
        self.write('selected-results.json', selected)
        self.write('independent-audit-results.json', [dict(returncode=0)])
        self.write('summary.json', dict(status='in_progress', increment_status='passed',
            level1_verified=False, level2_verified=False, external_missing_dependencies=[],
            independent_audits=1, selected_results=selected))
        self.manifest = self.run/'artifact-manifest.json'
        self.seal()

    def seal(self):
        self.write('artifact-manifest.json', dict(status='cataloged', artifact_root=str(self.run),
            manifest_self=str(self.manifest), changed_source_artifacts=str(self.run/'changed-source-artifacts.json'),
            files=[dict(path=str(p), bytes=p.stat().st_size, sha256=file_sha(p))
                   for p in sorted(self.run.rglob('*')) if p.is_file() and p != self.manifest]))
        self.digest = file_sha(self.manifest)

    def audit(self):
        return audit(self.root, self.manifest, self.digest)

    def test_controller_commits_survive_but_original_source_bytes_remain_bound(self):
        self.source.write_text('subsequent implementation')
        head = self.commit(self.root, 'driver.cc')
        (self.firesim/'driver.cc').write_text('subsequent simulator')
        self.commit(self.firesim, 'driver.cc')
        result = self.audit()
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['evolved_sources'][0]['committed_original'],
                         self.git(self.root, 'rev-parse', head+'^'))
        self.assertFalse(result['level1_verified'])
        self.assertFalse(result['level2_verified'])

    def test_all_cataloged_bytes_missing_files_and_extra_files_are_checked(self):
        saved = self.original.read_bytes()
        self.original.write_bytes(b'X'*len(saved))
        with self.assertRaisesRegex(FormatError, 'diagnostic'):
            self.audit()
        self.original.write_bytes(saved)
        self.original.unlink()
        with self.assertRaisesRegex(FormatError, 'diagnostic'):
            self.audit()
        self.original.write_bytes(saved)
        extra = self.run/'extra.log'; extra.write_bytes(b'')
        with self.assertRaisesRegex(FormatError, 'membership'):
            self.audit()

    def test_manifest_must_match_explicit_hash(self):
        self.manifest.write_bytes(self.manifest.read_bytes()+b'\n')
        with self.assertRaisesRegex(FormatError, 'manifest changed'):
            self.audit()

    def test_dangling_and_changed_link_reject(self):
        link = self.run/'native-link.log'; link.unlink(); link.symlink_to('missing')
        with self.assertRaisesRegex(FormatError, 'diagnostic'):
            self.audit()

    def test_duplicate_escape_and_manifest_self_entries_reject_even_resealed(self):
        original = json.loads(self.manifest.read_text())
        for name in (str(self.original), str(self.run/'..'/'outside'), str(self.manifest)):
            doc = dict(original, files=original['files']+[dict(path=name, bytes=0, sha256='0'*64)])
            self.manifest.write_text(json.dumps(doc)); self.digest = file_sha(self.manifest)
            with self.subTest(path=name), self.assertRaisesRegex(FormatError, 'catalog path'):
                self.audit()

    def test_protected_bytes_reject_after_controller_commit(self):
        self.source.write_text('new code'); self.commit(self.root, 'driver.cc')
        self.plan.write_text('unauthorized priorities')
        with self.assertRaisesRegex(FormatError, 'protected input'):
            self.audit()

    def test_staged_plan_rejects_even_if_worktree_matches(self):
        original = self.plan.read_bytes()
        self.plan.write_text('staged modification'); self.git(self.root, 'add', 'plan_agent.md')
        self.plan.write_bytes(original)
        with self.assertRaisesRegex(FormatError, 'plan staged'):
            self.audit()

    def test_controller_commit_cannot_include_plan(self):
        self.plan.write_text('committed modification'); self.commit(self.root, 'plan_agent.md')
        with self.assertRaisesRegex(FormatError, 'protected plan'):
            self.audit()

    def test_non_controller_commit_rejects(self):
        self.source.write_text('arbitrary change')
        self.commit(self.root, 'driver.cc', subject='arbitrary commit')
        with self.assertRaisesRegex(FormatError, 'controller checkpoint history'):
            self.audit()

    def test_rewritten_history_rejects(self):
        self.git(self.root, 'checkout', '--orphan', 'rewritten')
        self.git(self.root, 'rm', '--cached', 'driver.cc', 'plan_agent.md', 'plan_human.md')
        self.source.write_text('replacement root'); self.commit(self.root, 'driver.cc')
        with self.assertRaisesRegex(FormatError, 'not an ancestor'):
            self.audit()

    def test_no_uncommitted_source_fallback(self):
        self.source.write_text('new code')
        doc = json.loads((self.run/'changed-source-artifacts.json').read_text())
        doc[0]['sha256'] = '0'*64
        self.write('changed-source-artifacts.json', doc); self.seal()
        with self.assertRaisesRegex(FormatError, 'checkpoint provenance'):
            self.audit()

    def test_failed_or_missing_independent_audit_rejects(self):
        for audits in ([], [dict(returncode=1)]):
            self.write('independent-audit-results.json', audits); self.seal()
            with self.subTest(audits=audits), self.assertRaisesRegex(FormatError, 'independent audits'):
                self.audit()

    def test_resealed_false_cpu_acceptance_rejects(self):
        doc = json.loads((self.run/'summary.json').read_text()); doc['level1_verified'] = True
        self.write('summary.json', doc); self.seal()
        with self.assertRaisesRegex(FormatError, 'CPU acceptance'):
            self.audit()

    def test_selected_native_result_rebinding_rejects(self):
        self.write('selected-results.json', {}); self.seal()
        with self.assertRaisesRegex(FormatError, 'selected results'):
            self.audit()

    def test_empty_files_and_native_links_are_included(self):
        _, result = catalog_files(self.manifest, self.digest)
        self.assertEqual(result['cataloged_files'], 11)
        self.assertEqual(self.audit()['cataloged_files'], 11)

    def test_legacy_dangling_links_need_separately_bound_exact_targets(self):
        link = self.run/'stale.so'; link.symlink_to('missing-cache.so')
        with self.assertRaisesRegex(FormatError, 'membership'):
            self.audit()
        supplement = self.root/'links.json'
        supplement.write_text(json.dumps(dict(format_version=1, manifest_sha256=self.digest,
            links=[dict(path=str(link), target='missing-cache.so')])) )
        digest = file_sha(supplement)
        self.assertEqual(audit(self.root, self.manifest, self.digest, supplement, digest)
                         ['cataloged_dangling_links'], 1)
        link.unlink(); link.symlink_to('different-cache.so')
        with self.assertRaisesRegex(FormatError, 'changed dangling link'):
            audit(self.root, self.manifest, self.digest, supplement, digest)
        link.unlink(); link.symlink_to('missing-cache.so')
        supplement.write_bytes(supplement.read_bytes()+b'\n')
        with self.assertRaisesRegex(FormatError, 'supplemental link catalog changed'):
            audit(self.root, self.manifest, self.digest, supplement, digest)

    def test_new_seal_binds_dangling_links_without_supplement(self):
        link = self.run/'stale.so'; link.symlink_to('absent')
        doc = json.loads(self.manifest.read_text())
        doc['dangling_links'] = [dict(path=str(link), target='absent')]
        self.manifest.write_text(json.dumps(doc)); self.digest = file_sha(self.manifest)
        self.assertEqual(self.audit()['cataloged_dangling_links'], 1)
        link.unlink()
        with self.assertRaisesRegex(FormatError, 'changed dangling link'):
            self.audit()

    def test_supplement_cannot_belong_to_different_seal_or_skip_new_links(self):
        link = self.run/'stale.so'; link.symlink_to('absent')
        supplement = self.root/'links.json'
        doc = dict(format_version=1, manifest_sha256='0'*64,
                   links=[dict(path=str(link), target='absent')])
        supplement.write_text(json.dumps(doc))
        with self.assertRaisesRegex(FormatError, 'supplemental link provenance'):
            audit(self.root, self.manifest, self.digest, supplement, file_sha(supplement))
        doc['manifest_sha256'] = self.digest; supplement.write_text(json.dumps(doc))
        (self.run/'unlisted.so').symlink_to('also-absent')
        with self.assertRaisesRegex(FormatError, 'membership'):
            audit(self.root, self.manifest, self.digest, supplement, file_sha(supplement))


if __name__ == '__main__':
    unittest.main()
