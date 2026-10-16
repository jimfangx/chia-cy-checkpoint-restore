from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.native_input_guard import (
    audit_reused_input_guard, pin_reused_inputs, require_live_inputs_unchanged)


class ReusedNativeInputTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runs = self.root/'automations/checkpoint_loop/runs'
        self.runs.mkdir(parents=True)
        self.script = self.root/'verify.py'
        self.header = self.root/'driver.h'
        self.binary = self.runs/'simv'
        self.script.write_text('pin_reused_inputs(root, bindings, snapshots)')
        self.header.write_text('original compiled header')
        self.binary.write_bytes(b'original native executable')
        self.bindings = []
        for index, path in enumerate((self.script, self.header, self.binary)):
            snapshot = self.runs/str(index)
            snapshot.write_bytes(path.read_bytes())
            self.bindings.append(dict(path=str(path), sha256=file_sha(path), snapshot=str(snapshot)))

    def pin(self, **kwargs):
        return pin_reused_inputs(self.root, self.bindings, self.runs/'invocation', **kwargs)

    def report(self, pinned):
        return dict(source_inputs=self.bindings, invocation_source_inputs=pinned)

    def test_evolved_auditor_pins_current_bytes_and_preserves_original_build(self):
        self.script.write_text('updated auditor using pin_reused_inputs(root, bindings, snapshots)')
        pinned = self.pin(compiled=[self.header, self.binary])
        self.assertNotEqual(pinned[0]['sha256'], self.bindings[0]['sha256'])
        self.assertEqual(Path(pinned[0]['snapshot']).read_bytes(), self.script.read_bytes())
        require_live_inputs_unchanged(pinned)
        audit_reused_input_guard(self.root, self.report(pinned), self.script, compiled=[self.header, self.binary])

    def test_changed_compiled_header_rejects_before_build(self):
        self.header.write_text('incompatible driver header')
        with self.assertRaisesRegex(FormatError, 'changed new compilation input'):
            self.pin(compiled=[self.header])
        # Reusing an audited executable still binds its original header bytes.
        require_live_inputs_unchanged(self.pin())

    def test_edit_during_invocation_rejects_even_with_valid_old_snapshot(self):
        self.script.write_text('first updated auditor')
        pinned = self.pin()
        self.script.write_text('second update during execution')
        with self.assertRaisesRegex(FormatError, 'source changed during native invocation'):
            require_live_inputs_unchanged(pinned)

    def test_changed_runtime_executable_and_bad_source_snapshot_reject(self):
        original = self.binary.read_bytes()
        self.binary.write_bytes(b'changed native executable')
        with self.assertRaisesRegex(FormatError, 'changed/unarchived'):
            self.pin()
        self.binary.write_bytes(original)
        Path(self.bindings[0]['snapshot']).write_text('forged original auditor')
        with self.assertRaisesRegex(FormatError, 'changed inherited source snapshot'):
            self.pin()

    def test_missing_duplicate_or_unbound_inputs_reject(self):
        with self.assertRaisesRegex(FormatError, 'unbound new compilation input'):
            self.pin(compiled=[self.root/'omitted.cc'])
        self.bindings.append(self.bindings[0])
        with self.assertRaisesRegex(FormatError, 'ambiguous'):
            self.pin()
        self.bindings.pop()
        self.header.unlink()
        with self.assertRaisesRegex(FormatError, 'missing original native input'):
            self.pin()

    def test_audit_rejects_missing_guards_forged_snapshots_and_recompiled_sources(self):
        pinned = self.pin()
        report = self.report(pinned)
        report.pop('invocation_source_inputs')
        with self.assertRaisesRegex(FormatError, 'invocation source guard'):
            audit_reused_input_guard(self.root, report, self.script)
        report = self.report(pinned[:-1])
        with self.assertRaisesRegex(FormatError, 'incomplete invocation source guard'):
            audit_reused_input_guard(self.root, report, self.script)
        self.header.write_text('newly compiled but unbound header')
        report = self.report(self.pin())
        with self.assertRaisesRegex(FormatError, 'unbound new compilation source'):
            audit_reused_input_guard(self.root, report, self.script, compiled=[self.header])
        Path(report['invocation_source_inputs'][0]['snapshot']).write_text('forged invocation input')
        with self.assertRaisesRegex(FormatError, 'changed invocation source snapshot'):
            audit_reused_input_guard(self.root, report, self.script)

    def test_historical_report_without_guard_remains_auditable(self):
        Path(self.bindings[0]['snapshot']).write_text('historical verifier without invocation pinning')
        self.bindings[0]['sha256'] = file_sha(self.bindings[0]['snapshot'])
        audit_reused_input_guard(self.root, dict(source_inputs=self.bindings), self.script)


if __name__ == '__main__':
    unittest.main()
