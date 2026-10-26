"""Receipt isolation and fail-closed provenance; these fixtures never run VCS."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.regression_runner import audit, execute


CHILD = '''
import argparse,hashlib,json,shutil
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('native','out','mode','case'):p.add_argument('--'+name,required=True)
a=p.parse_args();out=Path(a.out)/'vcs-fixture';out.mkdir()
native=Path(a.native);doc=json.loads((native/'summary.json').read_text())
shutil.copyfile(native/'payload',out/'payload')
(out/'execution.log').write_text('fixture executed; no VCS or FPGA acceptance')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result=dict(status='pass',backend='eda',sources=doc['sources'],inputs=doc['inputs'],
            artifacts={'execution.log':sha(out/'execution.log')})
if a.case=='failed-status':result['status']='fail'
if a.case=='wrong-backend':result['backend']='f2'
if a.case=='bad-input':(out/'payload').write_text('changed payload')
if a.case=='source-drift':Path('design.sv').write_text('changed source')
if a.case=='duplicate':
 other=Path(a.out)/'vcs-other';other.mkdir();(other/'summary.json').write_text(json.dumps(result))
if a.case=='escape':
 out.rmdir() if not list(out.iterdir()) else None
 (out/'summary.json').symlink_to(native/'summary.json')
else:(out/'summary.json').write_text(json.dumps(result))
print(native/'summary.json' if a.case=='old-receipt' else out/'summary.json',flush=True)
raise SystemExit(3 if a.case=='nonzero' else 0)
'''


class RegressionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.runs = self.root / 'automations/checkpoint_loop/runs/test'
        self.runs.mkdir(parents=True)
        self.native = self.runs / 'native'
        self.native.mkdir()
        (self.root / 'design.sv').write_text('unchanged native input')
        (self.native / 'payload').write_text('native payload')
        (self.native / 'synth.log').write_text('fixture only, not synthesis')
        self.native_doc = dict(status='pass', backend='f2',
                               sources={'design.sv': file_sha(self.root / 'design.sv')},
                               inputs={'payload': file_sha(self.native / 'payload')},
                               artifacts={'synth.log': file_sha(self.native / 'synth.log')})
        (self.native / 'summary.json').write_text(json.dumps(self.native_doc))
        self.child = self.root / 'child.py'
        self.child.write_text(CHILD)
        self.output = self.runs / 'regressions'
        self.plan = self.runs / 'plan.json'
        self.command = dict(scope='connected', backend='eda', cwd='.',
                            argv=[sys.executable, str(self.child), '--mode', 'vcs',
                                  '--native', str(self.native), '--out', str(self.runs / 'old-output'),
                                  '--case', 'healthy'],
                            native_receipt=dict(path=str(self.native / 'summary.json'),
                                                sha256=file_sha(self.native / 'summary.json')))
        self.write_plan()

    def write_plan(self):
        self.plan.write_text(json.dumps(dict(format_version=1, backend='eda', commands=[self.command])))

    def run_case(self, case='healthy'):
        self.command['argv'][-1] = case
        self.write_plan()
        return execute(self.plan, self.output, self.root)

    def failed_result(self):
        paths = list(self.output.glob('*/result.json'))
        self.assertEqual(len(paths), 1)
        result = json.loads(paths[0].read_text())
        self.assertEqual(result['status'], 'fail')
        self.assertFalse(result['receipts'])
        return result

    def test_controller_rerun_retains_old_bytes_and_selects_only_new_attempt(self):
        # Reproduce the prior failure: several summaries already exist under
        # the template output, and a completed invocation is run a second time.
        stale = self.runs / 'old-output'
        for name in ('old-one', 'old-two'):
            (stale / name).mkdir(parents=True)
            (stale / name / 'summary.json').write_text('historical receipt')
        first = self.run_case()
        saved = {p: p.read_bytes() for p in first.parent.rglob('*') if p.is_file()}
        second = execute(self.plan, self.output, self.root)
        self.assertNotEqual(first.parent, second.parent)
        for p, data in saved.items():
            self.assertEqual(p.read_bytes(), data)
        for path in (first, second):
            self.assertEqual(audit(path, self.root)['scopes'], ['connected'])
        self.assertEqual((stale / 'old-one/summary.json').read_text(), 'historical receipt')

    def test_two_new_receipts_reject_instead_of_choosing_latest(self):
        with self.assertRaisesRegex(FormatError, 'ambiguous'):
            self.run_case('duplicate')
        self.failed_result()

    def test_exit_zero_cannot_substitute_old_receipt(self):
        with self.assertRaisesRegex(FormatError, 'explicitly return'):
            self.run_case('old-receipt')
        self.failed_result()

    def test_nonzero_keeps_failing_command_log_even_with_pass_summary(self):
        with self.assertRaisesRegex(FormatError, 'underlying log'):
            self.run_case('nonzero')
        result = self.failed_result()
        command = result['commands'][0]
        self.assertEqual(command['returncode'], 3)
        self.assertEqual(file_sha(command['log']), command['log_sha256'])

    def test_child_status_backend_and_payload_do_not_bypass_validation(self):
        for case in ('failed-status', 'wrong-backend', 'bad-input', 'escape'):
            with self.subTest(case=case), self.assertRaises(FormatError):
                self.run_case(case)

    def test_source_change_during_execution_rejects_pass_receipt(self):
        with self.assertRaisesRegex(FormatError, 'source stale'):
            self.run_case('source-drift')
        self.failed_result()

    def test_stale_later_scope_rejects_before_any_process_runs(self):
        doc = json.loads(self.plan.read_text())
        other = dict(self.command, scope='second', native_receipt=dict(self.command['native_receipt'], sha256='0' * 64))
        doc['commands'].append(other)
        self.plan.write_text(json.dumps(doc))
        with self.assertRaisesRegex(FormatError, 'pin changed'):
            execute(self.plan, self.output, self.root)
        self.assertEqual(self.failed_result()['commands'], [])

    def test_duplicate_or_wrong_backend_scope_rejects_without_execution(self):
        doc = json.loads(self.plan.read_text())
        doc['commands'] *= 2
        self.plan.write_text(json.dumps(doc))
        with self.assertRaisesRegex(FormatError, 'duplicate'):
            execute(self.plan, self.output, self.root)
        self.assertFalse(self.output.exists())
        doc['commands'] = [dict(self.command, backend='f2')]
        self.plan.write_text(json.dumps(doc))
        with self.assertRaisesRegex(FormatError, 'EDA argv'):
            execute(self.plan, self.output, self.root)

    def test_missing_or_duplicate_output_options_cannot_redirect_attempt(self):
        for tail in (['--out', 'extra'], []):
            self.command['argv'] = [sys.executable, str(self.child), '--native', str(self.native), '--mode', 'vcs'] + tail
            if tail:self.command['argv'] += tail
            self.write_plan()
            with self.subTest(tail=tail), self.assertRaisesRegex(FormatError, '--out'):
                execute(self.plan, self.output, self.root)

    def test_audit_rejects_missing_scopes_changed_argv_receipts_logs_and_native(self):
        path = self.run_case()
        original = path.read_bytes()
        doc = json.loads(original)
        mutations = [dict(doc, receipts={}), dict(doc, commands=[])]
        changed = json.loads(original)
        changed['commands'][0]['argv'][0] = 'different-interpreter'
        mutations.append(changed)
        changed = json.loads(original)
        changed['receipts']['connected']['native_receipt_sha256'] = '0' * 64
        mutations.append(changed)
        for mutation in mutations:
            path.write_text(json.dumps(mutation))
            with self.assertRaises(FormatError):
                audit(path, self.root)
        path.write_bytes(original)
        files = [Path(doc['commands'][0]['log']), Path(doc['receipts']['connected']['path']),
                 self.native / 'payload', self.native / 'summary.json', self.plan]
        for target in files:
            before = target.read_bytes()
            target.write_bytes(before + b'\nchanged')
            with self.subTest(target=target), self.assertRaises(FormatError):
                audit(path, self.root)
            target.write_bytes(before)
        self.assertEqual(audit(path, self.root)['status'], 'pass')


if __name__ == '__main__':
    unittest.main()
