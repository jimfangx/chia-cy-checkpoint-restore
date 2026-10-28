"""Preflight reruns must preserve every receipt and input referenced by an audit."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import f2_inventory
import f2_preflight


class PreflightTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.selected = self.base / "setup-selected.json"
        self.invocation = self.base / "build"
        self.invocation.mkdir()
        (self.invocation / "manager-commands.json").write_text(json.dumps(dict(run_farm_tag="checkpoint-f2-test")))
        (self.invocation / "config_runtime.yaml").write_text(yaml.safe_dump(dict(
            run_farm=dict(recipe_arg_overrides=dict(run_farm_tag="checkpoint-f2-test")),
            metasimulation=dict(metasimulation_enabled=False))))
        self.protected = self.base / "inputs.json"
        self.input = self.base / "plan.txt"
        self.input.write_text("read only")
        self.protected.write_text(json.dumps({str(self.input): f2_preflight.sha(self.input)}))
        for module in (f2_preflight, f2_inventory):
            scope = patch.object(module, "RUNS", self.base)
            scope.start()
            self.addCleanup(scope.stop)

    def collect(self, attempt, invocation, protected, session):
        (attempt / "native-setup.log").write_text("Vivado output")
        (attempt / "resource-inventory.json").write_text('{"request": "unique observation"}')
        return dict(status="pass", protected_inputs_unchanged=True, aws_identity={"RequestId": attempt.name})

    def run_check(self):
        return f2_preflight.run_preflight(self.base / "manager", self.invocation, self.protected,
                                           selected=self.selected, session=object())

    def assert_pinned(self, pin):
        receipt = Path(pin["path"])
        self.assertEqual(f2_preflight.sha(receipt), pin["sha256"])
        doc = json.loads(receipt.read_text())
        self.assertEqual(doc["status"], "pass")
        for name, digest in doc["artifacts"].items():
            self.assertEqual(f2_preflight.sha(receipt.parent / name), digest)

    def test_repeated_success_preserves_selected_receipt_and_all_evidence(self):
        with patch.object(f2_preflight, "collect", side_effect=self.collect):
            first = self.run_check()
            first_pin = json.loads(self.selected.read_text())
            first_files = {p: p.read_bytes() for p in first.parent.iterdir()}
            second = self.run_check()
        self.assertNotEqual(first, second)
        self.assertNotEqual(first.parent, second.parent)
        self.assertEqual(first_files, {p: p.read_bytes() for p in first.parent.iterdir()})
        self.assert_pinned(first_pin)
        self.assert_pinned(json.loads(self.selected.read_text()))

    def test_exception_and_failed_result_preserve_previous_success_selection(self):
        with patch.object(f2_preflight, "collect", side_effect=self.collect):
            self.run_check()
        pin_bytes = self.selected.read_bytes()
        for effect in (RuntimeError("AccessDenied"), lambda *args: dict(status="fail")):
            with self.subTest(effect=str(effect)), patch.object(f2_preflight, "collect", side_effect=effect):
                receipt = self.run_check()
                doc = json.loads(receipt.read_text())
                self.assertEqual(doc["status"], "fail")
                self.assertEqual(self.selected.read_bytes(), pin_bytes)
                self.assertTrue((receipt.parent / "protected-inputs.json").is_file())
        self.assert_pinned(json.loads(pin_bytes))
        original_sha = f2_preflight.sha
        producer_changed = False

        def changed_source_digest(path):
            if producer_changed and path == f2_preflight.ROOT / "automations/checkpoint_loop/f2_preflight.py":
                return "0" * 64
            return original_sha(path)

        def change_during_collection(*args):
            nonlocal producer_changed
            result = self.collect(*args)
            producer_changed = True
            return result

        with patch.object(f2_preflight, "sha", side_effect=changed_source_digest), patch.object(
                f2_preflight, "collect", side_effect=change_during_collection):
            receipt = self.run_check()
        self.assertEqual(json.loads(receipt.read_text())["status"], "fail")
        self.assertEqual(self.selected.read_bytes(), pin_bytes)

    def test_receipt_artifact_binding_detects_changed_evidence(self):
        with patch.object(f2_preflight, "collect", side_effect=self.collect):
            receipt = self.run_check()
        pin = json.loads(self.selected.read_text())
        self.assert_pinned(pin)
        (receipt.parent / "resource-inventory.json").write_text("tampered")
        with self.assertRaises(AssertionError):
            self.assert_pinned(pin)

    def test_invalid_evidence_scope_rejects_before_collect(self):
        with patch.object(f2_preflight, "collect") as collector:
            with self.assertRaisesRegex(ValueError, "beneath"):
                f2_preflight.run_preflight(self.base.parent / "outside", self.invocation, self.protected,
                                            selected=self.selected, session=object())
            collector.assert_not_called()

    def test_durable_audit_rejects_changed_missing_escaped_or_unbound_artifacts(self):
        with patch.object(f2_preflight, "collect", side_effect=self.collect):
            receipt = self.run_check()
        pin = json.loads(self.selected.read_text())
        original_doc = json.loads(receipt.read_text())
        self.assertEqual(f2_preflight.audit_receipt(receipt, pin["sha256"])["status"], "pass")
        resource = receipt.parent / "resource-inventory.json"
        original_resource = resource.read_bytes()
        resource.unlink()
        with self.assertRaisesRegex(ValueError, "artifact hash"):
            f2_preflight.audit_receipt(receipt, pin["sha256"])
        resource.write_bytes(original_resource)
        resource.write_text("changed")
        with self.assertRaisesRegex(ValueError, "artifact hash"):
            f2_preflight.audit_receipt(receipt, pin["sha256"])
        resource.write_bytes(original_resource)
        for name in ("../outside", str(self.protected), "subdir/../resource-inventory.json"):
            with self.subTest(name=name):
                doc = json.loads(json.dumps(original_doc))
                doc["artifacts"][name] = f2_preflight.sha(self.protected)
                receipt.write_text(json.dumps(doc))
                with self.assertRaisesRegex(ValueError, "direct local file"):
                    f2_preflight.audit_receipt(receipt, f2_preflight.sha(receipt))
        receipt.write_text(json.dumps(original_doc))
        (receipt.parent / "extra-evidence.log").write_text("unbound")
        with self.assertRaisesRegex(ValueError, "unbound evidence"):
            f2_preflight.audit_receipt(receipt, f2_preflight.sha(receipt))

    def test_durable_audit_rejects_changed_receipt_and_protected_inputs(self):
        with patch.object(f2_preflight, "collect", side_effect=self.collect):
            receipt = self.run_check()
        expected = f2_preflight.sha(receipt)
        original_bytes = receipt.read_bytes()
        doc = json.loads(original_bytes)
        doc["sources"]["automations/checkpoint_loop/f2_preflight.py"] = "0" * 64
        receipt.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "producer sources"):
            f2_preflight.audit_receipt(receipt, f2_preflight.sha(receipt))
        receipt.write_bytes(original_bytes)
        self.input.write_text("changed plan")
        with self.assertRaisesRegex(ValueError, "protected inputs changed"):
            f2_preflight.audit_receipt(receipt, expected)
        receipt.write_text(receipt.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "receipt hash"):
            f2_preflight.audit_receipt(receipt, expected)


if __name__ == "__main__":
    unittest.main()
