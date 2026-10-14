import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.retained_evidence import audit, check_native_input


class RetainedNativeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'sims/firesim').mkdir(parents=True)
        self.plan = self.root / 'plan_agent.md'; self.plan.write_text('protected user instructions')
        runs = self.root / 'automations/checkpoint_loop/runs/test'; runs.mkdir(parents=True)
        self.original = runs / 'native.log'; self.original.write_text('real native result')
        self.snapshot = runs / 'snapshot'; self.snapshot.write_bytes(self.original.read_bytes())
        self.archive = runs / 'archive.json'; self.protected = runs / 'protected.json'
        self.archive.write_text(json.dumps(dict(files=[dict(path=str(self.original), snapshot=str(self.snapshot),
                                                           sha256=file_sha(self.snapshot), bytes=self.snapshot.stat().st_size)])))
        self.protected.write_text(json.dumps({'plan_agent.md': file_sha(self.plan), '.git/index': 'old-index',
                                             'heads': ['old-root-head', 'old-firesim-head']}))
        self.mock = patch('tools.checkpoint_formats.retained_evidence.controller_ancestry', return_value=['old', 'controller'])
        self.mock.start(); self.addCleanup(self.mock.stop)

    def test_controller_index_changes_do_not_erase_original_input_guards(self):
        self.assertTrue(audit(self.root, self.archive, self.protected)['all_original_archive_bytes_preserved'])
        self.plan.write_text('unauthorized user instruction edit')
        with self.assertRaisesRegex(FormatError, 'protected input'):
            audit(self.root, self.archive, self.protected)

    def test_changed_archived_original_and_missing_native_evidence_reject(self):
        for path in (self.original, self.snapshot):
            saved = path.read_bytes(); path.write_bytes(saved + b' changed')
            with self.subTest(path=path), self.assertRaises(FormatError):
                audit(self.root, self.archive, self.protected)
            path.write_bytes(saved)
        self.original.unlink()
        with self.assertRaisesRegex(FormatError, 'missing retained'):
            audit(self.root, self.archive, self.protected)

    def test_duplicate_original_bindings_reject(self):
        doc = json.loads(self.archive.read_text()); doc['files'] *= 2
        self.archive.write_text(json.dumps(doc))
        with self.assertRaisesRegex(FormatError, 'ambiguous'):
            audit(self.root, self.archive, self.protected)

    def test_source_snapshot_fallback_cannot_hide_changed_runtime_evidence(self):
        source = self.root / 'driver.cc'; source.write_text('original native source')
        snapshot = self.root / 'original.cc'; snapshot.write_bytes(source.read_bytes())
        digest = file_sha(source)
        archived = {str(source): dict(snapshot=str(snapshot), sha256=digest)}
        source.write_text('subsequent implementation')
        check_native_input(self.root, source, digest, archived)
        snapshot.write_text('forged original native source')
        with self.assertRaises(FormatError):
            check_native_input(self.root, source, digest, archived)
        binding = json.loads(self.archive.read_text())['files'][0]
        self.original.write_text('forged runtime log')
        with self.assertRaises(FormatError):
            check_native_input(self.root, self.original, binding['sha256'], {str(self.original): binding})


if __name__ == '__main__':
    unittest.main()
