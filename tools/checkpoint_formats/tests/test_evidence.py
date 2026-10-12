import json
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError, canonical
from tools.checkpoint_formats.evidence import (
    artifact_catalog, audit_pair, file_sha, select_audit_pair, selected_audit_pair,
)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.proof = self.root / 'proof'
        self.proof.mkdir()
        (self.proof / 'engine.log').write_text('raw engine evidence\n')
        self.paths = []
        for name in ('first', 'second', 'retry'):
            run = self.root / name
            run.mkdir()
            path = run / 'summary.json'
            path.write_bytes(canonical(dict(status='passed', run=str(run), proof_run=str(self.proof),
                original_proofs_unchanged=True, formal_state_map_complete=False, gate_restore_authorized=False,
                original_proof_hashes={str(self.proof / 'engine.log'): file_sha(self.proof / 'engine.log')})))
            self.paths.append(path)
        self.selection = self.root / 'pair.json'

    def select(self, paths=None):
        return select_audit_pair(paths or self.paths[:2], self.proof, self.selection)

    def test_unselected_retry_does_not_invalidate_pair(self):
        self.select()
        self.paths[2].write_text('failed retry remains diagnostic\n')
        self.assertEqual([p for p, _ in audit_pair(self.selection, self.proof)], self.paths[:2])

    def test_selected_proof_survives_latest_proof_retry(self):
        self.select()
        latest = self.root / 'selection.json'
        latest.write_bytes(canonical(dict(run=str(self.proof))))
        retry = self.root / 'new-proof'
        retry.mkdir()
        (retry / 'engine.log').write_text('different proof invocation\n')
        latest.write_bytes(canonical(dict(run=str(retry))))
        proof, reports = selected_audit_pair(self.selection)
        self.assertEqual(proof, self.proof)
        self.assertEqual([p for p, _ in reports], self.paths[:2])
        with self.assertRaises(FormatError):
            audit_pair(self.selection, retry)
        (self.proof / 'engine.log').write_text('changed selected proof\n')
        with self.assertRaises(FormatError):
            selected_audit_pair(self.selection)

    def test_selected_proof_requires_absolute_existing_bound_directory(self):
        original = self.select()
        for value in (42, 'relative', str(self.root / 'missing'), str(self.root), str(self.paths[0])):
            self.selection.write_bytes(canonical(dict(original, proof_run=value)))
            with self.subTest(value=value), self.assertRaises(FormatError):
                selected_audit_pair(self.selection)

    def test_duplicate_alias_or_hardlinked_report_rejects(self):
        alias = self.root / 'alias.json'
        alias.symlink_to(self.paths[0])
        hardlink = self.root / 'hardlink.json'
        hardlink.hardlink_to(self.paths[0])
        for paths in ([self.paths[0]] * 2, [self.paths[0], alias], [self.paths[0], hardlink]):
            with self.subTest(paths=paths), self.assertRaises(FormatError):
                self.select(paths)
        self.assertFalse(self.selection.exists())

    def test_missing_empty_or_changed_selected_report_rejects(self):
        self.select()
        original = self.paths[0].read_bytes()
        for data in (b'', original + b'\n'):
            self.paths[0].write_bytes(data)
            with self.subTest(data=data), self.assertRaises(FormatError):
                audit_pair(self.selection, self.proof)
        self.paths[0].unlink()
        with self.assertRaises(FormatError):
            audit_pair(self.selection, self.proof)

    def test_changed_missing_or_added_proof_artifact_rejects(self):
        self.select()
        engine = self.proof / 'engine.log'
        original = engine.read_bytes()
        engine.write_text('forged engine\n')
        with self.assertRaises(FormatError):
            audit_pair(self.selection, self.proof)
        engine.unlink()
        with self.assertRaises(FormatError):
            audit_pair(self.selection, self.proof)
        engine.write_bytes(original)
        (self.proof / 'extra.log').write_text('unbound extra artifact\n')
        with self.assertRaises(FormatError):
            audit_pair(self.selection, self.proof)

    def test_wrong_provenance_or_authorization_rejects_even_rehashed(self):
        original = json.loads(self.paths[0].read_text())
        for field, value in [('proof_run', str(self.root)), ('run', str(self.root)),
                             ('status', 'failed'), ('formal_state_map_complete', True),
                             ('gate_restore_authorized', True), ('original_proofs_unchanged', False)]:
            self.paths[0].write_bytes(canonical(dict(original, **{field: value})))
            with self.subTest(field=field), self.assertRaises(FormatError):
                self.select()

    def test_wrong_pair_count_or_proof_run_rejects(self):
        for paths in (self.paths[:1], self.paths):
            with self.subTest(count=len(paths)), self.assertRaises(FormatError):
                self.select(paths)
        self.select()
        with self.assertRaises(FormatError):
            audit_pair(self.selection, self.root)

    def test_incomplete_rehashed_report_rejects(self):
        original = json.loads(self.paths[0].read_text())
        for changed in ([], {}, {k: v for k, v in original.items() if k != 'original_proof_hashes'},
                        dict(original, original_proof_hashes=[]), dict(original, run=42)):
            self.paths[0].write_bytes(canonical(changed))
            with self.subTest(changed=changed), self.assertRaises(FormatError):
                self.select()

    def test_catalog_requires_concrete_nonempty_absolute_files(self):
        alias = self.root / 'link'
        alias.symlink_to(self.paths[0])
        catalog = artifact_catalog([self.paths[0], alias])
        self.assertEqual(catalog, [dict(path=str(self.paths[0]), bytes=self.paths[0].stat().st_size,
                                       sha256=file_sha(self.paths[0]))])
        empty = self.root / 'empty'
        empty.touch()
        for path in (empty, self.root, self.root / 'missing', Path('relative.json')):
            with self.subTest(path=path), self.assertRaises(FormatError):
                artifact_catalog([path])
