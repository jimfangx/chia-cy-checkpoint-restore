"""Compiled fault provenance must survive coherent receipt rehashing."""
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests.audit_native_queue_staging import compiled_mutations, sha


class NativeQueueStagingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'generated').mkdir()
        self.original = (
            '    .live_state(capture_native_state),\n'
            '    .request_valid(capture_request_valid && staged_permission),\n'
            '    .response_ready(capture_response_ready && staged_permission));\n')
        self.original_path = self.root/'generated/Staged-generated.native-region-graft.sv'
        self.original_path.write_text(self.original)
        self.expected = {
            'compiled-staging-swap.sv': self.original.replace('.live_state(capture_native_state),',
                '.live_state({capture_native_state[1663:0],capture_native_state[6655:1664]}),'),
            'compiled-premature.sv': self.original.replace(
                'capture_request_valid && staged_permission', 'capture_request_valid'),
            'compiled-busy-release.sv': self.original.replace(
                'capture_response_ready && staged_permission', 'capture_response_ready'),
        }
        for name, text in self.expected.items():
            (self.root/name).write_text(text)
        self.receipt = dict(artifacts={name: sha(self.root/name) for name in self.expected})

    def test_all_three_exact_compiled_variants_are_bound(self):
        self.assertEqual(compiled_mutations(self.root, self.receipt), self.receipt['artifacts'])

    def test_unbound_source_is_rejected_even_when_present(self):
        for name in self.expected:
            with self.subTest(name=name):
                receipt = dict(artifacts=dict(self.receipt['artifacts']))
                del receipt['artifacts'][name]
                with self.assertRaisesRegex(FormatError, 'unbound compiled mutation'):
                    compiled_mutations(self.root, receipt)

    def test_coherently_rehashed_wrong_mutations_are_rejected(self):
        for name, text in self.expected.items():
            with self.subTest(name=name):
                path = self.root/name
                path.write_text(self.original)
                receipt = dict(artifacts=dict(self.receipt['artifacts'], **{name: sha(path)}))
                with self.assertRaisesRegex(FormatError, 'wrong compiled mutation'):
                    compiled_mutations(self.root, receipt)
                path.write_text(text)

    def test_swapped_variants_and_extra_edits_are_rejected_after_rehash(self):
        for name, text in self.expected.items():
            for wrong in (next(v for k, v in self.expected.items() if k != name), text+'// extra edit\n'):
                with self.subTest(name=name, wrong=wrong):
                    path = self.root/name
                    path.write_text(wrong)
                    receipt = dict(artifacts=dict(self.receipt['artifacts'], **{name: sha(path)}))
                    with self.assertRaisesRegex(FormatError, 'wrong compiled mutation'):
                        compiled_mutations(self.root, receipt)
                    path.write_text(text)

    def test_changed_or_missing_bound_source_is_rejected(self):
        for name, text in self.expected.items():
            with self.subTest(name=name):
                path = self.root/name
                path.write_text('changed')
                with self.assertRaisesRegex(FormatError, 'changed compiled mutation'):
                    compiled_mutations(self.root, self.receipt)
                path.unlink()
                with self.assertRaisesRegex(FormatError, 'unbound compiled mutation'):
                    compiled_mutations(self.root, self.receipt)
                path.write_text(text)

    def test_ambiguous_original_mutation_site_is_rejected(self):
        self.original_path.write_text(self.original*2)
        with self.assertRaisesRegex(FormatError, 'ambiguous original compiled mutation'):
            compiled_mutations(self.root, self.receipt)
