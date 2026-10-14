import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.native_regressions import audit_suite, run_suite


class NativeRegressionRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.out = self.root / 'automations/checkpoint_loop/runs/regressions'

    def checks(self, out):
        return [dict(purpose='retention test ' + str(i), cwd='.',
                     argv=[sys.executable, '-c', 'import os; print(os.getpid())']) for i in range(8)]

    def test_repeated_native_processes_retain_all_original_artifacts(self):
        first = run_suite(self.root, self.out, self.checks)
        bound = {str(p): file_sha(p) for p in first.parent.rglob('*') if p.is_file()}
        second = run_suite(self.root, self.out, self.checks)
        self.assertNotEqual(first.parent, second.parent)
        self.assertEqual(bound, {name: file_sha(name) for name in bound})
        self.assertEqual(audit_suite(first)['checks'], 8)
        self.assertEqual(audit_suite(second)['checks'], 8)

    def test_failure_is_retained_and_cannot_be_audited_as_pass(self):
        def failing(out):
            checks = self.checks(out)
            checks[2]['argv'] = [sys.executable, '-c', 'raise SystemExit(7)']
            return checks
        with self.assertRaisesRegex(FormatError, 'native regression failed'):
            run_suite(self.root, self.out, failing)
        report = next(self.out.glob('invocation-*/summary.json'))
        summary = json.loads(report.read_text())
        self.assertEqual(summary['status'], 'failed')
        self.assertEqual([c['returncode'] for c in summary['checks']], [0, 0, 7])
        with self.assertRaisesRegex(FormatError, 'did not finish'):
            audit_suite(report)

    def test_changed_missing_and_extra_evidence_reject(self):
        report = run_suite(self.root, self.out, self.checks)
        log = report.parent / 'check-0.log'
        saved = log.read_bytes()
        log.write_bytes(saved + b' altered')
        with self.assertRaisesRegex(FormatError, 'changed native'):
            audit_suite(report)
        log.write_bytes(saved)
        log.unlink()
        with self.assertRaisesRegex(FormatError, 'missing/extra'):
            audit_suite(report)
        log.write_bytes(saved)
        (report.parent / 'extra.log').write_text('not recorded')
        with self.assertRaisesRegex(FormatError, 'missing/extra'):
            audit_suite(report)

    def test_actual_retained_log_mutation_fails_post_execution_guard(self):
        self.out.mkdir(parents=True)
        original = self.out / 'prior-native.log'
        original.write_text('original native result')
        snapshot = self.out / 'snapshot'
        snapshot.write_bytes(original.read_bytes())
        archive = self.out / 'archive.json'
        archive.write_text(json.dumps(dict(files=[dict(path=str(original), snapshot=str(snapshot),
                                                      sha256=file_sha(original), bytes=original.stat().st_size)])))
        protected = self.out / 'protected.json'
        protected.write_text(json.dumps(dict(heads=['root-head', 'firesim-head'])))

        def mutation(out):
            return [dict(purpose='actual overwriting process', cwd='.', argv=[sys.executable, '-c',
                         'from pathlib import Path; Path(' + repr(str(original)) + ').write_text("overwritten")'])]

        with patch('tools.checkpoint_formats.retained_evidence.controller_ancestry', return_value=['saved']):
            with self.assertRaisesRegex(FormatError, 'changed original retained evidence'):
                run_suite(self.root, self.out, mutation, [(archive, protected)])
        report = next(self.out.glob('invocation-*/summary.json'))
        summary = json.loads(report.read_text())
        self.assertEqual(summary['status'], 'failed')
        self.assertEqual(summary['checks'][0]['returncode'], 0)
        self.assertEqual(snapshot.read_text(), 'original native result')

    def test_source_change_during_real_process_execution_cannot_pass(self):
        source = self.root / 'native.cc'
        source.write_text('original native source')

        def mutation(out):
            return [dict(purpose='actual changing process', cwd='.', argv=[sys.executable, '-c',
                         'from pathlib import Path; Path(' + repr(str(source)) + ').write_text("changed")'])]

        with self.assertRaisesRegex(FormatError, 'source changed during execution'):
            run_suite(self.root, self.out, mutation, sources=[source])
        report = next(self.out.glob('invocation-*/summary.json'))
        summary = json.loads(report.read_text())
        self.assertEqual(summary['status'], 'failed')
        binding = summary['source_inputs'][0]
        self.assertEqual(Path(binding['snapshot']).read_text(), 'original native source')


if __name__ == '__main__':
    unittest.main()
