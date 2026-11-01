"""Preflight reruns must preserve every receipt and input referenced by an audit."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

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
        inventory, summary = resource_fixture()
        inventory["aws_identity"] = summary["aws_identity"] = {"RequestId": attempt.name}
        (attempt / "resource-inventory.json").write_text(json.dumps(inventory))
        return dict(status="pass", protected_inputs_unchanged=True, **summary)

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

    def test_rehashed_inventory_cannot_hide_pending_image(self):
        with patch.object(f2_preflight, "collect", side_effect=self.collect):
            receipt = self.run_check()
        doc = json.loads(receipt.read_text())
        doc["pending_afi_ids"] = []
        receipt.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "resource summary"):
            f2_preflight.audit_receipt(receipt, f2_preflight.sha(receipt))
        # Rehashing the inventory and its enclosing receipt cannot erase an API page.
        resource = receipt.parent / "resource-inventory.json"
        inventory = json.loads(resource.read_text())
        inventory["owned_fpga_images"]["FpgaImages"] = []
        resource.write_text(json.dumps(inventory))
        doc["artifacts"][resource.name] = f2_preflight.sha(resource)
        receipt.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "flattened images"):
            f2_preflight.audit_receipt(receipt, f2_preflight.sha(receipt))


def resource_fixture():
    """A busy account is a valid observation, not an idle-resource assertion."""
    image = dict(FpgaImageId="afi-pending", FpgaImageGlobalId="agfi-pending",
                 Name="saturn-autoila", State=dict(Code="pending"), Tags=[])
    instance = dict(InstanceId="i-running", State=dict(Name="running"),
                    Tags=[dict(Key="fsimcluster", Value="checkpoint-f2-other")])
    process = dict(pid=23, executable="/tools/vivado", argv=["vivado", "-mode", "batch"])
    inventory = dict(owned_fpga_images=dict(FpgaImages=[image], pages=[dict(
        request=dict(Owners=["self"]), response=dict(FpgaImages=[image]))]),
        all_loop_instance_filters=[dict(Name="tag:fsimcluster", Values=["checkpoint-f2-*"])],
        all_loop_instances=[instance], local_build_processes=dict(processes=[process]),
        aws_identity=dict(Account="123"), region="us-west-2")
    summary = dict(owned_afi_ids=["afi-pending"], pending_afi_ids=["afi-pending"],
                   active_loop_instance_ids=["i-running"], local_processes=[process],
                   aws_identity=inventory["aws_identity"], region="us-west-2",
                   pending_afi_scope="account-owned in observed region; loop ownership unproven")
    return inventory, summary


class ResourceAuditTests(unittest.TestCase):
    def test_pending_untagged_afi_and_active_resources_are_preserved(self):
        inventory, summary = resource_fixture()
        before = deepcopy((inventory, summary))
        result = f2_preflight.audit_resources(summary, inventory)
        self.assertEqual(result["pending_account_fpga_images"], inventory["owned_fpga_images"]["FpgaImages"])
        self.assertEqual(result["active_loop_instance_ids"], ["i-running"])
        self.assertEqual(result["local_processes"], summary["local_processes"])
        self.assertIn("ownership unproven", result["pending_afi_scope"])
        self.assertEqual((inventory, summary), before)

    def test_account_query_follows_empty_intermediate_page(self):
        inventory, summary = resource_fixture()
        image = inventory["owned_fpga_images"]["FpgaImages"][0]
        ec2 = MagicMock()
        ec2.describe_fpga_images.side_effect = [dict(FpgaImages=[], NextToken="one"),
            dict(FpgaImages=[], NextToken="two"), dict(FpgaImages=[image])]
        inventory["owned_fpga_images"] = f2_preflight.account_fpga_images(ec2)
        self.assertEqual(f2_preflight.audit_resources(summary, inventory)["afi_api_pages"], 3)
        self.assertEqual([call.kwargs for call in ec2.describe_fpga_images.call_args_list],
                         [dict(Owners=["self"]), dict(Owners=["self"], NextToken="one"),
                          dict(Owners=["self"], NextToken="two")])
        self.assertEqual(set(ec2.method_calls[i][0] for i in range(3)), {"describe_fpga_images"})

    def test_empty_account_is_complete_only_with_terminal_api_page(self):
        inventory, summary = resource_fixture()
        ec2 = MagicMock()
        ec2.describe_fpga_images.return_value = dict(FpgaImages=[])
        inventory["owned_fpga_images"] = f2_preflight.account_fpga_images(ec2)
        summary.update(owned_afi_ids=[], pending_afi_ids=[])
        self.assertEqual(f2_preflight.audit_resources(summary, inventory)["pending_account_fpga_images"], [])
        inventory["owned_fpga_images"]["pages"] = []
        with self.assertRaisesRegex(ValueError, "omits API pages"):
            f2_preflight.audit_resources(summary, inventory)

    def test_pagination_error_or_repeated_token_is_not_empty_success(self):
        ec2 = MagicMock()
        ec2.describe_fpga_images.side_effect = [dict(FpgaImages=[], NextToken="one"), RuntimeError("AccessDenied")]
        with self.assertRaisesRegex(RuntimeError, "AccessDenied"):
            f2_preflight.account_fpga_images(ec2)
        ec2.describe_fpga_images.side_effect = [dict(FpgaImages=[], NextToken="one")] * 2
        with self.assertRaisesRegex(ValueError, "repeated AFI"):
            f2_preflight.account_fpga_images(ec2)

    def test_incomplete_reordered_or_wrong_owner_pages_reject(self):
        for case in ("truncated", "wrong-owner", "extra-terminal", "wrong-token", "repeat-token", "duplicate-image"):
            with self.subTest(case=case):
                inventory, summary = resource_fixture()
                owned = inventory["owned_fpga_images"]
                page = owned["pages"][0]
                if case == "truncated":
                    page["response"]["NextToken"] = "remaining"
                elif case == "wrong-owner":
                    page["request"]["Owners"] = ["all"]
                elif case == "extra-terminal":
                    owned["pages"].append(deepcopy(page))
                else:
                    page["response"]["NextToken"] = "one"
                    owned["pages"].append(dict(request=dict(Owners=["self"], NextToken="one"),
                                               response=dict(FpgaImages=[])))
                    if case == "wrong-token":
                        owned["pages"][1]["request"]["NextToken"] = "two"
                    elif case == "repeat-token":
                        owned["pages"][1]["response"]["NextToken"] = "one"
                    else:
                        owned["pages"][1]["response"]["FpgaImages"] = [deepcopy(owned["FpgaImages"][0])]
                        owned["FpgaImages"] *= 2
                with self.assertRaises(ValueError):
                    f2_preflight.audit_resources(summary, inventory)

    def test_resource_summary_cannot_drop_pending_or_active_work(self):
        for field in ("pending_afi_ids", "owned_afi_ids", "active_loop_instance_ids", "local_processes"):
            with self.subTest(field=field):
                inventory, summary = resource_fixture()
                summary[field] = []
                with self.assertRaisesRegex(ValueError, "resource summary"):
                    f2_preflight.audit_resources(summary, inventory)

    def test_wrong_region_identity_or_loop_ownership_claim_rejects(self):
        for field, value in (("region", "us-east-1"), ("aws_identity", {}),
                             ("pending_afi_scope", "loop-owned")):
            with self.subTest(field=field):
                inventory, summary = resource_fixture()
                summary[field] = value
                with self.assertRaisesRegex(ValueError, "resource summary"):
                    f2_preflight.audit_resources(summary, inventory)
        inventory, summary = resource_fixture()
        inventory["all_loop_instance_filters"][0]["Name"] = "tag:unrelated"
        with self.assertRaisesRegex(ValueError, "filter mismatch"):
            f2_preflight.audit_resources(summary, inventory)
        inventory, summary = resource_fixture()
        inventory["all_loop_instances"][0]["Tags"] = []
        with self.assertRaisesRegex(ValueError, "outside dedicated loop"):
            f2_preflight.audit_resources(summary, inventory)
        inventory, summary = resource_fixture()
        inventory["all_loop_instances"] *= 2
        with self.assertRaisesRegex(ValueError, "duplicate loop instance"):
            f2_preflight.audit_resources(summary, inventory)


if __name__ == "__main__":
    unittest.main()
